# SPDX-License-Identifier: Apache-2.0
"""Reward function contract for the v1 bandit.

Per roadmap § REC-008: the reward is the regression-suite pass rate over a
fixed set of ≥20 deterministic fixtures. The bandit sees this scalar; it
never sees raw case content.

Contract:
- `RegressionReward.for_arm(arm_id) -> float in [0.0, 1.0]`.
- No network. No filesystem writes. No non-determinism (given the same
  fixtures + seed, the reward is bit-identical across runs).
- Mock provider always returns the fixture's expected output for the arm
  that is the fixture's `expected_winner`. All other arms miss.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class RegressionCase:
    case_id: str
    category: str
    context_hash: str
    arm_inputs: Dict[str, Dict[str, str]]
    expected_winner: str
    reward_weight: float

    @classmethod
    def from_dict(cls, d: Dict[str, object]) -> "RegressionCase":
        return cls(
            case_id=str(d["case_id"]),
            category=str(d["category"]),
            context_hash=str(d["context_hash"]),
            arm_inputs=d["arm_inputs"],  # type: ignore[arg-type]
            expected_winner=str(d["expected_winner"]),
            reward_weight=float(d.get("reward_weight", 1.0)),
        )


def load_fixtures(dir_path: Path) -> List[RegressionCase]:
    """Load every *.jsonl file under `dir_path` in deterministic order."""
    cases: List[RegressionCase] = []
    for jsonl in sorted(dir_path.glob("*.jsonl")):
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            cases.append(RegressionCase.from_dict(json.loads(line)))
    if not cases:
        raise FileNotFoundError(f"no regression fixtures under {dir_path}")
    ids = [c.case_id for c in cases]
    if len(set(ids)) != len(ids):
        dupes = [i for i in ids if ids.count(i) > 1]
        raise ValueError(f"duplicate case_ids: {sorted(set(dupes))}")
    return cases


class RegressionReward:
    """Deterministic reward calculator over a fixture set.

    reward(arm_id) = sum(weight * hit) / sum(weight)
    where hit = 1 if arm is the fixture's expected_winner AND the mock
    provider "succeeded" (which it always does, by construction).
    """

    def __init__(self, cases: List[RegressionCase]) -> None:
        if not cases:
            raise ValueError("at least one case required")
        self._cases = list(cases)
        self._total_weight = sum(c.reward_weight for c in self._cases)
        if self._total_weight <= 0:
            raise ValueError("total reward_weight must be positive")

    @property
    def total_weight(self) -> float:
        return self._total_weight

    @property
    def case_count(self) -> int:
        return len(self._cases)

    def for_arm(self, arm_id: str) -> float:
        num = 0.0
        for c in self._cases:
            if c.expected_winner == arm_id and arm_id in c.arm_inputs:
                num += c.reward_weight
        return num / self._total_weight

    def all_scores(self) -> Dict[str, float]:
        scores: Dict[str, float] = {}
        for c in self._cases:
            for arm_id in c.arm_inputs:
                scores.setdefault(arm_id, 0.0)
        for arm_id in scores:
            scores[arm_id] = self.for_arm(arm_id)
        return scores


def context_hash(text: str) -> str:
    """Deterministic SHA256 hex digest, used to build/verify fixtures."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
