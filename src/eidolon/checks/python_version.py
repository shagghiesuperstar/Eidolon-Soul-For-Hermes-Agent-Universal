# SPDX-License-Identifier: Apache-2.0
"""Check: running Python interpreter is on the supported version rail.

Policy (REC-016):

- FAIL     : Python < 3.10 (installer already blocks this; belt-and-braces).
- DEGRADED : Python 3.10 **after** 2027-01-01 (3.10 EOL is 2026-10; give users
             time before flipping to DEGRADED).
- DEGRADED : Python > 3.13 (untested in the CI matrix as of 2026-07).
- PASS     : Python 3.11 - 3.13, and Python 3.10 while still supported.

Also exports ``compatibility_supported`` which aggregates
``python_version`` (currently the only compat-related check besides the
existing ``hermes_version`` freshness gate) as a single worst-of signal
consumed by the doctor.

The 3.10 deprecation date lives here as a module constant so tests can
manipulate it without monkey-patching ``datetime``.
"""

from __future__ import annotations

import datetime as _dt
import sys
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

from eidolon.checks import CheckResult, DEGRADED, FAIL, PASS

# When 3.10 becomes DEGRADED. Chosen safely after 3.10's upstream EOL
# (2026-10) so users have a clear transition runway.
PY_310_DEGRADED_AFTER = _dt.date(2027, 1, 1)

# Currently CI-tested Python matrix: 3.10, 3.11, 3.12, 3.13.
SUPPORTED_MIN = (3, 10)
UNTESTED_ABOVE = (3, 13)


def _today() -> _dt.date:
    """Isolated so tests can override it via monkeypatch."""
    return _dt.date.today()


def _current_version() -> Tuple[int, int]:
    return sys.version_info[0], sys.version_info[1]


def _classify(major_minor: Tuple[int, int], today: _dt.date) -> Tuple[str, str]:
    """Return (status, reason) for a given (major, minor) + reference date."""
    if major_minor < SUPPORTED_MIN:
        return (
            FAIL,
            f"python {major_minor[0]}.{major_minor[1]} is below the minimum "
            f"supported version {SUPPORTED_MIN[0]}.{SUPPORTED_MIN[1]}",
        )
    if major_minor == (3, 10):
        if today >= PY_310_DEGRADED_AFTER:
            return (
                DEGRADED,
                f"python 3.10 is past its supported window "
                f"(deprecated after {PY_310_DEGRADED_AFTER.isoformat()}); "
                "upgrade to 3.11+",
            )
        return (PASS, "python 3.10 is supported until " + PY_310_DEGRADED_AFTER.isoformat())
    if major_minor > UNTESTED_ABOVE:
        return (
            DEGRADED,
            f"python {major_minor[0]}.{major_minor[1]} is above the tested "
            f"matrix ({UNTESTED_ABOVE[0]}.{UNTESTED_ABOVE[1]}); "
            "may work but not verified",
        )
    return (PASS, f"python {major_minor[0]}.{major_minor[1]} is on the tested matrix")


def check() -> CheckResult:
    status, reason = _classify(_current_version(), _today())
    return CheckResult(name="python_version", status=status, reason=reason)


def compatibility_supported() -> CheckResult:
    """Aggregate the compat-facing checks into a single worst-of signal.

    Currently rolls up ``python_version`` (this file) and ``hermes_version``
    (Hermes freshness). Kept as a separate aggregator so operators can see
    both the per-check detail and a single "am I on a supported stack?"
    line at the top of ``doctor --json``.
    """
    from eidolon.checks import hermes_version

    sub = [check(), hermes_version.check()]
    if any(r.status == FAIL for r in sub):
        worst = FAIL
    elif any(r.status == DEGRADED for r in sub):
        worst = DEGRADED
    else:
        worst = PASS
    reasons = "; ".join(f"{r.name}={r.status}" for r in sub)
    return CheckResult(
        name="compatibility_supported",
        status=worst,
        reason=f"worst-of({reasons})",
    )
