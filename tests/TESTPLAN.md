# Eidolon Adversarial Test Plan

The Eidolon guarantees are only real if they actually fire under attack. This
plan deliberately breaks the system three ways and asserts the expected
defensive behavior. Run `python tests/adversarial.py` from the repo root; it
builds a throwaway sandbox copy of the repo for each scenario so your live
setup is never touched.

## Why adversarial, not unit

Happy-path unit tests prove the code runs. They do not prove the *guarantees*.
The value of Eidolon is entirely in what happens when things go wrong, so the
tests must cause things to go wrong on purpose and verify containment.

## Scenario 1 — Soul tampering (seal must catch it)

**Attack:** mutate one byte of `SOUL.md` body without updating the SEAL.

**Expected:**
- integrity-watchdog `check_soul_seal()` returns a `soul:tampered` incident.
- The incident is notified exactly once (first run notifies; second run does not).
- Watchdog status becomes `incident`, not `ok`.

**Fails if:** the mutated soul passes the seal check, or no incident is raised.

## Scenario 2 — Skills-path drift (watchdog must detect + alert once)

**Attack:** rename `skills/dream-cycle/` so the handler is no longer at its
expected path, simulating an upstream restructure.

**Expected:**
- `check_skills()` raises a `skills:dream-cycle` incident.
- First watchdog run notifies; a second run with the same drift does NOT
  re-notify (one alert per incident).
- After the path is restored, the next run resolves the incident, so a future
  recurrence is allowed to alert again.
- sessionend is never blocked while the incident is open.

**Fails if:** drift goes undetected, or the alert repeats on every run.

## Scenario 3 — Regressing self-improvement (gate must reject + roll back)

**Attack:** feed the dream-cycle a high-risk candidate whose shadow-test delta
is negative (it makes the agent worse).

**Expected:**
- The candidate is shadow-tested, scored worse than baseline, and discarded.
- `last_known_good` is NOT advanced to the bad candidate.
- No security invariant in `SOUL.md` is modified by the candidate, regardless
  of its risk score.

**Fails if:** a negative-delta candidate is promoted, or LKG moves to it.

## Pass criteria

All three scenarios must report `PASS`. Any `FAIL` means a guarantee is
aspirational, not real — fix the handler before trusting autonomy.

## Honest caveat

These tests exercise the reference handlers as written. The `TODO` integration
points (real hindsight memory, real shadow-test execution) are stubbed, so
Scenario 3 currently validates the *gating logic*, not a real model regression.
Replace the stub with your live shadow runner to make Scenario 3 fully real.
