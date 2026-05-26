from __future__ import annotations

import unittest

from tests.flowpilot_router_runtime_suite import load_named_runtime_tests


TEST_NAMES = (
    "test_pm_material_understanding_accepts_file_backed_memo_payload",
    "test_material_acceptance_requires_reviewer_sufficiency_and_pm_absorb_card",
    "test_material_scan_results_event_requires_result_ledger_absorption",
    "test_material_scan_direct_relay_blocks_body_hash_mismatch",
    "test_material_scan_direct_relay_blocks_missing_output_contract",
    "test_research_required_blocks_product_architecture_until_absorbed",
    "test_product_architecture_and_root_contract_gate_route_skeleton",
    "test_legacy_product_officer_model_report_does_not_close_modelability_gate",
    "test_process_route_model_canonical_event_writes_compatibility_alias",
    "test_pm_repair_transaction_commits_material_reissue_generation",
    "test_pm_repair_decision_side_effect_exposes_flag_before_wait_events",
    "test_pm_material_repair_rejects_role_reissue_without_fresh_packet_producer",
    "test_material_scan_mechanical_agent_id_gap_reissues_to_worker",
    "test_material_scan_path_only_done_receipt_schedules_controller_relay_repair",
    "test_material_scan_relay_repair_receipt_folds_after_runtime_relay",
    "test_material_insufficient_event_records_insufficient_state",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    return load_named_runtime_tests(loader, tests, pattern, TEST_NAMES)


if __name__ == "__main__":
    unittest.main()
