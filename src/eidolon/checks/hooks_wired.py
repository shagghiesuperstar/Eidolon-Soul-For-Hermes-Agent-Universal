"""Check: Hermes session-end hook + cron scheduling reference Eidolon skills.

Strategy: read config.yaml as text (stdlib-only; no PyYAML dependency) and
grep for the canonical skill directory names. This is a heuristic — full YAML
parsing is deferred until we take a hard PyYAML dep, which we're not doing yet.
"""

from __future__ import annotations

from eidolon.checks import CheckResult, DEGRADED, PASS
from eidolon.util.paths import hermes_home


HOOK_MARKERS = ("dream-cycle", "integrity-watchdog")


def check() -> CheckResult:
    cfg = hermes_home() / "config.yaml"
    if not cfg.exists():
        return CheckResult(
            name="hooks_wired",
            status=DEGRADED,
            reason="Hermes config.yaml missing; cannot verify hooks. See hermes_config.",
        )
    text = cfg.read_text(encoding="utf-8", errors="replace")
    missing = [m for m in HOOK_MARKERS if m not in text]
    if missing:
        return CheckResult(
            name="hooks_wired",
            status=DEGRADED,
            reason=(
                "Hermes config does not reference Eidolon skill(s): "
                + ", ".join(missing)
                + ". Run the install script or `hermes config set` to wire them."
            ),
        )
    return CheckResult(
        name="hooks_wired",
        status=PASS,
        reason="All Eidolon skill hooks referenced in Hermes config.",
    )
