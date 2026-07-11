# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the v2.0 Judgment Brain.

All tests MUST fail before the judgment/ package exists and pass after.
Run with: PYTHONPATH=src python -m unittest tests/unit/test_judgment.py
"""
import sys
import tempfile
import unittest
from pathlib import Path

SRC = str(Path(__file__).parent.parent.parent / "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from eidolon.judgment.classifier import ActionKind, classify_lesson
from eidolon.judgment.executor import execute_judgment
from eidolon.judgment.metrics import load_metrics, record_judgment
from eidolon.hermes_bridge import promote_lesson_to_hermes


class TestClassifier(unittest.TestCase):

    def test_soul_edict_never(self):
        kind, reason = classify_lesson("Never invent terminal output — always run the real command")
        self.assertEqual(kind, ActionKind.SOUL_EDICT)
        self.assertEqual(reason, "soul_signal")

    def test_soul_edict_must_verify(self):
        kind, _ = classify_lesson("Must verify before acting on any assumption about file paths")
        self.assertEqual(kind, ActionKind.SOUL_EDICT)

    def test_skill_update_probe(self):
        kind, reason = classify_lesson("Probe port before assuming service is running")
        self.assertEqual(kind, ActionKind.SKILL_UPDATE)
        self.assertEqual(reason, "skill_signal")

    def test_skill_update_paste_evidence(self):
        kind, _ = classify_lesson("Run the real command and paste evidence before claiming success")
        self.assertEqual(kind, ActionKind.SKILL_UPDATE)

    def test_config_tune_format(self):
        kind, _ = classify_lesson("Prefer concise bullet format in response output")
        self.assertEqual(kind, ActionKind.CONFIG_TUNE)

    def test_memory_retire_baked_in(self):
        kind, _ = classify_lesson("This pattern is now codified and baked in to skill file")
        self.assertEqual(kind, ActionKind.MEMORY_RETIRE)

    def test_memory_retain_fallback(self):
        kind, reason = classify_lesson("Something observed three times in recent sessions")
        self.assertEqual(kind, ActionKind.MEMORY_RETAIN)
        self.assertEqual(reason, "no_signal")

    def test_empty_returns_retain(self):
        kind, reason = classify_lesson("")
        self.assertEqual(kind, ActionKind.MEMORY_RETAIN)
        self.assertEqual(reason, "empty")


class TestExecutor(unittest.TestCase):

    def _tmpdir(self):
        return Path(tempfile.mkdtemp())

    def test_skill_update_creates_file(self):
        hh = self._tmpdir()
        result = execute_judgment(
            ActionKind.SKILL_UPDATE,
            "Probe before assuming",
            hermes_home=hh,
        )
        self.assertEqual(result["status"], "ok")
        skill_file = hh / "skills" / "_eidolon_staging" / "eidolon-learned.md"
        self.assertTrue(skill_file.exists())
        self.assertIn("Probe before assuming", skill_file.read_text())

    def test_soul_edict_writes_below_marker(self):
        hh = self._tmpdir()
        soul = hh / "SOUL.md"
        soul.write_text("# SOUL\n\nSome invariant text here.\n", encoding="utf-8")
        result = execute_judgment(
            ActionKind.SOUL_EDICT,
            "Never fabricate command output",
            hermes_home=hh,
        )
        self.assertEqual(result["status"], "ok")
        content = soul.read_text()
        self.assertIn("EIDOLON EDICTS", content)
        self.assertIn("Never fabricate command output", content)
        self.assertIn("Some invariant text here.", content)

    def test_soul_edict_dedup(self):
        hh = self._tmpdir()
        lesson = "Never fabricate command output"
        execute_judgment(ActionKind.SOUL_EDICT, lesson, hermes_home=hh)
        result = execute_judgment(ActionKind.SOUL_EDICT, lesson, hermes_home=hh)
        self.assertEqual(result["status"], "skip")

    def test_config_tune_creates_prefs_file(self):
        hh = self._tmpdir()
        result = execute_judgment(
            ActionKind.CONFIG_TUNE,
            "Prefer concise bullet format",
            hermes_home=hh,
        )
        self.assertEqual(result["status"], "ok")
        prefs = hh / "memories" / "eidolon-prefs.md"
        self.assertTrue(prefs.exists())
        self.assertIn("Prefer concise bullet format", prefs.read_text())

    def test_memory_retire_removes_line(self):
        hh = self._tmpdir()
        mem = hh / "memories" / "MEMORY.md"
        mem.parent.mkdir(parents=True, exist_ok=True)
        mem.write_text(
            "§\nEIDOLON LEARNED:\n- Probe before assuming the service is up\n§\n",
            encoding="utf-8",
        )
        result = execute_judgment(
            ActionKind.MEMORY_RETIRE,
            "Probe before assuming the service is up",
            hermes_home=hh,
        )
        self.assertEqual(result["status"], "ok")
        self.assertNotIn("Probe before assuming", mem.read_text())

    def test_memory_retain_is_noop(self):
        hh = self._tmpdir()
        result = execute_judgment(
            ActionKind.MEMORY_RETAIN,
            "Something vague observed in sessions",
            hermes_home=hh,
        )
        self.assertEqual(result["status"], "skip")


class TestMetrics(unittest.TestCase):

    def test_record_and_load(self):
        with tempfile.TemporaryDirectory() as td:
            eh = Path(td)
            record_judgment("skill_update", "ok", "Probe before assuming", eidolon_home=eh)
            record_judgment("soul_edict", "ok", "Never fabricate", eidolon_home=eh)
            record_judgment("config_tune", "ok", "Prefer concise", eidolon_home=eh)
            record_judgment("memory_retire", "ok", "Baked in", eidolon_home=eh)
            record_judgment("skill_update", "skip", "Duplicate", eidolon_home=eh)
            m = load_metrics(eh)
            self.assertEqual(m["lessons_judged"], 5)
            self.assertEqual(m["skills_modified"], 1)
            self.assertEqual(m["soul_edicts"], 1)
            self.assertEqual(m["config_changes"], 1)
            self.assertEqual(m["memory_retired"], 1)
            self.assertEqual(m["skipped"], 1)


class TestBridgeJudgmentIntegration(unittest.TestCase):

    def test_promote_returns_judgment_fields(self):
        with tempfile.TemporaryDirectory() as td:
            hh = Path(td)
            eh = Path(td) / "eidolon"
            result = promote_lesson_to_hermes(
                "Never invent terminal output — always run the real command",
                hermes_home=hh,
                eidolon_home=eh,
            )
            self.assertEqual(result["status"], "ok")
            self.assertIn("judgment_kind", result)
            self.assertIn("judgment_status", result)
            self.assertIn("metrics", result)
            self.assertEqual(result["judgment_kind"], "soul_edict")


if __name__ == "__main__":
    unittest.main()
