"""REC-022: proposals_applied must be >0 only after a real TIER-1 mutation."""
import importlib
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


class TestREC022OutputGate(unittest.TestCase):
    def _run_canary(self, tmp):
        """Run a minimal dream cycle with a canary lesson and return metrics."""
        import eidolon.judgment.metrics as m

        state_dir = tmp / "state"
        state_dir.mkdir()
        os.environ["EIDOLON_STATE_DIR"] = str(state_dir)
        os.environ["EIDOLON_HOME"] = str(state_dir)
        hermes_home = tmp / "hermes"
        (hermes_home / "memories").mkdir(parents=True)
        (hermes_home / "memories" / "MEMORY.md").write_text("")
        os.environ["HERMES_HOME"] = str(hermes_home)

        # Import handler fresh (env vars must be set before import)
        import skills  # noqa: F401

        spec = importlib.util.spec_from_file_location(
            "dream_handler", ROOT / "skills" / "dream-cycle" / "handler.py"
        )
        handler = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(handler)

        # Canary episode
        episode = {
            "kind": "lesson",
            "content": "canary: test skill update",
            "ts": 1000.0,
        }
        patterns = handler.reflect([episode])
        lessons = handler.extract_lessons(patterns)
        candidates = handler.propose(lessons)

        # Exercise the output gate, not only proposal generation.
        handler.gate_and_apply(candidates, {})

        # Verify at least one candidate is skill_update
        skill_update_candidates = [
            c for c in candidates if c.get("mutation_kind") == "skill_update"
        ]
        return skill_update_candidates, candidates, m.load(Path(state_dir))

    def test_propose_emits_skill_update_for_lesson_kind(self):
        """propose() must emit mutation_kind=skill_update for lesson-kind patterns."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            skill_update_candidates, all_candidates, _ = self._run_canary(tmp)
        self.assertTrue(
            len(skill_update_candidates) > 0,
            "No skill_update candidate produced. Got: "
            f"{[c.get('mutation_kind') for c in all_candidates]}",
        )

    def test_proposals_applied_increments_only_after_mutation(self):
        """proposals_applied must be >0 only if a TIER-1 staging write succeeds."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            _, _, metrics = self._run_canary(tmp)
        self.assertGreater(
            metrics.get("proposals_applied", 0),
            0,
            "proposals_applied=0 after canary; TIER-1 mutation gate not reached",
        )
        self.assertGreater(
            metrics.get("skills_modified", 0),
            0,
            "skills_modified=0 after canary; SKILL_UPDATE judgment did not execute",
        )

    def test_ledger_only_does_not_increment(self):
        """A ledger-only success (bridge status != ok) must not increment proposals_applied."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            state_dir = tmp / "state"
            state_dir.mkdir()
            os.environ["EIDOLON_STATE_DIR"] = str(state_dir)
            import eidolon.judgment.metrics as m

            # Simulate bridge returning status=skipped (not ok)
            spec = importlib.util.spec_from_file_location(
                "dream_handler2", ROOT / "skills" / "dream-cycle" / "handler.py"
            )
            handler = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(handler)
            handler._law_of_done_after_skill_update(
                "test lesson",
                "skipped",  # bridge_status != ok
                {"judgment_kind": "skill_update", "judgment_status": "ok"},
            )
            metrics = m.load(Path(state_dir))
        self.assertEqual(
            metrics.get("proposals_applied", 0),
            0,
            "proposals_applied incremented on bridge skip — gate violation",
        )
