"""Check: host Hermes config.yaml is reachable and parseable.

DEGRADED (not FAIL) when Hermes is not installed: Eidolon can still run its own
CLI, report empty state, and emit events. It just can't self-improve until a
host is present.
"""

from __future__ import annotations

from eidolon.checks import CheckResult, DEGRADED, FAIL, PASS
from eidolon.util.paths import hermes_home


def check() -> CheckResult:
    home = hermes_home()
    cfg = home / "config.yaml"
    if not home.exists():
        return CheckResult(
            name="hermes_config",
            status=DEGRADED,
            reason=f"Host Hermes home ({home}) does not exist; Eidolon runs in reduced mode.",
        )
    if not cfg.exists():
        return CheckResult(
            name="hermes_config",
            status=DEGRADED,
            reason="config.yaml missing from Hermes home; run `hermes update` to restore defaults.",
        )
    try:
        text = cfg.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return CheckResult(
            name="hermes_config",
            status=FAIL,
            reason=f"Cannot read Hermes config.yaml: {type(exc).__name__}",
        )
    if not text.strip():
        return CheckResult(
            name="hermes_config",
            status=DEGRADED,
            reason="Hermes config.yaml is empty.",
        )
    return CheckResult(
        name="hermes_config",
        status=PASS,
        reason=f"Hermes config.yaml readable ({len(text)} bytes).",
    )
