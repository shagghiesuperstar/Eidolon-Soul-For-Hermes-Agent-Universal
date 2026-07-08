# Eidolon MCP server

Eidolon ships a **stdlib-only, loopback-only** MCP server. It speaks a minimal
JSON-RPC 2.0 dialect over HTTP that MCP clients (e.g. Claude Desktop) can call.

- **Bind**: `127.0.0.1` only. Never the any-interface wildcard.
- **Port**: chosen by you via `--port`. No default.
- **Runtime deps**: zero. Stdlib only. No `mcp` client library needed to run
  the server. (The integration test suite is skipped when a client library
  is absent — see `tests/integration/test_mcp_client.py`.)
- **Tools exposed** (exactly 3):
  1. `eidolon.report`
  2. `eidolon.doctor`
  3. `eidolon.learn.step`

## Starting the server

```bash
eidolon mcp serve --port 7401
# [eidolon-mcp] listening on http://127.0.0.1:7401/mcp
```

## Quick smoke check

```bash
curl -sS -X POST http://127.0.0.1:7401/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | jq '.result.tools | length'
# 3
```

Call a tool:

```bash
curl -sS -X POST http://127.0.0.1:7401/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call",
       "params":{"name":"eidolon.doctor","arguments":{}}}' | jq '.result'
```

## Claude Desktop configuration

Claude Desktop reads a `claude_desktop_config.json`. Register Eidolon like this
(assuming `eidolon` is on your `PATH`):

```json
{
  "mcpServers": {
    "eidolon": {
      "command": "eidolon",
      "args": ["mcp", "serve", "--port", "7401"]
    }
  }
}
```

If your MCP client speaks HTTP+JSON-RPC directly instead of spawning a process,
point it at `http://127.0.0.1:7401/mcp`.

## Tool contract summary

| Tool | Inputs | Returns |
|------|--------|---------|
| `eidolon.report` | `since` (string, default `"24h"`) | Report body: schema, counters, `delta`, `has_baseline`. |
| `eidolon.doctor` | `model_check` (bool, default `false`) | `overall` (PASS/DEGRADED/FAIL) + `checks[]` (name/status/reason). |
| `eidolon.learn.step` | `iterations` (int, default 100), `seed` (int, default 42), optional `fixtures` path | `{exit_code, status, iterations, seed}`. |

Each tool returns the exact structured payload that `eidolon <command> --json`
would print. Empty state is a valid response; never `null`.

## Security model

- The server is single-tenant and loopback-only. Any process on the host can
  reach it. Do not expose it beyond 127.0.0.1.
- No authentication. If you need remote access, put it behind an SSH tunnel or
  a reverse proxy you control.
- Tools are pure functions over Eidolon's own event store; there is no
  arbitrary code execution surface.

## Rollback

```bash
git reset --hard origin/main && git branch -D rec-013/mcp-server
```

Refs: `master_EIDOLON_roadmap(F5).md` § REC-013.
