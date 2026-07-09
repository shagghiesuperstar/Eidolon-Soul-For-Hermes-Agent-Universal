# SPDX-License-Identifier: Apache-2.0
"""Unit tests for `eidolon skill` CLI subcommands (promote/demote/retire/status).

All tests are pure: no network, no real filesystem mutations — state dir is
redirected to a tempdir via EIDOLON_HOME env var.
"""
from __future__ import annotations

import json
import os
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch


def _make_manifest(d: Path, name: str = "test-skill", version: str = "1.0.0",
                   min_sessions: int = 0, min_posterior: float = 0.0,
                   min_pass_rate: float = 0.80) -> Path:
    """Write a manifest.yml into d/<name>/manifest.yml and return path."""
    skill_dir = d / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    manifest = skill_dir / "manifest.yml"
    manifest.write_text(
        textwrap.dedent(f"""\
            name: {name}
            version: {version}
            promotion:
              min_shadow_sessions: {min_sessions}
              min_bandit_posterior: {min_posterior}
              regression_suite_pass_rate: {min_pass_rate}
        """),
        encoding="utf-8",
    )
    return manifest


def _make_fixtures(d: Path, name: str, score: float) -> Path:
    """Write a synthetic fixtures/arm.jsonl that gives `name` the target score."""
    fixtures = d / "fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    f = fixtures / "arm.jsonl"
    # Two cases: first hit (weight=1), second miss (weight=1) -> score=0.5
    # Override with single hit (weight=1) -> score=1.0, or miss -> 0.0
    if score >= 1.0:
        lines = [json.dumps({"expected_winner": name, "weight": 1})]
    elif score <= 0.0:
        lines = [json.dumps({"expected_winner": "other", "weight": 1})]
    else:
        # score=0.5: one hit, one miss
        lines = [
            json.dumps({"expected_winner": name, "weight": 1}),
            json.dumps({"expected_winner": "other", "weight": 1}),
        ]
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return fixtures


class TestSkillStatus(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()
        os.environ["EIDOLON_HOME"] = self._tmp

    def tearDown(self):
        os.environ.pop("EIDOLON_HOME", None)
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _run(self, argv):
        from eidolon.cli import main
        return main(argv)

    def test_status_default_shadow(self):
        """Unknown skill reports shadow state; exit 0."""
        rc = self._run(["skill", "status", "nonexistent"])
        self.assertEqual(rc, 0)

    def test_status_json_output(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = self._run(["skill", "status", "my-skill", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["skill"], "my-skill")
        self.assertEqual(data["state"], "shadow")


class TestSkillRetire(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()
        os.environ["EIDOLON_HOME"] = self._tmp

    def tearDown(self):
        os.environ.pop("EIDOLON_HOME", None)
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _run(self, argv):
        from eidolon.cli import main
        return main(argv)

    def test_retire_transitions_to_retired(self):
        rc = self._run(["skill", "retire", "my-skill"])
        self.assertEqual(rc, 0)
        state_path = Path(self._tmp) / "skill-state.json"
        state = json.loads(state_path.read_text())
        self.assertEqual(state["my-skill"], "retired")

    def test_retire_idempotent(self):
        self._run(["skill", "retire", "my-skill"])
        rc = self._run(["skill", "retire", "my-skill"])
        self.assertEqual(rc, 0)

    def test_retire_json_output(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = self._run(["skill", "retire", "my-skill", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["to_state"], "retired")


class TestSkillDemote(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()
        os.environ["EIDOLON_HOME"] = self._tmp

    def tearDown(self):
        os.environ.pop("EIDOLON_HOME", None)
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _run(self, argv):
        from eidolon.cli import main
        return main(argv)

    def _set_state(self, name: str, state: str):
        from eidolon.commands.skill import _state_path
        p = _state_path()
        data = json.loads(p.read_text()) if p.exists() else {}
        data[name] = state
        p.write_text(json.dumps(data) + "\n")

    def test_demote_active_to_shadow(self):
        self._set_state("my-skill", "active")
        rc = self._run(["skill", "demote", "my-skill"])
        self.assertEqual(rc, 0)
        state_path = Path(self._tmp) / "skill-state.json"
        state = json.loads(state_path.read_text())
        self.assertEqual(state["my-skill"], "shadow")

    def test_demote_already_shadow_idempotent(self):
        rc = self._run(["skill", "demote", "my-skill"])
        self.assertEqual(rc, 0)

    def test_demote_retired_blocked(self):
        self._set_state("my-skill", "retired")
        rc = self._run(["skill", "demote", "my-skill"])
        self.assertEqual(rc, 1)


class TestSkillPromote(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()
        os.environ["EIDOLON_HOME"] = self._tmp

    def tearDown(self):
        os.environ.pop("EIDOLON_HOME", None)
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _run(self, argv):
        from eidolon.cli import main
        return main(argv)

    def test_promote_missing_manifest_degraded(self):
        rc = self._run(["skill", "promote", "no-manifest-skill"])
        self.assertEqual(rc, 2)

    def test_promote_missing_fixtures_degraded(self):
        manifest = _make_manifest(Path(self._tmp), name="my-skill")
        rc = self._run([
            "skill", "promote", "my-skill",
            "--manifest", str(manifest),
        ])
        self.assertEqual(rc, 2)

    def test_promote_low_score_blocked(self):
        tmp = Path(self._tmp)
        manifest = _make_manifest(tmp, name="my-skill", min_sessions=0, min_posterior=0.0, min_pass_rate=0.90)
        fixtures = _make_fixtures(tmp, "my-skill", score=0.0)
        rc = self._run([
            "skill", "promote", "my-skill",
            "--manifest", str(manifest),
            "--fixtures", str(fixtures),
        ])
        self.assertEqual(rc, 1)

    def test_promote_passing_score_activates(self):
        tmp = Path(self._tmp)
        manifest = _make_manifest(tmp, name="my-skill", min_sessions=0, min_posterior=0.0, min_pass_rate=0.80)
        fixtures = _make_fixtures(tmp, "my-skill", score=1.0)
        rc = self._run([
            "skill", "promote", "my-skill",
            "--manifest", str(manifest),
            "--fixtures", str(fixtures),
        ])
        self.assertEqual(rc, 0)
        state = json.loads((Path(self._tmp) / "skill-state.json").read_text())
        self.assertEqual(state["my-skill"], "active")

    def test_promote_already_active_idempotent(self):
        from eidolon.commands.skill import _state_path
        p = _state_path()
        p.write_text(json.dumps({"my-skill": "active"}) + "\n")
        tmp = Path(self._tmp)
        manifest = _make_manifest(tmp, name="my-skill")
        rc = self._run([
            "skill", "promote", "my-skill",
            "--manifest", str(manifest),
        ])
        self.assertEqual(rc, 0)

    def test_promote_retired_blocked(self):
        from eidolon.commands.skill import _state_path
        p = _state_path()
        p.write_text(json.dumps({"my-skill": "retired"}) + "\n")
        tmp = Path(self._tmp)
        manifest = _make_manifest(tmp, name="my-skill")
        rc = self._run([
            "skill", "promote", "my-skill",
            "--manifest", str(manifest),
        ])
        self.assertEqual(rc, 1)

    def test_promote_json_output_on_pass(self):
        import io
        from contextlib import redirect_stdout
        tmp = Path(self._tmp)
        manifest = _make_manifest(tmp, name="my-skill", min_sessions=0, min_posterior=0.0, min_pass_rate=0.80)
        fixtures = _make_fixtures(tmp, "my-skill", score=1.0)
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = self._run([
                "skill", "promote", "my-skill",
                "--manifest", str(manifest),
                "--fixtures", str(fixtures),
                "--json",
            ])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["to_state"], "active")
        self.assertEqual(data["skill"], "my-skill")

    def test_promote_unmet_sessions_blocked(self):
        tmp = Path(self._tmp)
        manifest = _make_manifest(tmp, name="my-skill", min_sessions=100, min_posterior=0.0, min_pass_rate=0.80)
        fixtures = _make_fixtures(tmp, "my-skill", score=1.0)
        rc = self._run([
            "skill", "promote", "my-skill",
            "--manifest", str(manifest),
            "--fixtures", str(fixtures),
        ])
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
