"""Run checks for the FlowPilot PM package-absorption model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

import flowpilot_pm_package_absorption_model as model


RESULTS_PATH = Path(__file__).resolve().with_name(
    "flowpilot_pm_package_absorption_results.json"
)

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.RAW_WORKER_RESULT_RELAYED_TO_REVIEWER: "raw PM-issued worker result reached reviewer before PM gate package",
    model.FORMAL_EVIDENCE_FROM_UNDISPOSITIONED_RESULT: "formal evidence used a worker result without PM absorbed disposition",
    model.REVIEWER_STARTED_WITHOUT_PM_GATE_PACKAGE: "reviewer gate started without a PM-built formal gate package",
    model.NODE_COMPLETION_WITHOUT_REVIEWER_GATE: "PM completed a node without PM disposition and reviewer node-completion gate",
    model.CRITICAL_REVIEWER_GATE_REMOVED: "critical PM route/node/evidence/closure decision bypassed reviewer gate",
    model.RESUME_RESULT_DIRECT_TO_REVIEWER: "raw PM-issued worker result reached reviewer before PM gate package",
    model.ORDINARY_EVIDENCE_DECISION_WITHOUT_GATE: "critical PM route/node/evidence/closure decision bypassed reviewer gate",
    model.RETIRED_MATERIAL_AUTHORITY_USED_AS_CURRENT: "retired material-specific package or gate used as current authority",
    model.CONTROLLER_READS_SEALED_BODY: "Controller read sealed packet/result body",
    model.RETIRED_REVIEWER_RELAY_USED_AS_CURRENT_ACCEPTANCE: "PM-issued worker result did not return to project_manager",
    model.PM_FORWARDED_RAW_PACKAGE_TO_REVIEWER: "raw PM-issued worker result reached reviewer before PM gate package",
    model.PM_FORMAL_PACKAGE_RELEASE_WITHOUT_IDENTITY: "reviewer gate started without PM disposition release and formal gate package identity",
    model.PM_DISPOSITION_WITHOUT_RUNTIME_CONTRACT: "PM package disposition was not bound to the role-output runtime contract",
    model.PM_DISPOSITION_HALF_WRITTEN_ACCEPTED: "PM package disposition was not committed as one registered control transaction",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|pkg={state.package_kind}|"
        f"gate={state.gate_kind}|pm={state.result_relayed_to_pm},"
        f"{state.pm_disposition_recorded},{state.pm_disposition},"
        f"{state.pm_disposition_runtime_contract_bound},"
        f"{state.pm_disposition_transaction_committed},"
        f"{state.pm_disposition_replay_verified},"
        f"{state.pm_disposition_half_written}|"
        f"pm_gate={state.pm_gate_package_written}|review={state.reviewer_gate_started},"
        f"{state.reviewer_gate_passed}|raw={state.reviewer_received_raw_worker_result}|"
        f"formal_release={state.pm_gate_package_released_by_disposition},"
        f"{state.pm_gate_package_identity_recorded}|"
        f"decision={state.route_or_node_decision_recorded}|node={state.node_completion_recorded}|"
        f"reason={state.terminal_reason}"
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
        for source, outgoing in enumerate(edges):
            if source not in can_reach_terminal and any(
                target in can_reach_terminal for _label, target in outgoing
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
        "reachability_failures": [
            failure.message for failure in report.reachability_failures
        ],
    }


def _hazard_report() -> dict[str, object]:
    hazards: dict[str, object] = {}
    failures: list[str] = []
    for name, state in model.hazard_states().items():
        scenario_failures = model.package_absorption_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in scenario_failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": scenario_failures,
        }
        if not detected:
            failures.append(f"{name}: expected failure containing {expected!r}")
    return {"ok": not failures, "hazards": hazards, "failures": failures}


def _retired_material_surface_absence_report(
    graph: dict[str, Any],
) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    accepted = [state for state in states if state.status == "accepted"]
    expected_positive_package_kinds = {
        model.PACKAGE_CURRENT_NODE,
        model.PACKAGE_RESEARCH,
        model.PACKAGE_PM_ROLE_WORK,
    }
    observed_positive_package_kinds = {
        state.package_kind
        for state in accepted
        if state.package_kind != model.PACKAGE_NONE
    }
    retired_package_acceptances = sorted(
        state.scenario
        for state in accepted
        if state.package_kind == model.RETIRED_PACKAGE_MATERIAL_SCAN
    )
    retired_gate_acceptances = sorted(
        state.scenario
        for state in accepted
        if state.gate_kind == model.RETIRED_GATE_MATERIAL_SUFFICIENCY
    )
    retired_named_valid_scenarios = sorted(
        scenario for scenario in model.VALID_SCENARIOS if "material" in scenario
    )
    negative_probe_present = (
        model.RETIRED_MATERIAL_AUTHORITY_USED_AS_CURRENT in model.NEGATIVE_SCENARIOS
    )
    ok = (
        observed_positive_package_kinds == expected_positive_package_kinds
        and not retired_package_acceptances
        and not retired_gate_acceptances
        and not retired_named_valid_scenarios
        and negative_probe_present
    )
    return {
        "ok": ok,
        "expected_positive_package_kinds": sorted(expected_positive_package_kinds),
        "observed_positive_package_kinds": sorted(observed_positive_package_kinds),
        "retired_package_acceptances": retired_package_acceptances,
        "retired_gate_acceptances": retired_gate_acceptances,
        "retired_named_valid_scenarios": retired_named_valid_scenarios,
        "negative_probe_present": negative_probe_present,
        "claim_boundary": (
            "This proves the PM package-absorption model accepts only research, "
            "current-node, or PM role-work package owners and exercises retired "
            "material authority only as a rejected hazard."
        ),
    }


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _hazard_report()
    retired_material_surface_absence = _retired_material_surface_absence_report(
        graph
    )
    result = {
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "retired_material_surface_absence": retired_material_surface_absence,
    }
    result["ok"] = all(
        section.get("ok", False)
        for section in (
            safe_graph,
            progress,
            explorer,
            hazards,
            retired_material_surface_absence,
        )
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
