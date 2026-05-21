"""Run checks for the FlowPilot Router reconciliation branch-pruning model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from dataclasses import asdict
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_router_reconciliation_branch_pruning_model as model


RESULTS_PATH = Path(__file__).resolve().with_name(
    "flowpilot_router_reconciliation_branch_pruning_results.json"
)

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.OVERCLAIM_BRANCH_EQUIVALENCE: (
        "branch contraction overclaimed equivalence without replay evidence"
    ),
    model.MISSING_EVENT_AUTHORITY: (
        "role-output event was recorded without durable Router authority"
    ),
    model.DUPLICATE_RUNTIME_STATE_OWNER: (
        "runtime-state branch pruning introduced duplicate state ownership"
    ),
    model.PROGRESS_ONLY_VALIDATION: (
        "background progress was claimed as pass without exit artifact"
    ),
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|surface={state.surface}|"
        f"case={state.result_case}|subcase={state.result_subcase}|"
        f"writes={state.observable_state_writes}|side_effects={state.side_effects}|"
        f"replay={state.requires_replay_evidence},{state.replay_or_alignment_evidence}|"
        f"authority={state.event_authority_required},{state.event_authority_present},"
        f"{state.event_recorded}|owners={state.runtime_state_owner_count}|"
        f"background={state.background_progress_seen},{state.background_exit_artifact_seen},"
        f"{state.validation_claimed_passed}|reason={state.terminal_reason}"
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
    result_cases = sorted(
        {
            state.result_case
            for state in accepted
            if state.surface != model.BACKGROUND_VALIDATION_SURFACE
        }
    )
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and set(accepted_scenarios) == set(model.VALID_SCENARIOS)
        and set(rejected_scenarios) == set(model.NEGATIVE_SCENARIOS)
        and set(model.RESULT_CASES).issuperset(result_cases),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "accepted_scenarios": accepted_scenarios,
        "rejected_scenarios": rejected_scenarios,
        "observed_result_cases": result_cases,
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
            if idx not in can_reach_terminal and any(
                target in can_reach_terminal for _label, target in outgoing
            ):
                can_reach_terminal.add(idx)
                changed = True
    stuck = [_state_id(state) for idx, state in enumerate(states) if idx not in terminal and not edges[idx]]
    cannot_reach_terminal = [
        _state_id(state) for idx, state in enumerate(states) if idx not in can_reach_terminal
    ]
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
        branch_failures = model.branch_pruning_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in branch_failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": branch_failures,
            "state": asdict(state),
        }
        if not detected:
            failures.append(f"{name}: expected failure containing {expected!r}")
    return {"ok": not failures, "hazards": hazards, "failures": failures}


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _hazard_report()
    result = {
        "model": "flowpilot_router_reconciliation_branch_pruning",
        "ownership_snapshot": model.ownership_snapshot(),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
    }
    result["ok"] = all(
        section.get("ok", False) for section in (safe_graph, progress, explorer, hazards)
    )
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
