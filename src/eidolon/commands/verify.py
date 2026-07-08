# SPDX-License-Identifier: Apache-2.0
"""`eidolon verify` — post-install end-to-end smoke test.

`verify` is distinct from `doctor`:

- `doctor` answers: "is my environment healthy right now?"  (read-only probes)
- `verify` answers: "does the eidolon CLI actually execute end-to-end?"

`verify` runs a fixed sequence of read-only subcommand invocations against the
current install and asserts each one exits with a status in the expected set.
It is what the installer runs at the end, and what CI runs to prove the wheel
we just built is not broken.

Semantics:
- verify itself is read-only. It never mutates state beyond what the exercised
  subcommands already do (doctor and report both create $EIDOLON_HOME on first
  run — that is the point of running them).
- The `--strict` flag treats DEGRADED as failure. Default treats DEGRADED as OK
  because Eidolon's contract is "run in reduced mode when Hermes is absent."
- Human output is a tabular checklist. --json emits the machine contract.

Exit codes (matches CLI spine):
- 0 : every step returned an acceptable status
- 2 : at least one step returned DEGRADED (only fires when --strict is set;
      otherwise DEGRADED is folded into PASS)
- 1 : at least one step returned FAIL, or an unexpected exception was raised
"""

from __future__ import annotations

import dataclasses
import io
import json
import sys
import time
from contextlib import redirect_stdout, redirect_stderr
from typing import Callable, List

from eidolon._version import __version__
from eidolon.util import events

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_DEGRADED = 2

# Status vocabulary — mirrors eidolon.checks but verify steps have a fourth
# state ("ERROR") for "step raised an exception we did not expect", which
# always maps to FAIL. This is a defense-in-depth belt on top of the
# `safe()` wrapper in the doctor check framework.
PASS = "PASS"
DEGRADED = "DEGRADED"
FAIL = "FAIL"
ERROR = "ERROR"


@dataclasses.dataclass
class StepResult:
    name: str
    status: str  # PASS | DEGRADED | FAIL | ERROR
    exit_code: int
    duration_ms: int
    detail: str

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)


def _classify(rc: int) -> str:
    if rc == 0:
        return PASS
    if rc == 2:
        return DEGRADED
    if rc == 1:
        return FAIL
    return ERROR


def _run_step(name: str, fn: Callable[[], int]) -> StepResult:
    """Run a subcommand entry-point in-process and capture its exit code + timing.

    We invoke the same function objects that the CLI dispatches to, so we
    exercise the identical code path a shell invocation would take, without
    the overhead of spawning a subprocess (which would require the CLI to be
    on PATH — often not true during CI before pip install completes).
    """
    buf_out = io.StringIO()
    buf_err = io.StringIO()
    t0 = time.monotonic()
    try:
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            rc = fn()
        status = _classify(int(rc))
        detail = f"exit={rc}"
    except SystemExit as exc:  # argparse or explicit sys.exit
        rc = int(exc.code) if isinstance(exc.code, int) else 1
        status = _classify(rc)
        detail = f"SystemExit(exit={rc})"
    except Exception as exc:  # noqa: BLE001 - by design, wrap anything
        rc = 1
        status = ERROR
        detail = f"raised {type(exc).__name__}: {exc}"
    dur_ms = int((time.monotonic() - t0) * 1000)
    return StepResult(name=name, status=status, exit_code=rc, duration_ms=dur_ms, detail=detail)


# ---------------------------------------------------------------------------
# Step implementations — each returns an int exit code
# ---------------------------------------------------------------------------

def _step_import() -> int:
    """Confirm the eidolon package is importable and reports a version string."""
    if not isinstance(__version__, str) or not __version__:
        return 1
    # Trivial semver-ish shape check; we do not enforce strict SemVer here
    # because dev builds may append `-dev0` or similar.
    if "." not in __version__:
        return 1
    return 0


def _step_doctor() -> int:
    """Run `eidolon doctor` in-process. Returns doctor's exit code."""
    from eidolon.commands import doctor as _doctor

    return _doctor.run(json_out=True)


def _step_report() -> int:
    """Run `eidolon report --since 24h` in-process. Empty state is a valid PASS."""
    from eidolon.commands import report as _report

    return _report.run(since="24h", json_out=True)


def _step_rollback_dry() -> int:
    """Run `eidolon rollback --dry-run` in-process — must never mutate state."""
    from eidolon.commands import rollback as _rollback

    return _rollback.run(dry_run=True, json_out=True)


STEPS: List[tuple[str, Callable[[], int]]] = [
    ("import_package", _step_import),
    ("cli_doctor", _step_doctor),
    ("cli_report", _step_report),
    ("cli_rollback_dry_run", _step_rollback_dry),
]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def _overall(results: List[StepResult], *, strict: bool) -> str:
    if any(r.status in (FAIL, ERROR) for r in results):
        return FAIL
    if any(r.status == DEGRADED for r in results):
        return DEGRADED if strict else PASS
    return PASS


def _print_human(results: List[StepResult], overall: str) -> None:
    glyph = {PASS: "PASS ", DEGRADED: "DEGRAD", FAIL: "FAIL ", ERROR: "ERROR"}
    print("eidolon verify — end-to-end CLI smoke")
    for r in results:
        tag = glyph.get(r.status, "?????")
        print(f"  [{tag}] {r.name:<24} {r.duration_ms:>4}ms  {r.detail}")
    print(f"\noverall: {overall}")


def run(*, json_out: bool = False, strict: bool = False) -> int:
    results: List[StepResult] = [_run_step(name, fn) for name, fn in STEPS]
    overall = _overall(results, strict=strict)

    # Emit each step + summary as structured events so operators can grep.
    for r in results:
        events.emit(
            f"verify.{r.name}",
            r.status if r.status in (PASS, DEGRADED, FAIL) else events.STATUS_INFO,
            source="commands.verify",
            exit_code=r.exit_code,
            duration_ms=r.duration_ms,
        )
    events.emit(
        "verify.summary",
        overall,
        source="commands.verify",
        n_steps=len(results),
        strict=strict,
    )

    if json_out:
        payload = {
            "overall": overall,
            "strict": strict,
            "steps": [r.as_dict() for r in results],
        }
        json.dump(payload, sys.stdout, sort_keys=True)
        sys.stdout.write("\n")
    else:
        _print_human(results, overall)

    if overall == FAIL:
        return EXIT_FAIL
    if overall == DEGRADED:
        return EXIT_DEGRADED
    return EXIT_OK
