#!/usr/bin/env python3
"""Validate Lampstand adapter-record promotion packet example."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "lampstand-adapter-record-promotion-packet.schema.json"
EXAMPLE = ROOT / "examples" / "lampstand" / "adapter-record-promotion-packet.example.json"


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
        print("Lampstand adapter-record promotion packet failed validation:")
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "<root>"
            print(f" - {location}: {error.message}")
        return 1

    if example["sourceAuthority"] != "lampstand.adapter_records":
        print("Promotion packet must preserve Lampstand adapter_records as source authority.")
        return 1

    if example["promotionMode"] != "review_only":
        print("Example promotion packet must remain review_only by default.")
        return 1

    record_ids = {record["recordId"] for record in example["records"]}
    for candidate in example["promotionCandidates"]:
        if candidate["sourceRecordId"] not in record_ids:
            print(f"Promotion candidate {candidate['candidateId']} references missing sourceRecordId {candidate['sourceRecordId']}")
            return 1
        if candidate["recommendedAction"] != "review":
            print(f"Promotion candidate {candidate['candidateId']} must require review by default.")
            return 1

    for record in example["records"]:
        if record["classification"] != "local_only":
            print(f"Example record {record['recordId']} must remain local_only.")
            return 1
        if record["policyDecision"]["decision"] == "deny":
            print(f"Denied record {record['recordId']} cannot be included in promotion packet example.")
            return 1

    if not example.get("policyDecisionRefs"):
        print("Promotion packet requires policyDecisionRefs.")
        return 1
    if not example.get("evidenceRefs"):
        print("Promotion packet requires evidenceRefs.")
        return 1

    print("Lampstand adapter-record promotion packet validates against schema.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
