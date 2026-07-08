# SPDX-License-Identifier: Apache-2.0
"""Provider-agnostic inference layer.

Public surface:
- InferenceRouter — resolves (tier, capabilities) -> concrete host provider.
- tiers           — canonical capability sets.
- RouterError     — raised when the router cannot even initialise.

Design constraint (REC-005, non-negotiable):
- No module in this package may reference a specific model or endpoint by name.
  Every string a caller supplies is a *capability requirement*, and every
  string this package returns is a Hermes-configured *provider key*, resolved
  from the host's provider_models_cache.json at call time.
- CI grep enforces this. See tests/unit/test_no_hardcoded_models.py.
"""

from eidolon.inference.router import InferenceRouter, RouterError, ProviderMatch
from eidolon.inference import tiers

__all__ = ["InferenceRouter", "RouterError", "ProviderMatch", "tiers"]
