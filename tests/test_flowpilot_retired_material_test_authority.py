from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RETIRED_AUTHORITY_TOKENS = (
    "tests.router_runtime.material_modeling",
    "pm_issues_material_and_capability_scan_packets",
    "router_direct_material_scan_dispatch_recheck_passed",
    "router_direct_material_scan_dispatch_recheck_blocked",
    "router_protocol_blocker_material_scan_dispatch_recheck",
    "worker_scan_packet_bodies_delivered_after_dispatch",
    "worker_scan_results_returned",
    "pm_records_material_scan_result_disposition",
    "reviewer_reports_material_sufficient",
    "reviewer_reports_material_insufficient",
    "pm_accepts_reviewed_material",
    "pm_requests_research_after_material_insufficient",
    "pm_writes_material_understanding",
    "relay_material_scan_packets",
    "relay_material_scan_results_to_pm",
    "relay_material_scan_results_to_reviewer",
)

CURRENT_AUTHORITY_SOURCES = (
    "scripts/test_tier/router_terminal_commands.py",
    "simulations/flowpilot_structure_maintenance_testmesh_catalog.py",
    "simulations/flowpilot_structure_maintenance_model.py",
    "simulations/flowpilot_router_facade_split_model.py",
    "simulations/flowpilot_known_friction_regression_matrix.py",
    "simulations/flowpilot_model_test_alignment_family_plans.py",
    "tests/router_runtime/common.py",
    "tests/router_runtime/packets.py",
    "tests/router_runtime/control_blockers.py",
    "tests/router_runtime/packet_result_family.py",
    "tests/router_runtime/resume.py",
    "tests/router_runtime/startup_bootstrap.py",
    "tests/router_runtime/startup_daemon.py",
    "tests/test_flowpilot_role_output_bridge_events.py",
    "tests/test_flowpilot_role_output_reconciliation.py",
    "tests/test_flowpilot_e2e_synthetic_chaos_replay.py",
    "tests/test_flowpilot_real_router_dry_run_rehearsal.py",
    "tests/test_flowpilot_synthetic_agent_trace_replay.py",
)


class RetiredMaterialTestAuthorityTests(unittest.TestCase):
    def test_deleted_material_modeling_modules_cannot_be_test_authority(self) -> None:
        self.assertFalse((ROOT / "tests/router_runtime/material_modeling.py").exists())
        self.assertFalse(
            (ROOT / "tests/test_flowpilot_router_runtime_material_modeling.py").exists()
        )

    def test_current_tier_testmesh_and_runtime_sources_have_no_retired_positive_tokens(self) -> None:
        violations: list[str] = []
        for relative in CURRENT_AUTHORITY_SOURCES:
            source = (ROOT / relative).read_text(encoding="utf-8")
            for token in RETIRED_AUTHORITY_TOKENS:
                if token in source:
                    violations.append(f"{relative}: {token}")
        self.assertEqual(violations, [])

    def test_retired_material_test_names_are_not_current_method_definitions(self) -> None:
        retired_names = (
            "test_pm_material_understanding_accepts_file_backed_memo_payload",
            "test_material_acceptance_requires_reviewer_sufficiency_and_pm_absorb_card",
            "test_material_scan_results_event_requires_result_ledger_absorption",
            "test_pm_repair_transaction_commits_material_reissue_generation",
            "test_pm_repair_decision_side_effect_exposes_flag_before_wait_events",
            "test_pm_material_repair_rejects_role_reissue_without_fresh_packet_producer",
            "test_e2e_no_producer_pm_repair_then_packet_reissue_exposes_producer_evidence",
            "test_real_router_repair_rehearsal_rejects_no_producer_then_accepts_packet_reissue",
        )
        definitions = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "tests").rglob("*.py")
        )
        for name in retired_names:
            with self.subTest(name=name):
                self.assertNotIn(f"def {name}(", definitions)


if __name__ == "__main__":
    unittest.main()
