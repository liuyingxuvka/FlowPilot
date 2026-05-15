"""FlowGuard model for the FlowPilot role output runtime.

Risk intent brief:
- Generalize the packet-runtime "clock-in" idea to formal role outputs while
  preserving sealed-body boundaries and removing Controller as the return
  receiver for completed work.
- Prevent hand-written PM/reviewer/officer/worker reports from reaching the
  router with missing required fields, missing explicit empty arrays, wrong
  role ownership, stale hashes, or body leakage in Controller-visible payloads.
- Keep semantic sufficiency out of the runtime: the runtime validates contract
  mechanics and records receipts; PM/reviewer/officer judgment still owns
  content quality.
- Avoid turning mechanical metadata gaps into PM repair loops when the original
  role can safely re-submit through the runtime.
- Let the runtime submit compact role-output envelopes directly to Router while
  keeping full audit detail in receipts and ledgers and leaving Controller to
  wait for Router status.
- Let route-declared quality packs appear as generic report checklist rows
  without teaching the runtime UI, desktop, localization, or product semantics.
- Treat the contract registry as the source of truth for runtime-backed role
  outputs so contracts, output types, allowed roles, aliases, and Router events
  cannot drift across separate manually maintained lists.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_PM_RESUME = "valid_pm_resume_decision"
VALID_STARTUP_ACTIVATION_APPROVAL = "valid_startup_activation_approval"
VALID_GATE_DECISION = "valid_gate_decision"
VALID_REVIEWER_REPORT = "valid_reviewer_report"
VALID_CONTROLLER_BOUNDARY_CONFIRMATION = "valid_controller_boundary_confirmation"
MISSING_REGISTRY_RUNTIME_BINDING = "missing_registry_runtime_binding"
REGISTRY_CONTRACT_ID_MISMATCH = "registry_contract_id_mismatch"
REGISTRY_ALLOWED_ROLE_MISMATCH = "registry_allowed_role_mismatch"
REGISTRY_ROUTER_EVENT_MISSING = "registry_router_event_missing"
UNREGISTERED_RUNTIME_OUTPUT_TYPE = "unregistered_runtime_output_type"
BROKEN_COMPAT_OUTPUT_ALIAS = "broken_compat_output_alias"
MISSING_RUNTIME_RECEIPT = "missing_runtime_receipt"
MISSING_REQUIRED_FIELD = "missing_required_field"
MISSING_EXPLICIT_EMPTY_ARRAY = "missing_explicit_empty_array"
WRONG_ROLE = "wrong_role"
STALE_BODY_HASH = "stale_body_hash"
INLINE_BODY_LEAK = "inline_body_leak"
CONTROLLER_READS_BODY = "controller_reads_body"
CONTROLLER_INTERMEDIATES_OUTPUT = "controller_intermediates_output"
SEMANTIC_AUTO_APPROVAL = "semantic_auto_approval"
MISSING_QUALITY_PACK_CHECK = "missing_quality_pack_check"
PACK_SPECIFIC_RUNTIME_JUDGMENT = "pack_specific_runtime_judgment"

VALID_SCENARIOS = (
    VALID_PM_RESUME,
    VALID_STARTUP_ACTIVATION_APPROVAL,
    VALID_GATE_DECISION,
    VALID_REVIEWER_REPORT,
    VALID_CONTROLLER_BOUNDARY_CONFIRMATION,
)

NEGATIVE_SCENARIOS = (
    MISSING_REGISTRY_RUNTIME_BINDING,
    REGISTRY_CONTRACT_ID_MISMATCH,
    REGISTRY_ALLOWED_ROLE_MISMATCH,
    REGISTRY_ROUTER_EVENT_MISSING,
    UNREGISTERED_RUNTIME_OUTPUT_TYPE,
    BROKEN_COMPAT_OUTPUT_ALIAS,
    MISSING_RUNTIME_RECEIPT,
    MISSING_REQUIRED_FIELD,
    MISSING_EXPLICIT_EMPTY_ARRAY,
    WRONG_ROLE,
    STALE_BODY_HASH,
    INLINE_BODY_LEAK,
    CONTROLLER_READS_BODY,
    CONTROLLER_INTERMEDIATES_OUTPUT,
    SEMANTIC_AUTO_APPROVAL,
    MISSING_QUALITY_PACK_CHECK,
    PACK_SPECIFIC_RUNTIME_JUDGMENT,
)

SCENARIOS = (*VALID_SCENARIOS, *NEGATIVE_SCENARIOS)

ROLE_REISSUE_REASONS = {
    "missing_runtime_receipt",
    "missing_required_field",
    "missing_explicit_empty_array",
    "stale_body_hash",
    "missing_quality_pack_check",
}

PM_REVIEW_REASONS = {
    "wrong_role",
    "inline_body_leak",
    "controller_intermediated_output",
    "controller_read_body",
    "runtime_attempted_semantic_approval",
    "runtime_attempted_pack_specific_judgment",
}

PROTOCOL_REPAIR_REASONS = {
    "missing_registry_runtime_binding",
    "registry_contract_id_mismatch",
    "registry_allowed_role_mismatch",
    "registry_router_event_missing",
    "unregistered_runtime_output_type",
    "broken_compat_output_alias",
}


@dataclass(frozen=True)
class Tick:
    """One role-output runtime transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class OutputContract:
    output_type: str
    contract_id: str
    allowed_role: str
    requires_explicit_empty_arrays: bool
    router_event: str
    alias_output_types: tuple[str, ...] = ()


PM_RESUME_CONTRACT = OutputContract(
    output_type="pm_resume_recovery_decision",
    contract_id="flowpilot.output_contract.pm_resume_decision.v1",
    allowed_role="project_manager",
    requires_explicit_empty_arrays=True,
    router_event="pm_resume_recovery_decision_returned",
    alias_output_types=("pm_resume_decision",),
)

STARTUP_ACTIVATION_APPROVAL_CONTRACT = OutputContract(
    output_type="pm_startup_activation_approval",
    contract_id="flowpilot.output_contract.pm_startup_activation_approval.v1",
    allowed_role="project_manager",
    requires_explicit_empty_arrays=False,
    router_event="pm_approves_startup_activation",
)

GATE_DECISION_CONTRACT = OutputContract(
    output_type="gate_decision",
    contract_id="flowpilot.output_contract.gate_decision.v1",
    allowed_role="human_like_reviewer",
    requires_explicit_empty_arrays=False,
    router_event="role_records_gate_decision",
)

REVIEWER_REPORT_CONTRACT = OutputContract(
    output_type="reviewer_review_report",
    contract_id="flowpilot.output_contract.reviewer_review_report.v1",
    allowed_role="human_like_reviewer",
    requires_explicit_empty_arrays=True,
    router_event="reviewer_reports_current_node_review",
)

CONTROLLER_BOUNDARY_CONFIRMATION_CONTRACT = OutputContract(
    output_type="controller_boundary_confirmation",
    contract_id="flowpilot.output_contract.controller_boundary_confirmation.v1",
    allowed_role="controller",
    requires_explicit_empty_arrays=False,
    router_event="",
)

CONTRACTS_BY_SCENARIO = {
    VALID_PM_RESUME: PM_RESUME_CONTRACT,
    VALID_STARTUP_ACTIVATION_APPROVAL: STARTUP_ACTIVATION_APPROVAL_CONTRACT,
    VALID_GATE_DECISION: GATE_DECISION_CONTRACT,
    VALID_REVIEWER_REPORT: REVIEWER_REPORT_CONTRACT,
    VALID_CONTROLLER_BOUNDARY_CONFIRMATION: CONTROLLER_BOUNDARY_CONFIRMATION_CONTRACT,
    MISSING_REGISTRY_RUNTIME_BINDING: STARTUP_ACTIVATION_APPROVAL_CONTRACT,
    REGISTRY_CONTRACT_ID_MISMATCH: STARTUP_ACTIVATION_APPROVAL_CONTRACT,
    REGISTRY_ALLOWED_ROLE_MISMATCH: STARTUP_ACTIVATION_APPROVAL_CONTRACT,
    REGISTRY_ROUTER_EVENT_MISSING: STARTUP_ACTIVATION_APPROVAL_CONTRACT,
    UNREGISTERED_RUNTIME_OUTPUT_TYPE: STARTUP_ACTIVATION_APPROVAL_CONTRACT,
    BROKEN_COMPAT_OUTPUT_ALIAS: PM_RESUME_CONTRACT,
    MISSING_RUNTIME_RECEIPT: PM_RESUME_CONTRACT,
    MISSING_REQUIRED_FIELD: PM_RESUME_CONTRACT,
    MISSING_EXPLICIT_EMPTY_ARRAY: PM_RESUME_CONTRACT,
    WRONG_ROLE: PM_RESUME_CONTRACT,
    STALE_BODY_HASH: PM_RESUME_CONTRACT,
    INLINE_BODY_LEAK: PM_RESUME_CONTRACT,
    CONTROLLER_READS_BODY: PM_RESUME_CONTRACT,
    CONTROLLER_INTERMEDIATES_OUTPUT: PM_RESUME_CONTRACT,
    SEMANTIC_AUTO_APPROVAL: GATE_DECISION_CONTRACT,
    MISSING_QUALITY_PACK_CHECK: REVIEWER_REPORT_CONTRACT,
    PACK_SPECIFIC_RUNTIME_JUDGMENT: REVIEWER_REPORT_CONTRACT,
}


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"
    output_type: str = ""
    contract_id: str = ""
    allowed_role: str = ""
    submitting_role: str = ""
    router_event: str = ""

    registry_runtime_binding_present: bool = False
    registry_contract_id_matches_runtime: bool = False
    registry_allowed_roles_match_runtime: bool = False
    registry_router_event_exists: bool = False
    runtime_output_type_declared_by_registry: bool = False
    compat_output_alias_valid: bool = True

    runtime_prepared_skeleton: bool = False
    runtime_required_fields_known: bool = False
    runtime_progress_status_initialized: bool = False
    progress_prompt_included: bool = False
    role_authored_body: bool = False
    required_fields_present: bool = False
    explicit_empty_arrays_present: bool = False
    fixed_values_valid: bool = False
    role_is_allowed: bool = False

    runtime_receipt_written: bool = False
    body_hash_verified: bool = False
    envelope_generated_by_runtime: bool = False
    envelope_leaks_body: bool = False
    controller_reads_body: bool = False
    controller_intermediates_output: bool = False
    direct_router_submission: bool = False
    router_receives_role_output_envelope: bool = False
    controller_waits_router_status: bool = False
    router_ready_evidence_available: bool = False
    controller_reentered_router_before_foreground_wait: bool = False
    controller_foreground_waits_role_after_router_ready: bool = False
    compact_envelope_refs_used: bool = False
    progress_updates_runtime_written: bool = True
    progress_value_numeric: bool = True
    progress_value_nonnegative: bool = True
    progress_message_metadata_only: bool = True
    progress_visibility_grant: str = "single_status_packet"  # single_status_packet | output_dir | sealed_body
    progress_used_for_semantic_decision: bool = False

    semantic_review_required: bool = True
    runtime_claimed_semantic_approval: bool = False
    quality_packs_declared: bool = False
    quality_pack_checks_present: bool = False
    runtime_claimed_pack_specific_judgment: bool = False

    router_decision: str = "none"  # none | accept | reject
    router_rejection_reason: str = "none"
    repair_lane: str = "none"  # none | same_role_reissue | pm_review


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


class RoleOutputRuntimeStep:
    """Model one role-output runtime transition.

    Input x State -> Set(Output x State)
    reads: output contract, role identity, runtime receipt, body hash,
    Controller visibility, semantic review boundary, and router decision
    writes: one preparation, validation, envelope, relay, or terminal decision
    idempotency: repeated ticks do not duplicate receipts or terminal decisions.
    """

    name = "RoleOutputRuntimeStep"
    reads = (
        "output_contract",
        "role_identity",
        "role_body",
        "runtime_receipt",
        "controller_visibility",
        "semantic_review_boundary",
        "router_decision",
    )
    writes = (
        "runtime_skeleton",
        "runtime_validation_receipt",
        "runtime_envelope",
        "router_terminal_decision",
    )
    input_description = "role-output runtime tick"
    output_description = "one abstract role-output runtime action"
    idempotency = "repeat ticks do not duplicate runtime receipts or terminal decisions"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def _contract_for(scenario: str) -> OutputContract:
    return CONTRACTS_BY_SCENARIO[scenario]


def _submitting_role_for(scenario: str, contract: OutputContract) -> str:
    if scenario == WRONG_ROLE:
        return "controller"
    return contract.allowed_role


def _has_required_fields(scenario: str) -> bool:
    return scenario != MISSING_REQUIRED_FIELD


def _has_explicit_empty_arrays(scenario: str, contract: OutputContract) -> bool:
    if scenario == MISSING_EXPLICIT_EMPTY_ARRAY and contract.requires_explicit_empty_arrays:
        return False
    return True


def _runtime_receipt_for(scenario: str) -> bool:
    return scenario != MISSING_RUNTIME_RECEIPT


def _body_hash_verified_for(scenario: str) -> bool:
    return scenario != STALE_BODY_HASH


def _envelope_leaks_body_for(scenario: str) -> bool:
    return scenario == INLINE_BODY_LEAK


def _controller_reads_body_for(scenario: str) -> bool:
    return scenario == CONTROLLER_READS_BODY


def _controller_intermediates_output_for(scenario: str) -> bool:
    return scenario == CONTROLLER_INTERMEDIATES_OUTPUT


def _semantic_approval_for(scenario: str) -> bool:
    return scenario == SEMANTIC_AUTO_APPROVAL


def _quality_packs_declared_for(scenario: str) -> bool:
    return scenario in {VALID_REVIEWER_REPORT, MISSING_QUALITY_PACK_CHECK, PACK_SPECIFIC_RUNTIME_JUDGMENT}


def _quality_pack_checks_present_for(scenario: str) -> bool:
    return scenario != MISSING_QUALITY_PACK_CHECK


def _pack_specific_runtime_judgment_for(scenario: str) -> bool:
    return scenario == PACK_SPECIFIC_RUNTIME_JUDGMENT


def _registry_binding_present_for(scenario: str) -> bool:
    return scenario != MISSING_REGISTRY_RUNTIME_BINDING


def _registry_contract_id_matches_for(scenario: str) -> bool:
    return scenario != REGISTRY_CONTRACT_ID_MISMATCH


def _registry_allowed_roles_match_for(scenario: str) -> bool:
    return scenario != REGISTRY_ALLOWED_ROLE_MISMATCH


def _registry_router_event_exists_for(scenario: str) -> bool:
    return scenario != REGISTRY_ROUTER_EVENT_MISSING


def _runtime_output_declared_for(scenario: str) -> bool:
    return scenario != UNREGISTERED_RUNTIME_OUTPUT_TYPE


def _compat_alias_valid_for(scenario: str) -> bool:
    return scenario != BROKEN_COMPAT_OUTPUT_ALIAS


def _router_rejection_reason(state: State) -> str:
    if not state.registry_runtime_binding_present:
        return "missing_registry_runtime_binding"
    if not state.registry_contract_id_matches_runtime:
        return "registry_contract_id_mismatch"
    if not state.registry_allowed_roles_match_runtime:
        return "registry_allowed_role_mismatch"
    if not state.registry_router_event_exists:
        return "registry_router_event_missing"
    if not state.runtime_output_type_declared_by_registry:
        return "unregistered_runtime_output_type"
    if not state.compat_output_alias_valid:
        return "broken_compat_output_alias"
    if not state.runtime_receipt_written:
        return "missing_runtime_receipt"
    if not state.required_fields_present:
        return "missing_required_field"
    if not state.explicit_empty_arrays_present:
        return "missing_explicit_empty_array"
    if not state.role_is_allowed:
        return "wrong_role"
    if not state.body_hash_verified:
        return "stale_body_hash"
    if state.envelope_leaks_body:
        return "inline_body_leak"
    if state.controller_intermediates_output:
        return "controller_intermediated_output"
    if state.controller_reads_body:
        return "controller_read_body"
    if state.runtime_claimed_semantic_approval:
        return "runtime_attempted_semantic_approval"
    if state.quality_packs_declared and not state.quality_pack_checks_present:
        return "missing_quality_pack_check"
    if state.runtime_claimed_pack_specific_judgment:
        return "runtime_attempted_pack_specific_judgment"
    return "none"


def _repair_lane_for(reason: str) -> str:
    if reason in PROTOCOL_REPAIR_REASONS:
        return "protocol_registry_repair"
    if reason in ROLE_REISSUE_REASONS:
        return "same_role_reissue"
    if reason in PM_REVIEW_REASONS:
        return "pm_review"
    return "none"


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return

    if state.scenario == "unset":
        for scenario in SCENARIOS:
            contract = _contract_for(scenario)
            yield Transition(
                f"select_{scenario}",
                replace(
                    state,
                    status="running",
                    scenario=scenario,
                    output_type=contract.output_type,
                    contract_id=contract.contract_id,
                    allowed_role=contract.allowed_role,
                    submitting_role=_submitting_role_for(scenario, contract),
                    router_event=contract.router_event,
                    registry_runtime_binding_present=_registry_binding_present_for(scenario),
                    registry_contract_id_matches_runtime=_registry_contract_id_matches_for(scenario),
                    registry_allowed_roles_match_runtime=_registry_allowed_roles_match_for(scenario),
                    registry_router_event_exists=_registry_router_event_exists_for(scenario),
                    runtime_output_type_declared_by_registry=_runtime_output_declared_for(scenario),
                    compat_output_alias_valid=_compat_alias_valid_for(scenario),
                ),
            )
        return

    if not state.runtime_prepared_skeleton:
        yield Transition(
            "runtime_prepares_contract_skeleton",
            replace(
                state,
                runtime_prepared_skeleton=True,
                runtime_required_fields_known=True,
                runtime_progress_status_initialized=True,
                progress_prompt_included=True,
                quality_packs_declared=_quality_packs_declared_for(state.scenario),
            ),
        )
        return

    if not state.role_authored_body:
        contract = _contract_for(state.scenario)
        yield Transition(
            "role_authors_body_inside_runtime_skeleton",
            replace(
                state,
                role_authored_body=True,
                required_fields_present=_has_required_fields(state.scenario),
                explicit_empty_arrays_present=_has_explicit_empty_arrays(state.scenario, contract),
                fixed_values_valid=True,
                role_is_allowed=state.submitting_role == state.allowed_role,
                quality_pack_checks_present=_quality_pack_checks_present_for(state.scenario),
            ),
        )
        return

    if not state.envelope_generated_by_runtime:
        yield Transition(
            "runtime_validates_writes_receipt_and_envelope",
            replace(
                state,
                runtime_receipt_written=_runtime_receipt_for(state.scenario),
                body_hash_verified=_body_hash_verified_for(state.scenario),
                envelope_generated_by_runtime=True,
                envelope_leaks_body=_envelope_leaks_body_for(state.scenario),
                compact_envelope_refs_used=True,
                runtime_claimed_semantic_approval=_semantic_approval_for(state.scenario),
                runtime_claimed_pack_specific_judgment=_pack_specific_runtime_judgment_for(state.scenario),
            ),
        )
        return

    if not state.direct_router_submission:
        yield Transition(
            "runtime_submits_role_output_directly_to_router",
            replace(
                state,
                controller_reads_body=_controller_reads_body_for(state.scenario),
                controller_intermediates_output=_controller_intermediates_output_for(state.scenario),
                direct_router_submission=True,
                router_receives_role_output_envelope=True,
                controller_waits_router_status=True,
                router_ready_evidence_available=True,
                controller_reentered_router_before_foreground_wait=True,
            ),
        )
        return

    if state.router_decision == "none":
        reason = _router_rejection_reason(state)
        if reason == "none":
            yield Transition(
                "router_accepts_runtime_checked_role_output",
                replace(state, status="accepted", router_decision="accept"),
            )
            return
        yield Transition(
            f"router_rejects_{reason}",
            replace(
                state,
                status="rejected",
                router_decision="reject",
                router_rejection_reason=reason,
                repair_lane=_repair_lane_for(reason),
            ),
        )


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return is_terminal(state)


def accepted_outputs_have_runtime_receipt(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and not state.runtime_receipt_written:
        return InvariantResult.fail("accepted role output without runtime receipt")
    return InvariantResult.pass_()


def accepted_outputs_have_registry_binding(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    if not state.registry_runtime_binding_present:
        return InvariantResult.fail("accepted role output without registry runtime binding")
    if not state.registry_contract_id_matches_runtime:
        return InvariantResult.fail("accepted role output with registry/runtime contract id mismatch")
    if not state.registry_allowed_roles_match_runtime:
        return InvariantResult.fail("accepted role output with registry/runtime allowed role mismatch")
    if not state.registry_router_event_exists:
        return InvariantResult.fail("accepted role output with missing Router event binding")
    if not state.runtime_output_type_declared_by_registry:
        return InvariantResult.fail("accepted runtime output type not declared by registry")
    if not state.compat_output_alias_valid:
        return InvariantResult.fail("accepted role output with broken compatibility output alias")
    return InvariantResult.pass_()


def accepted_outputs_satisfy_mechanical_contract(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    if not state.runtime_prepared_skeleton or not state.runtime_required_fields_known:
        return InvariantResult.fail("accepted role output without contract skeleton")
    if not state.required_fields_present:
        return InvariantResult.fail("accepted role output with missing required field")
    if not state.explicit_empty_arrays_present:
        return InvariantResult.fail("accepted role output with missing explicit empty array")
    if not state.fixed_values_valid:
        return InvariantResult.fail("accepted role output with invalid fixed value")
    if not state.body_hash_verified:
        return InvariantResult.fail("accepted role output with stale body hash")
    return InvariantResult.pass_()


def accepted_outputs_keep_role_boundary(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and (
        not state.role_is_allowed or state.submitting_role != state.allowed_role
    ):
        return InvariantResult.fail("accepted role output from wrong role")
    return InvariantResult.pass_()


def controller_never_reads_role_output_body(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.controller_reads_body:
        return InvariantResult.fail("accepted role output after Controller body read")
    return InvariantResult.pass_()


def accepted_outputs_submit_directly_to_router(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    if not state.direct_router_submission:
        return InvariantResult.fail("accepted role output without direct Router submission")
    if not state.router_receives_role_output_envelope:
        return InvariantResult.fail("accepted role output was not received by Router")
    if not state.controller_waits_router_status:
        return InvariantResult.fail("accepted role output left Controller waiting on a role instead of Router")
    if state.router_ready_evidence_available and not state.controller_reentered_router_before_foreground_wait:
        return InvariantResult.fail("accepted role output left Router-ready evidence unconsumed before foreground wait")
    if state.router_ready_evidence_available and state.controller_foreground_waits_role_after_router_ready:
        return InvariantResult.fail("accepted role output waited on role after Router-ready evidence existed")
    return InvariantResult.pass_()


def controller_never_intermediates_role_output(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.controller_intermediates_output:
        return InvariantResult.fail("accepted role output routed through Controller")
    return InvariantResult.pass_()


def accepted_envelope_is_metadata_only(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.envelope_leaks_body:
        return InvariantResult.fail("accepted role output envelope leaked body content")
    return InvariantResult.pass_()


def runtime_does_not_claim_semantic_approval(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.runtime_claimed_semantic_approval:
        return InvariantResult.fail("role output runtime replaced semantic gate approval")
    if state.status == "accepted" and state.runtime_claimed_pack_specific_judgment:
        return InvariantResult.fail("role output runtime judged quality-pack semantics")
    if state.status == "accepted" and not state.semantic_review_required:
        return InvariantResult.fail("accepted role output removed semantic review requirement")
    return InvariantResult.pass_()


def accepted_envelope_uses_compact_refs(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and not state.compact_envelope_refs_used:
        return InvariantResult.fail("accepted role output lacked compact body/receipt refs")
    return InvariantResult.pass_()


def accepted_outputs_have_default_progress_contract(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    if not state.runtime_progress_status_initialized:
        return InvariantResult.fail("accepted role output without default progress status")
    if not state.progress_prompt_included:
        return InvariantResult.fail("accepted role output without shared progress prompt")
    if state.progress_visibility_grant != "single_status_packet":
        return InvariantResult.fail("role-output progress visibility was wider than status metadata")
    if not state.progress_message_metadata_only:
        return InvariantResult.fail("role-output progress status leaked sealed body content")
    if not state.progress_updates_runtime_written:
        return InvariantResult.fail("role-output progress update bypassed runtime")
    if not (state.progress_value_numeric and state.progress_value_nonnegative):
        return InvariantResult.fail("role-output progress value was not nonnegative numeric")
    if state.progress_used_for_semantic_decision:
        return InvariantResult.fail("role-output progress was used as semantic decision evidence")
    return InvariantResult.pass_()


def declared_quality_packs_have_generic_rows(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.quality_packs_declared and not state.quality_pack_checks_present:
        return InvariantResult.fail("accepted role output omitted declared quality-pack checks")
    return InvariantResult.pass_()


def mechanical_gaps_route_to_role_reissue(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.status == "rejected"
        and state.router_rejection_reason in ROLE_REISSUE_REASONS
        and state.repair_lane != "same_role_reissue"
    ):
        return InvariantResult.fail("mechanical role-output gap escalated beyond same-role reissue")
    return InvariantResult.pass_()


def boundary_violations_route_to_pm_review(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.status == "rejected"
        and state.router_rejection_reason in PM_REVIEW_REASONS
        and state.repair_lane != "pm_review"
    ):
        return InvariantResult.fail("boundary violation did not route to PM review")
    return InvariantResult.pass_()


def registry_binding_violations_route_to_protocol_repair(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.status == "rejected"
        and state.router_rejection_reason in PROTOCOL_REPAIR_REASONS
        and state.repair_lane != "protocol_registry_repair"
    ):
        return InvariantResult.fail("registry binding violation did not route to protocol registry repair")
    return InvariantResult.pass_()


def negative_scenarios_are_rejected(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.scenario in NEGATIVE_SCENARIOS:
        return InvariantResult.fail(f"router accepted negative role-output scenario {state.scenario}")
    if state.status == "rejected" and state.scenario in VALID_SCENARIOS:
        return InvariantResult.fail(f"router rejected valid role-output scenario {state.scenario}")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepted_outputs_have_registry_binding",
        description="Router acceptance requires a registry-backed contract/output type/role/event binding.",
        predicate=accepted_outputs_have_registry_binding,
    ),
    Invariant(
        name="accepted_outputs_have_runtime_receipt",
        description="Router acceptance requires a role-output runtime validation receipt.",
        predicate=accepted_outputs_have_runtime_receipt,
    ),
    Invariant(
        name="accepted_outputs_satisfy_mechanical_contract",
        description="Runtime acceptance requires required fields, explicit arrays, fixed values, and fresh body hash.",
        predicate=accepted_outputs_satisfy_mechanical_contract,
    ),
    Invariant(
        name="accepted_outputs_keep_role_boundary",
        description="Runtime acceptance requires the submitting role to match the output contract.",
        predicate=accepted_outputs_keep_role_boundary,
    ),
    Invariant(
        name="controller_never_reads_role_output_body",
        description="Controller may receive only role-output envelope metadata.",
        predicate=controller_never_reads_role_output_body,
    ),
    Invariant(
        name="accepted_outputs_submit_directly_to_router",
        description="Accepted role outputs are submitted directly to Router; Controller waits for Router status.",
        predicate=accepted_outputs_submit_directly_to_router,
    ),
    Invariant(
        name="controller_never_intermediates_role_output",
        description="Controller must not be the return receiver for completed role-output work.",
        predicate=controller_never_intermediates_role_output,
    ),
    Invariant(
        name="accepted_envelope_is_metadata_only",
        description="Accepted Controller-visible envelopes must not leak role body content.",
        predicate=accepted_envelope_is_metadata_only,
    ),
    Invariant(
        name="runtime_does_not_claim_semantic_approval",
        description="The role-output runtime validates mechanics only and cannot approve semantic sufficiency.",
        predicate=runtime_does_not_claim_semantic_approval,
    ),
    Invariant(
        name="accepted_envelope_uses_compact_refs",
        description="Accepted runtime envelopes use compact body_ref and runtime_receipt_ref metadata.",
        predicate=accepted_envelope_uses_compact_refs,
    ),
    Invariant(
        name="accepted_outputs_have_default_progress_contract",
        description="Accepted role outputs initialize metadata-only progress and prompt roles to maintain it through runtime.",
        predicate=accepted_outputs_have_default_progress_contract,
    ),
    Invariant(
        name="declared_quality_packs_have_generic_rows",
        description="Declared route quality packs are answered through generic rows without pack-specific runtime judgment.",
        predicate=declared_quality_packs_have_generic_rows,
    ),
    Invariant(
        name="mechanical_gaps_route_to_role_reissue",
        description="Missing runtime receipts or mechanical fields should return to the same role, not become PM repair first.",
        predicate=mechanical_gaps_route_to_role_reissue,
    ),
    Invariant(
        name="boundary_violations_route_to_pm_review",
        description="Wrong role or body leakage remains PM-reviewable boundary failure.",
        predicate=boundary_violations_route_to_pm_review,
    ),
    Invariant(
        name="registry_binding_violations_route_to_protocol_repair",
        description="Contract/runtime/router binding drift routes to protocol registry repair.",
        predicate=registry_binding_violations_route_to_protocol_repair,
    ),
    Invariant(
        name="negative_scenarios_are_rejected",
        description="Every invalid role-output runtime scenario must be rejected.",
        predicate=negative_scenarios_are_rejected,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 6


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def build_workflow() -> Workflow:
    return Workflow((RoleOutputRuntimeStep(),), name="flowpilot_role_output_runtime")


def terminal_predicate(_input_obj, state: State, _trace) -> bool:
    return is_terminal(state)


def _accepted_base(**changes: object) -> State:
    base = State(
        status="accepted",
        scenario=VALID_PM_RESUME,
        output_type=PM_RESUME_CONTRACT.output_type,
        contract_id=PM_RESUME_CONTRACT.contract_id,
        allowed_role=PM_RESUME_CONTRACT.allowed_role,
        submitting_role=PM_RESUME_CONTRACT.allowed_role,
        router_event=PM_RESUME_CONTRACT.router_event,
        registry_runtime_binding_present=True,
        registry_contract_id_matches_runtime=True,
        registry_allowed_roles_match_runtime=True,
        registry_router_event_exists=True,
        runtime_output_type_declared_by_registry=True,
        compat_output_alias_valid=True,
        runtime_prepared_skeleton=True,
        runtime_required_fields_known=True,
        role_authored_body=True,
        required_fields_present=True,
        explicit_empty_arrays_present=True,
        fixed_values_valid=True,
        role_is_allowed=True,
        runtime_progress_status_initialized=True,
        progress_prompt_included=True,
        runtime_receipt_written=True,
        body_hash_verified=True,
        envelope_generated_by_runtime=True,
        direct_router_submission=True,
        router_receives_role_output_envelope=True,
        controller_waits_router_status=True,
        router_ready_evidence_available=True,
        controller_reentered_router_before_foreground_wait=True,
        compact_envelope_refs_used=True,
        router_decision="accept",
    )
    return replace(base, **changes)


def hazard_states() -> dict[str, State]:
    return {
        "missing_registry_runtime_binding": _accepted_base(registry_runtime_binding_present=False),
        "registry_contract_id_mismatch": _accepted_base(registry_contract_id_matches_runtime=False),
        "registry_allowed_role_mismatch": _accepted_base(registry_allowed_roles_match_runtime=False),
        "registry_router_event_missing": _accepted_base(registry_router_event_exists=False),
        "unregistered_runtime_output_type": _accepted_base(runtime_output_type_declared_by_registry=False),
        "broken_compat_output_alias": _accepted_base(compat_output_alias_valid=False),
        "missing_runtime_receipt": _accepted_base(runtime_receipt_written=False),
        "missing_required_field": _accepted_base(required_fields_present=False),
        "missing_explicit_empty_array": _accepted_base(explicit_empty_arrays_present=False),
        "wrong_role": _accepted_base(submitting_role="controller", role_is_allowed=False),
        "stale_body_hash": _accepted_base(body_hash_verified=False),
        "inline_body_leak": _accepted_base(envelope_leaks_body=True),
        "controller_reads_body": _accepted_base(controller_reads_body=True),
        "controller_intermediates_output": _accepted_base(controller_intermediates_output=True),
        "missing_direct_router_submission": _accepted_base(direct_router_submission=False),
        "missing_router_receipt": _accepted_base(router_receives_role_output_envelope=False),
        "controller_waits_role_instead_of_router": _accepted_base(controller_waits_router_status=False),
        "router_ready_next_action_waited_on_role": _accepted_base(
            router_ready_evidence_available=True,
            controller_reentered_router_before_foreground_wait=False,
            controller_foreground_waits_role_after_router_ready=True,
        ),
        "semantic_auto_approval": _accepted_base(runtime_claimed_semantic_approval=True),
        "missing_default_progress_status": _accepted_base(runtime_progress_status_initialized=False),
        "missing_progress_prompt": _accepted_base(progress_prompt_included=False),
        "progress_status_grants_output_dir": _accepted_base(progress_visibility_grant="output_dir"),
        "progress_status_leaks_body": _accepted_base(progress_message_metadata_only=False),
        "progress_update_manual_write": _accepted_base(progress_updates_runtime_written=False),
        "progress_value_nonnumeric": _accepted_base(progress_value_numeric=False),
        "progress_used_as_semantic_decision": _accepted_base(progress_used_for_semantic_decision=True),
        "missing_quality_pack_check": _accepted_base(
            scenario=MISSING_QUALITY_PACK_CHECK,
            output_type=REVIEWER_REPORT_CONTRACT.output_type,
            contract_id=REVIEWER_REPORT_CONTRACT.contract_id,
            allowed_role=REVIEWER_REPORT_CONTRACT.allowed_role,
            submitting_role=REVIEWER_REPORT_CONTRACT.allowed_role,
            quality_packs_declared=True,
            quality_pack_checks_present=False,
        ),
        "pack_specific_runtime_judgment": _accepted_base(
            scenario=PACK_SPECIFIC_RUNTIME_JUDGMENT,
            output_type=REVIEWER_REPORT_CONTRACT.output_type,
            contract_id=REVIEWER_REPORT_CONTRACT.contract_id,
            allowed_role=REVIEWER_REPORT_CONTRACT.allowed_role,
            submitting_role=REVIEWER_REPORT_CONTRACT.allowed_role,
            quality_packs_declared=True,
            quality_pack_checks_present=True,
            runtime_claimed_pack_specific_judgment=True,
        ),
    }
