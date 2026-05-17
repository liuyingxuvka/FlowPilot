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


alignment_runner = load_module(
    "flowpilot_test_model_test_alignment_runner",
    ROOT / "simulations" / "run_flowpilot_model_test_alignment_checks.py",
)


class FlowPilotModelTestAlignmentTests(unittest.TestCase):
    def test_alignment_report_is_green_for_declared_current_scope(self) -> None:
        report = alignment_runner.build_report()

        self.assertTrue(report["ok"], report["findings"])
        self.assertTrue(report["alignment_ok"], report["findings"])
        self.assertTrue(report["known_bad_ok"])
        self.assertEqual(
            report["families"],
            [
                "startup",
                "packet/card/ack",
                "route mutation",
                "terminal/closure/resume",
                "role/output contracts",
                "router loop/daemon",
                "test tiering/slow-test contracts",
                "meta/capability parents",
            ],
        )
        self.assertEqual(report["findings"], [])

    def test_each_plan_serializes_obligations_evidence_and_flowguard_report(self) -> None:
        report = alignment_runner.build_report()

        for plan in report["per_plan"]:
            with self.subTest(family=plan["family"]):
                self.assertTrue(plan["ok"], plan)
                self.assertEqual(plan["decision"], "model_test_alignment_green")
                self.assertTrue(plan["model_checks"])
                self.assertIn("coverage_boundary", plan)
                self.assertGreaterEqual(len(plan["plan"]["obligations"]), 1)
                self.assertGreaterEqual(len(plan["plan"]["test_evidence"]), 1)
                self.assertEqual(plan["report"]["findings"], [])
                self.assertIn("model_test_alignment_green", plan["report"]["summary"])

    def test_known_bad_sanity_checks_cover_required_hazards(self) -> None:
        report = alignment_runner.build_report()
        checks = {case["name"]: case for case in report["known_bad_sanity_checks"]}

        for name in (
            "missing_evidence",
            "stale_evidence",
            "progress_only_background_evidence",
            "overclaim_model_confidence",
            "orphan_evidence",
            "duplicate_same_kind_evidence",
        ):
            with self.subTest(name=name):
                self.assertIn(name, checks)
                self.assertTrue(checks[name]["ok"], checks[name])
                self.assertLessEqual(
                    set(checks[name]["expected_codes"]),
                    set(checks[name]["finding_codes"]),
                )
                self.assertFalse(checks[name]["report"]["ok"])

    def test_progress_only_background_evidence_is_not_passing_coverage(self) -> None:
        report = alignment_runner.build_report()
        case = {
            item["name"]: item for item in report["known_bad_sanity_checks"]
        }["progress_only_background_evidence"]

        self.assertIn("test_evidence_not_passing", case["finding_codes"])
        self.assertIn("missing_test_evidence", case["finding_codes"])
        evidence = case["plan"]["test_evidence"][0]
        self.assertEqual(evidence["result_status"], "running")

    def test_route_mutation_negative_evidence_points_to_runtime_tests(self) -> None:
        entries = alignment_runner.build_alignment_plan_entries()
        route_entry = next(entry for entry in entries if entry["family"] == "route mutation")
        evidence = {item.evidence_id: item for item in route_entry["plan"].test_evidence}

        for evidence_id in (
            "route_mutation.negative.required_preconditions",
            "route_mutation.negative.old_sibling_proof",
        ):
            with self.subTest(evidence_id=evidence_id):
                item = evidence[evidence_id]
                self.assertEqual(item.path, "tests/router_runtime/route_mutation.py")
                self.assertIn("tests.router_runtime.route_mutation", item.command)

    def test_main_writes_json_only_when_requested(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-alignment-runner-") as tmp_name:
            output_path = Path(tmp_name) / "alignment.json"
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                exit_code = alignment_runner.main(["--json-out", str(output_path)])

            self.assertEqual(exit_code, 0)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["ok"])
            self.assertEqual(json.loads(stdout.getvalue()), payload)


if __name__ == "__main__":
    unittest.main()
