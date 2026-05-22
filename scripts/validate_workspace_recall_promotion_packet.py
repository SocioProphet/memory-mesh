#!/usr/bin/env python3
"""Validate WorkspaceRecallPromotionPacket example."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/workspace-recall-promotion-packet.schema.json"
EXAMPLE = ROOT / "examples/workspace-recall/promotion-packet.example.json"


def main():
    try:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        example = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        for key in schema["required"]:
            if key not in example:
                raise AssertionError(f"missing {key}")
        assert example["apiVersion"] == "memory.mesh.workspace-recall-promotion/v1"
        assert example["kind"] == "WorkspaceRecallPromotionPacket"
        assert example["sourceWorkspace"]["workroomRef"].startswith("workroom://")
        assert example["sourceWorkspace"]["contextGraphRef"]
        assert example["candidate"]["recallCandidateRef"]
        assert example["review"]["mode"] == "review_only"
        assert example["review"]["required"] is True
        assert example["promotion"]["enabled"] is False
        assert example["promotion"]["performed"] is False
        assert example["evidenceRefs"]
        assert example["policyDecisionRefs"]
    except Exception as exc:
        print(f"ERR: {exc}", file=sys.stderr)
        return 2
    print("OK: WorkspaceRecallPromotionPacket validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
