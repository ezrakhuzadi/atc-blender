#!/bin/bash

set -euo pipefail

# Activate venv so we use the expected wait-for-it CLI from dependencies.
source .venv/bin/activate

echo "Waiting for DBs..."
wait_args=(--parallel --service "${REDIS_HOST}:${REDIS_PORT}")
if [[ -n "${POSTGRES_HOST:-}" && -n "${POSTGRES_PORT:-}" ]]; then
  wait_args+=(--service "${POSTGRES_HOST}:${POSTGRES_PORT}")
fi
wait-for-it "${wait_args[@]}"

celery --app=flight_blender worker --loglevel=info
