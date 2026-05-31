"""Run FlowPilot project topology-orientation checks."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Sequence

from flowguard import Explorer

import flowpilot_project_topology_orientation_model as model


RESULTS_PATH = Path(__file__).resolve().with_name(
    "flowpilot_project_topology_orientation_results.json"
)

REQUIRED_LABELS = (
    "topology_orientation_started",
    "generate_flowguard_project_topology",
    "agent_reads_topology_before_nontrivial_work",
    "pm_considers_topology_as_background",
    "flowguard_operator_keeps_topology_as_background",
    "reviewer_keeps_topology_as_background",
    "select_downstream_flowguard_route_after_orientation",
    "attach_owning_validation_evidence_separate_from_topology",
    "topology_orientation_complete",
)

HAZARD_EXPECTED_FAILURES = {
    "skipped_topology_intake": "Mature FlowGuard project completed non-trivial work without topology intake",
    "stale_topology": "Stale topology was accepted for mature FlowGuard work",
    "missing_model_layer": "Topology missing model layer",
    "missing_test_layer": "Topology missing test layer",
    "missing_code_layer": "Topology missing code layer",
    "missing_evidence_layer": "Topology missing evidence layer",
    "missing_known_bad_layer": "Topology missing known-bad/risk layer",
    "topology_as_validation": "Topology was used as validation evidence",
    "missing_owning_validation": "Topology orientation completed without separate owning validation evidence",
    "controller_interprets_topology": "Controller interpreted topology as a FlowGuard report",
    "reviewer_gate_from_topology": "Reviewer approved a gate from topology",
    "pm_route_mutation_from_topology": "PM mutated route from topology alone",
    "source_change_without_refresh": "Topology source changed without rebuild/check",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|mature={state.mature_flowguard_project}|"
        f"topology={state.topology_artifacts_present},{state.topology_current},"
        f"{state.topology_read_before_work}|layers={state.model_layer_present},"
        f"{state.test_layer_present},{state.code_layer_present},"
        f"{state.evidence_layer_present},{state.known_bad_layer_present}|"
        f"roles={state.pm_considered_topology},{state.flowguard_operator_treated_topology_as_background},"
        f"{state.reviewer_treated_topology_as_background}|validation="
        f"{state.owning_validation_evidence_present},{state.topology_used_as_validation_evidence}"
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
    target_failures = model.invariant_failures(model.target_success_state())
    return {
        "ok": not graph["invariant_failures"] and not missing_labels and not target_failures,
        "state_count": len(graph["states"]),
        "edge_count": graph["edge_count"],
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"],
        "target_plan_failures": target_failures,
    }


def _progress_report(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    success = {idx for idx, state in enumerate(states) if model.is_success(state)}
    can_reach_success = set(success)
    changed = True
    while changed:
        changed = False
        for idx, outgoing in enumerate(edges):
            if idx not in can_reach_success and any(target in can_reach_success for _label, target in outgoing):
                can_reach_success.add(idx)
                changed = True
    stuck = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in terminal and not edges[idx]
    ]
    return {
        "ok": bool(success) and not stuck and 0 in can_reach_success,
        "success_state_count": len(success),
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "initial_can_reach_success": 0 in can_reach_success,
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


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _check_hazards()
    target_state = model.target_success_state()
    target_plan = {
        "ok": not model.invariant_failures(target_state),
        "state": target_state.__dict__,
        "failures": model.invariant_failures(target_state),
    }
    return {
        "ok": bool(safe_graph["ok"])
        and bool(progress["ok"])
        and bool(explorer["ok"])
        and bool(hazards["ok"])
        and bool(target_plan["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "target_project_topology_orientation": target_plan,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args(argv)

    result = run_checks()
    if args.json_out:
        args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
