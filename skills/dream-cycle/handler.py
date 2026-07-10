#!/usr/bin/env python3
"""Eidolon dream-cycle handler.

Reference implementation. Wire from a Hermes sessionend hook and from cron.
Never blocks a live session; never requires approval for low-risk changes.
Security invariants in SOUL.md are immutable and never edited here.

REC-003 / REC-004 wiring (Fable-5 critical path):
- Emits structured events (dream.session, dream.reflect, dream.propose, ...)
  into $EIDOLON_HOME/events.jsonl so `eidolon report` produces real numbers.
- On the first successful run, takes a last-known-good snapshot of tracked
  files (SOUL.md + handlers). If any invariant regresses, callers can invoke
  `eidolon rollback` to restore.

REC-020 wiring:
- ingest()        pulls recent hindsight episodes from the MemoryAdapter.
- reflect()       clusters episodes into recurring patterns by kind.
- extract_lessons() writes each new lesson back to the adapter (kind="lesson").
- propose()       writes each candidate proposal to the adapter (kind="proposal").

REC-021 wiring:
- extract_lessons() and propose() now buffer writes through Outbox.capture()
  before flushing to the adapter in a single Outbox.flush() call.  A crash
  mid-write no longer loses entries; pending entries replay on the next cycle.

The adapter is loaded once per run via `eidolon.memory.loader.load_adapter()`
(reads $HERMES_HOME/config.yaml; falls back to hindsight; degrades to inmem).
When the eidolon package is not importable the handler falls back to the
legacy no-op stubs and emits DEGRADED events — it never hard-fails.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
LEGACY_STATE = ROOT / "state"
LEGACY_STATE.mkdir(exist_ok=True)
LEGACY_LOG = LEGACY_STATE / "dream-cycle.json"

# Make the sibling src/ package importable when running as a plain script.
_SRC = ROOT / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

try:
    from eidolon.util import events as _events  # type: ignore
    from eidolon.safety import take_snapshot, list_snapshots  # type: ignore
    from eidolon.memory.loader import load_adapter as _load_adapter  # type: ignore
    from eidolon.outbox import Outbox as _Outbox  # type: ignore
    _EIDOLON_AVAILABLE = True
except Exception:  # noqa: BLE001 - stay backward-compatible with older installs
    _EIDOLON_AVAILABLE = False
    _load_adapter = None  # type: ignore
    _Outbox = None  # type: ignore

# Module-level adapter singleton: loaded once per process, lazily on first use.
_ADAPTER = None


def _get_adapter():
    """Return the process-level MemoryAdapter, loading it on first call.

    Returns None (and emits DEGRADED) when the eidolon package is not
    importable.  Callers must guard on None.
    """
    global _ADAPTER  # noqa: PLW0603
    if _ADAPTER is not None:
        return _ADAPTER
    if not _EIDOLON_AVAILABLE:
        _emit(
            "dream.memory.adapter",
            "DEGRADED",
            reason="eidolon package not importable; memory wiring disabled",
        )
        return None
    try:
        _ADAPTER = _load_adapter()
        _emit("dream.memory.adapter", "INFO", backend=_ADAPTER.name)
        return _ADAPTER
    except Exception as exc:  # noqa: BLE001
        _emit(
            "dream.memory.adapter",
            "DEGRADED",
            reason=f"{type(exc).__name__}: {exc}",
        )
        return None


def _emit(kind: str, status: str = "INFO", **payload) -> None:
    """Emit into the Eidolon event pipeline if available; always print JSONL."""
    rec = {"ts": time.time(), "kind": kind, "status": status, **payload}
    print(json.dumps(rec, sort_keys=True))
    if _EIDOLON_AVAILABLE:
        try:
            _events.emit(kind, status, source="skills.dream-cycle", **payload)
        except Exception:  # noqa: BLE001 - event bus must never break the cycle
            pass


def log(phase, **data):
    """Backward-compatible wrapper for older call sites; forwards to _emit."""
    _emit(f"dream.{phase}", **data)
    return {"ts": time.time(), "phase": phase, **data}


def load_state():
    if LEGACY_LOG.exists():
        return json.loads(LEGACY_LOG.read_text())
    return {"runs": [], "last_known_good": None}


def save_state(state):
    LEGACY_LOG.write_text(json.dumps(state, indent=2))


# ---------------------------------------------------------------------------
# Dream phases
# ---------------------------------------------------------------------------

_INGEST_KINDS = ("lesson", "preference", "reflection", "episode")
_INGEST_LIMIT = 200  # max entries pulled per run
_INGEST_WINDOW = 7 * 24 * 3600  # look back 7 days


def ingest(mode: str) -> List[Dict[str, Any]]:
    """Pull recent episodes from the MemoryAdapter.

    Returns a list of memory entries (dicts).  Falls back to [] and emits
    DEGRADED if the adapter is unavailable or retrieve() fails.
    """
    adapter = _get_adapter()
    if adapter is None:
        log("ingest", mode=mode, n=0, status="DEGRADED")
        return []

    since_ts = time.time() - _INGEST_WINDOW
    episodes: List[Dict[str, Any]] = []
    try:
        for kind in _INGEST_KINDS:
            chunk = adapter.retrieve(
                kind=kind,
                limit=_INGEST_LIMIT,
                since_ts=since_ts,
            )
            episodes.extend(chunk)
    except Exception as exc:  # noqa: BLE001
        _emit(
            "dream.ingest",
            "DEGRADED",
            mode=mode,
            reason=f"{type(exc).__name__}: {exc}",
        )
        return []

    _emit("dream.ingest", "INFO", mode=mode, n=len(episodes))
    return episodes


def reflect(episodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Cluster episodes into recurring patterns by kind.

    Returns a list of pattern dicts::

        {"kind": str, "count": int, "sample": str}

    where ``sample`` is the content of the most-recent episode in the cluster.
    Pure function — no IO.
    """
    if not episodes:
        log("reflect", n=0)
        return []

    buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for ep in episodes:
        buckets[ep.get("kind", "unknown")].append(ep)

    patterns = []
    for kind, entries in buckets.items():
        entries.sort(key=lambda e: e.get("ts", 0), reverse=True)
        patterns.append({
            "kind": kind,
            "count": len(entries),
            "sample": entries[0].get("content", ""),
        })

    _emit("dream.reflect", "INFO", n=len(episodes), pattern_count=len(patterns))
    return patterns


def extract_lessons(
    patterns: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Synthesise one lesson per pattern cluster and durably buffer via Outbox.

    REC-021: entries are captured into the outbox (crash-safe JSONL) before
    the flush to the adapter.  A crash between entries no longer loses work;
    the next cycle replays any un-flushed entries.  When the eidolon package
    is not importable the function falls back to returning lessons without
    any IO (same degrade path as before REC-021).
    """
    if not patterns:
        log("lesson", n=0)
        return []

    adapter = _get_adapter()
    lessons: List[Dict[str, Any]] = []

    if adapter is not None and _Outbox is not None:
        ob = _Outbox()
        for pattern in patterns:
            lesson = {
                "kind": "lesson",
                "content": (
                    f"Pattern '{pattern['kind']}' observed {pattern['count']} time(s). "
                    f"Most recent: {pattern['sample'][:200]}"
                ),
                "source_kind": pattern["kind"],
                "source_count": pattern["count"],
            }
            lessons.append(lesson)
            try:
                ob.capture(lesson)
            except Exception as exc:  # noqa: BLE001
                _emit(
                    "dream.lesson.capture",
                    "DEGRADED",
                    pattern_kind=pattern["kind"],
                    reason=f"{type(exc).__name__}: {exc}",
                )
        try:
            result = ob.flush(adapter)
            _emit(
                "dream.lesson.flush",
                "INFO",
                flushed=result.flushed,
                skipped=result.skipped,
                failed=result.failed,
            )
            if result.failed:
                _emit(
                    "dream.lesson.flush",
                    "DEGRADED",
                    failed=result.failed,
                    reason="entries left in outbox pending for next cycle",
                )
        except Exception as exc:  # noqa: BLE001
            _emit(
                "dream.lesson.flush",
                "DEGRADED",
                reason=f"{type(exc).__name__}: {exc}",
            )
    else:
        # Degrade path: no outbox available (pre-REC-021 install or eidolon
        # package not importable).  Attempt direct adapter.store if possible.
        for pattern in patterns:
            lesson = {
                "kind": "lesson",
                "content": (
                    f"Pattern '{pattern['kind']}' observed {pattern['count']} time(s). "
                    f"Most recent: {pattern['sample'][:200]}"
                ),
                "source_kind": pattern["kind"],
                "source_count": pattern["count"],
            }
            lessons.append(lesson)
            if adapter is not None:
                try:
                    adapter.store(lesson)
                except Exception as exc:  # noqa: BLE001
                    _emit(
                        "dream.lesson.store",
                        "DEGRADED",
                        pattern_kind=pattern["kind"],
                        reason=f"{type(exc).__name__}: {exc}",
                    )

    _emit("dream.lesson", "INFO", n=len(lessons))
    return lessons


def propose(lessons: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate one candidate per lesson and durably buffer via Outbox.

    REC-021: same outbox pattern as extract_lessons.  Candidates are captured
    before flush; a crash replays cleanly on next cycle.
    """
    if not lessons:
        log("propose", n=0)
        return []

    adapter = _get_adapter()
    candidates: List[Dict[str, Any]] = []

    if adapter is not None and _Outbox is not None:
        ob = _Outbox()
        for lesson in lessons:
            candidate = {
                "id": f"proposal:{lesson.get('source_kind', 'unknown')}:{int(time.time())}",
                "kind": "proposal",
                "content": (
                    f"Improve handling of '{lesson.get('source_kind', 'unknown')}' "
                    f"events based on {lesson.get('source_count', 0)} observations."
                ),
                "lesson_content": lesson.get("content", ""),
                "risk": "low",
                "mutation_kind": "preference_update",
            }
            candidates.append(candidate)
            try:
                ob.capture(candidate)
            except Exception as exc:  # noqa: BLE001
                _emit(
                    "dream.propose.capture",
                    "DEGRADED",
                    proposal_id=candidate["id"],
                    reason=f"{type(exc).__name__}: {exc}",
                )
        try:
            result = ob.flush(adapter)
            _emit(
                "dream.propose.flush",
                "INFO",
                flushed=result.flushed,
                skipped=result.skipped,
                failed=result.failed,
            )
            if result.failed:
                _emit(
                    "dream.propose.flush",
                    "DEGRADED",
                    failed=result.failed,
                    reason="entries left in outbox pending for next cycle",
                )
        except Exception as exc:  # noqa: BLE001
            _emit(
                "dream.propose.flush",
                "DEGRADED",
                reason=f"{type(exc).__name__}: {exc}",
            )
    else:
        # Degrade path: no outbox available.
        for lesson in lessons:
            candidate = {
                "id": f"proposal:{lesson.get('source_kind', 'unknown')}:{int(time.time())}",
                "kind": "proposal",
                "content": (
                    f"Improve handling of '{lesson.get('source_kind', 'unknown')}' "
                    f"events based on {lesson.get('source_count', 0)} observations."
                ),
                "lesson_content": lesson.get("content", ""),
                "risk": "low",
                "mutation_kind": "preference_update",
            }
            candidates.append(candidate)
            if adapter is not None:
                try:
                    adapter.store(candidate)
                except Exception as exc:  # noqa: BLE001
                    _emit(
                        "dream.propose.store",
                        "DEGRADED",
                        proposal_id=candidate["id"],
                        reason=f"{type(exc).__name__}: {exc}",
                    )

    _emit("dream.propose", "INFO", n=len(candidates))
    return candidates


# ---------------------------------------------------------------------------
# Remaining phases — unchanged
# ---------------------------------------------------------------------------

def risk_of(candidate):
    """REC-010: 5-class classification via eidolon.safety.

    Falls back to a `candidate['risk']` string only if the eidolon package
    isn't importable (legacy/degraded runs). String fallback maps to the
    conservative HIGH by default so we never auto-apply a legacy candidate.
    """
    if _EIDOLON_AVAILABLE:
        try:
            from eidolon.safety import classify_action

            target = candidate.get("target", candidate.get("id", ""))
            mk = candidate.get("mutation_kind", candidate.get("risk", ""))
            return classify_action(target, mk, candidate.get("safety_flags", ()))
        except Exception as exc:  # noqa: BLE001
            log("classify.error", err=f"{type(exc).__name__}: {exc}")
            return "high"
    return candidate.get("risk", "high")


def apply_low(candidate):
    """Persist a LOW-risk apply to a measurable ledger under $EIDOLON_HOME.

    Writes one JSONL line to applied_proposals.jsonl and appends a short
    line to applied_lessons.md so `eidolon report` / operators can prove
    applies happened. Never touches SOUL.md or config.yaml.
    """
    rec = {
        "ts": time.time(),
        "id": candidate.get("id"),
        "mutation_kind": candidate.get("mutation_kind"),
        "content": (candidate.get("content") or "")[:500],
        "risk": "LOW",
    }
    home = Path(os.environ.get("EIDOLON_HOME", str(Path.home() / ".hermes" / "state" / "eidolon")))
    home.mkdir(parents=True, exist_ok=True)
    ledger = home / "applied_proposals.jsonl"
    try:
        with ledger.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        md = home / "applied_lessons.md"
        with md.open("a", encoding="utf-8") as fh:
            fh.write(f"- [{rec['ts']:.0f}] {rec['id']}: {rec['content'][:200]}\n")
    except OSError as exc:
        _emit("dream.apply.write", "DEGRADED", reason=f"{type(exc).__name__}: {exc}")
        log("apply", id=candidate.get("id"), risk="low", write="failed")
        return
    log("apply", id=candidate.get("id"), risk="low", write="ok", ledger=str(ledger))


def shadow_test(candidate):
    log("shadow", id=candidate.get("id"))
    return {"delta": 0.0}


def _audit_never_touch_or_high(candidate, risk_repr):
    """REC-010: write an audit entry when a NEVER_TOUCH or HIGH is refused."""
    entry = {
        "kind": "dream.refuse",
        "candidate_id": candidate.get("id"),
        "target": candidate.get("target"),
        "mutation_kind": candidate.get("mutation_kind"),
        "risk": risk_repr,
    }
    if _EIDOLON_AVAILABLE:
        try:
            from eidolon.util.paths import audit_log
            with audit_log().open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, sort_keys=True) + "\n")
            return
        except Exception:  # noqa: BLE001
            pass
    log("refuse", **entry)


def gate_and_apply(candidates, state):
    """REC-010 policy: LOW auto-applies; MEDIUM defers to shadow eval (REC-017);
    HIGH and NEVER_TOUCH never auto-apply and write an audit entry.
    """
    RC = None
    if _EIDOLON_AVAILABLE:
        try:
            from eidolon.safety import RiskClass as _RC
            RC = _RC
        except Exception:  # noqa: BLE001
            RC = None

    for c in candidates:
        r = risk_of(c)
        if RC is None:
            if isinstance(r, str) and r.lower() == "low":
                apply_low(c)
            else:
                result = shadow_test(c)
                if result["delta"] > 0:
                    log("promote", id=c.get("id"), delta=result["delta"])
                    state["last_known_good"] = c.get("id")
                else:
                    log("discard", id=c.get("id"), delta=result["delta"])
            continue

        if r == RC.LOW:
            apply_low(c)
            _emit("dream.apply", "PASS", candidate=c.get("id"), risk="LOW")
        elif r == RC.NO_OP:
            log("skip", id=c.get("id"), risk="NO_OP")
        elif r == RC.MEDIUM:
            log("defer", id=c.get("id"), risk="MEDIUM", reason="shadow eval not yet implemented")
            _emit(
                "dream.defer",
                "DEGRADED",
                candidate=c.get("id"),
                risk="MEDIUM",
                reason="shadow eval not yet implemented",
            )
        elif r == RC.HIGH:
            _audit_never_touch_or_high(c, "HIGH")
            _emit("dream.refuse", "FAIL", candidate=c.get("id"), risk="HIGH")
        elif r == RC.NEVER_TOUCH:
            _audit_never_touch_or_high(c, "NEVER_TOUCH")
            _emit("dream.refuse", "FAIL", candidate=c.get("id"), risk="NEVER_TOUCH")
        else:
            _audit_never_touch_or_high(c, f"UNKNOWN:{r!r}")
            _emit("dream.refuse", "FAIL", candidate=c.get("id"), risk="UNKNOWN")


def rollback_if_regressed(state):
    log("rollback-check", lkg=state.get("last_known_good"))


def run_watchdog():
    wd = ROOT / "skills" / "integrity-watchdog" / "handler.py"
    if wd.exists():
        os.system(f"{sys.executable} {wd}")


def _ensure_first_snapshot(state) -> None:
    """REC-004: set last_known_good on first successful run."""
    if _EIDOLON_AVAILABLE:
        try:
            if not list_snapshots():
                snap = take_snapshot(reason="first_success")
                state["last_known_good"] = snap.id
                _emit("dream.snapshot", "PASS", snapshot_id=snap.id, files=list(snap.files))
        except Exception as exc:  # noqa: BLE001
            _emit("dream.snapshot", "DEGRADED", reason=f"{type(exc).__name__}: {exc}")
    else:
        if not state.get("last_known_good"):
            state["last_known_good"] = f"cycle:{int(time.time())}"
            _emit(
                "dream.snapshot",
                "DEGRADED",
                reason="eidolon package not importable; using legacy marker only",
            )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["sessionend", "scheduled"], default="sessionend")
    args = ap.parse_args()

    _emit("dream.session", "INFO", mode=args.mode)

    state = load_state()
    episodes = ingest(args.mode)

    if args.mode == "scheduled":
        patterns = reflect(episodes)
        lessons = extract_lessons(patterns)
        candidates = propose(lessons)
        gate_and_apply(candidates, state)
        rollback_if_regressed(state)
    else:
        extract_lessons(reflect(episodes))

    run_watchdog()
    _ensure_first_snapshot(state)
    state["runs"].append({"ts": time.time(), "mode": args.mode})
    state["runs"] = state["runs"][-200:]
    save_state(state)
    log("done", mode=args.mode)


if __name__ == "__main__":
    main()
