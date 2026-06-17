from __future__ import annotations

import importlib
import json
import tempfile
import unittest
from pathlib import Path


acceptance_model = importlib.import_module("simulations.flowpilot_acceptance_testmesh_model")
acceptance_runner = importlib.import_module("simulations.run_flowpilot_acceptance_testmesh_checks")


class FlowPilotAcceptanceTestMeshTests(unittest.TestCase):
    def write_background_artifacts(
        self,
        root: Path,
        suite_id: str,
        *,
        failing_children: set[str] | None = None,
        running_children: set[str] | None = None,
        missing_children: set[str] | None = None,
    ) -> None:
        failing_children = failing_children or set()
        running_children = running_children or set()
        missing_children = missing_children or set()
        root.mkdir(parents=True, exist_ok=True)
        for old_artifact in root.glob("*"):
            if old_artifact.is_file():
                old_artifact.unlink()
        for name in acceptance_runner.BACKGROUND_CHILD_SUITES[suite_id]["expected"]:
            if name in missing_children:
                continue
            (root / f"{name}.combined.txt").write_text(f"{name} output\n", encoding="utf-8")
            (root / f"{name}.meta.json").write_text(
                json.dumps({"status": "running" if name in running_children else "finished", "duration_seconds": 1.0}),
                encoding="utf-8",
            )
            if name not in running_children:
                (root / f"{name}.exit.txt").write_text("1\n" if name in failing_children else "0\n", encoding="utf-8")

    def passed_router_background_dirs(self, root: Path) -> dict[str, Path]:
        dirs = {
            "router_quality_background_dir": root / "quality",
            "router_packets_background_dir": root / "packets",
            "router_route_background_dir": root / "route",
            "router_terminal_background_dir": root / "terminal",
        }
        suite_by_arg = {
            "router_quality_background_dir": "acceptance_router_quality_gate_children",
            "router_packets_background_dir": "acceptance_router_packet_tier",
            "router_route_background_dir": "acceptance_router_route_tier",
            "router_terminal_background_dir": "acceptance_router_terminal_tier",
        }
        for arg_name, suite_id in suite_by_arg.items():
            self.write_background_artifacts(dirs[arg_name], suite_id)
        return dirs

    def test_acceptance_testmesh_routine_gate_passes_without_hiding_release_gap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = acceptance_runner.run_checks(
                release_evidence=False,
                **self.passed_router_background_dirs(Path(tmp)),
            )

        self.assertTrue(result["ok"], result)
        self.assertTrue(result["test_mesh"]["routine_gate"]["ok"])
        self.assertTrue(result["routine_router_gate"]["ok"])
        self.assertFalse(result["release_gate"]["ok"])
        self.assertEqual(result["missing_payload_cells"], [])
        self.assertEqual(result["release_gate"]["deferred_suites"][0]["suite_id"], "acceptance_router_release_tiers")
        self.assertEqual(result["release_gate"]["deferred_suites"][0]["status"], "not_run")

    def test_acceptance_testmesh_release_evidence_can_close_release_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = acceptance_runner.run_checks(
                release_evidence=True,
                **self.passed_router_background_dirs(Path(tmp)),
            )

        self.assertTrue(result["ok"], result)
        self.assertTrue(result["release_gate"]["ok"])
        self.assertEqual(result["release_gate"]["deferred_suites"], [])

    def test_missing_router_background_artifacts_block_broad_routine_gate(self) -> None:
        result = acceptance_runner.run_checks(release_evidence=False)

        self.assertFalse(result["ok"])
        self.assertFalse(result["routine_router_gate"]["ok"])
        self.assertEqual(
            {
                "acceptance_router_quality_gate_children",
                "acceptance_router_packet_tier",
                "acceptance_router_route_tier",
                "acceptance_router_terminal_tier",
            },
            {item["suite_id"] for item in result["routine_router_gate"]["nonpassing_suites"]},
        )
        for item in result["routine_router_gate"]["nonpassing_suites"]:
            self.assertIn("not_current", item["nonpass_reasons"])

    def test_required_payload_cells_are_owned_by_current_child_suites(self) -> None:
        plan = acceptance_model.build_testmesh_plan()
        owners = acceptance_model.payload_cell_owners(plan)

        self.assertEqual(set(acceptance_model.PAYLOAD_CELLS), set(owners))
        for cell_id in acceptance_model.PAYLOAD_CELLS:
            with self.subTest(cell_id=cell_id):
                self.assertTrue(owners[cell_id], cell_id)

    def test_final_review_reject_repair_loop_is_a_required_payload_cell(self) -> None:
        plan = acceptance_model.build_testmesh_plan()
        owners = acceptance_model.payload_cell_owners(plan)

        self.assertIn("terminal_replay_reject_repair_rerun_closure", acceptance_model.PAYLOAD_CELLS)
        self.assertEqual(
            set(owners["terminal_replay_reject_repair_rerun_closure"]),
            {"acceptance_fake_ai_payload_chaos", "acceptance_terminal_replay_payloads"},
        )
        self.assertIn(
            "final_review_repair_return",
            {item.item_id for item in plan.partition_items},
        )

    def test_terminal_supplemental_repair_cells_are_required_and_owned(self) -> None:
        plan = acceptance_model.build_testmesh_plan()
        owners = acceptance_model.payload_cell_owners(plan)

        expected_cells = {
            "terminal_supplemental_contract_missing",
            "terminal_supplemental_contract_corrected_recovery",
            "terminal_supplemental_fake_ai_current_body_recovery",
            "terminal_supplemental_final_ledger_projection",
            "terminal_supplemental_round_cap_exhaustion",
            "terminal_hygiene_review_required",
            "terminal_hygiene_required_gap_blocks",
            "terminal_hygiene_supplemental_contract",
            "terminal_hygiene_final_ledger_projection",
        }
        self.assertTrue(expected_cells.issubset(set(acceptance_model.PAYLOAD_CELLS)))
        for cell_id in expected_cells:
            with self.subTest(cell_id=cell_id):
                self.assertIn("acceptance_terminal_supplemental_repair", set(owners[cell_id]))
        self.assertIn(
            "terminal_supplemental_repair_tail",
            {item.item_id for item in plan.partition_items},
        )

    def test_ai_contract_projection_cells_are_required_and_owned(self) -> None:
        plan = acceptance_model.build_testmesh_plan()
        owners = acceptance_model.payload_cell_owners(plan)

        projection_cells = {
            "ai_contract_semantic_recheck_profile_projection",
            "ai_contract_semantic_recheck_allowed_options_projection",
            "ai_contract_all_result_allowed_options_projection",
            "ai_contract_profile_required_fields_and_types_projection",
        }
        fake_ai_cells = {
            "ai_contract_semantic_recheck_forbidden_alias_feedback",
            "ai_contract_semantic_recheck_wrong_value_corrected_retry",
            "ai_contract_all_result_allowed_options_wrong_value",
            "ai_contract_profile_forbidden_alias_feedback",
        }
        self.assertTrue((projection_cells | fake_ai_cells).issubset(set(acceptance_model.PAYLOAD_CELLS)))
        for cell_id in projection_cells:
            with self.subTest(cell_id=cell_id):
                self.assertIn("acceptance_contract_runtime_tests", set(owners[cell_id]))
        for cell_id in fake_ai_cells:
            with self.subTest(cell_id=cell_id):
                self.assertIn("acceptance_fake_ai_payload_chaos", set(owners[cell_id]))
        self.assertIn(
            "ai_contract_projection_and_retry",
            {item.item_id for item in plan.partition_items},
        )

    def test_release_child_progress_only_or_not_run_is_not_a_pass(self) -> None:
        routine = acceptance_runner.run_checks(release_evidence=False)
        release_rows = [
            row
            for row in routine["test_mesh"]["rows"]
            if row["id"] == "acceptance_router_release_tiers"
        ]

        self.assertEqual(len(release_rows), 1)
        self.assertEqual(release_rows[0]["status"], "not_run")
        self.assertIn("not_run", release_rows[0]["nonpass_reasons"])
        self.assertFalse(routine["release_gate"]["ok"])

    def test_release_child_progress_timeout_or_stale_pass_is_not_release_evidence(self) -> None:
        cases = (
            {
                "name": "progress_only",
                "kwargs": {
                    "release_evidence": True,
                    "release_result_status": "progress_only",
                    "release_progress_only": True,
                    "release_background": True,
                    "release_has_exit_artifact": False,
                    "release_has_result_artifact": False,
                },
                "expected": {"progress_only", "missing_exit_artifact", "missing_result_artifact"},
            },
            {
                "name": "timeout",
                "kwargs": {
                    "release_evidence": False,
                    "release_result_status": "timeout",
                    "release_timeout_seconds": 30.0,
                    "release_background": True,
                },
                "expected": {"timeout", "not_current"},
            },
            {
                "name": "stale_pass",
                "kwargs": {
                    "release_evidence": True,
                    "release_result_status": "passed",
                    "release_evidence_current": False,
                    "release_stale_reasons": ("source_changed_after_result",),
                },
                "expected": {"not_current", "stale:source_changed_after_result"},
            },
        )

        for case in cases:
            with self.subTest(case=case["name"]):
                with tempfile.TemporaryDirectory() as tmp:
                    result = acceptance_runner.run_checks(
                        **case["kwargs"],
                        **self.passed_router_background_dirs(Path(tmp)),
                    )
                row = [
                    item
                    for item in result["test_mesh"]["rows"]
                    if item["id"] == "acceptance_router_release_tiers"
                ][0]

                self.assertFalse(result["release_gate"]["ok"])
                self.assertTrue(case["expected"].issubset(set(row["nonpass_reasons"])))

    def test_background_router_packet_failure_blocks_routine_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dirs = self.passed_router_background_dirs(Path(tmp))
            self.write_background_artifacts(
                dirs["router_packets_background_dir"],
                "acceptance_router_packet_tier",
                failing_children={"router_packet_runtime"},
            )
            result = acceptance_runner.run_checks(release_evidence=False, **dirs)

        self.assertFalse(result["ok"])
        self.assertFalse(result["routine_router_gate"]["ok"])
        packet = [
            item
            for item in result["routine_router_gate"]["nonpassing_suites"]
            if item["suite_id"] == "acceptance_router_packet_tier"
        ][0]
        self.assertIn("failed", packet["nonpass_reasons"])
        details = [
            item
            for item in result["router_tier_background_details"]
            if item["suite_id"] == "acceptance_router_packet_tier"
        ][0]
        self.assertEqual(details["failed_children"], ["router_packet_runtime"])

    def test_background_progress_without_exit_blocks_routine_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dirs = self.passed_router_background_dirs(Path(tmp))
            self.write_background_artifacts(
                dirs["router_quality_background_dir"],
                "acceptance_router_quality_gate_children",
                running_children={"router_quality_gates_route_draft_product_model"},
            )
            result = acceptance_runner.run_checks(release_evidence=False, **dirs)

        self.assertFalse(result["ok"])
        quality = [
            item
            for item in result["routine_router_gate"]["nonpassing_suites"]
            if item["suite_id"] == "acceptance_router_quality_gate_children"
        ][0]
        self.assertIn("progress_only", quality["nonpass_reasons"])
        self.assertIn("missing_exit_artifact", quality["nonpass_reasons"])

    def test_acceptance_testmesh_exposes_required_router_tier_mapping(self) -> None:
        result = acceptance_runner.run_checks()
        tiers = {item["tier"]: item for item in result["router_tier_mappings"]}

        self.assertEqual(
            {
                "router-quality-gates",
                "router-packets",
                "router-route",
                "router-terminal",
                "integration",
                "release",
                "final-confidence",
            },
            set(tiers),
        )
        self.assertEqual(tiers["router-terminal"]["risk"], "terminal replay segment targets and final-review repair-return loop")
        self.assertTrue(tiers["final-confidence"]["deferred_in_routine"])
        self.assertIn("terminal-return authority", tiers["final-confidence"]["risk"])

    def test_formal_exit_terminal_return_cells_are_release_owned(self) -> None:
        plan = acceptance_model.build_testmesh_plan()
        owners = acceptance_model.formal_exit_release_cell_owners(plan)

        expected_cells = {
            "formal_exit_terminal_return_missing",
            "formal_exit_startup_intake_blocks",
        }
        self.assertEqual(expected_cells, set(acceptance_model.FORMAL_EXIT_RELEASE_CELLS))
        for cell_id in expected_cells:
            with self.subTest(cell_id=cell_id):
                self.assertEqual(set(owners[cell_id]), {"acceptance_router_release_tiers"})
        self.assertIn(
            "formal_exit_authority",
            {item.item_id for item in plan.partition_items},
        )
        result = acceptance_runner.run_checks()
        self.assertEqual(expected_cells, set(result["formal_exit_release_cells"]))
        for cell_id in expected_cells:
            self.assertEqual(
                result["formal_exit_release_cell_owners"][cell_id],
                ["acceptance_router_release_tiers"],
            )


if __name__ == "__main__":
    unittest.main()
