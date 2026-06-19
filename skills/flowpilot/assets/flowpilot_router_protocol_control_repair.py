"""Control-blocker and repair policy tables extracted from ``flowpilot_router_protocol_catalog.py``."""

from __future__ import annotations

from typing import Any, Iterable

import flowpilot_runtime_closure
import packet_runtime
import role_output_runtime

from flowpilot_router_protocol_schemas import *

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

ROLE_BINDING_OPEN_RESULT = "opened_for_current_task"

ROLE_BINDING_REHYDRATION_RESULT = "rehydrated_from_current_run_memory"

ROLE_BINDING_CONTINUITY_RESULT = "live_agent_continuity_confirmed"

ROLE_BINDING_RESTORE_RESULT = "old_agent_restored"

ROLE_BINDING_TARGETED_REPLACEMENT_RESULT = "targeted_replacement_opened"

ROLE_BINDING_FULL_SET_RECOVERY_RESULT = "full_role_binding_recovery_opened"

ROLE_BINDING_ENVIRONMENT_BLOCKED_RESULT = "environment_blocked"

ROLE_BINDING_MODEL_POLICY = "strongest_available"

ROLE_BINDING_REASONING_EFFORT_POLICY = "highest_available"

ROLE_BINDING_PREFERRED_REASONING_EFFORT = "xhigh"

RESUME_ROLE_BINDING_RESULTS = {ROLE_BINDING_REHYDRATION_RESULT, ROLE_BINDING_CONTINUITY_RESULT}

ROLE_RECOVERY_RESULTS = {
    ROLE_BINDING_RESTORE_RESULT,
    ROLE_BINDING_TARGETED_REPLACEMENT_RESULT,
    ROLE_BINDING_FULL_SET_RECOVERY_RESULT,
    ROLE_BINDING_ENVIRONMENT_BLOCKED_RESULT,
}

ROLE_BINDING_CURRENT_RUN_DECISIONS = {"existing_current_agent_reused", "current_run_replacement_opened"}

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
        "controller_boundary": "deliver blocker metadata to PM; do not rerun self-interrogation or decide finding disposition",
    },
}

__all__ = (
    'ALLOWED_RECORD_EVENT_ENVELOPE_SCHEMAS',
    'ALLOWED_RECORD_EVENT_CONTROLLER_VISIBILITIES',
    'FORBIDDEN_RECORD_EVENT_ENVELOPE_BODY_FIELDS',
    'ROLE_BINDING_OPEN_RESULT',
    'ROLE_BINDING_REHYDRATION_RESULT',
    'ROLE_BINDING_CONTINUITY_RESULT',
    'ROLE_BINDING_RESTORE_RESULT',
    'ROLE_BINDING_TARGETED_REPLACEMENT_RESULT',
    'ROLE_BINDING_FULL_SET_RECOVERY_RESULT',
    'ROLE_BINDING_ENVIRONMENT_BLOCKED_RESULT',
    'ROLE_BINDING_MODEL_POLICY',
    'ROLE_BINDING_REASONING_EFFORT_POLICY',
    'ROLE_BINDING_PREFERRED_REASONING_EFFORT',
    'RESUME_ROLE_BINDING_RESULTS',
    'ROLE_RECOVERY_RESULTS',
    'ROLE_BINDING_CURRENT_RUN_DECISIONS',
    'CONTROL_BLOCKER_LANES',
    'PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES',
    'PM_BLOCKER_RECOVERY_OPTIONS',
    'REPAIR_TRANSACTION_EXECUTABLE_PLAN_KINDS',
    'REPAIR_TRANSACTION_SAFE_REPLAY_ACTION_TYPES',
    'BLOCKER_REPAIR_POLICY_ROWS',
)
