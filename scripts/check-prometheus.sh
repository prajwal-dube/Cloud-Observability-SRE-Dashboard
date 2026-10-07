#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Requires Docker; the image supplies native promtool, not a Python reimplementation.
docker run --rm --entrypoint promtool -v "$(pwd)/deploy/prometheus:/work:ro" -w /work   prom/prometheus:v3.5.0 check rules rules.yaml
docker run --rm --entrypoint promtool -v "$(pwd)/deploy/prometheus:/work:ro" -w /work   prom/prometheus:v3.5.0 test rules rule-tests.yaml
docker run --rm --entrypoint amtool -v "$(pwd)/deploy/alertmanager:/work:ro" -w /work   prom/alertmanager:v0.28.1 check-config local.yaml
