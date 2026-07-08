# SPDX-License-Identifier: Apache-2.0
"""Preference-pair logging (REC-009).

Schema-only. NO training happens here — REC-019 (DPO) consumes this file
once >=10k pairs accumulate.

Fields are STRUCTURAL. No prompt text. No response text. No operator
strings. Context is SHA256'd upstream by the caller; this module never
sees the input context.

Storage: `$EIDOLON_HOME/preferences.jsonl` — one JSON object per line,
append-only, UTF-8. Corrupt lines are skipped by `iter_pairs`, never
returned.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterator

from eidolon.util.paths import eidolon_state_dir


SCHEMA = 1

_VALID_SOURCES = frozenset({"bandit", "rollback", "operator_feedback"})


@dataclass
class PreferencePair:
    """One preference pair: chosen > rejected for a given context.

    Fields (frozen):
      schema        : int   — schema version (=1)
      ts            : float — epoch seconds when the pair was recorded
      pair_id       : str   — sha256(chosen|rejected|context)[:16], dedupable
      chosen_id     : str   — the arm/proposal id that was preferred
      rejected_id   : str   — the arm/proposal id that was NOT preferred
      context_hash  : str   — SHA256 hex of the context representation (already hashed by caller)
      source        : str   — one of {"bandit", "rollback", "operator_feedback"}
    """

    schema: int = SCHEMA
    ts: float = 0.0
    pair_id: str = ""
    chosen_id: str = ""
    rejected_id: str = ""
    context_hash: str = ""
    source: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def preferences_path() -> Path:
    return eidolon_state_dir() / "preferences.jsonl"


def _derive_pair_id(chosen_id: str, rejected_id: str, context_hash: str) -> str:
    return hashlib.sha256(
        f"{chosen_id}|{rejected_id}|{context_hash}".encode("utf-8")
    ).hexdigest()[:16]


def log_pair(
    chosen_id: str,
    rejected_id: str,
    source: str,
    context_hash: str,
    *,
    ts: float | None = None,
) -> PreferencePair:
    """Append one preference pair to the store. Returns the record written.

    Contract:
    - `chosen_id` and `rejected_id` must be non-empty and distinct.
    - `context_hash` must be a 64-hex-char SHA256 digest (validated).
      Callers are expected to hash context BEFORE calling this function;
      this module never accepts unhashed strings.
    - `source` must be a recognised source; unknown sources raise.
    """
    if not chosen_id or not rejected_id:
        raise ValueError("chosen_id and rejected_id must be non-empty")
    if chosen_id == rejected_id:
        raise ValueError(
            f"chosen_id == rejected_id ({chosen_id!r}); a pair must be strictly ordered"
        )
    if source not in _VALID_SOURCES:
        raise ValueError(
            f"unknown source {source!r}; expected one of {sorted(_VALID_SOURCES)}"
        )
    if not _is_sha256_hex(context_hash):
        raise ValueError(
            f"context_hash must be a 64-hex SHA256 digest; got {context_hash!r} "
            "(callers must hash upstream; this module accepts digests only)"
        )

    rec = PreferencePair(
        ts=time.time() if ts is None else ts,
        pair_id=_derive_pair_id(chosen_id, rejected_id, context_hash),
        chosen_id=chosen_id,
        rejected_id=rejected_id,
        context_hash=context_hash,
        source=source,
    )
    line = json.dumps(rec.as_dict(), separators=(",", ":"), sort_keys=True)
    with preferences_path().open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return rec


def iter_pairs() -> Iterator[PreferencePair]:
    """Yield every stored pair; skip corrupt or wrong-schema lines silently."""
    path = preferences_path()
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("schema") != SCHEMA:
                continue
            try:
                yield PreferencePair(**d)
            except TypeError:
                # Unknown/missing fields — skip rather than crash the reader.
                continue


def count() -> int:
    path = preferences_path()
    if not path.exists():
        return 0
    n = 0
    with path.open("r", encoding="utf-8") as fh:
        for _ in fh:
            n += 1
    return n


def _is_sha256_hex(s: str) -> bool:
    if len(s) != 64:
        return False
    try:
        int(s, 16)
    except ValueError:
        return False
    return True


# --- Emitter helpers ------------------------------------------------------
# These are the two v1 sources (per roadmap REC-009). Each helper hashes
# any input string BEFORE calling `log_pair`, preserving the invariant
# that only digests are persisted.

def emit_bandit_outcome(chosen_arm: str, rejected_arm: str, context: str) -> PreferencePair:
    """Emit a preference pair from a bandit arm-vs-arm outcome.

    `context` is hashed here; the input string never leaves this call.
    """
    ctx_hash = hashlib.sha256(context.encode("utf-8")).hexdigest()
    return log_pair(chosen_arm, rejected_arm, "bandit", ctx_hash)


def emit_rollback_event(prior_state_id: str, current_state_id: str, context: str) -> PreferencePair:
    """Emit a preference pair when a snapshot restore chooses prior state.

    `context` is hashed here; the input string never leaves this call.
    """
    ctx_hash = hashlib.sha256(context.encode("utf-8")).hexdigest()
    return log_pair(prior_state_id, current_state_id, "rollback", ctx_hash)
