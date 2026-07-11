# SPDX-License-Identifier: Apache-2.0
"""Unit tests: eidolon report surfaces Judgment Brain counters.

All tests use a tmp EIDOLON_STATE_DIR so they are fully isolated.
They fail before this fix (Report has no judgment fields, build() ignores
judgment.* events) and pass after.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TestReportJudgmentFields(unittest.TestCase):
    """Report dataclass exposes the five judgment counters."""

    def test_report_has_judgment_fields(self):
        from eidolon.reporting.metrics import Report
        r = Report()
        self.assertEqual(r.lessons_judged, 0)
        self.assertEqual(r.soul_edicts, 0)
        self.assertEqual(r.skills_modified, 0)
        self.assertEqual(r.config_changes, 0)
        self.assertEqual(r.memory_retired, 0)

    def test_as_dict_includes_judgment_fields(self):
        from eidolon.reporting.metrics import Report
        d = Report(lessons_judged=3, soul_edicts=1).as_dict()
        self.assertIn("lessons_judged", d)
        self.assertIn("soul_edicts", d)
        self.assertIn("skills_modified", d)
        self.assertIn("config_changes", d)
        self.assertIn("memory_retired", d)


class TestBuildAggregatesJudgmentEvents(unittest.TestCase):
    """build() counts judgment.* events from events.jsonl."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        os.environ["EIDOLON_STATE_DIR"] = self._tmp

    def tearDown(self):
        del os.environ["EIDOLON_STATE_DIR"]

    def _write_events(self, records):
        path = Path(self._tmp) / "events.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec) + "\n")

    def test_judgment_events_counted(self):
        import time
        now = time.time()
        self._write_events([
            {"ts": now - 10, "kind": "judgment.judged",  "status": "ok"},
            {"ts": now - 9,  "kind": "judgment.judged",  "status": "ok"},
            {"ts": now - 8,  "kind": "judgment.soul",    "status": "ok"},
            {"ts": now - 7,  "kind": "judgment.skill",   "status": "ok"},
            {"ts": now - 6,  "kind": "judgment.config",  "status": "ok"},
            {"ts": now - 5,  "kind": "judgment.retire",  "status": "ok"},
        ])
        from eidolon.reporting.metrics import build
        r = build(window="1h", now_ts=now)
        self.assertEqual(r.lessons_judged, 2)
        self.assertEqual(r.soul_edicts, 1)
        self.assertEqual(r.skills_modified, 1)
        self.assertEqual(r.config_changes, 1)
        self.assertEqual(r.memory_retired, 1)

    def test_events_outside_window_not_counted(self):
        import time
        now = time.time()
        self._write_events([
            {"ts": now - 7300, "kind": "judgment.judged", "status": "ok"},  # >2h ago
        ])
        from eidolon.reporting.metrics import build
        r = build(window="1h", now_ts=now)
        self.assertEqual(r.lessons_judged, 0)


class TestJudgmentMetricsRecord(unittest.TestCase):
    """judgment/metrics.py record() increments counters and emits events."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        os.environ["EIDOLON_STATE_DIR"] = self._tmp

    def tearDown(self):
        del os.environ["EIDOLON_STATE_DIR"]

    def test_record_soul_edict(self):
        from eidolon.judgment.metrics import record, load
        record("SOUL_EDICT")
        data = load()
        self.assertEqual(data["lessons_judged"], 1)
        self.assertEqual(data["soul_edicts"], 1)
        self.assertEqual(data["skills_modified"], 0)

    def test_record_skill_update(self):
        from eidolon.judgment.metrics import record, load
        record("SKILL_UPDATE")
        data = load()
        self.assertEqual(data["skills_modified"], 1)

    def test_record_memory_retain_noop_sub_counter(self):
        from eidolon.judgment.metrics import record, load
        record("MEMORY_RETAIN")
        data = load()
        self.assertEqual(data["lessons_judged"], 1)
        self.assertEqual(data["soul_edicts"], 0)
        self.assertEqual(data["skills_modified"], 0)

    def test_record_increments_cumulatively(self):
        from eidolon.judgment.metrics import record, load
        record("SOUL_EDICT")
        record("SOUL_EDICT")
        record("CONFIG_TUNE")
        data = load()
        self.assertEqual(data["lessons_judged"], 3)
        self.assertEqual(data["soul_edicts"], 2)
        self.assertEqual(data["config_changes"], 1)


class TestReportDeltaJudgment(unittest.TestCase):
    """_delta() includes all five judgment fields."""

    def test_delta_has_judgment_keys(self):
        from eidolon.reporting.metrics import Report
        from eidolon.commands.report import _delta
        r1 = Report(lessons_judged=5, soul_edicts=2, skills_modified=1,
                    config_changes=1, memory_retired=1)
        r2 = Report(lessons_judged=3, soul_edicts=1, skills_modified=0,
                    config_changes=0, memory_retired=0)
        d = _delta(r1, r2)
        self.assertEqual(d["lessons_judged"], 2)
        self.assertEqual(d["soul_edicts"], 1)
        self.assertEqual(d["skills_modified"], 1)
        self.assertEqual(d["config_changes"], 1)
        self.assertEqual(d["memory_retired"], 1)


class TestPrintHumanJudgment(unittest.TestCase):
    """_print_human() emits judgment section when not empty."""

    def test_judgment_section_in_output(self):
        import io
        from contextlib import redirect_stdout
        from eidolon.reporting.metrics import Report
        from eidolon.commands.report import _print_human
        r = Report(
            window="24h", empty_state=False,
            lessons_judged=4, soul_edicts=2, skills_modified=1,
            config_changes=0, memory_retired=1,
        )
        delta = {k: 0 for k in [
            "sessions_observed", "lessons_added", "proposals_generated",
            "proposals_applied", "rollback_count", "inference_requests",
            "lessons_judged", "soul_edicts", "skills_modified",
            "config_changes", "memory_retired",
        ]}
        buf = io.StringIO()
        with redirect_stdout(buf):
            _print_human(r, delta)
        output = buf.getvalue()
        self.assertIn("judgment brain", output)
        self.assertIn("lessons judged", output)
        self.assertIn("soul edicts", output)
        self.assertIn("skills modified", output)
        self.assertIn("memory lines retired", output)


if __name__ == "__main__":
    unittest.main()
