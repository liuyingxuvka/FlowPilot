"""FlowGuard model for FlowPilot current-field contracts.

This model owns the field-level question: which current fields may advance the
FlowPilot path, which component validates them, and which next state they can
unlock. Unsupported historical fields are modeled only as hazards; production
code should reject them through current-schema checks, not translate them.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_field_contracts"

SUCCESS = "success"
UNSUPPORTED_STARTUP_FIELD_ACCEPTED = "unsupported_startup_field_accepted"
UNSUPPORTED_FIELD_TRANSLATED = "unsupported_field_translated"
MISSING_BACKGROUND_ACK_ADVANCES = "missing_background_ack_advances"
PROVENANCE_PROMOTED_TO_SCOPE = "provenance_promoted_to_scope"
STARTUP_FIXED_ROLE_BINDING_GATE_REQUIRED = "startup_fixed_role_binding_gate_required"
FIXED_ROLE_COUNT_GATE_REQUIRED = "fixed_role_count_gate_required"
LEGACY_BOOT_ACTION_ACCEPTED = "legacy_boot_action_accepted"

SCENARIOS = (
    SUCCESS,
    UNSUPPORTED_STARTUP_FIELD_ACCEPTED,
    UNSUPPORTED_FIELD_TRANSLATED,
    MISSING_BACKGROUND_ACK_ADVANCES,
    PROVENANCE_PROMOTED_TO_SCOPE,
    STARTUP_FIXED_ROLE_BINDING_GATE_REQUIRED,
    FIXED_ROLE_COUNT_GATE_REQUIRED,
    LEGACY_BOOT_ACTION_ACCEPTED,
)
RISK_SCENARIOS = set(SCENARIOS) - {SUCCESS}

FIELD_LAYERS = {
    "top_level": "Run, route, and current packet pointers that decide whether the flow may advance.",
    "middle": "Package, role, lease, and result identity fields that decide whether work is current.",
    "leaf": "Concrete evidence, hash, path, receipt, review, and repair fields.",
}

FIELD_STATUSES = {
    "current": "Current user or package field that remains valid only inside the current runtime contract.",
    "mechanical_runtime_owned": "Runtime/Router owns existence, identity, path, hash, and ledger validity.",
    "pm_decision_owned": "PM owns disposition after Runtime mechanics and role quality/process evidence are available.",
    "reviewer_quality_owned": "Reviewer owns semantic quality, requirement satisfaction, and evidence credibility.",
    "flowguard_process_owned": "FlowGuard operator owns process, model, state, route, stale-evidence, and loop risk.",
    "retired": "Removed from current manifests/cards/output contracts; may exist only in history.",
    "forbidden_legacy": "Unsupported old field/event/card/output path that cannot advance current runtime.",
}

CURRENT_FIELD_CONTRACTS = (
    {
        "field": "startup_answers.background_collaboration_authorized",
        "logical_field": "background_collaboration_authorized",
        "layer": "leaf",
        "owner": "native_startup_intake_ui",
        "status": "current",
        "validator": "_validate_startup_answers",
        "required_value": True,
        "unlocks": "user_intake_packet_creation",
    },
    {
        "field": "startup_answers.provenance",
        "logical_field": "startup_answers_provenance",
        "layer": "leaf",
        "owner": "native_startup_intake_ui",
        "status": "current",
        "validator": "_validate_startup_answers",
        "required_value": "explicit_user_reply",
        "unlocks": "startup_answers_recorded",
    },
    {
        "field": "user_intake.metadata.controller_bootstrap_scope.background_collaboration_authorized",
        "logical_field": "startup_input_sealed_background_collaboration_authorized",
        "layer": "leaf",
        "owner": "packet_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_current_startup_options",
        "required_value": True,
        "unlocks": "pm_can_open_user_intake_packet",
    },
    {
        "field": "user_intake.metadata.startup_runtime_release_required",
        "logical_field": "startup_runtime_release_required",
        "layer": "leaf",
        "owner": "packet_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "create_user_intake_packet",
        "required_value": True,
        "unlocks": "router_held_startup_material_release",
    },
    {
        "field": "user_intake.metadata.startup_runtime_release_status",
        "logical_field": "startup_runtime_release_status",
        "layer": "leaf",
        "owner": "packet_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "create_user_intake_packet",
        "required_value": "router_held_until_mechanical_audit_and_display_status",
        "unlocks": "router_held_startup_material_release",
    },
    {
        "field": "startup_intake_record.startup_intake_authority_source",
        "logical_field": "startup_intake_authority_source",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_validate_startup_intake_result_payload",
        "required_value": "startup_intake_record",
        "unlocks": "startup_mechanical_audit",
    },
    {
        "field": "startup_intake_record.router_must_not_use_chat_history_for_startup_intake",
        "logical_field": "router_must_not_use_chat_history_for_startup_intake",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_startup_intake_record_context",
        "required_value": True,
        "unlocks": "startup_mechanical_audit",
    },
    {
        "field": "user_request_ref.startup_intake_authority_source",
        "logical_field": "startup_intake_authority_source",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_user_request_ref_from_startup_intake",
        "required_value": "startup_intake_record",
        "unlocks": "pm_startup_intake_context",
    },
    {
        "field": "user_request_ref.router_must_not_use_chat_history_for_startup_intake",
        "logical_field": "router_must_not_use_chat_history_for_startup_intake",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_user_request_ref_from_startup_intake",
        "required_value": True,
        "unlocks": "pm_startup_intake_context",
    },
    {
        "field": "run.run_id",
        "logical_field": "run_id",
        "layer": "top_level",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "new_run_state",
        "required_value": "current_run_id",
        "unlocks": "current_run_scope",
    },
    {
        "field": "run.run_root",
        "logical_field": "run_root",
        "layer": "top_level",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "new_run_state",
        "required_value": "current_run_root",
        "unlocks": "current_run_scope",
    },
    {
        "field": "route_frontier.active_node_id",
        "logical_field": "active_node_id",
        "layer": "top_level",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_validate_current_node_packet_event",
        "required_value": "current_active_node_id",
        "unlocks": "current_node_packet_scope",
    },
    {
        "field": "route_frontier.route_version",
        "logical_field": "route_version",
        "layer": "top_level",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_validate_current_node_packet_event",
        "required_value": "current_route_version",
        "unlocks": "current_node_packet_scope",
    },
    {
        "field": "current_packet.packet_id",
        "logical_field": "current_packet_id",
        "layer": "top_level",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_validate_current_node_packet_envelope",
        "required_value": "active_current_packet",
        "unlocks": "current_packet_assignment",
    },
    {
        "field": "startup_mechanical_audit.mechanical_checks.startup_answers_use_current_fields_only",
        "logical_field": "startup_mechanical_audit_current_fields_only",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_write_startup_mechanical_audit",
        "required_value": True,
        "unlocks": "pm_first_round_work",
    },
    {
        "field": "startup_mechanical_audit.mechanical_checks.background_collaboration_authorized",
        "logical_field": "startup_mechanical_audit_background_collaboration_authorized",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_write_startup_mechanical_audit",
        "required_value": True,
        "unlocks": "pm_first_round_work",
    },
    {
        "field": "current_role_agent_binding.role_key",
        "logical_field": "current_role_agent_binding.role_key",
        "layer": "middle",
        "owner": "host_background_collaboration",
        "status": "mechanical_runtime_owned",
        "validator": "_normalize_current_role_agent_binding",
        "required_value": "current_packet_runtime_role",
        "unlocks": "current_on_demand_role_binding",
    },
    {
        "field": "current_role_agent_binding.agent_id",
        "logical_field": "current_role_agent_binding.agent_id",
        "layer": "middle",
        "owner": "host_background_collaboration",
        "status": "mechanical_runtime_owned",
        "validator": "_normalize_current_role_agent_binding",
        "required_value": "current_role_agent_id",
        "unlocks": "current_on_demand_role_binding",
    },
    {
        "field": "current_role_agent_binding.model_policy",
        "logical_field": "current_role_agent_binding.model_policy",
        "layer": "middle",
        "owner": "host_background_collaboration",
        "status": "mechanical_runtime_owned",
        "validator": "_normalize_current_role_agent_binding",
        "required_value": "strongest_available",
        "unlocks": "current_on_demand_role_binding",
    },
    {
        "field": "current_role_agent_binding.reasoning_effort_policy",
        "logical_field": "current_role_agent_binding.reasoning_effort_policy",
        "layer": "middle",
        "owner": "host_background_collaboration",
        "status": "mechanical_runtime_owned",
        "validator": "_normalize_current_role_agent_binding",
        "required_value": "highest_available",
        "unlocks": "current_on_demand_role_binding",
    },
    {
        "field": "current_role_agent_binding.binding_open_result",
        "logical_field": "current_role_agent_binding.binding_open_result",
        "layer": "middle",
        "owner": "host_background_collaboration",
        "status": "mechanical_runtime_owned",
        "validator": "_normalize_current_role_agent_binding",
        "required_value": "opened_for_current_packet",
        "unlocks": "current_on_demand_role_binding",
    },
    {
        "field": "current_role_agent_binding.opened_for_run_id",
        "logical_field": "current_role_agent_binding.opened_for_run_id",
        "layer": "middle",
        "owner": "host_background_collaboration",
        "status": "mechanical_runtime_owned",
        "validator": "_normalize_current_role_agent_binding",
        "required_value": "current_run_id",
        "unlocks": "current_on_demand_role_binding",
    },
    {
        "field": "current_role_agent_binding.host_liveness_status",
        "logical_field": "host_liveness_status",
        "layer": "middle",
        "owner": "host_background_collaboration",
        "status": "mechanical_runtime_owned",
        "validator": "_normalize_current_role_agent_binding",
        "required_value": "active",
        "unlocks": "current_on_demand_role_binding",
    },
    {
        "field": "current_role_agent_binding.liveness_decision",
        "logical_field": "current_role_agent_binding.liveness_decision",
        "layer": "middle",
        "owner": "host_background_collaboration",
        "status": "mechanical_runtime_owned",
        "validator": "_normalize_current_role_agent_binding",
        "required_value": "confirmed_existing_agent",
        "unlocks": "current_on_demand_role_binding",
    },
    {
        "field": "role_binding_ledger.role_binding_mode",
        "logical_field": "role_binding_ledger.role_binding_mode",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_write_current_role_agent_binding",
        "required_value": "current_on_demand_role_binding",
        "unlocks": "role_binding_memory_and_role_io_protocol",
    },
    {
        "field": "role_binding_ledger.role_slots[].role_key",
        "logical_field": "role_binding_ledger.role_slots[].role_key",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_write_current_role_agent_binding",
        "required_value": "current_packet_runtime_role",
        "unlocks": "background_or_parallel_work",
    },
    {
        "field": "role_binding_ledger.role_slots[].agent_id",
        "logical_field": "role_binding_ledger.role_slots[].agent_id",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_write_current_role_agent_binding",
        "required_value": "current_role_agent_id",
        "unlocks": "background_or_parallel_work",
    },
    {
        "field": "role_binding_ledger.role_slots[].host_liveness_status",
        "logical_field": "host_liveness_status",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_write_current_role_agent_binding",
        "required_value": "active",
        "unlocks": "background_or_parallel_work",
    },
    {
        "field": "role_binding_ledger.role_slots[].liveness_decision",
        "logical_field": "role_binding_ledger.role_slots[].liveness_decision",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_write_current_role_agent_binding",
        "required_value": "confirmed_existing_agent",
        "unlocks": "background_or_parallel_work",
    },
    {
        "field": "role_binding_memory.current_role_agent_binding.host_liveness_status",
        "logical_field": "host_liveness_status",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_write_current_role_agent_binding",
        "required_value": "active",
        "unlocks": "resume_and_recovery_context",
    },
    {
        "field": "role_binding_memory.identity_policy.current_authority_source",
        "logical_field": "role_binding_memory.identity_policy.current_authority_source",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_write_current_role_agent_binding",
        "required_value": "role_binding_ledger",
        "unlocks": "resume_and_recovery_context",
    },
    {
        "field": "packet_result.packet_id",
        "logical_field": "packet_id",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_validate_current_node_result_event",
        "required_value": "current_packet_id",
        "unlocks": "current_result_mechanical_check",
    },
    {
        "field": "packet_result.result_id",
        "logical_field": "result_id",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_validate_current_node_result_event",
        "required_value": "current_result_id",
        "unlocks": "current_result_mechanical_check",
    },
    {
        "field": "packet_envelope.body_path",
        "logical_field": "path",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "validate_envelope_runtime_receipt",
        "required_value": "current_project_path",
        "unlocks": "runtime_receipt_check",
    },
    {
        "field": "packet_envelope.body_hash",
        "logical_field": "hash",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "validate_envelope_runtime_receipt",
        "required_value": "sha256_matches_body",
        "unlocks": "runtime_receipt_check",
    },
    {
        "field": "role_output_runtime.runtime_receipt_ref.path",
        "logical_field": "receipt_path",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "validate_envelope_runtime_receipt",
        "required_value": "current_receipt_path",
        "unlocks": "runtime_receipt_check",
    },
    {
        "field": "role_output_runtime.runtime_receipt_ref.hash",
        "logical_field": "receipt_hash",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "validate_envelope_runtime_receipt",
        "required_value": "receipt_hash_matches",
        "unlocks": "runtime_receipt_check",
    },
    {
        "field": "output_contract.missing_required_fields",
        "logical_field": "missing_fields",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "contract_self_check_metadata",
        "required_value": "explicit_missing_field_list",
        "unlocks": "current_ai_reissue_with_missing_fields",
    },
    {
        "field": "control_blocker.target_role_repair_instruction",
        "logical_field": "repair_instruction",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_write_control_blocker_repair_packet",
        "required_value": "current_role_repair_instruction",
        "unlocks": "current_ai_reissue_with_repair_instruction",
    },
    {
        "field": "pm_package_disposition.decision",
        "logical_field": "pm_disposition",
        "layer": "leaf",
        "owner": "project_manager",
        "status": "pm_decision_owned",
        "validator": "_write_pm_package_result_disposition",
        "required_value": "absorb_repair_block_or_stop",
        "unlocks": "runtime_frontier_update",
    },
    {
        "field": "reviewer_quality_review.decision",
        "logical_field": "reviewer_quality_decision",
        "layer": "leaf",
        "owner": "human_like_reviewer",
        "status": "reviewer_quality_owned",
        "validator": "_record_review_from_packet_result",
        "required_value": "quality_pass_or_block",
        "unlocks": "pm_quality_disposition",
    },
    {
        "field": "reviewer_quality_review.evidence",
        "logical_field": "reviewer_quality_evidence",
        "layer": "leaf",
        "owner": "human_like_reviewer",
        "status": "reviewer_quality_owned",
        "validator": "_record_review_from_packet_result",
        "required_value": "credible_current_evidence",
        "unlocks": "pm_quality_disposition",
    },
    {
        "field": "flowguard_process_review.target_result_id",
        "logical_field": "flowguard_target_result_id",
        "layer": "leaf",
        "owner": "flowguard_operator",
        "status": "flowguard_process_owned",
        "validator": "_record_flowguard_from_packet_result",
        "required_value": "current_result_id",
        "unlocks": "pm_process_disposition",
    },
    {
        "field": "flowguard_process_review.evidence_path",
        "logical_field": "flowguard_process_evidence_path",
        "layer": "leaf",
        "owner": "flowguard_operator",
        "status": "flowguard_process_owned",
        "validator": "_record_flowguard_from_packet_result",
        "required_value": "current_model_or_process_evidence",
        "unlocks": "pm_process_disposition",
    },
    {
        "field": "system_card_delivery.target_agent_id",
        "logical_field": "system_card_delivery.target_agent_id",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_system_card_target_agent_id",
        "required_value": "controller_runtime_helper_or_current_role_binding_agent",
        "unlocks": "direct_router_card_ack",
    },
)
REQUIRED_CURRENT_FIELD_CONTRACT_COUNT = len(CURRENT_FIELD_CONTRACTS)

RETIRED_FIELD_CONTRACTS = (
    {
        "field": "cards/reviewer/startup_fact_check.md",
        "status": "retired",
        "disposition": "removed_from_current_runtime_manifest",
    },
    {
        "field": "cards/phases/pm_startup_activation.md",
        "status": "retired",
        "disposition": "removed_from_current_runtime_manifest",
    },
)

FORBIDDEN_LEGACY_FIELD_CONTRACTS = (
    {
        "field": "startup_fact_report.external_fact_review.reviewer_checked_requirement_ids",
        "status": "forbidden_legacy",
        "disposition": "reject_as_old_startup_fact_gate",
    },
    {
        "field": "startup_fact_report.external_fact_review.direct_evidence_paths_checked",
        "status": "forbidden_legacy",
        "disposition": "reject_as_old_startup_fact_gate",
    },
    {
        "field": "reviewer_reports_startup_facts",
        "status": "forbidden_legacy",
        "disposition": "negative_test_only",
    },
    {
        "field": "pm_approves_startup_activation",
        "status": "forbidden_legacy",
        "disposition": "negative_test_only",
    },
    {
        "field": "reviewer_live_review_source",
        "status": "forbidden_legacy",
        "disposition": "replaced_by_startup_intake_authority_source",
    },
    {
        "field": "reviewer_must_not_use_chat_history",
        "status": "forbidden_legacy",
        "disposition": "replaced_by_router_must_not_use_chat_history_for_startup_intake",
    },
    {
        "field": "user_intake.metadata.pm_must_request_startup_reviewer_gate_before_opening_start_gate",
        "status": "forbidden_legacy",
        "disposition": "replaced_by_startup_runtime_release_required",
    },
    {
        "field": "user_intake.metadata.startup_gate_status",
        "status": "forbidden_legacy",
        "disposition": "replaced_by_startup_runtime_release_status",
    },
)

UNSUPPORTED_HISTORICAL_FIELD_SAMPLES = frozenset(
    {
        "startup_answers.runtime_role_assistances",
        "startup_answers.runtime_role_assistance_authorized",
        "startup_answers.scheduled_continuation",
        "startup_answers.heartbeat_requested",
        "startup_answers.single_agent_role_continuity_authorized",
        "boot_action.open_current_background_collaboration",
        "payload.current_background_role_bindings",
        "boot_action.bind_background_role_agents",
        "boot_action.start_role_slots",
        "boot_action.create_heartbeat_automation",
    }
)


@dataclass(frozen=True)
class Tick:
    pass


@dataclass(frozen=True)
class Action:
    label: str


@dataclass(frozen=True)
class State:
    status: str = "new"
    scenario: str = ""
    current_field_contracts_cataloged: int = 0
    field_statuses_cataloged: int = 0
    legacy_dispositions_cataloged: bool = False
    startup_answers_validated: bool = False
    packet_scope_filtered_to_current_options: bool = False
    top_level_runtime_fields_bound: bool = False
    startup_mechanical_field_audit_written: bool = False
    packet_role_runtime_fields_bound: bool = False
    runtime_leaf_mechanical_fields_bound: bool = False
    pm_decision_fields_bound: bool = False
    reviewer_quality_fields_bound: bool = False
    flowguard_process_fields_bound: bool = False
    current_background_agent_fields_bound: bool = False
    unsupported_historical_field_seen: bool = False
    unsupported_historical_field_accepted: bool = False
    unsupported_historical_field_translated: bool = False
    background_ack_missing: bool = False
    provenance_leaked_to_controller_scope: bool = False
    startup_fixed_role_binding_gate_required: bool = False
    fixed_role_count_gate_required: bool = False
    legacy_boot_action_accepted: bool = False
    classification: str = ""


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _selected_state(scenario: str) -> State:
    base = State(status="running", scenario=scenario)
    if scenario == SUCCESS:
        return base
    if scenario == UNSUPPORTED_STARTUP_FIELD_ACCEPTED:
        return replace(
            base,
            unsupported_historical_field_seen=True,
            unsupported_historical_field_accepted=True,
        )
    if scenario == UNSUPPORTED_FIELD_TRANSLATED:
        return replace(
            base,
            unsupported_historical_field_seen=True,
            unsupported_historical_field_translated=True,
        )
    if scenario == MISSING_BACKGROUND_ACK_ADVANCES:
        return replace(base, background_ack_missing=True)
    if scenario == PROVENANCE_PROMOTED_TO_SCOPE:
        return replace(base, provenance_leaked_to_controller_scope=True)
    if scenario == STARTUP_FIXED_ROLE_BINDING_GATE_REQUIRED:
        return replace(base, startup_fixed_role_binding_gate_required=True)
    if scenario == FIXED_ROLE_COUNT_GATE_REQUIRED:
        return replace(base, fixed_role_count_gate_required=True)
    if scenario == LEGACY_BOOT_ACTION_ACCEPTED:
        return replace(base, legacy_boot_action_accepted=True)
    raise ValueError(f"unknown scenario: {scenario}")


def field_contract_ready(state: State) -> bool:
    return (
        state.status == "running"
        and state.current_field_contracts_cataloged == REQUIRED_CURRENT_FIELD_CONTRACT_COUNT
        and state.field_statuses_cataloged == len(FIELD_STATUSES)
        and state.legacy_dispositions_cataloged
        and state.startup_answers_validated
        and state.packet_scope_filtered_to_current_options
        and state.top_level_runtime_fields_bound
        and state.startup_mechanical_field_audit_written
        and state.packet_role_runtime_fields_bound
        and state.runtime_leaf_mechanical_fields_bound
        and state.pm_decision_fields_bound
        and state.reviewer_quality_fields_bound
        and state.flowguard_process_fields_bound
        and state.current_background_agent_fields_bound
        and not state.unsupported_historical_field_accepted
        and not state.unsupported_historical_field_translated
        and not state.background_ack_missing
        and not state.provenance_leaked_to_controller_scope
        and not state.startup_fixed_role_binding_gate_required
        and not state.fixed_role_count_gate_required
        and not state.legacy_boot_action_accepted
    )


def _block_label(state: State) -> str:
    if state.unsupported_historical_field_accepted:
        return "block_unsupported_historical_field_accepted"
    if state.unsupported_historical_field_translated:
        return "block_unsupported_historical_field_translated"
    if state.background_ack_missing:
        return "block_missing_background_ack_field"
    if state.provenance_leaked_to_controller_scope:
        return "block_provenance_promoted_to_controller_scope"
    if state.startup_fixed_role_binding_gate_required:
        return "block_startup_fixed_role_binding_gate"
    if state.fixed_role_count_gate_required:
        return "block_fixed_role_count_gate"
    if state.legacy_boot_action_accepted:
        return "block_legacy_boot_action_accepted"
    return "block_field_contract_incomplete"


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _selected_state(scenario))
        return
    if state.status != "running":
        return
    if state.scenario != SUCCESS:
        label = _block_label(state)
        yield Transition(label, replace(state, status="blocked", classification=label))
        return
    if state.current_field_contracts_cataloged != REQUIRED_CURRENT_FIELD_CONTRACT_COUNT:
        yield Transition(
            "catalog_current_field_contracts",
            replace(state, current_field_contracts_cataloged=REQUIRED_CURRENT_FIELD_CONTRACT_COUNT),
        )
        return
    if state.field_statuses_cataloged != len(FIELD_STATUSES):
        yield Transition("catalog_field_status_lifecycle", replace(state, field_statuses_cataloged=len(FIELD_STATUSES)))
        return
    if not state.legacy_dispositions_cataloged:
        yield Transition("catalog_retired_and_forbidden_legacy_fields", replace(state, legacy_dispositions_cataloged=True))
        return
    if not state.startup_answers_validated:
        yield Transition("validate_startup_answer_fields", replace(state, startup_answers_validated=True))
        return
    if not state.packet_scope_filtered_to_current_options:
        yield Transition(
            "filter_packet_startup_scope_fields",
            replace(state, packet_scope_filtered_to_current_options=True),
        )
        return
    if not state.top_level_runtime_fields_bound:
        yield Transition(
            "bind_top_level_runtime_fields",
            replace(state, top_level_runtime_fields_bound=True),
        )
        return
    if not state.startup_mechanical_field_audit_written:
        yield Transition(
            "write_startup_mechanical_field_audit",
            replace(state, startup_mechanical_field_audit_written=True),
        )
        return
    if not state.packet_role_runtime_fields_bound:
        yield Transition(
            "bind_packet_role_result_current_fields",
            replace(state, packet_role_runtime_fields_bound=True),
        )
        return
    if not state.runtime_leaf_mechanical_fields_bound:
        yield Transition(
            "bind_runtime_leaf_mechanical_fields",
            replace(state, runtime_leaf_mechanical_fields_bound=True),
        )
        return
    if not state.pm_decision_fields_bound:
        yield Transition(
            "bind_pm_decision_fields",
            replace(state, pm_decision_fields_bound=True),
        )
        return
    if not state.reviewer_quality_fields_bound:
        yield Transition(
            "bind_reviewer_quality_fields",
            replace(state, reviewer_quality_fields_bound=True),
        )
        return
    if not state.flowguard_process_fields_bound:
        yield Transition(
            "bind_flowguard_process_fields",
            replace(state, flowguard_process_fields_bound=True),
        )
        return
    if not state.current_background_agent_fields_bound:
        yield Transition(
            "bind_current_background_agent_fields_after_route_allocation",
            replace(state, current_background_agent_fields_bound=True),
        )
        return
    if field_contract_ready(state):
        yield Transition("accept_field_contract", replace(state, status="complete", classification="accepted"))


def is_terminal(state: State) -> bool:
    return state.status in {"complete", "blocked"}


def is_success(state: State) -> bool:
    return is_terminal(state)


def hard_check_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status == "complete" and not field_contract_ready(replace(state, status="running")):
        failures.append("field contract was accepted without every current field transition")
    if state.status == "complete" and state.scenario in RISK_SCENARIOS:
        failures.append(f"risk scenario was accepted: {state.scenario}")
    if state.status == "blocked" and state.scenario == SUCCESS:
        failures.append("current field contract was blocked")
    return failures


def hard_invariant(state: State, trace: object) -> InvariantResult:
    del trace
    failures = hard_check_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "flowpilot_field_contract_gate",
        "Current fields must have one owner, one lifecycle status, one validator, and one forward transition; old fields cannot advance.",
        hard_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 16


class FlowPilotFieldContractStep:
    name = "FlowPilotFieldContractStep"
    reads = (
        "startup_answers",
        "packet_metadata",
        "startup_mechanical_audit",
        "role_binding_ledger",
        "current_role_agent_binding",
        "role_output_runtime_receipts",
        "pm_disposition",
        "reviewer_quality_review",
        "flowguard_process_review",
    )
    writes = ("field_contract_acceptance_or_block",)
    input_description = "field-contract scenario"
    output_description = "accepted current field contract or explicit block"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def build_workflow() -> Workflow:
    return Workflow((FlowPilotFieldContractStep(),), name=MODEL_ID)


def scenario_matrix() -> dict[str, str]:
    matrix: dict[str, str] = {}
    for scenario in SCENARIOS:
        transitions = list(next_safe_states(_selected_state(scenario)))
        matrix[scenario] = transitions[0].label if transitions else "missing_transition"
    return matrix


def hazard_states() -> dict[str, State]:
    hazards = {
        f"{scenario}_accepted": replace(_selected_state(scenario), status="complete")
        for scenario in RISK_SCENARIOS
    }
    hazards["success_overblocked"] = replace(_selected_state(SUCCESS), status="blocked")
    return hazards
