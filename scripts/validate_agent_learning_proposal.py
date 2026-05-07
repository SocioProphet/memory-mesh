#!/usr/bin/env python3
"""Validate AgentLearningProposal examples or generated proposal files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "agent-learning-proposal.schema.json"
DEFAULT_EXAMPLE = ROOT / "examples" / "agent-learning" / "proposal.example.json"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_proposal(example: dict, *, source_label: str) -> int:
    if example["proposalMode"] != "review_only":
        print(f"{source_label}: Agent learning proposal must remain review_only by default.")
        return 1

    if example["review"]["required"] is not True:
        print(f"{source_label}: Agent learning proposals must require review by default.")
        return 1

    if example["review"]["status"] != "pending":
        print(f"{source_label}: Proposal must remain pending until human review.")
        return 1

    if example.get("writeback", {}).get("enabled") is not False:
        print(f"{source_label}: Proposal must not enable durable writeback.")
        return 1

    if example.get("writeback", {}).get("performed") is not False:
        print(f"{source_label}: Proposal must not perform durable writeback.")
        return 1

    if example.get("redaction", {}).get("rawSensitivePayloadStored") is not False:
        print(f"{source_label}: Proposal must not store raw sensitive payloads by default.")
        return 1

    if not example.get("evidenceRefs"):
        print(f"{source_label}: Proposal requires evidenceRefs.")
        return 1

    if not example.get("policyDecisionRefs"):
        print(f"{source_label}: Proposal requires policyDecisionRefs.")
        return 1

    learning = example["learning"]
    retention = learning.get("retention")
    if retention and not str(retention).endswith("durable"):
        print(f"{source_label}: Example learning should target durable reviewed memory, not session-only memory.")
        return 1

    destination_path = example["destination"]["path"]
    if destination_path not in {"AGENTS.md", "SOURCEOS.md"} and not destination_path.startswith(".sourceos/"):
        print(f"{source_label}: Destination must be a repo-local operating contract or .sourceos path.")
        return 1

    diff = learning["proposedDiff"]
    if diff["format"] != "markdown-section" or not diff["content"].strip():
        print(f"{source_label}: Proposal must include a non-empty markdown-section proposedDiff.")
        return 1

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate AgentLearningProposal artifact.")
    parser.add_argument("--proposal", default=str(DEFAULT_EXAMPLE), help="Proposal JSON file to validate")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    proposal_path = Path(args.proposal).resolve()
    schema = load_json(SCHEMA)
    example = load_json(proposal_path)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(example), key=lambda error: list(error.path))
    if errors:
        print("Agent learning proposal failed validation:")
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "<root>"
            print(f" - {location}: {error.message}")
        return 1

    result = validate_proposal(example, source_label=str(proposal_path))
    if result != 0:
        return result

    print(f"Agent learning proposal validates against schema: {proposal_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
