from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    old_module = sys.modules.get(name)
    sys.modules[name] = module
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
        if old_module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old_module
    return module


model = load_module(
    "flowpilot_cartesian_control_plane_exhaustion_model",
    ROOT / "simulations" / "flowpilot_cartesian_control_plane_exhaustion_model.py",
)
runner = load_module(
    "run_flowpilot_cartesian_control_plane_exhaustion_checks",
    ROOT / "simulations" / "run_flowpilot_cartesian_control_plane_exhaustion_checks.py",
)


class FlowPilotCartesianControlPlaneExhaustionTests(unittest.TestCase):
    def test_cartesian_runner_accepts_valid_and_rejects_hazards(self) -> None:
        report = runner.run_checks()

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["model_id"], model.MODEL_ID)
        self.assertGreater(report["matrix"]["full_product_count"], 70000)
        self.assertGreater(report["matrix"]["applicable_count"], 7000)
        self.assertGreater(report["matrix"]["skipped_count"], report["matrix"]["applicable_count"])
        self.assertEqual(report["hazards"]["missing_expected_failures"], {})
        self.assertIn(
            "cartesian_normal_repair_entered_glassbreak",
            report["hazards"]["hazards"]["normal_repair_enters_glassbreak"],
        )
        self.assertIn(
            "cartesian_unsupported_shape_translated_instead_of_rejected",
            report["hazards"]["hazards"]["unsupported_shape_translated"],
        )
        self.assertIn(
            "cartesian_no_delta_retry_missing_required_delta_feedback",
            report["hazards"]["hazards"]["no_delta_retry_without_feedback"],
        )

    def test_persisted_cartesian_result_matches_live_summary(self) -> None:
        persisted = json.loads(runner.RESULTS_PATH.read_text(encoding="utf-8"))
        live = runner.run_checks()

        self.assertTrue(persisted["ok"], persisted)
        self.assertEqual(persisted["ok"], live["ok"])
        self.assertEqual(persisted["model_id"], live["model_id"])
        for key in (
            "full_product_count",
            "applicable_count",
            "skipped_count",
            "boundary_count",
            "mutation_count",
            "context_count",
            "consumer_count",
            "coverage_shard_count",
            "missing_dimensions",
            "missing_oracle_or_feedback",
            "normal_context_glassbreak_cells",
            "threshold_cells_without_loop_key",
            "retry_cells_without_delta_feedback",
        ):
            with self.subTest(section="matrix", key=key):
                self.assertEqual(persisted["matrix"][key], live["matrix"][key])
        for key in (
            "contract_exhaustion_bridge_count",
            "historical_failure_bridge_count",
            "contract_bridge_missing_consumption",
            "historical_bridge_missing_consumption",
            "missing_mutation_families",
            "fallback_bridge_translations",
            "canonical_bridge_translation_count",
        ):
            with self.subTest(section="bridges", key=key):
                self.assertEqual(persisted["bridges"][key], live["bridges"][key])

    def test_every_declared_dimension_has_applicable_cells(self) -> None:
        report = runner.run_checks()

        self.assertEqual(report["matrix"]["missing_dimensions"], {
            "boundary_ids": [],
            "mutation_ids": [],
            "contexts": [],
            "consumers": [],
        })
        self.assertEqual(
            report["matrix"]["full_product_count"],
            len(model.BOUNDARIES) * len(model.MUTATIONS) * len(model.CONTEXTS) * len(model.CONSUMERS),
        )
        self.assertEqual(report["native_contract_exhaustion"]["missing_generated_combination_cases"], [])
        self.assertEqual(report["native_contract_exhaustion"]["missing_model_owned_shards"], [])
        self.assertEqual(report["native_contract_exhaustion"]["missing_coverage_receipts"], [])

    def test_skipped_cells_are_explicitly_accounted_for(self) -> None:
        skipped = list(model.SKIPPED_CARTESIAN_CELLS)

        self.assertEqual(
            len(model.REQUIRED_CARTESIAN_CELLS) + len(skipped),
            model.CARTESIAN_MATRIX["full_product_count"],
        )
        self.assertTrue(skipped)
        self.assertFalse([cell for cell in skipped if not cell.get("skip_reason")])
        self.assertLessEqual(
            {
                "boundary_does_not_own_mutation_group",
                "boundary_not_present_in_context",
                "consumer_not_allowed_for_boundary",
                "threshold_probe_only_accepts_repeated_blocker_mutations",
            },
            {cell["skip_reason"] for cell in skipped},
        )

    def test_high_risk_mutations_are_present(self) -> None:
        mutation_kinds = {cell["mutation_kind"] for cell in model.REQUIRED_CARTESIAN_CELLS}

        for mutation in (
            "missing_body",
            "missing_required_field",
            "wrong_type",
            "missing_path",
            "wrong_current_path",
            "target_not_found",
            "wrong_run_id",
            "current_pointer_zero_bytes",
            "index_pointer_zero_bytes",
            "current_pointer_ambiguous_recovery",
            "pointer_write_lock_active",
            "wrong_node_id",
            "missing_evidence_manifest",
            "missing_authorized_read",
            "missing_related_authorized_body",
            "packet_body_not_opened",
            "missing_repair_evidence_obligations",
            "missing_repair_obligation_disposition",
            "unknown_repair_obligation_id",
            "stale_repair_obligation_evidence_ref",
            "missing_repair_obligation_consumption",
            "reissue_loses_inherited_authorized_reads",
            "reissue_loses_required_read_manifest",
            "progress_only_evidence",
            "retry_without_delta",
            "same_blocker_repeat",
            "same_root_no_delta_retry",
            "missing_root_cause_loop_key",
            "unsupported_command",
            "legacy_alias",
            "fallback_prose",
            "wrapper_shape",
            "json_object_stringified_as_string",
            "body_source_conflict",
            "body_file_unreadable",
        ):
            with self.subTest(mutation=mutation):
                self.assertIn(mutation, mutation_kinds)

    def test_pointer_and_submit_body_entry_cells_have_current_runtime_oracles(self) -> None:
        pointer_cells = [
            cell
            for cell in model.REQUIRED_CARTESIAN_CELLS
            if cell["boundary_id"] == "current_run_pointer"
        ]
        body_entry_cells = [
            cell
            for cell in model.REQUIRED_CARTESIAN_CELLS
            if cell["boundary_id"] == "submit_result_body_entry"
        ]

        self.assertTrue(pointer_cells)
        self.assertTrue(body_entry_cells)
        pointer_mutations = {cell["mutation_kind"] for cell in pointer_cells}
        self.assertLessEqual(
            {
                "current_pointer_zero_bytes",
                "index_pointer_zero_bytes",
                "current_pointer_ambiguous_recovery",
                "pointer_write_lock_active",
            },
            pointer_mutations,
        )
        for cell in pointer_cells:
            if cell["mutation_kind"] in model.POINTER_RECOVERY_MUTATIONS:
                with self.subTest(cell_id=cell["cell_id"]):
                    self.assertEqual(cell["expected_reaction"], "recover_pointer")
                    self.assertIn("corrupt_pointer_backup_path", cell["required_feedback_fields"])
                    self.assertIn("current_run_evidence", cell["required_feedback_fields"])
            if cell["mutation_kind"] in model.POINTER_BLOCKER_MUTATIONS:
                with self.subTest(cell_id=cell["cell_id"]):
                    self.assertEqual(cell["expected_reaction"], "terminal_blocker")

        body_entry_mutations = {cell["mutation_kind"] for cell in body_entry_cells}
        self.assertLessEqual(
            {"json_object_stringified_as_string", "body_source_conflict", "body_file_unreadable"},
            body_entry_mutations,
        )

    def test_repair_obligation_boundary_enters_pm_and_flowguard_contexts(self) -> None:
        cells = [
            cell
            for cell in model.REQUIRED_CARTESIAN_CELLS
            if cell["boundary_id"] == "pm_repair_obligation"
        ]

        self.assertTrue(cells)
        contexts = {cell["context"] for cell in cells}
        consumers = {cell["consumer"] for cell in cells}
        mutation_kinds = {cell["mutation_kind"] for cell in cells}
        self.assertIn("pm_repair", contexts)
        self.assertIn("flowguard_reissue", contexts)
        self.assertIn("project_manager", consumers)
        self.assertIn("flowguard_operator", consumers)
        self.assertIn("missing_repair_obligation_disposition", mutation_kinds)
        self.assertIn("missing_repair_obligation_consumption", mutation_kinds)

    def test_reissue_packet_boundary_covers_inherited_material_loss(self) -> None:
        cells = [
            cell
            for cell in model.REQUIRED_CARTESIAN_CELLS
            if cell["boundary_id"] == "reissue_packet_contract"
        ]

        self.assertTrue(cells)
        mutation_kinds = {cell["mutation_kind"] for cell in cells}
        contexts = {cell["context"] for cell in cells}
        consumers = {cell["consumer"] for cell in cells}
        self.assertIn("flowguard_reissue", contexts)
        self.assertIn("flowguard_operator", consumers)
        self.assertIn("reissue_loses_inherited_authorized_reads", mutation_kinds)
        self.assertIn("reissue_loses_required_read_manifest", mutation_kinds)

    def test_normal_repair_cells_never_expect_glassbreak(self) -> None:
        bad = [
            cell["cell_id"]
            for cell in model.REQUIRED_CARTESIAN_CELLS
            if cell["normal_repair_context"] and cell["expected_reaction"] == "glassbreak_alarm"
        ]

        self.assertEqual(bad, [])

    def test_glassbreak_cells_are_threshold_only_and_name_loop_key(self) -> None:
        cells = [
            cell
            for cell in model.REQUIRED_CARTESIAN_CELLS
            if cell["expected_reaction"] == "glassbreak_alarm"
        ]

        self.assertTrue(cells)
        for cell in cells:
            with self.subTest(cell_id=cell["cell_id"]):
                self.assertEqual(cell["context"], "glassbreak_threshold_probe")
                self.assertEqual(cell["consumer"], "glassbreak_controller")
                self.assertIn(cell["mutation_kind"], model.GLASSBREAK_MUTATIONS)
                self.assertTrue(cell["repeated_blocker_key_required"])
                self.assertEqual(cell["same_blocker_attempt_count"], model.GLASSBREAK_THRESHOLD)

    def test_compatibility_and_fallback_surfaces_are_rejected(self) -> None:
        compatibility_cells = [
            cell
            for cell in model.REQUIRED_CARTESIAN_CELLS
            if cell["mutation_kind"] in model.COMPATIBILITY_MUTATIONS
        ]

        self.assertTrue(compatibility_cells)
        for cell in compatibility_cells:
            with self.subTest(cell_id=cell["cell_id"]):
                self.assertEqual(cell["expected_reaction"], "mechanical_reject")
                self.assertTrue(cell["unsupported_shape_rejected"])
                self.assertIn("minimum_valid_shape", cell["required_feedback_fields"])

    def test_retry_cells_require_delta_feedback_until_threshold_probe(self) -> None:
        retry_cells = [
            cell
            for cell in model.REQUIRED_CARTESIAN_CELLS
            if cell["requires_next_packet_delta"]
        ]

        self.assertTrue(retry_cells)
        for cell in retry_cells:
            with self.subTest(cell_id=cell["cell_id"]):
                self.assertNotEqual(cell["expected_reaction"], "glassbreak_alarm")
                self.assertIn("required_delta", cell["required_feedback_fields"])

    def test_testmesh_registers_every_generated_owner(self) -> None:
        report = runner.run_checks()
        required_owners = {
            cell["required_evidence_owner"]
            for cell in report["matrix"]["required_cells"]
        }

        self.assertTrue(report["test_mesh"]["ok"], report["test_mesh"])
        self.assertEqual(set(report["test_mesh"]["required_child_suite_owners"]), required_owners)
        self.assertLessEqual(required_owners, set(report["test_mesh"]["child_suites"]))
        self.assertIn(runner.NATIVE_CONTRACT_SHARD_SUITE_ID, report["test_mesh"]["child_suites"])
        self.assertEqual(report["test_mesh"]["unowned_coverage_shard_ids"], [])
        self.assertTrue(report["test_mesh"]["flowguard_test_mesh"]["ok"], report["test_mesh"])
        for owner in required_owners:
            suite = report["test_mesh"]["child_suites"][owner]
            with self.subTest(owner=owner):
                self.assertGreater(suite["owned_cell_count"], 0)
                self.assertTrue(suite["owned_coverage_shard_ids"])
                self.assertTrue(suite["evidence_current"])
                self.assertEqual(suite["result_status"], "passed")

    def test_native_flowguard_contract_exhaustion_receipt_is_current(self) -> None:
        report = runner.run_checks()
        native = report["native_contract_exhaustion"]

        self.assertTrue(native["ok"], native)
        self.assertEqual(
            native["combination_case_count"],
            report["matrix"]["full_product_count"],
        )
        self.assertEqual(
            native["required_model_obligation_count"],
            report["matrix"]["full_product_count"],
        )
        self.assertGreater(native["flowpilot_model_owned_shard_count"], 10)
        self.assertIn(model.FLOWGUARD_NATIVE_RECEIPT_ID, native["required_coverage_receipt_ids"])
        self.assertTrue(
            [
                receipt
                for receipt in native["coverage_receipts"]
                if receipt["receipt_id"] == model.FLOWGUARD_NATIVE_RECEIPT_ID
                and receipt["current"]
                and receipt["covered_case_count"] >= report["matrix"]["full_product_count"]
                and receipt["shard_count"] == native["coverage_shard_count"]
            ],
            native["coverage_receipts"],
        )

    def test_applicable_cells_carry_combination_shard_and_receipt_ids(self) -> None:
        for cell in model.REQUIRED_CARTESIAN_CELLS:
            with self.subTest(cell_id=cell["cell_id"]):
                self.assertTrue(str(cell["contract_combination_case_id"]).startswith(f"cartesian:{model.MODEL_ID}:"))
                self.assertTrue(str(cell["coverage_shard_id"]).startswith(f"flowpilot_shard:{model.MODEL_ID}:"))
                self.assertEqual(cell["coverage_receipt_id"], model.FLOWGUARD_NATIVE_RECEIPT_ID)
                self.assertEqual(
                    tuple(cell["contract_axis_case_ids"]),
                    (
                        f"boundary:{cell['boundary_id']}",
                        f"mutation:{cell['mutation_kind']}",
                        f"context:{cell['context']}",
                        f"consumer:{cell['consumer']}",
                    ),
                )

    def test_contract_and_historical_bridges_are_consumed(self) -> None:
        report = runner.run_checks()

        self.assertTrue(report["bridges"]["ok"], report["bridges"])
        self.assertEqual(
            report["bridges"]["contract_exhaustion_bridge_count"],
            len(model.contract_model.REQUIRED_CONTRACT_EXHAUSTION_CELLS),
        )
        self.assertGreaterEqual(report["bridges"]["historical_failure_bridge_count"], 20)
        self.assertEqual(report["bridges"]["contract_bridge_missing_consumption"], [])
        self.assertEqual(report["bridges"]["historical_bridge_missing_consumption"], [])
        self.assertEqual(report["bridges"]["missing_mutation_families"], [])
        self.assertEqual(report["bridges"]["fallback_bridge_translations"], [])
        self.assertGreater(report["bridges"]["canonical_bridge_translation_count"], 0)

    def test_bridge_rows_preserve_source_identity_or_explicit_canonicalization(self) -> None:
        for row in (*model.CONTRACT_EXHAUSTION_BRIDGE_CELLS, *model.HISTORICAL_FAILURE_BRIDGE_CELLS):
            with self.subTest(bridge_id=row["bridge_id"]):
                self.assertTrue(row["cartesian_mutation_known"])
                self.assertTrue(row.get("source_mutation_known", row["source_mutation_kind"] in model.MUTATION_BY_ID))
                if row["cartesian_mutation_kind"] == row["source_mutation_kind"]:
                    self.assertIn(row.get("bridge_translation_kind", "identity"), {"", "identity"})
                else:
                    self.assertEqual(row["bridge_translation_kind"], "canonical_current_control_plane")
                    self.assertIn(row["source_mutation_kind"], model.CONTRACT_EXHAUSTION_MUTATION_CANONICALIZATION)
                    self.assertEqual(
                        row["cartesian_mutation_kind"],
                        model.CONTRACT_EXHAUSTION_MUTATION_CANONICALIZATION[row["source_mutation_kind"]],
                    )
                    self.assertTrue(row["bridge_translation_reason"])

    def test_research_packet_recipient_role_alias_is_cartesian_bridge_case(self) -> None:
        bridge = {
            row["bridge_id"]: row
            for row in model.HISTORICAL_FAILURE_BRIDGE_CELLS
        }
        row = bridge["historical_failure.history.research_packet_recipient_role_alias.legacy_alias"]

        self.assertEqual(row["source_failure_id"], "history.research_packet_recipient_role_alias")
        self.assertEqual(row["source_mutation_kind"], "legacy_alias")
        self.assertEqual(row["cartesian_boundary_id"], "historical_failure_bridge")
        self.assertTrue(row["cartesian_mutation_known"])

    def test_unknown_bridge_mutation_fails_without_fallback_translation(self) -> None:
        bad_rows = (
            {
                "bridge_id": "known_bad.future_contract_mutation",
                "source_mutation_kind": "future_missing_packet_semantic_field",
                "cartesian_mutation_kind": "missing_required_field",
            },
        )

        self.assertEqual(
            runner._bridge_missing_mutation_families(bad_rows),
            ["future_missing_packet_semantic_field"],
        )
        self.assertEqual(
            runner._bridge_fallback_translations(bad_rows),
            ["known_bad.future_contract_mutation"],
        )

    def test_high_risk_cells_have_current_runtime_canaries(self) -> None:
        corpus_paths = [
            ROOT / "tests" / "test_flowpilot_core_runtime.py",
            ROOT / "tests" / "test_flowpilot_high_standard_control_flow.py",
            ROOT / "tests" / "router_runtime" / "startup_bootstrap.py",
            ROOT / "tests" / "test_flowpilot_control_plane_contracts.py",
            ROOT / "tests" / "router_runtime" / "route_mutation_parent_backward.py",
            ROOT / "tests" / "router_runtime" / "route_mutation_model_miss_triage.py",
            ROOT / "tests" / "router_runtime" / "resume.py",
            ROOT / "tests" / "router_runtime" / "packets.py",
            ROOT / "tests" / "router_runtime" / "quality_gates.py",
        ]
        corpus = "\n".join(path.read_text(encoding="utf-8") for path in corpus_paths)
        canaries = {
            "body_hash_mismatch": "test_startup_intake_rejects_body_hash_mismatch",
            "package_disposition_body_hash_conflict": "test_pm_package_disposition_identity_conflicts_on_body_hash",
            "missing_evidence_policy": "test_flowguard_packet_rejects_missing_evidence_output_policy",
            "fallback_rejected": "test_fallback_route_action_payload_is_rejected_without_translation",
            "legacy_alias_rejected": "test_unsupported_route_action_alias_is_rejected_without_translation",
            "break_glass_repeat_root": "test_break_glass_counts_same_flowguard_root_cause_across_surface_gates",
            "pm_repair_break_glass": "test_pm_repair_decision_break_glass_routes_control_plane_without_user_wait",
            "pm_flowguard_acceptance_break_glass": "test_pm_flowguard_acceptance_break_glass_routes_control_plane_without_review",
            "pm_model_miss_break_glass": "test_pm_model_miss_break_glass_routes_control_blocker_without_unlocking_repair",
            "pm_resume_break_glass": "test_pm_resume_break_glass_routes_control_blocker_without_resume_success",
            "stale_flowguard_evidence": "test_final_matrix_rejects_stale_flowguard_evidence_id",
            "wrong_stale_authority": "test_packet_open_rejects_wrong_stale_or_tampered_authority",
            "current_run_no_project_root_fallback": "test_current_run_resolver_accepts_new_schema_and_rejects_project_root_fallback",
        }

        for label, test_name in canaries.items():
            with self.subTest(label=label):
                self.assertIn(test_name, corpus)

    def test_every_consumer_gets_runtime_relevant_cells(self) -> None:
        by_consumer = Counter(cell["consumer"] for cell in model.REQUIRED_CARTESIAN_CELLS)

        for consumer in model.CONSUMERS:
            with self.subTest(consumer=consumer):
                self.assertGreater(by_consumer[consumer], 0)


if __name__ == "__main__":
    unittest.main()
