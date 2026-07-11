# SPDX-License-Identifier: Apache-2.0
"""Aggregate events.jsonl into a stable numeric report.

Contract:
- Every field is an integer >= 0. Empty state is `0`, never `null`, never "N/A".
- The schema is versioned. Consumers pin `schema=1` and fail loudly on mismatch.
- The aggregator reads events verbatim; it never reinterprets historical events.

Event kinds this aggregator recognises:

    dream.reflect      -> pattern_events += 1 (per record)
    dream.lesson       -> lessons_added += 1
    dream.propose      -> proposals_generated += 1
    dream.apply        -> (observed for empty_state only; NOT DONE)
    dream.rollback     -> rollback_count += 1
    dream.session      -> sessions_observed += 1
    doctor.summary     -> doctor_runs += 1; last_doctor_status = status
    inference.request  -> inference_requests += 1
    inference.degraded -> inference_degraded += 1
    judgment.judged    -> lessons_judged += 1
    judgment.soul      -> soul_edicts += 1
    judgment.skill     -> skills_modified += 1
    judgment.config    -> config_changes += 1
    judgment.retire    -> memory_retired += 1

Vertical-slice scoreboard (v2.0 D4) — lifetime real-state integers, not
windowed event counts and never ledger fakes:

    lessons_extracted  -> persisted memory lessons (Hindsight JSONL)
    proposals_applied  -> EXACTLY judgment metrics Law-of-Done counter
                          from active Eidolon state (never max/floor/merge
                          with dream.apply event counts; ledger/event apply
                          attempts are NOT DONE)
    skills_staged      -> *.md files under HERMES_HOME/skills/_eidolon_staging
    inbox_cleared      -> persisted lessons with done=True
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
    bandit_arms: int = 0
    bandit_episodes: int = 0
    preference_pairs: int = 0
    # Judgment Brain counters (v2.0)
    lessons_judged: int = 0
    soul_edicts: int = 0
    skills_modified: int = 0
    config_changes: int = 0
    memory_retired: int = 0
    # Vertical-slice scoreboard (v2.0 D4) — real state, not ledger fakes
    lessons_extracted: int = 0
    skills_staged: int = 0
    inbox_cleared: int = 0
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
            # Event/ledger apply attempts are NOT DONE. Do not increment
            # proposals_applied; the scoreboard field is set exclusively from
            # persistent judgment metrics below.
            pass
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
        elif kind == "learn.step":
            arms = rec.get("arms", 0)
            if isinstance(arms, int) and arms > r.bandit_arms:
                r.bandit_arms = arms
            iters = rec.get("iterations", 0)
            if isinstance(iters, int):
                r.bandit_episodes += iters
        # Judgment Brain event kinds (v2.0)
        elif kind == "judgment.judged":
            r.lessons_judged += 1
        elif kind == "judgment.soul":
            r.soul_edicts += 1
        elif kind == "judgment.skill":
            r.skills_modified += 1
        elif kind == "judgment.config":
            r.config_changes += 1
        elif kind == "judgment.retire":
            r.memory_retired += 1

    # Fold in-file replay buffer counter (survives event log rotation).
    try:
        from eidolon.learning.replay import count as _replay_count

        stored = _replay_count()
        if stored > r.bandit_episodes:
            r.bandit_episodes = stored
    except Exception:  # noqa: BLE001 — reporting must never crash
        pass

    # Non-empty arm registry counts even without episodes yet.
    if r.bandit_arms == 0:
        try:
            from eidolon.learning.arms import default_registry

            r.bandit_arms = len(default_registry())
        except Exception:  # noqa: BLE001
            pass

    # Fold preference-pair count from persistent store.
    try:
        from eidolon.learning.preferences import count as _pref_count

        r.preference_pairs = _pref_count()
    except Exception:  # noqa: BLE001 — reporting must never crash
        pass

    # Fold judgment counters from persistent judgment metrics store.
    # This survives event-log rotation: the judgment store is the source of
    # truth for lifetime totals; events.jsonl gives the windowed view.
    try:
        from eidolon.judgment.metrics import load as _jload
        from eidolon.util.paths import eidolon_state_dir

        # Active Eidolon state (EIDOLON_STATE_DIR / EIDOLON_HOME / Hermes state).
        # Fall back to default load() (~/.eidolon) for older judgment writes
        # that did not pass an explicit home (other counters only).
        jm = _jload(eidolon_state_dir())
        jm_default = _jload()
        for key in (
            "lessons_judged",
            "soul_edicts",
            "skills_modified",
            "config_changes",
            "memory_retired",
        ):
            a = int(jm.get(key, 0) or 0)
            b = int(jm_default.get(key, 0) or 0)
            jm[key] = a if a >= b else b
        # Only overwrite if the persistent store shows more than what we
        # counted in the window — prevents double-counting on a cold log.
        if jm.get("lessons_judged", 0) > r.lessons_judged:
            r.lessons_judged = jm["lessons_judged"]
        if jm.get("soul_edicts", 0) > r.soul_edicts:
            r.soul_edicts = jm["soul_edicts"]
        if jm.get("skills_modified", 0) > r.skills_modified:
            r.skills_modified = jm["skills_modified"]
        if jm.get("config_changes", 0) > r.config_changes:
            r.config_changes = jm["config_changes"]
        if jm.get("memory_retired", 0) > r.memory_retired:
            r.memory_retired = jm["memory_retired"]
        # Scoreboard (D4): proposals_applied is EXACTLY the active-state
        # Law-of-Done judgment metric integer. Never max/floor/merge with
        # windowed dream.apply event counts — those are NOT DONE.
        r.proposals_applied = int(jm.get("proposals_applied", 0) or 0)
    except Exception:  # noqa: BLE001 — reporting must never crash
        pass

    # Scoreboard (D4): real filesystem / memory state, never ledger fakes.
    try:
        from eidolon.util.paths import hermes_home

        staging = hermes_home() / "skills" / "_eidolon_staging"
        if staging.is_dir():
            r.skills_staged = sum(
                1 for p in staging.iterdir() if p.is_file() and p.suffix == ".md"
            )
    except Exception:  # noqa: BLE001 — reporting must never crash
        pass

    try:
        from eidolon.memory.hindsight import HindsightAdapter

        # High limit: scoreboard is lifetime state, not a sample window.
        lessons = HindsightAdapter().retrieve(kind="lesson", limit=100_000)
        r.lessons_extracted = len(lessons)
        r.inbox_cleared = sum(1 for e in lessons if e.get("done") is True)
    except Exception:  # noqa: BLE001 — reporting must never crash
        pass

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
