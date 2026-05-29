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
        self.assertTrue(report["release_convergence_ok"])
        if not report["full_coverage_ok"]:
            diagnostic = report["full_model_test_code_diagnostic"]
            self.assertGreater(diagnostic["deferred_structure_split_count"], 0)
            self.assertEqual(diagnostic["unresolved_non_deferred_gap_count"], 0)
        self.assertEqual(
            report["families"],
            [
                "startup",
                "packet/card/ack",
                "packet result family",
                "route mutation",
                "terminal/closure/resume",
                "role/output contracts",
                "router loop/daemon",
                "repair transactions",
                "test tiering/slow-test contracts",
                "meta/capability parents",
            ],
        )
        self.assertEqual(report["findings"], [])

    def test_full_diagnostic_inventory_reports_current_gap_classes(self) -> None:
        report = alignment_runner.build_report()
        diagnostic = report["full_model_test_code_diagnostic"]

        self.assertTrue(diagnostic["ok"], diagnostic["known_bad_sanity_checks"])
        self.assertTrue(diagnostic["release_convergence_ok"])
        self.assertGreater(diagnostic["surface_count"], 100)
        for kind in (
            "owner_module",
            "public_facade",
            "script_entrypoint",
            "model_check_runner",
            "test_tier",
            "test_tier_command",
        ):
            with self.subTest(kind=kind):
                self.assertGreater(diagnostic["surface_counts"].get(kind, 0), 0)

        self.assertEqual(diagnostic["gap_counts"].get("missing_model", 0), 0)
        self.assertEqual(diagnostic["gap_counts"].get("extra_code", 0), 0)
        self.assertEqual(diagnostic["gap_counts"].get("internal_only_test", 0), 0)
        self.assertEqual(diagnostic["gap_counts"].get("missing_test", 0), 0)
        self.assertEqual(diagnostic["unresolved_non_deferred_gap_count"], 0)
        self.assertNotIn("stale_evidence", diagnostic["gap_counts"])

        gate_contract_gaps = [
            finding
            for finding in diagnostic["actionable_findings"]
            if finding["release_relevance"] in {"release_gate", "validation_gate"}
            and finding["code"] in {"missing_test", "internal_only_test"}
        ]
        self.assertEqual(gate_contract_gaps, [])

        for field in (
            "gap_counts_by_severity",
            "gap_counts_by_repair_type",
            "gap_counts_by_release_relevance",
            "actionable_summary",
        ):
            with self.subTest(field=field):
                self.assertIn(field, diagnostic)
        non_deferred_findings = [
            finding
            for finding in diagnostic["actionable_findings"]
            if finding["repair_type"] != "defer_structure_split"
        ]
        self.assertEqual(non_deferred_findings, [])
        if diagnostic["full_coverage_ok"]:
            self.assertEqual(diagnostic["gap_counts"].get("needs_structure_split", 0), 0)
            self.assertEqual(diagnostic["actionable_findings"], [])
            self.assertEqual(diagnostic["actionable_summary"], [])
        else:
            self.assertGreater(diagnostic["gap_counts"].get("needs_structure_split", 0), 0)
            self.assertGreater(diagnostic["deferred_structure_split_count"], 0)

        surfaces = {surface["surface_id"]: surface for surface in diagnostic["surfaces"]}
        self.assertIn("asset:flowpilot_router", surfaces)
        self.assertIn("script:run_test_tier", surfaces)
        self.assertIn("model-check:run_flowpilot_model_test_alignment_checks", surfaces)
        self.assertIn("tier:router", surfaces)
        self.assertIn("model-check:run_flowpilot_singleton_identity_checks", surfaces)
        singleton_authority = diagnostic["singleton_authority_coverage"]
        self.assertTrue(singleton_authority["ok"], singleton_authority)
        self.assertGreaterEqual(singleton_authority["authority_matrix_count"], 8)
        self.assertEqual(
            "simulations/flowpilot_singleton_identity_results.json",
            singleton_authority["result_path"],
        )
        for surface_id in (
            "asset:flowpilot_router",
            "script:run_test_tier",
            "tier:router",
        ):
            with self.subTest(surface_id=surface_id):
                surface = surfaces[surface_id]
                self.assertIn("surface_owner", surface)
                self.assertIn("release_relevance", surface)
                self.assertIn("repair_types", surface)
                self.assertIn("max_severity", surface)

        for finding in diagnostic["actionable_findings"][:20]:
            with self.subTest(finding=finding["dedupe_key"]):
                for field in (
                    "severity",
                    "surface_owner",
                    "release_relevance",
                    "repair_type",
                    "dedupe_key",
                    "priority_score",
                ):
                    self.assertIn(field, finding)

        priority_scores = [
            item["priority_score"] for item in diagnostic["actionable_findings"]
        ]
        self.assertEqual(priority_scores, sorted(priority_scores))


    def test_full_diagnostic_known_bad_cases_cover_false_confidence_hazards(self) -> None:
        diagnostic = alignment_runner.build_report()["full_model_test_code_diagnostic"]
        checks = {case["name"]: case for case in diagnostic["known_bad_sanity_checks"]}

        for name in (
            "orphan_code",
            "wrapper_only_evidence",
            "progress_only_background",
            "local_only_release_proof",
            "broad_unsplit_module",
        ):
            with self.subTest(name=name):
                self.assertIn(name, checks)
                self.assertTrue(checks[name]["ok"], checks[name])
                self.assertLessEqual(
                    set(checks[name]["expected_codes"]),
                    set(checks[name]["finding_codes"]),
                )
                surface = checks[name]["surface"]
                self.assertIn("surface_owner", surface)
                self.assertIn("release_relevance", surface)
                self.assertIn("repair_types", surface)

        self.assertIn(
            "rerun_public_release_evidence",
            checks["local_only_release_proof"]["surface"]["repair_types"],
        )

    def test_full_diagnostic_recognizes_public_contract_and_split_metadata(self) -> None:
        diagnostic = alignment_runner.build_report()["full_model_test_code_diagnostic"]
        surfaces = {surface["surface_id"]: surface for surface in diagnostic["surfaces"]}

        for surface_id in (
            "asset:packet_runtime",
            "asset:flowpilot_router_controller_scheduler_receipts",
            "asset:flowpilot_router_work_packets_pm_role",
            "asset:flowpilot_router_terminal_ledger",
        ):
            with self.subTest(surface_id=surface_id):
                surface = surfaces[surface_id]
                self.assertTrue(surface["has_external_contract"], surface)
                self.assertNotIn("internal_only_test", surface["gap_codes"])

        for surface_id in (
            "tier:integration",
            "tier-command:integration:smoke_autopilot_fast",
            "tier-command:all:smoke_autopilot_fast",
        ):
            with self.subTest(surface_id=surface_id):
                surface = surfaces[surface_id]
                self.assertTrue(surface["has_external_contract"], surface)
                self.assertNotIn("missing_test", surface["gap_codes"])
                self.assertNotIn("internal_only_test", surface["gap_codes"])

        for surface_id in (
            "script:install_flowpilot",
            "script:audit_local_install_sync",
            "script:check_install",
            "script:check_public_release",
            "script:flowpilot_packets",
            "script:flowpilot_outputs",
            "script:flowpilot_lifecycle",
            "script:run_test_tier",
        ):
            with self.subTest(surface_id=surface_id):
                surface = surfaces[surface_id]
                self.assertTrue(surface["has_test"], surface)
                self.assertTrue(surface["has_external_contract"], surface)
                self.assertNotIn("internal_only_test", surface["gap_codes"])

        completed_runtime_split = surfaces["asset:flowpilot_router_card_returns"]
        self.assertEqual(completed_runtime_split["split_status"], "completed_split")
        self.assertTrue(completed_runtime_split["has_external_contract"], completed_runtime_split)
        self.assertNotIn("needs_structure_split", completed_runtime_split["gap_codes"])
        self.assertIn("peer_safety_status", completed_runtime_split)

        completed = surfaces["asset:flowpilot_router_protocol_boot_cards"]
        self.assertEqual(completed["split_status"], "completed_split")
        self.assertTrue(completed["has_external_contract"], completed)
        self.assertNotIn("needs_structure_split", completed["gap_codes"])
        for surface_id in (
            "asset:flowpilot_router_protocol_startup_catalog",
            "asset:flowpilot_router_protocol_planning_cards",
            "asset:flowpilot_router_protocol_runtime_cards",
            "asset:flowpilot_router_protocol_card_metadata",
        ):
            with self.subTest(completed_split_surface=surface_id):
                surface = surfaces[surface_id]
                self.assertTrue(surface["has_external_contract"], surface)
                self.assertEqual(surface["gap_codes"], [])

        split_table = surfaces["asset:flowpilot_router_protocol_external_event_data"]
        self.assertEqual(split_table["split_status"], "completed_split")
        self.assertEqual(split_table["safe_split_class"], "declarative_protocol_table")
        self.assertLessEqual(split_table["line_count"], split_table["split_threshold"])
        self.assertEqual(split_table["top_level_function_count"], 0)
        self.assertEqual(split_table["top_level_class_count"], 0)
        self.assertNotIn("needs_structure_split", split_table["gap_codes"])
        self.assertTrue(split_table["has_external_contract"], split_table)
        for surface_id in (
            "asset:flowpilot_router_protocol_external_event_data_startup",
            "asset:flowpilot_router_protocol_external_event_data_material",
            "asset:flowpilot_router_protocol_external_event_data_route",
            "asset:flowpilot_router_protocol_external_event_data_terminal",
        ):
            with self.subTest(completed_external_event_data_surface=surface_id):
                surface = surfaces[surface_id]
                self.assertTrue(surface["has_external_contract"], surface)
                self.assertEqual(surface["gap_codes"], [])

    def test_full_diagnostic_uses_background_artifact_classification(self) -> None:
        diagnostic = alignment_runner.build_report()["full_model_test_code_diagnostic"]
        surfaces = {surface["surface_id"]: surface for surface in diagnostic["surfaces"]}
        surface = surfaces["tier-command:release:public_release_check"]

        self.assertIn(
            surface["evidence_status"],
            {
                "failed",
                "incomplete",
                "missing_final_artifacts",
                "passed",
                "progress_only",
                "release_local_only",
                "running",
                "stale",
            },
        )
        self.assertIn("background_evidence", surface)
        self.assertIn("selected", surface["background_evidence"])
        if surface["evidence_status"] == "release_local_only":
            self.assertIn("rerun_public_release_evidence", surface["repair_types"])

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
            "runtime_closure.validate_officer_request_record",
            "runtime_closure.continuation_quarantine_record",
            "daemon.run_router_daemon",
            "daemon.acquire_lock",
            "daemon.write_status",
            "startup_daemon.heartbeat_monitor",
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

    def test_known_friction_alignment_binds_matrix_and_contract_edges(self) -> None:
        entries = alignment_runner.build_alignment_plan_entries()
        router_entry = next(entry for entry in entries if entry["family"] == "router loop/daemon")
        role_output_entry = next(entry for entry in entries if entry["family"] == "role/output contracts")
        router_obligations = {item.obligation_id for item in router_entry["plan"].obligations}
        role_output_obligations = {item.obligation_id for item in role_output_entry["plan"].obligations}
        router_evidence = {item.evidence_id: item for item in router_entry["plan"].test_evidence}
        role_output_evidence = {item.evidence_id: item for item in role_output_entry["plan"].test_evidence}

        self.assertIn("router_loop.known_friction_regression_gate", router_obligations)
        self.assertIn("router_loop.package_disposition_repair_owned_role_output_replay", router_obligations)
        self.assertIn("router_loop.package_disposition_repair_owned_daemon_replay", router_obligations)
        self.assertIn("router_loop.package_disposition_stale_unowned_role_output_replay", router_obligations)
        self.assertIn("router_loop.package_disposition_stale_unowned_daemon_replay", router_obligations)
        self.assertIn("output_contract.self_check_required_fields", role_output_obligations)
        matrix_item = router_evidence["router_loop.known_friction.happy.matrix"]
        self.assertEqual(matrix_item.path, "tests/test_flowpilot_known_friction_regression_matrix.py")
        self.assertEqual(matrix_item.test_name, "test_known_friction_rows_cover_required_historical_failures")
        known_bad_item = router_evidence["router_loop.known_friction.negative.known_bad"]
        self.assertEqual(known_bad_item.test_name, "test_known_bad_cases_are_rejected")
        replay_item = router_evidence["router_loop.package_disposition_repair_owned_replay.edge.role_output"]
        self.assertEqual(
            replay_item.test_name,
            "test_repair_owned_package_disposition_conflict_replay_is_quarantined_without_daemon_error",
        )
        daemon_item = router_evidence["router_loop.package_disposition_repair_owned_replay.edge.daemon_tick"]
        self.assertEqual(
            daemon_item.test_name,
            "test_daemon_tick_quarantines_repair_owned_package_conflict_without_erasing_wait",
        )
        classifier_item = router_evidence["router_loop.package_disposition_repair_owned_replay.negative.classifier"]
        self.assertEqual(
            classifier_item.test_name,
            "test_pm_package_disposition_conflict_classifier_marks_repair_owned_replay",
        )
        stale_item = router_evidence["router_loop.package_disposition_stale_unowned_replay.edge.role_output"]
        self.assertEqual(
            stale_item.test_name,
            "test_stale_unowned_package_disposition_replay_preserves_canonical_body",
        )
        stale_daemon_item = router_evidence["router_loop.package_disposition_stale_unowned_replay.edge.daemon_tick"]
        self.assertEqual(
            stale_daemon_item.test_name,
            "test_daemon_tick_quarantines_stale_unowned_package_replay_without_reverting_body",
        )
        stale_negative_item = router_evidence["router_loop.package_disposition_stale_unowned_replay.negative.reject_old_body"]
        self.assertEqual(
            stale_negative_item.test_name,
            "test_stale_unowned_package_disposition_replay_preserves_canonical_body",
        )
        stale_daemon_negative_item = router_evidence["router_loop.package_disposition_stale_unowned_replay.negative.no_daemon_error"]
        self.assertEqual(
            stale_daemon_negative_item.test_name,
            "test_daemon_tick_quarantines_stale_unowned_package_replay_without_reverting_body",
        )
        contract_item = role_output_evidence["output_contract.negative.live_worker_missing_fields"]
        self.assertEqual(
            contract_item.test_name,
            "test_contract_self_check_metadata_reports_live_worker_missing_fields",
        )

    def test_repair_transaction_alignment_covers_empty_material_wait(self) -> None:
        entries = alignment_runner.build_alignment_plan_entries()
        repair_entry = next(entry for entry in entries if entry["family"] == "repair transactions")
        obligations = {item.obligation_id for item in repair_entry["plan"].obligations}
        evidence = {item.evidence_id: item for item in repair_entry["plan"].test_evidence}

        self.assertIn("repair_transactions.material_rework_requires_fresh_producer", obligations)
        self.assertIn("repair_transactions.multiround_fake_ai_no_producer_recovery", obligations)
        self.assertIn("repair_transactions.pm_decision_flag_atomicity", obligations)
        item = evidence["repair_transactions.negative.material_role_reissue_no_producer"]
        self.assertEqual(item.test_name, "test_pm_material_repair_rejects_role_reissue_without_fresh_packet_producer")
        self.assertEqual(item.path, "tests/router_runtime/material_modeling.py")
        edge_item = evidence["repair_transactions.edge.pm_decision_side_effect_atomicity"]
        self.assertEqual(
            edge_item.test_name,
            "test_pm_repair_decision_side_effect_exposes_flag_before_wait_events",
        )
        self.assertEqual(edge_item.path, "tests/router_runtime/material_modeling.py")
        e2e_item = evidence["repair_transactions.e2e.no_producer_then_packet_reissue"]
        self.assertEqual(
            e2e_item.test_name,
            "test_e2e_no_producer_pm_repair_then_packet_reissue_exposes_producer_evidence",
        )
        self.assertEqual(e2e_item.path, "tests/test_flowpilot_e2e_synthetic_chaos_replay.py")
        real_router_item = evidence["repair_transactions.real_router.producer_proof_recovery"]
        self.assertEqual(
            real_router_item.test_name,
            "test_real_router_repair_rehearsal_rejects_no_producer_then_accepts_packet_reissue",
        )
        self.assertEqual(real_router_item.path, "tests/test_flowpilot_real_router_dry_run_rehearsal.py")

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
