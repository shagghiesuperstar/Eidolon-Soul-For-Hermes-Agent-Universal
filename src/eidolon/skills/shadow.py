# SPDX-License-Identifier: Apache-2.0
"""Shadow evaluator for MEDIUM-risk proposals (REC-017).

Contract
--------
- Pure: no I/O except reading fixture files supplied by the caller.
- Stdlib-only.
- ``ShadowEvaluator.evaluate(arm_id, fixtures_dir)`` returns a ``ShadowResult``.
- Status codes follow the global vocabulary: PASS / FAIL / DEGRADED.
- A skill that reduces regression-suite pass rate below ``threshold`` is FAIL.
- Missing fixtures dir -> DEGRADED (loud).

The evaluator is **not** wired to auto-apply anything.  Application decisions
live in the dream-cycle handler; this module only scores and reports.
"""

from __future__ import annotations

import json

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

PASS = "PASS"
FAIL = "FAIL"
DEGRADED = "DEGRADED"

# Minimum weighted pass rate for a MEDIUM proposal to be considered safe.
DEFAULT_THRESHOLD: float = 0.80


@dataclass
class ShadowResult:
    """Result of a single shadow evaluation run.

    Attributes
    ----------
    status:    PASS | FAIL | DEGRADED
    score:     weighted regression pass-rate in [0.0, 1.0], or -1.0 on DEGRADED.
    reason:    human-readable explanation; never empty.
    arm_id:    the arm that was evaluated.
    threshold: the minimum score required for PASS.
    """

    status: str
    score: float
    reason: str
    arm_id: str
    threshold: float


class ShadowEvaluator:
    """Evaluate a candidate skill arm against the regression fixture set.

    Parameters
    ----------
    threshold:
        Weighted pass rate in [0.0, 1.0] that a candidate must reach for
        PASS.  Default is ``DEFAULT_THRESHOLD`` (0.80).  Values outside
        [0.0, 1.0] raise ``ValueError`` at construction time.
    """

    def __init__(self, threshold: float = DEFAULT_THRESHOLD) -> None:
        if not (0.0 <= threshold <= 1.0):
            raise ValueError(
                f"threshold must be in [0.0, 1.0], got {threshold!r}"
            )
        self._threshold = threshold

    @property
    def threshold(self) -> float:
        return self._threshold

    def evaluate(
        self,
        arm_id: str,
        fixtures_dir: Path,
    ) -> ShadowResult:
        """Score ``arm_id`` against all *.jsonl fixtures under ``fixtures_dir``.

        Returns
        -------
        ShadowResult with status PASS, FAIL, or DEGRADED.

        - DEGRADED: fixtures_dir missing / no usable fixtures found.
        - PASS: weighted score >= threshold.
        - FAIL: weighted score < threshold  (proposal must NOT be applied).
        """
        if not fixtures_dir.exists():
            return ShadowResult(
                status=DEGRADED,
                score=-1.0,
                reason=f"fixtures_dir_missing:{fixtures_dir}",
                arm_id=arm_id,
                threshold=self._threshold,
            )

        try:
            from eidolon.learning.rewards import load_fixtures, RegressionReward
        except ImportError as exc:
            return ShadowResult(
                status=DEGRADED,
                score=-1.0,
                reason=f"import_error:{exc}",
                arm_id=arm_id,
                threshold=self._threshold,
            )

        try:
            cases = load_fixtures(fixtures_dir)
        except FileNotFoundError:
            return ShadowResult(
                status=DEGRADED,
                score=-1.0,
                reason="no_fixtures_found",
                arm_id=arm_id,
                threshold=self._threshold,
            )
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            return ShadowResult(
                status=DEGRADED,
                score=-1.0,
                reason=f"fixture_error:{exc}",
                arm_id=arm_id,
                threshold=self._threshold,
            )

        reward = RegressionReward(cases)
        score = reward.for_arm(arm_id)

        if score >= self._threshold:
            return ShadowResult(
                status=PASS,
                score=score,
                reason=f"score {score:.4f} >= threshold {self._threshold:.4f}",
                arm_id=arm_id,
                threshold=self._threshold,
            )
        return ShadowResult(
            status=FAIL,
            score=score,
            reason=f"score {score:.4f} < threshold {self._threshold:.4f}",
            arm_id=arm_id,
            threshold=self._threshold,
        )
