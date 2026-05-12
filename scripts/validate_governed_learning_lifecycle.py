#!/usr/bin/env python3
"""Validate governed learning lifecycle and review queue examples."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE_SCHEMA = ROOT / "schemas" / "governed-learning-lifecycle-record.schema.json"
QUEUE_SCHEMA = ROOT / "schemas" / "governed-learning-review-queue-metrics.schema.json"
EXAMPLE_DIR = ROOT / "examples" / "governed-learning"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_schema(instance: dict, schema: dict, *, source_label: str) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
    if errors:
        lines = [f"{source_label} failed validation:"]
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "<root>"
            lines.append(f" - {location}: {error.message}")
        raise ValueError("\n".join(lines))


def validate_lifecycle_invariants(record: dict, *, source_label: str) -> None:
    status = record["lifecycleStatus"]
    governance = record["governance"]
    writeback = record["writeback"]
    redaction = record["redaction"]
    envelope = record["memoryObject"]["representationEnvelope"]

    if redaction["rawSensitivePayloadStored"] is not False:
        raise ValueError(f"{source_label}: lifecycle examples must not store raw sensitive payloads")

    if not record.get("evidenceRefs"):
        raise ValueError(f"{source_label}: lifecycle examples require evidenceRefs")

    if not record.get("policyDecisionRefs"):
        raise ValueError(f"{source_label}: lifecycle examples require policyDecisionRefs")

    if envelope["evidenceRefs"] != record["evidenceRefs"]:
        raise ValueError(f"{source_label}: representationEnvelope.evidenceRefs must match top-level evidenceRefs")

    if status == "accepted-memory":
        if governance["reviewStatus"] != "approved" or not governance.get("approvalRef"):
            raise ValueError(f"{source_label}: accepted memory requires approved review and approvalRef")
        if writeback["enabled"] is not True or writeback["performed"] is not True or not writeback.get("writebackRef"):
            raise ValueError(f"{source_label}: accepted memory requires performed writebackRef")
        if envelope["cacheState"] != "promoted" or envelope["revocationStatus"] != "active":
            raise ValueError(f"{source_label}: accepted memory must be promoted and active")

    if status == "rejected-proposal":
        if governance["reviewStatus"] != "rejected" or not governance.get("rejectionRef"):
            raise ValueError(f"{source_label}: rejected proposal requires rejectionRef")
        if writeback["enabled"] is not False or writeback["performed"] is not False or writeback.get("writebackRef") is not None:
            raise ValueError(f"{source_label}: rejected proposal must not write back")
        if envelope["writePolicy"]["mode"] != "no-writeback":
            raise ValueError(f"{source_label}: rejected proposal must carry no-writeback policy")

    if status == "revoked-memory":
        if governance["reviewStatus"] != "revoked" or not governance.get("revocationRef") or not governance.get("tombstoneRef"):
            raise ValueError(f"{source_label}: revoked memory requires revocationRef and tombstoneRef")
        if envelope["cacheState"] != "revoked" or envelope["revocationStatus"] != "revoked":
            raise ValueError(f"{source_label}: revoked memory must carry revoked cache/revocation state")
        if envelope["writePolicy"]["mode"] != "tombstone-writeback":
            raise ValueError(f"{source_label}: revoked memory must use tombstone-writeback policy")

    if status == "conflict-reconciliation":
        if governance["reviewStatus"] != "reconciled" or not governance.get("reconciliationRef"):
            raise ValueError(f"{source_label}: conflict reconciliation requires reconciliationRef")
        if not governance.get("conflictsWith") or not governance.get("supersedesRefs"):
            raise ValueError(f"{source_label}: conflict reconciliation requires conflictsWith and supersedesRefs")
        if writeback["enabled"] is not True or writeback["performed"] is not True or not writeback.get("writebackRef"):
            raise ValueError(f"{source_label}: conflict reconciliation requires performed writebackRef")


def validate_queue_invariants(metrics: dict, *, source_label: str) -> None:
    counts = metrics["counts"]
    if counts["arrived"] < counts["promoted"] + counts["rejected"]:
        raise ValueError(f"{source_label}: arrived count must cover promoted and rejected records")
    if counts["pending"] > counts["arrived"]:
        raise ValueError(f"{source_label}: pending count cannot exceed arrived count")
    for reason in metrics.get("blockedReasons", []):
        if reason["count"] == 0:
            raise ValueError(f"{source_label}: blocked reason entries should have positive counts")


def main() -> int:
    lifecycle_schema = load_json(LIFECYCLE_SCHEMA)
    queue_schema = load_json(QUEUE_SCHEMA)
    Draft202012Validator.check_schema(lifecycle_schema)
    Draft202012Validator.check_schema(queue_schema)

    lifecycle_examples = sorted(EXAMPLE_DIR.glob("lifecycle.*.example.json"))
    if not lifecycle_examples:
        raise SystemExit("No governed learning lifecycle examples found")

    checked = []
    for path in lifecycle_examples:
        data = load_json(path)
        validate_schema(data, lifecycle_schema, source_label=str(path))
        validate_lifecycle_invariants(data, source_label=str(path))
        checked.append(path.name)

    queue_examples = sorted(EXAMPLE_DIR.glob("review-queue.*.example.json"))
    if not queue_examples:
        raise SystemExit("No governed learning review queue examples found")

    for path in queue_examples:
        data = load_json(path)
        validate_schema(data, queue_schema, source_label=str(path))
        validate_queue_invariants(data, source_label=str(path))
        checked.append(path.name)

    print(json.dumps({"ok": True, "checked": checked}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
