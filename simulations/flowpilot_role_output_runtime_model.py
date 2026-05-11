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
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_PM_RESUME = "valid_pm_resume_decision"
VALID_GATE_DECISION = "valid_gate_decision"
VALID_REVIEWER_REPORT = "valid_reviewer_report"
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
    VALID_GATE_DECISION,
    VALID_REVIEWER_REPORT,
)

NEGATIVE_SCENARIOS = (
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


PM_RESUME_CONTRACT = OutputContract(
    output_type="pm_resume_recovery_decision",
    contract_id="flowpilot.output_contract.pm_resume_decision.v1",
    allowed_role="project_manager",
    requires_explicit_empty_arrays=True,
)

GATE_DECISION_CONTRACT = OutputContract(
    output_type="gate_decision",
    contract_id="flowpilot.output_contract.gate_decision.v1",
    allowed_role="human_like_reviewer",
    requires_explicit_empty_arrays=False,
)

REVIEWER_REPORT_CONTRACT = OutputContract(
    output_type="reviewer_review_report",
    contract_id="flowpilot.output_contract.reviewer_review_report.v1",
    allowed_role="human_like_reviewer",
    requires_explicit_empty_arrays=True,
)

CONTRACTS_BY_SCENARIO = {
    VALID_PM_RESUME: PM_RESUME_CONTRACT,
    VALID_GATE_DECISION: GATE_DECISION_CONTRACT,
    VALID_REVIEWER_REPORT: REVIEWER_REPORT_CONTRACT,
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


def _router_rejection_reason(state: State) -> str:
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


def negative_scenarios_are_rejected(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.scenario in NEGATIVE_SCENARIOS:
        return InvariantResult.fail(f"router accepted negative role-output scenario {state.scenario}")
    if state.status == "rejected" and state.scenario in VALID_SCENARIOS:
        return InvariantResult.fail(f"router rejected valid role-output scenario {state.scenario}")
    return InvariantResult.pass_()


INVARIANTS = (
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
        compact_envelope_refs_used=True,
        router_decision="accept",
    )
    return replace(base, **changes)


def hazard_states() -> dict[str, State]:
    return {
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
