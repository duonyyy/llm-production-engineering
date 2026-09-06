#!/usr/bin/env bash
# ==============================================================================
# collect_metrics.sh — Thu thập metrics từ vLLM /metrics endpoint
# ==============================================================================
# Cách dùng:
#   bash scripts/collect_metrics.sh                 # Một lần
#   bash scripts/collect_metrics.sh --watch 5       # Lặp mỗi 5 giây
# ==============================================================================
set -euo pipefail

PORT="${PORT:-8000}"
BASE_URL="http://localhost:${PORT}"
METRICS_URL="${BASE_URL}/metrics"
OUTPUT_DIR="results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="${OUTPUT_DIR}/metrics_${TIMESTAMP}.txt"

mkdir -p "${OUTPUT_DIR}"

collect_once() {
    echo "--- Metrics snapshot: $(date) ---"
    echo ""

    local raw
    raw=$(curl -s --connect-timeout 5 --max-time 10 "${METRICS_URL}" 2>&1) || {
        echo "✗ Không thể kết nối ${METRICS_URL}"
        return 1
    }

    echo "=== Nhóm metric chính ==="
    echo ""

    # Lọc các nhóm metric quan trọng cho Lab 01
    # ⚠️  Tên metric có thể thay đổi theo version vLLM.
    #     Kiểm tra output đầy đủ nếu không thấy kết quả.
    echo "--- Request state ---"
    echo "$raw" | grep -E "^vllm:(num_requests_running|num_requests_waiting|num_requests_swapped)" || echo "  (không tìm thấy; kiểm tra đúng major/version)"
    echo ""

    echo "--- Latency (histograms) ---"
    echo "$raw" | grep -E "^vllm:(time_to_first_token|time_per_output_token|inter_token_latency|e2e_request_latency|request_queue_time|request_prefill_time|request_decode_time)" | grep -v "bucket" | head -20 || echo "  (không tìm thấy; kiểm tra đúng major/version)"
    echo ""

    echo "--- KV Cache ---"
    echo "$raw" | grep -E "^vllm:(kv_cache_usage_perc|gpu_cache_usage_perc|cpu_cache_usage_perc)" || echo "  (không tìm thấy; v0.8.3 thường dùng gpu_cache_usage_perc)"
    echo ""

    echo "--- Prefix Cache ---"
    echo "$raw" | grep -E "^vllm:(prefix_cache_hits|prefix_cache_queries|gpu_prefix_cache_hit_rate|cpu_prefix_cache_hit_rate)" || echo "  (không tìm thấy; metric prefix thay đổi theo engine/version)"
    echo ""

    echo "--- Tokens ---"
    echo "$raw" | grep -E "^vllm:(prompt_tokens|prompt_tokens_total|generation_tokens|generation_tokens_total)" | grep -v "bucket" | head -10 || echo "  (không tìm thấy; kiểm tra đúng major/version)"
    echo ""

    # Lưu raw output
    echo "$raw" > "${OUTPUT_FILE}"
    echo "Raw metrics lưu tại: ${OUTPUT_FILE}"
}

# Parse arguments
if [ "${1:-}" = "--watch" ]; then
    INTERVAL="${2:-5}"
    echo "Chế độ watch: thu thập mỗi ${INTERVAL}s. Ctrl+C để dừng."
    echo ""
    while true; do
        collect_once
        echo ""
        sleep "${INTERVAL}"
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        OUTPUT_FILE="${OUTPUT_DIR}/metrics_${TIMESTAMP}.txt"
    done
else
    collect_once
fi
