"""HellGraph client — writes the person-graph onto the managed graph service.

Targets HellGraph's confirmed contract:
  - POST {HELLGRAPH_URL}/cskg/normalize   → canonicalize raw relations to CSKGEdges
  - POST {HELLGRAPH_URL}/v1/ingest         → persist {nodes, edges} (GraphNode/GraphEdge)
  - POST {HELLGRAPH_URL}/v1/retract        → supersede edges derived from given sources

Graceful-degrade like the other memory-mesh clients (mem0_client, MemoryMeshClient):
if HELLGRAPH_URL is unset the client is disabled and returns an inert result, so
the service runs (and tests pass) without a live graph. HellGraph's write path is
its TS store façade (addNode/addEdge); the /v1/ingest route replays a bundle
through it. The Rust kernel is never written directly.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

from .models import CSKGEdge, CSKGNode, GraphBundle


class HellGraphClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, timeout_seconds: float = 10.0) -> None:
        self.base_url = (base_url or os.getenv("HELLGRAPH_URL") or "").rstrip("/")
        self.api_key = api_key or os.getenv("HELLGRAPH_API_KEY") or ""
        self.timeout_seconds = timeout_seconds

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    @property
    def headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    async def normalize(self, edges: list[CSKGEdge]) -> list[CSKGEdge]:
        """Canonicalize relations through the CSKG normalizer. On absence/failure
        return the edges unchanged (normalization is a refinement, not a gate)."""
        if not self.enabled or not edges:
            return edges
        relations = [{"node1": e.node1, "relation": e.relation, "node2": e.node2,
                      "provenance_ref": (e.provenance_refs[0] if e.provenance_refs else None)} for e in edges]
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(f"{self.base_url}/cskg/normalize",
                                         json={"relations": relations}, headers=self.headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            return edges
        out: list[CSKGEdge] = []
        for i, raw in enumerate(data.get("edges", [])):
            base = edges[i] if i < len(edges) else None
            out.append(CSKGEdge(
                edge_id=raw.get("edge_id") or (base.edge_id if base else f"cskg-edge://{i}"),
                node1=raw.get("node1", base.node1 if base else ""),
                relation=raw.get("relation", base.relation if base else ""),
                node2=raw.get("node2", base.node2 if base else ""),
                provenance_refs=raw.get("provenance_refs") or (base.provenance_refs if base else []),
                source_evidence_refs=raw.get("source_evidence_refs") or (base.source_evidence_refs if base else []),
            ))
        return out or edges

    async def ingest(self, bundle: GraphBundle) -> dict[str, Any]:
        """Persist the bundle (nodes then edges) onto HellGraph."""
        if not self.enabled:
            return {"persisted": False, "reason": "hellgraph disabled", "nodes": len(bundle.nodes), "edges": len(bundle.edges)}
        payload = {
            "nodes": [self._node_wire(n) for n in bundle.nodes],
            "edges": [self._edge_wire(e) for e in bundle.edges],
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.post(f"{self.base_url}/v1/ingest", json=payload, headers=self.headers)
            resp.raise_for_status()
            return dict(resp.json())

    async def retract(self, source_refs: list[str]) -> dict[str, Any]:
        """Retention: supersede every edge derived from the given WorkspaceSources."""
        if not self.enabled:
            return {"retracted": False, "reason": "hellgraph disabled", "source_refs": source_refs}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.post(f"{self.base_url}/v1/retract",
                                     json={"provenance_refs": source_refs}, headers=self.headers)
            resp.raise_for_status()
            return dict(resp.json())

    # ── wire shapes: CSKG → HellGraph GraphNode / GraphEdge ──────────────────
    @staticmethod
    def _node_wire(n: CSKGNode) -> dict[str, Any]:
        return {
            "id": n.node_id,
            "labels": [n.node_type],
            "properties": {
                "label": n.label,
                "memory_scope": n.memory_scope,
                "provenance_refs": ",".join(n.provenance_refs),
                "source_evidence_refs": ",".join(n.source_evidence_refs),
                "external_projection_refs": ",".join(n.external_projection_refs),
            },
        }

    @staticmethod
    def _edge_wire(e: CSKGEdge) -> dict[str, Any]:
        return {
            "id": e.edge_id,
            "label": e.relation,
            "from": e.node1,
            "to": e.node2,
            "properties": {
                # HellGraph-mandatory epistemic fields — workspace imports are confirmed:
                "epistemicClass": "confirmed_relation",
                "confidence": 1.0,
                "promotionState": "confirmed",
                "provenance_refs": ",".join(e.provenance_refs),
                "source_evidence_refs": ",".join(e.source_evidence_refs),
            },
        }
