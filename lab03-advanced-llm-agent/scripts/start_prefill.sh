#!/usr/bin/env bash
set -euo pipefail

if [ "${LAB03_EXECUTE_LINUX:-no}" != "yes" ]; then
  echo "Refusing P/D start: set LAB03_EXECUTE_LINUX=yes in the intended Linux lab environment." >&2
  exit 2
fi
if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "Refusing P/D start: nvidia-smi is unavailable." >&2
  exit 2
fi
GPU_COUNT="$(nvidia-smi --query-gpu=index --format=csv,noheader | wc -l | tr -d ' ')"
if [ "${GPU_COUNT}" -lt 2 ]; then
  echo "Refusing P/D start: at least two visible GPUs are required; found ${GPU_COUNT}." >&2
  exit 2
fi

MODEL_ID="${MODEL_ID:-Qwen/Qwen2.5-0.5B-Instruct}"
IMAGE="${VLLM_IMAGE_PD:-vllm/vllm-openai:v0.23.0}"
CONTAINER="${LAB03_PREFILL_CONTAINER:-lab03-prefill}"
PORT="${PREFILL_PORT:-8101}"
CONFIG='{"kv_connector":"LMCacheMPConnector","kv_connector_module_path":"lmcache.integration.vllm.lmcache_mp_connector","kv_role":"kv_both","kv_connector_extra_config":{"lmcache.mp.host":"127.0.0.1","lmcache.mp.port":5555}}'

docker rm -f "${CONTAINER}" >/dev/null 2>&1 || true
docker run --rm -d --name "${CONTAINER}" --gpus 'device=0' --shm-size 2g \
  -p "127.0.0.1:${PORT}:8000" "${IMAGE}" "${MODEL_ID}" \
  --host 0.0.0.0 --port 8000 --max-model-len "${MAX_MODEL_LEN_PD:-4096}" \
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION_PD:-0.80}" \
  --kv-transfer-config "${CONFIG}"
echo "Started prefill worker ${CONTAINER}; this is not a production topology benchmark."
