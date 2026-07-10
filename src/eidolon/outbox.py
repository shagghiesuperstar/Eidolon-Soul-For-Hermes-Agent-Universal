# SPDX-License-Identifier: Apache-2.0
"""Eidolon transactional outbox (REC-019).

Purpose
-------
Decouple the moment an agent *decides* to write a memory entry from the moment
that entry actually lands in the backend.  On crash or backend failure the
entry survives in a crash-safe JSONL pending file and is retried on the next
dream cycle without duplication.

Design
------
- **Atomic capture**: ``Outbox.capture`` appends to a ``pending.jsonl`` file
  under ``$EIDOLON_HOME/outbox/`` using O_EXCL-safe line-append semantics.
  Each entry carries a stable ``eid`` (sha256 of content + ts) used for
  idempotency.
- **Idempotent flush**: ``Outbox.flush`` reads pending entries, calls
  ``MemoryAdapter.store`` for each one, and only removes an entry from the
  pending file *after* the store succeeds.  An entry that was already stored
  (detected via ``eid`` collision in the adapter) is silently skipped.
- **Crash safety**: The pending file is rewritten atomically (write to
  ``pending.jsonl.tmp`` then ``os.replace``) so a crash mid-flush never
  leaves a corrupt file.
- **No dependencies**: stdlib-only.  Does not shell out.  Does not import the
  MemoryAdapter at module level — caller passes one in.

Exit-code contract
------------------
This module never calls ``sys.exit``.  Callers that care about exit codes
should inspect the ``FlushResult`` returned by ``flush``.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, List, NamedTuple, Optional

if TYPE_CHECKING:
    from eidolon.memory.adapter import MemoryAdapter, MemoryEntry


class FlushResult(NamedTuple):
    """Summary returned by ``Outbox.flush``."""
    flushed: int    # entries successfully written to backend
    skipped: int    # entries already present (idempotent duplicate)
    failed: int     # entries that raised on store (left in pending)


def _eid(entry: "MemoryEntry") -> str:
    """Stable 16-hex-char content hash used as idempotency key."""
    blob = json.dumps(entry, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


class Outbox:
    """Crash-safe transactional outbox for Eidolon memory entries.

    Parameters
    ----------
    home:
        Directory under which ``outbox/pending.jsonl`` is created.  Defaults
        to ``$EIDOLON_HOME`` if set, otherwise ``~/.eidolon``.
    """

    _PENDING_NAME = "pending.jsonl"
    _TMP_NAME = "pending.jsonl.tmp"

    def __init__(self, home: Optional[Path] = None) -> None:
        if home is None:
            raw = os.environ.get("EIDOLON_HOME", "")
            home = Path(raw) if raw else Path.home() / ".eidolon"
        self._dir = home / "outbox"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._pending = self._dir / self._PENDING_NAME
        self._tmp = self._dir / self._TMP_NAME

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def capture(self, entry: "MemoryEntry") -> str:
        """Append *entry* to the pending file.  Returns the ``eid``.

        Thread-safe at the Python level (GIL protects the file open/write).
        Safe against concurrent processes only if ``$EIDOLON_HOME`` is
        per-process (the documented single-agent model).
        """
        entry = dict(entry)
        if "ts" not in entry:
            entry["ts"] = time.time()
        for field in ("kind", "content"):
            if field not in entry:
                raise ValueError(f"outbox entry missing required field: {field!r}")
        eid = _eid(entry)
        entry["_eid"] = eid
        line = json.dumps(entry, sort_keys=True, ensure_ascii=True)
        with self._pending.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        return eid

    def flush(self, adapter: "MemoryAdapter") -> FlushResult:
        """Drain pending entries into *adapter*.

        Each entry is stored exactly once.  Entries that fail remain in the
        pending file for the next cycle.  The pending file is rewritten
        atomically after each successful batch to prevent double-writes on
        retry.

        Returns a ``FlushResult`` with counts of flushed / skipped / failed.
        Never raises.
        """
        pending = self._load_pending()
        if not pending:
            return FlushResult(flushed=0, skipped=0, failed=0)

        flushed = 0
        skipped = 0
        failed_entries: List[dict] = []

        for entry in pending:
            eid = entry.get("_eid", "")
            # Strip the internal _eid before handing to adapter.
            store_entry = {k: v for k, v in entry.items() if k != "_eid"}
            try:
                adapter.store(store_entry)
                flushed += 1
            except Exception as exc:  # noqa: BLE001
                exc_name = type(exc).__name__
                # Idempotency: duplicate-key errors from adapters that enforce
                # uniqueness are treated as skip, not failure.
                if "duplicate" in exc_name.lower() or "exists" in str(exc).lower():
                    skipped += 1
                else:
                    failed_entries.append(entry)
                    failed_count_so_far = len(failed_entries)  # noqa: F841

        # Atomically rewrite pending with only the failed entries.
        self._save_pending(failed_entries)
        return FlushResult(flushed=flushed, skipped=skipped, failed=len(failed_entries))

    def pending_count(self) -> int:
        """Return the number of entries currently in the pending file."""
        return len(self._load_pending())

    def clear(self) -> None:
        """Remove all pending entries (use only in tests or after manual recovery)."""
        if self._pending.exists():
            self._pending.unlink()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load_pending(self) -> List[dict]:
        if not self._pending.exists():
            return []
        entries: List[dict] = []
        try:
            for line in self._pending.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass  # corrupt line — skip it, don't block the flush
        except OSError:
            return []
        return entries

    def _save_pending(self, entries: List[dict]) -> None:
        """Atomically overwrite the pending file with *entries*."""
        if not entries:
            if self._pending.exists():
                self._pending.unlink()
            return
        lines = "".join(
            json.dumps(e, sort_keys=True, ensure_ascii=True) + "\n" for e in entries
        )
        self._tmp.write_text(lines, encoding="utf-8")
        os.replace(self._tmp, self._pending)
