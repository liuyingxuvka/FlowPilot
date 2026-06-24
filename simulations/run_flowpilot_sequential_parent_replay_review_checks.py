"""Run checks for the FlowPilot sequential parent replay review model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

import flowpilot_sequential_parent_replay_review_model as model


RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_sequential_parent_replay_review_results.json")

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.RAW_REPLAY_CLOSES_PARENT: "parent replay closure recorded before independent review accepted",
    model.SEGMENT_DECISION_BEFORE_REVIEW: "PM parent segment decision offered before independent parent replay review",
    model.TERMINAL_REPLAY_BEFORE_PARENT_REVIEW: "terminal backward replay offered before required parent replay review",
    model.PARALLEL_PARENT_REPLAY_REVIEWS: "Router did not issue exactly one current parent replay review packet",
    model.ROOT_GAP_SELECTED_BEFORE_CHILD_GAP: "Router selected a shallower parent replay review gap before the deepest current gap",
    model.OLD_STATE_COUNTS_RAW_REPLAY_AS_COMPLETE: "fallback or old-state compatibility path was used for parent replay review",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|"
        f"raw={state.parent_replay_result_accepted}|review={state.independent_replay_review_accepted}|"
        f"closure={state.parent_replay_closure_recorded}|pm={state.pm_segment_decision_offered},"
        f"{state.pm_parent_completion_offered}|terminal={state.terminal_replay_offered}|"
        f"gaps={state.current_missing_review_gap_count}|issued={state.review_packets_issued_this_tick}|"
        f"depth={state.selected_gap_depth}/{state.deepest_missing_gap_depth}|"
        f"order={state.selected_gap_route_order_index}/{state.earliest_deepest_gap_route_order_index}|"
        f"fallback={state.fallback_or_compatibility_path_used}|reason={state.terminal_reason}"
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
    accepted_scenarios = sorted(state.scenario for state in accepted)
    rejected_scenarios = sorted(state.scenario for state in rejected)
    missing_labels = sorted(set(REQUIRED_LABELS) - set(graph["labels"]))
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and set(accepted_scenarios) == set(model.VALID_SCENARIOS)
        and set(rejected_scenarios) == set(model.NEGATIVE_SCENARIOS),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "accepted_scenarios": accepted_scenarios,
        "rejected_scenarios": rejected_scenarios,
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
    stuck = [_state_id(state) for idx, state in enumerate(states) if idx not in terminal and not edges[idx]]
    cannot_reach_terminal = [_state_id(state) for idx, state in enumerate(states) if idx not in can_reach_terminal]
    return {
        "ok": not stuck and not cannot_reach_terminal,
        "terminal_state_count": len(terminal),
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
        review_failures = model.replay_review_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in review_failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": review_failures,
        }
        if not detected:
            failures.append(f"{name}: expected failure containing {expected!r}")
    return {"ok": not failures, "hazards": hazards, "failures": failures}


def _intended_report() -> dict[str, object]:
    failures: dict[str, list[str]] = {}
    for scenario, state in model.intended_states().items():
        scenario_failures = model.replay_review_failures(state)
        if scenario_failures:
            failures[scenario] = scenario_failures
    return {"ok": not failures, "failures": failures, "accepted_plan": sorted(model.VALID_SCENARIOS)}


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
        "model": "flowpilot_sequential_parent_replay_review",
        "covered_risks": sorted(model.NEGATIVE_SCENARIOS),
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
