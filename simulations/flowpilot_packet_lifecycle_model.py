"""FlowGuard model for FlowPilot packet lifecycle hardening.

Risk intent brief:
- Prevent material/current-node packets from advancing when packet body,
  envelope, result envelope, and packet ledger proofs diverge.
- Protect the Controller boundary by requiring packet runtime receipts instead
  of self-attested role text before worker execution, result relay, reviewer
  pass, PM absorption, or PM node advance.
- Model-critical durable state: packet body hash identity across envelope and
  ledger, packet open envelope receipt, packet open ledger receipt, result
  ledger absorption, result relay, result open envelope receipt, result open
  ledger receipt, completed-agent role authority, and PM-required control
  blocker resolution.
- Adversarial branches include PM body repair with stale envelope/ledger hash,
  forged packet open envelope markers, missing packet ledger open receipts,
  result envelopes that were never absorbed into packet_ledger, forged result
  open envelope markers, completed_by_agent_id values that are role strings or
  unmapped IDs, and PM repair decisions that clear blockers without a corrected
  follow-up event.
- Hard invariants: dispatch requires synced packet body hash identity; result
  relay requires packet open envelope+ledger receipts and result ledger
  absorption; reviewer pass requires complete packet/result receipts plus
  completed-agent role authority; PM advancement requires reviewer pass; PM
  repair decisions by themselves do not clear active control blockers.
- Blindspot: this is a focused packet lifecycle model. It does not judge the
  semantic quality of worker or reviewer body content.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class Tick:
    """One packet lifecycle transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | passed
    steps: int = 0

    dispatch_gate_checked: bool = False
    packet_body_hash_identity_synced: bool = False
    packet_body_path_alias_normalized: bool = False
    result_body_path_alias_normalized: bool = False
    reviewer_dispatch_passed: bool = False
    packet_relayed_by_controller: bool = False
    packet_open_envelope_receipt: bool = False
    packet_open_ledger_receipt: bool = False
    write_grant_issued: bool = False

    worker_result_written: bool = False
    worker_project_write_performed: bool = False
    result_envelope_exists: bool = False
    result_ledger_absorbed: bool = False
    completed_agent_id_maps_to_role: bool = False
    result_relayed_by_controller: bool = False
    result_open_envelope_receipt: bool = False
    result_open_ledger_receipt: bool = False

    reviewer_runtime_audit_passed: bool = False
    pm_absorbed_reviewed_research: bool = False
    pm_advanced_node: bool = False

    control_blocker_active: bool = False
    control_blocker_lane: str = "none"  # none | pm_repair_decision_required | fatal_protocol_violation
    pm_repair_decision_recorded: bool = False
    followup_event_already_recorded: bool = False
    followup_reaudit_passed: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _inc(state: State, **changes: object) -> State:
    return replace(state, status="running", steps=state.steps + 1, **changes)


class PacketLifecycleStep:
    """Model one packet lifecycle transition.

    Input x State -> Set(Output x State)
    reads: packet/result envelopes, packet_ledger receipts, control blocker
    status, and completed-agent authority
    writes: dispatch proof, runtime receipts, result relay proof, reviewer
    audit outcome, PM absorption/advance, or PM control-blocker follow-up state
    idempotency: each receipt is monotonic and keyed by packet_id
    """

    name = "PacketLifecycleStep"
    input_description = "packet lifecycle tick"
    output_description = "one packet lifecycle state transition"
    reads = (
        "packet_body_hash_identity",
        "packet_open_receipts",
        "result_ledger_absorption",
        "result_open_receipts",
        "completed_agent_role_authority",
        "control_blocker_status",
    )
    writes = (
        "dispatch_gate",
        "packet_runtime_receipts",
        "result_runtime_receipts",
        "reviewer_packet_audit",
        "pm_control_blocker_resolution",
    )
    idempotency = "packet_id-keyed receipts are monotonic; PM decisions do not duplicate resolution"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "passed":
        return

    if state.control_blocker_active:
        if not state.pm_repair_decision_recorded:
            yield Transition(
                "pm_repair_decision_recorded_blocker_still_active",
                _inc(state, pm_repair_decision_recorded=True, control_blocker_active=True),
            )
            return
        if not state.followup_reaudit_passed:
            yield Transition(
                "followup_reaudit_resolves_pm_control_blocker",
                _inc(
                    state,
                    control_blocker_active=False,
                    followup_reaudit_passed=True,
                    dispatch_gate_checked=True,
                    packet_body_hash_identity_synced=True,
                    packet_body_path_alias_normalized=True,
                    result_body_path_alias_normalized=True,
                ),
            )
            yield Transition(
                "already_recorded_followup_resolves_pm_control_blocker",
                _inc(
                    state,
                    control_blocker_active=False,
                    followup_event_already_recorded=True,
                    followup_reaudit_passed=True,
                    dispatch_gate_checked=True,
                    packet_body_hash_identity_synced=True,
                    packet_body_path_alias_normalized=True,
                    result_body_path_alias_normalized=True,
                ),
            )
            return

    if not state.dispatch_gate_checked:
        yield Transition(
            "dispatch_gate_checks_body_envelope_and_ledger_hash_identity",
            _inc(
                state,
                dispatch_gate_checked=True,
                packet_body_hash_identity_synced=True,
                packet_body_path_alias_normalized=True,
                result_body_path_alias_normalized=True,
            ),
        )
        yield Transition(
            "pm_hash_repair_requires_followup_reaudit",
            _inc(
                state,
                control_blocker_active=True,
                control_blocker_lane="pm_repair_decision_required",
                packet_body_hash_identity_synced=False,
            ),
        )
        yield Transition(
            "fatal_protocol_violation_requires_pm_repair_decision",
            _inc(
                state,
                control_blocker_active=True,
                control_blocker_lane="fatal_protocol_violation",
            ),
        )
        return

    if not state.reviewer_dispatch_passed:
        yield Transition("reviewer_dispatch_passes_after_hash_identity", _inc(state, reviewer_dispatch_passed=True))
        return

    if not state.packet_relayed_by_controller:
        yield Transition("controller_relays_packet_envelope_only", _inc(state, packet_relayed_by_controller=True))
        return

    if not (state.packet_open_envelope_receipt and state.packet_open_ledger_receipt):
        yield Transition(
            "packet_runtime_open_records_envelope_and_ledger",
            _inc(state, packet_open_envelope_receipt=True, packet_open_ledger_receipt=True),
        )
        return

    if not state.write_grant_issued:
        yield Transition(
            "write_grant_issued_from_authorized_packet_scope",
            _inc(state, write_grant_issued=True),
        )
        return

    if not state.worker_result_written:
        yield Transition(
            "worker_result_written_under_write_grant",
            _inc(
                state,
                worker_project_write_performed=True,
                worker_result_written=True,
                result_envelope_exists=True,
                result_ledger_absorbed=True,
                completed_agent_id_maps_to_role=True,
            ),
        )
        return

    if not state.result_relayed_by_controller:
        yield Transition(
            "controller_relays_result_after_packet_and_result_ledger_checks",
            _inc(state, result_relayed_by_controller=True),
        )
        return

    if not (state.result_open_envelope_receipt and state.result_open_ledger_receipt):
        yield Transition(
            "reviewer_runtime_open_records_envelope_and_ledger",
            _inc(state, result_open_envelope_receipt=True, result_open_ledger_receipt=True),
        )
        return

    if not state.reviewer_runtime_audit_passed:
        yield Transition(
            "reviewer_passes_after_packet_result_and_agent_audit",
            _inc(state, reviewer_runtime_audit_passed=True),
        )
        return

    if not state.pm_absorbed_reviewed_research:
        yield Transition(
            "pm_absorbs_reviewed_research_after_packet_group_audit",
            _inc(state, pm_absorbed_reviewed_research=True),
        )
        return

    yield Transition(
        "pm_advances_after_reviewer_packet_audit",
        replace(_inc(state, pm_advanced_node=True), status="passed"),
    )


def is_terminal(state: State) -> bool:
    return state.status == "passed"


def is_success(state: State) -> bool:
    return is_terminal(state) and state.pm_advanced_node


def dispatch_requires_hash_identity(state: State, trace) -> InvariantResult:
    del trace
    if state.reviewer_dispatch_passed and not (
        state.dispatch_gate_checked
        and state.packet_body_hash_identity_synced
        and state.packet_body_path_alias_normalized
        and state.result_body_path_alias_normalized
    ):
        return InvariantResult.fail("dispatch passed without envelope/ledger packet body hash identity")
    return InvariantResult.pass_()


def result_relay_requires_packet_open_and_result_ledger(state: State, trace) -> InvariantResult:
    del trace
    if state.result_relayed_by_controller and not (
        state.packet_open_envelope_receipt
        and state.packet_open_ledger_receipt
        and state.write_grant_issued
        and state.result_envelope_exists
        and state.result_ledger_absorbed
    ):
        return InvariantResult.fail("result relay occurred before packet open receipts and result ledger absorption")
    return InvariantResult.pass_()


def reviewer_pass_requires_complete_runtime_receipts(state: State, trace) -> InvariantResult:
    del trace
    if state.reviewer_runtime_audit_passed and not (
        state.packet_open_envelope_receipt
        and state.packet_open_ledger_receipt
        and state.result_ledger_absorbed
        and state.result_open_envelope_receipt
        and state.result_open_ledger_receipt
        and state.completed_agent_id_maps_to_role
    ):
        return InvariantResult.fail("reviewer pass occurred without complete packet/result receipts and agent role authority")
    return InvariantResult.pass_()


def worker_project_writes_require_write_grant(state: State, trace) -> InvariantResult:
    del trace
    if state.worker_project_write_performed and not state.write_grant_issued:
        return InvariantResult.fail("worker project write occurred before a current-node write grant")
    if state.worker_result_written and not state.write_grant_issued:
        return InvariantResult.fail("worker result was written before a current-node write grant")
    return InvariantResult.pass_()


def pm_absorption_requires_reviewer_packet_audit(state: State, trace) -> InvariantResult:
    del trace
    if state.pm_absorbed_reviewed_research and not state.reviewer_runtime_audit_passed:
        return InvariantResult.fail("PM absorbed research before reviewer packet-group runtime audit passed")
    return InvariantResult.pass_()


def pm_advance_requires_reviewer_packet_audit(state: State, trace) -> InvariantResult:
    del trace
    if state.pm_advanced_node and not state.reviewer_runtime_audit_passed:
        return InvariantResult.fail("PM advanced node before reviewer packet runtime audit passed")
    return InvariantResult.pass_()


def pm_decision_does_not_clear_blocker_without_followup(state: State, trace) -> InvariantResult:
    del trace
    if state.pm_repair_decision_recorded and not state.followup_reaudit_passed and not state.control_blocker_active:
        return InvariantResult.fail("PM repair decision cleared blocker without corrected follow-up re-audit")
    return InvariantResult.pass_()


def fatal_protocol_violation_requires_pm_decision_before_followup(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.control_blocker_lane == "fatal_protocol_violation"
        and state.followup_reaudit_passed
        and not state.pm_repair_decision_recorded
    ):
        return InvariantResult.fail("fatal protocol violation follow-up was accepted before PM repair decision")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "dispatch_requires_hash_identity",
        "Reviewer dispatch requires packet body hash identity across body, envelope, and ledger.",
        dispatch_requires_hash_identity,
    ),
    Invariant(
        "result_relay_requires_packet_open_and_result_ledger",
        "Controller may relay result only after packet-open receipts, write grant, and result ledger absorption.",
        result_relay_requires_packet_open_and_result_ledger,
    ),
    Invariant(
        "reviewer_pass_requires_complete_runtime_receipts",
        "Reviewer pass requires complete packet/result runtime receipts and completed-agent authority.",
        reviewer_pass_requires_complete_runtime_receipts,
    ),
    Invariant(
        "worker_project_writes_require_write_grant",
        "Worker project writes and results require a PM packet-scoped write grant.",
        worker_project_writes_require_write_grant,
    ),
    Invariant(
        "pm_absorption_requires_reviewer_packet_audit",
        "PM research absorption requires a passed packet-group runtime audit.",
        pm_absorption_requires_reviewer_packet_audit,
    ),
    Invariant(
        "pm_advance_requires_reviewer_packet_audit",
        "PM node advancement requires a passed reviewer packet runtime audit.",
        pm_advance_requires_reviewer_packet_audit,
    ),
    Invariant(
        "pm_decision_does_not_clear_blocker_without_followup",
        "PM repair decision records intent but cannot clear a blocker without corrected follow-up re-audit.",
        pm_decision_does_not_clear_blocker_without_followup,
    ),
    Invariant(
        "fatal_protocol_violation_requires_pm_decision_before_followup",
        "Fatal protocol violations remain strict: PM repair decision is required before corrected follow-up replay.",
        fatal_protocol_violation_requires_pm_decision_before_followup,
    ),
)


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 16


REQUIRED_LABELS = (
    "dispatch_gate_checks_body_envelope_and_ledger_hash_identity",
    "pm_hash_repair_requires_followup_reaudit",
    "fatal_protocol_violation_requires_pm_repair_decision",
    "pm_repair_decision_recorded_blocker_still_active",
    "followup_reaudit_resolves_pm_control_blocker",
    "already_recorded_followup_resolves_pm_control_blocker",
    "reviewer_dispatch_passes_after_hash_identity",
    "controller_relays_packet_envelope_only",
    "packet_runtime_open_records_envelope_and_ledger",
    "write_grant_issued_from_authorized_packet_scope",
    "worker_result_written_under_write_grant",
    "controller_relays_result_after_packet_and_result_ledger_checks",
    "reviewer_runtime_open_records_envelope_and_ledger",
    "reviewer_passes_after_packet_result_and_agent_audit",
    "pm_absorbs_reviewed_research_after_packet_group_audit",
    "pm_advances_after_reviewer_packet_audit",
)


def build_workflow() -> Workflow:
    return Workflow((PacketLifecycleStep(),), name="flowpilot_packet_lifecycle")


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(str(result.message))
    return failures


def hazard_states() -> dict[str, State]:
    return {
        "stale_hash_after_body_repair": State(
            status="running",
            dispatch_gate_checked=True,
            packet_body_hash_identity_synced=False,
            reviewer_dispatch_passed=True,
        ),
        "packet_body_alias_not_normalized": State(
            status="running",
            dispatch_gate_checked=True,
            packet_body_hash_identity_synced=True,
            packet_body_path_alias_normalized=False,
            result_body_path_alias_normalized=True,
            reviewer_dispatch_passed=True,
        ),
        "result_body_alias_not_normalized": State(
            status="running",
            dispatch_gate_checked=True,
            packet_body_hash_identity_synced=True,
            packet_body_path_alias_normalized=True,
            result_body_path_alias_normalized=False,
            reviewer_dispatch_passed=True,
        ),
        "packet_open_envelope_only": State(
            status="running",
            dispatch_gate_checked=True,
            packet_body_hash_identity_synced=True,
            reviewer_dispatch_passed=True,
            packet_relayed_by_controller=True,
            packet_open_envelope_receipt=True,
            packet_open_ledger_receipt=False,
            result_envelope_exists=True,
            result_ledger_absorbed=True,
            result_relayed_by_controller=True,
        ),
        "result_without_ledger_absorption": State(
            status="running",
            dispatch_gate_checked=True,
            packet_body_hash_identity_synced=True,
            reviewer_dispatch_passed=True,
            packet_relayed_by_controller=True,
            packet_open_envelope_receipt=True,
            packet_open_ledger_receipt=True,
            write_grant_issued=True,
            result_envelope_exists=True,
            result_ledger_absorbed=False,
            result_relayed_by_controller=True,
        ),
        "worker_write_without_grant": State(
            status="running",
            dispatch_gate_checked=True,
            packet_body_hash_identity_synced=True,
            packet_body_path_alias_normalized=True,
            result_body_path_alias_normalized=True,
            reviewer_dispatch_passed=True,
            packet_relayed_by_controller=True,
            packet_open_envelope_receipt=True,
            packet_open_ledger_receipt=True,
            write_grant_issued=False,
            worker_project_write_performed=True,
            worker_result_written=True,
        ),
        "result_open_envelope_only": State(
            status="running",
            dispatch_gate_checked=True,
            packet_body_hash_identity_synced=True,
            reviewer_dispatch_passed=True,
            packet_relayed_by_controller=True,
            packet_open_envelope_receipt=True,
            packet_open_ledger_receipt=True,
            result_envelope_exists=True,
            result_ledger_absorbed=True,
            result_relayed_by_controller=True,
            result_open_envelope_receipt=True,
            result_open_ledger_receipt=False,
            completed_agent_id_maps_to_role=True,
            reviewer_runtime_audit_passed=True,
        ),
        "agent_id_role_string": State(
            status="running",
            dispatch_gate_checked=True,
            packet_body_hash_identity_synced=True,
            reviewer_dispatch_passed=True,
            packet_relayed_by_controller=True,
            packet_open_envelope_receipt=True,
            packet_open_ledger_receipt=True,
            result_envelope_exists=True,
            result_ledger_absorbed=True,
            result_relayed_by_controller=True,
            result_open_envelope_receipt=True,
            result_open_ledger_receipt=True,
            completed_agent_id_maps_to_role=False,
            reviewer_runtime_audit_passed=True,
        ),
        "pm_decision_clears_blocker_without_followup": State(
            status="running",
            control_blocker_lane="pm_repair_decision_required",
            control_blocker_active=False,
            pm_repair_decision_recorded=True,
            followup_reaudit_passed=False,
        ),
        "fatal_followup_without_pm_decision": State(
            status="running",
            control_blocker_lane="fatal_protocol_violation",
            control_blocker_active=False,
            pm_repair_decision_recorded=False,
            followup_event_already_recorded=True,
            followup_reaudit_passed=True,
        ),
        "pm_absorbs_without_packet_group_audit": State(
            status="running",
            pm_absorbed_reviewed_research=True,
            reviewer_runtime_audit_passed=False,
        ),
    }
