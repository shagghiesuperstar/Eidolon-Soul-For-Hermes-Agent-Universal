# SPDX-License-Identifier: Apache-2.0
"""Check: host Hermes release freshness.

Hermes upstream uses CalVer (`vYYYY.M.D[.patch]`), not SemVer, so
"current stable minus one minor" is not defined. Instead we enforce a
**date-based freshness window**: if the installed Hermes version string
parses as a date older than HERMES_MIN_DATE (a trailing ~90-day window),
we emit DEGRADED — never FAIL. Eidolon must still run against older
Hermes, just warn the operator that we haven't validated compatibility.

Precedence for reading the version:
1. $HERMES_VERSION env override (useful for testing + non-standard installs)
2. `version:` key in $HERMES_HOME/config.yaml
3. `$HERMES_HOME/VERSION` file (one line, e.g. `v2026.7.1`)

If none are found, we return DEGRADED (not FAIL) — Eidolon can still run
its own CLI without knowing the host version.
"""

from __future__ import annotations

import datetime as _dt
import os
import re
from pathlib import Path
from typing import Optional, Tuple

from eidolon.checks import CheckResult, DEGRADED, PASS
from eidolon.util.paths import hermes_home

# Trailing freshness window. Bump this constant in the same PR that ships each
# Eidolon release so the check stays a trailing-90-day window automatically.
# Anything older than HERMES_MIN_DATE surfaces as DEGRADED.
HERMES_MIN_DATE: _dt.date = _dt.date(2026, 4, 8)

# CalVer pattern: v2026.7.1 or v2026.5.29.2 (optional .patch)
_CALVER_RE = re.compile(r"^v?(\d{4})\.(\d{1,2})\.(\d{1,2})(?:\.(\d+))?$")


def parse_hermes_version(raw: str) -> Optional[_dt.date]:
    """Parse a Hermes CalVer string into a date.

    Returns None if the string does not match the CalVer pattern or the
    parsed year/month/day are not a valid calendar date.
    """
    if not raw:
        return None
    m = _CALVER_RE.match(raw.strip())
    if not m:
        return None
    year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return _dt.date(year, month, day)
    except ValueError:
        return None


def _read_version_from_config(cfg: Path) -> Optional[str]:
    """Best-effort scan for a `version:` line without pulling in PyYAML.

    Stdlib-first policy — we accept that a version buried in a nested mapping
    won't be found. Users can set $HERMES_VERSION to override.
    """
    try:
        text = cfg.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("version:"):
            # Handles: `version: v2026.7.1`  and  `version: "v2026.7.1"`
            value = stripped.split(":", 1)[1].strip().strip("\"'")
            return value or None
    return None


def _resolve_version() -> Tuple[Optional[str], str]:
    """Return (raw_version_string, source_label)."""
    env = os.environ.get("HERMES_VERSION")
    if env:
        return env, "env:HERMES_VERSION"

    home = hermes_home()
    cfg = home / "config.yaml"
    if cfg.exists():
        v = _read_version_from_config(cfg)
        if v:
            return v, "config.yaml:version"

    version_file = home / "VERSION"
    if version_file.exists():
        try:
            v = version_file.read_text(encoding="utf-8", errors="replace").strip()
            if v:
                return v, "VERSION file"
        except OSError:
            pass

    return None, "none"


def check() -> CheckResult:
    raw, source = _resolve_version()
    if raw is None:
        return CheckResult(
            name="hermes_version",
            status=DEGRADED,
            reason=(
                "Could not determine host Hermes version. Set $HERMES_VERSION, "
                "add a `version:` key to config.yaml, or drop a VERSION file in "
                "$HERMES_HOME. Eidolon runs without this check but cannot warn "
                "on stale hosts."
            ),
        )

    parsed = parse_hermes_version(raw)
    if parsed is None:
        return CheckResult(
            name="hermes_version",
            status=DEGRADED,
            reason=(
                f"Hermes version string {raw!r} (from {source}) does not match "
                "CalVer pattern vYYYY.M.D[.patch]. Cannot enforce freshness."
            ),
            detail={"raw": raw, "source": source},
        )

    if parsed < HERMES_MIN_DATE:
        days = (HERMES_MIN_DATE - parsed).days
        return CheckResult(
            name="hermes_version",
            status=DEGRADED,
            reason=(
                f"Host Hermes {raw} is older than the {HERMES_MIN_DATE.isoformat()} "
                f"freshness floor by {days} days. Eidolon will still run but "
                "compatibility with this Hermes release is untested. See "
                "RELEASING.md for the freshness policy."
            ),
            detail={
                "raw": raw,
                "parsed": parsed.isoformat(),
                "floor": HERMES_MIN_DATE.isoformat(),
                "days_stale": str(days),
                "source": source,
            },
        )

    return CheckResult(
        name="hermes_version",
        status=PASS,
        reason=f"Host Hermes {raw} within freshness window (floor {HERMES_MIN_DATE.isoformat()}).",
        detail={"raw": raw, "parsed": parsed.isoformat(), "source": source},
    )
