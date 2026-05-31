"""Run FlowGuard checks for fresh FlowPilot semantic gate outcomes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from flowguard import Explorer

try:  # pragma: no cover
    from . import flowpilot_semantic_gate_outcome_model as model
except ImportError:  # pragma: no cover
    import flowpilot_semantic_gate_outcome_model as model


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
RESULTS_PATH = ROOT / "flowpilot_semantic_gate_outcome_results.json"


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
        "evidence_role": "semantic_gate_outcome_model_not_live_host_proof",
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
    core_test = REPO_ROOT / "tests" / "test_flowpilot_core_runtime.py"
    recursive_test = REPO_ROOT / "tests" / "test_flowpilot_recursive_route_execution_runtime.py"
    runtime = REPO_ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_core_runtime" / "runtime.py"
    test_text = high_standard_test.read_text(encoding="utf-8")
    core_test_text = core_test.read_text(encoding="utf-8")
    recursive_test_text = recursive_test.read_text(encoding="utf-8")
    runtime_text = runtime.read_text(encoding="utf-8")
    obligations = {
        "semantic_outcome_parser": "_parse_packet_outcome" in runtime_text,
        "structured_verdict_parser": '"verdict"' in runtime_text
        and "test_structured_verdict_blocked_routes_to_semantic_repair" in core_test_text,
        "nested_flowguard_report_failure_parser": '"flowguard_report"' in runtime_text
        and "test_nested_flowguard_report_not_ok_routes_to_semantic_repair" in core_test_text,
        "declared_outcome_line_parser": "_declared_outcome_token_from_body" in runtime_text,
        "no_whole_body_nonpass_scan": "_NONPASS_TEXT_RE" not in runtime_text,
        "declared_pass_context_words_test": "test_declared_pass_ignores_contextual_failure_words" in core_test_text,
        "declared_block_line_test": "test_declared_block_line_routes_to_semantic_repair" in core_test_text,
        "active_blocker_ledger": "active_blockers" in runtime_text,
        "effective_blocker_view": "_blocker_current_effective" in runtime_text,
        "effective_packet_final_view": "_packet_requires_current_acceptance" in runtime_text,
        "pm_repair_decision_packet": "pm_repair_decision" in runtime_text,
        "reviewer_block_no_validation": "test_reviewer_block_routes_to_pm_repair_and_requires_recheck" in test_text,
        "system_validation_failure_routes_pm": "test_system_validation_failure_routes_to_pm_repair" in test_text,
        "workerlock_no_flowguard": "test_workerlocked_result_routes_pm_repair_without_flowguard_pass" in test_text,
        "same_class_recheck": "required_recheck_role" in test_text and "\"cleared\"" in test_text,
        "final_ledger_effective_packets": "test_final_ledger_uses_current_effective_packets" in recursive_test_text,
    }
    missing = [name for name, ok in obligations.items() if not ok]
    return {
        "ok": not missing,
        "obligations": obligations,
        "missing": missing,
        "evidence": [
            "skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
            "tests/test_flowpilot_core_runtime.py",
            "tests/test_flowpilot_high_standard_control_flow.py",
            "tests/test_flowpilot_recursive_route_execution_runtime.py",
        ],
    }


def run_checks() -> dict[str, Any]:
    flowguard = _flowguard_report()
    target_plan = _target_plan_report()
    hazards = _hazard_report()
    alignment = _model_test_alignment_report()
    rows = [
        {
            "id": "semantic_gate_outcome_flowguard_model",
            "status": "passed" if flowguard["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["simulations/flowpilot_semantic_gate_outcome_model.py"],
        },
        {
            "id": "semantic_gate_outcome_target_plan",
            "status": "passed" if target_plan["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["openspec/changes/harden-new-flowpilot-effective-outcomes/tasks.md"],
        },
        {
            "id": "semantic_gate_outcome_hazard_replay",
            "status": "passed" if hazards["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["simulations/flowpilot_semantic_gate_outcome_model.py"],
        },
        {
            "id": "semantic_gate_outcome_model_test_alignment",
            "status": "passed" if alignment["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": alignment["evidence"],
        },
    ]
    return {
        "result_type": "flowpilot_semantic_gate_outcome_checks",
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
