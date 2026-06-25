#!/usr/bin/env python3
"""Eidolon dream-cycle handler.

Reference implementation. Wire from a Hermes sessionend hook and from cron.
Never blocks a live session; never requires approval for low-risk changes.
Security invariants in SOUL.md are immutable and never edited here.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state"
STATE.mkdir(exist_ok=True)
LOG = STATE / "dream-cycle.json"


def log(phase, **data):
    rec = {"ts": time.time(), "phase": phase, **data}
    print(json.dumps(rec))
    return rec


def load_state():
    if LOG.exists():
        return json.loads(LOG.read_text())
    return {"runs": [], "last_known_good": None}


def save_state(state):
    LOG.write_text(json.dumps(state, indent=2))


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
    log("extract", n=len(patterns))
    return []


def propose(lessons):
    # TODO: generate candidate changes from lessons.
    log("propose", n=len(lessons))
    return []


def risk_of(candidate):
    # High if it touches behavior, tools, or anything near invariants.
    return candidate.get("risk", "high")


def apply_low(candidate):
    log("apply", id=candidate.get("id"), risk="low")


def shadow_test(candidate):
    # Run candidate in a sandbox vs baseline; return measured delta.
    log("shadow", id=candidate.get("id"))
    return {"delta": 0.0}


def gate_and_apply(candidates, state):
    for c in candidates:
        if risk_of(c) == "low":
            apply_low(c)
        else:
            result = shadow_test(c)
            if result["delta"] > 0:
                log("promote", id=c.get("id"), delta=result["delta"])
                state["last_known_good"] = c.get("id")
            else:
                log("discard", id=c.get("id"), delta=result["delta"])


def rollback_if_regressed(state):
    # TODO: compare current scores vs baseline; revert to LKG on regression.
    log("rollback-check", lkg=state.get("last_known_good"))


def run_watchdog():
    wd = ROOT / "skills" / "integrity-watchdog" / "handler.py"
    if wd.exists():
        os.system(f"{sys.executable} {wd}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["sessionend", "scheduled"], default="sessionend")
    args = ap.parse_args()

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
    state["runs"].append({"ts": time.time(), "mode": args.mode})
    state["runs"] = state["runs"][-200:]
    save_state(state)
    log("done", mode=args.mode)


if __name__ == "__main__":
    main()
