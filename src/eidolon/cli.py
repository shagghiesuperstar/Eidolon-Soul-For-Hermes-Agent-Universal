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
