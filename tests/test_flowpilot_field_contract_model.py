from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))

import flowpilot_field_contract_model as model  # noqa: E402
import run_flowpilot_field_contract_checks as runner  # noqa: E402


class FlowPilotFieldContractModelTests(unittest.TestCase):
    def test_current_field_contract_catalog_covers_startup_and_background_fields(self) -> None:
        fields = {entry["field"] for entry in model.CURRENT_FIELD_CONTRACTS}
        logical_fields = {entry["logical_field"] for entry in model.CURRENT_FIELD_CONTRACTS}
        statuses = {entry["status"] for entry in model.CURRENT_FIELD_CONTRACTS}
        layers = {entry["layer"] for entry in model.CURRENT_FIELD_CONTRACTS}

        self.assertIn("startup_answers.background_collaboration_authorized", fields)
        self.assertIn("startup_answers.provenance", fields)
        self.assertIn(
            "user_intake.metadata.controller_bootstrap_scope.background_collaboration_authorized",
            fields,
        )
        self.assertIn("user_intake.metadata.startup_runtime_release_required", fields)
        self.assertIn("user_intake.metadata.startup_runtime_release_status", fields)
        self.assertIn("startup_intake_record.startup_intake_authority_source", fields)
        self.assertIn(
            "startup_intake_record.router_must_not_use_chat_history_for_startup_intake",
            fields,
        )
        self.assertIn("user_request_ref.startup_intake_authority_source", fields)
        self.assertIn(
            "user_request_ref.router_must_not_use_chat_history_for_startup_intake",
            fields,
        )
        self.assertIn(
            "startup_mechanical_audit.mechanical_checks.startup_answers_use_current_fields_only",
            fields,
        )
        self.assertIn("run.run_id", fields)
        self.assertIn("run.run_root", fields)
        self.assertIn("route_frontier.active_node_id", fields)
        self.assertIn("route_frontier.route_version", fields)
        self.assertIn("current_packet.packet_id", fields)
        self.assertIn("packet_result.packet_id", fields)
        self.assertIn("packet_result.result_id", fields)
        self.assertIn("output_contract.missing_required_fields", fields)
        self.assertIn("preplanning.high_standard_contract.requirements[]", fields)
        self.assertIn("preplanning.high_standard_contract.requirements[].requirement_id", fields)
        self.assertIn("preplanning.high_standard_contract.requirements[].classification", fields)
        self.assertIn("preplanning.high_standard_contract.requirements[].summary", fields)
        self.assertIn("preplanning.high_standard_contract.requirements[].closure_blocking", fields)
        self.assertIn("preplanning.discovery.material_sources", fields)
        self.assertIn("preplanning.discovery.material_sufficiency", fields)
        self.assertIn("preplanning.discovery.local_skill_inventory", fields)
        self.assertIn("preplanning.discovery.candidate_only_skill_policy", fields)
        self.assertIn("preplanning.skill_standard.obligations[]", fields)
        self.assertIn("preplanning.skill_standard.obligations[].obligation_id", fields)
        self.assertIn("preplanning.skill_standard.obligations[].skill", fields)
        self.assertIn("preplanning.skill_standard.obligations[].classification", fields)
        self.assertIn("preplanning.skill_standard.obligations[].role_use", fields)
        self.assertIn("preplanning.skill_standard.obligations[].use_context", fields)
        self.assertIn("preplanning.skill_standard.obligations[].evidence_required", fields)
        self.assertIn("preplanning.skill_standard.obligations[].closure_blocking", fields)
        self.assertIn("control_blocker.target_role_repair_instruction", fields)
        self.assertIn("reviewer_quality_review.decision", fields)
        self.assertIn("flowguard_process_review.target_result_id", fields)
        self.assertIn("current_packet_id", logical_fields)
        self.assertIn("missing_fields", logical_fields)
        self.assertIn("repair_instruction", logical_fields)
        self.assertTrue({"top_level", "middle", "leaf"}.issubset(layers))
        self.assertIn("mechanical_runtime_owned", statuses)
        self.assertIn("pm_decision_owned", statuses)
        self.assertIn("reviewer_quality_owned", statuses)
        self.assertIn("flowguard_process_owned", statuses)
        self.assertIn("role_binding_ledger.role_slots[].agent_id", fields)
        self.assertIn("role_binding_ledger.role_binding_mode", fields)
        self.assertIn("role_binding_ledger.role_slots[].host_liveness_status", fields)
        self.assertIn("current_role_agent_binding.role_key", fields)
        self.assertIn("current_role_agent_binding.agent_id", fields)
        self.assertIn("current_role_agent_binding.host_liveness_status", fields)
        self.assertIn("current_role_agent_binding.liveness_decision", fields)
        self.assertNotIn(
            "startup_fact_report.external_fact_review.reviewer_checked_requirement_ids",
            fields,
        )
        self.assertNotIn(
            "startup_fact_report.external_fact_review.direct_evidence_paths_checked",
            fields,
        )
        self.assertNotIn("reviewer_live_review_source", fields)
        self.assertNotIn("reviewer_must_not_use_chat_history", fields)
        self.assertNotIn(
            "user_intake.metadata.pm_must_request_startup_reviewer_gate_before_opening_start_gate",
            fields,
        )
        self.assertNotIn("user_intake.metadata.startup_gate_status", fields)
        self.assertNotIn("preplanning.skill_standard.default_required_obligation", fields)
        self.assertNotIn("preplanning.skill_standard.selected_skills", fields)
        self.assertNotIn("preplanning.high_standard_contract.decision", fields)

    def test_field_status_catalog_marks_retired_and_forbidden_legacy(self) -> None:
        self.assertEqual(
            {
                "current",
                "mechanical_runtime_owned",
                "pm_decision_owned",
                "reviewer_quality_owned",
                "flowguard_process_owned",
                "retired",
                "forbidden_legacy",
            },
            set(model.FIELD_STATUSES),
        )
        self.assertTrue(all(entry["status"] == "retired" for entry in model.RETIRED_FIELD_CONTRACTS))
        self.assertTrue(
            all(entry["status"] == "forbidden_legacy" for entry in model.FORBIDDEN_LEGACY_FIELD_CONTRACTS)
        )
        forbidden = {entry["field"] for entry in model.FORBIDDEN_LEGACY_FIELD_CONTRACTS}
        self.assertIn("preplanning.skill_standard.default_required_obligation", forbidden)
        self.assertIn("preplanning.skill_standard.selected_skills", forbidden)
        self.assertIn("preplanning.high_standard_contract.decision", forbidden)

    def test_field_contract_model_blocks_old_field_translation_and_fixed_role_gates(self) -> None:
        hazards = runner._check_hazards()

        self.assertTrue(hazards["ok"], hazards)
        self.assertTrue(
            hazards["hazards"]["unsupported_field_translated_accepted"]["detected"],
            hazards,
        )
        self.assertTrue(
            hazards["hazards"]["fixed_role_count_gate_required_accepted"]["detected"],
            hazards,
        )

    def test_field_contract_runner_passes(self) -> None:
        result = runner.run_checks()

        self.assertTrue(result["ok"], result)
        self.assertFalse(result["missing_labels"], result)


if __name__ == "__main__":
    unittest.main()
