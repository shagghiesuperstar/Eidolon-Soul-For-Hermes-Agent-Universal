# SPDX-License-Identifier: Apache-2.0
"""Check: bandit subsystem is importable and has a non-empty arm registry.

DEGRADED if the registry is empty (system will still run, just no learning).
FAIL only on import error (real breakage).
"""

from __future__ import annotations

from eidolon.checks import CheckResult, DEGRADED, FAIL, PASS


def check() -> CheckResult:
    try:
        from eidolon.learning import arms as arms_mod
        from eidolon.learning.bandit import ThompsonBandit  # noqa: F401
        from eidolon.learning.replay import count as replay_count
    except ImportError as exc:
        return CheckResult(
            name="learning_bandit_ready",
            status=FAIL,
            reason=f"import_error:{type(exc).__name__}:{exc}",
        )

    registry = arms_mod.default_registry()
    n_arms = len(registry)
    if n_arms == 0:
        return CheckResult(
            name="learning_bandit_ready",
            status=DEGRADED,
            reason="arm registry empty; bandit inert until arms are registered",
        )

    try:
        n_episodes = replay_count()
    except OSError as exc:
        return CheckResult(
            name="learning_bandit_ready",
            status=DEGRADED,
            reason=f"replay_buffer_unreadable:{type(exc).__name__}",
            detail={"arms": str(n_arms)},
        )

    return CheckResult(
        name="learning_bandit_ready",
        status=PASS,
        reason=f"{n_arms} arms registered; {n_episodes} episodes logged.",
        detail={"arms": str(n_arms), "episodes": str(n_episodes)},
    )
