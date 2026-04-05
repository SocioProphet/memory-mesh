from __future__ import annotations

import tempfile
import unittest

from services.memoryd.app.models import MeshResource, RecallRequest, ScopeEnvelope, WriteRequest
from services.memoryd.app.store import InMemoryStore
from services.memoryd.app.sqlite_store import SQLiteStore


class StoreTests(unittest.IsolatedAsyncioTestCase):
    def make_envelope(self) -> ScopeEnvelope:
        return ScopeEnvelope(
            user_id='lord',
            agent_id='openclaw-main',
            run_id='run-1',
            workload_id='openclaw-gateway',
            source_interface='openclaw',
        )

    async def test_inmemory_write_and_recall(self) -> None:
        store = InMemoryStore()
        req = WriteRequest(envelope=self.make_envelope(), content='User prefers local-first tools and open source')
        event = await store.append_event('memory.write', {'content': req.content})
        await store.add_local_memory(req, event.event_id)

        recall = await store.search_local_memories(
            RecallRequest(
                envelope=self.make_envelope(),
                query='What tools does the user prefer?',
                top_k=5,
            )
        )
        self.assertTrue(recall)
        self.assertIn('local-first', recall[0].text)

    async def test_compile_config_from_attachment(self) -> None:
        store = InMemoryStore()
        resource = MeshResource(
            kind='MemoryAttachment',
            metadata={'name': 'openclaw-gateway', 'namespace': 'default'},
            spec={'workloadId': 'openclaw-gateway', 'policy': {'recall_top_k': 7, 'writeback_enabled': False}},
        )
        await store.apply_resource(resource)
        compiled = await store.compile_workload_config('openclaw-gateway')
        self.assertEqual(compiled.recall_top_k_limit, 7)
        self.assertFalse(compiled.writeback_enabled)

    async def test_sqlite_store_is_durable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = f'{tmp}/memorymesh.db'
            store = SQLiteStore(db_path=path)
            await store.init()
            req = WriteRequest(envelope=self.make_envelope(), content='The project name is memorymesh')
            event = await store.append_event('memory.write', {'content': req.content})
            await store.add_local_memory(req, event.event_id)

            reopened = SQLiteStore(db_path=path)
            await reopened.init()
            recall = await reopened.search_local_memories(
                RecallRequest(envelope=self.make_envelope(), query='What is the project name?', top_k=3)
            )
            self.assertTrue(recall)
            self.assertIn('memorymesh', recall[0].text)
