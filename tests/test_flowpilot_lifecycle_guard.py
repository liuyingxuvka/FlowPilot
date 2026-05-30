from __future__ import annotations

import importlib
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))

flowpilot_new = importlib.import_module("flowpilot_new")
host = importlib.import_module("ai_project_runtime.host")
run_shell = importlib.import_module("ai_project_runtime.run_shell")
runtime = importlib.import_module("ai_project_runtime.runtime")
lifecycle_runner = importlib.import_module("simulations.run_flowpilot_lifecycle_guard_checks")


class FlowPilotLifecycleGuardTests(unittest.TestCase):
    def test_nonterminal_status_blocks_controller_stop_and_persists_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = flowpilot_new.start_run(
                root,
                run_id="run-guard-start",
                headless_startup_text="Exercise lifecycle guard.",
                require_formal_ui=False,
            )

            self.assertFalse(started["lifecycle_guard"]["controller_stop_allowed"])
            self.assertEqual(started["lifecycle_guard"]["next_action"]["action_type"], "lease_agent")
            status = flowpilot_new.status(root)
            guard = status["status"]["lifecycle_guard"]
            self.assertFalse(guard["controller_stop_allowed"])
            self.assertIn(guard["decision"], {"process_next_action", "control_plane_stuck"})
            self.assertFalse(guard["sealed_bodies_visible"])
            duty = status["status"]["foreground_duty"]
            self.assertEqual(duty["action"], "process_next_action")
            self.assertFalse(duty["final_return_preflight"]["allowed"])

            shell = run_shell.load_run_shell(root, run_id="run-guard-start")
            ledger = run_shell.load_run_ledger(shell)
            refreshed = runtime.refresh_lifecycle_guard(ledger, trigger="unit_test")
            self.assertFalse(refreshed["controller_stop_allowed"])
            guard_path = shell.run_root / "lifecycle" / "guard.json"
            duty_path = shell.run_root / "lifecycle" / "foreground_duty.json"
            self.assertTrue(guard_path.exists())
            self.assertTrue(duty_path.exists())

    def test_terminal_fake_e2e_allows_controller_stop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = flowpilot_new.run_fake_e2e(
                root,
                run_id="run-guard-terminal",
                startup_text="Complete a fake project with lifecycle guard.",
            )

            self.assertTrue(result["ok"], result)
            status = flowpilot_new.status(root)
            guard = status["status"]["lifecycle_guard"]
            self.assertEqual(status["next_action"]["action_type"], "terminal_complete")
            self.assertEqual(guard["decision"], "terminal_return")
            self.assertTrue(guard["controller_stop_allowed"])
            duty = status["status"]["foreground_duty"]
            self.assertEqual(duty["action"], "terminal_return")
            self.assertTrue(duty["final_return_preflight"]["allowed"])

    def test_manual_resume_rehydrates_wait_state_from_current_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = flowpilot_new.start_run(
                root,
                run_id="run-guard-resume",
                headless_startup_text="Exercise manual resume.",
                require_formal_ui=False,
            )
            packet_id = started["next_action"]["subject_id"]
            lease_id = flowpilot_new.lease_agent(
                root,
                packet_id=packet_id,
                responsibility="pm",
                agent_id="fake-pm",
                host_kind="fake",
            )["lease_id"]
            flowpilot_new.ack(root, lease_id=lease_id, packet_id=packet_id)

            resumed = flowpilot_new.resume(root, reason="manual_resume_test")
            guard = resumed["lifecycle_guard"]
            self.assertEqual(resumed["next_action"]["action_type"], "wait_for_result")
            self.assertEqual(guard["decision"], "wait_for_result")
            self.assertEqual(guard["resume_source"], "manual_resume_test")
            self.assertEqual(guard["wait_subject"]["packet_id"], packet_id)
            self.assertTrue(guard["wait_subject"]["ack_received"])
            self.assertFalse(guard["controller_stop_allowed"])
            duty = resumed["foreground_duty"]
            self.assertEqual(duty["action"], "wait_patrol")
            self.assertEqual(duty["wait_patrol"]["seconds"], 60)
            self.assertFalse(duty["final_return_preflight"]["allowed"])

    def test_final_preflight_rejects_open_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flowpilot_new.start_run(
                root,
                run_id="run-final-preflight-open-packet",
                headless_startup_text="Exercise final preflight with open packet.",
                require_formal_ui=False,
            )

            preflight = flowpilot_new.final_preflight(root)

            self.assertFalse(preflight["ok"])
            self.assertFalse(preflight["final_return_preflight"]["allowed"])
            self.assertIn("next_action:lease_agent", preflight["final_return_preflight"]["blockers"])
            self.assertEqual(preflight["foreground_duty"]["action"], "process_next_action")

    def test_progress_keeps_slow_live_result_wait_in_patrol(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = flowpilot_new.start_run(
                root,
                run_id="run-progress-grace",
                headless_startup_text="Exercise progress-preserved wait.",
                require_formal_ui=False,
            )
            packet_id = started["next_action"]["subject_id"]
            lease_id = flowpilot_new.lease_agent(
                root,
                packet_id=packet_id,
                responsibility="pm",
                agent_id="fake-pm-progress",
                host_kind="fake",
            )["lease_id"]
            flowpilot_new.ack(root, lease_id=lease_id, packet_id=packet_id)

            shell = run_shell.load_run_shell(root, run_id="run-progress-grace")
            ledger = run_shell.load_run_ledger(shell)
            ledger["lifecycle_guard_config"]["result_liveness_seconds"] = 0
            run_shell.save_run_ledger(shell, ledger, guard_trigger="test_config")

            progress = flowpilot_new.progress(root, lease_id=lease_id, packet_id=packet_id, status="still_working")

            self.assertEqual(progress["next_action"]["action_type"], "wait_for_result")
            self.assertEqual(progress["lifecycle_guard"]["decision"], "wait_for_result")
            self.assertEqual(progress["lifecycle_guard"]["wait_recovery"]["state"], "grace_wait")
            self.assertEqual(progress["foreground_duty"]["action"], "wait_patrol")
            ledger = run_shell.load_run_ledger(shell)
            self.assertEqual(ledger["leases"][lease_id]["progress_count"], 1)
            self.assertEqual(ledger["packets"][packet_id]["status"], "acknowledged")

    def test_liveness_check_due_does_not_replace_without_failure_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = flowpilot_new.start_run(
                root,
                run_id="run-liveness-check-due",
                headless_startup_text="Exercise liveness due without replacement.",
                require_formal_ui=False,
            )
            packet_id = started["next_action"]["subject_id"]
            lease_id = flowpilot_new.lease_agent(
                root,
                packet_id=packet_id,
                responsibility="pm",
                agent_id="fake-pm-liveness",
                host_kind="fake",
            )["lease_id"]
            flowpilot_new.ack(root, lease_id=lease_id, packet_id=packet_id)
            shell = run_shell.load_run_shell(root, run_id="run-liveness-check-due")
            ledger = run_shell.load_run_ledger(shell)
            ledger["lifecycle_guard_config"]["result_liveness_seconds"] = 0
            ledger["leases"][lease_id]["ack_received_at"] = (
                datetime.now(timezone.utc) - timedelta(minutes=15)
            ).isoformat()
            run_shell.save_run_ledger(shell, ledger, guard_trigger="test_old_wait")

            patrol = flowpilot_new.patrol(root)

            self.assertEqual(patrol["lifecycle_guard"]["decision"], "wait_for_result")
            self.assertEqual(patrol["lifecycle_guard"]["wait_recovery"]["state"], "liveness_check_due")
            self.assertFalse(patrol["lifecycle_guard"]["wait_recovery"]["replacement_eligible"])
            self.assertEqual(patrol["foreground_duty"]["action"], "wait_patrol")

    def test_current_liveness_failure_allows_replacement_duty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = flowpilot_new.start_run(
                root,
                run_id="run-liveness-failure",
                headless_startup_text="Exercise liveness failure replacement.",
                require_formal_ui=False,
            )
            packet_id = started["next_action"]["subject_id"]
            lease_id = flowpilot_new.lease_agent(
                root,
                packet_id=packet_id,
                responsibility="pm",
                agent_id="fake-pm-failure",
                host_kind="fake",
            )["lease_id"]
            flowpilot_new.ack(root, lease_id=lease_id, packet_id=packet_id)
            shell = run_shell.load_run_shell(root, run_id="run-liveness-failure")
            ledger = run_shell.load_run_ledger(shell)
            ledger["leases"][lease_id]["liveness_status"] = "timeout_unknown"
            run_shell.save_run_ledger(shell, ledger, guard_trigger="test_liveness_failure")

            patrol = flowpilot_new.patrol(root)

            self.assertEqual(patrol["lifecycle_guard"]["decision"], "reissue_or_replace_lease")
            self.assertTrue(patrol["lifecycle_guard"]["wait_recovery"]["replacement_eligible"])
            self.assertEqual(patrol["foreground_duty"]["action"], "recover_or_reissue")

    def test_accepted_packet_rejects_reassignment_and_ack_regression(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = flowpilot_new.start_run(
                root,
                run_id="run-accepted-hard-gate",
                headless_startup_text="Exercise accepted packet hard gates.",
                require_formal_ui=False,
            )
            packet_id = started["next_action"]["subject_id"]
            lease_id = flowpilot_new.lease_agent(
                root,
                packet_id=packet_id,
                responsibility="pm",
                agent_id="fake-pm-accepted",
                host_kind="fake",
            )["lease_id"]
            flowpilot_new.ack(root, lease_id=lease_id, packet_id=packet_id)
            flowpilot_new.submit_result(root, lease_id=lease_id, packet_id=packet_id, body="SEALED_RESULT_BODY: PM")
            shell = run_shell.load_run_shell(root, run_id="run-accepted-hard-gate")
            ledger = run_shell.load_run_ledger(shell)
            packet = ledger["packets"][packet_id]
            packet["status"] = "accepted"
            packet["accepted_result_id"] = packet["result_ids"][-1]
            run_shell.save_run_ledger(shell, ledger, guard_trigger="test_accept")

            with self.assertRaisesRegex(Exception, "cannot assign accepted packet"):
                flowpilot_new.lease_agent(
                    root,
                    packet_id=packet_id,
                    responsibility="pm",
                    agent_id="fake-replacement",
                    host_kind="fake",
                )
            with self.assertRaisesRegex(Exception, "cannot ACK an accepted packet"):
                flowpilot_new.ack(root, lease_id=lease_id, packet_id=packet_id)

            ledger = run_shell.load_run_ledger(shell)
            self.assertEqual(ledger["packets"][packet_id]["status"], "accepted")

    def test_repair_accepted_packet_assignment_race_restores_original_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = flowpilot_new.start_run(
                root,
                run_id="run-accepted-race-repair",
                headless_startup_text="Exercise accepted race repair.",
                require_formal_ui=False,
            )
            packet_id = started["next_action"]["subject_id"]
            original_lease = flowpilot_new.lease_agent(
                root,
                packet_id=packet_id,
                responsibility="pm",
                agent_id="fake-pm-original",
                host_kind="fake",
            )["lease_id"]
            flowpilot_new.ack(root, lease_id=original_lease, packet_id=packet_id)
            result_id = flowpilot_new.submit_result(
                root,
                lease_id=original_lease,
                packet_id=packet_id,
                body="SEALED_RESULT_BODY: PM",
            )["result_id"]
            shell = run_shell.load_run_shell(root, run_id="run-accepted-race-repair")
            ledger = run_shell.load_run_ledger(shell)
            replacement_lease = runtime.lease_agent(
                ledger,
                "pm",
                agent_id="fake-pm-replacement",
                packet_id=packet_id,
            )
            ledger["packets"][packet_id]["status"] = "acknowledged"
            ledger["packets"][packet_id]["accepted_result_id"] = result_id
            ledger["packets"][packet_id]["assigned_lease_id"] = replacement_lease
            ledger["leases"][replacement_lease]["ack_received"] = True
            run_shell.save_run_ledger(shell, ledger, guard_trigger="test_race")

            before = flowpilot_new.status(root)
            self.assertEqual(before["next_action"]["action_type"], "repair_accepted_packet")
            self.assertEqual(before["lifecycle_guard"]["decision"], "repair_assignment_race")

            repaired = flowpilot_new.repair_accepted_packet(root, packet_id=packet_id)

            self.assertEqual(repaired["repair"]["closed_replacement_lease_ids"], [replacement_lease])
            self.assertNotEqual(repaired["next_action"]["subject_id"], packet_id)
            self.assertEqual(repaired["next_action"]["action_type"], "lease_agent")
            ledger = run_shell.load_run_ledger(shell)
            self.assertEqual(ledger["packets"][packet_id]["status"], "accepted")
            self.assertEqual(ledger["packets"][packet_id]["accepted_result_id"], result_id)
            self.assertEqual(ledger["packets"][packet_id]["assigned_lease_id"], original_lease)
            self.assertEqual(ledger["leases"][replacement_lease]["status"], "closed")

    def test_patrol_classifies_repeated_nonterminal_action_as_stuck(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flowpilot_new.start_run(
                root,
                run_id="run-guard-stuck",
                headless_startup_text="Exercise repeated action patrol.",
                require_formal_ui=False,
            )

            first = flowpilot_new.patrol(root)
            second = flowpilot_new.patrol(root)
            third = flowpilot_new.patrol(root)
            shell = run_shell.load_run_shell(root, run_id="run-guard-stuck")
            ledger = run_shell.load_run_ledger(shell)
            refreshed = runtime.refresh_lifecycle_guard(ledger, trigger="patrol")

            self.assertFalse(first["lifecycle_guard"]["controller_stop_allowed"])
            self.assertFalse(second["lifecycle_guard"]["controller_stop_allowed"])
            self.assertEqual(third["lifecycle_guard"]["decision"], "control_plane_stuck")
            self.assertEqual(refreshed["decision"], "control_plane_stuck")
            self.assertGreaterEqual(third["lifecycle_guard"]["repeated_count"], 3)

    def test_inactive_lease_result_is_quarantined_by_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = flowpilot_new.start_run(
                root,
                run_id="run-guard-inactive-result",
                headless_startup_text="Exercise inactive lease result.",
                require_formal_ui=False,
            )
            packet_id = started["next_action"]["subject_id"]
            lease_id = flowpilot_new.lease_agent(
                root,
                packet_id=packet_id,
                responsibility="pm",
                agent_id="fake-pm",
                host_kind="fake",
            )["lease_id"]
            flowpilot_new.ack(root, lease_id=lease_id, packet_id=packet_id)

            shell = run_shell.load_run_shell(root, run_id="run-guard-inactive-result")
            ledger = run_shell.load_run_ledger(shell)
            runtime.expire_lease(ledger, lease_id, "test_inactive")
            run_shell.save_run_ledger(shell, ledger, guard_trigger="test_expire")

            result = flowpilot_new.submit_result(
                root,
                lease_id=lease_id,
                packet_id=packet_id,
                body="SEALED_RESULT_BODY: late inactive lease result",
            )
            self.assertEqual(result["next_action"]["action_type"], "repair_packet")
            self.assertEqual(result["lifecycle_guard"]["decision"], "quarantine_stale_result")
            self.assertIn("closed_or_inactive_lease", result["lifecycle_guard"]["reason"])

    def test_late_result_after_route_mutation_stays_quarantined(self) -> None:
        ledger = runtime.new_ledger("Build", "Finish")
        ledger["startup_intake"] = {"sealed": True}
        runtime.create_route(ledger, "route one", ["one"])
        packet_id = runtime.issue_task_packet(ledger, "worker", "Do work", "sealed body")
        lease_id = host.lease_responsibility(
            ledger,
            "worker",
            host_kind="fake",
            agent_id="fake-worker",
            packet_id=packet_id,
            scope="test",
        )
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)
        runtime.create_route(ledger, "route two", ["two"])

        result_id = host.submit_host_result(ledger, lease_id, packet_id, "SEALED_RESULT_BODY: late")
        result = ledger["results"][result_id]

        self.assertEqual(ledger["packets"][packet_id]["status"], "quarantined_after_route_mutation")
        self.assertTrue(result["quarantined"])
        self.assertIn("quarantined_packet", result["mechanical_blockers"])
        self.assertIn("stale_route_version", result["mechanical_blockers"])

    def test_flowguard_lifecycle_model_is_green_and_catches_hazards(self) -> None:
        result = lifecycle_runner.run_checks()
        self.assertTrue(result["ok"], result)
        hazards = result["hazard_detection"]["hazards"]
        for expected in (
            "nonterminal_stop_allowed",
            "ack_only_terminal",
            "inactive_lease_waits_forever",
            "stale_result_accepted",
            "repeated_action_ignored",
        ):
            self.assertIn(expected, hazards)


if __name__ == "__main__":
    unittest.main()
