#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "${ROOT_DIR}/results"

URL="${INFERENCE_URL:-http://127.0.0.1:8080/v1/chat/completions}"
MODEL="${MODEL_ID:-Qwen/Qwen2.5-0.5B-Instruct}"
CONCURRENCY="${CONCURRENCY:-1}"
REQUESTS="${REQUESTS:-5}"
MAX_TOKENS="${MAX_TOKENS:-64}"
OUTPUT="${OUTPUT:-${ROOT_DIR}/results/c${CONCURRENCY}.csv}"

python3 "${ROOT_DIR}/benchmark/load_generator.py" \
  --url "${URL}" \
  --model "${MODEL}" \
  --input-file "${ROOT_DIR}/benchmark/workload.jsonl" \
  --concurrency "${CONCURRENCY}" \
  --requests "${REQUESTS}" \
  --max-tokens "${MAX_TOKENS}" \
  --output "${OUTPUT}" \
  "$@"
