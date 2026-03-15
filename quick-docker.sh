#!/usr/bin/env bash
# Quick Docker runner (Linux/macOS)
# Wrapper for deploy.sh with short commands.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_SCRIPT="${SCRIPT_DIR}/deploy.sh"

if [[ ! -f "${DEPLOY_SCRIPT}" ]]; then
    echo "Error: deploy.sh not found at ${DEPLOY_SCRIPT}"
    exit 1
fi

usage() {
    cat <<'EOF'
Usage: ./quick-docker.sh [command]

Commands:
  up       Start services (default)
  fresh    Fresh deploy (reset DB/volumes)
  build    Rebuild images (no cache)
  stop     Stop containers
  restart  Restart containers
  logs     Follow logs
  help     Show this help
EOF
}

cmd="${1:-up}"

case "${cmd}" in
    up)
        bash "${DEPLOY_SCRIPT}"
        ;;
    fresh)
        bash "${DEPLOY_SCRIPT}" --fresh
        ;;
    build)
        bash "${DEPLOY_SCRIPT}" --build
        ;;
    stop)
        bash "${DEPLOY_SCRIPT}" --stop
        ;;
    restart)
        bash "${DEPLOY_SCRIPT}" --restart
        ;;
    logs)
        bash "${DEPLOY_SCRIPT}" --logs
        ;;
    help|-h|--help)
        usage
        ;;
    *)
        echo "Unknown command: ${cmd}"
        usage
        exit 1
        ;;
esac
