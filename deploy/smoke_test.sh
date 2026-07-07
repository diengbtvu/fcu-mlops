#!/usr/bin/env bash
# Smoke-test the idle color BEFORE it receives any proxy traffic. Every check runs via
# `docker exec` straight into the color's own containers - never through the edge proxy,
# since the proxy is still pointed at the other color at this point.
#
# Usage: smoke_test.sh <compose-project-name>
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[smoke_test]${NC} $*"; }
warn() { echo -e "${YELLOW}[smoke_test]${NC} $*"; }
die()  { echo -e "${RED}[smoke_test] ERROR:${NC} $*" >&2; exit 1; }

PROJECT="${1:-}"
[ -n "$PROJECT" ] || die "Usage: $0 <compose-project-name>"

container_for() {
    local service="$1"
    docker ps -q \
        --filter "label=com.docker.compose.project=${PROJECT}" \
        --filter "label=com.docker.compose.service=${service}" \
        | head -n1
}

NGINX_CONTAINER="$(container_for nginx)"
PREDICT_CONTAINER="$(container_for predict-service)"

[ -n "$NGINX_CONTAINER" ] || die "No running nginx container found for project '${PROJECT}'."
[ -n "$PREDICT_CONTAINER" ] || die "No running predict-service container found for project '${PROJECT}'."

FAILED=0

check_status() {
    local description="$1" container="$2" url="$3" expected="$4"
    local actual
    actual="$(docker exec "$container" curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$url" || echo "000")"
    if [ "$actual" = "$expected" ]; then
        log "OK   ${description} -> ${actual}"
    else
        echo -e "${RED}[smoke_test] FAIL ${description} -> got ${actual}, expected ${expected}${NC}" >&2
        FAILED=1
    fi
}

# Liveness
check_status "nginx  GET /api/health"        "$NGINX_CONTAINER"   "http://127.0.0.1/api/health"        200
check_status "predict GET /predict/health"   "$PREDICT_CONTAINER" "http://127.0.0.1:5000/predict/health" 200

# A couple of genuinely public pages/endpoints
check_status "nginx  GET /login"             "$NGINX_CONTAINER"   "http://127.0.0.1/login"             200

# Security check: protected endpoints must reject unauthenticated requests, not just
# "be alive". A 200 here would mean auth is broken, not that the service is healthier.
check_status "nginx  GET /api/user (no auth)" "$NGINX_CONTAINER"  "http://127.0.0.1/api/user"           401

if [ "$FAILED" -ne 0 ]; then
    die "Smoke test failed for project '${PROJECT}'. Idle color will be torn down; active color keeps serving traffic untouched."
fi

log "All smoke tests passed for project '${PROJECT}'."
