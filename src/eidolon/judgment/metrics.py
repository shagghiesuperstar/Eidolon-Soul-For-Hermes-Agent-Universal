# SPDX-License-Identifier: Apache-2.0
"""Persist and load Judgment Brain metrics for `eidolon report`.

Metrics file: $EIDOLON_HOME/judgment_metrics.jsonl
Each line is one judgment event: {ts, kind, status, lesson_prefix}

load_metrics() aggregates totals from the full history:
    lessons_judged   — total classify calls
    skills_modified  — SKILL_UPDATE with status=ok
    soul_edicts      — SOUL_EDICT with status=ok
    config_changes   — CONFIG_TUNE with status=ok
    memory_retired   — MEMORY_RETIRE with status=ok
    memory_retained  — MEMORY_RETAIN (no-op)
    skipped          — duplicate / no-op
    failed           — any status=fail
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional


def _metrics_path(eidolon_home: Optional[Path] = None) -> Path:
    home = eidolon_home or Path(
        os.environ.get("EIDOLON_HOME", str(Path.home() / ".hermes" / "state" / "eidolon"))
    )
    p = home / "judgment_metrics.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def record_judgment(
    kind: str,
    status: str,
    lesson: str,
    *,
    eidolon_home: Optional[Path] = None,
) -> None:
    """Append one judgment event to the metrics log. Never raises."""
    entry = {
        "ts": time.time(),
        "kind": kind,
        "status": status,
        "lesson_prefix": lesson[:80],
    }
    try:
        path = _metrics_path(eidolon_home)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass  # metrics loss is acceptable; never crash the main path


def load_metrics(eidolon_home: Optional[Path] = None) -> Dict[str, Any]:
    """Return aggregated judgment counters from the full history."""
    counts: Dict[str, int] = {
        "lessons_judged": 0,
        "skills_modified": 0,
        "soul_edicts": 0,
        "config_changes": 0,
        "memory_retired": 0,
        "memory_retained": 0,
        "skipped": 0,
        "failed": 0,
    }
    path = _metrics_path(eidolon_home)
    if not path.exists():
        return counts

    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                counts["lessons_judged"] += 1
                kind = rec.get("kind", "")
                status = rec.get("status", "")
                if status == "fail":
                    counts["failed"] += 1
                elif status == "skip":
                    counts["skipped"] += 1
                elif status == "ok":
                    if kind == "skill_update":
                        counts["skills_modified"] += 1
                    elif kind == "soul_edict":
                        counts["soul_edicts"] += 1
                    elif kind == "config_tune":
                        counts["config_changes"] += 1
                    elif kind == "memory_retire":
                        counts["memory_retired"] += 1
                    elif kind == "memory_retain":
                        counts["memory_retained"] += 1
    except OSError:
        pass

    return counts


__all__ = ["record_judgment", "load_metrics"]
