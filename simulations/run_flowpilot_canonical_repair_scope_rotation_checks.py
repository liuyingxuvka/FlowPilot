"""Run FlowGuard checks for FlowPilot canonical repair-scope rotation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from flowguard import Explorer

try:  # pragma: no cover
    from . import flowpilot_canonical_repair_scope_rotation_model as model
except ImportError:  # pragma: no cover
    import flowpilot_canonical_repair_scope_rotation_model as model


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
RESULTS_PATH = ROOT / "flowpilot_canonical_repair_scope_rotation_results.json"


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
    runtime_path = REPO_ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_core_runtime" / "runtime.py"
    core_test_path = REPO_ROOT / "tests" / "test_flowpilot_core_runtime.py"
    high_standard_test_path = REPO_ROOT / "tests" / "test_flowpilot_high_standard_control_flow.py"
    recursive_test_path = REPO_ROOT / "tests" / "test_flowpilot_recursive_route_execution_runtime.py"
    runtime_text = runtime_path.read_text(encoding="utf-8")
    core_test_text = core_test_path.read_text(encoding="utf-8")
    high_standard_test_text = high_standard_test_path.read_text(encoding="utf-8")
    recursive_test_text = recursive_test_path.read_text(encoding="utf-8")
    obligations = {
        "five_choice_menu": (
            '"repair_current_scope"' in runtime_text
            and '"repair_parent_scope"' in runtime_text
            and '"redesign_route"' in runtime_text
            and '"waive_with_authority"' in runtime_text
            and '"stop_for_user"' in runtime_text
        ),
        "removed_decision_negative_test": "test_removed_pm_repair_decisions_are_rejected" in core_test_text,
        "fresh_packet_gate": "fresh repair packet does not exist" in runtime_text,
        "current_scope_replacement_test": "test_pm_disposition_repair_current_scope_creates_replacement_node" in high_standard_test_text,
        "parent_scope_replacement_test": "test_pm_repair_parent_scope_replaces_parent_and_descendants" in high_standard_test_text,
        "route_redesign_test": "test_pm_redesign_route_repair_is_gated_before_application" in high_standard_test_text,
        "june3_regression_test": "test_june3_same_node_empty_fresh_packet_regression_is_rejected" in core_test_text,
        "pm_disposition_current_name": "repair_current_scope" in high_standard_test_text,
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
            "id": "canonical_repair_scope_flowguard_model",
            "status": "passed" if flowguard["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["simulations/flowpilot_canonical_repair_scope_rotation_model.py"],
        },
        {
            "id": "canonical_repair_scope_target_plan",
            "status": "passed" if target_plan["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["openspec/changes/canonical-repair-scope-rotation/tasks.md"],
        },
        {
            "id": "canonical_repair_scope_hazard_replay",
            "status": "passed" if hazards["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["simulations/flowpilot_canonical_repair_scope_rotation_model.py"],
        },
        {
            "id": "canonical_repair_scope_model_test_alignment",
            "status": "passed" if alignment["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": alignment["evidence"],
        },
    ]
    return {
        "result_type": "flowpilot_canonical_repair_scope_rotation_checks",
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
