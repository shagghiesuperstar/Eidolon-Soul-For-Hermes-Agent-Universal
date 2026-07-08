# Eidolon — Universal Self-Improvement Layer for Hermes Agents

[![adversarial](https://github.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal/actions/workflows/adversarial.yml/badge.svg)](https://github.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal/actions/workflows/adversarial.yml)

Eidolon is a drop-in layer that hardens a Hermes agent's native dream, reflection, and memory loops into a disciplined, anti-fragile, self-improving system. Zero human babysitting: it runs autonomously, improves itself every session and on a schedule, and refuses to guess or gaslight. Deploy once and forget it.

## What it does

- **Clear SOUL.md contract** — a plain, zero-guess identity and operating contract the agent loads every session. No manual sealing or hashing to maintain.
- **Risk-gated self-improvement** — low-risk fixes auto-apply; high-risk changes are shadow-tested first; regressions auto-roll-back.
- **Dream cycle** — autonomous post-session and scheduled reflection that mines hindsight memory, extracts lessons, and proposes improvements.
- **Integrity watchdog** — detects when upstream Hermes changes (skills paths, hooks, cron) break your setup and alerts the operator **once** per incident, without blocking sessions.

## Principles

1. **No guessing.** If a fact is unknown, the agent says so and verifies before acting.
2. **No gaslighting.** It never rewrites history or denies prior state.
3. **Anti-fragile.** Drift and breakage make the system stronger, not silent.
4. **Autonomous.** Self-improvement requires zero approvals and zero reminders.
5. **Immutable safety.** Security invariants are never modified by self-improvement.

## Layout
```
SOUL.md                     Identity + operating contract (plain, no seal)
OPERATOR.md                 Human-facing setup + control guide
skills/dream-cycle/         Autonomous reflection + RL loop
skills/integrity-watchdog/  Drift detection + one-time alerting
tests/                      Adversarial harness + test plan
```

## The `eidolon` CLI

Eidolon ships a canonical command that never silently no-ops. Every subcommand
returns `0` on PASS, `2` on DEGRADED (loud reduced mode), and `1` on FAIL.

```
eidolon doctor              # preflight checks (JSON via --json, --model-check)
eidolon report --since 24h  # measurable deltas: sessions, lessons, proposals, rollbacks
eidolon rollback --dry-run  # restore from last-known-good snapshot
eidolon version             # print semver
```

Every Eidolon component emits structured events into `$EIDOLON_HOME/events.jsonl`
(default: `~/.hermes/state/eidolon/events.jsonl`). `eidolon report` reads that
log and prints integers you can plot. Empty state prints zeros with a first-run
banner — never `null`, never `N/A`.

## Install

```
pip install eidolon-hermes
```

Or drop the `skills/` directory into your Hermes skills path and point your
sessionend hook + cron at the dream-cycle and integrity-watchdog handlers.
See `OPERATOR.md` for details.

Verify the guarantees anytime with `python tests/adversarial.py` or
`PYTHONPATH=src python -m unittest discover -s tests/unit -v`.

## License

Apache License 2.0.
