from __future__ import annotations

import contextlib
import io
import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))

flowpilot_new = importlib.import_module("flowpilot_new")
run_shell = importlib.import_module("flowpilot_core_runtime.run_shell")
entrypoint_runner = importlib.import_module("simulations.run_flowpilot_new_entrypoint_checks")


class FlowPilotNewEntrypointTests(unittest.TestCase):
    def _complete_open_packet(
        self,
        root: Path,
        *,
        packet_id: str,
        responsibility: str,
        agent_id: str,
        body: str,
    ) -> tuple[str, str]:
        lease_id = flowpilot_new.lease_agent(
            root,
            packet_id=packet_id,
            responsibility=responsibility,
            agent_id=agent_id,
            host_kind="fake",
        )["lease_id"]
        flowpilot_new.ack(root, lease_id=lease_id, packet_id=packet_id)
        result_id = flowpilot_new.submit_result(
            root,
            lease_id=lease_id,
            packet_id=packet_id,
            body=body,
        )["result_id"]
        return lease_id, result_id

    def _open_packet_by_kind(self, ledger: dict[str, object], packet_kind: str) -> str:
        packets = ledger["packets"]
        self.assertIsInstance(packets, dict)
        for packet_id, packet in packets.items():
            self.assertIsInstance(packet, dict)
            envelope = packet["envelope"]
            self.assertIsInstance(envelope, dict)
            if envelope.get("packet_kind", "task") == packet_kind and packet.get("status") == "open":
                return str(packet_id)
        self.fail(f"missing open {packet_kind} packet")

    def test_start_rehearsal_reuses_old_startup_ui_and_enters_new_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = flowpilot_new.start_run(
                root,
                run_id="run-new-entry",
                headless_startup_text="Build a tiny project through new FlowPilot.",
                require_formal_ui=False,
            )

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["mode"], "rehearsal")
            self.assertEqual(result["next_action"]["action_type"], "lease_agent")
            self.assertEqual(result["next_action"]["responsibility"], "pm")
            shell = run_shell.load_run_shell(root, run_id="run-new-entry")
            ledger = run_shell.load_run_ledger(shell)
            self.assertTrue(ledger["startup_intake"]["current_run_authority"])
            self.assertTrue(ledger["contract_frozen"])
            self.assertEqual(ledger["active_route_version"], 1)
            self.assertEqual(len(ledger["packets"]), 1)
            packet = next(iter(ledger["packets"].values()))
            self.assertEqual(packet["envelope"]["responsibility"], "pm")
            rendered = json.dumps(result["status"], sort_keys=True)
            self.assertNotIn("Build a tiny project through new FlowPilot.", rendered)
            self.assertIn("flowpilot_startup_intake.ps1", " ".join(flowpilot_new.startup_ui_command(root, "run-new-entry")[0]))

    def test_fake_end_to_end_rehearsal_reaches_final_closure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = flowpilot_new.run_fake_e2e(
                root,
                run_id="run-e2e",
                startup_text="Build and validate a toy command.",
            )

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["closure"]["decision"], "complete")
            self.assertEqual(result["next_action"]["action_type"], "terminal_complete")
            shell = run_shell.load_run_shell(root, run_id="run-e2e")
            ledger = run_shell.load_run_ledger(shell)
            self.assertEqual(next(iter(ledger["reviews"].values()))["decision"], "accept")
            self.assertEqual(next(iter(ledger["flowguard_work_orders"].values()))["modeled_target"], "development_process")
            packet_kinds = [packet["envelope"].get("packet_kind", "task") for packet in ledger["packets"].values()]
            route_scopes = [packet["envelope"].get("route_scope", "") for packet in ledger["packets"].values()]
            for expected_scope in (
                "high_standard_contract",
                "discovery",
                "skill_standard",
                "planning",
                "node_acceptance_plan",
                "node",
                "node_pm_disposition",
            ):
                self.assertIn(expected_scope, route_scopes)
            for expected_kind in ("flowguard_check", "review", "pm_disposition"):
                self.assertIn(expected_kind, packet_kinds)
            self.assertNotIn("validation", packet_kinds)
            self.assertNotIn("closure", packet_kinds)
            self.assertTrue(ledger["system_closures"])
            self.assertEqual(packet_kinds.count("pm_disposition"), len(result["accepted_node_ids"]))
            self.assertEqual(len(ledger["node_acceptance_plans"]), len(result["accepted_node_ids"]))
            self.assertTrue(result["folded_boundaries"])
            self.assertTrue(all(boundary["command"] == "run-until-wait" for boundary in result["folded_boundaries"]))
            self.assertFalse(
                [
                    boundary
                    for boundary in result["folded_boundaries"]
                    if boundary["boundary_class"] not in {"role_dispatch", "terminal"}
                ]
            )
            self.assertEqual(ledger["final_requirement_evidence_matrix"]["status"], "clean")
            self.assertTrue(all(lease["status"] == "closed" for lease in ledger["leases"].values()))
            self.assertTrue(all(lease["ack_received"] for lease in ledger["leases"].values()))
            self.assertTrue(all(lease["packet_id"] for lease in ledger["leases"].values()))
            status = json.loads((shell.run_root / "console" / "status.json").read_text(encoding="utf-8"))
            self.assertFalse(status["sealed_bodies_visible"])
            self.assertFalse([lease for lease in status["leases"] if lease["status"] == "active"])

    def test_ack_only_and_pm_only_result_do_not_reach_terminal_closure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flowpilot_new.start_run(
                root,
                run_id="run-no-shortcut",
                headless_startup_text="Exercise no-shortcut closure.",
                require_formal_ui=False,
            )
            shell = run_shell.load_run_shell(root, run_id="run-no-shortcut")
            ledger = run_shell.load_run_ledger(shell)
            pm_packet = next(iter(ledger["packets"]))
            pm_lease = flowpilot_new.lease_agent(
                root,
                packet_id=pm_packet,
                responsibility="pm",
                agent_id="pm-agent",
                host_kind="fake",
            )["lease_id"]
            flowpilot_new.ack(root, lease_id=pm_lease, packet_id=pm_packet)

            ack_only_status = flowpilot_new.status(root)
            self.assertEqual(ack_only_status["next_action"]["action_type"], "wait_for_result")
            self.assertEqual(ack_only_status["status"]["closure"]["decision"], "not_attempted")

            after_pm = flowpilot_new.submit_result(
                root,
                lease_id=pm_lease,
                packet_id=pm_packet,
                body="SEALED_RESULT_BODY: PM result is not enough for closure.",
            )
            self.assertEqual(after_pm["next_action"]["action_type"], "lease_agent")
            self.assertEqual(after_pm["next_action"]["responsibility"], "flowguard_operator")
            self.assertNotEqual(after_pm["next_action"]["action_type"], "terminal_complete")
            after_pm_status = flowpilot_new.status(root)
            self.assertEqual(after_pm_status["status"]["closure"]["decision"], "not_attempted")
            ledger = run_shell.load_run_ledger(shell)
            self.assertEqual(ledger["packets"][pm_packet]["status"], "result_submitted")
            flowguard_packet = self._open_packet_by_kind(ledger, "flowguard_check")
            self.assertEqual(flowguard_packet, after_pm["next_action"]["subject_id"])
            flowguard_body = json.loads(ledger["packets"][flowguard_packet]["body"])
            policy = flowguard_body["evidence_output_policy"]
            self.assertIn(f"/evidence/flowguard/{flowguard_packet}", policy["run_local_evidence_root"])
            self.assertTrue(policy["required_for_formal_run"])
            self.assertIn("simulations/meta_thin_parent_results.json", policy["tracked_baseline_paths_forbidden_unless_explicit_baseline_update"])
            self.assertNotIn("recommended_runner_commands", flowguard_body)
            self.assertIn("select or create suitable FlowGuard evidence", flowguard_body["instruction"])

    def test_flowguard_operator_is_leased_through_its_own_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flowpilot_new.start_run(
                root,
                run_id="run-symmetric",
                headless_startup_text="Exercise symmetric packet flow.",
                require_formal_ui=False,
            )
            shell = run_shell.load_run_shell(root, run_id="run-symmetric")
            ledger = run_shell.load_run_ledger(shell)
            pm_packet = next(iter(ledger["packets"]))

            with self.assertRaisesRegex(Exception, "lease responsibility does not match packet"):
                flowpilot_new.lease_agent(
                    root,
                    packet_id=pm_packet,
                    responsibility="flowguard_operator",
                    agent_id="bad-flowguard",
                    host_kind="fake",
                )

            pm_lease = flowpilot_new.lease_agent(
                root,
                packet_id=pm_packet,
                responsibility="pm",
                agent_id="pm-agent",
                host_kind="fake",
            )["lease_id"]
            flowpilot_new.ack(root, lease_id=pm_lease, packet_id=pm_packet)
            after_pm = flowpilot_new.submit_result(
                root,
                lease_id=pm_lease,
                packet_id=pm_packet,
                body="SEALED_RESULT_BODY: PM result",
            )

            self.assertEqual(after_pm["next_action"]["action_type"], "lease_agent")
            self.assertEqual(after_pm["next_action"]["responsibility"], "flowguard_operator")
            flowguard_packet = after_pm["next_action"]["subject_id"]
            ledger = run_shell.load_run_ledger(shell)
            flowguard_body = json.loads(ledger["packets"][flowguard_packet]["body"])
            self.assertIn(f"/evidence/flowguard/{flowguard_packet}", flowguard_body["evidence_output_policy"]["run_local_evidence_root"])
            self.assertNotIn("recommended_runner_commands", flowguard_body)
            self.assertIn("select or create suitable FlowGuard evidence", flowguard_body["instruction"])
            flowguard_lease = flowpilot_new.lease_agent(
                root,
                packet_id=flowguard_packet,
                responsibility="flowguard_operator",
                agent_id="flowguard-agent",
                host_kind="fake",
            )["lease_id"]
            flowpilot_new.ack(root, lease_id=flowguard_lease, packet_id=flowguard_packet)
            flowpilot_new.submit_result(
                root,
                lease_id=flowguard_lease,
                packet_id=flowguard_packet,
                body="SEALED_RESULT_BODY: FlowGuard result",
            )

            ledger = run_shell.load_run_ledger(shell)
            self.assertEqual(ledger["packets"][flowguard_packet]["envelope"]["packet_kind"], "flowguard_check")
            self.assertEqual(ledger["packets"][flowguard_packet]["status"], "accepted")
            self.assertEqual(ledger["leases"][flowguard_lease]["status"], "closed")
            reviewer_packets = [
                packet for packet in ledger["packets"].values() if packet["envelope"].get("packet_kind") == "review"
            ]
            self.assertEqual(len(reviewer_packets), 1)

    def test_reviewer_packet_lease_projection_is_clean_before_and_after_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flowpilot_new.start_run(
                root,
                run_id="run-reviewer-clean",
                headless_startup_text="Exercise reviewer lease cleanliness.",
                require_formal_ui=False,
            )
            shell = run_shell.load_run_shell(root, run_id="run-reviewer-clean")
            ledger = run_shell.load_run_ledger(shell)
            pm_packet = next(iter(ledger["packets"]))
            self._complete_open_packet(
                root,
                packet_id=pm_packet,
                responsibility="pm",
                agent_id="pm-agent",
                body="SEALED_RESULT_BODY: PM result",
            )
            ledger = run_shell.load_run_ledger(shell)
            flowguard_packet = self._open_packet_by_kind(ledger, "flowguard_check")
            self._complete_open_packet(
                root,
                packet_id=flowguard_packet,
                responsibility="flowguard_operator",
                agent_id="flowguard-agent",
                body="SEALED_RESULT_BODY: FlowGuard result",
            )
            ledger = run_shell.load_run_ledger(shell)
            review_packet = self._open_packet_by_kind(ledger, "review")
            reviewer_lease = flowpilot_new.lease_agent(
                root,
                packet_id=review_packet,
                responsibility="reviewer",
                agent_id="reviewer-agent",
                host_kind="fake",
            )["lease_id"]

            before_ack = flowpilot_new.status(root)["status"]
            reviewer_rows = [row for row in before_ack["leases"] if row["lease_id"] == reviewer_lease]
            self.assertEqual(len(reviewer_rows), 1)
            self.assertEqual(reviewer_rows[0]["lease_id"], reviewer_lease)
            self.assertEqual(reviewer_rows[0]["agent_id"], "reviewer-agent")
            self.assertEqual(reviewer_rows[0]["responsibility"], "reviewer")
            self.assertEqual(reviewer_rows[0]["status"], "active")
            self.assertFalse(reviewer_rows[0]["ack_received"])
            self.assertEqual(reviewer_rows[0]["packet_id"], review_packet)

            flowpilot_new.ack(root, lease_id=reviewer_lease, packet_id=review_packet)
            after_ack = flowpilot_new.status(root)["status"]
            reviewer_rows = [row for row in after_ack["leases"] if row["lease_id"] == reviewer_lease]
            self.assertEqual(reviewer_rows[0]["packet_id"], review_packet)
            self.assertTrue(reviewer_rows[0]["ack_received"])

            flowpilot_new.submit_result(
                root,
                lease_id=reviewer_lease,
                packet_id=review_packet,
                body="SEALED_RESULT_BODY: Reviewer accepted the FlowGuard-backed result.",
            )
            after_review = flowpilot_new.status(root)["status"]
            self.assertFalse(
                [
                    row
                    for row in after_review["leases"]
                    if row["responsibility"] == "reviewer" and row["status"] == "active"
                ]
            )
            ledger = run_shell.load_run_ledger(shell)
            self.assertEqual(ledger["packets"][review_packet]["status"], "accepted")
            self.assertEqual(ledger["leases"][reviewer_lease]["status"], "closed")
            self.assertTrue(ledger["leases"][reviewer_lease]["ack_received"])
            packet_kinds = [packet["envelope"].get("packet_kind", "task") for packet in ledger["packets"].values()]
            self.assertNotIn("validation", packet_kinds)
            self.assertNotIn("closure", packet_kinds)
            self.assertTrue(ledger["system_closures"])
            self.assertNotEqual(after_review["next_action"].get("responsibility"), "validator")

    def test_status_is_read_only_but_patrol_refreshes_current_run_duty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flowpilot_new.start_run(
                root,
                run_id="run-status-readonly",
                headless_startup_text="Exercise status read-only behavior.",
                require_formal_ui=False,
            )
            shell = run_shell.load_run_shell(root, run_id="run-status-readonly")
            before = run_shell.load_run_ledger(shell)
            before_history = len(before.get("lifecycle_guard_history") or [])
            before_events = len(before.get("events") or [])

            flowpilot_new.status(root)
            flowpilot_new.status(root)
            after_status = run_shell.load_run_ledger(shell)

            self.assertEqual(len(after_status.get("lifecycle_guard_history") or []), before_history)
            self.assertEqual(len(after_status.get("events") or []), before_events)

            flowpilot_new.patrol(root, sleep_seconds=0)
            after_patrol = run_shell.load_run_ledger(shell)
            self.assertGreater(len(after_patrol.get("lifecycle_guard_history") or []), before_history)

    def test_formal_public_surface_omits_unsupported_side_command_paths(self) -> None:
        unsupported_functions = ("complete_flowguard", "review", "record_validation", "close")
        for name in unsupported_functions:
            self.assertFalse(hasattr(flowpilot_new, name), name)

        direct_help = io.StringIO()
        with self.assertRaises(SystemExit) as help_exit:
            with contextlib.redirect_stdout(direct_help):
                flowpilot_new.main(["--help"])
        self.assertEqual(help_exit.exception.code, 0)
        self.assertIn("run-until-wait", direct_help.getvalue())
        self.assertIn("repair-accepted-packet", direct_help.getvalue())

        direct_error = io.StringIO()
        with self.assertRaises(SystemExit) as error_exit:
            with contextlib.redirect_stderr(direct_error):
                flowpilot_new.main(["complete-flowguard"])
        self.assertEqual(error_exit.exception.code, 2)
        self.assertIn("invalid choice", direct_error.getvalue())

        completed = subprocess.run(
            [sys.executable, str(ASSETS / "flowpilot_new.py"), "--help"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("run-until-wait", completed.stdout)
        self.assertIn("repair-accepted-packet", completed.stdout)
        for command in ("complete-flowguard", "record-validation"):
            self.assertNotIn(command, completed.stdout)

        lease_help = subprocess.run(
            [sys.executable, str(ASSETS / "flowpilot_new.py"), "lease-agent", "--help"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(lease_help.returncode, 0, lease_help.stderr)
        self.assertIn("{live,fake,dry_run}", lease_help.stdout)
        self.assertIn("live=real host-supported role surface", lease_help.stdout)
        self.assertIn("role surface", lease_help.stdout)
        self.assertIn("Do not invent values outside", lease_help.stdout)
        self.assertIn("this menu", lease_help.stdout)

        rejected = subprocess.run(
            [sys.executable, str(ASSETS / "flowpilot_new.py"), "--root", str(Path.cwd()), "complete-flowguard"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("invalid choice", rejected.stderr)

    def test_invalid_host_kind_is_rejected_instead_of_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flowpilot_new.start_run(
                root,
                run_id="run-host-kind-reject",
                headless_startup_text="Exercise host kind rejection.",
                require_formal_ui=False,
            )
            shell = run_shell.load_run_shell(root, run_id="run-host-kind-reject")
            ledger = run_shell.load_run_ledger(shell)
            packet_id = next(iter(ledger["packets"]))

            rejected = subprocess.run(
                [
                    sys.executable,
                    str(ASSETS / "flowpilot_new.py"),
                    "--root",
                    str(root),
                    "lease-agent",
                    "--packet-id",
                    packet_id,
                    "--responsibility",
                    "pm",
                    "--agent-id",
                    "agent-1",
                    "--host-kind",
                    "codex_background_worker",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("invalid choice", rejected.stderr)

            direct_error = io.StringIO()
            with self.assertRaises(SystemExit) as direct_exit:
                with contextlib.redirect_stderr(direct_error):
                    flowpilot_new.main(
                        [
                            "--root",
                            str(root),
                            "lease-agent",
                            "--packet-id",
                            packet_id,
                            "--responsibility",
                            "pm",
                            "--agent-id",
                            "agent-1",
                            "--host-kind",
                            "codex_background_worker",
                        ]
                    )
            self.assertEqual(direct_exit.exception.code, 2)
            self.assertIn("invalid choice", direct_error.getvalue())

    def test_formal_mode_rejects_headless_startup_result_as_formal_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            command_result = flowpilot_new.start_run(
                root,
                run_id="run-formal-source",
                headless_startup_text="Headless text should stay rehearsal-only.",
                require_formal_ui=False,
            )
            result_path = Path(command_result["run"]["run_root"]) / "startup_intake" / "startup_intake_result.json"
            with self.assertRaisesRegex(Exception, "formal FlowPilot startup requires"):
                flowpilot_new._assert_formal_interactive_result(result_path)

    def test_flowguard_new_entrypoint_model_is_green_and_catches_hazards(self) -> None:
        result = entrypoint_runner.run_checks()
        self.assertTrue(result["ok"], result)
        self.assertIn("old_router_authority", result["hazard_detection"]["hazards"])
        self.assertIn("monitor_ui_required", result["hazard_detection"]["hazards"])
        self.assertIn("headless_formal_overclaim", result["hazard_detection"]["hazards"])
        self.assertIn("missing_host_kind_menu", result["hazard_detection"]["hazards"])
        self.assertIn("invented_host_kind_value", result["hazard_detection"]["hazards"])
        self.assertIn("active_prompt_historical_role_topology_residue", result["hazard_detection"]["hazards"])
        self.assertIn("tracked_baseline_flowguard_evidence", result["hazard_detection"]["hazards"])
        self.assertIn("nonterminal_stop_allowed", result["hazard_detection"]["hazards"])
        self.assertIn("terminal_without_lifecycle_guard", result["hazard_detection"]["hazards"])
        self.assertTrue(result["target_plan"]["state"]["host_kind_value_menu_presented"])
        self.assertTrue(result["target_plan"]["state"]["flowguard_evidence_run_local"])
        self.assertTrue(result["target_plan"]["state"]["terminal_controller_stop_allowed"])


if __name__ == "__main__":
    unittest.main()
