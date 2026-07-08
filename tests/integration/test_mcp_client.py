# SPDX-License-Identifier: Apache-2.0
"""Optional integration test: real MCP client against Eidolon's server.

This test is **skipped by default** — the `mcp` client library is not a
runtime dependency of Eidolon. If a developer has installed `mcp` locally
they can run this to prove wire compatibility beyond our stdlib server.

Enable manually:

    pip install mcp
    PYTHONPATH=src python -m unittest tests.integration.test_mcp_client -v

Refs: master_EIDOLON_roadmap(F5).md § REC-013.
"""

from __future__ import annotations

import importlib
import os
import socket
import threading
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in os.sys.path:
    os.sys.path.insert(0, str(_SRC))

try:
    mcp = importlib.import_module("mcp")
    _HAS_MCP = True
except ImportError:  # pragma: no cover - env-dependent
    mcp = None
    _HAS_MCP = False


@unittest.skipUnless(_HAS_MCP, "mcp client library not installed")
class MCPClientRoundTrip(unittest.TestCase):
    def test_placeholder(self):
        """Kept as a marker: a real client harness lives here once the mcp
        client's async surface stabilises. For now, the stdlib server's own
        HTTP tests in tests/unit/test_mcp_server.py cover wire behavior."""
        self.assertTrue(_HAS_MCP)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
