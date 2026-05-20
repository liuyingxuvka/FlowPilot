from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))

import flowpilot_router as router  # noqa: E402
import flowpilot_router_work_packets_pm_role_writes_decisions as pm_decisions  # noqa: E402
import packet_runtime  # noqa: E402
from flowpilot_control_plane_contracts import (  # noqa: E402
    control_plane_action_identity_fingerprint,
    control_plane_pending_wait_same_identity,
)
from packet_runtime_contracts import contract_self_check_metadata  # noqa: E402
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase, read_json  # noqa: E402


class FlowPilotControlPlaneContractUnitTests(unittest.TestCase):
    def test_control_blocker_identity_includes_blocker_artifact(self) -> None:
        base = {
            "action_type": "handle_control_blocker",
            "scope_kind": "run",
            "scope_id": "run-1",
            "label": "controller_handles_pm_repair_decision_required_control_blocker",
            "to_role": "project_manager",
            "postcondition": "control_blocker_delivered:blocker-a",
        }
        first = {
            **base,
            "blocker_id": "blocker-a",
            "blocker_artifact_path": ".flowpilot/runs/run-1/control_blocks/blocker-a.json",
        }
        second = {
            **base,
            "blocker_id": "blocker-b",
            "blocker_artifact_path": ".flowpilot/runs/run-1/control_blocks/blocker-b.json",
            "postcondition": "control_blocker_delivered:blocker-b",
        }

        self.assertNotEqual(
            router._router_scheduler_idempotency_key(first, "run", "run-1"),  # type: ignore[attr-defined]
            router._router_scheduler_idempotency_key(second, "run", "run-1"),  # type: ignore[attr-defined]
        )
        self.assertNotEqual(
            control_plane_action_identity_fingerprint(first),
            control_plane_action_identity_fingerprint(second),
        )

    def test_handle_control_blocker_is_stateful_postcondition_work(self) -> None:
        action = {
            "action_type": "handle_control_blocker",
            "blocker_id": "control-blocker-0002",
            "postcondition": "control_blocker_delivered:control-blocker-0002",
            "to_role": "project_manager",
        }

        action_class = router._controller_action_completion_class(action)  # type: ignore[attr-defined]

        self.assertEqual(action_class["kind"], "stateful_host_postcondition")
        self.assertEqual(action_class["artifact_kind"], "control_blocker_delivery")
        self.assertEqual(action_class["postcondition"], "control_blocker_delivered:control-blocker-0002")

    def test_contract_self_check_accepts_status_pass(self) -> None:
        metadata = contract_self_check_metadata(
            "## Contract Self-Check\n\nstatus: pass\n",
            {"contract_self_check_required": True},
        )

        self.assertTrue(metadata["completed"])
        self.assertTrue(metadata["passed"])
        self.assertEqual(metadata["decision"], "pass")

    def test_pending_wait_identity_is_bound_to_controller_action(self) -> None:
        first = {
            "action_type": "await_role_decision",
            "label": "controller_waits_for_pm",
            "waiting_for_role": "project_manager",
            "expected_return_path": "mailbox/outbox/events/pm.envelope.json",
            "controller_action_id": "controller-action-1",
            "last_wait_reminder_at": "2026-05-20T00:00:00Z",
        }
        same_wait_with_reminder = {
            **first,
            "last_wait_reminder_at": "2026-05-20T00:01:00Z",
        }
        different_wait = {
            **first,
            "controller_action_id": "controller-action-2",
        }

        self.assertTrue(control_plane_pending_wait_same_identity(first, same_wait_with_reminder))
        self.assertFalse(control_plane_pending_wait_same_identity(first, different_wait))


class FlowPilotControlPlaneContractRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_control_blocker_done_receipt_applies_delivery_postcondition(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-control-blocker-receipt")
        self.write_current_focus(root, run_root)
        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="test blocker",
            action_type="test_control_blocker",
            payload={"role": "project_manager"},
        )
        action = router._next_control_blocker_action(root, state, run_root)  # type: ignore[attr-defined]
        self.assertIsNotNone(action)
        assert action is not None
        self.assertEqual(action["action_type"], "handle_control_blocker")

        result = router._apply_done_controller_receipt_effects(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            action,
            {"schema_version": router.CONTROLLER_RECEIPT_SCHEMA, "status": "done", "payload": {}},
        )

        self.assertTrue(result["applied"])
        self.assertTrue(state["flags"][action["postcondition"]])
        blocker_record = read_json(root / blocker["blocker_artifact_path"])
        self.assertEqual(blocker_record["delivery_status"], "delivered")
        ledger = read_json(run_root / "control_blocks" / "control_blocker_delivery_ledger.json")
        self.assertEqual(ledger["deliveries"][-1]["blocker_id"], blocker["blocker_id"])

    def test_legacy_material_migration_preserves_relayed_envelope_bytes(self) -> None:
        root = self.make_project()
        run_id = "run-material-migration"
        run_root = self.write_minimal_run(root, run_id)
        self.write_current_focus(root, run_root)
        packet_id = "material-scan-signed"
        paths = packet_runtime.packet_paths(root, packet_id, run_id)
        paths["packet_dir"].mkdir(parents=True, exist_ok=True)
        packet_body = paths["packet_body"]
        packet_body.write_text("sealed material request", encoding="utf-8")
        envelope = {
            "schema_version": packet_runtime.PACKET_ENVELOPE_SCHEMA,
            "packet_id": packet_id,
            "packet_type": "material_scan",
            "from_role": "project_manager",
            "to_role": "worker_a",
            "node_id": "node-1",
            "body_path": router.project_relative(root, packet_body),
            "body_hash": packet_runtime.sha256_file(packet_body),
            "body_visibility": packet_runtime.SEALED_BODY_VISIBILITY,
        }
        envelope["controller_relay"] = {
            "schema_version": packet_runtime.CONTROLLER_RELAY_SCHEMA,
            "delivered_via_controller": True,
            "controller_agent_id": "controller-test",
            "received_from_role": "project_manager",
            "relayed_to_role": "worker_a",
            "received_at": router.utc_now(),
            "relayed_at": router.utc_now(),
            "envelope_hash": packet_runtime.envelope_hash(envelope),
            "body_was_read_by_controller": False,
            "body_was_executed_by_controller": False,
            "holder_before": "project_manager",
            "holder_after": "worker_a",
            "private_role_to_role_delivery_detected": False,
        }
        router.write_json(paths["packet_envelope"], envelope)
        original_bytes = paths["packet_envelope"].read_bytes()
        envelope_rel = router.project_relative(root, paths["packet_envelope"])
        router.write_json(
            router._material_scan_index_path(run_root),  # type: ignore[attr-defined]
            {
                "schema_version": "flowpilot.material_scan_index.v1",
                "run_id": run_id,
                "packets": [{"packet_id": packet_id, "packet_type": "material_scan", "packet_envelope_path": envelope_rel}],
            },
        )
        router.write_json(
            run_root / "packet_ledger.json",
            {
                "schema_version": packet_runtime.PACKET_LEDGER_SCHEMA,
                "run_id": run_id,
                "packets": [
                    {
                        "packet_id": packet_id,
                        "packet_type": "material_scan",
                        "packet_envelope_path": envelope_rel,
                        "packet_envelope": envelope,
                    }
                ],
            },
        )

        repaired = router._repair_legacy_material_packet_contracts(root, run_root)  # type: ignore[attr-defined]

        self.assertEqual(repaired, 1)
        self.assertEqual(paths["packet_envelope"].read_bytes(), original_bytes)
        migration = read_json(run_root / "material" / "legacy_material_packet_migration.json")
        self.assertEqual(migration["packets"][0]["migration_mode"], "sidecar_only_signed_envelope_preserved")
        ledger = read_json(run_root / "packet_ledger.json")
        self.assertNotIn("result_body_path", ledger["packets"][0]["packet_envelope"])
        index = read_json(router._material_scan_index_path(run_root))  # type: ignore[attr-defined]
        self.assertIn("result_body_path", index["packets"][0])

    def test_pm_formal_gate_package_has_path_hash_and_scope(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-formal-package")
        output_path = run_root / "material" / "pm_material_scan_result_disposition.json"
        result_envelope = run_root / "packets" / "packet-1" / "result_envelope.json"
        result_envelope.parent.mkdir(parents=True, exist_ok=True)
        router.write_json(result_envelope, {"schema_version": "flowpilot.packet_result_envelope.v1", "packet_id": "packet-1"})

        package_ref = pm_decisions._write_pm_formal_gate_package(
            router,
            root,
            output_path,
            run_state={"run_id": run_root.name},
            batch={"batch_id": "batch-1"},
            records=[
                {
                    "packet_id": "packet-1",
                    "result_envelope_path": router.project_relative(root, result_envelope),
                }
            ],
            batch_kind="material_scan",
            package_label="material_scan",
            gate_kind="material_sufficiency",
            decision="absorbed",
            payload={"decision_reason": "ready"},
        )

        self.assertTrue(package_ref["formal_gate_package_path"])
        self.assertTrue(package_ref["formal_gate_package_hash"])
        package = read_json(root / package_ref["formal_gate_package_path"])
        self.assertTrue(package["reviewer_readable"])
        self.assertEqual(package["reviewer_review_scope"], "pm_formal_gate_package_only")
        self.assertFalse(package["reviewer_receives_raw_worker_result"])
        self.assertTrue(package["content_boundary"]["excludes_worker_result_bodies"])

    def test_stale_run_state_save_cannot_resurrect_cleared_pending_wait(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-stale-pending-nonresurrection")
        path = router.run_state_path(run_root)
        initial = read_json(path)
        initial["pending_action"] = {
            "action_type": "await_role_decision",
            "label": "controller_waits_for_pm_startup_activation",
            "waiting_for_role": "project_manager",
            "expected_return_path": "mailbox/outbox/events/pm_startup_activation.envelope.json",
            "controller_action_id": "controller-action-stale",
        }
        router.write_json(path, initial)
        stale_state, _ = router.load_run_state_from_run_root(root, run_root)
        self.assertIsInstance(stale_state, dict)

        foreground = read_json(path)
        foreground["pending_action"] = None
        foreground["events"].append({"event": "pm_approves_startup_activation", "payload": {"source": "test"}})
        router.write_json(path, foreground)

        stale_state["history"].append({"event": "daemon_tick_after_foreground_clear", "payload": {"source": "test"}})
        router.save_run_state(run_root, stale_state)

        saved = read_json(path)
        self.assertIsNone(saved["pending_action"])
        self.assertIn(
            {"event": "pm_approves_startup_activation", "payload": {"source": "test"}},
            saved["events"],
        )
        self.assertIn(
            {"event": "daemon_tick_after_foreground_clear", "payload": {"source": "test"}},
            saved["history"],
        )


if __name__ == "__main__":
    unittest.main()
