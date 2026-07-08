# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the nightly regression eval driver (REC-014)."""

from __future__ import annotations

import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.eval import nightly  # noqa: E402
from tests.eval import regression_suite  # noqa: E402


class RegressionSuiteJSONTests(unittest.TestCase):
    def test_json_flag_emits_single_line(self):
        buf = io.StringIO()
        real = sys.stdout
        try:
            sys.stdout = buf
            rc = regression_suite.main(["--seed", "42", "--json"])
        finally:
            sys.stdout = real
        self.assertIn(rc, (0, 1))
        lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
        self.assertEqual(len(lines), 1, f"expected 1 line, got {lines!r}")
        payload = json.loads(lines[0])
        self.assertEqual(payload["schema"], 1)
        self.assertIn("pass_rate", payload)
        self.assertIn("misses", payload)
        self.assertEqual(payload["seed"], 42)

    def test_json_and_human_are_different(self):
        buf_json, buf_human = io.StringIO(), io.StringIO()
        real = sys.stdout
        try:
            sys.stdout = buf_json
            regression_suite.main(["--seed", "42", "--json"])
            sys.stdout = buf_human
            regression_suite.main(["--seed", "42"])
        finally:
            sys.stdout = real
        # Human form mentions "cases passed"; JSON form is one line of JSON.
        self.assertNotIn("cases passed", buf_json.getvalue())
        self.assertIn("cases passed", buf_human.getvalue())


class NightlyDryRunTests(unittest.TestCase):
    def test_dry_run_prints_threshold(self):
        buf = io.StringIO()
        real = sys.stdout
        try:
            sys.stdout = buf
            rc = nightly.main(["--dry-run", "--history", "/nonexistent/path.jsonl"])
        finally:
            sys.stdout = real
        self.assertEqual(rc, nightly.EXIT_OK)
        self.assertIn("would append delta=", buf.getvalue())
        self.assertIn("threshold 5%", buf.getvalue())


class NightlyDeltaTests(unittest.TestCase):
    def test_delta_with_no_previous_is_zero(self):
        self.assertEqual(nightly._delta({"pass_rate": 0.5}, None), 0.0)

    def test_delta_positive_when_improving(self):
        d = nightly._delta({"pass_rate": 0.9}, {"pass_rate": 0.8})
        self.assertAlmostEqual(d, 0.1)

    def test_delta_negative_when_regressing(self):
        d = nightly._delta({"pass_rate": 0.5}, {"pass_rate": 0.9})
        self.assertAlmostEqual(d, -0.4)

    def test_regression_threshold_constant_is_five_percent(self):
        # Locked so nightly-eval CI matches docs/eval.md.
        self.assertAlmostEqual(nightly.REGRESSION_THRESHOLD, 0.05)


class NightlyReadLastRecordTests(unittest.TestCase):
    def test_missing_file_returns_none(self, tmp_prefix: str = "/tmp/eidolon_test_"):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(nightly._read_last_record(Path(td) / "nope.jsonl"))

    def test_reads_last_line(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "history.jsonl"
            p.write_text(
                json.dumps({"pass_rate": 0.5}) + "\n"
                + json.dumps({"pass_rate": 0.8}) + "\n"
            )
            got = nightly._read_last_record(p)
            self.assertEqual(got, {"pass_rate": 0.8})

    def test_empty_file_returns_none(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "history.jsonl"
            p.write_text("")
            self.assertIsNone(nightly._read_last_record(p))


class NightlyAppendTests(unittest.TestCase):
    def _fake_metrics(self, pass_rate: float) -> dict:
        return {
            "schema": 1,
            "seed": 42,
            "total": 20,
            "passed": int(round(pass_rate * 20)),
            "pass_rate": pass_rate,
            "misses": [],
        }

    def test_appends_record_and_exits_ok_when_stable(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            hist = Path(td) / "history.jsonl"
            hist.write_text(json.dumps(self._fake_metrics(0.90)) + "\n")

            with mock.patch.object(nightly, "_run_suite", return_value=self._fake_metrics(0.90)):
                buf = io.StringIO()
                real = sys.stdout
                try:
                    sys.stdout = buf
                    rc = nightly.main(["--history", str(hist), "--ts", "2026-01-01T00:00:00Z"])
                finally:
                    sys.stdout = real

            self.assertEqual(rc, nightly.EXIT_OK)
            lines = hist.read_text().strip().splitlines()
            self.assertEqual(len(lines), 2)
            last = json.loads(lines[-1])
            self.assertEqual(last["ts"], "2026-01-01T00:00:00Z")
            self.assertEqual(last["pass_rate"], 0.90)

    def test_regression_returns_degraded(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            hist = Path(td) / "history.jsonl"
            hist.write_text(json.dumps(self._fake_metrics(0.90)) + "\n")

            # 0.90 -> 0.80 is a 10-percentage-point drop, > 5% threshold.
            with mock.patch.object(nightly, "_run_suite", return_value=self._fake_metrics(0.80)):
                real = sys.stdout
                sys.stdout = io.StringIO()
                try:
                    rc = nightly.main(["--history", str(hist), "--ts", "2026-01-02T00:00:00Z"])
                finally:
                    sys.stdout = real

            self.assertEqual(rc, nightly.EXIT_DEGRADED)
            lines = hist.read_text().strip().splitlines()
            # Even on regression, the new record is appended.
            self.assertEqual(len(lines), 2)

    def test_small_drop_below_threshold_is_ok(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            hist = Path(td) / "history.jsonl"
            hist.write_text(json.dumps(self._fake_metrics(0.90)) + "\n")

            # 0.90 -> 0.88: 2-point drop, below 5% threshold.
            with mock.patch.object(nightly, "_run_suite", return_value=self._fake_metrics(0.88)):
                real = sys.stdout
                sys.stdout = io.StringIO()
                try:
                    rc = nightly.main(["--history", str(hist)])
                finally:
                    sys.stdout = real

            self.assertEqual(rc, nightly.EXIT_OK)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
