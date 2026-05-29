# Channel provenance and memory write gates v0.1

## Status

Contract-only Memory Mesh consumer of ProCybernetica Reciprocal Channel Governance and the Ontogenesis `rcg:` semantic mirror.

This tranche does not introduce runtime writeback. It defines the memory-side discipline required before channel-conditioned observations can become durable memory.

## Placement

Memory Mesh owns durable memory proposal, review, promotion, writeback, revocation, tombstone, and reconciliation records.

ProCybernetica owns reciprocal channel governance doctrine and JSON-schema contract vocabulary.

Ontogenesis owns the RDF/OWL/SHACL semantic mirror for `Channel`, `Percept`, `InterpretantCandidate`, `CollapseDecision`, `RepairEvent`, `ProjectionProfile`, and `ChannelAuthorityEnvelope`.

AgentPlane owns execution evidence that may produce memory proposals.

Sociosphere owns cross-repo queue/coherence scheduling.

Sherlock owns discovery/index packets and must not become the memory source of truth.

## Memory-specific rule

No durable memory without channel lineage.

A memory candidate must preserve the channel-conditioned path by which it was observed, inferred, repaired, collapsed, reviewed, and authorized. The memory sink must not treat ASR output, model summaries, graph slices, dashboards, OCR, telemetry, or agent reports as clean fact.

## Memory classes

Memory Mesh should distinguish at least these classes:

- `observed_memory` — directly captured from a channel, still channel-conditioned;
- `inferred_memory` — model- or agent-derived from observations;
- `confirmed_memory` — explicitly validated by user, policy, artifact, or authoritative source;
- `operational_memory` — current working state with expiry/revalidation;
- `doctrine_memory` — durable doctrine or standing operating guidance;
- `preference_memory` — user or operator preference, scoped and revisable;
- `entity_memory` — relation-bearing memory that should later align to entity graph rules;
- `stale_memory` — not deleted, but no longer safe for default retrieval;
- `contested_memory` — disputed by newer evidence, user correction, or policy;
- `superseded_memory` — replaced by a newer confirmed record;
- `revoked_memory` — tombstoned rather than deleted.

## Write-gate requirements

A candidate memory is not promotable unless it declares:

1. source channel lineage;
2. percept and interpretant provenance;
3. confusability modes known at capture time;
4. collapse decision, if an interpretation was selected from alternatives;
5. repair events or explicit no-repair rationale;
6. confidence type, not only confidence level;
7. authority envelope for the source channel;
8. allowed and disallowed memory sinks;
9. promotion state;
10. review state;
11. evidence references;
12. policy decision references;
13. redaction posture;
14. expiry or revalidation posture.

## Forbidden promotions

The memory write gate must reject or keep review-only any proposal where:

- ASR or OCR output attempts to write confirmed memory without repair;
- a model summary attempts to write durable memory without source artifacts;
- a dashboard projection attempts to write whole-estate memory without coverage basis;
- a graph slice attempts to write a relation as confirmed fact without edge provenance;
- an agent report attempts to write operational truth without execution evidence;
- a stale memory attempts to reactivate itself without revalidation;
- a sensitive observer-profile inference attempts to persist without authorization;
- a high-risk sink is requested without repair, review, and policy decision refs.

## Integration with existing Memory Mesh lanes

`AgentLearningProposal` remains the review-only ingress surface for agent-discovered operational learning.

The governed learning lifecycle remains the durable promotion/rejection/revocation/reconciliation lifecycle.

This tranche adds a channel-provenance gate that can be referenced by those records before writeback is approved.

## Runtime non-claim

This document defines contract and validation posture only. It does not implement production memory writeback, agent execution, policy runtime, graph promotion, or connector ingestion.
