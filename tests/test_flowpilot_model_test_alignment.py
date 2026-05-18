from __future__ import annotations

import ast
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
        self.assertTrue(report["source_audit_ok"], report["findings"])
        self.assertTrue(report["source_known_bad_ok"])
        self.assertTrue(report["full_diagnostic_ok"])
        self.assertFalse(report["full_coverage_ok"])
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

    def test_full_diagnostic_inventory_reports_current_gap_classes(self) -> None:
        report = alignment_runner.build_report()
        diagnostic = report["full_model_test_code_diagnostic"]

        self.assertTrue(diagnostic["ok"], diagnostic["known_bad_sanity_checks"])
        self.assertFalse(diagnostic["full_coverage_ok"])
        self.assertGreater(diagnostic["surface_count"], 100)
        for kind in (
            "owner_module",
            "compatibility_facade",
            "script_entrypoint",
            "model_check_runner",
            "test_tier",
            "test_tier_command",
        ):
            with self.subTest(kind=kind):
                self.assertGreater(diagnostic["surface_counts"].get(kind, 0), 0)

        for code in (
            "missing_model",
            "missing_test",
            "extra_code",
            "internal_only_test",
            "needs_structure_split",
        ):
            with self.subTest(code=code):
                self.assertGreater(diagnostic["gap_counts"].get(code, 0), 0)

        surfaces = {surface["surface_id"]: surface for surface in diagnostic["surfaces"]}
        self.assertIn("asset:flowpilot_router", surfaces)
        self.assertIn("script:run_test_tier", surfaces)
        self.assertIn("model-check:run_flowpilot_model_test_alignment_checks", surfaces)
        self.assertIn("tier:router", surfaces)

    def test_full_diagnostic_known_bad_cases_cover_false_confidence_hazards(self) -> None:
        diagnostic = alignment_runner.build_report()["full_model_test_code_diagnostic"]
        checks = {case["name"]: case for case in diagnostic["known_bad_sanity_checks"]}

        for name in (
            "orphan_code",
            "wrapper_only_evidence",
            "progress_only_background",
            "broad_unsplit_module",
        ):
            with self.subTest(name=name):
                self.assertIn(name, checks)
                self.assertTrue(checks[name]["ok"], checks[name])
                self.assertLessEqual(
                    set(checks[name]["expected_codes"]),
                    set(checks[name]["finding_codes"]),
                )

    def test_source_audit_binds_code_contracts_to_real_python_sources(self) -> None:
        report = alignment_runner.build_report()
        source_plan = report["source_contract_plan"]

        self.assertTrue(source_plan["ok"], source_plan["findings"])
        self.assertTrue(source_plan["alignment_report"]["ok"])
        self.assertTrue(source_plan["source_audit_report"]["ok"])
        self.assertEqual(source_plan["source_audit_report"]["findings"], [])
        self.assertIn("AST-supported subset", source_plan["source_audit_boundary"])

        code_contract_ids = {
            item["code_contract_id"] for item in source_plan["plan"]["code_contracts"]
        }
        for code_contract_id in (
            "router.record_external_event",
            "packet.create_packet",
            "card.submit_card_ack",
            "route_sign.generate",
            "role_output.prepare_output_session",
            "test_tier.commands_for_tier",
            "meta_runner.main",
            "smoke.main",
        ):
            with self.subTest(code_contract_id=code_contract_id):
                self.assertIn(code_contract_id, code_contract_ids)

        for evidence in source_plan["source_audit_report"]["test_evidence"]:
            with self.subTest(evidence=evidence["evidence_id"]):
                self.assertTrue(evidence["found"], evidence)
                self.assertGreater(evidence["assert_count"], 0, evidence)
                self.assertEqual(evidence["assertion_scope"], "external_contract")

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

    def test_each_declared_test_evidence_path_contains_definition_when_source_auditable(self) -> None:
        skipped_names = {
            "run_packet_control_plane_checks",
            "FlowPilotControlGateTests meta/capability invariant checks",
        }
        evidence_rows = []
        for entry in alignment_runner.build_alignment_plan_entries():
            evidence_rows.extend(entry["plan"].test_evidence)
        evidence_rows.extend(
            alignment_runner.build_source_contract_alignment_plan().test_evidence
        )

        names_by_path: dict[str, set[str]] = {}
        for evidence in evidence_rows:
            if evidence.test_name in skipped_names:
                continue
            if not (
                evidence.test_name.startswith("test_")
                or evidence.test_name.startswith("Test")
            ):
                continue
            names = names_by_path.get(evidence.path)
            if names is None:
                source = (ROOT / evidence.path).read_text(encoding="utf-8")
                tree = ast.parse(source, filename=evidence.path)
                names = {
                    node.name
                    for node in ast.walk(tree)
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                }
                names_by_path[evidence.path] = names
            with self.subTest(evidence_id=evidence.evidence_id, path=evidence.path):
                self.assertIn(evidence.test_name, names)

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

    def test_source_known_bad_sanity_checks_cover_ast_hazards(self) -> None:
        report = alignment_runner.build_report()
        checks = {
            case["name"]: case
            for case in report["source_known_bad_sanity_checks"]
        }

        for name in (
            "missing_python_symbol",
            "internal_path_only_test",
            "missing_external_assertion",
            "extra_side_effect",
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
                self.assertTrue(item.path.startswith("tests/router_runtime/route_mutation_"))
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
