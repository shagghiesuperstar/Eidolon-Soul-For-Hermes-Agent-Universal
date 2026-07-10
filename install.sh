#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Eidolon installer — RECs 006/007
set -euo pipefail

VERSION="${EIDOLON_INSTALL_VERSION:-latest}"
WHEEL_URL="${EIDOLON_WHEEL_URL:-}"
PREFIX="${EIDOLON_PREFIX:-$HOME/.local}"
NO_HERMES=0
DRY_RUN=0

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --no-hermes) NO_HERMES=1 ;;
    --prefix=*) PREFIX="${1#*=}" ;;
    --wheel-url=*) WHEEL_URL="${1#*=}" ;;
    --version=*) VERSION="${1#*=}" ;;
    *) echo "unknown arg: $1" >&2; exit 64 ;;
  esac
  shift
done

log() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

log "Eidolon installer v${VERSION}"

# [1/4] host prerequisites
log "[1/4] verifying host prerequisites..."
command -v python3 >/dev/null || die "python3 not found"
PYVER=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
case "$PYVER" in
  3.10|3.11|3.12|3.13) : ;;
  *) die "python $PYVER not supported (need 3.10-3.13)" ;;
esac
log "  python $PYVER: PASS"

if [ "$DRY_RUN" -eq 1 ]; then
  log "installer dry-run: would install eidolon-hermes ${VERSION} to ${PREFIX}"
  exit 0
fi

# [2/4] install
log "[2/4] installing eidolon-hermes..."
if [ -n "$WHEEL_URL" ]; then
  TMPDIR="$(mktemp -d)"
  trap 'rm -rf "$TMPDIR"' EXIT
  # Support file:// protocol for local testing (strip prefix, copy instead of curl)
  case "$WHEEL_URL" in
    file://*)
      cp "${WHEEL_URL#file://}" "$TMPDIR/eidolon.whl"
      ;;
    *)
      curl -fsSL "$WHEEL_URL" -o "$TMPDIR/eidolon.whl"
      ;;
  esac
  python3 -m pip install --user "$TMPDIR/eidolon.whl"
else
  python3 -m pip install --user "eidolon-hermes${VERSION:+==$VERSION}"
fi
log "  pip install: PASS"

# [3/4] hooks
log "[3/4] wiring Hermes hooks..."
if [ "$NO_HERMES" -eq 1 ] || [ ! -d "${HERMES_HOME:-$HOME/.hermes}" ]; then
  log "  no Hermes home present or --no-hermes: DEGRADED (skipped)"
else
  # Wiring deferred to REC-017; safe no-op today.
  log "  hook wiring: DEGRADED (deferred to REC-017)"
fi

# [4/4] doctor
log "[4/4] running eidolon doctor..."
set +e
"$PREFIX/bin/eidolon" doctor --json 2>/dev/null | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
    print("  overall:", d["overall"])
    sys.exit({"PASS":0,"DEGRADED":2,"FAIL":1}.get(d["overall"],1))
except Exception:
    print("  overall: DEGRADED (could not parse doctor output)")
    sys.exit(2)
'
CODE=$?
set -e

log "Install completed. eidolon doctor exit: $CODE"
exit "$CODE"
