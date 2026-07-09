# Changelog

All notable changes to Eidolon are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning: [SemVer](https://semver.org/).

---

## [Unreleased]

### Added
- **REC-017** `src/eidolon/skills/` package: `ShadowEvaluator`, `ShadowResult`,
  and the `shadow` / `active` / `retired` lifecycle state machine
  (`lifecycle.py`). A MEDIUM-risk skill proposal must pass shadow eval before
  it can be promoted; a regressing skill is blocked even at high bandit
  posterior (adversarial invariant tested in `tests/unit/test_shadow_eval.py`).
- **REC-017** `src/eidolon/checks/shadow_eval_ready.py`: new doctor check
  verifying `ShadowEvaluator` imports and instantiates cleanly. Doctor now
  reports 13 checks.
- **REC-017** `docs/skill-lifecycle.md`: operator reference for shadow eval,
  promotion criteria, manifest schema, and state transitions.
- 14 new unit tests in `tests/unit/test_shadow_eval.py`.

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
