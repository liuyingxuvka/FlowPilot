"""FlowGuard model for FlowPilot daemon/Controller prompt boundaries.

Risk Purpose Header:
This FlowGuard model (https://github.com/liuyingxuvka/FlowGuard) reviews
FlowPilot prompt text that tells the foreground assistant who owns progress
after the Router daemon starts. It guards against daemon-mode prompts that
make Controller call `next`, `apply`, or `run-until-wait` as a normal
metronome, heartbeat prompts that resume into a manual router loop, unclear
next-step prompts that fall back to Router commands, and ledger-row prompts
that skip the Controller receipt path. Future agents should run
`python simulations/run_flowpilot_prompt_boundary_checks.py` when editing
FlowPilot launcher, Controller, heartbeat, or generated ledger prompt text.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_DAEMON_LEDGER_PROMPT_SET = "valid_daemon_ledger_prompt_set"
VALID_PRE_DAEMON_BOOTLOADER_PROMPT = "valid_pre_daemon_bootloader_prompt"
VALID_HEARTBEAT_LIVE_DAEMON_RESUME = "valid_heartbeat_live_daemon_resume"
VALID_HEARTBEAT_STALE_DAEMON_REPAIR = "valid_heartbeat_stale_daemon_repair"
VALID_CONTROLLER_LEDGER_RECEIPT_METADATA = "valid_controller_ledger_receipt_metadata"

DAEMON_PROMPT_PREFERS_RUN_UNTIL_WAIT = "daemon_prompt_prefers_run_until_wait"
HEARTBEAT_CONTINUES_ROUTER_LOOP = "heartbeat_continues_router_loop"
UNCLEAR_STEP_RETURNS_TO_ROUTER = "unclear_step_returns_to_router"
ROW_TO_ROW_USES_ROUTER_COMMAND = "row_to_row_uses_router_command"
PARTIAL_TABLE_READ_ERRORS = "partial_table_read_errors"
MISSING_STARTUP_PHASE_SPLIT = "missing_startup_phase_split"
CONTROLLER_LEDGER_METADATA_USES_APPLY = "controller_ledger_metadata_uses_apply"

VALID_SCENARIOS = (
    VALID_DAEMON_LEDGER_PROMPT_SET,
    VALID_PRE_DAEMON_BOOTLOADER_PROMPT,
    VALID_HEARTBEAT_LIVE_DAEMON_RESUME,
    VALID_HEARTBEAT_STALE_DAEMON_REPAIR,
    VALID_CONTROLLER_LEDGER_RECEIPT_METADATA,
)
NEGATIVE_SCENARIOS = (
    DAEMON_PROMPT_PREFERS_RUN_UNTIL_WAIT,
    HEARTBEAT_CONTINUES_ROUTER_LOOP,
    UNCLEAR_STEP_RETURNS_TO_ROUTER,
    ROW_TO_ROW_USES_ROUTER_COMMAND,
    PARTIAL_TABLE_READ_ERRORS,
    MISSING_STARTUP_PHASE_SPLIT,
    CONTROLLER_LEDGER_METADATA_USES_APPLY,
)
SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS

EXPECTED_REJECTIONS = {
    DAEMON_PROMPT_PREFERS_RUN_UNTIL_WAIT: "daemon_mode_manual_router_metronome",
    HEARTBEAT_CONTINUES_ROUTER_LOOP: "resume_prompt_manual_router_loop",
    UNCLEAR_STEP_RETURNS_TO_ROUTER: "unclear_step_router_fallback",
    ROW_TO_ROW_USES_ROUTER_COMMAND: "row_completion_skips_controller_receipt",
    PARTIAL_TABLE_READ_ERRORS: "partial_table_read_not_deferred",
    MISSING_STARTUP_PHASE_SPLIT: "pre_daemon_and_daemon_phases_not_distinguished",
    CONTROLLER_LEDGER_METADATA_USES_APPLY: "controller_ledger_metadata_confuses_apply_with_receipt",
}


@dataclass(frozen=True)
class Tick:
    """One prompt-boundary review tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"
    daemon_started: bool = False
    minimal_run_target_created: bool = False
    pre_daemon_bootloader_manual_allowed: bool = False
    startup_external_work_after_daemon: bool = False
    controller_attaches_to_daemon_status: bool = False
    controller_reads_action_ledger: bool = False
    controller_writes_receipt: bool = False
    controller_standby_when_no_row: bool = False
    router_owns_ordering_and_barriers: bool = False
    diagnostic_router_commands_only: bool = False
    manual_router_metronome_allowed: bool = False
    heartbeat_records_resume_event: bool = False
    heartbeat_attaches_existing_daemon: bool = False
    heartbeat_repairs_stale_daemon_only: bool = False
    heartbeat_continues_router_loop: bool = False
    unclear_step_rereads_daemon_and_ledger: bool = False
    unclear_step_returns_to_router: bool = False
    row_to_row_uses_router_command: bool = False
    partial_table_read_waits_next_tick: bool = False
    partial_table_read_errors: bool = False
    controller_row_metadata_receipt_command: bool = False
    controller_row_metadata_apply_required: bool = False
    controller_row_metadata_preserves_router_apply_intent: bool = False
    rejection_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class PromptBoundaryStep:
    """Model one prompt-boundary transition.

    Input x State -> Set(Output x State)
    reads: selected prompt scenario, startup phase, daemon status, Controller
    ledger wording, heartbeat wording, partial-read wording
    writes: abstract prompt authority decision and accept/reject status
    idempotency: terminal prompt-boundary decisions do not mutate runtime state
    """

    name = "PromptBoundaryStep"
    reads = (
        "scenario",
        "startup_phase",
        "daemon_status_prompt",
        "controller_action_ledger_prompt",
        "heartbeat_resume_prompt",
        "partial_read_prompt",
    )
    writes = ("prompt_boundary_decision",)
    input_description = "prompt boundary review tick"
    output_description = "one abstract prompt-boundary decision"
    idempotency = "terminal prompt decisions are stable and do not schedule work"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def initial_state() -> State:
    return State()


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return

    if state.scenario == "unset":
        for scenario in SCENARIOS:
            yield Transition(
                f"select_{scenario}",
                replace(state, status="running", scenario=scenario),
            )
        return

    if state.scenario == VALID_DAEMON_LEDGER_PROMPT_SET:
        yield Transition(
            f"accept_{VALID_DAEMON_LEDGER_PROMPT_SET}",
            replace(
                state,
                status="accepted",
                daemon_started=True,
                controller_attaches_to_daemon_status=True,
                controller_reads_action_ledger=True,
                controller_writes_receipt=True,
                controller_standby_when_no_row=True,
                router_owns_ordering_and_barriers=True,
                diagnostic_router_commands_only=True,
                partial_table_read_waits_next_tick=True,
            ),
        )
        return

    if state.scenario == VALID_PRE_DAEMON_BOOTLOADER_PROMPT:
        yield Transition(
            f"accept_{VALID_PRE_DAEMON_BOOTLOADER_PROMPT}",
            replace(
                state,
                status="accepted",
                minimal_run_target_created=True,
                pre_daemon_bootloader_manual_allowed=True,
                daemon_started=True,
                startup_external_work_after_daemon=True,
                controller_attaches_to_daemon_status=True,
                controller_reads_action_ledger=True,
                diagnostic_router_commands_only=True,
            ),
        )
        return

    if state.scenario == VALID_HEARTBEAT_LIVE_DAEMON_RESUME:
        yield Transition(
            f"accept_{VALID_HEARTBEAT_LIVE_DAEMON_RESUME}",
            replace(
                state,
                status="accepted",
                daemon_started=True,
                heartbeat_records_resume_event=True,
                heartbeat_attaches_existing_daemon=True,
                controller_attaches_to_daemon_status=True,
                controller_reads_action_ledger=True,
                controller_standby_when_no_row=True,
                diagnostic_router_commands_only=True,
            ),
        )
        return

    if state.scenario == VALID_HEARTBEAT_STALE_DAEMON_REPAIR:
        yield Transition(
            f"accept_{VALID_HEARTBEAT_STALE_DAEMON_REPAIR}",
            replace(
                state,
                status="accepted",
                heartbeat_records_resume_event=True,
                heartbeat_repairs_stale_daemon_only=True,
                controller_attaches_to_daemon_status=True,
                controller_reads_action_ledger=True,
                diagnostic_router_commands_only=True,
            ),
        )
        return

    if state.scenario == VALID_CONTROLLER_LEDGER_RECEIPT_METADATA:
        yield Transition(
            f"accept_{VALID_CONTROLLER_LEDGER_RECEIPT_METADATA}",
            replace(
                state,
                status="accepted",
                daemon_started=True,
                controller_attaches_to_daemon_status=True,
                controller_reads_action_ledger=True,
                controller_writes_receipt=True,
                diagnostic_router_commands_only=True,
                controller_row_metadata_receipt_command=True,
                controller_row_metadata_apply_required=False,
                controller_row_metadata_preserves_router_apply_intent=True,
            ),
        )
        return

    if state.scenario in EXPECTED_REJECTIONS:
        updates = {"status": "rejected", "rejection_reason": EXPECTED_REJECTIONS[state.scenario]}
        if state.scenario == DAEMON_PROMPT_PREFERS_RUN_UNTIL_WAIT:
            updates.update(daemon_started=True, manual_router_metronome_allowed=True)
        elif state.scenario == HEARTBEAT_CONTINUES_ROUTER_LOOP:
            updates.update(daemon_started=True, heartbeat_records_resume_event=True, heartbeat_continues_router_loop=True)
        elif state.scenario == UNCLEAR_STEP_RETURNS_TO_ROUTER:
            updates.update(daemon_started=True, unclear_step_returns_to_router=True)
        elif state.scenario == ROW_TO_ROW_USES_ROUTER_COMMAND:
            updates.update(daemon_started=True, controller_reads_action_ledger=True, row_to_row_uses_router_command=True)
        elif state.scenario == PARTIAL_TABLE_READ_ERRORS:
            updates.update(daemon_started=True, partial_table_read_errors=True)
        elif state.scenario == MISSING_STARTUP_PHASE_SPLIT:
            updates.update(startup_external_work_after_daemon=True)
        elif state.scenario == CONTROLLER_LEDGER_METADATA_USES_APPLY:
            updates.update(
                daemon_started=True,
                controller_reads_action_ledger=True,
                controller_row_metadata_apply_required=True,
                controller_row_metadata_receipt_command=False,
            )
        yield Transition(f"reject_{state.scenario}", replace(state, **updates))
        return


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return is_terminal(state) and not invariant_failures(state)


def terminal_predicate(_input_obj, state: State, _trace) -> bool:
    return is_terminal(state)


def accepted_daemon_prompts_have_ledger_path(state: State, _trace) -> InvariantResult:
    if state.status == "accepted" and state.daemon_started:
        if not state.controller_attaches_to_daemon_status:
            return InvariantResult.fail("accepted daemon prompt does not attach Controller to daemon status")
        if not state.controller_reads_action_ledger:
            return InvariantResult.fail("accepted daemon prompt does not read the Controller action ledger")
        if state.manual_router_metronome_allowed:
            return InvariantResult.fail("accepted daemon prompt allows manual Router metronome")
    return InvariantResult.pass_()


def accepted_row_prompts_use_receipts_not_router_commands(state: State, _trace) -> InvariantResult:
    if state.status == "accepted" and state.scenario == VALID_DAEMON_LEDGER_PROMPT_SET:
        if not state.controller_writes_receipt:
            return InvariantResult.fail("accepted ledger prompt lacks Controller receipt path")
        if state.row_to_row_uses_router_command:
            return InvariantResult.fail("accepted ledger prompt uses Router command between rows")
    return InvariantResult.pass_()


def accepted_resume_prompts_do_not_continue_router_loop(state: State, _trace) -> InvariantResult:
    if state.status == "accepted" and state.scenario in {
        VALID_HEARTBEAT_LIVE_DAEMON_RESUME,
        VALID_HEARTBEAT_STALE_DAEMON_REPAIR,
    }:
        if not state.heartbeat_records_resume_event:
            return InvariantResult.fail("accepted heartbeat prompt does not record resume event")
        if state.heartbeat_continues_router_loop:
            return InvariantResult.fail("accepted heartbeat prompt continues a manual router loop")
    return InvariantResult.pass_()


def accepted_startup_prompts_split_pre_daemon_and_daemon(state: State, _trace) -> InvariantResult:
    if state.status == "accepted" and state.scenario == VALID_PRE_DAEMON_BOOTLOADER_PROMPT:
        if not (
            state.minimal_run_target_created
            and state.pre_daemon_bootloader_manual_allowed
            and state.daemon_started
            and state.startup_external_work_after_daemon
        ):
            return InvariantResult.fail("accepted startup prompt does not split minimal bootloader from daemon-owned startup")
    return InvariantResult.pass_()


def accepted_prompts_defer_partial_table_reads(state: State, _trace) -> InvariantResult:
    if state.status == "accepted" and state.daemon_started:
        if state.partial_table_read_errors:
            return InvariantResult.fail("accepted prompt treats partial table read as error")
    return InvariantResult.pass_()


def accepted_controller_ledger_metadata_uses_receipt_projection(state: State, _trace) -> InvariantResult:
    if state.status == "accepted" and state.scenario == VALID_CONTROLLER_LEDGER_RECEIPT_METADATA:
        if not state.controller_row_metadata_receipt_command:
            return InvariantResult.fail("accepted Controller row metadata lacks controller-receipt command")
        if state.controller_row_metadata_apply_required:
            return InvariantResult.fail("accepted Controller row metadata still exposes apply_required as row completion")
        if not state.controller_row_metadata_preserves_router_apply_intent:
            return InvariantResult.fail("accepted Controller row metadata loses original Router apply intent")
    return InvariantResult.pass_()


def negative_scenarios_rejected(state: State, _trace) -> InvariantResult:
    if state.scenario in NEGATIVE_SCENARIOS and state.status == "accepted":
        return InvariantResult.fail(f"known-bad prompt scenario was accepted: {state.scenario}")
    return InvariantResult.pass_()


def terminal_decisions_are_explicit(state: State, _trace) -> InvariantResult:
    if state.status == "rejected" and state.rejection_reason == "none":
        return InvariantResult.fail("rejected prompt scenario lacks rejection reason")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepted_daemon_prompts_have_ledger_path",
        description="Daemon-mode prompts attach Controller to daemon status and Controller action ledger.",
        predicate=accepted_daemon_prompts_have_ledger_path,
    ),
    Invariant(
        name="accepted_row_prompts_use_receipts_not_router_commands",
        description="Controller ledger rows complete through row execution and Controller receipts, not Router commands between rows.",
        predicate=accepted_row_prompts_use_receipts_not_router_commands,
    ),
    Invariant(
        name="accepted_resume_prompts_do_not_continue_router_loop",
        description="Heartbeat/manual resume prompts attach to daemon state instead of continuing a manual router loop.",
        predicate=accepted_resume_prompts_do_not_continue_router_loop,
    ),
    Invariant(
        name="accepted_startup_prompts_split_pre_daemon_and_daemon",
        description="Startup prompts separate minimal pre-daemon bootloader actions from daemon-owned startup rows.",
        predicate=accepted_startup_prompts_split_pre_daemon_and_daemon,
    ),
    Invariant(
        name="accepted_prompts_defer_partial_table_reads",
        description="Prompts defer partial table reads to the next tick instead of treating them as corruption.",
        predicate=accepted_prompts_defer_partial_table_reads,
    ),
    Invariant(
        name="accepted_controller_ledger_metadata_uses_receipt_projection",
        description="Controller ledger row metadata exposes receipt completion while preserving original Router apply intent separately.",
        predicate=accepted_controller_ledger_metadata_uses_receipt_projection,
    ),
    Invariant(
        name="negative_scenarios_rejected",
        description="Known-bad prompt authority scenarios are rejected.",
        predicate=negative_scenarios_rejected,
    ),
    Invariant(
        name="terminal_decisions_are_explicit",
        description="Terminal prompt-boundary states record explicit accept/reject decisions.",
        predicate=terminal_decisions_are_explicit,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3
REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in SCENARIOS]
    + [f"accept_{scenario}" for scenario in VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in NEGATIVE_SCENARIOS]
)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def build_workflow() -> Workflow:
    return Workflow((PromptBoundaryStep(),), name="flowpilot_prompt_boundary")
