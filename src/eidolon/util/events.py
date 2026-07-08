# SPDX-License-Identifier: Apache-2.0
"""Append-only structured event log.

Design:
- One JSON object per line (JSONL). Never rewritten, only appended.
- Schema is versioned; the reader tolerates unknown fields for forward compat.
- Every event has: ts (epoch seconds), kind (str), status (PASS|DEGRADED|FAIL|INFO),
  source (module), and optional structural payload. Never operator content.

Callers:
- doctor.checks.*        (kind=doctor.<check>)
- commands.rollback      (kind=rollback.*)
- inference.router       (kind=inference.request / inference.degraded)
- dream-cycle handler    (kind=dream.reflect / dream.propose / dream.apply)
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Iterable

from eidolon.util.paths import events_log

SCHEMA_VERSION = 1

STATUS_PASS = "PASS"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"
STATUS_INFO = "INFO"

_VALID = {STATUS_PASS, STATUS_DEGRADED, STATUS_FAIL, STATUS_INFO}


def emit(kind: str, status: str, source: str, **payload: Any) -> Dict[str, Any]:
    """Append a structured event to the events log. Returns the event record."""
    if status not in _VALID:
        raise ValueError(f"Invalid status {status!r}; expected one of {_VALID}")
    record = {
        "schema": SCHEMA_VERSION,
        "ts": time.time(),
        "kind": kind,
        "status": status,
        "source": source,
        **payload,
    }
    path = events_log()
    # Line-buffered append; multi-process safe enough for hourly cron cadence.
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n")
    return record


def read(since_ts: float | None = None) -> Iterable[Dict[str, Any]]:
    """Yield events with ts >= since_ts (or all events if None)."""
    path = events_log()
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                # Never crash the reader on a corrupt line; emit an INFO and skip.
                continue
            if since_ts is None or rec.get("ts", 0) >= since_ts:
                yield rec
