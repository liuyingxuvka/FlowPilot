"""Run checks for the FlowPilot dynamic return-path model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_dynamic_return_path_model as model


RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_dynamic_return_path_results.json")
PROJECT_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.SYSTEM_CARD_ONLY_ROUTER_SUPPLIED_REPORT: "router-supplied contract has no concrete return event",
    model.TASK_CARD_WITHOUT_WORK_AUTHORITY: "task-like card lacks Router-registered work authority",
    model.IDENTITY_CARD_CARRIES_HIDDEN_WORK: "identity card carried hidden formal work",
    model.ROLE_GUESSES_UNKNOWN_EVENT: "role guessed a formal return event",
    model.REGISTERED_EVENT_NOT_CURRENTLY_ALLOWED: "formal return event is not currently allowed by Router wait state",
    model.MECHANICAL_GREEN_USED_AS_ROUTER_ACCEPTANCE: "mechanical role-output validation was treated as Router acceptance",
    model.STATIC_CARD_GUIDANCE_USED_AS_DYNAMIC_LEASE: "static card text was treated as a dynamic event lease",
    model.LEGACY_DIRECT_EVENT_COMPETES_WITH_PM_PACKET: "legacy direct officer event competes with PM role-work result contract",
    model.PM_ROLE_WORK_WRONG_RECIPIENT: "PM role-work result does not return to project_manager",
    model.WRONG_ROLE_USES_WORK_AUTHORITY: "work authority role does not match submitting role",
    model.WRONG_CONTRACT_USES_WORK_AUTHORITY: "work authority contract does not match submitted output",
    model.STALE_WORK_AUTHORITY_USED: "work authority route or frontier is stale",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|assignment={state.assignment_surface}|"
        f"mode={state.contract_event_mode}|source={state.return_event_source}|event={state.return_event_name}|"
        f"registered={state.return_event_registered}|allowed={state.return_event_currently_allowed}|"
        f"mechanical={state.mechanical_role_output_valid}|accepted={state.router_accepted_event}|"
        f"continue={state.current_run_allowed_to_continue}|reason={state.terminal_reason}"
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
        event_failures = model.return_path_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in event_failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": event_failures,
            "state": state.__dict__,
        }
        if not detected:
            failures.append(f"{name}: expected failure containing {expected!r}")
    return {"ok": not failures, "hazards": hazards, "failures": failures}


def run_checks(project_root: Path = PROJECT_ROOT) -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _hazard_report()
    live_projection = model.project_live_run_projection(project_root)
    result = {
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "live_run_projection": live_projection,
    }
    result["ok"] = all(section.get("ok", False) for section in (safe_graph, progress, explorer, hazards, live_projection))
    result["current_run_can_continue"] = bool(live_projection.get("current_run_can_continue"))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    args = parser.parse_args()

    result = run_checks(args.project_root.resolve())
    output = json.dumps(result, indent=2, sort_keys=True)
    print(output)
    if args.json_out:
        args.json_out.write_text(output + "\n", encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
