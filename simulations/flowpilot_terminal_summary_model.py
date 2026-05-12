"""FlowGuard model for FlowPilot terminal summary generation.

Risk purpose:
- This model uses FlowGuard (https://github.com/liuyingxuvka/FlowGuard) to
  review the final FlowPilot receipt flow.
- It guards against terminal runs exiting without a saved summary, Controller
  reading all run files before the run is terminal, missing FlowPilot GitHub
  attribution, unregistered summaries, repeated terminal-summary loops, and
  Controller using summary mode to mutate route/gate/project state.
- Future agents should run this model whenever terminal lifecycle, summary,
  run-index, or Controller read authority behavior changes.
- Companion command:
  `python simulations\run_flowpilot_terminal_summary_checks.py --json-out simulations\flowpilot_terminal_summary_results.json`

Risk intent brief:
- Prevent a completed, stopped, cancelled, or handoff-blocked FlowPilot run from
  losing its human-readable history receipt.
- Protect prompt isolation during normal work by granting all-files read only
  after Router has already reached a terminal run mode.
- Keep the final summary a simple terminal receipt, not a PM/reviewer gate or a
  route-progress authority.
- Preserve the discoverability requirement that saved summaries start with the
  FlowPilot GitHub link.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


TERMINAL_MODES = {
    "closed",
    "stopped_by_user",
    "cancelled_by_user",
    "blocked_handoff",
}


@dataclass(frozen=True)
class Tick:
    """One Router/Controller terminal-summary decision."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    terminal_mode: str = "none"
    router_terminal_mode_known: bool = False
    terminal_summary_card_delivered: bool = False
    terminal_read_all_run_files_authorized: bool = False
    controller_read_current_run_root_all_files: bool = False
    controller_read_outside_current_run_root: bool = False
    summary_displayed_to_user: bool = False
    summary_markdown_written: bool = False
    summary_json_written: bool = False
    summary_attribution_first_line: bool = False
    summary_registered_in_index: bool = False
    summary_display_matches_saved_content: bool = False
    terminal_lifecycle_observed: bool = False
    terminal_summary_requested_again: bool = False
    controller_continued_route_work: bool = False
    controller_approved_or_reopened_gate: bool = False
    controller_originated_project_evidence: bool = False
    controller_wrote_non_summary_file: bool = False


class Transition(NamedTuple):
    label: str
    state: State


class TerminalSummaryStep:
    """Model one terminal summary router action.

    Input x State -> Set(Output x State)
    reads: terminal lifecycle status, current run root, summary/index state
    writes: one terminal summary fact or final terminal observation
    idempotency: once the summary is written and registered, later ticks only
    observe terminal lifecycle and do not request another summary.
    """

    name = "TerminalSummaryStep"
    input_description = "terminal summary router tick"
    output_description = "one abstract terminal summary action"
    reads = ("terminal_lifecycle", "current_run_root", "final_summary_state")
    writes = ("terminal_summary_receipt", "run_index_summary_pointer")
    idempotency = "terminal summary is written once before terminal observation"

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


def _summary_complete(state: State) -> bool:
    return (
        state.summary_displayed_to_user
        and state.summary_markdown_written
        and state.summary_json_written
        and state.summary_attribution_first_line
        and state.summary_registered_in_index
        and state.summary_display_matches_saved_content
    )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.terminal_lifecycle_observed:
        return
    if state.terminal_mode == "none":
        for mode in sorted(TERMINAL_MODES):
            yield Transition(
                f"router_detects_terminal_mode_{mode}",
                replace(state, terminal_mode=mode, router_terminal_mode_known=True),
            )
        return
    if not state.terminal_summary_card_delivered:
        yield Transition(
            "router_delivers_terminal_summary_card",
            replace(
                state,
                terminal_summary_card_delivered=True,
                terminal_read_all_run_files_authorized=True,
            ),
        )
        return
    if not state.controller_read_current_run_root_all_files:
        yield Transition(
            "controller_reads_current_run_root_all_files",
            replace(state, controller_read_current_run_root_all_files=True),
        )
        return
    if not _summary_complete(state):
        yield Transition(
            "controller_writes_and_displays_terminal_summary",
            replace(
                state,
                summary_displayed_to_user=True,
                summary_markdown_written=True,
                summary_json_written=True,
                summary_attribution_first_line=True,
                summary_registered_in_index=True,
                summary_display_matches_saved_content=True,
            ),
        )
        return
    yield Transition(
        "router_observes_terminal_lifecycle_after_summary",
        replace(state, terminal_lifecycle_observed=True),
    )


def next_states(input_obj: Tick, state: State) -> Iterable[FunctionResult]:
    yield from TerminalSummaryStep().apply(input_obj, state)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.terminal_mode != "none" and state.terminal_mode not in TERMINAL_MODES:
        failures.append("unknown terminal summary mode")
    if state.router_terminal_mode_known and state.terminal_mode == "none":
        failures.append("Router marked terminal mode known without a terminal mode")
    if state.terminal_summary_card_delivered and not state.router_terminal_mode_known:
        failures.append("terminal summary card delivered before Router knew terminal mode")
    if state.terminal_read_all_run_files_authorized and not state.terminal_summary_card_delivered:
        failures.append("read-all-run-files authority existed without terminal summary card")
    if (
        state.controller_read_current_run_root_all_files
        and not state.terminal_read_all_run_files_authorized
    ):
        failures.append("Controller read all run files before terminal summary authorization")
    if state.controller_read_current_run_root_all_files and state.terminal_mode == "none":
        failures.append("Controller read all run files before run was terminal")
    if state.controller_read_outside_current_run_root:
        failures.append("Controller read outside current run root during terminal summary")
    if state.summary_markdown_written and not state.summary_attribution_first_line:
        failures.append("final summary markdown missing first-line FlowPilot GitHub attribution")
    if state.summary_registered_in_index and not state.summary_markdown_written:
        failures.append("index registered a final summary before markdown was written")
    if state.summary_json_written and not state.summary_markdown_written:
        failures.append("summary JSON written before summary markdown")
    if state.summary_display_matches_saved_content and not (
        state.summary_displayed_to_user and state.summary_markdown_written
    ):
        failures.append("summary display/content match recorded before display and saved markdown")
    if state.terminal_lifecycle_observed and not _summary_complete(state):
        failures.append("terminal lifecycle observed before final summary was saved and registered")
    if state.terminal_summary_requested_again and _summary_complete(state):
        failures.append("terminal summary requested again after summary was already complete")
    if state.controller_continued_route_work:
        failures.append("Controller continued route work in terminal summary mode")
    if state.controller_approved_or_reopened_gate:
        failures.append("Controller approved or reopened a gate in terminal summary mode")
    if state.controller_originated_project_evidence:
        failures.append("Controller originated project evidence in terminal summary mode")
    if state.controller_wrote_non_summary_file:
        failures.append("Controller wrote non-summary files in terminal summary mode")
    return failures


def terminal_summary_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_terminal_summary_receipt",
        description=(
            "A terminal FlowPilot run must receive a terminal summary card, "
            "Controller may read all current-run files only after that card, "
            "the saved markdown must start with the FlowPilot GitHub link, "
            "the JSON and index pointers must be written, the user-visible "
            "summary must match the saved receipt, and Controller must not use "
            "summary mode to continue route work or approve gates."
        ),
        predicate=terminal_summary_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 8


def build_workflow() -> Workflow:
    return Workflow((TerminalSummaryStep(),), name="flowpilot_terminal_summary")


def is_terminal(state: State) -> bool:
    return state.terminal_lifecycle_observed


def is_success(state: State) -> bool:
    return state.terminal_lifecycle_observed and _summary_complete(state)


def _terminal_ready(**changes: object) -> State:
    return replace(
        State(
            terminal_mode="closed",
            router_terminal_mode_known=True,
            terminal_summary_card_delivered=True,
            terminal_read_all_run_files_authorized=True,
            controller_read_current_run_root_all_files=True,
            summary_displayed_to_user=True,
            summary_markdown_written=True,
            summary_json_written=True,
            summary_attribution_first_line=True,
            summary_registered_in_index=True,
            summary_display_matches_saved_content=True,
        ),
        **changes,
    )


def hazard_states() -> dict[str, State]:
    return {
        "terminal_lifecycle_without_summary": State(
            terminal_mode="closed",
            router_terminal_mode_known=True,
            terminal_lifecycle_observed=True,
        ),
        "summary_card_before_terminal_mode": State(
            terminal_summary_card_delivered=True,
            terminal_read_all_run_files_authorized=True,
        ),
        "read_all_files_without_summary_card": State(
            terminal_mode="closed",
            router_terminal_mode_known=True,
            controller_read_current_run_root_all_files=True,
        ),
        "read_all_files_before_terminal": State(
            terminal_summary_card_delivered=True,
            terminal_read_all_run_files_authorized=True,
            controller_read_current_run_root_all_files=True,
        ),
        "controller_reads_outside_run_root": _terminal_ready(
            controller_read_outside_current_run_root=True,
        ),
        "summary_missing_flowpilot_attribution": _terminal_ready(
            summary_attribution_first_line=False,
        ),
        "summary_not_registered_in_index": _terminal_ready(
            summary_registered_in_index=False,
            terminal_lifecycle_observed=True,
        ),
        "summary_display_does_not_match_saved_content": _terminal_ready(
            summary_display_matches_saved_content=False,
            terminal_lifecycle_observed=True,
        ),
        "summary_requested_again_after_complete": _terminal_ready(
            terminal_summary_requested_again=True,
        ),
        "controller_continues_route_work_after_summary": _terminal_ready(
            controller_continued_route_work=True,
        ),
        "controller_approves_gate_after_summary": _terminal_ready(
            controller_approved_or_reopened_gate=True,
        ),
        "controller_originates_project_evidence_after_summary": _terminal_ready(
            controller_originated_project_evidence=True,
        ),
        "controller_writes_non_summary_file_after_summary": _terminal_ready(
            controller_wrote_non_summary_file=True,
        ),
        "stopped_run_without_summary": State(
            terminal_mode="stopped_by_user",
            router_terminal_mode_known=True,
            terminal_lifecycle_observed=True,
        ),
        "cancelled_run_without_summary": State(
            terminal_mode="cancelled_by_user",
            router_terminal_mode_known=True,
            terminal_lifecycle_observed=True,
        ),
        "blocked_handoff_without_summary": State(
            terminal_mode="blocked_handoff",
            router_terminal_mode_known=True,
            terminal_lifecycle_observed=True,
        ),
    }


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "Action",
    "State",
    "TerminalSummaryStep",
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
    "terminal_summary_invariant",
]
