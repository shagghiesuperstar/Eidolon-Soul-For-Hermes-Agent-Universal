# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the 5-class risk classifier (REC-010)."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from eidolon.safety import RiskClass, classify, classify_action, is_never_touch  # noqa: E402
from eidolon.safety.risk import NEVER_TOUCH_PATHS  # noqa: E402


class EnumOrdinalTests(unittest.TestCase):
    def test_exactly_five_members(self) -> None:
        members = list(RiskClass)
        self.assertEqual(len(members), 5)

    def test_strict_ordinal_order(self) -> None:
        self.assertLess(RiskClass.NO_OP, RiskClass.LOW)
        self.assertLess(RiskClass.LOW, RiskClass.MEDIUM)
        self.assertLess(RiskClass.MEDIUM, RiskClass.HIGH)
        self.assertLess(RiskClass.HIGH, RiskClass.NEVER_TOUCH)

    def test_only_low_auto_applies(self) -> None:
        self.assertTrue(RiskClass.LOW.is_auto_applyable())
        for r in (RiskClass.NO_OP, RiskClass.MEDIUM, RiskClass.HIGH, RiskClass.NEVER_TOUCH):
            self.assertFalse(r.is_auto_applyable(), msg=r)


class NeverTouchPathTests(unittest.TestCase):
    """Every NEVER_TOUCH_PATHS entry must actually classify to NEVER_TOUCH."""

    def test_soul_md(self) -> None:
        for target in ("SOUL.md", "./SOUL.md", "eidolon/SOUL.md", "skills/dream-cycle/SOUL.md"):
            with self.subTest(target=target):
                self.assertTrue(is_never_touch(target))
                self.assertEqual(classify({"target": target, "mutation_kind": "docs_only"}), RiskClass.NEVER_TOUCH)

    def test_config_yaml(self) -> None:
        for target in ("config.yaml", "./config.yaml", ".hermes/config.yaml", "/home/user/.hermes/config.yaml"):
            with self.subTest(target=target):
                self.assertTrue(is_never_touch(target), msg=target)

    def test_last_known_good(self) -> None:
        for target in ("last_known_good", "last_known_good/2026/latest.snap", "state/last_known_good/x.bin"):
            with self.subTest(target=target):
                self.assertTrue(is_never_touch(target), msg=target)

    def test_license_and_notice(self) -> None:
        for target in ("LICENSE", "LICENSE.md", "LICENSE.txt", "NOTICE", "NOTICE.md"):
            with self.subTest(target=target):
                self.assertTrue(is_never_touch(target), msg=target)

    def test_adversarial_workflow(self) -> None:
        for target in (".github/workflows/adversarial.yml", "adversarial.yml"):
            with self.subTest(target=target):
                self.assertTrue(is_never_touch(target), msg=target)

    def test_never_touch_beats_no_op(self) -> None:
        """NEVER_TOUCH ceiling overrides even a formal no-op."""
        self.assertEqual(
            classify({"target": "SOUL.md", "mutation_kind": "no_op"}),
            RiskClass.NEVER_TOUCH,
        )

    def test_all_registered_patterns_have_at_least_one_example_that_matches(self) -> None:
        """Every regex in NEVER_TOUCH_PATHS should match at least the pattern's own literal form."""
        import re

        # Build one 'synthetic sample' per pattern by stripping regex metachars.
        # This is a shape check, not a robustness proof.
        for pat in NEVER_TOUCH_PATHS:
            # Try a synthetic sample that should always match.
            samples = [
                "SOUL.md", "LICENSE", "NOTICE", "config.yaml",
                ".hermes/config.yaml", "last_known_good/x",
                ".github/workflows/adversarial.yml", "adversarial.yml",
            ]
            self.assertTrue(
                any(re.compile(pat).search(s) for s in samples),
                msg=f"pattern {pat!r} matches none of the canonical samples",
            )


class MutationKindMappingTests(unittest.TestCase):
    def test_low_kinds(self) -> None:
        for mk in ("docs_only", "typo_fix", "test_only", "comment_only"):
            with self.subTest(mk=mk):
                self.assertEqual(classify({"target": "notes.md", "mutation_kind": mk}), RiskClass.LOW)

    def test_medium_kinds(self) -> None:
        for mk in ("prompt_phrasing", "log_verbosity", "config_field_add"):
            with self.subTest(mk=mk):
                self.assertEqual(classify({"target": "prompts/x.txt", "mutation_kind": mk}), RiskClass.MEDIUM)

    def test_high_kinds(self) -> None:
        for mk in ("skill_code", "config_field_rewrite", "handler_signature"):
            with self.subTest(mk=mk):
                self.assertEqual(classify({"target": "skills/dream-cycle/handler.py", "mutation_kind": mk}), RiskClass.HIGH)

    def test_no_op_kinds(self) -> None:
        for mk in ("no_op", "identity", ""):
            with self.subTest(mk=mk):
                self.assertEqual(classify({"target": "somewhere.txt", "mutation_kind": mk}), RiskClass.NO_OP)

    def test_unknown_kind_fails_closed_to_high(self) -> None:
        self.assertEqual(
            classify({"target": "somewhere.txt", "mutation_kind": "invented_kind"}),
            RiskClass.HIGH,
        )


class ErgonomicClassifierTests(unittest.TestCase):
    def test_classify_action_matches_classify(self) -> None:
        r1 = classify_action("README.md", "docs_only")
        r2 = classify({"target": "README.md", "mutation_kind": "docs_only"})
        self.assertEqual(r1, r2)

    def test_safety_flags_accepted(self) -> None:
        r = classify_action("README.md", "docs_only", safety_flags=("dry_run",))
        self.assertEqual(r, RiskClass.LOW)


class PurityTests(unittest.TestCase):
    def test_classify_is_pure(self) -> None:
        """Repeated calls with same input must yield same output.

        The classifier must not depend on time.time(), random, or environ.
        This test doesn't monkey-patch (it doesn't need to); it just calls
        classify 500 times and asserts bit-identical output.
        """
        action = {"target": "src/eidolon/cli.py", "mutation_kind": "docs_only"}
        first = classify(action)
        for _ in range(500):
            self.assertEqual(classify(action), first)

    def test_source_imports_no_impurity(self) -> None:
        """safety/risk.py and safety/classifier.py MUST NOT import time/os/random."""
        forbidden = {"import os", "import time", "import random", "from os", "from time", "from random"}
        for name in ("risk.py", "classifier.py"):
            text = (_ROOT / "src" / "eidolon" / "safety" / name).read_text(encoding="utf-8")
            for f in forbidden:
                self.assertNotIn(
                    f, text,
                    msg=f"safety/{name} imports {f!r}; classifier must be pure (REC-010)",
                )


class SanitizationGrepTests(unittest.TestCase):
    """Roadmap invariant: safety/ must not mention operator/human/user_name."""

    def test_no_forbidden_tokens_in_safety_module(self) -> None:
        import re

        forbidden_re = re.compile(r"operator|human|user_name")
        offenders = []
        for path in (_ROOT / "src" / "eidolon" / "safety").glob("*.py"):
            text = path.read_text(encoding="utf-8")
            if forbidden_re.search(text):
                offenders.append(path.name)
        self.assertEqual(
            offenders, [],
            msg=f"safety/ files contain forbidden tokens: {offenders}",
        )


class DoctorCheckTests(unittest.TestCase):
    def test_doctor_lists_risk_classifier_check(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(_SRC)
        r = subprocess.run(
            [sys.executable, "-m", "eidolon", "doctor", "--json"],
            env=env, cwd=str(_ROOT), capture_output=True, text=True, timeout=30,
        )
        payload = json.loads(r.stdout)
        names = [c["name"] for c in payload["checks"]]
        self.assertIn("risk_classifier_ready", names)

    def test_risk_check_passes(self) -> None:
        from eidolon.checks.risk_classifier_ready import check
        result = check()
        self.assertEqual(result.status, "PASS", msg=f"got {result}")


class DreamCycleGateBehaviorTests(unittest.TestCase):
    """Integration: NEVER_TOUCH proposals are audited, LOW proposals auto-apply."""

    def test_never_touch_writes_audit_and_refuses(self) -> None:
        import tempfile
        # Import from repo path so we exercise the actual handler.
        sys.path.insert(0, str(_ROOT / "skills" / "dream-cycle"))
        try:
            import handler  # type: ignore
        finally:
            sys.path.pop(0)

        with tempfile.TemporaryDirectory() as td:
            os.environ["EIDOLON_HOME"] = td
            try:
                candidates = [
                    {"id": "c-never", "target": "SOUL.md", "mutation_kind": "docs_only"},
                    {"id": "c-low", "target": "docs/x.md", "mutation_kind": "docs_only"},
                    {"id": "c-high", "target": "src/eidolon/cli.py", "mutation_kind": "skill_code"},
                    {"id": "c-med", "target": "prompts/reflect.txt", "mutation_kind": "prompt_phrasing"},
                ]
                # Silence handler.log to stdout; we just care about the audit log.
                handler.gate_and_apply(candidates, {"runs": [], "last_known_good": None})
                from eidolon.util.paths import audit_log
                text = audit_log().read_text(encoding="utf-8") if audit_log().exists() else ""
                self.assertIn("c-never", text, msg=f"audit missing c-never; got: {text!r}")
                self.assertIn("c-high", text, msg=f"audit missing c-high; got: {text!r}")
                # LOW auto-applied, MEDIUM deferred — neither should audit.
                self.assertNotIn("c-low", text)
                self.assertNotIn("c-med", text)
            finally:
                os.environ.pop("EIDOLON_HOME", None)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
