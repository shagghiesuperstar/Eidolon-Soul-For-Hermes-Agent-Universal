# SPDX-License-Identifier: Apache-2.0
"""Regression: dream-cycle loop-closer drains pending outbox entries."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from eidolon.outbox import Outbox
from eidolon.memory.inmem import InMemAdapter

_H = ROOT / "skills" / "dream-cycle" / "handler.py"
_spec = importlib.util.spec_from_file_location("dream_handler", _H)
handler = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(handler)


class TestFlushLoopCloser(unittest.TestCase):
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

    def test_flush_drains_pending(self):
        ob = Outbox(home=self.home)
        for i in range(3):
            ob.capture({"kind": "lesson", "content": f"stale-{i}"})
        self.assertEqual(ob.pending_count(), 3)
        handler._flush_stale_outbox()
        self.assertEqual(Outbox(home=self.home).pending_count(), 0)
        self.assertEqual(len(self.adapter.retrieve(kind="lesson")), 3)


if __name__ == "__main__":
    unittest.main()
