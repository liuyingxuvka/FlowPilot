from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class ForegroundControllerRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_controller_route_memory_is_refreshed_and_required_for_pm_route_draft(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        history_path = run_root / "route_memory" / "route_history_index.json"
        context_path = run_root / "route_memory" / "pm_prior_path_context.json"
        self.assertTrue(history_path.exists())
        self.assertTrue(context_path.exists())
        history = read_json(history_path)
        context = read_json(context_path)
        self.assertEqual(history["schema_version"], "flowpilot.route_history_index.v1")
        self.assertEqual(context["schema_version"], "flowpilot.pm_prior_path_context.v1")
        self.assertEqual(history["generated_by"], "controller")
        self.assertFalse(history["sealed_packet_or_result_bodies_read"])
        self.assertFalse(context["controller_decision_authority"])

        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)
        self.complete_child_skill_gates(root)

        action = self.deliver_expected_card(root, "pm.prior_path_context")
        self.assertTrue(action["pm_prior_path_context_required_for_decision"])
        self.assertEqual(
            action["pm_context_paths"]["pm_prior_path_context"],
            self.rel(root, context_path),
        )

        self.deliver_expected_card(root, "pm.route_skeleton")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_route_draft", {"nodes": [{"node_id": "node-001"}]})

        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "nodes": [{"node_id": "node-001"}],
                **self.prior_path_context_review(root, "Route draft used current Controller route-memory indexes."),
            },
        )
        draft = read_json(run_root / "routes" / "route-001" / "flow.draft.json")
        self.assertEqual(draft["prior_path_context_review"]["source_paths"][0], self.rel(root, context_path))
    def test_controller_next_action_reuses_fresh_route_memory(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        history_path = run_root / "route_memory" / "route_history_index.json"
        context_path = run_root / "route_memory" / "pm_prior_path_context.json"
        history_before = read_json(history_path)
        context_before = read_json(context_path)

        action = router.next_action(root)

        self.assertEqual(action["action_type"], "sync_display_plan")
        self.assertEqual(read_json(history_path), history_before)
        self.assertEqual(read_json(context_path), context_before)
    def test_controller_action_summary_separates_done_history_from_active_work(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-a")
        ledger_path = run_root / "runtime" / "controller_action_ledger.json"
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        router.write_json(
            ledger_path,
            {
                "schema_version": router.CONTROLLER_ACTION_LEDGER_SCHEMA,
                "run_id": "run-a",
                "run_root": ".flowpilot/runs/run-a",
                "updated_at": router.utc_now(),
                "actions": [{"action_id": "action-1", "action_type": "open_startup_intake_ui", "status": "done"}],
            },
        )

        summary = router._controller_action_ledger_summary(run_root)  # type: ignore[attr-defined]

        self.assertEqual(summary["history_done_count"], 1)
        self.assertEqual(summary["active_work_count"], 0)
        self.assertEqual(summary["pending_action_ids"], [])
        self.assertEqual(summary["waiting_action_ids"], [])
    def test_passive_wait_projection_is_not_ordinary_controller_work(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)

        self.force_startup_fact_role_wait(root)

        ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        ordinary_types = [item.get("action_type") for item in ledger["actions"]]
        passive_types = [item.get("action_type") for item in ledger["passive_waits"]]
        self.assertNotIn("await_role_decision", ordinary_types)
        self.assertIn("await_role_decision", passive_types)
        self.assertTrue(ledger["controller_actions_are_executable_only"])
        self.assertTrue(ledger["passive_waits_projected_via_status_not_work_board"])
        summary = router._controller_action_ledger_summary(run_root)  # type: ignore[attr-defined]
        self.assertEqual(summary["passive_wait_count"], 1)
        self.assertEqual(summary["active_work_count"], 0)
    def test_router_daemon_tick_writes_controller_action_ledger_and_receipt_reconciles(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)

        result = router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)

        self.assertEqual(result["tick_count"], 1)
        action_id = result["ticks"][0]["controller_action_id"]
        self.assertTrue(action_id)
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{action_id}.json")
        self.assertEqual(action_record["schema_version"], router.CONTROLLER_ACTION_SCHEMA)
        self.assertIn(action_record["status"], {"pending", "waiting"})
        receipt_result = router.record_controller_action_receipt(
            root,
            action_id=action_id,
            status="done",
            payload={"test_receipt": True},
        )
        self.assertTrue(receipt_result["ok"])
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{action_id}.json")
        self.assertEqual(action_record["status"], "done")
        ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        self.assertGreaterEqual(ledger["counts"]["done"], 1)
    def test_reconciled_controller_action_backfills_receipt_done_scheduler_row(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        row = next(item for item in controller_ledger["actions"] if item.get("action_type") == "start_role_slots")
        action_path = run_root / "runtime" / "controller_actions" / f"{row['action_id']}.json"
        action_record = read_json(action_path)
        self.assertEqual(action_record["router_reconciliation_status"], "reconciled")

        scheduler_path = run_root / "runtime" / "router_scheduler_ledger.json"
        scheduler = read_json(scheduler_path)
        scheduler_row = next(item for item in scheduler["rows"] if item.get("row_id") == row["router_scheduler_row_id"])
        scheduler_row["router_state"] = "receipt_done"
        scheduler_row.pop("reconciled_at", None)
        router.write_json(scheduler_path, scheduler)

        result = router._reconcile_scheduled_controller_action_receipts(root, run_root, state)  # type: ignore[attr-defined]

        self.assertTrue(result["changed"])
        refreshed_scheduler = read_json(scheduler_path)
        refreshed_row = next(
            item for item in refreshed_scheduler["rows"] if item.get("row_id") == row["router_scheduler_row_id"]
        )
        self.assertEqual(refreshed_row["router_state"], "reconciled")
        self.assertEqual(refreshed_row["reconciliation"]["source"], "startup_bootloader_controller_receipt")
        self.assertEqual(
            refreshed_row["reconciliation"]["scheduler_backfill_source"],
            "reconciled_controller_action_scheduler_backfill",
        )
    def test_foreground_next_waits_on_fresh_controller_action_write_lock(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        action_path = sorted((run_root / "runtime" / "controller_actions").glob("*.json"))[0]
        original_entry = read_json(action_path)
        action_path.write_text(
            '{"schema_version": "flowpilot.controller_action.v1"}\nBROKEN',
            encoding="utf-8",
        )
        write_lock = router._json_write_lock_path(action_path)  # type: ignore[attr-defined]
        write_lock.write_text(
            json.dumps(
                {
                    "schema_version": "flowpilot.runtime_json_write_lock.v1",
                    "path": str(action_path),
                    "created_at": router.utc_now(),
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        def finish_write() -> None:
            time.sleep(0.5)
            action_path.write_text(json.dumps(original_entry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            unlink_with_windows_retry(write_lock)

        thread = threading.Thread(target=finish_write, daemon=True)
        thread.start()
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = router.main(["--root", str(root), "next", "--json"])
        thread.join(timeout=1.0)

        self.assertEqual(exit_code, 0, stdout.getvalue())
        result = json.loads(stdout.getvalue())
        self.assertTrue(result["runtime_write_settlement"]["waited"])
        self.assertEqual(result["runtime_write_settlement"]["command"], "next")
        self.assertGreaterEqual(result["runtime_write_settlement"]["wait_count"], 1)
        self.assertEqual(read_json(action_path)["schema_version"], router.CONTROLLER_ACTION_SCHEMA)
    def test_foreground_next_waits_on_stale_lock_when_owner_process_is_live(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        action_path = sorted((run_root / "runtime" / "controller_actions").glob("*.json"))[0]
        original_entry = read_json(action_path)
        action_path.write_text(
            '{"schema_version": "flowpilot.controller_action.v1"}\nBROKEN',
            encoding="utf-8",
        )
        write_lock = router._json_write_lock_path(action_path)  # type: ignore[attr-defined]
        write_lock.write_text(
            json.dumps(
                {
                    "schema_version": "flowpilot.runtime_json_write_lock.v1",
                    "path": str(action_path),
                    "pid": os.getpid(),
                    "created_at": router.utc_now(),
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        old = time.time() - router.RUNTIME_JSON_WRITE_LOCK_STALE_SECONDS - 5.0
        os.utime(write_lock, (old, old))

        def finish_write() -> None:
            time.sleep(0.5)
            action_path.write_text(json.dumps(original_entry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            unlink_with_windows_retry(write_lock)

        thread = threading.Thread(target=finish_write, daemon=True)
        thread.start()
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = router.main(["--root", str(root), "next", "--json"])
        thread.join(timeout=1.0)

        self.assertEqual(exit_code, 0, stdout.getvalue())
        result = json.loads(stdout.getvalue())
        self.assertTrue(result["runtime_write_settlement"]["waited"])
        self.assertTrue(result["runtime_write_settlement"]["waits"][0]["initial_liveness"]["owner_process_live"])
        self.assertEqual(read_json(action_path)["schema_version"], router.CONTROLLER_ACTION_SCHEMA)
    def test_controller_boundary_done_receipt_reclaims_router_postcondition(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        run_root, state, action = self.legacy_controller_boundary_action(root)
        self.assertEqual(action["action_type"], "confirm_controller_core_boundary")
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router._write_controller_boundary_confirmation(root, run_root, state)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)

        receipt = router.record_controller_action_receipt(
            root,
            action_id=entry["action_id"],
            status="done",
            payload={"controller_action_completed": True},
        )

        self.assertTrue(receipt["ok"])
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["controller_role_confirmed"])
        self.assertTrue(state["flags"]["controller_boundary_confirmation_written"])
        self.assertTrue((run_root / "startup" / "controller_boundary_confirmation.json").exists())
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{entry['action_id']}.json")
        self.assertEqual(action_record["router_reconciliation_status"], "reconciled")
    def test_controller_boundary_projection_reclaims_stale_flags_without_pending_action(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        run_root, state, action = self.legacy_controller_boundary_action(root)
        self.assertEqual(action["action_type"], "confirm_controller_core_boundary")
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router._write_controller_boundary_confirmation(root, run_root, state)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)

        receipt = router.record_controller_action_receipt(
            root,
            action_id=entry["action_id"],
            status="done",
            payload={"controller_action_completed": True},
        )
        self.assertTrue(receipt["ok"])

        state = read_json(router.run_state_path(run_root))
        state["flags"]["controller_role_confirmed"] = False
        state["flags"]["controller_role_confirmed_from_router_core"] = False
        state["flags"]["controller_boundary_confirmation_written"] = False
        state["pending_action"] = None
        state.pop("controller_boundary_confirmation", None)
        router.save_run_state(run_root, state)

        next_action = self.next_after_display_sync(root)

        self.assertNotEqual(next_action["action_type"], "confirm_controller_core_boundary")
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["controller_role_confirmed"])
        self.assertTrue(state["flags"]["controller_role_confirmed_from_router_core"])
        self.assertTrue(state["flags"]["controller_boundary_confirmation_written"])
        self.assertNotEqual((state.get("pending_action") or {}).get("action_type"), "confirm_controller_core_boundary")
        labels = [item["label"] for item in state["history"] if isinstance(item, dict)]
        self.assertIn("router_reconciled_controller_boundary_projection", labels)
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{entry['action_id']}.json")
        self.assertEqual(action_record["router_reconciliation_status"], "reconciled")
        scheduler = read_json(run_root / "runtime" / "router_scheduler_ledger.json")
        row = next(item for item in scheduler["rows"] if item["row_id"] == action_record["router_scheduler_row_id"])
        self.assertEqual(row["router_state"], "reconciled")
    def test_controller_action_ledger_handles_multiple_receipts_and_duplicates(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))

        first_action = router.make_action(
            action_type="check_prompt_manifest",
            actor="controller",
            label="test_multi_action_first",
            summary="Test first ledger action.",
        )
        second_action = router.make_action(
            action_type="write_startup_mechanical_audit",
            actor="controller",
            label="test_multi_action_second",
            summary="Test dependent ledger action.",
            extra={"dependencies": ["test_multi_action_first"]},
        )
        blocked_action = router.make_action(
            action_type="write_display_surface_status",
            actor="controller",
            label="test_multi_action_blocked",
            summary="Test blocked ledger action.",
        )
        first = router._write_controller_action_entry(root, run_root, state, first_action)  # type: ignore[attr-defined]
        second = router._write_controller_action_entry(root, run_root, state, second_action)  # type: ignore[attr-defined]
        blocked = router._write_controller_action_entry(root, run_root, state, blocked_action)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)

        ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        baseline_done = int(ledger["counts"].get("done") or 0)
        baseline_blocked = int(ledger["counts"].get("blocked") or 0)
        self.assertEqual(ledger["counts"]["pending"], 3)
        second_record = read_json(run_root / "runtime" / "controller_actions" / f"{second['action_id']}.json")
        self.assertEqual(second_record["dependencies"], [])
        scheduler = read_json(run_root / "runtime" / "router_scheduler_ledger.json")
        second_row = next(row for row in scheduler["rows"] if row["controller_action_id"] == second["action_id"])
        self.assertEqual(second_row["dependencies"], ["test_multi_action_first"])
        self.assertTrue(second_row["router_only_dependency_metadata"])

        router.record_controller_action_receipt(root, action_id=first["action_id"], status="done")
        router.record_controller_action_receipt(root, action_id=first["action_id"], status="done")
        router.record_controller_action_receipt(root, action_id=second["action_id"], status="done")
        router.record_controller_action_receipt(
            root,
            action_id=blocked["action_id"],
            status="blocked",
            payload={"reason": "test-blocked"},
        )

        ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        self.assertEqual(ledger["counts"]["done"], baseline_done + 2)
        self.assertEqual(ledger["counts"]["blocked"], baseline_blocked + 1)
        first_record = read_json(run_root / "runtime" / "controller_actions" / f"{first['action_id']}.json")
        blocked_record = read_json(run_root / "runtime" / "controller_actions" / f"{blocked['action_id']}.json")
        self.assertEqual(first_record["status"], "done")
        self.assertEqual(blocked_record["status"], "blocked")
        self.assertEqual(blocked_record["blocked_payload"], {"reason": "test-blocked"})
    def test_completed_pending_controller_action_receipt_is_not_returned_again(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        action = router.make_action(
            action_type="test_metadata_only_host_action",
            actor="controller",
            label="test_metadata_only_host_action",
            summary="Test metadata-only action already completed by Controller.",
        )
        state["pending_action"] = action
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)
        router.record_controller_action_receipt(
            root,
            action_id=entry["action_id"],
            status="done",
            payload={"completed_by_test": True},
        )

        next_action = self.next_after_display_sync(root)

        self.assertNotEqual(next_action["action_type"], "test_metadata_only_host_action")
        state = read_json(router.run_state_path(run_root))
        self.assertNotEqual((state.get("pending_action") or {}).get("controller_action_id"), entry["action_id"])
        labels = [item["label"] for item in state["history"] if isinstance(item, dict)]
        self.assertIn("router_reconciled_pending_controller_action_receipt", labels)
    def test_foreground_controller_standby_waits_on_live_daemon_role_wait(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        wait_action = self.force_startup_fact_role_wait(root)
        self.assertEqual(wait_action["action_type"], "await_role_decision")
        self.assertIn("reviewer_reports_startup_facts", wait_action["allowed_external_events"])

        standby = router.foreground_controller_standby(root, max_seconds=0, poll_seconds=0.01, bounded_diagnostic=True)

        self.assertEqual(standby["schema_version"], router.FOREGROUND_CONTROLLER_STANDBY_SCHEMA)
        self.assertEqual(standby["standby_state"], "timeout_still_waiting")
        self.assertTrue(standby["controller_must_continue_standby"])
        self.assertTrue(standby["router_daemon"]["daemon_live"])
        self.assertEqual(standby["current_wait"]["waiting_for_role"], "human_like_reviewer")
        self.assertEqual(standby["normal_router_progress_source"], "router_daemon_status_and_controller_action_ledger")
        self.assertTrue(standby["standby_does_not_drive_router_progress"])
        self.assertFalse(standby["sealed_body_reads_allowed"])
        self.assertFalse(standby["foreground_exit_allowed"])
        self.assertFalse(standby["controller_stop_allowed"])
        self.assertEqual(standby["foreground_required_mode"], "watch_router_daemon")
        self.assertFalse(standby["controller_must_process_pending_action_before_exit"])
        self.assertFalse(standby["controller_must_process_wait_target_before_exit"])
        self.assertEqual(standby["current_wait"]["wait_class"], "report_result")
        self.assertTrue(standby["current_wait"]["liveness_probe"]["required"])
        self.assertTrue(standby["current_wait"]["liveness_probe"]["current_liveness_is_not_cached_authority"])
        self.assertNotIn("role_alive", standby["current_wait"])
        self.assertTrue(standby["exit_policy"]["live_daemon_wait_requires_standby"])
        self.assertTrue(standby["bounded_diagnostic"])
        self.assertTrue(standby["bounded_timeout_is_diagnostic_only"])
        standby_task = standby["continuous_standby_task"]
        self.assertEqual(standby_task["task_kind"], "continuous_controller_standby")
        self.assertEqual(standby_task["codex_plan_sync"]["plan_status"], "in_progress")
        self.assertFalse(standby_task["foreground_close_allowed_while_flowpilot_running"])
        self.assertTrue(standby_task["new_controller_work_requires_ledger_update_and_top_down_reentry"])
        self.assertIn("continuous monitoring duty", standby_task["codex_plan_sync"]["plan_item"])
        self.assertIn("return to top-to-bottom row processing", standby_task["codex_plan_sync"]["plan_item"])
        self.assertIn("timeout_still_waiting", standby_task["do_not_mark_complete_on"])
        self.assertEqual(standby_task["current_wait"]["waiting_for_role"], "human_like_reviewer")
        run_root = self.run_root_for(root)
        ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        standby_rows = [
            item
            for item in ledger["actions"]
            if item.get("action_type") == router.CONTINUOUS_CONTROLLER_STANDBY_ACTION_TYPE
        ]
        self.assertEqual(len(standby_rows), 1)
        standby_entry = read_json(root / standby_rows[0]["action_path"])
        self.assertEqual(standby_entry["status"], "waiting")
        self.assertTrue(standby_entry["action"]["codex_plan_sync"]["required"])
        self.assertTrue(
            standby_entry["action"]["codex_plan_sync"]["new_controller_work_returns_to_top_down_processing"]
        )
    def test_foreground_controller_standby_materializes_report_reminder_with_liveness_probe(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        self.force_startup_fact_role_wait(root)
        state = read_json(router.run_state_path(run_root))
        state["pending_action"]["created_at"] = self.old_utc(minutes=11)
        lock = router._refresh_router_daemon_lock(root, run_root)  # type: ignore[attr-defined]
        router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            current_action=state["pending_action"],
            lock=lock,
        )
        router.save_run_state(run_root, state)

        standby = router.foreground_controller_standby(root, max_seconds=5, poll_seconds=0.01)

        self.assertEqual(standby["standby_state"], "controller_action_ready")
        self.assertEqual(standby["foreground_required_mode"], "process_controller_action")
        self.assertFalse(standby["controller_must_process_wait_target_before_exit"])
        self.assertTrue(standby["current_wait"]["reminder"]["due"])
        self.assertTrue(standby["current_wait"]["liveness_probe"]["due"])
        self.assertTrue(standby["current_wait"]["liveness_probe"]["required"])
        self.assertTrue(standby["current_wait"]["liveness_probe"]["current_liveness_is_not_cached_authority"])
        materialized = standby["materialized_wait_target_controller_action"]
        self.assertEqual(materialized["action_type"], router.WAIT_TARGET_REMINDER_ACTION_TYPE)
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{materialized['controller_action_id']}.json")
        reminder_action = action_record["action"]
        self.assertEqual(reminder_action["target_role"], "human_like_reviewer")
        self.assertEqual(reminder_action["wait_class"], "report_result")
        self.assertTrue(reminder_action["fresh_liveness_probe_required"])
        self.assertTrue(reminder_action["controller_must_use_router_authored_text"])
        self.assertFalse(reminder_action["sealed_body_reads_allowed"])

        receipt = router.record_controller_action_receipt(
            root,
            action_id=materialized["controller_action_id"],
            status="done",
            payload={
                "target_role": "human_like_reviewer",
                "delivered_to_role": "human_like_reviewer",
                "reminder_text_sha256": reminder_action["reminder_text_sha256"],
                "sealed_body_reads": False,
                "liveness_probe": {"checked_at": router.utc_now(), "result": "working"},
            },
        )
        self.assertTrue(receipt["ok"])
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["pending_action"]["last_wait_reminder_at"])
        self.assertEqual(state["pending_action"]["last_liveness_probe"]["result"], "working")
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{materialized['controller_action_id']}.json")
        self.assertEqual(action_record["status"], "done")
    def test_reconcile_replays_reconciled_wait_reminder_receipt_after_state_drift(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        self.force_startup_fact_role_wait(root)
        state = read_json(router.run_state_path(run_root))
        stale_checked_at = self.old_utc(minutes=11)
        delivered_at = router.utc_now()
        state["pending_action"]["created_at"] = self.old_utc(minutes=12)
        state["pending_action"]["last_wait_reminder_at"] = stale_checked_at
        state["pending_action"]["last_liveness_probe"] = {
            "checked_at": stale_checked_at,
            "result": "message_submission_accepted",
            "evidence_path": None,
        }
        state["pending_action"]["liveness_probe_result"] = "message_submission_accepted"
        lock = router._refresh_router_daemon_lock(root, run_root)  # type: ignore[attr-defined]
        router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            current_action=state["pending_action"],
            lock=lock,
        )
        router.save_run_state(run_root, state)

        standby = router.foreground_controller_standby(root, max_seconds=5, poll_seconds=0.01)

        materialized = standby["materialized_wait_target_controller_action"]
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{materialized['controller_action_id']}.json")
        reminder_action = action_record["action"]
        receipt = router.record_controller_action_receipt(
            root,
            action_id=materialized["controller_action_id"],
            status="done",
            payload={
                "target_role": "human_like_reviewer",
                "delivered_to_role": "human_like_reviewer",
                "reminder_text_sha256": reminder_action["reminder_text_sha256"],
                "sealed_body_reads": False,
                "delivered_at": delivered_at,
                "liveness_probe": {"checked_at": delivered_at, "result": "message_submission_accepted"},
                "liveness_probe_result": "message_submission_accepted",
                "liveness_probe_checked_at": delivered_at,
            },
        )
        self.assertTrue(receipt["ok"])
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{materialized['controller_action_id']}.json")
        self.assertEqual(action_record["router_reconciliation_status"], "reconciled")
        state_after_receipt = read_json(router.run_state_path(run_root))
        stale_replay = router._apply_done_controller_receipt_effects(  # type: ignore[attr-defined]
            root,
            run_root,
            state_after_receipt,
            reminder_action,
            {
                "schema_version": router.CONTROLLER_RECEIPT_SCHEMA,
                "status": "done",
                "payload": {
                    "target_role": "human_like_reviewer",
                    "delivered_to_role": "human_like_reviewer",
                    "reminder_text_sha256": reminder_action["reminder_text_sha256"],
                    "sealed_body_reads": False,
                    "delivered_at": stale_checked_at,
                    "liveness_probe": {
                        "checked_at": stale_checked_at,
                        "result": "message_submission_accepted",
                    },
                    "liveness_probe_result": "message_submission_accepted",
                    "liveness_probe_checked_at": stale_checked_at,
                },
            },
        )
        self.assertTrue(stale_replay["applied"])
        self.assertFalse(stale_replay["pending_wait_updated"])
        self.assertEqual(state_after_receipt["pending_action"]["last_wait_reminder_at"], delivered_at)

        drifted = read_json(router.run_state_path(run_root))
        drifted["pending_action"]["last_wait_reminder_at"] = stale_checked_at
        drifted["pending_action"]["last_liveness_probe"] = {
            "checked_at": stale_checked_at,
            "result": "message_submission_accepted",
            "evidence_path": None,
        }
        drifted["pending_action"]["liveness_probe_result"] = "message_submission_accepted"
        router.save_run_state(run_root, drifted)

        reconcile = router.reconcile_current_run(root)

        self.assertTrue(reconcile["repaired"]["scheduled_controller_receipts"]["changed"])
        repaired = read_json(router.run_state_path(run_root))
        self.assertEqual(repaired["pending_action"]["last_wait_reminder_at"], delivered_at)
        self.assertEqual(repaired["pending_action"]["last_liveness_probe"]["checked_at"], delivered_at)
        labels = [item["label"] for item in repaired["history"] if isinstance(item, dict)]
        self.assertIn("router_replayed_reconciled_wait_target_reminder_receipt", labels)
        standby_after_replay = router.foreground_controller_standby(root, max_seconds=0, poll_seconds=0.01, bounded_diagnostic=True)
        self.assertNotEqual(standby_after_replay["standby_state"], "wait_target_check_due")
        self.assertFalse(standby_after_replay["controller_must_process_wait_target_before_exit"])
    def test_foreground_controller_standby_default_waits_past_timeout_until_action(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        self.force_startup_fact_role_wait(root)
        result: dict[str, object] = {}

        def run_standby() -> None:
            try:
                result["standby"] = router.foreground_controller_standby(root, max_seconds=0, poll_seconds=0.01)
            except BaseException as exc:  # pragma: no cover - failure relay from thread
                result["error"] = exc

        thread = threading.Thread(target=run_standby, daemon=True)
        thread.start()
        time.sleep(0.05)
        self.assertNotIn("standby", result)

        state = read_json(router.run_state_path(run_root))
        ready_action = router.make_action(
            action_type="sync_display_plan",
            actor="controller",
            label="controller_syncs_display_plan_from_test",
            summary="Controller syncs visible display plan from test.",
        )
        router._write_controller_action_entry(root, run_root, state, ready_action)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)
        thread.join(timeout=1.0)

        self.assertNotIn("error", result)
        self.assertFalse(thread.is_alive())
        standby = result["standby"]
        self.assertIsInstance(standby, dict)
        self.assertEqual(standby["standby_state"], "controller_action_ready")
        self.assertIn(ready_action["controller_action_id"], standby["controller_action_ledger"]["pending_action_ids"])
    def test_foreground_controller_standby_returns_no_output_reissue_required(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        self.force_startup_fact_role_wait(root)
        state = read_json(router.run_state_path(run_root))
        state["pending_action"]["created_at"] = self.old_utc(minutes=11)
        state["pending_action"]["last_liveness_probe"] = {
            "checked_at": router.utc_now(),
            "result": "completed_without_expected_event",
            "evidence_path": "runtime/liveness/reviewer-completed-no-output.json",
        }
        lock = router._refresh_router_daemon_lock(root, run_root)  # type: ignore[attr-defined]
        router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            current_action=state["pending_action"],
            lock=lock,
        )
        router.save_run_state(run_root, state)

        standby = router.foreground_controller_standby(root, max_seconds=5, poll_seconds=0.01)

        self.assertEqual(standby["standby_state"], "wait_target_reissue_required")
        self.assertEqual(standby["foreground_required_mode"], "record_wait_target_no_output_reissue")
        self.assertTrue(standby["current_wait"]["reissue"]["required"])
        self.assertEqual(standby["current_wait"]["reissue"]["event"], "controller_reports_role_no_output")
        self.assertFalse(standby["current_wait"]["blocker"]["required"])
        self.assertEqual(
            standby["current_wait"]["reissue"]["record_event_payload"]["role_key"],
            "human_like_reviewer",
        )
        self.assertEqual(
            standby["current_wait"]["liveness_probe"]["last_result"],
            "completed_without_expected_event",
        )
    def test_foreground_controller_standby_returns_lost_role_blocker_required(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        self.force_startup_fact_role_wait(root)
        state = read_json(router.run_state_path(run_root))
        state["pending_action"]["created_at"] = self.old_utc(minutes=11)
        state["pending_action"]["last_liveness_probe"] = {
            "checked_at": router.utc_now(),
            "result": "unresponsive",
            "evidence_path": "runtime/liveness/reviewer-unresponsive.json",
        }
        lock = router._refresh_router_daemon_lock(root, run_root)  # type: ignore[attr-defined]
        router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            current_action=state["pending_action"],
            lock=lock,
        )
        router.save_run_state(run_root, state)

        standby = router.foreground_controller_standby(root, max_seconds=5, poll_seconds=0.01)

        self.assertEqual(standby["standby_state"], "wait_target_blocker_required")
        self.assertEqual(standby["foreground_required_mode"], "record_wait_target_blocker")
        self.assertTrue(standby["current_wait"]["blocker"]["required"])
        self.assertEqual(standby["current_wait"]["blocker"]["event"], "controller_reports_role_liveness_fault")
        self.assertEqual(standby["current_wait"]["blocker"]["record_event_payload"]["role_key"], "human_like_reviewer")
        self.assertEqual(standby["current_wait"]["liveness_probe"]["last_result"], "unresponsive")
    def test_foreground_controller_standby_returns_ack_reminder_and_blocker_due(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        runtime_dir = run_root / "runtime"
        for name in ("controller_actions", "controller_receipts"):
            path = runtime_dir / name
            if path.exists():
                shutil.rmtree(path)
            path.mkdir(parents=True, exist_ok=True)
        state = read_json(router.run_state_path(run_root))
        ack_action = router.make_action(
            action_type="await_card_return_event",
            actor="controller",
            label="controller_waits_for_pm_card_ack",
            summary="Controller waits for PM card ACK.",
            to_role="project_manager",
            extra={
                "waiting_for_role": "project_manager",
                "expected_return_path": "mailbox/outbox/card_acks/pm_core.ack.json",
            },
        )
        state["pending_action"] = ack_action
        state["daemon_mode_enabled"] = True
        return_ledger_path = run_root / "return_event_ledger.json"
        return_ledger = read_json(return_ledger_path)
        return_ledger.setdefault("pending_returns", []).append(
            {
                "return_id": "pm-core-ack",
                "return_kind": "system_card",
                "status": "awaiting_return",
                "target_role": "project_manager",
                "card_return_event": "pm_card_ack",
                "expected_return_path": "mailbox/outbox/card_acks/pm_core.ack.json",
            }
        )
        router.write_json(return_ledger_path, return_ledger)
        router._write_controller_action_entry(root, run_root, state, ack_action)  # type: ignore[attr-defined]
        state["pending_action"]["created_at"] = self.old_utc(minutes=4)
        lock = router._acquire_router_daemon_lock(root, run_root, state)  # type: ignore[attr-defined]
        router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            current_action=state["pending_action"],
            lock=lock,
        )
        router.save_run_state(run_root, state)

        reminder = router.foreground_controller_standby(root, max_seconds=5, poll_seconds=0.01)

        self.assertEqual(reminder["standby_state"], "controller_action_ready")
        self.assertEqual(reminder["current_wait"]["wait_class"], "ack")
        self.assertTrue(reminder["current_wait"]["reminder"]["due"])
        self.assertFalse(reminder["current_wait"]["blocker"]["required"])
        materialized = reminder["materialized_wait_target_controller_action"]
        self.assertEqual(materialized["action_type"], router.WAIT_TARGET_REMINDER_ACTION_TYPE)
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{materialized['controller_action_id']}.json")
        reminder_action = action_record["action"]
        self.assertEqual(reminder_action["target_role"], "project_manager")
        self.assertEqual(reminder_action["wait_class"], "ack")
        self.assertFalse(reminder_action["fresh_liveness_probe_required"])

        router.record_controller_action_receipt(
            root,
            action_id=materialized["controller_action_id"],
            status="done",
            payload={
                "target_role": "project_manager",
                "delivered_to_role": "project_manager",
                "reminder_text_sha256": reminder_action["reminder_text_sha256"],
                "sealed_body_reads": False,
            },
        )
        return_ledger = read_json(return_ledger_path)
        self.assertEqual(return_ledger["pending_returns"][0]["status"], "reminded")
        self.assertTrue(return_ledger["pending_returns"][0]["last_wait_reminder_at"])

        state = read_json(router.run_state_path(run_root))
        rebuilt_wait = router._next_pending_card_return_action(root, state, run_root)  # type: ignore[attr-defined]
        self.assertEqual(rebuilt_wait["last_wait_reminder_at"], return_ledger["pending_returns"][0]["last_wait_reminder_at"])
        state["pending_action"] = rebuilt_wait
        current_wait = router._pending_wait_summary(state, project_root=root)  # type: ignore[attr-defined]
        self.assertFalse(current_wait["reminder"]["due"])

        state["pending_action"]["created_at"] = self.old_utc(minutes=11)
        state["pending_action"]["last_wait_reminder_at"] = self.old_utc(minutes=11)
        lock = router._refresh_router_daemon_lock(root, run_root)  # type: ignore[attr-defined]
        router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            current_action=state["pending_action"],
            lock=lock,
        )
        router.save_run_state(run_root, state)

        blocker = router.foreground_controller_standby(root, max_seconds=5, poll_seconds=0.01)

        self.assertEqual(blocker["standby_state"], "wait_target_blocker_required")
        self.assertTrue(blocker["current_wait"]["blocker"]["required"])
        self.assertEqual(blocker["current_wait"]["blocker"]["reason"], "ack_missing_after_ten_minutes")
    def test_foreground_controller_standby_self_audits_controller_local_wait(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        runtime_dir = run_root / "runtime"
        for name in ("controller_actions", "controller_receipts"):
            path = runtime_dir / name
            if path.exists():
                shutil.rmtree(path)
            path.mkdir(parents=True, exist_ok=True)
        router.write_json(  # type: ignore[attr-defined]
            runtime_dir / "controller_action_ledger.json",
            {
                "schema_version": router.CONTROLLER_ACTION_LEDGER_SCHEMA,
                "run_id": run_root.name,
                "run_root": self.rel(root, run_root),
                "updated_at": router.utc_now(),
                "actions": [],
                "counts": {"pending": 0, "in_progress": 0, "done": 0, "blocked": 0, "waiting": 0, "skipped": 0, "total": 0},
            },
        )
        state = read_json(router.run_state_path(run_root))
        local_action = router.make_action(
            action_type="sync_display_plan",
            actor="controller",
            label="controller_syncs_display_plan",
            summary="Controller syncs local display plan.",
        )
        state["pending_action"] = local_action
        state["daemon_mode_enabled"] = True
        lock = router._acquire_router_daemon_lock(root, run_root, state)  # type: ignore[attr-defined]
        router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            current_action=local_action,
            lock=lock,
        )
        router.save_run_state(run_root, state)

        standby = router.foreground_controller_standby(root, max_seconds=5, poll_seconds=0.01)

        self.assertEqual(standby["standby_state"], "wait_target_check_due")
        self.assertEqual(standby["current_wait"]["wait_class"], "controller_local_action")
        self.assertTrue(standby["current_wait"]["controller_local_self_audit"]["required"])
        self.assertFalse(standby["current_wait"]["controller_local_self_audit"]["reminder_allowed"])
    def test_foreground_controller_standby_keeps_alive_when_daemon_has_no_ready_action(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        runtime_dir = run_root / "runtime"
        for name in ("controller_actions", "controller_receipts"):
            path = runtime_dir / name
            if path.exists():
                shutil.rmtree(path)
            path.mkdir(parents=True, exist_ok=True)
        state = read_json(router.run_state_path(run_root))
        state["pending_action"] = None
        state["daemon_mode_enabled"] = True
        router._rebuild_controller_action_ledger(root, run_root, state)  # type: ignore[attr-defined]
        lock = router._refresh_router_daemon_lock(root, run_root)  # type: ignore[attr-defined]
        router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            current_action=None,
            lock=lock,
        )
        router.save_run_state(run_root, state)

        standby = router.foreground_controller_standby(root, max_seconds=0, poll_seconds=0.01, bounded_diagnostic=True)

        self.assertEqual(standby["standby_state"], "timeout_still_waiting")
        self.assertTrue(standby["controller_must_continue_standby"])
        self.assertFalse(standby["controller_must_process_pending_action_before_exit"])
        self.assertFalse(standby["foreground_exit_allowed"])
        self.assertFalse(standby["controller_stop_allowed"])
        self.assertFalse(standby["user_status_update_allowed"])
        self.assertTrue(standby["controller_patrol_required"])
        self.assertTrue(standby["foreground_turn_return_is_not_controller_stop"])
        self.assertFalse(standby["final_answer_preflight"]["final_answer_allowed"])
        self.assertTrue(standby["final_answer_preflight"]["status_projection_is_not_stop_authority"])
        self.assertEqual(standby["foreground_required_mode"], "watch_router_daemon")
        self.assertEqual(standby["controller_action_ledger"]["pending_action_ids"], [])
        self.assertTrue(standby["exit_policy"]["live_daemon_wait_requires_standby"])
        standby_task = standby["continuous_standby_task"]
        self.assertEqual(standby_task["task_kind"], "continuous_controller_standby")
        self.assertTrue(standby_task["codex_plan_sync"]["required"])
        self.assertEqual(standby_task["codex_plan_sync"]["plan_status"], "in_progress")
        self.assertFalse(standby_task["foreground_close_allowed_while_flowpilot_running"])
        self.assertTrue(standby_task["new_controller_work_requires_ledger_update_and_top_down_reentry"])
        self.assertIn("continuous monitoring duty", standby_task["codex_plan_sync"]["plan_item"])
        self.assertIn("no_new_controller_action_yet", standby_task["do_not_mark_complete_on"])
        self.assertEqual(
            standby_task["required_command"],
            "python skills\\flowpilot\\assets\\flowpilot_router.py --root . --json controller-patrol-timer --seconds 60",
        )
        self.assertEqual(standby_task["patrol_timer_seconds"], 60.0)
        quiet_policy = standby_task["quiet_user_reporting_policy"]
        self.assertFalse(quiet_policy["continue_patrol_user_visible_message_required"])
        self.assertIn("quiet_patrol_continue", quiet_policy["silent_by_default_for"])
        self.assertIn("explicit_user_status_request", quiet_policy["report_when"])
        self.assertIn("continue_patrol", standby_task["do_not_mark_complete_on"])
        self.assertIn("wait for the next output", standby_task["loop_rule"])
        self.assertEqual(standby_task["completion_allowed_only_when"], "terminal_return_and_controller_stop_allowed_true")
    def test_controller_patrol_timer_continue_patrol_restarts_and_waits(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        runtime_dir = run_root / "runtime"
        for name in ("controller_actions", "controller_receipts"):
            path = runtime_dir / name
            if path.exists():
                shutil.rmtree(path)
            path.mkdir(parents=True, exist_ok=True)
        state = read_json(router.run_state_path(run_root))
        state["pending_action"] = None
        state["daemon_mode_enabled"] = True
        router._rebuild_controller_action_ledger(root, run_root, state)  # type: ignore[attr-defined]
        lock = router._refresh_router_daemon_lock(root, run_root)  # type: ignore[attr-defined]
        router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            current_action=None,
            lock=lock,
        )
        router.save_run_state(run_root, state)

        result = router.controller_patrol_timer(root, seconds=0)

        self.assertEqual(result["schema_version"], router.CONTROLLER_PATROL_TIMER_SCHEMA)
        self.assertEqual(result["patrol_result"], "continue_patrol")
        self.assertEqual(result["foreground_required_mode"], "watch_router_daemon")
        self.assertIn("prevent Controller from accidentally exiting", result["anti_exit_reminder"])
        self.assertIn("Immediately rerun next_command and wait", result["controller_instruction"])
        self.assertIn("Starting or restarting the command is not completion", result["controller_instruction"])
        self.assertEqual(
            result["next_command"],
            "python skills\\flowpilot\\assets\\flowpilot_router.py --root . --json controller-patrol-timer --seconds 0",
        )
        self.assertFalse(result["user_visible_message_required"])
        self.assertFalse(result["quiet_patrol_user_visible_message_required"])
        self.assertIn("continue_patrol", result["user_reporting_policy"]["silent_by_default_for"])
        self.assertIn("explicit_user_status_request", result["user_reporting_policy"]["report_when"])
        self.assertEqual(
            result["standby_status_after_rerun"],
            "continuous_controller_standby remains in_progress until the next command output",
        )
        self.assertFalse(result["command_start_is_completion"])
        self.assertFalse(result["command_restart_is_completion"])
        self.assertEqual(result["monitor_source"], "existing_router_daemon_monitor")
        self.assertFalse(result["final_answer_preflight"]["final_answer_allowed"])
        self.assertFalse(result["final_answer_preflight"]["controller_stop_allowed"])
        self.assertEqual(result["final_answer_preflight"]["continuous_controller_standby_status"], "in_progress")
        self.assertFalse(result["display_projection_is_stop_authority"])
    def test_controller_patrol_timer_continues_for_daemon_heartbeat_inside_thirty_second_window(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        runtime_dir = run_root / "runtime"
        for name in ("controller_actions", "controller_receipts"):
            path = runtime_dir / name
            if path.exists():
                shutil.rmtree(path)
            path.mkdir(parents=True, exist_ok=True)
        state = read_json(router.run_state_path(run_root))
        state["pending_action"] = None
        state["daemon_mode_enabled"] = True
        router._rebuild_controller_action_ledger(root, run_root, state)  # type: ignore[attr-defined]
        lock = router._refresh_router_daemon_lock(root, run_root)  # type: ignore[attr-defined]
        lock["last_tick_at"] = (
            datetime.now(timezone.utc).replace(microsecond=0) - timedelta(seconds=20)
        ).isoformat().replace("+00:00", "Z")
        router.write_json(run_root / "runtime" / "router_daemon.lock", lock)
        router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            current_action=None,
            lock=lock,
        )
        router.save_run_state(run_root, state)

        result = router.controller_patrol_timer(root, seconds=0)

        self.assertEqual(result["patrol_result"], "continue_patrol")
        router_daemon = result["standby_snapshot"]["router_daemon"]
        self.assertEqual(router_daemon["heartbeat_status"], "ok")
        self.assertTrue(router_daemon["lock_live"])
        self.assertEqual(router_daemon["heartbeat_check_after_seconds"], 30.0)
        self.assertLess(router_daemon["heartbeat_age_seconds"], router.ROUTER_DAEMON_HEARTBEAT_CHECK_SECONDS)
        self.assertFalse(router_daemon["controller_liveness_check_required"])
    def test_controller_patrol_timer_requests_liveness_check_after_delayed_daemon_heartbeat(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        runtime_dir = run_root / "runtime"
        for name in ("controller_actions", "controller_receipts"):
            path = runtime_dir / name
            if path.exists():
                shutil.rmtree(path)
            path.mkdir(parents=True, exist_ok=True)
        state = read_json(router.run_state_path(run_root))
        state["pending_action"] = None
        state["daemon_mode_enabled"] = True
        router._rebuild_controller_action_ledger(root, run_root, state)  # type: ignore[attr-defined]
        lock = router._refresh_router_daemon_lock(root, run_root)  # type: ignore[attr-defined]
        lock["last_tick_at"] = self.old_utc(minutes=1)
        router.write_json(run_root / "runtime" / "router_daemon.lock", lock)
        router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            current_action=None,
            lock=lock,
        )
        router.save_run_state(run_root, state)

        result = router.controller_patrol_timer(root, seconds=0)

        self.assertEqual(result["patrol_result"], "check_liveness")
        self.assertEqual(result["foreground_required_mode"], "check_liveness")
        self.assertIn("If the daemon is alive, stay attached", result["controller_instruction"])
        router_daemon = result["standby_snapshot"]["router_daemon"]
        self.assertEqual(router_daemon["heartbeat_status"], "check_liveness")
        self.assertGreater(router_daemon["heartbeat_age_seconds"], router.ROUTER_DAEMON_HEARTBEAT_CHECK_SECONDS)
        self.assertFalse(router_daemon["monitor_can_decide_recovery"])
        self.assertTrue(router_daemon["controller_liveness_check_required"])
    def test_foreground_controller_standby_wakes_on_controller_action_ledger(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        result = router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=False)
        action_id = result["ticks"][0]["controller_action_id"]
        self.assertTrue(action_id)

        standby = router.foreground_controller_standby(root, max_seconds=5, poll_seconds=0.01)

        self.assertEqual(standby["standby_state"], "controller_action_ready")
        self.assertIn(action_id, standby["controller_action_ledger"]["pending_action_ids"])
        self.assertFalse(standby["controller_must_continue_standby"])
        self.assertTrue(standby["controller_must_process_pending_action_before_exit"])
        self.assertFalse(standby["foreground_exit_allowed"])
        self.assertFalse(standby["controller_stop_allowed"])
        self.assertEqual(standby["foreground_required_mode"], "process_controller_action")
        self.assertTrue(standby["exit_policy"]["controller_action_ready_blocks_foreground_exit"])
    def test_controller_patrol_timer_wakes_on_controller_action_ledger(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        result = router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=False)
        action_id = result["ticks"][0]["controller_action_id"]

        patrol = router.controller_patrol_timer(root, seconds=0)

        self.assertEqual(patrol["patrol_result"], "new_controller_work")
        self.assertEqual(patrol["foreground_required_mode"], "process_controller_action")
        self.assertIn("process ready Controller rows", patrol["controller_instruction"])
        self.assertIn(action_id, patrol["standby_snapshot"]["controller_action_ledger"]["pending_action_ids"])
    def test_controller_patrol_timer_allows_terminal_return_only_when_stopped(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        runtime_dir = run_root / "runtime"
        for name in ("controller_actions", "controller_receipts"):
            path = runtime_dir / name
            if path.exists():
                shutil.rmtree(path)
            path.mkdir(parents=True, exist_ok=True)
        state = read_json(router.run_state_path(run_root))
        state["status"] = "completed"
        state["pending_action"] = None
        state["daemon_mode_enabled"] = True
        router._rebuild_controller_action_ledger(root, run_root, state)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)

        patrol = router.controller_patrol_timer(root, seconds=0)

        self.assertEqual(patrol["patrol_result"], "terminal_return")
        self.assertTrue(patrol["controller_stop_allowed"])
        self.assertEqual(patrol["completion_allowed_only_when"], "terminal_return_and_controller_stop_allowed_true")
        self.assertTrue(patrol["final_answer_preflight"]["final_answer_allowed"])
        self.assertEqual(patrol["final_answer_preflight"]["continuous_controller_standby_status"], "released")
    def test_nonterminal_user_status_return_is_not_controller_stop(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        state["pending_action"] = router.make_action(
            action_type="record_user_request",
            actor="controller",
            label="controller_waits_for_user_status_confirmation",
            summary="Controller waits for a user-facing status confirmation.",
            extra={"requires_user": True, "requires_payload": "user_request"},
        )
        state["daemon_mode_enabled"] = True
        router.save_run_state(run_root, state)

        standby = router.foreground_controller_standby(root, max_seconds=0, poll_seconds=0.01, bounded_diagnostic=True)
        patrol = router.controller_patrol_timer(root, seconds=0)

        self.assertEqual(standby["standby_state"], "user_input_required")
        self.assertEqual(standby["foreground_required_mode"], "return_for_user_input")
        self.assertTrue(standby["foreground_turn_return_allowed"])
        self.assertTrue(standby["user_status_update_allowed"])
        self.assertTrue(standby["foreground_turn_return_is_not_controller_stop"])
        self.assertFalse(standby["foreground_exit_allowed"])
        self.assertFalse(standby["controller_stop_allowed"])
        self.assertFalse(standby["final_answer_preflight"]["final_answer_allowed"])
        self.assertEqual(standby["final_answer_preflight"]["blocked_reason"], "nonterminal_controller_must_stay_attached")
        self.assertEqual(patrol["patrol_result"], "return_for_user_input")
        self.assertFalse(patrol["final_answer_preflight"]["final_answer_allowed"])
        self.assertTrue(patrol["final_answer_preflight"]["user_status_update_is_not_stop_permission"])
    def test_foreground_controller_standby_requests_liveness_check_on_stale_or_missing_daemon(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        router.stop_router_daemon(root, reason="test_standby_missing_daemon")

        standby = router.foreground_controller_standby(root, max_seconds=5, poll_seconds=0.01)

        self.assertEqual(standby["standby_state"], "daemon_liveness_check_required")
        self.assertFalse(standby["router_daemon"]["daemon_live"])
        self.assertFalse(standby["controller_must_continue_standby"])
        self.assertFalse(standby["foreground_exit_allowed"])
        self.assertFalse(standby["controller_stop_allowed"])
        self.assertTrue(standby["foreground_turn_return_allowed"])
        self.assertTrue(standby["foreground_turn_return_is_not_controller_stop"])
        self.assertTrue(standby["user_status_update_allowed"])
        self.assertFalse(standby["final_answer_preflight"]["final_answer_allowed"])
        self.assertEqual(standby["foreground_required_mode"], "check_liveness")
        self.assertEqual(standby["router_daemon"]["heartbeat_status"], "check_liveness")
        self.assertFalse(standby["router_daemon"]["monitor_can_decide_recovery"])
    def test_foreground_controller_standby_does_not_compute_router_next(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        wait_action = self.force_startup_fact_role_wait(root)
        self.assertEqual(wait_action["action_type"], "await_role_decision")

        with mock.patch.object(router, "compute_controller_action", side_effect=AssertionError("standby must not drive Router")):
            standby = router.foreground_controller_standby(root, max_seconds=0, poll_seconds=0.01, bounded_diagnostic=True)

        self.assertEqual(standby["standby_state"], "timeout_still_waiting")
        self.assertEqual(standby["diagnostic_router_reentry_commands"], ["next", "run-until-wait"])
    def test_router_daemon_card_ack_reconciles_matching_controller_ack_wait(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        action = self.deliver_startup_fact_check_card_without_ack(root)
        state = read_json(router.run_state_path(run_root))
        wait_action = router.make_action(
            action_type="await_card_return_event",
            actor="controller",
            label="controller_waits_for_reviewer_startup_fact_card_ack",
            summary="Controller waits for Reviewer startup fact card ACK.",
            to_role=str(action["to_role"]),
            extra={
                "waiting_for_role": str(action["to_role"]),
                "delivery_attempt_id": action["delivery_attempt_id"],
                "card_id": action["card_id"],
                "card_return_event": action["card_return_event"],
                "expected_return_path": action["expected_return_path"],
            },
        )
        wait_entry = router._write_controller_action_entry(root, run_root, state, wait_action)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)
        self.submit_system_card_ack_without_router_next(root, action)

        result = router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)

        self.assertEqual(result["tick_count"], 1)
        reconciled_wait = read_json(root / wait_entry["action_path"])
        self.assertEqual(reconciled_wait["status"], "resolved")
        self.assertEqual(reconciled_wait["router_reconciliation_status"], "reconciled")
        self.assertEqual(reconciled_wait["router_reconciliation"]["clearance_kind"], "ack_wait_only")
        self.assertTrue(reconciled_wait["router_reconciliation"]["ack_does_not_complete_output_bearing_work"])
        scheduler = read_json(run_root / "runtime" / "router_scheduler_ledger.json")
        row = next(item for item in scheduler["rows"] if item.get("row_id") == wait_entry["router_scheduler_row_id"])
        self.assertEqual(row["router_state"], "reconciled")
        summary = router._controller_action_ledger_summary(run_root)  # type: ignore[attr-defined]
        matching_waits = [
            item
            for item in summary["passive_waits"]
            if item.get("action_id") == wait_entry["action_id"]
        ]
        self.assertEqual(len(matching_waits), 1)
        self.assertEqual(matching_waits[0]["status"], "resolved")
        self.assertEqual(matching_waits[0]["router_reconciliation_status"], "reconciled")
    def test_display_plan_is_controller_synced_projection_from_pm_plan(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "sync_display_plan")
        self.assertEqual(action["display_kind"], "startup_waiting_state")
        self.assertIsNone(action.get("postcondition"))
        self.assertIsNone(action["next_step_contract"]["postcondition"])
        self.assertFalse(action["display_required"])
        self.assertFalse(action["requires_user_dialog_display_confirmation"])
        self.assertTrue(action["user_visible_display_suppressed"])
        self.assertEqual(action["internal_display_reason"], "waiting_for_pm_route_before_canonical_route")
        self.assertIn("internal waiting-for-PM-route placeholder", action["summary"])
        self.assertIn("no user-dialog route map is required", action["summary"])
        self.assertNotIn("Display the route map in the user dialog", action["summary"])
        self.assertNotIn("display_text", action)
        self.assertNotIn("payload_template", action)
        policy = action["controller_user_reporting_policy"]
        self.assertEqual(policy["schema_version"], router.CONTROLLER_USER_REPORTING_POLICY_SCHEMA)
        self.assertTrue(policy["plain_language_required"])
        self.assertTrue(policy["speak_only_when_user_value"])
        self.assertIn("quiet_patrol_continue", policy["silent_by_default_for"])
        self.assertIn("explicit_user_status_request", policy["report_when"])
        self.assertIn("plain language", policy["reminder"])
        self.assertEqual(action["next_step_contract"]["controller_user_reporting_policy"], policy)
        self.assertEqual(action["native_plan_projection"]["items"][0]["id"], "await_pm_route")
        result = router.apply_action(root, "sync_display_plan", self.payload_for_action(action))
        self.assertEqual(result["host_action"], "replace_visible_plan")
        self.assertEqual(result["display_kind"], "startup_waiting_state")
        self.assertFalse(result["display_required"])
        self.assertTrue(result["user_visible_display_suppressed"])
        self.assertNotIn("display_text", result)
        self.assertNotIn("user_dialog_display_confirmation", result)
        self.assertFalse((run_root / "display" / "user_dialog_display_ledger.json").exists())
        waiting_plan = read_json(run_root / "display_plan.json")
        self.assertEqual(waiting_plan["source_role"], "controller")
        self.assertEqual(waiting_plan["route_authority"], "none_until_pm_display_plan")
        visible_sync = read_json(router.run_state_path(run_root))["visible_plan_sync"]
        self.assertFalse(visible_sync["display_required"])
        self.assertTrue(visible_sync["user_visible_display_suppressed"])
        self.assertNotIn("user_dialog_display_confirmation", visible_sync)
        self.assertTrue(read_json(router.run_state_path(run_root))["flags"]["visible_plan_synced"])
        waiting_snapshot = read_json(run_root / "route_state_snapshot.json")
        self.assertEqual(waiting_snapshot["schema_version"], "flowpilot.route_state_snapshot.v1")
        self.assertTrue(waiting_snapshot["authority"]["current_pointer_matches_run"])
        self.assertEqual(waiting_snapshot["active_ui_task_catalog"]["active_tasks"][0]["run_id"], waiting_snapshot["run_id"])
        self.assertEqual(waiting_snapshot["continuation_quarantine"]["schema_version"], router.CONTINUATION_QUARANTINE_SCHEMA)
        self.assertFalse(waiting_snapshot["continuation_quarantine"]["prior_run_files_are_evidence_by_default"])
        waiting_refresh = read_json(run_root / "display" / "route_display_refresh.json")
        self.assertEqual(waiting_refresh["schema_version"], router.ROUTE_DISPLAY_REFRESH_SCHEMA)
        self.assertFalse(waiting_refresh["display_is_route_authority"])
        self.assertEqual(visible_sync["route_display_refresh_path"], self.rel(root, run_root / "display" / "route_display_refresh.json"))

        self.complete_pre_route_gates(root)
        route_plan = read_json(run_root / "display_plan.json")
        self.assertNotEqual(route_plan.get("source_event"), "pm_writes_route_draft")
        self.assertNotEqual(route_plan.get("scope"), "route")
        self.assertNotEqual(route_plan["items"][0]["id"], "node-001")
        draft_visibility = read_json(router.run_state_path(run_root))["draft_route_visibility"]
        self.assertFalse(draft_visibility["user_visible"])
        self.assertEqual(draft_visibility["reason"], "draft_routes_are_internal_until_pm_activates_reviewed_flow_json")

        index_path = root / ".flowpilot" / "index.json"
        index = read_json(index_path)
        index["runs"].append({"run_id": "run-stale", "run_root": ".flowpilot/runs/run-stale", "status": "running"})
        index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        self.activate_route(root)
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "sync_display_plan")
        self.assertIsNone(action.get("postcondition"))
        self.assertIsNone(action["next_step_contract"]["postcondition"])
        self.assertEqual(action["native_plan_projection"]["items"][0]["status"], "in_progress")
        self.assertEqual(action["display_kind"], "route_map")
        self.assertEqual(action["display_text_format"], "markdown_mermaid")
        self.assertTrue(action["route_sign_display_required"])
        self.assertIn(action["route_sign_source_kind"], {"flow_json", "route_state_snapshot"})
        self.assertNotEqual(action["route_sign_source_kind"], "flow_draft")
        self.assertIn("Display the canonical FlowPilot Route Sign", action["summary"])
        self.assertIn("committed route state", action["summary"])
        self.assertIn("# FlowPilot Route Sign", action["display_text"])
        self.assertIn("```mermaid", action["display_text"])
        self.assertIn("route=route-001", action["display_text"])
        self.assertIn("class n01 active;", action["display_text"])
        self.assertNotIn("Now: node-001", action["display_text"])
        self.assertNotIn("- node-001 - in_progress", action["display_text"])
        self.assertNotIn(action["controller_user_reporting_policy"]["reminder"], action["display_text"])
        self.assertTrue(action["current_status_summary_exists"])
        self.assertTrue(action["router_daemon_status_exists"])
        self.assertEqual(action["user_visible_status_source"]["status_summary_source"], "current_status_summary")
        self.assertEqual(action["user_visible_status_source"]["daemon_status_source"], "router_daemon_status")
        self.assertTrue(action["user_visible_status_source"]["controller_must_show_status_from_current_status_summary"])
        self.assertEqual(
            action["next_step_contract"]["controller_user_reporting_policy"],
            action["controller_user_reporting_policy"],
        )
        status_summary = read_json(run_root / "display" / "current_status_summary.json")
        progress = status_summary["progress_summary"]
        self.assertEqual(progress["schema_version"], "flowpilot.progress_summary.v1")
        self.assertEqual(progress["state"], status_summary["state_kind"])
        self.assertEqual(progress["level_count"], 1)
        self.assertEqual(progress["overall_total_nodes"], 1)
        self.assertEqual(progress["overall_completed_nodes"], 0)
        self.assertEqual(progress["levels"][0]["level"], 1)
        self.assertEqual(progress["levels"][0]["total_nodes"], 1)
        self.assertEqual(progress["levels"][0]["completed_nodes"], 0)
        self.assertEqual(progress["levels"][0]["current_index"], 1)
        self.assertEqual(progress["levels"][0]["current_node_id"], "node-001")
        self.assertTrue(progress["metadata_only"])
        self.assertTrue(progress["sealed_body_fields_excluded"])
        self.assertTrue(progress["diagnostic_paths_excluded"])
        self.assertTrue(progress["hash_fields_excluded"])
        self.assertTrue(progress["elapsed_seconds"] is None or progress["elapsed_seconds"] >= 0)
        router.apply_action(root, "sync_display_plan", self.payload_for_action(action))
        display_packet = read_json(run_root / "diagrams" / "user-flow-diagram-display.json")
        self.assertTrue(display_packet["canonical_route_available"])
        self.assertEqual(display_packet["display_role"], "canonical_route")
        self.assertFalse(display_packet["is_placeholder"])
        self.assertIsNone(display_packet["replacement_rule"])
        route_sign = (run_root / "diagrams" / "user-flow-diagram.mmd").read_text(encoding="utf-8")
        self.assertIn("route=route-001", route_sign)
        self.assertIn("class n01 active;", route_sign)
        self.assertNotIn("Now: node-001", route_sign)
        self.assertNotIn("route=unknown", route_sign)
        visible_sync = read_json(router.run_state_path(run_root))["visible_plan_sync"]
        self.assertEqual(visible_sync["display_text_format"], "markdown_mermaid")
        self.assertTrue(visible_sync["route_sign_display_required"])
        self.assertEqual(visible_sync["route_sign_node_count"], 1)
        self.assertFalse(visible_sync["display_is_route_authority"])
        active_refresh = read_json(run_root / "display" / "route_display_refresh.json")
        self.assertEqual(active_refresh["schema_version"], router.ROUTE_DISPLAY_REFRESH_SCHEMA)
        self.assertTrue(active_refresh["display_version_matches_frontier"])
        self.assertFalse(active_refresh["display_is_route_authority"])
        self.assertTrue(read_json(router.run_state_path(run_root))["flags"]["visible_plan_synced"])
        active_snapshot = read_json(run_root / "route_state_snapshot.json")
        self.assertEqual(active_snapshot["route"]["nodes"][0]["id"], "node-001")
        self.assertTrue(active_snapshot["route"]["nodes"][0]["is_active"])
        self.assertFalse(active_snapshot["continuation_quarantine"]["old_agent_ids_are_current_authority"])
        self.assertEqual(active_snapshot["authority"]["stale_running_index_entries"], [])
        self.assertEqual(
            active_snapshot["authority"]["background_running_index_entries"],
            [
                {
                    "background_active": True,
                    "flow_block_id": "run-stale",
                    "focus_selected": False,
                    "operation_target_allowed": True,
                    "run_id": "run-stale",
                    "run_root": ".flowpilot/runs/run-stale",
                    "stale_residue": False,
                    "status": "running",
                    "target_id": "run:run-stale",
                    "target_scope": "single",
                }
            ],
        )
        self.assertEqual(active_snapshot["authority"]["active_source"], "explicit_active_set")
        self.assertFalse(active_snapshot["authority"]["global_main_required"])
        self.assertTrue(active_snapshot["authority"]["operation_target_required"])
        self.assertEqual(active_snapshot["active_ui_task_catalog"]["hidden_non_current_running_index_entries"], [])
        self.assertEqual(active_snapshot["active_ui_task_catalog"]["authority"], "explicit_active_set")
        self.assertEqual(active_snapshot["active_ui_task_catalog"]["scope_kind"], "parallel_runs")
        self.assertFalse(active_snapshot["active_ui_task_catalog"]["global_main_required"])
        self.assertTrue(active_snapshot["active_ui_task_catalog"]["operation_target_required"])
        self.assertEqual(
            active_snapshot["active_ui_task_catalog"]["operation_targets"]["current_focus"],
            f"run:{active_snapshot['run_id']}",
        )
        self.assertEqual(
            sorted(active_snapshot["active_ui_task_catalog"]["operation_targets"]["all_active"]["run_ids"]),
            sorted([active_snapshot["run_id"], "run-stale"]),
        )
        self.assertEqual(
            [item["run_id"] for item in active_snapshot["active_ui_task_catalog"]["background_active_tasks"]],
            ["run-stale"],
        )
        self.assertEqual(
            [item["target_id"] for item in active_snapshot["active_ui_task_catalog"]["background_active_tasks"]],
            ["run:run-stale"],
        )
        self.assertEqual(status_summary["active_set_status"]["authority"], "explicit_active_set")
        self.assertFalse(status_summary["active_set_status"]["global_main_required"])
        self.assertTrue(status_summary["active_set_status"]["operation_target_required"])
        index_after = read_json(index_path)
        stale_entry = next(item for item in index_after["runs"] if item["run_id"] == "run-stale")
        self.assertEqual(stale_entry["status"], "running")
        self.assertNotIn("stale_reason", stale_entry)

        self.deliver_current_node_cards(root)
        node_plan = read_json(run_root / "display_plan.json")
        self.assertEqual(node_plan["source_event"], "pm_writes_node_acceptance_plan")
        self.assertEqual(node_plan["current_node"]["checklist"][0]["id"], "node-001-req")
    def test_role_output_envelope_writes_body_and_keeps_controller_visible_payload_sealed(self) -> None:
        root = self.make_project()
        envelope = router.write_role_output_envelope(
            root,
            output_path="role_outputs/route_process_check.json",
            body={"reviewed_by_role": "process_flowguard_officer", "passed": True},
            event_name="process_officer_passes_route_check",
            from_role="process_flowguard_officer",
        )

        self.assertEqual(envelope["schema_version"], "flowpilot.role_output_envelope.v1")
        self.assertEqual(envelope["controller_visibility"], "role_output_envelope_only")
        self.assertFalse(envelope["chat_response_body_allowed"])
        self.assertNotIn("passed", envelope)
        loaded = router._load_file_backed_role_payload(root, envelope)
        self.assertTrue(loaded["passed"])
        self.assertEqual(loaded["_role_output_envelope"]["body_path_key"], "report_path")
    def test_missing_system_card_ack_wait_confirms_controller_delivery_before_target_reminder(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        action = self.deliver_startup_fact_check_card_without_ack(root)
        state = read_json(router.run_state_path(run_root))
        router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)

        result = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report_pre_ack_controller_delivery_unconfirmed",
                self.startup_fact_report_body(root),
            ),
        )

        self.assertFalse(result["ok"])
        state = read_json(router.run_state_path(run_root))
        wait = state["pending_action"]
        self.assertEqual(wait["action_type"], "await_card_return_event")
        self.assertEqual(wait["missing_ack_recovery"], "confirm_or_reissue_controller_delivery_before_target_ack_reminder")
        self.assertEqual(wait["reminder_target"], "controller_delivery_task")
        self.assertFalse(wait["target_role_ack_reminder_allowed"])
        self.assertTrue(wait["controller_delivery_reissue_required_before_target_ack_reminder"])
        fact = wait["controller_delivery_fact"]
        self.assertEqual(fact["controller_delivery_fact_status"], "controller_delivery_unconfirmed")
        self.assertFalse(fact["target_role_ack_reminder_allowed"])
        self.assertEqual(fact["controller_delivery_reissue_reason"], "controller_delivery_not_marked_done")
        self.assertTrue(fact["matching_controller_actions"])
    def test_missing_system_card_ack_after_controller_delivery_done_reminds_target_role(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        action = self.deliver_startup_fact_check_card_without_ack(root)
        state = read_json(router.run_state_path(run_root))
        router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router._write_controller_receipt(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            action_id=action["controller_action_id"],
            status="done",
            payload={"delivery_relayed": True},
        )
        router.save_run_state(run_root, state)

        result = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report_pre_ack_controller_delivery_done",
                self.startup_fact_report_body(root),
            ),
        )

        self.assertFalse(result["ok"])
        state = read_json(router.run_state_path(run_root))
        wait = state["pending_action"]
        self.assertEqual(wait["missing_ack_recovery"], "remind_target_role_to_ack_original_committed_card")
        self.assertEqual(wait["reminder_target"], "original_committed_card")
        self.assertTrue(wait["target_role_ack_reminder_allowed"])
        self.assertFalse(wait["controller_delivery_reissue_required_before_target_ack_reminder"])
        self.assertEqual(wait["controller_delivery_fact"]["controller_delivery_fact_status"], "controller_delivery_done")
    def test_user_intake_settlement_finalizer_waits_for_controller_mail_after_activation(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        self.deliver_expected_card(root, "pm.core")
        self.deliver_expected_card(root, "pm.output_contract_catalog")
        self.deliver_expected_card(root, "pm.role_work_request")
        self.deliver_expected_card(root, "pm.phase_map")
        self.deliver_expected_card(root, "pm.startup_intake")

        state = read_json(router.run_state_path(run_root))
        blocked = router._run_router_return_settlement_finalizers(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test_idempotent_return_settlement_before_activation",
        )
        self.assertFalse(blocked["changed"])
        self.assertEqual(blocked["startup_user_intake_release"]["reason"], "startup_activation_not_approved")
        self.assert_startup_user_intake_held_by_router(root)

        self.deliver_startup_fact_check_card(root)
        router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report",
                self.startup_fact_report_body(root),
            ),
        )
        self.deliver_expected_card(root, "pm.startup_activation")
        router.record_external_event(
            root,
            "pm_approves_startup_activation",
            self.role_decision_envelope(
                root,
                "startup/pm_startup_activation",
                {"approved_by_role": "project_manager", "decision": "approved"},
            ),
        )

        state = read_json(router.run_state_path(run_root))
        first = router._run_router_return_settlement_finalizers(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test_idempotent_return_settlement_first",
        )
        router.save_run_state(run_root, state)

        self.assertFalse(first["changed"])
        self.assertEqual(first["startup_user_intake_release"]["reason"], "controller_deliver_mail_required")
        self.assertEqual(first["startup_user_intake_release"]["requires_action"], "deliver_mail")
        self.assert_startup_user_intake_held_by_router(root)

        self.deliver_user_intake_mail(root)

        state = read_json(router.run_state_path(run_root))
        second = router._run_router_return_settlement_finalizers(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test_idempotent_return_settlement_second",
        )
        router.save_run_state(run_root, state)
        state = read_json(router.run_state_path(run_root))
        packet_ledger = read_json(run_root / "packet_ledger.json")
        self.assertFalse(second["changed"])
        self.assertEqual(second["startup_user_intake_release"]["reason"], "controller_deliver_mail_required")
        self.assertTrue(state["flags"]["user_intake_delivered_to_pm"])
        self.assertFalse(state["ledger_check_requested"])
        self.assertEqual(state["mail_deliveries"], 1)
        self.assertEqual(len(state["delivered_mail"]), 1)
        self.assertEqual(len(packet_ledger["mail"]), 1)
        self.assertEqual(packet_ledger["mail"][0]["mail_id"], "user_intake")
        self.assertEqual(packet_ledger["mail"][0]["to_role"], "project_manager")
        self.assertEqual(packet_ledger["mail"][0]["delivered_by"], "controller")
        self.assertEqual(packet_ledger["active_packet_holder"], "project_manager")
        self.assertEqual(packet_ledger["active_packet_status"], "envelope-relayed")
        self.assertEqual(packet_ledger["packets"][0]["active_packet_holder"], "project_manager")
        self.assertEqual(packet_ledger["packets"][0]["active_packet_status"], "envelope-relayed")
        self.assertNotIn("packet_router_release", packet_ledger["packets"][0])
        self.assertIn("packet_controller_relay", packet_ledger["packets"][0])
        self.assertEqual(packet_ledger["packets"][0]["packet_controller_relay"]["relayed_to_role"], "project_manager")
        self.assertIsNone(state.get("active_control_blocker"))
        self.assertEqual(len(packet_ledger["packets"][0]["holder_history"]), 2)
    def test_controller_action_reconciliation_ignores_transient_temp_files(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-transient-action-scan")
        state = read_json(router.run_state_path(run_root))
        action_dir = router._controller_actions_dir(run_root)  # type: ignore[attr-defined]
        action_dir.mkdir(parents=True, exist_ok=True)
        (action_dir / ".tmp-1234-action.json").write_text("{", encoding="utf-8")

        ledger = router._rebuild_controller_action_ledger(root, run_root, state)  # type: ignore[attr-defined]
        result = router._reconcile_scheduled_controller_action_receipts(root, run_root, state)  # type: ignore[attr-defined]

        self.assertEqual(ledger["actions"], [])
        self.assertFalse(result["changed"])
        self.assertIsNone(state.get("active_control_blocker"))
    def test_child_skill_gates_block_raw_inventory_and_controller_approval(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)

        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.dependency_policy")
        self.ack_system_card_action(root, action)
        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "pm_records_dependency_policy",
                {
                    "host_level_install_requested": True,
                    "explicit_user_approval_recorded": False,
                },
            )
        router.record_external_event(root, "pm_records_dependency_policy", {"allowed_dependency_actions": ["use_existing_local_skill"]})

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_capabilities_manifest", {"raw_inventory_is_authority": True})
        router.record_external_event(
            root,
            "pm_writes_capabilities_manifest",
            {"capabilities": [{"capability_id": "cap-001", "behavior": "route capability"}]},
        )

        self.deliver_expected_card(root, "pm.child_skill_selection")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_child_skill_selection", {"raw_inventory_used_as_authority": True})
        controller_selected_skill = [
            {
                "skill_name": "bad-controller-approved-skill",
                "decision": "required",
                "gates": [{"gate_id": "bad", "required_approver": "controller", "controller_can_approve": True}],
            }
        ]
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_child_skill_selection", {"selected_skills": controller_selected_skill})
        safe_selected_skill = [
            {
                "skill_name": "model-first-function-flow",
                "decision": "required",
                "supported_capabilities": ["cap-001"],
                "gates": [
                    {
                        "gate_id": "process-model",
                        "required_approver": "process_flowguard_officer",
                        "controller_can_approve": False,
                    }
                ],
            }
        ]
        router.record_external_event(root, "pm_writes_child_skill_selection", {"selected_skills": safe_selected_skill})

        self.deliver_expected_card(root, "pm.child_skill_gate_manifest")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_child_skill_gate_manifest", {"selected_skills": controller_selected_skill})

        router.record_external_event(root, "pm_writes_child_skill_gate_manifest", {"selected_skills": safe_selected_skill})
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_approves_child_skill_manifest_for_route")

        self.deliver_expected_card(root, "reviewer.child_skill_gate_manifest_review")
        router.record_external_event(
            root,
            "reviewer_passes_child_skill_gate_manifest",
            self.role_report_envelope(
                root,
                "reviews/child_skill_gate_manifest_review",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )
        manifest_after_review = read_json(run_root / "child_skill_gate_manifest.json")
        self.assertTrue(manifest_after_review["approval"]["reviewer_passed"])
        self.assertFalse(manifest_after_review["approval"]["pm_approved_for_route"])
        router.record_external_event(root, "pm_approves_child_skill_manifest_for_route")
        manifest_after_approval = read_json(run_root / "child_skill_gate_manifest.json")
        self.assertTrue(manifest_after_approval["approval"]["reviewer_passed"])
        self.assertFalse(manifest_after_approval["approval"]["process_officer_passed"])
        self.assertTrue(manifest_after_approval["approval"]["process_officer_default_gate_removed"])
        self.assertFalse(manifest_after_approval["approval"]["product_officer_passed"])
        self.assertTrue(manifest_after_approval["approval"]["product_officer_default_gate_removed"])
        self.assertFalse((run_root / "flowguard" / "child_skill_conformance_model.json").exists())
        self.assertFalse((run_root / "flowguard" / "child_skill_product_fit.json").exists())
        self.assertFalse((run_root / "capabilities" / "capability_sync.json").exists())
        stale_state = read_json(router.run_state_path(run_root))
        stale_state["pending_action"] = {
            "action_type": "await_role_decision",
            "actor": "controller",
            "label": "controller_waits_for_expected_event_capability_evidence_synced",
            "summary": "Legacy stale wait for Router-owned capability evidence sync.",
            "allowed_external_events": ["capability_evidence_synced"],
            "to_role": "controller",
        }
        router.write_json(router.run_state_path(run_root), stale_state)

        action = self.next_after_display_sync(root)

        self.assertTrue((run_root / "capabilities" / "capability_sync.json").exists())
        state_after_sync = read_json(router.run_state_path(run_root))
        self.assertTrue(state_after_sync["flags"]["capability_evidence_synced"])
        pending_after_sync = state_after_sync.get("pending_action")
        if isinstance(pending_after_sync, dict):
            self.assertNotIn("capability_evidence_synced", pending_after_sync.get("allowed_external_events") or [])
        self.assertFalse(
            action["action_type"] == "await_role_decision"
            and "capability_evidence_synced" in (action.get("allowed_external_events") or [])
        )
    def test_controller_repair_work_packet_queues_bounded_controller_action(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="Controller needs a bounded repair packet",
            action_type="controller_no_legal_next_action",
            payload={"path": self.rel(root, state_path), "role": "controller"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))
        decision = self.pm_control_blocker_decision_body(
            blocker["blocker_id"],
            rerun_target="host_records_heartbeat_binding",
        )
        decision["repair_transaction"] = {
            "plan_kind": "controller_repair_work_packet",
            "work_packet": {
                "allowed_reads": [self.rel(root, state_path)],
                "allowed_writes": [self.rel(root, state_path)],
                "forbidden_actions": [
                    "approve gates",
                    "mutate routes",
                    "read sealed bodies",
                ],
                "success_evidence": ["controller records bounded repair evidence"],
            },
        }
        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(root, "control_blocks/controller_repair_packet_pm_decision", decision),
        )

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "controller_repair_work_packet")
        self.assertFalse(action["controller_may_approve_gate"])
        self.assertFalse(action["controller_may_mutate_route"])
        self.assertFalse(action["controller_may_read_sealed_bodies"])
        self.assertEqual(action["repair_execution_plan"]["mode"], "controller_repair_work_packet")
        result = router.apply_action(
            root,
            "controller_repair_work_packet",
            {"status": "done", "evidence": ["controller records bounded repair evidence"]},
        )
        self.assertEqual(result["repair_transaction_id"], action["repair_transaction_id"])
        transaction = read_json(run_root / "control_blocks" / "repair_transactions" / f"{action['repair_transaction_id']}.json")
        self.assertEqual(transaction["status"], "awaiting_recheck")
        self.assertEqual(transaction["controller_repair_work_packet_result"]["status"], "done")
    def test_controller_boundary_confirmation_records_envelope_only_event(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)

        next_action = self.next_after_display_sync(root)
        self.assertNotEqual(next_action["action_type"], "confirm_controller_core_boundary")
        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        self.assertTrue(state["flags"]["controller_role_confirmed"])
        boundary_events = [
            item for item in state["events"]
            if item.get("event") == "controller_role_confirmed_from_router_core"
        ]
        self.assertTrue(boundary_events)
        self.assertIn("path", boundary_events[-1]["payload"])
        self.assertIn("sha256", boundary_events[-1]["payload"])
        confirmation = state["controller_boundary_confirmation"]
        self.assertEqual(
            confirmation["output_contract_id"],
            "flowpilot.output_contract.controller_boundary_confirmation.v1",
        )
        self.assertEqual(confirmation["output_type"], "controller_boundary_confirmation")
        self.assertEqual(confirmation["role_output_envelope"]["controller_visibility"], "role_output_envelope_only")
    def test_controller_boundary_done_receipt_missing_deliverable_schedules_repair(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)

        run_root, state, action = self.legacy_controller_boundary_action(root)
        self.assertEqual(action["action_type"], "confirm_controller_core_boundary")
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        state["pending_action"] = action
        router._write_controller_receipt(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            action_id=entry["action_id"],
            status="done",
            payload={"controller_action_completed": True},
        )
        router.save_run_state(run_root, state)

        repair = self.next_after_display_sync(root)
        self.assertEqual(repair["action_type"], "complete_missing_controller_deliverable")
        self.assertEqual(repair["repair_of_controller_action_id"], entry["action_id"])
        self.assertEqual(repair["repair_attempt"], 1)
        original = read_json(router._controller_action_path(run_root, entry["action_id"]))  # type: ignore[attr-defined]
        self.assertEqual(original["status"], "repair_pending")
        self.assertEqual(original["deliverable_repair_attempts"], 1)
        self.assertEqual(original["deliverable_repair_failed_receipts"], 0)
        self.assertEqual(original["pending_deliverable_repair_action_id"], repair["controller_action_id"])
        self.assertEqual(original["pending_deliverable_repair_attempt"], 1)
        self.assertEqual(original["missing_deliverables"][0]["deliverable_id"], "controller_boundary_confirmation")
        self.assertEqual(
            original["missing_deliverables"][0]["output_contract_id"],
            "flowpilot.output_contract.controller_boundary_confirmation.v1",
        )
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state.get("active_control_blocker"))
    def test_controller_boundary_valid_artifact_reclaims_before_repair(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)

        run_root, state, action = self.legacy_controller_boundary_action(root)
        self.assertEqual(action["action_type"], "confirm_controller_core_boundary")
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router._write_controller_boundary_confirmation(root, run_root, state)  # type: ignore[attr-defined]
        state["pending_action"] = action
        router._write_controller_receipt(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            action_id=entry["action_id"],
            status="done",
            payload={"controller_action_completed": True},
        )
        router.save_run_state(run_root, state)

        next_action = self.next_after_display_sync(root)
        self.assertNotEqual(next_action["action_type"], "complete_missing_controller_deliverable")
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["controller_role_confirmed"])
        self.assertTrue(state["flags"]["controller_boundary_confirmation_written"])
        self.assertFalse(state.get("active_control_blocker"))
    def test_controller_boundary_handwritten_artifact_without_runtime_evidence_schedules_repair(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)

        run_root, state, action = self.legacy_controller_boundary_action(root)
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        body = router._controller_boundary_confirmation_body(root, run_root, state)  # type: ignore[attr-defined]
        router.write_json(run_root / "startup" / "controller_boundary_confirmation.json", body)
        state["pending_action"] = action
        router._write_controller_receipt(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            action_id=entry["action_id"],
            status="done",
            payload={"controller_action_completed": True},
        )
        router.save_run_state(run_root, state)

        repair = self.next_after_display_sync(root)
        self.assertEqual(repair["action_type"], "complete_missing_controller_deliverable")
        self.assertFalse(read_json(router.run_state_path(run_root)).get("active_control_blocker"))
    def test_controller_boundary_repair_action_resolves_original(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)

        run_root, state, action = self.legacy_controller_boundary_action(root)
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        state["pending_action"] = action
        router._write_controller_receipt(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            action_id=entry["action_id"],
            status="done",
            payload={"controller_action_completed": True},
        )
        router.save_run_state(run_root, state)
        repair = self.next_after_display_sync(root)

        result = router.apply_action(root, "complete_missing_controller_deliverable")
        self.assertTrue(result["ok"])
        self.assertEqual(result["repair_of_controller_action_id"], entry["action_id"])
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["controller_role_confirmed"])
        original = read_json(router._controller_action_path(run_root, entry["action_id"]))  # type: ignore[attr-defined]
        repair_entry = read_json(router._controller_action_path(run_root, repair["controller_action_id"]))  # type: ignore[attr-defined]
        self.assertEqual(original["status"], "resolved")
        self.assertEqual(original["resolved_by_controller_action_id"], repair["controller_action_id"])
        self.assertIsNone(original["pending_deliverable_repair_action_id"])
        self.assertEqual(original["pending_deliverable_repair_attempt"], 0)
        self.assertEqual(repair_entry["status"], "done")
    def test_controller_boundary_repair_budget_escalates_after_two_failures(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)

        run_root, state, action = self.legacy_controller_boundary_action(root)
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        state["pending_action"] = action
        router._write_controller_receipt(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            action_id=entry["action_id"],
            status="done",
            payload={"controller_action_completed": True},
        )
        router.save_run_state(run_root, state)
        repair_1 = self.next_after_display_sync(root)
        router.record_controller_action_receipt(
            root,
            action_id=repair_1["controller_action_id"],
            status="done",
            payload={"controller_action_completed": True},
        )
        state = read_json(router.run_state_path(run_root))
        repair_2 = state["pending_action"]
        self.assertEqual(repair_2["action_type"], "complete_missing_controller_deliverable")
        self.assertEqual(repair_2["repair_attempt"], 2)
        original = read_json(router._controller_action_path(run_root, entry["action_id"]))  # type: ignore[attr-defined]
        self.assertEqual(original["deliverable_repair_attempts"], 2)
        self.assertEqual(original["deliverable_repair_failed_receipts"], 1)
        self.assertEqual(original["pending_deliverable_repair_action_id"], repair_2["controller_action_id"])
        self.assertFalse(state.get("active_control_blocker"))

        router.record_controller_action_receipt(
            root,
            action_id=repair_2["controller_action_id"],
            status="done",
            payload={"controller_action_completed": True},
        )

        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state.get("active_control_blocker"))
        original = read_json(router._controller_action_path(run_root, entry["action_id"]))  # type: ignore[attr-defined]
        self.assertEqual(original["status"], "blocked")
        self.assertEqual(original["deliverable_repair_attempts"], 2)
        self.assertEqual(original["deliverable_repair_failed_receipts"], 2)
    def test_controller_boundary_duplicate_old_receipt_does_not_block_while_second_repair_pending(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)

        run_root, state, action = self.legacy_controller_boundary_action(root)
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        state["pending_action"] = action
        router._write_controller_receipt(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            action_id=entry["action_id"],
            status="done",
            payload={"controller_action_completed": True},
        )
        router.save_run_state(run_root, state)
        repair_1 = self.next_after_display_sync(root)
        router.record_controller_action_receipt(
            root,
            action_id=repair_1["controller_action_id"],
            status="done",
            payload={"controller_action_completed": True},
        )
        state = read_json(router.run_state_path(run_root))
        repair_2 = state["pending_action"]
        self.assertEqual(repair_2["repair_attempt"], 2)

        duplicate = router._schedule_controller_deliverable_repair(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            pending_action=repair_1,
            receipt=read_json(router._controller_receipt_path(run_root, repair_1["controller_action_id"])),  # type: ignore[attr-defined]
            apply_result={
                "applied": False,
                "repairable": True,
                "missing_deliverables": repair_1["missing_deliverables"],
            },
            source="duplicate_old_repair_receipt_replay",
        )

        self.assertFalse(duplicate["scheduled"])
        self.assertTrue(duplicate["pending_repair"])
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state.get("active_control_blocker"))
        original = read_json(router._controller_action_path(run_root, entry["action_id"]))  # type: ignore[attr-defined]
        self.assertEqual(original["status"], "repair_pending")
        self.assertEqual(original["deliverable_repair_attempts"], 2)
        self.assertEqual(original["deliverable_repair_failed_receipts"], 1)
