# Incident runbooks

For each incident record: UTC start time, user-visible symptom, firing rule and labels, investigation, root cause, repair, and resolution evidence. Check both dashboard and logs. Firing detection does not prove complete coverage, and absence of an alert does not establish health.

## High errors / high latency

1. Confirm traffic volume, error ratio, and p95. Distinguish controlled `OBS_DEMO_MODE` errors from genuine failures; injected responses include `X-NetOps-Demo: true`.
2. Review API logs: `kubectl logs deployment/lab-netops-api -n netops --since=10m`; inspect restarts and scheduling with `kubectl describe pod -n netops POD_NAME`. Locally use the same Compose files as startup with `logs --tail=100 api`.
3. Check PostgreSQL readiness/connection errors, CPU/memory limits, worker load, and deployment/image changes. Compare API handling time to client/probe latency; the former excludes external network/Ingress time.
4. Disable demo flags for a simulated incident. For a real regression, inspect `helm history lab -n netops` and roll back to a known compatible revision if appropriate; understand database schema compatibility first.
5. Request the API normally, wait for the five-minute rolling window and hold times, confirm resolved state, and capture evidence. Do not disable the alert as a fix.

## All API targets down / no targets discovered

`NetOpsAllAPITargetsDown` means discovered endpoints fail scrapes. `NetOpsAPITargetsMissing` means there are no matching scrape series. These cases need different discovery checks.

Inspect `kubectl get deployment,pods,svc,endpoints -n netops`; compare ready replica count with Prometheus Targets. Verify the instrumented image, the `metrics` named Service port, `release: monitoring` ServiceMonitor label, monitor namespace selectors, and `netops_job: netops-api`. Inspect `/metrics` via an API Service port-forward. A 503 can indicate its local SQLite store cannot be opened. Check that `/tmp` is writable through the original emptyDir/tmpfs. A timeout suggests routing or a NetworkPolicy issue. When ingress isolation is enabled, Prometheus pods in `monitoring` need access to port 8000 in addition to frontend/worker access. Never expose `/metrics` publicly to solve discovery.

## Unhealthy / stale / missing probes

Probe health 0 means the last worker-observed target was unhealthy. Staleness means no fresh API receipt timestamp for >30 seconds sustained for a minute. Missing-data rules cover the expected `api`/`frontend` targets. Check worker logs (`kubectl logs deployment/lab-netops-worker -n netops --since=10m`), configured target names/URLs, INGEST_TOKEN Secret references, API write responses, and shared PostgreSQL rows. Check frontend and API readiness separately. Correct authorization/connectivity before restarting. Wait for two fresh probe intervals and confirm target timestamps advance. Shared gauges are duplicated across API replicas; inspect deduplicated `max`, not `sum`. Clock synchronization matters for timestamp-based freshness.

## Shared database collection failure

All API replicas failing to read observations activates `NetOpsDatabaseCollectionFailed`. `/metrics` can still return request metrics with `netops_database_collect_success 0`. Inspect `kubectl get statefulset,pods,pvc -n netops`, database readiness, matching credentials, DNS/service endpoint, and policy allowance on port 5432. Do not print credentials into incident reports. A single API replica failure will not fire the all-replica rule; inspect the raw per-instance gauge to diagnose partial failures. Once connectivity is repaired, confirm collection gauge 1 and fresh probe data.

## High CPU / memory (Kubernetes only)

Confirm API cAdvisor metrics and resource-limit series exist. Compare per-pod request rates, CPU usage, working set, restarts, and OOMKilled/throttling evidence. Use `kubectl top pods -n netops` only if Metrics Server is installed; this lab does not install it. The alert holds above 85% of the configured container limit for five minutes. Review runaway work, memory growth, requests/limits, and replicas. Scale within cluster capacity and avoid treating a larger memory limit as root-cause remediation. Local Compose does not provide these exporter series; no-data there is expected.

## Alert firing but no notification

Default local route goes to the in-memory receiver at `http://alert-sink:8085/alerts`; inspect http://127.0.0.1:8085/notifications and Alertmanager logs. Default EKS route deliberately has no external destination. If Slack was configured, check `service="netops"`, inhibition/silences, group wait/interval, mounted secret path, webhook/channel permissions, and network egress. Inspect errors without revealing the webhook. In a network-restricted cluster Slack delivery will fail unless appropriate outbound access exists. Confirm resolved messages as well as firing messages. Receiver test fixtures are not evidence of Prometheus-driven delivery.
