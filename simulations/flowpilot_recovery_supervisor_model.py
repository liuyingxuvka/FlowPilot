"""FlowGuard model for FlowPilot Recovery Supervisor break-glass.

Risk purpose:
This model reviews the stronger break-glass architecture where ordinary
Controller progression is suspended, a temporary Recovery Supervisor identity
repairs same-family control-plane blockers under FlowGuard, and a fresh
Controller core is injected before normal route work resumes.

Run with:
    python simulations/run_flowpilot_recovery_supervisor_checks.py
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


SCENARIOS = (
    "metadata_only_control_plane_repair",
    "scoped_body_access_control_plane_repair",
)
MAX_SEQUENCE_LENGTH = 8


@dataclass(frozen=True)
class Tick:
    """One Recovery Supervisor transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    scenario: str = "none"
    status: str = "new"  # new | failed | recovery_open | diagnosed | repaired | reinjected | closed | normal

    normal_controller_active: bool = True
    recovery_supervisor_active: bool = False
    recovery_transaction_open: bool = False
    control_plane_blocker_recorded: bool = False
    blocker_family_classified: bool = False
    current_open_blockers_resolved_or_quarantined: bool = False
    historical_blockers_used_as_regression: bool = False
    flowguard_same_family_proof_recorded: bool = False

    role_lanes_unavailable: bool = False
    body_access_needed: bool = False
    scoped_body_access_grant_recorded: bool = False
    normal_controller_read_body: bool = False
    recovery_supervisor_read_unscoped_body: bool = False
    body_access_review_required: bool = False

    old_controller_generation_invalidated: bool = False
    controller_core_reinjected: bool = False
    returned_to_normal_controller: bool = False

    route_gate_approved_by_recovery: bool = False
    route_mutated_by_recovery: bool = False
    target_project_work_done_by_recovery: bool = False
    historical_blocker_reactivated_as_current: bool = False


class Transition(NamedTuple):
    label: str
    state: State


class RecoverySupervisorStep:
    """Model the Recovery Supervisor lifecycle.

    Input x State -> Set(Output x State)
    reads: Controller action ledger, Router daemon status, control blocker
    ledger, optional scoped body grant, Controller core manifest/hash.
    writes: recovery transaction, blocker family ledger, body-access grant,
    FlowGuard proof refs, Controller reinjection record.
    idempotency: transaction id and Controller generation prevent older
    blockers or old Controller state from becoming current authority again.
    """

    name = "RecoverySupervisorStep"
    reads = (
        "controller_action_ledger",
        "router_daemon_status",
        "control_plane_blocker_ledger",
        "body_access_grants",
        "controller_core_manifest",
    )
    writes = (
        "recovery_transaction",
        "control_plane_blocker_ledger",
        "flowguard_same_family_proof",
        "controller_reinjection",
    )
    input_description = "one break-glass recovery tick"
    output_description = "recovery transaction progress or restored normal Controller"
    idempotency = "transaction ids and controller generations bound recovery closure"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(output=Action(transition.label), new_state=transition.state, label=transition.label)


def initial_state() -> State:
    return State()


def _scenario_state(name: str) -> State:
    return State(
        scenario=name,
        status="failed",
        normal_controller_active=True,
        recovery_supervisor_active=False,
        role_lanes_unavailable=name == "scoped_body_access_control_plane_repair",
        body_access_needed=name == "scoped_body_access_control_plane_repair",
    )


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status == "normal":
        return ()
    if policy_failures(state) and state.status != "new":
        return ()
    if state.status == "new":
        return tuple(Transition(f"select_{scenario}", _scenario_state(scenario)) for scenario in SCENARIOS)
    if state.status == "failed":
        return (
            Transition(
                f"open_recovery_transaction_{state.scenario}",
                replace(
                    state,
                    status="recovery_open",
                    normal_controller_active=False,
                    recovery_supervisor_active=True,
                    recovery_transaction_open=True,
                    control_plane_blocker_recorded=True,
                ),
            ),
        )
    if state.status == "recovery_open":
        if state.body_access_needed:
            return (
                Transition(
                    f"grant_scoped_body_access_{state.scenario}",
                    replace(
                        state,
                        status="diagnosed",
                        scoped_body_access_grant_recorded=True,
                        body_access_review_required=True,
                        blocker_family_classified=True,
                    ),
                ),
            )
        return (
            Transition(
                f"classify_family_from_metadata_{state.scenario}",
                replace(state, status="diagnosed", blocker_family_classified=True),
            ),
        )
    if state.status == "diagnosed":
        return (
            Transition(
                f"record_same_family_repair_{state.scenario}",
                replace(
                    state,
                    status="repaired",
                    current_open_blockers_resolved_or_quarantined=True,
                    historical_blockers_used_as_regression=True,
                    flowguard_same_family_proof_recorded=True,
                ),
            ),
        )
    if state.status == "repaired":
        return (
            Transition(
                f"reinject_controller_core_{state.scenario}",
                replace(
                    state,
                    status="reinjected",
                    old_controller_generation_invalidated=True,
                    controller_core_reinjected=True,
                ),
            ),
        )
    if state.status == "reinjected":
        return (
            Transition(
                f"close_recovery_transaction_{state.scenario}",
                replace(
                    state,
                    status="closed",
                    recovery_transaction_open=False,
                    recovery_supervisor_active=False,
                ),
            ),
        )
    if state.status == "closed":
        return (
            Transition(
                f"return_to_normal_controller_{state.scenario}",
                replace(state, status="normal", normal_controller_active=True, returned_to_normal_controller=True),
            ),
        )
    return ()


def policy_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.normal_controller_active and state.recovery_supervisor_active:
        failures.append("normal Controller and Recovery Supervisor were active at the same time")
    if state.recovery_supervisor_active and state.normal_controller_active:
        failures.append("Recovery Supervisor opened without suspending normal Controller")
    if state.normal_controller_read_body:
        failures.append("normal Controller read a sealed body")
    if state.recovery_supervisor_read_unscoped_body:
        failures.append("Recovery Supervisor read a body without a scoped grant")
    if state.scoped_body_access_grant_recorded and not (
        state.role_lanes_unavailable and state.body_access_needed
    ):
        failures.append("scoped body access grant opened without role-lane failure and need")
    if state.body_access_needed and state.status in {"diagnosed", "repaired", "reinjected", "closed", "normal"}:
        if not (state.scoped_body_access_grant_recorded and state.body_access_review_required):
            failures.append("body-needed recovery progressed without scoped grant and review obligation")
    if state.status in {"repaired", "reinjected", "closed", "normal"}:
        if not (
            state.control_plane_blocker_recorded
            and state.blocker_family_classified
            and state.current_open_blockers_resolved_or_quarantined
            and state.historical_blockers_used_as_regression
            and state.flowguard_same_family_proof_recorded
        ):
            failures.append("recovery progressed before blocker family repair proof was complete")
    if state.status in {"closed", "normal"}:
        if not (state.old_controller_generation_invalidated and state.controller_core_reinjected):
            failures.append("recovery closed before Controller core reinjection")
    if state.returned_to_normal_controller and state.recovery_transaction_open:
        failures.append("normal Controller resumed while recovery transaction was still open")
    if state.returned_to_normal_controller and not state.controller_core_reinjected:
        failures.append("normal Controller resumed without fresh Controller core")
    if state.route_gate_approved_by_recovery:
        failures.append("Recovery Supervisor approved a route gate")
    if state.route_mutated_by_recovery:
        failures.append("Recovery Supervisor mutated route authority")
    if state.target_project_work_done_by_recovery:
        failures.append("Recovery Supervisor performed target project work")
    if state.historical_blocker_reactivated_as_current:
        failures.append("historical blocker was reactivated as current instead of used as regression evidence")
    return failures


def invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = policy_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_recovery_supervisor_identity_and_reentry",
        description=(
            "Recovery Supervisor suspends normal Controller, repairs same-family "
            "control-plane blockers with FlowGuard evidence, grants body access "
            "only when scoped and needed, reinjects Controller core, and then "
            "returns to normal Controller flow."
        ),
        predicate=invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((RecoverySupervisorStep(),), name="flowpilot_recovery_supervisor")


def is_terminal(state: State) -> bool:
    return state.status == "normal" or bool(policy_failures(state))


def is_success(state: State) -> bool:
    return state.status == "normal"


def _valid_normal_state() -> State:
    return State(
        scenario="metadata_only_control_plane_repair",
        status="normal",
        normal_controller_active=True,
        recovery_supervisor_active=False,
        recovery_transaction_open=False,
        control_plane_blocker_recorded=True,
        blocker_family_classified=True,
        current_open_blockers_resolved_or_quarantined=True,
        historical_blockers_used_as_regression=True,
        flowguard_same_family_proof_recorded=True,
        old_controller_generation_invalidated=True,
        controller_core_reinjected=True,
        returned_to_normal_controller=True,
    )


def hazard_states() -> dict[str, State]:
    base = _valid_normal_state()
    return {
        "normal_controller_reads_body": replace(base, normal_controller_read_body=True),
        "recovery_reads_unscoped_body": replace(base, recovery_supervisor_read_unscoped_body=True),
        "body_access_without_role_lane_failure": replace(
            base,
            scoped_body_access_grant_recorded=True,
            body_access_needed=True,
            role_lanes_unavailable=False,
            recovery_transaction_open=True,
        ),
        "closed_without_family_repair": replace(base, flowguard_same_family_proof_recorded=False),
        "closed_without_reinjection": replace(base, controller_core_reinjected=False),
        "normal_resumed_with_open_transaction": replace(base, recovery_transaction_open=True),
        "historical_blocker_reactivated": replace(base, historical_blocker_reactivated_as_current=True),
        "recovery_approved_gate": replace(base, route_gate_approved_by_recovery=True),
        "recovery_mutated_route": replace(base, route_mutated_by_recovery=True),
        "recovery_did_target_project_work": replace(base, target_project_work_done_by_recovery=True),
    }


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "SCENARIOS",
    "State",
    "Tick",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "policy_failures",
]
