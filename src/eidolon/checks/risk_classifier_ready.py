# SPDX-License-Identifier: Apache-2.0
"""Check: risk classifier is importable and NEVER_TOUCH_PATHS is non-empty."""

from __future__ import annotations

from eidolon.checks import CheckResult, DEGRADED, FAIL, PASS


def check() -> CheckResult:
    try:
        from eidolon.safety.risk import NEVER_TOUCH_PATHS, RiskClass, classify
    except ImportError as exc:
        return CheckResult(
            name="risk_classifier_ready",
            status=FAIL,
            reason=f"import_error:{type(exc).__name__}:{exc}",
        )

    n = len(NEVER_TOUCH_PATHS)
    if n == 0:
        return CheckResult(
            name="risk_classifier_ready",
            status=DEGRADED,
            reason="NEVER_TOUCH_PATHS is empty; classifier ceiling is inert",
        )

    # Sanity: enum has exactly 5 members, ordinal.
    members = list(RiskClass)
    if len(members) != 5:
        return CheckResult(
            name="risk_classifier_ready",
            status=FAIL,
            reason=f"RiskClass must have exactly 5 members; got {len(members)}",
        )

    return CheckResult(
        name="risk_classifier_ready",
        status=PASS,
        reason=f"5-class RiskClass loaded; {n} NEVER_TOUCH patterns.",
        detail={"patterns": str(n), "classes": str(len(members))},
    )
