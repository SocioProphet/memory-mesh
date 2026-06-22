#!/usr/bin/env python3
"""Validate Agent Harness memory-ledger example."""

from __future__ import annotations

from pathlib import Path
import json

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "agent-harness-memory-ledger.schema.json"
EXAMPLE = ROOT / "examples" / "agent-harness" / "memory-ledger.example.json"


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
        print("Agent Harness memory ledger failed validation:")
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "<root>"
            print(f" - {location}: {error.message}")
        return 1

    pointer = example["artifactPointer"]
    if not pointer["uri"].startswith("artifact://sha256/"):
        print("ArtifactPointer uri must use artifact://sha256/<digest>.")
        return 1
    if pointer["sha256"] not in pointer["uri"]:
        print("ArtifactPointer uri must contain the declared sha256 digest.")
        return 1

    snapshot = example["memorySnapshot"]
    if snapshot["sensitivePayloadPosture"] != "disallowed":
        print("Agent Harness baseline memory snapshot must disallow sensitive payload storage.")
        return 1

    recall = example["recallWritebackEvidence"]
    if recall["operation"].startswith("dry-run") and recall["operation"] == "dry-run-writeback":
        print("Dry-run writeback records must not perform actual writeback side effects.")
        return 1
    if not recall["policyDecisionRef"]:
        print("Recall/writeback evidence requires a policy decision reference.")
        return 1

    print("Agent Harness memory ledger validates against schema.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
