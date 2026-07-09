# Skill Lifecycle: Shadow Evaluation, Promotion, and Retirement

Eidolon manages the lifecycle of self-improvement proposals through a
three-state machine: **shadow → active → retired**.
This page covers how the states work, how to read a skill's manifest, and
how promotion and demotion decisions are enforced.

---

## States

| State | Meaning |
|---|---|
| `shadow` | Skill is under evaluation. It collects bandit sessions and regression scores but is NOT applied to live agent behavior. |
| `active` | All promotion criteria were met and the skill is applied to live sessions. |
| `retired` | Skill was explicitly retired (operator action or demotion after repeated regression). It is never auto-applied. |

### Transitions

```
shadow  ──promote──►  active
                        │
                     demote
                        │
                        ▼
                      shadow
active  ──retire──►  retired
shadow  ──retire──►  retired
```

Promotion is **never automatic** — it is a deliberate CLI action after all
criteria are verified. Demotion from active back to shadow is triggered when
the bandit posterior drops below the manifest threshold (the dream cycle
detects this and proposes demotion; operator confirms via CLI).

---

## Shadow Evaluation

Before a MEDIUM-risk proposal can be promoted, `ShadowEvaluator` scores the
candidate arm against the regression fixture set.

### How it works

1. The evaluator reads all `*.jsonl` files under the fixtures directory
   (`$EIDOLON_HOME/fixtures/` by default, overridable with `--fixtures`).
2. It computes a **weighted regression pass rate** for the candidate arm:
   `score = Σ(weight * hit) / Σ(weight)` where `hit = 1` if the arm is the
   fixture's `expected_winner`.
3. If `score ≥ threshold` (default **0.80**), the result is `PASS`.
   If `score < threshold`, the result is `FAIL` — the proposal is blocked.
4. If the fixtures directory is missing or empty, the result is `DEGRADED`
   (loud — the evaluator never silently no-ops).

### Adversarial invariant

> **A skill that regresses on the eval suite MUST NOT be promoted even if its
> bandit posterior is very high.**

This is enforced structurally: `check_promotion_criteria` checks
`regression_pass_rate` independently of `bandit_posterior`. Both must clear
their thresholds. There is no override flag.

### Exit codes from shadow eval (as surfaced by `eidolon skill promote`)

| Result | Meaning | CLI exit |
|---|---|---|
| `PASS` | Score ≥ threshold; ready to promote | `0` |
| `FAIL` | Score < threshold; blocked | `1` |
| `DEGRADED` | Fixtures missing/empty; cannot evaluate | `2` |

---

## The `manifest.yml` Schema

Every skill directory must contain a `manifest.yml` that declares promotion
criteria. Example:

```yaml
name: my-skill
version: 1.0.0
promotion:
  min_shadow_sessions: 20
  min_bandit_posterior: 0.65
  regression_suite_pass_rate: 0.95
```

| Field | Type | Default | Meaning |
|---|---|---|---|
| `name` | string | required | Unique skill identifier |
| `version` | string | required | SemVer tag for this skill |
| `promotion.min_shadow_sessions` | int | `20` | Minimum completed shadow sessions before promotion is allowed |
| `promotion.min_bandit_posterior` | float | `0.65` | Minimum bandit posterior mean the arm must hold |
| `promotion.regression_suite_pass_rate` | float | `0.95` | Minimum weighted regression pass rate from shadow eval |

All three promotion criteria must be met simultaneously. Failing any one blocks
promotion regardless of the other two.

---

## CLI Reference

```
eidolon skill status <name>          # print current state + last eval score
eidolon skill promote <name>         # run shadow eval + criteria check; exit 0 on PASS
eidolon skill promote <name> --manifest <path>   # explicit manifest.yml location
eidolon skill promote <name> --fixtures <path>   # explicit fixtures dir
eidolon skill demote <name>          # move active → shadow; exit 0
eidolon skill retire <name>          # move any state → retired; exit 0
eidolon skill promote <name> --json  # machine-readable output
```

All subcommands exit `0` (PASS), `1` (FAIL / blocked), or `2` (DEGRADED).
They never silently succeed when a criterion is unmet.

### Skill state store

State is persisted in `<eidolon_state_dir>/skill-state.json` — a flat JSON
mapping of skill name to current state token. The file is readable and
editable by operators in an emergency, but normal mutations go through the
CLI. The `eidolon_state_dir` is `$EIDOLON_HOME` if set, else
`$HERMES_HOME/state/eidolon`, else `~/.hermes/state/eidolon`.

---

## Doctor Check

The `shadow_eval_ready` doctor check verifies that `ShadowEvaluator` is
importable and instantiates cleanly at the default threshold:

```
eidolon doctor
...
[PASS] shadow_eval_ready  ShadowEvaluator ready; default threshold=0.8
```

If this check shows `FAIL`, shadow eval is broken and `eidolon skill promote`
will exit `2` (DEGRADED). Fix the import error before promoting any skill.

---

## Operator FAQ

**Q: My skill has a high bandit score but keeps failing shadow eval.**
A: The regression fixture set is the ground truth. Add or fix fixtures so they
correctly label your skill as the expected winner for the cases it handles.
Do not lower the `regression_suite_pass_rate` threshold as a workaround —
that weakens the adversarial invariant.

**Q: Can I skip shadow eval for a LOW-risk skill?**
A: Yes. LOW-risk changes are auto-applyable (`RiskClass.LOW.is_auto_applyable()
== True`) and skip the shadow gate entirely.

**Q: Can I promote a skill from a CI script?**
A: `eidolon skill promote <name>` exits non-zero on any unmet criterion,
making it safe to run in CI. Pipe `--json` output to your pipeline's
artifact store for auditability.

**Q: Where are the regression fixtures stored?**
A: Default: `$EIDOLON_HOME/fixtures/` (typically
`~/.hermes/state/eidolon/fixtures/`). Override with `--fixtures <path>`
or the `EIDOLON_FIXTURES_DIR` environment variable.

**Q: How do I check what state all my skills are in?**
A: Read `<eidolon_state_dir>/skill-state.json` directly, or run
`eidolon skill status <name>` (or `--json`) for each skill. A `skill list`
command is planned for a follow-up release.
