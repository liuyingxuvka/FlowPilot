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
class HeartbeatCase:
    case_id: str


@dataclass(frozen=True)
class NodePacket:
    packet_id: str
    allowed_origin: str = "worker"
    has_controller_reminder: bool = True


@dataclass(frozen=True)
class ResumeRequest:
    packet_id: str
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
    heartbeat_loads: tuple[str, ...] = ()
    heartbeat_state_blocks: tuple[str, ...] = ()
    heartbeat_ambiguous_blocks: tuple[str, ...] = ()
    pm_resume_requests: tuple[str, ...] = ()
    resume_packets: tuple[str, ...] = ()
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
    accepted_input_type = (NodeCase, HeartbeatCase)
    reads = ("packets",)
    writes = ("packets",)
    input_description = "node case selected by PM route loop"
    output_description = "PM-authored packet"
    idempotency = "Packet IDs are issued once."

    def apply(self, input_obj: NodeCase, state: State) -> Iterable[FunctionResult]:
        if not isinstance(input_obj, NodeCase):
            yield FunctionResult(input_obj, state, "pm_issue_pass_through")
            return
        new_state = state if input_obj.case_id in state.packets else replace(state, packets=state.packets + (input_obj.case_id,))
        has_reminder = not input_obj.case_id.startswith("missing_reminder")
        yield FunctionResult(NodePacket(input_obj.case_id, has_controller_reminder=has_reminder), new_state, "pm_packet_issued")


class HeartbeatResumeLoad:
    name = "HeartbeatResumeLoad"
    accepted_input_type = (HeartbeatCase, NodePacket)
    reads = ("packets", "dispatches", "worker_results")
    writes = (
        "heartbeat_loads",
        "heartbeat_state_blocks",
        "heartbeat_ambiguous_blocks",
        "reminder_checked",
        "dispatches",
        "worker_results",
    )
    input_description = "heartbeat wakeup case"
    output_description = "resume request, pending worker result, or blocked recovery"
    idempotency = "Heartbeat state load is keyed by packet ID."

    def apply(self, input_obj: HeartbeatCase, state: State) -> Iterable[FunctionResult]:
        if not isinstance(input_obj, HeartbeatCase):
            yield FunctionResult(input_obj, state, "heartbeat_load_pass_through")
            return
        packet_id = input_obj.case_id
        if packet_id.startswith("heartbeat_missing_state"):
            new_state = replace(state, heartbeat_state_blocks=state.heartbeat_state_blocks + (packet_id,))
            yield FunctionResult(DispatchBlocked(packet_id, "missing_current_run_state"), new_state, "heartbeat_missing_state_blocked")
            return
        if packet_id.startswith("heartbeat_ambiguous_worker_state"):
            new_state = replace(state, heartbeat_ambiguous_blocks=state.heartbeat_ambiguous_blocks + (packet_id,))
            yield FunctionResult(
                DispatchBlocked(packet_id, "ambiguous_worker_state_requires_pm_reissue"),
                new_state,
                "heartbeat_ambiguous_worker_blocked",
            )
            return
        if packet_id.startswith("heartbeat_worker_result_pending_review"):
            new_state = replace(
                state,
                heartbeat_loads=state.heartbeat_loads + (packet_id,),
                reminder_checked=state.reminder_checked + (packet_id,),
                dispatches=state.dispatches + (packet_id,),
                worker_results=state.worker_results + (packet_id,),
            )
            yield FunctionResult(NodeResult(packet_id, "worker"), new_state, "heartbeat_loaded_worker_result_for_review")
            return

        has_reminder = not packet_id.startswith("heartbeat_missing_reminder")
        new_state = state if packet_id in state.heartbeat_loads else replace(state, heartbeat_loads=state.heartbeat_loads + (packet_id,))
        yield FunctionResult(ResumeRequest(packet_id, has_controller_reminder=has_reminder), new_state, "heartbeat_state_loaded")


class ControllerAskPMOnResume:
    name = "ControllerAskPMOnResume"
    accepted_input_type = (ResumeRequest, NodePacket, NodeResult)
    reads = ("heartbeat_loads",)
    writes = ("pm_resume_requests",)
    input_description = "loaded heartbeat state requiring PM decision"
    output_description = "PM resume decision request"
    idempotency = "PM resume requests are keyed by packet ID."

    def apply(self, input_obj: ResumeRequest, state: State) -> Iterable[FunctionResult]:
        if not isinstance(input_obj, ResumeRequest):
            yield FunctionResult(input_obj, state, "heartbeat_ask_pm_pass_through")
            return
        new_state = state if input_obj.packet_id in state.pm_resume_requests else replace(
            state,
            pm_resume_requests=state.pm_resume_requests + (input_obj.packet_id,),
        )
        yield FunctionResult(input_obj, new_state, "heartbeat_resume_pm_requested")


class PMResumeDecision:
    name = "PMResumeDecision"
    accepted_input_type = (ResumeRequest, NodePacket, NodeResult)
    reads = ("pm_resume_requests",)
    writes = ("packets", "resume_packets")
    input_description = "PM decision requested by heartbeat resume"
    output_description = "PM-authored resume packet"
    idempotency = "PM resume packets are keyed by packet ID."

    def apply(self, input_obj: ResumeRequest, state: State) -> Iterable[FunctionResult]:
        if not isinstance(input_obj, ResumeRequest):
            yield FunctionResult(input_obj, state, "heartbeat_pm_decision_pass_through")
            return
        new_packets = state.packets if input_obj.packet_id in state.packets else state.packets + (input_obj.packet_id,)
        new_resume_packets = (
            state.resume_packets if input_obj.packet_id in state.resume_packets else state.resume_packets + (input_obj.packet_id,)
        )
        new_state = replace(state, packets=new_packets, resume_packets=new_resume_packets)
        label = "heartbeat_pm_packet_issued" if input_obj.has_controller_reminder else "heartbeat_pm_missing_controller_reminder"
        yield FunctionResult(
            NodePacket(input_obj.packet_id, has_controller_reminder=input_obj.has_controller_reminder),
            new_state,
            label,
        )


class ControllerReminderCheck:
    name = "ControllerReminderCheck"
    accepted_input_type = (NodePacket, NodeResult)
    reads = ("packets",)
    writes = ("reminder_checked", "reminder_blocks")
    input_description = "PM packet with required controller reminder"
    output_description = "NodePacket or DispatchBlocked"
    idempotency = "Reminder check is keyed by packet ID."

    def apply(self, input_obj: NodePacket, state: State) -> Iterable[FunctionResult]:
        if not isinstance(input_obj, NodePacket):
            yield FunctionResult(input_obj, state, "controller_reminder_pass_through")
            return
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
    accepted_input_type = (NodePacket, NodeResult)
    reads = ("packets",)
    writes = ("dispatches", "review_blocks")
    input_description = "PM packet"
    output_description = "ApprovedPacket or DispatchBlocked"
    idempotency = "Dispatch approval is keyed by packet ID."

    def apply(self, input_obj: NodePacket, state: State) -> Iterable[FunctionResult]:
        if not isinstance(input_obj, NodePacket):
            yield FunctionResult(input_obj, state, "reviewer_dispatch_pass_through")
            return
        # The case id encodes the abstract reviewer dispatch decision for finite exploration.
        if input_obj.packet_id.startswith("dispatch_block"):
            new_state = replace(state, review_blocks=state.review_blocks + (input_obj.packet_id,))
            yield FunctionResult(DispatchBlocked(input_obj.packet_id, "reviewer_dispatch_block"), new_state, "reviewer_dispatch_blocked")
            return
        new_state = state if input_obj.packet_id in state.dispatches else replace(state, dispatches=state.dispatches + (input_obj.packet_id,))
        yield FunctionResult(ApprovedPacket(input_obj.packet_id, input_obj.allowed_origin), new_state, "reviewer_dispatch_approved")


class WorkerOrControllerResult:
    name = "WorkerOrControllerResult"
    accepted_input_type = (ApprovedPacket, NodeResult)
    reads = ("dispatches",)
    writes = ("worker_results", "controller_artifacts")
    input_description = "dispatch-approved packet"
    output_description = "node result with origin"
    idempotency = "Node result is keyed by packet ID."

    def apply(self, input_obj: ApprovedPacket, state: State) -> Iterable[FunctionResult]:
        if not isinstance(input_obj, ApprovedPacket):
            yield FunctionResult(input_obj, state, "worker_result_pass_through")
            return
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


def heartbeat_resume_packet_requires_pm_request(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.resume_packets) - set(state.pm_resume_requests)
    if missing:
        return InvariantResult.fail(f"heartbeat resume packet without PM request: {sorted(missing)!r}")
    return InvariantResult.pass_()


def heartbeat_resume_packet_requires_loaded_state(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.resume_packets) - set(state.heartbeat_loads)
    if missing:
        return InvariantResult.fail(f"heartbeat resume packet without loaded state: {sorted(missing)!r}")
    return InvariantResult.pass_()


def ambiguous_worker_state_never_advances(state: State, trace) -> InvariantResult:
    del trace
    blocked = set(state.heartbeat_ambiguous_blocks)
    unsafe = blocked & (set(state.dispatches) | set(state.worker_results) | set(state.review_passes) | set(state.advances))
    if unsafe:
        return InvariantResult.fail(f"ambiguous worker state advanced or dispatched: {sorted(unsafe)!r}")
    return InvariantResult.pass_()


def missing_heartbeat_state_never_advances(state: State, trace) -> InvariantResult:
    del trace
    blocked = set(state.heartbeat_state_blocks)
    unsafe = blocked & (set(state.dispatches) | set(state.worker_results) | set(state.review_passes) | set(state.advances))
    if unsafe:
        return InvariantResult.fail(f"missing heartbeat state advanced or dispatched: {sorted(unsafe)!r}")
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
    Invariant(
        "heartbeat_resume_packet_requires_pm_request",
        "Heartbeat cannot mint a resume packet without first asking PM.",
        heartbeat_resume_packet_requires_pm_request,
    ),
    Invariant(
        "heartbeat_resume_packet_requires_loaded_state",
        "Heartbeat resume packets require loaded current-run state.",
        heartbeat_resume_packet_requires_loaded_state,
    ),
    Invariant(
        "ambiguous_worker_state_never_advances",
        "Ambiguous worker state blocks controller execution.",
        ambiguous_worker_state_never_advances,
    ),
    Invariant(
        "missing_heartbeat_state_never_advances",
        "Missing current-run state blocks heartbeat execution.",
        missing_heartbeat_state_never_advances,
    ),
)


EXTERNAL_INPUTS = (
    NodeCase("valid_worker_packet", "pass", "worker"),
    NodeCase("controller_origin_packet", "pass", "controller"),
    NodeCase("dispatch_block_packet", "block", "none"),
    NodeCase("missing_reminder_packet", "pass", "worker"),
    HeartbeatCase("heartbeat_valid_packet"),
    HeartbeatCase("heartbeat_missing_state"),
    HeartbeatCase("heartbeat_ambiguous_worker_state"),
    HeartbeatCase("heartbeat_worker_result_pending_review"),
    HeartbeatCase("heartbeat_missing_reminder"),
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
            HeartbeatResumeLoad(),
            ControllerAskPMOnResume(),
            PMResumeDecision(),
            ControllerReminderCheck(),
            ReviewerDispatch(),
            WorkerOrControllerResult(),
            ReviewerResult(),
            PMAdvance(),
        ),
        name="flowpilot_packet_control_plane",
    )
