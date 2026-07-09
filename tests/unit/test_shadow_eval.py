# SPDX-License-Identifier: Apache-2.0
"""Unit tests for REC-017: shadow evaluation gate and lifecycle state machine.

Adversarial invariant (must hold):
  A skill that regresses on the eval suite MUST NOT be promoted even if its
  bandit posterior is high.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from eidolon.skills.shadow import ShadowEvaluator, ShadowResult, DEFAULT_THRESHOLD, PASS, FAIL, DEGRADED
from eidolon.skills.lifecycle import (
    SkillManifest,
    PromotionResult,
    check_promotion_criteria,
    load_manifest,
    DEFAULT_MIN_SHADOW_SESSIONS,
    DEFAULT_MIN_BANDIT_POSTERIOR,
    DEFAULT_REGRESSION_PASS_RATE,
    STATE_SHADOW,
    STATE_ACTIVE,
    STATE_RETIRED,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _write_fixtures(dir_path: Path, winner_arm: str, n: int = 5) -> None:
    """Write n synthetic fixtures where `winner_arm` always wins."""
    lines = []
    for i in range(n):
        case = {
            "case_id": f"tc-{i:03d}",
            "category": "prompt_construction",
            "context_hash": f"{'a' * 60}{i:04d}",
            "arm_inputs": {winner_arm: {"input": f"x{i}"}, "loser": {"input": f"y{i}"}},
            "expected_winner": winner_arm,
            "reward_weight": 1.0,
        }
        lines.append(json.dumps(case))
    (dir_path / "fixtures.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _make_manifest(dir_path: Path, **overrides) -> Path:
    """Write a minimal manifest.yml with optional field overrides."""
    promo = {
        "min_shadow_sessions": overrides.get("min_shadow_sessions", DEFAULT_MIN_SHADOW_SESSIONS),
        "min_bandit_posterior": overrides.get("min_bandit_posterior", DEFAULT_MIN_BANDIT_POSTERIOR),
        "regression_suite_pass_rate": overrides.get("regression_suite_pass_rate", DEFAULT_REGRESSION_PASS_RATE),
    }
    text = (
        f"name: {overrides.get('name', 'test-skill')}\n"
        f"version: {overrides.get('version', '1.0.0')}\n"
        "promotion:\n"
        f"  min_shadow_sessions: {promo['min_shadow_sessions']}\n"
        f"  min_bandit_posterior: {promo['min_bandit_posterior']}\n"
        f"  regression_suite_pass_rate: {promo['regression_suite_pass_rate']}\n"
    )
    p = dir_path / "manifest.yml"
    p.write_text(text, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# ShadowEvaluator tests
# ---------------------------------------------------------------------------

class TestShadowEvaluatorPass(unittest.TestCase):
    """PASS path: arm is the winner for all fixtures; score == 1.0."""

    def test_pass_when_arm_wins_all_fixtures(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _write_fixtures(d, winner_arm="arm-A")
            ev = ShadowEvaluator(threshold=0.80)
            result = ev.evaluate("arm-A", d)
        self.assertEqual(result.status, PASS)
        self.assertAlmostEqual(result.score, 1.0)
        self.assertEqual(result.arm_id, "arm-A")


class TestShadowEvaluatorFail(unittest.TestCase):
    """FAIL path: arm loses all fixtures; score == 0.0 < threshold."""

    def test_fail_when_arm_wins_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _write_fixtures(d, winner_arm="arm-A")
            ev = ShadowEvaluator(threshold=0.80)
            result = ev.evaluate("loser", d)
        self.assertEqual(result.status, FAIL)
        self.assertAlmostEqual(result.score, 0.0)


class TestShadowEvaluatorDegraded(unittest.TestCase):
    """DEGRADED path: fixtures dir does not exist."""

    def test_degraded_missing_fixtures_dir(self):
        ev = ShadowEvaluator()
        result = ev.evaluate("any-arm", Path("/nonexistent/path/eidolon-fixtures"))
        self.assertEqual(result.status, DEGRADED)
        self.assertAlmostEqual(result.score, -1.0)
        self.assertIn("fixtures_dir_missing", result.reason)


class TestShadowEvaluatorDegradedEmptyDir(unittest.TestCase):
    """DEGRADED path: fixtures dir exists but contains no *.jsonl files."""

    def test_degraded_empty_fixtures_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            ev = ShadowEvaluator()
            result = ev.evaluate("any-arm", Path(tmp))
        self.assertEqual(result.status, DEGRADED)
        self.assertIn("no_fixtures_found", result.reason)


class TestShadowEvaluatorScoreBoundary(unittest.TestCase):
    """Boundary: score exactly equal to threshold -> PASS."""

    def test_score_at_threshold_is_pass(self):
        # 4 fixtures: arm-B wins 4 of 5 -> score = 0.80; threshold = 0.80 -> PASS
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            lines = []
            for i in range(4):
                lines.append(json.dumps({
                    "case_id": f"t{i}", "category": "prompt_construction",
                    "context_hash": "a" * 64,
                    "arm_inputs": {"arm-B": {"i": str(i)}, "other": {"i": "x"}},
                    "expected_winner": "arm-B", "reward_weight": 1.0,
                }))
            lines.append(json.dumps({
                "case_id": "t4", "category": "prompt_construction",
                "context_hash": "b" * 64,
                "arm_inputs": {"arm-B": {"i": "4"}, "other": {"i": "x"}},
                "expected_winner": "other", "reward_weight": 1.0,
            }))
            (d / "f.jsonl").write_text("\n".join(lines), encoding="utf-8")
            ev = ShadowEvaluator(threshold=0.80)
            result = ev.evaluate("arm-B", d)
        self.assertEqual(result.status, PASS)
        self.assertAlmostEqual(result.score, 0.80)


class TestShadowEvaluatorInvalidThreshold(unittest.TestCase):
    """Construction with threshold outside [0.0, 1.0] raises ValueError."""

    def test_threshold_above_one_raises(self):
        with self.assertRaises(ValueError):
            ShadowEvaluator(threshold=1.1)

    def test_threshold_negative_raises(self):
        with self.assertRaises(ValueError):
            ShadowEvaluator(threshold=-0.1)


# ---------------------------------------------------------------------------
# Lifecycle / PromotionCriteria tests
# ---------------------------------------------------------------------------

class TestPromotionEligible(unittest.TestCase):
    """All criteria met -> eligible."""

    def test_promotion_eligible_all_met(self):
        m = SkillManifest(
            name="test-skill", version="1.0.0",
            min_shadow_sessions=20, min_bandit_posterior=0.65,
            regression_suite_pass_rate=0.95,
        )
        result = check_promotion_criteria(
            m, shadow_sessions=25, bandit_posterior=0.70, regression_pass_rate=0.97
        )
        self.assertTrue(result.eligible)
        self.assertEqual(result.unmet, [])


class TestPromotionBlockedBySessions(unittest.TestCase):
    """Insufficient shadow sessions -> not eligible."""

    def test_blocked_insufficient_shadow_sessions(self):
        m = SkillManifest(
            name="test-skill", version="1.0.0",
            min_shadow_sessions=20, min_bandit_posterior=0.65,
            regression_suite_pass_rate=0.95,
        )
        result = check_promotion_criteria(
            m, shadow_sessions=5, bandit_posterior=0.90, regression_pass_rate=0.99
        )
        self.assertFalse(result.eligible)
        self.assertTrue(any("shadow_sessions" in u for u in result.unmet))


class TestAdversarialRegressionBlocksPromotion(unittest.TestCase):
    """ADVERSARIAL INVARIANT: high bandit posterior does NOT override low
    regression pass rate.  A regressing skill must never be promoted."""

    def test_high_posterior_cannot_override_regression_failure(self):
        m = SkillManifest(
            name="regressing-skill", version="2.0.0",
            min_shadow_sessions=20, min_bandit_posterior=0.65,
            regression_suite_pass_rate=0.95,
        )
        result = check_promotion_criteria(
            m,
            shadow_sessions=30,
            bandit_posterior=0.99,   # very high posterior
            regression_pass_rate=0.40,  # but regresses badly
        )
        self.assertFalse(result.eligible)
        self.assertTrue(any("regression_pass_rate" in u for u in result.unmet))


class TestManifestLoad(unittest.TestCase):
    """load_manifest parses a well-formed manifest.yml correctly."""

    def test_load_valid_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = _make_manifest(
                Path(tmp),
                name="my-skill",
                version="0.1.0",
                min_shadow_sessions=30,
                min_bandit_posterior=0.70,
                regression_suite_pass_rate=0.98,
            )
            m = load_manifest(p)
        self.assertEqual(m.name, "my-skill")
        self.assertEqual(m.version, "0.1.0")
        self.assertEqual(m.min_shadow_sessions, 30)
        self.assertAlmostEqual(m.min_bandit_posterior, 0.70)
        self.assertAlmostEqual(m.regression_suite_pass_rate, 0.98)

    def test_load_missing_manifest_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_manifest(Path("/nonexistent/manifest.yml"))


class TestShadowEvalReadyCheck(unittest.TestCase):
    """Doctor check imports cleanly and returns PASS."""

    def test_doctor_check_passes(self):
        from eidolon.checks.shadow_eval_ready import check
        result = check()
        self.assertEqual(result.name, "shadow_eval_ready")
        self.assertEqual(result.status, "PASS")


class TestMediumRiskIsGated(unittest.TestCase):
    """MEDIUM risk class requires shadow eval; LOW auto-applies; HIGH never auto-applies."""

    def test_medium_not_auto_applyable(self):
        from eidolon.safety.risk import RiskClass
        self.assertFalse(RiskClass.MEDIUM.is_auto_applyable())

    def test_low_is_auto_applyable(self):
        from eidolon.safety.risk import RiskClass
        self.assertTrue(RiskClass.LOW.is_auto_applyable())

    def test_high_not_auto_applyable(self):
        from eidolon.safety.risk import RiskClass
        self.assertFalse(RiskClass.HIGH.is_auto_applyable())

    def test_never_touch_not_auto_applyable(self):
        from eidolon.safety.risk import RiskClass
        self.assertFalse(RiskClass.NEVER_TOUCH.is_auto_applyable())
