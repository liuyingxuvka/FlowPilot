"""Run checks for the FlowPilot Controller break-glass repair model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_controller_break_glass_model as model


RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_controller_break_glass_results.json")

REQUIRED_LABELS = tuple(
    [f"select_{name}" for name in model.SCENARIOS]
    + [f"open_incident_{name}" for name in model.VALID_SCENARIOS]
    + [f"return_to_normal_{name}" for name in model.VALID_SCENARIOS]
    + [f"disclose_break_glass_{name}" for name in model.VALID_SCENARIOS]
    + [f"accept_{name}" for name in model.VALID_SCENARIOS]
    + [f"reject_{name}" for name in model.NEGATIVE_SCENARIOS]
    + [f"record_patch_{name}" for name in model.PATCH_SCENARIOS]
    + [f"record_patch_validation_{name}" for name in model.PATCH_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    "ordinary_project_bug_break_glass": "ordinary project defect used break-glass",
    "normal_pm_repair_available_break_glass": "normal PM repair lane was available",
    "missing_normal_lane_check": "normal repair lanes were checked",
    "missing_playbook_read": "without reading the playbook",
    "missing_incident_record": "without an incident record",
    "missing_recovery_transaction": "lacked a recovery transaction",
    "missing_patch_record": "without a patch record",
    "missing_patch_validation": "without closed validation",
    "patch_validation_not_run": "validation stayed not_run",
    "missing_return_to_normal": "did not return to normal Controller flow",
    "missing_final_disclosure": "not disclosed in final reporting",
    "controller_reads_sealed_body": "read a sealed packet or result body",
    "controller_does_project_work": "performed target-project work",
    "controller_approves_gate": "approved a gate",
    "controller_mutates_route": "mutated the route",
    "controller_changes_acceptance": "changed acceptance criteria",
    "controller_publishes": "published or deployed",
    "controller_handles_secret": "handled secrets",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|control={state.flowpilot_control_failure}|"
        f"ordinary={state.ordinary_project_defect}|normal_available={state.normal_repair_available}|"
        f"lanes={state.normal_lanes_checked}|playbook={state.playbook_read}|"
        f"incident={state.incident_recorded}|patch_used={state.patch_used}|"
        f"patch={state.patch_recorded}|returned={state.returned_to_normal_flow}|"
        f"disclosed={state.final_disclosed}"
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
        failures = model.policy_failures(state)
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
    accepted = sorted(state.scenario for state in terminal if state.status == "accepted")
    rejected = sorted(state.scenario for state in terminal if state.status == "rejected")
    missing_labels = sorted(set(REQUIRED_LABELS) - set(graph["labels"]))
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and set(accepted) == set(model.VALID_SCENARIOS)
        and set(rejected) == set(model.NEGATIVE_SCENARIOS),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "accepted_scenarios": accepted,
        "rejected_scenarios": rejected,
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
            if source not in can_reach_terminal and any(target in can_reach_terminal for _label, target in outgoing):
                can_reach_terminal.add(source)
                changed = True
    stuck = [_state_id(state) for idx, state in enumerate(states) if idx not in terminal and not edges[idx]]
    cannot_reach_terminal = [_state_id(state) for idx, state in enumerate(states) if idx not in can_reach_terminal]
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


def _hazard_report() -> dict[str, object]:
    hazards: dict[str, object] = {}
    failures: list[str] = []
    for name, state in model.hazard_states().items():
        policy_failures = model.policy_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in policy_failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": policy_failures,
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
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
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
