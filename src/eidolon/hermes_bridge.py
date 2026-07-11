# SPDX-License-Identifier: Apache-2.0
"""Write Eidolon lessons into surfaces Hermes Agent actually loads.

Without this module, Eidolon only writes private ledgers Hermes never reads.
That is zero value to the human. This bridge is the product.

Hermes loads ``$HERMES_HOME/memories/MEMORY.md`` into every session (within
``memory.memory_char_limit``). We maintain a bounded section there:

    §
    EIDOLON LEARNED:
    - <short lesson>
    §

Rules:
- Never touch SOUL.md or config.yaml.
- Bounded: max_lines lessons, max section ~900 chars, oldest dropped.
- Idempotent: identical lesson text is not duplicated.
- Loud: returns a result dict; never silent on failure.
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


SECTION_HEADER = "EIDOLON LEARNED:"
SECTION_START = "§\nEIDOLON LEARNED:\n"
SECTION_END = "\n§"
MAX_LESSONS = 12
MAX_SECTION_CHARS = 900
MAX_LESSON_CHARS = 180


def hermes_memory_path(hermes_home: Optional[Path] = None) -> Path:
    home = hermes_home or Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    # Prefer memories/MEMORY.md (Hermes profile memory store)
    candidates = [
        home / "memories" / "MEMORY.md",
        home / "MEMORY.md",
    ]
    for c in candidates:
        if c.exists():
            return c
    # Default create under memories/
    target = candidates[0]
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text("", encoding="utf-8")
    return target


def _normalize_lesson(text: str) -> str:
    t = " ".join((text or "").split())
    t = t.strip()
    if t.lower().startswith("improve handling of"):
        # Strip worthless template proposals — do not pollute Hermes memory
        return ""
    if len(t) > MAX_LESSON_CHARS:
        t = t[: MAX_LESSON_CHARS - 1].rstrip() + "…"
    return t


def _parse_section(body: str) -> List[str]:
    """Return list of lesson lines (without leading '- ')."""
    lines = []
    for raw in body.splitlines():
        s = raw.strip()
        if s.startswith("- "):
            lines.append(s[2:].strip())
        elif s and not s.startswith("EIDOLON"):
            lines.append(s)
    return lines


def _render_section(lessons: List[str]) -> str:
    body = "\n".join(f"- {x}" for x in lessons if x)
    block = f"§\n{SECTION_HEADER}\n{body}\n§"
    # trim from oldest if too large
    while len(block) > MAX_SECTION_CHARS and len(lessons) > 1:
        lessons = lessons[1:]
        body = "\n".join(f"- {x}" for x in lessons)
        block = f"§\n{SECTION_HEADER}\n{body}\n§"
    return block


def promote_lesson_to_hermes(
    lesson_text: str,
    *,
    hermes_home: Optional[Path] = None,
    source_id: str = "",
) -> Dict[str, Any]:
    """Append a lesson into Hermes MEMORY.md. Returns status dict."""
    text = _normalize_lesson(lesson_text)
    if not text:
        return {
            "status": "skipped",
            "reason": "empty_or_template_proposal",
            "source_id": source_id,
        }

    path = hermes_memory_path(hermes_home)
    try:
        original = path.read_text(encoding="utf-8") if path.exists() else ""
    except OSError as exc:
        return {"status": "fail", "reason": f"read:{exc}", "source_id": source_id}

    # Extract existing EIDOLON LEARNED section if present
    pattern = re.compile(
        r"§\s*\nEIDOLON LEARNED:\n(.*?)(?:\n§|$)",
        re.DOTALL | re.IGNORECASE,
    )
    m = pattern.search(original)
    if m:
        lessons = _parse_section(m.group(1))
        rest = original[: m.start()] + original[m.end() :]
    else:
        lessons = []
        rest = original

    # Dedup
    if any(text == L or text in L or L in text for L in lessons):
        return {
            "status": "skipped",
            "reason": "duplicate",
            "path": str(path),
            "source_id": source_id,
            "lessons": len(lessons),
        }

    lessons.append(text)
    if len(lessons) > MAX_LESSONS:
        lessons = lessons[-MAX_LESSONS:]

    section = _render_section(lessons)
    # Place section at end of MEMORY.md
    new_body = rest.rstrip() + "\n" + section + "\n"
    try:
        path.write_text(new_body, encoding="utf-8")
    except OSError as exc:
        return {"status": "fail", "reason": f"write:{exc}", "source_id": source_id}

    return {
        "status": "ok",
        "path": str(path),
        "source_id": source_id,
        "lessons": len(lessons),
        "wrote": text,
        "ts": time.time(),
    }


__all__ = ["promote_lesson_to_hermes", "hermes_memory_path", "SECTION_HEADER"]
