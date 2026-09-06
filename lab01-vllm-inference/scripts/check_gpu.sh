#!/usr/bin/env bash
# ==============================================================================
# check_gpu.sh — Kiểm tra GPU và môi trường trước khi chạy Lab
# ==============================================================================
set -euo pipefail

echo "============================================="
echo "  LAB 01 — GPU & Environment Check"
echo "============================================="
echo ""

# --- 1. Kiểm tra nvidia-smi ---
echo "[1/5] Kiểm tra nvidia-smi..."
if ! command -v nvidia-smi &>/dev/null; then
    echo "  ✗ nvidia-smi không tìm thấy. Cài NVIDIA Driver trước."
    exit 1
fi
nvidia-smi --query-gpu=index,name,driver_version,memory.total,memory.free,temperature.gpu \
    --format=csv,noheader,nounits | while IFS=',' read -r idx name driver mem_total mem_free temp; do
    echo "  GPU $idx: $name"
    echo "    Driver : $driver"
    echo "    VRAM   : ${mem_free}MB free / ${mem_total}MB total"
    echo "    Temp   : ${temp}°C"
done
echo ""

# --- 2. Kiểm tra CUDA ---
echo "[2/5] Kiểm tra CUDA version..."
if command -v nvcc &>/dev/null; then
    nvcc --version | grep "release" || true
else
    echo "  nvcc không có trên PATH (có thể chạy qua Docker, bỏ qua)."
fi
echo ""

# --- 3. Kiểm tra Docker ---
echo "[3/5] Kiểm tra Docker..."
if command -v docker &>/dev/null; then
    docker --version
else
    echo "  ✗ Docker không tìm thấy."
    exit 1
fi
echo ""

# --- 4. Kiểm tra NVIDIA Container Toolkit ---
echo "[4/5] Kiểm tra GPU trong Docker container..."
if docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu22.04 nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null; then
    echo "  ✓ Docker thấy GPU."
else
    echo "  ✗ Docker không thấy GPU. Kiểm tra NVIDIA Container Toolkit."
    echo "    Xem: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
    exit 1
fi
echo ""

# --- 5. Tóm tắt VRAM ---
echo "[5/5] Tóm tắt VRAM budget..."
echo ""
echo "  VRAM được sử dụng cho:"
echo "    Model weights"
echo "    + KV Cache (phụ thuộc concurrency & context length)"
echo "    + Runtime workspace"
echo "    + Batching / concurrency overhead"
echo ""
echo "  Profile RTX 3050 4GB: model 0.5B, MAX_MODEL_LEN=4096, GPU_MEMORY_UTILIZATION=0.80"
echo "  Benchmark an toàn: concurrency <= 4, output <= 64 tokens"
echo "  Khuyến nghị: >= 16GB VRAM cho model 7B FP16/BF16"
echo ""

echo "============================================="
echo "  ✓ Pre-flight check hoàn tất."
echo "============================================="
