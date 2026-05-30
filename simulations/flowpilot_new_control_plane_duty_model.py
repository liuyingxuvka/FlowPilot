"""FlowGuard model for the new FlowPilot control-plane duty repair.

Risk intent:
- Reuse the old FlowPilot split between fast Router/black-box internal ticks
  and slower foreground role-wait patrols.
- Keep internal mechanical packet issuance behind a public run-until-wait fold
  so Controller stops only at a durable boundary.
- Prevent read-only status from becoming a hidden writer.
- Prevent PM repair decisions from being inferred from hostile prose.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_new_control_plane_duty"
MAX_SEQUENCE_LENGTH = 13


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | complete | blocked
    old_patrol_logic_checked: bool = False
    action_classes_declared: bool = False
    router_internal_whitelist_declared: bool = False
    internal_actions_folded_to_boundary: bool = False
    internal_tick_seconds: int = 1
    role_wait_patrol_seconds: int = 60
    role_wait_patrol_preserved: bool = False
    status_is_read_only: bool = False
    structured_pm_decision_required: bool = False
    hostile_prose_ignored: bool = False
    missing_pm_decision_blocked: bool = False
    pm_stop_blocks_route: bool = False
    fake_e2e_uses_public_fold: bool = False
    focused_tests_current: bool = False
    internal_action_exposed_to_controller: bool = False
    status_mutates_ledger: bool = False
    hostile_prose_controls_decision: bool = False
    stopped_blocker_route_continues: bool = False
    external_wait_uses_internal_tick: bool = False


@dataclass(frozen=True)
class Tick:
    """One control-plane repair transition."""


@dataclass(frozen=True)
class Action:
    label: str


class Transition(NamedTuple):
    label: str
    state: State


REQUIRED_SAFE_LABELS = (
    "read_old_patrol_and_daemon_tick_logic",
    "declare_runtime_action_classes",
    "declare_router_internal_whitelist",
    "fold_internal_actions_until_boundary",
    "preserve_sixty_second_role_wait_patrol",
    "make_status_projection_read_only",
    "require_structured_pm_repair_decision",
    "block_missing_pm_repair_decision",
    "stop_for_user_pauses_route",
    "route_fake_e2e_through_public_fold",
    "add_focused_regression_tests",
    "complete_control_plane_duty_repair",
)


def initial_state() -> State:
    return State()


class ControlPlaneDutyStep:
    name = "FlowPilotNewControlPlaneDutyStep"
    input_description = "one control-plane duty repair tick"
    output_description = "one ordered model-safe repair step"
    reads = ("old_router_patrol_contract", "new_runtime_ledger", "pm_repair_packet_contract")
    writes = ("runtime_action_classifier", "run_until_wait_fold", "foreground_duty_contract", "tests")
    idempotency = "safe transitions only add current evidence or stricter gates"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(output=Action(transition.label), new_state=transition.state, label=transition.label)


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"blocked", "complete"}:
        return ()
    failures = invariant_failures(state)
    if failures:
        return (Transition("blocked_on_control_plane_invariant", replace(state, status="blocked")),)
    if state.status == "new":
        return (Transition("read_old_patrol_and_daemon_tick_logic", replace(state, status="running", old_patrol_logic_checked=True)),)
    if not state.action_classes_declared:
        return (Transition("declare_runtime_action_classes", replace(state, action_classes_declared=True)),)
    if not state.router_internal_whitelist_declared:
        return (Transition("declare_router_internal_whitelist", replace(state, router_internal_whitelist_declared=True)),)
    if not state.internal_actions_folded_to_boundary:
        return (Transition("fold_internal_actions_until_boundary", replace(state, internal_actions_folded_to_boundary=True)),)
    if not state.role_wait_patrol_preserved:
        return (Transition("preserve_sixty_second_role_wait_patrol", replace(state, role_wait_patrol_preserved=True)),)
    if not state.status_is_read_only:
        return (Transition("make_status_projection_read_only", replace(state, status_is_read_only=True)),)
    if not state.structured_pm_decision_required:
        return (Transition("require_structured_pm_repair_decision", replace(state, structured_pm_decision_required=True, hostile_prose_ignored=True)),)
    if not state.missing_pm_decision_blocked:
        return (Transition("block_missing_pm_repair_decision", replace(state, missing_pm_decision_blocked=True)),)
    if not state.pm_stop_blocks_route:
        return (Transition("stop_for_user_pauses_route", replace(state, pm_stop_blocks_route=True)),)
    if not state.fake_e2e_uses_public_fold:
        return (Transition("route_fake_e2e_through_public_fold", replace(state, fake_e2e_uses_public_fold=True)),)
    if not state.focused_tests_current:
        return (Transition("add_focused_regression_tests", replace(state, focused_tests_current=True)),)
    return (Transition("complete_control_plane_duty_repair", replace(state, status="complete")),)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.action_classes_declared and not state.old_patrol_logic_checked:
        failures.append("new action classes were declared before checking old patrol/tick logic")
    if state.internal_actions_folded_to_boundary and not (
        state.action_classes_declared and state.router_internal_whitelist_declared
    ):
        failures.append("internal folding needs action classes and a whitelist")
    if state.internal_actions_folded_to_boundary and state.internal_action_exposed_to_controller:
        failures.append("router-internal action leaked to Controller instead of folding to a boundary")
    if state.role_wait_patrol_preserved and state.role_wait_patrol_seconds != 60:
        failures.append("role wait patrol cadence changed away from 60 seconds")
    if state.role_wait_patrol_preserved and state.internal_tick_seconds != 1:
        failures.append("black-box/internal tick cadence changed away from 1 second")
    if state.external_wait_uses_internal_tick:
        failures.append("external role wait reused the 1 second internal tick")
    if state.status_is_read_only and state.status_mutates_ledger:
        failures.append("status projection still mutates the ledger")
    if state.structured_pm_decision_required and state.hostile_prose_controls_decision:
        failures.append("PM repair decision can still be controlled by prose")
    if state.structured_pm_decision_required and not state.hostile_prose_ignored:
        failures.append("structured PM parser does not prove hostile prose is ignored")
    if state.pm_stop_blocks_route and state.stopped_blocker_route_continues:
        failures.append("stopped PM blocker still allows route progress")
    if state.status == "complete" and not is_success(state):
        failures.append("completion claimed before all repair obligations were satisfied")
    return failures


def invariant(state: State, trace: object) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="control_plane_duty_invariants",
        description=(
            "New FlowPilot control-plane duty must reuse the old 1s internal tick "
            "and 60s foreground patrol split, fold safe internals to a boundary, "
            "keep status read-only, and require structured PM repair decisions."
        ),
        predicate=invariant,
    ),
)
EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((ControlPlaneDutyStep(),), name=MODEL_ID)


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return state.status in {"complete", "blocked"}


def is_success(state: State) -> bool:
    return (
        state.status == "complete"
        and state.old_patrol_logic_checked
        and state.action_classes_declared
        and state.router_internal_whitelist_declared
        and state.internal_actions_folded_to_boundary
        and state.internal_tick_seconds == 1
        and state.role_wait_patrol_seconds == 60
        and state.role_wait_patrol_preserved
        and state.status_is_read_only
        and state.structured_pm_decision_required
        and state.hostile_prose_ignored
        and state.missing_pm_decision_blocked
        and state.pm_stop_blocks_route
        and state.fake_e2e_uses_public_fold
        and state.focused_tests_current
    )


def hazard_states() -> dict[str, State]:
    target = target_state()
    return {
        "internal_action_exposed_to_controller": replace(target, internal_action_exposed_to_controller=True),
        "status_mutates_ledger": replace(target, status_mutates_ledger=True),
        "hostile_prose_controls_decision": replace(target, hostile_prose_controls_decision=True),
        "stopped_blocker_route_continues": replace(target, stopped_blocker_route_continues=True),
        "external_wait_uses_internal_tick": replace(target, external_wait_uses_internal_tick=True),
        "wrong_role_wait_patrol_seconds": replace(target, role_wait_patrol_seconds=1),
    }


def target_state() -> State:
    return State(
        status="complete",
        old_patrol_logic_checked=True,
        action_classes_declared=True,
        router_internal_whitelist_declared=True,
        internal_actions_folded_to_boundary=True,
        role_wait_patrol_preserved=True,
        status_is_read_only=True,
        structured_pm_decision_required=True,
        hostile_prose_ignored=True,
        missing_pm_decision_blocked=True,
        pm_stop_blocks_route=True,
        fake_e2e_uses_public_fold=True,
        focused_tests_current=True,
    )


def state_summary(state: State) -> dict[str, object]:
    return {
        "status": state.status,
        "internal_tick_seconds": state.internal_tick_seconds,
        "role_wait_patrol_seconds": state.role_wait_patrol_seconds,
        "internal_actions_folded_to_boundary": state.internal_actions_folded_to_boundary,
        "status_is_read_only": state.status_is_read_only,
        "structured_pm_decision_required": state.structured_pm_decision_required,
        "pm_stop_blocks_route": state.pm_stop_blocks_route,
    }
