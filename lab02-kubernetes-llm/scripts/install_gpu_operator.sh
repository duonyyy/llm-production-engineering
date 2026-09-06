#!/usr/bin/env bash
set -euo pipefail

GPU_OPERATOR_VERSION="${GPU_OPERATOR_VERSION:-v26.7.0}"
DRIVER_MODE="${DRIVER_MODE:-preinstalled}"

command -v helm >/dev/null 2>&1 || { echo "helm is required" >&2; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "kubectl is required" >&2; exit 1; }

if [[ -z "${KUBE_CONTEXT:-}" ]]; then
  echo "KUBE_CONTEXT must point to a reviewable Linux GPU cluster" >&2
  exit 1
fi

HELM_ARGS=(
  --namespace gpu-operator
  --create-namespace
  --version "${GPU_OPERATOR_VERSION#v}"
  --wait
)
if [[ "${DRIVER_MODE}" == "preinstalled" ]]; then
  HELM_ARGS+=(--set driver.enabled=false)
elif [[ "${DRIVER_MODE}" != "operator" ]]; then
  echo "DRIVER_MODE must be preinstalled or operator" >&2
  exit 1
fi

helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm repo update
helm upgrade --install gpu-operator nvidia/gpu-operator --kube-context "${KUBE_CONTEXT}" "${HELM_ARGS[@]}"

kubectl --context "${KUBE_CONTEXT}" -n gpu-operator get pods -o wide
kubectl --context "${KUBE_CONTEXT}" get nodes \
  -o custom-columns='NAME:.metadata.name,GPU_ALLOCATABLE:.status.allocatable.nvidia\.com/gpu,READY:.status.conditions[?(@.type=="Ready")].status'
