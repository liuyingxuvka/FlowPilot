"""Run checks for the FlowPilot startup-control model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_startup_control_model as model


HAZARD_EXPECTED_FAILURES = {
    "apply_without_receipt_review": "startup action was applied before reviewed answer receipt matched user text",
    "apply_without_payload_contract": "startup action was applied before an action payload contract existed",
    "fact_report_pass_before_apply": "reviewer startup fact report was written before startup action apply",
    "blocking_fact_report_allows_work": "reviewer startup fact report blocked but work beyond startup was allowed",
    "next_action_after_stop": "formal user stop/cancel did not prevent further next actions",
    "next_action_after_cancel": "formal user stop/cancel did not prevent further next actions",
    "unsealed_repair_packet": "router error repair packet was routed without being sealed",
    "repair_packet_to_controller": "router error repair packet was not routed to the responsible role",
    "controller_knows_repair_details": "Controller learned sealed router repair details",
    "router_error_complete_without_repair": "startup control completed after router error without responsible repair recovery",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|holder={state.holder}|"
        f"questions={state.startup_questions_asked}|waiting={state.waiting_for_user_text}|"
        f"user_text={state.user_text_recorded}|lifecycle={state.formal_lifecycle_signal}|"
        f"future_prevented={state.future_actions_prevented}|"
        f"issued_after_lifecycle={state.action_issued_after_lifecycle_signal}|"
        f"receipt={state.interpretation_receipt_written},"
        f"{state.receipt_reviewed_against_user_text},{state.receipt_matches_user_text}|"
        f"action={state.pending_action_type},contract={state.payload_contract_exists},"
        f"applied={state.startup_action_applied}|"
        f"fact_report={state.startup_fact_report_status},"
        f"file={state.startup_fact_report_file_backed}|"
        f"work={state.work_beyond_startup_allowed}|next={state.next_action_issued}|"
        f"error={state.router_error_seen}|repair="
        f"{state.repair_packet_registered},{state.repair_packet_sealed},"
        f"{state.repair_packet_responsible_role}->{state.repair_packet_recipient},"
        f"routed={state.repair_packet_routed_to_role}|"
        f"ctrl_detail={state.controller_knows_repair_details},"
        f"{state.controller_relayed_repair_details},"
        f"{state.repair_result_body_read_by_controller}|"
        f"repair_result={state.repair_result_returned_to_router}|"
        f"recovered={state.router_recovered_after_repair}"
    )


def _build_reachable_graph() -> dict[str, object]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    seen: list[model.State] = [initial]
    index = {initial: 0}
    labels: set[str] = set()
    edges: list[list[tuple[str, int, str]]] = []
    invariant_failures: list[dict[str, object]] = []

    while queue:
        state = queue.popleft()
        source_index = index[state]
        while len(edges) <= source_index:
            edges.append([])

        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})

        for transition in model.next_safe_states(state):
            labels.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(seen)
                seen.append(transition.state)
                queue.append(transition.state)
            edges[source_index].append(
                (transition.label, index[transition.state], transition.recipient)
            )

    return {
        "states": seen,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _safe_graph_report(graph: dict[str, object]) -> dict[str, object]:
    labels = set(graph["labels"])
    missing_labels = sorted(set(model.REQUIRED_LABELS) - labels)
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int, str]]] = graph["edges"]
    stop_cancel_outgoing = [
        {"source": index, "state": _state_id(states[index]), "edges": outgoing}
        for index, outgoing in enumerate(edges)
        if states[index].status in {"stopped", "cancelled"} and outgoing
    ]
    missing_recipients = [
        {"source": source, "label": label, "target": target}
        for source, outgoing in enumerate(edges)
        for label, target, recipient in outgoing
        if recipient in {"", "none", "unknown"}
    ]
    repair_states = [state for state in states if state.repair_packet_routed_to_role]
    unsealed_or_wrong_repair_states = [
        _state_id(state)
        for state in repair_states
        if not (
            state.router_error_seen
            and state.repair_packet_sealed
            and state.repair_packet_responsible_role
            in model.RESPONSIBLE_REPAIR_ROLES
            and state.repair_packet_recipient == state.repair_packet_responsible_role
            and not state.controller_knows_repair_details
            and not state.controller_relayed_repair_details
        )
    ]
    return {
        "ok": (
            not graph["invariant_failures"]
            and not missing_labels
            and any(model.is_success(state) for state in states)
            and any(state.status == "blocked" for state in states)
            and any(state.status == "stopped" for state in states)
            and any(state.status == "cancelled" for state in states)
            and not stop_cancel_outgoing
            and not missing_recipients
            and not unsealed_or_wrong_repair_states
        ),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "labels": sorted(labels),
        "missing_labels": missing_labels,
        "complete_state_count": sum(1 for state in states if state.status == "complete"),
        "blocked_state_count": sum(1 for state in states if state.status == "blocked"),
        "stopped_state_count": sum(1 for state in states if state.status == "stopped"),
        "cancelled_state_count": sum(1 for state in states if state.status == "cancelled"),
        "stop_cancel_outgoing_edges": stop_cancel_outgoing,
        "missing_recipient_edges": missing_recipients,
        "unsealed_or_wrong_repair_states": unsealed_or_wrong_repair_states,
        "invariant_failures": graph["invariant_failures"],
    }


def _check_progress(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int, str]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    success = {idx for idx, state in enumerate(states) if model.is_success(state)}

    can_reach_terminal = set(terminal)
    can_reach_success = set(success)
    changed = True
    while changed:
        changed = False
        for source, outgoing in enumerate(edges):
            targets = [target for _label, target, _recipient in outgoing]
            if source not in can_reach_terminal and any(
                target in can_reach_terminal for target in targets
            ):
                can_reach_terminal.add(source)
                changed = True
            if source not in can_reach_success and any(target in can_reach_success for target in targets):
                can_reach_success.add(source)
                changed = True

    stuck = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in terminal and not edges[idx]
    ]
    cannot_reach_terminal = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in can_reach_terminal
    ]
    return {
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_success,
        "initial_can_reach_success": 0 in can_reach_success,
        "initial_can_reach_terminal": 0 in can_reach_terminal,
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "cannot_reach_terminal_samples": cannot_reach_terminal[:10],
    }


def _run_flowguard_explorer() -> dict[str, object]:
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
        "reachability_failures": [
            failure.message for failure in report.reachability_failures
        ],
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
    graph = _build_reachable_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _check_progress(graph)
    explorer = _run_flowguard_explorer()
    hazards = _check_hazards()
    skipped_checks = {
        "conformance_replay": (
            "skipped_with_reason: this abstract startup-control model has no "
            "production replay adapter in the allowed write set"
        )
    }
    return {
        "ok": bool(
            safe_graph["ok"]
            and progress["ok"]
            and explorer["ok"]
            and hazards["ok"]
        ),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "skipped_checks": skipped_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Optional path for writing the JSON result payload.",
    )
    args = parser.parse_args()

    result = run_checks()
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
