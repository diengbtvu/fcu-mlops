#!/usr/bin/env bash
# Abort early if the server doesn't have enough headroom to run both colors side by
# side during the deploy window (blue+green briefly coexist between steps 6 and 11).
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; NC='\033[0m'
log()  { echo -e "${GREEN}[preflight]${NC} $*"; }
die()  { echo -e "${RED}[preflight] ERROR:${NC} $*" >&2; exit 1; }

MIN_RAM_MB="${MIN_RAM_MB:-500}"
MIN_DISK_GB="${MIN_DISK_GB:-5}"
DISK_PATH="${DISK_PATH:-/var/lib/docker}"
[ -d "$DISK_PATH" ] || DISK_PATH="/"

AVAILABLE_RAM_MB="$(awk '/MemAvailable/ {printf "%d", $2/1024}' /proc/meminfo)"
AVAILABLE_DISK_KB="$(df -Pk "$DISK_PATH" | awk 'NR==2 {print $4}')"
AVAILABLE_DISK_GB=$(( AVAILABLE_DISK_KB / 1024 / 1024 ))

log "RAM available: ${AVAILABLE_RAM_MB}MB (min: ${MIN_RAM_MB}MB)"
log "Disk available on ${DISK_PATH}: ${AVAILABLE_DISK_GB}GB (min: ${MIN_DISK_GB}GB)"

FAIL=0
if [ "$AVAILABLE_RAM_MB" -lt "$MIN_RAM_MB" ]; then
    echo -e "${RED}[preflight] RAM available (${AVAILABLE_RAM_MB}MB) < ${MIN_RAM_MB}MB${NC}" >&2
    FAIL=1
fi
if [ "$AVAILABLE_DISK_GB" -lt "$MIN_DISK_GB" ]; then
    echo -e "${RED}[preflight] Disk available (${AVAILABLE_DISK_GB}GB) < ${MIN_DISK_GB}GB${NC}" >&2
    FAIL=1
fi

if [ "$FAIL" -ne 0 ]; then
    die "Not enough headroom to run both colors during the deploy window. Deploy aborted before touching anything; nothing changed."
fi

log "Resources OK."
