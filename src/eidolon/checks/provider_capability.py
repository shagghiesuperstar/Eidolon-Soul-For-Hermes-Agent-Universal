"""Check: at least one inference provider satisfies Tier A capabilities.

This never names a specific model. It asks the inference router: given the
minimum capability set (context >= 8k, JSON-friendly output), can *any*
provider configured in provider_models_cache.json satisfy it?

DEGRADED means: Eidolon runs in heuristic-only mode. Regex sanitization,
template reports, and events all still work. Reflection/proposals do not.
"""

from __future__ import annotations

from eidolon.checks import CheckResult, DEGRADED, FAIL, PASS
from eidolon.inference.router import InferenceRouter, RouterError
from eidolon.inference.tiers import TIER_A, MIN_CAPABILITIES


def check() -> CheckResult:
    try:
        router = InferenceRouter.from_hermes()
    except RouterError as exc:
        return CheckResult(
            name="provider_capability",
            status=DEGRADED,
            reason=f"Inference router could not initialise: {exc}. Running heuristic-only.",
        )
    match = router.resolve(tier=TIER_A, requires=MIN_CAPABILITIES)
    if match is None:
        return CheckResult(
            name="provider_capability",
            status=DEGRADED,
            reason=(
                "No configured Hermes provider meets minimum capabilities "
                "(context>=8k, structured output). Eidolon runs in heuristic-only mode."
            ),
            detail={"tier": TIER_A, "providers_seen": ",".join(sorted(router.providers()))},
        )
    return CheckResult(
        name="provider_capability",
        status=PASS,
        reason=f"Provider tier '{match.tier}' available.",
        detail={"tier": match.tier, "capabilities": ",".join(sorted(match.capabilities))},
    )
