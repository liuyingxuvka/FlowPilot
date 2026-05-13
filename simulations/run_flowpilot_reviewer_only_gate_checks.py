"""Run checks for the FlowPilot Reviewer-only gate simplification model."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_reviewer_only_gate_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_reviewer_only_gate_results.json"

REQUIRED_LABELS = (
    "reviewer_only_gate_run_started",
    "pm_writes_root_contract",
    "reviewer_root_contract_card_emitted",
    "reviewer_passes_root_contract",
    "pm_freezes_root_contract_after_reviewer",
    "pm_writes_child_skill_manifest",
    "reviewer_child_skill_manifest_card_emitted",
    "reviewer_passes_child_skill_manifest",
    "pm_approves_child_skill_manifest_after_reviewer",
    "route_ready_after_reviewer_only_gates",
    "reviewer_only_gate_flow_complete",
)

HAZARD_EXPECTED_FAILURES = {
    "root_freeze_without_reviewer": "PM froze root contract before Reviewer pass",
    "root_freeze_waits_for_product_officer": "Reviewer-only root contract flow still required Product Officer",
    "root_freeze_requires_product_officer_artifact": "root contract freeze still required Product Officer artifact",
    "root_product_officer_card_emitted": "Reviewer-only root contract flow emitted removed Product Officer card",
    "child_approval_without_reviewer": "PM approved child-skill manifest before Reviewer pass",
    "child_approval_waits_for_process_officer": "Reviewer-only child-skill flow still required Process Officer",
    "child_approval_waits_for_product_officer": "Reviewer-only child-skill flow still required Product Officer",
    "child_approval_requires_process_officer_artifact": "child-skill approval still required Process Officer artifact",
    "child_approval_requires_product_officer_artifact": "child-skill approval still required Product Officer artifact",
    "child_process_officer_card_emitted": "Reviewer-only child-skill flow emitted removed Process Officer card",
    "child_product_officer_card_emitted": "Reviewer-only child-skill flow emitted removed Product Officer card",
    "root_reviewer_omits_verifiability": "Reviewer root contract pass omitted verifiability/testability check",
    "root_reviewer_omits_proof_obligations": "Reviewer root contract pass omitted proof obligation check",
    "child_reviewer_omits_skill_standards": "Reviewer child-skill pass omitted skill standard contract check",
    "child_reviewer_omits_evidence_obligations": "Reviewer child-skill pass omitted evidence obligation check",
    "pm_consultation_tail_required": "PM consultation was reintroduced as a required gate tail",
    "role_body_boundary_broken": "Reviewer-only gate simplification broke role/body boundary isolation",
    "legacy_officer_event_handlers_removed": "Reviewer-only gate simplification removed legacy officer event compatibility",
    "route_ready_without_root_freeze": "route became ready before PM froze root contract",
    "route_ready_without_child_manifest_approval": "route became ready before PM approved child-skill manifest",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|root={state.pm_root_contract_written},"
        f"{state.root_reviewer_card_emitted},{state.root_reviewer_passed},"
        f"{state.pm_root_contract_frozen}|root_officer="
        f"{state.root_product_officer_card_emitted},{state.root_product_officer_required},"
        f"{state.root_product_officer_artifact_required_for_freeze},"
        f"{state.root_product_officer_passed}|child={state.pm_child_manifest_written},"
        f"{state.child_reviewer_card_emitted},{state.child_reviewer_passed},"
        f"{state.pm_child_manifest_approved}|child_officers="
        f"{state.child_process_officer_card_emitted},{state.child_process_officer_required},"
        f"{state.child_process_officer_artifact_required_for_approval},"
        f"{state.child_process_officer_passed},{state.child_product_officer_card_emitted},"
        f"{state.child_product_officer_required},"
        f"{state.child_product_officer_artifact_required_for_approval},"
        f"{state.child_product_officer_passed}|"
        f"reviewer_root={state.reviewer_root_checks_user_requirements},"
        f"{state.reviewer_root_checks_verifiability},"
        f"{state.reviewer_root_checks_proof_obligations},"
        f"{state.reviewer_root_checks_scenario_coverage},"
        f"{state.reviewer_root_rejects_report_only_closure}|"
        f"reviewer_child={state.reviewer_child_checks_skill_standards},"
        f"{state.reviewer_child_checks_evidence_obligations},"
        f"{state.reviewer_child_checks_approvers},"
        f"{state.reviewer_child_checks_skipped_steps},"
        f"{state.reviewer_child_rejects_self_approval}|consult="
        f"{state.pm_consultation_used},{state.pm_consultation_required_for_gate}|"
        f"compat={state.role_body_boundary_preserved},{state.legacy_officer_events_preserved}|"
        f"route={state.route_ready}"
    )


def _build_graph() -> dict[str, object]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states: list[model.State] = [initial]
    index = {initial: 0}
    edges: list[list[tuple[str, int]]] = [[]]
    labels: set[str] = set()
    invariant_failures: list[dict[str, object]] = []

    while queue:
        state = queue.popleft()
        source = index[state]
        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})
        for transition in model.next_safe_states(state):
            labels.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(states)
                states.append(transition.state)
                edges.append([])
                queue.append(transition.state)
            edges[source].append((transition.label, index[transition.state]))

    return {
        "states": states,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _safe_graph_report(graph: dict[str, object]) -> dict[str, object]:
    missing_labels = sorted(set(REQUIRED_LABELS) - set(graph["labels"]))
    target_failures = model.invariant_failures(model.target_reviewer_only_state())
    return {
        "ok": not graph["invariant_failures"] and not missing_labels and not target_failures,
        "state_count": len(graph["states"]),
        "edge_count": graph["edge_count"],
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"],
        "target_plan_failures": target_failures,
    }


def _progress_report(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
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
        if idx not in terminal and not edges[idx]
    ]
    return {
        "ok": bool(success) and not stuck and 0 in can_reach_success,
        "success_state_count": len(success),
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "initial_can_reach_success": 0 in can_reach_success,
    }


def _flowguard_report() -> dict[str, object]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
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


def _check_hazards() -> dict[str, object]:
    hazards: dict[str, object] = {}
    ok = True
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": failures,
            "state": state.__dict__,
        }
        ok = ok and detected
    return {"ok": ok, "hazards": hazards}


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _check_hazards()
    target_state = model.target_reviewer_only_state()
    target_plan = {
        "ok": not model.invariant_failures(target_state),
        "state": target_state.__dict__,
        "failures": model.invariant_failures(target_state),
    }
    return {
        "ok": bool(safe_graph["ok"])
        and bool(progress["ok"])
        and bool(explorer["ok"])
        and bool(hazards["ok"])
        and bool(target_plan["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "target_reviewer_only_plan": target_plan,
        "optimization_plan": model.optimization_plan(),
    }


def main() -> int:
    result = run_checks()
    RESULTS_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
