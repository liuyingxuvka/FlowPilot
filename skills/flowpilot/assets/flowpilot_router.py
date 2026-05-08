"""Prompt-isolated FlowPilot router.

This module is the new FlowPilot control entrypoint. It is deliberately small:
it reads the current run state, returns one JSON action envelope, and verifies
that every bootloader/controller action was first authorized by the router.

The router is not a project manager. It does not decide whether evidence is
sufficient, whether a route is good, or whether a worker succeeded. It only
decides which system card or packet-delivery gate is currently allowed.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import flowpilot_user_flow_diagram
import packet_runtime


SCHEMA_VERSION = "flowpilot.router.v1"
BOOTSTRAP_STATE_SCHEMA = "flowpilot.bootstrap_state.v1"
RUN_STATE_SCHEMA = "flowpilot.run_state.v1"
PROMPT_MANIFEST_SCHEMA = "flowpilot.prompt_manifest.v1"
PACKET_LEDGER_SCHEMA = packet_runtime.PACKET_LEDGER_SCHEMA
RESUME_EVIDENCE_SCHEMA = "flowpilot.resume_reentry.v1"
ROUTE_HISTORY_INDEX_SCHEMA = "flowpilot.route_history_index.v1"
PM_PRIOR_PATH_CONTEXT_SCHEMA = "flowpilot.pm_prior_path_context.v1"
DISPLAY_PLAN_SCHEMA = "flowpilot.display_plan.v1"
ROUTE_STATE_SNAPSHOT_SCHEMA = "flowpilot.route_state_snapshot.v1"
CONTROL_BLOCKER_SCHEMA = "flowpilot.control_blocker.v1"
CONTROL_BLOCKER_REPAIR_PACKET_SCHEMA = "flowpilot.control_blocker_repair_packet.v1"
REPAIR_TRANSACTION_SCHEMA = "flowpilot.repair_transaction.v1"
REPAIR_TRANSACTION_INDEX_SCHEMA = "flowpilot.repair_transaction_index.v1"
ROLE_OUTPUT_ENVELOPE_SCHEMA = "flowpilot.role_output_envelope.v1"
LIVE_CARD_CONTEXT_SCHEMA = "flowpilot.live_card_context.v1"
PAYLOAD_CONTRACT_SCHEMA = "flowpilot.payload_contract.v1"
GATE_DECISION_SCHEMA = "flowpilot.gate_decision.v1"
GATE_DECISION_RECORD_SCHEMA = "flowpilot.gate_decision_record.v1"
GATE_DECISION_LEDGER_SCHEMA = "flowpilot.gate_decision_ledger.v1"
PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT = "pm_records_control_blocker_repair_decision"
PM_MODEL_MISS_TRIAGE_DECISION_EVENT = "pm_records_model_miss_triage_decision"
GATE_DECISION_EVENT = "role_records_gate_decision"
DISPLAY_CONFIRMATION_SCHEMA = "flowpilot.user_dialog_display_confirmation.v1"
DISPLAY_SURFACE_RECEIPT_SCHEMA = "flowpilot.display_surface_receipt.v1"
STARTUP_MECHANICAL_AUDIT_SCHEMA = "flowpilot.startup_mechanical_audit.v1"
ROUTER_OWNED_CHECK_PROOF_SCHEMA = "flowpilot.router_owned_check_proof.v1"
STARTUP_ANSWER_PROVENANCE = "explicit_user_reply"
STARTUP_ANSWER_INTERPRETATION_PROVENANCE = "ai_interpreted_from_explicit_user_reply"
STARTUP_ANSWER_INTERPRETATION_SCHEMA = "flowpilot.startup_answer_interpretation.v1"
USER_REQUEST_PROVENANCE = "explicit_user_request"
DISPLAY_CONFIRMATION_PROVENANCE = "controller_user_dialog_render"
DISPLAY_CONFIRMATION_TARGET = "user_dialog"
ROUTER_TRUSTED_PROOF_SOURCES = {"router_computed", "packet_runtime_hash", "host_receipt"}
ROLE_AGENT_SPAWN_RESULT = "spawned_fresh_for_task"
ROLE_AGENT_REHYDRATION_RESULT = "rehydrated_from_current_run_memory"
ROLE_AGENT_CONTINUITY_RESULT = "live_agent_continuity_confirmed"
RESUME_ROLE_AGENT_RESULTS = {ROLE_AGENT_REHYDRATION_RESULT, ROLE_AGENT_CONTINUITY_RESULT}
ROLE_AGENT_HOST_LIVENESS_STATUSES = {"active", "completed", "missing", "cancelled", "timeout_unknown", "unknown"}
ROLE_AGENT_BOUNDED_WAIT_RESULTS = {"not_waited", "completed", "timeout_unknown"}
ROLE_AGENT_LIVENESS_DECISIONS = {"confirmed_existing_agent", "spawned_replacement_from_current_run_memory"}
CONTROL_BLOCKER_LANES = {
    "control_plane_reissue",
    "pm_repair_decision_required",
    "fatal_protocol_violation",
}
PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES = {
    "pm_repair_decision_required",
    "fatal_protocol_violation",
}
PM_MODEL_MISS_TRIAGE_DECISION_ALLOWED_VALUES = {
    "request_officer_model_miss_analysis",
    "proceed_with_model_backed_repair",
    "out_of_scope_not_modelable",
    "needs_evidence_before_modeling",
    "stop_for_user",
}
PM_MODEL_MISS_TRIAGE_REPAIR_AUTHORIZED_VALUES = {
    "proceed_with_model_backed_repair",
    "out_of_scope_not_modelable",
}
PM_MODEL_MISS_TRIAGE_REQUIRED_BODY_FIELDS = (
    "decided_by_role",
    "decision",
    "defect_or_blocker_id",
    "reviewer_block_source_path",
    "model_miss_scope",
    "flowguard_capability",
    "same_class_findings_reviewed",
    "repair_recommendation_reviewed",
    "selected_next_action",
    "why_repair_may_start",
    "blockers",
    "contract_self_check",
)
MODEL_MISS_OFFICER_REPORT_REQUIRED_FIELDS = (
    "old_model_miss_reason",
    "bug_class_definition",
    "same_class_findings",
    "coverage_added",
    "candidate_repairs",
    "minimal_sufficient_repair_recommendation",
    "rejected_larger_repairs",
    "rejected_smaller_repairs",
    "post_repair_model_checks_required",
    "residual_blindspots",
    "contract_self_check",
)
STARTUP_ANSWER_ENUMS = {
    "background_agents": {"allow", "single-agent"},
    "scheduled_continuation": {"allow", "manual"},
    "display_surface": {"cockpit", "chat"},
}
GATE_DECISION_REQUIRED_FIELDS = (
    "gate_decision_version",
    "gate_id",
    "gate_kind",
    "owner_role",
    "risk_type",
    "gate_strength",
    "decision",
    "blocking",
    "required_evidence",
    "evidence_refs",
    "reason",
    "next_action",
    "contract_self_check",
)
PM_PRIOR_PATH_CONTEXT_REVIEW_REQUIRED_FIELDS = (
    "reviewed",
    "source_paths",
    "completed_nodes_considered",
    "superseded_nodes_considered",
    "stale_evidence_considered",
    "prior_blocks_or_experiments_considered",
    "impact_on_decision",
    "controller_summary_used_as_evidence",
)
PM_RESUME_CONTROLLER_REMINDER_REQUIRED_FIELDS = (
    "controller_only",
    "controller_may_read_sealed_bodies",
    "controller_may_infer_from_chat_history",
    "controller_may_advance_or_close_route",
)
PM_RESUME_DECISION_ALLOWED_VALUES = {
    "continue_current_packet_loop",
    "request_sender_reissue",
    "restore_or_replace_roles_from_memory",
    "create_repair_or_route_mutation_node",
    "stop_for_user_or_environment",
    "close_after_final_ledger_and_terminal_replay",
}
PM_RESUME_DECISION_REQUIRED_BODY_FIELDS = (
    "decision_owner",
    "decision",
    "explicit_recovery_evidence_recorded",
    *(f"prior_path_context_review.{field}" for field in PM_PRIOR_PATH_CONTEXT_REVIEW_REQUIRED_FIELDS),
    *(f"controller_reminder.{field}" for field in PM_RESUME_CONTROLLER_REMINDER_REQUIRED_FIELDS),
)
PM_PARENT_SEGMENT_DECISION_ALLOWED_VALUES = {
    "continue",
    "repair_existing_child",
    "add_sibling_child",
    "rebuild_child_subtree",
    "bubble_to_parent",
    "pm_stop",
}
PM_PARENT_SEGMENT_DECISION_REQUIRED_BODY_FIELDS = (
    "decision_owner",
    "decision",
    *(f"prior_path_context_review.{field}" for field in PM_PRIOR_PATH_CONTEXT_REVIEW_REQUIRED_FIELDS),
)
PM_TERMINAL_CLOSURE_DECISION_ALLOWED_VALUES = {
    "approve_terminal_closure",
}
PM_TERMINAL_CLOSURE_DECISION_REQUIRED_BODY_FIELDS = (
    "approved_by_role",
    "decision",
    *(f"prior_path_context_review.{field}" for field in PM_PRIOR_PATH_CONTEXT_REVIEW_REQUIRED_FIELDS),
)
GATE_DECISION_ALLOWED_KINDS = {
    "quality",
    "repair",
    "parent_replay",
    "resource",
    "stage_advance",
    "completion",
    "other",
}
GATE_DECISION_ALLOWED_OWNER_ROLES = {
    "project_manager",
    "human_like_reviewer",
    "process_flowguard_officer",
    "product_flowguard_officer",
}
GATE_DECISION_ALLOWED_RISKS = {
    "product_state",
    "visual_quality",
    "mixed_product_visual",
    "documentation_only",
    "composition",
    "resource",
    "control_state",
    "none",
}
GATE_DECISION_ALLOWED_STRENGTHS = {
    "hard",
    "soft",
    "advisory",
    "skip_with_reason",
}
GATE_DECISION_ALLOWED_DECISIONS = {
    "pass",
    "block",
    "waive",
    "skip",
    "repair_local",
    "mutate_route",
}
GATE_DECISION_ALLOWED_EVIDENCE_KINDS = {
    "file",
    "command",
    "screenshot",
    "model_result",
    "reviewer_walkthrough",
    "state_ref",
    "none",
}
GATE_DECISION_ALLOWED_NEXT_ACTIONS = {
    "continue",
    "local_repair",
    "route_mutation",
    "collect_evidence",
    "reviewer_recheck",
    "stop",
}
GATE_DECISION_SEMANTIC_OVERREACH_FIELDS = {
    "router_approved_semantic_sufficiency",
    "router_semantic_decision",
    "router_sufficiency_decision",
    "semantic_sufficiency_passed_by_router",
    "controller_approved_gate",
}

CREW_ROLE_KEYS = (
    "project_manager",
    "human_like_reviewer",
    "process_flowguard_officer",
    "product_flowguard_officer",
    "worker_a",
    "worker_b",
)

ROLE_CARD_KEYS = ("controller", *CREW_ROLE_KEYS)

RUNTIME_FLAG_DEFAULTS = {
    "resume_state_loaded": False,
    "resume_state_ambiguous": False,
    "resume_roles_restored": False,
    "resume_role_agents_rehydrated": False,
    "crew_rehydration_report_written": False,
    "continuation_binding_recorded": False,
    "startup_mechanical_audit_written": False,
    "startup_pending_mail_suspended_after_dead_end": False,
    "startup_display_status_written": False,
    "route_history_index_refreshed": False,
    "pm_prior_path_context_refreshed": False,
    "material_scan_packets_relayed": False,
    "material_scan_results_relayed_to_reviewer": False,
    "research_packet_relayed": False,
    "research_result_relayed_to_reviewer": False,
    "current_node_packet_relayed": False,
    "current_node_result_relayed_to_reviewer": False,
    "current_node_write_grant_issued": False,
    "node_completion_ledger_updated": False,
    "task_completion_projection_published": False,
}

SAFE_RUN_UNTIL_WAIT_ACTION_TYPES = frozenset(
    {
        "load_router",
        "create_run_shell",
        "write_current_pointer",
        "update_run_index",
        "copy_runtime_kit",
        "fill_runtime_placeholders",
        "initialize_mailbox",
        "write_user_intake",
    }
)

CURRENT_NODE_CYCLE_FLAGS = (
    "pm_node_started_event_delivered",
    "pm_node_acceptance_plan_card_delivered",
    "node_acceptance_plan_written",
    "reviewer_node_acceptance_plan_card_delivered",
    "node_acceptance_plan_reviewer_passed",
    "current_node_packet_registered",
    "current_node_write_grant_issued",
    "reviewer_current_node_dispatch_card_delivered",
    "current_node_dispatch_allowed",
    "current_node_packet_relayed",
    "current_node_worker_result_returned",
    "reviewer_worker_result_card_delivered",
    "current_node_result_relayed_to_reviewer",
    "node_reviewer_passed_result",
    "node_review_blocked",
    "pm_model_miss_triage_card_delivered",
    "model_miss_triage_closed",
    "pm_review_repair_card_delivered",
    "pm_reviewer_blocked_event_delivered",
    "pm_parent_backward_targets_card_delivered",
    "parent_backward_targets_built",
    "reviewer_parent_backward_replay_card_delivered",
    "parent_backward_replay_passed",
    "pm_parent_segment_decision_card_delivered",
    "parent_segment_decision_recorded",
    "node_completed_by_pm",
    "node_completion_ledger_updated",
)

MATERIAL_REPAIR_RECHECK_FLAGS = (
    "material_scan_dispatch_recheck_blocked",
    "material_scan_dispatch_recheck_protocol_blocked",
)

MATERIAL_REPAIR_OUTCOME_EVENTS = {
    "reviewer_allows_material_scan_dispatch",
    "worker_scan_results_returned",
    "reviewer_blocks_material_scan_dispatch_recheck",
    "reviewer_protocol_blocker_material_scan_dispatch_recheck",
}

ROUTE_COMPLETION_FLAGS = (
    "pm_evidence_quality_package_card_delivered",
    "evidence_quality_package_written",
    "reviewer_evidence_quality_card_delivered",
    "evidence_quality_reviewer_passed",
    "pm_final_ledger_card_delivered",
    "final_ledger_built_clean",
    "reviewer_final_backward_replay_card_delivered",
    "final_backward_replay_passed",
    "task_completion_projection_published",
    "pm_closure_card_delivered",
    "pm_closure_approved",
)

PM_PRIOR_CONTEXT_REQUIRED_CARD_IDS = {
    "pm.prior_path_context",
    "pm.route_skeleton",
    "pm.crew_rehydration_freshness",
    "pm.resume_decision",
    "pm.current_node_loop",
    "pm.node_acceptance_plan",
    "pm.model_miss_triage",
    "pm.review_repair",
    "pm.parent_segment_decision",
    "pm.evidence_quality_package",
    "pm.final_ledger",
    "pm.closure",
}

STARTUP_QUESTIONS = (
    {
        "id": "background_agents",
        "question": "Allow the standard six live background roles, or use single-agent six-role continuity?",
    },
    {
        "id": "scheduled_continuation",
        "question": "Allow scheduled continuation/heartbeat, or use manual resume only?",
    },
    {
        "id": "display_surface",
        "question": "Open FlowPilot Cockpit when startup state is ready, or use chat route signs?",
    },
)

BOOT_ACTIONS: tuple[dict[str, Any], ...] = (
    {
        "action_type": "ask_startup_questions",
        "flag": "startup_questions_asked",
        "label": "startup_questions_asked_from_router",
        "summary": "Ask the three FlowPilot startup questions, atomically record the waiting/stop boundary, and do not continue work in the same assistant turn.",
        "actor": "bootloader",
        "requires_user": True,
        "terminal_for_turn": True,
        "questions": STARTUP_QUESTIONS,
    },
    {
        "action_type": "write_startup_awaiting_answers_state",
        "flag": "startup_state_written_awaiting_answers",
        "label": "startup_state_written_awaiting_answers",
        "summary": "Record that the startup dialog is waiting for explicit user answers.",
        "actor": "bootloader",
    },
    {
        "action_type": "stop_for_startup_answers",
        "flag": "dialog_stopped_for_answers",
        "label": "dialog_stopped_for_startup_answers",
        "summary": "Stop after asking startup questions; no banner, route, agents, heartbeat, or implementation may start.",
        "actor": "bootloader",
        "terminal_for_turn": True,
    },
    {
        "action_type": "record_startup_answers",
        "flag": "startup_answers_recorded",
        "label": "startup_answers_recorded_by_router",
        "summary": "Record the later user reply that explicitly answered all startup questions.",
        "actor": "bootloader",
        "requires_user": True,
        "requires_payload": "startup_answers",
    },
    {
        "action_type": "emit_startup_banner",
        "flag": "banner_emitted",
        "label": "startup_banner_emitted_after_answers",
        "summary": "Display the startup banner in the user dialog after explicit answers, then record the confirmed display.",
        "actor": "bootloader",
        "card_id": "startup_banner",
    },
    {
        "action_type": "create_run_shell",
        "flag": "run_shell_created",
        "label": "run_shell_created",
        "summary": "Create a fresh run root under .flowpilot/runs.",
        "actor": "bootloader",
    },
    {
        "action_type": "write_current_pointer",
        "flag": "current_pointer_written",
        "label": "current_pointer_written",
        "summary": "Write .flowpilot/current.json as the active-run pointer.",
        "actor": "bootloader",
    },
    {
        "action_type": "update_run_index",
        "flag": "run_index_updated",
        "label": "run_index_updated",
        "summary": "Register the active run in .flowpilot/index.json.",
        "actor": "bootloader",
    },
    {
        "action_type": "copy_runtime_kit",
        "flag": "runtime_kit_copied",
        "label": "bootstrap_runtime_kit_copied",
        "summary": "Copy the audited runtime kit into the run root without generating new prompt bodies.",
        "actor": "bootloader",
    },
    {
        "action_type": "fill_runtime_placeholders",
        "flag": "placeholders_filled",
        "label": "bootstrap_placeholders_filled",
        "summary": "Fill run id, timestamps, and startup-answer placeholders only.",
        "actor": "bootloader",
    },
    {
        "action_type": "initialize_mailbox",
        "flag": "mailbox_initialized",
        "label": "mailbox_initialized_from_copied_kit",
        "summary": "Create mailbox, prompt-delivery, and packet-ledger state files.",
        "actor": "bootloader",
    },
    {
        "action_type": "record_user_request",
        "flag": "user_request_recorded",
        "label": "user_request_recorded_from_explicit_user_request",
        "summary": "Record the exact current FlowPilot task text from explicit user input before PM receives user_intake.",
        "actor": "bootloader",
        "requires_user": True,
        "requires_payload": "user_request",
    },
    {
        "action_type": "write_user_intake",
        "flag": "user_intake_ready",
        "label": "user_intake_template_filled_from_raw_user_request",
        "summary": "Write the user-intake packet from the router-recorded raw user request and startup answers.",
        "actor": "bootloader",
    },
    {
        "action_type": "start_role_slots",
        "flag": "roles_started",
        "label": "six_roles_started_from_user_answer",
        "summary": "Start the six current-task roles according to the user's background-agent answer.",
        "actor": "bootloader",
    },
    {
        "action_type": "inject_role_core_prompts",
        "flag": "role_core_prompts_injected",
        "label": "role_core_prompts_injected_from_copied_kit",
        "summary": "Deliver each role only its role core card from the copied runtime kit.",
        "actor": "bootloader",
    },
    {
        "action_type": "load_controller_core",
        "flag": "controller_core_loaded",
        "label": "controller_core_loaded",
        "summary": "End bootloader startup and enter the Controller-led router loop.",
        "actor": "bootloader",
    },
)

SYSTEM_CARD_SEQUENCE: tuple[dict[str, str], ...] = (
    {
        "flag": "pm_core_delivered",
        "label": "pm_core_card_delivered",
        "card_id": "pm.core",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_output_contract_catalog_delivered",
        "label": "pm_output_contract_catalog_card_delivered",
        "card_id": "pm.output_contract_catalog",
        "requires_flag": "pm_core_delivered",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_controller_reset_card_delivered",
        "label": "pm_controller_reset_duty_card_delivered",
        "card_id": "pm.controller_reset_duty",
        "requires_flag": "pm_output_contract_catalog_delivered",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_phase_map_delivered",
        "label": "pm_phase_map_card_delivered",
        "card_id": "pm.phase_map",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_startup_intake_card_delivered",
        "label": "pm_startup_intake_phase_card_delivered",
        "card_id": "pm.startup_intake",
        "to_role": "project_manager",
    },
    {
        "flag": "controller_resume_card_delivered",
        "label": "controller_resume_reentry_card_delivered",
        "card_id": "controller.resume_reentry",
        "requires_flag": "resume_state_loaded",
        "to_role": "controller",
    },
    {
        "flag": "pm_crew_rehydration_freshness_card_delivered",
        "label": "pm_crew_rehydration_freshness_card_delivered",
        "card_id": "pm.crew_rehydration_freshness",
        "requires_flag": "resume_roles_restored",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_resume_decision_card_delivered",
        "label": "pm_resume_decision_card_delivered",
        "card_id": "pm.resume_decision",
        "requires_flag": "pm_crew_rehydration_freshness_card_delivered",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_startup_fact_check_card_delivered",
        "label": "reviewer_startup_fact_check_card_delivered",
        "card_id": "reviewer.startup_fact_check",
        "requires_flag": "startup_mechanical_audit_written",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_startup_activation_card_delivered",
        "label": "pm_startup_activation_card_delivered",
        "card_id": "pm.startup_activation",
        "requires_flag": "startup_fact_reported",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_material_scan_card_delivered",
        "label": "pm_material_scan_card_delivered",
        "card_id": "pm.material_scan",
        "requires_flag": "startup_activation_approved",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_dispatch_card_delivered",
        "label": "reviewer_dispatch_request_card_delivered",
        "card_id": "reviewer.dispatch_request",
        "requires_any_flag": ["pm_material_packets_issued"],
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "reviewer_material_sufficiency_card_delivered",
        "label": "reviewer_material_sufficiency_card_delivered",
        "card_id": "reviewer.material_sufficiency",
        "requires_flag": "material_scan_results_relayed_to_reviewer",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_reviewer_report_event_delivered",
        "label": "pm_reviewer_report_event_card_delivered",
        "card_id": "pm.event.reviewer_report",
        "requires_any_flag": ["material_review_sufficient", "material_review_insufficient"],
        "to_role": "project_manager",
    },
    {
        "flag": "pm_material_absorb_or_research_card_delivered",
        "label": "pm_material_absorb_or_research_card_delivered",
        "card_id": "pm.material_absorb_or_research",
        "requires_flag": "pm_reviewer_report_event_delivered",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_research_package_card_delivered",
        "label": "pm_research_package_phase_card_delivered",
        "card_id": "pm.research_package",
        "requires_flag": "pm_research_requested",
        "to_role": "project_manager",
    },
    {
        "flag": "worker_research_report_card_delivered",
        "label": "worker_research_report_duty_card_delivered",
        "card_id": "worker.research_report",
        "requires_flag": "research_capability_decision_recorded",
        "to_role": "worker_a",
    },
    {
        "flag": "reviewer_research_check_card_delivered",
        "label": "reviewer_research_direct_source_check_card_delivered",
        "card_id": "reviewer.research_direct_source_check",
        "requires_flag": "research_result_relayed_to_reviewer",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_research_absorb_or_mutate_card_delivered",
        "label": "pm_research_absorb_or_mutate_phase_card_delivered",
        "card_id": "pm.research_absorb_or_mutate",
        "requires_flag": "research_review_passed",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_material_understanding_card_delivered",
        "label": "pm_material_understanding_phase_card_delivered",
        "card_id": "pm.material_understanding",
        "requires_flag": "material_accepted_by_pm",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_worker_result_card_delivered",
        "label": "reviewer_worker_result_review_card_delivered",
        "card_id": "reviewer.worker_result_review",
        "requires_flag": "current_node_result_relayed_to_reviewer",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_product_architecture_card_delivered",
        "label": "pm_product_architecture_phase_card_delivered",
        "card_id": "pm.product_architecture",
        "requires_flag": "material_understanding_written_by_pm",
        "to_role": "project_manager",
    },
    {
        "flag": "product_officer_product_architecture_card_delivered",
        "label": "product_officer_product_architecture_modelability_card_delivered",
        "card_id": "product_officer.product_architecture_modelability",
        "requires_flag": "product_architecture_written_by_pm",
        "to_role": "product_flowguard_officer",
    },
    {
        "flag": "reviewer_product_architecture_card_delivered",
        "label": "reviewer_product_architecture_challenge_card_delivered",
        "card_id": "reviewer.product_architecture_challenge",
        "requires_flag": "product_architecture_modelability_passed",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_root_contract_card_delivered",
        "label": "pm_root_contract_phase_card_delivered",
        "card_id": "pm.root_contract",
        "requires_flag": "product_architecture_reviewer_passed",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_root_contract_card_delivered",
        "label": "reviewer_root_contract_challenge_card_delivered",
        "card_id": "reviewer.root_contract_challenge",
        "requires_flag": "root_contract_written_by_pm",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "product_officer_root_contract_card_delivered",
        "label": "product_officer_root_contract_modelability_card_delivered",
        "card_id": "product_officer.root_contract_modelability",
        "requires_flag": "root_contract_reviewer_passed",
        "to_role": "product_flowguard_officer",
    },
    {
        "flag": "pm_dependency_policy_card_delivered",
        "label": "pm_dependency_policy_phase_card_delivered",
        "card_id": "pm.dependency_policy",
        "requires_flag": "root_contract_frozen_by_pm",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_child_skill_selection_card_delivered",
        "label": "pm_child_skill_selection_phase_card_delivered",
        "card_id": "pm.child_skill_selection",
        "requires_flag": "capabilities_manifest_written",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_child_skill_gate_manifest_card_delivered",
        "label": "pm_child_skill_gate_manifest_phase_card_delivered",
        "card_id": "pm.child_skill_gate_manifest",
        "requires_flag": "pm_child_skill_selection_written",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_child_skill_gate_manifest_card_delivered",
        "label": "reviewer_child_skill_gate_manifest_review_card_delivered",
        "card_id": "reviewer.child_skill_gate_manifest_review",
        "requires_flag": "child_skill_gate_manifest_written",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "process_officer_child_skill_card_delivered",
        "label": "process_officer_child_skill_conformance_model_card_delivered",
        "card_id": "process_officer.child_skill_conformance_model",
        "requires_flag": "child_skill_manifest_reviewer_passed",
        "to_role": "process_flowguard_officer",
    },
    {
        "flag": "product_officer_child_skill_card_delivered",
        "label": "product_officer_child_skill_product_fit_card_delivered",
        "card_id": "product_officer.child_skill_product_fit",
        "requires_flag": "child_skill_process_officer_passed",
        "to_role": "product_flowguard_officer",
    },
    {
        "flag": "pm_prior_path_context_card_delivered",
        "label": "pm_prior_path_context_phase_card_delivered",
        "card_id": "pm.prior_path_context",
        "requires_flag": "capability_evidence_synced",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_route_skeleton_card_delivered",
        "label": "pm_route_skeleton_phase_card_delivered",
        "card_id": "pm.route_skeleton",
        "requires_flag": "pm_prior_path_context_card_delivered",
        "to_role": "project_manager",
    },
    {
        "flag": "process_officer_route_check_card_delivered",
        "label": "process_officer_route_process_check_card_delivered",
        "card_id": "process_officer.route_process_check",
        "requires_flag": "route_draft_written_by_pm",
        "to_role": "process_flowguard_officer",
    },
    {
        "flag": "product_officer_route_check_card_delivered",
        "label": "product_officer_route_product_check_card_delivered",
        "card_id": "product_officer.route_product_check",
        "requires_flag": "process_officer_route_check_passed",
        "to_role": "product_flowguard_officer",
    },
    {
        "flag": "reviewer_route_check_card_delivered",
        "label": "reviewer_route_challenge_card_delivered",
        "card_id": "reviewer.route_challenge",
        "requires_flag": "product_officer_route_check_passed",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_current_node_card_delivered",
        "label": "pm_current_node_loop_phase_card_delivered",
        "card_id": "pm.current_node_loop",
        "requires_flag": "route_activated_by_pm",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_node_started_event_delivered",
        "label": "pm_node_started_event_card_delivered",
        "card_id": "pm.event.node_started",
        "requires_flag": "route_activated_by_pm",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_node_acceptance_plan_card_delivered",
        "label": "pm_node_acceptance_plan_phase_card_delivered",
        "card_id": "pm.node_acceptance_plan",
        "requires_flag": "pm_node_started_event_delivered",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_node_acceptance_plan_card_delivered",
        "label": "reviewer_node_acceptance_plan_review_card_delivered",
        "card_id": "reviewer.node_acceptance_plan_review",
        "requires_flag": "node_acceptance_plan_written",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "reviewer_current_node_dispatch_card_delivered",
        "label": "reviewer_current_node_dispatch_card_delivered",
        "card_id": "reviewer.current_node_dispatch",
        "requires_flag": "current_node_packet_registered",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_parent_backward_targets_card_delivered",
        "label": "pm_parent_backward_targets_phase_card_delivered",
        "card_id": "pm.parent_backward_targets",
        "requires_flag": "node_reviewer_passed_result",
        "requires_active_node_children": True,
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_parent_backward_replay_card_delivered",
        "label": "reviewer_parent_backward_replay_card_delivered",
        "card_id": "reviewer.parent_backward_replay",
        "requires_flag": "parent_backward_targets_built",
        "requires_active_node_children": True,
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_parent_segment_decision_card_delivered",
        "label": "pm_parent_segment_decision_card_delivered",
        "card_id": "pm.parent_segment_decision",
        "requires_flag": "parent_backward_replay_passed",
        "requires_active_node_children": True,
        "to_role": "project_manager",
    },
    {
        "flag": "pm_model_miss_triage_card_delivered",
        "label": "pm_model_miss_triage_phase_card_delivered",
        "card_id": "pm.model_miss_triage",
        "requires_any_flag": ["node_review_blocked", "material_scan_dispatch_blocked"],
        "to_role": "project_manager",
    },
    {
        "flag": "pm_review_repair_card_delivered",
        "label": "pm_review_repair_phase_card_delivered",
        "card_id": "pm.review_repair",
        "requires_flag": "model_miss_triage_closed",
        "requires_any_flag": ["node_review_blocked", "material_scan_dispatch_blocked"],
        "to_role": "project_manager",
    },
    {
        "flag": "pm_reviewer_blocked_event_delivered",
        "label": "pm_reviewer_blocked_event_card_delivered",
        "card_id": "pm.event.reviewer_blocked",
        "requires_any_flag": ["node_review_blocked", "material_scan_dispatch_blocked"],
        "to_role": "project_manager",
    },
    {
        "flag": "pm_evidence_quality_package_card_delivered",
        "label": "pm_evidence_quality_package_card_delivered",
        "card_id": "pm.evidence_quality_package",
        "requires_flag": "node_completed_by_pm",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_evidence_quality_card_delivered",
        "label": "reviewer_evidence_quality_review_card_delivered",
        "card_id": "reviewer.evidence_quality_review",
        "requires_flag": "evidence_quality_package_written",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_final_ledger_card_delivered",
        "label": "pm_final_ledger_phase_card_delivered",
        "card_id": "pm.final_ledger",
        "requires_flag": "evidence_quality_reviewer_passed",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_final_backward_replay_card_delivered",
        "label": "reviewer_final_backward_replay_card_delivered",
        "card_id": "reviewer.final_backward_replay",
        "requires_flag": "final_ledger_built_clean",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_closure_card_delivered",
        "label": "pm_closure_phase_card_delivered",
        "card_id": "pm.closure",
        "requires_flag": "final_backward_replay_passed",
        "to_role": "project_manager",
    },
)

CARD_PHASE_BY_ID = {
    "pm.product_architecture": "product_architecture",
    "product_officer.product_architecture_modelability": "product_architecture",
    "reviewer.product_architecture_challenge": "product_architecture",
    "pm.root_contract": "root_contract",
    "reviewer.root_contract_challenge": "root_contract",
    "product_officer.root_contract_modelability": "root_contract",
    "pm.dependency_policy": "dependency_policy",
    "pm.child_skill_selection": "child_skill_selection",
    "pm.child_skill_gate_manifest": "child_skill_gate_manifest",
    "reviewer.child_skill_gate_manifest_review": "child_skill_gate_manifest",
    "process_officer.child_skill_conformance_model": "child_skill_gate_manifest",
    "product_officer.child_skill_product_fit": "child_skill_gate_manifest",
    "pm.prior_path_context": "prior_path_context",
    "pm.route_skeleton": "route_skeleton",
    "process_officer.route_process_check": "route_skeleton",
    "product_officer.route_product_check": "route_skeleton",
    "reviewer.route_challenge": "route_skeleton",
}

CARD_REQUIRED_SOURCE_PATHS = {
    "pm.product_architecture": {
        "pm_material_understanding": "pm_material_understanding.json",
        "pm_material_understanding_payload": "material/pm_material_understanding_payload.json",
    },
    "product_officer.product_architecture_modelability": {
        "product_function_architecture": "product_function_architecture.json",
    },
    "reviewer.product_architecture_challenge": {
        "product_function_architecture": "product_function_architecture.json",
        "product_architecture_modelability": "flowguard/product_architecture_modelability.json",
    },
    "pm.root_contract": {
        "product_function_architecture": "product_function_architecture.json",
        "product_architecture_challenge": "reviews/product_architecture_challenge.json",
        "product_architecture_modelability": "flowguard/product_architecture_modelability.json",
    },
    "reviewer.root_contract_challenge": {
        "root_acceptance_contract": "root_acceptance_contract.json",
        "standard_scenario_pack": "standard_scenario_pack.json",
    },
    "product_officer.root_contract_modelability": {
        "root_acceptance_contract": "root_acceptance_contract.json",
        "standard_scenario_pack": "standard_scenario_pack.json",
    },
    "pm.dependency_policy": {
        "root_acceptance_contract": "root_acceptance_contract.json",
        "product_function_architecture": "product_function_architecture.json",
    },
    "pm.child_skill_selection": {
        "dependency_policy": "dependency_policy.json",
        "capabilities": "capabilities.json",
    },
    "pm.child_skill_gate_manifest": {
        "capabilities": "capabilities.json",
        "pm_child_skill_selection": "pm_child_skill_selection.json",
        "root_acceptance_contract": "root_acceptance_contract.json",
    },
    "reviewer.child_skill_gate_manifest_review": {
        "child_skill_gate_manifest": "child_skill_gate_manifest.json",
        "pm_child_skill_selection": "pm_child_skill_selection.json",
        "capabilities": "capabilities.json",
    },
    "process_officer.child_skill_conformance_model": {
        "child_skill_gate_manifest": "child_skill_gate_manifest.json",
        "child_skill_gate_manifest_review": "reviews/child_skill_gate_manifest_review.json",
        "pm_child_skill_selection": "pm_child_skill_selection.json",
        "capabilities": "capabilities.json",
    },
    "product_officer.child_skill_product_fit": {
        "child_skill_gate_manifest": "child_skill_gate_manifest.json",
        "child_skill_gate_manifest_review": "reviews/child_skill_gate_manifest_review.json",
        "child_skill_conformance_model": "flowguard/child_skill_conformance_model.json",
        "pm_child_skill_selection": "pm_child_skill_selection.json",
        "capabilities": "capabilities.json",
        "root_acceptance_contract": "root_acceptance_contract.json",
    },
    "pm.prior_path_context": {
        "child_skill_gate_manifest": "child_skill_gate_manifest.json",
        "child_skill_manifest_pm_approval": "child_skill_manifest_pm_approval.json",
        "capability_sync": "capabilities/capability_sync.json",
    },
    "pm.route_skeleton": {
        "root_acceptance_contract": "root_acceptance_contract.json",
        "child_skill_gate_manifest": "child_skill_gate_manifest.json",
        "child_skill_manifest_pm_approval": "child_skill_manifest_pm_approval.json",
        "capability_sync": "capabilities/capability_sync.json",
        "pm_prior_path_context": "route_memory/pm_prior_path_context.json",
    },
    "process_officer.route_process_check": {
        "root_acceptance_contract": "root_acceptance_contract.json",
        "child_skill_gate_manifest": "child_skill_gate_manifest.json",
        "capability_sync": "capabilities/capability_sync.json",
    },
    "product_officer.route_product_check": {
        "root_acceptance_contract": "root_acceptance_contract.json",
        "child_skill_gate_manifest": "child_skill_gate_manifest.json",
        "route_process_check": "flowguard/route_process_check.json",
    },
    "reviewer.route_challenge": {
        "root_acceptance_contract": "root_acceptance_contract.json",
        "child_skill_gate_manifest": "child_skill_gate_manifest.json",
        "route_process_check": "flowguard/route_process_check.json",
        "route_product_check": "flowguard/route_product_check.json",
    },
}

RUN_TERMINAL_STATUSES = {"stopped_by_user", "cancelled_by_user", "protocol_dead_end", "completed", "closed", "stopped"}

MAIL_SEQUENCE: tuple[dict[str, str], ...] = (
    {
        "flag": "user_intake_delivered_to_pm",
        "label": "user_intake_delivered_to_pm",
        "mail_id": "user_intake",
        "to_role": "project_manager",
    },
)

EXTERNAL_EVENTS: dict[str, dict[str, str]] = {
    "user_requests_run_stop": {
        "flag": "run_stopped_by_user",
        "summary": "The user explicitly stopped the active FlowPilot run; no further route work is authorized.",
    },
    "user_requests_run_cancel": {
        "flag": "run_cancelled_by_user",
        "summary": "The user explicitly cancelled the active FlowPilot run; no further route work is authorized.",
    },
    "pm_first_decision_resets_controller": {
        "flag": "pm_controller_reset_decision_returned",
        "requires_flag": "user_intake_delivered_to_pm",
        "summary": "PM reminded Controller that it is only a relay and status-flow controller.",
    },
    "controller_role_confirmed_from_pm_reset": {
        "flag": "controller_role_confirmed",
        "requires_flag": "pm_controller_reset_decision_returned",
        "summary": "Controller acknowledged PM reset and remains relay-only.",
    },
    "heartbeat_or_manual_resume_requested": {
        "flag": "resume_reentry_requested",
        "summary": "A heartbeat or manual resume wakeup requested router-guided re-entry.",
    },
    "host_records_heartbeat_binding": {
        "flag": "continuation_binding_recorded",
        "summary": "Host recorded the active run heartbeat/manual-resume binding before startup fact review.",
    },
    "pm_resume_recovery_decision_returned": {
        "flag": "pm_resume_recovery_decision_returned",
        "requires_flag": "pm_resume_decision_card_delivered",
        "summary": "PM returned a resume recovery decision after Controller state re-entry.",
    },
    "reviewer_reports_startup_facts": {
        "flag": "startup_fact_reported",
        "requires_flag": "reviewer_startup_fact_check_card_delivered",
        "summary": "Reviewer reported independent startup facts for PM activation.",
    },
    "pm_approves_startup_activation": {
        "flag": "startup_activation_approved",
        "requires_flag": "pm_startup_activation_card_delivered",
        "summary": "PM approved opening work beyond startup from the reviewer startup fact report.",
    },
    "pm_requests_startup_repair": {
        "flag": "startup_repair_requested",
        "requires_flag": "pm_startup_activation_card_delivered",
        "summary": "PM returned a targeted startup repair request instead of opening work beyond startup.",
    },
    "pm_declares_startup_protocol_dead_end": {
        "flag": "startup_protocol_dead_end_declared",
        "requires_flag": "pm_startup_activation_card_delivered",
        "summary": "PM declared that the startup block has no legal repair path in the current protocol and stopped the run.",
    },
    "pm_issues_material_and_capability_scan_packets": {
        "flag": "pm_material_packets_issued",
        "requires_flag": "pm_material_scan_card_delivered",
        "summary": "PM issued bounded material/capability scan packets.",
    },
    "pm_registers_current_node_packet": {
        "flag": "current_node_packet_registered",
        "requires_flag": "node_acceptance_plan_reviewer_passed",
        "summary": "PM registered a current-node packet envelope for reviewer dispatch.",
    },
    "reviewer_allows_material_scan_dispatch": {
        "flag": "reviewer_dispatch_allowed",
        "requires_flag": "reviewer_dispatch_card_delivered",
        "summary": "Reviewer allowed material scan dispatch.",
    },
    "reviewer_blocks_material_scan_dispatch": {
        "flag": "material_scan_dispatch_blocked",
        "requires_flag": "reviewer_dispatch_card_delivered",
        "summary": "Reviewer blocked material scan dispatch before worker packet relay.",
    },
    "reviewer_blocks_material_scan_dispatch_recheck": {
        "flag": "material_scan_dispatch_recheck_blocked",
        "requires_flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "Reviewer blocked material scan dispatch during repair transaction recheck.",
    },
    "reviewer_protocol_blocker_material_scan_dispatch_recheck": {
        "flag": "material_scan_dispatch_recheck_protocol_blocked",
        "requires_flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "Reviewer reported a protocol blocker during material scan repair transaction recheck.",
    },
    "reviewer_allows_current_node_dispatch": {
        "flag": "current_node_dispatch_allowed",
        "requires_flag": "reviewer_current_node_dispatch_card_delivered",
        "summary": "Reviewer allowed current-node worker dispatch.",
    },
    "worker_scan_packet_bodies_delivered_after_dispatch": {
        "flag": "worker_packets_delivered",
        "requires_flag": "material_scan_packets_relayed",
        "summary": "Worker packet bodies were delivered after reviewer dispatch.",
    },
    "worker_scan_results_returned": {
        "flag": "worker_scan_results_returned",
        "requires_flag": "worker_packets_delivered",
        "summary": "Worker scan results returned to reviewer path.",
    },
    "worker_current_node_result_returned": {
        "flag": "current_node_worker_result_returned",
        "requires_flag": "current_node_packet_relayed",
        "summary": "Worker returned a current-node result envelope.",
    },
    "reviewer_reports_material_sufficient": {
        "flag": "material_review_sufficient",
        "requires_flag": "reviewer_material_sufficiency_card_delivered",
        "summary": "Reviewer reported material sufficient.",
    },
    "reviewer_reports_material_insufficient": {
        "flag": "material_review_insufficient",
        "requires_flag": "reviewer_material_sufficiency_card_delivered",
        "summary": "Reviewer reported material insufficient.",
    },
    "pm_accepts_reviewed_material": {
        "flag": "material_accepted_by_pm",
        "requires_flag": "pm_material_absorb_or_research_card_delivered",
        "summary": "PM accepted reviewer-approved material.",
    },
    "pm_requests_research_after_material_insufficient": {
        "flag": "pm_research_requested",
        "requires_flag": "pm_material_absorb_or_research_card_delivered",
        "summary": "PM requested bounded research instead of accepting insufficient material.",
    },
    "pm_writes_research_package": {
        "flag": "research_package_written_by_pm",
        "requires_flag": "pm_research_package_card_delivered",
        "summary": "PM wrote a bounded research package after insufficient material.",
    },
    "research_capability_decision_recorded": {
        "flag": "research_capability_decision_recorded",
        "requires_flag": "research_package_written_by_pm",
        "summary": "PM recorded research source/tool capability and approval boundaries.",
    },
    "worker_research_report_returned": {
        "flag": "worker_research_report_returned",
        "requires_flag": "worker_research_report_card_delivered",
        "summary": "Worker returned a bounded research report.",
    },
    "reviewer_passes_research_direct_source_check": {
        "flag": "research_review_passed",
        "requires_flag": "reviewer_research_check_card_delivered",
        "summary": "Reviewer passed direct-source or experiment-output research check.",
    },
    "pm_absorbs_reviewed_research": {
        "flag": "research_result_absorbed_by_pm",
        "requires_flag": "pm_research_absorb_or_mutate_card_delivered",
        "summary": "PM absorbed reviewer-approved research into material understanding.",
    },
    "pm_writes_material_understanding": {
        "flag": "material_understanding_written_by_pm",
        "requires_flag": "pm_material_understanding_card_delivered",
        "summary": "PM wrote material understanding from reviewed material and approved research if required.",
    },
    "pm_writes_product_function_architecture": {
        "flag": "product_architecture_written_by_pm",
        "requires_flag": "pm_product_architecture_card_delivered",
        "summary": "PM wrote the product-function architecture from reviewed material.",
    },
    "reviewer_passes_product_architecture": {
        "flag": "product_architecture_reviewer_passed",
        "requires_flag": "reviewer_product_architecture_card_delivered",
        "summary": "Reviewer passed the PM product-function architecture challenge.",
    },
    "product_officer_passes_product_architecture_modelability": {
        "flag": "product_architecture_modelability_passed",
        "requires_flag": "product_officer_product_architecture_card_delivered",
        "summary": "Product FlowGuard Officer passed product architecture modelability.",
    },
    "pm_writes_root_acceptance_contract": {
        "flag": "root_contract_written_by_pm",
        "requires_flag": "pm_root_contract_card_delivered",
        "summary": "PM wrote the root acceptance contract and standard scenario pack draft.",
    },
    "reviewer_passes_root_acceptance_contract": {
        "flag": "root_contract_reviewer_passed",
        "requires_flag": "reviewer_root_contract_card_delivered",
        "summary": "Reviewer passed the root acceptance contract challenge.",
    },
    "product_officer_passes_root_acceptance_contract_modelability": {
        "flag": "root_contract_modelability_passed",
        "requires_flag": "product_officer_root_contract_card_delivered",
        "summary": "Product FlowGuard Officer passed root contract modelability.",
    },
    "pm_freezes_root_acceptance_contract": {
        "flag": "root_contract_frozen_by_pm",
        "requires_flag": "root_contract_modelability_passed",
        "summary": "PM froze the reviewed root acceptance contract as the completion floor.",
    },
    "pm_records_dependency_policy": {
        "flag": "dependency_policy_recorded",
        "requires_flag": "pm_dependency_policy_card_delivered",
        "summary": "PM recorded dependency and installation policy.",
    },
    "pm_writes_capabilities_manifest": {
        "flag": "capabilities_manifest_written",
        "requires_flag": "dependency_policy_recorded",
        "summary": "PM wrote route capabilities manifest from product architecture and root contract.",
    },
    "pm_writes_child_skill_selection": {
        "flag": "pm_child_skill_selection_written",
        "requires_flag": "pm_child_skill_selection_card_delivered",
        "summary": "PM wrote child-skill selection from product needs, not raw availability.",
    },
    "pm_writes_child_skill_gate_manifest": {
        "flag": "child_skill_gate_manifest_written",
        "requires_flag": "pm_child_skill_gate_manifest_card_delivered",
        "summary": "PM wrote the child-skill gate manifest.",
    },
    "reviewer_passes_child_skill_gate_manifest": {
        "flag": "child_skill_manifest_reviewer_passed",
        "requires_flag": "reviewer_child_skill_gate_manifest_card_delivered",
        "summary": "Reviewer passed child-skill gate manifest review.",
    },
    "process_officer_passes_child_skill_conformance_model": {
        "flag": "child_skill_process_officer_passed",
        "requires_flag": "process_officer_child_skill_card_delivered",
        "summary": "Process FlowGuard Officer passed child-skill conformance model review.",
    },
    "product_officer_passes_child_skill_product_fit": {
        "flag": "child_skill_product_officer_passed",
        "requires_flag": "product_officer_child_skill_card_delivered",
        "summary": "Product FlowGuard Officer passed child-skill product fit review.",
    },
    "pm_approves_child_skill_manifest_for_route": {
        "flag": "child_skill_manifest_pm_approved_for_route",
        "requires_flag": "child_skill_product_officer_passed",
        "summary": "PM approved the child-skill manifest for route use.",
    },
    "capability_evidence_synced": {
        "flag": "capability_evidence_synced",
        "requires_flag": "child_skill_manifest_pm_approved_for_route",
        "summary": "Capability evidence was synced after PM child-skill approval.",
    },
    "pm_writes_route_draft": {
        "flag": "route_draft_written_by_pm",
        "requires_flag": "pm_route_skeleton_card_delivered",
        "summary": "PM wrote the route draft from the frozen root contract.",
    },
    "process_officer_passes_route_check": {
        "flag": "process_officer_route_check_passed",
        "requires_flag": "process_officer_route_check_card_delivered",
        "summary": "Process FlowGuard Officer passed the route process check.",
    },
    "product_officer_passes_route_check": {
        "flag": "product_officer_route_check_passed",
        "requires_flag": "product_officer_route_check_card_delivered",
        "summary": "Product FlowGuard Officer passed the route product check.",
    },
    "reviewer_passes_route_check": {
        "flag": "reviewer_route_check_passed",
        "requires_flag": "reviewer_route_check_card_delivered",
        "summary": "Reviewer passed the route challenge.",
    },
    "pm_activates_reviewed_route": {
        "flag": "route_activated_by_pm",
        "requires_flag": "reviewer_route_check_passed",
        "summary": "PM activated route after required officer and reviewer checks.",
    },
    "pm_writes_node_acceptance_plan": {
        "flag": "node_acceptance_plan_written",
        "requires_flag": "pm_node_acceptance_plan_card_delivered",
        "summary": "PM wrote the active node acceptance plan before packet dispatch.",
    },
    "reviewer_passes_node_acceptance_plan": {
        "flag": "node_acceptance_plan_reviewer_passed",
        "requires_flag": "reviewer_node_acceptance_plan_card_delivered",
        "summary": "Reviewer passed the active node acceptance plan.",
    },
    "current_node_reviewer_blocks_result": {
        "flag": "node_review_blocked",
        "requires_flag": "reviewer_worker_result_card_delivered",
        "summary": "Reviewer blocked current-node result.",
    },
    "current_node_reviewer_passes_result": {
        "flag": "node_reviewer_passed_result",
        "requires_flag": "reviewer_worker_result_card_delivered",
        "summary": "Reviewer passed current-node result.",
    },
    "pm_builds_parent_backward_targets": {
        "flag": "parent_backward_targets_built",
        "requires_flag": "pm_parent_backward_targets_card_delivered",
        "summary": "PM built local parent backward replay targets for the active node.",
    },
    "reviewer_passes_parent_backward_replay": {
        "flag": "parent_backward_replay_passed",
        "requires_flag": "reviewer_parent_backward_replay_card_delivered",
        "summary": "Reviewer passed local parent backward replay.",
    },
    "pm_records_parent_segment_decision": {
        "flag": "parent_segment_decision_recorded",
        "requires_flag": "pm_parent_segment_decision_card_delivered",
        "summary": "PM recorded parent segment decision after local backward replay.",
    },
    "pm_mutates_route_after_review_block": {
        "flag": "route_mutated_by_pm",
        "requires_flag": "model_miss_triage_closed",
        "summary": "PM mutated the route and invalidated affected stale evidence after a reviewer block.",
    },
    "pm_records_model_miss_triage_decision": {
        "flag": "model_miss_triage_closed",
        "requires_flag": "pm_model_miss_triage_card_delivered",
        "summary": "PM recorded the model-miss triage decision that precedes normal repair.",
    },
    "pm_records_control_blocker_repair_decision": {
        "flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "PM recorded a repair decision for a router materialized control blocker.",
    },
    "role_records_gate_decision": {
        "flag": "gate_decision_recorded",
        "summary": "A PM, reviewer, or FlowGuard officer recorded a mechanically valid GateDecision.",
    },
    "pm_completes_current_node_from_reviewed_result": {
        "flag": "node_completed_by_pm",
        "requires_flag": "node_reviewer_passed_result",
        "summary": "PM completed current node from reviewed result.",
    },
    "pm_records_evidence_quality_package": {
        "flag": "evidence_quality_package_written",
        "requires_flag": "pm_evidence_quality_package_card_delivered",
        "summary": "PM recorded evidence, generated-resource, UI/visual, and quality package ledgers.",
    },
    "reviewer_passes_evidence_quality_package": {
        "flag": "evidence_quality_reviewer_passed",
        "requires_flag": "reviewer_evidence_quality_card_delivered",
        "summary": "Reviewer passed the evidence quality package before final ledger work.",
    },
    "pm_records_final_route_wide_ledger_clean": {
        "flag": "final_ledger_built_clean",
        "requires_flag": "pm_final_ledger_card_delivered",
        "summary": "PM built a current-route final ledger with zero unresolved items.",
    },
    "reviewer_final_backward_replay_passed": {
        "flag": "final_backward_replay_passed",
        "requires_flag": "reviewer_final_backward_replay_card_delivered",
        "summary": "Reviewer passed final backward replay.",
    },
    "pm_approves_terminal_closure": {
        "flag": "pm_closure_approved",
        "requires_flag": "pm_closure_card_delivered",
        "summary": "PM approved terminal closure after clean final ledger and backward replay.",
    },
}


class RouterError(ValueError):
    """Raised when a router operation violates the state machine."""

    def __init__(self, message: str, *, control_blocker: dict[str, Any] | None = None):
        super().__init__(message)
        self.control_blocker = control_blocker


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def runtime_kit_source() -> Path:
    return Path(__file__).resolve().parent / "runtime_kit"


def legacy_bootstrap_state_path(project_root: Path) -> Path:
    return project_root / ".flowpilot" / "bootstrap" / "startup_state.json"


def run_bootstrap_state_path(run_root: Path) -> Path:
    return run_root / "bootstrap" / "startup_state.json"


def bootstrap_state_path(project_root: Path, state: dict[str, Any] | None = None) -> Path:
    if state and state.get("run_root"):
        return run_bootstrap_state_path(project_root / str(state["run_root"]))
    current = read_json_if_exists(project_root / ".flowpilot" / "current.json")
    raw = current.get("startup_bootstrap_path")
    if raw:
        return project_root / str(raw)
    raw_root = current.get("current_run_root") or current.get("active_run_root") or current.get("run_root")
    if raw_root:
        candidate = run_bootstrap_state_path(project_root / str(raw_root))
        if candidate.exists():
            return candidate
    return legacy_bootstrap_state_path(project_root)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RouterError(f"expected JSON object: {path}")
    return payload


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return read_json(path)


def _json_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256((json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")).hexdigest()


def _without_role_output_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    body = dict(payload)
    body.pop("_role_output_envelope", None)
    return body


def _role_output_semantic_hash(path: Path) -> str | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    return _json_sha256(_without_role_output_envelope(raw))


def _role_output_semantic_hashes(path: Path) -> set[str]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return set()
    if not isinstance(raw, dict):
        return set()
    body = _without_role_output_envelope(raw)
    canonical_lf = json.dumps(body, indent=2, sort_keys=True) + "\n"
    variants = {canonical_lf, canonical_lf.replace("\n", "\r\n")}
    return {hashlib.sha256(variant.encode("utf-8")).hexdigest() for variant in variants}


def _role_output_hashes(path: Path) -> tuple[str, str | None]:
    raw_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    return raw_hash, _role_output_semantic_hash(path)


def project_relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise RouterError(f"path is outside project root: {path}") from exc


def resolve_project_path(project_root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else project_root / path


def _evidence_path_record(project_root: Path, path: Path) -> dict[str, Any]:
    record: dict[str, Any] = {"path": project_relative(project_root, path), "exists": path.exists()}
    if path.exists() and path.is_file():
        record["sha256"] = packet_runtime.sha256_file(path)
    return record


def _router_owned_check_proof_path(audit_path: Path) -> Path:
    return audit_path.with_name(f"{audit_path.name}.proof.json")


def _write_router_owned_check_proof(
    project_root: Path,
    run_root: Path,
    *,
    check_name: str,
    audit_path: Path,
    source_kind: str,
    evidence_paths: list[Path],
    reviewer_replacement_scope: str = "mechanical_only",
) -> dict[str, Any]:
    if source_kind not in ROUTER_TRUSTED_PROOF_SOURCES:
        raise RouterError(f"unsupported router-owned proof source: {source_kind}")
    if not audit_path.exists():
        raise RouterError(f"router-owned proof requires audit file: {audit_path}")
    proof_path = _router_owned_check_proof_path(audit_path)
    proof = {
        "schema_version": ROUTER_OWNED_CHECK_PROOF_SCHEMA,
        "run_id": run_root.name,
        "check_name": check_name,
        "check_owner": "flowpilot_router",
        "source_kind": source_kind,
        "trust_basis": "non_self_attested_recomputed_or_host_bound",
        "self_attested_ai_claims_accepted_as_proof": False,
        "reviewer_replacement_scope": reviewer_replacement_scope,
        "audit_path": project_relative(project_root, audit_path),
        "audit_sha256": packet_runtime.sha256_file(audit_path),
        "evidence_paths": [_evidence_path_record(project_root, path) for path in evidence_paths],
        "created_at": utc_now(),
    }
    write_json(proof_path, proof)
    return {"proof_path": project_relative(project_root, proof_path), "proof": proof}


def _validate_router_owned_check_proof(
    project_root: Path,
    run_root: Path,
    *,
    check_name: str,
    audit_path: Path,
) -> dict[str, Any]:
    proof_path = _router_owned_check_proof_path(audit_path)
    proof = read_json_if_exists(proof_path)
    if proof.get("schema_version") != ROUTER_OWNED_CHECK_PROOF_SCHEMA:
        raise RouterError(f"router-owned proof is missing or has wrong schema: {proof_path}")
    if proof.get("run_id") != run_root.name:
        raise RouterError("router-owned proof run_id mismatch")
    if proof.get("check_name") != check_name:
        raise RouterError("router-owned proof check_name mismatch")
    if proof.get("check_owner") != "flowpilot_router":
        raise RouterError("router-owned proof must be owned by flowpilot_router")
    if proof.get("source_kind") not in ROUTER_TRUSTED_PROOF_SOURCES:
        raise RouterError("router-owned proof has untrusted source_kind")
    if proof.get("self_attested_ai_claims_accepted_as_proof") is not False:
        raise RouterError("router-owned proof cannot accept self-attested AI claims")
    if proof.get("reviewer_replacement_scope") != "mechanical_only":
        raise RouterError("router-owned proof may replace only mechanical reviewer work")
    if proof.get("audit_path") != project_relative(project_root, audit_path):
        raise RouterError("router-owned proof audit_path mismatch")
    if proof.get("audit_sha256") != packet_runtime.sha256_file(audit_path):
        raise RouterError("router-owned proof audit hash is stale")
    return proof


def _load_file_backed_role_payload(project_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Load a role report/decision body from an envelope-only event payload."""

    if not isinstance(payload, dict):
        raise RouterError("role event payload must be an object")
    path_keys = (
        "body_path",
        "report_path",
        "decision_path",
        "result_body_path",
        "memo_path",
        "architecture_path",
        "contract_path",
        "manifest_path",
        "route_path",
        "draft_path",
        "plan_path",
        "package_path",
        "ledger_path",
    )
    hash_keys = (
        "body_hash",
        "report_hash",
        "decision_hash",
        "result_body_hash",
        "memo_hash",
        "architecture_hash",
        "contract_hash",
        "manifest_hash",
        "route_hash",
        "draft_hash",
        "plan_hash",
        "package_hash",
        "ledger_hash",
    )
    body_path_key = next((key for key in path_keys if payload.get(key)), None)
    if not body_path_key:
        if "path" in payload or "hash" in payload:
            raise RouterError(
                "role event envelope must use body_path/report_path/decision_path/result_body_path "
                "and body_hash/report_hash/decision_hash/result_body_hash"
            )
        raise RouterError("role event requires a file-backed body path")
    body_hash_key = next((key for key in hash_keys if payload.get(key)), None)
    if not body_hash_key:
        raise RouterError("role event requires a body/report/decision hash")
    body_path = payload[body_path_key]
    forbidden_controller_visible_body_keys = {
        "blockers",
        "checks",
        "decision",
        "evidence",
        "findings",
        "passed",
        "recommendations",
        "repair_instructions",
        "commands",
        "report_body",
        "decision_body",
        "result_body",
    }
    leaked_keys = sorted(forbidden_controller_visible_body_keys & set(payload))
    if leaked_keys:
        raise RouterError(f"envelope payload leaked role body fields to Controller: {', '.join(leaked_keys)}")
    path = resolve_project_path(project_root, str(body_path))
    if not path.exists():
        raise RouterError(f"role body path is missing: {body_path}")
    expected_hash = str(payload[body_hash_key])
    raw_hash, semantic_hash = _role_output_hashes(path)
    accepted_hashes = {raw_hash}
    accepted_hashes.update(_role_output_semantic_hashes(path))
    if expected_hash not in accepted_hashes:
        raise RouterError("role body hash mismatch")
    loaded = read_json(path)
    replay_hash = semantic_hash or raw_hash
    loaded["_role_output_envelope"] = {
        "body_path": project_relative(project_root, path),
        "body_hash": replay_hash,
        "body_raw_sha256": raw_hash,
        "body_semantic_sha256": semantic_hash,
        "body_path_key": body_path_key,
        "body_hash_key": body_hash_key,
        "controller_visibility": payload.get("controller_visibility") or "role_output_envelope_only",
        "chat_response_body_allowed": False,
    }
    return loaded


def _load_file_backed_role_payload_if_present(project_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    path_keys = {
        "body_path",
        "report_path",
        "decision_path",
        "result_body_path",
        "memo_path",
        "architecture_path",
        "contract_path",
        "manifest_path",
        "route_path",
        "draft_path",
        "plan_path",
        "package_path",
        "ledger_path",
    }
    if isinstance(payload, dict) and any(payload.get(key) for key in path_keys):
        return _load_file_backed_role_payload(project_root, payload)
    return payload


def _role_output_envelope_record(payload: dict[str, Any]) -> dict[str, Any]:
    envelope = payload.get("_role_output_envelope")
    if isinstance(envelope, dict):
        return {"_role_output_envelope": envelope}
    return {}


def _role_output_snapshot_name(run_root: Path, output_path: Path) -> str:
    try:
        relative = output_path.resolve().relative_to(run_root.resolve()).as_posix()
    except ValueError:
        relative = output_path.name
    return relative.replace("/", "__").replace("\\", "__")


def _role_output_envelope_record_for_mutable_artifact(
    project_root: Path,
    run_root: Path,
    output_path: Path,
    payload: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    envelope = payload.get("_role_output_envelope")
    if not isinstance(envelope, dict):
        return {}
    body_path = envelope.get("body_path")
    if not isinstance(body_path, str):
        return {"_role_output_envelope": envelope}
    source_path = resolve_project_path(project_root, body_path)
    if source_path.resolve() != output_path.resolve():
        return {"_role_output_envelope": envelope}
    snapshot_path = run_root / "role_output_snapshots" / f"{_role_output_snapshot_name(run_root, output_path)}.json"
    write_json(snapshot_path, _without_role_output_envelope(payload))
    raw_hash, semantic_hash = _role_output_hashes(snapshot_path)
    snapshot_envelope = dict(envelope)
    snapshot_envelope.update(
        {
            "body_path": project_relative(project_root, snapshot_path),
            "body_hash": semantic_hash or raw_hash,
            "body_raw_sha256": raw_hash,
            "body_semantic_sha256": semantic_hash,
            "body_snapshot_for_mutable_artifact": project_relative(project_root, output_path),
            "body_snapshot_reason": reason,
        }
    )
    return {"_role_output_envelope": snapshot_envelope}


def new_bootstrap_state(run_id: str | None = None, run_root_rel: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": BOOTSTRAP_STATE_SCHEMA,
        "status": "new",
        "bootstrap_scope": "run_scoped" if run_id and run_root_rel else "legacy",
        "router_loaded": False,
        "startup_state": "none",
        "bootloader_actions": 0,
        "router_action_requests": 0,
        "pending_action": None,
        "startup_answers": None,
        "user_request": None,
        "run_id": run_id,
        "run_root": run_root_rel,
        "flags": {action["flag"]: False for action in BOOT_ACTIONS},
        "history": [],
    }


def _create_startup_bootstrap_state(project_root: Path) -> dict[str, Any]:
    base_run_id = _create_run_id()
    for suffix in range(100):
        run_id = base_run_id if suffix == 0 else f"{base_run_id}-{suffix:02d}"
        run_root = project_root / ".flowpilot" / "runs" / run_id
        if not run_root.exists():
            break
    else:
        raise RouterError(f"could not allocate unique startup run id from {base_run_id}")
    run_root_rel = project_relative(project_root, run_root)
    state = new_bootstrap_state(run_id=run_id, run_root_rel=run_root_rel)
    write_json(
        project_root / ".flowpilot" / "current.json",
        {
            "schema_version": "flowpilot.current.v1",
            "current_run_id": run_id,
            "current_run_root": run_root_rel,
            "status": "startup_bootstrap",
            "startup_bootstrap_path": project_relative(project_root, run_bootstrap_state_path(run_root)),
            "updated_at": utc_now(),
        },
    )
    return state


def _load_existing_bootstrap_state(project_root: Path) -> dict[str, Any] | None:
    current = read_json_if_exists(project_root / ".flowpilot" / "current.json")
    raw = current.get("startup_bootstrap_path")
    candidate: Path | None = project_root / str(raw) if raw else None
    if candidate is None:
        raw_root = current.get("current_run_root") or current.get("active_run_root") or current.get("run_root")
        if raw_root:
            candidate = run_bootstrap_state_path(project_root / str(raw_root))
    if candidate is None or not candidate.exists():
        return None
    state = read_json(candidate)
    if state.get("schema_version") != BOOTSTRAP_STATE_SCHEMA:
        return None
    return state


def load_bootstrap_state(project_root: Path, *, create_if_missing: bool = False, new_invocation: bool = False) -> dict[str, Any]:
    if new_invocation:
        return _create_startup_bootstrap_state(project_root)
    state = _load_existing_bootstrap_state(project_root)
    if state is None:
        if not create_if_missing:
            return new_bootstrap_state()
        state = _create_startup_bootstrap_state(project_root)
    path = bootstrap_state_path(project_root, state)
    if not path.exists():
        return state
    flags = state.setdefault("flags", {})
    for action in BOOT_ACTIONS:
        flags.setdefault(action["flag"], False)
    state.setdefault("history", [])
    state.setdefault("pending_action", None)
    state.setdefault("router_action_requests", 0)
    state.setdefault("bootloader_actions", 0)
    _normalize_startup_question_stop_boundary(state)
    return state


def save_bootstrap_state(project_root: Path, state: dict[str, Any]) -> None:
    write_json(bootstrap_state_path(project_root, state), state)


def active_run_root(project_root: Path, state: dict[str, Any] | None = None) -> Path | None:
    if state and state.get("run_root"):
        return project_root / str(state["run_root"])
    current = read_json_if_exists(project_root / ".flowpilot" / "current.json")
    raw = current.get("current_run_root") or current.get("active_run_root") or current.get("run_root")
    if raw:
        return project_root / str(raw)
    run_id = current.get("current_run_id") or current.get("active_run_id") or current.get("run_id")
    if run_id:
        return project_root / ".flowpilot" / "runs" / str(run_id)
    return None


def run_state_path(run_root: Path) -> Path:
    return run_root / "router_state.json"


def new_run_state(run_id: str, run_root_rel: str) -> dict[str, Any]:
    return {
        "schema_version": RUN_STATE_SCHEMA,
        "run_id": run_id,
        "run_root": run_root_rel,
        "status": "controller_ready",
        "phase": "startup_intake",
        "holder": "controller",
        "pending_action": None,
        "manifest_check_requests": 0,
        "manifest_checks": 0,
        "ledger_check_requests": 0,
        "ledger_checks": 0,
        "prompt_deliveries": 0,
        "mail_deliveries": 0,
        "control_blockers": [],
        "resolved_control_blockers": [],
        "protocol_blockers": [],
        "gate_decisions": [],
        "active_control_blocker": None,
        "latest_control_blocker_path": None,
        "delivered_cards": [],
        "delivered_mail": [],
        "events": [],
        "flags": {
            "controller_core_loaded": True,
            **RUNTIME_FLAG_DEFAULTS,
            **{entry["flag"]: False for entry in SYSTEM_CARD_SEQUENCE},
            **{entry["flag"]: False for entry in MAIL_SEQUENCE},
            **{entry["flag"]: False for entry in EXTERNAL_EVENTS.values()},
        },
        "history": [],
    }


def load_run_state(project_root: Path, bootstrap_state: dict[str, Any] | None = None) -> tuple[dict[str, Any], Path] | tuple[None, None]:
    run_root = active_run_root(project_root, bootstrap_state)
    if run_root is None:
        return None, None
    path = run_state_path(run_root)
    if not path.exists():
        return None, run_root
    state = read_json(path)
    state.setdefault("flags", {})
    for flag, default in RUNTIME_FLAG_DEFAULTS.items():
        state["flags"].setdefault(flag, default)
    for entry in SYSTEM_CARD_SEQUENCE:
        state["flags"].setdefault(entry["flag"], False)
    for entry in MAIL_SEQUENCE:
        state["flags"].setdefault(entry["flag"], False)
    for event in EXTERNAL_EVENTS.values():
        state["flags"].setdefault(event["flag"], False)
    state.setdefault("history", [])
    state.setdefault("pending_action", None)
    state.setdefault("delivered_cards", [])
    state.setdefault("delivered_mail", [])
    state.setdefault("control_blockers", [])
    state.setdefault("resolved_control_blockers", [])
    state.setdefault("protocol_blockers", [])
    state.setdefault("gate_decisions", [])
    state.setdefault("active_control_blocker", None)
    state.setdefault("latest_control_blocker_path", None)
    state.setdefault("events", [])
    return state, run_root


def save_run_state(run_root: Path, state: dict[str, Any]) -> None:
    write_json(run_state_path(run_root), state)


def load_manifest_from_run(run_root: Path) -> dict[str, Any]:
    manifest_path = run_root / "runtime_kit" / "manifest.json"
    if not manifest_path.exists():
        manifest_path = runtime_kit_source() / "manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("schema_version") != PROMPT_MANIFEST_SCHEMA:
        raise RouterError("invalid prompt manifest schema")
    return manifest


def manifest_card(manifest: dict[str, Any], card_id: str) -> dict[str, Any]:
    cards = manifest.get("cards")
    if not isinstance(cards, list):
        raise RouterError("prompt manifest cards must be a list")
    for card in cards:
        if isinstance(card, dict) and card.get("id") == card_id:
            return card
    raise RouterError(f"card not found in prompt manifest: {card_id}")


def append_history(state: dict[str, Any], label: str, details: dict[str, Any] | None = None) -> None:
    history = state.setdefault("history", [])
    history.append({"at": utc_now(), "label": label, "details": details or {}})


def make_action(
    *,
    action_type: str,
    actor: str,
    label: str,
    summary: str,
    source: str = "router",
    allowed_reads: list[str] | None = None,
    allowed_writes: list[str] | None = None,
    card_id: str | None = None,
    mail_id: str | None = None,
    to_role: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    action: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "action_id": f"{label}:{utc_now()}",
        "action_type": action_type,
        "actor": actor,
        "source": source,
        "issued_by": "router",
        "label": label,
        "summary": summary,
        "allowed_reads": allowed_reads or [],
        "allowed_writes": allowed_writes or [],
        "created_at": utc_now(),
    }
    if card_id:
        action["card_id"] = card_id
        action["from"] = "system"
        action["issued_by"] = "router"
        action["delivered_by"] = "controller"
    if mail_id:
        action["mail_id"] = mail_id
        action["delivered_by"] = "controller"
    if to_role:
        action["to_role"] = to_role
    if extra:
        action.update(extra)
    if action.get("requires_user_dialog_display_confirmation") and "payload_template" not in action:
        display_kind = action.get("display_kind")
        display_text_sha256 = action.get("display_text_sha256")
        if isinstance(display_kind, str) and isinstance(display_text_sha256, str):
            action["payload_template"] = {
                "display_confirmation": {
                    "action_type": action_type,
                    "display_kind": display_kind,
                    "display_text_sha256": display_text_sha256,
                    "provenance": DISPLAY_CONFIRMATION_PROVENANCE,
                    "rendered_to": DISPLAY_CONFIRMATION_TARGET,
                }
            }
            action["payload_template_rule"] = (
                "First paste display_text exactly into the user dialog, then apply "
                "the action with this payload_template. Generated files, host UI "
                "updates, and display paths do not satisfy user-dialog display evidence."
            )
    resolved_recipient = str(action.get("to_role") or actor)
    action.setdefault("why_this_role", summary)
    action["next_step_contract"] = {
        "schema_version": "flowpilot.next_step_contract.v1",
        "controller_has_explicit_next": True,
        "action_type": action_type,
        "recipient_role": resolved_recipient,
        "controller_may_infer_next_from_chat": False,
        "controller_may_contact_unlisted_role": False,
        "controller_may_create_project_evidence": False,
        "sealed_body_reads_allowed": bool(action.get("sealed_body_reads_allowed", False)),
        "allowed_external_events": action.get("allowed_external_events", []),
        "postcondition": action.get("postcondition"),
    }
    return action


def _payload_contract(
    *,
    name: str,
    required_object: str,
    required_fields: list[str],
    optional_fields: list[str] | None = None,
    allowed_values: dict[str, list[Any]] | None = None,
    conditional_required_fields: dict[str, list[str]] | None = None,
    structural_requirements: list[str] | None = None,
    description: str,
    reviewer_check: str | None = None,
) -> dict[str, Any]:
    contract = {
        "schema_version": PAYLOAD_CONTRACT_SCHEMA,
        "name": name,
        "required_object": required_object,
        "required_fields": required_fields,
        "optional_fields": optional_fields or [],
        "conditional_required_fields": conditional_required_fields or {},
        "structural_requirements": structural_requirements or [],
        "allowed_values": allowed_values or {},
        "description": description,
        "controller_may_fill_missing_fields": False,
        "on_missing_or_ambiguous_payload": "ask_user_or_return_to_named_role; do_not_guess",
    }
    if reviewer_check:
        contract["reviewer_check"] = reviewer_check
    return contract


def _startup_answers_payload_contract() -> dict[str, Any]:
    return _payload_contract(
        name="startup_answers_with_optional_ai_interpretation_receipt",
        required_object="payload.startup_answers",
        required_fields=["background_agents", "scheduled_continuation", "display_surface", "provenance"],
        optional_fields=["payload.startup_answer_interpretation"],
        allowed_values={
            "startup_answers.background_agents": sorted(STARTUP_ANSWER_ENUMS["background_agents"]),
            "startup_answers.scheduled_continuation": sorted(STARTUP_ANSWER_ENUMS["scheduled_continuation"]),
            "startup_answers.display_surface": sorted(STARTUP_ANSWER_ENUMS["display_surface"]),
            "startup_answers.provenance": [
                STARTUP_ANSWER_PROVENANCE,
                STARTUP_ANSWER_INTERPRETATION_PROVENANCE,
            ],
            "startup_answer_interpretation.schema_version": [STARTUP_ANSWER_INTERPRETATION_SCHEMA],
            "startup_answer_interpretation.interpreted_by": ["controller", "bootloader"],
            "startup_answer_interpretation.interpretation_provenance": [STARTUP_ANSWER_INTERPRETATION_PROVENANCE],
            "startup_answer_interpretation.ambiguity_status": ["none"],
            "startup_answer_interpretation.interpreted_answers.background_agents": sorted(
                STARTUP_ANSWER_ENUMS["background_agents"]
            ),
            "startup_answer_interpretation.interpreted_answers.scheduled_continuation": sorted(
                STARTUP_ANSWER_ENUMS["scheduled_continuation"]
            ),
            "startup_answer_interpretation.interpreted_answers.display_surface": sorted(
                STARTUP_ANSWER_ENUMS["display_surface"]
            ),
        },
        conditional_required_fields={
            "when startup_answers.provenance=ai_interpreted_from_explicit_user_reply": [
                "startup_answer_interpretation.schema_version",
                "startup_answer_interpretation.raw_user_reply_text",
                "startup_answer_interpretation.interpreted_by",
                "startup_answer_interpretation.interpretation_provenance",
                "startup_answer_interpretation.ambiguity_status",
                "startup_answer_interpretation.interpreted_answers.background_agents",
                "startup_answer_interpretation.interpreted_answers.scheduled_continuation",
                "startup_answer_interpretation.interpreted_answers.display_surface",
            ],
        },
        description=(
            "Pass canonical enum answers. If the user's reply was natural language, the AI may interpret it into "
            "these fields only with a startup_answer_interpretation receipt that preserves the raw user reply and "
            "states ambiguity_status=none."
        ),
    )


def _display_surface_receipt_payload_contract() -> dict[str, Any]:
    return _payload_contract(
        name="display_surface_receipt",
        required_object="payload.display_confirmation",
        required_fields=[
            "display_confirmation.action_type",
            "display_confirmation.display_kind",
            "display_confirmation.display_text_sha256",
            "display_confirmation.provenance",
            "display_confirmation.rendered_to",
        ],
        optional_fields=["payload.display_surface_receipt"],
        allowed_values={
            "display_confirmation.provenance": [DISPLAY_CONFIRMATION_PROVENANCE],
            "display_confirmation.rendered_to": [DISPLAY_CONFIRMATION_TARGET],
            "display_surface_receipt.schema_version": [DISPLAY_SURFACE_RECEIPT_SCHEMA],
            "display_surface_receipt.actual_surface": ["chat_route_sign", "chat_route_sign_fallback", "cockpit"],
            "display_surface_receipt.host_display_surface_verified": [True],
        },
        conditional_required_fields={
            "when payload.display_surface_receipt is supplied": [
                "display_surface_receipt.schema_version",
                "display_surface_receipt.actual_surface",
            ],
            "when display_surface_receipt.actual_surface=cockpit": [
                "display_surface_receipt.host_display_surface_verified",
            ],
        },
        description=(
            "Confirm the router-provided route sign was displayed in the user dialog. If a native Cockpit or "
            "fallback display was attempted, include display_surface_receipt with the actual surface and host result."
        ),
        reviewer_check="Reviewer checks requested cockpit versus actual cockpit/fallback reality when Cockpit was requested.",
    )


def _role_slots_payload_contract() -> dict[str, Any]:
    return _payload_contract(
        name="role_slots_startup_receipt",
        required_object="payload",
        required_fields=[
            "background_agents_capability_status",
            "role_agents[].role_key",
            "role_agents[].agent_id",
            "role_agents[].spawn_result",
            "role_agents[].spawned_for_run_id",
            "role_agents[].spawned_after_startup_answers",
        ],
        optional_fields=["role_agents[].host_spawn_receipt"],
        allowed_values={
            "background_agents_capability_status": ["available"],
            "role_agents[].spawn_result": [ROLE_AGENT_SPAWN_RESULT],
            "role_agents[].host_spawn_receipt.source_kind": ["host_receipt"],
        },
        conditional_required_fields={
            "when role_agents[].host_spawn_receipt is supplied": [
                "role_agents[].host_spawn_receipt.source_kind",
                "role_agents[].host_spawn_receipt.spawned_for_run_id",
                "role_agents[].host_spawn_receipt.role_key",
                "role_agents[].host_spawn_receipt.agent_id",
            ],
        },
        structural_requirements=["Provide exactly one non-duplicate role agent record for each FlowPilot role key."],
        description="Record one fresh live host role agent per FlowPilot role when background agents were allowed.",
        reviewer_check="Reviewer checks live agent spawn freshness unless each slot carries a host receipt.",
    )


def _heartbeat_payload_contract(run_id: str, automation_id_hint: str) -> dict[str, Any]:
    return _payload_contract(
        name="heartbeat_host_automation_receipt",
        required_object="payload",
        required_fields=[
            "route_heartbeat_interval_minutes",
            "host_automation_id",
            "host_automation_verified",
            "host_automation_proof.source_kind",
            "host_automation_proof.run_id",
            "host_automation_proof.host_automation_id",
            "host_automation_proof.route_heartbeat_interval_minutes",
            "host_automation_proof.heartbeat_bound_to_current_run",
        ],
        allowed_values={
            "route_heartbeat_interval_minutes": [1],
            "host_automation_verified": [True],
            "host_automation_proof.source_kind": ["host_receipt"],
            "host_automation_proof.run_id": [run_id],
            "host_automation_proof.route_heartbeat_interval_minutes": [1],
            "host_automation_proof.heartbeat_bound_to_current_run": [True],
        },
        description="Bind the one-minute host heartbeat automation to this exact current run before startup fact review.",
        reviewer_check="Reviewer checks heartbeat host binding when scheduled continuation was requested.",
    )


def _resume_role_rehydration_payload_contract(
    run_state: dict[str, Any],
    contexts: list[dict[str, Any]],
) -> dict[str, Any]:
    del contexts
    return _payload_contract(
        name="resume_role_rehydration_receipt",
        required_object="payload",
        required_fields=[
            "background_agents_capability_status",
            "rehydrated_role_agents[].role_key",
            "rehydrated_role_agents[].agent_id",
            "rehydrated_role_agents[].rehydration_result",
            "rehydrated_role_agents[].rehydrated_for_run_id",
            "rehydrated_role_agents[].rehydrated_after_resume_tick_id",
            "rehydrated_role_agents[].spawned_after_resume_state_loaded",
            "rehydrated_role_agents[].core_prompt_path",
            "rehydrated_role_agents[].core_prompt_hash",
            "rehydrated_role_agents[].host_liveness_status",
            "rehydrated_role_agents[].liveness_decision",
            "rehydrated_role_agents[].resume_agent_attempted",
            "rehydrated_role_agents[].bounded_wait_result",
            "rehydrated_role_agents[].wait_agent_timeout_treated_as_active",
        ],
        allowed_values={
            "background_agents_capability_status": ["available"],
            "rehydrated_role_agents[].role_key": list(CREW_ROLE_KEYS),
            "rehydrated_role_agents[].rehydration_result": sorted(RESUME_ROLE_AGENT_RESULTS),
            "rehydrated_role_agents[].rehydrated_for_run_id": [run_state["run_id"]],
            "rehydrated_role_agents[].spawned_after_resume_state_loaded": [True],
            "rehydrated_role_agents[].host_liveness_status": sorted(ROLE_AGENT_HOST_LIVENESS_STATUSES),
            "rehydrated_role_agents[].liveness_decision": sorted(ROLE_AGENT_LIVENESS_DECISIONS),
            "rehydrated_role_agents[].resume_agent_attempted": [True],
            "rehydrated_role_agents[].bounded_wait_result": sorted(ROLE_AGENT_BOUNDED_WAIT_RESULTS),
            "rehydrated_role_agents[].wait_agent_timeout_treated_as_active": [False],
        },
        conditional_required_fields={
            "when role_rehydration_request[].role_memory_status=available": [
                "rehydrated_role_agents[].memory_packet_path",
                "rehydrated_role_agents[].memory_packet_hash",
                "rehydrated_role_agents[].memory_seeded_from_current_run",
            ],
            "when role_rehydration_request[].role_memory_status!=available": [
                "rehydrated_role_agents[].memory_missing_acknowledged",
                "rehydrated_role_agents[].replacement_seeded_from_common_run_context",
            ],
            "when rehydrated_role_agents[].role_key=project_manager": [
                "rehydrated_role_agents[].pm_resume_context_delivered",
            ],
        },
        structural_requirements=[
            "Provide exactly one non-duplicate rehydrated role agent record for each FlowPilot role key.",
            "Each record must match the corresponding role_rehydration_request path/hash fields.",
            "A wait_agent timeout must be recorded as timeout_unknown and must not justify live_agent_continuity_confirmed.",
            "missing, cancelled, unknown, or timeout_unknown host liveness must spawn a replacement from current-run memory instead of continuing to wait on the old role.",
        ],
        description="Restore or replace all six live FlowPilot role agents from current-run memory before PM resume decision.",
        reviewer_check="PM and reviewer checks use the written crew_rehydration_report before resume decisions.",
    )


def _pm_resume_decision_payload_contract(project_root: Path, run_root: Path) -> dict[str, Any]:
    pm_context = project_relative(project_root, _pm_prior_path_context_path(run_root))
    route_history = project_relative(project_root, _route_history_index_path(run_root))
    return _payload_contract(
        name="pm_resume_decision_role_output",
        required_object="role_output_body",
        required_fields=list(PM_RESUME_DECISION_REQUIRED_BODY_FIELDS),
        optional_fields=[
            "recovery_evidence",
            "role_freshness_verification",
            "packet_loop_continuation",
            "decision_rationale",
            "controller_reminder.controller_may_create_project_evidence",
            "controller_reminder.controller_may_approve_gates",
            "controller_reminder.controller_may_implement",
        ],
        allowed_values={
            "decision_owner": ["project_manager"],
            "decision": sorted(PM_RESUME_DECISION_ALLOWED_VALUES),
            "prior_path_context_review.reviewed": [True],
            "prior_path_context_review.source_paths": [[pm_context, route_history]],
            "prior_path_context_review.controller_summary_used_as_evidence": [False],
            "controller_reminder.controller_only": [True],
            "controller_reminder.controller_may_read_sealed_bodies": [False],
            "controller_reminder.controller_may_infer_from_chat_history": [False],
            "controller_reminder.controller_may_advance_or_close_route": [False],
            "controller_reminder.controller_may_create_project_evidence": [False],
        },
        conditional_required_fields={
            "when continuation/resume_reentry.json records ambiguous_state_blocks_controller_execution=true and decision=continue_current_packet_loop": [
                "explicit_recovery_evidence_recorded=true",
                "recovery_evidence",
            ],
            "when decision=close_after_final_ledger_and_terminal_replay": [
                "final_ledger_built_clean evidence",
                "final_backward_replay_passed evidence",
            ],
        },
        structural_requirements=[
            "Return the body through a role_output_envelope with decision_path and decision_hash.",
            "Cite exactly the current-run pm_prior_path_context.json and route_history_index.json in prior_path_context_review.source_paths.",
            "Use empty arrays explicitly when no completed, superseded, stale, blocked, or experimental history applies.",
        ],
        description=(
            "PM heartbeat/manual-resume recovery decision. This is a role-output body contract, "
            "not Controller-authored project evidence; Controller may only relay the envelope to the router."
        ),
    )


def _pm_parent_segment_decision_payload_contract(project_root: Path, run_root: Path) -> dict[str, Any]:
    pm_context = project_relative(project_root, _pm_prior_path_context_path(run_root))
    route_history = project_relative(project_root, _route_history_index_path(run_root))
    return _payload_contract(
        name="pm_parent_segment_decision_role_output",
        required_object="role_output_body",
        required_fields=list(PM_PARENT_SEGMENT_DECISION_REQUIRED_BODY_FIELDS),
        optional_fields=[
            "repair_node_id",
            "superseded_nodes",
            "stale_evidence_to_mark",
            "decision_rationale",
            "same_parent_replay_rerun_plan",
            "contract_self_check",
        ],
        allowed_values={
            "decision_owner": ["project_manager"],
            "decision": sorted(PM_PARENT_SEGMENT_DECISION_ALLOWED_VALUES),
            "prior_path_context_review.reviewed": [True],
            "prior_path_context_review.source_paths": [[pm_context, route_history]],
            "prior_path_context_review.controller_summary_used_as_evidence": [False],
        },
        conditional_required_fields={
            "when decision!=continue": [
                "decision_rationale",
                "stale_evidence_to_mark or superseded_nodes when affected evidence/nodes exist",
                "same_parent_replay_rerun_plan",
            ],
        },
        structural_requirements=[
            "Return the body through a role_output_envelope with decision_path and decision_hash.",
            "Cite exactly the current-run pm_prior_path_context.json and route_history_index.json in prior_path_context_review.source_paths.",
            "Use empty arrays explicitly when no completed, superseded, stale, blocked, or experimental history applies.",
            "Only decision=continue may close the active parent node; all other decisions require route mutation and same-parent replay rerun.",
        ],
        description=(
            "PM parent-segment decision after reviewer backward replay. This is a role-output body "
            "contract; Controller may only relay the envelope to the router."
        ),
    )


def _pm_terminal_closure_payload_contract(project_root: Path, run_root: Path) -> dict[str, Any]:
    pm_context = project_relative(project_root, _pm_prior_path_context_path(run_root))
    route_history = project_relative(project_root, _route_history_index_path(run_root))
    return _payload_contract(
        name="pm_terminal_closure_decision_role_output",
        required_object="role_output_body",
        required_fields=list(PM_TERMINAL_CLOSURE_DECISION_REQUIRED_BODY_FIELDS),
        optional_fields=[
            "final_report",
            "closure_rationale",
            "lifecycle_reconciliation",
            "lifecycle_reconciliation.final_route_wide_gate_ledger_clean",
            "lifecycle_reconciliation.terminal_backward_replay_passed",
            "lifecycle_reconciliation.task_completion_projection_ready_for_pm_terminal_closure",
            "lifecycle_reconciliation.execution_frontier_current",
            "lifecycle_reconciliation.crew_ledger_current",
            "lifecycle_reconciliation.continuation_binding_current",
            "lifecycle_reconciliation.current_ledgers_clean",
            "contract_self_check",
        ],
        allowed_values={
            "approved_by_role": ["project_manager"],
            "decision": sorted(PM_TERMINAL_CLOSURE_DECISION_ALLOWED_VALUES),
            "prior_path_context_review.reviewed": [True],
            "prior_path_context_review.source_paths": [[pm_context, route_history]],
            "prior_path_context_review.controller_summary_used_as_evidence": [False],
            "lifecycle_reconciliation.final_route_wide_gate_ledger_clean": [True],
            "lifecycle_reconciliation.terminal_backward_replay_passed": [True],
            "lifecycle_reconciliation.task_completion_projection_ready_for_pm_terminal_closure": [True],
            "lifecycle_reconciliation.execution_frontier_current": [True],
            "lifecycle_reconciliation.crew_ledger_current": [True],
            "lifecycle_reconciliation.continuation_binding_current": [True],
            "lifecycle_reconciliation.current_ledgers_clean": [True],
        },
        structural_requirements=[
            "Return the body through a role_output_envelope with decision_path and decision_hash.",
            "Cite exactly the current-run pm_prior_path_context.json and route_history_index.json in prior_path_context_review.source_paths.",
            "Use empty arrays explicitly when no completed, superseded, stale, blocked, or experimental history applies.",
            "Approve closure only after clean final ledger, passed terminal backward replay, current completion projection, clean lifecycle ledgers, and continuation binding are present.",
        ],
        description=(
            "PM terminal closure approval. This is a role-output body contract; Controller may only "
            "relay the envelope to the router and must not infer closure from chat history."
        ),
    )


def _pm_model_miss_triage_payload_contract(project_root: Path, run_root: Path) -> dict[str, Any]:
    return _payload_contract(
        name="pm_model_miss_triage_decision_role_output",
        required_object="role_output_body",
        required_fields=list(PM_MODEL_MISS_TRIAGE_REQUIRED_BODY_FIELDS),
        optional_fields=[
            "officer_request_refs",
            "officer_report_refs",
            "same_class_findings_summary",
            "candidate_repairs_considered",
            "minimal_sufficient_repair_recommendation",
            "rejected_larger_repairs",
            "rejected_smaller_repairs",
            "post_repair_model_checks_required",
            "decision_rationale",
        ],
        allowed_values={
            "decided_by_role": ["project_manager"],
            "decision": sorted(PM_MODEL_MISS_TRIAGE_DECISION_ALLOWED_VALUES),
            "same_class_findings_reviewed": [True, False],
            "repair_recommendation_reviewed": [True, False],
        },
        conditional_required_fields={
            "when decision=proceed_with_model_backed_repair": [
                "flowguard_capability.can_model_bug_class=true",
                "officer_report_refs[].report_path",
                "officer_report_refs[].report_hash",
                "same_class_findings_reviewed=true",
                "repair_recommendation_reviewed=true",
                "candidate_repairs_considered",
                "minimal_sufficient_repair_recommendation",
                "post_repair_model_checks_required",
            ],
            "when decision=out_of_scope_not_modelable": [
                "flowguard_capability.can_model_bug_class=false",
                "flowguard_capability.incapability_reason",
                "selected_next_action",
                "why_repair_may_start",
            ],
        },
        structural_requirements=[
            "Return the body through a role_output_envelope with decision_path and decision_hash.",
            "Do not start pm.review_repair until this decision either authorizes a model-backed repair or records why FlowGuard cannot model the bug class.",
            "For model-backed repair, officer reports must include old_model_miss_reason, bug_class_definition, same_class_findings, coverage_added, candidate_repairs, minimal_sufficient_repair_recommendation, rejected_larger_repairs, rejected_smaller_repairs, post_repair_model_checks_required, and residual_blindspots.",
            "PM selects the repair path; officer reports provide model evidence and repair recommendations but do not approve route mutation by themselves.",
        ],
        description=(
            "PM model-miss triage decision for reviewer blockers. This closes the obligation to ask why "
            "FlowGuard missed the bug class before normal repair planning can start."
        ),
    )


def _pm_decision_payload_contract_for_card(project_root: Path, run_root: Path, card_id: str) -> dict[str, Any] | None:
    if card_id == "pm.resume_decision":
        return _pm_resume_decision_payload_contract(project_root, run_root)
    if card_id == "pm.model_miss_triage":
        return _pm_model_miss_triage_payload_contract(project_root, run_root)
    if card_id == "pm.parent_segment_decision":
        return _pm_parent_segment_decision_payload_contract(project_root, run_root)
    if card_id == "pm.closure":
        return _pm_terminal_closure_payload_contract(project_root, run_root)
    return None


def _role_decision_payload_contract_for_events(
    project_root: Path, run_root: Path, allowed_events: list[str]
) -> dict[str, Any] | None:
    if allowed_events == ["pm_resume_recovery_decision_returned"]:
        return _pm_resume_decision_payload_contract(project_root, run_root)
    if allowed_events == [PM_MODEL_MISS_TRIAGE_DECISION_EVENT]:
        return _pm_model_miss_triage_payload_contract(project_root, run_root)
    if allowed_events == ["pm_records_parent_segment_decision"]:
        return _pm_parent_segment_decision_payload_contract(project_root, run_root)
    if allowed_events == ["pm_approves_terminal_closure"]:
        return _pm_terminal_closure_payload_contract(project_root, run_root)
    return None


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _control_blocker_error_code(message: str) -> str:
    cleaned: list[str] = []
    for char in message.lower():
        if char.isalnum():
            cleaned.append(char)
        elif cleaned and cleaned[-1] != "_":
            cleaned.append("_")
    code = "".join(cleaned).strip("_")
    return code[:96] or "router_hard_rejection"


def _project_relative_if_possible(project_root: Path, path: Path) -> str:
    try:
        return project_relative(project_root, path)
    except RouterError:
        return str(path)


def _payload_source_paths(project_root: Path, run_root: Path, payload: dict[str, Any] | None) -> dict[str, str]:
    source_paths = {
        "router_state": project_relative(project_root, run_state_path(run_root)),
    }
    packet_ledger = run_root / "packet_ledger.json"
    if packet_ledger.exists():
        source_paths["packet_ledger"] = project_relative(project_root, packet_ledger)
    if not isinstance(payload, dict):
        return source_paths
    for key in (
        "body_path",
        "report_path",
        "decision_path",
        "result_body_path",
        "packet_envelope_path",
        "result_envelope_path",
        "packet_index_path",
        "path",
    ):
        raw = payload.get(key)
        if not raw:
            continue
        candidate = resolve_project_path(project_root, str(raw))
        source_paths[key] = _project_relative_if_possible(project_root, candidate)
    return source_paths


def _control_payload_public_view(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    forbidden_body_keys = {
        "blockers",
        "checks",
        "commands",
        "decision",
        "decision_body",
        "evidence",
        "findings",
        "passed",
        "direct_material_sources_checked",
        "packet_matches_checked_sources",
        "pm_ready",
        "recommendations",
        "repair_instructions",
        "report_body",
        "result_body",
    }
    public: dict[str, Any] = {}
    for key, value in payload.items():
        if key in forbidden_body_keys:
            public[key] = "[redacted: role body field was controller-visible]"
            continue
        if key.endswith("_path") or key.endswith("_hash") or key in {
            "packet_id",
            "route_id",
            "node_id",
            "role",
            "from_role",
            "to_role",
            "expected_role",
            "completed_by_role",
            "reviewed_by_role",
            "controller_visibility",
            "chat_response_body_allowed",
        }:
            public[key] = _json_safe(value)
    return public


def _infer_responsible_role(event: str | None, payload: dict[str, Any] | None, message: str) -> str:
    if isinstance(payload, dict):
        for key in ("reviewed_by_role", "completed_by_role", "from_role", "to_role", "role", "expected_role"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
    if event:
        if event.startswith("reviewer_") or "reviewer" in event:
            return "human_like_reviewer"
        if event.startswith("worker_") or "worker_" in event:
            if "worker_b" in message or "worker-b" in message:
                return "worker_b"
            return "worker_a"
        if event.startswith("product_officer_"):
            return "product_flowguard_officer"
        if event.startswith("process_officer_"):
            return "process_flowguard_officer"
        if event.startswith("pm_"):
            return "project_manager"
    lowered = message.lower()
    if "product_flowguard_officer" in lowered:
        return "product_flowguard_officer"
    if "process_flowguard_officer" in lowered:
        return "process_flowguard_officer"
    if "human_like_reviewer" in lowered or "reviewer" in lowered:
        return "human_like_reviewer"
    if "project_manager" in lowered or message.startswith("PM "):
        return "project_manager"
    return "project_manager"


def _classify_control_blocker(message: str, *, event: str | None = None, action_type: str | None = None) -> str:
    del action_type
    lowered = message.lower()
    fatal_markers = (
        "private role-to-role",
        "controller relay violation",
        "body was read by controller",
        "body was executed by controller",
        "body_was_read_by_controller",
        "body_was_executed_by_controller",
        "controller read",
        "controller executes",
        "contaminated envelope",
        "leaked role body fields to controller",
        "controller relay envelope hash mismatch",
    )
    if any(marker in lowered for marker in fatal_markers):
        return "fatal_protocol_violation"
    if (
        event
        and (event.startswith("reviewer_") or "reviewer" in event)
        and any(
            marker in lowered
            for marker in (
                "result_body_not_opened",
                "packet_body_not_opened",
                "packet_ledger_missing_packet_body_open_receipt",
                "packet_ledger_missing_result_body_open_receipt",
                "body was not opened by target role after controller relay",
            )
        )
    ):
        return "control_plane_reissue"
    pm_markers = (
        "controller-origin",
        "wrong role",
        "wrong-role",
        "reviewer pass rejected by packet audit",
        "current-node result failed pre-relay packet runtime audit",
        "packet group reviewer audit failed",
        "body was not opened",
        "unopened",
        "stale",
        "unresolved",
        "final ledger",
        "route mutation",
        "parent segment",
        "ambiguous",
        "repair decision",
        "packet body hash mismatch",
        "result body hash mismatch",
        "result_completed_by_wrong_role",
        "completed_agent_id",
        "packet_ledger_missing_result_absorption",
        "packet_ledger_missing_packet_body_open_receipt",
    )
    if any(marker in lowered for marker in pm_markers):
        return "pm_repair_decision_required"
    if event in {
        "current_node_reviewer_passes_result",
        "reviewer_reports_material_sufficient",
        "reviewer_reports_material_insufficient",
        "reviewer_passes_research_direct_source_check",
        "reviewer_passes_route_check",
        "reviewer_final_backward_replay_passed",
    }:
        return "control_plane_reissue"
    reissue_markers = (
        "requires a file-backed body path",
        "requires a body/report/decision hash",
        "role body path is missing",
        "role body hash mismatch",
        "must be reviewed_by_role",
        "must explicitly pass",
        "gate report must",
        "requires direct_material_sources_checked",
        "requires packet_matches_checked_sources",
        "requires pm_ready",
        "must route to",
        "requires packet_id",
        "requires packet envelope",
        "missing source paths",
    )
    if any(marker in lowered for marker in reissue_markers):
        return "control_plane_reissue"
    return "pm_repair_decision_required"


def _should_materialize_control_blocker(
    message: str,
    *,
    event: str | None = None,
    action_type: str | None = None,
    payload: dict[str, Any] | None = None,
) -> bool:
    lowered = message.lower()
    if lowered.startswith("event ") and " requires " in lowered:
        return False
    if "run 'next' before applying" in lowered or "pending action is" in lowered:
        return False
    if "requires a file-backed body path" in lowered and not payload:
        return False
    material_markers = (
        "requires a file-backed body path",
        "requires a body/report/decision hash",
        "role body path is missing",
        "role body hash mismatch",
        "leaked role body fields to controller",
        "must be reviewed_by_role",
        "must explicitly pass",
        "gate report must",
        "requires direct_material_sources_checked",
        "requires packet_matches_checked_sources",
        "requires pm_ready",
        "packet group reviewer audit failed",
        "reviewer pass rejected by packet audit",
        "current-node result failed pre-relay packet runtime audit",
        "controller-origin",
        "wrong role",
        "wrong-role",
        "result_completed_by_wrong_role",
        "completed_agent_id",
        "packet_ledger_missing_result_absorption",
        "packet_ledger_missing_packet_body_open_receipt",
        "missing controller relay signature",
        "envelope was not delivered via controller",
        "controller did not sign",
        "private role-to-role",
        "controller relay violation",
        "contaminated envelope",
        "body was not opened",
        "unopened",
        "packet body hash mismatch",
        "result body hash mismatch",
        "controller relay envelope hash mismatch",
    )
    if any(marker in lowered for marker in material_markers):
        return True
    if action_type in {
        "relay_material_scan_packets",
        "relay_material_scan_results_to_reviewer",
        "relay_research_packet",
        "relay_research_result_to_reviewer",
        "relay_current_node_packet",
        "relay_current_node_result_to_reviewer",
    }:
        return True
    if isinstance(payload, dict) and any(
        payload.get(key)
        for key in (
            "body_path",
            "body_hash",
            "report_path",
            "report_hash",
            "decision_path",
            "decision_hash",
            "result_body_path",
            "result_body_hash",
        )
    ):
        return event is not None and (
            event.startswith("reviewer_")
            or event.startswith("process_officer_")
            or event.startswith("product_officer_")
            or event
            in {
                "current_node_reviewer_passes_result",
                "pm_resume_recovery_decision_returned",
                PM_MODEL_MISS_TRIAGE_DECISION_EVENT,
                "pm_records_parent_segment_decision",
            }
        )
    return False


def _skill_observation_reminder(
    message: str,
    *,
    event: str | None = None,
    action_type: str | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    lowered = message.lower()
    suggested_kind = "controller_compensation"
    if "route" in lowered or "frontier" in lowered:
        suggested_kind = "router_state_gap"
    elif "ledger" in lowered:
        suggested_kind = "ledger_gap"
    elif "display_plan" in lowered or "visible plan" in lowered:
        suggested_kind = "display_projection_gap"
    elif "heartbeat" in lowered or "pause" in lowered or "resume" in lowered:
        suggested_kind = "heartbeat_gap"
    elif "schema" in lowered or "field" in lowered or "hash" in lowered or "path" in lowered:
        suggested_kind = "schema_gap"
    return {
        "schema_version": "flowpilot.skill_observation_reminder.v1",
        "should_consider_recording": True,
        "reason": "router_control_plane_exception",
        "originating_event": event,
        "originating_action_type": action_type,
        "handling_lane": category,
        "suggested_kind": suggested_kind,
        "summary": message,
        "write_path": ".flowpilot/runs/<run_id>/flowpilot_skill_improvement_report.json",
        "record_only_if": "This reflects a FlowPilot skill/protocol/router weakness, not ordinary project work.",
        "do_not_include": [
            "sealed packet bodies",
            "sealed result bodies",
            "private role reasoning",
            "secrets",
        ],
    }


def _control_blocker_allowed_resolution_events(category: str, event: str | None) -> list[str]:
    if category == "control_plane_reissue" and event:
        return [event]
    if category in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES:
        return [PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT]
    return sorted(EXTERNAL_EVENTS)


def _control_blocker_policy(category: str, *, responsible_role: str, event: str | None) -> dict[str, Any]:
    if category == "control_plane_reissue":
        target_role = responsible_role
        instruction = (
            f"Deliver the sealed repair packet envelope to `{target_role}` and request a same-role reissue of the "
            "rejected control-plane output. Controller may route the packet path and hash only."
        )
        allowed = [
            "read this control blocker artifact",
            "deliver sealed_repair_packet_path and sealed_repair_packet_hash to the responsible role",
            "tell the responsible role to reissue the same control-plane output",
        ]
        forbidden = [
            "open sealed packet/result/report bodies",
            "infer project status from chat history",
            "ask a worker to change project substance",
            "convert the router rejection into PM-owned evidence",
        ]
        pm_required = False
    elif category == "fatal_protocol_violation":
        target_role = "project_manager"
        instruction = (
            "Stop normal route work and deliver this control blocker to `project_manager` for escalation. "
            "Controller may route the sealed repair packet envelope only and must not repair the route from chat."
        )
        allowed = [
            "read this control blocker artifact",
            "deliver sealed_repair_packet_path and sealed_repair_packet_hash to project_manager",
            "wait for an explicit PM or user recovery decision",
        ]
        forbidden = [
            "open sealed packet/result/report bodies",
            "contact the worker directly",
            "advance, close, or mutate the route",
            "treat controller-visible leaked content as evidence",
        ]
        pm_required = True
    else:
        target_role = "project_manager"
        instruction = (
            "Deliver the sealed repair packet envelope to `project_manager` for a repair decision. Controller must "
            "not decide whether the work is substantively acceptable and must not inspect or restate the repair details."
        )
        allowed = [
            "read this control blocker artifact",
            "deliver sealed_repair_packet_path and sealed_repair_packet_hash to project_manager",
            "quote blocker_id, error_code, handling_lane, and target_role",
        ]
        forbidden = [
            "open sealed packet/result/report bodies",
            "contact the worker directly about project repair",
            "summarize reviewer or worker body content",
            "advance route state from the rejected event",
        ]
        pm_required = True
    return {
        "target_role": target_role,
        "pm_decision_required": pm_required,
        "controller_instruction": instruction,
        "controller_allowed_actions": allowed,
        "controller_forbidden_actions": forbidden,
        "allowed_resolution_events": _control_blocker_allowed_resolution_events(category, event),
    }


def _write_control_blocker_repair_packet(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    blocker_id: str,
    category: str,
    target_role: str,
    responsible_role: str,
    error_message: str,
    event: str | None,
    action_type: str | None,
    payload: dict[str, Any] | None,
) -> dict[str, str]:
    packet_path = run_root / "control_blocks" / f"{blocker_id}.sealed_repair_packet.json"
    packet = {
        "schema_version": CONTROL_BLOCKER_REPAIR_PACKET_SCHEMA,
        "blocker_id": blocker_id,
        "run_id": run_state.get("run_id"),
        "body_visibility": "sealed_router_repair_details_for_target_role",
        "target_role": target_role,
        "responsible_role_for_reissue": responsible_role if category == "control_plane_reissue" else None,
        "handling_lane": category,
        "originating_event": event,
        "originating_action_type": action_type,
        "error_code": _control_blocker_error_code(error_message),
        "error_message": error_message,
        "source_paths": _payload_source_paths(project_root, run_root, payload),
        "payload_envelope_public_view": _control_payload_public_view(payload),
        "controller_may_read_body": False,
        "controller_may_repair_from_this_packet": False,
        "target_role_repair_instruction": (
            "Inspect this sealed packet, fix the rejected control-plane output, and reissue the router event named "
            "in allowed_resolution_events. Do not ask Controller to infer or patch the body."
        ),
        "allowed_resolution_events": _control_blocker_allowed_resolution_events(category, event),
        "created_at": utc_now(),
    }
    write_json(packet_path, packet)
    return {
        "sealed_repair_packet_path": project_relative(project_root, packet_path),
        "sealed_repair_packet_hash": hashlib.sha256(packet_path.read_bytes()).hexdigest(),
    }


def _supersede_prior_control_blockers(
    run_root: Path,
    *,
    blocker_id: str,
    category: str,
    event: str | None,
    action_type: str | None,
) -> None:
    control_root = run_root / "control_blocks"
    if not control_root.exists():
        return
    superseded_at = utc_now()
    for path in sorted(control_root.glob("*.json")):
        record = read_json_if_exists(path)
        if record.get("schema_version") != CONTROL_BLOCKER_SCHEMA:
            continue
        if record.get("resolution_status") or record.get("blocker_id") == blocker_id:
            continue
        if record.get("handling_lane") != category:
            continue
        if record.get("originating_event") != event or record.get("originating_action_type") != action_type:
            continue
        record["resolution_status"] = "superseded_by_newer_control_blocker"
        record["superseded_by_blocker_id"] = blocker_id
        record["resolved_at"] = superseded_at
        record["resolution_note"] = "A newer router rejection for the same control-plane event replaced this pending repair packet."
        write_json(path, record)


def _write_control_blocker(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    source: str,
    error_message: str,
    event: str | None = None,
    action_type: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = _classify_control_blocker(error_message, event=event, action_type=action_type)
    if category not in CONTROL_BLOCKER_LANES:
        category = "pm_repair_decision_required"
    responsible_role = _infer_responsible_role(event, payload, error_message)
    policy = _control_blocker_policy(category, responsible_role=responsible_role, event=event)
    index = len(run_state.setdefault("control_blockers", [])) + 1
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    blocker_id = f"control-blocker-{index:04d}-{stamp}"
    artifact_path = run_root / "control_blocks" / f"{blocker_id}.json"
    artifact_rel = project_relative(project_root, artifact_path)
    repair_packet = _write_control_blocker_repair_packet(
        project_root,
        run_root,
        run_state,
        blocker_id=blocker_id,
        category=category,
        target_role=policy["target_role"],
        responsible_role=responsible_role,
        error_message=error_message,
        event=event,
        action_type=action_type,
        payload=payload,
    )
    record = {
        "schema_version": CONTROL_BLOCKER_SCHEMA,
        "blocker_id": blocker_id,
        "run_id": run_state.get("run_id"),
        "created_at": utc_now(),
        "source": source,
        "originating_event": event,
        "originating_action_type": action_type,
        "handling_lane": category,
        "error_code": _control_blocker_error_code(error_message),
        "controller_visible_summary": "Router rejected a control-plane payload. Deliver the sealed repair packet to the target role.",
        "blocker_artifact_path": artifact_rel,
        "sealed_repair_packet_path": repair_packet["sealed_repair_packet_path"],
        "sealed_repair_packet_hash": repair_packet["sealed_repair_packet_hash"],
        "responsible_role_for_reissue": responsible_role if category == "control_plane_reissue" else None,
        "target_role": policy["target_role"],
        "pm_decision_required": policy["pm_decision_required"],
        "controller_instruction": policy["controller_instruction"],
        "controller_allowed_actions": policy["controller_allowed_actions"],
        "controller_forbidden_actions": policy["controller_forbidden_actions"],
        "allowed_resolution_events": policy["allowed_resolution_events"],
        "sealed_body_read_by_controller_allowed": False,
        "controller_history_is_evidence": False,
        "delivery_status": "pending",
        "skill_observation_reminder": _skill_observation_reminder(
            "Control-plane payload was rejected and a sealed repair packet was issued for the target role.",
            event=event,
            action_type=action_type,
            category=category,
        ),
    }
    write_json(artifact_path, record)
    _supersede_prior_control_blockers(
        run_root,
        blocker_id=blocker_id,
        category=category,
        event=event,
        action_type=action_type,
    )
    active = {
        "blocker_id": blocker_id,
        "handling_lane": category,
        "blocker_artifact_path": artifact_rel,
        "target_role": policy["target_role"],
        "responsible_role_for_reissue": record["responsible_role_for_reissue"],
        "pm_decision_required": policy["pm_decision_required"],
        "delivery_status": "pending",
        "sealed_repair_packet_path": repair_packet["sealed_repair_packet_path"],
        "sealed_repair_packet_hash": repair_packet["sealed_repair_packet_hash"],
        "originating_event": event,
        "originating_action_type": action_type,
        "created_at": record["created_at"],
    }
    run_state["active_control_blocker"] = active
    run_state["latest_control_blocker_path"] = artifact_rel
    run_state["control_blockers"].append(active)
    run_state["pending_action"] = None
    append_history(
        run_state,
        "router_recorded_control_blocker",
        {
            "blocker_id": blocker_id,
            "handling_lane": category,
            "target_role": policy["target_role"],
            "originating_event": event,
            "originating_action_type": action_type,
        },
    )
    _sync_control_plane_indexes(project_root, run_root, run_state)
    save_run_state(run_root, run_state)
    return record


def _control_blocker_record(project_root: Path, active: dict[str, Any]) -> dict[str, Any]:
    raw_path = active.get("blocker_artifact_path")
    if not raw_path:
        return active
    path = resolve_project_path(project_root, str(raw_path))
    if not path.exists():
        return active
    return read_json(path)


def _control_blocker_summary(record: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "blocker_id",
        "handling_lane",
        "blocker_artifact_path",
        "target_role",
        "responsible_role_for_reissue",
        "pm_decision_required",
        "delivery_status",
        "sealed_repair_packet_path",
        "sealed_repair_packet_hash",
        "originating_event",
        "originating_action_type",
        "created_at",
        "delivered_to_role",
        "delivered_at",
        "resolution_status",
        "resolved_by_event",
        "resolved_at",
        "pm_repair_decision_status",
        "pm_repair_decision_path",
        "pm_repair_decision_hash",
        "pm_repair_rerun_target",
        "repair_transaction_id",
        "repair_transaction_path",
        "repair_outcome_table",
        "allowed_resolution_events",
    )
    return {field: record.get(field) for field in fields if field in record}


def _sync_protocol_blocker_index(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    blockers: list[dict[str, Any]] = []
    blocker_root = run_root / "blockers"
    if blocker_root.exists():
        for path in sorted(blocker_root.glob("*.json")):
            record = read_json_if_exists(path)
            blockers.append(
                {
                    "path": project_relative(project_root, path),
                    "blocker_id": record.get("blocker_id") or path.stem,
                    "blocker_type": record.get("blocker_type"),
                    "status": record.get("status"),
                    "registered_at": record.get("registered_at") or utc_now(),
                }
            )
    run_state["protocol_blockers"] = blockers


def _sync_control_plane_indexes(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    summaries: list[dict[str, Any]] = []
    resolved: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None
    control_root = run_root / "control_blocks"
    if control_root.exists():
        for path in sorted(control_root.glob("*.json")):
            record = read_json_if_exists(path)
            if record.get("schema_version") != CONTROL_BLOCKER_SCHEMA:
                continue
            summary = _control_blocker_summary(record)
            summaries.append(summary)
            if record.get("resolution_status"):
                resolved.append(summary)
            else:
                active = summary
    run_state["control_blockers"] = summaries
    run_state["resolved_control_blockers"] = resolved
    run_state["active_control_blocker"] = active
    run_state["latest_control_blocker_path"] = active.get("blocker_artifact_path") if active else None
    _sync_protocol_blocker_index(project_root, run_root, run_state)
    _write_repair_transaction_index(project_root, run_root, run_state)


def _next_control_blocker_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    active = run_state.get("active_control_blocker")
    if not isinstance(active, dict):
        return None
    record = _control_blocker_record(project_root, active)
    artifact_rel = str(record.get("blocker_artifact_path") or active.get("blocker_artifact_path") or "")
    if not artifact_rel:
        return None
    if record.get("delivery_status") != "delivered":
        lane = str(record.get("handling_lane") or active.get("handling_lane") or "pm_repair_decision_required")
        target_role = str(record.get("target_role") or active.get("target_role") or "project_manager")
        return make_action(
            action_type="handle_control_blocker",
            actor="controller",
            label=f"controller_handles_{lane}_control_blocker",
            summary=f"Deliver router control blocker {record.get('blocker_id')} sealed repair packet envelope to {target_role}.",
            allowed_reads=[artifact_rel, project_relative(project_root, run_state_path(run_root))],
            allowed_writes=[
                project_relative(project_root, run_state_path(run_root)),
                project_relative(project_root, run_root / "control_blocks" / "control_blocker_delivery_ledger.json"),
            ],
            to_role=target_role,
            extra={
                "blocker_id": record.get("blocker_id"),
                "blocker_artifact_path": artifact_rel,
                "sealed_repair_packet_path": record.get("sealed_repair_packet_path"),
                "sealed_repair_packet_hash": record.get("sealed_repair_packet_hash"),
                "handling_lane": lane,
                "pm_decision_required": bool(record.get("pm_decision_required")),
                "responsible_role_for_reissue": record.get("responsible_role_for_reissue"),
                "repair_transaction_id": record.get("repair_transaction_id"),
                "repair_outcome_table": record.get("repair_outcome_table"),
                "controller_instruction": record.get("controller_instruction"),
                "controller_allowed_actions": record.get("controller_allowed_actions") or [],
                "controller_forbidden_actions": record.get("controller_forbidden_actions") or [],
                "sealed_body_reads_allowed": False,
                "controller_history_is_evidence": False,
                "allowed_resolution_events": record.get("allowed_resolution_events") or sorted(EXTERNAL_EVENTS),
                "repair_details_visibility": "sealed_to_target_role_not_controller",
                "skill_observation_reminder": record.get("skill_observation_reminder"),
            },
        )
    return make_action(
        action_type="await_role_decision",
        actor="controller",
        label="controller_waits_for_control_blocker_resolution",
        summary="A router control blocker has been delivered. Controller must wait for the target role's corrected event or PM recovery decision.",
        allowed_reads=[artifact_rel, project_relative(project_root, run_state_path(run_root))],
        allowed_writes=[project_relative(project_root, run_state_path(run_root))],
        extra={
            "allowed_external_events": record.get("allowed_resolution_events") or sorted(EXTERNAL_EVENTS),
            "blocker_artifact_path": artifact_rel,
            "repair_transaction_id": record.get("repair_transaction_id"),
            "repair_outcome_table": record.get("repair_outcome_table"),
        },
    )


def _mark_control_blocker_delivered(project_root: Path, run_root: Path, run_state: dict[str, Any], pending: dict[str, Any]) -> None:
    artifact_rel = str(pending.get("blocker_artifact_path") or "")
    if not artifact_rel:
        raise RouterError("control blocker action is missing blocker_artifact_path")
    artifact_path = resolve_project_path(project_root, artifact_rel)
    record = read_json(artifact_path)
    delivered_at = utc_now()
    target_role = str(pending.get("to_role") or record.get("target_role") or "project_manager")
    record["delivery_status"] = "delivered"
    record["delivered_by"] = "controller"
    record["delivered_to_role"] = target_role
    record["delivered_at"] = delivered_at
    write_json(artifact_path, record)
    active = run_state.get("active_control_blocker")
    if isinstance(active, dict) and active.get("blocker_id") == record.get("blocker_id"):
        active["delivery_status"] = "delivered"
        active["delivered_to_role"] = target_role
        active["delivered_at"] = delivered_at
    ledger_path = run_root / "control_blocks" / "control_blocker_delivery_ledger.json"
    ledger = read_json_if_exists(ledger_path) or {"schema_version": "flowpilot.control_blocker_delivery_ledger.v1", "deliveries": []}
    ledger.setdefault("deliveries", []).append(
        {
            "blocker_id": record.get("blocker_id"),
            "blocker_artifact_path": artifact_rel,
            "handling_lane": record.get("handling_lane"),
            "sealed_repair_packet_path": record.get("sealed_repair_packet_path"),
            "sealed_repair_packet_hash": record.get("sealed_repair_packet_hash"),
            "delivered_by": "controller",
            "delivered_to_role": target_role,
            "delivered_at": delivered_at,
        }
    )
    ledger["updated_at"] = delivered_at
    write_json(ledger_path, ledger)
    _sync_control_plane_indexes(project_root, run_root, run_state)


def _validate_model_miss_officer_report_refs(project_root: Path, decision: dict[str, Any]) -> list[dict[str, Any]]:
    refs = decision.get("officer_report_refs")
    if not isinstance(refs, list) or not refs:
        raise RouterError("model-backed repair requires non-empty officer_report_refs")
    checked: list[dict[str, Any]] = []
    for index, ref in enumerate(refs):
        if not isinstance(ref, dict):
            raise RouterError("officer_report_refs entries must be objects")
        report_path = str(ref.get("report_path") or ref.get("path") or "").strip()
        report_hash = str(ref.get("report_hash") or ref.get("hash") or "").strip()
        if not report_path:
            raise RouterError("officer_report_refs[].report_path is required")
        if not report_hash:
            raise RouterError("officer_report_refs[].report_hash is required")
        path = resolve_project_path(project_root, report_path)
        if not path.exists():
            raise RouterError(f"officer model-miss report path does not exist: {report_path}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != report_hash:
            raise RouterError(f"officer model-miss report hash mismatch for {report_path}")
        report = read_json(path)
        missing = [
            field
            for field in MODEL_MISS_OFFICER_REPORT_REQUIRED_FIELDS
            if field not in report or report.get(field) is None
        ]
        if missing:
            raise RouterError(
                "officer model-miss report is missing required fields: "
                + ", ".join(missing)
            )
        if not isinstance(report.get("same_class_findings"), list):
            raise RouterError("officer model-miss report requires same_class_findings list")
        if not isinstance(report.get("candidate_repairs"), list) or not report.get("candidate_repairs"):
            raise RouterError("officer model-miss report requires non-empty candidate_repairs")
        if not isinstance(report.get("minimal_sufficient_repair_recommendation"), dict):
            raise RouterError("officer model-miss report requires minimal_sufficient_repair_recommendation object")
        contract_self_check = report.get("contract_self_check")
        if not isinstance(contract_self_check, dict):
            raise RouterError("officer model-miss report requires contract_self_check")
        if contract_self_check.get("all_required_fields_present") is not True:
            raise RouterError("officer model-miss report requires contract_self_check.all_required_fields_present=true")
        if contract_self_check.get("exact_field_names_used") is not True:
            raise RouterError("officer model-miss report requires contract_self_check.exact_field_names_used=true")
        checked.append(
            {
                "index": index,
                "officer_role": ref.get("officer_role") or report.get("reported_by_role"),
                "report_path": report_path,
                "report_hash": report_hash,
                "same_class_finding_count": len(report.get("same_class_findings") or []),
                "candidate_repair_count": len(report.get("candidate_repairs") or []),
            }
        )
    return checked


def _write_model_miss_triage_decision(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> str:
    decision = _load_file_backed_role_payload(project_root, payload)
    if decision.get("decided_by_role") != "project_manager":
        raise RouterError("model-miss triage decision requires decided_by_role=project_manager")
    if not (
        run_state["flags"].get("node_review_blocked")
        or run_state["flags"].get("material_scan_dispatch_blocked")
    ):
        raise RouterError("model-miss triage decision requires an active reviewer block")
    missing = [
        field
        for field in PM_MODEL_MISS_TRIAGE_REQUIRED_BODY_FIELDS
        if field not in decision or decision.get(field) is None
    ]
    if missing:
        raise RouterError("model-miss triage decision is missing required fields: " + ", ".join(missing))
    decision_value = str(decision.get("decision") or "").strip()
    if decision_value not in PM_MODEL_MISS_TRIAGE_DECISION_ALLOWED_VALUES:
        raise RouterError("model-miss triage decision is not an allowed value")
    if not str(decision.get("defect_or_blocker_id") or "").strip():
        raise RouterError("model-miss triage decision requires defect_or_blocker_id")
    block_source = str(decision.get("reviewer_block_source_path") or "").strip()
    if not block_source:
        raise RouterError("model-miss triage decision requires reviewer_block_source_path")
    if not resolve_project_path(project_root, block_source).exists():
        raise RouterError("model-miss triage reviewer_block_source_path must exist")
    scope = decision.get("model_miss_scope")
    if not isinstance(scope, dict) or not str(scope.get("bug_class_definition") or "").strip():
        raise RouterError("model-miss triage decision requires model_miss_scope.bug_class_definition")
    capability = decision.get("flowguard_capability")
    if not isinstance(capability, dict) or not isinstance(capability.get("can_model_bug_class"), bool):
        raise RouterError("model-miss triage decision requires flowguard_capability.can_model_bug_class boolean")
    blockers = decision.get("blockers")
    if not isinstance(blockers, list):
        raise RouterError("model-miss triage decision requires blockers list")
    contract_self_check = decision.get("contract_self_check")
    if not isinstance(contract_self_check, dict):
        raise RouterError("model-miss triage decision requires contract_self_check")
    if contract_self_check.get("all_required_fields_present") is not True:
        raise RouterError("model-miss triage decision requires contract_self_check.all_required_fields_present=true")
    if contract_self_check.get("exact_field_names_used") is not True:
        raise RouterError("model-miss triage decision requires contract_self_check.exact_field_names_used=true")
    checked_reports: list[dict[str, Any]] = []
    if decision_value == "proceed_with_model_backed_repair":
        if capability.get("can_model_bug_class") is not True:
            raise RouterError("model-backed repair requires flowguard_capability.can_model_bug_class=true")
        if decision.get("same_class_findings_reviewed") is not True:
            raise RouterError("model-backed repair requires same_class_findings_reviewed=true")
        if decision.get("repair_recommendation_reviewed") is not True:
            raise RouterError("model-backed repair requires repair_recommendation_reviewed=true")
        if not decision.get("candidate_repairs_considered"):
            raise RouterError("model-backed repair requires candidate_repairs_considered")
        if not isinstance(decision.get("minimal_sufficient_repair_recommendation"), dict):
            raise RouterError("model-backed repair requires minimal_sufficient_repair_recommendation object")
        if not decision.get("post_repair_model_checks_required"):
            raise RouterError("model-backed repair requires post_repair_model_checks_required")
        checked_reports = _validate_model_miss_officer_report_refs(project_root, decision)
    elif decision_value == "out_of_scope_not_modelable":
        if capability.get("can_model_bug_class") is not False:
            raise RouterError("out-of-scope repair requires flowguard_capability.can_model_bug_class=false")
        if not str(capability.get("incapability_reason") or "").strip():
            raise RouterError("out-of-scope repair requires flowguard_capability.incapability_reason")
    elif decision_value in {"request_officer_model_miss_analysis", "needs_evidence_before_modeling", "stop_for_user"}:
        if decision.get("same_class_findings_reviewed") is True or decision.get("repair_recommendation_reviewed") is True:
            raise RouterError("non-authorizing model-miss decision must not claim reviewed repair evidence")
    if decision_value in PM_MODEL_MISS_TRIAGE_REPAIR_AUTHORIZED_VALUES:
        if not str(decision.get("selected_next_action") or "").strip():
            raise RouterError("repair-authorizing model-miss decision requires selected_next_action")
        if not str(decision.get("why_repair_may_start") or "").strip():
            raise RouterError("repair-authorizing model-miss decision requires why_repair_may_start")
    output = {
        "schema_version": "flowpilot.pm_model_miss_triage_decision.v1",
        "run_id": run_state["run_id"],
        "recorded_at": utc_now(),
        "decision": decision_value,
        "repair_authorized": decision_value in PM_MODEL_MISS_TRIAGE_REPAIR_AUTHORIZED_VALUES,
        "checked_officer_reports": checked_reports,
        **{field: decision.get(field) for field in PM_MODEL_MISS_TRIAGE_REQUIRED_BODY_FIELDS},
        **_role_output_envelope_record(decision),
    }
    if "officer_report_refs" in decision:
        output["officer_report_refs"] = decision.get("officer_report_refs")
    if "minimal_sufficient_repair_recommendation" in decision:
        output["minimal_sufficient_repair_recommendation"] = decision.get("minimal_sufficient_repair_recommendation")
    if "post_repair_model_checks_required" in decision:
        output["post_repair_model_checks_required"] = decision.get("post_repair_model_checks_required")
    decisions_dir = run_root / "defects" / "model_miss_triage"
    safe_id = "".join(
        char if char.isalnum() or char in {"-", "_"} else "-"
        for char in str(decision.get("defect_or_blocker_id") or "model-miss")
    ).strip("-") or "model-miss"
    decision_path = decisions_dir / f"{safe_id}.pm_model_miss_triage_decision.json"
    write_json(decision_path, output)
    run_state["model_miss_triage"] = {
        "decision": decision_value,
        "repair_authorized": output["repair_authorized"],
        "decision_path": project_relative(project_root, decision_path),
        "decision_hash": hashlib.sha256(decision_path.read_bytes()).hexdigest(),
        "defect_or_blocker_id": decision.get("defect_or_blocker_id"),
        "checked_officer_reports": checked_reports,
    }
    return decision_value


def _write_control_blocker_repair_decision(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    decision = _load_file_backed_role_payload(project_root, payload)
    if decision.get("decided_by_role") != "project_manager":
        raise RouterError("control blocker repair decision requires decided_by_role=project_manager")
    active = run_state.get("active_control_blocker")
    if not isinstance(active, dict) or active.get("delivery_status") != "delivered":
        raise RouterError("control blocker repair decision requires a delivered active control blocker")
    blocker_id = str(decision.get("blocker_id") or "")
    if blocker_id != active.get("blocker_id"):
        raise RouterError("control blocker repair decision must reference the active blocker_id")
    allowed_decisions = {
        "repair_completed",
        "repair_not_required",
        "resolved_by_followup_event",
        "continue_after_pm_review",
    }
    if decision.get("decision") not in allowed_decisions:
        raise RouterError("control blocker repair decision is not an allowed PM repair decision")
    prior_path_context_review = decision.get("prior_path_context_review")
    if not isinstance(prior_path_context_review, dict) or prior_path_context_review.get("reviewed") is not True:
        raise RouterError("control blocker repair decision requires prior_path_context_review.reviewed=true")
    source_paths = prior_path_context_review.get("source_paths")
    if not isinstance(source_paths, list):
        raise RouterError("control blocker repair decision requires prior_path_context_review.source_paths list")
    repair_action = str(decision.get("repair_action") or "").strip()
    if not repair_action:
        raise RouterError("control blocker repair decision requires repair_action")
    raw_rerun_target = decision.get("rerun_target")
    rerun_target = _control_resolution_event_name(raw_rerun_target) or str(raw_rerun_target or "").strip()
    if not rerun_target:
        raise RouterError("control blocker repair decision requires rerun_target")
    if rerun_target == PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT:
        raise RouterError("control blocker repair decision rerun_target must name a corrected follow-up event, not the PM decision event")
    repair_transaction_request = decision.get("repair_transaction")
    if not isinstance(repair_transaction_request, dict):
        raise RouterError("control blocker repair decision requires repair_transaction")
    requested_plan_kind = str(repair_transaction_request.get("plan_kind") or "").strip()
    if requested_plan_kind not in {"event_replay", "packet_reissue", "route_mutation"}:
        raise RouterError("repair_transaction.plan_kind must be event_replay, packet_reissue, or route_mutation")
    blockers = decision.get("blockers")
    if not isinstance(blockers, list):
        raise RouterError("control blocker repair decision requires blockers list")
    contract_self_check = decision.get("contract_self_check")
    if not isinstance(contract_self_check, dict):
        raise RouterError("control blocker repair decision requires contract_self_check")
    if contract_self_check.get("all_required_fields_present") is not True:
        raise RouterError("control blocker repair decision requires contract_self_check.all_required_fields_present=true")
    if contract_self_check.get("exact_field_names_used") is not True:
        raise RouterError("control blocker repair decision requires contract_self_check.exact_field_names_used=true")
    outcome_table = _repair_outcome_table(rerun_target)
    allowed_resolution_events = _repair_outcome_events(outcome_table)
    transaction_id = _repair_transaction_id(blocker_id)
    packet_generation_id = f"{transaction_id}-gen-001"
    packet_specs, packet_spec_source = _repair_packet_specs_from_decision(
        project_root,
        run_root,
        decision,
        rerun_target=rerun_target,
    )
    if packet_specs and requested_plan_kind != "packet_reissue":
        raise RouterError("repair transaction with replacement packets requires plan_kind=packet_reissue")
    if requested_plan_kind == "packet_reissue" and not packet_specs:
        raise RouterError("packet_reissue repair transaction requires replacement packets or a packet spec path")
    plan_kind = requested_plan_kind
    if packet_specs and rerun_target != "reviewer_allows_material_scan_dispatch":
        raise RouterError("repair transaction packet reissue is currently supported only for material scan dispatch")
    output = {
        "schema_version": "flowpilot.control_blocker_repair_decision.v1",
        "run_id": run_state["run_id"],
        "blocker_id": blocker_id,
        "decided_by_role": "project_manager",
        "decision": decision["decision"],
        "repair_transaction_id": transaction_id,
        "prior_path_context_review": prior_path_context_review,
        "repair_action": repair_action,
        "rerun_target": rerun_target,
        "outcome_table": outcome_table,
        "blockers": blockers,
        "contract_self_check": contract_self_check,
        "recorded_at": utc_now(),
        **_role_output_envelope_record(decision),
    }
    decision_path = run_root / "control_blocks" / f"{blocker_id}.pm_repair_decision.json"
    write_json(decision_path, output)
    generation_commit: dict[str, Any] | None = None
    if packet_specs:
        generation_commit = _commit_material_scan_repair_generation(
            project_root,
            run_root,
            run_state,
            transaction_id=transaction_id,
            packet_generation_id=packet_generation_id,
            packet_specs=packet_specs,
        )
        _set_pre_route_frontier_phase(run_root, str(run_state["run_id"]), "material_scan")
        run_state["phase"] = "material_scan"
    transaction = {
        "schema_version": REPAIR_TRANSACTION_SCHEMA,
        "transaction_id": transaction_id,
        "run_id": run_state["run_id"],
        "blocker_id": blocker_id,
        "originating_event": active.get("originating_event"),
        "originating_action_type": active.get("originating_action_type"),
        "status": "committed",
        "plan_kind": plan_kind,
        "packet_generation_id": packet_generation_id if generation_commit else None,
        "packet_spec_source": packet_spec_source,
        "generation_commit": generation_commit,
        "pm_repair_decision_path": project_relative(project_root, decision_path),
        "rerun_target": rerun_target,
        "outcome_table": outcome_table,
        "allowed_resolution_events": allowed_resolution_events,
        "opened_at": output["recorded_at"],
        "committed_at": utc_now(),
    }
    write_json(_repair_transaction_path(run_root, transaction_id), transaction)
    active_path = resolve_project_path(project_root, str(active.get("blocker_artifact_path") or ""))
    decision_rel = project_relative(project_root, decision_path)
    decision_hash = hashlib.sha256(decision_path.read_bytes()).hexdigest()
    if active_path.exists():
        record = read_json(active_path)
        record["pm_repair_decision_status"] = "recorded"
        record["pm_repair_decision_path"] = decision_rel
        record["pm_repair_decision_hash"] = decision_hash
        record["pm_repair_rerun_target"] = rerun_target
        record["repair_transaction_id"] = transaction_id
        record["repair_transaction_path"] = project_relative(project_root, _repair_transaction_path(run_root, transaction_id))
        record["repair_outcome_table"] = outcome_table
        record["allowed_resolution_events"] = allowed_resolution_events
        record["resolution_status"] = None
        write_json(active_path, record)
    active["pm_repair_decision_status"] = "recorded"
    active["pm_repair_decision_path"] = decision_rel
    active["pm_repair_decision_hash"] = decision_hash
    active["pm_repair_rerun_target"] = rerun_target
    active["repair_transaction_id"] = transaction_id
    active["repair_transaction_path"] = project_relative(project_root, _repair_transaction_path(run_root, transaction_id))
    active["repair_outcome_table"] = outcome_table
    active["allowed_resolution_events"] = allowed_resolution_events
    _sync_control_plane_indexes(project_root, run_root, run_state)


def _gate_decision_issue(field: str, message: str, owner: str = "gate_owner") -> dict[str, str]:
    return {"field": field, "message": message, "owner": owner}


def _gate_decision_safe_id(raw: str) -> str:
    chars: list[str] = []
    for char in raw.strip().lower():
        if char.isalnum():
            chars.append(char)
        elif chars and chars[-1] != "-":
            chars.append("-")
    safe = "".join(chars).strip("-")
    return safe[:96] or "gate-decision"


def _gate_decision_issues(project_root: Path, decision: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if not isinstance(decision, dict):
        return [_gate_decision_issue("gate_decision", "GateDecision must be a JSON object")]
    for field in GATE_DECISION_REQUIRED_FIELDS:
        if field not in decision or decision.get(field) in (None, ""):
            issues.append(_gate_decision_issue(field, "missing required GateDecision field"))
    if decision.get("gate_decision_version") != GATE_DECISION_SCHEMA:
        issues.append(_gate_decision_issue("gate_decision_version", f"must equal {GATE_DECISION_SCHEMA}"))
    enum_specs = (
        ("gate_kind", GATE_DECISION_ALLOWED_KINDS),
        ("owner_role", GATE_DECISION_ALLOWED_OWNER_ROLES),
        ("risk_type", GATE_DECISION_ALLOWED_RISKS),
        ("gate_strength", GATE_DECISION_ALLOWED_STRENGTHS),
        ("decision", GATE_DECISION_ALLOWED_DECISIONS),
        ("next_action", GATE_DECISION_ALLOWED_NEXT_ACTIONS),
    )
    for field, allowed in enum_specs:
        if field in decision and decision.get(field) not in allowed:
            issues.append(_gate_decision_issue(field, f"unsupported value: {decision.get(field)}"))
    leaked_overreach = sorted(GATE_DECISION_SEMANTIC_OVERREACH_FIELDS & set(decision))
    if leaked_overreach:
        issues.append(
            _gate_decision_issue(
                ",".join(leaked_overreach),
                "router may record only mechanical GateDecision conformance, not semantic sufficiency",
                "flowpilot_router",
            )
        )
    if "blocking" in decision and not isinstance(decision.get("blocking"), bool):
        issues.append(_gate_decision_issue("blocking", "must be a boolean"))
    required_evidence = decision.get("required_evidence")
    if not isinstance(required_evidence, list) or any(not isinstance(item, str) for item in required_evidence):
        issues.append(_gate_decision_issue("required_evidence", "must be a list of strings"))
    evidence_refs = decision.get("evidence_refs")
    if not isinstance(evidence_refs, list):
        issues.append(_gate_decision_issue("evidence_refs", "must be a list of evidence reference objects"))
        evidence_refs = []
    reason = str(decision.get("reason") or "").strip()
    if not reason:
        issues.append(_gate_decision_issue("reason", "GateDecision requires a concrete reason"))
    contract_self_check = decision.get("contract_self_check")
    if contract_self_check is not None:
        if not isinstance(contract_self_check, dict):
            issues.append(_gate_decision_issue("contract_self_check", "must be an object when provided"))
        else:
            if contract_self_check.get("all_required_fields_present") is not True:
                issues.append(_gate_decision_issue("contract_self_check.all_required_fields_present", "must be true"))
            if contract_self_check.get("exact_field_names_used") is not True:
                issues.append(_gate_decision_issue("contract_self_check.exact_field_names_used", "must be true"))
    gate_strength = decision.get("gate_strength")
    gate_decision = decision.get("decision")
    blocking = decision.get("blocking")
    next_action = decision.get("next_action")
    if gate_decision == "pass":
        if blocking is not False:
            issues.append(_gate_decision_issue("blocking", "pass decisions must not be blocking"))
        if next_action != "continue":
            issues.append(_gate_decision_issue("next_action", "pass decisions must route to continue"))
        if gate_strength == "hard" and not evidence_refs:
            issues.append(_gate_decision_issue("evidence_refs", "hard pass decisions require evidence references"))
    elif gate_decision == "block":
        if blocking is not True:
            issues.append(_gate_decision_issue("blocking", "block decisions must be blocking"))
    elif gate_decision in {"waive", "skip"}:
        if blocking is not False:
            issues.append(_gate_decision_issue("blocking", "waive and skip decisions must not be blocking"))
        if next_action != "continue":
            issues.append(_gate_decision_issue("next_action", "waive and skip decisions must route to continue"))
    elif gate_decision == "repair_local":
        if blocking is not True:
            issues.append(_gate_decision_issue("blocking", "repair_local decisions must be blocking until repaired"))
        if next_action not in {"local_repair", "reviewer_recheck", "collect_evidence"}:
            issues.append(_gate_decision_issue("next_action", "repair_local requires a local repair, recheck, or evidence collection action"))
    elif gate_decision == "mutate_route":
        if blocking is not True:
            issues.append(_gate_decision_issue("blocking", "mutate_route decisions must be blocking until route mutation"))
        if next_action != "route_mutation":
            issues.append(_gate_decision_issue("next_action", "mutate_route decisions must route to route_mutation"))
    if gate_strength == "advisory" and blocking is True:
        issues.append(_gate_decision_issue("blocking", "advisory gates cannot block"))
    if gate_strength == "skip_with_reason" and gate_decision not in {"skip", "waive"}:
        issues.append(_gate_decision_issue("decision", "skip_with_reason gates require skip or waive decision"))
    for index, evidence in enumerate(evidence_refs):
        prefix = f"evidence_refs[{index}]"
        if not isinstance(evidence, dict):
            issues.append(_gate_decision_issue(prefix, "evidence reference must be an object"))
            continue
        kind = evidence.get("kind")
        if kind not in GATE_DECISION_ALLOWED_EVIDENCE_KINDS:
            issues.append(_gate_decision_issue(f"{prefix}.kind", f"unsupported evidence kind: {kind}"))
            continue
        summary = str(evidence.get("summary") or "").strip()
        if not summary:
            issues.append(_gate_decision_issue(f"{prefix}.summary", "evidence reference requires summary"))
        if kind == "none":
            continue
        raw_path = str(evidence.get("path") or "").strip()
        raw_hash = str(evidence.get("hash") or "").strip()
        if not raw_path:
            issues.append(_gate_decision_issue(f"{prefix}.path", "non-none evidence requires path"))
            continue
        if not raw_hash:
            issues.append(_gate_decision_issue(f"{prefix}.hash", "non-none evidence requires hash"))
            continue
        evidence_path = resolve_project_path(project_root, raw_path)
        try:
            project_relative(project_root, evidence_path)
        except RouterError:
            issues.append(_gate_decision_issue(f"{prefix}.path", "evidence path must stay inside the project root"))
            continue
        if not evidence_path.exists() or not evidence_path.is_file():
            issues.append(_gate_decision_issue(f"{prefix}.path", "evidence path is missing"))
            continue
        actual_hash = packet_runtime.sha256_file(evidence_path)
        if raw_hash != actual_hash:
            issues.append(_gate_decision_issue(f"{prefix}.hash", "evidence hash does not match path content"))
    return issues


def _validate_gate_decision(project_root: Path, decision: dict[str, Any]) -> dict[str, Any]:
    issues = _gate_decision_issues(project_root, decision)
    if issues:
        first = issues[0]
        raise RouterError(f"GateDecision mechanical validation failed: {first['field']}: {first['message']}")
    return decision


def _gate_decision_record_path(run_root: Path, gate_id: str) -> Path:
    return run_root / "gate_decisions" / f"{_gate_decision_safe_id(gate_id)}.json"


def _gate_decision_summary(project_root: Path, record_path: Path, decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "gate_id": str(decision["gate_id"]),
        "gate_kind": decision["gate_kind"],
        "owner_role": decision["owner_role"],
        "risk_type": decision["risk_type"],
        "gate_strength": decision["gate_strength"],
        "decision": decision["decision"],
        "blocking": decision["blocking"],
        "next_action": decision["next_action"],
        "decision_path": project_relative(project_root, record_path),
    }


def _write_gate_decision(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    decision = _load_file_backed_role_payload(project_root, payload)
    _validate_gate_decision(project_root, decision)
    gate_id = str(decision["gate_id"])
    record_path = _gate_decision_record_path(run_root, gate_id)
    record = {
        "schema_version": GATE_DECISION_RECORD_SCHEMA,
        "run_id": run_state["run_id"],
        "recorded_at": utc_now(),
        "recorded_by_event": GATE_DECISION_EVENT,
        "gate_decision": decision,
        **_role_output_envelope_record(decision),
    }
    write_json(record_path, record)
    summary = _gate_decision_summary(project_root, record_path, decision)
    decisions = run_state.setdefault("gate_decisions", [])
    if not isinstance(decisions, list):
        decisions = []
        run_state["gate_decisions"] = decisions
    decisions[:] = [item for item in decisions if item.get("gate_id") != gate_id]
    decisions.append(summary)
    ledger_path = run_root / "gate_decisions" / "gate_decision_ledger.json"
    write_json(
        ledger_path,
        {
            "schema_version": GATE_DECISION_LEDGER_SCHEMA,
            "run_id": run_state["run_id"],
            "updated_at": utc_now(),
            "gate_decision_count": len(decisions),
            "gate_decisions": decisions,
        },
    )


def _control_blocker_allows_resolution_event(record: dict[str, Any], event: str) -> bool:
    if record.get("handling_lane") in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES and event == PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT:
        return False
    raw_events = record.get("allowed_resolution_events")
    if isinstance(raw_events, list) and raw_events:
        allowed_events = {_control_resolution_event_name(item) or str(item) for item in raw_events}
        return event in allowed_events
    if record.get("handling_lane") == "control_plane_reissue":
        return event == record.get("originating_event")
    return event in EXTERNAL_EVENTS


def _control_resolution_event_name(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("event", "corrected_followup_event", "event_name"):
            name = str(value.get(key) or "").strip()
            if name:
                return name
        return None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text in EXTERNAL_EVENTS or text == PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT:
        return text
    parsed: Any = None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            parsed = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            return text
    return _control_resolution_event_name(parsed) or text


def _resolve_delivered_control_blocker(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    resolved_by_event: str,
    from_already_recorded_event: bool = False,
) -> dict[str, Any] | None:
    active = run_state.get("active_control_blocker")
    if not isinstance(active, dict) or active.get("delivery_status") != "delivered":
        return None
    record = dict(active)
    artifact_rel = str(active.get("blocker_artifact_path") or "")
    artifact_path: Path | None = None
    if artifact_rel:
        artifact_path = resolve_project_path(project_root, artifact_rel)
        if artifact_path.exists():
            record = read_json(artifact_path)
    if from_already_recorded_event:
        lane = record.get("handling_lane")
        pm_repair_recorded = (
            lane in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES
            and record.get("pm_repair_decision_status") == "recorded"
        )
        if lane != "control_plane_reissue" and not pm_repair_recorded:
            return None
    if not _control_blocker_allows_resolution_event(record, resolved_by_event):
        return None
    if artifact_path and artifact_path.exists():
        resolved_at = utc_now()
        record["resolution_status"] = "accepted_followup_event_recorded"
        record["resolved_by_event"] = resolved_by_event
        record["resolved_at"] = resolved_at
        write_json(artifact_path, record)
    resolved = dict(active)
    resolved["resolution_status"] = "accepted_followup_event_recorded"
    resolved["resolved_by_event"] = resolved_by_event
    resolved["resolved_at"] = record.get("resolved_at") or utc_now()
    run_state.setdefault("resolved_control_blockers", []).append(resolved)
    run_state["active_control_blocker"] = None
    run_state["latest_control_blocker_path"] = None
    append_history(
        run_state,
        "router_resolved_control_blocker",
        {"blocker_id": resolved.get("blocker_id"), "resolved_by_event": resolved_by_event},
    )
    _sync_control_plane_indexes(project_root, run_root, run_state)
    return resolved


def _terminal_lifecycle_mode(run_state: dict[str, Any]) -> str | None:
    status = str(run_state.get("status") or "")
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    if status == "cancelled_by_user" or flags.get("run_cancelled_by_user"):
        return "cancelled_by_user"
    if status == "stopped_by_user" or flags.get("run_stopped_by_user"):
        return "stopped_by_user"
    if status == "protocol_dead_end" or flags.get("startup_protocol_dead_end_declared"):
        return "protocol_dead_end"
    return None


def _lifecycle_record_path(run_root: Path) -> Path:
    return run_root / "lifecycle" / "run_lifecycle.json"


def _write_run_lifecycle_request(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    payload: dict[str, Any],
) -> None:
    mode = "cancelled_by_user" if event == "user_requests_run_cancel" else "stopped_by_user"
    previous_pending = run_state.get("pending_action")
    active_blocker = run_state.get("active_control_blocker")
    cleanup_receipts = payload.get("cleanup_receipts") if isinstance(payload.get("cleanup_receipts"), list) else []
    record = {
        "schema_version": "flowpilot.run_lifecycle.v1",
        "run_id": run_state.get("run_id"),
        "status": mode,
        "requested_by": str(payload.get("requested_by") or "user"),
        "request_event": event,
        "reason": payload.get("reason"),
        "previous_pending_action": previous_pending,
        "active_control_blocker_at_request": active_blocker,
        "cleanup_receipts": cleanup_receipts,
        "controller_may_continue_route_work": False,
        "controller_may_spawn_new_role_work": False,
        "requested_at": utc_now(),
    }
    run_state["status"] = mode
    run_state["phase"] = "terminal"
    run_state["holder"] = "controller"
    run_state["pending_action"] = None
    reconciliation = _reconcile_terminal_lifecycle_authorities(project_root, run_root, run_state, mode=mode, event=event)
    record["cleanup_receipts"] = cleanup_receipts + reconciliation["cleanup_receipts"]
    record["reconciliation"] = reconciliation
    write_json(_lifecycle_record_path(run_root), record)
    append_history(run_state, f"run_{mode}", {"event": event, "lifecycle_path": project_relative(project_root, _lifecycle_record_path(run_root))})

    current_path = project_root / ".flowpilot" / "current.json"
    current = read_json_if_exists(current_path) or {}
    if current.get("current_run_id") == run_state.get("run_id"):
        current["status"] = mode
        current["updated_at"] = utc_now()
        write_json(current_path, current)

    index_path = project_root / ".flowpilot" / "index.json"
    index = read_json_if_exists(index_path) or {}
    runs = index.get("runs") if isinstance(index.get("runs"), list) else []
    for item in runs:
        if isinstance(item, dict) and item.get("run_id") == run_state.get("run_id"):
            item["status"] = mode
            item["updated_at"] = utc_now()
    index["updated_at"] = utc_now()
    if runs:
        index["runs"] = runs
    write_json(index_path, index)
    _write_route_state_snapshot(project_root, run_root, run_state, source_event=event)


def _reconcile_terminal_lifecycle_authorities(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    mode: str,
    event: str,
) -> dict[str, Any]:
    reconciled_at = utc_now()
    receipts: list[dict[str, Any]] = []
    source_paths: dict[str, str] = {}

    continuation_path = _continuation_binding_path(run_root)
    if continuation_path.exists():
        continuation = read_json(continuation_path)
        source_paths["continuation_binding"] = project_relative(project_root, continuation_path)
        previous_heartbeat_active = bool(continuation.get("heartbeat_active"))
        automation_id = str(continuation.get("host_automation_id") or "")
        automation_path = Path.home() / ".codex" / "automations" / automation_id / "automation.toml" if automation_id else None
        automation_exists = bool(automation_path and automation_path.exists())
        if automation_id and not automation_exists:
            cleanup_status = "missing_verified"
        elif automation_id and previous_heartbeat_active:
            cleanup_status = "external_cleanup_may_be_required"
        else:
            cleanup_status = "inactive_verified"
        continuation["heartbeat_active"] = False
        continuation["lifecycle_status"] = mode
        continuation["terminal_event"] = event
        continuation["terminal_reconciled_at"] = reconciled_at
        continuation["host_automation_cleanup_status"] = cleanup_status
        continuation["host_automation_toml_exists"] = automation_exists if automation_id else None
        continuation["host_automation_checked_path"] = str(automation_path) if automation_path else None
        write_json(continuation_path, continuation)
        receipts.append(
            {
                "authority": "continuation_binding",
                "path": project_relative(project_root, continuation_path),
                "previous_heartbeat_active": previous_heartbeat_active,
                "heartbeat_active": False,
                "host_automation_cleanup_status": continuation["host_automation_cleanup_status"],
                "host_automation_toml_exists": continuation["host_automation_toml_exists"],
            }
        )

    crew_path = run_root / "crew_ledger.json"
    if crew_path.exists():
        crew = read_json(crew_path)
        source_paths["crew_ledger"] = project_relative(project_root, crew_path)
        role_slots = crew.get("role_slots") if isinstance(crew.get("role_slots"), list) else []
        live_before = sum(1 for slot in role_slots if isinstance(slot, dict) and str(slot.get("status") or "").startswith("live_"))
        for slot in role_slots:
            if isinstance(slot, dict):
                slot["status"] = "stopped_with_run"
                slot["live_agent_active"] = False
                slot["stopped_at"] = reconciled_at
        crew["lifecycle_status"] = mode
        crew["terminal_reconciled_at"] = reconciled_at
        write_json(crew_path, crew)
        receipts.append(
            {
                "authority": "crew_ledger",
                "path": project_relative(project_root, crew_path),
                "live_role_slots_before": live_before,
                "live_role_slots_after": 0,
            }
        )

    packet_ledger_path = run_root / "packet_ledger.json"
    if packet_ledger_path.exists():
        packet_ledger = read_json(packet_ledger_path)
        source_paths["packet_ledger"] = project_relative(project_root, packet_ledger_path)
        previous_status = packet_ledger.get("active_packet_status")
        previous_holder = packet_ledger.get("active_packet_holder")
        packet_ledger["active_packet_status"] = mode
        packet_ledger["active_packet_holder"] = "controller"
        packet_ledger["terminal_lifecycle"] = {
            "status": mode,
            "event": event,
            "previous_active_packet_status": previous_status,
            "previous_active_packet_holder": previous_holder,
            "controller_may_continue_packet_loop": False,
            "reconciled_at": reconciled_at,
        }
        packet_ledger["updated_at"] = reconciled_at
        write_json(packet_ledger_path, packet_ledger)
        receipts.append(
            {
                "authority": "packet_ledger",
                "path": project_relative(project_root, packet_ledger_path),
                "previous_active_packet_status": previous_status,
                "active_packet_status": mode,
            }
        )

    frontier_path = run_root / "execution_frontier.json"
    if frontier_path.exists():
        frontier = read_json(frontier_path)
        source_paths["execution_frontier"] = project_relative(project_root, frontier_path)
        previous_status = frontier.get("status")
        frontier["status"] = mode
        frontier["phase"] = "terminal"
        frontier["terminal"] = True
        frontier["terminal_event"] = event
        frontier["updated_at"] = reconciled_at
        frontier["source"] = event
        write_json(frontier_path, frontier)
        receipts.append(
            {
                "authority": "execution_frontier",
                "path": project_relative(project_root, frontier_path),
                "previous_status": previous_status,
                "status": mode,
            }
        )

    report = {
        "schema_version": "flowpilot.terminal_lifecycle_reconciliation.v1",
        "run_id": run_state.get("run_id"),
        "status": mode,
        "event": event,
        "controller_may_continue_route_work": False,
        "controller_may_spawn_new_role_work": False,
        "cleanup_receipts": receipts,
        "source_paths": source_paths,
        "reconciled_at": reconciled_at,
    }
    write_json(run_root / "lifecycle" / "terminal_reconciliation.json", report)
    report["reconciliation_path"] = project_relative(project_root, run_root / "lifecycle" / "terminal_reconciliation.json")
    return report


def _write_protocol_dead_end_lifecycle(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    dead_end_path: Path,
    reason: str | None,
) -> None:
    mode = "protocol_dead_end"
    previous_pending = run_state.get("pending_action")
    active_blocker = run_state.get("active_control_blocker")
    write_json(
        _lifecycle_record_path(run_root),
        {
            "schema_version": "flowpilot.run_lifecycle.v1",
            "run_id": run_state.get("run_id"),
            "status": mode,
            "requested_by": "project_manager",
            "request_event": "pm_declares_startup_protocol_dead_end",
            "reason": reason,
            "protocol_dead_end_path": project_relative(project_root, dead_end_path),
            "previous_pending_action": previous_pending,
            "active_control_blocker_at_request": active_blocker,
            "controller_may_continue_route_work": False,
            "controller_may_spawn_new_role_work": False,
            "requested_at": utc_now(),
        },
    )
    run_state["status"] = mode
    run_state["phase"] = "terminal"
    run_state["holder"] = "controller"
    run_state["pending_action"] = None
    append_history(
        run_state,
        "run_protocol_dead_end",
        {"protocol_dead_end_path": project_relative(project_root, dead_end_path)},
    )

    current_path = project_root / ".flowpilot" / "current.json"
    current = read_json_if_exists(current_path) or {}
    if current.get("current_run_id") == run_state.get("run_id"):
        current["status"] = mode
        current["updated_at"] = utc_now()
        write_json(current_path, current)

    index_path = project_root / ".flowpilot" / "index.json"
    index = read_json_if_exists(index_path) or {}
    runs = index.get("runs") if isinstance(index.get("runs"), list) else []
    for item in runs:
        if isinstance(item, dict) and item.get("run_id") == run_state.get("run_id"):
            item["status"] = mode
            item["updated_at"] = utc_now()
    index["updated_at"] = utc_now()
    if runs:
        index["runs"] = runs
    write_json(index_path, index)


def _run_lifecycle_terminal_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    mode = _terminal_lifecycle_mode(run_state)
    if not mode:
        return None
    lifecycle_rel = project_relative(project_root, _lifecycle_record_path(run_root))
    return make_action(
        action_type="run_lifecycle_terminal",
        actor="controller",
        label=f"controller_observes_{mode}",
        summary="This FlowPilot run is terminal; no further route work is authorized.",
        allowed_reads=[lifecycle_rel, project_relative(project_root, run_state_path(run_root))],
        allowed_writes=[project_relative(project_root, run_state_path(run_root))],
        extra={
            "run_lifecycle_status": mode,
            "terminal_for_route": True,
            "controller_may_continue_route_work": False,
            "controller_may_spawn_new_role_work": False,
            "allowed_external_events": ["user_requests_run_stop", "user_requests_run_cancel"],
        },
    )


def _try_write_control_blocker_for_exception(
    project_root: Path,
    *,
    source: str,
    error_message: str,
    event: str | None = None,
    action_type: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not _should_materialize_control_blocker(
        error_message,
        event=event,
        action_type=action_type,
        payload=payload,
    ):
        return None
    try:
        bootstrap = load_bootstrap_state(project_root, create_if_missing=False)
        run_state, run_root = load_run_state(project_root, bootstrap)
        if run_state is None or run_root is None:
            return None
        return _write_control_blocker(
            project_root,
            run_root,
            run_state,
            source=source,
            error_message=error_message,
            event=event,
            action_type=action_type,
            payload=payload,
        )
    except Exception:
        try:
            fallback = {
                "schema_version": "flowpilot.control_blocker_materialization_failure.v1",
                "materialization_failed": True,
                "source": source,
                "error_message": error_message,
                "event": event,
                "action_type": action_type,
                "recorded_at": utc_now(),
            }
            flowpilot_root = project_root / ".flowpilot"
            failure_path = flowpilot_root / "control_blocker_materialization_failures.jsonl"
            failure_path.parent.mkdir(parents=True, exist_ok=True)
            with failure_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(fallback, sort_keys=True) + "\n")
            fallback["fallback_diagnostic_path"] = project_relative(project_root, failure_path)
            return fallback
        except Exception:
            return {
                "schema_version": "flowpilot.control_blocker_materialization_failure.v1",
                "materialization_failed": True,
                "source": source,
                "error_message": error_message,
                "event": event,
                "action_type": action_type,
            }


def _next_boot_action(state: dict[str, Any]) -> dict[str, Any] | None:
    if not state.get("router_loaded"):
        return {
            "action_type": "load_router",
            "flag": "router_loaded",
            "label": "bootloader_router_loaded",
            "summary": "Load the FlowPilot router and initialize bootstrap state.",
            "actor": "bootloader",
        }
    for action in BOOT_ACTIONS:
        if not state["flags"].get(action["flag"]):
            return action
    return None


def compute_bootloader_action(project_root: Path, state: dict[str, Any]) -> dict[str, Any] | None:
    if state.get("pending_action"):
        return state["pending_action"]
    boot_action = _next_boot_action(state)
    if boot_action is None:
        return None
    bootstrap_rel = project_relative(project_root, bootstrap_state_path(project_root, state))
    extra_fields = {
        "requires_user": bool(boot_action.get("requires_user", False)),
        "terminal_for_turn": bool(boot_action.get("terminal_for_turn", False)),
        "requires_payload": boot_action.get("requires_payload"),
        "questions": boot_action.get("questions", []),
        "postcondition": boot_action["flag"],
    }
    if boot_action["action_type"] == "emit_startup_banner":
        extra_fields.update(_startup_banner_display())
    if boot_action["action_type"] == "record_startup_answers":
        extra_fields["payload_contract"] = _startup_answers_payload_contract()
    if boot_action["action_type"] == "start_role_slots":
        extra_fields.update(_role_spawn_action_extra(state))
    action = make_action(
        action_type=str(boot_action["action_type"]),
        actor=str(boot_action["actor"]),
        label=str(boot_action["label"]),
        summary=str(boot_action["summary"]),
        allowed_reads=[bootstrap_rel],
        allowed_writes=[bootstrap_rel],
        card_id=boot_action.get("card_id"),
        extra=extra_fields,
    )
    state["pending_action"] = action
    if state.get("router_loaded"):
        state["router_action_requests"] = int(state.get("router_action_requests", 0)) + 1
    append_history(state, "router_computed_next_bootloader_action", {"action_type": action["action_type"]})
    save_bootstrap_state(project_root, state)
    return action


def _ensure_pending(state: dict[str, Any], action_type: str) -> dict[str, Any]:
    pending = state.get("pending_action")
    if not isinstance(pending, dict):
        raise RouterError("no pending router action; run 'next' before applying an action")
    if pending.get("action_type") != action_type:
        raise RouterError(f"pending action is {pending.get('action_type')!r}, not {action_type!r}")
    return pending


def _set_boot_flag(project_root: Path, state: dict[str, Any], flag: str, label: str, details: dict[str, Any] | None = None) -> None:
    if flag == "router_loaded":
        state["router_loaded"] = True
        state["status"] = "running"
    else:
        state["flags"][flag] = True
        state["bootloader_actions"] = int(state.get("bootloader_actions", 0)) + 1
    state["pending_action"] = None
    append_history(state, label, details)
    save_bootstrap_state(project_root, state)


def _normalize_startup_question_stop_boundary(state: dict[str, Any]) -> bool:
    flags = state.setdefault("flags", {})
    if not flags.get("startup_questions_asked"):
        return False
    if flags.get("startup_answers_recorded") or state.get("startup_answers"):
        return False
    changed = False
    if not flags.get("startup_state_written_awaiting_answers"):
        flags["startup_state_written_awaiting_answers"] = True
        changed = True
    if not flags.get("dialog_stopped_for_answers"):
        flags["dialog_stopped_for_answers"] = True
        changed = True
    if state.get("startup_state") != "awaiting_answers_stopped":
        state["startup_state"] = "awaiting_answers_stopped"
        changed = True
    pending = state.get("pending_action")
    if isinstance(pending, dict) and pending.get("action_type") in {
        "write_startup_awaiting_answers_state",
        "stop_for_startup_answers",
    }:
        state["pending_action"] = None
        append_history(
            state,
            "startup_question_stop_boundary_normalized",
            {"cleared_pending_action": pending.get("action_type")},
        )
        changed = True
    return changed


def _validate_startup_answer_interpretation(payload: dict[str, Any], answers: dict[str, str]) -> dict[str, Any] | None:
    provenance = answers.get("provenance")
    if provenance == STARTUP_ANSWER_PROVENANCE:
        if payload.get("startup_answer_interpretation") is not None:
            raise RouterError("startup_answer_interpretation is only allowed with ai_interpreted_from_explicit_user_reply provenance")
        return None
    receipt = payload.get("startup_answer_interpretation")
    if not isinstance(receipt, dict):
        raise RouterError("AI-interpreted startup answers require payload.startup_answer_interpretation receipt")
    if receipt.get("schema_version") != STARTUP_ANSWER_INTERPRETATION_SCHEMA:
        raise RouterError(f"startup_answer_interpretation requires schema_version={STARTUP_ANSWER_INTERPRETATION_SCHEMA}")
    raw_text = receipt.get("raw_user_reply_text")
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise RouterError("startup_answer_interpretation.raw_user_reply_text must preserve the user's non-empty reply")
    interpreted_by = receipt.get("interpreted_by")
    if interpreted_by not in {"controller", "bootloader"}:
        raise RouterError("startup_answer_interpretation.interpreted_by must be controller or bootloader")
    if receipt.get("interpretation_provenance") != STARTUP_ANSWER_INTERPRETATION_PROVENANCE:
        raise RouterError("startup_answer_interpretation.interpretation_provenance must match the AI-interpreted startup answer provenance")
    if receipt.get("ambiguity_status") != "none":
        raise RouterError("ambiguous startup answers must be returned to the user instead of applied")
    interpreted_answers = receipt.get("interpreted_answers")
    if not isinstance(interpreted_answers, dict):
        raise RouterError("startup_answer_interpretation.interpreted_answers must be an object")
    expected = {key: answers[key] for key in STARTUP_ANSWER_ENUMS}
    got = {key: interpreted_answers.get(key) for key in STARTUP_ANSWER_ENUMS}
    if got != expected:
        raise RouterError("startup_answer_interpretation.interpreted_answers must match payload.startup_answers")
    allowed_keys = {
        "schema_version",
        "raw_user_reply_text",
        "interpreted_by",
        "interpretation_provenance",
        "ambiguity_status",
        "interpreted_answers",
        "reviewer_must_check_raw_reply_alignment",
        "notes",
    }
    extra = sorted(set(receipt) - allowed_keys)
    if extra:
        raise RouterError(f"startup_answer_interpretation contains unsupported fields: {', '.join(extra)}")
    interpretation = {
        "schema_version": STARTUP_ANSWER_INTERPRETATION_SCHEMA,
        "raw_user_reply_text": raw_text.strip(),
        "interpreted_by": interpreted_by,
        "interpretation_provenance": STARTUP_ANSWER_INTERPRETATION_PROVENANCE,
        "ambiguity_status": "none",
        "interpreted_answers": expected,
        "notes": receipt.get("notes"),
        "recorded_at": utc_now(),
    }
    if "reviewer_must_check_raw_reply_alignment" in receipt:
        interpretation["reviewer_must_check_raw_reply_alignment"] = bool(receipt.get("reviewer_must_check_raw_reply_alignment"))
    return interpretation


def _validate_startup_answers(payload: dict[str, Any]) -> dict[str, str]:
    answers = payload.get("startup_answers")
    if not isinstance(answers, dict):
        raise RouterError("record_startup_answers requires payload.startup_answers object")
    provenance = answers.get("provenance")
    if provenance not in {STARTUP_ANSWER_PROVENANCE, STARTUP_ANSWER_INTERPRETATION_PROVENANCE}:
        raise RouterError("startup answers require provenance=explicit_user_reply or ai_interpreted_from_explicit_user_reply")
    allowed_keys = set(STARTUP_ANSWER_ENUMS) | {"provenance"}
    extra = sorted(set(answers) - allowed_keys)
    if extra:
        raise RouterError(f"startup answers contain unsupported fields: {', '.join(extra)}")
    validated: dict[str, str] = {}
    for answer_id, allowed_values in STARTUP_ANSWER_ENUMS.items():
        value = answers.get(answer_id)
        if not isinstance(value, str) or value not in allowed_values:
            allowed = ", ".join(sorted(allowed_values))
            raise RouterError(f"startup answer {answer_id} must be one of: {allowed}")
        validated[answer_id] = value
    validated["provenance"] = provenance
    _validate_startup_answer_interpretation(payload, validated)
    return validated


def _validate_user_request(payload: dict[str, Any]) -> dict[str, str]:
    request = payload.get("user_request")
    if not isinstance(request, dict):
        raise RouterError("record_user_request requires payload.user_request object")
    provenance = request.get("provenance")
    if provenance != USER_REQUEST_PROVENANCE:
        raise RouterError("user request requires provenance=explicit_user_request")
    text = request.get("text")
    if not isinstance(text, str) or not text.strip():
        raise RouterError("user_request.text must contain the exact non-empty user task")
    allowed_keys = {"text", "provenance", "source"}
    extra = sorted(set(request) - allowed_keys)
    if extra:
        raise RouterError(f"user request contains unsupported fields: {', '.join(extra)}")
    source = request.get("source") or "flowpilot_activation_or_user_reply"
    if not isinstance(source, str) or not source.strip():
        raise RouterError("user_request.source must be a non-empty string when supplied")
    return {
        "text": text.strip(),
        "provenance": USER_REQUEST_PROVENANCE,
        "source": source.strip(),
    }


def _display_text_hash(display_text: str) -> str:
    return hashlib.sha256(display_text.encode("utf-8")).hexdigest()


def _user_dialog_display_gate(
    fields: dict[str, Any],
    *,
    display_kind: str,
    display_text: str,
) -> dict[str, Any]:
    gated = dict(fields)
    gated.update(
        {
            "display_kind": display_kind,
            "display_text_sha256": _display_text_hash(display_text),
            "requires_payload": "display_confirmation",
            "requires_user_dialog_display_confirmation": True,
            "required_render_target": DISPLAY_CONFIRMATION_TARGET,
            "display_confirmation_schema": DISPLAY_CONFIRMATION_SCHEMA,
        }
    )
    return gated


def _validate_display_confirmation(
    payload: dict[str, Any],
    *,
    action_type: str,
    display_kind: str,
    display_text: str,
) -> dict[str, Any]:
    confirmation = payload.get("display_confirmation")
    if not isinstance(confirmation, dict):
        raise RouterError(
            f"{action_type} requires payload.display_confirmation before apply; "
            "render display_text in the user dialog first"
        )
    if confirmation.get("provenance") != DISPLAY_CONFIRMATION_PROVENANCE:
        raise RouterError(
            f"{action_type} display_confirmation requires provenance={DISPLAY_CONFIRMATION_PROVENANCE}"
        )
    if confirmation.get("rendered_to") != DISPLAY_CONFIRMATION_TARGET:
        raise RouterError(
            f"{action_type} display_confirmation requires rendered_to={DISPLAY_CONFIRMATION_TARGET}"
        )
    if confirmation.get("action_type") != action_type:
        raise RouterError(f"{action_type} display_confirmation action_type mismatch")
    if confirmation.get("display_kind") != display_kind:
        raise RouterError(f"{action_type} display_confirmation display_kind mismatch")
    expected_hash = _display_text_hash(display_text)
    if confirmation.get("display_text_sha256") != expected_hash:
        raise RouterError(f"{action_type} display_confirmation display_text_sha256 mismatch")
    return {
        "schema_version": DISPLAY_CONFIRMATION_SCHEMA,
        "action_type": action_type,
        "display_kind": display_kind,
        "rendered_to": DISPLAY_CONFIRMATION_TARGET,
        "display_text_sha256": expected_hash,
        "provenance": DISPLAY_CONFIRMATION_PROVENANCE,
        "confirmed_at": utc_now(),
    }


def _display_confirmation_for_action(payload: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    payload = payload or {}
    display_text = action.get("display_text")
    if not isinstance(display_text, str) or not display_text:
        raise RouterError("display confirmation requested for action without display_text")
    display_kind = action.get("display_kind")
    if not isinstance(display_kind, str) or not display_kind:
        raise RouterError("display confirmation requested for action without display_kind")
    return _validate_display_confirmation(
        payload,
        action_type=str(action.get("action_type") or ""),
        display_kind=display_kind,
        display_text=display_text,
    )


def _append_user_dialog_display_ledger(project_root: Path, run_root: Path, record: dict[str, Any]) -> None:
    del project_root
    ledger_path = run_root / "display" / "user_dialog_display_ledger.json"
    ledger = read_json_if_exists(ledger_path) or {
        "schema_version": "flowpilot.user_dialog_display_ledger.v1",
        "run_id": run_root.name,
        "records": [],
    }
    ledger.setdefault("records", []).append(record)
    ledger["updated_at"] = utc_now()
    write_json(ledger_path, ledger)


def _display_plan_display_kind(plan_projection: dict[str, Any]) -> str:
    items = plan_projection.get("items") if isinstance(plan_projection.get("items"), list) else []
    if (
        len(items) == 1
        and isinstance(items[0], dict)
        and items[0].get("id") == "await_pm_route"
        and plan_projection.get("current_node_id") is None
    ):
        return "startup_waiting_state"
    return "route_map"


def _display_plan_chat_markdown(plan_projection: dict[str, Any], *, display_kind: str) -> str:
    title = "# FlowPilot Startup Status" if display_kind == "startup_waiting_state" else "# FlowPilot Route Map"
    lines = [title, ""]
    for item in plan_projection.get("items") or []:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("id") or "Route item")
        status = str(item.get("status") or "pending")
        lines.append(f"- {label} - {status}")
    if len(lines) == 2:
        lines.append("- Waiting for PM route - in_progress")
    return "\n".join(lines).rstrip() + "\n"


def _display_plan_user_dialog_fields(plan_projection: dict[str, Any]) -> dict[str, Any]:
    display_kind = _display_plan_display_kind(plan_projection)
    display_text = _display_plan_chat_markdown(plan_projection, display_kind=display_kind)
    display_label = "startup waiting state" if display_kind == "startup_waiting_state" else "route map"
    return _user_dialog_display_gate(
        {
            "display_text": display_text,
            "display_text_format": "markdown",
            "display_required": True,
            "controller_must_display_text_before_apply": True,
            "generated_files_alone_satisfy_chat_display": False,
            "controller_display_rule": f"Paste this exact {display_label} display_text in the user dialog before applying sync_display_plan; display_plan.json or host-plan replacement alone does not satisfy display.",
        },
        display_kind=display_kind,
        display_text=display_text,
    )


def _display_route_sign_user_dialog_fields(route_sign: dict[str, Any]) -> dict[str, Any]:
    display_text = route_sign.get("markdown")
    if not isinstance(display_text, str) or not display_text.strip():
        raise RouterError("route-sign display requires non-empty markdown")
    return _user_dialog_display_gate(
        {
            "display_text": display_text,
            "display_text_format": "markdown_mermaid",
            "display_required": True,
            "controller_must_display_text_before_apply": True,
            "generated_files_alone_satisfy_chat_display": False,
            "controller_display_rule": "Paste this exact FlowPilot Route Sign Mermaid in the user dialog before applying sync_display_plan; display_plan.json or generated files alone do not satisfy display.",
        },
        display_kind="route_map",
        display_text=display_text,
    )


def _startup_banner_display() -> dict[str, Any]:
    banner_path = runtime_kit_source() / "cards" / "system" / "startup_banner.md"
    if not banner_path.exists():
        raise RouterError("startup banner card is missing")
    text = banner_path.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped.startswith("<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1"):
        end = stripped.find("-->")
        if end >= 0:
            stripped = stripped[end + 3 :].lstrip()
    display_text = stripped.rstrip() + "\n"
    return _user_dialog_display_gate(
        {
            "display_path": str(banner_path),
            "display_text": display_text,
            "display_text_format": "plain_text",
            "display_required": True,
            "controller_must_display_text_before_apply": True,
            "generated_files_alone_satisfy_chat_display": False,
            "controller_display_rule": "Paste this exact startup banner display_text in the user dialog before applying emit_startup_banner; apply requires display_confirmation.rendered_to=user_dialog with matching display_text_sha256.",
        },
        display_kind="startup_banner",
        display_text=display_text,
    )


def _role_spawn_action_extra(state: dict[str, Any]) -> dict[str, Any]:
    answers = state.get("startup_answers") if isinstance(state.get("startup_answers"), dict) else {}
    mode = answers.get("background_agents")
    extra: dict[str, Any] = {
        "background_agents_mode": mode,
        "role_keys": list(CREW_ROLE_KEYS),
    }
    if mode == "allow":
        extra.update(
            {
                "requires_payload": "role_agents",
                "requires_host_spawn": True,
                "spawn_policy": "spawn_all_six_fresh_current_task_agents_before_applying_action",
                "payload_contract": _role_slots_payload_contract(),
                "role_spawn_request": [
                    {
                        "role_key": role,
                        "spawn_result": ROLE_AGENT_SPAWN_RESULT,
                        "spawned_for_run_id": state.get("run_id"),
                        "spawned_after_startup_answers": True,
                    }
                    for role in CREW_ROLE_KEYS
                ],
            }
        )
    elif mode == "single-agent":
        extra.update(
            {
                "requires_host_spawn": False,
                "single_agent_continuity_authorized": True,
            }
        )
    return extra


def _normalize_role_agent_records(state: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, Any]]:
    answers = state.get("startup_answers") if isinstance(state.get("startup_answers"), dict) else {}
    mode = answers.get("background_agents")
    run_id = str(state.get("run_id") or "")
    if mode == "single-agent":
        return [
            {
                "role_key": role,
                "status": "single_agent_continuity_authorized",
                "agent_id": None,
                "spawn_result": "not_requested_single_agent_continuity",
                "fallback_authorized_by_startup_answer": True,
                "recorded_at": utc_now(),
            }
            for role in CREW_ROLE_KEYS
        ]
    if mode != "allow":
        raise RouterError("cannot start roles before background_agents startup answer is recorded")
    raw_records = payload.get("role_agents")
    if isinstance(raw_records, dict):
        iterable = list(raw_records.values())
    elif isinstance(raw_records, list):
        iterable = raw_records
    else:
        raise RouterError("start_role_slots requires payload.role_agents list or object")
    if payload.get("background_agents_capability_status") != "available":
        raise RouterError("live background roles require background_agents_capability_status=available")
    records_by_role: dict[str, dict[str, Any]] = {}
    for raw in iterable:
        if not isinstance(raw, dict):
            raise RouterError("each role agent record must be an object")
        role = raw.get("role_key")
        if role not in CREW_ROLE_KEYS:
            raise RouterError(f"role agent record has unsupported role_key: {role!r}")
        if role in records_by_role:
            raise RouterError(f"duplicate role agent record for {role}")
        agent_id = raw.get("agent_id")
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise RouterError(f"{role} requires a non-empty current agent_id")
        if raw.get("spawn_result") != ROLE_AGENT_SPAWN_RESULT:
            raise RouterError(f"{role} requires spawn_result=spawned_fresh_for_task")
        if raw.get("spawned_after_startup_answers") is not True:
            raise RouterError(f"{role} must be spawned_after_startup_answers=true")
        if raw.get("spawned_for_run_id") != run_id:
            raise RouterError(f"{role} must be spawned_for_run_id={run_id}")
        host_spawn_receipt = raw.get("host_spawn_receipt")
        if host_spawn_receipt is not None:
            if not isinstance(host_spawn_receipt, dict):
                raise RouterError(f"{role} host_spawn_receipt must be an object")
            if host_spawn_receipt.get("source_kind") != "host_receipt":
                raise RouterError(f"{role} host_spawn_receipt requires source_kind=host_receipt")
            if host_spawn_receipt.get("spawned_for_run_id") != run_id:
                raise RouterError(f"{role} host_spawn_receipt spawned_for_run_id mismatch")
            if host_spawn_receipt.get("role_key") != role:
                raise RouterError(f"{role} host_spawn_receipt role_key mismatch")
            if host_spawn_receipt.get("agent_id") != agent_id:
                raise RouterError(f"{role} host_spawn_receipt agent_id mismatch")
        records_by_role[str(role)] = {
            "role_key": str(role),
            "status": "live_agent_started",
            "agent_id": agent_id.strip(),
            "spawn_result": ROLE_AGENT_SPAWN_RESULT,
            "spawned_for_run_id": run_id,
            "spawned_after_startup_answers": True,
            **({"host_spawn_receipt": host_spawn_receipt} if isinstance(host_spawn_receipt, dict) else {}),
            "recorded_at": utc_now(),
        }
    missing = [role for role in CREW_ROLE_KEYS if role not in records_by_role]
    if missing:
        raise RouterError(f"missing live role agent records: {', '.join(missing)}")
    return [records_by_role[role] for role in CREW_ROLE_KEYS]


def _latest_resume_tick_id(run_state: dict[str, Any]) -> str:
    ticks = run_state.get("heartbeat_ticks") if isinstance(run_state.get("heartbeat_ticks"), list) else []
    for tick in reversed(ticks):
        if isinstance(tick, dict) and tick.get("tick_id"):
            return str(tick["tick_id"])
    return "manual-resume"


def _role_core_prompt_path(run_root: Path, role: str) -> Path:
    return run_root / "runtime_kit" / "cards" / "roles" / f"{role}.md"


def _role_memory_path(run_root: Path, role: str) -> Path:
    return run_root / "crew_memory" / f"{role}.json"


def _path_hash(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    return packet_runtime.sha256_file(path)


def _resume_role_context(project_root: Path, run_root: Path, run_state: dict[str, Any], role: str) -> dict[str, Any]:
    memory_path = _role_memory_path(run_root, role)
    core_path = _role_core_prompt_path(run_root, role)
    common_context = {
        "resume_reentry": project_relative(project_root, run_root / "continuation" / "resume_reentry.json"),
        "execution_frontier": project_relative(project_root, run_root / "execution_frontier.json"),
        "packet_ledger": project_relative(project_root, run_root / "packet_ledger.json"),
        "prompt_delivery_ledger": project_relative(project_root, run_root / "prompt_delivery_ledger.json"),
        "crew_ledger": project_relative(project_root, run_root / "crew_ledger.json"),
        "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
        "pm_prior_path_context": project_relative(project_root, _pm_prior_path_context_path(run_root)),
        "display_plan": project_relative(project_root, _display_plan_path(run_root)),
    }
    context = {
        "role_key": role,
        "required_rehydration_result": ROLE_AGENT_REHYDRATION_RESULT,
        "allowed_rehydration_results": sorted(RESUME_ROLE_AGENT_RESULTS),
        "rehydrated_for_run_id": run_state["run_id"],
        "rehydrated_after_resume_tick_id": _latest_resume_tick_id(run_state),
        "spawned_after_resume_state_loaded": True,
        "core_prompt_path": project_relative(project_root, core_path),
        "core_prompt_hash": _path_hash(core_path),
        "memory_packet_path": project_relative(project_root, memory_path),
        "memory_packet_hash": _path_hash(memory_path),
        "role_memory_status": "available" if memory_path.exists() else "missing",
        "common_context_paths": common_context,
        "controller_visibility": "state_and_envelopes_only",
        "sealed_body_reads_allowed": False,
        "chat_history_progress_inference_allowed": False,
    }
    if role == "project_manager":
        context["pm_resume_context_required"] = True
        context["pm_resume_context_paths"] = {
            "resume_reentry": common_context["resume_reentry"],
            "execution_frontier": common_context["execution_frontier"],
            "packet_ledger": common_context["packet_ledger"],
            "prompt_delivery_ledger": common_context["prompt_delivery_ledger"],
            "crew_ledger": common_context["crew_ledger"],
            "crew_memory": project_relative(project_root, run_root / "crew_memory"),
            "route_history_index": common_context["route_history_index"],
            "pm_prior_path_context": common_context["pm_prior_path_context"],
            "display_plan": common_context["display_plan"],
        }
    return context


def _resume_role_contexts(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    return [_resume_role_context(project_root, run_root, run_state, role) for role in CREW_ROLE_KEYS]


def _resume_role_rehydration_action_extra(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    answers = _startup_answers_from_run(run_root)
    mode = answers.get("background_agents")
    contexts = _resume_role_contexts(project_root, run_root, run_state)
    missing_memory = [item["role_key"] for item in contexts if item["role_memory_status"] != "available"]
    resume_next = _derive_resume_next_recipient_from_packet_ledger(run_root)
    extra: dict[str, Any] = {
        "background_agents_mode": mode,
        "role_keys": list(CREW_ROLE_KEYS),
        "resume_tick_id": _latest_resume_tick_id(run_state),
        "awaiting_role_from_packet_ledger": resume_next.get("next_recipient_role"),
        "resume_next_recipient_from_packet_ledger": resume_next,
        "role_rehydration_request": contexts,
        "memory_missing_role_keys": missing_memory,
        "crew_rehydration_report_path": project_relative(project_root, run_root / "continuation" / "crew_rehydration_report.json"),
        "liveness_preflight_required": True,
        "liveness_preflight_policy": {
            "roles_to_check": list(CREW_ROLE_KEYS),
            "current_waiting_role_source": "packet_ledger.next_recipient_role",
            "resume_agent_check_required": True,
            "bounded_wait_allowed": True,
            "wait_agent_timeout_result": "timeout_unknown",
            "timeout_unknown_is_active": False,
            "missing_cancelled_unknown_requires_replacement": True,
            "heartbeat_and_manual_resume_share_path": True,
        },
        "controller_visibility": "state_and_envelopes_only",
        "sealed_body_reads_allowed": False,
        "chat_history_progress_inference_allowed": False,
    }
    if mode == "allow":
        extra.update(
            {
                "requires_payload": "rehydrated_role_agents",
                "payload_contract": _resume_role_rehydration_payload_contract(run_state, contexts),
                "requires_host_spawn": True,
                "spawn_policy": "spawn_or_confirm_all_six_live_resume_roles_before_pm_resume_decision",
                "pm_memory_rehydration_required": True,
            }
        )
    elif mode == "single-agent":
        extra.update(
            {
                "requires_host_spawn": False,
                "single_agent_continuity_authorized": True,
            }
        )
    return extra


def _normalize_resume_role_agent_records(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    answers = _startup_answers_from_run(run_root)
    mode = answers.get("background_agents")
    contexts = {item["role_key"]: item for item in _resume_role_contexts(project_root, run_root, run_state)}
    resume_tick_id = _latest_resume_tick_id(run_state)
    if mode == "single-agent":
        return [
            {
                "role_key": role,
                "status": "single_agent_resume_continuity_authorized",
                "agent_id": None,
                "rehydration_result": "not_requested_single_agent_continuity",
                "rehydrated_for_run_id": run_state["run_id"],
                "rehydrated_after_resume_tick_id": resume_tick_id,
                "host_liveness_status": "not_applicable_single_agent",
                "liveness_decision": "single_agent_resume_continuity_authorized",
                "resume_agent_attempted": False,
                "bounded_wait_result": "not_applicable",
                "wait_agent_timeout_treated_as_active": False,
                "fallback_authorized_by_startup_answer": True,
                "recorded_at": utc_now(),
            }
            for role in CREW_ROLE_KEYS
        ]
    if mode != "allow":
        raise RouterError("cannot rehydrate roles before background_agents startup answer is recorded")
    if payload.get("background_agents_capability_status") != "available":
        raise RouterError("resume role rehydration requires background_agents_capability_status=available")
    raw_records = payload.get("rehydrated_role_agents") or payload.get("role_agents")
    if isinstance(raw_records, dict):
        iterable = list(raw_records.values())
    elif isinstance(raw_records, list):
        iterable = raw_records
    else:
        raise RouterError("rehydrate_role_agents requires payload.rehydrated_role_agents list or object")
    records_by_role: dict[str, dict[str, Any]] = {}
    for raw in iterable:
        if not isinstance(raw, dict):
            raise RouterError("each rehydrated role agent record must be an object")
        role = raw.get("role_key")
        if role not in CREW_ROLE_KEYS:
            raise RouterError(f"rehydrated role record has unsupported role_key: {role!r}")
        if role in records_by_role:
            raise RouterError(f"duplicate rehydrated role record for {role}")
        context = contexts[str(role)]
        agent_id = raw.get("agent_id")
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise RouterError(f"{role} requires a non-empty live resume agent_id")
        result = raw.get("rehydration_result") or raw.get("spawn_result")
        if result not in RESUME_ROLE_AGENT_RESULTS:
            raise RouterError(f"{role} requires resume rehydration result")
        host_liveness_status = str(raw.get("host_liveness_status") or "")
        if host_liveness_status not in ROLE_AGENT_HOST_LIVENESS_STATUSES:
            raise RouterError(f"{role} requires host_liveness_status")
        liveness_decision = str(raw.get("liveness_decision") or "")
        if liveness_decision not in ROLE_AGENT_LIVENESS_DECISIONS:
            raise RouterError(f"{role} requires liveness_decision")
        if raw.get("resume_agent_attempted") is not True:
            raise RouterError(f"{role} requires resume_agent_attempted=true")
        bounded_wait_result = str(raw.get("bounded_wait_result") or "")
        if bounded_wait_result not in ROLE_AGENT_BOUNDED_WAIT_RESULTS:
            raise RouterError(f"{role} requires bounded_wait_result")
        if raw.get("wait_agent_timeout_treated_as_active") is not False:
            raise RouterError(f"{role} must record wait_agent_timeout_treated_as_active=false")
        if bounded_wait_result == "timeout_unknown" and result == ROLE_AGENT_CONTINUITY_RESULT:
            raise RouterError(f"{role} wait_agent timeout_unknown cannot be treated as active continuity")
        if host_liveness_status in {"missing", "cancelled", "unknown", "timeout_unknown"} and liveness_decision == "confirmed_existing_agent":
            raise RouterError(f"{role} missing/cancelled/unknown host liveness cannot confirm existing agent")
        if result == ROLE_AGENT_CONTINUITY_RESULT and not (
            host_liveness_status == "active" and liveness_decision == "confirmed_existing_agent"
        ):
            raise RouterError(f"{role} live continuity requires active host liveness")
        if result == ROLE_AGENT_REHYDRATION_RESULT and liveness_decision != "spawned_replacement_from_current_run_memory":
            raise RouterError(f"{role} replacement rehydration requires spawned_replacement_from_current_run_memory")
        if raw.get("rehydrated_for_run_id") != run_state["run_id"]:
            raise RouterError(f"{role} must be rehydrated_for_run_id={run_state['run_id']}")
        if raw.get("rehydrated_after_resume_tick_id") != resume_tick_id:
            raise RouterError(f"{role} must be rehydrated_after_resume_tick_id={resume_tick_id}")
        if raw.get("spawned_after_resume_state_loaded") is not True:
            raise RouterError(f"{role} must be spawned_after_resume_state_loaded=true")
        if raw.get("core_prompt_path") != context["core_prompt_path"] or raw.get("core_prompt_hash") != context["core_prompt_hash"]:
            raise RouterError(f"{role} core prompt identity mismatch")
        memory_status = context["role_memory_status"]
        if memory_status == "available":
            if raw.get("memory_packet_path") != context["memory_packet_path"]:
                raise RouterError(f"{role} memory packet path mismatch")
            if raw.get("memory_packet_hash") != context["memory_packet_hash"]:
                raise RouterError(f"{role} memory packet hash mismatch")
            if raw.get("memory_seeded_from_current_run") is not True:
                raise RouterError(f"{role} must be seeded from current-run role memory")
        else:
            if raw.get("memory_missing_acknowledged") is not True:
                raise RouterError(f"{role} missing role memory must be acknowledged")
            if raw.get("replacement_seeded_from_common_run_context") is not True:
                raise RouterError(f"{role} replacement must be seeded from common current-run context")
        if role == "project_manager" and raw.get("pm_resume_context_delivered") is not True:
            raise RouterError("project_manager resume rehydration requires PM context delivery")
        records_by_role[str(role)] = {
            "role_key": str(role),
            "status": "live_agent_rehydrated",
            "agent_id": agent_id.strip(),
            "rehydration_result": str(result),
            "host_liveness_status": host_liveness_status,
            "liveness_decision": liveness_decision,
            "resume_agent_attempted": True,
            "bounded_wait_result": bounded_wait_result,
            "wait_agent_timeout_treated_as_active": False,
            "rehydrated_for_run_id": run_state["run_id"],
            "rehydrated_after_resume_tick_id": resume_tick_id,
            "spawned_after_resume_state_loaded": True,
            "role_memory_status": memory_status,
            "memory_packet_path": context["memory_packet_path"],
            "memory_packet_hash": context["memory_packet_hash"],
            "core_prompt_path": context["core_prompt_path"],
            "core_prompt_hash": context["core_prompt_hash"],
            "memory_seeded_from_current_run": memory_status == "available",
            "replacement_seeded_from_common_run_context": memory_status != "available",
            "pm_resume_context_delivered": role == "project_manager",
            "recorded_at": utc_now(),
        }
    missing = [role for role in CREW_ROLE_KEYS if role not in records_by_role]
    if missing:
        raise RouterError(f"missing rehydrated live role agent records: {', '.join(missing)}")
    return [records_by_role[role] for role in CREW_ROLE_KEYS]


def _write_resume_role_rehydration_report(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    records = _normalize_resume_role_agent_records(project_root, run_root, run_state, payload)
    memory_complete = all(record.get("role_memory_status") == "available" for record in records)
    resume_next = _derive_resume_next_recipient_from_packet_ledger(run_root)
    timeout_unknown_roles = [record["role_key"] for record in records if record.get("host_liveness_status") == "timeout_unknown" or record.get("bounded_wait_result") == "timeout_unknown"]
    missing_or_cancelled_roles = [
        record["role_key"]
        for record in records
        if record.get("host_liveness_status") in {"missing", "cancelled", "unknown"}
    ]
    replacement_roles = [
        record["role_key"]
        for record in records
        if record.get("liveness_decision") == "spawned_replacement_from_current_run_memory"
    ]
    report_path = run_root / "continuation" / "crew_rehydration_report.json"
    report = {
        "schema_version": "flowpilot.crew_rehydration_report.v1",
        "run_id": run_state["run_id"],
        "resume_tick_id": _latest_resume_tick_id(run_state),
        "background_agents_mode": _startup_answers_from_run(run_root).get("background_agents"),
        "recorded_at": utc_now(),
        "source_paths": {
            "resume_reentry": project_relative(project_root, run_root / "continuation" / "resume_reentry.json"),
            "crew_ledger": project_relative(project_root, run_root / "crew_ledger.json"),
            "crew_memory": project_relative(project_root, run_root / "crew_memory"),
            "execution_frontier": project_relative(project_root, run_root / "execution_frontier.json"),
            "packet_ledger": project_relative(project_root, run_root / "packet_ledger.json"),
            "prompt_delivery_ledger": project_relative(project_root, run_root / "prompt_delivery_ledger.json"),
            "pm_prior_path_context": project_relative(project_root, _pm_prior_path_context_path(run_root)),
            "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
        },
        "all_six_roles_ready": len(records) == len(CREW_ROLE_KEYS),
        "liveness_preflight": {
            "checked_at": utc_now(),
            "awaiting_role": resume_next.get("next_recipient_role"),
            "roles_checked": [record["role_key"] for record in records],
            "timeout_unknown_role_keys": timeout_unknown_roles,
            "missing_cancelled_or_unknown_role_keys": missing_or_cancelled_roles,
            "replacement_role_keys": replacement_roles,
            "wait_agent_timeout_treated_as_active": False,
            "decision": "roles_ready_after_replacement" if replacement_roles else "all_roles_active",
        },
        "current_run_memory_complete": memory_complete,
        "missing_memory_role_keys": [record["role_key"] for record in records if record.get("role_memory_status") != "available"],
        "pm_memory_rehydrated": any(
            record["role_key"] == "project_manager"
            and record.get("pm_resume_context_delivered") is True
            and record.get("role_memory_status") == "available"
            for record in records
        ),
        "role_records": records,
        "controller_visibility": "state_and_envelopes_only",
        "sealed_body_reads_allowed": False,
        "chat_history_progress_inference_allowed": False,
    }
    write_json(report_path, report)
    crew_path = run_root / "crew_ledger.json"
    crew = read_json_if_exists(crew_path)
    history = crew.get("resume_rehydration_history") if isinstance(crew.get("resume_rehydration_history"), list) else []
    history.append(
        {
            "report_path": project_relative(project_root, report_path),
            "resume_tick_id": report["resume_tick_id"],
            "recorded_at": report["recorded_at"],
            "all_six_roles_ready": report["all_six_roles_ready"],
            "current_run_memory_complete": memory_complete,
            "liveness_decision": report["liveness_preflight"]["decision"],
            "timeout_unknown_role_keys": timeout_unknown_roles,
            "missing_cancelled_or_unknown_role_keys": missing_or_cancelled_roles,
        }
    )
    crew.update(
        {
            "schema_version": "flowpilot.crew_ledger.v1",
            "run_id": run_state["run_id"],
            "role_slots": records,
            "latest_resume_rehydration_report": project_relative(project_root, report_path),
            "resume_rehydration_history": history,
            "updated_at": utc_now(),
        }
    )
    write_json(crew_path, crew)
    run_state["flags"]["resume_roles_restored"] = True
    run_state["flags"]["resume_role_agents_rehydrated"] = True
    run_state["flags"]["crew_rehydration_report_written"] = True
    if not memory_complete:
        run_state["flags"]["resume_state_ambiguous"] = True


def _create_run_id() -> str:
    return f"run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"


def _create_empty_packet_ledger(project_root: Path, run_id: str, run_root: Path) -> dict[str, Any]:
    return {
        "schema_version": PACKET_LEDGER_SCHEMA,
        "run_id": run_id,
        "run_root": project_relative(project_root, run_root),
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "controller_boundary": {
            "controller_only": True,
            "all_role_mail_routes_through_controller": True,
            "controller_may_read_packet_body": False,
            "controller_may_read_result_body": False,
            "controller_may_create_project_evidence": False,
            "reviewer_dispatch_required_before_worker": True,
        },
        "mail": [],
        "packets": [],
    }


def _active_packet_ledger_record(packet_ledger: dict[str, Any]) -> dict[str, Any] | None:
    active_packet_id = packet_ledger.get("active_packet_id")
    packets = packet_ledger.get("packets") if isinstance(packet_ledger.get("packets"), list) else []
    if active_packet_id:
        for record in reversed(packets):
            if isinstance(record, dict) and record.get("packet_id") == active_packet_id:
                return record
    for record in reversed(packets):
        if isinstance(record, dict):
            return record
    return None


def _derive_resume_next_recipient_from_packet_ledger(run_root: Path) -> dict[str, Any]:
    packet_ledger = read_json_if_exists(run_root / "packet_ledger.json") or {}
    record = _active_packet_ledger_record(packet_ledger)
    active_packet_id = packet_ledger.get("active_packet_id")
    status = str(packet_ledger.get("active_packet_status") or "")
    holder = str(packet_ledger.get("active_packet_holder") or "")
    packet_envelope = record.get("packet_envelope") if isinstance(record, dict) and isinstance(record.get("packet_envelope"), dict) else {}
    result_envelope = record.get("result_envelope") if isinstance(record, dict) and isinstance(record.get("result_envelope"), dict) else {}
    assigned_worker = str(record.get("assigned_worker_role") or packet_envelope.get("to_role") or "") if isinstance(record, dict) else ""
    result_recipient = str(result_envelope.get("next_recipient") or "") if result_envelope else ""

    controller_next_action = "resume_without_active_packet_then_request_pm_decision"
    next_recipient = "project_manager"
    reason = "No active packet is recorded, so resume must continue through PM resume decision after role rehydration."
    if active_packet_id:
        if status == "packet-with-controller":
            next_recipient = assigned_worker or "unknown"
            controller_next_action = "relay_packet_envelope_to_recorded_recipient"
            reason = "Packet ledger says the packet is with Controller and records the worker recipient."
        elif status in {"envelope-relayed", "packet-body-opened-by-recipient"}:
            next_recipient = holder or assigned_worker or "unknown"
            controller_next_action = "wait_for_recorded_packet_holder_result"
            reason = "Packet ledger says the packet is already with a role; Controller waits for that role's envelope-only return."
        elif status in {"worker-result-needs-review", "result-envelope-returned"}:
            next_recipient = result_recipient or "human_like_reviewer"
            controller_next_action = "relay_result_envelope_to_recorded_reviewer"
            reason = "Packet ledger says a result envelope is with Controller and records the review recipient."
        elif status in {"result-envelope-relayed", "result-body-opened-by-recipient"}:
            next_recipient = holder or result_recipient or "human_like_reviewer"
            controller_next_action = "wait_for_recorded_result_holder_review"
            reason = "Packet ledger says the result is already with its review holder."
        elif status == "contaminated-returned-to-sender":
            next_recipient = holder or str(record.get("from_role") or "project_manager") if isinstance(record, dict) else "project_manager"
            controller_next_action = "wait_for_sender_reissue_or_pm_repair_decision"
            reason = "Packet ledger says the envelope was returned to sender because the control boundary was violated."
        elif status == "superseded-by-replacement":
            next_recipient = "project_manager"
            controller_next_action = "wait_for_replacement_packet_or_pm_route_repair"
            reason = "Packet ledger says this packet was superseded, so PM owns the replacement or route repair decision."
        else:
            next_recipient = holder or assigned_worker or result_recipient or "project_manager"
            controller_next_action = "wait_for_ledger_recorded_holder_or_pm_resume_decision"
            reason = "Packet ledger has an active packet with a non-standard status; Controller must not infer from chat."

    return {
        "schema_version": "flowpilot.resume_next_recipient.v1",
        "source": "packet_ledger",
        "active_packet_id": active_packet_id,
        "active_packet_status": status or None,
        "active_packet_holder": holder or None,
        "controller_next_action": controller_next_action,
        "next_recipient_role": next_recipient,
        "controller_has_explicit_next_from_ledger": next_recipient != "unknown",
        "controller_may_infer_next_from_chat_history": False,
        "sealed_body_reads_allowed": False,
        "reason": reason,
    }


def _create_empty_execution_frontier(run_id: str) -> dict[str, Any]:
    return {
        "schema_version": "flowpilot.execution_frontier.v1",
        "run_id": run_id,
        "status": "startup_intake",
        "active_route_id": None,
        "active_node_id": None,
        "updated_at": utc_now(),
        "source": "router_bootstrap",
    }


def _set_pre_route_frontier_phase(run_root: Path, run_id: str, phase: str) -> None:
    frontier = read_json_if_exists(run_root / "execution_frontier.json") or _create_empty_execution_frontier(run_id)
    if frontier.get("active_route_id") or frontier.get("active_node_id"):
        return
    frontier["status"] = phase
    frontier["phase"] = phase
    frontier["updated_at"] = utc_now()
    frontier["source"] = "flowpilot_router"
    write_json(run_root / "execution_frontier.json", frontier)


def _create_empty_role_memory(run_id: str, role: str) -> dict[str, Any]:
    return {
        "schema_version": "flowpilot.role_memory.v1",
        "run_id": run_id,
        "role_key": role,
        "status": "slot_created_no_work_yet",
        "summary": "",
        "updated_at": utc_now(),
    }


def _startup_answers_from_run(run_root: Path) -> dict[str, Any]:
    payload = read_json_if_exists(run_root / "startup_answers.json")
    answers = payload.get("answers")
    if not isinstance(answers, dict):
        return {}
    return dict(answers)


def _scheduled_continuation_requested(answers: dict[str, Any]) -> bool:
    value = str(answers.get("scheduled_continuation") or "").lower()
    return bool(value) and "manual" not in value and "no" not in value and "disable" not in value


def _continuation_binding_path(run_root: Path) -> Path:
    return run_root / "continuation" / "continuation_binding.json"


def _stable_resume_launcher_contract() -> dict[str, Any]:
    return {
        "event": "heartbeat_or_manual_resume_requested",
        "wake_sources": ["heartbeat", "manual_resume"],
        "resume_action": "load_resume_state",
        "role_liveness_action": "rehydrate_role_agents",
        "router_reentry_required_on_every_wake": True,
        "heartbeat_and_manual_resume_share_path": True,
        "self_keepalive_allowed": False,
        "diagnostic_work_chain_status_only": True,
        "controller_only": True,
        "sealed_body_reads_allowed": False,
    }


def _write_initial_continuation_binding(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    answers = _startup_answers_from_run(run_root)
    scheduled_requested = _scheduled_continuation_requested(answers)
    binding = {
        "schema_version": "flowpilot.continuation_binding.v1",
        "run_id": run_state["run_id"],
        "mode": "scheduled_heartbeat" if scheduled_requested else "manual_resume",
        "scheduled_continuation_requested": scheduled_requested,
        "route_heartbeat_interval_minutes": 1 if scheduled_requested else 0,
        "heartbeat_active": False,
        "host_automation_id": None,
        "host_automation_verified": False,
        "stable_launcher": _stable_resume_launcher_contract(),
        "source_paths": {
            "startup_answers": project_relative(project_root, run_root / "startup_answers.json"),
            "router_state": project_relative(project_root, run_state_path(run_root)),
        },
        "updated_at": utc_now(),
    }
    write_json(_continuation_binding_path(run_root), binding)


def _write_host_heartbeat_binding(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    binding_path = _continuation_binding_path(run_root)
    binding = read_json_if_exists(binding_path)
    answers = _startup_answers_from_run(run_root)
    scheduled_requested = _scheduled_continuation_requested(answers)
    interval = int(payload.get("route_heartbeat_interval_minutes") or binding.get("route_heartbeat_interval_minutes") or 0)
    if scheduled_requested and interval != 1:
        raise RouterError("scheduled FlowPilot heartbeat must be one minute")
    if scheduled_requested and not payload.get("host_automation_id"):
        raise RouterError("scheduled FlowPilot heartbeat requires host_automation_id")
    if scheduled_requested and payload.get("host_automation_verified") is not True:
        raise RouterError("scheduled FlowPilot heartbeat requires host_automation_verified=true")
    host_automation_proof = payload.get("host_automation_proof")
    if scheduled_requested and not isinstance(host_automation_proof, dict):
        raise RouterError("scheduled FlowPilot heartbeat requires host_automation_proof")
    if host_automation_proof is not None:
        if not isinstance(host_automation_proof, dict):
            raise RouterError("host_automation_proof must be an object")
        if host_automation_proof.get("source_kind") != "host_receipt":
            raise RouterError("host_automation_proof requires source_kind=host_receipt")
        if host_automation_proof.get("run_id") != run_state["run_id"]:
            raise RouterError("host_automation_proof run_id must match current run")
        if host_automation_proof.get("host_automation_id") != payload.get("host_automation_id"):
            raise RouterError("host_automation_proof host_automation_id mismatch")
        if int(host_automation_proof.get("route_heartbeat_interval_minutes") or 0) != 1:
            raise RouterError("host_automation_proof requires one-minute heartbeat interval")
        if host_automation_proof.get("heartbeat_bound_to_current_run") is not True:
            raise RouterError("host_automation_proof must bind heartbeat to current run")
    binding.update(
        {
            "schema_version": "flowpilot.continuation_binding.v1",
            "run_id": run_state["run_id"],
            "mode": "scheduled_heartbeat" if scheduled_requested else "manual_resume",
            "scheduled_continuation_requested": scheduled_requested,
            "route_heartbeat_interval_minutes": 1 if scheduled_requested else 0,
            "heartbeat_active": bool(scheduled_requested),
            "host_automation_id": payload.get("host_automation_id") if scheduled_requested else None,
            "host_automation_verified": bool(scheduled_requested),
            "stable_launcher": _stable_resume_launcher_contract(),
            **({"host_automation_proof": host_automation_proof} if scheduled_requested and isinstance(host_automation_proof, dict) else {}),
            "recorded_by": str(payload.get("recorded_by") or "host"),
            "updated_at": utc_now(),
        }
    )
    write_json(binding_path, binding)


def _host_heartbeat_binding_ready(run_root: Path, run_state: dict[str, Any]) -> bool:
    binding = read_json_if_exists(_continuation_binding_path(run_root))
    return (
        binding.get("run_id") == run_state.get("run_id")
        and binding.get("mode") == "scheduled_heartbeat"
        and binding.get("scheduled_continuation_requested") is True
        and binding.get("heartbeat_active") is True
        and binding.get("route_heartbeat_interval_minutes") == 1
        and bool(binding.get("host_automation_id"))
        and binding.get("host_automation_verified") is True
        and _continuation_has_host_bound_automation_receipt(binding, str(run_state.get("run_id") or ""))
    )


def _append_heartbeat_tick(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    source = str(payload.get("source") or "heartbeat_or_manual_resume")
    tick = {
        "schema_version": "flowpilot.heartbeat_tick.v1",
        "run_id": run_state["run_id"],
        "tick_id": f"heartbeat-{len(run_state.get('heartbeat_ticks', [])) + 1:04d}",
        "work_chain_status": str(payload.get("work_chain_status") or "broken_or_unknown"),
        "work_chain_status_trust": "diagnostic_only",
        "recorded_at": utc_now(),
        "source": source,
        "resume_requested": True,
        "router_reentry_required": True,
        "self_keepalive_allowed": False,
        "heartbeat_automation_status": str(payload.get("heartbeat_automation_status") or "unknown"),
        "heartbeat_automation_status_checked": payload.get("heartbeat_automation_status_checked") is True,
    }
    ticks_path = run_root / "continuation" / "heartbeat_ticks.jsonl"
    ticks_path.parent.mkdir(parents=True, exist_ok=True)
    with ticks_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(tick, sort_keys=True) + "\n")
    run_state.setdefault("heartbeat_ticks", []).append(
        {
            "tick_id": tick["tick_id"],
            "work_chain_status": tick["work_chain_status"],
            "resume_requested": tick["resume_requested"],
            "router_reentry_required": tick["router_reentry_required"],
            "self_keepalive_allowed": tick["self_keepalive_allowed"],
            "heartbeat_automation_status": tick["heartbeat_automation_status"],
            "heartbeat_automation_status_checked": tick["heartbeat_automation_status_checked"],
        }
    )
    return tick


def _reset_resume_cycle_for_wakeup(run_state: dict[str, Any]) -> None:
    for flag in (
        "resume_reentry_requested",
        "resume_state_loaded",
        "resume_state_ambiguous",
        "resume_roles_restored",
        "resume_role_agents_rehydrated",
        "crew_rehydration_report_written",
        "controller_resume_card_delivered",
        "pm_crew_rehydration_freshness_card_delivered",
        "pm_resume_decision_card_delivered",
        "pm_resume_recovery_decision_returned",
    ):
        run_state["flags"][flag] = False


def _current_closure_state_clean(run_root: Path) -> bool:
    evidence = read_json_if_exists(run_root / "evidence" / "evidence_ledger.json")
    generated = read_json_if_exists(run_root / "generated_resource_ledger.json")
    final_ledger = read_json_if_exists(run_root / "final_route_wide_gate_ledger.json")
    terminal = read_json_if_exists(run_root / "reviews" / "terminal_backward_replay.json")
    task_projection = read_json_if_exists(_task_completion_projection_path(run_root))
    return (
        evidence.get("unresolved_count") == 0
        and evidence.get("stale_count") == 0
        and generated.get("pending_resource_count") == 0
        and generated.get("unresolved_resource_count") == 0
        and final_ledger.get("completion_allowed") is True
        and final_ledger.get("counts", {}).get("unresolved_count") == 0
        and terminal.get("passed") is True
        and task_projection.get("task_status") == "ready_for_pm_terminal_closure"
    )


def _invalidate_route_completion_if_dirty_before_closure(run_state: dict[str, Any], run_root: Path) -> None:
    flags = run_state["flags"]
    if not flags.get("final_backward_replay_passed"):
        return
    if flags.get("pm_closure_approved"):
        return
    if _current_closure_state_clean(run_root):
        return
    _reset_flags(run_state, ROUTE_COMPLETION_FLAGS)
    append_history(
        run_state,
        "route_completion_cycle_invalidated_by_dirty_closure_state",
        {
            "reason": "completion ledgers changed after terminal backward replay and before PM closure",
            "restart_from": "pm.evidence_quality_package",
        },
    )


def _startup_fact_checks(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, bool]:
    answers = _startup_answers_from_run(run_root)
    required_answer_ids = {item["id"] for item in STARTUP_QUESTIONS}
    current = read_json_if_exists(project_root / ".flowpilot" / "current.json")
    index = read_json_if_exists(project_root / ".flowpilot" / "index.json")
    crew = read_json_if_exists(run_root / "crew_ledger.json")
    role_slots = crew.get("role_slots") if isinstance(crew.get("role_slots"), list) else []
    role_keys = {slot.get("role_key") for slot in role_slots if isinstance(slot, dict)}
    live_role_slots_current = role_keys == set(CREW_ROLE_KEYS) and all(
        isinstance(slot, dict)
        and slot.get("status") == "live_agent_started"
        and isinstance(slot.get("agent_id"), str)
        and bool(str(slot.get("agent_id")).strip())
        and slot.get("spawn_result") == ROLE_AGENT_SPAWN_RESULT
        and slot.get("spawned_for_run_id") == run_state.get("run_id")
        and slot.get("spawned_after_startup_answers") is True
        for slot in role_slots
    )
    single_agent_slots_current = role_keys == set(CREW_ROLE_KEYS) and all(
        isinstance(slot, dict)
        and slot.get("status") == "single_agent_continuity_authorized"
        and slot.get("agent_id") is None
        and slot.get("fallback_authorized_by_startup_answer") is True
        for slot in role_slots
    )
    indexed_runs = index.get("runs") if isinstance(index.get("runs"), list) else []
    continuation_binding = read_json_if_exists(_continuation_binding_path(run_root))
    scheduled_requested = _scheduled_continuation_requested(answers)
    old_control_paths = [
        project_root / ".flowpilot" / "state.json",
        project_root / ".flowpilot" / "capabilities.json",
        project_root / ".flowpilot" / "execution_frontier.json",
        project_root / ".flowpilot" / "routes",
    ]
    return {
        "startup_answers_complete": required_answer_ids.issubset({key for key, value in answers.items() if value}),
        "current_pointer_matches_run": current.get("current_run_id") == run_state.get("run_id")
        and current.get("current_run_root") == run_state.get("run_root"),
        "index_points_to_run": index.get("current_run_id") == run_state.get("run_id")
        and any(isinstance(item, dict) and item.get("run_id") == run_state.get("run_id") for item in indexed_runs),
        "crew_slots_current": role_keys == set(CREW_ROLE_KEYS),
        "live_background_agents_current_if_allowed": live_role_slots_current
        if answers.get("background_agents") == "allow"
        else True,
        "single_agent_continuity_current_if_selected": single_agent_slots_current
        if answers.get("background_agents") == "single-agent"
        else True,
        "continuation_mode_recorded": bool(answers.get("scheduled_continuation")),
        "continuation_binding_current": continuation_binding.get("run_id") == run_state.get("run_id")
        and continuation_binding.get("schema_version") == "flowpilot.continuation_binding.v1",
        "scheduled_heartbeat_verified_if_requested": (
            continuation_binding.get("heartbeat_active") is True
            and continuation_binding.get("route_heartbeat_interval_minutes") == 1
            and bool(continuation_binding.get("host_automation_id"))
            and continuation_binding.get("host_automation_verified") is True
        )
        if scheduled_requested
        else continuation_binding.get("mode") == "manual_resume",
        "display_surface_recorded": bool(answers.get("display_surface")),
        "old_state_quarantined": not any(path.exists() for path in old_control_paths),
    }


def _role_slots_have_host_spawn_receipts(role_slots: list[dict[str, Any]], run_id: str) -> bool:
    for slot in role_slots:
        receipt = slot.get("host_spawn_receipt") if isinstance(slot, dict) else None
        if not isinstance(receipt, dict):
            return False
        if receipt.get("source_kind") != "host_receipt":
            return False
        if receipt.get("spawned_for_run_id") != run_id:
            return False
        if receipt.get("role_key") != slot.get("role_key"):
            return False
        if receipt.get("agent_id") != slot.get("agent_id"):
            return False
    return bool(role_slots)


def _continuation_has_host_bound_automation_receipt(continuation_binding: dict[str, Any], run_id: str) -> bool:
    proof = continuation_binding.get("host_automation_proof")
    if not isinstance(proof, dict):
        return False
    return (
        proof.get("source_kind") == "host_receipt"
        and proof.get("run_id") == run_id
        and proof.get("host_automation_id") == continuation_binding.get("host_automation_id")
        and proof.get("route_heartbeat_interval_minutes") == 1
        and proof.get("heartbeat_bound_to_current_run") is True
    )


def _startup_external_fact_requirements(run_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    answers = _startup_answers_from_run(run_root)
    crew = read_json_if_exists(run_root / "crew_ledger.json")
    role_slots = crew.get("role_slots") if isinstance(crew.get("role_slots"), list) else []
    continuation_binding = read_json_if_exists(_continuation_binding_path(run_root))
    requirements: list[dict[str, Any]] = []
    if answers.get("background_agents") == "allow" and not _role_slots_have_host_spawn_receipts(role_slots, str(run_state.get("run_id") or "")):
        requirements.append(
            {
                "id": "live_agent_spawn_freshness",
                "reason": "Router validates role-slot shape and run ids, but host spawn freshness needs a receipt or reviewer check.",
                "self_attested_payload_fields": ["role_agents[].spawn_result", "role_agents[].spawned_after_startup_answers"],
                "reviewer_direct_check_required": True,
            }
        )
    if _scheduled_continuation_requested(answers) and not _continuation_has_host_bound_automation_receipt(
        continuation_binding,
        str(run_state.get("run_id") or ""),
    ):
        requirements.append(
            {
                "id": "heartbeat_host_automation_current_run_binding",
                "reason": "Router validates the heartbeat binding fields, but host_automation_verified=true alone is an AI/host payload claim unless backed by a host receipt.",
                "self_attested_payload_fields": ["host_automation_verified", "host_automation_id"],
                "reviewer_direct_check_required": True,
            }
        )
    if answers.get("display_surface") == "cockpit":
        requirements.append(
            {
                "id": "cockpit_or_display_fallback_reality",
                "reason": "Router can record selected display mode and chat fallback, but live Cockpit availability or fallback necessity requires direct review when requested.",
                "self_attested_payload_fields": ["display_surface"],
                "reviewer_direct_check_required": True,
            }
        )
    return requirements


def _startup_fact_review_ownership(
    computed_checks: dict[str, bool],
    external_requirements: list[dict[str, Any]],
) -> dict[str, Any]:
    reviewer_ids = {str(item["id"]) for item in external_requirements if item.get("id")}
    router_owned = sorted(computed_checks)
    reviewer_owned = sorted(reviewer_ids)
    pm_decision_owned = ["startup_user_answer_authenticity"]
    covered = set(router_owned) | set(reviewer_owned) | set(pm_decision_owned)
    known = set(computed_checks) | reviewer_ids | set(pm_decision_owned)
    unowned = sorted(known - covered)
    return {
        "router_owned_mechanical_checks": router_owned,
        "reviewer_owned_external_fact_ids": reviewer_owned,
        "pm_decision_owned_unreviewable_fact_ids": pm_decision_owned,
        "unowned_fact_ids": unowned,
        "all_required_facts_have_owner": not unowned,
    }


def _write_startup_mechanical_audit(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    computed_checks: dict[str, bool],
) -> dict[str, Any]:
    audit_path = run_root / "startup" / "startup_mechanical_audit.json"
    proof_path = _router_owned_check_proof_path(audit_path)
    evidence_paths = [
        run_root / "startup_answers.json",
        project_root / ".flowpilot" / "current.json",
        project_root / ".flowpilot" / "index.json",
        run_root / "crew_ledger.json",
        _continuation_binding_path(run_root),
        run_state_path(run_root),
    ]
    external_requirements = _startup_external_fact_requirements(run_root, run_state)
    review_ownership = _startup_fact_review_ownership(computed_checks, external_requirements)
    audit = {
        "schema_version": STARTUP_MECHANICAL_AUDIT_SCHEMA,
        "run_id": run_state["run_id"],
        "check_owner": "flowpilot_router",
        "mechanical_checks": computed_checks,
        "mechanical_checks_passed": all(computed_checks.values()),
        "router_replacement_scope": "mechanical_only",
        "self_attested_ai_claims_accepted_as_proof": False,
        "fact_review_ownership": review_ownership,
        "reviewer_required_external_facts": external_requirements,
        "router_owned_check_proof_path": project_relative(project_root, proof_path),
        "source_paths": [_evidence_path_record(project_root, path) for path in evidence_paths],
        "written_at": utc_now(),
    }
    if not review_ownership["all_required_facts_have_owner"]:
        raise RouterError("startup fact ownership map left unowned requirements")
    write_json(audit_path, audit)
    proof_record = _write_router_owned_check_proof(
        project_root,
        run_root,
        check_name="startup_mechanical_checks",
        audit_path=audit_path,
        source_kind="router_computed",
        evidence_paths=evidence_paths,
    )
    _validate_router_owned_check_proof(
        project_root,
        run_root,
        check_name="startup_mechanical_checks",
        audit_path=audit_path,
    )
    audit["router_owned_check_proof"] = {
        "path": proof_record["proof_path"],
        "schema_version": ROUTER_OWNED_CHECK_PROOF_SCHEMA,
    }
    return audit


def _startup_mechanical_audit_context(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
) -> dict[str, Any] | None:
    audit_path = run_root / "startup" / "startup_mechanical_audit.json"
    if not audit_path.exists():
        return None
    audit = read_json_if_exists(audit_path)
    if audit.get("schema_version") != STARTUP_MECHANICAL_AUDIT_SCHEMA:
        return None
    if audit.get("run_id") != run_state.get("run_id"):
        return None
    try:
        proof = _validate_router_owned_check_proof(
            project_root,
            run_root,
            check_name="startup_mechanical_checks",
            audit_path=audit_path,
        )
    except RouterError:
        return None
    proof_path = _router_owned_check_proof_path(audit_path)
    return {
        "audit": audit,
        "audit_path": audit_path,
        "audit_hash": packet_runtime.sha256_file(audit_path),
        "proof": proof,
        "proof_path": proof_path,
        "proof_hash": packet_runtime.sha256_file(proof_path) if proof_path.exists() else None,
    }


def _startup_mechanical_audit_action_extra(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
) -> dict[str, Any]:
    context = _startup_mechanical_audit_context(project_root, run_root, run_state)
    if context is None:
        raise RouterError("startup mechanical audit must be written before reviewer startup fact card delivery")
    return {
        "startup_mechanical_audit_path": project_relative(project_root, context["audit_path"]),
        "startup_mechanical_audit_hash": context["audit_hash"],
        "router_owned_check_proof_path": project_relative(project_root, context["proof_path"]),
        "router_owned_check_proof_hash": context["proof_hash"],
        "router_computable_checks_already_enforced": True,
        "reviewer_should_not_reprove_router_computable_checks": True,
        "reviewer_required_external_facts": context["audit"].get("reviewer_required_external_facts") or [],
        "router_replacement_scope": "mechanical_only",
    }


def _validate_startup_external_fact_review(
    payload: dict[str, Any],
    requirements: list[dict[str, Any]],
    *,
    startup_mechanical_audit_hash: str | None = None,
) -> dict[str, Any]:
    if not requirements:
        return {
            "reviewed_by_role": "human_like_reviewer",
            "reviewer_required_external_fact_count": 0,
            "reviewer_checked_requirement_ids": [],
            "self_attested_ai_claims_accepted_as_proof": False,
        }
    review = payload.get("external_fact_review")
    if not isinstance(review, dict):
        raise RouterError("startup fact report requires external_fact_review for non-router-checkable facts")
    if review.get("reviewed_by_role") != "human_like_reviewer":
        raise RouterError("external_fact_review must be reviewed_by_role=human_like_reviewer")
    if (
        startup_mechanical_audit_hash
        and review.get("router_mechanical_audit_hash") is not None
        and review.get("router_mechanical_audit_hash") != startup_mechanical_audit_hash
    ):
        raise RouterError("external_fact_review must reference the current startup mechanical audit hash")
    if review.get("self_attested_ai_claims_accepted_as_proof") is not False:
        raise RouterError("external_fact_review cannot accept self-attested AI claims as proof")
    checked_ids = review.get("reviewer_checked_requirement_ids")
    if not isinstance(checked_ids, list):
        raise RouterError("external_fact_review requires reviewer_checked_requirement_ids list")
    checked = {str(item) for item in checked_ids}
    required = {str(item["id"]) for item in requirements if item.get("id")}
    missing = sorted(required - checked)
    if missing:
        raise RouterError(f"external_fact_review missing required checks: {', '.join(missing)}")
    direct_paths = review.get("direct_evidence_paths_checked")
    if not isinstance(direct_paths, list) or not direct_paths:
        raise RouterError("external_fact_review requires direct_evidence_paths_checked")
    return {
        "reviewed_by_role": "human_like_reviewer",
        "reviewer_required_external_fact_count": len(requirements),
        "reviewer_checked_requirement_ids": sorted(checked),
        "direct_evidence_paths_checked": direct_paths,
        "self_attested_ai_claims_accepted_as_proof": False,
        "notes": review.get("notes"),
    }


def _write_startup_fact_report(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    canonical_report_path = run_root / "startup" / "startup_fact_report.json"
    envelope = payload.get("_role_output_envelope")
    if isinstance(envelope, dict) and envelope.get("body_path"):
        source_path = resolve_project_path(project_root, str(envelope["body_path"]))
        if source_path.resolve() == canonical_report_path.resolve():
            raise RouterError("startup fact source report_path must not be the router canonical startup_fact_report.json")
    if payload.get("reviewed_by_role") != "human_like_reviewer":
        raise RouterError("startup fact report must be reviewed_by_role=human_like_reviewer")
    computed_checks = _startup_fact_checks(project_root, run_root, run_state)
    claimed_checks = payload.get("checks") if isinstance(payload.get("checks"), dict) else {}
    false_claims = [name for name, value in claimed_checks.items() if value is not True]
    passed = payload.get("passed") is True
    if passed and false_claims:
        raise RouterError(f"startup fact report contains failed checks: {', '.join(sorted(false_claims))}")
    blockers = [name for name, ok in computed_checks.items() if not ok]
    if passed and blockers:
        raise RouterError(f"startup facts are not clean: {', '.join(sorted(blockers))}")
    mechanical_context = _startup_mechanical_audit_context(project_root, run_root, run_state)
    if mechanical_context is None:
        raise RouterError("startup mechanical audit must be written before reviewer startup fact report")
    mechanical_audit = mechanical_context["audit"]
    if mechanical_audit.get("mechanical_checks") != computed_checks:
        raise RouterError("startup mechanical audit is stale; rewrite it before reviewer startup fact report")
    external_fact_review = _validate_startup_external_fact_review(
        payload,
        mechanical_audit["reviewer_required_external_facts"],
        startup_mechanical_audit_hash=mechanical_context["audit_hash"],
    )
    write_json(
        canonical_report_path,
        {
            "schema_version": "flowpilot.startup_fact_report.v1",
            "run_id": run_state["run_id"],
            "reviewed_by_role": "human_like_reviewer",
            "passed": passed,
            "status": "pass" if passed else "findings",
            "checks": computed_checks,
            "reviewer_claimed_checks": claimed_checks,
            "reviewer_reported_blockers": payload.get("blockers") if isinstance(payload.get("blockers"), list) else false_claims or blockers,
            "startup_mechanical_audit_path": project_relative(project_root, mechanical_context["audit_path"]),
            "startup_mechanical_audit_hash": mechanical_context["audit_hash"],
            "router_owned_check_proof_path": project_relative(project_root, mechanical_context["proof_path"]),
            "router_owned_check_proof_hash": mechanical_context["proof_hash"],
            "reviewer_required_external_facts": mechanical_audit["reviewer_required_external_facts"],
            "external_fact_review": external_fact_review,
            "requires_pm_startup_decision": not passed,
            "reviewer_directly_blocks_route": False,
            "reported_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )


def _write_startup_activation(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("approved_by_role") != "project_manager":
        raise RouterError("PM startup activation requires approved_by_role=project_manager")
    if payload.get("decision") != "approved":
        raise RouterError("PM startup activation requires decision=approved")
    fact_report = read_json_if_exists(run_root / "startup" / "startup_fact_report.json")
    fact_report_path = run_root / "startup" / "startup_fact_report.json"
    if not fact_report_path.exists():
        raise RouterError("PM startup activation requires reviewer startup_fact_report.json")
    clean_report = fact_report.get("passed") is True and fact_report.get("status") == "pass"
    approval_basis = "clean_reviewer_fact_report"
    findings_decision: dict[str, Any] | None = None
    if not clean_report:
        if fact_report.get("status") != "findings" or fact_report.get("requires_pm_startup_decision") is not True:
            raise RouterError("PM startup activation requires a passing reviewer startup fact report or PM findings decision")
        if payload.get("accepts_startup_findings_with_reason") is not True:
            raise RouterError("PM startup activation from reviewer findings requires accepts_startup_findings_with_reason=true")
        reason = str(payload.get("startup_findings_decision_reason") or "").strip()
        if not reason:
            raise RouterError("PM startup activation from reviewer findings requires startup_findings_decision_reason")
        reviewed_report = payload.get("reviewed_report_path") or project_relative(project_root, fact_report_path)
        if resolve_project_path(project_root, str(reviewed_report)).resolve() != fact_report_path.resolve():
            raise RouterError("PM startup activation reviewed_report_path must reference startup_fact_report.json")
        decision_kind = str(payload.get("startup_findings_decision") or "waived_with_reason")
        if decision_kind not in {"waived_with_reason", "unreviewable_requirement_demoted", "accepted_with_documented_risk"}:
            raise RouterError("PM startup activation startup_findings_decision is invalid")
        approval_basis = "pm_file_backed_findings_decision"
        findings_decision = {
            "startup_findings_decision": decision_kind,
            "startup_findings_decision_reason": reason,
            "reviewed_report_path": project_relative(project_root, fact_report_path),
            "reviewed_report_hash": packet_runtime.sha256_file(fact_report_path),
            "reviewer_findings_accepted_by_pm": True,
            "demoted_unreviewable_requirement_ids": payload.get("demoted_unreviewable_requirement_ids")
            if isinstance(payload.get("demoted_unreviewable_requirement_ids"), list)
            else [],
        }
    answers = _startup_answers_from_run(run_root)
    activation = {
        "schema_version": "flowpilot.startup_activation.v1",
        "run_id": run_state["run_id"],
        "approved_by_role": "project_manager",
        "decision": "approved",
        "background_agents": answers.get("background_agents"),
        "scheduled_continuation": answers.get("scheduled_continuation"),
        "display_surface": answers.get("display_surface"),
        "fact_report_path": project_relative(project_root, fact_report_path),
        "approval_basis": approval_basis,
        "approved_at": utc_now(),
        **_role_output_envelope_record(payload),
    }
    if findings_decision is not None:
        activation["pm_findings_decision"] = findings_decision
    write_json(run_root / "startup" / "startup_activation.json", activation)


def _write_startup_repair_request(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("decided_by_role") != "project_manager":
        raise RouterError("startup repair request requires decided_by_role=project_manager")
    if payload.get("decision") not in {"startup_repair_requested", "repair_requested"}:
        raise RouterError("startup repair request requires decision=startup_repair_requested")
    target = str(payload.get("target_role_or_system") or "").strip()
    allowed_targets = {"flowpilot_router", "human_like_reviewer", "project_manager", "worker_a", "worker_b"}
    if target not in allowed_targets:
        raise RouterError(f"startup repair request target_role_or_system must be one of: {', '.join(sorted(allowed_targets))}")
    repair_action = str(payload.get("repair_action") or "").strip()
    if not repair_action:
        raise RouterError("startup repair request requires repair_action")
    fact_report = read_json_if_exists(run_root / "startup" / "startup_fact_report.json")
    if fact_report.get("passed") is True:
        raise RouterError("startup repair request requires a non-passing reviewer startup fact report")
    current_blocked_report_path = run_root / "startup" / "startup_fact_report.json"
    if not current_blocked_report_path.exists():
        raise RouterError("startup repair request requires the current non-passing startup_fact_report.json")
    requested_blocked_report = payload.get("blocked_report_path") or project_relative(project_root, current_blocked_report_path)
    requested_blocked_report_path = resolve_project_path(project_root, str(requested_blocked_report))
    if requested_blocked_report_path.resolve() != current_blocked_report_path.resolve():
        raise RouterError("startup repair request blocked_report_path must be the current canonical startup_fact_report.json")
    blocked_report_hash = packet_runtime.sha256_file(current_blocked_report_path)
    envelope = payload.get("_role_output_envelope") if isinstance(payload.get("_role_output_envelope"), dict) else {}
    decision_hash = str(envelope.get("body_hash") or "")
    if not decision_hash:
        raise RouterError("startup repair request requires a file-backed PM decision hash")
    previous_request = run_state.get("startup_repair_request") if isinstance(run_state.get("startup_repair_request"), dict) else {}
    last_decision_hash = str(previous_request.get("decision_hash") or "")
    if last_decision_hash and decision_hash == last_decision_hash:
        raise RouterError(
            "startup repair request repeats the previous PM decision; write a fresh PM decision for the current blocking report"
        )
    startup_repair_cycle = int(run_state.get("startup_repair_cycle") or 0) + 1
    record = {
        "schema_version": "flowpilot.startup_repair_request.v1",
        "run_id": run_state["run_id"],
        "startup_repair_cycle": startup_repair_cycle,
        "decided_by_role": "project_manager",
        "decision": "startup_repair_requested",
        "repair_target_kind": payload.get("repair_target_kind") or ("system" if target == "flowpilot_router" else "role"),
        "target_role_or_system": target,
        "repair_action": repair_action,
        "blocked_report_path": project_relative(project_root, current_blocked_report_path),
        "blocked_report_hash": blocked_report_hash,
        "decision_path": envelope.get("body_path"),
        "decision_hash": decision_hash,
        "resume_event": payload.get("resume_event") or "reviewer_reports_startup_facts",
        "resume_condition": payload.get("resume_condition") or "targeted startup repair is complete and reviewer writes a fresh startup fact report",
        "controller_may_invent_repair": False,
        "recorded_at": utc_now(),
        **_role_output_envelope_record(payload),
    }
    cycle_path = run_root / "startup" / f"startup_repair_request.cycle-{startup_repair_cycle:03d}.json"
    write_json(cycle_path, record)
    write_json(run_root / "startup" / "startup_repair_request.json", record)
    ledger_path = run_root / "startup" / "startup_repair_requests.json"
    ledger = read_json_if_exists(ledger_path)
    entries = ledger.get("entries") if isinstance(ledger.get("entries"), list) else []
    entries.append(
        {
            "startup_repair_cycle": startup_repair_cycle,
            "path": project_relative(project_root, cycle_path),
            "blocked_report_path": record["blocked_report_path"],
            "blocked_report_hash": blocked_report_hash,
            "decision_path": record["decision_path"],
            "decision_hash": decision_hash,
            "target_role_or_system": target,
            "repair_action": repair_action,
            "recorded_at": record["recorded_at"],
        }
    )
    write_json(
        ledger_path,
        {
            "schema_version": "flowpilot.startup_repair_requests.v1",
            "run_id": run_state["run_id"],
            "entries": entries,
            "latest_cycle": startup_repair_cycle,
            "updated_at": utc_now(),
        },
    )
    for flag in (
        "startup_fact_reported",
        "pm_startup_activation_card_delivered",
        "startup_activation_approved",
        "startup_mechanical_audit_written",
        "reviewer_startup_fact_check_card_delivered",
    ):
        run_state["flags"][flag] = False
    run_state["startup_repair_cycle"] = startup_repair_cycle
    run_state["startup_repair_request"] = {
        "path": project_relative(project_root, run_root / "startup" / "startup_repair_request.json"),
        "cycle_path": project_relative(project_root, cycle_path),
        "ledger_path": project_relative(project_root, ledger_path),
        "startup_repair_cycle": startup_repair_cycle,
        "target_role_or_system": target,
        "repair_action": repair_action,
        "blocked_report_hash": blocked_report_hash,
        "decision_hash": decision_hash,
        "resume_event": record["resume_event"],
    }


def _write_startup_protocol_dead_end(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("declared_by_role") != "project_manager":
        raise RouterError("startup protocol dead-end requires declared_by_role=project_manager")
    if payload.get("decision") != "protocol_dead_end":
        raise RouterError("startup protocol dead-end requires decision=protocol_dead_end")
    if payload.get("no_legal_repair_path") is not True:
        raise RouterError("startup protocol dead-end requires no_legal_repair_path=true")
    reason = str(payload.get("why_no_existing_path_applies") or "").strip()
    if not reason:
        raise RouterError("startup protocol dead-end requires why_no_existing_path_applies")
    attempted_paths = payload.get("attempted_legal_paths")
    if not isinstance(attempted_paths, list) or not attempted_paths:
        raise RouterError("startup protocol dead-end requires attempted_legal_paths")
    resume_conditions = payload.get("resume_conditions")
    if not isinstance(resume_conditions, list) or not resume_conditions:
        raise RouterError("startup protocol dead-end requires resume_conditions")
    fact_report = read_json_if_exists(run_root / "startup" / "startup_fact_report.json")
    if fact_report.get("passed") is True:
        raise RouterError("startup protocol dead-end requires a non-passing reviewer startup fact report")
    dead_end_path = run_root / "lifecycle" / "startup_protocol_dead_end.json"
    record = {
        "schema_version": "flowpilot.startup_protocol_dead_end.v1",
        "run_id": run_state["run_id"],
        "declared_by_role": "project_manager",
        "decision": "protocol_dead_end",
        "dead_end_type": payload.get("dead_end_type") or "startup_block_has_no_protocol_route",
        "no_legal_repair_path": True,
        "why_no_existing_path_applies": reason,
        "attempted_legal_paths": attempted_paths,
        "conceptual_repair_direction": payload.get("conceptual_repair_direction"),
        "unsafe_to_continue_reason": payload.get("unsafe_to_continue_reason") or reason,
        "blocked_report_path": payload.get("blocked_report_path") or project_relative(project_root, run_root / "startup" / "startup_fact_report.json"),
        "effects": {
            "freeze_run": True,
            "cancel_or_suspend_pending_mail": True,
            "prevent_work_beyond_startup": True,
            "heartbeat_should_stop": False,
            "heartbeat_should_remain_for_resume_or_user_decision": True,
            **(payload.get("effects") if isinstance(payload.get("effects"), dict) else {}),
        },
        "resume_conditions": resume_conditions,
        "controller_may_continue_route_work": False,
        "controller_may_spawn_new_role_work": False,
        "declared_at": utc_now(),
        **_role_output_envelope_record(payload),
    }
    write_json(dead_end_path, record)
    run_state["flags"]["startup_pending_mail_suspended_after_dead_end"] = True
    _write_protocol_dead_end_lifecycle(
        project_root,
        run_root,
        run_state,
        dead_end_path=dead_end_path,
        reason=reason,
    )


def _route_sign_payload(
    project_root: Path,
    *,
    write: bool,
    trigger: str,
    mark_chat_displayed: bool,
    cockpit_open: bool = False,
    mark_ui_displayed: bool = False,
) -> dict[str, Any]:
    return flowpilot_user_flow_diagram.generate(
        project_root,
        write=write,
        trigger=trigger,
        cockpit_open=cockpit_open,
        display_surface="both" if cockpit_open else "chat",
        mark_chat_displayed=mark_chat_displayed,
        mark_ui_displayed=mark_ui_displayed,
        reviewer_check=False,
    )


def _startup_route_sign_payload(project_root: Path, *, write: bool, mark_chat_displayed: bool) -> dict[str, Any]:
    return _route_sign_payload(
        project_root,
        write=write,
        trigger="startup",
        mark_chat_displayed=mark_chat_displayed,
    )


def _route_map_route_sign_payload(project_root: Path, *, write: bool, mark_chat_displayed: bool) -> dict[str, Any]:
    return _route_sign_payload(
        project_root,
        write=write,
        trigger="key_node_change",
        mark_chat_displayed=mark_chat_displayed,
    )


def _route_sign_has_canonical_route(payload: dict[str, Any]) -> bool:
    return (
        payload.get("flowpilot_path_status") == "ok"
        and int(payload.get("route_node_count") or 0) > 0
        and str(payload.get("route_source_kind") or "none") != "none"
    )


def _display_surface_receipt_from_payload(
    payload: dict[str, Any],
    *,
    run_id: str,
    requested: str,
    selected_surface: str,
) -> dict[str, Any]:
    receipt = payload.get("display_surface_receipt") if isinstance(payload, dict) else None
    if receipt is None:
        return {
            "schema_version": DISPLAY_SURFACE_RECEIPT_SCHEMA,
            "run_id": run_id,
            "requested_display_surface": requested,
            "actual_surface": selected_surface,
            "source_kind": "controller_user_dialog_render",
            "host_display_surface_verified": False,
            "fallback_displayed": selected_surface != "cockpit",
            "recorded_at": utc_now(),
        }
    if not isinstance(receipt, dict):
        raise RouterError("display_surface_receipt must be an object when supplied")
    if receipt.get("schema_version") != DISPLAY_SURFACE_RECEIPT_SCHEMA:
        raise RouterError(f"display_surface_receipt requires schema_version={DISPLAY_SURFACE_RECEIPT_SCHEMA}")
    actual = receipt.get("actual_surface")
    if actual not in {"chat_route_sign", "chat_route_sign_fallback", "cockpit"}:
        raise RouterError("display_surface_receipt.actual_surface must be chat_route_sign, chat_route_sign_fallback, or cockpit")
    if receipt.get("run_id") not in {None, run_id}:
        raise RouterError("display_surface_receipt.run_id must match current run_id")
    if actual == "cockpit" and receipt.get("host_display_surface_verified") is not True:
        raise RouterError("display_surface_receipt for cockpit requires host_display_surface_verified=true")
    return {
        "schema_version": DISPLAY_SURFACE_RECEIPT_SCHEMA,
        "run_id": run_id,
        "requested_display_surface": requested,
        "actual_surface": actual,
        "source_kind": str(receipt.get("source_kind") or "host_receipt"),
        "host_display_surface_verified": bool(receipt.get("host_display_surface_verified")),
        "fallback_displayed": bool(receipt.get("fallback_displayed", actual != "cockpit")),
        "host_surface_id": receipt.get("host_surface_id"),
        "notes": receipt.get("notes"),
        "recorded_at": utc_now(),
    }


def _write_display_surface_status(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    display_confirmation: dict[str, Any],
    payload: dict[str, Any] | None = None,
) -> None:
    answers = _startup_answers_from_run(run_root)
    requested = str(answers.get("display_surface") or "chat route signs")
    requested_normalized = requested.lower()
    selected_surface = "chat_route_sign" if "chat" in requested_normalized else "chat_route_sign_fallback"
    display_receipt = _display_surface_receipt_from_payload(
        payload or {},
        run_id=str(run_state["run_id"]),
        requested=requested,
        selected_surface=selected_surface,
    )
    actual_surface = str(display_receipt.get("actual_surface") or selected_surface)
    if actual_surface == "cockpit":
        selected_surface = "cockpit"
    route_sign = _startup_route_sign_payload(project_root, write=True, mark_chat_displayed=True)
    sign_path = run_root / "diagrams" / "current_route_sign.md"
    sign_path.parent.mkdir(parents=True, exist_ok=True)
    sign_path.write_text(route_sign["markdown"], encoding="utf-8")
    write_json(
        run_root / "display" / "display_surface.json",
        {
            "schema_version": "flowpilot.display_surface.v1",
            "run_id": run_state["run_id"],
            "requested_display_surface": requested,
            "selected_surface": selected_surface,
            "actual_display_surface": actual_surface,
            "chat_route_sign_path": project_relative(project_root, sign_path),
            "standard_route_sign_markdown_path": project_relative(project_root, Path(route_sign["markdown_preview_path"])),
            "standard_route_sign_mermaid_path": project_relative(project_root, Path(route_sign["mermaid_path"])),
            "standard_route_sign_display_packet_path": project_relative(project_root, Path(route_sign["display_packet_path"])),
            "route_sign_mermaid_sha256": route_sign["mermaid_sha256"],
            "chat_display_required": route_sign["chat_display_required"],
            "chat_displayed_by_controller": True,
            "user_dialog_display_confirmation": display_confirmation,
            "display_surface_receipt": display_receipt,
            "host_display_surface_verified": bool(display_receipt.get("host_display_surface_verified")),
            "generated_files_alone_satisfy_chat_display": False,
            "controller_display_rule": "Controller must paste the router-provided display_text Mermaid block in chat before applying this action; generated files alone do not satisfy display.",
            "cockpit_status": "host_verified_open" if selected_surface == "cockpit" else "not_started_in_router_runtime",
            "cockpit_probe_required_for_requested_cockpit": "cockpit" in requested_normalized,
            "reviewer_fallback_check_required_for_requested_cockpit": "cockpit" in requested_normalized,
            "fallback_is_display_only_not_product_ui_completion": True,
            "updated_at": utc_now(),
        },
    )


def _material_packet_body_text_from_spec(project_root: Path, spec: dict[str, Any]) -> str:
    body_text = spec.get("body_text")
    if isinstance(body_text, str) and body_text.strip():
        return body_text
    raw_body_path = spec.get("body_path") or spec.get("packet_body_path")
    raw_body_hash = spec.get("body_hash") or spec.get("packet_body_hash")
    if not raw_body_path or not raw_body_hash:
        raise RouterError("material scan packet requires non-empty body_text or file-backed body_path/body_hash")
    body_path = resolve_project_path(project_root, str(raw_body_path))
    if not body_path.exists():
        raise RouterError(f"material scan packet body path is missing: {raw_body_path}")
    actual_hash = hashlib.sha256(body_path.read_bytes()).hexdigest()
    if actual_hash != str(raw_body_hash):
        raise RouterError("material scan packet body hash mismatch")
    loaded_text = body_path.read_text(encoding="utf-8")
    if not loaded_text.strip():
        raise RouterError("material scan packet body file is empty")
    return loaded_text


def _write_material_scan_packets(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    packet_specs = payload.get("packets")
    if not isinstance(packet_specs, list) or not packet_specs:
        raise RouterError("material scan requires payload.packets with PM-authored packet bodies")
    records: list[dict[str, Any]] = []
    for index, spec in enumerate(packet_specs, start=1):
        if not isinstance(spec, dict):
            raise RouterError("each material scan packet must be an object")
        packet_id = str(spec.get("packet_id") or f"material-scan-{index:03d}")
        to_role = str(spec.get("to_role") or "worker_a")
        if to_role not in {"worker_a", "worker_b"}:
            raise RouterError("material scan packet must target worker_a or worker_b")
        body_text = _material_packet_body_text_from_spec(project_root, spec)
        envelope = packet_runtime.create_packet(
            project_root,
            run_id=str(run_state["run_id"]),
            packet_id=packet_id,
            from_role="project_manager",
            to_role=to_role,
            node_id=str(spec.get("node_id") or "material-intake"),
            body_text=body_text,
            is_current_node=False,
            packet_type="material_scan",
            metadata={
                "stage": "material_scan",
                "source": "pm_issues_material_and_capability_scan_packets",
                **(spec.get("metadata") if isinstance(spec.get("metadata"), dict) else {}),
            },
            output_contract=spec.get("output_contract") if isinstance(spec.get("output_contract"), dict) else None,
        )
        paths = packet_runtime.packet_paths(project_root, packet_id, str(run_state["run_id"]))
        records.append(
            {
                "packet_id": packet_id,
                "to_role": to_role,
                "packet_envelope_path": envelope["body_path"].replace("packet_body.md", "packet_envelope.json"),
                "result_envelope_path": project_relative(project_root, paths["result_envelope"]),
                "result_body_path": project_relative(project_root, paths["result_body"]),
                "result_write_target": {
                    "result_envelope_path": project_relative(project_root, paths["result_envelope"]),
                    "result_body_path": project_relative(project_root, paths["result_body"]),
                },
                "output_contract_id": envelope.get("output_contract_id"),
            }
        )
    write_json(
        _material_scan_index_path(run_root),
        {
            "schema_version": "flowpilot.material_scan_packets.v1",
            "run_id": run_state["run_id"],
            "written_by_role": "project_manager",
            "controller_may_read_packet_body": False,
            "reviewer_dispatch_required_before_worker": True,
            "packets": records,
            "written_at": utc_now(),
        },
    )
    _set_pre_route_frontier_phase(run_root, str(run_state["run_id"]), "material_scan")


def _write_material_dispatch_block_report(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != "human_like_reviewer":
        raise RouterError("material dispatch block report must be reviewed_by_role=human_like_reviewer")
    if payload.get("dispatch_allowed") is not False:
        raise RouterError("material dispatch block report requires dispatch_allowed=false")
    blockers = payload.get("blockers")
    if not isinstance(blockers, list) or not blockers:
        raise RouterError("material dispatch block report requires non-empty blockers")
    material_index_path = _material_scan_index_path(run_root)
    if not material_index_path.exists():
        raise RouterError("material dispatch block report requires material scan packet index")
    report_path = run_root / "material" / "material_dispatch_block.json"
    reported_at = utc_now()
    write_json(
        report_path,
        {
            "schema_version": "flowpilot.material_dispatch_block.v1",
            "run_id": run_state["run_id"],
            "reviewed_by_role": "human_like_reviewer",
            "dispatch_allowed": False,
            "source_paths": [project_relative(project_root, material_index_path)],
            "checks": payload.get("checks") if isinstance(payload.get("checks"), dict) else {},
            "blockers": blockers,
            "residual_risks": payload.get("residual_risks") if isinstance(payload.get("residual_risks"), list) else [],
            "reported_at": reported_at,
            **_role_output_envelope_record(payload),
        },
    )
    run_state["material_dispatch_block"] = {
        "path": project_relative(project_root, report_path),
        "blockers": blockers,
        "reported_at": reported_at,
    }
    run_state["flags"]["reviewer_dispatch_allowed"] = False


def _write_material_dispatch_recheck_protocol_blocker(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != "human_like_reviewer":
        raise RouterError("material dispatch recheck protocol blocker requires reviewed_by_role=human_like_reviewer")
    blockers = payload.get("blockers")
    if not isinstance(blockers, list) or not blockers:
        raise RouterError("material dispatch recheck protocol blocker requires non-empty blockers")
    tx_path, transaction = _active_repair_transaction_for_event(
        run_root,
        "reviewer_protocol_blocker_material_scan_dispatch_recheck",
    )
    if tx_path is None or transaction is None:
        raise RouterError("material dispatch protocol blocker requires an active repair transaction")
    reported_at = utc_now()
    report_path = run_root / "control_blocks" / f"{transaction['transaction_id']}.reviewer_protocol_blocker.json"
    write_json(
        report_path,
        {
            "schema_version": "flowpilot.repair_transaction_protocol_blocker.v1",
            "run_id": run_state["run_id"],
            "repair_transaction_id": transaction["transaction_id"],
            "reviewed_by_role": "human_like_reviewer",
            "event_name": "reviewer_protocol_blocker_material_scan_dispatch_recheck",
            "blockers": blockers,
            "source_paths": payload.get("source_paths") if isinstance(payload.get("source_paths"), list) else [],
            "residual_risks": payload.get("residual_risks") if isinstance(payload.get("residual_risks"), list) else [],
            "reported_at": reported_at,
            **_role_output_envelope_record(payload),
        },
    )
    run_state["material_dispatch_block"] = {
        "path": project_relative(project_root, report_path),
        "blockers": blockers,
        "reported_at": reported_at,
        "repair_transaction_id": transaction["transaction_id"],
        "protocol_blocker": True,
    }
    run_state["flags"]["reviewer_dispatch_allowed"] = False
    run_state["flags"]["material_scan_dispatch_blocked"] = True


def _write_material_sufficiency_report(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any], *, sufficient: bool) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != "human_like_reviewer":
        raise RouterError("material sufficiency report must be reviewed_by_role=human_like_reviewer")
    if not run_state["flags"].get("material_scan_results_relayed_to_reviewer"):
        raise RouterError("material sufficiency report requires Controller-relayed material result envelopes")
    material_index = _load_packet_index(_material_scan_index_path(run_root), label="material scan")
    raw_agent_map = payload.get("agent_role_map")
    _validate_packet_group_for_reviewer(
        project_root,
        run_state,
        material_index["packets"],
        audit_path=run_root / "material" / "material_packet_review_audit.json",
        agent_role_map=raw_agent_map if isinstance(raw_agent_map, dict) else None,
    )
    if payload.get("direct_material_sources_checked") is not True:
        raise RouterError("material sufficiency report requires direct_material_sources_checked=true")
    if payload.get("packet_matches_checked_sources") is not True:
        raise RouterError("material sufficiency report requires packet_matches_checked_sources=true")
    if sufficient and payload.get("pm_ready") is not True:
        raise RouterError("sufficient material report requires pm_ready=true")
    write_json(
        run_root / "material" / "material_sufficiency_report.json",
        {
            "schema_version": "flowpilot.material_sufficiency_report.v1",
            "run_id": run_state["run_id"],
            "reviewed_by_role": "human_like_reviewer",
            "sufficient": sufficient,
            "direct_material_sources_checked": True,
            "packet_matches_checked_sources": True,
            "pm_ready": bool(payload.get("pm_ready")),
            "checked_source_paths": payload.get("checked_source_paths") or [],
            "blockers": payload.get("blockers") or [],
            "reported_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )


def _write_research_package(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    decision_question = payload.get("decision_question")
    if not decision_question:
        raise RouterError("research package requires decision_question")
    package = {
        "schema_version": "flowpilot.research_package.v1",
        "run_id": run_state["run_id"],
        "written_by_role": "project_manager",
        "decision_question": decision_question,
        "allowed_source_types": payload.get("allowed_source_types") or [],
        "host_capability_decision": payload.get("host_capability_decision") or "local_sources_only",
        "worker_owner": payload.get("worker_owner") or "worker_a",
        "reviewer_direct_check_required": True,
        "stop_conditions": payload.get("stop_conditions") or [],
        "written_at": utc_now(),
        **_role_output_envelope_record(payload),
    }
    write_json(run_root / "research" / "research_package.json", package)


def _write_research_capability_decision(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    package_path = run_root / "research" / "research_package.json"
    if not package_path.exists():
        raise RouterError("research capability decision requires research_package.json")
    if payload.get("explicit_user_approval_required") is True and payload.get("explicit_user_approval_recorded") is not True:
        raise RouterError("research capability decision requires recorded user approval for gated sources")
    package = read_json(package_path)
    worker_owner = str(package.get("worker_owner") or "worker_a")
    if worker_owner not in {"worker_a", "worker_b"}:
        raise RouterError("research worker owner must be worker_a or worker_b")
    packet_id = str(payload.get("packet_id") or "research-packet-001")
    allowed_source_types = list(package.get("allowed_source_types") or [])
    allowed_sources = payload.get("allowed_sources")
    if not isinstance(allowed_sources, list) or not allowed_sources:
        allowed_sources = allowed_source_types
    stop_conditions = list(package.get("stop_conditions") or [])
    research_body_payload = {
        "research_package_path": project_relative(project_root, package_path),
        "decision_question": package.get("decision_question"),
        "allowed_source_types": allowed_source_types,
        "allowed_sources": allowed_sources,
        "host_capability_decision": package.get("host_capability_decision"),
        "worker_owner": worker_owner,
        "reviewer_direct_check_required": bool(package.get("reviewer_direct_check_required")),
        "stop_conditions": stop_conditions,
    }
    body_text = payload.get("worker_packet_body")
    if body_text is None:
        body_text = json.dumps(research_body_payload, indent=2, sort_keys=True)
    if not isinstance(body_text, str) or not body_text.strip():
        raise RouterError("research capability decision requires non-empty worker packet body")
    envelope = packet_runtime.create_packet(
        project_root,
        run_id=str(run_state["run_id"]),
        packet_id=packet_id,
        from_role="project_manager",
        to_role=worker_owner,
        node_id="research",
        body_text=body_text,
        is_current_node=False,
        packet_type="research",
        metadata={
            "stage": "research",
            "source": "research_capability_decision_recorded",
            "research_package_path": project_relative(project_root, package_path),
        },
        output_contract=payload.get("output_contract") if isinstance(payload.get("output_contract"), dict) else None,
    )
    packet_paths = packet_runtime.packet_paths(project_root, packet_id, str(run_state["run_id"]))
    write_json(
        run_root / "research" / "research_capability_decision.json",
        {
            "schema_version": "flowpilot.research_capability_decision.v1",
            "run_id": run_state["run_id"],
            "recorded_by_role": "project_manager",
            "research_package_path": project_relative(project_root, package_path),
            "decision_question": package.get("decision_question"),
            "allowed_source_types": allowed_source_types,
            "allowed_sources": allowed_sources,
            "host_capability_decision": package.get("host_capability_decision"),
            "worker_owner": worker_owner,
            "reviewer_direct_check_required": bool(package.get("reviewer_direct_check_required")),
            "stop_conditions": stop_conditions,
            "explicit_user_approval_required": bool(payload.get("explicit_user_approval_required")),
            "explicit_user_approval_recorded": bool(payload.get("explicit_user_approval_recorded")),
            "worker_packet_id": packet_id,
            "recorded_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )
    write_json(
        _research_packet_index_path(run_root),
        {
            "schema_version": "flowpilot.research_packet.v1",
            "run_id": run_state["run_id"],
            "written_by_role": "project_manager",
            "packet_id": packet_id,
            "worker_owner": worker_owner,
            "controller_may_read_packet_body": False,
            "packet_envelope_path": envelope["body_path"].replace("packet_body.md", "packet_envelope.json"),
            "packet_body_path": envelope["body_path"],
            "packet_body_hash": envelope["body_hash"],
            "body_path": envelope["body_path"],
            "body_hash": envelope["body_hash"],
            "result_envelope_path": project_relative(project_root, packet_paths["result_envelope"]),
            "packets": [
                {
                    "packet_id": packet_id,
                    "to_role": worker_owner,
                    "packet_envelope_path": envelope["body_path"].replace("packet_body.md", "packet_envelope.json"),
                    "packet_body_path": envelope["body_path"],
                    "packet_body_hash": envelope["body_hash"],
                    "body_path": envelope["body_path"],
                    "body_hash": envelope["body_hash"],
                    "result_envelope_path": project_relative(project_root, packet_paths["result_envelope"]),
                }
            ],
            "written_at": utc_now(),
        },
    )


def _write_worker_research_report(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    if not run_state["flags"].get("research_packet_relayed"):
        raise RouterError("research report requires Controller-relayed research packet")
    research_index = _load_packet_index(_research_packet_index_path(run_root), label="research")
    _validate_packet_bodies_opened_by_targets(project_root, run_state, research_index["packets"])
    _validate_results_exist_for_packets(project_root, run_state, research_index["packets"], next_recipient="human_like_reviewer")
    if payload.get("completed_by_role") not in {"worker_a", "worker_b"}:
        raise RouterError("research report must be completed by worker_a or worker_b")
    if not payload.get("answers_decision_question"):
        raise RouterError("research report must state whether it answers the PM decision question")
    write_json(
        run_root / "research" / "worker_research_report.json",
        {
            "schema_version": "flowpilot.research_worker_report.v1",
            "run_id": run_state["run_id"],
            "completed_by_role": payload.get("completed_by_role"),
            "raw_evidence_pointers": payload.get("raw_evidence_pointers") or [],
            "negative_findings": payload.get("negative_findings") or [],
            "contradictions": payload.get("contradictions") or [],
            "confidence_boundary": payload.get("confidence_boundary") or "worker report only; reviewer check required",
            "answers_decision_question": bool(payload.get("answers_decision_question")),
            "reported_at": utc_now(),
        },
    )


def _write_material_understanding(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    if payload.get("pm_owned", True) is not True:
        raise RouterError("material understanding must be PM-owned")
    if run_state["flags"].get("pm_research_requested") and not run_state["flags"].get("research_result_absorbed_by_pm"):
        raise RouterError("PM material understanding requires reviewed research to be absorbed when research was requested")
    payload_snapshot_path = run_root / "material" / "pm_material_understanding_payload.json"
    write_json(
        payload_snapshot_path,
        {
            "schema_version": "flowpilot.pm_material_understanding_payload.v1",
            "run_id": run_state["run_id"],
            "payload_body": _without_role_output_envelope(payload),
            "source_role_output_envelope": _role_output_envelope_record(payload).get("_role_output_envelope"),
            "written_at": utc_now(),
        },
    )
    write_json(
        run_root / "pm_material_understanding.json",
        {
            "schema_version": "flowpilot.pm_material_understanding.v1",
            "run_id": run_state["run_id"],
            "pm_owned": True,
            "source_paths": {
                "payload_snapshot": project_relative(project_root, payload_snapshot_path),
            },
            "source_material_review": run_state.get("material_review"),
            "research_absorbed": bool(run_state["flags"].get("research_result_absorbed_by_pm")),
            "material_summary": payload.get("material_summary") or "",
            "contradictions": payload.get("contradictions") or [],
            "deferred_sources": payload.get("deferred_sources") or [],
            "route_consequences": payload.get("route_consequences") or [],
            "written_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )


def _write_product_function_architecture(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    if payload.get("pm_owned", True) is not True:
        raise RouterError("product-function architecture must be PM-owned")
    material_understanding_path = run_root / "pm_material_understanding.json"
    if not material_understanding_path.exists():
        raise RouterError("product-function architecture requires pm_material_understanding.json")
    required_lists = ("user_task_map", "product_capability_map", "feature_decisions", "functional_acceptance_matrix")
    missing_lists = [name for name in required_lists if not isinstance(payload.get(name), list) or not payload.get(name)]
    if missing_lists:
        raise RouterError(f"product-function architecture requires non-empty lists: {', '.join(missing_lists)}")
    if not isinstance(payload.get("highest_achievable_product_target"), dict) or not payload.get("highest_achievable_product_target"):
        raise RouterError("product-function architecture requires highest_achievable_product_target")
    semantic_policy = payload.get("semantic_fidelity_policy")
    if not isinstance(semantic_policy, dict) or semantic_policy.get("silent_downgrade_forbidden") is not True:
        raise RouterError("product-function architecture requires semantic_fidelity_policy.silent_downgrade_forbidden=true")
    root_requirements = payload.get("functional_acceptance_matrix")
    if not isinstance(root_requirements, list):
        raise RouterError("functional_acceptance_matrix must be a list when provided")
    architecture = {
        "schema_version": "flowpilot.product_function_architecture.v1",
        "run_id": run_state["run_id"],
        "status": str(payload.get("status") or "draft"),
        "pm_owned": True,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "source_paths": {
            "startup_answers": project_relative(project_root, run_root / "startup_answers.json"),
            "startup_activation": project_relative(project_root, run_root / "startup" / "startup_activation.json"),
            "display_surface": project_relative(project_root, run_root / "display" / "display_surface.json"),
            "pm_material_understanding": project_relative(project_root, material_understanding_path),
        },
        "source_material_review": run_state.get("material_review"),
        "high_standard_posture": payload.get("high_standard_posture") or {"highest_reasonably_achievable_is_floor": True},
        "unacceptable_result_review": payload.get("unacceptable_result_review") or [],
        "user_task_map": payload.get("user_task_map"),
        "product_capability_map": payload.get("product_capability_map"),
        "feature_decisions": payload.get("feature_decisions"),
        "display_rationale": payload.get("display_rationale") or [],
        "missing_feature_review": payload.get("missing_feature_review") or [],
        "negative_scope": payload.get("negative_scope") or [],
        "semantic_fidelity_policy": semantic_policy,
        "highest_achievable_product_target": payload.get("highest_achievable_product_target"),
        "functional_acceptance_matrix": root_requirements,
        "written_by_role": "project_manager",
        **_role_output_envelope_record(payload),
    }
    write_json(run_root / "product_function_architecture.json", architecture)


def _write_role_gate_report(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    expected_role: str,
    path: Path,
    schema_version: str,
    checked_paths: list[Path],
) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != expected_role:
        raise RouterError(f"gate report must be reviewed_by_role={expected_role}")
    if payload.get("passed") is not True:
        raise RouterError("gate report must explicitly pass")
    missing = [project_relative(project_root, item) for item in checked_paths if not item.exists()]
    if missing:
        raise RouterError(f"gate report is missing source paths: {', '.join(missing)}")
    write_json(
        path,
        {
            "schema_version": schema_version,
            "run_id": run_state["run_id"],
            "reviewed_by_role": expected_role,
            "passed": True,
            "source_paths": [project_relative(project_root, item) for item in checked_paths],
            "residual_blindspots": payload.get("residual_blindspots") or [],
            "reported_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )


def _write_root_acceptance_contract(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    if payload.get("pm_owned", True) is not True:
        raise RouterError("root acceptance contract must be PM-owned")
    architecture_path = run_root / "product_function_architecture.json"
    if not architecture_path.exists():
        raise RouterError("root contract requires product-function architecture")
    root_requirements = payload.get("root_requirements")
    if not isinstance(root_requirements, list) or not root_requirements:
        raise RouterError("root contract requires a non-empty root_requirements list")
    proof_matrix = payload.get("proof_matrix")
    if not isinstance(proof_matrix, list) or not proof_matrix:
        raise RouterError("root contract requires a non-empty proof_matrix list")
    scenario_ids = payload.get("selected_scenario_ids")
    if not isinstance(scenario_ids, list) or not scenario_ids:
        raise RouterError("root contract requires a non-empty selected_scenario_ids list")
    contract = {
        "schema_version": "flowpilot.root_acceptance_contract.v1",
        "run_id": run_state["run_id"],
        "pm_owned": True,
        "status": "approved",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "source_paths": {
            "product_function_architecture": project_relative(project_root, architecture_path),
        },
        "root_requirements": root_requirements,
        "proof_matrix": proof_matrix,
        "standard_scenario_pack": {
            "required": True,
            "path": project_relative(project_root, run_root / "standard_scenario_pack.json"),
            "selected_scenario_ids": scenario_ids,
        },
        "completion_policy": {
            "unresolved_residual_risks_allowed": False,
            "risk_triage_required_before_completion": True,
        },
        "written_by_role": "project_manager",
        **_role_output_envelope_record(payload),
    }
    scenario_pack = {
        "schema_version": "flowpilot.standard_scenario_pack.v1",
        "run_id": run_state["run_id"],
        "pm_owned": True,
        "status": "approved",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "selected_scenario_ids": scenario_ids,
        "selection_reason": payload.get("scenario_selection_reason") or "Selected from root acceptance contract risk coverage.",
    }
    write_json(run_root / "root_acceptance_contract.json", contract)
    write_json(run_root / "standard_scenario_pack.json", scenario_pack)
    (run_root / "contract.md").write_text(
        "\n".join(
            [
                "# FlowPilot Root Acceptance Contract",
                "",
                f"Run: {run_state['run_id']}",
                "",
                "The PM has frozen the root acceptance contract. See:",
                "",
                "- `root_acceptance_contract.json`",
                "- `standard_scenario_pack.json`",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _freeze_root_acceptance_contract(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    required_paths = [
        run_root / "root_acceptance_contract.json",
        run_root / "standard_scenario_pack.json",
        run_root / "contract.md",
        run_root / "reviews" / "root_contract_challenge.json",
        run_root / "flowguard" / "root_contract_modelability.json",
    ]
    missing = [project_relative(project_root, path) for path in required_paths if not path.exists()]
    if missing:
        raise RouterError(f"cannot freeze root contract; missing paths: {', '.join(missing)}")
    contract = read_json(run_root / "root_acceptance_contract.json")
    if contract.get("completion_policy", {}).get("unresolved_residual_risks_allowed") is not False:
        raise RouterError("root contract cannot allow unresolved residual risks")
    contract["status"] = "frozen"
    contract["frozen_by_role"] = "project_manager"
    contract["frozen_at"] = utc_now()
    write_json(run_root / "root_acceptance_contract.json", contract)


def _write_dependency_policy(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    contract_path = run_root / "root_acceptance_contract.json"
    if not contract_path.exists() or read_json(contract_path).get("status") != "frozen":
        raise RouterError("dependency policy requires frozen root contract")
    if payload.get("pm_owned", True) is not True:
        raise RouterError("dependency policy must be PM-owned")
    if payload.get("raw_inventory_is_authority") is True:
        raise RouterError("raw skill or host inventory cannot be authority for dependency policy")
    if payload.get("controller_self_install_allowed") is True:
        raise RouterError("Controller cannot self-approve host-level installs")
    host_install_requested = bool(payload.get("host_level_install_requested"))
    user_approval_recorded = bool(payload.get("explicit_user_approval_recorded"))
    if host_install_requested and not user_approval_recorded:
        raise RouterError("host-level installs require explicit recorded user approval")
    policy = {
        "schema_version": "flowpilot.dependency_policy.v1",
        "run_id": run_state["run_id"],
        "pm_owned": True,
        "status": str(payload.get("status") or "approved"),
        "source_paths": {
            "root_acceptance_contract": project_relative(project_root, contract_path),
            "product_function_architecture": project_relative(project_root, run_root / "product_function_architecture.json"),
        },
        "raw_inventory_is_authority": False,
        "raw_inventory_can_seed_candidates_only": True,
        "host_level_install_requested": host_install_requested,
        "explicit_user_approval_recorded": user_approval_recorded,
        "controller_self_install_allowed": False,
        "allowed_dependency_actions": payload.get("allowed_dependency_actions") or [],
        "blocked_dependency_actions": payload.get("blocked_dependency_actions") or ["host_install_without_user_approval"],
        "written_by_role": "project_manager",
        "written_at": utc_now(),
        **_role_output_envelope_record(payload),
    }
    write_json(run_root / "dependency_policy.json", policy)


def _write_capabilities_manifest(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    dependency_path = run_root / "dependency_policy.json"
    architecture_path = run_root / "product_function_architecture.json"
    contract_path = run_root / "root_acceptance_contract.json"
    if not dependency_path.exists():
        raise RouterError("capabilities manifest requires dependency_policy.json")
    if not architecture_path.exists():
        raise RouterError("capabilities manifest requires product_function_architecture.json")
    if not contract_path.exists() or read_json(contract_path).get("status") != "frozen":
        raise RouterError("capabilities manifest requires frozen root contract")
    if payload.get("pm_owned", True) is not True:
        raise RouterError("capabilities manifest must be PM-owned")
    if payload.get("raw_inventory_is_authority") is True:
        raise RouterError("raw skill or host inventory cannot authorize capabilities")
    architecture = read_json(architecture_path)
    capabilities = payload.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        capabilities = architecture.get("product_capability_map") or []
    if not isinstance(capabilities, list) or not capabilities:
        raise RouterError("capabilities manifest requires a non-empty capabilities list or product_capability_map")
    manifest = {
        "schema_version": "flowpilot.capabilities_manifest.v1",
        "run_id": run_state["run_id"],
        "pm_owned": True,
        "status": str(payload.get("status") or "approved"),
        "source_paths": {
            "dependency_policy": project_relative(project_root, dependency_path),
            "product_function_architecture": project_relative(project_root, architecture_path),
            "root_acceptance_contract": project_relative(project_root, contract_path),
        },
        "raw_inventory_is_authority": False,
        "raw_inventory_can_seed_candidates_only": True,
        "capabilities": capabilities,
        "capability_to_skill_needs": payload.get("capability_to_skill_needs") or [],
        "written_by_role": "project_manager",
        "written_at": utc_now(),
        **_role_output_envelope_record(payload),
    }
    write_json(run_root / "capabilities.json", manifest)


def _validate_selected_child_skills(selected_skills: Any) -> list[dict[str, Any]]:
    if not isinstance(selected_skills, list):
        raise RouterError("selected child skills must be a list")
    allowed_approvers = {
        "project_manager",
        "human_like_reviewer",
        "process_flowguard_officer",
        "product_flowguard_officer",
    }
    for skill in selected_skills:
        if not isinstance(skill, dict):
            raise RouterError("each selected child skill entry must be an object")
        for gate in skill.get("gates") or []:
            if not isinstance(gate, dict):
                raise RouterError("each child-skill gate must be an object")
            approver = gate.get("required_approver")
            if approver == "controller" or gate.get("controller_can_approve") is True:
                raise RouterError("Controller cannot approve child-skill gates")
            if approver and approver not in allowed_approvers:
                raise RouterError(f"unsupported child-skill gate approver: {approver}")
    return selected_skills


def _write_child_skill_selection(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    capabilities_path = run_root / "capabilities.json"
    if not capabilities_path.exists():
        raise RouterError("child-skill selection requires capabilities.json")
    if payload.get("pm_owned", True) is not True:
        raise RouterError("child-skill selection must be PM-owned")
    if payload.get("raw_inventory_used_as_authority") is True or payload.get("raw_inventory_is_authority") is True:
        raise RouterError("raw local skill inventory cannot authorize child-skill selection")
    selected_skills = payload.get("selected_skills")
    if selected_skills is None:
        selected_skills = payload.get("skill_decisions") or []
    selected_skills = _validate_selected_child_skills(selected_skills)
    selection = {
        "schema_version": "flowpilot.pm_child_skill_selection.v1",
        "run_id": run_state["run_id"],
        "pm_owned": True,
        "status": str(payload.get("status") or "approved"),
        "source_paths": {
            "capabilities_manifest": project_relative(project_root, capabilities_path),
            "dependency_policy": project_relative(project_root, run_root / "dependency_policy.json"),
        },
        "raw_inventory_used_as_authority": False,
        "raw_inventory_can_seed_candidates_only": True,
        "selected_from_product_needs": True,
        "selected_skills": selected_skills,
        "deferred_skills": payload.get("deferred_skills") or [],
        "rejected_skills": payload.get("rejected_skills") or [],
        "written_by_role": "project_manager",
        "written_at": utc_now(),
        **_role_output_envelope_record(payload),
    }
    write_json(run_root / "pm_child_skill_selection.json", selection)


def _write_child_skill_gate_manifest(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    selection_path = run_root / "pm_child_skill_selection.json"
    capabilities_path = run_root / "capabilities.json"
    contract_path = run_root / "root_acceptance_contract.json"
    for required_path, label in (
        (selection_path, "pm_child_skill_selection.json"),
        (capabilities_path, "capabilities.json"),
        (contract_path, "root_acceptance_contract.json"),
    ):
        if not required_path.exists():
            raise RouterError(f"child-skill gate manifest requires {label}")
    if payload.get("pm_owned", True) is not True:
        raise RouterError("child-skill gate manifest must be PM-owned")
    if payload.get("raw_inventory_is_authority") is True:
        raise RouterError("raw inventory cannot be authority for child-skill gate manifest")
    if payload.get("controller_self_approval_allowed") is True:
        raise RouterError("child-skill gate manifest cannot allow Controller self-approval")
    selection = read_json(selection_path)
    selected_skills = payload.get("selected_skills")
    if selected_skills is None:
        selected_skills = selection.get("selected_skills") or []
    selected_skills = _validate_selected_child_skills(selected_skills)
    manifest_path = run_root / "child_skill_gate_manifest.json"
    manifest = {
        "schema_version": "flowpilot.child_skill_gate_manifest.v1",
        "run_id": run_state["run_id"],
        "pm_owned": True,
        "status": str(payload.get("status") or "draft"),
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "source_paths": {
            "pm_child_skill_selection": project_relative(project_root, selection_path),
            "capabilities_manifest": project_relative(project_root, capabilities_path),
            "root_acceptance_contract": project_relative(project_root, contract_path),
        },
        "raw_inventory_is_authority": False,
        "controller_self_approval_allowed": False,
        "selected_skills": selected_skills,
        "approval": {
            "reviewer_passed": False,
            "process_officer_passed": False,
            "product_officer_passed": False,
            "pm_approved_for_route": False,
        },
        **_role_output_envelope_record_for_mutable_artifact(
            project_root,
            run_root,
            manifest_path,
            payload,
            reason="child_skill_gate_manifest_can_be_updated_by_review_gates",
        ),
    }
    write_json(manifest_path, manifest)


def _sync_child_skill_manifest_review_approval(project_root: Path, run_root: Path) -> None:
    manifest_path = run_root / "child_skill_gate_manifest.json"
    review_path = run_root / "reviews" / "child_skill_gate_manifest_review.json"
    if not manifest_path.exists() or not review_path.exists():
        return
    review = read_json(review_path)
    if review.get("passed") is not True:
        return
    manifest = read_json(manifest_path)
    manifest.update(
        _role_output_envelope_record_for_mutable_artifact(
            project_root,
            run_root,
            manifest_path,
            manifest,
            reason="child_skill_gate_manifest_review_approval_sync",
        )
    )
    approval = manifest.setdefault("approval", {})
    if approval.get("reviewer_passed") is True:
        return
    approval["reviewer_passed"] = True
    approval["reviewed_at"] = review.get("reported_at") or utc_now()
    manifest["updated_at"] = utc_now()
    write_json(manifest_path, manifest)


def _approve_child_skill_manifest_for_route(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    manifest_path = run_root / "child_skill_gate_manifest.json"
    required_paths = [
        manifest_path,
        run_root / "reviews" / "child_skill_gate_manifest_review.json",
        run_root / "flowguard" / "child_skill_conformance_model.json",
        run_root / "flowguard" / "child_skill_product_fit.json",
    ]
    missing = [project_relative(project_root, path) for path in required_paths if not path.exists()]
    if missing:
        raise RouterError(f"PM child-skill approval is missing required reports: {', '.join(missing)}")
    if payload.get("approved_by_role", "project_manager") != "project_manager":
        raise RouterError("child-skill manifest route approval must be by project_manager")
    if payload.get("controller_self_approval_allowed") is True:
        raise RouterError("child-skill manifest PM approval cannot allow Controller self-approval")
    manifest = read_json(manifest_path)
    manifest["status"] = "approved"
    manifest["updated_at"] = utc_now()
    manifest.setdefault("approval", {})
    manifest["approval"].update(
        {
            "reviewer_passed": True,
            "process_officer_passed": True,
            "product_officer_passed": True,
            "pm_approved_for_route": True,
            "approved_by_role": "project_manager",
            "approved_at": utc_now(),
        }
    )
    write_json(manifest_path, manifest)
    write_json(
        run_root / "child_skill_manifest_pm_approval.json",
        {
            "schema_version": "flowpilot.child_skill_manifest_pm_approval.v1",
            "run_id": run_state["run_id"],
            "approved_by_role": "project_manager",
            "approved_at": utc_now(),
            "source_paths": [project_relative(project_root, path) for path in required_paths],
        },
    )


def _sync_capability_evidence(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    manifest_path = run_root / "child_skill_gate_manifest.json"
    capabilities_path = run_root / "capabilities.json"
    approval_path = run_root / "child_skill_manifest_pm_approval.json"
    required_paths = [manifest_path, capabilities_path, approval_path]
    missing = [project_relative(project_root, path) for path in required_paths if not path.exists()]
    if missing:
        raise RouterError(f"capability evidence sync is missing paths: {', '.join(missing)}")
    manifest = read_json(manifest_path)
    if manifest.get("status") != "approved" or manifest.get("approval", {}).get("pm_approved_for_route") is not True:
        raise RouterError("capability evidence sync requires PM-approved child-skill manifest")
    write_json(
        run_root / "capabilities" / "capability_sync.json",
        {
            "schema_version": "flowpilot.capability_evidence_sync.v1",
            "run_id": run_state["run_id"],
            "synced_by": str(payload.get("synced_by") or "controller"),
            "pm_approved_manifest": True,
            "source_paths": [project_relative(project_root, path) for path in required_paths],
            "synced_at": utc_now(),
        },
    )


def _reset_flags(run_state: dict[str, Any], names: tuple[str, ...]) -> None:
    for name in names:
        run_state["flags"][name] = False


def _route_nodes(route: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = route.get("nodes")
    if not isinstance(nodes, list):
        return []
    return [node for node in nodes if isinstance(node, dict) and node.get("node_id")]


def _effective_route_nodes(route: dict[str, Any], mutations: dict[str, Any]) -> list[dict[str, Any]]:
    superseded = {
        str(node_id)
        for item in mutations.get("items", [])
        if isinstance(item, dict)
        for node_id in (item.get("superseded_nodes") or [])
    }
    effective = []
    for node in _route_nodes(route):
        node_id = str(node["node_id"])
        if node_id in superseded or node.get("status") in {"superseded", "stale", "failed"}:
            continue
        effective.append(node)
    return effective


def _next_effective_node_id(route: dict[str, Any], mutations: dict[str, Any], completed_nodes: list[str], current_node_id: str) -> str | None:
    effective_ids = [str(node["node_id"]) for node in _effective_route_nodes(route, mutations)]
    if not effective_ids:
        return None
    try:
        start = effective_ids.index(current_node_id) + 1
    except ValueError:
        start = 0
    completed = set(completed_nodes)
    for node_id in effective_ids[start:] + effective_ids[:start]:
        if node_id not in completed:
            return node_id
    return None


def _route_memory_root(run_root: Path) -> Path:
    return run_root / "route_memory"


def _route_history_index_path(run_root: Path) -> Path:
    return _route_memory_root(run_root) / "route_history_index.json"


def _pm_prior_path_context_path(run_root: Path) -> Path:
    return _route_memory_root(run_root) / "pm_prior_path_context.json"


def _route_memory_ready(run_root: Path, run_state: dict[str, Any]) -> bool:
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    return (
        bool(flags.get("route_history_index_refreshed"))
        and bool(flags.get("pm_prior_path_context_refreshed"))
        and _route_history_index_path(run_root).exists()
        and _pm_prior_path_context_path(run_root).exists()
    )


def _display_plan_path(run_root: Path) -> Path:
    return run_root / "display_plan.json"


def _route_state_snapshot_path(run_root: Path) -> Path:
    return run_root / "route_state_snapshot.json"


def _optional_source_path(project_root: Path, path: Path) -> str | None:
    return project_relative(project_root, path) if path.exists() else None


def _plan_item_status(raw_status: Any, *, active: bool = False) -> str:
    status = str(raw_status or "").lower()
    if active:
        return "in_progress"
    if status in {"complete", "completed", "done", "passed"}:
        return "completed"
    if status in {"active", "running", "current", "in_progress"}:
        return "in_progress"
    return "pending"


def _frontier_completed_node_ids(run_root: Path) -> set[str]:
    frontier = read_json_if_exists(run_root / "execution_frontier.json")
    completed = frontier.get("completed_nodes") if isinstance(frontier, dict) else []
    return {str(node_id) for node_id in completed or []}


def _route_item_status(
    run_root: Path,
    node_id: str,
    *,
    active_node_id: str | None,
    raw_status: Any = None,
) -> str:
    if node_id in _frontier_completed_node_ids(run_root):
        return "completed"
    if active_node_id and node_id == active_node_id:
        return "in_progress"
    status = str(raw_status or "").lower()
    if status in {"complete", "completed", "done", "passed"}:
        return "completed"
    return "pending"


def _display_plan_projection(plan: dict[str, Any]) -> dict[str, Any]:
    current_node_id = plan.get("current_node_id")

    def _projected_status(item: dict[str, Any]) -> str:
        item_id = str(item.get("id") or item.get("node_id") or "")
        status = str(item.get("status") or "").lower()
        if status in {"complete", "completed", "done", "passed"}:
            return "completed"
        if item_id == str(current_node_id or ""):
            return "in_progress"
        return "pending"

    return {
        "title": str(plan.get("title") or "FlowPilot"),
        "items": [
            {
                "id": str(item.get("id") or item.get("node_id") or f"item-{index:03d}"),
                "label": str(item.get("label") or item.get("title") or item.get("id") or f"Item {index}"),
                "status": _projected_status(item),
            }
            for index, item in enumerate(plan.get("items") or [], start=1)
            if isinstance(item, dict)
        ],
        "current_node_id": current_node_id,
        "current_node": plan.get("current_node") if isinstance(plan.get("current_node"), dict) else None,
    }


def _waiting_for_pm_display_plan(run_state: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": DISPLAY_PLAN_SCHEMA,
        "run_id": run_state["run_id"],
        "source_role": "controller",
        "scope": "startup_waiting_for_pm",
        "title": "FlowPilot",
        "items": [
            {
                "id": "await_pm_route",
                "label": "Waiting for PM route",
                "status": "in_progress",
            }
        ],
        "current_node_id": None,
        "route_authority": "none_until_pm_display_plan",
        "controller_may_invent_route_items": False,
        "updated_at": utc_now(),
    }


def _current_display_plan(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    del project_root
    path = _display_plan_path(run_root)
    if path.exists():
        return read_json(path)
    return _waiting_for_pm_display_plan(run_state)


def _display_plan_sync_payload(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    plan = _current_display_plan(project_root, run_root, run_state)
    projection = _display_plan_projection(plan)
    digest = hashlib.sha256(json.dumps(projection, sort_keys=True).encode("utf-8")).hexdigest()
    snapshot_path = _route_state_snapshot_path(run_root)
    snapshot_digest = hashlib.sha256(snapshot_path.read_bytes()).hexdigest() if snapshot_path.exists() else None
    route_sign = _route_map_route_sign_payload(project_root, write=False, mark_chat_displayed=False)
    route_sign_available = _route_sign_has_canonical_route(route_sign)
    dialog_fields = (
        _display_route_sign_user_dialog_fields(route_sign)
        if route_sign_available
        else _display_plan_user_dialog_fields(projection)
    )
    display_degraded_reason = None
    if not route_sign_available:
        display_degraded_reason = (
            "startup_waiting_for_pm_route"
            if _display_plan_display_kind(projection) == "startup_waiting_state"
            else "canonical_route_source_unavailable"
        )
    return {
        "display_plan_path": project_relative(project_root, _display_plan_path(run_root)),
        "display_plan_exists": _display_plan_path(run_root).exists(),
        "route_state_snapshot_path": project_relative(project_root, snapshot_path),
        "route_state_snapshot_exists": snapshot_path.exists(),
        "route_state_snapshot_hash": snapshot_digest,
        "projection_hash": digest,
        "native_plan_projection": projection,
        "host_action": "replace_visible_plan",
        "controller_may_invent_route_items": False,
        "route_sign_display_required": route_sign_available,
        "route_sign_display_degraded_reason": display_degraded_reason,
        "route_sign_markdown_path": route_sign.get("markdown_preview_path"),
        "route_sign_mermaid_path": route_sign.get("mermaid_path"),
        "route_sign_display_packet_path": route_sign.get("display_packet_path"),
        "route_sign_mermaid_sha256": route_sign.get("mermaid_sha256"),
        "route_sign_source_kind": route_sign.get("route_source_kind"),
        "route_sign_node_count": route_sign.get("route_node_count"),
        "route_sign_checklist_item_count": route_sign.get("route_checklist_item_count"),
        "route_sign_layout": route_sign.get("route_sign_layout"),
        "route_sign_source_route_path": route_sign.get("source_route_path"),
        "route_sign_source_frontier_path": route_sign.get("source_frontier_path"),
        **dialog_fields,
    }


def _active_ui_task_catalog(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    current = read_json_if_exists(project_root / ".flowpilot" / "current.json") or {}
    index = read_json_if_exists(project_root / ".flowpilot" / "index.json") or {}
    run_id = str(run_state.get("run_id") or "")
    run_root_rel = project_relative(project_root, run_root)
    current_run_id = str(current.get("current_run_id") or current.get("active_run_id") or "")
    current_run_root = str(current.get("current_run_root") or current.get("active_run_root") or "")
    current_status = str(current.get("status") or run_state.get("status") or "")
    hidden_statuses = {"completed", "closed", "stopped", "stopped_by_user", "protocol_dead_end", "abandoned", "discarded", "stale"}
    current_pointer_matches = current_run_id == run_id and current_run_root == run_root_rel
    active_tasks: list[dict[str, Any]] = []
    if current_pointer_matches and current_status not in hidden_statuses:
        active_tasks.append(
            {
                "run_id": run_id,
                "run_root": run_root_rel,
                "status": current_status or "running",
                "display_plan_path": project_relative(project_root, _display_plan_path(run_root)),
                "route_state_snapshot_path": project_relative(project_root, _route_state_snapshot_path(run_root)),
                "close_tab_behavior": "return_to_dialog_route_display",
            }
        )
    hidden_running = [
        {
            "run_id": str(item.get("run_id") or ""),
            "run_root": str(item.get("run_root") or ""),
            "status": str(item.get("status") or ""),
            "hidden_reason": "not_current_pointer",
        }
        for item in index.get("runs", [])
        if isinstance(item, dict)
        and item.get("status") == "running"
        and str(item.get("run_id") or "") != current_run_id
    ]
    return {
        "schema_version": "flowpilot.active_ui_task_catalog.v1",
        "authority": "current_json_only",
        "current_pointer_matches_run": current_pointer_matches,
        "active_tasks": active_tasks,
        "hidden_non_current_running_index_entries": hidden_running,
        "completed_abandoned_stale_history_default_visible": False,
    }


def _route_node_checklist(node: dict[str, Any], *, node_complete: bool = False) -> list[dict[str, Any]]:
    raw_items = node.get("checklist")
    if not isinstance(raw_items, list):
        raw_items = node.get("required_gates")
    if not isinstance(raw_items, list):
        raw_items = node.get("acceptance_checklist")
    if not isinstance(raw_items, list):
        raw_items = []
    checklist: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_items, start=1):
        if isinstance(raw, dict):
            item_id = str(raw.get("id") or raw.get("gate_id") or raw.get("label") or f"check-{index:03d}")
            label = str(raw.get("label") or raw.get("title") or raw.get("gate") or item_id)
            status = _plan_item_status(raw.get("status"), active=False)
        else:
            item_id = str(raw)
            label = item_id.replace("_", " ")
            status = "completed" if node_complete else "pending"
        checklist.append({"id": item_id, "label": label, "status": status})
    return checklist


def _active_route_payload(run_root: Path, route_id: str | None = None) -> dict[str, Any] | None:
    route_root = run_root / "routes"
    candidates: list[Path] = []
    if route_id:
        candidates.extend([route_root / route_id / "flow.json", route_root / route_id / "flow.draft.json"])
    if route_root.exists():
        candidates.extend(sorted(route_root.glob("*/flow.json")))
        candidates.extend(sorted(route_root.glob("*/flow.draft.json")))
    seen: set[Path] = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        if path.exists():
            return read_json(path)
    return None


def _build_route_state_snapshot(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    route_payload: dict[str, Any] | None = None,
    source_event: str | None = None,
) -> dict[str, Any]:
    current = read_json_if_exists(project_root / ".flowpilot" / "current.json") or {}
    index = read_json_if_exists(project_root / ".flowpilot" / "index.json") or {}
    frontier = read_json_if_exists(run_root / "execution_frontier.json") or {}
    packet_ledger = read_json_if_exists(run_root / "packet_ledger.json") or {}
    active_route_id = str(frontier.get("active_route_id") or run_state.get("active_route_id") or "")
    route = route_payload or _active_route_payload(run_root, active_route_id) or {}
    if not active_route_id:
        active_route_id = str(route.get("route_id") or "")
    active_node_id = str(frontier.get("active_node_id") or route.get("active_node_id") or "")
    run_id = str(run_state.get("run_id") or "")
    current_run_id = str(current.get("current_run_id") or current.get("active_run_id") or "")
    current_run_root = str(current.get("current_run_root") or current.get("active_run_root") or "")
    run_root_rel = project_relative(project_root, run_root)
    stale_running = [
        {
            "run_id": str(item.get("run_id") or ""),
            "status": str(item.get("status") or ""),
            "run_root": str(item.get("run_root") or ""),
        }
        for item in index.get("runs", [])
        if isinstance(item, dict)
        and item.get("status") == "running"
        and str(item.get("run_id") or "") != current_run_id
    ]
    nodes: list[dict[str, Any]] = []
    for position, node in enumerate(_iter_route_nodes(route), start=1):
        node_id = str(node.get("node_id") or node.get("id") or f"node-{position:03d}")
        status = _plan_item_status(node.get("status"), active=node_id == active_node_id)
        node_complete = status == "completed"
        nodes.append(
            {
                "id": node_id,
                "label": str(node.get("title") or node.get("label") or node_id),
                "status": status,
                "is_active": node_id == active_node_id,
                "is_complete": node_complete,
                "checklist": _route_node_checklist(node, node_complete=node_complete),
                "children": node.get("children") if isinstance(node.get("children"), list) else [],
            }
        )
    pending_action = run_state.get("pending_action") if isinstance(run_state.get("pending_action"), dict) else {}
    return {
        "schema_version": ROUTE_STATE_SNAPSHOT_SCHEMA,
        "run_id": run_id,
        "run_root": run_root_rel,
        "created_at": utc_now(),
        "source_event": source_event,
        "active_ui_task_catalog": _active_ui_task_catalog(project_root, run_root, run_state),
        "authority": {
            "active_source": "current_json_only",
            "current_pointer_path": ".flowpilot/current.json",
            "current_pointer_matches_run": current_run_id == run_id and current_run_root == run_root_rel,
            "index_running_entries_are_not_active_authority": True,
            "stale_running_index_entries": stale_running,
        },
        "route": {
            "route_id": active_route_id or route.get("route_id"),
            "route_version": route.get("route_version") or frontier.get("route_version"),
            "active_node_id": active_node_id or None,
            "nodes": nodes,
        },
        "frontier": {
            "path": project_relative(project_root, run_root / "execution_frontier.json"),
            "status": frontier.get("status"),
            "active_route_id": frontier.get("active_route_id"),
            "active_node_id": frontier.get("active_node_id"),
            "route_version": frontier.get("route_version"),
        },
        "state": {
            "path": project_relative(project_root, run_state_path(run_root)),
            "status": run_state.get("status"),
            "flags": dict(run_state.get("flags") or {}),
        },
        "packet_ledger": {
            "path": project_relative(project_root, run_root / "packet_ledger.json"),
            "active_packet_id": packet_ledger.get("active_packet_id"),
            "active_packet_status": packet_ledger.get("active_packet_status"),
            "active_packet_holder": packet_ledger.get("active_packet_holder"),
            "latest_packet_chain_audit_passed": packet_ledger.get("latest_packet_chain_audit_passed"),
            "latest_barrier_bundle_audit_passed": packet_ledger.get("latest_barrier_bundle_audit_passed"),
        },
        "next_action": {
            "action_type": pending_action.get("action_type"),
            "to_role": pending_action.get("to_role"),
            "label": pending_action.get("label"),
            "allowed_external_events": pending_action.get("allowed_external_events") or [],
        },
    }


def _write_route_state_snapshot(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    route_payload: dict[str, Any] | None = None,
    source_event: str | None = None,
) -> None:
    snapshot = _build_route_state_snapshot(
        project_root,
        run_root,
        run_state,
        route_payload=route_payload,
        source_event=source_event,
    )
    write_json(_route_state_snapshot_path(run_root), snapshot)


def _mark_display_plan_dirty(run_state: dict[str, Any]) -> None:
    run_state["visible_plan_sync"] = {}


def _write_display_plan_from_route(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    route_id: str,
    route_version: int,
    route_payload: dict[str, Any],
    active_node_id: str | None,
    source_event: str,
) -> None:
    nodes = _iter_route_nodes(route_payload)
    items = []
    for index, node in enumerate(nodes, start=1):
        node_id = str(node.get("node_id") or node.get("id") or f"node-{index:03d}")
        items.append(
            {
                "id": node_id,
                "label": str(node.get("title") or node.get("label") or node_id),
                "status": _route_item_status(
                    run_root,
                    node_id,
                    active_node_id=active_node_id,
                    raw_status=node.get("status"),
                ),
            }
        )
    if not items:
        items.append({"id": "route_pending", "label": "PM route", "status": "pending"})
    plan = {
        "schema_version": DISPLAY_PLAN_SCHEMA,
        "run_id": run_state["run_id"],
        "source_role": "project_manager",
        "source_event": source_event,
        "scope": "route",
        "title": str(route_payload.get("title") or route_payload.get("name") or "FlowPilot route"),
        "route_id": route_id,
        "route_version": route_version,
        "items": items,
        "current_node_id": active_node_id,
        "controller_may_invent_route_items": False,
        "updated_at": utc_now(),
    }
    write_json(_display_plan_path(run_root), plan)
    _write_route_state_snapshot(project_root, run_root, run_state, route_payload=route_payload, source_event=source_event)
    _mark_display_plan_dirty(run_state)


def _update_display_plan_current_node(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    node_id: str,
    node_title: str,
    checklist: list[dict[str, Any]],
    source_event: str,
) -> None:
    plan = read_json_if_exists(_display_plan_path(run_root))
    if not plan:
        plan = _waiting_for_pm_display_plan(run_state)
    items = plan.setdefault("items", [])
    for item in items:
        if isinstance(item, dict):
            item_id = str(item.get("id") or item.get("node_id") or "")
            item["status"] = _route_item_status(
                run_root,
                item_id,
                active_node_id=node_id,
                raw_status=item.get("status"),
            )
    plan.update(
        {
            "schema_version": DISPLAY_PLAN_SCHEMA,
            "run_id": run_state["run_id"],
            "source_role": "project_manager",
            "source_event": source_event,
            "scope": "node",
            "current_node_id": node_id,
            "current_node": {
                "id": node_id,
                "label": node_title,
                "checklist": checklist,
            },
            "controller_may_invent_route_items": False,
            "updated_at": utc_now(),
        }
    )
    write_json(_display_plan_path(run_root), plan)
    _write_route_state_snapshot(project_root, run_root, run_state, source_event=source_event)
    _mark_display_plan_dirty(run_state)


PRE_ROUTE_PHASE_ITEMS = (
    ("material_understanding", "Material understanding", "pm_material_understanding_card_delivered"),
    ("product_architecture", "Product architecture", "pm_product_architecture_card_delivered"),
    ("root_contract", "Root contract", "pm_root_contract_card_delivered"),
    ("dependency_policy", "Dependency policy", "pm_dependency_policy_card_delivered"),
    ("child_skill_gate_manifest", "Child-skill gates", "pm_child_skill_gate_manifest_card_delivered"),
)


def _latest_pre_route_phase(run_state: dict[str, Any]) -> str | None:
    for delivery in reversed(run_state.get("delivered_cards") or []):
        if not isinstance(delivery, dict):
            continue
        phase = CARD_PHASE_BY_ID.get(str(delivery.get("card_id") or ""))
        if phase:
            return phase
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    for phase, _label, flag in reversed(PRE_ROUTE_PHASE_ITEMS):
        if flags.get(flag):
            return phase
    return None


def _sync_execution_frontier_phase(run_root: Path, run_state: dict[str, Any]) -> None:
    phase = _latest_pre_route_phase(run_state)
    if not phase:
        return
    frontier_path = run_root / "execution_frontier.json"
    frontier = read_json_if_exists(frontier_path)
    if str(frontier.get("status") or run_state.get("status") or "") in RUN_TERMINAL_STATUSES:
        return
    run_state["phase"] = phase
    frontier["phase"] = phase
    if not frontier.get("active_route_id"):
        frontier["status"] = phase
    frontier["updated_at"] = utc_now()
    write_json(frontier_path, frontier)


def _write_pre_route_phase_display_plan_if_needed(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    phase = _latest_pre_route_phase(run_state)
    if phase is None:
        return False
    existing = read_json_if_exists(_display_plan_path(run_root))
    if existing.get("scope") in {"route", "node"} and existing.get("source_role") == "project_manager":
        return False
    phase_order = [item[0] for item in PRE_ROUTE_PHASE_ITEMS]
    active_index = phase_order.index(phase) if phase in phase_order else 0
    items = []
    for index, (item_id, label, _flag) in enumerate(PRE_ROUTE_PHASE_ITEMS):
        if index < active_index:
            status = "completed"
        elif index == active_index:
            status = "in_progress"
        else:
            status = "pending"
        items.append({"id": item_id, "label": label, "status": status})
    plan = {
        "schema_version": DISPLAY_PLAN_SCHEMA,
        "run_id": run_state["run_id"],
        "source_role": "controller",
        "source_event": "derived_pre_route_phase_sync",
        "scope": "pre_route_phase",
        "title": "FlowPilot route preparation",
        "items": items,
        "current_node_id": None,
        "route_authority": "none_until_pm_route_draft",
        "controller_may_invent_route_items": False,
        "updated_at": utc_now(),
    }
    write_json(_display_plan_path(run_root), plan)
    return True


def _reconcile_non_current_running_index_entries(project_root: Path, run_state: dict[str, Any]) -> int:
    current = read_json_if_exists(project_root / ".flowpilot" / "current.json") or {}
    index_path = project_root / ".flowpilot" / "index.json"
    index = read_json_if_exists(index_path) or {}
    runs = index.get("runs") if isinstance(index.get("runs"), list) else []
    current_run_id = str(current.get("current_run_id") or current.get("active_run_id") or "")
    updated = 0
    now = utc_now()
    for item in runs:
        if not isinstance(item, dict):
            continue
        if item.get("run_id") == run_state.get("run_id"):
            item["status"] = run_state.get("status") or item.get("status")
            item["updated_at"] = now
        elif item.get("status") == "running" and str(item.get("run_id") or "") != current_run_id:
            item["status"] = "stale_not_current"
            item["stale_reason"] = "not_current_pointer"
            item["updated_at"] = now
            updated += 1
    if runs:
        index["runs"] = runs
        index["updated_at"] = now
        write_json(index_path, index)
    return updated


def _sync_derived_run_views(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    reason: str,
    update_display: bool = True,
) -> None:
    _sync_control_plane_indexes(project_root, run_root, run_state)
    _sync_child_skill_manifest_review_approval(project_root, run_root)
    _sync_execution_frontier_phase(run_root, run_state)
    _reconcile_non_current_running_index_entries(project_root, run_state)
    display_updated = _write_pre_route_phase_display_plan_if_needed(project_root, run_root, run_state) if update_display else False
    _write_route_state_snapshot(project_root, run_root, run_state, source_event=reason)
    if display_updated:
        sync_payload = _display_plan_sync_payload(project_root, run_root, run_state)
        run_state["visible_plan_sync"] = {
            "display_plan_path": sync_payload["display_plan_path"],
            "route_state_snapshot_path": sync_payload["route_state_snapshot_path"],
            "route_state_snapshot_hash": sync_payload["route_state_snapshot_hash"],
            "projection_hash": sync_payload["projection_hash"],
            "synced_at": utc_now(),
            "host_action": "derived_pre_route_phase_projection",
        }


def _write_display_plan_from_pm_payload(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    source_event: str,
) -> None:
    raw_plan = payload.get("display_plan")
    if not isinstance(raw_plan, dict):
        return
    raw_items = raw_plan.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise RouterError(f"{source_event} display_plan requires non-empty items")
    items = []
    for index, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            raise RouterError(f"{source_event} display_plan items must be objects")
        item_id = item.get("id") or item.get("node_id") or f"item-{index:03d}"
        items.append(
            {
                "id": str(item_id),
                "label": str(item.get("label") or item.get("title") or item_id),
                "status": _route_item_status(
                    run_root,
                    str(item_id),
                    active_node_id=str(raw_plan.get("current_node_id") or ""),
                    raw_status=item.get("status"),
                ),
            }
        )
    plan = {
        "schema_version": DISPLAY_PLAN_SCHEMA,
        "run_id": run_state["run_id"],
        "source_role": "project_manager",
        "source_event": source_event,
        "scope": str(raw_plan.get("scope") or "route"),
        "title": str(raw_plan.get("title") or "FlowPilot route"),
        "items": items,
        "current_node_id": raw_plan.get("current_node_id"),
        "controller_may_invent_route_items": False,
        "updated_at": utc_now(),
    }
    if isinstance(raw_plan.get("current_node"), dict):
        plan["current_node"] = raw_plan["current_node"]
    write_json(_display_plan_path(run_root), plan)
    _write_route_state_snapshot(project_root, run_root, run_state, source_event=source_event)
    _mark_display_plan_dirty(run_state)


def _event_markers(run_state: dict[str, Any], names: set[str]) -> list[dict[str, Any]]:
    markers: list[dict[str, Any]] = []
    for event in run_state.get("events") or []:
        if not isinstance(event, dict):
            continue
        event_name = str(event.get("event") or "")
        if event_name not in names:
            continue
        markers.append(
            {
                "event": event_name,
                "summary": event.get("summary"),
                "recorded_at": event.get("recorded_at"),
            }
        )
    return markers


def _route_node_history(project_root: Path, run_root: Path, route_id: str, route: dict[str, Any]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for node in _route_nodes(route):
        node_id = str(node["node_id"])
        node_root = run_root / "routes" / route_id / "nodes" / node_id
        source_paths = {
            "node_acceptance_plan": _optional_source_path(project_root, node_root / "node_acceptance_plan.json"),
            "node_acceptance_plan_review": _optional_source_path(project_root, node_root / "reviews" / "node_acceptance_plan_review.json"),
            "parent_backward_replay": _optional_source_path(project_root, node_root / "parent_backward_replay.json"),
            "pm_parent_segment_decision": _optional_source_path(project_root, node_root / "pm_parent_segment_decision.json"),
        }
        nodes.append(
            {
                "node_id": node_id,
                "title": node.get("title"),
                "status": node.get("status") or "unknown",
                "created_by_mutation": bool(node.get("created_by_mutation")),
                "superseded_by": node.get("superseded_by"),
                "source_paths": {key: value for key, value in source_paths.items() if value},
            }
        )
    return nodes


def _refresh_route_memory(project_root: Path, run_root: Path, run_state: dict[str, Any], *, trigger: str) -> None:
    frontier = read_json_if_exists(run_root / "execution_frontier.json")
    route_id = str(frontier.get("active_route_id") or "")
    route_version = int(frontier.get("route_version") or 0)
    route_path = run_root / "routes" / route_id / "flow.json" if route_id else run_root / "routes" / "route-001" / "flow.json"
    route = read_json_if_exists(route_path)
    mutations_path = run_root / "routes" / route_id / "mutations.json" if route_id else run_root / "routes" / "route-001" / "mutations.json"
    mutations = read_json_if_exists(mutations_path)
    stale_ledger_path = run_root / "evidence" / "stale_evidence_ledger.json"
    stale_ledger = read_json_if_exists(stale_ledger_path)
    evidence_ledger_path = run_root / "evidence" / "evidence_ledger.json"
    evidence_ledger = read_json_if_exists(evidence_ledger_path)
    generated_ledger_path = run_root / "generated_resource_ledger.json"
    generated_ledger = read_json_if_exists(generated_ledger_path)
    completed_nodes = [str(item) for item in (frontier.get("completed_nodes") or [])]
    mutation_items = [item for item in (mutations.get("items") or []) if isinstance(item, dict)]
    superseded_nodes = sorted(
        {
            str(node_id)
            for item in mutation_items
            for node_id in (item.get("superseded_nodes") or [])
        }
    )
    stale_evidence = sorted(
        {
            str(item.get("evidence_id"))
            for item in (stale_ledger.get("items") or [])
            if isinstance(item, dict) and item.get("evidence_id")
        }
        | {
            str(evidence_id)
            for item in mutation_items
            for evidence_id in (item.get("stale_evidence") or [])
        }
    )
    effective_nodes = [str(node.get("node_id")) for node in _effective_route_nodes(route, mutations) if node.get("node_id")]
    route_nodes = _route_node_history(project_root, run_root, route_id or "route-001", route)
    reviewer_blocks = _event_markers(
        run_state,
        {
            "current_node_reviewer_blocks_result",
            "reviewer_reports_material_insufficient",
            "reviewer_blocks_material_scan_dispatch",
        },
    )
    reviewer_passes = _event_markers(
        run_state,
        {
            "reviewer_reports_material_sufficient",
            "reviewer_passes_research_direct_source_check",
            "reviewer_passes_node_acceptance_plan",
            "current_node_reviewer_passes_result",
            "reviewer_passes_parent_backward_replay",
            "reviewer_passes_evidence_quality_package",
            "reviewer_final_backward_replay_passed",
        },
    )
    research_or_experiments = []
    for label, path in (
        ("research_package", run_root / "research" / "research_package.json"),
        ("worker_research_report", run_root / "research" / "worker_research_report.json"),
        ("research_reviewer_report", run_root / "research" / "research_reviewer_report.json"),
        ("product_architecture_modelability", run_root / "flowguard" / "product_architecture_modelability.json"),
        ("root_contract_modelability", run_root / "flowguard" / "root_contract_modelability.json"),
        ("child_skill_conformance_model", run_root / "flowguard" / "child_skill_conformance_model.json"),
        ("child_skill_product_fit", run_root / "flowguard" / "child_skill_product_fit.json"),
    ):
        source_path = _optional_source_path(project_root, path)
        if source_path:
            research_or_experiments.append({"kind": label, "source_path": source_path})
    source_paths = {
        "router_state": project_relative(project_root, run_state_path(run_root)),
        "execution_frontier": _optional_source_path(project_root, run_root / "execution_frontier.json"),
        "active_route": _optional_source_path(project_root, route_path),
        "route_mutations": _optional_source_path(project_root, mutations_path),
        "packet_ledger": _optional_source_path(project_root, run_root / "packet_ledger.json"),
        "prompt_delivery_ledger": _optional_source_path(project_root, run_root / "prompt_delivery_ledger.json"),
        "evidence_ledger": _optional_source_path(project_root, evidence_ledger_path),
        "stale_evidence_ledger": _optional_source_path(project_root, stale_ledger_path),
        "generated_resource_ledger": _optional_source_path(project_root, generated_ledger_path),
    }
    history_index = {
        "schema_version": ROUTE_HISTORY_INDEX_SCHEMA,
        "run_id": run_state["run_id"],
        "generated_by": "controller",
        "controller_decision_authority": False,
        "sealed_packet_or_result_bodies_read": False,
        "trigger": trigger,
        "refreshed_at": utc_now(),
        "frontier": {
            "status": frontier.get("status"),
            "active_route_id": frontier.get("active_route_id"),
            "active_node_id": frontier.get("active_node_id"),
            "route_version": route_version,
            "completed_nodes": completed_nodes,
            "latest_mutation_path": frontier.get("latest_mutation_path"),
        },
        "route": {
            "effective_nodes": effective_nodes,
            "node_history": route_nodes,
            "route_node_count": len(route_nodes),
        },
        "mutations": {
            "count": len(mutation_items),
            "superseded_nodes": superseded_nodes,
            "items": [
                {
                    "route_version": item.get("route_version"),
                    "active_node_id": item.get("active_node_id"),
                    "reason": item.get("reason"),
                    "superseded_nodes": item.get("superseded_nodes") or [],
                    "stale_evidence": item.get("stale_evidence") or [],
                    "recorded_at": item.get("recorded_at"),
                }
                for item in mutation_items
            ],
        },
        "evidence": {
            "stale_evidence": stale_evidence,
            "unresolved_count": int(evidence_ledger.get("unresolved_count", 0) or 0),
            "stale_count": int(evidence_ledger.get("stale_count", 0) or 0),
            "generated_pending_resource_count": int(generated_ledger.get("pending_resource_count", 0) or 0),
            "generated_unresolved_resource_count": int(generated_ledger.get("unresolved_resource_count", 0) or 0),
        },
        "review_markers": {
            "blocks": reviewer_blocks,
            "passes": reviewer_passes,
        },
        "research_or_experiments": research_or_experiments,
        "source_paths": {key: value for key, value in source_paths.items() if value},
    }
    write_json(_route_history_index_path(run_root), history_index)
    pm_context = {
        "schema_version": PM_PRIOR_PATH_CONTEXT_SCHEMA,
        "run_id": run_state["run_id"],
        "generated_by": "controller",
        "controller_decision_authority": False,
        "sealed_packet_or_result_bodies_read": False,
        "trigger": trigger,
        "refreshed_at": history_index["refreshed_at"],
        "route_position": history_index["frontier"],
        "completed_nodes_considered": completed_nodes,
        "effective_nodes_considered": effective_nodes,
        "superseded_nodes_considered": superseded_nodes,
        "stale_evidence_considered": stale_evidence,
        "review_blocks_considered": reviewer_blocks,
        "review_passes_considered": reviewer_passes,
        "research_or_experiment_outputs_considered": research_or_experiments,
        "future_route_decision_requirements": [
            "Before route draft, route mutation, repair-node creation, node acceptance planning, resume continuation, final ledger, or closure, PM must read this current context and cite its path.",
            "PM must explain how completed, superseded, stale, blocked, and experimental history changes the next route or node decision.",
            "Controller-provided history is an index of reviewed files and state only; PM must not treat it as evidence beyond the cited source paths.",
        ],
        "source_paths": {
            **{key: value for key, value in source_paths.items() if value},
            "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
        },
    }
    write_json(_pm_prior_path_context_path(run_root), pm_context)
    run_state["flags"]["route_history_index_refreshed"] = True
    run_state["flags"]["pm_prior_path_context_refreshed"] = True


def _require_pm_prior_path_context(project_root: Path, run_root: Path, payload: dict[str, Any], *, purpose: str) -> dict[str, Any]:
    context_path = _pm_prior_path_context_path(run_root)
    history_path = _route_history_index_path(run_root)
    if not context_path.exists() or not history_path.exists():
        raise RouterError(f"{purpose} requires refreshed route memory before PM decision")
    review = payload.get("prior_path_context_review")
    if not isinstance(review, dict):
        raise RouterError(f"{purpose} requires prior_path_context_review")
    if review.get("reviewed") is not True:
        raise RouterError(f"{purpose} requires prior_path_context_review.reviewed=true")
    if review.get("controller_summary_used_as_evidence") is True:
        raise RouterError(f"{purpose} cannot treat Controller route history as acceptance evidence")
    expected_context = project_relative(project_root, context_path)
    expected_history = project_relative(project_root, history_path)
    source_paths = [str(path) for path in (review.get("source_paths") or [])]
    if expected_context not in source_paths:
        raise RouterError(f"{purpose} must cite current pm_prior_path_context.json")
    if expected_history not in source_paths:
        raise RouterError(f"{purpose} must cite current route_history_index.json")
    missing = [
        field
        for field in PM_PRIOR_PATH_CONTEXT_REVIEW_REQUIRED_FIELDS
        if field not in review and field not in {"reviewed", "source_paths"}
    ]
    if missing:
        raise RouterError(f"{purpose} prior_path_context_review missing fields: {', '.join(missing)}")
    return {
        "reviewed": True,
        "source_paths": [expected_context, expected_history],
        "completed_nodes_considered": review.get("completed_nodes_considered") or [],
        "superseded_nodes_considered": review.get("superseded_nodes_considered") or [],
        "stale_evidence_considered": review.get("stale_evidence_considered") or [],
        "prior_blocks_or_experiments_considered": review.get("prior_blocks_or_experiments_considered") or [],
        "impact_on_decision": review.get("impact_on_decision"),
        "controller_summary_used_as_evidence": False,
    }


def _pm_context_action_extra(project_root: Path, run_root: Path, entry: dict[str, str]) -> dict[str, Any]:
    if entry.get("to_role") != "project_manager":
        return {}
    context_path = _pm_prior_path_context_path(run_root)
    history_path = _route_history_index_path(run_root)
    extra = {
        "pm_context_paths": {
            "pm_prior_path_context": project_relative(project_root, context_path),
            "route_history_index": project_relative(project_root, history_path),
        },
        "pm_prior_path_context_required_for_decision": entry.get("card_id") in PM_PRIOR_CONTEXT_REQUIRED_CARD_IDS,
        "controller_history_is_evidence": False,
    }
    return extra


def _card_required_source_paths(project_root: Path, run_root: Path, card_id: str) -> dict[str, str]:
    source_paths: dict[str, str] = {}
    for label, relative_path in CARD_REQUIRED_SOURCE_PATHS.get(card_id, {}).items():
        path = run_root / relative_path
        if path.exists():
            source_paths[label] = project_relative(project_root, path)
    if card_id in {
        "process_officer.route_process_check",
        "product_officer.route_product_check",
        "reviewer.route_challenge",
    }:
        for draft_path in sorted((run_root / "routes").glob("*/flow.draft.json")):
            source_paths[f"route_draft_{draft_path.parent.name}"] = project_relative(project_root, draft_path)
    return source_paths


def _card_delivery_phase(card_id: str, card: dict[str, Any], frontier: dict[str, Any], run_state: dict[str, Any]) -> tuple[str, str | None]:
    card_phase = CARD_PHASE_BY_ID.get(card_id) or card.get("phase")
    current_phase = str(
        card_phase
        or frontier.get("phase")
        or frontier.get("status")
        or run_state.get("phase")
        or "unknown"
    )
    return current_phase, str(card_phase or "") or None


def _live_card_delivery_context(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    entry: dict[str, Any],
    card: dict[str, Any],
) -> dict[str, Any]:
    frontier = read_json_if_exists(run_root / "execution_frontier.json") or {}
    card_id = str(entry.get("card_id") or card.get("id") or "")
    current_phase, card_phase = _card_delivery_phase(card_id, card, frontier, run_state)
    user_request_path = str(
        run_state.get("user_request_path")
        or _optional_source_path(project_root, run_root / "user_request.json")
        or ""
    )
    source_paths = {
        "router_state": project_relative(project_root, run_state_path(run_root)),
        "execution_frontier": _optional_source_path(project_root, run_root / "execution_frontier.json"),
        "prompt_delivery_ledger": _optional_source_path(project_root, run_root / "prompt_delivery_ledger.json"),
        "packet_ledger": _optional_source_path(project_root, run_root / "packet_ledger.json"),
        "route_history_index": _optional_source_path(project_root, _route_history_index_path(run_root)),
        "pm_prior_path_context": _optional_source_path(project_root, _pm_prior_path_context_path(run_root)),
        "user_request_path": user_request_path or None,
    }
    source_paths.update(_card_required_source_paths(project_root, run_root, card_id))
    return {
        "schema_version": LIVE_CARD_CONTEXT_SCHEMA,
        "run_id": str(run_state.get("run_id") or run_root.name),
        "card_id": card_id,
        "to_role": str(entry.get("to_role") or card.get("audience") or ""),
        "current_task": {
            "user_request_path": user_request_path or None,
            "user_intake_packet_id": "user_intake" if (run_root / "mailbox" / "outbox" / "user_intake.json").exists() else None,
            "task_authority": "router_recorded_user_request_and_user_intake",
            "controller_summary_is_task_authority": False,
        },
        "current_stage": {
            "current_phase": current_phase,
            "card_phase": card_phase,
            "frontier_status": frontier.get("status"),
            "current_node_id": frontier.get("active_node_id"),
            "current_route_id": frontier.get("active_route_id"),
            "route_version": frontier.get("route_version"),
        },
        "source_paths": source_paths,
        "role_prompt_rule": (
            "Treat this router delivery envelope as the live context for the "
            "current run, current task, current card, current phase, and current "
            "node/frontier. If required context is missing or stale, do not "
            "continue from memory; return a protocol blocker through Controller."
        ),
    }


def _write_route_draft(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    prior_review = _require_pm_prior_path_context(project_root, run_root, payload, purpose="route draft")
    contract_path = run_root / "root_acceptance_contract.json"
    if not contract_path.exists():
        raise RouterError("route draft requires frozen root contract")
    contract = read_json(contract_path)
    if contract.get("status") != "frozen":
        raise RouterError("route draft requires root contract status=frozen")
    sync_path = run_root / "capabilities" / "capability_sync.json"
    child_manifest_path = run_root / "child_skill_gate_manifest.json"
    if not sync_path.exists():
        raise RouterError("route draft requires capability evidence sync")
    if not child_manifest_path.exists() or read_json(child_manifest_path).get("status") != "approved":
        raise RouterError("route draft requires approved child-skill gate manifest")
    route_id = str(payload.get("route_id") or "route-001")
    route_root = run_root / "routes" / route_id
    draft = payload.get("route") if isinstance(payload.get("route"), dict) else {}
    route_payload = {
        "schema_version": "flowpilot.route_draft.v1",
        "run_id": run_state["run_id"],
        "route_id": route_id,
        "route_version": int(payload.get("route_version") or 1),
        "source_root_contract": project_relative(project_root, contract_path),
        "prior_path_context_review": prior_review,
        "nodes": draft.get("nodes") or payload.get("nodes") or [],
        "written_by_role": "project_manager",
        "written_at": utc_now(),
        **_role_output_envelope_record(payload),
    }
    write_json(route_root / "flow.draft.json", route_payload)
    _write_display_plan_from_route(
        project_root,
        run_root,
        run_state,
        route_id=route_id,
        route_version=int(route_payload["route_version"]),
        route_payload=route_payload,
        active_node_id=None,
        source_event="pm_writes_route_draft",
    )


def _reset_route_review_after_route_draft_repair(run_state: dict[str, Any]) -> None:
    for flag in (
        "process_officer_route_check_card_delivered",
        "process_officer_route_check_passed",
        "product_officer_route_check_card_delivered",
        "product_officer_route_check_passed",
        "reviewer_route_check_card_delivered",
        "reviewer_route_check_passed",
        "route_activated_by_pm",
    ):
        run_state.setdefault("flags", {})[flag] = False


def _current_route_draft_path(run_root: Path) -> Path:
    route_root = run_root / "routes"
    candidates = sorted(route_root.glob("*/flow.draft.json")) if route_root.exists() else []
    if not candidates:
        raise RouterError("route check requires a route draft")
    if len(candidates) > 1:
        raise RouterError("route check requires an unambiguous current route draft")
    return candidates[0]


def _latest_event_payload(run_state: dict[str, Any], event_name: str) -> dict[str, Any]:
    for event in reversed(run_state.get("events", [])):
        if isinstance(event, dict) and event.get("event") == event_name:
            payload = event.get("payload")
            return payload if isinstance(payload, dict) else {}
    return {}


def _packet_paths(project_root: Path, run_state: dict[str, Any], packet_id: str) -> dict[str, Any]:
    return packet_runtime.packet_paths(project_root, packet_id, str(run_state["run_id"]))


def _packet_envelope_path(project_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> Path:
    raw_path = payload.get("packet_envelope_path")
    if raw_path:
        path = Path(str(raw_path))
        return path if path.is_absolute() else project_root / path
    packet_id = payload.get("packet_id")
    if not packet_id:
        raise RouterError("current-node packet event requires packet_id or packet_envelope_path")
    return _packet_paths(project_root, run_state, str(packet_id))["packet_envelope"]


def _result_envelope_path(project_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> Path:
    raw_path = payload.get("result_envelope_path")
    if raw_path:
        path = Path(str(raw_path))
        return path if path.is_absolute() else project_root / path
    packet_id = payload.get("packet_id") or _latest_event_payload(run_state, "pm_registers_current_node_packet").get("packet_id")
    if not packet_id:
        raise RouterError("current-node result event requires packet_id or result_envelope_path")
    return _packet_paths(project_root, run_state, str(packet_id))["result_envelope"]


def _current_node_packet_context(project_root: Path, run_state: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    payload = _latest_event_payload(run_state, "pm_registers_current_node_packet")
    envelope_path = _packet_envelope_path(project_root, run_state, payload)
    if not envelope_path.exists():
        raise RouterError(f"current-node packet envelope is missing: {envelope_path}")
    envelope = packet_runtime.load_envelope(project_root, envelope_path)
    return envelope, envelope_path


def _current_node_result_context(project_root: Path, run_state: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    payload = _latest_event_payload(run_state, "worker_current_node_result_returned")
    result_path = _result_envelope_path(project_root, run_state, payload)
    if not result_path.exists():
        raise RouterError(f"current-node result envelope is missing: {result_path}")
    result = packet_runtime.load_envelope(project_root, result_path)
    return result, result_path


def _packet_envelope_path_from_record(project_root: Path, run_state: dict[str, Any], record: dict[str, Any]) -> Path:
    raw_path = record.get("packet_envelope_path")
    if raw_path:
        path = Path(str(raw_path))
        return path if path.is_absolute() else project_root / path
    packet_id = record.get("packet_id")
    if not packet_id:
        raise RouterError("packet record requires packet_id or packet_envelope_path")
    return _packet_paths(project_root, run_state, str(packet_id))["packet_envelope"]


def _result_envelope_path_from_packet_record(project_root: Path, run_state: dict[str, Any], record: dict[str, Any]) -> Path:
    raw_path = record.get("result_envelope_path")
    if raw_path:
        path = Path(str(raw_path))
        return path if path.is_absolute() else project_root / path
    packet_id = record.get("packet_id")
    if not packet_id:
        raise RouterError("packet record requires packet_id or result_envelope_path")
    return _packet_paths(project_root, run_state, str(packet_id))["result_envelope"]


def _load_packet_index(path: Path, *, label: str) -> dict[str, Any]:
    if not path.exists():
        raise RouterError(f"{label} packet index is missing: {path}")
    index = read_json(path)
    if not isinstance(index.get("packets"), list) or not index["packets"]:
        raise RouterError(f"{label} packet index requires non-empty packets")
    return index


def _ensure_barrier_bundles_ready(project_root: Path, *, node_id: str | None = None) -> None:
    audit = packet_runtime.audit_barrier_bundles(project_root, node_id=node_id or None)
    if not audit.get("passed"):
        raise RouterError(
            "barrier bundle audit failed before packet relay: "
            + json.dumps(audit.get("blockers", []), sort_keys=True)
        )


def _material_scan_index_path(run_root: Path) -> Path:
    return run_root / "material" / "material_scan_packets.json"


def _research_packet_index_path(run_root: Path) -> Path:
    return run_root / "research" / "research_packet.json"


def _repair_transactions_root(run_root: Path) -> Path:
    return run_root / "control_blocks" / "repair_transactions"


def _repair_transaction_index_path(run_root: Path) -> Path:
    return _repair_transactions_root(run_root) / "repair_transaction_index.json"


def _repair_transaction_path(run_root: Path, transaction_id: str) -> Path:
    return _repair_transactions_root(run_root) / f"{transaction_id}.json"


def _repair_transaction_id(blocker_id: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in blocker_id).strip("-")
    return f"repair-tx-{safe or 'control-blocker'}"


def _repair_outcome_table(rerun_target: str) -> dict[str, dict[str, Any]]:
    if rerun_target == "reviewer_allows_material_scan_dispatch":
        return {
            "success": {
                "event": "reviewer_allows_material_scan_dispatch",
                "terminal": "complete",
            },
            "blocker": {
                "event": "reviewer_blocks_material_scan_dispatch_recheck",
                "terminal": "blocked",
            },
            "protocol_blocker": {
                "event": "reviewer_protocol_blocker_material_scan_dispatch_recheck",
                "terminal": "blocked",
            },
        }
    return {
        "success": {
            "event": rerun_target,
            "terminal": "complete",
        },
        "blocker": {
            "event": rerun_target,
            "terminal": "blocked",
            "shares_success_event": True,
        },
        "protocol_blocker": {
            "event": rerun_target,
            "terminal": "blocked",
            "shares_success_event": True,
        },
    }


def _repair_outcome_events(outcome_table: dict[str, Any]) -> list[str]:
    events: list[str] = []
    for name in ("success", "blocker", "protocol_blocker"):
        outcome = outcome_table.get(name)
        if not isinstance(outcome, dict):
            continue
        event = str(outcome.get("event") or "").strip()
        if event and event not in events:
            events.append(event)
    return events


def _repair_packet_specs_from_decision(
    project_root: Path,
    run_root: Path,
    decision: dict[str, Any],
    *,
    rerun_target: str,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    transaction = decision.get("repair_transaction") if isinstance(decision.get("repair_transaction"), dict) else {}
    raw_packets = (
        transaction.get("replacement_packets")
        or transaction.get("packets")
        or decision.get("replacement_packets")
        or decision.get("packets")
    )
    if isinstance(raw_packets, list) and raw_packets:
        return raw_packets, {
            "source": "decision_inline",
            "packet_count": len(raw_packets),
        }

    raw_path = (
        transaction.get("replacement_packet_specs_path")
        or transaction.get("packet_reissue_spec_path")
        or decision.get("replacement_packet_specs_path")
        or decision.get("packet_reissue_spec_path")
    )
    if not raw_path and rerun_target == "reviewer_allows_material_scan_dispatch":
        default_path = run_root / "material" / "pm_material_scan_packet_specs_reissue.project_manager.json"
        if default_path.exists():
            raw_path = project_relative(project_root, default_path)
    if not raw_path:
        return [], None

    spec_path = resolve_project_path(project_root, str(raw_path))
    if not spec_path.exists():
        raise RouterError(f"repair transaction packet spec path is missing: {raw_path}")
    expected_hash = (
        transaction.get("replacement_packet_specs_hash")
        or transaction.get("packet_reissue_spec_hash")
        or decision.get("replacement_packet_specs_hash")
        or decision.get("packet_reissue_spec_hash")
    )
    if expected_hash and packet_runtime.sha256_file(spec_path) != str(expected_hash):
        raise RouterError("repair transaction packet spec hash mismatch")
    spec = read_json(spec_path)
    packets = spec.get("packets")
    if not isinstance(packets, list) or not packets:
        raise RouterError("repair transaction packet spec requires non-empty packets")
    return packets, {
        "source": "packet_spec_file",
        "path": project_relative(project_root, spec_path),
        "sha256": packet_runtime.sha256_file(spec_path),
        "packet_count": len(packets),
    }


def _write_repair_transaction_index(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    root = _repair_transactions_root(run_root)
    transactions: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None
    if root.exists():
        for path in sorted(root.glob("repair-tx-*.json")):
            record = read_json_if_exists(path)
            if record.get("schema_version") != REPAIR_TRANSACTION_SCHEMA:
                continue
            summary = {
                "transaction_id": record.get("transaction_id"),
                "blocker_id": record.get("blocker_id"),
                "status": record.get("status"),
                "plan_kind": record.get("plan_kind"),
                "packet_generation_id": record.get("packet_generation_id"),
                "path": project_relative(project_root, path),
                "outcome_table": record.get("outcome_table"),
            }
            transactions.append(summary)
            if record.get("status") in {"opened", "committed", "awaiting_recheck"}:
                active = summary
    index = {
        "schema_version": REPAIR_TRANSACTION_INDEX_SCHEMA,
        "run_id": run_state.get("run_id"),
        "active_transaction": active,
        "transactions": transactions,
        "updated_at": utc_now(),
    }
    write_json(_repair_transaction_index_path(run_root), index)
    run_state["repair_transactions"] = transactions
    run_state["active_repair_transaction"] = active


def _commit_material_scan_repair_generation(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    transaction_id: str,
    packet_generation_id: str,
    packet_specs: list[dict[str, Any]],
) -> dict[str, Any]:
    existing_index = read_json_if_exists(_material_scan_index_path(run_root))
    superseded_packets = []
    for record in existing_index.get("packets", []) if isinstance(existing_index.get("packets"), list) else []:
        if isinstance(record, dict):
            superseded = dict(record)
            superseded["is_current_generation"] = False
            superseded["superseded_by_generation_id"] = packet_generation_id
            superseded_packets.append(superseded)

    records: list[dict[str, Any]] = []
    for index, spec in enumerate(packet_specs, start=1):
        if not isinstance(spec, dict):
            raise RouterError("each repair transaction packet spec must be an object")
        packet_id = str(spec.get("packet_id") or f"material-scan-repair-{index:03d}")
        to_role = str(spec.get("to_role") or "worker_a")
        if to_role not in {"worker_a", "worker_b"}:
            raise RouterError("material scan repair packet must target worker_a or worker_b")
        body_text = _material_packet_body_text_from_spec(project_root, spec)
        envelope = packet_runtime.create_packet(
            project_root,
            run_id=str(run_state["run_id"]),
            packet_id=packet_id,
            from_role="project_manager",
            to_role=to_role,
            node_id=str(spec.get("node_id") or "material-intake"),
            body_text=body_text,
            is_current_node=False,
            packet_type="material_scan",
            metadata={
                "stage": "material_scan",
                "source": "repair_transaction_commit",
                "repair_transaction_id": transaction_id,
                "packet_generation_id": packet_generation_id,
                "replacement_for": spec.get("replacement_for"),
                **(spec.get("metadata") if isinstance(spec.get("metadata"), dict) else {}),
            },
            output_contract=spec.get("output_contract") if isinstance(spec.get("output_contract"), dict) else None,
        )
        paths = packet_runtime.packet_paths(project_root, packet_id, str(run_state["run_id"]))
        records.append(
            {
                "packet_id": packet_id,
                "to_role": to_role,
                "packet_generation_id": packet_generation_id,
                "repair_transaction_id": transaction_id,
                "replacement_for": spec.get("replacement_for"),
                "is_current_generation": True,
                "packet_envelope_path": envelope["body_path"].replace("packet_body.md", "packet_envelope.json"),
                "result_envelope_path": project_relative(project_root, paths["result_envelope"]),
                "result_body_path": project_relative(project_root, paths["result_body"]),
                "result_write_target": {
                    "result_envelope_path": project_relative(project_root, paths["result_envelope"]),
                    "result_body_path": project_relative(project_root, paths["result_body"]),
                },
                "output_contract_id": envelope.get("output_contract_id"),
            }
        )

    write_json(
        _material_scan_index_path(run_root),
        {
            "schema_version": "flowpilot.material_scan_packets.v2",
            "run_id": run_state["run_id"],
            "written_by_role": "project_manager",
            "controller_may_read_packet_body": False,
            "reviewer_dispatch_required_before_worker": True,
            "current_generation_id": packet_generation_id,
            "repair_transaction_id": transaction_id,
            "packets": records,
            "superseded_packets": superseded_packets,
            "written_at": utc_now(),
        },
    )
    run_state["flags"]["material_scan_packets_relayed"] = False
    run_state["flags"]["worker_packets_delivered"] = False
    run_state["flags"]["worker_scan_results_returned"] = False
    run_state["flags"]["material_scan_results_relayed_to_reviewer"] = False
    run_state["flags"]["material_review_sufficient"] = False
    run_state["flags"]["material_review_insufficient"] = False
    run_state["material_review"] = None
    return {
        "packet_generation_id": packet_generation_id,
        "packet_count": len(records),
        "packets": records,
        "superseded_packet_count": len(superseded_packets),
        "dispatch_index_path": project_relative(project_root, _material_scan_index_path(run_root)),
        "packet_ledger_path": project_relative(project_root, run_root / "packet_ledger.json"),
    }


def _active_repair_transaction_for_event(run_root: Path, event: str) -> tuple[Path, dict[str, Any]] | tuple[None, None]:
    root = _repair_transactions_root(run_root)
    if not root.exists():
        return None, None
    for path in sorted(root.glob("repair-tx-*.json"), reverse=True):
        record = read_json_if_exists(path)
        if record.get("schema_version") != REPAIR_TRANSACTION_SCHEMA:
            continue
        if record.get("status") not in {"committed", "awaiting_recheck", "opened"}:
            continue
        if event in _repair_outcome_events(record.get("outcome_table") if isinstance(record.get("outcome_table"), dict) else {}):
            return path, record
    return None, None


def _repair_transaction_outcome_kind(transaction: dict[str, Any], event: str) -> str | None:
    table = transaction.get("outcome_table")
    if not isinstance(table, dict):
        return None
    for kind in ("success", "blocker", "protocol_blocker"):
        outcome = table.get(kind)
        if isinstance(outcome, dict) and outcome.get("event") == event:
            return kind
    return None


def _clear_successful_repair_lane_state(run_state: dict[str, Any], transaction: dict[str, Any], *, event: str) -> None:
    rerun_target = str(transaction.get("rerun_target") or "")
    is_material_repair = event in MATERIAL_REPAIR_OUTCOME_EVENTS or rerun_target in MATERIAL_REPAIR_OUTCOME_EVENTS
    flags = run_state.get("flags")
    if isinstance(flags, dict) and is_material_repair:
        for flag in MATERIAL_REPAIR_RECHECK_FLAGS:
            flags[flag] = False
        if event == "reviewer_allows_material_scan_dispatch":
            flags["material_scan_dispatch_blocked"] = False
    if is_material_repair:
        run_state["material_dispatch_block"] = None
    pending = run_state.get("pending_action")
    if isinstance(pending, dict):
        outcome_events = set(
            _repair_outcome_events(
                transaction.get("outcome_table") if isinstance(transaction.get("outcome_table"), dict) else {}
            )
        )
        pending_events = set(
            str(item)
            for item in pending.get("allowed_external_events", [])
            if isinstance(item, str)
        )
        if pending.get("repair_transaction_id") == transaction.get("transaction_id") or (
            pending_events and pending_events.issubset(outcome_events)
        ):
            run_state["pending_action"] = None


def _finalize_repair_transaction_outcome(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    payload: dict[str, Any] | None,
) -> dict[str, Any] | None:
    tx_path, transaction = _active_repair_transaction_for_event(run_root, event)
    if tx_path is None or transaction is None:
        return None
    outcome_kind = _repair_transaction_outcome_kind(transaction, event)
    if not outcome_kind:
        return None
    now = utc_now()
    transaction["reviewer_recheck"] = {
        "outcome": outcome_kind,
        "event": event,
        "payload_envelope_public_view": _control_payload_public_view(payload),
        "recorded_at": now,
    }
    if outcome_kind == "success":
        transaction["status"] = "complete"
        transaction["completed_at"] = now
        write_json(tx_path, transaction)
        _clear_successful_repair_lane_state(run_state, transaction, event=event)
        _write_repair_transaction_index(project_root, run_root, run_state)
        return {
            "transaction_id": transaction.get("transaction_id"),
            "outcome": outcome_kind,
            "status": "complete",
        }

    transaction["status"] = "blocked"
    transaction["blocked_at"] = now
    transaction["followup_blocker_required"] = True
    write_json(tx_path, transaction)

    blocker_id = str(transaction.get("blocker_id") or "")
    active = run_state.get("active_control_blocker")
    artifact_rel = str(active.get("blocker_artifact_path") or "") if isinstance(active, dict) else ""
    if artifact_rel:
        artifact_path = resolve_project_path(project_root, artifact_rel)
        if artifact_path.exists():
            blocker_record = read_json(artifact_path)
            if blocker_record.get("blocker_id") == blocker_id:
                blocker_record["resolution_status"] = f"repair_transaction_{outcome_kind}"
                blocker_record["resolved_by_event"] = event
                blocker_record["resolved_at"] = now
                blocker_record["repair_transaction_id"] = transaction.get("transaction_id")
                write_json(artifact_path, blocker_record)

    followup = _write_control_blocker(
        project_root,
        run_root,
        run_state,
        source="repair_transaction_recheck",
        error_message=(
            f"repair transaction {transaction.get('transaction_id')} ended with reviewer "
            f"{outcome_kind}; PM repair or routing decision is required before retrying dispatch."
        ),
        event=event,
        payload=payload,
    )
    transaction["followup_blocker_id"] = followup.get("blocker_id")
    transaction["followup_blocker_path"] = followup.get("blocker_artifact_path")
    write_json(tx_path, transaction)
    _write_repair_transaction_index(project_root, run_root, run_state)
    return {
        "transaction_id": transaction.get("transaction_id"),
        "outcome": outcome_kind,
        "status": "blocked",
        "followup_blocker_id": followup.get("blocker_id"),
    }


def _relay_packet_records(
    project_root: Path,
    run_state: dict[str, Any],
    records: list[dict[str, Any]],
    *,
    controller_agent_id: str,
) -> list[str]:
    relayed_ids: list[str] = []
    for record in records:
        envelope_path = _packet_envelope_path_from_record(project_root, run_state, record)
        if not envelope_path.exists():
            raise RouterError(f"packet envelope is missing: {envelope_path}")
        envelope = packet_runtime.load_envelope(project_root, envelope_path)
        _ensure_barrier_bundles_ready(project_root, node_id=str(envelope.get("node_id") or ""))
        packet_runtime.controller_relay_envelope(
            project_root,
            envelope=envelope,
            envelope_path=envelope_path,
            controller_agent_id=controller_agent_id,
            received_from_role=str(envelope.get("from_role") or "project_manager"),
            relayed_to_role=str(envelope.get("to_role")),
        )
        relayed_ids.append(str(envelope["packet_id"]))
    return relayed_ids


def _relay_result_records(
    project_root: Path,
    run_state: dict[str, Any],
    records: list[dict[str, Any]],
    *,
    to_role: str,
    controller_agent_id: str,
) -> list[str]:
    relayed_ids: list[str] = []
    agent_role_map = _agent_role_map_from_crew_ledger(project_root / str(run_state["run_root"]))
    for record in records:
        result_path = _result_envelope_path_from_packet_record(project_root, run_state, record)
        if not result_path.exists():
            raise RouterError(f"result envelope is missing: {result_path}")
        result = packet_runtime.load_envelope(project_root, result_path)
        if result.get("next_recipient") != to_role:
            raise RouterError(f"result envelope must route to {to_role}")
        if result.get("completed_by_role") == "controller":
            raise RouterError("Controller-origin result is invalid")
        packet_path = _packet_envelope_path_from_record(project_root, run_state, record)
        packet_envelope = packet_runtime.load_envelope(project_root, packet_path)
        audit = packet_runtime.validate_result_ready_for_reviewer_relay(
            project_root,
            packet_envelope=packet_envelope,
            result_envelope=result,
            agent_role_map=agent_role_map,
        )
        if not audit.get("passed"):
            raise RouterError(f"result envelope is not ready for reviewer relay: {audit.get('blockers')}")
        _ensure_barrier_bundles_ready(project_root, node_id=str(result.get("node_id") or ""))
        packet_runtime.controller_relay_envelope(
            project_root,
            envelope=result,
            envelope_path=result_path,
            controller_agent_id=controller_agent_id,
            received_from_role=str(result.get("completed_by_role") or "unknown"),
            relayed_to_role=to_role,
        )
        relayed_ids.append(str(result["packet_id"]))
    return relayed_ids


def _agent_role_map_from_crew_ledger(run_root: Path) -> dict[str, str] | None:
    crew = read_json_if_exists(run_root / "crew_ledger.json")
    role_slots = crew.get("role_slots") if isinstance(crew.get("role_slots"), list) else []
    agent_role_map: dict[str, str] = {}
    for slot in role_slots:
        if not isinstance(slot, dict):
            continue
        role_key = slot.get("role_key")
        agent_id = slot.get("agent_id")
        if isinstance(role_key, str) and isinstance(agent_id, str) and agent_id.strip():
            agent_role_map[agent_id.strip()] = role_key
    return agent_role_map or None


def _merge_agent_role_maps(primary: dict[str, str] | None, fallback: dict[str, str] | None) -> dict[str, str] | None:
    merged: dict[str, str] = {}
    if isinstance(fallback, dict):
        merged.update({str(key): str(value) for key, value in fallback.items()})
    if isinstance(primary, dict):
        merged.update({str(key): str(value) for key, value in primary.items()})
    return merged or None


def _validate_packet_bodies_opened_by_targets(project_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]]) -> None:
    for record in records:
        envelope_path = _packet_envelope_path_from_record(project_root, run_state, record)
        envelope = packet_runtime.load_envelope(project_root, envelope_path)
        expected_role = envelope.get("to_role")
        if envelope.get("body_opened_by_role", {}).get("role") != expected_role:
            raise RouterError(f"packet {envelope.get('packet_id')} body was not opened by target role after Controller relay")
        try:
            packet_runtime.verify_packet_open_receipt(project_root, envelope, role=str(expected_role))
        except packet_runtime.PacketRuntimeError as exc:
            raise RouterError(f"packet {envelope.get('packet_id')} ledger open receipt is invalid: {exc}") from exc


def _validate_results_exist_for_packets(project_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]], *, next_recipient: str) -> None:
    run_root = project_root / str(run_state["run_root"])
    agent_role_map = _agent_role_map_from_crew_ledger(run_root)
    for record in records:
        result_path = _result_envelope_path_from_packet_record(project_root, run_state, record)
        if not result_path.exists():
            raise RouterError(f"result envelope is missing: {result_path}")
        result = packet_runtime.load_envelope(project_root, result_path)
        if result.get("next_recipient") != next_recipient:
            raise RouterError(f"result envelope for packet {result.get('packet_id')} must route to {next_recipient}")
        if result.get("completed_by_role") == "controller":
            raise RouterError("Controller-origin result is invalid")
        packet_path = _packet_envelope_path_from_record(project_root, run_state, record)
        packet_envelope = packet_runtime.load_envelope(project_root, packet_path)
        audit = packet_runtime.validate_result_ready_for_reviewer_relay(
            project_root,
            packet_envelope=packet_envelope,
            result_envelope=result,
            agent_role_map=agent_role_map,
        )
        if not audit.get("passed"):
            raise RouterError(f"result envelope for packet {result.get('packet_id')} failed pre-relay audit: {audit.get('blockers')}")


def _validate_packet_group_for_reviewer(
    project_root: Path,
    run_state: dict[str, Any],
    records: list[dict[str, Any]],
    *,
    audit_path: Path,
    agent_role_map: dict[str, str] | None = None,
) -> None:
    trusted_agent_role_map = _agent_role_map_from_crew_ledger(project_root / str(run_state["run_root"]))
    merged_agent_role_map = _merge_agent_role_maps(trusted_agent_role_map, agent_role_map)
    audits: list[dict[str, Any]] = []
    blockers: list[str] = []
    evidence_paths: list[Path] = []
    for record in records:
        packet_path = _packet_envelope_path_from_record(project_root, run_state, record)
        result_path = _result_envelope_path_from_packet_record(project_root, run_state, record)
        evidence_paths.extend([packet_path, result_path])
        packet_envelope = packet_runtime.load_envelope(project_root, packet_path)
        result_envelope = packet_runtime.load_envelope(project_root, result_path)
        audit = packet_runtime.validate_for_reviewer(
            project_root,
            packet_envelope=packet_envelope,
            result_envelope=result_envelope,
            agent_role_map=merged_agent_role_map,
        )
        audits.append(audit)
        blockers.extend(str(blocker) for blocker in audit.get("blockers") or [])
    run_root = project_root / str(run_state["run_root"])
    proof_path = _router_owned_check_proof_path(audit_path)
    write_json(
        audit_path,
        {
            "schema_version": "flowpilot.packet_group_reviewer_audit.v1",
            "run_id": run_state["run_id"],
            "reviewed_by_role": "human_like_reviewer",
            "router_replacement_scope": "mechanical_only",
            "self_attested_ai_claims_accepted_as_proof": False,
            "router_owned_check_proof_path": project_relative(project_root, proof_path),
            "packet_count": len(records),
            "audits": audits,
            "blockers": blockers,
            "passed": not blockers,
            "reviewed_at": utc_now(),
        },
    )
    _write_router_owned_check_proof(
        project_root,
        run_root,
        check_name="packet_group_reviewer_audit",
        audit_path=audit_path,
        source_kind="packet_runtime_hash",
        evidence_paths=evidence_paths,
    )
    _validate_router_owned_check_proof(
        project_root,
        run_root,
        check_name="packet_group_reviewer_audit",
        audit_path=audit_path,
    )
    if blockers:
        raise RouterError(f"packet group reviewer audit failed: {blockers}")


def _active_frontier(run_root: Path) -> dict[str, Any]:
    frontier = read_json_if_exists(run_root / "execution_frontier.json")
    if not frontier.get("active_route_id") or not frontier.get("active_node_id"):
        raise RouterError("active execution frontier is missing route or node")
    return frontier


def _active_route_path(run_root: Path, frontier: dict[str, Any]) -> Path:
    return run_root / "routes" / str(frontier["active_route_id"]) / "flow.json"


def _active_route_flow(run_root: Path, frontier: dict[str, Any]) -> dict[str, Any]:
    route_path = _active_route_path(run_root, frontier)
    if not route_path.exists():
        raise RouterError(f"active route flow is missing: {route_path}")
    return read_json(route_path)


def _iter_route_nodes(route: dict[str, Any]) -> list[dict[str, Any]]:
    raw_nodes = route.get("nodes")
    if isinstance(raw_nodes, dict):
        return [item for item in raw_nodes.values() if isinstance(item, dict)]
    if isinstance(raw_nodes, list):
        return [item for item in raw_nodes if isinstance(item, dict)]
    return []


def _active_node_definition(run_root: Path, frontier: dict[str, Any]) -> dict[str, Any]:
    route = _active_route_flow(run_root, frontier)
    active_node_id = str(frontier["active_node_id"])
    for node in _iter_route_nodes(route):
        if node.get("node_id") == active_node_id or node.get("id") == active_node_id:
            return node
    return {"node_id": active_node_id}


def _node_child_ids(node: dict[str, Any]) -> list[str]:
    for key in ("child_node_ids", "children", "child_nodes"):
        raw_children = node.get(key)
        if isinstance(raw_children, list):
            child_ids: list[str] = []
            for child in raw_children:
                if isinstance(child, str):
                    child_ids.append(child)
                elif isinstance(child, dict):
                    child_id = child.get("node_id") or child.get("id")
                    if child_id:
                        child_ids.append(str(child_id))
            return child_ids
    return []


def _active_node_has_children(run_root: Path, frontier: dict[str, Any]) -> bool:
    return bool(_node_child_ids(_active_node_definition(run_root, frontier)))


def _active_node_root(run_root: Path, frontier: dict[str, Any]) -> Path:
    return run_root / "routes" / str(frontier["active_route_id"]) / "nodes" / str(frontier["active_node_id"])


def _active_node_acceptance_plan_path(run_root: Path, frontier: dict[str, Any]) -> Path:
    return _active_node_root(run_root, frontier) / "node_acceptance_plan.json"


def _active_node_write_grant_path(run_root: Path, frontier: dict[str, Any]) -> Path:
    return _active_node_root(run_root, frontier) / "current_node_write_grant.json"


def _active_node_completion_ledger_path(run_root: Path, frontier: dict[str, Any]) -> Path:
    return _active_node_root(run_root, frontier) / "node_completion_ledger.json"


def _task_completion_projection_path(run_root: Path) -> Path:
    return run_root / "completion" / "task_completion_projection.json"


def _resume_decision_path(run_root: Path) -> Path:
    return run_root / "continuation" / "pm_resume_decision.json"


def _resume_waits_for_pm_decision(run_state: dict[str, Any]) -> bool:
    flags = run_state["flags"]
    return (
        bool(flags.get("resume_reentry_requested"))
        and bool(flags.get("resume_state_loaded"))
        and bool(flags.get("resume_roles_restored"))
        and bool(flags.get("crew_rehydration_report_written"))
        and bool(flags.get("pm_resume_decision_card_delivered"))
        and not bool(flags.get("pm_resume_recovery_decision_returned"))
    )


def _write_pm_resume_decision(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("decision_owner") != "project_manager":
        raise RouterError("PM resume decision requires decision_owner=project_manager")
    prior_review = _require_pm_prior_path_context(project_root, run_root, payload, purpose="PM resume decision")
    resume_path = run_root / "continuation" / "resume_reentry.json"
    if not resume_path.exists():
        raise RouterError("PM resume decision requires continuation/resume_reentry.json")
    resume_evidence = read_json(resume_path)
    rehydration_path = run_root / "continuation" / "crew_rehydration_report.json"
    if not run_state["flags"].get("resume_roles_restored") or not rehydration_path.exists():
        raise RouterError("PM resume decision requires crew_rehydration_report before PM runway")
    rehydration_report = read_json(rehydration_path)
    if rehydration_report.get("all_six_roles_ready") is not True:
        raise RouterError("PM resume decision requires all six roles ready")
    if rehydration_report.get("pm_memory_rehydrated") is not True and rehydration_report.get("background_agents_mode") != "single-agent":
        raise RouterError("PM resume decision requires project_manager memory rehydration")
    decision = str(payload.get("decision") or "continue_current_packet_loop")
    if decision not in PM_RESUME_DECISION_ALLOWED_VALUES:
        raise RouterError(f"unsupported PM resume decision: {decision}")
    reminder = payload.get("controller_reminder")
    if not isinstance(reminder, dict):
        raise RouterError("PM resume decision requires controller_reminder")
    if reminder.get("controller_only") is not True:
        raise RouterError("PM resume decision must remind Controller it is controller_only")
    if reminder.get("controller_may_read_sealed_bodies") is not False:
        raise RouterError("PM resume decision must forbid sealed body reads")
    if reminder.get("controller_may_infer_from_chat_history") is not False:
        raise RouterError("PM resume decision must forbid chat-history route inference")
    if reminder.get("controller_may_advance_or_close_route") is not False:
        raise RouterError("PM resume decision must forbid Controller route advance or closure")
    ambiguous = bool(resume_evidence.get("ambiguous_state_blocks_controller_execution"))
    recovery_recorded = bool(payload.get("explicit_recovery_evidence_recorded"))
    if ambiguous and decision == "continue_current_packet_loop" and not recovery_recorded:
        raise RouterError("ambiguous resume state cannot continue without explicit recovery evidence")
    if decision == "close_after_final_ledger_and_terminal_replay" and not (
        run_state["flags"].get("final_ledger_built_clean") and run_state["flags"].get("final_backward_replay_passed")
    ):
        raise RouterError("resume closure requires final ledger and terminal replay to have passed")
    write_json(
        _resume_decision_path(run_root),
        {
            "schema_version": "flowpilot.pm_resume_decision.v1",
            "run_id": run_state["run_id"],
            "decision_owner": "project_manager",
            "decision": decision,
            "resume_ambiguous": ambiguous,
            "explicit_recovery_evidence_recorded": recovery_recorded,
            "source_paths": {
                "resume_reentry": project_relative(project_root, resume_path),
                "router_state": project_relative(project_root, run_state_path(run_root)),
                "execution_frontier": project_relative(project_root, run_root / "execution_frontier.json"),
                "packet_ledger": project_relative(project_root, run_root / "packet_ledger.json"),
                "prompt_delivery_ledger": project_relative(project_root, run_root / "prompt_delivery_ledger.json"),
                "crew_ledger": project_relative(project_root, run_root / "crew_ledger.json"),
                "crew_memory": project_relative(project_root, run_root / "crew_memory"),
                "crew_rehydration_report": project_relative(project_root, rehydration_path),
                "pm_prior_path_context": project_relative(project_root, _pm_prior_path_context_path(run_root)),
                "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
            },
            "crew_rehydration_report": {
                "path": project_relative(project_root, rehydration_path),
                "all_six_roles_ready": bool(rehydration_report.get("all_six_roles_ready")),
                "current_run_memory_complete": bool(rehydration_report.get("current_run_memory_complete")),
                "pm_memory_rehydrated": bool(rehydration_report.get("pm_memory_rehydrated")),
                "missing_memory_role_keys": rehydration_report.get("missing_memory_role_keys") or [],
            },
            "prior_path_context_review": prior_review,
            "controller_reminder": {
                "controller_only": True,
                "controller_may_read_sealed_bodies": False,
                "controller_may_infer_from_chat_history": False,
                "controller_may_advance_or_close_route": False,
                "controller_may_create_project_evidence": False,
            },
            "recorded_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )
    _write_display_plan_from_pm_payload(
        project_root,
        run_root,
        run_state,
        payload,
        source_event="pm_resume_recovery_decision_returned",
    )


def _write_node_acceptance_plan(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    prior_review = _require_pm_prior_path_context(project_root, run_root, payload, purpose="node acceptance plan")
    if payload.get("pm_owned", True) is not True:
        raise RouterError("node acceptance plan must be PM-owned")
    frontier = _active_frontier(run_root)
    active_node_id = str(frontier["active_node_id"])
    active_route_id = str(frontier["active_route_id"])
    if payload.get("node_id") and str(payload["node_id"]) != active_node_id:
        raise RouterError("node acceptance plan node_id must match active frontier")
    route_version = int(frontier.get("route_version") or 0)
    if payload.get("route_version") is not None and int(payload["route_version"]) != route_version:
        raise RouterError("node acceptance plan route_version must match active frontier")
    node_requirements = payload.get("node_requirements")
    if not isinstance(node_requirements, list) or not node_requirements:
        raise RouterError("node acceptance plan requires a non-empty node_requirements list")
    experiment_plan = payload.get("experiment_plan")
    if not isinstance(experiment_plan, list):
        raise RouterError("node acceptance plan requires experiment_plan list")
    high_standard = payload.get("high_standard_recheck")
    if not isinstance(high_standard, dict):
        raise RouterError("node acceptance plan requires high_standard_recheck")
    required_high_standard_fields = {
        "ideal_outcome",
        "unacceptable_outcomes",
        "higher_standard_opportunities",
        "semantic_downgrade_risks",
        "decision",
        "why_current_plan_meets_highest_reasonable_standard",
    }
    def _blank(value: Any) -> bool:
        return value is None or value == "" or value == []

    missing_high_standard = [
        name
        for name in sorted(required_high_standard_fields)
        if name not in high_standard or _blank(high_standard.get(name))
    ]
    if missing_high_standard:
        raise RouterError(f"node high-standard recheck missing fields: {', '.join(missing_high_standard)}")
    if str(high_standard.get("decision")) != "proceed":
        raise RouterError("node acceptance can proceed only after high_standard_recheck.decision=proceed")
    if high_standard.get("controller_can_downgrade_standard") is True:
        raise RouterError("Controller cannot downgrade node standards")
    node = _active_node_definition(run_root, frontier)
    child_ids = _node_child_ids(node)
    plan = {
        "schema_version": "flowpilot.node_acceptance_plan.v1",
        "run_id": run_state["run_id"],
        "route_id": active_route_id,
        "route_version": route_version,
        "node_id": active_node_id,
        "pm_owned": True,
        "status": str(payload.get("status") or "approved"),
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "source_paths": {
            "root_acceptance_contract": project_relative(project_root, run_root / "root_acceptance_contract.json"),
            "execution_frontier": project_relative(project_root, run_root / "execution_frontier.json"),
            "route_flow": project_relative(project_root, _active_route_path(run_root, frontier)),
            "product_function_architecture": project_relative(project_root, run_root / "product_function_architecture.json"),
            "pm_prior_path_context": project_relative(project_root, _pm_prior_path_context_path(run_root)),
            "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
        },
        "prior_path_context_review": prior_review,
        "node_structure": {
            "node_kind": "parent" if child_ids else "leaf",
            "has_children": bool(child_ids),
            "child_node_ids": child_ids,
            "parent_backward_replay_required": bool(child_ids),
            "semantic_importance_used_to_trigger_review": False,
        },
        "node_requirements": node_requirements,
        "experiment_plan": experiment_plan,
        "high_standard_recheck": {
            "ideal_outcome": high_standard.get("ideal_outcome"),
            "unacceptable_outcomes": high_standard.get("unacceptable_outcomes"),
            "higher_standard_opportunities": high_standard.get("higher_standard_opportunities"),
            "semantic_downgrade_risks": high_standard.get("semantic_downgrade_risks"),
            "decision": "proceed",
            "why_current_plan_meets_highest_reasonable_standard": high_standard.get("why_current_plan_meets_highest_reasonable_standard"),
            "controller_can_downgrade_standard": False,
        },
        "advance_gate": {
            "required_before_chunk_execution": True,
            "required_before_node_checkpoint": True,
            "reviewer_or_officer_direct_check_required": True,
        },
        "written_by_role": "project_manager",
    }
    write_json(_active_node_acceptance_plan_path(run_root, frontier), plan)
    _update_display_plan_current_node(
        project_root,
        run_root,
        run_state,
        node_id=str(frontier["active_node_id"]),
        node_title=str(node.get("title") or node.get("label") or frontier["active_node_id"]),
        checklist=[
            {
                "id": str(item.get("requirement_id") or f"requirement-{index:03d}"),
                "label": str(item.get("acceptance_statement") or item.get("label") or item.get("requirement_id") or f"Requirement {index}"),
                "status": "pending",
            }
            for index, item in enumerate(node_requirements, start=1)
            if isinstance(item, dict)
        ],
        source_event="pm_writes_node_acceptance_plan",
    )


def _write_parent_backward_targets(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    frontier = _active_frontier(run_root)
    node = _active_node_definition(run_root, frontier)
    child_ids = _node_child_ids(node)
    route_id = str(frontier["active_route_id"])
    route_version = int(frontier.get("route_version") or 0)
    active_node_id = str(frontier["active_node_id"])
    node_root = _active_node_root(run_root, frontier)
    targets = [
        {
            "parent_node_id": active_node_id,
            "child_node_ids": child_ids,
            "parent_backward_replay_path": project_relative(project_root, node_root / "parent_backward_replay.json"),
            "status": "not_started" if child_ids else "not_required",
            "pm_segment_decision": "not_reviewed" if child_ids else "not_required",
            "latest_repair_requires_rerun": False,
            "latest_replay_route_version": route_version,
        }
    ] if child_ids else []
    record = {
        "schema_version": "flowpilot.parent_backward_targets.v1",
        "run_id": run_state["run_id"],
        "route_id": route_id,
        "route_version": route_version,
        "pm_owned": True,
        "status": "current",
        "built_from_flow_path": project_relative(project_root, _active_route_path(run_root, frontier)),
        "built_at": utc_now(),
        "trigger_rule": {
            "structural_trigger": "any_effective_route_node_with_children",
            "semantic_importance_classification_required": False,
            "leaf_nodes_exempt_from_parent_backward_replay": True,
        },
        "targets": targets,
        "coverage": {
            "parent_targets_total": len(targets),
            "parent_targets_with_replay_passed": 0,
            "parent_targets_with_pm_decision": 0,
            "all_required_parent_replays_passed": not child_ids,
        },
        "written_by_role": "project_manager",
    }
    write_json(run_root / "routes" / route_id / "parent_backward_targets.json", record)


def _write_parent_backward_replay(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    frontier = _active_frontier(run_root)
    if not _active_node_has_children(run_root, frontier):
        raise RouterError("parent backward replay is required only for active nodes with children")
    targets_path = run_root / "routes" / str(frontier["active_route_id"]) / "parent_backward_targets.json"
    if not targets_path.exists():
        raise RouterError("parent backward replay requires parent_backward_targets.json")
    if payload.get("reviewed_by_role") != "human_like_reviewer":
        raise RouterError("parent backward replay must be reviewed_by_role=human_like_reviewer")
    if payload.get("passed") is not True:
        raise RouterError("parent backward replay must explicitly pass")
    active_node_id = str(frontier["active_node_id"])
    replay = {
        "schema_version": "flowpilot.parent_backward_replay.v1",
        "run_id": run_state["run_id"],
        "route_id": str(frontier["active_route_id"]),
        "route_version": int(frontier.get("route_version") or 0),
        "parent_node_id": active_node_id,
        "pm_owned": True,
        "status": "passed",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "source_paths": {
            "parent_backward_targets": project_relative(project_root, targets_path),
            "node_acceptance_plan": project_relative(project_root, _active_node_acceptance_plan_path(run_root, frontier)),
        },
        "reviewer_report": {
            "reviewer_role": "human_like_reviewer",
            "neutral_observation_written": bool(payload.get("neutral_observation_written", True)),
            "independent_probe_done": bool(payload.get("independent_probe_done", True)),
            "child_evidence_replayed": bool(payload.get("child_evidence_replayed", True)),
            "children_compose_into_parent_goal": True,
            "blocking_findings": [],
            "approval_valid": True,
        },
        "closure_gate": {
            "required_before_parent_checkpoint": True,
            "reviewer_passed": True,
            "unresolved_blocking_findings": 0,
            "parent_closure_allowed": False,
        },
        **_role_output_envelope_record(payload),
    }
    write_json(_active_node_root(run_root, frontier) / "parent_backward_replay.json", replay)


def _write_parent_segment_decision(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> str:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("decision_owner") != "project_manager":
        raise RouterError("parent segment decision requires decision_owner=project_manager")
    prior_review = _require_pm_prior_path_context(project_root, run_root, payload, purpose="parent segment decision")
    frontier = _active_frontier(run_root)
    replay_path = _active_node_root(run_root, frontier) / "parent_backward_replay.json"
    if not replay_path.exists():
        raise RouterError("parent segment decision requires parent_backward_replay.json")
    decision = str(payload.get("decision") or "continue")
    if decision not in PM_PARENT_SEGMENT_DECISION_ALLOWED_VALUES:
        raise RouterError(f"unsupported parent segment decision: {decision}")
    record = {
        "schema_version": "flowpilot.parent_segment_decision.v1",
        "run_id": run_state["run_id"],
        "route_id": str(frontier["active_route_id"]),
        "route_version": int(frontier.get("route_version") or 0),
        "parent_node_id": str(frontier["active_node_id"]),
        "decision_owner": "project_manager",
        "decision": decision,
        "route_mutation_required": decision != "continue",
        "same_parent_replay_rerun_required": decision != "continue",
        "prior_path_context_review": prior_review,
        "source_paths": {
            "parent_backward_replay": project_relative(project_root, replay_path),
            "pm_prior_path_context": project_relative(project_root, _pm_prior_path_context_path(run_root)),
            "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
        },
        "recorded_at": utc_now(),
        **_role_output_envelope_record(payload),
    }
    write_json(_active_node_root(run_root, frontier) / "pm_parent_segment_decision.json", record)
    if decision != "continue":
        repair_node_id = str(payload.get("repair_node_id") or f"{frontier['active_node_id']}-repair-{int(frontier.get('route_version') or 1) + 1}")
        _write_route_mutation(
            project_root,
            run_root,
            run_state,
            {
                "route_id": frontier["active_route_id"],
                "repair_node_id": repair_node_id,
                "reason": f"parent_segment_decision:{decision}",
                "stale_evidence": [project_relative(project_root, replay_path)],
                "superseded_nodes": payload.get("superseded_nodes") or [],
                "prior_path_context_review": payload.get("prior_path_context_review"),
            },
        )
    return decision


def _write_pm_research_absorption(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    reviewer_report_path = run_root / "research" / "research_reviewer_report.json"
    audit_path = run_root / "research" / "research_packet_review_audit.json"
    if not reviewer_report_path.exists():
        raise RouterError("PM can absorb research only after reviewer research report exists")
    if not audit_path.exists():
        raise RouterError("PM can absorb research only after packet-group reviewer runtime audit exists")
    audit = read_json(audit_path)
    if audit.get("passed") is not True:
        raise RouterError("PM can absorb research only after packet-group reviewer runtime audit passed")
    packet_ledger_path = run_root / "packet_ledger.json"
    if not packet_ledger_path.exists():
        raise RouterError("PM research absorption requires packet_ledger.json")
    absorption_path = run_root / "research" / "pm_research_absorption.json"
    write_json(
        absorption_path,
        {
            "schema_version": "flowpilot.pm_research_absorption.v1",
            "run_id": run_state["run_id"],
            "absorbed_by_role": "project_manager",
            "research_reviewer_report_path": project_relative(project_root, reviewer_report_path),
            "research_reviewer_report_hash": hashlib.sha256(reviewer_report_path.read_bytes()).hexdigest(),
            "packet_group_reviewer_audit_path": project_relative(project_root, audit_path),
            "packet_group_reviewer_audit_hash": hashlib.sha256(audit_path.read_bytes()).hexdigest(),
            "packet_ledger_path": project_relative(project_root, packet_ledger_path),
            "packet_ledger_hash": hashlib.sha256(packet_ledger_path.read_bytes()).hexdigest(),
            "packet_group_audit_passed": True,
            "absorbed_at": utc_now(),
        },
    )


def _validate_current_node_packet_event(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    if not run_state["flags"].get("node_acceptance_plan_reviewer_passed"):
        raise RouterError("current-node packet requires reviewer-passed node acceptance plan")
    envelope_path = _packet_envelope_path(project_root, run_state, payload)
    if not envelope_path.exists():
        raise RouterError(f"current-node packet envelope is missing: {envelope_path}")
    envelope = packet_runtime.load_envelope(project_root, envelope_path)
    frontier = _active_frontier(run_root)
    active_node = frontier.get("active_node_id")
    if active_node and envelope.get("node_id") != active_node:
        raise RouterError(
            f"packet node_id {envelope.get('node_id')!r} does not match frontier active_node_id {active_node!r}"
        )
    route_version = int(frontier.get("route_version") or 0)
    packet_route_version = envelope.get("metadata", {}).get("route_version")
    if packet_route_version is None:
        raise RouterError("current-node packet metadata.route_version is required")
    if int(packet_route_version) != route_version:
        raise RouterError("current-node packet route_version must match active frontier")
    plan_path = _active_node_acceptance_plan_path(run_root, frontier)
    if not plan_path.exists():
        raise RouterError("current-node packet requires node_acceptance_plan.json")
    if envelope.get("from_role") != "project_manager":
        raise RouterError("current-node packet must be issued by project_manager")
    if envelope.get("to_role") == "controller":
        raise RouterError("current-node packet cannot assign product work to Controller")
    if envelope.get("body_visibility") != packet_runtime.SEALED_BODY_VISIBILITY:
        raise RouterError("current-node packet body must be sealed to the target role")
    grant_path = _active_node_write_grant_path(run_root, frontier)
    write_json(
        grant_path,
        {
            "schema_version": "flowpilot.current_node_write_grant.v1",
            "run_id": run_state["run_id"],
            "route_id": str(frontier["active_route_id"]),
            "route_version": route_version,
            "node_id": str(frontier["active_node_id"]),
            "packet_id": str(envelope["packet_id"]),
            "granted_to_role": str(envelope["to_role"]),
            "granted_by_role": "project_manager",
            "grant_scope": "current_node_packet_body_and_result_only",
            "packet_envelope_path": project_relative(project_root, envelope_path),
            "packet_envelope_hash": hashlib.sha256(envelope_path.read_bytes()).hexdigest(),
            "packet_body_path": str(envelope.get("body_path") or ""),
            "packet_body_hash": str(envelope.get("body_hash") or ""),
            "controller_may_read_packet_body": False,
            "controller_may_write_project_artifacts": False,
            "issued_at": utc_now(),
        },
    )
    run_state["flags"]["current_node_write_grant_issued"] = True


def _validate_current_node_result_event(project_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    run_root = project_root / str(run_state["run_root"])
    frontier = _active_frontier(run_root)
    grant_path = _active_node_write_grant_path(run_root, frontier)
    if not run_state["flags"].get("current_node_write_grant_issued") or not grant_path.exists():
        raise RouterError("current-node worker result requires a current-node write grant")
    grant = read_json(grant_path)
    result_path = _result_envelope_path(project_root, run_state, payload)
    if not result_path.exists():
        raise RouterError(f"current-node result envelope is missing: {result_path}")
    result = packet_runtime.load_envelope(project_root, result_path)
    if str(result.get("packet_id") or "") != str(grant.get("packet_id") or ""):
        raise RouterError("current-node result packet_id does not match current-node write grant")
    if str(result.get("completed_by_role") or "") != str(grant.get("granted_to_role") or ""):
        raise RouterError("wrong role: current-node result completed_by_role does not match current-node write grant")
    if result.get("next_recipient") != "human_like_reviewer":
        raise RouterError("current-node worker result must route to human_like_reviewer")
    if result.get("completed_by_role") == "controller":
        raise RouterError("Controller-origin current-node result is invalid")
    packet_envelope, _packet_envelope_path = _current_node_packet_context(project_root, run_state)
    agent_role_map = _agent_role_map_from_crew_ledger(run_root)
    audit = packet_runtime.validate_result_ready_for_reviewer_relay(
        project_root,
        packet_envelope=packet_envelope,
        result_envelope=result,
        agent_role_map=agent_role_map,
    )
    if not audit.get("passed"):
        raise RouterError(f"current-node result failed pre-relay packet runtime audit: {audit.get('blockers')}")


def _validate_current_node_reviewer_pass(project_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != "human_like_reviewer":
        raise RouterError("current-node reviewer pass must be reviewed_by_role=human_like_reviewer")
    if payload.get("passed") is not True:
        raise RouterError("current-node reviewer pass must explicitly pass")
    run_root = project_root / str(run_state["run_root"])
    packet_envelope, packet_envelope_path = _current_node_packet_context(project_root, run_state)
    result_envelope, result_envelope_path = _current_node_result_context(project_root, run_state)
    raw_agent_map = payload.get("agent_role_map")
    payload_agent_role_map = raw_agent_map if isinstance(raw_agent_map, dict) else None
    trusted_agent_role_map = _agent_role_map_from_crew_ledger(run_root)
    agent_role_map = _merge_agent_role_maps(trusted_agent_role_map, payload_agent_role_map)
    audit = packet_runtime.validate_for_reviewer(
        project_root,
        packet_envelope=packet_envelope,
        result_envelope=result_envelope,
        agent_role_map=agent_role_map,
    )
    frontier = _active_frontier(run_root)
    audit_path = _active_node_root(run_root, frontier) / "reviews" / "current_node_packet_runtime_audit.json"
    proof_path = _router_owned_check_proof_path(audit_path)
    packet_body_path = resolve_project_path(project_root, str(packet_envelope.get("body_path") or ""))
    result_body_path = resolve_project_path(project_root, str(result_envelope.get("result_body_path") or ""))
    write_json(
        audit_path,
        {
            "schema_version": "flowpilot.current_node_packet_runtime_audit.v1",
            "run_id": run_state["run_id"],
            "route_id": str(frontier["active_route_id"]),
            "route_version": int(frontier.get("route_version") or 0),
            "node_id": str(frontier["active_node_id"]),
            "reviewed_by_role": "human_like_reviewer",
            "router_replacement_scope": "mechanical_only",
            "self_attested_ai_claims_accepted_as_proof": False,
            "router_owned_check_proof_path": project_relative(project_root, proof_path),
            "audit": audit,
            "passed": bool(audit.get("passed")),
            "blockers": audit.get("blockers") or [],
            "reviewed_at": utc_now(),
        },
    )
    _write_router_owned_check_proof(
        project_root,
        run_root,
        check_name="current_node_packet_runtime_audit",
        audit_path=audit_path,
        source_kind="packet_runtime_hash",
        evidence_paths=[
            packet_envelope_path,
            result_envelope_path,
            packet_body_path,
            result_body_path,
        ],
    )
    _validate_router_owned_check_proof(
        project_root,
        run_root,
        check_name="current_node_packet_runtime_audit",
        audit_path=audit_path,
    )
    if not audit.get("passed"):
        raise RouterError(f"reviewer pass rejected by packet audit: {audit.get('blockers')}")


def _route_payload_from_reviewed_draft(project_root: Path, run_root: Path, payload: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    draft_path = _current_route_draft_path(run_root)
    draft = read_json(draft_path)
    supplied_route = payload.get("route")
    route_payload = dict(supplied_route) if isinstance(supplied_route, dict) else dict(draft)
    route_payload["schema_version"] = "flowpilot.route.v1"
    route_payload["activated_from_draft_path"] = project_relative(project_root, draft_path)
    route_payload["activated_from_draft_hash"] = hashlib.sha256(draft_path.read_bytes()).hexdigest()
    route_payload["reviewed_route_activation_source"] = "flow.draft.json"
    if not route_payload.get("nodes"):
        raise RouterError("reviewed route activation requires non-empty reviewed route draft nodes")
    return route_payload, draft_path


def _write_route_activation(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    route_payload, draft_path = _route_payload_from_reviewed_draft(project_root, run_root, payload)
    route_id = str(payload.get("route_id") or route_payload.get("route_id") or draft_path.parent.name or "route-001")
    route_payload["route_id"] = route_id
    route_version = int(payload.get("route_version") or route_payload.get("route_version") or 1)
    route_payload["route_version"] = route_version
    route_nodes = _iter_route_nodes(route_payload)
    first_node = route_nodes[0] if route_nodes else {}
    active_node_id = str(
        payload.get("active_node_id")
        or payload.get("node_id")
        or route_payload.get("active_node_id")
        or first_node.get("node_id")
        or first_node.get("id")
        or "node-001"
    )
    route_root = run_root / "routes" / route_id
    route_payload["active_node_id"] = active_node_id
    route_payload["source"] = "pm_activates_reviewed_route"
    route_payload["updated_at"] = utc_now()
    write_json(route_root / "flow.json", route_payload)
    frontier = {
        "schema_version": "flowpilot.execution_frontier.v1",
        "run_id": run_state["run_id"],
        "status": "current_node_loop",
        "active_route_id": route_id,
        "active_node_id": active_node_id,
        "route_version": route_version,
        "updated_at": utc_now(),
        "source": "pm_activates_reviewed_route",
    }
    write_json(run_root / "execution_frontier.json", frontier)
    _write_display_plan_from_route(
        project_root,
        run_root,
        run_state,
        route_id=route_id,
        route_version=route_version,
        route_payload=route_payload,
        active_node_id=active_node_id,
        source_event="pm_activates_reviewed_route",
    )


def _write_route_mutation(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    prior_review = _require_pm_prior_path_context(project_root, run_root, payload, purpose="route mutation")
    frontier = read_json_if_exists(run_root / "execution_frontier.json")
    route_id = str(payload.get("route_id") or frontier.get("active_route_id") or "route-001")
    active_node_id = str(payload.get("active_node_id") or payload.get("repair_node_id") or frontier.get("active_node_id") or "node-001")
    route_version = int(payload.get("route_version") or int(frontier.get("route_version") or 1) + 1)
    superseded_nodes = [str(item) for item in (payload.get("superseded_nodes") or [])]
    stale_evidence = [str(item) for item in (payload.get("stale_evidence") or [])]
    mutation_record = {
        "schema_version": "flowpilot.route_mutation.v1",
        "run_id": run_state["run_id"],
        "route_id": route_id,
        "route_version": route_version,
        "active_node_id": active_node_id,
        "reason": payload.get("reason") or "reviewer_block",
        "stale_evidence": stale_evidence,
        "superseded_nodes": superseded_nodes,
        "prior_path_context_review": prior_review,
        "repair_restart_policy": {
            "same_scope_replay_rerun_required": True,
            "final_ledger_rebuild_required": True,
            "terminal_replay_restart_default": "restart_from_delivered_product",
        },
        "recorded_at": utc_now(),
        "recorded_by": "project_manager",
    }
    mutation_path = run_root / "routes" / route_id / "mutations.json"
    mutations = read_json_if_exists(mutation_path) or {"schema_version": "flowpilot.route_mutations.v1", "items": []}
    mutations.setdefault("items", []).append(mutation_record)
    mutations["updated_at"] = utc_now()
    write_json(mutation_path, mutations)
    route_path = run_root / "routes" / route_id / "flow.json"
    route = read_json_if_exists(route_path)
    route.setdefault("schema_version", "flowpilot.route.v1")
    route.setdefault("route_id", route_id)
    route["route_version"] = route_version
    nodes = route.setdefault("nodes", [])
    for node in nodes:
        if isinstance(node, dict) and str(node.get("node_id")) in superseded_nodes:
            node["status"] = "superseded"
            node["superseded_by"] = active_node_id
            node["superseded_at"] = utc_now()
    if not any(isinstance(node, dict) and str(node.get("node_id")) == active_node_id for node in nodes):
        nodes.append(
            {
                "node_id": active_node_id,
                "status": "active",
                "title": str(payload.get("repair_node_title") or "Repair node"),
                "created_by_mutation": True,
                "mutation_reason": mutation_record["reason"],
            }
        )
    route["active_node_id"] = active_node_id
    route["updated_at"] = utc_now()
    write_json(route_path, route)
    stale_ledger_path = run_root / "evidence" / "stale_evidence_ledger.json"
    stale_ledger = read_json_if_exists(stale_ledger_path) or {"schema_version": "flowpilot.stale_evidence_ledger.v1", "items": []}
    for evidence_id in stale_evidence:
        stale_ledger.setdefault("items", []).append(
            {
                "evidence_id": evidence_id,
                "status": "stale",
                "reason": mutation_record["reason"],
                "route_version": route_version,
                "recorded_at": utc_now(),
            }
        )
    stale_ledger["updated_at"] = utc_now()
    write_json(stale_ledger_path, stale_ledger)
    frontier.update(
        {
            "schema_version": "flowpilot.execution_frontier.v1",
            "run_id": run_state["run_id"],
            "status": "route_mutated_repair_pending",
            "active_route_id": route_id,
            "active_node_id": active_node_id,
            "route_version": route_version,
            "latest_mutation_path": project_relative(project_root, mutation_path),
            "updated_at": utc_now(),
            "source": "pm_mutates_route_after_review_block",
        }
    )
    write_json(run_root / "execution_frontier.json", frontier)
    _write_display_plan_from_route(
        project_root,
        run_root,
        run_state,
        route_id=route_id,
        route_version=route_version,
        route_payload=route,
        active_node_id=active_node_id,
        source_event="pm_mutates_route_after_review_block",
    )
    _reset_flags(run_state, CURRENT_NODE_CYCLE_FLAGS + ROUTE_COMPLETION_FLAGS)


def _write_evidence_quality_package(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    prior_review = _require_pm_prior_path_context(project_root, run_root, payload, purpose="evidence quality package")
    if payload.get("pm_owned", True) is not True:
        raise RouterError("evidence quality package must be PM-owned")
    if not run_state["flags"].get("node_completed_by_pm"):
        raise RouterError("evidence quality package requires PM-completed current node")
    frontier = _active_frontier(run_root)
    node_completion_ledger_path = _active_node_completion_ledger_path(run_root, frontier)
    if not run_state["flags"].get("node_completion_ledger_updated") or not node_completion_ledger_path.exists():
        raise RouterError("evidence quality package requires node completion ledger")
    evidence_items = payload.get("evidence_items")
    if evidence_items is None:
        evidence_items = []
    if not isinstance(evidence_items, list):
        raise RouterError("evidence_items must be a list")
    generated_resources = payload.get("generated_resources")
    if generated_resources is None:
        generated_resources = []
    if not isinstance(generated_resources, list):
        raise RouterError("generated_resources must be a list")
    ui_visual_required = bool(payload.get("ui_visual_evidence_required"))
    ui_visual_evidence = payload.get("ui_visual_evidence") if isinstance(payload.get("ui_visual_evidence"), dict) else {}
    if ui_visual_required:
        screenshot_paths = ui_visual_evidence.get("screenshot_paths")
        if not isinstance(screenshot_paths, list) or not screenshot_paths:
            raise RouterError("required UI/visual evidence needs screenshot_paths")
        if ui_visual_evidence.get("old_assets_reused") is True:
            raise RouterError("UI/visual evidence cannot reuse old assets as current evidence")
    unresolved_evidence = [item for item in evidence_items if isinstance(item, dict) and item.get("status") in {"unresolved", "blocked"}]
    stale_evidence = [item for item in evidence_items if isinstance(item, dict) and item.get("status") == "stale"]
    pending_resources = [
        item
        for item in generated_resources
        if isinstance(item, dict) and item.get("disposition") in {None, "", "pending", "unresolved"}
    ]
    if unresolved_evidence or stale_evidence:
        raise RouterError("evidence quality package cannot contain unresolved or stale current evidence")
    if pending_resources:
        raise RouterError("generated resources must have terminal dispositions")
    evidence_ledger_path = run_root / "evidence" / "evidence_ledger.json"
    generated_resource_ledger_path = run_root / "generated_resource_ledger.json"
    quality_package_path = run_root / "quality" / "quality_package.json"
    write_json(
        evidence_ledger_path,
        {
            "schema_version": "flowpilot.evidence_ledger.v1",
            "run_id": run_state["run_id"],
            "pm_owned": True,
            "items": evidence_items,
            "current_evidence_count": len(evidence_items),
            "stale_count": 0,
            "unresolved_count": 0,
            "controller_origin_evidence_allowed": False,
            "completion_report_only_allowed": False,
            "updated_at": utc_now(),
        },
    )
    write_json(
        generated_resource_ledger_path,
        {
            "schema_version": "flowpilot.generated_resource_ledger.v1",
            "run_id": run_state["run_id"],
            "pm_owned": True,
            "resources": generated_resources,
            "resource_count": len(generated_resources),
            "pending_resource_count": 0,
            "unresolved_resource_count": 0,
            "old_visual_assets_may_close_current_gate": False,
            "all_resources_have_terminal_disposition": True,
            "updated_at": utc_now(),
        },
    )
    write_json(
        quality_package_path,
        {
            "schema_version": "flowpilot.quality_package.v1",
            "run_id": run_state["run_id"],
            "pm_owned": True,
            "source_paths": {
                "evidence_ledger": project_relative(project_root, evidence_ledger_path),
                "generated_resource_ledger": project_relative(project_root, generated_resource_ledger_path),
                "execution_frontier": project_relative(project_root, run_root / "execution_frontier.json"),
                "node_completion_ledger": project_relative(project_root, node_completion_ledger_path),
                "pm_prior_path_context": project_relative(project_root, _pm_prior_path_context_path(run_root)),
                "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
                "packet_chain_audit": project_relative(project_root, run_root / "packet_chain_audit.json")
                if (run_root / "packet_chain_audit.json").exists()
                else None,
            },
            "prior_path_context_review": prior_review,
            "quality_checks": {
                "human_like_review_required": True,
                "completion_report_only_allowed": False,
                "rough_or_placeholder_completion_forbidden": True,
                "unresolved_evidence_count_zero": True,
                "unresolved_resource_count_zero": True,
            },
            "ui_visual_evidence": {
                "required": ui_visual_required,
                "status": "provided" if ui_visual_required else "not_applicable",
                "old_assets_reused": bool(ui_visual_evidence.get("old_assets_reused")),
                "screenshot_paths": ui_visual_evidence.get("screenshot_paths") or [],
                "visual_review_notes_path": ui_visual_evidence.get("visual_review_notes_path"),
            },
            "written_at": utc_now(),
        },
    )


def _root_requirement_ids(contract: dict[str, Any]) -> list[str]:
    ids = []
    for item in contract.get("root_requirements") or []:
        if isinstance(item, dict) and item.get("requirement_id"):
            ids.append(str(item["requirement_id"]))
    return ids


def _validated_root_replay(payload: dict[str, Any], required_ids: list[str]) -> list[dict[str, Any]]:
    replay = payload.get("root_contract_replay")
    if not isinstance(replay, list) or not replay:
        raise RouterError("final ledger requires root_contract_replay for every frozen root requirement")
    by_id = {str(item.get("requirement_id")): item for item in replay if isinstance(item, dict)}
    missing = [req_id for req_id in required_ids if req_id not in by_id]
    if missing:
        raise RouterError(f"final ledger missing root contract replay for: {', '.join(missing)}")
    failed = [
        req_id
        for req_id in required_ids
        if by_id[req_id].get("status") != "approved" or not by_id[req_id].get("evidence_paths")
    ]
    if failed:
        raise RouterError(f"final ledger root contract replay not approved with evidence for: {', '.join(failed)}")
    return [by_id[req_id] for req_id in required_ids]


def _build_source_of_truth_final_entries(
    project_root: Path,
    run_root: Path,
    frontier: dict[str, Any],
    route: dict[str, Any],
    mutations: dict[str, Any],
    contract: dict[str, Any],
    root_replay: list[dict[str, Any]],
    child_manifest: dict[str, Any],
    evidence_ledger: dict[str, Any],
    generated_ledger: dict[str, Any],
) -> list[dict[str, Any]]:
    route_id = str(frontier["active_route_id"])
    route_version = int(frontier.get("route_version") or 0)
    entries: list[dict[str, Any]] = []
    for replay in root_replay:
        entries.append(
            {
                "entry_id": f"root_contract:{replay['requirement_id']}",
                "route_version": route_version,
                "gate_family": "root_acceptance",
                "required_approver": "human_like_reviewer",
                "status": "approved",
                "source_of_truth_paths": replay.get("evidence_paths") or [],
                "evidence_paths": replay.get("evidence_paths") or [],
            }
        )
    for node in _effective_route_nodes(route, mutations):
        node_id = str(node["node_id"])
        node_root = run_root / "routes" / route_id / "nodes" / node_id
        entries.append(
            {
                "entry_id": f"{route_id}:{node_id}",
                "route_version": route_version,
                "node_id": node_id,
                "gate_family": "route_node",
                "required_approver": "project_manager",
                "status": "approved" if node_id in (frontier.get("completed_nodes") or []) or node_id == frontier.get("active_node_id") else "pending_review",
                "source_of_truth_paths": [
                    project_relative(project_root, path)
                    for path in (
                        node_root / "node_acceptance_plan.json",
                        node_root / "reviews" / "node_acceptance_plan_review.json",
                        node_root / "node_completion_ledger.json",
                        node_root / "parent_backward_replay.json",
                        node_root / "pm_parent_segment_decision.json",
                    )
                    if path.exists()
                ],
            }
        )
        entries[-1]["evidence_paths"] = list(entries[-1]["source_of_truth_paths"])
    for item in mutations.get("items") or []:
        if not isinstance(item, dict):
            continue
        for node_id in item.get("superseded_nodes") or []:
            entries.append(
                {
                    "entry_id": f"superseded:{node_id}",
                    "route_version": item.get("route_version", route_version),
                    "node_id": str(node_id),
                    "gate_family": "superseded_node",
                    "required_approver": "project_manager",
                    "status": "superseded_explained",
                    "source_of_truth_paths": [project_relative(project_root, run_root / "routes" / route_id / "mutations.json")],
                    "evidence_paths": [project_relative(project_root, run_root / "routes" / route_id / "mutations.json")],
                }
            )
    for skill in child_manifest.get("selected_skills") or []:
        if not isinstance(skill, dict):
            continue
        skill_name = str(skill.get("skill_name") or skill.get("name") or "child_skill")
        for gate in skill.get("gates") or []:
            if not isinstance(gate, dict):
                continue
            entries.append(
                {
                    "entry_id": f"child_skill:{skill_name}:{gate.get('gate_id') or len(entries)}",
                    "route_version": route_version,
                    "gate_family": "child_skill_gate",
                    "required_approver": gate.get("required_approver") or "project_manager",
                    "status": "approved",
                    "source_of_truth_paths": [project_relative(project_root, run_root / "child_skill_gate_manifest.json")],
                    "evidence_paths": [project_relative(project_root, run_root / "child_skill_gate_manifest.json")],
                }
            )
    for item in evidence_ledger.get("items") or []:
        if isinstance(item, dict) and item.get("evidence_id"):
            entries.append(
                {
                    "entry_id": f"evidence:{item['evidence_id']}",
                    "route_version": route_version,
                    "gate_family": "evidence_integrity",
                    "required_approver": "human_like_reviewer",
                    "status": item.get("status") or "current",
                    "source_of_truth_paths": [item.get("path")] if item.get("path") else [],
                    "evidence_paths": [item.get("path")] if item.get("path") else [],
                }
            )
    for resource in generated_ledger.get("resources") or []:
        if isinstance(resource, dict) and (resource.get("resource_id") or resource.get("path")):
            entries.append(
                {
                    "entry_id": f"generated_resource:{resource.get('resource_id') or resource.get('path')}",
                    "route_version": route_version,
                    "gate_family": "generated_resource_lineage",
                    "required_approver": "project_manager",
                    "status": resource.get("disposition") or "resolved",
                    "source_of_truth_paths": [resource.get("path")] if resource.get("path") else [],
                    "evidence_paths": [resource.get("path")] if resource.get("path") else [],
                }
            )
    if not entries:
        raise RouterError("final ledger source-of-truth scan produced no entries")
    return entries


def _write_final_route_wide_ledger(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    prior_review = _require_pm_prior_path_context(project_root, run_root, payload, purpose="final route-wide ledger")
    if payload.get("pm_owned", True) is not True:
        raise RouterError("final route-wide ledger must be PM-owned")
    required_paths = [
        run_root / "evidence" / "evidence_ledger.json",
        run_root / "generated_resource_ledger.json",
        run_root / "quality" / "quality_package.json",
        run_root / "reviews" / "evidence_quality_review.json",
        run_root / "execution_frontier.json",
        run_root / "root_acceptance_contract.json",
        run_root / "child_skill_gate_manifest.json",
    ]
    missing = [project_relative(project_root, path) for path in required_paths if not path.exists()]
    if missing:
        raise RouterError(f"final ledger requires evidence quality package and review: {', '.join(missing)}")
    if not run_state["flags"].get("evidence_quality_reviewer_passed"):
        raise RouterError("final ledger requires reviewer-passed evidence quality package")
    evidence_ledger = read_json(run_root / "evidence" / "evidence_ledger.json")
    generated_ledger = read_json(run_root / "generated_resource_ledger.json")
    quality_package = read_json(run_root / "quality" / "quality_package.json")
    contract = read_json(run_root / "root_acceptance_contract.json")
    if contract.get("status") != "frozen":
        raise RouterError("final ledger requires frozen root acceptance contract")
    child_manifest = read_json(run_root / "child_skill_gate_manifest.json")
    frontier = _active_frontier(run_root)
    route_id = str(frontier["active_route_id"])
    route_version = int(frontier.get("route_version") or 0)
    node_completion_ledger_path = _active_node_completion_ledger_path(run_root, frontier)
    if not run_state["flags"].get("node_completion_ledger_updated") or not node_completion_ledger_path.exists():
        raise RouterError("final ledger requires node completion ledger")
    evidence_unresolved_count = int(evidence_ledger.get("unresolved_count", 0) or 0)
    payload_unresolved_count = int(payload.get("unresolved_count", 0) or 0)
    unresolved_count = max(evidence_unresolved_count, payload_unresolved_count)
    unresolved_resource_count = int(payload.get("unresolved_resource_count", generated_ledger.get("unresolved_resource_count", 0) or 0))
    pending_resource_count = int(generated_ledger.get("pending_resource_count", 0) or 0)
    unresolved_residual_risk_count = int(payload.get("unresolved_residual_risk_count", 0))
    stale_count = int(payload.get("stale_count", evidence_ledger.get("stale_count", 0) or 0))
    if unresolved_count != 0:
        raise RouterError("final ledger requires unresolved_count=0")
    if unresolved_resource_count != 0:
        raise RouterError("final ledger requires unresolved_resource_count=0")
    if pending_resource_count != 0:
        raise RouterError("final ledger requires generated resources to have terminal dispositions")
    if unresolved_residual_risk_count != 0:
        raise RouterError("final ledger requires unresolved_residual_risk_count=0")
    if stale_count != 0:
        raise RouterError("final ledger cannot include stale current evidence")
    if quality_package.get("quality_checks", {}).get("completion_report_only_allowed") is not False:
        raise RouterError("final ledger forbids completion report-only closure")
    route_path = _active_route_path(run_root, frontier)
    route = read_json(route_path)
    mutations = read_json_if_exists(run_root / "routes" / route_id / "mutations.json")
    root_replay = _validated_root_replay(payload, _root_requirement_ids(contract))
    entries = _build_source_of_truth_final_entries(
        project_root,
        run_root,
        frontier,
        route,
        mutations,
        contract,
        root_replay,
        child_manifest,
        evidence_ledger,
        generated_ledger,
    )
    bad_entry_statuses = [
        str(entry.get("entry_id"))
        for entry in entries
        if entry.get("status") in {"pending", "pending_review", "blocked", "unresolved", "stale"}
    ]
    if bad_entry_statuses:
        raise RouterError(f"final ledger has unresolved source-of-truth entries: {', '.join(bad_entry_statuses)}")
    final_ledger_path = run_root / "final_route_wide_gate_ledger.json"
    terminal_map_path = run_root / "terminal_human_backward_replay_map.json"
    terminal_segments = [
        {
            "segment_id": str(entry["entry_id"]),
            "source_entry_id": str(entry["entry_id"]),
            "gate_family": entry.get("gate_family"),
            "status": "not_reviewed",
            "requires_pm_segment_decision": True,
        }
        for entry in entries
    ]
    gate_decision_ledger_path = run_root / "gate_decisions" / "gate_decision_ledger.json"
    gate_decisions = list(run_state.get("gate_decisions") or [])
    ledger = {
        "schema_version": "flowpilot.final_route_wide_gate_ledger.v1",
        "run_id": run_state["run_id"],
        "pm_owned": True,
        "status": "clean",
        "built_from_route": route_id,
        "built_from_route_version": route_version,
        "built_at": utc_now(),
        "source_paths": {
            "execution_frontier": project_relative(project_root, run_root / "execution_frontier.json"),
            "active_flow": project_relative(project_root, route_path),
            "node_completion_ledger": project_relative(project_root, node_completion_ledger_path),
            "evidence_ledger": project_relative(project_root, run_root / "evidence" / "evidence_ledger.json"),
            "generated_resource_ledger": project_relative(project_root, run_root / "generated_resource_ledger.json"),
            "quality_package": project_relative(project_root, run_root / "quality" / "quality_package.json"),
            "root_acceptance_contract": project_relative(project_root, run_root / "root_acceptance_contract.json"),
            "child_skill_gate_manifest": project_relative(project_root, run_root / "child_skill_gate_manifest.json"),
            "route_mutations": project_relative(project_root, run_root / "routes" / route_id / "mutations.json")
            if (run_root / "routes" / route_id / "mutations.json").exists()
            else None,
            "pm_prior_path_context": project_relative(project_root, _pm_prior_path_context_path(run_root)),
            "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
            "gate_decision_ledger": project_relative(project_root, gate_decision_ledger_path)
            if gate_decision_ledger_path.exists()
            else None,
        },
        "prior_path_context_review": prior_review,
        "current_route_scanned": True,
        "effective_nodes_resolved": True,
        "gate_families": {
            "child_skill_gates_collected": True,
            "human_review_gates_collected": True,
            "parent_backward_replays_collected": True,
            "product_process_gates_collected": True,
            "generated_resource_lineage_collected": True,
            "final_completion_gates_collected": True,
            "gate_decisions_collected": True,
        },
        "evidence_integrity": {
            "generated_resource_lineage_resolved": True,
            "stale_evidence_checked": True,
            "superseded_nodes_explained": True,
            "standard_scenarios_replayed": bool(payload.get("standard_scenarios_replayed", True)),
            "residual_risk_triage_done": True,
            "unresolved_residual_risk_count_zero": True,
            "blocked_items_have_pm_repair_or_stop_decision": True,
        },
        "counts": {
            "effective_node_count": len(_effective_route_nodes(route, mutations)),
            "gate_count": len(entries),
            "stale_count": stale_count,
            "generated_resource_count": int(generated_ledger.get("resource_count", 0) or 0),
            "pending_resource_count": pending_resource_count,
            "unresolved_resource_count": unresolved_resource_count,
            "unresolved_residual_risk_count": unresolved_residual_risk_count,
            "unresolved_count": unresolved_count,
            "gate_decision_count": len(gate_decisions),
        },
        "entries": entries,
        "gate_decisions": gate_decisions,
        "root_contract_replay": root_replay,
        "frozen_contract_replay": {
            "status": "replayed",
            "root_acceptance_contract_path": project_relative(project_root, run_root / "root_acceptance_contract.json"),
            "standard_scenario_pack_path": project_relative(project_root, run_root / "standard_scenario_pack.json"),
            "requirement_count": len(root_replay),
            "standard_scenarios_replayed": bool(payload.get("standard_scenarios_replayed", True)),
        },
        "terminal_human_backward_replay": {
            "required": True,
            "status": "ready_for_reviewer",
            "review_map_path": project_relative(project_root, terminal_map_path),
            "report_only_allowed": False,
        },
        "completion_allowed": False,
    }
    write_json(final_ledger_path, ledger)
    write_json(
        terminal_map_path,
        {
            "schema_version": "flowpilot.terminal_human_backward_replay_map.v1",
            "run_id": run_state["run_id"],
            "route_id": route_id,
            "route_version": route_version,
            "pm_owned": True,
            "status": "ready_for_reviewer",
            "built_from_ledger_path": project_relative(project_root, final_ledger_path),
            "built_at": utc_now(),
            "replay_order": ["delivered_product", "root_acceptance", "parent_or_module_nodes", "leaf_nodes", "pm_segment_decisions", "repair_restart_policy"],
            "segments": terminal_segments,
            "coverage": {
                "effective_nodes_total": len(_effective_route_nodes(route, mutations)),
                "segments_total": len(terminal_segments),
                "segments_reviewed": 0,
                "effective_nodes_reviewed_by_human": 0,
                "root_acceptance_reviewed": False,
                "parent_nodes_reviewed": False,
                "leaf_nodes_reviewed": False,
                "every_effective_node_has_pm_segment_decision": False,
            },
            "repair_restart_policy": {
                "default_restart": "restart_from_delivered_product",
                "latest_repair_invalidates_affected_segments": True,
                "latest_repair_requires_ledger_rebuild": True,
                "latest_repair_requires_replay_rerun": True,
                "latest_repair_requires_pm_reapproval": True,
            },
            "completion_gate": {
                "reviewer_passed": False,
                "pm_segment_decisions_recorded": False,
                "repair_restart_policy_recorded": True,
                "unresolved_repair_findings": 0,
                "completion_allowed": False,
            },
        },
    )


def _write_terminal_backward_replay(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != "human_like_reviewer":
        raise RouterError("terminal backward replay must be reviewed_by_role=human_like_reviewer")
    if payload.get("passed") is not True:
        raise RouterError("terminal backward replay must explicitly pass")
    final_ledger_path = run_root / "final_route_wide_gate_ledger.json"
    terminal_map_path = run_root / "terminal_human_backward_replay_map.json"
    if not final_ledger_path.exists() or not terminal_map_path.exists():
        raise RouterError("terminal backward replay requires final ledger and PM replay map")
    final_ledger = read_json(final_ledger_path)
    if final_ledger.get("pm_owned") is not True or final_ledger.get("status") != "clean":
        raise RouterError("terminal replay requires a PM-owned clean final ledger")
    if final_ledger.get("counts", {}).get("unresolved_count") != 0:
        raise RouterError("terminal replay cannot pass unless final ledger unresolved_count is zero")
    terminal_map = read_json(terminal_map_path)
    if terminal_map.get("status") != "ready_for_reviewer":
        raise RouterError("terminal replay map must be ready_for_reviewer")
    segments = terminal_map.get("segments") if isinstance(terminal_map.get("segments"), list) else []
    required_segment_ids = [
        str(segment.get("segment_id"))
        for segment in segments
        if isinstance(segment, dict) and segment.get("segment_id")
    ]
    segment_reviews = payload.get("segment_reviews")
    if not isinstance(segment_reviews, list) or not segment_reviews:
        raise RouterError("terminal backward replay requires segment_reviews for every replay-map segment")
    reviews_by_id = {
        str(item.get("segment_id")): item
        for item in segment_reviews
        if isinstance(item, dict) and item.get("segment_id")
    }
    missing_segments = [segment_id for segment_id in required_segment_ids if segment_id not in reviews_by_id]
    if missing_segments:
        raise RouterError(f"terminal backward replay missing segment reviews: {', '.join(missing_segments)}")
    failed_segments = [
        segment_id
        for segment_id in required_segment_ids
        if reviews_by_id[segment_id].get("reviewed_by_role") != "human_like_reviewer"
        or reviews_by_id[segment_id].get("passed") is not True
        or reviews_by_id[segment_id].get("pm_segment_decision") != "continue"
    ]
    if failed_segments:
        raise RouterError(f"terminal replay segments require reviewer pass and PM continue: {', '.join(failed_segments)}")
    for segment in segments:
        if isinstance(segment, dict) and segment.get("segment_id"):
            review = reviews_by_id.get(str(segment["segment_id"]))
            if review:
                segment["status"] = "passed"
                segment["review"] = review
    terminal_map["status"] = "passed"
    terminal_map.setdefault("coverage", {})
    terminal_map["coverage"].update(
        {
            "effective_nodes_reviewed_by_human": int(terminal_map["coverage"].get("effective_nodes_total", 1) or 1),
            "segments_reviewed": len(required_segment_ids),
            "root_acceptance_reviewed": True,
            "parent_nodes_reviewed": True,
            "leaf_nodes_reviewed": True,
            "every_effective_node_has_pm_segment_decision": True,
        }
    )
    terminal_map.setdefault("completion_gate", {})
    terminal_map["completion_gate"].update(
        {
            "reviewer_passed": True,
            "pm_segment_decisions_recorded": True,
            "repair_restart_policy_recorded": True,
            "unresolved_repair_findings": 0,
            "completion_allowed": True,
        }
    )
    terminal_map["reviewed_by_role"] = "human_like_reviewer"
    terminal_map["reviewed_at"] = utc_now()
    write_json(terminal_map_path, terminal_map)
    final_ledger.setdefault("terminal_human_backward_replay", {})
    final_ledger["terminal_human_backward_replay"].update(
        {
            "status": "passed",
            "review_map_path": project_relative(project_root, terminal_map_path),
            "report_only_allowed": False,
            "segments_reviewed": len(required_segment_ids),
        }
    )
    final_ledger["completion_allowed"] = True
    final_ledger["terminal_replay_review_path"] = project_relative(project_root, run_root / "reviews" / "terminal_backward_replay.json")
    final_ledger["terminal_replay_reviewed_at"] = utc_now()
    write_json(final_ledger_path, final_ledger)
    write_json(
        run_root / "reviews" / "terminal_backward_replay.json",
        {
            "schema_version": "flowpilot.terminal_backward_replay_review.v1",
            "run_id": run_state["run_id"],
            "reviewed_by_role": "human_like_reviewer",
            "passed": True,
            "source_paths": {
                "final_route_wide_gate_ledger": project_relative(project_root, final_ledger_path),
                "terminal_human_backward_replay_map": project_relative(project_root, terminal_map_path),
            },
            "segment_reviews": segment_reviews,
            "report_only_allowed": False,
            "reviewed_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )
    _write_task_completion_projection(
        project_root,
        run_root,
        run_state,
        source_event="reviewer_final_backward_replay_passed",
    )


def _write_task_completion_projection(project_root: Path, run_root: Path, run_state: dict[str, Any], *, source_event: str) -> Path:
    final_ledger_path = run_root / "final_route_wide_gate_ledger.json"
    terminal_replay_path = run_root / "reviews" / "terminal_backward_replay.json"
    frontier_path = run_root / "execution_frontier.json"
    final_ledger = read_json(final_ledger_path)
    terminal_replay = read_json(terminal_replay_path)
    frontier = read_json(frontier_path)
    if final_ledger.get("completion_allowed") is not True:
        raise RouterError("task completion projection requires completion_allowed final ledger")
    if terminal_replay.get("passed") is not True:
        raise RouterError("task completion projection requires passed terminal backward replay")
    projection_path = _task_completion_projection_path(run_root)
    write_json(
        projection_path,
        {
            "schema_version": "flowpilot.task_completion_projection.v1",
            "run_id": run_state["run_id"],
            "task_status": "ready_for_pm_terminal_closure",
            "projection_owner": "controller",
            "completion_fact_owner": "project_manager",
            "source_event": source_event,
            "derived_from": "active_route_state_frontier_and_ledger",
            "controller_may_declare_completion": False,
            "ui_or_chat_is_display_only": True,
            "source_paths": {
                "execution_frontier": project_relative(project_root, frontier_path),
                "final_route_wide_gate_ledger": project_relative(project_root, final_ledger_path),
                "terminal_backward_replay": project_relative(project_root, terminal_replay_path),
                "latest_node_completion_ledger": str(frontier.get("latest_node_completion_ledger_path") or ""),
            },
            "published_at": utc_now(),
        },
    )
    run_state["flags"]["task_completion_projection_published"] = True
    return projection_path


def _write_terminal_closure_suite(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("approved_by_role", "project_manager") != "project_manager":
        raise RouterError("terminal closure must be approved_by_role=project_manager")
    decision = str(payload.get("decision") or "")
    if decision not in PM_TERMINAL_CLOSURE_DECISION_ALLOWED_VALUES:
        raise RouterError("terminal closure requires decision=approve_terminal_closure")
    prior_review = _require_pm_prior_path_context(project_root, run_root, payload, purpose="terminal closure")
    final_ledger_path = run_root / "final_route_wide_gate_ledger.json"
    terminal_replay_path = run_root / "reviews" / "terminal_backward_replay.json"
    task_projection_path = _task_completion_projection_path(run_root)
    continuation_path = _continuation_binding_path(run_root)
    required_paths = [
        final_ledger_path,
        terminal_replay_path,
        task_projection_path,
        run_root / "execution_frontier.json",
        run_root / "crew_ledger.json",
        continuation_path,
    ]
    missing = [project_relative(project_root, path) for path in required_paths if not path.exists()]
    if missing:
        raise RouterError(f"terminal closure missing lifecycle paths: {', '.join(missing)}")
    final_ledger = read_json(final_ledger_path)
    if final_ledger.get("completion_allowed") is not True:
        raise RouterError("terminal closure requires completion_allowed final ledger")
    replay = read_json(terminal_replay_path)
    if replay.get("passed") is not True:
        raise RouterError("terminal closure requires passed terminal backward replay")
    task_projection = read_json(task_projection_path)
    if task_projection.get("task_status") != "ready_for_pm_terminal_closure":
        raise RouterError("terminal closure requires task completion projection")
    if not _current_closure_state_clean(run_root):
        raise RouterError("terminal closure requires current clean evidence/resource/final ledgers")
    continuation = read_json(continuation_path)
    continuation["heartbeat_active"] = False
    continuation["closed_at"] = utc_now()
    continuation["closure_reason"] = "terminal_completion"
    write_json(continuation_path, continuation)
    closure = {
        "schema_version": "flowpilot.terminal_closure_suite.v1",
        "run_id": run_state["run_id"],
        "approved_by_role": "project_manager",
        "status": "closed",
        "closed_at": utc_now(),
        "source_paths": {
            "final_route_wide_gate_ledger": project_relative(project_root, final_ledger_path),
            "terminal_backward_replay": project_relative(project_root, terminal_replay_path),
            "task_completion_projection": project_relative(project_root, task_projection_path),
            "execution_frontier": project_relative(project_root, run_root / "execution_frontier.json"),
            "crew_ledger": project_relative(project_root, run_root / "crew_ledger.json"),
            "continuation_binding": project_relative(project_root, continuation_path),
            "pm_prior_path_context": project_relative(project_root, _pm_prior_path_context_path(run_root)),
            "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
        },
        "decision": decision,
        "prior_path_context_review": prior_review,
        "lifecycle": {
            "heartbeat_active": False,
            "manual_resume_notice_required": False,
            "terminal_completion_notice_recorded": True,
            "crew_memory_archived": True,
        },
        "final_report": payload.get("final_report") or {},
        **_role_output_envelope_record(payload),
    }
    write_json(run_root / "closure" / "terminal_closure_suite.json", closure)
    frontier = _active_frontier(run_root)
    frontier["status"] = "closed"
    frontier["closed_at"] = utc_now()
    frontier["source"] = "pm_approves_terminal_closure"
    write_json(run_root / "execution_frontier.json", frontier)


def _write_node_completion_ledger(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    frontier: dict[str, Any],
    *,
    completed_node_id: str,
    completed_nodes: list[str],
    next_node_id: str | None,
) -> Path:
    packet_envelope, packet_envelope_path = _current_node_packet_context(project_root, run_state)
    result_envelope, result_envelope_path = _current_node_result_context(project_root, run_state)
    audit_path = _active_node_root(run_root, frontier) / "reviews" / "current_node_packet_runtime_audit.json"
    ledger_path = _active_node_completion_ledger_path(run_root, frontier)
    write_json(
        ledger_path,
        {
            "schema_version": "flowpilot.node_completion_ledger.v1",
            "run_id": run_state["run_id"],
            "route_id": str(frontier["active_route_id"]),
            "route_version": int(frontier.get("route_version") or 0),
            "node_id": completed_node_id,
            "completed_by_role": "project_manager",
            "reviewer_result_passed": True,
            "worker_result_packet_id": str(result_envelope.get("packet_id") or ""),
            "worker_result_completed_by_role": str(result_envelope.get("completed_by_role") or ""),
            "current_node_packet_id": str(packet_envelope.get("packet_id") or ""),
            "completed_nodes_after_update": completed_nodes,
            "next_node_id": next_node_id,
            "flowpilot_completable_work_closed": True,
            "human_inspection_notes_belong_in_final_report": True,
            "source_paths": {
                "execution_frontier_before_update": project_relative(project_root, run_root / "execution_frontier.json"),
                "node_acceptance_plan": project_relative(project_root, _active_node_acceptance_plan_path(run_root, frontier)),
                "current_node_write_grant": project_relative(project_root, _active_node_write_grant_path(run_root, frontier)),
                "packet_envelope": project_relative(project_root, packet_envelope_path),
                "result_envelope": project_relative(project_root, result_envelope_path),
                "current_node_packet_runtime_audit": project_relative(project_root, audit_path),
            },
            "completed_at": utc_now(),
        },
    )
    run_state["flags"]["node_completion_ledger_updated"] = True
    return ledger_path


def _mark_frontier_node_completed(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    frontier = _active_frontier(run_root)
    active_node_id = str(payload.get("node_id") or frontier.get("active_node_id") or "node-001")
    if active_node_id != str(frontier.get("active_node_id")):
        raise RouterError("completed node_id must match active frontier")
    if _active_node_has_children(run_root, frontier):
        replay_path = _active_node_root(run_root, frontier) / "parent_backward_replay.json"
        decision_path = _active_node_root(run_root, frontier) / "pm_parent_segment_decision.json"
        missing = [project_relative(project_root, path) for path in (replay_path, decision_path) if not path.exists()]
        if missing:
            raise RouterError(f"parent node completion requires backward replay and PM segment decision: {', '.join(missing)}")
        if not run_state["flags"].get("parent_backward_replay_passed"):
            raise RouterError("parent node completion requires reviewer-passed parent backward replay")
        if not run_state["flags"].get("parent_segment_decision_recorded"):
            raise RouterError("parent node completion requires PM parent segment decision")
        decision = read_json(decision_path)
        if decision.get("decision") != "continue":
            raise RouterError("parent node completion requires PM parent segment decision=continue")
    completed = list(frontier.get("completed_nodes") or [])
    if active_node_id not in completed:
        completed.append(active_node_id)
    route = read_json_if_exists(_active_route_path(run_root, frontier))
    mutations = read_json_if_exists(run_root / "routes" / str(frontier["active_route_id"]) / "mutations.json")
    next_node_id = _next_effective_node_id(route, mutations, completed, active_node_id)
    completion_ledger_path = _write_node_completion_ledger(
        project_root,
        run_root,
        run_state,
        frontier,
        completed_node_id=active_node_id,
        completed_nodes=completed,
        next_node_id=next_node_id,
    )
    frontier.update(
        {
            "schema_version": "flowpilot.execution_frontier.v1",
            "run_id": run_state["run_id"],
            "status": "current_node_loop" if next_node_id else "node_completed_by_pm",
            "active_node_id": next_node_id or active_node_id,
            "completed_nodes": completed,
            "latest_node_completion_ledger_path": project_relative(project_root, completion_ledger_path),
            "updated_at": utc_now(),
            "source": "pm_completes_current_node_from_reviewed_result",
        }
    )
    write_json(run_root / "execution_frontier.json", frontier)
    if next_node_id:
        _reset_flags(run_state, CURRENT_NODE_CYCLE_FLAGS)
    if route:
        _write_display_plan_from_route(
            project_root,
            run_root,
            run_state,
            route_id=str(frontier["active_route_id"]),
            route_version=int(frontier.get("route_version") or 0),
            route_payload=route,
            active_node_id=next_node_id,
            source_event="pm_completes_current_node_from_reviewed_result",
        )


def apply_bootloader_action(project_root: Path, action_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    state = load_bootstrap_state(project_root, create_if_missing=False)
    pending = _ensure_pending(state, action_type)
    payload = payload or {}
    result_extra: dict[str, Any] = {}

    if action_type == "load_router":
        _set_boot_flag(project_root, state, "router_loaded", "bootloader_router_loaded")
        return {"ok": True, "applied": action_type}

    action_meta = next((item for item in BOOT_ACTIONS if item["action_type"] == action_type), None)
    if action_meta is None:
        raise RouterError(f"unknown bootloader action: {action_type}")
    flag = str(action_meta["flag"])

    if action_type == "ask_startup_questions":
        state["startup_state"] = "awaiting_answers_stopped"
        state["flags"]["startup_state_written_awaiting_answers"] = True
        state["flags"]["dialog_stopped_for_answers"] = True
    elif action_type == "write_startup_awaiting_answers_state":
        state["startup_state"] = "awaiting_answers"
    elif action_type == "stop_for_startup_answers":
        state["startup_state"] = "awaiting_answers_stopped"
    elif action_type == "record_startup_answers":
        startup_answers = _validate_startup_answers(payload)
        state["startup_answers"] = startup_answers
        interpretation = _validate_startup_answer_interpretation(payload, startup_answers)
        if interpretation:
            state["startup_answer_interpretation"] = interpretation
        else:
            state["startup_answer_interpretation"] = None
        state["startup_state"] = "answers_complete"
    elif action_type == "emit_startup_banner":
        banner = _startup_banner_display()
        confirmation = _display_confirmation_for_action(payload, pending)
        banner["dialog_display_confirmation"] = confirmation
        state["startup_banner_path"] = banner["display_path"]
        state["startup_banner_display"] = banner
        state["startup_banner_dialog_display_confirmation"] = confirmation
        result_extra.update(banner)
    elif action_type == "create_run_shell":
        run_id = str(payload.get("run_id") or state.get("run_id") or _create_run_id())
        run_root = project_root / ".flowpilot" / "runs" / run_id
        run_root.mkdir(parents=True, exist_ok=True)
        state["run_id"] = run_id
        state["run_root"] = project_relative(project_root, run_root)
        write_json(
            run_root / "run.json",
            {
                "schema_version": "flowpilot.run.v1",
                "run_id": run_id,
                "created_at": utc_now(),
                "startup_model": "prompt_isolated_router",
                "legacy_backup_required": True,
            },
        )
    elif action_type == "write_current_pointer":
        if not state.get("run_id") or not state.get("run_root"):
            raise RouterError("cannot write current pointer before run shell exists")
        write_json(
            project_root / ".flowpilot" / "current.json",
            {
                "schema_version": "flowpilot.current.v1",
                "current_run_id": state["run_id"],
                "current_run_root": state["run_root"],
                "startup_bootstrap_path": project_relative(project_root, bootstrap_state_path(project_root, state)),
                "status": "running",
                "updated_at": utc_now(),
            },
        )
    elif action_type == "update_run_index":
        if not state.get("run_id") or not state.get("run_root"):
            raise RouterError("cannot update index before run shell exists")
        index_path = project_root / ".flowpilot" / "index.json"
        index = read_json_if_exists(index_path) or {"schema_version": "flowpilot.index.v1", "runs": []}
        runs = index.setdefault("runs", [])
        if not any(isinstance(item, dict) and item.get("run_id") == state["run_id"] for item in runs):
            runs.append({"run_id": state["run_id"], "run_root": state["run_root"], "created_at": utc_now(), "status": "running"})
        index["current_run_id"] = state["run_id"]
        index["updated_at"] = utc_now()
        write_json(index_path, index)
    elif action_type == "copy_runtime_kit":
        run_root = project_root / str(state["run_root"])
        source = runtime_kit_source()
        target = run_root / "runtime_kit"
        try:
            target.resolve().relative_to(run_root.resolve())
        except ValueError as exc:
            raise RouterError(f"runtime kit target outside run root: {target}") from exc
        if target.name != "runtime_kit":
            raise RouterError(f"refusing to replace unexpected runtime kit target: {target}")
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"))
    elif action_type == "fill_runtime_placeholders":
        run_root = project_root / str(state["run_root"])
        interpretation = state.get("startup_answer_interpretation") if isinstance(state.get("startup_answer_interpretation"), dict) else None
        interpretation_path = run_root / "startup_answer_interpretation.json"
        if interpretation:
            write_json(interpretation_path, interpretation)
        write_json(
            run_root / "startup_answers.json",
            {
                "schema_version": "flowpilot.startup_answers.v1",
                "run_id": state["run_id"],
                "answers": state.get("startup_answers") or {},
                "startup_answer_interpretation_path": project_relative(project_root, interpretation_path) if interpretation else None,
                "recorded_at": utc_now(),
            },
        )
    elif action_type == "initialize_mailbox":
        run_root = project_root / str(state["run_root"])
        for rel in ("mailbox/system_cards", "mailbox/inbox", "mailbox/outbox", "packets"):
            (run_root / rel).mkdir(parents=True, exist_ok=True)
        write_json(run_root / "packet_ledger.json", _create_empty_packet_ledger(project_root, str(state["run_id"]), run_root))
        write_json(run_root / "prompt_delivery_ledger.json", {"schema_version": "flowpilot.prompt_delivery_ledger.v1", "run_id": state["run_id"], "deliveries": []})
    elif action_type == "record_user_request":
        run_root = project_root / str(state["run_root"])
        user_request = _validate_user_request(payload)
        user_request_record = {
            "schema_version": "flowpilot.user_request.v1",
            "run_id": state["run_id"],
            "user_request": user_request,
            "recorded_at": utc_now(),
        }
        write_json(run_root / "user_request.json", user_request_record)
        state["user_request"] = user_request
        state["user_request_path"] = project_relative(project_root, run_root / "user_request.json")
    elif action_type == "write_user_intake":
        run_root = project_root / str(state["run_root"])
        user_request = state.get("user_request")
        if not isinstance(user_request, dict):
            raise RouterError("cannot write user_intake before record_user_request")
        user_intake = packet_runtime.create_user_intake_packet(
            project_root,
            run_id=str(state["run_id"]),
            packet_id="user_intake",
            node_id="startup",
            body_text=json.dumps(
                {
                    "user_request": user_request,
                    "user_request_path": state.get("user_request_path"),
                    "startup_answers": state.get("startup_answers") or {},
                    "startup_answers_path": project_relative(project_root, run_root / "startup_answers.json"),
                    "startup_answer_interpretation_path": project_relative(project_root, run_root / "startup_answer_interpretation.json")
                    if isinstance(state.get("startup_answer_interpretation"), dict)
                    else None,
                },
                indent=2,
                sort_keys=True,
            ),
            startup_options=state.get("startup_answers") or {},
        )
        write_json(run_root / "mailbox" / "outbox" / "user_intake.json", user_intake)
    elif action_type == "start_role_slots":
        run_root = project_root / str(state["run_root"])
        role_slots = _normalize_role_agent_records(state, payload)
        background_mode = (state.get("startup_answers") or {}).get("background_agents")
        write_json(
            run_root / "crew_ledger.json",
            {
                "schema_version": "flowpilot.crew_ledger.v1",
                "run_id": state["run_id"],
                "background_agents_mode": background_mode,
                "role_slots": role_slots,
                "created_at": utc_now(),
            },
        )
        crew_memory_root = run_root / "crew_memory"
        crew_memory_root.mkdir(parents=True, exist_ok=True)
        for role in CREW_ROLE_KEYS:
            write_json(crew_memory_root / f"{role}.json", _create_empty_role_memory(str(state["run_id"]), role))
    elif action_type == "inject_role_core_prompts":
        run_root = project_root / str(state["run_root"])
        role_cards = {
            role: f"runtime_kit/cards/roles/{role}.md"
            for role in ROLE_CARD_KEYS
            if (run_root / "runtime_kit" / "cards" / "roles" / f"{role}.md").exists()
        }
        write_json(
            run_root / "role_core_prompt_delivery.json",
            {
                "schema_version": "flowpilot.role_core_prompt_delivery.v1",
                "run_id": state["run_id"],
                "source": "copied_runtime_kit",
                "role_cards": role_cards,
                "delivered_at": utc_now(),
            },
        )
    elif action_type == "load_controller_core":
        run_root = project_root / str(state["run_root"])
        run_state = new_run_state(str(state["run_id"]), str(state["run_root"]))
        write_json(run_root / "execution_frontier.json", _create_empty_execution_frontier(str(state["run_id"])))
        _write_initial_continuation_binding(project_root, run_root, run_state)
        _refresh_route_memory(project_root, run_root, run_state, trigger="load_controller_core")
        write_json(run_state_path(run_root), run_state)
    else:
        raise RouterError(f"unimplemented action: {action_type}")

    _set_boot_flag(project_root, state, flag, str(pending["label"]), {"action_type": action_type})
    result = {"ok": True, "applied": action_type, "postcondition": flag}
    result.update(result_extra)
    return result


def _next_resume_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    flags = run_state["flags"]
    if not flags.get("resume_reentry_requested"):
        return None
    if not flags.get("resume_state_loaded"):
        resume_next = _derive_resume_next_recipient_from_packet_ledger(run_root)
        return make_action(
            action_type="load_resume_state",
            actor="controller",
            label="controller_loads_resume_state_before_role_rehydration",
            summary="Controller loads current-run state, ledgers, frontier, visible plan, and crew memory before live role rehydration.",
            allowed_reads=[
                ".flowpilot/current.json",
                project_relative(project_root, run_state_path(run_root)),
                project_relative(project_root, run_root / "prompt_delivery_ledger.json"),
                project_relative(project_root, run_root / "packet_ledger.json"),
                project_relative(project_root, run_root / "execution_frontier.json"),
                project_relative(project_root, run_root / "crew_ledger.json"),
                project_relative(project_root, run_root / "crew_memory"),
                project_relative(project_root, _continuation_binding_path(run_root)),
                project_relative(project_root, _route_history_index_path(run_root)),
                project_relative(project_root, _pm_prior_path_context_path(run_root)),
                project_relative(project_root, _display_plan_path(run_root)),
            ],
            allowed_writes=[
                project_relative(project_root, run_root / "continuation" / "resume_reentry.json"),
                project_relative(project_root, run_state_path(run_root)),
                project_relative(project_root, _route_history_index_path(run_root)),
                project_relative(project_root, _pm_prior_path_context_path(run_root)),
            ],
            extra={
                "postcondition": "resume_state_loaded",
                "controller_visibility": "state_and_envelopes_only",
                "sealed_body_reads_allowed": False,
                "chat_history_progress_inference_allowed": False,
                "wake_recorded_to_router_required": True,
                "visible_plan_restore_required": True,
                "role_rehydration_required_before_pm_resume_decision": True,
                "resume_next_recipient_from_packet_ledger": resume_next,
            },
        )
    if not flags.get("resume_roles_restored"):
        return make_action(
            action_type="rehydrate_role_agents",
            actor="controller",
            label="host_rehydrates_resume_roles_before_pm_decision",
            summary="Host restores or replaces all six live FlowPilot roles from current-run memory before PM resume decision.",
            allowed_reads=[
                project_relative(project_root, run_root / "continuation" / "resume_reentry.json"),
                project_relative(project_root, run_root / "runtime_kit" / "cards" / "roles"),
                project_relative(project_root, run_root / "crew_memory"),
                project_relative(project_root, run_root / "crew_ledger.json"),
                project_relative(project_root, run_root / "execution_frontier.json"),
                project_relative(project_root, run_root / "packet_ledger.json"),
                project_relative(project_root, run_root / "prompt_delivery_ledger.json"),
                project_relative(project_root, _route_history_index_path(run_root)),
                project_relative(project_root, _pm_prior_path_context_path(run_root)),
                project_relative(project_root, _display_plan_path(run_root)),
            ],
            allowed_writes=[
                project_relative(project_root, run_root / "continuation" / "crew_rehydration_report.json"),
                project_relative(project_root, run_root / "crew_ledger.json"),
                project_relative(project_root, run_state_path(run_root)),
            ],
            extra={
                "postcondition": "resume_roles_restored",
                **_resume_role_rehydration_action_extra(project_root, run_root, run_state),
            },
        )
    return None


def _next_startup_heartbeat_binding_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    answers = _startup_answers_from_run(run_root)
    if not _scheduled_continuation_requested(answers):
        return None
    if run_state["flags"].get("continuation_binding_recorded") and _host_heartbeat_binding_ready(run_root, run_state):
        return None
    automation_id_hint = f"flowpilot-{run_state['run_id']}-heartbeat"
    automation_name = f"FlowPilot {run_state['run_id']} heartbeat"
    prompt = (
        f"Wake the active FlowPilot run {run_state['run_id']} in {project_root} by returning to the "
        "FlowPilot router loop. Every heartbeat wake must record heartbeat_or_manual_resume_requested "
        "before any wait or resume claim. Do not self-classify the work chain as alive from old "
        "crew or route state, and do not use wait_agent timeout as proof of liveness. The router must "
        "load the current resume state, restore the visible plan, and request six-role liveness "
        "rehydration before any PM resume decision. Do not read sealed packet/result/report bodies."
    )
    return make_action(
        action_type="create_heartbeat_automation",
        actor="controller",
        label="host_creates_startup_heartbeat_automation",
        summary="Create the one-minute Codex heartbeat for the current run, then record its host receipt before startup fact review.",
        allowed_reads=[
            ".flowpilot/current.json",
            project_relative(project_root, run_state_path(run_root)),
            project_relative(project_root, run_root / "startup_answers.json"),
            project_relative(project_root, _continuation_binding_path(run_root)),
        ],
        allowed_writes=[
            project_relative(project_root, _continuation_binding_path(run_root)),
            project_relative(project_root, run_state_path(run_root)),
        ],
        extra={
            "postcondition": "continuation_binding_recorded",
            "requires_host_automation": True,
            "host_tool": "codex_app.automation_update",
            "automation_update_request": {
                "mode": "create",
                "kind": "heartbeat",
                "destination": "thread",
                "name": automation_name,
                "prompt": prompt,
                "rrule": "FREQ=MINUTELY;INTERVAL=1",
                "status": "ACTIVE",
            },
            "expected_payload": {
                "route_heartbeat_interval_minutes": 1,
                "host_automation_id": automation_id_hint,
                "host_automation_verified": True,
                "host_automation_proof": {
                    "source_kind": "host_receipt",
                    "run_id": run_state["run_id"],
                    "host_automation_id": automation_id_hint,
                    "route_heartbeat_interval_minutes": 1,
                    "heartbeat_bound_to_current_run": True,
                },
            },
            "payload_contract": _heartbeat_payload_contract(run_state["run_id"], automation_id_hint),
            "proof_required_before_apply": True,
        },
    )


def _next_startup_mechanical_audit_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    flags = run_state["flags"]
    if not flags.get("controller_role_confirmed"):
        return None
    if flags.get("startup_mechanical_audit_written") and _startup_mechanical_audit_context(project_root, run_root, run_state):
        return None
    return make_action(
        action_type="write_startup_mechanical_audit",
        actor="controller",
        label="controller_writes_startup_mechanical_audit",
        summary="Write the router-owned startup mechanical audit and proof before delivering the reviewer startup fact-check card.",
        allowed_reads=[
            project_relative(project_root, run_root / "startup_answers.json"),
            project_relative(project_root, project_root / ".flowpilot" / "current.json"),
            project_relative(project_root, project_root / ".flowpilot" / "index.json"),
            project_relative(project_root, run_root / "crew_ledger.json"),
            project_relative(project_root, _continuation_binding_path(run_root)),
            project_relative(project_root, run_state_path(run_root)),
        ],
        allowed_writes=[
            project_relative(project_root, run_root / "startup" / "startup_mechanical_audit.json"),
            project_relative(project_root, run_root / "startup" / "startup_mechanical_audit.json.proof.json"),
            project_relative(project_root, run_state_path(run_root)),
        ],
        to_role="human_like_reviewer",
        extra={
            "postcondition": "startup_mechanical_audit_written",
            "reviewer_card_waiting_for_audit": "reviewer.startup_fact_check",
            "router_replacement_scope": "mechanical_only",
        },
    )


def _next_display_plan_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    sync_payload = _display_plan_sync_payload(project_root, run_root, run_state)
    last_sync = run_state.get("visible_plan_sync") if isinstance(run_state.get("visible_plan_sync"), dict) else {}
    route_sign_fresh = (
        not sync_payload.get("route_sign_display_required")
        or last_sync.get("route_sign_mermaid_sha256") == sync_payload.get("route_sign_mermaid_sha256")
    )
    if last_sync.get("projection_hash") == sync_payload["projection_hash"] and route_sign_fresh:
        return None
    allowed_writes = [
        project_relative(project_root, run_state_path(run_root)),
        project_relative(project_root, _route_state_snapshot_path(run_root)),
        project_relative(project_root, run_root / "display" / "user_dialog_display_ledger.json"),
    ]
    if not sync_payload["display_plan_exists"]:
        allowed_writes.append(project_relative(project_root, _display_plan_path(run_root)))
    if sync_payload.get("route_sign_display_required"):
        allowed_writes.extend(
            [
                project_relative(project_root, run_root / "diagrams" / "user-flow-diagram.mmd"),
                project_relative(project_root, run_root / "diagrams" / "user-flow-diagram.md"),
                project_relative(project_root, run_root / "diagrams" / "user-flow-diagram-display.json"),
            ]
        )
    allowed_reads = [
        project_relative(project_root, project_root / ".flowpilot" / "current.json"),
        project_relative(project_root, _display_plan_path(run_root)),
        project_relative(project_root, _route_state_snapshot_path(run_root)),
        project_relative(project_root, run_state_path(run_root)),
    ]
    for raw_path in (
        sync_payload.get("route_sign_source_frontier_path"),
        sync_payload.get("route_sign_source_route_path"),
    ):
        if isinstance(raw_path, str) and raw_path:
            path = Path(raw_path)
            read_path = path if path.is_absolute() else project_root / path
            try:
                rel_path = project_relative(project_root, read_path)
            except RouterError:
                continue
            if rel_path not in allowed_reads:
                allowed_reads.append(rel_path)
    return make_action(
        action_type="sync_display_plan",
        actor="controller",
        label="controller_syncs_display_plan",
        summary="Display the route map in the user dialog, then replace the host visible plan from the run display_plan.json or clear it to a waiting-for-PM placeholder.",
        allowed_reads=allowed_reads,
        allowed_writes=allowed_writes,
        extra={
            "postcondition": "visible_plan_synced",
            **sync_payload,
        },
    )


def _next_startup_display_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    flags = run_state["flags"]
    if not flags.get("controller_role_confirmed"):
        return None
    if flags.get("startup_display_status_written"):
        return None
    route_sign = _startup_route_sign_payload(project_root, write=False, mark_chat_displayed=False)
    answers = _startup_answers_from_run(run_root)
    requested_display_surface = str(answers.get("display_surface") or "chat")
    cockpit_requested = requested_display_surface == "cockpit"
    display_gate = _user_dialog_display_gate(
        {
            "display_text": route_sign["markdown"],
            "display_text_format": "markdown_mermaid",
            "display_required": True,
            "controller_must_display_text_before_apply": True,
            "generated_files_alone_satisfy_chat_display": False,
            "controller_display_rule": "Paste this exact startup route-sign display_text in the user dialog before applying write_display_surface_status; generated files alone do not satisfy display.",
        },
        display_kind="startup_route_sign",
        display_text=route_sign["markdown"],
    )
    return make_action(
        action_type="write_display_surface_status",
        actor="controller",
        label="controller_writes_startup_display_surface_status",
        summary="Display the startup FlowPilot Route Sign Mermaid in chat, then write startup display-surface status before reviewer startup fact review.",
        allowed_reads=[
            project_relative(project_root, run_root / "startup_answers.json"),
            project_relative(project_root, run_root / "execution_frontier.json"),
        ],
        allowed_writes=[
            project_relative(project_root, run_root / "display" / "display_surface.json"),
            project_relative(project_root, run_root / "diagrams" / "current_route_sign.md"),
            project_relative(project_root, run_root / "diagrams" / "user-flow-diagram.mmd"),
            project_relative(project_root, run_root / "diagrams" / "user-flow-diagram.md"),
            project_relative(project_root, run_root / "diagrams" / "user-flow-diagram-display.json"),
            project_relative(project_root, run_root / "display" / "user_dialog_display_ledger.json"),
            project_relative(project_root, run_state_path(run_root)),
        ],
        extra={
            "postcondition": "startup_display_status_written",
            **display_gate,
            "chat_display_required": route_sign["chat_display_required"],
            "route_sign_mermaid_sha256": route_sign["mermaid_sha256"],
            "requested_display_surface": requested_display_surface,
            "resolved_display_surface": "chat-fallback" if cockpit_requested else "chat-requested",
            "cockpit_probe_required_for_requested_cockpit": cockpit_requested,
            "reviewer_fallback_check_required_for_requested_cockpit": cockpit_requested,
            "fallback_is_display_only_not_product_ui_completion": True,
            "payload_contract": _display_surface_receipt_payload_contract(),
        },
    )


def _next_system_card_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    flags = run_state["flags"]
    manifest = load_manifest_from_run(run_root)
    resume_waiting_for_pm = (
        bool(flags.get("resume_reentry_requested"))
        and bool(flags.get("resume_state_loaded"))
        and bool(flags.get("resume_roles_restored"))
        and not bool(flags.get("pm_resume_recovery_decision_returned"))
    )
    resume_card_ids = {"controller.resume_reentry", "pm.crew_rehydration_freshness", "pm.resume_decision"}
    for entry in SYSTEM_CARD_SEQUENCE:
        if resume_waiting_for_pm and entry["card_id"] not in resume_card_ids:
            continue
        if flags.get(entry["flag"]):
            continue
        required_flag = entry.get("requires_flag")
        if required_flag and not flags.get(required_flag):
            continue
        required_any = entry.get("requires_any_flag")
        if required_any and not any(flags.get(flag) for flag in required_any):
            continue
        if entry.get("requires_active_node_children") and not _active_node_has_children(run_root, _active_frontier(run_root)):
            continue
        to_role = _system_card_to_role(run_root, entry)
        if not run_state.get("manifest_check_requested"):
            return make_action(
                action_type="check_prompt_manifest",
                actor="controller",
                label="controller_instructed_to_check_prompt_manifest",
                summary="Controller must check prompt manifest before delivering the next system card.",
                allowed_reads=[project_relative(project_root, run_root / "runtime_kit" / "manifest.json")],
                allowed_writes=[project_relative(project_root, run_state_path(run_root))],
                extra={"next_card_id": entry["card_id"], "to_role": to_role},
            )
        card = manifest_card(manifest, entry["card_id"])
        delivery_extra = {"postcondition": entry["flag"]}
        delivery_extra.update(_pm_context_action_extra(project_root, run_root, entry))
        pm_decision_contract = _pm_decision_payload_contract_for_card(project_root, run_root, entry["card_id"])
        if pm_decision_contract is not None:
            delivery_extra["payload_contract"] = pm_decision_contract
        if entry["card_id"] == "reviewer.startup_fact_check":
            delivery_extra.update(_startup_mechanical_audit_action_extra(project_root, run_root, run_state))
        resolved_entry = {**entry, "to_role": to_role}
        delivery_context = _live_card_delivery_context(project_root, run_root, run_state, resolved_entry, card)
        delivery_extra["delivery_context"] = delivery_context
        allowed_reads = [project_relative(project_root, run_root / "runtime_kit" / str(card["path"]))]
        allowed_reads.extend(
            str(path)
            for path in delivery_context.get("source_paths", {}).values()
            if isinstance(path, str) and path
        )
        if entry["card_id"] == "reviewer.startup_fact_check":
            allowed_reads.extend(
                [
                    delivery_extra["startup_mechanical_audit_path"],
                    delivery_extra["router_owned_check_proof_path"],
                ]
            )
        return make_action(
            action_type="deliver_system_card",
            actor="controller",
            label=entry["label"],
            summary=f"Deliver system card {entry['card_id']} to {to_role}.",
            allowed_reads=allowed_reads,
            allowed_writes=[project_relative(project_root, run_root / "prompt_delivery_ledger.json")],
            card_id=entry["card_id"],
            to_role=to_role,
            extra=delivery_extra,
        )
    return None


def _system_card_to_role(run_root: Path, entry: dict[str, Any]) -> str:
    default_role = str(entry.get("to_role") or "")
    if entry.get("card_id") == "worker.research_report":
        index_path = _research_packet_index_path(run_root)
        if index_path.exists():
            try:
                index = _load_packet_index(index_path, label="research")
            except RouterError:
                return default_role
            packets = index.get("packets")
            if isinstance(packets, list) and packets:
                to_role = str(packets[0].get("to_role") or "").strip()
                if to_role:
                    return to_role
    return default_role


def _next_mail_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    flags = run_state["flags"]
    for entry in MAIL_SEQUENCE:
        if flags.get(entry["flag"]):
            continue
        if not run_state.get("ledger_check_requested"):
            return make_action(
                action_type="check_packet_ledger",
                actor="controller",
                label="controller_instructed_to_check_packet_ledger",
                summary="Controller must check packet ledger before delivering the next mail body.",
                allowed_reads=[project_relative(project_root, run_root / "packet_ledger.json")],
                allowed_writes=[project_relative(project_root, run_state_path(run_root))],
                extra={"next_mail_id": entry["mail_id"], "to_role": entry["to_role"]},
            )
        return make_action(
            action_type="deliver_mail",
            actor="controller",
            label=entry["label"],
            summary=f"Deliver mail {entry['mail_id']} to {entry['to_role']} through Controller.",
            allowed_reads=[project_relative(project_root, run_root / "mailbox" / "outbox" / f"{entry['mail_id']}.json")],
            allowed_writes=[project_relative(project_root, run_root / "packet_ledger.json")],
            mail_id=entry["mail_id"],
            to_role=entry["to_role"],
            extra={"postcondition": entry["flag"]},
        )
    return None


def _next_material_packet_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    flags = run_state["flags"]
    if (
        flags.get("pm_material_packets_issued")
        and flags.get("reviewer_dispatch_allowed")
        and not flags.get("material_scan_dispatch_blocked")
        and not flags.get("material_scan_packets_relayed")
    ):
        index = _load_packet_index(_material_scan_index_path(run_root), label="material scan")
        if not run_state.get("ledger_check_requested"):
            return make_action(
                action_type="relay_material_scan_packets",
                actor="controller",
                label="material_scan_packets_relayed_after_reviewer_dispatch_with_ledger_check",
                summary="Check the packet ledger and relay material scan packet envelopes to workers without opening bodies.",
                allowed_reads=[
                    project_relative(project_root, run_root / "packet_ledger.json"),
                    project_relative(project_root, _material_scan_index_path(run_root)),
                ],
                allowed_writes=[
                    project_relative(project_root, run_state_path(run_root)),
                    project_relative(project_root, run_root / "packet_ledger.json"),
                ],
                to_role="worker_a,worker_b",
                extra={
                    "postcondition": "material_scan_packets_relayed",
                    "controller_visibility": "packet_envelopes_only",
                    "sealed_body_reads_allowed": False,
                    "combined_ledger_check_and_relay": True,
                    "ledger_check_receipt_required": True,
                    "packet_ids": [record.get("packet_id") for record in index["packets"]],
                },
            )
        return make_action(
            action_type="relay_material_scan_packets",
            actor="controller",
            label="material_scan_packets_relayed_after_reviewer_dispatch",
            summary="Relay material scan packet envelopes to workers without opening bodies.",
            allowed_reads=[project_relative(project_root, _material_scan_index_path(run_root))],
            allowed_writes=[project_relative(project_root, run_root / "packet_ledger.json")],
            to_role="worker_a,worker_b",
            extra={
                "postcondition": "material_scan_packets_relayed",
                "controller_visibility": "packet_envelopes_only",
                "sealed_body_reads_allowed": False,
            },
        )
    if flags.get("worker_scan_results_returned") and not flags.get("material_scan_results_relayed_to_reviewer"):
        index = _load_packet_index(_material_scan_index_path(run_root), label="material scan")
        if not run_state.get("ledger_check_requested"):
            return make_action(
                action_type="relay_material_scan_results_to_reviewer",
                actor="controller",
                label="material_scan_results_relayed_to_reviewer_with_ledger_check",
                summary="Check the packet ledger and relay material scan result envelopes to reviewer without opening result bodies.",
                allowed_reads=[
                    project_relative(project_root, run_root / "packet_ledger.json"),
                    project_relative(project_root, _material_scan_index_path(run_root)),
                ],
                allowed_writes=[
                    project_relative(project_root, run_state_path(run_root)),
                    project_relative(project_root, run_root / "packet_ledger.json"),
                ],
                to_role="human_like_reviewer",
                extra={
                    "postcondition": "material_scan_results_relayed_to_reviewer",
                    "controller_visibility": "result_envelopes_only",
                    "sealed_body_reads_allowed": False,
                    "combined_ledger_check_and_relay": True,
                    "ledger_check_receipt_required": True,
                    "packet_ids": [record.get("packet_id") for record in index["packets"]],
                },
            )
        return make_action(
            action_type="relay_material_scan_results_to_reviewer",
            actor="controller",
            label="material_scan_results_relayed_to_reviewer",
            summary="Relay material scan result envelopes to reviewer without opening result bodies.",
            allowed_reads=[project_relative(project_root, _material_scan_index_path(run_root))],
            allowed_writes=[project_relative(project_root, run_root / "packet_ledger.json")],
            to_role="human_like_reviewer",
            extra={
                "postcondition": "material_scan_results_relayed_to_reviewer",
                "controller_visibility": "result_envelopes_only",
                "sealed_body_reads_allowed": False,
            },
        )
    return None


def _next_research_packet_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    flags = run_state["flags"]
    if flags.get("research_capability_decision_recorded") and not flags.get("research_packet_relayed"):
        index = _load_packet_index(_research_packet_index_path(run_root), label="research")
        if not run_state.get("ledger_check_requested"):
            return make_action(
                action_type="relay_research_packet",
                actor="controller",
                label="research_packet_relayed_to_worker_with_ledger_check",
                summary="Check the packet ledger and relay research packet envelope to worker without opening the body.",
                allowed_reads=[
                    project_relative(project_root, run_root / "packet_ledger.json"),
                    project_relative(project_root, _research_packet_index_path(run_root)),
                ],
                allowed_writes=[
                    project_relative(project_root, run_state_path(run_root)),
                    project_relative(project_root, run_root / "packet_ledger.json"),
                ],
                to_role=str(index["packets"][0].get("to_role") or "worker_a"),
                extra={
                    "postcondition": "research_packet_relayed",
                    "controller_visibility": "packet_envelope_only",
                    "sealed_body_reads_allowed": False,
                    "combined_ledger_check_and_relay": True,
                    "ledger_check_receipt_required": True,
                    "packet_ids": [record.get("packet_id") for record in index["packets"]],
                },
            )
        return make_action(
            action_type="relay_research_packet",
            actor="controller",
            label="research_packet_relayed_to_worker",
            summary="Relay research packet envelope to worker without opening the body.",
            allowed_reads=[project_relative(project_root, _research_packet_index_path(run_root))],
            allowed_writes=[project_relative(project_root, run_root / "packet_ledger.json")],
            to_role=str(index["packets"][0].get("to_role") or "worker_a"),
            extra={
                "postcondition": "research_packet_relayed",
                "controller_visibility": "packet_envelope_only",
                "sealed_body_reads_allowed": False,
            },
        )
    if flags.get("worker_research_report_returned") and not flags.get("research_result_relayed_to_reviewer"):
        index = _load_packet_index(_research_packet_index_path(run_root), label="research")
        if not run_state.get("ledger_check_requested"):
            return make_action(
                action_type="relay_research_result_to_reviewer",
                actor="controller",
                label="research_result_relayed_to_reviewer_with_ledger_check",
                summary="Check the packet ledger and relay research result envelope to reviewer without opening the result body.",
                allowed_reads=[
                    project_relative(project_root, run_root / "packet_ledger.json"),
                    project_relative(project_root, _research_packet_index_path(run_root)),
                ],
                allowed_writes=[
                    project_relative(project_root, run_state_path(run_root)),
                    project_relative(project_root, run_root / "packet_ledger.json"),
                ],
                to_role="human_like_reviewer",
                extra={
                    "postcondition": "research_result_relayed_to_reviewer",
                    "controller_visibility": "result_envelope_only",
                    "sealed_body_reads_allowed": False,
                    "combined_ledger_check_and_relay": True,
                    "ledger_check_receipt_required": True,
                    "packet_ids": [record.get("packet_id") for record in index["packets"]],
                },
            )
        return make_action(
            action_type="relay_research_result_to_reviewer",
            actor="controller",
            label="research_result_relayed_to_reviewer",
            summary="Relay research result envelope to reviewer without opening the result body.",
            allowed_reads=[project_relative(project_root, _research_packet_index_path(run_root))],
            allowed_writes=[project_relative(project_root, run_root / "packet_ledger.json")],
            to_role="human_like_reviewer",
            extra={
                "postcondition": "research_result_relayed_to_reviewer",
                "controller_visibility": "result_envelope_only",
                "sealed_body_reads_allowed": False,
            },
        )
    return None


def _next_current_node_packet_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    flags = run_state["flags"]
    if not flags.get("current_node_packet_registered"):
        return None
    if not flags.get("current_node_dispatch_allowed"):
        return None
    if not flags.get("current_node_packet_relayed"):
        payload = _latest_event_payload(run_state, "pm_registers_current_node_packet")
        envelope_path = _packet_envelope_path(project_root, run_state, payload)
        envelope = packet_runtime.load_envelope(project_root, envelope_path)
        frontier = _active_frontier(run_root)
        grant_path = _active_node_write_grant_path(run_root, frontier)
        grant_extra: dict[str, Any] = {}
        relay_allowed_reads = [project_relative(project_root, envelope_path)]
        if grant_path.exists():
            relay_allowed_reads.append(project_relative(project_root, grant_path))
            grant_extra = {
                "current_node_write_grant_path": project_relative(project_root, grant_path),
                "current_node_write_grant_hash": hashlib.sha256(grant_path.read_bytes()).hexdigest(),
            }
        if not run_state.get("ledger_check_requested"):
            return make_action(
                action_type="relay_current_node_packet",
                actor="controller",
                label="current_node_packet_relayed_after_reviewer_dispatch_with_ledger_check",
                summary=(
                    f"Check the packet ledger and relay current-node packet {envelope['packet_id']} "
                    f"to {envelope['to_role']} without opening its body."
                ),
                allowed_reads=[
                    project_relative(project_root, run_root / "packet_ledger.json"),
                    *relay_allowed_reads,
                ],
                allowed_writes=[
                    project_relative(project_root, run_state_path(run_root)),
                    project_relative(project_root, run_root / "packet_ledger.json"),
                ],
                to_role=str(envelope["to_role"]),
                extra={
                    "packet_id": envelope["packet_id"],
                    "postcondition": "current_node_packet_relayed",
                    "controller_visibility": "packet_envelope_only",
                    "sealed_body_reads_allowed": False,
                    "combined_ledger_check_and_relay": True,
                    "ledger_check_receipt_required": True,
                    **grant_extra,
                },
            )
        return make_action(
            action_type="relay_current_node_packet",
            actor="controller",
            label="current_node_packet_relayed_after_reviewer_dispatch",
            summary=f"Relay current-node packet {envelope['packet_id']} to {envelope['to_role']} without opening its body.",
            allowed_reads=relay_allowed_reads,
            allowed_writes=[project_relative(project_root, run_root / "packet_ledger.json")],
            to_role=str(envelope["to_role"]),
            extra={
                "packet_id": envelope["packet_id"],
                "postcondition": "current_node_packet_relayed",
                "controller_visibility": "packet_envelope_only",
                "sealed_body_reads_allowed": False,
                **grant_extra,
            },
        )
    if flags.get("current_node_worker_result_returned") and not flags.get("current_node_result_relayed_to_reviewer"):
        payload = _latest_event_payload(run_state, "worker_current_node_result_returned")
        result_path = _result_envelope_path(project_root, run_state, payload)
        result = packet_runtime.load_envelope(project_root, result_path)
        if not run_state.get("ledger_check_requested"):
            return make_action(
                action_type="relay_current_node_result_to_reviewer",
                actor="controller",
                label="current_node_result_relayed_to_reviewer_with_ledger_check",
                summary=(
                    "Check the packet ledger and relay the current-node worker "
                    "result envelope to reviewer without opening the result body."
                ),
                allowed_reads=[
                    project_relative(project_root, run_root / "packet_ledger.json"),
                    project_relative(project_root, result_path),
                ],
                allowed_writes=[
                    project_relative(project_root, run_state_path(run_root)),
                    project_relative(project_root, run_root / "packet_ledger.json"),
                ],
                to_role="human_like_reviewer",
                extra={
                    "packet_id": result["packet_id"],
                    "postcondition": "current_node_result_relayed_to_reviewer",
                    "controller_visibility": "result_envelope_only",
                    "sealed_body_reads_allowed": False,
                    "combined_ledger_check_and_relay": True,
                    "ledger_check_receipt_required": True,
                },
            )
        return make_action(
            action_type="relay_current_node_result_to_reviewer",
            actor="controller",
            label="current_node_result_relayed_to_reviewer",
            summary=f"Relay current-node result envelope {result['packet_id']} to reviewer without opening result body.",
            allowed_reads=[project_relative(project_root, result_path)],
            allowed_writes=[project_relative(project_root, run_root / "packet_ledger.json")],
            to_role="human_like_reviewer",
            extra={
                "packet_id": result["packet_id"],
                "postcondition": "current_node_result_relayed_to_reviewer",
                "controller_visibility": "result_envelope_only",
                "sealed_body_reads_allowed": False,
            },
        )
    return None


def _expected_role_decision_wait_action(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    *,
    label: str,
    summary: str,
    allowed_external_events: list[str],
    to_role: str,
    payload_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    extra: dict[str, Any] = {
        "allowed_external_events": allowed_external_events,
        "controller_only_mode_active": True,
        "controller_may_create_project_evidence": False,
        "expected_wait_is_not_control_blocker": True,
    }
    if payload_contract is not None:
        extra["payload_contract"] = payload_contract
    return make_action(
        action_type="await_role_decision",
        actor="controller",
        label=label,
        summary=summary,
        allowed_reads=[project_relative(project_root, run_state_path(run_root))],
        allowed_writes=[project_relative(project_root, run_state_path(run_root))],
        to_role=to_role,
        extra=extra,
    )


def _event_wait_role(event: str, meta: dict[str, str]) -> str:
    del meta
    if event.startswith("pm_"):
        return "project_manager"
    if event.startswith("reviewer_") or event.startswith("current_node_reviewer_"):
        return "human_like_reviewer"
    if event.startswith("product_officer_"):
        return "product_flowguard_officer"
    if event.startswith("process_officer_"):
        return "process_flowguard_officer"
    if event.startswith("worker_"):
        return "worker_a"
    if event.startswith("host_"):
        return "host"
    if event.startswith("controller_") or event in {"capability_evidence_synced"}:
        return "controller"
    if event == "research_capability_decision_recorded":
        return "project_manager"
    return "project_manager"


def _pending_expected_external_event_groups(run_state: dict[str, Any]) -> list[list[tuple[str, dict[str, str]]]]:
    flags = run_state["flags"]
    grouped: dict[str, list[tuple[str, dict[str, str]]]] = {}
    ordered_requires: list[str] = []
    for event, meta in EXTERNAL_EVENTS.items():
        required_flag = meta.get("requires_flag")
        if not required_flag:
            continue
        if required_flag not in grouped:
            grouped[required_flag] = []
            ordered_requires.append(required_flag)
        grouped[required_flag].append((event, meta))

    pending: list[list[tuple[str, dict[str, str]]]] = []
    for required_flag in ordered_requires:
        if not flags.get(required_flag):
            continue
        if required_flag == "pm_control_blocker_repair_decision_recorded" and not isinstance(
            run_state.get("active_control_blocker"), dict
        ):
            continue
        group = grouped[required_flag]
        if any(flags.get(meta["flag"]) for _event, meta in group):
            continue
        pending.append(group)
    return pending


def _next_expected_role_decision_wait_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    pending_groups = _pending_expected_external_event_groups(run_state)
    if not pending_groups:
        return None
    group = pending_groups[0]
    allowed_events = [event for event, _meta in group]
    roles = sorted({_event_wait_role(event, meta) for event, meta in group})
    required_flag = str(group[0][1].get("requires_flag") or "")
    role_label = roles[0] if len(roles) == 1 else ",".join(roles)
    safe_event_label = "_or_".join(allowed_events).replace("-", "_")
    return _expected_role_decision_wait_action(
        project_root,
        run_state,
        run_root,
        label=f"controller_waits_for_expected_event_{safe_event_label}",
        summary=(
            f"Prerequisite {required_flag} is satisfied and no controller action is due. "
            f"Controller must wait for expected external event(s): {', '.join(allowed_events)}."
        ),
        allowed_external_events=allowed_events,
        to_role=role_label,
        payload_contract=_role_decision_payload_contract_for_events(project_root, run_root, allowed_events),
    )


def _pending_role_decision_staleness(run_state: dict[str, Any], pending_action: object) -> dict[str, Any] | None:
    if not isinstance(pending_action, dict) or pending_action.get("action_type") != "await_role_decision":
        return None
    allowed_events = pending_action.get("allowed_external_events")
    if not isinstance(allowed_events, list) or not allowed_events:
        return {
            "reason": "await_role_decision_missing_allowed_external_events",
            "action_type": pending_action.get("action_type"),
            "label": pending_action.get("label"),
        }
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    invalid_events: list[dict[str, Any]] = []
    normalized_events: list[str] = []
    for item in allowed_events:
        if not isinstance(item, str):
            invalid_events.append({"issue": "non_string_allowed_external_event", "event": repr(item)})
            continue
        normalized_events.append(item)
        meta = EXTERNAL_EVENTS.get(item)
        if not isinstance(meta, dict):
            invalid_events.append({"issue": "unknown_external_event", "event": item})
            continue
        required_flag = meta.get("requires_flag")
        if required_flag and not flags.get(required_flag):
            invalid_events.append(
                {
                    "issue": "requires_flag_false",
                    "event": item,
                    "requires_flag": required_flag,
                    "current_value": flags.get(required_flag),
                }
            )
    if not invalid_events:
        return None
    return {
        "reason": "await_role_decision_allowed_event_not_currently_receivable",
        "action_type": pending_action.get("action_type"),
        "label": pending_action.get("label"),
        "allowed_external_events": normalized_events,
        "invalid_allowed_external_events": invalid_events,
    }


def compute_controller_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any]:
    terminal_action = _run_lifecycle_terminal_action(project_root, run_state, run_root)
    if terminal_action is not None:
        run_state["pending_action"] = terminal_action
        append_history(run_state, "router_computed_terminal_lifecycle_action", {"action_type": terminal_action["action_type"]})
        save_run_state(run_root, run_state)
        return terminal_action
    pending_action = run_state.get("pending_action")
    stale_pending = _pending_role_decision_staleness(run_state, pending_action)
    if stale_pending:
        run_state["pending_action"] = None
        append_history(run_state, "router_cleared_stale_pending_action", stale_pending)
        save_run_state(run_root, run_state)
    elif pending_action:
        return pending_action
    if not _route_memory_ready(run_root, run_state):
        _refresh_route_memory(project_root, run_root, run_state, trigger="router_next_action")
    action = _next_control_blocker_action(project_root, run_state, run_root)
    if action is None:
        action = _next_display_plan_action(project_root, run_state, run_root)
    if action is None:
        action = _next_resume_action(project_root, run_state, run_root)
    if action is None:
        action = _next_startup_heartbeat_binding_action(project_root, run_state, run_root)
    if action is None:
        action = _next_startup_mechanical_audit_action(project_root, run_state, run_root)
    if action is None:
        action = _next_startup_display_action(project_root, run_state, run_root)
    if action is None:
        _invalidate_route_completion_if_dirty_before_closure(run_state, run_root)
        action = _next_system_card_action(project_root, run_state, run_root)
    if action is None and _resume_waits_for_pm_decision(run_state):
        action = make_action(
            action_type="await_role_decision",
            actor="controller",
            label="controller_waits_for_pm_resume_decision",
            summary="Resume state has been loaded and resume cards delivered. Controller must wait for PM resume decision before continuing any route, mail, or packet work.",
            allowed_reads=[
                project_relative(project_root, run_root / "continuation" / "resume_reentry.json"),
                project_relative(project_root, run_state_path(run_root)),
            ],
            allowed_writes=[project_relative(project_root, run_state_path(run_root))],
            extra={
                "allowed_external_events": ["pm_resume_recovery_decision_returned"],
                "payload_contract": _pm_resume_decision_payload_contract(project_root, run_root),
            },
        )
    if action is None:
        action = _next_mail_action(project_root, run_state, run_root)
    if action is None:
        action = _next_material_packet_action(project_root, run_state, run_root)
    if action is None:
        action = _next_research_packet_action(project_root, run_state, run_root)
    if action is None:
        action = _next_current_node_packet_action(project_root, run_state, run_root)
    if action is None:
        action = _next_expected_role_decision_wait_action(project_root, run_state, run_root)
    if action is None:
        _write_control_blocker(
            project_root,
            run_root,
            run_state,
            source="router_no_legal_next_action",
            error_message=(
                "Controller has no legal next action; PM repair or routing decision is required before any "
                "further route, mail, packet, or project work."
            ),
            action_type="controller_no_legal_next_action",
            payload={
                "path": project_relative(project_root, run_state_path(run_root)),
                "role": "controller",
            },
        )
        action = _next_control_blocker_action(project_root, run_state, run_root)
        if action is None:
            raise RouterError("no legal next action control blocker was not materialized")
    run_state["pending_action"] = action
    append_history(run_state, "router_computed_next_controller_action", {"action_type": action["action_type"]})
    save_run_state(run_root, run_state)
    return action


def next_action(project_root: Path, *, new_invocation: bool = False) -> dict[str, Any]:
    project_root = project_root.resolve()
    bootstrap = load_bootstrap_state(project_root, create_if_missing=True, new_invocation=new_invocation)
    boot_action = compute_bootloader_action(project_root, bootstrap)
    if boot_action is not None:
        return boot_action
    run_state, run_root = load_run_state(project_root, bootstrap)
    if run_state is None or run_root is None:
        raise RouterError("bootloader complete but run router state is missing")
    return compute_controller_action(project_root, run_state, run_root)


def apply_controller_action(project_root: Path, action_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    bootstrap = load_bootstrap_state(project_root, create_if_missing=False)
    run_state, run_root = load_run_state(project_root, bootstrap)
    if run_state is None or run_root is None:
        raise RouterError("run state is missing")
    pending = _ensure_pending(run_state, action_type)
    if action_type == "check_prompt_manifest":
        run_state["manifest_check_requested"] = True
        run_state["manifest_check_requests"] = int(run_state.get("manifest_check_requests", 0)) + 1
        run_state["manifest_checks"] = int(run_state.get("manifest_checks", 0)) + 1
    elif action_type == "write_startup_mechanical_audit":
        computed_checks = _startup_fact_checks(project_root, run_root, run_state)
        _write_startup_mechanical_audit(project_root, run_root, run_state, computed_checks)
        context = _startup_mechanical_audit_context(project_root, run_root, run_state)
        if context is None:
            raise RouterError("startup mechanical audit was not written with a valid proof")
        run_state["flags"]["startup_mechanical_audit_written"] = True
        run_state["startup_mechanical_audit"] = {
            "path": project_relative(project_root, context["audit_path"]),
            "sha256": context["audit_hash"],
            "proof_path": project_relative(project_root, context["proof_path"]),
            "proof_sha256": context["proof_hash"],
            "written_before_reviewer_card": not run_state["flags"].get("reviewer_startup_fact_check_card_delivered"),
        }
    elif action_type == "deliver_system_card":
        card_id = str(pending["card_id"])
        card_entry = next((entry for entry in SYSTEM_CARD_SEQUENCE if entry["card_id"] == card_id), None)
        if card_entry is None:
            raise RouterError(f"unknown system card in pending action: {card_id}")
        if not run_state.get("manifest_check_requested"):
            raise RouterError("system card delivery requires a current manifest check")
        manifest = load_manifest_from_run(run_root)
        card = manifest_card(manifest, card_id)
        delivery_context = pending.get("delivery_context")
        if not isinstance(delivery_context, dict):
            delivery_context = _live_card_delivery_context(project_root, run_root, run_state, card_entry, card)
        delivery = {
            "card_id": card_id,
            "from": "system",
            "issued_by": "router",
            "delivered_by": "controller",
            "to_role": pending["to_role"],
            "path": card["path"],
            "delivery_context": delivery_context,
            "delivered_at": utc_now(),
        }
        if card_id == "reviewer.startup_fact_check":
            delivery.update(
                {
                    "startup_mechanical_audit_path": pending.get("startup_mechanical_audit_path"),
                    "startup_mechanical_audit_hash": pending.get("startup_mechanical_audit_hash"),
                    "router_owned_check_proof_path": pending.get("router_owned_check_proof_path"),
                    "router_owned_check_proof_hash": pending.get("router_owned_check_proof_hash"),
                    "router_computable_checks_already_enforced": True,
                    "reviewer_should_not_reprove_router_computable_checks": True,
                    "reviewer_required_external_facts": pending.get("reviewer_required_external_facts") or [],
                }
            )
        run_state["delivered_cards"].append(delivery)
        run_state["flags"][card_entry["flag"]] = True
        run_state["manifest_check_requested"] = False
        run_state["prompt_deliveries"] = int(run_state.get("prompt_deliveries", 0)) + 1
        ledger = read_json_if_exists(run_root / "prompt_delivery_ledger.json") or {"schema_version": "flowpilot.prompt_delivery_ledger.v1", "deliveries": []}
        ledger.setdefault("deliveries", []).append(delivery)
        ledger["updated_at"] = utc_now()
        write_json(run_root / "prompt_delivery_ledger.json", ledger)
    elif action_type == "check_packet_ledger":
        run_state["ledger_check_requested"] = True
        run_state["ledger_check_requests"] = int(run_state.get("ledger_check_requests", 0)) + 1
        run_state["ledger_checks"] = int(run_state.get("ledger_checks", 0)) + 1
    elif action_type == "deliver_mail":
        mail_id = str(pending["mail_id"])
        mail_entry = next((entry for entry in MAIL_SEQUENCE if entry["mail_id"] == mail_id), None)
        if mail_entry is None:
            raise RouterError(f"unknown mail in pending action: {mail_id}")
        if not run_state.get("ledger_check_requested"):
            raise RouterError("mail delivery requires a current packet-ledger check")
        delivery = {
            "mail_id": mail_id,
            "delivered_by": "controller",
            "to_role": pending["to_role"],
            "delivered_at": utc_now(),
        }
        run_state["delivered_mail"].append(delivery)
        run_state["flags"][mail_entry["flag"]] = True
        run_state["ledger_check_requested"] = False
        run_state["mail_deliveries"] = int(run_state.get("mail_deliveries", 0)) + 1
        ledger = read_json(run_root / "packet_ledger.json")
        ledger.setdefault("mail", []).append(delivery)
        ledger["updated_at"] = utc_now()
        write_json(run_root / "packet_ledger.json", ledger)
    elif action_type == "relay_material_scan_packets":
        combined_ledger_check = pending.get("combined_ledger_check_and_relay") is True
        if not run_state.get("ledger_check_requested"):
            if not combined_ledger_check:
                raise RouterError("material scan packet relay requires a current packet-ledger check")
            run_state["ledger_check_requested"] = True
            run_state["ledger_check_requests"] = int(run_state.get("ledger_check_requests", 0)) + 1
            run_state["ledger_checks"] = int(run_state.get("ledger_checks", 0)) + 1
        if not run_state.get("ledger_check_requested"):
            raise RouterError("material scan packet relay requires a current packet-ledger check")
        index = _load_packet_index(_material_scan_index_path(run_root), label="material scan")
        _relay_packet_records(project_root, run_state, index["packets"], controller_agent_id="controller")
        run_state["flags"]["material_scan_packets_relayed"] = True
        run_state["ledger_check_requested"] = False
    elif action_type == "relay_material_scan_results_to_reviewer":
        combined_ledger_check = pending.get("combined_ledger_check_and_relay") is True
        if not run_state.get("ledger_check_requested"):
            if not combined_ledger_check:
                raise RouterError("material scan result relay requires a current packet-ledger check")
            run_state["ledger_check_requested"] = True
            run_state["ledger_check_requests"] = int(run_state.get("ledger_check_requests", 0)) + 1
            run_state["ledger_checks"] = int(run_state.get("ledger_checks", 0)) + 1
        if not run_state.get("ledger_check_requested"):
            raise RouterError("material scan result relay requires a current packet-ledger check")
        index = _load_packet_index(_material_scan_index_path(run_root), label="material scan")
        _relay_result_records(project_root, run_state, index["packets"], to_role="human_like_reviewer", controller_agent_id="controller")
        run_state["flags"]["material_scan_results_relayed_to_reviewer"] = True
        run_state["ledger_check_requested"] = False
    elif action_type == "relay_research_packet":
        combined_ledger_check = pending.get("combined_ledger_check_and_relay") is True
        if not run_state.get("ledger_check_requested"):
            if not combined_ledger_check:
                raise RouterError("research packet relay requires a current packet-ledger check")
            run_state["ledger_check_requested"] = True
            run_state["ledger_check_requests"] = int(run_state.get("ledger_check_requests", 0)) + 1
            run_state["ledger_checks"] = int(run_state.get("ledger_checks", 0)) + 1
        if not run_state.get("ledger_check_requested"):
            raise RouterError("research packet relay requires a current packet-ledger check")
        index = _load_packet_index(_research_packet_index_path(run_root), label="research")
        _relay_packet_records(project_root, run_state, index["packets"], controller_agent_id="controller")
        run_state["flags"]["research_packet_relayed"] = True
        run_state["ledger_check_requested"] = False
    elif action_type == "relay_research_result_to_reviewer":
        combined_ledger_check = pending.get("combined_ledger_check_and_relay") is True
        if not run_state.get("ledger_check_requested"):
            if not combined_ledger_check:
                raise RouterError("research result relay requires a current packet-ledger check")
            run_state["ledger_check_requested"] = True
            run_state["ledger_check_requests"] = int(run_state.get("ledger_check_requests", 0)) + 1
            run_state["ledger_checks"] = int(run_state.get("ledger_checks", 0)) + 1
        if not run_state.get("ledger_check_requested"):
            raise RouterError("research result relay requires a current packet-ledger check")
        index = _load_packet_index(_research_packet_index_path(run_root), label="research")
        _relay_result_records(project_root, run_state, index["packets"], to_role="human_like_reviewer", controller_agent_id="controller")
        run_state["flags"]["research_result_relayed_to_reviewer"] = True
        run_state["ledger_check_requested"] = False
    elif action_type == "relay_current_node_packet":
        combined_ledger_check = pending.get("combined_ledger_check_and_relay") is True
        if not run_state.get("ledger_check_requested"):
            if not combined_ledger_check:
                raise RouterError("current-node packet relay requires a current packet-ledger check")
            run_state["ledger_check_requested"] = True
            run_state["ledger_check_requests"] = int(run_state.get("ledger_check_requests", 0)) + 1
            run_state["ledger_checks"] = int(run_state.get("ledger_checks", 0)) + 1
        if not run_state.get("ledger_check_requested"):
            raise RouterError("current-node packet relay requires a current packet-ledger check")
        envelope, envelope_path = _current_node_packet_context(project_root, run_state)
        if not run_state["flags"].get("current_node_dispatch_allowed"):
            raise RouterError("current-node packet relay requires reviewer dispatch allowance")
        _ensure_barrier_bundles_ready(project_root, node_id=str(envelope.get("node_id") or ""))
        packet_runtime.controller_relay_envelope(
            project_root,
            envelope=envelope,
            envelope_path=envelope_path,
            controller_agent_id="controller",
            received_from_role=str(envelope.get("from_role") or "project_manager"),
            relayed_to_role=str(envelope.get("to_role")),
        )
        run_state["flags"]["current_node_packet_relayed"] = True
        run_state["ledger_check_requested"] = False
    elif action_type == "relay_current_node_result_to_reviewer":
        combined_ledger_check = pending.get("combined_ledger_check_and_relay") is True
        if not run_state.get("ledger_check_requested"):
            if not combined_ledger_check:
                raise RouterError("current-node result relay requires a current packet-ledger check")
            run_state["ledger_check_requested"] = True
            run_state["ledger_check_requests"] = int(run_state.get("ledger_check_requests", 0)) + 1
            run_state["ledger_checks"] = int(run_state.get("ledger_checks", 0)) + 1
        result, result_path = _current_node_result_context(project_root, run_state)
        if not run_state["flags"].get("current_node_worker_result_returned"):
            raise RouterError("current-node result relay requires worker result event")
        _ensure_barrier_bundles_ready(project_root, node_id=str(result.get("node_id") or ""))
        packet_runtime.controller_relay_envelope(
            project_root,
            envelope=result,
            envelope_path=result_path,
            controller_agent_id="controller",
            received_from_role=str(result.get("completed_by_role") or "unknown"),
            relayed_to_role="human_like_reviewer",
        )
        run_state["flags"]["current_node_result_relayed_to_reviewer"] = True
        run_state["ledger_check_requested"] = False
    elif action_type == "load_resume_state":
        resume_next = _derive_resume_next_recipient_from_packet_ledger(run_root)
        required_paths = {
            "current_pointer": project_root / ".flowpilot" / "current.json",
            "router_state": run_state_path(run_root),
            "prompt_delivery_ledger": run_root / "prompt_delivery_ledger.json",
            "packet_ledger": run_root / "packet_ledger.json",
            "execution_frontier": run_root / "execution_frontier.json",
            "crew_ledger": run_root / "crew_ledger.json",
            "crew_memory": run_root / "crew_memory",
            "continuation_binding": _continuation_binding_path(run_root),
            "route_history_index": _route_history_index_path(run_root),
            "pm_prior_path_context": _pm_prior_path_context_path(run_root),
        }
        missing = [
            name
            for name, path in required_paths.items()
            if not path.exists()
        ]
        crew_memory_files = sorted((run_root / "crew_memory").glob("*.json")) if (run_root / "crew_memory").exists() else []
        display_payload = _display_plan_sync_payload(project_root, run_root, run_state)
        resume_record = {
            "schema_version": RESUME_EVIDENCE_SCHEMA,
            "run_id": run_state["run_id"],
            "resume_tick_id": _latest_resume_tick_id(run_state),
            "recorded_at": utc_now(),
            "recorded_by": "controller",
            "stable_launcher": True,
            "wake_recorded_to_router": True,
            "controller_only": True,
            "loaded_paths": {
                name: project_relative(project_root, path)
                for name, path in required_paths.items()
                if path.exists()
            },
            "missing_paths": missing,
            "crew_memory_count": len(crew_memory_files),
            "crew_memory_ready_for_rehydration": len(crew_memory_files) == len(CREW_ROLE_KEYS),
            "roles_restored_or_replaced": False,
            "role_rehydration_required": True,
            "controller_visibility": "state_and_envelopes_only",
            "controller_may_read_packet_body": False,
            "controller_may_read_result_body": False,
            "controller_may_infer_route_progress_from_chat_history": False,
            "display_plan_path": project_relative(project_root, _display_plan_path(run_root)),
            "visible_plan_restore_required": True,
            "visible_plan_restored_from_run": True,
            "display_plan_exists": display_payload["display_plan_exists"],
            "display_plan_projection_hash": display_payload["projection_hash"],
            "display_plan_projection": display_payload["native_plan_projection"],
            "resume_next_recipient_from_packet_ledger": resume_next,
            "pm_resume_decision_required": True,
            "ambiguous_state_blocks_controller_execution": bool(missing) or len(crew_memory_files) != len(CREW_ROLE_KEYS),
        }
        write_json(run_root / "continuation" / "resume_reentry.json", resume_record)
        run_state["flags"]["resume_state_loaded"] = True
        run_state["flags"]["resume_state_ambiguous"] = bool(resume_record["ambiguous_state_blocks_controller_execution"])
        run_state["flags"]["resume_roles_restored"] = False
    elif action_type == "rehydrate_role_agents":
        if not run_state["flags"].get("resume_state_loaded"):
            raise RouterError("resume role rehydration requires load_resume_state first")
        _write_resume_role_rehydration_report(project_root, run_root, run_state, payload or {})
    elif action_type == "create_heartbeat_automation":
        _write_host_heartbeat_binding(project_root, run_root, run_state, payload or {})
        run_state["flags"]["continuation_binding_recorded"] = True
        run_state["events"].append(
            {
                "event": "host_records_heartbeat_binding",
                "summary": EXTERNAL_EVENTS["host_records_heartbeat_binding"]["summary"],
                "payload": payload or {},
                "recorded_at": utc_now(),
                "source_action": action_type,
            }
        )
    elif action_type == "sync_display_plan":
        confirmation = _display_confirmation_for_action(payload, pending)
        sync_payload = _display_plan_sync_payload(project_root, run_root, run_state)
        if not sync_payload["display_plan_exists"]:
            write_json(_display_plan_path(run_root), _waiting_for_pm_display_plan(run_state))
            sync_payload = _display_plan_sync_payload(project_root, run_root, run_state)
        _write_route_state_snapshot(project_root, run_root, run_state, source_event="sync_display_plan")
        sync_payload = _display_plan_sync_payload(project_root, run_root, run_state)
        if sync_payload.get("route_sign_display_required"):
            route_sign = _route_map_route_sign_payload(project_root, write=True, mark_chat_displayed=True)
            sync_payload = {
                **sync_payload,
                "route_sign_markdown_path": route_sign.get("markdown_preview_path"),
                "route_sign_mermaid_path": route_sign.get("mermaid_path"),
                "route_sign_display_packet_path": route_sign.get("display_packet_path"),
                "route_sign_mermaid_sha256": route_sign.get("mermaid_sha256"),
                "route_sign_source_kind": route_sign.get("route_source_kind"),
                "route_sign_node_count": route_sign.get("route_node_count"),
                "route_sign_checklist_item_count": route_sign.get("route_checklist_item_count"),
                "route_sign_layout": route_sign.get("route_sign_layout"),
                "route_sign_source_route_path": route_sign.get("source_route_path"),
                "route_sign_source_frontier_path": route_sign.get("source_frontier_path"),
            }
        _append_user_dialog_display_ledger(project_root, run_root, confirmation)
        run_state["visible_plan_sync"] = {
            "display_plan_path": sync_payload["display_plan_path"],
            "route_state_snapshot_path": sync_payload["route_state_snapshot_path"],
            "route_state_snapshot_hash": sync_payload["route_state_snapshot_hash"],
            "projection_hash": sync_payload["projection_hash"],
            "display_text_format": sync_payload.get("display_text_format"),
            "route_sign_display_required": sync_payload.get("route_sign_display_required"),
            "route_sign_display_degraded_reason": sync_payload.get("route_sign_display_degraded_reason"),
            "route_sign_markdown_path": sync_payload.get("route_sign_markdown_path"),
            "route_sign_mermaid_path": sync_payload.get("route_sign_mermaid_path"),
            "route_sign_display_packet_path": sync_payload.get("route_sign_display_packet_path"),
            "route_sign_mermaid_sha256": sync_payload.get("route_sign_mermaid_sha256"),
            "route_sign_source_kind": sync_payload.get("route_sign_source_kind"),
            "route_sign_node_count": sync_payload.get("route_sign_node_count"),
            "route_sign_checklist_item_count": sync_payload.get("route_sign_checklist_item_count"),
            "route_sign_layout": sync_payload.get("route_sign_layout"),
            "route_sign_source_route_path": sync_payload.get("route_sign_source_route_path"),
            "route_sign_source_frontier_path": sync_payload.get("route_sign_source_frontier_path"),
            "synced_at": utc_now(),
            "host_action": sync_payload["host_action"],
            "user_dialog_display_confirmation": confirmation,
        }
    elif action_type == "write_display_surface_status":
        confirmation = _display_confirmation_for_action(payload, pending)
        _write_display_surface_status(project_root, run_root, run_state, confirmation, payload or {})
        _append_user_dialog_display_ledger(project_root, run_root, confirmation)
        run_state["flags"]["startup_display_status_written"] = True
    elif action_type == "handle_control_blocker":
        _mark_control_blocker_delivered(project_root, run_root, run_state, pending)
    elif action_type == "run_lifecycle_terminal":
        return {"ok": True, "applied": action_type, "terminal": True, "run_lifecycle_status": _terminal_lifecycle_mode(run_state)}
    elif action_type == "await_role_decision":
        return {"ok": True, "applied": action_type, "waiting": True}
    else:
        raise RouterError(f"unknown controller action: {action_type}")
    append_history(run_state, str(pending["label"]), {"action_type": action_type})
    run_state["pending_action"] = None
    _refresh_route_memory(project_root, run_root, run_state, trigger=f"after_controller_action:{action_type}")
    _sync_derived_run_views(
        project_root,
        run_root,
        run_state,
        reason=f"after_controller_action:{action_type}",
        update_display=action_type != "sync_display_plan",
    )
    save_run_state(run_root, run_state)
    result = {"ok": True, "applied": action_type}
    if action_type == "sync_display_plan":
        result.update(_display_plan_sync_payload(project_root, run_root, run_state))
        result["user_dialog_display_confirmation"] = run_state["visible_plan_sync"]["user_dialog_display_confirmation"]
    return result


def _record_external_event_unchecked(project_root: Path, event: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if event not in EXTERNAL_EVENTS:
        raise RouterError(f"unknown external event: {event}")
    bootstrap = load_bootstrap_state(project_root, create_if_missing=False)
    run_state, run_root = load_run_state(project_root, bootstrap)
    if run_state is None or run_root is None:
        raise RouterError("run state is missing")
    meta = EXTERNAL_EVENTS[event]
    flag = meta["flag"]
    required_flag = meta.get("requires_flag")
    parent_segment_decision: str | None = None
    model_miss_triage_decision: str | None = None
    if required_flag and not run_state["flags"].get(required_flag):
        raise RouterError(f"event {event} requires {required_flag}")
    _refresh_route_memory(project_root, run_root, run_state, trigger=f"before_external_event:{event}")
    if event == "heartbeat_or_manual_resume_requested":
        tick = _append_heartbeat_tick(project_root, run_root, run_state, payload or {})
        _reset_resume_cycle_for_wakeup(run_state)
        run_state["flags"]["resume_reentry_requested"] = True
        run_state["pending_action"] = None
        record = {
            "event": event,
            "summary": meta["summary"],
            "payload": payload or {},
            "recorded_at": utc_now(),
        }
        run_state["events"].append(record)
        append_history(run_state, event, {"heartbeat_tick": tick})
        _refresh_route_memory(project_root, run_root, run_state, trigger=f"after_external_event:{event}")
        _sync_derived_run_views(project_root, run_root, run_state, reason=f"after_external_event:{event}")
        save_run_state(run_root, run_state)
        return {"ok": True, "event": event, "heartbeat_tick": tick, "resume_requested": True}
    active_blocker = run_state.get("active_control_blocker")
    repeatable_pm_repair_decision = (
        event == PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT
        and isinstance(active_blocker, dict)
        and active_blocker.get("delivery_status") == "delivered"
        and active_blocker.get("handling_lane") in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES
    )
    repeatable_gate_decision = event == GATE_DECISION_EVENT
    repeatable_startup_repair_request = (
        event == "pm_requests_startup_repair"
        and run_state["flags"].get(flag)
        and run_state["flags"].get("startup_fact_reported")
        and run_state["flags"].get("pm_startup_activation_card_delivered")
    )
    repeatable_route_draft_repair = (
        event == "pm_writes_route_draft"
        and run_state["flags"].get(flag)
        and not run_state["flags"].get("route_activated_by_pm")
    )
    if run_state["flags"].get(flag) and not (
        repeatable_pm_repair_decision
        or repeatable_gate_decision
        or repeatable_startup_repair_request
        or repeatable_route_draft_repair
    ):
        finalized = _finalize_repair_transaction_outcome(
            project_root,
            run_root,
            run_state,
            event=event,
            payload=payload,
        )
        resolved = _resolve_delivered_control_blocker(
            project_root,
            run_root,
            run_state,
            resolved_by_event=event,
            from_already_recorded_event=True,
        )
        if resolved or finalized:
            run_state["pending_action"] = None
            _refresh_route_memory(project_root, run_root, run_state, trigger=f"after_already_recorded_event:{event}")
            _sync_derived_run_views(project_root, run_root, run_state, reason=f"after_already_recorded_event:{event}")
            save_run_state(run_root, run_state)
            return {
                "ok": True,
                "event": event,
                "already_recorded": True,
                "control_blocker_resolved": bool(resolved),
                "blocker_id": resolved.get("blocker_id") if resolved else None,
                "repair_transaction_finalized": finalized,
            }
        return {"ok": True, "event": event, "already_recorded": True}
    payload = payload or {}
    if event in {"user_requests_run_stop", "user_requests_run_cancel"}:
        _write_run_lifecycle_request(project_root, run_root, run_state, event=event, payload=payload)
    elif event == "pm_activates_reviewed_route":
        _write_route_activation(project_root, run_root, run_state, payload)
    elif event == "pm_resume_recovery_decision_returned":
        _write_pm_resume_decision(project_root, run_root, run_state, payload)
    elif event == "host_records_heartbeat_binding":
        _write_host_heartbeat_binding(project_root, run_root, run_state, payload)
    elif event == "pm_writes_node_acceptance_plan":
        _write_node_acceptance_plan(project_root, run_root, run_state, payload)
    elif event == "reviewer_passes_node_acceptance_plan":
        frontier = _active_frontier(run_root)
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="human_like_reviewer",
            path=_active_node_root(run_root, frontier) / "reviews" / "node_acceptance_plan_review.json",
            schema_version="flowpilot.node_acceptance_plan_review.v1",
            checked_paths=[
                _active_node_acceptance_plan_path(run_root, frontier),
                run_root / "execution_frontier.json",
            ],
        )
    elif event == "reviewer_reports_startup_facts":
        _write_startup_fact_report(project_root, run_root, run_state, payload)
    elif event == "pm_approves_startup_activation":
        _write_startup_activation(project_root, run_root, run_state, payload)
    elif event == "pm_requests_startup_repair":
        _write_startup_repair_request(project_root, run_root, run_state, payload)
    elif event == "pm_declares_startup_protocol_dead_end":
        _write_startup_protocol_dead_end(project_root, run_root, run_state, payload)
    elif event == "pm_issues_material_and_capability_scan_packets":
        _write_material_scan_packets(project_root, run_root, run_state, payload)
    elif event == "reviewer_blocks_material_scan_dispatch":
        _write_material_dispatch_block_report(project_root, run_root, run_state, payload)
    elif event == "reviewer_blocks_material_scan_dispatch_recheck":
        _write_material_dispatch_block_report(project_root, run_root, run_state, payload)
        _finalize_repair_transaction_outcome(project_root, run_root, run_state, event=event, payload=payload)
    elif event == "reviewer_protocol_blocker_material_scan_dispatch_recheck":
        _write_material_dispatch_recheck_protocol_blocker(project_root, run_root, run_state, payload)
        _finalize_repair_transaction_outcome(project_root, run_root, run_state, event=event, payload=payload)
    elif event == "worker_scan_packet_bodies_delivered_after_dispatch":
        material_index = _load_packet_index(_material_scan_index_path(run_root), label="material scan")
        _validate_packet_bodies_opened_by_targets(project_root, run_state, material_index["packets"])
    elif event == "worker_scan_results_returned":
        material_index = _load_packet_index(_material_scan_index_path(run_root), label="material scan")
        _validate_results_exist_for_packets(project_root, run_state, material_index["packets"], next_recipient="human_like_reviewer")
    elif event == "reviewer_reports_material_sufficient":
        _write_material_sufficiency_report(project_root, run_root, run_state, payload, sufficient=True)
    elif event == "reviewer_reports_material_insufficient":
        _write_material_sufficiency_report(project_root, run_root, run_state, payload, sufficient=False)
    elif event == "pm_writes_research_package":
        _write_research_package(project_root, run_root, run_state, payload)
    elif event == "research_capability_decision_recorded":
        _write_research_capability_decision(project_root, run_root, run_state, payload)
    elif event == "worker_research_report_returned":
        _write_worker_research_report(project_root, run_root, run_state, payload)
    elif event == "reviewer_passes_research_direct_source_check":
        research_index = _load_packet_index(_research_packet_index_path(run_root), label="research")
        raw_agent_map = payload.get("agent_role_map")
        _validate_packet_group_for_reviewer(
            project_root,
            run_state,
            research_index["packets"],
            audit_path=run_root / "research" / "research_packet_review_audit.json",
            agent_role_map=raw_agent_map if isinstance(raw_agent_map, dict) else None,
        )
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="human_like_reviewer",
            path=run_root / "research" / "research_reviewer_report.json",
            schema_version="flowpilot.research_reviewer_report.v1",
            checked_paths=[run_root / "research" / "research_package.json", run_root / "research" / "worker_research_report.json"],
        )
    elif event == "pm_absorbs_reviewed_research":
        _write_pm_research_absorption(project_root, run_root, run_state)
    elif event == "pm_writes_material_understanding":
        _write_material_understanding(project_root, run_root, run_state, payload)
    elif event == "pm_writes_product_function_architecture":
        _write_product_function_architecture(project_root, run_root, run_state, payload)
    elif event == "reviewer_passes_product_architecture":
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="human_like_reviewer",
            path=run_root / "reviews" / "product_architecture_challenge.json",
            schema_version="flowpilot.product_architecture_review.v1",
            checked_paths=[run_root / "product_function_architecture.json"],
        )
    elif event == "product_officer_passes_product_architecture_modelability":
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="product_flowguard_officer",
            path=run_root / "flowguard" / "product_architecture_modelability.json",
            schema_version="flowpilot.product_architecture_modelability.v1",
            checked_paths=[run_root / "product_function_architecture.json"],
        )
    elif event == "pm_writes_root_acceptance_contract":
        _write_root_acceptance_contract(project_root, run_root, run_state, payload)
    elif event == "reviewer_passes_root_acceptance_contract":
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="human_like_reviewer",
            path=run_root / "reviews" / "root_contract_challenge.json",
            schema_version="flowpilot.root_contract_review.v1",
            checked_paths=[run_root / "root_acceptance_contract.json", run_root / "standard_scenario_pack.json"],
        )
    elif event == "product_officer_passes_root_acceptance_contract_modelability":
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="product_flowguard_officer",
            path=run_root / "flowguard" / "root_contract_modelability.json",
            schema_version="flowpilot.root_contract_modelability.v1",
            checked_paths=[
                run_root / "root_acceptance_contract.json",
                run_root / "standard_scenario_pack.json",
                run_root / "reviews" / "root_contract_challenge.json",
            ],
        )
    elif event == "pm_freezes_root_acceptance_contract":
        _freeze_root_acceptance_contract(project_root, run_root, run_state)
    elif event == "pm_records_dependency_policy":
        _write_dependency_policy(project_root, run_root, run_state, payload)
    elif event == "pm_writes_capabilities_manifest":
        _write_capabilities_manifest(project_root, run_root, run_state, payload)
    elif event == "pm_writes_child_skill_selection":
        _write_child_skill_selection(project_root, run_root, run_state, payload)
    elif event == "pm_writes_child_skill_gate_manifest":
        _write_child_skill_gate_manifest(project_root, run_root, run_state, payload)
    elif event == "reviewer_passes_child_skill_gate_manifest":
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="human_like_reviewer",
            path=run_root / "reviews" / "child_skill_gate_manifest_review.json",
            schema_version="flowpilot.child_skill_gate_manifest_review.v1",
            checked_paths=[
                run_root / "child_skill_gate_manifest.json",
                run_root / "pm_child_skill_selection.json",
                run_root / "capabilities.json",
            ],
        )
        _sync_child_skill_manifest_review_approval(project_root, run_root)
    elif event == "process_officer_passes_child_skill_conformance_model":
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="process_flowguard_officer",
            path=run_root / "flowguard" / "child_skill_conformance_model.json",
            schema_version="flowpilot.child_skill_conformance_model.v1",
            checked_paths=[
                run_root / "child_skill_gate_manifest.json",
                run_root / "reviews" / "child_skill_gate_manifest_review.json",
            ],
        )
    elif event == "product_officer_passes_child_skill_product_fit":
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="product_flowguard_officer",
            path=run_root / "flowguard" / "child_skill_product_fit.json",
            schema_version="flowpilot.child_skill_product_fit.v1",
            checked_paths=[
                run_root / "child_skill_gate_manifest.json",
                run_root / "flowguard" / "child_skill_conformance_model.json",
                run_root / "product_function_architecture.json",
                run_root / "root_acceptance_contract.json",
            ],
        )
    elif event == "pm_approves_child_skill_manifest_for_route":
        _approve_child_skill_manifest_for_route(project_root, run_root, run_state, payload)
    elif event == "capability_evidence_synced":
        _sync_capability_evidence(project_root, run_root, run_state, payload)
    elif event == "pm_writes_route_draft":
        if repeatable_route_draft_repair:
            _reset_route_review_after_route_draft_repair(run_state)
        _write_route_draft(project_root, run_root, run_state, payload)
    elif event == "process_officer_passes_route_check":
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="process_flowguard_officer",
            path=run_root / "flowguard" / "route_process_check.json",
            schema_version="flowpilot.route_process_check.v1",
            checked_paths=[
                _current_route_draft_path(run_root),
                run_root / "root_acceptance_contract.json",
                run_root / "child_skill_gate_manifest.json",
            ],
        )
    elif event == "product_officer_passes_route_check":
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="product_flowguard_officer",
            path=run_root / "flowguard" / "route_product_check.json",
            schema_version="flowpilot.route_product_check.v1",
            checked_paths=[
                _current_route_draft_path(run_root),
                run_root / "product_function_architecture.json",
                run_root / "root_acceptance_contract.json",
                run_root / "flowguard" / "route_process_check.json",
            ],
        )
    elif event == "reviewer_passes_route_check":
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="human_like_reviewer",
            path=run_root / "reviews" / "route_challenge.json",
            schema_version="flowpilot.route_review.v1",
            checked_paths=[
                _current_route_draft_path(run_root),
                run_root / "flowguard" / "route_process_check.json",
                run_root / "flowguard" / "route_product_check.json",
            ],
        )
    elif event == "pm_registers_current_node_packet":
        _validate_current_node_packet_event(project_root, run_root, run_state, payload)
    elif event == "worker_current_node_result_returned":
        _validate_current_node_result_event(project_root, run_state, payload)
    elif event == "current_node_reviewer_passes_result":
        _validate_current_node_reviewer_pass(project_root, run_state, payload)
    elif event == "pm_builds_parent_backward_targets":
        _write_parent_backward_targets(project_root, run_root, run_state, payload)
    elif event == "reviewer_passes_parent_backward_replay":
        _write_parent_backward_replay(project_root, run_root, run_state, payload)
    elif event == "pm_records_parent_segment_decision":
        parent_segment_decision = _write_parent_segment_decision(project_root, run_root, run_state, payload)
    elif event == "pm_completes_current_node_from_reviewed_result":
        _mark_frontier_node_completed(project_root, run_root, run_state, payload)
    elif event == "pm_records_evidence_quality_package":
        _write_evidence_quality_package(project_root, run_root, run_state, payload)
    elif event == "reviewer_passes_evidence_quality_package":
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="human_like_reviewer",
            path=run_root / "reviews" / "evidence_quality_review.json",
            schema_version="flowpilot.evidence_quality_review.v1",
            checked_paths=[
                run_root / "evidence" / "evidence_ledger.json",
                run_root / "generated_resource_ledger.json",
                run_root / "quality" / "quality_package.json",
            ],
        )
    elif event == "pm_records_final_route_wide_ledger_clean":
        _write_final_route_wide_ledger(project_root, run_root, run_state, payload)
    elif event == "reviewer_final_backward_replay_passed":
        _write_terminal_backward_replay(project_root, run_root, run_state, payload)
    elif event == "pm_mutates_route_after_review_block":
        if not run_state["flags"].get("node_review_blocked"):
            raise RouterError("review-block route mutation requires an active node_review_blocked state")
        if not run_state["flags"].get("model_miss_triage_closed"):
            raise RouterError("review-block repair or route mutation requires closed model-miss triage first")
        _write_route_mutation(project_root, run_root, run_state, payload)
    elif event == PM_MODEL_MISS_TRIAGE_DECISION_EVENT:
        model_miss_triage_decision = _write_model_miss_triage_decision(project_root, run_root, run_state, payload)
    elif event == PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT:
        _write_control_blocker_repair_decision(project_root, run_root, run_state, payload)
    elif event == GATE_DECISION_EVENT:
        _write_gate_decision(project_root, run_root, run_state, payload)
    elif event == "pm_approves_terminal_closure":
        _write_terminal_closure_suite(project_root, run_root, run_state, payload)
    elif event == "pm_accepts_reviewed_material":
        if run_state.get("material_review") != "sufficient":
            raise RouterError("PM can accept material only after a sufficient reviewer material report")
    elif event == "pm_requests_research_after_material_insufficient":
        if run_state.get("material_review") != "insufficient":
            raise RouterError("PM can request research on this path only after an insufficient reviewer material report")
    record = {
        "event": event,
        "summary": meta["summary"],
        "payload": payload,
        "recorded_at": utc_now(),
    }
    run_state["flags"][flag] = True
    if event in {"current_node_reviewer_blocks_result", "reviewer_blocks_material_scan_dispatch"}:
        run_state["flags"]["pm_model_miss_triage_card_delivered"] = False
        run_state["flags"]["model_miss_triage_closed"] = False
        run_state["flags"]["pm_review_repair_card_delivered"] = False
        run_state["model_miss_triage"] = None
    if (
        event == PM_MODEL_MISS_TRIAGE_DECISION_EVENT
        and model_miss_triage_decision not in PM_MODEL_MISS_TRIAGE_REPAIR_AUTHORIZED_VALUES
    ):
        run_state["flags"][flag] = False
    if event == "pm_records_parent_segment_decision" and (parent_segment_decision or "continue") != "continue":
        run_state["flags"][flag] = False
    if event == "pm_absorbs_reviewed_research":
        run_state["flags"]["material_accepted_by_pm"] = True
    run_state["events"].append(record)
    if event == "reviewer_allows_material_scan_dispatch":
        _finalize_repair_transaction_outcome(project_root, run_root, run_state, event=event, payload=payload)
        run_state["flags"]["material_scan_dispatch_blocked"] = False
        run_state["material_dispatch_block"] = None
    else:
        _finalize_repair_transaction_outcome(project_root, run_root, run_state, event=event, payload=payload)
    if event == "reviewer_reports_material_sufficient":
        run_state["material_review"] = "sufficient"
    elif event == "reviewer_reports_material_insufficient":
        run_state["material_review"] = "insufficient"
    append_history(run_state, event, payload)
    _resolve_delivered_control_blocker(project_root, run_root, run_state, resolved_by_event=event)
    run_state["pending_action"] = None
    _refresh_route_memory(project_root, run_root, run_state, trigger=f"after_external_event:{event}")
    _sync_derived_run_views(project_root, run_root, run_state, reason=f"after_external_event:{event}")
    save_run_state(run_root, run_state)
    return {"ok": True, "event": event}


def record_external_event(project_root: Path, event: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        return _record_external_event_unchecked(project_root, event, payload)
    except (RouterError, packet_runtime.PacketRuntimeError) as exc:
        existing_blocker = getattr(exc, "control_blocker", None)
        if isinstance(existing_blocker, dict):
            raise
        blocker = _try_write_control_blocker_for_exception(
            project_root,
            source="router.record_external_event",
            error_message=str(exc),
            event=event,
            payload=payload,
        )
        if blocker:
            raise RouterError(str(exc), control_blocker=blocker) from exc
        raise


def apply_action(project_root: Path, action_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    bootstrap = load_bootstrap_state(project_root, create_if_missing=False)
    pending = bootstrap.get("pending_action")
    if isinstance(pending, dict) and pending.get("action_type") == action_type:
        return apply_bootloader_action(project_root, action_type, payload)
    try:
        return apply_controller_action(project_root, action_type, payload)
    except (RouterError, packet_runtime.PacketRuntimeError) as exc:
        existing_blocker = getattr(exc, "control_blocker", None)
        if isinstance(existing_blocker, dict):
            raise
        blocker = _try_write_control_blocker_for_exception(
            project_root,
            source="router.apply_controller_action",
            error_message=str(exc),
            action_type=action_type,
            payload=payload,
        )
        if blocker:
            raise RouterError(str(exc), control_blocker=blocker) from exc
        raise


def run_until_wait(project_root: Path, *, max_steps: int = 50, new_invocation: bool = False) -> dict[str, Any]:
    if max_steps < 1:
        raise RouterError("run-until-wait requires max_steps >= 1")
    applied_actions: list[dict[str, Any]] = []
    start_new = new_invocation
    for _ in range(max_steps):
        action = next_action(project_root, new_invocation=start_new)
        start_new = False
        action_type = str(action.get("action_type") or "")
        action_crosses_boundary = (
            action_type not in SAFE_RUN_UNTIL_WAIT_ACTION_TYPES
            or bool(action.get("requires_user"))
            or bool(action.get("requires_payload"))
            or bool(action.get("requires_user_dialog_display_confirmation"))
            or bool(action.get("requires_host_spawn"))
            or bool(action.get("requires_host_automation"))
            or bool(action.get("card_id"))
        )
        if action_crosses_boundary:
            result = dict(action)
            result["folded_command"] = "run-until-wait"
            result["folded_applied_count"] = len(applied_actions)
            result["folded_applied_actions"] = applied_actions
            result["folded_stop_reason"] = "requires_user_host_or_role_boundary"
            return result
        applied = apply_action(project_root, action_type, {})
        applied_actions.append({"action_type": action_type, "result": applied})
        if applied.get("waiting") or applied.get("terminal"):
            result = dict(applied)
            result["folded_command"] = "run-until-wait"
            result["folded_applied_count"] = len(applied_actions)
            result["folded_applied_actions"] = applied_actions
            result["folded_stop_reason"] = "terminal_or_waiting_action_applied"
            return result
    raise RouterError("run-until-wait reached max_steps before a wait boundary")


def _repair_role_output_envelope_hashes(project_root: Path, run_root: Path) -> int:
    repaired = 0
    for path in sorted(run_root.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        envelope = payload.get("_role_output_envelope")
        if not isinstance(envelope, dict):
            continue
        body_path = envelope.get("body_path")
        if not isinstance(body_path, str):
            continue
        resolved = resolve_project_path(project_root, body_path)
        if not resolved.exists():
            continue
        raw_hash, semantic_hash = _role_output_hashes(resolved)
        replay_hash = semantic_hash or raw_hash
        accepted_hashes = {raw_hash}
        accepted_hashes.update(_role_output_semantic_hashes(resolved))
        if envelope.get("body_hash") not in accepted_hashes and resolved.resolve() == path.resolve():
            payload.update(
                _role_output_envelope_record_for_mutable_artifact(
                    project_root,
                    run_root,
                    path,
                    payload,
                    reason="reconcile_mutable_artifact_role_output_hash",
                )
            )
            write_json(path, payload)
            repaired += 1
            continue
        if (
            envelope.get("body_hash") == replay_hash
            and envelope.get("body_raw_sha256") == raw_hash
            and envelope.get("body_semantic_sha256") == semantic_hash
        ):
            continue
        envelope["body_hash"] = replay_hash
        envelope["body_raw_sha256"] = raw_hash
        envelope["body_semantic_sha256"] = semantic_hash
        payload["_role_output_envelope"] = envelope
        write_json(path, payload)
        repaired += 1
    return repaired


def _reconciled_card_delivery_context(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    delivery: dict[str, Any],
    manifest: dict[str, Any],
    entries: dict[str, dict[str, str]],
) -> dict[str, Any] | None:
    card_id = str(delivery.get("card_id") or "")
    if card_id not in CARD_PHASE_BY_ID and card_id not in CARD_REQUIRED_SOURCE_PATHS:
        return None
    entry = entries.get(card_id)
    if entry is None:
        return None
    card = manifest_card(manifest, card_id)
    previous = delivery.get("delivery_context") if isinstance(delivery.get("delivery_context"), dict) else {}
    context = _live_card_delivery_context(project_root, run_root, run_state, entry, card)
    context["context_reconciled_at"] = utc_now()
    context["context_reconciled_reason"] = "current_run_state_reconciliation"
    if isinstance(previous, dict):
        context["original_current_stage"] = previous.get("current_stage")
    return context


def _repair_prompt_delivery_contexts(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> int:
    manifest = load_manifest_from_run(run_root)
    entries = {entry["card_id"]: entry for entry in SYSTEM_CARD_SEQUENCE}
    repaired = 0

    def repair_list(deliveries: list[Any]) -> int:
        count = 0
        for delivery in deliveries:
            if not isinstance(delivery, dict):
                continue
            context = _reconciled_card_delivery_context(project_root, run_root, run_state, delivery, manifest, entries)
            if context is None:
                continue
            if delivery.get("delivery_context") != context:
                delivery["delivery_context"] = context
                count += 1
        return count

    repaired += repair_list(run_state.setdefault("delivered_cards", []))
    ledger_path = run_root / "prompt_delivery_ledger.json"
    ledger = read_json_if_exists(ledger_path)
    deliveries = ledger.get("deliveries") if isinstance(ledger.get("deliveries"), list) else []
    ledger_repairs = repair_list(deliveries)
    if ledger_repairs:
        ledger["deliveries"] = deliveries
        ledger["updated_at"] = utc_now()
        write_json(ledger_path, ledger)
    return repaired + ledger_repairs


def _sync_current_and_index_status(project_root: Path, run_state: dict[str, Any]) -> None:
    now = utc_now()
    current_path = project_root / ".flowpilot" / "current.json"
    current = read_json_if_exists(current_path) or {}
    if current.get("current_run_id") == run_state.get("run_id"):
        current["status"] = run_state.get("status") or current.get("status")
        current["updated_at"] = now
        write_json(current_path, current)
    index_path = project_root / ".flowpilot" / "index.json"
    index = read_json_if_exists(index_path) or {}
    runs = index.get("runs") if isinstance(index.get("runs"), list) else []
    for item in runs:
        if isinstance(item, dict) and item.get("run_id") == run_state.get("run_id"):
            item["status"] = run_state.get("status") or item.get("status")
            item["updated_at"] = now
    if runs:
        index["runs"] = runs
        index["updated_at"] = now
        write_json(index_path, index)


def reconcile_current_run(project_root: Path) -> dict[str, Any]:
    bootstrap = load_bootstrap_state(project_root, create_if_missing=False)
    run_state, run_root = load_run_state(project_root, bootstrap)
    if run_state is None or run_root is None:
        raise RouterError("run state is missing")
    repaired: dict[str, Any] = {
        "prompt_delivery_contexts": 0,
        "role_output_envelope_hashes": 0,
        "terminal_lifecycle": False,
        "non_current_running_index_entries": 0,
    }
    status = str(run_state.get("status") or "")
    flags = run_state.setdefault("flags", {})
    if status == "stopped_by_user":
        flags["run_stopped_by_user"] = True
    elif status == "cancelled_by_user":
        flags["run_cancelled_by_user"] = True
    mode = _terminal_lifecycle_mode(run_state)
    if mode:
        run_state["status"] = mode
        run_state["phase"] = "terminal"
        run_state["holder"] = "controller"
        run_state["pending_action"] = None
        _reconcile_terminal_lifecycle_authorities(
            project_root,
            run_root,
            run_state,
            mode=mode,
            event="reconcile_current_run",
        )
        _sync_current_and_index_status(project_root, run_state)
        repaired["terminal_lifecycle"] = True
    repaired["prompt_delivery_contexts"] = _repair_prompt_delivery_contexts(project_root, run_root, run_state)
    repaired["role_output_envelope_hashes"] = _repair_role_output_envelope_hashes(project_root, run_root)
    _refresh_route_memory(project_root, run_root, run_state, trigger="reconcile_current_run")
    repaired["non_current_running_index_entries"] = _reconcile_non_current_running_index_entries(project_root, run_state)
    _sync_derived_run_views(project_root, run_root, run_state, reason="reconcile_current_run")
    append_history(run_state, "router_reconciled_current_run", repaired)
    save_run_state(run_root, run_state)
    return {
        "ok": True,
        "run_id": run_state.get("run_id"),
        "run_root": project_relative(project_root, run_root),
        "repaired": repaired,
    }


def write_role_output_envelope(
    project_root: Path,
    *,
    output_path: str,
    body: dict[str, Any] | None = None,
    body_file: str | None = None,
    path_key: str = "report_path",
    hash_key: str = "report_hash",
    event_name: str | None = None,
    from_role: str | None = None,
    to_role: str = "controller",
) -> dict[str, Any]:
    if path_key not in {"body_path", "report_path", "decision_path", "result_body_path"}:
        raise RouterError(f"unsupported role envelope path key: {path_key}")
    if hash_key not in {"body_hash", "report_hash", "decision_hash", "result_body_hash"}:
        raise RouterError(f"unsupported role envelope hash key: {hash_key}")
    path = resolve_project_path(project_root, output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if body_file:
        source_path = resolve_project_path(project_root, body_file)
        if not source_path.exists():
            raise RouterError(f"role output body file is missing: {body_file}")
        path.write_bytes(source_path.read_bytes())
    elif body is not None:
        write_json(path, body)
    elif not path.exists():
        raise RouterError("role output envelope requires body-json, body-file, or an existing output path")
    raw_hash, semantic_hash = _role_output_hashes(path)
    body_hash = semantic_hash or raw_hash
    envelope = {
        "schema_version": ROLE_OUTPUT_ENVELOPE_SCHEMA,
        path_key: project_relative(project_root, path),
        hash_key: body_hash,
        "controller_visibility": "role_output_envelope_only",
        "chat_response_body_allowed": False,
        "from_role": from_role,
        "to_role": to_role,
    }
    if event_name:
        envelope["event_name"] = event_name
    return envelope


def _artifact_issue(field: str, message: str, repair_owner: str = "project_manager") -> dict[str, str]:
    return {"field": field, "message": message, "repair_owner": repair_owner}


def _validate_hash_if_present(project_root: Path, payload: dict[str, Any], path_key: str, hash_key: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    raw_path = payload.get(path_key)
    raw_hash = payload.get(hash_key)
    if not raw_path:
        issues.append(_artifact_issue(path_key, "missing required path field", "artifact_author"))
        return issues
    path = resolve_project_path(project_root, str(raw_path))
    if not path.exists():
        issues.append(_artifact_issue(path_key, f"path does not exist: {raw_path}", "artifact_author"))
        return issues
    if not raw_hash:
        issues.append(_artifact_issue(hash_key, "missing required sha256 hash field", "artifact_author"))
        return issues
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != str(raw_hash):
        issues.append(_artifact_issue(hash_key, "hash does not match file content", "artifact_author"))
    return issues


def _validate_role_output_hash_if_present(project_root: Path, payload: dict[str, Any], path_key: str, hash_key: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    raw_path = payload.get(path_key)
    raw_hash = payload.get(hash_key)
    if not raw_path:
        issues.append(_artifact_issue(path_key, "missing required path field", "artifact_author"))
        return issues
    path = resolve_project_path(project_root, str(raw_path))
    if not path.exists():
        issues.append(_artifact_issue(path_key, f"path does not exist: {raw_path}", "artifact_author"))
        return issues
    if not raw_hash:
        issues.append(_artifact_issue(hash_key, "missing required sha256 hash field", "artifact_author"))
        return issues
    actual, semantic = _role_output_hashes(path)
    accepted = {actual}
    accepted.update(_role_output_semantic_hashes(path))
    if str(raw_hash) not in accepted:
        issues.append(_artifact_issue(hash_key, "hash does not match role output content", "artifact_author"))
    return issues


def validate_artifact(project_root: Path, artifact_type: str, artifact_path: str) -> dict[str, Any]:
    path = resolve_project_path(project_root, artifact_path)
    payload = read_json(path)
    issues: list[dict[str, str]] = []
    if artifact_type == "node_acceptance_plan":
        required_top = ("schema_version", "run_id", "route_id", "route_version", "node_id", "node_requirements", "experiment_plan", "high_standard_recheck", "prior_path_context_review")
        for field in required_top:
            if field not in payload or payload.get(field) in (None, "", []):
                issues.append(_artifact_issue(field, "missing required field", "project_manager"))
        high_standard = payload.get("high_standard_recheck") if isinstance(payload.get("high_standard_recheck"), dict) else {}
        for field in (
            "ideal_outcome",
            "unacceptable_outcomes",
            "higher_standard_opportunities",
            "semantic_downgrade_risks",
            "decision",
            "why_current_plan_meets_highest_reasonable_standard",
        ):
            if field not in high_standard or high_standard.get(field) in (None, "", []):
                issues.append(_artifact_issue(f"high_standard_recheck.{field}", "missing required field", "project_manager"))
        prior = payload.get("prior_path_context_review") if isinstance(payload.get("prior_path_context_review"), dict) else {}
        for field in (
            "reviewed",
            "source_paths",
            "completed_nodes_considered",
            "superseded_nodes_considered",
            "stale_evidence_considered",
            "prior_blocks_or_experiments_considered",
            "impact_on_decision",
        ):
            if field not in prior:
                issues.append(_artifact_issue(f"prior_path_context_review.{field}", "missing required field", "project_manager"))
    elif artifact_type == "packet_envelope":
        envelope = packet_runtime.normalize_envelope_aliases(payload)
        for field in ("schema_version", "packet_id", "from_role", "to_role", "node_id", "body_path", "body_hash", "body_visibility"):
            if field not in envelope or envelope.get(field) in (None, ""):
                issues.append(_artifact_issue(field, "missing required packet envelope field", str(envelope.get("from_role") or "project_manager")))
        if envelope.get("body_visibility") != packet_runtime.SEALED_BODY_VISIBILITY:
            issues.append(_artifact_issue("body_visibility", "packet body must stay sealed to target role", str(envelope.get("from_role") or "project_manager")))
        issues.extend(_validate_hash_if_present(project_root, envelope, "body_path", "body_hash"))
    elif artifact_type == "result_envelope":
        envelope = packet_runtime.normalize_envelope_aliases(payload)
        for field in ("schema_version", "packet_id", "completed_by_role", "result_body_path", "result_body_hash", "next_recipient", "body_visibility"):
            if field not in envelope or envelope.get(field) in (None, ""):
                issues.append(_artifact_issue(field, "missing required result envelope field", str(envelope.get("completed_by_role") or "worker")))
        if envelope.get("completed_by_role") == "controller":
            issues.append(_artifact_issue("completed_by_role", "Controller cannot author current-node results", "worker"))
        if envelope.get("body_visibility") != packet_runtime.SEALED_BODY_VISIBILITY:
            issues.append(_artifact_issue("body_visibility", "result body must stay sealed to reviewer/PM recipient", str(envelope.get("completed_by_role") or "worker")))
        issues.extend(_validate_hash_if_present(project_root, envelope, "result_body_path", "result_body_hash"))
    elif artifact_type == "role_output_envelope":
        path_keys = ("body_path", "report_path", "decision_path", "result_body_path", "memo_path", "architecture_path", "contract_path", "manifest_path", "route_path", "draft_path", "plan_path", "package_path", "ledger_path")
        found = False
        for path_key in path_keys:
            if payload.get(path_key):
                hash_key = path_key[:-5] + "_hash" if path_key.endswith("_path") else f"{path_key}_hash"
                found = True
                if payload.get(hash_key):
                    issues.extend(_validate_role_output_hash_if_present(project_root, payload, path_key, hash_key))
        if not found:
            issues.append(_artifact_issue("path", "role output envelope must include a known artifact path field", str(payload.get("from_role") or "role")))
        if not payload.get("from_role"):
            issues.append(_artifact_issue("from_role", "missing producing role", "role"))
        if not payload.get("to_role"):
            issues.append(_artifact_issue("to_role", "missing recipient role", "role"))
    elif artifact_type == "gate_decision":
        decision = payload.get("gate_decision") if isinstance(payload.get("gate_decision"), dict) else payload
        issues.extend(_gate_decision_issues(project_root, decision))
    else:
        raise RouterError(f"unsupported artifact validation type: {artifact_type}")
    return {
        "ok": not issues,
        "artifact_type": artifact_type,
        "artifact_path": project_relative(project_root, path),
        "issue_count": len(issues),
        "errors": issues,
        "next_action": None if not issues else f"repair_{artifact_type}",
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FlowPilot prompt-isolated router.")
    parser.add_argument("--root", default=".", help="Project root containing .flowpilot")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    sub = parser.add_subparsers(dest="command", required=True)
    next_parser = sub.add_parser("next", help="Return the next router-authorized action")
    next_parser.add_argument("--new-invocation", action="store_true", help="Start a fresh formal FlowPilot invocation")
    next_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    run_wait_parser = sub.add_parser("run-until-wait", help="Apply safe internal router actions and return the next wait-boundary action")
    run_wait_parser.add_argument("--max-steps", type=int, default=50)
    run_wait_parser.add_argument("--new-invocation", action="store_true", help="Start a fresh formal FlowPilot invocation")
    run_wait_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    apply_parser = sub.add_parser("apply", help="Apply a pending router action")
    apply_parser.add_argument("--action-type", required=True)
    apply_parser.add_argument("--payload-json", default="")
    apply_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    event_parser = sub.add_parser("record-event", help="Record a PM/reviewer/worker external event")
    event_parser.add_argument("--event", required=True)
    event_parser.add_argument("--payload-json", default="")
    event_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    envelope_parser = sub.add_parser("role-output-envelope", help="Write a role output body and return a controller-visible envelope")
    envelope_parser.add_argument("--output-path", required=True)
    envelope_parser.add_argument("--body-json", default="")
    envelope_parser.add_argument("--body-file", default="")
    envelope_parser.add_argument("--path-key", default="report_path")
    envelope_parser.add_argument("--hash-key", default="report_hash")
    envelope_parser.add_argument("--event-name", default="")
    envelope_parser.add_argument("--from-role", default="")
    envelope_parser.add_argument("--to-role", default="controller")
    envelope_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    validate_parser = sub.add_parser("validate-artifact", help="Validate a FlowPilot artifact before or during record-event")
    validate_parser.add_argument("--type", required=True, choices=["node_acceptance_plan", "packet_envelope", "result_envelope", "role_output_envelope", "gate_decision"])
    validate_parser.add_argument("--path", required=True)
    validate_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    reconcile_parser = sub.add_parser("reconcile-run", help="Rebuild derived indexes and live-run views for the current run")
    reconcile_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    state_parser = sub.add_parser("state", help="Print bootstrap and current run router state")
    state_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = Path(args.root).resolve()
    try:
        if args.command == "next":
            result = next_action(root, new_invocation=bool(getattr(args, "new_invocation", False)))
        elif args.command == "run-until-wait":
            result = run_until_wait(
                root,
                max_steps=int(args.max_steps),
                new_invocation=bool(getattr(args, "new_invocation", False)),
            )
        elif args.command == "apply":
            payload = json.loads(args.payload_json) if args.payload_json else {}
            result = apply_action(root, args.action_type, payload)
        elif args.command == "record-event":
            payload = json.loads(args.payload_json) if args.payload_json else {}
            result = record_external_event(root, args.event, payload)
        elif args.command == "role-output-envelope":
            body = json.loads(args.body_json) if args.body_json else None
            result = write_role_output_envelope(
                root,
                output_path=args.output_path,
                body=body,
                body_file=args.body_file or None,
                path_key=args.path_key,
                hash_key=args.hash_key,
                event_name=args.event_name or None,
                from_role=args.from_role or None,
                to_role=args.to_role,
            )
        elif args.command == "validate-artifact":
            result = validate_artifact(root, args.type, args.path)
        elif args.command == "reconcile-run":
            result = reconcile_current_run(root)
        elif args.command == "state":
            bootstrap = load_bootstrap_state(root, create_if_missing=False)
            run_state, run_root = load_run_state(root, bootstrap)
            active_ui_task_catalog = (
                _active_ui_task_catalog(root, run_root, run_state)
                if run_state is not None and run_root is not None
                else {"schema_version": "flowpilot.active_ui_task_catalog.v1", "active_tasks": []}
            )
            result = {
                "bootstrap": bootstrap,
                "run_root": str(run_root) if run_root else None,
                "run_state": run_state,
                "active_ui_task_catalog": active_ui_task_catalog,
            }
        else:
            raise RouterError(f"unknown command: {args.command}")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        error = {"ok": False, "error": str(exc)}
        control_blocker = getattr(exc, "control_blocker", None)
        if isinstance(control_blocker, dict):
            error["control_blocker"] = control_blocker
            error["blocker_artifact_path"] = control_blocker.get("blocker_artifact_path")
            error["handling_lane"] = control_blocker.get("handling_lane")
            error["controller_instruction"] = control_blocker.get("controller_instruction")
            if isinstance(control_blocker.get("skill_observation_reminder"), dict):
                error["skill_observation_reminder"] = control_blocker["skill_observation_reminder"]
        if "skill_observation_reminder" not in error and args.command in {"apply", "record-event"}:
            error["skill_observation_reminder"] = _skill_observation_reminder(
                str(exc),
                event=getattr(args, "event", None),
                action_type=getattr(args, "action_type", None),
            )
        print(json.dumps(error, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
