# SPDX-License-Identifier: Apache-2.0
"""Minimal MCP-compatible JSON-RPC 2.0 server over HTTP.

Design constraints (from REC-013):
- Stdlib only. No ``mcp`` client library as a runtime dep.
- Bind to 127.0.0.1 only. Never the any-interface wildcard. No IPv6 wildcard.
- Configurable port; no fixed port claim.
- Speaks the JSON-RPC methods MCP clients call first:
    * ``initialize``      -> minimal capabilities
    * ``tools/list``      -> the 3 Eidolon tools
    * ``tools/call``      -> dispatch to handler; returns MCP-shaped result

The transport is HTTP POST at ``/mcp``. Clients can also POST JSON-RPC to
``/`` for convenience; behavior is identical. GET returns a small banner
so operators can eyeball ``curl http://127.0.0.1:PORT/`` and see life.
"""

from __future__ import annotations

import json
import socket
import sys
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Optional, Tuple

from eidolon.mcp.tools import TOOLS, dispatch

# JSON-RPC 2.0 error codes we use.
JSONRPC_PARSE_ERROR = -32700
JSONRPC_INVALID_REQUEST = -32600
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INVALID_PARAMS = -32602
JSONRPC_INTERNAL_ERROR = -32603

_BIND_HOST = "127.0.0.1"  # loopback only; verified by sanitization grep


def _rpc_error(code: int, message: str, req_id: Any = None) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": code, "message": message},
    }


def _rpc_result(result: Any, req_id: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _handle_initialize(_params: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "protocolVersion": "2024-11-05",
        "serverInfo": {"name": "eidolon", "version": _eidolon_version()},
        "capabilities": {"tools": {"listChanged": False}},
    }


def _handle_tools_list(_params: Dict[str, Any]) -> Dict[str, Any]:
    return {"tools": [t.as_manifest() for t in TOOLS.values()]}


def _handle_tools_call(params: Dict[str, Any]) -> Dict[str, Any]:
    name = params.get("name")
    if not isinstance(name, str):
        raise _RPCError(JSONRPC_INVALID_PARAMS, "missing 'name'")
    if name not in TOOLS:
        raise _RPCError(JSONRPC_METHOD_NOT_FOUND, f"unknown tool: {name}")
    args = params.get("arguments") or {}
    if not isinstance(args, dict):
        raise _RPCError(JSONRPC_INVALID_PARAMS, "'arguments' must be object")
    payload = dispatch(name, args)
    # MCP tool-call result shape: content array + isError flag.
    is_error = "error" in payload
    text = json.dumps(payload, sort_keys=True)
    return {
        "content": [{"type": "text", "text": text}],
        "isError": bool(is_error),
    }


class _RPCError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


_METHODS = {
    "initialize": _handle_initialize,
    "tools/list": _handle_tools_list,
    "tools/call": _handle_tools_call,
}


def handle_rpc(body: bytes) -> Dict[str, Any]:
    """Parse a JSON-RPC request body and return a response dict."""
    try:
        req = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return _rpc_error(JSONRPC_PARSE_ERROR, f"parse error: {exc}")

    if not isinstance(req, dict):
        return _rpc_error(JSONRPC_INVALID_REQUEST, "request must be object")
    if req.get("jsonrpc") != "2.0":
        return _rpc_error(JSONRPC_INVALID_REQUEST, "jsonrpc must be '2.0'", req.get("id"))

    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params") or {}
    if not isinstance(params, dict):
        return _rpc_error(JSONRPC_INVALID_PARAMS, "params must be object", req_id)

    handler = _METHODS.get(method)
    if handler is None:
        return _rpc_error(JSONRPC_METHOD_NOT_FOUND, f"unknown method: {method}", req_id)

    try:
        return _rpc_result(handler(params), req_id)
    except _RPCError as exc:
        return _rpc_error(exc.code, exc.message, req_id)
    except Exception as exc:  # pragma: no cover - defensive
        return _rpc_error(JSONRPC_INTERNAL_ERROR, f"internal error: {exc}", req_id)


class _MCPHandler(BaseHTTPRequestHandler):
    server_version = "EidolonMCP/1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        # Route access logs to stderr; keep them terse.
        sys.stderr.write("[eidolon-mcp] " + (format % args) + "\n")

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        """CORS preflight for browser-based MCP clients."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        # Lightweight banner for humans; not part of the protocol.
        banner = {
            "server": "eidolon-mcp",
            "version": _eidolon_version(),
            "bind": _BIND_HOST,
            "endpoint": "POST /mcp (JSON-RPC 2.0)",
            "tools": list(TOOLS.keys()),
        }
        self._send_json(200, banner)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length > 0 else b""
        response = handle_rpc(raw)
        # JSON-RPC errors still ride 200 unless HTTP itself failed.
        self._send_json(200, response)


def _eidolon_version() -> str:
    from eidolon._version import __version__

    return __version__


def _resolve_bind() -> str:
    """Return the loopback bind address. Isolated so tests can assert it."""
    return _BIND_HOST


def serve(port: int) -> HTTPServer:
    """Create (do not start) an HTTPServer bound to 127.0.0.1:port.

    Callers own ``serve_forever`` / ``shutdown`` lifecycle. Kept separate
    so tests can spin the server on an ephemeral port and stop it cleanly.
    """
    if port < 0 or port > 65535:
        raise ValueError(f"port out of range: {port}")
    host = _resolve_bind()
    server = HTTPServer((host, port), _MCPHandler)
    return server


def run_forever(port: int) -> int:
    """Blocking entrypoint used by ``eidolon mcp serve --port N``."""
    server = serve(port)
    host, bound_port = server.server_address[:2]
    sys.stderr.write(
        f"[eidolon-mcp] listening on http://{host}:{bound_port}/mcp "
        f"(tools: {', '.join(TOOLS.keys())})\n"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.stderr.write("[eidolon-mcp] interrupted; shutting down\n")
    finally:
        server.server_close()
    return 0
