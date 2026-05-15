"""Run checks for the FlowPilot process-level Router liveness model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_process_liveness_model as model


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
RESULTS_PATH = ROOT / "flowpilot_process_liveness_results.json"

REQUIRED_LABELS = (
    "router_tick_starts_settlement_before_startup_action",
    "settlement_resolves_stale_startup_evidence_before_next_action",
    "router_exposes_one_pm_scope_decision_after_settlement",
    "pm_scope_decision_matches_router_allowed_event",
    "pm_activates_route_and_fresh_frontier",
    "pm_registers_current_node_packet_after_fresh_frontier",
    "router_dispatches_worker_after_packet_registration",
    "worker_result_event_matches_router_allowed_event",
    "router_checks_worker_result_ledger_before_pm_relay",
    "router_routes_worker_result_to_pm_after_ledger_check",
    "pm_records_result_disposition_before_reviewer_gate",
    "pm_releases_formal_reviewer_gate_after_disposition",
    "reviewer_passes_current_node_result",
    "reviewer_blocks_current_node_for_same_gate_repair",
    "reviewer_blocks_current_node_for_route_mutation",
    "reviewer_blocks_current_node_for_fatal_protocol_stop",
    "pm_completes_node_after_reviewer_pass",
    "router_runs_control_plane_reissue_attempt_1",
    "router_runs_control_plane_reissue_attempt_2",
    "router_escalates_exhausted_blocker_to_pm_repair",
    "pm_selects_same_gate_repair_with_return_gate",
    "pm_selects_user_stop_for_unrepairable_blocker",
    "pm_records_controlled_blocked_stop_after_repair_decision",
    "repair_worker_returns_result_to_router",
    "repair_result_event_matches_router_allowed_event",
    "router_checks_repair_result_ledger_before_reviewer_return",
    "same_reviewer_rechecks_repair_result_and_passes",
    "pm_records_route_mutation_with_stale_evidence_and_frontier",
    "router_rewrites_frontier_after_route_mutation",
    "reviewer_reruns_same_scope_replay_after_mutation",
    "pm_records_controlled_blocked_fatal_protocol_stop",
    "pm_updates_node_completion_ledger_after_node_completion",
    "reviewer_runs_parent_backward_replay_after_node_ledger",
    "pm_records_parent_segment_decision_after_backward_replay",
    "router_advances_to_next_node_after_parent_segment_review",
    "pm_scans_current_route_for_final_ledger",
    "pm_writes_evidence_quality_package_before_final_ledger",
    "reviewer_passes_evidence_quality_before_final_ledger",
    "pm_generates_final_ledger_source_of_truth",
    "pm_builds_clean_final_route_wide_ledger",
    "router_builds_terminal_replay_map_from_final_ledger",
    "reviewer_passes_terminal_replay_segments",
    "router_exposes_final_backward_replay_wait",
    "reviewer_records_final_backward_replay_pass",
    "router_publishes_task_completion_projection_from_ledger",
    "router_exposes_pm_terminal_closure_wait",
    "pm_approves_terminal_closure_after_projection",
    "process_liveness_complete_after_terminal_closure",
)

HAZARD_EXPECTED_FAILURES = {
    "next_action_before_settlement": "Router exposed a next action before starting settlement",
    "next_action_before_durable_evidence_settled": "Router exposed a next action before durable evidence settled",
    "multiple_next_actions_one_tick": "Router exposed more than one next action in one tick",
    "stale_pending_action_used_for_next_action": "Router exposed a next action from stale pending_action",
    "stale_blocker_survives_next_action": "Router exposed a next action while stale blocker remained active",
    "stale_pm_repair_row_not_superseded": "Router exposed next action before superseding stale PM repair row",
    "wait_target_without_allowed_event": "Router wait target had no allowed external event",
    "allowed_event_without_wait_target": "Router allowed event existed without an active wait target",
    "wrong_event_reconciled": "Router reconciled an event that did not match the active allowed event",
    "wrong_event_accepted": "Router accepted a wrong or unauthorized external event",
    "later_node_without_prior_review": "Router advanced to a later node before all previous nodes were reviewed and completed",
    "completion_ledger_includes_unreviewed_node": "node completion ledger includes a node without reviewer pass",
    "current_node_completed_without_review_mask": "current node completed before its reviewer pass was recorded",
    "packet_registered_on_stale_frontier": "current-node packet registered before route activation, fresh frontier, and fresh evidence",
    "worker_result_routed_without_ledger": "worker result routed to PM before ledger check",
    "reviewer_gate_before_pm_disposition": "reviewer gate released before PM result disposition",
    "reviewer_decision_without_gate": "reviewer decision recorded before formal reviewer gate release",
    "active_blocker_without_kind": "active control blocker had no blocker kind",
    "active_blocker_without_lane": "active control blocker had no handling lane",
    "small_fix_pm_before_retry_budget": "small-fix blocker was sent to PM before local retry budget was exhausted",
    "small_fix_misrouted_to_route_mutation": "small-fix blocker was misrouted to route mutation",
    "route_scope_misrouted_to_local_reissue": "route-scope blocker was misrouted to local reissue",
    "fatal_protocol_misrouted_to_repair": "fatal protocol blocker was misrouted to repair or route mutation",
    "pm_repair_before_retry_budget_exhausted": "PM repair requested before direct retry budget was exhausted",
    "retry_attempts_exceed_budget": "control blocker retry attempts exceeded retry budget",
    "exhausted_blocker_not_escalated": "exhausted control blocker stayed in direct reissue lane without PM repair",
    "pm_repair_loop_unbounded": "PM repair loop exceeded the bounded repair cycle limit",
    "pm_repair_request_without_decision": "PM repair request had no PM decision path",
    "same_gate_repair_without_return_gate": "PM same-gate repair decision lacked a named return gate",
    "reviewer_recheck_before_repair_ledger": "reviewer repair recheck passed before repair result ledger check",
    "route_mutation_without_stale_evidence": "route mutation did not mark old evidence stale",
    "route_mutation_without_stale_frontier": "route mutation did not mark old frontier stale",
    "route_mutation_loop_unbounded": "route mutation loop exceeded bounded route mutation limit",
    "final_scan_before_mutation_replay": "final route scan started before same-scope replay after mutation",
    "node_completed_before_reviewer_pass": "node completed before reviewer pass",
    "parent_segment_before_backward_replay": "PM parent segment decision recorded before parent backward replay",
    "current_route_scan_before_all_nodes_reviewed": "current route scan ran before every route node was reviewed and completed",
    "final_ledger_before_route_scan": "final ledger built before current route scan",
    "final_ledger_before_all_nodes_reviewed": "final ledger built before every route node was reviewed and completed",
    "final_ledger_with_unresolved_items": "final ledger built while unresolved items remained",
    "final_ledger_with_pending_generated_resources": "final ledger built while generated resources were pending",
    "terminal_replay_map_before_clean_ledger": "terminal replay map built before clean final ledger",
    "completion_before_final_backward_replay": "task completion projection published before final backward replay",
    "pm_closure_before_completion_projection": "PM closure approved before task completion projection",
    "complete_before_pm_closure": "process completed before PM terminal closure approval",
    "complete_before_all_nodes_reviewed": "process completed before every route node was reviewed and completed",
    "controller_reads_sealed_body": "Controller read a sealed packet or result body",
    "controller_originates_project_evidence": "Controller originated project evidence",
    "controller_advances_route": "Controller advanced route state without PM authority",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|phase={state.phase}|holder={state.holder}|"
        f"route={state.route_version}|node={state.current_node_index},"
        f"review_mask={state.node_review_pass_mask},"
        f"complete_mask={state.node_completion_ledger_mask}|"
        f"settle={state.settlement_started},"
        f"pending={state.durable_evidence_pending},fresh={state.evidence_fresh}|"
        f"stale={state.stale_pending_action},{state.stale_blocker_present},"
        f"{state.stale_pm_repair_row_present},{state.stale_pm_repair_row_superseded}|"
        f"next={state.next_action_exposed},{state.next_action_count}|"
        f"wait={state.wait_target},{state.allowed_event},{state.event_received},"
        f"{state.event_reconciled}|route_active={state.route_activated},"
        f"frontier={state.frontier_fresh}|packet={state.node_packet_registered},"
        f"worker={state.worker_dispatched},{state.worker_result_returned},"
        f"{state.worker_result_ledger_checked},{state.worker_result_routed_to_pm}|"
        f"pm={state.pm_result_disposition_recorded}|review={state.reviewer_gate_released},"
        f"{state.reviewer_decision}|blocker={state.control_blocker_active},"
        f"{state.blocker_kind},{state.blocker_lane},retry={state.retry_attempts}/{state.retry_budget},"
        f"exhausted={state.retry_budget_exhausted}|pm_repair={state.pm_repair_requested},"
        f"{state.pm_repair_decision},{state.repair_return_gate},cycles={state.pm_repair_cycles}|"
        f"mutation={state.route_mutation_recorded},{state.old_evidence_marked_stale},"
        f"{state.frontier_marked_stale},{state.frontier_rewritten_after_mutation},"
        f"{state.same_scope_replay_rerun}|terminal={state.final_ledger_built},"
        f"{state.final_ledger_clean},{state.final_backward_replay_passed},"
        f"{state.pm_terminal_closure_approved}"
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

        for label, new_state in model.next_states(state):
            labels.add(label)
            if new_state not in index:
                index[new_state] = len(states)
                states.append(new_state)
                queue.append(new_state)
            edges[source].append((label, index[new_state]))

    return {
        "states": states,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _safe_graph_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    labels = set(graph["labels"])
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    complete_state_count = sum(1 for state in states if state.status == "complete")
    controlled_blocked_state_count = sum(
        1 for state in states if state.status == "controlled_blocked"
    )
    return {
        "ok": (
            not graph["invariant_failures"]
            and not missing_labels
            and complete_state_count > 0
            and controlled_blocked_state_count > 0
        ),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "complete_state_count": complete_state_count,
        "controlled_blocked_state_count": controlled_blocked_state_count,
        "labels_seen": sorted(labels),
        "missing_labels": missing_labels,
        "invariant_failure_count": len(graph["invariant_failures"]),
        "invariant_failures": graph["invariant_failures"][:10],
    }


def _node_coverage_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    complete_states = [state for state in states if state.status == "complete"]
    all_node_mask = model.ROUTE_NODE_MASK
    complete_without_full_coverage = [
        _state_id(state)
        for state in complete_states
        if state.node_review_pass_mask != all_node_mask
        or state.node_completion_ledger_mask != all_node_mask
    ]
    final_scan_without_full_coverage = [
        _state_id(state)
        for state in states
        if state.current_route_scan_done
        and (
            state.node_review_pass_mask != all_node_mask
            or state.node_completion_ledger_mask != all_node_mask
        )
    ]
    max_node_seen = max((state.current_node_index for state in states), default=0)
    complete_coverage_paths = [
        _state_id(state)
        for state in complete_states
        if state.node_review_pass_mask == all_node_mask
        and state.node_completion_ledger_mask == all_node_mask
    ]
    return {
        "ok": (
            bool(complete_coverage_paths)
            and not complete_without_full_coverage
            and not final_scan_without_full_coverage
            and max_node_seen == model.ROUTE_NODE_COUNT - 1
        ),
        "route_node_count": model.ROUTE_NODE_COUNT,
        "max_node_seen": max_node_seen,
        "complete_states_with_full_coverage": len(complete_coverage_paths),
        "complete_without_full_coverage_count": len(complete_without_full_coverage),
        "complete_without_full_coverage_samples": complete_without_full_coverage[:10],
        "final_scan_without_full_coverage_count": len(final_scan_without_full_coverage),
        "final_scan_without_full_coverage_samples": final_scan_without_full_coverage[:10],
    }


def _progress_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    success = {idx for idx, state in enumerate(states) if model.is_success(state)}

    can_reach_terminal = set(terminal)
    can_reach_success = set(success)
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
            if source not in can_reach_success and any(
                target in can_reach_success for target in targets
            ):
                can_reach_success.add(source)
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
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_success,
        "initial_can_reach_success": 0 in can_reach_success,
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "cannot_reach_terminal_samples": cannot_reach_terminal[:10],
    }


def _tarjan_scc(edges: list[list[tuple[str, int]]]) -> list[list[int]]:
    index = 0
    stack: list[int] = []
    on_stack: set[int] = set()
    indices: dict[int, int] = {}
    lowlinks: dict[int, int] = {}
    components: list[list[int]] = []

    def strongconnect(node: int) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for _label, target in edges[node]:
            if target not in indices:
                strongconnect(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[target])

        if lowlinks[node] == indices[node]:
            component: list[int] = []
            while True:
                item = stack.pop()
                on_stack.remove(item)
                component.append(item)
                if item == node:
                    break
            components.append(component)

    for node in range(len(edges)):
        if node not in indices:
            strongconnect(node)
    return components


def _loop_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    closed_nonterminal_components: list[list[str]] = []

    for component in _tarjan_scc(edges):
        members = set(component)
        if any(model.is_terminal(states[index]) for index in members):
            continue
        has_external_edge = any(
            target not in members
            for index in members
            for _label, target in edges[index]
        )
        if not has_external_edge:
            closed_nonterminal_components.append(
                [_state_id(states[index]) for index in component[:5]]
            )

    return {
        "ok": not closed_nonterminal_components,
        "nonterminating_component_count": len(closed_nonterminal_components),
        "nonterminating_component_samples": closed_nonterminal_components[:10],
    }


def _run_flowguard_explorer() -> dict[str, object]:
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


def _hazard_report() -> dict[str, object]:
    hazards: dict[str, object] = {}
    ok = True
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in failures)
        ok = ok and detected
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": failures,
            "state": state.__dict__,
        }
    return {"ok": ok, "hazards": hazards}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _maybe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return _read_json(path)
    except json.JSONDecodeError:
        return {"_invalid_json": True, "_path": str(path)}


def _severity_counts(findings: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        severity = str(finding.get("severity", "info"))
        counts[severity] = counts.get(severity, 0) + 1
    return counts


def _current_run_projection() -> dict[str, object]:
    findings: list[dict[str, object]] = []
    evidence_paths: list[str] = []
    current_path = PROJECT_ROOT / ".flowpilot" / "current.json"
    if not current_path.exists():
        return {
            "ok": False,
            "status": "missing_current_pointer",
            "findings": [
                {
                    "id": "missing_current_pointer",
                    "severity": "blocking",
                    "summary": ".flowpilot/current.json is missing",
                }
            ],
        }

    current = _maybe_json(current_path)
    evidence_paths.append(str(current_path.relative_to(PROJECT_ROOT)))
    run_root_text = current.get("current_run_root")
    status = str(current.get("status") or "unknown")
    if not isinstance(run_root_text, str) or not run_root_text:
        findings.append(
            {
                "id": "current_run_root_missing",
                "severity": "blocking",
                "summary": ".flowpilot/current.json has no current_run_root",
            }
        )
        return {
            "ok": False,
            "status": status,
            "findings": findings,
            "evidence_paths": evidence_paths,
        }

    run_root = PROJECT_ROOT / run_root_text
    if not run_root.exists():
        findings.append(
            {
                "id": "current_run_root_missing_on_disk",
                "severity": "blocking",
                "summary": f"current run root does not exist: {run_root_text}",
            }
        )
        return {
            "ok": False,
            "status": status,
            "findings": findings,
            "evidence_paths": evidence_paths,
        }

    rel_run_root = str(run_root.relative_to(PROJECT_ROOT))
    frontier_path = run_root / "execution_frontier.json"
    router_path = run_root / "router_state.json"
    daemon_path = run_root / "runtime" / "router_daemon_status.json"
    packet_path = run_root / "packet_ledger.json"
    final_summary_path = run_root / "final_summary.json"
    route_history_path = run_root / "route_memory" / "route_history_index.json"
    for path in (
        frontier_path,
        router_path,
        daemon_path,
        packet_path,
        final_summary_path,
        route_history_path,
    ):
        if path.exists():
            evidence_paths.append(str(path.relative_to(PROJECT_ROOT)))

    frontier = _maybe_json(frontier_path)
    router_state = _maybe_json(router_path)
    daemon_status = _maybe_json(daemon_path)
    packet_ledger = _maybe_json(packet_path)
    final_summary = _maybe_json(final_summary_path)
    route_history = _maybe_json(route_history_path)

    frontier_status = str(frontier.get("status") or "unknown")
    frontier_terminal = bool(frontier.get("terminal"))
    terminal_event = str(frontier.get("terminal_event") or "")
    daemon_lifecycle = str(daemon_status.get("lifecycle_status") or "unknown")

    if status == "stopped_by_user" or terminal_event == "user_requests_run_stop":
        findings.append(
            {
                "id": "current_run_is_controlled_user_stop",
                "severity": "info",
                "summary": "current run is a controlled user stop, not a normal FlowPilot completion",
                "status": status,
                "frontier_status": frontier_status,
                "terminal_event": terminal_event,
            }
        )
    elif frontier_terminal and status not in {"complete", "stopped_by_user"}:
        findings.append(
            {
                "id": "terminal_frontier_status_not_classified",
                "severity": "warning",
                "summary": "execution frontier is terminal but current status is not clearly complete or stopped_by_user",
                "status": status,
                "frontier_status": frontier_status,
            }
        )

    active_blocker = router_state.get("active_control_blocker")
    if active_blocker:
        findings.append(
            {
                "id": "active_control_blocker_present",
                "severity": "blocking",
                "summary": "router_state still has active_control_blocker",
                "run_root": rel_run_root,
            }
        )

    unresolved_blockers: list[dict[str, object]] = []
    terminal_resolved_blockers: list[dict[str, object]] = []
    local_fix_misrouted_blockers: list[dict[str, object]] = []
    retry_budget_inconsistent_blockers: list[dict[str, object]] = []
    local_first_sources = {
        "controller_action_receipt_missing_router_postcondition",
        "startup_receipt_missing_router_postcondition",
        "startup_missing_postcondition",
    }
    for blocker in router_state.get("control_blockers", []) or []:
        if not isinstance(blocker, dict):
            continue
        resolution = str(blocker.get("resolution_status") or "")
        blocker_id = str(blocker.get("blocker_id") or "")
        source = str(blocker.get("source") or "")
        handling_lane = str(blocker.get("handling_lane") or "")
        artifact_path_text = blocker.get("blocker_artifact_path")
        if isinstance(artifact_path_text, str) and artifact_path_text:
            artifact_path = PROJECT_ROOT / artifact_path_text
            if artifact_path.exists() and artifact_path.suffix == ".json":
                evidence_paths.append(str(artifact_path.relative_to(PROJECT_ROOT)))
                artifact = _maybe_json(artifact_path)
                source = source or str(artifact.get("source") or "")
        direct_retry_budget = int(blocker.get("direct_retry_budget") or 0)
        direct_retry_attempts = int(blocker.get("direct_retry_attempts_used") or 0)
        direct_retry_exhausted = bool(blocker.get("direct_retry_budget_exhausted"))
        if direct_retry_budget <= direct_retry_attempts and not direct_retry_exhausted:
            retry_budget_inconsistent_blockers.append(
                {
                    "blocker_id": blocker_id,
                    "direct_retry_attempts_used": direct_retry_attempts,
                    "direct_retry_budget": direct_retry_budget,
                    "direct_retry_budget_exhausted": direct_retry_exhausted,
                    "handling_lane": handling_lane,
                }
            )
        if (
            source in local_first_sources
            and handling_lane in {
                "pm_repair",
                "pm_repair_decision_required",
            }
            and not direct_retry_exhausted
        ):
            local_fix_misrouted_blockers.append(
                {
                    "blocker_id": blocker_id,
                    "source": source,
                    "handling_lane": handling_lane,
                    "resolution_status": resolution,
                    "delivery_status": blocker.get("delivery_status"),
                }
            )
        if not resolution.startswith(("resolved", "superseded")):
            unresolved_blockers.append(
                {
                    "blocker_id": blocker_id,
                    "handling_lane": handling_lane,
                    "delivery_status": blocker.get("delivery_status"),
                    "resolution_status": resolution,
                }
            )
        elif blocker.get("resolved_by_event") == "user_requests_run_stop":
            terminal_resolved_blockers.append(
                {
                    "blocker_id": blocker_id,
                    "handling_lane": handling_lane,
                    "resolution_status": resolution,
                    "resolved_by_event": blocker.get("resolved_by_event"),
                }
            )
    if unresolved_blockers:
        findings.append(
            {
                "id": "unresolved_control_blockers",
                "severity": "blocking",
                "summary": "control blockers remain unresolved",
                "blockers": unresolved_blockers,
            }
        )
    if terminal_resolved_blockers:
        findings.append(
            {
                "id": "blocker_resolved_by_terminal_stop_not_repair",
                "severity": "info",
                "summary": "a blocker was cleared by user-stop terminal lifecycle, not by the normal PM repair return path",
                "blockers": terminal_resolved_blockers,
            }
        )
    if local_fix_misrouted_blockers:
        findings.append(
            {
                "id": "local_fix_style_blocker_routed_to_pm",
                "severity": "warning",
                "summary": "a blocker that looks like local settlement/reconciliation repair was routed to PM repair lane",
                "blockers": local_fix_misrouted_blockers,
            }
        )
    if retry_budget_inconsistent_blockers:
        findings.append(
            {
                "id": "blocker_retry_budget_flag_inconsistent",
                "severity": "warning",
                "summary": "a blocker retry budget is already exhausted by count but not marked exhausted",
                "blockers": retry_budget_inconsistent_blockers,
            }
        )

    controller_counts = (
        daemon_status.get("controller_action_ledger", {}).get("counts", {})
        if isinstance(daemon_status.get("controller_action_ledger"), dict)
        else {}
    )
    scheduler_counts = (
        daemon_status.get("router_scheduler_ledger", {}).get("counts", {})
        if isinstance(daemon_status.get("router_scheduler_ledger"), dict)
        else {}
    )
    open_controller_rows = int(controller_counts.get("pending") or 0) + int(
        controller_counts.get("waiting") or 0
    )
    open_scheduler_rows = int(scheduler_counts.get("queued") or 0) + int(
        scheduler_counts.get("waiting") or 0
    )
    if frontier_terminal and (open_controller_rows or open_scheduler_rows):
        findings.append(
            {
                "id": "terminal_run_retains_open_work_rows",
                "severity": "warning",
                "summary": "terminal run still has open Controller or scheduler rows; safe only as stopped-run history",
                "controller_open_rows": open_controller_rows,
                "scheduler_open_rows": open_scheduler_rows,
                "daemon_lifecycle": daemon_lifecycle,
            }
        )

    route_info = route_history.get("route") if isinstance(route_history.get("route"), dict) else {}
    review_markers = (
        route_history.get("review_markers")
        if isinstance(route_history.get("review_markers"), dict)
        else {}
    )
    effective_nodes = route_info.get("effective_nodes", [])
    if not isinstance(effective_nodes, list):
        effective_nodes = []
    route_node_count = int(route_info.get("route_node_count") or len(effective_nodes) or 0)
    review_pass_count = len(review_markers.get("passes") or [])
    completed_nodes = frontier.get("completed_nodes") or []
    if not isinstance(completed_nodes, list):
        completed_nodes = []
    if route_node_count == 0:
        severity = "blocking" if status == "complete" else "info"
        findings.append(
            {
                "id": "route_nodes_never_activated",
                "severity": severity,
                "summary": "no route nodes were activated, so per-node execution and reviewer coverage cannot be claimed",
                "route_node_count": route_node_count,
                "review_pass_count": review_pass_count,
                "completed_node_count": len(completed_nodes),
            }
        )
    elif status == "complete" and (
        len(completed_nodes) < route_node_count or review_pass_count < route_node_count
    ):
        findings.append(
            {
                "id": "completion_missing_per_node_review_coverage",
                "severity": "blocking",
                "summary": "run claims completion before every route node has completion and reviewer pass coverage",
                "route_node_count": route_node_count,
                "completed_node_count": len(completed_nodes),
                "review_pass_count": review_pass_count,
            }
        )

    flags = router_state.get("flags") if isinstance(router_state.get("flags"), dict) else {}
    if status == "complete":
        required_completion_flags = {
            "final_ledger_built": flags.get("final_ledger_built_clean") is True,
            "final_backward_replay": flags.get("final_backward_replay_passed") is True,
            "evidence_quality": flags.get("evidence_quality_reviewer_passed") is True,
        }
        missing = [name for name, ok in required_completion_flags.items() if not ok]
        if missing:
            findings.append(
                {
                    "id": "completion_missing_terminal_evidence",
                    "severity": "blocking",
                    "summary": "run claims completion but terminal ledger evidence is incomplete",
                    "missing": missing,
                }
            )
    else:
        findings.append(
            {
                "id": "normal_completion_not_claimed",
                "severity": "info",
                "summary": "normal route-wide completion was not claimed for the current run",
            }
        )

    packet_terminal = (
        packet_ledger.get("terminal_lifecycle", {})
        if isinstance(packet_ledger.get("terminal_lifecycle"), dict)
        else {}
    )
    if packet_terminal.get("status") == "stopped_by_user":
        findings.append(
            {
                "id": "packet_loop_stopped_by_user",
                "severity": "info",
                "summary": "packet loop was reconciled into stopped_by_user terminal lifecycle",
                "previous_active_packet_status": packet_terminal.get("previous_active_packet_status"),
            }
        )

    if final_summary and final_summary.get("run_lifecycle_status") == "stopped_by_user":
        findings.append(
            {
                "id": "terminal_summary_matches_user_stop",
                "severity": "info",
                "summary": "final summary reports stopped_by_user and forbids controller continuation",
            }
        )

    severity_counts = _severity_counts(findings)
    return {
        "ok": severity_counts.get("blocking", 0) == 0,
        "status": status,
        "run_root": rel_run_root,
        "frontier_status": frontier_status,
        "frontier_terminal": frontier_terminal,
        "daemon_lifecycle": daemon_lifecycle,
        "severity_counts": severity_counts,
        "findings": findings,
        "evidence_paths": evidence_paths,
    }


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    node_coverage = _node_coverage_report(graph)
    progress = _progress_report(graph)
    loops = _loop_report(graph)
    flowguard_explorer = _run_flowguard_explorer()
    hazard_checks = _hazard_report()
    current_run_projection = _current_run_projection()
    ok = (
        safe_graph["ok"]
        and node_coverage["ok"]
        and progress["ok"]
        and loops["ok"]
        and flowguard_explorer["ok"]
        and hazard_checks["ok"]
        and current_run_projection["ok"]
    )
    return {
        "ok": ok,
        "safe_graph": safe_graph,
        "node_coverage": node_coverage,
        "progress": progress,
        "loop": loops,
        "flowguard_explorer": flowguard_explorer,
        "hazard_checks": hazard_checks,
        "current_run_projection": current_run_projection,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="print compact JSON only")
    parser.add_argument(
        "--no-write-results",
        action="store_true",
        help="do not write simulations/flowpilot_process_liveness_results.json",
    )
    args = parser.parse_args(argv)

    result = run_checks()
    if not args.no_write_results:
        RESULTS_PATH.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("=== FlowPilot Process Liveness ===")
        print(json.dumps({k: result[k] for k in ("ok",)}, indent=2, sort_keys=True))
        print("\n=== Safe Graph ===")
        print(json.dumps(result["safe_graph"], indent=2, sort_keys=True))
        print("\n=== Node Coverage ===")
        print(json.dumps(result["node_coverage"], indent=2, sort_keys=True))
        print("\n=== Progress ===")
        print(json.dumps(result["progress"], indent=2, sort_keys=True))
        print("\n=== Loop ===")
        print(json.dumps(result["loop"], indent=2, sort_keys=True))
        print("\n=== Current Run Projection ===")
        print(json.dumps(result["current_run_projection"], indent=2, sort_keys=True))

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
