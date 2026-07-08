# SPDX-License-Identifier: Apache-2.0
"""Thompson-sampling bandit over Beta-Bernoulli arms.

Contract (per roadmap § REC-008):
- Stdlib only. No numpy, no scipy, no torch.
- Beta(alpha, beta) posteriors, one per arm.
- On each round: for each arm, draw x ~ Beta(alpha, beta); pick argmax(x).
- Update posterior with observed reward r in [0.0, 1.0]:
    alpha_new = alpha + r
    beta_new  = beta  + (1 - r)
- Reproducible: caller supplies a `random.Random` instance (or a seed).

Convergence expectation (validated by unit test):
- Two arms, true reward rates 0.7 vs 0.3, 100 episodes:
  the better arm's posterior mean must exceed 0.6 AND it must have been
  selected in at least 70/100 episodes.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class ArmPosterior:
    """Beta(alpha, beta) posterior for a single arm."""

    arm_id: str
    alpha: float = 1.0  # uniform prior
    beta: float = 1.0

    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    def update(self, reward: float) -> None:
        if not (0.0 <= reward <= 1.0):
            raise ValueError(f"reward {reward!r} not in [0.0, 1.0]")
        self.alpha += reward
        self.beta += 1.0 - reward


class ThompsonBandit:
    """Thompson sampling over a fixed set of arms.

    The bandit is intentionally stateless w.r.t. context; contextual routing
    happens one layer up (regression suite groups cases by category). This
    keeps the v1 surface minimal.
    """

    def __init__(self, arm_ids: List[str], rng: random.Random | None = None) -> None:
        if not arm_ids:
            raise ValueError("bandit requires >=1 arm")
        seen: set[str] = set()
        for a in arm_ids:
            if a in seen:
                raise ValueError(f"duplicate arm_id {a!r}")
            seen.add(a)
        self._posteriors: Dict[str, ArmPosterior] = {
            a: ArmPosterior(arm_id=a) for a in arm_ids
        }
        self._rng = rng if rng is not None else random.Random()
        self._selection_counts: Dict[str, int] = {a: 0 for a in arm_ids}

    def arms(self) -> List[str]:
        return list(self._posteriors.keys())

    def posterior(self, arm_id: str) -> ArmPosterior:
        return self._posteriors[arm_id]

    def posterior_means(self) -> Dict[str, float]:
        return {a: p.mean() for a, p in self._posteriors.items()}

    def selection_counts(self) -> Dict[str, int]:
        return dict(self._selection_counts)

    def sample_arm(self) -> str:
        """Draw one Thompson sample per arm; return the argmax arm_id.

        Ties are broken by deterministic first-encountered order, which
        combined with a seeded rng makes selection reproducible.
        """
        best_id = ""
        best_draw = -1.0
        for arm_id, post in self._posteriors.items():
            draw = self._rng.betavariate(post.alpha, post.beta)
            if draw > best_draw:
                best_draw = draw
                best_id = arm_id
        self._selection_counts[best_id] += 1
        return best_id

    def observe(self, arm_id: str, reward: float) -> Tuple[float, float]:
        """Update the given arm with reward in [0.0, 1.0]. Returns new (alpha, beta)."""
        if arm_id not in self._posteriors:
            raise KeyError(f"unknown arm_id {arm_id!r}")
        p = self._posteriors[arm_id]
        p.update(reward)
        return (p.alpha, p.beta)
