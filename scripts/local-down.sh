#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${PROJECT1_DIR:?Set the absolute extracted Project 1 folder}"
export OBS_PROJECT_DIR="$(pwd)"
docker compose --project-directory "$PROJECT1_DIR" --env-file "$PROJECT1_DIR/.env"   -f "$PROJECT1_DIR/compose.yaml" -f "$OBS_PROJECT_DIR/deploy/compose/observability.yaml" "$@" down
# No -v: PostgreSQL and monitoring volumes are retained by default.
