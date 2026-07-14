from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS_ROOT = ROOT / "skills" / "flowpilot" / "assets"
sys.path.insert(0, str(ASSETS_ROOT))
sys.path.insert(0, str(ROOT / "simulations"))

import flowpilot_material_artifact_map as material_map  # noqa: E402
import flowpilot_material_artifact_map_entries as material_entries  # noqa: E402
import flowpilot_material_artifact_map_ordinary as material_ordinary  # noqa: E402
import flowpilot_material_artifact_map_packets as material_packets  # noqa: E402
import flowpilot_router as router  # noqa: E402
import flowpilot_router_work_packets_pm_role_writes_decisions_formal_gate as formal_gate  # noqa: E402
import packet_runtime  # noqa: E402
import run_flowpilot_material_artifact_map_checks as material_map_checks  # noqa: E402


class FlowPilotMaterialAccessMeshTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="flowpilot-material-access-mesh-"))

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_model_alignment_evidence_paths_are_repository_relative(self) -> None:
        report = material_map_checks._implementation_alignment()

        self.assertTrue(report["ok"], report)
        self.assertTrue(report["paths"])
        self.assertTrue(all(not Path(path).is_absolute() for path in report["paths"]))

    def _formal_package_inputs(self, run_root: Path) -> tuple[Path, list[dict[str, str]]]:
        packet_dir = run_root / "packets" / "packet-001"
        result_dir = run_root / "results" / "packet-001"
        packet_dir.mkdir(parents=True, exist_ok=True)
        result_dir.mkdir(parents=True, exist_ok=True)
        packet_body = packet_dir / "packet_body.md"
        result_body = result_dir / "result_body.md"
        packet_runtime.write_text_atomic(packet_body, "SEALED PACKET")
        packet_runtime.write_text_atomic(result_body, "SEALED RESULT")
        packet_envelope = packet_dir / "packet_envelope.json"
        result_envelope = result_dir / "result_envelope.json"
        contract_id = "flowpilot.output_contract.worker_current_node_result.v1"
        packet_runtime.write_json_atomic(
            packet_envelope,
            {
                "schema_version": packet_runtime.PACKET_ENVELOPE_SCHEMA,
                "packet_id": "packet-001",
                "packet_type": "current_node",
                "from_role": "project_manager",
                "to_role": "worker",
                "body_path": packet_runtime.project_relative(self._tmp, packet_body),
                "body_hash": packet_runtime.sha256_file(packet_body),
                "output_contract_id": contract_id,
            },
        )
        packet_runtime.write_json_atomic(
            result_envelope,
            {
                "schema_version": packet_runtime.RESULT_ENVELOPE_SCHEMA,
                "packet_id": "packet-001",
                "source_packet_envelope_path": packet_runtime.project_relative(self._tmp, packet_envelope),
                "source_output_contract_id": contract_id,
                "result_body_path": packet_runtime.project_relative(self._tmp, result_body),
                "result_body_hash": packet_runtime.sha256_file(result_body),
                "contract_self_check": {
                    "required": True,
                    "completed": True,
                    "passed": True,
                    "decision": "pass",
                    "source_output_contract_id": contract_id,
                    "declared_source_output_contract_id": contract_id,
                    "source_output_contract_id_matches": True,
                },
            },
        )
        return (
            run_root / "research" / "pm_research_result_disposition.json",
            [
                {
                    "packet_id": "packet-001",
                    "packet_envelope_path": packet_runtime.project_relative(self._tmp, packet_envelope),
                    "result_envelope_path": packet_runtime.project_relative(self._tmp, result_envelope),
                }
            ],
        )

    def _write_formal_package(self, run_root: Path) -> dict[str, object]:
        output_path, records = self._formal_package_inputs(run_root)
        formal_gate._write_pm_formal_gate_package(
            router,
            self._tmp,
            output_path,
            run_state={"run_id": run_root.name, "run_root": packet_runtime.project_relative(self._tmp, run_root)},
            batch={"batch_id": "research-batch-001"},
            records=records,
            batch_kind="research",
            package_label="research",
            gate_kind="evidence_quality",
            decision="absorbed",
            payload={"decision_reason": "current direct evidence is ready for review"},
        )
        return packet_runtime.read_json(output_path.with_name("pm_research_formal_gate_package.json"))

    def test_missing_map_stays_absent_through_refresh_and_formal_package(self) -> None:
        run_root = self._tmp / ".flowpilot" / "runs" / "run-map-absent"
        run_root.mkdir(parents=True)
        map_path = material_map.material_artifact_map_path(run_root)

        self.assertEqual(material_map.refresh_material_artifact_map(self._tmp, run_root), {})
        self.assertFalse(map_path.exists())
        status = material_map.material_artifact_map_navigation_status(
            self._tmp, run_root
        )
        self.assertFalse(status["present"])
        self.assertFalse(status["navigation_usable"])
        self.assertIsNone(status["source_ref"])
        self.assertFalse(status["acceptance_evidence"])

        package = self._write_formal_package(run_root)

        self.assertFalse(map_path.exists())
        self.assertIsNone(package["material_artifact_map_path"])
        self.assertFalse(package["material_artifact_map_navigation_usable"])
        self.assertFalse(package["content_boundary"]["includes_material_artifact_map_refs"])
        self.assertTrue(package["content_boundary"]["includes_result_envelope_paths_and_hashes"])
        self.assertTrue(package["result_envelopes"][0]["result_envelope_hash"])

    def test_existing_map_is_refreshed_and_formal_package_links_navigation(self) -> None:
        run_root = self._tmp / ".flowpilot" / "runs" / "run-map-present"
        research_dir = run_root / "research"
        research_dir.mkdir(parents=True)
        packet_runtime.write_json_atomic(
            research_dir / "research_package.json",
            {"schema_version": "flowpilot.research_package.v1", "decision_question": "what evidence is needed?"},
        )
        material_map.refresh_material_artifact_map(
            self._tmp,
            run_root,
            {"run_id": run_root.name},
            create_if_missing=True,
        )
        packet_runtime.write_json_atomic(
            research_dir / "worker_research_report.json",
            {"schema_version": "flowpilot.research_worker_report.v1", "status": "current"},
        )

        package = self._write_formal_package(run_root)
        refreshed = material_map.read_material_artifact_map(run_root)
        status = material_map.material_artifact_map_navigation_status(
            self._tmp, run_root, refreshed
        )

        self.assertIn("research:worker_report", {entry["entry_id"] for entry in refreshed["entries"]})
        self.assertTrue(status["present"])
        self.assertTrue(status["navigation_usable"])
        self.assertIsNotNone(status["source_ref"])
        self.assertFalse(status["acceptance_evidence"])
        self.assertTrue(package["material_artifact_map_navigation_usable"])
        self.assertEqual(
            package["material_artifact_map_path"],
            packet_runtime.project_relative(self._tmp, material_map.material_artifact_map_path(run_root)),
        )
        self.assertTrue(package["content_boundary"]["includes_material_artifact_map_refs"])
        self.assertFalse(package["material_artifact_map_acceptance_evidence"])

    def test_existing_noncurrent_map_is_checked_but_not_linked(self) -> None:
        for source_status, count_key in (("blocked", "blocked_count"), ("stale", "stale_count"), ("unresolved", "unresolved_count")):
            with self.subTest(source_status=source_status):
                run_root = self._tmp / ".flowpilot" / "runs" / f"run-map-{source_status}"
                research_dir = run_root / "research"
                research_dir.mkdir(parents=True)
                packet_runtime.write_json_atomic(
                    research_dir / "research_package.json",
                    {"schema_version": "flowpilot.research_package.v1", "status": source_status},
                )
                doc = material_map.refresh_material_artifact_map(
                    self._tmp,
                    run_root,
                    {"run_id": run_root.name},
                    create_if_missing=True,
                )
                status = material_map.material_artifact_map_navigation_status(self._tmp, run_root, doc)

                self.assertTrue(status["present"])
                self.assertEqual(status[count_key], 1)
                self.assertFalse(status["navigation_usable"])
                self.assertIsNone(status["source_ref"])
                self.assertIn(f"{count_key}_nonzero", status["issues"])

                package = self._write_formal_package(run_root)
                self.assertIsNone(package["material_artifact_map_path"])
                self.assertFalse(package["material_artifact_map_navigation_usable"])
                self.assertTrue(material_map.material_artifact_map_path(run_root).exists())

    def test_retired_material_scan_family_and_events_are_not_current_map_authority(self) -> None:
        map_source = (ASSETS_ROOT / "flowpilot_material_artifact_map.py").read_text(encoding="utf-8")
        disposition_source = (
            ASSETS_ROOT / "flowpilot_router_work_packets_pm_role_writes_decisions_package_disposition.py"
        ).read_text(encoding="utf-8")
        memory_source = (ASSETS_ROOT / "flowpilot_router_route_frontier_context_memory.py").read_text(encoding="utf-8")

        self.assertNotIn("material_scan:packet_index", map_source)
        self.assertNotIn("batch_kind == 'material_scan'", disposition_source)
        self.assertNotIn("pm_records_material_scan_result_disposition", disposition_source)
        self.assertNotIn("reviewer_reports_material_sufficient", memory_source)
        self.assertNotIn("reviewer_reports_material_insufficient", memory_source)

    def test_ordinary_project_material_is_public_but_sealed_bodies_stay_runtime_authorized(self) -> None:
        project_root = self._tmp
        run_root = project_root / ".flowpilot" / "runs" / "run-material-mesh"
        research_dir = run_root / "research"
        packet_dir = run_root / "packets" / "packet-001"
        result_dir = run_root / "results" / "packet-001"
        chapter_dir = run_root / "chapters"
        for path in (research_dir, packet_dir, result_dir, chapter_dir):
            path.mkdir(parents=True, exist_ok=True)

        public_paths = [
            chapter_dir / "chapter_001.md",
            run_root / "route_plan.json",
            run_root / "evidence" / "flowguard_report.json",
        ]
        for path in public_paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            packet_runtime.write_text_atomic(path, f"PUBLIC MATERIAL {path.name}")

        sealed_packet_body = packet_dir / "packet_body.md"
        sealed_result_body = result_dir / "result_body.md"
        packet_runtime.write_text_atomic(sealed_packet_body, "SEALED PACKET TEXT")
        packet_runtime.write_text_atomic(sealed_result_body, "SEALED RESULT TEXT")
        packet_body_rel = packet_runtime.project_relative(project_root, sealed_packet_body)
        result_body_rel = packet_runtime.project_relative(project_root, sealed_result_body)

        packet_envelope_path = packet_dir / "packet_envelope.json"
        packet_runtime.write_json_atomic(
            packet_envelope_path,
            {
                "packet_id": "packet-001",
                "from_role": "project_manager",
                "to_role": "worker",
                "body_path": packet_body_rel,
                "body_hash": packet_runtime.sha256_file(sealed_packet_body),
                "body_visibility": "sealed_target_role_only",
            },
        )
        result_envelope_path = result_dir / "result_envelope.json"
        packet_runtime.write_json_atomic(
            result_envelope_path,
            {
                "packet_id": "packet-001",
                "completed_by_role": "worker",
                "next_recipient": "project_manager",
                "result_body_path": result_body_rel,
                "result_body_hash": packet_runtime.sha256_file(sealed_result_body),
                "body_visibility": "sealed_pm_only",
            },
        )
        packet_runtime.write_json_atomic(
            research_dir / "research_packet.json",
            {
                "batch_id": "batch-001",
                "packets": [
                    {
                        "packet_id": "packet-001",
                        "packet_envelope_path": packet_runtime.project_relative(project_root, packet_envelope_path),
                        "packet_body_path": packet_body_rel,
                        "packet_body_hash": packet_runtime.sha256_file(sealed_packet_body),
                        "result_envelope_path": packet_runtime.project_relative(project_root, result_envelope_path),
                    }
                ],
            },
        )

        public_source_paths = {
            packet_runtime.project_relative(project_root, path)
            for path in public_paths
        }
        direct_entries: list[dict[str, object]] = []
        material_packets.add_packet_index_entries(
            project_root,
            direct_entries,
            index_path=research_dir / "research_packet.json",
            batch_kind="research",
        )
        material_ordinary.add_ordinary_work_artifact_entries(
            project_root,
            run_root,
            direct_entries,
            material_artifact_map_filename=material_map.MATERIAL_ARTIFACT_MAP_FILENAME,
        )
        direct_rendered = json.dumps(direct_entries, sort_keys=True)
        self.assertIn("research:packet:packet-001", {entry["entry_id"] for entry in direct_entries})
        self.assertNotIn("SEALED PACKET TEXT", direct_rendered)
        self.assertNotIn("SEALED RESULT TEXT", direct_rendered)
        self.assertTrue(
            public_source_paths.issubset(
                {
                    source_path
                    for entry in direct_entries
                    if entry["kind"] == "ordinary_work_artifact"
                    for source_path in entry["source_paths"]
                }
            )
        )

        doc = material_map.refresh_material_artifact_map(
            project_root,
            run_root,
            {"run_id": "run-material-mesh"},
            create_if_missing=True,
        )
        rendered = json.dumps(doc, sort_keys=True)

        self.assertTrue(doc["ordinary_material_policy"]["ordinary_non_sealed_project_run_files_readable"])
        self.assertFalse(doc["ordinary_material_policy"]["map_is_allowlist"])
        self.assertFalse(doc["controller_may_read_sealed_bodies"])
        self.assertNotIn("SEALED PACKET TEXT", rendered)
        self.assertNotIn("SEALED RESULT TEXT", rendered)

        indexed_public_paths = {
            source_path
            for entry in doc["entries"]
            if entry["kind"] == "ordinary_work_artifact"
            for source_path in entry["source_paths"]
        }
        self.assertTrue(public_source_paths.issubset(indexed_public_paths))

        for entry in doc["entries"]:
            if entry["kind"] == "ordinary_work_artifact":
                self.assertFalse(entry["requires_runtime_open"])
                self.assertEqual(entry["allowed_role_reads"], material_entries.ORDINARY_WORK_MATERIAL_ROLES)
            for body_ref in entry.get("body_refs") or []:
                self.assertTrue(body_ref["requires_runtime_open"])
                self.assertFalse(body_ref["ordinary_file_read_allowed"])


if __name__ == "__main__":
    unittest.main()
