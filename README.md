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

## Lampstand adapter-record promotion packets

Memory Mesh now carries a review-only promotion-packet contract for Lampstand governed adapter records.

This is the bridge from local evidence to durable memory without collapsing authority boundaries:

- Lampstand remains the `adapter_records` source authority.
- Sherlock may search adapter records as local evidence.
- Memory Mesh receives reviewable promotion candidates.
- Durable writeback remains disabled unless explicitly approved later.

The contract, example, and validator live at:

- `schemas/lampstand-adapter-record-promotion-packet.schema.json`
- `examples/lampstand/adapter-record-promotion-packet.example.json`
- `scripts/validate_lampstand_adapter_record_promotion_packet.py`

Validate locally:

```bash
python -m pip install jsonschema
python scripts/validate_lampstand_adapter_record_promotion_packet.py
```

The workflow `.github/workflows/lampstand-adapter-record-promotion-packet.yml` runs this validation when the promotion packet schema, example, validator, or workflow changes.

The example enforces review-only promotion mode, local-only record classification, policy decision references, evidence references, and source-record linkage for every promotion candidate.

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

Memory Mesh defines a memory profile contract for Slash Topic scopes that provides the governance envelope for Lattice query routing.

The explicit route is:

1. Slash Topics is the public query and governance surface.
2. New Hope is the internal membrane and runtime substrate.
3. Memory Mesh attaches to Slash Topic scope after New Hope membrane admission.
4. Lab profile selection configures recall-time embedding, NLP, and multimodal behavior.
5. Physical backend routing remains downstream of the governed memory profile.

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
- **Explicit Lattice mapping** – `dryRun.queryRoutingPlan` carries `memoryProfileRef`, `memoryEventRef`, `publicSurfaceRef`, `runtimeSubstrateRef`, `runtimeAliasRef`, and `compatibilityRef`, matching Lattice `QueryRoutingDryRunPlan` fields.
- **Explicit Slash Topics / New Hope topology** – `topologyRoles.publicSurfaceRef` is `slash-topics-public-surface`; `runtimeSubstrateRef` is `new-hope-runtime-substrate`; `runtimeAliasRef` is `slash-topics-runtime-alias`; and `compatibilityRef` is `new-hope-compatibility`.
- **Lab profile selection without lab jobs** – `labProfile.launchLabJobs` is an invariant `false`; embedding/NLP/multimodal tuning applies at recall time only.

This contract coordinates with the Slash Topics / New Hope consolidation work in SocioProphet/slash-topics issue 19 and the explicit role split enforced by SocioProphet/sociosphere PR 236, emitted by SocioProphet/prophet-platform PR 290, and indexed by SocioProphet/sherlock-search PR 26.

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
