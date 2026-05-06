"""FlowGuard model for FlowPilot router command folding.

Risk intent brief:
- Compress repeated router subprocess calls only where the folded command is
  behaviorally equivalent to the original checked sequence.
- Preserve hard boundaries: user display, host automation/spawn, role decisions,
  sealed packet bodies, and cross-role prompt delivery must still stop the
  controller loop.
- Model-critical state: safe internal auto-apply actions, manifest checks before
  system-card bundles, packet-ledger checks before mail/packet relays, startup
  mechanical audit before reviewer startup fact card delivery, and file-backed
  role-output preflight before recording role events.
- Hard invariants: folded commands cannot skip the next deliverable card, mix
  card target roles, relay before ledger checks, deliver startup fact cards
  before router-owned audit proof, create control blockers for preflight-only
  role-output envelope failures, or cross user/host/role boundaries.
- Blindspot: this is an abstract command-folding model, not a filesystem replay
  of concrete FlowPilot run directories.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


RUN_UNTIL_WAIT_SAFE = "run_until_wait_safe"
CARD_BUNDLE_SAME_ROLE = "card_bundle_same_role"
CARD_BUNDLE_CROSS_ROLE = "card_bundle_cross_role"
CARD_BUNDLE_SKIPS_NEXT = "card_bundle_skips_next"
RELAY_CHECKED = "relay_checked"
RELAY_WITHOUT_LEDGER_CHECK = "relay_without_ledger_check"
STARTUP_FACT_CHECK = "startup_fact_check"
ROLE_OUTPUT_VALID = "role_output_valid"
ROLE_OUTPUT_BAD_ENVELOPE = "role_output_bad_envelope"

NEGATIVE_SCENARIOS = (
    CARD_BUNDLE_CROSS_ROLE,
    CARD_BUNDLE_SKIPS_NEXT,
    RELAY_WITHOUT_LEDGER_CHECK,
    ROLE_OUTPUT_BAD_ENVELOPE,
)

SCENARIOS = (
    RUN_UNTIL_WAIT_SAFE,
    CARD_BUNDLE_SAME_ROLE,
    CARD_BUNDLE_CROSS_ROLE,
    CARD_BUNDLE_SKIPS_NEXT,
    RELAY_CHECKED,
    RELAY_WITHOUT_LEDGER_CHECK,
    STARTUP_FACT_CHECK,
    ROLE_OUTPUT_VALID,
    ROLE_OUTPUT_BAD_ENVELOPE,
)

NEGATIVE_EXPECTED_REJECTIONS = {
    CARD_BUNDLE_CROSS_ROLE: "card_bundle_mixed_target_roles",
    CARD_BUNDLE_SKIPS_NEXT: "card_bundle_skipped_next_deliverable_card",
    RELAY_WITHOUT_LEDGER_CHECK: "relay_attempted_without_packet_ledger_check",
    ROLE_OUTPUT_BAD_ENVELOPE: "role_output_preflight_failed_without_control_blocker",
}


@dataclass(frozen=True)
class Tick:
    """One abstract command-folding tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"
    safe_internal_actions_applied: int = 0
    stopped_at_boundary: bool = False
    boundary_crossed: bool = False
    manifest_checked: bool = False
    card_bundle_same_role: bool = True
    next_card_matched: bool = True
    cards_delivered: int = 0
    ledger_checked: bool = False
    relay_recorded: bool = False
    startup_mechanical_audit_written: bool = False
    startup_fact_card_delivered: bool = False
    role_output_preflight_checked: bool = False
    role_output_file_backed: bool = False
    event_recorded: bool = False
    control_blocker_created: bool = False
    router_decision: str = "none"
    router_rejection_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class CommandFoldingStep:
    """Model one command-folding transition.

    Input x State -> Set(Output x State)
    reads: scenario, pending action boundary, manifest/ledger/audit/preflight
    state
    writes: folded command progress, terminal router decision
    idempotency: repeated ticks do not duplicate folded delivery or relay
    records after a terminal decision.
    """

    name = "CommandFoldingStep"
    reads = (
        "scenario",
        "pending_action_boundary",
        "manifest_check_state",
        "packet_ledger_check_state",
        "startup_audit_state",
        "role_output_preflight_state",
    )
    writes = (
        "folded_command_progress",
        "delivery_or_relay_record",
        "router_terminal_decision",
    )
    input_description = "router command-folding tick"
    output_description = "one abstract command-folding step"
    idempotency = "terminal folded command decisions are not duplicated"

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


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return

    if state.scenario == "unset":
        for scenario in SCENARIOS:
            yield Transition(
                "router_selects_command_folding_scenario",
                replace(state, status="running", scenario=scenario),
            )
        return

    if state.scenario == RUN_UNTIL_WAIT_SAFE:
        if state.safe_internal_actions_applied == 0:
            yield Transition(
                "run_until_wait_applies_safe_internal_actions",
                replace(state, safe_internal_actions_applied=3),
            )
            return
        if not state.stopped_at_boundary:
            yield Transition(
                "run_until_wait_stops_before_external_boundary",
                replace(
                    state,
                    stopped_at_boundary=True,
                    status="accepted",
                    router_decision="accept",
                ),
            )
        return

    if state.scenario in {CARD_BUNDLE_SAME_ROLE, CARD_BUNDLE_CROSS_ROLE, CARD_BUNDLE_SKIPS_NEXT}:
        if not state.manifest_checked:
            yield Transition(
                "card_bundle_checks_manifest_once",
                replace(state, manifest_checked=True),
            )
            return
        if state.scenario == CARD_BUNDLE_CROSS_ROLE:
            yield Transition(
                "card_bundle_rejects_cross_role_bundle",
                replace(
                    state,
                    card_bundle_same_role=False,
                    status="rejected",
                    router_decision="reject",
                    router_rejection_reason=NEGATIVE_EXPECTED_REJECTIONS[CARD_BUNDLE_CROSS_ROLE],
                ),
            )
            return
        if state.scenario == CARD_BUNDLE_SKIPS_NEXT:
            yield Transition(
                "card_bundle_rejects_skipping_next_deliverable_card",
                replace(
                    state,
                    next_card_matched=False,
                    status="rejected",
                    router_decision="reject",
                    router_rejection_reason=NEGATIVE_EXPECTED_REJECTIONS[CARD_BUNDLE_SKIPS_NEXT],
                ),
            )
            return
        yield Transition(
            "card_bundle_records_same_role_cards_in_order",
            replace(
                state,
                cards_delivered=2,
                status="accepted",
                router_decision="accept",
            ),
        )
        return

    if state.scenario in {RELAY_CHECKED, RELAY_WITHOUT_LEDGER_CHECK}:
        if state.scenario == RELAY_WITHOUT_LEDGER_CHECK:
            yield Transition(
                "relay_checked_rejects_relay_without_packet_ledger_check",
                replace(
                    state,
                    status="rejected",
                    router_decision="reject",
                    router_rejection_reason=NEGATIVE_EXPECTED_REJECTIONS[RELAY_WITHOUT_LEDGER_CHECK],
                ),
            )
            return
        if not state.ledger_checked:
            yield Transition(
                "relay_checked_checks_packet_ledger_once",
                replace(state, ledger_checked=True),
            )
            return
        yield Transition(
            "relay_checked_records_relay_after_ledger_check",
            replace(
                state,
                relay_recorded=True,
                status="accepted",
                router_decision="accept",
            ),
        )
        return

    if state.scenario == STARTUP_FACT_CHECK:
        if not state.startup_mechanical_audit_written:
            yield Transition(
                "prepare_startup_fact_check_writes_router_owned_audit",
                replace(state, startup_mechanical_audit_written=True),
            )
            return
        yield Transition(
            "startup_fact_card_delivery_requires_mechanical_audit",
            replace(
                state,
                manifest_checked=True,
                startup_fact_card_delivered=True,
                status="accepted",
                router_decision="accept",
            ),
        )
        return

    if state.scenario in {ROLE_OUTPUT_VALID, ROLE_OUTPUT_BAD_ENVELOPE}:
        if state.scenario == ROLE_OUTPUT_BAD_ENVELOPE:
            yield Transition(
                "record_role_output_checked_rejects_bad_envelope_without_control_blocker",
                replace(
                    state,
                    role_output_preflight_checked=True,
                    role_output_file_backed=False,
                    event_recorded=False,
                    control_blocker_created=False,
                    status="rejected",
                    router_decision="reject",
                    router_rejection_reason=NEGATIVE_EXPECTED_REJECTIONS[ROLE_OUTPUT_BAD_ENVELOPE],
                ),
            )
            return
        yield Transition(
            "record_role_output_checked_records_valid_file_backed_envelope",
            replace(
                state,
                role_output_preflight_checked=True,
                role_output_file_backed=True,
                event_recorded=True,
                status="accepted",
                router_decision="accept",
            ),
        )
        return


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return is_terminal(state)


def folded_run_until_wait_stops_at_boundary(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.scenario == RUN_UNTIL_WAIT_SAFE:
        if state.safe_internal_actions_applied < 1:
            return InvariantResult.fail("run-until-wait accepted without applying safe internal actions")
        if not state.stopped_at_boundary or state.boundary_crossed:
            return InvariantResult.fail("run-until-wait crossed or missed an external boundary")
    return InvariantResult.pass_()


def card_bundle_preserves_manifest_order_and_role(state: State, trace) -> InvariantResult:
    del trace
    if state.cards_delivered:
        if not state.manifest_checked:
            return InvariantResult.fail("card bundle delivered before manifest check")
        if not state.card_bundle_same_role:
            return InvariantResult.fail("card bundle delivered across target roles")
        if not state.next_card_matched:
            return InvariantResult.fail("card bundle skipped the next deliverable card")
    return InvariantResult.pass_()


def relay_requires_packet_ledger_check(state: State, trace) -> InvariantResult:
    del trace
    if state.relay_recorded and not state.ledger_checked:
        return InvariantResult.fail("relay recorded before packet-ledger check")
    return InvariantResult.pass_()


def startup_fact_card_requires_router_audit(state: State, trace) -> InvariantResult:
    del trace
    if state.startup_fact_card_delivered and not state.startup_mechanical_audit_written:
        return InvariantResult.fail("startup fact card delivered before router-owned startup mechanical audit")
    return InvariantResult.pass_()


def role_output_bad_preflight_is_non_materializing(state: State, trace) -> InvariantResult:
    del trace
    if state.scenario == ROLE_OUTPUT_BAD_ENVELOPE:
        if state.event_recorded:
            return InvariantResult.fail("bad role-output envelope recorded an event")
        if state.control_blocker_created:
            return InvariantResult.fail("bad role-output preflight created a control blocker")
    return InvariantResult.pass_()


def scenarios_end_in_expected_decisions(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.scenario in NEGATIVE_SCENARIOS:
        return InvariantResult.fail(f"router accepted negative folding scenario {state.scenario}")
    if state.status == "rejected" and state.scenario not in NEGATIVE_SCENARIOS:
        return InvariantResult.fail(f"router rejected valid folding scenario {state.scenario}")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="folded_run_until_wait_stops_at_boundary",
        description="run-until-wait may apply only safe internal actions and must stop before user/host/role boundaries.",
        predicate=folded_run_until_wait_stops_at_boundary,
    ),
    Invariant(
        name="card_bundle_preserves_manifest_order_and_role",
        description="card bundles require one manifest check, same target role, and the next deliverable card first.",
        predicate=card_bundle_preserves_manifest_order_and_role,
    ),
    Invariant(
        name="relay_requires_packet_ledger_check",
        description="checked relay records require a packet-ledger check first.",
        predicate=relay_requires_packet_ledger_check,
    ),
    Invariant(
        name="startup_fact_card_requires_router_audit",
        description="startup fact card delivery requires router-owned mechanical audit proof first.",
        predicate=startup_fact_card_requires_router_audit,
    ),
    Invariant(
        name="role_output_bad_preflight_is_non_materializing",
        description="bad role-output preflight rejects without recording events or materializing control blockers.",
        predicate=role_output_bad_preflight_is_non_materializing,
    ),
    Invariant(
        name="scenarios_end_in_expected_decisions",
        description="Valid folded scenarios are accepted and negative scenarios are rejected.",
        predicate=scenarios_end_in_expected_decisions,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 4
REQUIRED_LABELS = (
    "router_selects_command_folding_scenario",
    "run_until_wait_applies_safe_internal_actions",
    "run_until_wait_stops_before_external_boundary",
    "card_bundle_checks_manifest_once",
    "card_bundle_records_same_role_cards_in_order",
    "card_bundle_rejects_cross_role_bundle",
    "card_bundle_rejects_skipping_next_deliverable_card",
    "relay_checked_checks_packet_ledger_once",
    "relay_checked_records_relay_after_ledger_check",
    "relay_checked_rejects_relay_without_packet_ledger_check",
    "prepare_startup_fact_check_writes_router_owned_audit",
    "startup_fact_card_delivery_requires_mechanical_audit",
    "record_role_output_checked_rejects_bad_envelope_without_control_blocker",
    "record_role_output_checked_records_valid_file_backed_envelope",
)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def build_workflow() -> Workflow:
    return Workflow((CommandFoldingStep(),), name="flowpilot_command_folding")


def terminal_predicate(_input_obj, state: State, _trace) -> bool:
    return is_terminal(state)


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "NEGATIVE_EXPECTED_REJECTIONS",
    "NEGATIVE_SCENARIOS",
    "REQUIRED_LABELS",
    "SCENARIOS",
    "Action",
    "State",
    "Tick",
    "Transition",
    "build_workflow",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "next_states",
    "terminal_predicate",
]
