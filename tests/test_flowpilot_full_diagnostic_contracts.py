from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))

import flowpilot_router as router  # noqa: E402
import flowpilot_router_cli as router_cli  # noqa: E402
import flowpilot_router_control_transactions as control_transactions  # noqa: E402
import flowpilot_router_controller_repair_schedule as controller_repair_schedule  # noqa: E402
import flowpilot_router_controller_scheduler_receipts_pending as receipts_pending  # noqa: E402
import flowpilot_router_controller_scheduler_receipts_scheduled as receipts_scheduled  # noqa: E402
import flowpilot_router_controller_scheduler_receipts_writes as receipts_writes  # noqa: E402
import flowpilot_router_event_identity as event_identity  # noqa: E402
import flowpilot_router_event_intake as event_intake  # noqa: E402
import flowpilot_router_events_repair as events_repair  # noqa: E402
import flowpilot_router_expected_waits as expected_waits  # noqa: E402
import flowpilot_router_facade_export_manifest_actions as manifest_actions  # noqa: E402
import flowpilot_router_facade_export_manifest_controller as manifest_controller  # noqa: E402
import flowpilot_router_facade_export_manifest_route as manifest_route  # noqa: E402
import flowpilot_router_facade_export_manifest_startup as manifest_startup  # noqa: E402
import flowpilot_router_facade_export_manifest_terminal_work as manifest_terminal_work  # noqa: E402
import flowpilot_router_facade_exports as facade_exports  # noqa: E402
import flowpilot_router_internal_actions as internal_actions  # noqa: E402
import flowpilot_router_lifecycle_requests as lifecycle_requests  # noqa: E402
import flowpilot_router_lifecycle_support as lifecycle_support  # noqa: E402
import flowpilot_router_model_gate_state as model_gate_state  # noqa: E402
import flowpilot_router_payload_contracts as payload_contracts  # noqa: E402
import flowpilot_router_pm_role_followup as pm_role_followup  # noqa: E402
import flowpilot_router_prompt_delivery as prompt_delivery  # noqa: E402
import flowpilot_router_proof_validation as proof_validation  # noqa: E402
import flowpilot_router_protocol_external_events as protocol_external_events  # noqa: E402
import flowpilot_router_role_io_protocol as role_io_protocol  # noqa: E402
import flowpilot_router_role_output_bridge as role_output_bridge  # noqa: E402
import flowpilot_router_route_artifacts_evidence as route_artifacts_evidence  # noqa: E402
import flowpilot_router_route_completion_support as route_completion_support  # noqa: E402
import flowpilot_router_self_interrogation as self_interrogation  # noqa: E402
import flowpilot_router_startup_bootloader as startup_bootloader  # noqa: E402
import flowpilot_router_startup_closure as startup_closure  # noqa: E402
import flowpilot_router_startup_display as startup_display  # noqa: E402
import flowpilot_router_startup_fact_boundary as startup_fact_boundary  # noqa: E402
import flowpilot_router_startup_flow as startup_flow  # noqa: E402
import flowpilot_router_startup_intake as startup_intake  # noqa: E402
import flowpilot_router_startup_role_recovery as startup_role_recovery  # noqa: E402
import flowpilot_router_startup_support as startup_support  # noqa: E402
import flowpilot_router_system_cards_delivery as system_cards_delivery  # noqa: E402
import flowpilot_router_terminal_ledger_closure as terminal_closure  # noqa: E402
import flowpilot_router_terminal_ledger_recovery as terminal_recovery  # noqa: E402
import flowpilot_router_terminal_ledger_summary as terminal_summary  # noqa: E402
import flowpilot_router_work_packets_next_actions as work_packets_next_actions  # noqa: E402
import flowpilot_router_work_packets_pm_role_actions as work_packets_pm_role_actions  # noqa: E402
import flowpilot_user_flow_markdown as user_flow_markdown  # noqa: E402
import flowpilot_user_flow_mermaid as user_flow_mermaid  # noqa: E402
import flowpilot_user_flow_source as user_flow_source  # noqa: E402
import flowpilot_user_flow_stage as user_flow_stage  # noqa: E402
import flowpilot_user_flow_tree as user_flow_tree  # noqa: E402
import packet_control_plane_model_invariants as packet_invariants  # noqa: E402
import packet_control_plane_model_transitions_dispatch_results as packet_dispatch_results  # noqa: E402
import packet_control_plane_model_transitions_issue_resume as packet_issue_resume  # noqa: E402
import packet_control_plane_model_transitions_packet_relay as packet_relay  # noqa: E402
import packet_control_plane_model_transitions_review_pm as packet_review_pm  # noqa: E402
import packet_runtime  # noqa: E402
import packet_runtime_reviewer  # noqa: E402
from flowpilot_router_errors import RouterError  # noqa: E402
from packet_control_plane_model_state import (  # noqa: E402
    HeartbeatCase,
    NodeCase,
    NodePacket,
    NodeResult,
    State,
)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


class FlowPilotFullDiagnosticContractTests(unittest.TestCase):
    def setUp(self) -> None:
        for module in (
            control_transactions,
            controller_repair_schedule,
            event_identity,
            expected_waits,
            internal_actions,
            lifecycle_requests,
            lifecycle_support,
            model_gate_state,
            payload_contracts,
            pm_role_followup,
            proof_validation,
            route_artifacts_evidence,
            route_completion_support,
            self_interrogation,
            startup_bootloader,
            startup_closure,
            startup_display,
            startup_fact_boundary,
            startup_flow,
            startup_intake,
            startup_role_recovery,
            startup_support,
            system_cards_delivery,
        ):
            if hasattr(module, "_bind_router"):
                module._bind_router(router)

    def test_controller_control_scheduler_external_contracts(self) -> None:
        args = router_cli.parse_args(["--root", ".", "controller-receipt", "--action-id", "a1", "--status", "done"])
        self.assertEqual(args.command, "controller-receipt")
        self.assertEqual(args.action_id, "a1")
        self.assertEqual(args.status, "done")

        self.assertEqual(control_transactions._control_transaction_registry_path().name, "control_transaction_registry.json")
        self.assertEqual(
            control_transactions._control_transaction_contract_registry_path().name,
            "contract_index.json",
        )
        self.assertEqual(control_transactions._control_transaction_registry_issues(), [])
        row = control_transactions._control_transaction_row(None, "packet_dispatch")
        self.assertEqual(row["transaction_type"], "packet_dispatch")
        authorized = control_transactions._validate_control_transaction_requirements(
            None,
            transaction_type="packet_dispatch",
            producer_role="project_manager",
            output_contract_id="flowpilot.output_contract.pm_role_work_result.v1",
            required_commit_targets=("packet_ledger",),
            require_packet_authority=False,
            outcome_policy="single_event",
        )
        self.assertEqual(authorized["transaction_type"], "packet_dispatch")

        with tempfile.TemporaryDirectory(prefix="flowpilot-controller-contracts-") as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-test"
            run_root.mkdir(parents=True)
            run_state = {"run_id": "run-test", "flags": {}}
            repair = controller_repair_schedule._schedule_controller_deliverable_repair(
                project_root,
                run_root,
                run_state,
                pending_action={},
                receipt={},
                apply_result={},
                source="contract_test",
            )
            pending_row = receipts_pending._router_scheduler_row_for_controller_entry(
                router,
                run_root,
                {"router_scheduler_row_id": "missing-row"},
            )
            done_receipt = receipts_pending._done_controller_receipt_for_entry(
                router,
                run_root,
                {"action_id": "missing-action"},
            )
            scheduled_reconciliation = receipts_scheduled._scheduler_row_reconciliation_for_entry(
                router,
                run_root,
                {"router_scheduler_row_id": "missing-row"},
            )
            backfill = receipts_scheduled._backfill_scheduler_row_from_reconciled_controller_action(
                router,
                project_root,
                run_root,
                run_state,
                {"router_scheduler_row_id": ""},
                source="contract_test",
            )
            maybe_receipt = receipts_writes._maybe_write_controller_receipt_for_pending(
                router,
                project_root,
                run_root,
                run_state,
                {},
                status="done",
            )

        self.assertEqual(repair["reason"], "no_declared_missing_deliverables")
        self.assertEqual(pending_row, {})
        self.assertEqual(done_receipt, {})
        self.assertIsNone(scheduled_reconciliation)
        self.assertEqual(backfill["reason"], "controller_action_has_no_router_scheduler_row")
        self.assertIsNone(maybe_receipt)

    def test_event_wait_repair_external_contracts(self) -> None:
        first_hash = event_identity._stable_identity_hash(router, {"event": "pm_approves_startup_activation"})
        second_hash = event_identity._stable_identity_hash(router, {"event": "pm_approves_startup_activation"})
        self.assertEqual(first_hash, second_hash)
        self.assertEqual(len(first_hash), 64)
        self.assertTrue(
            event_identity._record_event_from_role_matches(
                router,
                "pm_approves_startup_activation",
                "project_manager",
                "project_manager",
            )
        )
        self.assertEqual(event_intake.role_list("worker_a, worker_b"), {"worker_a", "worker_b"})
        self.assertEqual(event_intake.system_card_delivery_flag(router, "pm.route_skeleton"), "pm_route_skeleton_card_delivered")
        self.assertIn("flowpilot_router_events_repair_policy", events_repair.owner_child_module_names())
        self.assertTrue(expected_waits._run_state_has_event({"events": [{"event": "worker_scan_results_returned"}]}, "worker_scan_results_returned"))

        run_state = {"flags": {}}
        pass_event = sorted(router.PRODUCT_BEHAVIOR_MODEL_PASS_EVENTS)[0]
        model_gate_state._sync_model_gate_alias_flags(run_state, pass_event)
        self.assertTrue(run_state["flags"]["product_behavior_model_submitted"])
        self.assertEqual(
            protocol_external_events.external_event_contract("pm_approves_startup_activation")["flag"],
            "startup_activation_approved",
        )

    def test_facade_export_manifest_external_contracts(self) -> None:
        action_exports = manifest_actions.owner_exports_actions()
        controller_exports = manifest_controller.owner_exports_controller()
        route_exports = manifest_route.owner_exports_route()
        startup_exports = manifest_startup.owner_exports_startup()
        terminal_exports = manifest_terminal_work.owner_exports_terminal_work()
        proxy = facade_exports.resolve_facade_export("parse_args", router)

        self.assertIn(("flowpilot_router_cli", True, False), action_exports)
        self.assertTrue(any(key[0] == "flowpilot_router_controller_repair" for key in controller_exports))
        self.assertTrue(any(key[0] == "flowpilot_router_model_gate_state" for key in route_exports))
        self.assertTrue(any(key[0] == "flowpilot_router_startup_bootloader" for key in startup_exports))
        self.assertTrue(any(key[0] == "flowpilot_router_pm_role_followup" for key in terminal_exports))
        self.assertEqual(proxy.__name__, "parse_args")
        self.assertEqual(proxy.__module__, router.__name__)

    def test_lifecycle_startup_system_card_external_contracts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-startup-contracts-") as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-test"
            run_root.mkdir(parents=True)
            run_state = {"run_id": "run-test", "flags": {}}
            lifecycle_path = lifecycle_support._lifecycle_record_path(run_root)
            terminal_clearance = lifecycle_requests._clear_active_control_blocker_for_terminal_lifecycle(
                project_root,
                run_root,
                run_state,
                mode="cancelled_by_user",
                event="user_requests_run_cancel",
                cleared_at="2026-05-18T00:00:00Z",
            )
            startup_support_state, startup_support_run_root = startup_support._ensure_startup_run_state(
                project_root,
                {"run_id": "run-test", "run_root": ".flowpilot/runs/run-test"},
            )
            heartbeat_reset = {"resume_cycle_id": "old", "flags": {"resume_reentry_requested": True}}
            lifecycle_support._reset_resume_cycle_for_wakeup(heartbeat_reset)
            display_hash = startup_display._display_text_hash(router, "FlowPilot display")
            display_gate = startup_display._user_dialog_display_gate(
                router,
                {"display_text": "FlowPilot display"},
                display_kind="route_map",
                display_text="FlowPilot display",
            )
            boot_depends = startup_bootloader._startup_bootloader_action_depends_on_role_slots(
                router,
                "recover_role_agents",
            )
            closure_ready = startup_closure._host_heartbeat_binding_ready(router, run_root, run_state)
            constraints = startup_fact_boundary._controller_boundary_constraints(router)
            normalized = {"startup_questions": {"background_agents": "yes"}}
            startup_intake._normalize_startup_question_stop_boundary(router, normalized)

            with self.assertRaisesRegex((KeyError, RouterError), "card_id|unknown system card"):
                system_cards_delivery._commit_system_card_delivery_artifact(
                    project_root,
                    run_state,
                    run_root,
                    {},
                )

        self.assertEqual(lifecycle_path.name, "run_lifecycle.json")
        self.assertIsNone(terminal_clearance)
        self.assertEqual(startup_support_state["run_id"], "run-test")
        self.assertEqual(startup_support_run_root, run_root)
        self.assertIn("resume_cycle_id", heartbeat_reset)
        self.assertFalse(heartbeat_reset["flags"]["resume_reentry_requested"])
        self.assertEqual(len(display_hash), 64)
        self.assertEqual(display_gate["required_render_target"], "user_dialog")
        self.assertIsInstance(boot_depends, bool)
        self.assertFalse(closure_ready)
        self.assertFalse(constraints["controller_may_read_sealed_bodies"])
        self.assertEqual(startup_flow.owner_module_name(), "flowpilot_router_startup_flow")
        self.assertIn("flowpilot_router_startup_role_context", startup_role_recovery.owner_child_module_names())

    def test_role_prompt_proof_terminal_work_packet_external_contracts(self) -> None:
        action = {"action_type": "check_packet_ledger", "label": "ledger-check"}
        run_state = {"run_id": "run-test", "flags": {}}
        internal_actions._append_router_internal_mechanical_record(
            run_state,
            action,
            status="applied",
            side_effect_applied=False,
        )
        payload_contract = payload_contracts._payload_contract(
            name="contract_test_payload",
            required_object="payload",
            required_fields=["ok"],
            description="Contract test payload.",
        )
        terminal_contract = payload_contracts._terminal_summary_payload_contract()
        role_ledger = role_io_protocol.empty_role_io_protocol_ledger("run-test")

        with tempfile.TemporaryDirectory(prefix="flowpilot-role-terminal-contracts-") as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-test"
            run_root.mkdir(parents=True)
            prompt = prompt_delivery.card_checkin_instruction(
                project_root,
                envelope_path=".flowpilot/runs/run-test/cards/card.json",
                role="project_manager",
                agent_id="agent-pm",
                card_return_event="pm_route_skeleton_acknowledged",
                bundle=False,
            )
            snapshot = role_output_bridge._role_output_snapshot_name(run_root, run_root / "outputs" / "report.json")
            status = route_completion_support._resume_waits_for_pm_decision(
                {"flags": {}, "pending_action": {"action_type": "await_role_decision"}}
            )
            terminal_status = terminal_recovery._recover_terminal_status_from_run_authorities(
                router,
                project_root,
                run_root,
                {"run_id": "run-test", "status": "cancelled_by_user"},
            )
            summary_action = terminal_summary._terminal_summary_action(
                router,
                project_root,
                {"run_id": "run-test"},
                run_root,
                mode="cancelled_by_user",
            )
            closure_closed = terminal_closure._terminal_closure_suite_is_closed(router, run_root)
            material_reconciled = work_packets_next_actions._try_reconcile_material_scan_body_delivery(
                router,
                project_root,
                run_root,
                {"run_id": "run-test", "flags": {}},
            )
            pm_role_reconciled = work_packets_pm_role_actions._try_reconcile_pm_role_work_results(
                router,
                project_root,
                run_root,
                {"run_id": "run-test", "flags": {}},
            )

            with self.assertRaisesRegex(RouterError, "router-owned proof"):
                proof_validation._validate_router_owned_check_proof(
                    project_root,
                    run_root,
                    check_name="startup_mechanical_audit",
                    audit_path=run_root / "startup" / "audit.json",
                )
            with self.assertRaisesRegex(RouterError, "active model-miss reviewer block"):
                route_artifacts_evidence._write_pm_review_block_repair(
                    project_root,
                    run_root,
                    {"run_id": "run-test", "flags": {}},
                    {},
                )
            with self.assertRaisesRegex(RouterError, "self-interrogation"):
                self_interrogation._require_clean_self_interrogation(
                    project_root,
                    run_root,
                    gate_name="contract_test_gate",
                )
            self_issue = self_interrogation._self_interrogation_issue(
                "contract issue",
                record_id="record-1",
                scope="current_node",
            )
            evidence_record = self_interrogation._evidence_path_record(project_root, run_root / "missing.json")

        self.assertTrue(internal_actions._action_is_router_internal_mechanical(action))
        self.assertEqual(len(run_state["router_internal_mechanical_events"]), 1)
        self.assertEqual(payload_contract["schema_version"], router.PAYLOAD_CONTRACT_SCHEMA)
        self.assertIn("summary_markdown", terminal_contract["required_fields"])
        self.assertFalse(pm_role_followup._pm_role_work_channel_open({"flags": {}, "pm_role_work": {"status": "closed"}}))
        self.assertEqual(prompt["command_name"], "receive-card")
        self.assertEqual(snapshot, "outputs__report.json")
        self.assertFalse(status)
        self.assertEqual(role_ledger["schema_version"], role_io_protocol.ROLE_IO_PROTOCOL_LEDGER_SCHEMA)
        self.assertEqual(terminal_status, "cancelled_by_user")
        self.assertEqual(summary_action["action_type"], "write_terminal_summary")
        self.assertFalse(closure_closed)
        self.assertFalse(material_reconciled)
        self.assertFalse(pm_role_reconciled)
        self.assertEqual(self_issue["record_id"], "record-1")
        self.assertFalse(evidence_record["exists"])

    def test_user_flow_external_contracts(self) -> None:
        route = {
            "route_id": "route-001",
            "route_version": "v1",
            "display_depth": 2,
            "nodes": [
                {"id": "root", "node_kind": "root", "children": [{"id": "implement", "label": "Implement"}]},
                {"id": "verify", "label": "Verify"},
            ],
        }
        frontier = {"active_node": "implement", "current_mainline": ["implement"], "status": "running"}
        source_summary = user_flow_source._route_source_summary(route)
        stage = user_flow_stage.classify_current_stage(frontier, route)
        active_node = user_flow_tree._active_node(frontier, {}, route)
        mermaid, metadata = user_flow_mermaid.build_mermaid(
            frontier=frontier,
            route=route,
            current_stage=stage,
            trigger="major_node_entry",
        )
        markdown = user_flow_markdown.build_chat_markdown(
            mermaid,
            generated_at="2026-05-18T00:00:00Z",
            current_stage=stage,
            active_route="route-001",
            active_node=active_node,
            trigger="major_node_entry",
            cockpit_open=False,
            chat_display_required=True,
            return_path={"required": False},
            active_path=[{"node_id": "implement", "label": "Implement"}],
            hidden_leaf_progress={"has_hidden_leaves": False},
            source_status="ok",
            source_findings=[],
        )

        self.assertEqual(source_summary["node_count"], 3)
        self.assertEqual(stage, "execution")
        self.assertEqual(active_node, "implement")
        self.assertIn("flowchart", mermaid)
        self.assertEqual(metadata["layout"], "route_nodes")
        self.assertIn("Current path: Implement", markdown)

    def test_packet_control_plane_and_reviewer_external_contracts(self) -> None:
        state = State()
        issued = list(packet_issue_resume.PMIssuePacket().apply(NodeCase("packet-1", "dispatch", "worker"), state))
        runtime_written = list(packet_relay.PacketRuntimeWrite().apply(issued[0].output, issued[0].state))
        reminder_checked = list(packet_relay.ControllerReminderCheck().apply(runtime_written[0].output, runtime_written[0].state))
        relayed = list(packet_relay.ControllerEnvelopeOnlyHandoff().apply(reminder_checked[0].output, reminder_checked[0].state))
        dispatch_state = replace(relayed[0].state, controller_relay_signatures=("packet-1",))
        dispatched = list(packet_dispatch_results.RouterDirectDispatch().apply(relayed[0].output, dispatch_state))
        resumed = list(packet_issue_resume.HeartbeatResumeLoad().apply(HeartbeatCase("heartbeat-packet"), state))
        reviewed = list(
            packet_review_pm.ReviewerResultEnvelopeCheck().apply(
                NodeResult("packet-1", "worker_a", "agent-worker_a"),
                State(result_controller_relay_signatures=("packet-1",), result_ledger_records=("packet-1",)),
            )
        )
        invariant = packet_invariants.controller_handoff_body_leak_never_advances(State(), [])

        with tempfile.TemporaryDirectory(prefix="flowpilot-packet-reviewer-contracts-") as tmp:
            project_root = Path(tmp)
            packet_body = project_root / ".flowpilot" / "runs" / "run-test" / "packets" / "packet-1.md"
            result_body = project_root / ".flowpilot" / "runs" / "run-test" / "results" / "packet-1.md"
            packet_body.parent.mkdir(parents=True)
            result_body.parent.mkdir(parents=True)
            packet_body.write_text("packet body", encoding="utf-8")
            result_body.write_text("result body", encoding="utf-8")
            packet_envelope = {
                "packet_id": "packet-1",
                "to_role": "worker_a",
                "body_path": str(packet_body.relative_to(project_root)),
                "body_hash": hashlib.sha256(b"packet body").hexdigest(),
                "body_opened_by_role": {
                    "role": "worker_a",
                    "controller_relay_verified": True,
                    "body_hash_verified": True,
                },
                "controller_relay": {"verified": True, "recipient_role": "worker_a"},
            }
            result_envelope = {
                "packet_id": "packet-1",
                "completed_by_role": "worker_a",
                "completed_by_agent_id": "agent-worker_a",
                "next_recipient": "human_like_reviewer",
                "result_body_path": str(result_body.relative_to(project_root)),
                "result_body_hash": hashlib.sha256(b"result body").hexdigest(),
                "result_body_opened_by_role": {
                    "role": "human_like_reviewer",
                    "controller_relay_verified": True,
                    "body_hash_verified": True,
                },
                "controller_relay": {"verified": True, "recipient_role": "human_like_reviewer"},
            }
            paths = packet_runtime.packet_paths(project_root, "packet-1", "run-test")
            write_json(
                paths["packet_ledger"],
                {
                    "schema_version": packet_runtime.PACKET_LEDGER_SCHEMA,
                    "run_id": "run-test",
                    "packets": [
                        {
                            "packet_id": "packet-1",
                            "packet_body_opened_by_role": "worker_a",
                            "packet_body_opened_after_controller_relay_check": True,
                            "result_body_opened_by_role": "human_like_reviewer",
                            "result_body_opened_after_controller_relay_check": True,
                            "result_body_hash": result_envelope["result_body_hash"],
                            "result_body_path": result_envelope["result_body_path"],
                            "result_envelope_path": str(paths["result_envelope"].relative_to(project_root)),
                        }
                    ],
                },
            )
            write_json(paths["result_envelope"], result_envelope)
            audit = packet_runtime_reviewer.validate_for_reviewer(
                project_root,
                packet_envelope=packet_envelope,
                result_envelope=result_envelope,
                agent_role_map={"agent-worker_a": "worker_a"},
            )

        self.assertEqual(issued[0].label, "pm_packet_issued")
        self.assertEqual(runtime_written[0].label, "packet_physical_files_written")
        self.assertEqual(reminder_checked[0].label, "controller_reminder_checked")
        self.assertEqual(relayed[0].label, "controller_handoff_envelope_only")
        self.assertEqual(dispatched[0].label, "router_direct_dispatch_approved")
        self.assertEqual(resumed[0].label, "heartbeat_state_loaded")
        self.assertEqual(reviewed[0].label, "result_envelope_checked")
        self.assertTrue(invariant.ok)
        self.assertTrue(audit["packet_envelope_checked"])
        self.assertTrue(audit["result_envelope_checked"])


if __name__ == "__main__":
    unittest.main()
