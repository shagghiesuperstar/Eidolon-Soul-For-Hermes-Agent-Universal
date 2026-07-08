# Installing Eidolon with Homebrew

## Prerequisites

- macOS or Linux with [Homebrew](https://brew.sh/) installed.
- Python 3.11+ is installed automatically as a Homebrew dependency.

## Install

```bash
brew tap eidolon-hermes/eidolon
brew install eidolon
```

The `brew tap` command adds the `eidolon-hermes/homebrew-eidolon` third-party
tap. `brew install eidolon` fetches the formula, creates an isolated
virtualenv under `$(brew --prefix)/opt/eidolon/libexec`, installs the
`eidolon-hermes` wheel into it, and symlinks the `eidolon` entry point into
your `$PATH`.

## Verify

```bash
eidolon --version
# eidolon <SemVer>

eidolon doctor --json
# JSON with 10+ checks; overall status is PASS or DEGRADED, never FAIL
```

## Upgrade

```bash
brew update
brew upgrade eidolon
```

Homebrew tracks new tags on the tap repo. The tap's own release workflow
(see below) auto-updates `Formula/eidolon.rb` on every Eidolon release, so
`brew upgrade` picks up new versions the same day.

## Uninstall

```bash
brew uninstall eidolon
brew untap eidolon-hermes/eidolon
```

Eidolon's state directory (`~/.eidolon/`) is NOT removed by `brew uninstall`.
To wipe local state:

```bash
rm -rf ~/.eidolon
```

## Under the hood

- **Tap repo**: `github.com/eidolon-hermes/homebrew-eidolon`. The formula
  path there is `Formula/eidolon.rb`, a mirror of
  `packaging/homebrew/eidolon.rb` in this main repo.
- **Formula shape**: Python virtualenv install via
  `Language::Python::Virtualenv`. Depends on `python@3.11`. No custom
  bottling — pip installs from a PyPI sdist inside the virtualenv.
- **No transitive deps**: eidolon-hermes has zero runtime Python
  dependencies (stdlib-first policy enforced by `pyproject.toml`), so no
  `resource` blocks appear in the formula.
- **Auto-update on release**: `.github/workflows/release.yml` in this repo,
  on every stable `v*` tag, updates the formula's `url`, `sha256`, and
  `version` and opens a PR against the tap repo.

## Troubleshooting

### `brew install eidolon` fails with sha256 mismatch

If you see `SHA256 mismatch` and the expected value is
`PLACEHOLDER_ON_FIRST_RELEASE_...`, the tap has not yet received its first
real release. The formula file in this repo ships with a placeholder that
the release workflow overwrites on first stable tag. Wait for the first
stable Eidolon release, then `brew update && brew install eidolon`.

### `brew audit --strict eidolon-hermes/eidolon/eidolon` reports errors

Before the first stable release, audit fails on the placeholder `sha256`
and unresolvable `url`. This is expected — see above. After the first
release, audit MUST pass; if it doesn't, file an issue on the tap repo.

### `eidolon doctor` reports FAIL

Doctor FAIL indicates a broken installation, not a Homebrew issue.
See [`OPERATOR.md`](../OPERATOR.md) for triage.

## Not on Homebrew yet

If you need Eidolon before the tap is published:

- `pip install eidolon-hermes` (once REC-007 ships the first release)
- `./install.sh` — the canonical installer, always up-to-date on `main`.

## References

- Roadmap § 8.12 (REC-012)
- Homebrew Python formula guide: <https://docs.brew.sh/Python-for-Formula-Authors>
