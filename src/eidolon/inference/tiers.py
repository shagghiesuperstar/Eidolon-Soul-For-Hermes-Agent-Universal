"""Canonical capability tiers.

Tiers are *requirements*, not model identities. A provider that meets the
tier's capability set is a valid resolution — regardless of vendor.

Tier A: any working host-configured provider with structured output + 8k ctx.
Tier B: mid-tier local or mid-tier API, 16k ctx, JSON mode.
Tier C: large local or frontier API, 32k ctx, JSON mode + tool_use.
"""

from __future__ import annotations

from typing import FrozenSet

TIER_A = "A"
TIER_B = "B"
TIER_C = "C"

# Capabilities the router understands. Any additional string a caller passes
# through `requires=` is treated as an opaque required feature that the host
# provider entry must declare.
CAP_JSON = "json_mode"
CAP_TOOLS = "tool_use"

MIN_CAPABILITIES: FrozenSet[str] = frozenset({CAP_JSON})
MID_CAPABILITIES: FrozenSet[str] = frozenset({CAP_JSON})
HIGH_CAPABILITIES: FrozenSet[str] = frozenset({CAP_JSON, CAP_TOOLS})

# Minimum context window (tokens) per tier. Router uses these when the caller
# does not pin `min_context` explicitly.
CTX_MIN: dict[str, int] = {
    TIER_A: 8_000,
    TIER_B: 16_000,
    TIER_C: 32_000,
}


def default_capabilities(tier: str) -> FrozenSet[str]:
    return {
        TIER_A: MIN_CAPABILITIES,
        TIER_B: MID_CAPABILITIES,
        TIER_C: HIGH_CAPABILITIES,
    }.get(tier, MIN_CAPABILITIES)
