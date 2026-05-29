"""State definitions for the FlowPilot prompt-isolation model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple


class Tick:
    """One prompt-isolation controller tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | blocked | complete
    startup_state: str = "none"  # none | awaiting_answers | answers_complete | controller_ready
    holder: str = "none"  # none | user | controller | pm | reviewer | worker | officer
    phase: str = "none"
    event: str = "none"

    router_loaded: bool = False
    startup_intake_ui_completed: bool = False
    startup_intake_result_recorded: bool = False
    startup_intake_body_boundary_enforced: bool = False
    run_scoped_bootstrap_created: bool = False
    stale_top_level_bootstrap_reused: bool = False
    startup_answer_values_valid: bool = False
    startup_answer_provenance: str = "none"  # none | explicit_user_reply | inferred | default | naked
    startup_answers_recorded: bool = False
    banner_emitted: bool = False
    startup_banner_user_visible: bool = False
    startup_banner_user_dialog_confirmed: bool = False
    run_shell_created: bool = False
    current_pointer_written: bool = False
    run_index_updated: bool = False
    runtime_kit_copied: bool = False
    bootloader_generated_prompt_body: bool = False
    placeholders_filled: bool = False
    mailbox_initialized: bool = False
    user_request_recorded: bool = False
    user_request_provenance: str = "none"  # none | explicit_user_request | inferred | default
    user_intake_ready: bool = False
    roles_started: bool = False
    fresh_role_agents_started: bool = False
    role_core_prompts_injected: bool = False
    controller_core_loaded: bool = False
    controller_boundary_confirmation_written: bool = False
    controller_boundary_policy_hash_recorded: bool = False
    pm_core_delivered: bool = False
    pm_controller_reset_card_delivered: bool = False
    pm_phase_map_delivered: bool = False
    pm_startup_intake_card_delivered: bool = False
    reviewer_startup_fact_check_card_delivered: bool = False
    startup_fact_reported: bool = False
    pm_startup_activation_card_delivered: bool = False
    startup_activation_approved: bool = False
    user_intake_delivered_to_pm: bool = False
    user_intake_controller_relayed: bool = False
    pm_controller_reset_decision_returned: bool = False
    controller_role_confirmed: bool = False

    pm_material_scan_card_delivered: bool = False
    pm_material_scan_packets_issued: bool = False
    reviewer_dispatch_card_delivered: bool = False
    reviewer_dispatch_allowed: bool = False
    worker_packets_delivered: bool = False
    worker_scan_results_returned: bool = False
    material_scan_result_ledger_checked: bool = False
    reviewer_material_sufficiency_card_delivered: bool = False
    material_review: str = "unknown"  # unknown | sufficient | research_required
    pm_material_absorb_or_research_card_delivered: bool = False
    material_accepted_by_pm: bool = False
    pm_research_package_card_delivered: bool = False
    pm_research_package_written: bool = False
    research_capability_decision_recorded: bool = False
    research_worker_report_card_delivered: bool = False
    research_reviewer_dispatch_card_delivered: bool = False
    research_dispatch_allowed: bool = False
    research_worker_packet_delivered: bool = False
    research_worker_report_returned: bool = False
    research_worker_result_ledger_checked: bool = False
    reviewer_research_direct_source_check_card_delivered: bool = False
    research_reviewer_direct_source_check_done: bool = False
    research_reviewer_passed: bool = False
    pm_research_absorb_or_mutate_card_delivered: bool = False
    research_absorbed_by_pm: bool = False
    pm_material_understanding_card_delivered: bool = False
    material_understanding_written: bool = False

    pm_product_architecture_card_delivered: bool = False
    product_architecture_draft_written: bool = False
    product_architecture_modelability_card_delivered: bool = False
    product_architecture_modelability_passed: bool = False
    product_architecture_officer_result_ledger_checked: bool = False
    product_architecture_challenge_card_delivered: bool = False
    product_architecture_reviewer_challenged: bool = False
    pm_root_contract_card_delivered: bool = False
    root_contract_draft_written: bool = False
    root_contract_challenge_card_delivered: bool = False
    root_contract_reviewer_challenged: bool = False
    root_contract_modelability_card_delivered: bool = False
    root_contract_modelability_passed: bool = False
    root_contract_officer_result_ledger_checked: bool = False
    root_contract_frozen_by_pm: bool = False
    pm_dependency_policy_card_delivered: bool = False
    dependency_policy_recorded: bool = False
    capabilities_manifest_written: bool = False
    pm_child_skill_selection_card_delivered: bool = False
    pm_child_skill_selection_written: bool = False
    pm_child_skill_gate_manifest_card_delivered: bool = False
    child_skill_gate_manifest_written: bool = False
    reviewer_child_skill_gate_manifest_card_delivered: bool = False
    child_skill_manifest_reviewer_passed: bool = False
    process_officer_child_skill_card_delivered: bool = False
    child_skill_process_officer_passed: bool = False
    child_skill_process_officer_result_ledger_checked: bool = False
    product_officer_child_skill_card_delivered: bool = False
    child_skill_product_officer_passed: bool = False
    child_skill_product_officer_result_ledger_checked: bool = False
    child_skill_manifest_pm_approved_for_route: bool = False
    capability_evidence_synced: bool = False
    pm_prior_path_context_card_delivered: bool = False
    route_history_context_refreshed: bool = False
    pm_prior_path_context_reviewed: bool = False
    route_history_context_stale: bool = False
    route_skeleton_prior_context_used: bool = False
    node_acceptance_plan_prior_context_used: bool = False
    route_mutation_prior_context_used: bool = False
    parent_segment_prior_context_used: bool = False
    evidence_quality_prior_context_used: bool = False
    final_ledger_prior_context_used: bool = False
    pm_route_skeleton_card_delivered: bool = False
    route_skeleton_written: bool = False
    route_activated_by_pm: bool = False
    route_mutated_by_pm: bool = False

    pm_current_node_card_delivered: bool = False
    pm_node_started_event_delivered: bool = False
    pm_node_acceptance_plan_card_delivered: bool = False
    node_acceptance_plan_written: bool = False
    reviewer_node_acceptance_plan_review_card_delivered: bool = False
    node_acceptance_plan_reviewed: bool = False
    pm_node_packet_issued: bool = False
    reviewer_current_node_dispatch_card_delivered: bool = False
    node_dispatch_allowed: bool = False
    node_worker_body_delivered: bool = False
    node_worker_result_returned: bool = False
    node_worker_result_ledger_checked: bool = False
    node_reviewer_reviewed_result: bool = False
    node_review_blocked: bool = False
    pm_review_repair_card_delivered: bool = False
    pm_reviewer_blocked_event_delivered: bool = False
    pm_node_repair_packet_issued: bool = False
    node_repair_result_returned: bool = False
    node_repair_result_ledger_checked: bool = False
    node_repair_review_passed: bool = False
    node_completed_by_pm: bool = False

    pm_parent_backward_targets_card_delivered: bool = False
    parent_backward_targets_enumerated: bool = False
    reviewer_parent_backward_replay_card_delivered: bool = False
    parent_backward_replay_passed: bool = False
    pm_parent_segment_decision_card_delivered: bool = False
    parent_pm_segment_decision_recorded: bool = False
    pm_evidence_quality_package_card_delivered: bool = False
    pm_evidence_quality_package_written: bool = False
    reviewer_evidence_quality_review_card_delivered: bool = False
    evidence_quality_reviewer_passed: bool = False
    pm_final_ledger_card_delivered: bool = False
    final_ledger_built_by_pm: bool = False
    final_backward_replay_passed: bool = False
    pm_closure_card_delivered: bool = False
    lifecycle_reconciled: bool = False
    heartbeat_stopped_or_manual_recorded: bool = False
    crew_archived: bool = False
    pm_completion_decision: bool = False

    prompt_deliveries: int = 0
    manifest_check_requests: int = 0
    manifest_checks: int = 0
    manifest_check_requested: bool = False
    mail_deliveries: int = 0
    ledger_check_requests: int = 0
    ledger_checks: int = 0
    ledger_check_requested: bool = False
    controller_read_forbidden_body: bool = False
    controller_origin_project_evidence: bool = False
    controller_relayed_body_content: bool = False
    role_output_body_file_written: bool = False
    role_output_envelope_only_to_controller: bool = False
    role_chat_response_disclosed_body: bool = False
    controller_used_role_chat_body: bool = False
    role_output_path_hash_verified: bool = False
    controller_direct_free_text_instruction_used: bool = False
    controller_inspected_router_internal_hard_checks: bool = False
    wrong_role_prompt_delivered: bool = False
    wrong_role_body_delivered: bool = False
    pm_used_unreviewed_evidence: bool = False
    bootloader_actions: int = 0
    router_action_requests: int = 0
    router_action_requested: bool = False
    system_card_identity_boundaries_verified: bool = False
    packet_body_identity_boundaries_verified: bool = False
    result_body_identity_boundaries_verified: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


__all__ = ["Action", "State", "Tick", "Transition", "initial_state"]
