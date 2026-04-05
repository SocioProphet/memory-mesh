#!/usr/bin/env bash
set -euo pipefail

MACHINE_NAME="${PODMAN_MACHINE_NAME:-podman-machine-default}"
CPUS="${PODMAN_MACHINE_CPUS:-4}"
MEMORY_MB="${PODMAN_MACHINE_MEMORY_MB:-8192}"
DISK_GB="${PODMAN_MACHINE_DISK_GB:-60}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/local/.env"

if ! command -v podman >/dev/null 2>&1; then
  echo "podman is not installed" >&2
  exit 1
fi

if ! podman compose version >/dev/null 2>&1; then
  echo "podman compose is unavailable; install a compose provider or Podman Desktop" >&2
  exit 1
fi

if ! podman machine inspect "$MACHINE_NAME" >/dev/null 2>&1; then
  echo "Initializing Podman machine $MACHINE_NAME"
  podman machine init --cpus "$CPUS" --memory "$MEMORY_MB" --disk-size "$DISK_GB" "$MACHINE_NAME"
fi

echo "Starting Podman machine $MACHINE_NAME"
podman machine start "$MACHINE_NAME" >/dev/null 2>&1 || true

echo "Verifying Podman socket"
podman info >/dev/null

cd "$ROOT_DIR/deploy/local"
if [[ ! -f .env ]]; then
  cp .env.example .env
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

echo "Bringing up local compose stack"
podman compose --env-file .env -f podman-compose.yaml up -d --build

echo "Local stack launched."
echo "memoryd: http://127.0.0.1:${MEMORYD_HOST_PORT:-8787}/healthz"
echo "qdrant: http://127.0.0.1:${QDRANT_HOST_PORT:-6333}"
