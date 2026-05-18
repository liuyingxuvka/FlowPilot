"""Schema, event-name, and startup identity constants extracted from ``flowpilot_router_protocol_catalog.py``."""

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
)
