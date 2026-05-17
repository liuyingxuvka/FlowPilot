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
    ModelObligation,
    ModelTestAlignmentPlan,
    TestEvidence,
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
) -> ModelObligation:
    return ModelObligation(
        obligation_id=obligation_id,
        obligation_type=obligation_type,
        description=description,
        required=True,
        required_test_kinds=tuple(required_test_kinds),
        risk_level=risk_level,
        allow_shared_evidence=allow_shared_evidence,
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
                path="tests/test_flowpilot_router_runtime_startup_daemon.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_startup_daemon",
                test_kind=HAPPY,
                covers=("startup.run_isolation_and_activation",),
            ),
            _evidence(
                "startup.negative.waits_for_answers",
                test_name="test_startup_waits_for_answers_before_banner_or_controller",
                path="tests/test_flowpilot_router_runtime_startup_daemon.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_startup_daemon",
                test_kind=NEGATIVE,
                covers=("startup.questions.pause_before_work",),
            ),
            _evidence(
                "startup.happy.answer_boundary",
                test_name="test_record_startup_answers_accepts_ai_interpretation_with_reviewer_receipt",
                path="tests/test_flowpilot_router_runtime_startup_daemon.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_startup_daemon",
                test_kind=HAPPY,
                covers=("startup.questions.pause_before_work",),
            ),
            _evidence(
                "startup.failure.activation_requires_reviewer",
                test_name="test_startup_activation_requires_reviewer_facts_before_work",
                path="tests/test_flowpilot_router_runtime_startup_daemon.py",
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
                path="tests/test_flowpilot_router_runtime_ack_return.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_ack_return",
                test_kind=EDGE,
                covers=("ack.return_wait_preconsumption",),
            ),
            _evidence(
                "ack.failure.incomplete_bundle",
                test_name="test_record_external_event_does_not_preconsume_incomplete_bundle_ack",
                path="tests/test_flowpilot_router_runtime_ack_return.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_ack_return",
                test_kind=FAILURE,
                covers=("ack.return_wait_preconsumption",),
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
                path="tests/test_flowpilot_router_runtime_route_mutation.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_route_mutation",
                test_kind=HAPPY,
                covers=("route_mutation.topology_and_recheck",),
            ),
            _evidence(
                "route_mutation.negative.required_preconditions",
                test_name="test_route_mutation_and_final_ledger_have_required_preconditions",
                path="tests/router_runtime/route_mutation.py",
                command="python -m unittest tests.router_runtime.route_mutation.RouteMutationRuntimeTests.test_route_mutation_and_final_ledger_have_required_preconditions",
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
                path="tests/router_runtime/route_mutation.py",
                command="python -m unittest tests.router_runtime.route_mutation.RouteMutationRuntimeTests.test_route_mutation_sibling_branch_replacement_blocks_old_sibling_proof",
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
                path="tests/test_flowpilot_router_runtime_terminal.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_terminal",
                test_kind=HAPPY,
                covers=("terminal.final_ledger_and_backward_replay",),
            ),
            _evidence(
                "terminal.negative.final_ledger_sources",
                test_name="test_final_ledger_rejects_missing_source_of_truth_entries_and_contract_replay",
                path="tests/test_flowpilot_router_runtime_terminal.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_terminal",
                test_kind=NEGATIVE,
                covers=("terminal.final_ledger_and_backward_replay",),
            ),
            _evidence(
                "closure.failure.dirty_defect_ledger",
                test_name="test_terminal_closure_blocks_dirty_defect_ledger_after_terminal_replay",
                path="tests/test_flowpilot_router_runtime_closure.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_closure",
                test_kind=FAILURE,
                covers=("closure.dirty_ledgers_block_completion",),
            ),
            _evidence(
                "resume.happy.loads_state",
                test_name="test_resume_reentry_loads_state_before_resume_cards",
                path="tests/test_flowpilot_router_runtime_resume.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_resume",
                test_kind=HAPPY,
                covers=("resume.current_run_reentry",),
            ),
            _evidence(
                "resume.failure.ambiguous_state",
                test_name="test_resume_ambiguous_state_blocks_continue_without_recovery_evidence",
                path="tests/test_flowpilot_router_runtime_resume.py",
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
                path="tests/test_flowpilot_router_runtime_packets.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_packets",
                test_kind=HAPPY,
                covers=("router_loop.packet_result_review_loop",),
            ),
            _evidence(
                "router_loop.failure.reviewer_audit",
                test_name="test_current_node_completion_requires_reviewer_passed_packet_audit",
                path="tests/test_flowpilot_router_runtime_packets.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_packets",
                test_kind=FAILURE,
                covers=("router_loop.packet_result_review_loop",),
            ),
            _evidence(
                "daemon.happy.formal_startup",
                test_name="test_formal_startup_starts_router_daemon_before_controller_core",
                path="tests/test_flowpilot_router_runtime_startup_daemon.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_startup_daemon",
                test_kind=HAPPY,
                covers=("daemon.lock_status_and_queue_progress",),
            ),
            _evidence(
                "daemon.edge.fresh_lock_wait",
                test_name="test_router_daemon_waits_on_fresh_scheduler_write_lock_before_error",
                path="tests/test_flowpilot_router_runtime_startup_daemon.py",
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


def build_report() -> dict[str, Any]:
    per_plan = [_plan_report(entry) for entry in build_alignment_plan_entries()]
    known_bad = [_known_bad_report(case) for case in _known_bad_cases()]
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
    alignment_ok = all(plan["ok"] for plan in per_plan)
    known_bad_ok = all(case["ok"] for case in known_bad)
    return {
        "ok": alignment_ok and known_bad_ok,
        "result_type": "flowpilot_model_test_alignment",
        "alignment_ok": alignment_ok,
        "known_bad_ok": known_bad_ok,
        "plan_count": len(per_plan),
        "families": [plan["family"] for plan in per_plan],
        "findings": findings,
        "finding_counts": _finding_counts(findings),
        "per_plan": per_plan,
        "known_bad_sanity_checks": known_bad,
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
