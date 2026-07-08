"""REC-004: last_known_good on first success + rollback restores."""

from __future__ import annotations

import io
import json
import shutil
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tests.unit._tmphomes import IsolatedHome


class RollbackTests(IsolatedHome):
    def setUp(self) -> None:
        super().setUp()
        # Simulate a repo checkout with tracked files present.
        # Snapshot module resolves repo_root as `parents[3]` of util/paths.py,
        # which is the actual repo (this checkout). So no path mocking needed.
        from eidolon.util.paths import repo_root

        self.root = repo_root()
        self.assertTrue((self.root / "SOUL.md").exists())

    def test_take_snapshot_captures_tracked_files_and_writes_manifest(self) -> None:
        from eidolon.safety import take_snapshot, list_snapshots

        snap = take_snapshot(reason="unit_test")
        self.assertGreater(len(snap.files), 0)
        self.assertIn("SOUL.md", snap.files)
        self.assertTrue(Path(snap.path, "manifest.json").exists())
        # Manifest checksum is deterministic given the same file contents.
        self.assertTrue(snap.checksum)
        # list_snapshots must see the new snapshot.
        self.assertTrue(any(s.id == snap.id for s in list_snapshots()))

    def test_current_pointer_is_set_after_snapshot(self) -> None:
        from eidolon.safety.snapshot import take_snapshot, current_snapshot

        snap = take_snapshot()
        cur = current_snapshot()
        self.assertIsNotNone(cur)
        self.assertEqual(cur.id, snap.id)

    def test_rollback_missing_snapshot_returns_degraded_not_fail(self) -> None:
        from eidolon.cli import main

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["rollback", "--json"])
        data = json.loads(buf.getvalue().strip().splitlines()[-1])
        # DEGRADED exit code (2), not FAIL (1). "no snapshot" is loud, not crash.
        self.assertEqual(code, 2)
        self.assertFalse(data["ok"])
        self.assertIn("no last_known_good", data["reason"])

    def test_rollback_restores_from_snapshot(self) -> None:
        from eidolon.safety import take_snapshot, rollback_to_last_known_good

        # Take a baseline snapshot of the actual repo file.
        soul = self.root / "SOUL.md"
        original = soul.read_text(encoding="utf-8")
        try:
            snap = take_snapshot(reason="baseline")

            # Mutate SOUL.md to a known bad state.
            soul.write_text("CORRUPTED\n", encoding="utf-8")
            self.assertEqual(soul.read_text(encoding="utf-8"), "CORRUPTED\n")

            # Rollback restores the original bytes.
            result = rollback_to_last_known_good(dry_run=False)
            self.assertTrue(result.ok)
            self.assertIn("SOUL.md", result.restored)
            self.assertEqual(soul.read_text(encoding="utf-8"), original)
            self.assertEqual(result.snapshot_id, snap.id)
        finally:
            # Belt-and-braces: always restore original bytes.
            soul.write_text(original, encoding="utf-8")

    def test_dry_run_reports_plan_without_mutating(self) -> None:
        from eidolon.safety import take_snapshot, rollback_to_last_known_good

        soul = self.root / "SOUL.md"
        original = soul.read_text(encoding="utf-8")
        try:
            take_snapshot(reason="baseline")
            soul.write_text("MUTATED\n", encoding="utf-8")

            result = rollback_to_last_known_good(dry_run=True)
            self.assertTrue(result.ok)
            self.assertIn("SOUL.md", result.would_restore)
            self.assertEqual(result.restored, [])
            # File still mutated (dry-run does not touch disk).
            self.assertEqual(soul.read_text(encoding="utf-8"), "MUTATED\n")
        finally:
            soul.write_text(original, encoding="utf-8")

    def test_dream_cycle_sets_lkg_on_first_success(self) -> None:
        """The acceptance test from lessons.md: LKG must be set on first success."""
        import subprocess
        import sys

        handler = self.root / "skills" / "dream-cycle" / "handler.py"
        env = {
            "PATH": "/usr/bin:/bin",
            "HERMES_HOME": str(self.hermes_home),
            "EIDOLON_HOME": str(self.eidolon_home),
        }
        # Run the handler in sessionend mode.
        result = subprocess.run(
            [sys.executable, str(handler), "--mode", "sessionend"],
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        # Handler must not crash even if hindsight/etc. are absent.
        self.assertEqual(
            result.returncode, 0,
            f"dream-cycle crashed: stdout={result.stdout} stderr={result.stderr}",
        )
        # Snapshot must exist.
        from eidolon.safety import list_snapshots
        snaps = list_snapshots()
        self.assertGreaterEqual(len(snaps), 1)


if __name__ == "__main__":
    unittest.main()
