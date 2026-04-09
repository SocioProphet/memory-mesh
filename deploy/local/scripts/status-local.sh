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

rc=0

podman compose --env-file .env -f podman-compose.yaml ps || rc=1

echo

echo "memoryd health:"
if ! curl -fsS "http://127.0.0.1:${MEMORYD_HOST_PORT:-8787}/healthz"; then
  echo "(unreachable)"
  rc=1
fi

echo

echo "qdrant health:"
if ! curl -fsS "http://127.0.0.1:${QDRANT_HOST_PORT:-6333}/" >/dev/null; then
  echo "(unreachable)"
  rc=1
else
  echo "ok"
fi

echo
exit "$rc"
