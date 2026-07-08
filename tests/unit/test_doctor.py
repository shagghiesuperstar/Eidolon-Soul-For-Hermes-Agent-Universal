"""REC-002: `eidolon doctor` with JSON output + DEGRADED state."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout

from tests.unit._tmphomes import IsolatedHome


class DoctorTests(IsolatedHome):
    def _run(self, argv):
        from eidolon.cli import main

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(argv)
        return code, buf.getvalue()

    def test_json_output_is_valid_and_has_overall(self) -> None:
        code, out = self._run(["doctor", "--json"])
        data = json.loads(out.strip().splitlines()[-1])
        self.assertIn("overall", data)
        self.assertIn("checks", data)
        self.assertIn(data["overall"], {"PASS", "DEGRADED", "FAIL"})
        for check in data["checks"]:
            self.assertIn("name", check)
            self.assertIn("status", check)
            self.assertIn("reason", check)
            self.assertIn(check["status"], {"PASS", "DEGRADED", "FAIL"})

    def test_missing_hermes_home_returns_degraded_not_fail(self) -> None:
        # We deliberately do NOT create a Hermes config; expected DEGRADED.
        code, _ = self._run(["doctor", "--json"])
        self.assertEqual(code, 2, "missing Hermes home must be DEGRADED (exit 2), not FAIL (1)")

    def test_wired_hooks_and_provider_yields_pass(self) -> None:
        self.write_hermes_config(
            "session_end_hook: dream-cycle\ncron:\n  - integrity-watchdog\n"
        )
        self.write_hermes_cache({
            "any-provider": {
                "tier": "A",
                "capabilities": ["json_mode"],
                "context_window": 32000,
            }
        })
        code, out = self._run(["doctor", "--json", "--model-check"])
        data = json.loads(out.strip().splitlines()[-1])
        self.assertEqual(code, 0, f"expected PASS overall, got: {data}")
        self.assertEqual(data["overall"], "PASS")

    def test_unplugged_provider_reports_degraded_never_silent(self) -> None:
        # Wired hooks, but no providers in the cache -> DEGRADED, not silent PASS.
        self.write_hermes_config(
            "session_end_hook: dream-cycle\ncron:\n  - integrity-watchdog\n"
        )
        self.write_hermes_cache({})  # empty cache = no providers
        code, out = self._run(["doctor", "--json", "--model-check"])
        data = json.loads(out.strip().splitlines()[-1])
        self.assertEqual(code, 2)
        provider_check = next(
            c for c in data["checks"] if c["name"] == "provider_capability"
        )
        self.assertEqual(provider_check["status"], "DEGRADED")
        self.assertIn("heuristic", provider_check["reason"].lower())


if __name__ == "__main__":
    unittest.main()
