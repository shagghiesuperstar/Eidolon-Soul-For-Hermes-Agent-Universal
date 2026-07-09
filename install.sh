#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Eidolon installer — self-improvement layer for Hermes Agent.
#
# Design principles (Fable-5 / roadmap § 8.6):
#   - Loud on failure. Never silently no-ops. Never claims success it can't prove.
#   - Idempotent. Re-running is a no-op that re-verifies.
#   - No sudo. No system Python mutation. User-local install only.
#   - macOS and Linux only. Windows users install manually.
#   - Stdlib-first: shell + python3 + git + pip. No brew/apt/curl-of-installers required.
#   - <90 seconds on cold cache. Verified by .github/workflows/installer-test.yml.
#
# Exit codes:
#   0  — install succeeded, `eidolon doctor` returned PASS or DEGRADED
#   1  — install failed (a prerequisite missing, network dead, pip refused, etc.)
#   2  — install technically succeeded but `eidolon doctor` returned FAIL
#   64 — usage error (bad flag)
#
# Environment overrides (all optional):
#   EIDOLON_REF          git ref to install (default: main)
#   EIDOLON_REPO         repo URL       (default: https://github.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal.git)
#   EIDOLON_METHOD       "pip" or "src" (default: "pip"; "src" clones the repo)
#   EIDOLON_SRC_DIR      where to clone if METHOD=src (default: $HOME/.eidolon/src)
#   EIDOLON_NO_FETCH     set to 1 to skip the git-fetch step when METHOD=src
#                        (use when EIDOLON_SRC_DIR is already checked out at the
#                         desired ref, e.g. inside a CI job)
#   EIDOLON_SKIP_DOCTOR  set to 1 to skip the final `eidolon doctor` gate
#   EIDOLON_PYTHON       python interpreter to use (default: auto-detect first of python3.13/12/11/10/python3)
#   HERMES_HOME          host Hermes home (default: $HOME/.hermes)
#   EIDOLON_HOME         Eidolon state root (default: $HERMES_HOME/state/eidolon)
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal/main/install.sh | bash
#   # or offline:
#   bash install.sh

set -euo pipefail

# ---------------------------------------------------------------------------
# 0. Constants + logging
# ---------------------------------------------------------------------------

EIDOLON_REPO="${EIDOLON_REPO:-https://github.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal.git}"
EIDOLON_REF="${EIDOLON_REF:-main}"
EIDOLON_METHOD="${EIDOLON_METHOD:-pip}"
EIDOLON_SRC_DIR="${EIDOLON_SRC_DIR:-$HOME/.eidolon/src}"
EIDOLON_NO_FETCH="${EIDOLON_NO_FETCH:-0}"
EIDOLON_SKIP_DOCTOR="${EIDOLON_SKIP_DOCTOR:-0}"
HERMES_HOME_DEFAULT="${HERMES_HOME:-$HOME/.hermes}"

# Colored logs only when stdout is a TTY.
if [[ -t 1 ]]; then
  C_R=$'\033[31m'; C_G=$'\033[32m'; C_Y=$'\033[33m'; C_B=$'\033[34m'; C_N=$'\033[0m'
else
  C_R=""; C_G=""; C_Y=""; C_B=""; C_N=""
fi

log()   { printf '%s[eidolon-install]%s %s\n' "$C_B" "$C_N" "$*"; }
warn()  { printf '%s[eidolon-install]%s %s%s%s\n' "$C_B" "$C_N" "$C_Y" "$*" "$C_N" >&2; }
error() { printf '%s[eidolon-install]%s %sERROR:%s %s\n' "$C_B" "$C_N" "$C_R" "$C_N" "$*" >&2; }
ok()    { printf '%s[eidolon-install]%s %s%s%s\n' "$C_B" "$C_N" "$C_G" "$*" "$C_N"; }

# ---------------------------------------------------------------------------
# 1. OS gate — macOS + Linux only
# ---------------------------------------------------------------------------

uname_s="$(uname -s 2>/dev/null || echo unknown)"
case "$uname_s" in
  Darwin|Linux) ;;
  *)
    error "Unsupported OS: $uname_s. Eidolon installer supports macOS + Linux only."
    error "Windows users: pip install eidolon-hermes  (once PyPI ships REC-007)."
    exit 1
    ;;
esac
log "OS: $uname_s"

# ---------------------------------------------------------------------------
# 2. Python detection — require 3.10..3.13
# ---------------------------------------------------------------------------

find_python() {
  if [[ -n "${EIDOLON_PYTHON:-}" ]]; then
    command -v "$EIDOLON_PYTHON" >/dev/null 2>&1 || return 1
    printf '%s' "$EIDOLON_PYTHON"
    return 0
  fi
  for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      # Verify it meets the >=3.10, <3.14 constraint.
      if "$candidate" -c 'import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] < (3,14) else 1)' 2>/dev/null; then
        printf '%s' "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

if ! PY="$(find_python)"; then
  error "No supported Python found. Eidolon requires Python 3.10, 3.11, 3.12, or 3.13."
  error "Install one (macOS: 'brew install python@3.13'; Debian/Ubuntu: 'apt install python3.13')"
  error "then re-run this installer. Or set EIDOLON_PYTHON=/path/to/python."
  exit 1
fi

PY_VER="$("$PY" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])')"
log "Python: $PY ($PY_VER)"

# ---------------------------------------------------------------------------
# 3. pip availability (with a helpful message if it's not there)
# ---------------------------------------------------------------------------

if ! "$PY" -m pip --version >/dev/null 2>&1; then
  error "pip is not available for $PY."
  error "Try:  $PY -m ensurepip --user  (or install python3-pip via your package manager)."
  exit 1
fi

# ---------------------------------------------------------------------------
# 4. git availability (only strictly required for METHOD=src or pip-from-git)
# ---------------------------------------------------------------------------

if ! command -v git >/dev/null 2>&1; then
  error "git is not installed but is required to install from source."
  error "macOS: 'xcode-select --install'  |  Debian/Ubuntu: 'apt install git'"
  exit 1
fi

# ---------------------------------------------------------------------------
# 5. Install the eidolon-hermes package
# ---------------------------------------------------------------------------

install_from_pip() {
  # Install directly from the git ref. Once REC-007 (PyPI) ships, this becomes
  # `pip install eidolon-hermes` and no git clone is needed.
  log "Installing eidolon-hermes from ${EIDOLON_REPO}@${EIDOLON_REF} via pip..."
  "$PY" -m pip install --user --upgrade \
    "git+${EIDOLON_REPO}@${EIDOLON_REF}#egg=eidolon-hermes" \
    || return 1
}

install_from_src() {
  mkdir -p "$(dirname "$EIDOLON_SRC_DIR")"
  if [[ "$EIDOLON_NO_FETCH" == "1" ]]; then
    log "EIDOLON_NO_FETCH=1: using existing checkout at ${EIDOLON_SRC_DIR}"
    if [[ ! -d "$EIDOLON_SRC_DIR" ]]; then
      error "EIDOLON_NO_FETCH=1 but $EIDOLON_SRC_DIR does not exist."
      return 1
    fi
  elif [[ -d "$EIDOLON_SRC_DIR/.git" ]]; then
    log "Updating existing clone at ${EIDOLON_SRC_DIR} -> ${EIDOLON_REF}"
    git -C "$EIDOLON_SRC_DIR" fetch --depth 1 origin "$EIDOLON_REF" || return 1
    git -C "$EIDOLON_SRC_DIR" checkout -f "FETCH_HEAD" || return 1
  else
    log "Cloning ${EIDOLON_REPO}@${EIDOLON_REF} -> ${EIDOLON_SRC_DIR}"
    rm -rf "$EIDOLON_SRC_DIR"
    git clone --depth 1 --branch "$EIDOLON_REF" "$EIDOLON_REPO" "$EIDOLON_SRC_DIR" || return 1
  fi
  log "Installing eidolon-hermes from local checkout..."
  "$PY" -m pip install --user --upgrade "$EIDOLON_SRC_DIR" || return 1
}

case "$EIDOLON_METHOD" in
  pip) install_from_pip ;;
  src) install_from_src ;;
  *)
    error "EIDOLON_METHOD must be 'pip' or 'src' (got '$EIDOLON_METHOD')."
    exit 64
    ;;
esac

# ---------------------------------------------------------------------------
# 6. Locate the installed CLI
# ---------------------------------------------------------------------------

# pip --user installs into different locations on macOS vs Linux. Ask Python
# where its script dir is, then add it to PATH for the doctor invocation.
USER_BIN="$("$PY" -c 'import sysconfig; print(sysconfig.get_path("scripts", scheme="posix_user"))')"
if [[ ! -x "$USER_BIN/eidolon" ]]; then
  # Fallback: some setups install into a different scheme.
  USER_BIN_ALT="$("$PY" -m site --user-base)/bin"
  if [[ -x "$USER_BIN_ALT/eidolon" ]]; then
    USER_BIN="$USER_BIN_ALT"
  fi
fi

if [[ ! -x "$USER_BIN/eidolon" ]]; then
  error "Install completed but 'eidolon' CLI not found in $USER_BIN."
  error "This usually means pip --user installs are landing somewhere unexpected."
  error "Try: $PY -m eidolon doctor  (module invocation always works)."
  exit 1
fi

export PATH="$USER_BIN:$PATH"
log "eidolon CLI: $USER_BIN/eidolon"
ok "Installed: $("$USER_BIN/eidolon" --version 2>&1 | head -1)"

# Persistence hint. We do not modify user shell rc files automatically —
# operator opt-in only. Just tell them what to do.
case "$PATH" in
  *"$USER_BIN"*) ;;
  *)
    warn "For future shells, add this to your ~/.zshrc or ~/.bashrc:"
    warn "    export PATH=\"$USER_BIN:\$PATH\""
    ;;
esac

# ---------------------------------------------------------------------------
# 7. Doctor gate — the loud verification
# ---------------------------------------------------------------------------

if [[ "$EIDOLON_SKIP_DOCTOR" == "1" ]]; then
  warn "Skipping 'eidolon doctor' (EIDOLON_SKIP_DOCTOR=1)."
  ok "Install complete."
  exit 0
fi

log "Running 'eidolon doctor' to verify install..."
set +e
"$USER_BIN/eidolon" doctor
DOCTOR_RC=$?
set -e

case "$DOCTOR_RC" in
  0)  ok "Doctor: PASS. Eidolon is ready."; exit 0 ;;
  2)  warn "Doctor: DEGRADED. Eidolon installed but running in reduced mode."
      warn "Re-run 'eidolon doctor --json' after installing/configuring Hermes to promote to PASS."
      exit 0 ;;
  1)  error "Doctor: FAIL. Install technically succeeded but Eidolon is not operational."
      error "Run 'eidolon doctor --json' to see which check(s) failed."
      exit 2 ;;
  *)  error "Doctor returned unexpected exit code $DOCTOR_RC."; exit 2 ;;
esac
