#!/usr/bin/env bash
set -euo pipefail

if [[ "${CONFIRM_CLEANUP:-}" != "YES" ]]; then
  echo "Refusing cleanup. Set CONFIRM_CLEANUP=YES to delete only Lab 02 namespace/resources." >&2
  exit 1
fi

KUBECTL=(kubectl)
if [[ -n "${KUBE_CONTEXT:-}" ]]; then KUBECTL+=(--context "${KUBE_CONTEXT}"); fi

"${KUBECTL[@]}" delete namespace lab02-kubernetes-llm --ignore-not-found
echo "Deleted namespace lab02-kubernetes-llm. Operator/monitoring/KServe installations were left intact."
