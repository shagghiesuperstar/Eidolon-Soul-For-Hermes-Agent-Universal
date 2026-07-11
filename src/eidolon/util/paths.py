# SPDX-License-Identifier: Apache-2.0
"""Path resolution for Eidolon state.

Rules:
- Never hardcode absolute paths; always resolve through pathlib.Path.home().
- Respect $HERMES_HOME and $EIDOLON_HOME overrides for tests + non-standard installs.
- Create directories on read to eliminate first-run TOCTOU races.
"""

from __future__ import annotations

import os
from pathlib import Path


def hermes_home() -> Path:
    """Root of the host Hermes installation's state tree.

    Precedence: $HERMES_HOME > ~/.hermes
    """
    override = os.environ.get("HERMES_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / ".hermes").resolve()


def eidolon_state_dir() -> Path:
    """Directory Eidolon owns exclusively for its own state.

    Precedence: $EIDOLON_STATE_DIR > $EIDOLON_HOME >
    $HERMES_HOME/state/eidolon > ~/.hermes/state/eidolon.

    ``EIDOLON_STATE_DIR`` is the explicit report/judgment isolation override;
    honoring it here keeps events and persistent judgment metrics in the same
    state tree instead of accidentally reading the live host event log.
    """
    override = os.environ.get("EIDOLON_STATE_DIR") or os.environ.get("EIDOLON_HOME")
    if override:
        p = Path(override).expanduser().resolve()
    else:
        p = hermes_home() / "state" / "eidolon"
    p.mkdir(parents=True, exist_ok=True)
    return p


def events_log() -> Path:
    return eidolon_state_dir() / "events.jsonl"


def report_state() -> Path:
    return eidolon_state_dir() / "report.json"


def last_known_good_dir() -> Path:
    d = eidolon_state_dir() / "last_known_good"
    d.mkdir(parents=True, exist_ok=True)
    return d


def audit_log() -> Path:
    return eidolon_state_dir() / "audit.jsonl"


def repo_root() -> Path:
    """Root of the Eidolon source checkout (three parents up from this file)."""
    return Path(__file__).resolve().parents[3]
