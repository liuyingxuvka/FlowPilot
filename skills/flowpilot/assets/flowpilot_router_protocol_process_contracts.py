"""Process-contract binding tables for FlowPilot protocol work contracts."""

from __future__ import annotations

from typing import Any

from flowpilot_router_contract_index import contract_selection_rules_by_task_family

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
    "flowguard_operator_model_report": {
        "task_family": "flowguard_operator.model_report",
        "packet_type": "flowguard_operator_request",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
    "flowguard_operator_model_miss_report": {
        "task_family": "flowguard_operator.model_miss_report",
        "packet_type": "flowguard_operator_request",
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
    "flowpilot.output_contract.flowguard_operator_model_report.v1": "flowguard_operator_model_report",
    "flowpilot.output_contract.flowguard_model_miss_report.v1": "flowguard_operator_model_miss_report",
}

PM_ROLE_WORK_FOREIGN_CONTRACT_IDS = {
    "flowpilot.output_contract.worker_current_node_result.v1",
    "flowpilot.output_contract.worker_material_scan_result.v1",
    "flowpilot.output_contract.worker_research_result.v1",
}

__all__ = (
    "PROCESS_CONTRACT_POLICIES",
    "PROCESS_CONTRACT_BINDINGS",
    "process_contract_binding_source_summary",
    "PM_ROLE_WORK_CONTRACT_PROCESS_KINDS",
    "PM_ROLE_WORK_FOREIGN_CONTRACT_IDS",
)
