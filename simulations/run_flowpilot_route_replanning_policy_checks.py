"""Run checks for the FlowPilot route replanning policy model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

import flowpilot_route_replanning_policy_model as model


RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_route_replanning_policy_results.json")

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.PLANNING_REPAIR_NODE_CREATED: "planning-phase issue used a repair node instead of route draft rewrite or ordinary node expansion",
    model.ROOT_REPAIR_BEFORE_CHILD_EXECUTION: "root planning created a repair node before any child execution",
    model.ORDINARY_NODE_MISSING_FIELDS: "added ordinary node lacks owner input output evidence or acceptance fields",
    model.CAPABILITY_CHANGE_WITHOUT_PRODUCT_CHECK: "product capability change lacks product-scope FlowGuard check",
    model.PROCESS_BEFORE_PRODUCT_FOR_CAPABILITY_CHANGE: "route-scope FlowGuard ran before product-scope FlowGuard for a product capability change",
    model.STRUCTURE_CHANGE_WITHOUT_PROCESS_CHECK: "route structure change lacks route-scope FlowGuard check",
    model.CHANGED_ROUTE_WITHOUT_REVIEWER: "changed route was used before Reviewer approval",
    model.NODE_ENTRY_REPAIR_BEFORE_WORK: "node-entry capability gap used a repair node before node work started",
    model.IN_PROGRESS_REPAIR_BEFORE_REVIEW_FAILURE: "in-progress capability gap used a repair node before reviewed failure",
    model.PM_HISTORICAL_DEFECT_FORCED_THROUGH_BLOCKER: "PM historical defect was forced through a fabricated blocker prerequisite",
    model.PM_HISTORICAL_DEFECT_WITHOUT_OBSERVATION: "PM historical defect repair lacks a structured defect observation",
    model.REPAIR_NODE_MISSING_FIELDS: "repair node lacks target reason input output evidence return or recheck fields",
    model.REPAIR_WITHOUT_STALE_RESET: "repair node lacks stale evidence reset",
    model.REPAIR_WITHOUT_MAINLINE_RETURN: "repair node lacks mainline return",
    model.ACTIVE_NODE_NOT_EXECUTABLE: "active node is not executable before route use",
    model.CONTROLLER_DIRECT_IMPLEMENTATION: "Controller performed product work before route gate",
    model.STALE_APPROVAL_REUSED_AFTER_CHANGE: "old approval was reused after route or product change",
    model.MILESTONE_ADVANCED_WITHOUT_RENEWAL: "top-level milestone advanced without mandatory plan renewal",
    model.MILESTONE_AUDIT_MISSING: "top-level milestone renewal lacks a complete current audit",
    model.MILESTONE_REMAINING_PLAN_INCOMPLETE: "top-level milestone renewal lacks a complete route to the final goal",
    model.MILESTONE_REMAINING_OBLIGATION_UNOWNED: "top-level milestone renewal leaves a remaining hard obligation without an owner",
    model.MILESTONE_AUDIT_CONTRACT_HASH_MISSING: "top-level milestone renewal is not bound to the frozen final-goal contract",
    model.MILESTONE_COMPLETED_PREFIX_UNBOUND: "top-level milestone renewal does not bind the cumulative completed prefix",
    model.MILESTONE_REMAINING_OWNER_NODE_UNBOUND: "top-level milestone renewal leaves a remaining gap without a submitted owner node",
    model.MILESTONE_CHECKER_IDENTITY_REUSED: "top-level milestone renewal reuses a checker identity for required evidence",
    model.MILESTONE_FLOWGUARD_BYPASSED: "top-level milestone renewal bypassed current FlowGuard review",
    model.MILESTONE_PM_ABSORPTION_BYPASSED: "top-level milestone renewal bypassed PM absorption of FlowGuard",
    model.MILESTONE_REVIEWER_BYPASSED: "top-level milestone renewal bypassed independent Reviewer approval",
    model.MILESTONE_SYSTEM_VALIDATION_BYPASSED: "top-level milestone renewal bypassed system validation",
    model.UNCHANGED_PLAN_BUMPED_ROUTE_VERSION: "unchanged remaining plan created a gratuitous route version",
    model.CHANGED_PLAN_KEPT_OLD_ROUTE_VERSION: "changed remaining plan kept the old active route version",
    model.CHANGED_PLAN_LOST_COMPLETED_PREFIX: "changed remaining plan discarded accepted milestone history",
    model.PREMATURE_TERMINAL_EMPTY_PLAN: "empty remaining plan was accepted before every hard obligation closed",
    model.RESUME_REUSED_HISTORICAL_MILESTONE_REVIEW: "resume reused a historical milestone review for the current gate",
    model.NESTED_CHILD_FORCED_GLOBAL_RENEWAL: "nested child closure started an unnecessary global milestone renewal",
    model.MILESTONE_REUSED_OLD_PLAN_WITHOUT_FRESH_WRITE: "top-level milestone renewal reused the old plan without freshly writing the complete remainder",
    model.REVIEWER_BLOCKED_MILESTONE_ADVANCED: "Reviewer-blocked milestone renewal advanced the frontier",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|phase={state.phase}|"
        f"issue={state.issue_kind}|origin={state.repair_trigger_origin}|"
        f"observation={state.structured_defect_observation_recorded}|"
        f"blocker_required={state.blocker_prerequisite_required}|"
        f"route_started={state.route_started}|"
        f"completed={state.completed_nodes}|node={state.current_node_kind}|"
        f"change={state.change_kind}|repair={state.repair_node_created}|"
        f"product_changed={state.product_capability_changed}|"
        f"product_fg={state.product_scope_flowguard_checked}|"
        f"process_fg={state.route_scope_flowguard_checked}|"
        f"reviewer={state.reviewer_approved_changed_route}|"
        f"active_exec={state.active_node_executable}|reason={state.terminal_reason}"
        f"|top_level={state.top_level_milestone}|audit={state.milestone_audit_complete}"
        f"|remaining_plan={state.remaining_plan_complete}|fresh_plan={state.fresh_remaining_plan_written}"
        f"|remaining_owned={state.remaining_obligations_owned}"
        f"|contract_current={state.milestone_contract_current}|prefix_bound={state.completed_prefix_bound}"
        f"|owner_nodes_bound={state.remaining_owner_nodes_bound}|checker_independent={state.checker_identities_independent}"
        f"|plan_changed={state.remaining_plan_changed}|milestone_fg={state.milestone_flowguard_checked}"
        f"|milestone_pm_absorb={state.milestone_pm_absorbed_flowguard}"
        f"|milestone_review={state.milestone_reviewer_approved}"
        f"|milestone_validation={state.milestone_system_validation_passed}"
        f"|route_version_changed={state.route_version_changed}"
        f"|prefix_preserved={state.completed_prefix_preserved}|empty_plan={state.empty_remaining_plan}"
        f"|all_closed={state.all_hard_obligations_closed}|frontier_advanced={state.frontier_advanced}"
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
    missing_labels = sorted(set(REQUIRED_LABELS) - set(graph["labels"]))
    accepted_scenarios = sorted(state.scenario for state in accepted)
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and set(accepted_scenarios) == set(model.VALID_SCENARIOS)
        and len(rejected) == len(model.NEGATIVE_SCENARIOS),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "accepted_scenarios": accepted_scenarios,
        "rejected_state_count": len(rejected),
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
