#!/usr/bin/env bash
set -u

echo "LAB03 preflight (read-only)"
echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "host=$(hostname)"
echo "os=$(uname -a 2>/dev/null || echo unavailable)"
echo "python=$(python3 --version 2>&1 || echo unavailable)"
echo "docker=$(docker --version 2>&1 || echo unavailable)"
echo "nvidia_smi=$(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1 || echo unavailable)"

if command -v nvidia-smi >/dev/null 2>&1; then
  gpu_count="$(nvidia-smi --query-gpu=index --format=csv,noheader 2>/dev/null | wc -l | tr -d ' ')"
else
  gpu_count=0
fi
echo "gpu_count=${gpu_count}"
if [ "${gpu_count}" -lt 2 ]; then
  echo "P/D status=NOT_RUN: two compatible NVIDIA GPUs are required for a real two-process test."
else
  echo "P/D status=ELIGIBLE_FOR_LINUX_VALIDATION: still verify driver, CUDA, vLLM, LMCache, NIXL and topology."
fi

if [ "${LAB03_EXECUTE_LINUX:-no}" != "yes" ]; then
  echo "execution_gate=closed (set LAB03_EXECUTE_LINUX=yes only in the intended Linux environment)"
else
  echo "execution_gate=open"
fi

echo "The preflight is evidence collection only; it does not prove inference or KV transfer."
