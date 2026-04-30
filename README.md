# memorymesh

This repository is the canonical upstream baseline for the SocioProphet memory mesh runtime and deployment work.

It keeps three concerns separate:

1. `services/memoryd/` is the control-plane and stable API for recall, writeback, config watch, and resource application.
2. `adapters/` contains integration shims for upstream systems such as LiteLLM and OpenClaw.
3. `third_party/` and `artifacts/` pin upstream software and model artifacts without forcing us to vendor entire upstream repos.

## Current status

This repository currently includes:

- a runnable `memoryd` FastAPI service with in-memory, SQLite, and PostgreSQL store seams;
- optional vector retrieval wiring through Qdrant plus a deterministic local embedder for bring-up;
- a LiteLLM callback hook that performs recall-before-call and writeback-after-call;
- an OpenClaw plugin that exposes `memory_search` and `memory_write` tools;
- repo-native lock manifests for upstream software and model artifacts;
- importer and validation scripts so upstream resolution happens in one controlled place instead of at runtime;
- local M2 Mac Podman and Google Cloud review deployment scaffolding.

## Professional Intelligence context packs

Memory Mesh now carries the first scoped context-pack surface for the Professional Intelligence OS Gate 3 demo path.

The context-pack contract and example live at:

- `schemas/professional-intelligence-context-pack.schema.json`
- `examples/professional-intelligence/context-pack.example.json`

Validate locally:

```bash
python -m pip install jsonschema
python scripts/validate_professional_intelligence_context_pack.py
```

The workflow `.github/workflows/professional-intelligence-context-pack.yml` runs this validation when the context-pack schema, example, validator, or workflow changes.

This context pack is intentionally workroom-scoped. It references the Professional Intelligence demo workroom, allowed agents, policy decision references, obligation references, search packet references, memory entries, and evidence records. It supplies the memory/context input for the Agentplane workflow bundle, Prophet Workspace workroom fixture, Policy Fabric policy decisions, and ContractForge obligations.

## Slash Topic memory profiles

Memory Mesh defines a memory profile contract for Slash Topic scopes that provides the governance envelope for Lattice query routing (Slash Topics scope → New Hope membrane admission → Memory Mesh profile → lab profile selection → physical backend routing).

The contract, example, and spec live at:

- `schemas/slash-topic-memory-profile.schema.json`
- `examples/slash-topics/memory-profile.example.json`
- `specs/slash-topic-memory-profile.v1.yaml`

Validate locally:

```bash
python -m pip install jsonschema
python scripts/validate_slash_topic_memory_profile.py
```

The workflow `.github/workflows/slash-topic-memory-profile.yml` runs this validation when the schema, example, validator, spec, or workflow changes.

Key properties of this contract:

- **No raw sensitive payloads stored by default** – `recallPolicy.sensitivePayloadStorage` defaults to `"disallowed"`.
- **No memory writeback in dry-run mode** – `writebackPolicy.dryRunMode` must be `"no-writeback"` when dry-run is active.
- **Explicit Lattice mapping** – `dryRun.queryRoutingPlan` carries both `memoryProfileRef` and `memoryEventRef`, matching Lattice `QueryRoutingDryRunPlan` fields.
- **Lab profile selection without lab jobs** – `labProfile.launchLabJobs` is an invariant `false`; embedding/NLP/multimodal tuning applies at recall time only.

This contract coordinates with the Slash Topics / New Hope consolidation work in SocioProphet/slash-topics issue 19.

## Repository semantics

This is the canonical public repository for the runtime and deployment work. It is not a disposable starter artifact.

## Recommended repo split

- `memorymesh` owns the runtime, adapters, importer logic, deployment scaffolding, and build inputs.
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
