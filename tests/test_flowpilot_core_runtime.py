from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_core_runtime"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    old_module = sys.modules.get(name)
    sys.modules[name] = module
    sys.path.insert(0, str(path.parent))
    sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
        if old_module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old_module
    return module


runtime = load_module("flowpilot_core_runtime_under_test", RUNTIME_ROOT / "runtime.py")
runtime_runner = load_module(
    "flowpilot_core_runtime_runner_under_test",
    ROOT / "simulations" / "run_flowpilot_core_runtime_checks.py",
)
development_runner = load_module(
    "flowpilot_core_runtime_development_runner_under_test",
    ROOT / "simulations" / "run_flowpilot_core_runtime_development_checks.py",
)
control_plane_duty_runner = load_module(
    "flowpilot_new_control_plane_duty_runner_under_test",
    ROOT / "simulations" / "run_flowpilot_new_control_plane_duty_checks.py",
)
control_plane_audit = load_module(
    "flowpilot_control_plane_friction_model_audit_under_test",
    ROOT / "simulations" / "flowpilot_control_plane_friction_model_audit.py",
)
control_surface = runtime.control_surface


class FlowPilotCoreRuntimeTests(unittest.TestCase):
    def test_runtime_assets_exist_and_document_boundaries(self) -> None:
        runtime_files = {path.name for path in RUNTIME_ROOT.iterdir() if path.is_file()}
        for required_file in {
            "__init__.py",
            "README.md",
            "runtime.py",
            "cli.py",
            "run_shell.py",
            "host.py",
            "router.py",
            "packets.py",
            "flowguard_orders.py",
            "review_closure.py",
            "cockpit.py",
            "migration.py",
        }:
            with self.subTest(required_file=required_file):
                self.assertIn(required_file, runtime_files)
        readme = (RUNTIME_ROOT / "README.md").read_text(encoding="utf-8")
        for phrase in (
            "The ledger is the truth",
            "ACK and progress are liveness only",
            "FlowGuard work orders must name the modeled target",
            "Non-authoritative inputs include prior runtime state",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, readme)

    def test_replacement_worker_can_finish_but_closed_worker_late_output_is_blocked(self) -> None:
        report = runtime_runner.replacement_worker_success()
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["accepted"])
        self.assertIn("closed_or_inactive_lease", report["details"]["late_result_blockers"])

    def test_wrong_flowguard_target_self_review_stale_route_and_stale_evidence_block(self) -> None:
        for scenario_name in (
            "wrong_flowguard_target_blocks",
            "self_review_blocks",
            "stale_route_output_blocks",
            "stale_evidence_blocks",
        ):
            with self.subTest(scenario=scenario_name):
                report = runtime_runner.SCENARIOS[scenario_name]()
                self.assertTrue(report["ok"], report)
                self.assertFalse(report["accepted"])

    def test_ack_and_progress_do_not_complete_packet(self) -> None:
        report = runtime_runner.ack_only_timeout_stays_incomplete()
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["details"]["before_timeout"]["action_type"], "wait_for_result")
        self.assertEqual(report["details"]["after_timeout"]["action_type"], "replace_lease")

    def test_public_console_hides_sealed_bodies(self) -> None:
        report = runtime_runner.console_does_not_leak_sealed_bodies()
        self.assertTrue(report["ok"], report)
        self.assertFalse(report["details"]["leaked"])
        rendered = json.dumps(report, sort_keys=True)
        self.assertNotIn("SEALED_TASK_BODY", rendered)
        self.assertNotIn("SEALED_RESULT_BODY", rendered)

    def test_router_closes_only_after_backward_chain_and_validation(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime_runner._complete_happy_path(ledger, packet_id, worker)

        self.assertEqual(ledger["closure"]["decision"], "complete")
        self.assertEqual(runtime.router_next_action(ledger).action_type, "terminal_complete")
        chain = ledger["closure"]["backward_chain"]
        self.assertEqual([item["packet_kind"] for item in chain if item["kind"] == "packet"], [
            "task",
            "flowguard_check",
            "review",
        ])
        self.assertTrue(ledger["system_closures"])
        self.assertFalse([lease for lease in ledger["leases"].values() if lease["status"] == "active"])

    def test_runtime_testmesh_does_not_overclaim_release_evidence(self) -> None:
        report = runtime_runner.run_checks()
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["test_mesh"]["parent_gates"]["routine_runtime_gate"]["ok"])
        self.assertFalse(report["test_mesh"]["parent_gates"]["release_runtime_gate"]["ok"])
        rows = {row["id"]: row for row in report["test_mesh"]["rows"]}
        self.assertEqual(rows["background_meta_capability"]["status"], "not_run")
        self.assertEqual(rows["install_surface_parity"]["status"], "not_run")

    def test_flowguard_development_model_accepts_order_and_rejects_hazards(self) -> None:
        report = development_runner.run_checks()
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["flowguard"]["ok"])
        self.assertTrue(report["target_plan"]["ok"])
        self.assertTrue(report["hazard_detection"]["ok"])
        self.assertIn("fixed_role_topology_reintroduced", report["hazard_detection"]["hazards"])

    def test_flowguard_control_plane_duty_model_matches_runtime_repairs(self) -> None:
        report = control_plane_duty_runner.run_checks()
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["flowguard"]["ok"])
        self.assertTrue(report["source_contract"]["ok"])
        self.assertIn("status_mutates_ledger", report["hazard_detection"]["hazards"])

    def test_current_run_resolver_accepts_new_schema_and_rejects_project_root_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / ".flowpilot" / "runs" / "run-new"
            run_root.mkdir(parents=True)
            ledger_path = run_root / "ledger.json"
            ledger_path.write_text("{}\n", encoding="utf-8")
            current_path = root / ".flowpilot" / "current.json"
            current_path.write_text(
                json.dumps(
                    {
                        "schema_version": "black_box_flowpilot_run_shell.v1",
                        "authority": "current_run_ledger",
                        "run_id": "run-new",
                        "run_root": str(run_root),
                        "ledger_path": str(ledger_path),
                    }
                ),
                encoding="utf-8",
            )

            resolution = control_surface.resolve_current_run(root)

            self.assertTrue(resolution.ok, resolution)
            self.assertEqual(resolution.run_id, "run-new")
            self.assertEqual(resolution.run_root, run_root.resolve())
            self.assertEqual(resolution.source_fields, ("run_id", "run_root"))

            current_path.write_text(
                json.dumps({"run_id": "run-new", "run_root": "."}),
                encoding="utf-8",
            )
            invalid = control_surface.resolve_current_run(root)

            self.assertFalse(invalid.ok)
            self.assertEqual(invalid.error_code, "invalid_run_root")

    def test_current_run_resolver_missing_pointer_returns_structured_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = control_surface.resolve_current_run(root)

            self.assertFalse(result.ok)
            self.assertEqual(result.error_code, "missing_file")
            finding = result.finding()
            self.assertEqual(finding["code"], "current_run_resolution_failed")
            self.assertIn("current.json", finding["evidence"]["pointer_path"])

    def test_safe_json_read_and_live_audit_report_invalid_utf8_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad_utf8 = root / "bad.json"
            bad_utf8.write_bytes(b"\xff\xfe")
            bad_json = root / "bad-syntax.json"
            bad_json.write_text("{", encoding="utf-8")

            utf8_result = control_surface.safe_read_json(bad_utf8)
            json_result = control_surface.safe_read_json(bad_json)

            self.assertFalse(utf8_result.ok)
            self.assertEqual(utf8_result.error_code, "invalid_utf8")
            self.assertFalse(json_result.ok)
            self.assertEqual(json_result.error_code, "invalid_json")

            run_root = root / ".flowpilot" / "runs" / "run-bad"
            run_root.mkdir(parents=True)
            (root / ".flowpilot" / "current.json").write_text(
                json.dumps({"run_id": "run-bad", "run_root": str(run_root)}),
                encoding="utf-8",
            )
            (run_root / "router_state.json").write_bytes(b"\xff\xfe")
            (run_root / "ledger.json").write_text(
                json.dumps(runtime.new_ledger("Goal", "Contract")),
                encoding="utf-8",
            )

            audit = control_plane_audit.audit_live_run(root)

            self.assertFalse(audit["ok"])
            codes = {finding["code"] for finding in audit["findings"]}
            self.assertIn("control_surface_evidence_unreadable", codes)

    def test_packet_control_surface_contracts_are_role_symmetric(self) -> None:
        required_roles = {
            "pm",
            "worker",
            "flowguard_operator",
            "reviewer",
        }
        ledger = runtime.new_ledger("Goal", "Contract")
        runtime.create_route(ledger, "Route", ["Do work"])
        for role in sorted(required_roles):
            packet_id = runtime.issue_task_packet(
                ledger,
                role,
                f"{role} objective",
                json.dumps({"role": role}),
                packet_kind="flowguard_check" if role == "flowguard_operator" else "task",
            )
            envelope = ledger["packets"][packet_id]["envelope"]
            self.assertEqual(envelope["output_contract"]["recipient_responsibility"], role)

        findings = control_surface.audit_packet_contracts(
            ledger,
            required_responsibilities=required_roles,
        )

        self.assertEqual(findings, [])

        bad_ledger = json.loads(json.dumps(ledger))
        reviewer_packet = next(
            packet
            for packet in bad_ledger["packets"].values()
            if packet["envelope"]["responsibility"] == "reviewer"
        )
        reviewer_packet["envelope"].pop("output_contract")
        bad_findings = control_surface.audit_packet_contracts(
            bad_ledger,
            required_responsibilities=required_roles,
        )

        self.assertIn("packet_contract_fields_missing", {finding["code"] for finding in bad_findings})

    def test_packet_result_contract_separates_ack_result_and_acceptance(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        runtime.create_route(ledger, "Route", ["Do work"])
        packet_id = runtime.issue_task_packet(ledger, "worker", "Do work", "body")
        lease_id = runtime.lease_agent(ledger, "worker", agent_id="worker-1", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)
        self.assertEqual(ledger["packets"][packet_id]["status"], "acknowledged")

        result_id = runtime.submit_result(ledger, lease_id, packet_id, "done")

        packet = ledger["packets"][packet_id]
        result = ledger["results"][result_id]
        self.assertEqual(packet["status"], "result_submitted")
        self.assertEqual(packet["accepted_result_id"], "")
        self.assertTrue(result["envelope"]["ack_result_accepted_separate"])
        self.assertEqual(result["envelope"]["output_contract"]["packet_id"], packet_id)
        self.assertEqual(control_surface.audit_packet_contracts(ledger), [])

    def test_declared_pass_ignores_contextual_failure_words(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)

        result_id = runtime.submit_result(
            ledger,
            worker,
            packet_id,
            "\n".join(
                [
                    "Status: PASS",
                    "The old topology check failed before this repair.",
                    "The report includes function-block rows and blocker history.",
                ]
            ),
        )

        self.assertEqual(ledger["results"][result_id]["semantic_decision"], "pass")
        self.assertEqual(ledger["packets"][packet_id]["status"], "result_submitted")
        self.assertFalse(ledger.get("active_blockers"))
        self.assertTrue([row for row in ledger["packets"].values() if row["envelope"].get("packet_kind") == "flowguard_check"])

    def test_declared_block_line_routes_to_semantic_repair(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)

        result_id = runtime.submit_result(
            ledger,
            worker,
            packet_id,
            "Decision: block\nReason: current evidence is not sufficient.",
        )

        self.assertEqual(ledger["results"][result_id]["semantic_decision"], "block")
        self.assertEqual(ledger["packets"][packet_id]["status"], "result_blocked")
        active = [row for row in ledger["active_blockers"].values() if row["status"] == "active"]
        self.assertEqual(len(active), 1)
        action = runtime.router_next_action(ledger)
        self.assertEqual(action.action_type, "lease_agent")
        self.assertEqual(action.responsibility, "pm")

    def test_run_until_wait_folds_internal_action_to_role_boundary(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        ledger["startup_intake"] = {"sealed": True}
        runtime.create_route(ledger, "Route", ["Do work"])

        boundary = runtime.run_until_wait(ledger)

        self.assertEqual(boundary["boundary_class"], "role_dispatch")
        self.assertEqual(boundary["next_action"]["action_type"], "lease_agent")
        self.assertEqual(boundary["folded_applied_count"], 1)
        self.assertEqual(boundary["folded_applied_actions"][0]["action_type"], "issue_task_packet")

    def test_pm_repair_decision_ignores_hostile_prose_when_structured_decision_is_present(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(
            ledger,
            worker,
            packet_id,
            json.dumps({"decision": "block", "blocking": True, "recommended_resolution": "needs repair"}),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-a", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet)

        runtime.submit_result(
            ledger,
            pm_lease,
            pm_packet,
            "decision=same_node_repair\nReason: this prose mentions stop_for_user and block, but they are not the decision.",
        )

        decision = next(iter(ledger["pm_repair_decisions"].values()))
        self.assertEqual(decision["decision"], "same_node_repair")
        self.assertEqual(ledger["active_blockers"][blocker_id]["status"], "awaiting_recheck")

    def test_pm_repair_decision_requires_structured_field_and_stop_pauses_route(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(
            ledger,
            worker,
            packet_id,
            json.dumps({"decision": "block", "blocking": True, "recommended_resolution": "needs PM"}),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        bad_pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-bad", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, bad_pm_lease)
        runtime.ack_lease(ledger, bad_pm_lease, pm_packet)

        bad_result = runtime.submit_result(
            ledger,
            bad_pm_lease,
            pm_packet,
            "This body says block and stop_for_user, but it has no structured decision field.",
        )

        self.assertEqual(ledger["results"][bad_result]["status"], "pm_repair_decision_blocked")
        self.assertFalse(ledger["pm_repair_decisions"])

        ledger["packets"][pm_packet]["status"] = "open"
        ledger["packets"][pm_packet]["assigned_lease_id"] = ""
        good_pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-good", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, good_pm_lease)
        runtime.ack_lease(ledger, good_pm_lease, pm_packet)
        runtime.submit_result(ledger, good_pm_lease, pm_packet, json.dumps({"decision": "stop_for_user"}))

        self.assertEqual(ledger["active_blockers"][blocker_id]["status"], "stopped")
        self.assertEqual(runtime.router_next_action(ledger).action_type, "wait_for_resume")


if __name__ == "__main__":
    unittest.main()
