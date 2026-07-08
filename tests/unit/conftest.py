# SPDX-License-Identifier: Apache-2.0
"""Test setup: point Eidolon at an isolated $EIDOLON_HOME + $HERMES_HOME.

Also ensures the src/ tree is importable when running `python -m unittest`
directly from the repo root, so tests do not require an editable install.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
