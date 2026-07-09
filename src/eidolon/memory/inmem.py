# SPDX-License-Identifier: Apache-2.0
"""In-memory adapter — CI/testing backend (REC-018).

Design goals:
- Zero filesystem IO: the entire store lives in a Python list.
- Zero external dependencies: stdlib only.
- Sufficient for the full test suite to run without a Hermes host.
- No consolidation logic: near-duplicate merging is out-of-scope for a
  volatile test store.  ``consolidate()`` always returns 0.

This adapter is selected automatically by ``loader.py`` when:
  1. The host config key ``memory.backend`` is absent or set to ``inmem``, OR
  2. The config file is unreadable (degraded fallback).

It is also the default for the entire unit test suite via ``IsolatedHome``.
"""

from __future__ import annotations

from typing import List, Optional

from eidolon.memory.adapter import MemoryAdapter, MemoryEntry, MemoryStoreError


class InMemAdapter(MemoryAdapter):
    """Volatile in-memory memory store.  Never survives process exit."""

    name = "inmem"

    def __init__(self) -> None:
        self._store: List[MemoryEntry] = []

    # ------------------------------------------------------------------
    # MemoryAdapter interface
    # ------------------------------------------------------------------

    def store(self, entry: MemoryEntry) -> None:
        """Append *entry* to the in-process list.

        Raises ``MemoryStoreError`` if required fields are missing rather than
        silently discarding malformed data.
        """
        try:
            self._validate_entry(entry)
        except ValueError as exc:
            raise MemoryStoreError(str(exc)) from exc
        self._store.append(self._stamp(entry))

    def retrieve(
        self,
        *,
        kind: Optional[str] = None,
        limit: int = 50,
        since_ts: Optional[float] = None,
    ) -> List[MemoryEntry]:
        """Return matching entries, newest-first.

        Never raises; returns ``[]`` in the degenerate case (empty store).
        """
        results = list(self._store)
        if kind is not None:
            results = [e for e in results if e.get("kind") == kind]
        if since_ts is not None:
            results = [e for e in results if e.get("ts", 0.0) >= since_ts]
        # Newest-first: sort by ts descending; entries without ts sort last.
        results.sort(key=lambda e: e.get("ts", 0.0), reverse=True)
        return results[:limit]

    def consolidate(self) -> int:
        """No-op: volatile stores don't need consolidation.  Returns 0."""
        return 0

    # ------------------------------------------------------------------
    # Test helpers (not part of the MemoryAdapter interface)
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Empty the store.  Useful in test ``tearDown``."""
        self._store.clear()

    def count(self) -> int:
        """Total entries in the store."""
        return len(self._store)
