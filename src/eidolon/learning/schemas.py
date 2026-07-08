# SPDX-License-Identifier: Apache-2.0
"""Versioned dataclass schemas for the learning subsystem.

INVARIANT: `schema = 1` is frozen. Adding, removing, renaming, or retyping any
field requires a new REC with a migration path. Downstream consumers (REC-009
preference logging, REC-019 DPO training) pin schema=1 and fail loudly on
mismatch.

If you need a new field, add REC-XXX/schema-v2 and bump the constant in ONE
place at the top of this file. Do not add optional fields ad-hoc.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict


SCHEMA = 1


@dataclass
class EpisodeRecord:
    """One bandit episode: an arm was drawn, evaluated, and rewarded.

    Fields (frozen):
      schema        : int   — schema version (=1)
      ts            : float — epoch seconds when the episode was logged
      episode_id    : str   — deterministic id: sha256(seed|iteration)[:16]
      arm_id        : str   — the arm the bandit selected
      context_hash  : str   — sha256 of the context, never the raw context
      reward        : float — in [0.0, 1.0]; regression pass rate
      posterior_a   : float — Beta.alpha AFTER this episode's update
      posterior_b   : float — Beta.beta AFTER this episode's update
    """

    schema: int = SCHEMA
    ts: float = 0.0
    episode_id: str = ""
    arm_id: str = ""
    context_hash: str = ""
    reward: float = 0.0
    posterior_a: float = 1.0
    posterior_b: float = 1.0

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ArmDefinition:
    """A single prompt-phrasing arm.

    v1 constraint: arms are Python string templates with `{placeholder}`
    positions. The bandit selects `arm_id`, not the substituted content.

    Fields (frozen):
      schema     : int  — schema version (=1)
      arm_id     : str  — unique across all arms; stable across releases
      family     : str  — logical grouping (e.g. "system_prompt_style")
      template   : str  — the prompt template body; may contain {slots}
      tags       : list[str] — free-form structural tags (never operator data)
    """

    schema: int = SCHEMA
    arm_id: str = ""
    family: str = ""
    template: str = ""
    tags: list[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)
