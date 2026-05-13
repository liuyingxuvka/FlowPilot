"""FlowGuard model for FlowPilot explicit next-recipient routing.

Risk intent brief:
- Prevent Controller from guessing which role should receive the next FlowPilot
  action after PM route drafts, route checks, worker results, review blocks,
  resume recovery, parent replay failures, and UI state sync.
- Preserve the legacy obligations while making every controller-visible
  transition carry a concrete recipient and allowed follow-up event.
- Protect route activation from dummy-route fallback, worker packets from
  duplicate owners, repair/reissue from wrong-role routing, resume from chat
  history inference, and Cockpit/UI state from stale index entries.
- Blindspot: this is an abstract process model. It must be paired with runtime
  tests and router conformance checks before claiming production behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


LEGACY_OBLIGATIONS = (
    "controller_boundary",
    "pm_route_draft",
    "process_officer_route_check",
    "reviewer_route_challenge",
    "reviewed_route_activation",
    "single_owner_worker_packet",
    "reviewer_before_worker_dispatch",
    "worker_result_reviewer_review",
    "rejection_routes_to_reissue_or_pm_repair",
    "resume_next_recipient_from_ledger",
    "parent_replay_failure_pm_decision",
    "repair_marks_stale_and_rewrites_frontier",
    "ui_snapshot_from_active_canonical_sources",
)
OBLIGATION_BITS = {name: 1 << index for index, name in enumerate(LEGACY_OBLIGATIONS)}
ALL_OBLIGATIONS = sum(OBLIGATION_BITS.values())

REQUIRED_LABELS = (
    "controller_boundary_confirmed",
    "pm_writes_route_draft",
    "router_dispatches_route_process_check_to_process_officer",
    "process_officer_returns_route_check",
    "pm_accepts_process_route_model",
    "router_dispatches_route_challenge_to_reviewer",
    "reviewer_returns_route_challenge_pass",
    "pm_activates_reviewed_route_from_draft",
    "pm_creates_worker_packet_with_single_owner",
    "reviewer_allows_worker_dispatch",
    "controller_relays_worker_packet_to_owner",
    "worker_owner_returns_result",
    "controller_relays_result_to_reviewer",
    "reviewer_blocks_result_with_control_plane_reissue_lane",
    "router_routes_reissue_to_original_responsible_role",
    "responsible_role_reissues_control_output",
    "controller_relays_reissued_result_to_reviewer",
    "reviewer_passes_reissued_result",
    "resume_loads_ledger_and_derives_next_recipient",
    "parent_replay_failure_routes_pm_segment_decision",
    "pm_segment_decision_marks_stale_and_rewrites_frontier",
    "ui_snapshot_built_from_active_canonical_sources",
    "completion_recorded_after_explicit_next_actions",
)

MAX_SEQUENCE_LENGTH = len(REQUIRED_LABELS) + 2


@dataclass(frozen=True)
class Tick:
    """One Controller tick asking Router for the next legal action."""


@dataclass(frozen=True)
class Action:
    name: str
    recipient: str


@dataclass(frozen=True)
class State:
    step: int = 0
    status: str = "new"  # new | running | blocked | complete
    obligations: int = 0
    last_action: str = "none"
    last_recipient: str = "none"

    controller_has_explicit_next: bool = True
    controller_content_decision: bool = False
    direct_external_pass_event_used: bool = False
    route_activation_source: str = "none"  # none | reviewed_draft | dummy

    packet_owner: str = "none"
    second_packet_owner_assigned: bool = False
    reviewer_dispatch_allowed: bool = False
    result_reviewed_by_reviewer: bool = False

    rejection_lane: str = "none"  # none | control_plane_reissue | pm_repair_decision_required
    reissue_target: str = "none"
    reissue_target_matches_owner: bool = True
    pm_repair_decision_recorded: bool = False

    resume_next_derived_from_ledger: bool = False
    parent_segment_pm_decision_recorded: bool = False
    stale_evidence_marked: bool = False
    frontier_rewritten_after_repair: bool = False

    ui_active_run_resolved: bool = False
    ui_snapshot_from_canonical: bool = False
    ui_used_stale_index_running_entry: bool = False


class Transition(NamedTuple):
    label: str
    recipient: str
    state: State


def _add(state: State, *names: str) -> int:
    mask = state.obligations
    for name in names:
        mask |= OBLIGATION_BITS[name]
    return mask


def initial_state() -> State:
    return State()


class RouterNextRecipientStep:
    """Model one explicit-recipient router transition.

    Input x State -> Set(Output x State)
    reads: route draft/review status, role/work packet ledger, repair lane,
    resume ledger, parent replay state, and active UI pointer
    writes: one explicit recipient action, obligation bit, packet holder,
    repair/frontier marker, or UI snapshot authority
    idempotency: repeat ticks observe completed steps and cannot mint duplicate
    owners or skip the recipient contract
    """

    name = "RouterNextRecipientStep"
    reads = (
        "phase",
        "role_or_packet_ledger",
        "route_draft_review_status",
        "repair_lane",
        "resume_ledger",
        "ui_active_run_pointer",
    )
    writes = (
        "explicit_recipient_action",
        "legacy_obligation_bit",
        "packet_holder",
        "repair_frontier_marker",
        "ui_snapshot_authority",
    )
    input_description = "one controller tick asking router for the next legal action"
    output_description = "one explicit next action with recipient"
    idempotency = "repeat ticks do not create duplicate holders or hidden next steps"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label, transition.recipient),
                new_state=transition.state,
                label=transition.label,
            )


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"blocked", "complete"}:
        return ()
    if invariant_failures(state):
        return (Transition("blocked_on_invariant_failure", "controller", replace(state, status="blocked")),)

    transitions = {
        0: Transition(
            "controller_boundary_confirmed",
            "controller",
            replace(
                state,
                status="running",
                step=1,
                obligations=_add(state, "controller_boundary"),
                last_action="controller_boundary_confirmed",
                last_recipient="controller",
            ),
        ),
        1: Transition(
            "pm_writes_route_draft",
            "project_manager",
            replace(
                state,
                step=2,
                obligations=_add(state, "pm_route_draft"),
                last_action="pm_writes_route_draft",
                last_recipient="project_manager",
            ),
        ),
        2: Transition(
            "router_dispatches_route_process_check_to_process_officer",
            "process_flowguard_officer",
            replace(
                state,
                step=3,
                last_action="router_dispatches_route_process_check_to_process_officer",
                last_recipient="process_flowguard_officer",
            ),
        ),
        3: Transition(
            "process_officer_returns_route_check",
            "controller",
            replace(
                state,
                step=4,
                obligations=_add(state, "process_officer_route_check"),
                last_action="process_officer_returns_route_check",
                last_recipient="controller",
            ),
        ),
        4: Transition(
            "pm_accepts_process_route_model",
            "project_manager",
            replace(
                state,
                step=5,
                last_action="pm_accepts_process_route_model",
                last_recipient="project_manager",
            ),
        ),
        5: Transition(
            "router_dispatches_route_challenge_to_reviewer",
            "human_like_reviewer",
            replace(
                state,
                step=6,
                last_action="router_dispatches_route_challenge_to_reviewer",
                last_recipient="human_like_reviewer",
            ),
        ),
        6: Transition(
            "reviewer_returns_route_challenge_pass",
            "controller",
            replace(
                state,
                step=7,
                obligations=_add(state, "reviewer_route_challenge"),
                last_action="reviewer_returns_route_challenge_pass",
                last_recipient="controller",
            ),
        ),
        7: Transition(
            "pm_activates_reviewed_route_from_draft",
            "project_manager",
            replace(
                state,
                step=8,
                obligations=_add(state, "reviewed_route_activation"),
                route_activation_source="reviewed_draft",
                last_action="pm_activates_reviewed_route_from_draft",
                last_recipient="project_manager",
            ),
        ),
        8: Transition(
            "pm_creates_worker_packet_with_single_owner",
            "project_manager",
            replace(
                state,
                step=9,
                obligations=_add(state, "single_owner_worker_packet"),
                packet_owner="worker_a",
                last_action="pm_creates_worker_packet_with_single_owner",
                last_recipient="project_manager",
            ),
        ),
        9: Transition(
            "reviewer_allows_worker_dispatch",
            "human_like_reviewer",
            replace(
                state,
                step=10,
                obligations=_add(state, "reviewer_before_worker_dispatch"),
                reviewer_dispatch_allowed=True,
                last_action="reviewer_allows_worker_dispatch",
                last_recipient="human_like_reviewer",
            ),
        ),
        10: Transition(
            "controller_relays_worker_packet_to_owner",
            "worker_a",
            replace(state, step=11, last_action="controller_relays_worker_packet_to_owner", last_recipient="worker_a"),
        ),
        11: Transition(
            "worker_owner_returns_result",
            "controller",
            replace(state, step=12, last_action="worker_owner_returns_result", last_recipient="controller"),
        ),
        12: Transition(
            "controller_relays_result_to_reviewer",
            "human_like_reviewer",
            replace(
                state,
                step=13,
                last_action="controller_relays_result_to_reviewer",
                last_recipient="human_like_reviewer",
            ),
        ),
        13: Transition(
            "reviewer_blocks_result_with_control_plane_reissue_lane",
            "controller",
            replace(
                state,
                step=14,
                rejection_lane="control_plane_reissue",
                obligations=_add(state, "worker_result_reviewer_review"),
                last_action="reviewer_blocks_result_with_control_plane_reissue_lane",
                last_recipient="controller",
            ),
        ),
        14: Transition(
            "router_routes_reissue_to_original_responsible_role",
            "worker_a",
            replace(
                state,
                step=15,
                obligations=_add(state, "rejection_routes_to_reissue_or_pm_repair"),
                reissue_target="worker_a",
                last_action="router_routes_reissue_to_original_responsible_role",
                last_recipient="worker_a",
            ),
        ),
        15: Transition(
            "responsible_role_reissues_control_output",
            "controller",
            replace(
                state,
                step=16,
                last_action="responsible_role_reissues_control_output",
                last_recipient="controller",
            ),
        ),
        16: Transition(
            "controller_relays_reissued_result_to_reviewer",
            "human_like_reviewer",
            replace(
                state,
                step=17,
                last_action="controller_relays_reissued_result_to_reviewer",
                last_recipient="human_like_reviewer",
            ),
        ),
        17: Transition(
            "reviewer_passes_reissued_result",
            "controller",
            replace(
                state,
                step=18,
                result_reviewed_by_reviewer=True,
                last_action="reviewer_passes_reissued_result",
                last_recipient="controller",
            ),
        ),
        18: Transition(
            "resume_loads_ledger_and_derives_next_recipient",
            "controller",
            replace(
                state,
                step=19,
                obligations=_add(state, "resume_next_recipient_from_ledger"),
                resume_next_derived_from_ledger=True,
                last_action="resume_loads_ledger_and_derives_next_recipient",
                last_recipient="controller",
            ),
        ),
        19: Transition(
            "parent_replay_failure_routes_pm_segment_decision",
            "project_manager",
            replace(
                state,
                step=20,
                obligations=_add(state, "parent_replay_failure_pm_decision"),
                parent_segment_pm_decision_recorded=True,
                last_action="parent_replay_failure_routes_pm_segment_decision",
                last_recipient="project_manager",
            ),
        ),
        20: Transition(
            "pm_segment_decision_marks_stale_and_rewrites_frontier",
            "project_manager",
            replace(
                state,
                step=21,
                obligations=_add(state, "repair_marks_stale_and_rewrites_frontier"),
                stale_evidence_marked=True,
                frontier_rewritten_after_repair=True,
                pm_repair_decision_recorded=True,
                last_action="pm_segment_decision_marks_stale_and_rewrites_frontier",
                last_recipient="project_manager",
            ),
        ),
        21: Transition(
            "ui_snapshot_built_from_active_canonical_sources",
            "ui_host",
            replace(
                state,
                step=22,
                obligations=_add(state, "ui_snapshot_from_active_canonical_sources"),
                ui_active_run_resolved=True,
                ui_snapshot_from_canonical=True,
                last_action="ui_snapshot_built_from_active_canonical_sources",
                last_recipient="ui_host",
            ),
        ),
        22: Transition(
            "completion_recorded_after_explicit_next_actions",
            "project_manager",
            replace(
                state,
                step=23,
                status="complete",
                last_action="completion_recorded_after_explicit_next_actions",
                last_recipient="project_manager",
            ),
        ),
    }
    transition = transitions.get(state.step)
    return (transition,) if transition else ()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status not in {"new", "complete"}:
        if not state.controller_has_explicit_next:
            failures.append("Controller lacks explicit next recipient/action")
        if state.last_recipient in {"unknown", "none"} and state.step > 0:
            failures.append("last transition had no explicit recipient")
    if state.controller_content_decision:
        failures.append("Controller made a content decision")
    if state.direct_external_pass_event_used:
        failures.append("role pass event was accepted without router-dispatched work package")
    if state.route_activation_source == "dummy":
        failures.append("route activated from dummy route instead of reviewed draft")
    if state.second_packet_owner_assigned:
        failures.append("same worker packet assigned to more than one owner")
    if state.packet_owner not in {"none", "worker_a", "worker_b"}:
        failures.append("worker packet owner is not a known worker role")
    if state.packet_owner != "none" and state.step >= 11 and not state.reviewer_dispatch_allowed:
        failures.append("worker packet relayed before router direct dispatch approval")
    if state.rejection_lane == "control_plane_reissue":
        if state.reissue_target == "unknown":
            failures.append("control-plane reissue has no target role")
        if not state.reissue_target_matches_owner:
            failures.append("control-plane reissue was routed to the wrong role")
    if state.rejection_lane == "pm_repair_decision_required" and not state.pm_repair_decision_recorded and state.step > 14:
        failures.append("project repair proceeded without PM repair decision")
    if state.step >= 19 and not state.resume_next_derived_from_ledger:
        failures.append("resume continued without deriving next recipient from ledger")
    if state.step >= 21 and not state.parent_segment_pm_decision_recorded:
        failures.append("parent replay repair proceeded without PM segment decision")
    if state.frontier_rewritten_after_repair and not state.stale_evidence_marked:
        failures.append("frontier rewritten without marking affected evidence stale")
    if state.ui_snapshot_from_canonical and not state.ui_active_run_resolved:
        failures.append("UI snapshot built without active run resolution")
    if state.ui_used_stale_index_running_entry:
        failures.append("UI snapshot used stale index running entry as active task")
    if state.status == "complete" and state.obligations != ALL_OBLIGATIONS:
        failures.append("completion recorded before all legacy obligations were preserved")
    return failures


def router_next_recipient_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_explicit_next_recipient_contract",
        description=(
            "Every controller-visible FlowPilot step must carry an explicit "
            "recipient/action while preserving route review, packet ownership, "
            "repair, resume, and UI active-run obligations."
        ),
        predicate=router_next_recipient_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((RouterNextRecipientStep(),), name="flowpilot_router_next_recipient_contract")


def is_terminal(state: State) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


def _covered_prefix_state() -> State:
    return State(
        step=22,
        status="running",
        obligations=ALL_OBLIGATIONS,
        last_action="ui_snapshot_built_from_active_canonical_sources",
        last_recipient="ui_host",
        route_activation_source="reviewed_draft",
        packet_owner="worker_a",
        reviewer_dispatch_allowed=True,
        result_reviewed_by_reviewer=True,
        rejection_lane="control_plane_reissue",
        reissue_target="worker_a",
        resume_next_derived_from_ledger=True,
        parent_segment_pm_decision_recorded=True,
        stale_evidence_marked=True,
        frontier_rewritten_after_repair=True,
        ui_active_run_resolved=True,
        ui_snapshot_from_canonical=True,
    )


def hazard_states() -> dict[str, State]:
    base = _covered_prefix_state()
    return {
        "controller_unknown_next": replace(base, controller_has_explicit_next=False),
        "direct_role_pass_without_dispatch": replace(base, direct_external_pass_event_used=True),
        "dummy_route_activation": replace(base, route_activation_source="dummy"),
        "controller_content_decision": replace(base, controller_content_decision=True),
        "double_worker_owner": replace(base, second_packet_owner_assigned=True),
        "reissue_wrong_role": replace(base, reissue_target_matches_owner=False),
        "resume_without_ledger_next": replace(base, resume_next_derived_from_ledger=False),
        "parent_repair_without_pm_segment_decision": replace(base, parent_segment_pm_decision_recorded=False),
        "frontier_rewrite_without_stale_mark": replace(base, stale_evidence_marked=False),
        "ui_uses_stale_running_index_entry": replace(base, ui_used_stale_index_running_entry=True),
        "completion_missing_legacy_obligation": replace(
            base,
            status="complete",
            obligations=ALL_OBLIGATIONS ^ OBLIGATION_BITS["reviewer_route_challenge"],
        ),
    }


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


__all__ = [
    "ALL_OBLIGATIONS",
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "LEGACY_OBLIGATIONS",
    "MAX_SEQUENCE_LENGTH",
    "REQUIRED_LABELS",
    "State",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "next_states",
]
