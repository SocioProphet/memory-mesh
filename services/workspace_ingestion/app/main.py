"""workspace_ingestion — the Personal Knowledge Graph ingestion service.

Reads prophet-workspace canonical objects → CSKG nodes/edges → normalizes through
HellGraph's CSKG normalizer → persists onto the managed HellGraph → records a
writeback summary in memoryd. Also serves retention retraction. Owns the PKG
runtime (contract = prophet-workspace PersonalContextGraph; substrate =
prophet-platform managed HellGraph).
"""
from __future__ import annotations

import os

from fastapi import FastAPI, Header, HTTPException

from .hellgraph_client import HellGraphClient
from .mapping import build_graph
from .memory_mesh_client import MemoryMeshClient
from .models import (
    IngestWorkspaceRequest,
    IngestWorkspaceResponse,
    RetractRequest,
    RetractResponse,
)

REQUIRE_API_KEY = os.getenv("WORKSPACE_INGESTION_REQUIRE_API_KEY", "false").lower() in {"1", "true", "yes"}
EXPECTED_API_KEY = os.getenv("WORKSPACE_INGESTION_API_KEY", "")

app = FastAPI(title="workspace_ingestion", version="0.1.0")

hellgraph = HellGraphClient(timeout_seconds=float(os.getenv("HELLGRAPH_TIMEOUT_SECONDS", "10")))
memoryd = MemoryMeshClient(timeout_seconds=float(os.getenv("MEMORYD_TIMEOUT_SECONDS", "10")))


async def require_api_key(x_api_key: str | None) -> None:
    if not REQUIRE_API_KEY:
        return
    if not EXPECTED_API_KEY:
        raise HTTPException(status_code=500, detail="api key enforcement enabled but WORKSPACE_INGESTION_API_KEY is empty")
    if x_api_key != EXPECTED_API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")


@app.get("/healthz")
async def healthz() -> dict[str, object]:
    return {"status": "ok", "hellgraph_enabled": hellgraph.enabled, "memoryd_enabled": memoryd.enabled}


@app.post("/v1/ingest/workspace", response_model=IngestWorkspaceResponse)
async def ingest_workspace(request: IngestWorkspaceRequest, x_api_key: str | None = Header(default=None)) -> IngestWorkspaceResponse:
    await require_api_key(x_api_key)
    self_ref = request.self_ref or f"cskg-node://self/{request.envelope.user_id}"

    bundle = build_graph(
        self_ref, request.envelope.user_id,
        contacts=request.contacts, events=request.events,
        messages=request.messages, artifacts=request.artifacts,
    )

    # Refine relations through the CSKG normalizer (no-op if HellGraph is absent).
    bundle.edges = await hellgraph.normalize(bundle.edges)
    normalized = hellgraph.enabled

    hg_result: dict[str, object] = {}
    recall_ref: str | None = None
    if request.persist:
        hg_result = await hellgraph.ingest(bundle)
        # Writeback-after-action: note the graph delta for recall.
        source_refs = sorted({r for n in bundle.nodes for r in n.provenance_refs})
        summary = await memoryd.write_summary(
            envelope=request.envelope.model_dump(),
            content={"event": "personal_context_graph.updated", "self_ref": self_ref,
                     "nodes": len(bundle.nodes), "edges": len(bundle.edges), "source_refs": source_refs},
            tags=["personal-knowledge-graph", "ingest"],
            metadata={"self_ref": self_ref, "workload_id": request.envelope.workload_id},
        )
        recall_ref = summary.get("memory_id") if isinstance(summary, dict) else None

    return IngestWorkspaceResponse(
        self_ref=self_ref, bundle=bundle, normalized=normalized,
        hellgraph=hg_result, recall_candidate_ref=recall_ref,
    )


@app.post("/v1/retract", response_model=RetractResponse)
async def retract(request: RetractRequest, x_api_key: str | None = Header(default=None)) -> RetractResponse:
    """Retention: a WorkspaceSource was deleted → retract its derived edges."""
    await require_api_key(x_api_key)
    result = await hellgraph.retract(request.source_refs)
    return RetractResponse(requested_source_refs=request.source_refs, hellgraph=result)
