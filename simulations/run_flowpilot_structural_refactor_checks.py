"""Run checks for the FlowPilot structural-refactor process model."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_structural_refactor_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_structural_refactor_results.json"

REQUIRED_LABELS = (
    "record_baseline_and_rollback_point",
    "write_openspec_structure_contract",
    "run_structural_refactor_flowguard_guard",
    "start_events_slice",
    "start_action_providers_slice",
    "start_action_handlers_slice",
    "start_tests_slice",
    "start_runtime_domain_slice",
    "start_meta_capability_models_slice",
    "run_meta_and_capability_checks_for_model_split",
    "start_install_tooling_slice",
    "start_docs_install_sync_slice",
    "run_focused_validation_for_current_slice",
    "sync_installed_flowpilot_skill",
    "run_public_boundary_privacy_check",
    "push_maintenance_branch_without_release",
    "structural_refactor_complete",
)

HAZARD_EXPECTED_FAILURES = {
    "change_before_baseline": "structural refactor changed code before baseline was recorded",
    "change_before_openspec": "structural refactor changed code before OpenSpec contract was ready",
    "change_before_flowguard": "structural refactor changed code before FlowGuard guard passed",
    "compat_entrypoint_deleted": "structural refactor deleted or bypassed compatibility entrypoints",
    "protocol_shape_changed": "structure-only refactor changed protocol or JSON shape",
    "model_split_without_heavy_checks": "Meta/Capability model split completed before both heavyweight checks completed",
    "remote_sync_before_install_sync": "remote sync happened before installed skill sync check",
    "remote_sync_before_privacy_check": "remote sync happened before public-boundary privacy check",
    "tag_release_in_structure_pass": "structure maintenance performed tag or release without explicit release scope",
}


def _state_id(state: model.State) -> str:
    return json.dumps(state.__dict__, sort_keys=True)


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
    return {
        "states": states,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _progress_report(graph: dict[str, object]) -> dict[str, object]:
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
        "terminal_state_count": len(terminal),
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "cannot_reach_terminal_samples": cannot_reach_terminal[:10],
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
    ok = True
    hazards: dict[str, object] = {}
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
    missing_labels = sorted(set(REQUIRED_LABELS) - set(graph["labels"]))
    safe_graph = {
        "ok": not graph["invariant_failures"] and not missing_labels,
        "state_count": len(graph["states"]),
        "edge_count": graph["edge_count"],
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"],
    }
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _check_hazards()
    return {
        "ok": bool(safe_graph["ok"]) and bool(progress["ok"]) and bool(explorer["ok"]) and bool(hazards["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
    }


def main() -> int:
    result = run_checks()
    RESULTS_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
