#!/usr/bin/env bash
# ==============================================================================
# start_vllm_offload.sh — Khởi động vLLM với CPU Weight Offload (nếu hỗ trợ)
# ==============================================================================
# ⚠️  Đây là CPU WEIGHT offload. Nó không phải multi-tier KV-cache offload.
#     CPU offload là tính năng phụ thuộc version vLLM và hardware.
#     Nếu flag không tồn tại trong version bạn dùng, bỏ qua thực nghiệm này
#     và ghi nhận trong báo cáo rằng tính năng chưa available.
#
#     Trước khi chạy, kiểm tra:
#       docker run --rm <vllm-image> --help | grep -i offload
# ==============================================================================
set -euo pipefail

MODEL_ID="${MODEL_ID:?Cần export MODEL_ID trước khi chạy.}"
PORT="${PORT:-8000}"
VLLM_IMAGE="${VLLM_IMAGE:-vllm/vllm-openai:v0.8.3}"
CONTAINER_NAME="${CONTAINER_NAME:-vllm-lab01-offload}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.80}"
CPU_OFFLOAD_GB="${CPU_OFFLOAD_GB:-1}"
HF_CACHE_DIR="${HF_HOME:-${HOME}/.cache/huggingface}"
TRUST_REMOTE_CODE="${TRUST_REMOTE_CODE:-0}"

TRUST_REMOTE_CODE_ARGS=()
if [ "${TRUST_REMOTE_CODE}" = "1" ]; then
    TRUST_REMOTE_CODE_ARGS+=(--trust-remote-code)
fi

echo "================================================================"
echo "  KHỞI ĐỘNG vLLM SERVER VỚI CPU WEIGHT OFFLOAD"
echo "  Model          : ${MODEL_ID}"
echo "  Port           : ${PORT}"
echo "  Image          : ${VLLM_IMAGE}"
echo "  CPU Offload GB : ${CPU_OFFLOAD_GB} GB"
echo "================================================================"

# Kiểm tra RAM máy chủ host trước khi cấp phát offload
if command -v free &>/dev/null; then
    AVAIL_RAM_GB=$(free -g | awk '/^Mem:/{print $7}')
    echo "  Host RAM còn trống: ~${AVAIL_RAM_GB} GB"
    if [ "$AVAIL_RAM_GB" -lt "$CPU_OFFLOAD_GB" ]; then
        echo "  ⚠ CẢNH BÁO: RAM host (${AVAIL_RAM_GB}GB) có thể không đủ cho CPU_OFFLOAD_GB (${CPU_OFFLOAD_GB}GB)!"
    fi
fi

mkdir -p "${HF_CACHE_DIR}"
docker rm -f "${CONTAINER_NAME}" 2>/dev/null || true

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
    --cpu-offload-gb "${CPU_OFFLOAD_GB}" \
    "${TRUST_REMOTE_CODE_ARGS[@]}" \
    --disable-log-requests

echo ""
echo "✓ Container '${CONTAINER_NAME}' đã khởi động (CPU Offload: ON)."
echo "  Theo dõi log: docker logs -f ${CONTAINER_NAME}"
echo ""

TIMEOUT=300
ELAPSED=0
INTERVAL=5
while [ $ELAPSED -lt $TIMEOUT ]; do
    if curl -s "http://localhost:${PORT}/v1/models" >/dev/null 2>&1; then
        echo "================================================================"
        echo "✓ vLLM SERVER (CPU WEIGHT OFFLOAD) SẴN SÀNG TẠI: http://localhost:${PORT}"
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

echo "✗ Timeout."
docker logs --tail 50 "${CONTAINER_NAME}"
exit 1
