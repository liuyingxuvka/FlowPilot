"""FlowGuard model for FlowPilot canonical repair-scope rotation.

Risk intent:
- Prevent PM repair loops from marking a blocker repaired without a fresh
  executable packet.
- Collapse the PM repair menu to one current five-choice contract.
- Replace current, parent, or route scope cleanly instead of mutating an old
  node in place.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_canonical_repair_scope_rotation"
MAX_SEQUENCE_LENGTH = 11
CURRENT_PM_REPAIR_DECISIONS = (
    "repair_current_scope",
    "repair_parent_scope",
    "redesign_route",
    "waive_with_authority",
    "stop_for_user",
)
REMOVED_PM_REPAIR_DECISIONS = (
    "same_node_repair",
    "sender_reissue",
    "collect_more_evidence",
    "mutate_route",
    "quarantine_evidence",
)
NONTERMINAL_REPAIRS = {
    "repair_current_scope",
    "repair_parent_scope",
    "redesign_route",
}
TERMINAL_REPAIRS = {"waive_with_authority", "stop_for_user"}


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | complete | blocked
    blocker_detected: bool = False
    menu_declared: bool = False
    old_decisions_rejected: bool = False
    pm_decision: str = "none"
    authority_ref_present: bool = False
    source_id: str = ""
    blocker_id: str = ""
    fresh_packet_id: str = ""
    fresh_packet_current_open: bool = False
    transaction_recorded: bool = False
    old_scope_superseded: bool = False
    replacement_scope_created: bool = False
    parent_found: bool = False
    descendants_superseded: bool = False
    route_plan_packet_present: bool = False
    flowguard_scan_passed: bool = False
    reviewer_scan_passed: bool = False
    route_version_switched: bool = False
    blocker_repair_packet_open: bool = False
    blocker_terminal: bool = False
    same_node_repair_in_place: bool = False
    old_decision_accepted: bool = False


@dataclass(frozen=True)
class Tick:
    """One canonical repair-scope transition."""


@dataclass(frozen=True)
class Action:
    label: str


class Transition(NamedTuple):
    label: str
    state: State


REQUIRED_SAFE_LABELS = (
    "record_current_blocker",
    "declare_five_choice_pm_menu",
    "reject_removed_pm_decisions",
    "pm_selects_repair_current_scope",
    "runtime_replaces_current_scope",
    "runtime_records_fresh_packet_transaction",
    "runtime_opens_blocker_repair_packet",
    "complete_nonterminal_repair_rotation",
    "pm_selects_repair_parent_scope",
    "runtime_replaces_parent_scope",
    "pm_selects_redesign_route",
    "runtime_stage_route_plan_scan",
    "runtime_activates_redesigned_route",
    "pm_selects_authorized_waiver",
    "pm_selects_stop_for_user",
)


def initial_state() -> State:
    return State()


class CanonicalRepairScopeRotationStep:
    name = "CanonicalRepairScopeRotationStep"
    input_description = "one PM repair/control-plane tick"
    output_description = "one ordered current-contract repair transition"
    reads = ("semantic_blocker", "pm_repair_decision", "route_nodes", "packets")
    writes = ("repair_transaction", "route_mutation", "blocker_status")
    idempotency = "blocker-id plus source-id scoped repair transaction"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(output=Action(transition.label), new_state=transition.state, label=transition.label)


def _with_current_transaction(state: State) -> State:
    return replace(
        state,
        source_id="node-001",
        blocker_id="blocker-001",
        fresh_packet_id="packet-001-repair",
        fresh_packet_current_open=True,
        transaction_recorded=True,
    )


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"blocked", "complete"}:
        return ()
    failures = invariant_failures(state)
    if failures:
        return (Transition("blocked_on_repair_scope_invariant", replace(state, status="blocked")),)
    if state.status == "new":
        return (Transition("record_current_blocker", replace(state, status="running", blocker_detected=True)),)
    if not state.menu_declared:
        return (Transition("declare_five_choice_pm_menu", replace(state, menu_declared=True)),)
    if not state.old_decisions_rejected:
        return (Transition("reject_removed_pm_decisions", replace(state, old_decisions_rejected=True)),)
    if state.pm_decision == "none":
        return (
            Transition(
                "pm_selects_repair_current_scope",
                replace(state, pm_decision="repair_current_scope", source_id="node-001", blocker_id="blocker-001"),
            ),
            Transition(
                "pm_selects_repair_parent_scope",
                replace(
                    state,
                    pm_decision="repair_parent_scope",
                    source_id="node-001",
                    blocker_id="blocker-001",
                    parent_found=True,
                ),
            ),
            Transition(
                "pm_selects_redesign_route",
                replace(state, pm_decision="redesign_route", source_id="route-v1", blocker_id="blocker-001"),
            ),
            Transition(
                "pm_selects_authorized_waiver",
                replace(
                    state,
                    pm_decision="waive_with_authority",
                    blocker_id="blocker-001",
                    authority_ref_present=True,
                    blocker_terminal=True,
                    status="complete",
                ),
            ),
            Transition(
                "pm_selects_stop_for_user",
                replace(state, pm_decision="stop_for_user", blocker_id="blocker-001", blocker_terminal=True, status="complete"),
            ),
        )
    if state.pm_decision == "repair_current_scope" and not state.replacement_scope_created:
        return (
            Transition(
                "runtime_replaces_current_scope",
                replace(state, old_scope_superseded=True, replacement_scope_created=True),
            ),
        )
    if state.pm_decision == "repair_parent_scope" and not state.replacement_scope_created:
        return (
            Transition(
                "runtime_replaces_parent_scope",
                replace(
                    state,
                    old_scope_superseded=True,
                    replacement_scope_created=True,
                    descendants_superseded=True,
                ),
            ),
        )
    if state.pm_decision == "redesign_route" and not state.route_plan_packet_present:
        return (
            Transition(
                "runtime_stage_route_plan_scan",
                replace(
                    state,
                    route_plan_packet_present=True,
                    flowguard_scan_passed=True,
                    reviewer_scan_passed=True,
                ),
            ),
        )
    if state.pm_decision == "redesign_route" and not state.route_version_switched:
        return (
            Transition(
                "runtime_activates_redesigned_route",
                replace(state, old_scope_superseded=True, replacement_scope_created=True, route_version_switched=True),
            ),
        )
    if state.pm_decision in NONTERMINAL_REPAIRS and state.replacement_scope_created and not state.transaction_recorded:
        return (Transition("runtime_records_fresh_packet_transaction", _with_current_transaction(state)),)
    if state.pm_decision in NONTERMINAL_REPAIRS and state.transaction_recorded and not state.blocker_repair_packet_open:
        return (
            Transition(
                "runtime_opens_blocker_repair_packet",
                replace(state, blocker_repair_packet_open=True),
            ),
        )
    if state.pm_decision in NONTERMINAL_REPAIRS and state.blocker_repair_packet_open:
        return (Transition("complete_nonterminal_repair_rotation", replace(state, status="complete")),)
    return ()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.menu_declared and not set(CURRENT_PM_REPAIR_DECISIONS).isdisjoint(REMOVED_PM_REPAIR_DECISIONS):
        failures.append("current PM repair menu overlaps removed decisions")
    if state.old_decision_accepted:
        failures.append("removed PM repair decision was accepted")
    if state.pm_decision in REMOVED_PM_REPAIR_DECISIONS:
        failures.append("removed PM repair decision reached runtime application")
    if state.same_node_repair_in_place:
        failures.append("same-node repair-in-place path survived")
    if state.pm_decision in NONTERMINAL_REPAIRS and state.blocker_repair_packet_open:
        if not state.fresh_packet_id:
            failures.append("repair_packet_open without fresh_packet_id")
        if not state.fresh_packet_current_open:
            failures.append("repair_packet_open without current open fresh packet")
        if not state.transaction_recorded:
            failures.append("repair_packet_open without repair transaction")
        if not state.source_id or not state.blocker_id:
            failures.append("repair transaction missing source_id or blocker_id")
    if state.pm_decision in {"repair_current_scope", "repair_parent_scope"} and state.blocker_repair_packet_open:
        if not (state.old_scope_superseded and state.replacement_scope_created):
            failures.append("scope repair opened without superseded old scope and replacement scope")
    if state.pm_decision == "repair_parent_scope":
        if state.replacement_scope_created and not state.parent_found:
            failures.append("parent repair guessed a parent scope")
        if state.blocker_repair_packet_open and not state.descendants_superseded:
            failures.append("parent repair kept descendants current")
    if state.pm_decision == "redesign_route":
        if state.route_version_switched and not (state.route_plan_packet_present and state.flowguard_scan_passed and state.reviewer_scan_passed):
            failures.append("route redesign activated without strict route plan and scans")
        if state.blocker_repair_packet_open and not state.route_version_switched:
            failures.append("route redesign opened blocker before route activation")
    if state.pm_decision == "waive_with_authority":
        if state.blocker_terminal and not state.authority_ref_present:
            failures.append("waiver terminal state lacks authority reference")
        if state.fresh_packet_id or state.blocker_repair_packet_open:
            failures.append("authorized waiver created a repair packet")
    if state.pm_decision == "stop_for_user":
        if state.fresh_packet_id or state.blocker_repair_packet_open:
            failures.append("stop_for_user created a repair packet")
    if state.status == "complete" and not is_success(state):
        failures.append("completion claimed before repair-scope obligations were satisfied")
    return failures


def invariant(state: State, trace: object) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="canonical_repair_scope_rotation_invariants",
        description=(
            "PM repair decisions use exactly the current five-choice menu, "
            "removed decisions are rejected, nonterminal repair opens only "
            "after a fresh current executable packet exists, parent repair "
            "abandons descendants, route redesign is scanned before activation, "
            "and terminal decisions create no packet."
        ),
        predicate=invariant,
    ),
)
EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((CanonicalRepairScopeRotationStep(),), name=MODEL_ID)


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return state.status in {"complete", "blocked"}


def is_success(state: State) -> bool:
    if state.status != "complete":
        return False
    if not (state.blocker_detected and state.menu_declared and state.old_decisions_rejected):
        return False
    if state.pm_decision in NONTERMINAL_REPAIRS:
        if not (
            state.old_scope_superseded
            and state.replacement_scope_created
            and state.transaction_recorded
            and state.source_id
            and state.blocker_id
            and state.fresh_packet_id
            and state.fresh_packet_current_open
            and state.blocker_repair_packet_open
        ):
            return False
        if state.pm_decision == "repair_parent_scope" and not (state.parent_found and state.descendants_superseded):
            return False
        if state.pm_decision == "redesign_route" and not (
            state.route_plan_packet_present
            and state.flowguard_scan_passed
            and state.reviewer_scan_passed
            and state.route_version_switched
        ):
            return False
        return True
    if state.pm_decision == "waive_with_authority":
        return state.authority_ref_present and state.blocker_terminal and not state.fresh_packet_id
    if state.pm_decision == "stop_for_user":
        return state.blocker_terminal and not state.fresh_packet_id
    return False


def target_state() -> State:
    return replace(
        initial_state(),
        status="complete",
        blocker_detected=True,
        menu_declared=True,
        old_decisions_rejected=True,
        pm_decision="repair_current_scope",
        source_id="node-001",
        blocker_id="blocker-001",
        fresh_packet_id="packet-001-repair",
        fresh_packet_current_open=True,
        transaction_recorded=True,
        old_scope_superseded=True,
        replacement_scope_created=True,
        blocker_repair_packet_open=True,
    )


def hazard_states() -> dict[str, State]:
    base = target_state()
    route_base = replace(
        base,
        pm_decision="redesign_route",
        source_id="route-v1",
        route_plan_packet_present=True,
        flowguard_scan_passed=True,
        reviewer_scan_passed=True,
        route_version_switched=True,
    )
    parent_base = replace(
        base,
        pm_decision="repair_parent_scope",
        parent_found=True,
        descendants_superseded=True,
    )
    return {
        "removed_decision_reached_runtime": replace(base, pm_decision="same_node_repair"),
        "same_node_repair_in_place_survived": replace(base, same_node_repair_in_place=True),
        "repair_packet_open_without_fresh_packet": replace(base, fresh_packet_id=""),
        "repair_packet_open_without_current_open_packet": replace(base, fresh_packet_current_open=False),
        "repair_packet_open_without_transaction": replace(base, transaction_recorded=False),
        "parent_repair_guessed_parent": replace(parent_base, parent_found=False),
        "parent_repair_kept_descendants_current": replace(parent_base, descendants_superseded=False),
        "route_redesign_without_plan": replace(route_base, route_plan_packet_present=False),
        "route_redesign_without_flowguard_scan": replace(route_base, flowguard_scan_passed=False),
        "waiver_without_authority": replace(
            base,
            pm_decision="waive_with_authority",
            authority_ref_present=False,
            blocker_terminal=True,
            fresh_packet_id="",
            blocker_repair_packet_open=False,
        ),
        "terminal_stop_created_packet": replace(
            base,
            pm_decision="stop_for_user",
            blocker_terminal=True,
            fresh_packet_id="packet-stop-should-not-exist",
            blocker_repair_packet_open=False,
        ),
    }


def state_summary(state: State) -> dict[str, object]:
    return state.__dict__.copy()
