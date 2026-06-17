"""Run FlowPilot FlowGuard work-order role-chain checks."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Sequence

from flowguard.explorer import Explorer

import flowpilot_flowguard_work_order_model as model


RESULTS_PATH = Path(__file__).resolve().with_name(
    "flowpilot_flowguard_work_order_results.json"
)

REQUIRED_LABELS = (
    "flowguard_work_order_run_started",
    "pm_writes_flowguard_work_order",
    "flowguard_operator_returns_current_flowguard_report",
    "pm_accepts_flowguard_report",
    "pm_assigns_packet_scoped_flowguard_obligations",
    "worker_returns_flowguard_obligation_coverage",
    "reviewer_checks_flowguard_report_support",
    "reviewer_passes_flowguard_backed_gate",
    "controller_surfaces_flowguard_status_only",
    "pm_approves_closure_after_report_chain",
    "flowguard_work_order_flow_complete",
)

HAZARD_EXPECTED_FAILURES = {
    "missing_work_order": "PM made a non-trivial decision without a FlowGuard Work Order",
    "missing_report": "PM made a non-trivial decision without a FlowGuard Report",
    "stale_report": "PM accepted a stale FlowGuard report",
    "wrong_scope_report": "PM accepted a wrongly scoped FlowGuard report",
    "progress_only_report": "PM accepted progress-only FlowGuard evidence",
    "skipped_checks_not_dispositioned": "PM accepted skipped FlowGuard checks without disposition",
    "unaccepted_report": "Reviewer passed before PM accepted the FlowGuard report",
    "flowguard_operator_gate_approval": "FlowGuard operator used FlowGuard report to approve a gate",
    "flowguard_operator_route_mutation": "FlowGuard operator used FlowGuard report to mutate the route",
    "reviewer_bypasses_report_check": "Reviewer passed a FlowGuard-backed gate without checking the report",
    "reviewer_reruns_without_pm_route": "Reviewer reran FlowGuard modeling without PM-routed work authority",
    "worker_route_mutation": "Worker used FlowGuard obligation coverage to mutate the route",
    "worker_waives_report_gap": "Worker waived a FlowGuard report gap",
    "controller_interprets_report": "Controller interpreted FlowGuard report contents",
    "controller_gate_approval": "Controller approved a gate from FlowGuard status",
    "closure_before_reviewer_pass": "PM closure approved before Reviewer passed the FlowGuard-backed gate",
    "not_required_used_for_nontrivial": "PM used flowguard_not_required_reason for non-trivial judgement",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|nontrivial={state.nontrivial_judgement}|"
        f"pm={state.pm_work_order_written},{state.pm_decision_made},"
        f"{state.flowguard_not_required_reason}|"
        f"report={state.report_returned},{state.report_scope_matches},"
        f"{state.report_current},{state.report_skipped_checks_dispositioned},"
        f"{state.report_progress_only},{state.report_pm_accepted}|"
        f"FlowGuard operator={state.flowguard_operator_answered_work_order},{state.flowguard_operator_approved_gate},"
        f"{state.flowguard_operator_mutated_route}|worker={state.worker_obligations_assigned},"
        f"{state.worker_returned_packet_scoped_coverage},{state.worker_mutated_route},"
        f"{state.worker_waived_report_gap}|reviewer={state.reviewer_checked_report},"
        f"{state.reviewer_passed_gate},{state.reviewer_reran_model_without_pm_route}|"
        f"controller={state.controller_surfaced_status},{state.controller_interpreted_report},"
        f"{state.controller_approved_gate}|closure={state.terminal_closure_approved}"
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
    target_failures = model.invariant_failures(model.target_success_state())
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
    target_state = model.target_success_state()
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
        "target_flowguard_work_order_plan": target_plan,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args(argv)

    result = run_checks()
    if args.json_out:
        args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
