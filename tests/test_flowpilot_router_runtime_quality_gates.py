from __future__ import annotations

import unittest

from tests.flowpilot_router_runtime_suite import load_named_runtime_tests


TEST_NAMES = (
    "test_next_effective_node_returns_parent_before_sibling_module_after_last_child",
    "test_route_check_results_require_router_delivered_check_cards",
    "test_route_draft_requires_product_behavior_model_report",
    "test_route_check_reports_require_hard_gate_verdict_fields",
    "test_process_route_repair_required_blocks_activation_and_reopens_pm_route_draft",
    "test_runtime_role_assistances_allow_requires_six_current_role_binding_records",
    "test_single_agent_answer_records_authorized_role_continuity_without_live_agents",
    "test_role_output_envelope_writes_body_and_keeps_controller_visible_payload_sealed",
    "test_role_output_envelope_hash_survives_same_path_envelope_rewrite",
    "test_user_intake_settlement_finalizer_waits_for_controller_mail_after_activation",
    "test_router_owned_check_proof_rejects_self_attested_and_stale_audit",
    "test_child_skill_gates_block_raw_inventory_and_controller_approval",
    "test_reviewer_and_flowguard_operator_gate_event_groups_have_non_pass_outcomes",
    "test_gate_outcome_block_specs_are_registered_and_reset_stale_passes",
    "test_child_skill_gate_manifest_block_records_repair_without_approval",
    "test_child_skill_gate_manifest_repair_pass_clears_active_gate_block",
    "test_node_completion_idempotency_is_scoped_to_active_node",
    "test_node_acceptance_plan_requires_pm_high_standard_recheck",
    "test_validate_artifact_reports_node_acceptance_missing_fields_together",
    "test_gate_decision_event_records_ledger_and_state",
    "test_gate_decision_same_identity_replay_is_already_recorded",
    "test_gate_decision_rejects_mechanical_contradictions",
    "test_validate_artifact_reports_gate_decision_issues_together",
    "test_evidence_quality_package_blocks_stale_and_missing_visual_evidence",
    "test_root_contract_freeze_requires_clean_self_interrogation_records",
    "test_manifest_references_existing_system_cards",
    "test_reviewer_block_events_are_registered_in_external_taxonomy",
    "test_model_miss_review_block_flags_stay_in_sync",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    return load_named_runtime_tests(loader, tests, pattern, TEST_NAMES)


if __name__ == "__main__":
    unittest.main()
