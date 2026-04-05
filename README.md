# memory-mesh-upstream

This repository is the upstream baseline for the SocioProphet memory mesh runtime and deployment work.

It keeps three concerns separate:

1. `services/memoryd/` is the control-plane and stable API for recall, writeback, config watch, and resource application.
2. `adapters/` contains integration shims for upstream systems such as LiteLLM and OpenClaw.
3. `third_party/` and `artifacts/` pin upstream software and model artifacts without forcing us to vendor entire upstream repos.

## Current status

This upstream currently includes:

- a runnable `memoryd` FastAPI service with in-memory, SQLite, and PostgreSQL store seams;
- optional vector retrieval wiring through Qdrant plus a deterministic local embedder for bring-up;
- a LiteLLM callback hook that performs recall-before-call and writeback-after-call;
- an OpenClaw plugin that exposes `memory_search` and `memory_write` tools;
- repo-native lock manifests for upstream software and model artifacts;
- importer and validation scripts so upstream resolution happens in one controlled place instead of at runtime;
- local M2 Mac Podman and Google Cloud review deployment scaffolding.

## Repository semantics

This is not a disposable starter artifact. This repository is the canonical upstream baseline for branch-and-PR driven development.

## Recommended repo split

- `memory-mesh-upstream` owns the runtime, adapters, importer logic, deployment scaffolding, and build inputs.
- `socioprophet-standards-storage` should mirror ADRs, normative schemas, retention policy, and benchmarks.
- `sociosphere` should register the component and adapter manifests.

## Layout

```text
adapters/
  litellm/
  openclaw-memory-mesh/
artifacts/
  models.lock.yaml
deploy/
services/
  memoryd/
specs/
  memoryd.openapi.yaml
third_party/
  upstreams.lock.yaml
scripts/
  validate_upstreams.py
  render_import_plan.py
  import_upstreams.py
```

## Supply-chain posture

- lock exact upstream versions in `third_party/upstreams.lock.yaml`
- mirror resolved artifacts into registries or stores we control
- vendor only patch queues or forked upstreams
- never allow production to fetch public dependencies at runtime

## Quickstart

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r services/memoryd/requirements.txt
uvicorn services.memoryd.app.main:app --reload --port 8787
```

In another shell:

```bash
python scripts/validate_upstreams.py third_party/upstreams.lock.yaml
python scripts/render_import_plan.py third_party/upstreams.lock.yaml
python scripts/import_upstreams.py third_party/upstreams.lock.yaml --output third_party/resolved.upstreams.json
```
