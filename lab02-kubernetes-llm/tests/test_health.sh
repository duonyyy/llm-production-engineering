#!/usr/bin/env bash
set -euo pipefail

NS="lab02-kubernetes-llm"
KUBECTL=(kubectl)
if [[ -n "${KUBE_CONTEXT:-}" ]]; then KUBECTL+=(--context "${KUBE_CONTEXT}"); fi

if [[ -n "${INFERENCE_URL:-}" ]]; then
  curl --fail --silent --show-error "${INFERENCE_URL%/}/health"
  echo "health endpoint OK"
  exit 0
fi

"${KUBECTL[@]}" -n "${NS}" get inferenceservice lab02-vllm
"${KUBECTL[@]}" -n "${NS}" get pods -l serving.kserve.io/inferenceservice=lab02-vllm -o wide
echo "For a data-plane check, set INFERENCE_URL to the reachable vLLM /health endpoint."
