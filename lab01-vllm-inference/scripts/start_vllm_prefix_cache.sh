#!/usr/bin/env bash
# ==============================================================================
# start_vllm_prefix_cache.sh — Khởi động vLLM server VỚI Prefix Caching (APC)
# ==============================================================================
# So sánh A/B: chạy script này thay cho start_vllm.sh để bật Prefix Cache.
# Giữ mọi tham số khác cố định để đảm bảo so sánh công bằng.
# ==============================================================================
set -euo pipefail

MODEL_ID="${MODEL_ID:?Cần export MODEL_ID trước khi chạy.}"
PORT="${PORT:-8000}"
VLLM_IMAGE="${VLLM_IMAGE:-vllm/vllm-openai:v0.8.3}"
CONTAINER_NAME="${CONTAINER_NAME:-vllm-lab01-prefix-cache}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.80}"
HF_CACHE_DIR="${HF_HOME:-${HOME}/.cache/huggingface}"
TRUST_REMOTE_CODE="${TRUST_REMOTE_CODE:-0}"

TRUST_REMOTE_CODE_ARGS=()
if [ "${TRUST_REMOTE_CODE}" = "1" ]; then
    TRUST_REMOTE_CODE_ARGS+=(--trust-remote-code)
fi

echo "================================================================"
echo "  KHỞI ĐỘNG vLLM SERVER VỚI PREFIX CACHING (APC: ON)"
echo "  Model       : ${MODEL_ID}"
echo "  Port        : ${PORT}"
echo "  Image       : ${VLLM_IMAGE}"
echo "  Max Context : ${MAX_MODEL_LEN} tokens"
echo "  Flag bổ sung: --enable-prefix-caching"
echo "================================================================"

mkdir -p "${HF_CACHE_DIR}"
docker rm -f "${CONTAINER_NAME}" 2>/dev/null || true

# Điểm khác biệt duy nhất so với baseline: cờ --enable-prefix-caching
docker run -d \
    --name "${CONTAINER_NAME}" \
    --gpus all \
    --shm-size=2g \
    --ipc=host \
    -p "${PORT}:8000" \
    -v "${HF_CACHE_DIR}:/root/.cache/huggingface" \
    -e HF_TOKEN="${HF_TOKEN:-}" \
    "${VLLM_IMAGE}" \
    --model "${MODEL_ID}" \
    --max-model-len "${MAX_MODEL_LEN}" \
    --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION}" \
    --dtype auto \
    --enable-prefix-caching \
    "${TRUST_REMOTE_CODE_ARGS[@]}" \
    --disable-log-requests

echo ""
echo "✓ Container '${CONTAINER_NAME}' đã được tạo (Prefix Cache: ON)."
echo "  Theo dõi log: docker logs -f ${CONTAINER_NAME}"
echo ""

# Chờ server sẵn sàng
TIMEOUT=300
ELAPSED=0
INTERVAL=5
while [ $ELAPSED -lt $TIMEOUT ]; do
    if curl -s "http://localhost:${PORT}/v1/models" >/dev/null 2>&1; then
        echo "================================================================"
        echo "✓ vLLM SERVER (PREFIX CACHE ON) SẴN SÀNG TẠI: http://localhost:${PORT}"
        echo "================================================================"
        exit 0
    fi

    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo "✗ Container dừng bất thường!"
        docker logs --tail 30 "${CONTAINER_NAME}"
        exit 1
    fi

    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
    echo "  ...đang chờ (${ELAPSED}s / ${TIMEOUT}s)"
done

echo "✗ Timeout — server chưa sẵn sàng."
docker logs --tail 50 "${CONTAINER_NAME}"
exit 1
