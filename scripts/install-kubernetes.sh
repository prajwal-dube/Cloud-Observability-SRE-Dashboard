#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${KPS_CHART_VERSION:?Select and pin a reviewed kube-prometheus-stack chart version from helm search repo --versions}"
[[ "$KPS_CHART_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "Use an explicit chart semantic version" >&2; exit 1; }
kubectl config current-context
kubectl get deployment lab-netops-api -n netops >/dev/null
kubectl get secret netops-grafana-admin -n monitoring >/dev/null
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update prometheus-community
helm show chart prometheus-community/kube-prometheus-stack --version "$KPS_CHART_VERSION" >/dev/null
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack   -n monitoring --version "$KPS_CHART_VERSION" -f deploy/kubernetes/stack-values.yaml "$@"   --atomic --wait --timeout 15m
kubectl apply -f deploy/kubernetes/api-monitor.yaml -f deploy/kubernetes/prometheus-rule.yaml   -f deploy/kubernetes/dashboard-configmap.yaml
# Applying an ingress allow policy alone would isolate API Pods and break existing traffic.
EXISTING_POLICY=$(kubectl get networkpolicy lab-netops-api -n netops --ignore-not-found -o name)
if [[ -n "$EXISTING_POLICY" ]]; then
  kubectl apply -f deploy/kubernetes/allow-prometheus.yaml
else
  echo "API ingress isolation is absent; extra Prometheus policy deliberately not applied."
fi
kubectl get pods,svc -n monitoring
kubectl get servicemonitors -n netops
