# SPDX-License-Identifier: Apache-2.0
"""REC-003: `eidolon report` produces integers and a stable schema."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout

from tests.unit._tmphomes import IsolatedHome


REQUIRED_FIELDS = {
    "schema",
    "sessions_observed",
    "lessons_added",
    "proposals_generated",
    "proposals_applied",
    "rollback_count",
    "inference_requests",
    "inference_degraded",
    "empty_state",
    "delta",
    "has_baseline",
    "last_doctor_status",
}


class ReportTests(IsolatedHome):
    def _run(self, argv):
        from eidolon.cli import main

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(argv)
        return code, buf.getvalue()

    def test_empty_state_is_valid_all_zeros(self) -> None:
        code, out = self._run(["report", "--json"])
        data = json.loads(out.strip().splitlines()[-1])
        self.assertEqual(code, 0)
        self.assertTrue(REQUIRED_FIELDS.issubset(data.keys()))
        for k in (
            "sessions_observed",
            "lessons_added",
            "proposals_generated",
            "proposals_applied",
            "rollback_count",
            "inference_requests",
            "inference_degraded",
        ):
            self.assertEqual(data[k], 0)
            self.assertIsInstance(data[k], int)
        self.assertTrue(data["empty_state"])
        self.assertEqual(data["schema"], 1)

    def test_events_are_counted_into_report(self) -> None:
        from eidolon.util import events

        for _ in range(3):
            events.emit("dream.session", events.STATUS_INFO, source="test", mode="sessionend")
        events.emit("dream.lesson", events.STATUS_INFO, source="test", n=1)
        events.emit("dream.propose", events.STATUS_INFO, source="test", n=1)
        # dream.apply is observed (non-empty window) but is NOT DONE: it must
        # not drive top-level proposals_applied (Law-of-Done judgment metric).
        events.emit("dream.apply", events.STATUS_INFO, source="test", id="c1")
        events.emit("dream.rollback", events.STATUS_INFO, source="test", snapshot_id="x")
        events.emit("inference.request", events.STATUS_PASS, source="test")
        events.emit("inference.degraded", events.STATUS_DEGRADED, source="test")

        code, out = self._run(["report", "--json"])
        data = json.loads(out.strip().splitlines()[-1])

        self.assertEqual(code, 0)
        self.assertFalse(data["empty_state"])
        self.assertEqual(data["sessions_observed"], 3)
        self.assertEqual(data["lessons_added"], 1)
        self.assertEqual(data["proposals_generated"], 1)
        self.assertEqual(
            data["proposals_applied"],
            0,
            "dream.apply events alone must not set proposals_applied",
        )
        self.assertEqual(data["rollback_count"], 1)
        self.assertEqual(data["inference_requests"], 1)
        self.assertEqual(data["inference_degraded"], 1)

    def test_schema_field_is_stable(self) -> None:
        code, out = self._run(["report", "--json"])
        data = json.loads(out.strip().splitlines()[-1])
        # Regression fence: if the schema changes, this must fail loudly.
        self.assertEqual(data["schema"], 1)

    def test_window_parsing_rejects_bad_input(self) -> None:
        from eidolon.reporting.metrics import parse_window

        for good in ("1h", "24h", "7d", "30m"):
            self.assertGreater(parse_window(good), 0)
        for bad in ("", "24", "24x", "-1h", "0d", "abc"):
            with self.assertRaises(ValueError):
                parse_window(bad)


if __name__ == "__main__":
    unittest.main()
