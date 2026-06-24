"""FlowGuard model for terminal FlowGuard coverage governance.

Risk purpose:
- Guards the terminal route stage where PM asks the FlowGuard operator for a
  whole-route coverage report before final ledger and terminal replay.
- Prevents scattered node-level FlowGuard notes, progress-only reports, stale
  reports, unaccepted reports, unresolved blockers, or pending PM suggestions
  from substituting for PM-accepted terminal coverage closure.
- Companion command:
  `python simulations/run_flowpilot_terminal_flowguard_coverage_checks.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


TERMINAL_FLOWGUARD_COVERAGE = "terminal_flowguard_coverage"

SCENARIOS = (TERMINAL_FLOWGUARD_COVERAGE,)
REQUIRED_LABELS = (
    "select_terminal_flowguard_coverage",
    "node_parent_replay_settled",
    "pm_requests_terminal_flowguard_coverage_review",
    "flowguard_operator_writes_terminal_coverage_report",
    "pm_accepts_terminal_flowguard_coverage_report",
    "pm_records_flowguard_terminal_coverage_closure",
    "reviewer_passes_flowguard_coverage_governance_segment",
    "pm_approves_terminal_closure",
    "terminal_flowguard_coverage_complete",
)
MAX_SEQUENCE_LENGTH = 10


@dataclass(frozen=True)
class Tick:
    """One terminal FlowGuard coverage transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | complete
    scenario: str = "unset"

    node_parent_replay_settled: bool = False
    terminal_work_order_recorded: bool = False
    terminal_report_written: bool = False
    report_current: bool = False
    report_pm_accepted: bool = False
    final_ledger_has_coverage_closure: bool = False
    reviewer_segment_present: bool = False
    reviewer_segment_passed: bool = False
    pm_closure_approved: bool = False

    scattered_node_evidence_only: bool = False
    progress_only_report: bool = False
    stale_report: bool = False
    unaccepted_report: bool = False
    unresolved_blocker: bool = False
    pending_pm_suggestion: bool = False
    operator_direct_target_repair: bool = False


class TerminalFlowGuardCoverageStep:
    """Input x State -> Set(Output x State) for terminal coverage governance.

    reads: node and parent replay ledgers, FlowGuard operator work-order lifecycle,
      FlowGuard model/test/evidence records, PM suggestion ledger, final ledger,
      terminal replay map
    writes: terminal FlowGuard coverage report, PM final ledger coverage row,
      terminal replay segment, terminal closure suite
    idempotency: report and closure facts are monotonic for one route version.
    """

    name = "TerminalFlowGuardCoverageStep"
    input_description = "one terminal FlowGuard coverage governance tick"
    output_description = "next PM/FlowGuard-operator/reviewer terminal coverage transition"
    reads = (
        "node_completion_ledgers",
        "parent_backward_replays",
        "flowguard_operator_work_orders",
        "flowguard_models",
        "flowguard_test_evidence",
        "pm_suggestion_ledger",
        "final_route_wide_gate_ledger",
        "terminal_human_backward_replay_map",
    )
    writes = (
        "flowguard_terminal_coverage_report",
        "final_route_wide_gate_ledger",
        "terminal_human_backward_replay_map",
        "terminal_closure_suite",
    )
    idempotency = "Retries observe the same route version and report path."

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for label, new_state in next_states(state):
            yield FunctionResult(output=Action(label), new_state=new_state, label=label)


def initial_state() -> State:
    return State()


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    if state.status == "complete":
        return ()

    if state.scenario == "unset":
        return (
            (
                "select_terminal_flowguard_coverage",
                replace(state, status="running", scenario=TERMINAL_FLOWGUARD_COVERAGE),
            ),
        )

    if not state.node_parent_replay_settled:
        return (("node_parent_replay_settled", replace(state, node_parent_replay_settled=True)),)
    if not state.terminal_work_order_recorded:
        return (
            (
                "pm_requests_terminal_flowguard_coverage_review",
                replace(state, terminal_work_order_recorded=True),
            ),
        )
    if not state.terminal_report_written:
        return (
            (
                "flowguard_operator_writes_terminal_coverage_report",
                replace(state, terminal_report_written=True, report_current=True),
            ),
        )
    if not state.report_pm_accepted:
        return (
            (
                "pm_accepts_terminal_flowguard_coverage_report",
                replace(state, report_pm_accepted=True),
            ),
        )
    if not state.final_ledger_has_coverage_closure:
        return (
            (
                "pm_records_flowguard_terminal_coverage_closure",
                replace(state, final_ledger_has_coverage_closure=True, reviewer_segment_present=True),
            ),
        )
    if not state.reviewer_segment_passed:
        return (
            (
                "reviewer_passes_flowguard_coverage_governance_segment",
                replace(state, reviewer_segment_present=True, reviewer_segment_passed=True),
            ),
        )
    if not state.pm_closure_approved:
        return (("pm_approves_terminal_closure", replace(state, pm_closure_approved=True)),)
    return (("terminal_flowguard_coverage_complete", replace(state, status="complete")),)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.terminal_work_order_recorded and not state.node_parent_replay_settled:
        failures.append("terminal FlowGuard coverage requested before node and parent replay settled")
    if state.report_pm_accepted and not state.terminal_report_written:
        failures.append("PM accepted terminal FlowGuard coverage before operator report exists")
    if state.final_ledger_has_coverage_closure and not state.report_pm_accepted:
        failures.append("final ledger records terminal FlowGuard coverage before PM accepts report")
    if state.reviewer_segment_passed and not state.final_ledger_has_coverage_closure:
        failures.append("reviewer passed FlowGuard governance segment before final ledger closure row")
    if state.reviewer_segment_passed and not state.reviewer_segment_present:
        failures.append("reviewer passed missing FlowGuard governance segment")
    if state.pm_closure_approved and not state.final_ledger_has_coverage_closure:
        failures.append("terminal closure approved without FlowGuard coverage closure row")
    if state.pm_closure_approved and not state.reviewer_segment_passed:
        failures.append("terminal closure approved before reviewer checked FlowGuard coverage governance")
    if state.pm_closure_approved and not state.report_current:
        failures.append("terminal closure approved with stale FlowGuard coverage report")
    if state.pm_closure_approved and not state.report_pm_accepted:
        failures.append("terminal closure approved with unaccepted FlowGuard coverage report")
    if state.pm_closure_approved and state.scattered_node_evidence_only:
        failures.append("terminal closure approved with scattered node FlowGuard evidence only")
    if state.pm_closure_approved and state.progress_only_report:
        failures.append("terminal closure approved with progress-only FlowGuard report")
    if state.pm_closure_approved and state.stale_report:
        failures.append("terminal closure approved with stale FlowGuard coverage evidence")
    if state.pm_closure_approved and state.unaccepted_report:
        failures.append("terminal closure approved with PM-unaccepted FlowGuard coverage evidence")
    if state.pm_closure_approved and state.unresolved_blocker:
        failures.append("terminal closure approved with unresolved FlowGuard coverage blocker")
    if state.pm_closure_approved and state.pending_pm_suggestion:
        failures.append("terminal closure approved with pending FlowGuard PM suggestion")
    if state.operator_direct_target_repair:
        failures.append("FlowGuard operator directly repaired target project instead of reporting coverage")
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
    _invariant(
        "coverage_request_after_replay_settled",
        "terminal FlowGuard coverage requested before node and parent replay settled",
    ),
    _invariant(
        "pm_accepts_existing_terminal_report",
        "PM accepted terminal FlowGuard coverage before operator report exists",
    ),
    _invariant(
        "final_ledger_requires_pm_accepted_report",
        "final ledger records terminal FlowGuard coverage before PM accepts report",
    ),
    _invariant(
        "reviewer_segment_after_final_ledger_row",
        "reviewer passed FlowGuard governance segment before final ledger closure row",
    ),
    _invariant(
        "reviewer_segment_must_exist",
        "reviewer passed missing FlowGuard governance segment",
    ),
    _invariant(
        "closure_requires_coverage_row",
        "terminal closure approved without FlowGuard coverage closure row",
    ),
    _invariant(
        "closure_requires_reviewer_coverage_segment",
        "terminal closure approved before reviewer checked FlowGuard coverage governance",
    ),
    _invariant(
        "closure_requires_current_report",
        "terminal closure approved with stale FlowGuard coverage report",
    ),
    _invariant(
        "closure_requires_pm_accepted_report",
        "terminal closure approved with unaccepted FlowGuard coverage report",
    ),
    _invariant(
        "closure_rejects_scattered_node_evidence_only",
        "terminal closure approved with scattered node FlowGuard evidence only",
    ),
    _invariant(
        "closure_rejects_progress_only_report",
        "terminal closure approved with progress-only FlowGuard report",
    ),
    _invariant(
        "closure_rejects_stale_evidence",
        "terminal closure approved with stale FlowGuard coverage evidence",
    ),
    _invariant(
        "closure_rejects_unaccepted_evidence",
        "terminal closure approved with PM-unaccepted FlowGuard coverage evidence",
    ),
    _invariant(
        "closure_rejects_unresolved_blocker",
        "terminal closure approved with unresolved FlowGuard coverage blocker",
    ),
    _invariant(
        "closure_rejects_pending_suggestion",
        "terminal closure approved with pending FlowGuard PM suggestion",
    ),
    _invariant(
        "operator_reports_not_repairs",
        "FlowGuard operator directly repaired target project instead of reporting coverage",
    ),
)


def intended_plan_state() -> State:
    return State(
        status="complete",
        scenario=TERMINAL_FLOWGUARD_COVERAGE,
        node_parent_replay_settled=True,
        terminal_work_order_recorded=True,
        terminal_report_written=True,
        report_current=True,
        report_pm_accepted=True,
        final_ledger_has_coverage_closure=True,
        reviewer_segment_present=True,
        reviewer_segment_passed=True,
        pm_closure_approved=True,
    )


HAZARD_STATES = {
    "closure_without_terminal_report": replace(
        intended_plan_state(),
        terminal_report_written=False,
        report_current=False,
        report_pm_accepted=False,
    ),
    "closure_with_scattered_node_evidence_only": replace(
        intended_plan_state(),
        scattered_node_evidence_only=True,
    ),
    "closure_with_progress_only_report": replace(
        intended_plan_state(),
        progress_only_report=True,
    ),
    "closure_with_stale_report": replace(
        intended_plan_state(),
        report_current=False,
        stale_report=True,
    ),
    "closure_with_unaccepted_report": replace(
        intended_plan_state(),
        report_pm_accepted=False,
        unaccepted_report=True,
    ),
    "closure_with_unresolved_blocker": replace(
        intended_plan_state(),
        unresolved_blocker=True,
    ),
    "closure_with_pending_pm_suggestion": replace(
        intended_plan_state(),
        pending_pm_suggestion=True,
    ),
    "closure_with_missing_reviewer_segment": replace(
        intended_plan_state(),
        reviewer_segment_present=False,
    ),
    "operator_direct_target_repair": replace(
        intended_plan_state(),
        operator_direct_target_repair=True,
    ),
}

HAZARD_EXPECTED_FAILURES = {
    "closure_without_terminal_report": "terminal closure approved with stale FlowGuard coverage report",
    "closure_with_scattered_node_evidence_only": "terminal closure approved with scattered node FlowGuard evidence only",
    "closure_with_progress_only_report": "terminal closure approved with progress-only FlowGuard report",
    "closure_with_stale_report": "terminal closure approved with stale FlowGuard coverage evidence",
    "closure_with_unaccepted_report": "terminal closure approved with PM-unaccepted FlowGuard coverage evidence",
    "closure_with_unresolved_blocker": "terminal closure approved with unresolved FlowGuard coverage blocker",
    "closure_with_pending_pm_suggestion": "terminal closure approved with pending FlowGuard PM suggestion",
    "closure_with_missing_reviewer_segment": "reviewer passed missing FlowGuard governance segment",
    "operator_direct_target_repair": "FlowGuard operator directly repaired target project instead of reporting coverage",
}

CARTESIAN_AXES = {
    "report_binding": ("missing", "scattered_node_evidence_only", "terminal_report"),
    "freshness": ("current", "stale"),
    "pm_acceptance": ("accepted", "unaccepted"),
    "blockers": ("none", "unresolved"),
    "pm_suggestions": ("disposed", "pending"),
    "reviewer_governance_segment": ("present_and_passed", "missing"),
}


def cartesian_hazard_states() -> dict[str, State]:
    cases: dict[str, State] = {}
    for report_binding in CARTESIAN_AXES["report_binding"]:
        for freshness in CARTESIAN_AXES["freshness"]:
            for pm_acceptance in CARTESIAN_AXES["pm_acceptance"]:
                for blockers in CARTESIAN_AXES["blockers"]:
                    for pm_suggestions in CARTESIAN_AXES["pm_suggestions"]:
                        for reviewer_segment in CARTESIAN_AXES["reviewer_governance_segment"]:
                            terminal_report = report_binding == "terminal_report"
                            current = freshness == "current"
                            accepted = pm_acceptance == "accepted"
                            segment_present = reviewer_segment == "present_and_passed"
                            safe = (
                                terminal_report
                                and current
                                and accepted
                                and blockers == "none"
                                and pm_suggestions == "disposed"
                                and segment_present
                            )
                            if safe:
                                continue
                            name = "|".join(
                                (
                                    f"report={report_binding}",
                                    f"freshness={freshness}",
                                    f"pm={pm_acceptance}",
                                    f"blockers={blockers}",
                                    f"suggestions={pm_suggestions}",
                                    f"reviewer={reviewer_segment}",
                                )
                            )
                            cases[name] = replace(
                                intended_plan_state(),
                                terminal_report_written=terminal_report,
                                report_current=current,
                                report_pm_accepted=accepted,
                                scattered_node_evidence_only=report_binding == "scattered_node_evidence_only",
                                progress_only_report=report_binding == "missing",
                                stale_report=freshness == "stale",
                                unaccepted_report=pm_acceptance == "unaccepted",
                                unresolved_blocker=blockers == "unresolved",
                                pending_pm_suggestion=pm_suggestions == "pending",
                                reviewer_segment_present=segment_present,
                            )
    return cases


def is_terminal(state: State) -> bool:
    return state.status == "complete"


def is_success(state: State) -> bool:
    return is_terminal(state) and not invariant_failures(state)


def build_workflow() -> Workflow:
    return Workflow((TerminalFlowGuardCoverageStep(),), name="flowpilot_terminal_flowguard_coverage")


EXTERNAL_INPUTS = (Tick(),)
