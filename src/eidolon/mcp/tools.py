# SPDX-License-Identifier: Apache-2.0
"""MCP tool definitions and dispatcher for Eidolon.

Three tools, all pure-Python calls into existing command modules. No shell
outshells, no subprocess, no network. Each tool returns the same structured
data the CLI would emit with ``--json``.

Tool schema follows the MCP spec's ``inputSchema`` (JSON-Schema draft-07
compatible subset). Keeping the schema minimal on purpose — every extra
field is a place for callers to disagree with us.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[[Mapping[str, Any]], Dict[str, Any]]

    def as_manifest(self) -> Dict[str, Any]:
        # Shape matches MCP ``tools/list`` result entries.
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


# --- Handlers -----------------------------------------------------------


def _handle_report(args: Mapping[str, Any]) -> Dict[str, Any]:
    """Return the same JSON body ``eidolon report --json`` would print.

    Accepts optional ``since`` (default ``"24h"``). Never raises for a
    malformed window; returns ``{"error": ...}`` and lets the dispatcher
    surface it as an MCP tool error.
    """
    from eidolon.reporting.metrics import build, parse_window

    since = str(args.get("since", "24h"))
    try:
        parse_window(since)  # validate early
    except ValueError as exc:
        return {"error": {"code": "invalid_window", "message": str(exc)}}

    report = build(window=since)
    prev = build(window=since, now_ts=report.since_ts)

    def _d(a: int, b: int) -> int:
        return a - b

    delta = {
        "sessions_observed": _d(report.sessions_observed, prev.sessions_observed),
        "lessons_added": _d(report.lessons_added, prev.lessons_added),
        "proposals_generated": _d(report.proposals_generated, prev.proposals_generated),
        "proposals_applied": _d(report.proposals_applied, prev.proposals_applied),
        "rollback_count": _d(report.rollback_count, prev.rollback_count),
        "inference_requests": _d(report.inference_requests, prev.inference_requests),
    }
    has_baseline = not prev.empty_state
    body = report.as_dict()
    body["delta"] = delta
    body["has_baseline"] = has_baseline
    return body


def _handle_doctor(args: Mapping[str, Any]) -> Dict[str, Any]:
    """Return doctor's structured result set + ``overall`` string."""
    from eidolon.checks import DEGRADED, FAIL, PASS, registry

    model_check = bool(args.get("model_check", False))
    results = [fn() for fn in registry()]
    if model_check:
        from eidolon.checks.provider_capability import check as _probe

        results.append(_probe())

    def _overall(rs: List[Any]) -> str:
        if any(r.status == FAIL for r in rs):
            return FAIL
        if any(r.status == DEGRADED for r in rs):
            return DEGRADED
        return PASS

    return {
        "overall": _overall(results),
        "checks": [
            {"name": r.name, "status": r.status, "reason": r.reason} for r in results
        ],
    }


def _handle_learn_step(args: Mapping[str, Any]) -> Dict[str, Any]:
    """Run one deterministic bandit-step batch and return a compact summary.

    Delegates to ``eidolon.commands.learn.run`` for behavior parity with
    ``eidolon learn --step``. Returns exit_code + note; the caller can
    subsequently pull ``eidolon.report`` for numeric deltas.
    """
    from eidolon.commands import learn as _learn

    try:
        iterations = int(args.get("iterations", 100))
        seed = int(args.get("seed", 42))
    except (TypeError, ValueError) as exc:
        return {"error": {"code": "invalid_argument", "message": str(exc)}}

    if iterations <= 0:
        return {
            "error": {
                "code": "invalid_argument",
                "message": "iterations must be positive",
            }
        }

    fixtures = args.get("fixtures")
    fixtures_dir = Path(str(fixtures)) if fixtures else None

    exit_code = _learn.run(
        iterations=iterations,
        seed=seed,
        fixtures_dir=fixtures_dir,
        stable_ts=True,
    )
    # 0=OK, 2=DEGRADED, 1=FAIL — mirrors CLI contract.
    status = {0: "PASS", 2: "DEGRADED", 1: "FAIL"}.get(exit_code, "UNKNOWN")
    return {"exit_code": exit_code, "status": status, "iterations": iterations, "seed": seed}


# --- Registry -----------------------------------------------------------


TOOLS: Dict[str, Tool] = {
    "eidolon.report": Tool(
        name="eidolon.report",
        description=(
            "Return Eidolon metrics for a rolling window. "
            "Empty-state is a valid response. Fields: schema, since_ts, "
            "generated_ts, window, sessions_observed, lessons_added, "
            "proposals_generated, proposals_applied, rollback_count, "
            "inference_requests, inference_degraded, last_doctor_status, "
            "delta (map), has_baseline (bool)."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "since": {
                    "type": "string",
                    "description": "Window like '24h', '7d', '1h'. Default '24h'.",
                    "default": "24h",
                },
            },
            "additionalProperties": False,
        },
        handler=_handle_report,
    ),
    "eidolon.doctor": Tool(
        name="eidolon.doctor",
        description=(
            "Run Eidolon preflight checks. Returns overall status "
            "(PASS/DEGRADED/FAIL) and a list of checks with per-item "
            "name/status/reason."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "model_check": {
                    "type": "boolean",
                    "description": "Also probe the configured inference provider.",
                    "default": False,
                },
            },
            "additionalProperties": False,
        },
        handler=_handle_doctor,
    ),
    "eidolon.learn.step": Tool(
        name="eidolon.learn.step",
        description=(
            "Run one deterministic bandit-step batch. No network, no live "
            "inference. Returns exit_code + status. Use eidolon.report "
            "afterwards to see numeric deltas."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "iterations": {"type": "integer", "minimum": 1, "default": 100},
                "seed": {"type": "integer", "default": 42},
                "fixtures": {"type": "string", "description": "Override fixtures directory."},
            },
            "additionalProperties": False,
        },
        handler=_handle_learn_step,
    ),
}


def dispatch(name: str, args: Mapping[str, Any] | None) -> Dict[str, Any]:
    """Look up ``name`` and invoke its handler with ``args`` (defaults to {}).

    Raises ``KeyError`` for unknown tool names — the JSON-RPC server maps
    that to a ``-32601`` (method not found) error.
    """
    tool = TOOLS[name]
    return tool.handler(args or {})
