# Grok Build Session Brief — v2.0 Vertical Slice

## Working branch
feat/v2.0-vertical-slice

## PR #44 status
CHECK FIRST: git log --oneline main | grep "Judgment Brain"
If not merged: inspect CI on branch v2.0-judgment-brain, fix if red, merge.
Everything below depends on judgment/ being on main.

## The ONE law of done
DONE = a real Hermes playbook file changes on disk AND the lesson
leaves the soft inbox AND proposals_applied increments AND the
scoreboard (X/Y/Z/W) prints from eidolon report --json.
Eidolon-only ledger writes without a Hermes file change = NOT DONE.

## What is real on main — do not re-implement
- skills/dream-cycle/handler.py     apply_low() writes MEMORY.md — READ IT
- src/eidolon/hermes_bridge.py      promote_lesson_to_hermes() is real
- src/eidolon/judgment/             classifier, executor, metrics (post PR#44)
- src/eidolon/memory/               MemoryAdapter ABC + HindsightAdapter + InMemAdapter
- src/eidolon/outbox.py             transactional outbox, crash-safe

## The gap you are closing (and ONLY this)
apply_low() does NOT:
  a) write a skill update to HERMES_HOME/skills/_eidolon_staging/
  b) mark lessons done in the adapter (no mark_done() method exists yet)
  c) increment proposals_applied in judgment/metrics.py
  d) surface X/Y/Z/W in eidolon report --json

## Exact deliverables (4, in order)
D1: executor.py — SKILL_UPDATE branch writes staging .md file
D2: MemoryAdapter.mark_done() — HindsightAdapter + InMemAdapter impls
D3: metrics.increment("proposals_applied") called from apply_low()
D4: eidolon report --json emits lessons_extracted, proposals_applied,
    skills_staged, inbox_cleared as integers

## Key constraints
- Staging dir only: HERMES_HOME/skills/_eidolon_staging/ — never live skills/
- Never touch SOUL.md, sanitize_check.py, tests/adversarial.py
- Stdlib only, zero new pip deps
- scripts/sanitize_check.py must pass (zero PII — no local paths or names)
- venv: ~/.hermes/vendor/eidolon-venv

## Test file
tests/unit/test_vertical_slice.py — 4 tests, must FAIL before impl, PASS after

## Relevant RECs in master_EIDOLON_roadmap(F5).md
REC-003, REC-010, REC-020, REC-021
