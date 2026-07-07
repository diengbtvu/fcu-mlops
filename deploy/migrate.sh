#!/usr/bin/env bash
# Run database migrations using the NEW (idle) image, against the shared MySQL, before
# anything else about the idle color is started. Because the DB is shared between both
# colors, every migration must be additive/idempotent: the currently-active color keeps
# running old code against the same, now-migrated schema until the switch happens.
#
# Usage: migrate.sh <blue|green> <tag>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
log() { echo -e "${GREEN}[migrate]${NC} $*"; }
die() { echo -e "${RED}[migrate] ERROR:${NC} $*" >&2; exit 1; }

COLOR="${1:-}"
TAG="${2:-}"
case "$COLOR" in blue|green) ;; *) die "Usage: $0 <blue|green> <tag>" ;; esac
[ -n "$TAG" ] || die "Usage: $0 <blue|green> <tag>"

APP_SLUG="${APP_SLUG:-hydrogen}"
ENV_FILE="$SCRIPT_DIR/.env.${COLOR}"
[ -f "$ENV_FILE" ] || die "${ENV_FILE} not found."

PROJECT="${APP_SLUG}-${COLOR}"
export TAG

log "Pulling laravel-webapp:${TAG} for project ${PROJECT}"
docker compose -p "$PROJECT" --env-file "$ENV_FILE" -f "$SCRIPT_DIR/docker-compose.app.yml" pull laravel-webapp

log "Running migrations (one-off container, project ${PROJECT})"
docker compose -p "$PROJECT" --env-file "$ENV_FILE" -f "$SCRIPT_DIR/docker-compose.app.yml" \
    run --rm --no-deps laravel-webapp php artisan migrate --force --no-interaction

log "Migrations applied successfully."
