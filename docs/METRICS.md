# Metrics and dashboard interpretation

| Metric | Type | Interpretation |
|---|---|---|
| `netops_http_requests_total` | Counter | Completed non-probe requests, by method, bounded route, and status class |
| `netops_http_request_duration_seconds` | Histogram | API handling time through iterable consumption, before telemetry commit |
| `netops_metrics_start_time_seconds` | Gauge | Store creation time; reset on API container restart |
| `netops_database_collect_success` | Gauge | 1 when shared observations can be read, otherwise 0 |
| `netops_probe_healthy` | Gauge | Most recent worker observation health; shared across API replicas |
| `netops_probe_latency_seconds` | Gauge | Latest HTTP probe duration, not user-request duration |
| `netops_probe_last_observed_timestamp_seconds` | Gauge | API receipt timestamp used to detect stale observations |
| `netops_probe_targets_truncated` | Gauge | 1 when more than twenty shared targets existed |

`/healthz`, `/readyz`, and `/metrics` are excluded from request counters and latency histograms. Otherwise their fast periodic requests would dilute user error ratios and latency. Unknown application paths still contribute as `__other__`.

Histogram buckets in seconds: 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, and +Inf. Exported buckets are cumulative; +Inf equals count. Sum is in seconds. Percentiles are interpolated estimates, not exact timings. No traffic yields an undefined/empty percentile, not proof of zero latency. At sustained demo delay of 750 ms, the estimated percentile can approach the top of its 0.5–1 second bucket.

Useful queries (paste into Prometheus):

```promql
sum by (namespace) (rate(netops_http_requests_total{job="netops-api",namespace="netops"}[5m]))

netops:http_errors:ratio5m{namespace="netops"}

1000 * netops:http_latency:p95_5m{namespace="netops"}

max by (namespace,target) (netops_probe_healthy{job="netops-api",namespace="netops"})

time() - max by (namespace,target) (netops_probe_last_observed_timestamp_seconds{job="netops-api",namespace="netops"})

ALERTS{service="netops",alertstate="firing"}
```

Recording rules consolidate rates and p50/p95/p99 across instances using histogram buckets, rather than averaging per-pod percentiles. Request error ratio falls back to zero when traffic exists but no 5xx series exists. Error and latency alerts require at least twenty requests in five minutes to reduce low-volume noise. Error ratio >5% holds for two minutes; p95 >500 ms holds for three. Scrapes and rule evaluations occur every fifteen seconds. Traffic and hold-time warm-up mean an alert is not instantaneous.

The 12 dashboard panels cover healthy scrape targets, requests/s, error ratio, p95, percentile history, requests by status class, probe health, probe latency, probe freshness, firing alerts, CPU cores, and memory working set. CPU/memory panels cover NetOps workload containers on Kubernetes. Their API alert thresholds compare usage to configured API container limits, not node capacity. The CPU/memory alerts require cAdvisor and kube-state-metrics; absent collectors or absent limits cause missing results, not a healthy verdict. They intentionally do not fire in the Compose lab.

`deploy/prometheus/rules.yaml` is the local rules file. Its group content must match `deploy/kubernetes/prometheus-rule.yaml`'s `spec.groups`. The dashboard JSON is likewise copied into a Kubernetes ConfigMap. Keep these in sync when changing rules or panels. The report records their equality at packaging time, not PromQL engine validation.
