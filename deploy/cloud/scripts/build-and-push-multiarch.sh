#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-memoryd}"
IMAGE_TAG="${IMAGE_TAG:-review}"
REGION="${REGION:?set REGION, e.g. us-central1}"
PROJECT_ID="${PROJECT_ID:?set PROJECT_ID}"
REPOSITORY="${REPOSITORY:?set REPOSITORY}"
MANIFEST_NAME="${MANIFEST_NAME:-memorymesh-${IMAGE_NAME}:${IMAGE_TAG}}"
TARGET="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${IMAGE_TAG}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

if ! command -v podman >/dev/null 2>&1; then
  echo "podman is not installed" >&2
  exit 1
fi

cd "$ROOT_DIR"

echo "Building multi-arch manifest ${MANIFEST_NAME}"
podman build \
  --platform linux/arm64,linux/amd64 \
  --manifest "$MANIFEST_NAME" \
  -f images/memoryd.Dockerfile \
  .

echo "Pushing ${TARGET}"
podman manifest push --all "$MANIFEST_NAME" "docker://${TARGET}"

echo "Done. Resolve the pushed digest and update deployment manifests before shared deploys."
