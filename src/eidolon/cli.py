# SPDX-License-Identifier: Apache-2.0
"""Canonical Eidolon CLI.

Design notes (Fable-5 direction):
- One well-named command per capability; flags exist but are never required.
- Every subcommand exits 0 on PASS, 2 on DEGRADED, 1 on FAIL, 64 on usage error.
  Exit codes match sysexits.h where sensible; DEGRADED is 2 so shell scripts can
  distinguish "loud reduced mode" from "broken".
- No subcommand ever silently no-ops. Empty-state is a valid, structured output.
- The CLI itself imports nothing outside stdlib and the `eidolon` package.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Callable, Dict

from eidolon._version import __version__

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_DEGRADED = 2
EXIT_USAGE = 64


def _cmd_doctor(args: argparse.Namespace) -> int:
    from eidolon.commands import doctor

    return doctor.run(json_out=args.json, model_check=args.model_check)


def _cmd_report(args: argparse.Namespace) -> int:
    from eidolon.commands import report

    return report.run(since=args.since, json_out=args.json)


def _cmd_version(_args: argparse.Namespace) -> int:
    print(__version__)
    return EXIT_OK


def _cmd_rollback(args: argparse.Namespace) -> int:
    from eidolon.commands import rollback

    return rollback.run(dry_run=args.dry_run, json_out=args.json)


def _cmd_verify(args: argparse.Namespace) -> int:
    from eidolon.commands import verify

    return verify.run(json_out=args.json, strict=args.strict)


def _cmd_learn(args: argparse.Namespace) -> int:
    from pathlib import Path

    from eidolon.commands import learn

    if not args.step:
        print("learn: --step is required (v1 has only the training-step verb)", file=sys.stderr)
        return EXIT_FAIL
    fixtures = Path(args.fixtures) if args.fixtures else None
    return learn.run(
        iterations=args.iterations,
        seed=args.seed,
        fixtures_dir=fixtures,
        stable_ts=not args.wall_clock_ts,
    )


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="eidolon",
        description="Self-improvement layer for Hermes Agent. "
        "Ships loud, degrades loud, never silently no-ops.",
    )
    p.add_argument("--version", action="version", version=f"eidolon {__version__}")

    sub = p.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = False  # allow bare `eidolon` to print help

    d = sub.add_parser("doctor", help="Preflight checks. Exits 0/2/1 for PASS/DEGRADED/FAIL.")
    d.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    d.add_argument(
        "--model-check",
        action="store_true",
        help="Also probe the configured inference provider for capability tier support.",
    )
    d.set_defaults(func=_cmd_doctor)

    r = sub.add_parser("report", help="Print measurable metrics (learning deltas, counters).")
    r.add_argument("--since", default="24h", help="Window (e.g. 24h, 7d). Default: 24h.")
    r.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    r.set_defaults(func=_cmd_report)

    v = sub.add_parser("version", help="Print the Eidolon version.")
    v.set_defaults(func=_cmd_version)

    b = sub.add_parser("rollback", help="Restore state from last-known-good snapshot.")
    b.add_argument("--dry-run", action="store_true", help="Report what would change; do not modify.")
    b.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    b.set_defaults(func=_cmd_rollback)

    vf = sub.add_parser(
        "verify",
        help="Post-install end-to-end smoke test. Exercises doctor + report + rollback --dry-run.",
    )
    vf.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    vf.add_argument(
        "--strict",
        action="store_true",
        help="Treat DEGRADED as failure (exit 2). Default folds DEGRADED into PASS.",
    )
    vf.set_defaults(func=_cmd_verify)

    ln = sub.add_parser(
        "learn",
        help="Run bandit episodes (v1: prompt-phrasing arms). Deterministic; no network.",
    )
    ln.add_argument("--step", action="store_true", help="Run one training-step batch.")
    ln.add_argument("--iterations", type=int, default=100)
    ln.add_argument("--seed", type=int, default=42)
    ln.add_argument("--fixtures", type=str, default=None, help="Override fixtures dir.")
    ln.add_argument(
        "--wall-clock-ts",
        action="store_true",
        help="Use wall-clock ts instead of the CI-stable hash-derived ts.",
    )
    ln.set_defaults(func=_cmd_learn)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help(sys.stderr)
        return EXIT_USAGE
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover - exercised via python -m
    raise SystemExit(main())
