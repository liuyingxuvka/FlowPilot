"""Final confidence FlowPilot test-tier commands."""

from __future__ import annotations

from .command_builders import TierCommand, _py


FINAL_CONFIDENCE_COMMANDS = (
    TierCommand(
        name="flowpilot_final_confidence_gate",
        command=_py(
            "simulations/run_flowpilot_final_confidence_gate_checks.py",
            "--run-checks",
            "--repository-confidence-only",
            "--evidence-manifest",
            "simulations/flowpilot_acceptance_testmesh_evidence_manifest.json",
            "--json-out",
            "simulations/flowpilot_final_confidence_gate_results.json",
        ),
        description=(
            "Fail-closed repository final-confidence consumer that consumes current audit, "
            "full model-test coverage, event idempotency, known-friction defect "
            "families, and Risk Evidence Ledger decisions after upstream TestMesh "
            "evidence closes. Per-run terminal-return authority remains scoped to "
            "that run's final-preflight."
        ),
        release_only=True,
        long_running=True,
        background_recommended=True,
        background_stage=1,
        evidence_dependency="terminal_consumer",
    ),
)
