"""System-card phase and source-path metadata for FlowPilot protocol boot cards."""

from __future__ import annotations

CARD_PHASE_BY_ID = {
    "pm.material_scan": "material_scan",
    "reviewer.material_sufficiency": "material_scan",
    "pm.product_architecture": "product_architecture",
    "flowguard_operator.product_architecture_modelability": "product_architecture",
    "pm.product_behavior_model_decision": "product_architecture",
    "reviewer.product_architecture_challenge": "product_architecture",
    "pm.root_contract": "root_contract",
    "reviewer.root_contract_challenge": "root_contract",
    "flowguard_operator.root_contract_modelability": "root_contract",
    "pm.dependency_policy": "dependency_policy",
    "pm.child_skill_selection": "child_skill_selection",
    "pm.child_skill_gate_manifest": "child_skill_gate_manifest",
    "reviewer.child_skill_gate_manifest_review": "child_skill_gate_manifest",
    "flowguard_operator.child_skill_conformance_model": "child_skill_gate_manifest",
    "flowguard_operator.child_skill_product_fit": "child_skill_gate_manifest",
    "pm.prior_path_context": "prior_path_context",
    "pm.route_skeleton": "route_skeleton",
    "flowguard_operator.route_process_check": "route_skeleton",
    "pm.process_route_model_decision": "route_skeleton",
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
        "flowguard_capability_snapshot": "flowguard/capability_snapshot.json",
    },
    "flowguard_operator.product_architecture_modelability": {
        "product_function_architecture": "product_function_architecture.json",
        "flowguard_capability_snapshot": "flowguard/capability_snapshot.json",
        "product_modeling_plan": "flowguard/product_modeling_plan.json",
    },
    "reviewer.product_architecture_challenge": {
        "product_function_architecture": "product_function_architecture.json",
        "product_behavior_model": "flowguard/product_behavior_model.json",
        "product_architecture_modelability": "flowguard/product_architecture_modelability.json",
        "pm_product_behavior_model_decision": "flowguard/product_behavior_model_pm_decision.json",
    },
    "pm.product_behavior_model_decision": {
        "product_function_architecture": "product_function_architecture.json",
        "flowguard_capability_snapshot": "flowguard/capability_snapshot.json",
        "product_modeling_plan": "flowguard/product_modeling_plan.json",
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
    "flowguard_operator.root_contract_modelability": {
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
        "flowguard_capability_snapshot": "flowguard/capability_snapshot.json",
        "product_modeling_plan": "flowguard/product_modeling_plan.json",
        "pm_product_behavior_model_decision": "flowguard/product_behavior_model_pm_decision.json",
        "root_acceptance_contract": "root_acceptance_contract.json",
    },
    "reviewer.child_skill_gate_manifest_review": {
        "child_skill_gate_manifest": "child_skill_gate_manifest.json",
        "pm_child_skill_selection": "pm_child_skill_selection.json",
        "capabilities": "capabilities.json",
    },
    "flowguard_operator.child_skill_conformance_model": {
        "child_skill_gate_manifest": "child_skill_gate_manifest.json",
        "child_skill_gate_manifest_review": "reviews/child_skill_gate_manifest_review.json",
        "pm_child_skill_selection": "pm_child_skill_selection.json",
        "capabilities": "capabilities.json",
    },
    "flowguard_operator.child_skill_product_fit": {
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
        "flowguard_capability_snapshot": "flowguard/capability_snapshot.json",
        "product_modeling_plan": "flowguard/product_modeling_plan.json",
        "pm_product_behavior_model_decision": "flowguard/product_behavior_model_pm_decision.json",
        "pm_prior_path_context": "route_memory/pm_prior_path_context.json",
    },
    "flowguard_operator.route_process_check": {
        "root_acceptance_contract": "root_acceptance_contract.json",
        "child_skill_gate_manifest": "child_skill_gate_manifest.json",
        "capability_sync": "capabilities/capability_sync.json",
        "flowguard_capability_snapshot": "flowguard/capability_snapshot.json",
        "product_modeling_plan": "flowguard/product_modeling_plan.json",
        "pm_product_behavior_model_decision": "flowguard/product_behavior_model_pm_decision.json",
        "process_modeling_plan": "flowguard/process_modeling_plan.json",
    },
    "pm.process_route_model_decision": {
        "root_acceptance_contract": "root_acceptance_contract.json",
        "child_skill_gate_manifest": "child_skill_gate_manifest.json",
        "flowguard_capability_snapshot": "flowguard/capability_snapshot.json",
        "product_modeling_plan": "flowguard/product_modeling_plan.json",
        "process_modeling_plan": "flowguard/process_modeling_plan.json",
        "process_route_model": "flowguard/process_route_model.json",
        "route_process_check": "flowguard/route_process_check.json",
    },
    "reviewer.route_challenge": {
        "root_acceptance_contract": "root_acceptance_contract.json",
        "child_skill_gate_manifest": "child_skill_gate_manifest.json",
        "flowguard_capability_snapshot": "flowguard/capability_snapshot.json",
        "product_modeling_plan": "flowguard/product_modeling_plan.json",
        "process_modeling_plan": "flowguard/process_modeling_plan.json",
        "pm_process_route_model_decision": "flowguard/process_route_model_pm_decision.json",
        "process_route_model": "flowguard/process_route_model.json",
        "route_process_check": "flowguard/route_process_check.json",
        "product_behavior_model": "flowguard/product_behavior_model.json",
    },
}


def system_card_metadata_catalog() -> dict[str, object]:
    """Return externally visible system-card metadata indexes."""

    return {
        "phase_card_ids": tuple(CARD_PHASE_BY_ID),
        "source_path_card_ids": tuple(CARD_REQUIRED_SOURCE_PATHS),
        "phase_count": len(CARD_PHASE_BY_ID),
        "source_path_count": len(CARD_REQUIRED_SOURCE_PATHS),
    }


__all__ = (
    "CARD_PHASE_BY_ID",
    "CARD_REQUIRED_SOURCE_PATHS",
    "system_card_metadata_catalog",
)
