"""Restore tracked files from the last-known-good snapshot."""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List

from eidolon.safety.snapshot import current_snapshot, Snapshot
from eidolon.util import events
from eidolon.util.paths import audit_log, repo_root


@dataclass
class RollbackResult:
    ok: bool
    snapshot_id: str = ""
    restored: List[str] = field(default_factory=list)
    would_restore: List[str] = field(default_factory=list)
    reason: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def _audit(record: dict) -> None:
    with audit_log().open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": time.time(), **record}, sort_keys=True) + "\n")


def rollback_to_last_known_good(*, dry_run: bool = False) -> RollbackResult:
    snap = current_snapshot()
    if snap is None:
        events.emit(
            "rollback.no_snapshot",
            events.STATUS_DEGRADED,
            source="safety.rollback",
            reason="last_known_good pointer missing or unreadable",
        )
        return RollbackResult(
            ok=False,
            reason=(
                "no last_known_good snapshot available; run a successful "
                "dream-cycle first"
            ),
        )

    src_dir = Path(snap.path)
    root = repo_root()
    plan: List[str] = list(snap.files)

    if dry_run:
        return RollbackResult(
            ok=True,
            snapshot_id=snap.id,
            would_restore=plan,
            reason="dry run; no files modified",
        )

    restored: List[str] = []
    for rel in plan:
        src = src_dir / rel
        dst = root / rel
        if not src.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        restored.append(rel)

    events.emit(
        "dream.rollback",
        events.STATUS_INFO,
        source="safety.rollback",
        snapshot_id=snap.id,
        restored=restored,
    )
    _audit({"event": "rollback", "snapshot_id": snap.id, "restored": restored})

    return RollbackResult(
        ok=True,
        snapshot_id=snap.id,
        restored=restored,
        reason=f"restored {len(restored)} file(s) from snapshot {snap.id}",
    )
