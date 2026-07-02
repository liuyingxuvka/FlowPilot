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

import flowpilot_material_artifact_map as material_map  # noqa: E402
import flowpilot_material_artifact_map_entries as material_entries  # noqa: E402
import flowpilot_material_artifact_map_ordinary as material_ordinary  # noqa: E402
import flowpilot_material_artifact_map_packets as material_packets  # noqa: E402
import packet_runtime  # noqa: E402


class FlowPilotMaterialAccessMeshTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="flowpilot-material-access-mesh-"))

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_ordinary_project_material_is_public_but_sealed_bodies_stay_runtime_authorized(self) -> None:
        project_root = self._tmp
        run_root = project_root / ".flowpilot" / "runs" / "run-material-mesh"
        material_dir = run_root / "material"
        packet_dir = run_root / "packets" / "packet-001"
        result_dir = run_root / "results" / "packet-001"
        chapter_dir = run_root / "chapters"
        for path in (material_dir, packet_dir, result_dir, chapter_dir):
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
            material_dir / "material_scan_packets.json",
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
            index_path=material_dir / "material_scan_packets.json",
            batch_kind="material_scan",
        )
        material_ordinary.add_ordinary_work_artifact_entries(
            project_root,
            run_root,
            direct_entries,
            material_artifact_map_filename=material_map.MATERIAL_ARTIFACT_MAP_FILENAME,
        )
        direct_rendered = json.dumps(direct_entries, sort_keys=True)
        self.assertIn("material_scan:packet:packet-001", {entry["entry_id"] for entry in direct_entries})
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

        doc = material_map.refresh_material_artifact_map(project_root, run_root, {"run_id": "run-material-mesh"})
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
