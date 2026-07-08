# SPDX-License-Identifier: Apache-2.0
"""Eidolon MCP surface.

Speaks a minimal, MCP-compatible JSON-RPC 2.0 wire protocol over HTTP.
Stdlib-only; no external MCP client library is a runtime dependency.

The server binds to 127.0.0.1 only (see `server.serve`). Ports are chosen
by the operator via `eidolon mcp serve --port <N>`.

Exposes exactly three tools (v1):
- eidolon.report      -> report.build JSON
- eidolon.doctor      -> doctor result set + overall
- eidolon.learn.step  -> deterministic bandit episode driver
"""

from eidolon.mcp.tools import TOOLS, dispatch  # re-exported for tests

__all__ = ["TOOLS", "dispatch"]
