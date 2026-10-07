#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${PROJECT1_DIR:?Set the absolute extracted Project 1 folder}"
export OBS_PROJECT_DIR="$(pwd)"
test -f "$PROJECT1_DIR/compose.yaml"
test -f "$PROJECT1_DIR/.env"
test -f .secrets/grafana-admin-password || { echo "Run python3 scripts/create-grafana-secret.py --local first" >&2; exit 1; }
docker compose --project-directory "$PROJECT1_DIR" --env-file "$PROJECT1_DIR/.env"   -f "$PROJECT1_DIR/compose.yaml" -f "$OBS_PROJECT_DIR/deploy/compose/observability.yaml" "$@" up --build -d
