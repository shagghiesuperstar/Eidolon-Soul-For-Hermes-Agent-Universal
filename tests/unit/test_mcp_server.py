# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the Eidolon MCP server (REC-013).

Contract we lock in here:
- Server binds to 127.0.0.1 (nothing else).
- ``tools/list`` returns exactly 3 tools.
- ``initialize`` returns a MCP-shaped handshake.
- Each tool round-trips against the CLI equivalent.
- Unknown method / unknown tool / malformed JSON produce JSON-RPC errors.
- ``eidolon mcp serve --port N`` wires through to the server.
"""

from __future__ import annotations

import io
import json
import os
import socket
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

# Ensure `src/` is importable when tests run from repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in os.sys.path:
    os.sys.path.insert(0, str(_SRC))


from eidolon import cli as eidolon_cli  # noqa: E402
from eidolon.mcp import server as mcp_server  # noqa: E402
from eidolon.mcp import tools as mcp_tools  # noqa: E402


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class ToolsRegistryTests(unittest.TestCase):
    def test_exactly_three_tools(self):
        self.assertEqual(len(mcp_tools.TOOLS), 4)

    def test_tool_names(self):
        self.assertEqual(
            set(mcp_tools.TOOLS.keys()),
            {"eidolon.report", "eidolon.doctor", "eidolon.learn.step", "eidolon.hindsight.retain"},
        )

    def test_manifest_shape(self):
        for tool in mcp_tools.TOOLS.values():
            m = tool.as_manifest()
            self.assertIn("name", m)
            self.assertIn("description", m)
            self.assertIn("inputSchema", m)
            self.assertEqual(m["inputSchema"]["type"], "object")


class DispatcherTests(unittest.TestCase):
    def test_report_matches_report_build(self):
        from eidolon.reporting.metrics import build

        got = mcp_tools.dispatch("eidolon.report", {"since": "24h"})
        want = build(window="24h").as_dict()
        # Compare counter/schema fields; timestamps drift by microseconds
        # between two independent build() calls, which is fine.
        _skip = {"since_ts", "generated_ts"}
        for k, v in want.items():
            if k in _skip:
                continue
            self.assertEqual(got.get(k), v, msg=f"field {k}")
        self.assertIn("delta", got)
        self.assertIn("has_baseline", got)
        # Both timestamps should still be present and near each other.
        self.assertAlmostEqual(got["since_ts"], want["since_ts"], delta=5)

    def test_report_rejects_bad_window(self):
        got = mcp_tools.dispatch("eidolon.report", {"since": "banana"})
        self.assertIn("error", got)
        self.assertEqual(got["error"]["code"], "invalid_window")

    def test_doctor_matches_registry(self):
        from eidolon.checks import registry, PASS, DEGRADED, FAIL

        got = mcp_tools.dispatch("eidolon.doctor", {})
        raw = [fn() for fn in registry()]
        self.assertEqual(len(got["checks"]), len(raw))
        for gd, rc in zip(got["checks"], raw):
            self.assertEqual(gd["name"], rc.name)
            self.assertEqual(gd["status"], rc.status)
        self.assertIn(got["overall"], (PASS, DEGRADED, FAIL))

    def test_learn_step_wraps_cli_run(self):
        # We stub out the CLI run so this doesn't touch fixtures/replay state.
        with mock.patch("eidolon.commands.learn.run", return_value=0) as m:
            got = mcp_tools.dispatch(
                "eidolon.learn.step", {"iterations": 3, "seed": 7}
            )
            m.assert_called_once()
            kwargs = m.call_args.kwargs
            self.assertEqual(kwargs["iterations"], 3)
            self.assertEqual(kwargs["seed"], 7)
        self.assertEqual(got["exit_code"], 0)
        self.assertEqual(got["status"], "PASS")

    def test_learn_step_rejects_zero_iterations(self):
        got = mcp_tools.dispatch("eidolon.learn.step", {"iterations": 0})
        self.assertIn("error", got)

    def test_learn_step_maps_degraded_status(self):
        with mock.patch("eidolon.commands.learn.run", return_value=2):
            got = mcp_tools.dispatch("eidolon.learn.step", {})
        self.assertEqual(got["status"], "DEGRADED")

    def test_unknown_tool_raises_keyerror(self):
        with self.assertRaises(KeyError):
            mcp_tools.dispatch("eidolon.unknown", {})


class RPCUnitTests(unittest.TestCase):
    def _rpc(self, method: str, params: dict | None = None, rid: int = 1) -> dict:
        req = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            req["params"] = params
        return mcp_server.handle_rpc(json.dumps(req).encode("utf-8"))

    def test_initialize(self):
        resp = self._rpc("initialize", {})
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertIn("result", resp)
        self.assertIn("protocolVersion", resp["result"])
        self.assertEqual(resp["result"]["serverInfo"]["name"], "eidolon")

    def test_tools_list_returns_three(self):
        resp = self._rpc("tools/list", {})
        self.assertEqual(len(resp["result"]["tools"]), 4)

    def test_tools_call_report(self):
        resp = self._rpc(
            "tools/call",
            {"name": "eidolon.report", "arguments": {"since": "24h"}},
        )
        self.assertIn("result", resp)
        self.assertFalse(resp["result"]["isError"])
        content = resp["result"]["content"][0]
        self.assertEqual(content["type"], "text")
        body = json.loads(content["text"])
        self.assertIn("schema", body)

    def test_tools_call_unknown_tool_error(self):
        resp = self._rpc(
            "tools/call", {"name": "eidolon.nope", "arguments": {}}
        )
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], mcp_server.JSONRPC_METHOD_NOT_FOUND)

    def test_tools_call_missing_name(self):
        resp = self._rpc("tools/call", {"arguments": {}})
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], mcp_server.JSONRPC_INVALID_PARAMS)

    def test_unknown_method(self):
        resp = self._rpc("does/not/exist", {})
        self.assertEqual(resp["error"]["code"], mcp_server.JSONRPC_METHOD_NOT_FOUND)

    def test_malformed_json(self):
        resp = mcp_server.handle_rpc(b"{not json")
        self.assertEqual(resp["error"]["code"], mcp_server.JSONRPC_PARSE_ERROR)

    def test_wrong_jsonrpc_version(self):
        req = {"jsonrpc": "1.0", "id": 1, "method": "tools/list"}
        resp = mcp_server.handle_rpc(json.dumps(req).encode("utf-8"))
        self.assertEqual(resp["error"]["code"], mcp_server.JSONRPC_INVALID_REQUEST)

    def test_params_must_be_object(self):
        req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": [1, 2]}
        resp = mcp_server.handle_rpc(json.dumps(req).encode("utf-8"))
        self.assertEqual(resp["error"]["code"], mcp_server.JSONRPC_INVALID_PARAMS)


class BindHostTests(unittest.TestCase):
    def test_bind_host_is_loopback(self):
        self.assertEqual(mcp_server._resolve_bind(), "127.0.0.1")

    def test_serve_rejects_bad_port(self):
        with self.assertRaises(ValueError):
            mcp_server.serve(-1)
        with self.assertRaises(ValueError):
            mcp_server.serve(70000)

    def test_serve_binds_loopback(self):
        port = _pick_free_port()
        srv = mcp_server.serve(port)
        try:
            host, bound = srv.server_address[:2]
            self.assertEqual(host, "127.0.0.1")
            self.assertEqual(bound, port)
        finally:
            srv.server_close()


class LiveServerTests(unittest.TestCase):
    """Spin the server on an ephemeral port and hit it over HTTP."""

    @classmethod
    def setUpClass(cls):
        cls.port = _pick_free_port()
        cls.server = mcp_server.serve(cls.port)
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True
        )
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def _post(self, body: dict) -> dict:
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/mcp",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def test_tools_list_over_http(self):
        resp = self._post({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertEqual(len(resp["result"]["tools"]), 4)

    def test_tools_call_doctor_over_http(self):
        resp = self._post(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "eidolon.doctor", "arguments": {}},
            }
        )
        self.assertIn("result", resp)
        body = json.loads(resp["result"]["content"][0]["text"])
        self.assertIn(body["overall"], ("PASS", "DEGRADED", "FAIL"))

    def test_get_banner(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/")
        with urllib.request.urlopen(req, timeout=5) as resp:
            banner = json.loads(resp.read().decode("utf-8"))
        self.assertEqual(banner["server"], "eidolon-mcp")
        self.assertEqual(banner["bind"], "127.0.0.1")
        self.assertEqual(sorted(banner["tools"]), sorted(mcp_tools.TOOLS.keys()))


class CLIWiringTests(unittest.TestCase):
    def test_mcp_serve_requires_port(self):
        parser = eidolon_cli._build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["mcp", "serve"])

    def test_mcp_serve_parses(self):
        parser = eidolon_cli._build_parser()
        args = parser.parse_args(["mcp", "serve", "--port", "7401"])
        self.assertEqual(args.command, "mcp")
        self.assertEqual(args.mcp_command, "serve")
        self.assertEqual(args.port, 7401)

    def test_mcp_serve_invokes_run_forever(self):
        with mock.patch(
            "eidolon.mcp.server.run_forever", return_value=0
        ) as m:
            rc = eidolon_cli.main(["mcp", "serve", "--port", "7402"])
            m.assert_called_once_with(port=7402)
        self.assertEqual(rc, 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
