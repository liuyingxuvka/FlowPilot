"""Protocol catalogs and declarative router tables for FlowPilot."""

from __future__ import annotations

from typing import Any, Iterable

import flowpilot_runtime_closure
import packet_runtime
import role_output_runtime

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
BLOCKER_REPAIR_POLICY_SCHEMA = "flowpilot.blocker_repair_policy.v1"
REPAIR_TRANSACTION_SCHEMA = "flowpilot.repair_transaction.v1"
REPAIR_TRANSACTION_INDEX_SCHEMA = "flowpilot.repair_transaction_index.v1"
ROLE_RECOVERY_TRANSACTION_SCHEMA = "flowpilot.role_recovery_transaction.v1"
ROLE_RECOVERY_REPORT_SCHEMA = "flowpilot.role_recovery_report.v1"
ROLE_RECOVERY_OBLIGATION_REPLAY_SCHEMA = "flowpilot.role_recovery_obligation_replay.v1"
CONTROL_TRANSACTION_REGISTRY_SCHEMA = "flowpilot.control_transaction_registry.v1"
ROUTE_ACTION_POLICY_REGISTRY_SCHEMA = "flowpilot.route_action_policy_registry.v1"
ROLE_OUTPUT_ENVELOPE_SCHEMA = "flowpilot.role_output_envelope.v1"
EVENT_ENVELOPE_SCHEMA = "flowpilot.event_envelope.v1"
LIVE_CARD_CONTEXT_SCHEMA = "flowpilot.live_card_context.v1"
PAYLOAD_CONTRACT_SCHEMA = "flowpilot.payload_contract.v1"
GATE_DECISION_SCHEMA = "flowpilot.gate_decision.v1"
GATE_DECISION_RECORD_SCHEMA = "flowpilot.gate_decision_record.v1"
GATE_DECISION_LEDGER_SCHEMA = "flowpilot.gate_decision_ledger.v1"
PM_SUGGESTION_LEDGER_ENTRY_SCHEMA = "flowpilot.pm_suggestion_item.v1"
SELF_INTERROGATION_INDEX_SCHEMA = "flowpilot.self_interrogation_index.v1"
SELF_INTERROGATION_RECORD_SCHEMA = "flowpilot.self_interrogation_record.v1"
PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT = "pm_records_control_blocker_repair_decision"
PM_CONTROL_BLOCKER_FOLLOWUP_BLOCKER_EVENT = "pm_records_control_blocker_followup_blocker"
PM_CONTROL_BLOCKER_PROTOCOL_BLOCKER_EVENT = "pm_records_control_blocker_protocol_blocker"
PM_PARENT_PROTOCOL_BLOCKER_EVENT = "pm_records_parent_protocol_blocker"
PM_MODEL_MISS_TRIAGE_DECISION_EVENT = "pm_records_model_miss_triage_decision"
PM_ROLE_WORK_REQUEST_EVENT = "pm_registers_role_work_request"
ROLE_WORK_RESULT_RETURNED_EVENT = "role_work_result_returned"
PM_ROLE_WORK_RESULT_DECISION_EVENT = "pm_records_role_work_result_decision"
GATE_DECISION_EVENT = "role_records_gate_decision"
EVENT_IDEMPOTENCY_LEDGER_SCHEMA = "flowpilot.external_event_idempotency.v1"
DISPLAY_CONFIRMATION_SCHEMA = "flowpilot.user_dialog_display_confirmation.v1"
DISPLAY_SURFACE_RECEIPT_SCHEMA = "flowpilot.display_surface_receipt.v1"
CURRENT_STATUS_SUMMARY_SCHEMA = "flowpilot.current_status_summary.v1"
OFFICER_REQUEST_LIFECYCLE_INDEX_SCHEMA = flowpilot_runtime_closure.OFFICER_REQUEST_LIFECYCLE_INDEX_SCHEMA
CONTINUATION_QUARANTINE_SCHEMA = flowpilot_runtime_closure.CONTINUATION_QUARANTINE_SCHEMA
FINAL_USER_REPORT_SCHEMA = flowpilot_runtime_closure.FINAL_USER_REPORT_SCHEMA
ROUTE_DISPLAY_REFRESH_SCHEMA = flowpilot_runtime_closure.ROUTE_DISPLAY_REFRESH_SCHEMA
CONTROLLER_USER_REPORTING_POLICY_SCHEMA = "flowpilot.controller_user_reporting_policy.v1"
DETERMINISTIC_BOOTSTRAP_SEED_EVIDENCE_SCHEMA = "flowpilot.deterministic_bootstrap_seed_evidence.v1"
FOREGROUND_CONTROLLER_STANDBY_SCHEMA = "flowpilot.foreground_controller_standby.v1"
CONTROLLER_PATROL_TIMER_SCHEMA = "flowpilot.controller_patrol_timer.v1"
CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE = role_output_runtime.CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE
CONTROLLER_BOUNDARY_CONFIRMATION_CONTRACT_ID = role_output_runtime.CONTROLLER_BOUNDARY_CONFIRMATION_CONTRACT_ID
CONTROLLER_STATEFUL_VALIDATOR_TABLE = {
    "confirm_controller_core_boundary": {
        "validator": "controller_boundary_confirmation_context",
        "postcondition": "controller_role_confirmed",
        "deliverable_id": "controller_boundary_confirmation",
        "artifact_kind": "controller_boundary_confirmation",
        "runtime_channel": "role_output_runtime",
        "output_type": CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE,
        "output_contract_id": CONTROLLER_BOUNDARY_CONFIRMATION_CONTRACT_ID,
    },
}
STARTUP_MECHANICAL_AUDIT_SCHEMA = "flowpilot.startup_mechanical_audit.v1"
ROUTER_OWNED_CHECK_PROOF_SCHEMA = "flowpilot.router_owned_check_proof.v1"
CONTROLLER_BOUNDARY_CONFIRMATION_SCHEMA = role_output_runtime.CONTROLLER_BOUNDARY_CONFIRMATION_SCHEMA
STARTUP_ANSWER_PROVENANCE = "explicit_user_reply"
STARTUP_ANSWER_INTERPRETATION_PROVENANCE = "ai_interpreted_from_explicit_user_reply"
STARTUP_ANSWER_INTERPRETATION_SCHEMA = "flowpilot.startup_answer_interpretation.v1"
STARTUP_INTAKE_RESULT_SCHEMA = "flowpilot.startup_intake_result.v1"
STARTUP_INTAKE_RECEIPT_SCHEMA = "flowpilot.startup_intake_receipt.v1"
STARTUP_INTAKE_ENVELOPE_SCHEMA = "flowpilot.startup_intake_envelope.v1"
STARTUP_INTAKE_RECORD_SCHEMA = "flowpilot.startup_intake_record.v1"
STARTUP_INTAKE_INTERACTIVE_LAUNCH_MODE = "interactive_native"
USER_REQUEST_REF_SCHEMA = "flowpilot.user_request_ref.v1"
USER_REQUEST_PROVENANCE = "explicit_user_request"
DISPLAY_CONFIRMATION_PROVENANCE = "controller_user_dialog_render"
DISPLAY_CONFIRMATION_TARGET = "user_dialog"
ROUTER_TRUSTED_PROOF_SOURCES = {"router_computed", "packet_runtime_hash", "host_receipt"}


ALLOWED_RECORD_EVENT_ENVELOPE_SCHEMAS = {
    EVENT_ENVELOPE_SCHEMA,
    ROLE_OUTPUT_ENVELOPE_SCHEMA,
}
ALLOWED_RECORD_EVENT_CONTROLLER_VISIBILITIES = {
    "event_envelope_only",
    "role_output_envelope_only",
    "packet_envelope_only",
    "result_envelope_only",
    "packet_and_result_envelopes_only",
    "control_event_envelope_only",
}
FORBIDDEN_RECORD_EVENT_ENVELOPE_BODY_FIELDS = {
    "blockers",
    "checks",
    "commands",
    "decision",
    "decision_body",
    "evidence",
    "findings",
    "passed",
    "recommendations",
    "repair_instructions",
    "report_body",
    "result_body",
}
ROLE_AGENT_SPAWN_RESULT = "spawned_fresh_for_task"
ROLE_AGENT_REHYDRATION_RESULT = "rehydrated_from_current_run_memory"
ROLE_AGENT_CONTINUITY_RESULT = "live_agent_continuity_confirmed"
ROLE_AGENT_OLD_RESTORE_RESULT = "old_agent_restored"
ROLE_AGENT_TARGETED_REPLACEMENT_RESULT = "targeted_replacement_spawned"
ROLE_AGENT_FULL_CREW_RECYCLE_RESULT = "full_crew_recycle_spawned"
ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT = "environment_blocked"
BACKGROUND_ROLE_MODEL_POLICY = "strongest_available"
BACKGROUND_ROLE_REASONING_EFFORT_POLICY = "highest_available"
BACKGROUND_ROLE_PREFERRED_REASONING_EFFORT = "xhigh"
RESUME_ROLE_AGENT_RESULTS = {ROLE_AGENT_REHYDRATION_RESULT, ROLE_AGENT_CONTINUITY_RESULT}
ROLE_RECOVERY_RESULTS = {
    ROLE_AGENT_OLD_RESTORE_RESULT,
    ROLE_AGENT_TARGETED_REPLACEMENT_RESULT,
    ROLE_AGENT_FULL_CREW_RECYCLE_RESULT,
    ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT,
}
ROLE_AGENT_HOST_LIVENESS_STATUSES = {"active", "completed", "missing", "cancelled", "timeout_unknown", "unknown"}
ROLE_AGENT_BOUNDED_WAIT_RESULTS = {"not_waited", "completed", "timeout_unknown"}
ROLE_AGENT_LIVENESS_DECISIONS = {"confirmed_existing_agent", "spawned_replacement_from_current_run_memory"}
ROLE_AGENT_LIVENESS_PROBE_MODE = "concurrent_batch"
CONTROL_BLOCKER_LANES = {
    "control_plane_reissue",
    "pm_repair_decision_required",
    "fatal_protocol_violation",
}
PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES = {
    "pm_repair_decision_required",
    "fatal_protocol_violation",
}
PM_BLOCKER_RECOVERY_OPTIONS = (
    "same_gate_repair",
    "rollback_to_prior_gate",
    "supplemental_node",
    "repair_node",
    "route_mutation",
    "evidence_quarantine",
    "allowed_waiver",
    "user_stop",
    "protocol_dead_end",
)
REPAIR_TRANSACTION_EXECUTABLE_PLAN_KINDS = {
    "operation_replay",
    "controller_repair_work_packet",
    "packet_reissue",
    "role_reissue",
    "router_internal_reconcile",
    "await_existing_event",
    "route_mutation",
    "terminal_stop",
}
REPAIR_TRANSACTION_LEGACY_PLAN_KIND_ALIASES = {
    "event_replay": "await_existing_event",
}
REPAIR_TRANSACTION_SAFE_REPLAY_ACTION_TYPES = {
    "deliver_mail",
    "deliver_system_card",
    "deliver_system_card_bundle",
    "relay_material_scan_packets",
    "relay_research_packets",
    "relay_current_node_packet",
    "relay_material_scan_results_to_pm",
    "relay_current_node_result_to_pm",
    "relay_research_results_to_pm",
}
BLOCKER_REPAIR_POLICY_ROWS: dict[str, dict[str, Any]] = {
    "mechanical_control_plane_reissue": {
        "policy_row_id": "mechanical_control_plane_reissue",
        "blocker_family": "mechanical_control_plane",
        "first_handler": "responsible_role",
        "direct_retry_budget": 2,
        "escalate_to": "project_manager",
        "pm_recovery_options": PM_BLOCKER_RECOVERY_OPTIONS,
        "return_policy": {
            "requires_named_return_gate": True,
            "default_return_gate": "originating_event",
            "blocked_gate_may_not_be_marked_passed_directly": True,
        },
        "hard_stop_conditions": [],
        "controller_boundary": "deliver policy row and sealed repair packet only; do not open sealed bodies or decide project substance",
    },
    "pm_semantic_repair": {
        "policy_row_id": "pm_semantic_repair",
        "blocker_family": "semantic_or_route_repair",
        "first_handler": "project_manager",
        "direct_retry_budget": 0,
        "escalate_to": "project_manager",
        "pm_recovery_options": PM_BLOCKER_RECOVERY_OPTIONS,
        "return_policy": {
            "requires_named_return_gate": True,
            "default_return_gate": "pm_selected_gate",
            "blocked_gate_may_not_be_marked_passed_directly": True,
        },
        "hard_stop_conditions": [],
        "controller_boundary": "deliver blocker metadata only and wait for PM recovery decision",
    },
    "fatal_protocol_violation": {
        "policy_row_id": "fatal_protocol_violation",
        "blocker_family": "fatal_protocol_violation",
        "first_handler": "project_manager",
        "direct_retry_budget": 0,
        "escalate_to": "project_manager",
        "pm_recovery_options": (
            "same_gate_repair",
            "rollback_to_prior_gate",
            "route_mutation",
            "evidence_quarantine",
            "user_stop",
            "protocol_dead_end",
        ),
        "return_policy": {
            "requires_named_return_gate": True,
            "default_return_gate": "pm_selected_safe_recovery_gate",
            "blocked_gate_may_not_be_marked_passed_directly": True,
        },
        "hard_stop_conditions": [
            "controller_body_access",
            "private_role_to_role_relay",
            "contaminated_evidence",
        ],
        "controller_boundary": "stop normal route work and deliver sealed repair packet envelope to PM",
    },
    "self_interrogation_repair": {
        "policy_row_id": "self_interrogation_repair",
        "blocker_family": "self_interrogation_disposition",
        "first_handler": "project_manager",
        "direct_retry_budget": 0,
        "escalate_to": "project_manager",
        "pm_recovery_options": (
            "rerun_self_interrogation",
            "record_disposition",
            "convert_findings_to_repair",
            "same_gate_repair",
            "rollback_to_prior_gate",
            "supplemental_node",
            "route_mutation",
            "evidence_quarantine",
            "allowed_waiver",
            "user_stop",
        ),
        "return_policy": {
            "requires_named_return_gate": True,
            "default_return_gate": "blocked_self_interrogation_gate",
            "blocked_gate_may_not_be_marked_passed_directly": True,
        },
        "hard_stop_conditions": [
            "unresolved_hard_current_findings_require_repair_or_authorized_waiver",
        ],
        "controller_boundary": "deliver blocker metadata to PM; do not rerun grill-me or decide finding disposition",
    },
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
PM_ROLE_WORK_REQUEST_INDEX_SCHEMA = "flowpilot.pm_role_work_request_index.v1"
PM_ROLE_WORK_REQUEST_SCHEMA = "flowpilot.pm_role_work_request.v1"
PM_ROLE_WORK_RESULT_DECISION_SCHEMA = "flowpilot.pm_role_work_result_decision.v1"
PARALLEL_PACKET_BATCH_SCHEMA = "flowpilot.parallel_packet_batch.v1"
PARALLEL_PACKET_BATCH_REF_SCHEMA = "flowpilot.parallel_packet_batch_ref.v1"
PM_ROLE_WORK_REQUEST_RECIPIENT_ROLES = {
    "human_like_reviewer",
    "process_flowguard_officer",
    "product_flowguard_officer",
    "worker_a",
    "worker_b",
}
PM_ROLE_WORK_REQUEST_MODES = {"blocking", "advisory", "prep-only"}
PM_ROLE_WORK_REQUEST_KINDS = {
    "model_miss",
    "evidence",
    "review",
    "implementation",
    "research",
    "model_update",
    "model_check",
    "other",
}
PM_ROLE_WORK_OPEN_STATUSES = {
    "open",
    "packet_created",
    "packet_relayed",
    "result_returned",
    "result_relayed_to_pm",
}
PM_ROLE_WORK_TERMINAL_DECISIONS = {"absorbed", "canceled", "superseded"}
PM_PACKAGE_RESULT_DECISIONS = {
    "absorbed",
    "rework_requested",
    "canceled",
    "blocked",
    "route_or_node_mutation_required",
}
PARALLEL_PACKET_BATCH_OPEN_STATUSES = {
    "registered",
    "packets_relayed",
    "partial_results_returned",
    "results_joined",
    "results_relayed_to_reviewer",
    "results_relayed_to_pm",
    "reviewed",
}
PARALLEL_PACKET_BATCH_RESULT_RETURNED_STATUSES = {
    "result_returned",
    "result_relayed_to_pm",
    "result_relayed_to_reviewer",
    "reviewed",
    "absorbed",
}
PARALLEL_PACKET_BATCH_RESULT_FINAL_STATUSES = {
    "results_relayed_to_pm",
    "results_relayed_to_reviewer",
    "reviewed",
    "review_blocked",
    "pm_absorbed",
    "absorbed",
    "canceled",
    "blocked",
    "route_or_node_mutation_required",
}
PROCESS_CONTRACT_BINDINGS: dict[str, dict[str, Any]] = {
    "current_node_work": {
        "task_family": "worker.current_node",
        "contract_id": "flowpilot.output_contract.worker_current_node_result.v1",
        "packet_type": "work_packet",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
    "pm_role_work_request": {
        "task_family": "pm.role_work_request",
        "contract_id": "flowpilot.output_contract.pm_role_work_result.v1",
        "packet_type": "pm_role_work_request",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
    "officer_model_report": {
        "task_family": "officer.model_report",
        "contract_id": "flowpilot.output_contract.officer_model_report.v1",
        "packet_type": "officer_request",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
    "officer_model_miss_report": {
        "task_family": "officer.model_miss_report",
        "contract_id": "flowpilot.output_contract.flowguard_model_miss_report.v1",
        "packet_type": "officer_request",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
    "reviewer_result_review": {
        "task_family": "reviewer.review",
        "contract_id": "flowpilot.output_contract.reviewer_review_report.v1",
        "packet_type": "review_request",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
    "material_scan": {
        "task_family": "worker.material_scan",
        "contract_id": "flowpilot.output_contract.worker_material_scan_result.v1",
        "packet_type": "material_scan",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
    "research": {
        "task_family": "worker.research",
        "contract_id": "flowpilot.output_contract.worker_research_result.v1",
        "packet_type": "research",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
    "control_blocker_repair": {
        "task_family": "pm.control_blocker_repair_decision",
        "contract_id": "flowpilot.output_contract.pm_control_blocker_repair_decision.v1",
        "packet_type": "role_decision",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
    "resume_decision": {
        "task_family": "pm.resume_decision",
        "contract_id": "flowpilot.output_contract.pm_resume_decision.v1",
        "packet_type": "role_decision",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
}
PM_ROLE_WORK_CONTRACT_PROCESS_KINDS = {
    "flowpilot.output_contract.pm_role_work_result.v1": "pm_role_work_request",
    "flowpilot.output_contract.officer_model_report.v1": "officer_model_report",
    "flowpilot.output_contract.flowguard_model_miss_report.v1": "officer_model_miss_report",
}
PM_ROLE_WORK_FOREIGN_CONTRACT_IDS = {
    "flowpilot.output_contract.worker_current_node_result.v1",
    "flowpilot.output_contract.worker_material_scan_result.v1",
    "flowpilot.output_contract.worker_research_result.v1",
}
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
PM_SUGGESTION_FINAL_DISPOSITIONS = {
    "adopt_now",
    "repair_or_reissue",
    "mutate_route",
    "defer_to_named_node",
    "reject_with_reason",
    "waive_with_authority",
    "stop_for_user",
    "record_for_flowpilot_maintenance",
}
PM_SUGGESTION_CLOSURE_STATUSES_BY_DISPOSITION = {
    "adopt_now": {"closed"},
    "repair_or_reissue": {"closed"},
    "mutate_route": {"closed"},
    "defer_to_named_node": {"deferred_to_named_node", "closed"},
    "reject_with_reason": {"closed"},
    "waive_with_authority": {"closed"},
    "stop_for_user": {"stopped_for_user", "closed"},
    "record_for_flowpilot_maintenance": {"closed"},
}
PM_SUGGESTION_WORKER_ROLES = {"worker_a", "worker_b"}
PM_SUGGESTION_OFFICER_ROLES = {"process_flowguard_officer", "product_flowguard_officer"}
SELF_INTERROGATION_SCOPES = {
    "startup",
    "product_architecture",
    "node_entry",
    "repair",
    "completion",
    "role_result",
}
SELF_INTERROGATION_HARD_SEVERITIES = {"hard_blocker", "current_gate_blocker"}
SELF_INTERROGATION_FINAL_DISPOSITIONS = {
    *PM_SUGGESTION_FINAL_DISPOSITIONS,
    "incorporated_into_artifact",
    "entered_pm_suggestion_ledger",
    "no_action_needed",
}
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
    "role_recovery_requested": False,
    "role_recovery_state_loaded": False,
    "role_recovery_roles_restored": False,
    "role_recovery_report_written": False,
    "role_recovery_environment_blocked": False,
    "role_recovery_obligations_scanned": False,
    "role_recovery_obligation_replay_completed": False,
    "role_recovery_pm_escalation_required": False,
    "role_no_output_reissue_recorded": False,
    "role_no_output_pm_escalation_required": False,
    "continuation_binding_recorded": False,
    "controller_boundary_confirmation_written": False,
    "controller_role_confirmed_from_router_core": False,
    "controller_boundary_recovery_requested": False,
    "startup_mechanical_audit_written": False,
    "startup_pending_mail_suspended_after_dead_end": False,
    "startup_display_status_written": False,
    "route_history_index_refreshed": False,
    "pm_prior_path_context_refreshed": False,
    "material_scan_packets_relayed": False,
    "material_scan_results_relayed_to_reviewer": False,
    "material_scan_results_relayed_to_pm": False,
    "material_scan_result_disposition_recorded": False,
    "material_scan_results_absorbed_by_pm": False,
    "research_packet_relayed": False,
    "research_result_relayed_to_reviewer": False,
    "research_result_relayed_to_pm": False,
    "research_result_disposition_recorded": False,
    "research_result_absorbed_for_review_by_pm": False,
    "current_node_packet_relayed": False,
    "current_node_result_relayed_to_reviewer": False,
    "current_node_result_relayed_to_pm": False,
    "current_node_result_disposition_recorded": False,
    "current_node_result_absorbed_by_pm": False,
    "current_node_write_grant_issued": False,
    "node_completion_ledger_updated": False,
    "task_completion_projection_published": False,
    "pm_role_work_request_registered": False,
    "pm_role_work_request_packet_relayed": False,
    "pm_role_work_result_returned": False,
    "pm_role_work_result_relayed_to_pm": False,
    "pm_role_work_result_absorbed": False,
    "model_miss_triage_followup_request_pending": False,
    "model_miss_triage_controlled_stop_recorded": False,
    "terminal_summary_card_delivered": False,
    "terminal_summary_written": False,
    "formal_router_daemon_started": False,
    "router_daemon_start_failed": False,
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
        "record_user_request",
        "write_user_intake",
        "start_router_daemon",
        "check_prompt_manifest",
        "sync_display_plan",
    }
)

ROUTER_INTERNAL_MECHANICAL_ACTION_TYPES = frozenset(
    {
        "check_prompt_manifest",
        "check_packet_ledger",
        "write_startup_mechanical_audit",
    }
)
ROUTER_INTERNAL_MECHANICAL_MAX_HOPS = 8

ROUTER_READY_PREEMPTION_ACTION_TYPES = frozenset(
    {
        "await_card_return_event",
        "await_card_bundle_return_event",
        "check_card_return_event",
        "check_card_bundle_return_event",
        "deliver_system_card",
        "deliver_system_card_bundle",
    }
)

CURRENT_NODE_CYCLE_FLAGS = (
    "pm_current_node_card_delivered",
    "pm_node_started_event_delivered",
    "pm_node_acceptance_plan_card_delivered",
    "node_acceptance_plan_written",
    "node_acceptance_plan_revised_by_pm",
    "reviewer_node_acceptance_plan_card_delivered",
    "node_acceptance_plan_reviewer_passed",
    "node_acceptance_plan_review_blocked",
    "current_node_packet_registered",
    "current_node_write_grant_issued",
    "current_node_packet_relayed",
    "current_node_worker_result_returned",
    "current_node_result_relayed_to_pm",
    "current_node_result_disposition_recorded",
    "current_node_result_absorbed_by_pm",
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

MODEL_MISS_REVIEW_BLOCK_FLAGS = (
    "node_acceptance_plan_review_blocked",
    "node_review_blocked",
)

MODEL_MISS_REVIEW_BLOCK_EVENTS = (
    "reviewer_blocks_node_acceptance_plan",
    "current_node_reviewer_blocks_result",
)

MODEL_MISS_ROUTE_MUTATION_BLOCK_FLAGS = (
    "node_acceptance_plan_review_blocked",
    "node_review_blocked",
)

# Material dispatch blockers are now router/control-blocker repair outcomes, not
# PM model-miss reviewer-block repair inputs.
MODEL_MISS_MATERIAL_DISPATCH_REPAIR_FLAGS: tuple[str, ...] = ()

MATERIAL_REPAIR_OUTCOME_EVENTS = {
    "router_direct_material_scan_dispatch_recheck_passed",
    "worker_scan_results_returned",
    "router_direct_material_scan_dispatch_recheck_blocked",
    "router_protocol_blocker_material_scan_dispatch_recheck",
}
CONTROL_BLOCKER_REPAIR_NON_SUCCESS_EVENTS = {
    PM_CONTROL_BLOCKER_FOLLOWUP_BLOCKER_EVENT,
    PM_CONTROL_BLOCKER_PROTOCOL_BLOCKER_EVENT,
}
LEAF_CURRENT_NODE_EVENT_CAPABILITY_EVENTS = {
    "pm_registers_current_node_packet",
    "worker_current_node_result_returned",
    "current_node_reviewer_passes_result",
    "current_node_reviewer_blocks_result",
    "pm_completes_current_node_from_reviewed_result",
}
PARENT_REPAIR_SAFE_EVENTS = {
    "pm_builds_parent_backward_targets",
    "reviewer_passes_parent_backward_replay",
    "reviewer_blocks_parent_backward_replay",
    "pm_records_parent_segment_decision",
    "pm_completes_parent_node_from_backward_replay",
    PM_PARENT_PROTOCOL_BLOCKER_EVENT,
}
PARENT_NODE_EVENT_CAPABILITY_EVENTS = PARENT_REPAIR_SAFE_EVENTS

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

SCOPED_EVENT_IDENTITY_POLICIES: dict[str, dict[str, Any]] = {
    "pm_mutates_route_after_review_block": {
        "family": "transaction",
        "dedupe_fields": ("control_blocker_id", "repair_transaction_id", "route_version"),
        "retry_group_fields": ("event", "control_blocker_id", "model_miss_block"),
        "max_distinct_keys_per_retry_group": 3,
    },
    PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT: {
        "family": "transaction",
        "dedupe_fields": ("control_blocker_id", "repair_transaction_id"),
        "retry_group_fields": ("event", "control_blocker_id"),
    },
    **{
        event: {
            "family": "control_blocker_repair_outcome",
            "dedupe_fields": ("control_blocker_id", "repair_transaction_id", "outcome"),
            "retry_group_fields": ("event", "control_blocker_id", "repair_transaction_id"),
        }
        for event in (*sorted(CONTROL_BLOCKER_REPAIR_NON_SUCCESS_EVENTS), PM_PARENT_PROTOCOL_BLOCKER_EVENT)
    },
    PM_ROLE_WORK_REQUEST_EVENT: {
        "family": "pm_role_work_request",
        "dedupe_fields": ("request_id",),
        "retry_group_fields": ("event", "request_id"),
    },
    ROLE_WORK_RESULT_RETURNED_EVENT: {
        "family": "pm_role_work_result",
        "dedupe_fields": ("request_id", "packet_id", "result_hash"),
        "retry_group_fields": ("event", "request_id"),
    },
    PM_ROLE_WORK_RESULT_DECISION_EVENT: {
        "family": "pm_role_work_result_decision",
        "dedupe_fields": ("request_id", "decision"),
        "retry_group_fields": ("event", "request_id"),
    },
    "worker_current_node_result_returned": {
        "family": "current_node_result",
        "dedupe_fields": ("packet_id", "result_hash"),
        "retry_group_fields": ("event", "packet_id"),
    },
    GATE_DECISION_EVENT: {
        "family": "gate",
        "dedupe_fields": ("gate_id", "route_version", "decided_by_role"),
        "retry_group_fields": ("event", "gate_id", "route_version"),
    },
    "pm_requests_startup_repair": {
        "family": "startup_cycle",
        "dedupe_fields": ("startup_review_cycle", "startup_fact_report_hash"),
        "retry_group_fields": ("event", "startup_fact_report_hash"),
    },
    "pm_writes_route_draft": {
        "family": "route_draft",
        "dedupe_fields": ("draft_version", "route_hash"),
        "retry_group_fields": ("event", "route_id"),
    },
    "pm_completes_current_node_from_reviewed_result": {
        "family": "node_completion",
        "dedupe_fields": ("node_id", "packet_id", "result_hash"),
        "retry_group_fields": ("event", "node_id"),
    },
    "pm_completes_parent_node_from_backward_replay": {
        "family": "node_completion",
        "dedupe_fields": ("node_id", "parent_backward_replay_hash", "parent_segment_decision_hash"),
        "retry_group_fields": ("event", "node_id"),
    },
}

PM_PRIOR_CONTEXT_REQUIRED_CARD_IDS = {
    "pm.prior_path_context",
    "pm.route_skeleton",
    "pm.product_behavior_model_decision",
    "pm.process_route_model_decision",
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
        "action_type": "start_router_daemon",
        "flag": "router_daemon_started",
        "label": "formal_router_daemon_started_as_startup_driver",
        "summary": "Start or attach the built-in one-second Router daemon, then let it schedule startup rows before any external startup work.",
        "actor": "bootloader",
    },
    {
        "action_type": "open_startup_intake_ui",
        "flag": "startup_questions_asked",
        "label": "startup_intake_ui_opened_from_router",
        "summary": "Open the native FlowPilot startup intake UI, then return to Router daemon status and the Controller action ledger without reading the body text in Controller context.",
        "actor": "bootloader",
        "requires_host_automation": True,
        "requires_payload": "startup_intake_result",
        "terminal_for_turn": True,
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
        "summary": "Record the exact current FlowPilot task text from explicit user input while the full user_intake remains sealed until startup activation.",
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
        "action_type": "load_controller_core",
        "flag": "controller_core_loaded",
        "label": "controller_core_loaded",
        "summary": "End bootloader startup, attach Controller to the Router daemon action ledger, and record Controller boundary confirmation evidence before Controller-ledger startup obligations.",
        "actor": "bootloader",
    },
    {
        "action_type": "emit_startup_banner",
        "flag": "banner_emitted",
        "label": "startup_banner_emitted_after_controller_core",
        "summary": "Display the startup banner in the user dialog after Controller core is loaded, then record the confirmed display.",
        "actor": "bootloader",
        "card_id": "startup_banner",
    },
    {
        "action_type": "create_heartbeat_automation",
        "flag": "continuation_binding_recorded",
        "label": "host_bootstraps_startup_heartbeat_automation",
        "summary": "Create the one-minute Codex heartbeat after Controller core handoff and before startup review or route work.",
        "actor": "bootloader",
        "requires_host_automation": True,
    },
    {
        "action_type": "start_role_slots",
        "flag": "roles_started",
        "label": "six_roles_started_from_user_answer",
        "summary": "Start the six current-task roles and record same-action role core prompt delivery according to the user's background-agent answer.",
        "actor": "bootloader",
    },
    {
        "action_type": "inject_role_core_prompts",
        "flag": "role_core_prompts_injected",
        "label": "role_core_prompts_injected_from_copied_kit",
        "summary": "Legacy recovery: deliver each role only its role core card from the copied runtime kit when an older bootstrap state still lacks the delivery receipt.",
        "actor": "bootloader",
    },
)

SYSTEM_CARD_SEQUENCE: tuple[dict[str, Any], ...] = (
    {
        "flag": "reviewer_startup_fact_check_card_delivered",
        "label": "reviewer_startup_fact_check_card_delivered",
        "card_id": "reviewer.startup_fact_check",
        "requires_all_flags": ["startup_mechanical_audit_written", "startup_display_status_written"],
        "to_role": "human_like_reviewer",
    },
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
        "flag": "pm_role_work_request_card_delivered",
        "label": "pm_role_work_request_card_delivered",
        "card_id": "pm.role_work_request",
        "requires_flag": "pm_output_contract_catalog_delivered",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_controller_reset_card_delivered",
        "label": "pm_controller_reset_recovery_card_delivered",
        "card_id": "pm.controller_reset_duty",
        "requires_flag": "controller_boundary_recovery_requested",
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
        "requires_flag": "user_intake_delivered_to_pm",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_material_sufficiency_card_delivered",
        "label": "reviewer_material_sufficiency_card_delivered",
        "card_id": "reviewer.material_sufficiency",
        "requires_flag": "material_scan_results_absorbed_by_pm",
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
        "requires_flag": "research_result_absorbed_for_review_by_pm",
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
        "requires_flag": "current_node_result_absorbed_by_pm",
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
        "flag": "pm_product_behavior_model_decision_card_delivered",
        "label": "pm_product_behavior_model_decision_card_delivered",
        "card_id": "pm.product_behavior_model_decision",
        "requires_flag": "product_behavior_model_submitted",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_product_architecture_card_delivered",
        "label": "reviewer_product_architecture_challenge_card_delivered",
        "card_id": "reviewer.product_architecture_challenge",
        "requires_flag": "pm_product_behavior_model_accepted",
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
        "flag": "pm_process_route_model_decision_card_delivered",
        "label": "pm_process_route_model_decision_card_delivered",
        "card_id": "pm.process_route_model_decision",
        "requires_flag": "process_route_model_submitted",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_route_check_card_delivered",
        "label": "reviewer_route_challenge_card_delivered",
        "card_id": "reviewer.route_challenge",
        "requires_flag": "pm_process_route_model_accepted",
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
        "flag": "pm_parent_backward_targets_card_delivered",
        "label": "pm_parent_backward_targets_phase_card_delivered",
        "card_id": "pm.parent_backward_targets",
        "requires_flag": "node_acceptance_plan_reviewer_passed",
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
        "requires_any_flag": list(MODEL_MISS_REVIEW_BLOCK_FLAGS),
        "to_role": "project_manager",
    },
    {
        "flag": "pm_review_repair_card_delivered",
        "label": "pm_review_repair_phase_card_delivered",
        "card_id": "pm.review_repair",
        "requires_flag": "model_miss_triage_closed",
        "requires_any_flag": list(MODEL_MISS_REVIEW_BLOCK_FLAGS),
        "to_role": "project_manager",
    },
    {
        "flag": "pm_reviewer_blocked_event_delivered",
        "label": "pm_reviewer_blocked_event_card_delivered",
        "card_id": "pm.event.reviewer_blocked",
        "requires_any_flag": list(MODEL_MISS_REVIEW_BLOCK_FLAGS),
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
    "pm.product_behavior_model_decision": "product_architecture",
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
    "pm.process_route_model_decision": "route_skeleton",
    "product_officer.route_product_check": "route_skeleton",
    "reviewer.route_challenge": "route_skeleton",
}

CARD_REQUIRED_SOURCE_PATHS = {
    "reviewer.startup_fact_check": {
        "startup_answers": "startup_answers.json",
        "startup_mechanical_audit": "startup/startup_mechanical_audit.json",
        "startup_mechanical_audit_proof": "startup/startup_mechanical_audit.json.proof.json",
        "display_surface": "display/display_surface.json",
        "continuation_binding": "continuation/continuation_binding.json",
    },
    "pm.product_architecture": {
        "pm_material_understanding": "pm_material_understanding.json",
        "pm_material_understanding_payload": "material/pm_material_understanding_payload.json",
    },
    "product_officer.product_architecture_modelability": {
        "product_function_architecture": "product_function_architecture.json",
    },
    "reviewer.product_architecture_challenge": {
        "product_function_architecture": "product_function_architecture.json",
        "product_behavior_model": "flowguard/product_behavior_model.json",
        "product_architecture_modelability": "flowguard/product_architecture_modelability.json",
        "pm_product_behavior_model_decision": "flowguard/product_behavior_model_pm_decision.json",
    },
    "pm.product_behavior_model_decision": {
        "product_function_architecture": "product_function_architecture.json",
        "product_behavior_model": "flowguard/product_behavior_model.json",
        "product_architecture_modelability": "flowguard/product_architecture_modelability.json",
    },
    "pm.root_contract": {
        "product_function_architecture": "product_function_architecture.json",
        "product_architecture_challenge": "reviews/product_architecture_challenge.json",
        "product_behavior_model": "flowguard/product_behavior_model.json",
        "product_architecture_modelability": "flowguard/product_architecture_modelability.json",
        "pm_product_behavior_model_decision": "flowguard/product_behavior_model_pm_decision.json",
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
        "pm_process_route_model_decision": "flowguard/process_route_model_pm_decision.json",
        "process_route_model": "flowguard/process_route_model.json",
        "route_process_check": "flowguard/route_process_check.json",
    },
    "reviewer.route_challenge": {
        "root_acceptance_contract": "root_acceptance_contract.json",
        "child_skill_gate_manifest": "child_skill_gate_manifest.json",
        "pm_process_route_model_decision": "flowguard/process_route_model_pm_decision.json",
        "process_route_model": "flowguard/process_route_model.json",
        "route_process_check": "flowguard/route_process_check.json",
        "product_behavior_model": "flowguard/product_behavior_model.json",
    },
}

EXTERNAL_EVENTS: dict[str, dict[str, Any]] = {
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
        "requires_flag": "pm_controller_reset_card_delivered",
        "summary": "Recovery-only PM reminder that Controller is only a relay and status-flow controller.",
    },
    "controller_role_confirmed_from_pm_reset": {
        "flag": "controller_role_confirmed",
        "requires_flag": "pm_controller_reset_decision_returned",
        "summary": "Controller acknowledged a recovery-only PM reset and remains relay-only.",
    },
    "heartbeat_or_manual_resume_requested": {
        "flag": "resume_reentry_requested",
        "summary": "A heartbeat or manual resume wakeup requested router-guided re-entry.",
    },
    "controller_reports_role_liveness_fault": {
        "flag": "role_recovery_requested",
        "summary": "Controller reported that a background role is missing, cancelled, unknown, timed out, or no longer addressable; unified role recovery must preempt normal work.",
    },
    "controller_reports_role_no_output": {
        "flag": "role_no_output_reissue_recorded",
        "summary": "Controller reported that the waited role is reachable or completed but Router still lacks the expected output; Router may reissue the same work before role recovery.",
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
        "forbids_active_node_children": True,
        "summary": "PM registered a current-node packet envelope for router direct dispatch.",
    },
    "router_direct_material_scan_dispatch_recheck_passed": {
        "flag": "material_scan_direct_dispatch_recheck_passed",
        "requires_flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "Router direct-dispatch repair recheck passed for material scan packets.",
    },
    "reviewer_allows_material_scan_dispatch": {
        "flag": "reviewer_dispatch_allowed",
        "requires_flag": "reviewer_dispatch_card_delivered",
        "legacy": True,
        "summary": "Legacy reviewer dispatch approval event retained for old run records only.",
    },
    "reviewer_blocks_material_scan_dispatch": {
        "flag": "material_scan_dispatch_blocked",
        "requires_flag": "reviewer_dispatch_card_delivered",
        "legacy": True,
        "summary": "Legacy reviewer dispatch block event retained for old run records only.",
    },
    "router_direct_material_scan_dispatch_recheck_blocked": {
        "flag": "material_scan_dispatch_recheck_blocked",
        "requires_flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "Router direct-dispatch repair recheck blocked material scan packets.",
    },
    "router_protocol_blocker_material_scan_dispatch_recheck": {
        "flag": "material_scan_dispatch_recheck_protocol_blocked",
        "requires_flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "Router direct-dispatch repair recheck found a protocol blocker.",
    },
    "reviewer_allows_current_node_dispatch": {
        "flag": "current_node_dispatch_allowed",
        "requires_flag": "reviewer_current_node_dispatch_card_delivered",
        "legacy": True,
        "summary": "Legacy current-node reviewer dispatch approval event retained for old run records only.",
    },
    "worker_scan_packet_bodies_delivered_after_dispatch": {
        "flag": "worker_packets_delivered",
        "requires_flag": "material_scan_packets_relayed",
        "summary": "Worker packet bodies were delivered after router direct dispatch.",
    },
    "worker_scan_results_returned": {
        "flag": "worker_scan_results_returned",
        "requires_flag": "worker_packets_delivered",
        "summary": "Worker scan results returned to the PM-first result path.",
    },
    "pm_records_material_scan_result_disposition": {
        "flag": "material_scan_result_disposition_recorded",
        "requires_flag": "material_scan_results_relayed_to_pm",
        "summary": "PM recorded material scan result disposition and released a formal material sufficiency package when absorbed.",
    },
    "worker_current_node_result_returned": {
        "flag": "current_node_worker_result_returned",
        "requires_flag": "current_node_packet_relayed",
        "summary": "Worker returned a current-node result envelope.",
    },
    "pm_records_current_node_result_disposition": {
        "flag": "current_node_result_disposition_recorded",
        "requires_flag": "current_node_result_relayed_to_pm",
        "summary": "PM recorded current-node worker result disposition and released the formal node-completion review package when absorbed.",
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
    "pm_records_research_result_disposition": {
        "flag": "research_result_disposition_recorded",
        "requires_flag": "research_result_relayed_to_pm",
        "summary": "PM recorded research result disposition and released a formal research source-check package when absorbed.",
    },
    "reviewer_passes_research_direct_source_check": {
        "flag": "research_review_passed",
        "requires_flag": "reviewer_research_check_card_delivered",
        "summary": "Reviewer passed direct-source or experiment-output research check.",
    },
    "reviewer_blocks_research_direct_source_check": {
        "flag": "research_review_blocked",
        "requires_flag": "reviewer_research_check_card_delivered",
        "summary": "Reviewer blocked direct-source or experiment-output research check.",
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
    "reviewer_blocks_product_architecture": {
        "flag": "product_architecture_reviewer_blocked",
        "requires_flag": "reviewer_product_architecture_card_delivered",
        "summary": "Reviewer blocked the PM product-function architecture challenge.",
    },
    "product_officer_passes_product_architecture_modelability": {
        "flag": "product_architecture_modelability_passed",
        "requires_flag": "product_officer_product_architecture_card_delivered",
        "gate_id": "product_behavior_model",
        "terminal_gate_outcome": True,
        "summary": "Compatibility alias: Product FlowGuard Officer submitted the product behavior model.",
    },
    "product_officer_submits_product_behavior_model": {
        "flag": "product_behavior_model_submitted",
        "requires_flag": "product_officer_product_architecture_card_delivered",
        "gate_id": "product_behavior_model",
        "terminal_gate_outcome": True,
        "summary": "Product FlowGuard Officer submitted the canonical product behavior model.",
    },
    "product_officer_model_report": {
        "flag": "legacy_product_officer_model_report_received",
        "requires_flag": "product_officer_product_architecture_card_delivered",
        "gate_id": "product_behavior_model",
        "legacy": True,
        "terminal_gate_outcome": False,
        "summary": "Legacy Product FlowGuard model-report status event retained only so old run artifacts remain registered in the event taxonomy.",
    },
    "pm_accepts_product_behavior_model": {
        "flag": "pm_product_behavior_model_accepted",
        "requires_flag": "pm_product_behavior_model_decision_card_delivered",
        "summary": "PM accepted the Product FlowGuard product behavior model as the product basis for review and route planning.",
    },
    "pm_requests_product_behavior_model_rebuild": {
        "flag": "pm_product_behavior_model_rebuild_requested",
        "requires_flag": "pm_product_behavior_model_decision_card_delivered",
        "summary": "PM rejected the current product behavior model and requested product architecture/model rebuild before reviewer challenge.",
    },
    "product_officer_blocks_product_architecture_modelability": {
        "flag": "product_architecture_modelability_blocked",
        "requires_flag": "product_officer_product_architecture_card_delivered",
        "gate_id": "product_behavior_model",
        "terminal_gate_outcome": True,
        "summary": "Compatibility alias: Product FlowGuard Officer blocked the product behavior model.",
    },
    "product_officer_blocks_product_behavior_model": {
        "flag": "product_behavior_model_blocked",
        "requires_flag": "product_officer_product_architecture_card_delivered",
        "gate_id": "product_behavior_model",
        "terminal_gate_outcome": True,
        "summary": "Product FlowGuard Officer blocked the canonical product behavior model.",
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
    "reviewer_blocks_root_acceptance_contract": {
        "flag": "root_contract_reviewer_blocked",
        "requires_flag": "reviewer_root_contract_card_delivered",
        "summary": "Reviewer blocked the root acceptance contract challenge.",
    },
    "product_officer_passes_root_acceptance_contract_modelability": {
        "flag": "root_contract_modelability_passed",
        "requires_flag": "product_officer_root_contract_card_delivered",
        "legacy": True,
        "summary": "Product FlowGuard Officer passed root contract modelability.",
    },
    "product_officer_blocks_root_acceptance_contract_modelability": {
        "flag": "root_contract_modelability_blocked",
        "requires_flag": "product_officer_root_contract_card_delivered",
        "legacy": True,
        "summary": "Product FlowGuard Officer blocked root contract modelability.",
    },
    "pm_freezes_root_acceptance_contract": {
        "flag": "root_contract_frozen_by_pm",
        "requires_flag": "root_contract_reviewer_passed",
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
    "reviewer_blocks_child_skill_gate_manifest": {
        "flag": "child_skill_manifest_reviewer_blocked",
        "requires_flag": "reviewer_child_skill_gate_manifest_card_delivered",
        "summary": "Reviewer blocked child-skill gate manifest review.",
    },
    "process_officer_passes_child_skill_conformance_model": {
        "flag": "child_skill_process_officer_passed",
        "requires_flag": "process_officer_child_skill_card_delivered",
        "legacy": True,
        "summary": "Process FlowGuard Officer passed child-skill conformance model review.",
    },
    "process_officer_blocks_child_skill_conformance_model": {
        "flag": "child_skill_process_officer_blocked",
        "requires_flag": "process_officer_child_skill_card_delivered",
        "legacy": True,
        "summary": "Process FlowGuard Officer blocked child-skill conformance model review.",
    },
    "product_officer_passes_child_skill_product_fit": {
        "flag": "child_skill_product_officer_passed",
        "requires_flag": "product_officer_child_skill_card_delivered",
        "legacy": True,
        "summary": "Product FlowGuard Officer passed child-skill product fit review.",
    },
    "product_officer_blocks_child_skill_product_fit": {
        "flag": "child_skill_product_officer_blocked",
        "requires_flag": "product_officer_child_skill_card_delivered",
        "legacy": True,
        "summary": "Product FlowGuard Officer blocked child-skill product fit review.",
    },
    "pm_approves_child_skill_manifest_for_route": {
        "flag": "child_skill_manifest_pm_approved_for_route",
        "requires_flag": "child_skill_manifest_reviewer_passed",
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
        "gate_id": "process_route_model",
        "terminal_gate_outcome": True,
        "summary": "Compatibility alias: Process FlowGuard Officer submitted the process route model.",
    },
    "process_officer_submits_process_route_model": {
        "flag": "process_route_model_submitted",
        "requires_flag": "process_officer_route_check_card_delivered",
        "gate_id": "process_route_model",
        "terminal_gate_outcome": True,
        "summary": "Process FlowGuard Officer submitted the canonical process route model.",
    },
    "pm_accepts_process_route_model": {
        "flag": "pm_process_route_model_accepted",
        "requires_flag": "pm_process_route_model_decision_card_delivered",
        "summary": "PM accepted the Process FlowGuard serial route execution model before Reviewer route challenge.",
    },
    "pm_requests_process_route_model_rebuild": {
        "flag": "pm_process_route_model_rebuild_requested",
        "requires_flag": "pm_process_route_model_decision_card_delivered",
        "summary": "PM rejected the current process route model and requested route/model rebuild before route challenge.",
    },
    "process_officer_requires_route_repair": {
        "flag": "process_officer_route_repair_required",
        "requires_flag": "process_officer_route_check_card_delivered",
        "gate_id": "process_route_model",
        "terminal_gate_outcome": True,
        "summary": "Compatibility alias: Process FlowGuard Officer requested process route model repair.",
    },
    "process_officer_requests_process_route_model_repair": {
        "flag": "process_route_model_repair_required",
        "requires_flag": "process_officer_route_check_card_delivered",
        "gate_id": "process_route_model",
        "terminal_gate_outcome": True,
        "summary": "Process FlowGuard Officer requested repair of the canonical process route model.",
    },
    "process_officer_blocks_route_check": {
        "flag": "process_officer_route_check_blocked",
        "requires_flag": "process_officer_route_check_card_delivered",
        "gate_id": "process_route_model",
        "terminal_gate_outcome": True,
        "summary": "Compatibility alias: Process FlowGuard Officer blocked the process route model.",
    },
    "process_officer_blocks_process_route_model": {
        "flag": "process_route_model_blocked",
        "requires_flag": "process_officer_route_check_card_delivered",
        "gate_id": "process_route_model",
        "terminal_gate_outcome": True,
        "summary": "Process FlowGuard Officer blocked the canonical process route model.",
    },
    "product_officer_passes_route_check": {
        "flag": "product_officer_route_check_passed",
        "requires_flag": "product_officer_route_check_card_delivered",
        "legacy": True,
        "summary": "Compatibility event: Product FlowGuard Officer passed the legacy route product check.",
    },
    "product_officer_blocks_route_check": {
        "flag": "product_officer_route_check_blocked",
        "requires_flag": "product_officer_route_check_card_delivered",
        "legacy": True,
        "summary": "Compatibility event: Product FlowGuard Officer blocked the legacy route product check.",
    },
    "reviewer_passes_route_check": {
        "flag": "reviewer_route_check_passed",
        "requires_flag": "reviewer_route_check_card_delivered",
        "summary": "Reviewer passed the route challenge.",
    },
    "reviewer_blocks_route_check": {
        "flag": "reviewer_route_check_blocked",
        "requires_flag": "reviewer_route_check_card_delivered",
        "summary": "Reviewer blocked the route challenge.",
    },
    "pm_activates_reviewed_route": {
        "flag": "route_activated_by_pm",
        "requires_flag": "reviewer_route_check_passed",
        "summary": "PM activated route after Product Officer product model, Process Officer route model, and Reviewer route challenge.",
    },
    "pm_writes_node_acceptance_plan": {
        "flag": "node_acceptance_plan_written",
        "requires_flag": "pm_node_acceptance_plan_card_delivered",
        "summary": "PM wrote the active node acceptance plan before packet dispatch.",
    },
    "pm_revises_node_acceptance_plan": {
        "flag": "node_acceptance_plan_revised_by_pm",
        "requires_flag": "model_miss_triage_closed",
        "summary": "PM revised the active node acceptance plan as same-node repair after reviewer block.",
    },
    "reviewer_passes_node_acceptance_plan": {
        "flag": "node_acceptance_plan_reviewer_passed",
        "requires_flag": "reviewer_node_acceptance_plan_card_delivered",
        "summary": "Reviewer passed the active node acceptance plan.",
    },
    "reviewer_blocks_node_acceptance_plan": {
        "flag": "node_acceptance_plan_review_blocked",
        "requires_flag": "reviewer_node_acceptance_plan_card_delivered",
        "summary": "Reviewer blocked the active node acceptance plan before worker packet registration.",
    },
    "reviewer_blocks_current_node_dispatch": {
        "flag": "current_node_dispatch_blocked",
        "requires_flag": "reviewer_current_node_dispatch_card_delivered",
        "legacy": True,
        "summary": "Legacy current-node reviewer dispatch block event retained for old run records only.",
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
    "reviewer_blocks_parent_backward_replay": {
        "flag": "parent_backward_replay_blocked",
        "requires_flag": "reviewer_parent_backward_replay_card_delivered",
        "summary": "Reviewer blocked local parent backward replay.",
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
    "pm_registers_role_work_request": {
        "flag": "pm_role_work_request_registered",
        "summary": "PM registered a bounded role-work request through the generic always-available PM channel.",
    },
    "role_work_result_returned": {
        "flag": "pm_role_work_result_returned",
        "summary": "The requested role returned a result envelope for a PM role-work request.",
    },
    "pm_records_role_work_result_decision": {
        "flag": "pm_role_work_result_absorbed",
        "summary": "PM recorded whether a role-work result was absorbed, canceled, or superseded.",
    },
    "pm_records_control_blocker_repair_decision": {
        "flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "PM recorded a repair decision for a router materialized control blocker.",
    },
    "pm_records_control_blocker_followup_blocker": {
        "flag": "pm_control_blocker_followup_blocker_recorded",
        "requires_flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "PM recorded that a control-blocker repair follow-up ended in a blocker that needs a new PM decision.",
    },
    "pm_records_control_blocker_protocol_blocker": {
        "flag": "pm_control_blocker_protocol_blocker_recorded",
        "requires_flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "PM recorded that a control-blocker repair follow-up exposed a protocol blocker.",
    },
    "pm_records_parent_protocol_blocker": {
        "flag": "parent_protocol_blocker_recorded",
        "requires_flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "PM recorded a parent/module repair protocol blocker after parent backward replay repair.",
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
    "pm_completes_parent_node_from_backward_replay": {
        "flag": "node_completed_by_pm",
        "requires_flag": "parent_segment_decision_recorded",
        "summary": "PM completed a parent/module node after reviewer-passed backward replay and PM segment decision.",
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
    "reviewer_blocks_evidence_quality_package": {
        "flag": "evidence_quality_reviewer_blocked",
        "requires_flag": "reviewer_evidence_quality_card_delivered",
        "summary": "Reviewer blocked the evidence quality package before final ledger work.",
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
    "reviewer_blocks_final_backward_replay": {
        "flag": "final_backward_replay_blocked",
        "requires_flag": "reviewer_final_backward_replay_card_delivered",
        "summary": "Reviewer blocked final backward replay.",
    },
    "pm_approves_terminal_closure": {
        "flag": "pm_closure_approved",
        "requires_flag": "pm_closure_card_delivered",
        "summary": "PM approved terminal closure after clean final ledger and backward replay.",
    },
}


PRODUCT_ARCHITECTURE_REPAIR_RESET_FLAGS = (
    "pm_product_architecture_card_delivered",
    "product_architecture_written_by_pm",
    "pm_product_behavior_model_decision_card_delivered",
    "pm_product_behavior_model_accepted",
    "pm_product_behavior_model_rebuild_requested",
    "product_architecture_reviewer_passed",
    "product_behavior_model_submitted",
    "product_behavior_model_blocked",
    "product_architecture_modelability_passed",
    "product_architecture_modelability_blocked",
    "reviewer_product_architecture_card_delivered",
    "product_officer_product_architecture_card_delivered",
    "root_contract_written_by_pm",
    "root_contract_reviewer_passed",
    "root_contract_modelability_passed",
    "root_contract_frozen_by_pm",
    "pm_child_skill_selection_written",
    "child_skill_gate_manifest_written",
    "child_skill_manifest_reviewer_passed",
    "child_skill_process_officer_passed",
    "child_skill_product_officer_passed",
    "child_skill_manifest_pm_approved_for_route",
    "capability_evidence_synced",
    "route_draft_written_by_pm",
    "process_route_model_submitted",
    "process_route_model_repair_required",
    "process_route_model_blocked",
    "process_officer_route_check_passed",
    "process_officer_route_repair_required",
    "process_officer_route_check_blocked",
    "pm_process_route_model_decision_card_delivered",
    "pm_process_route_model_accepted",
    "pm_process_route_model_rebuild_requested",
    "product_officer_route_check_passed",
    "reviewer_route_check_passed",
    "route_activated_by_pm",
)
ROOT_CONTRACT_REPAIR_RESET_FLAGS = (
    "root_contract_written_by_pm",
    "root_contract_reviewer_passed",
    "root_contract_modelability_passed",
    "root_contract_frozen_by_pm",
    "reviewer_root_contract_card_delivered",
    "product_officer_root_contract_card_delivered",
    "pm_child_skill_selection_written",
    "child_skill_gate_manifest_written",
    "child_skill_manifest_reviewer_passed",
    "child_skill_process_officer_passed",
    "child_skill_product_officer_passed",
    "child_skill_manifest_pm_approved_for_route",
    "capability_evidence_synced",
    "route_draft_written_by_pm",
    "process_officer_route_check_passed",
    "pm_process_route_model_decision_card_delivered",
    "pm_process_route_model_accepted",
    "pm_process_route_model_rebuild_requested",
    "product_officer_route_check_passed",
    "reviewer_route_check_passed",
    "route_activated_by_pm",
)
CHILD_SKILL_GATE_REPAIR_RESET_FLAGS = (
    "child_skill_gate_manifest_written",
    "child_skill_manifest_reviewer_passed",
    "child_skill_process_officer_passed",
    "child_skill_product_officer_passed",
    "child_skill_manifest_pm_approved_for_route",
    "capability_evidence_synced",
    "reviewer_child_skill_gate_manifest_card_delivered",
    "process_officer_child_skill_card_delivered",
    "product_officer_child_skill_card_delivered",
    "route_draft_written_by_pm",
    "process_route_model_submitted",
    "process_route_model_repair_required",
    "process_route_model_blocked",
    "process_officer_route_check_passed",
    "process_officer_route_repair_required",
    "process_officer_route_check_blocked",
    "pm_process_route_model_decision_card_delivered",
    "pm_process_route_model_accepted",
    "pm_process_route_model_rebuild_requested",
    "product_officer_route_check_passed",
    "reviewer_route_check_passed",
    "route_activated_by_pm",
)
ROUTE_GATE_REPAIR_RESET_FLAGS = (
    "route_draft_written_by_pm",
    "process_route_model_submitted",
    "process_route_model_repair_required",
    "process_route_model_blocked",
    "process_officer_route_check_passed",
    "process_officer_route_repair_required",
    "process_officer_route_check_blocked",
    "pm_process_route_model_decision_card_delivered",
    "pm_process_route_model_accepted",
    "pm_process_route_model_rebuild_requested",
    "product_officer_route_check_passed",
    "reviewer_route_check_passed",
    "process_officer_route_check_card_delivered",
    "product_officer_route_check_card_delivered",
    "reviewer_route_check_card_delivered",
    "route_activated_by_pm",
)
RESEARCH_GATE_REPAIR_RESET_FLAGS = (
    "research_package_written_by_pm",
    "research_capability_decision_recorded",
    "research_packet_relayed",
    "research_result_relayed_to_pm",
    "research_result_disposition_recorded",
    "research_result_absorbed_for_review_by_pm",
    "worker_research_report_returned",
    "research_review_passed",
    "reviewer_research_check_card_delivered",
    "pm_research_absorb_or_mutate_card_delivered",
    "research_result_absorbed_by_pm",
)
PARENT_BACKWARD_REPAIR_RESET_FLAGS = (
    "parent_backward_targets_built",
    "parent_backward_replay_passed",
    "reviewer_parent_backward_replay_card_delivered",
    "parent_segment_decision_recorded",
    "pm_parent_segment_decision_card_delivered",
)
EVIDENCE_QUALITY_REPAIR_RESET_FLAGS = (
    "evidence_quality_package_written",
    "evidence_quality_reviewer_passed",
    "reviewer_evidence_quality_card_delivered",
    "final_ledger_built_clean",
    "final_backward_replay_passed",
    "reviewer_final_backward_replay_card_delivered",
    "pm_closure_approved",
    "pm_closure_card_delivered",
)
FINAL_BACKWARD_REPAIR_RESET_FLAGS = (
    "final_ledger_built_clean",
    "final_backward_replay_passed",
    "reviewer_final_backward_replay_card_delivered",
    "pm_closure_approved",
    "pm_closure_card_delivered",
)

GATE_OUTCOME_BLOCK_EVENT_SPECS: dict[str, dict[str, Any]] = {
    "reviewer_blocks_research_direct_source_check": {
        "expected_role": "human_like_reviewer",
        "path": "research/research_reviewer_block.json",
        "schema_version": "flowpilot.research_reviewer_block.v1",
        "checked_paths": ("research/research_package.json", "research/worker_research_report.json"),
        "reset_flags": RESEARCH_GATE_REPAIR_RESET_FLAGS,
    },
    "reviewer_blocks_product_architecture": {
        "expected_role": "human_like_reviewer",
        "path": "reviews/product_architecture_challenge_block.json",
        "schema_version": "flowpilot.product_architecture_block.v1",
        "checked_paths": ("product_function_architecture.json",),
        "reset_flags": PRODUCT_ARCHITECTURE_REPAIR_RESET_FLAGS,
    },
    "product_officer_blocks_product_architecture_modelability": {
        "expected_role": "product_flowguard_officer",
        "path": "flowguard/product_architecture_modelability_block.json",
        "schema_version": "flowpilot.product_architecture_modelability_block.v1",
        "checked_paths": ("product_function_architecture.json",),
        "reset_flags": tuple(
            flag
            for flag in PRODUCT_ARCHITECTURE_REPAIR_RESET_FLAGS
            if flag != "product_architecture_modelability_blocked"
        ),
    },
    "product_officer_blocks_product_behavior_model": {
        "expected_role": "product_flowguard_officer",
        "path": "flowguard/product_behavior_model_block.json",
        "schema_version": "flowpilot.product_behavior_model_block.v1",
        "checked_paths": ("product_function_architecture.json",),
        "reset_flags": tuple(
            flag
            for flag in PRODUCT_ARCHITECTURE_REPAIR_RESET_FLAGS
            if flag != "product_behavior_model_blocked"
        ),
    },
    "reviewer_blocks_root_acceptance_contract": {
        "expected_role": "human_like_reviewer",
        "path": "reviews/root_contract_challenge_block.json",
        "schema_version": "flowpilot.root_contract_block.v1",
        "checked_paths": ("root_acceptance_contract.json", "standard_scenario_pack.json"),
        "reset_flags": ROOT_CONTRACT_REPAIR_RESET_FLAGS,
    },
    "product_officer_blocks_root_acceptance_contract_modelability": {
        "expected_role": "product_flowguard_officer",
        "path": "flowguard/root_contract_modelability_block.json",
        "schema_version": "flowpilot.root_contract_modelability_block.v1",
        "checked_paths": (
            "root_acceptance_contract.json",
            "standard_scenario_pack.json",
            "reviews/root_contract_challenge.json",
        ),
        "reset_flags": ROOT_CONTRACT_REPAIR_RESET_FLAGS,
    },
    "reviewer_blocks_child_skill_gate_manifest": {
        "expected_role": "human_like_reviewer",
        "path": "reviews/child_skill_gate_manifest_block.json",
        "schema_version": "flowpilot.child_skill_gate_manifest_block.v1",
        "checked_paths": ("child_skill_gate_manifest.json", "pm_child_skill_selection.json", "capabilities.json"),
        "reset_flags": CHILD_SKILL_GATE_REPAIR_RESET_FLAGS,
    },
    "process_officer_blocks_child_skill_conformance_model": {
        "expected_role": "process_flowguard_officer",
        "path": "flowguard/child_skill_conformance_model_block.json",
        "schema_version": "flowpilot.child_skill_conformance_model_block.v1",
        "checked_paths": ("child_skill_gate_manifest.json", "reviews/child_skill_gate_manifest_review.json"),
        "reset_flags": CHILD_SKILL_GATE_REPAIR_RESET_FLAGS,
    },
    "product_officer_blocks_child_skill_product_fit": {
        "expected_role": "product_flowguard_officer",
        "path": "flowguard/child_skill_product_fit_block.json",
        "schema_version": "flowpilot.child_skill_product_fit_block.v1",
        "checked_paths": (
            "child_skill_gate_manifest.json",
            "flowguard/child_skill_conformance_model.json",
            "product_function_architecture.json",
            "root_acceptance_contract.json",
        ),
        "reset_flags": CHILD_SKILL_GATE_REPAIR_RESET_FLAGS,
    },
    "product_officer_blocks_route_check": {
        "expected_role": "product_flowguard_officer",
        "path": "flowguard/route_product_check_block.json",
        "schema_version": "flowpilot.route_product_check_block.v1",
        "checked_paths": ("__current_route_draft__", "flowguard/product_architecture_modelability.json", "root_acceptance_contract.json", "flowguard/route_process_check.json"),
        "reset_flags": ROUTE_GATE_REPAIR_RESET_FLAGS,
    },
    "reviewer_blocks_route_check": {
        "expected_role": "human_like_reviewer",
        "path": "reviews/route_challenge_block.json",
        "schema_version": "flowpilot.route_review_block.v1",
        "checked_paths": (
            "__current_route_draft__",
            "flowguard/route_process_check.json",
            "flowguard/process_route_model_pm_decision.json",
            "flowguard/product_behavior_model.json",
        ),
        "reset_flags": ROUTE_GATE_REPAIR_RESET_FLAGS,
    },
    "reviewer_blocks_parent_backward_replay": {
        "expected_role": "human_like_reviewer",
        "path": "__active_node_root__/reviews/parent_backward_replay_block.json",
        "schema_version": "flowpilot.parent_backward_replay_block.v1",
        "checked_paths": ("__parent_backward_targets__", "__active_node_acceptance_plan__"),
        "reset_flags": PARENT_BACKWARD_REPAIR_RESET_FLAGS,
    },
    "reviewer_blocks_evidence_quality_package": {
        "expected_role": "human_like_reviewer",
        "path": "reviews/evidence_quality_block.json",
        "schema_version": "flowpilot.evidence_quality_block.v1",
        "checked_paths": ("evidence/evidence_ledger.json", "generated_resource_ledger.json", "quality/quality_package.json"),
        "reset_flags": EVIDENCE_QUALITY_REPAIR_RESET_FLAGS,
    },
    "reviewer_blocks_final_backward_replay": {
        "expected_role": "human_like_reviewer",
        "path": "reviews/final_backward_replay_block.json",
        "schema_version": "flowpilot.final_backward_replay_block.v1",
        "checked_paths": ("final_route_wide_gate_ledger.json", "terminal_human_backward_replay_map.json"),
        "reset_flags": FINAL_BACKWARD_REPAIR_RESET_FLAGS,
    },
}
GATE_OUTCOME_BLOCK_EVENTS = frozenset(GATE_OUTCOME_BLOCK_EVENT_SPECS)
GATE_OUTCOME_PASS_CLEAR_FLAGS: dict[str, tuple[str, ...]] = {
    "reviewer_passes_research_direct_source_check": ("research_review_blocked",),
    "reviewer_passes_product_architecture": ("product_architecture_reviewer_blocked",),
    "product_officer_passes_product_architecture_modelability": (
        "product_behavior_model_blocked",
        "product_architecture_modelability_blocked",
    ),
    "product_officer_submits_product_behavior_model": (
        "product_behavior_model_blocked",
        "product_architecture_modelability_blocked",
    ),
    "reviewer_passes_root_acceptance_contract": ("root_contract_reviewer_blocked",),
    "product_officer_passes_root_acceptance_contract_modelability": ("root_contract_modelability_blocked",),
    "reviewer_passes_child_skill_gate_manifest": ("child_skill_manifest_reviewer_blocked",),
    "process_officer_passes_child_skill_conformance_model": ("child_skill_process_officer_blocked",),
    "product_officer_passes_child_skill_product_fit": ("child_skill_product_officer_blocked",),
    "process_officer_passes_route_check": (
        "process_route_model_repair_required",
        "process_route_model_blocked",
        "process_officer_route_repair_required",
        "process_officer_route_check_blocked",
    ),
    "process_officer_submits_process_route_model": (
        "process_route_model_repair_required",
        "process_route_model_blocked",
        "process_officer_route_repair_required",
        "process_officer_route_check_blocked",
    ),
    "product_officer_passes_route_check": ("product_officer_route_check_blocked",),
    "reviewer_passes_route_check": ("reviewer_route_check_blocked",),
    "reviewer_passes_parent_backward_replay": ("parent_backward_replay_blocked",),
    "reviewer_passes_evidence_quality_package": ("evidence_quality_reviewer_blocked",),
    "reviewer_final_backward_replay_passed": ("final_backward_replay_blocked",),
}
GATE_OUTCOME_PASS_CLEARS_EVENTS: dict[str, tuple[str, ...]] = {
    pass_event: tuple(
        block_event
        for block_event in GATE_OUTCOME_BLOCK_EVENTS
        if EXTERNAL_EVENTS[block_event]["flag"] in clear_flags
    )
    for pass_event, clear_flags in GATE_OUTCOME_PASS_CLEAR_FLAGS.items()
}

GATE_CONTRACT_SCHEMA = "flowpilot.gate_contract.v1"
GATE_CONTRACTS: dict[str, dict[str, Any]] = {
    "product_behavior_model": {
        "schema_version": GATE_CONTRACT_SCHEMA,
        "gate_id": "product_behavior_model",
        "card_id": "product_officer.product_architecture_modelability",
        "required_flag": "product_behavior_model_submitted",
        "wait_requires_flag": "product_officer_product_architecture_card_delivered",
        "target_role": "product_flowguard_officer",
        "output_contract_id": "flowpilot.output_contract.officer_model_report.v1",
        "pass_events": (
            "product_officer_submits_product_behavior_model",
            "product_officer_passes_product_architecture_modelability",
        ),
        "block_events": (
            "product_officer_blocks_product_behavior_model",
            "product_officer_blocks_product_architecture_modelability",
        ),
        "legacy_non_completion_events": ("product_officer_model_report",),
        "completion_rule": "pass_or_block_event_required",
        "legacy_event_policy": "registered_metadata_only_not_gate_completion",
        "canonical_artifact": "flowguard/product_behavior_model.json",
        "compatibility_artifact": "flowguard/product_architecture_modelability.json",
    },
    "process_route_model": {
        "schema_version": GATE_CONTRACT_SCHEMA,
        "gate_id": "process_route_model",
        "card_id": "process_officer.route_process_check",
        "required_flag": "process_route_model_submitted",
        "wait_requires_flag": "process_officer_route_check_card_delivered",
        "target_role": "process_flowguard_officer",
        "output_contract_id": "flowpilot.output_contract.officer_model_report.v1",
        "pass_events": (
            "process_officer_submits_process_route_model",
            "process_officer_passes_route_check",
        ),
        "block_events": (
            "process_officer_requests_process_route_model_repair",
            "process_officer_blocks_process_route_model",
            "process_officer_requires_route_repair",
            "process_officer_blocks_route_check",
        ),
        "legacy_non_completion_events": (),
        "completion_rule": "pass_repair_or_block_event_required",
        "legacy_event_policy": "compatibility_aliases_satisfy_canonical_flags",
        "canonical_artifact": "flowguard/process_route_model.json",
        "compatibility_artifact": "flowguard/route_process_check.json",
    },
}
GATE_CONTRACT_ALIASES = {
    "product_architecture_modelability": "product_behavior_model",
    "route_process_check": "process_route_model",
}
GATE_CONTRACTS_BY_CARD = {
    str(contract["card_id"]): gate_id
    for gate_id, contract in GATE_CONTRACTS.items()
}
GATE_CONTRACTS_BY_EVENT = {
    event: gate_id
    for gate_id, contract in GATE_CONTRACTS.items()
    for event in (
        *contract.get("pass_events", ()),
        *contract.get("block_events", ()),
        *contract.get("legacy_non_completion_events", ()),
    )
}


def _public_gate_contract(contract: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(contract, dict):
        return None
    public = dict(contract)
    for key in ("pass_events", "block_events", "legacy_non_completion_events"):
        public[key] = list(public.get(key) or [])
    return public


def _gate_contract_for_id(gate_id: str | None) -> dict[str, Any] | None:
    if not gate_id:
        return None
    key = str(gate_id)
    return GATE_CONTRACTS.get(key) or GATE_CONTRACTS.get(GATE_CONTRACT_ALIASES.get(key, ""))


def _gate_contract_for_card(card_id: str | None) -> dict[str, Any] | None:
    if not card_id:
        return None
    return _gate_contract_for_id(GATE_CONTRACTS_BY_CARD.get(str(card_id)))


def _gate_contract_for_event(event: str | None) -> dict[str, Any] | None:
    if not event:
        return None
    return _gate_contract_for_id(GATE_CONTRACTS_BY_EVENT.get(str(event)))


def _gate_contract_for_events(events: Iterable[str]) -> dict[str, Any] | None:
    gate_ids = {
        GATE_CONTRACTS_BY_EVENT[str(event)]
        for event in events
        if str(event) in GATE_CONTRACTS_BY_EVENT
    }
    if len(gate_ids) == 1:
        return _gate_contract_for_id(next(iter(gate_ids)))
    return None


def _event_is_terminal_gate_outcome(event: str, meta: dict[str, Any]) -> bool:
    if meta.get("legacy") or meta.get("terminal_gate_outcome") is False:
        return False
    contract = _gate_contract_for_event(event)
    if contract is None:
        return True
    return event in set(contract.get("pass_events") or ()) | set(contract.get("block_events") or ())


def _gate_completion_wait_group(group: list[tuple[str, dict[str, Any]]]) -> list[tuple[str, dict[str, Any]]]:
    if not _gate_contract_for_events(event for event, _meta in group):
        return group
    terminal_group = [
        (event, meta)
        for event, meta in group
        if _event_is_terminal_gate_outcome(event, meta)
    ]
    return terminal_group or group


PRODUCT_BEHAVIOR_MODEL_PASS_EVENTS = frozenset(
    {
        "product_officer_submits_product_behavior_model",
        "product_officer_passes_product_architecture_modelability",
    }
)
PRODUCT_BEHAVIOR_MODEL_BLOCK_EVENTS = frozenset(
    {
        "product_officer_blocks_product_behavior_model",
        "product_officer_blocks_product_architecture_modelability",
    }
)
PROCESS_ROUTE_MODEL_PASS_EVENTS = frozenset(
    {
        "process_officer_submits_process_route_model",
        "process_officer_passes_route_check",
    }
)
PROCESS_ROUTE_MODEL_REPAIR_EVENTS = frozenset(
    {
        "process_officer_requests_process_route_model_repair",
        "process_officer_requires_route_repair",
    }
)
PROCESS_ROUTE_MODEL_BLOCK_EVENTS = frozenset(
    {
        "process_officer_blocks_process_route_model",
        "process_officer_blocks_route_check",
    }
)


__all__ = (
    'SCHEMA_VERSION',
    'BOOTSTRAP_STATE_SCHEMA',
    'RUN_STATE_SCHEMA',
    'PROMPT_MANIFEST_SCHEMA',
    'PACKET_LEDGER_SCHEMA',
    'RESUME_EVIDENCE_SCHEMA',
    'ROUTE_HISTORY_INDEX_SCHEMA',
    'PM_PRIOR_PATH_CONTEXT_SCHEMA',
    'DISPLAY_PLAN_SCHEMA',
    'ROUTE_STATE_SNAPSHOT_SCHEMA',
    'CONTROL_BLOCKER_SCHEMA',
    'CONTROL_BLOCKER_REPAIR_PACKET_SCHEMA',
    'BLOCKER_REPAIR_POLICY_SCHEMA',
    'REPAIR_TRANSACTION_SCHEMA',
    'REPAIR_TRANSACTION_INDEX_SCHEMA',
    'ROLE_RECOVERY_TRANSACTION_SCHEMA',
    'ROLE_RECOVERY_REPORT_SCHEMA',
    'ROLE_RECOVERY_OBLIGATION_REPLAY_SCHEMA',
    'CONTROL_TRANSACTION_REGISTRY_SCHEMA',
    'ROUTE_ACTION_POLICY_REGISTRY_SCHEMA',
    'ROLE_OUTPUT_ENVELOPE_SCHEMA',
    'EVENT_ENVELOPE_SCHEMA',
    'LIVE_CARD_CONTEXT_SCHEMA',
    'PAYLOAD_CONTRACT_SCHEMA',
    'GATE_DECISION_SCHEMA',
    'GATE_DECISION_RECORD_SCHEMA',
    'GATE_DECISION_LEDGER_SCHEMA',
    'PM_SUGGESTION_LEDGER_ENTRY_SCHEMA',
    'SELF_INTERROGATION_INDEX_SCHEMA',
    'SELF_INTERROGATION_RECORD_SCHEMA',
    'PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT',
    'PM_CONTROL_BLOCKER_FOLLOWUP_BLOCKER_EVENT',
    'PM_CONTROL_BLOCKER_PROTOCOL_BLOCKER_EVENT',
    'PM_PARENT_PROTOCOL_BLOCKER_EVENT',
    'PM_MODEL_MISS_TRIAGE_DECISION_EVENT',
    'PM_ROLE_WORK_REQUEST_EVENT',
    'ROLE_WORK_RESULT_RETURNED_EVENT',
    'PM_ROLE_WORK_RESULT_DECISION_EVENT',
    'GATE_DECISION_EVENT',
    'EVENT_IDEMPOTENCY_LEDGER_SCHEMA',
    'DISPLAY_CONFIRMATION_SCHEMA',
    'DISPLAY_SURFACE_RECEIPT_SCHEMA',
    'CURRENT_STATUS_SUMMARY_SCHEMA',
    'OFFICER_REQUEST_LIFECYCLE_INDEX_SCHEMA',
    'CONTINUATION_QUARANTINE_SCHEMA',
    'FINAL_USER_REPORT_SCHEMA',
    'ROUTE_DISPLAY_REFRESH_SCHEMA',
    'CONTROLLER_USER_REPORTING_POLICY_SCHEMA',
    'DETERMINISTIC_BOOTSTRAP_SEED_EVIDENCE_SCHEMA',
    'FOREGROUND_CONTROLLER_STANDBY_SCHEMA',
    'CONTROLLER_PATROL_TIMER_SCHEMA',
    'CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE',
    'CONTROLLER_BOUNDARY_CONFIRMATION_CONTRACT_ID',
    'CONTROLLER_STATEFUL_VALIDATOR_TABLE',
    'STARTUP_MECHANICAL_AUDIT_SCHEMA',
    'ROUTER_OWNED_CHECK_PROOF_SCHEMA',
    'CONTROLLER_BOUNDARY_CONFIRMATION_SCHEMA',
    'STARTUP_ANSWER_PROVENANCE',
    'STARTUP_ANSWER_INTERPRETATION_PROVENANCE',
    'STARTUP_ANSWER_INTERPRETATION_SCHEMA',
    'STARTUP_INTAKE_RESULT_SCHEMA',
    'STARTUP_INTAKE_RECEIPT_SCHEMA',
    'STARTUP_INTAKE_ENVELOPE_SCHEMA',
    'STARTUP_INTAKE_RECORD_SCHEMA',
    'STARTUP_INTAKE_INTERACTIVE_LAUNCH_MODE',
    'USER_REQUEST_REF_SCHEMA',
    'USER_REQUEST_PROVENANCE',
    'DISPLAY_CONFIRMATION_PROVENANCE',
    'DISPLAY_CONFIRMATION_TARGET',
    'ROUTER_TRUSTED_PROOF_SOURCES',
    'ALLOWED_RECORD_EVENT_ENVELOPE_SCHEMAS',
    'ALLOWED_RECORD_EVENT_CONTROLLER_VISIBILITIES',
    'FORBIDDEN_RECORD_EVENT_ENVELOPE_BODY_FIELDS',
    'ROLE_AGENT_SPAWN_RESULT',
    'ROLE_AGENT_REHYDRATION_RESULT',
    'ROLE_AGENT_CONTINUITY_RESULT',
    'ROLE_AGENT_OLD_RESTORE_RESULT',
    'ROLE_AGENT_TARGETED_REPLACEMENT_RESULT',
    'ROLE_AGENT_FULL_CREW_RECYCLE_RESULT',
    'ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT',
    'BACKGROUND_ROLE_MODEL_POLICY',
    'BACKGROUND_ROLE_REASONING_EFFORT_POLICY',
    'BACKGROUND_ROLE_PREFERRED_REASONING_EFFORT',
    'RESUME_ROLE_AGENT_RESULTS',
    'ROLE_RECOVERY_RESULTS',
    'ROLE_AGENT_HOST_LIVENESS_STATUSES',
    'ROLE_AGENT_BOUNDED_WAIT_RESULTS',
    'ROLE_AGENT_LIVENESS_DECISIONS',
    'ROLE_AGENT_LIVENESS_PROBE_MODE',
    'CONTROL_BLOCKER_LANES',
    'PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES',
    'PM_BLOCKER_RECOVERY_OPTIONS',
    'REPAIR_TRANSACTION_EXECUTABLE_PLAN_KINDS',
    'REPAIR_TRANSACTION_LEGACY_PLAN_KIND_ALIASES',
    'REPAIR_TRANSACTION_SAFE_REPLAY_ACTION_TYPES',
    'BLOCKER_REPAIR_POLICY_ROWS',
    'PM_MODEL_MISS_TRIAGE_DECISION_ALLOWED_VALUES',
    'PM_MODEL_MISS_TRIAGE_REPAIR_AUTHORIZED_VALUES',
    'PM_MODEL_MISS_TRIAGE_REQUIRED_BODY_FIELDS',
    'MODEL_MISS_OFFICER_REPORT_REQUIRED_FIELDS',
    'PM_ROLE_WORK_REQUEST_INDEX_SCHEMA',
    'PM_ROLE_WORK_REQUEST_SCHEMA',
    'PM_ROLE_WORK_RESULT_DECISION_SCHEMA',
    'PARALLEL_PACKET_BATCH_SCHEMA',
    'PARALLEL_PACKET_BATCH_REF_SCHEMA',
    'PM_ROLE_WORK_REQUEST_RECIPIENT_ROLES',
    'PM_ROLE_WORK_REQUEST_MODES',
    'PM_ROLE_WORK_REQUEST_KINDS',
    'PM_ROLE_WORK_OPEN_STATUSES',
    'PM_ROLE_WORK_TERMINAL_DECISIONS',
    'PM_PACKAGE_RESULT_DECISIONS',
    'PARALLEL_PACKET_BATCH_OPEN_STATUSES',
    'PARALLEL_PACKET_BATCH_RESULT_RETURNED_STATUSES',
    'PARALLEL_PACKET_BATCH_RESULT_FINAL_STATUSES',
    'PROCESS_CONTRACT_BINDINGS',
    'PM_ROLE_WORK_CONTRACT_PROCESS_KINDS',
    'PM_ROLE_WORK_FOREIGN_CONTRACT_IDS',
    'STARTUP_ANSWER_ENUMS',
    'GATE_DECISION_REQUIRED_FIELDS',
    'PM_PRIOR_PATH_CONTEXT_REVIEW_REQUIRED_FIELDS',
    'PM_RESUME_CONTROLLER_REMINDER_REQUIRED_FIELDS',
    'PM_RESUME_DECISION_ALLOWED_VALUES',
    'PM_RESUME_DECISION_REQUIRED_BODY_FIELDS',
    'PM_PARENT_SEGMENT_DECISION_ALLOWED_VALUES',
    'PM_PARENT_SEGMENT_DECISION_REQUIRED_BODY_FIELDS',
    'PM_TERMINAL_CLOSURE_DECISION_ALLOWED_VALUES',
    'PM_TERMINAL_CLOSURE_DECISION_REQUIRED_BODY_FIELDS',
    'PM_SUGGESTION_FINAL_DISPOSITIONS',
    'PM_SUGGESTION_CLOSURE_STATUSES_BY_DISPOSITION',
    'PM_SUGGESTION_WORKER_ROLES',
    'PM_SUGGESTION_OFFICER_ROLES',
    'SELF_INTERROGATION_SCOPES',
    'SELF_INTERROGATION_HARD_SEVERITIES',
    'SELF_INTERROGATION_FINAL_DISPOSITIONS',
    'GATE_DECISION_ALLOWED_KINDS',
    'GATE_DECISION_ALLOWED_OWNER_ROLES',
    'GATE_DECISION_ALLOWED_RISKS',
    'GATE_DECISION_ALLOWED_STRENGTHS',
    'GATE_DECISION_ALLOWED_DECISIONS',
    'GATE_DECISION_ALLOWED_EVIDENCE_KINDS',
    'GATE_DECISION_ALLOWED_NEXT_ACTIONS',
    'GATE_DECISION_SEMANTIC_OVERREACH_FIELDS',
    'CREW_ROLE_KEYS',
    'ROLE_CARD_KEYS',
    'RUNTIME_FLAG_DEFAULTS',
    'SAFE_RUN_UNTIL_WAIT_ACTION_TYPES',
    'ROUTER_INTERNAL_MECHANICAL_ACTION_TYPES',
    'ROUTER_INTERNAL_MECHANICAL_MAX_HOPS',
    'ROUTER_READY_PREEMPTION_ACTION_TYPES',
    'CURRENT_NODE_CYCLE_FLAGS',
    'MATERIAL_REPAIR_RECHECK_FLAGS',
    'MODEL_MISS_REVIEW_BLOCK_FLAGS',
    'MODEL_MISS_REVIEW_BLOCK_EVENTS',
    'MODEL_MISS_ROUTE_MUTATION_BLOCK_FLAGS',
    'MODEL_MISS_MATERIAL_DISPATCH_REPAIR_FLAGS',
    'MATERIAL_REPAIR_OUTCOME_EVENTS',
    'CONTROL_BLOCKER_REPAIR_NON_SUCCESS_EVENTS',
    'LEAF_CURRENT_NODE_EVENT_CAPABILITY_EVENTS',
    'PARENT_REPAIR_SAFE_EVENTS',
    'PARENT_NODE_EVENT_CAPABILITY_EVENTS',
    'ROUTE_COMPLETION_FLAGS',
    'SCOPED_EVENT_IDENTITY_POLICIES',
    'PM_PRIOR_CONTEXT_REQUIRED_CARD_IDS',
    'STARTUP_QUESTIONS',
    'BOOT_ACTIONS',
    'SYSTEM_CARD_SEQUENCE',
    'CARD_PHASE_BY_ID',
    'CARD_REQUIRED_SOURCE_PATHS',
    'EXTERNAL_EVENTS',
    'PRODUCT_ARCHITECTURE_REPAIR_RESET_FLAGS',
    'ROOT_CONTRACT_REPAIR_RESET_FLAGS',
    'CHILD_SKILL_GATE_REPAIR_RESET_FLAGS',
    'ROUTE_GATE_REPAIR_RESET_FLAGS',
    'RESEARCH_GATE_REPAIR_RESET_FLAGS',
    'PARENT_BACKWARD_REPAIR_RESET_FLAGS',
    'EVIDENCE_QUALITY_REPAIR_RESET_FLAGS',
    'FINAL_BACKWARD_REPAIR_RESET_FLAGS',
    'GATE_OUTCOME_BLOCK_EVENT_SPECS',
    'GATE_OUTCOME_BLOCK_EVENTS',
    'GATE_OUTCOME_PASS_CLEAR_FLAGS',
    'GATE_OUTCOME_PASS_CLEARS_EVENTS',
    'GATE_CONTRACT_SCHEMA',
    'GATE_CONTRACTS',
    'GATE_CONTRACT_ALIASES',
    'GATE_CONTRACTS_BY_CARD',
    'GATE_CONTRACTS_BY_EVENT',
    '_public_gate_contract',
    '_gate_contract_for_id',
    '_gate_contract_for_card',
    '_gate_contract_for_event',
    '_gate_contract_for_events',
    '_event_is_terminal_gate_outcome',
    '_gate_completion_wait_group',
    'PRODUCT_BEHAVIOR_MODEL_PASS_EVENTS',
    'PRODUCT_BEHAVIOR_MODEL_BLOCK_EVENTS',
    'PROCESS_ROUTE_MODEL_PASS_EVENTS',
    'PROCESS_ROUTE_MODEL_REPAIR_EVENTS',
    'PROCESS_ROUTE_MODEL_BLOCK_EVENTS',
)
