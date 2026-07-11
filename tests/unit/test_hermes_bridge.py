# SPDX-License-Identifier: Apache-2.0
import tempfile
import unittest
from pathlib import Path

from eidolon.hermes_bridge import promote_lesson_to_hermes, SECTION_HEADER


class HermesBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        (self.home / "memories").mkdir()
        (self.home / "memories" / "MEMORY.md").write_text(
            "STYLE: be direct.\n§\nOther stuff.\n§\n", encoding="utf-8"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_writes_section_hermes_reads(self):
        r = promote_lesson_to_hermes(
            "Always probe ports before claiming architecture",
            hermes_home=self.home,
            source_id="t1",
        )
        self.assertEqual(r["status"], "ok")
        body = (self.home / "memories" / "MEMORY.md").read_text(encoding="utf-8")
        self.assertIn(SECTION_HEADER, body)
        self.assertIn("probe ports", body)
        self.assertIn("STYLE: be direct", body)  # preserved

    def test_skips_worthless_template(self):
        r = promote_lesson_to_hermes(
            "Improve handling of 'lesson' events based on 9 observations.",
            hermes_home=self.home,
        )
        self.assertEqual(r["status"], "skipped")
        body = (self.home / "memories" / "MEMORY.md").read_text(encoding="utf-8")
        self.assertNotIn("Improve handling", body)

    def test_dedup(self):
        promote_lesson_to_hermes("Never invent command output", hermes_home=self.home)
        r = promote_lesson_to_hermes("Never invent command output", hermes_home=self.home)
        self.assertEqual(r["status"], "skipped")
        self.assertEqual(r["reason"], "duplicate")


if __name__ == "__main__":
    unittest.main()
