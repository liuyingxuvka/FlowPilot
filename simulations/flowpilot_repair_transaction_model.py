"""FlowGuard model for the single current FlowPilot repair transaction path.

Risk intent brief:
- Keep PM repair prose separate from Router execution authority.
- Require every committed repair to name one supported plan kind and the
  concrete current producer, queued action, Router handler, or terminal stop
  that makes it executable.
- Keep the PM decision flag, transaction commit, outcome table, and exposed
  follow-up wait on one ordered current-state path.
- Require independent FlowGuard recheck when the blocker is modelable and
  independent Reviewer recheck before success can resume the main flow.
- Treat retired replacement-packet repair authority as a known-bad input, not
  as a second successful route.

This remains the existing repair-transaction model owner. It intentionally
contracts the retired material-generation branch instead of adding a parallel
model or compatibility path. It is a blocker-backed transaction-mechanics
child of the unified repair engine: it carries a typed blocker trigger into
that engine, but it cannot claim direct PM historical-defect intake or shared
repair-engine ownership.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_MISS_REVIEW_BLOCK_LANES = {
    "node_acceptance_plan": "route_mutation",
    "current_node_dispatch": "route_mutation",
    "node_result": "route_mutation",
}

NODE_KINDS = {"leaf", "parent", "module", "repair"}
PARENT_NODE_KINDS = {"parent", "module"}
CONTROL_REPAIR_ORIGINS = {
    "none",
    "node_acceptance_plan",
    "current_node_dispatch",
    "current_node_result",
    "parent_backward_replay",
}

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

EXECUTABLE_REPAIR_PLAN_KINDS = {
    "operation_replay",
    "controller_repair_work_packet",
    "role_reissue",
    "router_internal_reconcile",
    "await_existing_event",
    "route_mutation",
    "terminal_stop",
}
RETIRED_REPAIR_PLAN_KINDS = {"packet_reissue"}

EVENT_NODE_KIND_COMPATIBILITY = {
    event: {"leaf", "repair"} for event in LEAF_CURRENT_NODE_EVENTS
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
    """One repair-control transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | blocked | complete
    holder: str = "controller"
    active_node_kind: str = "leaf"
    control_repair_origin: str = "none"
    repair_trigger_origin: str = "none"  # none | reviewer_or_system_failure | pm_historical_defect
    shared_repair_engine_handoff_recorded: bool = False
    shared_repair_engine_handoff_id_present: bool = False
    owns_shared_repair_engine: bool = False
    pm_proactive_historical_intake_claimed: bool = False
    rerun_target_event: str = "reviewer_current_node_result_decision"
    steps: int = 0

    blocker_detected: bool = False
    blocker_kind: str = "none"
    blocker_pm_repair_lane: str = "none"
    blocker_registered_in_router: bool = False
    blocker_has_origin_event: bool = False
    blocker_has_allowed_nonterminal_events: bool = False
    pm_model_miss_cards_accept_blocker_kind: bool = False
    pm_model_miss_triage_accepts_blocker_kind: bool = False
    pm_review_repair_event_accepts_blocker_kind: bool = False
    pm_review_repair_event_routes_blocker_kind: bool = False

    model_miss_triage_recorded: bool = False
    flowguard_bug_class_modelable: bool = True
    flowguard_out_of_scope_reason_recorded: bool = False
    model_miss_flowguard_operator_request_issued: bool = False
    model_miss_flowguard_operator_report_returned: bool = False
    same_class_findings_recorded: bool = False
    repair_candidates_compared: bool = False
    minimal_sufficient_repair_recommended: bool = False
    pm_selected_repair_after_model_miss: bool = False

    pm_repair_decision_recorded: bool = False
    pm_repair_decision_flag_visible: bool = False
    pm_decision_resolves_blocker: bool = False
    repair_transaction_opened: bool = False
    transaction_id_recorded: bool = False
    transaction_plan_kind: str = "none"
    repair_plan_validation_passed: bool = False

    replay_operation_recorded: bool = False
    replay_operation_safe: bool = False
    concrete_repair_action_queued: bool = False
    current_followup_producer_bound: bool = False
    existing_event_producer_found: bool = False
    controller_repair_packet_bounded: bool = False
    router_internal_handler_found: bool = False
    terminal_stop_recorded: bool = False

    outcome_table_staged: bool = False
    transaction_committed_atomically: bool = False
    post_decision_wait_events_exposed: bool = False
    success_outcome_routable: bool = False
    blocker_outcome_routable: bool = False
    protocol_outcome_routable: bool = False
    success_outcome_event: str = "none"
    blocker_outcome_event: str = "none"
    protocol_outcome_event: str = "none"

    post_repair_model_check_passed: bool = False
    reviewer_recheck_requested: bool = False
    reviewer_can_emit_success: bool = False
    reviewer_can_emit_blocker: bool = False
    reviewer_can_emit_protocol_blocker: bool = False
    reviewer_outcome: str = "none"
    router_accepted_reviewer_outcome: bool = False

    original_blocker_resolved: bool = False
    followup_blocker_registered: bool = False
    repair_transaction_index_refreshed: bool = False
    frontier_refreshed: bool = False
    display_refreshed: bool = False
    main_flow_resumed_after_success: bool = False
    no_legal_next_action: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _inc(state: State, **changes: object) -> State:
    return replace(state, steps=state.steps + 1, status="running", **changes)


def _event_allowed_for_node_kind(event: str, node_kind: str) -> bool:
    return node_kind in EVENT_NODE_KIND_COMPATIBILITY.get(event, set())


def _outcome_events(state: State) -> tuple[str, ...]:
    return (
        state.success_outcome_event,
        state.blocker_outcome_event,
        state.protocol_outcome_event,
    )


def _plan_has_execution_evidence(state: State) -> bool:
    kind = state.transaction_plan_kind
    if kind == "operation_replay":
        return (
            state.replay_operation_recorded
            and state.replay_operation_safe
            and state.concrete_repair_action_queued
        )
    if kind == "controller_repair_work_packet":
        return (
            state.controller_repair_packet_bounded
            and state.concrete_repair_action_queued
        )
    if kind in {"role_reissue", "route_mutation"}:
        return state.current_followup_producer_bound
    if kind == "router_internal_reconcile":
        return state.router_internal_handler_found
    if kind == "await_existing_event":
        return state.existing_event_producer_found
    if kind == "terminal_stop":
        return state.terminal_stop_recorded
    return False


class RepairTransactionStep:
    """Evaluate one current-contract repair transaction step.

    Input x State -> Set(Output x State)
    reads: current blocker, PM decision, executable plan evidence, current
    outcome table, independent model/reviewer results, and current authorities
    writes: one ordered transaction fact or a terminal blocker/resolution state
    idempotency: facts are monotonic within one current transaction identity
    """

    name = "RepairTransactionStep"
    input_description = "one repair-control tick"
    output_description = "one current-contract repair transition"
    reads = (
        "router_blocker_state",
        "pm_repair_decision",
        "repair_transaction_plan",
        "current_producer_or_action",
        "router_outcome_table",
        "independent_recheck_result",
    )
    writes = (
        "repair_transaction",
        "router_resolution",
        "followup_blocker",
        "current_authority_refresh",
    )
    idempotency = "monotonic current transaction facts"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"blocked", "complete"}:
        return

    if not state.blocker_detected:
        for blocker_kind, lane, origin in (
            ("node_acceptance_plan", "route_mutation", "node_acceptance_plan"),
            ("current_node_dispatch", "route_mutation", "current_node_dispatch"),
            ("node_result", "route_mutation", "current_node_result"),
        ):
            yield Transition(
                f"reviewer_blocker_detected_{blocker_kind}",
                _inc(
                    state,
                    blocker_detected=True,
                    blocker_kind=blocker_kind,
                    blocker_pm_repair_lane=lane,
                    control_repair_origin=origin,
                    repair_trigger_origin="reviewer_or_system_failure",
                    pm_model_miss_cards_accept_blocker_kind=True,
                    pm_model_miss_triage_accepts_blocker_kind=True,
                    pm_review_repair_event_accepts_blocker_kind=True,
                    pm_review_repair_event_routes_blocker_kind=True,
                ),
            )
        return

    if not state.blocker_registered_in_router:
        yield Transition(
            "router_registers_blocker_with_origin_and_failure_events",
            _inc(
                state,
                holder="controller",
                blocker_registered_in_router=True,
                blocker_has_origin_event=True,
                blocker_has_allowed_nonterminal_events=True,
            ),
        )
        return

    if not state.shared_repair_engine_handoff_recorded:
        yield Transition(
            "router_hands_blocker_trigger_to_unified_repair_engine",
            _inc(
                state,
                holder="controller",
                shared_repair_engine_handoff_recorded=True,
                shared_repair_engine_handoff_id_present=True,
            ),
        )
        return

    if not state.model_miss_triage_recorded:
        yield Transition(
            "pm_records_model_miss_triage_for_modelable_blocker",
            _inc(state, holder="project_manager", model_miss_triage_recorded=True),
        )
        return

    if (
        state.flowguard_bug_class_modelable
        and not state.model_miss_flowguard_operator_request_issued
    ):
        yield Transition(
            "pm_requests_flowguard_operator_same_class_model",
            _inc(
                state,
                holder="project_manager",
                model_miss_flowguard_operator_request_issued=True,
            ),
        )
        return

    if (
        state.flowguard_bug_class_modelable
        and not state.model_miss_flowguard_operator_report_returned
    ):
        yield Transition(
            "flowguard_operator_reports_same_class_findings",
            _inc(
                state,
                holder="flowguard_operator",
                model_miss_flowguard_operator_report_returned=True,
                same_class_findings_recorded=True,
            ),
        )
        return

    if not state.repair_candidates_compared:
        yield Transition(
            "flowguard_operator_compares_minimal_repair_candidates",
            _inc(
                state,
                holder="flowguard_operator",
                repair_candidates_compared=True,
                minimal_sufficient_repair_recommended=True,
            ),
        )
        return

    if not state.pm_selected_repair_after_model_miss:
        yield Transition(
            "pm_selects_repair_after_model_miss_review",
            _inc(
                state,
                holder="project_manager",
                pm_selected_repair_after_model_miss=True,
            ),
        )
        return

    if not state.pm_repair_decision_recorded:
        yield Transition(
            "pm_records_repair_decision_without_self_resolution",
            _inc(
                state,
                holder="project_manager",
                pm_repair_decision_recorded=True,
                pm_repair_decision_flag_visible=True,
                pm_decision_resolves_blocker=False,
            ),
        )
        return

    if not state.repair_transaction_opened:
        yield Transition(
            "router_opens_current_contract_repair_transaction",
            _inc(
                state,
                holder="controller",
                repair_transaction_opened=True,
                transaction_id_recorded=True,
                transaction_plan_kind="operation_replay",
            ),
        )
        return

    if not state.repair_plan_validation_passed:
        yield Transition(
            "router_validates_and_queues_safe_operation_replay",
            _inc(
                state,
                holder="controller",
                repair_plan_validation_passed=True,
                replay_operation_recorded=True,
                replay_operation_safe=True,
                concrete_repair_action_queued=True,
            ),
        )
        return

    if not state.transaction_committed_atomically:
        yield Transition(
            "router_atomically_commits_current_repair_and_outcome_table",
            _inc(
                state,
                holder="controller",
                outcome_table_staged=True,
                transaction_committed_atomically=True,
                post_decision_wait_events_exposed=True,
                success_outcome_routable=True,
                blocker_outcome_routable=True,
                protocol_outcome_routable=True,
                success_outcome_event="reviewer_current_node_result_decision",
                blocker_outcome_event="pm_records_current_node_repair_blocker",
                protocol_outcome_event="pm_records_current_node_protocol_blocker",
            ),
        )
        return

    if state.flowguard_bug_class_modelable and not state.post_repair_model_check_passed:
        yield Transition(
            "flowguard_operator_checks_current_repair_effect",
            _inc(
                state,
                holder="flowguard_operator",
                post_repair_model_check_passed=True,
            ),
        )
        return

    if not state.reviewer_recheck_requested:
        yield Transition(
            "reviewer_recheck_requested_after_current_commit",
            _inc(
                state,
                holder="human_like_reviewer",
                reviewer_recheck_requested=True,
                reviewer_can_emit_success=True,
                reviewer_can_emit_blocker=True,
                reviewer_can_emit_protocol_blocker=True,
            ),
        )
        return

    if state.reviewer_outcome == "none":
        yield Transition(
            "reviewer_recheck_allows_dispatch",
            _inc(
                state,
                holder="human_like_reviewer",
                reviewer_outcome="success",
                router_accepted_reviewer_outcome=True,
            ),
        )
        yield Transition(
            "reviewer_recheck_returns_followup_blocker",
            _inc(
                state,
                holder="human_like_reviewer",
                reviewer_outcome="blocker",
                router_accepted_reviewer_outcome=True,
            ),
        )
        yield Transition(
            "reviewer_recheck_returns_protocol_blocker",
            _inc(
                state,
                holder="human_like_reviewer",
                reviewer_outcome="protocol_blocker",
                router_accepted_reviewer_outcome=True,
            ),
        )
        return

    if not state.repair_transaction_index_refreshed:
        success = state.reviewer_outcome == "success"
        yield Transition(
            "router_refreshes_current_authorities_after_repair_outcome",
            replace(
                _inc(
                    state,
                    holder="controller",
                    original_blocker_resolved=success,
                    followup_blocker_registered=not success,
                    repair_transaction_index_refreshed=True,
                    frontier_refreshed=True,
                    display_refreshed=True,
                    main_flow_resumed_after_success=success,
                ),
                status="complete" if success else "blocked",
            ),
        )


def blocker_registration_is_routable(state: State, trace) -> InvariantResult:
    del trace
    if state.blocker_registered_in_router and not (
        state.blocker_detected
        and state.blocker_has_origin_event
        and state.blocker_has_allowed_nonterminal_events
    ):
        return InvariantResult.fail(
            "router blocker registration lacks origin or nonterminal repair events"
        )
    return InvariantResult.pass_()


def blocker_transaction_delegates_to_unified_engine(
    state: State, trace
) -> InvariantResult:
    del trace
    if (
        state.pm_proactive_historical_intake_claimed
        or state.repair_trigger_origin == "pm_historical_defect"
    ):
        return InvariantResult.fail(
            "blocker repair transaction child cannot own PM-proactive historical repair intake"
        )
    if state.owns_shared_repair_engine:
        return InvariantResult.fail(
            "blocker repair transaction child claimed shared repair-engine ownership"
        )
    if (
        state.blocker_registered_in_router
        and (
            state.model_miss_triage_recorded
            or state.pm_repair_decision_recorded
            or state.repair_transaction_opened
        )
        and not (
            state.repair_trigger_origin == "reviewer_or_system_failure"
            and state.shared_repair_engine_handoff_recorded
            and state.shared_repair_engine_handoff_id_present
        )
    ):
        return InvariantResult.fail(
            "blocker repair transaction did not hand its typed trigger to the unified repair engine"
        )
    return InvariantResult.pass_()


def model_miss_block_kind_has_end_to_end_repair_lane(
    state: State, trace
) -> InvariantResult:
    del trace
    if not state.blocker_detected:
        return InvariantResult.pass_()
    expected_lane = MODEL_MISS_REVIEW_BLOCK_LANES.get(state.blocker_kind)
    if (
        expected_lane is None
        or state.blocker_pm_repair_lane != expected_lane
        or not state.pm_model_miss_cards_accept_blocker_kind
        or not state.pm_model_miss_triage_accepts_blocker_kind
        or not state.pm_review_repair_event_accepts_blocker_kind
        or not state.pm_review_repair_event_routes_blocker_kind
    ):
        return InvariantResult.fail(
            f"reviewer block kind {state.blocker_kind} is not accepted end-to-end by PM model-miss repair"
        )
    return InvariantResult.pass_()


def pm_decision_cannot_resolve_blocker(state: State, trace) -> InvariantResult:
    del trace
    if state.pm_decision_resolves_blocker:
        return InvariantResult.fail("PM repair decision resolved the blocker by itself")
    return InvariantResult.pass_()


def pm_decision_flag_is_visible_before_post_decision_wait(
    state: State, trace
) -> InvariantResult:
    del trace
    if state.post_decision_wait_events_exposed and not (
        state.pm_repair_decision_recorded and state.pm_repair_decision_flag_visible
    ):
        return InvariantResult.fail(
            "post-decision repair wait events were exposed before the PM repair decision flag was visible"
        )
    return InvariantResult.pass_()


def model_miss_triage_precedes_repair_decision(
    state: State, trace
) -> InvariantResult:
    del trace
    if state.pm_repair_decision_recorded and not state.model_miss_triage_recorded:
        return InvariantResult.fail(
            "PM selected repair before recording model-miss triage"
        )
    return InvariantResult.pass_()


def model_backed_repair_requires_flowguard_operator_report(
    state: State, trace
) -> InvariantResult:
    del trace
    if (
        state.flowguard_bug_class_modelable
        and state.pm_selected_repair_after_model_miss
        and not (
            state.model_miss_flowguard_operator_request_issued
            and state.model_miss_flowguard_operator_report_returned
            and state.same_class_findings_recorded
            and state.repair_candidates_compared
            and state.minimal_sufficient_repair_recommended
        )
    ):
        return InvariantResult.fail(
            "modelable repair was selected without FlowGuard operator findings and candidate comparison"
        )
    if (
        not state.flowguard_bug_class_modelable
        and state.pm_selected_repair_after_model_miss
        and not state.flowguard_out_of_scope_reason_recorded
    ):
        return InvariantResult.fail(
            "out-of-scope model miss lacks an explicit FlowGuard incapability reason"
        )
    return InvariantResult.pass_()


def repair_decision_requires_transaction(state: State, trace) -> InvariantResult:
    del trace
    if state.pm_repair_decision_recorded and state.transaction_committed_atomically and not (
        state.repair_transaction_opened and state.transaction_id_recorded
    ):
        return InvariantResult.fail(
            "PM repair decision advanced without a durable repair transaction"
        )
    return InvariantResult.pass_()


def repair_transaction_plan_is_executable(state: State, trace) -> InvariantResult:
    del trace
    if state.repair_plan_validation_passed:
        if state.transaction_plan_kind not in EXECUTABLE_REPAIR_PLAN_KINDS:
            return InvariantResult.fail(
                "repair transaction committed with unsupported executable plan kind"
            )
        if not _plan_has_execution_evidence(state):
            return InvariantResult.fail(
                "repair transaction committed without concrete producer, queued action, Router handler, or terminal stop"
            )
    if state.transaction_committed_atomically and not state.repair_plan_validation_passed:
        return InvariantResult.fail(
            "repair transaction committed without executable plan validation"
        )
    return InvariantResult.pass_()


def transaction_commit_requires_current_outcome_table(
    state: State, trace
) -> InvariantResult:
    del trace
    if state.transaction_committed_atomically and not (
        state.outcome_table_staged
        and state.success_outcome_routable
        and state.blocker_outcome_routable
        and state.protocol_outcome_routable
    ):
        return InvariantResult.fail(
            "repair transaction committed without a complete current outcome table"
        )
    return InvariantResult.pass_()


def active_node_and_repair_origin_are_known(state: State, trace) -> InvariantResult:
    del trace
    if state.active_node_kind not in NODE_KINDS:
        return InvariantResult.fail("repair transaction used unknown active node kind")
    if state.control_repair_origin not in CONTROL_REPAIR_ORIGINS:
        return InvariantResult.fail("repair transaction used unknown repair origin")
    return InvariantResult.pass_()


def repair_rerun_target_matches_node_kind(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.transaction_committed_atomically
        and state.transaction_plan_kind != "terminal_stop"
        and not _event_allowed_for_node_kind(
            state.rerun_target_event, state.active_node_kind
        )
    ):
        return InvariantResult.fail(
            "repair rerun target event incompatible with active node kind"
        )
    return InvariantResult.pass_()


def parent_repair_targets_parent_safe_event(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.active_node_kind in PARENT_NODE_KINDS
        or state.control_repair_origin == "parent_backward_replay"
    ) and state.transaction_committed_atomically:
        if state.rerun_target_event not in PARENT_REPAIR_SAFE_EVENTS:
            return InvariantResult.fail(
                "parent repair targeted a leaf-only current-node event"
            )
    return InvariantResult.pass_()


def committed_outcome_table_has_event_identities(
    state: State, trace
) -> InvariantResult:
    del trace
    if state.transaction_committed_atomically:
        events = _outcome_events(state)
        if any(event == "none" for event in events):
            return InvariantResult.fail(
                "repair outcome table lacks explicit event identity"
            )
        if len(set(events)) != 3:
            return InvariantResult.fail(
                "repair outcome table collapsed success blocker and protocol-blocker events"
            )
        if any(
            event in BUSINESS_VALIDATED_REPAIR_EVENTS
            for event in (state.blocker_outcome_event, state.protocol_outcome_event)
        ):
            return InvariantResult.fail(
                "repair outcome table reused a business-validated event for a non-success outcome"
            )
    return InvariantResult.pass_()


def outcome_events_match_node_kind(state: State, trace) -> InvariantResult:
    del trace
    if state.transaction_committed_atomically:
        for event in _outcome_events(state):
            if event == "none":
                continue
            compatible = EVENT_NODE_KIND_COMPATIBILITY.get(event)
            if compatible is not None and state.active_node_kind not in compatible:
                return InvariantResult.fail(
                    "repair outcome event incompatible with active node kind"
                )
    return InvariantResult.pass_()


def reviewer_recheck_requires_current_commit(state: State, trace) -> InvariantResult:
    del trace
    if state.reviewer_recheck_requested and not (
        state.transaction_committed_atomically
        and state.outcome_table_staged
        and state.success_outcome_routable
        and state.blocker_outcome_routable
        and state.protocol_outcome_routable
        and (
            state.post_repair_model_check_passed
            or not state.flowguard_bug_class_modelable
        )
    ):
        return InvariantResult.fail(
            "reviewer recheck was requested before current repair commit, outcome table, and required model check"
        )
    return InvariantResult.pass_()


def reviewer_outcomes_are_accepted_by_router(
    state: State, trace
) -> InvariantResult:
    del trace
    if state.reviewer_outcome == "success" and not state.reviewer_can_emit_success:
        return InvariantResult.fail("reviewer success outcome was not declared routable")
    if state.reviewer_outcome == "blocker" and not state.reviewer_can_emit_blocker:
        return InvariantResult.fail("reviewer blocker outcome was not declared routable")
    if (
        state.reviewer_outcome == "protocol_blocker"
        and not state.reviewer_can_emit_protocol_blocker
    ):
        return InvariantResult.fail(
            "reviewer protocol-blocker outcome was not declared routable"
        )
    if (
        state.reviewer_outcome != "none"
        and not state.router_accepted_reviewer_outcome
    ):
        return InvariantResult.fail("reviewer recheck outcome was not accepted by router")
    return InvariantResult.pass_()


def terminal_state_has_refreshed_authorities(
    state: State, trace
) -> InvariantResult:
    del trace
    if state.status in {"complete", "blocked"} and not (
        state.repair_transaction_index_refreshed
        and state.frontier_refreshed
        and state.display_refreshed
    ):
        return InvariantResult.fail(
            "terminal repair state did not refresh transaction index, frontier, and display"
        )
    if state.status == "complete" and not (
        state.original_blocker_resolved and state.main_flow_resumed_after_success
    ):
        return InvariantResult.fail(
            "successful repair terminal did not resolve blocker and resume main flow"
        )
    if state.status == "blocked" and not state.followup_blocker_registered:
        return InvariantResult.fail(
            "failed repair terminal did not register a follow-up blocker"
        )
    return InvariantResult.pass_()


def no_dead_end_after_recheck(state: State, trace) -> InvariantResult:
    del trace
    if state.no_legal_next_action and not (
        state.followup_blocker_registered or state.terminal_stop_recorded
    ):
        return InvariantResult.fail(
            "controller reached no legal next action without a current follow-up blocker or terminal stop"
        )
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="blocker_registration_is_routable",
        description="Router blocker registration preserves origin and repair outcomes.",
        predicate=blocker_registration_is_routable,
    ),
    Invariant(
        name="blocker_transaction_delegates_to_unified_engine",
        description="Blocker transaction mechanics carry one typed blocker trigger to the shared engine without owning PM-proactive intake.",
        predicate=blocker_transaction_delegates_to_unified_engine,
    ),
    Invariant(
        name="model_miss_block_kind_has_end_to_end_repair_lane",
        description="Every current reviewer blocker kind has one PM repair lane.",
        predicate=model_miss_block_kind_has_end_to_end_repair_lane,
    ),
    Invariant(
        name="pm_decision_cannot_resolve_blocker",
        description="PM prose cannot resolve the blocker.",
        predicate=pm_decision_cannot_resolve_blocker,
    ),
    Invariant(
        name="pm_decision_flag_is_visible_before_post_decision_wait",
        description="The PM decision flag is visible before any follow-up wait.",
        predicate=pm_decision_flag_is_visible_before_post_decision_wait,
    ),
    Invariant(
        name="model_miss_triage_precedes_repair_decision",
        description="Model-miss triage precedes the PM repair decision.",
        predicate=model_miss_triage_precedes_repair_decision,
    ),
    Invariant(
        name="model_backed_repair_requires_flowguard_operator_report",
        description="Modelable repairs use independent FlowGuard evidence.",
        predicate=model_backed_repair_requires_flowguard_operator_report,
    ),
    Invariant(
        name="repair_decision_requires_transaction",
        description="A committed PM repair decision has a durable transaction.",
        predicate=repair_decision_requires_transaction,
    ),
    Invariant(
        name="repair_transaction_plan_is_executable",
        description="Only current plan kinds with concrete execution evidence commit.",
        predicate=repair_transaction_plan_is_executable,
    ),
    Invariant(
        name="transaction_commit_requires_current_outcome_table",
        description="Commit includes one complete three-way outcome table.",
        predicate=transaction_commit_requires_current_outcome_table,
    ),
    Invariant(
        name="active_node_and_repair_origin_are_known",
        description="The current node kind and repair origin are known.",
        predicate=active_node_and_repair_origin_are_known,
    ),
    Invariant(
        name="repair_rerun_target_matches_node_kind",
        description="The rerun target is valid for the current node kind.",
        predicate=repair_rerun_target_matches_node_kind,
    ),
    Invariant(
        name="parent_repair_targets_parent_safe_event",
        description="Parent repair cannot target a leaf-only event.",
        predicate=parent_repair_targets_parent_safe_event,
    ),
    Invariant(
        name="committed_outcome_table_has_event_identities",
        description="Outcome identities are explicit and distinct.",
        predicate=committed_outcome_table_has_event_identities,
    ),
    Invariant(
        name="outcome_events_match_node_kind",
        description="Outcome events match the active node kind.",
        predicate=outcome_events_match_node_kind,
    ),
    Invariant(
        name="reviewer_recheck_requires_current_commit",
        description="Reviewer recheck consumes committed current repair evidence.",
        predicate=reviewer_recheck_requires_current_commit,
    ),
    Invariant(
        name="reviewer_outcomes_are_accepted_by_router",
        description="Each Reviewer outcome is routable and accepted.",
        predicate=reviewer_outcomes_are_accepted_by_router,
    ),
    Invariant(
        name="terminal_state_has_refreshed_authorities",
        description="Terminal repair state refreshes all current projections.",
        predicate=terminal_state_has_refreshed_authorities,
    ),
    Invariant(
        name="no_dead_end_after_recheck",
        description="A failed recheck has a follow-up blocker or terminal stop.",
        predicate=no_dead_end_after_recheck,
    ),
)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def _safe_base(**changes: object) -> State:
    base = State(
        status="running",
        holder="human_like_reviewer",
        active_node_kind="leaf",
        control_repair_origin="current_node_result",
        repair_trigger_origin="reviewer_or_system_failure",
        shared_repair_engine_handoff_recorded=True,
        shared_repair_engine_handoff_id_present=True,
        rerun_target_event="reviewer_current_node_result_decision",
        blocker_detected=True,
        blocker_kind="node_result",
        blocker_pm_repair_lane="route_mutation",
        blocker_registered_in_router=True,
        blocker_has_origin_event=True,
        blocker_has_allowed_nonterminal_events=True,
        pm_model_miss_cards_accept_blocker_kind=True,
        pm_model_miss_triage_accepts_blocker_kind=True,
        pm_review_repair_event_accepts_blocker_kind=True,
        pm_review_repair_event_routes_blocker_kind=True,
        model_miss_triage_recorded=True,
        flowguard_bug_class_modelable=True,
        model_miss_flowguard_operator_request_issued=True,
        model_miss_flowguard_operator_report_returned=True,
        same_class_findings_recorded=True,
        repair_candidates_compared=True,
        minimal_sufficient_repair_recommended=True,
        pm_selected_repair_after_model_miss=True,
        pm_repair_decision_recorded=True,
        pm_repair_decision_flag_visible=True,
        repair_transaction_opened=True,
        transaction_id_recorded=True,
        transaction_plan_kind="operation_replay",
        repair_plan_validation_passed=True,
        replay_operation_recorded=True,
        replay_operation_safe=True,
        concrete_repair_action_queued=True,
        outcome_table_staged=True,
        transaction_committed_atomically=True,
        post_decision_wait_events_exposed=True,
        success_outcome_routable=True,
        blocker_outcome_routable=True,
        protocol_outcome_routable=True,
        success_outcome_event="reviewer_current_node_result_decision",
        blocker_outcome_event="pm_records_current_node_repair_blocker",
        protocol_outcome_event="pm_records_current_node_protocol_blocker",
        post_repair_model_check_passed=True,
        reviewer_recheck_requested=True,
        reviewer_can_emit_success=True,
        reviewer_can_emit_blocker=True,
        reviewer_can_emit_protocol_blocker=True,
    )
    return replace(base, **changes)


def hazard_states() -> dict[str, State]:
    return {
        "blocker_handoff_to_unified_engine_missing": _safe_base(
            shared_repair_engine_handoff_recorded=False,
            shared_repair_engine_handoff_id_present=False,
        ),
        "pm_proactive_historical_intake_claimed_by_blocker_child": _safe_base(
            repair_trigger_origin="pm_historical_defect",
            pm_proactive_historical_intake_claimed=True,
        ),
        "blocker_child_claims_shared_engine_ownership": _safe_base(
            owns_shared_repair_engine=True,
        ),
        "router_blocker_missing_origin": _safe_base(
            blocker_has_origin_event=False
        ),
        "node_acceptance_plan_without_pm_lane": _safe_base(
            blocker_kind="node_acceptance_plan",
            blocker_pm_repair_lane="none",
        ),
        "current_node_dispatch_missing_model_miss_card_support": _safe_base(
            blocker_kind="current_node_dispatch",
            pm_model_miss_cards_accept_blocker_kind=False,
        ),
        "retired_material_dispatch_repair_lane_reintroduced": _safe_base(
            blocker_kind="material_dispatch",
            blocker_pm_repair_lane="material_dispatch_recheck",
        ),
        "pm_decision_self_resolves_blocker": _safe_base(
            pm_decision_resolves_blocker=True
        ),
        "post_decision_wait_exposed_before_pm_flag_visible": _safe_base(
            pm_repair_decision_flag_visible=False
        ),
        "repair_decision_without_model_miss_triage": _safe_base(
            model_miss_triage_recorded=False
        ),
        "modelable_repair_without_flowguard_report": _safe_base(
            model_miss_flowguard_operator_report_returned=False
        ),
        "repair_commits_without_transaction_identity": _safe_base(
            repair_transaction_opened=False,
            transaction_id_recorded=False,
        ),
        "retired_packet_reissue_accepted": _safe_base(
            transaction_plan_kind="packet_reissue"
        ),
        "operation_replay_without_safe_recorded_action": _safe_base(
            replay_operation_safe=False
        ),
        "controller_repair_packet_unbounded": _safe_base(
            transaction_plan_kind="controller_repair_work_packet",
            replay_operation_recorded=False,
            replay_operation_safe=False,
            controller_repair_packet_bounded=False,
        ),
        "role_reissue_without_current_producer": _safe_base(
            transaction_plan_kind="role_reissue",
            replay_operation_recorded=False,
            replay_operation_safe=False,
            concrete_repair_action_queued=False,
            current_followup_producer_bound=False,
        ),
        "await_existing_event_without_producer": _safe_base(
            transaction_plan_kind="await_existing_event",
            replay_operation_recorded=False,
            replay_operation_safe=False,
            concrete_repair_action_queued=False,
            existing_event_producer_found=False,
        ),
        "router_reconcile_without_handler": _safe_base(
            transaction_plan_kind="router_internal_reconcile",
            replay_operation_recorded=False,
            replay_operation_safe=False,
            concrete_repair_action_queued=False,
            router_internal_handler_found=False,
        ),
        "terminal_stop_without_terminal_record": _safe_base(
            transaction_plan_kind="terminal_stop",
            replay_operation_recorded=False,
            replay_operation_safe=False,
            concrete_repair_action_queued=False,
            terminal_stop_recorded=False,
        ),
        "transaction_commits_without_plan_validation": _safe_base(
            repair_plan_validation_passed=False
        ),
        "transaction_commits_without_outcome_table": _safe_base(
            outcome_table_staged=False
        ),
        "success_only_outcome_table": _safe_base(
            blocker_outcome_routable=False,
            protocol_outcome_routable=False,
        ),
        "parent_repair_rerun_targets_current_node_packet": _safe_base(
            active_node_kind="parent",
            control_repair_origin="parent_backward_replay",
            rerun_target_event="pm_registers_current_node_packet",
            success_outcome_event="pm_completes_parent_node",
        ),
        "collapsed_repair_outcomes_on_business_event": _safe_base(
            blocker_outcome_event="reviewer_current_node_result_decision",
            protocol_outcome_event="reviewer_current_node_result_decision",
        ),
        "routable_outcome_missing_event_identity": _safe_base(
            success_outcome_event="none"
        ),
        "reviewer_recheck_before_current_commit": _safe_base(
            transaction_committed_atomically=False
        ),
        "reviewer_recheck_before_post_repair_model_check": _safe_base(
            post_repair_model_check_passed=False
        ),
        "reviewer_blocker_unroutable": _safe_base(
            reviewer_outcome="blocker",
            router_accepted_reviewer_outcome=False,
        ),
        "successful_terminal_without_authority_refresh": _safe_base(
            status="complete",
            reviewer_outcome="success",
            router_accepted_reviewer_outcome=True,
            original_blocker_resolved=True,
            main_flow_resumed_after_success=True,
            repair_transaction_index_refreshed=False,
            frontier_refreshed=False,
            display_refreshed=False,
        ),
        "controller_no_next_action_without_followup_blocker": _safe_base(
            no_legal_next_action=True,
            followup_blocker_registered=False,
        ),
    }


def build_workflow() -> Workflow:
    return Workflow((RepairTransactionStep(),), name="flowpilot_repair_transaction")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 21
