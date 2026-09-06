#!/usr/bin/env bash
# ======================================================================
# collect_run_metadata.sh — Gom provenance cho một lần chạy Lab 01
# ======================================================================
# Không ghi toàn bộ docker inspect vì có thể chứa HF_TOKEN hoặc biến bí mật.
# Chỉ lưu version, image digest/id, /v1/models, /metrics và log server.
# ======================================================================
set -u

PORT="${PORT:-8000}"
OUTPUT_ROOT="${OUTPUT_ROOT:-results/run_metadata}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT_DIR="${OUTPUT_ROOT}/${TIMESTAMP}"
CONTAINER_NAME="${CONTAINER_NAME:-}"

mkdir -p "${OUTPUT_DIR}"

if [ -z "${CONTAINER_NAME}" ] && command -v docker >/dev/null 2>&1; then
    CONTAINER_NAME="$(docker ps -a --filter "name=vllm-lab01" --format '{{.Names}}' | head -n 1)"
fi

{
    echo "timestamp=${TIMESTAMP}"
    echo "port=${PORT}"
    echo "container_name=${CONTAINER_NAME:-UNAVAILABLE}"
    echo "model_id=${MODEL_ID:-UNSET}"
    echo "vllm_image=${VLLM_IMAGE:-UNSET}"
    echo "max_model_len=${MAX_MODEL_LEN:-UNSET}"
    echo "gpu_memory_utilization=${GPU_MEMORY_UTILIZATION:-UNSET}"
    echo "trust_remote_code=${TRUST_REMOTE_CODE:-0}"
    echo
    if command -v python3 >/dev/null 2>&1; then python3 --version 2>&1; else echo "python3=UNAVAILABLE"; fi
    if command -v nvidia-smi >/dev/null 2>&1; then nvidia-smi 2>&1; else echo "nvidia-smi=UNAVAILABLE"; fi
    if command -v docker >/dev/null 2>&1; then docker version 2>&1; else echo "docker=UNAVAILABLE"; fi
} > "${OUTPUT_DIR}/environment.txt"

if curl -fsS --connect-timeout 5 --max-time 15 "http://localhost:${PORT}/v1/models" > "${OUTPUT_DIR}/v1_models.json" 2>&1; then
    echo "v1_models=OK"
else
    echo "v1_models=UNAVAILABLE" >> "${OUTPUT_DIR}/environment.txt"
fi

if curl -fsS --connect-timeout 5 --max-time 15 "http://localhost:${PORT}/metrics" > "${OUTPUT_DIR}/metrics.txt" 2>&1; then
    echo "metrics=OK"
else
    echo "metrics=UNAVAILABLE" >> "${OUTPUT_DIR}/environment.txt"
fi

if [ -n "${CONTAINER_NAME}" ] && command -v docker >/dev/null 2>&1; then
    docker inspect --format 'image={{.Config.Image}} image_id={{.Image}}' "${CONTAINER_NAME}" > "${OUTPUT_DIR}/container_image.txt" 2>&1 || echo "container_image=UNAVAILABLE" > "${OUTPUT_DIR}/container_image.txt"
    docker logs --tail 500 "${CONTAINER_NAME}" > "${OUTPUT_DIR}/server.log" 2>&1 || echo "server_log=UNAVAILABLE" > "${OUTPUT_DIR}/server.log"
else
    echo "container_image=UNAVAILABLE" > "${OUTPUT_DIR}/container_image.txt"
    echo "server_log=UNAVAILABLE" > "${OUTPUT_DIR}/server.log"
fi

echo "Metadata lưu tại: ${OUTPUT_DIR}"
