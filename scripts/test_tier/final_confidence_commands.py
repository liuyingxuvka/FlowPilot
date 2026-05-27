"""Final confidence FlowPilot test-tier commands."""

from __future__ import annotations

from .command_builders import TierCommand, _py


FINAL_CONFIDENCE_COMMANDS = (
    TierCommand(
        name="flowpilot_final_confidence_gate",
        command=_py(
            "simulations/run_flowpilot_final_confidence_gate_checks.py",
            "--run-checks",
            "--json-out",
            "simulations/flowpilot_final_confidence_gate_results.json",
        ),
        description=(
            "Fail-closed final confidence gate that consumes current live audit, "
            "full model-test coverage, event idempotency, known-friction defect "
            "families, and Risk Evidence Ledger decisions."
        ),
    ),
)
