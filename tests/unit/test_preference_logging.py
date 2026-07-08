# SPDX-License-Identifier: Apache-2.0
"""Unit tests for preference-pair logging (REC-009)."""

from __future__ import annotations

import hashlib
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

from eidolon.learning.preferences import (  # noqa: E402
    SCHEMA,
    PreferencePair,
    _derive_pair_id,
    count,
    emit_bandit_outcome,
    emit_rollback_event,
    iter_pairs,
    log_pair,
    preferences_path,
)


def _ctx(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class SchemaTests(unittest.TestCase):
    def test_schema_frozen_at_one(self) -> None:
        self.assertEqual(SCHEMA, 1)
        self.assertEqual(PreferencePair().schema, 1)

    def test_dataclass_fields_are_exactly_the_frozen_set(self) -> None:
        expected = {"schema", "ts", "pair_id", "chosen_id", "rejected_id", "context_hash", "source"}
        actual = set(PreferencePair().as_dict().keys())
        self.assertEqual(actual, expected)


class LogPairValidationTests(unittest.TestCase):
    def _isolated(self) -> tempfile.TemporaryDirectory:
        td = tempfile.TemporaryDirectory()
        os.environ["EIDOLON_HOME"] = td.name
        return td

    def test_empty_ids_raise(self) -> None:
        td = self._isolated()
        try:
            with self.assertRaises(ValueError):
                log_pair("", "b", "bandit", _ctx("c"))
            with self.assertRaises(ValueError):
                log_pair("a", "", "bandit", _ctx("c"))
        finally:
            os.environ.pop("EIDOLON_HOME", None)
            td.cleanup()

    def test_identical_ids_raise(self) -> None:
        td = self._isolated()
        try:
            with self.assertRaises(ValueError):
                log_pair("a", "a", "bandit", _ctx("c"))
        finally:
            os.environ.pop("EIDOLON_HOME", None)
            td.cleanup()

    def test_unknown_source_raises(self) -> None:
        td = self._isolated()
        try:
            with self.assertRaises(ValueError):
                log_pair("a", "b", "invented", _ctx("c"))
        finally:
            os.environ.pop("EIDOLON_HOME", None)
            td.cleanup()

    def test_non_sha256_context_raises(self) -> None:
        td = self._isolated()
        try:
            with self.assertRaises(ValueError):
                log_pair("a", "b", "bandit", "not-a-hash")
            with self.assertRaises(ValueError):
                log_pair("a", "b", "bandit", "z" * 64)  # non-hex
        finally:
            os.environ.pop("EIDOLON_HOME", None)
            td.cleanup()


class LogPairPersistenceTests(unittest.TestCase):
    def test_append_and_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            os.environ["EIDOLON_HOME"] = td
            try:
                r1 = log_pair("arm-A", "arm-B", "bandit", _ctx("ctx-1"), ts=1.0)
                pairs = list(iter_pairs())
                self.assertEqual(len(pairs), 1)
                self.assertEqual(pairs[0].chosen_id, "arm-A")
                self.assertEqual(pairs[0].rejected_id, "arm-B")
                self.assertEqual(pairs[0].source, "bandit")
                self.assertEqual(pairs[0].pair_id, r1.pair_id)
            finally:
                os.environ.pop("EIDOLON_HOME", None)

    def test_append_is_monotonic(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            os.environ["EIDOLON_HOME"] = td
            try:
                for i in range(10):
                    log_pair(f"a{i}", f"b{i}", "bandit", _ctx(f"ctx-{i}"), ts=float(i))
                self.assertEqual(count(), 10)
                # File monotonically grew.
                sz = preferences_path().stat().st_size
                log_pair("aX", "bX", "bandit", _ctx("ctx-X"), ts=99.0)
                self.assertGreater(preferences_path().stat().st_size, sz)
            finally:
                os.environ.pop("EIDOLON_HOME", None)

    def test_pair_id_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            os.environ["EIDOLON_HOME"] = td
            try:
                ch = _ctx("same")
                p1 = log_pair("a", "b", "bandit", ch, ts=1.0)
                self.assertEqual(p1.pair_id, _derive_pair_id("a", "b", ch))
                # Symmetric swap yields a DIFFERENT pair_id (order matters).
                p2 = log_pair("b", "a", "bandit", ch, ts=2.0)
                self.assertNotEqual(p1.pair_id, p2.pair_id)
            finally:
                os.environ.pop("EIDOLON_HOME", None)

    def test_iter_skips_corrupt_lines(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            os.environ["EIDOLON_HOME"] = td
            try:
                # Write a valid line + a corrupt line + another valid line.
                log_pair("a", "b", "bandit", _ctx("c1"), ts=1.0)
                path = preferences_path()
                with path.open("a", encoding="utf-8") as fh:
                    fh.write("this is not json\n")
                log_pair("c", "d", "bandit", _ctx("c2"), ts=2.0)
                pairs = list(iter_pairs())
                self.assertEqual(len(pairs), 2)
                self.assertEqual([p.chosen_id for p in pairs], ["a", "c"])
            finally:
                os.environ.pop("EIDOLON_HOME", None)

    def test_iter_skips_wrong_schema(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            os.environ["EIDOLON_HOME"] = td
            try:
                path = preferences_path()
                # Write a schema=99 line directly.
                fake = {"schema": 99, "chosen_id": "x", "rejected_id": "y", "pair_id": "z", "ts": 0.0, "context_hash": "0" * 64, "source": "bandit"}
                with path.open("w", encoding="utf-8") as fh:
                    fh.write(json.dumps(fake) + "\n")
                self.assertEqual(list(iter_pairs()), [])
            finally:
                os.environ.pop("EIDOLON_HOME", None)


class EmitterHashesRawContextTests(unittest.TestCase):
    """Callers pass raw context; emitters must hash before storing."""

    def test_bandit_emitter_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            os.environ["EIDOLON_HOME"] = td
            try:
                p = emit_bandit_outcome("A", "B", "some-context-string")
                # Stored context is a SHA256, not the input string.
                self.assertNotIn("some-context-string", p.context_hash)
                self.assertEqual(len(p.context_hash), 64)
                int(p.context_hash, 16)
            finally:
                os.environ.pop("EIDOLON_HOME", None)

    def test_rollback_emitter_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            os.environ["EIDOLON_HOME"] = td
            try:
                p = emit_rollback_event("prior", "current", "some-context-string")
                self.assertNotIn("some-context-string", p.context_hash)
                self.assertEqual(p.source, "rollback")
            finally:
                os.environ.pop("EIDOLON_HOME", None)


class SanitizationGrepTests(unittest.TestCase):
    """Roadmap invariant: preferences.py must not mention content/payload/body/raw."""

    def test_no_forbidden_tokens_in_preferences_module(self) -> None:
        target = _ROOT / "src" / "eidolon" / "learning" / "preferences.py"
        text = target.read_text(encoding="utf-8")
        forbidden = ["content", "payload", "body", "raw"]
        offenders = [tok for tok in forbidden if tok in text]
        self.assertEqual(
            offenders,
            [],
            msg=f"preferences.py contains forbidden tokens {offenders}; "
            "structural fields only per roadmap REC-009 sanitization contract",
        )


class DoctorPreferencesCheckTests(unittest.TestCase):
    def test_check_present_and_degraded_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            env = dict(os.environ)
            env["EIDOLON_HOME"] = td
            env["PYTHONPATH"] = str(_SRC)
            r = subprocess.run(
                [sys.executable, "-m", "eidolon", "doctor", "--json"],
                env=env, cwd=str(_ROOT), capture_output=True, text=True, timeout=30,
            )
            payload = json.loads(r.stdout)
            check = next((c for c in payload["checks"] if c["name"] == "preferences_schema"), None)
            self.assertIsNotNone(check, msg="preferences_schema check missing from doctor")
            self.assertEqual(check["status"], "DEGRADED")

    def test_check_passes_with_valid_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            os.environ["EIDOLON_HOME"] = td
            try:
                log_pair("a", "b", "bandit", _ctx("ctx"), ts=1.0)
            finally:
                os.environ.pop("EIDOLON_HOME", None)
            env = dict(os.environ)
            env["EIDOLON_HOME"] = td
            env["PYTHONPATH"] = str(_SRC)
            r = subprocess.run(
                [sys.executable, "-m", "eidolon", "doctor", "--json"],
                env=env, cwd=str(_ROOT), capture_output=True, text=True, timeout=30,
            )
            payload = json.loads(r.stdout)
            check = next((c for c in payload["checks"] if c["name"] == "preferences_schema"), None)
            self.assertIsNotNone(check)
            self.assertEqual(check["status"], "PASS")


class ReportIncludesPreferenceCountTests(unittest.TestCase):
    def test_report_json_has_preference_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            env = dict(os.environ)
            env["EIDOLON_HOME"] = td
            env["PYTHONPATH"] = str(_SRC)
            r = subprocess.run(
                [sys.executable, "-m", "eidolon", "report", "--json"],
                env=env, cwd=str(_ROOT), capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            payload = json.loads(r.stdout)
            self.assertIn("preference_pairs", payload)
            self.assertIsInstance(payload["preference_pairs"], int)


class LearnEmitsPreferencePairsTests(unittest.TestCase):
    def test_learn_step_writes_preference_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            env = dict(os.environ)
            env["EIDOLON_HOME"] = td
            env["PYTHONPATH"] = str(_SRC)
            r = subprocess.run(
                [sys.executable, "-m", "eidolon", "learn", "--step", "--iterations", "20", "--seed", "3"],
                env=env, cwd=str(_ROOT), capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            path = Path(td) / "preferences.jsonl"
            self.assertTrue(path.exists(), msg="preferences.jsonl not written by learn --step")
            lines = [l for l in path.read_text().splitlines() if l.strip()]
            self.assertGreater(len(lines), 0)
            # Every line must be schema=1 with the frozen field set.
            for l in lines:
                d = json.loads(l)
                self.assertEqual(d["schema"], 1)
                self.assertEqual(d["source"], "bandit")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
