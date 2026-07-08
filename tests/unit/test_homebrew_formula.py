# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the Homebrew formula (REC-012).

Read-only shape checks. Does NOT invoke `brew` — that runs locally per
docs/install-brew.md and in the tap repo's own CI (once created).
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_FORMULA = _ROOT / "packaging" / "homebrew" / "eidolon.rb"
_INSTALL_DOC = _ROOT / "docs" / "install-brew.md"
_TAP_WORKFLOW = _ROOT / ".github" / "workflows" / "homebrew-tap-update.yml"
_README = _ROOT / "README.md"


class FormulaShapeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(_FORMULA.exists(), "packaging/homebrew/eidolon.rb missing")
        self.body = _FORMULA.read_text(encoding="utf-8")

    def test_class_name(self) -> None:
        self.assertRegex(self.body, r"(?m)^class Eidolon < Formula")

    def test_includes_virtualenv_helper(self) -> None:
        self.assertIn("include Language::Python::Virtualenv", self.body)

    def test_has_required_top_fields(self) -> None:
        for field in ("desc ", "homepage ", "url ", "sha256 ", "license "):
            self.assertRegex(self.body, rf"(?m)^\s*{re.escape(field)}", f"missing field: {field.strip()}")

    def test_homepage_is_https_and_correct(self) -> None:
        self.assertRegex(
            self.body,
            r'homepage\s+"https://github\.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal"',
        )

    def test_license_is_apache_2(self) -> None:
        self.assertRegex(self.body, r'license\s+"Apache-2\.0"')

    def test_depends_on_python_311_range(self) -> None:
        # Roadmap verify grep: depends_on "python@3.1[1-3]"
        self.assertRegex(self.body, r'(?m)^\s*depends_on\s+"python@3\.1[1-3]"')

    def test_install_uses_virtualenv_helper(self) -> None:
        self.assertRegex(self.body, r"def install\s*\n\s*virtualenv_install_with_resources")

    def test_test_block_calls_version_and_doctor(self) -> None:
        self.assertIn('eidolon --version', self.body)
        self.assertIn('"doctor"', self.body)

    def test_no_curl_or_https_body_leaks(self) -> None:
        # Sanity: no `system "curl"` shortcuts, no plaintext http URLs.
        self.assertNotIn('"http://', self.body)


class PlaceholderMarkersTests(unittest.TestCase):
    """Until first stable release, formula ships with placeholders.

    These tests document the pre-release state. When the first release lands
    and the release workflow rewrites the formula, both markers disappear and
    these tests are expected to be updated to their post-release form
    (documented in the failure message).
    """

    def setUp(self) -> None:
        self.body = _FORMULA.read_text(encoding="utf-8")

    def test_placeholder_present_pre_release(self) -> None:
        has_placeholder = "PLACEHOLDER_ON_FIRST_RELEASE" in self.body
        self.assertTrue(
            has_placeholder,
            "Post-release: sha256 must be a real 64-char hex. Update this "
            "test to `assertRegex(body, r'sha256\\s+\"[0-9a-f]{64}\"')`.",
        )

    def test_placeholder_url_dev(self) -> None:
        # The placeholder URL references v0.0.0. When a real release lands,
        # both this test and the URL itself will change.
        if "PLACEHOLDER_ON_FIRST_RELEASE" in self.body:
            self.assertIn("v0.0.0", self.body)


class InstallDocTests(unittest.TestCase):
    def test_install_doc_exists(self) -> None:
        self.assertTrue(_INSTALL_DOC.exists())

    def test_install_doc_covers_key_commands(self) -> None:
        body = _INSTALL_DOC.read_text(encoding="utf-8")
        for needle in (
            "brew tap eidolon-hermes/eidolon",
            "brew install eidolon",
            "brew upgrade eidolon",
            "brew uninstall eidolon",
            "eidolon --version",
            "eidolon doctor",
        ):
            self.assertIn(needle, body, f"install-brew.md missing: {needle}")


class TapWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(_TAP_WORKFLOW.exists(), "homebrew-tap-update.yml missing")
        self.body = _TAP_WORKFLOW.read_text(encoding="utf-8")

    def test_triggers_on_release_published(self) -> None:
        self.assertRegex(self.body, r"types:\s*\[published\]")

    def test_skips_prereleases(self) -> None:
        # Same filter shape as publish-pypi.
        self.assertIn("!contains(github.event.release.tag_name, '-')", self.body)

    def test_targets_tap_repo(self) -> None:
        self.assertIn("eidolon-hermes/homebrew-eidolon", self.body)

    def test_updates_formula_path(self) -> None:
        self.assertIn("Formula/eidolon.rb", self.body)

    def test_uses_pypi_sdist_url_template(self) -> None:
        self.assertIn(
            "https://files.pythonhosted.org/packages/source/e/eidolon-hermes/",
            self.body,
        )

    def test_guards_missing_token_gracefully(self) -> None:
        # Missing HOMEBREW_TAP_PUSH_TOKEN must warn, not fail.
        self.assertIn("HOMEBREW_TAP_PUSH_TOKEN", self.body)
        self.assertIn("Skipped tap update", self.body)


class ReadmeTests(unittest.TestCase):
    def test_readme_advertises_brew_tap(self) -> None:
        body = _README.read_text(encoding="utf-8")
        self.assertIn("brew tap eidolon-hermes/eidolon", body)
        self.assertIn("brew install eidolon", body)


if __name__ == "__main__":
    unittest.main()
