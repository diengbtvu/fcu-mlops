#!/usr/bin/env bash
# Rerun report benchmark inside the predict-service container.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# -lt 1 ]]; then
    echo "Usage: ./quick-benchmark.sh <report_id> [clean|resume]" >&2
    echo "Example: ./quick-benchmark.sh KNN_HPR_20260424 clean" >&2
    exit 2
fi

REPORT_ID="$1"
MODE="${2:-clean}"

if [[ ! "${REPORT_ID}" =~ ^[A-Za-z0-9_.-]+$ ]]; then
    echo "Invalid report id: ${REPORT_ID}" >&2
    exit 2
fi

if [[ "${MODE}" != "clean" && "${MODE}" != "resume" ]]; then
    echo "Usage: ./quick-benchmark.sh <report_id> [clean|resume]" >&2
    exit 2
fi

cd "${SCRIPT_DIR}"

echo "Checking benchmark env in predict-service..."
docker compose exec -T predict-service sh -lc \
    'printenv | grep -E "OLLAMA_BENCHMARK|BENCHMARK_LLM_CLIENT" | sort || true'

if [[ "${MODE}" == "clean" ]]; then
    echo "Removing old benchmark output for ${REPORT_ID}..."
    docker compose exec -T predict-service sh -lc \
        "rm -rf '/app/app/reports/${REPORT_ID}/benchmark_eval'"
fi

RESUME_FLAG=""
if [[ "${MODE}" == "resume" ]]; then
    RESUME_FLAG="--resume"
fi

echo "Running A/B/C benchmark for ${REPORT_ID} (${MODE})..."
docker compose exec -T predict-service sh -lc "
set -e
cd /app
BENCHMARK_LLM_CLIENT=ollama \
OLLAMA_BENCHMARK_DISABLE_THINKING=1 \
OLLAMA_BENCHMARK_JSON_NUM_PREDICT=4096 \
OLLAMA_BENCHMARK_GENERATION_NUM_PREDICT=2200 \
python scripts/run_benchmark.py \
  --bundle-path 'app/reports/${REPORT_ID}' \
  --output-dir 'app/reports/${REPORT_ID}/benchmark_eval' \
  --client ollama \
  --arms A,B,C \
  --conditions image_table_summary \
  --levels L1,L2L3,L1L2L3 \
  ${RESUME_FLAG}
"

echo "Benchmark finished for ${REPORT_ID}."
