# Eidolon — Universal Self-Improvement Layer for Hermes Agents

Eidolon is a drop-in layer that hardens a Hermes agent's native dream, reflection, and memory loops into a disciplined, anti-fragile, self-improving system. Zero human babysitting: it runs autonomously, improves itself every session and on a schedule, and refuses to guess or gaslight.

## What it does

- **Quine-sealed SOUL.md** — a self-verifying, zero-guess identity and operating contract. If the soul is tampered with, the agent knows.
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
SOUL.md                      Quine-sealed identity + operating contract
OPERATOR.md                  Human-facing setup + control guide
skills/dream-cycle/          Autonomous reflection + RL loop
skills/integrity-watchdog/   Drift detection + one-time alerting
```

## Install

Drop the `skills/` directory into your Hermes skills path and point your sessionend hook + cron at the dream-cycle and integrity-watchdog handlers. See `OPERATOR.md` for details.

## License

Apache License 2.0.
