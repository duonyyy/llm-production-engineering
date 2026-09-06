#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NS="lab02-kubernetes-llm"
KUBECTL=(kubectl)
if [[ -n "${KUBE_CONTEXT:-}" ]]; then KUBECTL+=(--context "${KUBE_CONTEXT}"); fi

if [[ "${DRY_RUN:-0}" == "1" ]]; then
  KUBECTL+=(apply --dry-run=client -f)
else
  KUBECTL+=(apply -f)
fi

for manifest in \
  namespace.yaml \
  rbac.yaml \
  inference-service.yaml \
  service-monitor.yaml \
  autoscaling.yaml \
  endpoint-picker-config.yaml \
  pod-disruption-budget.yaml \
  network-policy.yaml; do
  echo "Applying ${manifest}"
  "${KUBECTL[@]}" "${ROOT_DIR}/manifests/${manifest}"
done

echo "Applying monitoring/alerts.yaml"
"${KUBECTL[@]}" "${ROOT_DIR}/monitoring/alerts.yaml"

if [[ "${DRY_RUN:-0}" != "1" ]]; then
  "${KUBECTL[@]:0:${#KUBECTL[@]}-3}" -n "${NS}" get inferenceservice,pods,svc
fi
