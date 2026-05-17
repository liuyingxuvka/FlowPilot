"""Executable FlowGuard checks for FlowPilot slow-test contracts."""

from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from flowguard import Explorer

import flowpilot_slow_test_contract_model as model


RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_slow_test_contract_results.json")

REQUIRED_LABELS = {
    "select_valid_route_mutation_parent_contract",
    "accept_valid_route_mutation_parent_contract",
    "select_valid_release_with_child_oracle",
    "accept_valid_release_with_child_oracle",
    "reject_missing_child_contract",
    "reject_missing_child_owner",
    "reject_duplicate_state_owner",
    "reject_unbound_input_contract",
    "reject_unbound_output_contract",
    "reject_parent_replays_child_boot",
    "reject_parent_replays_packet_worker_flow",
    "reject_parent_reads_child_internal_state",
    "reject_missing_legal_route_action_state",
    "reject_parent_owns_no_mutation_outputs",
    "reject_stale_child_evidence",
    "reject_hidden_child_skip",
    "reject_release_oracle_hidden",
    "reject_release_oracle_stale",
}

EXPECTED_HAZARD_FAILURES = {
    "missing_child_contract": {"child_contract_missing"},
    "missing_child_owner": {"child_owner_missing"},
    "duplicate_state_owner": {"duplicate_state_owner"},
    "unbound_input_contract": {"input_contract_unbound"},
    "unbound_output_contract": {"output_contract_unbound"},
    "parent_replays_child_boot": {"parent_replays_child_boot"},
    "parent_replays_packet_worker_flow": {"parent_replays_packet_worker_flow"},
    "parent_reads_child_internal_state": {"parent_reads_child_internal_state"},
    "missing_legal_route_action_state": {"legal_route_action_state_missing"},
    "parent_owns_no_mutation_outputs": {"parent_mutation_output_owner_missing"},
    "stale_child_evidence": {"child_evidence_stale"},
    "hidden_child_skip": {"hidden_child_skip"},
    "release_oracle_hidden": {
        "release_child_oracle_hidden",
        "release_child_oracle_not_current",
    },
    "release_oracle_stale": {"release_child_oracle_not_current"},
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|family={state.test_family}|"
        f"layers={state.parent_layer_declared},{state.child_contract_declared},"
        f"{state.child_owner_registered},{state.duplicate_state_owner}|"
        f"io={state.input_contract_bound},{state.output_contract_bound}|"
        f"child={state.child_evidence_current},{state.hidden_child_skip}|"
        f"parent={state.parent_only_calls_parent_event},"
        f"{state.parent_replays_child_boot},{state.parent_replays_packet_worker_flow},"
        f"{state.parent_reads_child_internal_state}|"
        f"route={state.legal_route_action_state_provided},"
        f"{state.mutation_outputs_owned_by_parent}|"
        f"release={state.release_scope},{state.release_oracle_visible},"
        f"{state.release_oracle_current}"
    )


def _walk_graph() -> dict[str, Any]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states: list[model.State] = [initial]
    index = {initial: 0}
    edges: list[list[tuple[str, int]]] = []
    labels_seen: set[str] = set()
    violations: list[dict[str, Any]] = []

    while queue:
        state = queue.popleft()
        source = index[state]
        while len(edges) <= source:
            edges.append([])
        failures = model.invariant_failures(state)
        if failures:
            violations.append({"state": _state_id(state), "failures": failures})
        for transition in model.next_safe_states(state):
            labels_seen.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(states)
                states.append(transition.state)
                queue.append(transition.state)
            edges[source].append((transition.label, index[transition.state]))

    return {
        "ok": not violations and not (REQUIRED_LABELS - labels_seen),
        "states": states,
        "edges": edges,
        "state_count": len(states),
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "terminal_state_count": sum(1 for state in states if model.is_terminal(state)),
        "accepted_state_count": sum(1 for state in states if state.status == "accepted"),
        "rejected_state_count": sum(1 for state in states if state.status == "rejected"),
        "labels_seen": sorted(labels_seen),
        "missing_labels": sorted(REQUIRED_LABELS - labels_seen),
        "violations": violations,
    }


def _progress_report(graph: Mapping[str, Any]) -> dict[str, Any]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for idx, outgoing in enumerate(edges):
            if idx not in can_reach_terminal and any(
                target in can_reach_terminal for _label, target in outgoing
            ):
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
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_terminal,
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "cannot_reach_terminal_samples": cannot_reach_terminal[:10],
    }


def _flowguard_report() -> dict[str, Any]:
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


def _terminal_state_for(name: str) -> model.State:
    selected = None
    for transition in model.next_safe_states(model.initial_state()):
        if transition.label == f"select_{name}":
            selected = transition.state
            break
    if selected is None:
        raise AssertionError(f"scenario was not selectable: {name}")
    terminals = list(model.next_safe_states(selected))
    if len(terminals) != 1:
        raise AssertionError(f"scenario did not have exactly one terminal transition: {name}")
    return terminals[0].state


def _scenario_review() -> dict[str, Any]:
    valid: list[str] = []
    rejected: list[str] = []
    bad_accepts: list[dict[str, Any]] = []
    bad_rejects: list[dict[str, Any]] = []

    for name in sorted(model.VALID_SCENARIOS):
        terminal = _terminal_state_for(name)
        if terminal.status == "accepted":
            valid.append(name)
        else:
            bad_rejects.append(
                {
                    "scenario": name,
                    "status": terminal.status,
                    "failures": model.contract_failures(terminal),
                }
            )

    for name in sorted(model.NEGATIVE_SCENARIOS):
        terminal = _terminal_state_for(name)
        failures = set(model.contract_failures(terminal))
        expected = EXPECTED_HAZARD_FAILURES[name]
        if terminal.status == "rejected" and expected <= failures:
            rejected.append(name)
        else:
            bad_accepts.append(
                {
                    "scenario": name,
                    "status": terminal.status,
                    "expected": sorted(expected),
                    "actual": sorted(failures),
                }
            )

    return {
        "ok": not bad_accepts and not bad_rejects,
        "valid_scenarios_accepted": valid,
        "hazard_scenarios_rejected": rejected,
        "bad_accepts": bad_accepts,
        "bad_rejects": bad_rejects,
    }


def _graph_for_output(graph: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in graph.items()
        if key not in {"states", "edges"}
    }


def build_report() -> dict[str, Any]:
    graph = _walk_graph()
    progress = _progress_report(graph)
    flowguard = _flowguard_report()
    scenarios = _scenario_review()
    ok = graph["ok"] and progress["ok"] and flowguard["ok"] and scenarios["ok"]
    return {
        "ok": ok,
        "model": "flowpilot_slow_test_contract",
        "result_type": "test_mesh_contract",
        "contract_family": "route_mutation",
        "graph": _graph_for_output(graph),
        "progress": progress,
        "flowguard_explorer": flowguard,
        "scenario_review": scenarios,
        "expected_hazard_failures": {
            key: sorted(value) for key, value in sorted(EXPECTED_HAZARD_FAILURES.items())
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)

    result = build_report()
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    output_path = args.json_out
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
