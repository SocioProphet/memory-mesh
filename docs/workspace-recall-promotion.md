# Workspace Recall Promotion

## Purpose

This document defines the Memory Mesh handoff for Workspace Context Fabric recall candidates.

Prophet Workspace owns the workroom-facing `RecallCandidate` object. Memory Mesh owns the review and promotion path for durable recall records.

## Boundary

The v0.1 path is review-only by default:

```text
Workspace RecallCandidate
  -> WorkspaceRecallPromotionPacket
  -> AgentLearningProposal-compatible review queue
  -> approved durable record only after review
```

Memory Mesh does not silently promote workspace context into durable recall. The packet preserves refs to the workroom, context graph, runtime binding, AgentPlane evidence, platform evidence, and policy decisions.

## Object

The first object is:

```text
schemas/workspace-recall-promotion-packet.schema.json
examples/workspace-recall/promotion-packet.example.json
```

## Required posture

- source workspace refs are preserved;
- review mode defaults to `review_only`;
- raw sensitive payload storage is false in the example;
- durable action is disabled until review approval;
- evidence and policy refs are mandatory;
- AgentPlane and Prophet Platform refs remain external authority refs.

## Validation

```bash
python scripts/validate_workspace_recall_promotion_packet.py
```
