"""Run FlowGuard checks for Recovery Supervisor break-glass."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_recovery_supervisor_model as model


RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_recovery_supervisor_results.json")

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"open_recovery_transaction_{scenario}" for scenario in model.SCENARIOS]
    + [
        "classify_family_from_metadata_metadata_only_control_plane_repair",
        "grant_scoped_body_access_scoped_body_access_control_plane_repair",
    ]
    + [f"record_same_family_repair_{scenario}" for scenario in model.SCENARIOS]
    + [f"reinject_controller_core_{scenario}" for scenario in model.SCENARIOS]
    + [f"close_recovery_transaction_{scenario}" for scenario in model.SCENARIOS]
    + [f"return_to_normal_controller_{scenario}" for scenario in model.SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    "normal_controller_reads_body": "normal Controller read a sealed body",
    "recovery_reads_unscoped_body": "Recovery Supervisor read a body without a scoped grant",
    "body_access_without_role_lane_failure": "scoped body access grant opened without role-lane failure",
    "closed_without_family_repair": "recovery progressed before blocker family repair proof was complete",
    "closed_without_reinjection": "recovery closed before Controller core reinjection",
    "normal_resumed_with_open_transaction": "normal Controller resumed while recovery transaction was still open",
    "historical_blocker_reactivated": "historical blocker was reactivated as current",
    "recovery_approved_gate": "Recovery Supervisor approved a route gate",
    "recovery_mutated_route": "Recovery Supervisor mutated route authority",
    "recovery_did_target_project_work": "Recovery Supervisor performed target project work",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|normal={state.normal_controller_active}|"
        f"supervisor={state.recovery_supervisor_active}|tx={state.recovery_transaction_open}|"
        f"family={state.blocker_family_classified},{state.flowguard_same_family_proof_recorded}|"
        f"body={state.body_access_needed},{state.scoped_body_access_grant_recorded}|"
        f"reinject={state.old_controller_generation_invalidated},{state.controller_core_reinjected}|"
        f"returned={state.returned_to_normal_controller}"
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
    successes = sorted(state.scenario for state in states if model.is_success(state))
    missing_labels = sorted(set(REQUIRED_LABELS) - set(graph["labels"]))
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and set(successes) == set(model.SCENARIOS),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "success_scenarios": successes,
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"][:5],
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
    misses: list[str] = []
    for name, state in model.hazard_states().items():
        failures = model.policy_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": failures,
        }
        if not detected:
            misses.append(f"{name}: expected failure containing {expected!r}")
    return {"ok": not misses, "hazards": hazards, "failures": misses}


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    flowguard = _flowguard_report()
    hazards = _hazard_report()
    result = {
        "safe_graph": safe_graph,
        "flowguard_explorer": flowguard,
        "hazard_checks": hazards,
    }
    result["ok"] = all(section.get("ok", False) for section in (safe_graph, flowguard, hazards))
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
