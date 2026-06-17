from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
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


audit_validation_artifacts = load_module(
    "flowpilot_test_audit_validation_artifacts",
    ROOT / "scripts" / "audit_validation_artifacts.py",
)
flowpilot_runtime_retention = load_module(
    "flowpilot_test_runtime_retention",
    ROOT / "scripts" / "flowpilot_runtime_retention.py",
)
flowpilot_paths_wrapper = load_module(
    "flowpilot_test_script_flowpilot_paths",
    ROOT / "scripts" / "flowpilot_paths.py",
)
flowpilot_user_flow_diagram_wrapper = load_module(
    "flowpilot_test_script_flowpilot_user_flow_diagram",
    ROOT / "scripts" / "flowpilot_user_flow_diagram.py",
)
run_flowguard_coverage_sweep = load_module(
    "flowpilot_test_run_flowguard_coverage_sweep",
    ROOT / "scripts" / "run_flowguard_coverage_sweep.py",
)
flowpilot_maintenance_registry = load_module(
    "flowpilot_test_maintenance_registry",
    ROOT / "scripts" / "flowpilot_maintenance_registry.py",
)
install_checks_common = load_module(
    "flowpilot_test_install_checks_common",
    ROOT / "scripts" / "install_checks" / "common.py",
)
flowpilot_maintenance_map = load_module(
    "flowpilot_test_maintenance_map",
    ROOT / "scripts" / "flowpilot_maintenance_map.py",
)
flowpilot_thin_parent_checks = load_module(
    "flowpilot_test_thin_parent_checks",
    ROOT / "simulations" / "flowpilot_thin_parent_checks.py",
)
flowpilot_model_hierarchy_inventory = load_module(
    "flowpilot_test_model_hierarchy_inventory",
    ROOT / "simulations" / "flowpilot_model_hierarchy_checks_runner_inventory.py",
)


class FlowPilotMaintenanceToolTests(unittest.TestCase):
    def test_validation_artifact_audit_reports_duplicate_pairs_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-artifact-audit-") as tmp_name:
            tmp = Path(tmp_name)
            checks = tmp / "sample_checks_results.json"
            results = tmp / "sample_results.json"
            other = tmp / "other_results.json"
            payload = {"ok": True, "states": 3}
            checks.write_text(json.dumps(payload), encoding="utf-8")
            results.write_text(json.dumps(payload), encoding="utf-8")
            other.write_text(json.dumps({"ok": True, "states": 4}), encoding="utf-8")

            before = {path.name: path.read_text(encoding="utf-8") for path in tmp.iterdir()}
            report = audit_validation_artifacts.build_report(tmp)
            after = {path.name: path.read_text(encoding="utf-8") for path in tmp.iterdir()}

        self.assertTrue(report["read_only"])
        self.assertEqual(report["artifact_count"], 3)
        self.assertEqual(report["duplicate_group_count"], 1)
        self.assertEqual(report["runner_duplicate_pair_count"], 1)
        self.assertEqual(report["shadow_pair_count"], 1)
        self.assertFalse(report["shadow_result_pairs"][0]["semantic_drift"])
        self.assertEqual(before, after)

    def test_validation_artifact_audit_reports_stale_shadow_semantics(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-artifact-audit-stale-") as tmp_name:
            tmp = Path(tmp_name)
            checks = tmp / "sample_checks_results.json"
            results = tmp / "sample_results.json"
            checks.write_text(
                json.dumps({"ok": True, "note": "retaining modelability names as unsupported_historical aliases"}),
                encoding="utf-8",
            )
            results.write_text(json.dumps({"ok": True, "note": "current canonical artifact"}), encoding="utf-8")

            report = audit_validation_artifacts.build_report(tmp)

        self.assertEqual(report["shadow_pair_count"], 1)
        self.assertEqual(report["semantic_drift_pair_count"], 1)
        self.assertEqual(report["stale_shadow_semantics_pair_count"], 1)
        self.assertTrue(report["stale_shadow_semantics_pairs"][0]["stale_shadow_semantics"])

    def test_parent_evidence_prefers_canonical_results_over_shadow_checks(self) -> None:
        thin_rows = flowpilot_thin_parent_checks.result_index()
        hierarchy_rows = flowpilot_model_hierarchy_inventory._result_index()

        self.assertEqual(
            thin_rows["flowpilot_repair_transaction"]["result_file"],
            "simulations/flowpilot_repair_transaction_results.json",
        )
        self.assertEqual(
            thin_rows["flowpilot_dynamic_return_path"]["result_file"],
            "simulations/flowpilot_dynamic_return_path_results.json",
        )
        self.assertEqual(
            hierarchy_rows["flowpilot_repair_transaction"]["result_file"],
            "simulations/flowpilot_repair_transaction_results.json",
        )
        self.assertEqual(
            hierarchy_rows["flowpilot_dynamic_return_path"]["result_file"],
            "simulations/flowpilot_dynamic_return_path_results.json",
        )

    def test_runtime_retention_report_preserves_current_run_and_reports_excess(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-runtime-retention-") as tmp_name:
            root = Path(tmp_name)
            runs = root / ".flowpilot" / "runs"
            for run_id in ("run-20260501-010101", "run-20260502-020202", "run-20260503-030303"):
                run_root = runs / run_id
                run_root.mkdir(parents=True)
                (run_root / "state.json").write_text("{}", encoding="utf-8")
            (root / ".flowpilot" / "current.json").write_text(
                json.dumps(
                    {
                        "run_id": "run-20260503-030303",
                        "run_root": ".flowpilot/runs/run-20260503-030303",
                    }
                ),
                encoding="utf-8",
            )
            (root / ".flowpilot" / "index.json").write_text(
                json.dumps(
                    {
                        "run_id": "run-20260503-030303",
                        "runs": [
                            {"run_id": "run-20260501-010101", "created_at": "2026-05-01T01:01:01Z"},
                            {"run_id": "run-20260502-020202", "created_at": "2026-05-02T02:02:02Z"},
                            {"run_id": "run-20260503-030303", "created_at": "2026-05-03T03:03:03Z"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            report = flowpilot_runtime_retention.build_report(root, max_runs=2)

        self.assertTrue(report["read_only"])
        self.assertEqual(report["current_run_id"], "run-20260503-030303")
        self.assertEqual(report["run_directory_count"], 3)
        self.assertEqual(report["excess_run_directory_count"], 1)
        self.assertEqual(len(report["stale_candidates"]), 1)
        self.assertFalse(report["stale_candidates"][0]["is_current"])

    def test_script_flowpilot_paths_delegates_to_skill_asset_source(self) -> None:
        self.assertTrue(flowpilot_paths_wrapper.ASSET_PATH.is_file())
        self.assertTrue(callable(flowpilot_paths_wrapper.resolve_flowpilot_paths))
        resolved = flowpilot_paths_wrapper.resolve_flowpilot_paths(ROOT)
        self.assertIn("flowpilot_root", resolved)
        self.assertEqual(resolved["project_root"], ROOT.resolve())

    def test_script_user_flow_diagram_delegates_to_skill_asset_source(self) -> None:
        self.assertTrue(flowpilot_user_flow_diagram_wrapper.ASSET_PATH.is_file())
        self.assertTrue(callable(flowpilot_user_flow_diagram_wrapper.generate))
        self.assertTrue(callable(flowpilot_user_flow_diagram_wrapper.main))
        self.assertNotEqual(
            flowpilot_user_flow_diagram_wrapper.__file__,
            str(flowpilot_user_flow_diagram_wrapper.ASSET_PATH),
        )

    def test_current_pointer_template_uses_only_current_contract_fields(self) -> None:
        template = json.loads((ROOT / "templates" / "flowpilot" / "current.template.json").read_text(encoding="utf-8"))

        self.assertEqual(template["run_id"], "run-001")
        self.assertEqual(template["run_root"], ".flowpilot/runs/run-001")
        self.assertNotIn("current_run_id", template)
        self.assertNotIn("current_run_root", template)
        self.assertNotIn("active_run_id", template)
        self.assertNotIn("active_run_root", template)

    def test_startup_templates_do_not_offer_fallback_modes(self) -> None:
        paths = [
            ROOT / "templates" / "flowpilot" / "state.template.json",
            ROOT / "templates" / "flowpilot" / "startup_mechanical_audit.template.json",
            ROOT / "templates" / "flowpilot" / "pm_startup_intake_decision.template.json",
            ROOT / "templates" / "flowpilot" / "standard_scenario_pack.template.json",
            ROOT / "templates" / "flowpilot" / "capabilities.template.json",
        ]

        for path in paths:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8").lower()
                self.assertNotIn("fallback", text)

    def test_current_runtime_templates_do_not_reintroduce_fallback_continuity(self) -> None:
        checked_text = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in [
                ROOT / "templates" / "flowpilot" / "README.md",
                ROOT / "templates" / "flowpilot" / "continuation_evidence.template.json",
                ROOT / "templates" / "flowpilot" / "execution_frontier.template.json",
                ROOT / "templates" / "flowpilot" / "role_binding_ledger.template.json",
            ]
        )

        forbidden = [
            "single-agent fallback",
            "user fallback",
            "fallback_node",
            "fallback_projection_method",
            "native/fallback",
            "chat fallback",
        ]
        for phrase in forbidden:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, checked_text)

    def test_coverage_sweep_requests_json_stdout_when_runner_also_has_json_out(self) -> None:
        script_path = ROOT / "simulations" / "run_flowpilot_dispatch_recipient_gate_checks.py"
        script_text = """
parser.add_argument("--json", action="store_true")
parser.add_argument("--json-out", type=Path)
if args.json_out:
    args.json_out.write_text(payload, encoding="utf-8")
"""
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout='{"ok": true}\n',
            stderr="",
        )
        with mock.patch.object(
            run_flowguard_coverage_sweep.subprocess,
            "run",
            return_value=completed,
        ) as run_mock:
            payload, metadata = run_flowguard_coverage_sweep._run_runner(
                script_path,
                script_text,
                timeout_seconds=10,
            )

        command = run_mock.call_args.args[0]
        self.assertIn("--json", command)
        self.assertNotIn("--json-out", command)
        self.assertEqual(payload, {"ok": True})
        self.assertIsNone(metadata["parse_error"])

    def test_coverage_sweep_resolves_root_simulations_result_path(self) -> None:
        script_path = ROOT / "simulations" / "run_flowpilot_field_mesh_checks.py"
        result_path = run_flowguard_coverage_sweep._declared_result_path(
            script_path,
            'RESULTS_PATH = ROOT / "simulations" / "flowpilot_field_mesh_results.json"',
        )

        self.assertEqual(
            result_path,
            ROOT / "simulations" / "flowpilot_field_mesh_results.json",
        )

    def test_coverage_sweep_runs_final_confidence_as_repository_only_diagnostic(self) -> None:
        script_path = ROOT / "simulations" / "run_flowpilot_final_confidence_gate_checks.py"
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout='{"ok": true}\n',
            stderr="",
        )
        with mock.patch.object(
            run_flowguard_coverage_sweep.subprocess,
            "run",
            return_value=completed,
        ) as run_mock:
            payload, metadata = run_flowguard_coverage_sweep._run_runner(
                script_path,
                script_path.read_text(encoding="utf-8"),
                timeout_seconds=10,
            )

        command = run_mock.call_args.args[0]
        self.assertIn("--run-checks", command)
        self.assertIn("--repository-confidence-only", command)
        self.assertIn("--json-out", command)
        self.assertIn("flowpilot_final_confidence_gate_results.json", " ".join(command))
        self.assertEqual(payload, {"ok": True})
        self.assertIsNone(metadata["parse_error"])

    def test_maintenance_map_records_owner_modules_tiers_and_diagnostic_status(self) -> None:
        report = flowpilot_maintenance_map.build_report(ROOT)

        self.assertTrue(report["read_only"])
        self.assertGreater(report["categories"]["runtime_assets"]["file_count"], 0)
        self.assertGreater(report["runtime_owner_modules"]["file_count"], 0)
        self.assertEqual(
            report["runtime_owner_modules"]["over_threshold_count"],
            len(report["runtime_owner_modules"]["over_threshold"]),
        )
        self.assertIn("fast", report["test_tiers"]["tier_names"])
        self.assertTrue(report["diagnostic"]["present"])
        diagnostic_payload = json.loads(
            (ROOT / "simulations" / "flowpilot_model_test_alignment_results.json").read_text(encoding="utf-8")
        )
        full = diagnostic_payload["full_model_test_code_diagnostic"]
        self.assertEqual(report["diagnostic"]["full_coverage_ok"], diagnostic_payload["full_coverage_ok"])
        self.assertEqual(report["diagnostic"]["gap_surface_count"], full["gap_surface_count"])
        runtime_decision = report["current_maintenance_decisions"][0]
        if report["runtime_owner_modules"]["over_threshold_count"]:
            self.assertIn("currently have", runtime_decision)
            self.assertIn("over the StructureMesh line threshold", runtime_decision)
        else:
            self.assertIn("are under the StructureMesh line threshold", runtime_decision)

    def test_maintenance_registry_is_source_for_map_facade_and_entrypoint_lists(self) -> None:
        self.assertEqual(
            tuple(flowpilot_maintenance_map.RUNTIME_FACADES),
            flowpilot_maintenance_registry.RUNTIME_FACADES,
        )
        self.assertEqual(
            tuple(flowpilot_maintenance_map.SCRIPT_ENTRYPOINTS),
            flowpilot_maintenance_registry.SCRIPT_ENTRYPOINTS,
        )
        self.assertEqual(
            tuple(flowpilot_maintenance_map.MODEL_FACADES),
            flowpilot_maintenance_registry.MODEL_FACADES,
        )
        self.assertEqual(
            dict(flowpilot_maintenance_map.THRESHOLDS),
            dict(flowpilot_maintenance_registry.THRESHOLDS),
        )
        self.assertTrue(
            set(flowpilot_maintenance_registry.install_required_surface_paths()).issubset(
                set(install_checks_common.REQUIRED_FILES)
            )
        )

    def test_maintenance_map_markdown_names_public_facades_and_scripts(self) -> None:
        report = flowpilot_maintenance_map.build_report(ROOT)
        markdown = flowpilot_maintenance_map.render_markdown(report)

        self.assertIn("FlowPilot Maintenance Map", markdown)
        self.assertIn("flowpilot_router.py", markdown)
        self.assertIn("run_test_tier.py", markdown)
        self.assertIn("Model-test-code diagnostic", markdown)
        self.assertIn("Current decisions", markdown)


if __name__ == "__main__":
    unittest.main()
