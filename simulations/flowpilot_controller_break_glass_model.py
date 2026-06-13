"""FlowGuard model for Controller break-glass repair authority.

The model keeps the development-mode emergency lane narrow: it can only open
for FlowPilot control-plane failures after normal repair lanes are checked, and
it cannot become ordinary Controller self-repair, sealed-body access, gate
approval, route mutation, or hidden temporary patching.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_SCENARIOS = (
    "control_flow_stuck_no_legal_next_action",
    "event_authority_contradiction",
    "pm_packet_repair_lane_broken",
    "non_replayable_package_artifact_blocks_packet_replay",
    "repair_loop_threshold_control_fault",
    "repair_loop_threshold_false_alarm",
)
NEGATIVE_SCENARIOS = (
    "ordinary_project_bug",
    "normal_pm_repair_available",
    "cross_node_similar_failures",
)
SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS
PATCH_SCENARIOS = {"control_flow_stuck_no_legal_next_action", "repair_loop_threshold_control_fault"}
MAX_SEQUENCE_LENGTH = 9


@dataclass(frozen=True)
class Tick:
    """One Controller break-glass policy transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    scenario: str = "none"
    status: str = "new"  # new | assessed | incident_open | patch_recorded | patch_validated | returned | disclosed | accepted | rejected
    flowpilot_control_failure: bool = False
    ordinary_project_defect: bool = False
    normal_repair_available: bool = False
    normal_lanes_checked: bool = False
    repair_loop_threshold_exceeded: bool = False
    repair_loop_threshold_false_alarm: bool = False
    package_artifact_not_replayable: bool = False
    playbook_read: bool = False
    incident_recorded: bool = False
    recovery_transaction_recorded: bool = False
    patch_used: bool = False
    patch_recorded: bool = False
    patch_validation_status: str = "none"  # none | pending | passed | blocked | quarantined | not_run
    returned_to_normal_flow: bool = False
    final_disclosed: bool = False

    controller_read_sealed_body: bool = False
    controller_did_target_project_work: bool = False
    controller_approved_gate: bool = False
    controller_mutated_route: bool = False
    controller_changed_acceptance: bool = False
    controller_published_or_deployed: bool = False
    controller_handled_secret: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


class BreakGlassStep:
    """Model Controller break-glass repair.

    Input x State -> Set(Output x State)
    reads: daemon status, Controller action ledger, blocker metadata, prompt and
    contract registries, incident/patch ledgers.
    writes: break-glass incident/patch records and return-to-normal markers.
    idempotency: repeated assessment can reject or reopen the same incident, but
    cannot create route evidence or role approvals.
    """

    name = "ControllerBreakGlassStep"
    reads = (
        "router_daemon_status",
        "controller_action_ledger",
        "control_blocker_metadata",
        "manifest_contract_registry",
        "break_glass_ledger",
    )
    writes = ("break_glass_incident", "break_glass_patch", "return_to_normal_marker")
    input_description = "Controller control-plane recovery tick"
    output_description = "break-glass decision, record, validation, or rejection"
    idempotency = "records are scoped by incident id and do not approve gates"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def _scenario_state(name: str) -> State:
    if name in VALID_SCENARIOS:
        return State(
            scenario=name,
            status="assessed",
            flowpilot_control_failure=True,
            ordinary_project_defect=False,
            normal_repair_available=False,
            normal_lanes_checked=True,
            repair_loop_threshold_exceeded=name.startswith("repair_loop_threshold"),
            repair_loop_threshold_false_alarm=name == "repair_loop_threshold_false_alarm",
            package_artifact_not_replayable=name == "non_replayable_package_artifact_blocks_packet_replay",
            patch_used=name in PATCH_SCENARIOS,
        )
    return State(
        scenario=name,
        status="assessed",
        flowpilot_control_failure=False,
        ordinary_project_defect=name == "ordinary_project_bug",
        normal_repair_available=name in {"normal_pm_repair_available", "cross_node_similar_failures"},
        normal_lanes_checked=True,
    )


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"accepted", "rejected"}:
        return ()
    failures = policy_failures(state)
    if failures and state.status != "new":
        return (Transition(f"reject_{state.scenario}", replace(state, status="rejected")),)
    if state.status == "new":
        return tuple(Transition(f"select_{name}", _scenario_state(name)) for name in SCENARIOS)
    if state.status == "assessed":
        if state.scenario in NEGATIVE_SCENARIOS:
            return (Transition(f"reject_{state.scenario}", replace(state, status="rejected")),)
        return (
            Transition(
                f"open_incident_{state.scenario}",
                replace(
                    state,
                    status="incident_open",
                    playbook_read=True,
                    incident_recorded=True,
                    recovery_transaction_recorded=True,
                ),
            ),
        )
    if state.status == "incident_open":
        if state.patch_used and not state.patch_recorded:
            return (
                Transition(
                    f"record_patch_{state.scenario}",
                    replace(
                        state,
                        status="patch_recorded",
                        patch_recorded=True,
                        patch_validation_status="pending",
                    ),
                ),
            )
        return (
            Transition(
                f"return_to_normal_{state.scenario}",
                replace(state, status="returned", returned_to_normal_flow=True),
            ),
        )
    if state.status == "patch_recorded":
        return (
            Transition(
                f"record_patch_validation_{state.scenario}",
                replace(state, status="patch_validated", patch_validation_status="passed"),
            ),
        )
    if state.status == "patch_validated":
        return (
            Transition(
                f"return_to_normal_{state.scenario}",
                replace(state, status="returned", returned_to_normal_flow=True),
            ),
        )
    if state.status == "returned":
        return (
            Transition(
                f"disclose_break_glass_{state.scenario}",
                replace(state, status="disclosed", final_disclosed=True),
            ),
        )
    if state.status == "disclosed":
        return (Transition(f"accept_{state.scenario}", replace(state, status="accepted")),)
    return ()


def policy_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.controller_read_sealed_body:
        failures.append("Controller break-glass read a sealed packet or result body")
    if state.controller_did_target_project_work:
        failures.append("Controller break-glass performed target-project work")
    if state.controller_approved_gate:
        failures.append("Controller break-glass approved a gate")
    if state.controller_mutated_route:
        failures.append("Controller break-glass mutated the route")
    if state.controller_changed_acceptance:
        failures.append("Controller break-glass changed acceptance criteria")
    if state.controller_published_or_deployed:
        failures.append("Controller break-glass published or deployed")
    if state.controller_handled_secret:
        failures.append("Controller break-glass handled secrets or private account data")
    if state.status in {"incident_open", "patch_recorded", "patch_validated", "returned", "disclosed", "accepted"}:
        if not state.playbook_read:
            failures.append("break-glass opened without reading the playbook")
        if not state.normal_lanes_checked:
            failures.append("break-glass opened before normal repair lanes were checked")
        if not state.flowpilot_control_failure:
            failures.append("break-glass opened without a FlowPilot control-plane failure")
        if state.ordinary_project_defect:
            failures.append("ordinary project defect used break-glass")
        if state.normal_repair_available:
            failures.append("normal PM repair lane was available but break-glass was used")
        if state.repair_loop_threshold_exceeded and not state.normal_lanes_checked:
            failures.append("repair loop threshold break-glass lacked normal lane assessment")
        if not state.incident_recorded:
            failures.append("break-glass used without an incident record")
        if not state.recovery_transaction_recorded:
            failures.append("break-glass closure lacked a recovery transaction or explicit blocked/quarantined disposition")
    if state.patch_used and state.status in {"returned", "disclosed", "accepted"} and not state.patch_recorded:
        failures.append("temporary break-glass patch was used without a patch record")
    if state.patch_used and state.status in {"returned", "disclosed", "accepted"}:
        if state.patch_validation_status not in {"passed", "blocked", "quarantined"}:
            failures.append("break-glass patch returned to normal flow without closed validation, blocked, or quarantined disposition")
        if state.patch_validation_status == "not_run":
            failures.append("break-glass patch validation stayed not_run")
    if state.status in {"disclosed", "accepted"} and not state.returned_to_normal_flow:
        failures.append("break-glass did not return to normal Controller flow")
    if state.status == "accepted" and not state.final_disclosed:
        failures.append("break-glass use was not disclosed in final reporting")
    return failures


def break_glass_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = policy_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_controller_break_glass_authority",
        description=(
            "Controller break-glass is limited to FlowPilot control-plane "
            "failures, records incident/patch evidence, returns to normal flow, "
            "and never grants sealed-body, gate, route, project, release, or "
            "secret-handling powers."
        ),
        predicate=break_glass_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((BreakGlassStep(),), name="flowpilot_controller_break_glass")


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted"


def _accepted_valid_state() -> State:
    return State(
        scenario="control_flow_stuck_no_legal_next_action",
        status="accepted",
        flowpilot_control_failure=True,
        normal_lanes_checked=True,
        playbook_read=True,
        incident_recorded=True,
        recovery_transaction_recorded=True,
        patch_used=True,
        patch_recorded=True,
        patch_validation_status="passed",
        returned_to_normal_flow=True,
        final_disclosed=True,
    )


def hazard_states() -> dict[str, State]:
    base = _accepted_valid_state()
    return {
        "ordinary_project_bug_break_glass": replace(base, ordinary_project_defect=True, flowpilot_control_failure=False),
        "normal_pm_repair_available_break_glass": replace(base, normal_repair_available=True),
        "missing_normal_lane_check": replace(base, normal_lanes_checked=False),
        "missing_playbook_read": replace(base, playbook_read=False),
        "missing_incident_record": replace(base, incident_recorded=False),
        "missing_recovery_transaction": replace(base, recovery_transaction_recorded=False),
        "missing_patch_record": replace(base, patch_recorded=False),
        "missing_patch_validation": replace(base, patch_validation_status="pending"),
        "patch_validation_not_run": replace(base, patch_validation_status="not_run"),
        "missing_return_to_normal": replace(base, returned_to_normal_flow=False),
        "missing_final_disclosure": replace(base, final_disclosed=False),
        "controller_reads_sealed_body": replace(base, controller_read_sealed_body=True),
        "controller_does_project_work": replace(base, controller_did_target_project_work=True),
        "controller_approves_gate": replace(base, controller_approved_gate=True),
        "controller_mutates_route": replace(base, controller_mutated_route=True),
        "controller_changes_acceptance": replace(base, controller_changed_acceptance=True),
        "controller_publishes": replace(base, controller_published_or_deployed=True),
        "controller_handles_secret": replace(base, controller_handled_secret=True),
    }


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "NEGATIVE_SCENARIOS",
    "PATCH_SCENARIOS",
    "SCENARIOS",
    "VALID_SCENARIOS",
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
