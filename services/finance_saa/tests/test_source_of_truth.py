from __future__ import annotations

import json
import unittest
from datetime import date, datetime, timezone

from services.finance_saa.app import main as finance_main
from services.finance_saa.app.models import DecisionPack, PortfolioMetrics, PortfolioProposal, PortfolioWeight


def sample_session_payload() -> dict:
    return {
        'envelope': {
            'user_id': 'u1',
            'agent_id': 'finance-agent',
            'run_id': 'run-1',
            'workload_id': 'wl-1',
            'workspace_id': 'ws-1',
            'channel': None,
            'thread_id': None,
            'source_interface': 'finance_saa',
            'metadata': {},
        },
        'context': {
            'mandate_id': 'mandate-1',
            'workload_id': 'wl-1',
            'valuation_date': str(date(2026, 4, 15)),
            'data_cutoff': str(datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc)),
            'benchmark_id': 'bench-1',
            'universe_id': 'uni-1',
            'ips_resource_keys': ['ips/a'],
        },
        'notes': 'bootstrap',
    }


def sample_proposal() -> PortfolioProposal:
    return PortfolioProposal(
        proposal_id='proposal-1',
        method_id='equal-weight',
        weights=[PortfolioWeight(asset_id='asset-a', weight=0.5), PortfolioWeight(asset_id='asset-b', weight=0.5)],
        metrics=PortfolioMetrics(expected_return=0.08, expected_volatility=0.12, expected_sharpe=0.66),
        evidence_refs=[{'kind': 'test'}],
    )


class FinanceSourceOfTruthTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        finance_main._sessions.clear()
        finance_main._assumptions.clear()
        finance_main._proposals.clear()
        finance_main._critiques.clear()
        finance_main._votes.clear()
        finance_main._risk_checks.clear()
        finance_main._decisions.clear()
        finance_main._events.clear()
        finance_main._memory_receipts.clear()
        finance_main.MEMORYD_SOURCE_OF_TRUTH = True
        finance_main.memoryd.enabled = True

    async def test_build_and_hydrate_session_snapshot_round_trip(self) -> None:
        session_id = 'sess-1'
        finance_main._sessions[session_id] = sample_session_payload()
        finance_main._assumptions[session_id] = [{'assumption_set_id': 'a1', 'role': 'macro'}]
        finance_main._proposals[session_id] = {'proposal-1': sample_proposal()}
        finance_main._critiques[session_id] = [{'critique_id': 'c1'}]
        finance_main._votes[session_id] = [{'ballot_id': 'b1'}]
        finance_main._risk_checks[session_id] = [{'proposal_id': 'proposal-1', 'passed': True}]
        finance_main._decisions[session_id] = DecisionPack(
            decision_id='decision-1',
            selected_proposal_id='proposal-1',
            rationale='ok',
            approval_mode='bootstrap-majority',
            metrics={'expected_return': 0.08},
            evidence_refs=[{'kind': 'session'}],
        )

        snapshot = finance_main.build_session_snapshot(session_id)

        finance_main._sessions.clear()
        finance_main._assumptions.clear()
        finance_main._proposals.clear()
        finance_main._critiques.clear()
        finance_main._votes.clear()
        finance_main._risk_checks.clear()
        finance_main._decisions.clear()

        hydrated = finance_main.hydrate_snapshot(session_id, snapshot)
        self.assertIsNotNone(hydrated)
        self.assertEqual(finance_main._sessions[session_id]['context']['mandate_id'], 'mandate-1')
        self.assertEqual(len(finance_main._assumptions[session_id]), 1)
        self.assertIn('proposal-1', finance_main._proposals[session_id])
        self.assertIsInstance(finance_main._proposals[session_id]['proposal-1'], PortfolioProposal)
        self.assertEqual(len(finance_main._critiques[session_id]), 1)
        self.assertEqual(len(finance_main._votes[session_id]), 1)
        self.assertEqual(len(finance_main._risk_checks[session_id]), 1)
        self.assertEqual(finance_main._decisions[session_id].decision_id, 'decision-1')

    async def test_require_session_recovers_from_memory_snapshot(self) -> None:
        session_id = 'sess-2'
        snapshot = {
            'session': sample_session_payload(),
            'assumptions': [{'assumption_set_id': 'a1'}],
            'proposals': {'proposal-1': sample_proposal().model_dump()},
            'critiques': [{'critique_id': 'c1'}],
            'votes': [{'ballot_id': 'b1'}],
            'risk_checks': [{'proposal_id': 'proposal-1', 'passed': True}],
            'decision': None,
        }

        async def fake_recall(*, envelope, query, top_k=20):
            return {
                'hits': [
                    {
                        'text': json.dumps(
                            {
                                'artifact_type': 'session_snapshot',
                                'session_id': session_id,
                                'payload': snapshot,
                            }
                        )
                    }
                ]
            }

        finance_main.memoryd.recall = fake_recall  # type: ignore[assignment]
        envelope = sample_session_payload()['envelope']
        recovered = await finance_main.require_session(session_id, envelope)
        self.assertEqual(recovered['context']['mandate_id'], 'mandate-1')
        self.assertIn('proposal-1', finance_main._proposals[session_id])
        self.assertEqual(len(finance_main._votes[session_id]), 1)

    async def test_require_session_falls_back_to_local_cache_when_memory_disabled(self) -> None:
        session_id = 'sess-3'
        finance_main.memoryd.enabled = False
        finance_main._sessions[session_id] = sample_session_payload()
        envelope = sample_session_payload()['envelope']
        recovered = await finance_main.require_session(session_id, envelope)
        self.assertEqual(recovered['context']['mandate_id'], 'mandate-1')

    async def test_persist_artifact_records_memory_receipt(self) -> None:
        session_id = 'sess-4'

        async def fake_write_artifact(**kwargs):
            return {'stored': True, 'memory_id': 'mem-1', 'artifact_type': kwargs['metadata']['artifact_type']}

        finance_main.memoryd.write_artifact = fake_write_artifact  # type: ignore[assignment]
        envelope = sample_session_payload()['envelope']
        await finance_main.persist_artifact(
            artifact_type='session',
            session_id=session_id,
            envelope=envelope,
            payload=sample_session_payload(),
            tags=['session'],
        )
        self.assertEqual(len(finance_main._memory_receipts[session_id]), 1)
        self.assertEqual(finance_main._memory_receipts[session_id][0]['memory_id'], 'mem-1')


if __name__ == '__main__':
    unittest.main()
