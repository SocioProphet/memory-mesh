from __future__ import annotations

import os
from collections import defaultdict
from typing import Any

from fastapi import FastAPI, Header, HTTPException

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

app = FastAPI(title='finance_saa', version='0.1.0')

_sessions: dict[str, dict[str, Any]] = {}
_assumptions: dict[str, list[dict[str, Any]]] = defaultdict(list)
_proposals: dict[str, dict[str, PortfolioProposal]] = defaultdict(dict)
_critiques: dict[str, list[dict[str, Any]]] = defaultdict(list)
_votes: dict[str, list[dict[str, Any]]] = defaultdict(list)
_decisions: dict[str, DecisionPack] = {}
_events: list[EventEnvelope] = []


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


def require_session(session_id: str) -> dict[str, Any]:
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail='session not found')
    return session


@app.get('/')
async def root() -> dict[str, Any]:
    return {
        'service': 'finance_saa',
        'version': app.version,
        'session_count': len(_sessions),
        'decision_count': len(_decisions),
    }


@app.get('/healthz')
async def healthz() -> dict[str, Any]:
    return {
        'ok': True,
        'session_count': len(_sessions),
        'proposal_count': sum(len(items) for items in _proposals.values()),
        'event_count': len(_events),
    }


@app.post('/v1/session/start', response_model=SessionStartResponse)
async def session_start(request: SessionStartRequest, x_api_key: str | None = Header(default=None)) -> SessionStartResponse:
    await require_api_key(x_api_key)
    session_id = f"sess_{request.envelope.run_id}_{len(_sessions) + 1}"
    _sessions[session_id] = {
        'envelope': request.envelope.model_dump(),
        'context': request.context.model_dump(),
        'notes': request.notes,
    }
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
    return SessionStartResponse(session_id=session_id, run_id=request.envelope.run_id, event_id=event.event_id)


@app.post('/v1/assumptions/submit', response_model=AcceptedResponse)
async def assumptions_submit(request: AssumptionsSubmitRequest, x_api_key: str | None = Header(default=None)) -> AcceptedResponse:
    await require_api_key(x_api_key)
    require_session(request.session_id)
    _assumptions[request.session_id].append(request.assumption_set.model_dump())
    event = emit(
        'finance.assumptions.submitted',
        {
            'session_id': request.session_id,
            'assumption_set_id': request.assumption_set.assumption_set_id,
            'role': request.assumption_set.role,
        },
    )
    return AcceptedResponse(accepted=True, event_id=event.event_id)


@app.post('/v1/proposals/submit', response_model=AcceptedResponse)
async def proposal_submit(request: ProposalSubmitRequest, x_api_key: str | None = Header(default=None)) -> AcceptedResponse:
    await require_api_key(x_api_key)
    require_session(request.session_id)
    _proposals[request.session_id][request.proposal.proposal_id] = request.proposal
    event = emit(
        'finance.proposal.submitted',
        {
            'session_id': request.session_id,
            'proposal_id': request.proposal.proposal_id,
            'method_id': request.proposal.method_id,
        },
    )
    return AcceptedResponse(accepted=True, event_id=event.event_id)


@app.post('/v1/proposals/critique', response_model=AcceptedResponse)
async def proposal_critique(request: ProposalCritiqueRequest, x_api_key: str | None = Header(default=None)) -> AcceptedResponse:
    await require_api_key(x_api_key)
    require_session(request.session_id)
    if request.critique.proposal_id not in _proposals[request.session_id]:
        raise HTTPException(status_code=404, detail='proposal not found')
    _critiques[request.session_id].append(request.critique.model_dump())
    event = emit(
        'finance.critique.submitted',
        {
            'session_id': request.session_id,
            'critique_id': request.critique.critique_id,
            'proposal_id': request.critique.proposal_id,
            'reviewer_role': request.critique.reviewer_role,
        },
    )
    return AcceptedResponse(accepted=True, event_id=event.event_id)


@app.post('/v1/risk/check', response_model=RiskCheckResponse)
async def risk_check(request: RiskCheckRequest, x_api_key: str | None = Header(default=None)) -> RiskCheckResponse:
    await require_api_key(x_api_key)
    require_session(request.session_id)
    proposal = _proposals[request.session_id].get(request.proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail='proposal not found')
    findings: list[dict[str, Any]] = []
    total_weight = sum(item.weight for item in proposal.weights)
    if abs(total_weight - 1.0) > 0.05:
        findings.append({'severity': 'warn', 'code': 'weights.not_normalized', 'message': f'weights sum to {total_weight:.4f}'})
    passed = not any(item['severity'] == 'block' for item in findings)
    event = emit(
        'finance.risk.checked',
        {
            'session_id': request.session_id,
            'proposal_id': request.proposal_id,
            'passed': passed,
            'finding_count': len(findings),
        },
    )
    return RiskCheckResponse(passed=passed, findings=findings, event_id=event.event_id)


@app.post('/v1/votes/record', response_model=VoteRecordResponse)
async def vote_record(request: VoteRecordRequest, x_api_key: str | None = Header(default=None)) -> VoteRecordResponse:
    await require_api_key(x_api_key)
    require_session(request.session_id)
    _votes[request.session_id].append(request.ballot.model_dump())
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
    return VoteRecordResponse(accepted=True, tally_state=tally_state, event_id=event.event_id)


@app.post('/v1/decisions/select', response_model=DecisionSelectResponse)
async def decision_select(request: DecisionSelectRequest, x_api_key: str | None = Header(default=None)) -> DecisionSelectResponse:
    await require_api_key(x_api_key)
    session = require_session(request.session_id)
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
    return DecisionSelectResponse(decision_pack=decision, event_id=event.event_id)
