"""Run checks for the FlowPilot integration Cartesian coverage model."""

from __future__ import annotations

import argparse
import json
from collections import Counter, deque
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

import flowpilot_integration_cartesian_coverage_model as model


RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_integration_cartesian_coverage_results.json")

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)


def _state_id(state: model.State) -> str:
    return f"scenario={state.scenario}|status={state.status}"


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
    expected = model.expected_failures_by_hazard()
    for name, state in model.hazard_states().items():
        actual = model.state_failures(state)
        detected = expected[name] == actual and bool(actual)
        hazards[name] = {
            "detected": detected,
            "expected_failures": expected[name],
            "failures": actual,
        }
        if not detected:
            failures.append(f"{name}: expected {expected[name]!r}, got {actual!r}")
    return {"ok": not failures, "hazards": hazards, "failures": failures}


def _matrix_report() -> dict[str, object]:
    coverage = model.axis_value_coverage()
    missing_axis_values = {
        axis: row["missing"]
        for axis, row in coverage.items()
        if row["missing"]
    }
    by_outcome: Counter[str] = Counter()
    by_authority: Counter[str] = Counter()
    sampled_cells: list[dict[str, Any]] = []
    runtime_hard_blocker_cells: list[str] = []
    worker_current_gate_blocker_cells: list[str] = []
    for index, cell in enumerate(model.iter_required_cells()):
        by_outcome[str(cell["expected_outcome"])] += 1
        by_authority[str(cell["required_authority"])] += 1
        if index < 25:
            sampled_cells.append(cell)
        if cell["runtime_hard_blocker_allowed"]:
            runtime_hard_blocker_cells.append(str(cell["cell_id"]))
        if cell["worker_current_gate_blocker_allowed"]:
            worker_current_gate_blocker_cells.append(str(cell["cell_id"]))

    failures = model.matrix_failures(model.iter_required_cells())
    return {
        "ok": not missing_axis_values and not failures and not runtime_hard_blocker_cells and not worker_current_gate_blocker_cells,
        "declared_counts": model.matrix_counts(),
        "observed_cell_count": sum(by_outcome.values()),
        "axis_coverage": coverage,
        "missing_axis_values": missing_axis_values,
        "by_expected_outcome": dict(sorted(by_outcome.items())),
        "by_required_authority": dict(sorted(by_authority.items())),
        "runtime_hard_blocker_cells": runtime_hard_blocker_cells[:20],
        "worker_current_gate_blocker_cells": worker_current_gate_blocker_cells[:20],
        "matrix_failures": failures[:20],
        "sampled_cells": sampled_cells,
    }


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    explorer = _flowguard_report()
    hazards = _hazard_report()
    matrix = _matrix_report()
    result = {
        "model_id": model.MODEL_ID,
        "safe_graph": safe_graph,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "matrix": matrix,
    }
    result["ok"] = all(section.get("ok", False) for section in (safe_graph, explorer, hazards, matrix))
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
