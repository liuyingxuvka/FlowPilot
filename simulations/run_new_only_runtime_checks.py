"""Run checks for the FlowPilot new-only runtime model."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_new_only_runtime_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_new_only_runtime_results.json"

HAZARD_EXPECTED_FAILURES = {
    "retired_input_accepted": "retired input was accepted as current runtime input",
    "retired_input_migrated": "retired input was migrated into current state",
    "retired_event_canonicalized": "retired event alias was canonicalized",
    "retired_prompt_path_offered": "active prompt offered a retired path",
    "prior_authority_quarantine_removed": "prior authority quarantine was removed",
    "completion_without_current_start": "completion without current start",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|current={state.current_start_seen},"
        f"{state.current_startup_intake_seen},{state.current_event_seen},"
        f"{state.current_role_output_seen},{state.current_repair_transaction_seen},"
        f"{state.current_layout_seen}|retired={state.accepted_retired_input},"
        f"{state.migrated_retired_input},{state.canonicalized_retired_event},"
        f"{state.retired_prompt_path_offered}|"
        f"prior_quarantined={state.prior_authority_quarantined}"
    )


def _build_reachable_graph() -> dict[str, object]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    seen: list[model.State] = [initial]
    index = {initial: 0}
    labels: set[str] = set()
    edges: list[list[tuple[str, int]]] = []
    invariant_failures: list[dict[str, object]] = []

    while queue:
        state = queue.popleft()
        source_index = index[state]
        while len(edges) <= source_index:
            edges.append([])

        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})

        for input_obj in model.EXTERNAL_INPUTS:
            for transition in model.next_states(input_obj, state):
                labels.add(transition.label)
                if transition.state not in index:
                    index[transition.state] = len(seen)
                    seen.append(transition.state)
                    queue.append(transition.state)
                edges[source_index].append((transition.label, index[transition.state]))

    return {
        "states": seen,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _graph_report(graph: dict[str, object]) -> dict[str, object]:
    labels = set(graph["labels"])
    required = set(model.REQUIRED_CURRENT_LABELS) | set(model.REQUIRED_REJECTION_LABELS)
    missing_labels = sorted(required - labels)
    states: list[model.State] = graph["states"]
    complete_states = [state for state in states if model.is_success(state)]
    return {
        "ok": not graph["invariant_failures"] and not missing_labels and bool(complete_states),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "labels": sorted(labels),
        "missing_labels": missing_labels,
        "complete_state_count": len(complete_states),
        "rejected_state_count": sum(1 for state in states if state.status == "rejected"),
        "invariant_failures": graph["invariant_failures"],
    }


def _check_progress(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    success = {idx for idx, state in enumerate(states) if model.is_success(state)}
    can_reach_success = set(success)
    changed = True
    while changed:
        changed = False
        for source, outgoing in enumerate(edges):
            targets = [target for _label, target in outgoing]
            if source not in can_reach_success and any(target in can_reach_success for target in targets):
                can_reach_success.add(source)
                changed = True
    stuck = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in terminal and not edges[idx]
    ]
    return {
        "ok": not stuck and 0 in can_reach_success,
        "initial_can_reach_success": 0 in can_reach_success,
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
    }


def _explore_current_path() -> dict[str, object]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=(model.Tick(model.CURRENT_CONTRACT_TICK),),
        invariants=model.INVARIANTS,
        max_sequence_length=len(model.CURRENT_INPUTS),
        terminal_predicate=lambda _input, state, _trace: model.is_terminal(state),
        success_predicate=lambda state, _trace: model.is_success(state),
        required_labels=model.REQUIRED_CURRENT_LABELS,
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


def _explore_retired_input_rejections() -> dict[str, object]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=tuple(model.Tick(kind) for kind in model.RETIRED_INPUTS),
        invariants=model.INVARIANTS,
        max_sequence_length=1,
        terminal_predicate=lambda _input, state, _trace: model.is_terminal(state),
        success_predicate=lambda state, _trace: state.status == "rejected",
        required_labels=model.REQUIRED_REJECTION_LABELS,
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
    graph = _build_reachable_graph()
    safe_graph = _graph_report(graph)
    progress = _check_progress(graph)
    current_explorer = _explore_current_path()
    retired_input_explorer = _explore_retired_input_rejections()
    hazards = _check_hazards()
    return {
        "ok": (
            bool(safe_graph["ok"])
            and bool(progress["ok"])
            and bool(current_explorer["ok"])
            and bool(retired_input_explorer["ok"])
            and bool(hazards["ok"])
        ),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_current_path_explorer": current_explorer,
        "flowguard_retired_input_rejection_explorer": retired_input_explorer,
        "hazard_checks": hazards,
    }


def main() -> int:
    result = run_checks()
    RESULTS_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
