#!/usr/bin/env bash
# Manual/CI rollback: point the proxy at <blue|green> again. Safe to run directly on the
# server without any CI involvement - this is exactly what deploy-prod's rollback path
# and the rollback.yml workflow both call.
#
# Assumes the target color's containers still exist (deploy.sh's drain window uses
# `compose stop`, not `down`, precisely so rollback can just restart them). If the
# target color was fully torn down (`compose down`), there is no image tag to recover
# here - run deploy.sh with an explicit tag instead.
#
# Usage: rollback.sh <blue|green>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[rollback]${NC} $*"; }
warn() { echo -e "${YELLOW}[rollback]${NC} $*"; }
die()  { echo -e "${RED}[rollback] ERROR:${NC} $*" >&2; exit 1; }

APP_SLUG="${APP_SLUG:-hydrogen}"
HEALTHY_TIMEOUT_SECONDS="${HEALTHY_TIMEOUT_SECONDS:-120}"
LOCK_FILE="$SCRIPT_DIR/.deploy.lock"

TARGET_COLOR="${1:-}"
case "$TARGET_COLOR" in blue|green) ;; *) die "Usage: $0 <blue|green>" ;; esac
TARGET_PROJECT="${APP_SLUG}-${TARGET_COLOR}"
[ -f "$SCRIPT_DIR/.env.${TARGET_COLOR}" ] || die ".env.${TARGET_COLOR} not found."

exec 9>"$LOCK_FILE"
flock -n 9 || die "A deploy/rollback is already running (lock: ${LOCK_FILE})."

container_for() {
    docker ps -a -q \
        --filter "label=com.docker.compose.project=${TARGET_PROJECT}" \
        --filter "label=com.docker.compose.service=$1" \
        | head -n1
}

WEBAPP_CID="$(container_for laravel-webapp)"
[ -n "$WEBAPP_CID" ] || die "No laravel-webapp container found at all for ${TARGET_PROJECT}. It was fully torn down - use deploy.sh prod <tag> instead."

# Recover the exact tag this color was last running, so we don't have to ask for one.
IMAGE_REF="$(docker inspect -f '{{.Config.Image}}' "$WEBAPP_CID")"
TAG="${IMAGE_REF##*:}"
[ -n "$TAG" ] || die "Could not determine image tag from container ${WEBAPP_CID} (${IMAGE_REF})."
export TAG
log "Rolling back to ${TARGET_COLOR} (${TARGET_PROJECT}) using previously-running tag=${TAG}"

if ! docker compose -p "$TARGET_PROJECT" --env-file ".env.${TARGET_COLOR}" -f "$SCRIPT_DIR/docker-compose.app.yml" up -d; then
    die "Failed to (re)start ${TARGET_COLOR}. Proxy left untouched."
fi

log "Waiting up to ${HEALTHY_TIMEOUT_SECONDS}s for ${TARGET_COLOR} to become healthy"
DEADLINE=$(( $(date +%s) + HEALTHY_TIMEOUT_SECONDS ))
for svc in nginx laravel-webapp predict-service; do
    CID="$(container_for "$svc")"
    [ -n "$CID" ] || die "Container for service '${svc}' not found in ${TARGET_PROJECT}. Proxy left untouched."
    while true; do
        STATUS="$(docker inspect -f '{{.State.Health.Status}}' "$CID" 2>/dev/null || echo unknown)"
        [ "$STATUS" = "healthy" ] && break
        if [ "$(date +%s)" -ge "$DEADLINE" ]; then
            die "Service '${svc}' did not become healthy within ${HEALTHY_TIMEOUT_SECONDS}s (status: ${STATUS}). Proxy left untouched."
        fi
        sleep 3
    done
    log "  ${svc}: healthy"
done

log "Smoke testing ${TARGET_COLOR} before switching traffic to it"
if ! "$SCRIPT_DIR/smoke_test.sh" "$TARGET_PROJECT"; then
    die "Smoke test failed for ${TARGET_COLOR}. Proxy left untouched, NOT switched."
fi

log "Switching proxy to ${TARGET_COLOR}"
"$SCRIPT_DIR/switch_proxy.sh" "$TARGET_COLOR"
log "Rollback complete. Active color is now ${TARGET_COLOR}."
