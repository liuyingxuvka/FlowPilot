from __future__ import annotations

import importlib
import hashlib
import json
import tempfile
import unittest
from pathlib import Path


acceptance_model = importlib.import_module("simulations.flowpilot_acceptance_testmesh_model")
acceptance_runner = importlib.import_module("simulations.run_flowpilot_acceptance_testmesh_checks")
evidence_compiler = importlib.import_module("scripts.compile_flowpilot_acceptance_testmesh_evidence")
evidence_truth = importlib.import_module("simulations.flowpilot_evidence_truth")
test_tier_runner = importlib.import_module("scripts.run_test_tier")


class FlowPilotAcceptanceTestMeshTests(unittest.TestCase):
    def write_tier_proof_root(self, root: Path, tier: str) -> None:
        root.mkdir(parents=True, exist_ok=True)
        source_digest = evidence_compiler.source_fingerprint()
        (root / f"{tier}_background_supervisor.meta.json").write_text(
            json.dumps(
                {
                    "status": "passed",
                    "exit_code": 0,
                    "timed_out": False,
                    "start_time": "2026-07-10T00:00:00+00:00",
                    "end_time": "2026-07-10T00:00:01+00:00",
                    "covered_source_fingerprint_start": source_digest,
                    "covered_source_fingerprint_end": source_digest,
                    "source_fingerprint_current": True,
                }
            ),
            encoding="utf-8",
        )
        (root / f"{tier}_background_supervisor.exit.txt").write_text("0\n", encoding="utf-8")
        child_names = {"child"}
        if tier == "all":
            child_names.update(
                name
                for config in acceptance_runner.BACKGROUND_CHILD_SUITES.values()
                for name in config["expected"]
            )
        for name in sorted(child_names):
            (root / f"{name}.meta.json").write_text(
                json.dumps(
                    {
                        "name": name,
                        "status": "passed",
                        "exit_code": 0,
                        "covered_source_fingerprint": source_digest,
                    }
                ),
                encoding="utf-8",
            )
            (root / f"{name}.exit.txt").write_text("0\n", encoding="utf-8")

    def current_routine_evidence(self, root: Path) -> dict[str, dict[str, object]]:
        root.mkdir(parents=True, exist_ok=True)
        declared = acceptance_model.build_testmesh_plan()
        router_ids = {
            "acceptance_router_quality_gate_children",
            "acceptance_router_packet_tier",
            "acceptance_router_route_tier",
            "acceptance_router_terminal_tier",
            "acceptance_router_release_tiers",
        }
        evidence: dict[str, dict[str, object]] = {}
        for suite in declared.child_suites:
            if suite.suite_id in router_ids:
                continue
            artifact = root / f"{suite.suite_id}.result.json"
            artifact.write_text(
                json.dumps({"suite_id": suite.suite_id, "status": "passed"}, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            fingerprint = hashlib.sha256(artifact.read_bytes()).hexdigest()
            covered_obligation_ids = evidence_truth.testmesh_receipt_obligation_ids(
                declared,
                suite,
            )
            proof = {
                "artifact_id": f"proof.{suite.suite_id}",
                "producer_route": "flowguard-test-mesh-test-fixture",
                "command": suite.command,
                "result_path": str(artifact),
                "result_status": "passed",
                "exit_code": 0,
                "artifact_fingerprints": {str(artifact): fingerprint},
                "covered_obligation_ids": list(covered_obligation_ids),
                "assertion_scope": "external_contract",
                "current": True,
                "route_evidence_current": True,
            }
            evidence[suite.suite_id] = {
                "result_status": "passed",
                "evidence_tier": "external_contract",
                "evidence_current": True,
                "test_count": 1,
                "selected_count": 1,
                "exit_code": 0,
                "result_path": str(artifact),
                "has_exit_artifact": True,
                "has_result_artifact": True,
                "proof_artifact": proof,
                **evidence_truth.testmesh_final_receipt_fields(
                    proof,
                    covered_obligation_ids=covered_obligation_ids,
                ),
            }
        return evidence

    def release_proof(self, root: Path) -> dict[str, object]:
        artifact = root / "release.result.json"
        artifact.write_text('{"status":"passed"}\n', encoding="utf-8")
        return {
            "artifact_id": "proof.acceptance_router_release_tiers",
            "producer_route": "flowguard-test-mesh-test-fixture",
            "command": "python scripts/run_test_tier.py --tier release --background",
            "result_path": str(artifact),
            "result_status": "passed",
            "exit_code": 0,
            "artifact_fingerprints": {str(artifact): hashlib.sha256(artifact.read_bytes()).hexdigest()},
            "covered_obligation_ids": list(acceptance_model.RELEASE_EVIDENCE_CELLS),
            "assertion_scope": "external_contract",
            "current": True,
            "route_evidence_current": True,
        }

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
                routine_evidence_overrides=self.current_routine_evidence(Path(tmp) / "routine"),
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
                routine_evidence_overrides=self.current_routine_evidence(Path(tmp) / "routine"),
                release_proof_artifact=self.release_proof(Path(tmp)),
                **self.passed_router_background_dirs(Path(tmp)),
            )

        self.assertTrue(result["ok"], result)
        self.assertTrue(result["release_gate"]["ok"])
        self.assertEqual(result["release_gate"]["deferred_suites"], [])

    def test_background_evidence_compiler_emits_current_fingerprinted_proofs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            all_root = root / "all"
            adversarial_root = root / "adversarial"
            release_root = root / "release"
            self.write_tier_proof_root(all_root, "all")
            self.write_tier_proof_root(adversarial_root, "formal-submit-adversarial")
            self.write_tier_proof_root(release_root, "release")

            manifest = evidence_compiler.compile_manifest(
                all_root=all_root,
                adversarial_root=adversarial_root,
                release_root=release_root,
            )
            strict_result = acceptance_runner.run_checks(
                release_evidence=True,
                release_background=True,
                routine_evidence_overrides=manifest["routine"],
                release_proof_artifact=manifest["release"]["proof_artifact"],
                release_test_count=manifest["release"]["test_count"],
                release_selected_count=manifest["release"]["selected_count"],
            )

        self.assertTrue(manifest["source_fingerprint"])
        self.assertEqual(
            manifest["schema_version"],
            evidence_compiler.MANIFEST_SCHEMA_VERSION,
        )
        self.assertEqual(
            set(manifest["routine"]),
            {
                suite.suite_id
                for suite in acceptance_model.build_testmesh_plan().child_suites
                if suite.suite_id != "acceptance_router_release_tiers"
            },
        )
        self.assertTrue(strict_result["ok"])
        self.assertTrue(strict_result["routine_router_gate"]["ok"])
        final_receipt_fields = {
            "run_id",
            "terminal_status",
            "result_fingerprint",
            "covered_obligation_ids",
            "artifact_version",
            "verifier_version",
        }
        for row in (*manifest["routine"].values(), manifest["release"]):
            self.assertTrue(final_receipt_fields.issubset(row), row)
            self.assertEqual(row["terminal_status"], "passed")
            self.assertTrue(row["result_fingerprint"])
            self.assertEqual(
                row["covered_obligation_ids"],
                row["proof_artifact"]["covered_obligation_ids"],
            )
            self.assertTrue(row["artifact_version"])
            self.assertIn("flowguard-testmesh/", row["verifier_version"])
        packet_proof = manifest["routine"]["acceptance_router_packet_tier"]
        self.assertEqual(
            packet_proof["test_count"],
            len(
                acceptance_runner.BACKGROUND_CHILD_SUITES[
                    "acceptance_router_packet_tier"
                ]["expected"]
            ),
        )
        self.assertTrue(
            manifest["routine"]["acceptance_contract_runtime_tests"]["proof_artifact"]["artifact_fingerprints"]
        )
        self.assertEqual(manifest["release"]["proof_artifact"]["result_status"], "passed")
        self.assertEqual(
            manifest["release"]["test_count"],
            manifest["release"]["proof_artifact"]["metadata"]["executed_child_command_count"],
        )
        self.assertEqual(
            manifest["release"]["selected_count"],
            manifest["release"]["proof_artifact"]["metadata"]["selected_child_command_count"],
        )
        self.assertEqual(
            manifest["release"]["proof_artifact"]["metadata"]["covered_tiers"],
            ["all", "formal-submit-adversarial", "release"],
        )
        self.assertNotIn(
            "final-confidence",
            manifest["release"]["proof_artifact"]["metadata"]["covered_tiers"],
        )

    def test_final_manifest_missing_receipt_fields_are_rejected_as_one_class(self) -> None:
        expected_codes = {
            "run_id": "final_receipt_run_id_missing",
            "terminal_status": "final_receipt_terminal_status_missing",
            "result_fingerprint": "final_receipt_result_fingerprint_missing",
            "covered_obligation_ids": "final_receipt_coverage_incomplete",
            "artifact_version": "final_receipt_artifact_version_missing",
            "verifier_version": "final_receipt_verifier_version_missing",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            all_root = root / "all"
            adversarial_root = root / "adversarial"
            release_root = root / "release"
            self.write_tier_proof_root(all_root, "all")
            self.write_tier_proof_root(adversarial_root, "formal-submit-adversarial")
            self.write_tier_proof_root(release_root, "release")
            manifest = evidence_compiler.compile_manifest(
                all_root=all_root,
                adversarial_root=adversarial_root,
                release_root=release_root,
            )

            for field_name, expected_code in expected_codes.items():
                with self.subTest(field_name=field_name):
                    routine = {
                        suite_id: dict(row)
                        for suite_id, row in manifest["routine"].items()
                    }
                    routine["acceptance_complete_workstream_profiles"].pop(field_name)
                    result = acceptance_runner.run_checks(
                        release_evidence=False,
                        routine_evidence_overrides=routine,
                    )
                    finding_codes = {
                        finding["code"] for finding in result["report"]["findings"]
                    }
                    self.assertFalse(result["ok"])
                    self.assertIn(expected_code, finding_codes)

    def test_background_evidence_compiler_does_not_persist_machine_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            all_root = root / "all"
            adversarial_root = root / "adversarial"
            release_root = root / "release"
            self.write_tier_proof_root(all_root, "all")
            self.write_tier_proof_root(adversarial_root, "formal-submit-adversarial")
            self.write_tier_proof_root(release_root, "release")

            manifest = evidence_compiler.compile_manifest(
                all_root=all_root.resolve(),
                adversarial_root=adversarial_root.resolve(),
                release_root=release_root.resolve(),
            )
            serialized = json.dumps(manifest, sort_keys=True)

        self.assertNotIn(str(root.resolve()), serialized)
        self.assertNotIn("\\\\Users\\\\", serialized)
        self.assertIn("<external>/all", serialized)
        self.assertIn("<external>/adversarial", serialized)
        self.assertIn("<external>/release", serialized)

    def test_direct_background_overrides_do_not_persist_machine_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = acceptance_runner.run_checks(
                release_evidence=False,
                **self.passed_router_background_dirs(root),
            )
            serialized = json.dumps(result, sort_keys=True)

        self.assertNotIn(str(root.resolve()), serialized)
        self.assertNotIn("\\\\Users\\\\", serialized)
        self.assertIn("<external>/quality", serialized)
        self.assertIn("<external>/packets", serialized)
        self.assertIn("<external>/route", serialized)
        self.assertIn("<external>/terminal", serialized)

    def test_background_evidence_compiler_rejects_source_changed_during_tier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            all_root = root / "all"
            adversarial_root = root / "adversarial"
            release_root = root / "release"
            self.write_tier_proof_root(all_root, "all")
            self.write_tier_proof_root(adversarial_root, "formal-submit-adversarial")
            self.write_tier_proof_root(release_root, "release")
            meta_path = all_root / "all_background_supervisor.meta.json"
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["covered_source_fingerprint_end"] = "changed-source"
            meta["source_fingerprint_current"] = False
            meta_path.write_text(json.dumps(meta), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "source fingerprint is missing or stale"):
                evidence_compiler.compile_manifest(
                    all_root=all_root,
                    adversarial_root=adversarial_root,
                    release_root=release_root,
                )

    def test_background_evidence_compiler_rejects_missing_router_child(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            all_root = root / "all"
            adversarial_root = root / "adversarial"
            release_root = root / "release"
            self.write_tier_proof_root(all_root, "all")
            self.write_tier_proof_root(adversarial_root, "formal-submit-adversarial")
            self.write_tier_proof_root(release_root, "release")
            (all_root / "router_packets_generic_ack_mail.meta.json").unlink()
            (all_root / "router_packets_generic_ack_mail.exit.txt").unlink()

            with self.assertRaisesRegex(
                ValueError,
                "acceptance_router_packet_tier is missing current all-tier child evidence",
            ):
                evidence_compiler.compile_manifest(
                    all_root=all_root,
                    adversarial_root=adversarial_root,
                    release_root=release_root,
                )

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
            "terminal_supplemental_fake_ai_current_checklist_recovery",
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

    def test_integration_cartesian_cells_are_required_and_owned(self) -> None:
        plan = acceptance_model.build_testmesh_plan()
        owners = acceptance_model.payload_cell_owners(plan)

        integration_cells = {
            "integration_cartesian_hard_underblock",
            "integration_cartesian_advisory_overblock",
            "integration_cartesian_worker_boundary",
            "integration_cartesian_runtime_no_hard_blocker",
            "integration_cartesian_model_miss",
        }
        self.assertTrue(integration_cells.issubset(set(acceptance_model.PAYLOAD_CELLS)))
        for cell_id in integration_cells:
            with self.subTest(cell_id=cell_id):
                self.assertEqual(set(owners[cell_id]), {"acceptance_integration_cartesian_coverage"})
        self.assertIn(
            "integration_cartesian_coverage",
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
            },
            set(tiers),
        )
        self.assertEqual(tiers["router-terminal"]["risk"], "terminal replay segment targets and final-review repair-return loop")
        self.assertNotIn("final-confidence", tiers)

    def test_router_packet_child_suite_matches_current_tier_exactly(self) -> None:
        expected = acceptance_runner.BACKGROUND_CHILD_SUITES[
            "acceptance_router_packet_tier"
        ]["expected"]
        actual = tuple(
            command.name
            for command in test_tier_runner.commands_for_tier("router-packets")
        )

        self.assertEqual(expected, actual)
        self.assertNotIn("router_packets_material", expected)

    def test_upstream_release_evidence_cells_are_release_owned(self) -> None:
        plan = acceptance_model.build_testmesh_plan()
        owners = acceptance_model.release_evidence_cell_owners(plan)

        expected_cells = {
            "all_tier_complete",
            "formal_submit_adversarial_tier_complete",
            "release_tier_complete",
        }
        self.assertEqual(expected_cells, set(acceptance_model.RELEASE_EVIDENCE_CELLS))
        for cell_id in expected_cells:
            with self.subTest(cell_id=cell_id):
                self.assertEqual(set(owners[cell_id]), {"acceptance_router_release_tiers"})
        self.assertNotIn("formal_exit_authority", {item.item_id for item in plan.partition_items})
        result = acceptance_runner.run_checks()
        self.assertEqual(expected_cells, set(result["release_evidence_cells"]))
        for cell_id in expected_cells:
            self.assertEqual(
                result["release_evidence_cell_owners"][cell_id],
                ["acceptance_router_release_tiers"],
            )


if __name__ == "__main__":
    unittest.main()
