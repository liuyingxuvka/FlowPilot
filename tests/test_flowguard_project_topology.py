from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
    return module


topology = load_module(
    "flowguard_project_topology_under_test",
    ROOT / "scripts" / "flowguard_project_topology.py",
)


class FlowGuardProjectTopologyTests(unittest.TestCase):
    def test_build_report_contains_model_test_code_and_evidence_layers(self) -> None:
        report = topology.build_report(ROOT)

        self.assertEqual(report["artifact_type"], "flowguard_project_topology")
        self.assertTrue(report["orientation_only"])
        self.assertGreater(report["layer_counts"]["models"], 50)
        self.assertGreater(report["layer_counts"]["alignment_families"], 5)
        self.assertGreater(report["layer_counts"]["code_surfaces"], 100)
        self.assertGreater(report["layer_counts"]["test_commands"], 10)
        self.assertGreater(report["layer_counts"]["known_bad_signals"], 0)
        self.assertIn("route", report["areas"])
        self.assertIn("model-mesh", report["areas"])
        self.assertIn("model_test_alignment", report["evidence_summary"])
        self.assertIn("Topology guides project understanding only", report["validation_warning"])

    def test_render_markdown_names_orientation_boundary_and_area_map(self) -> None:
        report = topology.build_report(ROOT)
        markdown = topology.render_markdown(report)

        self.assertIn("FlowGuard Project Topology", markdown)
        self.assertIn("orientation only", markdown)
        self.assertIn("Area Map", markdown)
        self.assertIn("Model Runner Samples", markdown)
        self.assertIn("Alignment Families", markdown)
        self.assertIn("not validation evidence", markdown)

    def test_write_and_check_topology_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowguard-topology-") as tmp_name:
            tmp = Path(tmp_name)
            json_path = tmp / "topology.json"
            markdown_path = tmp / "topology.md"

            report = topology.write_topology(ROOT, json_path=json_path, markdown_path=markdown_path)
            check = topology.check_topology(ROOT, json_path=json_path, markdown_path=markdown_path)

            self.assertTrue(json_path.exists())
            self.assertTrue(markdown_path.exists())
            self.assertTrue(check["ok"], check["findings"])
            self.assertEqual(check["layer_counts"], report["layer_counts"])

    def test_check_reports_missing_and_stale_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowguard-topology-stale-") as tmp_name:
            tmp = Path(tmp_name)
            json_path = tmp / "topology.json"
            markdown_path = tmp / "topology.md"
            topology.write_topology(ROOT, json_path=json_path, markdown_path=markdown_path)
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            payload["sources"][0]["size"] = -1
            json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

            check = topology.check_topology(ROOT, json_path=json_path, markdown_path=markdown_path)

        self.assertFalse(check["ok"])
        self.assertIn("topology_source_stale", {finding["code"] for finding in check["findings"]})

    def test_check_rejects_missing_required_layers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowguard-topology-layer-") as tmp_name:
            tmp = Path(tmp_name)
            json_path = tmp / "topology.json"
            markdown_path = tmp / "topology.md"
            topology.write_topology(ROOT, json_path=json_path, markdown_path=markdown_path)
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            payload["layer_counts"]["code_surfaces"] = 0
            json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

            check = topology.check_topology(ROOT, json_path=json_path, markdown_path=markdown_path)

        self.assertFalse(check["ok"])
        self.assertIn("code_layer_missing", {finding["code"] for finding in check["findings"]})


if __name__ == "__main__":
    unittest.main()
