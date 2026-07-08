# SPDX-License-Identifier: Apache-2.0
"""Doctor check framework.

Every check is a callable returning a CheckResult. Checks must:
- Be read-only (no filesystem mutations, no network writes).
- Return DEGRADED (not FAIL) when a component is missing but Eidolon can still
  operate in reduced mode. FAIL is reserved for conditions that block core CLI
  operation.
- Complete in under 2 seconds. Network probes get a hard 3s timeout.
- Never raise; wrap unexpected exceptions in a FAIL result with the exception
  class name as the reason.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Callable, Dict, List

PASS = "PASS"
DEGRADED = "DEGRADED"
FAIL = "FAIL"


@dataclass
class CheckResult:
    name: str
    status: str
    reason: str
    detail: Dict[str, str] | None = None

    def as_dict(self) -> Dict[str, object]:
        d = asdict(self)
        if self.detail is None:
            d.pop("detail")
        return d


CheckFn = Callable[[], CheckResult]


def safe(fn: CheckFn) -> CheckFn:
    """Wrap a check so exceptions surface as FAIL rather than crashing doctor."""

    def wrapper() -> CheckResult:
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - by design, wrap anything
            return CheckResult(
                name=getattr(fn, "__name__", "unknown"),
                status=FAIL,
                reason=f"check_raised:{type(exc).__name__}",
            )

    wrapper.__name__ = getattr(fn, "__name__", "wrapped_check")
    return wrapper


def registry() -> List[CheckFn]:
    """Return the ordered list of checks doctor runs.

    Import-locally so a broken check module doesn't tank the whole CLI.
    """
    from eidolon.checks import (
        hermes_config,
        hermes_version,
        hooks_wired,
        provider_capability,
        soul_present,
        state_dir,
    )

    return [
        safe(soul_present.check),
        safe(hermes_config.check),
        safe(hermes_version.check),
        safe(state_dir.check),
        safe(hooks_wired.check),
        safe(provider_capability.check),
    ]
