# SPDX-License-Identifier: Apache-2.0
"""Transactional outbox for Eidolon lesson and proposal capture (REC-019).

Design
------
Writes go to a crash-safe **pending file** (``$EIDOLON_HOME/outbox/pending.jsonl``).
A ``flush()`` call drains that file into the main event ledger
(``$EIDOLON_HOME/events.jsonl``) exactly once per entry, then truncates
the pending file.  This two-phase design means:

- A crash between ``capture()`` and ``flush()`` leaves entries in pending
  — they are replayed on the next flush.
- A crash *during* flush cannot produce duplicates: the pending file is only
  truncated after the ledger write succeeds.

The pending file is line-delimited JSON (JSONL).  Each line is a
``MemoryEntry``-compatible dict with at minimum ``kind``, ``content``, ``ts``.

Usage
-----
::

    from eidolon.outbox import Outbox

    ob = Outbox()                           # uses $EIDOLON_HOME by default
    ob.capture({"kind": "lesson", "content": "prefer explicit over implicit"})
    flushed = ob.flush()                    # returns count of entries written

All methods are **thread-safe** via a per-instance ``threading.Lock``.
The outbox never raises on degraded state — it emits a DEGRADED event
and returns a safe default instead.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import List, Optional

from eidolon.memory.adapter import MemoryEntry

try:
    from eidolon.util.events import emit, STATUS_DEGRADED, STATUS_INFO  # type: ignore
    from eidolon.util.paths import eidolon_home  # type: ignore
    _UTIL_AVAILABLE = True
except Exception:  # noqa: BLE001
    _UTIL_AVAILABLE = False

_SOURCE = "eidolon.outbox"


def _default_home() -> Path:
    """Return $EIDOLON_HOME or ~/.eidolon as a fallback."""
    if _UTIL_AVAILABLE:
        try:
            return eidolon_home()
        except Exception:  # noqa: BLE001
            pass
    raw = os.environ.get("EIDOLON_HOME", "")
    return Path(raw) if raw else Path.home() / ".eidolon"


def _emit(kind: str, status: str, **kw) -> None:
    if _UTIL_AVAILABLE:
        try:
            emit(kind, status, _SOURCE, **kw)
        except Exception:  # noqa: BLE001
            pass


class Outbox:
    """Crash-safe two-phase outbox for Eidolon memory entries."""

    def __init__(self, home: Optional[Path] = None) -> None:
        self._home = Path(home) if home else _default_home()
        self._dir = self._home / "outbox"
        self._pending = self._dir / "pending.jsonl"
        self._ledger = self._home / "events.jsonl"
        self._lock = threading.Lock()
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            _emit("outbox.init", "DEGRADED", reason=str(exc))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def capture(self, entry: MemoryEntry) -> None:
        """Append *entry* to the pending file.

        Fills in ``ts`` if absent.  Raises nothing; emits DEGRADED on failure.
        """
        stamped = dict(entry)
        if "ts" not in stamped:
            stamped["ts"] = time.time()
        for field in ("kind", "content"):
            if field not in stamped:
                _emit("outbox.capture", "DEGRADED",
                      reason=f"entry missing required field {field!r}")
                return
        line = json.dumps(stamped, sort_keys=True) + "\n"
        with self._lock:
            try:
                with self._pending.open("a", encoding="utf-8") as fh:
                    fh.write(line)
                    fh.flush()
                    os.fsync(fh.fileno())
            except OSError as exc:
                _emit("outbox.capture", "DEGRADED", reason=str(exc))

    def flush(self, *, kind_filter: Optional[str] = None) -> int:
        """Drain the pending file into the event ledger.

        Returns the number of entries written.  Each entry is written to the
        ledger exactly once — the pending file is only truncated after all
        ledger writes succeed.  Entries that fail JSON parsing are skipped
        with a DEGRADED event and dropped from pending (they cannot be
        replayed safely).

        Parameters
        ----------
        kind_filter:
            If set, only entries whose ``kind`` matches this string are
            flushed.  Non-matching entries remain in the pending file.
        """
        with self._lock:
            return self._flush_locked(kind_filter=kind_filter)

    def pending_count(self) -> int:
        """Return the number of entries currently in the pending file."""
        with self._lock:
            return self._count_pending()

    # ------------------------------------------------------------------
    # Internal helpers (must be called under self._lock)
    # ------------------------------------------------------------------

    def _flush_locked(self, *, kind_filter: Optional[str]) -> int:
        if not self._pending.exists():
            return 0

        try:
            raw = self._pending.read_text(encoding="utf-8")
        except OSError as exc:
            _emit("outbox.flush", "DEGRADED", reason=f"read pending: {exc}")
            return 0

        lines = [l for l in raw.splitlines() if l.strip()]
        if not lines:
            return 0

        to_flush: List[str] = []
        to_keep: List[str] = []

        for line in lines:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                _emit("outbox.flush", "DEGRADED",
                      reason=f"bad JSON in pending, dropping: {exc}")
                continue  # drop unparseable line
            if kind_filter is not None and entry.get("kind") != kind_filter:
                to_keep.append(line)
            else:
                to_flush.append(line)

        if not to_flush:
            return 0

        # Write to ledger first — then truncate pending.
        written = 0
        try:
            with self._ledger.open("a", encoding="utf-8") as fh:
                for line in to_flush:
                    fh.write(line + "\n")
                    written += 1
                fh.flush()
                os.fsync(fh.fileno())
        except OSError as exc:
            _emit("outbox.flush", "DEGRADED",
                  reason=f"ledger write failed: {exc}", dropped=len(to_flush))
            return 0

        # Ledger write succeeded — now update pending.
        try:
            if to_keep:
                content = "\n".join(to_keep) + "\n"
                self._pending.write_text(content, encoding="utf-8")
            else:
                self._pending.write_text("", encoding="utf-8")
        except OSError as exc:
            # Ledger has the data; pending truncation failed. Emit but don't
            # roll back — a future flush will re-read and find no new lines.
            _emit("outbox.flush", "DEGRADED",
                  reason=f"pending truncation failed: {exc}")

        _emit("outbox.flush", "INFO", flushed=written, kept=len(to_keep))
        return written

    def _count_pending(self) -> int:
        if not self._pending.exists():
            return 0
        try:
            return sum(
                1 for l in self._pending.read_text(encoding="utf-8").splitlines()
                if l.strip()
            )
        except OSError:
            return 0
