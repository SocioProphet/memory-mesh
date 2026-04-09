#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LOCAL_DIR="$ROOT_DIR/deploy/local"
ENV_EXAMPLE="$LOCAL_DIR/.env.example"
ENV_FILE="$LOCAL_DIR/.env"

if ! command -v podman >/dev/null 2>&1; then
  echo "ERROR: podman is not installed" >&2
  exit 1
fi

if ! podman compose version >/dev/null 2>&1; then
  echo "ERROR: podman compose is unavailable; install a compose provider or Podman Desktop" >&2
  exit 1
fi

for path in "$LOCAL_DIR/podman-compose.yaml" "$ROOT_DIR/images/memoryd.Dockerfile" "$ROOT_DIR/services/memoryd/requirements.txt" "$ENV_EXAMPLE"; do
  if [[ ! -e "$path" ]]; then
    echo "ERROR: required file is missing: $path" >&2
    exit 1
  fi
done

SOURCE_ENV="$ENV_EXAMPLE"
if [[ -f "$ENV_FILE" ]]; then
  SOURCE_ENV="$ENV_FILE"
fi

set -a
# shellcheck disable=SC1090
source "$SOURCE_ENV"
set +a

check_port() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      echo "ERROR: TCP port $port is already in use" >&2
      return 1
    fi
  else
    echo "WARN: lsof not found; skipping local port check for $port" >&2
  fi
}

check_port "${MEMORYD_HOST_PORT:-8787}"
check_port "${POSTGRES_HOST_PORT:-5432}"
check_port "${QDRANT_HOST_PORT:-6333}"

ARCH="$(uname -m || true)"
if [[ "$ARCH" != "arm64" ]]; then
  echo "WARN: expected Apple Silicon arm64 host, detected: $ARCH" >&2
fi

echo "Podman version:"
podman version || true

echo "Podman machines:"
podman machine list || true

echo "Preflight OK."
echo "Local dir: $LOCAL_DIR"
echo "Env source: $SOURCE_ENV"
echo "Ports: memoryd=${MEMORYD_HOST_PORT:-8787}, postgres=${POSTGRES_HOST_PORT:-5432}, qdrant=${QDRANT_HOST_PORT:-6333}"
