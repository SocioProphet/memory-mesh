#!/usr/bin/env python3
"""Validate WallGuard memory compartment gate examples."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "wallguard-memory-compartment-gate.schema.json"
EXAMPLE_DIR = ROOT / "examples" / "wallguard-memory-compartment-gate"
RESTRICTED_CLASSES = {"client_scoped", "matter_scoped", "wall_restricted", "contaminated"}
GLOBAL_CLASSES = {"global", "firm_approved"}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_schema(instance: dict, schema: dict, *, source_label: str) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
    if errors:
        lines = [f"{source_label} failed schema validation:"]
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "<root>"
            lines.append(f" - {location}: {error.message}")
        raise ValueError("\n".join(lines))


def semantic_diagnostics(record: dict) -> list[str]:
    diagnostics: list[str] = []
    source = record["sourceCompartment"]
    target = record["targetCompartment"]
    operation = record["operation"]
    admitted = record["admitted"]
    decision = record["admissionDecision"]
    outcome = record["wallDecisionOutcome"]
    reason = record["reasonCode"]
    writeback = record["writeback"]
    wall_ref = record["wallRef"]

    if admitted and decision != "admit":
        diagnostics.append("admitted=true requires admissionDecision=admit")
    if decision == "admit" and not admitted:
        diagnostics.append("admissionDecision=admit requires admitted=true")
    if admitted and outcome != "allow":
        diagnostics.append("admitted operations require WallGuard allow outcome")

    if wall_ref == "unknown" and admitted:
        diagnostics.append("missing active wall context cannot be admitted")
    if wall_ref == "unknown" and decision != "fail-closed":
        diagnostics.append("missing active wall context must fail closed")

    if admitted and source["wallRef"] not in {wall_ref, "none"}:
        diagnostics.append("admitted source compartment wallRef must match active wallRef or be none")
    if admitted and target["wallRef"] not in {wall_ref, "none"}:
        diagnostics.append("admitted target compartment wallRef must match active wallRef or be none")

    source_class = source["compartmentClass"]
    target_class = target["compartmentClass"]
    if source_class in RESTRICTED_CLASSES and target_class in GLOBAL_CLASSES and operation in {"write_memory", "embedding_write", "memory_promotion"}:
        if admitted:
            diagnostics.append("restricted source compartments cannot write or promote directly to global/firm-approved compartments")
        if writeback.get("performed"):
            diagnostics.append("restricted-to-global rejected examples must not perform durable writeback")

    if operation == "clean_room_release" and outcome != "clean_room_release_allowed" and admitted:
        diagnostics.append("clean room release admission requires clean_room_release_allowed outcome")

    if not admitted and reason == "same_wall_allowed":
        diagnostics.append("non-admitted operations cannot use same_wall_allowed")
    if writeback.get("performed") and not writeback.get("writebackRef"):
        diagnostics.append("performed writeback requires writebackRef")
    if writeback.get("performed") and not writeback.get("durableWritebackEnabled"):
        diagnostics.append("performed writeback requires durableWritebackEnabled=true")

    return diagnostics


def expected_semantic_result(path: Path) -> str:
    return "fail" if ".rejected." in path.name or path.name.startswith("bad-") else "pass"


def main() -> int:
    schema = load_json(SCHEMA)
    Draft202012Validator.check_schema(schema)
    examples = sorted(EXAMPLE_DIR.glob("*.example.json"))
    if not examples:
        raise SystemExit("No WallGuard memory compartment gate examples found")

    results = []
    for path in examples:
        record = load_json(path)
        validate_schema(record, schema, source_label=str(path))
        diagnostics = semantic_diagnostics(record)
        actual = "fail" if diagnostics else "pass"
        expected = expected_semantic_result(path)
        results.append({"example": path.name, "expected": expected, "actual": actual, "diagnostics": diagnostics})
        if expected != actual:
            raise ValueError(json.dumps(results[-1], indent=2))

    print(json.dumps({"ok": True, "checked": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
