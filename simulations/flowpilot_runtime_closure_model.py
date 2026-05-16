"""FlowGuard model for FlowPilot runtime closure maintenance.

Risk purpose:
- Uses FlowGuard (https://github.com/liuyingxuvka/FlowGuard) to review the
  FlowPilot runtime-closure pass.
- Guards against officer reports bypassing PM packet requests, old continuation
  state becoming current authority, final user reports substituting for
  terminal closure, and stale route-display projections overriding route state.
- Run or update this model when changing officer request/report routing,
  continuation import/quarantine behavior, terminal summary/user-report
  writing, or route-display refresh semantics.
- Companion command:
  `python simulations/run_flowpilot_runtime_closure_checks.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


SCENARIOS = (
    "officer_authorized_packet",
    "continuation_quarantine",
    "closure_user_report",
    "route_display_refresh",
)


@dataclass(frozen=True)
class Tick:
    """One runtime-closure transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | complete
    scenario: str = "unset"

    pm_officer_request_packet_recorded: bool = False
    officer_report_router_event_authorized: bool = False
    officer_report_body_sealed_from_controller: bool = False
    officer_report_relayed_to_pm: bool = False
    officer_gate_advanced: bool = False

    prior_state_imported: bool = False
    quarantine_recorded: bool = False
    imported_item_read_only: bool = False
    old_agent_id_audit_only: bool = False
    old_assets_dispositioned: bool = False
    imported_state_used_as_current_authority: bool = False

    final_ledger_clean: bool = False
    terminal_backward_replay_passed: bool = False
    pm_closure_approved: bool = False
    final_user_report_written: bool = False
    final_user_report_used_as_closure_input: bool = False

    route_frontier_changed: bool = False
    display_refreshed: bool = False
    display_version_matches_frontier: bool = False
    display_used_as_route_authority: bool = False


def initial_state() -> State:
    return State()


class RuntimeClosureStep:
    """Input x State -> Set(Output x State) for runtime closure."""

    name = "RuntimeClosureStep"
    input_description = "one FlowPilot runtime-closure step"
    output_description = "officer, quarantine, closure-report, or display-refresh transition"
    reads = (
        "pm role-work/officer request index",
        "packet/result envelopes",
        "current-run quarantine records",
        "terminal closure authorities",
        "route/frontier/display files",
    )
    writes = (
        "officer report completion state",
        "current-run quarantine ledger",
        "final user report artifacts",
        "display refresh artifacts",
    )
    idempotency = "Retries update current-run records without duplicating authority or terminal completion."

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for label, new_state in next_states(state):
            yield FunctionResult(output=Action(label), new_state=new_state, label=label)


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    if state.status == "complete":
        return ()

    if state.scenario == "unset":
        return tuple(
            (
                f"select_{scenario}",
                replace(state, status="running", scenario=scenario),
            )
            for scenario in SCENARIOS
        )

    if state.scenario == "officer_authorized_packet":
        if not state.pm_officer_request_packet_recorded:
            return (("pm_records_officer_request_packet", replace(state, pm_officer_request_packet_recorded=True)),)
        if not state.officer_report_router_event_authorized:
            return (("router_authorizes_officer_report_event", replace(state, officer_report_router_event_authorized=True)),)
        if not state.officer_report_body_sealed_from_controller:
            return (
                (
                    "controller_relays_officer_envelope_without_body",
                    replace(state, officer_report_body_sealed_from_controller=True),
                ),
            )
        if not state.officer_report_relayed_to_pm:
            return (("router_relays_officer_report_to_pm", replace(state, officer_report_relayed_to_pm=True)),)
        return (
            (
                "pm_advances_gate_from_authorized_officer_report",
                replace(state, officer_gate_advanced=True, status="complete"),
            ),
        )

    if state.scenario == "continuation_quarantine":
        if not state.prior_state_imported:
            return (("current_run_imports_prior_evidence", replace(state, prior_state_imported=True)),)
        if not state.quarantine_recorded:
            return (("current_run_records_quarantine_disposition", replace(state, quarantine_recorded=True)),)
        if not state.imported_item_read_only:
            return (("imported_control_state_marked_read_only", replace(state, imported_item_read_only=True)),)
        if not state.old_agent_id_audit_only:
            return (("old_agent_ids_marked_audit_only", replace(state, old_agent_id_audit_only=True)),)
        if not state.old_assets_dispositioned:
            return (("old_assets_dispositioned_before_reuse", replace(state, old_assets_dispositioned=True)),)
        return (("continuation_quarantine_complete", replace(state, status="complete")),)

    if state.scenario == "closure_user_report":
        if not state.final_ledger_clean:
            return (("pm_final_ledger_clean", replace(state, final_ledger_clean=True)),)
        if not state.terminal_backward_replay_passed:
            return (("reviewer_terminal_backward_replay_passed", replace(state, terminal_backward_replay_passed=True)),)
        if not state.pm_closure_approved:
            return (("pm_approves_terminal_closure", replace(state, pm_closure_approved=True)),)
        if not state.final_user_report_written:
            return (("controller_writes_final_user_report", replace(state, final_user_report_written=True)),)
        return (("closure_user_report_complete", replace(state, status="complete")),)

    if state.scenario == "route_display_refresh":
        if not state.route_frontier_changed:
            return (("route_or_frontier_changes", replace(state, route_frontier_changed=True)),)
        if not state.display_refreshed:
            return (
                (
                    "router_refreshes_route_display_projection",
                    replace(state, display_refreshed=True, display_version_matches_frontier=True),
                ),
            )
        return (("display_refresh_complete", replace(state, status="complete")),)

    return ()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []

    if state.officer_gate_advanced and not state.pm_officer_request_packet_recorded:
        failures.append("officer gate advanced without PM request packet")
    if state.officer_gate_advanced and not state.officer_report_router_event_authorized:
        failures.append("officer gate advanced without router-authorized report event")
    if state.officer_report_relayed_to_pm and not state.officer_report_body_sealed_from_controller:
        failures.append("officer report relay exposed sealed body to Controller")

    if state.imported_state_used_as_current_authority and not state.quarantine_recorded:
        failures.append("imported prior state became authority without quarantine")
    if state.imported_state_used_as_current_authority and not state.imported_item_read_only:
        failures.append("imported control state was not converted to read-only evidence")
    if state.imported_state_used_as_current_authority and not state.old_agent_id_audit_only:
        failures.append("old agent id became current authority")
    if state.imported_state_used_as_current_authority and not state.old_assets_dispositioned:
        failures.append("old asset became current evidence without disposition")

    if state.final_user_report_written and not (
        state.final_ledger_clean
        and state.terminal_backward_replay_passed
        and state.pm_closure_approved
    ):
        failures.append("final user report written before clean terminal closure")
    if state.final_user_report_used_as_closure_input:
        failures.append("final user report was used as closure authority")

    if state.display_refreshed and state.display_used_as_route_authority:
        failures.append("display projection used as route authority")
    if state.route_frontier_changed and state.display_refreshed and not state.display_version_matches_frontier:
        failures.append("display projection refreshed with stale route frontier version")

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
    _invariant("officer_requires_pm_request", "officer gate advanced without PM request packet"),
    _invariant("officer_requires_router_authorization", "officer gate advanced without router-authorized report event"),
    _invariant("officer_body_stays_sealed", "officer report relay exposed sealed body to Controller"),
    _invariant("prior_state_requires_quarantine", "imported prior state became authority without quarantine"),
    _invariant("prior_control_state_read_only", "imported control state was not converted to read-only evidence"),
    _invariant("old_agent_ids_are_audit_only", "old agent id became current authority"),
    _invariant("old_assets_need_disposition", "old asset became current evidence without disposition"),
    _invariant("user_report_after_closure_only", "final user report written before clean terminal closure"),
    _invariant("user_report_not_closure_authority", "final user report was used as closure authority"),
    _invariant("display_not_route_authority", "display projection used as route authority"),
    _invariant("display_refresh_matches_frontier", "display projection refreshed with stale route frontier version"),
)


HAZARD_STATES = {
    "officer_direct_event_without_request": replace(
        initial_state(),
        status="complete",
        scenario="officer_authorized_packet",
        officer_report_router_event_authorized=True,
        officer_report_body_sealed_from_controller=True,
        officer_report_relayed_to_pm=True,
        officer_gate_advanced=True,
    ),
    "officer_invented_event": replace(
        initial_state(),
        status="complete",
        scenario="officer_authorized_packet",
        pm_officer_request_packet_recorded=True,
        officer_report_body_sealed_from_controller=True,
        officer_report_relayed_to_pm=True,
        officer_gate_advanced=True,
    ),
    "prior_state_reused_without_quarantine": replace(
        initial_state(),
        scenario="continuation_quarantine",
        prior_state_imported=True,
        imported_state_used_as_current_authority=True,
    ),
    "old_agent_id_reused_as_current": replace(
        initial_state(),
        scenario="continuation_quarantine",
        prior_state_imported=True,
        quarantine_recorded=True,
        imported_item_read_only=True,
        old_assets_dispositioned=True,
        imported_state_used_as_current_authority=True,
    ),
    "final_report_before_pm_closure": replace(
        initial_state(),
        scenario="closure_user_report",
        final_ledger_clean=True,
        terminal_backward_replay_passed=True,
        final_user_report_written=True,
    ),
    "final_report_used_as_closure_input": replace(
        initial_state(),
        scenario="closure_user_report",
        final_ledger_clean=True,
        terminal_backward_replay_passed=True,
        pm_closure_approved=True,
        final_user_report_written=True,
        final_user_report_used_as_closure_input=True,
    ),
    "stale_display_refresh": replace(
        initial_state(),
        scenario="route_display_refresh",
        route_frontier_changed=True,
        display_refreshed=True,
    ),
    "display_overrides_route_state": replace(
        initial_state(),
        scenario="route_display_refresh",
        route_frontier_changed=True,
        display_refreshed=True,
        display_version_matches_frontier=True,
        display_used_as_route_authority=True,
    ),
}


HAZARD_EXPECTED_FAILURES = {
    "officer_direct_event_without_request": "officer gate advanced without PM request packet",
    "officer_invented_event": "officer gate advanced without router-authorized report event",
    "prior_state_reused_without_quarantine": "imported prior state became authority without quarantine",
    "old_agent_id_reused_as_current": "old agent id became current authority",
    "final_report_before_pm_closure": "final user report written before clean terminal closure",
    "final_report_used_as_closure_input": "final user report was used as closure authority",
    "stale_display_refresh": "display projection refreshed with stale route frontier version",
    "display_overrides_route_state": "display projection used as route authority",
}


REQUIRED_LABELS = (
    "select_officer_authorized_packet",
    "pm_records_officer_request_packet",
    "router_authorizes_officer_report_event",
    "controller_relays_officer_envelope_without_body",
    "router_relays_officer_report_to_pm",
    "pm_advances_gate_from_authorized_officer_report",
    "select_continuation_quarantine",
    "current_run_imports_prior_evidence",
    "current_run_records_quarantine_disposition",
    "imported_control_state_marked_read_only",
    "old_agent_ids_marked_audit_only",
    "old_assets_dispositioned_before_reuse",
    "continuation_quarantine_complete",
    "select_closure_user_report",
    "pm_final_ledger_clean",
    "reviewer_terminal_backward_replay_passed",
    "pm_approves_terminal_closure",
    "controller_writes_final_user_report",
    "closure_user_report_complete",
    "select_route_display_refresh",
    "route_or_frontier_changes",
    "router_refreshes_route_display_projection",
    "display_refresh_complete",
)


def build_workflow() -> Workflow:
    return Workflow((RuntimeClosureStep(),), name="flowpilot_runtime_closure")


def is_terminal(state: State) -> bool:
    return state.status == "complete"


def is_success(state: State) -> bool:
    return state.status == "complete" and not invariant_failures(state)


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 8
