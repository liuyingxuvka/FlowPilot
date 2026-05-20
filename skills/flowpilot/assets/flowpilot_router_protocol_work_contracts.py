"""Model-miss, PM role-work, and process-contract tables extracted from ``flowpilot_router_protocol_catalog.py``."""

from __future__ import annotations

from typing import Any, Iterable

import flowpilot_runtime_closure
import packet_runtime
import role_output_runtime
from flowpilot_router_contract_index import contract_selection_rules_by_task_family

from flowpilot_router_protocol_schemas import *
from flowpilot_router_protocol_control_repair import *

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

PROCESS_CONTRACT_POLICIES: dict[str, dict[str, str]] = {
    "current_node_work": {
        "task_family": "worker.current_node",
        "packet_type": "work_packet",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
    "pm_role_work_request": {
        "task_family": "pm.role_work_request",
        "packet_type": "pm_role_work_request",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
    "officer_model_report": {
        "task_family": "officer.model_report",
        "packet_type": "officer_request",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
    "officer_model_miss_report": {
        "task_family": "officer.model_miss_report",
        "packet_type": "officer_request",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
    "reviewer_result_review": {
        "task_family": "reviewer.review",
        "packet_type": "review_request",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
    "material_scan": {
        "task_family": "worker.material_scan",
        "packet_type": "material_scan",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
    "research": {
        "task_family": "worker.research",
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
        "packet_type": "role_decision",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
}


def _process_contract_bindings() -> dict[str, dict[str, Any]]:
    rules_by_family = contract_selection_rules_by_task_family()
    bindings: dict[str, dict[str, Any]] = {}
    for process_kind, policy in PROCESS_CONTRACT_POLICIES.items():
        contract_task_family = policy.get("contract_task_family", policy["task_family"])
        rule = rules_by_family.get(contract_task_family, {})
        contract_id = str(rule.get("contract_id") or policy.get("contract_id") or "")
        if not contract_id:
            raise KeyError(contract_task_family)
        bindings[process_kind] = {
            "task_family": policy["task_family"],
            "contract_id": contract_id,
            "packet_type": policy.get("packet_type", rule.get("packet_type", "")),
            "required_result_next_recipient": policy["required_result_next_recipient"],
            "absorbing_role": policy["absorbing_role"],
        }
    return bindings


def process_contract_binding_source_summary() -> dict[str, dict[str, Any]]:
    rules_by_family = contract_selection_rules_by_task_family()
    summary: dict[str, dict[str, Any]] = {}
    for process_kind, policy in PROCESS_CONTRACT_POLICIES.items():
        contract_task_family = policy.get("contract_task_family", policy["task_family"])
        rule = rules_by_family.get(contract_task_family)
        summary[process_kind] = {
            "task_family": policy["task_family"],
            "contract_task_family": contract_task_family,
            "process_policy_source": "python_process_policy",
            "contract_id_source": "contract_index" if rule else "python_process_policy",
            "contract_id": str((rule or {}).get("contract_id") or policy.get("contract_id") or ""),
            "registry_backed_contract_id": bool(rule),
        }
    return summary


PROCESS_CONTRACT_BINDINGS: dict[str, dict[str, Any]] = _process_contract_bindings()

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

__all__ = (
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
    'PROCESS_CONTRACT_POLICIES',
    'PROCESS_CONTRACT_BINDINGS',
    'process_contract_binding_source_summary',
    'PM_ROLE_WORK_CONTRACT_PROCESS_KINDS',
    'PM_ROLE_WORK_FOREIGN_CONTRACT_IDS',
)
