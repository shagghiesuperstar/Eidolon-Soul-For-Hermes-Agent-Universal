# Judgment Brain — Operator Reference

> v2.0 — The missing arrow. Eidolon v1 wrote lessons into MEMORY.md and stopped.
> The Judgment Brain classifies each lesson and executes a real action against
> the files Hermes Agent loads every session.

## What it does

Every time `promote_lesson_to_hermes()` successfully writes a lesson, the
Judgment Brain immediately:

1. **Classifies** the lesson into one of five `ActionKind` values
2. **Executes** the corresponding file write
3. **Records** the event to `judgment_metrics.jsonl` for `eidolon report`

## SOUL.md compatibility — zero config required

This works universally across all Hermes Agent installs:

- **Existing SOUL.md** — the `EIDOLON EDICTS` marker is appended at the end of
  whatever content already exists. Every line above the marker is untouched.
- **No SOUL.md** — the file is created with just the marker + first edict.
- **SOUL.md with existing EIDOLON EDICTS section** — new edicts are appended
  below the existing ones. Duplicates are skipped (idempotent).

No migration step. No install config. Works on first dream cycle.

## Action kinds

| ActionKind | Hermes file written | Human meaning |
|---|---|---|
| `SOUL_EDICT` | `$HERMES_HOME/SOUL.md` (EIDOLON EDICTS section) | Universal behavioural rule; Hermes always sees it |
| `SKILL_UPDATE` | `$HERMES_HOME/skills/eidolon-learned.md` | Repeatable workflow pattern; Hermes loads at session start |
| `CONFIG_TUNE` | `$HERMES_HOME/memories/eidolon-prefs.md` | Formatting/style preference; Hermes injects from memories/ |
| `MEMORY_RETIRE` | Removes line from `MEMORY.md` | Lesson is baked in elsewhere; MEMORY.md line is now noise |
| `MEMORY_RETAIN` | No-op | Lesson not yet actionable; stays in MEMORY.md |

## Classification rules

Classification is rule-based (no LLM call, no external dependency). Priority:

1. Retire signals win first (`codified`, `baked in`, `verified in`…)
2. Soul signals (`never`, `always`, `must not`, `invariant`…)
3. Skill signals (`probe before`, `run the real command`, `workflow`…)
4. Config signals (`format`, `prefer`, `output style`…)
5. Default: MEMORY_RETAIN

See `src/eidolon/judgment/classifier.py` for the full signal lists.

## Measurable output

Run `eidolon report` to see:

```
lessons_judged   — total classify calls
skills_modified  — SKILL_UPDATE status=ok
soul_edicts      — SOUL_EDICT status=ok
config_changes   — CONFIG_TUNE status=ok
memory_retired   — MEMORY_RETIRE status=ok (lines cleaned from MEMORY.md)
skipped          — duplicates / no-ops
failed           — any execution error
```

Metrics are persisted in `$EIDOLON_HOME/judgment_metrics.jsonl`.

## Safety

- SOUL.md invariants above the `EIDOLON EDICTS` marker are **never touched**.
- All writes are atomic (`write-tmp` + `os.replace`).
- Judgment Brain failure never crashes the MEMORY.md write path (degrades loudly via result dict).
- `MEMORY_RETAIN` is always a safe no-op.
- Works identically regardless of which Hermes memory plugin is active.

## Human proof test

After running one dream cycle with a lesson like
`"Never invent terminal output — always run the real command"`:

1. Open `$HERMES_HOME/SOUL.md` — look for `EIDOLON EDICTS` section
2. Start a **new** Hermes session
3. Ask: *"What rule do you follow about terminal output?"*
4. If Hermes states the rule from memory — **the arrow is real**

That is the only proof that matters.
