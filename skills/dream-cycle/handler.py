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
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

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
    _EIDOLON_AVAILABLE = True
except Exception:  # noqa: BLE001 - stay backward-compatible with older installs
    _EIDOLON_AVAILABLE = False


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


def ingest(mode):
    # TODO: pull recent episodes from hindsight memory for this agent.
    log("ingest", mode=mode)
    return []


def reflect(episodes):
    # TODO: cluster episodes; surface recurring failure/success patterns.
    log("reflect", n=len(episodes))
    return []


def extract_lessons(patterns):
    # TODO: write versioned, append-mostly lessons to hindsight memory.
    log("lesson", n=len(patterns))
    return []


def propose(lessons):
    # TODO: generate candidate changes from lessons.
    log("propose", n=len(lessons))
    return []


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
    log("apply", id=candidate.get("id"), risk="low")


def shadow_test(candidate):
    # Run candidate in a sandbox vs baseline; return measured delta.
    log("shadow", id=candidate.get("id"))
    return {"delta": 0.0}


def _audit_never_touch_or_high(candidate, risk_repr):
    """REC-010: write an audit entry when a NEVER_TOUCH or HIGH is refused.

    Writes to eidolon's audit log if available; otherwise falls back to
    the legacy dream-cycle state log so the refusal is never silent.
    """
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
    # Import RiskClass lazily so this handler still runs when the eidolon
    # package isn't installed (loud-degraded mode).
    RC = None
    if _EIDOLON_AVAILABLE:
        try:
            from eidolon.safety import RiskClass as _RC
            RC = _RC
        except Exception:  # noqa: BLE001
            RC = None

    for c in candidates:
        r = risk_of(c)
        # Legacy string path (RC unavailable).
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

        # Fast path: enum-based decision tree.
        if r == RC.LOW:
            apply_low(c)
            _emit("dream.apply", "PASS", candidate=c.get("id"), risk="LOW")
        elif r == RC.NO_OP:
            log("skip", id=c.get("id"), risk="NO_OP")
        elif r == RC.MEDIUM:
            # REC-017 will land shadow eval. Until then, DEGRADED, not applied.
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
        else:  # noqa: PLR2004
            _audit_never_touch_or_high(c, f"UNKNOWN:{r!r}")
            _emit("dream.refuse", "FAIL", candidate=c.get("id"), risk="UNKNOWN")


def rollback_if_regressed(state):
    # TODO: compare current scores vs baseline; revert to LKG on regression.
    log("rollback-check", lkg=state.get("last_known_good"))


def run_watchdog():
    wd = ROOT / "skills" / "integrity-watchdog" / "handler.py"
    if wd.exists():
        os.system(f"{sys.executable} {wd}")


def _ensure_first_snapshot(state) -> None:
    """REC-004: set last_known_good on first successful run.

    If Eidolon package is unavailable, we fall back to the legacy string marker
    (state["last_known_good"] = "cycle:<ts>") so old operators still get *some*
    breadcrumb; loud degraded mode is enforced by emitting `dream.snapshot` with
    status=DEGRADED.
    """
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
