# Installing Eidolon

## One-line install

```bash
curl -fsSL https://raw.githubusercontent.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal/main/install.sh | bash
```

Expected exit codes:

| Code | Meaning |
|------|---------|
| `0` | PASS — Eidolon installed and `eidolon doctor` is fully green |
| `2` | DEGRADED — installed but running in reduced mode (e.g. no Hermes host present) |
| `1` | FAIL — installation or doctor check failed |

## Flags

| Flag | Description |
|------|-------------|
| `--dry-run` | Print what would happen; do not install anything |
| `--no-hermes` | Skip Hermes hook wiring (useful on CI or fresh VMs) |
| `--prefix=<path>` | Install to a custom prefix (default: `$HOME/.local`) |
| `--wheel-url=<url>` | Install from a specific wheel URL instead of PyPI (useful for testing) |
| `--version=<ver>` | Pin to a specific `eidolon-hermes` version on PyPI |

## Requirements

- Python 3.10, 3.11, 3.12, or 3.13
- `curl`
- macOS 14+ or Ubuntu 22.04/24.04

## Verify the install

```bash
eidolon doctor
```

On a fresh machine without Hermes installed, you will see `DEGRADED` — this is correct and expected. Install and configure [Hermes Agent](https://github.com/NousResearch/hermes) first to reach `PASS`.

## Uninstall

```bash
pip uninstall eidolon-hermes
```
