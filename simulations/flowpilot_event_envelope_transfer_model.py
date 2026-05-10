"""FlowGuard model for FlowPilot record-event envelope transfer.

Risk intent brief:
- Prevent Controller from hand-copying event envelope fields into a reconstructed
  payload that can lose runtime receipts or hide packet lists.
- Preserve the envelope/body split: Controller may pass a whole payload or a
  path/hash reference, but must not read or rewrite sealed role/report/result
  bodies.
- Model-critical state: event envelope schema, project-local path, file hash,
  event name, producing role, current allowed external event, controller
  visibility, forbidden body fields, runtime receipt refs, material-scan packet
  lists, duplicate submission, and router terminal decision.
- Adversarial branches include missing file, hash mismatch, event mismatch,
  wrong role, bad visibility, body-field leakage, hand-reconstructed payloads,
  missing runtime receipt refs, hidden material packets, duplicate envelope
  replay, and envelopes outside the current allowed event group.
- Hard invariants: envelope refs are equivalent to full envelope payloads for
  legal inputs; every accepted event passed schema/hash/event/role/visibility/
  forbidden-body checks; refs do not let Controller read or mutate sealed body
  content; known reviewer runtime-receipt and PM material-packets failures are
  rejected only on the manual-reconstruction path and avoided by refs.
- Blindspot: this is a focused control-plane model. It does not judge the
  semantic quality of reviewer reports, PM decisions, or packet bodies.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_REVIEWER_FULL = "valid_reviewer_full_payload"
VALID_REVIEWER_REF = "valid_reviewer_envelope_ref"
VALID_MATERIAL_FULL = "valid_material_full_payload"
VALID_MATERIAL_REF = "valid_material_envelope_ref"
MANUAL_RECEIPT_RENAMED = "manual_receipt_field_renamed"
MANUAL_PACKETS_NESTED = "manual_packets_nested_or_dropped"
DUPLICATE_SAME_ENVELOPE = "duplicate_same_envelope"
MISSING_FILE = "missing_envelope_file"
HASH_MISMATCH = "envelope_hash_mismatch"
BAD_SCHEMA = "bad_envelope_schema"
EVENT_MISMATCH = "event_name_mismatch"
ROLE_MISMATCH = "from_role_mismatch"
BAD_VISIBILITY = "bad_controller_visibility"
FORBIDDEN_BODY_FIELD = "forbidden_body_field"
OUTSIDE_ALLOWED_EVENT = "outside_allowed_event"
MISSING_RUNTIME_RECEIPT_REF = "missing_runtime_receipt_ref"


ACCEPTED_SCENARIOS = {
    VALID_REVIEWER_FULL,
    VALID_REVIEWER_REF,
    VALID_MATERIAL_FULL,
    VALID_MATERIAL_REF,
}

IDEMPOTENT_SCENARIOS = {DUPLICATE_SAME_ENVELOPE}

REJECTED_SCENARIOS = {
    MANUAL_RECEIPT_RENAMED,
    MANUAL_PACKETS_NESTED,
    MISSING_FILE,
    HASH_MISMATCH,
    BAD_SCHEMA,
    EVENT_MISMATCH,
    ROLE_MISMATCH,
    BAD_VISIBILITY,
    FORBIDDEN_BODY_FIELD,
    OUTSIDE_ALLOWED_EVENT,
    MISSING_RUNTIME_RECEIPT_REF,
}

SCENARIOS = tuple(sorted(ACCEPTED_SCENARIOS | IDEMPOTENT_SCENARIOS | REJECTED_SCENARIOS))


@dataclass(frozen=True)
class Tick:
    """One record-event transfer transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected | already_recorded
    scenario: str = "unset"
    input_mode: str = "unset"  # full_payload | envelope_ref | manual_reconstruction
    event: str = ""
    expected_event: str = ""
    from_role: str = ""
    expected_role: str = ""

    role_generated_standard_envelope: bool = False
    envelope_ref_used: bool = False
    full_payload_used: bool = False
    manual_reconstruction_used: bool = False
    controller_read_sealed_body: bool = False
    controller_mutated_envelope_fields: bool = False

    envelope_path_project_local: bool = False
    envelope_file_exists: bool = False
    envelope_hash_matches: bool = False
    schema_allowed: bool = False
    event_name_matches_cli: bool = False
    event_currently_allowed: bool = False
    from_role_matches_contract: bool = False
    controller_visibility_allowed: bool = False
    forbidden_body_fields_absent: bool = False
    router_read_envelope_json: bool = False
    router_used_loaded_envelope_as_payload: bool = False

    runtime_receipt_ref_present: bool = False
    runtime_receipt_ref_preserved: bool = False
    material_packets_present: bool = False
    material_packets_preserved_top_level: bool = False

    duplicate_submission: bool = False
    prior_event_recorded: bool = False
    duplicate_side_effect_written: bool = False

    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


class EnvelopeTransferStep:
    """Model one record-event envelope transfer transition.

    Input x State -> Set(Output x State)
    reads: envelope ref, envelope file/hash/schema/event/from_role/visibility,
    forbidden controller-visible fields, runtime receipt refs, material packets,
    current allowed external events, and prior event flags.
    writes: accepted event, rejection reason, or idempotent already-recorded
    outcome.
    idempotency: a duplicate of the same already-recorded envelope returns
    already-recorded without another event side effect.
    """

    name = "EnvelopeTransferStep"
    reads = (
        "envelope_ref",
        "event_envelope",
        "current_allowed_external_event",
        "prior_event_flag",
    )
    writes = ("router_event_decision",)
    input_description = "record-event envelope transfer tick"
    output_description = "one router validation or terminal decision"
    idempotency = "duplicate same-envelope submissions do not create duplicate event side effects"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(output=Action(transition.label), new_state=transition.state, label=transition.label)


def _base_event_fields(scenario: str) -> dict[str, object]:
    if scenario in {VALID_MATERIAL_FULL, VALID_MATERIAL_REF, MANUAL_PACKETS_NESTED}:
        return {
            "event": "pm_issues_material_and_capability_scan_packets",
            "expected_event": "pm_issues_material_and_capability_scan_packets",
            "from_role": "project_manager",
            "expected_role": "project_manager",
            "material_packets_present": True,
            "material_packets_preserved_top_level": True,
            "runtime_receipt_ref_present": False,
            "runtime_receipt_ref_preserved": False,
        }
    return {
        "event": "reviewer_reports_startup_facts",
        "expected_event": "reviewer_reports_startup_facts",
        "from_role": "human_like_reviewer",
        "expected_role": "human_like_reviewer",
        "material_packets_present": False,
        "material_packets_preserved_top_level": False,
        "runtime_receipt_ref_present": True,
        "runtime_receipt_ref_preserved": True,
    }


def _selected_state(scenario: str) -> State:
    mode = "manual_reconstruction"
    if scenario in {VALID_REVIEWER_REF, VALID_MATERIAL_REF, DUPLICATE_SAME_ENVELOPE, MISSING_FILE, HASH_MISMATCH}:
        mode = "envelope_ref"
    elif scenario in {VALID_REVIEWER_FULL, VALID_MATERIAL_FULL}:
        mode = "full_payload"

    fields = _base_event_fields(scenario)
    state = State(
        status="running",
        scenario=scenario,
        input_mode=mode,
        role_generated_standard_envelope=scenario != MANUAL_RECEIPT_RENAMED and scenario != MANUAL_PACKETS_NESTED,
        envelope_ref_used=mode == "envelope_ref",
        full_payload_used=mode == "full_payload",
        manual_reconstruction_used=mode == "manual_reconstruction",
        controller_read_sealed_body=False,
        controller_mutated_envelope_fields=mode == "manual_reconstruction",
        envelope_path_project_local=True,
        envelope_file_exists=True,
        envelope_hash_matches=True,
        schema_allowed=True,
        event_name_matches_cli=True,
        event_currently_allowed=True,
        from_role_matches_contract=True,
        controller_visibility_allowed=True,
        forbidden_body_fields_absent=True,
        **fields,
    )

    if scenario == MANUAL_RECEIPT_RENAMED:
        state = replace(state, runtime_receipt_ref_present=False, runtime_receipt_ref_preserved=False)
    elif scenario == MANUAL_PACKETS_NESTED:
        state = replace(state, material_packets_preserved_top_level=False)
    elif scenario == DUPLICATE_SAME_ENVELOPE:
        state = replace(state, duplicate_submission=True, prior_event_recorded=True)
    elif scenario == MISSING_FILE:
        state = replace(state, envelope_file_exists=False)
    elif scenario == HASH_MISMATCH:
        state = replace(state, envelope_hash_matches=False)
    elif scenario == BAD_SCHEMA:
        state = replace(state, schema_allowed=False)
    elif scenario == EVENT_MISMATCH:
        state = replace(state, event_name_matches_cli=False, expected_event="pm_issues_material_and_capability_scan_packets")
    elif scenario == ROLE_MISMATCH:
        state = replace(state, from_role_matches_contract=False, from_role="project_manager")
    elif scenario == BAD_VISIBILITY:
        state = replace(state, controller_visibility_allowed=False)
    elif scenario == FORBIDDEN_BODY_FIELD:
        state = replace(state, forbidden_body_fields_absent=False, controller_read_sealed_body=True)
    elif scenario == OUTSIDE_ALLOWED_EVENT:
        state = replace(state, event_currently_allowed=False)
    elif scenario == MISSING_RUNTIME_RECEIPT_REF:
        state = replace(state, runtime_receipt_ref_present=False, runtime_receipt_ref_preserved=False)
    return state


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _selected_state(scenario))
        return
    if state.status != "running":
        return
    if state.duplicate_submission and state.prior_event_recorded:
        yield Transition(
            "router_returns_already_recorded_for_duplicate_same_envelope",
            replace(
                state,
                status="already_recorded",
                router_read_envelope_json=True,
                router_used_loaded_envelope_as_payload=True,
                duplicate_side_effect_written=False,
                terminal_reason="idempotent_duplicate",
            ),
        )
        return
    hard_checks = (
        state.envelope_path_project_local
        and state.envelope_file_exists
        and state.envelope_hash_matches
        and state.schema_allowed
        and state.event_name_matches_cli
        and state.event_currently_allowed
        and state.from_role_matches_contract
        and state.controller_visibility_allowed
        and state.forbidden_body_fields_absent
    )
    known_payload_shape_ok = (
        (state.event == "reviewer_reports_startup_facts" and state.runtime_receipt_ref_present and state.runtime_receipt_ref_preserved)
        or (
            state.event == "pm_issues_material_and_capability_scan_packets"
            and state.material_packets_present
            and state.material_packets_preserved_top_level
        )
    )
    if hard_checks and known_payload_shape_ok and not state.controller_read_sealed_body:
        yield Transition(
            "router_accepts_full_payload_or_verified_envelope_ref",
            replace(
                state,
                status="accepted",
                router_read_envelope_json=state.envelope_ref_used,
                router_used_loaded_envelope_as_payload=True,
                terminal_reason="accepted",
            ),
        )
        return
    reason = "hard_check_failed"
    if state.event == "reviewer_reports_startup_facts" and (
        not state.runtime_receipt_ref_present or not state.runtime_receipt_ref_preserved
    ):
        reason = "runtime_receipt_ref_missing_or_not_preserved"
    elif state.event == "pm_issues_material_and_capability_scan_packets" and (
        state.material_packets_present and not state.material_packets_preserved_top_level
    ):
        reason = "material_packets_not_visible_at_payload_top_level"
    elif not state.event_currently_allowed:
        reason = "event_not_currently_allowed"
    elif not state.forbidden_body_fields_absent:
        reason = "forbidden_body_field"
    yield Transition(
        f"router_rejects_{state.scenario}",
        replace(
            state,
            status="rejected",
            router_read_envelope_json=state.envelope_ref_used and state.envelope_file_exists and state.envelope_hash_matches,
            router_used_loaded_envelope_as_payload=False,
            terminal_reason=reason,
        ),
    )


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected", "already_recorded"}


def is_success(state: State) -> bool:
    return state.status == "accepted"


def terminal_predicate(_input_obj: object, state: State, _trace: object) -> bool:
    return is_terminal(state)


def build_workflow() -> Workflow:
    return Workflow((EnvelopeTransferStep(),), name="flowpilot_event_envelope_transfer")


def accepted_requires_all_checks(state: State, trace: object) -> InvariantResult:
    del trace
    if state.status == "accepted" and not (
        state.schema_allowed
        and state.event_name_matches_cli
        and state.event_currently_allowed
        and state.from_role_matches_contract
        and state.controller_visibility_allowed
        and state.forbidden_body_fields_absent
        and state.envelope_hash_matches
    ):
        return InvariantResult.fail("accepted envelope without all hard checks")
    return InvariantResult.pass_()


def envelope_ref_preserves_controller_boundary(state: State, trace: object) -> InvariantResult:
    del trace
    if state.envelope_ref_used and state.controller_read_sealed_body:
        return InvariantResult.fail("envelope ref path let Controller read sealed body")
    if state.envelope_ref_used and state.controller_mutated_envelope_fields:
        return InvariantResult.fail("envelope ref path let Controller mutate envelope fields")
    return InvariantResult.pass_()


def legal_ref_equivalent_to_full_payload(state: State, trace: object) -> InvariantResult:
    del trace
    if state.scenario in {VALID_REVIEWER_REF, VALID_MATERIAL_REF} and state.status == "accepted" and not state.router_used_loaded_envelope_as_payload:
        return InvariantResult.fail("legal envelope ref was not normalized to the same payload used by full envelope input")
    return InvariantResult.pass_()


def known_failures_are_rejected_only_on_bad_shape(state: State, trace: object) -> InvariantResult:
    del trace
    if state.scenario == VALID_REVIEWER_REF and state.status == "rejected":
        return InvariantResult.fail("valid reviewer ref still lost runtime_receipt_ref")
    if state.scenario == VALID_MATERIAL_REF and state.status == "rejected":
        return InvariantResult.fail("valid material ref still hid packets from payload.packets")
    if state.scenario == MANUAL_RECEIPT_RENAMED and state.status == "accepted":
        return InvariantResult.fail("manual reconstruction with renamed runtime receipt was accepted")
    if state.scenario == MANUAL_PACKETS_NESTED and state.status == "accepted":
        return InvariantResult.fail("manual reconstruction with hidden material packets was accepted")
    return InvariantResult.pass_()


def duplicate_same_envelope_is_idempotent(state: State, trace: object) -> InvariantResult:
    del trace
    if state.scenario == DUPLICATE_SAME_ENVELOPE and state.status == "already_recorded" and state.duplicate_side_effect_written:
        return InvariantResult.fail("duplicate same envelope wrote a duplicate side effect")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "accepted_requires_all_checks",
        "Accepted event envelopes must pass schema, hash, event, role, visibility, allowed-event, and forbidden-body checks.",
        accepted_requires_all_checks,
    ),
    Invariant(
        "envelope_ref_preserves_controller_boundary",
        "Controller may pass path/hash refs but may not read sealed bodies or mutate envelope fields.",
        envelope_ref_preserves_controller_boundary,
    ),
    Invariant(
        "legal_ref_equivalent_to_full_payload",
        "Legal envelope refs normalize to the same payload surface as a full envelope JSON submission.",
        legal_ref_equivalent_to_full_payload,
    ),
    Invariant(
        "known_failures_are_rejected_only_on_bad_shape",
        "Refs preserve runtime_receipt_ref and material packets while manual reconstruction failures are rejected.",
        known_failures_are_rejected_only_on_bad_shape,
    ),
    Invariant(
        "duplicate_same_envelope_is_idempotent",
        "Duplicate same-envelope submissions must be already-recorded without duplicate side effects.",
        duplicate_same_envelope_is_idempotent,
    ),
)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, None)
        if not result.ok:
            failures.append(result.message)
    return failures


def hazard_states() -> dict[str, State]:
    accepted = replace(_selected_state(VALID_REVIEWER_REF), status="accepted", router_used_loaded_envelope_as_payload=True)
    return {
        "accepted_without_hash_check": replace(accepted, envelope_hash_matches=False),
        "accepted_outside_allowed_event": replace(accepted, event_currently_allowed=False),
        "accepted_wrong_role": replace(accepted, from_role_matches_contract=False),
        "accepted_forbidden_body_field": replace(accepted, forbidden_body_fields_absent=False, controller_read_sealed_body=True),
        "ref_controller_mutated_envelope": replace(accepted, envelope_ref_used=True, controller_mutated_envelope_fields=True),
        "manual_receipt_accepted": replace(_selected_state(MANUAL_RECEIPT_RENAMED), status="accepted"),
        "manual_packets_accepted": replace(_selected_state(MANUAL_PACKETS_NESTED), status="accepted"),
        "duplicate_side_effect": replace(_selected_state(DUPLICATE_SAME_ENVELOPE), status="already_recorded", duplicate_side_effect_written=True),
    }


MAX_SEQUENCE_LENGTH = 4
EXTERNAL_INPUTS = (Tick(),)


__all__ = [
    "ACCEPTED_SCENARIOS",
    "EXTERNAL_INPUTS",
    "IDEMPOTENT_SCENARIOS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "REJECTED_SCENARIOS",
    "SCENARIOS",
    "State",
    "Tick",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "terminal_predicate",
]
