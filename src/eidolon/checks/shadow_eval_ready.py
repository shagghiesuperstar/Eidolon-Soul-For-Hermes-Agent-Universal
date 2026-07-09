# SPDX-License-Identifier: Apache-2.0
"""Check: ShadowEvaluator is importable and instantiable with default threshold."""

from __future__ import annotations

from eidolon.checks import CheckResult, DEGRADED, FAIL, PASS


def check() -> CheckResult:
    try:
        from eidolon.skills.shadow import ShadowEvaluator, DEFAULT_THRESHOLD
    except ImportError as exc:
        return CheckResult(
            name="shadow_eval_ready",
            status=FAIL,
            reason=f"import_error:{type(exc).__name__}:{exc}",
        )

    try:
        ev = ShadowEvaluator()
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name="shadow_eval_ready",
            status=FAIL,
            reason=f"instantiation_error:{type(exc).__name__}:{exc}",
        )

    if not (0.0 < ev.threshold <= 1.0):
        return CheckResult(
            name="shadow_eval_ready",
            status=DEGRADED,
            reason=f"threshold out of useful range: {ev.threshold}",
        )

    return CheckResult(
        name="shadow_eval_ready",
        status=PASS,
        reason=f"ShadowEvaluator ready; default threshold={DEFAULT_THRESHOLD}",
        detail={"threshold": str(DEFAULT_THRESHOLD)},
    )
