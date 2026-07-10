# SPDX-License-Identifier: Apache-2.0
"""preference_update is auto-applyable LOW (canary apply path)."""
import unittest

from eidolon.safety.risk import RiskClass, classify
from eidolon.safety.classifier import classify_action


class PreferenceUpdateRiskTests(unittest.TestCase):
    def test_preference_update_is_low(self):
        r = classify({"mutation_kind": "preference_update", "target": ""})
        self.assertEqual(r, RiskClass.LOW)
        self.assertTrue(r.is_auto_applyable())

    def test_classify_action_preference_update(self):
        r = classify_action("", "preference_update")
        self.assertEqual(r, RiskClass.LOW)


if __name__ == "__main__":
    unittest.main()
