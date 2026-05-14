"""Run checks for the FlowPilot parallel packet batch model."""

from __future__ import annotations

import argparse
import json
from collections import deque

from flowguard import Explorer

import flowpilot_parallel_packet_batch_model as model


REQUIRED_LABELS = (
    "register_parallel_packet_batch",
    "relay_every_batch_packet",
    "record_one_batch_result_without_join",
    "continue_non_dependent_action_during_partial_batch_wait",
    "wait_for_all_batch_results",
    "review_full_batch",
    "pm_absorbs_reviewed_batch",
    "advance_after_batch_join_review_and_pm_absorption",
)

HAZARD_EXPECTED_FAILURES = {
    "advance_after_first_result": "route stage advanced before full batch join, review, and PM absorption",
    "partial_review_pass": "reviewer passed batch without reviewing every packet result",
    "busy_role_overload": "router assigned a second open packet to a busy role",
    "duplicate_packet_or_batch": "duplicate active batch or batch id was accepted",
    "old_single_packet_bypass": "old single-packet path bypassed the batch index",
    "officer_result_not_joined": "officer packet result was not counted in the batch join",
    "controller_reads_body": "Controller read sealed body or lost envelope-only boundary",
    "blocked_packet_passed": "batch passed even though at least one packet was blocked",
    "repair_lineage_lost": "replacement batch lost parent batch or packet lineage",
    "prompt_runtime_drift": "prompt advertises batch parallelism but runtime remains single active request",
    "static_event_producer_wait": "dynamic batch wait rejected a valid remaining event producer role",
    "partial_result_without_member_status": "partial batch result was recorded without member-level status tracking",
    "partial_result_count_not_reflected": "partial batch result was not reflected in member returned count",
    "partial_result_hidden_from_status": "partial batch result was hidden from status accounting",
    "partial_missing_role_summary_stale": "partial batch missing-role summary was stale",
    "non_dependent_continuation_depends_on_missing_blocker": "non-dependent batch continuation depended on a missing blocking result",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|registered={state.batch_registered}|"
        f"packets={state.packet_count}|relay={state.packets_relayed}|"
        f"results={state.results_returned}|partial={state.partial_result_recorded},"
        f"{state.partial_result_count},{state.partial_result_visible_to_status},"
        f"{state.missing_role_summary_valid}|joined={state.batch_joined}|"
        f"review={state.batch_review_done},{state.reviewed_packet_count},{state.batch_review_passed}|"
        f"pm={state.pm_absorbed_batch}|advanced={state.stage_advanced}|"
        f"officer_join={state.officer_packets_counted_in_join}|"
        f"nondep={state.non_dependent_action_executed},"
        f"{state.non_dependent_action_depends_on_missing_blocker}|"
        f"dynamic_wait={state.dynamic_wait_producer_binding_valid}|"
        f"overload={state.role_overload_accepted}|old={state.old_single_packet_bypass_used}|"
        f"body={state.controller_read_sealed_body}|drift={state.prompt_advertises_batch},{state.runtime_supports_batch}"
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
    args = parser.parse_args()
    report = run_checks()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "flowpilot parallel packet batch checks: "
            f"{'ok' if report['ok'] else 'FAILED'} "
            f"states={report['safe_graph']['state_count']} "
            f"edges={report['safe_graph']['edge_count']}"
        )
        if not report["ok"]:
            print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
