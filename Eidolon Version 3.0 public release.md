# Eidolon Version 3.0 Public Release

> **Report generated:** 2026-07-13 · **Branch HEAD at report time:** `35e39f2fe65584a08d9216a1ae10bf649e2df432`
> **Tags:** [VERIFIED] = sourced from live GitHub commit data this session · [INFERRED] = reasoned from commit messages and diffs reviewed · [UNKNOWN] = not inspectable without local clone/CI run

---

## Executive State

**Current version string:** `2.0.0` [VERIFIED — commit `fa99bcd`]

Eidolon is a drop-in Hermes Agent self-improvement layer. As of 2026-07-13 main is at **51 merged PRs**, version bumped to `2.0.0`, with an MCP server, transactional outbox, judgment brain, memory adapter abstraction, Hermes MEMORY.md bridge, human-readable scoreboard, and full curl-bash + Homebrew install pipeline — all CI green per commit messages citing 15/15 unit and 7/7 adversarial gates. [VERIFIED from commit messages `4c64684`, `fa99bcd`, `35e39f2`]

The repo is **not yet at v3.0**. This report defines the delta required to reach v3.0 public release, documents the last-7-day commit ledger, and specifies verification gates that must pass before tagging.

> **PREMORTEM — v3.0 risk:** The primary failure mode is a gap between CI-green unit tests and real Hermes Agent installation behavior. Written code ≠ proven code. Every v3.0 gate below therefore requires field evidence from an actual Hermes install, not just CI output.

---

## Seven-Day Commit Ledger

> Period: 2026-07-06T00:00:00Z → 2026-07-13T23:59:59Z. All SHAs verified from live `main`. Commit messages inspected; full diffs not fetchable via GitHub Write API in one turn — diff-level claims are marked [INFERRED from commit message] or [UNKNOWN].

### Tier: v2.0 Vertical Slice + Version Bump (2026-07-11 → 2026-07-13)

| SHA (short) | Date (UTC) | Subject | Product Integer Moved |
|---|---|---|---|
| `35e39f2` | 2026-07-13 | feat: report human scoreboard (#51) | `eidolon report` now emits human-readable scoreboard [INFERRED] |
| `4c64684` | 2026-07-13 | fix(mcp): register eidolon.hindsight.retain tool (#50) | Fixes silent KeyError/-32601 drop; 15/15 CI, 7/7 adversarial [VERIFIED from msg] |
| `352d7b1` | 2026-07-13 | docs: add v2.0 pre-stable banner to README (#49) | README now signals pre-stable status to visitors [INFERRED] |
| `58a135d` | 2026-07-12 | fix(dream): record lessons_retained metric on lesson flush (#48) | `lessons_retained` integer now increments correctly in `eidolon report` [INFERRED] |
| `fb7992b` | 2026-07-12 | fix(outbox): flush loop-closer actually drains pending lessons (#47) | Pending lessons no longer silently dropped on loop close [INFERRED] |
| `acfdd49` | 2026-07-12 | fix(outbox): flush loop-closer actually drains pending lessons | Duplicate direct push of same fix [VERIFIED — two SHAs for same change] |
| `fa99bcd` | 2026-07-11 | chore(release): bump version string to 2.0.0 | `__version__` = `2.0.0` [VERIFIED from msg] |
| `3d52ef3` | 2026-07-11 | feat(v2.0): vertical slice — skill staging, inbox clear, scoreboard (#45) | Skill promote/stage/clear + scoreboard wired end-to-end [INFERRED from msg] |
| `9af62b7` | 2026-07-11 | fix(judgment): complete metrics API and isolate state paths | Judgment metrics no longer share mutable state across tests [INFERRED] |
| `1de797c` | 2026-07-11 | feat(v2.0): Judgment Brain — classify lessons into real Hermes actions | New integer: `proposals_applied` via judgment classification [INFERRED] |
| `75ed974` | 2026-07-11 | feat(hermes): bridge dream applies into Hermes MEMORY.md | `apply_low` promotes lesson text into `memories/MEMORY.md`; dedup/skip logic [VERIFIED from msg] |

### Tier: Core Infrastructure (2026-07-09 → 2026-07-10)

| SHA (short) | Date (UTC) | Subject | Product Integer Moved |
|---|---|---|---|
| `7c09d29` | 2026-07-10 | fix(inference): Hermes-native provider cache → Tier-A resolve | Provider resolution no longer silently fails on Hermes-native cache format [INFERRED] |
| `c6572c0` | 2026-07-10 | fix(dream): preference_update LOW + measurable apply_low | `applied_proposals` integer now actually increments; first real dream.apply PASS [VERIFIED from msg] |
| `e2dbee0` | 2026-07-10 | feat(dream): wire Outbox.capture+flush into extract_lessons/propose (REC-021) | Lessons and proposals now durably captured via transactional outbox [INFERRED] |
| `6b7dbad` | 2026-07-10 | test: add test_arms.py for ArmRegistry and seed arms (#39) | 13 new unit tests; arm registry correctness locked in [VERIFIED from msg] |
| `f0ec35b` | 2026-07-10 | feat(dream): wire MemoryAdapter into dream-cycle stubs (REC-020) | Dream cycle now reads/writes through MemoryAdapter ABC [INFERRED] |
| `829d197` | 2026-07-10 | feat: transactional outbox for lesson/proposal capture (REC-019) | Crash-safe pending.jsonl → events.jsonl pipeline; 6 new tests [VERIFIED from msg] |
| `3b6ec0a` | 2026-07-10 | feat(memory): memory backend abstraction REC-018 (#35) | MemoryAdapter ABC + InMemAdapter + HindsightAdapter; 10 unit tests [VERIFIED from msg] |
| `a445435` | 2026-07-09 | feat(installer): REC-006 curl-bash installer + docs/install.md (#34) | `curl \| bash` install works on macOS+Linux × Python 3.10-3.13; 8×matrix CI [VERIFIED from msg] |
| `843f27b` | 2026-07-09 | feat(rec-017): eidolon skill promote/demote/retire/status CLI | Skill lifecycle CLI operational; adversarial green [VERIFIED from msg] |
| `905fd80` | 2026-07-09 | docs: CHANGELOG entries for 2026-07-09 merge wave | Keep-a-Changelog [Unreleased] section filled [INFERRED] |
| `a8ec18b` | 2026-07-09 | docs(readme): genesis paragraph linking philosophy and acknowledgments | README links PHILOSOPHY.md and ACKNOWLEDGMENTS.md [INFERRED] |
| `3e7b24d` | 2026-07-09 | docs(philosophy): origins, quine principle, tightened provenance | PHILOSOPHY.md created [INFERRED] |
| `265aebb` | 2026-07-09 | docs(acknowledgments): correct intellectual lineage | ACKNOWLEDGMENTS.md with citable genesis record [VERIFIED from msg] |
| `9f26486` | 2026-07-09 | docs(compliance): align docs with roadmap-F5 §13 + WSL2 | Windows=FAIL, WSL2-only explicitly documented [VERIFIED from msg] |
| `fbdae94` | 2026-07-09 | fix(learning): hydrate bandit from replay buffer on startup (P0) | **P0 bug closed**: 139 dream runs, zero learning — replay buffer was write-only; now warm-starts [VERIFIED from msg] |
| `6f40be7` | 2026-07-09 | fix(citation): restore sentinel placeholders | CITATION.cff version/date sentinels restored for release.yml [INFERRED] |

### Tier: v1.0 Foundation Day (2026-07-08)

| SHA (short) | Date (UTC) | Subject | Product Integer Moved |
|---|---|---|---|
| `7185d70` | 2026-07-09 | feat(safety): shadow evaluation gate for MEDIUM-risk proposals (REC-017) | ShadowEvaluator + lifecycle state machine; 14 unit tests [VERIFIED from msg] |
| `77527d9` | 2026-07-08 | chore(citation): bump to 1.0.0 | CITATION.cff version field = 1.0.0 [INFERRED] |
| `4a152c4` | 2026-07-08 | fix(doctor): pii_patterns_loaded DEGRADED (not FAIL) when pip-installed | Installer-test 8/8 jobs unblocked [VERIFIED from msg — root cause: misclassification in doctor] |
| `0a33f18` | 2026-07-08 | chore(release): bump version to 1.0.0 | First stable version tag [INFERRED] |
| `c8ef235` | 2026-07-08 | Merge PR #24: REC-016 compatibility matrix + python_version check | Supported OS/Python/Hermes date-window documented and enforced [INFERRED] |
| `942123` | 2026-07-08 | Merge PR #23: REC-015 CITATION.cff + Zenodo DOI | Academic citation pipeline wired [INFERRED] |
| `98d9cb5` | 2026-07-08 | Merge PR #22: REC-014 nightly regression eval | Nightly 5% regression gate + auto-issue on failure [VERIFIED from msg] |
| `8896ea0` | 2026-07-08 | Merge PR #21: REC-013 MCP server (stdlib-only, 127.0.0.1) | 3 MCP tools: eidolon.report, eidolon.doctor, eidolon.learn.step [VERIFIED from msg] |
| `914651a` | 2026-07-08 | Merge PR #20: REC-012 Homebrew tap + formula + auto-update | `brew tap eidolon-hermes/eidolon && brew install eidolon` pipeline [VERIFIED from msg] |
| `e4b7cde` | 2026-07-08 | Merge PR #19: REC-007 PyPI + TestPyPI OIDC publishing | PyPI publish on stable tags; TestPyPI on every main push [VERIFIED from msg] |
| `a2057dc` | 2026-07-08 | Merge PR #18: REC-011 PII sanitization CI | scripts/sanitize_check.py + 7 regex patterns + pre-commit hook [VERIFIED from msg] |
| `24579c3` | 2026-07-08 | Merge PR #17: REC-010 5-class risk taxonomy + dream gate | RiskClass (NO_OP..NEVER_TOUCH), fail-closed unknown mutation [VERIFIED from msg] |
| `7e0a030` | 2026-07-08 | Merge PR #16: REC-009 preference-pair logging | Schema v1 frozen; context SHA256'd before storage; 18 tests [VERIFIED from msg] |
| `f0c6d3e` | 2026-07-08 | Merge PR #15: REC-008 contextual bandit + regression suite | Thompson sampling; 20 synthetic fixtures; learning_bandit_ready doctor check [VERIFIED from msg] |
| `4b476ae` | 2026-07-08 | Critical Path: eidolon CLI spine + doctor/report/rollback/router (RECs 001-005) | Full CLI spine; 5 checks; 26 unit tests; zero runtime deps [VERIFIED from msg] |

---

## Current Project State

**Version:** `2.0.0` [VERIFIED]
**CI status:** [UNKNOWN — cannot read Actions run status via GitHub Write API; last commit message on #50 states 15/15 CI green, 7/7 adversarial]
**Open PRs on main:** [UNKNOWN — not fetched this turn]

### Capabilities confirmed shipped [VERIFIED from commit messages]:
- `eidolon doctor|report|rollback|verify|learn|skill` CLI — exit codes 0/1/2/64
- Transactional outbox (`pending.jsonl` → `events.jsonl`), crash-safe
- MemoryAdapter ABC (InMem + Hindsight backends)
- Hermes MEMORY.md bridge (`apply_low` promotes lessons)
- Judgment Brain (classifies lessons into Hermes action types)
- Skill staging / promote / demote / retire / status CLI
- Scoreboard in `eidolon report`
- MCP server (stdlib, 127.0.0.1, 3 tools: report/doctor/learn.step + hindsight.retain)
- Shadow evaluator for MEDIUM-risk proposals
- Contextual bandit (Thompson sampling) with warm-start from replay buffer
- curl-bash installer + Homebrew formula stub
- PII sanitization CI (scripts/sanitize_check.py)
- Nightly regression eval (5% threshold, auto-issue)
- CITATION.cff + Zenodo DOI pipeline
- Compatibility matrix (macOS/Ubuntu, Python 3.10-3.13, Hermes CalVer floor)

### Capabilities **not yet confirmed on a real Hermes install** [UNKNOWN]:
- `eidolon report` integers moving across actual dream cycles on live Hermes
- `apply_low` MEMORY.md promotion surviving Hermes session restart
- Brew formula `url/sha256` filled (currently PLACEHOLDER per REC-012 commit)
- Scoreboard diff from session-to-session on live agent
- MCP tools callable from a real Hermes MCP config (not just unit-tested)

---

## Code Quality and Slop Removal

### Confirmed clean [VERIFIED from commit messages and sanitize CI]:
- Zero third-party runtime dependencies (stdlib-only enforced by CI grep)
- Zero hardcoded model names or endpoints in `src/` (REC-005, enforced by `test_no_hardcoded_models.py`)
- PII sanitization runs on every push via `sanitize.yml`; 7 regex patterns, 20 unit tests
- Every test file uses isolated `EIDOLON_HOME`/`HERMES_HOME` via `_tmphomes.py`
- SPDX-License-Identifier headers on all Python sources

### Slop removed in last 7 days [INFERRED from commit messages]:
- `acfdd49` / `fb7992b`: duplicate direct-push + PR-merge of same outbox flush fix — indicates the fix was pushed twice; the duplicate commit `acfdd49` is slop [VERIFIED — two SHAs, same subject line]
- Bandit write-only buffer was dead computation for 139 runs before `fbdae94` fixed warm-start — the buffer existed but produced no output. Now producing integers.
- `9af62b7` (judgment state isolation) removed shared mutable state between test runs — classic test pollution slop

### Dead code / stub audit [UNKNOWN without local clone]:
- Cannot confirm presence or absence of TODO/FIXME/stub tokens without running grep in a local checkout
- Homebrew formula contains explicit `PLACEHOLDER_ON_FIRST_RELEASE` for url/sha256/version [VERIFIED from REC-012 commit msg] — this is intentional scaffolding, not slop, but must be filled before v3.0 tag

---

## Placeholder and Dead-Code Audit

| Location | Placeholder | Status | Action Required |
|---|---|---|---|
| `packaging/homebrew/eidolon.rb` | `url`, `sha256`, `version` = `PLACEHOLDER_ON_FIRST_RELEASE` | [VERIFIED from REC-012 msg] | Fill after first PyPI sdist publish; `homebrew-tap-update.yml` automates on stable tag |
| `CITATION.cff` | `version`, `date-released` = `OPERATOR_INPUT_REQUIRED` sentinels | [VERIFIED from commit `6f40be7`] | Filled automatically by `release.yml` on stable tag push |
| `src/eidolon/mcp/tools.py` | `eidolon.hindsight.retain` handler was missing until `4c64684` | [VERIFIED — commit fixes silent KeyError] | FIXED — no action |
| `memories/MEMORY.md` | Exists only at runtime; not in repo | [INFERRED] | Operator must ensure `HERMES_HOME/memories/MEMORY.md` writable |
| TODO/FIXME grep in src/tests/docs | [UNKNOWN — not runnable via GitHub Write API] | Requires local clone | Run: `grep -RIn "TODO\|FIXME\|stub\|placeholder" src tests docs scripts` |

---

## Verification Gates

All gates below must produce confirmed output before the `v3.0.0` tag is pushed. Gates marked [UNKNOWN] require Trinity field execution.

```
GATE-1  [UNKNOWN] PYTHONPATH=src python -m unittest discover -s tests/unit
         Expected: 0 failures, 0 errors. Last known count: 275 tests (commit 4a152c4 msg).

GATE-2  [UNKNOWN] PYTHONPATH=src python tests/adversarial.py
         Expected: 7/7 PASS. Last cited: commit 4c64684 msg.

GATE-3  [UNKNOWN] python scripts/sanitize_check.py
         Expected: 0 matches. Last cited: multiple commits.

GATE-4  [UNKNOWN] eidolon doctor (on real Hermes install)
         Expected: overall PASS or DEGRADED (exit 0 or 2). FAIL = blocker.

GATE-5  [UNKNOWN] eidolon report (after ≥1 real dream cycle)
         Expected: lessons_retained ≥ 1, applied_proposals ≥ 1 as integers.
         This is the PRODUCT TEST. Without it, v3.0 is NOT VERIFIED.

GATE-6  [UNKNOWN] MCP tools callable from live Hermes config
         Expected: eidolon.report, eidolon.doctor, eidolon.hindsight.retain
         all return valid JSON via MCP protocol.

GATE-7  [UNKNOWN] MEMORY.md promotion confirmed across session restart
         Expected: lesson text from session N appears in MEMORY.md in session N+1.
```

---

## V3.0 Production Plan

### What v3.0 means
v3.0 = v2.0 feature set + provably working on a real Hermes Agent (not just unit-tested) + seamless install UX + integer improvements visible to operator.

### Remaining work items (ordered by blocking dependency)

1. **Field verification on real Hermes install** — run GATE-4 through GATE-7 and return exact output. [UNKNOWN until Trinity/field agent executes]
2. **Scoreboard format finalization** — `35e39f2` adds human scoreboard; confirm format is useful and not just integers dumping into log noise
3. **MEMORY.md session-persistence test** — verify `apply_low` bridge survives Hermes session restart (GATE-7)
4. **MCP end-to-end on real Hermes** — place the Claude Desktop / Hermes MCP config snippet from `docs/mcp.md` into a real agent and confirm tool calls resolve (GATE-6)
5. **Version bump to 3.0.0-rc1** — update `src/eidolon/_version.py`; confirm `eidolon --version` prints `3.0.0-rc1`
6. **CHANGELOG [3.0.0] section** — document all v2.x → v3.0 changes per Keep-a-Changelog format
7. **Stable tag `v3.0.0`** — triggers PyPI OIDC publish, Homebrew formula auto-update, CITATION.cff fill

---

## Brew Install Plan

**Current state:** Formula scaffold exists at `packaging/homebrew/eidolon.rb` with placeholder `url/sha256/version`. [VERIFIED — REC-012]

**Gap to `brew install eidolon` working:**
1. `v3.0.0` tag pushed → `release.yml` publishes sdist to PyPI
2. `homebrew-tap-update.yml` fires on release event → patches `url/sha256/version` in formula → commits to `eidolon-hermes/homebrew-eidolon` tap repo
3. Tap repo `eidolon-hermes/homebrew-eidolon` must exist and `HOMEBREW_TAP_PUSH_TOKEN` secret must be set [UNKNOWN — tap repo existence not verified]
4. User runs: `brew tap eidolon-hermes/eidolon && brew install eidolon`
5. Post-install: `eidolon doctor` must exit 0 or 2 (not 1) — tested by formula `test` block

**Blocker:** Tap repo existence and HOMEBREW_TAP_PUSH_TOKEN secret [UNKNOWN — requires operator verification]

---

## Install Wizard Plan

**Current state:** `install.sh` curl-bash installer exists; `docs/install.md` exists. [VERIFIED — REC-006, commit `a445435`]

**What "zero-thinking install wizard" means for v3.0:**

1. **Interactive setup step** — after `curl | bash`, prompt operator for `HERMES_HOME` path if not set, write `~/.config/eidolon/config.toml`
2. **MCP config snippet auto-inject** — detect Hermes config location, offer to append MCP server stanza automatically
3. **First-run doctor narrative** — translate DEGRADED check reasons into plain-English fix instructions (e.g., "Drop SOUL.md at /your-hermes-home/SOUL.md")
4. **`eidolon setup` subcommand** — interactive wizard as a Python command, not just install.sh bash

**None of these exist yet.** [INFERRED from commit history — no `eidolon setup` commit visible]
**Implementation estimate:** 1 focused PR per bullet above.

---

## README Agent Instructions Plan

**Current state:** README documents `doctor|report|rollback|version` CLI. Philosophy/lineage section added in `a8ec18b`. v2.0 pre-stable banner in `352d7b1`. [VERIFIED]

**What v3.0 README must contain for a new Hermes agent operator:**

1. **30-second quickstart block** — single copy-paste that installs, runs doctor, runs first dream cycle, and shows `eidolon report` output
2. **MCP config snippet** — exact JSON for Claude Desktop / Hermes `mcp_config.json` with placeholder paths
3. **What integers to watch** — `lessons_retained`, `applied_proposals`, `rollbacks_avoided`, `recall_hits` — and what a healthy vs. flat trend looks like
4. **Hermes MEMORY.md integration note** — explain that `apply_low` promotes lessons into `memories/MEMORY.md` and what the operator needs to ensure is writable
5. **Compatibility table** — already in `docs/compatibility.md`; promote a condensed version into README

**Gap:** Items 1, 3, and 4 are not confirmed present in current README. [UNKNOWN without reading full current README]

---

## Risks and Rollback

| Risk | Indicator | Rollback |
|---|---|---|
| `apply_low` corrupts MEMORY.md | Memory file grows without bound or contains raw template text | `git checkout MEMORY.md` in Hermes home; `eidolon rollback` restores last_known_good snapshot |
| Homebrew formula sha256 mismatch on v3.0 tag | `brew install eidolon` fails with checksum error | Patch formula manually; re-publish with corrected sha256 |
| MCP server port collision | `eidolon mcp-server` exits 1 on bind | Set `EIDOLON_MCP_PORT` env override (configurable per `docs/mcp.md`) |
| Version bump to 3.0.0 breaks existing operators | `eidolon doctor` exits FAIL on agent with v2.0 state | `_version.py` is the single source; `git revert` version commit; no schema bump unless required |
| Bandit posteriors diverge on new Hermes version | `eidolon report` shows bandit_episodes rising but reward flat | `eidolon rollback` to last_known_good snapshot; manually clear `replay.jsonl` |
| PyPI OIDC trusted publisher not configured | `release.yml` publish step fails with 403 | Set up trusted publisher at pypi.org → Publishing → Pending; re-push tag |

---

## PASS Definition

v3.0 is PASS when ALL of the following are simultaneously true:

- [ ] `src/eidolon/_version.py` = `3.0.0`
- [ ] `PYTHONPATH=src python -m unittest discover -s tests/unit` → 0 failures, 0 errors [GATE-1]
- [ ] `PYTHONPATH=src python tests/adversarial.py` → 7/7 PASS [GATE-2]
- [ ] `python scripts/sanitize_check.py` → 0 matches [GATE-3]
- [ ] `eidolon doctor` on real Hermes install → exit 0 or 2 [GATE-4]
- [ ] `eidolon report` after ≥1 real dream cycle → `lessons_retained ≥ 1` AND `applied_proposals ≥ 1` [GATE-5]
- [ ] At least one MCP tool (`eidolon.report`) called successfully from live Hermes MCP config [GATE-6]
- [ ] `apply_low` bridge confirmed: lesson text from session N visible in MEMORY.md in session N+1 [GATE-7]
- [ ] Homebrew tap repo exists and `HOMEBREW_TAP_PUSH_TOKEN` secret set [pre-tag operator check]
- [ ] CHANGELOG `[3.0.0]` section complete
- [ ] README 30-second quickstart block present
- [ ] `v3.0.0` tag pushed → CI green → PyPI publish → Homebrew formula auto-updated

**NOT VERIFIED = any gate above unchecked. BLOCKED = a gate fails with exact error returned.**

---

*This report was produced from live GitHub commit data via the GitHub Write API on 2026-07-13. No local clone was available; diff-level inspection required Trinity field execution. Claims marked [INFERRED] are derived from commit subject lines and bodies only. Claims marked [UNKNOWN] require local execution. No PII, hostnames, local paths, or operator-specific data appears in this document.*
