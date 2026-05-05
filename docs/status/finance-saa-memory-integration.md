# finance_saa memory integration status

Date: 2026-04-24
Repository: `SocioProphet/memory-mesh`

## Purpose

This document records the current integration state of the `finance_saa` runtime work inside `memory-mesh`, including what is merged, what is tested, what remains unproven, and where the work should integrate next across the wider SocioProphet estate.

## Current merged state

`main` now contains the first memory-backed finance committee vertical slice:

- `memoryd` runtime alignment toward the draft `memory.mesh.v1` contract.
- `finance_saa` bootstrap runtime.
- finance artifact persistence into `memoryd`.
- finance session snapshot persistence.
- snapshot-backed session recovery from `memoryd`.
- runtime validation workflow.
- focused finance source-of-truth test workflow.

## Relevant merged PRs

- PR #6 — draft `memory.mesh.v1` and `finance.saa.v1` contracts plus runtime alignment work.
- PR #8 — finance source-of-truth remediation, moving finance session recovery toward snapshot-backed memory semantics.
- PR #9 — runtime validation workflow for `memoryd` and `finance_saa`.
- PR #10 — focused finance source-of-truth tests and dedicated test workflow.

## Runtime surfaces now present

### `memoryd`

`memoryd` now exposes and/or supports the runtime semantics needed by the current bootstrap slice:

- scoped `ScopeEnvelope` context
- compiled workload configuration
- `config_hash` support
- local memory write IDs
- typed memory events
- workload/workspace-aware recall filtering
- policy-gated raw event and relation recall access

### `finance_saa`

`finance_saa` currently provides an HTTP/FastAPI bootstrap service for:

- session start
- assumptions submit
- proposal submit
- proposal critique
- risk check
- vote record
- decision select

The service persists finance artifacts to `memoryd` and now persists `session_snapshot` artifacts after state mutations. On session lookup, it prefers snapshot-backed recovery from `memoryd` when `FINANCE_SAA_MEMORYD_SOURCE_OF_TRUTH=true`.

## Validation surfaces now present

### Runtime validation

Workflow: `.github/workflows/validate-runtime.yml`

Covers:

- dependency installation for `memoryd` and `finance_saa`
- Python module compilation for runtime services and scripts
- upstream lock validation
- deploy asset validation

### Finance source-of-truth tests

Workflow: `.github/workflows/test-finance-source-of-truth.yml`

Covers:

- snapshot round-trip via `build_session_snapshot()` and `hydrate_snapshot()`
- session recovery from a `memoryd` snapshot
- fallback to local cache when memory is disabled
- memory receipt recording when persisting artifacts

## Known limitations

1. **No confirmed workflow result captured here.** The workflows are present on `main`, but a pass/fail status has not yet been recorded in this status document.
2. **HTTP-first bootstrap remains.** `finance_saa` and `memoryd` are still HTTP/FastAPI surfaces, not TriTRPC-native services.
3. **Snapshot recovery is not full replay.** `finance_saa` recovers session state from snapshots, not from a deterministic event-sourced replay stream.
4. **Typed artifact API is incomplete.** Finance artifacts are still persisted through memory write semantics, not through first-class `Artifact.Write`, `Artifact.Latest`, or `Artifact.ReplaySession` APIs.
5. **Policy is not yet externalized.** Decision gating is still local runtime behavior rather than compiled policy from `policy-fabric`.
6. **Ontology semantics are not yet integrated.** Finance artifacts do not yet have RDF/OWL/JSON-LD classes and SHACL gates in `ontogenesis`.
7. **AgentPlane evidence is not yet wired.** Finance sessions do not yet emit AgentPlane `ValidationArtifact`, `RunArtifact`, `ReplayArtifact`, or promotion/reversal artifacts.
8. **Platform deployment is not yet wired.** `prophet-platform` does not yet carry the deployment profile, platform contract, or eval-fabric receipt surface for this capability.

## Cross-repo ownership map

| Concern | Owning repo | Current status |
|---|---|---|
| Memory substrate and bootstrap finance slice | `SocioProphet/memory-mesh` | Active, merged vertical slice |
| Deterministic RPC and fixtures | `SocioProphet/TriTRPC` | Not yet integrated for this capability |
| Runtime/deployment hub | `SocioProphet/prophet-platform` | Not yet wired |
| Execution/evidence/replay | `SocioProphet/agentplane` | Not yet wired |
| Policy-as-code gates | `SocioProphet/policy-fabric` | Not yet wired |
| Ontology/SHACL semantics | `SocioProphet/ontogenesis` | Not yet wired |
| Human/approval/promotion-adjacent intelligence surface | `SocioProphet/human-digital-twin` | Pattern exists; not yet integrated |

## Recommended next implementation phase

Phase 1 should harden `memoryd` as a typed artifact substrate:

- add `Artifact.Write`
- add `Artifact.Get`
- add `Artifact.List`
- add `Artifact.Latest`
- add `Artifact.ReplaySession`
- add idempotency keys
- add parent artifact hashes
- add monotonic sequence numbers per session
- add tests for deterministic latest-snapshot selection and stale-snapshot rejection

## Completion definition for Phase 1

Phase 1 is complete when `finance_saa` no longer recovers snapshots via free-text recall and instead uses typed artifact APIs for deterministic session reconstruction.

## Follow-on phases

1. Add typed artifact APIs in `memoryd` and migrate `finance_saa` onto them.
2. Add `memory.mesh.v1` and `finance.saa.v1` TriTRPC contract fixtures.
3. Add platform-facing service/deployment contracts in `prophet-platform`.
4. Add ontology modules and SHACL gates in `ontogenesis`.
5. Add policy examples and compiled decision gates in `policy-fabric`.
6. Add AgentPlane bundle/evidence/replay integration.
7. Add estate-level ADR documenting ownership boundaries and integration flow.
