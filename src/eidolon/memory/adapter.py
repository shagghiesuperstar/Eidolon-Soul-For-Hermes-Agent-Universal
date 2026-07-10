# SPDX-License-Identifier: Apache-2.0
"""Abstract base class for Eidolon memory adapters (REC-018).

Contract
--------
Every adapter MUST:

- Be **read-side safe**: ``retrieve`` must never raise; degrade loudly via the
  events log and return an empty list if the backend is unavailable.
- Be **write-side loud**: ``store`` must raise ``MemoryStoreError`` (or a
  subclass) on a hard failure rather than silently discarding data.
- Be **consolidation-optional**: ``consolidate`` is a best-effort nightly
  operation.  If the adapter cannot run it (e.g. no LLM provider), it MUST
  emit a DEGRADED event and return 0, not raise.
- Be **pure w.r.t. subprocess**: no shelling out to ``hermes`` or any other
  binary.  All IO goes through the filesystem or in-process data structures.
- Carry **no PII** across the interface.  Callers are responsible for
  sanitizing content before calling ``store``.

Schema
------
A *memory entry* is a plain ``dict`` with at minimum::

    {
        "kind":    str,   # e.g. "lesson", "preference", "reflection"
        "content": str,   # sanitized, operator-visible text
        "ts":      float, # epoch seconds (set by adapter if caller omits)
    }

Adapters MAY add fields but MUST preserve these three.
"""

from __future__ import annotations

import abc
import time
from typing import Any, Dict, List, Optional

MemoryEntry = Dict[str, Any]


class MemoryStoreError(Exception):
    """Raised by ``MemoryAdapter.store`` on an unrecoverable write failure."""


class MemoryAdapter(abc.ABC):
    """Interface every memory backend must implement.

    Subclass this and implement the three abstract methods.
    The constructor must accept no required arguments so the loader
    can instantiate adapters without operator-specific kwargs.
    """

    # Human-readable backend name shown in ``eidolon doctor``.
    name: str = "<unnamed>"

    # ---------------------------------------------------------------------------
    # Abstract interface
    # ---------------------------------------------------------------------------

    @abc.abstractmethod
    def store(self, entry: MemoryEntry) -> None:
        """Persist *entry*.

        Fills in ``entry["ts"]`` if missing.  Raises ``MemoryStoreError`` on
        hard failure.
        """

    @abc.abstractmethod
    def retrieve(
        self,
        *,
        kind: Optional[str] = None,
        limit: int = 50,
        since_ts: Optional[float] = None,
    ) -> List[MemoryEntry]:
        """Return up to *limit* entries matching the filters.

        Results are ordered newest-first.  Never raises; returns ``[]`` on
        any backend error and emits a DEGRADED event.
        """

    @abc.abstractmethod
    def consolidate(self) -> int:
        """Merge near-duplicate entries to keep the store compact.

        Returns the number of entries removed (0 if nothing to do or if the
        operation is not supported by this adapter).
        """

    # ---------------------------------------------------------------------------
    # Helpers available to all subclasses
    # ---------------------------------------------------------------------------

    @staticmethod
    def _stamp(entry: MemoryEntry) -> MemoryEntry:
        """Return *entry* with ``ts`` set to now if absent."""
        if "ts" not in entry:
            entry = {**entry, "ts": time.time()}
        return entry

    @staticmethod
    def _validate_entry(entry: MemoryEntry) -> None:
        """Raise ``ValueError`` if *entry* is missing required fields."""
        for field in ("kind", "content"):
            if field not in entry:
                raise ValueError(f"memory entry missing required field: {field!r}")
