# Governed learning lifecycle v0.1

## Status

Contract-only continuation of `memory-mesh#22` after the learning representation envelope landed in PR #28.

This tranche models what happens after an agent emits a review-only learning proposal. It keeps the existing Memory Mesh lane as the durable-memory lifecycle owner and does not introduce runtime writeback behavior.

## Lifecycle states

### `accepted-memory`

A reviewed proposal has been approved and promoted into a durable memory or repo-local playbook update.

Required characteristics:

- evidence refs remain attached;
- policy decision refs remain attached;
- approval ref is present;
- writeback ref is present;
- representation envelope is promoted and active.

### `rejected-proposal`

A reviewed proposal is not promoted because evidence is insufficient, policy denies the update, or it conflicts with an authoritative playbook or memory.

Required characteristics:

- rejection ref is present;
- no writeback is performed;
- representation envelope carries `no-writeback`;
- candidate provenance is preserved for audit.

### `revoked-memory`

A previously accepted memory is invalidated because newer evidence, policy, or a superseding playbook entry replaces it.

Required characteristics:

- revocation ref is present;
- tombstone ref is present;
- state is `revoked` instead of deleted;
- supersession links are preserved where known.

### `conflict-reconciliation`

Two or more proposals or memory entries target the same repo-local destination and must be reconciled rather than duplicated.

Required characteristics:

- reconciliation ref is present;
- conflicting refs are listed;
- superseded refs are listed;
- one durable writeback records the reconciled outcome.

## Review queue metrics

Governed learning review is a queue. The metrics fixture records:

- arrivals;
- pending proposals;
- promoted records;
- rejected records;
- revoked records;
- superseded records;
- stale records;
- blocked reasons;
- average, p95, and oldest-pending latency.

These metrics are intended for Sociosphere and DeliveryExcellence integration. Memory Mesh records the contract and fixtures; it does not become the estate scheduler.

## Ownership boundaries

Memory Mesh owns proposal, review, promotion, writeback, revocation, tombstone, and reconciliation lifecycle records.

Ontogenesis owns semantic vocabulary for claims, assertions, evidence, SHIR context, projection, and projection loss.

AgentPlane owns execution evidence and stop-gate artifacts that may produce learning proposals.

Sociosphere owns scheduler/coherence coordination and queue-state aggregation across repos.

Sherlock owns discovery/index packets over these records, not the source of truth.

## Validation

Run:

```bash
python -m pip install jsonschema
make validate-governed-learning-lifecycle
```

The validator enforces basic invariants for accepted, rejected, revoked, and reconciled records, plus review queue metrics consistency.
