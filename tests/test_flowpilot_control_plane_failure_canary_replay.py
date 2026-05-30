from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase

import flowpilot_router_io_locks as router_io_locks  # noqa: E402
from scripts.test_tier import background as test_tier_background  # noqa: E402


class FlowPilotControlPlaneFailureCanaryReplayTests(FlowPilotRouterRuntimeTestBase):
    def test_canary_fresh_scheduler_write_lock_waits_then_recovers(self) -> None:
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
            time.sleep(0.05)
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
        self.assertFalse(write_lock.exists())

    def test_canary_corrupt_scheduler_ledger_marks_daemon_error_not_live(self) -> None:
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

    def test_canary_dead_daemon_resume_restart_path_before_normal_work(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        lock_path = run_root / "runtime" / "router_daemon.lock"
        lock = read_json(lock_path)
        lock["last_tick_at"] = "2000-01-01T00:00:00Z"
        lock["owner"] = {"pid": 999999999, "process_name": "missing-test-daemon"}
        router.write_json(lock_path, lock)

        router.record_external_event(root, "heartbeat_or_manual_resume_requested")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_resume_state")
        recovery = action["router_daemon_resume_recovery"]
        self.assertFalse(recovery["router_daemon_lock_live"])
        self.assertFalse(recovery["router_daemon_owner_process_live"])
        self.assertEqual(recovery["decision"], "restart_router_daemon_from_current_state")

        router.apply_action(root, "load_resume_state")
        resume_evidence = read_json(run_root / "continuation" / "resume_reentry.json")
        self.assertTrue(resume_evidence["router_daemon_liveness_checked"])
        self.assertTrue(resume_evidence["router_daemon_restarted_if_dead"])
        self.assertTrue(resume_evidence["controller_action_ledger_loaded"])

    def test_canary_duplicate_heartbeat_resume_is_idempotent(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        router.record_external_event(root, "heartbeat_or_manual_resume_requested")
        first_action = router.next_action(root)
        router.record_external_event(root, "heartbeat_or_manual_resume_requested")
        second_action = router.next_action(root)

        self.assertEqual(first_action["action_type"], "load_resume_state")
        self.assertEqual(second_action["action_type"], "load_resume_state")
        self.assertEqual(second_action["router_daemon_resume_recovery"]["decision"], "attach_controller_to_live_daemon")
        router.apply_action(root, "load_resume_state")
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["resume_state_loaded"])
        resume_evidence = read_json(run_root / "continuation" / "resume_reentry.json")
        self.assertTrue(resume_evidence["router_daemon_liveness_checked"])
        next_action = self.next_after_display_sync(root)
        self.assertEqual(next_action["action_type"], "rehydrate_role_bindings")
        router.stop_router_daemon(root, reason="test_cleanup")

    def test_canary_peer_run_stop_does_not_mutate_current_run(self) -> None:
        root = self.make_project()
        run_a = self.write_minimal_run(root, "run-a")
        run_b = self.write_minimal_run(root, "run-b")
        self.write_current_focus(root, run_b)
        state_a = read_json(router.run_state_path(run_a))
        state_b = read_json(router.run_state_path(run_b))
        router._acquire_router_daemon_lock(root, run_a, state_a)  # type: ignore[attr-defined]
        router._acquire_router_daemon_lock(root, run_b, state_b)  # type: ignore[attr-defined]

        stopped = router.stop_router_daemon(root, reason="control_plane_canary_peer_stop", run_root=run_a)

        self.assertEqual(stopped["run_id"], "run-a")
        self.assertEqual(read_json(root / ".flowpilot" / "current.json")["current_run_id"], "run-b")
        self.assertEqual(read_json(run_a / "runtime" / "router_daemon.lock")["status"], "released")
        self.assertEqual(read_json(run_b / "runtime" / "router_daemon.lock")["status"], "active")
        self.assertFalse(read_json(router.run_state_path(run_a))["daemon_mode_enabled"])
        self.assertTrue(read_json(router.run_state_path(run_b))["daemon_mode_enabled"])

    def test_canary_progress_only_background_artifact_is_not_standard_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-control-canary-bg-") as tmp_name:
            root = Path(tmp_name)
            paths = test_tier_background.artifact_paths(root, "control_plane_canary_background")
            paths["combined"].parent.mkdir(parents=True, exist_ok=True)
            paths["combined"].write_text("model regression still running\n", encoding="utf-8")

            progress = test_tier_background.classify_background_artifact(root, "control_plane_canary_background")
            self.assertEqual(progress["status"], "progress_only")
            self.assertFalse(progress["ok"])
            self.assertIn("missing_exit", progress["reasons"])

            paths["out"].write_text("model regression passed\n", encoding="utf-8")
            paths["err"].write_text("", encoding="utf-8")
            paths["combined"].write_text("model regression passed\n", encoding="utf-8")
            paths["exit"].write_text("0\n", encoding="utf-8")
            paths["meta"].write_text(
                json.dumps(
                    {
                        "name": "control_plane_canary_background",
                        "status": "passed",
                        "exit_code": 0,
                        "proof_reused": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            final = test_tier_background.classify_background_artifact(root, "control_plane_canary_background")
            self.assertEqual(final["status"], "passed")
            self.assertTrue(final["ok"])
            self.assertEqual(final["exit_code"], 0)

    def test_canary_stop_fence_survives_scheduler_lock(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        scheduler_path = run_root / "runtime" / "router_scheduler_ledger.json"
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

        with mock.patch.object(router_io_locks, "RUNTIME_JSON_WRITE_LOCK_TIMEOUT_SECONDS", 0.01):
            result = router.record_external_event(root, "user_requests_run_stop", {"reason": "control-plane canary"})

        self.assertTrue(result["ok"])
        state = read_json(router.run_state_path(run_root))
        lock = read_json(run_root / "runtime" / "router_daemon.lock")
        status = read_json(run_root / "runtime" / "router_daemon_status.json")
        fence = read_json(run_root / "lifecycle" / "terminal_fence.json")
        self.assertEqual(state["status"], "stopped_by_user")
        self.assertFalse(state["daemon_mode_enabled"])
        self.assertEqual(lock["status"], "terminal_stopped")
        self.assertEqual(status["lifecycle_status"], "terminal_stopped")
        self.assertFalse(status["daemon_live"])
        self.assertEqual(fence["controller_work_fence"]["status"], "best_effort_failed")
        self.assertEqual(fence["controller_work_fence"]["error"]["type"], "RouterLedgerWriteInProgress")
        write_lock.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
