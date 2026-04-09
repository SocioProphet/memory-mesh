#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LOCAL_DIR="$ROOT_DIR/deploy/local"
ENV_FILE="$LOCAL_DIR/.env"

if ! command -v podman >/dev/null 2>&1; then
  echo "podman is not installed" >&2
  exit 1
fi

if ! podman compose version >/dev/null 2>&1; then
  echo "podman compose is unavailable; install a compose provider or Podman Desktop" >&2
  exit 1
fi

cd "$LOCAL_DIR"
if [[ ! -f .env ]] && [[ -f .env.example ]]; then
  cp .env.example .env
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

podman compose --env-file .env -f podman-compose.yaml down

echo "Local stack stopped."
