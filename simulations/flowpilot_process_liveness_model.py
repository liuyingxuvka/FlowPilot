"""FlowGuard model for FlowPilot process-level Router liveness.

Risk purpose:
- This is a FlowGuard model (https://github.com/liuyingxuvka/FlowGuard) for
  the middle layer between heavyweight Meta/Capability checks and focused
  Router boundary models.
- It reviews the end-to-end FlowPilot control process while preserving the
  Router mechanics that recent compressed full-flow models missed: settlement
  before next action, legal wait/event authority, blocker lanes, retry budgets,
  PM repair return gates, route mutation freshness, and terminal ledger
  convergence.
- Future agents should run this model when a change could affect the overall
  Router/Controller/PM/Reviewer/Worker flow but Meta/Capability checks are too
  expensive or too compressed for the immediate diagnostic question.
- Companion command: `python simulations/run_flowpilot_process_liveness_checks.py`.

Risk intent brief:
- Prevent FlowPilot from entering a route state that is legal-looking but cannot
  complete or block cleanly.
- Protect against stale durable evidence, stale PM repair rows, wrong event
  authority, blocker loops, PM repair dead ends, route mutation with fresh-looking
  old evidence, skipped route nodes, missing reviewer passes, and terminal
  completion before ledger/replay closure.
- Model-critical durable state: Router tick settlement, pending action, active
  wait target, allowed external event, durable evidence freshness, active
  blocker lane, retry counters, PM repair decision and return gate, route
  version/frontier freshness, per-node review/completion coverage, final
  route-wide ledger, terminal replay, and PM closure.
- Blindspot: this model is not a concrete replay adapter for every runtime file
  or packet body. It deliberately abstracts product semantics and sealed
  packet/result contents.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MAX_RETRY_BUDGET = 2
MAX_PM_REPAIR_CYCLES = 1
MAX_ROUTE_MUTATIONS = 1
ROUTE_NODE_COUNT = 3
ROUTE_NODE_MASK = (1 << ROUTE_NODE_COUNT) - 1

WAIT_EVENTS = {
    "none": "none",
    "pm_scope_decision": "pm_records_scope_decision",
    "worker_result": "worker_current_node_result_returned",
    "reviewer_result": "reviewer_records_current_node_decision",
    "pm_repair_decision": "pm_records_control_blocker_repair_decision",
    "repair_result": "worker_repair_result_returned",
    "terminal_reviewer": "reviewer_records_final_backward_replay",
    "pm_closure": "pm_records_terminal_closure",
}


def _node_bit(index: int) -> int:
    return 1 << index


def _previous_nodes_mask(index: int) -> int:
    return (1 << index) - 1


def _all_nodes_reviewed_and_completed(state: State) -> bool:
    return (
        state.node_review_pass_mask == ROUTE_NODE_MASK
        and state.node_completion_ledger_mask == ROUTE_NODE_MASK
    )


@dataclass(frozen=True)
class Tick:
    """One abstract Router process tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | controlled_blocked | complete
    phase: str = "startup"  # startup | node | repair | mutation | terminal
    holder: str = "none"  # none | router | controller | pm | reviewer | worker
    route_version: int = 0
    current_node_index: int = 0
    node_review_pass_mask: int = 0
    node_completion_ledger_mask: int = 0

    settlement_started: bool = False
    durable_evidence_pending: bool = False
    evidence_fresh: bool = False
    stale_pending_action: bool = False
    stale_blocker_present: bool = False
    stale_pm_repair_row_present: bool = False
    stale_pm_repair_row_superseded: bool = False
    next_action_exposed: bool = False
    next_action_count: int = 0

    wait_target: str = "none"
    allowed_event: str = "none"
    event_received: str = "none"
    event_reconciled: bool = False
    wrong_event_accepted: bool = False

    route_activated: bool = False
    frontier_fresh: bool = False
    node_packet_registered: bool = False
    worker_dispatched: bool = False
    worker_result_returned: bool = False
    worker_result_ledger_checked: bool = False
    worker_result_routed_to_pm: bool = False
    pm_result_disposition_recorded: bool = False
    reviewer_gate_released: bool = False
    reviewer_decision: str = "none"  # none | pass | block

    control_blocker_active: bool = False
    blocker_kind: str = "none"  # none | small_fix | route_scope | fatal_protocol
    blocker_lane: str = "none"  # none | control_plane_reissue | pm_repair | route_mutation | fatal_protocol
    retry_budget: int = MAX_RETRY_BUDGET
    retry_attempts: int = 0
    retry_budget_exhausted: bool = False
    pm_repair_requested: bool = False
    pm_repair_decision: str = "none"  # none | same_gate_repair | mutate_route | user_stop | protocol_dead_end
    pm_repair_cycles: int = 0
    repair_return_gate: str = "none"
    repair_returned_to_gate: bool = False
    repair_result_returned: bool = False
    repair_result_ledger_checked: bool = False
    reviewer_recheck_passed: bool = False

    route_mutation_recorded: bool = False
    old_evidence_marked_stale: bool = False
    frontier_marked_stale: bool = False
    frontier_rewritten_after_mutation: bool = False
    same_scope_replay_rerun: bool = False

    node_completed: bool = False
    node_completion_ledger_updated: bool = False
    parent_backward_replay_done: bool = False
    pm_parent_segment_decision_recorded: bool = False
    current_route_scan_done: bool = False
    evidence_quality_package_done: bool = False
    reviewer_evidence_quality_passed: bool = False
    unresolved_items_present: bool = False
    generated_resources_pending: bool = False
    final_ledger_source_of_truth_generated: bool = False
    final_ledger_built: bool = False
    final_ledger_clean: bool = False
    terminal_replay_map_built: bool = False
    terminal_replay_segments_passed: bool = False
    final_backward_replay_passed: bool = False
    task_completion_projection_published: bool = False
    pm_terminal_closure_approved: bool = False

    controller_read_sealed_body: bool = False
    controller_originated_project_evidence: bool = False
    controller_advanced_route: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _step(state: State, **changes: object) -> State:
    return replace(state, **changes)


def _open_wait(state: State, wait_target: str, *, holder: str = "controller") -> State:
    return replace(
        state,
        holder=holder,
        wait_target=wait_target,
        allowed_event=WAIT_EVENTS[wait_target],
        event_received="none",
        event_reconciled=False,
        next_action_exposed=True,
        next_action_count=1,
    )


def _close_wait(state: State, *, holder: str) -> State:
    return replace(
        state,
        holder=holder,
        wait_target="none",
        allowed_event="none",
        event_received="none",
        event_reconciled=False,
        next_action_exposed=False,
        next_action_count=0,
    )


def _advance_to_next_node(state: State) -> State:
    return replace(
        state,
        phase="node",
        holder="router",
        current_node_index=state.current_node_index + 1,
        node_packet_registered=False,
        worker_dispatched=False,
        worker_result_returned=False,
        worker_result_ledger_checked=False,
        worker_result_routed_to_pm=False,
        pm_result_disposition_recorded=False,
        reviewer_gate_released=False,
        reviewer_decision="none",
        control_blocker_active=False,
        blocker_kind="none",
        blocker_lane="none",
        retry_attempts=0,
        retry_budget_exhausted=False,
        pm_repair_requested=False,
        pm_repair_decision="none",
        pm_repair_cycles=0,
        repair_return_gate="none",
        repair_returned_to_gate=False,
        repair_result_returned=False,
        repair_result_ledger_checked=False,
        reviewer_recheck_passed=False,
        node_completed=False,
        node_completion_ledger_updated=False,
        parent_backward_replay_done=False,
        pm_parent_segment_decision_recorded=False,
        wait_target="none",
        allowed_event="none",
        event_received="none",
        event_reconciled=False,
        next_action_exposed=False,
        next_action_count=0,
    )


class ProcessLivenessStep:
    """Model one Router process step.

    Input x State -> Set(Output x State)
    reads: durable evidence, pending Controller action, Router wait target,
    allowed external event, blocker policy, retry counters, PM repair decision,
    route/frontier version, final ledger state
    writes: one settlement fact, one wait/action exposure, one role event
    reconciliation, one blocker/retry/repair/mutation fact, or one terminal
    closure fact
    idempotency: repeat ticks cannot duplicate next actions, consume wrong
    events, revive stale evidence, or create unbounded repair loops.
    """

    name = "ProcessLivenessStep"
    input_description = "one abstract Router process tick"
    output_description = "one control-plane process transition"
    reads = (
        "durable_evidence",
        "pending_action",
        "wait_target",
        "allowed_external_event",
        "control_blocker",
        "retry_budget",
        "pm_repair_decision",
        "route_frontier",
        "route_node_cursor",
        "node_coverage_ledger",
        "terminal_ledger",
    )
    writes = (
        "settlement_record",
        "next_action_record",
        "event_reconciliation",
        "blocker_lane",
        "repair_return_gate",
        "route_frontier",
        "node_review_coverage",
        "node_completion_coverage",
        "terminal_status",
    )
    idempotency = "one tick exposes at most one next action and consumes each event once"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"controlled_blocked", "complete"}:
        return

    if state.status == "new":
        yield Transition(
            "router_tick_starts_settlement_before_startup_action",
            _step(
                state,
                status="running",
                holder="router",
                settlement_started=True,
                durable_evidence_pending=True,
                stale_pending_action=True,
                stale_blocker_present=True,
                stale_pm_repair_row_present=True,
            ),
        )
        return

    if state.phase == "startup" and state.durable_evidence_pending:
        yield Transition(
            "settlement_resolves_stale_startup_evidence_before_next_action",
            _step(
                state,
                durable_evidence_pending=False,
                evidence_fresh=True,
                stale_pending_action=False,
                stale_blocker_present=False,
                stale_pm_repair_row_superseded=True,
            ),
        )
        return

    if state.phase == "startup" and not state.next_action_exposed and not state.route_activated:
        yield Transition(
            "router_exposes_one_pm_scope_decision_after_settlement",
            _open_wait(state, "pm_scope_decision"),
        )
        return

    if state.wait_target == "pm_scope_decision" and not state.event_reconciled:
        yield Transition(
            "pm_scope_decision_matches_router_allowed_event",
            _step(
                state,
                event_received=WAIT_EVENTS["pm_scope_decision"],
                event_reconciled=True,
            ),
        )
        return

    if state.phase == "startup" and state.event_reconciled and not state.route_activated:
        yield Transition(
            "pm_activates_route_and_fresh_frontier",
            _close_wait(
                _step(
                    state,
                    phase="node",
                    holder="pm",
                    route_activated=True,
                    frontier_fresh=True,
                    route_version=1,
                ),
                holder="pm",
            ),
        )
        return

    if state.phase == "node" and state.route_activated and not state.node_packet_registered:
        yield Transition(
            "pm_registers_current_node_packet_after_fresh_frontier",
            _step(
                state,
                holder="pm",
                node_packet_registered=True,
                next_action_exposed=False,
                next_action_count=0,
            ),
        )
        return

    if state.phase == "node" and state.node_packet_registered and not state.worker_dispatched:
        yield Transition(
            "router_dispatches_worker_after_packet_registration",
            _open_wait(
                _step(state, holder="controller", worker_dispatched=True),
                "worker_result",
            ),
        )
        return

    if state.wait_target == "worker_result" and not state.event_reconciled:
        yield Transition(
            "worker_result_event_matches_router_allowed_event",
            _step(
                state,
                worker_result_returned=True,
                event_received=WAIT_EVENTS["worker_result"],
                event_reconciled=True,
            ),
        )
        return

    if state.worker_result_returned and not state.worker_result_ledger_checked:
        yield Transition(
            "router_checks_worker_result_ledger_before_pm_relay",
            _close_wait(
                _step(state, holder="router", worker_result_ledger_checked=True),
                holder="router",
            ),
        )
        return

    if state.worker_result_ledger_checked and not state.worker_result_routed_to_pm:
        yield Transition(
            "router_routes_worker_result_to_pm_after_ledger_check",
            _step(state, holder="pm", worker_result_routed_to_pm=True),
        )
        return

    if state.worker_result_routed_to_pm and not state.pm_result_disposition_recorded:
        yield Transition(
            "pm_records_result_disposition_before_reviewer_gate",
            _step(state, holder="pm", pm_result_disposition_recorded=True),
        )
        return

    if state.pm_result_disposition_recorded and not state.reviewer_gate_released:
        yield Transition(
            "pm_releases_formal_reviewer_gate_after_disposition",
            _open_wait(
                _step(state, holder="controller", reviewer_gate_released=True),
                "reviewer_result",
            ),
        )
        return

    if state.wait_target == "reviewer_result" and not state.event_reconciled:
        yield Transition(
            "reviewer_passes_current_node_result",
            _step(
                state,
                holder="reviewer",
                reviewer_decision="pass",
                node_review_pass_mask=state.node_review_pass_mask
                | _node_bit(state.current_node_index),
                event_received=WAIT_EVENTS["reviewer_result"],
                event_reconciled=True,
            ),
        )
        yield Transition(
            "reviewer_blocks_current_node_for_same_gate_repair",
            _step(
                state,
                holder="reviewer",
                reviewer_decision="block",
                control_blocker_active=True,
                blocker_kind="small_fix",
                blocker_lane="control_plane_reissue",
                event_received=WAIT_EVENTS["reviewer_result"],
                event_reconciled=True,
            ),
        )
        if state.route_version <= MAX_ROUTE_MUTATIONS:
            yield Transition(
                "reviewer_blocks_current_node_for_route_mutation",
                _step(
                    state,
                    holder="reviewer",
                    reviewer_decision="block",
                    control_blocker_active=True,
                    blocker_kind="route_scope",
                    blocker_lane="route_mutation",
                    event_received=WAIT_EVENTS["reviewer_result"],
                    event_reconciled=True,
                ),
            )
        yield Transition(
            "reviewer_blocks_current_node_for_fatal_protocol_stop",
            _step(
                state,
                holder="reviewer",
                reviewer_decision="block",
                control_blocker_active=True,
                blocker_kind="fatal_protocol",
                blocker_lane="fatal_protocol",
                event_received=WAIT_EVENTS["reviewer_result"],
                event_reconciled=True,
            ),
        )
        return

    if state.reviewer_decision == "pass" and not state.node_completed:
        yield Transition(
            "pm_completes_node_after_reviewer_pass",
            _close_wait(_step(state, holder="pm", node_completed=True), holder="pm"),
        )
        return

    if (
        state.blocker_lane == "control_plane_reissue"
        and state.retry_attempts < state.retry_budget
        and not state.retry_budget_exhausted
    ):
        next_attempt = state.retry_attempts + 1
        yield Transition(
            f"router_runs_control_plane_reissue_attempt_{next_attempt}",
            _close_wait(
                _step(
                    state,
                    phase="repair",
                    holder="router",
                    retry_attempts=next_attempt,
                    retry_budget_exhausted=next_attempt >= state.retry_budget,
                ),
                holder="router",
            ),
        )
        return

    if (
        state.blocker_lane == "control_plane_reissue"
        and state.retry_budget_exhausted
        and not state.pm_repair_requested
    ):
        yield Transition(
            "router_escalates_exhausted_blocker_to_pm_repair",
            _open_wait(
                _step(
                    state,
                    blocker_lane="pm_repair",
                    pm_repair_requested=True,
                    pm_repair_cycles=1,
                ),
                "pm_repair_decision",
            ),
        )
        return

    if state.wait_target == "pm_repair_decision" and not state.event_reconciled:
        yield Transition(
            "pm_selects_same_gate_repair_with_return_gate",
            _close_wait(
                _step(
                    state,
                    holder="pm",
                    pm_repair_decision="same_gate_repair",
                    repair_return_gate="reviewer_result_recheck",
                    event_received=WAIT_EVENTS["pm_repair_decision"],
                    event_reconciled=True,
                ),
                holder="pm",
            ),
        )
        yield Transition(
            "pm_selects_user_stop_for_unrepairable_blocker",
            _close_wait(
                _step(
                    state,
                    holder="pm",
                    pm_repair_decision="user_stop",
                    repair_return_gate="controlled_blocked",
                    event_received=WAIT_EVENTS["pm_repair_decision"],
                    event_reconciled=True,
                ),
                holder="pm",
            ),
        )
        return

    if state.pm_repair_decision == "user_stop":
        yield Transition(
            "pm_records_controlled_blocked_stop_after_repair_decision",
            _close_wait(
                _step(state, status="controlled_blocked", holder="pm"),
                holder="pm",
            ),
        )
        return

    if (
        state.pm_repair_decision == "same_gate_repair"
        and not state.repair_result_returned
        and state.wait_target == "none"
    ):
        yield Transition(
            "repair_worker_returns_result_to_router",
            _open_wait(
                _step(state, holder="controller", repair_returned_to_gate=True),
                "repair_result",
            ),
        )
        return

    if state.wait_target == "repair_result" and not state.event_reconciled:
        yield Transition(
            "repair_result_event_matches_router_allowed_event",
            _step(
                state,
                repair_result_returned=True,
                event_received=WAIT_EVENTS["repair_result"],
                event_reconciled=True,
            ),
        )
        return

    if state.repair_result_returned and not state.repair_result_ledger_checked:
        yield Transition(
            "router_checks_repair_result_ledger_before_reviewer_return",
            _close_wait(
                _step(state, holder="router", repair_result_ledger_checked=True),
                holder="router",
            ),
        )
        return

    if state.repair_result_ledger_checked and not state.reviewer_recheck_passed:
        yield Transition(
            "same_reviewer_rechecks_repair_result_and_passes",
            _step(
                state,
                holder="reviewer",
                reviewer_recheck_passed=True,
                reviewer_decision="pass",
                node_review_pass_mask=state.node_review_pass_mask
                | _node_bit(state.current_node_index),
                control_blocker_active=False,
                blocker_kind="none",
                blocker_lane="none",
            ),
        )
        return

    if state.blocker_lane == "route_mutation" and not state.route_mutation_recorded:
        yield Transition(
            "pm_records_route_mutation_with_stale_evidence_and_frontier",
            _close_wait(
                _step(
                    state,
                    phase="mutation",
                    holder="pm",
                    route_mutation_recorded=True,
                    old_evidence_marked_stale=True,
                    frontier_marked_stale=True,
                    evidence_fresh=False,
                    frontier_fresh=False,
                    route_version=state.route_version + 1,
                ),
                holder="pm",
            ),
        )
        return

    if state.route_mutation_recorded and not state.frontier_rewritten_after_mutation:
        yield Transition(
            "router_rewrites_frontier_after_route_mutation",
            _step(
                state,
                holder="router",
                frontier_rewritten_after_mutation=True,
                frontier_fresh=True,
            ),
        )
        return

    if state.frontier_rewritten_after_mutation and not state.same_scope_replay_rerun:
        yield Transition(
            "reviewer_reruns_same_scope_replay_after_mutation",
            _step(
                state,
                holder="reviewer",
                same_scope_replay_rerun=True,
                evidence_fresh=True,
                control_blocker_active=False,
                blocker_kind="none",
                blocker_lane="none",
                reviewer_decision="pass",
                node_review_pass_mask=state.node_review_pass_mask
                | _node_bit(state.current_node_index),
            ),
        )
        return

    if state.blocker_lane == "fatal_protocol":
        yield Transition(
            "pm_records_controlled_blocked_fatal_protocol_stop",
            _close_wait(
                _step(state, status="controlled_blocked", holder="pm"),
                holder="pm",
            ),
        )
        return

    if state.node_completed and not state.node_completion_ledger_updated:
        yield Transition(
            "pm_updates_node_completion_ledger_after_node_completion",
            _step(
                state,
                holder="pm",
                node_completion_ledger_updated=True,
                node_completion_ledger_mask=state.node_completion_ledger_mask
                | _node_bit(state.current_node_index),
            ),
        )
        return

    if state.node_completion_ledger_updated and not state.parent_backward_replay_done:
        yield Transition(
            "reviewer_runs_parent_backward_replay_after_node_ledger",
            _step(state, holder="reviewer", parent_backward_replay_done=True),
        )
        return

    if state.parent_backward_replay_done and not state.pm_parent_segment_decision_recorded:
        yield Transition(
            "pm_records_parent_segment_decision_after_backward_replay",
            _step(state, holder="pm", pm_parent_segment_decision_recorded=True),
        )
        return

    if (
        state.pm_parent_segment_decision_recorded
        and not _all_nodes_reviewed_and_completed(state)
        and state.current_node_index < ROUTE_NODE_COUNT - 1
    ):
        yield Transition(
            "router_advances_to_next_node_after_parent_segment_review",
            _advance_to_next_node(state),
        )
        return

    if (
        state.pm_parent_segment_decision_recorded
        and _all_nodes_reviewed_and_completed(state)
        and not state.current_route_scan_done
    ):
        yield Transition(
            "pm_scans_current_route_for_final_ledger",
            _step(state, phase="terminal", holder="pm", current_route_scan_done=True),
        )
        return

    if state.current_route_scan_done and not state.evidence_quality_package_done:
        yield Transition(
            "pm_writes_evidence_quality_package_before_final_ledger",
            _step(state, holder="pm", evidence_quality_package_done=True),
        )
        return

    if state.evidence_quality_package_done and not state.reviewer_evidence_quality_passed:
        yield Transition(
            "reviewer_passes_evidence_quality_before_final_ledger",
            _step(state, holder="reviewer", reviewer_evidence_quality_passed=True),
        )
        return

    if state.reviewer_evidence_quality_passed and not state.final_ledger_source_of_truth_generated:
        yield Transition(
            "pm_generates_final_ledger_source_of_truth",
            _step(
                state,
                holder="pm",
                unresolved_items_present=False,
                generated_resources_pending=False,
                final_ledger_source_of_truth_generated=True,
            ),
        )
        return

    if state.final_ledger_source_of_truth_generated and not state.final_ledger_built:
        yield Transition(
            "pm_builds_clean_final_route_wide_ledger",
            _step(state, holder="pm", final_ledger_built=True, final_ledger_clean=True),
        )
        return

    if state.final_ledger_clean and not state.terminal_replay_map_built:
        yield Transition(
            "router_builds_terminal_replay_map_from_final_ledger",
            _step(state, holder="router", terminal_replay_map_built=True),
        )
        return

    if state.terminal_replay_map_built and not state.terminal_replay_segments_passed:
        yield Transition(
            "reviewer_passes_terminal_replay_segments",
            _step(state, holder="reviewer", terminal_replay_segments_passed=True),
        )
        return

    if (
        state.terminal_replay_segments_passed
        and not state.final_backward_replay_passed
        and state.wait_target == "none"
    ):
        yield Transition(
            "router_exposes_final_backward_replay_wait",
            _open_wait(
                _step(state, holder="controller"),
                "terminal_reviewer",
            ),
        )
        return

    if state.wait_target == "terminal_reviewer" and not state.event_reconciled:
        yield Transition(
            "reviewer_records_final_backward_replay_pass",
            _step(
                state,
                holder="reviewer",
                final_backward_replay_passed=True,
                event_received=WAIT_EVENTS["terminal_reviewer"],
                event_reconciled=True,
            ),
        )
        return

    if state.final_backward_replay_passed and not state.task_completion_projection_published:
        yield Transition(
            "router_publishes_task_completion_projection_from_ledger",
            _close_wait(
                _step(state, holder="router", task_completion_projection_published=True),
                holder="router",
            ),
        )
        return

    if (
        state.task_completion_projection_published
        and not state.pm_terminal_closure_approved
        and state.wait_target == "none"
    ):
        yield Transition(
            "router_exposes_pm_terminal_closure_wait",
            _open_wait(state, "pm_closure"),
        )
        return

    if state.wait_target == "pm_closure" and not state.event_reconciled:
        yield Transition(
            "pm_approves_terminal_closure_after_projection",
            _step(
                state,
                holder="pm",
                pm_terminal_closure_approved=True,
                event_received=WAIT_EVENTS["pm_closure"],
                event_reconciled=True,
            ),
        )
        return

    if state.pm_terminal_closure_approved:
        yield Transition(
            "process_liveness_complete_after_terminal_closure",
            _step(state, status="complete", holder="pm"),
        )


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []

    if state.controller_read_sealed_body:
        failures.append("Controller read a sealed packet or result body")
    if state.controller_originated_project_evidence:
        failures.append("Controller originated project evidence")
    if state.controller_advanced_route:
        failures.append("Controller advanced route state without PM authority")

    if state.next_action_count > 1:
        failures.append("Router exposed more than one next action in one tick")
    if state.next_action_exposed and not state.settlement_started:
        failures.append("Router exposed a next action before starting settlement")
    if state.next_action_exposed and state.durable_evidence_pending:
        failures.append("Router exposed a next action before durable evidence settled")
    if state.next_action_exposed and state.stale_pending_action:
        failures.append("Router exposed a next action from stale pending_action")
    if state.next_action_exposed and state.stale_blocker_present:
        failures.append("Router exposed a next action while stale blocker remained active")
    if state.stale_pm_repair_row_present and not state.stale_pm_repair_row_superseded and state.next_action_exposed:
        failures.append("Router exposed next action before superseding stale PM repair row")

    if state.wait_target != "none" and state.allowed_event == "none":
        failures.append("Router wait target had no allowed external event")
    if state.wait_target == "none" and state.allowed_event != "none":
        failures.append("Router allowed event existed without an active wait target")
    if state.event_reconciled and state.event_received != state.allowed_event:
        failures.append("Router reconciled an event that did not match the active allowed event")
    if state.wrong_event_accepted:
        failures.append("Router accepted a wrong or unauthorized external event")

    if not 0 <= state.current_node_index < ROUTE_NODE_COUNT:
        failures.append("Router current node cursor moved outside the route")
    prior_nodes = _previous_nodes_mask(state.current_node_index)
    if (
        state.current_node_index > 0
        and (
            (state.node_review_pass_mask & prior_nodes) != prior_nodes
            or (state.node_completion_ledger_mask & prior_nodes) != prior_nodes
        )
    ):
        failures.append("Router advanced to a later node before all previous nodes were reviewed and completed")
    if state.node_completion_ledger_mask & ~state.node_review_pass_mask:
        failures.append("node completion ledger includes a node without reviewer pass")
    current_node_bit = _node_bit(state.current_node_index)
    if state.node_completed and not (state.node_review_pass_mask & current_node_bit):
        failures.append("current node completed before its reviewer pass was recorded")
    if (
        state.node_completion_ledger_updated
        and not (state.node_completion_ledger_mask & current_node_bit)
    ):
        failures.append("current node completion ledger flag did not cover the current node")

    mutation_frontier_rewrite_transient = (
        state.phase == "mutation"
        and state.route_mutation_recorded
        and not state.same_scope_replay_rerun
    )
    if (
        state.node_packet_registered
        and not mutation_frontier_rewrite_transient
        and not (state.route_activated and state.frontier_fresh and state.evidence_fresh)
    ):
        failures.append("current-node packet registered before route activation, fresh frontier, and fresh evidence")
    if state.worker_dispatched and not state.node_packet_registered:
        failures.append("worker dispatched before current-node packet registration")
    if state.worker_result_ledger_checked and not state.worker_result_returned:
        failures.append("worker result ledger checked before result return")
    if state.worker_result_routed_to_pm and not state.worker_result_ledger_checked:
        failures.append("worker result routed to PM before ledger check")
    if state.reviewer_gate_released and not state.pm_result_disposition_recorded:
        failures.append("reviewer gate released before PM result disposition")
    if state.reviewer_decision != "none" and not state.reviewer_gate_released:
        failures.append("reviewer decision recorded before formal reviewer gate release")

    if state.control_blocker_active and state.blocker_kind == "none":
        failures.append("active control blocker had no blocker kind")
    if state.control_blocker_active and state.blocker_lane == "none":
        failures.append("active control blocker had no handling lane")
    if (
        state.blocker_kind == "small_fix"
        and state.blocker_lane == "pm_repair"
        and state.pm_repair_requested
        and not state.retry_budget_exhausted
    ):
        failures.append("small-fix blocker was sent to PM before local retry budget was exhausted")
    if state.blocker_kind == "small_fix" and state.blocker_lane == "route_mutation":
        failures.append("small-fix blocker was misrouted to route mutation")
    if state.blocker_kind == "route_scope" and state.blocker_lane == "control_plane_reissue":
        failures.append("route-scope blocker was misrouted to local reissue")
    if state.blocker_kind == "fatal_protocol" and state.blocker_lane not in {"fatal_protocol", "none"}:
        failures.append("fatal protocol blocker was misrouted to repair or route mutation")
    if state.blocker_lane == "pm_repair" and state.pm_repair_requested and not state.retry_budget_exhausted:
        failures.append("PM repair requested before direct retry budget was exhausted")
    if state.retry_attempts > state.retry_budget:
        failures.append("control blocker retry attempts exceeded retry budget")
    if (
        state.retry_budget_exhausted
        and state.blocker_lane == "control_plane_reissue"
        and not state.pm_repair_requested
        and state.next_action_exposed
    ):
        failures.append("exhausted control blocker stayed in direct reissue lane without PM repair")
    if state.pm_repair_cycles > MAX_PM_REPAIR_CYCLES:
        failures.append("PM repair loop exceeded the bounded repair cycle limit")
    if (
        state.pm_repair_requested
        and state.pm_repair_decision == "none"
        and state.wait_target != "pm_repair_decision"
        and state.status not in {"controlled_blocked", "complete"}
    ):
        failures.append("PM repair request had no PM decision path")
    if state.pm_repair_decision == "same_gate_repair" and state.repair_return_gate == "none":
        failures.append("PM same-gate repair decision lacked a named return gate")
    if state.repair_result_ledger_checked and not state.repair_result_returned:
        failures.append("repair result ledger checked before repair result return")
    if state.reviewer_recheck_passed and not state.repair_result_ledger_checked:
        failures.append("reviewer repair recheck passed before repair result ledger check")
    if state.reviewer_decision == "pass" and state.control_blocker_active and not state.reviewer_recheck_passed:
        failures.append("blocked node passed without repair recheck or route mutation")

    if state.route_mutation_recorded:
        if not state.old_evidence_marked_stale:
            failures.append("route mutation did not mark old evidence stale")
        if not state.frontier_marked_stale:
            failures.append("route mutation did not mark old frontier stale")
        if state.route_version > MAX_ROUTE_MUTATIONS + 1:
            failures.append("route mutation loop exceeded bounded route mutation limit")
    if (
        state.route_mutation_recorded
        and state.node_packet_registered
        and state.next_action_exposed
        and not state.frontier_rewritten_after_mutation
    ):
        failures.append("mutated route reused current-node packet before frontier rewrite")
    if state.frontier_rewritten_after_mutation and not state.same_scope_replay_rerun and state.current_route_scan_done:
        failures.append("final route scan started before same-scope replay after mutation")

    if state.node_completed and state.reviewer_decision != "pass":
        failures.append("node completed before reviewer pass")
    if state.node_completion_ledger_updated and not state.node_completed:
        failures.append("node completion ledger updated before PM node completion")
    if state.parent_backward_replay_done and not state.node_completion_ledger_updated:
        failures.append("parent backward replay ran before node completion ledger")
    if state.pm_parent_segment_decision_recorded and not state.parent_backward_replay_done:
        failures.append("PM parent segment decision recorded before parent backward replay")
    if state.current_route_scan_done and state.route_mutation_recorded and not state.same_scope_replay_rerun:
        failures.append("current route scan ran before mutation same-scope replay")
    if state.current_route_scan_done and not _all_nodes_reviewed_and_completed(state):
        failures.append("current route scan ran before every route node was reviewed and completed")
    if state.final_ledger_built:
        if not state.current_route_scan_done:
            failures.append("final ledger built before current route scan")
        if not _all_nodes_reviewed_and_completed(state):
            failures.append("final ledger built before every route node was reviewed and completed")
        if not state.reviewer_evidence_quality_passed:
            failures.append("final ledger built before reviewer evidence-quality pass")
        if not state.final_ledger_source_of_truth_generated:
            failures.append("final ledger built before source-of-truth generation")
        if state.unresolved_items_present:
            failures.append("final ledger built while unresolved items remained")
        if state.generated_resources_pending:
            failures.append("final ledger built while generated resources were pending")
        if state.route_mutation_recorded and not state.old_evidence_marked_stale:
            failures.append("final ledger built without stale evidence quarantine after mutation")
    if state.terminal_replay_map_built and not state.final_ledger_clean:
        failures.append("terminal replay map built before clean final ledger")
    if state.terminal_replay_segments_passed and not state.terminal_replay_map_built:
        failures.append("terminal replay segments passed before replay map")
    if state.final_backward_replay_passed and not state.terminal_replay_segments_passed:
        failures.append("final backward replay passed before terminal replay segments")
    if state.task_completion_projection_published and not state.final_backward_replay_passed:
        failures.append("task completion projection published before final backward replay")
    if state.pm_terminal_closure_approved and not state.task_completion_projection_published:
        failures.append("PM closure approved before task completion projection")
    if state.status == "complete" and not state.pm_terminal_closure_approved:
        failures.append("process completed before PM terminal closure approval")
    if state.status == "complete" and not _all_nodes_reviewed_and_completed(state):
        failures.append("process completed before every route node was reviewed and completed")

    return failures


def _invariant(name: str, expected: str) -> Invariant:
    def check(state: State, trace) -> InvariantResult:
        del trace
        failures = invariant_failures(state)
        if expected in failures:
            return InvariantResult.fail(expected)
        return InvariantResult.pass_()

    return Invariant(name=name, description=expected, predicate=check)


INVARIANTS = (
    _invariant("controller_never_reads_sealed_body", "Controller read a sealed packet or result body"),
    _invariant("controller_never_originates_project_evidence", "Controller originated project evidence"),
    _invariant("controller_never_advances_route", "Controller advanced route state without PM authority"),
    _invariant("one_next_action_per_tick", "Router exposed more than one next action in one tick"),
    _invariant("settlement_before_next_action", "Router exposed a next action before starting settlement"),
    _invariant("durable_evidence_settled_before_next_action", "Router exposed a next action before durable evidence settled"),
    _invariant("stale_pending_action_not_used", "Router exposed a next action from stale pending_action"),
    _invariant("stale_blocker_not_active_before_next_action", "Router exposed a next action while stale blocker remained active"),
    _invariant("stale_pm_repair_row_superseded_before_next_action", "Router exposed next action before superseding stale PM repair row"),
    _invariant("wait_target_has_allowed_event", "Router wait target had no allowed external event"),
    _invariant("allowed_event_requires_wait_target", "Router allowed event existed without an active wait target"),
    _invariant("reconciled_event_matches_allowed_event", "Router reconciled an event that did not match the active allowed event"),
    _invariant("wrong_event_not_accepted", "Router accepted a wrong or unauthorized external event"),
    _invariant("node_cursor_stays_in_route", "Router current node cursor moved outside the route"),
    _invariant("advance_requires_prior_node_reviews", "Router advanced to a later node before all previous nodes were reviewed and completed"),
    _invariant("completion_ledger_subset_of_reviewer_passes", "node completion ledger includes a node without reviewer pass"),
    _invariant("current_node_completion_requires_current_review", "current node completed before its reviewer pass was recorded"),
    _invariant("node_ledger_covers_current_node", "current node completion ledger flag did not cover the current node"),
    _invariant("packet_registration_requires_fresh_route", "current-node packet registered before route activation, fresh frontier, and fresh evidence"),
    _invariant("worker_dispatch_requires_packet", "worker dispatched before current-node packet registration"),
    _invariant("worker_result_ledger_after_return", "worker result ledger checked before result return"),
    _invariant("worker_result_pm_relay_after_ledger", "worker result routed to PM before ledger check"),
    _invariant("reviewer_gate_after_pm_disposition", "reviewer gate released before PM result disposition"),
    _invariant("reviewer_decision_after_formal_gate", "reviewer decision recorded before formal reviewer gate release"),
    _invariant("control_blocker_has_kind", "active control blocker had no blocker kind"),
    _invariant("control_blocker_has_lane", "active control blocker had no handling lane"),
    _invariant("small_fix_not_pm_before_retry", "small-fix blocker was sent to PM before local retry budget was exhausted"),
    _invariant("small_fix_not_route_mutation", "small-fix blocker was misrouted to route mutation"),
    _invariant("route_scope_not_local_reissue", "route-scope blocker was misrouted to local reissue"),
    _invariant("fatal_protocol_not_repair", "fatal protocol blocker was misrouted to repair or route mutation"),
    _invariant("pm_repair_after_retry_exhaustion", "PM repair requested before direct retry budget was exhausted"),
    _invariant("retry_attempts_bounded", "control blocker retry attempts exceeded retry budget"),
    _invariant("retry_exhaustion_escalates", "exhausted control blocker stayed in direct reissue lane without PM repair"),
    _invariant("pm_repair_cycle_bounded", "PM repair loop exceeded the bounded repair cycle limit"),
    _invariant("pm_repair_has_decision_path", "PM repair request had no PM decision path"),
    _invariant("same_gate_repair_has_return_gate", "PM same-gate repair decision lacked a named return gate"),
    _invariant("repair_result_ledger_after_return", "repair result ledger checked before repair result return"),
    _invariant("repair_recheck_after_ledger", "reviewer repair recheck passed before repair result ledger check"),
    _invariant("blocked_node_needs_repair_or_mutation", "blocked node passed without repair recheck or route mutation"),
    _invariant("route_mutation_marks_old_evidence_stale", "route mutation did not mark old evidence stale"),
    _invariant("route_mutation_marks_frontier_stale", "route mutation did not mark old frontier stale"),
    _invariant("route_mutation_loop_bounded", "route mutation loop exceeded bounded route mutation limit"),
    _invariant("mutation_rewrites_frontier_before_packet_reuse", "mutated route reused current-node packet before frontier rewrite"),
    _invariant("mutation_replay_before_final_scan", "final route scan started before same-scope replay after mutation"),
    _invariant("node_completion_requires_reviewer_pass", "node completed before reviewer pass"),
    _invariant("node_ledger_after_completion", "node completion ledger updated before PM node completion"),
    _invariant("parent_replay_after_node_ledger", "parent backward replay ran before node completion ledger"),
    _invariant("parent_segment_after_replay", "PM parent segment decision recorded before parent backward replay"),
    _invariant("route_scan_after_mutation_replay", "current route scan ran before mutation same-scope replay"),
    _invariant("route_scan_after_all_node_reviews", "current route scan ran before every route node was reviewed and completed"),
    _invariant("final_ledger_after_current_route_scan", "final ledger built before current route scan"),
    _invariant("final_ledger_after_all_node_reviews", "final ledger built before every route node was reviewed and completed"),
    _invariant("final_ledger_after_evidence_quality", "final ledger built before reviewer evidence-quality pass"),
    _invariant("final_ledger_after_source_of_truth", "final ledger built before source-of-truth generation"),
    _invariant("final_ledger_zero_unresolved", "final ledger built while unresolved items remained"),
    _invariant("final_ledger_no_pending_resources", "final ledger built while generated resources were pending"),
    _invariant("final_ledger_quarantines_stale_mutation_evidence", "final ledger built without stale evidence quarantine after mutation"),
    _invariant("terminal_replay_map_after_clean_ledger", "terminal replay map built before clean final ledger"),
    _invariant("terminal_segments_after_replay_map", "terminal replay segments passed before replay map"),
    _invariant("final_backward_replay_after_segments", "final backward replay passed before terminal replay segments"),
    _invariant("completion_projection_after_final_replay", "task completion projection published before final backward replay"),
    _invariant("pm_closure_after_completion_projection", "PM closure approved before task completion projection"),
    _invariant("completion_after_pm_closure", "process completed before PM terminal closure approval"),
    _invariant("completion_after_all_node_reviews", "process completed before every route node was reviewed and completed"),
)


def build_workflow() -> Workflow:
    return Workflow((ProcessLivenessStep(),), name="flowpilot_process_liveness")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"controlled_blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


def _running(**changes: object) -> State:
    return replace(State(status="running", settlement_started=True, evidence_fresh=True), **changes)


def hazard_states() -> dict[str, State]:
    return {
        "next_action_before_settlement": _running(
            settlement_started=False,
            next_action_exposed=True,
            next_action_count=1,
        ),
        "next_action_before_durable_evidence_settled": _running(
            durable_evidence_pending=True,
            next_action_exposed=True,
            next_action_count=1,
        ),
        "multiple_next_actions_one_tick": _running(
            next_action_exposed=True,
            next_action_count=2,
        ),
        "stale_pending_action_used_for_next_action": _running(
            stale_pending_action=True,
            next_action_exposed=True,
            next_action_count=1,
        ),
        "stale_blocker_survives_next_action": _running(
            stale_blocker_present=True,
            next_action_exposed=True,
            next_action_count=1,
        ),
        "stale_pm_repair_row_not_superseded": _running(
            stale_pm_repair_row_present=True,
            stale_pm_repair_row_superseded=False,
            next_action_exposed=True,
            next_action_count=1,
        ),
        "wait_target_without_allowed_event": _running(
            wait_target="worker_result",
            allowed_event="none",
        ),
        "allowed_event_without_wait_target": _running(
            wait_target="none",
            allowed_event=WAIT_EVENTS["worker_result"],
        ),
        "wrong_event_reconciled": _running(
            wait_target="worker_result",
            allowed_event=WAIT_EVENTS["worker_result"],
            event_received=WAIT_EVENTS["reviewer_result"],
            event_reconciled=True,
        ),
        "wrong_event_accepted": _running(wrong_event_accepted=True),
        "later_node_without_prior_review": _running(
            current_node_index=1,
            node_review_pass_mask=0,
            node_completion_ledger_mask=0,
        ),
        "completion_ledger_includes_unreviewed_node": _running(
            node_review_pass_mask=0,
            node_completion_ledger_mask=1,
        ),
        "current_node_completed_without_review_mask": _running(
            node_completed=True,
            reviewer_decision="pass",
            node_review_pass_mask=0,
        ),
        "packet_registered_on_stale_frontier": _running(
            route_activated=True,
            frontier_fresh=False,
            node_packet_registered=True,
        ),
        "worker_result_routed_without_ledger": _running(
            worker_result_returned=True,
            worker_result_routed_to_pm=True,
        ),
        "reviewer_gate_before_pm_disposition": _running(
            worker_result_ledger_checked=True,
            worker_result_routed_to_pm=True,
            reviewer_gate_released=True,
        ),
        "reviewer_decision_without_gate": _running(
            reviewer_decision="pass",
        ),
        "active_blocker_without_kind": _running(
            control_blocker_active=True,
            blocker_kind="none",
            blocker_lane="control_plane_reissue",
        ),
        "active_blocker_without_lane": _running(
            control_blocker_active=True,
            blocker_kind="small_fix",
            blocker_lane="none",
        ),
        "small_fix_pm_before_retry_budget": _running(
            control_blocker_active=True,
            blocker_kind="small_fix",
            blocker_lane="pm_repair",
            retry_attempts=0,
            retry_budget_exhausted=False,
            pm_repair_requested=True,
        ),
        "small_fix_misrouted_to_route_mutation": _running(
            control_blocker_active=True,
            blocker_kind="small_fix",
            blocker_lane="route_mutation",
        ),
        "route_scope_misrouted_to_local_reissue": _running(
            control_blocker_active=True,
            blocker_kind="route_scope",
            blocker_lane="control_plane_reissue",
        ),
        "fatal_protocol_misrouted_to_repair": _running(
            control_blocker_active=True,
            blocker_kind="fatal_protocol",
            blocker_lane="pm_repair",
            pm_repair_requested=True,
        ),
        "pm_repair_before_retry_budget_exhausted": _running(
            control_blocker_active=True,
            blocker_kind="small_fix",
            blocker_lane="pm_repair",
            retry_attempts=0,
            retry_budget_exhausted=False,
            pm_repair_requested=True,
        ),
        "retry_attempts_exceed_budget": _running(
            control_blocker_active=True,
            blocker_lane="control_plane_reissue",
            retry_attempts=3,
            retry_budget=2,
        ),
        "exhausted_blocker_not_escalated": _running(
            control_blocker_active=True,
            blocker_lane="control_plane_reissue",
            retry_attempts=2,
            retry_budget=2,
            retry_budget_exhausted=True,
            pm_repair_requested=False,
            next_action_exposed=True,
            next_action_count=1,
        ),
        "pm_repair_loop_unbounded": _running(
            blocker_lane="pm_repair",
            retry_budget_exhausted=True,
            pm_repair_requested=True,
            pm_repair_decision="same_gate_repair",
            pm_repair_cycles=2,
        ),
        "pm_repair_request_without_decision": _running(
            blocker_lane="pm_repair",
            retry_budget_exhausted=True,
            pm_repair_requested=True,
            pm_repair_decision="none",
        ),
        "same_gate_repair_without_return_gate": _running(
            blocker_lane="pm_repair",
            retry_budget_exhausted=True,
            pm_repair_requested=True,
            pm_repair_decision="same_gate_repair",
            repair_return_gate="none",
        ),
        "reviewer_recheck_before_repair_ledger": _running(
            repair_result_returned=True,
            reviewer_recheck_passed=True,
        ),
        "route_mutation_without_stale_evidence": _running(
            route_mutation_recorded=True,
            frontier_marked_stale=True,
        ),
        "route_mutation_without_stale_frontier": _running(
            route_mutation_recorded=True,
            old_evidence_marked_stale=True,
        ),
        "route_mutation_loop_unbounded": _running(
            route_mutation_recorded=True,
            old_evidence_marked_stale=True,
            frontier_marked_stale=True,
            route_version=3,
        ),
        "final_scan_before_mutation_replay": _running(
            route_mutation_recorded=True,
            old_evidence_marked_stale=True,
            frontier_marked_stale=True,
            frontier_rewritten_after_mutation=True,
            same_scope_replay_rerun=False,
            current_route_scan_done=True,
        ),
        "node_completed_before_reviewer_pass": _running(
            node_completed=True,
            reviewer_decision="none",
        ),
        "parent_segment_before_backward_replay": _running(
            node_completed=True,
            node_completion_ledger_updated=True,
            pm_parent_segment_decision_recorded=True,
        ),
        "current_route_scan_before_all_nodes_reviewed": _running(
            current_route_scan_done=True,
            node_review_pass_mask=1,
            node_completion_ledger_mask=1,
        ),
        "final_ledger_before_route_scan": _running(
            final_ledger_built=True,
            node_review_pass_mask=ROUTE_NODE_MASK,
            node_completion_ledger_mask=ROUTE_NODE_MASK,
            reviewer_evidence_quality_passed=True,
            final_ledger_source_of_truth_generated=True,
        ),
        "final_ledger_before_all_nodes_reviewed": _running(
            current_route_scan_done=True,
            final_ledger_built=True,
            node_review_pass_mask=1,
            node_completion_ledger_mask=1,
            reviewer_evidence_quality_passed=True,
            final_ledger_source_of_truth_generated=True,
        ),
        "final_ledger_with_unresolved_items": _running(
            current_route_scan_done=True,
            node_review_pass_mask=ROUTE_NODE_MASK,
            node_completion_ledger_mask=ROUTE_NODE_MASK,
            reviewer_evidence_quality_passed=True,
            final_ledger_source_of_truth_generated=True,
            final_ledger_built=True,
            unresolved_items_present=True,
        ),
        "final_ledger_with_pending_generated_resources": _running(
            current_route_scan_done=True,
            node_review_pass_mask=ROUTE_NODE_MASK,
            node_completion_ledger_mask=ROUTE_NODE_MASK,
            reviewer_evidence_quality_passed=True,
            final_ledger_source_of_truth_generated=True,
            final_ledger_built=True,
            generated_resources_pending=True,
        ),
        "terminal_replay_map_before_clean_ledger": _running(
            terminal_replay_map_built=True,
            final_ledger_clean=False,
        ),
        "completion_before_final_backward_replay": _running(
            task_completion_projection_published=True,
            final_backward_replay_passed=False,
        ),
        "pm_closure_before_completion_projection": _running(
            pm_terminal_closure_approved=True,
            task_completion_projection_published=False,
        ),
        "complete_before_pm_closure": _running(
            status="complete",
            pm_terminal_closure_approved=False,
        ),
        "complete_before_all_nodes_reviewed": _running(
            status="complete",
            pm_terminal_closure_approved=True,
            node_review_pass_mask=1,
            node_completion_ledger_mask=1,
        ),
        "controller_reads_sealed_body": _running(controller_read_sealed_body=True),
        "controller_originates_project_evidence": _running(controller_originated_project_evidence=True),
        "controller_advances_route": _running(controller_advanced_route=True),
    }


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 90


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "Action",
    "ROUTE_NODE_COUNT",
    "ROUTE_NODE_MASK",
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
]
