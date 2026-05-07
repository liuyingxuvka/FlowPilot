"""FlowGuard model for FlowPilot control-plane friction fixes.

Risk intent brief:
- Prevent prompt-isolation shortcuts from becoming handoff dead ends.
- Preserve Controller's envelope-only boundary while reducing purely
  mechanical handoff steps.
- Model-critical durable state: research package fields, worker packet
  materialization, packet/result open receipts, control-blocker routing,
  stop lifecycle reconciliation, active-task authority, and display snapshot
  freshness.
- Adversarial branches include dropped research scope fields, reviewer reports
  accepted without a result-body receipt, missing-receipt blockers escalated to
  PM instead of same-role reissue, stopped runs with live heartbeat/crew/packet
  state, stale snapshots treated as active UI state, ambiguous multi-active
  runs under current-json-only authority, and optimized transactions that skip
  hash, role, or Controller-boundary checks.
- Hard invariants: package-to-packet fields are preserved; reviewer decisions
  require legal open receipts; missing receipt repair is same-role reissue;
  stopped runs reconcile all visible lifecycle authorities; active snapshots
  are fresh; multi-active visibility has explicit authority; optimized
  transactions keep hash, role, and envelope-only guarantees.
- Blindspot: this is a focused abstract model. It is paired with runtime tests
  for concrete JSON writers and router behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class Tick:
    """One control-plane handoff tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | complete
    mode: str = "unknown"  # unknown | expanded | optimized
    holder: str = "controller"
    handoff_steps: int = 0

    controller_boundary_confirmed: bool = False
    controller_read_sealed_body: bool = False
    role_identity_checked: bool = False
    hash_verified: bool = False

    pm_research_package_written: bool = False
    research_package_has_decision_question: bool = False
    research_package_has_allowed_sources: bool = False
    research_package_has_stop_conditions: bool = False
    research_capability_decision_recorded: bool = False
    worker_packet_written: bool = False
    worker_packet_preserves_research_fields: bool = False

    packet_delivered: bool = False
    packet_body_open_receipt: bool = False
    result_returned: bool = False
    result_routed_to_reviewer: bool = False
    result_body_open_receipt: bool = False
    reviewer_report_written: bool = False
    reviewer_report_accepted: bool = False

    optimized_relay_transaction: bool = False
    optimized_transaction_records_delivery: bool = False
    optimized_transaction_records_open_receipts: bool = False
    optimized_transaction_records_result_return: bool = False

    receipt_missing_blocker: bool = False
    control_blocker_lane: str = "none"  # none | control_plane_reissue | pm_repair_decision_required
    control_blocker_target_role: str = "none"  # none | human_like_reviewer | project_manager

    stop_requested: bool = False
    current_status_stopped: bool = False
    continuation_heartbeat_active: bool = False
    crew_live_agents_active: bool = False
    packet_loop_active: bool = False
    frontier_terminal: bool = False

    snapshot_published_as_active: bool = False
    snapshot_fresh_against_frontier_and_ledger: bool = False
    multiple_running_index_entries_visible: bool = False
    active_task_authority: str = "current_json_only"  # current_json_only | explicit_active_set


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


class ControlPlaneStep:
    """Model one FlowPilot control-plane handoff transition.

    Input x State -> Set(Output x State)
    reads: package scope, packet receipts, blocker lane, lifecycle authorities,
    snapshot freshness, and optimized transaction markers
    writes: one durable control-plane fact or terminal status
    idempotency: each fact is monotonic; repeated ticks do not duplicate
    receipts or reopen sealed bodies
    """

    name = "ControlPlaneStep"
    input_description = "control-plane handoff tick"
    output_description = "one FlowPilot friction-control transition"
    reads = (
        "controller_boundary",
        "research_package",
        "packet_receipts",
        "control_blocker_lane",
        "lifecycle_authorities",
        "active_snapshot",
    )
    writes = (
        "package_materialization",
        "packet_transaction_receipt",
        "blocker_route",
        "lifecycle_reconciliation",
        "snapshot_refresh",
        "terminal_status",
    )
    idempotency = "monotonic state facts; optimized transaction records one composite receipt"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def _inc(state: State, **changes: object) -> State:
    return replace(state, handoff_steps=state.handoff_steps + 1, **changes)


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "complete":
        return

    if not state.controller_boundary_confirmed:
        yield Transition(
            "controller_boundary_confirmed_envelope_only",
            _inc(state, status="running", controller_boundary_confirmed=True),
        )
        return

    if state.mode == "unknown":
        yield Transition("select_expanded_safe_flow", _inc(state, mode="expanded"))
        yield Transition("select_optimized_transaction_flow", _inc(state, mode="optimized"))
        return

    if not state.pm_research_package_written:
        yield Transition(
            "pm_writes_research_package_with_scope_fields",
            _inc(
                state,
                holder="pm",
                pm_research_package_written=True,
                research_package_has_decision_question=True,
                research_package_has_allowed_sources=True,
                research_package_has_stop_conditions=True,
            ),
        )
        return

    if not state.research_capability_decision_recorded:
        yield Transition(
            "pm_records_research_capability_decision_preserving_package_scope",
            _inc(state, holder="pm", research_capability_decision_recorded=True),
        )
        return

    if not state.worker_packet_written:
        yield Transition(
            "worker_packet_materialized_with_research_scope",
            _inc(
                state,
                holder="controller",
                worker_packet_written=True,
                worker_packet_preserves_research_fields=True,
            ),
        )
        return

    if state.mode == "optimized":
        if not state.optimized_relay_transaction:
            yield Transition(
                "optimized_relay_transaction_records_delivery_open_and_hash",
                _inc(
                    state,
                    holder="reviewer",
                    packet_delivered=True,
                    packet_body_open_receipt=True,
                    result_returned=True,
                    result_routed_to_reviewer=True,
                    result_body_open_receipt=True,
                    optimized_relay_transaction=True,
                    optimized_transaction_records_delivery=True,
                    optimized_transaction_records_open_receipts=True,
                    optimized_transaction_records_result_return=True,
                    role_identity_checked=True,
                    hash_verified=True,
                ),
            )
            return
    else:
        if not state.packet_delivered:
            yield Transition("packet_delivered_by_controller", _inc(state, holder="worker", packet_delivered=True))
            return
        if not state.packet_body_open_receipt:
            yield Transition(
                "target_records_packet_body_open_receipt",
                _inc(state, holder="worker", packet_body_open_receipt=True, role_identity_checked=True, hash_verified=True),
            )
            return
        if not state.result_returned:
            yield Transition("worker_result_returned_to_ledger", _inc(state, holder="controller", result_returned=True))
            return
        if not state.result_routed_to_reviewer:
            yield Transition(
                "controller_routes_result_to_reviewer_after_ledger_check",
                _inc(state, holder="reviewer", result_routed_to_reviewer=True),
            )
            return
        if not state.result_body_open_receipt:
            yield Transition(
                "reviewer_records_result_body_open_receipt",
                _inc(state, holder="reviewer", result_body_open_receipt=True),
            )
            return

    if not state.reviewer_report_written:
        yield Transition(
            "reviewer_writes_report_after_receipts",
            _inc(state, holder="reviewer", reviewer_report_written=True),
        )
        return

    if not state.reviewer_report_accepted:
        yield Transition(
            "router_accepts_reviewer_report",
            _inc(state, holder="controller", reviewer_report_accepted=True),
        )
        return

    if not state.stop_requested:
        yield Transition("user_stop_requested", _inc(state, holder="controller", stop_requested=True))
        return

    if not state.current_status_stopped:
        yield Transition(
            "run_lifecycle_reconciled_all_authorities",
            _inc(
                state,
                current_status_stopped=True,
                continuation_heartbeat_active=False,
                crew_live_agents_active=False,
                packet_loop_active=False,
                frontier_terminal=True,
            ),
        )
        return

    if not state.snapshot_published_as_active:
        yield Transition(
            "route_state_snapshot_refreshed_after_lifecycle_change",
            _inc(
                state,
                snapshot_published_as_active=True,
                snapshot_fresh_against_frontier_and_ledger=True,
            ),
        )
        return

    yield Transition("control_plane_flow_complete", replace(state, status="complete"))


def research_scope_preserved(state: State, trace) -> InvariantResult:
    del trace
    if state.worker_packet_written and not (
        state.research_package_has_decision_question
        and state.research_package_has_allowed_sources
        and state.research_package_has_stop_conditions
        and state.worker_packet_preserves_research_fields
    ):
        return InvariantResult.fail(
            "worker research packet was materialized after PM package scope fields were dropped"
        )
    return InvariantResult.pass_()


def reviewer_report_requires_open_receipts(state: State, trace) -> InvariantResult:
    del trace
    if state.reviewer_report_accepted and not (
        state.packet_delivered
        and state.packet_body_open_receipt
        and state.result_returned
        and state.result_routed_to_reviewer
        and state.result_body_open_receipt
    ):
        return InvariantResult.fail(
            "reviewer report was accepted before delivery, packet-open, result-return, relay, and result-open receipts existed"
        )
    return InvariantResult.pass_()


def missing_receipt_uses_same_role_reissue(state: State, trace) -> InvariantResult:
    del trace
    if state.receipt_missing_blocker and not (
        state.control_blocker_lane == "control_plane_reissue"
        and state.control_blocker_target_role == "human_like_reviewer"
    ):
        return InvariantResult.fail(
            "missing receipt blocker was not routed as same-role reviewer control-plane reissue"
        )
    return InvariantResult.pass_()


def stopped_run_reconciles_authorities(state: State, trace) -> InvariantResult:
    del trace
    if state.current_status_stopped and (
        state.continuation_heartbeat_active
        or state.crew_live_agents_active
        or state.packet_loop_active
        or not state.frontier_terminal
    ):
        return InvariantResult.fail(
            "stopped run left heartbeat, crew, packet loop, or frontier authority active"
        )
    return InvariantResult.pass_()


def active_snapshot_is_fresh(state: State, trace) -> InvariantResult:
    del trace
    if state.snapshot_published_as_active and not state.snapshot_fresh_against_frontier_and_ledger:
        return InvariantResult.fail("active route_state_snapshot is stale against frontier or packet ledger")
    return InvariantResult.pass_()


def multi_active_requires_explicit_authority(state: State, trace) -> InvariantResult:
    del trace
    if state.multiple_running_index_entries_visible and state.active_task_authority == "current_json_only":
        return InvariantResult.fail("multiple active UI tasks were exposed under current_json_only authority")
    return InvariantResult.pass_()


def controller_boundary_survives_optimization(state: State, trace) -> InvariantResult:
    del trace
    if state.controller_read_sealed_body:
        return InvariantResult.fail("Controller read sealed packet/result body")
    if state.optimized_relay_transaction and not (
        state.optimized_transaction_records_delivery
        and state.optimized_transaction_records_open_receipts
        and state.optimized_transaction_records_result_return
        and state.role_identity_checked
        and state.hash_verified
    ):
        return InvariantResult.fail(
            "optimized relay transaction skipped delivery, receipt, result-return, role, or hash evidence"
        )
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="research_scope_preserved",
        description="Research package scope fields survive capability decision and worker packet materialization.",
        predicate=research_scope_preserved,
    ),
    Invariant(
        name="reviewer_report_requires_open_receipts",
        description="Reviewer report acceptance requires legal packet/result receipts.",
        predicate=reviewer_report_requires_open_receipts,
    ),
    Invariant(
        name="missing_receipt_uses_same_role_reissue",
        description="Mechanical missing-receipt blockers route to same-role reissue, not PM repair.",
        predicate=missing_receipt_uses_same_role_reissue,
    ),
    Invariant(
        name="stopped_run_reconciles_authorities",
        description="A user-stopped run turns off heartbeat, crew, packet loop, and frontier authorities.",
        predicate=stopped_run_reconciles_authorities,
    ),
    Invariant(
        name="active_snapshot_is_fresh",
        description="User-visible active snapshots are fresh against frontier and packet ledger.",
        predicate=active_snapshot_is_fresh,
    ),
    Invariant(
        name="multi_active_requires_explicit_authority",
        description="Multiple active UI tasks require explicit active-set authority.",
        predicate=multi_active_requires_explicit_authority,
    ),
    Invariant(
        name="controller_boundary_survives_optimization",
        description="Handoff optimization cannot weaken Controller's envelope-only, role, or hash guarantees.",
        predicate=controller_boundary_survives_optimization,
    ),
)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(str(result.message))
    return failures


def _safe_base(**changes: object) -> State:
    return replace(
        State(
            status="running",
            controller_boundary_confirmed=True,
            mode="expanded",
            pm_research_package_written=True,
            research_package_has_decision_question=True,
            research_package_has_allowed_sources=True,
            research_package_has_stop_conditions=True,
            research_capability_decision_recorded=True,
            worker_packet_written=True,
            worker_packet_preserves_research_fields=True,
            packet_delivered=True,
            packet_body_open_receipt=True,
            result_returned=True,
            result_routed_to_reviewer=True,
            result_body_open_receipt=True,
            reviewer_report_written=True,
            reviewer_report_accepted=True,
            role_identity_checked=True,
            hash_verified=True,
        ),
        **changes,
    )


def hazard_states() -> dict[str, State]:
    return {
        "research_package_scope_dropped": _safe_base(worker_packet_preserves_research_fields=False),
        "reviewer_report_without_result_open_receipt": _safe_base(result_body_open_receipt=False),
        "missing_receipt_blocker_escalated_to_pm": _safe_base(
            receipt_missing_blocker=True,
            control_blocker_lane="pm_repair_decision_required",
            control_blocker_target_role="project_manager",
        ),
        "stopped_run_with_active_heartbeat": _safe_base(
            current_status_stopped=True,
            continuation_heartbeat_active=True,
            frontier_terminal=True,
        ),
        "stopped_run_with_active_packet_loop": _safe_base(
            current_status_stopped=True,
            packet_loop_active=True,
            frontier_terminal=True,
        ),
        "stopped_run_without_terminal_frontier": _safe_base(
            current_status_stopped=True,
            frontier_terminal=False,
        ),
        "stale_snapshot_published_as_active": _safe_base(
            snapshot_published_as_active=True,
            snapshot_fresh_against_frontier_and_ledger=False,
        ),
        "multiple_active_tasks_under_current_json_only": _safe_base(
            multiple_running_index_entries_visible=True,
            active_task_authority="current_json_only",
        ),
        "optimized_transaction_without_hash_check": _safe_base(
            mode="optimized",
            optimized_relay_transaction=True,
            optimized_transaction_records_delivery=True,
            optimized_transaction_records_open_receipts=True,
            optimized_transaction_records_result_return=True,
            hash_verified=False,
        ),
        "controller_reads_sealed_body": _safe_base(controller_read_sealed_body=True),
    }


def build_workflow() -> Workflow:
    return Workflow((ControlPlaneStep(),), name="flowpilot_control_plane_friction")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status == "complete"


def is_success(state: State) -> bool:
    return state.status == "complete"


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 32


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
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
]
