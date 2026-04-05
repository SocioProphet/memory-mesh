# memorymesh starter

This repository starter is structured as if it were the initial cut of `SocioProphet/memorymesh`.

It keeps three concerns separate:

1. `services/memoryd/` is the control-plane and stable API for recall, writeback, config watch, and resource application.
2. `adapters/` contains integration shims for upstream systems such as LiteLLM and OpenClaw.
3. `third_party/` and `artifacts/` pin upstream software and model artifacts without forcing us to vendor entire upstream repos.

## Current status

This starter now includes:

- a runnable `memoryd` FastAPI service with an in-memory store and a Mem0 REST backend adapter;
- a LiteLLM callback hook that performs recall-before-call and writeback-after-call;
- an OpenClaw plugin that exposes `memory_search` and `memory_write` tools;
- repo-native lock manifests for upstream software and model artifacts;
- importer/validation scripts so upstream resolution happens in one controlled place instead of at runtime.

## Recommended repo split

- `memorymesh` owns the runtime, adapters, importer logic, and build inputs.
- `socioprophet-standards-storage` should mirror ADRs, normative schemas, retention policy, and benchmarks.
- `sociosphere` should register the component and adapter manifests.

## Layout

```text
adapters/
  litellm/
  openclaw-memory-mesh/
artifacts/
  models.lock.yaml
services/
  memoryd/
specs/
  memoryd.openapi.yaml
  schemas/
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
cd services/memoryd
python -m venv .venv
. .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload --port 8787
```

In another shell:

```bash
python scripts/validate_upstreams.py third_party/upstreams.lock.yaml
python scripts/render_import_plan.py third_party/upstreams.lock.yaml
python scripts/import_upstreams.py third_party/upstreams.lock.yaml --output third_party/resolved.upstreams.json
```
