# Eidolon compatibility matrix

Eidolon runs on a small, deliberately narrow support surface. The matrix
below is the source of truth; the `python_version` + `hermes_version` doctor
checks enforce it at runtime.

## Support policy

- **PASS** — combination is in the CI matrix and actively tested.
- **DEGRADED** — Eidolon may run, but the combination is either past its
  supported window or above the tested ceiling. `doctor` exits 2.
- **FAIL** — combination is unsupported. `doctor` exits 1.

## Matrix

| OS                         | Python 3.10                          | Python 3.11 | Python 3.12 | Python 3.13 | Python 3.14+ |
|----------------------------|--------------------------------------|-------------|-------------|-------------|--------------|
| macOS 13+ (Ventura+)       | PASS until 2027-01-01, then DEGRADED | PASS        | PASS        | PASS        | DEGRADED     |
| Ubuntu 22.04 / 24.04 LTS   | PASS until 2027-01-01, then DEGRADED | PASS        | PASS        | PASS        | DEGRADED     |
| Debian 12                  | PASS until 2027-01-01, then DEGRADED | PASS        | PASS        | PASS        | DEGRADED     |
| Alpine (musl)              | DEGRADED (untested libc)             | DEGRADED    | DEGRADED    | DEGRADED    | DEGRADED     |
| Windows (native)           | DEGRADED (WSL preferred)             | DEGRADED    | DEGRADED    | DEGRADED    | DEGRADED     |

Python < 3.10 is a hard **FAIL** on every OS; the installer refuses to run
and the `python_version` check enforces it again at doctor time.

## Hermes freshness

The `hermes_version` doctor check (shipped in PR #2) reasons over Hermes's
CalVer date, not a SemVer number. Policy:

- `hermes.version` within 90 days of today → **PASS**.
- 90–180 days stale → **DEGRADED** with a "run `hermes update`" hint.
- More than 180 days stale → still **DEGRADED** (never FAIL) — Hermes stale
  should not block Eidolon's core CLI.

## Sunset schedule for Python 3.10

| Date         | Behavior                                                            |
|--------------|---------------------------------------------------------------------|
| < 2027-01-01 | `python_version` returns **PASS** for 3.10 (upstream EOL is 2026-10; grace period). |
| ≥ 2027-01-01 | `python_version` returns **DEGRADED** with an "upgrade to 3.11+" hint. |

The deprecation date is a single module constant
(`eidolon.checks.python_version.PY_310_DEGRADED_AFTER`); tuning it is a
one-line change.

## Verify

```bash
PYTHONPATH=src python -m eidolon doctor --json \
  | jq '.checks[] | select(.name=="python_version" or .name=="compatibility_supported")'
```

Refs: `master_EIDOLON_roadmap(F5).md` § REC-016.
