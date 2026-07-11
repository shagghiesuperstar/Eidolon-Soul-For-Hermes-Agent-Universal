# SPDX-License-Identifier: Apache-2.0
"""Execute a classified judgment action against Hermes Agent files on disk.

Each ActionKind maps to a concrete file write:

    SOUL_EDICT    → appends to $HERMES_HOME/SOUL.md  "EIDOLON EDICTS" section
                    (append-only, never rewrites invariants above the marker)
                    Auto-creates the marker if absent — works on any SOUL.md
                    including a brand-new Hermes install with no prior config.
    SKILL_UPDATE  → appends lesson to
                    $HERMES_HOME/skills/_eidolon_staging/eidolon-learned.md
                    (staging only — never live skills/; creates file + header)
    CONFIG_TUNE   → appends to $HERMES_HOME/memories/eidolon-prefs.md
                    (Hermes loads all .md files in memories/)
    MEMORY_RETIRE → removes matching lesson line from MEMORY.md
                    (lesson is baked into a real file; MEMORY.md line is noise)
    MEMORY_RETAIN → no-op; lesson stays in MEMORY.md

All writes are atomic (write-tmp + os.replace). Never touches SOUL.md
invariants above the EIDOLON EDICTS marker. Exit: result dict always returned.
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .classifier import ActionKind


# ---------------------------------------------------------------------------
# File-location helpers
# ---------------------------------------------------------------------------

def _hermes_home(hermes_home: Optional[Path] = None) -> Path:
    return hermes_home or Path(
        os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))
    )


def _soul_path(hermes_home: Optional[Path]) -> Path:
    return _hermes_home(hermes_home) / "SOUL.md"


def _skill_path(hermes_home: Optional[Path]) -> Path:
    """Staging playbook path — never write live skills outside _eidolon_staging."""
    p = (
        _hermes_home(hermes_home)
        / "skills"
        / "_eidolon_staging"
        / "eidolon-learned.md"
    )
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _prefs_path(hermes_home: Optional[Path]) -> Path:
    p = _hermes_home(hermes_home) / "memories" / "eidolon-prefs.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _memory_path(hermes_home: Optional[Path]) -> Path:
    candidates = [
        _hermes_home(hermes_home) / "memories" / "MEMORY.md",
        _hermes_home(hermes_home) / "MEMORY.md",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


# ---------------------------------------------------------------------------
# SOUL_EDICT
# ---------------------------------------------------------------------------

_EDICT_HEADER = "## EIDOLON EDICTS (auto-learned; never edit above this line)"
_EDICT_MARKER = "EIDOLON EDICTS"


def _write_soul_edict(lesson: str, path: Path) -> Dict[str, Any]:
    """Append lesson to the EIDOLON EDICTS section of SOUL.md.

    Safety contract:
    - Only appends *below* the EIDOLON EDICTS marker.
    - If the marker does not exist, it is appended at the very end of whatever
      SOUL.md the user already has — preserving every line above unchanged.
    - If SOUL.md does not exist at all, it is created with just the header +
      the new edict. This covers a brand-new Hermes install.
    - Never rewrites or deletes any content above the marker.
    """
    try:
        body = path.read_text(encoding="utf-8") if path.exists() else ""
    except OSError as exc:
        return {"status": "fail", "reason": f"soul_read:{exc}"}

    # Dedup
    if lesson in body:
        return {"status": "skip", "reason": "duplicate_soul_edict"}

    if _EDICT_MARKER not in body:
        body = body.rstrip() + f"\n\n{_EDICT_HEADER}\n"

    new_line = f"- {lesson}"
    idx = body.index(_EDICT_MARKER)
    eol = body.find("\n", idx)
    if eol == -1:
        eol = len(body)
    body = body[: eol + 1] + new_line + "\n" + body[eol + 1 :]

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(path, body)
    except OSError as exc:
        return {"status": "fail", "reason": f"soul_write:{exc}"}

    return {"status": "ok", "file": str(path), "wrote": new_line}


# ---------------------------------------------------------------------------
# SKILL_UPDATE
# ---------------------------------------------------------------------------

_SKILL_HEADER = (
    "# Eidolon Learned Skills\n\n"
    "These skill notes are auto-maintained by Eidolon's Judgment Brain.\n"
    "Do not edit manually — lessons graduate here from MEMORY.md.\n"
)


def _write_skill_update(lesson: str, path: Path) -> Dict[str, Any]:
    try:
        body = path.read_text(encoding="utf-8") if path.exists() else ""
    except OSError as exc:
        return {"status": "fail", "reason": f"skill_read:{exc}"}

    if not body:
        body = _SKILL_HEADER

    if lesson in body:
        return {"status": "skip", "reason": "duplicate_skill"}

    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    body = body.rstrip() + f"\n\n## {ts}\n- {lesson}\n"

    try:
        _atomic_write(path, body)
    except OSError as exc:
        return {"status": "fail", "reason": f"skill_write:{exc}"}

    return {"status": "ok", "file": str(path), "wrote": lesson}


# ---------------------------------------------------------------------------
# CONFIG_TUNE
# ---------------------------------------------------------------------------

_PREFS_HEADER = (
    "# Eidolon Learned Preferences\n\n"
    "Auto-maintained by Eidolon Judgment Brain. Hermes loads all .md in memories/.\n"
)


def _write_config_tune(lesson: str, path: Path) -> Dict[str, Any]:
    try:
        body = path.read_text(encoding="utf-8") if path.exists() else ""
    except OSError as exc:
        return {"status": "fail", "reason": f"prefs_read:{exc}"}

    if not body:
        body = _PREFS_HEADER

    if lesson in body:
        return {"status": "skip", "reason": "duplicate_pref"}

    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    body = body.rstrip() + f"\n- [{ts}] {lesson}\n"

    try:
        _atomic_write(path, body)
    except OSError as exc:
        return {"status": "fail", "reason": f"prefs_write:{exc}"}

    return {"status": "ok", "file": str(path), "wrote": lesson}


# ---------------------------------------------------------------------------
# MEMORY_RETIRE
# ---------------------------------------------------------------------------

def _retire_memory_line(lesson: str, path: Path) -> Dict[str, Any]:
    """Remove a lesson line from MEMORY.md once it is codified elsewhere."""
    if not path.exists():
        return {"status": "skip", "reason": "memory_file_absent"}

    try:
        body = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"status": "fail", "reason": f"memory_read:{exc}"}

    pattern = re.compile(
        r"^- " + re.escape(lesson[:60]) + r".*$",
        re.MULTILINE,
    )
    new_body, n = pattern.subn("", body)
    if n == 0:
        return {"status": "skip", "reason": "lesson_not_found_in_memory"}

    new_body = re.sub(r"\n{3,}", "\n\n", new_body)

    try:
        _atomic_write(path, new_body)
    except OSError as exc:
        return {"status": "fail", "reason": f"memory_write:{exc}"}

    return {"status": "ok", "file": str(path), "retired": lesson}


# ---------------------------------------------------------------------------
# Atomic write helper
# ---------------------------------------------------------------------------

def _atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute_judgment(
    kind: ActionKind,
    lesson: str,
    *,
    hermes_home: Optional[Path] = None,
) -> Dict[str, Any]:
    """Execute the action implied by kind for this lesson.

    Returns a result dict with 'status': 'ok' | 'skip' | 'fail'.
    Never raises.
    """
    try:
        if kind == ActionKind.SOUL_EDICT:
            return _write_soul_edict(lesson, _soul_path(hermes_home))

        if kind == ActionKind.SKILL_UPDATE:
            return _write_skill_update(lesson, _skill_path(hermes_home))

        if kind == ActionKind.CONFIG_TUNE:
            return _write_config_tune(lesson, _prefs_path(hermes_home))

        if kind == ActionKind.MEMORY_RETIRE:
            return _retire_memory_line(lesson, _memory_path(hermes_home))

        # MEMORY_RETAIN — intentional no-op
        return {"status": "skip", "reason": "memory_retain_noop"}

    except Exception as exc:  # pylint: disable=broad-except
        return {"status": "fail", "reason": f"unexpected:{exc}"}


__all__ = ["execute_judgment"]
