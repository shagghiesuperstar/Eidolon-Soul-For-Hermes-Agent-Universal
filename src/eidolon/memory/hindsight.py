# SPDX-License-Identifier: Apache-2.0
"""Hindsight adapter — filesystem-backed production backend (REC-018).

Storage layout under the Eidolon state directory::

    $EIDOLON_HOME/memory/hindsight.jsonl  — append-only entry log

Design principles:
- Filesystem-only: no subprocesses, no network calls.
- Loud on write failure: ``store`` raises ``MemoryStoreError`` rather than
  discarding data silently.
- Graceful on read: ``retrieve`` catches all IO errors, emits a DEGRADED
  event, and returns ``[]``.
- Consolidation: removes exact-content duplicates within the same ``kind``;
  emits an INFO event with ``removed`` count.  Pure regex, no LLM.
- Hermes-host optional: degrades to DEGRADED (never FAIL) when
  ``$HERMES_HOME`` does not exist.

Thread / process safety: append-mode file IO is safe at hourly cron cadence.
Concurrent writers at sub-second frequency are out of scope for v1.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from eidolon.memory.adapter import MemoryAdapter, MemoryEntry, MemoryStoreError
from eidolon.util.events import emit, STATUS_DEGRADED, STATUS_INFO
from eidolon.util.paths import eidolon_state_dir

_SOURCE = "eidolon.memory.hindsight"


def _memory_dir() -> Path:
    """Directory that owns the hindsight store; created on first use."""
    d = eidolon_state_dir() / "memory"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _store_path() -> Path:
    return _memory_dir() / "hindsight.jsonl"


class HindsightAdapter(MemoryAdapter):
    """Append-only JSONL memory store persisted under the Eidolon state directory."""

    name = "hindsight"

    # ------------------------------------------------------------------
    # MemoryAdapter interface
    # ------------------------------------------------------------------

    def store(self, entry: MemoryEntry) -> None:
        """Persist *entry* to ``hindsight.jsonl``.

        Raises ``MemoryStoreError`` if required fields are missing or if the
        file cannot be written.
        """
        try:
            self._validate_entry(entry)
        except ValueError as exc:
            raise MemoryStoreError(str(exc)) from exc

        entry = self._stamp(entry)
        line = json.dumps(entry, separators=(",", ":"), sort_keys=True)
        try:
            path = _store_path()
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError as exc:
            raise MemoryStoreError(f"hindsight write failed: {exc}") from exc

    def retrieve(
        self,
        *,
        kind: Optional[str] = None,
        limit: int = 50,
        since_ts: Optional[float] = None,
    ) -> List[MemoryEntry]:
        """Return up to *limit* entries matching filters, newest-first.

        Never raises: IO errors emit DEGRADED and return ``[]``.
        """
        path = _store_path()
        if not path.exists():
            return []
        results: List[MemoryEntry] = []
        try:
            with path.open("r", encoding="utf-8") as fh:
                for raw in fh:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        entry: MemoryEntry = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if kind is not None and entry.get("kind") != kind:
                        continue
                    if since_ts is not None and entry.get("ts", 0.0) < since_ts:
                        continue
                    results.append(entry)
        except OSError as exc:
            emit(
                "memory.retrieve",
                STATUS_DEGRADED,
                _SOURCE,
                reason=f"hindsight read error: {exc}",
            )
            return []
        results.sort(key=lambda e: e.get("ts", 0.0), reverse=True)
        return results[:limit]

    def consolidate(self) -> int:
        """Remove exact-content duplicates within each ``kind``.

        Two entries are considered duplicates if they share the same ``kind``
        and ``content`` (case-sensitive).  The *newest* entry (highest ``ts``)
        is kept.  Returns the number of entries removed.

        Emits an INFO event with ``removed`` count.  Emits DEGRADED on IO
        error.  Never raises.
        """
        path = _store_path()
        if not path.exists():
            return 0

        try:
            raw_lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            emit(
                "memory.consolidate",
                STATUS_DEGRADED,
                _SOURCE,
                reason=f"consolidate read error: {exc}",
            )
            return 0

        raw_entries: List[MemoryEntry] = []
        for ln in raw_lines:
            ln = ln.strip()
            if not ln:
                continue
            try:
                raw_entries.append(json.loads(ln))
            except json.JSONDecodeError:
                continue

        # Deduplicate: keep newest per (kind, content).
        seen: Dict[tuple, MemoryEntry] = {}
        for entry in raw_entries:
            key = (entry.get("kind", ""), entry.get("content", ""))
            existing = seen.get(key)
            if existing is None or entry.get("ts", 0.0) > existing.get("ts", 0.0):
                seen[key] = entry

        kept = list(seen.values())
        removed = len(raw_entries) - len(kept)

        if removed > 0:
            kept.sort(key=lambda e: e.get("ts", 0.0))
            try:
                with path.open("w", encoding="utf-8") as fh:
                    for entry in kept:
                        fh.write(
                            json.dumps(entry, separators=(",", ":"), sort_keys=True)
                            + "\n"
                        )
            except OSError as exc:
                emit(
                    "memory.consolidate",
                    STATUS_DEGRADED,
                    _SOURCE,
                    reason=f"consolidate write error: {exc}",
                )
                return 0

        emit(
            "memory.consolidate",
            STATUS_INFO,
            _SOURCE,
            removed=removed,
        )
        return removed
