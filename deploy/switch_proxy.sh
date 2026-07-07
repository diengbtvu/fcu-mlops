#!/usr/bin/env bash
# Switch the edge proxy's active upstream to <blue|green>.
#
# Critical detail: active-upstream.caddy is bind-mounted into the proxy container as a
# single file (inode-based bind mount). We must overwrite its CONTENT in place with
# `printf > file`. We must NEVER `mv` a replacement file over it (or write-then-rename) -
# that swaps the inode, and the container's bind mount keeps pointing at the OLD inode,
# so `caddy reload` would silently keep serving the old upstream forever.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[switch_proxy]${NC} $*"; }
warn() { echo -e "${YELLOW}[switch_proxy]${NC} $*"; }
die()  { echo -e "${RED}[switch_proxy] ERROR:${NC} $*" >&2; exit 1; }

# The edge proxy is NOT a dedicated stack of ours - this server already runs one shared
# Caddy (project "aura-content", container "aura-caddy") on ports 80/443 for several
# unrelated domains. zettix.net is one more server block in ITS Caddyfile
# (/root/aura-content/Caddyfile), and that container is joined to our hydrogen_net so it
# can resolve frontend-<color>. See deploy/README.md.
PROXY_CONTAINER_NAME="${PROXY_CONTAINER_NAME:-aura-caddy}"
UPSTREAM_FILE="${UPSTREAM_FILE:-$SCRIPT_DIR/active-upstream.caddy}"
ACTIVE_COLOR_FILE="${ACTIVE_COLOR_FILE:-$SCRIPT_DIR/.active-color}"

TARGET_COLOR="${1:-}"
case "$TARGET_COLOR" in
    blue|green) ;;
    *) die "Usage: $0 <blue|green> (got: '${TARGET_COLOR}')" ;;
esac

PROXY_CONTAINER="$(docker ps -q --filter "name=^${PROXY_CONTAINER_NAME}$")"
[ -n "$PROXY_CONTAINER" ] || die "Proxy container '${PROXY_CONTAINER_NAME}' not found/running."

[ -f "$UPSTREAM_FILE" ] || die "Upstream file not found: $UPSTREAM_FILE"
PREVIOUS_CONTENT="$(cat "$UPSTREAM_FILE")"

log "Switching upstream -> frontend-${TARGET_COLOR}:80 (previous: ${PREVIOUS_CONTENT})"

# Overwrite content in place. This truncates+writes the existing inode; it does not
# create a new file, so the bind mount in the running container sees the new bytes
# immediately.
printf 'to frontend-%s:80\n' "$TARGET_COLOR" > "$UPSTREAM_FILE"

restore_previous() {
    warn "Restoring previous upstream content and aborting switch."
    printf '%s\n' "$PREVIOUS_CONTENT" > "$UPSTREAM_FILE"
}

if ! docker exec "$PROXY_CONTAINER" caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile; then
    restore_previous
    die "caddy validate failed, chưa switch, màu cũ (${PREVIOUS_CONTENT}) vẫn đang nhận traffic."
fi

if ! docker exec "$PROXY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile; then
    restore_previous
    # Best-effort: try to reload back to the restored content too, so runtime state
    # matches the file we just restored.
    docker exec "$PROXY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile || true
    die "caddy reload failed, chưa switch, màu cũ (${PREVIOUS_CONTENT}) vẫn đang nhận traffic."
fi

printf '%s\n' "$TARGET_COLOR" > "$ACTIVE_COLOR_FILE"
log "Switched successfully. Active color is now: ${TARGET_COLOR}"
