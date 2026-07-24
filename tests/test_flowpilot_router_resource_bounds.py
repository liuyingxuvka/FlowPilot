from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from unittest import mock

from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase, read_json, router


def _file_identity(path: Path) -> tuple[str, int, int]:
    return (
        hashlib.sha256(path.read_bytes()).hexdigest(),
        path.stat().st_mtime_ns,
        path.stat().st_size,
    )


class FlowPilotRouterResourceBoundsTests(FlowPilotRouterRuntimeTestBase):
    def make_bounded_project(self) -> tuple[Path, Path]:
        root = self.make_project()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        return root, self.write_minimal_run(root, "run-resource-bounds")

    def test_save_run_state_skips_ten_thousand_semantically_identical_writes(self) -> None:
        root, run_root = self.make_bounded_project()
        del root
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        state["pending_action"] = {
            "action_type": "await_role_decision",
            "label": "bounded_wait",
            "seen_count": 10_000,
            "last_seen_at": "2026-07-24T00:00:00Z",
            "wait_reminder_history": [
                {
                    "delivered_at": "2026-07-24T00:00:00Z",
                    "reminder_text_sha256": "legacy-growth",
                }
            ],
            "last_wait_reminder_at": "2026-07-24T00:00:00Z",
            "last_wait_reminder_sha256": "current-reminder",
        }
        self.assertTrue(router.save_run_state(run_root, state))
        persisted = read_json(state_path)
        self.assertNotIn("seen_count", persisted["pending_action"])
        self.assertNotIn("last_seen_at", persisted["pending_action"])
        self.assertNotIn("wait_reminder_history", persisted["pending_action"])
        baseline = _file_identity(state_path)

        writes = sum(bool(router.save_run_state(run_root, state)) for _ in range(10_000))

        self.assertEqual(writes, 0)
        self.assertEqual(_file_identity(state_path), baseline)

    def test_same_action_and_receipt_are_single_commit_across_ten_thousand_replays(self) -> None:
        root, run_root = self.make_bounded_project()
        state = read_json(router.run_state_path(run_root))
        state["daemon_mode_enabled"] = False
        router._ensure_controller_action_ledger(root, run_root, state)  # type: ignore[attr-defined]
        router._ensure_router_scheduler_ledger(root, run_root, state)  # type: ignore[attr-defined]
        router._ensure_router_ownership_ledger(root, run_root, state)  # type: ignore[attr-defined]
        action = router.make_action(
            action_type="resource_bound_test_action",
            actor="controller",
            label="resource_bound_test_action",
            summary="Exercise semantic controller receipt idempotency.",
            extra={
                "scope_kind": "run",
                "scope_id": "run",
                "idempotency_key": "resource-bound-test-action",
            },
        )
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        action_id = str(entry["action_id"])
        receipt = router._write_controller_receipt(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            action_id=action_id,
            status="done",
            payload={"result": "completed-once"},
        )
        router._reconcile_scheduled_controller_action_receipts(root, run_root, state)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)

        paths = {
            "state": router.run_state_path(run_root),
            "action": router._controller_action_path(run_root, action_id),  # type: ignore[attr-defined]
            "receipt": router._controller_receipt_path(run_root, action_id),  # type: ignore[attr-defined]
            "controller": router._controller_action_ledger_path(run_root),  # type: ignore[attr-defined]
            "scheduler": router._router_scheduler_ledger_path(run_root),  # type: ignore[attr-defined]
            "ownership": router._router_ownership_ledger_path(run_root),  # type: ignore[attr-defined]
        }
        baseline = {name: _file_identity(path) for name, path in paths.items()}
        history_count = len(state.get("history") or [])

        replay_receipts = [
            router._write_controller_receipt(  # type: ignore[attr-defined]
                root,
                run_root,
                state,
                action_id=action_id,
                status="done",
                payload={"result": "completed-once"},
            )
            for _ in range(10_000)
        ]
        replay_entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        summary = router._reconcile_controller_receipts(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            scheduler_fold_owner="daemon",
        )
        router._reconcile_scheduled_controller_action_receipts(root, run_root, state)  # type: ignore[attr-defined]
        self.assertFalse(router.save_run_state(run_root, state))

        self.assertTrue(all(item == receipt for item in replay_receipts))
        self.assertEqual(replay_entry["action_id"], action_id)
        self.assertEqual(summary["already_current_receipts"], 1)
        self.assertEqual({name: _file_identity(path) for name, path in paths.items()}, baseline)
        self.assertEqual(len(state.get("history") or []), history_count)
        self.assertEqual(len(list(router._controller_actions_dir(run_root).glob("*.json"))), 1)  # type: ignore[attr-defined]
        self.assertEqual(len(list(router._controller_receipts_dir(run_root).glob("*.json"))), 1)  # type: ignore[attr-defined]
        controller = read_json(paths["controller"])
        scheduler = read_json(paths["scheduler"])
        self.assertEqual(len(controller["actions"]), 1)
        self.assertEqual(len(scheduler["rows"]), 1)
        self.assertNotIn("seen_count", controller["actions"][0])
        self.assertNotIn("last_seen_at", controller["actions"][0])

        with self.assertRaises(router.RouterError):
            router._write_controller_receipt(  # type: ignore[attr-defined]
                root,
                run_root,
                state,
                action_id=action_id,
                status="done",
                payload={"result": "conflicting-second-result"},
            )
        self.assertEqual(_file_identity(paths["receipt"]), baseline["receipt"])

    def test_wait_reminder_replay_keeps_only_compact_current_owner_fields(self) -> None:
        root, run_root = self.make_bounded_project()
        state = read_json(router.run_state_path(run_root))
        return_ledger_path = run_root / "return_event_ledger.json"
        router.write_json(
            return_ledger_path,
            {
                "schema_version": router.RETURN_EVENT_LEDGER_SCHEMA,
                "run_id": state["run_id"],
                "pending_returns": [
                    {
                        "return_id": "pm-ack",
                        "return_kind": "system_card",
                        "status": "awaiting_return",
                        "target_role": "project_manager",
                        "expected_return_path": "mailbox/outbox/card_acks/pm.ack.json",
                        "wait_reminder_history": [
                            {"delivered_at": f"2026-07-24T00:00:{index:02d}Z"}
                            for index in range(60)
                        ],
                    }
                ],
                "completed_returns": [],
                "updated_at": "2026-07-24T00:00:00Z",
            },
        )
        action = {
            "action_type": router.WAIT_TARGET_REMINDER_ACTION_TYPE,
            "wait_class": "ack",
            "target_role": "project_manager",
            "expected_return_path": "mailbox/outbox/card_acks/pm.ack.json",
        }
        delivered_at = "2026-07-24T01:00:00Z"
        first = router._mark_pending_return_wait_reminded(  # type: ignore[attr-defined]
            run_root,
            state["run_id"],
            action,
            delivered_at=delivered_at,
            reminder_hash="reminder-sha256",
            receipt_payload={},
        )
        baseline = _file_identity(return_ledger_path)
        second = router._mark_pending_return_wait_reminded(  # type: ignore[attr-defined]
            run_root,
            state["run_id"],
            action,
            delivered_at=delivered_at,
            reminder_hash="reminder-sha256",
            receipt_payload={},
        )

        self.assertTrue(first["changed"])
        self.assertFalse(second["changed"])
        self.assertEqual(_file_identity(return_ledger_path), baseline)
        pending = read_json(return_ledger_path)["pending_returns"][0]
        self.assertEqual(pending["status"], "reminded")
        self.assertEqual(pending["last_wait_reminder_at"], delivered_at)
        self.assertEqual(pending["last_wait_reminder_sha256"], "reminder-sha256")
        self.assertNotIn("wait_reminder_history", pending)

    def test_actual_observe_ticks_update_liveness_without_semantic_rewrites(self) -> None:
        root, run_root = self.make_bounded_project()
        state = read_json(router.run_state_path(run_root))
        lock = router._acquire_router_daemon_lock(root, run_root, state)  # type: ignore[attr-defined]
        router._ensure_daemon_runtime_state(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_observing",
        )
        router.save_run_state(run_root, state)
        semantic_paths = {
            "state": router.run_state_path(run_root),
            "controller": router._controller_action_ledger_path(run_root),  # type: ignore[attr-defined]
            "scheduler": router._router_scheduler_ledger_path(run_root),  # type: ignore[attr-defined]
            "ownership": router._router_ownership_ledger_path(run_root),  # type: ignore[attr-defined]
        }
        baseline = {name: _file_identity(path) for name, path in semantic_paths.items()}

        first = router._router_daemon_tick(root, run_root, state, observe_only=True)  # type: ignore[attr-defined]
        second = router._router_daemon_tick(root, run_root, state, observe_only=True)  # type: ignore[attr-defined]

        self.assertFalse(first["semantic_changed"])
        self.assertFalse(first["state_written"])
        self.assertFalse(second["semantic_changed"])
        self.assertFalse(second["state_written"])
        self.assertEqual({name: _file_identity(path) for name, path in semantic_paths.items()}, baseline)
        status = read_json(router._router_daemon_status_path(run_root))  # type: ignore[attr-defined]
        self.assertEqual(status["tick_interval_seconds"], 1)
        self.assertTrue(status["last_tick_at"])
        self.assertTrue(status["daemon_live"])
        router._release_router_daemon_lock(  # type: ignore[attr-defined]
            root,
            run_root,
            reason="test_complete",
            status="released",
        )

    def test_ten_thousand_tick_daemon_result_is_bounded_and_has_no_tick_array(self) -> None:
        root, run_root = self.make_bounded_project()
        state = read_json(router.run_state_path(run_root))
        state["router_daemon_status_path"] = router.project_relative(  # type: ignore[attr-defined]
            root,
            router._router_daemon_status_path(run_root),  # type: ignore[attr-defined]
        )
        router.save_run_state(run_root, state)
        state_baseline = _file_identity(router.run_state_path(run_root))

        def no_change_tick(
            project_root: Path,
            target_run_root: Path,
            target_state: dict,
            *,
            observe_only: bool,
        ) -> dict:
            del project_root, target_run_root, target_state
            return {
                "tick_at": "2026-07-24T01:00:00Z",
                "observe_only": observe_only,
                "semantic_state_changed": False,
                "projection_changed": False,
                "frontier_advanced": False,
                "semantic_changed": False,
                "state_written": False,
                "change_reasons": [],
                "terminal": False,
            }

        with (
            mock.patch.object(router, "_ensure_daemon_runtime_state", return_value={}),
            mock.patch.object(router, "_router_daemon_tick", side_effect=no_change_tick),
            mock.patch.object(router.time, "sleep", return_value=None),
        ):
            result = router.run_router_daemon(
                root,
                max_ticks=10_000,
                observe_only=True,
                release_lock_on_exit=True,
                run_root=run_root,
            )

        self.assertEqual(result["tick_interval_seconds"], 1)
        self.assertEqual(result["tick_count"], 10_000)
        self.assertEqual(result["semantic_change_count"], 0)
        self.assertEqual(result["no_change_tick_count"], 10_000)
        self.assertNotIn("ticks", result)
        self.assertLessEqual(len(result["anomalies"]), 16)
        self.assertLessEqual(len(json.dumps(result, sort_keys=True).encode("utf-8")), 64 * 1024)
        self.assertEqual(_file_identity(router.run_state_path(run_root)), state_baseline)
        status = read_json(router._router_daemon_status_path(run_root))  # type: ignore[attr-defined]
        self.assertEqual(status["tick_interval_seconds"], 1)
        self.assertTrue(status["last_tick_at"])


if __name__ == "__main__":
    import unittest

    unittest.main()
