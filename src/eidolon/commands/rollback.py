# SPDX-License-Identifier: Apache-2.0
"""`eidolon rollback` — restore from last-known-good snapshot."""

from __future__ import annotations

import json
import sys

from eidolon.safety import rollback_to_last_known_good

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_DEGRADED = 2


def run(*, dry_run: bool = False, json_out: bool = False) -> int:
    result = rollback_to_last_known_good(dry_run=dry_run)

    # REC-009: emit a preference pair on a real (non-dry-run) rollback.
    # Prior state is preferred over current-broken state. Context is a
    # structural digest of the file set — never raw content.
    if not dry_run and result.ok and result.restored:
        try:
            from eidolon.learning.preferences import emit_rollback_event

            file_digest = "|".join(sorted(result.restored))
            emit_rollback_event(
                prior_state_id="last_known_good",
                current_state_id="pre_rollback",
                context=f"rollback:{file_digest}",
            )
        except Exception:  # noqa: BLE001 — emission must never break rollback
            pass

    if json_out:
        json.dump(result.as_dict(), sys.stdout, sort_keys=True)
        sys.stdout.write("\n")
    else:
        if result.ok:
            print(f"rollback: {result.reason}")
            files = result.would_restore if dry_run else result.restored
            for f in files:
                marker = "would restore" if dry_run else "restored"
                print(f"  {marker}: {f}")
        else:
            print(f"rollback failed: {result.reason}", file=sys.stderr)
    if not result.ok:
        return EXIT_DEGRADED  # missing snapshot is DEGRADED, not FAIL
    return EXIT_OK
