#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTEXT_ARGS=()
if [[ -n "${KUBE_CONTEXT:-}" ]]; then
  CONTEXT_ARGS+=(--context "${KUBE_CONTEXT}")
fi

echo "== Lab 02 preflight =="
echo "workspace=${ROOT_DIR}"
echo "mode=${MODE:-auto}"

for tool in kubectl python3; do
  if command -v "${tool}" >/dev/null 2>&1; then
    echo "[OK] ${tool}: $(command -v "${tool}")"
  else
    echo "[WARN] missing ${tool}"
  fi
done

if command -v helm >/dev/null 2>&1; then
  helm version --short || true
else
  echo "[WARN] helm missing; install scripts cannot run"
fi

if ! command -v kubectl >/dev/null 2>&1; then
  echo "[INFO] kubectl missing: manifest-only mode"
  exit 0
fi

if ! kubectl "${CONTEXT_ARGS[@]}" version >/tmp/lab02-kubectl-version.txt 2>&1; then
  echo "[INFO] no reachable Kubernetes API: manifest-only mode"
  sed -n '1,12p' /tmp/lab02-kubectl-version.txt || true
  exit 0
fi

echo "-- kubectl version --"
kubectl "${CONTEXT_ARGS[@]}" version
echo "-- nodes --"
kubectl "${CONTEXT_ARGS[@]}" get nodes -o wide
echo "-- all pods snapshot --"
kubectl "${CONTEXT_ARGS[@]}" get pods -A

echo "-- GPU allocatable --"
GPU_ROWS="$(kubectl "${CONTEXT_ARGS[@]}" get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.allocatable.nvidia\.com/gpu}{"\n"}{end}')"
if [[ -z "${GPU_ROWS//[[:space:]]/}" ]]; then
  echo "[WARN] no nvidia.com/gpu allocatable value; do not call GPU workload runnable"
else
  printf '%s\n' "${GPU_ROWS}"
fi

echo "-- operator/KServe hints --"
kubectl "${CONTEXT_ARGS[@]}" get pods -n gpu-operator 2>/dev/null || echo "gpu-operator namespace not found"
kubectl "${CONTEXT_ARGS[@]}" get crd inferenceservices.serving.kserve.io 2>/dev/null || echo "KServe InferenceService CRD not found"
echo "[OK] preflight finished; inspect output and save it as evidence"
