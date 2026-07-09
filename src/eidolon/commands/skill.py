# SPDX-License-Identifier: Apache-2.0
"""`eidolon skill` subcommands: promote / demote / retire / status.

State is persisted in ``<eidolon_state_dir>/skill-state.json`` — a flat
mapping of skill name -> current state token (shadow|active|retired).

Exit codes (all verbs):
- 0  : PASS (action completed or criteria fully met)
- 1  : FAIL (criteria unmet, blocked)
- 2  : DEGRADED (fixtures/manifest missing; cannot evaluate)
- 64 : usage error (wrong verb or missing args)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

from eidolon.skills.lifecycle import (
    STATE_ACTIVE,
    STATE_RETIRED,
    STATE_SHADOW,
    SkillManifest,
    check_promotion_criteria,
    load_manifest,
)
from eidolon.util import events
from eidolon.util.paths import eidolon_state_dir

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_DEGRADED = 2
EXIT_USAGE = 64

_SOURCE = "commands.skill"


# ---------------------------------------------------------------------------
# State store helpers (flat JSON, append-safe enough for operator cadence)
# ---------------------------------------------------------------------------


def _state_path() -> Path:
    return eidolon_state_dir() / "skill-state.json"


def _load_state() -> dict:
    p = _state_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(state: dict) -> None:
    p = _state_path()
    p.write_text(json.dumps(state, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _current_state(name: str) -> str:
    """Return current lifecycle state for skill, defaulting to shadow."""
    return _load_state().get(name, STATE_SHADOW)


# ---------------------------------------------------------------------------
# Verb implementations
# ---------------------------------------------------------------------------


def _do_status(
    name: str,
    *,
    json_out: bool = False,
) -> int:
    """Print current lifecycle state + last shadow eval score (if recorded)."""
    state = _load_state()
    current = state.get(name, STATE_SHADOW)
    score = state.get(f"{name}.__last_score", None)

    if json_out:
        payload = {"skill": name, "state": current}
        if score is not None:
            payload["last_score"] = score
        json.dump(payload, sys.stdout, sort_keys=True)
        sys.stdout.write("\n")
    else:
        score_str = f"  last_score={score:.4f}" if isinstance(score, float) else ""
        print(f"skill {name!r}: {current}{score_str}")

    events.emit(
        f"skill.status.{name}",
        events.STATUS_INFO,
        source=_SOURCE,
        skill=name,
        state=current,
    )
    return EXIT_OK


def _do_promote(
    name: str,
    *,
    manifest_path: Optional[Path],
    fixtures_dir: Optional[Path],
    json_out: bool = False,
) -> int:
    """Run shadow eval + promotion criteria; transition shadow -> active on PASS."""
    # Resolve manifest
    if manifest_path is None:
        manifest_path = eidolon_state_dir() / "skills" / name / "manifest.yml"

    try:
        manifest = load_manifest(manifest_path)
    except FileNotFoundError:
        _emit_and_print(
            name,
            "promote",
            EXIT_DEGRADED,
            f"manifest_missing:{manifest_path}",
            json_out,
        )
        return EXIT_DEGRADED
    except ValueError as exc:
        _emit_and_print(name, "promote", EXIT_FAIL, f"manifest_invalid:{exc}", json_out)
        return EXIT_FAIL

    # Current state guard
    current = _current_state(name)
    if current == STATE_ACTIVE:
        _emit_and_print(name, "promote", EXIT_OK, "already_active", json_out)
        return EXIT_OK
    if current == STATE_RETIRED:
        _emit_and_print(
            name,
            "promote",
            EXIT_FAIL,
            "cannot_promote_retired_skill:use_retire_then_readd",
            json_out,
        )
        return EXIT_FAIL

    # Shadow eval
    if fixtures_dir is None:
        fixtures_dir = eidolon_state_dir() / "fixtures"

    try:
        from eidolon.skills.shadow import ShadowEvaluator
    except ImportError as exc:
        _emit_and_print(
            name, "promote", EXIT_DEGRADED, f"shadow_eval_import_error:{exc}", json_out
        )
        return EXIT_DEGRADED

    evaluator = ShadowEvaluator(threshold=manifest.regression_suite_pass_rate)
    result = evaluator.evaluate(name, fixtures_dir)

    if result.status == "DEGRADED":
        _emit_and_print(
            name, "promote", EXIT_DEGRADED, f"shadow_eval_degraded:{result.reason}", json_out
        )
        return EXIT_DEGRADED

    # Promotion criteria check (passes shadow score as regression_pass_rate)
    shadow_sessions = _load_state().get(f"{name}.__shadow_sessions", 0)
    # bandit posterior stored by learn loop; default 0.0 if not yet tracked
    bandit_posterior = _load_state().get(f"{name}.__bandit_posterior", 0.0)

    pr = check_promotion_criteria(
        manifest,
        shadow_sessions=shadow_sessions,
        bandit_posterior=bandit_posterior,
        regression_pass_rate=result.score if result.score >= 0.0 else 0.0,
    )

    if not pr.eligible:
        _emit_and_print(name, "promote", EXIT_FAIL, pr.reason, json_out)
        return EXIT_FAIL

    # Commit promotion
    state = _load_state()
    state[name] = STATE_ACTIVE
    state[f"{name}.__last_score"] = result.score
    _save_state(state)

    _emit_and_print(
        name,
        "promote",
        EXIT_OK,
        f"promoted_to_active:score={result.score:.4f}",
        json_out,
        from_state=STATE_SHADOW,
        to_state=STATE_ACTIVE,
    )
    return EXIT_OK


def _do_demote(
    name: str,
    *,
    json_out: bool = False,
) -> int:
    """Transition active -> shadow."""
    current = _current_state(name)
    if current == STATE_RETIRED:
        _emit_and_print(
            name, "demote", EXIT_FAIL, "cannot_demote_retired_skill", json_out
        )
        return EXIT_FAIL
    if current == STATE_SHADOW:
        _emit_and_print(name, "demote", EXIT_OK, "already_shadow", json_out)
        return EXIT_OK

    state = _load_state()
    state[name] = STATE_SHADOW
    _save_state(state)
    _emit_and_print(
        name,
        "demote",
        EXIT_OK,
        "demoted_to_shadow",
        json_out,
        from_state=STATE_ACTIVE,
        to_state=STATE_SHADOW,
    )
    return EXIT_OK


def _do_retire(
    name: str,
    *,
    json_out: bool = False,
) -> int:
    """Transition any state -> retired."""
    current = _current_state(name)
    if current == STATE_RETIRED:
        _emit_and_print(name, "retire", EXIT_OK, "already_retired", json_out)
        return EXIT_OK

    state = _load_state()
    prev = state.get(name, STATE_SHADOW)
    state[name] = STATE_RETIRED
    _save_state(state)
    _emit_and_print(
        name,
        "retire",
        EXIT_OK,
        "retired",
        json_out,
        from_state=prev,
        to_state=STATE_RETIRED,
    )
    return EXIT_OK


# ---------------------------------------------------------------------------
# Output helper
# ---------------------------------------------------------------------------


def _emit_and_print(
    name: str,
    verb: str,
    exit_code: int,
    reason: str,
    json_out: bool,
    **extra,
) -> None:
    status_map = {EXIT_OK: events.STATUS_PASS, EXIT_FAIL: events.STATUS_FAIL, EXIT_DEGRADED: events.STATUS_DEGRADED}
    ev_status = status_map.get(exit_code, events.STATUS_INFO)

    events.emit(
        f"skill.{verb}.{name}",
        ev_status,
        source=_SOURCE,
        skill=name,
        reason=reason,
        **extra,
    )

    if json_out:
        payload = {"skill": name, "verb": verb, "status": ev_status, "reason": reason}
        payload.update(extra)
        json.dump(payload, sys.stdout, sort_keys=True)
        sys.stdout.write("\n")
    else:
        glyph = {EXIT_OK: "✓", EXIT_FAIL: "✗", EXIT_DEGRADED: "!"}.get(exit_code, "?")
        print(f"  {glyph} skill {verb} {name!r}: {reason}")


# ---------------------------------------------------------------------------
# Public run() entry — called by cli.py
# ---------------------------------------------------------------------------


def run(
    verb: str,
    name: str,
    *,
    manifest: Optional[str] = None,
    fixtures: Optional[str] = None,
    json_out: bool = False,
) -> int:
    """Dispatch to the correct verb handler.

    Parameters
    ----------
    verb:     one of promote | demote | retire | status
    name:     skill name as it appears in manifest.yml
    manifest: optional path override for manifest.yml
    fixtures: optional path override for fixtures dir
    json_out: emit machine-readable JSON instead of human text
    """
    if not name or not name.strip():
        print("skill: NAME is required", file=sys.stderr)
        return EXIT_USAGE

    manifest_path = Path(manifest).expanduser().resolve() if manifest else None
    fixtures_dir = Path(fixtures).expanduser().resolve() if fixtures else None

    if verb == "status":
        return _do_status(name, json_out=json_out)
    if verb == "promote":
        return _do_promote(
            name, manifest_path=manifest_path, fixtures_dir=fixtures_dir, json_out=json_out
        )
    if verb == "demote":
        return _do_demote(name, json_out=json_out)
    if verb == "retire":
        return _do_retire(name, json_out=json_out)

    print(f"skill: unknown verb {verb!r}", file=sys.stderr)
    return EXIT_USAGE
