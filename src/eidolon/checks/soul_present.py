"""Check: SOUL.md is present and non-empty at the repo root."""

from __future__ import annotations

from eidolon.checks import CheckResult, DEGRADED, FAIL, PASS
from eidolon.util.paths import repo_root


def check() -> CheckResult:
    p = repo_root() / "SOUL.md"
    if not p.exists():
        return CheckResult(
            name="soul_present",
            status=FAIL,
            reason="SOUL.md not found at repo root; identity contract missing.",
        )
    size = p.stat().st_size
    if size < 512:
        return CheckResult(
            name="soul_present",
            status=DEGRADED,
            reason=f"SOUL.md is unexpectedly small ({size} bytes); may be truncated.",
        )
    return CheckResult(
        name="soul_present",
        status=PASS,
        reason=f"SOUL.md present ({size} bytes).",
    )
