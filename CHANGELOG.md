# Changelog

All notable changes to Eidolon are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning: [SemVer](https://semver.org/).

---

## [Unreleased]

### Added
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
- **`tests/unit/test_dream_memory_adapter.py` (REC-020):** 8 tests covering
  `ingest` with unavailable adapter, core recall gate (REC-020 critical path),
  reflect clustering, reflect sample ordering, `extract_lessons` write-path,
  `extract_lessons` store-fail degrade, `propose` write-path, and `propose`
  store-fail degrade. All FAILED before this commit, all PASS after.

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
  posteriors survive session backwards. Both FAILED before the fix, PASS after.
- **Shadow eval infrastructure (PR #25 / REC-017).**
- **`ACKNOWLEDGMENTS.md` (PR #27).**
- **`PHILOSOPHY.md` (PR #28).**
- **`README.md` Philosophy & Lineage paragraph (PR #30).**

### Changed
- **`docs/compatibility.md` + `README.md` (PR #29):** Windows row set to FAIL;
  WSL2-only paragraph added.

---

## [1.0.0] — 2026-07-01

### Added
- `eidolon` CLI with subcommands: `doctor`, `verify`, `report`, `rollback`,
  `version`, `learn`, `mcp serve`.
- `src/eidolon/checks/` framework: 12 preflight checks.
- `src/eidolon/learning/`: `EpsilonGreedyBandit`, `RegressionReward`,
  `load_fixtures`, `ReplayBuffer`, preference learning, and `LearningSchemas`.
- `src/eidolon/safety/`: `RiskClass` enum with `is_auto_applyable()`.
- `src/eidolon/inference/`: provider capability tier detection.
- `src/eidolon/reporting/`: event ledger reader powering `eidolon report`.
- `src/eidolon/mcp/`: stdlib-only JSON-RPC MCP server.
- `scripts/sanitize_check.py` + `.sanitize-patterns.yml`: CI PII gate.
- `tests/adversarial.py`: S1–S3 safety guarantees.
- `install.sh`, `SOUL.md`, `OPERATOR.md`, `RELEASING.md`.
- Zenodo DOI metadata, `CITATION.cff`, `docs/citing.md`.
- CI workflows: `adversarial.yml`, `installer-test.yml`, `release.yml`.
- Homebrew tap formula.
- `docs/`: `compatibility.md`, `eval.md`, `install-brew.md`, `mcp.md`,
  `risk-model.md`.

[Unreleased]: https://github.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal/releases/tag/v1.0.0
