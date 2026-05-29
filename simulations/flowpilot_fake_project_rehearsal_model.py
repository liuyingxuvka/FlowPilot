"""FlowGuard model for black-box fake-project FlowPilot rehearsal."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_fake_project_blackbox_rehearsal"
MAX_SEQUENCE_LENGTH = 32


@dataclass(frozen=True)
class State:
    status: str = "new"
    startup_ui_opened: bool = False
    fake_user_package_written: bool = False
    startup_ui_closed: bool = False
    startup_body_sealed: bool = False
    cli_start_recorded_route: bool = False
    pm_packet_complete: bool = False
    flowguard_packet_complete: bool = False
    review_packet_complete: bool = False
    validation_packet_complete: bool = False
    closure_packet_complete: bool = False
    route_nodes_materialized: bool = False
    route_node_1_complete: bool = False
    route_node_2_complete: bool = False
    route_node_3_complete: bool = False
    final_route_wide_ledger_built: bool = False
    terminal_status_checked: bool = False
    wrong_role_lease_rejected: bool = False
    wrong_role_recovery_completed: bool = False
    route_mutation_recovered: bool = False
    missing_ack_result_blocked: bool = False
    ack_only_wait_observed: bool = False
    retired_side_command_rejected: bool = False
    scenario_report_written: bool = False
    internal_helper_only: bool = False
    startup_body_leaked: bool = False
    result_body_leaked: bool = False
    wrong_role_lease_accepted: bool = False
    missing_ack_result_accepted: bool = False
    ack_only_terminal: bool = False
    pm_only_terminal: bool = False
    planning_chain_terminal: bool = False
    terminal_missing_route_node: bool = False
    route_mutation_without_frontier_rewrite: bool = False
    side_command_surface_available: bool = False
    terminal_active_lease: bool = False
    terminal_missing_role_packet: bool = False
    error_flow_unrecovered: bool = False


@dataclass(frozen=True)
class Tick:
    """One black-box rehearsal transition."""


@dataclass(frozen=True)
class Action:
    label: str


class Transition(NamedTuple):
    label: str
    state: State


REQUIRED_SAFE_LABELS = (
    "open_startup_ui",
    "write_fake_user_startup_package",
    "close_startup_ui_and_seal_body",
    "start_cli_records_route",
    "complete_pm_packet_via_cli",
    "complete_flowguard_packet_via_cli",
    "complete_review_packet_via_cli",
    "complete_validation_packet_via_cli",
    "complete_closure_packet_via_cli",
    "materialize_route_nodes_from_pm_plan",
    "complete_route_node_1_via_cli",
    "complete_route_node_2_via_cli",
    "complete_route_node_3_via_cli",
    "build_final_route_wide_ledger",
    "verify_terminal_public_status",
    "observe_wrong_role_lease_rejection",
    "recover_from_wrong_role_with_valid_packets",
    "observe_route_mutation_recovery",
    "observe_missing_ack_result_block",
    "observe_ack_only_wait_not_terminal",
    "observe_retired_side_command_rejection",
    "write_rehearsal_report",
)


def initial_state() -> State:
    return State()


class FakeProjectRehearsalStep:
    name = "FakeProjectRehearsalStep"
    reads = (
        "startup_ui_state",
        "cli_command_surface",
        "packet_lifecycle",
        "lease_ack_state",
        "public_status_projection",
        "error_scenario_results",
    )
    writes = (
        "startup_rehearsal_result",
        "fake_role_results",
        "packet_side_effects",
        "status_projection",
        "error_flow_report",
        "test_mesh_row",
    )
    input_description = "Input x State: one requested black-box fake-project rehearsal step"
    output_description = "Set(Output x State): legal next rehearsal states and observed failure branches"
    idempotency = "each step records an externally invoked CLI observation, never a direct internal shortcut"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(output=Action(transition.label), new_state=transition.state, label=transition.label)


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"blocked", "complete"}:
        return ()
    failures = invariant_failures(state)
    if failures:
        return (Transition("blocked_on_fake_project_rehearsal_invariant", replace(state, status="blocked")),)
    if not state.startup_ui_opened:
        return (Transition("open_startup_ui", replace(state, startup_ui_opened=True, status="running")),)
    if not state.fake_user_package_written:
        return (Transition("write_fake_user_startup_package", replace(state, fake_user_package_written=True)),)
    if not state.startup_ui_closed or not state.startup_body_sealed:
        return (
            Transition(
                "close_startup_ui_and_seal_body",
                replace(state, startup_ui_closed=True, startup_body_sealed=True),
            ),
        )
    if not state.cli_start_recorded_route:
        return (Transition("start_cli_records_route", replace(state, cli_start_recorded_route=True)),)
    if not state.pm_packet_complete:
        return (Transition("complete_pm_packet_via_cli", replace(state, pm_packet_complete=True)),)
    if not state.flowguard_packet_complete:
        return (Transition("complete_flowguard_packet_via_cli", replace(state, flowguard_packet_complete=True)),)
    if not state.review_packet_complete:
        return (Transition("complete_review_packet_via_cli", replace(state, review_packet_complete=True)),)
    if not state.validation_packet_complete:
        return (Transition("complete_validation_packet_via_cli", replace(state, validation_packet_complete=True)),)
    if not state.closure_packet_complete:
        return (Transition("complete_closure_packet_via_cli", replace(state, closure_packet_complete=True)),)
    if not state.route_nodes_materialized:
        return (Transition("materialize_route_nodes_from_pm_plan", replace(state, route_nodes_materialized=True)),)
    if not state.route_node_1_complete:
        return (Transition("complete_route_node_1_via_cli", replace(state, route_node_1_complete=True)),)
    if not state.route_node_2_complete:
        return (Transition("complete_route_node_2_via_cli", replace(state, route_node_2_complete=True)),)
    if not state.route_node_3_complete:
        return (Transition("complete_route_node_3_via_cli", replace(state, route_node_3_complete=True)),)
    if not state.final_route_wide_ledger_built:
        return (Transition("build_final_route_wide_ledger", replace(state, final_route_wide_ledger_built=True)),)
    if not state.terminal_status_checked:
        return (Transition("verify_terminal_public_status", replace(state, terminal_status_checked=True)),)
    if not state.wrong_role_lease_rejected:
        return (Transition("observe_wrong_role_lease_rejection", replace(state, wrong_role_lease_rejected=True)),)
    if not state.wrong_role_recovery_completed:
        return (Transition("recover_from_wrong_role_with_valid_packets", replace(state, wrong_role_recovery_completed=True)),)
    if not state.route_mutation_recovered:
        return (Transition("observe_route_mutation_recovery", replace(state, route_mutation_recovered=True)),)
    if not state.missing_ack_result_blocked:
        return (Transition("observe_missing_ack_result_block", replace(state, missing_ack_result_blocked=True)),)
    if not state.ack_only_wait_observed:
        return (Transition("observe_ack_only_wait_not_terminal", replace(state, ack_only_wait_observed=True)),)
    if not state.retired_side_command_rejected:
        return (Transition("observe_retired_side_command_rejection", replace(state, retired_side_command_rejected=True)),)
    if not state.scenario_report_written:
        return (Transition("write_rehearsal_report", replace(state, scenario_report_written=True, status="complete")),)
    return ()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.fake_user_package_written and not state.startup_ui_opened:
        failures.append("fake startup package was written before startup UI opened")
    if state.startup_ui_closed and not state.fake_user_package_written:
        failures.append("startup UI closed without fake user package")
    if state.startup_body_sealed and not state.startup_ui_closed:
        failures.append("startup body sealed before startup UI closed")
    if state.cli_start_recorded_route and not state.startup_body_sealed:
        failures.append("CLI route was recorded before sealed startup body")
    if state.pm_packet_complete and not state.cli_start_recorded_route:
        failures.append("PM packet completed before CLI start route")
    if state.flowguard_packet_complete and not state.pm_packet_complete:
        failures.append("FlowGuard packet completed before PM packet")
    if state.review_packet_complete and not state.flowguard_packet_complete:
        failures.append("Reviewer packet completed before FlowGuard packet")
    if state.validation_packet_complete and not state.review_packet_complete:
        failures.append("Validation packet completed before review packet")
    if state.closure_packet_complete and not state.validation_packet_complete:
        failures.append("Closure packet completed before validation packet")
    if state.terminal_status_checked and not state.closure_packet_complete:
        failures.append("Terminal status checked before closure packet")
    if state.route_nodes_materialized and not state.closure_packet_complete:
        failures.append("Route nodes materialized before PM planning packet closure")
    if state.route_node_1_complete and not state.route_nodes_materialized:
        failures.append("Route node 1 completed before route materialization")
    if state.route_node_2_complete and not state.route_node_1_complete:
        failures.append("Route node 2 completed before route node 1")
    if state.route_node_3_complete and not state.route_node_2_complete:
        failures.append("Route node 3 completed before route node 2")
    if state.final_route_wide_ledger_built and not state.route_node_3_complete:
        failures.append("Final route-wide ledger built before three route nodes completed")
    if state.terminal_status_checked and not state.final_route_wide_ledger_built:
        failures.append("Terminal status checked before final route-wide ledger")
    if state.wrong_role_recovery_completed and not state.wrong_role_lease_rejected:
        failures.append("Wrong-role recovery claimed before wrong-role rejection")
    if state.route_mutation_recovered and not state.terminal_status_checked:
        failures.append("Route mutation recovery claimed before normal recursive terminal path")
    if state.scenario_report_written and not (
        state.terminal_status_checked
        and state.wrong_role_recovery_completed
        and state.route_mutation_recovered
        and state.missing_ack_result_blocked
        and state.ack_only_wait_observed
        and state.retired_side_command_rejected
    ):
        failures.append("Rehearsal report written before normal and error scenarios completed")
    if state.internal_helper_only:
        failures.append("Rehearsal used an internal helper instead of the public CLI black box")
    if state.startup_body_leaked:
        failures.append("Public status leaked the sealed startup body")
    if state.result_body_leaked:
        failures.append("Public status leaked a sealed role result body")
    if state.wrong_role_lease_accepted:
        failures.append("Wrong-role lease was accepted against another role's packet")
    if state.missing_ack_result_accepted:
        failures.append("Missing-ACK result was accepted as authoritative")
    if state.ack_only_terminal:
        failures.append("ACK-only path reached terminal completion")
    if state.pm_only_terminal:
        failures.append("PM-only path reached terminal completion")
    if state.planning_chain_terminal:
        failures.append("Planning packet chain reached terminal completion before route nodes")
    if state.terminal_missing_route_node:
        failures.append("Terminal completion missed an effective route node")
    if state.route_mutation_without_frontier_rewrite:
        failures.append("Route mutation did not rewrite the execution frontier")
    if state.side_command_surface_available:
        failures.append("Retired side-command completion surface was still available")
    if state.terminal_active_lease:
        failures.append("Terminal status retained an active lease")
    if state.terminal_missing_role_packet:
        failures.append("Terminal status did not include all required role packets")
    if state.error_flow_unrecovered:
        failures.append("Observed error flow could not recover or expose a repair boundary")
    return failures


def is_success(state: State) -> bool:
    return state.status == "complete" and not invariant_failures(state)


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return state.status in {"complete", "blocked"}


def state_summary(state: State) -> dict[str, bool | str]:
    return dict(state.__dict__)


def target_state() -> State:
    state = initial_state()
    while True:
        transitions = next_safe_states(state)
        if not transitions:
            return state
        state = transitions[0].state


def hazard_states() -> dict[str, State]:
    target = target_state()
    return {
        "internal_helper_only": replace(target, internal_helper_only=True),
        "startup_body_leak": replace(target, startup_body_leaked=True),
        "result_body_leak": replace(target, result_body_leaked=True),
        "wrong_role_lease_accepted": replace(target, wrong_role_lease_accepted=True),
        "missing_ack_result_accepted": replace(target, missing_ack_result_accepted=True),
        "ack_only_terminal": replace(target, ack_only_terminal=True),
        "pm_only_terminal": replace(target, pm_only_terminal=True),
        "planning_chain_terminal": replace(target, planning_chain_terminal=True),
        "terminal_missing_route_node": replace(target, route_node_3_complete=False, terminal_missing_route_node=True),
        "route_mutation_without_frontier_rewrite": replace(target, route_mutation_without_frontier_rewrite=True),
        "side_command_surface_available": replace(target, side_command_surface_available=True),
        "terminal_active_lease": replace(target, terminal_active_lease=True),
        "terminal_missing_role_packet": replace(target, terminal_missing_role_packet=True),
        "error_flow_unrecovered": replace(target, error_flow_unrecovered=True),
    }


def build_workflow() -> Workflow:
    return Workflow(blocks=(FakeProjectRehearsalStep(),), name=MODEL_ID)


def _invariant(state: State, trace: object) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "blackbox_fake_project_rehearsal",
        "A fake project rehearsal must use the real startup and CLI packet lifecycle while separately proving error branches do not overclaim completion.",
        _invariant,
    ),
)
EXTERNAL_INPUTS = (Tick(),)
