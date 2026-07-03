from __future__ import annotations

import importlib.util
import json
import sys
import unittest
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
    "flowpilot_progress_lifecycle_cartesian_model",
    ROOT / "simulations" / "flowpilot_progress_lifecycle_cartesian_model.py",
)
runner = load_module(
    "run_flowpilot_progress_lifecycle_cartesian_checks",
    ROOT / "simulations" / "run_flowpilot_progress_lifecycle_cartesian_checks.py",
)


class FlowPilotProgressLifecycleCartesianTests(unittest.TestCase):
    def test_runner_accepts_full_progress_lifecycle_cartesian_matrix(self) -> None:
        report = runner.run_checks()

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["model_id"], model.MODEL_ID)
        self.assertEqual(report["matrix"]["full_product_count"], model.required_cell_count())
        self.assertGreaterEqual(report["matrix"]["full_product_count"], 20000)
        self.assertEqual(report["matrix"]["runtime_mismatch_count"], 0)
        self.assertEqual(report["matrix"]["node_order_variant_failures"], [])
        self.assertEqual(report["matrix"]["control_noise_variant_failures"], [])
        self.assertEqual(report["matrix"]["packet_projection_cells"], [])
        self.assertEqual(report["matrix"]["removed_status_projection_failures"], [])

    def test_persisted_result_matches_live_summary(self) -> None:
        persisted = json.loads(runner.RESULTS_PATH.read_text(encoding="utf-8"))
        live = runner.run_checks()

        self.assertTrue(persisted["ok"], persisted)
        self.assertEqual(persisted["ok"], live["ok"])
        self.assertEqual(persisted["model_id"], live["model_id"])
        for key in (
            "full_product_count",
            "axis_counts",
            "missing_axis_values",
            "runtime_mismatch_count",
            "node_order_variant_failures",
            "control_noise_variant_failures",
            "coverage_shard_count",
        ):
            with self.subTest(section="matrix", key=key):
                self.assertEqual(persisted["matrix"][key], live["matrix"][key])

    def test_every_declared_axis_value_is_covered(self) -> None:
        report = runner.run_checks()

        self.assertEqual(report["matrix"]["missing_axis_values"], {})
        for axis, values in model.AXIS_VALUES.items():
            with self.subTest(axis=axis):
                self.assertEqual(report["matrix"]["axis_counts"][axis], len(values))
                self.assertEqual(
                    set(report["matrix"]["axis_coverage"][axis]["observed"]),
                    set(values),
                )

    def test_removed_statuses_leave_denominator(self) -> None:
        for status in model.REMOVED_STATUSES:
            cell = next(
                candidate
                for candidate in model.iter_required_cells()
                if candidate["node_status"] == status
                and candidate["route_topology"] == "stable_active_route"
                and candidate["node_order_projection"] == "complete_effective_order"
                and candidate["node_kind"] == "leaf"
                and candidate["control_plane_noise"] == "none"
                and candidate["repair_generation"] == "positive"
            )
            expected = cell["expected_progress"]
            with self.subTest(status=status):
                self.assertEqual(expected["display"], "2/2")
                self.assertEqual(expected["expanded_nodes"], 2)
                self.assertEqual(expected["repair_generations"], 0)

    def test_active_node_order_projection_is_not_a_denominator_authority(self) -> None:
        baseline: dict[tuple[str, str, str, str, str], tuple[int, int, str]] = {}
        for cell in model.iter_required_cells():
            key = (
                str(cell["node_status"]),
                str(cell["route_topology"]),
                str(cell["node_kind"]),
                str(cell["control_plane_noise"]),
                str(cell["repair_generation"]),
            )
            progress = cell["expected_progress"]
            value = (progress["ended_nodes"], progress["expanded_nodes"], progress["source"])
            baseline.setdefault(key, value)
            self.assertEqual(baseline[key], value)

    def test_native_contract_exhaustion_and_testmesh_are_current(self) -> None:
        report = runner.run_checks()

        native = report["native_contract_exhaustion"]
        self.assertTrue(native["ok"], native)
        self.assertEqual(native["combination_case_count"], model.required_cell_count())
        self.assertEqual(native["required_model_obligation_count"], model.required_cell_count())
        self.assertIn(model.FLOWGUARD_NATIVE_RECEIPT_ID, native["required_coverage_receipt_ids"])

        test_mesh = report["test_mesh"]
        self.assertTrue(test_mesh["ok"], test_mesh)
        self.assertEqual(test_mesh["unowned_coverage_shard_ids"], [])
        self.assertIn(runner.RUNTIME_MATRIX_SUITE_ID, test_mesh["child_suites"])
        self.assertTrue(test_mesh["child_suites"][runner.RUNTIME_MATRIX_SUITE_ID]["evidence_current"])


if __name__ == "__main__":
    unittest.main()
