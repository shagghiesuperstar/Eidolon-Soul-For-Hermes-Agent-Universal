# SPDX-License-Identifier: Apache-2.0
"""Adapter loader for the memory backend (REC-018).

Selection logic
---------------
The loader reads the Hermes host config at::

    $HERMES_HOME/config.yaml

and looks for the key ``memory.backend``.  Supported values::

    memory.backend: hindsight   # default production adapter
    memory.backend: inmem       # CI / test adapter

If the config file is absent, unreadable, or the key is missing, the loader
defaults to ``hindsight`` and emits an INFO event explaining why.

If the value is unrecognised, the loader degrades to ``inmem``, emits a
DEGRADED event, and never raises.

Stdlib-only YAML parsing
------------------------
PyYAML is forbidden (stdlib-first invariant).  The config file uses a simple
``key: value`` flat structure for this key — we extract it with ``re``.
Nested keys are expressed as dot-separated names in a single flat mapping::

    memory.backend: hindsight

Any YAML feature beyond ``key: value`` lines is silently ignored by the
parser.  This is intentional and safe for a config key that is a plain string.
"""

from __future__ import annotations

import re
from typing import Optional

from eidolon.memory.adapter import MemoryAdapter
from eidolon.memory.inmem import InMemAdapter
from eidolon.memory.hindsight import HindsightAdapter
from eidolon.util.events import emit, STATUS_DEGRADED, STATUS_INFO
from eidolon.util.paths import hermes_home

_SOURCE = "eidolon.memory.loader"
_KNOWN: dict[str, type[MemoryAdapter]] = {
    "hindsight": HindsightAdapter,
    "inmem": InMemAdapter,
}
_DEFAULT_BACKEND = "hindsight"

# Matches lines like:  memory.backend: hindsight
#                  or: memory.backend:hindsight
_KEY_RE = re.compile(
    r"^\s*memory\.backend\s*:\s*(?P<value>[^#\s]+)",
    re.MULTILINE,
)


def _read_backend_from_config() -> Optional[str]:
    """Return the raw ``memory.backend`` value from Hermes config, or None."""
    config_path = hermes_home() / "config.yaml"
    if not config_path.exists():
        return None
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = _KEY_RE.search(text)
    if m:
        return m.group("value").strip()
    return None


def load_adapter() -> MemoryAdapter:
    """Instantiate and return the configured memory adapter.

    Always returns a usable adapter.  Degrades to ``InMemAdapter`` if the
    configured backend is unrecognised; emits a DEGRADED event in that case.
    """
    raw = _read_backend_from_config()

    if raw is None:
        emit(
            "memory.loader",
            STATUS_INFO,
            _SOURCE,
            reason="memory.backend not set in host config; defaulting to hindsight",
            selected="hindsight",
        )
        return HindsightAdapter()

    cls = _KNOWN.get(raw)
    if cls is None:
        emit(
            "memory.loader",
            STATUS_DEGRADED,
            _SOURCE,
            reason=f"unknown memory.backend {raw!r}; falling back to inmem",
            configured=raw,
            selected="inmem",
        )
        return InMemAdapter()

    emit(
        "memory.loader",
        STATUS_INFO,
        _SOURCE,
        reason="memory backend loaded from config",
        selected=raw,
    )
    return cls()
