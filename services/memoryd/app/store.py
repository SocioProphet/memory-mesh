from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Protocol
from uuid import uuid4

from .models import CompiledWorkloadConfig, EventRecord, MemoryHit, MeshResource, RecallRequest, WriteRequest, dump_model


class StoreProtocol(Protocol):
    async def init(self) -> None: ...
    async def close(self) -> None: ...
    async def apply_resource(self, resource: MeshResource) -> str: ...
    async def get_resource(self, kind: str, namespace: str, name: str) -> MeshResource | None: ...
    async def append_event(self, event_type: str, payload: dict) -> EventRecord: ...
    async def list_events(self, limit: int = 50) -> list[EventRecord]: ...
    async def compile_workload_config(self, workload_id: str) -> CompiledWorkloadConfig: ...
    async def add_local_memory(self, request: WriteRequest, event_id: str) -> str: ...
    async def search_local_memories(self, request: RecallRequest) -> list[MemoryHit]: ...
    async def health(self) -> dict: ...


class InMemoryStore:
    def __init__(self) -> None:
        self._resources: dict[str, MeshResource] = {}
        self._events: list[EventRecord] = []
        self._memories: dict[str, dict] = {}
        self._resource_index: dict[str, list[str]] = defaultdict(list)

    async def init(self) -> None:
        return None

    async def close(self) -> None:
        return None

    @staticmethod
    def resource_key(kind: str, namespace: str, name: str) -> str:
        return f'{kind}:{namespace}:{name}'

    async def apply_resource(self, resource: MeshResource) -> str:
        key = self.resource_key(resource.kind, resource.metadata.namespace, resource.metadata.name)
        self._resources[key] = resource
        self._resource_index[resource.kind].append(key)
        return key

    async def get_resource(self, kind: str, namespace: str, name: str) -> MeshResource | None:
        return self._resources.get(self.resource_key(kind, namespace, name))

    async def append_event(self, event_type: str, payload: dict) -> EventRecord:
        event = EventRecord(event_type=event_type, payload=payload)
        self._events.append(event)
        return event

    async def list_events(self, limit: int = 50) -> list[EventRecord]:
        return list(reversed(self._events[-limit:]))

    async def compile_workload_config(self, workload_id: str) -> CompiledWorkloadConfig:
        return compile_workload_config_from_resources(self._resources.values(), workload_id=workload_id)

    async def add_local_memory(self, request: WriteRequest, event_id: str) -> str:
        memory_id = uuid4().hex
        record = {
            'memory_id': memory_id,
            'text': request.content,
            'memory_class': request.memory_class.value,
            'tags': list(request.tags),
            'metadata': dict(request.metadata),
            'event_id': event_id,
            'envelope': dump_model(request.envelope),
        }
        self._memories[memory_id] = record
        return memory_id

    async def search_local_memories(self, request: RecallRequest) -> list[MemoryHit]:
        query_tokens = tokenize(request.query)
        hits: list[MemoryHit] = []
        for record in self._memories.values():
            env = record['envelope']
            scope_bonus, scope_name = scope_bonus_for_request(request, env)
            if scope_bonus < 0:
                continue
            overlap = token_overlap(query_tokens, tokenize(record['text']))
            if overlap <= 0 and request.query.lower() not in record['text'].lower():
                continue
            score = overlap + scope_bonus
            hits.append(
                MemoryHit(
                    memory_id=record['memory_id'],
                    text=record['text'],
                    score=score,
                    source='memoryd.memory',
                    scope=scope_name,
                    tags=record['tags'],
                    metadata=record['metadata'],
                    event_id=record['event_id'],
                )
            )
        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[: request.top_k]

    async def health(self) -> dict:
        return {
            'backend': 'memory',
            'resource_count': len(self._resources),
            'event_count': len(self._events),
            'memory_count': len(self._memories),
        }


def compile_workload_config_from_resources(resources: Iterable[MeshResource], *, workload_id: str) -> CompiledWorkloadConfig:
    attachments: list[dict] = []
    peers: list[dict] = []
    export_policies: list[dict] = []
    conflict_policies: list[dict] = []
    recall_scope_order = ['run', 'agent', 'user']
    recall_top_k_limit = 10
    local_first = True
    writeback_enabled = True
    allow_backend_persistence = True

    for resource in resources:
        spec = resource.spec or {}
        targets = set(spec.get('targetWorkloads') or spec.get('workloadIds') or [])
        applies = not targets or workload_id in targets or spec.get('workloadId') == workload_id or resource.metadata.name == workload_id
        if not applies:
            continue
        dumped = dump_model(resource)
        if resource.kind == 'MemoryAttachment':
            attachments.append(dumped)
            policy = spec.get('policy') or {}
            recall_scope_order = list(policy.get('scopeOrder') or policy.get('scope_order') or recall_scope_order)
            recall_top_k_limit = int(policy.get('topKLimit') or policy.get('recall_top_k') or recall_top_k_limit)
            writeback_enabled = bool(policy.get('writebackEnabled', policy.get('writeback_enabled', writeback_enabled)))
            allow_backend_persistence = bool(policy.get('allowBackendPersistence', policy.get('allow_backend_persistence', allow_backend_persistence)))
            local_first = bool(policy.get('localFirst', policy.get('local_first', local_first)))
        elif resource.kind == 'MemoryPeer':
            peers.append(dumped)
        elif resource.kind == 'ExportPolicy':
            export_policies.append(dumped)
        elif resource.kind == 'ConflictPolicy':
            conflict_policies.append(dumped)
        elif resource.kind == 'GlobalRecallPolicy':
            recall_scope_order = list(spec.get('scopeOrder') or spec.get('scope_order') or recall_scope_order)
            recall_top_k_limit = int(spec.get('topKLimit') or spec.get('recall_top_k') or recall_top_k_limit)
            local_first = bool(spec.get('localFirst', spec.get('local_first', local_first)))
            writeback_enabled = bool(spec.get('writebackEnabled', spec.get('writeback_enabled', writeback_enabled)))
            allow_backend_persistence = bool(spec.get('allowBackendPersistence', spec.get('allow_backend_persistence', allow_backend_persistence)))

    return CompiledWorkloadConfig(
        workload_id=workload_id,
        recall_scope_order=recall_scope_order,
        recall_top_k_limit=recall_top_k_limit,
        local_first=local_first,
        writeback_enabled=writeback_enabled,
        allow_backend_persistence=allow_backend_persistence,
        attachments=attachments,
        peers=peers,
        export_policies=export_policies,
        conflict_policies=conflict_policies,
    )


def tokenize(text: str) -> set[str]:
    return {token.strip('.,!?;:()[]{}').lower() for token in text.split() if token.strip()}


def token_overlap(query_tokens: set[str], text_tokens: set[str]) -> float:
    if not query_tokens or not text_tokens:
        return 0.0
    return float(len(query_tokens & text_tokens))


def scope_bonus_for_request(request: RecallRequest, env: dict) -> tuple[float, str]:
    req = request.envelope
    if env.get('run_id') == req.run_id:
        return 3.0, 'run'
    if env.get('agent_id') == req.agent_id and env.get('user_id') == req.user_id:
        return 2.0, 'agent'
    if env.get('user_id') == req.user_id:
        return 1.0, 'user'
    return -1.0, 'none'


def dedupe_hits(hits: list[MemoryHit]) -> list[MemoryHit]:
    best_by_id: dict[str, MemoryHit] = {}
    for hit in hits:
        existing = best_by_id.get(hit.memory_id)
        if existing is None or hit.score > existing.score:
            best_by_id[hit.memory_id] = hit
    return list(best_by_id.values())
