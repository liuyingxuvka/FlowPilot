"""FlowGuard model for FlowPilot handoff/artifact protocol upgrades.

Risk intent brief:
- Validate the planned FlowPilot upgrade before changing Router, role cards, or
  output contracts.
- Protected harms: message-only work products, Router truncating official
  artifacts, reviewers missing handoff context, stale artifact refs, PM
  suggestions being ignored, optional consultation being confused with final PM
  disposition, consultation being forced for trivial suggestions, ACKs being
  treated as completion evidence, and sealed body content leaking into ledgers.
- Modeled state and side effects: role-authored artifact, handoff letter,
  artifact refs and hashes, downstream read/check behavior, PM suggestion
  lifecycle, optional specialist consultation, final PM disposition, gate
  advancement, ACK, and Router preservation behavior.
- Hard invariants: substantive work must have a formal artifact; handoff must
  point to verified artifacts; Router must preserve rather than rebuild official
  artifacts; downstream review reads handoff and checks artifacts; PM
  consultation is optional and never final; blocking suggestions cannot advance
  while unresolved; ACK is not completion; ledgers contain references only.
- Blindspot: this abstract model does not verify concrete prompt wording or JSON
  schema spelling. Runtime, card coverage, and router regression tests must still
  validate implementation files.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_FULL_UPGRADE_PLAN = "valid_full_upgrade_plan"
VALID_DIRECT_PM_DISPOSITION = "valid_direct_pm_disposition"
VALID_OPTIONAL_CONSULTATION = "valid_optional_consultation"
VALID_NO_SUGGESTION_HANDOFF = "valid_no_suggestion_handoff"
VALID_ROUTE_ARTIFACT_PRESERVED = "valid_route_artifact_preserved"

MESSAGE_ONLY_WORK_PRODUCT = "message_only_work_product"
ROUTER_TRUNCATES_ARTIFACT = "router_truncates_artifact"
DOWNSTREAM_SKIPS_HANDOFF = "downstream_skips_handoff"
HANDOFF_ARTIFACT_MISMATCH = "handoff_artifact_mismatch"
STALE_HASH_ACCEPTED = "stale_hash_accepted"
MISSING_PM_SUGGESTION_SECTION = "missing_pm_suggestion_section"
SUGGESTION_IGNORED_BY_PM = "suggestion_ignored_by_pm"
CONSULTATION_TREATED_AS_FINAL = "consultation_treated_as_final"
FORCED_CONSULTATION_FOR_MINOR = "forced_consultation_for_minor"
CONSULTATION_WITHOUT_PACKET = "consultation_without_packet"
CONSULTATION_RESULT_NOT_READ = "consultation_result_not_read"
BLOCKER_ADVANCES_WHILE_CONSULTING = "blocker_advances_while_consulting"
ACK_TREATED_AS_COMPLETION = "ack_treated_as_completion"
MAJOR_DIRECT_REJECT_WITHOUT_REASON = "major_direct_reject_without_reason"
LEDGER_LEAKS_SEALED_BODY = "ledger_leaks_sealed_body"

VALID_SCENARIOS = (
    VALID_FULL_UPGRADE_PLAN,
    VALID_DIRECT_PM_DISPOSITION,
    VALID_OPTIONAL_CONSULTATION,
    VALID_NO_SUGGESTION_HANDOFF,
    VALID_ROUTE_ARTIFACT_PRESERVED,
)

NEGATIVE_SCENARIOS = (
    MESSAGE_ONLY_WORK_PRODUCT,
    ROUTER_TRUNCATES_ARTIFACT,
    DOWNSTREAM_SKIPS_HANDOFF,
    HANDOFF_ARTIFACT_MISMATCH,
    STALE_HASH_ACCEPTED,
    MISSING_PM_SUGGESTION_SECTION,
    SUGGESTION_IGNORED_BY_PM,
    CONSULTATION_TREATED_AS_FINAL,
    FORCED_CONSULTATION_FOR_MINOR,
    CONSULTATION_WITHOUT_PACKET,
    CONSULTATION_RESULT_NOT_READ,
    BLOCKER_ADVANCES_WHILE_CONSULTING,
    ACK_TREATED_AS_COMPLETION,
    MAJOR_DIRECT_REJECT_WITHOUT_REASON,
    LEDGER_LEAKS_SEALED_BODY,
)

SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS

DISPOSITION_NONE = "none"
DISPOSITION_ADOPT = "adopt"
DISPOSITION_PARTIAL = "partial"
DISPOSITION_DEFER = "defer"
DISPOSITION_REJECT = "reject"
DISPOSITION_COVERED = "covered"
DISPOSITION_ROUTE_MUTATION = "route_mutation"
DISPOSITION_STOP_FOR_USER = "stop_for_user"


@dataclass(frozen=True)
class Tick:
    """One abstract handoff/artifact protocol transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"

    formal_artifact_written: bool = False
    handoff_written: bool = False
    handoff_is_only_work_product: bool = False
    handoff_has_work_summary: bool = False
    artifact_refs_present: bool = False
    artifact_paths_exist: bool = False
    artifact_hashes_verified: bool = False
    changed_paths_declared: bool = False
    inspection_notes_present: bool = False
    handoff_artifact_consistent: bool = False
    sealed_body_content_in_handoff_or_ledger: bool = False

    router_validates_refs: bool = False
    router_preserves_role_artifact: bool = False
    router_rebuilds_narrow_artifact: bool = False
    official_review_target_is_role_artifact: bool = False
    role_authored_extra_fields_preserved: bool = False

    downstream_receives_handoff: bool = False
    downstream_reads_handoff: bool = False
    downstream_checks_formal_artifact: bool = False
    downstream_records_consistency_check: bool = False

    ack_recorded: bool = False
    ack_used_as_completion: bool = False
    work_completion_recorded_from_artifact: bool = False

    suggestion_section_present: bool = False
    suggestion_present: bool = True
    no_new_suggestion_statement: bool = False
    suggestion_logged_for_pm: bool = False
    suggestion_blocks_current_gate: bool = False
    suggestion_major: bool = False

    pm_direct_decision_has_basis: bool = False
    pm_final_disposition_recorded: bool = False
    pm_final_disposition: str = DISPOSITION_NONE
    pm_freeform_reason_recorded: bool = False

    consultation_required_by_pm: bool = False
    consultation_forced_by_protocol: bool = False
    consultation_request_packet_written: bool = False
    consultation_target_role_valid: bool = False
    consultation_question_bounded: bool = False
    consultation_artifact_refs_present: bool = False
    consultation_result_artifact_written: bool = False
    consultation_result_read_by_pm: bool = False
    pm_final_disposition_after_consultation: bool = False

    gate_advances: bool = False
    terminal_closure: bool = False
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class HandoffArtifactProtocolStep:
    """Model one FlowPilot handoff/artifact protocol decision.

    Input x State -> Set(Output x State)
    reads: role output envelope, handoff, artifact refs, suggestion ledger,
    consultation packets, PM disposition, gate state, and ACK state.
    writes: accepted or rejected protocol transition.
    idempotency: repeated checking of the same handoff/artifact ref does not
    create duplicate completion or PM disposition side effects.
    """

    name = "HandoffArtifactProtocolStep"
    reads = (
        "role_output_envelope",
        "handoff_letter",
        "formal_artifact",
        "pm_suggestion_ledger",
        "consultation_packet",
        "gate_state",
        "ack_state",
    )
    writes = (
        "router_artifact_registration",
        "downstream_delivery_context",
        "pm_suggestion_disposition",
        "gate_decision",
    )
    input_description = "FlowPilot handoff/artifact protocol tick"
    output_description = "one protocol acceptance or rejection"
    idempotency = "artifact refs and PM disposition are checked once per role output"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def initial_state() -> State:
    return State()


def _safe_base(scenario: str) -> State:
    return State(
        status="running",
        scenario=scenario,
        formal_artifact_written=True,
        handoff_written=True,
        handoff_has_work_summary=True,
        artifact_refs_present=True,
        artifact_paths_exist=True,
        artifact_hashes_verified=True,
        changed_paths_declared=True,
        inspection_notes_present=True,
        handoff_artifact_consistent=True,
        router_validates_refs=True,
        router_preserves_role_artifact=True,
        official_review_target_is_role_artifact=True,
        role_authored_extra_fields_preserved=True,
        downstream_receives_handoff=True,
        downstream_reads_handoff=True,
        downstream_checks_formal_artifact=True,
        downstream_records_consistency_check=True,
        ack_recorded=True,
        work_completion_recorded_from_artifact=True,
        suggestion_section_present=True,
        suggestion_present=True,
        suggestion_logged_for_pm=True,
        pm_direct_decision_has_basis=True,
        pm_final_disposition_recorded=True,
        pm_final_disposition=DISPOSITION_COVERED,
        pm_freeform_reason_recorded=True,
        gate_advances=True,
    )


def _scenario_state(scenario: str) -> State:
    if scenario == VALID_FULL_UPGRADE_PLAN:
        return replace(
            _safe_base(scenario),
            suggestion_major=True,
            consultation_required_by_pm=True,
            consultation_request_packet_written=True,
            consultation_target_role_valid=True,
            consultation_question_bounded=True,
            consultation_artifact_refs_present=True,
            consultation_result_artifact_written=True,
            consultation_result_read_by_pm=True,
            pm_final_disposition_after_consultation=True,
            pm_final_disposition=DISPOSITION_PARTIAL,
        )
    if scenario == VALID_DIRECT_PM_DISPOSITION:
        return replace(
            _safe_base(scenario),
            suggestion_major=False,
            pm_final_disposition=DISPOSITION_ADOPT,
        )
    if scenario == VALID_OPTIONAL_CONSULTATION:
        return replace(
            _safe_base(scenario),
            suggestion_major=True,
            consultation_required_by_pm=True,
            consultation_request_packet_written=True,
            consultation_target_role_valid=True,
            consultation_question_bounded=True,
            consultation_artifact_refs_present=True,
            consultation_result_artifact_written=True,
            consultation_result_read_by_pm=True,
            pm_final_disposition_after_consultation=True,
            pm_final_disposition=DISPOSITION_ROUTE_MUTATION,
        )
    if scenario == VALID_NO_SUGGESTION_HANDOFF:
        return replace(
            _safe_base(scenario),
            suggestion_present=False,
            no_new_suggestion_statement=True,
            suggestion_logged_for_pm=False,
            pm_final_disposition_recorded=False,
            pm_final_disposition=DISPOSITION_NONE,
            pm_freeform_reason_recorded=False,
        )
    if scenario == VALID_ROUTE_ARTIFACT_PRESERVED:
        return replace(
            _safe_base(scenario),
            role_authored_extra_fields_preserved=True,
            router_preserves_role_artifact=True,
            router_rebuilds_narrow_artifact=False,
            pm_final_disposition=DISPOSITION_COVERED,
        )

    state = _safe_base(scenario)
    if scenario == MESSAGE_ONLY_WORK_PRODUCT:
        return replace(state, formal_artifact_written=False, handoff_is_only_work_product=True)
    if scenario == ROUTER_TRUNCATES_ARTIFACT:
        return replace(
            state,
            router_preserves_role_artifact=False,
            router_rebuilds_narrow_artifact=True,
            role_authored_extra_fields_preserved=False,
        )
    if scenario == DOWNSTREAM_SKIPS_HANDOFF:
        return replace(state, downstream_reads_handoff=False, downstream_records_consistency_check=False)
    if scenario == HANDOFF_ARTIFACT_MISMATCH:
        return replace(state, handoff_artifact_consistent=False, downstream_records_consistency_check=False)
    if scenario == STALE_HASH_ACCEPTED:
        return replace(state, artifact_hashes_verified=False, router_validates_refs=False)
    if scenario == MISSING_PM_SUGGESTION_SECTION:
        return replace(state, suggestion_section_present=False, suggestion_present=False, no_new_suggestion_statement=False)
    if scenario == SUGGESTION_IGNORED_BY_PM:
        return replace(state, suggestion_logged_for_pm=True, pm_final_disposition_recorded=False)
    if scenario == CONSULTATION_TREATED_AS_FINAL:
        return replace(
            state,
            suggestion_major=True,
            consultation_required_by_pm=True,
            consultation_request_packet_written=True,
            consultation_target_role_valid=True,
            consultation_question_bounded=True,
            consultation_artifact_refs_present=True,
            consultation_result_artifact_written=False,
            consultation_result_read_by_pm=False,
            pm_final_disposition_recorded=False,
            pm_final_disposition_after_consultation=False,
        )
    if scenario == FORCED_CONSULTATION_FOR_MINOR:
        return replace(
            state,
            suggestion_major=False,
            pm_direct_decision_has_basis=True,
            consultation_forced_by_protocol=True,
            consultation_required_by_pm=True,
        )
    if scenario == CONSULTATION_WITHOUT_PACKET:
        return replace(
            state,
            suggestion_major=True,
            consultation_required_by_pm=True,
            consultation_request_packet_written=False,
            consultation_target_role_valid=False,
            consultation_question_bounded=False,
            consultation_artifact_refs_present=False,
        )
    if scenario == CONSULTATION_RESULT_NOT_READ:
        return replace(
            state,
            suggestion_major=True,
            consultation_required_by_pm=True,
            consultation_request_packet_written=True,
            consultation_target_role_valid=True,
            consultation_question_bounded=True,
            consultation_artifact_refs_present=True,
            consultation_result_artifact_written=True,
            consultation_result_read_by_pm=False,
            pm_final_disposition_after_consultation=False,
        )
    if scenario == BLOCKER_ADVANCES_WHILE_CONSULTING:
        return replace(
            state,
            suggestion_blocks_current_gate=True,
            consultation_required_by_pm=True,
            consultation_request_packet_written=True,
            consultation_target_role_valid=True,
            consultation_question_bounded=True,
            consultation_artifact_refs_present=True,
            consultation_result_artifact_written=False,
            consultation_result_read_by_pm=False,
            pm_final_disposition_recorded=False,
            gate_advances=True,
        )
    if scenario == ACK_TREATED_AS_COMPLETION:
        return replace(state, work_completion_recorded_from_artifact=False, ack_used_as_completion=True)
    if scenario == MAJOR_DIRECT_REJECT_WITHOUT_REASON:
        return replace(
            state,
            suggestion_major=True,
            consultation_required_by_pm=False,
            pm_final_disposition=DISPOSITION_REJECT,
            pm_freeform_reason_recorded=False,
        )
    if scenario == LEDGER_LEAKS_SEALED_BODY:
        return replace(state, sealed_body_content_in_handoff_or_ledger=True)
    raise ValueError(f"unknown scenario: {scenario}")


def protocol_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status not in {"running", "accepted", "rejected"}:
        return failures

    if state.handoff_is_only_work_product or not state.formal_artifact_written:
        failures.append("substantive work product exists only in the handoff letter")
    if not state.handoff_written or not state.handoff_has_work_summary:
        failures.append("handoff letter is missing or lacks work summary")
    if not state.artifact_refs_present or not state.artifact_paths_exist:
        failures.append("handoff lacks concrete artifact refs")
    if not state.artifact_hashes_verified or not state.router_validates_refs:
        failures.append("artifact refs were accepted without current path/hash validation")
    if state.router_rebuilds_narrow_artifact or not state.router_preserves_role_artifact:
        failures.append("Router rebuilt or narrowed the role-authored official artifact")
    if not state.official_review_target_is_role_artifact or not state.role_authored_extra_fields_preserved:
        failures.append("official review target does not preserve role-authored fields")
    if not state.downstream_receives_handoff or not state.downstream_reads_handoff:
        failures.append("downstream role did not receive and read the handoff letter")
    if not state.downstream_checks_formal_artifact or not state.downstream_records_consistency_check:
        failures.append("downstream role did not check handoff against formal artifacts")
    if not state.handoff_artifact_consistent:
        failures.append("handoff claims do not match formal artifacts")
    if state.ack_used_as_completion or (state.gate_advances and not state.work_completion_recorded_from_artifact):
        failures.append("ACK was treated as completion evidence")
    if state.sealed_body_content_in_handoff_or_ledger:
        failures.append("sealed body content leaked into handoff or ledger")

    if not state.suggestion_section_present:
        failures.append("role output omitted PM Suggestion Items")
    if not state.suggestion_present and not state.no_new_suggestion_statement:
        failures.append("no-suggestion case lacks explicit no-new-suggestion statement")
    if state.suggestion_present and not state.suggestion_logged_for_pm:
        failures.append("PM suggestion was not logged for PM disposition")
    if state.suggestion_present and not state.pm_final_disposition_recorded and not state.consultation_required_by_pm:
        failures.append("PM ignored a suggestion without final disposition or consultation")

    if state.consultation_forced_by_protocol and not state.suggestion_major and state.pm_direct_decision_has_basis:
        failures.append("consultation was forced for a minor suggestion despite sufficient PM basis")
    if state.consultation_required_by_pm:
        if not (
            state.consultation_request_packet_written
            and state.consultation_target_role_valid
            and state.consultation_question_bounded
            and state.consultation_artifact_refs_present
        ):
            failures.append("PM consultation request lacks bounded formal packet")
        if state.gate_advances and not state.pm_final_disposition_after_consultation:
            failures.append("PM failed to issue final disposition after consultation")
        if state.pm_final_disposition_recorded and not state.pm_final_disposition_after_consultation:
            failures.append("consultation request was treated as final PM disposition")
        if state.consultation_result_artifact_written and not state.consultation_result_read_by_pm:
            failures.append("PM did not read consultation result before final disposition")
        if state.consultation_result_artifact_written and not state.pm_final_disposition_after_consultation:
            failures.append("PM failed to issue final disposition after consultation")

    if state.suggestion_blocks_current_gate and state.gate_advances:
        resolved = state.pm_final_disposition_recorded and (
            state.pm_final_disposition
            in {
                DISPOSITION_ADOPT,
                DISPOSITION_PARTIAL,
                DISPOSITION_DEFER,
                DISPOSITION_COVERED,
                DISPOSITION_ROUTE_MUTATION,
                DISPOSITION_STOP_FOR_USER,
            }
        )
        if not resolved:
            failures.append("blocking suggestion advanced while unresolved or consulting")
    if (
        state.suggestion_major
        and state.pm_final_disposition == DISPOSITION_REJECT
        and not state.pm_freeform_reason_recorded
    ):
        failures.append("major suggestion was directly rejected without PM reason")

    return failures


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _scenario_state(scenario))
        return

    failures = protocol_failures(state)
    if failures:
        yield Transition(
            f"reject_{state.scenario}",
            replace(state, status="rejected", terminal_reason="; ".join(failures)),
        )
        return
    yield Transition(
        f"accept_{state.scenario}",
        replace(state, status="accepted", terminal_reason="handoff_artifact_protocol_ok"),
    )


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and not protocol_failures(state)


def accepted_states_have_no_failures(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and protocol_failures(state):
        return InvariantResult.fail("unsafe handoff/artifact protocol was accepted")
    if state.status == "rejected" and not protocol_failures(state):
        return InvariantResult.fail("safe handoff/artifact protocol was rejected")
    return InvariantResult.pass_()


def router_preserves_official_artifacts(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and (
        state.router_rebuilds_narrow_artifact
        or not state.router_preserves_role_artifact
        or not state.role_authored_extra_fields_preserved
    ):
        return InvariantResult.fail("accepted Router path did not preserve official artifact")
    return InvariantResult.pass_()


def downstream_review_uses_handoff_and_artifacts(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and not (
        state.downstream_reads_handoff
        and state.downstream_checks_formal_artifact
        and state.downstream_records_consistency_check
    ):
        return InvariantResult.fail("accepted downstream review skipped handoff/artifact consistency")
    return InvariantResult.pass_()


def pm_consultation_is_optional_and_nonfinal(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    if state.consultation_forced_by_protocol:
        return InvariantResult.fail("accepted path forced consultation")
    if state.consultation_required_by_pm and not state.pm_final_disposition_after_consultation:
        return InvariantResult.fail("accepted consultation path lacked later PM final disposition")
    return InvariantResult.pass_()


def blockers_do_not_advance_unresolved(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.suggestion_blocks_current_gate and not state.pm_final_disposition_recorded:
        return InvariantResult.fail("accepted unresolved current-gate blocker")
    return InvariantResult.pass_()


def ack_is_not_completion_evidence(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.ack_used_as_completion:
        return InvariantResult.fail("accepted path used ACK as completion evidence")
    return InvariantResult.pass_()


def ledgers_are_reference_only(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.sealed_body_content_in_handoff_or_ledger:
        return InvariantResult.fail("accepted path leaked sealed body content")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepted_states_have_no_failures",
        description="Only safe handoff/artifact protocol states can be accepted.",
        predicate=accepted_states_have_no_failures,
    ),
    Invariant(
        name="router_preserves_official_artifacts",
        description="Router does not rebuild or truncate role-authored official artifacts.",
        predicate=router_preserves_official_artifacts,
    ),
    Invariant(
        name="downstream_review_uses_handoff_and_artifacts",
        description="Downstream reviewers/officers/PM read handoff and check formal artifacts.",
        predicate=downstream_review_uses_handoff_and_artifacts,
    ),
    Invariant(
        name="pm_consultation_is_optional_and_nonfinal",
        description="Consultation is a PM-available intermediate tool, not forced and not final.",
        predicate=pm_consultation_is_optional_and_nonfinal,
    ),
    Invariant(
        name="blockers_do_not_advance_unresolved",
        description="Blocking suggestions cannot advance while only consulting or unresolved.",
        predicate=blockers_do_not_advance_unresolved,
    ),
    Invariant(
        name="ack_is_not_completion_evidence",
        description="ACK records cannot substitute for formal artifact-backed completion.",
        predicate=ack_is_not_completion_evidence,
    ),
    Invariant(
        name="ledgers_are_reference_only",
        description="Handoff and suggestion ledgers carry refs, not sealed body content.",
        predicate=ledgers_are_reference_only,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def build_workflow() -> Workflow:
    return Workflow((HandoffArtifactProtocolStep(),), name="flowpilot_handoff_artifact_protocol")


def terminal_predicate(_input_obj, state: State, _trace) -> bool:
    return is_terminal(state)


def hazard_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "NEGATIVE_SCENARIOS",
    "SCENARIOS",
    "VALID_SCENARIOS",
    "Action",
    "State",
    "Tick",
    "Transition",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "next_states",
    "protocol_failures",
    "terminal_predicate",
]
