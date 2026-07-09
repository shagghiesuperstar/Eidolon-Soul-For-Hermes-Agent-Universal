# SPDX-License-Identifier: Apache-2.0
"""Skill lifecycle state machine: promote / demote / retire (REC-017).

State transitions
-----------------
    shadow  ->  active   (promote)  — all manifest criteria met
    active  ->  shadow   (demote)   — bandit posterior drops below threshold
    active  ->  retired  (retire)   — explicit operator action
    shadow  ->  retired  (retire)   — explicit operator action

Manifest format (YAML-like, parsed stdlib-only)
-----------------------------------------------
A ``manifest.yml`` file alongside a skill declares its promotion criteria::

    name: my-skill
    version: 1.0.0
    promotion:
      min_shadow_sessions: 20
      min_bandit_posterior: 0.65
      regression_suite_pass_rate: 0.95

Rules
-----
- Promotion is a CLI action, NOT automatic.  This module enforces criteria;
  it does NOT apply changes to Hermes skill files.
- ``eidolon skill promote <name>`` calls ``check_promotion_criteria`` and
  fails loudly if any criterion is unmet.
- The state machine never touches SOUL.md, .hermes/config.yaml, or any file
  in NEVER_TOUCH_PATHS.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional

# --- Defaults (per REC-017 manifest spec) ----------------------------------

DEFAULT_MIN_SHADOW_SESSIONS: int = 20
DEFAULT_MIN_BANDIT_POSTERIOR: float = 0.65
DEFAULT_REGRESSION_PASS_RATE: float = 0.95

# Skill state tokens.
STATE_SHADOW = "shadow"
STATE_ACTIVE = "active"
STATE_RETIRED = "retired"


@dataclass
class SkillManifest:
    """Parsed representation of a skill's manifest.yml."""

    name: str
    version: str
    min_shadow_sessions: int
    min_bandit_posterior: float
    regression_suite_pass_rate: float


@dataclass
class PromotionResult:
    """Outcome of a promotion eligibility check."""

    eligible: bool
    reason: str
    unmet: list  # list[str] of unmet criterion descriptions


def _parse_manifest(text: str) -> Dict[str, Any]:
    """Minimal stdlib YAML parser for the fixed manifest schema.

    Only handles the two-level structure used by skill manifests.  Does NOT
    support anchors, multi-line values, lists, or any YAML feature beyond
    scalar key: value and one level of indented block mapping.
    """
    result: Dict[str, Any] = {}
    current_key: Optional[str] = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)', stripped)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if indent == 0:
            if val:
                result[key] = val
            else:
                result[key] = {}
                current_key = key
        else:
            if current_key and isinstance(result.get(current_key), dict):
                if val:
                    result[current_key][key] = val
    return result


def load_manifest(manifest_path: Path) -> SkillManifest:
    """Load and validate a skill manifest.yml.

    Raises
    ------
    FileNotFoundError: manifest_path does not exist.
    ValueError: manifest is missing required fields or has invalid values.
    """
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")
    raw = _parse_manifest(manifest_path.read_text(encoding="utf-8"))
    name = raw.get("name")
    version = raw.get("version")
    if not name or not version:
        raise ValueError("manifest must have 'name' and 'version' fields")
    promo = raw.get("promotion", {})
    if not isinstance(promo, dict):
        promo = {}
    try:
        min_shadow = int(promo.get("min_shadow_sessions", DEFAULT_MIN_SHADOW_SESSIONS))
        min_posterior = float(promo.get("min_bandit_posterior", DEFAULT_MIN_BANDIT_POSTERIOR))
        min_pass_rate = float(promo.get("regression_suite_pass_rate", DEFAULT_REGRESSION_PASS_RATE))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"manifest promotion field invalid: {exc}") from exc
    return SkillManifest(
        name=str(name),
        version=str(version),
        min_shadow_sessions=min_shadow,
        min_bandit_posterior=min_posterior,
        regression_suite_pass_rate=min_pass_rate,
    )


def check_promotion_criteria(
    manifest: SkillManifest,
    *,
    shadow_sessions: int,
    bandit_posterior: float,
    regression_pass_rate: float,
) -> PromotionResult:
    """Evaluate whether a skill meets all promotion criteria.

    Parameters
    ----------
    manifest:             loaded SkillManifest for the candidate skill.
    shadow_sessions:      number of shadow sessions completed.
    bandit_posterior:     current bandit posterior mean for this arm.
    regression_pass_rate: current regression suite pass rate for this arm.

    Returns
    -------
    PromotionResult with ``eligible=True`` only if ALL criteria are met.
    A skill that regresses on the eval suite (low regression_pass_rate) MUST
    NOT be promoted even if its bandit posterior is high (adversarial invariant).
    """
    unmet = []

    if shadow_sessions < manifest.min_shadow_sessions:
        unmet.append(
            f"shadow_sessions {shadow_sessions} < required {manifest.min_shadow_sessions}"
        )
    if bandit_posterior < manifest.min_bandit_posterior:
        unmet.append(
            f"bandit_posterior {bandit_posterior:.4f} < required {manifest.min_bandit_posterior:.4f}"
        )
    if regression_pass_rate < manifest.regression_suite_pass_rate:
        unmet.append(
            f"regression_pass_rate {regression_pass_rate:.4f} < required "
            f"{manifest.regression_suite_pass_rate:.4f}"
        )

    if unmet:
        return PromotionResult(
            eligible=False,
            reason="promotion_criteria_unmet:" + ";".join(unmet),
            unmet=unmet,
        )
    return PromotionResult(
        eligible=True,
        reason=f"all criteria met for {manifest.name}@{manifest.version}",
        unmet=[],
    )
