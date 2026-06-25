# Skill: dream-cycle

Autonomous reflection, reinforcement, and risk-gated self-improvement for an
Eidolon-equipped Hermes agent. Runs on sessionend (light) and on cron (deep).
Never blocks a live session; never requires approval for low-risk work.

## Modes

- `--mode sessionend` : light pass. Capture the just-finished session's outcomes
  to hindsight memory, extract obvious lessons, queue heavier analysis.
- `--mode scheduled`  : deep pass. Mine recent memory, score policies, propose
  improvements, gate by risk, apply or shadow-test, roll back regressions.

## Pipeline

1. **Ingest** — pull recent episodes (expected vs actual, errors, operator edits).
2. **Reflect** — cluster episodes, find recurring failure/success patterns.
3. **Extract** — write versioned lessons to hindsight memory (append-mostly).
4. **Propose** — generate candidate changes (prompt, heuristics, tool use).
5. **Gate** — classify each candidate Low / High risk (see SOUL.md §3).
6. **Apply / Shadow** — Low: apply now. High: run in sandbox vs baseline.
7. **Score & Promote** — promote only on measured improvement; else discard.
8. **Rollback** — if a promoted change regresses next cycle, revert to LKG.
9. **Watch** — invoke integrity-watchdog before exit.

## Guarantees

- Security invariants (SOUL.md §2) are never modified by any candidate.
- All experiments are logged with outcome; rollbacks record their reason.
- Failures are reported plainly; nothing is fabricated or hidden.

## Outputs

- Hindsight memory: new/updated lessons.
- `state/dream-cycle.json`: last run, applied changes, rollbacks, scores.
- Log line per phase for operator verification.
