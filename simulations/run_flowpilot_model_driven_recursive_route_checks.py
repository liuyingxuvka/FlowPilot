"""Run checks for the FlowPilot model-driven recursive route model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_model_driven_recursive_route_model as model


RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_model_driven_recursive_route_results.json")

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.ROUTE_DRAFTED_BEFORE_PRODUCT_MODEL: "route drafted before Product Officer wrote product behavior model",
    model.PRODUCT_MODEL_PM_DECISION_SKIPPED: "route drafted before PM accepted product behavior model",
    model.PRODUCT_REVIEW_SKIPPED_BEFORE_ROUTE: "route drafted before reviewer challenged product model",
    model.PROCESS_MODEL_MISSING_BEFORE_ACTIVATION: "route activated without Process Officer serial execution model",
    model.PROCESS_MODEL_NOT_SERIAL: "process route execution model is not serial",
    model.HIDDEN_PARALLEL_LEAF_MARKED_READY: "leaf readiness accepted hidden parallel or multi-worker work",
    model.LEAF_TOO_LARGE_NOT_PROMOTED: "oversized leaf was not promoted to a parent with child nodes",
    model.PROMOTED_LEAF_KEEPS_OLD_APPROVALS: "promoted leaf kept stale approvals instead of rerunning local gates",
    model.NON_LEAF_ENTRY_PRODUCT_LOOP_SKIPPED: "non-leaf node entered children before local product model PM decision and reviewer challenge",
    model.NON_LEAF_ENTRY_PROCESS_LOOP_SKIPPED: "non-leaf node entered children before local serial process model PM decision and reviewer challenge",
    model.PARENT_COMPLETION_OMITS_CHILD_COVERAGE: "parent completed before all child nodes were accounted for",
    model.PARENT_OMISSION_PATCHED_WITHOUT_MODEL_MISS: "parent omission patched without Process/FlowGuard model-miss triage and model upgrade",
    model.SAME_CLASS_OMISSIONS_NOT_SEARCHED: "parent model miss did not search same-class omissions",
    model.FINAL_CLOSURE_OMITS_MAJOR_NODE_REVIEW: "project completed before final review covered all major nodes and subtrees",
    model.FINAL_MODEL_MISS_NOT_UPGRADED: "final omission closed without Process/FlowGuard model-miss upgrade",
    model.PLACEHOLDER_KEPT_AFTER_REAL_ROUTE: "real route available but startup placeholder remained active",
    model.REAL_ROUTE_WITHOUT_MERMAID: "real route display omitted Mermaid graph in chat",
    model.REAL_ROUTE_USES_PROTOCOL_STAGES: "real route Mermaid did not use canonical serial execution model",
    model.COCKPIT_HIDES_DEEP_TREE: "Cockpit display hid full route tree or current path",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|"
        f"product={state.product_behavior_model_written},{state.pm_product_model_decision},{state.reviewer_product_model_challenge_passed}|"
        f"process={state.process_route_execution_model_written},{state.process_route_execution_model_serial},{state.pm_process_model_decision}|"
        f"node={state.node_product_model_written},{state.node_process_execution_model_written},{state.child_execution_started}|"
        f"parent={state.parent_completed},{state.parent_children_all_accounted_for}|"
        f"final={state.project_completed},{state.final_all_major_nodes_reviewed}|"
        f"display={state.real_route_mermaid_displayed_in_chat},{state.real_route_uses_serial_execution_model}|"
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
        "failures": failures,
    }


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    reports = {
        "safe_graph": _safe_graph_report(graph),
        "progress": _progress_report(graph),
        "flowguard": _flowguard_report(),
        "hazards": _hazard_report(),
        "intended_plan": _intended_plan_report(),
    }
    ok = all(report.get("ok") for report in reports.values())
    return {"ok": ok, **reports}


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

