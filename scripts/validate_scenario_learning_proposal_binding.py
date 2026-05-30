#!/usr/bin/env python3
"""Validate ScenarioLearningProposalBinding examples."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "scenario-learning-proposal-binding.schema.json"
DEFAULT_EXAMPLE = ROOT / "examples" / "scenario-learning" / "scenario-learning-proposal-binding.example.json"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_binding(example: dict, *, source_label: str) -> int:
    gate = example["reviewOnlyGate"]
    if gate["proposalMode"] != "review_only":
        print(f"{source_label}: Scenario learning binding must remain review_only.")
        return 1

    if gate["reviewRequired"] is not True or gate["reviewStatus"] != "pending":
        print(f"{source_label}: Scenario learning binding must remain pending human review.")
        return 1

    writeback = example["writeback"]
    if writeback["enabled"] is not False or writeback["performed"] is not False:
        print(f"{source_label}: Scenario learning binding must not enable or perform durable writeback.")
        return 1

    if writeback["writebackRef"] is not None:
        print(f"{source_label}: Scenario learning binding must not carry a writebackRef before approval.")
        return 1

    if example["redaction"]["rawSensitivePayloadStored"] is not False:
        print(f"{source_label}: Scenario learning binding must not store raw sensitive payloads.")
        return 1

    scenario = example["sourceScenario"]
    if scenario["claimPromotionState"] not in {"raw", "hypothesis", "triaged", "blocked"}:
        print(f"{source_label}: Scenario claimPromotionState must not be promoted beyond triaged/blocked.")
        return 1

    if not scenario["runtimeDecisionReceiptRefs"]:
        print(f"{source_label}: Scenario learning binding requires runtime decision receipt references.")
        return 1

    memory_effect = example["memoryEffect"]
    if memory_effect["proposalRequired"] is not True:
        print(f"{source_label}: Scenario memory effect must require proposal routing.")
        return 1

    if memory_effect["reviewState"] not in {"pending_review", "blocked"}:
        print(f"{source_label}: Scenario memory effect must remain pending_review or blocked.")
        return 1

    if not example.get("evidenceRefs"):
        print(f"{source_label}: Scenario learning binding requires evidenceRefs.")
        return 1

    if not example.get("policyDecisionRefs"):
        print(f"{source_label}: Scenario learning binding requires policyDecisionRefs.")
        return 1

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate ScenarioLearningProposalBinding artifact.")
    parser.add_argument("--binding", default=str(DEFAULT_EXAMPLE), help="Scenario learning binding JSON file to validate")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    binding_path = Path(args.binding).resolve()
    schema = load_json(SCHEMA)
    example = load_json(binding_path)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(example), key=lambda error: list(error.path))
    if errors:
        print("Scenario learning proposal binding failed validation:")
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "<root>"
            print(f" - {location}: {error.message}")
        return 1

    result = validate_binding(example, source_label=str(binding_path))
    if result != 0:
        return result

    print(f"Scenario learning proposal binding validates against schema: {binding_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
