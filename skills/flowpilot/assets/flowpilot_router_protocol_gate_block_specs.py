"""Gate block-event specs for FlowPilot router protocol."""

from __future__ import annotations

from typing import Any

from flowpilot_router_protocol_gate_reset_flags import *

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

__all__ = (
    'GATE_OUTCOME_BLOCK_EVENT_SPECS',
    'GATE_OUTCOME_BLOCK_EVENTS',
)
