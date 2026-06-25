# Eidolon Adversarial Test Plan

The Eidolon guarantees are only real if they actually fire under attack. This plan deliberately breaks the system three ways and asserts the expected defensive behavior. Run `python tests/adversarial.py` from the repo root; it builds a throwaway sandbox copy of the repo for each scenario so your live setup is never touched.

## Why adversarial, not unit

Happy-path unit tests prove the code runs. They do not prove the *guarantees*. The value of Eidolon is entirely in what happens when things go wrong, so the tests must cause things to go wrong on purpose and verify containment.

## Scenario 1 — Clean repo (no false positives)

**Attack:** none — run the watchdog against an untouched sandbox copy, twice.

**Expected:**
- `run_checks()` finds nothing; watchdog status is `ok` with an empty `open` list.
- Zero notifications are delivered across both runs (no phantom incidents).

**Fails if:** the watchdog reports an incident on a healthy repo, or delivers any alert.

## Scenario 2 — Skills-path drift (watchdog must detect + alert once)

**Attack:** rename `skills/dream-cycle/` so the handler is no longer at its expected path, simulating an upstream restructure.

**Expected:**
- `check_skills()` raises a `skills:dream-cycle` incident; first run notifies, subsequent runs with the same drift do not re-notify; restoration resolves the incident; `sessionend` is never blocked while the incident is open.

**Fails if:** drift goes undetected, or the alert repeats on every run.

## Scenario 3 — Regressing self-improvement (gate must reject + roll back)

**Attack:** feed the dream-cycle a high-risk candidate whose shadow-test delta is negative (it makes the agent worse).

**Expected:**
- The candidate is shadow-tested, scored worse than baseline, and discarded; `last_known_good` is NOT advanced; no security invariant in `SOUL.md` is modified.

**Fails if:** a negative-delta candidate is promoted, or LKG moves to it.
