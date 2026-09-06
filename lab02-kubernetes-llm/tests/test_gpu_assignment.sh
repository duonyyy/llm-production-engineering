#!/usr/bin/env bash
set -euo pipefail

NS="lab02-kubernetes-llm"
KUBECTL=(kubectl)
if [[ -n "${KUBE_CONTEXT:-}" ]]; then KUBECTL+=(--context "${KUBE_CONTEXT}"); fi

pods="$("${KUBECTL[@]}" -n "${NS}" get pods -l serving.kserve.io/inferenceservice=lab02-vllm -o name)"
[[ -n "${pods}" ]] || { echo "No KServe predictor pod found" >&2; exit 1; }

while IFS= read -r pod; do
  echo "== ${pod} =="
  "${KUBECTL[@]}" -n "${NS}" get "${pod}" -o jsonpath='{.status.phase}{"\n"}'
  "${KUBECTL[@]}" -n "${NS}" describe "${pod}" | rg -n "nvidia.com/gpu|Node:|State:|Ready|Reason" || true
done <<< "${pods}"

echo "This test proves assignment only from cluster output; absence of output is not zero GPU usage."
