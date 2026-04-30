#!/usr/bin/env python3
"""Validate the Slash Topic memory profile schema and example."""

from __future__ import annotations

from pathlib import Path
import json

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "slash-topic-memory-profile.schema.json"
EXAMPLE = ROOT / "examples" / "slash-topics" / "memory-profile.example.json"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    schema = load_json(SCHEMA)
    example = load_json(EXAMPLE)

    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(example), key=lambda e: list(e.path))
    if errors:
        print("Slash Topic memory profile failed schema validation:")
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "<root>"
            print(f" - {location}: {error.message}")
        return 1

    # Acceptance-criteria checks from the issue.

    recall = example["recallPolicy"]
    if recall["sensitivePayloadStorage"] != "disallowed":
        print(
            "Slash Topic memory profile must set sensitivePayloadStorage to "
            "'disallowed' by default (no raw sensitive payloads stored)."
        )
        return 1

    writeback = example["writebackPolicy"]
    if writeback["dryRunMode"] != "no-writeback":
        print(
            "Slash Topic memory profile dryRunMode must be 'no-writeback' "
            "(no memory writeback in dry-run mode)."
        )
        return 1

    dry_run = example.get("dryRun", {})
    if not dry_run.get("enabled", False):
        print("Slash Topic memory profile example must demonstrate dry-run mode.")
        return 1

    plan = dry_run.get("queryRoutingPlan", {})
    if not plan.get("memoryProfileRef") or not plan.get("memoryEventRef"):
        print(
            "Slash Topic memory profile dryRun.queryRoutingPlan must supply "
            "both memoryProfileRef and memoryEventRef (Lattice QueryRoutingDryRunPlan mapping)."
        )
        return 1

    if plan["memoryProfileRef"] != example["memoryProfileRef"]:
        print(
            "dryRun.queryRoutingPlan.memoryProfileRef must match the top-level "
            "memoryProfileRef."
        )
        return 1

    if not example.get("evidenceRefs"):
        print("Slash Topic memory profile requires at least one evidenceRef.")
        return 1

    lab = example.get("labProfile", {})
    if lab.get("launchLabJobs") is not False:
        print(
            "labProfile.launchLabJobs must be false; lab profile selection "
            "must not trigger background lab jobs."
        )
        return 1

    print("Slash Topic memory profile validates against schema and acceptance criteria.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
