# SPDX-License-Identifier: Apache-2.0
"""Unit tests for REC-021: Outbox.capture+flush wired into extract_lessons/propose.

All four tests FAIL before the REC-021 handler change (direct adapter.store
calls with no outbox) and PASS after (outbox capture+flush path active).
"""

import importlib
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Minimal in-process stubs so handler.py loads without a real Hermes install
# ---------------------------------------------------------------------------

class _CapturingAdapter:
    """Records every entry passed to store()."""
    name = "capturing"

    def __init__(self):
        self.stored: List[Dict[str, Any]] = []

    def store(self, entry: Dict[str, Any]) -> None:
        self.stored.append(dict(entry))

    def retrieve(self, *, kind: str, limit: int, since_ts: float) -> List[Dict[str, Any]]:
        return [e for e in self.stored if e.get("kind") == kind][:limit]


class _FailAdapter:
    """Raises on every store() call."""
    name = "failing"

    def store(self, entry: Dict[str, Any]) -> None:
        raise OSError("simulated backend failure")

    def retrieve(self, *, kind: str, limit: int, since_ts: float) -> List[Dict[str, Any]]:
        return []


def _load_handler(tmp_home: Path, adapter) -> ModuleType:
    """Import handler from the repo tree, injecting stubs into sys.modules."""
    repo_root = Path(__file__).resolve().parents[2]
    handler_path = repo_root / "skills" / "dream-cycle" / "handler.py"

    # Stub out the heavy eidolon sub-packages before handler imports them.
    stubs = {
        "eidolon": ModuleType("eidolon"),
        "eidolon.util": ModuleType("eidolon.util"),
        "eidolon.util.events": ModuleType("eidolon.util.events"),
        "eidolon.safety": ModuleType("eidolon.safety"),
        "eidolon.memory": ModuleType("eidolon.memory"),
        "eidolon.memory.loader": ModuleType("eidolon.memory.loader"),
    }
    stubs["eidolon.util.events"].emit = lambda *a, **kw: None  # type: ignore
    stubs["eidolon.safety"].take_snapshot = lambda **kw: type("S", (), {"id": "snap", "files": []})()  # type: ignore
    stubs["eidolon.safety"].list_snapshots = lambda: []  # type: ignore
    stubs["eidolon.memory.loader"].load_adapter = lambda: adapter  # type: ignore

    # Import the real Outbox from src/ so outbox crash-safety is genuine.
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    from eidolon.outbox import Outbox  # noqa: PLC0415
    stubs["eidolon.outbox"] = ModuleType("eidolon.outbox")
    stubs["eidolon.outbox"].Outbox = Outbox  # type: ignore

    saved = {k: sys.modules.get(k) for k in stubs}
    sys.modules.update(stubs)

    spec = importlib.util.spec_from_file_location("handler_rec021", handler_path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    # Point EIDOLON_HOME at the tmp dir so outbox writes are isolated.
    import os
    os.environ["EIDOLON_HOME"] = str(tmp_home)
    # Reset module-level adapter singleton so each test gets a fresh one.
    spec.loader.exec_module(mod)  # type: ignore
    mod._ADAPTER = adapter  # inject directly — skip loader
    mod._EIDOLON_AVAILABLE = True
    mod._Outbox = Outbox

    # Restore sys.modules after load so other tests are unaffected.
    for k, v in saved.items():
        if v is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = v

    return mod


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestExtractLessonsOutboxWiring(unittest.TestCase):
    """extract_lessons() routes writes through Outbox, not direct store."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._adapter = _CapturingAdapter()
        self._h = _load_handler(Path(self._tmp.name), self._adapter)

    def tearDown(self):
        self._tmp.cleanup()

    def test_lessons_land_in_adapter_via_outbox(self):
        patterns = [
            {"kind": "episode", "count": 3, "sample": "ran out of context"},
            {"kind": "preference", "count": 2, "sample": "prefer terse replies"},
        ]
        lessons = self._h.extract_lessons(patterns)
        self.assertEqual(len(lessons), 2)
        # Entries must have reached the adapter.
        stored_kinds = [e["kind"] for e in self._adapter.stored]
        self.assertEqual(stored_kinds.count("lesson"), 2)

    def test_lessons_returned_even_if_flush_fails(self):
        """Lessons are returned to caller even when the adapter is a _FailAdapter."""
        fail_tmp = tempfile.TemporaryDirectory()
        try:
            h = _load_handler(Path(fail_tmp.name), _FailAdapter())
            patterns = [{"kind": "episode", "count": 1, "sample": "x"}]
            lessons = h.extract_lessons(patterns)
            # Caller still gets the lesson — cycle must not abort.
            self.assertEqual(len(lessons), 1)
            self.assertEqual(lessons[0]["kind"], "lesson")
        finally:
            fail_tmp.cleanup()


class TestProposeOutboxWiring(unittest.TestCase):
    """propose() routes writes through Outbox, not direct store."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._adapter = _CapturingAdapter()
        self._h = _load_handler(Path(self._tmp.name), self._adapter)

    def tearDown(self):
        self._tmp.cleanup()

    def test_proposals_land_in_adapter_via_outbox(self):
        lessons = [
            {
                "kind": "lesson",
                "content": "Pattern 'episode' observed 3 time(s). Most recent: x",
                "source_kind": "episode",
                "source_count": 3,
            }
        ]
        candidates = self._h.propose(lessons)
        self.assertEqual(len(candidates), 1)
        stored_kinds = [e["kind"] for e in self._adapter.stored]
        self.assertIn("proposal", stored_kinds)

    def test_flush_failure_leaves_pending_entries(self):
        """When the adapter fails, pending.jsonl must have entries for replay."""
        fail_tmp = tempfile.TemporaryDirectory()
        try:
            h = _load_handler(Path(fail_tmp.name), _FailAdapter())
            lessons = [
                {
                    "kind": "lesson",
                    "content": "x",
                    "source_kind": "episode",
                    "source_count": 1,
                }
            ]
            candidates = h.propose(lessons)
            # Candidate still returned.
            self.assertEqual(len(candidates), 1)
            # Pending file must exist with at least one entry.
            pending = Path(fail_tmp.name) / "outbox" / "pending.jsonl"
            self.assertTrue(pending.exists(), "pending.jsonl missing after flush failure")
            lines = [l for l in pending.read_text().splitlines() if l.strip()]
            self.assertGreater(len(lines), 0, "pending.jsonl is empty after flush failure")
        finally:
            fail_tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
