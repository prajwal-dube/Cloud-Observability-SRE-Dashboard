# Optional real Slack notifications

Default behavior does not send Slack messages. Use this section only with a webhook created for a channel you intend to notify. Keep webhook URLs out of Git, logs, screenshots, command arguments, and resume evidence. Treat the URL as a secret and rotate it if exposed.

The configuration helper reads the URL through a hidden terminal prompt and makes no outbound HTTP request. It validates the ordinary `https://hooks.slack.com/services/...` form; Slack Gov/other integrations are outside this helper's scope. Incoming webhooks may be bound to their configured channel regardless of the `channel` field: choose the right webhook/channel at creation.

## Local activation

```bash
python3 scripts/configure-slack.py --local --channel '#netops-alerts'
bash scripts/local-up.sh -f "$PWD/slack-compose.local.json"
```

The generated Alertmanager configuration references `.secrets/slack-url` via a container-mounted file and filters notifications to `service="netops"`. Firing and resolved notifications are enabled. Local Grafana/webhook files are container-readable inside a host directory restricted to mode 0700. This assumes a local trusted Unix workstation; confirm permissions and Compose bind-mount access under your OS. Generated configuration/overrides contain paths/channel but no URL. Do not add `.secrets` to Git.

To demonstrate errors with Slack enabled, use both overlays, in this order:

```bash
bash scripts/local-up.sh -f "$PWD/deploy/compose/demo.yaml" -f "$PWD/slack-compose.local.json"
python3 scripts/traffic.py --seconds 420 --concurrency 2
```

Use the base plus Slack overlay to recover normal behavior; the original local sink no longer receives these notifications. Removing the Slack overlay and restarting restores the local receiver.

## EKS activation

After creating `monitoring` and installing the base stack:

```bash
python3 scripts/configure-slack.py --channel '#netops-alerts'
bash scripts/install-kubernetes.sh -f "$PWD/slack-values.local.json"
```

Keep the same `KPS_CHART_VERSION`. If persistence was enabled, include `-f deploy/kubernetes/persistence-values.yaml` as well; Helm updates must preserve your chosen overrides. The helper creates `netops-slack` via stdin and refuses to overwrite it. Alertmanager mounts `slack-url` under `/etc/alertmanager/secrets/netops-slack/`. `tplConfig: false` prevents Helm from evaluating the Alertmanager notification templates. The default receiver drops unrelated chart alerts and the service-filtered route sends only this app's alerts to Slack.

After activation, test in your lab, capture redacted firing and resolved messages, and check Alertmanager logs for delivery errors. Returning to base values removes the Slack route (preserve persistence overrides); then delete the unused `netops-slack` Secret. The project authoring environment did not configure a live webhook or send any message.
