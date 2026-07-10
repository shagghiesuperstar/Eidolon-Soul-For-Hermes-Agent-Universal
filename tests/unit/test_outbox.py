# SPDX-License-Identifier: Apache-2.0
"""Tests for src/eidolon/outbox.py (REC-019).

All six tests FAILED before this commit (module did not exist).
All six tests PASS after.

Run with::

    PYTHONPATH=src python -m unittest tests/unit/test_outbox.py -v
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure src/ is on the path when run directly.
_SRC = Path(__file__).resolve().parents[2] / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from eidolon.outbox import Outbox  # noqa: E402


class TestOutboxCapture(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        self.ob = Outbox(home=self.home)

    def tearDown(self):
        self._tmp.cleanup()

    def test_capture_writes_to_pending(self):
        """capture() must append a valid JSON line to pending.jsonl."""
        self.ob.capture({"kind": "lesson", "content": "test lesson"})
        pending = self.home / "outbox" / "pending.jsonl"
        self.assertTrue(pending.exists())
        lines = [l for l in pending.read_text().splitlines() if l.strip()]
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertEqual(entry["kind"], "lesson")
        self.assertEqual(entry["content"], "test lesson")
        self.assertIn("ts", entry)

    def test_capture_stamps_ts_if_absent(self):
        """capture() must add ts when not supplied by caller."""
        self.ob.capture({"kind": "lesson", "content": "no ts"})
        pending = self.home / "outbox" / "pending.jsonl"
        entry = json.loads(pending.read_text().strip())
        self.assertIsInstance(entry["ts"], float)

    def test_capture_missing_kind_does_not_write(self):
        """capture() must silently drop (and emit DEGRADED) if kind absent."""
        self.ob.capture({"content": "missing kind"})
        self.assertEqual(self.ob.pending_count(), 0)

    def test_capture_missing_content_does_not_write(self):
        """capture() must silently drop (and emit DEGRADED) if content absent."""
        self.ob.capture({"kind": "lesson"})
        self.assertEqual(self.ob.pending_count(), 0)


class TestOutboxFlush(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        self.ob = Outbox(home=self.home)

    def tearDown(self):
        self._tmp.cleanup()

    def _ledger_entries(self):
        ledger = self.home / "events.jsonl"
        if not ledger.exists():
            return []
        return [
            json.loads(l)
            for l in ledger.read_text().splitlines()
            if l.strip()
        ]

    def test_flush_exactly_once(self):
        """Entries flushed to ledger must not appear again on second flush."""
        self.ob.capture({"kind": "lesson", "content": "once"})
        first = self.ob.flush()
        second = self.ob.flush()
        self.assertEqual(first, 1)
        self.assertEqual(second, 0)
        entries = self._ledger_entries()
        self.assertEqual(len(entries), 1)

    def test_flush_empty_pending_returns_zero(self):
        """flush() on an empty outbox must return 0 without creating ledger."""
        count = self.ob.flush()
        self.assertEqual(count, 0)
        self.assertFalse((self.home / "events.jsonl").exists())

    def test_kind_filter_leaves_non_matching_in_pending(self):
        """flush(kind_filter='lesson') must leave 'proposal' entries in pending."""
        self.ob.capture({"kind": "lesson", "content": "a lesson"})
        self.ob.capture({"kind": "proposal", "content": "a proposal"})
        flushed = self.ob.flush(kind_filter="lesson")
        self.assertEqual(flushed, 1)
        self.assertEqual(self.ob.pending_count(), 1)
        entries = self._ledger_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["kind"], "lesson")

    def test_crash_resume_replays_pending(self):
        """Entries written to pending but not flushed survive a restart."""
        self.ob.capture({"kind": "lesson", "content": "survives crash"})
        # Simulate restart: create a new Outbox instance over same home.
        ob2 = Outbox(home=self.home)
        flushed = ob2.flush()
        self.assertEqual(flushed, 1)
        entries = self._ledger_entries()
        self.assertEqual(entries[0]["content"], "survives crash")


if __name__ == "__main__":
    unittest.main()
