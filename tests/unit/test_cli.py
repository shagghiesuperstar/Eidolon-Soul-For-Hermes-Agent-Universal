# SPDX-License-Identifier: Apache-2.0
"""REC-001: canonical CLI spine."""

from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout

from tests.unit._tmphomes import IsolatedHome


class CLISpineTests(IsolatedHome):
    def test_version_exits_zero_and_prints_semver(self) -> None:
        from eidolon.cli import main

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["version"])
        self.assertEqual(code, 0)
        out = buf.getvalue().strip()
        self.assertRegex(out, r"^\d+\.\d+\.\d+(?:-\w+\d*)?$")

    def test_bare_invocation_exits_usage_error(self) -> None:
        from eidolon.cli import main

        err = io.StringIO()
        with redirect_stderr(err):
            code = main([])
        self.assertEqual(code, 64)  # sysexits.EX_USAGE
        self.assertIn("usage:", err.getvalue().lower())

    def test_unknown_command_argparse_errors_cleanly(self) -> None:
        from eidolon.cli import main

        with self.assertRaises(SystemExit) as ctx:
            main(["does-not-exist"])
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
