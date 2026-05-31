"""Transition helpers for ``flowpilot_router_loop_model``."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from flowguard import FunctionResult

from flowpilot_router_loop_model_state import (
    BUSINESS_VALIDATED_REPAIR_EVENTS,
    EVENT_NODE_KIND_COMPATIBILITY,
    EXPECTED_ROLE_EVENT_CONTRACTS,
    MAX_ROUTE_MUTATIONS,
    PARENT_REPAIR_SAFE_EVENTS,
    Action,
    Condition,
    ConditionGroup,
    EventContract,
    State,
    Tick,
    Transition,
    initial_state,
)

class RouterLoopStep:
    """Model one current-node router transition.

    Input x State -> Set(Output x State)
    reads: route activation, packet loop holder, reviewer decision, mutation
    status, stale evidence/frontier state, and terminal ledger status
    writes: one control-plane fact, packet-loop handoff, mutation marker,
    terminal ledger fact, or terminal status
    idempotency: a repeated tick observes the current state and advances at
    most one missing fact; terminal states produce no further side effects.
    """

    name = "RouterLoopStep"
    reads = (
        "controller_boundary",
        "route_activation",
        "flowguard_operator_packet_loop",
        "packet_loop",
        "repair_recheck_loop",
        "reviewer_decision",
        "route_mutation",
        "final_ledger",
    )
    writes = (
        "control_plane_fact",
        "packet_handoff",
        "packet_ledger_check",
        "route_mutation_marker",
        "final_ledger_fact",
        "terminal_status",
    )
    input_description = "current-node router tick"
    output_description = "one abstract FlowPilot packet-loop action"
    idempotency = "repeat ticks do not duplicate completed packet or ledger facts"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def _clear_current_node_cycle(state: State, **changes: object) -> State:
    return replace(
        state,
        route_activated=False,
        active_node_kind="leaf",
        flowguard_operator_packet_card_delivered=False,
        flowguard_operator_packet_relayed=False,
        flowguard_operator_packet_identity_boundary_present=False,
        flowguard_operator_result_returned=False,
        flowguard_operator_result_identity_boundary_present=False,
        flowguard_operator_result_ledger_checked=False,
        flowguard_operator_result_routed_to_pm=False,
        pm_absorbed_flowguard_operator_result=False,
        flowguard_operator_lifecycle_flags_current=False,
        route_history_context_refreshed=False,
        pm_prior_path_context_reviewed=False,
        route_history_context_stale=True,
        node_acceptance_plan_prior_context_used=False,
        parent_segment_prior_context_used=False,
        evidence_quality_prior_context_used=False,
        final_ledger_prior_context_used=False,
        pm_node_high_standard_gate_opened=False,
        pm_node_high_standard_risks_reviewed=False,
        node_acceptance_plan_written=False,
        reviewer_node_acceptance_plan_reviewed=False,
        current_node_packet_registered=False,
        write_grant_issued=False,
        reviewer_dispatch_allowed=False,
        worker_dispatched=False,
        worker_project_write_performed=False,
        worker_packet_identity_boundary_present=False,
        active_holder_lease_issued=False,
        active_holder_contact_attempted=False,
        active_holder_contact_is_current_holder=True,
        active_holder_contact_agent_matches=True,
        active_holder_contact_packet_current=True,
        active_holder_contact_route_frontier_current=True,
        active_holder_contact_action_allowed=True,
        active_holder_ack_recorded=False,
        active_holder_packet_opened_through_runtime=False,
        active_holder_progress_recorded=False,
        active_holder_progress_controller_safe=True,
        active_holder_packet_family="current_node",
        generalized_packet_registered=False,
        generalized_packet_relayed=False,
        generalized_packet_identity_boundary_present=True,
        generalized_packet_live_holder_known=True,
        generalized_result_target_is_pm=True,
        fast_lane_initial_result_submitted=False,
        fast_lane_mechanical_reject_recorded=False,
        fast_lane_result_resubmitted=False,
        fast_lane_result_mechanics_passed=False,
        fast_lane_controller_notice_written=False,
        worker_result_returned=False,
        worker_result_identity_boundary_present=False,
        worker_result_ledger_checked=False,
        worker_result_routed_to_pm=False,
        pm_result_disposition_recorded=False,
        pm_formal_node_gate_package_released=False,
        worker_result_routed_to_reviewer=False,
        reviewer_worker_result_card_delivered=False,
        reviewer_decision="none",
        repair_packet_registered=False,
        repair_dispatch_allowed=False,
        repair_worker_dispatched=False,
        repair_packet_identity_boundary_present=False,
        repair_result_returned=False,
        repair_result_identity_boundary_present=False,
        repair_result_ledger_checked=False,
        repair_result_routed_to_reviewer=False,
        repair_recheck_passed=False,
        pm_node_completion_card_delivered=False,
        pm_node_completed=False,
        node_completion_ledger_updated=False,
        parent_backward_targets_enumerated=False,
        parent_backward_replay_passed=False,
        parent_pm_segment_decision_recorded=False,
        parent_node_completed=False,
        same_scope_replay_rerun_after_mutation=False,
        current_route_scan_done=False,
        pm_evidence_quality_package_card_delivered=False,
        evidence_quality_package_written=False,
        evidence_quality_review_card_delivered=False,
        evidence_quality_reviewer_passed=False,
        stale_or_unresolved_evidence_present=False,
        pending_generated_resources=False,
        ui_visual_required=False,
        ui_visual_screenshots_present=False,
        old_assets_reused_as_current_evidence=False,
        unresolved_count_zero=False,
        pm_final_ledger_card_delivered=False,
        final_ledger_source_of_truth_generated=False,
        final_ledger_built=False,
        final_ledger_clean=False,
        terminal_replay_map_generated_from_final_ledger=False,
        terminal_replay_root_segment_passed=False,
        terminal_replay_parent_segment_passed=False,
        terminal_replay_leaf_segment_passed=False,
        terminal_replay_pm_segment_decisions_recorded=False,
        final_backward_replay_card_delivered=False,
        final_backward_replay_passed=False,
        task_completion_projection_published=False,
        pm_terminal_closure_card_delivered=False,
        control_repair_origin="none",
        control_repair_wait_event="none",
        repair_outcome_success_event="none",
        repair_outcome_blocker_event="none",
        repair_outcome_protocol_blocker_event="none",
        **changes,
    )


def _condition_matches(state: State, condition: Condition) -> bool:
    field_name, expected = condition
    return getattr(state, field_name) == expected


def _conditions_match(state: State, conditions: ConditionGroup) -> bool:
    return all(_condition_matches(state, condition) for condition in conditions)


def _event_contract_satisfied(state: State, contract: EventContract) -> bool:
    return any(
        _conditions_match(state, conditions)
        for conditions in contract.satisfied_by_any
    )


def expected_role_event_waits(state: State) -> tuple[str, ...]:
    return tuple(
        contract.name
        for contract in EXPECTED_ROLE_EVENT_CONTRACTS
        if _conditions_match(state, contract.requires_all)
        and not _event_contract_satisfied(state, contract)
    )


def expected_wait_hazard_states() -> dict[str, State]:
    samples: dict[str, State] = {}
    pending = [initial_state()]
    seen = {initial_state()}
    while pending:
        state = pending.pop(0)
        if state.status not in {"blocked", "complete"}:
            for wait_name in expected_role_event_waits(state):
                hazard_name = f"expected_role_event_wait_{wait_name}_materializes_blocker"
                samples.setdefault(
                    hazard_name,
                    replace(state, pm_decision_required_blocker_written=True),
                )
        for transition in next_safe_states(state):
            if transition.state not in seen:
                seen.add(transition.state)
                pending.append(transition.state)
    return samples


def _event_allowed_for_node_kind(event: str, node_kind: str) -> bool:
    allowed = EVENT_NODE_KIND_COMPATIBILITY.get(event)
    if allowed is None:
        return True
    return node_kind in allowed


def _repair_outcome_events(state: State) -> tuple[str, ...]:
    return tuple(
        event
        for event in (
            state.repair_outcome_success_event,
            state.repair_outcome_blocker_event,
            state.repair_outcome_protocol_blocker_event,
        )
        if event != "none"
    )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"blocked", "complete"}:
        return

    if not state.controller_boundary_confirmed:
        yield Transition(
            "controller_boundary_confirmed_envelope_only",
            replace(
                state,
                status="running",
                holder="controller",
                controller_boundary_confirmed=True,
                controller_only_mode_active=True,
            ),
        )
        return

    if not state.route_activated and state.route_version == 0:
        yield Transition(
            "controller_fail_closes_no_next_action_to_pm_blocker",
            replace(
                state,
                status="blocked",
                holder="pm",
                no_next_action_detected=True,
                pm_decision_required_blocker_written=True,
            ),
        )

    if state.route_mutation_count and not state.frontier_rewritten_after_mutation:
        yield Transition(
            "frontier_rewritten_for_mutated_route",
            replace(
                state,
                holder="pm",
                frontier_rewritten_after_mutation=True,
            ),
        )
        return

    if not state.route_activated:
        if state.route_version == 0:
            yield Transition(
                "pm_activates_route",
                replace(
                    state,
                    holder="pm",
                    route_version=1,
                    route_activated=True,
                ),
            )
            return
        yield Transition(
            "pm_activates_mutated_route",
            replace(state, holder="pm", route_activated=True),
        )
        return

    if not state.flowguard_operator_lifecycle_flags_current:
        yield Transition(
            "flowguard_operator_lifecycle_flags_reconciled_before_model_packet",
            replace(state, holder="pm", flowguard_operator_lifecycle_flags_current=True),
        )
        return

    if not state.flowguard_operator_packet_card_delivered:
        yield Transition(
            "flowguard_operator_packet_card_delivered_before_controller_relay",
            replace(state, holder="FlowGuard operator", flowguard_operator_packet_card_delivered=True),
        )
        return

    if not state.flowguard_operator_packet_relayed:
        yield Transition(
            "flowguard_operator_packet_relayed_after_flowguard_operator_card",
            replace(
                state,
                holder="FlowGuard operator",
                flowguard_operator_packet_relayed=True,
                flowguard_operator_packet_identity_boundary_present=True,
            ),
        )
        return

    if not state.flowguard_operator_result_returned:
        yield Transition(
            "flowguard_operator_result_returned_to_packet_ledger",
            replace(
                state,
                holder="controller",
                flowguard_operator_result_returned=True,
                flowguard_operator_result_identity_boundary_present=True,
            ),
        )
        return

    if not state.flowguard_operator_result_ledger_checked:
        yield Transition(
            "flowguard_operator_result_ledger_checked_before_pm_relay",
            replace(state, holder="controller", flowguard_operator_result_ledger_checked=True),
        )
        return

    if not state.flowguard_operator_result_routed_to_pm:
        yield Transition(
            "flowguard_operator_result_routed_to_pm_after_ledger_check",
            replace(state, holder="pm", flowguard_operator_result_routed_to_pm=True),
        )
        return

    if not state.pm_absorbed_flowguard_operator_result:
        yield Transition(
            "pm_absorbs_flowguard_operator_result_before_node_packet",
            replace(state, holder="pm", pm_absorbed_flowguard_operator_result=True),
        )
        return

    if (
        not state.node_acceptance_plan_written
        and (not state.route_history_context_refreshed or state.route_history_context_stale)
    ):
        yield Transition(
            "controller_refreshes_route_history_context_for_node_plan",
            replace(
                state,
                holder="controller",
                route_history_context_refreshed=True,
                pm_prior_path_context_reviewed=False,
                route_history_context_stale=False,
            ),
        )
        return

    if not state.node_acceptance_plan_written and not state.pm_prior_path_context_reviewed:
        yield Transition(
            "pm_reads_prior_path_context_for_node_plan",
            replace(state, holder="pm", pm_prior_path_context_reviewed=True),
        )
        return

    if not state.pm_node_high_standard_gate_opened:
        yield Transition(
            "pm_opens_current_node_high_standard_gate",
            replace(
                state,
                holder="pm",
                pm_node_high_standard_gate_opened=True,
                pm_node_high_standard_risks_reviewed=True,
            ),
        )
        return

    if not state.node_acceptance_plan_written:
        yield Transition(
            "pm_writes_node_acceptance_plan_before_packet",
            replace(
                state,
                holder="pm",
                node_acceptance_plan_written=True,
                node_acceptance_plan_prior_context_used=True,
            ),
        )
        return

    if not state.reviewer_node_acceptance_plan_reviewed:
        yield Transition(
            "reviewer_reviews_node_acceptance_plan_before_packet",
            replace(
                state,
                holder="reviewer",
                reviewer_node_acceptance_plan_reviewed=True,
            ),
        )
        return

    if not state.current_node_packet_registered:
        yield Transition(
            "current_node_packet_registered_after_route_activation_and_acceptance_plan",
            replace(
                state,
                holder="controller",
                current_node_packet_registered=True,
            ),
        )
        return

    if not state.write_grant_issued:
        yield Transition(
            "write_grant_issued_from_current_node_packet",
            replace(state, holder="pm", write_grant_issued=True),
        )
        return

    if not state.reviewer_dispatch_allowed:
        yield Transition(
            "router_direct_dispatch_allowed_for_current_node",
            replace(state, holder="reviewer", reviewer_dispatch_allowed=True),
        )
        return

    if not state.worker_dispatched:
        yield Transition(
            "worker_dispatched_after_router_direct_dispatch",
            replace(
                state,
                holder="worker",
                worker_dispatched=True,
                worker_packet_identity_boundary_present=True,
            ),
        )
        return

    if not state.active_holder_lease_issued:
        yield Transition(
            "active_holder_lease_issued_for_current_worker",
            replace(state, holder="worker", active_holder_lease_issued=True),
        )
        return

    if not state.active_holder_ack_recorded:
        yield Transition(
            "active_holder_ack_recorded_by_current_worker",
            replace(
                state,
                holder="worker",
                active_holder_contact_attempted=True,
                active_holder_ack_recorded=True,
            ),
        )
        return

    if not state.active_holder_packet_opened_through_runtime:
        yield Transition(
            "active_holder_packet_opened_through_runtime",
            replace(state, holder="worker", active_holder_packet_opened_through_runtime=True),
        )
        return

    if not state.active_holder_progress_recorded:
        yield Transition(
            "active_holder_progress_recorded_as_controller_safe_metadata",
            replace(
                state,
                holder="worker",
                active_holder_contact_attempted=True,
                active_holder_progress_recorded=True,
            ),
        )
        return

    if not state.fast_lane_initial_result_submitted:
        yield Transition(
            "active_holder_initial_result_submitted_to_router",
            replace(
                state,
                holder="worker",
                active_holder_contact_attempted=True,
                fast_lane_initial_result_submitted=True,
            ),
        )
        return

    if not state.fast_lane_mechanical_reject_recorded:
        yield Transition(
            "router_mechanically_rejects_result_to_same_holder",
            replace(
                state,
                holder="worker",
                fast_lane_mechanical_reject_recorded=True,
            ),
        )
        return

    if not state.fast_lane_result_resubmitted:
        yield Transition(
            "active_holder_resubmits_mechanically_repaired_result",
            replace(
                state,
                holder="worker",
                active_holder_contact_attempted=True,
                fast_lane_result_resubmitted=True,
            ),
        )
        return

    if not state.fast_lane_result_mechanics_passed:
        yield Transition(
            "router_accepts_fast_lane_result_mechanics",
            replace(
                state,
                holder="controller",
                fast_lane_result_mechanics_passed=True,
                worker_result_returned=True,
                worker_result_identity_boundary_present=True,
            ),
        )
        return

    if not state.worker_result_returned:
        yield Transition(
            "worker_result_returned_to_packet_ledger",
            replace(
                state,
                holder="controller",
                worker_project_write_performed=True,
                worker_result_returned=True,
                worker_result_identity_boundary_present=True,
            ),
        )
        return

    if not state.worker_result_ledger_checked:
        yield Transition(
            "worker_result_ledger_checked_before_pm_relay",
            replace(state, holder="controller", worker_result_ledger_checked=True),
        )
        return

    if not state.fast_lane_controller_notice_written:
        yield Transition(
            "router_writes_controller_notice_after_fast_lane_close",
            replace(state, holder="controller", fast_lane_controller_notice_written=True),
        )
        return

    if not state.worker_result_routed_to_pm:
        yield Transition(
            "worker_result_routed_to_pm",
            replace(
                state,
                holder="pm",
                worker_result_routed_to_pm=True,
            ),
        )
        return

    if not state.pm_result_disposition_recorded:
        yield Transition(
            "pm_records_current_node_result_disposition",
            replace(state, holder="pm", pm_result_disposition_recorded=True),
        )
        return

    if not state.pm_formal_node_gate_package_released:
        yield Transition(
            "pm_releases_current_node_formal_gate_package_to_reviewer",
            replace(state, holder="reviewer", pm_formal_node_gate_package_released=True),
        )
        return

    if not state.reviewer_worker_result_card_delivered:
        yield Transition(
            "reviewer_worker_result_review_card_delivered_after_pm_gate_release",
            replace(state, holder="reviewer", reviewer_worker_result_card_delivered=True),
        )
        return

    if state.reviewer_decision == "none":
        yield Transition(
            "reviewer_passes_current_node_result",
            replace(state, holder="reviewer", reviewer_decision="pass"),
        )
        if state.route_mutation_count < MAX_ROUTE_MUTATIONS:
            yield Transition(
                "reviewer_blocks_current_node_result",
                replace(
                    state,
                    holder="reviewer",
                    reviewer_decision="block",
                    reviewer_block_seen=True,
                    route_history_context_stale=True,
                ),
            )
        else:
            yield Transition(
                "reviewer_blocks_mutated_route_result_terminal",
                replace(
                    state,
                    status="blocked",
                    holder="reviewer",
                    reviewer_decision="block",
                    reviewer_block_seen=True,
                ),
            )
        return

    if state.reviewer_decision == "block":
        if not state.route_history_context_refreshed or state.route_history_context_stale:
            yield Transition(
                "controller_refreshes_route_history_context_for_repair_or_mutation",
                replace(
                    state,
                    holder="controller",
                    route_history_context_refreshed=True,
                    pm_prior_path_context_reviewed=False,
                    route_history_context_stale=False,
                ),
            )
            return

        if not state.pm_prior_path_context_reviewed:
            yield Transition(
                "pm_reads_prior_path_context_for_repair_or_mutation",
                replace(state, holder="pm", pm_prior_path_context_reviewed=True),
            )
            return

        if not state.repair_packet_registered:
            yield Transition(
                "pm_registers_repair_packet_after_reviewer_block",
                replace(state, holder="pm", repair_packet_registered=True),
            )
            if state.route_mutation_count < MAX_ROUTE_MUTATIONS:
                yield Transition(
                    "route_mutation_after_reviewer_block_marks_stale_evidence_and_frontier",
                    _clear_current_node_cycle(
                        state,
                        holder="pm",
                        route_version=state.route_version + 1,
                        route_mutation_count=state.route_mutation_count + 1,
                        pm_prior_path_context_used_for_route_mutation=True,
                        stale_evidence_marked=True,
                        frontier_marked_stale=True,
                        frontier_rewritten_after_mutation=False,
                    ),
                )
            return

        if not state.repair_dispatch_allowed:
            yield Transition(
                "router_direct_repair_dispatch_after_block",
                replace(state, holder="reviewer", repair_dispatch_allowed=True),
            )
            return

        if not state.repair_worker_dispatched:
            yield Transition(
                "repair_worker_dispatched_after_router_direct_dispatch",
                replace(
                    state,
                    holder="worker",
                    repair_worker_dispatched=True,
                    repair_packet_identity_boundary_present=True,
                ),
            )
            return

        if not state.repair_result_returned:
            yield Transition(
                "repair_result_returned_to_packet_ledger",
                replace(
                    state,
                    holder="controller",
                    repair_result_returned=True,
                    repair_result_identity_boundary_present=True,
                ),
            )
            return

        if not state.repair_result_ledger_checked:
            yield Transition(
                "repair_result_ledger_checked_before_reviewer_relay",
                replace(state, holder="controller", repair_result_ledger_checked=True),
            )
            return

        if not state.repair_result_routed_to_reviewer:
            yield Transition(
                "repair_result_routed_to_reviewer_after_ledger_check",
                replace(state, holder="reviewer", repair_result_routed_to_reviewer=True),
            )
            return

        if not state.repair_recheck_passed:
            yield Transition(
                "reviewer_rechecks_repair_result",
                replace(state, holder="reviewer", repair_recheck_passed=True),
            )
            return

        yield Transition(
            "reviewer_passes_current_node_after_repair_recheck",
            replace(state, holder="reviewer", reviewer_decision="pass"),
        )
        return

    if state.reviewer_decision != "pass":
        return

    if not state.pm_node_completion_card_delivered:
        yield Transition(
            "pm_node_completion_card_delivered_after_reviewer_pass",
            replace(state, holder="pm", pm_node_completion_card_delivered=True),
        )
        return

    if not state.pm_node_completed:
        yield Transition(
            "pm_completes_current_node_after_reviewer_pass",
            replace(
                state,
                holder="pm",
                pm_node_completed=True,
                route_history_context_refreshed=False,
                pm_prior_path_context_reviewed=False,
                route_history_context_stale=True,
            ),
        )
        return

    if not state.node_completion_ledger_updated:
        yield Transition(
            "node_completion_ledger_updated_after_pm_completion",
            replace(state, holder="controller", node_completion_ledger_updated=True),
        )
        return

    if not state.parent_backward_targets_enumerated:
        yield Transition(
            "pm_enumerates_parent_backward_targets_after_node_completion",
            replace(state, holder="pm", parent_backward_targets_enumerated=True),
        )
        return

    if not state.parent_backward_replay_passed:
        yield Transition(
            "reviewer_parent_backward_replay_after_targets",
            replace(state, holder="reviewer", parent_backward_replay_passed=True),
        )
        return

    if (
        not state.parent_pm_segment_decision_recorded
        and (not state.route_history_context_refreshed or state.route_history_context_stale)
    ):
        yield Transition(
            "controller_refreshes_route_history_context_for_parent_segment",
            replace(
                state,
                holder="controller",
                route_history_context_refreshed=True,
                pm_prior_path_context_reviewed=False,
                route_history_context_stale=False,
            ),
        )
        return

    if not state.parent_pm_segment_decision_recorded and not state.pm_prior_path_context_reviewed:
        yield Transition(
            "pm_reads_prior_path_context_for_parent_segment",
            replace(state, holder="pm", pm_prior_path_context_reviewed=True),
        )
        return

    if not state.parent_pm_segment_decision_recorded:
        yield Transition(
            "pm_records_parent_segment_decision_after_backward_replay",
            replace(
                state,
                holder="pm",
                parent_pm_segment_decision_recorded=True,
                parent_segment_prior_context_used=True,
            ),
        )
        return

    if not state.parent_node_completed:
        yield Transition(
            "pm_completes_parent_node_after_replay_and_segment_decision",
            replace(state, holder="pm", parent_node_completed=True),
        )
        return

    if state.route_mutation_count and not state.same_scope_replay_rerun_after_mutation:
        yield Transition(
            "reviewer_reruns_same_scope_replay_after_route_mutation",
            replace(state, holder="reviewer", same_scope_replay_rerun_after_mutation=True),
        )
        return

    if not state.current_route_scan_done:
        yield Transition(
            "current_route_scanned_for_final_ledger",
            replace(state, holder="pm", current_route_scan_done=True),
        )
        return

    if not state.pm_evidence_quality_package_card_delivered:
        yield Transition(
            "pm_evidence_quality_package_card_delivered_before_final_ledger",
            replace(
                state,
                holder="pm",
                pm_evidence_quality_package_card_delivered=True,
            ),
        )
        return

    if not state.evidence_quality_package_written:
        yield Transition(
            "pm_writes_evidence_quality_package_before_final_ledger",
            replace(
                state,
                holder="pm",
                evidence_quality_package_written=True,
                evidence_quality_prior_context_used=True,
            ),
        )
        return

    if not state.evidence_quality_review_card_delivered:
        yield Transition(
            "evidence_quality_review_card_delivered_after_package",
            replace(
                state,
                holder="reviewer",
                evidence_quality_review_card_delivered=True,
            ),
        )
        return

    if not state.evidence_quality_reviewer_passed:
        yield Transition(
            "reviewer_passes_evidence_quality_before_final_ledger",
            replace(
                state,
                holder="reviewer",
                evidence_quality_reviewer_passed=True,
                route_history_context_refreshed=False,
                pm_prior_path_context_reviewed=False,
                route_history_context_stale=True,
            ),
        )
        return

    if not state.route_history_context_refreshed or state.route_history_context_stale:
        yield Transition(
            "controller_refreshes_route_history_context_for_final_ledger",
            replace(
                state,
                holder="controller",
                route_history_context_refreshed=True,
                pm_prior_path_context_reviewed=False,
                route_history_context_stale=False,
            ),
        )
        return

    if not state.pm_prior_path_context_reviewed:
        yield Transition(
            "pm_reads_prior_path_context_for_final_ledger",
            replace(state, holder="pm", pm_prior_path_context_reviewed=True),
        )
        return

    if not state.unresolved_count_zero:
        yield Transition(
            "final_ledger_zero_unresolved_confirmed",
            replace(state, holder="pm", unresolved_count_zero=True),
        )
        yield Transition(
            "final_ledger_scan_finds_unresolved_items",
            replace(state, status="blocked", holder="pm"),
        )
        return

    if not state.pm_final_ledger_card_delivered:
        yield Transition(
            "pm_final_ledger_card_delivered_after_evidence_quality_pass",
            replace(
                state,
                holder="pm",
                pm_final_ledger_card_delivered=True,
                final_ledger_prior_context_used=True,
            ),
        )
        return

    if not state.final_ledger_source_of_truth_generated:
        yield Transition(
            "pm_generates_final_ledger_source_of_truth",
            replace(state, holder="pm", final_ledger_source_of_truth_generated=True),
        )
        return

    if not state.final_ledger_built:
        yield Transition(
            "pm_builds_clean_final_ledger",
            replace(
                state,
                holder="pm",
                final_ledger_built=True,
                final_ledger_clean=True,
                final_ledger_prior_context_used=True,
            ),
        )
        return

    if not state.terminal_replay_map_generated_from_final_ledger:
        yield Transition(
            "terminal_replay_map_generated_from_final_ledger",
            replace(
                state,
                holder="pm",
                terminal_replay_map_generated_from_final_ledger=True,
            ),
        )
        return

    if not state.terminal_replay_root_segment_passed:
        yield Transition(
            "reviewer_terminal_root_segment_replayed",
            replace(state, holder="reviewer", terminal_replay_root_segment_passed=True),
        )
        return

    if not state.terminal_replay_parent_segment_passed:
        yield Transition(
            "reviewer_terminal_parent_segment_replayed",
            replace(state, holder="reviewer", terminal_replay_parent_segment_passed=True),
        )
        return

    if not state.terminal_replay_leaf_segment_passed:
        yield Transition(
            "reviewer_terminal_leaf_segment_replayed",
            replace(state, holder="reviewer", terminal_replay_leaf_segment_passed=True),
        )
        return

    if not state.terminal_replay_pm_segment_decisions_recorded:
        yield Transition(
            "pm_records_terminal_segment_decisions",
            replace(
                state,
                holder="pm",
                terminal_replay_pm_segment_decisions_recorded=True,
            ),
        )
        return

    if not state.final_backward_replay_passed:
        if not state.final_backward_replay_card_delivered:
            yield Transition(
                "final_backward_replay_card_delivered_after_terminal_segments",
                replace(
                    state,
                    holder="reviewer",
                    final_backward_replay_card_delivered=True,
                ),
            )
            return
        yield Transition(
            "reviewer_final_backward_replay_after_all_segments",
            replace(state, holder="reviewer", final_backward_replay_passed=True),
        )
        return

    if not state.task_completion_projection_published:
        yield Transition(
            "task_completion_projection_published_from_completion_ledger",
            replace(state, holder="controller", task_completion_projection_published=True),
        )
        return

    if not state.pm_terminal_closure_card_delivered:
        yield Transition(
            "pm_terminal_closure_card_delivered_after_completion_projection",
            replace(state, holder="pm", pm_terminal_closure_card_delivered=True),
        )
        return

    yield Transition(
        "completion_recorded_after_final_replay",
        replace(state, status="complete", holder="pm"),
    )
