# SPDX-License-Identifier: Apache-2.0
"""Check: preferences.jsonl (if present) has every line at schema=1.

PASS: file exists and every line parses as schema=1.
DEGRADED: file does not exist yet (nothing has emitted a pair; not a failure).
FAIL: file exists but at least one line is corrupt or has wrong schema.
"""

from __future__ import annotations

import json

from eidolon.checks import CheckResult, DEGRADED, FAIL, PASS
from eidolon.learning.preferences import SCHEMA as PREF_SCHEMA
from eidolon.learning.preferences import preferences_path


def check() -> CheckResult:
    path = preferences_path()
    if not path.exists():
        return CheckResult(
            name="preferences_schema",
            status=DEGRADED,
            reason=(
                "preferences.jsonl not present yet; will be created by first "
                "bandit-outcome or rollback event."
            ),
        )

    n = 0
    corrupt = 0
    wrong_schema = 0
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                n += 1
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    corrupt += 1
                    continue
                if d.get("schema") != PREF_SCHEMA:
                    wrong_schema += 1
    except OSError as exc:
        return CheckResult(
            name="preferences_schema",
            status=FAIL,
            reason=f"cannot read {path}: {type(exc).__name__}",
        )

    if corrupt or wrong_schema:
        return CheckResult(
            name="preferences_schema",
            status=FAIL,
            reason=(
                f"corrupt lines: {corrupt}; wrong-schema lines: {wrong_schema} "
                f"out of {n}. Schema is frozen at v{PREF_SCHEMA}."
            ),
            detail={
                "pairs": str(n),
                "corrupt": str(corrupt),
                "wrong_schema": str(wrong_schema),
            },
        )
    return CheckResult(
        name="preferences_schema",
        status=PASS,
        reason=f"{n} pairs, all schema=v{PREF_SCHEMA}.",
        detail={"pairs": str(n)},
    )
