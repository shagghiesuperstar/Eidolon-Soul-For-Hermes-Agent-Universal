# SPDX-License-Identifier: Apache-2.0
"""Regression: a dream cycle that flushes a lesson increments memory_retained.
Canary 2026-07-12: 139 runs, all metrics zero. Normal lesson flush touched no
counter (only SKILL_UPDATE+mark_done incremented proposals_applied).
"""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from eidolon.memory.inmem import InMemAdapter
from eidolon.judgment import metrics

_H = ROOT / "skills" / "dream-cycle" / "handler.py"
_spec = importlib.util.spec_from_file_location("dream_handler_m", _H)
handler = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(handler)


class TestDreamMetricsRecord(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.home = Path(self._td.name)
        self.saved = {}
        for k in ("EIDOLON_STATE_DIR", "EIDOLON_HOME"):
            self.saved[k] = handler.os.environ.get(k)
            handler.os.environ[k] = str(self.home)
        self.adapter = InMemAdapter()
        handler._ADAPTER = self.adapter

    def tearDown(self):
        for k, v in self.saved.items():
            if v is None:
                handler.os.environ.pop(k, None)
            else:
                handler.os.environ[k] = v
        handler._ADAPTER = None
        self._td.cleanup()

    def test_lesson_flush_increments_counter(self):
        before = metrics.load(eidolon_home=self.home)["memory_retained"]
        patterns = [{"kind": "preference", "count": 2, "sample": "user likes terse"}]
        lessons = handler.extract_lessons(patterns)
        self.assertEqual(len(lessons), 1)
        after = metrics.load(eidolon_home=self.home)["memory_retained"]
        self.assertGreater(after, before)


if __name__ == "__main__":
    unittest.main()
