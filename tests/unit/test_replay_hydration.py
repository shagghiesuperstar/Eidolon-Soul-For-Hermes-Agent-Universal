# SPDX-License-Identifier: Apache-2.0
"""Replay hydration tests — proves bandit posteriors are durable across sessions.

Design intent (arXiv:2604.15097 attributed): compact structured experience
representations must survive session boundaries.  These tests verify the
mechanism: hydrate_bandit() replays persisted episodes into a fresh bandit
so posteriors warm-start from real evidence rather than uniform priors.

No Evolver source, assets, tests, names, prompts, or schemas copied.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from eidolon.learning.bandit import ThompsonBandit  # noqa: E402
from eidolon.learning.replay import hydrate_bandit  # noqa: E402
from eidolon.learning.schemas import EpisodeRecord  # noqa: E402


class _MeanRng:
    """Deterministic RNG that always draws the posterior mean — removes sampling
    variance so selection assertions are unconditional."""

    def betavariate(self, alpha: float, beta: float) -> float:
        return alpha / (alpha + beta)


def _record(arm_id: str, reward: float) -> EpisodeRecord:
    return EpisodeRecord(arm_id=arm_id, reward=reward)


class ReplayHydrationTests(unittest.TestCase):
    def test_hydrate_bandit_consumes_matching_records_and_skips_orphans(self) -> None:
        """Matching arm ids update posteriors; unknown arm ids are counted, not raised."""
        bandit = ThompsonBandit(["kept"])

        consumed, skipped = hydrate_bandit(
            bandit,
            iter([_record("kept", 1.0), _record("missing", 0.0)]),
        )

        self.assertEqual(consumed, 1)
        self.assertEqual(skipped, 1)
        # alpha started at 1.0; one reward=1.0 observe() adds 1.0 -> 2.0
        self.assertEqual(bandit.posterior("kept").alpha, 2.0)
        self.assertEqual(bandit.posterior("kept").beta, 1.0)

    def test_hydration_changes_selection_from_recorded_evidence(self) -> None:
        """After hydration with biased evidence the better arm wins selection.

        Cold bandit (uniform priors) picks 'first' (first-encountered tie-break).
        Warm bandit (3x reward=0 on 'first', 3x reward=1 on 'second') picks
        'second' — proving posteriors survive session boundaries.
        """
        cold = ThompsonBandit(["first", "second"], rng=_MeanRng())
        self.assertEqual(cold.sample_arm(), "first")  # pre-condition: tie -> first

        warm = ThompsonBandit(["first", "second"], rng=_MeanRng())
        records = [_record("first", 0.0) for _ in range(3)]
        records.extend(_record("second", 1.0) for _ in range(3))
        consumed, skipped = hydrate_bandit(warm, iter(records))

        self.assertEqual(consumed, 6)
        self.assertEqual(skipped, 0)
        self.assertEqual(warm.sample_arm(), "second")
        self.assertGreater(
            warm.posterior("second").mean(),
            warm.posterior("first").mean(),
        )


if __name__ == "__main__":
    unittest.main()
