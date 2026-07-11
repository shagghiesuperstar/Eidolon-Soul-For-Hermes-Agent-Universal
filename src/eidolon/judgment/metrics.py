# SPDX-License-Identifier: Apache-2.0
"""Judgment Brain persistent metrics.

Two responsibilities:
1. Persist lifetime judgment counters to a JSON file that survives
   events.jsonl rotation.
2. Emit judgment.* event kinds into events.jsonl so reporting/metrics.py
   build() can aggregate them in any time window.

All writes are atomic (write-tmp + os.replace). Reads never raise on
missing file — returns zeroed dict. Failures emit a DEGRADED event but
never propagate to callers.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Dict

from eidolon.util import events

_FILENAME = "eidolon_judgment_metrics.json"

_ZERO: Dict[str, int] = {
    "lessons_judged": 0,
    "soul_edicts": 0,
    "skills_modified": 0,
    "config_changes": 0,
    "memory_retired": 0,
}

# Maps ActionKind string -> (counter_key, event_kind)
_ACTION_MAP = {
    "SOUL_EDICT":   ("soul_edicts",     "judgment.soul"),
    "SKILL_UPDATE": ("skills_modified", "judgment.skill"),
    "CONFIG_TUNE":  ("config_changes",  "judgment.config"),
    "MEMORY_RETIRE":("memory_retired",  "judgment.retire"),
    "MEMORY_RETAIN": None,  # no-op; count judged but no sub-kind event
}


def _metrics_path() -> Path:
    state_dir = os.environ.get("EIDOLON_STATE_DIR", "").strip()
    if state_dir:
        return Path(state_dir) / _FILENAME
    return Path.home() / ".eidolon" / _FILENAME


def load() -> Dict[str, int]:
    """Load lifetime judgment counters. Returns zeroed dict if file absent/corrupt."""
    path = _metrics_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return {k: int(raw.get(k, 0)) for k in _ZERO}
    except Exception:  # noqa: BLE001
        return dict(_ZERO)


def _save(data: Dict[str, int]) -> None:
    path = _metrics_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".jmetrics_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, sort_keys=True)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def record(action_kind: str) -> None:
    """Increment counters for one judgment action and emit events.

    Safe to call from hermes_bridge.py. Failures are caught and emitted
    as DEGRADED events so the MEMORY.md write path is never blocked.
    """
    try:
        data = load()
        data["lessons_judged"] = data.get("lessons_judged", 0) + 1

        # Emit the per-lesson event so windowed aggregation works.
        events.emit(
            "judgment.judged",
            events.STATUS_OK,
            source="judgment.metrics",
            action_kind=action_kind,
        )

        mapping = _ACTION_MAP.get(action_kind)
        if mapping is not None:
            counter_key, event_kind = mapping
            data[counter_key] = data.get(counter_key, 0) + 1
            events.emit(
                event_kind,
                events.STATUS_OK,
                source="judgment.metrics",
                action_kind=action_kind,
            )

        _save(data)
    except Exception as exc:  # noqa: BLE001
        events.emit(
            "judgment.metrics.error",
            events.STATUS_DEGRADED,
            source="judgment.metrics",
            error=str(exc),
        )
