# SPDX-License-Identifier: Apache-2.0
"""Tests for `eidolon learn --step` end-to-end (REC-008)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


class LearnCommandTests(unittest.TestCase):
    def _env(self, home: str) -> dict:
        env = dict(os.environ)
        env["EIDOLON_HOME"] = home
        env["PYTHONPATH"] = str(_SRC)
        return env

    def test_step_writes_replay(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            env = self._env(td)
            r = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "eidolon",
                    "learn",
                    "--step",
                    "--iterations",
                    "25",
                    "--seed",
                    "42",
                ],
                capture_output=True,
                text=True,
                env=env,
                cwd=str(_ROOT),
                timeout=60,
            )
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            payload = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertEqual(payload["iterations"], 25)
            self.assertEqual(payload["seed"], 42)
            self.assertGreaterEqual(len(payload["arms"]), 1)
            # replay.jsonl should have 25 lines.
            rp = Path(td) / "replay.jsonl"
            self.assertTrue(rp.exists())
            self.assertEqual(sum(1 for _ in rp.read_text().splitlines()), 25)

    def test_step_reproducible_with_same_seed(self) -> None:
        with tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
            args = [
                sys.executable,
                "-m",
                "eidolon",
                "learn",
                "--step",
                "--iterations",
                "40",
                "--seed",
                "7",
            ]
            r1 = subprocess.run(args, env=self._env(td1), cwd=str(_ROOT), capture_output=True, text=True, timeout=60)
            r2 = subprocess.run(args, env=self._env(td2), cwd=str(_ROOT), capture_output=True, text=True, timeout=60)
            self.assertEqual(r1.returncode, 0, msg=r1.stderr)
            self.assertEqual(r2.returncode, 0, msg=r2.stderr)
            p1 = (Path(td1) / "replay.jsonl").read_text()
            p2 = (Path(td2) / "replay.jsonl").read_text()
            # ts is deterministic (stable_ts=True by default), so files match.
            self.assertEqual(p1, p2)

    def test_missing_step_flag_is_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            r = subprocess.run(
                [sys.executable, "-m", "eidolon", "learn"],
                env=self._env(td),
                cwd=str(_ROOT),
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("--step", r.stderr)

    def test_report_includes_bandit_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            env = self._env(td)
            subprocess.run(
                [sys.executable, "-m", "eidolon", "learn", "--step", "--iterations", "10", "--seed", "1"],
                env=env, cwd=str(_ROOT), capture_output=True, text=True, timeout=60, check=True,
            )
            r = subprocess.run(
                [sys.executable, "-m", "eidolon", "report", "--json"],
                env=env, cwd=str(_ROOT), capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            payload = json.loads(r.stdout)
            self.assertIn("bandit_arms", payload)
            self.assertIn("bandit_episodes", payload)
            self.assertGreater(payload["bandit_arms"], 0)
            self.assertGreaterEqual(payload["bandit_episodes"], 10)

    def test_doctor_learning_check_present(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            r = subprocess.run(
                [sys.executable, "-m", "eidolon", "doctor", "--json"],
                env=self._env(td), cwd=str(_ROOT), capture_output=True, text=True, timeout=30,
            )
            payload = json.loads(r.stdout)
            names = [c["name"] for c in payload["checks"]]
            self.assertIn("learning_bandit_ready", names)

    def test_regression_suite_passes_at_seed_42(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(_SRC)
        r = subprocess.run(
            [sys.executable, "-m", "tests.eval.regression_suite", "--seed", "42"],
            env=env, cwd=str(_ROOT), capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(r.returncode, 0, msg=r.stderr + r.stdout)
        self.assertIn("20/20 cases passed", r.stdout)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
