# SPDX-License-Identifier: Apache-2.0
"""Rule-based risk classifier — pure function surface (REC-010).

`classify_action(target_path, mutation_kind, safety_flags)` is the ergonomic
callsite for `dream-cycle` and future skills. It builds the action dict and
forwards to `safety.risk.classify` so both callsites share one truth.

Regex-first path matching is done by `safety.risk.is_never_touch`, which is
what enforces the NEVER_TOUCH ceiling regardless of other flags.
"""

from __future__ import annotations

from typing import Iterable

from eidolon.safety.risk import RiskClass, classify


def classify_action(
    target_path: str,
    mutation_kind: str,
    safety_flags: Iterable[str] = (),
) -> RiskClass:
    """Ergonomic classifier for callers. PURE; no I/O; no time; no randomness."""
    return classify(
        {
            "target": target_path,
            "mutation_kind": mutation_kind,
            "safety_flags": tuple(safety_flags),
        }
    )


__all__ = ["classify_action", "RiskClass"]
