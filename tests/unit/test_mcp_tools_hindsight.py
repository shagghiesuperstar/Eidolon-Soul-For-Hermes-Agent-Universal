# SPDX-License-Identifier: Apache-2.0
"""Tests for the eidolon.hindsight.retain MCP tool.

Acceptance gates (fails-before / passes-after contract):

1. dispatch("eidolon.hindsight.retain", ...) no longer raises KeyError
   (the tool is registered).
2. A valid call returns flushed=1, skipped=0, failed=0, status=PASS.
3. Lesson appears in hindsight.jsonl with correct kind + content.
4. Duplicate call returns skipped=1, flushed=0 — idempotent.
5. Missing 'kind'    → error dict, status DEGRADED, no crash.
6. Missing 'content' → error dict, status DEGRADED, no crash.
7. Tool is present in TOOLS manifest (eidolon.hindsight.retain).
"""

from __future__ import annotations

import json
import unittest

from tests.unit._tmphomes import IsolatedHome


class TestHindsightRetainTool(IsolatedHome):

    def _dispatch(self, args):
        from eidolon.mcp.tools import dispatch
        return dispatch("eidolon.hindsight.retain", args)

    def _store_path(self):
        return self.eidolon_home / "memory" / "hindsight.jsonl"

    # ------------------------------------------------------------------
    # Gate 1: tool is registered — dispatch no longer raises KeyError
    # ------------------------------------------------------------------
    def test_tool_registered(self):
        from eidolon.mcp.tools import TOOLS
        self.assertIn("eidolon.hindsight.retain", TOOLS)

    # ------------------------------------------------------------------
    # Gate 2 + 3: valid call → flushed=1, lesson persisted
    # ------------------------------------------------------------------
    def test_valid_call_flushes_lesson(self):
        result = self._dispatch({"kind": "lesson", "content": "trust but verify"})
        self.assertNotIn("error", result, msg=f"unexpected error: {result}")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["flushed"], 1)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["failed"], 0)

        store = self._store_path()
        self.assertTrue(store.exists(), "hindsight.jsonl was not created")
        lines = [json.loads(ln) for ln in store.read_text().splitlines() if ln.strip()]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "lesson")
        self.assertEqual(lines[0]["content"], "trust but verify")

    # ------------------------------------------------------------------
    # Gate 4: duplicate call → skipped=1
    # ------------------------------------------------------------------
    def test_duplicate_skipped(self):
        args = {"kind": "lesson", "content": "trust but verify"}
        self._dispatch(args)  # first write
        result = self._dispatch(args)  # identical entry
        self.assertNotIn("error", result, msg=f"unexpected error: {result}")
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["flushed"], 0)

    # ------------------------------------------------------------------
    # Gate 5: missing kind → DEGRADED, no exception
    # ------------------------------------------------------------------
    def test_missing_kind_degraded(self):
        result = self._dispatch({"content": "some lesson"})
        self.assertIn("error", result)
        self.assertEqual(result["status"], "DEGRADED")
        self.assertEqual(result["error"]["code"], "missing_field")

    # ------------------------------------------------------------------
    # Gate 6: missing content → DEGRADED, no exception
    # ------------------------------------------------------------------
    def test_missing_content_degraded(self):
        result = self._dispatch({"kind": "lesson"})
        self.assertIn("error", result)
        self.assertEqual(result["status"], "DEGRADED")
        self.assertEqual(result["error"]["code"], "missing_field")

    # ------------------------------------------------------------------
    # Gate 7: manifest entry present with required inputSchema fields
    # ------------------------------------------------------------------
    def test_manifest_shape(self):
        from eidolon.mcp.tools import TOOLS
        tool = TOOLS["eidolon.hindsight.retain"]
        manifest = tool.as_manifest()
        self.assertEqual(manifest["name"], "eidolon.hindsight.retain")
        required = manifest["inputSchema"].get("required", [])
        self.assertIn("kind", required)
        self.assertIn("content", required)

    # ------------------------------------------------------------------
    # Bonus: optional 'source' field is stored when provided
    # ------------------------------------------------------------------
    def test_source_field_stored(self):
        self._dispatch({"kind": "observation", "content": "model latency spiked", "source": "dream-cycle"})
        store = self._store_path()
        lines = [json.loads(ln) for ln in store.read_text().splitlines() if ln.strip()]
        self.assertEqual(lines[0]["source"], "dream-cycle")


if __name__ == "__main__":
    unittest.main()
