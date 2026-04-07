#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LOCAL_DIR="$ROOT_DIR/deploy/local"
ENV_FILE="$LOCAL_DIR/.env"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="$ROOT_DIR/.artifacts/local-debug/$STAMP"
mkdir -p "$OUT_DIR"

SOURCE_ENV="$LOCAL_DIR/.env.example"
if [[ -f "$ENV_FILE" ]]; then
  SOURCE_ENV="$ENV_FILE"
fi

set -a
# shellcheck disable=SC1090
source "$SOURCE_ENV"
set +a

{
  echo "timestamp=$STAMP"
  echo "memoryd_host_port=${MEMORYD_HOST_PORT:-8787}"
  echo "postgres_host_port=${POSTGRES_HOST_PORT:-5432}"
  echo "qdrant_host_port=${QDRANT_HOST_PORT:-6333}"
  echo "qdrant_enabled=${QDRANT_ENABLED:-true}"
} > "$OUT_DIR/env-summary.txt"

podman version > "$OUT_DIR/podman-version.txt" 2>&1 || true
podman info > "$OUT_DIR/podman-info.txt" 2>&1 || true
podman machine list > "$OUT_DIR/podman-machine-list.txt" 2>&1 || true
podman ps -a > "$OUT_DIR/podman-ps-a.txt" 2>&1 || true

if podman compose version >/dev/null 2>&1; then
  (
    cd "$LOCAL_DIR"
    podman compose --env-file .env -f podman-compose.yaml ps > "$OUT_DIR/compose-ps.txt" 2>&1 || true
    podman compose --env-file .env -f podman-compose.yaml logs --no-color memoryd > "$OUT_DIR/memoryd.log" 2>&1 || true
    podman compose --env-file .env -f podman-compose.yaml logs --no-color postgres > "$OUT_DIR/postgres.log" 2>&1 || true
    podman compose --env-file .env -f podman-compose.yaml logs --no-color qdrant > "$OUT_DIR/qdrant.log" 2>&1 || true
  )
fi

curl -sS "http://127.0.0.1:${MEMORYD_HOST_PORT:-8787}/healthz" > "$OUT_DIR/memoryd-health.json" 2>&1 || true
curl -sS "http://127.0.0.1:${QDRANT_HOST_PORT:-6333}/" > "$OUT_DIR/qdrant-health.txt" 2>&1 || true

echo "Wrote local debug bundle to $OUT_DIR"
