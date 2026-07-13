# Eidolon — Universal Self-Improvement Layer for Hermes Agents

> **v2.0.0 · pre‑stable** — under active development. PyPI release, stable
> DOI, and a formal upgrade path are tracked in the roadmap. The CLI and
> dream‑cycle are functional; expect breaking changes between minor versions
> until v2.1.

[![adversarial](https://github.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal/actions/workflows/adversarial.yml/badge.svg)](https://github.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal/actions/workflows/adversarial.yml)
[![installer-test](https://github.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal/actions/workflows/installer-test.yml/badge.svg)](https://github.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal/actions/workflows/installer-test.yml)
[![release](https://github.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal/actions/workflows/release.yml/badge.svg)](https://github.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal/actions/workflows/release.yml)
[![TestPyPI](https://img.shields.io/badge/TestPyPI-eidolon--hermes-blue?logo=pypi)](https://test.pypi.org/project/eidolon-hermes/)

Eidolon is a drop-in layer that hardens a Hermes agent's native dream, reflection, and memory loops into a disciplined, anti-fragile, self-improving system. Zero human babysitting: it runs autonomously, improves itself every session and on a schedule, and refuses to guess or gaslight. Deploy once and forget it.

## What it does

- **Clear SOUL.md contract** — a plain, zero-guess identity and operating contract the agent loads every session. No manual sealing or hashing to maintain.
- **Risk-gated self-improvement** — low-risk fixes auto-apply; high-risk changes are shadow-tested first; regressions auto-roll-back.
- **Dream cycle** — autonomous post-session and scheduled reflection that mines hindsight memory, extracts lessons, and proposes improvements.
- **Transactional outbox** — lessons and proposals are captured crash-safely to `$EIDOLON_HOME/outbox/pending.jsonl` and flushed to the event ledger exactly once. A crash between capture and flush replays cleanly on next run.
- **Integrity watchdog** — detects when upstream Hermes changes (skills paths, hooks, cron) break your setup and alerts the operator **once** per incident, without blocking sessions.

## Principles

1. **No guessing.** If a fact is unknown, the agent says so and verifies before acting.
2. **No gaslighting.** It never rewrites history or denies prior state.
3. **Anti-fragile.** Drift and breakage make the system stronger, not silent.
4. **Autonomous.** Self-improvement requires zero approvals and zero reminders.
5. **Immutable safety.** Security invariants are never modified by self-improvement.

## Philosophy & Lineage

Eidolon's design descends from prompt-distillation research (PromptQuine, Wang et al.,
ICML 2025), the Yao Meta-Skill doctrine for structured skill lifecycles, and the
soul-document pattern for intrinsic agent values. The learning path is bandit-based
exploration graduating to DPO — no PPO, no telemetry, no GUI. For the full
intellectual story, see [PHILOSOPHY.md](PHILOSOPHY.md) and
[ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md).

## Layout
```
SOUL.md                     Identity + operating contract (plain, no seal)
OPERATOR.md                 Human-facing setup + control guide
skills/dream-cycle/         Autonomous reflection + RL loop
skills/integrity-watchdog/  Drift detection + one-time alerting
src/eidolon/outbox.py       Crash-safe transactional outbox (REC-019)
tests/                      Adversarial harness + test plan
```

## The `eidolon` CLI

Eidolon ships a canonical command that never silently no-ops. Every subcommand
returns `0` on PASS, `2` on DEGRADED (loud reduced mode), and `1` on FAIL.

```
eidolon doctor              # preflight checks (JSON via --json, --model-check)
eidolon verify              # post-install end-to-end CLI smoke test (--json, --strict)
eidolon report --since 24h  # measurable deltas: sessions, lessons, proposals, rollbacks
eidolon rollback --dry-run  # restore from last-known-good snapshot
eidolon version             # print semver
```

Every Eidolon component emits structured events into `$EIDOLON_HOME/events.jsonl`
(default: `~/.hermes/state/eidolon/events.jsonl`). `eidolon report` reads that
log and prints integers you can plot. Empty state prints zeros with a first-run
banner — never `null`, never `N/A`.

### `eidolon report` — human-readable scoreboard

Running `eidolon report` with no flags prints a full human-readable output
including a four-counter **scoreboard** at the bottom:

```
Eidolon report — no events in the requested window yet.
This is expected on a fresh install; the first dream-cycle run will
populate metrics. Verify install with `eidolon doctor`.

  ── scoreboard ──
  Lessons extracted   :      0
  Proposals applied   :      0
  Skills staged       :      0
  Inbox cleared       :      0
```

After the first dream-cycle run the output includes windowed metrics and the
scoreboard reflects real persistent state:

```
Eidolon report — window: 24h
  sessions observed        :      3  (+3)
  lessons added            :     12  (+12)
  proposals generated      :      4  (+4)
  proposals applied        :      2  (+2)
  ...

  ── scoreboard ──
  Lessons extracted   :     12
  Proposals applied   :      2
  Skills staged       :      1
  Inbox cleared       :      9
```

The four scoreboard counters are **real persistent-state integers** (not windowed
event counts): `lessons_extracted` counts persisted Hindsight JSONL entries,
`proposals_applied` is the Law-of-Done judgment counter, `skills_staged` counts
`*.md` files under `$HERMES_HOME/skills/_eidolon_staging`, and `inbox_cleared`
is lessons with `done=True`.

### `eidolon report --json` — machine-readable output

Pass `--json` to get raw JSON on stdout (schema 1, stable):

```bash
eidolon report --json
```

Output format (all fields are integers >= 0; `schema` is always `1`):

```json
{
  "schema": 1,
  "window": "24h",
  "empty_state": true,
  "sessions_observed": 0,
  "lessons_added": 0,
  "proposals_generated": 0,
  "proposals_applied": 0,
  "rollback_count": 0,
  "inference_requests": 0,
  "inference_degraded": 0,
  "lessons_extracted": 0,
  "skills_staged": 0,
  "inbox_cleared": 0,
  "delta": { ... },
  "has_baseline": false
}
```

Consumers must pin `schema=1` and fail loudly on mismatch. The `--json` schema
is not modified by this change.

## Install

One-liner (macOS + Linux + WSL2, Python 3.10–3.13):

```
curl -fsSL https://raw.githubusercontent.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal/main/install.sh | bash
```

**Windows:** Native Windows is not supported. Use WSL2 (Ubuntu 22.04 or
24.04 LTS), since Hermes Agent itself runs under WSL2.

What the installer does:

1. Detects Python 3.10–3.13 (aborts loudly if absent — no silent guessing).
2. `pip install --user` the `eidolon-hermes` package from the pinned git ref.
3. Runs `eidolon doctor` at the end. If doctor says FAIL, the installer
   exits non-zero. If DEGRADED (no host Hermes yet), install succeeds and
   the operator is told exactly why.

Once REC-007 (PyPI publish) lands, the one-liner becomes `pip install eidolon-hermes`.

### Homebrew (macOS + Linuxbrew)

After the first stable release lands on PyPI, Eidolon is also available via a Homebrew tap:

```
brew tap eidolon-hermes/eidolon
brew install eidolon
```

See [`docs/install-brew.md`](docs/install-brew.md) for details, upgrade, and uninstall. The formula lives at `packaging/homebrew/eidolon.rb` in this repo; the tap repo mirrors it on every release.

Installer environment overrides (all optional):

| Var | Purpose | Default |
|---|---|---|
| `EIDOLON_REF` | Git ref to install | `main` |
| `EIDOLON_METHOD` | `pip` or `src` (clone-then-install) | `pip` |
| `EIDOLON_PYTHON` | Interpreter to bind to | Auto-detected |
| `EIDOLON_SKIP_DOCTOR` | `1` skips the final doctor gate | `0` |
| `HERMES_HOME` | Host Hermes home | `$HOME/.hermes` |
| `EIDOLON_HOME` | Eidolon state root | `$HERMES_HOME/state/eidolon` |

After install, verify anytime:

```
eidolon doctor            # environment health
eidolon verify --strict   # end-to-end CLI smoke; --strict promotes DEGRADED to exit 2
python tests/adversarial.py                              # S1–S3 guarantees
PYTHONPATH=src python -m unittest discover -s tests/unit # full unit suite
```

Don't want the installer script? Drop the `skills/` directory into your
Hermes skills path and point your sessionend hook + cron at the
dream-cycle and integrity-watchdog handlers. See `OPERATOR.md`.

## PII sanitization hook (REC-011)

CI runs `scripts/sanitize_check.py` on every PR. To catch leaks locally
before they hit CI, wire up the pre-commit hook once per clone:

```bash
git config core.hooksPath .githooks
```

Add a new pattern by appending to `.sanitize-patterns.yml`; the reader is
stdlib-only. Every pattern MUST ship with `<name>_positive.txt` and
`<name>_clean.txt` fixtures under `tests/fixtures/sanitize_selftest/`.
Bypass with `git commit --no-verify` only in emergencies — CI still enforces.

## Releases & DOI

Eidolon uses SemVer (`vX.Y.Z`); host Hermes uses CalVer. The `hermes_version`
doctor check reasons over dates, not SemVer — see
`src/eidolon/checks/hermes_version.py`. Stable tags are minted on Zenodo
(`.zenodo.json` at repo root is the source of truth). Prereleases skip DOI
minting. See [RELEASING.md](RELEASING.md) for the full tagging + DOI policy.

## Cite this

If Eidolon supports academic work, cite it via
[`CITATION.cff`](CITATION.cff). BibTeX and APA-style examples live in
[`docs/citing.md`](docs/citing.md). GitHub renders the CFF as a
"Cite this repository" widget on the project page.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
