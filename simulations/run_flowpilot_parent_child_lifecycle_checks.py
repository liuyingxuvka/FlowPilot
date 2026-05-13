"""Run checks for the FlowPilot parent/child lifecycle model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_parent_child_lifecycle_model as model


RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_parent_child_lifecycle_results.json")

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.PARENT_TARGETS_BEFORE_CHILD_ENTRY: "parent closure action requested before child subtree entry",
    model.PARENT_REPLAY_BEFORE_CHILD_ENTRY: "parent closure action requested before child subtree entry",
    model.PARENT_SEGMENT_BEFORE_CHILD_COMPLETION: "parent closure action requested before all effective children completed",
    model.PARENT_COMPLETE_BEFORE_CHILD_COMPLETION: "parent closure action requested before all effective children completed",
    model.SIBLING_MODULE_LEAF_ENTERED_BEFORE_PARENT_REPLAY: "sibling module leaf entered before previous parent backward replay",
    model.NON_NEAREST_PARENT_SELECTED_FOR_CHILD_REPLAY: "router selected a non-nearest parent scope for child completion replay",
    model.NON_LEAF_ACCEPTANCE_STUCK_ON_PARENT: "non-leaf acceptance passed but Router did not enter a child subtree",
    model.PARENT_DISPATCHES_WORKER_PACKET: "parent or module node attempted worker packet dispatch",
    model.DIRECT_CHILD_DONE_DESCENDANT_PENDING: "direct child completion was treated as subtree completion while descendants were pending",
    model.STALE_ROUTE_STATUS_COUNTS_AS_CHILD_DONE: "stale route status was used as child completion authority",
    model.CHILD_COMPLETION_FROM_OLD_ROUTE_VERSION: "child completion ledger belongs to a stale route version",
    model.PARENT_FLAGS_LEAK_TO_CHILD: "child frontier entered without resetting parent current-node cycle flags",
    model.ABSTRACT_GREEN_WITHOUT_LIVE_ACTION_REPLAY: "abstract model green was used without live Router next-action replay",
    model.LIVE_ROUTER_ACTION_NOT_IN_MODEL: "live Router next action was not covered by the conformance model",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|kind={state.active_node_kind}|"
        f"entry={state.non_leaf_acceptance_plan_passed},{state.child_frontier_entered},{state.child_cycle_flags_reset}|"
        f"children={state.direct_children_completed},{state.descendant_leaves_completed},"
        f"{state.effective_children_all_completed},{state.child_completion_ledger_current}|"
        f"parent={state.parent_backward_targets_requested},{state.parent_backward_replay_requested},"
        f"{state.parent_segment_decision_recorded},{state.parent_completed}|"
        f"after_child={state.last_child_completion_committed},{state.parent_review_ready_after_child_completion},"
        f"{state.parent_scope_reactivated_for_replay},{state.sibling_module_leaf_entered_before_parent_replay},"
        f"{state.nearest_parent_scope_selected}|"
        f"live={state.live_router_next_action_replayed},{state.live_router_next_action_known_to_model}|"
        f"reason={state.terminal_reason}"
    )


def _build_graph() -> dict[str, Any]:
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
        for transition in model.next_safe_states(state):
            labels.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(states)
                states.append(transition.state)
                queue.append(transition.state)
            edges[source].append((transition.label, index[transition.state]))
    return {
        "states": states,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _safe_graph_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    terminal = [state for state in states if model.is_terminal(state)]
    accepted = [state for state in terminal if state.status == "accepted"]
    rejected = [state for state in terminal if state.status == "rejected"]
    missing_labels = sorted(set(REQUIRED_LABELS) - set(graph["labels"]))
    accepted_scenarios = sorted(state.scenario for state in accepted)
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and set(accepted_scenarios) == set(model.VALID_SCENARIOS)
        and len(rejected) == len(model.NEGATIVE_SCENARIOS),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "accepted_scenarios": accepted_scenarios,
        "rejected_state_count": len(rejected),
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"][:5],
    }


def _progress_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for source, outgoing in enumerate(edges):
            if source not in can_reach_terminal and any(target in can_reach_terminal for _label, target in outgoing):
                can_reach_terminal.add(source)
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
        "ok": not stuck and not cannot_reach_terminal,
        "stuck_state_count": len(stuck),
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "samples": (stuck + cannot_reach_terminal)[:5],
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


def _hazard_report() -> dict[str, object]:
    hazards: dict[str, object] = {}
    failures: list[str] = []
    for name, state in model.hazard_states().items():
        lifecycle_failures = model.lifecycle_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in lifecycle_failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": lifecycle_failures,
        }
        if not detected:
            failures.append(f"{name}: expected failure containing {expected!r}")
    return {"ok": not failures, "hazards": hazards, "failures": failures}


def _intended_report() -> dict[str, object]:
    parent_failures = model.lifecycle_failures(model.intended_parent_state())
    leaf_failures = model.lifecycle_failures(model.intended_leaf_state())
    last_child_failures = model.lifecycle_failures(model.intended_last_child_returns_to_parent_review_state())
    return {
        "ok": not parent_failures and not leaf_failures and not last_child_failures,
        "parent_failures": parent_failures,
        "leaf_failures": leaf_failures,
        "last_child_returns_to_parent_review_failures": last_child_failures,
    }


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    reports = {
        "safe_graph": _safe_graph_report(graph),
        "progress": _progress_report(graph),
        "flowguard": _flowguard_report(),
        "hazards": _hazard_report(),
        "intended": _intended_report(),
    }
    ok = all(report.get("ok") for report in reports.values())
    return {
        "ok": ok,
        "model": "flowpilot_parent_child_lifecycle",
        "covered_same_class_hazards": sorted(model.NEGATIVE_SCENARIOS),
        **reports,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args(argv)
    result = run_checks()
    args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"ok={result['ok']} results={args.json_out}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
