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
    system_validation_recorded: bool = False
    system_closure_recorded: bool = False
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
    foreground_wait_patrol_observed: bool = False
    lifecycle_resume_rehydrated: bool = False
    lifecycle_patrol_recovery_classified: bool = False
    slow_live_reviewer_progress_preserved: bool = False
    accepted_packet_reassignment_rejected: bool = False
    nonterminal_guard_stop_blocked: bool = False
    scoped_closure_final_preflight_blocked: bool = False
    retired_side_command_rejected: bool = False
    scenario_report_written: bool = False
    internal_helper_only: bool = False
    startup_body_leaked: bool = False
    result_body_leaked: bool = False
    wrong_role_lease_accepted: bool = False
    missing_ack_result_accepted: bool = False
    ack_only_terminal: bool = False
    lifecycle_resume_from_chat: bool = False
    lifecycle_patrol_allows_nonterminal_stop: bool = False
    lifecycle_repeated_wait_not_recovered: bool = False
    slow_live_reviewer_replaced: bool = False
    accepted_packet_reassignment_allowed: bool = False
    foreground_final_preflight_missing: bool = False
    passive_wait_completed: bool = False
    scoped_closure_final_return_allowed: bool = False
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
    "record_system_validation_after_review",
    "record_system_closure_after_system_validation",
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
    "observe_foreground_wait_patrol_duty",
    "observe_lifecycle_resume_rehydration",
    "observe_lifecycle_patrol_recovery",
    "observe_slow_live_reviewer_progress_preserved",
    "observe_accepted_packet_reassignment_rejection",
    "observe_lifecycle_guard_blocks_nonterminal_stop",
    "observe_scoped_closure_final_preflight_block",
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
    if not state.system_validation_recorded:
        return (Transition("record_system_validation_after_review", replace(state, system_validation_recorded=True)),)
    if not state.system_closure_recorded:
        return (Transition("record_system_closure_after_system_validation", replace(state, system_closure_recorded=True)),)
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
    if not state.foreground_wait_patrol_observed:
        return (Transition("observe_foreground_wait_patrol_duty", replace(state, foreground_wait_patrol_observed=True)),)
    if not state.lifecycle_resume_rehydrated:
        return (Transition("observe_lifecycle_resume_rehydration", replace(state, lifecycle_resume_rehydrated=True)),)
    if not state.lifecycle_patrol_recovery_classified:
        return (Transition("observe_lifecycle_patrol_recovery", replace(state, lifecycle_patrol_recovery_classified=True)),)
    if not state.slow_live_reviewer_progress_preserved:
        return (
            Transition(
                "observe_slow_live_reviewer_progress_preserved",
                replace(state, slow_live_reviewer_progress_preserved=True),
            ),
        )
    if not state.accepted_packet_reassignment_rejected:
        return (
            Transition(
                "observe_accepted_packet_reassignment_rejection",
                replace(state, accepted_packet_reassignment_rejected=True),
            ),
        )
    if not state.nonterminal_guard_stop_blocked:
        return (Transition("observe_lifecycle_guard_blocks_nonterminal_stop", replace(state, nonterminal_guard_stop_blocked=True)),)
    if not state.scoped_closure_final_preflight_blocked:
        return (Transition("observe_scoped_closure_final_preflight_block", replace(state, scoped_closure_final_preflight_blocked=True)),)
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
    if state.system_validation_recorded and not state.review_packet_complete:
        failures.append("System validation recorded before review packet")
    if state.system_closure_recorded and not state.system_validation_recorded:
        failures.append("System closure recorded before system validation")
    if state.terminal_status_checked and not state.system_closure_recorded:
        failures.append("Terminal status checked before system closure")
    if state.route_nodes_materialized and not state.system_closure_recorded:
        failures.append("Route nodes materialized before PM planning system closure")
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
        and state.foreground_wait_patrol_observed
        and state.lifecycle_resume_rehydrated
        and state.lifecycle_patrol_recovery_classified
        and state.slow_live_reviewer_progress_preserved
        and state.accepted_packet_reassignment_rejected
        and state.nonterminal_guard_stop_blocked
        and state.scoped_closure_final_preflight_blocked
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
    if state.foreground_wait_patrol_observed and not state.ack_only_wait_observed:
        failures.append("Foreground wait patrol was observed before ACK-only wait")
    if state.lifecycle_resume_from_chat:
        failures.append("Lifecycle resume used chat history instead of current-run ledger")
    if state.lifecycle_patrol_allows_nonterminal_stop:
        failures.append("Lifecycle patrol allowed nonterminal Controller stop")
    if state.lifecycle_repeated_wait_not_recovered:
        failures.append("Lifecycle patrol failed to classify repeated wait as recovery")
    if state.slow_live_reviewer_replaced:
        failures.append("Slow live reviewer progress caused replacement instead of patrol wait")
    if state.accepted_packet_reassignment_allowed:
        failures.append("Accepted packet reassignment was allowed")
    if state.foreground_final_preflight_missing:
        failures.append("Foreground final-return preflight was missing from rehearsal")
    if state.passive_wait_completed:
        failures.append("Passive wait was treated as completion instead of foreground duty")
    if state.scoped_closure_final_return_allowed:
        failures.append("Scoped closure allowed final return while later work remained")
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
        "lifecycle_resume_from_chat": replace(target, lifecycle_resume_from_chat=True),
        "lifecycle_patrol_allows_nonterminal_stop": replace(target, lifecycle_patrol_allows_nonterminal_stop=True),
        "lifecycle_repeated_wait_not_recovered": replace(target, lifecycle_patrol_recovery_classified=False, lifecycle_repeated_wait_not_recovered=True),
        "slow_live_reviewer_replaced": replace(target, slow_live_reviewer_progress_preserved=False, slow_live_reviewer_replaced=True),
        "accepted_packet_reassignment_allowed": replace(target, accepted_packet_reassignment_rejected=False, accepted_packet_reassignment_allowed=True),
        "foreground_final_preflight_missing": replace(target, foreground_final_preflight_missing=True),
        "passive_wait_completed": replace(target, foreground_wait_patrol_observed=False, passive_wait_completed=True),
        "scoped_closure_final_return_allowed": replace(target, scoped_closure_final_preflight_blocked=False, scoped_closure_final_return_allowed=True),
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
