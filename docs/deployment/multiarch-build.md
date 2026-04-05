# Multi-architecture image build notes

## Goal

Build `memoryd` images that can run on both the local Apple Silicon developer machine and cloud targets.

## Default policy

- local development: `linux/arm64` is enough;
- shared cloud builds: publish a manifest that includes at least `linux/amd64` and `linux/arm64`;
- any image that might go to Cloud Run must include `linux/amd64`.

## Local single-arch build

```bash
podman build \
  -f images/memoryd.Dockerfile \
  -t localhost/memorymesh-memoryd:dev \
  .
```

## Multi-arch build with Podman

```bash
podman build \
  --platform linux/arm64,linux/amd64 \
  --manifest memorymesh-memoryd:review \
  -f images/memoryd.Dockerfile \
  .
```

Then push the manifest to Artifact Registry.

```bash
podman manifest push --all \
  memorymesh-memoryd:review \
  docker://REGION-docker.pkg.dev/PROJECT/REPO/memoryd:review
```

## Notes

- The target registry must already exist.
- Authenticate Podman to Artifact Registry before pushing.
- Once the image is pushed, resolve the digest and deploy by digest, not by tag.
