"""WorkspaceSource → CSKG mapping (the person-graph builder).

Pure functions: canonical workspace records → CSKGNode/CSKGEdge, every element
provenance-bound to the originating WorkspaceSource id. No IO here — the service
layer normalizes + persists. Mirrors the prophet-mesh prototype adapters, but
emits the CSKG wire shape and carries workspace-source provenance_refs.
"""
from __future__ import annotations

import re
from typing import Any

from .models import CSKGEdge, CSKGNode, GraphBundle

# Contact labels/groupRefs hints that reclassify knows → relatedTo (family).
FAMILY_HINTS = {
    "family", "mom", "dad", "mother", "father", "sister", "brother",
    "parent", "child", "sibling", "spouse", "wife", "husband", "son", "daughter",
}


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_") or "x"


def node_id(node_type: str, key: str) -> str:
    return f"cskg-node://{node_type.lower()}/{slug(key)}"


def edge_id(relation: str, n1: str, n2: str) -> str:
    return f"cskg-edge://{relation}/{slug(n1)}-{slug(n2)}"


def _source_ref(rec: dict[str, Any], surface: str, ident: str) -> str:
    return rec.get("sourceId") or f"workspace-source:{surface}/{slug(ident)}"


def _evidence(rec: dict[str, Any]) -> list[str]:
    refs = rec.get("evidenceRefs") or []
    corr = rec.get("evidenceCorrelationId")
    if corr:
        refs = [*refs, corr]
    return list(refs)


class GraphBuilder:
    """Accumulates nodes (deduped by id) and edges for one person-graph."""

    def __init__(self, self_ref: str) -> None:
        self.self_ref = self_ref
        self.nodes: dict[str, CSKGNode] = {}
        self.edges: list[CSKGEdge] = []
        self._edge_ids: set[str] = set()

    def add_node(self, node: CSKGNode) -> None:
        # First writer wins on type/label; merge provenance so a node seen from
        # two sources carries both refs.
        existing = self.nodes.get(node.node_id)
        if existing is None:
            self.nodes[node.node_id] = node
        else:
            existing.provenance_refs = sorted(set(existing.provenance_refs) | set(node.provenance_refs))
            existing.source_evidence_refs = sorted(set(existing.source_evidence_refs) | set(node.source_evidence_refs))
            existing.external_projection_refs = sorted(
                set(existing.external_projection_refs) | set(node.external_projection_refs)
            )

    def add_edge(self, edge: CSKGEdge) -> None:
        if edge.edge_id in self._edge_ids:
            return
        self._edge_ids.add(edge.edge_id)
        self.edges.append(edge)

    def bundle(self) -> GraphBundle:
        return GraphBundle(nodes=list(self.nodes.values()), edges=self.edges)


def seed_self(builder: GraphBuilder, user_id: str) -> None:
    builder.add_node(CSKGNode(
        node_id=builder.self_ref, node_type="Self", label="Self",
        provenance_refs=["workspace-source:onboarding"],
    ))


def adapt_contact(builder: GraphBuilder, rec: dict[str, Any]) -> str:
    cid = rec.get("contactId") or rec.get("displayName") or "unknown"
    if rec.get("contactClass") == "organization":
        oid = node_id("organization", cid)
        builder.add_node(CSKGNode(
            node_id=oid, node_type="Organization", label=rec.get("displayName") or cid,
            provenance_refs=[_source_ref(rec, "contacts", cid)], source_evidence_refs=_evidence(rec),
        ))
        return oid

    nid = node_id("person", cid)
    label = rec.get("displayName") or " ".join(
        p for p in (rec.get("givenName"), rec.get("familyName")) if p
    ) or cid
    src = _source_ref(rec, "contacts", cid)
    ev = _evidence(rec)

    projections = [f"projection:social/{slug(sp.get('handle') or sp.get('url') or 'x')}"
                   for sp in (rec.get("socialProfiles") or [])]
    builder.add_node(CSKGNode(
        node_id=nid, node_type="Person", label=label,
        provenance_refs=[src], source_evidence_refs=ev, external_projection_refs=projections,
    ))

    hints = {h.lower() for h in (rec.get("labels") or [])} | {h.lower() for h in (rec.get("groupRefs") or [])}
    relation = "relatedTo" if hints & FAMILY_HINTS else "knows"
    builder.add_edge(CSKGEdge(
        edge_id=edge_id(relation, builder.self_ref, nid),
        node1=builder.self_ref, relation=relation, node2=nid,
        provenance_refs=[src], source_evidence_refs=ev,
    ))

    org_ref = rec.get("organizationRef")
    if org_ref:
        oid = node_id("organization", org_ref)
        builder.add_node(CSKGNode(
            node_id=oid, node_type="Organization", label=org_ref, provenance_refs=[src], source_evidence_refs=ev,
        ))
        builder.add_edge(CSKGEdge(
            edge_id=edge_id("worksAt", nid, oid), node1=nid, relation="worksAt", node2=oid,
            provenance_refs=[src], source_evidence_refs=ev,
        ))
    return nid


def adapt_event(builder: GraphBuilder, rec: dict[str, Any]) -> str:
    eid = rec.get("eventId") or rec.get("title") or "unknown"
    nid = node_id("event", eid)
    src = _source_ref(rec, "calendar", eid)
    ev = _evidence(rec)
    builder.add_node(CSKGNode(
        node_id=nid, node_type="Event", label=rec.get("title") or eid,
        provenance_refs=[src], source_evidence_refs=ev,
    ))
    builder.add_edge(CSKGEdge(
        edge_id=edge_id("participatedIn", builder.self_ref, nid),
        node1=builder.self_ref, relation="participatedIn", node2=nid,
        provenance_refs=[src], source_evidence_refs=ev,
    ))
    for att in rec.get("attendees") or []:
        if att.get("isSelf"):
            continue
        cref = att.get("contactRef")
        if not cref:
            continue
        pid = node_id("person", cref)
        if pid not in builder.nodes:
            builder.add_node(CSKGNode(
                node_id=pid, node_type="Person", label=att.get("name") or cref,
                provenance_refs=[src], source_evidence_refs=ev,
            ))
        builder.add_edge(CSKGEdge(
            edge_id=edge_id("participatedIn", pid, nid), node1=pid, relation="participatedIn", node2=nid,
            provenance_refs=[src], source_evidence_refs=ev,
        ))
    return nid


def adapt_message(builder: GraphBuilder, rec: dict[str, Any]) -> str | None:
    frm = rec.get("from") or {}
    if frm.get("isSelf"):
        return None
    mid = rec.get("messageId") or "unknown"
    src = _source_ref(rec, "mail", rec.get("threadId") or mid)
    ev = _evidence(rec)
    cref = frm.get("contactRef")
    if cref:
        pid = node_id("person", cref)
        label = frm.get("name") or cref
    else:
        email = frm.get("email", "unknown")
        pid = node_id("person", f"email_{email}")
        label = frm.get("name") or email
    if pid not in builder.nodes:
        builder.add_node(CSKGNode(
            node_id=pid, node_type="Person", label=label, provenance_refs=[src], source_evidence_refs=ev,
        ))
    builder.add_edge(CSKGEdge(
        edge_id=edge_id("communicatedWith", builder.self_ref, pid),
        node1=builder.self_ref, relation="communicatedWith", node2=pid,
        provenance_refs=[src], source_evidence_refs=ev,
    ))
    return pid


def adapt_artifact(builder: GraphBuilder, rec: dict[str, Any]) -> str:
    aid = rec.get("artifactId") or rec.get("title") or "unknown"
    nid = node_id("document", aid)
    src = _source_ref(rec, "office", aid)
    ev = _evidence(rec)
    builder.add_node(CSKGNode(
        node_id=nid, node_type="Document", label=rec.get("title") or aid,
        provenance_refs=[src], source_evidence_refs=ev,
    ))
    builder.add_edge(CSKGEdge(
        edge_id=edge_id("authored", builder.self_ref, nid),
        node1=builder.self_ref, relation="authored", node2=nid,
        provenance_refs=[src], source_evidence_refs=ev,
    ))
    return nid


def build_graph(
    self_ref: str,
    user_id: str,
    *,
    contacts: list[dict] | None = None,
    events: list[dict] | None = None,
    messages: list[dict] | None = None,
    artifacts: list[dict] | None = None,
) -> GraphBundle:
    """Fold a workspace export into a person-graph. People first so calendar/mail
    edges resolve onto existing Person nodes."""
    builder = GraphBuilder(self_ref)
    seed_self(builder, user_id)
    for rec in contacts or []:
        adapt_contact(builder, rec)
    for rec in artifacts or []:
        adapt_artifact(builder, rec)
    for rec in events or []:
        adapt_event(builder, rec)
    for rec in messages or []:
        adapt_message(builder, rec)
    return builder.bundle()
