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
        self.assertIn("route_node.supplemental_repair_contract_ids", fields)
        self.assertIn("route_node.supplemental_repair_item_ids", fields)
        self.assertIn("terminal_supplemental_repair.current_round", fields)
        self.assertIn("terminal_supplemental_repair.max_rounds", fields)
        self.assertIn("terminal_supplemental_repair.status", fields)
        self.assertIn("supplemental_repair_contracts[].repair_items[].owner_repair_node_id", fields)
        self.assertIn("output_contract.missing_required_fields", fields)
        self.assertIn("output_contract.forbidden_fields_seen", fields)
        self.assertIn("output_contract.contract_family_id", fields)
        self.assertIn("output_contract.mechanical_contract_failure", fields)
        self.assertIn("output_contract.minimal_valid_shape", fields)
        self.assertIn("current_handoff_contract.contract_family_id", fields)
        self.assertIn("current_handoff_contract.input_material_manifest.authorized_result_reads[]", fields)
        self.assertIn("current_handoff_contract.input_material_manifest.authorized_result_read_ids", fields)
        self.assertIn("current_handoff_contract.input_material_manifest.required_authorized_read_count", fields)
        self.assertIn("flowguard_reissue_packet.envelope.authorized_result_reads[]", fields)
        self.assertIn(
            "flowguard_reissue_packet.current_handoff_contract.input_material_manifest.required_authorized_reads_before_submit",
            fields,
        )
        self.assertIn(
            "current_handoff_contract.input_material_manifest.all_required_authorized_result_bodies_must_be_opened_before_submit",
            fields,
        )
        self.assertIn(
            "current_handoff_contract.input_material_manifest.packet_body_opened_by_assigned_role_via_open_packet",
            fields,
        )
        self.assertIn("pm_repair_packet.repair_evidence_obligations[]", fields)
        self.assertIn("pm_repair_packet.repair_evidence_obligations[].obligation_id", fields)
        self.assertIn("pm_repair_packet.repair_evidence_obligations[].source_blocker_id", fields)
        self.assertIn("pm_repair_packet.repair_evidence_obligations[].evidence_kind", fields)
        self.assertIn("pm_repair_result.repair_obligation_disposition[]", fields)
        self.assertIn("pm_repair_result.repair_obligation_disposition[].obligation_id", fields)
        self.assertIn("pm_repair_result.repair_obligation_disposition[].disposition", fields)
        self.assertIn("repair_packet.repair_obligation_context", fields)
        self.assertIn("flowguard.semantic_recheck.consumed_repair_obligation_ids", fields)
        self.assertIn("current_handoff_contract.required_report_contract.required_result_body_fields", fields)
        self.assertIn("current_handoff_contract.required_report_contract.forbidden_result_body_fields", fields)
        self.assertIn("current_handoff_contract.missing_information_response", fields)
        self.assertIn("current_handoff_contract.downstream_consumer.unlocks", fields)
        self.assertIn("current_handoff_contract.status_projection_requirements.repair_chain_visible_when_current", fields)
        self.assertIn("packet.repair_blocker_id", fields)
        self.assertIn("packet.envelope.repair_blocker_id", fields)
        self.assertIn("packet.active_blocker_id", fields)
        self.assertIn("current_handoff_contract.input_material_manifest.subject_id", fields)
        self.assertIn("current_handoff_contract.input_material_manifest.target_result_id", fields)
        self.assertIn("current_handoff_contract.input_material_manifest.route_node_id", fields)
        self.assertIn("current_handoff_contract.input_material_manifest.blocker_id", fields)
        self.assertIn("staged_effect.blocker_id", fields)
        self.assertIn("flowguard_evidence.generator_inputs.blocker_id", fields)
        self.assertIn("flowguard_evidence.subject_context.blocker_id", fields)
        self.assertIn("flowguard_result.blocker_id", fields)
        self.assertIn("flowguard_evidence_manifest.entries[].blocker_id", fields)
        self.assertIn("review_packet.repair_blocker_id", fields)
        self.assertIn("active_blocker.status", fields)
        self.assertIn("active_blocker.retired_by_blocker_id", fields)
        self.assertIn("preplanning.high_standard_contract.requirements[]", fields)
        self.assertIn("preplanning.high_standard_contract.requirements[].requirement_id", fields)
        self.assertIn("preplanning.high_standard_contract.requirements[].classification", fields)
        self.assertIn("preplanning.high_standard_contract.requirements[].summary", fields)
        self.assertIn("preplanning.high_standard_contract.requirements[].closure_rule", fields)
        self.assertIn("preplanning.high_standard_contract.acceptance_item_registry.items[]", fields)
        self.assertIn("preplanning.high_standard_contract.acceptance_item_registry.items[].acceptance_item_id", fields)
        self.assertIn("preplanning.high_standard_contract.acceptance_item_registry.items[].source_type", fields)
        self.assertIn("preplanning.high_standard_contract.acceptance_item_registry.items[].quality_floor", fields)
        self.assertIn("preplanning.high_standard_contract.acceptance_item_registry.items[].future_evidence_rule", fields)
        self.assertIn("preplanning.discovery.material_sources", fields)
        self.assertIn("preplanning.discovery.material_sufficiency", fields)
        self.assertIn("preplanning.discovery.candidate_skill_inventory", fields)
        self.assertIn("preplanning.skill_standard.obligations[]", fields)
        self.assertIn("preplanning.skill_standard.obligations[].obligation_id", fields)
        self.assertIn("preplanning.skill_standard.obligations[].skill", fields)
        self.assertIn("preplanning.skill_standard.obligations[].classification", fields)
        self.assertIn("preplanning.skill_standard.obligations[].role_use", fields)
        self.assertIn("preplanning.skill_standard.obligations[].use_context", fields)
        self.assertIn("preplanning.skill_standard.obligations[].evidence_rule", fields)
        self.assertIn("control_blocker.target_role_repair_instruction", fields)
        self.assertIn("reviewer_quality_review.decision", fields)
        self.assertIn("flowguard_process_review.target_result_id", fields)
        self.assertIn("packet_result.flowguard_check.modeled_boundary", fields)
        self.assertIn("packet_result.flowguard_check.blockers[]", fields)
        self.assertIn("packet_result.flowguard_check.contract_self_check", fields)
        self.assertIn("flowguard_evidence.json.model_test_alignment_report.decision", fields)
        self.assertIn("flowguard_work_order.decision", fields)
        self.assertIn("flowguard_evidence_manifest.entries[].flowguard_result_id", fields)
        self.assertIn("active_packets", fields)
        self.assertIn("accepted_result_packets", fields)
        self.assertIn("closure_accepted_packets", fields)
        self.assertIn("flowguard_evidence_file_hard_decision", logical_fields)
        self.assertIn("current_packet_id", logical_fields)
        self.assertIn("repair_blocker_id", logical_fields)
        self.assertIn("supplemental_repair_item_projection", logical_fields)
        self.assertIn("terminal_supplemental_repair_round", logical_fields)
        self.assertIn("handoff_blocker_id", logical_fields)
        self.assertIn("authorized_result_read_ids", logical_fields)
        self.assertIn("repair_evidence_obligations", logical_fields)
        self.assertIn("repair_obligation_disposition", logical_fields)
        self.assertIn("consumed_repair_obligation_ids", logical_fields)
        self.assertIn("staged_effect_blocker_id", logical_fields)
        self.assertIn("flowguard_result_blocker_id", logical_fields)
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
        self.assertNotIn("role_binding_ledger.role_slots[].liveness_status", fields)
        self.assertIn("current_role_agent_binding.role_key", fields)
        self.assertIn("current_role_agent_binding.agent_id", fields)
        self.assertIn("current_role_agent_binding.host_liveness_status", fields)
        self.assertIn("current_role_agent_binding.liveness_decision", fields)
        self.assertIn("current_handoff_contract.required_report_contract.required_child_fields", fields)
        self.assertIn("current_handoff_contract.required_report_contract.branch_valid_shapes", fields)
        self.assertIn("current_handoff_contract.required_report_contract.non_empty_array_fields", fields)
        self.assertIn("submission_checklist.required_result_body_fields", fields)
        self.assertIn("submission_checklist.required_child_fields", fields)
        self.assertIn("submission_checklist.branch_valid_shapes", fields)
        self.assertIn("submission_checklist.non_empty_array_fields", fields)
        self.assertIn(
            "submission_checklist.input_material_manifest.required_authorized_reads_before_submit",
            fields,
        )
        self.assertIn("output_contract.mechanical_contract_failure.failed_branch", fields)
        self.assertIn("output_contract.mechanical_contract_failure.failed_field_path", fields)
        self.assertIn("output_contract.branch_minimal_valid_shape", fields)
        self.assertIn("submission_checklist_required_child_fields", logical_fields)
        self.assertIn("submission_checklist_branch_valid_shapes", logical_fields)
        self.assertIn("submission_checklist_required_authorized_reads_before_submit", logical_fields)
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
        self.assertNotIn("preplanning.high_standard_contract.contract_rows", fields)
        self.assertNotIn("preplanning.high_standard_contract.requirements[].closure_blocking", fields)
        self.assertNotIn("preplanning.high_standard_contract.acceptance_item_registry.items[].final_replay_required", fields)
        self.assertNotIn("preplanning.discovery.local_skill_inventory", fields)
        self.assertNotIn("preplanning.discovery.candidate_only_skill_policy", fields)
        self.assertNotIn("preplanning.skill_standard.obligations[].evidence_required", fields)
        self.assertNotIn("preplanning.skill_standard.obligations[].closure_blocking", fields)
        self.assertNotIn("packet_result.flowguard_check.evidence_consistency.hard_evidence_decision", fields)
        self.assertNotIn("packet_result.review.independent_challenge", fields)

    def test_field_lifecycle_chain_models_repair_identity_end_to_end(self) -> None:
        chains = {entry["chain_id"]: entry for entry in model.FIELD_LIFECYCLE_CHAINS}

        chain = chains["repair_blocker_identity_recheck_chain"]
        self.assertEqual(chain["source"], "active_blocker.blocker_id")
        self.assertEqual(chain["mechanical_gate"], "_formal_repair_identity_blockers")
        self.assertEqual(chain["human_quality_gate"], "_record_review_from_packet_result")
        self.assertTrue(chain["no_prose_authority"])
        self.assertTrue(chain["no_reviewer_mechanical_field_check"])
        self.assertEqual(
            chain["field_sequence"],
            (
                "packet.repair_blocker_id",
                "packet.envelope.repair_blocker_id",
                "current_handoff_contract.input_material_manifest.blocker_id",
                "flowguard_evidence.generator_inputs.blocker_id",
                "flowguard_evidence.subject_context.blocker_id",
                "flowguard_result.blocker_id",
                "flowguard_evidence_manifest.entries[].blocker_id",
                "review_packet.repair_blocker_id",
            ),
        )

        sealed_body_chain = chains["sealed_body_authorized_material_lifecycle_chain"]
        self.assertEqual(sealed_body_chain["source"], "active_blocker.result_id")
        self.assertEqual(sealed_body_chain["mechanical_gate"], "_required_authorized_result_read_blockers")
        self.assertIn(
            "current_handoff_contract.input_material_manifest.authorized_result_read_ids",
            sealed_body_chain["field_sequence"],
        )
        self.assertIn(
            "runtime.open_authorized_input_materials_for_role",
            sealed_body_chain["field_sequence"],
        )
        reissue_material_chain = chains["flowguard_reissue_authorized_material_inheritance_chain"]
        self.assertEqual(
            reissue_material_chain["source"],
            "source_flowguard_packet.envelope.authorized_result_reads[]",
        )
        self.assertIn(
            "runtime._flowguard_reissue_inherited_authorized_result_reads",
            reissue_material_chain["field_sequence"],
        )
        self.assertIn(
            "flowguard_reissue_packet.current_handoff_contract.input_material_manifest.required_authorized_reads_before_submit",
            reissue_material_chain["field_sequence"],
        )
        self.assertIn(
            "runtime._required_authorized_result_read_blockers",
            reissue_material_chain["field_sequence"],
        )

        repair_obligation_chain = chains["pm_repair_evidence_obligation_lifecycle_chain"]
        self.assertEqual(repair_obligation_chain["source"], "active_blocker.missing_required_fields")
        self.assertEqual(repair_obligation_chain["mechanical_gate"], "_pm_repair_obligation_disposition_violation")
        self.assertEqual(repair_obligation_chain["human_quality_gate"], "_flowguard_semantic_recheck_contract_violation")
        self.assertIn("repair_packet.repair_obligation_context", repair_obligation_chain["field_sequence"])
        self.assertIn("flowguard.semantic_recheck.consumed_repair_obligation_ids", repair_obligation_chain["field_sequence"])

    def test_field_lifecycle_chains_separate_routing_and_closure_packet_projections(self) -> None:
        chains = {entry["chain_id"]: entry for entry in model.FIELD_LIFECYCLE_CHAINS}

        routing_chain = chains["derived_active_packet_projection_chain"]
        closure_chain = chains["derived_closure_accepted_packet_projection_chain"]

        self.assertIn("_current_packets_for_routing", routing_chain["field_sequence"])
        self.assertIn("render_compact_console.active_packets", routing_chain["field_sequence"])
        self.assertNotIn("attempt_final_closure.active_packets", routing_chain["field_sequence"])
        self.assertEqual(closure_chain["mechanical_gate"], "_accepted_packets_for_closure_evidence")
        self.assertIn("_accepted_result_packets_for_active_route", closure_chain["field_sequence"])
        self.assertIn("_accepted_packets_for_closure_evidence", closure_chain["field_sequence"])
        self.assertIn("accepted_packet_lease_health.accepted_result_packets", closure_chain["field_sequence"])
        self.assertIn("attempt_final_closure.accepted_packets", closure_chain["field_sequence"])

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
        self.assertIn("preplanning.high_standard_contract.contract_rows", forbidden)
        self.assertIn("pm_repair_decision.authority", forbidden)
        self.assertIn("pm_disposition.summary", forbidden)

    def test_packet_result_contract_catalog_covers_current_packet_families(self) -> None:
        self.assertIs(model.PACKET_RESULT_CONTRACTS, model.packet_result_contracts.PACKET_RESULT_CONTRACTS)
        contracts = {entry["family_id"]: entry for entry in model.PACKET_RESULT_CONTRACTS}

        self.assertEqual(model.REQUIRED_PACKET_RESULT_CONTRACT_COUNT, len(contracts))
        for family_id in (
            "task.high_standard_contract",
            "task.discovery",
            "task.skill_standard",
            "task.planning",
            "task.node_acceptance_plan",
            "task.node",
            "task.parent_backward_replay",
            "flowguard_check.post_result",
            "review.any_current_subject",
            "review.terminal_backward_replay",
            "pm_repair_decision.pm_repair_decision",
            "pm_flowguard_acceptance.pm_flowguard_acceptance",
            "pm_disposition.node_pm_disposition",
        ):
            self.assertIn(family_id, contracts)
        self.assertNotIn("flowguard_check.node_prework_flowguard", contracts)

        self.assertEqual(
            contracts["task.high_standard_contract"]["required_fields"],
            ("requirements", "acceptance_item_registry"),
        )
        self.assertIn("decision", contracts["task.high_standard_contract"]["forbidden_fields"])
        self.assertIn("contract_rows", contracts["task.high_standard_contract"]["forbidden_fields"])
        self.assertIn("obligations", contracts["task.skill_standard"]["required_fields"])
        self.assertIn("selected_skills", contracts["task.skill_standard"]["forbidden_fields"])
        self.assertEqual(contracts["task.node_acceptance_plan"]["required_fields"], ("decision",))
        node_branch_shapes = model.packet_result_contracts.branch_valid_shapes_for_family("task.node_acceptance_plan")
        self.assertIn("node_context_package", node_branch_shapes["decision=pass"])
        self.assertIn("route_plan", node_branch_shapes["decision=redesign_route"])
        self.assertIn("pm_visible_summary", contracts["flowguard_check.post_result"]["required_fields"])
        self.assertIn("modeled_boundary", contracts["flowguard_check.post_result"]["required_fields"])
        self.assertIn("contract_self_check", contracts["flowguard_check.post_result"]["required_fields"])
        self.assertIn("evidence_consistency", contracts["flowguard_check.post_result"]["forbidden_fields"])
        self.assertIn("authority", contracts["pm_repair_decision.pm_repair_decision"]["forbidden_fields"])
        self.assertIn(
            "route_plan.nodes[].title when decision=redesign_route",
            contracts["pm_repair_decision.pm_repair_decision"]["required_child_fields"],
        )
        branch_shapes = model.packet_result_contracts.branch_valid_shapes_for_family(
            "pm_repair_decision.pm_repair_decision"
        )
        self.assertIn("decision=redesign_route", branch_shapes)
        self.assertIn("route_plan", branch_shapes["decision=redesign_route"])
        self.assertIn("summary", contracts["pm_disposition.node_pm_disposition"]["forbidden_fields"])
        self.assertIn("flowguard_absorption", contracts["pm_flowguard_acceptance.pm_flowguard_acceptance"]["required_fields"])
        self.assertIn(
            "route_plan.nodes[].title when decision=redesign_route",
            contracts["pm_flowguard_acceptance.pm_flowguard_acceptance"]["required_child_fields"],
        )

    def test_field_lifecycle_chains_cover_flowguard_evidence_file_handoff(self) -> None:
        chains = {entry["chain_id"]: entry for entry in model.FIELD_LIFECYCLE_CHAINS}
        chain = chains["flowguard_current_evidence_file_to_reviewer_handoff_chain"]

        self.assertEqual(chain["mechanical_gate"], "_flowguard_current_report_violation")
        self.assertTrue(chain["no_prose_authority"])
        self.assertTrue(chain["no_reviewer_mechanical_field_check"])
        self.assertIn(
            "flowguard_evidence.json.model_test_alignment_report.decision",
            chain["field_sequence"],
        )
        self.assertIn("packet_result.flowguard_check.modeled_boundary", chain["field_sequence"])
        self.assertIn("packet_result.flowguard_check.blockers[]", chain["field_sequence"])
        self.assertIn("flowguard_evidence_manifest.entries[].flowguard_result_id", chain["field_sequence"])

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
        self.assertTrue(
            hazards["hazards"]["packet_result_contract_misaligned_accepted"]["detected"],
            hazards,
        )
        self.assertTrue(
            hazards["hazards"]["repair_identity_prose_only_accepted"]["detected"],
            hazards,
        )
        self.assertTrue(
            hazards["hazards"]["repair_identity_chain_misaligned_accepted"]["detected"],
            hazards,
        )
        self.assertTrue(
            hazards["hazards"]["repair_identity_reviewer_owned_accepted"]["detected"],
            hazards,
        )

    def test_field_contract_runner_passes(self) -> None:
        result = runner.run_checks()

        self.assertTrue(result["ok"], result)
        self.assertFalse(result["missing_labels"], result)
        self.assertTrue(result["source_alignment"]["ok"], result["source_alignment"])


if __name__ == "__main__":
    unittest.main()
