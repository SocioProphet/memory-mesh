#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LOCAL_DIR="$ROOT_DIR/deploy/local"
ENV_FILE="$LOCAL_DIR/.env"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

API_KEY="${MEMORYD_API_KEY:-memorymesh-local-dev}"
BASE_URL="http://127.0.0.1:${MEMORYD_HOST_PORT:-8787}"

curl -fsS "$BASE_URL/healthz" >/dev/null

curl -fsS -X POST "$BASE_URL/v1/write" \
  -H "content-type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{
    "envelope": {
      "user_id": "lord",
      "agent_id": "local-smoke",
      "run_id": "run-smoke-001",
      "workload_id": "memorymesh-local",
      "source_interface": "smoke-script"
    },
    "content": "The local Podman stack on the M2 Mac is working.",
    "memory_class": "fact",
    "persist_to_backend": false,
    "metadata": {"test": true},
    "tags": ["smoke", "local"]
  }' >/dev/null

curl -fsS -X POST "$BASE_URL/v1/recall" \
  -H "content-type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{
    "envelope": {
      "user_id": "lord",
      "agent_id": "local-smoke",
      "run_id": "run-smoke-001",
      "workload_id": "memorymesh-local",
      "source_interface": "smoke-script"
    },
    "query": "What proves the local Podman stack works?",
    "top_k": 3
  }'
