from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))

import flowpilot_router as router  # noqa: E402
import flowpilot_router_role_output_bridge_events as role_output_bridge_events  # noqa: E402
import flowpilot_router_work_packets_pm_role_writes_decisions as pm_decisions  # noqa: E402
import flowpilot_closure_kernel as closure_kernel  # noqa: E402
import packet_runtime  # noqa: E402
import role_output_runtime  # noqa: E402
from flowpilot_control_plane_contracts import (  # noqa: E402
    control_plane_action_identity_fingerprint,
    control_plane_pending_wait_same_identity,
)
from packet_runtime_contracts import contract_self_check_metadata  # noqa: E402
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase, read_json  # noqa: E402


class FlowPilotControlPlaneContractUnitTests(unittest.TestCase):
    def test_material_disposition_role_output_does_not_short_circuit_on_global_flag(self) -> None:
        scoped_identity = {
            "event": "pm_records_material_scan_result_disposition",
            "dedupe_key": "pm_records_material_scan_result_disposition:test",
            "family": "pm_package_disposition",
            "conflict_fields": ["body_hash"],
            "scope": {
                "batch_id": "repair-generation-batch",
                "packet_generation_id": "repair-generation",
                "body_hash": "abc123",
            },
        }

        for event in (
            "pm_records_material_scan_result_disposition",
            "pm_records_research_result_disposition",
            "pm_records_current_node_result_disposition",
        ):
            with self.subTest(event=event):
                self.assertFalse(
                    role_output_bridge_events._event_allows_run_wide_flag_short_circuit(
                        event,
                        {**scoped_identity, "event": event, "dedupe_key": f"{event}:test"},
                    )
                )

    def test_non_package_role_output_can_still_short_circuit_on_global_flag(self) -> None:
        self.assertTrue(
            role_output_bridge_events._event_allows_run_wide_flag_short_circuit(
                "reviewer_reports_material_sufficient",
                None,
            )
        )

    def test_pm_package_disposition_identity_conflicts_on_body_hash(self) -> None:
        for event in (
            "pm_records_material_scan_result_disposition",
            "pm_records_research_result_disposition",
            "pm_records_current_node_result_disposition",
        ):
            with self.subTest(event=event):
                run_state: dict[str, object] = {}
                first_identity = {
                    "event": event,
                    "dedupe_key": f"{event}:test",
                    "family": "pm_package_disposition",
                    "conflict_fields": ["body_hash"],
                    "scope": {
                        "batch_id": "batch-1",
                        "packet_ids": "packet-a,packet-b",
                        "packet_generation_id": "generation-1",
                        "body_hash": "hash-a",
                    },
                    "retry_group": f"{event}:test",
                }
                router._mark_scoped_event_recorded(run_state, first_identity)  # type: ignore[attr-defined]

                replay_identity = {
                    **first_identity,
                    "scope": {**first_identity["scope"], "body_hash": "hash-a"},
                }
                router._check_scoped_event_conflict(run_state, replay_identity)  # type: ignore[attr-defined]
                self.assertTrue(router._scoped_event_is_recorded(run_state, replay_identity))  # type: ignore[attr-defined]

                conflict_identity = {
                    **first_identity,
                    "scope": {**first_identity["scope"], "body_hash": "hash-b"},
                }
                with self.assertRaisesRegex(router.RouterError, "conflicts with an already recorded package disposition"):  # type: ignore[attr-defined]
                    router._check_scoped_event_conflict(run_state, conflict_identity)  # type: ignore[attr-defined]

    def test_pm_package_disposition_conflict_classifier_marks_repair_owned_replay(self) -> None:
        for event in (
            "pm_records_material_scan_result_disposition",
            "pm_records_research_result_disposition",
            "pm_records_current_node_result_disposition",
        ):
            with self.subTest(event=event):
                first_identity = {
                    "event": event,
                    "dedupe_key": f"{event}:test",
                    "family": "pm_package_disposition",
                    "conflict_fields": ["body_hash"],
                    "scope": {
                        "batch_id": "batch-1",
                        "packet_ids": "packet-a,packet-b",
                        "packet_generation_id": "generation-1",
                        "body_hash": "hash-a",
                    },
                    "retry_group": f"{event}:test",
                }
                conflict_identity = {
                    **first_identity,
                    "scope": {**first_identity["scope"], "body_hash": "hash-b"},
                }

                blocker_state: dict[str, object] = {
                    "active_control_blocker": {
                        "blocker_id": "control-blocker-1",
                        "originating_event": event,
                        "handling_lane": "pm_repair_decision_required",
                        "target_role": "project_manager",
                        "pm_decision_required": True,
                        "delivery_status": "delivered",
                    }
                }
                router._mark_scoped_event_recorded(blocker_state, first_identity)  # type: ignore[attr-defined]
                blocker_classification = router._classify_scoped_event_conflict(blocker_state, conflict_identity)  # type: ignore[attr-defined]
                self.assertEqual(
                    blocker_classification["classification"],
                    "control_blocker_owned_stale_conflict",
                )
                with self.assertRaisesRegex(router.RouterError, "conflicts with an already recorded package disposition"):  # type: ignore[attr-defined]
                    router._check_scoped_event_conflict(blocker_state, conflict_identity)  # type: ignore[attr-defined]

                repair_state: dict[str, object] = {
                    "active_repair_transaction": {
                        "transaction_id": "repair-tx-1",
                        "blocker_id": "control-blocker-1",
                        "status": "committed",
                        "originating_event": event,
                    }
                }
                router._mark_scoped_event_recorded(repair_state, first_identity)  # type: ignore[attr-defined]
                repair_classification = router._classify_scoped_event_conflict(repair_state, conflict_identity)  # type: ignore[attr-defined]
                self.assertEqual(
                    repair_classification["classification"],
                    "pm_repair_owned_stale_conflict",
                )

                terminal_state: dict[str, object] = {"status": "stopped_by_user", "flags": {"run_stopped_by_user": True}}
                router._mark_scoped_event_recorded(terminal_state, first_identity)  # type: ignore[attr-defined]
                terminal_classification = router._classify_scoped_event_conflict(terminal_state, conflict_identity)  # type: ignore[attr-defined]
                self.assertEqual(
                    terminal_classification["classification"],
                    "terminal_quarantine",
                )

    def test_pm_package_disposition_policies_use_body_hash_as_conflict_evidence(self) -> None:
        for event in (
            "pm_records_material_scan_result_disposition",
            "pm_records_research_result_disposition",
            "pm_records_current_node_result_disposition",
        ):
            policy = router.SCOPED_EVENT_IDENTITY_POLICIES[event]  # type: ignore[attr-defined]
            self.assertEqual(
                tuple(policy["dedupe_fields"]),
                ("batch_id", "packet_ids", "packet_generation_id"),
            )
            self.assertEqual(tuple(policy["conflict_fields"]), ("body_hash",))

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

    def test_pm_role_work_identity_includes_batch_packet_request_and_target(self) -> None:
        base = {
            "action_type": "relay_pm_role_work_request_packet",
            "scope_kind": "run",
            "scope_id": "run-1",
            "label": "pm_role_work_request_batch_relayed",
            "postcondition": "pm_role_work_request_packet_relayed",
        }
        first = {
            **base,
            "batch_id": "batch-a",
            "request_id": "request-a",
            "packet_id": "packet-a",
            "packet_ids": ["packet-a"],
            "to_role": "flowguard_operator",
        }
        second = {
            **base,
            "batch_id": "batch-b",
            "request_id": "request-b",
            "packet_id": "packet-b",
            "packet_ids": ["packet-b"],
            "to_role": "flowguard_operator",
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

    def test_control_blocker_wait_identity_includes_blocker_artifact(self) -> None:
        first = {
            "action_type": "await_role_decision",
            "label": "controller_waits_for_control_blocker_resolution",
            "waiting_for_role": "project_manager",
            "controller_action_id": "controller-action-control-blocker",
            "blocker_id": "control-blocker-a",
            "blocker_artifact_path": ".flowpilot/runs/run-1/control_blocks/control-blocker-a.json",
        }
        second = {
            **first,
            "blocker_id": "control-blocker-b",
            "blocker_artifact_path": ".flowpilot/runs/run-1/control_blocks/control-blocker-b.json",
        }

        self.assertFalse(control_plane_pending_wait_same_identity(first, second))

    def test_closure_kernel_normalizes_controller_and_role_rows(self) -> None:
        controller = closure_kernel.classify_closure(
            "controller_action",
            {"status": "resolved", "router_reconciliation_status": "reconciled"},
        )
        self.assertFalse(controller.blocks_progress)
        self.assertEqual(controller.classification, closure_kernel.CLOSURE_CLOSED_SUCCESS)

        incomplete_controller = closure_kernel.classify_closure(
            "controller_action",
            {"status": "done"},
        )
        self.assertTrue(incomplete_controller.blocks_progress)
        self.assertEqual(incomplete_controller.classification, closure_kernel.CLOSURE_REPAIR_REQUIRED)

        scheduler_open = closure_kernel.classify_closure(
            "router_scheduler_row",
            {"router_state": "receipt_done", "controller_status": "done"},
        )
        self.assertTrue(scheduler_open.blocks_progress)

        scheduler_closed = closure_kernel.classify_closure(
            "router_scheduler_row",
            {"router_state": "reconciled", "controller_status": "done"},
        )
        self.assertFalse(scheduler_closed.blocks_progress)

        target_busy = closure_kernel.classify_closure(
            "pm_role_work_target",
            {"status": "packet_relayed"},
        )
        self.assertTrue(target_busy.blocks_progress)

        target_done_pm_busy = closure_kernel.classify_closure(
            "pm_role_work_target",
            {"status": "result_returned"},
        )
        self.assertFalse(target_done_pm_busy.blocks_progress)

        pm_busy = closure_kernel.classify_closure(
            "pm_role_work_pm",
            {"status": "result_returned"},
        )
        self.assertTrue(pm_busy.blocks_progress)

        pm_any_busy = closure_kernel.classify_closure(
            "pm_role_work_any",
            {"status": "result_returned"},
        )
        self.assertTrue(pm_any_busy.blocks_progress)

        pm_any_closed = closure_kernel.classify_closure(
            "pm_role_work_any",
            {"status": "absorbed"},
        )
        self.assertFalse(pm_any_closed.blocks_progress)

        ack_resolved_by_receipt = closure_kernel.classify_closure(
            "ack_return",
            {"status": "resolved", "receipt_ref_count": 1},
        )
        self.assertFalse(ack_resolved_by_receipt.blocks_progress)

        unknown = closure_kernel.classify_closure(
            "worker_result",
            {"status": "new_closed_word"},
        )
        self.assertTrue(unknown.blocks_progress)
        self.assertEqual(unknown.classification, closure_kernel.CLOSURE_UNKNOWN_NEEDS_RECHECK)


class FlowPilotControlPlaneContractRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def _prepare_material_scan_pm_disposition(
        self,
        root: Path,
        run_id: str,
        *,
        packet_count: int = 1,
    ) -> tuple[Path, dict, dict, Path]:
        run_root = self.write_minimal_run(root, run_id)
        run_state = read_json(router.run_state_path(run_root))
        records: list[dict[str, object]] = []
        for index in range(packet_count):
            suffix = "" if packet_count == 1 else f"-{chr(ord('a') + index)}"
            packet_id = f"packet-release{suffix}"
            role = "worker" if index % 2 == 0 else "flowguard_operator"
            packet = packet_runtime.create_packet(
                root,
                run_id=run_id,
                packet_id=packet_id,
                from_role="project_manager",
                to_role=role,
                node_id="node-001",
                body_text=f"material scan {packet_id}",
            )
            packet_path = root / packet["body_path"].replace("packet_body.md", "packet_envelope.json")
            packet = packet_runtime.deliver_envelope_metadata(
                root,
                envelope=packet,
                envelope_path=packet_path,
                controller_agent_id="agent-controller",
                received_from_role="project_manager",
                relayed_to_role=role,
            )
            packet_runtime.read_packet_body_for_role(root, packet, role=role)
            result = packet_runtime.write_result(
                root,
                packet_envelope=packet,
                completed_by_role=role,
                completed_by_agent_id=f"agent-{role}",
                result_body_text=f"scan result {packet_id}\n\nContract Self-Check\n\nstatus: pass\n",
                next_recipient="project_manager",
            )
            result_path = root / result["result_body_path"].replace("result_body.md", "result_envelope.json")
            result = packet_runtime.deliver_envelope_metadata(
                root,
                envelope=result,
                envelope_path=result_path,
                controller_agent_id="agent-controller",
                received_from_role=role,
                relayed_to_role="project_manager",
            )
            packet_runtime.read_result_body_for_role(root, result, role="project_manager")
            records.append(
                {
                    "packet_id": packet_id,
                    "to_role": role,
                    "packet_generation_id": "material-generation-release",
                    "packet_envelope_path": router.project_relative(root, packet_path),
                    "result_envelope_path": router.project_relative(root, result_path),
                    "status": "result_relayed_to_pm",
                }
            )
        batch = router._write_parallel_packet_batch(  # type: ignore[attr-defined]
            root,
            run_root,
            run_state,
            batch_id="batch-release",
            batch_kind="material_scan",
            phase="material_scan",
            records=records,
            node_id="material-intake",
            join_policy="all_results_before_pm_absorption",
            review_policy="pm_absorbs_batch_before_material_sufficiency_review",
            pm_absorption_required=True,
        )
        batch["status"] = "results_relayed_to_pm"
        router._write_parallel_packet_batch_state(run_root, batch)  # type: ignore[attr-defined]
        router.write_json(
            run_root / "material" / "material_scan_packets.json",
            {
                "schema_version": "flowpilot.material_scan_packets.v2",
                "run_id": run_state["run_id"],
                "written_by_role": "project_manager",
                "batch_id": "batch-release",
                "batch_kind": "material_scan",
                "current_generation_id": "material-generation-release",
                "controller_may_read_packet_body": False,
                "router_direct_dispatch_required_before_worker": True,
                "reviewer_dispatch_required_before_worker": False,
                "packets": records,
                "written_at": router.utc_now(),
            },
        )
        output_path = run_root / "material" / "pm_material_scan_result_disposition.json"
        payload = role_output_runtime.submit_output(
            root,
            output_type="pm_package_result_disposition",
            role="project_manager",
            agent_id="agent-project_manager",
            run_id=run_root.name,
            event_name="pm_records_material_scan_result_disposition",
            body={
                "decided_by_role": "project_manager",
                "decision": "absorbed",
                "decision_reason": "ready",
                "residual_risks": [],
            },
        )
        return run_root, run_state, payload, output_path

    def test_pm_package_disposition_rejects_handwritten_body(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        material_index_path = run_root / "material" / "material_scan_packets.json"
        self.open_packets_and_write_results(root, material_index_path, result_text="material scan result")
        router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")
        router.record_external_event(root, "worker_scan_results_returned")
        self.apply_next_packet_action(root, "relay_material_scan_results_to_pm")
        self.open_results_for_pm(root, material_index_path)

        with self.assertRaises(router.RouterError) as raised:
            router.record_external_event(
                root,
                "pm_records_material_scan_result_disposition",
                {
                    "decided_by_role": "project_manager",
                    "decision": "absorbed",
                    "decision_reason": "handwritten body should not pass",
                },
            )

        self.assertIn("role-output runtime envelope", str(raised.exception))

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

    def test_pm_formal_gate_package_has_path_hash_and_scope(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-formal-package")
        output_path = run_root / "material" / "pm_material_scan_result_disposition.json"
        packet_envelope = run_root / "packets" / "packet-1" / "packet_envelope.json"
        result_envelope = run_root / "packets" / "packet-1" / "result_envelope.json"
        result_envelope.parent.mkdir(parents=True, exist_ok=True)
        router.write_json(
            packet_envelope,
            {
                "schema_version": packet_runtime.PACKET_ENVELOPE_SCHEMA,
                "packet_id": "packet-1",
                "packet_type": "material_scan",
                "from_role": "project_manager",
                "to_role": "worker",
                "body_path": router.project_relative(root, result_envelope.parent / "packet_body.md"),
                "body_hash": "hash",
                "output_contract_id": "flowpilot.output_contract.worker_material_scan_result.v1",
                "output_contract": {
                    "schema_version": "flowpilot.output_contract.v1",
                    "contract_id": "flowpilot.output_contract.worker_material_scan_result.v1",
                    "recipient_role": "worker",
                    "selected_by_role": "project_manager",
                },
            },
        )
        router.write_json(
            result_envelope,
            {
                "schema_version": packet_runtime.RESULT_ENVELOPE_SCHEMA,
                "packet_id": "packet-1",
                "source_packet_envelope_path": router.project_relative(root, packet_envelope),
                "source_output_contract_id": "flowpilot.output_contract.worker_material_scan_result.v1",
                "contract_self_check": {
                    "required": True,
                    "completed": True,
                    "passed": True,
                    "decision": "pass",
                    "source_output_contract_id": "flowpilot.output_contract.worker_material_scan_result.v1",
                    "declared_source_output_contract_id": "flowpilot.output_contract.worker_material_scan_result.v1",
                    "source_output_contract_id_matches": True,
                },
            },
        )

        package_ref = pm_decisions._write_pm_formal_gate_package(
            router,
            root,
            output_path,
            run_state={"run_id": run_root.name, "run_root": router.project_relative(root, run_root)},
            batch={"batch_id": "batch-1"},
            records=[
                {
                    "packet_id": "packet-1",
                    "packet_envelope_path": router.project_relative(root, packet_envelope),
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
        result_entry = package["result_envelopes"][0]
        self.assertEqual(result_entry["packet_envelope_path"], router.project_relative(root, packet_envelope))
        self.assertEqual(result_entry["packet_envelope_hash"], packet_runtime.sha256_file(packet_envelope))
        self.assertEqual(result_entry["result_envelope_hash"], packet_runtime.sha256_file(result_envelope))
        self.assertEqual(
            result_entry["source_output_contract_id"],
            "flowpilot.output_contract.worker_material_scan_result.v1",
        )
        self.assertTrue(result_entry["contract_self_check"]["ok"])
        self.assertTrue(package["all_source_result_contract_self_checks_passed"])

    def test_pm_formal_gate_package_blocks_failed_source_self_check(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-formal-package-bad-self-check")
        output_path = run_root / "material" / "pm_material_scan_result_disposition.json"
        packet_envelope = run_root / "packets" / "packet-1" / "packet_envelope.json"
        result_envelope = run_root / "packets" / "packet-1" / "result_envelope.json"
        result_envelope.parent.mkdir(parents=True, exist_ok=True)
        router.write_json(
            packet_envelope,
            {
                "schema_version": packet_runtime.PACKET_ENVELOPE_SCHEMA,
                "packet_id": "packet-1",
                "packet_type": "material_scan",
                "from_role": "project_manager",
                "to_role": "worker",
                "body_path": router.project_relative(root, result_envelope.parent / "packet_body.md"),
                "body_hash": "hash",
                "output_contract_id": "flowpilot.output_contract.worker_material_scan_result.v1",
            },
        )
        router.write_json(
            result_envelope,
            {
                "schema_version": packet_runtime.RESULT_ENVELOPE_SCHEMA,
                "packet_id": "packet-1",
                "source_packet_envelope_path": router.project_relative(root, packet_envelope),
                "source_output_contract_id": "flowpilot.output_contract.worker_material_scan_result.v1",
                "contract_self_check": {
                    "required": True,
                    "completed": False,
                    "passed": False,
                    "decision": None,
                    "source_output_contract_id_matches": True,
                },
            },
        )

        with self.assertRaisesRegex(router.RouterError, "contract self-checks"):
            pm_decisions._write_pm_formal_gate_package(
                router,
                root,
                output_path,
                run_state={"run_id": run_root.name, "run_root": router.project_relative(root, run_root)},
                batch={"batch_id": "batch-1"},
                records=[
                    {
                        "packet_id": "packet-1",
                        "packet_envelope_path": router.project_relative(root, packet_envelope),
                        "result_envelope_path": router.project_relative(root, result_envelope),
                    }
                ],
                batch_kind="material_scan",
                package_label="material_scan",
                gate_kind="material_sufficiency",
                decision="absorbed",
                payload={"decision_reason": "ready"},
            )

    def test_absorbed_pm_disposition_records_reviewer_release_evidence(self) -> None:
        root = self.make_project()
        run_root, run_state, payload, output_path = self._prepare_material_scan_pm_disposition(
            root,
            "run-disposition-release",
        )

        pm_decisions._write_pm_package_result_disposition(
            router,
            root,
            run_root,
            run_state,
            payload,
            batch_kind="material_scan",
            package_label="material_scan",
            gate_kind="material_sufficiency",
            output_path=output_path,
            router_event="pm_records_material_scan_result_disposition",
        )

        disposition = read_json(output_path)
        release = disposition["pm_reviewer_release_evidence"]
        self.assertEqual(disposition["control_transaction"]["transaction_type"], "result_absorption")
        self.assertEqual(
            disposition["control_transaction"]["output_contract_id"],
            "flowpilot.output_contract.pm_package_result_disposition.v1",
        )
        self.assertTrue(disposition["formal_gate_package_released"])
        self.assertTrue(release["release_satisfied"])
        self.assertEqual(release["release_kind"], "absorbed_pm_package_result_disposition")
        self.assertTrue(release["formal_gate_package_path"])
        self.assertTrue(release["formal_gate_package_hash"])
        self.assertFalse(release["reviewer_receives_raw_worker_result"])

    def test_pm_disposition_records_packet_outcomes_and_blocks_mixed_absorption(self) -> None:
        root = self.make_project()
        run_root, run_state, _payload, output_path = self._prepare_material_scan_pm_disposition(
            root,
            "run-disposition-packet-outcomes",
            packet_count=2,
        )
        mixed_payload = role_output_runtime.submit_output(
            root,
            output_type="pm_package_result_disposition",
            role="project_manager",
            agent_id="agent-project_manager",
            run_id=run_root.name,
            event_name="pm_records_material_scan_result_disposition",
            body={
                "decided_by_role": "project_manager",
                "decision": "rework_requested",
                "decision_reason": "Worker result needs a targeted repair.",
                "packet_outcomes": [
                    {
                        "packet_id": "packet-release-a",
                        "outcome": "accepted",
                        "reason": "Worker result is usable.",
                    },
                    {
                        "packet_id": "packet-release-b",
                        "outcome": "rework_requested",
                        "reason": "Worker result failed PM self-check.",
                    },
                ],
                "residual_risks": [],
            },
        )

        pm_decisions._write_pm_package_result_disposition(
            router,
            root,
            run_root,
            run_state,
            mixed_payload,
            batch_kind="material_scan",
            package_label="material_scan",
            gate_kind="material_sufficiency",
            output_path=output_path,
            router_event="pm_records_material_scan_result_disposition",
        )

        disposition = read_json(output_path)
        self.assertFalse(disposition["formal_gate_package_released"])
        self.assertEqual(disposition["packet_outcome_summary"]["accepted"], 1)
        self.assertEqual(disposition["packet_outcome_summary"]["rework_requested"], 1)
        batch = router._active_parallel_packet_batch(run_root, "material_scan")  # type: ignore[attr-defined]
        self.assertEqual(batch["status"], "rework_requested")
        outcomes = {record["packet_id"]: record["pm_result_outcome"]["outcome"] for record in batch["packets"]}
        self.assertEqual(outcomes["packet-release-a"], "accepted")
        self.assertEqual(outcomes["packet-release-b"], "rework_requested")

    def test_pm_disposition_rejects_absorbed_with_rework_packet_outcome(self) -> None:
        root = self.make_project()
        run_root, run_state, _payload, output_path = self._prepare_material_scan_pm_disposition(
            root,
            "run-disposition-contradictory-outcomes",
        )
        contradictory_payload = role_output_runtime.submit_output(
            root,
            output_type="pm_package_result_disposition",
            role="project_manager",
            agent_id="agent-project_manager",
            run_id=run_root.name,
            event_name="pm_records_material_scan_result_disposition",
            body={
                "decided_by_role": "project_manager",
                "decision": "absorbed",
                "decision_reason": "This contradicts the packet outcome.",
                "packet_outcomes": [
                    {
                        "packet_id": "packet-release",
                        "outcome": "rework_requested",
                        "reason": "The packet still needs repair.",
                    }
                ],
                "residual_risks": [],
            },
        )

        with self.assertRaisesRegex(router.RouterError, "cannot be absorbed while packet outcomes require more work"):  # type: ignore[attr-defined]
            pm_decisions._write_pm_package_result_disposition(
                router,
                root,
                run_root,
                run_state,
                contradictory_payload,
                batch_kind="material_scan",
                package_label="material_scan",
                gate_kind="material_sufficiency",
                output_path=output_path,
                router_event="pm_records_material_scan_result_disposition",
            )

    def test_pm_disposition_rejects_second_body_for_same_batch_generation(self) -> None:
        root = self.make_project()
        run_root, run_state, payload, output_path = self._prepare_material_scan_pm_disposition(
            root,
            "run-disposition-duplicate-conflict",
        )
        pm_decisions._write_pm_package_result_disposition(
            router,
            root,
            run_root,
            run_state,
            payload,
            batch_kind="material_scan",
            package_label="material_scan",
            gate_kind="material_sufficiency",
            output_path=output_path,
            router_event="pm_records_material_scan_result_disposition",
        )
        second_payload = role_output_runtime.submit_output(
            root,
            output_type="pm_package_result_disposition",
            role="project_manager",
            agent_id="agent-project_manager",
            run_id=run_root.name,
            event_name="pm_records_material_scan_result_disposition",
            body={
                "decided_by_role": "project_manager",
                "decision": "rework_requested",
                "decision_reason": "Different second PM body must not create a new decision.",
                "residual_risks": [],
            },
        )

        with self.assertRaisesRegex(router.RouterError, "already recorded for this batch/generation"):  # type: ignore[attr-defined]
            pm_decisions._write_pm_package_result_disposition(
                router,
                root,
                run_root,
                run_state,
                second_payload,
                batch_kind="material_scan",
                package_label="material_scan",
                gate_kind="material_sufficiency",
                output_path=output_path,
                router_event="pm_records_material_scan_result_disposition",
            )

    def test_material_disposition_rejects_stale_active_batch(self) -> None:
        root = self.make_project()
        run_root, run_state, payload, output_path = self._prepare_material_scan_pm_disposition(
            root,
            "run-disposition-stale-generation",
        )
        stale_batch = router._active_parallel_packet_batch(run_root, "material_scan")  # type: ignore[attr-defined]
        stale_batch["batch_id"] = "batch-release-stale"
        stale_batch["status"] = "results_relayed_to_pm"
        for record in stale_batch["packets"]:
            record["batch_id"] = "batch-release-stale"
            record["packet_generation_id"] = "material-generation-stale"
        router.write_json(router._parallel_packet_batch_path(run_root, "batch-release-stale"), stale_batch)  # type: ignore[attr-defined]
        router.write_json(
            router._parallel_packet_batch_ref_path(run_root, "material_scan"),  # type: ignore[attr-defined]
            {
                "schema_version": router.PARALLEL_PACKET_BATCH_REF_SCHEMA,  # type: ignore[attr-defined]
                "run_id": run_state["run_id"],
                "batch_kind": "material_scan",
                "active_batch_id": "batch-release-stale",
                "batch_path": router.project_relative(root, router._parallel_packet_batch_path(run_root, "batch-release-stale")),  # type: ignore[attr-defined]
                "updated_at": router.utc_now(),
            },
        )

        with self.assertRaisesRegex(router.RouterError, "batch does not match current material generation"):  # type: ignore[attr-defined]
            pm_decisions._write_pm_package_result_disposition(
                router,
                root,
                run_root,
                run_state,
                payload,
                batch_kind="material_scan",
                package_label="material_scan",
                gate_kind="material_sufficiency",
                output_path=output_path,
                router_event="pm_records_material_scan_result_disposition",
            )

    def test_pm_disposition_requires_registered_commit_targets(self) -> None:
        root = self.make_project()
        run_root, run_state, payload, output_path = self._prepare_material_scan_pm_disposition(
            root,
            "run-disposition-registry-mismatch",
        )
        registry = read_json(ROOT / "skills" / "flowpilot" / "assets" / "runtime_kit" / "control_transaction_registry.json")
        for row in registry["transaction_types"]:
            if row.get("transaction_type") == "result_absorption":
                row["commit_targets"] = [
                    target for target in row["commit_targets"] if target != "pm_package_disposition"
                ]
        registry_path = run_root / "runtime_kit" / "control_transaction_registry.json"
        router.write_json(registry_path, registry)

        with self.assertRaises(router.RouterError) as raised:  # type: ignore[attr-defined]
            pm_decisions._write_pm_package_result_disposition(
                router,
                root,
                run_root,
                run_state,
                payload,
                batch_kind="material_scan",
                package_label="material_scan",
                gate_kind="material_sufficiency",
                output_path=output_path,
                router_event="pm_records_material_scan_result_disposition",
            )

        self.assertIn("commit target pm_package_disposition is not declared", str(raised.exception))

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
