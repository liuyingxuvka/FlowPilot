"""Run FlowGuard checks for the new FlowPilot lifecycle guard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from flowguard import Explorer

try:  # pragma: no cover
    from . import flowpilot_lifecycle_guard_model as model
except ImportError:  # pragma: no cover
    import flowpilot_lifecycle_guard_model as model


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
RESULTS_PATH = ROOT / "flowpilot_lifecycle_guard_results.json"


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
        "evidence_role": "lifecycle_guard_model_not_live_host_proof",
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
    lifecycle_test = REPO_ROOT / "tests" / "test_flowpilot_lifecycle_guard.py"
    fake_scenarios = ROOT / "flowpilot_fake_project_rehearsal_scenarios.py"
    lifecycle_text = lifecycle_test.read_text(encoding="utf-8")
    fake_text = fake_scenarios.read_text(encoding="utf-8")
    obligations = {
        "nonterminal_foreground_duty": "foreground_duty" in lifecycle_text and "process_next_action" in lifecycle_text,
        "wait_patrol_duty": "wait_patrol" in lifecycle_text and "wait_patrol" in fake_text,
        "final_preflight_blocks_open_packet": "test_final_preflight_rejects_open_packet" in lifecycle_text,
        "terminal_preflight_allows_return": "terminal_return" in lifecycle_text,
        "scoped_closure_fake_rehearsal_boundary": "final-preflight" in fake_text and "planning_chain_does_not_terminal" in fake_text,
        "recovery_or_blocker_duty": "recover_or_reissue" in fake_text and "control_plane_stuck" in lifecycle_text,
        "slow_live_progress_preserved": (
            "test_progress_keeps_slow_live_result_wait_in_patrol" in lifecycle_text
            and "slow_reviewer_progress_preserved" in fake_text
            and "still_working" in fake_text
        ),
        "liveness_failure_required_before_replacement": (
            "test_liveness_check_due_does_not_replace_without_failure_evidence" in lifecycle_text
            and "test_current_liveness_failure_allows_replacement_duty" in lifecycle_text
            and "no_output" in fake_text
        ),
        "accepted_packet_reassignment_rejected": (
            "test_accepted_packet_rejects_reassignment_and_ack_regression" in lifecycle_text
            and "accepted_packet_reassignment_rejected" in fake_text
            and "cannot assign accepted packet" in fake_text
        ),
        "accepted_packet_race_repair": "test_repair_accepted_packet_assignment_race_restores_original_result" in lifecycle_text,
        "terminal_lifecycle_stop_cancel": (
            "test_user_stop_terminal_fence_allows_exit_without_closure" in lifecycle_text
            and "test_user_cancel_terminal_fence_blocks_new_work" in lifecycle_text
            and "stop_terminal_fence" in fake_text
        ),
        "host_liveness_bridge": (
            "test_host_liveness_not_found_overrides_prior_progress" in lifecycle_text
            and "host_liveness_bridge_recovery" in fake_text
            and "host-liveness" in fake_text
        ),
        "orphan_evidence_recovery": (
            "test_orphan_runner_summary_routes_recovery_without_accepting_packet" in lifecycle_text
            and "orphan_runner_summary_recovery" in fake_text
            and "recover_orphan_evidence" in fake_text
        ),
    }
    missing = [name for name, ok in obligations.items() if not ok]
    return {
        "ok": not missing,
        "obligations": obligations,
        "missing": missing,
        "evidence": [
            "tests/test_flowpilot_lifecycle_guard.py",
            "simulations/flowpilot_fake_project_rehearsal_scenarios.py",
        ],
    }


def run_checks() -> dict[str, Any]:
    flowguard = _flowguard_report()
    target_plan = _target_plan_report()
    hazards = _hazard_report()
    alignment = _model_test_alignment_report()
    rows = [
        {
            "id": "new_lifecycle_guard_flowguard_model",
            "status": "passed" if flowguard["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["simulations/flowpilot_lifecycle_guard_model.py"],
        },
        {
            "id": "new_lifecycle_guard_target_plan",
            "status": "passed" if target_plan["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["openspec/changes/harden-new-flowpilot-liveness-recovery/tasks.md"],
        },
        {
            "id": "new_lifecycle_guard_hazard_replay",
            "status": "passed" if hazards["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["simulations/flowpilot_lifecycle_guard_model.py"],
        },
        {
            "id": "new_foreground_duty_model_test_alignment",
            "status": "passed" if alignment["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": alignment["evidence"],
        },
    ]
    return {
        "result_type": "flowpilot_lifecycle_guard_checks",
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
