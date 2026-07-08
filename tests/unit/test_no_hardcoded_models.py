# SPDX-License-Identifier: Apache-2.0
"""REC-005 CI enforcement: no hardcoded model / provider identities in src/.

This is the load-bearing test that keeps the router provider-agnostic. If a
future PR introduces `"gpt-4o"` or `"claude-sonnet"` as a string literal
inside src/eidolon/, this test must fail and block the merge.

Exemptions are declared explicitly at the bottom of this file and require
justification in the PR description.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


# Patterns we consider "hardcoded model identity". Match on string literals.
FORBIDDEN_PATTERNS = [
    re.compile(r"\"gpt-[0-9]"),
    re.compile(r"\"gpt-4o"),
    re.compile(r"\"claude-(?:opus|sonnet|haiku|3|4|5)"),
    re.compile(r"\"llama-[0-9]"),
    re.compile(r"\"llama3"),
    re.compile(r"\"mistral-"),
    re.compile(r"\"qwen"),
    re.compile(r"\"gemini-"),
    re.compile(r"\"o1-"),
    re.compile(r"\"o3-"),
    re.compile(r"api\.openai\.com"),
    re.compile(r"api\.anthropic\.com"),
    re.compile(r"generativelanguage\.googleapis"),
]

# Allow test fixtures / provider-key names that legitimately reference vendors.
# Everything under src/eidolon/ must stay clean.
SCAN_ROOTS = ("src/eidolon",)


class NoHardcodedModelsTests(unittest.TestCase):
    def test_no_forbidden_pattern_in_src(self) -> None:
        repo = Path(__file__).resolve().parents[2]
        offenders: list[tuple[str, int, str]] = []
        for root in SCAN_ROOTS:
            for py in (repo / root).rglob("*.py"):
                for lineno, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
                    for pat in FORBIDDEN_PATTERNS:
                        if pat.search(line):
                            offenders.append((str(py.relative_to(repo)), lineno, line.strip()))
        self.assertEqual(
            offenders, [],
            "REC-005 violation: hardcoded model or provider identity found in src/:\n"
            + "\n".join(f"  {f}:{n}: {l}" for f, n, l in offenders),
        )


if __name__ == "__main__":
    unittest.main()
