"""Run checks for the current-contract FlowPilot repair transaction model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard.explorer import Explorer

import flowpilot_repair_transaction_model as model


REQUIRED_LABELS = (
    "reviewer_blocker_detected_node_acceptance_plan",
    "reviewer_blocker_detected_current_node_dispatch",
    "reviewer_blocker_detected_node_result",
    "router_registers_blocker_with_origin_and_failure_events",
    "pm_records_model_miss_triage_for_modelable_blocker",
    "pm_requests_flowguard_operator_same_class_model",
    "flowguard_operator_reports_same_class_findings",
    "flowguard_operator_compares_minimal_repair_candidates",
    "pm_selects_repair_after_model_miss_review",
    "pm_records_repair_decision_without_self_resolution",
    "router_opens_current_contract_repair_transaction",
    "router_validates_and_queues_safe_operation_replay",
    "router_atomically_commits_current_repair_and_outcome_table",
    "flowguard_operator_checks_current_repair_effect",
    "reviewer_recheck_requested_after_current_commit",
    "reviewer_recheck_allows_dispatch",
    "reviewer_recheck_returns_followup_blocker",
    "reviewer_recheck_returns_protocol_blocker",
    "router_refreshes_current_authorities_after_repair_outcome",
)


HAZARD_EXPECTED_FAILURES = {
    "router_blocker_missing_origin": "router blocker registration lacks origin or nonterminal repair events",
    "node_acceptance_plan_without_pm_lane": "reviewer block kind node_acceptance_plan is not accepted end-to-end by PM model-miss repair",
    "current_node_dispatch_missing_model_miss_card_support": "reviewer block kind current_node_dispatch is not accepted end-to-end by PM model-miss repair",
    "retired_material_dispatch_repair_lane_reintroduced": "reviewer block kind material_dispatch is not accepted end-to-end by PM model-miss repair",
    "pm_decision_self_resolves_blocker": "PM repair decision resolved the blocker by itself",
    "post_decision_wait_exposed_before_pm_flag_visible": "post-decision repair wait events were exposed before the PM repair decision flag was visible",
    "repair_decision_without_model_miss_triage": "PM selected repair before recording model-miss triage",
    "modelable_repair_without_flowguard_report": "modelable repair was selected without FlowGuard operator findings and candidate comparison",
    "repair_commits_without_transaction_identity": "PM repair decision advanced without a durable repair transaction",
    "retired_packet_reissue_accepted": "repair transaction committed with unsupported executable plan kind",
    "operation_replay_without_safe_recorded_action": "repair transaction committed without concrete producer, queued action, Router handler, or terminal stop",
    "controller_repair_packet_unbounded": "repair transaction committed without concrete producer, queued action, Router handler, or terminal stop",
    "role_reissue_without_current_producer": "repair transaction committed without concrete producer, queued action, Router handler, or terminal stop",
    "await_existing_event_without_producer": "repair transaction committed without concrete producer, queued action, Router handler, or terminal stop",
    "router_reconcile_without_handler": "repair transaction committed without concrete producer, queued action, Router handler, or terminal stop",
    "terminal_stop_without_terminal_record": "repair transaction committed without concrete producer, queued action, Router handler, or terminal stop",
    "transaction_commits_without_plan_validation": "repair transaction committed without executable plan validation",
    "transaction_commits_without_outcome_table": "repair transaction committed without a complete current outcome table",
    "success_only_outcome_table": "repair transaction committed without a complete current outcome table",
    "parent_repair_rerun_targets_current_node_packet": "repair rerun target event incompatible with active node kind",
    "collapsed_repair_outcomes_on_business_event": "repair outcome table collapsed success blocker and protocol-blocker events",
    "routable_outcome_missing_event_identity": "repair outcome table lacks explicit event identity",
    "reviewer_recheck_before_current_commit": "reviewer recheck was requested before current repair commit, outcome table, and required model check",
    "reviewer_recheck_before_post_repair_model_check": "reviewer recheck was requested before current repair commit, outcome table, and required model check",
    "reviewer_blocker_unroutable": "reviewer recheck outcome was not accepted by router",
    "successful_terminal_without_authority_refresh": "terminal repair state did not refresh transaction index, frontier, and display",
    "controller_no_next_action_without_followup_blocker": "controller reached no legal next action without a current follow-up blocker or terminal stop",
}


def _build_reachable_graph() -> dict[str, object]:
    start = model.initial_state()
    queue: deque[model.State] = deque([start])
    seen: set[model.State] = {start}
    edges: list[tuple[model.State, str, model.State]] = []
    labels: set[str] = set()
    invariant_failures: list[dict[str, object]] = []

    while queue:
        state = queue.popleft()
        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append(
                {"state": state.__dict__, "failures": failures}
            )
            continue
        for label, nxt in model.next_states(state):
            labels.add(label)
            edges.append((state, label, nxt))
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)

    terminals = {state for state in seen if model.is_terminal(state)}
    return {
        "states": seen,
        "edges": edges,
        "labels": labels,
        "terminals": terminals,
        "invariant_failures": invariant_failures,
    }


def _safe_graph_report(graph: dict[str, object]) -> dict[str, object]:
    states = graph["states"]
    edges = graph["edges"]
    labels = graph["labels"]
    terminals = graph["terminals"]
    invariant_failures = graph["invariant_failures"]
    missing = sorted(set(REQUIRED_LABELS) - set(labels))
    success_count = sum(1 for state in terminals if model.is_success(state))
    blocked_count = len(terminals) - success_count
    return {
        "ok": not invariant_failures and not missing and success_count > 0 and blocked_count > 0,
        "state_count": len(states),
        "edge_count": len(edges),
        "success_state_count": success_count,
        "blocked_state_count": blocked_count,
        "labels": sorted(labels),
        "missing_labels": missing,
        "invariant_failures": invariant_failures,
    }


def _progress_report(graph: dict[str, object]) -> dict[str, object]:
    states: set[model.State] = graph["states"]
    edges: list[tuple[model.State, str, model.State]] = graph["edges"]
    terminals: set[model.State] = graph["terminals"]
    reverse: dict[model.State, set[model.State]] = {state: set() for state in states}
    outgoing: dict[model.State, int] = {state: 0 for state in states}
    for source, _label, target in edges:
        reverse.setdefault(target, set()).add(source)
        outgoing[source] = outgoing.get(source, 0) + 1

    can_reach_terminal = set(terminals)
    queue: deque[model.State] = deque(terminals)
    while queue:
        target = queue.popleft()
        for source in reverse.get(target, set()):
            if source not in can_reach_terminal:
                can_reach_terminal.add(source)
                queue.append(source)

    cannot_reach = [state for state in states if state not in can_reach_terminal]
    stuck = [
        state
        for state in states
        if state not in terminals and outgoing.get(state, 0) == 0
    ]
    return {
        "ok": not cannot_reach and not stuck,
        "initial_can_reach_success": any(model.is_success(state) for state in terminals),
        "cannot_reach_terminal_count": len(cannot_reach),
        "cannot_reach_terminal_samples": [state.__dict__ for state in cannot_reach[:5]],
        "stuck_state_count": len(stuck),
        "stuck_state_samples": [state.__dict__ for state in stuck[:5]],
    }


def _loop_report(graph: dict[str, object]) -> dict[str, object]:
    nonprogress = [
        {
            "label": label,
            "source_steps": source.steps,
            "target_steps": target.steps,
        }
        for source, label, target in graph["edges"]
        if target.steps <= source.steps and not model.is_terminal(target)
    ]
    return {
        "ok": not nonprogress,
        "nonprogress_edge_count": len(nonprogress),
        "nonprogress_edge_samples": nonprogress[:10],
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
        "reachability_failures": [
            failure.message for failure in report.reachability_failures
        ],
    }


def _check_hazards() -> dict[str, object]:
    hazards: dict[str, object] = {}
    ok = True
    states = model.hazard_states()
    missing_expectations = sorted(set(states) - set(HAZARD_EXPECTED_FAILURES))
    stale_expectations = sorted(set(HAZARD_EXPECTED_FAILURES) - set(states))
    for name, state in states.items():
        failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES.get(name, "")
        detected = bool(expected) and any(expected in failure for failure in failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": failures,
            "state": state.__dict__,
        }
        ok = ok and detected
    return {
        "ok": ok and not missing_expectations and not stale_expectations,
        "hazards": hazards,
        "missing_expectations": missing_expectations,
        "stale_expectations": stale_expectations,
    }


def _architecture_candidate() -> dict[str, object]:
    return {
        "name": "current_contract_repair_transaction",
        "principles": [
            "PM explanation fields never create Router work by themselves.",
            "One supported repair_transaction.plan_kind owns execution authority.",
            "Every commit carries a concrete producer, queued action, Router handler, or terminal stop.",
            "The PM decision flag, transaction, outcome table, and follow-up wait share one ordered current-state boundary.",
            "Independent FlowGuard and Reviewer checks consume the current repair effect before success resumes the main flow.",
            "Retired replacement-packet authority is rejected rather than translated.",
        ],
        "implementation_map": [
            "Validate plan_kind and plan-specific execution evidence before commit.",
            "Reject packet_reissue and all replacement-packet fields at the current runtime boundary.",
            "Publish distinct success, blocker, and protocol-blocker event identities.",
            "Refresh repair transaction index, frontier, and display from the accepted current outcome.",
        ],
    }


def run_checks(*, json_out_requested: bool = False) -> dict[str, object]:
    graph = _build_reachable_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    loop = _loop_report(graph)
    explorer = _flowguard_report()
    hazards = _check_hazards()
    skipped_checks = {
        "production_mutation": (
            "covered_elsewhere: this runner validates the model contract; "
            "runtime conformance is exercised by current router unit tests"
        )
    }
    if not json_out_requested:
        skipped_checks["default_results_file"] = (
            "skipped_with_reason: no --json-out path was provided"
        )
    return {
        "ok": bool(safe_graph["ok"])
        and bool(progress["ok"])
        and bool(loop["ok"])
        and bool(explorer["ok"])
        and bool(hazards["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "loop": loop,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "architecture_candidate": _architecture_candidate(),
        "skipped_checks": skipped_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = run_checks(json_out_requested=bool(args.json_out))
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
