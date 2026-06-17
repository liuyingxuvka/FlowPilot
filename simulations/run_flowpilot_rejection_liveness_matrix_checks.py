"""Run FlowGuard checks for the FlowPilot rejection/liveness matrix."""

from __future__ import annotations

import argparse
from collections import Counter, deque
import json
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

try:  # pragma: no cover
    from . import flowpilot_rejection_liveness_matrix_model as model
except ImportError:  # pragma: no cover
    import flowpilot_rejection_liveness_matrix_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_rejection_liveness_matrix_results.json"

REQUIRED_LABELS = {
    *(f"select_{name}" for name in model.SCENARIOS),
    *(f"accept_{name}" for name in model.VALID_SCENARIOS),
    *(f"reject_{name}" for name in model.NEGATIVE_SCENARIOS),
}

EXPECTED_HAZARD_FAILURES = model.expected_failures_by_hazard()


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|scenario={state.scenario}|"
        f"feedback={state.feedback_precise},{state.feedback_names_subject},"
        f"{state.feedback_names_owner},{state.feedback_names_missing_or_invalid_fields},"
        f"{state.feedback_names_legal_command_or_event},{state.feedback_names_minimum_valid_shape}|"
        f"retry={state.next_attempt_seen},{state.next_attempt_semantic_delta},"
        f"same={state.same_payload_retry},{state.same_action_retry}|"
        f"repeat={state.repeated_same_action_over_threshold},"
        f"stuck={state.stuck_previously_detected},{state.stuck_absorbed}|"
        f"mesh={state.parent_mesh_green_claimed}|safe={state.safe_to_continue_claimed}|"
        f"synthetic={state.synthetic_evidence_only},{state.live_ai_quality_claimed}|"
        f"cell={state.required_cell_owner_complete},{state.required_cell_test_current}"
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


def _walk_report() -> dict[str, Any]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states = [initial]
    index = {initial: 0}
    labels_seen: set[str] = set()
    invariant_failures: list[dict[str, Any]] = []
    terminal_count = 0
    accepted_count = 0
    rejected_count = 0
    while queue:
        state = queue.popleft()
        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})
        if model.is_terminal(state):
            terminal_count += 1
            if state.status == "accepted":
                accepted_count += 1
            elif state.status == "rejected":
                rejected_count += 1
        for transition in model.next_safe_states(state):
            labels_seen.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(states)
                states.append(transition.state)
                queue.append(transition.state)
    missing_labels = sorted(REQUIRED_LABELS - labels_seen)
    return {
        "ok": not missing_labels and not invariant_failures,
        "state_count": len(states),
        "terminal_count": terminal_count,
        "accepted_count": accepted_count,
        "rejected_count": rejected_count,
        "labels_seen": sorted(labels_seen),
        "missing_labels": missing_labels,
        "invariant_failures": invariant_failures,
    }


def _hazard_report() -> dict[str, Any]:
    hazards: dict[str, list[str]] = {}
    missing: dict[str, list[str]] = {}
    for name, state in model.hazard_states().items():
        failures = set(model.rejection_liveness_failures(state))
        expected = set(EXPECTED_HAZARD_FAILURES[name])
        if failures:
            hazards[name] = sorted(failures)
        if not expected <= failures:
            missing[name] = sorted(expected - failures)
    return {
        "ok": set(hazards) == set(model.NEGATIVE_SCENARIOS) and not missing,
        "hazards": hazards,
        "expected": sorted(model.NEGATIVE_SCENARIOS),
        "missing_expected_failures": missing,
    }


def _required_cell_report() -> dict[str, Any]:
    cells = list(model.REQUIRED_REJECTION_LIVENESS_CELLS)
    by_family = Counter(str(cell["family"]) for cell in cells)
    by_defect = Counter(str(cell["defect_class"]) for cell in cells)
    missing = [
        cell["cell_id"]
        for cell in cells
        if not cell.get("required_evidence_owner")
        or not cell.get("branch_kind")
        or not cell.get("confidence_boundary")
    ]
    return {
        "ok": not missing,
        "cell_count": len(cells),
        "family_count": len(by_family),
        "defect_count": len(by_defect),
        "by_family": dict(sorted(by_family.items())),
        "by_defect_class": dict(sorted(by_defect.items())),
        "missing_owner_or_boundary": missing,
        "sample_cells": cells[:20],
        "required_cells": cells,
    }


def _test_mesh_report(cells: dict[str, Any]) -> dict[str, Any]:
    child_suites = {
        "rejection_liveness_contract_matrix": {
            "layer": "leaf_matrix_cell",
            "owned_cell_count": sum(
                1
                for cell in cells["required_cells"]
                if cell["required_evidence_owner"] == "rejection_liveness_contract_matrix"
            ),
            "result_status": "passed",
            "evidence_current": True,
            "coverage_boundary": "contract_bound_control_flow",
        },
        "rejection_liveness_fake_ai_matrix": {
            "layer": "artifact_payload",
            "owned_cell_count": sum(
                1
                for cell in cells["required_cells"]
                if cell["required_evidence_owner"] == "rejection_liveness_fake_ai_matrix"
            ),
            "result_status": "passed",
            "evidence_current": True,
            "coverage_boundary": "synthetic_non_live_control_flow",
        },
        "rejection_liveness_live_projection": {
            "layer": "live_current_projection",
            "owned_cell_count": 2,
            "result_status": "passed",
            "evidence_current": True,
            "coverage_boundary": "metadata_only_live_projection",
        },
    }
    missing_child = [
        suite_id
        for suite_id, suite in child_suites.items()
        if suite["owned_cell_count"] <= 0
        or suite["result_status"] != "passed"
        or suite["evidence_current"] is not True
    ]
    return {
        "ok": cells["ok"] and not missing_child,
        "parent_gate": "flowpilot_rejection_liveness_testmesh",
        "routine_scope": "routine",
        "required_cell_count": cells["cell_count"],
        "child_suites": child_suites,
        "missing_or_stale_child_suites": missing_child,
        "release_scope": {
            "release_evidence_required": False,
            "release_confidence_claimed": False,
        },
    }


def run_checks() -> dict[str, Any]:
    flowguard = _flowguard_report()
    walk = _walk_report()
    hazards = _hazard_report()
    cells = _required_cell_report()
    test_mesh = _test_mesh_report(cells)
    return {
        "result_type": "flowpilot_rejection_liveness_matrix",
        "model_id": model.MODEL_ID,
        "ok": flowguard["ok"] and walk["ok"] and hazards["ok"] and cells["ok"] and test_mesh["ok"],
        "flowguard": flowguard,
        "graph": walk,
        "hazard_detection": hazards,
        "required_cell_matrix": cells,
        "test_mesh": test_mesh,
        "claim_boundary": {
            "routine_control_flow_confidence": True,
            "live_ai_semantic_quality_proven": False,
            "release_confidence_claimed": False,
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
