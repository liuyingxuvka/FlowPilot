"""Run FlowGuard Model-Test Alignment checks for major FlowPilot families.

This runner is intentionally read-only. It does not execute the referenced
tests or long parent FlowGuard checks; it reviews declared model obligations
against ordinary test evidence by using FlowGuard's Model-Test Alignment API.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Sequence

from flowguard import (
    CodeContract,
    ModelObligation,
    ModelTestAlignmentPlan,
    TestEvidence,
    audit_python_code_contracts,
    audit_python_test_assertions,
    review_python_contract_source_audit,
    review_model_test_alignment,
)


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
        "split_status": "deferred_split",
        "split_reason": "line_threshold_exceeded | declarative_families_mixed",
        "deferred_split_reason": "fresh_owner_module_polish",
        "peer_safety_status": "do_not_edit_without_claim",
        "safe_split_class": "declarative_protocol_table",
        "recommended_next_action": "immediate_declarative_split_after_claim",
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
        "split_status": "deferred_split",
        "split_reason": "line_threshold_exceeded | declarative_families_mixed",
        "deferred_split_reason": "fresh_owner_module_polish",
        "peer_safety_status": "do_not_edit_without_claim",
        "safe_split_class": "declarative_manifest",
        "recommended_next_action": "immediate_declarative_split_after_claim",
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


def build_alignment_plan_entries() -> list[dict[str, Any]]:
    """Build major FlowPilot model/test-family alignment plans."""

    startup = ModelTestAlignmentPlan(
        model_id="startup",
        obligations=(
            _obligation(
                "startup.questions.pause_before_work",
                obligation_type="contract",
                description="Startup asks the three questions, waits for answers, and blocks banner/controller work until the answer boundary is satisfied.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "startup.run_isolation_and_activation",
                obligation_type="scenario",
                description="Startup creates prompt-isolated current-run state and requires reviewer facts plus PM approval before work beyond startup.",
                required_test_kinds=(HAPPY, FAILURE),
            ),
        ),
        test_evidence=(
            _evidence(
                "startup.happy.prompt_isolated_run",
                test_name="test_startup_sequence_creates_prompt_isolated_run",
                path="tests/router_runtime/startup_bootstrap.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_startup_daemon",
                test_kind=HAPPY,
                covers=("startup.run_isolation_and_activation",),
            ),
            _evidence(
                "startup.negative.waits_for_answers",
                test_name="test_startup_waits_for_answers_before_banner_or_controller",
                path="tests/router_runtime/startup_bootstrap.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_startup_daemon",
                test_kind=NEGATIVE,
                covers=("startup.questions.pause_before_work",),
            ),
            _evidence(
                "startup.happy.answer_boundary",
                test_name="test_record_startup_answers_accepts_ai_interpretation_with_reviewer_receipt",
                path="tests/router_runtime/startup_bootstrap.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_startup_daemon",
                test_kind=HAPPY,
                covers=("startup.questions.pause_before_work",),
            ),
            _evidence(
                "startup.failure.activation_requires_reviewer",
                test_name="test_startup_activation_requires_reviewer_facts_before_work",
                path="tests/router_runtime/startup_bootstrap.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_startup_daemon",
                test_kind=FAILURE,
                covers=("startup.run_isolation_and_activation",),
            ),
        ),
    )

    packet_card_ack = ModelTestAlignmentPlan(
        model_id="packet_card_ack",
        obligations=(
            _obligation(
                "packet.physical_body_boundary",
                obligation_type="contract",
                description="Packet envelopes, bodies, result files, hashes, and recipient reads stay physically separated from Controller relay text.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "card.ack_identity_and_bundle",
                obligation_type="hazard",
                description="Card and bundle ACKs require correct role, token, receipt, hash, and per-card completion before advancing.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "ack.return_wait_preconsumption",
                obligation_type="transition",
                description="Router preconsumes valid ACK/return events and blocks incomplete or invalid pre-ACK reports without advancing stale waits.",
                required_test_kinds=(EDGE, FAILURE),
            ),
            _obligation(
                "packet_control_plane.facade_split_integrity",
                obligation_type="contract",
                description="Packet control-plane model keeps its facade import path while state, transition, and invariant owners remain executable.",
                required_test_kinds=(HAPPY,),
            ),
        ),
        test_evidence=(
            _evidence(
                "packet.happy.physical_files",
                test_name="test_pm_issue_writes_physical_envelope_body_and_ledger",
                path="tests/test_flowpilot_packet_runtime.py",
                command="python -m unittest tests.test_flowpilot_packet_runtime",
                test_kind=HAPPY,
                covers=("packet.physical_body_boundary",),
            ),
            _evidence(
                "packet.negative.controller_body_exclusion",
                test_name="test_controller_handoff_contains_envelope_only_not_body_content",
                path="tests/test_flowpilot_packet_runtime.py",
                command="python -m unittest tests.test_flowpilot_packet_runtime",
                test_kind=NEGATIVE,
                covers=("packet.physical_body_boundary",),
            ),
            _evidence(
                "card.happy.card_ack",
                test_name="test_card_runtime_opens_card_and_submits_ack",
                path="tests/test_flowpilot_card_runtime.py",
                command="python -m pytest tests/test_flowpilot_card_runtime.py",
                test_kind=HAPPY,
                covers=("card.ack_identity_and_bundle",),
            ),
            _evidence(
                "card.negative.wrong_role_ack",
                test_name="test_card_runtime_rejects_wrong_role_and_ack_without_receipt",
                path="tests/test_flowpilot_card_runtime.py",
                command="python -m pytest tests/test_flowpilot_card_runtime.py",
                test_kind=NEGATIVE,
                covers=("card.ack_identity_and_bundle",),
            ),
            _evidence(
                "ack.edge.preconsume_valid_ack",
                test_name="test_record_external_event_preconsumes_valid_card_ack_before_blocking",
                path="tests/router_runtime/ack_return.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_ack_return",
                test_kind=EDGE,
                covers=("ack.return_wait_preconsumption",),
            ),
            _evidence(
                "ack.failure.incomplete_bundle",
                test_name="test_record_external_event_does_not_preconsume_incomplete_bundle_ack",
                path="tests/router_runtime/ack_return.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_ack_return",
                test_kind=FAILURE,
                covers=("ack.return_wait_preconsumption",),
            ),
            _evidence(
                "packet_control_plane.happy.split_runner",
                test_name="run_packet_control_plane_checks",
                path="skills/flowpilot/assets/run_packet_control_plane_checks.py",
                command="python skills/flowpilot/assets/run_packet_control_plane_checks.py",
                test_kind=HAPPY,
                covers=("packet_control_plane.facade_split_integrity",),
            ),
        ),
    )

    route_mutation = ModelTestAlignmentPlan(
        model_id="route_mutation",
        obligations=(
            _obligation(
                "route_mutation.topology_and_recheck",
                obligation_type="contract",
                description="Route mutation declares topology, affected nodes, process/product rechecks, and old packet supersession before activation.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "route_mutation.sibling_replacement_stales_old_evidence",
                obligation_type="hazard",
                description="Sibling branch replacement marks old sibling evidence stale and projects replacement/replay scope in the route display.",
                required_test_kinds=(NEGATIVE, EDGE),
            ),
        ),
        test_evidence=(
            _evidence(
                "route_mutation.happy.contract_fixture",
                test_name="TestRouteMutationChildContractFixture",
                path="tests/flowpilot_route_mutation_contracts.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_route_mutation",
                test_kind=HAPPY,
                covers=("route_mutation.topology_and_recheck",),
            ),
            _evidence(
                "route_mutation.negative.required_preconditions",
                test_name="test_route_mutation_and_final_ledger_have_required_preconditions",
                path="tests/router_runtime/route_mutation_preconditions.py",
                command="python -m unittest tests.router_runtime.route_mutation_preconditions.RouteMutationPreconditionRuntimeTests.test_route_mutation_and_final_ledger_have_required_preconditions",
                test_kind=NEGATIVE,
                covers=("route_mutation.topology_and_recheck",),
            ),
            _evidence(
                "route_mutation.edge.sibling_replacement_display",
                test_name="test_sibling_branch_replacement_draws_replacement_and_replay_scope",
                path="tests/test_flowpilot_user_flow_diagram.py",
                command="python -m unittest tests.test_flowpilot_user_flow_diagram.FlowPilotUserFlowDiagramTests.test_sibling_branch_replacement_draws_replacement_and_replay_scope",
                test_kind=EDGE,
                covers=("route_mutation.sibling_replacement_stales_old_evidence",),
            ),
            _evidence(
                "route_mutation.negative.old_sibling_proof",
                test_name="test_route_mutation_sibling_branch_replacement_blocks_old_sibling_proof",
                path="tests/router_runtime/route_mutation_sibling_replacement.py",
                command="python -m unittest tests.router_runtime.route_mutation_sibling_replacement.RouteMutationSiblingReplacementRuntimeTests.test_route_mutation_sibling_branch_replacement_blocks_old_sibling_proof",
                test_kind=NEGATIVE,
                covers=("route_mutation.sibling_replacement_stales_old_evidence",),
            ),
        ),
    )

    terminal_closure_resume = ModelTestAlignmentPlan(
        model_id="terminal_closure_resume",
        obligations=(
            _obligation(
                "terminal.final_ledger_and_backward_replay",
                obligation_type="invariant",
                description="Terminal completion requires a clean PM-built final ledger, delivered-product backward replay, and PM completion approval.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "closure.dirty_ledgers_block_completion",
                obligation_type="hazard",
                description="Closure blocks dirty defect, PM-suggestion, role-memory, quarantine, or source-of-truth state after terminal replay.",
                required_test_kinds=(FAILURE,),
            ),
            _obligation(
                "resume.current_run_reentry",
                obligation_type="transition",
                description="Resume re-entry loads current-run state, frontier, packet ledger, daemon/owner state, role memory, and recovery evidence before PM work.",
                required_test_kinds=(HAPPY, FAILURE),
            ),
        ),
        test_evidence=(
            _evidence(
                "terminal.happy.replay_segments",
                test_name="test_terminal_replay_requires_reviewed_segments_and_pm_segment_decisions",
                path="tests/router_runtime/terminal.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_terminal",
                test_kind=HAPPY,
                covers=("terminal.final_ledger_and_backward_replay",),
            ),
            _evidence(
                "terminal.negative.final_ledger_sources",
                test_name="test_final_ledger_rejects_missing_source_of_truth_entries_and_contract_replay",
                path="tests/router_runtime/terminal.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_terminal",
                test_kind=NEGATIVE,
                covers=("terminal.final_ledger_and_backward_replay",),
            ),
            _evidence(
                "closure.failure.dirty_defect_ledger",
                test_name="test_terminal_closure_blocks_dirty_defect_ledger_after_terminal_replay",
                path="tests/router_runtime/closure.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_closure",
                test_kind=FAILURE,
                covers=("closure.dirty_ledgers_block_completion",),
            ),
            _evidence(
                "resume.happy.loads_state",
                test_name="test_resume_reentry_loads_state_before_resume_cards",
                path="tests/router_runtime/resume.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_resume",
                test_kind=HAPPY,
                covers=("resume.current_run_reentry",),
            ),
            _evidence(
                "resume.failure.ambiguous_state",
                test_name="test_resume_ambiguous_state_blocks_continue_without_recovery_evidence",
                path="tests/router_runtime/resume.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_resume",
                test_kind=FAILURE,
                covers=("resume.current_run_reentry",),
            ),
        ),
    )

    role_output = ModelTestAlignmentPlan(
        model_id="role_output_contracts",
        obligations=(
            _obligation(
                "role_output.registry_authority",
                obligation_type="contract",
                description="Role outputs are registry-bound, role-authored, authority-checked, and submitted only through current Router waits.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "output_contract.packet_binding",
                obligation_type="contract",
                description="Output contracts are repeated in packet envelope/body/ledger/result and rejected for wrong recipients.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
        ),
        test_evidence=(
            _evidence(
                "role_output.happy.registry_preparable",
                test_name="test_registry_backed_output_types_are_preparable",
                path="tests/test_flowpilot_role_output_runtime.py",
                command="python -m unittest tests.test_flowpilot_role_output_runtime",
                test_kind=HAPPY,
                covers=("role_output.registry_authority",),
            ),
            _evidence(
                "role_output.negative.wrong_role",
                test_name="test_runtime_rejects_wrong_role_and_role_key_agent_id",
                path="tests/test_flowpilot_role_output_runtime.py",
                command="python -m unittest tests.test_flowpilot_role_output_runtime",
                test_kind=NEGATIVE,
                covers=("role_output.registry_authority",),
            ),
            _evidence(
                "output_contract.happy.packet_binding",
                test_name="test_pm_packet_repeats_output_contract_in_envelope_body_ledger_and_result",
                path="tests/test_flowpilot_output_contracts.py",
                command="python -m unittest tests.test_flowpilot_output_contracts",
                test_kind=HAPPY,
                covers=("output_contract.packet_binding",),
            ),
            _evidence(
                "output_contract.negative.wrong_recipient",
                test_name="test_packet_rejects_contract_for_wrong_recipient",
                path="tests/test_flowpilot_output_contracts.py",
                command="python -m unittest tests.test_flowpilot_output_contracts",
                test_kind=NEGATIVE,
                covers=("output_contract.packet_binding",),
            ),
        ),
    )

    router_loop_daemon = ModelTestAlignmentPlan(
        model_id="router_loop_daemon",
        obligations=(
            _obligation(
                "router_loop.packet_result_review_loop",
                obligation_type="transition",
                description="The current-node loop dispatches packets only after direct-dispatch preflight and routes results through PM/reviewer gates.",
                required_test_kinds=(HAPPY, FAILURE),
            ),
            _obligation(
                "daemon.lock_status_and_queue_progress",
                obligation_type="invariant",
                description="The persistent Router daemon owns one run lock, records status, waits on fresh locks, and does not reactivate released locks.",
                required_test_kinds=(HAPPY, EDGE),
            ),
        ),
        test_evidence=(
            _evidence(
                "router_loop.happy.direct_dispatch",
                test_name="test_current_node_packet_relay_uses_router_direct_dispatch",
                path="tests/router_runtime/packets.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_packets",
                test_kind=HAPPY,
                covers=("router_loop.packet_result_review_loop",),
            ),
            _evidence(
                "router_loop.failure.reviewer_audit",
                test_name="test_current_node_completion_requires_reviewer_passed_packet_audit",
                path="tests/router_runtime/packets.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_packets",
                test_kind=FAILURE,
                covers=("router_loop.packet_result_review_loop",),
            ),
            _evidence(
                "daemon.happy.formal_startup",
                test_name="test_formal_startup_starts_router_daemon_before_controller_core",
                path="tests/router_runtime/startup_bootstrap.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_startup_daemon",
                test_kind=HAPPY,
                covers=("daemon.lock_status_and_queue_progress",),
            ),
            _evidence(
                "daemon.edge.fresh_lock_wait",
                test_name="test_router_daemon_waits_on_fresh_scheduler_write_lock_before_error",
                path="tests/router_runtime/startup_daemon.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_startup_daemon",
                test_kind=EDGE,
                covers=("daemon.lock_status_and_queue_progress",),
            ),
        ),
    )

    tiering = ModelTestAlignmentPlan(
        model_id="test_tiering_slow_contracts",
        obligations=(
            _obligation(
                "test_tiering.foreground_fast_scope",
                obligation_type="contract",
                description="Fast/router tiers are scoped, foreground-safe, and exclude release-only, coverage sweep, and legacy full regressions.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "test_tiering.background_artifact_contract",
                obligation_type="hazard",
                description="Background validation needs final out/err/combined/exit/meta artifacts; progress lines alone are not pass evidence.",
                required_test_kinds=(NEGATIVE,),
            ),
            _obligation(
                "slow_test.parent_child_contracts",
                obligation_type="contract",
                description="Slow-test parents declare child owners and I/O contracts and do not replay child internals as parent proof.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
        ),
        test_evidence=(
            _evidence(
                "tiering.happy.fast_scope",
                test_name="test_fast_tier_excludes_release_coverage_and_legacy_full",
                path="tests/test_flowpilot_test_tiers.py",
                command="python -m unittest tests.test_flowpilot_test_tiers",
                test_kind=HAPPY,
                covers=("test_tiering.foreground_fast_scope",),
            ),
            _evidence(
                "tiering.negative.release_exclusion",
                test_name="test_fast_and_router_tiers_do_not_contain_release_only_commands",
                path="tests/test_flowpilot_test_tiers.py",
                command="python -m unittest tests.test_flowpilot_test_tiers",
                test_kind=NEGATIVE,
                covers=("test_tiering.foreground_fast_scope",),
            ),
            _evidence(
                "tiering.negative.progress_only",
                test_name="test_tiering_flowguard_model_rejects_known_bad_hazards",
                path="tests/test_flowpilot_test_tiers.py",
                command="python -m unittest tests.test_flowpilot_test_tiers.FlowPilotTestTierTests.test_tiering_flowguard_model_rejects_known_bad_hazards",
                test_kind=NEGATIVE,
                covers=("test_tiering.background_artifact_contract",),
            ),
            _evidence(
                "slow_contract.happy.valid_contracts",
                test_name="test_slow_test_contract_flowguard_model_rejects_parent_child_hazards",
                path="tests/test_flowpilot_test_tiers.py",
                command="python -m unittest tests.test_flowpilot_test_tiers.FlowPilotTestTierTests.test_slow_test_contract_flowguard_model_rejects_parent_child_hazards",
                test_kind=HAPPY,
                covers=("slow_test.parent_child_contracts",),
            ),
            _evidence(
                "slow_contract.negative.parent_child_hazards",
                test_name="test_slow_test_contract_flowguard_model_rejects_parent_child_hazards",
                path="tests/test_flowpilot_test_tiers.py",
                command="python -m unittest tests.test_flowpilot_test_tiers.FlowPilotTestTierTests.test_slow_test_contract_flowguard_model_rejects_parent_child_hazards",
                test_kind=NEGATIVE,
                covers=("slow_test.parent_child_contracts",),
            ),
        ),
    )

    meta_capability = ModelTestAlignmentPlan(
        model_id="meta_capability_parents",
        obligations=(
            _obligation(
                "meta_parent.thin_default_and_layered_full_boundary",
                obligation_type="contract",
                description="Meta parent routine evidence uses thin-parent proof by default and layered full proof only when explicitly requested.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "capability_parent.proof_reuse_and_fast_boundary",
                obligation_type="contract",
                description="Capability parent evidence rejects stale proof reuse and keeps fast smoke on the non-legacy path.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "parents.abstract_not_ordinary_conformance",
                obligation_type="invariant",
                description="Meta/Capability parent model evidence stays bounded as abstract model-hierarchy confidence, not ordinary production conformance.",
                required_test_kinds=(EDGE,),
            ),
        ),
        test_evidence=(
            _evidence(
                "meta_parent.happy.thin_default",
                test_name="test_default_meta_runner_uses_thin_parent_without_full_graph",
                path="tests/test_flowpilot_thin_parent_checks.py",
                command="python -m unittest tests.test_flowpilot_thin_parent_checks",
                test_kind=HAPPY,
                covers=("meta_parent.thin_default_and_layered_full_boundary",),
            ),
            _evidence(
                "meta_parent.negative.legacy_explicit_only",
                test_name="test_legacy_full_meta_runner_preserves_monolithic_path",
                path="tests/test_flowpilot_thin_parent_checks.py",
                command="python -m unittest tests.test_flowpilot_thin_parent_checks",
                test_kind=NEGATIVE,
                covers=("meta_parent.thin_default_and_layered_full_boundary",),
            ),
            _evidence(
                "capability_parent.happy.proof_reuse_guard",
                test_name="test_capability_result_proof_rejects_stale_reuse",
                path="tests/test_flowguard_result_proof.py",
                command="python -m unittest tests.test_flowguard_result_proof",
                test_kind=HAPPY,
                covers=("capability_parent.proof_reuse_and_fast_boundary",),
            ),
            _evidence(
                "capability_parent.negative.fast_smoke_no_legacy",
                test_name="test_smoke_fast_only_marks_slow_model_checks_fast",
                path="tests/test_flowguard_result_proof.py",
                command="python -m unittest tests.test_flowguard_result_proof",
                test_kind=NEGATIVE,
                covers=("capability_parent.proof_reuse_and_fast_boundary",),
            ),
            _evidence(
                "parents.edge.control_gate_unit_checks",
                test_name="FlowPilotControlGateTests meta/capability invariant checks",
                path="tests/test_flowpilot_control_gates.py",
                command="python -m unittest tests.test_flowpilot_control_gates",
                test_kind=EDGE,
                covers=("parents.abstract_not_ordinary_conformance",),
            ),
        ),
    )

    return [
        _plan_entry(
            "startup",
            startup,
            model_checks=(
                "python simulations/run_flowpilot_startup_control_checks.py",
                "python simulations/run_flowpilot_deterministic_startup_bootstrap_checks.py",
            ),
            coverage_boundary="Startup alignment covers ordinary runtime and unit tests for the startup gate. It does not rerun UI smoke or long parent graphs.",
        ),
        _plan_entry(
            "packet/card/ack",
            packet_card_ack,
            model_checks=(
                "python simulations/run_flowpilot_packet_lifecycle_checks.py",
                "python simulations/run_flowpilot_card_envelope_checks.py",
                "python simulations/run_flowpilot_event_contract_checks.py",
                "python skills/flowpilot/assets/run_packet_control_plane_checks.py",
            ),
            coverage_boundary="Packet/card/ACK alignment covers mechanical handoff, identity, hash, receipt, and ACK/return hazards. It does not treat ACK as semantic role approval.",
        ),
        _plan_entry(
            "route mutation",
            route_mutation,
            model_checks=("python simulations/run_flowpilot_route_mutation_activation_checks.py",),
            coverage_boundary="Route-mutation alignment covers activation preconditions, sibling replacement, stale evidence, and route-sign projection for ordinary tests.",
        ),
        _plan_entry(
            "terminal/closure/resume",
            terminal_closure_resume,
            model_checks=(
                "python simulations/run_flowpilot_runtime_closure_checks.py",
                "python simulations/run_flowpilot_recursive_closure_reconciliation_checks.py",
                "python simulations/run_flowpilot_resume_checks.py",
            ),
            coverage_boundary="Terminal, closure, and resume alignment covers runtime tests for ledger closure and re-entry. It is not a production replay adapter.",
        ),
        _plan_entry(
            "role/output contracts",
            role_output,
            model_checks=(
                "python simulations/run_output_contract_checks.py",
                "python simulations/run_flowpilot_role_output_runtime_checks.py",
            ),
            coverage_boundary="Role/output alignment covers mechanical role-output and packet-output contracts. It does not judge task semantic quality.",
        ),
        _plan_entry(
            "router loop/daemon",
            router_loop_daemon,
            model_checks=(
                "python simulations/run_flowpilot_router_loop_checks.py",
                "python simulations/run_flowpilot_persistent_router_daemon_checks.py",
            ),
            coverage_boundary="Router-loop/daemon alignment covers foreground unit/runtime tests for queue, lock, and packet-loop behavior. It does not run long daemon soak tests.",
        ),
        _plan_entry(
            "test tiering/slow-test contracts",
            tiering,
            model_checks=(
                "python simulations/run_flowpilot_test_tiering_checks.py",
                "python simulations/run_flowpilot_slow_test_contract_checks.py",
            ),
            coverage_boundary="Test-tiering alignment covers test-plan mechanics and slow-test parent/child contracts, including progress-only background hazards.",
        ),
        _plan_entry(
            "meta/capability parents",
            meta_capability,
            model_checks=(
                "python simulations/run_meta_checks.py",
                "python simulations/run_capability_checks.py",
                "python simulations/run_meta_checks.py --full --fast",
                "python simulations/run_capability_checks.py --full --fast",
            ),
            coverage_boundary="Meta/Capability alignment covers parent-runner proof boundaries and control-gate unit evidence only. Parent results remain abstract model confidence, not ordinary production conformance.",
        ),
    ]


def _source_obligation(
    obligation_id: str,
    *,
    obligation_type: str,
    description: str,
    required_test_kinds: Sequence[str],
) -> ModelObligation:
    return _obligation(
        obligation_id,
        obligation_type=obligation_type,
        description=description,
        required_test_kinds=required_test_kinds,
        allow_shared_implementation=True,
    )


def build_source_contract_alignment_plan() -> ModelTestAlignmentPlan:
    """Build the AST-audited model/code/test contract subset."""

    obligations = (
        _source_obligation(
            "startup.questions.pause_before_work",
            obligation_type="contract",
            description="Source-audited startup boundary for run-until-wait, action application, and next-action answer handling.",
            required_test_kinds=(HAPPY, NEGATIVE),
        ),
        _source_obligation(
            "startup.run_isolation_and_activation",
            obligation_type="scenario",
            description="Source-audited startup activation failure boundary through recorded external events.",
            required_test_kinds=(FAILURE,),
        ),
        _source_obligation(
            "packet.physical_body_boundary",
            obligation_type="contract",
            description="Source-audited Controller handoff boundary that keeps packet bodies out of Controller relay text.",
            required_test_kinds=(NEGATIVE,),
        ),
        _source_obligation(
            "card.ack_identity_and_bundle",
            obligation_type="hazard",
            description="Source-audited card open/ACK/validation contract for externally visible card acknowledgement mechanics.",
            required_test_kinds=(HAPPY,),
        ),
        _source_obligation(
            "ack.return_wait_preconsumption",
            obligation_type="transition",
            description="Source-audited ACK preconsumption boundary through Router events and card ACK helpers.",
            required_test_kinds=(EDGE,),
        ),
        _source_obligation(
            "route_mutation.topology_and_recheck",
            obligation_type="contract",
            description="Source-audited route mutation precondition boundary through Router events and packet issuance.",
            required_test_kinds=(NEGATIVE,),
        ),
        _source_obligation(
            "route_mutation.sibling_replacement_stales_old_evidence",
            obligation_type="hazard",
            description="Source-audited sibling replacement boundary through Router events, packet issuance, and route-sign output.",
            required_test_kinds=(EDGE, NEGATIVE),
        ),
        _source_obligation(
            "terminal.final_ledger_and_backward_replay",
            obligation_type="invariant",
            description="Source-audited terminal replay/final-ledger boundary through Router event intake.",
            required_test_kinds=(HAPPY, NEGATIVE),
        ),
        _source_obligation(
            "resume.current_run_reentry",
            obligation_type="transition",
            description="Source-audited resume re-entry boundary through Router event intake, next action, and action application.",
            required_test_kinds=(HAPPY, FAILURE),
        ),
        _source_obligation(
            "role_output.registry_authority",
            obligation_type="contract",
            description="Source-audited role-output session preparation contract.",
            required_test_kinds=(HAPPY,),
        ),
        _source_obligation(
            "output_contract.packet_binding",
            obligation_type="contract",
            description="Source-audited packet output contract across packet creation, Controller relay, and result writes.",
            required_test_kinds=(HAPPY,),
        ),
        _source_obligation(
            "router_loop.packet_result_review_loop",
            obligation_type="transition",
            description="Source-audited current-node packet/result review loop boundary through Router event intake.",
            required_test_kinds=(HAPPY, FAILURE),
        ),
        _source_obligation(
            "runtime_closure.officer_lifecycle_contract",
            obligation_type="contract",
            description="Source-audited officer request/result lifecycle records keep PM authority, sealed-body boundaries, and validation results explicit.",
            required_test_kinds=(HAPPY,),
        ),
        _source_obligation(
            "runtime_closure.continuation_and_final_report_contract",
            obligation_type="contract",
            description="Source-audited continuation quarantine, final user report, and route display refresh records separate current-run authority from display/report artifacts.",
            required_test_kinds=(HAPPY,),
        ),
        _source_obligation(
            "daemon.lock_status_queue_contract",
            obligation_type="contract",
            description="Source-audited daemon lock/status/tick contracts prevent duplicate writers and distinguish live, stale, stopped, and errored daemon states.",
            required_test_kinds=(HAPPY, EDGE, NEGATIVE),
        ),
        _source_obligation(
            "startup_daemon.lock_liveness_contract",
            obligation_type="contract",
            description="Source-audited startup-daemon liveness helpers classify lock freshness and heartbeat monitor requirements.",
            required_test_kinds=(HAPPY,),
        ),
        _source_obligation(
            "test_tiering.foreground_fast_scope",
            obligation_type="contract",
            description="Source-audited test-tier command selection boundary.",
            required_test_kinds=(NEGATIVE,),
        ),
        _source_obligation(
            "meta_parent.thin_default_and_layered_full_boundary",
            obligation_type="contract",
            description="Source-audited Meta runner entrypoint for thin-parent default evidence.",
            required_test_kinds=(HAPPY,),
        ),
        _source_obligation(
            "capability_parent.proof_reuse_and_fast_boundary",
            obligation_type="contract",
            description="Source-audited smoke fast-path entrypoint for Capability proof boundary evidence.",
            required_test_kinds=(NEGATIVE,),
        ),
    )
    code_contracts = (
        _contract(
            "router.run_until_wait",
            path="skills/flowpilot/assets/flowpilot_router_controller_runtime.py",
            symbol="run_until_wait",
            implements=("startup.questions.pause_before_work",),
            external_inputs=("project_root",),
        ),
        _contract(
            "router.apply_action",
            path="skills/flowpilot/assets/flowpilot_router_controller_runtime.py",
            symbol="apply_action",
            implements=("startup.questions.pause_before_work", "resume.current_run_reentry"),
            external_inputs=("project_root", "action_type", "payload"),
        ),
        _contract(
            "router.record_external_event",
            path="skills/flowpilot/assets/flowpilot_router_controller_runtime.py",
            symbol="record_external_event",
            implements=(
                "startup.run_isolation_and_activation",
                "ack.return_wait_preconsumption",
                "route_mutation.topology_and_recheck",
                "route_mutation.sibling_replacement_stales_old_evidence",
                "terminal.final_ledger_and_backward_replay",
                "resume.current_run_reentry",
                "router_loop.packet_result_review_loop",
            ),
            external_inputs=("project_root", "event", "payload"),
        ),
        _contract(
            "router.next_action",
            path="skills/flowpilot/assets/flowpilot_router_controller_runtime.py",
            symbol="next_action",
            implements=("startup.questions.pause_before_work", "resume.current_run_reentry"),
            external_inputs=("project_root",),
        ),
        _contract(
            "packet.create_packet",
            path="skills/flowpilot/assets/packet_runtime_creation_core.py",
            symbol="create_packet",
            implements=(
                "route_mutation.topology_and_recheck",
                "route_mutation.sibling_replacement_stales_old_evidence",
                "output_contract.packet_binding",
            ),
            external_inputs=("project_root", "from_role", "to_role", "packet_id"),
            side_effects=("write_controller_status_packet", "write_json_atomic", "write_text_atomic"),
        ),
        _contract(
            "packet.build_controller_handoff",
            path="skills/flowpilot/assets/packet_runtime_creation_handoff.py",
            symbol="build_controller_handoff",
            implements=("packet.physical_body_boundary",),
            external_inputs=("envelope", "envelope_path"),
        ),
        _contract(
            "packet.controller_handoff_text",
            path="skills/flowpilot/assets/packet_runtime_creation_handoff.py",
            symbol="controller_handoff_text",
            implements=("packet.physical_body_boundary",),
            external_inputs=("handoff",),
        ),
        _contract(
            "packet.controller_relay_envelope",
            path="skills/flowpilot/assets/packet_runtime_relay.py",
            symbol="controller_relay_envelope",
            implements=("output_contract.packet_binding",),
            external_inputs=("project_root", "envelope", "envelope_path"),
            side_effects=("update", "write_json_atomic"),
        ),
        _contract(
            "packet.write_result",
            path="skills/flowpilot/assets/packet_runtime_results.py",
            symbol="write_result",
            implements=("output_contract.packet_binding",),
            external_inputs=("project_root", "packet_envelope", "result_body_text"),
            side_effects=("write_controller_status_packet", "write_json_atomic", "write_text_atomic"),
        ),
        _contract(
            "card.open_card",
            path="skills/flowpilot/assets/card_runtime_ack.py",
            symbol="open_card",
            implements=("card.ack_identity_and_bundle", "ack.return_wait_preconsumption"),
            external_inputs=("project_root", "envelope_path", "role", "agent_id"),
            side_effects=("write_json",),
        ),
        _contract(
            "card.submit_card_ack",
            path="skills/flowpilot/assets/card_runtime_ack.py",
            symbol="submit_card_ack",
            implements=("card.ack_identity_and_bundle", "ack.return_wait_preconsumption"),
            external_inputs=("project_root", "envelope_path", "role", "agent_id"),
            side_effects=("write_json",),
        ),
        _contract(
            "card.validate_card_ack",
            path="skills/flowpilot/assets/card_runtime_ack.py",
            symbol="validate_card_ack",
            implements=("card.ack_identity_and_bundle",),
            external_inputs=("project_root", "envelope_path", "ack_path"),
        ),
        _contract(
            "route_sign.generate",
            path="skills/flowpilot/assets/flowpilot_user_flow_diagram.py",
            symbol="generate",
            implements=("route_mutation.sibling_replacement_stales_old_evidence",),
            external_inputs=("root",),
            side_effects=("write_text",),
        ),
        _contract(
            "role_output.prepare_output_session",
            path="skills/flowpilot/assets/role_output_runtime_progress.py",
            symbol="prepare_output_session",
            implements=("role_output.registry_authority",),
            external_inputs=("project_root", "role", "agent_id", "output_type"),
            side_effects=("write_output_progress_status",),
        ),
        _contract(
            "runtime_closure.validate_officer_request_record",
            path="skills/flowpilot/assets/flowpilot_runtime_closure.py",
            symbol="validate_officer_request_record",
            implements=("runtime_closure.officer_lifecycle_contract",),
            external_inputs=("record",),
        ),
        _contract(
            "runtime_closure.validate_officer_result_record",
            path="skills/flowpilot/assets/flowpilot_runtime_closure.py",
            symbol="validate_officer_result_record",
            implements=("runtime_closure.officer_lifecycle_contract",),
            external_inputs=("record", "result"),
        ),
        _contract(
            "runtime_closure.officer_lifecycle_entry_from_request",
            path="skills/flowpilot/assets/flowpilot_runtime_closure.py",
            symbol="officer_lifecycle_entry_from_request",
            implements=("runtime_closure.officer_lifecycle_contract",),
            external_inputs=("record", "now"),
        ),
        _contract(
            "runtime_closure.continuation_quarantine_record",
            path="skills/flowpilot/assets/flowpilot_runtime_closure.py",
            symbol="continuation_quarantine_record",
            implements=("runtime_closure.continuation_and_final_report_contract",),
            external_inputs=("run_id", "run_root", "current_pointer", "run_index", "created_at"),
        ),
        _contract(
            "runtime_closure.validate_continuation_quarantine_record",
            path="skills/flowpilot/assets/flowpilot_runtime_closure.py",
            symbol="validate_continuation_quarantine_record",
            implements=("runtime_closure.continuation_and_final_report_contract",),
            external_inputs=("record",),
        ),
        _contract(
            "runtime_closure.final_user_report_record",
            path="skills/flowpilot/assets/flowpilot_runtime_closure.py",
            symbol="final_user_report_record",
            implements=("runtime_closure.continuation_and_final_report_contract",),
            external_inputs=("run_id", "lifecycle_status", "summary_path", "summary_json_path", "summary_sha256", "displayed_to_user", "written_at"),
        ),
        _contract(
            "runtime_closure.validate_final_user_report_record",
            path="skills/flowpilot/assets/flowpilot_runtime_closure.py",
            symbol="validate_final_user_report_record",
            implements=("runtime_closure.continuation_and_final_report_contract",),
            external_inputs=("record",),
        ),
        _contract(
            "runtime_closure.route_display_refresh_record",
            path="skills/flowpilot/assets/flowpilot_runtime_closure.py",
            symbol="route_display_refresh_record",
            implements=("runtime_closure.continuation_and_final_report_contract",),
            external_inputs=("run_id", "display_plan_path", "route_state_snapshot_path", "projection_hash", "refreshed_at"),
        ),
        _contract(
            "runtime_closure.validate_route_display_refresh_record",
            path="skills/flowpilot/assets/flowpilot_runtime_closure.py",
            symbol="validate_route_display_refresh_record",
            implements=("runtime_closure.continuation_and_final_report_contract",),
            external_inputs=("record",),
        ),
        _contract(
            "daemon.run_router_daemon",
            path="skills/flowpilot/assets/flowpilot_router_daemon_runtime.py",
            symbol="run_router_daemon",
            implements=("daemon.lock_status_queue_contract",),
            external_inputs=("router", "project_root"),
            side_effects=("save_run_state",),
        ),
        _contract(
            "daemon.stop_router_daemon",
            path="skills/flowpilot/assets/flowpilot_router_daemon_runtime.py",
            symbol="stop_router_daemon",
            implements=("daemon.lock_status_queue_contract",),
            external_inputs=("router", "project_root", "reason"),
            side_effects=("save_run_state",),
        ),
        _contract(
            "daemon.acquire_lock",
            path="skills/flowpilot/assets/flowpilot_router_daemon_runtime.py",
            symbol="_acquire_router_daemon_lock",
            implements=("daemon.lock_status_queue_contract",),
            external_inputs=("router", "project_root", "run_root", "run_state"),
            side_effects=("write", "write_json"),
        ),
        _contract(
            "daemon.refresh_lock",
            path="skills/flowpilot/assets/flowpilot_router_daemon_runtime.py",
            symbol="_refresh_router_daemon_lock",
            implements=("daemon.lock_status_queue_contract",),
            external_inputs=("router", "project_root", "run_root"),
            side_effects=("write_json",),
        ),
        _contract(
            "daemon.release_lock",
            path="skills/flowpilot/assets/flowpilot_router_daemon_runtime.py",
            symbol="_release_router_daemon_lock",
            implements=("daemon.lock_status_queue_contract",),
            external_inputs=("router", "project_root", "run_root", "reason"),
            side_effects=("write_json",),
        ),
        _contract(
            "daemon.write_status",
            path="skills/flowpilot/assets/flowpilot_router_daemon_runtime.py",
            symbol="_write_router_daemon_status",
            implements=("daemon.lock_status_queue_contract",),
            external_inputs=("router", "project_root", "run_root", "run_state", "lifecycle_status"),
            side_effects=("write_json",),
        ),
        _contract(
            "daemon.tick",
            path="skills/flowpilot/assets/flowpilot_router_daemon_runtime.py",
            symbol="_router_daemon_tick",
            implements=("daemon.lock_status_queue_contract",),
            external_inputs=("router", "project_root", "run_root", "run_state", "observe_only"),
            side_effects=("save_run_state", "update"),
        ),
        _contract(
            "startup_daemon.lock_liveness",
            path="skills/flowpilot/assets/flowpilot_router_startup_daemon.py",
            symbol="_router_daemon_lock_liveness",
            implements=("startup_daemon.lock_liveness_contract",),
            external_inputs=("lock",),
        ),
        _contract(
            "startup_daemon.heartbeat_monitor",
            path="skills/flowpilot/assets/flowpilot_router_startup_daemon.py",
            symbol="_router_daemon_heartbeat_monitor",
            implements=("startup_daemon.lock_liveness_contract",),
            external_inputs=("lock", "liveness", "status_exists", "status_ok"),
        ),
        _contract(
            "startup_daemon.lock_is_live",
            path="skills/flowpilot/assets/flowpilot_router_startup_daemon.py",
            symbol="_router_daemon_lock_is_live",
            implements=("startup_daemon.lock_liveness_contract",),
            external_inputs=("lock",),
        ),
        _contract(
            "test_tier.commands_for_tier",
            path="scripts/run_test_tier.py",
            symbol="commands_for_tier",
            implements=("test_tiering.foreground_fast_scope",),
            external_inputs=("tier",),
        ),
        _contract(
            "meta_runner.main",
            path="simulations/run_meta_checks.py",
            symbol="main",
            implements=("meta_parent.thin_default_and_layered_full_boundary",),
            external_inputs=("argv",),
            side_effects=("write_text",),
        ),
        _contract(
            "smoke.main",
            path="scripts/smoke_autopilot.py",
            symbol="main",
            implements=("capability_parent.proof_reuse_and_fast_boundary",),
            external_inputs=("argv",),
        ),
    )
    test_evidence = (
        _evidence(
            "source.startup.waits",
            test_name="test_startup_waits_for_answers_before_banner_or_controller",
            path="tests/router_runtime/startup_bootstrap.py",
            command="python -m unittest tests.test_flowpilot_router_runtime_startup_daemon",
            test_kind=NEGATIVE,
            covers=("startup.questions.pause_before_work",),
            code_contracts=("router.run_until_wait", "router.apply_action"),
        ),
        _evidence(
            "source.startup.answer",
            test_name="test_record_startup_answers_accepts_ai_interpretation_with_reviewer_receipt",
            path="tests/router_runtime/startup_bootstrap.py",
            command="python -m unittest tests.test_flowpilot_router_runtime_startup_daemon",
            test_kind=HAPPY,
            covers=("startup.questions.pause_before_work",),
            code_contracts=("router.apply_action", "router.next_action"),
        ),
        _evidence(
            "source.startup.activation",
            test_name="test_startup_activation_requires_reviewer_facts_before_work",
            path="tests/router_runtime/startup_bootstrap.py",
            command="python -m unittest tests.test_flowpilot_router_runtime_startup_daemon",
            test_kind=FAILURE,
            covers=("startup.run_isolation_and_activation",),
            code_contracts=("router.record_external_event",),
        ),
        _evidence(
            "source.packet.handoff",
            test_name="test_controller_handoff_contains_envelope_only_not_body_content",
            path="tests/test_flowpilot_packet_runtime.py",
            command="python -m unittest tests.test_flowpilot_packet_runtime",
            test_kind=NEGATIVE,
            covers=("packet.physical_body_boundary",),
            code_contracts=("packet.build_controller_handoff", "packet.controller_handoff_text"),
        ),
        _evidence(
            "source.card.happy",
            test_name="test_card_runtime_opens_card_and_submits_ack",
            path="tests/test_flowpilot_card_runtime.py",
            command="python -m pytest tests/test_flowpilot_card_runtime.py",
            test_kind=HAPPY,
            covers=("card.ack_identity_and_bundle",),
            code_contracts=("card.open_card", "card.submit_card_ack", "card.validate_card_ack"),
        ),
        _evidence(
            "source.ack.edge",
            test_name="test_record_external_event_preconsumes_valid_card_ack_before_blocking",
            path="tests/router_runtime/ack_return.py",
            command="python -m unittest tests.test_flowpilot_router_runtime_ack_return",
            test_kind=EDGE,
            covers=("ack.return_wait_preconsumption",),
            code_contracts=("router.record_external_event", "card.open_card", "card.submit_card_ack"),
        ),
        _evidence(
            "source.route.preconditions",
            test_name="test_route_mutation_and_final_ledger_have_required_preconditions",
            path="tests/router_runtime/route_mutation_preconditions.py",
            command="python -m unittest tests.router_runtime.route_mutation_preconditions.RouteMutationPreconditionRuntimeTests.test_route_mutation_and_final_ledger_have_required_preconditions",
            test_kind=NEGATIVE,
            covers=("route_mutation.topology_and_recheck",),
            code_contracts=("router.record_external_event", "packet.create_packet"),
        ),
        _evidence(
            "source.route.sibling",
            test_name="test_route_mutation_sibling_branch_replacement_blocks_old_sibling_proof",
            path="tests/router_runtime/route_mutation_sibling_replacement.py",
            command="python -m unittest tests.router_runtime.route_mutation_sibling_replacement.RouteMutationSiblingReplacementRuntimeTests.test_route_mutation_sibling_branch_replacement_blocks_old_sibling_proof",
            test_kind=NEGATIVE,
            covers=("route_mutation.sibling_replacement_stales_old_evidence",),
            code_contracts=("router.record_external_event", "packet.create_packet"),
        ),
        _evidence(
            "source.route.display",
            test_name="test_sibling_branch_replacement_draws_replacement_and_replay_scope",
            path="tests/test_flowpilot_user_flow_diagram.py",
            command="python -m unittest tests.test_flowpilot_user_flow_diagram.FlowPilotUserFlowDiagramTests.test_sibling_branch_replacement_draws_replacement_and_replay_scope",
            test_kind=EDGE,
            covers=("route_mutation.sibling_replacement_stales_old_evidence",),
            code_contracts=("route_sign.generate",),
        ),
        _evidence(
            "source.terminal.replay",
            test_name="test_terminal_replay_requires_reviewed_segments_and_pm_segment_decisions",
            path="tests/router_runtime/terminal.py",
            command="python -m unittest tests.test_flowpilot_router_runtime_terminal",
            test_kind=HAPPY,
            covers=("terminal.final_ledger_and_backward_replay",),
            code_contracts=("router.record_external_event",),
        ),
        _evidence(
            "source.terminal.final",
            test_name="test_final_ledger_rejects_missing_source_of_truth_entries_and_contract_replay",
            path="tests/router_runtime/terminal.py",
            command="python -m unittest tests.test_flowpilot_router_runtime_terminal",
            test_kind=NEGATIVE,
            covers=("terminal.final_ledger_and_backward_replay",),
            code_contracts=("router.record_external_event",),
        ),
        _evidence(
            "source.resume.loads",
            test_name="test_resume_reentry_loads_state_before_resume_cards",
            path="tests/router_runtime/resume.py",
            command="python -m unittest tests.test_flowpilot_router_runtime_resume",
            test_kind=HAPPY,
            covers=("resume.current_run_reentry",),
            code_contracts=("router.record_external_event", "router.next_action", "router.apply_action"),
        ),
        _evidence(
            "source.resume.ambiguous",
            test_name="test_resume_ambiguous_state_blocks_continue_without_recovery_evidence",
            path="tests/router_runtime/resume.py",
            command="python -m unittest tests.test_flowpilot_router_runtime_resume",
            test_kind=FAILURE,
            covers=("resume.current_run_reentry",),
            code_contracts=("router.record_external_event", "router.apply_action"),
        ),
        _evidence(
            "source.role.prep",
            test_name="test_registry_backed_output_types_are_preparable",
            path="tests/test_flowpilot_role_output_runtime.py",
            command="python -m unittest tests.test_flowpilot_role_output_runtime",
            test_kind=HAPPY,
            covers=("role_output.registry_authority",),
            code_contracts=("role_output.prepare_output_session",),
        ),
        _evidence(
            "source.runtime_closure.records",
            test_name="test_runtime_closure_external_record_contracts_are_self_validating",
            path="tests/test_flowpilot_router_boundaries.py",
            command="python -m unittest tests.test_flowpilot_router_boundaries.FlowPilotRouterBoundaryTests.test_runtime_closure_external_record_contracts_are_self_validating",
            test_kind=HAPPY,
            covers=(
                "runtime_closure.officer_lifecycle_contract",
                "runtime_closure.continuation_and_final_report_contract",
            ),
            code_contracts=(
                "runtime_closure.validate_officer_request_record",
                "runtime_closure.validate_officer_result_record",
                "runtime_closure.officer_lifecycle_entry_from_request",
                "runtime_closure.continuation_quarantine_record",
                "runtime_closure.validate_continuation_quarantine_record",
                "runtime_closure.final_user_report_record",
                "runtime_closure.validate_final_user_report_record",
                "runtime_closure.route_display_refresh_record",
                "runtime_closure.validate_route_display_refresh_record",
            ),
        ),
        _evidence(
            "source.daemon.run_stop",
            test_name="test_router_daemon_observation_initializes_lock_status_and_ledger",
            path="tests/router_runtime/startup_daemon.py",
            command="python -m unittest tests.test_flowpilot_router_runtime_startup_daemon",
            test_kind=HAPPY,
            covers=("daemon.lock_status_queue_contract",),
            code_contracts=("daemon.run_router_daemon", "daemon.stop_router_daemon"),
        ),
        _evidence(
            "source.daemon.tick_bound",
            test_name="test_router_daemon_tick_stays_bound_when_current_focus_changes",
            path="tests/router_runtime/startup_daemon.py",
            command="python -m unittest tests.test_flowpilot_router_runtime_startup_daemon",
            test_kind=EDGE,
            covers=("daemon.lock_status_queue_contract",),
            code_contracts=("daemon.acquire_lock", "daemon.tick"),
        ),
        _evidence(
            "source.daemon.refresh_lock",
            test_name="test_router_daemon_refresh_does_not_reactivate_released_lock",
            path="tests/router_runtime/startup_daemon.py",
            command="python -m unittest tests.test_flowpilot_router_runtime_startup_daemon",
            test_kind=NEGATIVE,
            covers=("daemon.lock_status_queue_contract",),
            code_contracts=("daemon.acquire_lock", "daemon.refresh_lock", "daemon.release_lock"),
        ),
        _evidence(
            "source.daemon.status",
            test_name="test_router_daemon_status_not_active_after_error_lock_or_missing_pid",
            path="tests/router_runtime/startup_daemon.py",
            command="python -m unittest tests.test_flowpilot_router_runtime_startup_daemon",
            test_kind=FAILURE,
            covers=("daemon.lock_status_queue_contract",),
            code_contracts=("daemon.write_status",),
        ),
        _evidence(
            "source.startup_daemon.liveness",
            test_name="test_startup_daemon_helpers_belong_to_owner_module",
            path="tests/test_flowpilot_router_boundaries.py",
            command="python -m unittest tests.test_flowpilot_router_boundaries.FlowPilotRouterBoundaryTests.test_startup_daemon_helpers_belong_to_owner_module",
            test_kind=HAPPY,
            covers=("startup_daemon.lock_liveness_contract",),
            code_contracts=(
                "startup_daemon.lock_liveness",
                "startup_daemon.heartbeat_monitor",
                "startup_daemon.lock_is_live",
            ),
        ),
        _evidence(
            "source.output.packet",
            test_name="test_pm_packet_repeats_output_contract_in_envelope_body_ledger_and_result",
            path="tests/test_flowpilot_output_contracts.py",
            command="python -m unittest tests.test_flowpilot_output_contracts",
            test_kind=HAPPY,
            covers=("output_contract.packet_binding",),
            code_contracts=("packet.create_packet", "packet.controller_relay_envelope", "packet.write_result"),
        ),
        _evidence(
            "source.router.direct",
            test_name="test_current_node_packet_relay_uses_router_direct_dispatch",
            path="tests/router_runtime/packets.py",
            command="python -m unittest tests.test_flowpilot_router_runtime_packets",
            test_kind=HAPPY,
            covers=("router_loop.packet_result_review_loop",),
            code_contracts=("router.record_external_event",),
        ),
        _evidence(
            "source.router.audit",
            test_name="test_current_node_completion_requires_reviewer_passed_packet_audit",
            path="tests/router_runtime/packets.py",
            command="python -m unittest tests.test_flowpilot_router_runtime_packets",
            test_kind=FAILURE,
            covers=("router_loop.packet_result_review_loop",),
            code_contracts=("router.record_external_event",),
        ),
        _evidence(
            "source.tier.release",
            test_name="test_fast_and_router_tiers_do_not_contain_release_only_commands",
            path="tests/test_flowpilot_test_tiers.py",
            command="python -m unittest tests.test_flowpilot_test_tiers",
            test_kind=NEGATIVE,
            covers=("test_tiering.foreground_fast_scope",),
            code_contracts=("test_tier.commands_for_tier",),
        ),
        _evidence(
            "source.meta.thin",
            test_name="test_default_meta_runner_uses_thin_parent_without_full_graph",
            path="tests/test_flowpilot_thin_parent_checks.py",
            command="python -m unittest tests.test_flowpilot_thin_parent_checks",
            test_kind=HAPPY,
            covers=("meta_parent.thin_default_and_layered_full_boundary",),
            code_contracts=("meta_runner.main",),
        ),
        _evidence(
            "source.smoke.fast",
            test_name="test_smoke_fast_only_marks_slow_model_checks_fast",
            path="tests/test_flowguard_result_proof.py",
            command="python -m unittest tests.test_flowguard_result_proof",
            test_kind=NEGATIVE,
            covers=("capability_parent.proof_reuse_and_fast_boundary",),
            code_contracts=("smoke.main",),
        ),
    )
    return ModelTestAlignmentPlan(
        model_id="model_test_code_source_contracts",
        obligations=obligations,
        code_contracts=code_contracts,
        test_evidence=test_evidence,
        require_code_contracts=True,
    )


def _read_sources_for_plan(plan: ModelTestAlignmentPlan) -> dict[str, str]:
    paths = {contract.path for contract in plan.code_contracts}
    paths.update(evidence.path for evidence in plan.test_evidence)
    return {path: (ROOT / path).read_text(encoding="utf-8") for path in sorted(paths)}


def _source_contract_plan_report() -> dict[str, Any]:
    plan = build_source_contract_alignment_plan()
    alignment_report = review_model_test_alignment(plan)
    source_by_path = _read_sources_for_plan(plan)
    code_evidence = audit_python_code_contracts(plan.code_contracts, source_by_path)
    test_assertions = audit_python_test_assertions(plan.test_evidence, plan.code_contracts, source_by_path)
    source_report = review_python_contract_source_audit(
        plan.code_contracts,
        plan.test_evidence,
        code_evidence,
        test_assertions,
    )
    findings = [
        {"layer": "model_code_test_alignment", **finding}
        for finding in alignment_report.to_dict()["findings"]
    ]
    findings.extend(
        {"layer": "python_source_contract_audit", **finding}
        for finding in source_report.to_dict()["findings"]
    )
    return {
        "ok": alignment_report.ok and source_report.ok,
        "model_id": plan.model_id,
        "source_audit_boundary": SOURCE_AUDIT_BOUNDARY,
        "finding_count": len(findings),
        "finding_counts": _finding_counts(findings),
        "findings": findings,
        "plan": plan.to_dict(),
        "alignment_report": alignment_report.to_dict(),
        "source_audit_report": source_report.to_dict(),
    }


def _known_bad_cases() -> list[dict[str, Any]]:
    obligation = _obligation(
        "known_bad.required_obligation",
        obligation_type="hazard",
        description="Synthetic obligation used only to prove the FlowGuard alignment reviewer rejects bad evidence.",
        required_test_kinds=(HAPPY,),
    )
    path = "tests/test_flowpilot_model_test_alignment.py"
    command = "python -m unittest tests.test_flowpilot_model_test_alignment"
    return [
        {
            "name": "missing_evidence",
            "expected_codes": ["missing_test_evidence"],
            "plan": ModelTestAlignmentPlan(
                model_id="known_bad_missing_evidence",
                obligations=(obligation,),
                test_evidence=(),
            ),
        },
        {
            "name": "stale_evidence",
            "expected_codes": ["stale_test_evidence"],
            "plan": ModelTestAlignmentPlan(
                model_id="known_bad_stale_evidence",
                obligations=(obligation,),
                test_evidence=(
                    _evidence(
                        "known_bad.stale",
                        test_name="synthetic stale evidence",
                        path=path,
                        command=command,
                        test_kind=HAPPY,
                        covers=("known_bad.required_obligation",),
                        evidence_current=False,
                        stale_reasons=("model obligation changed after evidence was recorded",),
                    ),
                ),
            ),
        },
        {
            "name": "progress_only_background_evidence",
            "expected_codes": ["test_evidence_not_passing"],
            "plan": ModelTestAlignmentPlan(
                model_id="known_bad_progress_only",
                obligations=(obligation,),
                test_evidence=(
                    _evidence(
                        "known_bad.progress_only",
                        test_name="synthetic background check with progress output only",
                        path=path,
                        command=command,
                        test_kind=HAPPY,
                        covers=("known_bad.required_obligation",),
                        result_status=RUNNING,
                    ),
                ),
            ),
        },
        {
            "name": "overclaim_model_confidence",
            "expected_codes": ["test_overclaims_model_confidence"],
            "plan": ModelTestAlignmentPlan(
                model_id="known_bad_overclaim",
                obligations=(obligation,),
                test_evidence=(
                    _evidence(
                        "known_bad.overclaim",
                        test_name="synthetic evidence that overclaims full model confidence",
                        path=path,
                        command=command,
                        test_kind=HAPPY,
                        covers=("known_bad.required_obligation",),
                        overclaims_model_confidence=True,
                    ),
                ),
            ),
        },
        {
            "name": "orphan_evidence",
            "expected_codes": ["orphan_test_evidence"],
            "plan": ModelTestAlignmentPlan(
                model_id="known_bad_orphan",
                obligations=(obligation,),
                test_evidence=(
                    _evidence(
                        "known_bad.orphan",
                        test_name="synthetic evidence without obligation binding",
                        path=path,
                        command=command,
                        test_kind=HAPPY,
                        covers=(),
                    ),
                ),
            ),
        },
        {
            "name": "duplicate_same_kind_evidence",
            "expected_codes": ["duplicate_test_evidence_owner"],
            "plan": ModelTestAlignmentPlan(
                model_id="known_bad_duplicate",
                obligations=(obligation,),
                test_evidence=(
                    _evidence(
                        "known_bad.duplicate.first",
                        test_name="synthetic duplicate evidence first owner",
                        path=path,
                        command=command,
                        test_kind=HAPPY,
                        covers=("known_bad.required_obligation",),
                    ),
                    _evidence(
                        "known_bad.duplicate.second",
                        test_name="synthetic duplicate evidence second owner",
                        path=path,
                        command=command,
                        test_kind=HAPPY,
                        covers=("known_bad.required_obligation",),
                    ),
                ),
            ),
        },
    ]


def _source_known_bad_cases() -> list[dict[str, Any]]:
    command = "python -m unittest tests.test_flowpilot_model_test_alignment"
    return [
        {
            "name": "missing_python_symbol",
            "expected_codes": ["source_contract_missing_symbol"],
            "code_contracts": (
                CodeContract(
                    "source_bad.missing",
                    path="synthetic_source.py",
                    symbol="missing_symbol",
                ),
            ),
            "test_evidence": (),
            "source_by_path": {
                "synthetic_source.py": "def other_symbol():\n    return 1\n",
            },
        },
        {
            "name": "internal_path_only_test",
            "expected_codes": [
                "source_test_internal_path_only",
                "source_test_missing_code_contract_call",
            ],
            "code_contracts": (
                CodeContract(
                    "source_bad.foo",
                    path="synthetic_source.py",
                    symbol="foo",
                ),
            ),
            "test_evidence": (
                TestEvidence(
                    "source_bad.internal_path",
                    test_name="test_foo",
                    path="test_synthetic_source.py",
                    command=command,
                    result_status=PASSED,
                    covered_code_contracts=("source_bad.foo",),
                ),
            ),
            "source_by_path": {
                "synthetic_source.py": "def foo(value):\n    return value\n",
                "test_synthetic_source.py": "def test_foo():\n    assert 1 == 1\n",
            },
        },
        {
            "name": "missing_external_assertion",
            "expected_codes": [
                "source_test_internal_path_only",
                "source_test_missing_external_assertion",
            ],
            "code_contracts": (
                CodeContract(
                    "source_bad.foo",
                    path="synthetic_source.py",
                    symbol="foo",
                ),
            ),
            "test_evidence": (
                TestEvidence(
                    "source_bad.no_assert",
                    test_name="test_foo",
                    path="test_synthetic_source.py",
                    command=command,
                    result_status=PASSED,
                    covered_code_contracts=("source_bad.foo",),
                ),
            ),
            "source_by_path": {
                "synthetic_source.py": "def foo(value):\n    return value\n",
                "test_synthetic_source.py": "def test_foo():\n    foo(1)\n",
            },
        },
        {
            "name": "extra_side_effect",
            "expected_codes": ["source_contract_extra_side_effect"],
            "code_contracts": (
                CodeContract(
                    "source_bad.extra_effect",
                    path="synthetic_source.py",
                    symbol="foo",
                ),
            ),
            "test_evidence": (),
            "source_by_path": {
                "synthetic_source.py": (
                    "def write_json(payload):\n"
                    "    return None\n\n"
                    "def foo(value):\n"
                    "    write_json({'value': value})\n"
                    "    return value\n"
                ),
            },
        },
    ]


def _finding_counts(findings: Sequence[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        code = str(finding["code"])
        counts[code] = counts.get(code, 0) + 1
    return dict(sorted(counts.items()))


def _finding_counts_by_field(
    findings: Sequence[dict[str, Any]],
    field_name: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        value = str(finding.get(field_name, "unknown"))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def _line_count(text: str) -> int:
    return len(text.splitlines())


def _load_module_from_path(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    old_module = sys.modules.get(module_name)
    sys.modules[module_name] = module
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
        if old_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = old_module
    return module


def _python_summary(path: Path) -> dict[str, Any]:
    text = _read_text(path)
    rel_path = _repo_path(str(path.relative_to(ROOT)))
    summary: dict[str, Any] = {
        "path": rel_path,
        "line_count": _line_count(text),
        "top_level_functions": [],
        "top_level_classes": [],
        "local_imports": [],
        "has_main": False,
        "parse_error": "",
        "all_exports_count": 0,
    }
    try:
        tree = ast.parse(text, filename=rel_path)
    except SyntaxError as exc:
        summary["parse_error"] = str(exc)
        return summary
    functions: list[str] = []
    classes: list[str] = []
    imports: list[str] = []
    all_exports_count = 0
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith(("flowpilot_", "packet_", "card_", "role_", "barrier_")):
                imports.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(("flowpilot_", "packet_", "card_", "role_", "barrier_")):
                    imports.append(alias.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.Tuple, ast.List)):
                        all_exports_count = len(node.value.elts)
    summary["top_level_functions"] = sorted(functions)
    summary["top_level_classes"] = sorted(classes)
    summary["local_imports"] = sorted(set(imports))
    summary["has_main"] = "main" in functions
    summary["all_exports_count"] = all_exports_count
    return summary


def _text_corpus(paths: Sequence[Path]) -> str:
    return "\n".join(_read_text(path) for path in paths if path.exists())


def _simulation_model_corpus() -> str:
    paths = [
        path
        for path in sorted((ROOT / "simulations").glob("*.py"))
        if path.name != "run_flowpilot_model_test_alignment_checks.py"
    ]
    return _text_corpus(paths)


def _test_corpus() -> str:
    return _text_corpus(sorted((ROOT / "tests").rglob("*.py")))


def _surface_mentions(text: str, rel_path: str, stem: str) -> bool:
    return rel_path in text or stem in text


def _asset_model_binding(stem: str) -> str | None:
    if stem in ASSET_MODEL_BINDING_STEMS:
        return ASSET_MODEL_BINDING_STEMS[stem]
    for prefix, binding in ASSET_MODEL_BINDING_PREFIXES.items():
        if stem.startswith(prefix):
            return binding
    return None


def _script_model_binding(stem: str) -> str | None:
    return SCRIPT_MODEL_BINDING_STEMS.get(stem)


def _surface_kind_for_asset(stem: str, summary: dict[str, Any]) -> str:
    if stem in ASSET_FACADE_MODULES:
        return "compatibility_facade"
    local_imports = summary.get("local_imports", [])
    if summary.get("all_exports_count", 0) >= 6 and len(local_imports) >= 2:
        return "compatibility_facade"
    return "owner_module"


def _surface_threshold(kind: str) -> int:
    if kind == "compatibility_facade":
        return FACADE_STRUCTURE_SPLIT_LINE_THRESHOLD
    if kind == "script_entrypoint":
        return SCRIPT_STRUCTURE_SPLIT_LINE_THRESHOLD
    return OWNER_STRUCTURE_SPLIT_LINE_THRESHOLD


def _diagnostic_gap_codes(surface: dict[str, Any]) -> list[str]:
    codes: list[str] = []
    if not surface.get("has_model", False):
        codes.append("missing_model")
    if not surface.get("has_code", False):
        codes.append("missing_code")
    if not surface.get("has_test", False):
        codes.append("missing_test")
    if surface.get("has_code", False) and not surface.get("has_model", False):
        codes.append("extra_code")
    if (
        surface.get("has_test", False)
        and surface.get("kind") != "test_tier"
        and not surface.get("has_external_contract", False)
    ):
        codes.append("internal_only_test")
    if surface.get("evidence_status") in STALE_EVIDENCE_STATUSES:
        codes.append("stale_evidence")
    if surface.get("line_count", 0) > int(surface.get("split_threshold", 10**9)):
        codes.append("needs_structure_split")
    return [code for code in DIAGNOSTIC_GAP_CODES if code in codes]


def _diagnostic_surface_owner(surface: dict[str, Any]) -> str:
    owner = surface.get("surface_owner") or surface.get("owner")
    if owner:
        return str(owner)
    kind = str(surface.get("kind", "unknown"))
    if kind == "test_tier_command":
        return f"test-tier:{surface.get('tier', 'unknown')}"
    if kind == "test_tier":
        return "test-tier"
    path = str(surface.get("path", ""))
    if path:
        stem = Path(path).stem
        if path.startswith("skills/flowpilot/assets/"):
            return stem
        if path.startswith("scripts/"):
            return f"script:{stem}"
        if path.startswith("simulations/"):
            return f"model-check:{stem}"
    return str(surface.get("name", surface.get("surface_id", "unknown")))


def _diagnostic_release_relevance(surface: dict[str, Any]) -> str:
    relevance = surface.get("release_relevance")
    if relevance:
        return str(relevance)
    kind = str(surface.get("kind", "unknown"))
    path = str(surface.get("path", ""))
    stem = Path(path).stem if path else str(surface.get("name", ""))
    if surface.get("tier") == "legacy-full" or str(surface.get("name", "")).startswith(
        ("meta_legacy", "capability_legacy")
    ):
        return "legacy_validation"
    release_scripts = {
        "audit_local_install_sync",
        "check_install",
        "check_public_release",
        "install_flowpilot",
        "run_test_tier",
    }
    if surface.get("release_only") or stem in release_scripts:
        return "release_gate"
    if kind in {"test_tier", "test_tier_command", "model_check_runner"}:
        return "validation_gate"
    if kind in {"compatibility_facade", "owner_module"}:
        return "runtime_contract"
    if kind == "script_entrypoint":
        return "public_cli"
    return "maintenance"


def _diagnostic_repair_type(code: str, surface: dict[str, Any]) -> str:
    if code == "needs_structure_split" and surface.get("structure_split_status") == "deferred":
        return "defer_structure_split"
    if code == "stale_evidence" and surface.get("evidence_status") == "release_local_only":
        return "rerun_public_release_evidence"
    if code == "stale_evidence" and surface.get("evidence_status") == "failed":
        return "fix_failing_background_evidence"
    if code == "stale_evidence" and surface.get("evidence_status") in {
        "incomplete",
        "missing_final_artifacts",
        "progress_only",
        "running",
        "stale",
    }:
        return "complete_background_evidence"
    return DIAGNOSTIC_REPAIR_TYPES.get(code, "inspect_gap")


def _diagnostic_severity(code: str, surface: dict[str, Any]) -> str:
    relevance = str(surface.get("release_relevance", _diagnostic_release_relevance(surface)))
    kind = str(surface.get("kind", "unknown"))
    if code == "missing_code":
        return "critical"
    if code == "stale_evidence" and relevance in {"release_gate", "validation_gate"}:
        return "critical"
    if code == "missing_test" and relevance in {"release_gate", "validation_gate"}:
        return "high"
    if code in {"missing_model", "internal_only_test"} and kind in {
        "compatibility_facade",
        "owner_module",
        "script_entrypoint",
    }:
        return "high"
    if code == "needs_structure_split":
        return "medium"
    if code == "extra_code":
        return "low"
    return "medium"


def _diagnostic_priority_score(code: str, surface: dict[str, Any]) -> int:
    severity = _diagnostic_severity(code, surface)
    relevance = str(surface.get("release_relevance", _diagnostic_release_relevance(surface)))
    code_order = {
        "missing_code": 0,
        "stale_evidence": 1,
        "missing_test": 2,
        "internal_only_test": 3,
        "missing_model": 4,
        "needs_structure_split": 5,
        "extra_code": 6,
    }
    release_boost = {
        "release_gate": 0,
        "validation_gate": 2,
        "runtime_contract": 4,
        "public_cli": 6,
        "maintenance": 8,
        "legacy_validation": 12,
    }.get(relevance, 8)
    return (
        DIAGNOSTIC_SEVERITY_SCORE.get(severity, 99)
        + release_boost
        + code_order.get(code, 20)
    )


def _diagnostic_dedupe_key(code: str, surface: dict[str, Any]) -> str:
    owner = str(surface.get("surface_owner", _diagnostic_surface_owner(surface)))
    repair_type = _diagnostic_repair_type(code, surface)
    return f"{owner}|{repair_type}|{code}"


def _finalize_surface(surface: dict[str, Any]) -> dict[str, Any]:
    surface = dict(surface)
    surface["surface_owner"] = _diagnostic_surface_owner(surface)
    surface["release_relevance"] = _diagnostic_release_relevance(surface)
    gap_codes = _diagnostic_gap_codes(surface)
    surface["gap_codes"] = gap_codes
    surface["covered"] = not gap_codes
    surface["repair_types"] = sorted(
        {_diagnostic_repair_type(code, surface) for code in gap_codes}
    )
    surface["max_severity"] = (
        min(
            (_diagnostic_severity(code, surface) for code in gap_codes),
            key=lambda item: DIAGNOSTIC_SEVERITY_SCORE.get(item, 99),
        )
        if gap_codes
        else "none"
    )
    return surface


def _surface_findings(surface: dict[str, Any]) -> list[dict[str, Any]]:
    findings = []
    for code in surface["gap_codes"]:
        repair_type = _diagnostic_repair_type(code, surface)
        severity = _diagnostic_severity(code, surface)
        findings.append(
            {
                "code": code,
                "surface_id": surface["surface_id"],
                "kind": surface["kind"],
                "path": surface.get("path", ""),
                "name": surface.get("name", surface["surface_id"]),
                "surface_owner": surface["surface_owner"],
                "release_relevance": surface["release_relevance"],
                "repair_type": repair_type,
                "severity": severity,
                "dedupe_key": _diagnostic_dedupe_key(code, surface),
                "priority_score": _diagnostic_priority_score(code, surface),
                "message": _diagnostic_message(code, surface),
            }
        )
    return findings


def _actionable_summary(findings: Sequence[dict[str, Any]], *, limit: int = 40) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for finding in sorted(
        findings,
        key=lambda item: (
            int(item.get("priority_score", 999)),
            str(item.get("path", "")),
            str(item.get("surface_id", "")),
        ),
    ):
        key = str(finding["dedupe_key"])
        group = grouped.get(key)
        if group is None:
            group = {
                "dedupe_key": key,
                "severity": finding["severity"],
                "surface_owner": finding["surface_owner"],
                "release_relevance": finding["release_relevance"],
                "repair_type": finding["repair_type"],
                "primary_code": finding["code"],
                "priority_score": finding["priority_score"],
                "message": finding["message"],
                "finding_count": 0,
                "gap_codes": [],
                "surface_ids": [],
                "paths": [],
            }
            grouped[key] = group
        group["finding_count"] += 1
        if finding["code"] not in group["gap_codes"]:
            group["gap_codes"].append(finding["code"])
        if finding["surface_id"] not in group["surface_ids"]:
            group["surface_ids"].append(finding["surface_id"])
        path = finding.get("path", "")
        if path and path not in group["paths"]:
            group["paths"].append(path)
    for group in grouped.values():
        group["gap_codes"] = sorted(group["gap_codes"])
        group["surface_ids"] = group["surface_ids"][:12]
        group["paths"] = group["paths"][:8]
    return sorted(
        grouped.values(),
        key=lambda item: (
            int(item["priority_score"]),
            str(item["surface_owner"]),
            str(item["repair_type"]),
            str(item["primary_code"]),
        ),
    )[:limit]


def _diagnostic_message(code: str, surface: dict[str, Any]) -> str:
    name = surface.get("name", surface["surface_id"])
    if code == "missing_model":
        return f"{name} is not bound to an executable FlowGuard/model obligation in the current diagnostic corpus"
    if code == "missing_code":
        return f"{name} references code or command targets that are missing"
    if code == "missing_test":
        return f"{name} has no ordinary test evidence in the current diagnostic corpus"
    if code == "extra_code":
        return f"{name} exists as code without a model binding"
    if code == "internal_only_test":
        return f"{name} has tests or mentions but no source-level external contract binding"
    if code == "stale_evidence":
        status = surface.get("evidence_status", "unknown")
        return f"{name} has non-final background evidence status: {status}"
    if code == "needs_structure_split":
        return (
            f"{name} has {surface.get('line_count', 0)} lines, above the "
            f"{surface.get('split_threshold')} line diagnostic threshold"
        )
    return f"{name} has diagnostic gap {code}"


def _command_references_exist(command: Sequence[str]) -> bool:
    for token in command:
        normalized = token.replace("\\", "/")
        if normalized.endswith(".py"):
            if not (ROOT / normalized).exists():
                return False
        if normalized.startswith(("tests.", "simulations.")):
            module_path = ROOT / (normalized.replace(".", "/") + ".py")
            package_init = ROOT / normalized.replace(".", "/") / "__init__.py"
            if not module_path.exists() and not package_init.exists():
                return False
    return True


def _command_contains_test_target(command: Sequence[str]) -> bool:
    return any(
        token.startswith("tests.")
        or token.startswith("tests/")
        or token.startswith("tests\\")
        or token.startswith("tests")
        for token in command
    )


def _command_contains_model_runner(command: Sequence[str]) -> bool:
    return any(
        token.startswith("simulations/run_") and token.endswith(".py")
        for token in command
    )


def _background_evidence_for_command(
    run_test_tier: Any,
    command: Any,
    *,
    tier: str,
) -> dict[str, Any]:
    names = BACKGROUND_COMMAND_ARTIFACT_ALIASES.get(command.name, (command.name,))
    inspected: list[dict[str, Any]] = []
    preferred: dict[str, Any] | None = None
    for root in BACKGROUND_ARTIFACT_ROOTS:
        for name in names:
            evidence = run_test_tier.classify_background_artifact(
                root,
                name,
                command=command,
                tier=tier,
            )
            evidence["artifact_root"] = _repo_path(str(root.relative_to(ROOT))) if root.is_relative_to(ROOT) else str(root)
            evidence["artifact_name"] = name
            inspected.append(evidence)
            if evidence["status"] not in {"incomplete", "missing_final_artifacts"}:
                preferred = evidence
                break
        if preferred is not None:
            break
    if preferred is None:
        preferred = {
            "name": command.name,
            "status": "missing_final_artifacts",
            "execution_status": "missing_final_artifacts",
            "ok": False,
            "proof_scope": "unknown",
            "reasons": ["no_final_background_artifacts_found"],
            "artifacts": {},
        }
    return {
        "selected": preferred,
        "inspected": inspected,
    }


def _test_tier_command_surfaces(
    *,
    model_text: str,
    test_text: str,
) -> list[dict[str, Any]]:
    run_test_tier_path = ROOT / "scripts" / "run_test_tier.py"
    run_test_tier = _load_module_from_path(
        "flowpilot_alignment_diagnostic_run_test_tier",
        run_test_tier_path,
    )
    surfaces: list[dict[str, Any]] = []
    test_tiering_external_contract = (
        (ROOT / "simulations" / "flowpilot_test_tiering_model.py").exists()
        and TEST_TIER_COMMAND_CONTRACT_TEST_MARKER in test_text
    )
    for tier in run_test_tier.tier_names():
        commands = run_test_tier.commands_for_tier(tier)
        tier_surface = _finalize_surface(
            {
                "surface_id": f"tier:{tier}",
                "kind": "test_tier",
                "name": tier,
                "path": "scripts/run_test_tier.py",
                "has_model": tier in model_text or tier in test_text,
                "has_code": True,
                "has_test": tier in test_text,
                "has_external_contract": test_tiering_external_contract,
                "model_binding": "test_tiering_model",
                "evidence_status": "passed",
                "line_count": len(commands),
                "split_threshold": 999,
                "command_count": len(commands),
            }
        )
        surfaces.append(tier_surface)
        for command in commands:
            command_text = " ".join(command.command)
            evidence_status = "passed"
            background_evidence: dict[str, Any] | None = None
            if command.background_recommended or command.long_running:
                background_evidence = _background_evidence_for_command(
                    run_test_tier,
                    command,
                    tier=tier,
                )
                evidence_status = str(background_evidence["selected"]["status"])
            has_validation_target = _command_contains_test_target(command.command) or _command_contains_model_runner(command.command)
            surface = {
                "surface_id": f"tier-command:{tier}:{command.name}",
                "kind": "test_tier_command",
                "name": command.name,
                "path": "scripts/run_test_tier.py",
                "tier": tier,
                "command": list(command.command),
                "has_model": tier_surface["has_model"] or command.name in model_text or command.name in test_text,
                "has_code": _command_references_exist(command.command),
                "has_test": has_validation_target or command.name in test_text,
                "has_external_contract": tier_surface["has_external_contract"],
                "model_binding": tier_surface["model_binding"],
                "evidence_status": evidence_status,
                "line_count": 1,
                "split_threshold": 999,
                "long_running": command.long_running,
                "release_only": command.release_only,
                "background_recommended": command.background_recommended,
                "command_text": command_text,
            }
            if background_evidence is not None:
                surface["background_evidence"] = background_evidence
                surface["proof_scope"] = background_evidence["selected"].get("proof_scope", "unknown")
            surfaces.append(_finalize_surface(surface))
    return surfaces


def _asset_surfaces(
    *,
    model_text: str,
    test_text: str,
    source_contract_paths: set[str],
) -> list[dict[str, Any]]:
    surfaces: list[dict[str, Any]] = []
    aggregate_asset_contract_test_exists = (
        ASSET_SURFACE_CONTRACT_TEST_PATH.exists()
        and ASSET_SURFACE_CONTRACT_TEST_MARKER in test_text
    )
    for path in sorted((ROOT / "skills" / "flowpilot" / "assets").glob("*.py")):
        rel_path = _repo_path(str(path.relative_to(ROOT)))
        stem = path.stem
        summary = _python_summary(path)
        kind = _surface_kind_for_asset(stem, summary)
        surface_id = f"asset:{stem}"
        split_repair = dict(STRUCTURE_SPLIT_REPAIR_PLAN.get(stem, {}))
        if split_repair:
            split_repair.setdefault("recent_owner_context", list(RECENT_OWNER_MODULE_POLISH_COMMITS))
            split_repair.setdefault("structure_split_status", "deferred")
        model_binding = _asset_model_binding(stem)
        aggregate_facade_contract = aggregate_asset_contract_test_exists and kind == "compatibility_facade"
        has_external_contract = (
            rel_path in source_contract_paths
            or surface_id in FACADE_PARITY_EXTERNAL_CONTRACT_SURFACE_IDS
            or aggregate_facade_contract
        )
        has_model = bool(model_binding) or has_external_contract or _surface_mentions(model_text, rel_path, stem)
        has_test = aggregate_facade_contract or has_external_contract or _surface_mentions(test_text, rel_path, stem)
        surfaces.append(
            _finalize_surface(
                {
                    "surface_id": surface_id,
                    "kind": kind,
                    "name": stem,
                    "path": rel_path,
                    "has_model": has_model,
                    "has_code": path.exists() and not bool(summary["parse_error"]),
                    "has_test": has_test,
                    "has_external_contract": has_external_contract,
                    "model_binding": model_binding,
                    "evidence_status": "passed",
                    "line_count": summary["line_count"],
                    "split_threshold": _surface_threshold(kind),
                    "top_level_function_count": len(summary["top_level_functions"]),
                    "top_level_class_count": len(summary["top_level_classes"]),
                    "local_import_count": len(summary["local_imports"]),
                    "parse_error": summary["parse_error"],
                    **split_repair,
                }
            )
        )
    return surfaces


def _script_surfaces(*, model_text: str, test_text: str) -> list[dict[str, Any]]:
    surfaces: list[dict[str, Any]] = []
    aggregate_script_contract_test_exists = (
        SCRIPT_SURFACE_CONTRACT_TEST_PATH.exists()
        and SCRIPT_SURFACE_CONTRACT_TEST_MARKER in test_text
    )
    for path in sorted((ROOT / "scripts").glob("*.py")):
        rel_path = _repo_path(str(path.relative_to(ROOT)))
        stem = path.stem
        summary = _python_summary(path)
        model_binding = _script_model_binding(stem)
        has_model = bool(model_binding) or _surface_mentions(model_text, rel_path, stem)
        has_test = aggregate_script_contract_test_exists or _surface_mentions(test_text, rel_path, stem)
        has_external_contract = aggregate_script_contract_test_exists or (stem in SCRIPT_CLI_EXTERNAL_CONTRACT_STEMS and has_test)
        surfaces.append(
            _finalize_surface(
                {
                    "surface_id": f"script:{stem}",
                    "kind": "script_entrypoint",
                    "name": stem,
                    "path": rel_path,
                    "has_model": has_model,
                    "has_code": path.exists() and not bool(summary["parse_error"]),
                    "has_test": has_test,
                    "has_external_contract": has_external_contract,
                    "model_binding": model_binding,
                    "evidence_status": "passed",
                    "line_count": summary["line_count"],
                    "split_threshold": _surface_threshold("script_entrypoint"),
                    "has_main": summary["has_main"],
                    "parse_error": summary["parse_error"],
                }
            )
        )
    return surfaces


def _model_check_surfaces(*, test_text: str) -> list[dict[str, Any]]:
    surfaces: list[dict[str, Any]] = []
    aggregate_contract_test_exists = (
        MODEL_CHECK_RUNNER_CONTRACT_TEST_PATH.exists()
        and MODEL_CHECK_RUNNER_CONTRACT_TEST_MARKER in test_text
    )
    for path in sorted((ROOT / "simulations").glob("run_*checks.py")):
        rel_path = _repo_path(str(path.relative_to(ROOT)))
        stem = path.stem
        summary = _python_summary(path)
        has_test = aggregate_contract_test_exists or _surface_mentions(test_text, rel_path, stem)
        surfaces.append(
            _finalize_surface(
                {
                    "surface_id": f"model-check:{stem}",
                    "kind": "model_check_runner",
                    "name": stem,
                    "path": rel_path,
                    "has_model": True,
                    "has_code": path.exists() and summary["has_main"] and not bool(summary["parse_error"]),
                    "has_test": has_test,
                    "has_external_contract": aggregate_contract_test_exists or stem == "run_flowpilot_model_test_alignment_checks",
                    "model_binding": "model_check_runner_contract",
                    "evidence_status": "passed",
                    "line_count": summary["line_count"],
                    "split_threshold": _surface_threshold("script_entrypoint"),
                    "has_main": summary["has_main"],
                    "parse_error": summary["parse_error"],
                }
            )
        )
    return surfaces


def _full_diagnostic_known_bad_cases() -> list[dict[str, Any]]:
    return [
        {
            "name": "orphan_code",
            "expected_codes": ["missing_model", "missing_test", "extra_code"],
            "surface": {
                "surface_id": "synthetic:orphan_code",
                "kind": "owner_module",
                "name": "orphan_code",
                "path": "skills/flowpilot/assets/orphan_code.py",
                "has_model": False,
                "has_code": True,
                "has_test": False,
                "has_external_contract": False,
                "evidence_status": "passed",
                "line_count": 20,
                "split_threshold": OWNER_STRUCTURE_SPLIT_LINE_THRESHOLD,
            },
        },
        {
            "name": "wrapper_only_evidence",
            "expected_codes": ["internal_only_test"],
            "surface": {
                "surface_id": "synthetic:wrapper_only",
                "kind": "compatibility_facade",
                "name": "wrapper_only",
                "path": "skills/flowpilot/assets/wrapper_only.py",
                "has_model": True,
                "has_code": True,
                "has_test": True,
                "has_external_contract": False,
                "evidence_status": "passed",
                "line_count": 20,
                "split_threshold": FACADE_STRUCTURE_SPLIT_LINE_THRESHOLD,
            },
        },
        {
            "name": "progress_only_background",
            "expected_codes": ["stale_evidence"],
            "surface": {
                "surface_id": "synthetic:progress_only",
                "kind": "test_tier_command",
                "name": "progress_only_background",
                "path": "scripts/run_test_tier.py",
                "has_model": True,
                "has_code": True,
                "has_test": True,
                "has_external_contract": True,
                "evidence_status": "running",
                "line_count": 1,
                "split_threshold": 999,
            },
        },
        {
            "name": "local_only_release_proof",
            "expected_codes": ["stale_evidence"],
            "surface": {
                "surface_id": "synthetic:local_only_release",
                "kind": "test_tier_command",
                "name": "local_only_release",
                "path": "scripts/run_test_tier.py",
                "has_model": True,
                "has_code": True,
                "has_test": True,
                "has_external_contract": True,
                "evidence_status": "release_local_only",
                "line_count": 1,
                "split_threshold": 999,
                "release_only": True,
            },
        },
        {
            "name": "broad_unsplit_module",
            "expected_codes": ["needs_structure_split"],
            "surface": {
                "surface_id": "synthetic:broad_module",
                "kind": "owner_module",
                "name": "broad_module",
                "path": "skills/flowpilot/assets/broad_module.py",
                "has_model": True,
                "has_code": True,
                "has_test": True,
                "has_external_contract": True,
                "evidence_status": "passed",
                "line_count": OWNER_STRUCTURE_SPLIT_LINE_THRESHOLD + 1,
                "split_threshold": OWNER_STRUCTURE_SPLIT_LINE_THRESHOLD,
            },
        },
    ]


def _full_diagnostic_known_bad_report(case: dict[str, Any]) -> dict[str, Any]:
    surface = _finalize_surface(case["surface"])
    finding_codes = sorted(surface["gap_codes"])
    expected = set(case["expected_codes"])
    return {
        "name": case["name"],
        "ok": expected.issubset(finding_codes),
        "expected_codes": sorted(expected),
        "finding_codes": finding_codes,
        "surface": surface,
    }


def build_full_model_test_code_diagnostic() -> dict[str, Any]:
    source_plan = build_source_contract_alignment_plan()
    source_contract_paths = {contract.path for contract in source_plan.code_contracts}
    model_text = _simulation_model_corpus()
    test_text = _test_corpus()
    surfaces = []
    surfaces.extend(
        _asset_surfaces(
            model_text=model_text,
            test_text=test_text,
            source_contract_paths=source_contract_paths,
        )
    )
    surfaces.extend(_script_surfaces(model_text=model_text, test_text=test_text))
    surfaces.extend(_model_check_surfaces(test_text=test_text))
    surfaces.extend(_test_tier_command_surfaces(model_text=model_text, test_text=test_text))
    surfaces = sorted(surfaces, key=lambda item: (item["kind"], item["surface_id"]))
    findings: list[dict[str, Any]] = []
    for surface in surfaces:
        findings.extend(_surface_findings(surface))
    known_bad = [
        _full_diagnostic_known_bad_report(case)
        for case in _full_diagnostic_known_bad_cases()
    ]
    surface_counts: dict[str, int] = {}
    for surface in surfaces:
        kind = str(surface["kind"])
        surface_counts[kind] = surface_counts.get(kind, 0) + 1
    actionable_findings = sorted(
        findings,
        key=lambda item: (
            int(item.get("priority_score", 999)),
            str(item["path"]),
            str(item["surface_id"]),
        ),
    )
    actionable_summary = _actionable_summary(findings)
    return {
        "ok": all(item["ok"] for item in known_bad),
        "result_type": "flowpilot_full_model_test_code_diagnostic",
        "diagnostic_boundary": FULL_DIAGNOSTIC_BOUNDARY,
        "full_coverage_ok": not findings,
        "surface_count": len(surfaces),
        "surface_counts": dict(sorted(surface_counts.items())),
        "covered_surface_count": sum(1 for surface in surfaces if surface["covered"]),
        "gap_surface_count": sum(1 for surface in surfaces if surface["gap_codes"]),
        "gap_counts": _finding_counts(findings),
        "gap_counts_by_severity": _finding_counts_by_field(findings, "severity"),
        "gap_counts_by_repair_type": _finding_counts_by_field(findings, "repair_type"),
        "gap_counts_by_release_relevance": _finding_counts_by_field(findings, "release_relevance"),
        "findings": findings,
        "actionable_findings": actionable_findings[:80],
        "actionable_summary": actionable_summary,
        "surfaces": surfaces,
        "known_bad_ok": all(item["ok"] for item in known_bad),
        "known_bad_sanity_checks": known_bad,
    }


def _plan_report(entry: dict[str, Any]) -> dict[str, Any]:
    plan: ModelTestAlignmentPlan = entry["plan"]
    report = review_model_test_alignment(plan)
    findings = report.to_dict()["findings"]
    return {
        "family": entry["family"],
        "model_id": plan.model_id,
        "ok": report.ok,
        "decision": report.decision,
        "finding_count": len(report.findings),
        "finding_counts": _finding_counts(findings),
        "model_checks": entry["model_checks"],
        "coverage_boundary": entry["coverage_boundary"],
        "plan": plan.to_dict(),
        "report": report.to_dict(),
    }


def _known_bad_report(case: dict[str, Any]) -> dict[str, Any]:
    plan: ModelTestAlignmentPlan = case["plan"]
    report = review_model_test_alignment(plan)
    finding_codes = sorted({finding.code for finding in report.findings})
    expected = set(case["expected_codes"])
    return {
        "name": case["name"],
        "ok": (not report.ok) and expected.issubset(finding_codes),
        "expected_codes": sorted(expected),
        "finding_codes": finding_codes,
        "plan": plan.to_dict(),
        "report": report.to_dict(),
    }


def _source_known_bad_report(case: dict[str, Any]) -> dict[str, Any]:
    code_contracts: Sequence[CodeContract] = case["code_contracts"]
    test_evidence: Sequence[TestEvidence] = case["test_evidence"]
    code_evidence = audit_python_code_contracts(code_contracts, case["source_by_path"])
    test_assertions = audit_python_test_assertions(
        test_evidence,
        code_contracts,
        case["source_by_path"],
    )
    report = review_python_contract_source_audit(
        code_contracts,
        test_evidence,
        code_evidence,
        test_assertions,
    )
    finding_codes = sorted({finding.code for finding in report.findings})
    expected = set(case["expected_codes"])
    return {
        "name": case["name"],
        "ok": (not report.ok) and expected.issubset(finding_codes),
        "expected_codes": sorted(expected),
        "finding_codes": finding_codes,
        "code_contracts": [contract.to_dict() for contract in code_contracts],
        "test_evidence": [evidence.to_dict() for evidence in test_evidence],
        "report": report.to_dict(),
    }


def build_report() -> dict[str, Any]:
    per_plan = [_plan_report(entry) for entry in build_alignment_plan_entries()]
    known_bad = [_known_bad_report(case) for case in _known_bad_cases()]
    source_contract_plan = _source_contract_plan_report()
    source_known_bad = [
        _source_known_bad_report(case) for case in _source_known_bad_cases()
    ]
    full_diagnostic = build_full_model_test_code_diagnostic()
    findings: list[dict[str, Any]] = []
    for plan in per_plan:
        for finding in plan["report"]["findings"]:
            findings.append(
                {
                    "family": plan["family"],
                    "model_id": plan["model_id"],
                    **finding,
                }
            )
    findings.extend(source_contract_plan["findings"])
    alignment_ok = all(plan["ok"] for plan in per_plan)
    known_bad_ok = all(case["ok"] for case in known_bad)
    source_audit_ok = source_contract_plan["ok"]
    source_known_bad_ok = all(case["ok"] for case in source_known_bad)
    full_diagnostic_ok = full_diagnostic["ok"]
    return {
        "ok": alignment_ok and known_bad_ok and source_audit_ok and source_known_bad_ok and full_diagnostic_ok,
        "result_type": "flowpilot_model_test_alignment",
        "alignment_ok": alignment_ok,
        "known_bad_ok": known_bad_ok,
        "source_audit_ok": source_audit_ok,
        "source_known_bad_ok": source_known_bad_ok,
        "full_diagnostic_ok": full_diagnostic_ok,
        "full_coverage_ok": full_diagnostic["full_coverage_ok"],
        "source_audit_boundary": SOURCE_AUDIT_BOUNDARY,
        "full_diagnostic_boundary": FULL_DIAGNOSTIC_BOUNDARY,
        "plan_count": len(per_plan),
        "families": [plan["family"] for plan in per_plan],
        "findings": findings,
        "finding_counts": _finding_counts(findings),
        "per_plan": per_plan,
        "source_contract_plan": source_contract_plan,
        "full_model_test_code_diagnostic": full_diagnostic,
        "known_bad_sanity_checks": known_bad,
        "source_known_bad_sanity_checks": source_known_bad,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path for writing the JSON result payload.",
    )
    args = parser.parse_args(argv)

    report = build_report()
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
