# SPDX-License-Identifier: Apache-2.0
"""REC-006: `eidolon verify` — post-install end-to-end smoke test."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout, redirect_stderr

from tests.unit._tmphomes import IsolatedHome


class VerifyContractTests(IsolatedHome):
    """Verify's contract: run 4 in-process steps, aggregate to PASS/DEGRADED/FAIL."""

    def _run_json(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            from eidolon.cli import main

            code = main(argv)
        return code, buf.getvalue()

    def test_verify_json_shape_is_stable(self):
        code, out = self._run_json(["verify", "--json"])
        # Fresh isolated home => no Hermes => DEGRADED sub-steps => overall PASS (non-strict).
        self.assertIn(code, (0, 2))  # PASS or DEGRADED, never FAIL in a clean tmp
        payload = json.loads(out.splitlines()[-1])
        self.assertIn("overall", payload)
        self.assertIn("steps", payload)
        self.assertIn("strict", payload)
        self.assertIsInstance(payload["steps"], list)
        # Exactly the four canonical steps in this order.
        step_names = [s["name"] for s in payload["steps"]]
        self.assertEqual(
            step_names,
            ["import_package", "cli_doctor", "cli_report", "cli_rollback_dry_run"],
        )
        for step in payload["steps"]:
            for k in ("name", "status", "exit_code", "duration_ms", "detail"):
                self.assertIn(k, step)
            self.assertIn(step["status"], {"PASS", "DEGRADED", "FAIL", "ERROR"})
            self.assertIsInstance(step["exit_code"], int)
            self.assertIsInstance(step["duration_ms"], int)
            self.assertGreaterEqual(step["duration_ms"], 0)

    def test_verify_non_strict_folds_degraded_into_pass(self):
        # No Hermes present => doctor is DEGRADED. Non-strict verify must exit 0.
        code, out = self._run_json(["verify", "--json"])
        payload = json.loads(out.splitlines()[-1])
        self.assertEqual(payload["strict"], False)
        # If any step is DEGRADED but none FAIL, overall must be PASS in non-strict.
        statuses = [s["status"] for s in payload["steps"]]
        if any(s == "DEGRADED" for s in statuses) and not any(
            s in ("FAIL", "ERROR") for s in statuses
        ):
            self.assertEqual(payload["overall"], "PASS")
            self.assertEqual(code, 0)

    def test_verify_strict_promotes_degraded_to_exit_2(self):
        code, out = self._run_json(["verify", "--json", "--strict"])
        payload = json.loads(out.splitlines()[-1])
        self.assertEqual(payload["strict"], True)
        statuses = [s["status"] for s in payload["steps"]]
        if any(s == "DEGRADED" for s in statuses) and not any(
            s in ("FAIL", "ERROR") for s in statuses
        ):
            self.assertEqual(payload["overall"], "DEGRADED")
            self.assertEqual(code, 2)

    def test_verify_human_output_prints_overall_line(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            from eidolon.cli import main

            main(["verify"])
        text = buf.getvalue()
        self.assertIn("eidolon verify", text)
        self.assertRegex(text, r"overall:\s+(PASS|DEGRADED|FAIL)")
        # All four steps must appear in human output.
        for name in ("import_package", "cli_doctor", "cli_report", "cli_rollback_dry_run"):
            self.assertIn(name, text)

    def test_verify_never_returns_unexpected_exit_codes(self):
        code, _ = self._run_json(["verify", "--json"])
        # Contract: {0, 1, 2} only. 64 (usage) is impossible from an accepted invocation.
        self.assertIn(code, {0, 1, 2})

    def test_verify_help_appears_in_subcommand_list(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            from eidolon.cli import main

            main([])  # bare invocation prints help to stderr
        self.assertIn("verify", buf.getvalue())


class VerifyStepBehaviorTests(IsolatedHome):
    """Direct-invocation tests for verify.run() bypassing the CLI parser."""

    def test_run_returns_int(self):
        from eidolon.commands import verify

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = verify.run(json_out=True, strict=False)
        self.assertIsInstance(rc, int)
        self.assertIn(rc, {0, 1, 2})

    def test_json_output_is_single_line(self):
        from eidolon.commands import verify

        buf = io.StringIO()
        with redirect_stdout(buf):
            verify.run(json_out=True, strict=False)
        # Exactly one JSON payload followed by a newline.
        lines = [line for line in buf.getvalue().splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)
        json.loads(lines[0])  # must be valid JSON

    def test_events_are_emitted_for_verify(self):
        from eidolon.commands import verify
        from eidolon.util import events, paths

        buf = io.StringIO()
        with redirect_stdout(buf):
            verify.run(json_out=True, strict=False)

        log = paths.events_log()
        self.assertTrue(log.exists(), "verify should have emitted events.jsonl")
        text = log.read_text(encoding="utf-8")
        # One event per step + one summary event = 5 verify.* events minimum.
        # (doctor also emits its own events during the cli_doctor step; that's fine.)
        verify_events = [
            line for line in text.splitlines() if line and "\"verify." in line
        ]
        self.assertGreaterEqual(len(verify_events), 5)
        self.assertTrue(any("verify.summary" in line for line in verify_events))


class VerifyBudgetTests(IsolatedHome):
    """verify must not become a slow-test rat-nest. 5 seconds is the ceiling."""

    def test_verify_completes_under_five_seconds(self):
        import time

        from eidolon.commands import verify

        t0 = time.monotonic()
        buf = io.StringIO()
        with redirect_stdout(buf):
            verify.run(json_out=True, strict=False)
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 5.0, f"verify took {elapsed:.2f}s; budget is 5s")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
