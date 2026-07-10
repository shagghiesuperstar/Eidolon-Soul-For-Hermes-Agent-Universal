# SPDX-License-Identifier: Apache-2.0
"""Unit tests for eidolon.learning.arms -- ArmRegistry and seed arms."""

import unittest

from eidolon.learning.arms import ArmRegistry, default_registry, register_arm
from eidolon.learning.schemas import ArmDefinition


def _arm(arm_id: str, family: str = "prompt_phrasing") -> ArmDefinition:
    return ArmDefinition(
        arm_id=arm_id,
        family=family,
        template="{task}",
        tags=[],
    )


class TestArmRegistryBasics(unittest.TestCase):

    def setUp(self):
        self.reg = ArmRegistry()

    def test_register_and_get(self):
        self.reg.register(_arm("a1"))
        result = self.reg.get("a1")
        self.assertEqual(result.arm_id, "a1")

    def test_has_true_and_false(self):
        self.reg.register(_arm("a2"))
        self.assertTrue(self.reg.has("a2"))
        self.assertFalse(self.reg.has("missing"))

    def test_ids_preserves_insertion_order(self):
        for aid in ["x", "y", "z"]:
            self.reg.register(_arm(aid))
        self.assertEqual(self.reg.ids(), ["x", "y", "z"])

    def test_all_returns_all_arms(self):
        self.reg.register(_arm("p"))
        self.reg.register(_arm("q"))
        ids = {a.arm_id for a in self.reg.all()}
        self.assertEqual(ids, {"p", "q"})

    def test_len(self):
        self.assertEqual(len(self.reg), 0)
        self.reg.register(_arm("r"))
        self.assertEqual(len(self.reg), 1)


class TestArmRegistryGuards(unittest.TestCase):

    def setUp(self):
        self.reg = ArmRegistry()

    def test_rejects_empty_arm_id(self):
        with self.assertRaises(ValueError):
            self.reg.register(_arm(""))

    def test_rejects_non_prompt_phrasing_family(self):
        with self.assertRaises(ValueError):
            self.reg.register(_arm("bad", family="tool_ordering"))

    def test_rejects_duplicate_arm_id(self):
        self.reg.register(_arm("dup"))
        with self.assertRaises(ValueError):
            self.reg.register(_arm("dup"))


class TestModuleLevelHelpers(unittest.TestCase):

    def test_default_registry_returns_same_instance(self):
        self.assertIs(default_registry(), default_registry())

    def test_default_registry_is_nonempty(self):
        self.assertGreater(len(default_registry()), 0)


class TestSeedArms(unittest.TestCase):

    def setUp(self):
        self.reg = default_registry()

    def test_seed_arm_ids_present(self):
        for aid in ["pp-terse-v1", "pp-explain-v1", "pp-checklist-v1", "pp-recall-v1"]:
            self.assertTrue(self.reg.has(aid), f"missing seed arm: {aid}")

    def test_seed_arms_have_prompt_phrasing_family(self):
        for arm in self.reg.all():
            self.assertEqual(arm.family, "prompt_phrasing")

    def test_seed_arm_templates_contain_task_placeholder(self):
        for arm in self.reg.all():
            self.assertIn("{task}", arm.template, f"{arm.arm_id} template missing {{task}}")

    def test_seed_arms_have_nonempty_tags(self):
        for arm in self.reg.all():
            self.assertIsInstance(arm.tags, list)
            self.assertGreater(len(arm.tags), 0, f"{arm.arm_id} has empty tags")


if __name__ == "__main__":
    unittest.main()
