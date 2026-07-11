# Changelog

All notable changes to Eidolon are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning: [SemVer](https://semver.org/).

---

## [Unreleased]

### Added
- **Hermes memory bridge (`eidolon.hermes_bridge`):** LOW applies promote real
  lesson text into `$HERMES_HOME/memories/MEMORY.md` (what Hermes injects every
  session). Template "Improve handling of…" proposals are skipped. Dedup +
  bounded section. Private ledger retained for audit only.

### Fixed
- **Hermes-native provider cache:** infer json_mode + 128k context from non-empty models lists so doctor provider_capability PASSes on real hosts.

### Fixed
- **Proposal auto-apply path:** `mutation_kind=preference_update` is now RiskClass.LOW
  (was fail-closed HIGH). `apply_low` writes `applied_proposals.jsonl` + `applied_lessons.md`
  under `$EIDOLON_HOME` so applies are measurable (never touches SOUL/config).

### Added
- **Outbox wiring in dream write path — REC-021:** `extract_lessons()` and
  `propose()` now buffer entries through `Outbox.capture()` before calling
  `Outbox.flush(adapter)` once per function.  A crash mid-write no longer
  loses entries; un-flushed entries in `$EIDOLON_HOME/outbox/pending.jsonl`
  replay automatically on the next dream cycle.  When the eidolon package is
  not importable the functions degrade to direct `adapter.store()` calls
  (same degrade path as REC-020).
- **`tests/unit/test_dream_outbox_wiring.py` (REC-021):** 4 unit tests
  verifying: lessons land in adapter via outbox, lessons returned even on
  flush failure, proposals land in adapter via outbox, and flush failure
  leaves entries in `pending.jsonl` for replay.  All FAILED before this
  change, all PASS after.

- **Dream-cycle MemoryAdapter wiring — REC-020:** All four TODO stubs in
  `skills/dream-cycle/handler.py` are now wired to the `MemoryAdapter`:
  - `ingest()` calls `adapter.retrieve(kind=..., limit=200, since_ts=<7d>)` for
    each of `lesson`, `preference`, `reflection`, `episode` and returns the
    merged list.
  - `reflect()` clusters episodes by `kind`, sorts newest-first, and returns
    one `{kind, count, sample}` pattern dict per cluster. Pure function; no IO.
  - `extract_lessons()` synthesises one lesson per pattern and calls
    `adapter.store(kind="lesson", ...)` for each. Store failures emit DEGRADED
    events; the lesson is still returned so the cycle continues.
  - `propose()` generates one candidate proposal per lesson and calls
    `adapter.store(kind="proposal", ...)`. Store failures are DEGRADED events;
    the candidate is still returned for `gate_and_apply`.
  - Adapter is loaded once per process via `_get_adapter()` using
    `eidolon.memory.loader.load_adapter()`. When unavailable, all four
    functions degrade loudly and return their zero-state (empty list).
- **`tests/unit/test_dream_memory_adapter.py` (REC-020):** 9 tests covering
  `ingest` with unavailable adapter, core recall gate (REC-020 critical path),
  reflect clustering, reflect sample ordering, `extract_lessons` write-path,
  `extract_lessons` store-fail degrade, `propose` write-path, and `propose`
  store-fail degrade.

- **Transactional outbox — `src/eidolon/outbox.py` (REC-019):** Crash-safe
  capture + idempotent flush layer between the dream cycle and any
  `MemoryAdapter` backend.  `Outbox.capture` appends to
  `$EIDOLON_HOME/outbox/pending.jsonl` (atomic line-append; each entry
  carries a 16-hex `_eid` for idempotency).  `Outbox.flush(adapter)` drains
  the pending file into the adapter exactly once, rewrites the file
  atomically via `os.replace`, and returns a `FlushResult(flushed, skipped,
  failed)`.  A crash mid-flush replays cleanly on next cycle; duplicate
  entries (adapter raises `"duplicate"` / `"exists"`) are skipped, not
  failed.  Stdlib-only; no new dependencies.
- **`tests/unit/test_outbox.py` (REC-019):** 10 unit tests covering capture,
  missing-field validation, pending count, flush-exactly-once, backend
  failure retention, duplicate-skip, and partial-failure isolation.  All
  FAILED before this commit, all PASS after.

### Fixed
- **P0 — Learning loop write-only bug (PR #31):** `ThompsonBandit` always
  started with uniform priors. `replay.jsonl` was append-only; posteriors were
  never hydrated on startup. Added `hydrate_bandit(bandit, records)` pure
  function to `replay.py` and wired it into `commands/learn.py` immediately
  after bandit init. `replay_hydrated` and `replay_orphaned` counts now
  surface in the `learn.step` event and JSON stdout. Root cause of canary
  symptom: 139 dream runs, zero durable learning.
- **`CITATION.cff` sentinel restore:** `version` and `date-released` restored
  to `OPERATOR_INPUT_REQUIRED_ON_RELEASE_TAG` so `bump-citation` CI job owns
  these fields at tag-push time. Fixes `test_placeholders_present`.

### Added (prior)
- **`tests/unit/test_replay_hydration.py` (PR #31):** 2 new tests proving
  posteriors survive session boundaries. Both FAILED before the fix, PASS after.
- **Shadow eval infrastructure (PR #25 / REC-017):** `src/eidolon/skills/`
  package: `ShadowEvaluator`, `ShadowResult`, and the `shadow` / `active` /
  `retired` lifecycle state machine (`lifecycle.py`). A MEDIUM-risk skill
  proposal must pass shadow eval before it can be promoted; a regressing skill
  is blocked even at high bandit posterior (adversarial invariant tested in
  `tests/unit/test_shadow_eval.py`).
- **REC-017** `src/eidolon/checks/shadow_eval_ready.py`: new doctor check
  verifying `ShadowEvaluator` imports and instantiates cleanly. Doctor now
  reports 13 checks.
- **REC-017** `docs/skill-lifecycle.md`: operator reference for shadow eval,
  promotion criteria, manifest schema, and state transitions.
- 14 new unit tests in `tests/unit/test_shadow_eval.py`.
- **`ACKNOWLEDGMENTS.md` (PR #27):** Canonical intellectual lineage.
- **`PHILOSOPHY.md` (PR #28):** Origins, Quine Principle, Five Principles
  failure-mode provenance, Measurable-Improvement Thesis, §13 non-goals mirror.
- **`README.md` Philosophy & Lineage paragraph (PR #30):** Links
  `PHILOSOPHY.md` and `ACKNOWLEDGMENTS.md`.

### Changed
- **`docs/compatibility.md` + `README.md` (PR #29):** Windows row set to FAIL
  across all Python columns; explicit WSL2-only paragraph added.

---

## [1.0.0] — 2026-07-01

### Added
- `eidolon` CLI with subcommands: `doctor`, `verify`, `report`, `rollback`,
  `version`, `learn`, `mcp serve`.
- `src/eidolon/checks/` framework: 12 preflight checks covering soul contract,
  Hermes config/version, Python version, hooks, provider capability, bandit
  readiness, preference schema, risk classifier, PII patterns, and state dir.
- `src/eidolon/learning/`: `EpsilonGreedyBandit`, `RegressionReward`,
  `load_fixtures`, `ReplayBuffer`, preference learning, and `LearningSchemas`.
- `src/eidolon/safety/`: `RiskClass` enum (LOW / MEDIUM / HIGH / NEVER_TOUCH)
  with `is_auto_applyable()` enforcement.
- `src/eidolon/inference/`: provider capability tier detection.
- `src/eidolon/reporting/`: event ledger reader powering `eidolon report`.
- `src/eidolon/mcp/`: stdlib-only JSON-RPC MCP server (`eidolon mcp serve`).
- `scripts/sanitize_check.py` + `.sanitize-patterns.yml`: CI PII gate; pre-commit
  hook via `.githooks/pre-commit`.
- `tests/adversarial.py`: S1–S3 safety guarantees (no silent no-op, risk gating,
  rollback integrity).
- `install.sh`: one-liner installer with doctor gate and env-var overrides.
- `SOUL.md`, `OPERATOR.md`, `RELEASING.md`: identity contract, operator guide,
  release policy.
- Zenodo DOI metadata (`.zenodo.json`), `CITATION.cff`, `docs/citing.md`.
- CI workflows: `adversarial.yml`, `installer-test.yml`, `release.yml`.
- Homebrew tap formula (`packaging/homebrew/eidolon.rb`).
- `docs/`: `compatibility.md`, `eval.md`, `install-brew.md`, `mcp.md`,
  `risk-model.md`.

[Unreleased]: https://github.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal/releases/tag/v1.0.0
