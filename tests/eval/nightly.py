# SPDX-License-Identifier: Apache-2.0
"""Nightly-eval driver.

Runs ``tests/eval/regression_suite.py --seed 42 --json``, computes deltas
against the last line of ``docs/eval-history.jsonl``, and:

- In ``--dry-run``: prints ``would append delta=X.XX (threshold Y%)`` and
  exits 0. Does not modify any file.
- Otherwise: appends the new record to ``docs/eval-history.jsonl`` on
  stdout for a bot-commit workflow to pick up, and returns exit code:
    * 0 if no regression beyond the threshold,
    * 2 if a regression >REGRESSION_THRESHOLD is detected (DEGRADED); the
      workflow then opens a `regression` issue.

No live inference. Uses REC-008's mock provider by way of the regression
suite's static reward function.
"""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# Regression threshold. Editable without a REC per roadmap.
REGRESSION_THRESHOLD = 0.05  # 5% drop in pass_rate

EXIT_OK = 0
EXIT_DEGRADED = 2
EXIT_FAIL = 1


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _history_path() -> Path:
    return _repo_root() / "docs" / "eval-history.jsonl"


def _run_suite(seed: int, fixtures: Optional[Path]) -> Dict[str, Any]:
    """Invoke the regression suite in-process for determinism."""
    # Make ``tests.eval.regression_suite`` importable whether the driver
    # is run via ``python -m tests.eval.nightly`` or ``python tests/eval/nightly.py``.
    repo_root = _repo_root()
    for p in (str(repo_root), str(repo_root / "src")):
        if p not in sys.path:
            sys.path.insert(0, p)
    from tests.eval import regression_suite

    argv = ["--seed", str(seed), "--json"]
    if fixtures is not None:
        argv += ["--fixtures", str(fixtures)]
    buf = io.StringIO()
    real_stdout = sys.stdout
    try:
        sys.stdout = buf
        regression_suite.main(argv)
    finally:
        sys.stdout = real_stdout
    line = buf.getvalue().strip().splitlines()[-1]
    return json.loads(line)


def _read_last_record(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return None
    with path.open("r", encoding="utf-8") as fh:
        lines = [ln.strip() for ln in fh if ln.strip()]
    if not lines:
        return None
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return None


def _delta(current: Dict[str, Any], previous: Optional[Dict[str, Any]]) -> float:
    if previous is None:
        return 0.0
    cur = float(current.get("pass_rate", 0.0))
    prv = float(previous.get("pass_rate", 0.0))
    return cur - prv


def _build_record(
    metrics: Dict[str, Any],
    ts: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "schema": 1,
        "ts": ts or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seed": metrics["seed"],
        "total": metrics["total"],
        "passed": metrics["passed"],
        "pass_rate": metrics["pass_rate"],
        "misses": metrics.get("misses", []),
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="nightly")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--fixtures", type=str, default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute delta and print intent; do not modify history.",
    )
    parser.add_argument(
        "--history",
        type=str,
        default=None,
        help="Override docs/eval-history.jsonl path (for tests).",
    )
    parser.add_argument(
        "--ts",
        type=str,
        default=None,
        help="Override timestamp string (for tests).",
    )
    args = parser.parse_args(argv)

    fixtures = Path(args.fixtures) if args.fixtures else None
    history = Path(args.history) if args.history else _history_path()

    try:
        metrics = _run_suite(args.seed, fixtures)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"nightly: regression suite failed: {exc}", file=sys.stderr)
        return EXIT_FAIL

    previous = _read_last_record(history)
    delta = _delta(metrics, previous)
    threshold_pct = REGRESSION_THRESHOLD * 100
    regressed = delta < -REGRESSION_THRESHOLD

    if args.dry_run:
        print(
            f"would append delta={delta:+.2f} (threshold {threshold_pct:.0f}%)"
        )
        return EXIT_OK

    record = _build_record(metrics, ts=args.ts)
    history.parent.mkdir(parents=True, exist_ok=True)
    with history.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")

    print(f"appended delta={delta:+.4f} (threshold {threshold_pct:.0f}%)")
    if regressed:
        print(
            f"REGRESSION: pass_rate dropped {delta:+.4f} (>|{REGRESSION_THRESHOLD}|); "
            "workflow will open a `regression` issue.",
            file=sys.stderr,
        )
        return EXIT_DEGRADED
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
