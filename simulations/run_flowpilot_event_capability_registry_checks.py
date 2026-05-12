"""Run checks for the FlowPilot event-capability registry model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_event_capability_registry_model as model


RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_event_capability_registry_results.json")

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.UNREGISTERED_EVENT_ACCEPTED: "event capability row is missing",
    model.FALSE_PRECONDITION_WAIT_ACCEPTED: "event capability precondition is not currently receivable",
    model.WRONG_PRODUCER_ROLE_WAIT_ACCEPTED: "wait target role does not include event producer role",
    model.ACK_EVENT_WAIT_ACCEPTED: "direct ACK/check-in event was accepted as external capability",
    model.PARENT_CURRENT_PACKET_WAIT_ACCEPTED: "event capability incompatible with active node kind",
    model.PARENT_BACKWARD_RERUN_TARGETS_LEAF_DISPATCH: "parent backward replay repair used non-parent-safe event",
    model.PARENT_BACKWARD_SUCCESS_OUTCOME_LEAF_EVENT: "parent backward replay repair used non-parent-safe event",
    model.COLLAPSED_REPAIR_OUTCOMES_ON_BUSINESS_EVENT: "repair outcome table collapsed success blocker and protocol-blocker events",
    model.BLOCKER_OUTCOME_USES_SUCCESS_EVENT: "repair non-success outcome uses success-only business event",
    model.PROTOCOL_OUTCOME_USES_SUCCESS_EVENT: "repair outcome event is not eligible for protocol_blocker row",
    model.PM_REPAIR_EVENT_AS_RERUN_TARGET: "event capability cannot be used as repair rerun target",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|"
        f"node={state.active_node_kind}|origin={state.repair_origin}|"
        f"target_role={state.target_role}|receivable={state.currently_receivable}|"
        f"waits={state.wait_events}|rerun={state.rerun_target}|"
        f"outcomes={state.repair_success_event},{state.repair_blocker_event},"
        f"{state.repair_protocol_event}|reason={state.terminal_reason}"
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
        for idx, outgoing in enumerate(edges):
            if idx not in can_reach_terminal and any(target in can_reach_terminal for _label, target in outgoing):
                can_reach_terminal.add(idx)
                changed = True
    stuck = [_state_id(state) for idx, state in enumerate(states) if idx not in terminal and not edges[idx]]
    cannot_reach_terminal = [_state_id(state) for idx, state in enumerate(states) if idx not in can_reach_terminal]
    return {
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_terminal,
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
        terminal_predicate=model.terminal_predicate,
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
        capability_failures = model.event_capability_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in capability_failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": capability_failures,
            "state": state.__dict__,
        }
        if not detected:
            failures.append(f"{name}: expected failure containing {expected!r}")
    return {"ok": not failures, "hazards": hazards, "failures": failures}


def _architecture_candidate() -> dict[str, object]:
    return {
        "name": "event_capability_registry",
        "principles": [
            "External event registration is necessary but not sufficient for execution.",
            "The same capability lookup gates waits, PM rerun targets, and repair outcome rows.",
            "Parent/module backward-replay repairs are restricted to parent-safe events.",
            "Repair success, blocker, and protocol-blocker rows use distinct eligible event identities.",
            "Controller wait target roles are derived from event producer roles, not prompt text.",
        ],
        "minimum_runtime_change_set": [
            "Add event capability metadata around the existing Router EXTERNAL_EVENTS table.",
            "Use the capability validator before writing control-blocker waits.",
            "Use the capability validator before committing a PM repair rerun target.",
            "Reject unsupported generic repair outcome tables instead of collapsing non-success rows onto the success event.",
            "Keep material dispatch repair on its existing three explicit outcome events.",
        ],
    }


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _hazard_report()
    result = {
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "architecture_candidate": _architecture_candidate(),
    }
    result["ok"] = all(section.get("ok", False) for section in (safe_graph, progress, explorer, hazards))
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
