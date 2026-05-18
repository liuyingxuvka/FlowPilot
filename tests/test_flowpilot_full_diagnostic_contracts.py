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
import flowpilot_router_facade_imports as router_facade_imports  # noqa: E402
import flowpilot_runtime as flowpilot_runtime_cli  # noqa: E402
import flowpilot_runtime_args as flowpilot_runtime_args  # noqa: E402
import flowpilot_runtime_commands as flowpilot_runtime_commands  # noqa: E402
import flowpilot_runtime_role_output_commands as flowpilot_runtime_role_output_commands  # noqa: E402
import flowpilot_router_cli as router_cli  # noqa: E402
import flowpilot_router_control_transactions as control_transactions  # noqa: E402
import flowpilot_router_controller_repair_schedule as controller_repair_schedule  # noqa: E402
import flowpilot_router_controller_repair_deliverables as controller_repair_deliverables  # noqa: E402
import flowpilot_router_controller_repair_deliverable_contracts as controller_repair_deliverable_contracts  # noqa: E402
import flowpilot_router_controller_repair_deliverable_projection as controller_repair_deliverable_projection  # noqa: E402
import flowpilot_router_controller_repair_deliverable_projection_boundary as controller_repair_deliverable_projection_boundary  # noqa: E402
import flowpilot_router_controller_repair_deliverable_resolution as controller_repair_deliverable_resolution  # noqa: E402
import flowpilot_router_controller_repair_mail as controller_repair_mail  # noqa: E402
import flowpilot_router_controller_repair_mail_delivery as controller_repair_mail_delivery  # noqa: E402
import flowpilot_router_controller_repair_mail_pending as controller_repair_mail_pending  # noqa: E402
import flowpilot_router_controller_repair_mail_postconditions as controller_repair_mail_postconditions  # noqa: E402
import flowpilot_router_controller_scheduler_receipts_pending as receipts_pending  # noqa: E402
import flowpilot_router_controller_scheduler_receipts_scheduled as receipts_scheduled  # noqa: E402
import flowpilot_router_controller_scheduler_receipts_writes as receipts_writes  # noqa: E402
import flowpilot_router_event_identity as event_identity  # noqa: E402
import flowpilot_router_event_identity_payload as event_identity_payload  # noqa: E402
import flowpilot_router_event_identity_replay as event_identity_replay  # noqa: E402
import flowpilot_router_event_identity_scopes as event_identity_scopes  # noqa: E402
import flowpilot_router_event_intake as event_intake  # noqa: E402
import flowpilot_router_events_repair as events_repair  # noqa: E402
import flowpilot_router_events_repair_blocker_actions as repair_blocker_actions  # noqa: E402
import flowpilot_router_events_repair_blocker_indexes as repair_blocker_indexes  # noqa: E402
import flowpilot_router_events_repair_blocker_records as repair_blocker_records  # noqa: E402
import flowpilot_router_events_repair_blockers as repair_blockers  # noqa: E402
import flowpilot_router_events_repair_event_capability as repair_event_capability  # noqa: E402
import flowpilot_router_events_repair_gate_decisions as repair_gate_decisions  # noqa: E402
import flowpilot_router_events_repair_model_gate as repair_model_gate  # noqa: E402
import flowpilot_router_events_repair_model_miss as repair_model_miss  # noqa: E402
import flowpilot_router_events_repair_policy as repair_policy  # noqa: E402
import flowpilot_router_events_repair_policy_classification as repair_policy_classification  # noqa: E402
import flowpilot_router_events_repair_policy_snapshot as repair_policy_snapshot  # noqa: E402
import flowpilot_router_events_repair_repair_decisions as repair_decisions  # noqa: E402
import flowpilot_router_events_repair_transaction_finalize as repair_transaction_finalize  # noqa: E402
import flowpilot_router_events_repair_transaction_material as repair_transaction_material  # noqa: E402
import flowpilot_router_events_repair_transaction_outcomes as repair_transaction_outcomes  # noqa: E402
import flowpilot_router_events_repair_transaction_paths as repair_transaction_paths  # noqa: E402
import flowpilot_router_events_repair_transaction_resolution as repair_transaction_resolution  # noqa: E402
import flowpilot_router_events_repair_transactions as repair_transactions  # noqa: E402
import flowpilot_router_expected_waits as expected_waits  # noqa: E402
import flowpilot_router_expected_waits_actions as expected_waits_actions  # noqa: E402
import flowpilot_router_expected_waits_events as expected_waits_events  # noqa: E402
import flowpilot_router_expected_waits_reconciliation as expected_waits_reconciliation  # noqa: E402
import flowpilot_router_facade_export_manifest_actions as manifest_actions  # noqa: E402
import flowpilot_router_action_factory_dispatch as action_dispatch  # noqa: E402
import flowpilot_router_action_factory_dispatch_apply as action_dispatch_apply  # noqa: E402
import flowpilot_router_action_factory_dispatch_blockers as action_dispatch_blockers  # noqa: E402
import flowpilot_router_action_factory_dispatch_cards as action_dispatch_cards  # noqa: E402
import flowpilot_router_action_factory_dispatch_waits as action_dispatch_waits  # noqa: E402
import flowpilot_router_action_handlers_packets as action_packets  # noqa: E402
import flowpilot_router_action_handlers_packets_current_node as action_packets_current_node  # noqa: E402
import flowpilot_router_action_handlers_packets_material as action_packets_material  # noqa: E402
import flowpilot_router_action_handlers_packets_pm_role_work as action_packets_pm_role_work  # noqa: E402
import flowpilot_router_action_handlers_packets_types as action_packets_types  # noqa: E402
import flowpilot_router_action_providers as action_providers  # noqa: E402
import flowpilot_router_action_providers_common as action_providers_common  # noqa: E402
import flowpilot_router_action_providers_finalize as action_providers_finalize  # noqa: E402
import flowpilot_router_action_providers_fresh as action_providers_fresh  # noqa: E402
import flowpilot_router_action_providers_lifecycle as action_providers_lifecycle  # noqa: E402
import flowpilot_router_action_providers_pending as action_providers_pending  # noqa: E402
import flowpilot_router_card_returns as card_returns  # noqa: E402
import flowpilot_router_card_returns_actions as card_returns_actions  # noqa: E402
import flowpilot_router_card_returns_pre_review as card_returns_pre_review  # noqa: E402
import flowpilot_router_card_returns_records as card_returns_records  # noqa: E402
import flowpilot_router_card_returns_settlement as card_returns_settlement  # noqa: E402
import flowpilot_router_controller_scheduler_current_work as scheduler_current_work  # noqa: E402
import flowpilot_router_controller_scheduler_ledgers as scheduler_ledgers  # noqa: E402
import flowpilot_router_controller_scheduler_ledgers_actions as scheduler_ledgers_actions  # noqa: E402
import flowpilot_router_controller_scheduler_ledgers_ownership as scheduler_ledgers_ownership  # noqa: E402
import flowpilot_router_controller_scheduler_ledgers_scheduler as scheduler_ledgers_scheduler  # noqa: E402
import flowpilot_router_controller_scheduler_wait_targets as scheduler_wait_targets  # noqa: E402
import flowpilot_router_controller_scheduler_waits as scheduler_waits  # noqa: E402
import flowpilot_router_facade_export_manifest_controller as manifest_controller  # noqa: E402
import flowpilot_router_facade_export_manifest_controller_events as manifest_controller_events  # noqa: E402
import flowpilot_router_facade_export_manifest_controller_lifecycle as manifest_controller_lifecycle  # noqa: E402
import flowpilot_router_facade_export_manifest_controller_repair as manifest_controller_repair  # noqa: E402
import flowpilot_router_facade_export_manifest_controller_scheduler as manifest_controller_scheduler  # noqa: E402
import flowpilot_router_facade_export_manifest_route as manifest_route  # noqa: E402
import flowpilot_router_facade_export_manifest_startup as manifest_startup  # noqa: E402
import flowpilot_router_facade_export_manifest_terminal_work as manifest_terminal_work  # noqa: E402
import flowpilot_router_facade_exports as facade_exports  # noqa: E402
import flowpilot_router_internal_actions as internal_actions  # noqa: E402
import flowpilot_router_lifecycle_requests as lifecycle_requests  # noqa: E402
import flowpilot_router_lifecycle_support as lifecycle_support  # noqa: E402
import flowpilot_router_model_gate_state as model_gate_state  # noqa: E402
import flowpilot_router_payload_contracts as payload_contracts  # noqa: E402
import flowpilot_router_payload_contracts_core as payload_contracts_core  # noqa: E402
import flowpilot_router_payload_contracts_pm as payload_contracts_pm  # noqa: E402
import flowpilot_router_payload_contracts_startup as payload_contracts_startup  # noqa: E402
import flowpilot_router_pm_role_followup as pm_role_followup  # noqa: E402
import flowpilot_router_prompt_delivery as prompt_delivery  # noqa: E402
import flowpilot_router_proof_validation as proof_validation  # noqa: E402
import flowpilot_router_protocol_external_events as protocol_external_events  # noqa: E402
import flowpilot_router_protocol_decision_fields as decision_fields  # noqa: E402
import flowpilot_router_protocol_decision_tables as decision_tables  # noqa: E402
import flowpilot_router_protocol_event_capabilities as event_capabilities  # noqa: E402
import flowpilot_router_protocol_external_events_material as external_events_material  # noqa: E402
import flowpilot_router_protocol_external_events_route as external_events_route  # noqa: E402
import flowpilot_router_protocol_external_events_startup as external_events_startup  # noqa: E402
import flowpilot_router_protocol_external_events_terminal as external_events_terminal  # noqa: E402
import flowpilot_router_protocol_gate_block_specs as gate_block_specs  # noqa: E402
import flowpilot_router_protocol_gate_outcomes as gate_outcomes  # noqa: E402
import flowpilot_router_protocol_gate_pass_clears as gate_pass_clears  # noqa: E402
import flowpilot_router_protocol_gate_reset_flags as gate_reset_flags  # noqa: E402
import flowpilot_router_protocol_runtime_flags as runtime_flags  # noqa: E402
import flowpilot_router_protocol_scoped_event_identity as scoped_event_identity  # noqa: E402
import flowpilot_router_role_io_protocol as role_io_protocol  # noqa: E402
import flowpilot_router_role_output_bridge as role_output_bridge  # noqa: E402
import flowpilot_router_route_artifacts_architecture as route_artifacts_architecture  # noqa: E402
import flowpilot_router_route_artifacts_architecture_gate_blocks as route_artifacts_architecture_gate_blocks  # noqa: E402
import flowpilot_router_route_artifacts_architecture_product as route_artifacts_architecture_product  # noqa: E402
import flowpilot_router_route_artifacts_architecture_route_checks as route_artifacts_architecture_route_checks  # noqa: E402
import flowpilot_router_route_artifacts_evidence as route_artifacts_evidence  # noqa: E402
import flowpilot_router_route_artifacts_nodes as route_artifacts_nodes  # noqa: E402
import flowpilot_router_route_artifacts_nodes_acceptance as route_artifacts_nodes_acceptance  # noqa: E402
import flowpilot_router_route_artifacts_nodes_delegates as route_artifacts_nodes_delegates  # noqa: E402
import flowpilot_router_route_artifacts_nodes_parent as route_artifacts_nodes_parent  # noqa: E402
import flowpilot_router_route_artifacts_planning as route_artifacts_planning  # noqa: E402
import flowpilot_router_route_artifacts_planning_capabilities as route_artifacts_planning_capabilities  # noqa: E402
import flowpilot_router_route_artifacts_planning_contract as route_artifacts_planning_contract  # noqa: E402
import flowpilot_router_route_artifacts_planning_resume as route_artifacts_planning_resume  # noqa: E402
import flowpilot_router_route_completion_support as route_completion_support  # noqa: E402
import flowpilot_router_route_frontier_context as route_frontier_context  # noqa: E402
import flowpilot_router_route_frontier_context_cards as route_frontier_context_cards  # noqa: E402
import flowpilot_router_route_frontier_context_drafts as route_frontier_context_drafts  # noqa: E402
import flowpilot_router_route_frontier_context_memory as route_frontier_context_memory  # noqa: E402
import flowpilot_router_route_frontier_display_plan as route_frontier_display_plan  # noqa: E402
import flowpilot_router_route_frontier_memory_paths as route_frontier_memory_paths  # noqa: E402
import flowpilot_router_route_frontier_nodes as route_frontier_nodes  # noqa: E402
import flowpilot_router_route_frontier_policy as route_frontier_policy  # noqa: E402
import flowpilot_router_route_frontier_policy_completion as route_frontier_policy_completion  # noqa: E402
import flowpilot_router_route_frontier_policy_registry as route_frontier_policy_registry  # noqa: E402
import flowpilot_router_route_frontier_policy_topology as route_frontier_policy_topology  # noqa: E402
import flowpilot_router_route_frontier_status as route_frontier_status  # noqa: E402
import flowpilot_router_route_frontier_status_catalog as route_frontier_status_catalog  # noqa: E402
import flowpilot_router_route_frontier_status_summary as route_frontier_status_summary  # noqa: E402
import flowpilot_router_route_frontier_status_views as route_frontier_status_views  # noqa: E402
import flowpilot_router_route_frontier_views as route_frontier_views  # noqa: E402
import flowpilot_router_self_interrogation as self_interrogation  # noqa: E402
import flowpilot_router_self_interrogation_proofs as self_interrogation_proofs  # noqa: E402
import flowpilot_router_self_interrogation_records as self_interrogation_records  # noqa: E402
import flowpilot_router_self_interrogation_records_requirements as self_interrogation_records_requirements  # noqa: E402
import flowpilot_router_self_interrogation_suggestions as self_interrogation_suggestions  # noqa: E402
import flowpilot_router_startup_bootloader as startup_bootloader  # noqa: E402
import flowpilot_router_startup_bootloader_actions as startup_bootloader_actions  # noqa: E402
import flowpilot_router_startup_bootloader_daemon as startup_bootloader_daemon  # noqa: E402
import flowpilot_router_startup_bootloader_progress as startup_bootloader_progress  # noqa: E402
import flowpilot_router_startup_bootloader_state as startup_bootloader_state  # noqa: E402
import flowpilot_router_startup_closure as startup_closure  # noqa: E402
import flowpilot_router_startup_display as startup_display  # noqa: E402
import flowpilot_router_startup_fact_boundary as startup_fact_boundary  # noqa: E402
import flowpilot_router_startup_fact_boundary_audit as startup_fact_boundary_audit  # noqa: E402
import flowpilot_router_startup_fact_boundary_checks as startup_fact_boundary_checks  # noqa: E402
import flowpilot_router_startup_fact_boundary_controller as startup_fact_boundary_controller  # noqa: E402
import flowpilot_router_startup_fact_boundary_reports as startup_fact_boundary_reports  # noqa: E402
import flowpilot_router_startup_flow as startup_flow  # noqa: E402
import flowpilot_router_startup_intake as startup_intake  # noqa: E402
import flowpilot_router_startup_intake_materialization as startup_intake_materialization  # noqa: E402
import flowpilot_router_startup_intake_ui as startup_intake_ui  # noqa: E402
import flowpilot_router_startup_intake_validation as startup_intake_validation  # noqa: E402
import flowpilot_router_startup_resume_binding as startup_resume_binding  # noqa: E402
import flowpilot_router_startup_resume_binding_actions as startup_resume_actions  # noqa: E402
import flowpilot_router_startup_resume_binding_records as startup_resume_records  # noqa: E402
import flowpilot_router_startup_resume_binding_reports as startup_resume_reports  # noqa: E402
import flowpilot_router_startup_role_recovery as startup_role_recovery  # noqa: E402
import flowpilot_router_startup_role_transactions as startup_role_transactions  # noqa: E402
import flowpilot_router_startup_role_transactions_core as startup_role_transactions_core  # noqa: E402
import flowpilot_router_startup_role_transactions_records as startup_role_transactions_records  # noqa: E402
import flowpilot_router_startup_role_transactions_replay as startup_role_transactions_replay  # noqa: E402
import flowpilot_router_startup_role_transactions_waits as startup_role_transactions_waits  # noqa: E402
import flowpilot_router_startup_support as startup_support  # noqa: E402
import flowpilot_router_system_cards_delivery as system_cards_delivery  # noqa: E402
import flowpilot_router_system_cards_delivery_bundle as system_cards_delivery_bundle  # noqa: E402
import flowpilot_router_system_cards_delivery_single as system_cards_delivery_single  # noqa: E402
import flowpilot_router_system_cards_selection as system_cards_selection  # noqa: E402
import flowpilot_router_system_cards_selection_bundle as system_cards_selection_bundle  # noqa: E402
import flowpilot_router_system_cards_selection_next as system_cards_selection_next  # noqa: E402
import flowpilot_router_system_cards_selection_reconcile as system_cards_selection_reconcile  # noqa: E402
import flowpilot_router_system_cards_selection_tokens as system_cards_selection_tokens  # noqa: E402
import flowpilot_router_terminal_ledger_closure as terminal_closure  # noqa: E402
import flowpilot_router_terminal_ledger_recovery as terminal_recovery  # noqa: E402
import flowpilot_router_terminal_ledger_summary as terminal_summary  # noqa: E402
import flowpilot_router_work_packets_current_node as work_packets_current_node  # noqa: E402
import flowpilot_router_work_packets_current_node_paths as work_packets_current_node_paths  # noqa: E402
import flowpilot_router_work_packets_current_node_relay as work_packets_current_node_relay  # noqa: E402
import flowpilot_router_work_packets_current_node_validation as work_packets_current_node_validation  # noqa: E402
import flowpilot_router_work_packets_next_actions as work_packets_next_actions  # noqa: E402
import flowpilot_router_work_packets_pm_role_actions as work_packets_pm_role_actions  # noqa: E402
import flowpilot_router_work_packets_pm_role_lifecycle as work_packets_pm_role_lifecycle  # noqa: E402
import flowpilot_router_work_packets_pm_role_lifecycle_contracts as work_packets_pm_role_lifecycle_contracts  # noqa: E402
import flowpilot_router_work_packets_pm_role_lifecycle_index as work_packets_pm_role_lifecycle_index  # noqa: E402
import flowpilot_router_work_packets_pm_role_lifecycle_officer as work_packets_pm_role_lifecycle_officer  # noqa: E402
import flowpilot_router_work_packets_pm_role_writes as work_packets_pm_role_writes  # noqa: E402
import flowpilot_router_work_packets_pm_role_writes_decisions as work_packets_pm_role_writes_decisions  # noqa: E402
import flowpilot_router_work_packets_pm_role_writes_request as work_packets_pm_role_writes_request  # noqa: E402
import flowpilot_router_work_packets_pm_role_writes_results as work_packets_pm_role_writes_results  # noqa: E402
import flowpilot_user_flow_markdown as user_flow_markdown  # noqa: E402
import flowpilot_user_flow_mermaid as user_flow_mermaid  # noqa: E402
import flowpilot_user_flow_source as user_flow_source  # noqa: E402
import flowpilot_user_flow_stage as user_flow_stage  # noqa: E402
import flowpilot_user_flow_tree as user_flow_tree  # noqa: E402
import packet_control_plane_model_invariants as packet_invariants  # noqa: E402
import packet_control_plane_model_invariants_dispatch as packet_invariants_dispatch  # noqa: E402
import packet_control_plane_model_invariants_handoff as packet_invariants_handoff  # noqa: E402
import packet_control_plane_model_invariants_origin as packet_invariants_origin  # noqa: E402
import packet_control_plane_model_invariants_resume as packet_invariants_resume  # noqa: E402
import packet_control_plane_model_transitions_dispatch_results as packet_dispatch_results  # noqa: E402
import packet_control_plane_model_transitions_issue_resume as packet_issue_resume  # noqa: E402
import packet_control_plane_model_transitions_packet_relay as packet_relay  # noqa: E402
import packet_control_plane_model_transitions_review_pm as packet_review_pm  # noqa: E402
import packet_runtime  # noqa: E402
import packet_runtime_reviewer  # noqa: E402
import role_output_runtime_schema as role_output_schema  # noqa: E402
import role_output_runtime_schema_authority as role_output_schema_authority  # noqa: E402
import role_output_runtime_schema_io as role_output_schema_io  # noqa: E402
import role_output_runtime_schema_quality as role_output_schema_quality  # noqa: E402
import role_output_runtime_schema_specs as role_output_schema_specs  # noqa: E402
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
            card_returns,
            controller_repair_schedule,
            controller_repair_deliverables,
            controller_repair_mail,
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
            route_artifacts_architecture,
            route_artifacts_nodes,
            route_artifacts_planning,
            route_completion_support,
            route_frontier_context,
            route_frontier_policy,
            route_frontier_status,
            repair_blockers,
            repair_model_gate,
            self_interrogation,
            startup_bootloader,
            startup_closure,
            startup_display,
            startup_fact_boundary,
            startup_flow,
            startup_intake,
            startup_role_recovery,
            startup_role_transactions,
            startup_support,
            system_cards_delivery,
            system_cards_selection,
            work_packets_current_node,
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
        self.assertIs(scheduler_waits._pending_wait_summary, scheduler_wait_targets._pending_wait_summary)
        self.assertIs(scheduler_waits._derive_current_work, scheduler_current_work._derive_current_work)
        self.assertEqual(
            set(scheduler_waits.__all__),
            set(scheduler_wait_targets.__all__) | set(scheduler_current_work.__all__),
        )
        self.assertIs(
            scheduler_ledgers._router_scheduler_ledger_summary,
            scheduler_ledgers_scheduler._router_scheduler_ledger_summary,
        )
        self.assertIs(
            scheduler_ledgers._router_ownership_ledger_summary,
            scheduler_ledgers_ownership._router_ownership_ledger_summary,
        )
        self.assertIs(
            scheduler_ledgers._controller_action_ledger_summary,
            scheduler_ledgers_actions._controller_action_ledger_summary,
        )
        self.assertEqual(
            set(scheduler_ledgers.__all__),
            set(scheduler_ledgers_scheduler.__all__)
            | set(scheduler_ledgers_ownership.__all__)
            | set(scheduler_ledgers_actions.__all__),
        )
        self.assertIs(
            controller_repair_deliverables._controller_deliverable_contract,
            controller_repair_deliverable_contracts._controller_deliverable_contract,
        )
        self.assertIs(
            controller_repair_deliverables._router_scheduler_row_for_controller_entry,
            controller_repair_deliverable_projection._router_scheduler_row_for_controller_entry,
        )
        self.assertIs(
            controller_repair_deliverable_projection._sync_controller_boundary_confirmation_from_artifact,
            controller_repair_deliverable_projection_boundary._sync_controller_boundary_confirmation_from_artifact,
        )
        self.assertIs(
            controller_repair_deliverable_projection._reconcile_controller_boundary_confirmation_projection,
            controller_repair_deliverable_projection_boundary._reconcile_controller_boundary_confirmation_projection,
        )
        self.assertIs(
            controller_repair_deliverables._mark_controller_deliverable_repair_resolved,
            controller_repair_deliverable_resolution._mark_controller_deliverable_repair_resolved,
        )
        self.assertEqual(
            set(controller_repair_deliverables.__all__),
            set(controller_repair_deliverable_contracts.__all__)
            | set(controller_repair_deliverable_projection.__all__)
            | set(controller_repair_deliverable_resolution.__all__),
        )
        self.assertIs(
            controller_repair_mail._pending_controller_action_id,
            controller_repair_mail_pending._pending_controller_action_id,
        )
        self.assertIs(
            controller_repair_mail._mail_sequence_entry,
            controller_repair_mail_delivery._mail_sequence_entry,
        )
        self.assertIs(
            controller_repair_mail._fold_mail_delivery_postcondition,
            controller_repair_mail_postconditions._fold_mail_delivery_postcondition,
        )
        self.assertEqual(
            set(controller_repair_mail.__all__),
            set(controller_repair_mail_pending.__all__)
            | set(controller_repair_mail_delivery.__all__)
            | set(controller_repair_mail_postconditions.__all__),
        )
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
        self.assertIs(event_identity._stable_identity_hash, event_identity_scopes._stable_identity_hash)
        self.assertIs(
            event_identity._load_file_backed_role_payload,
            event_identity_payload._load_file_backed_role_payload,
        )
        self.assertIs(
            event_identity._scoped_event_is_recorded,
            event_identity_replay._scoped_event_is_recorded,
        )
        self.assertEqual(
            set(event_identity.__all__),
            set(event_identity_payload.__all__)
            | set(event_identity_scopes.__all__)
            | set(event_identity_replay.__all__),
        )
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
        self.assertIs(
            repair_policy._blocker_repair_policy_rows,
            repair_policy_snapshot._blocker_repair_policy_rows,
        )
        self.assertIs(
            repair_policy._classify_control_blocker,
            repair_policy_classification._classify_control_blocker,
        )
        self.assertIs(
            repair_policy._event_capability_issue,
            repair_event_capability._event_capability_issue,
        )
        self.assertEqual(
            set(repair_policy.__all__),
            set(repair_policy_snapshot.__all__)
            | set(repair_policy_classification.__all__)
            | set(repair_event_capability.__all__),
        )
        self.assertIs(
            repair_transactions._resolve_delivered_control_blocker,
            repair_transaction_resolution._resolve_delivered_control_blocker,
        )
        self.assertIs(repair_transactions._repair_transaction_path, repair_transaction_paths._repair_transaction_path)
        self.assertIs(repair_transactions._repair_outcome_table, repair_transaction_outcomes._repair_outcome_table)
        self.assertIs(
            repair_transactions._commit_material_scan_repair_generation,
            repair_transaction_material._commit_material_scan_repair_generation,
        )
        self.assertIs(
            repair_transactions._finalize_repair_transaction_outcome,
            repair_transaction_finalize._finalize_repair_transaction_outcome,
        )
        self.assertEqual(
            set(repair_transactions.__all__),
            set(repair_transaction_resolution.__all__)
            | set(repair_transaction_paths.__all__)
            | set(repair_transaction_outcomes.__all__)
            | set(repair_transaction_material.__all__)
            | set(repair_transaction_finalize.__all__),
        )
        self.assertIs(repair_blockers._write_control_blocker, repair_blocker_records._write_control_blocker)
        self.assertIs(repair_blockers._control_blocker_summary, repair_blocker_indexes._control_blocker_summary)
        self.assertIs(repair_blockers._next_control_blocker_action, repair_blocker_actions._next_control_blocker_action)
        self.assertEqual(
            set(repair_blockers.__all__),
            set(repair_blocker_records.__all__)
            | set(repair_blocker_indexes.__all__)
            | set(repair_blocker_actions.__all__),
        )
        self.assertIs(
            repair_model_gate._write_model_miss_triage_decision,
            repair_model_miss._write_model_miss_triage_decision,
        )
        self.assertIs(
            repair_model_gate._repair_transaction_execution_plan,
            repair_decisions._repair_transaction_execution_plan,
        )
        self.assertIs(repair_model_gate._write_gate_decision, repair_gate_decisions._write_gate_decision)
        self.assertEqual(
            set(repair_model_gate.__all__),
            set(repair_model_miss.__all__) | set(repair_decisions.__all__) | set(repair_gate_decisions.__all__),
        )
        self.assertTrue(expected_waits._run_state_has_event({"events": [{"event": "worker_scan_results_returned"}]}, "worker_scan_results_returned"))
        self.assertIs(
            expected_waits._next_expected_role_decision_wait_action,
            expected_waits_actions._next_expected_role_decision_wait_action,
        )
        self.assertIs(expected_waits._run_state_has_event, expected_waits_events._run_state_has_event)
        self.assertIs(
            expected_waits._try_reconcile_material_scan_results,
            expected_waits_reconciliation._try_reconcile_material_scan_results,
        )

        run_state = {"flags": {}}
        pass_event = sorted(router.PRODUCT_BEHAVIOR_MODEL_PASS_EVENTS)[0]
        model_gate_state._sync_model_gate_alias_flags(run_state, pass_event)
        self.assertTrue(run_state["flags"]["product_behavior_model_submitted"])
        self.assertEqual(
            protocol_external_events.external_event_contract("pm_approves_startup_activation")["flag"],
            "startup_activation_approved",
        )
        split_events = {
            **external_events_startup.EXTERNAL_EVENTS_STARTUP,
            **external_events_material.EXTERNAL_EVENTS_MATERIAL,
            **external_events_route.EXTERNAL_EVENTS_ROUTE,
            **external_events_terminal.EXTERNAL_EVENTS_TERMINAL,
        }
        self.assertEqual(split_events, protocol_external_events.EXTERNAL_EVENTS)
        self.assertIs(
            gate_outcomes.PRODUCT_ARCHITECTURE_REPAIR_RESET_FLAGS,
            gate_reset_flags.PRODUCT_ARCHITECTURE_REPAIR_RESET_FLAGS,
        )
        self.assertEqual(
            gate_outcomes.GATE_OUTCOME_BLOCK_EVENT_SPECS,
            gate_block_specs.GATE_OUTCOME_BLOCK_EVENT_SPECS,
        )
        self.assertEqual(
            gate_outcomes.GATE_OUTCOME_PASS_CLEARS_EVENTS,
            gate_pass_clears.GATE_OUTCOME_PASS_CLEARS_EVENTS,
        )
        self.assertIs(decision_tables.STARTUP_ANSWER_ENUMS, decision_fields.STARTUP_ANSWER_ENUMS)
        self.assertIs(decision_tables.RUNTIME_FLAG_DEFAULTS, runtime_flags.RUNTIME_FLAG_DEFAULTS)
        self.assertIs(
            decision_tables.PARENT_NODE_EVENT_CAPABILITY_EVENTS,
            event_capabilities.PARENT_NODE_EVENT_CAPABILITY_EVENTS,
        )
        self.assertIs(
            decision_tables.SCOPED_EVENT_IDENTITY_POLICIES,
            scoped_event_identity.SCOPED_EVENT_IDENTITY_POLICIES,
        )

    def test_facade_export_manifest_external_contracts(self) -> None:
        action_exports = manifest_actions.owner_exports_actions()
        controller_exports = manifest_controller.owner_exports_controller()
        route_exports = manifest_route.owner_exports_route()
        startup_exports = manifest_startup.owner_exports_startup()
        terminal_exports = manifest_terminal_work.owner_exports_terminal_work()
        proxy = facade_exports.resolve_facade_export("parse_args", router)

        self.assertIn(("flowpilot_router_cli", True, False), action_exports)
        self.assertIs(
            action_packets._apply_relay_material_scan_packets,
            action_packets_material._apply_relay_material_scan_packets,
        )
        self.assertIs(
            action_packets._apply_relay_pm_role_work_request_packet,
            action_packets_pm_role_work._apply_relay_pm_role_work_request_packet,
        )
        self.assertIs(
            action_packets._apply_relay_current_node_packet,
            action_packets_current_node._apply_relay_current_node_packet,
        )
        self.assertEqual(action_packets_types.ActionHandlerOutcome().result_extra, {})
        self.assertIsNone(action_packets_types.ActionHandlerOutcome().early_return)
        self.assertEqual(
            set(action_packets.__all__),
            set(action_packets_material.__all__)
            | set(action_packets_pm_role_work.__all__)
            | set(action_packets_current_node.__all__),
        )
        self.assertIs(action_dispatch._dispatch_gate_card_entry, action_dispatch_cards._dispatch_gate_card_entry)
        self.assertIs(action_dispatch._dispatch_gate_wait_action, action_dispatch_waits._dispatch_gate_wait_action)
        self.assertIs(action_dispatch._dispatch_gate_packet_blocker, action_dispatch_blockers._dispatch_gate_packet_blocker)
        self.assertIs(action_dispatch._apply_dispatch_recipient_gate, action_dispatch_apply._apply_dispatch_recipient_gate)
        self.assertEqual(
            set(action_dispatch.__all__) - {"OWNER_MODULE"},
            set(action_dispatch_cards.__all__)
            | set(action_dispatch_waits.__all__)
            | set(action_dispatch_blockers.__all__)
            | set(action_dispatch_apply.__all__),
        )
        self.assertEqual(action_providers.PROVIDER_ORDER, action_providers_common.PROVIDER_ORDER)
        self.assertIs(action_providers.ProviderOutcome, action_providers_common.ProviderOutcome)
        self.assertIs(action_providers.lifecycle_provider, action_providers_lifecycle.lifecycle_provider)
        self.assertIs(action_providers.pending_action_provider, action_providers_pending.pending_action_provider)
        self.assertIs(action_providers.fresh_action_provider, action_providers_fresh.fresh_action_provider)
        self.assertIs(action_providers.finalize_controller_action, action_providers_finalize.finalize_controller_action)
        self.assertEqual(action_providers.ProviderOutcome(action={}).action, {})
        self.assertIs(router.read_json, router_facade_imports.read_json)
        self.assertIs(router.write_json, router_facade_imports.write_json)
        self.assertIs(router.RouterError, router_facade_imports.RouterError)
        self.assertIs(
            router.flowpilot_router_action_handlers,
            router_facade_imports.flowpilot_router_action_handlers,
        )
        self.assertTrue(any(key[0] == "flowpilot_router_controller_repair" for key in controller_exports))
        split_controller_exports = {
            **manifest_controller_repair.OWNER_EXPORTS_CONTROLLER_REPAIR,
            **manifest_controller_scheduler.OWNER_EXPORTS_CONTROLLER_SCHEDULER,
            **manifest_controller_events.OWNER_EXPORTS_CONTROLLER_EVENTS,
            **manifest_controller_lifecycle.OWNER_EXPORTS_CONTROLLER_LIFECYCLE,
        }
        self.assertEqual(split_controller_exports, controller_exports)
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
        self.assertIs(
            startup_resume_binding._normalize_resume_role_agent_records,
            startup_resume_records._normalize_resume_role_agent_records,
        )
        self.assertEqual(
            startup_resume_binding._write_resume_role_rehydration_report.__module__,
            startup_resume_reports.__name__,
        )
        self.assertIs(
            startup_resume_binding._next_resume_action,
            startup_resume_actions._next_resume_action,
        )
        self.assertIs(startup_bootloader._next_boot_action, startup_bootloader_progress._next_boot_action)
        self.assertIs(startup_bootloader._set_boot_flag, startup_bootloader_state._set_boot_flag)
        self.assertIs(
            startup_bootloader._startup_daemon_schedule_bootloader_action,
            startup_bootloader_daemon._startup_daemon_schedule_bootloader_action,
        )
        self.assertIs(startup_bootloader.apply_bootloader_action, startup_bootloader_actions.apply_bootloader_action)
        self.assertIs(startup_fact_boundary._startup_fact_checks, startup_fact_boundary_checks._startup_fact_checks)
        self.assertIs(
            startup_fact_boundary._controller_boundary_constraints,
            startup_fact_boundary_controller._controller_boundary_constraints,
        )
        self.assertIs(
            startup_fact_boundary._startup_mechanical_audit_context,
            startup_fact_boundary_audit._startup_mechanical_audit_context,
        )
        self.assertIs(
            startup_fact_boundary._write_startup_fact_report,
            startup_fact_boundary_reports._write_startup_fact_report,
        )
        self.assertIs(
            startup_intake._normalize_startup_question_stop_boundary,
            startup_intake_ui._normalize_startup_question_stop_boundary,
        )
        self.assertIs(startup_intake._validate_startup_answers, startup_intake_validation._validate_startup_answers)
        self.assertIs(
            startup_intake._write_startup_answers_record,
            startup_intake_materialization._write_startup_answers_record,
        )
        self.assertIs(
            startup_role_transactions._current_crew_generation,
            startup_role_transactions_core._current_crew_generation,
        )
        self.assertIs(
            startup_role_transactions._normalize_role_recovery_agent_records,
            startup_role_transactions_records._normalize_role_recovery_agent_records,
        )
        self.assertIs(
            startup_role_transactions._role_recovery_wait_candidates,
            startup_role_transactions_waits._role_recovery_wait_candidates,
        )
        self.assertIs(
            startup_role_transactions._plan_role_recovery_obligation_replay,
            startup_role_transactions_replay._plan_role_recovery_obligation_replay,
        )
        self.assertEqual(
            set(startup_role_transactions.__all__),
            set(startup_role_transactions_core.__all__)
            | set(startup_role_transactions_records.__all__)
            | set(startup_role_transactions_waits.__all__)
            | set(startup_role_transactions_replay.__all__),
        )
        self.assertIs(
            system_cards_delivery._commit_system_card_delivery_artifact,
            system_cards_delivery_single._commit_system_card_delivery_artifact,
        )
        self.assertIs(
            system_cards_delivery._commit_system_card_bundle_delivery_artifact,
            system_cards_delivery_bundle._commit_system_card_bundle_delivery_artifact,
        )
        self.assertEqual(
            set(system_cards_delivery.__all__),
            set(system_cards_delivery_single.__all__) | set(system_cards_delivery_bundle.__all__),
        )
        self.assertIs(
            system_cards_selection._direct_router_ack_token_for_card,
            system_cards_selection_tokens._direct_router_ack_token_for_card,
        )
        self.assertIs(
            system_cards_selection._next_system_card_action,
            system_cards_selection_next._next_system_card_action,
        )
        self.assertIs(
            system_cards_selection._next_system_card_bundle_action,
            system_cards_selection_bundle._next_system_card_bundle_action,
        )
        self.assertIs(
            system_cards_selection._reconcile_durable_wait_evidence,
            system_cards_selection_reconcile._reconcile_durable_wait_evidence,
        )
        self.assertEqual(
            set(system_cards_selection.__all__),
            set(system_cards_selection_tokens.__all__)
            | set(system_cards_selection_next.__all__)
            | set(system_cards_selection_bundle.__all__)
            | set(system_cards_selection_reconcile.__all__),
        )

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
        self.assertIs(payload_contracts._payload_contract, payload_contracts_startup._payload_contract)
        self.assertIs(payload_contracts._payload_contract, payload_contracts_core._payload_contract)
        self.assertIs(
            payload_contracts._startup_answers_payload_contract,
            payload_contracts_startup._startup_answers_payload_contract,
        )
        self.assertIs(
            payload_contracts._pm_resume_decision_payload_contract,
            payload_contracts_pm._pm_resume_decision_payload_contract,
        )
        self.assertIs(
            payload_contracts._role_decision_payload_contract_for_events,
            payload_contracts_pm._role_decision_payload_contract_for_events,
        )
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
        self.assertIs(card_returns._pending_return_records, card_returns_records._pending_return_records)
        self.assertIs(
            card_returns._current_node_pre_review_reconciliation_blockers,
            card_returns_pre_review._current_node_pre_review_reconciliation_blockers,
        )
        self.assertIs(card_returns._apply_card_return_event_check, card_returns_actions._apply_card_return_event_check)
        self.assertIs(
            card_returns._run_router_return_settlement_finalizers,
            card_returns_settlement._run_router_return_settlement_finalizers,
        )
        self.assertEqual(
            set(card_returns.__all__),
            set(card_returns_records.__all__)
            | set(card_returns_pre_review.__all__)
            | set(card_returns_actions.__all__)
            | set(card_returns_settlement.__all__),
        )
        self.assertIs(
            work_packets_current_node._current_node_packet_records,
            work_packets_current_node_paths._current_node_packet_records,
        )
        self.assertIs(
            work_packets_current_node._issue_current_node_active_holder_leases,
            work_packets_current_node_relay._issue_current_node_active_holder_leases,
        )
        self.assertIs(
            work_packets_current_node._validate_current_node_packet_event,
            work_packets_current_node_validation._validate_current_node_packet_event,
        )
        self.assertEqual(
            set(work_packets_current_node.__all__),
            set(work_packets_current_node_paths.__all__)
            | set(work_packets_current_node_relay.__all__)
            | set(work_packets_current_node_validation.__all__),
        )
        self.assertIs(
            work_packets_pm_role_lifecycle._pm_role_work_request_record,
            work_packets_pm_role_lifecycle_index._pm_role_work_request_record,
        )
        self.assertIs(
            work_packets_pm_role_lifecycle._record_officer_lifecycle_request,
            work_packets_pm_role_lifecycle_officer._record_officer_lifecycle_request,
        )
        self.assertIs(
            work_packets_pm_role_lifecycle._validate_pm_role_work_process_contract_binding,
            work_packets_pm_role_lifecycle_contracts._validate_pm_role_work_process_contract_binding,
        )
        self.assertEqual(
            set(work_packets_pm_role_lifecycle.__all__),
            set(work_packets_pm_role_lifecycle_index.__all__)
            | set(work_packets_pm_role_lifecycle_officer.__all__)
            | set(work_packets_pm_role_lifecycle_contracts.__all__),
        )
        self.assertIs(
            work_packets_pm_role_writes._write_pm_role_work_request,
            work_packets_pm_role_writes_request._write_pm_role_work_request,
        )
        self.assertIs(
            work_packets_pm_role_writes._write_role_work_result_returned,
            work_packets_pm_role_writes_results._write_role_work_result_returned,
        )
        self.assertIs(
            work_packets_pm_role_writes._write_pm_role_work_result_decision,
            work_packets_pm_role_writes_decisions._write_pm_role_work_result_decision,
        )
        self.assertEqual(
            set(work_packets_pm_role_writes.__all__),
            set(work_packets_pm_role_writes_request.__all__)
            | set(work_packets_pm_role_writes_results.__all__)
            | set(work_packets_pm_role_writes_decisions.__all__),
        )
        self.assertEqual(self_issue["record_id"], "record-1")
        self.assertFalse(evidence_record["exists"])
        self.assertIs(
            self_interrogation._pm_suggestion_ledger_status,
            self_interrogation_suggestions._pm_suggestion_ledger_status,
        )
        self.assertIs(
            self_interrogation._self_interrogation_issue,
            self_interrogation_records._self_interrogation_issue,
        )
        self.assertIs(
            self_interrogation._evidence_path_record,
            self_interrogation_proofs._evidence_path_record,
        )
        self.assertIs(
            self_interrogation._require_clean_self_interrogation,
            self_interrogation_records_requirements._require_clean_self_interrogation,
        )
        self.assertIs(role_output_schema.OutputTypeSpec, role_output_schema_specs.OutputTypeSpec)
        self.assertIs(
            role_output_schema.controller_boundary_constraints,
            role_output_schema_io.controller_boundary_constraints,
        )
        self.assertIs(
            role_output_schema.quality_pack_checks_for_run,
            role_output_schema_quality.quality_pack_checks_for_run,
        )
        self.assertIs(
            role_output_schema.validate_direct_router_submission_authority,
            role_output_schema_authority.validate_direct_router_submission_authority,
        )
        self.assertIs(
            route_artifacts_architecture._write_product_function_architecture,
            route_artifacts_architecture_product._write_product_function_architecture,
        )
        self.assertIs(
            route_artifacts_architecture._write_role_gate_report,
            route_artifacts_architecture_product._write_role_gate_report,
        )
        self.assertIs(
            route_artifacts_architecture._write_role_block_report,
            route_artifacts_architecture_gate_blocks._write_role_block_report,
        )
        self.assertIs(
            route_artifacts_architecture._write_route_process_pass_report,
            route_artifacts_architecture_route_checks._write_route_process_pass_report,
        )
        self.assertEqual(
            set(route_artifacts_architecture.__all__),
            set(route_artifacts_architecture_product.__all__)
            | set(route_artifacts_architecture_gate_blocks.__all__)
            | set(route_artifacts_architecture_route_checks.__all__),
        )
        self.assertIs(
            route_artifacts_nodes._write_node_acceptance_plan,
            route_artifacts_nodes_acceptance._write_node_acceptance_plan,
        )
        self.assertIs(
            route_artifacts_nodes._write_parent_backward_targets,
            route_artifacts_nodes_parent._write_parent_backward_targets,
        )
        self.assertIs(
            route_artifacts_nodes._validate_current_node_packet_envelope,
            route_artifacts_nodes_delegates._validate_current_node_packet_envelope,
        )
        self.assertEqual(
            set(route_artifacts_nodes.__all__),
            set(route_artifacts_nodes_acceptance.__all__)
            | set(route_artifacts_nodes_parent.__all__)
            | set(route_artifacts_nodes_delegates.__all__),
        )
        self.assertIs(
            route_artifacts_planning._write_root_acceptance_contract,
            route_artifacts_planning_contract._write_root_acceptance_contract,
        )
        self.assertIs(
            route_artifacts_planning._write_child_skill_selection,
            route_artifacts_planning_capabilities._write_child_skill_selection,
        )
        self.assertIs(
            route_artifacts_planning._write_pm_resume_decision,
            route_artifacts_planning_resume._write_pm_resume_decision,
        )
        self.assertEqual(
            set(route_artifacts_planning.__all__),
            set(route_artifacts_planning_contract.__all__)
            | set(route_artifacts_planning_capabilities.__all__)
            | set(route_artifacts_planning_resume.__all__),
        )

    def test_user_flow_external_contracts(self) -> None:
        self.assertIs(route_frontier_views._route_nodes, route_frontier_nodes._route_nodes)
        self.assertIs(route_frontier_views._route_memory_root, route_frontier_memory_paths._route_memory_root)
        self.assertIs(
            route_frontier_views._display_plan_sync_payload,
            route_frontier_display_plan._display_plan_sync_payload,
        )
        self.assertEqual(
            set(route_frontier_views.__all__),
            set(route_frontier_nodes.__all__)
            | set(route_frontier_memory_paths.__all__)
            | set(route_frontier_display_plan.__all__),
        )
        self.assertIs(route_frontier_context._refresh_route_memory, route_frontier_context_memory._refresh_route_memory)
        self.assertIs(
            route_frontier_context._card_required_source_paths,
            route_frontier_context_cards._card_required_source_paths,
        )
        self.assertIs(route_frontier_context._write_route_draft, route_frontier_context_drafts._write_route_draft)
        self.assertEqual(
            set(route_frontier_context.__all__),
            set(route_frontier_context_memory.__all__)
            | set(route_frontier_context_cards.__all__)
            | set(route_frontier_context_drafts.__all__),
        )
        self.assertIs(
            route_frontier_policy._load_route_action_policy_registry,
            route_frontier_policy_registry._load_route_action_policy_registry,
        )
        self.assertIs(route_frontier_policy._active_frontier, route_frontier_policy_topology._active_frontier)
        self.assertIs(
            route_frontier_policy._route_action_for_event,
            route_frontier_policy_registry._route_action_for_event,
        )
        self.assertEqual(
            set(route_frontier_policy.__all__),
            set(route_frontier_policy_registry.__all__)
            | set(route_frontier_policy_topology.__all__)
            | set(route_frontier_policy_completion.__all__),
        )
        self.assertIs(route_frontier_status._active_ui_task_catalog, route_frontier_status_catalog._active_ui_task_catalog)
        self.assertIs(route_frontier_status._build_progress_summary, route_frontier_status_summary._build_progress_summary)
        self.assertIs(route_frontier_status._write_display_plan_from_route, route_frontier_status_views._write_display_plan_from_route)
        self.assertEqual(
            set(route_frontier_status.__all__),
            set(route_frontier_status_catalog.__all__)
            | set(route_frontier_status_summary.__all__)
            | set(route_frontier_status_views.__all__),
        )

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
        runtime_args = flowpilot_runtime_cli.parse_args(
            ["--root", ".", "open-packet", "--envelope-path", "packet.json", "--role", "worker_a", "--agent-id", "agent-a"]
        )
        self.assertEqual(runtime_args.command, "open-packet")
        self.assertIs(flowpilot_runtime_cli.parse_args, flowpilot_runtime_args.parse_args)
        self.assertIs(flowpilot_runtime_cli._read_body_json, flowpilot_runtime_commands._read_body_json)
        self.assertIs(flowpilot_runtime_cli._receive_card, flowpilot_runtime_commands._receive_card)
        self.assertIs(
            flowpilot_runtime_commands.execute_role_output_command,
            flowpilot_runtime_role_output_commands.execute_role_output_command,
        )
        self.assertEqual(
            set(flowpilot_runtime_cli.__all__),
            set(flowpilot_runtime_args.__all__) | set(flowpilot_runtime_commands.__all__),
        )

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
        child_invariant_exports = (
            set(packet_invariants_origin.__all__)
            | set(packet_invariants_handoff.__all__)
            | set(packet_invariants_dispatch.__all__)
            | set(packet_invariants_resume.__all__)
        )
        self.assertEqual(set(packet_invariants.__all__) - {"INVARIANTS"}, child_invariant_exports)
        self.assertEqual(
            [invariant.name for invariant in packet_invariants.INVARIANTS],
            [
                "no_advance_from_controller_artifact",
                "advance_requires_review_pass",
                "review_pass_requires_role_origin_audit",
                "review_pass_requires_mail_chain_audit",
                "recipient_body_open_requires_controller_relay_signature",
                "missing_or_unopened_mail_requires_pm_restart_or_repair",
                "invalid_origin_block_requires_warning",
                "controller_body_boundary_blocks_never_advance",
                "controller_handoff_body_leak_never_advances",
                "missing_mutual_role_reminder_never_advances",
                "controller_relay_requires_physical_files_and_envelope_only_handoff",
                "holder_change_requires_user_status_update",
                "cockpit_missing_major_node_requires_chat_mermaid",
                "dispatch_requires_packet_envelope_and_hash_checks",
                "dispatch_requires_output_contract_and_run_scoped_result_paths",
                "packet_integrity_blocks_never_advance",
                "review_pass_requires_result_envelope_body_and_agent_checks",
                "result_body_integrity_blocks_never_advance",
                "result_relay_requires_packet_open_and_result_ledger",
                "wrong_role_completion_never_advances",
                "result_requires_dispatch",
                "dispatch_requires_controller_reminder",
                "packet_open_blocks_never_produce_result_or_advance",
                "heartbeat_resume_packet_requires_pm_request",
                "heartbeat_resume_packet_requires_loaded_state",
                "ambiguous_worker_state_never_advances",
                "missing_heartbeat_state_never_advances",
            ],
        )


if __name__ == "__main__":
    unittest.main()
