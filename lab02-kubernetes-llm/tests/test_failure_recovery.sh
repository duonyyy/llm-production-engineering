#!/usr/bin/env bash
set -euo pipefail

if [[ "${CONFIRM_FAILURE_TEST:-}" != "YES" ]]; then
  echo "Refusing destructive lab test. Set CONFIRM_FAILURE_TEST=YES on a non-production lab cluster." >&2
  exit 1
fi

NS="lab02-kubernetes-llm"
KUBECTL=(kubectl)
if [[ -n "${KUBE_CONTEXT:-}" ]]; then KUBECTL+=(--context "${KUBE_CONTEXT}"); fi

pod="$("${KUBECTL[@]}" -n "${NS}" get pods \
  -l serving.kserve.io/inferenceservice=lab02-vllm \
  -o jsonpath='{.items[0].metadata.name}')"
[[ -n "${pod}" ]] || { echo "No predictor pod found" >&2; exit 1; }

before="$(date +%s)"
echo "Deleting ${pod}; save current readiness/traffic evidence before this command."
"${KUBECTL[@]}" -n "${NS}" delete pod "${pod}" --wait=false
"${KUBECTL[@]}" -n "${NS}" wait --for=condition=Ready pod -l serving.kserve.io/inferenceservice=lab02-vllm --timeout=600s
after="$(date +%s)"

echo "recovery_seconds=$((after - before))"
"${KUBECTL[@]}" -n "${NS}" get pods -l serving.kserve.io/inferenceservice=lab02-vllm -o wide
echo "Correlate this timestamp with failed requests, retries, readiness and SLO impact in the report."
