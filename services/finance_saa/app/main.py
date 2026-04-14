from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Any

from fastapi import FastAPI, Header, HTTPException

from .memory_mesh_client import MemoryMeshClient
from .models import (
    AcceptedResponse,
    AssumptionsSubmitRequest,
    DecisionPack,
    DecisionSelectRequest,
    DecisionSelectResponse,
    EventEnvelope,
    PortfolioProposal,
    ProposalCritiqueRequest,
    ProposalSubmitRequest,
    RiskCheckRequest,
    RiskCheckResponse,
    SessionStartRequest,
    SessionStartResponse,
    VoteRecordRequest,
    VoteRecordResponse,
)


REQUIRE_API_KEY = os.getenv('FINANCE_SAA_REQUIRE_API_KEY', 'false').lower() in {'1', 'true', 'yes'}
EXPECTED_API_KEY = os.getenv('FINANCE_SAA_API_KEY', '')
MEMORYD_SOURCE_OF_TRUTH = os.getenv('FINANCE_SAA_MEMORYD_SOURCE_OF_TRUTH', 'true').lower() in {'1', 'true', 'yes'}

app = FastAPI(title='finance_saa', version='0.3.0')

memoryd = MemoryMeshClient(timeout_seconds=float(os.getenv('FINANCE_SAA_MEMORYD_TIMEOUT_SECONDS', '10')))

_sessions: dict[str, dict[str, Any]] = {}
_assumptions: dict[str, list[dict[str, Any]]] = defaultdict(list)
_proposals: dict[str, dict[str, PortfolioProposal]] = defaultdict(dict)
_critiques: dict[str, list[dict[str, Any]]] = defaultdict(list)
_votes: dict[str, list[dict[str, Any]]] = defaultdict(list)
_risk_checks: dict[str, list[dict[str, Any]]] = defaultdict(list)
_decisions: dict[str, DecisionPack] = {}
_events: list[EventEnvelope] = []
_memory_receipts: dict[str, list[dict[str, Any]]] = defaultdict(list)


async def require_api_key(x_api_key: str | None) -> None:
    if not REQUIRE_API_KEY:
        return
    if not EXPECTED_API_KEY:
        raise HTTPException(status_code=500, detail='finance_saa api key enforcement enabled but FINANCE_SAA_API_KEY is empty')
    if x_api_key != EXPECTED_API_KEY:
        raise HTTPException(status_code=401, detail='invalid api key')


def emit(event_type: str, payload: dict[str, Any]) -> EventEnvelope:
    event = EventEnvelope(event_type=event_type, payload=payload)
    _events.append(event)
    return event


def serialize_proposals(session_id: str) -> dict[str, Any]:
    return {proposal_id: proposal.model_dump() for proposal_id, proposal in _proposals[session_id].items()}


def build_session_snapshot(session_id: str) -> dict[str, Any]:
    decision = _decisions.get(session_id)
    return {
        'session': _sessions.get(session_id),
        'assumptions': list(_assumptions.get(session_id, [])),
        'proposals': serialize_proposals(session_id),
        'critiques': list(_critiques.get(session_id, [])),
        'votes': list(_votes.get(session_id, [])),
        'risk_checks': list(_risk_checks.get(session_id, [])),
        'decision': decision.model_dump() if decision is not None else None,
    }


def hydrate_snapshot(session_id: str, snapshot: dict[str, Any]) -> dict[str, Any] | None:
    session_payload = snapshot.get('session')
    if not isinstance(session_payload, dict):
        return None
    _sessions[session_id] = session_payload
    _assumptions[session_id] = [item for item in list(snapshot.get('assumptions') or []) if isinstance(item, dict)]

    proposals_payload = snapshot.get('proposals') or {}
    loaded_proposals: dict[str, PortfolioProposal] = {}
    if isinstance(proposals_payload, dict):
        for proposal_id, payload in proposals_payload.items():
            if isinstance(payload, dict):
                loaded_proposals[str(proposal_id)] = PortfolioProposal.model_validate(payload)
    _proposals[session_id] = loaded_proposals

    _critiques[session_id] = [item for item in list(snapshot.get('critiques') or []) if isinstance(item, dict)]
    _votes[session_id] = [item for item in list(snapshot.get('votes') or []) if isinstance(item, dict)]
    _risk_checks[session_id] = [item for item in list(snapshot.get('risk_checks') or []) if isinstance(item, dict)]

    decision_payload = snapshot.get('decision')
    if isinstance(decision_payload, dict):
        _decisions[session_id] = DecisionPack.model_validate(decision_payload)
    elif session_id in _decisions:
        del _decisions[session_id]
    return session_payload


async def persist_artifact(*, artifact_type: str, session_id: str, envelope: dict[str, Any], payload: dict[str, Any], tags: list[str]) -> None:
    if not memoryd.enabled:
        return
    metadata = {
        'artifact_type': artifact_type,
        'session_id': session_id,
        'workload_id': envelope['workload_id'],
        'run_id': envelope['run_id'],
        'source_service': 'finance_saa',
    }
    receipt = await memoryd.write_artifact(
        envelope=envelope,
        content={'artifact_type': artifact_type, 'session_id': session_id, 'payload': payload},
        memory_class='decision' if artifact_type == 'decision' else 'summary',
        tags=['finance_saa', artifact_type, *tags],
        metadata=metadata,
    )
    _memory_receipts[session_id].append(receipt)


async def persist_session_snapshot(session_id: str, envelope: dict[str, Any]) -> None:
    if not memoryd.enabled:
        return
    snapshot = build_session_snapshot(session_id)
    await persist_artifact(
        artifact_type='session_snapshot',
        session_id=session_id,
        envelope=envelope,
        payload=snapshot,
        tags=['session_snapshot', session_id],
    )


async def recover_snapshot_from_memory(envelope: dict[str, Any], session_id: str) -> dict[str, Any] | None:
    if not memoryd.enabled:
        return None
    recalled = await memoryd.recall(envelope=envelope, query=f'{session_id} session_snapshot', top_k=20)
    hits = list(recalled.get('hits') or [])
    for hit in hits:
        text = hit.get('text')
        if not isinstance(text, str):
            continue
        try:
            payload = json.loads(text)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get('artifact_type') == 'session_snapshot' and payload.get('session_id') == session_id:
            snapshot_payload = payload.get('payload') or {}
            if isinstance(snapshot_payload, dict):
                hydrate_snapshot(session_id, snapshot_payload)
                return snapshot_payload
    return None


async def require_session(session_id: str, envelope: dict[str, Any]) -> dict[str, Any]:
    if MEMORYD_SOURCE_OF_TRUTH and memoryd.enabled:
        snapshot = await recover_snapshot_from_memory(envelope, session_id)
        if snapshot is not None:
            session_payload = snapshot.get('session')
            if isinstance(session_payload, dict):
                return session_payload
    session = _sessions.get(session_id)
    if session is not None:
        return session
    raise HTTPException(status_code=404, detail='session not found')


@app.get('/')
async def root() -> dict[str, Any]:
    return {
        'service': 'finance_saa',
        'version': app.version,
        'session_count': len(_sessions),
        'decision_count': len(_decisions),
        'memoryd_enabled': memoryd.enabled,
        'memoryd_source_of_truth': MEMORYD_SOURCE_OF_TRUTH,
    }


@app.get('/healthz')
async def healthz() -> dict[str, Any]:
    return {
        'ok': True,
        'session_count': len(_sessions),
        'proposal_count': sum(len(items) for items in _proposals.values()),
        'event_count': len(_events),
        'memoryd_enabled': memoryd.enabled,
        'memoryd_source_of_truth': MEMORYD_SOURCE_OF_TRUTH,
    }


@app.post('/v1/session/start', response_model=SessionStartResponse)
async def session_start(request: SessionStartRequest, x_api_key: str | None = Header(default=None)) -> SessionStartResponse:
    await require_api_key(x_api_key)
    envelope = request.envelope.model_dump()
    session_id = f"sess_{request.envelope.run_id}_{len(_sessions) + 1}"
    session_payload = {
        'envelope': envelope,
        'context': request.context.model_dump(),
        'notes': request.notes,
    }
    _sessions[session_id] = session_payload
    event = emit(
        'finance.session.started',
        {
            'session_id': session_id,
            'run_id': request.envelope.run_id,
            'workload_id': request.envelope.workload_id,
            'mandate_id': request.context.mandate_id,
            'valuation_date': str(request.context.valuation_date),
            'data_cutoff': str(request.context.data_cutoff),
        },
    )
    await persist_artifact(
        artifact_type='session',
        session_id=session_id,
        envelope=envelope,
        payload=session_payload,
        tags=['session', request.context.mandate_id],
    )
    await persist_session_snapshot(session_id, envelope)
    return SessionStartResponse(session_id=session_id, run_id=request.envelope.run_id, event_id=event.event_id)


@app.post('/v1/assumptions/submit', response_model=AcceptedResponse)
async def assumptions_submit(request: AssumptionsSubmitRequest, x_api_key: str | None = Header(default=None)) -> AcceptedResponse:
    await require_api_key(x_api_key)
    envelope = request.envelope.model_dump()
    await require_session(request.session_id, envelope)
    assumption_payload = request.assumption_set.model_dump()
    _assumptions[request.session_id].append(assumption_payload)
    event = emit(
        'finance.assumptions.submitted',
        {
            'session_id': request.session_id,
            'assumption_set_id': request.assumption_set.assumption_set_id,
            'role': request.assumption_set.role,
        },
    )
    await persist_artifact(
        artifact_type='assumption',
        session_id=request.session_id,
        envelope=envelope,
        payload=assumption_payload,
        tags=['assumption', request.assumption_set.role],
    )
    await persist_session_snapshot(request.session_id, envelope)
    return AcceptedResponse(accepted=True, event_id=event.event_id)


@app.post('/v1/proposals/submit', response_model=AcceptedResponse)
async def proposal_submit(request: ProposalSubmitRequest, x_api_key: str | None = Header(default=None)) -> AcceptedResponse:
    await require_api_key(x_api_key)
    envelope = request.envelope.model_dump()
    await require_session(request.session_id, envelope)
    _proposals[request.session_id][request.proposal.proposal_id] = request.proposal
    proposal_payload = request.proposal.model_dump()
    event = emit(
        'finance.proposal.submitted',
        {
            'session_id': request.session_id,
            'proposal_id': request.proposal.proposal_id,
            'method_id': request.proposal.method_id,
        },
    )
    await persist_artifact(
        artifact_type='proposal',
        session_id=request.session_id,
        envelope=envelope,
        payload=proposal_payload,
        tags=['proposal', request.proposal.method_id],
    )
    await persist_session_snapshot(request.session_id, envelope)
    return AcceptedResponse(accepted=True, event_id=event.event_id)


@app.post('/v1/proposals/critique', response_model=AcceptedResponse)
async def proposal_critique(request: ProposalCritiqueRequest, x_api_key: str | None = Header(default=None)) -> AcceptedResponse:
    await require_api_key(x_api_key)
    envelope = request.envelope.model_dump()
    await require_session(request.session_id, envelope)
    if request.critique.proposal_id not in _proposals[request.session_id]:
        raise HTTPException(status_code=404, detail='proposal not found')
    critique_payload = request.critique.model_dump()
    _critiques[request.session_id].append(critique_payload)
    event = emit(
        'finance.critique.submitted',
        {
            'session_id': request.session_id,
            'critique_id': request.critique.critique_id,
            'proposal_id': request.critique.proposal_id,
            'reviewer_role': request.critique.reviewer_role,
        },
    )
    await persist_artifact(
        artifact_type='critique',
        session_id=request.session_id,
        envelope=envelope,
        payload=critique_payload,
        tags=['critique', request.critique.reviewer_role],
    )
    await persist_session_snapshot(request.session_id, envelope)
    return AcceptedResponse(accepted=True, event_id=event.event_id)


@app.post('/v1/risk/check', response_model=RiskCheckResponse)
async def risk_check(request: RiskCheckRequest, x_api_key: str | None = Header(default=None)) -> RiskCheckResponse:
    await require_api_key(x_api_key)
    envelope = request.envelope.model_dump()
    await require_session(request.session_id, envelope)
    proposal = _proposals[request.session_id].get(request.proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail='proposal not found')
    findings: list[dict[str, Any]] = []
    total_weight = sum(item.weight for item in proposal.weights)
    if abs(total_weight - 1.0) > 0.05:
        findings.append({'severity': 'warn', 'code': 'weights.not_normalized', 'message': f'weights sum to {total_weight:.4f}'})
    passed = not any(item['severity'] == 'block' for item in findings)
    risk_payload = {
        'proposal_id': request.proposal_id,
        'passed': passed,
        'findings': findings,
        'scenario_set_id': request.scenario_set_id,
    }
    _risk_checks[request.session_id].append(risk_payload)
    event = emit(
        'finance.risk.checked',
        {
            'session_id': request.session_id,
            'proposal_id': request.proposal_id,
            'passed': passed,
            'finding_count': len(findings),
        },
    )
    await persist_artifact(
        artifact_type='risk_check',
        session_id=request.session_id,
        envelope=envelope,
        payload=risk_payload,
        tags=['risk_check', 'passed' if passed else 'failed'],
    )
    await persist_session_snapshot(request.session_id, envelope)
    return RiskCheckResponse(passed=passed, findings=findings, event_id=event.event_id)


@app.post('/v1/votes/record', response_model=VoteRecordResponse)
async def vote_record(request: VoteRecordRequest, x_api_key: str | None = Header(default=None)) -> VoteRecordResponse:
    await require_api_key(x_api_key)
    envelope = request.envelope.model_dump()
    await require_session(request.session_id, envelope)
    ballot_payload = request.ballot.model_dump()
    _votes[request.session_id].append(ballot_payload)
    tally_state = {
        'ballot_count': len(_votes[request.session_id]),
        'proposal_count': len(_proposals[request.session_id]),
    }
    event = emit(
        'finance.vote.recorded',
        {
            'session_id': request.session_id,
            'ballot_id': request.ballot.ballot_id,
            'voter_role': request.ballot.voter_role,
            'ballot_type': request.ballot.ballot_type,
        },
    )
    await persist_artifact(
        artifact_type='vote',
        session_id=request.session_id,
        envelope=envelope,
        payload={'ballot': ballot_payload, 'tally_state': tally_state},
        tags=['vote', request.ballot.voter_role],
    )
    await persist_session_snapshot(request.session_id, envelope)
    return VoteRecordResponse(accepted=True, tally_state=tally_state, event_id=event.event_id)


@app.post('/v1/decisions/select', response_model=DecisionSelectResponse)
async def decision_select(request: DecisionSelectRequest, x_api_key: str | None = Header(default=None)) -> DecisionSelectResponse:
    await require_api_key(x_api_key)
    envelope = request.envelope.model_dump()
    session = await require_session(request.session_id, envelope)
    proposal = _proposals[request.session_id].get(request.selected_proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail='proposal not found')
    if not _critiques[request.session_id]:
        raise HTTPException(status_code=409, detail='at least one critique is required before decision selection')
    if not _votes[request.session_id]:
        raise HTTPException(status_code=409, detail='at least one vote is required before decision selection')
    decision = DecisionPack(
        decision_id=f"decision_{request.session_id}",
        selected_proposal_id=request.selected_proposal_id,
        rationale=request.rationale,
        approval_mode='bootstrap-majority',
        metrics=proposal.metrics.model_dump(),
        evidence_refs=[
            {'kind': 'session', 'session_id': request.session_id},
            {'kind': 'mandate', 'mandate_id': session['context']['mandate_id']},
        ],
    )
    _decisions[request.session_id] = decision
    event = emit(
        'finance.decision.selected',
        {
            'session_id': request.session_id,
            'decision_id': decision.decision_id,
            'selected_proposal_id': request.selected_proposal_id,
        },
    )
    await persist_artifact(
        artifact_type='decision',
        session_id=request.session_id,
        envelope=envelope,
        payload=decision.model_dump(),
        tags=['decision', session['context']['mandate_id']],
    )
    await persist_session_snapshot(request.session_id, envelope)
    return DecisionSelectResponse(decision_pack=decision, event_id=event.event_id)
