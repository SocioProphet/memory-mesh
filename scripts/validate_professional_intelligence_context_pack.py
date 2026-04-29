#!/usr/bin/env python3
"""Validate Professional Intelligence context-pack example."""

from __future__ import annotations

from pathlib import Path
import json

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "professional-intelligence-context-pack.schema.json"
EXAMPLE = ROOT / "examples" / "professional-intelligence" / "context-pack.example.json"


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
        print("Professional Intelligence context pack failed validation:")
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "<root>"
            print(f" - {location}: {error.message}")
        return 1

    recall_policy = example["recallPolicy"]
    if recall_policy["scope"] != "workroom-scoped":
        print("Professional Intelligence context pack must be workroom-scoped.")
        return 1
    if recall_policy["trainingUse"] != "disabled":
        print("Professional Intelligence context pack must disable training use by default.")
        return 1
    if not example["policyDecisionRefs"] or not example["obligationRefs"]:
        print("Professional Intelligence context pack requires policy and obligation references.")
        return 1
    if not example["allowedAgentRefs"]:
        print("Professional Intelligence context pack requires at least one allowed agent reference.")
        return 1

    print("Professional Intelligence context pack validates against schema.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
