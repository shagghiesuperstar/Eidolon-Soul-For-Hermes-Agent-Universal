# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the date-based Hermes freshness check.

Hermes upstream is CalVer, not SemVer — verify the check reasons over dates,
degrades on unparseable input, and never raises FAIL for a merely stale host.
"""

from __future__ import annotations

import datetime as _dt
import os
import unittest
from unittest import mock

from tests.unit._tmphomes import IsolatedHome


class ParseHermesVersionTests(unittest.TestCase):
    def test_parses_standard_calver(self) -> None:
        from eidolon.checks.hermes_version import parse_hermes_version

        self.assertEqual(parse_hermes_version("v2026.7.1"), _dt.date(2026, 7, 1))

    def test_parses_calver_with_patch(self) -> None:
        from eidolon.checks.hermes_version import parse_hermes_version

        self.assertEqual(parse_hermes_version("v2026.5.29.2"), _dt.date(2026, 5, 29))

    def test_parses_without_v_prefix(self) -> None:
        from eidolon.checks.hermes_version import parse_hermes_version

        self.assertEqual(parse_hermes_version("2026.5.28"), _dt.date(2026, 5, 28))

    def test_rejects_semver(self) -> None:
        from eidolon.checks.hermes_version import parse_hermes_version

        self.assertIsNone(parse_hermes_version("v1.2.3"))

    def test_rejects_garbage(self) -> None:
        from eidolon.checks.hermes_version import parse_hermes_version

        self.assertIsNone(parse_hermes_version("not-a-version"))
        self.assertIsNone(parse_hermes_version(""))

    def test_rejects_invalid_calendar_date(self) -> None:
        from eidolon.checks.hermes_version import parse_hermes_version

        # Month 13, day 32, and Feb 30 all fail the datetime constructor.
        self.assertIsNone(parse_hermes_version("v2026.13.1"))
        self.assertIsNone(parse_hermes_version("v2026.7.32"))
        self.assertIsNone(parse_hermes_version("v2026.2.30"))


class HermesVersionCheckTests(IsolatedHome):
    def _run_check(self):
        # Import inside test so module-level state (HERMES_MIN_DATE) is fresh.
        from eidolon.checks.hermes_version import check

        return check()

    def test_no_version_source_is_degraded(self) -> None:
        result = self._run_check()
        self.assertEqual(result.status, "DEGRADED")
        self.assertIn("Could not determine host Hermes version", result.reason)

    def test_env_override_wins(self) -> None:
        with mock.patch.dict(os.environ, {"HERMES_VERSION": "v2026.7.1"}):
            result = self._run_check()
        # July 7 test date; July 1 is fresh vs. floor 2026-04-08.
        self.assertEqual(result.status, "PASS")
        self.assertIn("v2026.7.1", result.reason)

    def test_stale_version_is_degraded_not_fail(self) -> None:
        with mock.patch.dict(os.environ, {"HERMES_VERSION": "v2025.1.1"}):
            result = self._run_check()
        self.assertEqual(
            result.status,
            "DEGRADED",
            "stale Hermes must never surface as FAIL — Eidolon must still run",
        )
        self.assertIn("older than", result.reason)
        self.assertIn("days_stale", result.detail or {})

    def test_unparseable_version_is_degraded_with_raw(self) -> None:
        with mock.patch.dict(os.environ, {"HERMES_VERSION": "definitely-not-calver"}):
            result = self._run_check()
        self.assertEqual(result.status, "DEGRADED")
        self.assertIn("CalVer", result.reason)
        self.assertEqual(result.detail["raw"], "definitely-not-calver")

    def test_version_file_is_used_when_env_absent(self) -> None:
        (self.hermes_home / "VERSION").write_text("v2026.6.15\n", encoding="utf-8")
        result = self._run_check()
        self.assertEqual(result.status, "PASS")
        self.assertIn("v2026.6.15", result.reason)

    def test_config_yaml_version_key_is_used(self) -> None:
        self.write_hermes_config("version: v2026.5.29\nother: stuff\n")
        result = self._run_check()
        self.assertEqual(result.status, "PASS")

    def test_config_yaml_quoted_version_is_parsed(self) -> None:
        self.write_hermes_config('version: "v2026.5.29"\n')
        result = self._run_check()
        self.assertEqual(result.status, "PASS")

    def test_env_takes_precedence_over_config(self) -> None:
        # Config says stale; env says fresh; env should win.
        self.write_hermes_config("version: v2024.1.1\n")
        with mock.patch.dict(os.environ, {"HERMES_VERSION": "v2026.7.1"}):
            result = self._run_check()
        self.assertEqual(result.status, "PASS")

    def test_doctor_registry_includes_hermes_version(self) -> None:
        from eidolon.checks import registry

        names = [fn.__name__ for fn in registry()]
        self.assertIn("check", names)  # sanity — checks are named `check`
        # Run all checks and collect names emitted via CheckResult.
        results = [fn() for fn in registry()]
        result_names = {r.name for r in results}
        self.assertIn("hermes_version", result_names)


if __name__ == "__main__":
    unittest.main()
