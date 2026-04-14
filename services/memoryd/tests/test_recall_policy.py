from __future__ import annotations

import unittest

from services.memoryd.app.models import MemoryHit, RecallRequest, ScopeEnvelope
from services.memoryd.app.store import rank_hits_by_policy, scope_bonus_for_request, scope_name_for_request


class RecallPolicyTests(unittest.TestCase):
    def make_request(self, *, scope_order: list[str] | None = None) -> RecallRequest:
        return RecallRequest(
            envelope=ScopeEnvelope(
                user_id='lord',
                agent_id='openclaw-main',
                run_id='run-1',
                workload_id='openclaw-gateway',
                workspace_id='workspace-1',
                channel='channel-1',
                thread_id='thread-1',
                source_interface='openclaw',
            ),
            query='open source local memory',
            top_k=5,
            scope_order=scope_order or ['run', 'agent', 'user'],
        )

    def test_scope_name_prefers_thread_channel_workspace_before_run(self) -> None:
        request = self.make_request()
        self.assertEqual(scope_name_for_request(request, {'user_id': 'lord', 'thread_id': 'thread-1'}), 'thread')
        self.assertEqual(scope_name_for_request(request, {'user_id': 'lord', 'channel': 'channel-1'}), 'channel')
        self.assertEqual(scope_name_for_request(request, {'user_id': 'lord', 'workspace_id': 'workspace-1'}), 'workspace')
        self.assertEqual(scope_name_for_request(request, {'user_id': 'lord', 'run_id': 'run-1'}), 'run')

    def test_scope_bonus_respects_configured_order(self) -> None:
        request = self.make_request(scope_order=['agent', 'run', 'user'])
        agent_bonus, _ = scope_bonus_for_request(request, {'user_id': 'lord', 'agent_id': 'openclaw-main'})
        run_bonus, _ = scope_bonus_for_request(request, {'user_id': 'lord', 'run_id': 'run-1'})
        self.assertGreater(agent_bonus, run_bonus)

    def test_rank_hits_prefers_local_sources_when_local_first(self) -> None:
        hits = [
            MemoryHit(memory_id='backend-run', text='remote run context', score=6.0, source='mem0', scope='run'),
            MemoryHit(memory_id='local-agent', text='local agent context', score=5.0, source='memoryd.sqlite', scope='agent'),
        ]
        ranked = rank_hits_by_policy(hits, scope_order=['agent', 'run', 'user'], local_first=True)
        self.assertEqual(ranked[0].memory_id, 'local-agent')

    def test_rank_hits_prefers_scope_when_local_first_disabled(self) -> None:
        hits = [
            MemoryHit(memory_id='local-user', text='local user context', score=9.0, source='memoryd.sqlite', scope='user'),
            MemoryHit(memory_id='backend-run', text='remote run context', score=7.0, source='mem0', scope='run'),
        ]
        ranked = rank_hits_by_policy(hits, scope_order=['run', 'agent', 'user'], local_first=False)
        self.assertEqual(ranked[0].memory_id, 'backend-run')

    def test_scope_bonus_hard_filters_by_workload_id(self) -> None:
        request = self.make_request()
        # Memory tagged to a different workload must be excluded
        bonus, scope = scope_bonus_for_request(
            request, {'user_id': 'lord', 'run_id': 'run-1', 'workload_id': 'other-workload'}
        )
        self.assertEqual(bonus, -1.0)
        self.assertEqual(scope, 'none')
        # Memory tagged to the same workload must not be excluded
        bonus2, _ = scope_bonus_for_request(
            request, {'user_id': 'lord', 'run_id': 'run-1', 'workload_id': 'openclaw-gateway'}
        )
        self.assertGreater(bonus2, 0)
        # Memory without a workload_id tag must not be excluded (backward compat)
        bonus3, _ = scope_bonus_for_request(request, {'user_id': 'lord', 'run_id': 'run-1'})
        self.assertGreater(bonus3, 0)

    def test_scope_bonus_hard_filters_by_workspace_id_when_both_set(self) -> None:
        request = self.make_request()
        # Memory in a different workspace must be excluded when both sides have a workspace_id
        bonus, scope = scope_bonus_for_request(
            request, {'user_id': 'lord', 'run_id': 'run-1', 'workspace_id': 'other-workspace'}
        )
        self.assertEqual(bonus, -1.0)
        self.assertEqual(scope, 'none')
        # Memory without workspace_id must not be excluded (request has workspace, env does not)
        bonus2, _ = scope_bonus_for_request(request, {'user_id': 'lord', 'run_id': 'run-1'})
        self.assertGreater(bonus2, 0)


if __name__ == '__main__':
    unittest.main()
