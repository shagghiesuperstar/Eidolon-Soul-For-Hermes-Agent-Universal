# SPDX-License-Identifier: Apache-2.0
"""Safety primitives: snapshots, rollback, risk classification."""

from eidolon.safety.classifier import classify_action
from eidolon.safety.risk import (
    NEVER_TOUCH_PATHS,
    RiskClass,
    classify,
    is_never_touch,
)
from eidolon.safety.rollback import RollbackResult, rollback_to_last_known_good
from eidolon.safety.snapshot import Snapshot, list_snapshots, take_snapshot

__all__ = [
    "Snapshot",
    "take_snapshot",
    "list_snapshots",
    "rollback_to_last_known_good",
    "RollbackResult",
    "RiskClass",
    "classify",
    "classify_action",
    "is_never_touch",
    "NEVER_TOUCH_PATHS",
]
