# SPDX-License-Identifier: Apache-2.0
"""Unit tests for REC-020: MemoryAdapter wiring in the dream-cycle handler."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

# Import the handler functions we're testing.
import importlib
import types

# We need to import handler.py as a module.
# It lives outside src/ so we load it by path.
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


def _reset_adapter():
    """Clear the module-level adapter singleton between tests."""
    _handler._ADAPTER = None


class TestIngest(unittest.TestCase):
    def setUp(self):
        _reset_adapter()

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
        self.assertIn("reflection", kinds)
        self.assertEqual(len(result), 2)


class TestReflect(unittest.TestCase):
    def test_reflect_empty_returns_empty(self):
        result = _handler.reflect([])
        self.assertEqual(result, [])

    def test_reflect_clusters_by_kind(self):
        episodes = [
            {"kind": "lesson", "content": "a", "ts": 1.0},
            {"kind": "lesson", "content": "b", "ts": 2.0},
            {"kind": "reflection", "content": "c", "ts": 3.0},
        ]
        patterns = _handler.reflect(episodes)
        kinds = {p["kind"] for p in patterns}
        self.assertEqual(kinds, {"lesson", "reflection"})
        lesson_pattern = next(p for p in patterns if p["kind"] == "lesson")
        self.assertEqual(lesson_pattern["count"], 2)

    def test_reflect_sample_is_most_recent(self):
        episodes = [
            {"kind": "lesson", "content": "older", "ts": 1.0},
            {"kind": "lesson", "content": "newer", "ts": 2.0},
        ]
        patterns = _handler.reflect(episodes)
        self.assertEqual(patterns[0]["sample"], "newer")


class TestExtractLessons(unittest.TestCase):
    def setUp(self):
        _reset_adapter()

    def test_extract_lessons_writes_to_adapter(self):
        adapter = _CapturingAdapter()
        patterns = [{"kind": "lesson", "count": 3, "sample": "sample text"}]
        with patch.object(_handler, "_EIDOLON_AVAILABLE", True):
            with patch.object(_handler, "_ADAPTER", adapter):
                lessons = _handler.extract_lessons(patterns)
        self.assertEqual(len(lessons), 1)
        stored = adapter.retrieve(kind="lesson")
        self.assertEqual(len(stored), 1)
        self.assertIn("3 time", stored[0]["content"])

    def test_extract_lessons_degrades_on_store_error(self):
        """Store failure must not raise — lesson is still returned."""
        patterns = [{"kind": "lesson", "count": 1, "sample": "x"}]
        with patch.object(_handler, "_EIDOLON_AVAILABLE", True):
            with patch.object(_handler, "_ADAPTER", _FailingAdapter()):
                lessons = _handler.extract_lessons(patterns)
        self.assertEqual(len(lessons), 1)


class TestPropose(unittest.TestCase):
    def setUp(self):
        _reset_adapter()

    def test_propose_writes_to_adapter(self):
        adapter = _CapturingAdapter()
        lessons = [{
            "kind": "lesson",
            "content": "some lesson",
            "source_kind": "reflection",
            "source_count": 2,
        }]
        with patch.object(_handler, "_EIDOLON_AVAILABLE", True):
            with patch.object(_handler, "_ADAPTER", adapter):
                candidates = _handler.propose(lessons)
        self.assertEqual(len(candidates), 1)
        stored = adapter.retrieve(kind="proposal")
        self.assertEqual(len(stored), 1)
        self.assertIn("reflection", stored[0]["content"])

    def test_propose_degrades_on_store_error(self):
        """Store failure must not raise — candidate is still returned."""
        lessons = [{"kind": "lesson", "content": "x",
                    "source_kind": "lesson", "source_count": 1}]
        with patch.object(_handler, "_EIDOLON_AVAILABLE", True):
            with patch.object(_handler, "_ADAPTER", _FailingAdapter()):
                candidates = _handler.propose(lessons)
        self.assertEqual(len(candidates), 1)


if __name__ == "__main__":
    unittest.main()
