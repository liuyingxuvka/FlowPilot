"""Run checks for the FlowPilot terminal FlowGuard coverage model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

import flowpilot_terminal_flowguard_coverage_model as model


RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_terminal_flowguard_coverage_results.json")


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|scenario={state.scenario}|"
        f"replay={state.node_parent_replay_settled}|work_order={state.terminal_work_order_recorded}|"
        f"report={state.terminal_report_written},{state.report_current},{state.report_pm_accepted}|"
        f"ledger={state.final_ledger_has_coverage_closure}|"
        f"reviewer={state.reviewer_segment_present},{state.reviewer_segment_passed}|"
        f"closure={state.pm_closure_approved}"
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
        for label, new_state in model.next_states(state):
            labels.add(label)
            if new_state not in index:
                index[new_state] = len(states)
                states.append(new_state)
                queue.append(new_state)
            edges[source].append((label, index[new_state]))

    return {
        "states": states,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _safe_graph_report(graph: dict[str, Any]) -> dict[str, object]:
    terminal_states = [state for state in graph["states"] if model.is_terminal(state)]
    missing_labels = sorted(set(model.REQUIRED_LABELS) - set(graph["labels"]))
    return {
        "ok": not graph["invariant_failures"] and not missing_labels and bool(terminal_states),
        "state_count": len(graph["states"]),
        "edge_count": graph["edge_count"],
        "terminal_state_count": len(terminal_states),
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"],
    }


def _progress_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for idx, outgoing in enumerate(edges):
            if idx not in can_reach_terminal and any(target in can_reach_terminal for _label, target in outgoing):
                can_reach_terminal.add(idx)
                changed = True
    stuck = [_state_id(state) for idx, state in enumerate(states) if idx not in terminal and not edges[idx]]
    cannot_reach_terminal = [_state_id(state) for idx, state in enumerate(states) if idx not in can_reach_terminal]
    return {
        "ok": not stuck and not cannot_reach_terminal,
        "stuck_state_count": len(stuck),
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "samples": (stuck + cannot_reach_terminal)[:10],
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
            {
                "label": getattr(item, "label", getattr(item, "required_label", "")),
                "reason": getattr(item, "reason", str(item)),
            }
            for item in report.reachability_failures
        ],
    }


def _hazard_report() -> dict[str, object]:
    hazards: dict[str, object] = {}
    ok = True
    for name, state in model.HAZARD_STATES.items():
        failures = model.invariant_failures(state)
        expected = model.HAZARD_EXPECTED_FAILURES[name]
        detected = expected in failures
        ok = ok and detected
        hazards[name] = {"detected": detected, "expected": expected, "failures": failures}
    return {"ok": ok, "hazards": hazards}


def _cartesian_report() -> dict[str, object]:
    cases = model.cartesian_hazard_states()
    misses: list[dict[str, object]] = []
    for name, state in cases.items():
        failures = model.invariant_failures(state)
        if not failures:
            misses.append({"case": name, "state": _state_id(state)})
    return {
        "ok": not misses,
        "axis_count": len(model.CARTESIAN_AXES),
        "case_count": len(cases),
        "miss_count": len(misses),
        "misses": misses[:10],
    }


def _intended_plan_report() -> dict[str, object]:
    failures = model.invariant_failures(model.intended_plan_state())
    return {"ok": not failures, "failures": failures}


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    reports = {
        "safe_graph": _safe_graph_report(graph),
        "progress": _progress_report(graph),
        "flowguard": _flowguard_report(),
        "hazards": _hazard_report(),
        "cartesian_fake_response_hazards": _cartesian_report(),
        "intended_plan": _intended_plan_report(),
    }
    return {
        "ok": all(bool(report.get("ok")) for report in reports.values()),
        "model_boundary": "terminal_flowguard_coverage",
        **reports,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
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
