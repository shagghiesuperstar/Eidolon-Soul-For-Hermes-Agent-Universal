# SPDX-License-Identifier: Apache-2.0
"""Deterministic 20-case regression evaluator.

Usage:
    PYTHONPATH=src python -m tests.eval.regression_suite --seed 42

Contract:
- Exits 0 iff every case's `expected_winner` is a registered arm AND the
  reward function returns > 0 for that arm.
- Prints `20/20 cases passed` on success.
- No network. No real inference. No wall-clock non-determinism.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _repo_root() -> Path:
    # This file lives at tests/eval/regression_suite.py.
    return Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="regression_suite")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--fixtures",
        type=str,
        default=str(_repo_root() / "tests" / "eval" / "fixtures"),
    )
    args = parser.parse_args(argv)

    # Ensure src/ is importable when running as `python -m tests.eval.regression_suite`.
    src = _repo_root() / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from eidolon.learning import arms as arms_mod
    from eidolon.learning.rewards import RegressionReward, load_fixtures

    cases = load_fixtures(Path(args.fixtures))
    registry = arms_mod.default_registry()

    unknown = [c.expected_winner for c in cases if not registry.has(c.expected_winner)]
    if unknown:
        print(f"FAIL: unknown expected_winners in fixtures: {sorted(set(unknown))}")
        return 1

    reward = RegressionReward(cases)
    scores = reward.all_scores()

    passed = 0
    for c in cases:
        s = scores.get(c.expected_winner, 0.0)
        if s > 0.0:
            passed += 1
        else:
            print(f"MISS: case={c.case_id} winner={c.expected_winner} score={s}")

    total = len(cases)
    print(f"{passed}/{total} cases passed (seed={args.seed})")
    return 0 if passed == total else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
