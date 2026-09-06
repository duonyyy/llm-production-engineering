#!/usr/bin/env bash
# ==============================================================================
# start_vllm.sh — Khởi động vLLM server baseline (Prefix Cache OFF)
# ==============================================================================
# Cách dùng:
#   export MODEL_ID="Qwen/Qwen2.5-0.5B-Instruct"  # profile mặc định cho RTX 3050 4GB
#   export PORT=8000
#   bash scripts/start_vllm.sh
# ==============================================================================
set -euo pipefail

# --- Tham số cấu hình ---
MODEL_ID="${MODEL_ID:?Cần export MODEL_ID trước khi chạy. Ví dụ: export MODEL_ID=Qwen/Qwen2.5-0.5B-Instruct}"
PORT="${PORT:-8000}"

# Pin image version cụ thể để đảm bảo tính tái lập (Reproducibility).
# Có thể override bằng: export VLLM_IMAGE="vllm/vllm-openai:v0.8.3"
VLLM_IMAGE="${VLLM_IMAGE:-vllm/vllm-openai:v0.8.3}"
CONTAINER_NAME="${CONTAINER_NAME:-vllm-lab01-baseline}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.80}"
HF_CACHE_DIR="${HF_HOME:-${HOME}/.cache/huggingface}"
TRUST_REMOTE_CODE="${TRUST_REMOTE_CODE:-0}"

TRUST_REMOTE_CODE_ARGS=()
if [ "${TRUST_REMOTE_CODE}" = "1" ]; then
    TRUST_REMOTE_CODE_ARGS+=(--trust-remote-code)
fi

echo "================================================================"
echo "  KHỞI ĐỘNG vLLM BASELINE SERVER (Prefix Cache: OFF)"
echo "  Model       : ${MODEL_ID}"
echo "  Port        : ${PORT}"
echo "  Image       : ${VLLM_IMAGE}"
echo "  Max Context : ${MAX_MODEL_LEN} tokens"
echo "  GPU Mem Util: ${GPU_MEMORY_UTILIZATION}"
echo "  HF Cache    : ${HF_CACHE_DIR}"
echo "================================================================"

# Tạo thư mục cache nếu chưa có
mkdir -p "${HF_CACHE_DIR}"

# Dừng container cũ nếu đang chạy
docker rm -f "${CONTAINER_NAME}" 2>/dev/null || true

# Khởi động vLLM container
# Lưu ý: Mount cache volume giúp tái sử dụng trọng số mô hình đã tải, không tải lại qua mạng.
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
    "${TRUST_REMOTE_CODE_ARGS[@]}" \
    --disable-log-requests

echo ""
echo "✓ Container '${CONTAINER_NAME}' đã được tạo và đang chạy ở background."
echo "  Theo dõi log tải mô hình: docker logs -f ${CONTAINER_NAME}"
echo ""

# Chờ server sẵn sàng với polling loop
echo "Đang chờ server sẵn sàng (timeout 300s)..."
TIMEOUT=300
ELAPSED=0
INTERVAL=5
while [ $ELAPSED -lt $TIMEOUT ]; do
    if curl -s "http://localhost:${PORT}/v1/models" >/dev/null 2>&1; then
        echo ""
        echo "================================================================"
        echo "✓ vLLM SERVER ĐÃ SẴN SÀNG TẠI: http://localhost:${PORT}"
        echo "================================================================"
        echo "Kiểm tra nhanh:"
        echo "  curl http://localhost:${PORT}/v1/models | jq ."
        echo "  curl http://localhost:${PORT}/metrics | head -20"
        exit 0
    fi

    # Kiểm tra xem container có bị chết giữa chừng không (ví dụ OOM hoặc lỗi tải weights)
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo ""
        echo "✗ Container '${CONTAINER_NAME}' đã dừng bất thường!"
        echo "--- 30 dòng log cuối cùng: ---"
        docker logs --tail 30 "${CONTAINER_NAME}"
        exit 1
    fi

    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
    echo "  ...đang chờ (${ELAPSED}s / ${TIMEOUT}s)"
done

echo ""
echo "✗ Timeout — server chưa sẵn sàng sau ${TIMEOUT}s."
echo "  Kiểm tra log: docker logs --tail 50 ${CONTAINER_NAME}"
exit 1
