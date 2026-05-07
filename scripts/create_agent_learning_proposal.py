#!/usr/bin/env python3
"""Create review-only AgentLearningProposal artifacts.

This script never writes durable memory. It produces a reviewable JSON proposal
that can later be approved, rejected, or superseded by a human/governance flow.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_proposal(args: argparse.Namespace) -> dict:
    proposal_id = args.proposal_id or f"urn:srcos:memory-proposal:{args.session_ref.split(':')[-1]}"
    evidence_refs = args.evidence_ref or []
    policy_refs = args.policy_decision_ref or []
    return {
        "apiVersion": "memory.mesh.agent-learning/v1",
        "kind": "AgentLearningProposal",
        "proposalId": proposal_id,
        "createdAt": args.created_at or utc_now(),
        "sourceSession": {
            "sessionRef": args.session_ref,
            "taskRef": args.task_ref,
            "repo": args.repo,
            "agentRef": args.agent_ref,
            "workcellArtifactRef": args.workcell_artifact_ref,
            "invocationArtifactRef": args.invocation_artifact_ref,
            "stopGateArtifactRef": args.stop_gate_artifact_ref,
        },
        "destination": {
            "scope": args.scope,
            "targetRef": args.target_ref,
            "path": args.path,
            "memoryNamespace": args.memory_namespace,
        },
        "proposalMode": "review_only",
        "learningType": args.learning_type,
        "learning": {
            "title": args.title,
            "summary": args.summary,
            "rationale": args.rationale,
            "proposedDiff": {
                "format": args.diff_format,
                "content": args.diff_content,
            },
            "conflictsWith": args.conflicts_with or [],
            "confidence": args.confidence,
            "retention": args.retention,
        },
        "review": {
            "required": True,
            "status": "pending",
            "reviewerRefs": args.reviewer_ref or ["human:repo-maintainer"],
            "approvalRef": None,
            "reviewNotes": args.review_notes,
        },
        "evidenceRefs": evidence_refs,
        "policyDecisionRefs": policy_refs,
        "redaction": {
            "rawSensitivePayloadStored": False,
            "redactionSummary": args.redaction_summary,
        },
        "writeback": {
            "enabled": False,
            "performed": False,
            "writebackRef": None,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a review-only Memory Mesh AgentLearningProposal artifact.")
    parser.add_argument("--proposal-id")
    parser.add_argument("--created-at")
    parser.add_argument("--session-ref", required=True)
    parser.add_argument("--task-ref", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--agent-ref", required=True)
    parser.add_argument("--workcell-artifact-ref")
    parser.add_argument("--invocation-artifact-ref")
    parser.add_argument("--stop-gate-artifact-ref")
    parser.add_argument("--scope", choices=["repo", "project", "user", "organization", "enterprise"], default="repo")
    parser.add_argument("--target-ref", required=True)
    parser.add_argument("--path", required=True)
    parser.add_argument("--memory-namespace")
    parser.add_argument("--learning-type", choices=["operational-fact", "playbook-update", "policy-note", "tooling-note", "risk-note", "architecture-note"], default="playbook-update")
    parser.add_argument("--title", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--rationale", required=True)
    parser.add_argument("--diff-format", choices=["unified-diff", "markdown-section", "json-patch", "none"], default="markdown-section")
    parser.add_argument("--diff-content", required=True)
    parser.add_argument("--conflicts-with", action="append")
    parser.add_argument("--confidence", type=float, default=0.75)
    parser.add_argument("--retention", choices=["session-only", "repo-durable", "project-durable", "org-durable", "enterprise-durable"], default="repo-durable")
    parser.add_argument("--reviewer-ref", action="append")
    parser.add_argument("--review-notes")
    parser.add_argument("--evidence-ref", action="append", required=True)
    parser.add_argument("--policy-decision-ref", action="append", required=True)
    parser.add_argument("--redaction-summary", default="No raw sensitive payload stored in the proposal.")
    parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 0 <= args.confidence <= 1:
        raise SystemExit("--confidence must be between 0 and 1")
    proposal = build_proposal(args)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(proposal, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(proposal, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
