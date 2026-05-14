"""FlowGuard model for the FlowPilot current-node router packet loop.

Risk intent brief:
- Prevent Controller from turning packet relay into route authority.
- Protect sealed packet/result bodies and project evidence from Controller
  reads or authorship.
- Model-critical durable state: PM route activation, current-node packet
  registration, PM high-standard gate, router direct dispatch, worker
  dispatch, active-holder packet lease, fast-lane mechanical retry/result
  submission, Controller next-action notice, PM result disposition, formal
  reviewer gate release, reviewer pass/block, route mutation, stale
  evidence/frontier marking, node completion, final route-wide ledger
  source-of-truth generation, same-scope replay, generated-resource and visual
  evidence closure, and segmented final backward replay.
- Adversarial branches include packet registration before route activation,
  worker dispatch before router direct dispatch, reviewer pass before PM
  disposition and formal gate release, result relay before packet-ledger checks,
  reviewer result-review card before PM gate release, officer packet relay without an officer card, repair/recheck
  bypasses around the reviewer,
  router wait events that are impossible under the active node kind, parent
  repair lanes that target leaf/current-node worker dispatch, collapsed repair
  outcome tables that map success/blocker/protocol-blocker to one
  business-validated event,
  route mutation without reviewer block or stale markers, PM completion before
  reviewer pass, final ledger without a current route scan/zero unresolved
  items/source-of-truth file, stale/unresolved evidence, pending generated
  resources, missing screenshots for UI/visual work, old assets reused as
  current evidence, final replay without a clean ledger or segment decisions,
  Controller body reads, and Controller-origin project evidence.
- Hard invariants: current-node packets require active route and fresh frontier;
  controller-only mode fail-closes to PM when no legal next action exists;
  expected PM/reviewer role-event waits must not be materialized as
  no-next-action blockers;
  current-node packets gate write grants; router direct dispatch gates worker work;
  worker and officer results are
  packet-ledger checked before PM relay; PM dispositions worker results before
  formal reviewer gate packages; active-holder fast-lane
  closure writes a Controller-visible next-action notice before cross-role relay; repair/recheck returns to the
  reviewer before PM completion; reviewer result decisions require the
  formal PM gate package and result-review system card; mutation requires reviewer block and stale
  evidence/frontier markers; same-scope replay reruns after mutation;
  PM node completion updates the durable completion ledger before parent replay
  or task completion projection;
  evidence/quality package and reviewer evidence quality pass precede final
  ledger source-of-truth generation; final ledger and segmented replay are
  ordered terminal gates; Controller remains envelope-only.
- Blindspot: this is an abstract control-plane model, not a replay adapter for
  the concrete router implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MAX_ROUTE_MUTATIONS = 1
NODE_KINDS = {"leaf", "parent", "module", "repair"}
PARENT_NODE_KINDS = {"parent", "module"}
LEAF_CURRENT_NODE_EVENTS = {
    "pm_registers_current_node_packet",
    "reviewer_allows_current_node_dispatch",
    "worker_current_node_result_returned",
    "reviewer_current_node_result_decision",
    "pm_completes_current_node",
}
PARENT_REPAIR_SAFE_EVENTS = {
    "pm_enters_child_subtree",
    "pm_records_parent_protocol_blocker",
    "pm_records_parent_segment_decision",
    "pm_completes_parent_node",
    "reviewer_parent_backward_replay",
}
BUSINESS_VALIDATED_REPAIR_EVENTS = LEAF_CURRENT_NODE_EVENTS | {
    "pm_completes_parent_node",
    "pm_records_parent_segment_decision",
}
EVENT_NODE_KIND_COMPATIBILITY = {
    event: {"leaf", "repair"}
    for event in LEAF_CURRENT_NODE_EVENTS
}
EVENT_NODE_KIND_COMPATIBILITY.update(
    {
        "pm_enters_child_subtree": PARENT_NODE_KINDS,
        "pm_records_parent_protocol_blocker": PARENT_NODE_KINDS,
        "pm_records_parent_segment_decision": PARENT_NODE_KINDS,
        "pm_completes_parent_node": PARENT_NODE_KINDS,
        "reviewer_parent_backward_replay": PARENT_NODE_KINDS,
    }
)


@dataclass(frozen=True)
class Tick:
    """One router/controller current-node loop tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | blocked | complete
    holder: str = "none"  # none | controller | pm | reviewer | worker | officer
    active_node_kind: str = "leaf"  # leaf | parent | module | repair
    route_version: int = 0

    controller_boundary_confirmed: bool = False
    controller_only_mode_active: bool = False
    no_next_action_detected: bool = False
    pm_decision_required_blocker_written: bool = False
    controller_read_sealed_body: bool = False
    controller_originated_project_evidence: bool = False
    controller_relayed_body_content: bool = False
    control_repair_origin: str = "none"  # none | parent_backward_replay | current_node_result | material_dispatch
    control_repair_wait_event: str = "none"
    repair_outcome_success_event: str = "none"
    repair_outcome_blocker_event: str = "none"
    repair_outcome_protocol_blocker_event: str = "none"

    route_activated: bool = False
    officer_packet_card_delivered: bool = False
    officer_packet_relayed: bool = False
    officer_packet_identity_boundary_present: bool = False
    officer_result_returned: bool = False
    officer_result_identity_boundary_present: bool = False
    officer_result_ledger_checked: bool = False
    officer_result_routed_to_pm: bool = False
    pm_absorbed_officer_result: bool = False
    officer_lifecycle_flags_current: bool = False
    route_history_context_refreshed: bool = False
    pm_prior_path_context_reviewed: bool = False
    route_history_context_stale: bool = False
    node_acceptance_plan_prior_context_used: bool = False
    pm_prior_path_context_used_for_route_mutation: bool = False
    parent_segment_prior_context_used: bool = False
    evidence_quality_prior_context_used: bool = False
    final_ledger_prior_context_used: bool = False
    pm_node_high_standard_gate_opened: bool = False
    pm_node_high_standard_risks_reviewed: bool = False
    node_acceptance_plan_written: bool = False
    reviewer_node_acceptance_plan_reviewed: bool = False
    current_node_packet_registered: bool = False
    write_grant_issued: bool = False
    reviewer_dispatch_allowed: bool = False
    worker_dispatched: bool = False
    worker_project_write_performed: bool = False
    worker_packet_identity_boundary_present: bool = False
    active_holder_lease_issued: bool = False
    active_holder_contact_attempted: bool = False
    active_holder_contact_is_current_holder: bool = True
    active_holder_contact_agent_matches: bool = True
    active_holder_contact_packet_current: bool = True
    active_holder_contact_route_frontier_current: bool = True
    active_holder_contact_action_allowed: bool = True
    active_holder_ack_recorded: bool = False
    active_holder_packet_opened_through_runtime: bool = False
    active_holder_progress_recorded: bool = False
    active_holder_progress_controller_safe: bool = True
    active_holder_packet_family: str = "current_node"  # current_node | material_scan | research | pm_role_work
    generalized_packet_registered: bool = False
    generalized_packet_relayed: bool = False
    generalized_packet_identity_boundary_present: bool = True
    generalized_packet_live_holder_known: bool = True
    generalized_result_target_is_pm: bool = True
    fast_lane_initial_result_submitted: bool = False
    fast_lane_mechanical_reject_recorded: bool = False
    fast_lane_result_resubmitted: bool = False
    fast_lane_result_mechanics_passed: bool = False
    fast_lane_controller_notice_written: bool = False
    worker_result_returned: bool = False
    worker_result_identity_boundary_present: bool = False
    worker_result_ledger_checked: bool = False
    worker_result_routed_to_pm: bool = False
    pm_result_disposition_recorded: bool = False
    pm_formal_node_gate_package_released: bool = False
    worker_result_routed_to_reviewer: bool = False
    reviewer_worker_result_card_delivered: bool = False
    reviewer_decision: str = "none"  # none | pass | block
    reviewer_block_seen: bool = False
    repair_packet_registered: bool = False
    repair_dispatch_allowed: bool = False
    repair_worker_dispatched: bool = False
    repair_packet_identity_boundary_present: bool = False
    repair_result_returned: bool = False
    repair_result_identity_boundary_present: bool = False
    repair_result_ledger_checked: bool = False
    repair_result_routed_to_reviewer: bool = False
    repair_recheck_passed: bool = False
    pm_node_completion_card_delivered: bool = False
    pm_node_completed: bool = False
    node_completion_ledger_updated: bool = False
    parent_backward_targets_enumerated: bool = False
    parent_backward_replay_passed: bool = False
    parent_pm_segment_decision_recorded: bool = False
    parent_node_completed: bool = False

    route_mutation_count: int = 0
    stale_evidence_marked: bool = False
    frontier_marked_stale: bool = False
    frontier_rewritten_after_mutation: bool = False
    same_scope_replay_rerun_after_mutation: bool = False

    current_route_scan_done: bool = False
    pm_evidence_quality_package_card_delivered: bool = False
    evidence_quality_package_written: bool = False
    evidence_quality_review_card_delivered: bool = False
    evidence_quality_reviewer_passed: bool = False
    stale_or_unresolved_evidence_present: bool = False
    pending_generated_resources: bool = False
    ui_visual_required: bool = False
    ui_visual_screenshots_present: bool = False
    old_assets_reused_as_current_evidence: bool = False
    unresolved_count_zero: bool = False
    pm_final_ledger_card_delivered: bool = False
    final_ledger_source_of_truth_generated: bool = False
    final_ledger_built: bool = False
    final_ledger_clean: bool = False
    terminal_replay_map_generated_from_final_ledger: bool = False
    terminal_replay_root_segment_passed: bool = False
    terminal_replay_parent_segment_passed: bool = False
    terminal_replay_leaf_segment_passed: bool = False
    terminal_replay_pm_segment_decisions_recorded: bool = False
    final_backward_replay_card_delivered: bool = False
    final_backward_replay_passed: bool = False
    task_completion_projection_published: bool = False
    pm_terminal_closure_card_delivered: bool = False


class Transition(NamedTuple):
    label: str
    state: State


Condition = tuple[str, object]
ConditionGroup = tuple[Condition, ...]


@dataclass(frozen=True)
class EventContract:
    """Abstract role-event contract used to distinguish legal waits from dead ends."""

    name: str
    requires_all: ConditionGroup
    satisfied_by_any: tuple[ConditionGroup, ...]
    role: str


EXPECTED_ROLE_EVENT_CONTRACTS: tuple[EventContract, ...] = (
    EventContract(
        name="officer_result_returned",
        role="officer",
        requires_all=(("officer_packet_relayed", True),),
        satisfied_by_any=(
            (("officer_result_returned", True),),
        ),
    ),
    EventContract(
        name="pm_absorbs_officer_result",
        role="pm",
        requires_all=(("officer_result_routed_to_pm", True),),
        satisfied_by_any=(
            (("pm_absorbed_officer_result", True),),
        ),
    ),
    EventContract(
        name="pm_opens_current_node_high_standard_gate",
        role="pm",
        requires_all=(
            ("pm_absorbed_officer_result", True),
            ("pm_prior_path_context_reviewed", True),
        ),
        satisfied_by_any=(
            (("pm_node_high_standard_gate_opened", True),),
        ),
    ),
    EventContract(
        name="pm_writes_node_acceptance_plan",
        role="pm",
        requires_all=(
            ("pm_node_high_standard_gate_opened", True),
            ("pm_prior_path_context_reviewed", True),
        ),
        satisfied_by_any=(
            (("node_acceptance_plan_written", True),),
        ),
    ),
    EventContract(
        name="reviewer_reviews_node_acceptance_plan",
        role="reviewer",
        requires_all=(("node_acceptance_plan_written", True),),
        satisfied_by_any=(
            (("reviewer_node_acceptance_plan_reviewed", True),),
        ),
    ),
    EventContract(
        name="pm_registers_current_node_packet",
        role="pm",
        requires_all=(("reviewer_node_acceptance_plan_reviewed", True),),
        satisfied_by_any=(
            (("current_node_packet_registered", True),),
        ),
    ),
    EventContract(
        name="reviewer_allows_current_node_dispatch",
        role="reviewer",
        requires_all=(
            ("current_node_packet_registered", True),
            ("write_grant_issued", True),
        ),
        satisfied_by_any=(
            (("reviewer_dispatch_allowed", True),),
        ),
    ),
    EventContract(
        name="worker_current_node_result_returned",
        role="worker",
        requires_all=(("worker_dispatched", True),),
        satisfied_by_any=(
            (("worker_result_returned", True),),
        ),
    ),
    EventContract(
        name="pm_records_current_node_result_disposition",
        role="pm",
        requires_all=(("worker_result_routed_to_pm", True),),
        satisfied_by_any=(
            (("pm_result_disposition_recorded", True),),
        ),
    ),
    EventContract(
        name="pm_releases_current_node_formal_gate",
        role="pm",
        requires_all=(("pm_result_disposition_recorded", True),),
        satisfied_by_any=(
            (("pm_formal_node_gate_package_released", True),),
        ),
    ),
    EventContract(
        name="reviewer_current_node_result_decision",
        role="reviewer",
        requires_all=(
            ("pm_formal_node_gate_package_released", True),
            ("reviewer_worker_result_card_delivered", True),
        ),
        satisfied_by_any=(
            (("reviewer_decision", "pass"),),
            (("reviewer_decision", "block"),),
        ),
    ),
    EventContract(
        name="pm_repair_or_route_mutation_decision",
        role="pm",
        requires_all=(
            ("reviewer_decision", "block"),
            ("pm_prior_path_context_reviewed", True),
        ),
        satisfied_by_any=(
            (("repair_packet_registered", True),),
            (("route_mutation_count", 1),),
        ),
    ),
    EventContract(
        name="reviewer_allows_repair_dispatch",
        role="reviewer",
        requires_all=(("repair_packet_registered", True),),
        satisfied_by_any=(
            (("repair_dispatch_allowed", True),),
        ),
    ),
    EventContract(
        name="worker_repair_result_returned",
        role="worker",
        requires_all=(("repair_worker_dispatched", True),),
        satisfied_by_any=(
            (("repair_result_returned", True),),
        ),
    ),
    EventContract(
        name="reviewer_rechecks_repair_result",
        role="reviewer",
        requires_all=(("repair_result_routed_to_reviewer", True),),
        satisfied_by_any=(
            (("repair_recheck_passed", True),),
        ),
    ),
    EventContract(
        name="pm_completes_current_node",
        role="pm",
        requires_all=(
            ("reviewer_decision", "pass"),
            ("pm_node_completion_card_delivered", True),
        ),
        satisfied_by_any=(
            (("pm_node_completed", True),),
        ),
    ),
    EventContract(
        name="pm_enumerates_parent_backward_targets",
        role="pm",
        requires_all=(("node_completion_ledger_updated", True),),
        satisfied_by_any=(
            (("parent_backward_targets_enumerated", True),),
        ),
    ),
    EventContract(
        name="reviewer_parent_backward_replay",
        role="reviewer",
        requires_all=(("parent_backward_targets_enumerated", True),),
        satisfied_by_any=(
            (("parent_backward_replay_passed", True),),
        ),
    ),
    EventContract(
        name="pm_records_parent_segment_decision",
        role="pm",
        requires_all=(
            ("parent_backward_replay_passed", True),
            ("pm_prior_path_context_reviewed", True),
        ),
        satisfied_by_any=(
            (("parent_pm_segment_decision_recorded", True),),
        ),
    ),
    EventContract(
        name="pm_completes_parent_node",
        role="pm",
        requires_all=(("parent_pm_segment_decision_recorded", True),),
        satisfied_by_any=(
            (("parent_node_completed", True),),
        ),
    ),
    EventContract(
        name="pm_writes_evidence_quality_package",
        role="pm",
        requires_all=(("pm_evidence_quality_package_card_delivered", True),),
        satisfied_by_any=(
            (("evidence_quality_package_written", True),),
        ),
    ),
    EventContract(
        name="reviewer_evidence_quality_review",
        role="reviewer",
        requires_all=(("evidence_quality_review_card_delivered", True),),
        satisfied_by_any=(
            (("evidence_quality_reviewer_passed", True),),
        ),
    ),
    EventContract(
        name="pm_generates_final_ledger_source_of_truth",
        role="pm",
        requires_all=(("pm_final_ledger_card_delivered", True),),
        satisfied_by_any=(
            (("final_ledger_source_of_truth_generated", True),),
        ),
    ),
    EventContract(
        name="pm_builds_clean_final_ledger",
        role="pm",
        requires_all=(
            ("pm_final_ledger_card_delivered", True),
            ("final_ledger_source_of_truth_generated", True),
        ),
        satisfied_by_any=(
            (("final_ledger_built", True), ("final_ledger_clean", True)),
        ),
    ),
    EventContract(
        name="reviewer_terminal_root_segment_replay",
        role="reviewer",
        requires_all=(("terminal_replay_map_generated_from_final_ledger", True),),
        satisfied_by_any=(
            (("terminal_replay_root_segment_passed", True),),
        ),
    ),
    EventContract(
        name="reviewer_terminal_parent_segment_replay",
        role="reviewer",
        requires_all=(("terminal_replay_root_segment_passed", True),),
        satisfied_by_any=(
            (("terminal_replay_parent_segment_passed", True),),
        ),
    ),
    EventContract(
        name="reviewer_terminal_leaf_segment_replay",
        role="reviewer",
        requires_all=(("terminal_replay_parent_segment_passed", True),),
        satisfied_by_any=(
            (("terminal_replay_leaf_segment_passed", True),),
        ),
    ),
    EventContract(
        name="pm_records_terminal_segment_decisions",
        role="pm",
        requires_all=(("terminal_replay_leaf_segment_passed", True),),
        satisfied_by_any=(
            (("terminal_replay_pm_segment_decisions_recorded", True),),
        ),
    ),
    EventContract(
        name="reviewer_final_backward_replay",
        role="reviewer",
        requires_all=(("final_backward_replay_card_delivered", True),),
        satisfied_by_any=(
            (("final_backward_replay_passed", True),),
        ),
    ),
    EventContract(
        name="pm_terminal_closure",
        role="pm",
        requires_all=(("pm_terminal_closure_card_delivered", True),),
        satisfied_by_any=(
            (("status", "complete"),),
        ),
    ),
)


def initial_state() -> State:
    return State()


class RouterLoopStep:
    """Model one current-node router transition.

    Input x State -> Set(Output x State)
    reads: route activation, packet loop holder, reviewer decision, mutation
    status, stale evidence/frontier state, and terminal ledger status
    writes: one control-plane fact, packet-loop handoff, mutation marker,
    terminal ledger fact, or terminal status
    idempotency: a repeated tick observes the current state and advances at
    most one missing fact; terminal states produce no further side effects.
    """

    name = "RouterLoopStep"
    reads = (
        "controller_boundary",
        "route_activation",
        "officer_packet_loop",
        "packet_loop",
        "repair_recheck_loop",
        "reviewer_decision",
        "route_mutation",
        "final_ledger",
    )
    writes = (
        "control_plane_fact",
        "packet_handoff",
        "packet_ledger_check",
        "route_mutation_marker",
        "final_ledger_fact",
        "terminal_status",
    )
    input_description = "current-node router tick"
    output_description = "one abstract FlowPilot packet-loop action"
    idempotency = "repeat ticks do not duplicate completed packet or ledger facts"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def _clear_current_node_cycle(state: State, **changes: object) -> State:
    return replace(
        state,
        route_activated=False,
        active_node_kind="leaf",
        officer_packet_card_delivered=False,
        officer_packet_relayed=False,
        officer_packet_identity_boundary_present=False,
        officer_result_returned=False,
        officer_result_identity_boundary_present=False,
        officer_result_ledger_checked=False,
        officer_result_routed_to_pm=False,
        pm_absorbed_officer_result=False,
        officer_lifecycle_flags_current=False,
        route_history_context_refreshed=False,
        pm_prior_path_context_reviewed=False,
        route_history_context_stale=True,
        node_acceptance_plan_prior_context_used=False,
        parent_segment_prior_context_used=False,
        evidence_quality_prior_context_used=False,
        final_ledger_prior_context_used=False,
        pm_node_high_standard_gate_opened=False,
        pm_node_high_standard_risks_reviewed=False,
        node_acceptance_plan_written=False,
        reviewer_node_acceptance_plan_reviewed=False,
        current_node_packet_registered=False,
        write_grant_issued=False,
        reviewer_dispatch_allowed=False,
        worker_dispatched=False,
        worker_project_write_performed=False,
        worker_packet_identity_boundary_present=False,
        active_holder_lease_issued=False,
        active_holder_contact_attempted=False,
        active_holder_contact_is_current_holder=True,
        active_holder_contact_agent_matches=True,
        active_holder_contact_packet_current=True,
        active_holder_contact_route_frontier_current=True,
        active_holder_contact_action_allowed=True,
        active_holder_ack_recorded=False,
        active_holder_packet_opened_through_runtime=False,
        active_holder_progress_recorded=False,
        active_holder_progress_controller_safe=True,
        active_holder_packet_family="current_node",
        generalized_packet_registered=False,
        generalized_packet_relayed=False,
        generalized_packet_identity_boundary_present=True,
        generalized_packet_live_holder_known=True,
        generalized_result_target_is_pm=True,
        fast_lane_initial_result_submitted=False,
        fast_lane_mechanical_reject_recorded=False,
        fast_lane_result_resubmitted=False,
        fast_lane_result_mechanics_passed=False,
        fast_lane_controller_notice_written=False,
        worker_result_returned=False,
        worker_result_identity_boundary_present=False,
        worker_result_ledger_checked=False,
        worker_result_routed_to_pm=False,
        pm_result_disposition_recorded=False,
        pm_formal_node_gate_package_released=False,
        worker_result_routed_to_reviewer=False,
        reviewer_worker_result_card_delivered=False,
        reviewer_decision="none",
        repair_packet_registered=False,
        repair_dispatch_allowed=False,
        repair_worker_dispatched=False,
        repair_packet_identity_boundary_present=False,
        repair_result_returned=False,
        repair_result_identity_boundary_present=False,
        repair_result_ledger_checked=False,
        repair_result_routed_to_reviewer=False,
        repair_recheck_passed=False,
        pm_node_completion_card_delivered=False,
        pm_node_completed=False,
        node_completion_ledger_updated=False,
        parent_backward_targets_enumerated=False,
        parent_backward_replay_passed=False,
        parent_pm_segment_decision_recorded=False,
        parent_node_completed=False,
        same_scope_replay_rerun_after_mutation=False,
        current_route_scan_done=False,
        pm_evidence_quality_package_card_delivered=False,
        evidence_quality_package_written=False,
        evidence_quality_review_card_delivered=False,
        evidence_quality_reviewer_passed=False,
        stale_or_unresolved_evidence_present=False,
        pending_generated_resources=False,
        ui_visual_required=False,
        ui_visual_screenshots_present=False,
        old_assets_reused_as_current_evidence=False,
        unresolved_count_zero=False,
        pm_final_ledger_card_delivered=False,
        final_ledger_source_of_truth_generated=False,
        final_ledger_built=False,
        final_ledger_clean=False,
        terminal_replay_map_generated_from_final_ledger=False,
        terminal_replay_root_segment_passed=False,
        terminal_replay_parent_segment_passed=False,
        terminal_replay_leaf_segment_passed=False,
        terminal_replay_pm_segment_decisions_recorded=False,
        final_backward_replay_card_delivered=False,
        final_backward_replay_passed=False,
        task_completion_projection_published=False,
        pm_terminal_closure_card_delivered=False,
        control_repair_origin="none",
        control_repair_wait_event="none",
        repair_outcome_success_event="none",
        repair_outcome_blocker_event="none",
        repair_outcome_protocol_blocker_event="none",
        **changes,
    )


def _condition_matches(state: State, condition: Condition) -> bool:
    field_name, expected = condition
    return getattr(state, field_name) == expected


def _conditions_match(state: State, conditions: ConditionGroup) -> bool:
    return all(_condition_matches(state, condition) for condition in conditions)


def _event_contract_satisfied(state: State, contract: EventContract) -> bool:
    return any(
        _conditions_match(state, conditions)
        for conditions in contract.satisfied_by_any
    )


def expected_role_event_waits(state: State) -> tuple[str, ...]:
    return tuple(
        contract.name
        for contract in EXPECTED_ROLE_EVENT_CONTRACTS
        if _conditions_match(state, contract.requires_all)
        and not _event_contract_satisfied(state, contract)
    )


def expected_wait_hazard_states() -> dict[str, State]:
    samples: dict[str, State] = {}
    pending = [initial_state()]
    seen = {initial_state()}
    while pending:
        state = pending.pop(0)
        if state.status not in {"blocked", "complete"}:
            for wait_name in expected_role_event_waits(state):
                hazard_name = f"expected_role_event_wait_{wait_name}_materializes_blocker"
                samples.setdefault(
                    hazard_name,
                    replace(state, pm_decision_required_blocker_written=True),
                )
        for transition in next_safe_states(state):
            if transition.state not in seen:
                seen.add(transition.state)
                pending.append(transition.state)
    return samples


def _event_allowed_for_node_kind(event: str, node_kind: str) -> bool:
    allowed = EVENT_NODE_KIND_COMPATIBILITY.get(event)
    if allowed is None:
        return True
    return node_kind in allowed


def _repair_outcome_events(state: State) -> tuple[str, ...]:
    return tuple(
        event
        for event in (
            state.repair_outcome_success_event,
            state.repair_outcome_blocker_event,
            state.repair_outcome_protocol_blocker_event,
        )
        if event != "none"
    )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"blocked", "complete"}:
        return

    if not state.controller_boundary_confirmed:
        yield Transition(
            "controller_boundary_confirmed_envelope_only",
            replace(
                state,
                status="running",
                holder="controller",
                controller_boundary_confirmed=True,
                controller_only_mode_active=True,
            ),
        )
        return

    if not state.route_activated and state.route_version == 0:
        yield Transition(
            "controller_fail_closes_no_next_action_to_pm_blocker",
            replace(
                state,
                status="blocked",
                holder="pm",
                no_next_action_detected=True,
                pm_decision_required_blocker_written=True,
            ),
        )

    if state.route_mutation_count and not state.frontier_rewritten_after_mutation:
        yield Transition(
            "frontier_rewritten_for_mutated_route",
            replace(
                state,
                holder="pm",
                frontier_rewritten_after_mutation=True,
            ),
        )
        return

    if not state.route_activated:
        if state.route_version == 0:
            yield Transition(
                "pm_activates_route",
                replace(
                    state,
                    holder="pm",
                    route_version=1,
                    route_activated=True,
                ),
            )
            return
        yield Transition(
            "pm_activates_mutated_route",
            replace(state, holder="pm", route_activated=True),
        )
        return

    if not state.officer_lifecycle_flags_current:
        yield Transition(
            "officer_lifecycle_flags_reconciled_before_model_packet",
            replace(state, holder="pm", officer_lifecycle_flags_current=True),
        )
        return

    if not state.officer_packet_card_delivered:
        yield Transition(
            "officer_packet_card_delivered_before_controller_relay",
            replace(state, holder="officer", officer_packet_card_delivered=True),
        )
        return

    if not state.officer_packet_relayed:
        yield Transition(
            "officer_packet_relayed_after_officer_card",
            replace(
                state,
                holder="officer",
                officer_packet_relayed=True,
                officer_packet_identity_boundary_present=True,
            ),
        )
        return

    if not state.officer_result_returned:
        yield Transition(
            "officer_result_returned_to_packet_ledger",
            replace(
                state,
                holder="controller",
                officer_result_returned=True,
                officer_result_identity_boundary_present=True,
            ),
        )
        return

    if not state.officer_result_ledger_checked:
        yield Transition(
            "officer_result_ledger_checked_before_pm_relay",
            replace(state, holder="controller", officer_result_ledger_checked=True),
        )
        return

    if not state.officer_result_routed_to_pm:
        yield Transition(
            "officer_result_routed_to_pm_after_ledger_check",
            replace(state, holder="pm", officer_result_routed_to_pm=True),
        )
        return

    if not state.pm_absorbed_officer_result:
        yield Transition(
            "pm_absorbs_officer_result_before_node_packet",
            replace(state, holder="pm", pm_absorbed_officer_result=True),
        )
        return

    if (
        not state.node_acceptance_plan_written
        and (not state.route_history_context_refreshed or state.route_history_context_stale)
    ):
        yield Transition(
            "controller_refreshes_route_history_context_for_node_plan",
            replace(
                state,
                holder="controller",
                route_history_context_refreshed=True,
                pm_prior_path_context_reviewed=False,
                route_history_context_stale=False,
            ),
        )
        return

    if not state.node_acceptance_plan_written and not state.pm_prior_path_context_reviewed:
        yield Transition(
            "pm_reads_prior_path_context_for_node_plan",
            replace(state, holder="pm", pm_prior_path_context_reviewed=True),
        )
        return

    if not state.pm_node_high_standard_gate_opened:
        yield Transition(
            "pm_opens_current_node_high_standard_gate",
            replace(
                state,
                holder="pm",
                pm_node_high_standard_gate_opened=True,
                pm_node_high_standard_risks_reviewed=True,
            ),
        )
        return

    if not state.node_acceptance_plan_written:
        yield Transition(
            "pm_writes_node_acceptance_plan_before_packet",
            replace(
                state,
                holder="pm",
                node_acceptance_plan_written=True,
                node_acceptance_plan_prior_context_used=True,
            ),
        )
        return

    if not state.reviewer_node_acceptance_plan_reviewed:
        yield Transition(
            "reviewer_reviews_node_acceptance_plan_before_packet",
            replace(
                state,
                holder="reviewer",
                reviewer_node_acceptance_plan_reviewed=True,
            ),
        )
        return

    if not state.current_node_packet_registered:
        yield Transition(
            "current_node_packet_registered_after_route_activation_and_acceptance_plan",
            replace(
                state,
                holder="controller",
                current_node_packet_registered=True,
            ),
        )
        return

    if not state.write_grant_issued:
        yield Transition(
            "write_grant_issued_from_current_node_packet",
            replace(state, holder="pm", write_grant_issued=True),
        )
        return

    if not state.reviewer_dispatch_allowed:
        yield Transition(
            "router_direct_dispatch_allowed_for_current_node",
            replace(state, holder="reviewer", reviewer_dispatch_allowed=True),
        )
        return

    if not state.worker_dispatched:
        yield Transition(
            "worker_dispatched_after_router_direct_dispatch",
            replace(
                state,
                holder="worker",
                worker_dispatched=True,
                worker_packet_identity_boundary_present=True,
            ),
        )
        return

    if not state.active_holder_lease_issued:
        yield Transition(
            "active_holder_lease_issued_for_current_worker",
            replace(state, holder="worker", active_holder_lease_issued=True),
        )
        return

    if not state.active_holder_ack_recorded:
        yield Transition(
            "active_holder_ack_recorded_by_current_worker",
            replace(
                state,
                holder="worker",
                active_holder_contact_attempted=True,
                active_holder_ack_recorded=True,
            ),
        )
        return

    if not state.active_holder_packet_opened_through_runtime:
        yield Transition(
            "active_holder_packet_opened_through_runtime",
            replace(state, holder="worker", active_holder_packet_opened_through_runtime=True),
        )
        return

    if not state.active_holder_progress_recorded:
        yield Transition(
            "active_holder_progress_recorded_as_controller_safe_metadata",
            replace(
                state,
                holder="worker",
                active_holder_contact_attempted=True,
                active_holder_progress_recorded=True,
            ),
        )
        return

    if not state.fast_lane_initial_result_submitted:
        yield Transition(
            "active_holder_initial_result_submitted_to_router",
            replace(
                state,
                holder="worker",
                active_holder_contact_attempted=True,
                fast_lane_initial_result_submitted=True,
            ),
        )
        return

    if not state.fast_lane_mechanical_reject_recorded:
        yield Transition(
            "router_mechanically_rejects_result_to_same_holder",
            replace(
                state,
                holder="worker",
                fast_lane_mechanical_reject_recorded=True,
            ),
        )
        return

    if not state.fast_lane_result_resubmitted:
        yield Transition(
            "active_holder_resubmits_mechanically_repaired_result",
            replace(
                state,
                holder="worker",
                active_holder_contact_attempted=True,
                fast_lane_result_resubmitted=True,
            ),
        )
        return

    if not state.fast_lane_result_mechanics_passed:
        yield Transition(
            "router_accepts_fast_lane_result_mechanics",
            replace(
                state,
                holder="controller",
                fast_lane_result_mechanics_passed=True,
                worker_result_returned=True,
                worker_result_identity_boundary_present=True,
            ),
        )
        return

    if not state.worker_result_returned:
        yield Transition(
            "worker_result_returned_to_packet_ledger",
            replace(
                state,
                holder="controller",
                worker_project_write_performed=True,
                worker_result_returned=True,
                worker_result_identity_boundary_present=True,
            ),
        )
        return

    if not state.worker_result_ledger_checked:
        yield Transition(
            "worker_result_ledger_checked_before_pm_relay",
            replace(state, holder="controller", worker_result_ledger_checked=True),
        )
        return

    if not state.fast_lane_controller_notice_written:
        yield Transition(
            "router_writes_controller_notice_after_fast_lane_close",
            replace(state, holder="controller", fast_lane_controller_notice_written=True),
        )
        return

    if not state.worker_result_routed_to_pm:
        yield Transition(
            "worker_result_routed_to_pm",
            replace(
                state,
                holder="pm",
                worker_result_routed_to_pm=True,
            ),
        )
        return

    if not state.pm_result_disposition_recorded:
        yield Transition(
            "pm_records_current_node_result_disposition",
            replace(state, holder="pm", pm_result_disposition_recorded=True),
        )
        return

    if not state.pm_formal_node_gate_package_released:
        yield Transition(
            "pm_releases_current_node_formal_gate_package_to_reviewer",
            replace(state, holder="reviewer", pm_formal_node_gate_package_released=True),
        )
        return

    if not state.reviewer_worker_result_card_delivered:
        yield Transition(
            "reviewer_worker_result_review_card_delivered_after_pm_gate_release",
            replace(state, holder="reviewer", reviewer_worker_result_card_delivered=True),
        )
        return

    if state.reviewer_decision == "none":
        yield Transition(
            "reviewer_passes_current_node_result",
            replace(state, holder="reviewer", reviewer_decision="pass"),
        )
        if state.route_mutation_count < MAX_ROUTE_MUTATIONS:
            yield Transition(
                "reviewer_blocks_current_node_result",
                replace(
                    state,
                    holder="reviewer",
                    reviewer_decision="block",
                    reviewer_block_seen=True,
                    route_history_context_stale=True,
                ),
            )
        else:
            yield Transition(
                "reviewer_blocks_mutated_route_result_terminal",
                replace(
                    state,
                    status="blocked",
                    holder="reviewer",
                    reviewer_decision="block",
                    reviewer_block_seen=True,
                ),
            )
        return

    if state.reviewer_decision == "block":
        if not state.route_history_context_refreshed or state.route_history_context_stale:
            yield Transition(
                "controller_refreshes_route_history_context_for_repair_or_mutation",
                replace(
                    state,
                    holder="controller",
                    route_history_context_refreshed=True,
                    pm_prior_path_context_reviewed=False,
                    route_history_context_stale=False,
                ),
            )
            return

        if not state.pm_prior_path_context_reviewed:
            yield Transition(
                "pm_reads_prior_path_context_for_repair_or_mutation",
                replace(state, holder="pm", pm_prior_path_context_reviewed=True),
            )
            return

        if not state.repair_packet_registered:
            yield Transition(
                "pm_registers_repair_packet_after_reviewer_block",
                replace(state, holder="pm", repair_packet_registered=True),
            )
            if state.route_mutation_count < MAX_ROUTE_MUTATIONS:
                yield Transition(
                    "route_mutation_after_reviewer_block_marks_stale_evidence_and_frontier",
                    _clear_current_node_cycle(
                        state,
                        holder="pm",
                        route_version=state.route_version + 1,
                        route_mutation_count=state.route_mutation_count + 1,
                        pm_prior_path_context_used_for_route_mutation=True,
                        stale_evidence_marked=True,
                        frontier_marked_stale=True,
                        frontier_rewritten_after_mutation=False,
                    ),
                )
            return

        if not state.repair_dispatch_allowed:
            yield Transition(
                "router_direct_repair_dispatch_after_block",
                replace(state, holder="reviewer", repair_dispatch_allowed=True),
            )
            return

        if not state.repair_worker_dispatched:
            yield Transition(
                "repair_worker_dispatched_after_router_direct_dispatch",
                replace(
                    state,
                    holder="worker",
                    repair_worker_dispatched=True,
                    repair_packet_identity_boundary_present=True,
                ),
            )
            return

        if not state.repair_result_returned:
            yield Transition(
                "repair_result_returned_to_packet_ledger",
                replace(
                    state,
                    holder="controller",
                    repair_result_returned=True,
                    repair_result_identity_boundary_present=True,
                ),
            )
            return

        if not state.repair_result_ledger_checked:
            yield Transition(
                "repair_result_ledger_checked_before_reviewer_relay",
                replace(state, holder="controller", repair_result_ledger_checked=True),
            )
            return

        if not state.repair_result_routed_to_reviewer:
            yield Transition(
                "repair_result_routed_to_reviewer_after_ledger_check",
                replace(state, holder="reviewer", repair_result_routed_to_reviewer=True),
            )
            return

        if not state.repair_recheck_passed:
            yield Transition(
                "reviewer_rechecks_repair_result",
                replace(state, holder="reviewer", repair_recheck_passed=True),
            )
            return

        yield Transition(
            "reviewer_passes_current_node_after_repair_recheck",
            replace(state, holder="reviewer", reviewer_decision="pass"),
        )
        return

    if state.reviewer_decision != "pass":
        return

    if not state.pm_node_completion_card_delivered:
        yield Transition(
            "pm_node_completion_card_delivered_after_reviewer_pass",
            replace(state, holder="pm", pm_node_completion_card_delivered=True),
        )
        return

    if not state.pm_node_completed:
        yield Transition(
            "pm_completes_current_node_after_reviewer_pass",
            replace(
                state,
                holder="pm",
                pm_node_completed=True,
                route_history_context_refreshed=False,
                pm_prior_path_context_reviewed=False,
                route_history_context_stale=True,
            ),
        )
        return

    if not state.node_completion_ledger_updated:
        yield Transition(
            "node_completion_ledger_updated_after_pm_completion",
            replace(state, holder="controller", node_completion_ledger_updated=True),
        )
        return

    if not state.parent_backward_targets_enumerated:
        yield Transition(
            "pm_enumerates_parent_backward_targets_after_node_completion",
            replace(state, holder="pm", parent_backward_targets_enumerated=True),
        )
        return

    if not state.parent_backward_replay_passed:
        yield Transition(
            "reviewer_parent_backward_replay_after_targets",
            replace(state, holder="reviewer", parent_backward_replay_passed=True),
        )
        return

    if (
        not state.parent_pm_segment_decision_recorded
        and (not state.route_history_context_refreshed or state.route_history_context_stale)
    ):
        yield Transition(
            "controller_refreshes_route_history_context_for_parent_segment",
            replace(
                state,
                holder="controller",
                route_history_context_refreshed=True,
                pm_prior_path_context_reviewed=False,
                route_history_context_stale=False,
            ),
        )
        return

    if not state.parent_pm_segment_decision_recorded and not state.pm_prior_path_context_reviewed:
        yield Transition(
            "pm_reads_prior_path_context_for_parent_segment",
            replace(state, holder="pm", pm_prior_path_context_reviewed=True),
        )
        return

    if not state.parent_pm_segment_decision_recorded:
        yield Transition(
            "pm_records_parent_segment_decision_after_backward_replay",
            replace(
                state,
                holder="pm",
                parent_pm_segment_decision_recorded=True,
                parent_segment_prior_context_used=True,
            ),
        )
        return

    if not state.parent_node_completed:
        yield Transition(
            "pm_completes_parent_node_after_replay_and_segment_decision",
            replace(state, holder="pm", parent_node_completed=True),
        )
        return

    if state.route_mutation_count and not state.same_scope_replay_rerun_after_mutation:
        yield Transition(
            "reviewer_reruns_same_scope_replay_after_route_mutation",
            replace(state, holder="reviewer", same_scope_replay_rerun_after_mutation=True),
        )
        return

    if not state.current_route_scan_done:
        yield Transition(
            "current_route_scanned_for_final_ledger",
            replace(state, holder="pm", current_route_scan_done=True),
        )
        return

    if not state.pm_evidence_quality_package_card_delivered:
        yield Transition(
            "pm_evidence_quality_package_card_delivered_before_final_ledger",
            replace(
                state,
                holder="pm",
                pm_evidence_quality_package_card_delivered=True,
            ),
        )
        return

    if not state.evidence_quality_package_written:
        yield Transition(
            "pm_writes_evidence_quality_package_before_final_ledger",
            replace(
                state,
                holder="pm",
                evidence_quality_package_written=True,
                evidence_quality_prior_context_used=True,
            ),
        )
        return

    if not state.evidence_quality_review_card_delivered:
        yield Transition(
            "evidence_quality_review_card_delivered_after_package",
            replace(
                state,
                holder="reviewer",
                evidence_quality_review_card_delivered=True,
            ),
        )
        return

    if not state.evidence_quality_reviewer_passed:
        yield Transition(
            "reviewer_passes_evidence_quality_before_final_ledger",
            replace(
                state,
                holder="reviewer",
                evidence_quality_reviewer_passed=True,
                route_history_context_refreshed=False,
                pm_prior_path_context_reviewed=False,
                route_history_context_stale=True,
            ),
        )
        return

    if not state.route_history_context_refreshed or state.route_history_context_stale:
        yield Transition(
            "controller_refreshes_route_history_context_for_final_ledger",
            replace(
                state,
                holder="controller",
                route_history_context_refreshed=True,
                pm_prior_path_context_reviewed=False,
                route_history_context_stale=False,
            ),
        )
        return

    if not state.pm_prior_path_context_reviewed:
        yield Transition(
            "pm_reads_prior_path_context_for_final_ledger",
            replace(state, holder="pm", pm_prior_path_context_reviewed=True),
        )
        return

    if not state.unresolved_count_zero:
        yield Transition(
            "final_ledger_zero_unresolved_confirmed",
            replace(state, holder="pm", unresolved_count_zero=True),
        )
        yield Transition(
            "final_ledger_scan_finds_unresolved_items",
            replace(state, status="blocked", holder="pm"),
        )
        return

    if not state.pm_final_ledger_card_delivered:
        yield Transition(
            "pm_final_ledger_card_delivered_after_evidence_quality_pass",
            replace(
                state,
                holder="pm",
                pm_final_ledger_card_delivered=True,
                final_ledger_prior_context_used=True,
            ),
        )
        return

    if not state.final_ledger_source_of_truth_generated:
        yield Transition(
            "pm_generates_final_ledger_source_of_truth",
            replace(state, holder="pm", final_ledger_source_of_truth_generated=True),
        )
        return

    if not state.final_ledger_built:
        yield Transition(
            "pm_builds_clean_final_ledger",
            replace(
                state,
                holder="pm",
                final_ledger_built=True,
                final_ledger_clean=True,
                final_ledger_prior_context_used=True,
            ),
        )
        return

    if not state.terminal_replay_map_generated_from_final_ledger:
        yield Transition(
            "terminal_replay_map_generated_from_final_ledger",
            replace(
                state,
                holder="pm",
                terminal_replay_map_generated_from_final_ledger=True,
            ),
        )
        return

    if not state.terminal_replay_root_segment_passed:
        yield Transition(
            "reviewer_terminal_root_segment_replayed",
            replace(state, holder="reviewer", terminal_replay_root_segment_passed=True),
        )
        return

    if not state.terminal_replay_parent_segment_passed:
        yield Transition(
            "reviewer_terminal_parent_segment_replayed",
            replace(state, holder="reviewer", terminal_replay_parent_segment_passed=True),
        )
        return

    if not state.terminal_replay_leaf_segment_passed:
        yield Transition(
            "reviewer_terminal_leaf_segment_replayed",
            replace(state, holder="reviewer", terminal_replay_leaf_segment_passed=True),
        )
        return

    if not state.terminal_replay_pm_segment_decisions_recorded:
        yield Transition(
            "pm_records_terminal_segment_decisions",
            replace(
                state,
                holder="pm",
                terminal_replay_pm_segment_decisions_recorded=True,
            ),
        )
        return

    if not state.final_backward_replay_passed:
        if not state.final_backward_replay_card_delivered:
            yield Transition(
                "final_backward_replay_card_delivered_after_terminal_segments",
                replace(
                    state,
                    holder="reviewer",
                    final_backward_replay_card_delivered=True,
                ),
            )
            return
        yield Transition(
            "reviewer_final_backward_replay_after_all_segments",
            replace(state, holder="reviewer", final_backward_replay_passed=True),
        )
        return

    if not state.task_completion_projection_published:
        yield Transition(
            "task_completion_projection_published_from_completion_ledger",
            replace(state, holder="controller", task_completion_projection_published=True),
        )
        return

    if not state.pm_terminal_closure_card_delivered:
        yield Transition(
            "pm_terminal_closure_card_delivered_after_completion_projection",
            replace(state, holder="pm", pm_terminal_closure_card_delivered=True),
        )
        return

    yield Transition(
        "completion_recorded_after_final_replay",
        replace(state, status="complete", holder="pm"),
    )


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []

    if state.active_node_kind not in NODE_KINDS:
        failures.append("active node kind is outside the modeled event compatibility table")
    if state.controller_read_sealed_body:
        failures.append("Controller read a sealed packet/result body")
    if state.controller_originated_project_evidence:
        failures.append("Controller originated project evidence")
    if state.controller_relayed_body_content:
        failures.append("Controller relayed packet/result body content instead of envelope-only metadata")
    if state.no_next_action_detected and not state.pm_decision_required_blocker_written:
        failures.append("Controller detected no legal next action without writing a PM decision-required blocker")
    if state.no_next_action_detected and state.controller_originated_project_evidence:
        failures.append("Controller started project work after no-next-action instead of fail-closing to PM")
    if expected_role_event_waits(state) and (
        state.no_next_action_detected or state.pm_decision_required_blocker_written
    ):
        failures.append("expected role-event wait incorrectly wrote PM decision-required blocker")
    if (
        state.control_repair_wait_event != "none"
        and not _event_allowed_for_node_kind(state.control_repair_wait_event, state.active_node_kind)
    ):
        failures.append("router allowed event incompatible with active node kind")
    if (
        state.control_repair_origin == "parent_backward_replay"
        and state.control_repair_wait_event != "none"
        and state.control_repair_wait_event not in PARENT_REPAIR_SAFE_EVENTS
    ):
        failures.append("parent backward replay repair waited on non-parent-safe event")
    outcome_events = _repair_outcome_events(state)
    if (
        len(outcome_events) == 3
        and len(set(outcome_events)) == 1
        and outcome_events[0] in BUSINESS_VALIDATED_REPAIR_EVENTS
    ):
        failures.append("repair outcome table collapsed success blocker and protocol-blocker onto one business-validated event")
    for outcome_event in outcome_events:
        if not _event_allowed_for_node_kind(outcome_event, state.active_node_kind):
            failures.append("repair outcome event incompatible with active node kind")

    if state.route_activated and not state.controller_boundary_confirmed:
        failures.append("route activated before Controller relay boundary was confirmed")
    if state.officer_lifecycle_flags_current and not state.route_activated:
        failures.append("officer lifecycle flags reconciled before route activation")
    if state.officer_packet_card_delivered and not state.officer_lifecycle_flags_current:
        failures.append("officer packet card delivered before officer lifecycle flags were reconciled")
    if state.officer_packet_card_delivered and not state.route_activated:
        failures.append("officer packet card delivered before route activation")
    if state.officer_packet_relayed and not state.officer_packet_card_delivered:
        failures.append("officer packet relayed before officer card")
    if state.officer_packet_relayed and not state.officer_packet_identity_boundary_present:
        failures.append("officer packet relayed without packet recipient identity boundary")
    if state.officer_result_returned and not state.officer_packet_relayed:
        failures.append("officer result returned before officer packet relay")
    if state.officer_result_returned and not state.officer_result_identity_boundary_present:
        failures.append("officer result returned without completed-by identity boundary")
    if state.officer_result_ledger_checked and not state.officer_result_returned:
        failures.append("officer result ledger checked before officer result returned")
    if state.officer_result_routed_to_pm and not state.officer_result_ledger_checked:
        failures.append("officer result routed to PM before packet-ledger check")
    if state.pm_absorbed_officer_result and not state.officer_result_routed_to_pm:
        failures.append("PM absorbed officer result before result relay")
    if state.pm_node_high_standard_gate_opened and not (
        state.pm_absorbed_officer_result and state.pm_node_high_standard_risks_reviewed
    ):
        failures.append("PM high-standard gate opened before officer result absorption and risk review")
    if state.node_acceptance_plan_written and not state.node_acceptance_plan_prior_context_used:
        failures.append("node acceptance plan written before PM read fresh prior path context")
    if state.node_acceptance_plan_written and not state.pm_node_high_standard_gate_opened:
        failures.append("node acceptance plan written before PM high-standard gate")
    if state.node_acceptance_plan_written and not state.route_activated:
        failures.append("node acceptance plan written before route activation")
    if state.reviewer_node_acceptance_plan_reviewed and not state.node_acceptance_plan_written:
        failures.append("reviewer reviewed node acceptance plan before PM wrote it")
    if state.current_node_packet_registered and not state.route_activated:
        failures.append("current-node packet registered before route activation")
    if state.current_node_packet_registered and state.active_node_kind in PARENT_NODE_KINDS:
        failures.append("current-node packet registered for parent or module node")
    if state.current_node_packet_registered and not (
        state.node_acceptance_plan_written
        and state.reviewer_node_acceptance_plan_reviewed
        and state.pm_node_high_standard_gate_opened
    ):
        failures.append("current-node packet registered before PM high-standard gate and reviewed node acceptance plan")
    if (
        state.current_node_packet_registered
        and state.route_mutation_count
        and not state.frontier_rewritten_after_mutation
    ):
        failures.append("current-node packet registered against stale mutation frontier")

    if state.reviewer_dispatch_allowed and not state.current_node_packet_registered:
        failures.append("router direct dispatch allowed before current-node packet registration")
    if state.write_grant_issued and not state.current_node_packet_registered:
        failures.append("write grant issued before current-node packet registration")
    if state.worker_dispatched and not state.reviewer_dispatch_allowed:
        failures.append("worker dispatched before router direct dispatch")
    if state.worker_dispatched and not state.write_grant_issued:
        failures.append("worker dispatched before current-node write grant")
    if state.worker_project_write_performed and not state.write_grant_issued:
        failures.append("worker project write occurred before current-node write grant")
    if state.worker_project_write_performed and not state.active_holder_lease_issued:
        failures.append("worker project work started before active-holder lease")
    if state.worker_dispatched and not state.worker_packet_identity_boundary_present:
        failures.append("worker dispatched without packet recipient identity boundary")
    if state.active_holder_packet_family not in {"current_node", "material_scan", "research", "pm_role_work"}:
        failures.append("active-holder lease used unsupported packet family")
    if state.active_holder_lease_issued and state.active_holder_packet_family == "current_node" and not (
        state.current_node_packet_registered
        and state.write_grant_issued
        and state.reviewer_dispatch_allowed
        and state.worker_dispatched
        and state.worker_packet_identity_boundary_present
    ):
        failures.append("active-holder lease issued before current worker dispatch and write grant")
    if state.active_holder_lease_issued and state.active_holder_packet_family != "current_node" and not (
        state.generalized_packet_registered
        and state.generalized_packet_relayed
        and state.generalized_packet_identity_boundary_present
        and state.generalized_packet_live_holder_known
    ):
        failures.append(
            "generalized active-holder lease issued before packet registration, relay, identity boundary, or live holder"
        )
    if (
        state.active_holder_lease_issued
        and state.active_holder_packet_family in {"material_scan", "research", "pm_role_work"}
        and not state.generalized_result_target_is_pm
    ):
        failures.append("generalized active-holder result did not return to PM disposition path")
    if state.active_holder_contact_attempted and not state.active_holder_lease_issued:
        failures.append("active-holder contact attempted without an issued lease")
    if state.active_holder_contact_attempted and not state.active_holder_contact_is_current_holder:
        failures.append("active-holder fast lane accepted contact from a non-holder role")
    if state.active_holder_contact_attempted and not state.active_holder_contact_agent_matches:
        failures.append("active-holder fast lane accepted contact from a stale or wrong agent")
    if state.active_holder_contact_attempted and not state.active_holder_contact_packet_current:
        failures.append("active-holder fast lane accepted a stale or wrong packet")
    if state.active_holder_contact_attempted and not state.active_holder_contact_route_frontier_current:
        failures.append("active-holder fast lane accepted contact after route or frontier staleness")
    if state.active_holder_contact_attempted and not state.active_holder_contact_action_allowed:
        failures.append("active-holder fast lane accepted an action outside the lease")
    if state.active_holder_ack_recorded and not state.active_holder_contact_attempted:
        failures.append("active-holder ack recorded without a fast-lane contact attempt")
    if state.active_holder_packet_opened_through_runtime and not state.active_holder_ack_recorded:
        failures.append("active-holder packet opened through runtime before packet ack")
    if state.active_holder_progress_recorded and not state.active_holder_ack_recorded:
        failures.append("active-holder progress recorded before packet ack")
    if state.active_holder_progress_recorded and not state.active_holder_packet_opened_through_runtime:
        failures.append("active-holder progress recorded before packet body runtime open")
    if state.active_holder_progress_recorded and not state.active_holder_progress_controller_safe:
        failures.append("active-holder progress exposed sealed body, findings, evidence, or recommendations")
    if state.fast_lane_initial_result_submitted and not state.active_holder_ack_recorded:
        failures.append("active-holder result submitted before packet ack")
    if state.fast_lane_initial_result_submitted and not state.active_holder_packet_opened_through_runtime:
        failures.append("active-holder result submitted before packet body was opened through packet runtime")
    if state.fast_lane_initial_result_submitted and not state.active_holder_contact_attempted:
        failures.append("active-holder result submitted without a fast-lane contact attempt")
    if state.fast_lane_mechanical_reject_recorded and not state.fast_lane_initial_result_submitted:
        failures.append("router mechanical rejection recorded before active-holder result submission")
    if state.fast_lane_result_resubmitted and not state.fast_lane_mechanical_reject_recorded:
        failures.append("active-holder result resubmitted without prior router mechanical rejection")
    if state.fast_lane_result_mechanics_passed and not (
        state.fast_lane_initial_result_submitted
        and (
            not state.fast_lane_mechanical_reject_recorded
            or state.fast_lane_result_resubmitted
        )
    ):
        failures.append("router accepted fast-lane result mechanics before valid submit or resubmit")
    if state.worker_result_returned and not state.fast_lane_result_mechanics_passed:
        failures.append("worker result returned before active-holder mechanics pass")
    if state.worker_result_returned and not state.worker_dispatched:
        failures.append("worker result returned before worker dispatch")
    if state.worker_result_returned and not state.worker_result_identity_boundary_present:
        failures.append("worker result returned without completed-by identity boundary")
    if state.worker_result_ledger_checked and not state.worker_result_returned:
        failures.append("worker result ledger checked before result was returned")
    if state.fast_lane_controller_notice_written and not (
        state.worker_result_ledger_checked and state.fast_lane_result_mechanics_passed
    ):
        failures.append("router wrote Controller next-action notice before fast-lane mechanics and ledger check passed")
    if state.worker_result_routed_to_pm and not (
        state.worker_result_returned and state.worker_result_ledger_checked
    ):
        failures.append("worker result routed before result was returned and packet-ledger checked")
    if state.worker_result_routed_to_pm and not state.fast_lane_controller_notice_written:
        failures.append("worker result routed to PM before router wrote Controller next-action notice")
    if state.worker_result_routed_to_reviewer:
        failures.append("worker result routed directly to reviewer before PM disposition")
    if state.pm_result_disposition_recorded and not state.worker_result_routed_to_pm:
        failures.append("PM disposition recorded before worker result was routed to PM")
    if state.pm_formal_node_gate_package_released and not state.pm_result_disposition_recorded:
        failures.append("PM formal node gate package released before result disposition")
    if state.reviewer_worker_result_card_delivered and not state.pm_formal_node_gate_package_released:
        failures.append("reviewer result-review card delivered before PM formal gate package")
    if state.reviewer_decision in {"pass", "block"} and not state.pm_formal_node_gate_package_released:
        failures.append("reviewer decided before PM formal gate package release")
    if state.reviewer_decision in {"pass", "block"} and not state.reviewer_worker_result_card_delivered:
        failures.append("reviewer decided before result-review card delivery")
    if state.reviewer_decision == "pass" and not state.pm_result_disposition_recorded:
        failures.append("reviewer pass recorded before PM result disposition")
    if state.repair_packet_registered and not state.reviewer_block_seen:
        failures.append("repair packet registered before reviewer block")
    if state.repair_dispatch_allowed and not state.repair_packet_registered:
        failures.append("reviewer allowed repair dispatch before repair packet")
    if state.repair_worker_dispatched and not state.repair_dispatch_allowed:
        failures.append("repair worker dispatched before router direct repair dispatch")
    if state.repair_worker_dispatched and not state.repair_packet_identity_boundary_present:
        failures.append("repair worker dispatched without packet recipient identity boundary")
    if state.repair_result_returned and not state.repair_worker_dispatched:
        failures.append("repair result returned before repair worker dispatch")
    if state.repair_result_returned and not state.repair_result_identity_boundary_present:
        failures.append("repair result returned without completed-by identity boundary")
    if state.repair_result_ledger_checked and not state.repair_result_returned:
        failures.append("repair result ledger checked before repair result returned")
    if state.repair_result_routed_to_reviewer and not (
        state.repair_result_returned and state.repair_result_ledger_checked
    ):
        failures.append("repair result routed before result was returned and packet-ledger checked")
    if state.repair_recheck_passed and not state.repair_result_routed_to_reviewer:
        failures.append("repair recheck passed before repair result reached reviewer")
    if (
        state.reviewer_block_seen
        and state.route_mutation_count == 0
        and state.reviewer_decision == "pass"
        and not state.repair_recheck_passed
    ):
        failures.append("reviewer pass after block recorded without repair recheck")
    if state.pm_node_completed and state.reviewer_decision != "pass":
        failures.append("PM completed current node before reviewer pass")
    if state.pm_node_completion_card_delivered and state.reviewer_decision != "pass":
        failures.append("PM node completion card delivered before reviewer pass")
    if state.pm_node_completed and state.reviewer_block_seen and not (
        state.route_mutation_count or state.repair_recheck_passed
    ):
        failures.append("PM completed repaired node before reviewer recheck or route mutation")
    if state.node_completion_ledger_updated and not state.pm_node_completed:
        failures.append("node completion ledger updated before PM node completion")
    if state.parent_backward_targets_enumerated and not state.pm_node_completed:
        failures.append("parent backward targets enumerated before current node completion")
    if state.parent_backward_targets_enumerated and not state.node_completion_ledger_updated:
        failures.append("parent backward targets enumerated before node completion ledger update")
    if state.parent_backward_replay_passed and not state.parent_backward_targets_enumerated:
        failures.append("parent backward replay passed before parent backward targets")
    if state.parent_pm_segment_decision_recorded and not state.parent_backward_replay_passed:
        failures.append("PM parent segment decision recorded before parent backward replay")
    if state.parent_pm_segment_decision_recorded and not state.parent_segment_prior_context_used:
        failures.append("PM parent segment decision recorded before PM read fresh prior path context")
    if state.parent_node_completed and not (
        state.parent_backward_replay_passed
        and state.parent_pm_segment_decision_recorded
    ):
        failures.append("parent node completed before parent backward replay and PM segment decision")

    if state.route_mutation_count and not state.reviewer_block_seen:
        failures.append("route mutation recorded without reviewer block")
    if state.route_mutation_count and not state.stale_evidence_marked:
        failures.append("route mutation did not mark affected evidence stale")
    if state.route_mutation_count and not state.frontier_marked_stale:
        failures.append("route mutation did not mark the execution frontier stale")
    if state.route_mutation_count and not state.pm_prior_path_context_used_for_route_mutation:
        failures.append("route mutation recorded before PM used prior path context")
    if state.frontier_rewritten_after_mutation and not state.route_mutation_count:
        failures.append("frontier rewrite recorded without a route mutation")
    if state.same_scope_replay_rerun_after_mutation and not (
        state.route_mutation_count and state.parent_node_completed
    ):
        failures.append("same-scope replay rerun recorded without route mutation and parent completion")

    if state.current_route_scan_done and not state.parent_node_completed:
        failures.append("current route scanned for final ledger before parent node completion")
    if (
        state.current_route_scan_done
        and state.route_mutation_count
        and not state.same_scope_replay_rerun_after_mutation
    ):
        failures.append("current route scanned for final ledger before same-scope replay rerun after mutation")
    if state.pm_evidence_quality_package_card_delivered and not state.current_route_scan_done:
        failures.append("PM evidence/quality package card delivered before current route scan")
    if state.evidence_quality_package_written and not (
        state.pm_evidence_quality_package_card_delivered
        and state.current_route_scan_done
    ):
        failures.append("PM evidence/quality package written before package card and current route scan")
    if state.evidence_quality_package_written and not state.evidence_quality_prior_context_used:
        failures.append("PM evidence/quality package written before PM read fresh prior path context")
    if state.evidence_quality_review_card_delivered and not state.evidence_quality_package_written:
        failures.append("evidence quality review card delivered before PM evidence/quality package")
    if state.evidence_quality_reviewer_passed and not state.evidence_quality_package_written:
        failures.append("reviewer evidence quality pass recorded before PM evidence/quality package")
    if state.evidence_quality_reviewer_passed and not state.evidence_quality_review_card_delivered:
        failures.append("reviewer evidence quality pass recorded before evidence quality review card")
    if state.unresolved_count_zero and not state.current_route_scan_done:
        failures.append("zero unresolved final ledger count confirmed before current route scan")
    if state.unresolved_count_zero and state.stale_or_unresolved_evidence_present:
        failures.append("zero unresolved final ledger count confirmed while stale or unresolved evidence remained")
    if state.unresolved_count_zero and state.pending_generated_resources:
        failures.append("zero unresolved final ledger count confirmed while generated resources were still pending")
    if state.unresolved_count_zero and (
        state.ui_visual_required and not state.ui_visual_screenshots_present
    ):
        failures.append("zero unresolved final ledger count confirmed before required UI/visual screenshots existed")
    if state.unresolved_count_zero and state.old_assets_reused_as_current_evidence:
        failures.append("zero unresolved final ledger count confirmed while old assets were reused as current evidence")
    if state.pm_final_ledger_card_delivered and not state.pm_evidence_quality_package_card_delivered:
        failures.append("PM final ledger card delivered before PM evidence/quality package card")
    if state.pm_final_ledger_card_delivered and not state.evidence_quality_reviewer_passed:
        failures.append("PM final ledger card delivered before reviewer evidence quality pass")
    if state.pm_final_ledger_card_delivered and not state.final_ledger_prior_context_used:
        failures.append("PM final ledger card delivered before PM read fresh prior path context")
    if state.final_ledger_source_of_truth_generated and not (
        state.current_route_scan_done
        and state.unresolved_count_zero
        and state.pm_final_ledger_card_delivered
        and state.evidence_quality_reviewer_passed
    ):
        failures.append("final ledger source of truth generated before current route scan, zero unresolved, final-ledger card, and reviewer evidence quality pass")
    if state.final_ledger_built and not (
        state.parent_node_completed
        and state.current_route_scan_done
        and state.unresolved_count_zero
        and state.pm_final_ledger_card_delivered
        and state.evidence_quality_reviewer_passed
        and state.final_ledger_source_of_truth_generated
    ):
        failures.append("final ledger built before parent node completion, current route scan, zero unresolved, final-ledger card, evidence quality reviewer pass, and source-of-truth generation")
    if state.final_ledger_built and not state.final_ledger_prior_context_used:
        failures.append("final ledger built before PM read fresh prior path context")
    if state.final_ledger_built and state.stale_or_unresolved_evidence_present:
        failures.append("final ledger built while stale or unresolved evidence remained")
    if state.final_ledger_built and state.pending_generated_resources:
        failures.append("final ledger built while generated resources were still pending")
    if state.final_ledger_built and (
        state.ui_visual_required and not state.ui_visual_screenshots_present
    ):
        failures.append("final ledger built before required UI/visual screenshots existed")
    if state.final_ledger_built and state.old_assets_reused_as_current_evidence:
        failures.append("final ledger built while old assets were reused as current evidence")
    if state.final_ledger_clean and not state.final_ledger_built:
        failures.append("final ledger marked clean before it was built")
    if state.terminal_replay_map_generated_from_final_ledger and not (
        state.final_ledger_clean and state.final_ledger_source_of_truth_generated
    ):
        failures.append("terminal replay map generated before clean source-of-truth final ledger")
    if state.terminal_replay_root_segment_passed and not state.terminal_replay_map_generated_from_final_ledger:
        failures.append("terminal root segment replayed before replay map generation")
    if state.terminal_replay_parent_segment_passed and not state.terminal_replay_root_segment_passed:
        failures.append("terminal parent segment replayed before root segment")
    if state.terminal_replay_leaf_segment_passed and not state.terminal_replay_parent_segment_passed:
        failures.append("terminal leaf segment replayed before parent segment")
    if state.terminal_replay_pm_segment_decisions_recorded and not (
        state.terminal_replay_root_segment_passed
        and state.terminal_replay_parent_segment_passed
        and state.terminal_replay_leaf_segment_passed
    ):
        failures.append("PM terminal segment decisions recorded before all terminal replay segments")
    if state.final_backward_replay_passed and not (
        state.final_ledger_clean
        and state.terminal_replay_map_generated_from_final_ledger
        and state.terminal_replay_pm_segment_decisions_recorded
    ):
        failures.append("final backward replay passed before clean ledger, replay map, and PM segment decisions")
    if (
        state.final_backward_replay_card_delivered
        and not state.terminal_replay_pm_segment_decisions_recorded
    ):
        failures.append("final backward replay card delivered before terminal replay segment decisions")
    if state.final_backward_replay_passed and not state.final_backward_replay_card_delivered:
        failures.append("final backward replay passed before reviewer card delivery")
    if state.task_completion_projection_published and not (
        state.node_completion_ledger_updated and state.final_backward_replay_passed
    ):
        failures.append("task completion projection published before node completion ledger and final backward replay")
    if state.pm_terminal_closure_card_delivered and not state.task_completion_projection_published:
        failures.append("PM terminal closure card delivered before task completion projection")
    if state.status == "complete" and not state.final_backward_replay_passed:
        failures.append("completion recorded before final backward replay")
    if state.status == "complete" and not state.pm_terminal_closure_card_delivered:
        failures.append("completion recorded before PM terminal closure card")
    if state.status == "complete" and not state.task_completion_projection_published:
        failures.append("completion recorded before task completion projection was derived from completion ledger")

    return failures


def router_loop_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_router_current_node_packet_loop",
        description=(
            "The current-node packet loop requires route activation before packet "
            "registration, a PM high-standard gate and reviewed node acceptance "
            "plan before the packet, officer lifecycle flags before officer "
            "packet relay, controller no-next-action states fail-close to PM, "
            "expected role-event waits never materialize PM blockers, "
            "current-node packets gate write grants, router direct dispatch before "
            "worker or repair work, "
            "packet-ledger checks before worker/officer result relay, PM result "
            "disposition before formal reviewer node-completion gates, reviewer "
            "recheck before repaired completion, reviewer-blocked route mutation "
            "with stale evidence/frontier markers, same-scope replay after "
            "mutation, node completion ledger updates before parent backward replay "
            "or task completion projection, parent backward replay plus PM segment "
            "decision before parent completion, evidence-quality review and resource closure "
            "before final ledger source of truth, and clean final ledger before "
            "segmented terminal backward replay."
        ),
        predicate=router_loop_invariant,
    ),
)


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 110


def build_workflow() -> Workflow:
    return Workflow((RouterLoopStep(),), name="flowpilot_router_current_node_loop")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


def _active_packet_loop(**changes: object) -> State:
    base = State(
        status="running",
        holder="reviewer",
        route_version=1,
        controller_boundary_confirmed=True,
        route_activated=True,
        officer_packet_card_delivered=True,
        officer_packet_relayed=True,
        officer_packet_identity_boundary_present=True,
        officer_result_returned=True,
        officer_result_identity_boundary_present=True,
        officer_result_ledger_checked=True,
        officer_result_routed_to_pm=True,
        pm_absorbed_officer_result=True,
        officer_lifecycle_flags_current=True,
        route_history_context_refreshed=True,
        pm_prior_path_context_reviewed=True,
        node_acceptance_plan_prior_context_used=True,
        pm_node_high_standard_gate_opened=True,
        pm_node_high_standard_risks_reviewed=True,
        node_acceptance_plan_written=True,
        reviewer_node_acceptance_plan_reviewed=True,
        current_node_packet_registered=True,
        write_grant_issued=True,
        reviewer_dispatch_allowed=True,
        worker_dispatched=True,
        worker_project_write_performed=True,
        worker_packet_identity_boundary_present=True,
        active_holder_lease_issued=True,
        active_holder_contact_attempted=True,
        active_holder_ack_recorded=True,
        active_holder_packet_opened_through_runtime=True,
        active_holder_progress_recorded=True,
        fast_lane_initial_result_submitted=True,
        fast_lane_mechanical_reject_recorded=True,
        fast_lane_result_resubmitted=True,
        fast_lane_result_mechanics_passed=True,
        fast_lane_controller_notice_written=True,
        worker_result_returned=True,
        worker_result_identity_boundary_present=True,
        worker_result_ledger_checked=True,
        worker_result_routed_to_pm=True,
        pm_result_disposition_recorded=True,
        pm_formal_node_gate_package_released=True,
        reviewer_worker_result_card_delivered=True,
    )
    return replace(base, **changes)


def _reviewer_passed(**changes: object) -> State:
    return _active_packet_loop(reviewer_decision="pass", **changes)


def _reviewer_blocked(**changes: object) -> State:
    return _active_packet_loop(
        reviewer_decision="block",
        reviewer_block_seen=True,
        **changes,
    )


def _mutated(**changes: object) -> State:
    base = State(
        status="running",
        holder="pm",
        route_version=2,
        controller_boundary_confirmed=True,
        route_mutation_count=1,
        reviewer_block_seen=True,
        pm_prior_path_context_used_for_route_mutation=True,
        stale_evidence_marked=True,
        frontier_marked_stale=True,
        route_history_context_stale=True,
    )
    return replace(base, **changes)


def _active_holder_leased(**changes: object) -> State:
    base = State(
        status="running",
        holder="worker",
        route_version=1,
        controller_boundary_confirmed=True,
        route_activated=True,
        officer_lifecycle_flags_current=True,
        officer_packet_card_delivered=True,
        officer_packet_relayed=True,
        officer_packet_identity_boundary_present=True,
        officer_result_returned=True,
        officer_result_identity_boundary_present=True,
        officer_result_ledger_checked=True,
        officer_result_routed_to_pm=True,
        pm_absorbed_officer_result=True,
        route_history_context_refreshed=True,
        pm_prior_path_context_reviewed=True,
        node_acceptance_plan_prior_context_used=True,
        pm_node_high_standard_gate_opened=True,
        pm_node_high_standard_risks_reviewed=True,
        node_acceptance_plan_written=True,
        reviewer_node_acceptance_plan_reviewed=True,
        current_node_packet_registered=True,
        write_grant_issued=True,
        reviewer_dispatch_allowed=True,
        worker_dispatched=True,
        worker_packet_identity_boundary_present=True,
        active_holder_lease_issued=True,
    )
    return replace(base, **changes)


def _generalized_active_holder_leased(packet_family: str, **changes: object) -> State:
    base = State(
        status="running",
        holder="worker",
        route_version=1,
        controller_boundary_confirmed=True,
        route_activated=True,
        active_holder_lease_issued=True,
        active_holder_packet_family=packet_family,
        generalized_packet_registered=True,
        generalized_packet_relayed=True,
        generalized_packet_identity_boundary_present=True,
        generalized_packet_live_holder_known=True,
        generalized_result_target_is_pm=True,
    )
    return replace(base, **changes)


def _node_completed(**changes: object) -> State:
    return _reviewer_passed(
        pm_node_completion_card_delivered=True,
        pm_node_completed=True,
        node_completion_ledger_updated=True,
        **changes,
    )


def _parent_completed(**changes: object) -> State:
    base = _node_completed(
        parent_backward_targets_enumerated=True,
        parent_backward_replay_passed=True,
        parent_pm_segment_decision_recorded=True,
        parent_node_completed=True,
        parent_segment_prior_context_used=True,
        route_history_context_refreshed=False,
        pm_prior_path_context_reviewed=False,
        route_history_context_stale=True,
    )
    return replace(base, **changes)


def _final_ready(**changes: object) -> State:
    base = _parent_completed(
        current_route_scan_done=True,
        pm_evidence_quality_package_card_delivered=True,
        evidence_quality_package_written=True,
        evidence_quality_prior_context_used=True,
        evidence_quality_review_card_delivered=True,
        evidence_quality_reviewer_passed=True,
        route_history_context_refreshed=True,
        pm_prior_path_context_reviewed=True,
        route_history_context_stale=False,
        unresolved_count_zero=True,
        pm_final_ledger_card_delivered=True,
        final_ledger_source_of_truth_generated=True,
        final_ledger_built=True,
        final_ledger_clean=True,
        final_ledger_prior_context_used=True,
        terminal_replay_map_generated_from_final_ledger=True,
        terminal_replay_root_segment_passed=True,
        terminal_replay_parent_segment_passed=True,
        terminal_replay_leaf_segment_passed=True,
        terminal_replay_pm_segment_decisions_recorded=True,
    )
    return replace(base, **changes)


def hazard_states() -> dict[str, State]:
    hazards = {
        "packet_registered_before_route_activation": State(
            status="running",
            controller_boundary_confirmed=True,
            current_node_packet_registered=True,
        ),
        "officer_packet_card_before_route_activation": State(
            status="running",
            controller_boundary_confirmed=True,
            officer_packet_card_delivered=True,
        ),
        "officer_packet_card_before_lifecycle_flags": State(
            status="running",
            controller_boundary_confirmed=True,
            route_version=1,
            route_activated=True,
            officer_packet_card_delivered=True,
            officer_lifecycle_flags_current=False,
        ),
        "officer_packet_relayed_without_officer_card": State(
            status="running",
            controller_boundary_confirmed=True,
            route_version=1,
            route_activated=True,
            officer_packet_relayed=True,
        ),
        "officer_result_routed_without_ledger_check": State(
            status="running",
            controller_boundary_confirmed=True,
            route_version=1,
            route_activated=True,
            officer_packet_card_delivered=True,
            officer_packet_relayed=True,
            officer_result_returned=True,
            officer_result_routed_to_pm=True,
            officer_result_ledger_checked=False,
        ),
        "worker_dispatched_before_reviewer_dispatch": State(
            status="running",
            controller_boundary_confirmed=True,
            route_version=1,
            route_activated=True,
            node_acceptance_plan_written=True,
            reviewer_node_acceptance_plan_reviewed=True,
            current_node_packet_registered=True,
            worker_dispatched=True,
        ),
        "reviewer_acceptance_plan_review_without_plan": State(
            status="running",
            controller_boundary_confirmed=True,
            route_version=1,
            route_activated=True,
            reviewer_node_acceptance_plan_reviewed=True,
        ),
        "node_acceptance_plan_without_pm_high_standard_gate": State(
            status="running",
            controller_boundary_confirmed=True,
            route_version=1,
            route_activated=True,
            officer_lifecycle_flags_current=True,
            route_history_context_refreshed=True,
            pm_prior_path_context_reviewed=True,
            node_acceptance_plan_written=True,
        ),
        "node_acceptance_plan_without_prior_path_context": State(
            status="running",
            controller_boundary_confirmed=True,
            route_version=1,
            route_activated=True,
            officer_lifecycle_flags_current=True,
            pm_node_high_standard_gate_opened=True,
            pm_node_high_standard_risks_reviewed=True,
            node_acceptance_plan_written=True,
            route_history_context_refreshed=False,
            pm_prior_path_context_reviewed=False,
        ),
        "packet_registered_before_acceptance_plan_review": State(
            status="running",
            controller_boundary_confirmed=True,
            route_version=1,
            route_activated=True,
            pm_node_high_standard_gate_opened=True,
            pm_node_high_standard_risks_reviewed=True,
            current_node_packet_registered=True,
        ),
        "parent_node_current_packet_registered": State(
            status="running",
            controller_boundary_confirmed=True,
            route_version=1,
            route_activated=True,
            active_node_kind="parent",
            pm_node_high_standard_gate_opened=True,
            pm_node_high_standard_risks_reviewed=True,
            node_acceptance_plan_written=True,
            reviewer_node_acceptance_plan_reviewed=True,
            current_node_packet_registered=True,
        ),
        "control_repair_wait_event_incompatible_with_parent": State(
            status="running",
            controller_boundary_confirmed=True,
            route_version=1,
            route_activated=True,
            active_node_kind="parent",
            control_repair_origin="parent_backward_replay",
            control_repair_wait_event="pm_registers_current_node_packet",
        ),
        "parent_backward_repair_targets_leaf_dispatch": State(
            status="running",
            controller_boundary_confirmed=True,
            route_version=1,
            route_activated=True,
            active_node_kind="parent",
            control_repair_origin="parent_backward_replay",
            control_repair_wait_event="pm_registers_current_node_packet",
            repair_outcome_success_event="pm_registers_current_node_packet",
            repair_outcome_blocker_event="pm_registers_current_node_packet",
            repair_outcome_protocol_blocker_event="pm_registers_current_node_packet",
        ),
        "collapsed_repair_outcomes_on_business_validated_event": State(
            status="running",
            controller_boundary_confirmed=True,
            route_version=1,
            route_activated=True,
            active_node_kind="leaf",
            control_repair_origin="current_node_result",
            control_repair_wait_event="pm_registers_current_node_packet",
            repair_outcome_success_event="pm_registers_current_node_packet",
            repair_outcome_blocker_event="pm_registers_current_node_packet",
            repair_outcome_protocol_blocker_event="pm_registers_current_node_packet",
        ),
        "write_grant_before_packet_registration": State(
            status="running",
            controller_boundary_confirmed=True,
            route_version=1,
            route_activated=True,
            write_grant_issued=True,
        ),
        "worker_dispatched_before_write_grant": _active_packet_loop(
            write_grant_issued=False,
            worker_project_write_performed=False,
            worker_result_returned=False,
            worker_result_identity_boundary_present=False,
            worker_result_ledger_checked=False,
            worker_result_routed_to_pm=False,
            pm_result_disposition_recorded=False,
            pm_formal_node_gate_package_released=False,
            worker_result_routed_to_reviewer=False,
            reviewer_worker_result_card_delivered=False,
        ),
        "worker_project_write_without_grant": _active_packet_loop(
            write_grant_issued=False,
        ),
        "active_holder_lease_before_worker_dispatch": _active_holder_leased(
            worker_dispatched=False,
            worker_packet_identity_boundary_present=False,
        ),
        "current_node_packet_relayed_without_active_holder_lease": _active_holder_leased(
            active_holder_lease_issued=False,
            worker_project_write_performed=True,
        ),
        "active_holder_contact_without_lease": _active_holder_leased(
            active_holder_lease_issued=False,
            active_holder_contact_attempted=True,
        ),
        "active_holder_contact_by_wrong_role": _active_holder_leased(
            active_holder_contact_attempted=True,
            active_holder_contact_is_current_holder=False,
        ),
        "active_holder_contact_by_stale_agent": _active_holder_leased(
            active_holder_contact_attempted=True,
            active_holder_contact_agent_matches=False,
        ),
        "active_holder_contact_by_stale_packet": _active_holder_leased(
            active_holder_contact_attempted=True,
            active_holder_contact_packet_current=False,
        ),
        "active_holder_contact_after_stale_frontier": _active_holder_leased(
            active_holder_contact_attempted=True,
            active_holder_contact_route_frontier_current=False,
        ),
        "active_holder_contact_action_not_allowed": _active_holder_leased(
            active_holder_contact_attempted=True,
            active_holder_contact_action_allowed=False,
        ),
        "material_active_holder_lease_without_packet_registration": _generalized_active_holder_leased(
            "material_scan",
            generalized_packet_registered=False,
        ),
        "research_active_holder_contact_by_wrong_role": _generalized_active_holder_leased(
            "research",
            active_holder_contact_attempted=True,
            active_holder_contact_is_current_holder=False,
        ),
        "pm_role_work_active_holder_without_live_holder": _generalized_active_holder_leased(
            "pm_role_work",
            generalized_packet_live_holder_known=False,
        ),
        "generalized_active_holder_result_not_to_pm": _generalized_active_holder_leased(
            "material_scan",
            generalized_result_target_is_pm=False,
        ),
        "active_holder_unknown_packet_family": _generalized_active_holder_leased(
            "legacy_unknown",
        ),
        "fast_lane_progress_leaks_controller_visible_content": _active_holder_leased(
            active_holder_contact_attempted=True,
            active_holder_ack_recorded=True,
            active_holder_progress_recorded=True,
            active_holder_progress_controller_safe=False,
        ),
        "fast_lane_result_before_packet_ack": _active_holder_leased(
            active_holder_contact_attempted=True,
            fast_lane_initial_result_submitted=True,
            active_holder_ack_recorded=False,
        ),
        "fast_lane_result_before_packet_open": _active_holder_leased(
            active_holder_contact_attempted=True,
            active_holder_ack_recorded=True,
            fast_lane_initial_result_submitted=True,
            worker_project_write_performed=False,
        ),
        "fast_lane_mechanical_pass_marks_node_complete": _active_holder_leased(
            active_holder_contact_attempted=True,
            active_holder_ack_recorded=True,
            fast_lane_initial_result_submitted=True,
            fast_lane_result_mechanics_passed=True,
            worker_result_returned=True,
            worker_result_identity_boundary_present=True,
            pm_node_completed=True,
        ),
        "fast_lane_closes_without_controller_notice": _active_packet_loop(
            fast_lane_controller_notice_written=False,
        ),
        "fast_lane_controller_notice_before_ledger_check": _active_holder_leased(
            active_holder_contact_attempted=True,
            active_holder_ack_recorded=True,
            fast_lane_initial_result_submitted=True,
            fast_lane_result_mechanics_passed=True,
            worker_result_returned=True,
            worker_result_identity_boundary_present=True,
            worker_result_ledger_checked=False,
            fast_lane_controller_notice_written=True,
        ),
        "legacy_worker_result_return_without_fast_lane_mechanics": _active_holder_leased(
            worker_result_returned=True,
            worker_result_identity_boundary_present=True,
            fast_lane_result_mechanics_passed=False,
        ),
        "reviewer_pass_without_routed_worker_result": _active_packet_loop(
            pm_formal_node_gate_package_released=False,
            reviewer_decision="pass",
        ),
        "reviewer_result_card_before_result_relay": _active_packet_loop(
            pm_formal_node_gate_package_released=False,
            reviewer_worker_result_card_delivered=True,
        ),
        "reviewer_decision_without_result_review_card": _active_packet_loop(
            reviewer_worker_result_card_delivered=False,
            reviewer_decision="pass",
        ),
        "worker_result_routed_without_ledger_check": _active_packet_loop(
            worker_result_ledger_checked=False,
            worker_result_routed_to_pm=True,
        ),
        "worker_result_routed_directly_to_reviewer": _active_packet_loop(
            worker_result_routed_to_reviewer=True,
        ),
        "pm_completion_without_reviewer_pass": _active_packet_loop(
            reviewer_decision="none",
            pm_node_completed=True,
        ),
        "node_completion_ledger_without_pm_completion": _reviewer_passed(
            node_completion_ledger_updated=True,
        ),
        "expected_pm_completion_wait_materializes_blocker": _reviewer_passed(
            pm_node_completion_card_delivered=True,
            pm_decision_required_blocker_written=True,
        ),
        "repair_packet_without_reviewer_block": _active_packet_loop(
            repair_packet_registered=True,
            reviewer_decision="none",
            reviewer_block_seen=False,
        ),
        "repair_worker_dispatched_before_reviewer_dispatch": _reviewer_blocked(
            repair_packet_registered=True,
            repair_worker_dispatched=True,
            repair_dispatch_allowed=False,
        ),
        "repair_result_routed_without_ledger_check": _reviewer_blocked(
            repair_packet_registered=True,
            repair_dispatch_allowed=True,
            repair_worker_dispatched=True,
            repair_result_returned=True,
            repair_result_routed_to_reviewer=True,
            repair_result_ledger_checked=False,
        ),
        "repair_recheck_without_reviewer_result": _reviewer_blocked(
            repair_packet_registered=True,
            repair_dispatch_allowed=True,
            repair_worker_dispatched=True,
            repair_result_returned=True,
            repair_result_ledger_checked=True,
            repair_recheck_passed=True,
            repair_result_routed_to_reviewer=False,
        ),
        "pm_completion_after_block_without_recheck": _active_packet_loop(
            reviewer_decision="pass",
            reviewer_block_seen=True,
            repair_recheck_passed=False,
            pm_node_completed=True,
        ),
        "route_mutation_without_reviewer_block": _mutated(reviewer_block_seen=False),
        "route_mutation_without_stale_evidence": _mutated(stale_evidence_marked=False),
        "route_mutation_without_stale_frontier": _mutated(frontier_marked_stale=False),
        "route_mutation_without_prior_path_context": _mutated(
            pm_prior_path_context_used_for_route_mutation=False
        ),
        "packet_registered_against_stale_mutation_frontier": _mutated(
            route_activated=True,
            officer_lifecycle_flags_current=True,
            pm_node_high_standard_gate_opened=True,
            pm_node_high_standard_risks_reviewed=True,
            node_acceptance_plan_written=True,
            reviewer_node_acceptance_plan_reviewed=True,
            current_node_packet_registered=True,
            frontier_rewritten_after_mutation=False,
        ),
        "final_scan_before_same_scope_replay_after_mutation": _parent_completed(
            route_mutation_count=1,
            stale_evidence_marked=True,
            frontier_marked_stale=True,
            frontier_rewritten_after_mutation=True,
            same_scope_replay_rerun_after_mutation=False,
            current_route_scan_done=True,
        ),
        "parent_completed_without_backward_replay": _node_completed(
            parent_node_completed=True,
        ),
        "parent_completed_without_pm_segment_decision": _node_completed(
            parent_backward_targets_enumerated=True,
            parent_backward_replay_passed=True,
            parent_node_completed=True,
        ),
        "parent_targets_before_node_completion_ledger": _reviewer_passed(
            pm_node_completed=True,
            node_completion_ledger_updated=False,
            parent_backward_targets_enumerated=True,
        ),
        "parent_segment_decision_without_prior_path_context": _node_completed(
            parent_backward_targets_enumerated=True,
            parent_backward_replay_passed=True,
            parent_pm_segment_decision_recorded=True,
            route_history_context_refreshed=False,
            pm_prior_path_context_reviewed=False,
            route_history_context_stale=True,
        ),
        "final_ledger_card_before_evidence_quality_package_card": _parent_completed(
            current_route_scan_done=True,
            pm_final_ledger_card_delivered=True,
        ),
        "final_ledger_card_before_reviewer_evidence_quality_pass": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            pm_final_ledger_card_delivered=True,
        ),
        "expected_evidence_quality_package_wait_materializes_blocker": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=False,
            evidence_quality_review_card_delivered=False,
            evidence_quality_reviewer_passed=False,
            pm_decision_required_blocker_written=True,
        ),
        "expected_evidence_quality_review_wait_materializes_blocker": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_review_card_delivered=True,
            evidence_quality_reviewer_passed=False,
            pm_decision_required_blocker_written=True,
        ),
        "final_ledger_built_before_evidence_quality_reviewer_pass": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_built=True,
            final_ledger_clean=True,
        ),
        "final_ledger_without_parent_completion": _node_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_built=True,
            final_ledger_clean=True,
        ),
        "final_ledger_without_node_completion": State(
            status="running",
            controller_boundary_confirmed=True,
            route_version=1,
            route_activated=True,
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_built=True,
            final_ledger_clean=True,
        ),
        "final_ledger_without_current_route_scan": _parent_completed(
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_built=True,
            final_ledger_clean=True,
        ),
        "final_ledger_with_unresolved_items": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            unresolved_count_zero=False,
            pm_final_ledger_card_delivered=True,
            final_ledger_built=True,
            final_ledger_clean=True,
        ),
        "final_ledger_without_source_of_truth_generation": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            route_history_context_refreshed=True,
            pm_prior_path_context_reviewed=True,
            route_history_context_stale=False,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_source_of_truth_generated=False,
            final_ledger_built=True,
            final_ledger_clean=True,
        ),
        "final_ledger_card_without_prior_path_context": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            pm_final_ledger_card_delivered=True,
            route_history_context_refreshed=False,
            pm_prior_path_context_reviewed=False,
            route_history_context_stale=True,
        ),
        "expected_final_ledger_wait_materializes_blocker": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_review_card_delivered=True,
            evidence_quality_reviewer_passed=True,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_source_of_truth_generated=False,
            final_ledger_built=False,
            final_ledger_clean=False,
            pm_decision_required_blocker_written=True,
        ),
        "final_ledger_without_prior_path_context": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_source_of_truth_generated=True,
            final_ledger_built=True,
            final_ledger_clean=True,
            route_history_context_refreshed=False,
            pm_prior_path_context_reviewed=False,
            route_history_context_stale=True,
        ),
        "final_ledger_with_stale_or_unresolved_evidence": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            stale_or_unresolved_evidence_present=True,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_built=True,
            final_ledger_clean=True,
        ),
        "final_ledger_with_pending_generated_resources": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            pending_generated_resources=True,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_built=True,
            final_ledger_clean=True,
        ),
        "final_ledger_missing_ui_visual_screenshots": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            ui_visual_required=True,
            ui_visual_screenshots_present=False,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_built=True,
            final_ledger_clean=True,
        ),
        "final_ledger_reuses_old_assets_as_current_evidence": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            old_assets_reused_as_current_evidence=True,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_built=True,
            final_ledger_clean=True,
        ),
        "final_backward_replay_without_clean_ledger": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_source_of_truth_generated=True,
            final_ledger_built=True,
            final_ledger_clean=False,
            terminal_replay_map_generated_from_final_ledger=True,
            terminal_replay_root_segment_passed=True,
            terminal_replay_parent_segment_passed=True,
            terminal_replay_leaf_segment_passed=True,
            terminal_replay_pm_segment_decisions_recorded=True,
            final_backward_replay_passed=True,
        ),
        "terminal_replay_map_without_source_ledger": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_source_of_truth_generated=False,
            final_ledger_built=True,
            final_ledger_clean=True,
            terminal_replay_map_generated_from_final_ledger=True,
        ),
        "terminal_parent_segment_before_root": _final_ready(
            terminal_replay_map_generated_from_final_ledger=True,
            terminal_replay_root_segment_passed=False,
            terminal_replay_parent_segment_passed=True,
        ),
        "terminal_leaf_segment_before_parent": _final_ready(
            terminal_replay_map_generated_from_final_ledger=True,
            terminal_replay_root_segment_passed=True,
            terminal_replay_parent_segment_passed=False,
            terminal_replay_leaf_segment_passed=True,
        ),
        "terminal_pm_decisions_before_segments": _final_ready(
            terminal_replay_map_generated_from_final_ledger=True,
            terminal_replay_root_segment_passed=True,
            terminal_replay_parent_segment_passed=False,
            terminal_replay_leaf_segment_passed=True,
            terminal_replay_pm_segment_decisions_recorded=True,
        ),
        "final_backward_replay_without_segments": _final_ready(
            terminal_replay_map_generated_from_final_ledger=True,
            terminal_replay_root_segment_passed=True,
            terminal_replay_parent_segment_passed=True,
            terminal_replay_leaf_segment_passed=True,
            terminal_replay_pm_segment_decisions_recorded=False,
            final_backward_replay_passed=True,
        ),
        "expected_final_backward_replay_wait_materializes_blocker": _final_ready(
            final_backward_replay_card_delivered=True,
            final_backward_replay_passed=False,
            pm_decision_required_blocker_written=True,
        ),
        "controller_reads_sealed_body": State(
            status="running",
            controller_boundary_confirmed=True,
            controller_read_sealed_body=True,
        ),
        "controller_originates_project_evidence": State(
            status="running",
            controller_boundary_confirmed=True,
            controller_originated_project_evidence=True,
        ),
        "no_next_action_without_pm_blocker": State(
            status="running",
            holder="controller",
            controller_boundary_confirmed=True,
            controller_only_mode_active=True,
            no_next_action_detected=True,
            pm_decision_required_blocker_written=False,
        ),
        "true_no_next_action_without_blocker": State(
            status="running",
            holder="controller",
            controller_boundary_confirmed=True,
            controller_only_mode_active=True,
            no_next_action_detected=True,
            pm_decision_required_blocker_written=False,
        ),
        "controller_does_project_work_after_no_next_action": State(
            status="running",
            holder="controller",
            controller_boundary_confirmed=True,
            controller_only_mode_active=True,
            no_next_action_detected=True,
            pm_decision_required_blocker_written=True,
            controller_originated_project_evidence=True,
        ),
        "controller_relays_body_content": State(
            status="running",
            controller_boundary_confirmed=True,
            controller_relayed_body_content=True,
        ),
        "task_completion_projection_without_completion_ledger": _final_ready(
            node_completion_ledger_updated=False,
            final_backward_replay_passed=True,
            task_completion_projection_published=True,
        ),
        "expected_pm_terminal_closure_wait_materializes_blocker": _final_ready(
            final_backward_replay_card_delivered=True,
            final_backward_replay_passed=True,
            task_completion_projection_published=True,
            pm_terminal_closure_card_delivered=True,
            pm_decision_required_blocker_written=True,
        ),
        "completion_before_final_backward_replay": _final_ready(status="complete"),
        "completion_without_task_completion_projection": _final_ready(
            status="complete",
            final_backward_replay_passed=True,
            task_completion_projection_published=False,
        ),
    }
    hazards.update(expected_wait_hazard_states())
    return hazards


__all__ = [
    "EXPECTED_ROLE_EVENT_CONTRACTS",
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "Action",
    "EventContract",
    "State",
    "Tick",
    "Transition",
    "build_workflow",
    "expected_role_event_waits",
    "expected_wait_hazard_states",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "next_states",
    "router_loop_invariant",
]
