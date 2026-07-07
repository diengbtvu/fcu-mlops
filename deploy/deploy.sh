#!/usr/bin/env bash
# Blue/green deploy orchestrator. Runs ON THE SERVER (invoked over SSH by CI, or by hand).
#
#   deploy/deploy.sh prod <tag>
#
# Any failure before step 9 (switch) leaves the currently-active color completely
# untouched and still serving traffic. See deploy/README.md for the full picture.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${GREEN}[deploy]${NC} $*"; }
warn() { echo -e "${YELLOW}[deploy]${NC} $*"; }
die()  { echo -e "${RED}[deploy] ERROR:${NC} $*" >&2; exit 1; }

APP_SLUG="${APP_SLUG:-hydrogen}"
DOMAIN="${DOMAIN:-zettix.net}"
DB_PROJECT="${DB_PROJECT:-${APP_SLUG}-db}"
KEEP_BACKUPS="${KEEP_BACKUPS:-10}"
DRAIN_SECONDS="${DRAIN_SECONDS:-300}"
HEALTHY_TIMEOUT_SECONDS="${HEALTHY_TIMEOUT_SECONDS:-120}"

LOCK_FILE="$SCRIPT_DIR/.deploy.lock"
BACKUP_DIR="$SCRIPT_DIR/backups"
LOG_DIR="$SCRIPT_DIR/logs"
ACTIVE_COLOR_FILE="$SCRIPT_DIR/.active-color"
mkdir -p "$BACKUP_DIR" "$LOG_DIR"

# ---------------------------------------------------------------------------
# Args
# ---------------------------------------------------------------------------
ENVIRONMENT="${1:-}"
TAG="${2:-}"
[ "$ENVIRONMENT" = "prod" ] || die "Usage: $0 prod <tag>"
[ -n "$TAG" ] || die "Usage: $0 prod <tag>"

read_env_var() {
    local file="$1" key="$2"
    [ -f "$file" ] || return 0
    grep -E "^${key}=" "$file" | tail -n1 | cut -d'=' -f2-
}

compose_app() {
    local project="$1" color="$2"; shift 2
    TAG="$TAG" docker compose -p "$project" --env-file ".env.${color}" -f "$SCRIPT_DIR/docker-compose.app.yml" "$@"
}

container_for() {
    local project="$1" service="$2"
    docker ps -q \
        --filter "label=com.docker.compose.project=${project}" \
        --filter "label=com.docker.compose.service=${service}" \
        | head -n1
}

# ---------------------------------------------------------------------------
# Step 1: lock (prevent two overlapping deploys)
# ---------------------------------------------------------------------------
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    die "Another deploy is already running (lock held: ${LOCK_FILE}). Nothing changed, try again once it finishes."
fi
log "Lock acquired. Deploying tag=${TAG}"

# ---------------------------------------------------------------------------
# Step 2: preflight resources
# ---------------------------------------------------------------------------
log "Step 2/11: preflight resource check"
"$SCRIPT_DIR/preflight_resources.sh"

# ---------------------------------------------------------------------------
# Step 3: read active color
# ---------------------------------------------------------------------------
[ -f "$ACTIVE_COLOR_FILE" ] || printf 'blue\n' > "$ACTIVE_COLOR_FILE"
ACTIVE_COLOR="$(tr -d '[:space:]' < "$ACTIVE_COLOR_FILE")"
case "$ACTIVE_COLOR" in
    blue)  IDLE_COLOR=green ;;
    green) IDLE_COLOR=blue ;;
    *) die "Invalid content in ${ACTIVE_COLOR_FILE}: '${ACTIVE_COLOR}' (expected blue|green). Nothing changed." ;;
esac
ACTIVE_PROJECT="${APP_SLUG}-${ACTIVE_COLOR}"
IDLE_PROJECT="${APP_SLUG}-${IDLE_COLOR}"
log "Step 3/11: active=${ACTIVE_COLOR} (${ACTIVE_PROJECT}), idle=${IDLE_COLOR} (${IDLE_PROJECT})"

[ -f "$SCRIPT_DIR/.env.${IDLE_COLOR}" ] || die "$SCRIPT_DIR/.env.${IDLE_COLOR} not found. Bootstrap it first (see README). Nothing changed, ${ACTIVE_COLOR} still serving."

# ---------------------------------------------------------------------------
# Step 4: backup DB before touching anything
# ---------------------------------------------------------------------------
log "Step 4/11: backing up database"
MYSQL_CONTAINER="$(container_for "$DB_PROJECT" mysql)"
[ -n "$MYSQL_CONTAINER" ] || die "Shared MySQL container not found (project=${DB_PROJECT}). Nothing changed, ${ACTIVE_COLOR} still serving."

DB_NAME="$(read_env_var "$SCRIPT_DIR/.env.${IDLE_COLOR}" DB_DATABASE)"
MYSQL_ROOT_PASSWORD="$(read_env_var "$SCRIPT_DIR/.env.db" MYSQL_ROOT_PASSWORD)"
[ -n "$DB_NAME" ] || die "DB_DATABASE missing from .env.${IDLE_COLOR}. Nothing changed, ${ACTIVE_COLOR} still serving."
[ -n "$MYSQL_ROOT_PASSWORD" ] || die "MYSQL_ROOT_PASSWORD missing from .env.db. Nothing changed, ${ACTIVE_COLOR} still serving."

TIMESTAMP="$(date +%Y%m%d%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/${APP_SLUG}_predeploy_${TIMESTAMP}.sql.gz"
# Ephemeral/queue/cache tables: high churn, no business value in a pre-deploy safety
# backup, and they bloat the dump considerably.
EXCLUDE_TABLES=(cache cache_locks sessions jobs failed_jobs job_batches)
IGNORE_ARGS=()
for t in "${EXCLUDE_TABLES[@]}"; do
    IGNORE_ARGS+=(--ignore-table="${DB_NAME}.${t}")
done

if ! docker exec -e MYSQL_PWD="$MYSQL_ROOT_PASSWORD" "$MYSQL_CONTAINER" \
        mysqldump -u root "${IGNORE_ARGS[@]}" --single-transaction --quick "$DB_NAME" \
        | gzip > "$BACKUP_FILE"; then
    rm -f "$BACKUP_FILE"
    die "DB backup failed. Nothing changed, ${ACTIVE_COLOR} still serving."
fi
log "Backup written: ${BACKUP_FILE} ($(du -h "$BACKUP_FILE" | cut -f1))"

# ---------------------------------------------------------------------------
# Step 5: migrations (backward-compatible, idempotent - see README)
# ---------------------------------------------------------------------------
if [ -x "$SCRIPT_DIR/migrate.sh" ]; then
    log "Step 5/11: running migrations against shared DB (using ${IDLE_COLOR} image)"
    if ! "$SCRIPT_DIR/migrate.sh" "$IDLE_COLOR" "$TAG"; then
        die "Migration failed. Chưa switch, ${ACTIVE_COLOR} vẫn sống. Idle color chưa được start."
    fi
else
    warn "Step 5/11: no migrate.sh found, skipping migrations."
fi

# ---------------------------------------------------------------------------
# Step 6: pull + up idle color
# ---------------------------------------------------------------------------
log "Step 6/11: pulling and starting ${IDLE_COLOR} (${IDLE_PROJECT})"
if ! compose_app "$IDLE_PROJECT" "$IDLE_COLOR" pull; then
    die "Pull failed for ${IDLE_COLOR}. Chưa switch, ${ACTIVE_COLOR} vẫn sống."
fi
if ! compose_app "$IDLE_PROJECT" "$IDLE_COLOR" up -d --remove-orphans; then
    die "Failed to start ${IDLE_COLOR}. Chưa switch, ${ACTIVE_COLOR} vẫn sống. Kiểm tra: docker compose -p ${IDLE_PROJECT} logs"
fi

# ---------------------------------------------------------------------------
# Step 7: wait for idle color to report healthy
# ---------------------------------------------------------------------------
log "Step 7/11: waiting up to ${HEALTHY_TIMEOUT_SECONDS}s for ${IDLE_COLOR} containers to become healthy"
SERVICES=(nginx laravel-webapp predict-service)
DEADLINE=$(( $(date +%s) + HEALTHY_TIMEOUT_SECONDS ))
for svc in "${SERVICES[@]}"; do
    CID="$(container_for "$IDLE_PROJECT" "$svc")"
    [ -n "$CID" ] || { compose_app "$IDLE_PROJECT" "$IDLE_COLOR" down; die "Container for service '${svc}' not found in ${IDLE_PROJECT}. Idle color torn down, ${ACTIVE_COLOR} vẫn sống."; }
    while true; do
        STATUS="$(docker inspect -f '{{.State.Health.Status}}' "$CID" 2>/dev/null || echo "unknown")"
        [ "$STATUS" = "healthy" ] && break
        if [ "$(date +%s)" -ge "$DEADLINE" ]; then
            compose_app "$IDLE_PROJECT" "$IDLE_COLOR" down
            die "Service '${svc}' did not become healthy within ${HEALTHY_TIMEOUT_SECONDS}s (last status: ${STATUS}). Idle color torn down, ${ACTIVE_COLOR} vẫn sống."
        fi
        sleep 3
    done
    log "  ${svc}: healthy"
done

# ---------------------------------------------------------------------------
# Step 8: smoke test idle color directly (not through the proxy - it has no traffic yet)
# ---------------------------------------------------------------------------
log "Step 8/11: smoke testing ${IDLE_COLOR}"
if ! "$SCRIPT_DIR/smoke_test.sh" "$IDLE_PROJECT"; then
    compose_app "$IDLE_PROJECT" "$IDLE_COLOR" down
    die "Smoke test failed for ${IDLE_COLOR}. Idle color torn down, ${ACTIVE_COLOR} vẫn sống, chưa switch."
fi

# ---------------------------------------------------------------------------
# Step 9: switch proxy to idle color
# ---------------------------------------------------------------------------
log "Step 9/11: switching proxy traffic to ${IDLE_COLOR}"
if ! "$SCRIPT_DIR/switch_proxy.sh" "$IDLE_COLOR"; then
    compose_app "$IDLE_PROJECT" "$IDLE_COLOR" down
    die "Switch failed. Idle color torn down, ${ACTIVE_COLOR} vẫn sống."
fi

# ---------------------------------------------------------------------------
# Step 10: verify through real traffic path (host -> proxy -> new color), auto-rollback
# ---------------------------------------------------------------------------
log "Step 10/11: verifying via public path (https://${DOMAIN}/health)"
sleep 2
HTTP_CODE="$(curl -sk --max-time 10 --resolve "${DOMAIN}:443:127.0.0.1" -o /dev/null -w '%{http_code}' "https://${DOMAIN}/health" || echo "000")"
if [ "$HTTP_CODE" != "200" ]; then
    warn "Public verification failed (got HTTP ${HTTP_CODE}). AUTO-ROLLBACK: switching back to ${ACTIVE_COLOR}."
    "$SCRIPT_DIR/switch_proxy.sh" "$ACTIVE_COLOR" || warn "Rollback switch also failed! Manual intervention required: deploy/switch_proxy.sh ${ACTIVE_COLOR}"
    die "AUTO-ROLLBACK done: proxy back on ${ACTIVE_COLOR}. ${IDLE_COLOR} (${IDLE_PROJECT}) left RUNNING for debugging - inspect then 'docker compose -p ${IDLE_PROJECT} logs' / down it manually."
fi
log "Public verification OK (HTTP ${HTTP_CODE})."

# ---------------------------------------------------------------------------
# Step 11: drain window, then stop old color + cleanup (backgrounded, lock released)
# ---------------------------------------------------------------------------
log "Step 11/11: scheduling drain window (${DRAIN_SECONDS}s) before stopping ${ACTIVE_COLOR}"
DRAIN_LOG="$LOG_DIR/drain_${TIMESTAMP}.log"
REGISTRY_VAL="$(read_env_var "$SCRIPT_DIR/.env.${IDLE_COLOR}" REGISTRY)"
IMAGE_PREFIX_VAL="$(read_env_var "$SCRIPT_DIR/.env.${IDLE_COLOR}" IMAGE_PREFIX)"
IMAGE_PREFIX_VAL="${IMAGE_PREFIX_VAL:-fcu-mlops}"
nohup bash -c "
    exec 9>&-
    sleep '${DRAIN_SECONDS}'
    echo \"[drain] stopping old color ${ACTIVE_COLOR} (${ACTIVE_PROJECT})\"
    TAG='${TAG}' docker compose -p '${ACTIVE_PROJECT}' --env-file '.env.${ACTIVE_COLOR}' -f '${SCRIPT_DIR}/docker-compose.app.yml' stop
    docker image prune -f >/dev/null 2>&1 || true
    # Old tagged images (not just dangling ones) pile up fast - predict-service alone is
    # ~8GB per tag. Remove every tag except the one just deployed; docker itself refuses
    # to remove a tag still referenced by an existing (even stopped) container, so this
    # naturally leaves the previous color's image alone until IT is deployed over too.
    for svc in frontend webapp predict; do
        docker images \"${REGISTRY_VAL}/${IMAGE_PREFIX_VAL}-\${svc}\" --format '{{.Tag}}' | while read -r old_tag; do
            [ \"\$old_tag\" = '${TAG}' ] && continue
            docker rmi \"${REGISTRY_VAL}/${IMAGE_PREFIX_VAL}-\${svc}:\$old_tag\" >/dev/null 2>&1 || true
        done
    done
    ls -1t '${BACKUP_DIR}'/${APP_SLUG}_predeploy_*.sql.gz 2>/dev/null | tail -n +\$(( ${KEEP_BACKUPS} + 1 )) | xargs -r rm -f
    echo \"[drain] done\"
" >>"$DRAIN_LOG" 2>&1 &
disown

log "Deploy complete. Active color is now ${IDLE_COLOR}. Draining ${ACTIVE_COLOR} in background (log: ${DRAIN_LOG})."
