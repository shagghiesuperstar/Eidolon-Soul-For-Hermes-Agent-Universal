# Skill: integrity-watchdog

Detects when the surrounding Hermes environment drifts in a way that breaks
the Eidolon setup, attempts a safe self-repair, and notifies the operator
**exactly once per incident**. Never blocks sessionend. Never spams.

## What it checks

1. **Skills path** — are `dream-cycle` and `integrity-watchdog` present and loadable
   at the expected location? (Upstream updates sometimes move skill dirs.)
2. **Hook wiring** — is the sessionend hook still pointed at the dream-cycle handler?
3. **Cron** — do the expected scheduled entries still exist?
4. **Soul seal** — does `SOUL.md` recompute to its embedded SEAL? A mismatch means
   tampering or corruption.

## Behavior

- Each check produces `ok` or an incident with a stable `incident_key`.
- State is kept in `state/integrity-watchdog.json`. An incident already marked
  `notified` is NOT re-notified — this is how one-time alerting is guaranteed.
- When an incident clears, the alert is resolved and the key is removed, so a
  future recurrence will notify again (one alert per genuine incident).
- Safe self-repair is attempted where it is non-destructive and reversible
  (e.g. re-add a missing cron line). Destructive repairs are never auto-run;
  they are surfaced to the operator instead.

## Notification

Reads `EIDOLON_NOTIFY` (a webhook URL or `tg:<chat_id>`). If unset, incidents
are logged only. Notifications are best-effort and never block the cycle.

## Invariants

- Never blocks or delays sessionend.
- Never sends more than one alert per active incident.
- Never modifies security invariants while "repairing".
