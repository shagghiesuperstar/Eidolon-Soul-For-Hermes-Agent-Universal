"""Aggregate events.jsonl into a stable numeric report.

Contract:
- Every field is an integer >= 0. Empty state is `0`, never `null`, never "N/A".
- The schema is versioned. Consumers pin `schema=1` and fail loudly on mismatch.
- The aggregator reads events verbatim; it never reinterprets historical events.

Event kinds this aggregator recognises:

    dream.reflect      -> pattern_events += 1 (per record)
    dream.lesson       -> lessons_added += 1
    dream.propose      -> proposals_generated += 1
    dream.apply        -> proposals_applied += 1
    dream.rollback     -> rollback_count += 1
    dream.session      -> sessions_observed += 1
    doctor.summary     -> doctor_runs += 1; last_doctor_status = status
    inference.request  -> inference_requests += 1
    inference.degraded -> inference_degraded += 1
"""

from __future__ import annotations

import time
from dataclasses import dataclass, asdict, field
from typing import Any, Dict

from eidolon.util import events


SCHEMA = 1


@dataclass
class Report:
    schema: int = SCHEMA
    since_ts: float = 0.0
    generated_ts: float = 0.0
    window: str = ""
    sessions_observed: int = 0
    pattern_events: int = 0
    lessons_added: int = 0
    proposals_generated: int = 0
    proposals_applied: int = 0
    rollback_count: int = 0
    doctor_runs: int = 0
    last_doctor_status: str = "UNKNOWN"
    inference_requests: int = 0
    inference_degraded: int = 0
    empty_state: bool = True
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Parse human-friendly window strings ("24h", "7d", "1h") to seconds.
_UNITS = {"h": 3600, "d": 86400, "m": 60}


def parse_window(window: str) -> int:
    window = window.strip().lower()
    if not window:
        raise ValueError("empty window")
    unit = window[-1]
    if unit not in _UNITS:
        raise ValueError(f"unknown window unit {unit!r}; expected h/d/m")
    try:
        n = int(window[:-1])
    except ValueError as exc:
        raise ValueError(f"invalid window quantity in {window!r}") from exc
    if n <= 0:
        raise ValueError("window quantity must be positive")
    return n * _UNITS[unit]


def build(window: str = "24h", *, now_ts: float | None = None) -> Report:
    """Aggregate events in the given window and return a structured report."""
    now = now_ts if now_ts is not None else time.time()
    seconds = parse_window(window)
    since = now - seconds

    r = Report(since_ts=since, generated_ts=now, window=window)
    saw_any = False

    for rec in events.read(since_ts=since):
        saw_any = True
        kind = rec.get("kind", "")
        status = rec.get("status", "")
        if kind == "dream.reflect":
            r.pattern_events += 1
        elif kind == "dream.lesson":
            r.lessons_added += 1
        elif kind == "dream.propose":
            r.proposals_generated += 1
        elif kind == "dream.apply":
            r.proposals_applied += 1
        elif kind == "dream.rollback":
            r.rollback_count += 1
        elif kind == "dream.session":
            r.sessions_observed += 1
        elif kind == "doctor.summary":
            r.doctor_runs += 1
            if isinstance(status, str) and status:
                r.last_doctor_status = status
        elif kind == "inference.request":
            r.inference_requests += 1
        elif kind == "inference.degraded":
            r.inference_degraded += 1

    r.empty_state = not saw_any
    if r.empty_state:
        r.notes.append(
            "no events in window: this is a first-run install. "
            "Once dream-cycle runs, metrics will populate."
        )
    if r.rollback_count > 0:
        r.notes.append(
            f"rollback triggered {r.rollback_count}x in window; "
            "inspect audit log."
        )
    if r.inference_degraded > 0 and r.inference_requests == 0:
        r.notes.append(
            "all inference attempts degraded in this window: "
            "check `eidolon doctor --model-check`."
        )
    return r
