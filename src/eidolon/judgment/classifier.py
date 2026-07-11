# SPDX-License-Identifier: Apache-2.0
"""Rule-based lesson classifier — stdlib only, zero external dependencies.

Each lesson is classified into exactly one ActionKind based on keyword and
pattern matching. Rules are deterministic and testable; no LLM call is made.
This works universally across all Hermes memory plugin configurations.

Classification priority (first match wins):
    1. SOUL_EDICT    — lesson is a universal behavioural rule / invariant
    2. SKILL_UPDATE  — lesson targets a specific repeatable skill or tool
    3. CONFIG_TUNE   — lesson is a tuning/formatting/structure preference
    4. MEMORY_RETIRE — lesson is already codified; memory line can be removed
    5. MEMORY_RETAIN — default: keep in MEMORY.md, not yet actionable enough
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Tuple


class ActionKind(str, Enum):
    SOUL_EDICT    = "soul_edict"      # write to SOUL.md learned-edicts section
    SKILL_UPDATE  = "skill_update"    # append/create a skill file Hermes loads
    CONFIG_TUNE   = "config_tune"     # write to agent config / preferences
    MEMORY_RETIRE = "memory_retire"   # remove line from MEMORY.md (baked in)
    MEMORY_RETAIN = "memory_retain"   # keep in MEMORY.md; not yet actionable


# ---------------------------------------------------------------------------
# Signal sets — order matters: checked top-down, first hit wins
# ---------------------------------------------------------------------------

_SOUL_SIGNALS = [
    r"\bnever\b",
    r"\balways\b",
    r"\bmust\b.{0,40}\bnot\b",
    r"\bmust\b.{0,40}\bverify\b",
    r"\bnever invent\b",
    r"\bnever fabricate\b",
    r"\bnever assume\b",
    r"\bnever guess\b",
    r"\bdo not pretend\b",
    r"\binvariant\b",
    r"\boperating rule\b",
    r"\bcore principle\b",
    r"\bidentity\b.{0,30}\brule\b",
]

_SKILL_SIGNALS = [
    r"\bprobe\b",
    r"\bskill\b",
    r"\btool\b.{0,40}\buse\b",
    r"\bwhen.{0,60}\bcommand\b",
    r"\bwhen.{0,60}\bterminal\b",
    r"\brun the (real |actual )?command\b",
    r"\bpaste (evidence|output|result)\b",
    r"\bprobe (before|first|not assume)\b",
    r"\bverify.{0,40}\bbefore (acting|claiming|reporting)\b",
    r"\bdebugging pattern\b",
    r"\bworkflow\b",
    r"\bstep[- ]by[- ]step\b",
    r"\bprocedure\b",
    r"\bprotocol\b",
]

_CONFIG_SIGNALS = [
    r"\bformat\b",
    r"\bstructure\b.{0,30}(output|response|reply)\b",
    r"\bresponse (style|length|tone)\b",
    r"\boutput (style|format|length)\b",
    r"\bprefer.{0,50}(table|bullet|list|concis|brief|terse)\b",
    r"\balways (use|include|start|end).{0,40}(table|header|section)\b",
    r"\btemperature\b",
    r"\bmax.{0,10}token\b",
    r"\bconfig\b",
    r"\bsetting\b",
    r"\btuning\b",
    r"\boptimiz\b",
]

_RETIRE_SIGNALS = [
    r"\bimplemented\b",
    r"\bcodified\b",
    r"\bwired\b.{0,30}(in|into|up)\b",
    r"\bproven\b",
    r"\bverified\b.{0,30}(in|into|by)\b",
    r"\bno longer needed\b",
    r"\bbaked in\b",
    r"\bnow default\b",
]


def _matches(text: str, patterns: list) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in patterns)


def classify_lesson(lesson_text: str) -> Tuple[ActionKind, str]:
    """Classify a lesson into an ActionKind.

    Returns (kind, reason) where reason is a short human-readable string
    explaining which signal fired. Never raises; returns MEMORY_RETAIN on
    empty or unclassifiable input.
    """
    text = (lesson_text or "").strip()
    if not text:
        return ActionKind.MEMORY_RETAIN, "empty"

    if _matches(text, _RETIRE_SIGNALS):
        return ActionKind.MEMORY_RETIRE, "retire_signal"

    if _matches(text, _SOUL_SIGNALS):
        return ActionKind.SOUL_EDICT, "soul_signal"

    if _matches(text, _SKILL_SIGNALS):
        return ActionKind.SKILL_UPDATE, "skill_signal"

    if _matches(text, _CONFIG_SIGNALS):
        return ActionKind.CONFIG_TUNE, "config_signal"

    return ActionKind.MEMORY_RETAIN, "no_signal"


__all__ = ["ActionKind", "classify_lesson"]
