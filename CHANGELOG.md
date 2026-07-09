# Changelog

All notable changes to this project are documented in this file.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Added — REC-017: Shadow evaluation for skill promotion/demotion

- `src/eidolon/skills/shadow.py` — `ShadowEvaluator` scores a candidate arm
  against the regression fixture set (in-process, stdlib-only, no network).
  Returns `ShadowResult(status, score, reason, arm_id, threshold)`.
  `MEDIUM`-risk proposals must pass shadow evaluation before any application.
- `src/eidolon/skills/lifecycle.py` — `promote` / `demote` / `retire` state
  machine.  `check_promotion_criteria` enforces `min_shadow_sessions`,
  `min_bandit_posterior`, and `regression_suite_pass_rate` from `manifest.yml`.
  **Adversarial invariant**: a skill that regresses on the eval suite cannot
  be promoted even with a high bandit posterior.
- `src/eidolon/checks/shadow_eval_ready.py` — doctor check; registered in
  `checks/__init__.py`.
- `tests/unit/test_shadow_eval.py` — 14 unit tests covering PASS, FAIL,
  DEGRADED, boundary, adversarial, manifest parsing, and risk-class gating.

### Changed

- `src/eidolon/checks/__init__.py` — `shadow_eval_ready` check appended to
  `registry()`.  Doctor now reports 13 checks on a fully wired host.

<!-- Previous releases will appear here as PRs are merged and tagged. -->
