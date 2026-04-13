# Content, Support, and Ops Memory Loop Design

## Purpose

This document defines how `memory-mesh` participates in the governed control loop for content, support, premium support, query orchestration, and operations-domain intelligence.

`memory-mesh` is the long-horizon retained memory layer. It does not replace the query plane, ontology plane, or ops-domain intelligence plane. It retains history, prior decisions, prior outcomes, accepted and rejected recommendations, reusable context, and recall-before-change signals.

## Repository role

`memory-mesh` owns:

- recall-before-call / recall-before-change runtime seams
- writeback-after-call / writeback-after-outcome seams
- retained support, query, and ops-context history
- prior-case linkage and repeated-resolution memory
- optional vector retrieval and deterministic memory embeddings for bring-up

It does not own:

- semantic meaning of memory classes (`ontogenesis`)
- base storage standards (`socioprophet-standards-storage`)
- ops-domain normalization of raw logs and anomalies (`global-devsecops-intelligence`)
- canonical query orchestration (`sherlock-search`)

## Core memory objects

`memory-mesh` should retain, at minimum, typed records linked to the upstream semantic classes.

### `MemoryRecord`
Canonical retained unit for prior context.

### `SupportInteractionMemory`
Retained support interaction history, linked to support tier, domain, category, outcome, and evidence.

### `AssetUsageMemory`
History of which assets, templates, or runbooks were used for what task, under what support tier, with what result.

### `RecommendationHistory`
Accepted, rejected, ignored, or superseded recommendations, including premium-support recommendations and ops recommendations.

### `IncidentResolutionMemory`
Prior anomaly, incident-story, and ticket-resolution history derived from normalized ops-domain intelligence.

### `OverlayMemory`
Premium-overlay, tenant-overlay, or customer-specific conventions, exclusions, prior decisions, vocabulary, and local preferences.

### `LearningLinkMemory`
Memory handles linking retained history to learning objectives and curriculum objects in `alexandrian-academy`.

## Required behaviors

### Recall before change
Before a support recommendation, content promotion, asset revision, or ops remediation is proposed, the runtime should be able to query `memory-mesh` for:

- prior similar interactions
- prior accepted or rejected recommendations
- prior anomaly/remediation pairings
- prior support-tier-specific overlays
- prior objections or unresolved confusion signals

### Writeback after outcome
After an interaction or action completes, `memory-mesh` should persist:

- outcome state
- linked assets and evidence
- recommendation acceptance or rejection
- support tier and overlay context
- operational context references when present
- associated learning-objective references when present

### Cross-plane linkability
Memory records must be linkable to:

- Sherlock query IDs and result sets
- support interactions and escalation packets
- incident stories and anomaly findings from `global-devsecops-intelligence`
- learning objectives and curriculum objects from `alexandrian-academy`
- action/replay/evidence handles from `agentplane`

## Retrieval lanes

### Support recall
Used by standard and premium support to retrieve similar cases, prior runbooks, prior objections, and prior successful resolution paths.

### Query recall
Used by `sherlock-search` to enrich query planning and result ranking with prior decision context.

### Ops recall
Used by operational intelligence and support systems to remember repeated anomalies, recurring incident stories, and prior remediation outcomes.

### Learning recall
Used to feed learning-objective evaluation and explanation-quality refinement in `alexandrian-academy`.

## Premium support implications

Premium support should not fork the memory system. It should use the same memory substrate with explicit overlay and entitlement controls.

Premium support memory may include:

- tenant-specific incidents and support narratives
- customer-approved workarounds and exclusions
- local naming conventions and vocabulary
- TAM / SME handoff history
- premium-only overlay assets and resolution patterns

These overlays must remain policy-scoped and traceable.

## Integration map

- `ontogenesis`: semantic meaning of `MemoryRecord` and related classes
- `socioprophet-standards-storage`: transport and storage invariants for memory-linked payloads
- `sherlock-search`: query-plane consumer of memory context
- `global-devsecops-intelligence`: producer of normalized ops-domain findings that can be written into retained memory
- `alexandrian-academy`: producer/consumer of learning-linked memory context
- `agentplane`: producer of replay/evidence handles attached to memory writebacks
- `prophet-platform`: runtime and API host for memory-aware workflows

## Immediate implementation tranche

1. Define the retained-memory object families and their typed references.
2. Add recall-before-change guidance for support and query workflows.
3. Add writeback-after-outcome guidance for support, ops, and content workflows.
4. Ensure memory records preserve support tier, overlay provenance, and evidence linkage.

## Outcome

When implemented correctly, `memory-mesh` becomes the retained memory substrate that lets support, premium support, query orchestration, and ops intelligence learn from prior outcomes instead of operating as stateless loops.
