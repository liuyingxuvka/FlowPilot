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
run_flowguard_coverage_sweep = load_module(
    "flowpilot_test_run_flowguard_coverage_sweep",
    ROOT / "scripts" / "run_flowguard_coverage_sweep.py",
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
        self.assertEqual(before, after)

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
                        "current_run_id": "run-20260503-030303",
                        "current_run_root": ".flowpilot/runs/run-20260503-030303",
                    }
                ),
                encoding="utf-8",
            )
            (root / ".flowpilot" / "index.json").write_text(
                json.dumps(
                    {
                        "current_run_id": "run-20260503-030303",
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


if __name__ == "__main__":
    unittest.main()
