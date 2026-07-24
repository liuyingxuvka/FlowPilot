"""FlowGuard model for FlowPilot current-field contracts.

This model owns the field-level question: which current fields may advance the
FlowPilot path, which component validates them, and which next state they can
unlock. Unsupported historical fields are modeled only as hazards; production
code should reject them through current-schema checks, not translate them.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import sys
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow

RUNTIME_CONTRACTS_DIR = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "flowpilot"
    / "assets"
    / "flowpilot_core_runtime"
)
if str(RUNTIME_CONTRACTS_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_CONTRACTS_DIR))

import packet_result_contracts  # noqa: E402
import packet_stage_evidence_matrix  # noqa: E402


MODEL_ID = "flowpilot_field_contracts"

SUCCESS = "success"
UNSUPPORTED_STARTUP_FIELD_ACCEPTED = "unsupported_startup_field_accepted"
UNSUPPORTED_FIELD_TRANSLATED = "unsupported_field_translated"
MISSING_BACKGROUND_ACK_ADVANCES = "missing_background_ack_advances"
PROVENANCE_PROMOTED_TO_SCOPE = "provenance_promoted_to_scope"
STARTUP_FIXED_ROLE_BINDING_GATE_REQUIRED = "startup_fixed_role_binding_gate_required"
FIXED_ROLE_COUNT_GATE_REQUIRED = "fixed_role_count_gate_required"
LEGACY_BOOT_ACTION_ACCEPTED = "legacy_boot_action_accepted"
PACKET_RESULT_CONTRACT_MISALIGNED = "packet_result_contract_misaligned"
REPAIR_IDENTITY_PROSE_ONLY = "repair_identity_prose_only"
REPAIR_IDENTITY_CHAIN_MISALIGNED = "repair_identity_chain_misaligned"
REPAIR_IDENTITY_REVIEWER_OWNED = "repair_identity_reviewer_owned"

SCENARIOS = (
    SUCCESS,
    UNSUPPORTED_STARTUP_FIELD_ACCEPTED,
    UNSUPPORTED_FIELD_TRANSLATED,
    MISSING_BACKGROUND_ACK_ADVANCES,
    PROVENANCE_PROMOTED_TO_SCOPE,
    STARTUP_FIXED_ROLE_BINDING_GATE_REQUIRED,
    FIXED_ROLE_COUNT_GATE_REQUIRED,
    LEGACY_BOOT_ACTION_ACCEPTED,
    PACKET_RESULT_CONTRACT_MISALIGNED,
    REPAIR_IDENTITY_PROSE_ONLY,
    REPAIR_IDENTITY_CHAIN_MISALIGNED,
    REPAIR_IDENTITY_REVIEWER_OWNED,
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
        "field": "flowpilot_runtime_self_check_receipt.ok",
        "logical_field": "portable_runtime_self_check_ok",
        "layer": "leaf",
        "owner": "flowpilot_runtime_self_check",
        "status": "mechanical_runtime_owned",
        "validator": "flowpilot_runtime_self_check.runtime_self_check",
        "required_value": True,
        "unlocks": "target_project_flowpilot_run_without_dev_repo_scripts",
    },
    {
        "field": "flowpilot_runtime_self_check_receipt.dev_repo_simulations_required",
        "logical_field": "target_project_dev_repo_simulations_required",
        "layer": "leaf",
        "owner": "flowpilot_runtime_self_check",
        "status": "mechanical_runtime_owned",
        "validator": "flowpilot_runtime_self_check.runtime_self_check",
        "required_value": False,
        "unlocks": "portable_installed_skill_runtime",
    },
    {
        "field": "flowpilot_runtime_self_check_receipt.required_runtime_assets[]",
        "logical_field": "portable_runtime_required_assets",
        "layer": "leaf",
        "owner": "flowpilot_runtime_self_check",
        "status": "mechanical_runtime_owned",
        "validator": "flowpilot_runtime_self_check.runtime_self_check",
        "required_value": "installed_skill_required_asset_paths",
        "unlocks": "runtime_start_blocks_missing_installed_assets",
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
        "field": "packet.status",
        "logical_field": "packet_status_currentness",
        "layer": "middle",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "lifecycle": "terminal_monotonic",
        "validator": "submit_result",
        "required_value": "noncurrent_terminal_status_preserved_after_late_result",
        "unlocks": "single_current_packet_routing_authority",
    },
    {
        "field": "packet.result_ids",
        "logical_field": "packet_result_history",
        "layer": "middle",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "lifecycle": "append_only_audit",
        "validator": "submit_result",
        "required_value": "append_only_result_history_without_current_authority",
        "unlocks": "late_result_audit_without_packet_reactivation",
    },
    {
        "field": "packet.accepted_result_id",
        "logical_field": "accepted_result_pointer",
        "layer": "middle",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "lifecycle": "single_authority_pointer",
        "validator": "_accept_packet_result",
        "required_value": "single_runtime_acceptance_commit_point",
        "unlocks": "accepted_packet_result_authority",
    },
    {
        "field": "packet.latest_quarantined_result_id",
        "logical_field": "latest_quarantined_result_pointer",
        "layer": "middle",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "lifecycle": "single_authority_pointer",
        "validator": "submit_result",
        "required_value": "quarantine_audit_pointer_only",
        "unlocks": "quarantined_result_visibility_without_current_authority",
    },
    {
        "field": "route_node.status",
        "logical_field": "route_node_currentness_status",
        "layer": "middle",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "lifecycle": "terminal_monotonic",
        "validator": "_route_node_is_noncurrent",
        "required_value": "accepted_waived_superseded_nodes_exclude_packets_from_current_work",
        "unlocks": "route_node_scoped_packet_currentness",
    },
    {
        "field": "route_node.supplemental_repair_contract_ids",
        "logical_field": "supplemental_repair_contract_projection",
        "layer": "leaf",
        "owner": "project_manager",
        "status": "current",
        "lifecycle": "append_only_current_contract_projection",
        "validator": "_normalize_strict_route_plan_nodes",
        "required_value": "contract_ids_from_pm_supplemental_repair_contract",
        "unlocks": "supplemental_repair_item_final_ledger_closure",
    },
    {
        "field": "route_node.supplemental_repair_item_ids",
        "logical_field": "supplemental_repair_item_projection",
        "layer": "leaf",
        "owner": "project_manager",
        "status": "current",
        "lifecycle": "append_only_current_contract_projection",
        "validator": "_normalize_strict_route_plan_nodes",
        "required_value": "repair_item_ids_from_pm_supplemental_repair_contract",
        "unlocks": "supplemental_repair_item_final_ledger_closure",
    },
    {
        "field": "terminal_supplemental_repair.current_round",
        "logical_field": "terminal_supplemental_repair_round",
        "layer": "middle",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "lifecycle": "monotonic_until_exhausted",
        "validator": "_parse_terminal_supplemental_repair_contract_payload",
        "required_value": "next_round_number_not_exceeding_three",
        "unlocks": "terminal_supplemental_repair_round_cap",
    },
    {
        "field": "terminal_supplemental_repair.max_rounds",
        "logical_field": "terminal_supplemental_repair_max_rounds",
        "layer": "middle",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "lifecycle": "constant_runtime_owned",
        "validator": "_terminal_supplemental_state",
        "required_value": 3,
        "unlocks": "repair_rounds_exhausted_terminal_stop",
    },
    {
        "field": "terminal_supplemental_repair.status",
        "logical_field": "terminal_supplemental_repair_status",
        "layer": "middle",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "lifecycle": "inactive_active_clean_or_exhausted",
        "validator": "_record_terminal_supplemental_repair_contract",
        "required_value": "inactive|active|clean|repair_rounds_exhausted",
        "unlocks": "terminal_closure_or_terminal_stop",
    },
    {
        "field": "supplemental_repair_contracts[].repair_items[].owner_repair_node_id",
        "logical_field": "supplemental_repair_item_owner_node",
        "layer": "leaf",
        "owner": "project_manager",
        "status": "current",
        "lifecycle": "current_contract_append_only",
        "validator": "_parse_terminal_supplemental_repair_contract_payload",
        "required_value": "current_or_route_plan_repair_node_id",
        "unlocks": "supplemental_repair_node_execution_and_closure",
    },
    {
        "field": "execution_frontier.pending_route_mutation",
        "logical_field": "pending_route_mutation",
        "layer": "middle",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "lifecycle": "pending_until_commit",
        "validator": "_advance_frontier_after_node_acceptance",
        "required_value": "cleared_or_terminal_after_replacement_node_commit",
        "unlocks": "route_mutation_frontier_no_stale_pending_work",
    },
    {
        "field": "active_packets",
        "logical_field": "active_packet_projection",
        "layer": "middle",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "lifecycle": "derived_projection",
        "validator": "_current_packets_for_routing",
        "required_value": "derived_from_packet_is_noncurrent_for_routing",
        "unlocks": "router_and_compact_views_share_router_currentness",
    },
    {
        "field": "closure_accepted_packets",
        "logical_field": "closure_accepted_packet_evidence_projection",
        "layer": "middle",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "lifecycle": "derived_projection",
        "validator": "_accepted_packets_for_closure_evidence",
        "required_value": "derived_from_active_route_accepted_packet_result_authority",
        "unlocks": "final_closure_uses_accepted_evidence_without_reactivating_packets",
    },
    {
        "field": "accepted_result_packets",
        "logical_field": "active_route_accepted_result_packet_projection",
        "layer": "middle",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "lifecycle": "derived_projection",
        "validator": "_accepted_result_packets_for_active_route",
        "required_value": "active_route_packets_with_accepted_result_id_even_when_not_router_current",
        "unlocks": "accepted_packet_lease_health_and_closure_evidence",
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
        "field": "responsibility_lease.ack_received",
        "logical_field": "ack_received",
        "layer": "middle",
        "owner": "flowpilot_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "ack_lease",
        "required_value": "true_before_result_wait",
        "unlocks": "current_wait_liveness_evidence",
    },
    {
        "field": "responsibility_lease.ack_received_at",
        "logical_field": "ack_received_at",
        "layer": "middle",
        "owner": "flowpilot_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "ack_lease",
        "required_value": "current_run_timestamp",
        "unlocks": "current_wait_liveness_evidence",
    },
    {
        "field": "current_role_agent_binding.current_run_binding_decision",
        "logical_field": "current_role_agent_binding.current_run_binding_decision",
        "layer": "middle",
        "owner": "host_background_collaboration",
        "status": "mechanical_runtime_owned",
        "validator": "_normalize_current_role_agent_binding",
        "required_value": "existing_current_agent_reused_or_current_run_replacement_opened",
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
        "field": "responsibility_lease.progress_count",
        "logical_field": "progress_count",
        "layer": "middle",
        "owner": "flowpilot_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "record_progress",
        "required_value": "metadata_only_liveness_counter",
        "unlocks": "current_wait_liveness_evidence",
    },
    {
        "field": "responsibility_lease.last_progress_at",
        "logical_field": "last_progress_at",
        "layer": "middle",
        "owner": "flowpilot_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "record_progress",
        "required_value": "current_run_timestamp",
        "unlocks": "current_wait_liveness_evidence",
    },
    {
        "field": "role_binding_ledger.role_slots[].current_run_binding_decision",
        "logical_field": "role_binding_ledger.role_slots[].current_run_binding_decision",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_write_current_role_agent_binding",
        "required_value": "existing_current_agent_reused_or_current_run_replacement_opened",
        "unlocks": "background_or_parallel_work",
    },
    {
        "field": "lifecycle_guard.last_liveness_evidence_kind",
        "logical_field": "last_liveness_evidence_kind",
        "layer": "middle",
        "owner": "flowpilot_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_latest_liveness_evidence",
        "required_value": "ack_or_progress_only",
        "unlocks": "current_wait_liveness_evidence",
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
        "field": "output_contract.forbidden_fields_seen",
        "logical_field": "forbidden_fields_seen",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "contract_self_check_metadata",
        "required_value": "explicit_forbidden_field_list",
        "unlocks": "current_ai_reissue_with_forbidden_fields",
    },
    {
        "field": "output_contract.contract_family_id",
        "logical_field": "contract_family_id",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "contract_self_check_metadata",
        "required_value": "current_packet_result_family_id",
        "unlocks": "same_family_current_contract_reissue",
    },
    {
        "field": "output_contract.mechanical_contract_failure",
        "logical_field": "mechanical_contract_failure",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "contract_self_check_metadata",
        "required_value": "structured_missing_and_forbidden_field_report",
        "unlocks": "same_family_current_contract_reissue",
    },
    {
        "field": "output_contract.minimal_valid_shape",
        "logical_field": "minimal_valid_shape",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "contract_self_check_metadata",
        "required_value": "family_specific_current_shape_example",
        "unlocks": "current_ai_reissue_without_old_shape_guessing",
    },
    {
        "field": "output_contract.mechanical_contract_failure.failed_branch",
        "logical_field": "failed_branch",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_contract_block",
        "required_value": "current_contract_branch_that_failed",
        "unlocks": "current_ai_reissue_with_branch_specific_correction",
    },
    {
        "field": "output_contract.mechanical_contract_failure.failed_field_path",
        "logical_field": "failed_field_path",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_contract_block",
        "required_value": "current_contract_field_path_that_failed",
        "unlocks": "current_ai_reissue_with_branch_specific_correction",
    },
    {
        "field": "output_contract.branch_minimal_valid_shape",
        "logical_field": "branch_minimal_valid_shape",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_block_result_and_reissue_current_packet_family",
        "required_value": "branch_specific_current_shape_example",
        "unlocks": "current_ai_reissue_without_branch_shape_guessing",
    },
    {
        "field": "current_handoff_contract.contract_family_id",
        "logical_field": "contract_family_id",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_build_current_handoff_contract",
        "required_value": "current_packet_result_family_id",
        "unlocks": "role_visible_current_contract",
    },
    {
        "field": "current_handoff_contract.stage_evidence_matrix.family_id",
        "logical_field": "stage_evidence_family_id",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_build_current_handoff_contract",
        "required_value": "same_family_as_current_packet_result_contract",
        "unlocks": "role_visible_stage_evidence_contract",
    },
    {
        "field": "current_handoff_contract.stage_evidence_matrix.lifecycle_stage",
        "logical_field": "stage_evidence_lifecycle_stage",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_build_current_handoff_contract",
        "required_value": "current_stage_for_this_packet_family",
        "unlocks": "role_knows_current_evidence_timing",
    },
    {
        "field": "current_handoff_contract.stage_evidence_matrix.current_required_fields",
        "logical_field": "stage_evidence_current_required_fields",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_build_current_handoff_contract",
        "required_value": "non_empty_current_stage_pass_criteria",
        "unlocks": "role_does_not_guess_future_stage_evidence",
    },
    {
        "field": "current_handoff_contract.input_material_manifest.authorized_result_reads[]",
        "logical_field": "authorized_result_reads",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_normalize_authorized_result_reads",
        "required_value": "current_result_read_refs_with_hash_and_allowed_roles",
        "unlocks": "role_reads_current_inputs_before_submit",
    },
    {
        "field": "current_handoff_contract.input_material_manifest.authorized_result_read_ids",
        "logical_field": "authorized_result_read_ids",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_build_current_handoff_contract",
        "required_value": "all_result_body_ids_the_assigned_role_must_open_before_submit",
        "unlocks": "role_reads_all_related_blocker_context_bodies",
    },
    {
        "field": "current_handoff_contract.input_material_manifest.required_authorized_read_count",
        "logical_field": "required_authorized_read_count",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_build_current_handoff_contract",
        "required_value": "count_of_required_authorized_result_bodies_before_submit",
        "unlocks": "model_detects_missing_related_body_authorization",
    },
    {
        "field": "flowguard_reissue_packet.envelope.authorized_result_reads[]",
        "logical_field": "flowguard_reissue_authorized_result_reads",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_flowguard_reissue_inherited_authorized_result_reads",
        "required_value": "source_flowguard_packet_authorized_result_reads",
        "unlocks": "reissued_flowguard_packet_requires_same_material_bodies",
    },
    {
        "field": "flowguard_reissue_packet.current_handoff_contract.input_material_manifest.required_authorized_reads_before_submit",
        "logical_field": "flowguard_reissue_required_authorized_reads_before_submit",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_build_current_handoff_contract",
        "required_value": "source_flowguard_packet_required_authorized_read_ids",
        "unlocks": "reissued_flowguard_packet_blocks_unopened_inherited_bodies",
    },
    {
        "field": "current_handoff_contract.input_material_manifest.all_required_authorized_result_bodies_must_be_opened_before_submit",
        "logical_field": "all_required_authorized_result_bodies_must_be_opened_before_submit",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_required_authorized_result_read_blockers",
        "required_value": True,
        "unlocks": "result_submission_waits_for_all_related_body_receipts",
    },
    {
        "field": "current_handoff_contract.input_material_manifest.packet_body_opened_by_assigned_role_via_open_packet",
        "logical_field": "packet_body_opened_by_assigned_role_via_open_packet",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "flowpilot_new_role_commands.open_packet",
        "required_value": True,
        "unlocks": "assigned_role_reads_current_packet_body_and_authorized_materials_together",
    },
    {
        "field": "pm_repair_packet.repair_evidence_obligations[]",
        "logical_field": "repair_evidence_obligations",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_repair_evidence_obligations_for_blocker",
        "required_value": "one_row_per_current_blocker_missing_material_or_recheck_need",
        "unlocks": "pm_must_disposition_specific_repair_obligations",
    },
    {
        "field": "pm_repair_packet.repair_evidence_obligations[].obligation_id",
        "logical_field": "repair_evidence_obligation_id",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_repair_evidence_obligations_for_blocker",
        "required_value": "stable_current_blocker_scoped_obligation_id",
        "unlocks": "repair_obligation_disposition_exact_match",
    },
    {
        "field": "pm_repair_packet.repair_evidence_obligations[].source_blocker_id",
        "logical_field": "repair_evidence_obligation_source_blocker_id",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_repair_evidence_obligations_for_blocker",
        "required_value": "current_blocker_id",
        "unlocks": "repair_context_binds_back_to_blocker",
    },
    {
        "field": "pm_repair_packet.repair_evidence_obligations[].evidence_kind",
        "logical_field": "repair_evidence_obligation_evidence_kind",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_repair_evidence_obligations_for_blocker",
        "required_value": "current_blocker_evidence_kind",
        "unlocks": "repair_worker_and_flowguard_know_what_evidence_to_produce_or_recheck",
    },
    {
        "field": "pm_repair_result.repair_obligation_disposition[]",
        "logical_field": "repair_obligation_disposition",
        "layer": "middle",
        "owner": "pm",
        "status": "pm_decision_owned",
        "validator": "_pm_repair_obligation_disposition_violation",
        "required_value": "one_disposition_per_repair_evidence_obligation",
        "unlocks": "repair_packet_receives_obligation_context",
    },
    {
        "field": "pm_repair_result.repair_obligation_disposition[].obligation_id",
        "logical_field": "repair_obligation_disposition_obligation_id",
        "layer": "leaf",
        "owner": "pm",
        "status": "pm_decision_owned",
        "validator": "_pm_repair_obligation_disposition_violation",
        "required_value": "exact_obligation_id_from_pm_repair_packet",
        "unlocks": "runtime_rejects_unknown_duplicate_or_missing_disposition_rows",
    },
    {
        "field": "pm_repair_result.repair_obligation_disposition[].disposition",
        "logical_field": "repair_obligation_disposition_status",
        "layer": "leaf",
        "owner": "pm",
        "status": "pm_decision_owned",
        "validator": "_pm_repair_obligation_disposition_violation",
        "required_value": "decision_consistent_resolution_not_summary_or_registry_only",
        "unlocks": "runtime_rejects_reason_only_or_stale_evidence_repairs",
    },
    {
        "field": "repair_packet.repair_obligation_context",
        "logical_field": "repair_obligation_context",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_attach_repair_obligation_context_to_packet",
        "required_value": "pm_decision_obligations_and_dispositions_copied_to_current_repair_packet",
        "unlocks": "repair_role_reads_what_the_repair_must_fix",
    },
    {
        "field": "flowguard.semantic_recheck.consumed_repair_obligation_ids",
        "logical_field": "consumed_repair_obligation_ids",
        "layer": "leaf",
        "owner": "flowguard_operator",
        "status": "flowguard_process_owned",
        "validator": "_flowguard_semantic_recheck_contract_violation",
        "required_value": "all_repair_evidence_obligation_ids_from_result_contract_profile_binding",
        "unlocks": "flowguard_cannot_pass_without_consuming_repair_obligations",
    },
    {
        "field": "flowguard_packet.envelope.result_contract_profile_ids[]",
        "logical_field": "flowguard_result_contract_profile_ids",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "issue_task_packet",
        "required_value": "flowguard.semantic_recheck_required_when_semantic_recheck_is_current_contract",
        "unlocks": "semantic_recheck_fields_are_external_structured_contract_not_hidden_body_fields",
    },
    {
        "field": "flowguard_packet.envelope.result_contract_profile_bindings.flowguard.semantic_recheck_required",
        "logical_field": "flowguard_semantic_recheck_profile_binding",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "packet_result_contracts.effective_result_contract_from_envelope",
        "required_value": "blocker_id_authorized_result_read_ids_repair_obligation_ids_and_coverage_boundary",
        "unlocks": "ai_visible_required_fields_allowed_values_field_types_and_minimal_shape",
    },
    {
        "field": "current_handoff_contract.required_report_contract.required_result_body_fields",
        "logical_field": "required_result_body_fields",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_current_result_submission_contract_violation",
        "required_value": "same_fields_as_packet_result_contract_row",
        "unlocks": "role_submits_contract_declared_result",
    },
    {
        "field": "current_handoff_contract.required_report_contract.required_child_fields",
        "logical_field": "required_child_fields",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_build_current_handoff_contract",
        "required_value": "same_child_fields_as_packet_result_contract_row",
        "unlocks": "role_submits_nested_contract_declared_result",
    },
    {
        "field": "current_handoff_contract.required_report_contract.branch_valid_shapes",
        "logical_field": "branch_valid_shapes",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "branch_valid_shapes_for_family",
        "required_value": "branch_specific_current_shape_examples",
        "unlocks": "role_submits_contract_declared_branch_result",
    },
    {
        "field": "current_handoff_contract.required_report_contract.non_empty_array_fields",
        "logical_field": "non_empty_array_fields",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_build_current_handoff_contract",
        "required_value": "same_non_empty_array_fields_as_packet_result_contract_row",
        "unlocks": "role_keeps_required_evidence_arrays_non_empty",
    },
    {
        "field": "current_handoff_contract.required_report_contract.forbidden_fields",
        "logical_field": "required_report_contract_forbidden_fields",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_build_current_handoff_contract",
        "required_value": "same_forbidden_fields_as_effective_packet_result_contract",
        "unlocks": "role_avoids_unsupported_old_fields_from_the_single_handoff_authority",
    },
    {
        "field": "current_handoff_contract.required_report_contract.stage_evidence_matrix",
        "logical_field": "required_report_stage_evidence_matrix",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_build_current_handoff_contract",
        "required_value": "same_stage_evidence_matrix_as_current_handoff_contract",
        "unlocks": "assigned_role_submits_against_current_stage_not_future_stage",
    },
    {
        "field": "submission_checklist.required_result_body_fields",
        "logical_field": "submission_checklist_required_result_body_fields",
        "layer": "middle",
        "owner": "flowpilot_new_role_commands",
        "status": "mechanical_runtime_owned",
        "validator": "_submission_checklist_from_current_handoff_contract",
        "required_value": "projection_of_current_handoff_contract.required_report_contract.required_result_body_fields",
        "unlocks": "assigned_role_sees_current_required_result_fields",
    },
    {
        "field": "submission_checklist.required_child_fields",
        "logical_field": "submission_checklist_required_child_fields",
        "layer": "middle",
        "owner": "flowpilot_new_role_commands",
        "status": "mechanical_runtime_owned",
        "validator": "_submission_checklist_from_current_handoff_contract",
        "required_value": "projection_of_current_handoff_contract.required_report_contract.required_child_fields",
        "unlocks": "assigned_role_sees_current_nested_result_fields",
    },
    {
        "field": "submission_checklist.branch_valid_shapes",
        "logical_field": "submission_checklist_branch_valid_shapes",
        "layer": "middle",
        "owner": "flowpilot_new_role_commands",
        "status": "mechanical_runtime_owned",
        "validator": "_submission_checklist_from_current_handoff_contract",
        "required_value": "projection_of_current_handoff_contract.required_report_contract.branch_valid_shapes",
        "unlocks": "assigned_role_sees_current_branch_shape_examples",
    },
    {
        "field": "submission_checklist.non_empty_array_fields",
        "logical_field": "submission_checklist_non_empty_array_fields",
        "layer": "middle",
        "owner": "flowpilot_new_role_commands",
        "status": "mechanical_runtime_owned",
        "validator": "_submission_checklist_from_current_handoff_contract",
        "required_value": "projection_of_current_handoff_contract.required_report_contract.non_empty_array_fields",
        "unlocks": "assigned_role_sees_current_non_empty_array_obligations",
    },
    {
        "field": "submission_checklist.input_material_manifest.required_authorized_reads_before_submit",
        "logical_field": "submission_checklist_required_authorized_reads_before_submit",
        "layer": "middle",
        "owner": "flowpilot_new_role_commands",
        "status": "mechanical_runtime_owned",
        "validator": "_submission_checklist_from_current_handoff_contract",
        "required_value": "projection_of_current_handoff_contract.input_material_manifest.required_authorized_reads_before_submit",
        "unlocks": "assigned_role_sees_current_required_result_body_reads",
    },
    {
        "field": "current_handoff_contract.missing_information_response",
        "logical_field": "missing_information_response",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_packet_handoff_missing_information_response",
        "required_value": "current_contract_exit_without_old_shape_translation",
        "unlocks": "role_blocks_or_reissues_without_guessing",
    },
    {
        "field": "research_packet_spec.to_role",
        "logical_field": "research_packet_recipient_role",
        "layer": "middle",
        "owner": "flowpilot_router_work_packets_material",
        "status": "mechanical_runtime_owned",
        "validator": "_write_research_capability_decision",
        "required_value": "worker_or_flowguard_operator",
        "unlocks": "research_packet_created_for_current_role",
    },
    {
        "field": "current_handoff_contract.downstream_consumer.unlocks",
        "logical_field": "downstream_consumer",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_build_current_handoff_contract",
        "required_value": "same_unlock_as_packet_result_contract_row",
        "unlocks": "next_runtime_consumer_receives_expected_report",
    },
    {
        "field": "current_handoff_contract.status_projection_requirements.repair_chain_visible_when_current",
        "logical_field": "repair_chain_visible_when_current",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_blocker_current_effective",
        "required_value": "true_for_current_repair_chain",
        "unlocks": "public_status_shows_current_repair_chain",
    },
    {
        "field": "packet.repair_blocker_id",
        "logical_field": "repair_blocker_id",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_packet_repair_blocker_id",
        "required_value": "current_blocker_id_for_repair_chain",
        "unlocks": "current_repair_identity_scope",
    },
    {
        "field": "packet.envelope.repair_blocker_id",
        "logical_field": "repair_blocker_id",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "issue_task_packet",
        "required_value": "same_current_blocker_id_as_packet_repair_blocker_id",
        "unlocks": "current_handoff_contract_blocker_projection",
    },
    {
        "field": "packet.active_blocker_id",
        "logical_field": "active_blocker_id",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_record_semantic_blocker",
        "required_value": "current_active_blocker_id_or_empty_after_disposition",
        "unlocks": "current_blocker_repair_or_review_gate",
    },
    {
        "field": "current_handoff_contract.input_material_manifest.subject_id",
        "logical_field": "handoff_subject_id",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_build_current_handoff_contract",
        "required_value": "current_subject_packet_or_blocker_id",
        "unlocks": "role_receives_current_subject_identity",
    },
    {
        "field": "current_handoff_contract.input_material_manifest.target_result_id",
        "logical_field": "handoff_target_result_id",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_build_current_handoff_contract",
        "required_value": "current_target_result_id_when_result_bound",
        "unlocks": "role_receives_current_target_result_identity",
    },
    {
        "field": "current_handoff_contract.input_material_manifest.route_node_id",
        "logical_field": "handoff_route_node_id",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_build_current_handoff_contract",
        "required_value": "current_route_node_id",
        "unlocks": "role_receives_current_route_node_identity",
    },
    {
        "field": "current_handoff_contract.input_material_manifest.blocker_id",
        "logical_field": "handoff_blocker_id",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_build_current_handoff_contract",
        "required_value": "current_repair_blocker_id_or_explicit_not_applicable",
        "unlocks": "runtime_mechanical_repair_identity_gate",
    },
    {
        "field": "staged_effect.blocker_id",
        "logical_field": "staged_effect_blocker_id",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_attach_staged_effect",
        "required_value": "same_current_repair_blocker_id_or_explicit_not_applicable",
        "unlocks": "review_gate_after_runtime_identity_check",
    },
    {
        "field": "flowguard_evidence.generator_inputs.blocker_id",
        "logical_field": "flowguard_generator_blocker_id",
        "layer": "leaf",
        "owner": "flowguard_operator",
        "status": "flowguard_process_owned",
        "validator": "_ensure_flowguard_packet_for_task_result",
        "required_value": "same_current_repair_blocker_id_or_explicit_not_applicable",
        "unlocks": "flowguard_replay_binds_repair_identity",
    },
    {
        "field": "flowguard_evidence.subject_context.blocker_id",
        "logical_field": "flowguard_subject_context_blocker_id",
        "layer": "leaf",
        "owner": "flowguard_operator",
        "status": "flowguard_process_owned",
        "validator": "_ensure_flowguard_packet_for_task_result",
        "required_value": "same_current_repair_blocker_id_or_explicit_not_applicable",
        "unlocks": "flowguard_subject_context_binds_repair_identity",
    },
    {
        "field": "flowguard_result.blocker_id",
        "logical_field": "flowguard_result_blocker_id",
        "layer": "leaf",
        "owner": "flowguard_operator",
        "status": "flowguard_process_owned",
        "validator": "_record_flowguard_from_packet_result",
        "required_value": "same_current_repair_blocker_id_or_explicit_not_applicable",
        "unlocks": "reviewer_receives_process_evidence_after_runtime_identity_gate",
    },
    {
        "field": "flowguard_evidence_manifest.entries[].blocker_id",
        "logical_field": "flowguard_evidence_manifest_blocker_id",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_flowguard_evidence_reads_for_review",
        "required_value": "same_current_repair_blocker_id_as_flowguard_result_blocker_id",
        "unlocks": "review_packet_receives_matching_process_evidence_identity",
    },
    {
        "field": "review_packet.repair_blocker_id",
        "logical_field": "review_repair_blocker_id",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_ensure_review_packet_for_task_result",
        "required_value": "same_current_repair_blocker_id_as_flowguard_packet",
        "unlocks": "reviewer_quality_review_after_runtime_identity_gate",
    },
    {
        "field": "active_blocker.status",
        "logical_field": "active_blocker_status",
        "layer": "middle",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_retire_older_same_family_blockers",
        "required_value": "current_open_or_dispositioned_after_route_replacement",
        "unlocks": "final_preflight_ignores_audit_only_superseded_blockers",
    },
    {
        "field": "active_blocker.retired_by_blocker_id",
        "logical_field": "retired_by_blocker_id",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_retire_older_same_family_blockers",
        "required_value": "new_current_blocker_id_when_superseded",
        "unlocks": "superseded_repair_chain_disposition",
    },
    {
        "field": "preplanning.high_standard_contract.requirements[]",
        "logical_field": "high_standard_requirements",
        "layer": "middle",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_high_standard_contract_result_violation",
        "required_value": "non_empty_top_level_requirements_list_without_decision_wrapper",
        "unlocks": "high_standard_contract_flowguard_review",
    },
    {
        "field": "preplanning.high_standard_contract.requirements[].requirement_id",
        "logical_field": "high_standard_requirement_id",
        "layer": "leaf",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_parse_high_standard_requirements",
        "required_value": "non_empty_string",
        "unlocks": "high_standard_requirement_binding",
    },
    {
        "field": "preplanning.high_standard_contract.requirements[].classification",
        "logical_field": "high_standard_requirement_classification",
        "layer": "leaf",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_parse_high_standard_requirements",
        "required_value": "current_requirement_classification",
        "unlocks": "high_standard_requirement_binding",
    },
    {
        "field": "preplanning.high_standard_contract.requirements[].summary",
        "logical_field": "high_standard_requirement_summary",
        "layer": "leaf",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_parse_high_standard_requirements",
        "required_value": "non_empty_string",
        "unlocks": "high_standard_requirement_binding",
    },
    {
        "field": "preplanning.high_standard_contract.requirements[].closure_rule",
        "logical_field": "high_standard_requirement_closure_rule",
        "layer": "leaf",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_parse_high_standard_requirements",
        "required_value": "non_empty_current_closure_rule",
        "unlocks": "high_standard_requirement_binding",
    },
    {
        "field": "preplanning.high_standard_contract.acceptance_item_registry.items[]",
        "logical_field": "acceptance_item_registry",
        "layer": "middle",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_high_standard_contract_result_violation",
        "required_value": "non_empty_top_level_items_list_with_user_and_pm_high_standard_sources",
        "unlocks": "route_node_acceptance_item_assignment",
    },
    {
        "field": "preplanning.high_standard_contract.acceptance_item_registry.items[].acceptance_item_id",
        "logical_field": "acceptance_item_id",
        "layer": "leaf",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_parse_acceptance_item_registry",
        "required_value": "unique_non_empty_string",
        "unlocks": "node_and_final_replay_acceptance_item_binding",
    },
    {
        "field": "preplanning.high_standard_contract.acceptance_item_registry.items[].source_type",
        "logical_field": "acceptance_item_source_type",
        "layer": "leaf",
        "owner": "pm",
        "status": "pm_decision_owned",
        "validator": "_parse_acceptance_item_registry",
        "required_value": "at_least_one_user_explicit_or_user_implicit_and_one_pm_high_standard",
        "unlocks": "user_and_pm_standard_coverage_audit",
    },
    {
        "field": "preplanning.high_standard_contract.acceptance_item_registry.items[].quality_floor",
        "logical_field": "acceptance_item_quality_floor",
        "layer": "leaf",
        "owner": "pm",
        "status": "pm_decision_owned",
        "validator": "_parse_acceptance_item_registry",
        "required_value": "non_empty_high_quality_floor",
        "unlocks": "reviewer_blocks_low_quality_success",
    },
    {
        "field": "preplanning.high_standard_contract.acceptance_item_registry.items[].future_evidence_rule",
        "logical_field": "acceptance_item_future_evidence_rule",
        "layer": "leaf",
        "owner": "reviewer",
        "status": "reviewer_quality_owned",
        "validator": "_parse_acceptance_item_registry",
        "required_value": "non_empty_future_evidence_rule_without_terminal_proof_requirement",
        "unlocks": "node_plan_and_final_replay_evidence_check",
    },
    {
        "field": "task.discovery.packet.body.runtime_local_capability_inventory",
        "logical_field": "runtime_local_capability_inventory",
        "layer": "middle",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "lifecycle": "packet_only_shallow_snapshot",
        "validator": "_runtime_local_capability_inventory",
        "required_value": "current_local_skill_paths_and_availability_without_deep_instruction_read",
        "unlocks": "pm_candidate_skill_selection",
    },
    {
        "field": "preplanning.discovery.candidate_skill_inventory",
        "logical_field": "preplanning_candidate_skill_inventory",
        "layer": "leaf",
        "owner": "project_manager",
        "status": "pm_decision_owned",
        "lifecycle": "accepted_current_selection",
        "validator": "_ensure_skill_standard_packet",
        "required_value": "explicit_list_selected_from_current_runtime_inventory",
        "unlocks": "selected_skill_deep_read_and_skill_standard_contract",
    },
    {
        "field": "packet_result.contract_self_check.workstream_plan_and_completion",
        "logical_field": "role_workstream_plan_and_completion",
        "layer": "middle",
        "owner": "assigned_substantive_role_agent",
        "status": "reviewer_quality_owned",
        "lifecycle": "role_authored_semantic_report",
        "validator": "REVIEW_FLOW_STAGE_CHALLENGE_BINDINGS",
        "required_value": "numbered_plan_rows_with_status_evidence_deviation_integration_verification_and_remaining_blockers",
        "unlocks": "reviewer_quality_disposition_or_pm_repair",
    },
    {
        "field": "preplanning.skill_standard.obligations[]",
        "logical_field": "skill_standard_obligations",
        "layer": "middle",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_parse_skill_obligations",
        "required_value": "non_empty_top_level_obligations_list",
        "unlocks": "skill_standard_contract_acceptance",
    },
    {
        "field": "preplanning.skill_standard.obligations[].obligation_id",
        "logical_field": "skill_standard_obligation_id",
        "layer": "leaf",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_parse_skill_obligations",
        "required_value": "non_empty_string",
        "unlocks": "skill_standard_obligation_binding",
    },
    {
        "field": "preplanning.skill_standard.obligations[].skill",
        "logical_field": "skill_standard_obligation_skill",
        "layer": "leaf",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_parse_skill_obligations",
        "required_value": "non_empty_string",
        "unlocks": "skill_standard_obligation_binding",
    },
    {
        "field": "preplanning.skill_standard.obligations[].classification",
        "logical_field": "skill_standard_obligation_classification",
        "layer": "leaf",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_parse_skill_obligations",
        "required_value": "non_empty_string",
        "unlocks": "skill_standard_obligation_binding",
    },
    {
        "field": "preplanning.skill_standard.obligations[].role_use",
        "logical_field": "skill_standard_obligation_role_use",
        "layer": "leaf",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_parse_skill_obligations",
        "required_value": "non_empty_string",
        "unlocks": "skill_standard_obligation_binding",
    },
    {
        "field": "preplanning.skill_standard.obligations[].use_context",
        "logical_field": "skill_standard_obligation_use_context",
        "layer": "leaf",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_parse_skill_obligations",
        "required_value": "non_empty_string",
        "unlocks": "skill_standard_obligation_binding",
    },
    {
        "field": "preplanning.skill_standard.obligations[].evidence_rule",
        "logical_field": "skill_standard_obligation_evidence_rule",
        "layer": "leaf",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_parse_skill_obligations",
        "required_value": "non_empty_string",
        "unlocks": "skill_standard_obligation_binding",
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
        "field": "packet_result_contract.review.required_fields",
        "logical_field": "review_packet_result_required_fields",
        "layer": "middle",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_json_payload_contract_check",
        "required_value": "same_fields_as_reviewer_review_report_contract",
        "unlocks": "review_report_can_enter_quality_gate",
    },
    {
        "field": "packet_result.review.blockers[]",
        "logical_field": "review_packet_result_blockers",
        "layer": "leaf",
        "owner": "human_like_reviewer",
        "status": "reviewer_quality_owned",
        "validator": "_json_payload_contract_check",
        "required_value": "explicit_array_of_current_stage_fixed_blocker_classes",
        "unlocks": "reviewer_quality_review_after_runtime_mechanics",
    },
    {
        "field": "packet_result.review.passed",
        "logical_field": "review_packet_result_passed",
        "layer": "leaf",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_strict_packet_outcome_contract_violation",
        "required_value": "boolean_passed_current_report_outcome",
        "unlocks": "review_pass_or_block_outcome",
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
        "field": "flowguard_packet.subject_stage_evidence_matrix",
        "logical_field": "flowguard_subject_stage_evidence_matrix",
        "layer": "middle",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_ensure_flowguard_packet_for_task_result",
        "required_value": "current_subject_packet_stage_evidence_row",
        "unlocks": "flowguard_checks_current_stage_without_premature_future_evidence",
    },
    {
        "field": "review_packet.subject_stage_evidence_matrix",
        "logical_field": "review_subject_stage_evidence_matrix",
        "layer": "middle",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_ensure_review_packet_for_task_result",
        "required_value": "current_subject_packet_stage_evidence_row",
        "unlocks": "reviewer_checks_current_stage_without_premature_future_evidence",
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
        "field": "packet_result_contract.flowguard_check.required_fields",
        "logical_field": "flowguard_packet_result_required_fields",
        "layer": "middle",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_json_payload_contract_check",
        "required_value": "same_fields_as_flowguard_operator_model_report_contract",
        "unlocks": "flowguard_report_can_enter_process_gate",
    },
    {
        "field": "packet_result.flowguard_check.passed",
        "logical_field": "flowguard_packet_result_passed",
        "layer": "leaf",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_flowguard_current_report_violation",
        "required_value": "boolean_passed_current_report_outcome_consistent_with_hard_evidence",
        "unlocks": "flowguard_pass_or_block_outcome",
    },
    {
        "field": "packet_result.flowguard_check.modeled_boundary",
        "logical_field": "flowguard_report_modeled_boundary",
        "layer": "leaf",
        "owner": "flowguard_operator",
        "status": "flowguard_process_owned",
        "validator": "_json_payload_contract_check",
        "required_value": "current_subject_boundary_summary",
        "unlocks": "pm_process_disposition_with_modeled_scope",
    },
    {
        "field": "packet_result.flowguard_check.blockers[]",
        "logical_field": "flowguard_report_blockers",
        "layer": "leaf",
        "owner": "flowguard_operator",
        "status": "flowguard_process_owned",
        "validator": "_json_payload_contract_check",
        "required_value": "explicit_array_of_current_stage_fixed_blocker_classes",
        "unlocks": "flowguard_block_or_reissue_before_reviewer",
    },
    {
        "field": "packet_result.flowguard_check.contract_self_check",
        "logical_field": "flowguard_report_contract_self_check",
        "layer": "leaf",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_json_payload_contract_check",
        "required_value": "current_contract_self_check_object",
        "unlocks": "flowguard_report_can_enter_process_gate",
    },
    {
        "field": "flowguard_evidence.json.model_test_alignment_report.decision",
        "logical_field": "flowguard_evidence_file_hard_decision",
        "layer": "leaf",
        "owner": "flowguard_operator",
        "status": "flowguard_process_owned",
        "validator": "_flowguard_packet_artifact_hard_decision",
        "required_value": "pass_or_block_current_model_evidence",
        "unlocks": "flowguard_pass_or_block_outcome",
    },
    {
        "field": "flowguard_work_order.decision",
        "logical_field": "flowguard_work_order_decision",
        "layer": "middle",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_record_flowguard_from_packet_result",
        "required_value": "derived_after_current_flowguard_report_and_evidence_file",
        "unlocks": "matching_flowguard_report_for_review",
    },
    {
        "field": "flowguard_evidence_manifest.entries[].flowguard_result_id",
        "logical_field": "review_packet_flowguard_manifest_result_id",
        "layer": "middle",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "_flowguard_evidence_reads_for_review",
        "required_value": "accepted_consistent_flowguard_pass_result_id",
        "unlocks": "reviewer_quality_gate",
    },
    {
        "field": "packet_result.flowguard_check.missing_test_kinds",
        "logical_field": "flowguard_packet_result_missing_test_kinds",
        "layer": "leaf",
        "owner": "flowguard_operator",
        "status": "flowguard_process_owned",
        "validator": "_json_payload_contract_check",
        "required_value": "explicit_array",
        "unlocks": "pm_process_disposition_with_test_gap_visibility",
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
    {
        "field": "pending_action.last_wait_reminder_at",
        "logical_field": "compact_wait_reminder_time",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_apply_wait_target_reminder_receipt",
        "validator_path": "skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_effects.py",
        "required_value": "current_matching_reminder_delivery_time",
        "unlocks": "wait_liveness_without_copied_reminder_history",
    },
    {
        "field": "pending_action.last_wait_reminder_sha256",
        "logical_field": "compact_wait_reminder_identity",
        "layer": "leaf",
        "owner": "flowpilot_router",
        "status": "mechanical_runtime_owned",
        "validator": "_apply_wait_target_reminder_receipt",
        "validator_path": "skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_effects.py",
        "required_value": "current_matching_reminder_sha256",
        "unlocks": "idempotent_wait_reminder_reconciliation",
    },
    {
        "field": "daemon_result.tick_count",
        "logical_field": "bounded_daemon_tick_count",
        "layer": "leaf",
        "owner": "flowpilot_router_daemon",
        "status": "mechanical_runtime_owned",
        "validator": "run_router_daemon",
        "validator_path": "skills/flowpilot/assets/flowpilot_router_daemon_runtime.py",
        "required_value": "aggregate_count_without_tick_body_array",
        "unlocks": "bounded_daemon_terminal_evidence",
    },
    {
        "field": "daemon_result.anomalies[]",
        "logical_field": "bounded_daemon_anomaly_sample",
        "layer": "leaf",
        "owner": "flowpilot_router_daemon",
        "status": "mechanical_runtime_owned",
        "validator": "_compact_router_daemon_tick",
        "validator_path": "skills/flowpilot/assets/flowpilot_router_daemon_runtime.py",
        "required_value": "at_most_router_daemon_anomaly_sample_limit",
        "unlocks": "bounded_daemon_terminal_evidence",
    },
    {
        "field": "lease.last_progress_status",
        "logical_field": "finite_progress_status",
        "layer": "middle",
        "owner": "flowpilot_core_runtime",
        "status": "mechanical_runtime_owned",
        "validator": "record_progress",
        "validator_path": "skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
        "required_value": "one_of_current_progress_statuses",
        "unlocks": "semantic_or_due_progress_liveness",
    },
    {
        "field": "background_child_meta.stdout",
        "logical_field": "v5_stdout_stream_descriptor",
        "layer": "leaf",
        "owner": "flowpilot_test_tier",
        "status": "mechanical_runtime_owned",
        "validator": "stream_descriptor",
        "validator_path": "scripts/test_tier/evidence_v5.py",
        "required_value": "path_sha256_bytes_lines",
        "unlocks": "v5_owner_result_fingerprint",
    },
    {
        "field": "background_child_meta.stderr",
        "logical_field": "v5_stderr_stream_descriptor",
        "layer": "leaf",
        "owner": "flowpilot_test_tier",
        "status": "mechanical_runtime_owned",
        "validator": "stream_descriptor",
        "validator_path": "scripts/test_tier/evidence_v5.py",
        "required_value": "path_sha256_bytes_lines",
        "unlocks": "v5_owner_result_fingerprint",
    },
    {
        "field": "background_child_meta.combined_kind",
        "logical_field": "bounded_combined_terminal_index_kind",
        "layer": "leaf",
        "owner": "flowpilot_test_tier",
        "status": "mechanical_runtime_owned",
        "validator": "terminal_stream_index_bytes",
        "validator_path": "scripts/test_tier/evidence_v5.py",
        "required_value": "terminal_stream_index",
        "unlocks": "bounded_human_readable_validation_index",
    },
    {
        "field": "acceptance_testmesh_evidence_manifest.owners[].proof_ref",
        "logical_field": "v5_owner_proof_reference",
        "layer": "middle",
        "owner": "flowpilot_test_tier",
        "status": "mechanical_runtime_owned",
        "validator": "validate_owner_reference",
        "validator_path": "scripts/test_tier/impact_resolution.py",
        "required_value": "exact_current_owner_meta_path_sha_and_result_fingerprint",
        "unlocks": "v5_owner_reuse_or_execution_evidence",
    },
    {
        "field": "runtime_retention_plan.plan_id",
        "logical_field": "frozen_retention_plan_identity",
        "layer": "middle",
        "owner": "flowpilot_runtime_retention",
        "status": "mechanical_runtime_owned",
        "validator": "build_plan",
        "validator_path": "scripts/flowpilot_runtime_retention.py",
        "required_value": "content_derived_current_plan_identity",
        "unlocks": "explicit_retention_apply_authorization",
    },
    {
        "field": "runtime_retention_apply.plan_sha256",
        "logical_field": "retention_apply_plan_hash_binding",
        "layer": "middle",
        "owner": "flowpilot_runtime_retention",
        "status": "mechanical_runtime_owned",
        "validator": "apply_plan",
        "validator_path": "scripts/flowpilot_runtime_retention.py",
        "required_value": "exact_supplied_frozen_plan_sha256",
        "unlocks": "current_candidate_revalidation_and_archive_creation",
    },
    {
        "field": "run_index.runs[].archive_sha256",
        "logical_field": "verified_retention_archive_identity",
        "layer": "middle",
        "owner": "flowpilot_runtime_retention",
        "status": "mechanical_runtime_owned",
        "validator": "_create_verified_archive",
        "validator_path": "scripts/flowpilot_runtime_retention.py",
        "required_value": "readback_verified_archive_sha256",
        "unlocks": "archive_index_commit_before_heavy_path_cleanup",
    },
    {
        "field": "run_index.runs[].archive_cleanup_status",
        "logical_field": "retention_cleanup_terminal_disposition",
        "layer": "middle",
        "owner": "flowpilot_runtime_retention",
        "status": "mechanical_runtime_owned",
        "validator": "_mark_cleanup",
        "validator_path": "scripts/flowpilot_runtime_retention.py",
        "required_value": "pending_complete_or_incomplete_with_errors",
        "unlocks": "honest_retention_completion_claim",
    },
)
REQUIRED_CURRENT_FIELD_CONTRACT_COUNT = len(CURRENT_FIELD_CONTRACTS)

FIELD_LIFECYCLE_CHAINS = (
    {
        "chain_id": "repair_blocker_identity_recheck_chain",
        "source": "active_blocker.blocker_id",
        "field_sequence": (
            "packet.repair_blocker_id",
            "packet.envelope.repair_blocker_id",
            "current_handoff_contract.input_material_manifest.blocker_id",
            "flowguard_evidence.generator_inputs.blocker_id",
            "flowguard_evidence.subject_context.blocker_id",
            "flowguard_result.blocker_id",
            "flowguard_evidence_manifest.entries[].blocker_id",
            "review_packet.repair_blocker_id",
        ),
        "mechanical_gate": "_formal_repair_identity_blockers",
        "human_quality_gate": "_record_review_from_packet_result",
        "terminal_disposition": "active_blocker.status",
        "no_prose_authority": True,
        "no_reviewer_mechanical_field_check": True,
    },
    {
        "chain_id": "sealed_body_authorized_material_lifecycle_chain",
        "source": "active_blocker.result_id",
        "field_sequence": (
            "current_handoff_contract.input_material_manifest.authorized_result_reads[]",
            "current_handoff_contract.input_material_manifest.authorized_result_read_ids",
            "current_handoff_contract.input_material_manifest.required_authorized_read_count",
            "current_handoff_contract.input_material_manifest.all_required_authorized_result_bodies_must_be_opened_before_submit",
            "current_handoff_contract.input_material_manifest.packet_body_opened_by_assigned_role_via_open_packet",
            "runtime.open_authorized_input_materials_for_role",
            "runtime._required_authorized_result_read_blockers",
        ),
        "mechanical_gate": "_required_authorized_result_read_blockers",
        "human_quality_gate": "assigned_role_current_packet_result",
        "terminal_disposition": "packet_result.status",
        "no_prose_authority": True,
        "no_reviewer_mechanical_field_check": True,
    },
    {
        "chain_id": "stage_evidence_matrix_packet_lifecycle_chain",
        "source": "packet_result_contracts.PACKET_RESULT_CONTRACTS[].family_id",
        "field_sequence": (
            "packet_stage_evidence_matrix.PACKET_STAGE_EVIDENCE_MATRIX_BY_FAMILY",
            "current_handoff_contract.stage_evidence_matrix.family_id",
            "current_handoff_contract.stage_evidence_matrix.lifecycle_stage",
            "current_handoff_contract.stage_evidence_matrix.current_required_fields",
            "current_handoff_contract.required_report_contract.stage_evidence_matrix",
            "flowguard_packet.subject_stage_evidence_matrix",
            "review_packet.subject_stage_evidence_matrix",
        ),
        "mechanical_gate": "_packet_stage_evidence_row + _build_current_handoff_contract",
        "human_quality_gate": "_ensure_flowguard_packet_for_task_result + _ensure_review_packet_for_task_result",
        "terminal_disposition": "current_stage_evidence_timing",
        "no_prose_authority": True,
        "no_reviewer_mechanical_field_check": True,
    },
    {
        "chain_id": "portable_runtime_self_check_receipt_chain",
        "source": "installed_flowpilot_skill_assets",
        "field_sequence": (
            "flowpilot_runtime_self_check.REQUIRED_RUNTIME_ASSETS",
            "flowpilot_runtime_self_check_receipt.ok",
            "flowpilot_runtime_self_check_receipt.dev_repo_simulations_required",
            "flowpilot_runtime_self_check_receipt.required_runtime_assets[]",
            "run_root.runtime.flowpilot_runtime_self_check_receipt.json",
            "ledger.flowpilot_runtime_self_check",
        ),
        "mechanical_gate": "flowpilot_runtime_self_check.runtime_self_check",
        "human_quality_gate": "start_run",
        "terminal_disposition": "run_start_allowed_or_blocked",
        "no_prose_authority": True,
        "no_reviewer_mechanical_field_check": True,
    },
    {
        "chain_id": "flowguard_reissue_authorized_material_inheritance_chain",
        "source": "source_flowguard_packet.envelope.authorized_result_reads[]",
        "field_sequence": (
            "source_flowguard_packet.envelope.authorized_result_reads[]",
            "source_flowguard_packet.current_handoff_contract.input_material_manifest.required_authorized_reads_before_submit",
            "runtime._flowguard_reissue_inherited_authorized_result_reads",
            "flowguard_reissue_packet.envelope.authorized_result_reads[]",
            "flowguard_reissue_packet.body.authorized_result_reads[]",
            "flowguard_reissue_packet.current_handoff_contract.input_material_manifest.required_authorized_reads_before_submit",
            "runtime.open_authorized_input_materials_for_role",
            "runtime._required_authorized_result_read_blockers",
        ),
        "mechanical_gate": "_flowguard_reissue_inherited_authorized_result_reads + _required_authorized_result_read_blockers",
        "human_quality_gate": "_flowguard_semantic_recheck_contract_violation",
        "terminal_disposition": "flowguard_reissue_result.status",
        "no_prose_authority": True,
        "no_reviewer_mechanical_field_check": True,
    },
    {
        "chain_id": "pm_repair_evidence_obligation_lifecycle_chain",
        "source": "active_blocker.missing_required_fields",
        "field_sequence": (
            "pm_repair_packet.repair_evidence_obligations[]",
            "pm_repair_packet.repair_evidence_obligations[].obligation_id",
            "pm_repair_packet.repair_evidence_obligations[].source_blocker_id",
            "pm_repair_packet.repair_evidence_obligations[].evidence_kind",
            "pm_repair_result.repair_obligation_disposition[]",
            "pm_repair_result.repair_obligation_disposition[].obligation_id",
            "pm_repair_result.repair_obligation_disposition[].disposition",
            "repair_packet.repair_obligation_context",
            "flowguard_packet.envelope.result_contract_profile_ids[]",
            "flowguard_packet.envelope.result_contract_profile_bindings.flowguard.semantic_recheck_required",
            "flowguard.semantic_recheck.consumed_repair_obligation_ids",
        ),
        "mechanical_gate": "_pm_repair_obligation_disposition_violation",
        "human_quality_gate": "_flowguard_semantic_recheck_contract_violation",
        "terminal_disposition": "active_blocker.status",
        "no_prose_authority": True,
        "no_reviewer_mechanical_field_check": True,
    },
    {
        "chain_id": "role_report_packet_result_contract_chain",
        "source": "role_output_contract.required_body_fields",
        "field_sequence": (
            "contract_index.reviewer_review_report.required_body_fields",
            "packet_result_contract.review.required_fields",
            "packet_result_contract.review.required_child_fields",
            "packet_result_contract.review.explicit_array_fields",
            "contract_index.flowguard_operator_model_report.required_body_fields",
            "packet_result_contract.flowguard_check.required_fields",
            "packet_result_contract.flowguard_check.explicit_array_fields",
            "runtime._json_payload_contract_check",
            "runtime._strict_packet_outcome_contract_violation",
            "fake_e2e.current_report_success_body",
        ),
        "mechanical_gate": "_json_payload_contract_check",
        "human_quality_gate": "_record_review_from_packet_result",
        "terminal_disposition": "packet_result.status",
        "no_prose_authority": True,
        "no_reviewer_mechanical_field_check": True,
    },
    {
        "chain_id": "flowguard_current_evidence_file_to_reviewer_handoff_chain",
        "source": "flowguard_evidence.json.model_test_alignment_report.decision",
        "field_sequence": (
            "flowguard_evidence.json.model_test_alignment_report.decision",
            "packet_result.flowguard_check.modeled_boundary",
            "packet_result.flowguard_check.blockers[]",
            "packet_result.flowguard_check.contract_self_check",
            "packet_result.flowguard_check.passed",
            "flowguard_work_order.decision",
            "flowguard_evidence_manifest.entries[].flowguard_result_id",
        ),
        "mechanical_gate": "_flowguard_current_report_violation",
        "human_quality_gate": "_record_review_from_packet_result",
        "terminal_disposition": "packet_result.status",
        "no_prose_authority": True,
        "no_reviewer_mechanical_field_check": True,
    },
    {
        "chain_id": "packet_currentness_lifecycle_chain",
        "source": "packet.status",
        "field_sequence": (
            "packet.status",
            "packet.result_ids",
            "packet.accepted_result_id",
            "packet.latest_quarantined_result_id",
            "route_node.status",
            "execution_frontier.pending_route_mutation",
            "active_packets",
            "accepted_result_packets",
            "closure_accepted_packets",
        ),
        "mechanical_gate": "_packet_is_noncurrent_for_routing",
        "human_quality_gate": "_record_review_from_packet_result",
        "terminal_disposition": "packet.status",
        "no_prose_authority": True,
        "no_reviewer_mechanical_field_check": True,
    },
    {
        "chain_id": "derived_active_packet_projection_chain",
        "source": "_packet_is_noncurrent_for_routing",
        "field_sequence": (
            "_current_packets_for_routing",
            "render_compact_console.active_packets",
        ),
        "mechanical_gate": "_packet_is_noncurrent_for_routing",
        "human_quality_gate": "_record_review_from_packet_result",
        "terminal_disposition": "active_packets",
        "no_prose_authority": True,
        "no_reviewer_mechanical_field_check": True,
    },
    {
        "chain_id": "derived_closure_accepted_packet_projection_chain",
        "source": "_accepted_result_packets_for_active_route",
        "field_sequence": (
            "_accepted_result_packets_for_active_route",
            "_accepted_packets_for_closure_evidence",
            "accepted_packet_lease_health.accepted_result_packets",
            "attempt_final_closure.accepted_packets",
            "final_closure.backward_chain",
        ),
        "mechanical_gate": "_accepted_packets_for_closure_evidence",
        "human_quality_gate": "_record_review_from_packet_result",
        "terminal_disposition": "closure_accepted_packets",
        "no_prose_authority": True,
        "no_reviewer_mechanical_field_check": True,
    },
)
REQUIRED_FIELD_LIFECYCLE_CHAIN_COUNT = len(FIELD_LIFECYCLE_CHAINS)

PACKET_RESULT_CONTRACTS = packet_result_contracts.PACKET_RESULT_CONTRACTS
REQUIRED_PACKET_RESULT_CONTRACT_COUNT = len(PACKET_RESULT_CONTRACTS)
PACKET_STAGE_EVIDENCE_MATRIX = packet_stage_evidence_matrix.PACKET_STAGE_EVIDENCE_MATRIX
REQUIRED_PACKET_STAGE_EVIDENCE_MATRIX_COUNT = len(PACKET_STAGE_EVIDENCE_MATRIX)

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
    {
        "field": "cards/phases/pm_material_scan.md",
        "status": "retired",
        "disposition": "deleted_from_current_runtime_material_work_uses_ordinary_role_packages",
    },
    {
        "field": "cards/reviewer/material_sufficiency.md",
        "status": "retired",
        "disposition": "deleted_from_current_runtime_material_work_uses_existing_review_windows",
    },
    {
        "field": "cards/phases/pm_material_absorb_or_research.md",
        "status": "retired",
        "disposition": "deleted_from_current_runtime_pm_routes_reading_or_research_as_ordinary_work",
    },
    {
        "field": "cards/phases/pm_material_understanding.md",
        "status": "retired",
        "disposition": "deleted_from_current_runtime_no_special_material_form_or_gate",
    },
)

FORBIDDEN_LEGACY_FIELD_CONTRACTS = (
    {
        "field": "controller_action.seen_count",
        "status": "forbidden_legacy",
        "disposition": "observation_liveness_belongs_to_bounded_daemon_status",
    },
    {
        "field": "controller_action.last_seen_at",
        "status": "forbidden_legacy",
        "disposition": "semantic_updated_at_and_receipt_identity_are_current_authority",
    },
    {
        "field": "router_state.wait_reminder_history[]",
        "status": "forbidden_legacy",
        "disposition": "current_wait_receipt_and_compact_reminder_state_are_single_authority",
    },
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
    {
        "field": "preplanning.skill_standard.default_required_obligation",
        "status": "forbidden_legacy",
        "disposition": "reject_as_missing_current_obligations",
    },
    {
        "field": "preplanning.skill_standard.selected_skills",
        "status": "forbidden_legacy",
        "disposition": "reject_as_old_skill_standard_shape",
    },
    {
        "field": "preplanning.high_standard_contract.decision",
        "status": "forbidden_legacy",
        "disposition": "reject_as_hidden_generic_decision_wrapper",
    },
    {
        "field": "preplanning.high_standard_contract.contract_rows",
        "status": "forbidden_legacy",
        "disposition": "reject_as_old_contract_row_wrapper",
    },
    {
        "field": "pm_repair_decision.authority",
        "status": "forbidden_legacy",
        "disposition": "reject_as_authority_ref_alias",
    },
    {
        "field": "pm_disposition.summary",
        "status": "forbidden_legacy",
        "disposition": "reject_as_reason_alias",
    },
    {
        "field": "research_packet_spec.recipient_role",
        "status": "forbidden_legacy",
        "disposition": "reject_as_to_role_alias",
    },
    {
        "field": "current_role_agent_binding.host_liveness_status",
        "status": "forbidden_legacy",
        "disposition": "replaced_by_responsibility_lease_ack_and_progress_evidence",
    },
    {
        "field": "role_binding_ledger.role_slots[].host_liveness_status",
        "status": "forbidden_legacy",
        "disposition": "replaced_by_responsibility_lease_ack_and_progress_evidence",
    },
    {
        "field": "role_binding_memory.current_role_agent_binding.host_liveness_status",
        "status": "forbidden_legacy",
        "disposition": "replaced_by_responsibility_lease_ack_and_progress_evidence",
    },
    {
        "field": "current_role_agent_binding.liveness_decision",
        "status": "forbidden_legacy",
        "disposition": "replaced_by_current_run_binding_decision",
    },
    {
        "field": "role_binding_ledger.role_slots[].liveness_decision",
        "status": "forbidden_legacy",
        "disposition": "replaced_by_current_run_binding_decision",
    },
    {
        "field": "responsibility_lease.liveness_status",
        "status": "forbidden_legacy",
        "disposition": "deleted_current_wait_authority",
    },
    {
        "field": "responsibility_lease.last_liveness_status",
        "status": "forbidden_legacy",
        "disposition": "deleted_current_wait_authority",
    },
    {
        "field": "responsibility_lease.liveness_checked_at",
        "status": "forbidden_legacy",
        "disposition": "deleted_current_wait_authority",
    },
    {
        "field": "responsibility_lease.host_liveness_history",
        "status": "forbidden_legacy",
        "disposition": "deleted_current_wait_authority",
    },
    {
        "field": "runtime.host_liveness_reports",
        "status": "forbidden_legacy",
        "disposition": "deleted_current_wait_authority",
    },
    {
        "field": "lifecycle_guard_config.ack_blocker_seconds",
        "status": "forbidden_legacy",
        "disposition": "replaced_by_ack_replace_seconds",
    },
    {
        "field": "lifecycle_guard_config.result_liveness_seconds",
        "status": "forbidden_legacy",
        "disposition": "replaced_by_progress_reminder_seconds",
    },
    {
        "field": "lifecycle_guard_config.progress_grace_seconds",
        "status": "forbidden_legacy",
        "disposition": "replaced_by_progress_replace_seconds",
    },
    {
        "field": "preplanning.discovery.material_sources",
        "status": "forbidden_legacy",
        "disposition": "reject_material_discovery_field_use_ordinary_role_work_and_current_evidence_refs",
    },
    {
        "field": "preplanning.discovery.material_sufficiency",
        "status": "forbidden_legacy",
        "disposition": "reject_special_material_sufficiency_gate_use_existing_reviewer_quality_gate",
    },
    {
        "field": "preplanning.discovery.material_current",
        "status": "forbidden_legacy",
        "disposition": "reject_material_specific_currency_flag_use_evidence_owned_freshness_checks",
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
        "preplanning.skill_standard.default_required_obligation",
        "preplanning.skill_standard.selected_skills",
        "preplanning.high_standard_contract.decision",
        "preplanning.high_standard_contract.contract_rows",
        "pm_repair_decision.authority",
        "pm_disposition.summary",
        "preplanning.discovery.material_sources",
        "preplanning.discovery.material_sufficiency",
        "preplanning.discovery.material_current",
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
    field_lifecycle_chains_cataloged: int = 0
    legacy_dispositions_cataloged: bool = False
    startup_answers_validated: bool = False
    packet_scope_filtered_to_current_options: bool = False
    top_level_runtime_fields_bound: bool = False
    startup_mechanical_field_audit_written: bool = False
    packet_role_runtime_fields_bound: bool = False
    runtime_leaf_mechanical_fields_bound: bool = False
    formal_repair_identity_chain_bound: bool = False
    formal_repair_identity_mechanical_gate_bound: bool = False
    pm_decision_fields_bound: bool = False
    reviewer_quality_fields_bound: bool = False
    flowguard_process_fields_bound: bool = False
    current_background_agent_fields_bound: bool = False
    packet_result_contracts_cataloged: int = 0
    unsupported_historical_field_seen: bool = False
    unsupported_historical_field_accepted: bool = False
    unsupported_historical_field_translated: bool = False
    background_ack_missing: bool = False
    provenance_leaked_to_controller_scope: bool = False
    startup_fixed_role_binding_gate_required: bool = False
    fixed_role_count_gate_required: bool = False
    legacy_boot_action_accepted: bool = False
    packet_result_contract_misaligned: bool = False
    repair_identity_prose_only: bool = False
    repair_identity_chain_misaligned: bool = False
    repair_identity_reviewer_owned: bool = False
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
    if scenario == PACKET_RESULT_CONTRACT_MISALIGNED:
        return replace(base, packet_result_contract_misaligned=True)
    if scenario == REPAIR_IDENTITY_PROSE_ONLY:
        return replace(base, repair_identity_prose_only=True)
    if scenario == REPAIR_IDENTITY_CHAIN_MISALIGNED:
        return replace(base, repair_identity_chain_misaligned=True)
    if scenario == REPAIR_IDENTITY_REVIEWER_OWNED:
        return replace(base, repair_identity_reviewer_owned=True)
    raise ValueError(f"unknown scenario: {scenario}")


def field_contract_ready(state: State) -> bool:
    return (
        state.status == "running"
        and state.current_field_contracts_cataloged == REQUIRED_CURRENT_FIELD_CONTRACT_COUNT
        and state.field_statuses_cataloged == len(FIELD_STATUSES)
        and state.field_lifecycle_chains_cataloged == REQUIRED_FIELD_LIFECYCLE_CHAIN_COUNT
        and state.legacy_dispositions_cataloged
        and state.startup_answers_validated
        and state.packet_scope_filtered_to_current_options
        and state.top_level_runtime_fields_bound
        and state.startup_mechanical_field_audit_written
        and state.packet_role_runtime_fields_bound
        and state.runtime_leaf_mechanical_fields_bound
        and state.formal_repair_identity_chain_bound
        and state.formal_repair_identity_mechanical_gate_bound
        and state.pm_decision_fields_bound
        and state.reviewer_quality_fields_bound
        and state.flowguard_process_fields_bound
        and state.current_background_agent_fields_bound
        and state.packet_result_contracts_cataloged == REQUIRED_PACKET_RESULT_CONTRACT_COUNT
        and not state.unsupported_historical_field_accepted
        and not state.unsupported_historical_field_translated
        and not state.background_ack_missing
        and not state.provenance_leaked_to_controller_scope
        and not state.startup_fixed_role_binding_gate_required
        and not state.fixed_role_count_gate_required
        and not state.legacy_boot_action_accepted
        and not state.packet_result_contract_misaligned
        and not state.repair_identity_prose_only
        and not state.repair_identity_chain_misaligned
        and not state.repair_identity_reviewer_owned
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
    if state.packet_result_contract_misaligned:
        return "block_packet_result_contract_misaligned"
    if state.repair_identity_prose_only:
        return "block_repair_identity_prose_only"
    if state.repair_identity_chain_misaligned:
        return "block_repair_identity_chain_misaligned"
    if state.repair_identity_reviewer_owned:
        return "block_repair_identity_reviewer_owned"
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
    if state.field_lifecycle_chains_cataloged != REQUIRED_FIELD_LIFECYCLE_CHAIN_COUNT:
        yield Transition(
            "catalog_field_lifecycle_chains",
            replace(state, field_lifecycle_chains_cataloged=REQUIRED_FIELD_LIFECYCLE_CHAIN_COUNT),
        )
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
    if not state.formal_repair_identity_chain_bound:
        yield Transition(
            "bind_formal_repair_identity_chain",
            replace(state, formal_repair_identity_chain_bound=True),
        )
        return
    if not state.formal_repair_identity_mechanical_gate_bound:
        yield Transition(
            "bind_runtime_repair_identity_mechanical_gate",
            replace(state, formal_repair_identity_mechanical_gate_bound=True),
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
    if state.packet_result_contracts_cataloged != REQUIRED_PACKET_RESULT_CONTRACT_COUNT:
        yield Transition(
            "catalog_packet_result_family_contracts",
            replace(state, packet_result_contracts_cataloged=REQUIRED_PACKET_RESULT_CONTRACT_COUNT),
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
MAX_SEQUENCE_LENGTH = 21


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
        "packet_result_contracts",
        "field_lifecycle_chains",
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
