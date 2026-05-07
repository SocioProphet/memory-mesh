#!/usr/bin/env python3
"""Smoke-test AgentLearningProposal generation and validation."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts" / "create_agent_learning_proposal.py"
VALIDATOR = ROOT / "scripts" / "validate_agent_learning_proposal.py"


def die(message: str) -> None:
    print(f"Agent learning proposal generator smoke failed: {message}")
    raise SystemExit(1)


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=False)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "proposal.json"
        generated = run([
            sys.executable,
            str(GENERATOR),
            "--session-ref", "urn:srcos:session:generator-smoke",
            "--task-ref", "urn:srcos:task:generator-smoke",
            "--repo", "SocioProphet/agentplane",
            "--agent-ref", "agentplane:guarded-command-invocation",
            "--target-ref", "SocioProphet/agentplane",
            "--path", "AGENTS.md",
            "--title", "Capture guarded invocation remediation",
            "--summary", "Document that guarded invocations require a passing or waived stop gate before completion.",
            "--rationale", "Agents must not treat command success alone as task completion.",
            "--diff-content", "### Guarded invocation completion\n\nA guarded invocation is complete only when its command exits zero and the stop gate returns pass or waived.\n",
            "--evidence-ref", "urn:srcos:artifact:guarded-invocation:generator-smoke",
            "--policy-decision-ref", "agentplane/stop-gate/guardrail-clear",
            "--out", str(out),
        ])
        if generated.returncode != 0:
            die(f"generator failed: stdout={generated.stdout} stderr={generated.stderr}")
        if not out.exists():
            die("generator did not write output file")

        proposal = json.loads(out.read_text(encoding="utf-8"))
        if proposal["proposalMode"] != "review_only":
            die("generated proposal is not review_only")
        if proposal["writeback"]["enabled"] is not False or proposal["writeback"]["performed"] is not False:
            die("generated proposal enabled or performed writeback")
        if proposal["redaction"]["rawSensitivePayloadStored"] is not False:
            die("generated proposal stores raw sensitive payloads")

        validated = run([sys.executable, str(VALIDATOR), "--proposal", str(out)])
        if validated.returncode != 0:
            die(f"generated proposal failed validation: stdout={validated.stdout} stderr={validated.stderr}")

    print("Agent learning proposal generator smoke validates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
