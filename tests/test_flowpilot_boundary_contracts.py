from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))
sys.path.insert(0, str(ROOT / "simulations"))

import controller_process_aside as aside  # noqa: E402
import flowpilot_material_artifact_map as material_map  # noqa: E402
import flowpilot_material_artifact_map_entries as material_map_entries  # noqa: E402
import flowpilot_router as router  # noqa: E402
import flowpilot_router_controller_scheduler_current_work as current_work  # noqa: E402
import flowpilot_router_controller_scheduler_current_work_pending as current_work_pending  # noqa: E402
import flowpilot_router_controller_scheduler_receipts_bootloader as receipt_bootloader  # noqa: E402
import flowpilot_router_controller_scheduler_receipts_effects as receipt_effects  # noqa: E402
import packet_runtime  # noqa: E402
from flowguard import review_code_boundary_conformance  # noqa: E402
from flowpilot_model_test_alignment_source_code_contracts import source_code_contracts  # noqa: E402
from flowpilot_model_test_alignment_source_contracts import (  # noqa: E402
    source_boundary_contracts,
    source_boundary_observations,
)


class FlowPilotBoundaryContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="flowpilot-boundary-contract-"))

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_controller_process_aside_is_metadata_only_and_validated(self) -> None:
        contract = aside.controller_process_aside_contract()

        self.assertEqual(contract["schema_version"], aside.CONTROLLER_PROCESS_ASIDE_CONTRACT_SCHEMA)
        self.assertEqual(contract["field_name"], "controller_aside")
        self.assertTrue(contract["optional"])
        self.assertEqual(contract["target"], "controller_only")
        authority = contract["authority_boundary"]
        self.assertTrue(authority["not_formal_evidence"])
        self.assertTrue(authority["not_decision_or_approval"])
        self.assertTrue(authority["does_not_satisfy_wait"])
        self.assertTrue(authority["does_not_authorize_progress"])
        self.assertTrue(authority["does_not_create_router_event"])
        self.assertFalse(authority["worker_to_worker_visible"])
        self.assertFalse(authority["router_semantic_inspection_allowed"])
        self.assertTrue(authority["router_may_preserve_shape_only"])

        built = aside.build_controller_aside(
            "  started\n\n waiting for Router  ",
            from_role="worker_a",
            source="role_output_runtime.progress_status",
        )
        self.assertIsNotNone(built)
        assert built is not None
        self.assertEqual(built["schema_version"], aside.CONTROLLER_PROCESS_ASIDE_SCHEMA)
        self.assertEqual(built["from_role"], "worker_a")
        self.assertEqual(built["to_role"], "controller")
        self.assertEqual(built["text"], "started\nwaiting for Router")
        self.assertTrue(built["not_formal_evidence"])
        self.assertTrue(built["does_not_satisfy_wait"])
        self.assertTrue(built["does_not_authorize_progress"])
        self.assertTrue(built["does_not_create_router_event"])
        self.assertFalse(built["router_semantic_inspection_allowed"])

        self.assertIsNone(aside.validate_controller_aside_text(None))
        self.assertIsNone(aside.validate_controller_aside_text("   \n\t"))
        with self.assertRaisesRegex(ValueError, "non-empty lines or fewer"):
            aside.validate_controller_aside_text("one\ntwo\nthree\nfour")
        with self.assertRaisesRegex(ValueError, "characters or fewer"):
            aside.validate_controller_aside_text("x" * (aside.CONTROLLER_PROCESS_ASIDE_MAX_LEN + 1))

    def test_material_artifact_map_is_index_only_and_preserves_sealed_body_boundary(self) -> None:
        project_root = self._tmp
        run_root = project_root / ".flowpilot" / "runs" / "run-boundary"
        packet_dir = run_root / "packets" / "material-scan-001"
        result_dir = run_root / "results" / "material-scan-001"
        material_dir = run_root / "material"
        packet_dir.mkdir(parents=True)
        result_dir.mkdir(parents=True)
        material_dir.mkdir(parents=True)

        packet_body = packet_dir / "packet_body.md"
        result_body = result_dir / "result_body.md"
        packet_runtime.write_text_atomic(packet_body, "SEALED_PACKET_BODY_TEXT")
        packet_runtime.write_text_atomic(result_body, "SEALED_RESULT_BODY_TEXT")
        packet_body_rel = packet_runtime.project_relative(project_root, packet_body)
        result_body_rel = packet_runtime.project_relative(project_root, result_body)

        packet_envelope = {
            "schema_version": "test.packet_envelope.v1",
            "packet_id": "material-scan-001",
            "from_role": "project_manager",
            "to_role": "worker_a",
            "body_path": packet_body_rel,
            "body_hash": packet_runtime.sha256_file(packet_body),
            "body_visibility": "sealed_target_role_only",
        }
        packet_envelope_path = packet_dir / "packet_envelope.json"
        packet_runtime.write_json_atomic(packet_envelope_path, packet_envelope)

        result_envelope = {
            "schema_version": "test.result_envelope.v1",
            "packet_id": "material-scan-001",
            "completed_by_role": "worker_a",
            "next_recipient": "project_manager",
            "result_body_path": result_body_rel,
            "result_body_hash": packet_runtime.sha256_file(result_body),
            "body_visibility": "sealed_pm_only",
            "contract_self_check": {"status": "pass"},
        }
        result_envelope_path = result_dir / "result_envelope.json"
        packet_runtime.write_json_atomic(result_envelope_path, result_envelope)

        material_index = {
            "schema_version": "test.material_index.v1",
            "batch_id": "batch-material",
            "written_by_role": "project_manager",
            "packets": [
                {
                    "packet_id": "material-scan-001",
                    "packet_envelope_path": packet_runtime.project_relative(project_root, packet_envelope_path),
                    "packet_body_path": packet_body_rel,
                    "packet_body_hash": packet_envelope["body_hash"],
                    "result_envelope_path": packet_runtime.project_relative(project_root, result_envelope_path),
                }
            ],
        }
        packet_runtime.write_json_atomic(material_dir / "material_scan_packets.json", material_index)

        doc = material_map.refresh_material_artifact_map(project_root, run_root, {"run_id": "run-boundary"})

        self.assertEqual(doc["schema_version"], material_map.MATERIAL_ARTIFACT_MAP_SCHEMA)
        self.assertEqual(doc["run_id"], "run-boundary")
        self.assertFalse(doc["controller_decision_authority"])
        self.assertFalse(doc["controller_may_read_sealed_bodies"])
        self.assertFalse(doc["sealed_packet_or_result_bodies_read"])
        self.assertTrue(doc["body_text_excluded"])
        self.assertGreaterEqual(doc["entry_count"], 3)
        self.assertNotIn("SEALED_PACKET_BODY_TEXT", json.dumps(doc, sort_keys=True))
        self.assertNotIn("SEALED_RESULT_BODY_TEXT", json.dumps(doc, sort_keys=True))

        entry_ids = material_map.review_source_entry_ids(doc, batch_kind="material_scan")
        self.assertIn("material_scan:packet_index", entry_ids)
        self.assertIn("material_scan:packet:material-scan-001", entry_ids)
        self.assertIn("material_scan:result:material-scan-001", entry_ids)
        review_paths = material_map.reviewable_source_paths(doc, entry_ids=entry_ids)
        self.assertIn(packet_runtime.project_relative(project_root, material_dir / "material_scan_packets.json"), review_paths)
        self.assertIn(packet_runtime.project_relative(project_root, packet_envelope_path), review_paths)
        self.assertIn(packet_runtime.project_relative(project_root, result_envelope_path), review_paths)

        result_entry = next(
            entry for entry in doc["entries"] if entry["entry_id"] == "material_scan:result:material-scan-001"
        )
        self.assertTrue(result_entry["sealed_body_boundary_preserved"])
        self.assertTrue(result_entry["requires_runtime_open"])
        self.assertTrue(result_entry["body_refs"])
        self.assertTrue(all(ref["ordinary_file_read_allowed"] is False for ref in result_entry["body_refs"]))
        self.assertEqual(result_entry["allowed_role_reads"], ["project_manager", "human_like_reviewer"])

        summary = material_map.material_artifact_map_summary(doc)
        self.assertEqual(summary["entry_count"], doc["entry_count"])
        self.assertTrue(summary["body_text_excluded"])
        self.assertFalse(summary["controller_decision_authority"])
        source_ref = material_map.material_artifact_map_source_ref(project_root, run_root)
        self.assertIsNotNone(source_ref)
        assert source_ref is not None
        self.assertEqual(source_ref["path"], packet_runtime.project_relative(project_root, material_map.material_artifact_map_path(run_root)))
        self.assertTrue(source_ref["hash"])
        self.assertEqual(material_map.read_material_artifact_map(run_root)["schema_version"], material_map.MATERIAL_ARTIFACT_MAP_SCHEMA)

    def test_material_artifact_map_entry_policy_preserves_reference_boundaries(self) -> None:
        project_root = self._tmp
        run_root = project_root / ".flowpilot" / "runs" / "run-entry-policy"
        material_dir = run_root / "material"
        material_dir.mkdir(parents=True)

        source_path = material_dir / "pm_material_scan_result_disposition.json"
        packet_runtime.write_json_atomic(source_path, {"decision": "absorbed"})
        sealed_ref = material_map_entries.sealed_body_ref(
            "sealed/body.md",
            "abc123",
            visibility="sealed_pm_only",
        )
        source_ref = material_map_entries.safe_source_ref(project_root, source_path)
        self.assertIsNotNone(source_ref)
        self.assertIsNotNone(sealed_ref)
        assert source_ref is not None
        assert sealed_ref is not None

        entry = material_map_entries.make_entry(
            entry_id="entry-policy:test",
            kind="policy_test",
            producer_role="project_manager",
            owner_role="human_like_reviewer",
            status="current",
            authority_level="navigation_only",
            safe_summary="safe metadata only",
            source_refs=[source_ref],
            body_refs=[sealed_ref],
        )

        self.assertFalse(entry["body_text_included"])
        self.assertTrue(entry["sealed_body_boundary_preserved"])
        self.assertTrue(entry["requires_runtime_open"])
        self.assertFalse(entry["body_refs"][0]["ordinary_file_read_allowed"])
        self.assertEqual(entry["source_paths"], [packet_runtime.project_relative(project_root, source_path)])
        self.assertNotIn("sealed body text", json.dumps(entry, sort_keys=True).lower())

        static_entries = material_map_entries.static_artifact_entries(project_root, run_root)
        by_id = {item["entry_id"]: item for item in static_entries}
        self.assertEqual(by_id["material:pm_result_disposition"]["status"], "current")
        self.assertEqual(material_map_entries.status_counts(static_entries)["current"], len(static_entries))

    def test_receipt_bootloader_policy_child_preserves_facade_boundary(self) -> None:
        router_stub = ModuleType("router_stub")
        router_stub.BOOT_ACTIONS = []
        router_stub._boot_action_meta = lambda action_type: receipt_effects._boot_action_meta(  # type: ignore[attr-defined]
            router_stub,
            action_type,
        )

        boot_meta = receipt_bootloader._boot_action_meta(router_stub, "load_router")
        facade_meta = receipt_effects._boot_action_meta(router_stub, "load_router")

        self.assertEqual(boot_meta, facade_meta)
        self.assertEqual(boot_meta["flag"], "router_loaded")
        self.assertIn(receipt_bootloader, receipt_effects._OWNER_CHILD_MODULES)
        self.assertTrue(
            receipt_bootloader._matching_bootstrap_pending_action(
                router_stub,
                {"pending_action": {"controller_action_id": "action-1"}},
                {"controller_action_id": "action-1", "action_type": "load_router"},
            )
        )
        self.assertTrue(
            receipt_effects._matching_bootstrap_pending_action(
                router_stub,
                {"pending_action": {"action_type": "load_router"}},
                {"controller_action_id": "action-2", "action_type": "load_router"},
            )
        )

        result = receipt_bootloader._apply_startup_bootloader_receipt_effects(
            router_stub,
            self._tmp,
            self._tmp / ".flowpilot" / "runs" / "run-receipt",
            {"run_id": "run-receipt", "flags": {}},
            {"action_type": "ordinary_controller_action"},
            {},
        )

        self.assertEqual(result["reason"], "not_bootloader_action")

    def test_current_work_pending_policy_child_preserves_facade_boundary(self) -> None:
        project_root = self._tmp
        run_root = project_root / ".flowpilot" / "runs" / "run-current-work-pending"
        runtime_root = run_root / "runtime"
        runtime_root.mkdir(parents=True)
        pending = {
            "controller_action_id": "action-1",
            "router_scheduler_row_id": "row-1",
            "action_type": "await_current_scope_reconciliation",
            "label": "Wait for local reconciliation",
        }
        packet_runtime.write_json_atomic(
            runtime_root / "router_scheduler_ledger.json",
            {
                "schema_version": "test.router_scheduler_ledger.v1",
                "rows": [
                    {
                        "row_id": "row-1",
                        "controller_action_id": "action-1",
                        "action_type": "await_current_scope_reconciliation",
                        "router_state": "reconciled",
                        "controller_status": "done",
                    }
                ],
            },
        )

        open_ledger = {
            "valid_json": True,
            "actions": [{"action_id": "action-1", "status": "pending"}],
            "passive_waits": [],
        }
        self.assertIn(current_work_pending, current_work._OWNER_CHILD_MODULES)
        self.assertTrue(
            current_work_pending._pending_action_has_controller_authority(router, pending, open_ledger)
        )
        self.assertEqual(
            current_work_pending._pending_action_has_controller_authority(router, pending, open_ledger),
            current_work._pending_action_has_controller_authority(router, pending, open_ledger),
        )

        child_row = current_work_pending._scheduler_row_for_pending_action(router, run_root, pending)
        facade_row = current_work._scheduler_row_for_pending_action(router, run_root, pending)
        self.assertEqual(child_row, facade_row)
        self.assertEqual(child_row["row_id"], "row-1")

        controller_ledger = {"valid_json": True, "actions": [], "passive_waits": []}
        child_resolution = current_work_pending._pending_action_durable_resolution(
            router,
            run_root,
            pending,
            controller_ledger=controller_ledger,
        )
        facade_resolution = current_work._pending_action_durable_resolution(
            router,
            run_root,
            pending,
            controller_ledger=controller_ledger,
        )
        self.assertEqual(child_resolution, facade_resolution)
        self.assertIsNotNone(child_resolution)
        assert child_resolution is not None
        self.assertEqual(child_resolution["source"], "router_scheduler_ledger")

        run_state = {"run_id": "run-current-work-pending", "pending_action": dict(pending), "history": []}
        cleared = current_work_pending._clear_pending_action_if_durable_wait_resolved(
            router,
            project_root,
            run_root,
            run_state,
            source="boundary_test",
        )
        self.assertTrue(cleared["changed"])
        self.assertIsNone(run_state["pending_action"])
        self.assertEqual(run_state["history"][-1]["label"], "router_cleared_pending_action_after_durable_wait_resolution")
        self.assertTrue(
            current_work_pending._pending_role_wait_should_use_batch_projection(
                router,
                {"action_type": "await_role_decision", "to_role": "worker_a"},
            )
        )
        self.assertEqual(
            current_work_pending._pending_role_wait_should_use_batch_projection(
                router,
                {"action_type": "await_role_decision", "to_role": "worker_a"},
            ),
            current_work._pending_role_wait_should_use_batch_projection(
                router,
                {"action_type": "await_role_decision", "to_role": "worker_a"},
            ),
        )

    def test_source_boundary_observations_match_declared_code_boundaries(self) -> None:
        report = review_code_boundary_conformance(
            source_boundary_contracts(),
            source_boundary_observations(),
            source_code_contracts(),
        )

        self.assertTrue(report.ok, report.format_text(max_findings=20))
        self.assertEqual(report.decision, "code_boundary_conformance_green")
        self.assertFalse(report.findings)


if __name__ == "__main__":
    unittest.main()
