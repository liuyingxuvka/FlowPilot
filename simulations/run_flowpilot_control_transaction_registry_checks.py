"""Run checks for the FlowPilot control transaction registry model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_control_transaction_registry_model as model


RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_control_transaction_registry_results.json")

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.UNREGISTERED_TRANSACTION_TYPE: "transaction type is not registered",
    model.CONTRACT_PASS_EVENT_CAPABILITY_MISSING: "event capability was not validated or failed",
    model.EVENT_PASS_CONTRACT_MISSING: "contract binding is missing or mismatched",
    model.PACKET_AUTHORITY_MISSING: "packet authority role origin was not checked",
    model.COMPLETED_AGENT_INVALID: "completed agent identity is not authorized for role",
    model.COLLAPSED_REPAIR_OUTCOMES: "repair outcomes are not three distinct events",
    model.REPAIR_WITHOUT_TRANSACTION: "repair transaction is required before commit",
    model.PARENT_REPAIR_LEAF_EVENT: "parent repair targets a leaf-only event",
    model.PARTIAL_COMMIT_TARGETS: "transaction commit targets are incomplete",
    model.ACTIVE_BLOCKER_MARKED_GREEN: "active blocker cannot be marked safe to continue",
    model.LEGACY_BAD_TRANSACTION_CONTINUES: "invalid legacy transaction was not quarantined",
    model.REGISTRY_REFERENCE_MISSING: "control transaction registry references missing contract or event",
    model.ROUTE_MUTATION_WITHOUT_STALE_POLICY: "route mutation omitted stale-evidence policy",
    model.REVIEWER_NON_SUCCESS_USES_SUCCESS_EVENT: "non-success outcome uses a success-only event",
    model.ATOMIC_COMMIT_TARGET_MISSING: "atomic commit target is missing",
    model.CONTROL_PLANE_REISSUE_WITHOUT_DELIVERY_AUTHORITY: "control-plane reissue lacks delivery authority",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|type={state.transaction_type}|"
        f"registry={state.registry_row_present},{state.registry_references_exist}|"
        f"contract={state.contract_required},{state.contract_binding_ok}|"
        f"event={state.event_capability_required},{state.event_capability_ok}|"
        f"packet={state.packet_authority_required},{state.role_origin_checked},"
        f"{state.completed_agent_id_belongs_to_role},{state.completed_agent_id_is_role_key}|"
        f"repair={state.repair_transaction_required},{state.repair_transaction_present},"
        f"{state.outcome_policy},{state.outcome_events_distinct},{state.non_success_uses_success_event}|"
        f"parent={state.parent_repair},{state.repair_target_is_leaf_event}|"
        f"commit={state.commit_targets}|legacy={state.legacy_transaction},"
        f"{state.legacy_transaction_invalid},{state.legacy_quarantined}|"
        f"reissue={state.control_plane_reissue},{state.reissue_delivery_authority_present},"
        f"{state.original_event_flag_currently_set}|reason={state.terminal_reason}"
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
        transaction_failures = model.control_transaction_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in transaction_failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": transaction_failures,
            "state": state.__dict__,
        }
        if not detected:
            failures.append(f"{name}: expected failure containing {expected!r}")
    return {"ok": not failures, "hazards": hazards, "failures": failures}


def _architecture_candidate() -> dict[str, object]:
    return {
        "name": "control_transaction_registry",
        "principles": [
            "Every FlowPilot control write is a registered transaction.",
            "Contract registry, event capability registry, repair transaction records, and packet authority are sub-registries.",
            "The registry authorizes commits, not only event names.",
            "Legacy invalid transactions are quarantined instead of replayed.",
            "Accepted transactions commit required state surfaces together.",
        ],
        "minimum_runtime_change_set": [
            "Add runtime_kit/control_transaction_registry.json.",
            "Add source checks that validate transaction rows against existing Router events and contract ids.",
            "Use the registry in the PM control-blocker repair path before writing repair transaction state.",
            "Expose packet authority as a required transaction fact for result absorption.",
            "Teach the mesh that invalid legacy transactions block current-run continuation.",
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
