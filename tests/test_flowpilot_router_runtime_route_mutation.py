from __future__ import annotations

import unittest

from tests.flowpilot_router_runtime_suite import load_named_runtime_tests


TEST_NAMES = (
    "test_controller_route_memory_is_refreshed_and_required_for_pm_route_draft",
    "test_review_block_route_mutation_requires_closed_model_miss_triage",
    "test_stale_review_block_route_mutation_wait_is_recomputed_before_pm_triage",
    "test_route_root_node_entry_gap_requires_replanning_not_repair_node",
    "test_reviewed_route_activation_uses_pm_draft_without_dummy_fallback",
    "test_route_activation_rejects_active_node_missing_from_reviewed_route",
    "test_route_mutation_requires_topology_and_resets_route_hard_gates",
    "test_route_mutation_and_final_ledger_have_required_preconditions",
    "test_route_mutation_new_repair_transaction_is_not_swallowed_by_old_flag",
    "test_route_mutation_supersede_strategy_does_not_require_return_to_original",
    "test_route_mutation_sibling_branch_replacement_blocks_old_sibling_proof",
    "test_parent_backward_non_continue_decision_mutates_route_and_requires_rerun",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    return load_named_runtime_tests(loader, tests, pattern, TEST_NAMES)


if __name__ == "__main__":
    unittest.main()
