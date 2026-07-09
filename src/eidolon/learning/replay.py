# SPDX-License-Identifier: Apache-2.0
"""Append-only replay buffer for bandit episodes.

Contract:
- One JSON object per line at `$EIDOLON_HOME/replay.jsonl`.
- Never rewritten, never truncated. Rotation (if ever) is a future REC.
- Schema is frozen at v1; readers pin `schema == 1`.
- The buffer stores ONLY the fields in `EpisodeRecord`: no raw context, no
  raw prompts, no operator strings.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator, TYPE_CHECKING

if TYPE_CHECKING:
    from eidolon.learning.bandit import ThompsonBandit

from eidolon.learning.schemas import SCHEMA, EpisodeRecord
from eidolon.util.paths import eidolon_state_dir


def replay_path() -> Path:
    return eidolon_state_dir() / "replay.jsonl"


def append(record: EpisodeRecord) -> None:
    """Append one episode record to the replay buffer.

    Any field mismatching schema=1 raises before touching disk.
    """
    if record.schema != SCHEMA:
        raise ValueError(f"schema mismatch: expected {SCHEMA}, got {record.schema}")
    line = json.dumps(record.as_dict(), separators=(",", ":"), sort_keys=True)
    path = replay_path()
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def iter_records() -> Iterator[EpisodeRecord]:
    """Yield every record; skip corrupt lines silently (never crash reader)."""
    path = replay_path()
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("schema") != SCHEMA:
                # Loud in memory, silent on stream — caller can count via `count()`.
                continue
            yield EpisodeRecord(**d)


def hydrate_bandit(
    bandit: "ThompsonBandit",
    records: Iterator[EpisodeRecord],
) -> tuple[int, int]:
    """Replay persisted episodes into a fresh bandit to restore durable posteriors.

    Iterates *records* once, calling ``bandit.observe()`` for every record
    whose ``arm_id`` is registered in the bandit.  Records referencing
    unknown arms are counted as orphaned and silently skipped — callers
    should emit DEGRADED if ``skipped_orphaned > 0``.

    Returns:
        (consumed, skipped_orphaned) — both are non-negative integers.

    This function is pure w.r.t. IO: it performs no file reads or writes.
    All IO is the caller's responsibility (pass ``iter_records()`` from
    outside so the function stays testable without touching disk).
    """
    consumed = 0
    skipped_orphaned = 0
    known = set(bandit.arms())
    for record in records:
        if record.arm_id not in known:
            skipped_orphaned += 1
            continue
        bandit.observe(record.arm_id, record.reward)
        consumed += 1
    return consumed, skipped_orphaned


def count() -> int:
    path = replay_path()
    if not path.exists():
        return 0
    n = 0
    with path.open("r", encoding="utf-8") as fh:
        for _ in fh:
            n += 1
    return n
