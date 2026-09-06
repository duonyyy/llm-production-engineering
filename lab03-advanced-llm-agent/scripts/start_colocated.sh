#!/usr/bin/env bash
set -euo pipefail

MODEL_ID="${MODEL_ID:-Qwen/Qwen2.5-0.5B-Instruct}"
PORT="${COLOCATED_PORT:-8000}"
CONTAINER="${LAB03_COLOCATED_CONTAINER:-lab03-colocated}"
IMAGE="${VLLM_IMAGE_COLOCATED:-vllm/vllm-openai:v0.8.3}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-2048}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.72}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is unavailable; no colocated server was started." >&2
  exit 2
fi
if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is unavailable; no colocated server was started." >&2
  exit 2
fi

docker rm -f "${CONTAINER}" >/dev/null 2>&1 || true
docker run --rm -d --name "${CONTAINER}" \
  --gpus 'device=0' \
  --shm-size 2g \
  -p "127.0.0.1:${PORT}:8000" \
  "${IMAGE}" "${MODEL_ID}" \
  --host 0.0.0.0 \
  --port 8000 \
  --max-model-len "${MAX_MODEL_LEN}" \
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION}" \
  --max-num-seqs 1

echo "Started ${CONTAINER}; collect /v1/models and /metrics before benchmarking."
