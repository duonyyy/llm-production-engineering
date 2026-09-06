#!/usr/bin/env bash
# ==============================================================================
# stop_server.sh — Dừng và dọn container vLLM
# ==============================================================================
# Dừng tất cả container Lab 01 hoặc container cụ thể.
# Cách dùng:
#   bash scripts/stop_server.sh                 # Dừng tất cả container lab01
#   bash scripts/stop_server.sh <container>     # Dừng container cụ thể
# ==============================================================================
set -euo pipefail

LAB_PREFIX="vllm-lab01"

if [ $# -ge 1 ]; then
    echo "Dừng container: $1"
    docker rm -f "$1" 2>/dev/null && echo "  ✓ Đã dừng." || echo "  Container không tồn tại."
else
    echo "Dừng tất cả container có prefix '${LAB_PREFIX}'..."
    CONTAINERS=$(docker ps -a --filter "name=${LAB_PREFIX}" --format '{{.Names}}' 2>/dev/null || true)
    if [ -z "$CONTAINERS" ]; then
        echo "  Không tìm thấy container nào."
    else
        for c in $CONTAINERS; do
            docker rm -f "$c" 2>/dev/null && echo "  ✓ Dừng: $c"
        done
    fi
fi

echo ""
echo "Lưu ý: Script này KHÔNG xóa model cache (~/.cache/huggingface)."
echo "Nếu muốn xóa thủ công: rm -rf ~/.cache/huggingface/hub/<model>"
