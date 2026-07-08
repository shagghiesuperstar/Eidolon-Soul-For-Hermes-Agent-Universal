#!/usr/bin/env python3
"""PII sanitization scanner (REC-011).

Reads .sanitize-patterns.yml at repo root, walks every non-excluded file,
and greps for each pattern. Exits 0 if clean, 1 if any match is found.

Constraints (roadmap § 8.11):
- PyYAML is forbidden. The YAML shape is fixed and simple, so we parse it
  with a small stdlib-only reader.
- Exclusions are path-prefix, not glob.
- --self-test runs against tests/fixtures/sanitize_selftest/ and asserts
  every positive fixture matches and every clean fixture does not.

Usage:
    python scripts/sanitize_check.py           # scan repo, exit 1 on hit
    python scripts/sanitize_check.py --self-test
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
PATTERNS_FILE = REPO_ROOT / ".sanitize-patterns.yml"
SELFTEST_DIR = REPO_ROOT / "tests" / "fixtures" / "sanitize_selftest"

# Directories never scanned (build artefacts, VCS).
GLOBAL_EXCLUDES = (
    ".git/",
    ".github/",
    "__pycache__/",
    "dist/",
    "build/",
    ".eggs/",
    "node_modules/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".venv/",
    "venv/",
    "tests/fixtures/sanitize_selftest/",  # scanner-owned; own tests exercise it.
)

# Binary/asset extensions we never scan.
BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip",
    ".gz", ".tgz", ".tar", ".whl", ".pyc", ".so", ".dylib", ".woff",
    ".woff2", ".ttf", ".otf", ".mp4", ".mp3", ".wav",
}


@dataclass
class Pattern:
    name: str
    regex: str
    exclude_paths: List[str] = field(default_factory=list)
    compiled: Optional[re.Pattern] = None

    def matches_path(self, rel: str) -> bool:
        """Return True if this pattern should be applied to rel."""
        for prefix in self.exclude_paths:
            if rel.startswith(prefix):
                return False
        return True


# ---------------------------------------------------------------------------
# Minimal YAML reader (stdlib only)
# ---------------------------------------------------------------------------

def _strip_comment(line: str) -> str:
    """Remove trailing comment while respecting a single-quoted regex value."""
    out = []
    in_squote = False
    for ch in line:
        if ch == "'":
            in_squote = not in_squote
            out.append(ch)
            continue
        if ch == "#" and not in_squote:
            break
        out.append(ch)
    return "".join(out).rstrip()


def _unquote(val: str) -> str:
    val = val.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        return val[1:-1]
    return val


def _parse_list_inline(val: str) -> List[str]:
    """Parse a YAML flow-style list: [a, b, c]."""
    val = val.strip()
    if not (val.startswith("[") and val.endswith("]")):
        raise ValueError(f"expected flow list, got: {val!r}")
    body = val[1:-1].strip()
    if not body:
        return []
    return [_unquote(x.strip()) for x in body.split(",") if x.strip()]


def parse_patterns_file(path: Path) -> List[Pattern]:
    """Parse the fixed-shape .sanitize-patterns.yml.

    Grammar (line-oriented):
        patterns:
          - name: <id>
            regex: '<pattern>'
            exclude_paths: [a/, b/]   # optional
    """
    if not path.exists():
        raise FileNotFoundError(str(path))
    entries: List[Pattern] = []
    current: Optional[Pattern] = None
    in_patterns = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = _strip_comment(raw)
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped == "patterns:":
            in_patterns = True
            continue
        if not in_patterns:
            continue
        # New list item
        if stripped.startswith("- "):
            if current is not None:
                entries.append(current)
            current = Pattern(name="", regex="")
            # Some list items place the first key on the same line: `- name: X`
            after = stripped[2:].strip()
            if ":" in after:
                key, _, val = after.partition(":")
                _assign(current, key.strip(), val.strip())
            continue
        if current is None:
            continue
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            _assign(current, key.strip(), val.strip())
    if current is not None:
        entries.append(current)
    # Compile
    for p in entries:
        if not p.name or not p.regex:
            raise ValueError(f"pattern entry missing name/regex: {p}")
        p.compiled = re.compile(p.regex)
    return entries


def _assign(p: Pattern, key: str, val: str) -> None:
    if key == "name":
        p.name = _unquote(val)
    elif key == "regex":
        p.regex = _unquote(val)
    elif key == "exclude_paths":
        p.exclude_paths = _parse_list_inline(val)
    # ignore unknown keys (forward-compat)


# ---------------------------------------------------------------------------
# Repo scan
# ---------------------------------------------------------------------------

def _is_excluded(rel: str) -> bool:
    for prefix in GLOBAL_EXCLUDES:
        if rel.startswith(prefix):
            return True
    return False


def iter_scanned_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if _is_excluded(rel):
            continue
        if path.suffix.lower() in BINARY_EXTS:
            continue
        yield path


def _redact(match_text: str) -> str:
    if len(match_text) <= 6:
        return "***"
    return match_text[:3] + "***" + match_text[-2:]


def scan_repo(root: Path, patterns: List[Pattern]) -> List[Tuple[str, int, str, str]]:
    """Return list of (relpath, lineno, pattern_name, redacted_match)."""
    hits: List[Tuple[str, int, str, str]] = []
    for path in iter_scanned_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        lines = text.splitlines()
        for pat in patterns:
            if not pat.matches_path(rel):
                continue
            for lineno, line in enumerate(lines, start=1):
                m = pat.compiled.search(line)
                if m:
                    hits.append((rel, lineno, pat.name, _redact(m.group(0))))
    return hits


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def run_self_test(patterns: List[Pattern]) -> Tuple[int, int, List[str]]:
    """Run against fixture directory.

    Fixtures live at tests/fixtures/sanitize_selftest/:
        <pattern_name>_positive.txt   -- MUST match at least once
        <pattern_name>_clean.txt      -- MUST NOT match

    Returns (passed, total, failures).
    """
    if not SELFTEST_DIR.exists():
        return (0, 0, [f"missing fixture dir: {SELFTEST_DIR}"])
    total = 0
    passed = 0
    failures: List[str] = []
    for pat in patterns:
        pos = SELFTEST_DIR / f"{pat.name}_positive.txt"
        neg = SELFTEST_DIR / f"{pat.name}_clean.txt"
        for label, path, must_match in (
            ("positive", pos, True),
            ("clean", neg, False),
        ):
            if not path.exists():
                failures.append(f"missing fixture: {path.name}")
                total += 1
                continue
            total += 1
            text = path.read_text(encoding="utf-8")
            found = bool(pat.compiled.search(text))
            if found == must_match:
                passed += 1
            else:
                failures.append(
                    f"{pat.name} {label}: expected match={must_match} got={found}"
                )
    return (passed, total, failures)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="PII sanitization scanner (REC-011).")
    ap.add_argument("--self-test", action="store_true", help="Run fixture self-test.")
    ap.add_argument("--patterns", default=str(PATTERNS_FILE),
                    help="Path to .sanitize-patterns.yml")
    ap.add_argument("--root", default=str(REPO_ROOT),
                    help="Repo root to scan.")
    args = ap.parse_args(argv)

    try:
        patterns = parse_patterns_file(Path(args.patterns))
    except (FileNotFoundError, ValueError, re.error) as exc:
        print(f"sanitize_check: pattern load failed: {exc}", file=sys.stderr)
        return 2

    if args.self_test:
        passed, total, failures = run_self_test(patterns)
        for f in failures:
            print(f"  FAIL: {f}", file=sys.stderr)
        if passed == total and total > 0:
            print(f"self-test PASS ({passed}/{total} cases)")
            return 0
        print(f"self-test FAIL ({passed}/{total} cases)", file=sys.stderr)
        return 1

    hits = scan_repo(Path(args.root), patterns)
    if not hits:
        print("sanitize scan clean (0 matches)")
        return 0
    for rel, lineno, name, redacted in hits:
        print(f"{rel}:{lineno}: {name} {redacted}")
    print(f"sanitize scan: {len(hits)} match(es)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
