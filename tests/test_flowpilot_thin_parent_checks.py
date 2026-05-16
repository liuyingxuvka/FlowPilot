from __future__ import annotations

import contextlib
import importlib.util
import io
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


thin_parent_checks = load_module(
    "flowpilot_test_thin_parent_checks",
    ROOT / "simulations" / "flowpilot_thin_parent_checks.py",
)
run_meta_checks = load_module(
    "flowpilot_test_thin_parent_run_meta_checks",
    ROOT / "simulations" / "run_meta_checks.py",
)


class FlowPilotThinParentChecksTests(unittest.TestCase):
    def test_meta_thin_parent_result_is_small_and_release_bounded(self) -> None:
        result = thin_parent_checks.build_thin_parent_result("meta")

        self.assertTrue(result["ok"])
        self.assertEqual(result["result_type"], "thin_parent")
        self.assertEqual(result["routine_confidence"], "current")
        self.assertLess(result["graph"]["state_count"], thin_parent_checks.HEAVYWEIGHT_STATE_THRESHOLD)
        self.assertTrue(result["legacy_full_regression"]["required_for_release"])
        self.assertIn(
            result["release_confidence"],
            {"current", "current_with_full_regression", "requires_full_regression"},
        )

    def test_missing_ledger_evidence_blocks_thin_parent(self) -> None:
        ledger = json.loads(thin_parent_checks.LEDGER_PATH.read_text(encoding="utf-8"))
        ledger["parents"]["meta"]["partitions"][0]["evidence_ids"].append(
            "missing_child_model_for_test"
        )

        with tempfile.TemporaryDirectory(
            prefix="flowpilot-thin-ledger-",
            dir=ROOT / "tmp",
        ) as tmp_name:
            tmp_ledger = Path(tmp_name) / "ledger.json"
            tmp_ledger.write_text(json.dumps(ledger), encoding="utf-8")
            old_ledger = thin_parent_checks.LEDGER_PATH
            try:
                thin_parent_checks.LEDGER_PATH = tmp_ledger
                result = thin_parent_checks.build_thin_parent_result("meta")
            finally:
                thin_parent_checks.LEDGER_PATH = old_ledger

        failures = result["thin_parent"]["failures"]
        self.assertFalse(result["ok"])
        self.assertIn("missing_child_evidence", {failure["code"] for failure in failures})

    def test_default_meta_runner_uses_thin_parent_without_full_graph(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-thin-runner-") as tmp_name:
            tmp = Path(tmp_name)
            old_results = run_meta_checks.RESULTS_PATH
            old_proof = run_meta_checks.PROOF_PATH
            old_graph = run_meta_checks._run_sharded_graph_checks
            try:
                run_meta_checks.RESULTS_PATH = tmp / "meta_thin_parent_results.json"
                run_meta_checks.PROOF_PATH = tmp / "meta_thin_parent_results.proof.json"

                def fail_if_called():
                    raise AssertionError("default runner expanded the legacy full graph")

                run_meta_checks._run_sharded_graph_checks = fail_if_called
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(run_meta_checks.main([]), 0)
                payload = json.loads(run_meta_checks.RESULTS_PATH.read_text(encoding="utf-8"))
                self.assertEqual(payload["result_type"], "thin_parent")
            finally:
                run_meta_checks.RESULTS_PATH = old_results
                run_meta_checks.PROOF_PATH = old_proof
                run_meta_checks._run_sharded_graph_checks = old_graph

    def test_forced_full_meta_runner_preserves_legacy_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-full-runner-") as tmp_name:
            tmp = Path(tmp_name)
            old_results = run_meta_checks.LEGACY_RESULTS_PATH
            old_proof = run_meta_checks.LEGACY_PROOF_PATH
            old_graph = run_meta_checks._run_sharded_graph_checks
            try:
                run_meta_checks.LEGACY_RESULTS_PATH = tmp / "results.json"
                run_meta_checks.LEGACY_PROOF_PATH = tmp / "results.proof.json"

                def small_full_graph():
                    return (
                        {"ok": True, "state_count": 1, "edge_count": 0},
                        {"ok": True, "stuck_state_count": 0},
                        {"ok": True, "nonterminating_component_count": 0},
                    )

                run_meta_checks._run_sharded_graph_checks = small_full_graph
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(run_meta_checks.main(["--full", "--force"]), 0)
                payload = json.loads(run_meta_checks.LEGACY_RESULTS_PATH.read_text(encoding="utf-8"))
                self.assertEqual(payload["result_type"], "legacy_full_parent")
                self.assertTrue(run_meta_checks.LEGACY_PROOF_PATH.exists())
            finally:
                run_meta_checks.LEGACY_RESULTS_PATH = old_results
                run_meta_checks.LEGACY_PROOF_PATH = old_proof
                run_meta_checks._run_sharded_graph_checks = old_graph


if __name__ == "__main__":
    unittest.main()
