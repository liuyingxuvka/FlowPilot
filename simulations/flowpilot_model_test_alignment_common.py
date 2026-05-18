"""Common declarations for FlowPilot model-test alignment diagnostics."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from flowguard import CodeContract, ModelObligation, ModelTestAlignmentPlan, TestEvidence

ROOT = Path(__file__).resolve().parents[1]

HAPPY = "happy_path"
FAILURE = "failure_path"
EDGE = "edge_path"
NEGATIVE = "negative_path"
REPLAY = "replay"
PASSED = "passed"
RUNNING = "running"

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
    "asset:packet_runtime",
    "asset:flowpilot_router_controller_scheduler_receipts",
    "asset:flowpilot_router_work_packets_pm_role",
    "asset:flowpilot_router_terminal_ledger",
    "asset:flowpilot_router_facade_export_manifest_controller_events",
    "asset:flowpilot_router_facade_export_manifest_controller_lifecycle",
    "asset:flowpilot_router_facade_export_manifest_controller_repair",
    "asset:flowpilot_router_facade_export_manifest_controller_scheduler",
    "asset:flowpilot_router_protocol_external_events_material",
    "asset:flowpilot_router_protocol_external_events_route",
    "asset:flowpilot_router_protocol_external_events_startup",
    "asset:flowpilot_router_protocol_external_events_terminal",
}

SCRIPT_CLI_EXTERNAL_CONTRACT_STEMS = {
    "audit_local_install_sync",
    "check_install",
    "check_public_release",
    "flowpilot_lifecycle",
    "flowpilot_outputs",
    "flowpilot_packets",
    "install_flowpilot",
    "run_test_tier",
}

ASSET_MODEL_BINDING_PREFIXES = {
    "flowpilot_router_": "router_runtime_architecture",
    "packet_runtime_": "packet_runtime_architecture",
    "role_output_runtime_": "role_output_runtime_architecture",
}

ASSET_MODEL_BINDING_STEMS = {
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
    "flowpilot_outputs": "role_output_cli",
    "flowpilot_packets": "packet_runtime_cli",
    "flowpilot_paths": "runtime_path_cli",
    "flowpilot_runtime_retention": "runtime_retention_cli",
    "install_flowpilot": "local_install_sync",
    "run_flowguard_coverage_sweep": "coverage_sweep_runner",
    "run_test_tier": "test_tier_runner",
    "smoke_autopilot": "smoke_fast_validation",
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
    "flowpilot_router_work_packets_current_node": {
        "split_status": "deferred_split",
        "split_reason": "line_threshold_exceeded | mixed_owner_families",
        "deferred_split_reason": "fresh_owner_module_polish | state_ordering_sensitive | needs_structuremesh_target",
        "peer_safety_status": "do_not_edit_without_claim",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "claim_and_model_before_split",
    },
    "flowpilot_router_card_returns": {
        "split_status": "deferred_split",
        "split_reason": "line_threshold_exceeded | mixed_owner_families",
        "deferred_split_reason": "fresh_owner_module_polish | state_ordering_sensitive | needs_structuremesh_target",
        "peer_safety_status": "do_not_edit_without_claim",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "claim_and_model_before_split",
    },
    "role_output_runtime_schema": {
        "split_status": "deferred_split",
        "split_reason": "line_threshold_exceeded | mixed_owner_families",
        "deferred_split_reason": "fresh_owner_module_polish | state_ordering_sensitive | needs_structuremesh_target",
        "peer_safety_status": "do_not_edit_without_claim",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "claim_and_model_before_split",
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
        "split_status": "deferred_split",
        "split_reason": "line_threshold_exceeded | declarative_families_mixed",
        "deferred_split_reason": "fresh_owner_module_polish",
        "peer_safety_status": "do_not_edit_without_claim",
        "safe_split_class": "declarative_protocol_table",
        "recommended_next_action": "immediate_declarative_split_after_claim",
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
    "flowpilot_router_route_artifacts_architecture": {
        "split_status": "deferred_split",
        "split_reason": "line_threshold_exceeded | route_artifact_families_mixed",
        "deferred_split_reason": "fresh_owner_module_polish | state_ordering_sensitive | needs_structuremesh_target",
        "peer_safety_status": "do_not_edit_without_claim",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "claim_and_model_before_split",
    },
    "flowpilot_router_route_artifacts_nodes": {
        "split_status": "deferred_split",
        "split_reason": "line_threshold_exceeded | route_artifact_families_mixed",
        "deferred_split_reason": "fresh_owner_module_polish | state_ordering_sensitive | needs_structuremesh_target",
        "peer_safety_status": "do_not_edit_without_claim",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "claim_and_model_before_split",
    },
    "flowpilot_router_route_artifacts_planning": {
        "split_status": "deferred_split",
        "split_reason": "line_threshold_exceeded | route_artifact_families_mixed",
        "deferred_split_reason": "fresh_owner_module_polish | state_ordering_sensitive | needs_structuremesh_target",
        "peer_safety_status": "do_not_edit_without_claim",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "claim_and_model_before_split",
    },
    "flowpilot_router_route_frontier_policy": {
        "split_status": "deferred_split",
        "split_reason": "line_threshold_exceeded | route_frontier_families_mixed",
        "deferred_split_reason": "fresh_owner_module_polish | state_ordering_sensitive | needs_structuremesh_target",
        "peer_safety_status": "do_not_edit_without_claim",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "claim_and_model_before_split",
    },
    "flowpilot_router_route_frontier_status": {
        "split_status": "deferred_split",
        "split_reason": "line_threshold_exceeded | route_frontier_families_mixed",
        "deferred_split_reason": "fresh_owner_module_polish | state_ordering_sensitive | needs_structuremesh_target",
        "peer_safety_status": "do_not_edit_without_claim",
        "safe_split_class": "stateful_runtime_flow",
        "recommended_next_action": "claim_and_model_before_split",
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
    "meta_legacy_full": ("meta_legacy_full", "run_meta_checks"),
    "capability_legacy_full": ("capability_legacy_full", "run_capability_checks"),
}

LEGACY_FULL_LAYERED_PARENT = {
    "meta_legacy_full": "meta",
    "capability_legacy_full": "capability",
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
) -> TestEvidence:
    repo_path = _repo_path(path)
    resolved = ROOT / repo_path
    current = evidence_current and resolved.exists()
    reasons = tuple(stale_reasons)
    if evidence_current and not resolved.exists():
        reasons = reasons + (f"referenced path does not exist: {repo_path}",)
    return TestEvidence(
        evidence_id=evidence_id,
        test_name=test_name,
        path=repo_path,
        command=command,
        result_status=result_status,
        evidence_current=current,
        test_kind=test_kind,
        covered_obligations=tuple(covers),
        covered_code_contracts=tuple(code_contracts),
        stale_reasons=reasons,
        overclaims_model_confidence=overclaims_model_confidence,
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
    side_effects: Sequence[str] = (),
) -> CodeContract:
    return CodeContract(
        code_contract_id=code_contract_id,
        path=_repo_path(path),
        symbol=symbol,
        implements_obligations=tuple(implements),
        external_inputs=tuple(external_inputs),
        external_outputs=tuple(external_outputs),
        side_effects=tuple(side_effects),
    )


def _finding_counts(findings: Sequence[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        severity = str(finding.get("severity", "unknown"))
        counts[severity] = counts.get(severity, 0) + 1
    return counts


__all__ = [name for name in globals() if not name.startswith("__")]
