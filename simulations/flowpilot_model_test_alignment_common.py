"""Common declarations for FlowPilot model-test alignment diagnostics."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from flowguard import (
    CodeBoundaryContract,
    CodeBoundaryObservation,
    CodeContract,
    ModelObligation,
    ModelTestAlignmentPlan,
    TestEvidence,
)

try:  # pragma: no cover
    from .flowpilot_evidence_truth import derived_owner_proof
except ImportError:  # pragma: no cover
    from flowpilot_evidence_truth import derived_owner_proof

ROOT = Path(__file__).resolve().parents[1]

HAPPY = "happy_path"
FAILURE = "failure_path"
EDGE = "edge_path"
NEGATIVE = "negative_path"
REPLAY = "replay"
PASSED = "passed"
RUNNING = "running"

_EXECUTION_EVIDENCE_BUNDLE: dict[str, Any] | None = None
_DECLARATION_ONLY = True
_EXECUTION_EVIDENCE_SCOPE = "routine"


def configure_execution_evidence(
    bundle: dict[str, Any] | None,
    *,
    declaration_only: bool,
    evidence_scope: str = "routine",
) -> None:
    """Set the current proof bundle used while constructing alignment rows."""

    global _EXECUTION_EVIDENCE_BUNDLE, _DECLARATION_ONLY, _EXECUTION_EVIDENCE_SCOPE
    _EXECUTION_EVIDENCE_BUNDLE = bundle
    _DECLARATION_ONLY = declaration_only
    _EXECUTION_EVIDENCE_SCOPE = evidence_scope


def current_execution_evidence_bundle() -> dict[str, Any] | None:
    return _EXECUTION_EVIDENCE_BUNDLE


def current_execution_evidence_scope() -> str:
    return _EXECUTION_EVIDENCE_SCOPE

SOURCE_AUDIT_BOUNDARY = (
    "Source-contract alignment is a conservative AST-supported subset of "
    "critical externally visible Python surfaces. It proves that selected "
    "tests directly call the declared code contract symbols and assert their "
    "external boundary. It does not replace the broader declaration alignment, "
    "runtime conformance replay, or long FlowGuard regressions."
)

FULL_DIAGNOSTIC_BOUNDARY = (
    "Full model-test-code diagnostics inventory repository maintenance "
    "surfaces and classify coverage gaps. They are coverage-accounting "
    "evidence: a covered row means the surface has model/test/code binding "
    "evidence, not that every internal behavior has been semantically proved."
)

ASSET_FACADE_MODULES = {
    "card_runtime",
    "flowpilot_runtime",
    "flowpilot_router",
    "flowpilot_router_action_factory",
    "flowpilot_router_action_handlers",
    "flowpilot_router_controller_scheduler",
    "flowpilot_router_controller_scheduler_receipts",
    "flowpilot_router_facade_export_manifest",
    "flowpilot_router_route_artifacts",
    "flowpilot_router_route_frontier",
    "flowpilot_router_system_cards",
    "flowpilot_router_terminal_ledger",
    "flowpilot_router_work_packets",
    "flowpilot_router_work_packets_pm_role",
    "flowpilot_user_flow_diagram",
    "packet_control_plane_model",
    "packet_control_plane_model_transitions",
    "packet_runtime",
    "role_output_runtime",
}

FACADE_PARITY_EXTERNAL_CONTRACT_SURFACE_IDS = {
    "asset:flowpilot_closure_kernel",
    "asset:flowpilot_control_plane_contracts",
    "asset:packet_runtime",
    "asset:flowpilot_runtime",
    "asset:flowpilot_runtime_args",
    "asset:flowpilot_runtime_command_dispatch",
    "asset:flowpilot_runtime_commands",
    "asset:flowpilot_runtime_role_output_commands",
    "asset:flowpilot_router",
    "asset:flowpilot_router_facade_imports",
    "asset:flowpilot_router_contract_index",
    "asset:flowpilot_router_controller_scheduler_receipts",
    "asset:flowpilot_router_controller_scheduler_receipts_packet_fold_evidence",
    "asset:flowpilot_router_controller_scheduler_receipts_packet_fold_record_evidence",
    "asset:flowpilot_router_controller_scheduler_receipts_packet_folds",
    "asset:flowpilot_router_work_packets_pm_role",
    "asset:flowpilot_router_terminal_ledger",
    "asset:flowpilot_router_terminal_ledger_flowguard_coverage",
    "asset:flowpilot_router_terminal_ledger_writer",
    "asset:flowpilot_router_facade_export_manifest_controller_events",
    "asset:flowpilot_router_facade_export_manifest_controller_lifecycle",
    "asset:flowpilot_router_facade_export_manifest_controller_repair",
    "asset:flowpilot_router_facade_export_manifest_controller_scheduler",
    "asset:flowpilot_router_protocol_external_events_material",
    "asset:flowpilot_router_protocol_external_events_route",
    "asset:flowpilot_router_protocol_external_events_startup",
    "asset:flowpilot_router_protocol_external_events_terminal",
    "asset:flowpilot_router_protocol_decision_fields",
    "asset:flowpilot_router_protocol_event_capabilities",
    "asset:flowpilot_router_protocol_dispatch_policy",
    "asset:flowpilot_router_protocol_external_event_data",
    "asset:flowpilot_router_protocol_external_event_data_material",
    "asset:flowpilot_router_protocol_external_event_data_route",
    "asset:flowpilot_router_protocol_external_event_data_startup",
    "asset:flowpilot_router_protocol_external_event_data_terminal",
    "asset:flowpilot_router_protocol_external_event_registry",
    "asset:flowpilot_router_protocol_gate_registry",
    "asset:flowpilot_router_protocol_runtime_flags",
    "asset:flowpilot_router_protocol_scoped_event_identity",
    "asset:flowpilot_router_protocol_gate_block_specs",
    "asset:flowpilot_router_protocol_gate_pass_clears",
    "asset:flowpilot_router_protocol_gate_reset_flags",
    "asset:flowpilot_router_protocol_process_contracts",
    "asset:flowpilot_router_action_factory_dispatch",
    "asset:flowpilot_router_action_factory_dispatch_apply",
    "asset:flowpilot_router_action_factory_dispatch_blockers",
    "asset:flowpilot_router_action_factory_dispatch_cards",
    "asset:flowpilot_router_action_factory_dispatch_waits",
    "asset:flowpilot_router_action_handlers_packets_current_node",
    "asset:flowpilot_router_action_handlers_packets_material",
    "asset:flowpilot_router_action_handlers_packets_pm_role_work",
    "asset:flowpilot_router_action_handlers_packets_types",
    "asset:flowpilot_router_action_providers",
    "asset:flowpilot_router_action_providers_common",
    "asset:flowpilot_router_action_providers_finalize",
    "asset:flowpilot_router_action_providers_fresh",
    "asset:flowpilot_router_action_providers_lifecycle",
    "asset:flowpilot_router_action_providers_pending",
    "asset:flowpilot_router_card_returns",
    "asset:flowpilot_router_card_returns_actions",
    "asset:flowpilot_router_card_returns_pre_review",
    "asset:flowpilot_router_card_returns_records",
    "asset:flowpilot_router_card_returns_settlement",
    "asset:flowpilot_router_controller_repair_deliverable_contracts",
    "asset:flowpilot_router_controller_repair_deliverable_projection",
    "asset:flowpilot_router_controller_repair_deliverable_projection_boundary",
    "asset:flowpilot_router_controller_repair_deliverable_resolution",
    "asset:flowpilot_router_controller_repair_deliverables",
    "asset:flowpilot_router_controller_repair_mail",
    "asset:flowpilot_router_controller_repair_mail_delivery",
    "asset:flowpilot_router_controller_repair_mail_pending",
    "asset:flowpilot_router_controller_repair_mail_postconditions",
    "asset:flowpilot_router_controller_scheduler_current_work",
    "asset:flowpilot_router_controller_scheduler_ledgers",
    "asset:flowpilot_router_controller_scheduler_ledgers_actions",
    "asset:flowpilot_router_controller_scheduler_ledgers_ownership",
    "asset:flowpilot_router_controller_scheduler_ledgers_scheduler",
    "asset:flowpilot_router_controller_scheduler_wait_targets",
    "asset:flowpilot_router_controller_scheduler_standby_task",
    "asset:flowpilot_router_controller_wait_audit_scanners",
    "asset:flowpilot_router_event_identity",
    "asset:flowpilot_router_event_identity_payload",
    "asset:flowpilot_router_event_identity_replay",
    "asset:flowpilot_router_event_identity_scopes",
    "asset:flowpilot_router_events_repair_blocker_actions",
    "asset:flowpilot_router_events_repair_blocker_indexes",
    "asset:flowpilot_router_events_repair_blocker_records",
    "asset:flowpilot_router_events_repair_blockers",
    "asset:flowpilot_router_events_repair_event_capability",
    "asset:flowpilot_router_events_repair_gate_decisions",
    "asset:flowpilot_router_events_repair_model_gate",
    "asset:flowpilot_router_events_repair_model_miss",
    "asset:flowpilot_router_events_repair_policy",
    "asset:flowpilot_router_events_repair_policy_classification",
    "asset:flowpilot_router_events_repair_policy_snapshot",
    "asset:flowpilot_router_events_repair_repair_decisions",
    "asset:flowpilot_router_events_repair_transaction_finalize",
    "asset:flowpilot_router_events_repair_transaction_outcomes",
    "asset:flowpilot_router_events_repair_transaction_paths",
    "asset:flowpilot_router_events_repair_transaction_resolution",
    "asset:flowpilot_router_events_repair_transactions",
    "asset:flowpilot_router_expected_waits",
    "asset:flowpilot_router_expected_waits_actions",
    "asset:flowpilot_router_expected_waits_events",
    "asset:flowpilot_router_expected_waits_reconciliation",
    "asset:flowpilot_router_payload_contracts",
    "asset:flowpilot_router_payload_contracts_core",
    "asset:flowpilot_router_payload_contracts_pm",
    "asset:flowpilot_router_payload_contracts_startup",
    "asset:flowpilot_router_route_artifacts_architecture",
    "asset:flowpilot_router_route_artifacts_architecture_gate_blocks",
    "asset:flowpilot_router_route_artifacts_architecture_product",
    "asset:flowpilot_router_route_artifacts_architecture_product_core",
    "asset:flowpilot_router_route_artifacts_architecture_product_decisions",
    "asset:flowpilot_router_route_artifacts_architecture_product_intent",
    "asset:flowpilot_router_route_artifacts_architecture_route_checks",
    "asset:flowpilot_router_route_artifacts_nodes",
    "asset:flowpilot_router_route_artifacts_nodes_acceptance",
    "asset:flowpilot_router_route_artifacts_nodes_delegates",
    "asset:flowpilot_router_route_artifacts_nodes_parent",
    "asset:flowpilot_router_route_artifacts_planning",
    "asset:flowpilot_router_route_artifacts_planning_capabilities",
    "asset:flowpilot_router_route_artifacts_planning_contract",
    "asset:flowpilot_router_route_artifacts_planning_resume",
    "asset:flowpilot_router_route_frontier_context",
    "asset:flowpilot_router_route_frontier_context_cards",
    "asset:flowpilot_router_route_frontier_context_drafts",
    "asset:flowpilot_router_route_frontier_context_memory",
    "asset:flowpilot_router_route_frontier_display_plan",
    "asset:flowpilot_router_route_frontier_memory_paths",
    "asset:flowpilot_router_route_frontier_nodes",
    "asset:flowpilot_router_route_frontier_policy",
    "asset:flowpilot_router_route_frontier_policy_completion",
    "asset:flowpilot_router_route_frontier_policy_completion_authority",
    "asset:flowpilot_router_route_frontier_policy_completion_context",
    "asset:flowpilot_router_route_frontier_policy_completion_ledger",
    "asset:flowpilot_router_route_frontier_policy_registry",
    "asset:flowpilot_router_route_frontier_policy_topology",
    "asset:flowpilot_router_route_frontier_status",
    "asset:flowpilot_router_route_frontier_status_catalog",
    "asset:flowpilot_router_route_frontier_status_summary",
    "asset:flowpilot_router_route_frontier_status_views",
    "asset:flowpilot_router_self_interrogation",
    "asset:flowpilot_router_self_interrogation_proofs",
    "asset:flowpilot_router_self_interrogation_records",
    "asset:flowpilot_router_self_interrogation_records_requirements",
    "asset:flowpilot_router_self_interrogation_suggestions",
    "asset:flowpilot_router_startup_bootloader",
    "asset:flowpilot_router_startup_bootloader_actions",
    "asset:flowpilot_router_startup_bootloader_daemon",
    "asset:flowpilot_router_startup_bootloader_progress",
    "asset:flowpilot_router_startup_bootloader_state",
    "asset:flowpilot_router_startup_mechanical_boundary",
    "asset:flowpilot_router_startup_mechanical_boundary_audit",
    "asset:flowpilot_router_startup_mechanical_boundary_checks",
    "asset:flowpilot_router_startup_mechanical_boundary_controller",
    "asset:flowpilot_router_startup_intake",
    "asset:flowpilot_router_startup_intake_materialization",
    "asset:flowpilot_router_startup_intake_ui",
    "asset:flowpilot_router_startup_intake_validation",
    "asset:flowpilot_router_startup_resume_binding_actions",
    "asset:flowpilot_router_startup_resume_binding_records",
    "asset:flowpilot_router_startup_resume_binding_reports",
    "asset:flowpilot_router_startup_role_transactions",
    "asset:flowpilot_router_startup_role_transactions_core",
    "asset:flowpilot_router_startup_role_transactions_records",
    "asset:flowpilot_router_startup_role_transactions_replay",
    "asset:flowpilot_router_startup_role_transactions_waits",
    "asset:flowpilot_router_system_cards_delivery",
    "asset:flowpilot_router_system_cards_delivery_bundle",
    "asset:flowpilot_router_system_cards_delivery_single",
    "asset:flowpilot_router_system_cards_selection",
    "asset:flowpilot_router_system_cards_selection_bundle",
    "asset:flowpilot_router_system_cards_selection_next",
    "asset:flowpilot_router_system_cards_selection_reconcile",
    "asset:flowpilot_router_system_cards_selection_tokens",
    "asset:flowpilot_router_daemon_runtime_diagnostics",
    "asset:flowpilot_router_daemon_runtime_lock",
    "asset:flowpilot_router_work_packets_current_node",
    "asset:flowpilot_router_work_packets_current_node_paths",
    "asset:flowpilot_router_work_packets_current_node_relay",
    "asset:flowpilot_router_work_packets_current_node_relay_leases",
    "asset:flowpilot_router_work_packets_current_node_relay_runtime_ops",
    "asset:flowpilot_router_work_packets_current_node_validation",
    "asset:flowpilot_router_work_packets_pm_role_lifecycle_contracts",
    "asset:flowpilot_router_work_packets_pm_role_lifecycle_index",
    "asset:flowpilot_router_work_packets_pm_role_lifecycle_flowguard_operator",
    "asset:flowpilot_router_work_packets_pm_role_writes_decisions",
    "asset:flowpilot_router_work_packets_pm_role_writes_decisions_formal_gate",
    "asset:flowpilot_router_work_packets_pm_role_writes_decisions_package_disposition",
    "asset:flowpilot_router_work_packets_pm_role_writes_decisions_packet_outcomes",
    "asset:flowpilot_router_work_packets_pm_role_writes_decisions_role_result",
    "asset:flowpilot_router_work_packets_pm_role_writes_request",
    "asset:flowpilot_router_work_packets_pm_role_writes_results",
    "asset:flowpilot_router_work_packets_research_next",
    "asset:flowpilot_router_work_packets_role_agents",
    "asset:flowpilot_user_flow_diagram",
    "asset:flowpilot_user_flow_diagram_cli",
    "asset:flowpilot_user_flow_diagram_generate",
    "asset:flowpilot_controller_break_glass_cli",
    "asset:flowpilot_controller_break_glass_core",
    "asset:flowpilot_controller_break_glass_recovery",
    "asset:packet_control_plane_model_invariants_dispatch",
    "asset:packet_control_plane_model_invariants_handoff",
    "asset:packet_control_plane_model_invariants_origin",
    "asset:packet_control_plane_model_invariants_resume",
    "asset:packet_runtime_active_holder_core",
    "asset:packet_runtime_active_holder_events",
    "asset:packet_runtime_active_holder_lease",
    "asset:packet_runtime_active_holder_results",
    "asset:packet_runtime_cli",
    "asset:packet_runtime_cli_args",
    "asset:packet_runtime_cli_main",
    "asset:role_output_runtime_schema",
    "asset:role_output_runtime_schema_authority",
    "asset:role_output_runtime_schema_io",
    "asset:role_output_runtime_schema_payload",
    "asset:role_output_runtime_schema_quality",
    "asset:role_output_runtime_schema_specs",
    "asset:role_output_runtime_envelope_receipts",
}

SCRIPT_CLI_EXTERNAL_CONTRACT_STEMS = {
    "audit_local_install_sync",
    "check_install",
    "check_public_release",
    "flowpilot_lifecycle",
    "flowpilot_maintenance_registry",
    "flowpilot_outputs",
    "flowpilot_packets",
    "install_flowpilot",
    "run_test_tier",
}

ASSET_MODEL_BINDING_PREFIXES = {
    "flowpilot_runtime_": "runtime_cli_architecture",
    "flowpilot_router_": "router_runtime_architecture",
    "packet_runtime_": "packet_runtime_architecture",
    "role_output_runtime_": "role_output_runtime_architecture",
}

ASSET_MODEL_BINDING_STEMS = {
    "flowpilot_controller_break_glass_core": "controller_break_glass_runtime_contracts",
    "flowpilot_controller_break_glass_cli": "controller_break_glass_runtime_contracts",
    "flowpilot_controller_break_glass_recovery": "recovery_supervisor_contracts",
    "flowpilot_runtime_path_evidence": "runtime_path_contracts",
    "flowpilot_router_daemon_runtime_diagnostics": "router_daemon_runtime_architecture",
    "flowpilot_closure_kernel": "control_plane_closure_kernel",
    "flowpilot_control_plane_contracts": "control_plane_contracts",
    "flowpilot_paths": "runtime_path_contracts",
    "run_packet_control_plane_checks": "packet_control_plane_model_checks",
}

SCRIPT_MODEL_BINDING_STEMS = {
    "audit_local_install_sync": "local_install_sync",
    "audit_validation_artifacts": "validation_artifact_audit",
    "check_install": "local_install_sync",
    "check_public_release": "public_release_audit",
    "check_runtime_card_capability_reminders": "runtime_card_capability_reminders",
    "flowpilot_defects": "defect_governance_cli",
    "flowpilot_lifecycle": "lifecycle_cli",
    "flowpilot_maintenance_map": "maintenance_map_cli",
    "flowpilot_maintenance_registry": "maintenance_registry_cli",
    "flowpilot_outputs": "role_output_cli",
    "flowpilot_packets": "packet_runtime_cli",
    "flowpilot_paths": "runtime_path_cli",
    "flowpilot_runtime_retention": "runtime_retention_cli",
    "install_flowpilot": "local_install_sync",
    "refresh_flowpilot_skillguard_contract": "skillguard_deep_contract_maintenance",
    "run_flowguard_background": "flowpilot_test_tiering.background_artifact_contract",
    "run_flowguard_coverage_sweep": "coverage_sweep_runner",
    "run_test_tier": "test_tier_runner",
    "smoke_flowpilot": "smoke_fast_validation",
}

MODEL_CHECK_RUNNER_CONTRACT_TEST_PATH = (
    ROOT / "tests" / "test_flowpilot_model_check_runner_contracts.py"
)
MODEL_CHECK_RUNNER_CONTRACT_TEST_MARKER = "MODEL_CHECK_RUNNER_CONTRACT_STEMS"
ASSET_SURFACE_CONTRACT_TEST_PATH = (
    ROOT / "tests" / "test_flowpilot_asset_surface_contracts.py"
)
ASSET_SURFACE_CONTRACT_TEST_MARKER = "ASSET_SURFACE_CONTRACT_TEST_PATH"
SCRIPT_SURFACE_CONTRACT_TEST_PATH = (
    ROOT / "tests" / "test_flowpilot_script_surface_contracts.py"
)
SCRIPT_SURFACE_CONTRACT_TEST_MARKER = "SCRIPT_SURFACE_CONTRACT_TEST_PATH"
TEST_TIER_COMMAND_CONTRACT_TEST_MARKER = "test_all_tier_commands_have_external_command_contracts"

STRUCTURE_SPLIT_REPAIR_PLAN = {
    "flowpilot_new": {
        "split_status": "completed_split",
        "split_reason": "current_flowpilot_entrypoint_command_families_extracted_without_legacy_acceptance",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_new_shared.py",
            "skills/flowpilot/assets/flowpilot_new_role_commands.py",
            "skills/flowpilot/assets/flowpilot_new_run_commands.py",
            "skills/flowpilot/assets/flowpilot_new_cli.py",
        ),
        "peer_safety_status": "claimed_by_split_flowpilot_hff_structure_surfaces",
        "safe_split_class": "current_runtime_entrypoint",
        "recommended_next_action": "monitor_flowpilot_new_child_contracts",
        "structure_split_status": "completed",
    },
    "flowguard_project_topology": {
        "split_status": "completed_split",
        "split_reason": "project_topology_collect_render_check_partitions_extracted_without_changing_cli",
        "completed_split_paths": (
            "scripts/flowguard_project_topology_lib/common.py",
            "scripts/flowguard_project_topology_lib/collectors.py",
            "scripts/flowguard_project_topology_lib/render.py",
        ),
        "peer_safety_status": "claimed_by_split_flowpilot_hff_structure_surfaces",
        "safe_split_class": "project_topology_cli",
        "recommended_next_action": "monitor_topology_generator_child_contracts",
        "structure_split_status": "completed",
    },
    "flowpilot_router": {
        "split_status": "completed_split",
        "split_reason": "router_import_alias_surface_extracted_without_changing_entrypoint_contracts",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_facade_imports.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "public_facade_import_surface",
        "recommended_next_action": "monitor_router_facade_import_surface_contracts",
    },
    "flowpilot_router_controller_scheduler_receipts_packet_folds": {
        "split_status": "completed_split",
        "split_reason": "packet_result_receipt_fold_evidence_and_record_checks_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_packet_fold_evidence.py",
            "skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_packet_fold_record_evidence.py",
            "skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_packet_folds.py",
        ),
        "peer_safety_status": "claimed_by_complete_synthetic_agent_coverage_matrix",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "monitor_controller_receipt_packet_fold_child_contracts",
    },
    "flowpilot_router_work_packets_current_node": {
        "split_status": "completed_split",
        "split_reason": "current_node_path_relay_lease_runtime_operation_and_validation_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_work_packets_current_node_paths.py",
            "skills/flowpilot/assets/flowpilot_router_work_packets_current_node_relay.py",
            "skills/flowpilot/assets/flowpilot_router_work_packets_current_node_relay_leases.py",
            "skills/flowpilot/assets/flowpilot_router_work_packets_current_node_relay_runtime_ops.py",
            "skills/flowpilot/assets/flowpilot_router_work_packets_current_node_validation.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "monitor_current_node_child_contracts",
    },
    "flowpilot_router_card_returns": {
        "split_status": "completed_split",
        "split_reason": "card_return_record_pre_review_action_and_settlement_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_card_returns_records.py",
            "skills/flowpilot/assets/flowpilot_router_card_returns_pre_review.py",
            "skills/flowpilot/assets/flowpilot_router_card_returns_actions.py",
            "skills/flowpilot/assets/flowpilot_router_card_returns_settlement.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "monitor_card_return_child_contracts",
    },
    "flowpilot_router_action_providers": {
        "split_status": "completed_split",
        "split_reason": "provider_common_lifecycle_pending_fresh_and_finalize_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_action_providers_common.py",
            "skills/flowpilot/assets/flowpilot_router_action_providers_lifecycle.py",
            "skills/flowpilot/assets/flowpilot_router_action_providers_pending.py",
            "skills/flowpilot/assets/flowpilot_router_action_providers_fresh.py",
            "skills/flowpilot/assets/flowpilot_router_action_providers_finalize.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "runtime_action_provider_helper",
        "recommended_next_action": "monitor_action_provider_child_contracts",
    },
    "role_output_runtime_schema": {
        "split_status": "completed_split",
        "split_reason": "role_output_schema_specs_io_quality_authority_and_payload_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/role_output_runtime_schema_specs.py",
            "skills/flowpilot/assets/role_output_runtime_schema_io.py",
            "skills/flowpilot/assets/role_output_runtime_schema_quality.py",
            "skills/flowpilot/assets/role_output_runtime_schema_authority.py",
            "skills/flowpilot/assets/role_output_runtime_schema_payload.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "monitor_role_output_schema_child_contracts",
    },
    "flowpilot_router_protocol_boot_cards": {
        "split_status": "completed_split",
        "split_reason": "startup_and_system_card_declarative_tables_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_protocol_startup_catalog.py",
            "skills/flowpilot/assets/flowpilot_router_protocol_planning_cards.py",
            "skills/flowpilot/assets/flowpilot_router_protocol_runtime_cards.py",
            "skills/flowpilot/assets/flowpilot_router_protocol_card_metadata.py",
        ),
        "peer_safety_status": "claimed_by_add_runtime_owner_contracts_and_safe_splits",
        "safe_split_class": "declarative_protocol_table",
        "recommended_next_action": "monitor_split_catalog_contracts",
    },
    "flowpilot_router_protocol_decision_tables": {
        "split_status": "completed_split",
        "split_reason": "decision_fields_runtime_flags_event_capabilities_and_scoped_identity_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_protocol_decision_fields.py",
            "skills/flowpilot/assets/flowpilot_router_protocol_runtime_flags.py",
            "skills/flowpilot/assets/flowpilot_router_protocol_event_capabilities.py",
            "skills/flowpilot/assets/flowpilot_router_protocol_scoped_event_identity.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "declarative_protocol_table",
        "recommended_next_action": "monitor_decision_table_child_contracts",
    },
    "flowpilot_router_protocol_gate_outcomes": {
        "split_status": "completed_split",
        "split_reason": "gate_outcome_reset_block_and_pass_clear_tables_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_protocol_gate_reset_flags.py",
            "skills/flowpilot/assets/flowpilot_router_protocol_gate_block_specs.py",
            "skills/flowpilot/assets/flowpilot_router_protocol_gate_pass_clears.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "declarative_protocol_table",
        "recommended_next_action": "monitor_gate_outcome_child_contracts",
    },
    "flowpilot_router_event_identity": {
        "split_status": "completed_split",
        "split_reason": "external_event_payload_scoped_identity_and_replay_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_event_identity_payload.py",
            "skills/flowpilot/assets/flowpilot_router_event_identity_scopes.py",
            "skills/flowpilot/assets/flowpilot_router_event_identity_replay.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "runtime_identity_helper",
        "recommended_next_action": "monitor_event_identity_child_contracts",
    },
    "flowpilot_router_action_factory_dispatch": {
        "split_status": "completed_split",
        "split_reason": "dispatch_gate_card_wait_blocker_and_apply_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_action_factory_dispatch_cards.py",
            "skills/flowpilot/assets/flowpilot_router_action_factory_dispatch_waits.py",
            "skills/flowpilot/assets/flowpilot_router_action_factory_dispatch_blockers.py",
            "skills/flowpilot/assets/flowpilot_router_action_factory_dispatch_apply.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "runtime_dispatch_gate_helper",
        "recommended_next_action": "monitor_dispatch_gate_child_contracts",
    },
    "flowpilot_router_action_handlers_packets": {
        "split_status": "completed_split",
        "split_reason": "material_research_pm_role_work_and_current_node_packet_handlers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_action_handlers_packets_types.py",
            "skills/flowpilot/assets/flowpilot_router_action_handlers_packets_material.py",
            "skills/flowpilot/assets/flowpilot_router_action_handlers_packets_pm_role_work.py",
            "skills/flowpilot/assets/flowpilot_router_action_handlers_packets_current_node.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "runtime_action_handler_helper",
        "recommended_next_action": "monitor_packet_action_handler_child_contracts",
    },
    "flowpilot_router_controller_scheduler_waits": {
        "split_status": "completed_split",
        "split_reason": "wait_target_and_current_work_projection_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_controller_scheduler_wait_targets.py",
            "skills/flowpilot/assets/flowpilot_router_controller_scheduler_current_work.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "runtime_scheduler_wait_helper",
        "recommended_next_action": "monitor_scheduler_wait_child_contracts",
    },
    "flowpilot_router_controller_scheduler_ledgers": {
        "split_status": "completed_split",
        "split_reason": "scheduler_ownership_and_controller_action_ledger_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_controller_scheduler_ledgers_scheduler.py",
            "skills/flowpilot/assets/flowpilot_router_controller_scheduler_ledgers_ownership.py",
            "skills/flowpilot/assets/flowpilot_router_controller_scheduler_ledgers_actions.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "runtime_scheduler_ledger_helper",
        "recommended_next_action": "monitor_scheduler_ledger_child_contracts",
    },
    "flowpilot_router_expected_waits": {
        "split_status": "completed_split",
        "split_reason": "expected_wait_action_event_and_reconciliation_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_expected_waits_actions.py",
            "skills/flowpilot/assets/flowpilot_router_expected_waits_events.py",
            "skills/flowpilot/assets/flowpilot_router_expected_waits_reconciliation.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "runtime_expected_wait_helper",
        "recommended_next_action": "monitor_expected_wait_child_contracts",
    },
    "flowpilot_router_controller_repair_deliverables": {
        "split_status": "completed_split",
        "split_reason": "controller_repair_deliverable_contract_projection_and_resolution_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_controller_repair_deliverable_contracts.py",
            "skills/flowpilot/assets/flowpilot_router_controller_repair_deliverable_projection.py",
            "skills/flowpilot/assets/flowpilot_router_controller_repair_deliverable_projection_boundary.py",
            "skills/flowpilot/assets/flowpilot_router_controller_repair_deliverable_resolution.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "runtime_controller_repair_helper",
        "recommended_next_action": "monitor_controller_repair_deliverable_child_contracts",
    },
    "flowpilot_router_controller_repair_mail": {
        "split_status": "completed_split",
        "split_reason": "controller_repair_mail_pending_delivery_and_postcondition_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_controller_repair_mail_pending.py",
            "skills/flowpilot/assets/flowpilot_router_controller_repair_mail_delivery.py",
            "skills/flowpilot/assets/flowpilot_router_controller_repair_mail_postconditions.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "runtime_controller_repair_helper",
        "recommended_next_action": "monitor_controller_repair_mail_child_contracts",
    },
    "flowpilot_router_events_repair_blockers": {
        "split_status": "completed_split",
        "split_reason": "control_blocker_record_index_and_action_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_events_repair_blocker_records.py",
            "skills/flowpilot/assets/flowpilot_router_events_repair_blocker_indexes.py",
            "skills/flowpilot/assets/flowpilot_router_events_repair_blocker_actions.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "runtime_repair_blocker_helper",
        "recommended_next_action": "monitor_control_blocker_child_contracts",
    },
    "flowpilot_router_events_repair_model_gate": {
        "split_status": "completed_split",
        "split_reason": "model_miss_repair_decision_and_gate_decision_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_events_repair_model_miss.py",
            "skills/flowpilot/assets/flowpilot_router_events_repair_repair_decisions.py",
            "skills/flowpilot/assets/flowpilot_router_events_repair_gate_decisions.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "runtime_repair_model_gate_helper",
        "recommended_next_action": "monitor_repair_model_gate_child_contracts",
    },
    "flowpilot_router_events_repair_policy": {
        "split_status": "completed_split",
        "split_reason": "repair_policy_snapshot_classification_and_event_capability_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_events_repair_policy_snapshot.py",
            "skills/flowpilot/assets/flowpilot_router_events_repair_policy_classification.py",
            "skills/flowpilot/assets/flowpilot_router_events_repair_event_capability.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "runtime_repair_policy_helper",
        "recommended_next_action": "monitor_repair_policy_child_contracts",
    },
    "flowpilot_router_events_repair_transactions": {
        "split_status": "completed_split",
        "split_reason": "repair_transaction_resolution_paths_outcomes_and_finalize_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_events_repair_transaction_resolution.py",
            "skills/flowpilot/assets/flowpilot_router_events_repair_transaction_paths.py",
            "skills/flowpilot/assets/flowpilot_router_events_repair_transaction_outcomes.py",
            "skills/flowpilot/assets/flowpilot_router_events_repair_transaction_finalize.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "runtime_repair_transaction_helper",
        "recommended_next_action": "monitor_repair_transaction_child_contracts",
    },
    "flowpilot_router_facade_export_manifest_controller": {
        "split_status": "completed_split",
        "split_reason": "controller_export_manifest_declarative_shards_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_facade_export_manifest_controller_repair.py",
            "skills/flowpilot/assets/flowpilot_router_facade_export_manifest_controller_scheduler.py",
            "skills/flowpilot/assets/flowpilot_router_facade_export_manifest_controller_events.py",
            "skills/flowpilot/assets/flowpilot_router_facade_export_manifest_controller_lifecycle.py",
        ),
        "peer_safety_status": "claimed_by_continue_flowpilot_structure_maintenance",
        "safe_split_class": "declarative_manifest",
        "recommended_next_action": "monitor_controller_manifest_child_contracts",
    },
    "flowpilot_router_protocol_external_events": {
        "split_status": "completed_split",
        "split_reason": "external_event_declarative_shards_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_protocol_external_events_startup.py",
            "skills/flowpilot/assets/flowpilot_router_protocol_external_events_material.py",
            "skills/flowpilot/assets/flowpilot_router_protocol_external_events_route.py",
            "skills/flowpilot/assets/flowpilot_router_protocol_external_events_terminal.py",
        ),
        "peer_safety_status": "claimed_by_continue_flowpilot_structure_maintenance",
        "safe_split_class": "declarative_protocol_table",
        "recommended_next_action": "monitor_external_event_shard_contracts",
    },
    "flowpilot_router_protocol_external_event_data": {
        "split_status": "completed_split",
        "split_reason": (
            "phase_indexed_external_event_data_split_into_startup_material_route_terminal_tables"
        ),
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_protocol_external_event_data_startup.py",
            "skills/flowpilot/assets/flowpilot_router_protocol_external_event_data_material.py",
            "skills/flowpilot/assets/flowpilot_router_protocol_external_event_data_route.py",
            "skills/flowpilot/assets/flowpilot_router_protocol_external_event_data_terminal.py",
        ),
        "peer_safety_status": "claimed_by_complete_flowpilot_maintenance_convergence",
        "safe_split_class": "declarative_protocol_table",
        "recommended_next_action": "monitor_external_event_data_phase_contracts",
    },
    "flowpilot_router_payload_contracts": {
        "split_status": "completed_split",
        "split_reason": "startup_and_pm_payload_contract_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_payload_contracts_startup.py",
            "skills/flowpilot/assets/flowpilot_router_payload_contracts_core.py",
            "skills/flowpilot/assets/flowpilot_router_payload_contracts_pm.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "runtime_payload_contract_helper",
        "recommended_next_action": "monitor_payload_contract_child_contracts",
    },
    "flowpilot_router_route_artifacts_architecture": {
        "split_status": "completed_split",
        "split_reason": "route_artifact_product_gate_block_and_route_check_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_route_artifacts_architecture_product.py",
            "skills/flowpilot/assets/flowpilot_router_route_artifacts_architecture_gate_blocks.py",
            "skills/flowpilot/assets/flowpilot_router_route_artifacts_architecture_route_checks.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "monitor_route_artifact_architecture_child_contracts",
    },
    "flowpilot_router_route_artifacts_architecture_product": {
        "split_status": "completed_split",
        "split_reason": "product_architecture_intent_and_pm_decision_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_route_artifacts_architecture_product_core.py",
            "skills/flowpilot/assets/flowpilot_router_route_artifacts_architecture_product_intent.py",
            "skills/flowpilot/assets/flowpilot_router_route_artifacts_architecture_product_decisions.py",
        ),
        "peer_safety_status": "claimed_by_split_flowpilot_hff_structure_surfaces",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "monitor_route_artifact_product_child_contracts",
    },
    "flowpilot_router_route_artifacts_nodes": {
        "split_status": "completed_split",
        "split_reason": "node_acceptance_parent_replay_and_delegate_validation_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_route_artifacts_nodes_acceptance.py",
            "skills/flowpilot/assets/flowpilot_router_route_artifacts_nodes_parent.py",
            "skills/flowpilot/assets/flowpilot_router_route_artifacts_nodes_delegates.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "monitor_route_artifact_node_child_contracts",
    },
    "flowpilot_router_route_artifacts_planning": {
        "split_status": "completed_split",
        "split_reason": "planning_contract_capability_and_resume_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_route_artifacts_planning_contract.py",
            "skills/flowpilot/assets/flowpilot_router_route_artifacts_planning_capabilities.py",
            "skills/flowpilot/assets/flowpilot_router_route_artifacts_planning_resume.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "monitor_route_artifact_planning_child_contracts",
    },
    "flowpilot_router_route_frontier_context": {
        "split_status": "completed_split",
        "split_reason": "route_frontier_context_memory_card_and_draft_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_route_frontier_context_memory.py",
            "skills/flowpilot/assets/flowpilot_router_route_frontier_context_cards.py",
            "skills/flowpilot/assets/flowpilot_router_route_frontier_context_drafts.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "runtime_route_frontier_context_helper",
        "recommended_next_action": "monitor_route_frontier_context_child_contracts",
    },
    "flowpilot_router_route_frontier_policy": {
        "split_status": "completed_split",
        "split_reason": "route_frontier_policy_registry_topology_and_completion_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_route_frontier_policy_registry.py",
            "skills/flowpilot/assets/flowpilot_router_route_frontier_policy_topology.py",
            "skills/flowpilot/assets/flowpilot_router_route_frontier_policy_completion.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "runtime_route_frontier_policy_helper",
        "recommended_next_action": "monitor_route_frontier_policy_child_contracts",
    },
    "flowpilot_router_route_frontier_policy_completion": {
        "split_status": "completed_split",
        "split_reason": "route_frontier_completion_authority_context_and_ledger_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_route_frontier_policy_completion_authority.py",
            "skills/flowpilot/assets/flowpilot_router_route_frontier_policy_completion_context.py",
            "skills/flowpilot/assets/flowpilot_router_route_frontier_policy_completion_ledger.py",
        ),
        "peer_safety_status": "claimed_by_split_route_frontier_policy_completion",
        "safe_split_class": "runtime_route_frontier_policy_completion_helper",
        "recommended_next_action": "monitor_route_frontier_policy_completion_child_contracts",
    },
    "flowpilot_router_route_frontier_status": {
        "split_status": "completed_split",
        "split_reason": "route_frontier_status_catalog_summary_and_view_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_route_frontier_status_catalog.py",
            "skills/flowpilot/assets/flowpilot_router_route_frontier_status_summary.py",
            "skills/flowpilot/assets/flowpilot_router_route_frontier_status_views.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "runtime_route_frontier_status_helper",
        "recommended_next_action": "monitor_route_frontier_status_child_contracts",
    },
    "flowpilot_router_route_frontier_views": {
        "split_status": "completed_split",
        "split_reason": "route_frontier_nodes_memory_paths_and_display_plan_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_route_frontier_nodes.py",
            "skills/flowpilot/assets/flowpilot_router_route_frontier_memory_paths.py",
            "skills/flowpilot/assets/flowpilot_router_route_frontier_display_plan.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "runtime_route_frontier_view_helper",
        "recommended_next_action": "monitor_route_frontier_view_child_contracts",
    },
    "flowpilot_router_self_interrogation": {
        "split_status": "completed_split",
        "split_reason": "self_interrogation_suggestion_record_and_proof_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_self_interrogation_suggestions.py",
            "skills/flowpilot/assets/flowpilot_router_self_interrogation_records.py",
            "skills/flowpilot/assets/flowpilot_router_self_interrogation_records_requirements.py",
            "skills/flowpilot/assets/flowpilot_router_self_interrogation_proofs.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "runtime_self_interrogation_helper",
        "recommended_next_action": "monitor_self_interrogation_child_contracts",
    },
    "flowpilot_router_system_cards_delivery": {
        "split_status": "completed_split",
        "split_reason": "system_card_single_and_bundle_delivery_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_system_cards_delivery_single.py",
            "skills/flowpilot/assets/flowpilot_router_system_cards_delivery_bundle.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "system_card_delivery_helper",
        "recommended_next_action": "monitor_system_card_delivery_child_contracts",
    },
    "flowpilot_router_system_cards_selection": {
        "split_status": "completed_split",
        "split_reason": "system_card_token_next_bundle_and_reconcile_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_system_cards_selection_tokens.py",
            "skills/flowpilot/assets/flowpilot_router_system_cards_selection_next.py",
            "skills/flowpilot/assets/flowpilot_router_system_cards_selection_bundle.py",
            "skills/flowpilot/assets/flowpilot_router_system_cards_selection_reconcile.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "system_card_selection_helper",
        "recommended_next_action": "monitor_system_card_selection_child_contracts",
    },
    "flowpilot_router_work_packets_next_actions": {
        "split_status": "completed_split",
        "split_reason": "role_agent_research_and_result_reconciliation_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_work_packets_role_agents.py",
            "skills/flowpilot/assets/flowpilot_router_work_packets_research_next.py",
            "skills/flowpilot/assets/flowpilot_router_work_packets_result_reconciliation.py",
        ),
        "peer_safety_status": "claimed_by_split_flowpilot_hff_structure_surfaces",
        "safe_split_class": "runtime_work_packet_next_action_helper",
        "recommended_next_action": "monitor_work_packet_next_action_child_contracts",
    },
    "flowpilot_router_work_packets_pm_role_lifecycle": {
        "split_status": "completed_split",
        "split_reason": "pm_role_work_index_flowguard_operator_lifecycle_and_contract_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_work_packets_pm_role_lifecycle_index.py",
            "skills/flowpilot/assets/flowpilot_router_work_packets_pm_role_lifecycle_flowguard_operator.py",
            "skills/flowpilot/assets/flowpilot_router_work_packets_pm_role_lifecycle_contracts.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "runtime_pm_role_work_helper",
        "recommended_next_action": "monitor_pm_role_work_lifecycle_child_contracts",
    },
    "flowpilot_router_work_packets_pm_role_writes": {
        "split_status": "completed_split",
        "split_reason": "pm_role_work_request_result_and_decision_writers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_work_packets_pm_role_writes_request.py",
            "skills/flowpilot/assets/flowpilot_router_work_packets_pm_role_writes_results.py",
            "skills/flowpilot/assets/flowpilot_router_work_packets_pm_role_writes_decisions.py",
            "skills/flowpilot/assets/flowpilot_router_work_packets_pm_role_writes_decisions_formal_gate.py",
            "skills/flowpilot/assets/flowpilot_router_work_packets_pm_role_writes_decisions_package_disposition.py",
            "skills/flowpilot/assets/flowpilot_router_work_packets_pm_role_writes_decisions_packet_outcomes.py",
            "skills/flowpilot/assets/flowpilot_router_work_packets_pm_role_writes_decisions_role_result.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "runtime_pm_role_work_helper",
        "recommended_next_action": "monitor_pm_role_work_writer_child_contracts",
    },
    "flowpilot_user_flow_diagram": {
        "split_status": "completed_split",
        "split_reason": "route_sign_generation_and_cli_entrypoint_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_user_flow_diagram_generate.py",
            "skills/flowpilot/assets/flowpilot_user_flow_diagram_cli.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "route_sign_facade",
        "recommended_next_action": "monitor_route_sign_generate_and_cli_contracts",
    },
    "flowpilot_runtime": {
        "split_status": "completed_split",
        "split_reason": "unified_runtime_cli_argument_parsing_command_execution_and_dispatch_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_runtime_args.py",
            "skills/flowpilot/assets/flowpilot_runtime_command_dispatch.py",
            "skills/flowpilot/assets/flowpilot_runtime_commands.py",
            "skills/flowpilot/assets/flowpilot_runtime_role_output_commands.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "runtime_cli_facade",
        "recommended_next_action": "monitor_unified_runtime_cli_child_contracts",
    },
    "flowpilot_router_startup_bootloader": {
        "split_status": "completed_split",
        "split_reason": "startup_bootloader_progress_state_daemon_and_action_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_startup_bootloader_progress.py",
            "skills/flowpilot/assets/flowpilot_router_startup_bootloader_state.py",
            "skills/flowpilot/assets/flowpilot_router_startup_bootloader_daemon.py",
            "skills/flowpilot/assets/flowpilot_router_startup_bootloader_actions.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "monitor_startup_bootloader_child_contracts",
    },
    "flowpilot_router_startup_mechanical_boundary": {
        "split_status": "completed_split",
        "split_reason": "startup_mechanical_check_controller_and_audit_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_startup_mechanical_boundary_checks.py",
            "skills/flowpilot/assets/flowpilot_router_startup_mechanical_boundary_controller.py",
            "skills/flowpilot/assets/flowpilot_router_startup_mechanical_boundary_audit.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "monitor_startup_mechanical_audit_child_contracts",
    },
    "flowpilot_router_startup_intake": {
        "split_status": "completed_split",
        "split_reason": "startup_intake_ui_validation_and_materialization_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_startup_intake_ui.py",
            "skills/flowpilot/assets/flowpilot_router_startup_intake_validation.py",
            "skills/flowpilot/assets/flowpilot_router_startup_intake_materialization.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "monitor_startup_intake_child_contracts",
    },
    "flowpilot_router_startup_resume_binding": {
        "split_status": "completed_split",
        "split_reason": "startup_resume_records_reports_and_actions_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_startup_resume_binding_records.py",
            "skills/flowpilot/assets/flowpilot_router_startup_resume_binding_reports.py",
            "skills/flowpilot/assets/flowpilot_router_startup_resume_binding_actions.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "monitor_startup_resume_binding_child_contracts",
    },
    "flowpilot_router_startup_role_transactions": {
        "split_status": "completed_split",
        "split_reason": "startup_role_transaction_core_record_wait_and_replay_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_startup_role_transactions_core.py",
            "skills/flowpilot/assets/flowpilot_router_startup_role_transactions_records.py",
            "skills/flowpilot/assets/flowpilot_router_startup_role_transactions_waits.py",
            "skills/flowpilot/assets/flowpilot_router_startup_role_transactions_replay.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "monitor_startup_role_transaction_child_contracts",
    },
    "packet_control_plane_model_invariants": {
        "split_status": "completed_split",
        "split_reason": "packet_control_plane_invariant_families_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/packet_control_plane_model_invariants_origin.py",
            "skills/flowpilot/assets/packet_control_plane_model_invariants_handoff.py",
            "skills/flowpilot/assets/packet_control_plane_model_invariants_dispatch.py",
            "skills/flowpilot/assets/packet_control_plane_model_invariants_resume.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "model_invariant_registry",
        "recommended_next_action": "monitor_packet_control_plane_invariant_order_contract",
    },
    "packet_runtime_active_holder": {
        "split_status": "completed_split",
        "split_reason": "active_holder_core_lease_events_and_results_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/packet_runtime_active_holder_core.py",
            "skills/flowpilot/assets/packet_runtime_active_holder_lease.py",
            "skills/flowpilot/assets/packet_runtime_active_holder_events.py",
            "skills/flowpilot/assets/packet_runtime_active_holder_results.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "monitor_packet_active_holder_child_contracts",
    },
    "packet_runtime_cli": {
        "split_status": "completed_split",
        "split_reason": "packet_runtime_cli_args_and_command_dispatch_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/packet_runtime_cli_args.py",
            "skills/flowpilot/assets/packet_runtime_cli_main.py",
        ),
        "peer_safety_status": "claimed_by_finish_flowpilot_structure_debt",
        "safe_split_class": "cli_facade",
        "recommended_next_action": "monitor_packet_cli_child_contracts",
    },
    "flowpilot_controller_break_glass": {
        "split_status": "completed_split",
        "split_reason": "core_data_path_validation_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_controller_break_glass_core.py",
        ),
        "peer_safety_status": "claimed_by_converge_new_only_maintenance_cleanup",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "monitor_break_glass_core_child_contracts",
    },
    "flowpilot_router_controller_scheduler_standby": {
        "split_status": "completed_split",
        "split_reason": "continuous_standby_task_payload_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_controller_scheduler_standby_task.py",
        ),
        "peer_safety_status": "claimed_by_converge_new_only_maintenance_cleanup",
        "safe_split_class": "runtime_scheduler_wait_helper",
        "recommended_next_action": "monitor_standby_task_child_contracts",
    },
    "flowpilot_router_controller_wait_audit": {
        "split_status": "completed_split",
        "split_reason": "controller_wait_receipt_metadata_scanners_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_controller_wait_audit_scanners.py",
        ),
        "peer_safety_status": "claimed_by_converge_new_only_maintenance_cleanup",
        "safe_split_class": "runtime_scheduler_wait_helper",
        "recommended_next_action": "monitor_wait_audit_scanner_child_contracts",
    },
    "flowpilot_router_daemon_runtime": {
        "split_status": "completed_split",
        "split_reason": "run_root_resolution_and_daemon_lock_lifecycle_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/flowpilot_router_daemon_runtime_lock.py",
        ),
        "peer_safety_status": "claimed_by_converge_new_only_maintenance_cleanup",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "monitor_daemon_lock_child_contracts",
    },
    "role_output_runtime_envelopes": {
        "split_status": "completed_split",
        "split_reason": "runtime_receipt_validation_and_envelope_lookup_helpers_extracted",
        "completed_split_paths": (
            "skills/flowpilot/assets/role_output_runtime_envelope_receipts.py",
        ),
        "peer_safety_status": "claimed_by_converge_new_only_maintenance_cleanup",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "monitor_role_output_receipt_child_contracts",
    },
}

RECENT_OWNER_MODULE_POLISH_COMMITS = ("bd83ae52", "435292eb", "c874e8b3")

OWNER_STRUCTURE_SPLIT_LINE_THRESHOLD = 450
FACADE_STRUCTURE_SPLIT_LINE_THRESHOLD = 320
SCRIPT_STRUCTURE_SPLIT_LINE_THRESHOLD = 650

BACKGROUND_ARTIFACT_ROOTS = (
    ROOT / "tmp" / "flowguard_background",
    ROOT / "tmp" / "test_background",
)

BACKGROUND_COMMAND_ARTIFACT_ALIASES = {
    "meta_full": ("meta_full", "run_meta_checks"),
    "capability_full": ("capability_full", "run_capability_checks"),
}

STALE_EVIDENCE_STATUSES = {
    "failed",
    "incomplete",
    "missing_final_artifacts",
    "progress_only",
    "release_local_only",
    "running",
    "stale",
}

DIAGNOSTIC_GAP_CODES = (
    "missing_model",
    "missing_code",
    "missing_test",
    "extra_code",
    "internal_only_test",
    "stale_evidence",
    "needs_structure_split",
)

DIAGNOSTIC_REPAIR_TYPES = {
    "missing_model": "add_model_binding",
    "missing_code": "restore_code_reference",
    "missing_test": "add_external_contract_test",
    "extra_code": "classify_or_remove_code",
    "internal_only_test": "upgrade_to_external_contract_test",
    "stale_evidence": "rerun_or_reclassify_evidence",
    "needs_structure_split": "split_structure",
}

DIAGNOSTIC_SEVERITY_SCORE = {
    "critical": 0,
    "high": 10,
    "medium": 20,
    "low": 30,
}


def _repo_path(path: str) -> str:
    return path.replace("\\", "/")


def _evidence(
    evidence_id: str,
    *,
    test_name: str,
    path: str,
    command: str,
    test_kind: str,
    covers: Sequence[str],
    code_contracts: Sequence[str] = (),
    result_status: str = PASSED,
    evidence_current: bool = True,
    stale_reasons: Sequence[str] = (),
    overclaims_model_confidence: bool = False,
    evidence_role: str = "primary",
    evidence_target_id: str = "",
) -> TestEvidence:
    repo_path = _repo_path(path)
    resolved = ROOT / repo_path
    reasons = tuple(stale_reasons)
    if evidence_current and not resolved.exists():
        reasons = reasons + (f"referenced path does not exist: {repo_path}",)
    proof = None
    reuse_ticket = None
    proof_gaps: tuple[str, ...] = ()
    requested_pass = result_status == PASSED and evidence_current
    if requested_pass and resolved.exists() and not _DECLARATION_ONLY:
        bundle = _EXECUTION_EVIDENCE_BUNDLE or {}
        owners = bundle.get("owners")
        owner_ids = []
        if isinstance(owners, dict):
            for owner_id, owner_row in owners.items():
                identity = (
                    owner_row.get("identity")
                    if isinstance(owner_row, dict)
                    else None
                )
                covered_evidence_ids = (
                    identity.get("covered_evidence_ids")
                    if isinstance(identity, dict)
                    else None
                )
                if (
                    isinstance(covered_evidence_ids, list)
                    and evidence_id in covered_evidence_ids
                ):
                    owner_ids.append(str(owner_id))
        if len(owner_ids) == 1:
            proof, reuse_ticket, proof_gaps = derived_owner_proof(
                bundle,
                owner_id=owner_ids[0],
                covered_obligation_ids=tuple(covers),
                projected_evidence_id=evidence_id,
            )
        elif not owner_ids:
            proof_gaps = ("test_evidence_owner_binding_missing",)
        else:
            proof_gaps = ("test_evidence_owner_binding_ambiguous",)
    current = requested_pass and resolved.exists() and proof is not None and reuse_ticket is not None and not proof_gaps
    effective_status = PASSED if current else (result_status if result_status != PASSED else "not_run")
    if requested_pass and not current:
        if _DECLARATION_ONLY:
            reasons = reasons + ("declaration-only row has no current execution proof",)
        else:
            reasons = reasons + tuple(f"execution proof gap: {code}" for code in proof_gaps or ("proof_bundle_missing",))
    return TestEvidence(
        evidence_id=evidence_id,
        test_name=test_name,
        path=repo_path,
        command=command,
        result_status=effective_status,
        evidence_current=current,
        test_kind=test_kind,
        covered_obligations=tuple(covers),
        covered_code_contracts=tuple(code_contracts),
        proof_artifact=proof,
        result_reused=proof is not None,
        reuse_ticket=reuse_ticket,
        stale_reasons=reasons,
        overclaims_model_confidence=overclaims_model_confidence,
        evidence_role=evidence_role,
        evidence_target_id=evidence_target_id,
    )


def _obligation(
    obligation_id: str,
    *,
    obligation_type: str,
    description: str,
    required_test_kinds: Sequence[str],
    risk_level: str = "high",
    allow_shared_evidence: bool = False,
    allow_shared_implementation: bool = False,
) -> ModelObligation:
    return ModelObligation(
        obligation_id=obligation_id,
        obligation_type=obligation_type,
        description=description,
        required=True,
        required_test_kinds=tuple(required_test_kinds),
        risk_level=risk_level,
        allow_shared_evidence=allow_shared_evidence,
        allow_shared_implementation=allow_shared_implementation,
    )


def _plan_entry(
    family: str,
    plan: ModelTestAlignmentPlan,
    *,
    model_checks: Sequence[str],
    coverage_boundary: str,
) -> dict[str, Any]:
    return {
        "family": family,
        "plan": plan,
        "model_checks": list(model_checks),
        "coverage_boundary": coverage_boundary,
    }


def _contract(
    code_contract_id: str,
    *,
    path: str,
    symbol: str,
    implements: Sequence[str],
    external_inputs: Sequence[str] = (),
    external_outputs: Sequence[str] = ("return",),
    state_reads: Sequence[str] = (),
    state_writes: Sequence[str] = (),
    side_effects: Sequence[str] = (),
    error_paths: Sequence[str] = (),
    role: str = "owner",
    behavior_plane: str = "",
    business_intent_id: str = "",
    behavior_commitment_id: str = "",
    primary_path_id: str = "",
) -> CodeContract:
    return CodeContract(
        code_contract_id=code_contract_id,
        path=_repo_path(path),
        symbol=symbol,
        implements_obligations=tuple(implements),
        external_inputs=tuple(external_inputs),
        external_outputs=tuple(external_outputs),
        state_reads=tuple(state_reads),
        state_writes=tuple(state_writes),
        side_effects=tuple(side_effects),
        error_paths=tuple(error_paths),
        role=role,
        behavior_plane=behavior_plane,
        business_intent_id=business_intent_id,
        behavior_commitment_id=behavior_commitment_id,
        primary_path_id=primary_path_id,
    )


def _finding_counts(findings: Sequence[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        severity = str(finding.get("severity", "unknown"))
        counts[severity] = counts.get(severity, 0) + 1
    return counts


__all__ = [name for name in globals() if not name.startswith("__")]
