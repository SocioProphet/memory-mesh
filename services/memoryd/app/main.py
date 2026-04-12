from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator
from urllib.parse import urlparse

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse

from .embedding import HashingEmbedder
from .mem0_client import Mem0RestClient
from .models import (
    ApplyResourceResponse,
    CompiledWorkloadConfig,
    MeshResource,
    RecallRequest,
    RecallResponse,
    WriteRequest,
    WriteResponse,
    dump_model,
)
from .postgres_store import PostgresStore
from .qdrant_index import QdrantMemoryIndex
from .sqlite_store import SQLiteStore
from .store import InMemoryStore, StoreProtocol, rank_hits_by_policy


REQUIRE_API_KEY = os.getenv('MEMORYD_REQUIRE_API_KEY', 'false').lower() in {'1', 'true', 'yes'}
EXPECTED_API_KEY = os.getenv('MEMORYD_API_KEY', '')
STORE_URI = os.getenv('MEMORYMESH_STORE_URI', os.getenv('MEMORYD_STORE_URL', 'memory://'))
VECTOR_SIZE = int(os.getenv('MEMORYMESH_VECTOR_SIZE', '256'))
QDRANT_ENABLED = os.getenv('QDRANT_ENABLED', 'false').lower() in {'1', 'true', 'yes'}
QDRANT_URL = os.getenv('QDRANT_URL', '').rstrip('/')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY', '')
QDRANT_COLLECTION = os.getenv('QDRANT_COLLECTION', 'memorymesh-local')
QDRANT_DISTANCE = os.getenv('QDRANT_DISTANCE', 'Cosine')
EMBEDDING_SALT = os.getenv('MEMORYMESH_EMBEDDING_SALT', 'memorymesh-starter-v1')

mem0 = Mem0RestClient(
    base_url=os.getenv('MEM0_BASE_URL'),
    api_key=os.getenv('MEM0_API_KEY'),
    timeout_seconds=float(os.getenv('MEM0_TIMEOUT_SECONDS', '10')),
)

vector_index = QdrantMemoryIndex(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY or None,
    collection_name=QDRANT_COLLECTION,
    vector_size=VECTOR_SIZE,
    distance=QDRANT_DISTANCE,
    enabled=QDRANT_ENABLED and bool(QDRANT_URL),
    timeout_seconds=float(os.getenv('QDRANT_TIMEOUT_SECONDS', '10')),
)
embedder = HashingEmbedder(dimension=VECTOR_SIZE, salt=EMBEDDING_SALT)


def build_store(store_uri: str) -> StoreProtocol:
    if not store_uri or store_uri == 'memory://':
        return InMemoryStore()
    if store_uri.startswith('sqlite:///'):
        parsed = urlparse(store_uri)
        return SQLiteStore(db_path=parsed.path, vector_index=vector_index if vector_index.enabled else None)
    if store_uri.startswith('postgresql://') or store_uri.startswith('postgres://'):
        return PostgresStore(dsn=store_uri, schema=os.getenv('MEMORYMESH_PG_SCHEMA', 'memorymesh'), vector_index=vector_index if vector_index.enabled else None)
    raise RuntimeError(f'Unsupported MEMORYMESH_STORE_URI: {store_uri}')


store: StoreProtocol = build_store(STORE_URI)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await store.init()
    yield
    await store.close()


app = FastAPI(title='memoryd', version='0.2.0', lifespan=lifespan)


async def require_api_key(x_api_key: str | None) -> None:
    if not REQUIRE_API_KEY:
        return
    if not EXPECTED_API_KEY:
        raise HTTPException(status_code=500, detail='memoryd api key enforcement enabled but MEMORYD_API_KEY is empty')
    if x_api_key != EXPECTED_API_KEY:
        raise HTTPException(status_code=401, detail='invalid api key')


def ensure_query_vector(request: RecallRequest) -> RecallRequest:
    if request.query_vector is None and vector_index.enabled:
        request.query_vector = embedder.embed(request.query)
    return request


def ensure_write_vector(request: WriteRequest) -> WriteRequest:
    if request.vector is None and vector_index.enabled:
        request.vector = embedder.embed(request.content)
    return request


@app.get('/')
async def root() -> dict:
    return {
        'service': 'memoryd',
        'version': app.version,
        'store_uri': STORE_URI,
        'mem0_enabled': mem0.enabled,
        'vector_enabled': vector_index.enabled,
    }


@app.get('/healthz')
async def healthz() -> dict:
    return {
        'ok': True,
        'mem0_enabled': mem0.enabled,
        'store': await store.health(),
    }


@app.post('/v1/resources/apply', response_model=ApplyResourceResponse)
async def apply_resource(resource: MeshResource, x_api_key: str | None = Header(default=None)) -> ApplyResourceResponse:
    await require_api_key(x_api_key)
    key = await store.apply_resource(resource)
    await store.append_event('resource.applied', {'resource': dump_model(resource)})
    return ApplyResourceResponse(applied=True, resource_key=key)


@app.get('/v1/resources/{kind}/{namespace}/{name}')
async def get_resource(kind: str, namespace: str, name: str, x_api_key: str | None = Header(default=None)) -> dict:
    await require_api_key(x_api_key)
    resource = await store.get_resource(kind=kind, namespace=namespace, name=name)
    if resource is None:
        raise HTTPException(status_code=404, detail='resource not found')
    return dump_model(resource)


@app.get('/v1/config/{workload_id}', response_model=CompiledWorkloadConfig)
async def get_compiled_config(workload_id: str, x_api_key: str | None = Header(default=None)) -> CompiledWorkloadConfig:
    await require_api_key(x_api_key)
    return await store.compile_workload_config(workload_id=workload_id)


async def config_stream(workload_id: str) -> AsyncIterator[str]:
    while True:
        compiled = await store.compile_workload_config(workload_id=workload_id)
        payload = json.dumps(dump_model(compiled), default=str)
        yield f'event: config\ndata: {payload}\n\n'
        await asyncio.sleep(15)


@app.get('/v1/watch/config/{workload_id}')
async def watch_workload_config(workload_id: str, x_api_key: str | None = Header(default=None)) -> StreamingResponse:
    await require_api_key(x_api_key)
    return StreamingResponse(config_stream(workload_id), media_type='text/event-stream')


@app.post('/v1/recall', response_model=RecallResponse)
async def recall(request: RecallRequest, x_api_key: str | None = Header(default=None)) -> RecallResponse:
    await require_api_key(x_api_key)
    request = ensure_query_vector(request)
    compiled = await store.compile_workload_config(workload_id=request.envelope.workload_id)

    local_hits = await store.search_local_memories(request)
    backend_hits = []
    if mem0.enabled and compiled.allow_backend_persistence:
        try:
            backend_hits = await mem0.recall(request)
        except Exception as exc:  # pragma: no cover
            await store.append_event('backend.recall.error', {'error': str(exc), 'query': request.query})

    merged = rank_hits_by_policy(
        local_hits + backend_hits,
        scope_order=compiled.recall_scope_order,
        local_first=compiled.local_first,
    )
    return RecallResponse(query=request.query, hits=merged[: min(request.top_k, compiled.recall_top_k_limit)], compiled_policy=dump_model(compiled))


@app.post('/v1/write', response_model=WriteResponse)
async def write(request: WriteRequest, x_api_key: str | None = Header(default=None)) -> WriteResponse:
    await require_api_key(x_api_key)
    request = ensure_write_vector(request)
    compiled = await store.compile_workload_config(workload_id=request.envelope.workload_id)
    if not compiled.writeback_enabled:
        raise HTTPException(status_code=403, detail='writeback disabled for workload')

    event = await store.append_event(
        'memory.write',
        {
            'envelope': dump_model(request.envelope),
            'content': request.content,
            'memory_class': request.memory_class.value,
            'metadata': request.metadata,
            'tags': request.tags,
        },
    )
    await store.add_local_memory(request=request, event_id=event.event_id)

    backend_memory_ids = []
    if request.persist_to_backend and mem0.enabled and compiled.allow_backend_persistence:
        try:
            backend_memory_ids = await mem0.write(request)
        except Exception as exc:  # pragma: no cover
            await store.append_event('backend.write.error', {'error': str(exc), 'event_id': event.event_id})

    return WriteResponse(event_id=event.event_id, backend_memory_ids=backend_memory_ids, stored_locally=True)


@app.get('/v1/events')
async def list_events(limit: int = 50, x_api_key: str | None = Header(default=None)) -> dict:
    await require_api_key(x_api_key)
    items = [dump_model(item) for item in await store.list_events(limit=limit)]
    return {'items': items}
