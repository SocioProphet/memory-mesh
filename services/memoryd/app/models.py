from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field


T = TypeVar('T', bound=BaseModel)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def dump_model(model: Any) -> dict[str, Any]:
    if hasattr(model, 'model_dump'):
        return model.model_dump()  # type: ignore[no-any-return]
    if hasattr(model, 'dict'):
        return model.dict()  # type: ignore[no-any-return]
    raise TypeError(f'Object {type(model)!r} does not support model dumping')


def parse_model(model_type: type[T], payload: dict[str, Any]) -> T:
    if hasattr(model_type, 'model_validate'):
        return model_type.model_validate(payload)  # type: ignore[return-value]
    return model_type.parse_obj(payload)  # type: ignore[return-value]


class MemoryClass(str, Enum):
    interaction = 'interaction'
    fact = 'fact'
    preference = 'preference'
    decision = 'decision'
    summary = 'summary'
    scratch = 'scratch'


class ResourceMetadata(BaseModel):
    namespace: str = 'default'
    name: str
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)


class MeshResource(BaseModel):
    apiVersion: str = 'memorymesh.socioprophet.io/v1alpha1'
    kind: Literal['MemoryAttachment', 'GlobalRecallPolicy', 'MemoryPeer', 'ExportPolicy', 'ConflictPolicy']
    metadata: ResourceMetadata
    spec: dict[str, Any] = Field(default_factory=dict)


class ApplyResourceResponse(BaseModel):
    applied: bool
    resource_key: str


class ScopeEnvelope(BaseModel):
    user_id: str
    agent_id: str
    run_id: str
    workload_id: str
    workspace_id: str | None = None
    channel: str | None = None
    thread_id: str | None = None
    source_interface: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecallRequest(BaseModel):
    envelope: ScopeEnvelope
    query: str
    top_k: int = Field(default=5, ge=1, le=50)
    scope_order: list[str] = Field(default_factory=lambda: ['run', 'agent', 'user'])
    include_relations: bool = False
    include_raw_events: bool = False
    filters: dict[str, Any] = Field(default_factory=dict)
    query_vector: list[float] | None = None


class MemoryHit(BaseModel):
    memory_id: str
    text: str
    score: float
    source: str
    scope: str
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    event_id: str | None = None


class RecallResponse(BaseModel):
    query: str
    hits: list[MemoryHit]
    compiled_policy: dict[str, Any]


class WriteRequest(BaseModel):
    envelope: ScopeEnvelope
    content: str = Field(min_length=1)
    memory_class: MemoryClass = MemoryClass.interaction
    persist_to_backend: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    vector: list[float] | None = None


class WriteResponse(BaseModel):
    event_id: str
    backend_memory_ids: list[str] = Field(default_factory=list)
    stored_locally: bool = True


class EventRecord(BaseModel):
    event_id: str = Field(default_factory=lambda: uuid4().hex)
    event_type: str
    payload: dict[str, Any]
    created_at: datetime = Field(default_factory=utcnow)


class CompiledWorkloadConfig(BaseModel):
    workload_id: str
    recall_scope_order: list[str] = Field(default_factory=lambda: ['run', 'agent', 'user'])
    recall_top_k_limit: int = 10
    local_first: bool = True
    writeback_enabled: bool = True
    allow_backend_persistence: bool = True
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    peers: list[dict[str, Any]] = Field(default_factory=list)
    export_policies: list[dict[str, Any]] = Field(default_factory=list)
    conflict_policies: list[dict[str, Any]] = Field(default_factory=list)
