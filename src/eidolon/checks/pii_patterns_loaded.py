# SPDX-License-Identifier: Apache-2.0
"""Check: .sanitize-patterns.yml parses and has >=5 entries (REC-011)."""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

from eidolon.checks import CheckResult, FAIL, PASS

_MIN_PATTERNS = 5


def _repo_root() -> Path:
    # src/eidolon/checks/pii_patterns_loaded.py -> repo root is 4 levels up.
    return Path(__file__).resolve().parents[3]


def _load_scanner_module():
    root = _repo_root()
    scanner_path = root / "scripts" / "sanitize_check.py"
    if not scanner_path.exists():
        return None, scanner_path
    spec = importlib.util.spec_from_file_location(
        "_eidolon_sanitize_check", str(scanner_path)
    )
    if spec is None or spec.loader is None:
        return None, scanner_path
    module = importlib.util.module_from_spec(spec)
    # Register in sys.modules before exec so dataclasses (and other stdlib
    # helpers that resolve via sys.modules[cls.__module__]) can find it.
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:  # noqa: BLE001
        sys.modules.pop(spec.name, None)
        return None, scanner_path
    return module, scanner_path


def check() -> CheckResult:
    root = _repo_root()
    patterns_path = root / ".sanitize-patterns.yml"

    if not patterns_path.exists():
        return CheckResult(
            name="pii_patterns_loaded",
            status=FAIL,
            reason=f"missing {patterns_path.name}",
        )

    scanner, scanner_path = _load_scanner_module()
    if scanner is None:
        return CheckResult(
            name="pii_patterns_loaded",
            status=FAIL,
            reason=f"cannot import {scanner_path.name}",
        )

    try:
        patterns = scanner.parse_patterns_file(patterns_path)
    except (ValueError, re.error, OSError) as exc:
        return CheckResult(
            name="pii_patterns_loaded",
            status=FAIL,
            reason=f"parse_failed:{type(exc).__name__}:{exc}",
        )

    count = len(patterns)
    if count < _MIN_PATTERNS:
        return CheckResult(
            name="pii_patterns_loaded",
            status=FAIL,
            reason=f"only {count} patterns (need >={_MIN_PATTERNS})",
        )

    return CheckResult(
        name="pii_patterns_loaded",
        status=PASS,
        reason=f"{count} sanitization patterns loaded.",
        detail={"count": str(count)},
    )
