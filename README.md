# Project 3 — Cloud Observability & SRE Dashboard

A hands-on monitoring extension for Project 1's NetOps application, deployable locally or on its EKS cluster (including a cluster provisioned by Project 2). Includes an instrumented Python API snapshot, Prometheus, a 12-panel Grafana dashboard, ten alert rules, optional Slack routing, and reproducible incident exercises.

**Status:** 22 Python tests passed in the authoring environment. Docker images, native PromQL rule tests, Helm rendering, EKS deployment, Grafana dashboard rendering, and Slack delivery have NOT been executed here. See `docs/VERIFICATION.md`. No cloud resources were created and no external notifications were sent. The project is a learning lab; execute and collect evidence before claiming deployment on a resume.

## Prerequisites

Extract both Project 1 and this ZIP. Keep each folder intact. Local path: Python 3.11+, Docker with Compose v2, and Project 1's generated `.env`. Follow Project 1's setup if it has not been initialized. Kubernetes path additionally requires AWS CLI, kubectl, Helm 3, a working EKS cluster, deployed Helm release `lab` in namespace `netops`, and ECR push permissions. This package does not provision a new cluster.

## Run the local lab

From this project's root:

```bash
export PROJECT1_DIR=/absolute/path/to/project-1-netops-eks
python3 scripts/create-grafana-secret.py --local
bash scripts/offline-check.sh
bash scripts/check-prometheus.sh
bash scripts/local-up.sh
python3 scripts/traffic.py --seconds 90
python3 scripts/smoke.py
```

The secret generator refuses to overwrite an existing credential; run it once. `offline-check.sh` requires only the Python standard library. `check-prometheus.sh` requires Docker and validates the actual Prometheus rules plus Alertmanager configuration using their native tools. It also runs the three supplied synthetic PromQL scenarios.

Open the app at http://127.0.0.1:8080, Prometheus at http://127.0.0.1:9090, Grafana at http://127.0.0.1:3000, and Alertmanager at http://127.0.0.1:9093. Grafana username is `admin`; read `.secrets/grafana-admin-password` privately to sign in. Never include it in screenshots or Git. The provisioned dashboard is **NetOps — Application & Kubernetes Health**. Allow at least two scrapes before rate queries appear, and several minutes for five-minute windows to stabilize.

Only Kubernetes supplies cAdvisor/container CPU and memory metrics in this lab. The final two dashboard panels show no data under Compose, which is expected. This package does not install a log aggregation platform; use the application JSON logs and troubleshooting commands in the runbooks.

## Demonstrate an incident

```bash
bash scripts/local-up.sh -f "$PWD/deploy/compose/demo.yaml"
python3 scripts/traffic.py --seconds 420 --concurrency 2
curl -fsS http://127.0.0.1:8085/notifications
```

The opt-in overlay delays API reads by 750 ms and returns a simulated HTTP 500 on every fourth read **per Gunicorn worker**. Health probes and authenticated observation ingestion remain operational. The high-error-rate and p95 latency alerts should progress through pending/firing once their conditions and hold times are satisfied. Confirm this yourself; this is an intended behavior, not a recorded deployment result. Default local notifications go to a local HTTP receiver, not Slack. Its last 100 summaries are held in memory.

Restore normal behavior with `bash scripts/local-up.sh`, generate more traffic, and wait for the five-minute window and notification group interval to clear. Record firing and resolved evidence. Stop with `bash scripts/local-down.sh` (supply the same additional overlays if used). This keeps named volumes including Project 1's PostgreSQL data. Do not append `-v` unless you intend to delete the lab data.

## EKS and optional Slack

Follow `docs/EKS_SETUP.md` to build and deploy the instrumented image, install a version-pinned kube-prometheus-stack, and port-forward the private monitoring UIs. Follow `docs/SLACK.md` only when you have a workspace/channel and want real notifications. Default EKS alert routing discards outbound notifications while still exposing alert state in the UI.

## Contents and learning path

1. `docs/ARCHITECTURE.md` — data flow, exporters, and design tradeoffs.
2. `docs/METRICS.md` — labels, histograms, aggregation, and PromQL examples.
3. `docs/EKS_SETUP.md` — deploy against existing infrastructure.
4. `docs/RUNBOOKS.md` — diagnose and recover from each alert family.
5. `docs/SLACK.md` — optional secret-backed notification routing.
6. `docs/EVIDENCE.md` — capture genuine results and discuss them in interviews.
7. `RESUME_POINTS.md` — conservative bullets and deployment wording after verification.

Native configuration sources: [Prometheus histogram guidance](https://prometheus.io/docs/practices/histograms/), [rule unit tests](https://prometheus.io/docs/prometheus/latest/configuration/unit_testing_rules/), [Alertmanager configuration](https://prometheus.io/docs/alerting/latest/configuration/), [Prometheus Operator API](https://prometheus-operator.dev/docs/api-reference/api/), and [kube-prometheus-stack chart](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack). Review current compatibility and security advisories before deploying. Local image tags are reproducibility choices; image scanning and digest pinning are follow-up work.
