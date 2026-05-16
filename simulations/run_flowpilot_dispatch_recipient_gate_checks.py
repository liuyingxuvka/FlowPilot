"""Run checks for the FlowPilot dispatch recipient gate model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_dispatch_recipient_gate_model as model


REQUIRED_LABELS = (
    "dispatch_idle_work_packet",
    "wait_for_busy_active_packet_before_dispatch",
    "wait_for_missing_ack_before_formal_packet",
    "wait_for_passive_role_result_before_dispatch",
    "allow_user_intake_mail_after_resolved_startup_card_wait",
    "allow_pm_mail_after_resolved_role_output_wait",
    "allow_ack_only_prompt_while_packet_active",
    "wait_for_pending_pm_output_before_independent_output_card",
    "allow_event_card_for_same_pending_pm_output",
    "allow_system_card_for_active_obligation",
    "wait_for_user_intake_first_output_before_independent_pm_card",
    "allow_pm_dispatch_after_user_intake_first_output",
    "allow_same_role_system_card_bundle",
    "allow_different_idle_roles_parallel",
    "block_duplicate_same_role_batch",
    "block_illegal_packet_even_when_idle",
    "allow_worker_after_role_work_result_returned",
    "wait_for_pm_disposition_before_new_pm_dispatch",
)

HAZARD_EXPECTED_FAILURES = {
    "busy_active_packet_dispatch_exposed": "busy target role received a second independent dispatch",
    "missing_ack_dispatch_exposed": "busy target role received a second independent dispatch",
    "passive_wait_dispatch_exposed": "busy target role received a second independent dispatch",
    "stale_card_ack_passive_wait_blocks_user_intake": "resolved passive wait did not free the target role",
    "stale_role_output_passive_wait_blocks_pm_mail": "resolved passive wait did not free the target role",
    "busy_wait_without_concrete_obligation": "busy-recipient wait did not name a concrete blocking obligation",
    "ack_only_prompt_blocked_as_work": "ACK-only prompt card was treated as independent work",
    "independent_output_card_exposed_while_pm_output_pending": "busy target role received a second independent dispatch",
    "same_output_context_card_blocked": "same-output event/context card was blocked",
    "duplicate_same_role_batch_exposed": "same batch assigned two independent open packets to one role",
    "illegal_packet_exposed": "illegal packet or target dispatch was exposed",
    "same_role_bundle_rejected": "same-role system-card bundle was rejected instead of treated as one grouped delivery",
    "system_card_for_active_holder_blocked": "same-obligation instruction card was blocked",
    "independent_pm_card_exposed_while_user_intake_active": "busy target role received a second independent dispatch",
    "user_intake_first_output_still_blocks_pm": "prior packet completion did not free the target role",
    "different_idle_parallel_blocked": "different idle roles were blocked from parallel dispatch",
    "returned_worker_result_still_blocks_worker": "returned role-work result did not free the original target role",
    "pm_dispatch_exposed_before_disposition": "PM received a new dispatch while prior result disposition was pending",
    "wait_leaks_sealed_body": "busy-recipient wait exposed sealed body content",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|kind={state.candidate_kind}|target={state.target_role}|"
        f"legal={state.target_identity_valid},{state.packet_legal},{state.active_holder_legal}|"
        f"group={state.same_role_grouped_delivery}|parallel={state.parallel_roles_unique},"
        f"{state.different_idle_roles_parallel}|output={state.candidate_output_bearing}|"
        f"busy={state.unresolved_ack_for_target},"
        f"{state.passive_wait_for_target},{state.passive_wait_source},"
        f"{state.passive_wait_durable_status},{state.pending_expected_output_for_target},"
        f"{state.same_output_context_card},{state.active_packet_held_by_target},"
        f"{state.same_obligation_instruction},{state.prior_packet_completed_by_flow_state},"
        f"{state.pm_role_work_status_for_target},{state.pm_disposition_pending}|"
        f"out={state.dispatch_exposed},{state.wait_exposed},{state.block_exposed}|"
        f"wait={state.wait_target_role},{state.wait_source_named},"
        f"{state.wait_obligation_identity_present},{state.sealed_body_exposed_in_wait}"
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
    return {
        "ok": not graph["invariant_failures"] and not missing_labels,
        "state_count": len(graph["states"]),
        "edge_count": graph["edge_count"],
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"],
    }


def _progress_report(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    success = {idx for idx, state in enumerate(states) if model.is_success(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for idx, outgoing in enumerate(edges):
            if idx not in can_reach_terminal and any(target in can_reach_terminal for _label, target in outgoing):
                can_reach_terminal.add(idx)
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
        "ok": bool(success) and not stuck and not cannot_reach_terminal and 0 in can_reach_terminal,
        "success_state_count": len(success),
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "cannot_reach_terminal_samples": cannot_reach_terminal[:10],
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


def _implementation_plan_report() -> dict[str, object]:
    state = model.implementation_plan_state()
    failures = model.invariant_failures(state)
    return {
        "ok": not failures,
        "state": state.__dict__,
        "failures": failures,
    }


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _check_hazards()
    implementation_plan = _implementation_plan_report()
    return {
        "ok": (
            safe_graph["ok"]
            and progress["ok"]
            and explorer["ok"]
            and hazards["ok"]
            and implementation_plan["ok"]
        ),
        "safe_graph": safe_graph,
        "progress": progress,
        "explorer": explorer,
        "hazards": hazards,
        "implementation_plan": implementation_plan,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print the full JSON report.")
    parser.add_argument("--json-out", type=Path, help="Write the full JSON report to this path.")
    args = parser.parse_args()
    report = run_checks()
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(payload, encoding="utf-8")
    if args.json:
        print(payload, end="")
    else:
        print(
            "flowpilot dispatch recipient gate checks: "
            f"{'ok' if report['ok'] else 'FAILED'} "
            f"states={report['safe_graph']['state_count']} "
            f"edges={report['safe_graph']['edge_count']}"
        )
        if not report["ok"]:
            print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
