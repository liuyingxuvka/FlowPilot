"""Run FlowGuard checks for the clean FlowPilot protocol kernel."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

try:  # pragma: no cover
    from . import flowpilot_protocol_kernel_model as model
except ImportError:  # pragma: no cover
    import flowpilot_protocol_kernel_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_protocol_kernel_results.json"

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [
        "accept_verified_result",
        "block_missing_ack",
        "block_ack_without_output",
        "block_wrong_packet_shape",
        "block_closed_agent_output",
        "block_self_review",
        "block_weak_review",
        "block_stale_evidence",
        "block_route_mutation_old_packet",
        "block_flowguard_wrong_target",
        "block_final_closure_gap",
    ]
)


def _flowguard_report() -> dict[str, Any]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=model.terminal_predicate,
        success_predicate=lambda state, _trace: model.is_success(state),
        required_labels=REQUIRED_LABELS,
    ).explore()
    return {
        "ok": report.ok,
        "summary": report.summary,
        "violation_count": len(report.violations),
        "dead_branch_count": len(report.dead_branches),
        "exception_branch_count": len(report.exception_branches),
        "reachability_failure_count": len(report.reachability_failures),
        "reachability_failures": [failure.message for failure in report.reachability_failures],
    }


def _hazard_report() -> dict[str, Any]:
    hazards: dict[str, list[str]] = {}
    for name, state in model.hazard_states().items():
        failures = model.hard_check_failures(state)
        if failures:
            hazards[name] = failures
    expected = set(model.hazard_states())
    return {
        "ok": set(hazards) == expected,
        "hazards": hazards,
        "expected": sorted(expected),
    }


def _matrix_report() -> dict[str, Any]:
    matrix = model.scenario_matrix()
    expected = {
        model.SUCCESS: "accept_verified_result",
        model.MISSING_ACK: "block_missing_ack",
        model.ACK_WITHOUT_OUTPUT: "block_ack_without_output",
        model.WRONG_PACKET_SHAPE: "block_wrong_packet_shape",
        model.CLOSED_AGENT_OUTPUT: "block_closed_agent_output",
        model.SELF_REVIEW: "block_self_review",
        model.WEAK_REVIEW: "block_weak_review",
        model.STALE_EVIDENCE: "block_stale_evidence",
        model.ROUTE_MUTATION_OLD_PACKET: "block_route_mutation_old_packet",
        model.FLOWGUARD_WRONG_TARGET: "block_flowguard_wrong_target",
        model.FINAL_CLOSURE_GAP: "block_final_closure_gap",
    }
    mismatches = {
        scenario: {"expected": expected_label, "actual": matrix.get(scenario)}
        for scenario, expected_label in expected.items()
        if matrix.get(scenario) != expected_label
    }
    return {"ok": not mismatches, "matrix": matrix, "mismatches": mismatches}


def run_checks() -> dict[str, Any]:
    flowguard = _flowguard_report()
    hazards = _hazard_report()
    matrix = _matrix_report()
    report = {
        "result_type": "flowpilot_protocol_kernel_kernel",
        "model_id": model.MODEL_ID,
        "flowguard": flowguard,
        "hazard_detection": hazards,
        "scenario_matrix": matrix,
        "safe_scenarios": sorted(model.SAFE_SCENARIOS),
        "risk_scenarios": sorted(model.RISK_SCENARIOS),
        "ok": bool(flowguard["ok"] and hazards["ok"] and matrix["ok"]),
    }
    RESULTS_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = run_checks()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"[flowpilot-protocol-kernel] ok={report['ok']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
