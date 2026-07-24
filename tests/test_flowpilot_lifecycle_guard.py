from __future__ import annotations

import importlib
import json
import sys
import tempfile
import unittest
from unittest import mock
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))

flowpilot_new = importlib.import_module("flowpilot_new")
host = importlib.import_module("flowpilot_core_runtime.host")
run_shell = importlib.import_module("flowpilot_core_runtime.run_shell")
runtime = importlib.import_module("flowpilot_core_runtime.runtime")
lifecycle_runner = importlib.import_module("simulations.run_flowpilot_lifecycle_guard_checks")


def role_result_body(summary: str, **fields: object) -> str:
    payload: dict[str, object] = {
        "decision": "pass",
        "pm_visible_summary": [summary],
        "current_evidence_refs": ["current-runtime-evidence"],
    }
    payload.update(fields)
    return json.dumps(payload)


class FlowPilotLifecycleGuardTests(unittest.TestCase):
    def _lease_packet(
        self,
        root: Path,
        *,
        packet_id: str,
        responsibility: str,
        agent_id: str,
        host_kind: str = "fake",
    ) -> str:
        dispatch = flowpilot_new.dispatch_current_role(
            root,
            packet_id=packet_id,
            responsibility=responsibility,
            host_kind=host_kind,
            agent_id=agent_id,
        )
        self.assertTrue(dispatch["ok"], dispatch)
        return str(dispatch["lease_id"])

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
            self.assertEqual(started["lifecycle_guard"]["next_action"]["action_type"], "dispatch_current_role")
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

    def test_repeated_dispatch_current_role_reuses_current_active_lease(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = flowpilot_new.start_run(
                root,
                run_id="run-dispatch-idempotent",
                headless_startup_text="Exercise repeated dispatch.",
                require_formal_ui=False,
            )
            packet_id = started["next_action"]["subject_id"]

            first = flowpilot_new.dispatch_current_role(
                root,
                packet_id=packet_id,
                responsibility="pm",
                host_kind="fake",
                agent_id="fake-pm",
            )
            shell = run_shell.load_run_shell(root, run_id="run-dispatch-idempotent")
            first_ledger = run_shell.load_run_ledger(shell)
            first_lease_count = len(first_ledger["leases"])
            second = flowpilot_new.dispatch_current_role(
                root,
                packet_id=packet_id,
                responsibility="pm",
                host_kind="fake",
                agent_id="fake-pm",
            )
            second_ledger = run_shell.load_run_ledger(shell)

            self.assertTrue(first["ok"], first)
            self.assertTrue(second["ok"], second)
            self.assertEqual(second["lease_id"], first["lease_id"])
            self.assertEqual(len(second_ledger["leases"]), first_lease_count)
            self.assertEqual(second_ledger["packets"][packet_id]["assigned_lease_id"], first["lease_id"])
            self.assertEqual(second_ledger["leases"][first["lease_id"]]["status"], "active")

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
            lease_id = self._lease_packet(
                root,
                packet_id=packet_id,
                responsibility="pm",
                agent_id="fake-pm",
            )
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
            self.assertEqual(duty["wait_patrol"]["seconds"], 300)
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
            self.assertIn("next_action:dispatch_current_role", preflight["final_return_preflight"]["blockers"])
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
            lease_id = self._lease_packet(
                root,
                packet_id=packet_id,
                responsibility="pm",
                agent_id="fake-pm-progress",
            )
            flowpilot_new.ack(root, lease_id=lease_id, packet_id=packet_id)

            shell = run_shell.load_run_shell(root, run_id="run-progress-grace")
            progress = flowpilot_new.progress(root, lease_id=lease_id, packet_id=packet_id, status="working")

            self.assertEqual(progress["next_action"]["action_type"], "wait_for_result")
            self.assertEqual(progress["lifecycle_guard"]["decision"], "wait_for_result")
            self.assertEqual(progress["lifecycle_guard"]["wait_recovery"]["state"], "grace_wait")
            self.assertEqual(progress["foreground_duty"]["action"], "wait_patrol")
            ledger = run_shell.load_run_ledger(shell)
            self.assertEqual(ledger["leases"][lease_id]["progress_count"], 1)
            self.assertEqual(ledger["packets"][packet_id]["status"], "acknowledged")

    def test_progress_coalesces_same_status_but_persists_change_and_due_reminder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = flowpilot_new.start_run(
                root,
                run_id="run-progress-coalescing",
                headless_startup_text="Exercise bounded progress persistence.",
                require_formal_ui=False,
            )
            packet_id = started["next_action"]["subject_id"]
            lease_id = self._lease_packet(
                root,
                packet_id=packet_id,
                responsibility="pm",
                agent_id="fake-pm-progress-coalescing",
            )
            flowpilot_new.ack(root, lease_id=lease_id, packet_id=packet_id)
            shell = run_shell.load_run_shell(root, run_id="run-progress-coalescing")

            first = flowpilot_new.progress(
                root,
                lease_id=lease_id,
                packet_id=packet_id,
                status="working",
            )
            first_ledger = run_shell.load_run_ledger(shell)
            first_progress_events = [
                event for event in first_ledger["events"] if event["event_type"] == "lease_progress"
            ]
            ledger_mtime = shell.ledger_path.stat().st_mtime_ns

            with mock.patch.object(run_shell, "save_run_ledger", wraps=run_shell.save_run_ledger) as save_mock:
                repeated = flowpilot_new.progress(
                    root,
                    lease_id=lease_id,
                    packet_id=packet_id,
                    status="working",
                )

            repeated_ledger = run_shell.load_run_ledger(shell)
            self.assertFalse(first["coalesced"])
            self.assertTrue(repeated["coalesced"])
            self.assertFalse(repeated["progress_update"]["persisted"])
            save_mock.assert_not_called()
            self.assertEqual(shell.ledger_path.stat().st_mtime_ns, ledger_mtime)
            self.assertEqual(repeated_ledger["leases"][lease_id]["progress_count"], 1)
            self.assertEqual(
                len([event for event in repeated_ledger["events"] if event["event_type"] == "lease_progress"]),
                len(first_progress_events),
            )

            changed = flowpilot_new.progress(
                root,
                lease_id=lease_id,
                packet_id=packet_id,
                status="verifying",
            )
            self.assertFalse(changed["coalesced"])
            self.assertEqual(changed["progress_update"]["reason"], "status_changed")
            changed_ledger = run_shell.load_run_ledger(shell)
            self.assertEqual(changed_ledger["leases"][lease_id]["progress_count"], 2)

            changed_ledger["leases"][lease_id]["last_progress_at"] = (
                datetime.now(timezone.utc) - timedelta(minutes=10)
            ).isoformat()
            run_shell.save_run_ledger(shell, changed_ledger, guard_trigger="test_progress_due")
            due = flowpilot_new.progress(
                root,
                lease_id=lease_id,
                packet_id=packet_id,
                status="verifying",
            )
            due_ledger = run_shell.load_run_ledger(shell)
            self.assertFalse(due["coalesced"])
            self.assertEqual(due["progress_update"]["reason"], "due_liveness_reminder")
            self.assertEqual(due_ledger["leases"][lease_id]["progress_count"], 3)

    def test_progress_rejects_status_outside_current_finite_vocabulary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = flowpilot_new.start_run(
                root,
                run_id="run-progress-invalid-status",
                headless_startup_text="Exercise finite progress status rejection.",
                require_formal_ui=False,
            )
            packet_id = started["next_action"]["subject_id"]
            lease_id = self._lease_packet(
                root,
                packet_id=packet_id,
                responsibility="pm",
                agent_id="fake-pm-progress-invalid",
            )
            flowpilot_new.ack(root, lease_id=lease_id, packet_id=packet_id)

            with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "progress status must be one of"):
                flowpilot_new.progress(
                    root,
                    lease_id=lease_id,
                    packet_id=packet_id,
                    status="still_working",
                )

    def test_ack_wait_uses_five_and_ten_minute_thresholds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = flowpilot_new.start_run(
                root,
                run_id="run-ack-thresholds",
                headless_startup_text="Exercise ACK wait thresholds.",
                require_formal_ui=False,
            )
            packet_id = started["next_action"]["subject_id"]
            lease_id = self._lease_packet(
                root,
                packet_id=packet_id,
                responsibility="pm",
                agent_id="fake-pm-ack-threshold",
            )
            shell = run_shell.load_run_shell(root, run_id="run-ack-thresholds")
            ledger = run_shell.load_run_ledger(shell)
            ledger["leases"][lease_id]["created_at"] = (datetime.now(timezone.utc) - timedelta(minutes=4, seconds=59)).isoformat()
            run_shell.save_run_ledger(shell, ledger, guard_trigger="test_ack_wait")

            patrol = flowpilot_new.patrol(root)
            self.assertEqual(patrol["lifecycle_guard"]["wait_recovery"]["state"], "wait_patrol")

            ledger = run_shell.load_run_ledger(shell)
            ledger["leases"][lease_id]["created_at"] = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
            run_shell.save_run_ledger(shell, ledger, guard_trigger="test_ack_reminder")
            patrol = flowpilot_new.patrol(root)
            self.assertEqual(patrol["lifecycle_guard"]["decision"], "wait_for_ack")
            self.assertEqual(patrol["lifecycle_guard"]["wait_recovery"]["state"], "ack_reminder_due")
            self.assertFalse(patrol["lifecycle_guard"]["wait_recovery"]["replacement_eligible"])
            self.assertEqual(patrol["foreground_duty"]["action"], "wait_patrol")
            self.assertTrue(patrol["foreground_duty"]["wait_patrol"]["reminder"]["due"])
            self.assertEqual(patrol["foreground_duty"]["wait_patrol"]["reminder"]["kind"], "ack")

            ledger = run_shell.load_run_ledger(shell)
            ledger["leases"][lease_id]["created_at"] = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
            run_shell.save_run_ledger(shell, ledger, guard_trigger="test_ack_replace")
            patrol = flowpilot_new.patrol(root)
            self.assertEqual(patrol["lifecycle_guard"]["decision"], "reissue_or_replace_lease")
            self.assertEqual(patrol["lifecycle_guard"]["wait_recovery"]["state"], "ack_replacement_due")
            self.assertTrue(patrol["lifecycle_guard"]["wait_recovery"]["replacement_eligible"])
            self.assertEqual(patrol["foreground_duty"]["action"], "recover_or_reissue")

    def test_acknowledged_wait_uses_progress_reminder_and_replacement_thresholds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = flowpilot_new.start_run(
                root,
                run_id="run-progress-thresholds",
                headless_startup_text="Exercise progress evidence thresholds.",
                require_formal_ui=False,
            )
            packet_id = started["next_action"]["subject_id"]
            lease_id = self._lease_packet(
                root,
                packet_id=packet_id,
                responsibility="pm",
                agent_id="fake-pm-progress-threshold",
            )
            flowpilot_new.ack(root, lease_id=lease_id, packet_id=packet_id)
            shell = run_shell.load_run_shell(root, run_id="run-progress-thresholds")
            ledger = run_shell.load_run_ledger(shell)
            ledger["leases"][lease_id]["ack_received_at"] = (datetime.now(timezone.utc) - timedelta(minutes=9, seconds=59)).isoformat()
            run_shell.save_run_ledger(shell, ledger, guard_trigger="test_progress_fresh")

            patrol = flowpilot_new.patrol(root)
            self.assertEqual(patrol["lifecycle_guard"]["decision"], "wait_for_result")
            self.assertEqual(patrol["lifecycle_guard"]["wait_recovery"]["state"], "grace_wait")

            ledger = run_shell.load_run_ledger(shell)
            ledger["leases"][lease_id]["ack_received_at"] = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
            run_shell.save_run_ledger(shell, ledger, guard_trigger="test_progress_reminder")
            patrol = flowpilot_new.patrol(root)
            self.assertEqual(patrol["lifecycle_guard"]["decision"], "wait_for_result")
            self.assertEqual(patrol["lifecycle_guard"]["wait_recovery"]["state"], "progress_reminder_due")
            self.assertFalse(patrol["lifecycle_guard"]["wait_recovery"]["replacement_eligible"])
            self.assertEqual(patrol["foreground_duty"]["wait_patrol"]["reminder"]["kind"], "progress")

            recovered = flowpilot_new.progress(root, lease_id=lease_id, packet_id=packet_id, status="working")
            self.assertEqual(recovered["lifecycle_guard"]["decision"], "wait_for_result")
            self.assertEqual(recovered["lifecycle_guard"]["wait_recovery"]["state"], "grace_wait")

            ledger = run_shell.load_run_ledger(shell)
            stale = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
            ledger["leases"][lease_id]["ack_received_at"] = stale
            ledger["leases"][lease_id]["last_progress_at"] = stale
            run_shell.save_run_ledger(shell, ledger, guard_trigger="test_progress_replace")
            patrol = flowpilot_new.patrol(root)
            self.assertEqual(patrol["lifecycle_guard"]["decision"], "reissue_or_replace_lease")
            self.assertEqual(patrol["lifecycle_guard"]["wait_recovery"]["state"], "progress_replacement_due")
            self.assertTrue(patrol["lifecycle_guard"]["wait_recovery"]["replacement_eligible"])

    def test_legacy_host_liveness_current_surface_is_removed(self) -> None:
        self.assertFalse(hasattr(flowpilot_new, "host_liveness"))
        self.assertFalse(hasattr(runtime, "record_host_liveness"))

    def test_legacy_liveness_fields_do_not_override_fresh_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = flowpilot_new.start_run(
                root,
                run_id="run-legacy-liveness-residue",
                headless_startup_text="Exercise legacy liveness residue.",
                require_formal_ui=False,
            )
            packet_id = started["next_action"]["subject_id"]
            lease_id = self._lease_packet(
                root,
                packet_id=packet_id,
                responsibility="pm",
                agent_id="fake-pm-legacy-residue",
            )
            flowpilot_new.ack(root, lease_id=lease_id, packet_id=packet_id)
            shell = run_shell.load_run_shell(root, run_id="run-legacy-liveness-residue")
            ledger = run_shell.load_run_ledger(shell)
            ledger["leases"][lease_id]["liveness_status"] = "timeout_unknown"
            ledger["leases"][lease_id]["last_liveness_status"] = "lost"
            run_shell.save_run_ledger(shell, ledger, guard_trigger="test_legacy_residue")

            recovered = flowpilot_new.progress(root, lease_id=lease_id, packet_id=packet_id, status="working")

            self.assertEqual(recovered["lifecycle_guard"]["decision"], "wait_for_result")
            self.assertEqual(recovered["lifecycle_guard"]["wait_recovery"]["state"], "grace_wait")
            self.assertEqual(
                recovered["lifecycle_guard"]["wait_recovery"]["last_liveness_evidence_kind"],
                "progress",
            )

    def test_user_stop_terminal_fence_allows_exit_without_closure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = flowpilot_new.start_run(
                root,
                run_id="run-user-stop-terminal",
                headless_startup_text="Exercise explicit stop.",
                require_formal_ui=False,
            )
            packet_id = started["next_action"]["subject_id"]
            lease_id = self._lease_packet(
                root,
                packet_id=packet_id,
                responsibility="pm",
                agent_id="fake-pm-stop",
            )

            stopped = flowpilot_new.stop_run(root, reason="unit test stop")

            self.assertEqual(stopped["next_action"]["action_type"], "terminal_lifecycle")
            self.assertEqual(stopped["lifecycle_guard"]["decision"], "terminal_return")
            self.assertTrue(stopped["final_return_preflight"]["allowed"])
            self.assertEqual(stopped["final_return_preflight"]["terminal_lifecycle_status"], "stopped_by_user")
            shell = run_shell.load_run_shell(root, run_id="run-user-stop-terminal")
            ledger = run_shell.load_run_ledger(shell)
            self.assertEqual(ledger["leases"][lease_id]["status"], "closed")
            self.assertEqual(ledger["packets"][packet_id]["status"], "stopped_by_user")
            self.assertTrue((shell.run_root / "lifecycle" / "terminal_lifecycle.json").exists())
            with self.assertRaisesRegex(Exception, "run is terminal"):
                flowpilot_new.ack(root, lease_id=lease_id, packet_id=packet_id)

    def test_user_cancel_terminal_fence_blocks_new_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = flowpilot_new.start_run(
                root,
                run_id="run-user-cancel-terminal",
                headless_startup_text="Exercise explicit cancel.",
                require_formal_ui=False,
            )
            packet_id = started["next_action"]["subject_id"]

            cancelled = flowpilot_new.cancel_run(root, reason="unit test cancel")

            self.assertEqual(cancelled["next_action"]["action_type"], "terminal_lifecycle")
            self.assertTrue(cancelled["final_return_preflight"]["allowed"])
            with self.assertRaisesRegex(Exception, "run is terminal"):
                flowpilot_new.dispatch_current_role(
                    root,
                    packet_id=packet_id,
                    responsibility="pm",
                    host_kind="fake",
                    agent_id="pm-agent",
                )

    def test_orphan_runner_summary_routes_recovery_without_accepting_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = flowpilot_new.start_run(
                root,
                run_id="run-orphan-runner-summary",
                headless_startup_text="Exercise orphan evidence recovery.",
                require_formal_ui=False,
            )
            packet_id = started["next_action"]["subject_id"]
            lease_id = self._lease_packet(
                root,
                packet_id=packet_id,
                responsibility="pm",
                agent_id="fake-pm-orphan",
            )
            flowpilot_new.ack(root, lease_id=lease_id, packet_id=packet_id)
            shell = run_shell.load_run_shell(root, run_id="run-orphan-runner-summary")
            summary_path = shell.run_root / "evidence" / "flowguard" / packet_id / "runner_summary.json"
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary_path.write_text(
                json.dumps(
                    {
                        "status": "completed",
                        "runners": [{"name": "fake-check", "exit_code": 0}],
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            patrol = flowpilot_new.patrol(root)

            self.assertEqual(patrol["lifecycle_guard"]["decision"], "reissue_or_replace_lease")
            self.assertEqual(patrol["lifecycle_guard"]["wait_recovery"]["state"], "orphan_evidence")
            self.assertEqual(patrol["foreground_duty"]["action"], "recover_or_reissue")
            ledger = run_shell.load_run_ledger(shell)
            self.assertIn(packet_id, ledger["orphan_evidence"])
            self.assertEqual(ledger["packets"][packet_id]["status"], "acknowledged")
            self.assertFalse(ledger["packets"][packet_id]["accepted_result_id"])

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
            lease_id = self._lease_packet(
                root,
                packet_id=packet_id,
                responsibility="pm",
                agent_id="fake-pm-accepted",
            )
            flowpilot_new.ack(root, lease_id=lease_id, packet_id=packet_id)
            flowpilot_new.submit_result(
                root,
                lease_id=lease_id,
                packet_id=packet_id,
                body=role_result_body("PM"),
            )
            shell = run_shell.load_run_shell(root, run_id="run-accepted-hard-gate")
            ledger = run_shell.load_run_ledger(shell)
            packet = ledger["packets"][packet_id]
            packet["status"] = "accepted"
            packet["accepted_result_id"] = packet["result_ids"][-1]
            run_shell.save_run_ledger(shell, ledger, guard_trigger="test_accept")

            with self.assertRaisesRegex(Exception, "cannot assign accepted packet"):
                flowpilot_new.dispatch_current_role(
                    root,
                    packet_id=packet_id,
                    responsibility="pm",
                    host_kind="fake",
                    agent_id="pm-agent",
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
            original_lease = self._lease_packet(
                root,
                packet_id=packet_id,
                responsibility="pm",
                agent_id="fake-pm-original",
            )
            flowpilot_new.ack(root, lease_id=original_lease, packet_id=packet_id)
            result_id = flowpilot_new.submit_result(
                root,
                lease_id=original_lease,
                packet_id=packet_id,
                body=role_result_body("PM"),
            )["result_id"]
            shell = run_shell.load_run_shell(root, run_id="run-accepted-race-repair")
            ledger = run_shell.load_run_ledger(shell)
            ledger["results"][result_id]["status"] = "accepted"
            ledger["results"][result_id]["accepted"] = True
            ledger["packets"][packet_id]["status"] = "acknowledged"
            ledger["packets"][packet_id]["accepted_result_id"] = ""
            assignment = runtime.resolve_role_assignment(ledger, "pm", packet_id=packet_id, host_kind="fake")
            replacement_lease = runtime.lease_agent(
                ledger,
                "pm",
                packet_id=packet_id,
                assignment_id=assignment["assignment_id"],
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
            self.assertEqual(repaired["next_action"]["action_type"], "dispatch_current_role")
            ledger = run_shell.load_run_ledger(shell)
            self.assertEqual(ledger["packets"][packet_id]["status"], "accepted")
            self.assertEqual(ledger["packets"][packet_id]["accepted_result_id"], result_id)
            self.assertEqual(ledger["packets"][packet_id]["assigned_lease_id"], original_lease)
            self.assertEqual(ledger["leases"][replacement_lease]["status"], "closed")

    def test_patrol_does_not_classify_repeated_role_dispatch_as_stuck(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flowpilot_new.start_run(
                root,
                run_id="run-guard-role-dispatch",
                headless_startup_text="Exercise repeated action patrol.",
                require_formal_ui=False,
            )

            first = flowpilot_new.patrol(root)
            second = flowpilot_new.patrol(root)
            third = flowpilot_new.patrol(root)
            shell = run_shell.load_run_shell(root, run_id="run-guard-role-dispatch")
            ledger = run_shell.load_run_ledger(shell)
            refreshed = runtime.refresh_lifecycle_guard(ledger, trigger="patrol")

            self.assertFalse(first["lifecycle_guard"]["controller_stop_allowed"])
            self.assertFalse(second["lifecycle_guard"]["controller_stop_allowed"])
            self.assertEqual(third["lifecycle_guard"]["decision"], "process_next_action")
            self.assertEqual(refreshed["decision"], "process_next_action")
            self.assertEqual(third["lifecycle_guard"]["next_action_class"], "role_dispatch")
            self.assertGreaterEqual(third["lifecycle_guard"]["repeated_count"], 3)

    def test_prior_stuck_decision_absorbs_same_action_until_progress_event(self) -> None:
        ledger = runtime.new_ledger("Build the thing", "Finish cleanly")
        first = runtime.preview_lifecycle_guard(ledger, trigger="patrol")
        ledger["lifecycle_guard_history"] = [
            {
                "created_at": "2026-06-15T00:00:00Z",
                "trigger": "patrol",
                "decision": "control_plane_stuck",
                "controller_stop_allowed": False,
                "action_key": first["action_key"],
                "observed_event_count": first["observed_event_count"],
                "repeated_count": 3,
                "subject_id": first["next_action"].get("subject_id", ""),
            }
        ]

        absorbed = runtime.preview_lifecycle_guard(ledger, trigger="final_preflight")

        self.assertEqual(absorbed["action_key"], first["action_key"])
        self.assertEqual(absorbed["observed_event_count"], first["observed_event_count"])
        self.assertEqual(absorbed["decision"], "control_plane_stuck")
        self.assertTrue(absorbed["stuck_absorbed_from_history"])
        self.assertIn("same nonterminal action", absorbed["reason"])

    def test_inactive_lease_result_is_rejected_before_result_allocation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = flowpilot_new.start_run(
                root,
                run_id="run-guard-inactive-result",
                headless_startup_text="Exercise inactive lease result.",
                require_formal_ui=False,
            )
            packet_id = started["next_action"]["subject_id"]
            lease_id = self._lease_packet(
                root,
                packet_id=packet_id,
                responsibility="pm",
                agent_id="fake-pm",
            )
            flowpilot_new.ack(root, lease_id=lease_id, packet_id=packet_id)

            shell = run_shell.load_run_shell(root, run_id="run-guard-inactive-result")
            ledger = run_shell.load_run_ledger(shell)
            runtime.expire_lease(ledger, lease_id, "test_inactive")
            run_shell.save_run_ledger(shell, ledger, guard_trigger="test_expire")

            before = run_shell.load_run_ledger(shell)
            before_result_ids = list(before["packets"][packet_id]["result_ids"])
            before_result_count = len(before["results"])
            with self.assertRaisesRegex(Exception, "closed_or_inactive_lease"):
                flowpilot_new.submit_result(
                    root,
                    lease_id=lease_id,
                    packet_id=packet_id,
                    body=role_result_body("late inactive lease result"),
                )
            after = run_shell.load_run_ledger(shell)
            self.assertEqual(after["packets"][packet_id]["result_ids"], before_result_ids)
            self.assertEqual(len(after["results"]), before_result_count)

    def test_late_result_after_route_mutation_is_rejected_before_result_allocation(self) -> None:
        ledger = runtime.new_ledger("Build", "Finish")
        ledger["startup_intake"] = {
            "sealed": True,
            "startup_answers": {
                runtime.BACKGROUND_COLLABORATION_ACK_FIELD: True,
            },
        }
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

        packet = ledger["packets"][packet_id]
        before_result_ids = list(packet["result_ids"])
        before_result_count = len(ledger["results"])
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "quarantined_packet|stale_route_version"):
            host.submit_host_result(
                ledger,
                lease_id,
                packet_id,
                role_result_body("late"),
            )

        self.assertEqual(ledger["packets"][packet_id]["status"], "quarantined_after_route_mutation")
        self.assertEqual(packet["result_ids"], before_result_ids)
        self.assertEqual(len(ledger["results"]), before_result_count)

    def test_late_result_rejects_noncurrent_packet_statuses_without_mutation(self) -> None:
        for terminal_status in ("accepted", "quarantined_after_route_mutation", "superseded_after_repair"):
            with self.subTest(terminal_status=terminal_status):
                ledger = runtime.new_ledger("Build", "Finish")
                ledger["startup_intake"] = {
                    "sealed": True,
                    "startup_answers": {
                        runtime.BACKGROUND_COLLABORATION_ACK_FIELD: True,
                    },
                }
                runtime.create_route(ledger, "route", ["one"])
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
                packet = ledger["packets"][packet_id]
                packet["status"] = terminal_status
                if terminal_status == "accepted":
                    ledger["results"]["result-existing"] = {
                        "result_id": "result-existing",
                        "packet_id": packet_id,
                        "producer_lease_id": lease_id,
                        "status": "accepted",
                        "accepted": True,
                    }
                    packet["accepted_result_id"] = "result-existing"

                before_result_ids = list(packet["result_ids"])
                before_result_count = len(ledger["results"])
                with self.assertRaisesRegex(
                    runtime.BlackBoxRuntimeError,
                    "duplicate_after_packet_accepted|noncurrent_packet|quarantined_packet",
                ):
                    host.submit_host_result(
                        ledger,
                        lease_id,
                        packet_id,
                        role_result_body(f"late {terminal_status}"),
                    )

                self.assertEqual(packet["status"], terminal_status)
                self.assertEqual(packet["result_ids"], before_result_ids)
                self.assertEqual(len(ledger["results"]), before_result_count)

    def test_fake_host_late_result_is_rejected_without_reactivation(self) -> None:
        ledger = runtime.new_ledger("Build", "Finish")
        ledger["startup_intake"] = {
            "sealed": True,
            "startup_answers": {
                runtime.BACKGROUND_COLLABORATION_ACK_FIELD: True,
            },
        }
        runtime.create_route(ledger, "route", ["one"])
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
        packet = ledger["packets"][packet_id]
        packet["status"] = "superseded_after_repair"

        before_result_ids = list(packet["result_ids"])
        before_result_count = len(ledger["results"])
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "noncurrent_packet"):
            host.submit_host_result(ledger, lease_id, packet_id, role_result_body("late fake host"))

        self.assertEqual(packet["status"], "superseded_after_repair")
        self.assertEqual(packet["result_ids"], before_result_ids)
        self.assertEqual(len(ledger["results"]), before_result_count)

    def test_current_result_history_appends_on_open_packet(self) -> None:
        ledger = runtime.new_ledger("Build", "Finish")
        ledger["startup_intake"] = {
            "sealed": True,
            "startup_answers": {
                runtime.BACKGROUND_COLLABORATION_ACK_FIELD: True,
            },
        }
        runtime.create_route(ledger, "route", ["one"])
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

        result_id = host.submit_host_result(ledger, lease_id, packet_id, role_result_body("current"))

        packet = ledger["packets"][packet_id]
        self.assertEqual(packet["result_ids"], [result_id])
        self.assertEqual(packet["status"], "result_submitted")
        self.assertFalse(ledger["results"][result_id]["non_authoritative"])

    def test_accept_packet_result_writes_single_pointer_on_current_commit(self) -> None:
        ledger = runtime.new_ledger("Build", "Finish")
        ledger["startup_intake"] = {
            "sealed": True,
            "startup_answers": {
                runtime.BACKGROUND_COLLABORATION_ACK_FIELD: True,
            },
        }
        runtime.create_route(ledger, "route", ["one"])
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
        packet = ledger["packets"][packet_id]
        result = {
            "result_id": "result-current-commit",
            "packet_id": packet_id,
            "producer_lease_id": lease_id,
            "status": "mechanically_valid",
            "accepted": False,
        }
        ledger["results"][result["result_id"]] = result
        packet["result_ids"].append(result["result_id"])

        runtime._accept_packet_result(ledger, packet, result, ledger["leases"][lease_id], reason="unit_accept")

        self.assertEqual(packet["status"], "accepted")
        self.assertEqual(packet["accepted_result_id"], result["result_id"])
        self.assertEqual(result["status"], "accepted")
        self.assertTrue(result["accepted"])

    def test_duplicate_after_accepted_rejects_without_polluting_accepted_result_pointer(self) -> None:
        ledger = runtime.new_ledger("Build", "Finish")
        ledger["startup_intake"] = {
            "sealed": True,
            "startup_answers": {
                runtime.BACKGROUND_COLLABORATION_ACK_FIELD: True,
            },
        }
        runtime.create_route(ledger, "route", ["one"])
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
        first_result_id = host.submit_host_result(ledger, lease_id, packet_id, role_result_body("first"))
        packet = ledger["packets"][packet_id]
        packet["status"] = "accepted"
        packet["accepted_result_id"] = first_result_id
        ledger["results"][first_result_id]["status"] = "accepted"
        ledger["results"][first_result_id]["accepted"] = True

        before_result_ids = list(packet["result_ids"])
        before_result_count = len(ledger["results"])
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "packet already accepted"):
            host.submit_host_result(ledger, lease_id, packet_id, role_result_body("duplicate"))

        self.assertEqual(packet["status"], "accepted")
        self.assertEqual(packet["accepted_result_id"], first_result_id)
        self.assertEqual(packet["result_ids"], before_result_ids)
        self.assertEqual(len(ledger["results"]), before_result_count)

    def test_duplicate_current_same_lease_result_rejects_without_second_result(self) -> None:
        ledger = runtime.new_ledger("Build", "Finish")
        ledger["startup_intake"] = {
            "sealed": True,
            "startup_answers": {
                runtime.BACKGROUND_COLLABORATION_ACK_FIELD: True,
            },
        }
        runtime.create_route(ledger, "route", ["one"])
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
        first_result_id = host.submit_host_result(ledger, lease_id, packet_id, role_result_body("first"))
        packet = ledger["packets"][packet_id]
        before_result_ids = list(packet["result_ids"])
        before_result_count = len(ledger["results"])

        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "duplicate_output_from_same_lease"):
            host.submit_host_result(ledger, lease_id, packet_id, role_result_body("second"))

        self.assertEqual(packet["status"], "result_submitted")
        self.assertEqual(packet["result_ids"], before_result_ids)
        self.assertEqual(len(ledger["results"]), before_result_count)
        self.assertEqual(packet["result_ids"], [first_result_id])

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
