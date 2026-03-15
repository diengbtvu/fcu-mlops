#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-.}"

# Legacy terms that must not exist in source content or filenames.
CONTENT_PATTERN='(schwann|viability|cell_viability|\bpsc\b)'
FILE_PATTERN='(schwann|viability|cell_viability|(^|[^a-z0-9])psc([^a-z0-9]|$))'

EXCLUDE_GLOBS=(
  "--glob" "!**/.git/**"
  "--glob" "!**/vendor/**"
  "--glob" "!**/node_modules/**"
  "--glob" "!**/__pycache__/**"
  "--glob" "!scripts/check-legacy-terms.sh"
)

echo "[1/2] Checking content for legacy terms..."
if rg -n -i -S "${EXCLUDE_GLOBS[@]}" "$CONTENT_PATTERN" "$ROOT_DIR"; then
  echo
  echo "Legacy content terms found. Please replace/remove them."
  exit 1
fi

echo "[2/2] Checking filenames for legacy terms..."
if find "$ROOT_DIR" -type f \
    | rg -i "$FILE_PATTERN" \
    | rg -v '/(\.git|vendor|node_modules|__pycache__)/'; then
  echo
  echo "Legacy filenames found. Please rename/remove them."
  exit 1
fi

echo "No legacy terms found in content or filenames."
