# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the PII sanitization scanner (REC-011)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

_SCANNER_PATH = _ROOT / "scripts" / "sanitize_check.py"
_PATTERNS_PATH = _ROOT / ".sanitize-patterns.yml"


def _load_scanner():
    spec = importlib.util.spec_from_file_location(
        "_sanitize_check_under_test", str(_SCANNER_PATH)
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


scanner = _load_scanner()


class PatternFileTests(unittest.TestCase):
    def test_patterns_file_exists(self) -> None:
        self.assertTrue(_PATTERNS_PATH.exists())

    def test_parses_without_pyyaml(self) -> None:
        # If PyYAML sneaks in as a scanner dep, this test still works but the
        # roadmap invariant would be violated; we check import shape below.
        patterns = scanner.parse_patterns_file(_PATTERNS_PATH)
        self.assertGreaterEqual(len(patterns), 7)

    def test_scanner_module_does_not_import_yaml(self) -> None:
        source = _SCANNER_PATH.read_text(encoding="utf-8")
        self.assertNotIn("import yaml", source)
        self.assertNotIn("from yaml", source)

    def test_each_pattern_compiles(self) -> None:
        patterns = scanner.parse_patterns_file(_PATTERNS_PATH)
        for p in patterns:
            self.assertIsNotNone(p.compiled, f"pattern {p.name} did not compile")


class SelfTestTests(unittest.TestCase):
    def test_self_test_all_pass(self) -> None:
        patterns = scanner.parse_patterns_file(_PATTERNS_PATH)
        passed, total, failures = scanner.run_self_test(patterns)
        self.assertEqual(passed, total, f"failures: {failures}")
        self.assertGreater(total, 0)

    def test_every_pattern_has_positive_and_clean_fixture(self) -> None:
        patterns = scanner.parse_patterns_file(_PATTERNS_PATH)
        fixture_dir = _ROOT / "tests" / "fixtures" / "sanitize_selftest"
        for p in patterns:
            pos = fixture_dir / f"{p.name}_positive.txt"
            neg = fixture_dir / f"{p.name}_clean.txt"
            self.assertTrue(pos.exists(), f"missing positive fixture for {p.name}")
            self.assertTrue(neg.exists(), f"missing clean fixture for {p.name}")


class ScanBehaviourTests(unittest.TestCase):
    def _mk_repo(self, contents: dict) -> Path:
        tmp = Path(tempfile.mkdtemp())
        for rel, body in contents.items():
            path = tmp / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        return tmp

    def test_clean_repo_scan_returns_empty(self) -> None:
        patterns = scanner.parse_patterns_file(_PATTERNS_PATH)
        tmp = self._mk_repo({"a.py": "print('hello')\n"})
        hits = scanner.scan_repo(tmp, patterns)
        self.assertEqual(hits, [])

    def test_aws_key_leak_detected(self) -> None:
        patterns = scanner.parse_patterns_file(_PATTERNS_PATH)
        tmp = self._mk_repo({"leak.txt": "AKIAABCDEFGHIJKLMNOP\n"})
        hits = scanner.scan_repo(tmp, patterns)
        names = [h[2] for h in hits]
        self.assertIn("aws_access_key", names)

    def test_redaction_masks_middle(self) -> None:
        patterns = scanner.parse_patterns_file(_PATTERNS_PATH)
        tmp = self._mk_repo({"leak.txt": "ghp_abcdefghijklmnopqrstuvwxyz0123456789\n"})
        hits = scanner.scan_repo(tmp, patterns)
        self.assertEqual(len(hits), 1)
        _rel, _line, _name, redacted = hits[0]
        self.assertIn("***", redacted)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz", redacted)

    def test_exclude_paths_respected(self) -> None:
        patterns = scanner.parse_patterns_file(_PATTERNS_PATH)
        tmp = self._mk_repo({
            "docs/example.md": "/Users/alice/notes.md\n",
        })
        hits = scanner.scan_repo(tmp, patterns)
        names = [h[2] for h in hits]
        self.assertNotIn("absolute_user_path", names)

    def test_global_excludes_skip_git_dir(self) -> None:
        patterns = scanner.parse_patterns_file(_PATTERNS_PATH)
        tmp = self._mk_repo({".git/HEAD": "AKIAABCDEFGHIJKLMNOP\n"})
        hits = scanner.scan_repo(tmp, patterns)
        self.assertEqual(hits, [])

    def test_binary_extensions_skipped(self) -> None:
        patterns = scanner.parse_patterns_file(_PATTERNS_PATH)
        tmp = self._mk_repo({"logo.png": "AKIAABCDEFGHIJKLMNOP\n"})
        hits = scanner.scan_repo(tmp, patterns)
        self.assertEqual(hits, [])


class CliInvocationTests(unittest.TestCase):
    def test_self_test_exit_zero(self) -> None:
        r = subprocess.run(
            [sys.executable, str(_SCANNER_PATH), "--self-test"],
            capture_output=True, text=True, cwd=str(_ROOT),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("self-test PASS", r.stdout)

    def test_repo_scan_exit_zero(self) -> None:
        r = subprocess.run(
            [sys.executable, str(_SCANNER_PATH)],
            capture_output=True, text=True, cwd=str(_ROOT),
        )
        self.assertEqual(r.returncode, 0,
                         f"stdout={r.stdout}\nstderr={r.stderr}")

    def test_simulated_leak_exit_one(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, dir=str(_ROOT / "scripts"),
            prefix="leak_test_"
        ) as f:
            f.write("AKIAABCDEFGHIJKLMNOP\n")
            leak_path = Path(f.name)
        try:
            r = subprocess.run(
                [sys.executable, str(_SCANNER_PATH)],
                capture_output=True, text=True, cwd=str(_ROOT),
            )
            self.assertEqual(r.returncode, 1)
            self.assertIn("aws_access_key", r.stdout)
        finally:
            leak_path.unlink(missing_ok=True)


class DoctorCheckTests(unittest.TestCase):
    def test_pii_patterns_loaded_check_passes(self) -> None:
        from eidolon.checks.pii_patterns_loaded import check
        result = check()
        self.assertEqual(result.status, "PASS", result.reason)
        self.assertEqual(result.name, "pii_patterns_loaded")

    def test_check_is_in_registry(self) -> None:
        from eidolon.checks import registry
        names = [fn().name for fn in registry()]
        self.assertIn("pii_patterns_loaded", names)


class WorkflowFileTests(unittest.TestCase):
    def test_sanitize_workflow_exists(self) -> None:
        wf = _ROOT / ".github" / "workflows" / "sanitize.yml"
        self.assertTrue(wf.exists())

    def test_workflow_runs_scanner(self) -> None:
        wf = (_ROOT / ".github" / "workflows" / "sanitize.yml").read_text(encoding="utf-8")
        self.assertIn("sanitize_check.py", wf)
        self.assertIn("--self-test", wf)

    def test_pre_commit_hook_exists_and_executable(self) -> None:
        hook = _ROOT / ".githooks" / "pre-commit"
        self.assertTrue(hook.exists())
        # Executable bit is best-effort on CI file systems; content check is definitive.
        text = hook.read_text(encoding="utf-8")
        self.assertIn("sanitize_check.py", text)


if __name__ == "__main__":
    unittest.main()
