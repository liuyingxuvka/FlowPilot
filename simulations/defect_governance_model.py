"""FlowGuard model for FlowPilot defect and evidence governance.

Risk intent: blocking findings, invalid evidence, and controlled pauses must be
first-class run state. A project cannot advance or complete merely because an
implementation was patched; fixed blockers need same-class recheck evidence,
and fixture/invalid/stale evidence must be disclosed instead of overwritten.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple


@dataclass(frozen=True)
class State:
    run_started: bool = False
    defect_ledger_initialized: bool = False
    evidence_ledger_initialized: bool = False
    skill_improvement_live_report_initialized: bool = False
    reviewer_blocker_found: bool = False
    defect_event_logged: bool = False
    pm_triaged_defect: bool = False
    blocker_open: bool = False
    repair_recorded: bool = False
    fixed_pending_recheck: bool = False
    same_class_recheck_passed: bool = False
    defect_closed_by_pm: bool = False
    invalid_evidence_seen: bool = False
    evidence_registered: bool = False
    evidence_classified: bool = False
    replacement_evidence_linked: bool = False
    fixture_evidence_disclosed: bool = False
    flowpilot_skill_issue_observed: bool = False
    skill_issue_live_report_updated: bool = False
    pause_requested: bool = False
    heartbeat_reconciled: bool = False
    pause_snapshot_written: bool = False
    terminal_completion_started: bool = False
    terminal_completion_allowed: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def next_safe_states(state: State) -> Iterable[Transition]:
    if not state.run_started:
        yield Transition("run_started", replace(state, run_started=True))
        return
    if not state.defect_ledger_initialized:
        yield Transition(
            "defect_ledger_initialized",
            replace(state, defect_ledger_initialized=True),
        )
        return
    if not state.evidence_ledger_initialized:
        yield Transition(
            "evidence_ledger_initialized",
            replace(state, evidence_ledger_initialized=True),
        )
        return
    if not state.skill_improvement_live_report_initialized:
        yield Transition(
            "skill_improvement_live_report_initialized",
            replace(state, skill_improvement_live_report_initialized=True),
        )
        return
    if not state.reviewer_blocker_found:
        yield Transition(
            "reviewer_blocker_found",
            replace(state, reviewer_blocker_found=True),
        )
        return
    if state.reviewer_blocker_found and not state.defect_event_logged:
        yield Transition(
            "defect_event_logged_by_discovering_role",
            replace(state, defect_event_logged=True, blocker_open=True),
        )
        return
    if state.blocker_open and not state.pm_triaged_defect:
        yield Transition(
            "pm_triaged_blocking_defect",
            replace(state, pm_triaged_defect=True),
        )
        return
    if state.blocker_open and state.pm_triaged_defect and not state.repair_recorded:
        yield Transition(
            "repair_recorded_fixed_pending_recheck",
            replace(
                state,
                blocker_open=False,
                repair_recorded=True,
                fixed_pending_recheck=True,
            ),
        )
        return
    if state.fixed_pending_recheck and not state.same_class_recheck_passed:
        yield Transition(
            "same_class_recheck_passed",
            replace(state, same_class_recheck_passed=True),
        )
        return
    if state.same_class_recheck_passed and not state.defect_closed_by_pm:
        yield Transition(
            "pm_closed_rechecked_defect",
            replace(state, fixed_pending_recheck=False, defect_closed_by_pm=True),
        )
        return
    if not state.invalid_evidence_seen:
        yield Transition(
            "invalid_parallel_screenshot_seen",
            replace(state, invalid_evidence_seen=True),
        )
        return
    if state.invalid_evidence_seen and not state.evidence_registered:
        yield Transition(
            "invalid_evidence_registered",
            replace(state, evidence_registered=True),
        )
        return
    if state.evidence_registered and not state.evidence_classified:
        yield Transition(
            "evidence_status_and_source_classified",
            replace(state, evidence_classified=True),
        )
        return
    if state.evidence_classified and not state.replacement_evidence_linked:
        yield Transition(
            "replacement_evidence_linked",
            replace(state, replacement_evidence_linked=True),
        )
        return
    if state.replacement_evidence_linked and not state.fixture_evidence_disclosed:
        yield Transition(
            "fixture_evidence_disclosed_separately",
            replace(state, fixture_evidence_disclosed=True),
        )
        return
    if not state.flowpilot_skill_issue_observed:
        yield Transition(
            "flowpilot_skill_issue_observed",
            replace(state, flowpilot_skill_issue_observed=True),
        )
        return
    if state.flowpilot_skill_issue_observed and not state.skill_issue_live_report_updated:
        yield Transition(
            "skill_issue_live_report_updated",
            replace(state, skill_issue_live_report_updated=True),
        )
        return
    if not state.pause_requested:
        yield Transition("pause_requested", replace(state, pause_requested=True))
        return
    if state.pause_requested and not state.heartbeat_reconciled:
        yield Transition(
            "heartbeat_lifecycle_reconciled_for_pause",
            replace(state, heartbeat_reconciled=True),
        )
        return
    if state.heartbeat_reconciled and not state.pause_snapshot_written:
        yield Transition(
            "pause_snapshot_written",
            replace(state, pause_snapshot_written=True),
        )
        return
    if not state.terminal_completion_started:
        yield Transition(
            "terminal_completion_started",
            replace(state, terminal_completion_started=True),
        )
        return
    if not state.terminal_completion_allowed:
        yield Transition(
            "terminal_completion_allowed",
            replace(state, terminal_completion_allowed=True),
        )


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if (state.reviewer_blocker_found or state.blocker_open) and not state.defect_ledger_initialized:
        failures.append("blocking finding happened before defect ledger initialization")
    if state.reviewer_blocker_found and state.pm_triaged_defect and not state.defect_event_logged:
        failures.append("PM triaged a blocker before the discovering role logged a defect event")
    if state.repair_recorded and not (state.defect_event_logged and state.pm_triaged_defect):
        failures.append("repair was recorded before defect event and PM triage")
    if state.defect_closed_by_pm and not (
        state.repair_recorded and state.same_class_recheck_passed
    ):
        failures.append("PM closed a blocker before repair and same-class recheck")
    if state.terminal_completion_allowed and (
        state.blocker_open or state.fixed_pending_recheck
    ):
        failures.append("terminal completion allowed with open blocker or pending recheck")
    if state.invalid_evidence_seen and not state.evidence_ledger_initialized:
        failures.append("invalid evidence appeared before evidence ledger initialization")
    if state.terminal_completion_allowed and state.invalid_evidence_seen and not (
        state.evidence_registered
        and state.evidence_classified
        and state.replacement_evidence_linked
        and state.fixture_evidence_disclosed
    ):
        failures.append("terminal completion allowed before invalid/stale/fixture evidence was classified")
    if state.flowpilot_skill_issue_observed and not state.skill_issue_live_report_updated:
        if state.pause_snapshot_written or state.terminal_completion_allowed:
            failures.append("FlowPilot skill issue was not written to live report before pause or completion")
    if state.pause_requested and state.pause_snapshot_written and not state.heartbeat_reconciled:
        failures.append("pause snapshot was written before heartbeat lifecycle reconciliation")
    if state.pause_requested and state.terminal_completion_allowed and not state.pause_snapshot_written:
        failures.append("terminal completion or restart path skipped pause snapshot after pause request")
    return failures


def hazard_states() -> dict[str, State]:
    return {
        "blocker_never_logged": State(
            run_started=True,
            defect_ledger_initialized=True,
            evidence_ledger_initialized=True,
            skill_improvement_live_report_initialized=True,
            reviewer_blocker_found=True,
            pm_triaged_defect=True,
        ),
        "closed_without_recheck": State(
            run_started=True,
            defect_ledger_initialized=True,
            evidence_ledger_initialized=True,
            skill_improvement_live_report_initialized=True,
            reviewer_blocker_found=True,
            defect_event_logged=True,
            pm_triaged_defect=True,
            repair_recorded=True,
            defect_closed_by_pm=True,
        ),
        "terminal_with_pending_recheck": State(
            run_started=True,
            defect_ledger_initialized=True,
            evidence_ledger_initialized=True,
            skill_improvement_live_report_initialized=True,
            defect_event_logged=True,
            pm_triaged_defect=True,
            repair_recorded=True,
            fixed_pending_recheck=True,
            terminal_completion_started=True,
            terminal_completion_allowed=True,
        ),
        "invalid_evidence_overwritten": State(
            run_started=True,
            defect_ledger_initialized=True,
            evidence_ledger_initialized=True,
            skill_improvement_live_report_initialized=True,
            invalid_evidence_seen=True,
            terminal_completion_started=True,
            terminal_completion_allowed=True,
        ),
        "pause_without_snapshot": State(
            run_started=True,
            defect_ledger_initialized=True,
            evidence_ledger_initialized=True,
            skill_improvement_live_report_initialized=True,
            pause_requested=True,
            heartbeat_reconciled=True,
            terminal_completion_started=True,
            terminal_completion_allowed=True,
        ),
    }
