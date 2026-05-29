#!/usr/bin/env python3
"""Validate channel provenance memory write-gate examples."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "channel-provenance-memory-write-gate.schema.json"
EXAMPLE_DIR = ROOT / "examples" / "channel-provenance"
HIGH_RISK_SINKS = {"confirmed_memory", "graph_edge", "claim_promotion", "policy_binding", "high_risk_action", "publish", "delete", "authorize_agent"}


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
    requested_sink = record["promotion"]["requestedSink"]
    envelope = record["authorityEnvelope"]
    collapse = record.get("collapseDecision")
    writeback = record["writeback"]
    review = record["review"]

    if requested_sink not in envelope["allowedSinks"]:
        diagnostics.append(f"requested sink {requested_sink} is not allowed by channel authority envelope")

    if requested_sink in envelope["disallowedSinks"]:
        diagnostics.append(f"requested sink {requested_sink} is explicitly disallowed by channel authority envelope")

    if requested_sink in envelope["requiresRepairFor"]:
        repair_refs = [] if collapse is None else collapse.get("repairEventRefs", [])
        if not repair_refs:
            diagnostics.append(f"requested sink {requested_sink} requires repair event refs")

    if requested_sink in HIGH_RISK_SINKS:
        if review["status"] != "approved" or not review.get("approvalRef"):
            diagnostics.append(f"high-risk sink {requested_sink} requires approved review and approvalRef")
        if not writeback.get("enabled"):
            diagnostics.append(f"high-risk sink {requested_sink} cannot be promoted with writeback disabled")

    if record["redaction"]["rawSensitivePayloadStored"] is not False:
        diagnostics.append("raw sensitive payload storage must remain false")

    if writeback["performed"] and not writeback.get("writebackRef"):
        diagnostics.append("performed writeback requires writebackRef")

    if record["memoryClass"] == "confirmed_memory" and record["promotion"]["promotionState"] != "confirmed":
        diagnostics.append("confirmed_memory requires confirmed promotionState")

    if record["memoryClass"] != "confirmed_memory" and requested_sink == "confirmed_memory":
        diagnostics.append("confirmed_memory sink requires confirmed_memory class")

    if record["interpretant"]["selectedRef"] not in record["interpretant"]["candidateRefs"]:
        diagnostics.append("selected interpretant must be one of candidateRefs")

    return diagnostics


def expected_semantic_result(path: Path) -> str:
    return "fail" if ".rejected." in path.name or path.name.startswith("bad-") else "pass"


def main() -> int:
    schema = load_json(SCHEMA)
    Draft202012Validator.check_schema(schema)
    examples = sorted(EXAMPLE_DIR.glob("write-gate.*.example.json"))
    if not examples:
        raise SystemExit("No channel provenance write-gate examples found")

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
