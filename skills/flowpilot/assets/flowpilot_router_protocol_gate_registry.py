"""Canonical gate outcome registry for FlowPilot router protocol tables."""

from __future__ import annotations

from typing import Any, Mapping


GATE_REPAIR_RESET_FLAGS: dict[str, tuple[str, ...]] = {
    "product_architecture": (
        "pm_product_architecture_card_delivered",
        "product_architecture_written_by_pm",
        "pm_product_behavior_model_decision_card_delivered",
        "pm_product_behavior_model_accepted",
        "pm_product_behavior_model_rebuild_requested",
        "product_architecture_reviewer_passed",
        "product_behavior_model_submitted",
        "product_behavior_model_blocked",
        "reviewer_product_architecture_card_delivered",
        "flowguard_operator_product_architecture_card_delivered",
        "root_contract_written_by_pm",
        "root_contract_reviewer_passed",
        "root_contract_frozen_by_pm",
        "pm_child_skill_selection_written",
        "child_skill_gate_manifest_written",
        "child_skill_manifest_reviewer_passed",
        "child_skill_manifest_pm_approved_for_route",
        "capability_evidence_synced",
        "pm_implementation_intent_card_delivered",
        "pm_implementation_intent_written",
        "flowguard_operator_target_realization_model_card_delivered",
        "target_realization_model_submitted",
        "target_realization_model_blocked",
        "pm_target_realization_model_decision_card_delivered",
        "pm_target_realization_model_accepted",
        "pm_target_realization_model_rebuild_requested",
        "reviewer_implementation_intent_card_delivered",
        "implementation_intent_reviewer_passed",
        "implementation_intent_reviewer_blocked",
        "pm_prior_path_context_card_delivered",
        "route_draft_written_by_pm",
        "process_route_model_submitted",
        "process_route_model_repair_required",
        "process_route_model_blocked",
        "pm_process_route_model_decision_card_delivered",
        "pm_process_route_model_accepted",
        "pm_process_route_model_rebuild_requested",
        "reviewer_route_check_passed",
        "route_activated_by_pm",
    ),
    "root_contract": (
        "root_contract_written_by_pm",
        "root_contract_reviewer_passed",
        "root_contract_frozen_by_pm",
        "reviewer_root_contract_card_delivered",
        "flowguard_operator_root_contract_card_delivered",
        "pm_child_skill_selection_written",
        "child_skill_gate_manifest_written",
        "child_skill_manifest_reviewer_passed",
        "child_skill_manifest_pm_approved_for_route",
        "capability_evidence_synced",
        "pm_implementation_intent_card_delivered",
        "pm_implementation_intent_written",
        "flowguard_operator_target_realization_model_card_delivered",
        "target_realization_model_submitted",
        "target_realization_model_blocked",
        "pm_target_realization_model_decision_card_delivered",
        "pm_target_realization_model_accepted",
        "pm_target_realization_model_rebuild_requested",
        "reviewer_implementation_intent_card_delivered",
        "implementation_intent_reviewer_passed",
        "implementation_intent_reviewer_blocked",
        "pm_prior_path_context_card_delivered",
        "route_draft_written_by_pm",
        "pm_process_route_model_decision_card_delivered",
        "pm_process_route_model_accepted",
        "pm_process_route_model_rebuild_requested",
        "reviewer_route_check_passed",
        "route_activated_by_pm",
    ),
    "child_skill_gate": (
        "child_skill_gate_manifest_written",
        "child_skill_manifest_reviewer_passed",
        "child_skill_manifest_pm_approved_for_route",
        "capability_evidence_synced",
        "reviewer_child_skill_gate_manifest_card_delivered",
        "flowguard_operator_child_skill_conformance_card_delivered",
        "flowguard_operator_child_skill_product_fit_card_delivered",
        "pm_implementation_intent_card_delivered",
        "pm_implementation_intent_written",
        "flowguard_operator_target_realization_model_card_delivered",
        "target_realization_model_submitted",
        "target_realization_model_blocked",
        "pm_target_realization_model_decision_card_delivered",
        "pm_target_realization_model_accepted",
        "pm_target_realization_model_rebuild_requested",
        "reviewer_implementation_intent_card_delivered",
        "implementation_intent_reviewer_passed",
        "implementation_intent_reviewer_blocked",
        "pm_prior_path_context_card_delivered",
        "route_draft_written_by_pm",
        "process_route_model_submitted",
        "process_route_model_repair_required",
        "process_route_model_blocked",
        "pm_process_route_model_decision_card_delivered",
        "pm_process_route_model_accepted",
        "pm_process_route_model_rebuild_requested",
        "reviewer_route_check_passed",
        "route_activated_by_pm",
    ),
    "route_gate": (
        "route_draft_written_by_pm",
        "process_route_model_submitted",
        "process_route_model_repair_required",
        "process_route_model_blocked",
        "pm_process_route_model_decision_card_delivered",
        "pm_process_route_model_accepted",
        "pm_process_route_model_rebuild_requested",
        "reviewer_route_check_passed",
        "flowguard_operator_route_check_card_delivered",
        "flowguard_operator_product_route_check_card_delivered",
        "reviewer_route_check_card_delivered",
        "route_activated_by_pm",
    ),
    "research_gate": (
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
    ),
    "parent_backward": (
        "parent_backward_targets_built",
        "parent_backward_replay_passed",
        "reviewer_parent_backward_replay_card_delivered",
        "parent_segment_decision_recorded",
        "pm_parent_segment_decision_card_delivered",
    ),
    "evidence_quality": (
        "evidence_quality_package_written",
        "evidence_quality_reviewer_passed",
        "reviewer_evidence_quality_card_delivered",
        "final_ledger_built_clean",
        "final_backward_replay_passed",
        "reviewer_final_backward_replay_card_delivered",
        "pm_closure_approved",
        "pm_closure_card_delivered",
    ),
    "final_backward": (
        "final_ledger_built_clean",
        "final_backward_replay_passed",
        "reviewer_final_backward_replay_card_delivered",
        "pm_closure_approved",
        "pm_closure_card_delivered",
    ),
}

PRODUCT_ARCHITECTURE_REPAIR_RESET_FLAGS = GATE_REPAIR_RESET_FLAGS["product_architecture"]
ROOT_CONTRACT_REPAIR_RESET_FLAGS = GATE_REPAIR_RESET_FLAGS["root_contract"]
CHILD_SKILL_GATE_REPAIR_RESET_FLAGS = GATE_REPAIR_RESET_FLAGS["child_skill_gate"]
ROUTE_GATE_REPAIR_RESET_FLAGS = GATE_REPAIR_RESET_FLAGS["route_gate"]
RESEARCH_GATE_REPAIR_RESET_FLAGS = GATE_REPAIR_RESET_FLAGS["research_gate"]
PARENT_BACKWARD_REPAIR_RESET_FLAGS = GATE_REPAIR_RESET_FLAGS["parent_backward"]
EVIDENCE_QUALITY_REPAIR_RESET_FLAGS = GATE_REPAIR_RESET_FLAGS["evidence_quality"]
FINAL_BACKWARD_REPAIR_RESET_FLAGS = GATE_REPAIR_RESET_FLAGS["final_backward"]


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
    "flowguard_operator_blocks_product_behavior_model": {
        "expected_role": "flowguard_operator",
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
    "reviewer_blocks_child_skill_gate_manifest": {
        "expected_role": "human_like_reviewer",
        "path": "reviews/child_skill_gate_manifest_block.json",
        "schema_version": "flowpilot.child_skill_gate_manifest_block.v1",
        "checked_paths": ("child_skill_gate_manifest.json", "pm_child_skill_selection.json", "capabilities.json"),
        "reset_flags": CHILD_SKILL_GATE_REPAIR_RESET_FLAGS,
    },
    "reviewer_blocks_implementation_intent_challenge": {
        "expected_role": "human_like_reviewer",
        "path": "reviews/implementation_intent_challenge_block.json",
        "schema_version": "flowpilot.implementation_intent_review_block.v1",
        "checked_paths": (
            "implementation_intent/pm_implementation_intent.json",
            "flowguard/target_realization_model.json",
            "flowguard/target_realization_model_pm_decision.json",
            "flowguard/product_behavior_model.json",
        ),
        "reset_flags": (
            "implementation_intent_reviewer_passed",
            "pm_prior_path_context_card_delivered",
            "route_draft_written_by_pm",
            "process_route_model_submitted",
            "process_route_model_repair_required",
            "process_route_model_blocked",
            "pm_process_route_model_decision_card_delivered",
            "pm_process_route_model_accepted",
            "pm_process_route_model_rebuild_requested",
            "reviewer_route_check_passed",
            "route_activated_by_pm",
        ),
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
            "flowguard/target_realization_model.json",
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
    "flowguard_operator_submits_product_behavior_model": (
        "product_behavior_model_blocked",
    ),
    "reviewer_passes_root_acceptance_contract": ("root_contract_reviewer_blocked",),
    "reviewer_passes_child_skill_gate_manifest": ("child_skill_manifest_reviewer_blocked",),
    "flowguard_operator_submits_target_realization_model": (
        "target_realization_model_blocked",
    ),
    "reviewer_passes_implementation_intent_challenge": ("implementation_intent_reviewer_blocked",),
    "flowguard_operator_submits_process_route_model": (
        "process_route_model_repair_required",
        "process_route_model_blocked",
    ),
    "reviewer_passes_route_check": ("reviewer_route_check_blocked",),
    "reviewer_passes_parent_backward_replay": ("parent_backward_replay_blocked",),
    "reviewer_passes_evidence_quality_package": ("evidence_quality_reviewer_blocked",),
    "reviewer_final_backward_replay_passed": ("final_backward_replay_blocked",),
}


def gate_outcome_pass_clears_events(
    external_events: Mapping[str, Mapping[str, Any]],
) -> dict[str, tuple[str, ...]]:
    return {
        pass_event: tuple(
            block_event
            for block_event in GATE_OUTCOME_BLOCK_EVENTS
            if external_events[block_event]["flag"] in clear_flags
        )
        for pass_event, clear_flags in GATE_OUTCOME_PASS_CLEAR_FLAGS.items()
    }


__all__ = (
    "GATE_REPAIR_RESET_FLAGS",
    "PRODUCT_ARCHITECTURE_REPAIR_RESET_FLAGS",
    "ROOT_CONTRACT_REPAIR_RESET_FLAGS",
    "CHILD_SKILL_GATE_REPAIR_RESET_FLAGS",
    "ROUTE_GATE_REPAIR_RESET_FLAGS",
    "RESEARCH_GATE_REPAIR_RESET_FLAGS",
    "PARENT_BACKWARD_REPAIR_RESET_FLAGS",
    "EVIDENCE_QUALITY_REPAIR_RESET_FLAGS",
    "FINAL_BACKWARD_REPAIR_RESET_FLAGS",
    "GATE_OUTCOME_BLOCK_EVENT_SPECS",
    "GATE_OUTCOME_BLOCK_EVENTS",
    "GATE_OUTCOME_PASS_CLEAR_FLAGS",
    "gate_outcome_pass_clears_events",
)
