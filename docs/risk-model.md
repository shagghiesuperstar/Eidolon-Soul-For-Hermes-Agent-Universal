# Eidolon Risk Model (REC-010)

Eidolon classifies every self-modification proposal into one of five ordinal
buckets. The class determines whether the proposal auto-applies, defers to
shadow evaluation, or is refused with an audit trail.

The classifier is defined in `src/eidolon/safety/risk.py`. It is a **pure**
function: no I/O, no time, no randomness. Any impurity is a bug.

---

## The five classes

Ordering (safest → most dangerous):

```
NO_OP  <  LOW  <  MEDIUM  <  HIGH  <  NEVER_TOUCH
```

### `NO_OP` — formal no-op
Action is a no-op by construction. Safe to skip.

**Examples**
- `{"mutation_kind": "no_op", ...}`
- `{"mutation_kind": "identity", ...}`
- Empty `mutation_kind`.

**dream-cycle behaviour**: skipped, logged as `skip`. No side effects.

### `LOW` — safe to auto-apply
Cosmetic, documentation, tests, or comments. No behavioural change.

**Examples**
- `{"mutation_kind": "docs_only", "target": "README.md"}`
- `{"mutation_kind": "typo_fix", "target": "src/eidolon/cli.py"}`
- `{"mutation_kind": "test_only", "target": "tests/unit/test_new.py"}`
- `{"mutation_kind": "comment_only", "target": "src/eidolon/commands/report.py"}`

**dream-cycle behaviour**: auto-applied. Emits `dream.apply` PASS event.

### `MEDIUM` — deferred to shadow eval
Behavioural but reversible. Requires shadow evaluation (REC-017).

Until REC-017 lands, MEDIUM proposals emit `dream.defer` at DEGRADED
status and are NOT applied. Loud, not silent.

**Examples**
- `{"mutation_kind": "prompt_phrasing", "target": "skills/dream-cycle/prompts/reflect.txt"}`
- `{"mutation_kind": "log_verbosity", "target": "src/eidolon/util/events.py"}`
- `{"mutation_kind": "config_field_add", "target": "config.yaml.example"}`

**dream-cycle behaviour**: logged as `defer`, emits DEGRADED event. Waiting on REC-017.

### `HIGH` — never auto-applied
Behavioural, potentially irreversible. Requires operator sign-off.

**Examples**
- `{"mutation_kind": "skill_code", "target": "skills/dream-cycle/handler.py"}`
- `{"mutation_kind": "config_field_rewrite", "target": "config.yaml.example"}`
- `{"mutation_kind": "handler_signature", "target": "src/eidolon/checks/hermes_config.py"}`
- Unknown / unrecognised `mutation_kind` (**fail-closed default**).

**dream-cycle behaviour**: audit-logged, emits `dream.refuse` FAIL event.

### `NEVER_TOUCH` — the ceiling
Target matches any pattern in `NEVER_TOUCH_PATHS`. Overrides every other
signal — a `NO_OP` mutation on `SOUL.md` is still `NEVER_TOUCH`.

**Patterns (§ 0.3)**
- `SOUL.md` at any depth
- `LICENSE`, `NOTICE` and any variants
- `.hermes/config.yaml` (host Hermes config)
- `config.yaml` (local)
- `last_known_good/` tree
- `.github/workflows/adversarial.yml` (guarantees CI)
- `adversarial.yml` (bare)

**dream-cycle behaviour**: audit-logged, emits `dream.refuse` FAIL event with `risk="NEVER_TOUCH"`.

---

## Editing rules

- **Adding** a `NEVER_TOUCH_PATHS` entry is a one-line change in `risk.py`. **No REC required.**
- **Removing** a `NEVER_TOUCH_PATHS` entry is a **safety loosening**. **REC required.** The removal REC must state:
  1. What target is being un-protected.
  2. What alternative safeguard replaces it.
  3. Which adversarial test proves the alternative works.

## Purity contract

The classifier and all helpers in `safety/risk.py` and `safety/classifier.py`
are pure. If you find yourself importing `os`, `time`, `random`, or the
filesystem, stop — you're building the wrong thing.

Unit test `test_classifier_is_pure` monkey-patches `time.time`, `random`,
and `os.environ` and calls `classify` 100× with the same input; the
result must be bit-identical across every call.

## Doctor check

`eidolon doctor` runs `risk_classifier_ready`:

- PASS: 5 enum members + non-empty `NEVER_TOUCH_PATHS`.
- FAIL: enum has fewer than 5 members (semantic drift).
- FAIL: import error (module removed or renamed).
- DEGRADED: `NEVER_TOUCH_PATHS` is empty (someone commented out the ceiling).
