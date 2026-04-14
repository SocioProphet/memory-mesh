from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from services.memoryd.app.models import ScopeEnvelope


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SessionContext(BaseModel):
    mandate_id: str
    workload_id: str
    valuation_date: date
    data_cutoff: datetime
    benchmark_id: str
    universe_id: str
    ips_resource_keys: list[str] = Field(default_factory=list)


class AssumptionSet(BaseModel):
    assumption_set_id: str
    role: str
    asset_class: str | None = None
    narrative: str
    values: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)


class PortfolioWeight(BaseModel):
    asset_id: str
    weight: float


class ProposalMetrics(BaseModel):
    expected_return: float
    expected_volatility: float
    expected_sharpe: float
    turnover: float | None = None
    tracking_error: float | None = None


class PortfolioProposal(BaseModel):
    proposal_id: str
    method_id: str
    weights: list[PortfolioWeight] = Field(default_factory=list)
    metrics: ProposalMetrics
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)


class Critique(BaseModel):
    critique_id: str
    proposal_id: str
    reviewer_role: str
    disposition: str
    findings: list[dict[str, Any]] = Field(default_factory=list)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)


class VoteBallot(BaseModel):
    ballot_id: str
    voter_role: str
    ballot_type: str
    rankings: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)
    rationale: str
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)


class DecisionPack(BaseModel):
    decision_id: str
    selected_proposal_id: str
    rationale: str
    approval_mode: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)


class SessionStartRequest(BaseModel):
    envelope: ScopeEnvelope
    context: SessionContext
    notes: str | None = None


class SessionStartResponse(BaseModel):
    session_id: str
    run_id: str
    event_id: str


class AssumptionsSubmitRequest(BaseModel):
    envelope: ScopeEnvelope
    session_id: str
    assumption_set: AssumptionSet


class AcceptedResponse(BaseModel):
    accepted: bool
    event_id: str


class ProposalSubmitRequest(BaseModel):
    envelope: ScopeEnvelope
    session_id: str
    proposal: PortfolioProposal


class ProposalCritiqueRequest(BaseModel):
    envelope: ScopeEnvelope
    session_id: str
    critique: Critique


class RiskCheckRequest(BaseModel):
    envelope: ScopeEnvelope
    session_id: str
    proposal_id: str
    scenario_set_id: str | None = None


class RiskCheckResponse(BaseModel):
    passed: bool
    findings: list[dict[str, Any]] = Field(default_factory=list)
    event_id: str


class VoteRecordRequest(BaseModel):
    envelope: ScopeEnvelope
    session_id: str
    ballot: VoteBallot


class VoteRecordResponse(BaseModel):
    accepted: bool
    tally_state: dict[str, Any] = Field(default_factory=dict)
    event_id: str


class DecisionSelectRequest(BaseModel):
    envelope: ScopeEnvelope
    session_id: str
    selected_proposal_id: str
    rationale: str


class DecisionSelectResponse(BaseModel):
    decision_pack: DecisionPack
    event_id: str


class EventEnvelope(BaseModel):
    event_id: str = Field(default_factory=lambda: uuid4().hex)
    event_type: str
    created_at: datetime = Field(default_factory=utcnow)
    payload: dict[str, Any] = Field(default_factory=dict)
