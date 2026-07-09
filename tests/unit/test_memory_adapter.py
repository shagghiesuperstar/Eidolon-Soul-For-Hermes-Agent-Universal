# SPDX-License-Identifier: Apache-2.0
"""REC-018: memory backend abstraction tests.

All 10 tests pass without a live Hermes host.

Test inventory:
  TestInMemAdapter          (6 tests) — round-trip, ts stamp, kind filter,
                                        since_ts filter, missing field error,
                                        consolidate no-op
  TestLoaderDegradesBehavior (2 tests) — default-to-hindsight, unknown-backend
  TestHindsightAdapter       (2 tests) — filesystem persistence, consolidation
"""

from __future__ import annotations

import time
import unittest

from tests.unit._tmphomes import IsolatedHome


class TestInMemAdapter(IsolatedHome):
    """InMemAdapter round-trips, filtering, consolidation."""

    def setUp(self) -> None:
        super().setUp()
        from eidolon.memory.inmem import InMemAdapter
        self.adapter = InMemAdapter()

    # ------------------------------------------------------------------
    # 1. Basic round-trip
    # ------------------------------------------------------------------
    def test_store_and_retrieve_round_trip(self) -> None:
        self.adapter.store({"kind": "lesson", "content": "always emit events"})
        hits = self.adapter.retrieve(kind="lesson")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["content"], "always emit events")

    # ------------------------------------------------------------------
    # 2. ts is stamped automatically
    # ------------------------------------------------------------------
    def test_store_stamps_ts_when_absent(self) -> None:
        before = time.time()
        self.adapter.store({"kind": "lesson", "content": "ts test"})
        after = time.time()
        hits = self.adapter.retrieve(kind="lesson")
        ts = hits[0]["ts"]
        self.assertGreaterEqual(ts, before)
        self.assertLessEqual(ts, after)

    # ------------------------------------------------------------------
    # 3. kind filter
    # ------------------------------------------------------------------
    def test_retrieve_filters_by_kind(self) -> None:
        self.adapter.store({"kind": "lesson", "content": "A"})
        self.adapter.store({"kind": "preference", "content": "B"})
        hits = self.adapter.retrieve(kind="lesson")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["content"], "A")

    # ------------------------------------------------------------------
    # 4. since_ts filter
    # ------------------------------------------------------------------
    def test_retrieve_filters_by_since_ts(self) -> None:
        old_ts = time.time() - 3600
        self.adapter.store({"kind": "lesson", "content": "old", "ts": old_ts})
        self.adapter.store({"kind": "lesson", "content": "new"})
        hits = self.adapter.retrieve(kind="lesson", since_ts=time.time() - 300)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["content"], "new")

    # ------------------------------------------------------------------
    # 5. Missing required field raises MemoryStoreError
    # ------------------------------------------------------------------
    def test_store_raises_on_missing_required_field(self) -> None:
        from eidolon.memory.adapter import MemoryStoreError
        with self.assertRaises(MemoryStoreError):
            self.adapter.store({"kind": "lesson"})  # missing 'content'

    # ------------------------------------------------------------------
    # 6. consolidate() is always 0 for InMemAdapter
    # ------------------------------------------------------------------
    def test_inmem_consolidate_returns_zero(self) -> None:
        self.adapter.store({"kind": "lesson", "content": "dup"})
        self.adapter.store({"kind": "lesson", "content": "dup"})
        self.assertEqual(self.adapter.consolidate(), 0)
        # Both entries still present (inmem does not deduplicate).
        self.assertEqual(self.adapter.count(), 2)


class TestLoaderDegradesBehavior(IsolatedHome):
    """loader.load_adapter() degrades correctly in various config states."""

    # ------------------------------------------------------------------
    # 7. No config file -> defaults to HindsightAdapter, emits INFO event
    # ------------------------------------------------------------------
    def test_loader_defaults_to_hindsight_when_no_config(self) -> None:
        from eidolon.memory.loader import load_adapter
        from eidolon.memory.hindsight import HindsightAdapter
        from eidolon.util.events import read as read_events

        adapter = load_adapter()
        self.assertIsInstance(adapter, HindsightAdapter)

        events = list(read_events())
        loader_events = [
            e for e in events
            if e.get("kind") == "memory.loader" and e.get("status") == "INFO"
        ]
        self.assertGreater(len(loader_events), 0)

    # ------------------------------------------------------------------
    # 8. Unknown backend in config -> falls back to InMemAdapter,
    #    emits DEGRADED event with configured value
    # ------------------------------------------------------------------
    def test_loader_degrades_to_inmem_on_unknown_backend(self) -> None:
        from eidolon.memory.loader import load_adapter
        from eidolon.memory.inmem import InMemAdapter
        from eidolon.util.events import read as read_events

        self.write_hermes_config("memory.backend: totally_unknown_backend\n")

        adapter = load_adapter()
        self.assertIsInstance(adapter, InMemAdapter)

        events = list(read_events())
        degraded = [
            e for e in events
            if e.get("kind") == "memory.loader" and e.get("status") == "DEGRADED"
        ]
        self.assertGreater(len(degraded), 0)
        self.assertIn("totally_unknown_backend", degraded[0].get("configured", ""))


class TestHindsightAdapter(IsolatedHome):
    """HindsightAdapter filesystem persistence and consolidation."""

    def setUp(self) -> None:
        super().setUp()
        from eidolon.memory.hindsight import HindsightAdapter
        self.adapter = HindsightAdapter()

    # ------------------------------------------------------------------
    # 9. Hindsight store persists across adapter instances
    # ------------------------------------------------------------------
    def test_hindsight_persists_to_disk(self) -> None:
        self.adapter.store({"kind": "lesson", "content": "persisted"})
        from eidolon.memory.hindsight import HindsightAdapter
        adapter2 = HindsightAdapter()
        hits = adapter2.retrieve(kind="lesson")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["content"], "persisted")

    # ------------------------------------------------------------------
    # 10. consolidate removes exact-content duplicates, keeps unique entries
    # ------------------------------------------------------------------
    def test_hindsight_consolidate_removes_exact_duplicates(self) -> None:
        for _ in range(3):
            self.adapter.store({"kind": "lesson", "content": "dup"})
        self.adapter.store({"kind": "lesson", "content": "unique"})
        removed = self.adapter.consolidate()
        self.assertEqual(removed, 2)  # 3 copies -> 1 kept = 2 removed
        hits = self.adapter.retrieve(kind="lesson")
        self.assertEqual(len(hits), 2)  # "dup" + "unique"


if __name__ == "__main__":
    unittest.main()
