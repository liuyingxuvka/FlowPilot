"""Model-miss, PM role-work, and process-contract tables extracted from ``flowpilot_router_protocol_catalog.py``."""

from __future__ import annotations

from typing import Any

from flowpilot_router_protocol_schemas import *
from flowpilot_router_protocol_control_repair import *
from flowpilot_router_protocol_process_contracts import *

PM_MODEL_MISS_TRIAGE_DECISION_ALLOWED_VALUES = {
    "request_flowguard_operator_model_miss_analysis",
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

MODEL_MISS_FLOWGUARD_OPERATOR_REPORT_REQUIRED_FIELDS = (
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
    "flowguard_operator",
    "worker",
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

PM_PACKAGE_RESULT_DISPOSITION_OUTPUT_TYPE = "pm_package_result_disposition"
PM_PACKAGE_RESULT_DISPOSITION_CONTRACT_ID = (
    "flowpilot.output_contract.pm_package_result_disposition.v1"
)

PM_PACKAGE_RESULT_DECISIONS = {
    "absorbed",
    "rework_requested",
    "canceled",
    "blocked",
    "route_or_node_mutation_required",
}

PM_PACKAGE_RESULT_PACKET_OUTCOMES = {
    "accepted",
    "rework_requested",
    "canceled",
    "blocked",
    "route_or_node_mutation_required",
}

PM_PACKAGE_RESULT_DISPOSITION_REQUIRED_FIELDS = (
    "decided_by_role",
    "decision",
    "decision_reason",
    "residual_risks",
    "contract_self_check",
)


def pm_package_result_disposition_payload_contract(name: str) -> dict[str, Any]:
    return {
        "schema_version": PAYLOAD_CONTRACT_SCHEMA,
        "name": name,
        "required_object": "role_output_body",
        "expected_return_envelope": "role_output_envelope",
        "expected_output_type": PM_PACKAGE_RESULT_DISPOSITION_OUTPUT_TYPE,
        "expected_output_contract_id": PM_PACKAGE_RESULT_DISPOSITION_CONTRACT_ID,
        "runtime_command": "flowpilot_new.py submit-result --lease-id <lease-id> --packet-id <packet-id> --body <sealed_result_summary>",
        "required_fields": list(PM_PACKAGE_RESULT_DISPOSITION_REQUIRED_FIELDS),
        "recommended_fields": ["packet_outcomes"],
        "packet_outcomes_contract": {
            "description": "One row per member packet when worker-specific outcomes differ.",
            "required_fields": ["packet_id", "outcome", "reason"],
            "allowed_outcomes": sorted(PM_PACKAGE_RESULT_PACKET_OUTCOMES),
            "accepted_outcome_for_absorption": "accepted",
        },
        "allowed_values": {
            "decided_by_role": ["project_manager"],
            "decision": sorted(PM_PACKAGE_RESULT_DECISIONS),
        },
        "result_body_open_required_by_role": "project_manager",
        "controller_visibility": "role_output_envelope_only",
        "body_must_not_be_in_event_envelope": True,
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

__all__ = (
    'PM_MODEL_MISS_TRIAGE_DECISION_ALLOWED_VALUES',
    'PM_MODEL_MISS_TRIAGE_REPAIR_AUTHORIZED_VALUES',
    'PM_MODEL_MISS_TRIAGE_REQUIRED_BODY_FIELDS',
    'MODEL_MISS_FLOWGUARD_OPERATOR_REPORT_REQUIRED_FIELDS',
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
    'PM_PACKAGE_RESULT_DISPOSITION_OUTPUT_TYPE',
    'PM_PACKAGE_RESULT_DISPOSITION_CONTRACT_ID',
    'PM_PACKAGE_RESULT_DECISIONS',
    'PM_PACKAGE_RESULT_PACKET_OUTCOMES',
    'PM_PACKAGE_RESULT_DISPOSITION_REQUIRED_FIELDS',
    'pm_package_result_disposition_payload_contract',
    'PARALLEL_PACKET_BATCH_OPEN_STATUSES',
    'PARALLEL_PACKET_BATCH_RESULT_RETURNED_STATUSES',
    'PARALLEL_PACKET_BATCH_RESULT_FINAL_STATUSES',
    'PROCESS_CONTRACT_POLICIES',
    'PROCESS_CONTRACT_BINDINGS',
    'process_contract_binding_source_summary',
    'PM_ROLE_WORK_CONTRACT_PROCESS_KINDS',
    'PM_ROLE_WORK_FOREIGN_CONTRACT_IDS',
)
