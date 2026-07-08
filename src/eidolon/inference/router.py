# SPDX-License-Identifier: Apache-2.0
"""Provider-agnostic inference router (REC-005).

Contract:
- Router.from_hermes() reads $HERMES_HOME/provider_models_cache.json.
- The file's TOP-LEVEL KEYS are the only valid provider identifiers. This
  matches the lesson learned from the `custom:ds4` incident (see SOUL/state
  lessons): only real, resolvable provider keys are accepted.
- resolve(tier, requires) returns a ProviderMatch or None. It NEVER guesses
  a model. It NEVER falls back to a hardcoded default.
- All resolution attempts are recorded to the events log as either
  inference.request (PASS) or inference.degraded (DEGRADED).

Schema of provider_models_cache.json (host-owned; we tolerate variations):

    {
      "<provider-key>": {
        "tier": "A" | "B" | "C",
        "capabilities": ["json_mode", "tool_use", ...],
        "context_window": 32000,
        ...opaque host fields we do not read...
      },
      ...
    }

Backward compat: if `tier` is absent, the router infers `A` (safe default);
if `capabilities` is absent, it treats the provider as offering only the
implicit minimum (no `json_mode`), which excludes it from Tier B+ resolutions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import FrozenSet, Iterable, Optional, Set

from eidolon.inference.tiers import (
    CAP_JSON,
    CTX_MIN,
    TIER_A,
    default_capabilities,
)
from eidolon.util import events
from eidolon.util.paths import hermes_home


CACHE_FILENAME = "provider_models_cache.json"

_TIER_ORDER = {TIER_A: 0, "B": 1, "C": 2}


class RouterError(RuntimeError):
    """Raised when the router cannot even initialise (missing/corrupt cache)."""


@dataclass(frozen=True)
class ProviderMatch:
    """A resolved provider that meets a caller's capability requirements.

    Callers pass this back to the host Hermes to actually execute inference —
    Eidolon does not perform HTTP itself. The `provider` field is the top-level
    key in provider_models_cache.json; the host knows how to call it.
    """

    provider: str
    tier: str
    capabilities: FrozenSet[str] = field(default_factory=frozenset)
    context_window: int = 0


class InferenceRouter:
    def __init__(self, providers: dict[str, dict]):
        # Provider entries are already normalised (see _normalise).
        self._providers: dict[str, dict] = providers

    # ------------------------------------------------------------------ ctors
    @classmethod
    def from_hermes(cls) -> "InferenceRouter":
        path = hermes_home() / CACHE_FILENAME
        if not path.exists():
            # DEGRADED, not FAIL: host may not be installed yet.
            return cls({})
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RouterError(f"cannot read {CACHE_FILENAME}: {type(exc).__name__}") from exc
        if not isinstance(raw, dict):
            raise RouterError(f"{CACHE_FILENAME} root must be an object; got {type(raw).__name__}")
        return cls({k: cls._normalise(v) for k, v in raw.items() if isinstance(v, dict)})

    @classmethod
    def from_dict(cls, providers: dict[str, dict]) -> "InferenceRouter":
        """Test hook: build a router from an in-memory provider map."""
        return cls({k: cls._normalise(v) for k, v in providers.items()})

    @staticmethod
    def _normalise(entry: dict) -> dict:
        return {
            "tier": entry.get("tier", TIER_A),
            "capabilities": frozenset(entry.get("capabilities", ()) or ()),
            "context_window": int(entry.get("context_window", 0) or 0),
        }

    # -------------------------------------------------------------- accessors
    def providers(self) -> Iterable[str]:
        return list(self._providers.keys())

    # ------------------------------------------------------------ resolution
    def resolve(
        self,
        *,
        tier: str,
        requires: Iterable[str] | None = None,
        min_context: int | None = None,
    ) -> Optional[ProviderMatch]:
        """Return a ProviderMatch that meets the requirements, or None.

        Never guesses. If the host has no matching provider, returns None
        and emits an `inference.degraded` event with a reason. Callers must
        handle None by degrading loudly.
        """
        need_caps: Set[str] = set(requires) if requires is not None else set(default_capabilities(tier))
        need_ctx: int = min_context if min_context is not None else CTX_MIN.get(tier, 0)

        candidates: list[tuple[int, str, dict]] = []
        for provider, entry in self._providers.items():
            entry_tier = entry["tier"]
            # Provider must be at least the requested tier.
            if _TIER_ORDER.get(entry_tier, -1) < _TIER_ORDER.get(tier, 0):
                continue
            if not need_caps.issubset(entry["capabilities"]):
                continue
            if entry["context_window"] < need_ctx:
                continue
            # Prefer the exact tier (avoid over-provisioning a Tier C for a
            # Tier A request). Tie-break by provider name for determinism.
            distance = _TIER_ORDER[entry_tier] - _TIER_ORDER.get(tier, 0)
            candidates.append((distance, provider, entry))

        if not candidates:
            events.emit(
                "inference.degraded",
                events.STATUS_DEGRADED,
                source="inference.router",
                requested_tier=tier,
                requested_caps=sorted(need_caps),
                requested_min_context=need_ctx,
                providers_seen=sorted(self._providers.keys()),
                reason="no_provider_meets_requirements",
            )
            return None

        candidates.sort(key=lambda c: (c[0], c[1]))
        _, provider, entry = candidates[0]
        match = ProviderMatch(
            provider=provider,
            tier=entry["tier"],
            capabilities=entry["capabilities"],
            context_window=entry["context_window"],
        )
        events.emit(
            "inference.request",
            events.STATUS_PASS,
            source="inference.router",
            requested_tier=tier,
            resolved_provider=provider,
            resolved_tier=entry["tier"],
        )
        return match
