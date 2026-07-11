# SPDX-License-Identifier: Apache-2.0
"""Vertical-slice tests (v2.0 D1–D4).

D1: SKILL_UPDATE must write a real Markdown playbook under
HERMES_HOME/skills/_eidolon_staging/ (never live skills/).

D2: MemoryAdapter.mark_done() mutates lesson done-state on InMemAdapter and
persists it on HindsightAdapter (filesystem JSONL backend; no network).

D3: apply_low() Law of Done — only after a real SKILL_UPDATE staging write
succeeds, mark the lesson done via MemoryAdapter, then
metrics.increment("proposals_applied"). Ledger-only / skip / failed mark_done
must not increment.

D4: ``eidolon report --json`` emits scoreboard integers lessons_extracted,
proposals_applied, skills_staged, inbox_cleared from real state (not ledger
fakes): judgment metrics, staging Markdown files, persisted lessons.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = str(ROOT / "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from eidolon.judgment.classifier import ActionKind
from eidolon.judgment.executor import execute_judgment
from tests.unit._tmphomes import IsolatedHome

_HANDLER_PATH = ROOT / "skills" / "dream-cycle" / "handler.py"
_handler_spec = importlib.util.spec_from_file_location(
    "dream_handler_vertical_slice", _HANDLER_PATH
)
_handler = importlib.util.module_from_spec(_handler_spec)
assert _handler_spec.loader is not None
_handler_spec.loader.exec_module(_handler)


class TestD1SkillUpdateStaging(unittest.TestCase):
    """D1: SKILL_UPDATE writes a Markdown playbook under _eidolon_staging only."""

    def test_skill_update_writes_staging_playbook(self):
        hh = Path(tempfile.mkdtemp())
        lesson = "Probe port before assuming the service is running"

        result = execute_judgment(
            ActionKind.SKILL_UPDATE,
            lesson,
            hermes_home=hh,
        )

        self.assertEqual(result["status"], "ok")

        staging_dir = hh / "skills" / "_eidolon_staging"
        self.assertTrue(
            staging_dir.is_dir(),
            "expected HERMES_HOME/skills/_eidolon_staging/ to exist",
        )

        playbooks = sorted(staging_dir.glob("*.md"))
        self.assertTrue(
            playbooks,
            "expected at least one Markdown playbook under _eidolon_staging/",
        )

        content = playbooks[0].read_text(encoding="utf-8")
        self.assertIn(lesson, content)
        self.assertGreater(len(content.strip()), 0)

        # Hard constraint: never write live skills outside _eidolon_staging
        live_skill = hh / "skills" / "eidolon-learned.md"
        self.assertFalse(
            live_skill.exists(),
            "SKILL_UPDATE must not write live skills/eidolon-learned.md",
        )
        for p in (hh / "skills").iterdir():
            if p.name == "_eidolon_staging":
                continue
            if p.is_file() and p.suffix == ".md":
                self.fail(f"unexpected live skill write outside staging: {p}")


class TestD2MarkDone(IsolatedHome):
    """D2: mark_done leaves the soft inbox by flipping lesson done-state."""

    def test_inmem_mark_done_mutates_lesson_done_state(self):
        from eidolon.memory.inmem import InMemAdapter

        adapter = InMemAdapter()
        lesson = "Always probe the service before claiming it is up"
        adapter.store({"kind": "lesson", "content": lesson})

        before = adapter.retrieve(kind="lesson")
        self.assertEqual(len(before), 1)
        self.assertFalse(before[0].get("done", False))

        self.assertTrue(hasattr(adapter, "mark_done"), "MemoryAdapter must expose mark_done")
        ok = adapter.mark_done(lesson)
        self.assertTrue(ok, "mark_done must return True when a matching lesson exists")

        after = adapter.retrieve(kind="lesson")
        self.assertEqual(len(after), 1)
        self.assertTrue(
            after[0].get("done") is True,
            "InMemAdapter.mark_done must set done=True on the stored lesson",
        )
        # Same object identity in the volatile store — not a no-op copy.
        self.assertIs(after[0], before[0])
        self.assertTrue(before[0].get("done") is True)

    def test_inmem_mark_done_missing_returns_false(self):
        from eidolon.memory.inmem import InMemAdapter

        adapter = InMemAdapter()
        adapter.store({"kind": "lesson", "content": "known lesson"})
        self.assertFalse(adapter.mark_done("lesson that was never stored"))
        remaining = adapter.retrieve(kind="lesson")
        self.assertEqual(len(remaining), 1)
        self.assertFalse(remaining[0].get("done", False))

    def test_hindsight_mark_done_persists_across_instances(self):
        """Hindsight uses the real filesystem JSONL contract (no network)."""
        from eidolon.memory.hindsight import HindsightAdapter
        from eidolon.util.paths import eidolon_state_dir

        lesson = "Prefer real command output over invented evidence"
        a1 = HindsightAdapter()
        a1.store({"kind": "lesson", "content": lesson})

        self.assertTrue(hasattr(a1, "mark_done"), "HindsightAdapter must expose mark_done")
        ok = a1.mark_done(lesson)
        self.assertTrue(ok)

        # Fresh instance must read done=True from disk under EIDOLON_HOME.
        a2 = HindsightAdapter()
        hits = a2.retrieve(kind="lesson")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["content"], lesson)
        self.assertTrue(
            hits[0].get("done") is True,
            "HindsightAdapter.mark_done must rewrite hindsight.jsonl with done=True",
        )

        store = eidolon_state_dir() / "memory" / "hindsight.jsonl"
        self.assertTrue(store.is_file(), "hindsight backend must persist under state dir")
        raw = store.read_text(encoding="utf-8")
        self.assertIn('"done":true', raw.replace(" ", ""))
        # Isolation: store lives under the test EIDOLON_HOME (resolve for macOS /var).
        self.assertTrue(
            store.resolve().is_relative_to(self.eidolon_home.resolve()),
            "hindsight.jsonl must stay under the isolated EIDOLON_HOME",
        )


class TestD3ApplyLowProposalsApplied(IsolatedHome):
    """D3: real apply_low path increments proposals_applied only on Law of Done."""

    def setUp(self) -> None:
        super().setUp()
        # Judgment metrics honor EIDOLON_STATE_DIR (IsolatedHome sets EIDOLON_HOME).
        self._saved_state_dir = os.environ.get("EIDOLON_STATE_DIR")
        os.environ["EIDOLON_STATE_DIR"] = str(self.eidolon_home)
        # Hindsight backend under isolated homes (real filesystem, no mocks).
        self.write_hermes_config("memory.backend: hindsight\n")
        (self.hermes_home / "memories").mkdir(parents=True, exist_ok=True)
        (self.hermes_home / "memories" / "MEMORY.md").write_text(
            "STYLE: be direct.\n", encoding="utf-8"
        )
        _handler._ADAPTER = None

    def tearDown(self) -> None:
        _handler._ADAPTER = None
        if self._saved_state_dir is None:
            os.environ.pop("EIDOLON_STATE_DIR", None)
        else:
            os.environ["EIDOLON_STATE_DIR"] = self._saved_state_dir
        super().tearDown()

    def test_apply_low_law_of_done_increments_proposals_applied(self):
        """Genuine apply_low: staging write + mark_done → proposals_applied.

        Also proves ledger-only success and missing mark_done do not increment.
        """
        from eidolon.judgment.metrics import load as load_metrics
        from eidolon.memory.hindsight import HindsightAdapter

        lesson = "Probe the service before claiming the port is open"
        # Soft inbox: lesson must already exist for mark_done to succeed.
        adapter = HindsightAdapter()
        adapter.store({"kind": "lesson", "content": lesson})
        _handler._ADAPTER = adapter

        before = load_metrics(self.eidolon_home)
        self.assertEqual(before.get("proposals_applied", 0), 0)

        # --- Negative: template / empty lesson → ledger may write, no increment ---
        _handler.apply_low(
            {
                "id": "neg-template",
                "content": "Improve handling of 'lesson' events based on 9 observations.",
                "lesson_content": "Improve handling of 'lesson' events based on 9 observations.",
                "mutation_kind": "preference_update",
            }
        )
        after_template = load_metrics(self.eidolon_home)
        self.assertEqual(
            after_template.get("proposals_applied", 0),
            0,
            "template/skipped bridge must not increment proposals_applied",
        )
        ledger = self.eidolon_home / "applied_proposals.jsonl"
        self.assertTrue(
            ledger.is_file(),
            "ledger may still record the apply attempt (ledger-only is NOT DONE)",
        )

        # --- Negative: real skill path but lesson not in adapter → no increment ---
        orphan = "Run the real command and paste evidence from the terminal"
        _handler._ADAPTER = HindsightAdapter()  # empty store — mark_done misses
        _handler.apply_low(
            {
                "id": "neg-orphan",
                "content": orphan,
                "lesson_content": orphan,
                "mutation_kind": "preference_update",
            }
        )
        staging_after_orphan = (
            self.hermes_home / "skills" / "_eidolon_staging" / "eidolon-learned.md"
        )
        # Orphan may still stage (filesystem ok) but without mark_done → no counter.
        after_orphan = load_metrics(self.eidolon_home)
        self.assertEqual(
            after_orphan.get("proposals_applied", 0),
            0,
            "failed mark_done (lesson absent) must not increment proposals_applied",
        )

        # --- Positive: staging write + mark_done → proposals_applied == 1 ---
        adapter2 = HindsightAdapter()
        # Re-store lesson if orphan path polluted MEMORY; use distinct skill lesson.
        skill_lesson = "Probe port before assuming the service is running"
        adapter2.store({"kind": "lesson", "content": skill_lesson})
        _handler._ADAPTER = adapter2

        _handler.apply_low(
            {
                "id": "pos-skill",
                "content": skill_lesson,
                "lesson_content": skill_lesson,
                "mutation_kind": "preference_update",
            }
        )

        staging = (
            self.hermes_home / "skills" / "_eidolon_staging" / "eidolon-learned.md"
        )
        self.assertTrue(
            staging.is_file(),
            "Law of Done requires a real SKILL_UPDATE staging Markdown write",
        )
        staged_body = staging.read_text(encoding="utf-8")
        self.assertIn(skill_lesson, staged_body)

        # Live skills/ must stay untouched (only _eidolon_staging).
        live = self.hermes_home / "skills" / "eidolon-learned.md"
        self.assertFalse(live.exists(), "must not write live skills outside staging")

        hits = [
            e
            for e in adapter2.retrieve(kind="lesson")
            if e.get("content") == skill_lesson
        ]
        self.assertEqual(len(hits), 1)
        self.assertTrue(
            hits[0].get("done") is True,
            "apply_low must mark_done via MemoryAdapter after staging write",
        )

        after = load_metrics(self.eidolon_home)
        self.assertEqual(
            after.get("proposals_applied"),
            1,
            "proposals_applied must increment exactly once after full Law of Done",
        )


class TestD4ReportScoreboard(IsolatedHome):
    """D4: report --json scoreboard X/Y/Z/W from real state (not ledger fakes)."""

    SCOREBOARD_KEYS = (
        "lessons_extracted",
        "proposals_applied",
        "skills_staged",
        "inbox_cleared",
    )

    def setUp(self) -> None:
        super().setUp()
        # Judgment metrics honor EIDOLON_STATE_DIR (same isolation as D3).
        self._saved_state_dir = os.environ.get("EIDOLON_STATE_DIR")
        os.environ["EIDOLON_STATE_DIR"] = str(self.eidolon_home)

    def tearDown(self) -> None:
        if self._saved_state_dir is None:
            os.environ.pop("EIDOLON_STATE_DIR", None)
        else:
            os.environ["EIDOLON_STATE_DIR"] = self._saved_state_dir
        super().tearDown()

    def _run_report_json(self):
        import io
        import json
        from contextlib import redirect_stdout

        from eidolon.cli import main

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["report", "--json"])
        raw = buf.getvalue().strip().splitlines()[-1]
        return code, json.loads(raw)

    def test_report_json_scoreboard_fields_from_real_state(self):
        """Genuine RED→GREEN: four int fields wired to real judgment/staging/memory."""
        from eidolon.judgment.metrics import increment, load as load_metrics
        from eidolon.memory.hindsight import HindsightAdapter

        # --- Empty baseline: all four keys present as int zero ---
        code0, empty = self._run_report_json()
        self.assertEqual(code0, 0)
        for key in self.SCOREBOARD_KEYS:
            self.assertIn(key, empty, f"report --json must emit top-level {key!r}")
            self.assertIsInstance(
                empty[key],
                int,
                f"{key} must be int (got {type(empty[key]).__name__})",
            )
            self.assertEqual(empty[key], 0, f"{key} must be 0 with no real state")

        # --- Seed real state (not ledger / not hardcoded report values) ---
        adapter = HindsightAdapter()
        lesson_a = "Probe the service before claiming the port is open"
        lesson_b = "Prefer real command output over invented evidence"
        lesson_c = "Never touch SOUL.md from automated applies"
        adapter.store({"kind": "lesson", "content": lesson_a})
        adapter.store({"kind": "lesson", "content": lesson_b})
        adapter.store({"kind": "lesson", "content": lesson_c})
        self.assertTrue(adapter.mark_done(lesson_a))
        self.assertTrue(adapter.mark_done(lesson_b))
        # lesson_c remains open in the soft inbox

        # Judgment metrics: Law-of-Done counter (not applied_proposals.jsonl).
        increment("proposals_applied", eidolon_home=self.eidolon_home)
        increment("proposals_applied", eidolon_home=self.eidolon_home)
        self.assertEqual(load_metrics(self.eidolon_home).get("proposals_applied"), 2)

        # Real staging Markdown files under HERMES_HOME/skills/_eidolon_staging.
        staging = self.hermes_home / "skills" / "_eidolon_staging"
        staging.mkdir(parents=True, exist_ok=True)
        (staging / "playbook-a.md").write_text(
            f"# staged\n\n{lesson_a}\n", encoding="utf-8"
        )
        (staging / "playbook-b.md").write_text(
            f"# staged\n\n{lesson_b}\n", encoding="utf-8"
        )
        (staging / "not-a-skill.txt").write_text("ignore me\n", encoding="utf-8")
        # Non-md must not count; only *.md under _eidolon_staging.
        self.assertEqual(len(list(staging.glob("*.md"))), 2)

        # Ledger noise must not drive the scoreboard.
        ledger = self.eidolon_home / "applied_proposals.jsonl"
        ledger.write_text(
            '{"id":"ledger-noise","content":"must not inflate scoreboard"}\n',
            encoding="utf-8",
        )

        # dream.apply event noise must not floor/inflate proposals_applied.
        # Ledger/event apply attempts are NOT DONE; judgment metrics stay at 2.
        from eidolon.util import events

        for i in range(200):
            events.emit(
                "dream.apply",
                events.STATUS_INFO,
                source="test",
                id=f"event-noise-{i}",
            )

        code, data = self._run_report_json()
        self.assertEqual(code, 0)

        for key in self.SCOREBOARD_KEYS:
            self.assertIn(key, data)
            self.assertIsInstance(
                data[key],
                int,
                f"{key} must be JSON integer type, not {type(data[key]).__name__}",
            )
            # JSON numbers that are whole values must stay true ints (not bool).
            self.assertFalse(
                isinstance(data[key], bool),
                f"{key} must not be bool",
            )

        self.assertEqual(
            data["lessons_extracted"],
            3,
            "lessons_extracted must count persisted lesson entries",
        )
        self.assertEqual(
            data["proposals_applied"],
            2,
            "proposals_applied must be EXACTLY judgment metrics (not dream.apply event floor)",
        )
        self.assertEqual(
            data["skills_staged"],
            2,
            "skills_staged must count real *.md under _eidolon_staging",
        )
        self.assertEqual(
            data["inbox_cleared"],
            2,
            "inbox_cleared must count persisted lessons with done=True",
        )


if __name__ == "__main__":
    unittest.main()
