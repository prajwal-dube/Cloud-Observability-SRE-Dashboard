# EKS setup against an existing NetOps release

Run every command from this project root unless specified. Confirm `aws sts get-caller-identity` and `kubectl config current-context` against your intended lab. EKS, nodes, load balancers, EBS disks, NAT, ECR, and logs can incur charges. Use Project 1 or Project 2's documented cluster access/bootstrap; this package does not create or take ownership of their infrastructure.

## 1. Publish the instrumented API

Use your existing API ECR repository. Choose an immutable commit-related image tag, not `latest`:

```bash
export PROJECT1_DIR=/absolute/path/to/project-1-netops-eks
export AWS_REGION=us-east-1
export API_ECR_URI=123456789012.dkr.ecr.us-east-1.amazonaws.com/netops-api
export API_IMAGE_TAG=obs-your-commit
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "${API_ECR_URI%%/*}"
docker build --platform linux/amd64 -t "$API_ECR_URI:$API_IMAGE_TAG" instrumented-api
docker push "$API_ECR_URI:$API_IMAGE_TAG"
```

Replace sample account/repository/region with actual values from Projects 1/2. For ARM nodes, build the matching platform instead. The snapshot preserves the original API database schema, routes, and observation authorization. Project 1's migration job remains compatible.

Preserve all existing Helm values, including frontend/worker image tags, ALB annotations, secret references, and exposure restrictions:

```bash
helm get values lab -n netops -o json > app-values.local.json
python3 scripts/api-image-override.py --values app-values.local.json --repository "$API_ECR_URI" --tag "$API_IMAGE_TAG"
helm upgrade lab "$PROJECT1_DIR/deploy/helm/netops" -n netops -f app-values.local.json --atomic --wait --timeout 10m
kubectl rollout status deployment/lab-netops-api -n netops
kubectl logs deployment/lab-netops-api -n netops --tail=30
```

The script changes only `images.api.repository` and `images.api.tag` in the provided values file. Keep your original file privately for rollback. Do not commit exported Helm values. Existing Secrets stay referenced by name. Confirm the chart directory above matches your extracted Project 1 (its chart is `deploy/helm/netops`). Do not deploy with an empty values file if the release needs custom image tags or Ingress settings.

## 2. Install monitoring with a reviewed chart version

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update prometheus-community
helm search repo prometheus-community/kube-prometheus-stack --versions
export KPS_CHART_VERSION=YOUR_SELECTED_SEMANTIC_VERSION
python3 scripts/create-grafana-secret.py
helm template monitoring prometheus-community/kube-prometheus-stack -n monitoring --version "$KPS_CHART_VERSION" -f deploy/kubernetes/stack-values.yaml > monitoring-render.local.yaml
bash scripts/install-kubernetes.sh
```

Replace the version placeholder with a real `major.minor.patch` compatible with your Kubernetes version. Review chart release notes, render output, expected RBAC, image versions, requests/limits, and availability of the `uid: prometheus` datasource. Install is atomic and waits; it does not guarantee every optional collector works on your cluster.

For persistent history, first confirm `kubectl get storageclass netops-gp3` and a healthy EBS CSI driver, then add `-f deploy/kubernetes/persistence-values.yaml` to both render and installer commands. Project 2 alone does not install Project 1's application/StorageClass/add-ons; finish the Project 1 deployment against that cluster first. The optional storage uses 5 GiB for Prometheus and 1 GiB each for Grafana and Alertmanager. Retained EBS volumes can keep incurring charges after uninstall.

The installer adds the scraping allow-policy only if Project 1's API isolation policy already exists. Applying that allow-policy by itself would start isolating API ingress and break frontend/worker traffic. If you use a differently named custom policy, inspect its behavior and add equivalent monitoring access yourself.

## 3. Confirm pod-level scraping and dashboard

```bash
kubectl get pods,svc -n monitoring
kubectl get servicemonitor netops-api -n netops -o yaml
kubectl get endpoints netops-observed-api -n netops
kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9090:9090
```

In separate terminals:

```bash
kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80
kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-alertmanager 9093:9093
```

Check actual Service names with `kubectl get svc -n monitoring` if your chart version differs. Read the Grafana password privately from Secret `netops-grafana-admin`, key `admin-password`; username `admin`. Keep the UIs private via port-forwarding.

Send requests to your existing authorized app URL or port-forward `svc/lab-netops-api` on port 8000 and run `traffic.py --url http://127.0.0.1:8000/api/targets --seconds 300`. Run `python3 scripts/smoke.py`. In Prometheus Targets, confirm one healthy scrape target **per ready API pod**. Inspect `/metrics` and the datasource/dashboard manually. Check container CPU/memory panels and exporter targets; smoke checks alone do not establish their correctness.

## 4. Controlled incident and recovery

Only on your lab application:

```bash
kubectl set env deployment/lab-netops-api -n netops OBS_DEMO_MODE=true OBS_DEMO_DELAY_MS=750 OBS_DEMO_ERROR_EVERY=4
kubectl rollout status deployment/lab-netops-api -n netops
python3 scripts/traffic.py --url http://127.0.0.1:8000/api/targets --seconds 420 --concurrency 2
```

Deployment updates restart pods; restart port-forwarding if it loses its selected pod. The default EKS receiver sends nothing externally. Observe pending/firing states and, if explicitly configured, Slack messages. Recover:

```bash
kubectl set env deployment/lab-netops-api -n netops OBS_DEMO_MODE- OBS_DEMO_DELAY_MS- OBS_DEMO_ERROR_EVERY-
kubectl rollout status deployment/lab-netops-api -n netops
```

Generate normal traffic and wait for the five-minute lookback and notification group interval. `kubectl set env` is a temporary lab edit outside Helm values; do not persist demo flags as desired production configuration. Keep a timestamped incident record.

## Cleanup

Disable demo flags first. Remove this project's monitoring resources with `kubectl delete -f deploy/kubernetes/api-monitor.yaml -f deploy/kubernetes/prometheus-rule.yaml -f deploy/kubernetes/dashboard-configmap.yaml --ignore-not-found`, then uninstall only this lab's monitoring release: `helm uninstall monitoring -n monitoring`. If installed, remove `allow-prometheus.yaml` separately. Do not delete shared CRDs, the whole namespace, PostgreSQL, or the cluster as a monitoring cleanup shortcut. Delete this project's Grafana/Slack Secrets when no longer needed. Inspect PVCs/PVs/EBS volumes and their reclaim policies before deliberately removing retained storage. For full lab teardown, separately follow the provisioning project's procedure and inspect cloud resource inventory. An uninstall is not proof that your AWS bill has stopped.
