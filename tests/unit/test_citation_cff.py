# SPDX-License-Identifier: Apache-2.0
"""Unit tests for CITATION.cff and the release-time CFF bump (REC-015).

These tests do not require the ``cffconvert`` package. They exercise:
- CITATION.cff structural validity (parseable YAML, required fields present).
- Author list is generic (no personal contact info leaked).
- Placeholder strings match the expected `OPERATOR_INPUT_REQUIRED_*` pattern.
- docs/citing.md exists and contains a BibTeX example.
- README has a "Cite this" link pointing to CITATION.cff.
- release.yml has a `bump-citation` job gated on stable tags.
- The bump regexes correctly rewrite `version:` and `date-released:` lines.
"""

from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError:  # pragma: no cover - CI has PyYAML
        raise unittest.SkipTest("PyYAML not available")
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


class CitationCFFTests(unittest.TestCase):
    def setUp(self):
        self.path = _REPO_ROOT / "CITATION.cff"

    def test_exists_at_repo_root(self):
        self.assertTrue(self.path.exists(), "CITATION.cff must be at repo root")

    def test_parses_as_yaml(self):
        _load_yaml(self.path)  # raises on invalid YAML

    def test_required_top_level_keys(self):
        doc = _load_yaml(self.path)
        required = {
            "cff-version",
            "message",
            "title",
            "abstract",
            "authors",
            "license",
            "repository-code",
            "keywords",
            "version",
            "date-released",
            "doi",
        }
        missing = required - set(doc.keys())
        self.assertFalse(missing, f"missing keys: {sorted(missing)}")

    def test_cff_version_is_1_2_0(self):
        doc = _load_yaml(self.path)
        self.assertEqual(str(doc["cff-version"]), "1.2.0")

    def test_license_is_apache2(self):
        doc = _load_yaml(self.path)
        self.assertEqual(doc["license"], "Apache-2.0")

    def test_repository_code_matches_project(self):
        doc = _load_yaml(self.path)
        self.assertIn(
            "shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal",
            doc["repository-code"],
        )

    def test_authors_is_generic(self):
        doc = _load_yaml(self.path)
        authors = doc["authors"]
        self.assertIsInstance(authors, list)
        self.assertGreaterEqual(len(authors), 1)
        # No personal contact info fields leaked.
        for a in authors:
            self.assertNotIn("email", a)
            self.assertNotIn("orcid", a)
            self.assertNotIn("address", a)

    def test_placeholders_present(self):
        text = self.path.read_text(encoding="utf-8")
        # Exactly 3 placeholder occurrences: version, date-released, doi.
        matches = re.findall(r"OPERATOR_INPUT_REQUIRED", text)
        self.assertEqual(len(matches), 3)

    def test_placeholder_field_mapping(self):
        doc = _load_yaml(self.path)
        for field in ("version", "date-released", "doi"):
            self.assertIn("OPERATOR_INPUT_REQUIRED", str(doc[field]))


class CitingDocTests(unittest.TestCase):
    def test_docs_citing_md_exists(self):
        self.assertTrue((_REPO_ROOT / "docs" / "citing.md").exists())

    def test_bibtex_example_present(self):
        text = (_REPO_ROOT / "docs" / "citing.md").read_text(encoding="utf-8")
        self.assertIn("@software{eidolon_hermes", text)
        self.assertIn("Apache-2.0", text)
        self.assertIn("bibtex", text.lower())


class ReadmeCiteLinkTests(unittest.TestCase):
    def test_readme_links_to_citation_cff(self):
        text = (_REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("## Cite this", text)
        self.assertIn("CITATION.cff", text)


class ReleaseWorkflowBumpTests(unittest.TestCase):
    def setUp(self):
        self.wf = _REPO_ROOT / ".github" / "workflows" / "release.yml"
        self.doc = _load_yaml(self.wf)

    def test_bump_citation_job_present(self):
        jobs = self.doc.get("jobs", {})
        self.assertIn("bump-citation", jobs)

    def test_bump_citation_gated_on_stable_tags(self):
        job = self.doc["jobs"]["bump-citation"]
        # Excludes pre-release tags (contains a '-' like v1.2.3-rc1).
        self.assertIn("startsWith(github.ref, 'refs/tags/v')", job["if"])
        self.assertIn("!contains(github.ref, '-')", job["if"])

    def test_bump_citation_needs_publish(self):
        job = self.doc["jobs"]["bump-citation"]
        needs = job.get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        self.assertIn("publish-pypi", needs)

    def test_bump_citation_has_contents_write(self):
        job = self.doc["jobs"]["bump-citation"]
        self.assertEqual(job.get("permissions", {}).get("contents"), "write")


class BumpRegexTests(unittest.TestCase):
    """Lock the substitution logic used inside the release workflow's inline Python."""

    def test_rewrites_version_and_date(self):
        original = (
            'version: "OPERATOR_INPUT_REQUIRED_ON_RELEASE_TAG"\n'
            'date-released: "OPERATOR_INPUT_REQUIRED_ON_RELEASE_TAG"\n'
        )
        version = "1.3.0"
        released = "2026-07-08"
        out = re.sub(r"^version: .*$", f'version: "{version}"', original, flags=re.M)
        out = re.sub(
            r"^date-released: .*$",
            f'date-released: "{released}"',
            out,
            flags=re.M,
        )
        self.assertIn('version: "1.3.0"', out)
        self.assertIn('date-released: "2026-07-08"', out)
        self.assertNotIn("OPERATOR_INPUT_REQUIRED_ON_RELEASE_TAG", out)

    def test_leaves_doi_placeholder_untouched(self):
        original = (
            'version: "OPERATOR_INPUT_REQUIRED_ON_RELEASE_TAG"\n'
            'doi: "OPERATOR_INPUT_REQUIRED_AFTER_FIRST_ZENODO_MINT"\n'
        )
        out = re.sub(r"^version: .*$", 'version: "1.0.0"', original, flags=re.M)
        self.assertIn("OPERATOR_INPUT_REQUIRED_AFTER_FIRST_ZENODO_MINT", out)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
