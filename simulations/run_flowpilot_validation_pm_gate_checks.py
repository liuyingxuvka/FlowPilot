"""Run FlowGuard checks for FlowPilot validation automation and PM gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

try:  # pragma: no cover
    from . import flowpilot_validation_pm_gate_model as model
except ImportError:  # pragma: no cover
    import flowpilot_validation_pm_gate_model as model


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
RESULTS_PATH = ROOT / "flowpilot_validation_pm_gate_results.json"


def _flowguard_report() -> dict[str, Any]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=model.terminal_predicate,
        success_predicate=lambda state, _trace: model.is_success(state),
        required_labels=model.REQUIRED_SAFE_LABELS,
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


def _target_plan_report() -> dict[str, Any]:
    state = model.target_state()
    failures = model.invariant_failures(state)
    return {
        "ok": not failures and model.is_success(state),
        "evidence_role": "validation_pm_gate_model_not_live_host_proof",
        "failures": failures,
        "state": model.state_summary(state),
        "labels": list(model.REQUIRED_SAFE_LABELS),
    }


def _hazard_report() -> dict[str, Any]:
    hazards: dict[str, list[str]] = {}
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        if failures:
            hazards[name] = failures
    return {
        "ok": set(hazards) == set(model.hazard_states()),
        "hazards": hazards,
        "expected": sorted(model.hazard_states()),
    }


def _model_test_alignment_report() -> dict[str, Any]:
    high_standard_test = REPO_ROOT / "tests" / "test_flowpilot_high_standard_control_flow.py"
    core_runtime_test = REPO_ROOT / "tests" / "test_flowpilot_core_runtime.py"
    runtime = REPO_ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_core_runtime" / "runtime.py"
    test_text = high_standard_test.read_text(encoding="utf-8")
    core_test_text = core_runtime_test.read_text(encoding="utf-8")
    runtime_text = runtime.read_text(encoding="utf-8")
    obligations = {
        "system_validation_helper": "_record_system_validation_for_packet" in runtime_text,
        "system_closure_helper": "_auto_close_packet_after_system_validation" in runtime_text,
        "system_closure_ledger": "system_closures" in runtime_text,
        "reviewer_pass_no_closure_flowguard_operator_packet": "test_reviewer_pass_auto_closes_without_closure_flowguard_operator_packet" in test_text,
        "system_validation_failure_routes_pm": "test_system_validation_failure_routes_to_pm_repair" in test_text,
        "old_validator_closure_roles_removed": "test_validator_and_closure_flowguard_operator_are_not_runtime_roles" in test_text,
        "old_validation_closure_packets_rejected": "test_validation_and_closure_packet_kinds_are_rejected" in test_text,
        "pm_decision_gate_ledger": "pm_decision_gates" in runtime_text,
        "pm_redesign_route_repair_gated": "test_pm_redesign_route_repair_is_gated_before_application" in test_text,
        "pm_current_scope_repair_gated": "test_pm_repair_current_scope_for_packet_scope_is_gated_before_application" in test_text,
        "pm_redesign_route_disposition_gated": "test_pm_redesign_route_disposition_is_gated_before_application" in test_text,
        "runtime_staged_effect_helper": "_attach_staged_effect" in runtime_text,
        "route_redesign_staged_effect_kind": "commit_route_redesign" in runtime_text,
        "node_acceptance_staged_effect_kind": "commit_node_acceptance_plan" in runtime_text,
        "staged_node_acceptance_test": "test_node_acceptance_plan_result_stages_effect_before_closure" in core_test_text,
        "staged_route_redesign_test": "test_redesign_route_pm_decision_stages_route_effect_until_gate_applies" in core_test_text,
        "current_target_bad_packet_tests": (
            "test_result_submitted_repair_target_is_superseded_after_reissue" in core_test_text
            and "test_nested_pm_repair_decision_wrapper_is_rejected_and_reissued" in core_test_text
        ),
        "staged_effect_same_family_convergence_test": (
            "test_staged_effect_same_family_reuses_pending_effect" in core_test_text
        ),
        "review_future_state_boundary_card_test": "test_current_contract_staged_effect_guidance_is_role_scoped" in (
            REPO_ROOT / "tests" / "test_flowpilot_card_instruction_coverage.py"
        ).read_text(encoding="utf-8"),
    }
    missing = [name for name, ok in obligations.items() if not ok]
    return {
        "ok": not missing,
        "obligations": obligations,
        "missing": missing,
        "evidence": [
            "skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
            "tests/test_flowpilot_high_standard_control_flow.py",
            "tests/test_flowpilot_core_runtime.py",
            "tests/test_flowpilot_card_instruction_coverage.py",
        ],
    }


def run_checks() -> dict[str, Any]:
    flowguard = _flowguard_report()
    target_plan = _target_plan_report()
    hazards = _hazard_report()
    alignment = _model_test_alignment_report()
    rows = [
        {
            "id": "validation_pm_gate_flowguard_model",
            "status": "passed" if flowguard["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["simulations/flowpilot_validation_pm_gate_model.py"],
        },
        {
            "id": "validation_pm_gate_target_plan",
            "status": "passed" if target_plan["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["openspec/changes/auto-close-after-system-validation/tasks.md"],
        },
        {
            "id": "validation_pm_gate_hazard_replay",
            "status": "passed" if hazards["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["simulations/flowpilot_validation_pm_gate_model.py"],
        },
        {
            "id": "validation_pm_gate_model_test_alignment",
            "status": "passed" if alignment["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": alignment["evidence"],
        },
    ]
    return {
        "result_type": "flowpilot_validation_pm_gate_checks",
        "model_id": model.MODEL_ID,
        "ok": flowguard["ok"] and target_plan["ok"] and hazards["ok"] and alignment["ok"],
        "flowguard": flowguard,
        "target_plan": target_plan,
        "hazard_detection": hazards,
        "model_test_alignment": alignment,
        "test_mesh": {
            "rows": rows,
            "routine_gate": {"ok": all(row["status"] == "passed" for row in rows)},
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--no-write-results", action="store_true")
    args = parser.parse_args()

    result = run_checks()
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(output, end="")
    if not args.no_write_results:
        args.json_out.write_text(output, encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
