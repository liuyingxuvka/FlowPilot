"""FlowGuard model for FlowPilot repair transactions.

Risk intent brief:
- Prevent one-off PM repair patches from bypassing packet runtime authority.
- Model the durable repair transaction that should exist between a reviewer
  blocker and any resumed worker dispatch.
- Critical state: blocker registration, PM repair decision, transaction plan,
  packet generation materialization, packet ledger, dispatch index, router
  resolution table, reviewer recheck outcome, and refreshed run authorities.
- Adversarial branches include spec-only reissues, partial publication, success
  only resolution gates, reviewer blocker outcomes that cannot be routed, PM
  decisions resolving blockers by themselves, stale packet generations, and
  controller no-legal-next-action after a valid recheck failure.
- Hard invariant: a repair is a transaction. It either commits one coherent new
  packet generation with both success and non-success outcomes routable, or it
  remains blocked with a router-visible follow-up blocker.
- Blindspot: this is a protocol model. It does not assert product quality or
  inspect concrete packet body contents.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


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
    steps: int = 0

    blocker_detected: bool = False
    blocker_registered_in_router: bool = False
    blocker_has_origin_event: bool = False
    blocker_has_allowed_nonterminal_events: bool = False

    pm_repair_decision_recorded: bool = False
    pm_decision_resolves_blocker: bool = False
    repair_transaction_opened: bool = False
    transaction_id_recorded: bool = False
    transaction_plan_kind: str = "none"  # none | packet_reissue | route_mutation

    replacement_spec_written: bool = False
    packet_files_staged: bool = False
    ledger_entries_staged: bool = False
    dispatch_index_staged: bool = False
    router_resolution_table_staged: bool = False
    transaction_committed_atomically: bool = False
    partial_generation_published: bool = False

    replacement_generation_published: bool = False
    old_generation_superseded: bool = False
    canonical_packet_identity_unique: bool = False
    packet_hashes_replayable: bool = False
    result_write_targets_explicit: bool = False

    success_outcome_routable: bool = False
    blocker_outcome_routable: bool = False
    protocol_outcome_routable: bool = False

    reviewer_recheck_requested: bool = False
    reviewer_can_emit_success: bool = False
    reviewer_can_emit_blocker: bool = False
    reviewer_can_emit_protocol_blocker: bool = False
    reviewer_outcome: str = "none"  # none | success | blocker | protocol_blocker
    router_accepted_reviewer_outcome: bool = False

    original_blocker_resolved: bool = False
    followup_blocker_registered: bool = False
    packet_ledger_refreshed: bool = False
    frontier_refreshed: bool = False
    display_refreshed: bool = False
    no_legal_next_action: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _inc(state: State, **changes: object) -> State:
    return replace(state, steps=state.steps + 1, status="running", **changes)


class RepairTransactionStep:
    """One FlowPilot repair transaction transition.

    Input x State -> Set(Output x State)
    reads: blocker state, PM decision, staged generation, outcome table,
    reviewer recheck result, visible run authorities
    writes: one durable transaction fact or terminal blocker/resolution state
    idempotency: facts are monotonic within a transaction id; a committed
    generation is not republished with a different body identity
    """

    name = "RepairTransactionStep"
    input_description = "repair-control tick"
    output_description = "one repair transaction state transition"
    reads = (
        "router_blocker_state",
        "pm_repair_decision",
        "packet_generation_stage",
        "router_resolution_table",
        "reviewer_recheck_result",
    )
    writes = (
        "repair_transaction",
        "packet_runtime_generation",
        "router_resolution",
        "followup_blocker",
        "refreshed_authorities",
    )
    idempotency = "transaction-id scoped monotonic writes"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"complete", "blocked"}:
        return

    if not state.blocker_detected:
        yield Transition(
            "reviewer_blocker_detected",
            _inc(state, blocker_detected=True, holder="controller"),
        )
        return

    if not state.blocker_registered_in_router:
        yield Transition(
            "router_registers_blocker_with_origin_and_failure_events",
            _inc(
                state,
                blocker_registered_in_router=True,
                blocker_has_origin_event=True,
                blocker_has_allowed_nonterminal_events=True,
            ),
        )
        return

    if not state.pm_repair_decision_recorded:
        yield Transition(
            "pm_records_repair_decision_without_resolving_blocker",
            _inc(
                state,
                holder="pm",
                pm_repair_decision_recorded=True,
                pm_decision_resolves_blocker=False,
            ),
        )
        return

    if not state.repair_transaction_opened:
        yield Transition(
            "router_opens_repair_transaction",
            _inc(
                state,
                holder="controller",
                repair_transaction_opened=True,
                transaction_id_recorded=True,
                transaction_plan_kind="packet_reissue",
            ),
        )
        return

    if not state.replacement_spec_written:
        yield Transition(
            "pm_writes_reissue_spec_inside_transaction",
            _inc(state, holder="pm", replacement_spec_written=True),
        )
        return

    if not state.transaction_committed_atomically:
        yield Transition(
            "router_atomically_commits_reissue_generation_and_outcome_table",
            _inc(
                state,
                holder="controller",
                packet_files_staged=True,
                ledger_entries_staged=True,
                dispatch_index_staged=True,
                router_resolution_table_staged=True,
                transaction_committed_atomically=True,
                partial_generation_published=False,
                replacement_generation_published=True,
                old_generation_superseded=True,
                canonical_packet_identity_unique=True,
                packet_hashes_replayable=True,
                result_write_targets_explicit=True,
                success_outcome_routable=True,
                blocker_outcome_routable=True,
                protocol_outcome_routable=True,
            ),
        )
        return

    if not state.reviewer_recheck_requested:
        yield Transition(
            "reviewer_recheck_requested_after_committed_generation",
            _inc(
                state,
                holder="reviewer",
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
                holder="controller",
                reviewer_outcome="success",
                router_accepted_reviewer_outcome=True,
                original_blocker_resolved=True,
            ),
        )
        yield Transition(
            "reviewer_recheck_returns_followup_blocker",
            _inc(
                state,
                holder="controller",
                reviewer_outcome="blocker",
                router_accepted_reviewer_outcome=True,
                followup_blocker_registered=True,
            ),
        )
        yield Transition(
            "reviewer_recheck_returns_protocol_blocker",
            _inc(
                state,
                holder="controller",
                reviewer_outcome="protocol_blocker",
                router_accepted_reviewer_outcome=True,
                followup_blocker_registered=True,
            ),
        )
        return

    if not (
        state.packet_ledger_refreshed and state.frontier_refreshed and state.display_refreshed
    ):
        terminal_status = "complete" if state.original_blocker_resolved else "blocked"
        yield Transition(
            "router_refreshes_visible_authorities_after_recheck",
            replace(
                state,
                status=terminal_status,
                steps=state.steps + 1,
                holder="controller",
                packet_ledger_refreshed=True,
                frontier_refreshed=True,
                display_refreshed=True,
                no_legal_next_action=False,
            ),
        )
        return


def blocker_registration_is_routable(state: State, trace) -> InvariantResult:
    del trace
    if state.blocker_registered_in_router and not (
        state.blocker_has_origin_event and state.blocker_has_allowed_nonterminal_events
    ):
        return InvariantResult.fail(
            "router blocker registration lacked origin or nonterminal repair events"
        )
    return InvariantResult.pass_()


def pm_decision_cannot_resolve_blocker(state: State, trace) -> InvariantResult:
    del trace
    if state.pm_repair_decision_recorded and state.pm_decision_resolves_blocker:
        return InvariantResult.fail("PM repair decision resolved the blocker by itself")
    return InvariantResult.pass_()


def repair_decision_requires_transaction(state: State, trace) -> InvariantResult:
    del trace
    if state.replacement_spec_written and not (
        state.repair_transaction_opened
        and state.transaction_id_recorded
        and state.transaction_plan_kind in {"packet_reissue", "route_mutation"}
    ):
        return InvariantResult.fail(
            "PM repair wrote replacement artifacts outside a repair transaction"
        )
    return InvariantResult.pass_()


def transaction_commit_requires_complete_generation(state: State, trace) -> InvariantResult:
    del trace
    if state.transaction_committed_atomically and not (
        state.packet_files_staged
        and state.ledger_entries_staged
        and state.dispatch_index_staged
        and state.router_resolution_table_staged
        and not state.partial_generation_published
    ):
        return InvariantResult.fail(
            "repair transaction committed without packet files, ledger, dispatch index, router table, or atomic publication"
        )
    return InvariantResult.pass_()


def committed_generation_has_single_identity(state: State, trace) -> InvariantResult:
    del trace
    if state.replacement_generation_published and not (
        state.old_generation_superseded
        and state.canonical_packet_identity_unique
        and state.packet_hashes_replayable
        and state.result_write_targets_explicit
    ):
        return InvariantResult.fail(
            "replacement packet generation lacked supersession, canonical identity, replayable hashes, or explicit result targets"
        )
    return InvariantResult.pass_()


def outcome_table_accepts_success_and_failure(state: State, trace) -> InvariantResult:
    del trace
    if state.router_resolution_table_staged and not (
        state.success_outcome_routable
        and state.blocker_outcome_routable
        and state.protocol_outcome_routable
    ):
        return InvariantResult.fail(
            "repair transaction router outcome table did not route success, blocker, and protocol outcomes"
        )
    return InvariantResult.pass_()


def reviewer_recheck_requires_committed_generation(state: State, trace) -> InvariantResult:
    del trace
    if state.reviewer_recheck_requested and not (
        state.transaction_committed_atomically
        and state.replacement_generation_published
        and state.success_outcome_routable
        and state.blocker_outcome_routable
        and state.protocol_outcome_routable
    ):
        return InvariantResult.fail(
            "reviewer recheck was requested before a committed generation and complete outcome table"
        )
    return InvariantResult.pass_()


def reviewer_outcomes_are_accepted_by_router(state: State, trace) -> InvariantResult:
    del trace
    if state.reviewer_outcome != "none" and not state.router_accepted_reviewer_outcome:
        return InvariantResult.fail("reviewer recheck outcome was not accepted by router")
    if state.reviewer_outcome == "success" and not state.success_outcome_routable:
        return InvariantResult.fail("reviewer success outcome was not routable")
    if state.reviewer_outcome == "blocker" and not state.blocker_outcome_routable:
        return InvariantResult.fail("reviewer blocker outcome was not routable")
    if state.reviewer_outcome == "protocol_blocker" and not state.protocol_outcome_routable:
        return InvariantResult.fail("reviewer protocol blocker outcome was not routable")
    return InvariantResult.pass_()


def terminal_state_has_refreshed_authorities(state: State, trace) -> InvariantResult:
    del trace
    if state.status in {"complete", "blocked"} and not (
        state.packet_ledger_refreshed and state.frontier_refreshed and state.display_refreshed
    ):
        return InvariantResult.fail(
            "terminal repair transaction state did not refresh ledger, frontier, and display authorities"
        )
    if state.status == "complete" and not state.original_blocker_resolved:
        return InvariantResult.fail("repair transaction completed without resolving the original blocker")
    if state.status == "blocked" and not state.followup_blocker_registered:
        return InvariantResult.fail("repair transaction blocked without registering a follow-up blocker")
    return InvariantResult.pass_()


def no_dead_end_after_recheck(state: State, trace) -> InvariantResult:
    del trace
    if state.no_legal_next_action:
        return InvariantResult.fail("repair transaction reached no legal next action")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="blocker_registration_is_routable",
        description="A blocker carries origin and nonterminal repair events.",
        predicate=blocker_registration_is_routable,
    ),
    Invariant(
        name="pm_decision_cannot_resolve_blocker",
        description="PM repair decisions choose a repair, they do not self-resolve blockers.",
        predicate=pm_decision_cannot_resolve_blocker,
    ),
    Invariant(
        name="repair_decision_requires_transaction",
        description="Replacement artifacts are written only inside a repair transaction.",
        predicate=repair_decision_requires_transaction,
    ),
    Invariant(
        name="transaction_commit_requires_complete_generation",
        description="A committed repair transaction publishes one complete packet generation atomically.",
        predicate=transaction_commit_requires_complete_generation,
    ),
    Invariant(
        name="committed_generation_has_single_identity",
        description="The replacement generation supersedes old packets and has one replayable canonical identity.",
        predicate=committed_generation_has_single_identity,
    ),
    Invariant(
        name="outcome_table_accepts_success_and_failure",
        description="Router outcome table routes success, blocker, and protocol blocker outcomes.",
        predicate=outcome_table_accepts_success_and_failure,
    ),
    Invariant(
        name="reviewer_recheck_requires_committed_generation",
        description="Reviewer recheck starts only after commit and complete outcome table.",
        predicate=reviewer_recheck_requires_committed_generation,
    ),
    Invariant(
        name="reviewer_outcomes_are_accepted_by_router",
        description="Every reviewer recheck outcome has a router transition.",
        predicate=reviewer_outcomes_are_accepted_by_router,
    ),
    Invariant(
        name="terminal_state_has_refreshed_authorities",
        description="Resolved or blocked repair transactions refresh visible authorities.",
        predicate=terminal_state_has_refreshed_authorities,
    ),
    Invariant(
        name="no_dead_end_after_recheck",
        description="Repair transactions never enter controller no-legal-next-action.",
        predicate=no_dead_end_after_recheck,
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
            blocker_detected=True,
            blocker_registered_in_router=True,
            blocker_has_origin_event=True,
            blocker_has_allowed_nonterminal_events=True,
            pm_repair_decision_recorded=True,
            repair_transaction_opened=True,
            transaction_id_recorded=True,
            transaction_plan_kind="packet_reissue",
            replacement_spec_written=True,
            packet_files_staged=True,
            ledger_entries_staged=True,
            dispatch_index_staged=True,
            router_resolution_table_staged=True,
            transaction_committed_atomically=True,
            replacement_generation_published=True,
            old_generation_superseded=True,
            canonical_packet_identity_unique=True,
            packet_hashes_replayable=True,
            result_write_targets_explicit=True,
            success_outcome_routable=True,
            blocker_outcome_routable=True,
            protocol_outcome_routable=True,
            reviewer_recheck_requested=True,
            reviewer_can_emit_success=True,
            reviewer_can_emit_blocker=True,
            reviewer_can_emit_protocol_blocker=True,
            reviewer_outcome="success",
            router_accepted_reviewer_outcome=True,
            original_blocker_resolved=True,
            packet_ledger_refreshed=True,
            frontier_refreshed=True,
            display_refreshed=True,
        ),
        **changes,
    )


def hazard_states() -> dict[str, State]:
    return {
        "blocker_registered_without_nonterminal_events": _safe_base(
            blocker_has_allowed_nonterminal_events=False,
        ),
        "pm_decision_self_resolves_blocker": _safe_base(
            pm_decision_resolves_blocker=True,
        ),
        "reissue_spec_outside_transaction": _safe_base(
            repair_transaction_opened=False,
            transaction_id_recorded=False,
            replacement_spec_written=True,
        ),
        "transaction_commits_packet_files_without_ledger": _safe_base(
            transaction_committed_atomically=True,
            packet_files_staged=True,
            ledger_entries_staged=False,
        ),
        "transaction_commits_ledger_without_dispatch_index": _safe_base(
            transaction_committed_atomically=True,
            ledger_entries_staged=True,
            dispatch_index_staged=False,
        ),
        "transaction_commits_without_router_outcome_table": _safe_base(
            transaction_committed_atomically=True,
            router_resolution_table_staged=False,
        ),
        "partial_generation_published_before_commit": _safe_base(
            transaction_committed_atomically=True,
            partial_generation_published=True,
        ),
        "replacement_generation_keeps_old_generation_current": _safe_base(
            replacement_generation_published=True,
            old_generation_superseded=False,
        ),
        "replacement_generation_has_duplicate_identity": _safe_base(
            replacement_generation_published=True,
            canonical_packet_identity_unique=False,
        ),
        "success_only_outcome_table": _safe_base(
            router_resolution_table_staged=True,
            success_outcome_routable=True,
            blocker_outcome_routable=False,
            protocol_outcome_routable=False,
        ),
        "reviewer_recheck_before_commit": _safe_base(
            transaction_committed_atomically=False,
            reviewer_recheck_requested=True,
        ),
        "reviewer_blocker_unroutable": _safe_base(
            reviewer_outcome="blocker",
            router_accepted_reviewer_outcome=False,
            blocker_outcome_routable=False,
        ),
        "reviewer_protocol_blocker_unroutable": _safe_base(
            reviewer_outcome="protocol_blocker",
            router_accepted_reviewer_outcome=False,
            protocol_outcome_routable=False,
        ),
        "blocked_terminal_without_followup_blocker": _safe_base(
            status="blocked",
            reviewer_outcome="blocker",
            original_blocker_resolved=False,
            followup_blocker_registered=False,
        ),
        "complete_terminal_without_authority_refresh": _safe_base(
            status="complete",
            packet_ledger_refreshed=False,
            frontier_refreshed=False,
            display_refreshed=False,
        ),
        "controller_no_legal_next_after_recheck": _safe_base(
            reviewer_outcome="protocol_blocker",
            no_legal_next_action=True,
        ),
    }


def build_workflow() -> Workflow:
    return Workflow((RepairTransactionStep(),), name="flowpilot_repair_transaction")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"complete", "blocked"}


def is_success(state: State) -> bool:
    return state.status == "complete"


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 24


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "Action",
    "State",
    "Tick",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_states",
]
