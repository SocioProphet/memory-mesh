#!/usr/bin/env python3
"""Validate AgentLearningProposal example."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "agent-learning-proposal.schema.json"
EXAMPLE = ROOT / "examples" / "agent-learning" / "proposal.example.json"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    schema = load_json(SCHEMA)
    example = load_json(EXAMPLE)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(example), key=lambda error: list(error.path))
    if errors:
        print("Agent learning proposal failed validation:")
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "<root>"
            print(f" - {location}: {error.message}")
        return 1

    if example["proposalMode"] != "review_only":
        print("Agent learning proposal example must remain review_only by default.")
        return 1

    if example["review"]["required"] is not True:
        print("Agent learning proposals must require review by default.")
        return 1

    if example["review"]["status"] != "pending":
        print("Example proposal must remain pending until human review.")
        return 1

    if example.get("writeback", {}).get("enabled") is not False:
        print("Example proposal must not enable durable writeback.")
        return 1

    if example.get("writeback", {}).get("performed") is not False:
        print("Example proposal must not perform durable writeback.")
        return 1

    if example.get("redaction", {}).get("rawSensitivePayloadStored") is not False:
        print("Agent learning proposal must not store raw sensitive payloads by default.")
        return 1

    if not example.get("evidenceRefs"):
        print("Agent learning proposal requires evidenceRefs.")
        return 1

    if not example.get("policyDecisionRefs"):
        print("Agent learning proposal requires policyDecisionRefs.")
        return 1

    learning = example["learning"]
    retention = learning.get("retention")
    if retention and not str(retention).endswith("durable"):
        print("Example learning should target durable reviewed memory, not session-only memory.")
        return 1

    destination_path = example["destination"]["path"]
    if destination_path not in {"AGENTS.md", "SOURCEOS.md"} and not destination_path.startswith(".sourceos/"):
        print("Example destination must be a repo-local operating contract or .sourceos path.")
        return 1

    diff = learning["proposedDiff"]
    if diff["format"] != "markdown-section" or not diff["content"].strip():
        print("Example proposal must include a non-empty markdown-section proposedDiff.")
        return 1

    print("Agent learning proposal validates against schema.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
