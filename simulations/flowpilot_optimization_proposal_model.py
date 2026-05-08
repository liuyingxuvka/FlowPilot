"""FlowGuard model for proposed FlowPilot control-plane optimizations.

Risk intent brief:
- Evaluate speed-oriented protocol proposals before any runtime or prompt-card
  change lands.
- Protect harms: losing six live roles, silently introducing light mode,
  letting Controller read bodies or originate evidence, replacing PM/reviewer/
  officer judgement with router proofs, advancing after partial parallel gates,
  freezing merged artifacts too early, or closing terminal lifecycle before the
  final ledger/replay contract is complete.
- Modeled state and side effects: controller authority receipt, system-card
  bundle receipts, packet ledger relay transactions, mechanical proof scope,
  parallel gate joins, PM artifact merging, clean-pass auto advancement, and
  terminal lifecycle cleanup.
- Hard invariants: optimizations may reduce handoffs or critical path depth
  only when every role-scoped judgement, packet/open/hash receipt, source-of-
  truth artifact, final ledger, and terminal backward replay remains present.
- Blindspot: this is a proposal model. It does not claim the current router
  runtime already implements these optimized paths; implementation still needs
  runtime-specific tests after any later code change.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


BASELINE_HANDOFF_STEPS = 44
BASELINE_CRITICAL_PATH_TICKS = 44


@dataclass(frozen=True)
class Tick:
    """One abstract proposal-evaluation tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | complete
    profile: str = "none"  # none | baseline | phase1 | phase2 | phase3

    handoff_steps: int = 0
    critical_path_ticks: int = 0

    six_roles_live: bool = False
    lazy_spawn_used: bool = False
    light_mode_used: bool = False
    pm_ownership_kept: bool = False
    reviewer_judgement_kept: bool = False
    process_officer_judgement_kept: bool = False
    product_officer_judgement_kept: bool = False
    child_skill_gate_evidence_obligations_kept: bool = False

    controller_core_delivered: bool = False
    pm_reset_message_used: bool = False
    router_owned_controller_receipt: bool = False
    controller_role_confirmed: bool = False
    controller_policy_hash_recorded: bool = False
    startup_reviewer_fact_check_kept: bool = False
    startup_reviewer_external_facts_checked: bool = False

    controller_envelope_only: bool = False
    controller_read_sealed_body: bool = False
    controller_originated_project_evidence: bool = False
    sealed_body_boundary_kept: bool = False

    same_role_card_bundle_used: bool = False
    cross_role_bundle_used: bool = False
    manifest_batch_checked: bool = False
    per_card_ledger_entries_kept: bool = False
    card_ids_hashes_paths_recorded: bool = False

    packet_ledger_relay_transaction_used: bool = False
    packet_ledger_check_receipt: bool = False
    packet_delivery_recorded: bool = False
    target_open_receipt_recorded: bool = False
    result_return_recorded: bool = False
    reviewer_result_open_receipt_recorded: bool = False
    role_identity_checked: bool = False
    body_hash_verified: bool = False

    router_mechanical_proof_used: bool = False
    router_mechanical_proof_trusted_source: bool = False
    router_mechanical_proof_file_backed: bool = False
    router_mechanical_proof_hash_current: bool = False
    reviewer_replacement_scope_mechanical_only: bool = False
    proof_replaces_semantic_review: bool = False
    self_attested_ai_claims_used_as_proof: bool = False

    parallel_gate_checks_used: bool = False
    product_architecture_reviewer_passed: bool = False
    product_architecture_officer_passed: bool = False
    root_contract_reviewer_passed: bool = False
    root_contract_officer_passed: bool = False
    child_manifest_reviewer_passed: bool = False
    child_manifest_process_officer_passed: bool = False
    child_manifest_product_officer_passed: bool = False
    route_reviewer_passed: bool = False
    route_process_officer_passed: bool = False
    route_product_officer_passed: bool = False
    pm_waited_for_all_parallel_passes: bool = False
    advanced_after_first_parallel_pass: bool = False

    artifact_merge_used: bool = False
    merged_artifact_has_typed_sections: bool = False
    merged_artifact_responsibilities_separate: bool = False
    merged_artifact_required_fields_complete: bool = False
    root_contract_freeze_separate: bool = False
    node_acceptance_plan_kept: bool = False
    current_node_packet_draft_kept: bool = False
    evidence_quality_kept: bool = False
    evidence_quality_reviewer_passed: bool = False
    final_ledger_source_of_truth_kept: bool = False
    final_ledger_after_evidence_quality: bool = False

    clean_pass_auto_advance_used: bool = False
    pm_clean_pass_preauthorized: bool = False
    all_required_gates_passed: bool = False
    blockers_empty: bool = False
    auto_advance_mechanical_next_only: bool = False
    route_mutation_pending: bool = False
    quality_judgement_pending: bool = False

    terminal_lifecycle_router_owned: bool = False
    pm_closure_approved: bool = False
    terminal_backward_replay_passed: bool = False
    terminal_ledger_clean: bool = False
    lifecycle_cleanup_after_closure: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _full_strength_base(**changes: object) -> State:
    return replace(
        State(
            status="running",
            six_roles_live=True,
            pm_ownership_kept=True,
            reviewer_judgement_kept=True,
            process_officer_judgement_kept=True,
            product_officer_judgement_kept=True,
            child_skill_gate_evidence_obligations_kept=True,
            controller_core_delivered=True,
            controller_role_confirmed=True,
            startup_reviewer_fact_check_kept=True,
            startup_reviewer_external_facts_checked=True,
            controller_envelope_only=True,
            sealed_body_boundary_kept=True,
            all_required_gates_passed=True,
            blockers_empty=True,
            node_acceptance_plan_kept=True,
            current_node_packet_draft_kept=True,
            evidence_quality_kept=True,
            evidence_quality_reviewer_passed=True,
            final_ledger_source_of_truth_kept=True,
            final_ledger_after_evidence_quality=True,
            pm_closure_approved=True,
            terminal_backward_replay_passed=True,
            terminal_ledger_clean=True,
            lifecycle_cleanup_after_closure=True,
        ),
        **changes,
    )


def baseline_state() -> State:
    return _full_strength_base(
        profile="baseline",
        handoff_steps=BASELINE_HANDOFF_STEPS,
        critical_path_ticks=BASELINE_CRITICAL_PATH_TICKS,
        pm_reset_message_used=True,
        controller_policy_hash_recorded=True,
        packet_ledger_check_receipt=True,
        packet_delivery_recorded=True,
        target_open_receipt_recorded=True,
        result_return_recorded=True,
        reviewer_result_open_receipt_recorded=True,
        role_identity_checked=True,
        body_hash_verified=True,
        product_architecture_reviewer_passed=True,
        product_architecture_officer_passed=True,
        root_contract_reviewer_passed=True,
        root_contract_officer_passed=True,
        child_manifest_reviewer_passed=True,
        child_manifest_process_officer_passed=True,
        child_manifest_product_officer_passed=True,
        route_reviewer_passed=True,
        route_process_officer_passed=True,
        route_product_officer_passed=True,
        pm_waited_for_all_parallel_passes=True,
        root_contract_freeze_separate=True,
    )


def safe_phase1_state() -> State:
    return _full_strength_base(
        profile="phase1",
        handoff_steps=34,
        critical_path_ticks=34,
        router_owned_controller_receipt=True,
        controller_policy_hash_recorded=True,
        same_role_card_bundle_used=True,
        manifest_batch_checked=True,
        per_card_ledger_entries_kept=True,
        card_ids_hashes_paths_recorded=True,
        packet_ledger_relay_transaction_used=True,
        packet_ledger_check_receipt=True,
        packet_delivery_recorded=True,
        target_open_receipt_recorded=True,
        result_return_recorded=True,
        reviewer_result_open_receipt_recorded=True,
        role_identity_checked=True,
        body_hash_verified=True,
        router_mechanical_proof_used=True,
        router_mechanical_proof_trusted_source=True,
        router_mechanical_proof_file_backed=True,
        router_mechanical_proof_hash_current=True,
        reviewer_replacement_scope_mechanical_only=True,
        product_architecture_reviewer_passed=True,
        product_architecture_officer_passed=True,
        root_contract_reviewer_passed=True,
        root_contract_officer_passed=True,
        child_manifest_reviewer_passed=True,
        child_manifest_process_officer_passed=True,
        child_manifest_product_officer_passed=True,
        route_reviewer_passed=True,
        route_process_officer_passed=True,
        route_product_officer_passed=True,
        pm_waited_for_all_parallel_passes=True,
        root_contract_freeze_separate=True,
    )


def safe_phase2_state() -> State:
    return replace(
        safe_phase1_state(),
        profile="phase2",
        handoff_steps=34,
        critical_path_ticks=27,
        parallel_gate_checks_used=True,
        pm_waited_for_all_parallel_passes=True,
    )


def guarded_phase3_state() -> State:
    return replace(
        safe_phase2_state(),
        profile="phase3",
        handoff_steps=30,
        critical_path_ticks=24,
        artifact_merge_used=True,
        merged_artifact_has_typed_sections=True,
        merged_artifact_responsibilities_separate=True,
        merged_artifact_required_fields_complete=True,
        root_contract_freeze_separate=True,
        clean_pass_auto_advance_used=True,
        pm_clean_pass_preauthorized=True,
        auto_advance_mechanical_next_only=True,
        terminal_lifecycle_router_owned=True,
    )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "complete":
        return
    if state.status == "new":
        yield Transition("select_baseline_full_strength_flow", baseline_state())
        yield Transition("select_phase1_mechanical_receipt_fold", safe_phase1_state())
        yield Transition("select_phase2_parallel_gate_join", safe_phase2_state())
        yield Transition("select_phase3_guarded_artifact_and_clean_pass_fold", guarded_phase3_state())
        return
    yield Transition("proposal_profile_evaluation_completed", replace(state, status="complete"))


class OptimizationProposalStep:
    """Model one optimization proposal transition.

    Input x State -> Set(Output x State)
    reads: proposed optimization profile, role evidence, packet receipts,
    proof scope, gate pass state, final ledger state
    writes: one selected proposal profile or terminal evaluation status
    idempotency: facts are monotonic; no transition removes role evidence
    """

    name = "OptimizationProposalStep"
    input_description = "FlowPilot optimization proposal tick"
    output_description = "one proposal profile transition"
    reads = (
        "profile",
        "role_evidence",
        "packet_receipts",
        "proof_scope",
        "parallel_gate_status",
        "final_ledger_status",
    )
    writes = ("proposal_profile", "handoff_metrics", "terminal_status")
    idempotency = "monotonic proposal facts"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def _all_parallel_gate_passes(state: State) -> bool:
    return (
        state.product_architecture_reviewer_passed
        and state.product_architecture_officer_passed
        and state.root_contract_reviewer_passed
        and state.root_contract_officer_passed
        and state.child_manifest_reviewer_passed
        and state.child_manifest_process_officer_passed
        and state.child_manifest_product_officer_passed
        and state.route_reviewer_passed
        and state.route_process_officer_passed
        and state.route_product_officer_passed
    )


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status == "new":
        return failures
    if state.lazy_spawn_used or state.light_mode_used or not state.six_roles_live:
        failures.append("formal FlowPilot optimization used lazy roles, light mode, or fewer than six live roles")
    if not (
        state.pm_ownership_kept
        and state.reviewer_judgement_kept
        and state.process_officer_judgement_kept
        and state.product_officer_judgement_kept
    ):
        failures.append("role judgement ownership was weakened by an optimization")
    if not state.child_skill_gate_evidence_obligations_kept:
        failures.append("child-skill gate evidence obligations were dropped")
    if state.controller_read_sealed_body or state.controller_originated_project_evidence:
        failures.append("Controller read sealed body or originated project evidence")
    if not state.controller_envelope_only or not state.sealed_body_boundary_kept:
        failures.append("Controller envelope-only or sealed-body boundary was not preserved")

    if state.router_owned_controller_receipt and not (
        state.controller_core_delivered
        and state.controller_role_confirmed
        and state.controller_policy_hash_recorded
        and state.startup_reviewer_fact_check_kept
        and state.startup_reviewer_external_facts_checked
    ):
        failures.append("router-owned controller receipt lacked core delivery, policy hash, role confirmation, or startup reviewer fact check")
    if not (state.router_owned_controller_receipt or state.pm_reset_message_used):
        failures.append("Controller role confirmation had neither PM reset nor router-owned receipt authority")

    if state.same_role_card_bundle_used and not (
        not state.cross_role_bundle_used
        and state.manifest_batch_checked
        and state.per_card_ledger_entries_kept
        and state.card_ids_hashes_paths_recorded
    ):
        failures.append("system-card bundle lost same-role, manifest batch, per-card ledger, or hash/path evidence")

    if state.packet_ledger_relay_transaction_used and not (
        state.packet_ledger_check_receipt
        and state.packet_delivery_recorded
        and state.target_open_receipt_recorded
        and state.result_return_recorded
        and state.reviewer_result_open_receipt_recorded
        and state.role_identity_checked
        and state.body_hash_verified
    ):
        failures.append("packet ledger relay transaction skipped ledger, delivery, open, result, role, or hash evidence")

    if state.router_mechanical_proof_used and not (
        state.router_mechanical_proof_trusted_source
        and state.router_mechanical_proof_file_backed
        and state.router_mechanical_proof_hash_current
        and state.reviewer_replacement_scope_mechanical_only
        and not state.proof_replaces_semantic_review
        and not state.self_attested_ai_claims_used_as_proof
    ):
        failures.append("router-owned proof was not trusted, file-backed, current-hash, mechanical-only, or non-self-attested")

    if state.parallel_gate_checks_used and not (
        _all_parallel_gate_passes(state)
        and state.pm_waited_for_all_parallel_passes
        and not state.advanced_after_first_parallel_pass
    ):
        failures.append("parallel gate optimization advanced before every reviewer/officer pass joined")

    if state.artifact_merge_used and not (
        state.merged_artifact_has_typed_sections
        and state.merged_artifact_responsibilities_separate
        and state.merged_artifact_required_fields_complete
        and state.root_contract_freeze_separate
        and state.node_acceptance_plan_kept
        and state.current_node_packet_draft_kept
        and state.evidence_quality_kept
        and state.evidence_quality_reviewer_passed
        and state.final_ledger_source_of_truth_kept
        and state.final_ledger_after_evidence_quality
    ):
        failures.append("artifact merge collapsed responsibility, freeze points, required sections, node packet, evidence quality, or final ledger order")

    if state.clean_pass_auto_advance_used and not (
        state.pm_clean_pass_preauthorized
        and state.all_required_gates_passed
        and state.blockers_empty
        and state.auto_advance_mechanical_next_only
        and not state.route_mutation_pending
        and not state.quality_judgement_pending
    ):
        failures.append("clean-pass auto advance was used outside mechanical, preauthorized, all-pass, blocker-free state")

    if state.terminal_lifecycle_router_owned and not (
        state.pm_closure_approved
        and state.terminal_backward_replay_passed
        and state.terminal_ledger_clean
        and state.lifecycle_cleanup_after_closure
    ):
        failures.append("router-owned terminal lifecycle cleanup ran before PM closure, final replay, clean ledger, or closure ordering")

    if state.status == "complete" and not (
        state.all_required_gates_passed
        and state.pm_closure_approved
        and state.terminal_backward_replay_passed
        and state.terminal_ledger_clean
        and state.final_ledger_source_of_truth_kept
    ):
        failures.append("proposal profile completed without the full final closure contract")

    if state.handoff_steps > BASELINE_HANDOFF_STEPS or state.critical_path_ticks > BASELINE_CRITICAL_PATH_TICKS:
        failures.append("optimization profile increased handoff or critical-path cost above baseline")

    return failures


def proposal_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_optimization_preserves_full_strength",
        description=(
            "Control-plane optimization may reduce handoffs only when it "
            "preserves six-role authority, sealed-body isolation, independent "
            "semantic review, packet receipts, and final closure gates."
        ),
        predicate=proposal_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


def build_workflow() -> Workflow:
    return Workflow((OptimizationProposalStep(),), name="flowpilot_optimization_proposal")


def is_terminal(state: State) -> bool:
    return state.status == "complete"


def is_success(state: State) -> bool:
    return state.status == "complete" and not invariant_failures(state)


def hazard_states() -> dict[str, State]:
    safe = guarded_phase3_state()
    return {
        "lazy_six_roles": replace(safe, lazy_spawn_used=True, six_roles_live=False),
        "small_task_light_mode": replace(safe, light_mode_used=True),
        "controller_reads_sealed_body": replace(safe, controller_read_sealed_body=True),
        "router_reset_missing_policy_hash": replace(
            safe,
            router_owned_controller_receipt=True,
            pm_reset_message_used=False,
            controller_policy_hash_recorded=False,
        ),
        "router_reset_without_startup_fact_review": replace(
            safe,
            router_owned_controller_receipt=True,
            startup_reviewer_fact_check_kept=False,
        ),
        "card_bundle_cross_role": replace(safe, same_role_card_bundle_used=True, cross_role_bundle_used=True),
        "card_bundle_missing_per_card_ledger": replace(safe, same_role_card_bundle_used=True, per_card_ledger_entries_kept=False),
        "ledger_relay_missing_result_open_receipt": replace(
            safe,
            packet_ledger_relay_transaction_used=True,
            reviewer_result_open_receipt_recorded=False,
        ),
        "ledger_relay_missing_hash": replace(
            safe,
            packet_ledger_relay_transaction_used=True,
            body_hash_verified=False,
        ),
        "mechanical_proof_replaces_semantic_review": replace(
            safe,
            router_mechanical_proof_used=True,
            proof_replaces_semantic_review=True,
        ),
        "mechanical_proof_self_attested": replace(
            safe,
            router_mechanical_proof_used=True,
            self_attested_ai_claims_used_as_proof=True,
        ),
        "parallel_gate_first_pass_advance": replace(
            safe,
            parallel_gate_checks_used=True,
            pm_waited_for_all_parallel_passes=False,
            advanced_after_first_parallel_pass=True,
        ),
        "parallel_gate_missing_product_officer": replace(
            safe,
            parallel_gate_checks_used=True,
            child_manifest_product_officer_passed=False,
        ),
        "artifact_merge_collapses_responsibility": replace(
            safe,
            artifact_merge_used=True,
            merged_artifact_responsibilities_separate=False,
        ),
        "artifact_merge_early_root_contract_freeze": replace(
            safe,
            artifact_merge_used=True,
            root_contract_freeze_separate=False,
        ),
        "artifact_merge_without_evidence_quality_review": replace(
            safe,
            artifact_merge_used=True,
            evidence_quality_reviewer_passed=False,
        ),
        "auto_advance_without_pm_preauthorization": replace(
            safe,
            clean_pass_auto_advance_used=True,
            pm_clean_pass_preauthorized=False,
        ),
        "auto_advance_during_route_mutation": replace(
            safe,
            clean_pass_auto_advance_used=True,
            route_mutation_pending=True,
        ),
        "auto_advance_replaces_quality_judgement": replace(
            safe,
            clean_pass_auto_advance_used=True,
            quality_judgement_pending=True,
        ),
        "terminal_lifecycle_before_pm_closure": replace(
            safe,
            terminal_lifecycle_router_owned=True,
            pm_closure_approved=False,
        ),
        "terminal_lifecycle_before_final_replay": replace(
            safe,
            terminal_lifecycle_router_owned=True,
            terminal_backward_replay_passed=False,
        ),
    }


def proposal_catalog() -> dict[str, dict[str, object]]:
    return {
        "phase1_mechanical_receipts": {
            "profile": safe_phase1_state(),
            "interpretation": "modeled_safe_under_guards",
            "scope": "router-owned controller receipt, same-role system-card bundle, manifest batch receipt, ledger+relay transaction, mechanical proof",
            "runtime_readiness": "model_only_until_router_startup_and_delivery_paths_are_updated",
        },
        "phase2_parallel_gates": {
            "profile": safe_phase2_state(),
            "interpretation": "conditional_safe_under_join_guards",
            "scope": "parallel reviewer/officer checks with PM waiting for every required pass",
            "runtime_readiness": "needs_wait_join_runtime_model_and tests_before_implementation",
        },
        "phase3_artifact_clean_pass": {
            "profile": guarded_phase3_state(),
            "interpretation": "conditional_safe_with_strict_artifact_and_auto_advance_guards",
            "scope": "typed artifact merge, clean-pass mechanical auto-advance, terminal lifecycle cleanup after closure",
            "runtime_readiness": "highest_risk_model_only_until_artifact_equivalence_and_terminal_lifecycle_tests_exist",
        },
    }
