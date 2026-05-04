from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class NodeCase:
    case_id: str
    reviewer_dispatch: str
    result_origin: str


@dataclass(frozen=True)
class NodePacket:
    packet_id: str
    allowed_origin: str = "worker"
    has_controller_reminder: bool = True


@dataclass(frozen=True)
class DispatchBlocked:
    packet_id: str
    reason: str


@dataclass(frozen=True)
class ApprovedPacket:
    packet_id: str
    allowed_origin: str


@dataclass(frozen=True)
class NodeResult:
    packet_id: str
    origin: str


@dataclass(frozen=True)
class ReviewPass:
    packet_id: str


@dataclass(frozen=True)
class ReviewBlock:
    packet_id: str
    reason: str


@dataclass(frozen=True)
class PMAdvanced:
    packet_id: str


@dataclass(frozen=True)
class State:
    packets: tuple[str, ...] = ()
    reminder_checked: tuple[str, ...] = ()
    reminder_blocks: tuple[str, ...] = ()
    dispatches: tuple[str, ...] = ()
    worker_results: tuple[str, ...] = ()
    controller_artifacts: tuple[str, ...] = ()
    review_passes: tuple[str, ...] = ()
    review_blocks: tuple[str, ...] = ()
    advances: tuple[str, ...] = ()


class PMIssuePacket:
    name = "PMIssuePacket"
    accepted_input_type = NodeCase
    reads = ("packets",)
    writes = ("packets",)
    input_description = "node case selected by PM route loop"
    output_description = "PM-authored packet"
    idempotency = "Packet IDs are issued once."

    def apply(self, input_obj: NodeCase, state: State) -> Iterable[FunctionResult]:
        new_state = state if input_obj.case_id in state.packets else replace(state, packets=state.packets + (input_obj.case_id,))
        has_reminder = not input_obj.case_id.startswith("missing_reminder")
        yield FunctionResult(NodePacket(input_obj.case_id, has_controller_reminder=has_reminder), new_state, "pm_packet_issued")


class ControllerReminderCheck:
    name = "ControllerReminderCheck"
    accepted_input_type = NodePacket
    reads = ("packets",)
    writes = ("reminder_checked", "reminder_blocks")
    input_description = "PM packet with required controller reminder"
    output_description = "NodePacket or DispatchBlocked"
    idempotency = "Reminder check is keyed by packet ID."

    def apply(self, input_obj: NodePacket, state: State) -> Iterable[FunctionResult]:
        if not input_obj.has_controller_reminder:
            new_state = replace(state, reminder_blocks=state.reminder_blocks + (input_obj.packet_id,))
            yield FunctionResult(DispatchBlocked(input_obj.packet_id, "missing_controller_reminder"), new_state, "controller_missing_pm_reminder")
            return
        new_state = state if input_obj.packet_id in state.reminder_checked else replace(
            state, reminder_checked=state.reminder_checked + (input_obj.packet_id,)
        )
        yield FunctionResult(input_obj, new_state, "controller_reminder_checked")


class ReviewerDispatch:
    name = "ReviewerDispatch"
    accepted_input_type = NodePacket
    reads = ("packets",)
    writes = ("dispatches", "review_blocks")
    input_description = "PM packet"
    output_description = "ApprovedPacket or DispatchBlocked"
    idempotency = "Dispatch approval is keyed by packet ID."

    def apply(self, input_obj: NodePacket, state: State) -> Iterable[FunctionResult]:
        # The case id encodes the abstract reviewer dispatch decision for finite exploration.
        if input_obj.packet_id.startswith("dispatch_block"):
            new_state = replace(state, review_blocks=state.review_blocks + (input_obj.packet_id,))
            yield FunctionResult(DispatchBlocked(input_obj.packet_id, "reviewer_dispatch_block"), new_state, "reviewer_dispatch_blocked")
            return
        new_state = state if input_obj.packet_id in state.dispatches else replace(state, dispatches=state.dispatches + (input_obj.packet_id,))
        yield FunctionResult(ApprovedPacket(input_obj.packet_id, input_obj.allowed_origin), new_state, "reviewer_dispatch_approved")


class WorkerOrControllerResult:
    name = "WorkerOrControllerResult"
    accepted_input_type = ApprovedPacket
    reads = ("dispatches",)
    writes = ("worker_results", "controller_artifacts")
    input_description = "dispatch-approved packet"
    output_description = "node result with origin"
    idempotency = "Node result is keyed by packet ID."

    def apply(self, input_obj: ApprovedPacket, state: State) -> Iterable[FunctionResult]:
        origin = "controller" if input_obj.packet_id.startswith("controller_origin") else "worker"
        if origin == "controller":
            new_state = replace(state, controller_artifacts=state.controller_artifacts + (input_obj.packet_id,))
            yield FunctionResult(NodeResult(input_obj.packet_id, origin), new_state, "controller_origin_result")
            return
        new_state = replace(state, worker_results=state.worker_results + (input_obj.packet_id,))
        yield FunctionResult(NodeResult(input_obj.packet_id, origin), new_state, "worker_result")


class ReviewerResult:
    name = "ReviewerResult"
    accepted_input_type = NodeResult
    reads = ("worker_results", "controller_artifacts")
    writes = ("review_passes", "review_blocks")
    input_description = "node result"
    output_description = "ReviewPass or ReviewBlock"
    idempotency = "Review result is keyed by packet ID."

    def apply(self, input_obj: NodeResult, state: State) -> Iterable[FunctionResult]:
        if input_obj.origin != "worker":
            new_state = replace(state, review_blocks=state.review_blocks + (input_obj.packet_id,))
            yield FunctionResult(ReviewBlock(input_obj.packet_id, "block_invalid_role_origin"), new_state, "review_block_invalid_role_origin")
            return
        new_state = replace(state, review_passes=state.review_passes + (input_obj.packet_id,))
        yield FunctionResult(ReviewPass(input_obj.packet_id), new_state, "review_pass")


class PMAdvance:
    name = "PMAdvance"
    accepted_input_type = ReviewPass
    reads = ("review_passes",)
    writes = ("advances",)
    input_description = "review pass"
    output_description = "PMAdvanced"
    idempotency = "Advance is keyed by packet ID."

    def apply(self, input_obj: ReviewPass, state: State) -> Iterable[FunctionResult]:
        new_state = state if input_obj.packet_id in state.advances else replace(state, advances=state.advances + (input_obj.packet_id,))
        yield FunctionResult(PMAdvanced(input_obj.packet_id), new_state, "pm_advanced")


def no_advance_from_controller_artifact(state: State, trace) -> InvariantResult:
    del trace
    bad = set(state.controller_artifacts) & set(state.advances)
    if bad:
        return InvariantResult.fail(f"controller-origin evidence advanced: {sorted(bad)!r}")
    return InvariantResult.pass_()


def advance_requires_review_pass(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.advances) - set(state.review_passes)
    if missing:
        return InvariantResult.fail(f"advance without review pass: {sorted(missing)!r}")
    return InvariantResult.pass_()


def result_requires_dispatch(state: State, trace) -> InvariantResult:
    del trace
    result_ids = set(state.worker_results) | set(state.controller_artifacts)
    missing = result_ids - set(state.dispatches)
    if missing:
        return InvariantResult.fail(f"result without reviewer dispatch: {sorted(missing)!r}")
    return InvariantResult.pass_()


def dispatch_requires_controller_reminder(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.dispatches) - set(state.reminder_checked)
    if missing:
        return InvariantResult.fail(f"dispatch without controller reminder check: {sorted(missing)!r}")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "no_advance_from_controller_artifact",
        "Controller-origin implementation evidence cannot advance a route.",
        no_advance_from_controller_artifact,
    ),
    Invariant(
        "advance_requires_review_pass",
        "PM advancement requires reviewer pass.",
        advance_requires_review_pass,
    ),
    Invariant(
        "result_requires_dispatch",
        "No role result exists without reviewer dispatch approval.",
        result_requires_dispatch,
    ),
    Invariant(
        "dispatch_requires_controller_reminder",
        "Reviewer dispatch cannot occur unless the PM reminder to the controller is present.",
        dispatch_requires_controller_reminder,
    ),
)


EXTERNAL_INPUTS = (
    NodeCase("valid_worker_packet", "pass", "worker"),
    NodeCase("controller_origin_packet", "pass", "controller"),
    NodeCase("dispatch_block_packet", "block", "none"),
    NodeCase("missing_reminder_packet", "pass", "worker"),
)


def initial_state() -> State:
    return State()


def terminal_predicate(current_output, state, trace) -> bool:
    del state, trace
    return isinstance(current_output, (PMAdvanced, ReviewBlock, DispatchBlocked))


def build_workflow() -> Workflow:
    return Workflow(
        (
            PMIssuePacket(),
            ControllerReminderCheck(),
            ReviewerDispatch(),
            WorkerOrControllerResult(),
            ReviewerResult(),
            PMAdvance(),
        ),
        name="flowpilot_packet_control_plane",
    )
