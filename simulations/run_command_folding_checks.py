"""Run checks for the FlowPilot router command-folding model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_command_folding_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_command_folding_results.json"


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|"
        f"safe={state.safe_internal_actions_applied},stop={state.stopped_at_boundary},cross={state.boundary_crossed}|"
        f"manifest={state.manifest_checked},cards={state.cards_delivered},same_role={state.card_bundle_same_role},next={state.next_card_matched}|"
        f"ledger={state.ledger_checked},relay={state.relay_recorded}|"
        f"audit={state.startup_mechanical_audit_written},startup_card={state.startup_fact_card_delivered}|"
        f"preflight={state.role_output_preflight_checked},file={state.role_output_file_backed},event={state.event_recorded},blocker={state.control_blocker_created}|"
        f"router={state.router_decision}:{state.router_rejection_reason}"
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

        for transition in model.next_safe_states(state):
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


def _safe_graph_report(graph: dict[str, object]) -> dict[str, object]:
    labels = set(graph["labels"])
    states: list[model.State] = graph["states"]
    missing_labels = sorted(set(model.REQUIRED_LABELS) - labels)
    terminals = [state for state in states if model.is_terminal(state)]
    accepted = [state for state in terminals if state.status == "accepted"]
    rejected = [state for state in terminals if state.status == "rejected"]
    accepted_scenarios = sorted(state.scenario for state in accepted)
    rejected_scenarios = sorted(state.scenario for state in rejected)
    expected_accepted = sorted(
        scenario for scenario in model.SCENARIOS if scenario not in model.NEGATIVE_SCENARIOS
    )
    expected_rejected = sorted(model.NEGATIVE_SCENARIOS)
    return {
        "ok": (
            not graph["invariant_failures"]
            and not missing_labels
            and accepted_scenarios == expected_accepted
            and rejected_scenarios == expected_rejected
        ),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "accepted_scenarios": accepted_scenarios,
        "rejected_scenarios": rejected_scenarios,
        "missing_labels": missing_labels,
        "invariant_failure_count": len(graph["invariant_failures"]),
        "invariant_failures": graph["invariant_failures"][:10],
    }


def _check_expected_scenarios(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    terminal_by_scenario = {
        state.scenario: state
        for state in states
        if model.is_terminal(state) and state.scenario != "unset"
    }
    failures: list[str] = []
    results: dict[str, str] = {}

    for scenario in model.SCENARIOS:
        terminal = terminal_by_scenario.get(scenario)
        if terminal is None:
            failures.append(f"{scenario}: no terminal state")
            results[scenario] = "missing"
            continue
        results[scenario] = f"{terminal.status}:{terminal.router_rejection_reason}"
        if scenario in model.NEGATIVE_EXPECTED_REJECTIONS:
            expected_reason = model.NEGATIVE_EXPECTED_REJECTIONS[scenario]
            if terminal.status != "rejected" or terminal.router_rejection_reason != expected_reason:
                failures.append(
                    f"{scenario}: expected rejected:{expected_reason}, got {results[scenario]}"
                )
        elif terminal.status != "accepted":
            failures.append(f"{scenario}: expected accepted, got {terminal.status}")

    return {"ok": not failures, "results": results, "failures": failures}


def _check_progress(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for source, outgoing in enumerate(edges):
            targets = [target for _label, target in outgoing]
            if source not in can_reach_terminal and any(target in can_reach_terminal for target in targets):
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
        "ok": not stuck and not cannot_reach_terminal,
        "stuck_state_count": len(stuck),
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "samples": (stuck + cannot_reach_terminal)[:10],
    }


def _run_flowguard_explorer() -> dict[str, object]:
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
        "reachability_failures": [
            failure.message for failure in report.reachability_failures
        ],
    }


def run_checks() -> dict[str, object]:
    graph = _build_reachable_graph()
    checks = {
        "safe_graph": _safe_graph_report(graph),
        "expected_scenarios": _check_expected_scenarios(graph),
        "progress": _check_progress(graph),
        "flowguard_explorer": _run_flowguard_explorer(),
    }
    return {
        "ok": all(check["ok"] for check in checks.values()),
        "model": "flowpilot_command_folding",
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", default=str(RESULTS_PATH))
    args = parser.parse_args()
    report = run_checks()
    out = Path(args.json_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
