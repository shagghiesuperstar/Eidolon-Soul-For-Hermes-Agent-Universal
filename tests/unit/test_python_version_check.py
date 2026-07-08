# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the python_version + compatibility_supported checks (REC-016)."""

from __future__ import annotations

import datetime as _dt
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from eidolon.checks import DEGRADED, FAIL, PASS, registry  # noqa: E402
from eidolon.checks import python_version as pv  # noqa: E402


class ClassifierTests(unittest.TestCase):
    def test_below_min_is_fail(self):
        status, _ = pv._classify((3, 9), _dt.date(2026, 1, 1))
        self.assertEqual(status, FAIL)

    def test_ancient_is_fail(self):
        status, _ = pv._classify((2, 7), _dt.date(2026, 1, 1))
        self.assertEqual(status, FAIL)

    def test_310_pass_before_deprecation_date(self):
        status, reason = pv._classify((3, 10), _dt.date(2026, 12, 31))
        self.assertEqual(status, PASS)
        self.assertIn("supported until", reason)

    def test_310_degraded_on_deprecation_date(self):
        status, reason = pv._classify((3, 10), _dt.date(2027, 1, 1))
        self.assertEqual(status, DEGRADED)
        self.assertIn("upgrade to 3.11+", reason)

    def test_310_degraded_after_deprecation_date(self):
        status, _ = pv._classify((3, 10), _dt.date(2030, 6, 15))
        self.assertEqual(status, DEGRADED)

    def test_311_pass_forever_in_matrix(self):
        for d in (_dt.date(2026, 1, 1), _dt.date(2030, 1, 1)):
            status, _ = pv._classify((3, 11), d)
            self.assertEqual(status, PASS, msg=str(d))

    def test_312_pass(self):
        status, _ = pv._classify((3, 12), _dt.date(2026, 7, 8))
        self.assertEqual(status, PASS)

    def test_313_pass(self):
        status, _ = pv._classify((3, 13), _dt.date(2026, 7, 8))
        self.assertEqual(status, PASS)

    def test_314_is_degraded(self):
        status, reason = pv._classify((3, 14), _dt.date(2026, 7, 8))
        self.assertEqual(status, DEGRADED)
        self.assertIn("above the tested matrix", reason)

    def test_far_future_is_degraded(self):
        status, _ = pv._classify((4, 0), _dt.date(2030, 1, 1))
        self.assertEqual(status, DEGRADED)


class LiveCheckTests(unittest.TestCase):
    def test_current_interpreter_never_fails(self):
        r = pv.check()
        # We build/CI on 3.10-3.13 today; the CI ceiling can rise, but
        # nothing in the tested matrix should ever come back FAIL.
        # This is a REC-016 constraint: "Never FAIL for a Python version
        # that appears in the CI matrix."
        self.assertIn(r.status, (PASS, DEGRADED))

    def test_never_pass_outside_matrix(self):
        # Constraint: "Never PASS for a Python version outside the CI matrix."
        with mock.patch.object(pv, "_current_version", return_value=(3, 15)):
            r = pv.check()
            self.assertNotEqual(r.status, PASS)
        with mock.patch.object(pv, "_current_version", return_value=(3, 9)):
            r = pv.check()
            self.assertNotEqual(r.status, PASS)

    def test_name_is_python_version(self):
        self.assertEqual(pv.check().name, "python_version")


class AggregatorTests(unittest.TestCase):
    def test_aggregator_name(self):
        r = pv.compatibility_supported()
        self.assertEqual(r.name, "compatibility_supported")

    def test_aggregator_returns_worst_of(self):
        from eidolon.checks import hermes_version

        def _pass():
            from eidolon.checks import CheckResult
            return CheckResult(name="hermes_version", status=PASS, reason="ok")

        def _fail():
            from eidolon.checks import CheckResult
            return CheckResult(name="hermes_version", status=FAIL, reason="broken")

        # python_version -> DEGRADED, hermes_version -> PASS -> overall DEGRADED
        with mock.patch.object(pv, "check", return_value=type(pv.check())(
            name="python_version", status=DEGRADED, reason="stale"
        )):
            with mock.patch.object(hermes_version, "check", _pass):
                self.assertEqual(pv.compatibility_supported().status, DEGRADED)
            # python DEGRADED + hermes FAIL -> FAIL
            with mock.patch.object(hermes_version, "check", _fail):
                self.assertEqual(pv.compatibility_supported().status, FAIL)

    def test_aggregator_pass_when_all_pass(self):
        from eidolon.checks import CheckResult, hermes_version

        with mock.patch.object(
            pv, "check",
            return_value=CheckResult(name="python_version", status=PASS, reason="ok"),
        ):
            with mock.patch.object(
                hermes_version, "check",
                return_value=CheckResult(name="hermes_version", status=PASS, reason="ok"),
            ):
                self.assertEqual(pv.compatibility_supported().status, PASS)


class RegistryTests(unittest.TestCase):
    def test_python_version_registered(self):
        names = [fn().name for fn in registry()]
        self.assertIn("python_version", names)

    def test_compatibility_supported_registered(self):
        names = [fn().name for fn in registry()]
        self.assertIn("compatibility_supported", names)


class ConstantTests(unittest.TestCase):
    def test_deprecation_date(self):
        self.assertEqual(pv.PY_310_DEGRADED_AFTER, _dt.date(2027, 1, 1))

    def test_supported_min(self):
        self.assertEqual(pv.SUPPORTED_MIN, (3, 10))

    def test_untested_above(self):
        self.assertEqual(pv.UNTESTED_ABOVE, (3, 13))


class DocsMatrixTests(unittest.TestCase):
    def test_compatibility_md_exists(self):
        self.assertTrue((_REPO_ROOT / "docs" / "compatibility.md").exists())

    def test_matrix_names_the_python_versions(self):
        text = (_REPO_ROOT / "docs" / "compatibility.md").read_text(encoding="utf-8")
        for v in ("3.10", "3.11", "3.12", "3.13"):
            self.assertIn(v, text, msg=f"docs must list Python {v}")

    def test_matrix_mentions_hermes_freshness(self):
        text = (_REPO_ROOT / "docs" / "compatibility.md").read_text(encoding="utf-8")
        self.assertIn("hermes_version", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
