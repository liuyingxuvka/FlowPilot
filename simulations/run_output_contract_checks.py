"""Run checks for the FlowPilot output-contract propagation model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_output_contract_model as model


REQUIRED_LABELS = (
    "pm_selects_system_contract_by_task_family",
    "packet_embeds_selected_contract",
    "packet_omits_selected_contract",
    "packet_embeds_mismatched_contract",
    "packet_embeds_contract_with_hidden_router_requirement",
    "packet_embeds_contract_with_missing_required_body_field",
    "packet_omits_report_contract_delivery",
    "packet_embeds_body_field_in_envelope",
    "controller_relays_envelope_only",
    "role_receives_relayed_packet",
    "final_reporter_receives_report_contract",
    "final_reporter_missing_report_contract",
    "role_self_check_passes_body_envelope_contract",
    "role_self_check_rejects_missing_contract",
    "role_self_check_rejects_mismatched_contract",
    "role_self_check_rejects_missing_required_body_field",
    "role_self_check_rejects_missing_report_contract_delivery",
    "role_self_check_rejects_forbidden_envelope_body_field",
    "router_accepts_self_checked_contract",
    "router_rejects_missing_contract",
    "router_rejects_mismatched_contract",
    "router_rejects_hidden_router_requirement_absent_from_contract",
    "router_rejects_missing_required_body_field",
    "router_rejects_missing_report_contract_delivery",
    "router_rejects_forbidden_envelope_body_field",
)

HAZARD_EXPECTED_FAILURES = {
    model.MISSING_CONTRACT: "missing or mismatched propagated contract",
    model.MISMATCHED_CONTRACT: "missing or mismatched propagated contract",
    model.HIDDEN_ROUTER_REQUIREMENT: "hidden router requirement absent from contract",
    model.MISSING_REQUIRED_BODY_FIELD: "missing required body field",
    model.MISSING_REPORT_CONTRACT_DELIVERY: "final reporter received report contract",
    model.FORBIDDEN_ENVELOPE_BODY_FIELD: "forbidden envelope body field",
    "controller_reads_body": "Controller relayed or read packet body content",
    "controller_relays_body_content": "Controller relayed or read packet body content",
    "accept_without_role_self_check": "role self-check passed",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|family={state.task_family}|"
        f"selected={state.selected_contract_id}|packet={state.packet_contract_id}|"
        f"envelope={state.envelope_contract_id}|body={state.body_contract_id}|"
        f"report_contract_delivery={state.final_reporter_received_report_contract}|"
        f"role_check={state.role_self_check}:{state.role_self_check_reason}|"
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


def _check_safe_graph(graph: dict[str, object]) -> dict[str, object]:
    labels = set(graph["labels"])
    states: list[model.State] = graph["states"]
    terminals = [state for state in states if model.is_terminal(state)]
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    accepted = [state for state in terminals if state.status == "accepted"]
    rejected = [state for state in terminals if state.status == "rejected"]
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and len(accepted) == len(model.VALID_SCENARIOS)
        and len(rejected) == len(model.NEGATIVE_SCENARIOS),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "accepted_state_count": len(accepted),
        "rejected_state_count": len(rejected),
        "missing_labels": missing_labels,
        "invariant_failure_count": len(graph["invariant_failures"]),
        "invariant_failures": graph["invariant_failures"][:5],
    }


def _check_negative_scenarios(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    terminal_by_scenario = {
        state.scenario: state
        for state in states
        if model.is_terminal(state) and state.scenario != "unset"
    }
    scenario_results: dict[str, str] = {}
    failures: list[str] = []
    for scenario, expected_reason in model.NEGATIVE_EXPECTED_REJECTIONS.items():
        terminal = terminal_by_scenario.get(scenario)
        if terminal is None:
            failures.append(f"{scenario}: no terminal state")
            scenario_results[scenario] = "missing"
            continue
        if (
            terminal.status != "rejected"
            or terminal.router_rejection_reason != expected_reason
        ):
            failures.append(
                f"{scenario}: expected rejection {expected_reason}, got "
                f"{terminal.status}:{terminal.router_rejection_reason}"
            )
        scenario_results[scenario] = (
            f"{terminal.status}:{terminal.router_rejection_reason}"
        )

    for scenario in model.VALID_SCENARIOS:
        terminal = terminal_by_scenario.get(scenario)
        if terminal is None:
            failures.append(f"{scenario}: no terminal state")
            scenario_results[scenario] = "missing"
            continue
        if terminal.status != "accepted":
            failures.append(f"{scenario}: expected acceptance, got {terminal.status}")
        scenario_results[scenario] = terminal.status

    return {
        "ok": not failures,
        "results": scenario_results,
        "failures": failures,
    }


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
        "samples": (stuck + cannot_reach_terminal)[:5],
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
        required_labels=REQUIRED_LABELS,
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
    results: dict[str, str] = {}
    failures: list[str] = []
    for name, state in model.hazard_states().items():
        invariant_failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in invariant_failures)
        results[name] = "detected" if detected else "missed"
        if not detected:
            failures.append(f"{name}: expected failure containing {expected!r}")
    return {
        "ok": not failures,
        "results": results,
        "failures": failures,
    }


def _pass_fail(ok: bool) -> str:
    return "pass" if ok else "fail"


def run_checks() -> dict[str, object]:
    graph = _build_reachable_graph()
    safe_graph = _check_safe_graph(graph)
    progress = _check_progress(graph)
    negative_scenarios = _check_negative_scenarios(graph)
    hazards = _check_hazards()
    explorer = _run_flowguard_explorer()
    ok = all(
        bool(check["ok"])
        for check in (safe_graph, progress, negative_scenarios, hazards, explorer)
    )

    result: dict[str, object] = {
        "ok": ok,
        "checks": {
            "safe_graph": _pass_fail(bool(safe_graph["ok"])),
            "progress": _pass_fail(bool(progress["ok"])),
            "negative_scenarios": _pass_fail(bool(negative_scenarios["ok"])),
            "hazard_invariants": _pass_fail(bool(hazards["ok"])),
            "flowguard_explorer": _pass_fail(bool(explorer["ok"])),
        },
        "counts": {
            "states": safe_graph["state_count"],
            "edges": safe_graph["edge_count"],
            "accepted": safe_graph["accepted_state_count"],
            "rejected": safe_graph["rejected_state_count"],
        },
        "negative_scenarios": negative_scenarios["results"],
        "missing_labels": safe_graph["missing_labels"],
        "skipped_checks": {
            "conformance_replay": (
                "skipped_with_reason: abstract output-contract model has no "
                "production replay adapter in the requested new-file scope"
            )
        },
    }

    if not ok:
        result["failure_details"] = {
            "safe_graph": safe_graph,
            "progress": progress,
            "negative_scenarios": negative_scenarios,
            "hazard_invariants": hazards,
            "flowguard_explorer": explorer,
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Optional path for writing the JSON result payload.",
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
