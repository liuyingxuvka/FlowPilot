"""Run checks for the FlowPilot router action payload-contract model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_router_action_contract_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_router_action_contract_results.json"

HAZARD_EXPECTED_FAILURES = {
    model.CONTRACT_MISSING_INTERPRETATION_SCHEMA: (
        "internal required fields absent from payload_contract"
    ),
    model.PAYLOAD_MISSING_INTERPRETATION_SCHEMA: (
        "payload without schema_version"
    ),
    model.CONTRACT_INCOMPLETE_INTERPRETATION_REQUIRED_FIELDS: (
        "internal required fields absent from payload_contract"
    ),
    "controller_may_fill_missing_fields": "Controller field guessing",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|"
        f"published={state.payload_contract_published}|"
        f"payload={state.payload_built_from_contract},"
        f"interpretation={state.payload_includes_interpretation}|"
        f"contract_missing={sorted(model.INTERPRETATION_REQUIRED_FIELDS - state.contract.required_nested_fields)}|"
        f"payload_missing={sorted(state.internal_interpretation_required_fields - state.payload_interpretation_fields)}|"
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
        [
            model.VALID_EXPLICIT_STARTUP,
            model.VALID_AI_INTERPRETED_STARTUP,
        ]
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
        "accepted_state_count": len(accepted),
        "rejected_state_count": len(rejected),
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
    results: dict[str, str] = {}
    failures: list[str] = []

    for scenario in (model.VALID_EXPLICIT_STARTUP, model.VALID_AI_INTERPRETED_STARTUP):
        terminal = terminal_by_scenario.get(scenario)
        if terminal is None:
            failures.append(f"{scenario}: no terminal state")
            results[scenario] = "missing"
            continue
        results[scenario] = terminal.status
        if terminal.status != "accepted":
            failures.append(f"{scenario}: expected accepted, got {terminal.status}")

    for scenario, expected_reason in model.NEGATIVE_EXPECTED_REJECTIONS.items():
        terminal = terminal_by_scenario.get(scenario)
        if terminal is None:
            failures.append(f"{scenario}: no terminal state")
            results[scenario] = "missing"
            continue
        results[scenario] = f"{terminal.status}:{terminal.router_rejection_reason}"
        if (
            terminal.status != "rejected"
            or terminal.router_rejection_reason != expected_reason
        ):
            failures.append(
                f"{scenario}: expected rejected:{expected_reason}, got {results[scenario]}"
            )

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
            if source not in can_reach_terminal and any(
                target in can_reach_terminal for target in targets
            ):
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
            "state": {
                "scenario": state.scenario,
                "status": state.status,
                "contract_required_nested_fields": sorted(
                    state.contract.required_nested_fields
                ),
                "payload_interpretation_fields": sorted(
                    state.payload_interpretation_fields
                ),
                "router_decision": state.router_decision,
            },
        }
        ok = ok and detected
    return {"ok": ok, "hazards": hazards}


def _pass_fail(ok: bool) -> str:
    return "pass" if ok else "fail"


def run_checks() -> dict[str, object]:
    graph = _build_reachable_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _check_progress(graph)
    scenarios = _check_expected_scenarios(graph)
    hazards = _check_hazards()
    explorer = _run_flowguard_explorer()
    ok = all(
        bool(check["ok"])
        for check in (safe_graph, progress, scenarios, hazards, explorer)
    )

    result: dict[str, object] = {
        "ok": ok,
        "checks": {
            "safe_graph": _pass_fail(bool(safe_graph["ok"])),
            "progress": _pass_fail(bool(progress["ok"])),
            "scenario_outcomes": _pass_fail(bool(scenarios["ok"])),
            "hazard_invariants": _pass_fail(bool(hazards["ok"])),
            "flowguard_explorer": _pass_fail(bool(explorer["ok"])),
        },
        "counts": {
            "states": safe_graph["state_count"],
            "edges": safe_graph["edge_count"],
            "accepted": safe_graph["accepted_state_count"],
            "rejected": safe_graph["rejected_state_count"],
        },
        "scenario_outcomes": scenarios["results"],
        "missing_labels": safe_graph["missing_labels"],
        "risk_boundary": (
            "abstract next_action payload_contract visibility for "
            "record_startup_answers; no filesystem replay or production router "
            "mutation in this allowed write scope"
        ),
        "skipped_checks": {
            "conformance_replay": (
                "skipped_with_reason: abstract router action-contract model has "
                "no production replay adapter in the requested ownership scope"
            )
        },
        "adoption_note": {
            "flowguard_used": True,
            "workflow_or_risk_modeled": (
                "router action payload_contract exposure for startup answer "
                "interpretation nested required fields"
            ),
            "commands_expected": [
                "python -m py_compile simulations\\flowpilot_router_action_contract_model.py simulations\\run_router_action_contract_checks.py",
                "python simulations\\run_router_action_contract_checks.py --json-out simulations\\flowpilot_router_action_contract_results.json",
            ],
            "confidence_boundary": (
                "model-level confidence only; pair with router runtime tests from "
                "the main thread production-code change"
            ),
        },
    }

    if not ok:
        result["failure_details"] = {
            "safe_graph": safe_graph,
            "progress": progress,
            "scenario_outcomes": scenarios,
            "hazard_invariants": hazards,
            "flowguard_explorer": explorer,
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json-out",
        type=Path,
        default=RESULTS_PATH,
        help="Path for writing the JSON result payload.",
    )
    args = parser.parse_args()

    result = run_checks()
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
