# Installing Eidolon

## One-line install

```bash
curl -fsSL https://raw.githubusercontent.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal/main/install.sh | bash
```

The installer exits with:

| Code | Meaning |
|------|---------|
| `0` | PASS — fully wired and doctor is green |
| `2` | DEGRADED — installed but Hermes not present or hooks not wired |
| `1` | FAIL — installation could not complete |
| `64` | Usage error — unknown argument |

## Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--dry-run` | off | Print what would be installed and exit 0; no changes made |
| `--no-hermes` | off | Skip the Hermes hook-wiring step (exits DEGRADED) |
| `--prefix=<path>` | `$HOME/.local` | Installation prefix for the `eidolon` binary |
| `--wheel-url=<url>` | *(PyPI)* | Install from a specific wheel URL or `file://` path |
| `--version=<ver>` | `latest` | Pin a specific `eidolon-hermes` version from PyPI |

## Examples

```bash
# Dry run (no changes)
bash install.sh --dry-run

# Install without touching Hermes hooks
bash install.sh --no-hermes

# Install a specific version
bash install.sh --version=1.2.3

# Install from a locally built wheel (CI / offline)
bash install.sh --wheel-url=file:///path/to/eidolon_hermes-1.0.0-py3-none-any.whl --no-hermes

# Custom prefix
bash install.sh --prefix=/usr/local
```

## Prerequisites

- Python 3.10, 3.11, 3.12, or 3.13
- `curl` (for remote installs)
- macOS 14+ or Ubuntu 22.04+

## What the installer does

1. **Verifies prerequisites** — checks Python version.
2. **Installs `eidolon-hermes`** — via PyPI or a provided wheel URL.
3. **Wires Hermes hooks** — skipped (DEGRADED) if Hermes is not installed; full wiring lands in REC-017.
4. **Runs `eidolon doctor`** — mirrors the exit code so your CI knows the install health.

## Idempotency

Running the installer twice on the same machine returns the same exit code.
`pip install --user` is idempotent; the hook-wiring step is a no-op if
already wired.

## Local development hook

To enable the pre-commit PII scanner:

```bash
git config core.hooksPath .githooks
```
