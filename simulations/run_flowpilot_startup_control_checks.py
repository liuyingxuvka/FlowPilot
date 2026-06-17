"""Run checks for the current FlowPilot startup-control model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard.explorer import Explorer

import flowpilot_startup_control_model as model


RESULTS_PATH = Path(__file__).resolve().parent / "flowpilot_startup_control_results.json"

EXPECTED_HAZARD_FAILURES = {
    "legacy_reviewer_startup_fact_gate": "legacy reviewer startup fact gate was used",
    "legacy_pm_startup_activation_gate": "legacy PM startup activation gate was used",
    "legacy_heartbeat_created": "legacy heartbeat continuation was created",
    "fixed_role_slots_started": "fixed startup role slots were started",
    "reviewer_mechanical_fact_reproof": "reviewer was asked to re-prove runtime/router mechanical facts",
    "work_without_background_agent": "role work started without current background agent opening",
    "material_card_before_user_intake": "material scan started before current PM entry and on-demand background agent opening",
    "route_activation_before_current_entry": "route was activated before first PM work entry",
    "next_action_before_active_route": "next action was issued before active route",
    "completion_before_pm_closure": "startup control completed before route work, PM closure, and lifecycle close",
    "next_action_after_stop": "action was issued after formal lifecycle stop/cancel",
    "unsealed_repair_packet": "router repair packet was routed without being sealed",
    "repair_packet_to_controller": "router repair packet was routed to controller",
    "controller_knows_repair_details": "Controller learned sealed repair details",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|holder={state.holder}|"
        f"intake={state.startup_intake_ui_completed}|user={state.user_text_recorded}|"
        f"contract={state.startup_task_contract_recorded}|core={state.controller_core_loaded}|"
        f"boundary={state.controller_boundary_evidence_written}|audit={state.startup_mechanical_audit_written}|"
        f"display={state.startup_display_status_written}|mail={state.user_intake_delivered_to_pm}|"
        f"pm_ack={state.pm_startup_intake_ack_clean}|agent={state.current_role_agent_opened_on_demand}|"
        f"material={state.material_scan_card_delivered}|route={state.active_route_exists}|"
        f"next={state.next_action_issued}|work={state.route_work_completed}|closure={state.pm_closure_approved}|"
        f"lifecycle={state.lifecycle_continuation_closed}|signal={state.formal_lifecycle_signal}|"
        f"legacy={state.reviewer_startup_fact_gate_used},{state.pm_startup_activation_gate_used},"
        f"{state.legacy_heartbeat_created},{state.fixed_role_slots_started}|"
        f"repair={state.router_error_seen},{state.repair_packet_registered},{state.repair_packet_sealed},"
        f"{state.repair_packet_recipient},{state.repair_result_returned_to_router},{state.router_recovered_after_repair}"
    )


def _build_graph() -> dict[str, object]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states: list[model.State] = [initial]
    index = {initial: 0}
    labels: set[str] = set()
    edges: list[list[tuple[str, int, str]]] = []
    invariant_failures: list[dict[str, object]] = []

    while queue:
        state = queue.popleft()
        source = index[state]
        while len(edges) <= source:
            edges.append([])
        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})
        for transition in model.next_safe_states(state):
            labels.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(states)
                states.append(transition.state)
                queue.append(transition.state)
            edges[source].append((transition.label, index[transition.state], transition.recipient))

    return {
        "states": states,
        "edges": edges,
        "labels": labels,
        "invariant_failures": invariant_failures,
        "edge_count": sum(len(row) for row in edges),
    }


def _progress_report(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int, str]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for idx, outgoing in enumerate(edges):
            if idx not in can_reach_terminal and any(target in can_reach_terminal for _label, target, _recipient in outgoing):
                can_reach_terminal.add(idx)
                changed = True
    stuck = [_state_id(state) for idx, state in enumerate(states) if idx not in terminal and not edges[idx]]
    cannot_reach_terminal = [_state_id(state) for idx, state in enumerate(states) if idx not in can_reach_terminal]
    return {
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_terminal,
        "initial_can_reach_terminal": 0 in can_reach_terminal,
        "initial_can_reach_success": any(model.is_success(state) for state in states),
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "cannot_reach_terminal_samples": cannot_reach_terminal[:10],
    }


def _check_hazards() -> dict[str, object]:
    hazards: dict[str, object] = {}
    ok = True
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        expected = EXPECTED_HAZARD_FAILURES[name]
        detected = any(expected in failure for failure in failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": failures,
            "state": state.__dict__,
        }
        ok = ok and detected
    return {"ok": ok, "hazards": hazards}


def _flowguard_report() -> dict[str, object]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=lambda _input, state, _trace: model.is_terminal(state),
        success_predicate=lambda state, _trace: model.is_success(state),
        required_labels=model.REQUIRED_LABELS,
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


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    labels = set(graph["labels"])
    missing_labels = sorted(set(model.REQUIRED_LABELS) - labels)
    progress = _progress_report(graph)
    hazards = _check_hazards()
    flowguard = _flowguard_report()
    safe_graph = {
        "ok": not graph["invariant_failures"] and not missing_labels,
        "state_count": len(graph["states"]),
        "edge_count": graph["edge_count"],
        "labels": sorted(labels),
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"],
        "complete_state_count": sum(1 for state in graph["states"] if state.status == "complete"),
        "stopped_state_count": sum(1 for state in graph["states"] if state.status == "stopped"),
        "cancelled_state_count": sum(1 for state in graph["states"] if state.status == "cancelled"),
    }
    result = {
        "ok": bool(safe_graph["ok"] and progress["ok"] and hazards["ok"] and flowguard["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "hazard_checks": hazards,
        "flowguard_explorer": flowguard,
        "skipped_checks": {
            "conformance_replay": "skipped_with_reason: abstract startup-control model; production coverage comes from router startup runtime tests"
        },
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args()
    result = run_checks()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
