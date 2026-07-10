# SPDX-License-Identifier: Apache-2.0
"""Unit tests for src/eidolon/outbox.py (REC-019)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from eidolon.outbox import Outbox, FlushResult  # noqa: E402
from eidolon.memory.inmem import InMemAdapter   # noqa: E402
from eidolon.memory.adapter import MemoryStoreError  # noqa: E402


class _FailingAdapter:
    """Adapter that always raises MemoryStoreError on store."""
    name = "failing"
    def store(self, entry):
        raise MemoryStoreError("backend down")
    def retrieve(self, *, kind=None, limit=50, since_ts=None):
        return []
    def consolidate(self):
        return 0


class _DuplicateAdapter:
    """Adapter that raises a 'duplicate' error on every store."""
    name = "duplicate"
    def store(self, entry):
        raise MemoryStoreError("duplicate entry exists")
    def retrieve(self, *, kind=None, limit=50, since_ts=None):
        return []
    def consolidate(self):
        return 0


class TestOutboxCapture(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.home = Path(self._td.name)
        self.box = Outbox(home=self.home)

    def tearDown(self):
        self._td.cleanup()

    def test_capture_creates_pending_file(self):
        self.box.capture({"kind": "lesson", "content": "x"})
        pending = self.home / "outbox" / "pending.jsonl"
        self.assertTrue(pending.exists())

    def test_capture_sets_eid(self):
        eid = self.box.capture({"kind": "lesson", "content": "y"})
        self.assertEqual(len(eid), 16)

    def test_capture_missing_kind_raises(self):
        with self.assertRaises(ValueError):
            self.box.capture({"content": "no kind"})

    def test_capture_missing_content_raises(self):
        with self.assertRaises(ValueError):
            self.box.capture({"kind": "lesson"})

    def test_pending_count(self):
        self.box.capture({"kind": "lesson", "content": "a"})
        self.box.capture({"kind": "lesson", "content": "b"})
        self.assertEqual(self.box.pending_count(), 2)


class TestOutboxFlush(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.home = Path(self._td.name)
        self.box = Outbox(home=self.home)
        self.adapter = InMemAdapter()

    def tearDown(self):
        self._td.cleanup()

    def test_flush_empty_returns_zero_counts(self):
        result = self.box.flush(self.adapter)
        self.assertEqual(result, FlushResult(flushed=0, skipped=0, failed=0))

    def test_pending_entries_flush_exactly_once(self):
        """Core idempotency gate: flushed=1, pending cleared after flush."""
        self.box.capture({"kind": "lesson", "content": "remember this"})
        result = self.box.flush(self.adapter)
        self.assertEqual(result.flushed, 1)
        self.assertEqual(result.failed, 0)
        # pending file must be gone after successful flush
        self.assertEqual(self.box.pending_count(), 0)
        # entry must be in the adapter
        entries = self.adapter.retrieve(kind="lesson")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["content"], "remember this")

    def test_failed_store_leaves_entry_in_pending(self):
        self.box.capture({"kind": "lesson", "content": "fragile"})
        result = self.box.flush(_FailingAdapter())
        self.assertEqual(result.failed, 1)
        self.assertEqual(result.flushed, 0)
        self.assertEqual(self.box.pending_count(), 1)

    def test_duplicate_store_counted_as_skipped(self):
        self.box.capture({"kind": "lesson", "content": "dup"})
        result = self.box.flush(_DuplicateAdapter())
        self.assertEqual(result.skipped, 1)
        self.assertEqual(result.failed, 0)
        self.assertEqual(self.box.pending_count(), 0)

    def test_partial_failure_leaves_only_failed_in_pending(self):
        """2 entries: first succeeds, second fails — only second stays pending."""
        self.box.capture({"kind": "lesson", "content": "ok"})
        self.box.capture({"kind": "lesson", "content": "bad"})

        call_count = [0]
        original_store = self.adapter.store

        def selective_store(entry):
            call_count[0] += 1
            if entry.get("content") == "bad":
                raise MemoryStoreError("injected failure")
            original_store(entry)

        self.adapter.store = selective_store
        result = self.box.flush(self.adapter)
        self.assertEqual(result.flushed, 1)
        self.assertEqual(result.failed, 1)
        self.assertEqual(self.box.pending_count(), 1)
        remaining = self.box._load_pending()
        self.assertEqual(remaining[0]["content"], "bad")


if __name__ == "__main__":
    unittest.main()
