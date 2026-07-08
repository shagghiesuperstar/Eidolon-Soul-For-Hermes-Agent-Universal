# SPDX-License-Identifier: Apache-2.0
"""Check: Eidolon can create + write its own state directory."""

from __future__ import annotations

from eidolon.checks import CheckResult, FAIL, PASS
from eidolon.util.paths import eidolon_state_dir


def check() -> CheckResult:
    d = eidolon_state_dir()  # side-effect: mkdir -p
    probe = d / ".doctor-write-probe"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return CheckResult(
            name="state_dir",
            status=FAIL,
            reason=f"Cannot write to {d}: {type(exc).__name__}",
        )
    return CheckResult(
        name="state_dir",
        status=PASS,
        reason=f"State dir writable at {d}.",
    )
