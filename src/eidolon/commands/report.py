"""`eidolon report` — print measurable metrics for the given window.

Empty state is a valid, structured output. Non-empty state includes deltas
computed against the previous window (for `--since 24h`, we compare against
the 24h before that). The comparison is best-effort: if there is no prior
window data, `delta_*` fields are 0 and `has_baseline` is False.
"""

from __future__ import annotations

import json
import sys

from eidolon.reporting.metrics import Report, build, parse_window
from eidolon.util import events

EXIT_OK = 0


def _delta(report: Report, prev: Report) -> dict:
    def d(a: int, b: int) -> int:
        return a - b

    return {
        "sessions_observed": d(report.sessions_observed, prev.sessions_observed),
        "lessons_added": d(report.lessons_added, prev.lessons_added),
        "proposals_generated": d(report.proposals_generated, prev.proposals_generated),
        "proposals_applied": d(report.proposals_applied, prev.proposals_applied),
        "rollback_count": d(report.rollback_count, prev.rollback_count),
        "inference_requests": d(report.inference_requests, prev.inference_requests),
    }


def _print_human(report: Report, delta: dict) -> None:
    if report.empty_state:
        print("Eidolon report — no events in the requested window yet.")
        print("This is expected on a fresh install; the first dream-cycle run will")
        print("populate metrics. Verify install with `eidolon doctor`.")
        return
    print(f"Eidolon report — window: {report.window}")
    print(f"  sessions observed        : {report.sessions_observed:>6}  ({delta['sessions_observed']:+d})")
    print(f"  lessons added            : {report.lessons_added:>6}  ({delta['lessons_added']:+d})")
    print(f"  proposals generated      : {report.proposals_generated:>6}  ({delta['proposals_generated']:+d})")
    print(f"  proposals applied        : {report.proposals_applied:>6}  ({delta['proposals_applied']:+d})")
    print(f"  rollbacks                : {report.rollback_count:>6}  ({delta['rollback_count']:+d})")
    print(f"  inference requests       : {report.inference_requests:>6}  ({delta['inference_requests']:+d})")
    print(f"  inference degraded       : {report.inference_degraded:>6}")
    print(f"  last doctor status       : {report.last_doctor_status}")
    if report.notes:
        print("\nnotes:")
        for n in report.notes:
            print(f"  - {n}")


def run(*, since: str = "24h", json_out: bool = False) -> int:
    seconds = parse_window(since)
    now = None  # let build() pick time.time()

    report = build(window=since)
    prev = build(window=since, now_ts=report.since_ts)  # same span, one window earlier
    delta = _delta(report, prev)

    events.emit(
        "report.generated",
        events.STATUS_INFO,
        source="commands.report",
        window=since,
        empty=report.empty_state,
    )

    if json_out:
        payload = {
            **report.as_dict(),
            "delta": delta,
            "has_baseline": not prev.empty_state,
        }
        json.dump(payload, sys.stdout, sort_keys=True)
        sys.stdout.write("\n")
    else:
        _print_human(report, delta)

    return EXIT_OK
