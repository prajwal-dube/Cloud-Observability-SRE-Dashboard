# Verification evidence and interview preparation

Do not substitute synthetic tests for an actual cloud deployment. Keep a dated results folder containing redacted output and screenshots from your own run. No percentages, availability claims, MTTR improvements, or cost savings are asserted by this package.

Evidence checklist:

- Record Git commit, image digest, selected chart version, Kubernetes version, and environment (local/EKS).
- Save offline test output and the native `promtool` rule/config validation output separately.
- Confirm all ready API pods are individually scraped; capture target discovery and one `/metrics` response without secrets.
- Capture the provisioned dashboard with real request/error/latency/probe data. Capture actual cluster CPU and memory data on EKS, or explicitly mark those panels unverified.
- Enable the bounded fault demo, generate traffic, and record pending -> firing state and UTC timestamps. These are injected errors and delays, not evidence of naturally occurring incidents.
- Record a real Alertmanager-delivered local event or an authorized redacted Slack message. The Python receiver fixture test alone does not prove full routing.
- Recover, generate normal traffic, and record resolved state/notification. Show that health probes remained distinct from API request error metrics.
- Save a short incident report with root cause, fix, and verification. If you measure detection/recovery time, state the traffic, windows, hold times, and exact timestamp method; do not invent improvement percentages.
- Inspect cloud inventory after teardown, including retained EBS volumes and load balancers.

Interview questions to practice:

1. Why must Prometheus scrape pod endpoints instead of one load-balanced Service IP for application counters?
2. How does the exporter keep counters consistent across two processes, and what scaling limitation does SQLite introduce?
3. Why are health and scrape requests excluded from the error denominator?
4. Why aggregate histogram buckets before estimating a percentile? How does bucket width affect accuracy?
5. Why deduplicate shared database probe gauges with `max` instead of summing replicas?
6. What is the difference between a failed scrape and a missing target?
7. Why does adding a standalone NetworkPolicy change ingress behavior even if other traffic was previously unrestricted?
8. What can still fail while Grafana is healthy and application metrics exist?
9. What is persistent storage protecting, and what is it not protecting?
10. How would you evolve the lab toward production: exporter overhead benchmarking, metric-drop visibility, authenticated telemetry, HA, retention/backup, log aggregation, secret rotation, image scanning, and measured SLOs?
