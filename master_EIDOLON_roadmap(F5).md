# master_EIDOLON_roadmap(F5).md

> **Authored by**: Fable-5 (Perplexity Model Council synthesis, chief-architect stance)
> **Audience**: Autonomous coding agents (any capability tier). Written to be
> executable by inferior-model agents (Haiku, GPT-4o-mini, Gemini Flash class)
> without judgment calls. Every step is a runnable command with an expected
> exit code and expected substring.
> **Repo**: https://github.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal
> **Generated at**: 2026-07-07 (America/Chicago)
> **Roadmap horizon**: 12 months from generation date
> **Contract**: This file overrides every other planning artifact in this repo
> if they disagree. Prior artifacts (`EIDOLON_PERPLEXITY_SUBMIT.md`,
> Appendix B verdicts) remain valid as background context but are not the
> executable plan; **this** file is.

---

## HOW TO USE THIS FILE

You are an autonomous coding agent. You will execute this roadmap REC by REC,
in the order given. You will not skip RECs. You will not reorder RECs unless
a REC explicitly says `MAY_PARALLELIZE_WITH: <REC-ID>`. You will not invent
new RECs; if a need arises that no REC covers, you will stop and ask the
operator.

For every REC, in order:

1. Read the REC's `Do exactly this` block.
2. Execute the commands in the block in the order given.
3. Run the REC's `Verify` block.
4. If every `Pass criterion` is met, commit with the REC's `Commit message`
   template and move to the next REC.
5. If any `Pass criterion` fails, run the REC's `Rollback` block and stop.
   Do not attempt creative fixes. Report the failure to the operator with:
   (a) the REC ID, (b) the exact failing criterion, (c) the last 50 lines of
   stdout/stderr, (d) the git SHA before the attempted change.

**Never** invent files, paths, environment variables, model names, or API
endpoints that are not in this document. If a value is missing, the REC will
say `OPERATOR_INPUT_REQUIRED` and you will stop and ask.

**Never** merge a PR without CI green on all required checks.
Required checks are enumerated in [`§ CI Contract`](#ci-contract).

---

## TABLE OF CONTENTS

- [0. Vocabulary + Invariants](#0-vocabulary--invariants)
- [1. Repo Ground Truth (state at generation time)](#1-repo-ground-truth-state-at-generation-time)
- [2. End State Definition (what "done" means)](#2-end-state-definition-what-done-means)
- [3. Directive Hierarchy (immutable operator rules)](#3-directive-hierarchy-immutable-operator-rules)
- [4. Environment Contract (what agents may assume)](#4-environment-contract-what-agents-may-assume)
- [5. CI Contract (required checks + naming)](#5-ci-contract-required-checks--naming)
- [6. Global Gates (must hold between all RECs)](#6-global-gates-must-hold-between-all-recs)
- [7. Work Already Completed (RECs 001–005 + freshness/licensing)](#7-work-already-completed-recs-001005--freshnesslicensing)
- [8. Critical Path Tier 1 — RECs 006–011](#8-critical-path-tier-1--recs-006011)
- [9. Foundation Tier 2 — RECs 012–016](#9-foundation-tier-2--recs-012016)
- [10. Aspirational Tier 3 — RECs 017–020](#10-aspirational-tier-3--recs-017020)
- [11. Cross-Cutting Concerns (safety, privacy, telemetry)](#11-cross-cutting-concerns-safety-privacy-telemetry)
- [12. Inference Requirements Matrix (frozen v1)](#12-inference-requirements-matrix-frozen-v1)
- [13. Explicit Non-Goals (rejected forever)](#13-explicit-non-goals-rejected-forever)
- [14. Operator Checklist (out-of-band actions)](#14-operator-checklist-out-of-band-actions)
- [15. Verification Master Script](#15-verification-master-script)
- [16. Release Cadence + DOI Policy](#16-release-cadence--doi-policy)
- [17. Failure Recovery Playbook](#17-failure-recovery-playbook)
- [18. Glossary of Named Constants](#18-glossary-of-named-constants)
- [19. Change Control (how this file changes)](#19-change-control-how-this-file-changes)

---

## 0. VOCABULARY + INVARIANTS

### 0.1 Status codes (used everywhere)

Every check, every command, every subprocess returns exactly one of:

| Code | Meaning | Exit code | Doctor JSON `status` |
|------|---------|-----------|----------------------|
| `PASS` | The check succeeded. | 0 | `"PASS"` |
| `DEGRADED` | The check succeeded structurally but is running in reduced mode. Eidolon still runs. | 2 | `"DEGRADED"` |
| `FAIL` | The check failed. Eidolon cannot proceed. | 1 | `"FAIL"` |
| Usage error | The CLI was invoked wrong. | 64 | (never appears in doctor output) |

**Never introduce a fourth status.** Never use `WARN`, `ERROR`, `SKIP`, `TODO`,
`UNKNOWN` as a status value. `[UNKNOWN]` is a reasoning tag for the operator
style, not a runtime status.

### 0.2 Loud-mode invariant (immutable)

Eidolon **never silently no-ops**. Every code path that could no-op MUST emit
a JSONL event to `$EIDOLON_HOME/events.jsonl` with `status="DEGRADED"` and a
human-readable `reason` field. This is enforced by the adversarial suite; do
not weaken it.

### 0.3 Immutable-safety invariant

The following files are **NEVER** modified by any autonomous action:

- `SOUL.md` (operator identity contract)
- `~/.hermes/config.yaml` top-level keys
- `~/.hermes/state/last_known_good/**`
- `LICENSE`
- `.github/workflows/adversarial.yml` (adversarial CI runner itself)

Automated processes that need to change these MUST fail with `status=FAIL` and
require operator action. This is checked by REC-010.

### 0.4 Provider-agnostic invariant

**Zero hardcoded model names, provider names, or API endpoints** in
`src/eidolon/`. Routing is by capability tier and requirement, never by name.
Enforced by `tests/unit/test_no_hardcoded_models.py` (already present).
The current forbidden-pattern list is in that file; expand it as new brand
names emerge but never contract it.

### 0.5 Stdlib-first invariant

`pyproject.toml` `dependencies` array MUST be empty until a REC explicitly
adds a dep with justification. Any REC that adds a runtime dep MUST:

- Justify it in the PR description.
- Add the dep to `NOTICE` with attribution.
- Add a `--no-<dep>` degraded fallback path or explain why one is impossible.

---

## 1. REPO GROUND TRUTH (STATE AT GENERATION TIME)

### 1.1 What ships as of 2026-07-07

**Merged to `main`**: None of the Critical Path RECs are merged yet. The
`main` branch is at the pre-CLI state with `SOUL.md`, `OPERATOR.md`, and the
`skills/dream-cycle/` handler.

**Open pull requests** (order matters):

| PR | Title | Head branch | Contains | Status |
|----|-------|-------------|----------|--------|
| [#1](https://github.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal/pull/1) | Critical Path: eidolon CLI spine + doctor/report/rollback/router (RECs 001-005) | `critical-path/rec-001-005-cli-spine` | RECs 001–005 + tests + CI matrix | OPEN, MERGEABLE, CI green |
| [#2](https://github.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal/pull/2) | Licensing + Zenodo + Hermes freshness (Fable-5 open questions) | `critical-path/rec-license-zenodo-hermes-freshness` | SPDX headers, NOTICE, `.zenodo.json`, RELEASING.md, `hermes_version` check (REC-016 correction) | OPEN, MERGEABLE, CI green |

**Merge order (mandatory)**: PR #1 → PR #2 → begin REC-006.

### 1.2 Files present in PR #1

```
src/eidolon/
  __init__.py, __main__.py, _version.py, cli.py
  commands/{__init__,doctor,report,rollback}.py
  checks/{__init__,hermes_config,hooks_wired,provider_capability,soul_present,state_dir}.py
  inference/{__init__,router,tiers}.py
  safety/{__init__,rollback,snapshot}.py
  reporting/{__init__,metrics}.py
  util/{__init__,events,paths}.py
tests/unit/
  __init__.py, _tmphomes.py, conftest.py
  test_cli.py, test_doctor.py, test_no_hardcoded_models.py
  test_report.py, test_rollback.py, test_router.py
.gitignore, pyproject.toml
.github/workflows/adversarial.yml   (Python 3.10–3.13 matrix + unit tests)
```

### 1.3 Files present in PR #2

```
.zenodo.json, NOTICE, RELEASING.md
src/eidolon/checks/hermes_version.py
tests/unit/test_hermes_version.py
+ SPDX headers on all Python files (34 files, +1 line each)
+ README "Releases & DOI" section
+ test_doctor.py fixture update
```

### 1.4 What is definitively NOT in the repo yet

- `install.sh` (REC-006)
- Published-to-PyPI wheels (REC-007 publishing side; the `pyproject.toml` scaffolding exists)
- Learning subsystem (`src/eidolon/learning/`) — RECs 008, 009, 019
- Risk model expansion — REC-010 (there is only a boolean risk in dream-cycle today)
- PII sanitization CI — REC-011
- Homebrew tap repo — REC-012
- MCP server — REC-013
- Nightly eval workflow — REC-014
- `CITATION.cff` — REC-015 (`.zenodo.json` shipped in PR #2, but CFF is separate)
- Skills lifecycle / shadow evaluation — REC-017
- Memory adapter abstraction — REC-018
- MCP registry + Home Assistant packaging — REC-020

---

## 2. END STATE DEFINITION (WHAT "DONE" MEANS)

At the completion of this roadmap, an inferior-model agent MUST be able to
execute the following on a fresh Ubuntu 22.04 or macOS 14+ machine with only
Python 3.11+ preinstalled, and observe every line of expected output.

### 2.1 Five-minute install verification

```bash
$ curl -fsSL https://eidolon-hermes.example.com/install.sh | bash
Eidolon installer v1.x.x
[1/4] verifying host prerequisites... PASS
[2/4] installing eidolon-hermes... PASS
[3/4] wiring Hermes hooks... DEGRADED (no Hermes home present; skipped)
[4/4] running eidolon doctor... DEGRADED
Install completed in 47s. Run `eidolon doctor` to see the reduced-mode reason.
```

Exit code: `2` (DEGRADED, because no Hermes host is installed on the fresh VM;
this is not a failure — the installer is faithful).

### 2.2 Doctor on a wired Hermes host

```bash
$ eidolon doctor --json | jq .overall
"PASS"

$ eidolon doctor --json | jq '.checks[].name'
"soul_present"
"hermes_config"
"hermes_version"
"state_dir"
"hooks_wired"
"provider_capability"
"risk_classifier_ready"        # added by REC-010
"pii_patterns_loaded"          # added by REC-011
"compatibility_supported"      # added by REC-016
"learning_bandit_ready"        # added by REC-008
"preferences_schema"           # added by REC-009
```

### 2.3 Report shows real numbers

```bash
$ eidolon report --since 24h --json
{
  "schema": 1,
  "window": "24h",
  "sessions": <int>,
  "lessons_added": <int>,
  "proposals_generated": <int>,
  "proposals_applied": <int>,
  "rollbacks": <int>,
  "bandit_arms": <int>,        # REC-008
  "preference_pairs": <int>,   # REC-009
  "risk_classified": <int>,    # REC-010
  "sanitize_hits": <int>       # REC-011
}
```

All values are non-negative integers. Never `null`, never `"N/A"`.

### 2.4 MCP surface

```bash
$ eidolon mcp serve --port 7401 &
$ curl -sS http://127.0.0.1:7401/mcp/tools | jq '.tools | length'
3
```

Tools exposed: `eidolon.report`, `eidolon.doctor`, `eidolon.learn.step`.

### 2.5 Homebrew

```bash
$ brew tap eidolon-hermes/eidolon
$ brew install eidolon
$ eidolon --version
1.x.x
```

### 2.6 Learning shows measurable improvement

Given a synthetic operator profile driving 100 sessions, after 100 bandit
iterations:

```bash
$ eidolon learn --step --iterations 100 --profile tests/fixtures/synthetic_op.json
$ eidolon report --window 7d --json | jq '.bandit_arms'
>= 3
```

And the regression suite must show ≥5% improvement in weighted score vs the
baseline arm on the held-out slice (see REC-008 acceptance test).

### 2.7 Reproducible academic surface

```bash
$ cat CITATION.cff | grep '^doi:'
doi: 10.5281/zenodo.<N>
```

DOI resolves. Zenodo record present. Reproducibility: the `v1.x.x` tag can be
checked out and the full test suite + adversarial + nightly eval pass on the
CI matrix.

### 2.8 Loud-mode adversarial suite

`python tests/adversarial.py` prints `N/N checks passed` where N ≥ 7 (RECs may
add adversarial scenarios; N never decreases).

---

## 3. DIRECTIVE HIERARCHY (IMMUTABLE OPERATOR RULES)

These override any REC. If a REC appears to contradict a directive, the
directive wins and the REC MUST be revised before execution.

1. **NO GUESSING.** Verify facts against primary sources (upstream repos,
   package registries, standards docs) or tag `[UNKNOWN]` in the PR
   description. Never write `# TODO: verify` in shipping code — either
   verify now or open an issue with a clear reproducer.
2. **NO GASLIGHTING.** Never rewrite history, never claim a test passed
   without stdout evidence in the commit message, never delete a failing
   test to make CI green.
3. **NO EAGERNESS.** No filler text. No flattery. No "great question!" in PR
   descriptions or code comments.
4. **NO SILENT NO-OPS.** Every conditional skip emits a DEGRADED event.
5. **NO HARDCODED MODELS.** Every inference call routes through
   `src/eidolon/inference/router.py`.
6. **NO DIRECT `~/.hermes/config.yaml` EDITS.** Use `hermes config set` or
   route through the operator. Enforced by REC-010.
7. **NO SECRETS IN THE REPO.** Enforced by REC-011 sanitization CI.
8. **NO NEW RUNTIME DEPS WITHOUT A `--no-<dep>` FALLBACK PATH.** Stdlib-first
   invariant.

---

## 4. ENVIRONMENT CONTRACT (WHAT AGENTS MAY ASSUME)

### 4.1 Python

- CPython 3.10, 3.11, 3.12, 3.13 supported. Any REC that requires a newer
  version must first bump the floor in `pyproject.toml` AND update the CI
  matrix in `.github/workflows/adversarial.yml` in the same PR.
- No PyPy support until REC-020+ (aspirational).

### 4.2 Operating systems

- macOS 14 (Sonoma) and 15 (Sequoia) — first-class targets.
- Ubuntu 22.04 LTS and 24.04 LTS — first-class targets.
- Debian 12 — best-effort (CI runs but not gating).
- Windows — **NOT supported**. Do not add Windows checks or paths. If a REC
  proposal touches Windows, reject it.

### 4.3 Filesystem paths

Resolved via `src/eidolon/util/paths.py`. Never hardcode absolute paths in
new code. Precedence (already implemented):

- `hermes_home()` → `$HERMES_HOME` → `~/.hermes`
- `eidolon_state_dir()` → `$EIDOLON_HOME` → `$HERMES_HOME/state/eidolon`

### 4.4 Environment variables (canonical list)

| Var | Consumer | Purpose |
|-----|----------|---------|
| `HERMES_HOME` | paths.py | Override Hermes home |
| `EIDOLON_HOME` | paths.py | Override Eidolon state dir |
| `HERMES_VERSION` | checks/hermes_version.py | Override version detection |
| `EIDOLON_LOG_LEVEL` | (planned REC-011+) | Debug logging verbosity |

Any new env var added by any REC MUST be added to this table in the same PR.

### 4.5 GitHub environment

- Base repo: `shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal`
- After REC-012 finalizes org migration: `eidolon-hermes/eidolon` (or the
  final chosen name — see `OPERATOR_INPUT_REQUIRED` in REC-012).
- Tap repo: `eidolon-hermes/homebrew-eidolon` (created out-of-band by
  operator per REC-012).
- Git identity for autonomous commits: `Eidolon Agent (Fable-5)
  <eidolon-agent@users.noreply.github.com>` (already configured).
- `gh` CLI must be invoked with `api_credentials=["github"]`.

---

## 5. CI CONTRACT (REQUIRED CHECKS + NAMING)

### 5.1 Required checks (blocking on all PRs to `main`)

| Check name | Workflow | Purpose | Added by |
|------------|----------|---------|----------|
| `adversarial (3.10)` | `adversarial.yml` | Unit tests + adversarial suite on Python 3.10 | REC-001 (present) |
| `adversarial (3.11)` | `adversarial.yml` | Same, 3.11 | REC-001 (present) |
| `adversarial (3.12)` | `adversarial.yml` | Same, 3.12 | REC-001 (present) |
| `adversarial (3.13)` | `adversarial.yml` | Same, 3.13 | REC-001 (present) |
| `Socket Security: Project Report` | (external) | Supply-chain SBOM | Pre-existing |
| `Socket Security: Pull Request Alerts` | (external) | Vulnerability alerts | Pre-existing |
| `installer-test (macos)` | `installer-test.yml` | Fresh-VM installer smoke | REC-006 |
| `installer-test (ubuntu)` | `installer-test.yml` | Same, Ubuntu | REC-006 |
| `sanitize` | `sanitize.yml` | PII pattern scan | REC-011 |
| `nightly-eval` | `nightly-eval.yml` | Learning regression (nightly, not blocking PRs) | REC-014 |

### 5.2 Naming rules

- Workflow files: `kebab-case.yml`.
- Job names inside a workflow: `snake_case` if scripted, `kebab-case` if
  purely declarative.
- Check-run display names: match the workflow's `name:` field verbatim; do
  not rely on GitHub's fallback.

### 5.3 Adding a required check

Any REC that adds a required check MUST:

1. Add the workflow file.
2. Add the check name to this section in the same PR (this file is source of truth).
3. Update `.github/settings.yml` or the operator's branch protection rules
   out-of-band (documented in the REC's `Operator step` field).

---

## 6. GLOBAL GATES (MUST HOLD BETWEEN ALL RECs)

Before starting **any** REC, verify all of the following. If any fails, stop.

### G1. Working tree clean

```bash
git status --porcelain
# Expected: empty output (exit 0)
```

### G2. On a REC branch, not `main`

```bash
test "$(git branch --show-current)" != "main"
# Expected: exit 0
```

### G3. All merged RECs' tests still green locally

```bash
cd $(git rev-parse --show-toplevel)
PYTHONPATH=src python -m unittest discover -s tests/unit 2>&1 | tail -3
# Expected: "OK" on last line, exit 0

PYTHONPATH=src python tests/adversarial.py 2>&1 | tail -1
# Expected: "N/N checks passed" where N >= 7
```

### G4. No hardcoded models regression

```bash
PYTHONPATH=src python -m unittest tests.unit.test_no_hardcoded_models -v 2>&1 | tail -3
# Expected: "OK"
```

### G5. Git identity set

```bash
git config user.name && git config user.email
# Expected non-empty. If empty, set to:
# git config user.name "Eidolon Agent (Fable-5)"
# git config user.email "eidolon-agent@users.noreply.github.com"
```

---

## 7. WORK ALREADY COMPLETED (RECs 001–005 + FRESHNESS/LICENSING)

**Reference only.** Do not re-execute. Both PRs are open + MERGEABLE + green.
The specifics of REC-016's original SemVer framing were corrected: Hermes
upstream is CalVer (`vYYYY.M.D[.patch]`), so freshness is a **date window**,
not a SemVer floor. This is enforced by `src/eidolon/checks/hermes_version.py`
(PR #2) and documented in `RELEASING.md`.

### 7.1 REC-001 (SHIPPED, PR #1)

- CLI spine: `src/eidolon/{cli,__main__,__init__,_version}.py`
- Entry point `eidolon = eidolon.cli:main` in `pyproject.toml`
- Exit codes: 0/1/2/64 per § 0.1

### 7.2 REC-002 (SHIPPED, PR #1)

- `eidolon doctor` and `eidolon doctor --json`
- Six checks (five in PR #1, `hermes_version` added in PR #2)
- Mandatory DEGRADED state; adversarial "unplug provider" returns DEGRADED

### 7.3 REC-003 (SHIPPED, PR #1)

- `eidolon report` reads `events.jsonl`
- Schema v1 in `src/eidolon/reporting/metrics.py`
- All integers, never null

### 7.4 REC-004 (SHIPPED, PR #1)

- `src/eidolon/safety/{snapshot,rollback}.py`
- Copy-on-write snapshots, sha256 manifest
- `eidolon rollback --dry-run` returns DEGRADED on missing snapshot

### 7.5 REC-005 (SHIPPED, PR #1)

- `src/eidolon/inference/{router,tiers}.py`
- Zero hardcoded model names (enforced by test)

### 7.6 Licensing + Zenodo + freshness (SHIPPED, PR #2)

- SPDX headers everywhere
- `NOTICE`, `.zenodo.json`, `RELEASING.md`
- `hermes_version` check with CalVer date-based freshness

---

## 8. CRITICAL PATH TIER 1 — RECs 006–011

**Ship all six within 30 days of PR #1+#2 merge.** Order matters. Do not
skip. Do not reorder unless explicitly permitted.

---

### REC-006: `curl | bash` installer

**Depends on**: RECs 001–007 merged. **Blocks**: REC-012.
**MAY_PARALLELIZE_WITH**: REC-008 (different files, no shared surface).

**Priority**: P1 · **Type**: packaging · **Effort**: 3 days · **Risk**: medium

#### Do exactly this

1. Create branch:
   ```bash
   git checkout main && git pull --ff-only
   git checkout -b rec-006/curl-bash-installer
   ```
2. Create `install.sh` at repo root with the exact template in
   [§ 8.6.1 Installer template](#861-installer-template).
3. Create `.github/workflows/installer-test.yml` with the exact matrix in
   [§ 8.6.2 Installer CI](#862-installer-ci).
4. Create `docs/install.md` documenting the single-line invocation and the
   `--dry-run`, `--no-hermes`, `--prefix=<path>` flags.
5. Add `installer-test (macos)` and `installer-test (ubuntu)` to § 5.1.

#### Constraints on the installer

- `#!/usr/bin/env bash` + `set -euo pipefail`.
- No `sudo` unless `EIDOLON_INSTALLER_SUDO=1` is explicitly set.
- No nested `curl | bash` — the installer downloads one Python wheel from a
  SHA-pinned URL, verifies the SHA, then invokes `python3 -m pip install
  --user <wheel>`.
- On completion, runs `eidolon doctor` and mirrors its exit code.
- Total wall-clock < 90s on a fresh CI VM.
- Idempotent: running twice on the same machine returns the same exit code.
- The wheel URL is `https://files.pythonhosted.org/packages/.../eidolon_hermes-<VER>-py3-none-any.whl` after REC-007 ships. Until then, the installer resolves the wheel from a versioned GitHub Release asset URL — the installer MUST accept `--wheel-url=<url>` for testing.

#### Verify

```bash
# Static checks
grep -n 'set -euo pipefail' install.sh   # exit 0, line 2 or 3
shellcheck install.sh                     # exit 0

# On fresh Ubuntu container
docker run --rm -v $PWD:/repo -w /repo ubuntu:22.04 bash -c '
  apt-get update && apt-get install -y python3 python3-pip curl &&
  bash install.sh --dry-run
'
# Expected exit code: 0
# Expected stdout contains: "installer dry-run: would install eidolon-hermes"

# Sanitization
grep -E 'curl.*\|.*(bash|sh)' install.sh | grep -v '^#'
# Expected: empty (no nested pipe-to-shell)
```

#### Pass criteria

- [ ] `install.sh` exists at repo root, executable (`chmod +x`).
- [ ] `.github/workflows/installer-test.yml` has both `macos-latest` and `ubuntu-latest` jobs.
- [ ] `shellcheck install.sh` exits 0.
- [ ] Dry-run on Ubuntu 22.04 container exits 0.
- [ ] CI `installer-test (macos)` and `installer-test (ubuntu)` both green on the PR.
- [ ] `docs/install.md` documents `--dry-run`, `--no-hermes`, `--prefix`, `--wheel-url`.

#### Rollback

```bash
git reset --hard origin/main
git branch -D rec-006/curl-bash-installer
```

#### Commit message template

```
feat(installer): curl|bash installer (REC-006)

- install.sh with SHA-pinned wheel fetch + eidolon doctor terminal step
- .github/workflows/installer-test.yml (macOS + Ubuntu)
- docs/install.md

set -euo pipefail throughout; no nested pipe-to-shell; idempotent.
Fresh-VM install to `eidolon doctor` in <90s on CI matrix.

Refs: master_EIDOLON_roadmap(F5).md § REC-006
```

#### Operator step (out-of-band, non-blocking)

- Configure the DNS/hosting for `install.eidolon-hermes.example.com` (or
  whatever the org resolves to). Until then, users use the raw
  GitHub Release download URL.

---

### REC-007: `pyproject.toml` + `pip install eidolon-hermes` (publishing)

**Depends on**: RECs 001–005 merged. **Blocks**: REC-006 wheel-hosting, REC-012.

**Priority**: P1 · **Type**: packaging · **Effort**: 1 day · **Risk**: low

The scaffolding (`pyproject.toml` name = `eidolon-hermes`, dynamic version,
entry point) already exists from PR #1. This REC adds the **publishing
pipeline**: TestPyPI on every merge to main, PyPI on tagged `v*` releases
with manual approval.

#### Do exactly this

1. Create branch: `rec-007/pypi-publishing`.
2. Create `.github/workflows/release.yml` with the exact template in
   [§ 8.7.1 Release workflow](#871-release-workflow).
3. Create `MANIFEST.in` including `README.md`, `LICENSE`, `NOTICE`, `RELEASING.md`, `SOUL.md`, `OPERATOR.md`.
4. Verify `python -m build` produces a wheel + sdist locally.
5. Add a TestPyPI badge to README.

#### Constraints

- Use PyPI **trusted publishing** (OIDC), not API tokens. The workflow uses
  `pypa/gh-action-pypi-publish@release/v1`.
- Publishing to real PyPI requires **manual approval** via a GitHub
  Environment named `pypi-prod`.
- TestPyPI publishing is automatic on every push to `main` (uses environment `pypi-test`).
- Version comes from `src/eidolon/_version.py` `__version__`. Never edit
  the version in `pyproject.toml` directly.
- The `-dev0` suffix is dropped only at release-tag time.

#### Verify

```bash
python -m pip install --upgrade build
python -m build
ls dist/
# Expected: eidolon_hermes-<VER>-py3-none-any.whl, eidolon-hermes-<VER>.tar.gz

python -m pip install --user dist/eidolon_hermes-*-py3-none-any.whl
which eidolon
eidolon --version
# Expected: matches src/eidolon/_version.py, exit 0

python -m pip uninstall -y eidolon-hermes
```

CI-side verification: push a `v0.0.0-rc0` tag on the branch, confirm the
workflow runs, and that **TestPyPI upload succeeds** and **PyPI upload
requires manual approval** (should pause on the environment gate).

#### Pass criteria

- [ ] `python -m build` produces both artifacts locally.
- [ ] Local install → `eidolon --version` works.
- [ ] `MANIFEST.in` includes all top-level docs (`README`, `LICENSE`, `NOTICE`, `SOUL.md`, `OPERATOR.md`).
- [ ] `release.yml` uses OIDC trusted publishing (no `PYPI_API_TOKEN`).
- [ ] TestPyPI upload works on a dry-run tag.
- [ ] PyPI upload path exists but requires environment approval.
- [ ] README shows TestPyPI badge.

#### Rollback

```bash
git reset --hard origin/main && git branch -D rec-007/pypi-publishing
```

#### Commit message template

```
feat(release): PyPI + TestPyPI publishing pipeline (REC-007)

- .github/workflows/release.yml (OIDC trusted publishing)
- MANIFEST.in with all top-level docs
- README TestPyPI badge

TestPyPI on every main push; PyPI requires manual environment approval.
Version single-sourced from src/eidolon/_version.py.

Refs: master_EIDOLON_roadmap(F5).md § REC-007
```

#### Operator step (out-of-band, blocking real PyPI)

- Register `eidolon-hermes` on PyPI and TestPyPI (user account, before org exists).
- Configure PyPI trusted publisher for `shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal` repo, workflow `release.yml`, environment `pypi-prod` / `pypi-test`.
- Squat `hermes-eidolon`, `eidolon-agent`, `eidolon-soul` (per Fable-5 recommendation, PR #2 discussion).

---

### REC-008: Contextual bandit + regression suite

**Depends on**: RECs 001–005 merged. **Blocks**: REC-009 (data schema), REC-017, REC-019.

**Priority**: P1 · **Type**: architecture · **Effort**: 5 days · **Risk**: medium

**v1 arm scope**: **prompt phrasing ONLY** (per Fable-5 stance in PR #2). Tool
ordering is out of scope until REC-017's shadow evaluation lands.

#### Do exactly this

1. Create branch: `rec-008/bandit-and-regression-suite`.
2. Create `src/eidolon/learning/` package:
   - `__init__.py` (empty, SPDX header)
   - `bandit.py` — Thompson sampling over Beta-Bernoulli arms; stdlib-only
   - `arms.py` — arm registry (v1: prompt phrasing arms only)
   - `rewards.py` — reward function contract; regression-suite pass rate is the reward
   - `replay.py` — append-only JSONL replay buffer at `$EIDOLON_HOME/replay.jsonl`
3. Create `src/eidolon/learning/schemas.py` — versioned dataclass schemas.
   Version = `schema = 1`. **Never** bump without a migration REC.
4. Create `src/eidolon/commands/learn.py` — `eidolon learn --step` subcommand.
5. Create `tests/eval/regression_suite.py` — the ≥20-case deterministic eval.
6. Create `tests/eval/fixtures/*.jsonl` — 20 seed cases (see § 8.8.1 for the
   canonical fixture format). **Every fixture is a synthetic persona; zero
   real operator data.**
7. Add `learning_bandit_ready` check to `src/eidolon/checks/`. Registered in
   doctor.
8. Add `bandit_arms` field to `metrics.py` report schema (schema stays v1;
   the field is optional-with-default-zero, so no breaking change).
9. Unit tests in `tests/unit/test_bandit.py`:
   - Bandit produces reproducible arm selection given a seed.
   - After 100 simulated episodes with a known-better arm (win rate 0.7 vs
     0.3), the better arm's posterior mean > 0.6 and selection frequency > 0.7.
   - Replay buffer is append-only (no in-place mutations).

#### Constraints

- Thompson sampling over Beta(α, β) posteriors. No neural bandit. Stdlib-only.
- Arms are **prompt-phrasing variants only** for v1. Each arm is a Python
  string template with `{placeholder}` positions; the bandit selects the
  template ID, not the substituted content.
- The bandit **never** modifies `SOUL.md`, skill code, or `~/.hermes/config.yaml`.
- The reward is computed by running the regression suite against a mock
  provider that always returns deterministic outputs (fixtures include
  expected outputs). No real inference in tests.
- The replay buffer schema is versioned and stable — the fields, order, and
  types are frozen at REC-008 landing; new fields require a schema bump REC.

#### Verify

```bash
# Unit tests
PYTHONPATH=src python -m unittest tests.unit.test_bandit -v
# Expected: "OK"; specifically test_known_better_arm_wins must PASS

# Regression suite (deterministic; no network)
PYTHONPATH=src python -m tests.eval.regression_suite --seed 42
# Expected exit 0; stdout contains "20/20 cases passed"

# End-to-end
EIDOLON_HOME=/tmp/eid PYTHONPATH=src python -m eidolon learn --step --iterations 100 --seed 42
cat /tmp/eid/replay.jsonl | wc -l
# Expected: 100

PYTHONPATH=src python -m eidolon report --json | jq '.bandit_arms'
# Expected: integer > 0

# Doctor picks up the new check
PYTHONPATH=src python -m eidolon doctor --json | jq '.checks[] | select(.name=="learning_bandit_ready")'
# Expected: a JSON object with status one of PASS/DEGRADED/FAIL
```

#### Pass criteria

- [ ] `src/eidolon/learning/` package created with 6 files above.
- [ ] `eidolon learn --step` works end-to-end and writes to replay buffer.
- [ ] Bandit convergence test PASSES with p<0.01 (seed-fixed).
- [ ] Regression suite `20/20 cases passed` at seed 42.
- [ ] `bandit_arms` field appears in `eidolon report --json`.
- [ ] `learning_bandit_ready` check registered in doctor.
- [ ] `test_no_hardcoded_models.py` still passes (no model names introduced).
- [ ] `grep -rE 'operator_name|bank_[a-z]+' src/eidolon/learning/` returns empty.

#### Rollback

```bash
git reset --hard origin/main && git branch -D rec-008/bandit-and-regression-suite
```

#### Commit message template

```
feat(learning): contextual bandit + regression suite (REC-008)

- src/eidolon/learning/{bandit,arms,rewards,replay,schemas}.py
- src/eidolon/commands/learn.py: `eidolon learn --step`
- tests/eval/regression_suite.py + 20 synthetic fixtures
- tests/unit/test_bandit.py: convergence test with fixed seed

v1 arms: prompt phrasing only (tool ordering deferred to REC-017).
Reward: regression-suite pass rate. Thompson sampling; stdlib only.
Zero real inference in tests; mock provider returns fixed outputs.

Refs: master_EIDOLON_roadmap(F5).md § REC-008
```

---

### REC-009: Preference-pair logging (schema-only)

**Depends on**: REC-008 merged. **Blocks**: REC-019 (needs the data).

**Priority**: P1 · **Type**: architecture · **Effort**: 2 days · **Risk**: low

Log preference pairs from bandit outcomes AND from operator-visible
`accepted/rejected` events. Do not train on them yet — REC-019 does that.

#### Do exactly this

1. Create branch: `rec-009/preference-pair-logging`.
2. Create `src/eidolon/learning/preferences.py`:
   - `PreferencePair` dataclass: `{ts: float, pair_id: str, chosen_id: str, rejected_id: str, context_hash: str, source: str, schema: int = 1}`.
   - `log_pair(chosen, rejected, source, context)` appends to `$EIDOLON_HOME/preferences.jsonl`.
   - `iter_pairs()` streams pairs back with schema check.
3. Wire two emitters:
   - Bandit outcome: when arm A's reward > arm B's over the last k
     episodes on the same context, emit `PreferencePair(chosen=A, rejected=B, source="bandit")`.
   - Rollback event: when a snapshot is restored, emit
     `PreferencePair(chosen=<prior_state>, rejected=<current_state>, source="rollback")`.
4. Unit tests in `tests/unit/test_preference_logging.py`:
   - Schema stability: golden fixture round-trips.
   - Append-only: file monotonically grows.
   - Sanitization: `context_hash` is a SHA256, never the raw context.
5. Add `preferences_schema` check to doctor (verifies file exists and every
   line parses as schema=1).

#### Constraints

- **Only structural records**: `chosen_id`, `rejected_id`, `context_hash`.
  Never raw prompt text, never raw response text.
- The `pair_id` is `sha256(chosen_id + "|" + rejected_id + "|" + context_hash)`
  truncated to 16 hex chars — deterministic, dedupable.
- File is JSONL, one pair per line, UTF-8.

#### Verify

```bash
PYTHONPATH=src python -m unittest tests.unit.test_preference_logging -v
# Expected: OK

EIDOLON_HOME=/tmp/eid python -c "
from eidolon.learning.preferences import log_pair, iter_pairs
log_pair('arm-A', 'arm-B', 'bandit', 'ctx-1')
pairs = list(iter_pairs())
assert len(pairs) == 1
assert pairs[0].chosen_id == 'arm-A'
print('OK')
"
# Expected: OK

grep -rE 'content|payload|body|raw' src/eidolon/learning/preferences.py
# Expected: no matches (payloads must be structural only)
```

#### Pass criteria

- [ ] `preferences.py` module with dataclass, `log_pair`, `iter_pairs`.
- [ ] JSONL emission verified by round-trip.
- [ ] Sanitization grep clean.
- [ ] Bandit and rollback code paths both emit pairs (verified by unit tests).
- [ ] `preferences_schema` doctor check present and PASSes with valid file, DEGRADED with missing file.
- [ ] `preference_pairs` field appears in `eidolon report`.

#### Rollback

```bash
git reset --hard origin/main && git branch -D rec-009/preference-pair-logging
```

#### Commit message template

```
feat(learning): preference-pair logging (REC-009)

- src/eidolon/learning/preferences.py: structural-only preference records
- Emitters: bandit outcomes + rollback events
- tests/unit/test_preference_logging.py: schema stability + sanitization

Schema v1 frozen. No raw content ever logged; context is SHA256'd.
Enables REC-019 (DPO) once ≥10k pairs accumulate. No training in this REC.

Refs: master_EIDOLON_roadmap(F5).md § REC-009
```

---

### REC-010: Risk classification (5-class + immutable-safety enforcement)

**Depends on**: REC-004 merged (rollback exists), can run in parallel with REC-008/009. **Blocks**: REC-017.

**Priority**: P1 · **Type**: safety · **Effort**: 2 days · **Risk**: low

Replace the today-binary risk with a 5-class ordinal: `no-op | low | medium | high | never-touch`.

#### Do exactly this

1. Create branch: `rec-010/risk-classification`.
2. Create `src/eidolon/safety/risk.py`:
   - Enum `RiskClass = {NO_OP, LOW, MEDIUM, HIGH, NEVER_TOUCH}`
   - `NEVER_TOUCH_PATHS` constant list (see § 0.3): SOUL.md, config.yaml top keys, last_known_good/, LICENSE, adversarial.yml
   - `classify(action: dict) -> RiskClass`
3. Create `src/eidolon/safety/classifier.py`:
   - Rule-based, stdlib-only.
   - `classify_action(target_path, mutation_kind, safety_flags) -> RiskClass`.
   - Regex-first path matching; if a target matches any `NEVER_TOUCH_PATHS`
     pattern, class is `NEVER_TOUCH` regardless of other flags.
4. Modify `skills/dream-cycle/handler.py`:
   - Every proposal is classified.
   - Auto-apply gate: only `LOW` proposals auto-apply. `MEDIUM` requires
     shadow evaluation (REC-017 will land it; until then, `MEDIUM` events
     are logged as DEGRADED with reason "shadow eval not yet implemented").
   - `HIGH` and `NEVER_TOUCH` never auto-apply; the handler emits FAIL and
     writes an audit log entry.
5. Create `docs/risk-model.md` documenting the 5 classes with examples.
6. Add `risk_classifier_ready` doctor check (verifies `risk.py` importable and
   `NEVER_TOUCH_PATHS` non-empty).
7. Unit tests in `tests/unit/test_risk_classification.py`:
   - Every class value maps to exactly one bucket.
   - `NEVER_TOUCH_PATHS` entries all classify to `NEVER_TOUCH`.
   - Attempting to auto-apply a `NEVER_TOUCH` action raises + writes audit log entry.
   - Regression test: previously-binary risk actions still classify the same way (round-trip).

#### Constraints

- The classifier is **pure** (no I/O, no time, no randomness). Any impurity is
  a bug.
- Adding a `NEVER_TOUCH_PATHS` entry is a one-line change and does NOT
  require a REC.
- Removing a `NEVER_TOUCH_PATHS` entry REQUIRES a REC (this is a safety
  loosening).

#### Verify

```bash
PYTHONPATH=src python -m unittest tests.unit.test_risk_classification -v
# Expected: OK

PYTHONPATH=src python -c "
from eidolon.safety.risk import classify, RiskClass
# NEVER_TOUCH regardless of other signals
r = classify({'target': 'SOUL.md', 'mutation_kind': 'append'})
assert r == RiskClass.NEVER_TOUCH, r
print('OK')
"
# Expected: OK

grep -rE 'operator|human|user_name' src/eidolon/safety/
# Expected: empty
```

#### Pass criteria

- [ ] Enum `RiskClass` has exactly 5 members, in strict ordinal order.
- [ ] `NEVER_TOUCH_PATHS` includes all § 0.3 items.
- [ ] `dream-cycle/handler.py` auto-applies ONLY `LOW`.
- [ ] `NEVER_TOUCH` action raises + audit log entry written.
- [ ] `risk_classifier_ready` doctor check present.
- [ ] `docs/risk-model.md` exists with examples per class.
- [ ] Sanitization grep clean.

#### Rollback

```bash
git reset --hard origin/main && git branch -D rec-010/risk-classification
```

#### Commit message template

```
feat(safety): 5-class risk classification (REC-010)

- src/eidolon/safety/{risk,classifier}.py: ordinal RiskClass enum
- NEVER_TOUCH_PATHS: SOUL.md, config.yaml top keys, last_known_good, LICENSE, adversarial.yml
- dream-cycle handler auto-applies LOW only; MEDIUM defers to REC-017 (shadow eval)
- docs/risk-model.md, risk_classifier_ready doctor check
- Pure classifier (no I/O); enforced by unit test

Refs: master_EIDOLON_roadmap(F5).md § REC-010
```

---

### REC-011: PII sanitization CI

**Depends on**: RECs 001–005 merged. **Blocks**: nothing directly, but REC-014 assumes CI is clean.

**Priority**: P1 · **Type**: safety · **Effort**: 1 day · **Risk**: low

#### Do exactly this

1. Create branch: `rec-011/sanitize-ci`.
2. Create `.sanitize-patterns.yml` at repo root — YAML list of regex patterns.
   **Seed with**:
   ```yaml
   # DO NOT commit real values here; these are patterns to detect them.
   patterns:
     - name: absolute_user_path
       regex: '/(Users|home)/[a-z0-9_-]{2,}/'
       exclude_paths: [tests/, docs/]
     - name: ipv4_private_range
       regex: '\b(10|192\.168|172\.(1[6-9]|2[0-9]|3[0-1]))\.[0-9]{1,3}\.[0-9]{1,3}\b'
     - name: local_hostname
       regex: '\b[a-z0-9-]+\.local\b'
     - name: agent_id_placeholder
       regex: '\b(hermes|eidolon)-[a-z0-9]{6,}-[a-z0-9]{4,}\b'
     - name: aws_access_key
       regex: '\bAKIA[0-9A-Z]{16}\b'
     - name: pypi_token
       regex: '\bpypi-[A-Za-z0-9_-]{50,}\b'
     - name: github_token
       regex: '\bghp_[A-Za-z0-9]{36}\b'
   ```
3. Create `scripts/sanitize_check.py`:
   - Reads `.sanitize-patterns.yml`.
   - Walks the repo (excludes `.git`, `__pycache__`, `dist`, `build`).
   - For each pattern, greps every non-excluded file.
   - Prints matches with `path:line: <PATTERN NAME> <redacted-match>`.
   - Exit 0 if no matches; exit 1 otherwise.
   - `--self-test` flag runs against a `tests/fixtures/sanitize_selftest/` dir
     with known matches and known clean cases.
4. Create `.github/workflows/sanitize.yml` — runs on every PR, blocks merge.
5. Create `.githooks/pre-commit` — same script, local guard. Document
   `git config core.hooksPath .githooks` in README.
6. Add `pii_patterns_loaded` doctor check (verifies YAML parses and has ≥5 patterns).

#### Constraints

- **PyYAML is forbidden.** Parse the YAML with stdlib `re` + a minimal
  hand-rolled parser (since the file structure is fixed and simple). This
  keeps the stdlib-first invariant.
- The self-test fixtures MUST include both positive and negative cases per pattern.
- Exclusions are path-prefix, not glob.

#### Verify

```bash
python scripts/sanitize_check.py --self-test
# Expected: exit 0, "self-test PASS (14/14 cases)"

# Run against the repo
python scripts/sanitize_check.py
# Expected: exit 0, "sanitize scan clean (0 matches)"

# Simulate a leak
echo 'AKIAABCDEFGHIJKLMNOP' > /tmp/leak.txt && cp /tmp/leak.txt scripts/leak_test.txt
python scripts/sanitize_check.py; echo "exit=$?"
# Expected: exit=1, one match reported
rm scripts/leak_test.txt

PYTHONPATH=src python -m eidolon doctor --json | jq '.checks[] | select(.name=="pii_patterns_loaded").status'
# Expected: "PASS"
```

#### Pass criteria

- [ ] `.sanitize-patterns.yml` has ≥7 seed patterns.
- [ ] `scripts/sanitize_check.py` runs without PyYAML.
- [ ] Self-test: all cases pass.
- [ ] Repo scan is clean at PR time.
- [ ] CI workflow `sanitize` is required.
- [ ] `pii_patterns_loaded` doctor check present.
- [ ] Adding a pattern is a one-line YAML change.

#### Rollback

```bash
git reset --hard origin/main && git branch -D rec-011/sanitize-ci
```

#### Commit message template

```
feat(safety): PII sanitization CI (REC-011)

- .sanitize-patterns.yml: 7 seed regex patterns
- scripts/sanitize_check.py: stdlib-only scanner + --self-test
- .github/workflows/sanitize.yml: required check
- .githooks/pre-commit: local mirror
- pii_patterns_loaded doctor check

Enforces Appendix D.1 (Zero PII) as CI, not soft convention.

Refs: master_EIDOLON_roadmap(F5).md § REC-011
```

---

## 8.6.1 Installer template (referenced by REC-006)

Save as `install.sh`. This is the **canonical** installer body. Do not
substantially reflow.

```bash
#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Eidolon installer — RECs 006/007
set -euo pipefail

VERSION="${EIDOLON_INSTALL_VERSION:-latest}"
WHEEL_URL="${EIDOLON_WHEEL_URL:-}"
PREFIX="${EIDOLON_PREFIX:-$HOME/.local}"
NO_HERMES=0
DRY_RUN=0

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --no-hermes) NO_HERMES=1 ;;
    --prefix=*) PREFIX="${1#*=}" ;;
    --wheel-url=*) WHEEL_URL="${1#*=}" ;;
    --version=*) VERSION="${1#*=}" ;;
    *) echo "unknown arg: $1" >&2; exit 64 ;;
  esac
  shift
done

log() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

log "Eidolon installer v${VERSION}"

# [1/4] host prerequisites
log "[1/4] verifying host prerequisites..."
command -v python3 >/dev/null || die "python3 not found"
PYVER=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
case "$PYVER" in
  3.10|3.11|3.12|3.13) : ;;
  *) die "python $PYVER not supported (need 3.10–3.13)" ;;
esac
log "  python $PYVER: PASS"

if [ "$DRY_RUN" -eq 1 ]; then
  log "installer dry-run: would install eidolon-hermes ${VERSION} to ${PREFIX}"
  exit 0
fi

# [2/4] install
log "[2/4] installing eidolon-hermes..."
if [ -n "$WHEEL_URL" ]; then
  TMPDIR="$(mktemp -d)"
  trap 'rm -rf "$TMPDIR"' EXIT
  curl -fsSL "$WHEEL_URL" -o "$TMPDIR/eidolon.whl"
  python3 -m pip install --user "$TMPDIR/eidolon.whl"
else
  python3 -m pip install --user "eidolon-hermes${VERSION:+==$VERSION}"
fi
log "  pip install: PASS"

# [3/4] hooks
log "[3/4] wiring Hermes hooks..."
if [ "$NO_HERMES" -eq 1 ] || [ ! -d "${HERMES_HOME:-$HOME/.hermes}" ]; then
  log "  no Hermes home present or --no-hermes: DEGRADED (skipped)"
else
  # Wiring TBD — safe no-op today; REC-017 will introduce real wiring.
  log "  hook wiring: DEGRADED (deferred to REC-017)"
fi

# [4/4] doctor
log "[4/4] running eidolon doctor..."
set +e
"$PREFIX/bin/eidolon" doctor --json | python3 -c '
import json,sys
d=json.load(sys.stdin)
print("  overall:", d["overall"])
sys.exit({"PASS":0,"DEGRADED":2,"FAIL":1}[d["overall"]])
'
CODE=$?
set -e

log "Install completed. eidolon doctor exit: $CODE"
exit "$CODE"
```

## 8.6.2 Installer CI (referenced by REC-006)

Save as `.github/workflows/installer-test.yml`:

```yaml
name: installer-test
on:
  pull_request:
  push:
    branches: [main]

jobs:
  installer-test:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: shellcheck install.sh
      - run: bash install.sh --dry-run
      - name: build local wheel
        run: |
          python -m pip install --upgrade build
          python -m build --wheel
      - name: install from local wheel
        run: |
          WHL=$(ls dist/*.whl | head -1)
          bash install.sh --wheel-url=file://$PWD/$WHL --no-hermes
```

## 8.7.1 Release workflow (referenced by REC-007)

Save as `.github/workflows/release.yml`:

```yaml
name: release
on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.ver.outputs.version }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - id: ver
        run: |
          V=$(python -c 'from src.eidolon._version import __version__; print(__version__)')
          echo "version=$V" >> "$GITHUB_OUTPUT"
      - run: |
          python -m pip install --upgrade build
          python -m build
      - uses: actions/upload-artifact@v4
        with: { name: dist, path: dist/ }

  publish-testpypi:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: pypi-test
    permissions: { id-token: write }
    steps:
      - uses: actions/download-artifact@v4
        with: { name: dist, path: dist/ }
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          repository-url: https://test.pypi.org/legacy/

  publish-pypi:
    needs: build
    if: startsWith(github.ref, 'refs/tags/v') && !contains(github.ref, '-')
    runs-on: ubuntu-latest
    environment: pypi-prod
    permissions: { id-token: write }
    steps:
      - uses: actions/download-artifact@v4
        with: { name: dist, path: dist/ }
      - uses: pypa/gh-action-pypi-publish@release/v1
```

## 8.8.1 Regression fixture format (referenced by REC-008)

Every file under `tests/eval/fixtures/*.jsonl` is one line per case:

```json
{"case_id": "rc-001", "category": "memory_recall", "context_hash": "<sha256>", "arm_inputs": {"prompt_variant_A": {...}, "prompt_variant_B": {...}}, "expected_winner": "A", "reward_weight": 1.0}
```

- `case_id` unique across fixtures.
- `category` ∈ {memory_recall, tool_selection, prompt_construction}.
- `context_hash` is a SHA256 of the context representation — the raw
  context is regenerable from the seed but not stored.
- `arm_inputs` is a mapping from arm ID to its deterministic mock-provider
  input; every arm ID here must be registered in `arms.py`.
- `expected_winner` is the ground-truth arm ID.
- `reward_weight` is a positive float; the regression score is
  `sum(weight * hit) / sum(weight)`.

---

## 9. FOUNDATION TIER 2 — RECs 012–016

Ship within 90 days of PR #1 merge. Each REC below is self-contained.

---

### REC-012: `brew install eidolon` via tap

**Depends on**: REC-007 shipped (PyPI wheel exists). **Blocks**: nothing.

**Priority**: P2 · **Type**: packaging · **Effort**: 2 days · **Risk**: low

#### Do exactly this

**Prerequisite** (operator, out-of-band, `OPERATOR_INPUT_REQUIRED`):
Create the tap repo `eidolon-hermes/homebrew-eidolon` (empty). If the org
`eidolon-hermes` does not yet exist, create it first (per PR #2 discussion).
The formula path is `Formula/eidolon.rb` in that tap repo.

Steps:

1. In this repo, create branch `rec-012/homebrew-tap`.
2. Create `packaging/homebrew/eidolon.rb` — the formula body (see § 9.12.1).
3. Create `docs/install-brew.md` — one-page how-to.
4. Update `README.md` install section to include the brew path.
5. In the tap repo (out-of-band), commit `Formula/eidolon.rb` copied from
   this repo. Add a GH Action to auto-update the formula on each new
   Eidolon release tag (see § 9.12.2).

#### Constraints

- Formula is Python-based (`Formula` subclass of `Formula`), depends on
  Homebrew's `python@3.11` bottle.
- No custom bottling. Users install from the PyPI wheel via `pip install`
  inside the formula.
- Tap repo name **must** start with `homebrew-`.

#### Verify

```bash
# In this repo
grep -q '^depends_on "python@3\.1[1-3]"' packaging/homebrew/eidolon.rb
# Expected: exit 0

# Locally (macOS only)
brew tap eidolon-hermes/eidolon "file://$PWD/../homebrew-eidolon"
brew install --build-from-source eidolon-hermes/eidolon/eidolon
brew audit --strict eidolon-hermes/eidolon/eidolon
# Expected: exit 0 on macOS

eidolon --version
# Expected: matches _version.py
```

#### Pass criteria

- [ ] Formula file present at `packaging/homebrew/eidolon.rb`.
- [ ] `brew audit --strict` passes.
- [ ] `docs/install-brew.md` exists.
- [ ] README has brew install line.
- [ ] Tap repo `homebrew-eidolon` exists in `eidolon-hermes` org and has a copy of the formula.

#### Rollback

```bash
git reset --hard origin/main && git branch -D rec-012/homebrew-tap
# Tap repo: revert or leave; no user impact until announced
```

#### Commit message template

```
feat(packaging): Homebrew tap + formula (REC-012)

- packaging/homebrew/eidolon.rb: Homebrew formula
- docs/install-brew.md
- README brew install section

Users: `brew tap eidolon-hermes/eidolon && brew install eidolon`.
Formula installs from PyPI wheel; no custom bottling.

Refs: master_EIDOLON_roadmap(F5).md § REC-012
```

---

### REC-013: `eidolon-mcp` server

**Depends on**: RECs 002, 003, 008 shipped. **Blocks**: REC-020.

**Priority**: P2 · **Type**: architecture · **Effort**: 3 days · **Risk**: low

#### Do exactly this

1. Branch: `rec-013/mcp-server`.
2. Create `src/eidolon/mcp/`:
   - `__init__.py`
   - `server.py` — stdlib-only MCP over HTTP+JSON-RPC (or stdio).
     Bind to 127.0.0.1 only.
   - `tools.py` — three tool definitions: `eidolon.report`,
     `eidolon.doctor`, `eidolon.learn.step`.
3. Add `eidolon mcp serve --port <N>` subcommand.
4. Create `docs/mcp.md` with a Claude Desktop config JSON snippet.
5. Unit tests in `tests/unit/test_mcp_server.py`:
   - Server starts and responds to `tools/list` with 3 tools.
   - Each tool call returns the same output as calling the CLI directly.
6. Add integration marker in `tests/integration/test_mcp_client.py` (skipped
   if `mcp` client library is missing; do not add the client as a runtime dep).

#### Constraints

- **Zero external MCP libraries as a runtime dep.** Speak the wire protocol
  from stdlib. If this is materially harder than expected, stop and open
  an issue for operator review; do not add a dep silently.
- Bind explicitly to `127.0.0.1`. No `0.0.0.0`. No IPv6 wildcard.
- Port is user-configurable via `--port`. No fixed port claim.
- Only three tools in v1. Do not add more without a new REC.

#### Verify

```bash
PYTHONPATH=src python -m unittest tests.unit.test_mcp_server -v
# Expected: OK

PYTHONPATH=src python -m eidolon mcp serve --port 7401 &
sleep 1
curl -sS -X POST http://127.0.0.1:7401/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | jq '.result.tools | length'
# Expected: 3
kill %1

grep -rE 'http://[0-9]|0\.0\.0\.0|localhost' src/eidolon/mcp/
# Expected: only 127.0.0.1 references, no 0.0.0.0
```

#### Pass criteria

- [ ] Server starts, exposes exactly 3 tools.
- [ ] Each tool round-trips against the CLI equivalent.
- [ ] Sanitization grep confirms 127.0.0.1 only.
- [ ] `docs/mcp.md` has a Claude Desktop config example.
- [ ] Zero new runtime deps.

#### Rollback

```bash
git reset --hard origin/main && git branch -D rec-013/mcp-server
```

#### Commit message template

```
feat(mcp): Eidolon MCP server (REC-013)

- src/eidolon/mcp/{server,tools}.py: stdlib-only MCP server
- 3 tools: eidolon.report, eidolon.doctor, eidolon.learn.step
- Binds 127.0.0.1 only; configurable port
- docs/mcp.md with Claude Desktop config snippet

Refs: master_EIDOLON_roadmap(F5).md § REC-013
```

---

### REC-014: Nightly regression eval

**Depends on**: REC-008 shipped. **Blocks**: nothing.

**Priority**: P2 · **Type**: architecture · **Effort**: 2 days · **Risk**: low

#### Do exactly this

1. Branch: `rec-014/nightly-eval`.
2. Create `.github/workflows/nightly-eval.yml`:
   - Trigger: `schedule: cron: '17 07 * * *'` (07:17 UTC daily; off-peak).
   - Steps: run `tests/eval/regression_suite.py --seed 42 --json` and append
     the JSON to `docs/eval-history.jsonl` via a bot commit.
   - If any metric regresses > 5% vs the last entry, open a GitHub issue
     tagged `regression`.
3. Create `tests/eval/nightly.py` — thin driver that calls
   `regression_suite.py` and computes deltas.
4. Create `docs/eval.md` — how to read `eval-history.jsonl`.

#### Constraints

- **No live inference.** Uses the same mock provider as REC-008's unit tests.
- Bot commits are made by `eidolon-agent[bot]` (a GitHub App set up
  out-of-band) or by the `eidolon-agent` account with a fine-grained PAT
  stored in `NIGHTLY_EVAL_PAT` secret.
- The regression threshold (5%) is a constant in `tests/eval/nightly.py`,
  editable without a REC.

#### Verify

```bash
# Local dry-run
PYTHONPATH=src python tests/eval/nightly.py --dry-run
# Expected: exit 0, prints "would append delta=X.XX (threshold 5%)"

# CI: after merge, wait for one nightly run
gh run list --workflow=nightly-eval.yml --limit 1
# Expected: after ~24h, one successful run
```

#### Pass criteria

- [ ] Workflow file exists.
- [ ] `tests/eval/nightly.py` runs locally in dry-run mode.
- [ ] `docs/eval.md` documents the format.
- [ ] First successful CI run appends a line to `docs/eval-history.jsonl`.
- [ ] Regression issue creation path tested (manually trigger with a
      seeded regression fixture on a throwaway branch).

#### Rollback

```bash
git reset --hard origin/main && git branch -D rec-014/nightly-eval
```

#### Commit message template

```
feat(ci): nightly regression eval (REC-014)

- .github/workflows/nightly-eval.yml (07:17 UTC daily)
- tests/eval/nightly.py: delta computation + threshold gate
- docs/eval.md: interpretation guide

Uses REC-008's mock provider; no live inference in CI.
Regression >5% opens a `regression` issue automatically.

Refs: master_EIDOLON_roadmap(F5).md § REC-014
```

---

### REC-015: `CITATION.cff` + Zenodo DOI

**Depends on**: PR #2 merged (`.zenodo.json` present). **Blocks**: academic surface.

**Priority**: P2 · **Type**: docs · **Effort**: 0.5 days · **Risk**: low

#### Do exactly this

1. Branch: `rec-015/citation-cff`.
2. Create `CITATION.cff` at repo root (spec: https://citation-file-format.github.io/):
   ```yaml
   cff-version: 1.2.0
   message: "If you use Eidolon in academic work, please cite it as below."
   title: "Eidolon: Self-Improvement Soul for Hermes Agent"
   abstract: "Provider-agnostic self-improvement layer for the Hermes Agent ecosystem."
   authors:
     - name: "Shag (Pixel Rainbow)"
   license: Apache-2.0
   repository-code: "https://github.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal"
   keywords: [hermes, agent, llm, self-improvement, eidolon]
   version: "OPERATOR_INPUT_REQUIRED_ON_RELEASE_TAG"
   date-released: "OPERATOR_INPUT_REQUIRED_ON_RELEASE_TAG"
   doi: "OPERATOR_INPUT_REQUIRED_AFTER_FIRST_ZENODO_MINT"
   ```
3. Create `docs/citing.md` with a BibTeX example.
4. On first stable `v*` tag, the release workflow (REC-007) MUST also update
   `CITATION.cff` `version` and `date-released` fields via a bot commit.
5. Add a "Cite this" line to the README linking to `CITATION.cff`.

#### Constraints

- The DOI field starts as a placeholder; it is populated **once** after the
  first Zenodo release mint (see RELEASING.md for the DOI policy).
- Author list is generic; no personal contact info.

#### Verify

```bash
# Validate the CFF
pip install --user cffconvert
cffconvert -i CITATION.cff --validate
# Expected: "Valid CITATION.cff (schema 1.2.0)."

# GitHub renders "Cite this repository" on the repo page — verify manually after merge.
```

#### Pass criteria

- [ ] `CITATION.cff` validates via `cffconvert`.
- [ ] `docs/citing.md` includes BibTeX.
- [ ] README has a "Cite this" link.
- [ ] Placeholders explicitly marked `OPERATOR_INPUT_REQUIRED_*`.
- [ ] Release workflow updated to bump CFF version at tag time.

#### Rollback

```bash
git reset --hard origin/main && git branch -D rec-015/citation-cff
```

#### Commit message template

```
docs(citation): CITATION.cff + Zenodo DOI plumbing (REC-015)

- CITATION.cff (spec 1.2.0)
- docs/citing.md with BibTeX
- README "Cite this" link
- release.yml bumps CFF version + date on stable tags

DOI field populated after first Zenodo mint (RELEASING.md).

Refs: master_EIDOLON_roadmap(F5).md § REC-015
```

---

### REC-016: Compatibility matrix + supported-versions check

**Depends on**: PR #2 merged (Hermes freshness check exists). **Blocks**: nothing.

**Priority**: P2 · **Type**: docs+code · **Effort**: 2 days · **Risk**: low

**Note**: PR #2 already shipped the **freshness** side of this REC — the
`hermes_version` check with CalVer date reasoning. What remains is the
**docs matrix + Python version enforcement**.

#### Do exactly this

1. Branch: `rec-016/compatibility-matrix`.
2. Create `docs/compatibility.md` — a table listing supported (OS, Python, Hermes date-window) combinations.
3. Create `src/eidolon/checks/python_version.py`:
   - Emits DEGRADED for Python 3.10 with a "3.11+ recommended" reason after
     2027-01-01 (well ahead of 3.10 EOL, so users have time).
   - Emits FAIL for anything < 3.10 (installer already blocks; this is a
     belt-and-braces check).
   - Emits DEGRADED for anything > 3.13 (untested).
4. Register `python_version` and `compatibility_supported` (an aggregator) in
   the doctor registry.
5. Update `.github/workflows/adversarial.yml` if any changes are needed to
   the matrix (currently 3.10–3.13; keep as-is).

#### Constraints

- Never FAIL for a Python version that appears in the CI matrix.
- Never PASS for a Python version outside the CI matrix.

#### Verify

```bash
PYTHONPATH=src python -m eidolon doctor --json | jq '.checks[] | select(.name=="python_version").status'
# On Python 3.11-3.13: "PASS"
# On Python 3.10: "PASS" (until 2027-01-01), then "DEGRADED"
```

#### Pass criteria

- [ ] `docs/compatibility.md` exists with a filled matrix.
- [ ] `python_version` doctor check registered.
- [ ] `compatibility_supported` aggregator returns worst-of the input checks.
- [ ] Unit test covers each version bucket.

#### Rollback

```bash
git reset --hard origin/main && git branch -D rec-016/compatibility-matrix
```

#### Commit message template

```
docs+feat(compat): compatibility matrix + python_version check (REC-016)

- docs/compatibility.md: supported (OS, Python, Hermes date-window)
- src/eidolon/checks/python_version.py: aggregator + individual check
- doctor registry registers both

Complements PR #2's date-based Hermes freshness check.

Refs: master_EIDOLON_roadmap(F5).md § REC-016
```

---

## 10. ASPIRATIONAL TIER 3 — RECs 017–020

**Ship within 12 months of PR #1 merge, in order.**

---

### REC-017: Shadow evaluation for skill promotion/demotion

**Depends on**: RECs 004, 008, 010 shipped. **Blocks**: real self-modification of skills.

**Priority**: P3 · **Type**: architecture · **Effort**: 2 weeks · **Risk**: high

#### Do exactly this

1. Branch: `rec-017/shadow-evaluation`.
2. Create `src/eidolon/skills/`:
   - `__init__.py`
   - `shadow.py` — runs candidate skills in shadow mode (results captured, not applied) for N sessions.
   - `lifecycle.py` — promote / demote / retire state machine.
3. Every skill has a `manifest.yml` describing its promotion criteria:
   ```yaml
   name: <string>
   version: <semver>
   promotion:
     min_shadow_sessions: 20
     min_bandit_posterior: 0.65
     regression_suite_pass_rate: 0.95
   ```
4. `eidolon skill promote <name>` — CLI command; refuses unless criteria met.
5. `eidolon skill list --shadow` — shows candidates in shadow.
6. Unit tests + one adversarial test:
   - Adversarial: a skill that regresses on the eval suite must NEVER be
     promoted, even with high bandit posterior.

#### Constraints

- Skill shadow evaluation NEVER modifies `~/.hermes/skills/*/handler.py` directly.
- All state lives in `$EIDOLON_HOME/skills/shadow/<skill>/*.jsonl`.
- Promotion is a **CLI action**, not automatic. Automatic promotion is a
  separate future REC.

#### Verify + Pass criteria + Rollback

Standard structure (see prior RECs).

**Pass criteria specific to REC-017**:

- [ ] Adversarial test: regressing skill fails promotion.
- [ ] Adversarial test: high-bandit + high-eval skill promotes.
- [ ] No direct edits to `~/.hermes/skills/` verified by sanitization grep.

---

### REC-018: Memory backend abstraction

**Depends on**: no Eidolon RECs; depends on Hermes memory subsystem being stable. **Blocks**: nothing.

**Priority**: P3 · **Type**: architecture · **Effort**: 1 week · **Risk**: medium

Introduce an adapter interface: `MemoryAdapter` with `store()`, `retrieve()`,
`consolidate()`. Ship two adapters: `HindsightAdapter` (production) and
`InMemAdapter` (CI/testing). Route selection is via host config.

Standard REC structure applies. Key constraint: **the in-memory adapter must
be sufficient for the entire test suite to run without a Hermes host.**

---

### REC-019: Bandit → DPO graduation

**Depends on**: REC-009 has emitted ≥10k preference pairs. **Blocks**: nothing.

**Priority**: P3 · **Type**: architecture · **Effort**: 3 weeks · **Risk**: high

#### Preconditions (verify before starting)

```bash
wc -l $EIDOLON_HOME/preferences.jsonl
# Expected: >= 10000
```

If < 10k, **do not start**. Continue to accumulate. Report the current count
to the operator and stop.

Once ≥ 10k:

1. Branch: `rec-019/dpo-training`.
2. Add first runtime dependency: `torch>=2.2` OR `mlx>=0.15` (Apple Silicon path). This is the **first** approved runtime dep; document heavily in NOTICE.
3. `src/eidolon/learning/dpo.py` — training loop.
4. `src/eidolon/learning/train.py` — CLI entry `eidolon learn --train dpo`.
5. Held-out slice: last 10% of pairs, never seen during training.
6. Acceptance: trained policy outperforms bandit best-fixed-arm by ≥ 5% on held-out slice.

**Key constraint**: The trained policy is a JSON file (weights + config)
loaded at inference time. No dynamic Python code generation. No shell
execution of trained artifacts.

Standard verify/rollback structure.

---

### REC-020: MCP registry + Home Assistant add-on

**Depends on**: REC-013 shipped. **Blocks**: nothing.

**Priority**: P3 · **Type**: packaging · **Effort**: 1 week · **Risk**: low

Two artifacts:

1. `packaging/mcp-registry/manifest.json` — a manifest that a public MCP
   tool registry (spec URL to be filled at REC time) can ingest.
2. `packaging/homeassistant/config.yaml` — HA add-on config, with a
   restricted permission scope documented per HA add-on schema.

Both are additive surface. No core code changes.

Standard verify/rollback structure.

---

## 11. CROSS-CUTTING CONCERNS (safety, privacy, telemetry)

### 11.1 Safety review checklist (applied at every PR)

For every PR that touches `src/eidolon/safety/`, `src/eidolon/skills/`,
`skills/dream-cycle/`, or `SOUL.md`:

- [ ] The `NEVER_TOUCH_PATHS` list in `src/eidolon/safety/risk.py` is unchanged (or expanded, never contracted).
- [ ] No new auto-apply pathway for `MEDIUM+` risk actions.
- [ ] Every new event type has a `status` field.
- [ ] The adversarial suite has a scenario for the new behavior.

### 11.2 Privacy invariants (enforced by REC-011)

- No absolute user paths (`/Users/*`, `/home/*`) in the repo except in `tests/` and `docs/` (which are audited manually).
- No IP addresses in the private RFC 1918 ranges.
- No `.local` hostnames.
- No secrets patterns (`AKIA*`, `ghp_*`, `pypi-*`).

### 11.3 Telemetry policy

**Zero opt-out telemetry in v1.** Any telemetry — even anonymous — requires
its own REC and operator approval. Users report metrics via `eidolon report`;
Eidolon never phones home.

---

## 12. INFERENCE REQUIREMENTS MATRIX (FROZEN v1)

Copied verbatim from the Fable-5 verdict. **This table is frozen**; changes
require a new REC that updates both this section and the corresponding
component code.

| Component | Min model class (local) | Min model class (API) | Context window min | Structured output | Latency budget | Tier routing | Zero-LLM degradation | Quality-floor test |
|---|---|---|---|---|---|---|---|---|
| dream-cycle: reflection | 7B instruct, Q4 | Any mid-tier | 16k | JSON preferred | 90s (Tier B), 30s (Tier A API) | B default; A escalates; C uses local | Emit "reflection skipped: no provider" event; empty pattern set with reason | 10 fixed session traces → ≥3 distinct patterns per trace |
| dream-cycle: lesson extraction | 7B instruct | Any mid-tier | 8k | JSON required (versioned schema) | 30s | B default | Skip; `lessons_added=0` with reason | 5 fixed patterns → lesson objects match schema |
| dream-cycle: proposal generation | 14B instruct or 7B+tools | Mid-tier | 16k | JSON required | 60s | B for local, A for API | Skip; `proposals_generated=0` | 5 fixed lesson sets → proposals include `target`, `risk_class`, `acceptance_test` |
| dream-cycle: shadow evaluation | Same as reflection | Same | 8k | Bool + numeric score JSON | 30s per candidate | Same as reflection | Skip evaluation, candidate stays pending | 20 fixed (candidate, ground-truth) pairs; ≥70% agreement |
| Memory consolidation | 7B instruct | Any | 32k | JSON | 300s nightly | B/C only; skip on A | Skip; "consolidation skipped" | 100 dup/near-dup memories → merged set size within ±10% expected |
| PII / sanitization scan | Regex-first, LLM only for ambiguity | Any (ambiguous only) | 4k | Bool + span JSON | 5s per commit | Regex path is A-safe; LLM escalation is B+ | **Regex-only mode is default and always available**; LLM is escalation only | 30 fixed strings (15 PII, 15 clean); precision ≥ 0.95, recall ≥ 0.90 on regex-only |
| Curriculum generator | 14B instruct | Mid-tier | 32k | JSON | 120s weekly | B/C; A escalates weekly to API | Skip; run last week's curriculum | 10 fixed operator profiles → ≥3 skill categories |
| Reward / preference model | 7B instruct or classifier head | Any | 8k | Numeric score JSON | 5s per episode | B default | Fall back to heuristic scorer with `mode="heuristic"` | 50 fixed (episode, expected_score) pairs; Spearman ρ ≥ 0.6 |
| Report generation | Template-first, LLM optional | Optional API for narrative | 4k | Markdown | 10s | A-safe (templates); B/C for narrative overlay | **Templates always available**; LLM narrative is enrichment only | Golden-file test on fixture data |

### 12.1 Tier routing policy

- **Tier A** (API-key-only, any hardware): All inference to host Hermes API provider. Regex/template fallbacks always available. If host has no API provider: doctor DEGRADED; affected components emit zero-work events with reason.
- **Tier B** (16–32GB Apple Silicon / consumer GPU): Route reflection/lessons/proposals to local 7–14B; escalate to API when local returns malformed JSON twice or misses latency budget.
- **Tier C** (64GB+ workstation): Local-first for everything including consolidation and curriculum. API is opt-in "second opinion".

### 12.2 Escalation rule

A task escalates one tier when:

- Structured-output validation fails twice, OR
- Latency budget exceeds 2×, OR
- Quality-floor test fails at doctor-check time.

### 12.3 Provider-agnostic interface

The router requests `tier` + `capabilities` (`json_mode`, `min_context`,
`max_latency_s`). Host Hermes resolves to a concrete provider via
`provider_models_cache.json`. **No component in Eidolon ever names a model
or endpoint directly.** Enforced by `tests/unit/test_no_hardcoded_models.py`.

---

## 13. EXPLICIT NON-GOALS (REJECTED FOREVER)

These are rejected. If a future REC proposal matches one of these,
**reject the REC** and cite this section.

- **Public leaderboard** at `eidolon.<domain>/leaderboard`. Gamification risk, no signal.
- **EidolonCon, certification program, plugin marketplace**. Community theater.
- **Rename the project** to escape "prior art" concerns. Name equity > search-engine tax.
- **PPO / GRPO / RLAIF as MVP learning primitive**. Fragile, sample-inefficient. Bandit → DPO only.
- **Direct edits to `~/.hermes/config.yaml`**. Use `hermes config set`.
- **Genetic algorithms over prompt variants**. No principled reward signal.
- **Multi-agent federated learning in v1 or v2**. Privacy story unsolved.
- **Hard-coding DwarfStar / DS4 / any specific local engine as first-class dep**. All engines are adapters behind the capability router.
- **Silent no-ops anywhere in the codebase**. Loud-mode invariant.
- **"Cite this in academic papers" campaign** before REC-015 lands with a real DOI.
- **Opt-out telemetry**. Zero telemetry in v1.
- **Windows support** (per § 4.2).
- **PyPy support** in Tier 1 or 2. Reconsider only at REC-020+.
- **A GUI**. Eidolon is a CLI and a library. Distribution via MCP + HA is the extent of "surface".

---

## 14. OPERATOR CHECKLIST (out-of-band actions)

Actions the roadmap cannot execute autonomously. Mark done as completed.

### 14.1 GitHub

- [ ] Create org `eidolon-hermes` (or the operator's chosen final name).
- [ ] Transfer this repo to that org at v1.0 cut. Old URL redirects.
- [ ] Create tap repo `eidolon-hermes/homebrew-eidolon` (empty for REC-012).
- [ ] Configure branch protection on `main`: require all § 5.1 checks + 1 review.
- [ ] Add `eidolon-agent` (or bot account) as a collaborator with limited scope for nightly commits.

### 14.2 PyPI

- [ ] Register `eidolon-hermes` on PyPI (matches `pyproject.toml`).
- [ ] Register `eidolon-hermes` on TestPyPI.
- [ ] Configure PyPI trusted publisher for the repo, workflow `release.yml`, environments `pypi-prod` and `pypi-test`.
- [ ] Defensive squats on PyPI: `hermes-eidolon`, `eidolon-agent`, `eidolon-soul`.

### 14.3 Zenodo

- [ ] Link Zenodo to the GitHub org (once created).
- [ ] Enable Zenodo integration for the repo.
- [ ] Verify `.zenodo.json` metadata renders on a `v0.9.0-rc0` test tag.
- [ ] After first stable `v*` tag mints: fill DOI in `CITATION.cff` (REC-015).

### 14.4 Hosting

- [ ] `install.eidolon-hermes.example.com` (or org-chosen domain) → GitHub Release assets.
- [ ] SSL cert managed via CloudFlare or Let's Encrypt.

---

## 15. VERIFICATION MASTER SCRIPT

At any point after REC-011 lands, running this script MUST pass. It is the
end-to-end gate for "is the repo consistent with the roadmap":

```bash
#!/usr/bin/env bash
# scripts/roadmap_verify.sh
set -euo pipefail

echo "== Global gates =="
[ "$(git branch --show-current)" != "main" ] || { echo "on main"; exit 1; }
[ -z "$(git status --porcelain)" ] || { echo "dirty tree"; exit 1; }

echo "== Unit tests =="
PYTHONPATH=src python -m unittest discover -s tests/unit

echo "== Adversarial =="
PYTHONPATH=src python tests/adversarial.py

echo "== Hardcoded-models check =="
PYTHONPATH=src python -m unittest tests.unit.test_no_hardcoded_models

echo "== Sanitize =="
python scripts/sanitize_check.py

echo "== Doctor =="
PYTHONPATH=src python -m eidolon doctor --json | python -c '
import json,sys
d=json.load(sys.stdin)
assert d["overall"] in {"PASS","DEGRADED"}, d
print("doctor overall:", d["overall"])
'

echo "== Report schema =="
PYTHONPATH=src python -m eidolon report --json | python -c '
import json,sys
d=json.load(sys.stdin)
assert d["schema"] == 1
for k in ("sessions","lessons_added","proposals_generated","proposals_applied","rollbacks"):
    assert isinstance(d[k], int) and d[k] >= 0, (k, d[k])
print("report schema: OK")
'

echo "== ALL VERIFICATION PASSED =="
```

Create this file at `scripts/roadmap_verify.sh` as part of the first REC
that ships after this roadmap is committed (i.e., part of REC-006's PR or
a standalone housekeeping PR immediately after).

---

## 16. RELEASE CADENCE + DOI POLICY

### 16.1 Version numbers

Eidolon is **SemVer**: `vMAJOR.MINOR.PATCH`. Host Hermes is CalVer; do not
confuse them.

- `MAJOR` bumps on breaking API changes (report schema, CLI subcommands
  removed, config path changes).
- `MINOR` bumps on new features (a new REC lands).
- `PATCH` bumps on bug fixes.
- Prerelease: `-rc1`, `-beta1`, `-alpha1`, `-dev0` (dev is unreleased HEAD).

### 16.2 Cadence

- Patch releases: as needed, no gating.
- Minor releases: at the end of each Tier's shipping window (Tier 1 → v1.4.0, Tier 2 → v1.5.0, Tier 3 → v2.0.0).
- Major releases: only when the report schema, CLI, or safety invariants change materially.

### 16.3 DOI policy (from RELEASING.md, restated)

- Stable `vX.Y.Z` tags → Zenodo mint.
- Prerelease tags (`-rc*`, `-beta*`, `-alpha*`) → discard the Zenodo draft before publishing.
- `-dev*` → never tagged.

### 16.4 Version bump checklist (used at every release)

1. Bump `src/eidolon/_version.py` (drop `-dev0`).
2. Update `CHANGELOG.md` (create if missing).
3. Update `CITATION.cff` `version` and `date-released` (REC-015 automation does this on tag).
4. `git tag -s vX.Y.Z -m "Eidolon vX.Y.Z"`.
5. `git push origin vX.Y.Z`.
6. Approve the PyPI publish job in `pypi-prod` environment.
7. Verify Zenodo picks up the tag.
8. Bump `_version.py` to next `-dev0` on `main`.

---

## 17. FAILURE RECOVERY PLAYBOOK

### 17.1 A REC's CI fails

- Read the failing check's log.
- Match the failure to a `Pass criterion` in the REC.
- If the failure matches, iterate on the branch. Do NOT force-push over
  `main`.
- If the failure does not match any criterion, STOP and report to the
  operator. Do not invent a fix.

### 17.2 A merged REC causes a downstream regression

- Roll forward with a patch PR, not a revert (revert only if the regression
  blocks all further work).
- The regression's fix must add a new unit test that would have caught it.

### 17.3 The adversarial suite fails after a REC lands

- **Highest severity.** Immediately revert the REC's PR.
- Open an incident issue tagged `p0`.
- Do not proceed to any subsequent REC until adversarial is green.

### 17.4 A `NEVER_TOUCH` file changes autonomously

- **Critical.** Halt all autonomous work.
- Roll back to the last-known-good snapshot.
- Investigate the code path that permitted the change.
- File a `p0` issue tagged `safety-invariant-violation`.

### 17.5 A secret is committed

- Immediately rotate the secret (operator action).
- Force-push to remove the object (`git filter-repo` or GitHub's
  secret-removal support).
- Add a pattern to `.sanitize-patterns.yml` covering the class of secret.
- Post-mortem issue tagged `security`.

---

## 18. GLOSSARY OF NAMED CONSTANTS

Every named constant that inferior models might invent. Bookmark:

| Name | Value | Defined in | Purpose |
|------|-------|------------|---------|
| `PASS`, `DEGRADED`, `FAIL` | `"PASS"`, `"DEGRADED"`, `"FAIL"` | `src/eidolon/checks/__init__.py` | Status codes |
| Exit code 0 | integer 0 | (universal) | PASS |
| Exit code 1 | integer 1 | (universal) | FAIL |
| Exit code 2 | integer 2 | (universal) | DEGRADED |
| Exit code 64 | integer 64 | (sysexits.h) | Usage error |
| `HERMES_MIN_DATE` | `date(2026, 4, 8)` at PR #2 landing | `src/eidolon/checks/hermes_version.py` | 90d trailing freshness floor |
| `NEVER_TOUCH_PATHS` | list of path patterns | `src/eidolon/safety/risk.py` (REC-010) | Immutable-safety enforcement |
| `RiskClass` enum | `NO_OP, LOW, MEDIUM, HIGH, NEVER_TOUCH` | `src/eidolon/safety/risk.py` (REC-010) | 5-class ordinal risk |
| Schema version | `1` (frozen) | `src/eidolon/reporting/metrics.py` | Report + preference schemas |
| Bandit posterior threshold for promotion | `0.65` | `src/eidolon/skills/lifecycle.py` (REC-017) | Skill promotion gate |
| DPO training threshold | `10000` preference pairs | REC-019 precondition | Bandit → DPO graduation |
| Regression suite size | `20` cases (v1) | `tests/eval/fixtures/*.jsonl` (REC-008) | Minimum eval breadth |
| Nightly regression threshold | `5%` | `tests/eval/nightly.py` (REC-014) | Auto-issue trigger |
| Installer wall-clock budget | `90` seconds | `.github/workflows/installer-test.yml` (REC-006) | 5-minute rule enforcement |

If a constant is not in this table, it is a named constant *waiting to be
added*. Add it in the REC that introduces it, in the same PR.

---

## 19. CHANGE CONTROL (how this file changes)

### 19.1 Anyone can propose an edit

Open a PR that modifies this file. The PR title MUST be prefixed
`roadmap(F5):`. Example: `roadmap(F5): clarify REC-013 MCP tool naming`.

### 19.2 Roadmap-breaking changes require operator sign-off

The following changes require an explicit operator approval in the PR
before merge (bot approvals do not count):

- Removing a REC.
- Changing a REC's priority tier.
- Loosening a directive in § 3.
- Removing a `NEVER_TOUCH_PATHS` entry.
- Contracting the required-check list in § 5.1.
- Adding a new opt-out telemetry mechanism.
- Adding Windows to § 4.2.

### 19.3 Non-breaking changes

The following do NOT require operator approval (but still need CI green):

- Fixing typos.
- Adding new RECs at the end of a tier (as long as they respect the tier's
  effort ceiling and don't invert dependencies).
- Refining a REC's `Verify` block to catch a real bug the current block missed.
- Adding examples, glossary entries, or clarifications.

### 19.4 Superseding this file

If a new F-N (F-6, F-7, …) roadmap is produced, this file MUST be renamed
`archived/master_EIDOLON_roadmap(F5).md` in the same PR that lands the new
one. Never delete a superseded roadmap; keep it in `archived/` for
provenance and diffing.

---

## END OF ROADMAP

This roadmap is deterministic, source-cited to the repo's own artifacts, and
executable REC-by-REC by any autonomous coding agent. It is not a suggestion.
It is a work order.

If any step is ambiguous, STOP and ask the operator. Do not guess. Do not
gaslight. Do not eagerly fill in blanks.

— Fable-5
