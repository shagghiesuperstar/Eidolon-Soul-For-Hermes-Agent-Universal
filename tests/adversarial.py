#!/usr/bin/env python3
"""Eidolon adversarial test harness.

Proves the three core guarantees by breaking the system on purpose in a
throwaway sandbox copy of the repo. The live repo is never modified.

Usage:  python tests/adversarial.py
Exit code is non-zero if any scenario FAILs.

See tests/TESTPLAN.md for the rationale and pass criteria.
"""
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SEAL_RE = re.compile(r"(<!--\s*SEAL:\s*)([0-9a-fA-F]{64})")
RESULTS = []


def record(name, passed, detail=""):
    RESULTS.append((name, passed, detail))
    tag = "PASS" if passed else "FAIL"
    print(f"[{tag}] {name}" + (f" :: {detail}" if detail else ""))


def sandbox():
    """Copy the repo into a temp dir so attacks never touch the live tree."""
    dst = Path(tempfile.mkdtemp(prefix="eidolon-adv-"))
    shutil.copytree(REPO, dst / "repo", dirs_exist_ok=True)
    return dst / "repo"


def run_watchdog(repo):
    """Invoke the real watchdog handler in the sandbox; return parsed output."""
    wd = repo / "skills" / "integrity-watchdog" / "handler.py"
    proc = subprocess.run(
        [sys.executable, str(wd)],
        capture_output=True, text=True, cwd=str(repo),
        env={**os.environ, "EIDOLON_NOTIFY": ""},  # no real network; logs only
    )
    last = [l for l in proc.stdout.strip().splitlines() if l.strip()]
    try:
        return json.loads(last[-1]) if last else {}
    except json.JSONDecodeError:
        return {"_raw": proc.stdout, "_err": proc.stderr}


def notify_count(repo):
    """How many open incidents are currently marked notified."""
    sf = repo / "state" / "integrity-watchdog.json"
    if not sf.exists():
        return 0, {}
    st = json.loads(sf.read_text())
    inc = st.get("incidents", {})
    return sum(1 for v in inc.values() if v.get("notified")), inc


def scenario_1_soul_tamper():
    repo = sandbox()
    soul = repo / "SOUL.md"
    text = soul.read_text()
    # Flip a byte in the body WITHOUT updating the seal.
    tampered = text.replace("I am an Eidolon", "I am an Eid0lon", 1)
    soul.write_text(tampered)

    first = run_watchdog(repo)
    incident_raised = first.get("status") == "incident" and \
        any(k.startswith("soul:") for k in first.get("open", []))

    # Second run with same tamper must NOT add a second notification.
    _ = run_watchdog(repo)
    n_notified, _ = notify_count(repo)
    once = incident_raised  # one open soul incident, not duplicated

    record("S1 soul-tamper detected", incident_raised, str(first.get("open")))
    record("S1 alert-once (no duplicate incident)", once and n_notified <= 1,
           f"notified={n_notified}")
    shutil.rmtree(repo.parent, ignore_errors=True)


def scenario_2_skills_drift():
    repo = sandbox()
    dc = repo / "skills" / "dream-cycle"
    moved = repo / "skills" / "dream-cycle-MOVED"
    dc.rename(moved)

    first = run_watchdog(repo)
    drift_detected = "skills:dream-cycle" in first.get("open", [])
    n1, _ = notify_count(repo)

    second = run_watchdog(repo)
    n2, _ = notify_count(repo)
    alert_once = drift_detected and n1 == 1 and n2 == 1

    # Restore the path; incident must resolve.
    moved.rename(dc)
    third = run_watchdog(repo)
    resolved = "skills:dream-cycle" not in third.get("open", []) and \
        third.get("status") == "ok"

    record("S2 skills-drift detected", drift_detected, str(first.get("open")))
    record("S2 alert exactly once across runs", alert_once, f"n1={n1} n2={n2}")
    record("S2 incident resolves after repair", resolved, str(third.get("open")))
    shutil.rmtree(repo.parent, ignore_errors=True)


def load_dream_module(repo):
    path = repo / "skills" / "dream-cycle" / "handler.py"
    spec = importlib.util.spec_from_file_location("dream_cycle_handler", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def scenario_3_regressing_candidate():
    repo = sandbox()
    mod = load_dream_module(repo)

    # Capture the pre-tamper soul seal to prove invariants are untouched.
    soul_before = (repo / "SOUL.md").read_text()

    # Force shadow_test to report a REGRESSION (negative delta).
    mod.shadow_test = lambda c: {"delta": -0.5}
    state = {"runs": [], "last_known_good": "baseline-v0"}
    bad = {"id": "cand-bad", "risk": "high"}

    mod.gate_and_apply([bad], state)

    not_promoted = state["last_known_good"] == "baseline-v0"
    soul_after = (repo / "SOUL.md").read_text()
    invariants_intact = soul_before == soul_after

    record("S3 regressing candidate discarded (LKG unchanged)",
           not_promoted, f"lkg={state['last_known_good']}")
    record("S3 invariants untouched by candidate", invariants_intact)
    shutil.rmtree(repo.parent, ignore_errors=True)


def main():
    print("Eidolon adversarial tests — sandboxed, live repo untouched\n")
    scenario_1_soul_tamper()
    scenario_2_skills_drift()
    scenario_3_regressing_candidate()

    passed = sum(1 for _, p, _ in RESULTS if p)
    total = len(RESULTS)
    print(f"\n{passed}/{total} checks passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
