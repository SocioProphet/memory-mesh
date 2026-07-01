"""Pydantic models for the Personal Knowledge Graph ingestion service.

The runtime that turns prophet-workspace canonical objects (WorkspaceSource:
contacts / calendar / mail / office-artifact) into CSKG nodes + edges and writes
them into the managed HellGraph. Edges conform to HellGraph's CSKGEdge shape
{node1, relation, node2, provenance_refs, source_evidence_refs}. This realises the
PersonalContextGraph contract (prophet-workspace) on the substrate
(prophet-platform); memory-mesh owns the runtime.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ScopeEnvelope(BaseModel):
    """Mirrors the memoryd ScopeEnvelope so recall/writeback share one scope."""
    user_id: str
    agent_id: str = "memory-steward"
    run_id: str = "pkg-ingest"
    workload_id: str = "personal-knowledge-graph"
    workspace_id: str | None = None
    source_interface: str = "prophet-workspace"
    metadata: dict[str, Any] = Field(default_factory=dict)


class CSKGNode(BaseModel):
    node_id: str
    node_type: str                       # Self | Person | Place | Organization | Thing | Interest | Event | Document | Communication | Account
    label: str
    provenance_refs: list[str] = Field(default_factory=list)      # workspace-source:… ids (Layer-1 canonical objects)
    source_evidence_refs: list[str] = Field(default_factory=list)
    memory_scope: str = "relationship_context:approved"
    external_projection_refs: list[str] = Field(default_factory=list)  # reference-only external-KG links (via ProviderProjection)


class CSKGEdge(BaseModel):
    edge_id: str
    node1: str
    relation: str                        # relatedTo | knows | worksAt | participatedIn | communicatedWith | authored | …
    node2: str
    provenance_refs: list[str] = Field(default_factory=list)
    source_evidence_refs: list[str] = Field(default_factory=list)


class GraphBundle(BaseModel):
    nodes: list[CSKGNode] = Field(default_factory=list)
    edges: list[CSKGEdge] = Field(default_factory=list)


class IngestWorkspaceRequest(BaseModel):
    """A workspace export to fold into the person-graph. Records are the canonical
    contract shapes (lenient dicts — we consume known fields, ignore the rest)."""
    envelope: ScopeEnvelope
    self_ref: str | None = None          # defaults to cskg-node://self/<user_id>
    contacts: list[dict[str, Any]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    persist: bool = True                 # write through to HellGraph (else dry-run: return the bundle only)


class IngestWorkspaceResponse(BaseModel):
    self_ref: str
    bundle: GraphBundle
    normalized: bool = False             # edges passed through /cskg/normalize
    hellgraph: dict[str, Any] = Field(default_factory=dict)
    recall_candidate_ref: str | None = None


class RetractRequest(BaseModel):
    """Retention: a WorkspaceSource was deleted → retract everything derived from
    it (HellGraph flips those edges to promotionState=superseded)."""
    source_refs: list[str]


class RetractResponse(BaseModel):
    requested_source_refs: list[str]
    hellgraph: dict[str, Any] = Field(default_factory=dict)
