"""Current FlowPilot packet family and blocker repair contract matrix.

This file is the single machine-readable table for the current FlowPilot
submission path. It intentionally has no legacy aliases, compatibility fields,
or "accept either shape" branches: every field listed here is either current,
moved to one current owner, or deleted.
"""

from __future__ import annotations

from typing import Any, Mapping


STAGE_EVIDENCE_MATRIX_SCHEMA_VERSION = "flowpilot.packet_contract_matrix.v2"


PACKET_FAMILY_IDS: tuple[str, ...] = (
    "task.high_standard_contract",
    "task.discovery",
    "task.skill_standard",
    "task.planning",
    "task.node_acceptance_plan",
    "task.node",
    "flowguard_check.post_result",
    "review.any_current_subject",
    "review.parent_backward_replay",
    "review.terminal_backward_replay",
    "pm_repair_decision.pm_repair_decision",
    "pm_disposition.node_pm_disposition",
    "pm_flowguard_acceptance.pm_flowguard_acceptance",
)


BLOCKER_CLASS_TO_NEXT_ACTION: dict[str, str] = {
    "mechanical_contract_missing_field": "same_packet_reissue",
    "invalid_blocker_shape": "same_role_reissue",
    "local_artifact": "pm_repair_decision",
    "evidence_gap": "pm_repair_decision",
    "missing_required_information": "same_packet_block_or_stop_for_user",
    "flowguard_failure": "pm_repair_decision",
    "route_decomposition": "pm_repair_decision",
    "composition": "pm_repair_decision",
    "missing_matching_flowguard_report": "issue_matching_flowguard_packet",
    "system_validation_failure": "pm_repair_decision",
    "terminal_closure": "pm_repair_decision",
    "needs_user": "stop_for_user_or_waive_with_authority",
}


COMMON_PASS_BLOCK_DECISION_OPTIONS: tuple[str, ...] = ("pass", "block")
HIGH_STANDARD_REQUIREMENT_CLASSIFICATION_OPTIONS: tuple[str, ...] = (
    "hard_current",
    "high_standard_current",
    "optional_current",
    "future_suggestion",
    "rejected_expansion",
)
ACCEPTANCE_ITEM_SOURCE_TYPE_OPTIONS: tuple[str, ...] = (
    "user_explicit",
    "user_implicit",
    "pm_high_standard",
    "low_quality_success_risk",
    "target_realization",
    "child_skill_standard",
    "flowguard_obligation",
)
ACCEPTANCE_ITEM_QUALITY_FLOOR_OPTIONS: tuple[str, ...] = (
    "high_quality_required",
    "normal_quality_required",
    "evidence_only",
)
ACCEPTANCE_ITEM_STATUS_OPTIONS: tuple[str, ...] = (
    "active",
    "waived",
    "superseded",
)
SKILL_STANDARD_CLASSIFICATION_OPTIONS: tuple[str, ...] = (
    "required",
    "conditional_required",
)
NODE_KIND_OPTIONS: tuple[str, ...] = ("parent", "module", "leaf", "repair")
RESPONSIBILITY_OPTIONS: tuple[str, ...] = (
    "pm",
    "worker",
    "research_worker",
    "reviewer",
    "flowguard_operator",
    "ui_qa",
)
REVIEWER_ROLE_OPTIONS: tuple[str, ...] = ("human_like_reviewer",)
FLOWGUARD_REVIEWER_ROLE_OPTIONS: tuple[str, ...] = ("flowguard_operator",)
BOOLEAN_OPTIONS: tuple[bool, bool] = (True, False)
TRUE_ONLY_OPTIONS: tuple[bool, ...] = (True,)
TERMINAL_REPLAY_STATUS_OPTIONS: tuple[str, ...] = ("closed", "blocked", "waived", "superseded")
PM_REPAIR_DECISION_OPTIONS: tuple[str, ...] = (
    "break_glass",
    "repair_current_scope",
    "repair_parent_scope",
    "redesign_route",
    "waive_with_authority",
    "stop_for_user",
)
PM_DISPOSITION_DECISION_OPTIONS: tuple[str, ...] = (
    "accept",
    "repair_current_scope",
    "redesign_route",
    "block",
    "stop",
)
PM_FLOWGUARD_ACCEPTANCE_DECISION_OPTIONS: tuple[str, ...] = (
    "accept",
    "break_glass",
    "redesign_route",
    "block",
    "stop_for_user",
)
FLOWGUARD_SEMANTIC_COVERAGE_BOUNDARY_OPTIONS: tuple[str, ...] = ("subject_bound_semantic",)
TERMINAL_SUPPLEMENTAL_REPAIR_GAP_KIND_OPTIONS: tuple[str, ...] = (
    "latent_high_standard_requirement",
    "missing_implementation",
    "missing_validation",
    "weak_evidence",
    "route_structure_gap",
    "terminal_replay_gap",
    "final_artifact_hygiene_gap",
)


RESULT_CONTRACT_PROFILE_IDS: tuple[str, ...] = (
    "flowguard.semantic_recheck_required",
    "flowguard.subject_artifacts_consumed_required",
)


RESULT_CONTRACT_PROFILES: dict[str, dict[str, Any]] = {
    "flowguard.semantic_recheck_required": {
        "family_id": "flowguard_check.post_result",
        "required_fields": ("semantic_recheck",),
        "required_child_fields": (
            "semantic_recheck.blocker_id",
            "semantic_recheck.subject_result_consumed",
            "semantic_recheck.subject_bound_semantic_coverage",
            "semantic_recheck.coverage_boundary",
            "semantic_recheck.consumed_authorized_result_read_ids[]",
        ),
        "explicit_array_fields": (
            "semantic_recheck.consumed_authorized_result_read_ids",
            "semantic_recheck.consumed_repair_obligation_ids",
        ),
        "non_empty_array_fields": ("semantic_recheck.consumed_authorized_result_read_ids",),
        "allowed_value_options": {
            "semantic_recheck.subject_result_consumed": TRUE_ONLY_OPTIONS,
            "semantic_recheck.subject_bound_semantic_coverage": TRUE_ONLY_OPTIONS,
            "semantic_recheck.coverage_boundary": FLOWGUARD_SEMANTIC_COVERAGE_BOUNDARY_OPTIONS,
        },
        "field_type_requirements": {
            "semantic_recheck": "object",
            "semantic_recheck.blocker_id": "string",
            "semantic_recheck.subject_result_consumed": "boolean:true",
            "semantic_recheck.subject_bound_semantic_coverage": "boolean:true",
            "semantic_recheck.coverage_boundary": "string:subject_bound_semantic",
            "semantic_recheck.consumed_authorized_result_read_ids": "array:string",
            "semantic_recheck.consumed_repair_obligation_ids": "array:string",
        },
        "forbidden_aliases": {
            "authorized_result_body_consumed": "semantic_recheck.subject_result_consumed",
            "semantic_recheck.authorized_result_body_consumed": "semantic_recheck.subject_result_consumed",
            "blocker_bound_semantic_requirement_satisfied": "semantic_recheck.subject_bound_semantic_coverage",
            "semantic_recheck.blocker_bound_semantic_requirement_satisfied": (
                "semantic_recheck.subject_bound_semantic_coverage"
            ),
            "repair_evidence_obligations_consumed": "semantic_recheck.consumed_repair_obligation_ids",
            "semantic_recheck.repair_evidence_obligations_consumed": (
                "semantic_recheck.consumed_repair_obligation_ids"
            ),
        },
    },
    "flowguard.subject_artifacts_consumed_required": {
        "family_id": "flowguard_check.post_result",
        "required_fields": ("subject_artifacts_consumed",),
        "required_child_fields": (
            "subject_artifacts_consumed[]",
            "subject_artifacts_consumed[].artifact_id",
        ),
        "explicit_array_fields": ("subject_artifacts_consumed",),
        "non_empty_array_fields": ("subject_artifacts_consumed",),
        "allowed_value_options": {},
        "field_type_requirements": {
            "subject_artifacts_consumed": "array:object",
            "subject_artifacts_consumed[].artifact_id": "string",
        },
        "forbidden_aliases": {
            "consumed_subject_artifacts": "subject_artifacts_consumed",
            "subject_artifact_consumption": "subject_artifacts_consumed",
        },
    },
}
FINAL_ARTIFACT_HYGIENE_CATEGORY_OPTIONS: tuple[str, ...] = (
    "artifact_lineage",
    "code_maintainability",
    "document_cleanup",
    "model_coverage",
    "other",
    "process_ledger_cleanup",
    "test_coverage",
    "ui_polish",
)


REPAIR_LINEAGE_REQUIRED_FIELDS: tuple[str, ...] = (
    "original_blocker_id",
    "prior_repair_packet_id",
    "prior_repair_result_id",
    "prior_repair_evidence_refs",
    "failed_recheck_report_id",
    "prior_failure_reason",
    "current_blocking_report_id",
    "new_repair_delta",
    "return_gate",
)


REPAIR_NODE_CONTEXT_REQUIRED_FIELDS: tuple[str, ...] = (
    "source_packet_id",
    "source_body_hash",
    "source_objective",
    "source_output_contract",
    "source_acceptance_criteria",
    "target_result_id",
    "stale_evidence_ids",
    "blocker_class",
    "required_recheck_role",
    "recommended_resolution",
    "repeat_context",
    "repair_obligation_context",
    "authorized_result_reads",
)


PARENT_REPLACEMENT_CONTEXT_REQUIRED_FIELDS: tuple[str, ...] = (
    "repair_parent_scope_contract",
    "repair_parent_scope_contract.source_parent_node_id",
    "repair_parent_scope_contract.inherit_existing_children",
    "repair_parent_scope_contract.repair_child_specs[]",
    "inherited_child_node_ids",
    "inherited_accepted_result_ids",
    "replacement_parent_node_id",
    "child_node_ids",
)


PM_REPAIR_PAYLOAD_FIELDS: tuple[str, ...] = (
    "decision",
    "reason",
    "target_blocker_id",
    "next_action",
)


CURRENT_SCOPE_REPAIR_ROUTE_SHAPE = "repair_current_scope via _replace_scope_and_open_repair_packet"
PARENT_SCOPE_REPAIR_ROUTE_SHAPE = "repair_parent_scope with repair_parent_scope_contract and active repair_child_specs"
NODE_ENTRY_REDESIGN_ROUTE_SHAPE = "redesign_route with replacement parent/module plus child_node_ids"


BLOCKER_REPAIR_PACKET_CONTRACTS: dict[str, dict[str, Any]] = {
    "mechanical_contract_missing_field": {
        "repair_packet_family": "same_packet_reissue",
        "owner_role": "original_producer_role",
        "required_context_fields": (
            "blocked_packet_id",
            "blocked_result_id",
            "missing_required_fields",
            "minimal_valid_shape",
            "failed_field_path",
        ),
        "required_payload_fields": ("corrected_result_body",),
        "return_gate": "runtime_mechanical_validation",
        "repeat_repair_must_carry_lineage": True,
    },
    "invalid_blocker_shape": {
        "repair_packet_family": "same_role_reissue",
        "owner_role": "blocking_report_role",
        "required_context_fields": (
            "blocked_packet_id",
            "blocked_result_id",
            "invalid_blocker_id",
            "allowed_blocker_classes",
            "blocker_class_to_next_action",
        ),
        "required_payload_fields": ("corrected_blocker",),
        "return_gate": "runtime_blocker_shape_validation",
        "repeat_repair_must_carry_lineage": True,
    },
    "local_artifact": {
        "repair_packet_family": "pm_repair_decision.pm_repair_decision",
        "owner_role": "pm",
        "required_context_fields": (
            "subject_packet_id",
            "subject_result_id",
            "review_result_id",
            "review_result_open_receipt_id",
            "blocker_id",
            *REPAIR_NODE_CONTEXT_REQUIRED_FIELDS,
        ),
        "required_payload_fields": PM_REPAIR_PAYLOAD_FIELDS,
        "return_gate": "pm_selected_repair_gate",
        "leaf_repair_route_shape": CURRENT_SCOPE_REPAIR_ROUTE_SHAPE,
        "parent_repair_route_shape": PARENT_SCOPE_REPAIR_ROUTE_SHAPE,
        "parent_repair_required_context_fields": PARENT_REPLACEMENT_CONTEXT_REQUIRED_FIELDS,
        "repeat_repair_must_carry_lineage": True,
    },
    "evidence_gap": {
        "repair_packet_family": "pm_repair_decision.pm_repair_decision",
        "owner_role": "pm",
        "required_context_fields": (
            "subject_packet_id",
            "subject_result_id",
            "blocking_report_id",
            "blocking_report_open_receipt_id",
            "missing_evidence_kinds",
            *REPAIR_NODE_CONTEXT_REQUIRED_FIELDS,
        ),
        "required_payload_fields": PM_REPAIR_PAYLOAD_FIELDS,
        "return_gate": "pm_selected_repair_gate",
        "leaf_repair_route_shape": CURRENT_SCOPE_REPAIR_ROUTE_SHAPE,
        "parent_repair_route_shape": PARENT_SCOPE_REPAIR_ROUTE_SHAPE,
        "parent_repair_required_context_fields": PARENT_REPLACEMENT_CONTEXT_REQUIRED_FIELDS,
        "repeat_repair_must_carry_lineage": True,
    },
    "missing_required_information": {
        "repair_packet_family": "same_packet_block_or_stop_for_user",
        "owner_role": "current_packet_owner_or_pm",
        "required_context_fields": (
            "blocked_packet_id",
            "blocked_result_id",
            "missing_information",
            "recommended_resolution",
            "minimal_valid_shape",
        ),
        "required_payload_fields": (
            "decision",
            "blocker_class",
            "recommended_resolution",
            "pm_visible_summary",
        ),
        "return_gate": "runtime_current_packet_contract_or_user_stop",
        "repeat_repair_must_carry_lineage": True,
    },
    "flowguard_failure": {
        "repair_packet_family": "pm_repair_decision.pm_repair_decision",
        "owner_role": "pm",
        "required_context_fields": (
            "subject_packet_id",
            "subject_result_id",
            "flowguard_result_id",
            "flowguard_result_open_receipt_id",
            "flowguard_evidence_path",
            "blocker_id",
            *REPAIR_NODE_CONTEXT_REQUIRED_FIELDS,
        ),
        "required_payload_fields": PM_REPAIR_PAYLOAD_FIELDS,
        "return_gate": "pm_selected_repair_gate",
        "leaf_repair_route_shape": CURRENT_SCOPE_REPAIR_ROUTE_SHAPE,
        "parent_repair_route_shape": PARENT_SCOPE_REPAIR_ROUTE_SHAPE,
        "parent_repair_required_context_fields": PARENT_REPLACEMENT_CONTEXT_REQUIRED_FIELDS,
        "repeat_repair_must_carry_lineage": True,
    },
    "route_decomposition": {
        "repair_packet_family": "pm_repair_decision.pm_repair_decision",
        "owner_role": "pm",
        "required_context_fields": (
            "active_route_version",
            "subject_packet_id",
            "subject_result_id",
            "blocking_report_ids",
            "blocking_report_open_receipt_ids",
            *REPAIR_NODE_CONTEXT_REQUIRED_FIELDS,
        ),
        "required_payload_fields": PM_REPAIR_PAYLOAD_FIELDS,
        "return_gate": "pm_selected_repair_gate",
        "leaf_repair_route_shape": CURRENT_SCOPE_REPAIR_ROUTE_SHAPE,
        "parent_repair_route_shape": PARENT_SCOPE_REPAIR_ROUTE_SHAPE,
        "parent_repair_required_context_fields": PARENT_REPLACEMENT_CONTEXT_REQUIRED_FIELDS,
        "recommended_route_shape": NODE_ENTRY_REDESIGN_ROUTE_SHAPE,
        "repeat_repair_must_carry_lineage": True,
    },
    "composition": {
        "repair_packet_family": "pm_repair_decision.pm_repair_decision",
        "owner_role": "pm",
        "required_context_fields": (
            "parent_node_id",
            "child_node_ids",
            "child_evidence_refs",
            "parent_replay_result_id",
            "parent_replay_open_receipt_id",
            *PARENT_REPLACEMENT_CONTEXT_REQUIRED_FIELDS,
        ),
        "required_payload_fields": PM_REPAIR_PAYLOAD_FIELDS,
        "return_gate": "pm_selected_repair_gate",
        "leaf_repair_route_shape": CURRENT_SCOPE_REPAIR_ROUTE_SHAPE,
        "parent_repair_route_shape": PARENT_SCOPE_REPAIR_ROUTE_SHAPE,
        "parent_repair_required_context_fields": PARENT_REPLACEMENT_CONTEXT_REQUIRED_FIELDS,
        "repeat_repair_must_carry_lineage": True,
    },
    "missing_matching_flowguard_report": {
        "repair_packet_family": "flowguard_check.post_result",
        "owner_role": "flowguard_operator",
        "required_context_fields": (
            "subject_packet_id",
            "target_result_id",
            "required_flowguard_target",
            "authorized_result_reads",
            "subject_stage_evidence_matrix",
        ),
        "required_payload_fields": (
            "pm_visible_summary",
            "reviewed_by_role",
            "passed",
            "modeled_boundary",
            "blockers",
            "pm_suggestion_items",
            "contract_self_check",
        ),
        "return_gate": "review_packet_release",
        "repeat_repair_must_carry_lineage": True,
    },
    "system_validation_failure": {
        "repair_packet_family": "pm_repair_decision.pm_repair_decision",
        "owner_role": "pm",
        "required_context_fields": (
            "subject_packet_id",
            "subject_result_id",
            "validation_evidence_id",
            "validation_blockers",
            *REPAIR_NODE_CONTEXT_REQUIRED_FIELDS,
        ),
        "required_payload_fields": PM_REPAIR_PAYLOAD_FIELDS,
        "return_gate": "pm_selected_repair_gate",
        "leaf_repair_route_shape": CURRENT_SCOPE_REPAIR_ROUTE_SHAPE,
        "parent_repair_route_shape": PARENT_SCOPE_REPAIR_ROUTE_SHAPE,
        "parent_repair_required_context_fields": PARENT_REPLACEMENT_CONTEXT_REQUIRED_FIELDS,
        "repeat_repair_must_carry_lineage": True,
    },
    "terminal_closure": {
        "repair_packet_family": "pm_repair_decision.pm_repair_decision",
        "owner_role": "pm",
        "required_context_fields": (
            "terminal_replay_result_id",
            "terminal_replay_open_receipt_id",
            "final_replay_segment_ids",
            "unclosed_acceptance_item_ids",
            "waiver_record_ids",
            *REPAIR_NODE_CONTEXT_REQUIRED_FIELDS,
        ),
        "required_payload_fields": PM_REPAIR_PAYLOAD_FIELDS,
        "return_gate": "pm_selected_repair_gate",
        "leaf_repair_route_shape": CURRENT_SCOPE_REPAIR_ROUTE_SHAPE,
        "parent_repair_route_shape": PARENT_SCOPE_REPAIR_ROUTE_SHAPE,
        "parent_repair_required_context_fields": PARENT_REPLACEMENT_CONTEXT_REQUIRED_FIELDS,
        "repeat_repair_must_carry_lineage": True,
    },
    "needs_user": {
        "repair_packet_family": "pm_repair_decision.pm_repair_decision",
        "owner_role": "pm",
        "required_context_fields": (
            "subject_packet_id",
            "subject_result_id",
            "blocker_id",
            "question_or_authority_needed",
            "affected_acceptance_item_ids",
        ),
        "required_payload_fields": PM_REPAIR_PAYLOAD_FIELDS,
        "conditional_required_fields": {
            "waive_with_authority": ("authority_ref",),
        },
        "return_gate": "terminal_user_stop_or_authority_waiver_gate",
        "repeat_repair_must_carry_lineage": True,
    },
}


CURRENT_REQUIRED_FIELDS_BY_FAMILY: dict[str, tuple[str, ...]] = {
    "task.high_standard_contract": ("requirements", "acceptance_item_registry"),
    "task.discovery": (
        "decision",
        "material_sources",
        "material_sufficiency",
        "candidate_skill_inventory",
    ),
    "task.skill_standard": ("decision", "obligations"),
    "task.planning": ("schema_version", "decision", "nodes"),
    "task.node_acceptance_plan": ("decision", "node_context_package"),
    "task.node": ("decision", "pm_visible_summary", "current_evidence_refs"),
    "review.parent_backward_replay": (
        "pm_visible_summary",
        "reviewed_by_role",
        "passed",
        "parent_node_id",
        "child_node_ids",
        "child_evidence_refs",
        "findings",
        "blockers",
        "pm_suggestion_items",
        "contract_self_check",
    ),
    "flowguard_check.post_result": (
        "pm_visible_summary",
        "reviewed_by_role",
        "passed",
        "modeled_boundary",
        "blockers",
        "pm_suggestion_items",
        "contract_self_check",
    ),
    "review.any_current_subject": (
        "pm_visible_summary",
        "reviewed_by_role",
        "passed",
        "findings",
        "blockers",
        "pm_suggestion_items",
        "contract_self_check",
    ),
    "review.terminal_backward_replay": (
        "pm_visible_summary",
        "reviewed_by_role",
        "passed",
        "findings",
        "blockers",
        "pm_suggestion_items",
        "final_artifact_refs",
        "acceptance_item_closure",
        "route_segment_replay",
        "waiver_records",
        "final_blockers",
        "contract_self_check",
    ),
    "pm_repair_decision.pm_repair_decision": PM_REPAIR_PAYLOAD_FIELDS,
    "pm_disposition.node_pm_disposition": (
        "decision",
        "reason",
        "acceptance_item_disposition",
    ),
    "pm_flowguard_acceptance.pm_flowguard_acceptance": (
        "decision",
        "reason",
        "flowguard_absorption",
        "accepted_flowguard_result_id",
    ),
}


MOVED_FIELDS_BY_FAMILY: dict[str, tuple[str, ...]] = {
    "task.high_standard_contract": (
        "acceptance_item_registry.items[].owner_node_ids -> task.planning.nodes[].acceptance_item_ids",
    ),
    "task.node_acceptance_plan": (
        "worker_result_artifacts -> task.node.current_evidence_refs",
        "final_backward_replay_evidence -> review.terminal_backward_replay",
    ),
}


DELETED_FIELDS_BY_FAMILY: dict[str, tuple[str, ...]] = {
    "task.high_standard_contract": (
        "requirements[].evidence_rule",
        "requirements[].closure_blocking",
        "requirements[].report_only_closure_allowed",
        "acceptance_item_registry.items[].review_gate_ids",
        "acceptance_item_registry.items[].final_replay_required",
        "acceptance_item_registry.items[].low_quality_failure_patterns",
    ),
    "task.discovery": ("local_skill_inventory", "candidate_only_skill_policy"),
    "task.skill_standard": (
        "obligations[].closure_blocking",
        "obligations[].evidence_required",
    ),
    "task.node_acceptance_plan": (
        "test_obligation_matrix.pre_worker[]",
        "work_packet_projection",
        "final_user_intent_checks",
        "structure_hygiene_expectation",
        "high_standard_requirement_ids",
    ),
    "flowguard_check.post_result": (
        "commands_run",
        "counterexamples_or_absence",
        "hard_invariants",
        "skipped_checks",
        "model_obligations",
        "ordinary_test_evidence",
        "missing_test_kinds",
        "conformance_boundary",
        "confidence_boundary",
        "residual_blindspots",
        "background_artifact_completion",
        "evidence_consistency",
    ),
    "review.any_current_subject": (
        "direct_evidence_paths_checked",
        "independent_challenge",
        "residual_risks",
        "parent_backward_replay_review_id",
        "independent_parent_replay_review",
    ),
    "review.parent_backward_replay": (
        "task.parent_backward_replay",
        "composition_decision",
        "review_id",
        "independent_review_id",
        "parent_backward_replay_review_id",
    ),
    "pm_disposition.node_pm_disposition": (
        "covered_requirement_ids",
        "accepted_acceptance_item_ids",
        "blocked_acceptance_item_ids",
        "waived_acceptance_item_ids",
        "superseded_acceptance_item_ids",
        "reviewer_absorption",
        "flowguard_absorption",
        "residual_risk_disposition",
        "semantic_downgrade_disposition",
        "validation_evidence_ids",
        "waived_requirement_ids",
    ),
}


ALLOWED_BLOCKER_CLASSES_BY_FAMILY: dict[str, tuple[str, ...]] = {
    "task.high_standard_contract": (
        "mechanical_contract_missing_field",
        "invalid_blocker_shape",
        "local_artifact",
    ),
    "task.discovery": (
        "mechanical_contract_missing_field",
        "invalid_blocker_shape",
        "local_artifact",
    ),
    "task.skill_standard": (
        "mechanical_contract_missing_field",
        "invalid_blocker_shape",
        "local_artifact",
    ),
    "task.planning": (
        "mechanical_contract_missing_field",
        "invalid_blocker_shape",
        "route_decomposition",
        "local_artifact",
    ),
    "task.node_acceptance_plan": (
        "mechanical_contract_missing_field",
        "invalid_blocker_shape",
        "route_decomposition",
        "local_artifact",
    ),
    "task.node": (
        "mechanical_contract_missing_field",
        "invalid_blocker_shape",
        "evidence_gap",
        "missing_required_information",
        "flowguard_failure",
        "local_artifact",
    ),
    "review.parent_backward_replay": (
        "mechanical_contract_missing_field",
        "invalid_blocker_shape",
        "composition",
        "evidence_gap",
        "route_decomposition",
        "local_artifact",
    ),
    "flowguard_check.post_result": (
        "mechanical_contract_missing_field",
        "invalid_blocker_shape",
        "flowguard_failure",
        "missing_required_information",
    ),
    "review.any_current_subject": (
        "mechanical_contract_missing_field",
        "invalid_blocker_shape",
        "local_artifact",
        "evidence_gap",
        "missing_matching_flowguard_report",
        "route_decomposition",
        "flowguard_failure",
    ),
    "review.terminal_backward_replay": (
        "mechanical_contract_missing_field",
        "invalid_blocker_shape",
        "terminal_closure",
        "needs_user",
        "local_artifact",
    ),
    "pm_repair_decision.pm_repair_decision": (
        "mechanical_contract_missing_field",
        "invalid_blocker_shape",
    ),
    "pm_disposition.node_pm_disposition": (
        "mechanical_contract_missing_field",
        "invalid_blocker_shape",
        "evidence_gap",
        "system_validation_failure",
        "needs_user",
        "local_artifact",
    ),
    "pm_flowguard_acceptance.pm_flowguard_acceptance": (
        "mechanical_contract_missing_field",
        "invalid_blocker_shape",
        "flowguard_failure",
    ),
}


ALLOWED_VALUE_OPTIONS_BY_FAMILY: dict[str, dict[str, tuple[Any, ...]]] = {
    "task.high_standard_contract": {
        "requirements[].classification": HIGH_STANDARD_REQUIREMENT_CLASSIFICATION_OPTIONS,
        "acceptance_item_registry.items[].source_type": ACCEPTANCE_ITEM_SOURCE_TYPE_OPTIONS,
        "acceptance_item_registry.items[].quality_floor": ACCEPTANCE_ITEM_QUALITY_FLOOR_OPTIONS,
        "acceptance_item_registry.items[].status": ACCEPTANCE_ITEM_STATUS_OPTIONS,
    },
    "task.discovery": {
        "decision": COMMON_PASS_BLOCK_DECISION_OPTIONS,
    },
    "task.skill_standard": {
        "decision": COMMON_PASS_BLOCK_DECISION_OPTIONS,
        "obligations[].classification": SKILL_STANDARD_CLASSIFICATION_OPTIONS,
        "obligations[].role_use": RESPONSIBILITY_OPTIONS,
    },
    "task.planning": {
        "schema_version": ("flowpilot.route_plan.v1",),
        "decision": COMMON_PASS_BLOCK_DECISION_OPTIONS,
        "nodes[].node_kind": NODE_KIND_OPTIONS,
        "nodes[].responsibility": RESPONSIBILITY_OPTIONS,
    },
    "task.node_acceptance_plan": {
        "decision": ("pass", "block", "redesign_route"),
        "route_plan.schema_version when decision=redesign_route": ("flowpilot.route_plan.v1",),
        "route_plan.nodes[].node_kind when decision=redesign_route": NODE_KIND_OPTIONS,
        "route_plan.nodes[].responsibility when decision=redesign_route": RESPONSIBILITY_OPTIONS,
    },
    "task.node": {
        "decision": COMMON_PASS_BLOCK_DECISION_OPTIONS,
    },
    "review.parent_backward_replay": {
        "reviewed_by_role": REVIEWER_ROLE_OPTIONS,
        "passed": BOOLEAN_OPTIONS,
        "blockers[].blocker_class": ALLOWED_BLOCKER_CLASSES_BY_FAMILY["review.parent_backward_replay"],
        "contract_self_check.all_required_fields_present": (True,),
        "contract_self_check.exact_field_names_used": (True,),
        "contract_self_check.empty_required_arrays_explicit": (True,),
        "contract_self_check.runtime_mechanical_validation_passed": (True,),
    },
    "flowguard_check.post_result": {
        "reviewed_by_role": FLOWGUARD_REVIEWER_ROLE_OPTIONS,
        "passed": BOOLEAN_OPTIONS,
        "blockers[].blocker_class": ALLOWED_BLOCKER_CLASSES_BY_FAMILY["flowguard_check.post_result"],
        "contract_self_check.all_required_fields_present": (True,),
        "contract_self_check.exact_field_names_used": (True,),
        "contract_self_check.empty_required_arrays_explicit": (True,),
        "contract_self_check.runtime_mechanical_validation_passed": (True,),
    },
    "review.any_current_subject": {
        "reviewed_by_role": REVIEWER_ROLE_OPTIONS,
        "passed": BOOLEAN_OPTIONS,
        "blockers[].blocker_class": ALLOWED_BLOCKER_CLASSES_BY_FAMILY["review.any_current_subject"],
        "contract_self_check.all_required_fields_present": (True,),
        "contract_self_check.exact_field_names_used": (True,),
        "contract_self_check.empty_required_arrays_explicit": (True,),
        "contract_self_check.runtime_mechanical_validation_passed": (True,),
    },
    "review.terminal_backward_replay": {
        "reviewed_by_role": REVIEWER_ROLE_OPTIONS,
        "passed": BOOLEAN_OPTIONS,
        "blockers[].blocker_class": ALLOWED_BLOCKER_CLASSES_BY_FAMILY["review.terminal_backward_replay"],
        "route_segment_replay[].status": TERMINAL_REPLAY_STATUS_OPTIONS,
        "final_artifact_refs[].status": TERMINAL_REPLAY_STATUS_OPTIONS,
        "acceptance_item_closure[].status": TERMINAL_REPLAY_STATUS_OPTIONS,
        "final_blockers[].blocker_class": ALLOWED_BLOCKER_CLASSES_BY_FAMILY["review.terminal_backward_replay"],
        "contract_self_check.all_required_fields_present": (True,),
        "contract_self_check.exact_field_names_used": (True,),
        "contract_self_check.empty_required_arrays_explicit": (True,),
        "contract_self_check.runtime_mechanical_validation_passed": (True,),
    },
    "pm_repair_decision.pm_repair_decision": {
        "decision": PM_REPAIR_DECISION_OPTIONS,
        "next_action": PM_REPAIR_DECISION_OPTIONS,
        "route_plan.schema_version when decision=redesign_route": ("flowpilot.route_plan.v1",),
        "route_plan.nodes[].node_kind when decision=redesign_route": NODE_KIND_OPTIONS,
        "route_plan.nodes[].responsibility when decision=redesign_route": RESPONSIBILITY_OPTIONS,
        "supplemental_repair_contract.schema_version when terminal supplemental repair": (
            "flowpilot.terminal_supplemental_repair_contract.v1",
        ),
        "supplemental_repair_contract.repair_items[].gap_kind when terminal supplemental repair": (
            TERMINAL_SUPPLEMENTAL_REPAIR_GAP_KIND_OPTIONS
        ),
        "supplemental_repair_contract.repair_items[].hygiene_category when gap_kind=final_artifact_hygiene_gap": (
            FINAL_ARTIFACT_HYGIENE_CATEGORY_OPTIONS
        ),
        "supplemental_repair_contract.repair_items[].status when terminal supplemental repair": ("open",),
        "repair_parent_scope_contract.schema_version when decision=repair_parent_scope": (
            "flowpilot.parent_repair_scope_contract.v1",
        ),
    },
    "pm_disposition.node_pm_disposition": {
        "decision": PM_DISPOSITION_DECISION_OPTIONS,
        "acceptance_item_disposition[].disposition": ("accepted", "blocked", "waived", "superseded"),
    },
    "pm_flowguard_acceptance.pm_flowguard_acceptance": {
        "decision": PM_FLOWGUARD_ACCEPTANCE_DECISION_OPTIONS,
        "route_plan.schema_version when decision=redesign_route": ("flowpilot.route_plan.v1",),
        "route_plan.nodes[].node_kind when decision=redesign_route": NODE_KIND_OPTIONS,
        "route_plan.nodes[].responsibility when decision=redesign_route": RESPONSIBILITY_OPTIONS,
    },
}


PACKET_STAGE_EVIDENCE_MATRIX: tuple[dict[str, Any], ...] = tuple(
    {
        "family_id": family_id,
        "lifecycle_stage": {
            "task.high_standard_contract": "preplanning_contract_definition",
            "task.discovery": "preplanning_material_discovery",
            "task.skill_standard": "preplanning_skill_standard_contract",
            "task.planning": "route_planning",
            "task.node_acceptance_plan": "node_plan_definition",
            "task.node": "node_result_execution",
            "flowguard_check.post_result": "post_result_flowguard_check",
            "review.any_current_subject": "independent_current_subject_review",
            "review.parent_backward_replay": "parent_backward_review",
            "review.terminal_backward_replay": "terminal_final_backward_replay",
            "pm_repair_decision.pm_repair_decision": "pm_repair_decision",
            "pm_disposition.node_pm_disposition": "pm_node_result_disposition",
            "pm_flowguard_acceptance.pm_flowguard_acceptance": "pm_flowguard_absorption",
        }[family_id],
        "required_evidence_owner": {
            "task.high_standard_contract": "flowpilot_runtime_mechanical_contract",
            "task.discovery": "pm_material_discovery",
            "task.skill_standard": "pm_skill_selection",
            "task.planning": "pm_route_plan",
            "task.node_acceptance_plan": "pm_node_acceptance_plan",
            "task.node": "assigned_worker_current_result",
            "flowguard_check.post_result": "flowguard_operator_current_model",
            "review.any_current_subject": "reviewer_current_subject_review",
            "review.parent_backward_replay": "reviewer_parent_backward_review",
            "review.terminal_backward_replay": "reviewer_terminal_backward_replay",
            "pm_repair_decision.pm_repair_decision": "pm_current_blocker_disposition",
            "pm_disposition.node_pm_disposition": "pm_acceptance_item_disposition",
            "pm_flowguard_acceptance.pm_flowguard_acceptance": "pm_flowguard_absorption",
        }[family_id],
        "current_required_fields": CURRENT_REQUIRED_FIELDS_BY_FAMILY[family_id],
        "moved_fields": MOVED_FIELDS_BY_FAMILY.get(family_id, ()),
        "deleted_fields": DELETED_FIELDS_BY_FAMILY.get(family_id, ()),
        "allowed_value_options": ALLOWED_VALUE_OPTIONS_BY_FAMILY[family_id],
        "allowed_blocker_classes": ALLOWED_BLOCKER_CLASSES_BY_FAMILY[family_id],
        "blocker_next_actions": {
            blocker_class: BLOCKER_CLASS_TO_NEXT_ACTION[blocker_class]
            for blocker_class in ALLOWED_BLOCKER_CLASSES_BY_FAMILY[family_id]
        },
        "blocker_repair_packet_contracts": {
            blocker_class: BLOCKER_REPAIR_PACKET_CONTRACTS[blocker_class]
            for blocker_class in ALLOWED_BLOCKER_CLASSES_BY_FAMILY[family_id]
        },
        "repeat_repair_required_fields": REPAIR_LINEAGE_REQUIRED_FIELDS,
        "repair_node_required_context_fields": REPAIR_NODE_CONTEXT_REQUIRED_FIELDS,
        "parent_replacement_required_context_fields": PARENT_REPLACEMENT_CONTEXT_REQUIRED_FIELDS,
    }
    for family_id in PACKET_FAMILY_IDS
)


PACKET_STAGE_EVIDENCE_MATRIX_BY_FAMILY = {
    str(row["family_id"]): row for row in PACKET_STAGE_EVIDENCE_MATRIX
}


def stage_evidence_row_for_family(family_id: str) -> Mapping[str, Any]:
    row = PACKET_STAGE_EVIDENCE_MATRIX_BY_FAMILY.get(family_id)
    if row is None:
        raise KeyError(f"missing packet contract matrix row for family: {family_id}")
    return row


def current_required_fields_for_family(family_id: str) -> tuple[str, ...]:
    return tuple(stage_evidence_row_for_family(family_id)["current_required_fields"])


def moved_fields_for_family(family_id: str) -> tuple[str, ...]:
    return tuple(stage_evidence_row_for_family(family_id)["moved_fields"])


def deleted_fields_for_family(family_id: str) -> tuple[str, ...]:
    return tuple(stage_evidence_row_for_family(family_id)["deleted_fields"])


def allowed_value_options_for_family(family_id: str) -> Mapping[str, tuple[Any, ...]]:
    return stage_evidence_row_for_family(family_id)["allowed_value_options"]


def result_contract_profile(profile_id: str) -> Mapping[str, Any]:
    try:
        return RESULT_CONTRACT_PROFILES[profile_id]
    except KeyError as exc:
        raise KeyError(f"missing result contract profile: {profile_id}") from exc


def result_contract_profiles(profile_ids: tuple[str, ...] | list[str]) -> tuple[Mapping[str, Any], ...]:
    return tuple(result_contract_profile(str(profile_id)) for profile_id in profile_ids if str(profile_id))


def allowed_blocker_classes_for_family(family_id: str) -> tuple[str, ...]:
    return tuple(stage_evidence_row_for_family(family_id)["allowed_blocker_classes"])


def next_action_for_blocker_class(blocker_class: str) -> str:
    try:
        return BLOCKER_CLASS_TO_NEXT_ACTION[blocker_class]
    except KeyError as exc:
        raise KeyError(f"missing next action for blocker class: {blocker_class}") from exc


def blocker_repair_packet_contract(blocker_class: str) -> Mapping[str, Any]:
    try:
        return BLOCKER_REPAIR_PACKET_CONTRACTS[blocker_class]
    except KeyError as exc:
        raise KeyError(f"missing repair packet contract for blocker class: {blocker_class}") from exc


def blocker_repair_packet_contracts_for_family(family_id: str) -> Mapping[str, Mapping[str, Any]]:
    row = stage_evidence_row_for_family(family_id)
    return row["blocker_repair_packet_contracts"]


def repair_lineage_required_fields() -> tuple[str, ...]:
    return REPAIR_LINEAGE_REQUIRED_FIELDS


def repair_node_context_required_fields() -> tuple[str, ...]:
    return REPAIR_NODE_CONTEXT_REQUIRED_FIELDS


def parent_replacement_context_required_fields() -> tuple[str, ...]:
    return PARENT_REPLACEMENT_CONTEXT_REQUIRED_FIELDS


def _json_value(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def stage_evidence_row_json(family_id: str) -> dict[str, Any]:
    row = dict(stage_evidence_row_for_family(family_id))
    row["schema_version"] = STAGE_EVIDENCE_MATRIX_SCHEMA_VERSION
    return {key: _json_value(value) for key, value in row.items()}


ROLE_VISIBLE_STAGE_EVIDENCE_FIELDS: tuple[str, ...] = (
    "family_id",
    "lifecycle_stage",
    "required_evidence_owner",
    "current_required_fields",
    "allowed_value_options",
    "allowed_blocker_classes",
    "blocker_next_actions",
    "blocker_repair_packet_contracts",
    "repeat_repair_required_fields",
    "repair_node_required_context_fields",
    "parent_replacement_required_context_fields",
)


def role_visible_stage_evidence_row_json(family_id: str) -> dict[str, Any]:
    row = stage_evidence_row_json(family_id)
    return {
        key: _json_value(row[key])
        for key in ROLE_VISIBLE_STAGE_EVIDENCE_FIELDS
        if key in row
    } | {"schema_version": STAGE_EVIDENCE_MATRIX_SCHEMA_VERSION}
