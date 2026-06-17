"""Run checks for the FlowPilot Controller process-aside model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

import flowpilot_controller_process_aside_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_controller_process_aside_results.json"

HAZARD_EXPECTED_FAILURES = {
    "aside_satisfies_formal_wait": "process aside satisfied a formal wait",
    "aside_replaces_formal_body": "process aside replaced the formal output body",
    "aside_becomes_evidence": "Controller used process aside as formal content",
    "aside_drives_router_event": "Router semantically inspected process aside text",
    "worker_to_workerside": "worker process aside became Worker-to-Worker communication",
    "missing_aside_blocks_flow": "missing optional process aside blocked formal flow",
    "controller_reports_formal_content_from_aside": "Controller used process aside as formal content",
    "routine_aside_relayed_to_user": "routine process aside was automatically relayed to the user",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|"
        f"aside={state.aside_present},{state.aside_labeled_process_only},"
        f"{state.aside_marked_not_formal_evidence},"
        f"{state.aside_marked_no_progress_authority}|"
        f"formal={state.formal_output_present},{state.formal_output_validated},"
        f"{state.formal_wait_satisfied_by_formal_output},"
        f"{state.formal_wait_satisfied_by_aside}|"
        f"router={state.router_preserved_aside},"
        f"{state.router_semantically_inspected_aside},"
        f"{state.router_event_derived_from_aside}|"
        f"controller={state.controller_reads_aside},"
        f"{state.controller_uses_aside_for_operational_status},"
        f"{state.controller_uses_aside_for_formal_content},"
        f"user_msg={state.user_visible_message_emitted_from_aside},"
        f"formal_visible={state.formal_state_independently_user_visible}|"
        f"worker={state.workerside_controller_only},"
        f"{state.workerside_visible_to_sibling_worker}|"
        f"missing_blocks={state.missing_aside_blocks_flow}"
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
    terminal = [state for state in graph["states"] if model.is_terminal(state)]
    accepted = sorted(state.scenario for state in terminal if state.status == "accepted")
    rejected = sorted(state.scenario for state in terminal if state.status == "rejected")
    missing_labels = sorted(set(model.REQUIRED_LABELS) - set(graph["labels"]))
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and set(accepted) == set(model.VALID_SCENARIOS)
        and set(rejected) == set(model.NEGATIVE_SCENARIOS),
        "state_count": len(graph["states"]),
        "edge_count": graph["edge_count"],
        "accepted_scenarios": accepted,
        "rejected_scenarios": rejected,
        "missing_labels": missing_labels,
        "invariant_failure_count": len(graph["invariant_failures"]),
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
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_terminal,
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
        terminal_predicate=model.terminal_predicate,
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
        "reachability_failures": [failure.message for failure in report.reachability_failures],
    }


def _hazard_report() -> dict[str, object]:
    hazards: dict[str, object] = {}
    failures: list[str] = []
    for name, state in model.hazard_states().items():
        scenario_failures = model.process_aside_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in scenario_failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": scenario_failures,
            "state": state.__dict__,
        }
        if not detected:
            failures.append(f"{name}: expected failure containing {expected!r}")
    return {"ok": not failures, "hazards": hazards, "failures": failures}


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    flowguard = _flowguard_report()
    hazards = _hazard_report()
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "ok": bool(safe_graph["ok"]) and bool(progress["ok"]) and bool(flowguard["ok"]) and bool(hazards["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": flowguard,
        "hazard_checks": hazards,
        "model_boundary": (
            "focused Controller process-aside authority model; runtime tests and "
            "prompt coverage remain required for production confidence"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", default=str(RESULTS_PATH))
    args = parser.parse_args()

    results = run_checks()
    output_path = Path(args.json_out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0 if results["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
