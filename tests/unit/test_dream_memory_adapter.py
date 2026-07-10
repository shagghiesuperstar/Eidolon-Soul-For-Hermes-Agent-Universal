# SPDX-License-Identifier: Apache-2.0
"""Unit tests for REC-020 + REC-021: MemoryAdapter and Outbox wiring in the
dream-cycle handler."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]  # tests/unit -> repo root
sys.path.insert(0, str(ROOT / "src"))

import importlib
import importlib.util
import types

_handler_path = ROOT / "skills" / "dream-cycle" / "handler.py"
spec = importlib.util.spec_from_file_location("dream_handler", _handler_path)
_handler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_handler)


class _CapturingAdapter:
    """In-process memory adapter that captures store calls for inspection."""
    name = "capturing"

    def __init__(self):
        self._store: list = []

    def store(self, entry):
        self._store.append(dict(entry))

    def retrieve(self, *, kind=None, limit=50, since_ts=None):
        if kind is None:
            return list(self._store)
        return [e for e in self._store if e.get("kind") == kind]

    def consolidate(self):
        return 0


class _FailingAdapter:
    """Adapter whose store always raises."""
    name = "failing"

    def store(self, entry):
        raise RuntimeError("backend unavailable")

    def retrieve(self, *, kind=None, limit=50, since_ts=None):
        return []

    def consolidate(self):
        return 0


def _reset_singletons():
    """Clear module-level singletons between tests."""
    _handler._ADAPTER = None
    _handler._OUTBOX = None


class TestIngest(unittest.TestCase):
    def setUp(self):
        _reset_singletons()

    def test_ingest_returns_empty_when_adapter_unavailable(self):
        """When _EIDOLON_AVAILABLE is False, ingest returns [] without raising."""
        with patch.object(_handler, "_EIDOLON_AVAILABLE", False):
            with patch.object(_handler, "_ADAPTER", None):
                result = _handler.ingest("sessionend")
        self.assertEqual(result, [])

    def test_dream_run_recalls_from_backend(self):
        """Core REC-020 gate: ingest returns entries stored in the adapter."""
        adapter = _CapturingAdapter()
        adapter.store({"kind": "lesson", "content": "test lesson", "ts": 1.0})
        adapter.store({"kind": "reflection", "content": "test reflect", "ts": 2.0})

        with patch.object(_handler, "_EIDOLON_AVAILABLE", True):
            with patch.object(_handler, "_ADAPTER", adapter):
                result = _handler.ingest("scheduled")

        kinds = {e["kind"] for e in result}
        self.assertIn("lesson", kinds)


# ---------------------------------------------------------------------------
# REC-021: Outbox wiring tests
# ---------------------------------------------------------------------------

class TestExtractLessonsOutbox(unittest.TestCase):
    """REC-021 gate: extract_lessons captures each lesson via the outbox."""

    def setUp(self):
        _reset_singletons()

    def test_extract_lessons_captures_to_outbox(self):
        """After extract_lessons, entry is either pending or flushed via adapter."""
        from eidolon.outbox import Outbox

        adapter = _CapturingAdapter()
        patterns = [{"kind": "episode", "count": 3, "sample": "something happened"}]

        with tempfile.TemporaryDirectory() as tmp:
            outbox = Outbox(home=Path(tmp))

            with patch.object(_handler, "_EIDOLON_AVAILABLE", True):
                with patch.object(_handler, "_ADAPTER", adapter):
                    with patch.object(_handler, "_OUTBOX", outbox):
                        lessons = _handler.extract_lessons(patterns)

        self.assertEqual(len(lessons), 1)
        # After a successful flush the entry lands in adapter OR stays pending
        # if flush failed — at least one of the two must be non-empty.
        stored_lessons = [e for e in adapter._store if e.get("kind") == "lesson"]
        pending = outbox.pending_count()
        self.assertTrue(
            len(stored_lessons) > 0 or pending > 0,
            "lesson must be in adapter store or outbox pending after extract_lessons",
        )

    def test_extract_lessons_entry_in_adapter_on_success(self):
        """Happy path: lesson lands in adapter after capture+flush."""
        from eidolon.outbox import Outbox

        adapter = _CapturingAdapter()
        patterns = [{"kind": "preference", "count": 5, "sample": "user prefers terse"}]

        with tempfile.TemporaryDirectory() as tmp:
            outbox = Outbox(home=Path(tmp))

            with patch.object(_handler, "_EIDOLON_AVAILABLE", True):
                with patch.object(_handler, "_ADAPTER", adapter):
                    with patch.object(_handler, "_OUTBOX", outbox):
                        _handler.extract_lessons(patterns)

        stored = [e for e in adapter._store if e.get("kind") == "lesson"]
        self.assertEqual(len(stored), 1)
        self.assertIn("preference", stored[0]["content"])


class TestProposeOutbox(unittest.TestCase):
    """REC-021 gate: propose captures each proposal via the outbox."""

    def setUp(self):
        _reset_singletons()

    def test_propose_captures_to_outbox(self):
        """After propose, entry is either pending or flushed via adapter."""
        from eidolon.outbox import Outbox

        adapter = _CapturingAdapter()
        lessons = [{
            "kind": "lesson",
            "content": "Pattern 'episode' observed 3 time(s).",
            "source_kind": "episode",
            "source_count": 3,
        }]

        with tempfile.TemporaryDirectory() as tmp:
            outbox = Outbox(home=Path(tmp))

            with patch.object(_handler, "_EIDOLON_AVAILABLE", True):
                with patch.object(_handler, "_ADAPTER", adapter):
                    with patch.object(_handler, "_OUTBOX", outbox):
                        candidates = _handler.propose(lessons)

        self.assertEqual(len(candidates), 1)
        stored_proposals = [e for e in adapter._store if e.get("kind") == "proposal"]
        pending = outbox.pending_count()
        self.assertTrue(
            len(stored_proposals) > 0 or pending > 0,
            "proposal must be in adapter store or outbox pending after propose",
        )

    def test_propose_entry_in_adapter_on_success(self):
        """Happy path: proposal lands in adapter after capture+flush."""
        from eidolon.outbox import Outbox

        adapter = _CapturingAdapter()
        lessons = [{
            "kind": "lesson",
            "content": "Pattern 'reflection' observed 2 time(s).",
            "source_kind": "reflection",
            "source_count": 2,
        }]

        with tempfile.TemporaryDirectory() as tmp:
            outbox = Outbox(home=Path(tmp))

            with patch.object(_handler, "_EIDOLON_AVAILABLE", True):
                with patch.object(_handler, "_ADAPTER", adapter):
                    with patch.object(_handler, "_OUTBOX", outbox):
                        candidates = _handler.propose(lessons)

        stored = [e for e in adapter._store if e.get("kind") == "proposal"]
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["mutation_kind"], "preference_update")


class TestFlushFailureDegraded(unittest.TestCase):
    """REC-021 gate: adapter raise → DEGRADED event, function returns results."""

    def setUp(self):
        _reset_singletons()

    def _collect_degraded_events(self, fn, *args, **kwargs):
        """Run fn and collect any DEGRADED-status _emit calls."""
        emitted = []
        original_emit = _handler._emit

        def capturing_emit(kind, status="INFO", **payload):
            if status == "DEGRADED":
                emitted.append({"kind": kind, "status": status, **payload})
            original_emit(kind, status, **payload)

        with patch.object(_handler, "_emit", side_effect=capturing_emit):
            result = fn(*args, **kwargs)
        return result, emitted

    def test_flush_failure_degrades_not_raises_lessons(self):
        """extract_lessons: failing adapter → DEGRADED emitted, lessons returned."""
        from eidolon.outbox import Outbox

        failing = _FailingAdapter()
        patterns = [{"kind": "episode", "count": 1, "sample": "x"}]

        with tempfile.TemporaryDirectory() as tmp:
            outbox = Outbox(home=Path(tmp))

            with patch.object(_handler, "_EIDOLON_AVAILABLE", True):
                with patch.object(_handler, "_ADAPTER", failing):
                    with patch.object(_handler, "_OUTBOX", outbox):
                        lessons, degraded = self._collect_degraded_events(
                            _handler.extract_lessons, patterns
                        )

        # Must return candidates even on failure
        self.assertEqual(len(lessons), 1)
        # Must emit at least one DEGRADED event
        self.assertTrue(
            len(degraded) > 0,
            "expected at least one DEGRADED event when flush fails",
        )

    def test_flush_failure_degrades_not_raises_propose(self):
        """propose: failing adapter → DEGRADED emitted, candidates returned."""
        from eidolon.outbox import Outbox

        failing = _FailingAdapter()
        lessons = [{
            "kind": "lesson",
            "content": "Pattern 'episode' observed 1 time(s).",
            "source_kind": "episode",
            "source_count": 1,
        }]

        with tempfile.TemporaryDirectory() as tmp:
            outbox = Outbox(home=Path(tmp))

            with patch.object(_handler, "_EIDOLON_AVAILABLE", True):
                with patch.object(_handler, "_ADAPTER", failing):
                    with patch.object(_handler, "_OUTBOX", outbox):
                        candidates, degraded = self._collect_degraded_events(
                            _handler.propose, lessons
                        )

        self.assertEqual(len(candidates), 1)
        self.assertTrue(
            len(degraded) > 0,
            "expected at least one DEGRADED event when flush fails",
        )

    def test_flush_failure_leaves_entry_pending(self):
        """On store failure the outbox retains the entry for the next cycle."""
        from eidolon.outbox import Outbox

        failing = _FailingAdapter()
        patterns = [{"kind": "episode", "count": 2, "sample": "y"}]

        with tempfile.TemporaryDirectory() as tmp:
            outbox = Outbox(home=Path(tmp))

            with patch.object(_handler, "_EIDOLON_AVAILABLE", True):
                with patch.object(_handler, "_ADAPTER", failing):
                    with patch.object(_handler, "_OUTBOX", outbox):
                        _handler.extract_lessons(patterns)

            pending = outbox.pending_count()

        self.assertGreater(pending, 0, "failed entry must remain in outbox pending")


class TestCrashResume(unittest.TestCase):
    """REC-021 optional: pending entry from failed flush is flushed on second run."""

    def setUp(self):
        _reset_singletons()

    def test_pending_entry_flushed_on_second_run(self):
        """Entry stuck in pending after a failed store lands in adapter on retry."""
        from eidolon.outbox import Outbox

        patterns = [{"kind": "episode", "count": 1, "sample": "crash test"}]

        with tempfile.TemporaryDirectory() as tmp:
            outbox = Outbox(home=Path(tmp))

            # First run: adapter fails → entry stays pending.
            failing = _FailingAdapter()
            with patch.object(_handler, "_EIDOLON_AVAILABLE", True):
                with patch.object(_handler, "_ADAPTER", failing):
                    with patch.object(_handler, "_OUTBOX", outbox):
                        _handler.extract_lessons(patterns)

            self.assertGreater(outbox.pending_count(), 0)

            # Second run: adapter recovers → pending entry must flush.
            good_adapter = _CapturingAdapter()
            with patch.object(_handler, "_EIDOLON_AVAILABLE", True):
                with patch.object(_handler, "_ADAPTER", good_adapter):
                    with patch.object(_handler, "_OUTBOX", outbox):
                        _handler.extract_lessons(patterns)

        # Both the crash-surviving entry and the new one should be in adapter.
        stored = [e for e in good_adapter._store if e.get("kind") == "lesson"]
        self.assertGreaterEqual(
            len(stored), 1,
            "pending entry from failed first run must appear in adapter after recovery",
        )
        self.assertEqual(outbox.pending_count(), 0, "pending file must be empty after full flush")
