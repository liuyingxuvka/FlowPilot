"""Run FlowGuard Model-Test Alignment checks for major FlowPilot families.

This runner is intentionally read-only. It does not execute the referenced
tests or long parent FlowGuard checks; it reviews declared model obligations
against ordinary test evidence by using FlowGuard's Model-Test Alignment API.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
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
            path="skills/flowpilot/assets/packet_runtime_creation.py",
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
            path="skills/flowpilot/assets/packet_runtime_creation.py",
            symbol="build_controller_handoff",
            implements=("packet.physical_body_boundary",),
            external_inputs=("envelope", "envelope_path"),
        ),
        _contract(
            "packet.controller_handoff_text",
            path="skills/flowpilot/assets/packet_runtime_creation.py",
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
    return {
        "ok": alignment_ok and known_bad_ok and source_audit_ok and source_known_bad_ok,
        "result_type": "flowpilot_model_test_alignment",
        "alignment_ok": alignment_ok,
        "known_bad_ok": known_bad_ok,
        "source_audit_ok": source_audit_ok,
        "source_known_bad_ok": source_known_bad_ok,
        "source_audit_boundary": SOURCE_AUDIT_BOUNDARY,
        "plan_count": len(per_plan),
        "families": [plan["family"] for plan in per_plan],
        "findings": findings,
        "finding_counts": _finding_counts(findings),
        "per_plan": per_plan,
        "source_contract_plan": source_contract_plan,
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
