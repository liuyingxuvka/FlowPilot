from __future__ import annotations

import time

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class ControllerRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_all_passive_wait_types_are_status_projections_not_work_rows(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        passive_actions = [
            router.make_action(
                action_type="await_role_decision",
                actor="controller",
                label="test_wait_role",
                summary="Wait for role output.",
                to_role="project_manager",
                extra={"allowed_external_events": ["pm_resume_recovery_decision_returned"]},
            ),
            router.make_action(
                action_type="await_card_return_event",
                actor="controller",
                label="test_wait_card",
                summary="Wait for card ACK.",
                to_role="project_manager",
                extra={"expected_return_path": "runtime/card_returns/test-card.json"},
            ),
            router.make_action(
                action_type="await_card_bundle_return_event",
                actor="controller",
                label="test_wait_bundle",
                summary="Wait for bundled card ACK.",
                to_role="project_manager",
                extra={"expected_return_path": "runtime/card_returns/test-bundle.json"},
            ),
            router.make_action(
                action_type="await_current_scope_reconciliation",
                actor="controller",
                label="test_wait_scope_reconciliation",
                summary="Wait for local reconciliation.",
                to_role="controller",
                extra={"scope_kind": "current_node", "scope_id": "node-001", "blockers": [{"kind": "test"}]},
            ),
        ]

        for action in passive_actions:
            router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)

        ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        ordinary_types = [item.get("action_type") for item in ledger["actions"]]
        passive_types = [item.get("action_type") for item in ledger["passive_waits"]]
        for action_type in router.PASSIVE_WAIT_STATUS_ACTION_TYPES:
            self.assertNotIn(action_type, ordinary_types)
            self.assertIn(action_type, passive_types)
        self.assertEqual(ledger["passive_wait_count"], len(router.PASSIVE_WAIT_STATUS_ACTION_TYPES))

    def test_done_receipt_rejects_failed_delivery_payload(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        action = router.make_action(
            action_type="send_wait_target_reminder",
            actor="controller",
            label="controller_sends_wait_target_reminder",
            summary="Send reminder to waiting role.",
            to_role="worker",
            extra={"postcondition": "wait_target_reminder_sent"},
        )
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)

        with self.assertRaisesRegex(router.RouterError, "cannot report failed delivery"):
            router.record_controller_action_receipt(
                root,
                action_id=entry["action_id"],
                status="done",
                payload={
                    "message_delivery_status": "failed_agent_not_found",
                    "message_delivery_error": "target not found",
                },
            )

    def test_current_work_uses_packet_holder_when_pending_wait_is_empty(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-current-work-packet")
        state = read_json(router.run_state_path(run_root))
        state["pending_action"] = None
        router.save_run_state(run_root, state)
        router.write_json(
            run_root / "packet_ledger.json",
            {
                "schema_version": router.PACKET_LEDGER_SCHEMA,
                "run_id": "run-current-work-packet",
                "active_packet_id": "user_intake",
                "active_packet_status": "packet-body-opened-by-recipient",
                "active_packet_holder": "project_manager",
                "packets": [
                    {
                        "packet_id": "user_intake",
                        "active_packet_status": "packet-body-opened-by-recipient",
                        "active_packet_holder": "project_manager",
                    }
                ],
                "mail": [],
                "updated_at": router.utc_now(),
            },
        )

        daemon_status = router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
        )
        router._write_current_status_summary(run_root, state)  # type: ignore[attr-defined]
        status_summary = read_json(run_root / "display" / "current_status_summary.json")
        snapshot = router._build_foreground_controller_standby_snapshot(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            started_at=router.utc_now(),
            start_monotonic=time.monotonic(),
            poll_count=0,
            max_seconds=0,
            poll_seconds=0.1,
        )

        self.assertIsNone(daemon_status["current_wait"]["waiting_for_role"])
        self.assertEqual(daemon_status["current_work"]["owner_kind"], "role")
        self.assertEqual(daemon_status["current_work"]["owner_key"], "project_manager")
        self.assertEqual(daemon_status["current_work"]["source"], "packet_ledger")
        self.assertEqual(status_summary["current_work"]["owner_key"], "project_manager")
        self.assertEqual(status_summary["current_work"]["packet_id"], "user_intake")
        self.assertEqual(snapshot["current_work"]["owner_key"], "project_manager")
    def test_current_work_uses_passive_reconciliation_owner_when_pending_wait_is_empty(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-current-work-passive")
        state = read_json(router.run_state_path(run_root))
        state["pending_action"] = None
        passive_action = router.make_action(
            action_type="await_current_scope_reconciliation",
            actor="controller",
            label="controller_reconciles_current_scope",
            summary="Reconcile current scope before continuing.",
            to_role="controller",
            extra={"scope_kind": "startup", "scope_id": "startup", "blockers": [{"kind": "test"}]},
        )
        router._write_controller_action_entry(root, run_root, state, passive_action)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)

        daemon_status = router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
        )
        router._write_current_status_summary(run_root, state)  # type: ignore[attr-defined]
        status_summary = read_json(run_root / "display" / "current_status_summary.json")

        self.assertIsNone(daemon_status["current_wait"]["waiting_for_role"])
        self.assertEqual(daemon_status["current_work"]["owner_kind"], "controller")
        self.assertEqual(daemon_status["current_work"]["owner_key"], "controller")
        self.assertEqual(daemon_status["current_work"]["source"], "controller_action_ledger.passive_waits")
        self.assertIn("Reconcile current scope", daemon_status["current_work"]["task_label"])
        self.assertEqual(status_summary["current_work"]["owner_key"], "controller")
        self.assertEqual(status_summary["current_work"]["source"], "controller_action_ledger.passive_waits")

    def test_current_status_summary_marks_stale_pending_projection_display_only(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        action = router.make_action(
            action_type="write_display_surface_status",
            actor="controller",
            label="stale_display_status_projection",
            summary="Display status action that has already been receipted.",
            extra={"postcondition": "startup_display_status_written"},
        )
        state["pending_action"] = action
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router._write_controller_receipt(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            action_id=entry["action_id"],
            status="done",
            payload={"display_confirmation": {"rendered_to": "chat"}},
        )
        router.save_run_state(run_root, state)

        router._write_current_status_summary(run_root, state)  # type: ignore[attr-defined]
        status_summary = read_json(run_root / "display" / "current_status_summary.json")

        self.assertEqual(status_summary["state_kind"], "running")
        self.assertTrue(status_summary["projection_authority"]["display_only"])
        self.assertFalse(status_summary["projection_authority"]["controller_stop_authority"])
        self.assertEqual(
            status_summary["projection_authority"]["control_authorities"],
            ["runtime/router_daemon_status.json", "runtime/controller_action_ledger.json"],
        )
        self.assertEqual(status_summary["next_step"]["action_type"], "write_display_surface_status")
        self.assertEqual(status_summary["next_step"]["source_action_id"], entry["action_id"])
        self.assertFalse(status_summary["next_step"]["fresh_for_controller_decision"])
        self.assertTrue(status_summary["next_step"]["display_only"])
        self.assertFalse(status_summary["next_step"]["controller_stop_authority"])
        self.assertNotEqual(status_summary["current_work"]["source"], "pending_action")
        self.assertFalse(status_summary["foreground_exit_policy"]["controller_stop_allowed"])
        self.assertFalse(status_summary["foreground_exit_policy"]["final_answer_preflight"]["final_answer_allowed"])

    def test_router_daemon_status_projects_protocol_dead_end_terminal_boundary(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        state["status"] = "protocol_dead_end"
        state["phase"] = "terminal"
        state.setdefault("flags", {})["control_blocker_protocol_dead_end_declared"] = True
        state["daemon_mode_enabled"] = True
        router.save_run_state(run_root, state)

        daemon_status = router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
        )

        self.assertEqual(daemon_status["lifecycle_status"], "terminal_stopped")
        self.assertEqual(daemon_status["run_lifecycle_status"], "protocol_dead_end")
        self.assertEqual(daemon_status["control_projection"]["projection_kind"], "protocol_dead_end")
        self.assertTrue(daemon_status["control_projection"]["controller_stop_allowed"])
        self.assertFalse(daemon_status["control_projection"]["work_chain_liveness_claimed"])
        self.assertTrue(daemon_status["control_projection"]["daemon_patrol_is_liveness_only"])

    def test_foreground_receipt_defers_scheduler_fold_to_live_daemon(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        state = read_json(router.run_state_path(run_root))
        state["daemon_mode_enabled"] = True
        router.save_run_state(run_root, state)
        router._acquire_router_daemon_lock(root, run_root, state, replace_stale=True)  # type: ignore[attr-defined]
        action = router.make_action(
            action_type="write_display_surface_status",
            actor="controller",
            label="test_foreground_receipt_fold_deferral",
            summary="Write display status.",
            extra={"postcondition": "startup_display_status_written"},
        )

        try:
            entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
            row_id = entry["router_scheduler_row_id"]
            router._write_controller_receipt(  # type: ignore[attr-defined]
                root,
                run_root,
                state,
                action_id=entry["action_id"],
                status="done",
                payload={"completed_by_test_controller": True},
            )

            deferred_action = read_json(run_root / "runtime" / "controller_actions" / f"{entry['action_id']}.json")
            scheduler = read_json(run_root / "runtime" / "router_scheduler_ledger.json")
            row = next(item for item in scheduler["rows"] if item["row_id"] == row_id)
            self.assertTrue(deferred_action["router_scheduler_fold_deferred"])
            self.assertEqual(deferred_action["router_scheduler_fold_deferred_reason"], "live_daemon_owns_scheduler_ledger")
            self.assertEqual(row["router_state"], "queued")

            result = router._reconcile_controller_receipts(  # type: ignore[attr-defined]
                root,
                run_root,
                state,
                scheduler_fold_owner="daemon",
            )

            folded_action = read_json(run_root / "runtime" / "controller_actions" / f"{entry['action_id']}.json")
            scheduler = read_json(run_root / "runtime" / "router_scheduler_ledger.json")
            row = next(item for item in scheduler["rows"] if item["row_id"] == row_id)
            self.assertGreaterEqual(result["scheduler_folds"], 1)
            self.assertFalse(folded_action.get("router_scheduler_fold_deferred", False))
            self.assertEqual(row["router_state"], "receipt_done")
        finally:
            router._release_router_daemon_lock(  # type: ignore[attr-defined]
                root,
                run_root,
                reason="test_foreground_receipt_defers_scheduler_fold_to_live_daemon",
            )

    def test_resolved_scope_wait_is_superseded_and_clears_pending_projection(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)
        state = read_json(router.run_state_path(run_root))
        action = router.make_action(
            action_type="await_current_scope_reconciliation",
            actor="controller",
            label="test_resolved_scope_wait",
            summary="Wait for a scope that is already resolved.",
            to_role="controller",
            extra={"scope_kind": "startup", "scope_id": "startup", "blockers": [{"kind": "stale"}]},
        )
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        state["pending_action"] = action
        router.save_run_state(run_root, state)

        result = router._reconcile_scheduled_controller_action_receipts(root, run_root, state)  # type: ignore[attr-defined]

        self.assertTrue(result["changed"])
        self.assertEqual(result["superseded"], 1)
        self.assertIsNone(state.get("pending_action"))
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{entry['action_id']}.json")
        self.assertEqual(action_record["status"], "superseded")
        self.assertEqual(action_record["router_reconciliation_status"], "superseded_by_resolved_current_scope")
        scheduler = read_json(run_root / "runtime" / "router_scheduler_ledger.json")
        row = next(item for item in scheduler["rows"] if item["row_id"] == entry["router_scheduler_row_id"])
        self.assertEqual(row["router_state"], "superseded")

    def test_reconciled_scheduler_row_is_not_downgraded_by_later_receipt_sync(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        action = router.make_action(
            action_type="write_display_surface_status",
            actor="controller",
            label="test_reconciled_scheduler_row",
            summary="Test scheduler reconciliation monotonicity.",
            extra={"postcondition": "startup_display_status_written"},
        )
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        row_id = entry["router_scheduler_row_id"]
        router._update_router_scheduler_row(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            row_id=row_id,
            router_state="reconciled",
            reconciliation={"source": "test_reconciliation"},
        )
        router._update_router_scheduler_row(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            row_id=row_id,
            router_state="receipt_done",
            reconciliation={"source": "late_receipt_sync"},
        )

        scheduler = read_json(run_root / "runtime" / "router_scheduler_ledger.json")
        row = next(item for item in scheduler["rows"] if item["row_id"] == row_id)
        self.assertEqual(row["router_state"], "reconciled")
        self.assertEqual(row["reconciliation"]["source"], "test_reconciliation")
        self.assertEqual(row["reconciliation"]["latest_receipt_sync"]["source"], "late_receipt_sync")
    def test_sync_display_plan_done_receipt_updates_router_fact_before_next_action(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)

        result = router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)
        action_id = result["last_tick"]["controller_action_id"]
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{action_id}.json")
        self.assertEqual(action_record["action_type"], "sync_display_plan")
        self.assert_controller_receipt_entry_projection(action_record)

        router.record_controller_action_receipt(
            root,
            action_id=action_id,
            status="done",
            payload={"completed_by_test_controller": True},
        )

        next_action = router.next_action(root)

        self.assertNotEqual(next_action["action_type"], "sync_display_plan")
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["visible_plan_synced"])
        self.assertIn("visible_plan_sync", state)
        self.assertEqual(state["visible_plan_sync"]["host_action"], "replace_visible_plan")
        self.assertNotEqual((state.get("pending_action") or {}).get("controller_action_id"), action_id)
        labels = [item["label"] for item in state["history"] if isinstance(item, dict)]
        self.assertIn("router_reconciled_pending_controller_action_receipt", labels)

