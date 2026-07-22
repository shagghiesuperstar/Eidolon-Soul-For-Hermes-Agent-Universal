# SPDX-License-Identifier: Apache-2.0
"""5-class risk enum + NEVER_TOUCH_PATHS registry (REC-010).

Ordinal from safest to most dangerous:
    NO_OP < LOW < MEDIUM < HIGH < NEVER_TOUCH

Semantics:
- NO_OP       — action is a formal no-op; safe to skip entirely.
- LOW         — safe to auto-apply. dream-cycle applies these without shadow eval.
- MEDIUM      — requires shadow evaluation (REC-017). Until REC-017 lands,
                MEDIUM proposals are logged DEGRADED and NOT applied.
- HIGH        — never auto-apply. Requires explicit approval via review. Handler emits FAIL
                and writes an audit log entry.
- NEVER_TOUCH — the classifier's ceiling. Any target matching a pattern in
                NEVER_TOUCH_PATHS is NEVER_TOUCH regardless of other flags.

NEVER_TOUCH_PATHS invariants (§ 0.3 of the roadmap):
- SOUL.md
- config.yaml top-level keys
- last_known_good/ tree
- LICENSE and NOTICE files
- adversarial.yml (the guarantees CI file)

Editing rules:
- ADDING a NEVER_TOUCH_PATHS entry is a one-line change; no REC required.
- REMOVING an entry is a safety loosening; REQUIRES a REC.

The classifier is PURE: no I/O, no time, no randomness. Impurity is a bug.
"""

from __future__ import annotations

import re
from enum import IntEnum
from typing import Any, Dict, Iterable, Tuple


class RiskClass(IntEnum):
    """Ordinal risk class. Comparison follows the numeric ordering above."""

    NO_OP = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    NEVER_TOUCH = 4

    def is_auto_applyable(self) -> bool:
        """Only LOW auto-applies. Everything else routes through gates."""
        return self is RiskClass.LOW


# --- NEVER_TOUCH_PATHS ---------------------------------------------------
# Each entry is a regex string; matched against a normalised action target.
# Adding an entry: append one line here. Do not remove without a REC.
NEVER_TOUCH_PATHS: Tuple[str, ...] = (
    r"(?:^|/)SOUL\.md$",                              # canonical soul spec
    r"(?:^|/)LICENSE(?:\.[a-zA-Z0-9]+)?$",            # LICENSE, LICENSE.md, LICENSE.txt
    r"(?:^|/)NOTICE(?:\.[a-zA-Z0-9]+)?$",             # NOTICE and variants
    r"(?:^|/)\.hermes/config\.yaml$",                 # host Hermes config
    r"(?:^|/)config\.yaml$",                          # local config.yaml
    r"(?:^|/)last_known_good(?:/|$)",                 # LKG snapshots
    r"(?:^|/)\.github/workflows/adversarial\.yml$",   # guarantees CI
    r"(?:^|/)adversarial\.yml$",                      # bare adversarial spec
)


_NEVER_TOUCH_RE = re.compile("|".join(f"(?:{p})" for p in NEVER_TOUCH_PATHS))


# Mutation kinds that are safe to auto-apply. ``skill_update`` is staging-only;
# the Judgment Brain writes under ``skills/_eidolon_staging`` and the Law of
# Done verifies that write before counting the proposal as applied.
_MUTATION_LOW = frozenset(
    {"docs_only", "typo_fix", "test_only", "comment_only", "preference_update", "skill_update"}
)
_MUTATION_MEDIUM = frozenset({"prompt_phrasing", "log_verbosity", "config_field_add"})
_MUTATION_HIGH = frozenset({"skill_code", "config_field_rewrite", "handler_signature"})
_MUTATION_NO_OP = frozenset({"no_op", "identity", ""})


def _normalise_target(target: str) -> str:
    """Normalise a target path for matching: forward slashes, no leading ./."""
    t = target.strip().replace("\\", "/")
    if t.startswith("./"):
        t = t[2:]
    return t


def is_never_touch(target: str) -> bool:
    """True iff `target` matches ANY NEVER_TOUCH pattern (regex)."""
    if not target:
        return False
    return _NEVER_TOUCH_RE.search(_normalise_target(target)) is not None


def classify(action: Dict[str, Any]) -> RiskClass:
    """Classify an action dict. PURE: no I/O, no side effects.

    Recognised keys (all optional; missing keys default to conservative):
      target        : str  — the file path or symbolic target being mutated
      mutation_kind : str  — one of the mutation-kind buckets defined above
      safety_flags  : iterable[str] — orthogonal signals (currently unused;
                                       reserved for future risk factors)

    Precedence (top wins):
      1. target matches NEVER_TOUCH_PATHS -> NEVER_TOUCH
      2. mutation_kind in _MUTATION_HIGH  -> HIGH
      3. mutation_kind in _MUTATION_MEDIUM-> MEDIUM
      4. mutation_kind in _MUTATION_LOW   -> LOW
      5. mutation_kind in _MUTATION_NO_OP -> NO_OP
      6. anything else (unknown target/kind) -> HIGH (fail-closed default)
    """
    target = str(action.get("target", ""))
    mutation_kind = str(action.get("mutation_kind", ""))

    if is_never_touch(target):
        return RiskClass.NEVER_TOUCH

    if mutation_kind in _MUTATION_HIGH:
        return RiskClass.HIGH
    if mutation_kind in _MUTATION_MEDIUM:
        return RiskClass.MEDIUM
    if mutation_kind in _MUTATION_LOW:
        return RiskClass.LOW
    if mutation_kind in _MUTATION_NO_OP:
        return RiskClass.NO_OP

    # Fail-closed: unknown -> HIGH, never LOW.
    return RiskClass.HIGH


def never_touch_patterns() -> Iterable[str]:
    """Return the frozen tuple of NEVER_TOUCH patterns (for introspection)."""
    return NEVER_TOUCH_PATHS
