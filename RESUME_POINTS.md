# Resume wording — Project 3

**Project:** Cloud Observability & SRE Dashboard  
**Technologies:** Python, Prometheus, Grafana, Alertmanager, Docker Compose, Helm, Kubernetes, AWS EKS, Linux, optional Slack

Use the following after reviewing the implementation and running its available tests. These describe implemented code/configuration, not an unverified cloud deployment:

- Instrumented a Python API with Prometheus-compatible request counters, latency histograms, and HTTP probe metrics; validated shared-worker counters with concurrent process and thread tests.
- Built a 12-panel Grafana dashboard and ten Prometheus alert rules covering API errors, latency, target availability, stale probes, and Kubernetes resource usage.
- Created Docker Compose and Helm monitoring configurations, secret-backed optional Slack routing, and controlled incident exercises with diagnosis and recovery runbooks.

After actually deploying and collecting evidence, replace the last bullet with wording such as:

- Deployed Prometheus and Grafana on AWS EKS using Helm and ServiceMonitor discovery; demonstrated alert firing and resolution during controlled API failure simulations.

Use that deployment bullet only after those steps succeed. Mention Slack delivery only after observing actual authorized messages. Mention CPU/memory dashboards only after verifying Kubernetes exporter data. Do not claim reduced MTTR, improved uptime, response-time gains, production operations, or deployment success from the supplied configuration alone. Replace technologies you did not personally use with the subset you can explain and demonstrate.
