"""Run checks for the FlowPilot recursive decomposition model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_recursive_decomposition_model as model


RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_recursive_decomposition_results.json")

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.FIXED_TWO_LAYER_COMPLEX_ROUTE: "complex route was accepted with fixed two-layer depth",
    model.COARSE_LEAF_MARKED_READY: "leaf is too coarse for direct worker execution",
    model.OVER_SPLIT_LEAF_STEPS: "route over-split operational steps without independent acceptance value",
    model.REVIEWER_SKIPS_DEPTH_REVIEW: "reviewer did not check both insufficient depth and over-decomposition",
    model.PARENT_DISPATCHED_TO_WORKER: "router dispatched a parent or module node to a worker",
    model.UNREADY_LEAF_DISPATCHED: "dispatchable leaf lacks passing leaf-readiness gate",
    model.PARENT_REVIEW_SKIPPED: "parent completed without passing backward composition review",
    model.PARENT_FAILURE_ADVANCES: "parent review failure advanced without route mutation or child rework",
    model.MUTATION_FRONTIER_NOT_RESET: "route mutation split node without resetting stale frontier",
    model.DISPLAY_LEAKS_DEEP_TREE: "user display leaked the deep internal route tree",
    model.DISPLAY_HIDES_ACTIVE_PATH: "user display hides active deep path or hidden leaf progress",
    model.FINAL_LEDGER_OMITS_DEEP_LEAF: "final route-wide ledger omits deep leaf nodes",
    model.MISSING_DECOMPOSITION_MEMORY: "PMK route memory lacks decomposition rationale",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|depth={state.canonical_tree_depth}|"
        f"node={state.dispatched_node_kind}|ready={state.dispatched_leaf_readiness_status}|"
        f"parent_review={state.parent_backward_review_passed}/{state.parent_backward_review_failed}|"
        f"display={state.display_depth},path={state.active_path_breadcrumb_visible}|"
        f"pmk={state.pmk_decomposition_memory_written}|ledger={state.final_ledger_covers_deep_leaves}|"
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
        protocol_failures = model.protocol_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in protocol_failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": protocol_failures,
        }
        if not detected:
            failures.append(f"{name}: expected failure containing {expected!r}")
    return {"ok": not failures, "hazards": hazards, "failures": failures}


def _intended_plan_report() -> dict[str, object]:
    state = model.intended_plan_state()
    failures = model.protocol_failures(state)
    return {
        "ok": not failures,
        "scenario": state.scenario,
        "state": state.__dict__,
        "failures": failures,
    }


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _hazard_report()
    intended_plan = _intended_plan_report()
    result = {
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "intended_plan": intended_plan,
    }
    result["ok"] = all(
        section.get("ok", False)
        for section in (safe_graph, progress, explorer, hazards, intended_plan)
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args()

    result = run_checks()
    output = json.dumps(result, indent=2, sort_keys=True)
    print(output)
    if args.json_out:
        args.json_out.write_text(output + "\n", encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
