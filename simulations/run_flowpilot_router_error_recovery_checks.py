"""Run FlowGuard checks for the FlowPilot RouterError recovery model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_router_error_recovery_model as model


REQUIRED_LABELS = {
    "role_output_reaches_router_control_blocker_case",
    "router_rejects_event_and_writes_control_blocker",
    "runtime_returns_blocked_result_with_router_next_action",
    "controller_applies_router_next_action_and_waits_for_target_role",
    "role_output_reaches_router_plain_error_case",
    "router_rejects_event_without_control_blocker",
}

HAZARD_EXPECTED_FAILURES = {
    "control_blocker_error_broke_controller_chain": "control blocker RouterError broke controller chain instead of returning Router next_action",
    "blocked_result_missing_control_blocker": "blocked runtime result omitted control_blocker metadata",
    "blocked_result_missing_next_action": "blocked runtime result omitted Router-supplied next_action",
    "runtime_hardcoded_pm_instead_of_router_next_action": "blocked runtime result omitted Router-supplied next_action",
    "plain_router_error_swallowed": "plain RouterError was swallowed as a successful blocked result",
    "rejected_event_marked_accepted": "rejected role event was marked accepted",
    "controller_self_repairs_control_blocker": "Controller attempted to self-repair a control blocker",
    "controller_reads_sealed_blocker_body": "Controller read sealed control blocker body",
    "duplicate_blocker_written_during_recovery": "runtime recovery created duplicate control blockers",
}

TERMINAL_STATUSES = {"waiting_for_role", "plain_error_failed"}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|scenario={state.scenario}|err={state.router_error_kind}|"
        f"submitted={state.role_output_submitted}|rejected={state.router_rejected_event}|"
        f"blocker={state.control_blocker_written},{state.control_blocker_count}|"
        f"runtime={state.runtime_exit_code},{state.runtime_returned_blocked_result},"
        f"{state.runtime_returned_control_blocker},{state.runtime_requested_router_next_action}|"
        f"next={state.next_action_source},{state.next_action_type},{state.next_action_target_role}|"
        f"controller={state.controller_applied_next_action},{state.pm_or_target_role_wait_exposed}|"
        f"bad={state.chain_broken},{state.heartbeat_required_for_recovery},"
        f"{state.non_control_error_swallowed},{state.controller_self_repaired},"
        f"{state.controller_read_sealed_body},{state.original_event_accepted},"
        f"{state.original_event_retried_by_controller},{state.runtime_hardcoded_pm_target}"
    )


def _build_graph() -> dict[str, object]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states: list[model.State] = [initial]
    index = {initial: 0}
    edges: list[list[tuple[str, int]]] = []
    labels: set[str] = set()
    invariant_failures: list[dict[str, object]] = []

    while queue:
        state = queue.popleft()
        source = index[state]
        while len(edges) <= source:
            edges.append([])
        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})
        for label, new_state in model.next_states(state):
            labels.add(label)
            if new_state not in index:
                index[new_state] = len(states)
                states.append(new_state)
                queue.append(new_state)
            edges[source].append((label, index[new_state]))

    stuck_states = [
        _state_id(state)
        for state, state_index in index.items()
        if not edges[state_index]
        and state.status not in TERMINAL_STATUSES
        and not model.invariant_failures(state)
    ]
    missing_labels = sorted(REQUIRED_LABELS - labels)
    return {
        "state_count": len(states),
        "edge_count": sum(len(item) for item in edges),
        "labels": sorted(labels),
        "missing_required_labels": missing_labels,
        "invariant_failures": invariant_failures,
        "stuck_states": stuck_states,
    }


def _check_hazards() -> list[dict[str, object]]:
    misses: list[dict[str, object]] = []
    hazards = model.hazard_states()
    for name, expected in HAZARD_EXPECTED_FAILURES.items():
        failures = model.invariant_failures(hazards[name])
        if expected not in failures:
            misses.append({"hazard": name, "expected": expected, "actual_failures": failures})
    return misses


def run_checks() -> dict[str, object]:
    # Keep a real FlowGuard exploration in the check path; the explicit graph
    # builder gives stable project-specific hazard reporting.
    flowguard_report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=model.terminal_predicate,
        success_predicate=lambda state, _trace: model.is_success(state),
        required_labels=REQUIRED_LABELS,
        progress_steps=0,
    ).explore()
    graph = _build_graph()
    hazard_misses = _check_hazards()
    passed = not (
        not flowguard_report.ok
        or graph["missing_required_labels"]
        or graph["invariant_failures"]
        or graph["stuck_states"]
        or hazard_misses
    )
    return {
        "passed": passed,
        "workflow": "flowpilot_router_error_recovery",
        "flowguard": {
            "ok": flowguard_report.ok,
            "summary": flowguard_report.summary,
            "violation_count": len(flowguard_report.violations),
            "dead_branch_count": len(flowguard_report.dead_branches),
            "exception_branch_count": len(flowguard_report.exception_branches),
            "reachability_failure_count": len(flowguard_report.reachability_failures),
            "reachability_failures": [failure.message for failure in flowguard_report.reachability_failures],
        },
        "graph": graph,
        "hazard_misses": hazard_misses,
        "hazard_expected_failures": HAZARD_EXPECTED_FAILURES,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", default="")
    args = parser.parse_args()

    result = run_checks()
    text = json.dumps(result, indent=2, sort_keys=True)
    print(text)
    if args.json_out:
        path = Path(args.json_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
