"""FlowGuard model for FlowPilot control-plane friction fixes.

Risk intent brief:
- Prevent prompt-isolation shortcuts from becoming handoff dead ends.
- Preserve Controller's envelope-only boundary while reducing purely
  mechanical handoff steps.
- Model-critical durable state: research package fields, worker packet
  materialization, material-scan dispatch integrity, packet/result open
  receipts, control-blocker routing, stop lifecycle reconciliation,
  active-task authority, display snapshot freshness, required phase-source
  context, and live-run artifact registration.
- Adversarial branches include dropped research scope fields, reviewer reports
  accepted without a result-body receipt, missing-receipt blockers escalated to
  PM instead of same-role reissue, material-scan packet dispatch with phase,
  contract, write-target, or canonical-body drift, PM repair reissue specs that
  never enter the packet runtime, success-only repair gates that cannot accept
  reviewer recheck blockers, stopped runs with live heartbeat/crew/packet
  state, stale snapshots treated as active UI state, ambiguous multi-active
  runs under current-json-only authority, product architecture delivery without
  PM material-understanding source paths, protocol blockers written outside
  router-visible state, stage-advance views left stale, stale role-decision
  waits that expose external events before their requires_flag is true, and
  optimized transactions that skip hash, role, or Controller-boundary checks.
  Status summaries, ack auto-consumption, stale wait reconciliation, role-work
  recipient normalization, model-miss report completeness, and role-memory
  deltas are included because these are the planned speed improvements.
  Long-running role-work waits are included: Controller can see only a
  metadata-only controller_status_packet progress surface, never sealed packet
  or result bodies. Reviewer-block repair routing is included: PM can repair
  node-local defects by revising or reissuing fresh same-node artifacts, while
  route mutation is reserved for defects the current node cannot semantically
  contain.
- Hard invariants: package-to-packet fields are preserved; material-scan
  dispatch requires phase, contract, write-target, and canonical-body
  consistency; repair reissues must materialize into packet files, ledger, and
  dispatch index; reviewer recheck failures must remain routable; reviewer
  decisions require legal open receipts; missing receipt repair is same-role
  reissue; stopped runs reconcile all visible lifecycle authorities; active
  snapshots are fresh; phase cards carry required source context; protocol
  blockers are router-visible; stage-advance views refresh; multi-active
  visibility has explicit authority; await_role_decision exposes only currently
  receivable external events; optimized transactions keep hash, role, and
  envelope-only guarantees; long-running waits expose exactly one status
  packet, progress is runtime-written numeric metadata, and status messages do
  not carry findings, evidence, recommendations, or body summaries; node-local
  reviewer blocks remain routable without a route mutation, use fresh repair
  evidence, and require the same review class to recheck before continuation;
  route mutations record why the current node cannot contain the repair and
  reopen route checks; optimized ack consumption validates exact ack, role, and
  hash; a valid direct ACK file that already exists is consumed before a later
  role event is blocked as an unresolved card return; pending waits reconcile
  only from durable packet/status evidence;
  user-facing status summaries remain metadata-only and blocker-consistent;
  PM role-work and current-node worker results return to PM before formal
  reviewer gates; role memory is an index, never an approval authority; and a
  complete model-miss officer report can reach a PM decision without a second
  officer loop; child-skill gate reviewer passes clear only the matching
  current gate blocker; direct Router ACK consumption preserves the semantic
  reviewer pass/block wait; PM repair authority cannot impersonate reviewer
  event authority; no-legal-next blockers wait for currently receivable role
  output; duplicate PM repair decisions are idempotent for the same blocker;
  Controller user reports do not expose internal action, packet, ledger, hash,
  contract, or diagnostic-path metadata by default; Router actions carry a
  Controller-facing plain-language reminder that is not itself user-visible;
  compact progress summaries include bounded route-level progress facts;
  display/status Controller work remains nonblocking; external keepalive work
  still requires lightweight confirmation; Controller delivery receipts only
  close Controller-owned delivery work and must become target-role waits rather
  than role completion; stateful Controller receipts cannot clear or advance a
  hard pending action until the Router can verify or reclaim the declared
  postcondition evidence; daemon ticks cannot escalate a half-complete
  Controller receipt when valid Router-owned artifacts already exist; and
  role-output events cannot be accepted from a prepared/progress status surface
  without a file-backed body path plus replayable body hash; PM role-work
  obligations are keyed by batch/request/packet/role, host delivery success and
  active-holder liveness are separate gates, packet-ledger IO is atomic and
  corruption-recoverable, result self-checks are machine-parseable, runtime
  authority backs every advertised reader; Router-owned internal postconditions
  with ready inputs materialize evidence or emit a router-visible blocker
  instead of becoming passive Controller/role waits; resolved obligations clear
  passive wait and reminder projections; stale daemon/run-state saves cannot
  resurrect a live wait after the authoritative Router obligation state has
  cleared it; and material repair progress is derived from the active
  generation/batch rather than stale run-wide flags.
- Blindspot: this is still a focused control-plane model. The live-run audit
  checks file-level consistency, but it does not prove product content quality.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple


PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES = frozenset(
    {"pm_repair_decision_required", "fatal_protocol_violation"}
)


@dataclass(frozen=True)
class Tick:
    """One control-plane handoff tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | complete
    mode: str = "unknown"  # unknown | expanded | optimized
    holder: str = "controller"
    handoff_steps: int = 0

    controller_boundary_confirmed: bool = False
    controller_read_sealed_body: bool = False
    role_identity_checked: bool = False
    hash_verified: bool = False
    stateful_controller_receipt_done: bool = False
    stateful_controller_postcondition_declared: bool = False
    stateful_controller_postcondition_evidence_written: bool = False
    stateful_controller_advanced_from_receipt: bool = False
    controller_delivery_receipt_done: bool = False
    controller_delivery_host_status: str = "none"  # none | delivered | failed_agent_not_found
    controller_delivery_target_role_wait_started: bool = False
    controller_delivery_used_as_role_completion: bool = False
    controller_delivery_missing_role_output_blocker: bool = False
    pm_role_work_identity_includes_batch_request_packet_role: bool = False
    pm_role_work_closed_identity_reused_for_distinct_request: bool = False
    pm_role_work_request_postcondition_scoped: bool = False
    pm_role_work_open_request_masked_by_global_flag: bool = False
    active_holder_lease_issued: bool = False
    active_holder_agent_identity_recorded: bool = False
    active_holder_agent_host_live: bool = False
    active_holder_packet_role_matches: bool = False
    packet_ledger_write_atomic: bool = False
    packet_ledger_write_locked_or_cas: bool = False
    packet_ledger_readback_validated: bool = False
    packet_ledger_corruption_recoverable: bool = False
    packet_ledger_corrupt_read_crashed_daemon: bool = False
    router_owned_artifact_exists: bool = False
    router_owned_artifact_proof_valid: bool = False
    router_owned_postcondition_reclaimed_from_artifact: bool = False
    router_tick_saw_receipt_before_flag: bool = False
    router_tick_escalated_before_reclaim: bool = False
    router_internal_postcondition_due: bool = False
    router_internal_postcondition_inputs_ready: bool = False
    router_internal_postcondition_materialized: bool = False
    router_internal_postcondition_blocker_materialized: bool = False
    router_internal_postcondition_exposed_as_role_wait: bool = False
    router_internal_postcondition_expected_evidence_exists: bool = False
    router_internal_postcondition_executable_action_pending: bool = False
    resolved_obligation_evidence_exists: bool = False
    resolved_obligation_live_passive_wait: bool = False
    resolved_obligation_live_blocked_reminder: bool = False
    resolved_obligation_projection_reconciled: bool = True
    controller_display_work_soft_recorded: bool = False
    controller_display_work_hard_postcondition: bool = False
    controller_display_work_escalated_to_pm: bool = False
    external_keepalive_confirmation_required: bool = False
    external_keepalive_confirmed: bool = False
    signed_envelope_relayed: bool = False
    signed_envelope_rewritten_after_relay: bool = False
    signed_envelope_migration_sidecar_written: bool = False
    signed_envelope_mutable_indexes_backfilled: bool = False
    control_blocker_action_identity_includes_blocker: bool = False
    controller_action_closed_identity_reused: bool = False
    control_blocker_receipt_postcondition_declared: bool = False
    control_blocker_receipt_effect_applied: bool = False
    current_wait_derived_from_obligation: bool = False
    stale_run_state_save_seen: bool = False
    latest_state_cleared_wait: bool = False
    stale_run_state_pending_matches_loaded_wait: bool = False
    stale_run_state_preserved_wait_clear: bool = False
    stale_run_state_resurrected_closed_wait: bool = False
    self_check_template_status_pass_allowed: bool = False
    self_check_parser_status_pass_accepted: bool = False
    material_gate_depends_on_result_body: bool = False
    result_self_check_machine_parseable: bool = True
    result_reader_authority_matches_runtime: bool = True

    pm_research_package_written: bool = False
    research_package_has_decision_question: bool = False
    research_package_has_allowed_sources: bool = False
    research_package_has_stop_conditions: bool = False
    research_capability_decision_recorded: bool = False
    worker_packet_written: bool = False
    worker_packet_preserves_research_fields: bool = False
    material_dispatch_requested: bool = False
    material_dispatch_reviewed: bool = False
    material_dispatch_allowed: bool = False
    material_dispatch_phase_context_consistent: bool = True
    material_dispatch_output_contract_consistent: bool = True
    material_dispatch_write_target_explicit: bool = True
    material_dispatch_single_canonical_body: bool = True
    pm_repair_reissue_spec_written: bool = False
    pm_repair_reissue_packet_files_materialized: bool = True
    pm_repair_reissue_packets_registered_in_ledger: bool = True
    pm_repair_reissue_dispatch_index_updated: bool = True
    pm_repair_allowed_success_only: bool = False
    pm_repair_non_success_outcome_routable: bool = True
    active_repair_transaction_stale: bool = False
    repair_recheck_pending_action_stale: bool = False
    expected_role_decision_requires_unsatisfied_flag: bool = False
    reviewer_recheck_protocol_blocker_written: bool = False
    reviewer_recheck_protocol_blocker_routable: bool = True

    packet_delivered: bool = False
    packet_body_open_receipt: bool = False
    result_returned: bool = False
    result_routed_to_reviewer: bool = False
    result_routed_to_pm: bool = False
    result_body_open_receipt: bool = False
    pm_result_disposition_recorded: bool = False
    pm_formal_review_package_released: bool = False
    pm_formal_review_package_has_artifact: bool = False
    pm_formal_review_package_hash_recorded: bool = False
    pm_formal_review_package_scope_declared: bool = False
    reviewer_report_written: bool = False
    reviewer_report_accepted: bool = False

    pm_material_understanding_written: bool = False
    pm_material_understanding_source_available: bool = False
    product_architecture_card_delivered: bool = False
    product_architecture_delivery_has_material_context: bool = False
    protocol_blocker_file_written: bool = False
    protocol_blocker_registered_in_router_state: bool = False
    control_blocker_artifact_status_written: bool = False
    control_blocker_router_index_matches_artifact: bool = True
    phase_dependency_cards_delivered: bool = False
    phase_required_sources_complete: bool = False
    delivered_card_phase_context_fresh: bool = False
    terminal_snapshot_published: bool = False
    terminal_snapshot_flags_consistent: bool = True
    child_skill_gate_review_recorded: bool = False
    child_skill_gate_manifest_synced_with_review: bool = True
    child_skill_gate_repair_flow_started: bool = False
    child_skill_gate_pm_rewrote_after_block: bool = False
    gate_card_requires_semantic_outcome: bool = False
    card_ack_consumed: bool = False
    semantic_gate_wait_exposed_after_ack: bool = True
    gate_outcome_block_active: bool = False
    gate_outcome_block_gate_key: str = "none"
    gate_outcome_pass_recorded: bool = False
    gate_outcome_pass_gate_key: str = "none"
    gate_outcome_same_generation: bool = True
    gate_outcome_clear_target_matches_pass_gate: bool = True
    terminal_continuation_cleanup_recorded: bool = False
    terminal_host_automation_cleanup_proven: bool = True
    role_output_envelopes_recorded: bool = False
    role_output_hashes_replayable: bool = True
    stage_advanced_after_material_scan: bool = False
    frontier_fresh_after_stage_advance: bool = False
    product_stage_view_published: bool = False
    product_stage_view_fresh: bool = False
    route_draft_written: bool = False
    route_draft_has_nodes: bool = True
    route_draft_single_canonical_source: bool = True
    route_draft_shadow_source_used: bool = False
    route_process_check_card_delivered: bool = False
    route_process_check_passed: bool = False
    route_draft_repaired_after_check: bool = False
    route_review_flags_reset_after_draft_repair: bool = True

    status_summary_published: bool = False
    status_summary_fresh_against_frontier_and_packet: bool = False
    status_summary_metadata_only: bool = True
    status_summary_blocker_state_consistent: bool = True
    controller_user_reporting_policy_present: bool = False
    router_action_user_reporting_reminder_present: bool = False
    controller_table_prompt_user_language_guidance_present: bool = False
    controller_reporting_budget_present: bool = False
    quiet_internal_progress_silent: bool = True
    routine_process_aside_relayed_to_user: bool = False
    user_report_limited_to_meaningful_change: bool = True
    user_report_plain_language: bool = True
    user_report_internal_metadata_exposed: bool = False
    router_action_user_reporting_reminder_displayed_to_user: bool = False
    status_summary_progress_facts_present: bool = False
    status_summary_progress_level_count_valid: bool = True
    status_summary_progress_counts_valid: bool = True
    status_summary_progress_elapsed_valid_or_null: bool = True
    status_summary_progress_metadata_only: bool = True

    review_block_observed: bool = False
    review_block_scope: str = "none"  # none | node_local | route_invalidating
    pm_selected_same_node_repair: bool = False
    same_node_repair_path_routable: bool = True
    fresh_repair_evidence_written: bool = False
    stale_blocked_evidence_reused_as_pass: bool = False
    same_review_class_rechecked_repair: bool = False
    pm_selected_route_mutation: bool = False
    current_node_cannot_contain_repair_reason_present: bool = False

    optimized_relay_transaction: bool = False
    optimized_transaction_records_delivery: bool = False
    optimized_transaction_records_open_receipts: bool = False
    optimized_transaction_records_result_return: bool = False
    optimized_card_ack_transaction: bool = False
    card_ack_validated: bool = False
    card_ack_role_checked: bool = False
    card_ack_hash_checked: bool = False
    pending_card_return_kind: str = "none"  # none | system_card | system_card_bundle
    pending_card_return_ack_file_present: bool = False
    pending_card_return_ack_valid: bool = False
    pending_card_return_ack_role_checked: bool = False
    pending_card_return_ack_hash_checked: bool = False
    pending_card_return_bundle_receipts_complete: bool = True
    card_return_ledger_resolved: bool = False
    role_event_arrived_while_ack_pending: bool = False
    pre_event_card_ack_auto_consumed: bool = False
    role_event_blocked_by_unresolved_card_return: bool = False
    pre_event_role_wait_authority_present: bool = True
    pre_event_role_wait_authority_preserved: bool = True
    role_event_accepted_after_pre_event_ack: bool = False
    pre_event_ack_selected_matching_pending_return: bool = True
    duplicate_completed_return_written: bool = False
    missing_ack_report_arrived: bool = False
    missing_ack_report_quarantined: bool = False
    same_role_ack_recovery_requested: bool = False
    missing_ack_report_event_flag_set: bool = False
    quarantined_report_used_as_evidence: bool = False
    old_pre_ack_report_revived: bool = False
    report_submitted_after_valid_ack: bool = True
    pending_return_dependency_matches_report: bool = True
    missing_ack_generic_pm_blocker_created: bool = False
    repeated_ack_recovery_failed: bool = False
    pm_escalated_after_repeated_ack_failure: bool = False
    pending_wait_reconciled: bool = False
    pending_wait_reconciliation_uses_packet_ledger: bool = False
    pending_wait_reconciliation_uses_status_packet: bool = False
    pending_wait_reconciliation_role_verified: bool = False
    pending_wait_reconciliation_hash_verified: bool = False
    pending_wait_reconciliation_from_chat: bool = False
    stale_wait_pending: bool = False
    durable_result_evidence_exists: bool = False
    stale_wait_reissued_without_reconciliation: bool = False
    partial_batch_active: bool = False
    partial_batch_packet_count: int = 0
    partial_batch_results_returned: int = 0
    partial_batch_result_refreshed_from_members: bool = True
    partial_batch_missing_role_summary_accurate: bool = True
    status_summary_waiting_role_matches_partial_batch: bool = True
    duplicate_reconciliation_incremented_count: bool = False
    pm_role_work_result_normalized: bool = False
    pm_role_work_result_routes_to_pm: bool = True
    current_node_result_routes_to_pm: bool = True
    model_miss_officer_report_complete: bool = False
    model_miss_pm_decision_from_single_report: bool = False
    role_memory_delta_written: bool = False
    role_memory_used_for_authority: bool = False

    receipt_missing_blocker: bool = False
    control_blocker_lane: str = "none"  # none | control_plane_reissue | pm_repair_decision_required | fatal_protocol_violation
    control_blocker_target_role: str = "none"  # none | human_like_reviewer | project_manager
    pm_repair_decision_recorded: bool = False
    control_blocker_followup_event_matchable: bool = True
    control_resolution_predicate_normalized: bool = True
    followup_event_expected_role: str = "none"
    followup_event_from_role: str = "none"
    valid_role_output_waiting: bool = False
    no_legal_next_control_blocker_materialized: bool = False
    duplicate_pm_repair_decision_seen: bool = False
    duplicate_repair_created_new_blocker: bool = False

    stop_requested: bool = False
    current_status_stopped: bool = False
    continuation_heartbeat_active: bool = False
    crew_live_agents_active: bool = False
    packet_loop_active: bool = False
    frontier_terminal: bool = False

    snapshot_published_as_active: bool = False
    snapshot_fresh_against_frontier_and_ledger: bool = False
    multiple_running_index_entries_visible: bool = False
    active_task_authority: str = "current_focus_only"  # current_focus_only | explicit_active_set

    role_work_wait_pending: bool = False
    role_work_status_packet_exists: bool = True
    role_work_status_packet_read_allowed: bool = True
    role_work_status_visibility_grant: str = "single_status_packet"  # none | single_status_packet | packet_dir | sealed_body
    role_work_progress_observed: bool = False
    role_work_progress_runtime_written: bool = True
    role_work_progress_numeric: bool = True
    role_work_progress_nonnegative: bool = True
    role_work_status_message_safe: bool = True

    work_package_progress_default_scope: str = "all_work_packages"  # packet_only | all_work_packages
    role_output_wait_pending: bool = False
    role_output_progress_prompt_inherited: bool = True
    role_output_status_packet_exists: bool = True
    role_output_status_packet_read_allowed: bool = True
    role_output_status_visibility_grant: str = "single_status_packet"  # none | single_status_packet | output_dir | sealed_body
    role_output_progress_observed: bool = False
    role_output_progress_runtime_written: bool = True
    role_output_progress_numeric: bool = True
    role_output_progress_nonnegative: bool = True
    role_output_status_message_safe: bool = True
    progress_status_used_as_decision_evidence: bool = False
    role_output_status_prepared_only: bool = False
    role_output_status_used_as_event_evidence: bool = False
    role_output_event_submitted: bool = False
    role_output_event_accepted: bool = False
    role_output_file_backed_body_path_present: bool = True
    role_output_body_hash_verified: bool = True

    material_repair_generation_protocol_checked: bool = False
    operation_replay_fresh_controller_action_id: bool = True
    operation_replay_targets_current_generation: bool = True
    operation_replay_ledger_io_authorized: bool = True
    controller_repair_work_packet_receipt_folded: bool = True
    controller_repair_work_packet_facade_exported: bool = True
    pm_material_disposition_generation_scoped: bool = True
    pm_material_disposition_matches_current_generation: bool = True
    stale_pm_material_disposition_restored: bool = False
    material_progress_projection_generation_scoped: bool = True
    material_global_progress_flags_match_active_generation: bool = True
    material_next_action_derived_from_active_batch: bool = True
    material_reissue_clears_or_quarantines_stale_progress_flags: bool = True
    stale_run_state_save_preserves_material_generation_flag_clear: bool = True
    material_dispatch_block_matches_active_generation: bool = True
    role_output_event_deduped_by_body_ref: bool = True
    role_output_current_generation_not_short_circuited_by_global_flag: bool = True
    role_output_package_disposition_domain_first_commit: bool = True
    pm_package_authority_split_preserves_wait: bool = True
    pm_package_authority_split_repairs_domain_commit: bool = True
    pm_package_authority_split_crashed_daemon: bool = False
    pm_package_authority_split_accepted_as_success: bool = False
    duplicate_role_event_side_effect_written: bool = False
    pm_package_disposition_semantic_identity_deduped: bool = True
    pm_package_disposition_body_hash_conflict_checked: bool = True
    pm_package_repair_owned_conflict_replay_quarantined: bool = True
    pm_package_repair_owned_conflict_preserves_wait: bool = True
    pm_package_repair_owned_conflict_crashed_daemon: bool = False
    pm_package_repair_owned_conflict_accepted_as_success: bool = False
    pm_package_repair_owned_conflict_duplicate_blocker: bool = False
    pm_package_stale_unowned_conflict_replay_quarantined: bool = True
    pm_package_stale_unowned_conflict_preserves_canonical: bool = True
    pm_package_stale_unowned_conflict_crashed_daemon: bool = False
    pm_package_stale_unowned_conflict_accepted_as_success: bool = False
    pm_package_packet_outcomes_recorded: bool = True
    packet_result_author_identity_replayable: bool = True
    packet_result_author_matches_current_role: bool = True
    break_glass_patch_validation_finalized: bool = True

class Transition(NamedTuple):
    label: str
    state: State

def initial_state() -> State:
    return State()


__all__ = [
    "PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES",
    "Action",
    "State",
    "Tick",
    "Transition",
    "initial_state",
]
