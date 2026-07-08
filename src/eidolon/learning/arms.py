# SPDX-License-Identifier: Apache-2.0
"""Arm registry for the v1 bandit.

Scope (per roadmap § REC-008): PROMPT-PHRASING ARMS ONLY.

Tool ordering, skill selection, and mutable-config arms are OUT OF SCOPE
until REC-017's shadow evaluation lands. Adding a non-prompt-phrasing arm
here is a policy violation; the audit hook in `handler.py` will refuse to
auto-apply anything sourced from a non-`prompt_phrasing` family.

The registry is populated at import time with a small seed set that the
regression suite fixtures reference by id. Extending the registry is a
one-line change plus a fixture update; it does NOT require a schema bump.
"""

from __future__ import annotations

from typing import Dict, Iterable, List

from eidolon.learning.schemas import ArmDefinition


class ArmRegistry:
    """In-memory arm registry. Stdlib-only, deterministic order preserved."""

    def __init__(self) -> None:
        self._arms: Dict[str, ArmDefinition] = {}

    def register(self, arm: ArmDefinition) -> None:
        if not arm.arm_id:
            raise ValueError("arm_id must be non-empty")
        if arm.family != "prompt_phrasing":
            raise ValueError(
                f"arm {arm.arm_id!r}: v1 arms must have family='prompt_phrasing'; "
                f"got {arm.family!r}. Tool-ordering arms deferred to REC-017."
            )
        if arm.arm_id in self._arms:
            raise ValueError(f"duplicate arm_id: {arm.arm_id!r}")
        self._arms[arm.arm_id] = arm

    def get(self, arm_id: str) -> ArmDefinition:
        return self._arms[arm_id]

    def has(self, arm_id: str) -> bool:
        return arm_id in self._arms

    def ids(self) -> List[str]:
        return list(self._arms.keys())

    def all(self) -> Iterable[ArmDefinition]:
        return self._arms.values()

    def __len__(self) -> int:
        return len(self._arms)


# Module-level default registry, seeded below.
_default = ArmRegistry()


def default_registry() -> ArmRegistry:
    return _default


def register_arm(arm: ArmDefinition) -> None:
    _default.register(arm)


# --- v1 seed arms ---------------------------------------------------------
# Kept intentionally small and structural. No operator language. No secrets.
# Every arm_id below is referenced by tests/eval/fixtures/*.jsonl.
_SEED_ARMS = [
    ArmDefinition(
        arm_id="pp-terse-v1",
        family="prompt_phrasing",
        template="{task}\n\nBe terse. Return only the answer.",
        tags=["style:terse"],
    ),
    ArmDefinition(
        arm_id="pp-explain-v1",
        family="prompt_phrasing",
        template="{task}\n\nExplain your reasoning briefly, then answer.",
        tags=["style:explain"],
    ),
    ArmDefinition(
        arm_id="pp-checklist-v1",
        family="prompt_phrasing",
        template="{task}\n\nList the sub-steps you will take, then execute them.",
        tags=["style:checklist"],
    ),
    ArmDefinition(
        arm_id="pp-recall-v1",
        family="prompt_phrasing",
        template="Recall prior context, then answer:\n{task}",
        tags=["style:recall"],
    ),
]


for _arm in _SEED_ARMS:
    _default.register(_arm)
