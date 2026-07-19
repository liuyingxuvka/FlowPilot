from __future__ import annotations

import time

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase
import flowpilot_router_io as router_io  # noqa: E402
import flowpilot_router_io_json as router_io_json  # noqa: E402
import flowpilot_router_io_locks as router_io_locks  # noqa: E402
import flowpilot_router_daemon_runtime as router_daemon_runtime  # noqa: E402


class StartupDaemonRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_daemon_error_diagnostics_include_memory_context(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-daemon-error", status="controller_ready")
        state = read_json(router.run_state_path(run_root))
        state["pending_action"] = router.make_action(
            action_type="load_resume_state",
            actor="controller",
            label="controller_loads_resume_state",
            summary="Pending action included in daemon diagnostics.",
        )
        router.save_run_state(run_root, state)

        diagnostics = router._router_daemon_error_diagnostics(root, run_root, state, MemoryError())  # type: ignore[attr-defined]

        self.assertEqual(diagnostics["type"], "MemoryError")
        self.assertEqual(diagnostics["current_action"]["action_type"], "load_resume_state")
        self.assertIn("artifact_size_summary", diagnostics)
        self.assertIn("router_state", diagnostics["artifact_size_summary"]["key_files"])
        self.assertIn("traceback", diagnostics)
        self.assertIn("traceback_unavailable_reason", diagnostics)

    def test_bootloader_action_requires_pending_router_action(self) -> None:
        root = self.make_project()

        with self.assertRaises(router.RouterError):
            router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_router")
        self.assertEqual(self.next_and_apply(root)["applied"], "load_router")
    def test_run_until_wait_folds_only_internal_bootloader_actions_after_banner(self) -> None:
        root = self.make_project()
        router.run_until_wait(root, new_invocation=True)
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))

        result = router.run_until_wait(root)

        self.assertEqual(result["action_type"], "load_controller_core")
        self.assertEqual(result["folded_command"], "run-until-wait")
        self.assertEqual([item["action_type"] for item in result["folded_applied_actions"]], [])
        self.assertEqual(result["folded_stop_reason"], "requires_user_host_or_role_boundary")
        bootstrap = self.bootstrap_state(root)
        self.assertTrue(bootstrap["flags"]["run_shell_created"])
        self.assertTrue(bootstrap["flags"]["router_daemon_started"])
        self.assertTrue(bootstrap["flags"]["mailbox_initialized"])
        self.assertTrue(bootstrap["flags"].get("user_request_recorded", False))
        self.assertTrue(bootstrap["flags"].get("deterministic_bootstrap_seed_completed", False))
        self.assertFalse(bootstrap["flags"].get("banner_emitted", False))
        self.assertFalse(bootstrap["flags"].get("roles_started", False))
        self.assertTrue((root / ".flowpilot" / "current.json").exists())
        run_root = self.run_root_for(root)
        self.assertTrue((run_root / "packet_ledger.json").exists())
        self.assertTrue((run_root / "bootstrap" / "deterministic_bootstrap_seed_evidence.json").exists())
        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        startup_types = [item.get("action_type") for item in controller_ledger["actions"] if item.get("scope_kind") == "startup"]
        self.assertIn("load_controller_core", startup_types)
        self.assertNotIn("emit_startup_banner", startup_types)
        self.assertNotIn("start_role_slots", startup_types)
        self.assertNotIn("fill_runtime_placeholders", startup_types)
        self.assertNotIn("initialize_mailbox", startup_types)
        self.assertNotIn("record_user_request", startup_types)
        self.assertNotIn("write_user_intake", startup_types)

        load_action = result
        self.assertEqual(load_action["action_type"], "load_controller_core")
    def test_run_until_wait_folds_user_intake_then_stops_before_role_boundary(self) -> None:
        root = self.make_project()
        router.run_until_wait(root, new_invocation=True)
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))

        result = router.run_until_wait(root)

        self.assertEqual(result["action_type"], "load_controller_core")
        self.assertEqual([item["action_type"] for item in result["folded_applied_actions"]], [])
        self.assertEqual(result["folded_stop_reason"], "requires_user_host_or_role_boundary")
        self.assertTrue((self.run_root_for(root) / "mailbox" / "outbox" / "user_intake.json").exists())
        self.assertTrue(
            (self.run_root_for(root) / "bootstrap" / "deterministic_bootstrap_seed_evidence.json").exists()
        )
        self.assertFalse(self.bootstrap_state(root)["flags"].get("roles_started", False))
    def test_reconciled_scheduler_row_receipt_replay_does_not_create_pm_blocker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)
        router.apply_action(root, "start_router_daemon")
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_controller_core")
        router.apply_action(root, "load_controller_core")

        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        load_core_row = next(item for item in controller_ledger["actions"] if item.get("action_type") == "load_controller_core")
        action_path = run_root / "runtime" / "controller_actions" / f"{load_core_row['action_id']}.json"
        entry = read_json(action_path)
        self.assert_controller_receipt_entry_projection(entry)
        entry.pop("router_reconciliation_status", None)
        entry.pop("router_reconciled_at", None)
        entry.pop("router_reconciliation", None)
        router.write_json(action_path, entry)

        run_state = read_json(router.run_state_path(run_root))
        result = router._reconcile_scheduled_controller_action_receipts(root, run_root, run_state)  # type: ignore[attr-defined]

        self.assertTrue(result["changed"])
        self.assertEqual(result["blocked"], 0)
        refreshed = read_json(action_path)
        self.assertEqual(refreshed["router_reconciliation_status"], "reconciled")
        control_blocks = run_root / "control_blocks"
        self.assertFalse(control_blocks.exists() and list(control_blocks.glob("*.json")))
    def test_run_until_wait_reaches_card_boundary_after_router_internal_manifest_check(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root, startup_answers=STARTUP_ANSWERS)
        while True:
            action = self.next_after_display_sync(root)
            if action["action_type"] in {"deliver_system_card", "deliver_system_card_bundle"}:
                break
            self.assertNotEqual(action["action_type"], "create_heartbeat_automation")
            if action["action_type"] in {
                "confirm_controller_core_boundary",
                "write_startup_mechanical_audit",
                "write_display_surface_status",
                "inject_role_io_protocol",
                "open_current_role_agent",
            }:
                router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
                continue
            self.fail(f"unexpected action before card boundary: {action['action_type']}")

        self.assertIn("check_prompt_manifest", self.router_internal_action_types(root))

        state = read_json(router.run_state_path(run_root))
        self.assertIn(state["pending_action"]["action_type"], {"deliver_system_card", "deliver_system_card_bundle"})

        result = router.run_until_wait(root)

        self.assertIn(result["action_type"], {"deliver_system_card", "deliver_system_card_bundle"})
        self.assertEqual(result["folded_applied_actions"], [])
        self.assertEqual(result["folded_stop_reason"], "requires_user_host_or_role_boundary")
    def test_router_daemon_observation_initializes_lock_status_and_ledger(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)

        result = router.run_router_daemon(root, max_ticks=1, observe_only=True, release_lock_on_exit=False)

        self.assertTrue(result["ok"])
        self.assertEqual(result["tick_interval_seconds"], 1)
        lock = read_json(run_root / "runtime" / "router_daemon.lock")
        status = read_json(run_root / "runtime" / "router_daemon_status.json")
        ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        self.assertEqual(lock["schema_version"], router.ROUTER_DAEMON_LOCK_SCHEMA)
        self.assertEqual(lock["status"], "active")
        self.assertEqual(status["schema_version"], router.ROUTER_DAEMON_STATUS_SCHEMA)
        self.assertTrue(status["daemon_mode_enabled"])
        self.assertEqual(status["tick_interval_seconds"], 1)
        self.assertNotIn("router_ownership_ledger", status)
        self.assertFalse(status["router_internal_ownership_ledger_visible_to_controller"])
        self.assertTrue((run_root / "runtime" / "router_ownership_ledger.json").exists())
        self.assertEqual(ledger["schema_version"], router.CONTROLLER_ACTION_LEDGER_SCHEMA)
        self.assertLess(list(ledger).index("controller_table_prompt"), list(ledger).index("actions"))
        prompt = ledger["controller_table_prompt"]
        self.assertEqual(prompt["language"], "en")
        self.assertEqual(prompt["row_processing_order"], "top_to_bottom")
        self.assertTrue(prompt["foreground_controller_must_remain_attached_while_flowpilot_running"])
        self.assertFalse(prompt["sealed_body_reads_allowed"])
        self.assertIn("Work from top to bottom", prompt["text"])
        self.assertIn("As long as FlowPilot is still running", prompt["text"])
        self.assertIn("continuous monitoring duty, not a finishable checklist item", prompt["text"])
        self.assertIn("return to top-to-bottom row processing", prompt["text"])

        with self.assertRaisesRegex(router.RouterError, "already active"):
            router.run_router_daemon(root, max_ticks=1, observe_only=True)
        stopped = router.stop_router_daemon(root, reason="test_cleanup")
        self.assertEqual(stopped["lock_status"], "released")
    def test_router_daemon_tick_stays_bound_when_current_focus_changes(self) -> None:
        root = self.make_project()
        run_a = self.write_minimal_run(root, "run-a")
        run_b = self.write_minimal_run(root, "run-b")
        self.write_current_focus(root, run_a)
        state_a = read_json(router.run_state_path(run_a))
        router._acquire_router_daemon_lock(root, run_a, state_a)  # type: ignore[attr-defined]

        self.write_current_focus(root, run_b)
        tick = router._router_daemon_tick(root, run_a, state_a, observe_only=True)  # type: ignore[attr-defined]

        self.assertEqual(tick["observe_only"], True)
        self.assertEqual(read_json(router.run_state_path(run_a))["run_id"], "run-a")
        self.assertEqual(read_json(router.run_state_path(run_b))["run_id"], "run-b")
        status_a = read_json(run_a / "runtime" / "router_daemon_status.json")
        self.assertEqual(status_a["run_id"], "run-a")
        self.assertEqual(status_a["run_root"], ".flowpilot/runs/run-a")
        self.assertFalse((run_b / "runtime" / "controller_action_ledger.json").exists())
    def test_stale_router_state_save_preserves_foreground_events_and_true_flags(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-stale-save")
        stale_state, _ = router.load_run_state_from_run_root(root, run_root)
        self.assertIsInstance(stale_state, dict)

        foreground = read_json(router.run_state_path(run_root))
        foreground["flags"]["user_intake_delivered_to_pm"] = True
        foreground["events"].append({"event": "foreground_event", "payload": {"source": "test"}})
        router.write_json(router.run_state_path(run_root), foreground)

        stale_state["daemon_mode_enabled"] = True
        stale_state["history"].append({"event": "daemon_history", "payload": {"source": "test"}})
        router.save_run_state(run_root, stale_state)

        saved = read_json(router.run_state_path(run_root))
        self.assertTrue(saved["daemon_mode_enabled"])
        self.assertTrue(saved["flags"]["user_intake_delivered_to_pm"])
        self.assertIn({"event": "foreground_event", "payload": {"source": "test"}}, saved["events"])
        self.assertIn({"event": "daemon_history", "payload": {"source": "test"}}, saved["history"])
    def test_router_daemon_stop_targets_one_parallel_run(self) -> None:
        root = self.make_project()
        run_a = self.write_minimal_run(root, "run-a")
        run_b = self.write_minimal_run(root, "run-b")
        self.write_current_focus(root, run_b)
        state_a = read_json(router.run_state_path(run_a))
        state_b = read_json(router.run_state_path(run_b))
        router._acquire_router_daemon_lock(root, run_a, state_a)  # type: ignore[attr-defined]
        router._acquire_router_daemon_lock(root, run_b, state_b)  # type: ignore[attr-defined]

        stopped = router.stop_router_daemon(root, reason="test_stop_a", run_root=run_a)

        self.assertEqual(stopped["run_id"], "run-a")
        self.assertEqual(read_json(run_a / "runtime" / "router_daemon.lock")["status"], "released")
        self.assertEqual(read_json(run_b / "runtime" / "router_daemon.lock")["status"], "active")
        self.assertFalse(read_json(router.run_state_path(run_a))["daemon_mode_enabled"])
        self.assertTrue(read_json(router.run_state_path(run_b))["daemon_mode_enabled"])
    def test_router_daemon_liveness_rejects_reused_pid_identity(self) -> None:
        owner = router._router_daemon_owner()  # type: ignore[attr-defined]
        lock = {
            "schema_version": router.ROUTER_DAEMON_LOCK_SCHEMA,
            "status": "active",
            "created_at": router.utc_now(),
            "last_tick_at": router.utc_now(),
            "owner": {**owner, "start_token": "different-process-start"},
        }

        liveness = router._router_daemon_lock_liveness(lock)  # type: ignore[attr-defined]

        self.assertTrue(liveness["pid_live"])
        self.assertFalse(liveness["process_live"])
        self.assertFalse(liveness["live"])
        self.assertIn("owner_process_identity_mismatch", liveness["reasons"])
    def test_router_daemon_stop_releases_only_after_exact_tree_cleanup(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-dedicated-stop")
        state = read_json(router.run_state_path(run_root))
        owner = {
            "pid": 424242,
            "start_token": "test-start-token",
            "host": "test-host",
            "process_kind": "dedicated_daemon",
            "daemon_instance_id": "test-daemon-instance",
        }
        lock_path = run_root / "runtime" / "router_daemon.lock"
        router.write_json(
            lock_path,
            {
                "schema_version": router.ROUTER_DAEMON_LOCK_SCHEMA,
                "run_id": state["run_id"],
                "run_root": router.project_relative(root, run_root),
                "status": "active",
                "created_at": router.utc_now(),
                "last_tick_at": router.utc_now(),
                "owner": owner,
            },
        )
        child = {"pid": 424243, "start_token": "child-start-token"}
        observed_statuses: list[str] = []
        live_identities = {
            (owner["pid"], owner["start_token"]),
            (child["pid"], child["start_token"]),
        }

        def identity_is_live(identity: dict) -> bool:
            return (identity.get("pid"), identity.get("start_token")) in live_identities

        def cleanup_tree(identity: dict, *, timeout_seconds: float) -> dict:
            del timeout_seconds
            observed_statuses.append(read_json(lock_path)["status"])
            live_identities.discard((identity.get("pid"), identity.get("start_token")))
            if identity == owner:
                live_identities.discard((child["pid"], child["start_token"]))
            return {
                "cleanup_confirmed": True,
                "descendant_zero_confirmed": True,
                "reason": "process_tree_exited",
                "observed_descendant_identities": [child],
                "remaining_live_identities": [],
                "pid_reuse_detected": False,
                "signal_sent": True,
            }

        with mock.patch.object(router, "_process_identity_is_live", side_effect=identity_is_live), mock.patch.object(
            router,
            "_process_descendant_identities",
            return_value=[child],
        ), mock.patch.object(
            router,
            "_terminate_process_tree",
            side_effect=cleanup_tree,
        ), mock.patch.object(
            router,
            "ROUTER_DAEMON_STOP_TIMEOUT_SECONDS",
            0.0,
        ):
            stopped = router.stop_router_daemon(root, reason="test_exact_tree_cleanup", run_root=run_root)

        self.assertEqual(observed_statuses, ["stop_requested"])
        self.assertTrue(stopped["process_cleanup"]["cleanup_confirmed"])
        self.assertTrue(stopped["process_cleanup"]["descendant_zero_confirmed"])
        released = read_json(lock_path)
        self.assertEqual(released["status"], "released")
        self.assertEqual(released["owner"], owner)
        self.assertEqual(released["released_owner"], owner)
        self.assertTrue(released["cleanup_proof"]["cleanup_confirmed"])
    def test_router_daemon_stop_collects_descendant_created_during_stop_wait(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-late-descendant-stop")
        state = read_json(router.run_state_path(run_root))
        owner = {
            "pid": 434343,
            "start_token": "late-owner-token",
            "host": "test-host",
            "process_kind": "dedicated_daemon",
            "daemon_instance_id": "late-daemon-instance",
        }
        child = {"pid": 434344, "start_token": "late-child-token"}
        lock_path = run_root / "runtime" / "router_daemon.lock"
        router.write_json(
            lock_path,
            {
                "schema_version": router.ROUTER_DAEMON_LOCK_SCHEMA,
                "run_id": state["run_id"],
                "run_root": router.project_relative(root, run_root),
                "status": "active",
                "created_at": router.utc_now(),
                "last_tick_at": router.utc_now(),
                "owner": owner,
            },
        )
        live_identities = {
            (owner["pid"], owner["start_token"]),
            (child["pid"], child["start_token"]),
        }
        descendant_calls = 0
        cleanup_targets: list[dict] = []

        def identity_is_live(identity: dict) -> bool:
            return (identity.get("pid"), identity.get("start_token")) in live_identities

        def descendants(_identity: dict) -> list[dict]:
            nonlocal descendant_calls
            descendant_calls += 1
            return [] if descendant_calls == 1 else [child]

        def stop_wait(_seconds: float) -> None:
            live_identities.discard((owner["pid"], owner["start_token"]))

        def cleanup_tree(identity: dict, *, timeout_seconds: float) -> dict:
            del timeout_seconds
            cleanup_targets.append(identity)
            live_identities.discard((identity.get("pid"), identity.get("start_token")))
            return {
                "cleanup_confirmed": True,
                "descendant_zero_confirmed": True,
                "reason": "process_tree_exited",
                "observed_descendant_identities": [],
                "remaining_live_identities": [],
                "pid_reuse_detected": False,
                "signal_sent": True,
            }

        with mock.patch.object(
            router,
            "_process_identity_is_live",
            side_effect=identity_is_live,
        ), mock.patch.object(
            router,
            "_process_descendant_identities",
            side_effect=descendants,
        ), mock.patch.object(
            router,
            "_terminate_process_tree",
            side_effect=cleanup_tree,
        ), mock.patch.object(
            router.time,
            "sleep",
            side_effect=stop_wait,
        ), mock.patch.object(
            router,
            "ROUTER_DAEMON_STOP_TIMEOUT_SECONDS",
            1.0,
        ):
            stopped = router.stop_router_daemon(
                root,
                reason="test_late_descendant_cleanup",
                run_root=run_root,
            )

        self.assertEqual(cleanup_targets, [child])
        self.assertEqual(
            stopped["process_cleanup"]["observed_descendant_identities"],
            [child],
        )
        self.assertTrue(stopped["process_cleanup"]["cleanup_confirmed"])
        self.assertTrue(stopped["process_cleanup"]["descendant_zero_confirmed"])
        self.assertEqual(read_json(lock_path)["status"], "released")
    def test_router_daemon_stop_does_not_signal_reused_pid(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-reused-pid")
        state = read_json(router.run_state_path(run_root))
        owner = {
            "pid": 515151,
            "start_token": "old-start-token",
            "host": "test-host",
            "process_kind": "dedicated_daemon",
            "daemon_instance_id": "old-daemon-instance",
        }
        router.write_json(
            run_root / "runtime" / "router_daemon.lock",
            {
                "schema_version": router.ROUTER_DAEMON_LOCK_SCHEMA,
                "run_id": state["run_id"],
                "run_root": router.project_relative(root, run_root),
                "status": "active",
                "created_at": router.utc_now(),
                "last_tick_at": router.utc_now(),
                "owner": owner,
            },
        )

        with mock.patch.object(router, "_process_identity_is_live", return_value=False), mock.patch.object(
            router,
            "_process_is_live",
            return_value=True,
        ), mock.patch.object(router, "_terminate_process_tree") as terminate:
            stopped = router.stop_router_daemon(root, reason="test_pid_reuse", run_root=run_root)

        terminate.assert_not_called()
        self.assertTrue(stopped["process_cleanup"]["cleanup_confirmed"])
        self.assertTrue(stopped["process_cleanup"]["pid_reuse_detected"])
        self.assertEqual(
            stopped["process_cleanup"]["reason"],
            "pid_reused_target_identity_not_signaled",
        )
    def test_router_daemon_refresh_does_not_reactivate_released_lock(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-a")
        state = read_json(router.run_state_path(run_root))
        router._acquire_router_daemon_lock(root, run_root, state)  # type: ignore[attr-defined]
        router._release_router_daemon_lock(root, run_root, reason="test_release", status="released")  # type: ignore[attr-defined]

        refreshed = router._refresh_router_daemon_lock(root, run_root)  # type: ignore[attr-defined]

        self.assertEqual(refreshed["status"], "released")
        self.assertEqual(read_json(run_root / "runtime" / "router_daemon.lock")["status"], "released")
    def test_router_daemon_stop_requested_owner_blocks_second_writer(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-stop-requested")
        self.write_current_focus(root, run_root)
        state = read_json(router.run_state_path(run_root))
        router._acquire_router_daemon_lock(root, run_root, state)  # type: ignore[attr-defined]
        lock_path = run_root / "runtime" / "router_daemon.lock"
        lock = read_json(lock_path)
        lock["status"] = "stop_requested"
        router.write_json(lock_path, lock)

        with self.assertRaisesRegex(router.RouterError, "already active"):
            router.run_router_daemon(root, max_ticks=1, observe_only=True)

        stopped = router.stop_router_daemon(root, reason="test_stop_requested_cleanup", run_root=run_root)
        self.assertEqual(stopped["lock_status"], "released")
    def test_router_daemon_immediately_continues_after_queue_budget_stop(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        calls: list[int] = []

        def fake_queue(project_root: Path, run_root: Path, run_state: dict) -> dict:
            del project_root, run_root, run_state
            calls.append(1)
            return {
                "queued_count": router.ROUTER_DAEMON_MAX_QUEUE_ACTIONS_PER_TICK if len(calls) == 1 else 0,
                "queued_actions": [],
                "stop_reason": "max_actions_per_tick" if len(calls) == 1 else "no_action",
                "current_action": None,
            }

        with (
            mock.patch.object(router, "_router_daemon_fill_action_queue", side_effect=fake_queue),
            mock.patch.object(router.time, "sleep") as sleep_mock,
        ):
            result = router.run_router_daemon(root, max_ticks=2, release_lock_on_exit=True)

        self.assertEqual(result["tick_count"], 2)
        self.assertEqual(len(calls), 2)
        sleep_mock.assert_not_called()
    def test_router_daemon_sleeps_after_real_queue_wait(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)

        def fake_queue(project_root: Path, run_root: Path, run_state: dict) -> dict:
            del project_root, run_root, run_state
            return {
                "queued_count": 1,
                "queued_actions": [],
                "stop_reason": "barrier",
                "current_action": None,
            }

        with (
            mock.patch.object(router, "_router_daemon_fill_action_queue", side_effect=fake_queue),
            mock.patch.object(router.time, "sleep") as sleep_mock,
        ):
            result = router.run_router_daemon(root, max_ticks=2, release_lock_on_exit=True)

        self.assertEqual(result["tick_count"], 2)
        sleep_mock.assert_called_once_with(router.ROUTER_DAEMON_TICK_SECONDS)
    def test_true_barriers_still_stop_scheduler_queueing(self) -> None:
        root = self.make_project()
        run_root = root / "run"
        run_root.mkdir(parents=True)
        run_state = {"run_id": "test-run"}

        cases = (
            (
                "open_startup_intake_ui",
                {"requires_host_automation": True, "requires_payload": "startup_intake_result"},
            ),
            (
                "await_card_return_event",
                {"expected_return_path": "mailbox/outbox/card_acks/test.ack.json"},
            ),
        )

        for action_type, extra in cases:
            with self.subTest(action_type=action_type):
                action = router.make_action(
                    action_type=action_type,
                    actor="bootloader" if action_type != "await_card_return_event" else "controller",
                    label=f"test_{action_type}",
                    summary=f"Test true scheduler barrier for {action_type}.",
                    extra=extra,
                )
                prepared = router._prepare_router_scheduled_action(root, run_root, run_state, action)  # type: ignore[attr-defined]
                self.assertEqual(prepared["router_scheduler_progress_class"], "true_barrier")
                self.assertNotEqual(prepared["router_scheduler_barrier_kind"], "none")
                self.assertFalse(router._router_daemon_can_continue_after_enqueued_action(prepared))  # type: ignore[attr-defined]
    def test_runtime_ledgers_remain_valid_json_after_repeated_daemon_writes(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)

        for _ in range(3):
            result = router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)
            self.assertEqual(result["tick_count"], 1)
            for path in (
                run_root / "runtime" / "router_scheduler_ledger.json",
                run_root / "runtime" / "controller_action_ledger.json",
                run_root / "runtime" / "router_daemon_status.json",
                run_root / "runtime" / "router_daemon.lock",
            ):
                payload = read_json(path)
                self.assertIsInstance(payload, dict)
    def test_runtime_json_dead_owner_write_lock_is_replaced_with_takeover_record(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        state = read_json(router.run_state_path(run_root))
        scheduler_path = run_root / "runtime" / "router_scheduler_ledger.json"
        write_lock = router._json_write_lock_path(scheduler_path)  # type: ignore[attr-defined]
        write_lock.write_text(
            json.dumps(
                {
                    "schema_version": "flowpilot.runtime_json_write_lock.v1",
                    "path": str(scheduler_path),
                    "pid": 0,
                    "created_at": router.utc_now(),
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        liveness = router._json_write_lock_liveness(scheduler_path)  # type: ignore[attr-defined]
        self.assertEqual(liveness["classification"], "dead_owner_takeover")
        self.assertTrue(liveness["takeover_allowed"])
        router.write_json(scheduler_path, router._empty_router_scheduler_ledger(root, run_root, state))  # type: ignore[attr-defined]

        self.assertFalse(write_lock.exists())
        takeover_log_path = router._json_write_lock_takeover_log_path(scheduler_path)  # type: ignore[attr-defined]
        records = [json.loads(line) for line in takeover_log_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(records[-1]["classification"], "dead_owner_takeover")
        self.assertEqual(read_json(scheduler_path)["schema_version"], router.ROUTER_SCHEDULER_LEDGER_SCHEMA)

    def test_runtime_json_self_owned_stale_write_lock_is_safely_recovered(self) -> None:
        root = self.make_project()
        path = root / "runtime" / "controller_action_ledger.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"schema_version": "flowpilot.controller_action_ledger.v1"}) + "\n", encoding="utf-8")
        write_lock = router_io._json_write_lock_path(path)  # type: ignore[attr-defined]
        write_lock.write_text(
            json.dumps(
                {
                    "schema_version": "flowpilot.runtime_json_write_lock.v1",
                    "path": str(path),
                    "pid": os.getpid(),
                    "created_at": router.utc_now(),
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        stale_time = time.time() - router_io_locks.RUNTIME_JSON_WRITE_LOCK_STALE_SECONDS - 5.0
        os.utime(write_lock, (stale_time, stale_time))

        liveness = router_io._json_write_lock_liveness(path)  # type: ignore[attr-defined]
        self.assertEqual(liveness["classification"], "self_owned_stale_takeover")
        self.assertTrue(liveness["takeover_allowed"])
        router_io.write_json_atomic(path, {"schema_version": "flowpilot.controller_action_ledger.v1", "ok": True})

        self.assertFalse(write_lock.exists())
        self.assertTrue(read_json(path)["ok"])
        takeover_log_path = router_io._json_write_lock_takeover_log_path(path)  # type: ignore[attr-defined]
        records = [json.loads(line) for line in takeover_log_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(records[-1]["classification"], "self_owned_stale_takeover")
        self.assertTrue(records[-1]["owner_is_self"])
        self.assertTrue(records[-1]["target_valid_json"])
        self.assertFalse(records[-1]["tmp_artifact_present"])

    def test_runtime_json_self_owned_completed_write_lock_is_safely_recovered(self) -> None:
        root = self.make_project()
        path = root / "runtime" / "controller_action_ledger.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"schema_version": "flowpilot.controller_action_ledger.v1"}) + "\n", encoding="utf-8")
        initial_signature = router_io._runtime_json_target_signature(path)  # type: ignore[attr-defined]
        write_lock = router_io._json_write_lock_path(path)  # type: ignore[attr-defined]
        write_lock.write_text(
            json.dumps(
                {
                    "schema_version": "flowpilot.runtime_json_write_lock.v1",
                    "path": str(path),
                    "pid": os.getpid(),
                    "target_initial_signature": initial_signature,
                    "created_at": router.utc_now(),
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        path.write_text(
            json.dumps({"schema_version": "flowpilot.controller_action_ledger.v1", "completed": True}) + "\n",
            encoding="utf-8",
        )

        liveness = router_io._json_write_lock_liveness(path)  # type: ignore[attr-defined]
        self.assertEqual(liveness["classification"], "self_owned_completed_write_takeover")
        self.assertTrue(liveness["takeover_allowed"])
        self.assertTrue(liveness["target_signature_changed"])
        router_io.write_json_atomic(path, {"schema_version": "flowpilot.controller_action_ledger.v1", "ok": True})

        self.assertFalse(write_lock.exists())
        self.assertTrue(read_json(path)["ok"])
        takeover_log_path = router_io._json_write_lock_takeover_log_path(path)  # type: ignore[attr-defined]
        records = [json.loads(line) for line in takeover_log_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(records[-1]["classification"], "self_owned_completed_write_takeover")
        self.assertTrue(records[-1]["target_signature_changed"])

    def test_runtime_json_fresh_self_owned_write_lock_is_not_stolen(self) -> None:
        root = self.make_project()
        path = root / "runtime" / "router_scheduler_ledger.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"schema_version": router.ROUTER_SCHEDULER_LEDGER_SCHEMA}) + "\n", encoding="utf-8")
        write_lock = router_io._json_write_lock_path(path)  # type: ignore[attr-defined]
        write_lock.write_text(
            json.dumps(
                {
                    "schema_version": "flowpilot.runtime_json_write_lock.v1",
                    "path": str(path),
                    "pid": os.getpid(),
                    "created_at": router.utc_now(),
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        with mock.patch.object(router_io_locks, "RUNTIME_JSON_WRITE_LOCK_TIMEOUT_SECONDS", 0.02), mock.patch.object(
            router_io_locks,
            "RUNTIME_JSON_WRITE_LOCK_POLL_SECONDS",
            0.001,
        ):
            with self.assertRaises(router.RouterLedgerWriteInProgress) as raised:
                router_io.write_json_atomic(path, {"schema_version": router.ROUTER_SCHEDULER_LEDGER_SCHEMA})

        self.assertEqual(raised.exception.write_lock["classification"], "active_self_owner")
        self.assertFalse(raised.exception.write_lock["takeover_allowed"])
        self.assertTrue(write_lock.exists())

    def test_runtime_json_self_owned_stale_lock_with_temp_artifact_is_not_cleared(self) -> None:
        root = self.make_project()
        path = root / "runtime" / "router_scheduler_ledger.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"schema_version": router.ROUTER_SCHEDULER_LEDGER_SCHEMA}) + "\n", encoding="utf-8")
        write_lock = router_io._json_write_lock_path(path)  # type: ignore[attr-defined]
        write_lock.write_text(
            json.dumps(
                {
                    "schema_version": "flowpilot.runtime_json_write_lock.v1",
                    "path": str(path),
                    "pid": os.getpid(),
                    "created_at": router.utc_now(),
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        tmp_path = path.parent / ".tmp-test-self-owned-lock.json"
        tmp_path.write_text("partial", encoding="utf-8")
        stale_time = time.time() - router_io_locks.RUNTIME_JSON_WRITE_LOCK_STALE_SECONDS - 5.0
        os.utime(write_lock, (stale_time, stale_time))

        with mock.patch.object(router_io_locks, "RUNTIME_JSON_WRITE_LOCK_TIMEOUT_SECONDS", 0.02), mock.patch.object(
            router_io_locks,
            "RUNTIME_JSON_WRITE_LOCK_POLL_SECONDS",
            0.001,
        ):
            with self.assertRaises(router.RouterLedgerWriteInProgress) as raised:
                router_io.write_json_atomic(path, {"schema_version": router.ROUTER_SCHEDULER_LEDGER_SCHEMA})

        self.assertEqual(raised.exception.write_lock["classification"], "self_owned_stale_unsafe")
        self.assertFalse(raised.exception.write_lock["takeover_allowed"])
        self.assertTrue(raised.exception.write_lock["tmp_artifact_present"])
        self.assertTrue(write_lock.exists())

    def test_runtime_json_lock_cleanup_failure_is_recorded(self) -> None:
        root = self.make_project()
        path = root / "runtime" / "router_scheduler_ledger.json"

        with mock.patch.object(router_io_locks, "RUNTIME_JSON_WRITE_LOCK_CLEANUP_RETRY_SECONDS", 0.01), mock.patch.object(
            router_io_locks,
            "RUNTIME_JSON_WRITE_LOCK_POLL_SECONDS",
            0.001,
        ), mock.patch.object(
            router_io_locks,
            "_unlink_runtime_json_write_lock",
            side_effect=PermissionError("scanner still has the lock"),
        ):
            router_io.write_json_atomic(path, {"schema_version": router.ROUTER_SCHEDULER_LEDGER_SCHEMA})

        cleanup_log_path = router_io._json_write_lock_cleanup_log_path(path)  # type: ignore[attr-defined]
        records = [json.loads(line) for line in cleanup_log_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(records[-1]["phase"], "write_json_atomic_finally")
        self.assertEqual(records[-1]["error_type"], "PermissionError")
        self.assertTrue(records[-1]["target_verified"])
        self.assertTrue(records[-1]["target_valid_json"])
        self.assertTrue(router_io._json_write_lock_path(path).exists())  # type: ignore[attr-defined]

    def test_router_daemon_corrupted_scheduler_ledger_writes_error_status(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        scheduler_path = run_root / "runtime" / "router_scheduler_ledger.json"
        scheduler_path.write_text(
            '{"schema_version": "flowpilot.router_scheduler_ledger.v1"}\nBROKEN',
            encoding="utf-8",
        )

        with self.assertRaises(router.RouterLedgerCorruptionError):
            router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)

        lock = read_json(run_root / "runtime" / "router_daemon.lock")
        status = read_json(run_root / "runtime" / "router_daemon_status.json")
        self.assertEqual(lock["status"], "error")
        self.assertEqual(status["lifecycle_status"], "daemon_error")
        self.assertFalse(status["daemon_live"])
        self.assertEqual(status["error"]["type"], "RouterLedgerCorruptionError")
        self.assertFalse(status["router_scheduler_ledger"]["valid_json"])
    def test_router_daemon_waits_on_fresh_scheduler_write_lock_before_error(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        state = read_json(router.run_state_path(run_root))
        scheduler_path = run_root / "runtime" / "router_scheduler_ledger.json"
        scheduler_path.write_text(
            '{"schema_version": "flowpilot.router_scheduler_ledger.v1"}\nBROKEN',
            encoding="utf-8",
        )
        write_lock = router._json_write_lock_path(scheduler_path)  # type: ignore[attr-defined]
        write_lock.write_text(
            json.dumps(
                {
                    "schema_version": "flowpilot.runtime_json_write_lock.v1",
                    "path": str(scheduler_path),
                    "pid": os.getpid(),
                    "created_at": router.utc_now(),
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        def finish_write() -> None:
            time.sleep(0.5)
            ledger = router._empty_router_scheduler_ledger(root, run_root, state)  # type: ignore[attr-defined]
            scheduler_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            unlink_with_windows_retry(write_lock)

        thread = threading.Thread(target=finish_write, daemon=True)
        thread.start()
        result = router.run_router_daemon(root, max_ticks=2, observe_only=True, release_lock_on_exit=True)
        thread.join(timeout=1.0)

        self.assertEqual(result["tick_count"], 2)
        self.assertTrue(result["ticks"][0]["deferred"])
        self.assertEqual(result["ticks"][0]["defer_reason"], "runtime_ledger_write_in_progress")
        self.assertFalse(result["ticks"][1].get("deferred", False))
        self.assertEqual(read_json(scheduler_path)["schema_version"], router.ROUTER_SCHEDULER_LEDGER_SCHEMA)
    def test_atomic_replace_permission_error_becomes_runtime_write_wait(self) -> None:
        root = self.make_project()
        path = root / "runtime" / "router_scheduler_ledger.json"

        with mock.patch.object(router_io_locks, "RUNTIME_JSON_WRITE_LOCK_TIMEOUT_SECONDS", 0.02), mock.patch.object(
            router_io_locks,
            "RUNTIME_JSON_WRITE_LOCK_POLL_SECONDS",
            0.001,
        ), mock.patch.object(router_io_json.os, "replace", side_effect=PermissionError("locked by Windows")):
            with self.assertRaises(router.RouterLedgerWriteInProgress) as raised:
                router_io.write_json_atomic(path, {"schema_version": router.ROUTER_SCHEDULER_LEDGER_SCHEMA})

        self.assertEqual(raised.exception.path, path)
        self.assertFalse(router_io._json_write_lock_path(path).exists())

    def test_atomic_lock_acquire_retries_transient_windows_permission_error(self) -> None:
        root = self.make_project()
        path = root / "runtime" / "startup_state.json"
        original_open = router_io_locks.os.open
        calls = 0

        def transient_open(*args, **kwargs):  # type: ignore[no-untyped-def]
            nonlocal calls
            calls += 1
            if calls == 1:
                raise PermissionError("Windows writer is settling")
            return original_open(*args, **kwargs)

        with mock.patch.object(
            router_io_locks.os,
            "open",
            side_effect=transient_open,
        ), mock.patch.object(
            router_io_locks,
            "RUNTIME_JSON_WRITE_LOCK_POLL_SECONDS",
            0.001,
        ):
            router_io.write_json_atomic(
                path,
                {"schema_version": "flowpilot.startup_state.v1"},
            )

        self.assertGreaterEqual(calls, 2)
        self.assertEqual(
            read_json(path)["schema_version"],
            "flowpilot.startup_state.v1",
        )
        self.assertFalse(router_io._json_write_lock_path(path).exists())

    def test_atomic_lock_acquire_permission_error_fails_as_writer_contention(self) -> None:
        root = self.make_project()
        path = root / "runtime" / "startup_state.json"

        with mock.patch.object(
            router_io_locks.os,
            "open",
            side_effect=PermissionError("Windows writer never settled"),
        ), mock.patch.object(
            router_io_locks,
            "RUNTIME_JSON_WRITE_LOCK_TIMEOUT_SECONDS",
            0.01,
        ), mock.patch.object(
            router_io_locks,
            "RUNTIME_JSON_WRITE_LOCK_POLL_SECONDS",
            0.001,
        ):
            with self.assertRaises(router.RouterLedgerWriteInProgress) as raised:
                router_io.write_json_atomic(
                    path,
                    {"schema_version": "flowpilot.startup_state.v1"},
                )

        self.assertEqual(raised.exception.path, path)
        self.assertTrue(raised.exception.write_lock["acquire_permission_error"])
        self.assertEqual(
            raised.exception.write_lock["acquire_error_type"],
            "PermissionError",
        )

    def test_atomic_verify_permission_error_becomes_runtime_write_wait(self) -> None:
        root = self.make_project()
        path = root / "runtime" / "router_scheduler_ledger.json"
        original_read_json = router_io_json.read_json

        def flaky_readback(read_path: Path) -> dict:
            if read_path == path:
                raise PermissionError("scanner locked readback")
            return original_read_json(read_path)

        with mock.patch.object(router_io_json, "read_json", side_effect=flaky_readback):
            with self.assertRaises(router.RouterLedgerWriteInProgress) as raised:
                router_io.write_json_atomic(path, {"schema_version": router.ROUTER_SCHEDULER_LEDGER_SCHEMA})

        self.assertEqual(raised.exception.path, path)
        self.assertTrue(raised.exception.write_lock["verification_readback_error"])
        self.assertEqual(raised.exception.write_lock["verification_error_type"], "PermissionError")
        self.assertFalse(router_io._json_write_lock_path(path).exists())
        self.assertEqual(original_read_json(path)["schema_version"], router.ROUTER_SCHEDULER_LEDGER_SCHEMA)

    def test_readiness_reader_treats_windows_permission_error_as_not_ready(self) -> None:
        root = self.make_project()
        path = root / "runtime" / "router_daemon.lock"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"status":"active"}\n', encoding="utf-8")

        with mock.patch.object(
            router_io_json,
            "read_json",
            side_effect=PermissionError("Windows sharing violation"),
        ):
            self.assertEqual(router_io_json.read_json_if_valid(path), {})

    def test_formal_daemon_readiness_fails_closed_on_unavailable_lock(self) -> None:
        root = self.make_project()
        run_root = root / ".flowpilot" / "runs" / "run-readiness"
        lock = {
            "schema_version": router.ROUTER_DAEMON_LOCK_SCHEMA,
            "status": "active",
            "last_tick_at": router.utc_now(),
            "stale_after_seconds": router.ROUTER_DAEMON_LOCK_STALE_SECONDS,
            "owner": router._router_daemon_owner(),  # type: ignore[attr-defined]
        }
        status = {
            "schema_version": router.ROUTER_DAEMON_STATUS_SCHEMA,
            "daemon_mode_enabled": True,
            "tick_interval_seconds": router.ROUTER_DAEMON_TICK_SECONDS,
            "lock": {"live": True},
            "run_root": router.project_relative(root, run_root),
        }
        ledger = {"schema_version": router.CONTROLLER_ACTION_LEDGER_SCHEMA}

        with mock.patch.object(
            router,
            "read_json_if_valid",
            side_effect=[{}, status, ledger],
        ):
            self.assertFalse(router._formal_router_daemon_ready(root, run_root))
        with mock.patch.object(
            router,
            "read_json_if_valid",
            side_effect=[lock, status, ledger],
        ):
            self.assertTrue(router._formal_router_daemon_ready(root, run_root))
    def test_formal_daemon_start_timeout_cleans_tree_before_release(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-start-timeout")
        state = read_json(router.run_state_path(run_root))
        identity = {"pid": 616161, "start_token": "spawned-start-token"}
        instance_id = "spawned-daemon-instance"
        lock_path = run_root / "runtime" / "router_daemon.lock"
        call_order: list[str] = []

        def fake_spawn(project_root: Path, target_run_root: Path) -> dict:
            router.write_json(
                lock_path,
                {
                    "schema_version": router.ROUTER_DAEMON_LOCK_SCHEMA,
                    "run_id": state["run_id"],
                    "run_root": router.project_relative(project_root, target_run_root),
                    "status": "active",
                    "created_at": router.utc_now(),
                    "last_tick_at": router.utc_now(),
                    "owner": {
                        **identity,
                        "process_kind": "dedicated_daemon",
                        "daemon_instance_id": instance_id,
                    },
                },
            )
            return {
                "pid": identity["pid"],
                "process_identity": identity,
                "daemon_instance_id": instance_id,
                "stderr_path": "",
            }

        def cleanup_tree(target: dict, *, timeout_seconds: float) -> dict:
            del target, timeout_seconds
            call_order.append("cleanup")
            return {
                "cleanup_confirmed": True,
                "descendant_zero_confirmed": True,
                "remaining_live_identities": [],
                "reason": "process_tree_exited",
            }

        original_release = router._release_router_daemon_lock  # type: ignore[attr-defined]

        def release_after_cleanup(*args, **kwargs):
            call_order.append("release")
            return original_release(*args, **kwargs)

        with mock.patch.object(router, "_formal_router_daemon_ready", return_value=False), mock.patch.object(
            router,
            "_spawn_startup_router_daemon_process",
            side_effect=fake_spawn,
        ), mock.patch.object(
            router,
            "_terminate_process_tree",
            side_effect=cleanup_tree,
        ), mock.patch.object(
            router,
            "_release_router_daemon_lock",
            side_effect=release_after_cleanup,
        ), mock.patch.object(
            router,
            "ROUTER_DAEMON_STARTUP_TIMEOUT_SECONDS",
            0.0,
        ):
            with self.assertRaisesRegex(router.RouterError, "failed readiness check"):
                router._start_or_attach_formal_router_daemon(root, run_root, state)  # type: ignore[attr-defined]

        self.assertEqual(call_order, ["cleanup", "release"])
        released = read_json(lock_path)
        self.assertEqual(released["status"], "released")
        self.assertTrue(released["cleanup_proof"]["cleanup_confirmed"])

    def test_foreground_retry_reattaches_current_inflight_daemon_without_second_spawn(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-inflight-daemon-retry")
        state = read_json(router.run_state_path(run_root))
        identity = {"pid": 717171, "start_token": "inflight-start-token"}
        daemon_instance_id = "inflight-daemon-instance"
        router._append_router_daemon_event(  # type: ignore[attr-defined]
            run_root,
            "formal_router_daemon_process_opened",
            {
                "process_identity": identity,
                "process_launch_plan": {
                    "kind": "windows_venv_direct_base_owner",
                },
                "daemon_instance_id": daemon_instance_id,
                "command": ["python", "flowpilot_router.py", "daemon"],
                "stdout_path": router.project_relative(
                    root,
                    run_root / "runtime" / "router_daemon.startup.out.txt",
                ),
                "stderr_path": router.project_relative(
                    root,
                    run_root / "runtime" / "router_daemon.startup.err.txt",
                ),
            },
        )

        with mock.patch.object(
            router,
            "_process_identity_is_live",
            return_value=True,
        ), mock.patch.object(
            router,
            "_formal_router_daemon_ready",
            side_effect=[False, True, True],
        ), mock.patch.object(
            router,
            "_spawn_startup_router_daemon_process",
        ) as spawn:
            result = router_daemon_runtime._start_or_attach_formal_router_daemon(
                router,
                root,
                run_root,
                state,
            )

        spawn.assert_not_called()
        self.assertFalse(result["attached_existing_daemon"])
        self.assertEqual(result["spawn_info"]["process_identity"], identity)
        self.assertEqual(
            result["spawn_info"]["daemon_instance_id"],
            daemon_instance_id,
        )

    def test_router_daemon_nested_state_write_lock_wait_does_not_exit(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        state_path = router.run_state_path(run_root)
        tick_exc = router.RouterLedgerWriteInProgress(
            run_root / "runtime" / "router_scheduler_ledger.json",
            {"active": True, "classification": "active_live_owner", "path": "scheduler.write.lock"},
            "scheduler write in progress",
        )
        nested_exc = router.RouterLedgerWriteInProgress(
            state_path,
            {"active": True, "classification": "active_live_owner", "path": str(state_path) + ".write.lock"},
            "state write in progress",
        )
        original_save = router.save_run_state
        save_count = 0

        def flaky_save(path: Path, payload: dict) -> None:
            nonlocal save_count
            save_count += 1
            if save_count == 1:
                original_save(path, payload)
                return
            raise nested_exc

        with mock.patch.object(router, "_router_daemon_tick", side_effect=tick_exc), mock.patch.object(
            router,
            "save_run_state",
            side_effect=flaky_save,
        ):
            result = router.run_router_daemon(root, max_ticks=1, observe_only=True, release_lock_on_exit=True)

        self.assertEqual(result["tick_count"], 1)
        self.assertTrue(result["ticks"][0]["deferred"])
        self.assertEqual(result["ticks"][0]["defer_reason"], "runtime_ledger_write_in_progress")
        self.assertEqual(result["ticks"][0]["nested_defer_reason"], "runtime_ledger_write_status_save_in_progress")
        lock = read_json(run_root / "runtime" / "router_daemon.lock")
        self.assertNotEqual(lock.get("status"), "error")
    def test_terminal_startup_daemon_schedule_does_not_append_boot_rows(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)
        router.apply_action(root, "start_router_daemon")
        scheduler_path = run_root / "runtime" / "router_scheduler_ledger.json"
        router.record_external_event(root, "user_requests_run_stop", {"reason": "test terminal startup guard"})
        state = read_json(router.run_state_path(run_root))
        before_rows = list(read_json(scheduler_path)["rows"])

        result = router._startup_daemon_schedule_bootloader_action(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test_terminal_startup_guard",
        )

        after_rows = read_json(scheduler_path)["rows"]
        self.assertFalse(result["scheduled"])
        self.assertTrue(result["terminal"])
        self.assertEqual(result["reason"], "terminal_lifecycle")
        self.assertEqual(len(after_rows), len(before_rows))
        self.assertFalse(
            any(
                row.get("action_type") == "open_startup_intake_ui"
                and row.get("router_state") in {"queued", "waiting"}
                for row in after_rows
            )
        )
    def test_dedicated_daemon_terminal_mark_waits_for_process_exit_cleanup(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-terminal-exit-pending")
        state = read_json(router.run_state_path(run_root))
        router._acquire_router_daemon_lock(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            process_kind="dedicated_daemon",
            daemon_instance_id="test-current-dedicated",
        )

        router._mark_router_daemon_terminal(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            reason="test_terminal",
        )

        pending = read_json(run_root / "runtime" / "router_daemon.lock")
        self.assertEqual(pending["status"], "terminal_exit_pending")
        self.assertNotIn("released_at", pending)
        stopped = router.stop_router_daemon(root, reason="test_terminal_cleanup", run_root=run_root)
        self.assertEqual(stopped["lock_status"], "released")
        self.assertTrue(stopped["process_cleanup"]["descendant_zero_confirmed"])
    def test_router_daemon_status_not_active_after_error_lock_or_missing_pid(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        state = read_json(router.run_state_path(run_root))
        base_lock = {
            "schema_version": router.ROUTER_DAEMON_LOCK_SCHEMA,
            "run_id": state.get("run_id"),
            "run_root": router.project_relative(root, run_root),
            "created_at": router.utc_now(),
            "last_tick_at": router.utc_now(),
            "tick_interval_seconds": router.ROUTER_DAEMON_TICK_SECONDS,
            "stale_after_seconds": router.ROUTER_DAEMON_LOCK_STALE_SECONDS,
            "owner": router._router_daemon_owner(),  # type: ignore[attr-defined]
        }

        error_status = router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            lock={**base_lock, "status": "error"},
        )
        self.assertEqual(error_status["lifecycle_status"], "daemon_error")
        self.assertFalse(error_status["lock"]["live"])

        missing_pid_status = router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            lock={
                **base_lock,
                "status": "active",
                "owner": {"pid": 999999999, "process_name": "missing-test-daemon"},
            },
        )
        self.assertEqual(missing_pid_status["lifecycle_status"], "daemon_stale_or_missing")
        self.assertFalse(missing_pid_status["lock"]["process_live"])
        self.assertFalse(missing_pid_status["daemon_live"])
