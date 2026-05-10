# Learning representation envelope v0.1

## Status

Draft implementation slice for `memory-mesh#22`.

This document folds the communications-systems-derived learning representation doctrine into the existing governed memory proposal channel. It does not create a second durable-memory architecture. `AgentLearningProposal` remains the review-only ingress surface for agent-discovered operational learning.

## Placement

Memory Mesh owns durable memory proposal, review, promotion, writeback, revocation, and playbook reconciliation.

Ontogenesis owns the semantic vocabulary for claims, assertions, evidence, SHIR context, projection, and projection-loss reporting.

AgentPlane owns guarded execution, run evidence, stop-gate artifacts, typed traces, and detector/evaluator receipts.

Sociosphere owns queueing, topology, scheduler state, coherence barriers, and cross-repo orchestration.

Sherlock owns discovery/index packets and must not become the memory source of truth.

## Communications-system mapping

The MIT communications stack gives six constraints for governed learning memory:

1. Sampling: learning proposals must identify the bounded observation window and freshness posture behind the learning.
2. Framing: a learning must be a typed frame with source session, destination, evidence, policy, review, redaction, and writeback state.
3. Compression: summaries and playbook diffs are allowed only when they preserve evidence, provenance, authority, unresolved conflicts, and retention.
4. Detection: detector-derived learnings must expose their signal class, noise assumption, confidence, and abstention boundary.
5. Error/provenance: schema validity, checksum validity, semantic truth, and policy approval are separate states.
6. Queueing: review/promotion should be measurable as a queue, including arrival, blocked reason, staleness, and promotion latency.

## Extension fields

The first implementation slice extends `AgentLearningProposal` with optional contract fields. They are optional for backward compatibility but should be populated by new producers.

### `observationContext`

Captures the sampling and compression basis behind a proposed learning.

Required when present:

- `observedAt`
- `validTime`
- `freshnessPolicy`
- `samplingBasis`
- `compressionBasis`

The field prevents unbounded transcript residue from being promoted as durable memory. It requires the producer to say what was observed and what was compressed.

### `representationEnvelope`

Captures frame, authority, cache/coherence, evidence, provenance, policy, and write policy.

Required when present:

- `frameType`
- `authoritySource`
- `sourceEpoch`
- `validityWindow`
- `cacheState`
- `dirtyState`
- `revocationStatus`
- `correlationId`
- `evidenceRefs`
- `provenanceRefs`
- `policyContext`
- `writePolicy`

The cache/coherence vocabulary aligns with Sociosphere's scheduler/coherence lane. Memory Mesh records it as metadata; it does not become the global scheduler.

### `learningSignal`

Captures the signal/detector context when a proposed learning comes from an agent observation, detector, ranker, evaluator, or mixed process.

Required when present:

- `signalClass`
- `noiseAssumption`
- `confidence`
- `abstentionBoundary`

This prevents a model or agent from hiding a detector assumption behind prose.

### `reviewQueue`

Captures queue metadata for proposal review and promotion.

Required when present:

- `proposalArrivedAt`
- `reviewRequiredBy`
- `blockedReason`
- `staleAfter`

The purpose is observability. Review queue metrics should flow to DeliveryExcellence/Sociosphere rather than becoming local-only comments.

## Invariants

- No raw sensitive payload is stored by default.
- No durable writeback occurs in `review_only` mode.
- No accepted memory exists without evidence refs.
- No cross-repo or global memory promotion occurs without policy decision refs.
- No detector-derived learning is actionable without signal/noise assumptions.
- No compressed playbook update may erase provenance or conflicts.
- No rejected, revoked, superseded, or stale learning may remain silently active.

## First validation slice

This tranche updates:

- `schemas/agent-learning-proposal.schema.json`
- `examples/agent-learning/proposal.example.json`

Existing validation remains:

```bash
python -m pip install jsonschema
make validate-agent-learning-proposal
```

## Future slices

1. Add companion accepted-memory and revoked-memory examples.
2. Add conflict/supersession examples for duplicate or contradictory playbook learnings.
3. Emit derived queue metrics for pending proposal age, blocked reason, stale count, promotion latency, and rejection rate.
4. Align Ontogenesis terms to SHIR `Assertion`, `Evidence`, `Receipt`, `Context`, and `ProjectionLossReport`.
5. Align Sociosphere representation envelope fields with scheduler/coherence schemas.
