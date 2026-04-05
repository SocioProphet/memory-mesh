# Artifact resolution policy

## Intent

`memorymesh` must never depend on best-effort runtime fetches from public registries. All external software and model assets are resolved through an importer workflow that writes reproducible build inputs.

## Rules

1. Every upstream package, repo, image, or plugin must have an exact pin.
2. Every deployable artifact should be mirrored into an internal location before production use.
3. Vendoring whole upstream repos is the exception, not the default.
4. Models are pinned separately from code because model governance needs different metadata.
5. Production builds must consume only local lockfiles, archived artifacts, or internally mirrored registries.

## Allowed forms of pinning

- npm exact versions such as `3.2.0`
- PyPI exact versions such as `1.83.2`
- Git tags plus expected commit SHA
- OCI image digests
- model file SHA-256 hashes

## Repo conventions

- `third_party/upstreams.lock.yaml` is the source of truth for software upstreams.
- `artifacts/models.lock.yaml` is the source of truth for model assets.
- `third_party/patches/` is reserved for patch queues we intentionally carry.
- importer scripts can render derived build inputs, but developers should not edit generated files by hand.
