# OPERATOR — Eidolon Setup & Control Guide

This is the only file you need to read as a human. The agent reads `SOUL.md`;
you read this.

## What you get

A Hermes agent that improves itself continuously and autonomously, never asks
you to approve routine self-improvement, never asks you to remember to run
anything, and never guesses or gaslights. It alerts you only when something
actually needs you — once per incident.

## Requirements

- A running Hermes agent with a skills directory, a sessionend hook, and cron.
- Hindsight (or compatible) memory available to the agent.
- A notification channel (Telegram, email, or any webhook) for one-time alerts.

## Install

1. Copy `SOUL.md` to your agent's identity/system path so it loads on every session.
2. Copy `skills/dream-cycle/` and `skills/integrity-watchdog/` into your skills dir.
3. Wire the hooks (see below).
4. Set the notification channel via env var `EIDOLON_NOTIFY` (URL or `tg:<chat_id>`).

## Wiring (zero reminders, zero approvals)

**Sessionend hook** — runs after every session, non-blocking:
```
on sessionend -> python skills/dream-cycle/handler.py --mode sessionend
```

**Cron** — deep reflection + drift sweep on a schedule (example: hourly):
```
0 * * * *  python skills/dream-cycle/handler.py --mode scheduled
*/15 * * * * python skills/integrity-watchdog/handler.py
```

The dream cycle also invokes the watchdog each run, so cron for the watchdog is
optional belt-and-suspenders.

## Risk gating (what runs without you)

| Risk | Examples | Behavior |
|------|----------|----------|
| Low  | prompt tweaks, lesson extraction, memory hygiene | Auto-apply |
| High | behavior/tool changes, anything near invariants  | Shadow-test, promote only on measured win |
| Any regression | scored worse than baseline | Auto-rollback to last-known-good |

Security invariants in `SOUL.md` §2 are immutable and are never touched by
self-improvement, regardless of risk score.

## When will it bother you?

Only the integrity watchdog pings you, and only **once per incident**, when:

- The skills path moved or your skills no longer load.
- The sessionend hook or cron entry was removed or rewired by an upstream update.
- The `SOUL.md` seal check fails (possible tampering or corruption).

It does not block your sessions while waiting on you. It records the incident,
attempts a safe self-repair, and resolves the alert when the issue clears.

## Verifying it's alive

- Check the dream-cycle log for periodic `reflect` + `improve` entries.
- Check the watchdog state file for `status: ok` and a recent timestamp.
- Trigger a deliberate drift (rename the skills dir in a test copy) and confirm
  you receive exactly one alert, not a stream.

## Uninstall

Remove the two skills, the hook line, and the cron entries. `SOUL.md` is inert
without the loop; deleting it returns the agent to stock behavior.
