"""Transition helpers for ``flowpilot_control_plane_friction_model``."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from flowguard import FunctionResult

from flowpilot_control_plane_friction_model_state import (
    Action,
    State,
    Tick,
    Transition,
    initial_state,
)


class ControlPlaneStep:
    """Model one FlowPilot control-plane handoff transition.

    Input x State -> Set(Output x State)
    reads: package scope, packet receipts, blocker lane, lifecycle authorities,
    snapshot freshness, and optimized transaction markers
    writes: one durable control-plane fact or terminal status
    idempotency: each fact is monotonic; repeated ticks do not duplicate
    receipts or reopen sealed bodies
    """

    name = "ControlPlaneStep"
    input_description = "control-plane handoff tick"
    output_description = "one FlowPilot friction-control transition"
    reads = (
        "controller_boundary",
        "research_package",
        "packet_receipts",
        "control_blocker_lane",
        "lifecycle_authorities",
        "active_snapshot",
        "status_summary",
        "role_memory",
    )
    writes = (
        "package_materialization",
        "packet_transaction_receipt",
        "ack_transaction_receipt",
        "pending_wait_reconciliation",
        "status_summary",
        "role_memory_delta",
        "blocker_route",
        "lifecycle_reconciliation",
        "snapshot_refresh",
        "terminal_status",
    )
    idempotency = "monotonic state facts; optimized transaction records one composite receipt"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )

def _inc(state: State, **changes: object) -> State:
    return replace(state, handoff_steps=state.handoff_steps + 1, **changes)

def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "complete":
        return

    if not state.controller_boundary_confirmed:
        yield Transition(
            "controller_boundary_confirmed_envelope_only",
            _inc(
                state,
                status="running",
                controller_boundary_confirmed=True,
                controller_user_reporting_policy_present=True,
                router_action_user_reporting_reminder_present=True,
                controller_table_prompt_user_language_guidance_present=True,
                user_report_plain_language=True,
                user_report_internal_metadata_exposed=False,
                router_action_user_reporting_reminder_displayed_to_user=False,
            ),
        )
        return

    if state.mode == "unknown":
        yield Transition("select_expanded_safe_flow", _inc(state, mode="expanded"))
        yield Transition("select_optimized_transaction_flow", _inc(state, mode="optimized"))
        return

    if not state.stateful_controller_receipt_done:
        yield Transition(
            "controller_applies_stateful_postcondition_before_done_receipt",
            _inc(
                state,
                holder="controller",
                stateful_controller_receipt_done=True,
                stateful_controller_postcondition_declared=True,
                stateful_controller_postcondition_evidence_written=True,
                stateful_controller_advanced_from_receipt=True,
            ),
        )
        return

    if not state.controller_delivery_receipt_done:
        yield Transition(
            "controller_delivery_done_starts_target_role_wait",
            _inc(
                state,
                holder="controller",
                controller_delivery_receipt_done=True,
                controller_delivery_target_role_wait_started=True,
                controller_delivery_used_as_role_completion=False,
                controller_delivery_missing_role_output_blocker=False,
            ),
        )
        return

    if not state.router_owned_postcondition_reclaimed_from_artifact:
        yield Transition(
            "router_reclaims_valid_router_owned_artifact_before_blocker",
            _inc(
                state,
                holder="router",
                router_owned_artifact_exists=True,
                router_owned_artifact_proof_valid=True,
                router_tick_saw_receipt_before_flag=True,
                router_owned_postcondition_reclaimed_from_artifact=True,
                router_tick_escalated_before_reclaim=False,
                stateful_controller_postcondition_evidence_written=True,
                stateful_controller_advanced_from_receipt=True,
            ),
        )
        return

    if not state.controller_display_work_soft_recorded:
        yield Transition(
            "controller_display_work_soft_recorded_without_hard_gate",
            _inc(
                state,
                holder="controller",
                controller_display_work_soft_recorded=True,
                controller_display_work_hard_postcondition=False,
                controller_display_work_escalated_to_pm=False,
            ),
        )
        return

    if not state.external_keepalive_confirmed:
        yield Transition(
            "external_keepalive_action_confirmed_with_light_marker",
            _inc(
                state,
                holder="controller",
                external_keepalive_confirmation_required=True,
                external_keepalive_confirmed=True,
            ),
        )
        return

    if not state.signed_envelope_migration_sidecar_written:
        yield Transition(
            "signed_material_migration_preserves_relayed_envelope",
            _inc(
                state,
                signed_envelope_relayed=True,
                signed_envelope_rewritten_after_relay=False,
                signed_envelope_migration_sidecar_written=True,
                signed_envelope_mutable_indexes_backfilled=True,
            ),
        )
        return

    if not state.control_blocker_action_identity_includes_blocker:
        yield Transition(
            "control_blocker_action_identity_bound_to_artifact",
            _inc(
                state,
                control_blocker_action_identity_includes_blocker=True,
                controller_action_closed_identity_reused=False,
            ),
        )
        return

    if not state.control_blocker_receipt_effect_applied:
        yield Transition(
            "control_blocker_done_receipt_applies_delivery_postcondition",
            _inc(
                state,
                control_blocker_receipt_postcondition_declared=True,
                control_blocker_receipt_effect_applied=True,
            ),
        )
        return

    if not state.stale_run_state_preserved_wait_clear:
        yield Transition(
            "stale_run_state_save_preserves_cleared_wait_projection",
            _inc(
                state,
                current_wait_derived_from_obligation=True,
                stale_run_state_save_seen=True,
                latest_state_cleared_wait=True,
                stale_run_state_pending_matches_loaded_wait=True,
                stale_run_state_preserved_wait_clear=True,
                stale_run_state_resurrected_closed_wait=False,
            ),
        )
        return

    if not state.self_check_parser_status_pass_accepted:
        yield Transition(
            "self_check_status_pass_parser_aligned",
            _inc(
                state,
                self_check_template_status_pass_allowed=True,
                self_check_parser_status_pass_accepted=True,
            ),
        )
        return

    if not state.pm_research_package_written:
        yield Transition(
            "pm_writes_research_package_with_scope_fields",
            _inc(
                state,
                holder="pm",
                pm_research_package_written=True,
                research_package_has_decision_question=True,
                research_package_has_allowed_sources=True,
                research_package_has_stop_conditions=True,
            ),
        )
        return

    if not state.research_capability_decision_recorded:
        yield Transition(
            "pm_records_research_capability_decision_preserving_package_scope",
            _inc(state, holder="pm", research_capability_decision_recorded=True),
        )
        return

    if not state.worker_packet_written:
        yield Transition(
            "worker_packet_materialized_with_research_scope",
            _inc(
                state,
                holder="controller",
                worker_packet_written=True,
                worker_packet_preserves_research_fields=True,
            ),
        )
        return

    if not state.material_dispatch_reviewed:
        yield Transition(
            "router_direct_material_scan_dispatch_after_packet_integrity_check",
            _inc(
                state,
                holder="controller",
                material_dispatch_requested=True,
                material_dispatch_reviewed=True,
                material_dispatch_allowed=True,
                material_dispatch_phase_context_consistent=True,
                material_dispatch_output_contract_consistent=True,
                material_dispatch_write_target_explicit=True,
                material_dispatch_single_canonical_body=True,
            ),
        )
        return

    if state.mode == "optimized":
        if not state.optimized_card_ack_transaction:
            yield Transition(
                "optimized_card_ack_auto_consumed_with_validation",
                _inc(
                    state,
                    optimized_card_ack_transaction=True,
                    card_ack_validated=True,
                    card_ack_role_checked=True,
                    card_ack_hash_checked=True,
                ),
            )
            return
        if not state.optimized_relay_transaction:
            yield Transition(
                "optimized_relay_transaction_records_delivery_open_and_hash",
                _inc(
                    state,
                    holder="pm",
                    packet_delivered=True,
                    packet_body_open_receipt=True,
                    result_returned=True,
                    result_routed_to_pm=True,
                    result_body_open_receipt=True,
                    pm_result_disposition_recorded=True,
                    pm_formal_review_package_released=True,
                    pm_formal_review_package_has_artifact=True,
                    pm_formal_review_package_hash_recorded=True,
                    pm_formal_review_package_scope_declared=True,
                    optimized_relay_transaction=True,
                    optimized_transaction_records_delivery=True,
                    optimized_transaction_records_open_receipts=True,
                    optimized_transaction_records_result_return=True,
                    role_identity_checked=True,
                    hash_verified=True,
                ),
            )
            return

        if not state.pending_wait_reconciled:
            yield Transition(
                "pending_wait_reconciled_from_packet_status",
                _inc(
                    state,
                    pending_wait_reconciled=True,
                    pending_wait_reconciliation_uses_packet_ledger=True,
                    pending_wait_reconciliation_uses_status_packet=True,
                    pending_wait_reconciliation_role_verified=True,
                    pending_wait_reconciliation_hash_verified=True,
                    pending_wait_reconciliation_from_chat=False,
                    stale_wait_pending=True,
                    durable_result_evidence_exists=True,
                    stale_wait_reissued_without_reconciliation=False,
                    partial_batch_active=True,
                    partial_batch_packet_count=2,
                    partial_batch_results_returned=1,
                    partial_batch_result_refreshed_from_members=True,
                    partial_batch_missing_role_summary_accurate=True,
                    status_summary_waiting_role_matches_partial_batch=True,
                    duplicate_reconciliation_incremented_count=False,
                ),
            )
            return
    else:
        if not state.packet_delivered:
            yield Transition("packet_delivered_by_controller", _inc(state, holder="worker", packet_delivered=True))
            return
        if not state.packet_body_open_receipt:
            yield Transition(
                "target_records_packet_body_open_receipt",
                _inc(state, holder="worker", packet_body_open_receipt=True, role_identity_checked=True, hash_verified=True),
            )
            return
        if not state.result_returned:
            yield Transition("worker_result_returned_to_ledger", _inc(state, holder="controller", result_returned=True))
            return
        if not state.result_routed_to_pm:
            yield Transition(
                "controller_routes_result_to_pm_after_ledger_check",
                _inc(state, holder="pm", result_routed_to_pm=True),
            )
            return
        if not state.result_body_open_receipt:
            yield Transition(
                "pm_records_result_body_open_receipt",
                _inc(state, holder="pm", result_body_open_receipt=True),
            )
            return
        if not state.pm_result_disposition_recorded:
            yield Transition(
                "pm_records_package_result_disposition",
                _inc(state, holder="pm", pm_result_disposition_recorded=True),
            )
            return
        if not state.pm_formal_review_package_released:
            yield Transition(
                "pm_releases_formal_gate_package_to_reviewer",
                _inc(
                    state,
                    holder="reviewer",
                    pm_formal_review_package_released=True,
                    pm_formal_review_package_has_artifact=True,
                    pm_formal_review_package_hash_recorded=True,
                    pm_formal_review_package_scope_declared=True,
                ),
            )
            return

    if not state.pm_role_work_result_normalized:
        yield Transition(
            "role_work_result_recipient_normalized_by_packet_type",
            _inc(
                state,
                pm_role_work_result_normalized=True,
                pm_role_work_result_routes_to_pm=True,
                current_node_result_routes_to_pm=True,
            ),
        )
        return

    if not state.model_miss_officer_report_complete:
        yield Transition(
            "model_miss_officer_report_complete_for_pm_decision",
            _inc(
                state,
                holder="process_flowguard_officer",
                model_miss_officer_report_complete=True,
                model_miss_pm_decision_from_single_report=True,
            ),
        )
        return

    if not state.role_memory_delta_written:
        yield Transition(
            "role_memory_delta_written_as_non_authority_index",
            _inc(
                state,
                role_memory_delta_written=True,
                role_memory_used_for_authority=False,
            ),
        )
        return

    if not state.reviewer_report_written:
        yield Transition(
            "reviewer_writes_report_after_receipts",
            _inc(state, holder="reviewer", reviewer_report_written=True),
        )
        return

    if not state.reviewer_report_accepted:
        yield Transition(
            "router_accepts_reviewer_report",
            _inc(state, holder="controller", reviewer_report_accepted=True),
        )
        return

    if not state.pm_material_understanding_written:
        yield Transition(
            "pm_material_understanding_written_to_canonical_files",
            _inc(
                state,
                holder="pm",
                pm_material_understanding_written=True,
                pm_material_understanding_source_available=True,
            ),
        )
        return

    if not state.product_architecture_card_delivered:
        yield Transition(
            "product_architecture_card_delivered_with_material_context_and_fresh_views",
            _inc(
                state,
                holder="pm",
                product_architecture_card_delivered=True,
                product_architecture_delivery_has_material_context=True,
                phase_dependency_cards_delivered=True,
                phase_required_sources_complete=True,
                delivered_card_phase_context_fresh=True,
                stage_advanced_after_material_scan=True,
                frontier_fresh_after_stage_advance=True,
                product_stage_view_published=True,
                product_stage_view_fresh=True,
            ),
        )
        return

    if not state.status_summary_published:
        yield Transition(
            "status_summary_published_from_public_state",
            _inc(
                state,
                status_summary_published=True,
                status_summary_fresh_against_frontier_and_packet=True,
                status_summary_metadata_only=True,
                status_summary_blocker_state_consistent=True,
                status_summary_progress_facts_present=True,
                status_summary_progress_level_count_valid=True,
                status_summary_progress_counts_valid=True,
                status_summary_progress_elapsed_valid_or_null=True,
                status_summary_progress_metadata_only=True,
            ),
        )
        return

    if not state.route_draft_written:
        yield Transition(
            "pm_writes_route_draft_with_nonempty_nodes",
            _inc(state, holder="pm", route_draft_written=True, route_draft_has_nodes=True),
        )
        return

    if state.route_draft_written and not state.route_process_check_card_delivered:
        yield Transition(
            "route_process_check_card_delivered_with_route_draft_context",
            _inc(state, holder="officer", route_process_check_card_delivered=True),
        )
        return

    if state.route_process_check_card_delivered and not state.route_process_check_passed:
        yield Transition(
            "process_officer_passes_route_check_after_nonempty_route",
            _inc(state, holder="controller", route_process_check_passed=True),
        )
        return

    if state.route_process_check_passed and not state.child_skill_gate_repair_flow_started:
        yield Transition(
            "reviewer_blocks_child_skill_gate_manifest_for_repair",
            _inc(
                state,
                holder="reviewer",
                child_skill_gate_repair_flow_started=True,
                gate_card_requires_semantic_outcome=True,
                gate_outcome_block_active=True,
                gate_outcome_block_gate_key="child_skill_gate_manifest",
                gate_outcome_pass_recorded=False,
                gate_outcome_pass_gate_key="none",
                gate_outcome_same_generation=True,
                gate_outcome_clear_target_matches_pass_gate=True,
            ),
        )
        return

    if state.gate_outcome_block_active and not state.child_skill_gate_pm_rewrote_after_block:
        yield Transition(
            "pm_rewrites_child_skill_gate_after_block",
            _inc(
                state,
                holder="project_manager",
                child_skill_gate_pm_rewrote_after_block=True,
            ),
        )
        return

    if (
        state.child_skill_gate_pm_rewrote_after_block
        and not state.card_ack_consumed
        and not state.role_event_arrived_while_ack_pending
    ):
        yield Transition(
            "role_event_arrives_after_valid_card_ack_before_ledger_resolved",
            _inc(
                state,
                holder="router",
                pending_card_return_kind="system_card_bundle",
                pending_card_return_ack_file_present=True,
                pending_card_return_ack_valid=True,
                pending_card_return_ack_role_checked=True,
                pending_card_return_ack_hash_checked=True,
                pending_card_return_bundle_receipts_complete=True,
                card_return_ledger_resolved=False,
                role_event_arrived_while_ack_pending=True,
                role_event_blocked_by_unresolved_card_return=False,
                pre_event_role_wait_authority_present=True,
                pre_event_role_wait_authority_preserved=True,
                role_event_accepted_after_pre_event_ack=False,
                pre_event_ack_selected_matching_pending_return=True,
                duplicate_completed_return_written=False,
            ),
        )
        yield Transition(
            "role_event_arrives_before_missing_card_ack",
            _inc(
                state,
                holder="router",
                pending_card_return_kind="system_card",
                pending_card_return_ack_file_present=False,
                pending_card_return_ack_valid=False,
                pending_card_return_ack_role_checked=False,
                pending_card_return_ack_hash_checked=False,
                pending_card_return_bundle_receipts_complete=True,
                card_return_ledger_resolved=False,
                role_event_arrived_while_ack_pending=True,
                role_event_blocked_by_unresolved_card_return=False,
                pending_return_dependency_matches_report=True,
                missing_ack_report_arrived=True,
                missing_ack_report_quarantined=False,
                same_role_ack_recovery_requested=False,
                missing_ack_report_event_flag_set=False,
                quarantined_report_used_as_evidence=False,
                old_pre_ack_report_revived=False,
                report_submitted_after_valid_ack=False,
                missing_ack_generic_pm_blocker_created=False,
            ),
        )
        yield Transition(
            "router_consumes_gate_card_ack_and_preserves_semantic_wait",
            _inc(
                state,
                holder="controller",
                pending_card_return_kind="system_card",
                pending_card_return_ack_file_present=True,
                pending_card_return_ack_valid=True,
                pending_card_return_ack_role_checked=True,
                pending_card_return_ack_hash_checked=True,
                pending_card_return_bundle_receipts_complete=True,
                card_return_ledger_resolved=True,
                card_ack_consumed=True,
                semantic_gate_wait_exposed_after_ack=True,
            ),
        )
        return

    if (
        state.missing_ack_report_arrived
        and not state.missing_ack_report_quarantined
        and state.pending_return_dependency_matches_report
    ):
        yield Transition(
            "router_quarantines_pre_ack_report_and_requests_same_role_ack_recovery",
            _inc(
                state,
                holder="router",
                missing_ack_report_quarantined=True,
                same_role_ack_recovery_requested=True,
                missing_ack_report_event_flag_set=False,
                missing_ack_generic_pm_blocker_created=False,
                role_event_blocked_by_unresolved_card_return=False,
            ),
        )
        return

    if (
        state.missing_ack_report_quarantined
        and state.same_role_ack_recovery_requested
        and not state.card_return_ledger_resolved
    ):
        yield Transition(
            "same_role_reads_card_and_submits_valid_ack_after_quarantine",
            _inc(
                state,
                holder="router",
                pending_card_return_ack_file_present=True,
                pending_card_return_ack_valid=True,
                pending_card_return_ack_role_checked=True,
                pending_card_return_ack_hash_checked=True,
                pending_card_return_bundle_receipts_complete=True,
                card_return_ledger_resolved=True,
                card_ack_consumed=True,
                semantic_gate_wait_exposed_after_ack=True,
            ),
        )
        return

    if (
        state.missing_ack_report_quarantined
        and state.card_return_ledger_resolved
        and state.card_ack_consumed
        and not state.role_event_accepted_after_pre_event_ack
    ):
        yield Transition(
            "same_role_resubmits_fresh_report_after_valid_ack",
            _inc(
                state,
                holder="router",
                role_event_accepted_after_pre_event_ack=True,
                report_submitted_after_valid_ack=True,
                old_pre_ack_report_revived=False,
                missing_ack_report_event_flag_set=True,
            ),
        )
        return

    if (
        state.role_event_arrived_while_ack_pending
        and state.pending_card_return_ack_file_present
        and not state.pre_event_card_ack_auto_consumed
    ):
        yield Transition(
            "router_pre_consumes_valid_card_ack_before_role_event",
            _inc(
                state,
                holder="router",
                pre_event_card_ack_auto_consumed=True,
                card_return_ledger_resolved=True,
                card_ack_consumed=True,
                semantic_gate_wait_exposed_after_ack=True,
                role_event_blocked_by_unresolved_card_return=False,
                pre_event_role_wait_authority_preserved=True,
                role_event_accepted_after_pre_event_ack=True,
                pre_event_ack_selected_matching_pending_return=True,
                duplicate_completed_return_written=False,
            ),
        )
        return

    if (
        state.child_skill_gate_pm_rewrote_after_block
        and not state.card_ack_consumed
    ):
        yield Transition(
            "router_consumes_gate_card_ack_and_preserves_semantic_wait",
            _inc(
                state,
                holder="controller",
                card_ack_consumed=True,
                semantic_gate_wait_exposed_after_ack=True,
            ),
        )
        return

    if state.card_ack_consumed and not state.gate_outcome_pass_recorded:
        yield Transition(
            "reviewer_passes_repaired_child_skill_gate_and_clears_block",
            _inc(
                state,
                holder="reviewer",
                child_skill_gate_review_recorded=True,
                child_skill_gate_manifest_synced_with_review=True,
                gate_outcome_block_active=False,
                gate_outcome_pass_recorded=True,
                gate_outcome_pass_gate_key="child_skill_gate_manifest",
                gate_outcome_same_generation=True,
                gate_outcome_clear_target_matches_pass_gate=True,
                followup_event_expected_role="human_like_reviewer",
                followup_event_from_role="human_like_reviewer",
            ),
        )
        return

    if state.route_process_check_passed and state.review_block_scope == "none":
        yield Transition(
            "reviewer_block_classified_as_node_local",
            _inc(
                state,
                holder="project_manager",
                review_block_observed=True,
                review_block_scope="node_local",
            ),
        )
        yield Transition(
            "reviewer_block_classified_as_route_invalidating",
            _inc(
                state,
                holder="project_manager",
                review_block_observed=True,
                review_block_scope="route_invalidating",
            ),
        )
        return

    if state.review_block_scope == "node_local":
        if not state.pm_selected_same_node_repair:
            yield Transition(
                "pm_selects_same_node_repair_for_node_local_block",
                _inc(
                    state,
                    holder="project_manager",
                    pm_selected_same_node_repair=True,
                    same_node_repair_path_routable=True,
                ),
            )
            return
        if not state.fresh_repair_evidence_written:
            yield Transition(
                "same_node_repair_writes_fresh_plan_or_result",
                _inc(
                    state,
                    holder="project_manager",
                    fresh_repair_evidence_written=True,
                    stale_blocked_evidence_reused_as_pass=False,
                ),
            )
            return
        if not state.same_review_class_rechecked_repair:
            yield Transition(
                "same_reviewer_rechecks_repair_before_continue",
                _inc(
                    state,
                    holder="reviewer",
                    same_review_class_rechecked_repair=True,
                ),
            )
            return

    if state.review_block_scope == "route_invalidating":
        if not state.pm_selected_route_mutation:
            yield Transition(
                "pm_selects_route_mutation_for_route_invalidating_block",
                _inc(
                    state,
                    holder="project_manager",
                    pm_selected_route_mutation=True,
                    current_node_cannot_contain_repair_reason_present=True,
                ),
            )
            return
        if not state.route_draft_repaired_after_check:
            yield Transition(
                "route_mutation_resets_route_checks_for_reapproval",
                _inc(
                    state,
                    holder="controller",
                    route_process_check_card_delivered=False,
                    route_process_check_passed=False,
                    route_draft_repaired_after_check=True,
                    route_review_flags_reset_after_draft_repair=True,
                ),
            )
            return

    if not state.role_work_wait_pending:
        yield Transition(
            "controller_waits_for_role_work_with_status_packet_read",
            _inc(
                state,
                holder="controller",
                role_work_wait_pending=True,
                role_work_status_packet_exists=True,
                role_work_status_packet_read_allowed=True,
                role_work_status_visibility_grant="single_status_packet",
            ),
        )
        return

    if state.role_work_wait_pending and not state.role_work_progress_observed:
        yield Transition(
            "target_role_updates_progress_status_via_runtime",
            _inc(
                state,
                holder="process_flowguard_officer",
                role_work_progress_observed=True,
                role_work_progress_runtime_written=True,
                role_work_progress_numeric=True,
                role_work_progress_nonnegative=True,
                role_work_status_message_safe=True,
            ),
        )
        return

    if not state.role_output_wait_pending:
        yield Transition(
            "controller_waits_for_role_output_with_status_packet_read",
            _inc(
                state,
                holder="controller",
                work_package_progress_default_scope="all_work_packages",
                role_output_wait_pending=True,
                role_output_progress_prompt_inherited=True,
                role_output_status_packet_exists=True,
                role_output_status_packet_read_allowed=True,
                role_output_status_visibility_grant="single_status_packet",
            ),
        )
        return

    if state.role_output_wait_pending and not state.role_output_progress_observed:
        yield Transition(
            "target_role_updates_role_output_progress_via_runtime",
            _inc(
                state,
                holder="project_manager",
                role_output_progress_observed=True,
                role_output_progress_runtime_written=True,
                role_output_progress_numeric=True,
                role_output_progress_nonnegative=True,
                role_output_status_message_safe=True,
            ),
        )
        return

    if not state.role_output_event_submitted:
        yield Transition(
            "role_output_event_submitted_with_file_backed_body",
            _inc(
                state,
                holder="project_manager",
                role_output_event_submitted=True,
                role_output_event_accepted=True,
                role_output_file_backed_body_path_present=True,
                role_output_body_hash_verified=True,
                role_output_status_prepared_only=False,
                role_output_status_used_as_event_evidence=False,
            ),
        )
        return

    if not state.stop_requested:
        yield Transition("user_stop_requested", _inc(state, holder="controller", stop_requested=True))
        return

    if not state.current_status_stopped:
        yield Transition(
            "run_lifecycle_reconciled_all_authorities",
            _inc(
                state,
                current_status_stopped=True,
                continuation_heartbeat_active=False,
                crew_live_agents_active=False,
                packet_loop_active=False,
                frontier_terminal=True,
                terminal_snapshot_published=True,
                terminal_snapshot_flags_consistent=True,
                terminal_continuation_cleanup_recorded=True,
                terminal_host_automation_cleanup_proven=True,
            ),
        )
        return

    if not state.snapshot_published_as_active:
        yield Transition(
            "route_state_snapshot_refreshed_after_lifecycle_change",
            _inc(
                state,
                snapshot_published_as_active=True,
                snapshot_fresh_against_frontier_and_ledger=True,
            ),
        )
        return

    yield Transition("control_plane_flow_complete", replace(state, status="complete"))


__all__ = [
    "ControlPlaneStep",
    "next_safe_states",
]
