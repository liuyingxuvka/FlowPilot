"""FlowGuard model for FlowPilot parallel packet batch routing.

Risk intent brief:
- Model the proposed PM-authored parallel packet batch before runtime changes.
- Protect harms: route stage advancement from partial packet results, reviewer
  pass over only a subset of batch results, role overload, duplicate packet
  registration, old single-packet bypasses, officer-result join loss,
  Controller sealed-body reads, blocked packet pass-through, repair lineage
  loss, prompt/runtime drift, and static event-producer waits that reject a
  valid remaining batch member.
- Modeled state and side effects: batch registration, packet membership, role
  busy state, packet relay, result return, reviewer batch coverage, PM
  absorption, repair lineage, prompt/runtime conformance, and stage advance.
- Hard invariant: a batch may advance only after every member packet returned,
  every required packet was reviewed in one batch review, no packet is blocked,
  and PM absorbed the reviewed batch when PM absorption is required.
- Blindspot: this is an abstract control-flow model. Runtime tests still need
  to prove concrete file paths, hashes, packet ledgers, and prompt cards match
  the implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


TOTAL_PACKETS = 4
WORKER_PACKETS = 2
OFFICER_PACKETS = 2


@dataclass(frozen=True)
class Tick:
    """One abstract router batch transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | complete
    batch_registered: bool = False
    batch_id_unique: bool = True
    duplicate_active_batch_accepted: bool = False
    packet_count: int = 0
    packet_ids_unique: bool = True
    all_packets_in_batch_index: bool = False
    old_single_packet_bypass_used: bool = False

    worker_packet_count: int = 0
    officer_packet_count: int = 0
    officer_packets_counted_in_join: bool = False

    role_busy_guard_enabled: bool = False
    role_overload_accepted: bool = False
    packets_relayed: int = 0
    controller_envelope_only: bool = True
    controller_read_sealed_body: bool = False

    results_returned: int = 0
    blocked_packet_count: int = 0
    batch_joined: bool = False
    dynamic_wait_producer_binding_valid: bool = True

    review_required: bool = True
    batch_review_done: bool = False
    reviewed_packet_count: int = 0
    reviewer_open_receipts_verified: bool = False
    batch_review_passed: bool = False

    pm_absorption_required: bool = True
    pm_absorbed_batch: bool = False

    repair_reissued: bool = False
    repair_lineage_recorded: bool = True

    prompt_advertises_batch: bool = True
    runtime_supports_batch: bool = True

    stage_advanced: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def registered_batch_state() -> State:
    return State(
        status="running",
        batch_registered=True,
        packet_count=TOTAL_PACKETS,
        worker_packet_count=WORKER_PACKETS,
        officer_packet_count=OFFICER_PACKETS,
        all_packets_in_batch_index=True,
        officer_packets_counted_in_join=True,
        role_busy_guard_enabled=True,
        prompt_advertises_batch=True,
        runtime_supports_batch=True,
    )


def relayed_batch_state() -> State:
    return replace(registered_batch_state(), packets_relayed=TOTAL_PACKETS)


def returned_batch_state() -> State:
    return replace(relayed_batch_state(), results_returned=TOTAL_PACKETS, batch_joined=True)


def reviewed_batch_state() -> State:
    return replace(
        returned_batch_state(),
        batch_review_done=True,
        reviewed_packet_count=TOTAL_PACKETS,
        reviewer_open_receipts_verified=True,
        batch_review_passed=True,
    )


def absorbed_batch_state() -> State:
    return replace(reviewed_batch_state(), pm_absorbed_batch=True)


def success_state() -> State:
    return replace(absorbed_batch_state(), status="complete", stage_advanced=True)


def repaired_batch_state() -> State:
    return replace(
        registered_batch_state(),
        repair_reissued=True,
        repair_lineage_recorded=True,
    )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "new":
        yield Transition("register_parallel_packet_batch", registered_batch_state())
        return
    if state.status == "running" and state.batch_registered and state.packets_relayed == 0:
        yield Transition("relay_every_batch_packet", relayed_batch_state())
        yield Transition("reissue_batch_with_lineage", repaired_batch_state())
        return
    if state.status == "running" and state.packets_relayed == TOTAL_PACKETS and state.results_returned == 0:
        yield Transition("wait_for_all_batch_results", returned_batch_state())
        return
    if state.status == "running" and state.batch_joined and not state.batch_review_done:
        yield Transition("review_full_batch", reviewed_batch_state())
        return
    if state.status == "running" and state.batch_review_passed and not state.pm_absorbed_batch:
        yield Transition("pm_absorbs_reviewed_batch", absorbed_batch_state())
        return
    if state.status == "running" and state.pm_absorbed_batch and not state.stage_advanced:
        yield Transition("advance_after_batch_join_review_and_pm_absorption", success_state())


class ParallelPacketBatchStep:
    """Model one parallel packet batch transition.

    Input x State -> Set(Output x State)
    reads: active batch index, packet ledger, role busy state, result ledger,
    reviewer coverage, PM absorption, prompt/runtime conformance
    writes: batch status, packet relay status, result status, review status,
    PM absorption status, and stage advancement status
    idempotency: batch and packet ids are stable; repeated checks must not
    create duplicate packet records or duplicate stage advancement.
    """

    name = "ParallelPacketBatchStep"
    input_description = "FlowPilot parallel batch tick"
    output_description = "one batch routing transition"
    reads = (
        "batch_index",
        "packet_ledger",
        "role_busy_state",
        "result_ledger",
        "reviewer_coverage",
        "pm_absorption",
        "prompt_runtime_conformance",
    )
    writes = (
        "batch_index",
        "packet_relay_status",
        "result_join_status",
        "review_status",
        "pm_absorption_status",
        "route_stage",
    )
    idempotency = "batch_id and packet_id keyed updates"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status == "new":
        return failures

    if state.batch_registered and (not state.batch_id_unique or state.duplicate_active_batch_accepted):
        failures.append("duplicate active batch or batch id was accepted")
    if state.batch_registered and (state.packet_count <= 0 or not state.packet_ids_unique):
        failures.append("batch accepted without a positive unique packet list")
    if state.packets_relayed and not (state.batch_registered and state.all_packets_in_batch_index):
        failures.append("packet relayed without canonical batch membership")
    if state.old_single_packet_bypass_used:
        failures.append("old single-packet path bypassed the batch index")
    if state.role_overload_accepted or not state.role_busy_guard_enabled:
        failures.append("router assigned a second open packet to a busy role")
    if not state.controller_envelope_only or state.controller_read_sealed_body:
        failures.append("Controller read sealed body or lost envelope-only boundary")
    if state.batch_joined and state.results_returned != state.packet_count:
        failures.append("batch joined before every packet result returned")
    if not state.dynamic_wait_producer_binding_valid:
        failures.append("dynamic batch wait rejected a valid remaining event producer role")
    if state.officer_packet_count and not state.officer_packets_counted_in_join:
        failures.append("officer packet result was not counted in the batch join")
    if state.batch_review_passed and not (
        state.batch_review_done
        and state.reviewed_packet_count == state.packet_count
        and state.reviewer_open_receipts_verified
    ):
        failures.append("reviewer passed batch without reviewing every packet result")
    if state.batch_review_passed and state.blocked_packet_count:
        failures.append("batch passed even though at least one packet was blocked")
    if state.stage_advanced and not (
        state.batch_registered
        and state.batch_joined
        and state.results_returned == state.packet_count
        and (not state.review_required or state.batch_review_passed)
        and (not state.pm_absorption_required or state.pm_absorbed_batch)
        and state.blocked_packet_count == 0
    ):
        failures.append("route stage advanced before full batch join, review, and PM absorption")
    if state.repair_reissued and not state.repair_lineage_recorded:
        failures.append("replacement batch lost parent batch or packet lineage")
    if state.prompt_advertises_batch and not state.runtime_supports_batch:
        failures.append("prompt advertises batch parallelism but runtime remains single active request")

    return failures


def batch_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_parallel_packet_batch_preserves_join_review_and_pm_absorption",
        description=(
            "PM-authored parallel batches may advance only after every packet "
            "is registered, relayed, returned, reviewed when required, and "
            "absorbed by PM when required."
        ),
        predicate=batch_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 7


def build_workflow() -> Workflow:
    return Workflow((ParallelPacketBatchStep(),), name="flowpilot_parallel_packet_batch")


def is_terminal(state: State) -> bool:
    return state.status == "complete"


def is_success(state: State) -> bool:
    return state.status == "complete" and not invariant_failures(state)


def implementation_plan_state() -> State:
    return success_state()


def hazard_states() -> dict[str, State]:
    safe = success_state()
    return {
        "advance_after_first_result": replace(
            safe,
            results_returned=1,
            batch_joined=False,
            batch_review_done=False,
            reviewed_packet_count=0,
            reviewer_open_receipts_verified=False,
            batch_review_passed=False,
            pm_absorbed_batch=False,
            stage_advanced=True,
        ),
        "partial_review_pass": replace(
            safe,
            batch_review_done=True,
            reviewed_packet_count=TOTAL_PACKETS - 1,
            reviewer_open_receipts_verified=True,
            batch_review_passed=True,
        ),
        "busy_role_overload": replace(safe, role_overload_accepted=True),
        "duplicate_packet_or_batch": replace(safe, duplicate_active_batch_accepted=True),
        "old_single_packet_bypass": replace(safe, old_single_packet_bypass_used=True),
        "officer_result_not_joined": replace(safe, officer_packets_counted_in_join=False),
        "controller_reads_body": replace(safe, controller_read_sealed_body=True),
        "blocked_packet_passed": replace(safe, blocked_packet_count=1, batch_review_passed=True),
        "repair_lineage_lost": replace(safe, repair_reissued=True, repair_lineage_recorded=False),
        "prompt_runtime_drift": replace(safe, prompt_advertises_batch=True, runtime_supports_batch=False),
        "static_event_producer_wait": replace(safe, dynamic_wait_producer_binding_valid=False),
    }
