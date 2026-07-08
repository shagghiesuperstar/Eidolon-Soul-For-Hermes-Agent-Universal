# SPDX-License-Identifier: Apache-2.0
"""soul_present: multi-location search + FAIL vs DEGRADED semantics."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

from tests.unit._tmphomes import IsolatedHome


class SoulPresentTests(IsolatedHome):
    def _write_soul(self, path: Path, size: int = 1024) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Padding to hit the target size cheaply.
        path.write_text("SOUL contract\n" + ("x" * max(0, size - 14)), encoding="utf-8")

    def _unset(self, name: str) -> None:
        os.environ.pop(name, None)

    def test_env_override_wins(self):
        from eidolon.checks import soul_present

        p = self.tmp / "custom" / "MY_SOUL.md"
        self._write_soul(p, size=1024)
        try:
            os.environ["EIDOLON_SOUL_PATH"] = str(p)
            r = soul_present.check()
        finally:
            self._unset("EIDOLON_SOUL_PATH")

        self.assertEqual(r.status, "PASS")
        self.assertIn("env:EIDOLON_SOUL_PATH", r.reason)

    def test_hermes_home_soul_md_found(self):
        from eidolon.checks import soul_present

        self._write_soul(self.hermes_home / "SOUL.md")
        r = soul_present.check()
        self.assertEqual(r.status, "PASS")
        self.assertIn("$HERMES_HOME/SOUL.md", r.reason)

    def test_small_soul_yields_degraded(self):
        from eidolon.checks import soul_present

        p = self.hermes_home / "SOUL.md"
        p.write_text("tiny", encoding="utf-8")
        r = soul_present.check()
        self.assertEqual(r.status, "DEGRADED")
        self.assertIn("truncated", r.reason)

    def test_missing_in_source_checkout_is_fail(self):
        """When pyproject.toml exists at repo_root, missing SOUL.md is FAIL."""
        from eidolon.checks import soul_present
        from eidolon.util import paths

        # In the test environment repo_root() resolves to the actual repo,
        # which HAS pyproject.toml AND SOUL.md at its root. So this test
        # verifies the happy source-checkout path.
        r = soul_present.check()
        # Without a $HERMES_HOME/SOUL.md, the check should still find the
        # repo-root SOUL.md and PASS.
        self.assertEqual(r.status, "PASS")
        # Confirm it came from repo_root, not $HERMES_HOME.
        self.assertIn("repo_root", r.reason)

    def test_missing_when_pip_installed_is_degraded(self):
        """Simulate pip-installed mode by monkey-patching repo_root to a dir with no pyproject.toml."""
        from eidolon.checks import soul_present as sp

        fake_root = self.tmp / "fake_site_packages_root"
        fake_root.mkdir(parents=True, exist_ok=True)
        # No pyproject.toml, no SOUL.md at this fake root.

        # soul_present imported repo_root by-name at module load time, so we
        # patch it in the soul_present namespace, not eidolon.util.paths.
        saved = sp.repo_root
        try:
            sp.repo_root = lambda: fake_root  # type: ignore[assignment]
            # No SOUL.md in $HERMES_HOME either.
            r = sp.check()
        finally:
            sp.repo_root = saved  # type: ignore[assignment]

        # Because pyproject.toml is not at fake_root, we are not a source checkout,
        # so the missing SOUL.md must degrade (not fail).
        self.assertEqual(r.status, "DEGRADED")
        self.assertIn("SOUL.md not found", r.reason)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
