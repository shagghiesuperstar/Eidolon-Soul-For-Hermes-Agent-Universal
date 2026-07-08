# SPDX-License-Identifier: Apache-2.0
"""`eidolon learn --step` — run N deterministic bandit episodes.

Contract:
- No network. No real inference. The reward is computed against fixtures
  under `tests/eval/fixtures/` (or `--fixtures DIR`).
- Reproducible: same `--seed` + same fixtures + same arm registry ->
  same replay.jsonl bytes (except `ts` field, which we hash-derive from
  seed+iteration to keep the buffer bit-stable in CI).
- Writes to `$EIDOLON_HOME/replay.jsonl` via `learning.replay.append`.

Exit codes:
  0 — all requested iterations completed
  2 — completed with DEGRADED signal (e.g. no fixtures found)
  1 — hard failure
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path
from typing import Optional

from eidolon.learning import arms as arms_mod
from eidolon.learning.bandit import ThompsonBandit
from eidolon.learning.replay import append as replay_append
from eidolon.learning.rewards import RegressionReward, load_fixtures
from eidolon.learning.schemas import EpisodeRecord
from eidolon.util import events
from eidolon.util.paths import repo_root

EXIT_OK = 0
EXIT_DEGRADED = 2
EXIT_FAIL = 1


def _default_fixtures_dir() -> Path:
    return repo_root() / "tests" / "eval" / "fixtures"


def _episode_id(seed: int, iteration: int) -> str:
    return hashlib.sha256(f"{seed}|{iteration}".encode("utf-8")).hexdigest()[:16]


def _deterministic_ts(seed: int, iteration: int) -> float:
    """Bit-stable timestamp for CI: hash-derived, not wall-clock.

    Keeps replay.jsonl comparable across runs. Real production emission
    uses wall-clock (see `EpisodeRecord.ts` default at write time).
    """
    h = hashlib.sha256(f"ts|{seed}|{iteration}".encode("utf-8")).digest()
    # Map first 4 bytes to a stable float in [0, 1e9).
    n = int.from_bytes(h[:4], "big")
    return float(n) / 4.294967295  # -> [0, 1e9)


def run(
    *,
    iterations: int = 100,
    seed: int = 42,
    fixtures_dir: Optional[Path] = None,
    stable_ts: bool = True,
) -> int:
    if iterations <= 0:
        print(f"learn: --iterations must be positive, got {iterations}", file=sys.stderr)
        return EXIT_FAIL

    fixtures_path = fixtures_dir or _default_fixtures_dir()
    if not fixtures_path.exists():
        events.emit(
            "learn.degraded",
            events.STATUS_DEGRADED,
            source="commands.learn",
            reason="no_fixtures_dir",
            path=str(fixtures_path),
        )
        print(f"learn: fixtures dir not found: {fixtures_path}", file=sys.stderr)
        return EXIT_DEGRADED

    try:
        cases = load_fixtures(fixtures_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"learn: {exc}", file=sys.stderr)
        return EXIT_FAIL

    reward = RegressionReward(cases)
    arm_ids = arms_mod.default_registry().ids()

    # Filter to arms that appear in at least one fixture — the bandit is
    # only meaningful over arms with observable reward.
    referenced: set[str] = set()
    for c in cases:
        referenced.update(c.arm_inputs.keys())
    bandit_arms = [a for a in arm_ids if a in referenced]
    if not bandit_arms:
        print("learn: no registered arms appear in fixtures", file=sys.stderr)
        return EXIT_FAIL

    bandit = ThompsonBandit(bandit_arms, rng=random.Random(seed))

    for i in range(iterations):
        picked = bandit.sample_arm()
        r = reward.for_arm(picked)
        alpha, beta = bandit.observe(picked, r)
        ts = _deterministic_ts(seed, i) if stable_ts else time.time()
        rec = EpisodeRecord(
            ts=ts,
            episode_id=_episode_id(seed, i),
            arm_id=picked,
            # Context hash: fold arm-id + iteration; never fixture content.
            context_hash=hashlib.sha256(f"{picked}|{i}".encode("utf-8")).hexdigest(),
            reward=r,
            posterior_a=alpha,
            posterior_b=beta,
        )
        replay_append(rec)

    posterior = bandit.posterior_means()
    counts = bandit.selection_counts()

    # REC-009: emit preference pairs from bandit outcomes.
    # For each pair (A, B) where A's posterior mean strictly beats B's, log
    # A > B once, using a stable structural context tag (never raw content).
    try:
        from eidolon.learning.preferences import emit_bandit_outcome

        ranked = sorted(posterior.items(), key=lambda kv: kv[1], reverse=True)
        for i in range(len(ranked)):
            for j in range(i + 1, len(ranked)):
                chosen, chosen_mean = ranked[i]
                rejected, rejected_mean = ranked[j]
                if chosen_mean > rejected_mean:
                    emit_bandit_outcome(
                        chosen_arm=chosen,
                        rejected_arm=rejected,
                        context=f"learn:seed={seed}:iterations={iterations}",
                    )
    except Exception:  # noqa: BLE001 — emission must never break training
        pass

    events.emit(
        "learn.step",
        events.STATUS_PASS,
        source="commands.learn",
        iterations=iterations,
        seed=seed,
        arms=len(bandit_arms),
        posterior_means=posterior,
        selection_counts=counts,
    )
    print(
        json.dumps(
            {
                "iterations": iterations,
                "seed": seed,
                "arms": bandit_arms,
                "posterior_means": posterior,
                "selection_counts": counts,
            },
            sort_keys=True,
        )
    )
    return EXIT_OK


def build_parser(sub: argparse._SubParsersAction) -> None:  # pragma: no cover - wiring
    p = sub.add_parser("learn", help="Run bandit episodes (v1: prompt-phrasing arms).")
    p.add_argument("--step", action="store_true", help="Run one training step batch.")
    p.add_argument("--iterations", type=int, default=100)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--fixtures", type=str, default=None, help="Override fixtures dir.")
    p.add_argument(
        "--wall-clock-ts",
        action="store_true",
        help="Use wall-clock ts instead of the CI-stable hash-derived ts.",
    )
    p.set_defaults(_run=_cmd_learn)


def _cmd_learn(args: argparse.Namespace) -> int:
    if not args.step:
        print("learn: --step is required (v1 has only the training-step verb)", file=sys.stderr)
        return EXIT_FAIL
    fixtures = Path(args.fixtures) if args.fixtures else None
    return run(
        iterations=args.iterations,
        seed=args.seed,
        fixtures_dir=fixtures,
        stable_ts=not args.wall_clock_ts,
    )
