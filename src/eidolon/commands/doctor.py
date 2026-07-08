# SPDX-License-Identifier: Apache-2.0
"""`eidolon doctor` — preflight checks with a mandatory DEGRADED state.

Exit codes:
- 0 : all checks PASS
- 2 : at least one DEGRADED check, no FAILs
- 1 : at least one FAIL

Human output is intentionally terse. Machine output (--json) is the contract.
"""

from __future__ import annotations

import json
import sys
from typing import List

from eidolon.checks import CheckResult, DEGRADED, FAIL, PASS, registry
from eidolon.util import events

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_DEGRADED = 2


def _overall(results: List[CheckResult]) -> str:
    if any(r.status == FAIL for r in results):
        return FAIL
    if any(r.status == DEGRADED for r in results):
        return DEGRADED
    return PASS


def _print_human(results: List[CheckResult], overall: str) -> None:
    glyph = {PASS: "✓", DEGRADED: "!", FAIL: "✗"}
    for r in results:
        # Plain ASCII fallback for terminals without Unicode.
        mark = glyph.get(r.status, "?")
        print(f"  {mark} [{r.status:<8}] {r.name}: {r.reason}")
    print(f"\noverall: {overall}")


def run(*, json_out: bool = False, model_check: bool = False) -> int:
    results = [fn() for fn in registry()]

    if model_check:
        # Additional deterministic capability probe. Result contributes to overall.
        from eidolon.checks.provider_capability import check as _probe

        results.append(_probe())

    overall = _overall(results)

    for r in results:
        events.emit(
            f"doctor.{r.name}",
            r.status if r.status in (PASS, DEGRADED, FAIL) else events.STATUS_INFO,
            source="commands.doctor",
            reason=r.reason,
        )
    events.emit(
        "doctor.summary",
        overall,
        source="commands.doctor",
        n_checks=len(results),
    )

    if json_out:
        payload = {
            "overall": overall,
            "checks": [r.as_dict() for r in results],
        }
        json.dump(payload, sys.stdout, sort_keys=True)
        sys.stdout.write("\n")
    else:
        _print_human(results, overall)

    if overall == FAIL:
        return EXIT_FAIL
    if overall == DEGRADED:
        return EXIT_DEGRADED
    return EXIT_OK
