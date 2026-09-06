#!/usr/bin/env bash
set -euo pipefail

KSERVE_VERSION="${KSERVE_VERSION:-v0.20.0}"
CERT_MANAGER_VERSION="${CERT_MANAGER_VERSION:-v1.21.1}"

command -v helm >/dev/null 2>&1 || { echo "helm is required" >&2; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "kubectl is required" >&2; exit 1; }
[[ -n "${KUBE_CONTEXT:-}" ]] || { echo "KUBE_CONTEXT is required" >&2; exit 1; }

# KServe Standard mode requires cert-manager for webhook certificates.
kubectl --context "${KUBE_CONTEXT}" apply --server-side \
  -f "https://github.com/cert-manager/cert-manager/releases/download/${CERT_MANAGER_VERSION}/cert-manager.yaml"
kubectl --context "${KUBE_CONTEXT}" -n cert-manager wait --for=condition=Available deployment/cert-manager --timeout=180s
kubectl --context "${KUBE_CONTEXT}" -n cert-manager wait --for=condition=Available deployment/cert-manager-webhook --timeout=180s

helm upgrade --install kserve-crd oci://ghcr.io/kserve/charts/kserve-crd \
  --kube-context "${KUBE_CONTEXT}" \
  --version "${KSERVE_VERSION}" \
  --namespace kserve \
  --create-namespace \
  --wait
helm upgrade --install kserve-resources oci://ghcr.io/kserve/charts/kserve-resources \
  --kube-context "${KUBE_CONTEXT}" \
  --version "${KSERVE_VERSION}" \
  --namespace kserve \
  --set kserve.controller.deploymentMode=Standard \
  --wait

kubectl --context "${KUBE_CONTEXT}" -n kserve get pods
kubectl --context "${KUBE_CONTEXT}" get crd inferenceservices.serving.kserve.io
