#!/usr/bin/env bash
set -euo pipefail

PROM_STACK_VERSION="${PROM_STACK_VERSION:-88.0.1}"
INSTALL_KEDA="${INSTALL_KEDA:-0}"
KEDA_VERSION="${KEDA_VERSION:-2.19.0}"

command -v helm >/dev/null 2>&1 || { echo "helm is required" >&2; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "kubectl is required" >&2; exit 1; }
[[ -n "${KUBE_CONTEXT:-}" ]] || { echo "KUBE_CONTEXT is required" >&2; exit 1; }

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --kube-context "${KUBE_CONTEXT}" \
  --namespace monitoring \
  --create-namespace \
  --version "${PROM_STACK_VERSION}" \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
  --set prometheus.prometheusSpec.ruleSelectorNilUsesHelmValues=false \
  --wait

if [[ "${INSTALL_KEDA}" == "1" ]]; then
  kubectl --context "${KUBE_CONTEXT}" apply --server-side \
    -f "https://github.com/kedacore/keda/releases/download/v${KEDA_VERSION}/keda-${KEDA_VERSION}.yaml"
  kubectl --context "${KUBE_CONTEXT}" -n keda get pods
else
  echo "KEDA skipped; set INSTALL_KEDA=1 only after reviewing Prometheus access/auth."
fi

kubectl --context "${KUBE_CONTEXT}" -n monitoring get pods
