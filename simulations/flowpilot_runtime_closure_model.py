"""FlowGuard model for FlowPilot runtime closure maintenance.

Risk purpose:
- Uses FlowGuard (https://github.com/liuyingxuvka/FlowGuard) to review the
  FlowPilot runtime-closure pass.
- Guards against FlowGuard operator reports bypassing PM packet requests, old continuation
  state becoming current authority, final user reports substituting for
  terminal closure, and stale route-display projections overriding route state.
- Run or update this model when changing FlowGuard operator request/report routing,
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
    "flowguard_operator_authorized_packet",
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

    pm_flowguard_operator_request_packet_recorded: bool = False
    flowguard_operator_report_router_event_authorized: bool = False
    flowguard_operator_report_body_sealed_from_controller: bool = False
    flowguard_operator_report_relayed_to_pm: bool = False
    flowguard_operator_gate_advanced: bool = False

    prior_state_imported: bool = False
    quarantine_recorded: bool = False
    imported_item_read_only: bool = False
    old_agent_id_audit_only: bool = False
    old_assets_dispositioned: bool = False
    imported_state_used_as_current_authority: bool = False

    final_ledger_clean: bool = False
    terminal_ledger_hygiene_clean: bool = False
    dirty_accepted_pointers_absent: bool = False
    stale_active_blockers_absent: bool = False
    break_glass_incidents_closed: bool = False
    temporary_patch_validation_closed: bool = False
    final_reviewer_authorized_reads_complete: bool = False
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
    output_description = "FlowGuard operator, quarantine, closure-report, or display-refresh transition"
    reads = (
        "pm role-work/FlowGuard operator request index",
        "packet/result envelopes",
        "current-run quarantine records",
        "terminal closure authorities",
        "route/frontier/display files",
    )
    writes = (
        "FlowGuard operator report completion state",
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

    if state.scenario == "flowguard_operator_authorized_packet":
        if not state.pm_flowguard_operator_request_packet_recorded:
            return (("pm_records_flowguard_operator_request_packet", replace(state, pm_flowguard_operator_request_packet_recorded=True)),)
        if not state.flowguard_operator_report_router_event_authorized:
            return (("router_authorizes_flowguard_operator_report_event", replace(state, flowguard_operator_report_router_event_authorized=True)),)
        if not state.flowguard_operator_report_body_sealed_from_controller:
            return (
                (
                    "controller_relays_flowguard_operator_envelope_without_body",
                    replace(state, flowguard_operator_report_body_sealed_from_controller=True),
                ),
            )
        if not state.flowguard_operator_report_relayed_to_pm:
            return (("router_relays_flowguard_operator_report_to_pm", replace(state, flowguard_operator_report_relayed_to_pm=True)),)
        return (
            (
                "pm_advances_gate_from_authorized_flowguard_operator_report",
                replace(state, flowguard_operator_gate_advanced=True, status="complete"),
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
        if not state.terminal_ledger_hygiene_clean:
            return (
                (
                    "terminal_ledger_hygiene_passed",
                    replace(
                        state,
                        terminal_ledger_hygiene_clean=True,
                        dirty_accepted_pointers_absent=True,
                        stale_active_blockers_absent=True,
                        break_glass_incidents_closed=True,
                        temporary_patch_validation_closed=True,
                    ),
                ),
            )
        if not state.final_ledger_clean:
            return (("pm_final_ledger_clean", replace(state, final_ledger_clean=True)),)
        if not state.final_reviewer_authorized_reads_complete:
            return (
                (
                    "final_reviewer_authorized_reads_complete",
                    replace(state, final_reviewer_authorized_reads_complete=True),
                ),
            )
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

    if state.flowguard_operator_gate_advanced and not state.pm_flowguard_operator_request_packet_recorded:
        failures.append("FlowGuard operator gate advanced without PM request packet")
    if state.flowguard_operator_gate_advanced and not state.flowguard_operator_report_router_event_authorized:
        failures.append("FlowGuard operator gate advanced without router-authorized report event")
    if state.flowguard_operator_report_relayed_to_pm and not state.flowguard_operator_report_body_sealed_from_controller:
        failures.append("FlowGuard operator report relay exposed sealed body to Controller")

    if state.imported_state_used_as_current_authority and not state.quarantine_recorded:
        failures.append("imported prior state became authority without quarantine")
    if state.imported_state_used_as_current_authority and not state.imported_item_read_only:
        failures.append("imported control state was not converted to read-only evidence")
    if state.imported_state_used_as_current_authority and not state.old_agent_id_audit_only:
        failures.append("old agent id became current authority")
    if state.imported_state_used_as_current_authority and not state.old_assets_dispositioned:
        failures.append("old asset became current evidence without disposition")

    closure_hygiene_clean = (
        state.terminal_ledger_hygiene_clean
        and state.dirty_accepted_pointers_absent
        and state.stale_active_blockers_absent
        and state.break_glass_incidents_closed
        and state.temporary_patch_validation_closed
        and state.final_reviewer_authorized_reads_complete
    )
    if state.final_user_report_written and not (
        state.final_ledger_clean
        and closure_hygiene_clean
        and state.terminal_backward_replay_passed
        and state.pm_closure_approved
    ):
        failures.append("final user report written before clean terminal closure")
    if state.scenario == "closure_user_report" and state.final_user_report_written:
        if not state.dirty_accepted_pointers_absent:
            failures.append("terminal closure ignored dirty accepted-result pointers")
        if not state.stale_active_blockers_absent:
            failures.append("terminal closure ignored stale active blockers")
        if not state.break_glass_incidents_closed:
            failures.append("terminal closure ignored open break-glass incidents")
        if not state.temporary_patch_validation_closed:
            failures.append("terminal closure ignored pending break-glass patch validation")
        if not state.final_reviewer_authorized_reads_complete:
            failures.append("terminal closure ran without complete final Reviewer authorized reads")
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
    _invariant("flowguard_operator_requires_pm_request", "FlowGuard operator gate advanced without PM request packet"),
    _invariant("flowguard_operator_requires_router_authorization", "FlowGuard operator gate advanced without router-authorized report event"),
    _invariant("flowguard_operator_body_stays_sealed", "FlowGuard operator report relay exposed sealed body to Controller"),
    _invariant("prior_state_requires_quarantine", "imported prior state became authority without quarantine"),
    _invariant("prior_control_state_read_only", "imported control state was not converted to read-only evidence"),
    _invariant("old_agent_ids_are_audit_only", "old agent id became current authority"),
    _invariant("old_assets_need_disposition", "old asset became current evidence without disposition"),
    _invariant("user_report_after_closure_only", "final user report written before clean terminal closure"),
    _invariant("closure_blocks_dirty_accepted_pointers", "terminal closure ignored dirty accepted-result pointers"),
    _invariant("closure_blocks_stale_active_blockers", "terminal closure ignored stale active blockers"),
    _invariant("closure_blocks_open_break_glass_incidents", "terminal closure ignored open break-glass incidents"),
    _invariant("closure_blocks_pending_break_glass_patch_validation", "terminal closure ignored pending break-glass patch validation"),
    _invariant("closure_requires_final_reviewer_authorized_reads", "terminal closure ran without complete final Reviewer authorized reads"),
    _invariant("user_report_not_closure_authority", "final user report was used as closure authority"),
    _invariant("display_not_route_authority", "display projection used as route authority"),
    _invariant("display_refresh_matches_frontier", "display projection refreshed with stale route frontier version"),
)


HAZARD_STATES = {
    "flowguard_operator_direct_event_without_request": replace(
        initial_state(),
        status="complete",
        scenario="flowguard_operator_authorized_packet",
        flowguard_operator_report_router_event_authorized=True,
        flowguard_operator_report_body_sealed_from_controller=True,
        flowguard_operator_report_relayed_to_pm=True,
        flowguard_operator_gate_advanced=True,
    ),
    "flowguard_operator_invented_event": replace(
        initial_state(),
        status="complete",
        scenario="flowguard_operator_authorized_packet",
        pm_flowguard_operator_request_packet_recorded=True,
        flowguard_operator_report_body_sealed_from_controller=True,
        flowguard_operator_report_relayed_to_pm=True,
        flowguard_operator_gate_advanced=True,
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
        terminal_ledger_hygiene_clean=True,
        dirty_accepted_pointers_absent=True,
        stale_active_blockers_absent=True,
        break_glass_incidents_closed=True,
        temporary_patch_validation_closed=True,
        final_reviewer_authorized_reads_complete=True,
        final_ledger_clean=True,
        terminal_backward_replay_passed=True,
        final_user_report_written=True,
    ),
    "final_report_used_as_closure_input": replace(
        initial_state(),
        scenario="closure_user_report",
        terminal_ledger_hygiene_clean=True,
        dirty_accepted_pointers_absent=True,
        stale_active_blockers_absent=True,
        break_glass_incidents_closed=True,
        temporary_patch_validation_closed=True,
        final_reviewer_authorized_reads_complete=True,
        final_ledger_clean=True,
        terminal_backward_replay_passed=True,
        pm_closure_approved=True,
        final_user_report_written=True,
        final_user_report_used_as_closure_input=True,
    ),
    "terminal_dirty_accepted_pointer_ignored": replace(
        initial_state(),
        scenario="closure_user_report",
        terminal_ledger_hygiene_clean=True,
        dirty_accepted_pointers_absent=False,
        stale_active_blockers_absent=True,
        break_glass_incidents_closed=True,
        temporary_patch_validation_closed=True,
        final_reviewer_authorized_reads_complete=True,
        final_ledger_clean=True,
        terminal_backward_replay_passed=True,
        pm_closure_approved=True,
        final_user_report_written=True,
    ),
    "terminal_stale_active_blocker_ignored": replace(
        initial_state(),
        scenario="closure_user_report",
        terminal_ledger_hygiene_clean=True,
        dirty_accepted_pointers_absent=True,
        stale_active_blockers_absent=False,
        break_glass_incidents_closed=True,
        temporary_patch_validation_closed=True,
        final_reviewer_authorized_reads_complete=True,
        final_ledger_clean=True,
        terminal_backward_replay_passed=True,
        pm_closure_approved=True,
        final_user_report_written=True,
    ),
    "terminal_open_break_glass_ignored": replace(
        initial_state(),
        scenario="closure_user_report",
        terminal_ledger_hygiene_clean=True,
        dirty_accepted_pointers_absent=True,
        stale_active_blockers_absent=True,
        break_glass_incidents_closed=False,
        temporary_patch_validation_closed=True,
        final_reviewer_authorized_reads_complete=True,
        final_ledger_clean=True,
        terminal_backward_replay_passed=True,
        pm_closure_approved=True,
        final_user_report_written=True,
    ),
    "terminal_pending_patch_ignored": replace(
        initial_state(),
        scenario="closure_user_report",
        terminal_ledger_hygiene_clean=True,
        dirty_accepted_pointers_absent=True,
        stale_active_blockers_absent=True,
        break_glass_incidents_closed=True,
        temporary_patch_validation_closed=False,
        final_reviewer_authorized_reads_complete=True,
        final_ledger_clean=True,
        terminal_backward_replay_passed=True,
        pm_closure_approved=True,
        final_user_report_written=True,
    ),
    "terminal_final_reviewer_auth_missing": replace(
        initial_state(),
        scenario="closure_user_report",
        terminal_ledger_hygiene_clean=True,
        dirty_accepted_pointers_absent=True,
        stale_active_blockers_absent=True,
        break_glass_incidents_closed=True,
        temporary_patch_validation_closed=True,
        final_reviewer_authorized_reads_complete=False,
        final_ledger_clean=True,
        terminal_backward_replay_passed=True,
        pm_closure_approved=True,
        final_user_report_written=True,
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
    "flowguard_operator_direct_event_without_request": "FlowGuard operator gate advanced without PM request packet",
    "flowguard_operator_invented_event": "FlowGuard operator gate advanced without router-authorized report event",
    "prior_state_reused_without_quarantine": "imported prior state became authority without quarantine",
    "old_agent_id_reused_as_current": "old agent id became current authority",
    "final_report_before_pm_closure": "final user report written before clean terminal closure",
    "final_report_used_as_closure_input": "final user report was used as closure authority",
    "terminal_dirty_accepted_pointer_ignored": "terminal closure ignored dirty accepted-result pointers",
    "terminal_stale_active_blocker_ignored": "terminal closure ignored stale active blockers",
    "terminal_open_break_glass_ignored": "terminal closure ignored open break-glass incidents",
    "terminal_pending_patch_ignored": "terminal closure ignored pending break-glass patch validation",
    "terminal_final_reviewer_auth_missing": "terminal closure ran without complete final Reviewer authorized reads",
    "stale_display_refresh": "display projection refreshed with stale route frontier version",
    "display_overrides_route_state": "display projection used as route authority",
}


REQUIRED_LABELS = (
    "select_flowguard_operator_authorized_packet",
    "pm_records_flowguard_operator_request_packet",
    "router_authorizes_flowguard_operator_report_event",
    "controller_relays_flowguard_operator_envelope_without_body",
    "router_relays_flowguard_operator_report_to_pm",
    "pm_advances_gate_from_authorized_flowguard_operator_report",
    "select_continuation_quarantine",
    "current_run_imports_prior_evidence",
    "current_run_records_quarantine_disposition",
    "imported_control_state_marked_read_only",
    "old_agent_ids_marked_audit_only",
    "old_assets_dispositioned_before_reuse",
    "continuation_quarantine_complete",
    "select_closure_user_report",
    "terminal_ledger_hygiene_passed",
    "pm_final_ledger_clean",
    "final_reviewer_authorized_reads_complete",
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
