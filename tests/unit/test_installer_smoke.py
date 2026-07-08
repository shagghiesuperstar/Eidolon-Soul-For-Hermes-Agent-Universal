# SPDX-License-Identifier: Apache-2.0
"""REC-006: install.sh contract tests.

We do NOT actually run pip install here — that is the installer-test.yml
workflow's job (macos + ubuntu matrix). These tests assert structural
invariants of install.sh that a future edit could easily regress:

- The file exists and is executable.
- It has a shebang, an SPDX header, and `set -euo pipefail`.
- It advertises the exit-code contract in a comment.
- It gates on macOS/Linux and on Python 3.10..3.13.
- It ends with a doctor invocation and interprets doctor's rc.
- `bash -n install.sh` parses without syntax errors.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
INSTALLER = REPO / "install.sh"


class InstallerStructuralTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(INSTALLER.exists(), f"install.sh not found at {INSTALLER}")
        self.text = INSTALLER.read_text(encoding="utf-8")

    def test_installer_is_executable(self) -> None:
        mode = INSTALLER.stat().st_mode
        self.assertTrue(mode & 0o111, "install.sh must have the executable bit set")

    def test_installer_has_bash_shebang(self) -> None:
        first = self.text.splitlines()[0]
        self.assertTrue(
            first.startswith("#!") and "bash" in first,
            f"install.sh must have a bash shebang; got: {first!r}",
        )

    def test_installer_has_spdx_header(self) -> None:
        self.assertIn("SPDX-License-Identifier: Apache-2.0", self.text[:400])

    def test_installer_enables_strict_mode(self) -> None:
        self.assertTrue(
            re.search(r"^set -euo pipefail\s*$", self.text, re.MULTILINE),
            "install.sh must contain `set -euo pipefail` on its own line",
        )

    def test_installer_documents_exit_codes(self) -> None:
        # We document 0, 1, 2, and 64 in the header comment block.
        header = self.text[:2500]
        for code in ("0", "1", "2", "64"):
            self.assertTrue(
                re.search(rf"^#\s+{code}\b", header, re.MULTILINE),
                msg=f"install.sh header must document exit code {code}",
            )

    def test_installer_gates_on_os(self) -> None:
        # We only support Darwin and Linux; anything else exits 1.
        self.assertIn("Darwin", self.text)
        self.assertIn("Linux", self.text)

    def test_installer_gates_on_python_version(self) -> None:
        # We enforce >=3.10, <3.14 (matches pyproject.toml requires-python).
        self.assertRegex(
            self.text,
            r"3\s*,\s*10\)\s*<=\s*sys\.version_info\[:2\]\s*<\s*\(\s*3\s*,\s*14",
        )

    def test_installer_calls_pip_from_python_module(self) -> None:
        # Never `pip install ...` bare — always `$PY -m pip install ...` so we
        # bind to the same interpreter we validated.
        self.assertRegex(self.text, r'"\$PY"\s+-m\s+pip\s+install')
        # And --user to avoid sudo / system-Python mutation.
        self.assertIn("pip install --user", self.text)

    def test_installer_runs_doctor_at_the_end(self) -> None:
        # The last operational step must be a doctor invocation whose rc drives
        # the installer's overall exit code.
        self.assertIn("eidolon\" doctor", self.text)
        # And it must classify rc 0/1/2 explicitly.
        for pattern in (r"DOCTOR_RC=\$\?", r"case \"\$DOCTOR_RC\""):
            self.assertRegex(self.text, pattern)

    def test_installer_syntax_is_valid_bash(self) -> None:
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("bash not on PATH in test environment")
        rc = subprocess.run(
            [bash, "-n", str(INSTALLER)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(
            rc.returncode,
            0,
            f"bash -n install.sh returned {rc.returncode}\nstderr: {rc.stderr}",
        )

    def test_installer_never_calls_sudo(self) -> None:
        # Grep for a bare `sudo` invocation (word boundary; ignore the word in
        # comments discussing "no sudo").
        for line in self.text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            self.assertNotRegex(
                line,
                r"(^|\s|;|\|)sudo\b",
                msg=f"install.sh must not call sudo; offending line: {line!r}",
            )

    def test_installer_supports_env_overrides(self) -> None:
        # Every override documented in the header must have a matching default assignment.
        for var in (
            "EIDOLON_REPO",
            "EIDOLON_REF",
            "EIDOLON_METHOD",
            "EIDOLON_SRC_DIR",
            "EIDOLON_NO_FETCH",
            "EIDOLON_SKIP_DOCTOR",
        ):
            self.assertRegex(
                self.text,
                rf"{var}=\"\$\{{{var}:-",
                msg=f"install.sh must default {var} via ${{{var}:-...}}",
            )

    def test_installer_is_within_size_budget(self) -> None:
        # Roadmap § 8.6.1 targets ~70 lines but real installers grow. Hard cap
        # at 400 lines to keep this thing auditable in a single sitting.
        lines = len(self.text.splitlines())
        self.assertLess(lines, 400, f"install.sh has {lines} lines; budget is <400")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
