"""Run the focused FlowPilot complete-workstream FlowGuard child model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Sequence

from flowguard.explorer import Explorer

import flowpilot_complete_workstream_orchestration_model as model


RESULTS_PATH = Path(__file__).resolve().with_name(
    "flowpilot_complete_workstream_orchestration_results.json"
)

REQUIRED_LABELS = (
    "substantive_role_workstream_started",
    "role_understands_bounded_assignment",
    "role_writes_specific_numbered_plan",
    "role_records_risk_and_flowguard_decision",
    "role_executes_bounded_plan",
    "role_integrates_own_and_delegated_outputs",
    "role_verifies_and_self_repairs_in_scope",
    "role_submits_plan_completion_report",
    "reviewer_audits_plan_rows_against_artifacts",
    "pm_disposes_sub9_reviewer_score",
    "substantive_role_workstream_complete",
)

HAZARD_EXPECTED_FAILURES = {
    "missing_plan": "role executed before writing a numbered plan",
    "vague_plan": "role executed from a missing or vague plan",
    "incomplete_required_step": "Reviewer accepted an incomplete required plan step",
    "completion_contradiction": "completion claim contradicts incomplete plan rows",
    "evidence_mismatch": "reported plan evidence does not match actual artifacts",
    "stale_evidence": "role or Reviewer used stale evidence for completion",
    "delegation_not_integrated": "delegated outputs were not integrated",
    "verification_missing": "role submitted without current verification",
    "repair_missing": "role left a known in-scope defect unrepaired",
    "unresolved_hidden": "substantive report hid unresolved work",
    "role_local_flowguard_self_approval": "role-local FlowGuard self-approved",
    "formal_gate_replaced": "role-local FlowGuard replaced a required independent gate",
    "worker_product_scope_leak": "Worker changed PM-owned product scope",
    "worker_route_authority_leak": "Worker changed PM-owned route or acceptance boundaries",
    "controller_substantive_plan": "non-substantive Controller entered",
    "pm_ignored_sub9": "PM silently ignored a Reviewer score below 9",
}


def _state_id(state: model.State) -> str:
    return (
        f"role={state.role}|status={state.status}|"
        f"lifecycle={state.assignment_understood},{state.numbered_plan_written_before_execution},"
        f"{state.risk_decision_recorded},{state.execution_completed},{state.integration_completed},"
        f"{state.verification_completed},{state.report_submitted}|"
        f"review={state.reviewer_audited_plan_against_artifacts},{state.reviewer_score},"
        f"{state.pm_disposed_sub9_score}"
    )


def _graph_report() -> dict[str, object]:
    initials = model.initial_states()
    queue: deque[model.State] = deque(initials)
    states = list(initials)
    index = {state: idx for idx, state in enumerate(states)}
    edges: list[list[tuple[str, int]]] = [[] for _ in states]
    labels: set[str] = set()
    failures: list[dict[str, object]] = []
    while queue:
        state = queue.popleft()
        source = index[state]
        current_failures = model.invariant_failures(state)
        if current_failures:
            failures.append({"state": _state_id(state), "failures": current_failures})
        for transition in model.next_safe_states(state):
            labels.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(states)
                states.append(transition.state)
                edges.append([])
                queue.append(transition.state)
            edges[source].append((transition.label, index[transition.state]))

    success = {idx for idx, state in enumerate(states) if model.is_success(state)}
    can_reach_success = set(success)
    changed = True
    while changed:
        changed = False
        for idx, outgoing in enumerate(edges):
            if idx not in can_reach_success and any(target in can_reach_success for _label, target in outgoing):
                can_reach_success.add(idx)
                changed = True
    stuck = [
        _state_id(state)
        for idx, state in enumerate(states)
        if not model.is_terminal(state) and not edges[idx]
    ]
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    missing_role_success = sorted(
        role
        for role in model.SUBSTANTIVE_ROLES
        if not any(state.role == role and model.is_success(state) for state in states)
    )
    initial_progress = all(index[state] in can_reach_success for state in initials)
    return {
        "ok": not failures and not missing_labels and not stuck and not missing_role_success and initial_progress,
        "state_count": len(states),
        "edge_count": sum(len(row) for row in edges),
        "missing_labels": missing_labels,
        "missing_role_success": missing_role_success,
        "invariant_failures": failures,
        "stuck_states": stuck,
        "all_initial_roles_can_reach_success": initial_progress,
        "fairness": {
            "role_count": len(model.SUBSTANTIVE_ROLES),
            "success_role_count": len(model.SUBSTANTIVE_ROLES) - len(missing_role_success),
        },
    }


def _explorer_report() -> dict[str, object]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=model.initial_states(),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=lambda _input, state, _trace: model.is_terminal(state),
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


def _hazard_report() -> dict[str, object]:
    rows: dict[str, object] = {}
    ok = True
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in failures)
        rows[name] = {"detected": detected, "expected": expected, "failures": failures}
        ok = ok and detected
    return {"ok": ok, "known_bad_count": len(rows), "rows": rows}


def _implementation_alignment() -> dict[str, object]:
    root = Path(__file__).resolve().parents[1]
    paths = {
        "handoff": root / "skills/flowpilot/assets/flowpilot_core_runtime/role_handoff.py",
        "contracts": root / "skills/flowpilot/assets/flowpilot_core_runtime/packet_result_contracts.py",
        "runtime": root / "skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
        "pm": root / "skills/flowpilot/assets/runtime_kit/cards/roles/project_manager.md",
        "worker": root / "skills/flowpilot/assets/runtime_kit/cards/roles/worker.md",
        "reviewer": root / "skills/flowpilot/assets/runtime_kit/cards/roles/human_like_reviewer.md",
        "flowguard": root / "skills/flowpilot/assets/runtime_kit/cards/roles/flowguard_operator.md",
    }
    texts = {key: path.read_text(encoding="utf-8").lower() for key, path in paths.items()}
    checks = {
        "shared_handoff_lifecycle": "workstream plan and completion" in texts["handoff"],
        "semantic_self_check_shape": "workstream_plan_and_completion" in texts["contracts"],
        "accountable_leaf_wording": "independently accountable complete workstream" in texts["runtime"],
        "pm_long_project_posture": "long-running" in texts["pm"] or "long project" in texts["pm"],
        "worker_numbered_plan": "numbered plan" in texts["worker"],
        "reviewer_plan_artifact_audit": "plan" in texts["reviewer"] and "artifact" in texts["reviewer"],
        "flowguard_no_self_approval": "self-approval" in texts["flowguard"] or "self-approve" in texts["flowguard"],
        "controller_excluded": "controller" in texts["handoff"] and "foreground action ledger" in texts["handoff"],
    }
    missing = sorted(key for key, value in checks.items() if not value)
    return {
        "ok": not missing,
        "checks": checks,
        "missing": missing,
        "paths": [path.relative_to(root).as_posix() for path in paths.values()],
    }


def run_checks() -> dict[str, object]:
    graph = _graph_report()
    explorer = _explorer_report()
    hazards = _hazard_report()
    alignment = _implementation_alignment()
    successes = {
        role: model.invariant_failures(model.success_state(role))
        for role in model.SUBSTANTIVE_ROLES
    }
    target_ok = all(not failures for failures in successes.values())
    return {
        "model_id": model.MODEL_ID,
        "ok": graph["ok"] and explorer["ok"] and hazards["ok"] and alignment["ok"] and target_ok,
        "safe_graph_and_progress": graph,
        "flowguard_explorer": explorer,
        "known_bad_hazards": hazards,
        "implementation_alignment": alignment,
        "target_success_failures": successes,
        "claim_boundary": (
            "This focused finite-state model proves only the declared role lifecycle and known-bad mutations; "
            "it does not prove arbitrary future AI semantics."
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args(argv)
    result = run_checks()
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
