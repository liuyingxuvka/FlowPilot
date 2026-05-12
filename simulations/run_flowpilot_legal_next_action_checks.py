"""Run checks for the FlowPilot legal next-action policy model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_legal_next_action_model as model


RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_legal_next_action_results.json")

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.PM_DECISION_WITHOUT_LEGAL_ACTIONS: "PM decision was requested before legal next actions were computed",
    model.PARENT_CLOSURE_OFFERED_BEFORE_CHILD_CHAIN_CLOSED: "parent closure action was offered before child chain closed",
    model.SEGMENT_DECISION_OFFERED_BEFORE_PARENT_REPLAY_PASS: "parent segment decision was offered before parent backward replay passed",
    model.DIRECT_CHILD_DONE_USED_AS_SUBTREE_DONE: "direct child completion was used as subtree completion",
    model.STALE_CHILD_COMPLETION_AUTHORITY: "stale child completion authority was used",
    model.PM_SELECTED_ACTION_OUTSIDE_LEGAL_SET: "PM selected an action outside the Router legal action set",
    model.EVENT_REGISTERED_BUT_ACTION_ILLEGAL: "registered event was allowed while route action predicate was false",
    model.STALE_LEGAL_ACTION_SNAPSHOT_COMMITTED: "stale legal-action snapshot was committed",
    model.POLICY_REGISTRY_REFERENCE_MISSING: "route action policy references missing contract, event, or transaction",
    model.ACTION_NODE_KIND_MISMATCH: "route action is incompatible with active node kind",
    model.ROUTE_MUTATION_WITHOUT_STALE_EVIDENCE_POLICY: "route mutation omitted stale-evidence policy or parent replay rerun",
    model.TERMINAL_CLOSURE_OFFERED_WITH_OPEN_ROUTE_WORK: "terminal closure was offered with open route work",
    model.PM_WORK_REQUEST_BYPASSES_ROUTE_ACTION_POLICY: "PM work-request channel bypassed route-action policy",
    model.LEGAL_ACTION_PARTIAL_COMMIT: "legal action commit targets are incomplete",
    model.MESH_GREEN_WITHOUT_LEGAL_ACTION_PROJECTION: "mesh green claim lacked legal-action projection",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|action={state.pm_selected_action}|"
        f"legal={state.legal_actions_computed},{state.legal_actions_include_selected},"
        f"{state.legal_action_snapshot_current}|"
        f"policy={state.policy_row_present},{state.policy_references_exist},"
        f"{state.event_registered},{state.output_contract_registered},"
        f"{state.control_transaction_registered},{state.action_predicate_true}|"
        f"node={state.active_node_kind},{state.action_node_kind_ok}|"
        f"child={state.child_frontier_entered},{state.child_leaf_executed},"
        f"{state.direct_child_completed},{state.descendant_leaves_completed},"
        f"{state.effective_children_all_completed},{state.child_completion_ledger_current},"
        f"{state.stale_route_status_used}|"
        f"replay={state.parent_backward_replay_passed},{state.parent_segment_decision_continue}|"
        f"mutation={state.route_mutation_requested},{state.stale_evidence_policy_applied},"
        f"{state.affected_parent_replay_rerun_required}|"
        f"terminal={state.open_route_nodes},{state.active_blocker_present},"
        f"{state.stale_evidence_present}|"
        f"commit={state.commit_attempted},{state.commit_targets_complete},"
        f"{state.route_frontier_ledger_versions_match_at_commit}|"
        f"mesh={state.legal_action_projection_available_to_mesh},{state.mesh_green_claimed}|"
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
            if source not in can_reach_terminal and any(target in can_reach_terminal for _label, target in outgoing):
                can_reach_terminal.add(source)
                changed = True
    stuck = [_state_id(state) for idx, state in enumerate(states) if idx not in terminal and not edges[idx]]
    cannot_reach_terminal = [_state_id(state) for idx, state in enumerate(states) if idx not in can_reach_terminal]
    return {
        "ok": not stuck and not cannot_reach_terminal,
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
        legal_action_failures = model.legal_action_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in legal_action_failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": legal_action_failures,
            "state": state.__dict__,
        }
        if not detected:
            failures.append(f"{name}: expected failure containing {expected!r}")
    return {"ok": not failures, "hazards": hazards, "failures": failures}


def _intended_report() -> dict[str, object]:
    failures: dict[str, list[str]] = {}
    for scenario, state in model.intended_plan_states().items():
        plan_failures = model.legal_action_failures(state)
        if plan_failures:
            failures[scenario] = plan_failures
    return {
        "ok": not failures,
        "failures": failures,
        "accepted_plan": sorted(model.VALID_SCENARIOS),
    }


def _candidate_fix_plan() -> dict[str, object]:
    return {
        "name": "legal_next_actions_policy",
        "minimum_runtime_change_set": [
            "Add a compact route-action policy registry that references existing event, contract, and transaction rows.",
            "Compute legal_next_actions from route/frontier/ledger/flags before PM route-movement decisions.",
            "Include legal_next_actions and blocking reasons in PM decision payload context.",
            "Reject PM submitted route movement events whose selected action is outside the current legal set.",
            "Re-check legal actions immediately before route/frontier/ledger commits.",
            "Expose legal-action projection to the model mesh before current-run continuation claims.",
        ],
        "implementation_order": [
            "registry",
            "compute helper",
            "PM decision wait payload",
            "event submission validator",
            "commit validator",
            "model mesh projection",
        ],
    }


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    reports = {
        "safe_graph": _safe_graph_report(graph),
        "progress": _progress_report(graph),
        "flowguard": _flowguard_report(),
        "hazards": _hazard_report(),
        "intended": _intended_report(),
    }
    ok = all(report.get("ok") for report in reports.values())
    return {
        "ok": ok,
        "model": "flowpilot_legal_next_action",
        "covered_risks": sorted(model.NEGATIVE_SCENARIOS),
        "candidate_fix_plan": _candidate_fix_plan(),
        **reports,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args(argv)
    result = run_checks()
    args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"ok={result['ok']} results={args.json_out}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
