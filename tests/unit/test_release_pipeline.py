# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the release pipeline (REC-007).

These tests are read-only sanity checks on the workflow YAML and MANIFEST.in.
They MUST NOT invoke `python -m build` or hit the network. Full build is
verified locally and in CI via the workflow itself.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOW = _ROOT / ".github" / "workflows" / "release.yml"
_MANIFEST = _ROOT / "MANIFEST.in"
_PYPROJECT = _ROOT / "pyproject.toml"
_VERSION_PY = _ROOT / "src" / "eidolon" / "_version.py"


class WorkflowFileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(_WORKFLOW.exists(), "release.yml missing")
        self.body = _WORKFLOW.read_text(encoding="utf-8")

    def test_workflow_name_is_release(self) -> None:
        # `name:` appears as the first line, but assertRegex is not multiline.
        self.assertTrue(self.body.startswith("name: release"),
                        f"workflow must start with `name: release`; got: {self.body[:40]!r}")

    def test_triggers_include_main_push_and_v_tags(self) -> None:
        self.assertIn("branches: [main]", self.body)
        self.assertIn("tags: ['v*']", self.body)

    def test_publish_pypi_gated_on_tag_and_no_dash(self) -> None:
        # Prereleases contain a dash (e.g. v1.0.0-rc1); real PyPI must skip them.
        self.assertRegex(
            self.body,
            r"if:\s*startsWith\(github\.ref,\s*'refs/tags/v'\)\s*&&\s*!contains\(github\.ref,\s*'-'\)",
        )

    def test_uses_pypi_trusted_publisher_action(self) -> None:
        self.assertIn("pypa/gh-action-pypi-publish@release/v1", self.body)

    def test_no_api_token_secrets(self) -> None:
        # Trusted publishing means no long-lived tokens live in secrets.
        forbidden = ("PYPI_API_TOKEN", "TWINE_PASSWORD", "PYPI_TOKEN")
        for tok in forbidden:
            self.assertNotIn(tok, self.body, f"forbidden secret ref: {tok}")

    def test_id_token_write_present_on_publish_jobs(self) -> None:
        # OIDC requires id-token: write for each publish job.
        count = len(re.findall(r"id-token:\s*write", self.body))
        self.assertGreaterEqual(count, 2, "id-token: write must appear on both publish jobs")

    def test_environments_named_pypi_test_and_pypi_prod(self) -> None:
        self.assertIn("name: pypi-test", self.body)
        self.assertIn("name: pypi-prod", self.body)

    def test_testpypi_repository_url(self) -> None:
        self.assertIn("https://test.pypi.org/legacy/", self.body)

    def test_tag_matches_version_guard_present(self) -> None:
        # The build job must fail if the git tag does not match _version.py.
        self.assertIn('tag matches version', self.body.lower() + self.body)
        self.assertIn('does not match _version.py', self.body)

    def test_build_runs_twine_check(self) -> None:
        self.assertIn("twine check", self.body)


class ManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(_MANIFEST.exists(), "MANIFEST.in missing")
        self.body = _MANIFEST.read_text(encoding="utf-8")

    def test_manifest_includes_required_top_level_docs(self) -> None:
        for doc in ("README.md", "LICENSE", "NOTICE", "RELEASING.md",
                    "SOUL.md", "OPERATOR.md"):
            self.assertRegex(
                self.body,
                rf"(?m)^\s*include\s+{re.escape(doc)}\s*$",
                f"MANIFEST.in must `include {doc}` (roadmap REC-007 pass criterion)",
            )

    def test_manifest_prunes_tests_and_github(self) -> None:
        self.assertIn("prune tests", self.body)
        self.assertIn("prune .github", self.body)


class PyprojectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.body = _PYPROJECT.read_text(encoding="utf-8")

    def test_project_name_is_eidolon_hermes(self) -> None:
        self.assertRegex(self.body, r'name\s*=\s*"eidolon-hermes"')

    def test_version_is_dynamic(self) -> None:
        self.assertRegex(self.body, r'dynamic\s*=\s*\[\s*"version"\s*\]')

    def test_dynamic_version_points_to_version_py(self) -> None:
        self.assertIn("eidolon._version.__version__", self.body)

    def test_console_entry_point(self) -> None:
        self.assertIn('eidolon = "eidolon.cli:main"', self.body)


class VersionModuleTests(unittest.TestCase):
    def test_version_importable_and_pep440_shaped(self) -> None:
        # We do not import eidolon._version here to avoid side effects; parse
        # the file directly.
        source = _VERSION_PY.read_text(encoding="utf-8")
        m = re.search(r'__version__\s*=\s*"([^"]+)"', source)
        self.assertIsNotNone(m, "_version.py must define __version__ as a string literal")
        version = m.group(1)
        # PEP 440 allows: X.Y.Z, X.Y.Z-dev0, X.Y.ZrcN, X.Y.Z.devN, etc.
        # Accept the shapes we actually use in this project.
        self.assertRegex(
            version,
            r"^\d+\.\d+\.\d+(?:[-.]?(?:dev|rc|a|b|alpha|beta)\d+)?$",
            f"version {version!r} does not match project convention",
        )


if __name__ == "__main__":
    unittest.main()
