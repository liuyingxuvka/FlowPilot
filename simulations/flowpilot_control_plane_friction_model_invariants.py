"""Invariant helpers for ``flowpilot_control_plane_friction_model``."""

from __future__ import annotations

from flowguard import Invariant, InvariantResult

from flowpilot_control_plane_friction_model_state import (
    PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES,
    State,
)


def research_scope_preserved(state: State, trace) -> InvariantResult:
    del trace
    if state.worker_packet_written and not (
        state.research_package_has_decision_question
        and state.research_package_has_allowed_sources
        and state.research_package_has_stop_conditions
        and state.worker_packet_preserves_research_fields
    ):
        return InvariantResult.fail(
            "worker research packet was materialized after PM package scope fields were dropped"
        )
    return InvariantResult.pass_()

def material_scan_dispatch_requires_packet_integrity(state: State, trace) -> InvariantResult:
    del trace
    if state.material_dispatch_requested and not (
        state.material_dispatch_phase_context_consistent
        and state.material_dispatch_output_contract_consistent
        and state.material_dispatch_write_target_explicit
        and state.material_dispatch_single_canonical_body
    ):
        return InvariantResult.fail(
            "material scan dispatch request had inconsistent phase, output contract, write-target, or canonical-body state"
        )
    if state.material_dispatch_allowed and not state.material_dispatch_reviewed:
        return InvariantResult.fail(
            "material scan dispatch was allowed before router direct-dispatch preflight"
        )
    return InvariantResult.pass_()

def reviewer_report_requires_open_receipts(state: State, trace) -> InvariantResult:
    del trace
    if state.reviewer_report_accepted and not (
        state.packet_delivered
        and state.packet_body_open_receipt
        and state.result_returned
        and state.result_routed_to_pm
        and state.result_body_open_receipt
        and state.pm_result_disposition_recorded
        and state.pm_formal_review_package_released
    ):
        return InvariantResult.fail(
            "reviewer report was accepted before delivery, packet-open, result-return, PM relay, PM disposition, formal gate package, and result-open receipts existed"
        )
    return InvariantResult.pass_()

def formal_gate_package_release_requires_artifact(state: State, trace) -> InvariantResult:
    del trace
    if state.pm_formal_review_package_released and not (
        state.pm_formal_review_package_has_artifact
        and state.pm_formal_review_package_hash_recorded
        and state.pm_formal_review_package_scope_declared
    ):
        return InvariantResult.fail(
            "PM formal gate package release lacked reviewer-readable artifact path, hash, or scope"
        )
    return InvariantResult.pass_()

def missing_receipt_uses_same_role_reissue(state: State, trace) -> InvariantResult:
    del trace
    if state.receipt_missing_blocker and not (
        state.control_blocker_lane == "control_plane_reissue"
        and state.control_blocker_target_role == "human_like_reviewer"
    ):
        return InvariantResult.fail(
            "missing receipt blocker was not routed as same-role reviewer control-plane reissue"
        )
    return InvariantResult.pass_()

def stopped_run_reconciles_authorities(state: State, trace) -> InvariantResult:
    del trace
    if state.current_status_stopped and (
        state.continuation_heartbeat_active
        or state.crew_live_agents_active
        or state.packet_loop_active
        or not state.frontier_terminal
    ):
        return InvariantResult.fail(
            "stopped run left heartbeat, crew, packet loop, or frontier authority active"
        )
    return InvariantResult.pass_()

def active_snapshot_is_fresh(state: State, trace) -> InvariantResult:
    del trace
    if state.snapshot_published_as_active and not state.snapshot_fresh_against_frontier_and_ledger:
        return InvariantResult.fail("active route_state_snapshot is stale against frontier or packet ledger")
    return InvariantResult.pass_()

def product_architecture_delivery_requires_material_context(state: State, trace) -> InvariantResult:
    del trace
    if state.product_architecture_card_delivered and not (
        state.pm_material_understanding_written
        and state.pm_material_understanding_source_available
        and state.product_architecture_delivery_has_material_context
    ):
        return InvariantResult.fail(
            "product architecture card was delivered without PM material-understanding source paths"
        )
    return InvariantResult.pass_()

def protocol_blockers_are_router_visible(state: State, trace) -> InvariantResult:
    del trace
    if state.protocol_blocker_file_written and not state.protocol_blocker_registered_in_router_state:
        return InvariantResult.fail("protocol blocker file existed without router-visible blocker registration")
    return InvariantResult.pass_()

def control_blocker_indexes_match_artifacts(state: State, trace) -> InvariantResult:
    del trace
    if state.control_blocker_artifact_status_written and not state.control_blocker_router_index_matches_artifact:
        return InvariantResult.fail("router control blocker index disagreed with control blocker artifact status")
    return InvariantResult.pass_()

def stateful_controller_receipts_require_postcondition_evidence(
    state: State, trace
) -> InvariantResult:
    del trace
    if (
        state.stateful_controller_receipt_done
        and state.stateful_controller_postcondition_declared
        and not state.stateful_controller_postcondition_evidence_written
    ):
        return InvariantResult.fail(
            "stateful controller receipt was marked done before Router-visible postcondition evidence existed"
        )
    if state.stateful_controller_advanced_from_receipt and not (
        state.stateful_controller_receipt_done
        and (
            not state.stateful_controller_postcondition_declared
            or state.stateful_controller_postcondition_evidence_written
        )
    ):
        return InvariantResult.fail(
            "stateful controller action advanced without a verified receipt and postcondition evidence"
        )
    return InvariantResult.pass_()

def controller_delivery_receipts_do_not_complete_target_work(state: State, trace) -> InvariantResult:
    del trace
    if state.controller_delivery_receipt_done and state.controller_delivery_host_status != "delivered":
        return InvariantResult.fail(
            "Controller delivery receipt was marked done without host delivery success"
        )
    if state.controller_delivery_used_as_role_completion:
        return InvariantResult.fail(
            "Controller delivery receipt was treated as target-role completion"
        )
    if state.controller_delivery_missing_role_output_blocker:
        return InvariantResult.fail(
            "Router created a missing role-output blocker from a Controller delivery receipt"
        )
    if state.controller_delivery_receipt_done and not state.controller_delivery_target_role_wait_started:
        return InvariantResult.fail(
            "Controller delivery receipt did not transition to a target-role wait"
        )
    return InvariantResult.pass_()

def pm_role_work_identity_is_work_unit_scoped(state: State, trace) -> InvariantResult:
    del trace
    if state.pm_role_work_closed_identity_reused_for_distinct_request:
        return InvariantResult.fail(
            "PM role-work action identity omitted batch, request, packet, or target role"
        )
    if (
        (state.pm_role_work_result_normalized or state.role_work_wait_pending)
        and not state.pm_role_work_identity_includes_batch_request_packet_role
    ):
        return InvariantResult.fail(
            "PM role-work wait or result used an identity that was not scoped to batch, request, packet, and target role"
        )
    if state.pm_role_work_open_request_masked_by_global_flag and not state.pm_role_work_request_postcondition_scoped:
        return InvariantResult.fail(
            "PM role-work global postcondition masked an open request-specific obligation"
        )
    return InvariantResult.pass_()

def active_holder_leases_require_host_liveness(state: State, trace) -> InvariantResult:
    del trace
    if state.active_holder_lease_issued and not (
        state.active_holder_agent_identity_recorded
        and state.active_holder_agent_host_live
        and state.active_holder_packet_role_matches
    ):
        return InvariantResult.fail(
            "active holder lease was issued without concrete agent identity, host liveness, and packet-role match"
        )
    return InvariantResult.pass_()

def packet_ledger_io_is_atomic_and_recoverable(state: State, trace) -> InvariantResult:
    del trace
    ledger_activity = (
        state.packet_delivered
        or state.result_returned
        or state.pending_wait_reconciled
        or (
            state.pm_repair_reissue_spec_written
            and state.pm_repair_reissue_packets_registered_in_ledger
        )
    )
    if ledger_activity and not (
        state.packet_ledger_write_atomic
        and state.packet_ledger_write_locked_or_cas
        and state.packet_ledger_readback_validated
    ):
        return InvariantResult.fail(
            "packet ledger write path lacked atomic unique-temp, lock/CAS, or readback validation"
        )
    if state.packet_ledger_corrupt_read_crashed_daemon:
        return InvariantResult.fail(
            "packet ledger corrupt read crashed the daemon instead of producing a recoverable control blocker"
        )
    if state.packet_ledger_corrupt_read_crashed_daemon is False and state.packet_ledger_corruption_recoverable is False:
        return InvariantResult.pass_()
    if not state.packet_ledger_corruption_recoverable:
        return InvariantResult.fail(
            "packet ledger corruption was not modeled as recoverable before daemon continuation"
        )
    return InvariantResult.pass_()

def material_gate_result_evidence_is_machine_and_authority_backed(
    state: State, trace
) -> InvariantResult:
    del trace
    if state.material_gate_depends_on_result_body and not state.result_self_check_machine_parseable:
        return InvariantResult.fail(
            "material gate depended on a result body whose Contract Self-Check was not machine-parseable"
        )
    if state.material_gate_depends_on_result_body and not state.result_reader_authority_matches_runtime:
        return InvariantResult.fail(
            "artifact map advertised result-body reader access that runtime relay authority did not grant"
        )
    return InvariantResult.pass_()

def router_owned_artifacts_are_reclaimed_before_blocker(state: State, trace) -> InvariantResult:
    del trace
    durable_artifact_valid = state.router_owned_artifact_exists and state.router_owned_artifact_proof_valid
    if (
        durable_artifact_valid
        and state.router_tick_saw_receipt_before_flag
        and not state.router_owned_postcondition_reclaimed_from_artifact
    ):
        return InvariantResult.fail(
            "valid Router-owned artifact/proof existed but Router did not reclaim the postcondition"
        )
    if durable_artifact_valid and state.router_tick_escalated_before_reclaim:
        return InvariantResult.fail(
            "daemon tick escalated a half-complete Controller receipt before durable artifact reclaim"
        )
    return InvariantResult.pass_()

def router_internal_postconditions_materialize_or_block(state: State, trace) -> InvariantResult:
    del trace
    ready_internal_postcondition = (
        state.router_internal_postcondition_due
        and state.router_internal_postcondition_inputs_ready
    )
    if ready_internal_postcondition and state.router_internal_postcondition_exposed_as_role_wait:
        return InvariantResult.fail(
            "router-owned internal postcondition was exposed as a Controller/role wait instead of materializing or blocking"
        )
    if ready_internal_postcondition and not (
        state.router_internal_postcondition_materialized
        or state.router_internal_postcondition_blocker_materialized
    ):
        return InvariantResult.fail(
            "router-owned internal postcondition had ready inputs but no materialized evidence or router-visible blocker"
        )
    if (
        state.router_internal_postcondition_exposed_as_role_wait
        and not state.router_internal_postcondition_expected_evidence_exists
        and not state.router_internal_postcondition_executable_action_pending
    ):
        return InvariantResult.fail(
            "passive wait advertised missing router-owned internal evidence without an executable owner action"
        )
    return InvariantResult.pass_()

def resolved_obligation_projections_are_cleared(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.resolved_obligation_evidence_exists
        and (
            state.resolved_obligation_live_passive_wait
            or state.resolved_obligation_live_blocked_reminder
        )
        and not state.resolved_obligation_projection_reconciled
    ):
        return InvariantResult.fail(
            "resolved Router obligation still had a live passive wait or blocked reminder projection"
        )
    return InvariantResult.pass_()

def controller_display_work_remains_nonblocking(state: State, trace) -> InvariantResult:
    del trace
    if state.controller_display_work_hard_postcondition:
        return InvariantResult.fail(
            "display/status controller work was treated as a hard postcondition gate"
        )
    if state.controller_display_work_escalated_to_pm:
        return InvariantResult.fail(
            "display/status controller work was escalated to PM repair"
        )
    return InvariantResult.pass_()

def external_keepalive_actions_require_light_confirmation(state: State, trace) -> InvariantResult:
    del trace
    if state.external_keepalive_confirmation_required and not state.external_keepalive_confirmed:
        return InvariantResult.fail(
            "external keepalive action lacked lightweight completion confirmation"
        )
    return InvariantResult.pass_()

def signed_envelopes_are_immutable_after_relay(state: State, trace) -> InvariantResult:
    del trace
    if state.signed_envelope_relayed and state.signed_envelope_rewritten_after_relay:
        return InvariantResult.fail(
            "signed packet or result envelope was rewritten after Controller relay hash binding"
        )
    if (
        state.signed_envelope_relayed
        and state.signed_envelope_mutable_indexes_backfilled
        and not state.signed_envelope_migration_sidecar_written
    ):
        return InvariantResult.fail(
            "signed envelope migration backfilled mutable projections without a sidecar record"
        )
    return InvariantResult.pass_()

def controller_action_identity_is_obligation_scoped(state: State, trace) -> InvariantResult:
    del trace
    if state.control_blocker_receipt_postcondition_declared and not state.control_blocker_action_identity_includes_blocker:
        return InvariantResult.fail(
            "control blocker Controller action identity omitted blocker artifact identity"
        )
    if state.controller_action_closed_identity_reused:
        return InvariantResult.fail(
            "closed Controller action row was reused for a different Router obligation identity"
        )
    return InvariantResult.pass_()

def control_blocker_receipts_apply_delivery_postcondition(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.control_blocker_receipt_postcondition_declared
        and not state.control_blocker_receipt_effect_applied
    ):
        return InvariantResult.fail(
            "control blocker done receipt did not apply the Router-visible delivery postcondition"
        )
    return InvariantResult.pass_()

def current_wait_projection_does_not_resurrect_closed_obligation(state: State, trace) -> InvariantResult:
    del trace
    if state.stale_run_state_resurrected_closed_wait:
        return InvariantResult.fail(
            "stale run-state save resurrected a closed Controller wait projection"
        )
    if (
        state.stale_run_state_save_seen
        and state.latest_state_cleared_wait
        and state.stale_run_state_pending_matches_loaded_wait
        and not state.stale_run_state_preserved_wait_clear
    ):
        return InvariantResult.fail(
            "stale run-state save did not preserve the latest cleared pending wait"
        )
    if state.stale_run_state_save_seen and not state.current_wait_derived_from_obligation:
        return InvariantResult.fail(
            "live pending wait was treated as independent state instead of an obligation projection"
        )
    return InvariantResult.pass_()

def self_check_parser_matches_template_vocabulary(state: State, trace) -> InvariantResult:
    del trace
    if state.self_check_template_status_pass_allowed and not state.self_check_parser_status_pass_accepted:
        return InvariantResult.fail(
            "Contract Self-Check parser rejected status: pass even though templates allow it"
        )
    return InvariantResult.pass_()

def role_output_events_require_file_backed_body(state: State, trace) -> InvariantResult:
    del trace
    if (
        (
            state.role_output_event_submitted
            or state.role_output_event_accepted
            or state.pm_repair_decision_recorded
        )
        and not (
            state.role_output_file_backed_body_path_present
            and state.role_output_body_hash_verified
        )
    ):
        return InvariantResult.fail(
            "role output event was accepted without a file-backed body path and verified body hash"
        )
    if state.role_output_status_used_as_event_evidence or (
        state.role_output_status_prepared_only and state.role_output_event_accepted
    ):
        return InvariantResult.fail(
            "role output status/progress was used as role event evidence"
        )
    return InvariantResult.pass_()

def material_repair_generation_protocol_is_current(state: State, trace) -> InvariantResult:
    del trace
    if not state.material_repair_generation_protocol_checked:
        return InvariantResult.pass_()
    if not state.operation_replay_fresh_controller_action_id:
        return InvariantResult.fail(
            "operation replay reused a closed Controller action identity"
        )
    if not state.operation_replay_targets_current_generation:
        return InvariantResult.fail(
            "operation replay targeted a superseded material packet generation"
        )
    if not state.operation_replay_ledger_io_authorized:
        return InvariantResult.fail(
            "material result relay replay lacked current packet-ledger and material-index authority"
        )
    if not state.controller_repair_work_packet_receipt_folded:
        return InvariantResult.fail(
            "controller_repair_work_packet receipt did not fold the repair transaction"
        )
    if not state.controller_repair_work_packet_facade_exported:
        return InvariantResult.fail(
            "controller_repair_work_packet receipt helper was not exported through the Router facade"
        )
    if not (
        state.pm_material_disposition_generation_scoped
        and state.pm_material_disposition_matches_current_generation
    ):
        return InvariantResult.fail(
            "PM material result disposition was not scoped to the current packet generation"
        )
    if state.stale_pm_material_disposition_restored:
        return InvariantResult.fail(
            "stale PM material disposition was restored as current-generation success"
        )
    if not (
        state.material_progress_projection_generation_scoped
        and state.material_global_progress_flags_match_active_generation
    ):
        return InvariantResult.fail(
            "material progress flags were not scoped to the active material generation"
        )
    if not state.material_next_action_derived_from_active_batch:
        return InvariantResult.fail(
            "material next action was derived from stale run-wide material flags instead of active batch state"
        )
    if not state.material_reissue_clears_or_quarantines_stale_progress_flags:
        return InvariantResult.fail(
            "material packet reissue left superseded progress flags visible for the current generation"
        )
    if not state.stale_run_state_save_preserves_material_generation_flag_clear:
        return InvariantResult.fail(
            "stale run-state save restored superseded material progress flags after current generation reset"
        )
    if not state.material_dispatch_block_matches_active_generation:
        return InvariantResult.fail(
            "material dispatch protocol block referenced a superseded repair generation"
        )
    return InvariantResult.pass_()

def role_event_identity_and_audit_records_are_closed(state: State, trace) -> InvariantResult:
    del trace
    if not state.material_repair_generation_protocol_checked:
        return InvariantResult.pass_()
    if not state.role_output_event_deduped_by_body_ref:
        return InvariantResult.fail(
            "role-output events were not deduped by event type and body reference"
        )
    if not state.role_output_current_generation_not_short_circuited_by_global_flag:
        return InvariantResult.fail(
            "role-output reconciliation short-circuited current-generation material event on a run-wide flag"
        )
    if not state.role_output_package_disposition_domain_first_commit:
        return InvariantResult.fail(
            "role-output package disposition reconciliation recorded event progress before domain artifact commit"
        )
    if not (
        state.pm_package_authority_split_preserves_wait
        or state.pm_package_authority_split_repairs_domain_commit
    ):
        return InvariantResult.fail(
            "recorded PM package disposition without canonical authority closed the legal wait before preserving it or repairing the canonical domain commit"
        )
    if state.pm_package_authority_split_crashed_daemon:
        return InvariantResult.fail(
            "recorded PM package disposition without canonical authority crashed the daemon"
        )
    if state.pm_package_authority_split_accepted_as_success:
        return InvariantResult.fail(
            "recorded PM package disposition without canonical authority was accepted as successful progress"
        )
    if state.duplicate_role_event_side_effect_written:
        return InvariantResult.fail(
            "duplicate role-output event wrote a duplicate side effect"
        )
    if not state.pm_package_disposition_semantic_identity_deduped:
        return InvariantResult.fail(
            "PM package dispositions were not deduped by semantic batch identity"
        )
    if not state.pm_package_disposition_body_hash_conflict_checked:
        return InvariantResult.fail(
            "PM package disposition body_hash was not checked as conflict evidence"
        )
    if not state.pm_package_repair_owned_conflict_replay_quarantined:
        return InvariantResult.fail(
            "repair-owned PM package disposition body_hash conflict replay was not quarantined"
        )
    if not state.pm_package_repair_owned_conflict_preserves_wait:
        return InvariantResult.fail(
            "repair-owned PM package disposition body_hash conflict replay did not preserve the legal wait"
        )
    if state.pm_package_repair_owned_conflict_crashed_daemon:
        return InvariantResult.fail(
            "repair-owned PM package disposition body_hash conflict replay crashed the daemon"
        )
    if state.pm_package_repair_owned_conflict_accepted_as_success:
        return InvariantResult.fail(
            "repair-owned PM package disposition body_hash conflict replay was accepted as a successful disposition"
        )
    if state.pm_package_repair_owned_conflict_duplicate_blocker:
        return InvariantResult.fail(
            "repair-owned PM package disposition body_hash conflict replay created a duplicate blocker"
        )
    if not state.pm_package_stale_unowned_conflict_replay_quarantined:
        return InvariantResult.fail(
            "stale unowned PM package disposition body_hash conflict replay was not quarantined"
        )
    if not state.pm_package_stale_unowned_conflict_preserves_canonical:
        return InvariantResult.fail(
            "stale unowned PM package disposition body_hash conflict replay did not preserve canonical body"
        )
    if state.pm_package_stale_unowned_conflict_crashed_daemon:
        return InvariantResult.fail(
            "stale unowned PM package disposition body_hash conflict replay crashed the daemon"
        )
    if state.pm_package_stale_unowned_conflict_accepted_as_success:
        return InvariantResult.fail(
            "stale unowned PM package disposition body_hash conflict replay was accepted as a successful disposition"
        )
    if not state.pm_package_packet_outcomes_recorded:
        return InvariantResult.fail(
            "PM package disposition did not record per-packet outcomes"
        )
    if not state.break_glass_patch_validation_finalized:
        return InvariantResult.fail(
            "break-glass patch record remained pending validation after validation evidence existed"
        )
    return InvariantResult.pass_()

def packet_result_authority_is_ledger_replayable(state: State, trace) -> InvariantResult:
    del trace
    if not state.material_repair_generation_protocol_checked:
        return InvariantResult.pass_()
    if not state.packet_result_author_identity_replayable:
        return InvariantResult.fail(
            "packet result author identity was not replayable from the packet ledger"
        )
    if not state.packet_result_author_matches_current_role:
        return InvariantResult.fail(
            "packet result author identity did not match the current runtime responsibility binding"
        )
    return InvariantResult.pass_()

def pm_repair_followup_events_are_matchable(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.control_blocker_lane in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES
        and state.pm_repair_decision_recorded
        and (
            not state.control_blocker_followup_event_matchable
            or not state.control_resolution_predicate_normalized
        )
    ):
        return InvariantResult.fail(
            "PM repair follow-up event could not be matched by normalized router resolution logic"
        )
    return InvariantResult.pass_()

def pm_repair_reissue_requires_packet_runtime_materialization(
    state: State, trace
) -> InvariantResult:
    del trace
    if (
        state.control_blocker_lane in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES
        and state.pm_repair_decision_recorded
        and state.pm_repair_reissue_spec_written
        and not (
            state.pm_repair_reissue_packet_files_materialized
            and state.pm_repair_reissue_packets_registered_in_ledger
            and state.pm_repair_reissue_dispatch_index_updated
        )
    ):
        return InvariantResult.fail(
            "PM repair reissue specs did not materialize into packet runtime files, ledger, and dispatch index"
        )
    return InvariantResult.pass_()

def pm_repair_recheck_outcomes_remain_routable(state: State, trace) -> InvariantResult:
    del trace
    repair_runtime_ready = (
        state.pm_repair_reissue_packet_files_materialized
        and state.pm_repair_reissue_packets_registered_in_ledger
        and state.pm_repair_reissue_dispatch_index_updated
    )
    needs_failure_route = (
        state.pm_repair_reissue_spec_written and not repair_runtime_ready
    ) or state.reviewer_recheck_protocol_blocker_written
    if (
        state.control_blocker_lane in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES
        and state.pm_repair_decision_recorded
        and needs_failure_route
        and (
            state.pm_repair_allowed_success_only
            or not state.pm_repair_non_success_outcome_routable
            or not state.reviewer_recheck_protocol_blocker_routable
        )
    ):
        return InvariantResult.fail(
            "PM repair recheck allowed only success while reviewer blocker or protocol outcome was not routable"
        )
    return InvariantResult.pass_()

def repair_success_clears_stale_repair_lane(state: State, trace) -> InvariantResult:
    del trace
    if state.active_repair_transaction_stale or state.repair_recheck_pending_action_stale:
        return InvariantResult.fail(
            "repair transaction success left stale active repair transaction or repair recheck pending action"
        )
    return InvariantResult.pass_()

def expected_role_decisions_require_satisfied_flags(state: State, trace) -> InvariantResult:
    del trace
    if state.expected_role_decision_requires_unsatisfied_flag:
        return InvariantResult.fail(
            "await_role_decision exposed an external event whose requires_flag was false"
        )
    return InvariantResult.pass_()

def delivered_cards_include_required_phase_sources(state: State, trace) -> InvariantResult:
    del trace
    if state.phase_dependency_cards_delivered and not state.phase_required_sources_complete:
        return InvariantResult.fail("delivered phase card was missing required upstream source paths")
    return InvariantResult.pass_()

def delivered_card_phase_context_is_fresh(state: State, trace) -> InvariantResult:
    del trace
    if state.phase_dependency_cards_delivered and not state.delivered_card_phase_context_fresh:
        return InvariantResult.fail("delivered card current_phase did not match its actual workflow phase")
    return InvariantResult.pass_()

def terminal_snapshot_flags_match_terminal_state(state: State, trace) -> InvariantResult:
    del trace
    if state.terminal_snapshot_published and not state.terminal_snapshot_flags_consistent:
        return InvariantResult.fail("terminal route_state_snapshot flags disagreed with terminal run status")
    return InvariantResult.pass_()

def child_skill_gate_manifest_syncs_review_status(state: State, trace) -> InvariantResult:
    del trace
    if state.child_skill_gate_review_recorded and not state.child_skill_gate_manifest_synced_with_review:
        return InvariantResult.fail("child-skill gate manifest did not sync reviewer pass status")
    return InvariantResult.pass_()

def gate_pass_clears_matching_current_block(state: State, trace) -> InvariantResult:
    del trace
    if state.gate_outcome_pass_recorded and not state.gate_outcome_clear_target_matches_pass_gate:
        return InvariantResult.fail("gate pass cleared a different gate outcome block")
    if (
        state.gate_outcome_pass_recorded
        and state.gate_outcome_same_generation
        and state.gate_outcome_block_gate_key == state.gate_outcome_pass_gate_key
        and state.gate_outcome_block_active
    ):
        return InvariantResult.fail("gate pass left the matching active gate outcome block live")
    return InvariantResult.pass_()

def card_ack_preserves_semantic_gate_wait(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.card_ack_consumed
        and state.gate_card_requires_semantic_outcome
        and not state.semantic_gate_wait_exposed_after_ack
    ):
        return InvariantResult.fail("card ACK consumed the mechanical wait without exposing semantic gate outcome wait")
    return InvariantResult.pass_()

def followup_events_keep_event_role_authority(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.followup_event_expected_role == "human_like_reviewer"
        and state.followup_event_from_role
        and state.followup_event_from_role not in {"none", "human_like_reviewer"}
    ):
        return InvariantResult.fail("reviewer follow-up event was accepted from the PM repair target role")
    return InvariantResult.pass_()

def no_legal_next_waits_for_current_role_output(state: State, trace) -> InvariantResult:
    del trace
    if state.valid_role_output_waiting and state.no_legal_next_control_blocker_materialized:
        return InvariantResult.fail("no-legal-next control blocker was created while a valid role output was receivable")
    return InvariantResult.pass_()

def duplicate_pm_repair_decisions_are_idempotent(state: State, trace) -> InvariantResult:
    del trace
    if state.duplicate_pm_repair_decision_seen and state.duplicate_repair_created_new_blocker:
        return InvariantResult.fail("duplicate PM repair decision created a new control blocker")
    return InvariantResult.pass_()

def terminal_continuation_cleanup_is_proven(state: State, trace) -> InvariantResult:
    del trace
    if state.terminal_continuation_cleanup_recorded and not state.terminal_host_automation_cleanup_proven:
        return InvariantResult.fail("terminal continuation cleanup lacked host automation proof")
    return InvariantResult.pass_()

def role_output_hashes_are_replayable(state: State, trace) -> InvariantResult:
    del trace
    if state.role_output_envelopes_recorded and not state.role_output_hashes_replayable:
        return InvariantResult.fail("persisted role-output envelope hashes were not replayable against body paths")
    return InvariantResult.pass_()

def frontier_tracks_product_architecture_delivery(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.product_architecture_card_delivered
        and state.stage_advanced_after_material_scan
        and not state.frontier_fresh_after_stage_advance
    ):
        return InvariantResult.fail("execution frontier remained at material_scan after product architecture delivery")
    return InvariantResult.pass_()

def display_surfaces_track_product_architecture_delivery(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.product_architecture_card_delivered
        and state.product_stage_view_published
        and not state.product_stage_view_fresh
    ):
        return InvariantResult.fail("route snapshot or display plan remained stale after product architecture delivery")
    return InvariantResult.pass_()

def status_summary_is_public_and_fresh(state: State, trace) -> InvariantResult:
    del trace
    if state.status_summary_published and not state.status_summary_fresh_against_frontier_and_packet:
        return InvariantResult.fail("status summary was published stale against frontier or packet state")
    if state.status_summary_published and not state.status_summary_metadata_only:
        return InvariantResult.fail("status summary exposed sealed body, evidence table, source, or hash details")
    if state.status_summary_published and not state.status_summary_blocker_state_consistent:
        return InvariantResult.fail("status summary hid an unresolved blocker or pending repair state")
    if state.status_summary_published and not state.status_summary_progress_facts_present:
        return InvariantResult.fail("status summary omitted compact progress facts")
    if state.status_summary_published and not state.status_summary_progress_level_count_valid:
        return InvariantResult.fail("status summary progress facts had an invalid level count")
    if state.status_summary_published and not state.status_summary_progress_counts_valid:
        return InvariantResult.fail("status summary progress facts had inconsistent node counts")
    if state.status_summary_published and not state.status_summary_progress_elapsed_valid_or_null:
        return InvariantResult.fail("status summary elapsed runtime was neither valid nor null")
    if state.status_summary_published and not state.status_summary_progress_metadata_only:
        return InvariantResult.fail("status summary progress facts exposed internal metadata")
    if (
        state.partial_batch_active
        and state.partial_batch_results_returned > 0
        and not state.partial_batch_result_refreshed_from_members
    ):
        return InvariantResult.fail(
            "partial batch returned result was not reflected in member returned count"
        )
    if state.partial_batch_active and not state.partial_batch_missing_role_summary_accurate:
        return InvariantResult.fail(
            "partial batch missing-role summary was stale"
        )
    if (
        state.status_summary_published
        and state.partial_batch_active
        and not state.status_summary_waiting_role_matches_partial_batch
    ):
        return InvariantResult.fail(
            "status summary named a completed role instead of the remaining partial-batch role"
        )
    return InvariantResult.pass_()

def controller_user_reporting_policy_is_plain(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "new" and not state.controller_user_reporting_policy_present:
        return InvariantResult.fail("Controller user reporting policy was missing")
    if state.status != "new" and not state.router_action_user_reporting_reminder_present:
        return InvariantResult.fail("Router action lacked Controller plain-language user reporting reminder")
    if state.status != "new" and not state.controller_table_prompt_user_language_guidance_present:
        return InvariantResult.fail("Controller table prompt lacked plain-language user reporting guidance")
    if state.status != "new" and not state.controller_reporting_budget_present:
        return InvariantResult.fail("Controller user reporting policy lacked speak/silence budget")
    if not state.quiet_internal_progress_silent:
        return InvariantResult.fail("Controller quiet internal progress was user-visible chatter")
    if state.routine_process_aside_relayed_to_user:
        return InvariantResult.fail("Controller routine process aside was relayed to user")
    if not state.user_report_limited_to_meaningful_change:
        return InvariantResult.fail("Controller user report was not limited to meaningful user-facing changes")
    if state.controller_user_reporting_policy_present and not state.user_report_plain_language:
        return InvariantResult.fail("Controller user reporting policy did not require plain language")
    if state.user_report_internal_metadata_exposed:
        return InvariantResult.fail("Controller user report exposed internal action, packet, ledger, hash, contract, or diagnostic metadata")
    if state.router_action_user_reporting_reminder_displayed_to_user:
        return InvariantResult.fail("Router action user reporting reminder leaked into user-visible display text")
    return InvariantResult.pass_()

def route_checks_require_nonempty_route_nodes(state: State, trace) -> InvariantResult:
    del trace
    if state.route_process_check_card_delivered and not state.route_draft_has_nodes:
        return InvariantResult.fail("route process check was delivered for an empty route draft")
    if state.route_process_check_card_delivered and (
        not state.route_draft_single_canonical_source or state.route_draft_shadow_source_used
    ):
        return InvariantResult.fail(
            "route process check used a shadow route draft instead of the canonical route source"
        )
    return InvariantResult.pass_()

def route_draft_repair_resets_stale_route_checks(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.route_draft_repaired_after_check
        and not state.route_review_flags_reset_after_draft_repair
        and (state.route_process_check_card_delivered or state.route_process_check_passed)
    ):
        return InvariantResult.fail("route draft repair left stale route-check flags active")
    return InvariantResult.pass_()

def node_local_blocks_remain_same_node_routable(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.review_block_scope == "node_local"
        and state.pm_selected_route_mutation
        and not state.current_node_cannot_contain_repair_reason_present
    ):
        return InvariantResult.fail(
            "node-local reviewer block was escalated to route mutation without a current-node-incapability reason"
        )
    if state.pm_selected_same_node_repair and not state.same_node_repair_path_routable:
        return InvariantResult.fail("same-node reviewer-block repair had no router-routable follow-up path")
    return InvariantResult.pass_()

def route_invalidating_blocks_require_route_mutation(state: State, trace) -> InvariantResult:
    del trace
    if state.review_block_scope == "route_invalidating" and state.pm_selected_same_node_repair:
        return InvariantResult.fail("route-invalidating reviewer block was handled as same-node repair")
    if state.pm_selected_route_mutation and not state.current_node_cannot_contain_repair_reason_present:
        return InvariantResult.fail("route mutation lacked why the current node cannot contain the repair")
    if state.pm_selected_route_mutation and state.role_work_wait_pending and not (
        state.route_draft_repaired_after_check
        and state.route_process_check_card_delivered
        and state.route_process_check_passed
    ):
        return InvariantResult.fail("route mutation continued without resetting and rerunning route checks")
    return InvariantResult.pass_()

def same_node_repair_requires_fresh_evidence_and_recheck(state: State, trace) -> InvariantResult:
    del trace
    if state.pm_selected_same_node_repair and state.stale_blocked_evidence_reused_as_pass:
        return InvariantResult.fail("same-node repair reused stale blocked evidence as passing evidence")
    if state.same_review_class_rechecked_repair and not state.fresh_repair_evidence_written:
        return InvariantResult.fail("same-node repair was rechecked before fresh repair evidence existed")
    if (
        state.pm_selected_same_node_repair
        and state.fresh_repair_evidence_written
        and state.role_work_wait_pending
        and not state.same_review_class_rechecked_repair
    ):
        return InvariantResult.fail("same-node repair continued without same-review-class recheck")
    return InvariantResult.pass_()

def multi_active_requires_explicit_authority(state: State, trace) -> InvariantResult:
    del trace
    if state.multiple_running_index_entries_visible and state.active_task_authority != "explicit_active_set":
        return InvariantResult.fail("multiple active UI tasks were exposed without explicit active-set authority")
    return InvariantResult.pass_()

def controller_boundary_survives_optimization(state: State, trace) -> InvariantResult:
    del trace
    if state.controller_read_sealed_body:
        return InvariantResult.fail("Controller read sealed packet/result body")
    if state.optimized_relay_transaction and not (
        state.optimized_transaction_records_delivery
        and state.optimized_transaction_records_open_receipts
        and state.optimized_transaction_records_result_return
        and state.role_identity_checked
        and state.hash_verified
    ):
        return InvariantResult.fail(
            "optimized relay transaction skipped delivery, receipt, result-return, role, or hash evidence"
        )
    return InvariantResult.pass_()

def optimized_ack_consumption_validates_receipt(state: State, trace) -> InvariantResult:
    del trace
    if state.optimized_card_ack_transaction and not (
        state.card_ack_validated
        and state.card_ack_role_checked
        and state.card_ack_hash_checked
    ):
        return InvariantResult.fail(
            "optimized card ack consumption skipped ack validation, role check, or hash check"
        )
    return InvariantResult.pass_()

def valid_card_ack_file_precedes_unresolved_role_event_block(state: State, trace) -> InvariantResult:
    del trace
    valid_ack_file_exists = (
        state.pending_card_return_ack_file_present
        and state.pending_card_return_ack_valid
        and state.pending_card_return_ack_role_checked
        and state.pending_card_return_ack_hash_checked
        and state.pending_card_return_bundle_receipts_complete
    )
    if (
        state.role_event_arrived_while_ack_pending
        and valid_ack_file_exists
        and state.role_event_blocked_by_unresolved_card_return
        and not state.pre_event_card_ack_auto_consumed
    ):
        return InvariantResult.fail(
            "valid card ACK file was present but role event was blocked before Router consumed the ACK"
        )
    if (
        state.role_event_arrived_while_ack_pending
        and state.pre_event_card_ack_auto_consumed
        and not (
            valid_ack_file_exists
            and state.card_return_ledger_resolved
            and state.card_ack_consumed
            and not state.role_event_blocked_by_unresolved_card_return
        )
    ):
        return InvariantResult.fail(
            "pre-event card ACK consumption skipped validation or did not resolve ledger before accepting role event"
        )
    return InvariantResult.pass_()

def pre_event_ack_rejects_invalid_or_incomplete_ack(state: State, trace) -> InvariantResult:
    del trace
    invalid_or_incomplete_ack = (
        state.pending_card_return_ack_file_present
        and (
            not state.pending_card_return_ack_valid
            or not state.pending_card_return_ack_role_checked
            or not state.pending_card_return_ack_hash_checked
            or not state.pending_card_return_bundle_receipts_complete
        )
    )
    if (
        state.role_event_arrived_while_ack_pending
        and invalid_or_incomplete_ack
        and state.role_event_accepted_after_pre_event_ack
    ):
        return InvariantResult.fail(
            "pre-event ACK reconciliation accepted a role event after an invalid or incomplete ACK"
        )
    return InvariantResult.pass_()

def pre_event_ack_preserves_role_wait_authority(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.role_event_arrived_while_ack_pending
        and state.pre_event_card_ack_auto_consumed
        and state.pre_event_role_wait_authority_present
        and not state.pre_event_role_wait_authority_preserved
    ):
        return InvariantResult.fail("pre-event ACK reconciliation cleared the role event wait authority")
    return InvariantResult.pass_()

def pre_event_ack_consumption_is_single_matched_resolution(state: State, trace) -> InvariantResult:
    del trace
    if state.pre_event_card_ack_auto_consumed and not state.pre_event_ack_selected_matching_pending_return:
        return InvariantResult.fail("pre-event ACK reconciliation consumed a non-matching pending return")
    if state.pre_event_card_ack_auto_consumed and state.duplicate_completed_return_written:
        return InvariantResult.fail("pre-event ACK reconciliation wrote duplicate completed-return records")
    return InvariantResult.pass_()

def missing_ack_report_must_quarantine_and_recover(state: State, trace) -> InvariantResult:
    del trace
    ack_missing = state.missing_ack_report_arrived and not state.pending_card_return_ack_file_present
    if ack_missing and state.missing_ack_report_event_flag_set:
        return InvariantResult.fail("missing-ACK report was accepted before the card ACK existed")
    if (
        state.missing_ack_report_arrived
        and state.pending_return_dependency_matches_report
        and state.same_role_ack_recovery_requested
        and not state.missing_ack_report_quarantined
    ):
        return InvariantResult.fail("missing-ACK report recovery requested reread without quarantining the premature report")
    return InvariantResult.pass_()

def quarantined_report_is_audit_only(state: State, trace) -> InvariantResult:
    del trace
    if state.missing_ack_report_quarantined and state.quarantined_report_used_as_evidence:
        return InvariantResult.fail("quarantined pre-ACK report was used as acceptance evidence")
    if state.missing_ack_report_quarantined and state.old_pre_ack_report_revived:
        return InvariantResult.fail("old pre-ACK report was revived after ACK instead of requiring a fresh report")
    return InvariantResult.pass_()

def accepted_report_must_follow_valid_ack(state: State, trace) -> InvariantResult:
    del trace
    if state.role_event_accepted_after_pre_event_ack and not (
        state.card_return_ledger_resolved
        and state.card_ack_consumed
        and state.report_submitted_after_valid_ack
        and not state.old_pre_ack_report_revived
    ):
        return InvariantResult.fail("accepted report did not follow a valid resolved card ACK")
    return InvariantResult.pass_()

def recoverable_missing_ack_uses_same_role_recovery_first(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.missing_ack_report_arrived
        and state.pending_return_dependency_matches_report
        and not state.repeated_ack_recovery_failed
        and state.missing_ack_generic_pm_blocker_created
    ):
        return InvariantResult.fail("first recoverable missing-ACK report escalated to a generic PM/control blocker")
    if (
        state.missing_ack_report_arrived
        and state.pending_return_dependency_matches_report
        and state.repeated_ack_recovery_failed
        and not state.pm_escalated_after_repeated_ack_failure
    ):
        return InvariantResult.fail("repeated missing-ACK recovery failure did not escalate to PM")
    return InvariantResult.pass_()

def missing_ack_recovery_is_dependency_scoped(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.missing_ack_report_arrived
        and not state.pending_return_dependency_matches_report
        and state.missing_ack_report_quarantined
    ):
        return InvariantResult.fail("unrelated pending card return quarantined a report with no matching dependency")
    return InvariantResult.pass_()

def pending_wait_reconciliation_uses_durable_packet_state(state: State, trace) -> InvariantResult:
    del trace
    if state.stale_wait_reissued_without_reconciliation:
        return InvariantResult.fail(
            "stale wait was reissued after durable packet result already existed"
        )
    if (
        state.stale_wait_pending
        and state.durable_result_evidence_exists
        and not state.pending_wait_reconciled
    ):
        return InvariantResult.fail(
            "pending wait had durable result evidence but was not reconciled before waiting"
        )
    if state.pending_wait_reconciled and state.pending_wait_reconciliation_from_chat:
        return InvariantResult.fail("pending wait reconciliation used chat or history instead of durable packet state")
    if state.pending_wait_reconciled and not (
        state.pending_wait_reconciliation_uses_packet_ledger
        and state.pending_wait_reconciliation_uses_status_packet
        and state.pending_wait_reconciliation_role_verified
        and state.pending_wait_reconciliation_hash_verified
    ):
        return InvariantResult.fail(
            "pending wait reconciliation skipped packet ledger, status packet, role, or hash evidence"
        )
    if state.duplicate_reconciliation_incremented_count:
        return InvariantResult.fail(
            "duplicate wait reconciliation incremented a packet result more than once"
        )
    return InvariantResult.pass_()

def role_work_recipient_normalization_preserves_routes(state: State, trace) -> InvariantResult:
    del trace
    if state.pm_role_work_result_normalized and not state.pm_role_work_result_routes_to_pm:
        return InvariantResult.fail("PM role-work result did not route back to project_manager")
    if state.pm_role_work_result_normalized and not state.current_node_result_routes_to_pm:
        return InvariantResult.fail("current-node worker result did not route back to project_manager")
    return InvariantResult.pass_()

def model_miss_report_can_feed_pm_once(state: State, trace) -> InvariantResult:
    del trace
    if state.model_miss_pm_decision_from_single_report and not state.model_miss_officer_report_complete:
        return InvariantResult.fail("PM model-miss decision used an incomplete officer report")
    return InvariantResult.pass_()

def role_memory_is_index_not_authority(state: State, trace) -> InvariantResult:
    del trace
    if state.role_memory_used_for_authority:
        return InvariantResult.fail("role memory was used as approval or completion authority")
    return InvariantResult.pass_()

def role_work_wait_exposes_status_packet_only(state: State, trace) -> InvariantResult:
    del trace
    if (
        (state.role_work_wait_pending or state.role_output_wait_pending)
        and state.work_package_progress_default_scope != "all_work_packages"
    ):
        return InvariantResult.fail(
            "work-package progress was not default for all role work"
        )
    if state.role_work_wait_pending and not (
        state.role_work_status_packet_exists and state.role_work_status_packet_read_allowed
    ):
        return InvariantResult.fail(
            "role-work wait did not expose matching controller status packet"
        )
    if state.role_work_wait_pending and state.role_work_status_visibility_grant != "single_status_packet":
        return InvariantResult.fail(
            "role-work progress visibility grant exposed more than controller status packet"
        )
    if state.role_output_wait_pending and not state.role_output_progress_prompt_inherited:
        return InvariantResult.fail(
            "formal role-output work lacked shared progress prompt coverage"
        )
    if state.role_output_wait_pending and not (
        state.role_output_status_packet_exists and state.role_output_status_packet_read_allowed
    ):
        return InvariantResult.fail(
            "role-output wait did not expose matching controller status packet"
        )
    if state.role_output_wait_pending and state.role_output_status_visibility_grant != "single_status_packet":
        return InvariantResult.fail(
            "role-output progress visibility grant exposed more than controller status packet"
        )
    return InvariantResult.pass_()

def controller_visible_status_is_metadata_only(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.role_work_wait_pending
        and state.role_work_status_packet_read_allowed
        and not state.role_work_status_message_safe
    ):
        return InvariantResult.fail(
            "controller-visible progress status leaked sealed body details"
        )
    if (
        state.role_output_wait_pending
        and state.role_output_status_packet_read_allowed
        and not state.role_output_status_message_safe
    ):
        return InvariantResult.fail(
            "controller-visible role-output progress status leaked sealed body details"
        )
    if state.progress_status_used_as_decision_evidence:
        return InvariantResult.fail(
            "progress status was used as role decision evidence"
        )
    return InvariantResult.pass_()

def role_progress_updates_use_runtime_contract(state: State, trace) -> InvariantResult:
    del trace
    if state.role_work_progress_observed and not state.role_work_progress_runtime_written:
        return InvariantResult.fail("role progress status update bypassed packet runtime")
    if state.role_output_progress_observed and not state.role_output_progress_runtime_written:
        return InvariantResult.fail("role-output progress status update bypassed packet runtime")
    return InvariantResult.pass_()

def role_progress_value_is_numeric(state: State, trace) -> InvariantResult:
    del trace
    if state.role_work_progress_observed and not (
        state.role_work_progress_numeric and state.role_work_progress_nonnegative
    ):
        return InvariantResult.fail("role progress status was not a nonnegative numeric value")
    if state.role_output_progress_observed and not (
        state.role_output_progress_numeric and state.role_output_progress_nonnegative
    ):
        return InvariantResult.fail("role-output progress status was not a nonnegative numeric value")
    return InvariantResult.pass_()

INVARIANTS = (
    Invariant(
        name="research_scope_preserved",
        description="Research package scope fields survive capability decision and worker packet materialization.",
        predicate=research_scope_preserved,
    ),
    Invariant(
        name="material_scan_dispatch_requires_packet_integrity",
        description="Material-scan dispatch reviews verify phase, output contract, write target, and canonical packet body consistency.",
        predicate=material_scan_dispatch_requires_packet_integrity,
    ),
    Invariant(
        name="reviewer_report_requires_open_receipts",
        description="Reviewer report acceptance requires legal packet/result receipts.",
        predicate=reviewer_report_requires_open_receipts,
    ),
    Invariant(
        name="formal_gate_package_release_requires_artifact",
        description="PM formal gate package release carries reviewer-readable path, hash, and scope.",
        predicate=formal_gate_package_release_requires_artifact,
    ),
    Invariant(
        name="missing_receipt_uses_same_role_reissue",
        description="Mechanical missing-receipt blockers route to same-role reissue, not PM repair.",
        predicate=missing_receipt_uses_same_role_reissue,
    ),
    Invariant(
        name="stopped_run_reconciles_authorities",
        description="A user-stopped run turns off heartbeat, crew, packet loop, and frontier authorities.",
        predicate=stopped_run_reconciles_authorities,
    ),
    Invariant(
        name="active_snapshot_is_fresh",
        description="User-visible active snapshots are fresh against frontier and packet ledger.",
        predicate=active_snapshot_is_fresh,
    ),
    Invariant(
        name="product_architecture_delivery_requires_material_context",
        description="Product architecture delivery includes canonical PM material-understanding source paths.",
        predicate=product_architecture_delivery_requires_material_context,
    ),
    Invariant(
        name="protocol_blockers_are_router_visible",
        description="Protocol blocker files are registered in router-visible blocker state.",
        predicate=protocol_blockers_are_router_visible,
    ),
    Invariant(
        name="control_blocker_indexes_match_artifacts",
        description="Router control-blocker summaries match the durable blocker artifact status.",
        predicate=control_blocker_indexes_match_artifacts,
    ),
    Invariant(
        name="stateful_controller_receipts_require_postcondition_evidence",
        description="Controller done receipts for stateful actions must close a Router-visible postcondition evidence contract before advancement.",
        predicate=stateful_controller_receipts_require_postcondition_evidence,
    ),
    Invariant(
        name="controller_delivery_receipts_do_not_complete_target_work",
        description="Controller delivery receipts only close Controller-owned delivery work and transition to target-role waits.",
        predicate=controller_delivery_receipts_do_not_complete_target_work,
    ),
    Invariant(
        name="pm_role_work_identity_is_work_unit_scoped",
        description="PM role-work obligations use batch, request, packet, and target-role scoped identity and postconditions.",
        predicate=pm_role_work_identity_is_work_unit_scoped,
    ),
    Invariant(
        name="active_holder_leases_require_host_liveness",
        description="Packet active-holder leases require concrete agent identity, host liveness, and packet-role match.",
        predicate=active_holder_leases_require_host_liveness,
    ),
    Invariant(
        name="packet_ledger_io_is_atomic_and_recoverable",
        description="Packet ledger writes are atomic/locked/readback-validated and corrupt reads become recoverable blockers.",
        predicate=packet_ledger_io_is_atomic_and_recoverable,
    ),
    Invariant(
        name="material_gate_result_evidence_is_machine_and_authority_backed",
        description="Material gates depend only on machine-parseable result self-checks and runtime-backed reader authority.",
        predicate=material_gate_result_evidence_is_machine_and_authority_backed,
    ),
    Invariant(
        name="router_owned_artifacts_are_reclaimed_before_blocker",
        description="Valid Router-owned artifacts and proofs are reclaimed before daemon ticks escalate a missing postcondition blocker.",
        predicate=router_owned_artifacts_are_reclaimed_before_blocker,
    ),
    Invariant(
        name="router_internal_postconditions_materialize_or_block",
        description="Router-owned internal postconditions materialize evidence or emit router-visible blockers instead of passive role waits.",
        predicate=router_internal_postconditions_materialize_or_block,
    ),
    Invariant(
        name="resolved_obligation_projections_are_cleared",
        description="Resolved Router obligations do not leave live passive waits or blocked reminder projections.",
        predicate=resolved_obligation_projections_are_cleared,
    ),
    Invariant(
        name="controller_display_work_remains_nonblocking",
        description="Controller display/status work may be soft-recorded but cannot hard-block route progress or escalate to PM repair.",
        predicate=controller_display_work_remains_nonblocking,
    ),
    Invariant(
        name="external_keepalive_actions_require_light_confirmation",
        description="External keepalive actions use lightweight hard confirmation because missing them can break autonomous continuation.",
        predicate=external_keepalive_actions_require_light_confirmation,
    ),
    Invariant(
        name="signed_envelopes_are_immutable_after_relay",
        description="Signed packet/result envelopes are not rewritten after Controller relay.",
        predicate=signed_envelopes_are_immutable_after_relay,
    ),
    Invariant(
        name="controller_action_identity_is_obligation_scoped",
        description="Controller action rows are scoped to a single Router obligation identity.",
        predicate=controller_action_identity_is_obligation_scoped,
    ),
    Invariant(
        name="control_blocker_receipts_apply_delivery_postcondition",
        description="Control-blocker done receipts apply the Router-visible delivery effect.",
        predicate=control_blocker_receipts_apply_delivery_postcondition,
    ),
    Invariant(
        name="current_wait_projection_does_not_resurrect_closed_obligation",
        description="Stale daemon saves cannot resurrect a pending wait after the current Router obligation cleared it.",
        predicate=current_wait_projection_does_not_resurrect_closed_obligation,
    ),
    Invariant(
        name="self_check_parser_matches_template_vocabulary",
        description="Contract Self-Check parser accepts the pass vocabulary templates allow.",
        predicate=self_check_parser_matches_template_vocabulary,
    ),
    Invariant(
        name="role_output_events_require_file_backed_body",
        description="Role-output events require file-backed bodies and verified hashes; status/progress packets are never decision evidence.",
        predicate=role_output_events_require_file_backed_body,
    ),
    Invariant(
        name="material_repair_generation_protocol_is_current",
        description="Material repair replay, Controller receipts, and PM dispositions stay scoped to the current packet generation.",
        predicate=material_repair_generation_protocol_is_current,
    ),
    Invariant(
        name="role_event_identity_and_audit_records_are_closed",
        description="Role-output events are idempotent by body reference and break-glass patch records close after validation.",
        predicate=role_event_identity_and_audit_records_are_closed,
    ),
    Invariant(
        name="packet_result_authority_is_ledger_replayable",
        description="Packet result authorship remains replayable from the packet ledger and matches the current runtime responsibility.",
        predicate=packet_result_authority_is_ledger_replayable,
    ),
    Invariant(
        name="pm_repair_followup_events_are_matchable",
        description="PM repair decisions store follow-up resolution events in a router-matchable form.",
        predicate=pm_repair_followup_events_are_matchable,
    ),
    Invariant(
        name="pm_repair_reissue_requires_packet_runtime_materialization",
        description="PM repair reissue specs enter physical packet files, packet ledger, and dispatch index before recheck can proceed.",
        predicate=pm_repair_reissue_requires_packet_runtime_materialization,
    ),
    Invariant(
        name="pm_repair_recheck_outcomes_remain_routable",
        description="Reviewer rechecks after PM repair can route blocker or protocol outcomes, not only success.",
        predicate=pm_repair_recheck_outcomes_remain_routable,
    ),
    Invariant(
        name="repair_success_clears_stale_repair_lane",
        description="Successful repair transactions leave no stale repair/recheck pending lane.",
        predicate=repair_success_clears_stale_repair_lane,
    ),
    Invariant(
        name="expected_role_decisions_require_satisfied_flags",
        description="Role-decision waits expose only external events whose requires_flag is currently true.",
        predicate=expected_role_decisions_require_satisfied_flags,
    ),
    Invariant(
        name="delivered_cards_include_required_phase_sources",
        description="Every delivered phase card carries required upstream source paths for its workflow phase.",
        predicate=delivered_cards_include_required_phase_sources,
    ),
    Invariant(
        name="delivered_card_phase_context_is_fresh",
        description="Delivered card current_phase matches the actual card workflow phase.",
        predicate=delivered_card_phase_context_is_fresh,
    ),
    Invariant(
        name="terminal_snapshot_flags_match_terminal_state",
        description="Terminal route_state_snapshot flags agree with terminal run status.",
        predicate=terminal_snapshot_flags_match_terminal_state,
    ),
    Invariant(
        name="child_skill_gate_manifest_syncs_review_status",
        description="Child-skill gate manifest approval state agrees with accepted reviewer reports.",
        predicate=child_skill_gate_manifest_syncs_review_status,
    ),
    Invariant(
        name="gate_pass_clears_matching_current_block",
        description="A same-gate current reviewer pass clears the matching active gate outcome blocker and does not clear a different gate.",
        predicate=gate_pass_clears_matching_current_block,
    ),
    Invariant(
        name="card_ack_preserves_semantic_gate_wait",
        description="Direct Router ACK consumption resolves only the mechanical ACK and keeps the semantic reviewer pass/block wait receivable.",
        predicate=card_ack_preserves_semantic_gate_wait,
    ),
    Invariant(
        name="followup_events_keep_event_role_authority",
        description="Control-blocker follow-up events use the event's own authorizing role, not the PM repair target role.",
        predicate=followup_events_keep_event_role_authority,
    ),
    Invariant(
        name="no_legal_next_waits_for_current_role_output",
        description="No-legal-next control blockers are not emitted while a valid role output is still receivable.",
        predicate=no_legal_next_waits_for_current_role_output,
    ),
    Invariant(
        name="duplicate_pm_repair_decisions_are_idempotent",
        description="A repeated PM decision for the same control blocker does not create another blocker.",
        predicate=duplicate_pm_repair_decisions_are_idempotent,
    ),
    Invariant(
        name="terminal_continuation_cleanup_is_proven",
        description="Terminal continuation cleanup has durable host automation proof.",
        predicate=terminal_continuation_cleanup_is_proven,
    ),
    Invariant(
        name="role_output_hashes_are_replayable",
        description="Persisted role-output envelopes can be replayed by hashing their body paths.",
        predicate=role_output_hashes_are_replayable,
    ),
    Invariant(
        name="frontier_tracks_product_architecture_delivery",
        description="Execution frontier moves forward when product architecture is delivered.",
        predicate=frontier_tracks_product_architecture_delivery,
    ),
    Invariant(
        name="display_surfaces_track_product_architecture_delivery",
        description="Route snapshot and display plan refresh after product architecture delivery.",
        predicate=display_surfaces_track_product_architecture_delivery,
    ),
    Invariant(
        name="status_summary_is_public_and_fresh",
        description="Compact status summaries are fresh and user-facing metadata only.",
        predicate=status_summary_is_public_and_fresh,
    ),
    Invariant(
        name="controller_user_reporting_policy_is_plain",
        description="Controller user-facing reports use plain language and hide internal control-plane metadata by default.",
        predicate=controller_user_reporting_policy_is_plain,
    ),
    Invariant(
        name="route_checks_require_nonempty_route_nodes",
        description="Route process checks cannot be delivered for empty route drafts.",
        predicate=route_checks_require_nonempty_route_nodes,
    ),
    Invariant(
        name="route_draft_repair_resets_stale_route_checks",
        description="A repeated route draft before activation resets downstream route-check flags.",
        predicate=route_draft_repair_resets_stale_route_checks,
    ),
    Invariant(
        name="node_local_blocks_remain_same_node_routable",
        description="Node-local reviewer blocks can be repaired without route mutation and have a router-visible recheck path.",
        predicate=node_local_blocks_remain_same_node_routable,
    ),
    Invariant(
        name="route_invalidating_blocks_require_route_mutation",
        description="Route-invalidating reviewer blocks use route mutation with a current-node-incapability reason and fresh route checks.",
        predicate=route_invalidating_blocks_require_route_mutation,
    ),
    Invariant(
        name="same_node_repair_requires_fresh_evidence_and_recheck",
        description="Same-node repairs cannot reuse stale blocked evidence and must pass the same review class before continuation.",
        predicate=same_node_repair_requires_fresh_evidence_and_recheck,
    ),
    Invariant(
        name="multi_active_requires_explicit_authority",
        description="Multiple active UI tasks require explicit active-set authority.",
        predicate=multi_active_requires_explicit_authority,
    ),
    Invariant(
        name="controller_boundary_survives_optimization",
        description="Handoff optimization cannot weaken Controller's envelope-only, role, or hash guarantees.",
        predicate=controller_boundary_survives_optimization,
    ),
    Invariant(
        name="optimized_ack_consumption_validates_receipt",
        description="Optimized card ack consumption validates exact ack, role, and hash.",
        predicate=optimized_ack_consumption_validates_receipt,
    ),
    Invariant(
        name="valid_card_ack_file_precedes_unresolved_role_event_block",
        description="A valid direct ACK already on disk is consumed before Router blocks a later role event for unresolved card return.",
        predicate=valid_card_ack_file_precedes_unresolved_role_event_block,
    ),
    Invariant(
        name="pre_event_ack_rejects_invalid_or_incomplete_ack",
        description="Pre-event ACK reconciliation never accepts invalid, wrong-role, wrong-hash, or incomplete bundle ACKs.",
        predicate=pre_event_ack_rejects_invalid_or_incomplete_ack,
    ),
    Invariant(
        name="pre_event_ack_preserves_role_wait_authority",
        description="Pre-event ACK reconciliation does not clear the unrelated role-event wait that authorizes the incoming event.",
        predicate=pre_event_ack_preserves_role_wait_authority,
    ),
    Invariant(
        name="pre_event_ack_consumption_is_single_matched_resolution",
        description="Pre-event ACK reconciliation consumes only the matching pending return and remains idempotent.",
        predicate=pre_event_ack_consumption_is_single_matched_resolution,
    ),
    Invariant(
        name="missing_ack_report_must_quarantine_and_recover",
        description="A report that arrives before its required card ACK is quarantined and routed to same-role ACK recovery.",
        predicate=missing_ack_report_must_quarantine_and_recover,
    ),
    Invariant(
        name="quarantined_report_is_audit_only",
        description="A pre-ACK quarantined report cannot become acceptance evidence or be revived after ACK.",
        predicate=quarantined_report_is_audit_only,
    ),
    Invariant(
        name="accepted_report_must_follow_valid_ack",
        description="Accepted reports after a missing-ACK recovery must be fresh submissions after a valid ACK is resolved.",
        predicate=accepted_report_must_follow_valid_ack,
    ),
    Invariant(
        name="recoverable_missing_ack_uses_same_role_recovery_first",
        description="The first recoverable missing-ACK report uses same-role recovery before PM escalation.",
        predicate=recoverable_missing_ack_uses_same_role_recovery_first,
    ),
    Invariant(
        name="missing_ack_recovery_is_dependency_scoped",
        description="Missing-ACK report quarantine applies only when the pending card return matches the reporting role dependency.",
        predicate=missing_ack_recovery_is_dependency_scoped,
    ),
    Invariant(
        name="pending_wait_reconciliation_uses_durable_packet_state",
        description="Stale role waits reconcile only from durable packet ledger/status evidence.",
        predicate=pending_wait_reconciliation_uses_durable_packet_state,
    ),
    Invariant(
        name="role_work_recipient_normalization_preserves_routes",
        description="PM role-work results return to PM while current-node results still route to reviewer.",
        predicate=role_work_recipient_normalization_preserves_routes,
    ),
    Invariant(
        name="model_miss_report_can_feed_pm_once",
        description="One complete model-miss officer report can support PM decision without a second officer loop.",
        predicate=model_miss_report_can_feed_pm_once,
    ),
    Invariant(
        name="role_memory_is_index_not_authority",
        description="Role memory deltas are resume indexes, not approval or completion authority.",
        predicate=role_memory_is_index_not_authority,
    ),
    Invariant(
        name="role_work_wait_exposes_status_packet_only",
        description="Long-running role-work waits expose only the matching Controller status packet.",
        predicate=role_work_wait_exposes_status_packet_only,
    ),
    Invariant(
        name="controller_visible_status_is_metadata_only",
        description="Controller-readable progress status remains brief metadata and does not carry sealed findings.",
        predicate=controller_visible_status_is_metadata_only,
    ),
    Invariant(
        name="role_progress_updates_use_runtime_contract",
        description="Roles update progress through the packet runtime rather than ad hoc JSON edits.",
        predicate=role_progress_updates_use_runtime_contract,
    ),
    Invariant(
        name="role_progress_value_is_numeric",
        description="Progress values are comparable nonnegative numbers.",
        predicate=role_progress_value_is_numeric,
    ),
)

def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(str(result.message))
    return failures


__all__ = [
    "INVARIANTS",
    "invariant_failures",
]
