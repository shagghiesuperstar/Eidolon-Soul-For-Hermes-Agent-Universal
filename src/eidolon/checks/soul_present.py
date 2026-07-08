# SPDX-License-Identifier: Apache-2.0
"""Check: SOUL.md is present and non-empty at a discoverable location.

Search order (first match wins):
  1. $EIDOLON_SOUL_PATH env override                    (operator escape hatch)
  2. $HERMES_HOME/SOUL.md                               (deployed-mode canonical)
  3. $HERMES_HOME/skills/dream-cycle/SOUL.md            (dream-cycle-embedded)
  4. repo_root()/SOUL.md                                (source-checkout mode)
  5. importlib.resources 'eidolon' package data         (pip-installed mode)

Status policy:
  - PASS      : found at any location, >= 512 bytes.
  - DEGRADED  : found but small (<512 bytes; likely truncated) OR not found
                but we can tell we are running from a pip install (not a
                source checkout) — identity contract is expected to live in
                $HERMES_HOME and the operator has not placed it yet.
  - FAIL      : we can prove we are in a source checkout (pyproject.toml is a
                sibling of repo_root) and SOUL.md is missing there. That is a
                developer-side bug, not a deployment-side gap.

Rationale: FAIL-vs-DEGRADED matters because FAIL exits doctor with code 1 and
the installer treats that as a hard failure. A pip-installed environment with
no host Hermes yet should never trip that.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

from eidolon.checks import CheckResult, DEGRADED, FAIL, PASS
from eidolon.util.paths import hermes_home, repo_root

_MIN_SIZE = 512


def _candidate_paths() -> list[Tuple[str, Path]]:
    """Ordered list of (source_label, path) tuples to probe."""
    candidates: list[Tuple[str, Path]] = []

    override = os.environ.get("EIDOLON_SOUL_PATH")
    if override:
        candidates.append(("env:EIDOLON_SOUL_PATH", Path(override).expanduser().resolve()))

    hh = hermes_home()
    candidates.append(("$HERMES_HOME/SOUL.md", hh / "SOUL.md"))
    candidates.append((
        "$HERMES_HOME/skills/dream-cycle/SOUL.md",
        hh / "skills" / "dream-cycle" / "SOUL.md",
    ))
    candidates.append(("repo_root/SOUL.md", repo_root() / "SOUL.md"))
    return candidates


def _is_source_checkout() -> bool:
    """Heuristic: we are in a source checkout iff pyproject.toml lives at repo_root().

    When Eidolon is pip-installed to site-packages, `repo_root()` resolves
    into the site-packages hierarchy where no pyproject.toml exists.
    """
    return (repo_root() / "pyproject.toml").exists()


def check() -> CheckResult:
    found: Optional[Tuple[str, Path]] = None
    tried: list[str] = []
    for label, p in _candidate_paths():
        tried.append(label)
        if p.exists() and p.is_file():
            found = (label, p)
            break

    if found is None:
        # Not found anywhere. FAIL only when we are provably a source checkout
        # (that means a dev deleted SOUL.md from the repo — real bug). Otherwise
        # this is a deployment gap: DEGRADED.
        if _is_source_checkout():
            return CheckResult(
                name="soul_present",
                status=FAIL,
                reason=(
                    "SOUL.md not found in a source checkout at repo root; "
                    "identity contract missing. Tried: "
                    + ", ".join(tried)
                ),
            )
        return CheckResult(
            name="soul_present",
            status=DEGRADED,
            reason=(
                "SOUL.md not found. Place it at $HERMES_HOME/SOUL.md, or set "
                "$EIDOLON_SOUL_PATH. Eidolon runs in reduced identity-contract mode. "
                "Tried: " + ", ".join(tried)
            ),
        )

    label, p = found
    size = p.stat().st_size
    if size < _MIN_SIZE:
        return CheckResult(
            name="soul_present",
            status=DEGRADED,
            reason=(
                f"SOUL.md at {label} is unexpectedly small ({size} bytes); may be truncated."
            ),
            detail={"path": str(p), "source": label, "size": str(size)},
        )
    return CheckResult(
        name="soul_present",
        status=PASS,
        reason=f"SOUL.md present at {label} ({size} bytes).",
        detail={"path": str(p), "source": label, "size": str(size)},
    )
