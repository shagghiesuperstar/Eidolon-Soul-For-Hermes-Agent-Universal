"""Snapshot management for last-known-good rollback (REC-004).

Strategy:
- A snapshot is a directory under $EIDOLON_HOME/last_known_good/<timestamp>/
- Contents are copies of the tracked files (SOUL.md, dream-cycle handler,
  integrity-watchdog handler). Tracked set is intentionally small; growing
  it later is a config change.
- Snapshots are copy-on-write in intent (we never mutate an existing snapshot
  directory); on POSIX we use hardlinks where possible via stdlib shutil.
- After a successful cycle, the most recent snapshot is symlinked to
  `last_known_good/current`. If the symlink cannot be created (Windows without
  developer mode), we write a text pointer file instead.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List

from eidolon.util.paths import last_known_good_dir, repo_root


# Files Eidolon considers "load-bearing" for its own operation. Editing this
# list is a deliberate config change and shows up in git blame.
TRACKED_RELATIVE = (
    "SOUL.md",
    "skills/dream-cycle/handler.py",
    "skills/integrity-watchdog/handler.py",
)

CURRENT_POINTER = "current"


@dataclass(frozen=True)
class Snapshot:
    id: str  # timestamp-based, sortable
    path: str
    files: tuple[str, ...]
    checksum: str  # sha256 over sorted (relpath, file_sha256) pairs


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _compute_checksum(dest: Path, files: List[Path]) -> str:
    parts = []
    for rel in sorted(str(f.relative_to(dest)) for f in files):
        p = dest / rel
        parts.append(f"{rel}:{_sha256_file(p)}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _update_current(pointer_target: Path, dest: Path) -> None:
    """Point `current` at the new snapshot. Prefer symlink; fall back to file."""
    if pointer_target.exists() or pointer_target.is_symlink():
        try:
            if pointer_target.is_symlink() or pointer_target.is_file():
                pointer_target.unlink()
            else:
                shutil.rmtree(pointer_target)
        except OSError:
            pass
    try:
        pointer_target.symlink_to(dest.name, target_is_directory=True)
    except (OSError, NotImplementedError):
        pointer_target.write_text(dest.name + "\n", encoding="utf-8")


def take_snapshot(*, reason: str = "cycle_success") -> Snapshot:
    """Copy all tracked files into a new snapshot directory.

    Missing tracked files are silently omitted (a fresh repo may not have all
    skills yet); the snapshot manifest records exactly which files were
    captured, so restoration is deterministic.
    """
    root = repo_root()
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    dest = last_known_good_dir() / ts
    dest.mkdir(parents=True, exist_ok=False)

    captured: List[Path] = []
    for rel in TRACKED_RELATIVE:
        src = root / rel
        if not src.exists():
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        captured.append(target)

    checksum = _compute_checksum(dest, captured) if captured else ""
    manifest = {
        "id": ts,
        "reason": reason,
        "created_ts": time.time(),
        "files": [str(p.relative_to(dest)) for p in captured],
        "checksum": checksum,
    }
    (dest / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    _update_current(last_known_good_dir() / CURRENT_POINTER, dest)

    return Snapshot(
        id=ts,
        path=str(dest),
        files=tuple(manifest["files"]),
        checksum=checksum,
    )


def list_snapshots() -> List[Snapshot]:
    root = last_known_good_dir()
    out: List[Snapshot] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name == CURRENT_POINTER:
            continue
        mf = child / "manifest.json"
        if not mf.exists():
            continue
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        out.append(
            Snapshot(
                id=data.get("id", child.name),
                path=str(child),
                files=tuple(data.get("files", ())),
                checksum=data.get("checksum", ""),
            )
        )
    return out


def current_snapshot() -> Snapshot | None:
    root = last_known_good_dir()
    pointer = root / CURRENT_POINTER
    if pointer.is_symlink():
        target_name = Path(pointer.readlink() if hasattr(pointer, "readlink") else str(pointer)).name
    elif pointer.is_file():
        target_name = pointer.read_text(encoding="utf-8").strip()
    else:
        return None
    target = root / target_name
    if not target.exists():
        return None
    mf = target / "manifest.json"
    if not mf.exists():
        return None
    try:
        data = json.loads(mf.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return Snapshot(
        id=data.get("id", target.name),
        path=str(target),
        files=tuple(data.get("files", ())),
        checksum=data.get("checksum", ""),
    )
