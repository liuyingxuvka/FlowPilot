"""FlowGuard model for FlowPilot route-authority singularity.

Risk purpose:
- FlowPilot Router must expose one current legal route-authority path at a
  time and reject wrong-path, wrong-role, old-alias, fallback/prose, stale, or
  no-delta repeat submissions with machine-readable repair feedback.
- Future agents should run
  `python simulations/run_flowpilot_route_authority_singularity_checks.py`
  before changing route-action policy rows, PM route movement events, control
  blocker repair feedback, synthetic agent replay, or model-mesh continuation
  claims.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_PM_SINGLE_PATH = "valid_pm_single_path"
VALID_REVIEWER_SINGLE_PATH = "valid_reviewer_single_path"
VALID_CORRECTED_RETRY = "valid_corrected_retry"

OWNER_MISSING = "owner_missing"
OWNER_CONFLICT = "owner_conflict"
LEGAL_ACTIONS_MISSING = "legal_actions_missing"
PM_WRONG_PATH_PARENT_CLOSURE = "pm_wrong_path_parent_closure"
WRONG_ROLE_ROUTE_ACTION = "wrong_role_route_action"
STALE_AUTHORITY_SNAPSHOT = "stale_authority_snapshot"
OLD_ALIAS_TRANSLATED = "old_alias_translated"
FALLBACK_PROSE_TRANSLATED = "fallback_prose_translated"
REJECTION_FEEDBACK_MISSING = "rejection_feedback_missing"
REPEATED_NO_DELTA_ACCEPTED = "repeated_no_delta_accepted"
MESH_GREEN_WITHOUT_AUTHORITY_EVIDENCE = "mesh_green_without_authority_evidence"

VALID_SCENARIOS = (
    VALID_PM_SINGLE_PATH,
    VALID_REVIEWER_SINGLE_PATH,
    VALID_CORRECTED_RETRY,
)
NEGATIVE_SCENARIOS = (
    OWNER_MISSING,
    OWNER_CONFLICT,
    LEGAL_ACTIONS_MISSING,
    PM_WRONG_PATH_PARENT_CLOSURE,
    WRONG_ROLE_ROUTE_ACTION,
    STALE_AUTHORITY_SNAPSHOT,
    OLD_ALIAS_TRANSLATED,
    FALLBACK_PROSE_TRANSLATED,
    REJECTION_FEEDBACK_MISSING,
    REPEATED_NO_DELTA_ACCEPTED,
    MESH_GREEN_WITHOUT_AUTHORITY_EVIDENCE,
)
SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    """One route-authority submission/rejection tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | selected | accepted | rejected
    scenario: str = "unset"

    authority_registry_present: bool = True
    legal_actions_computed: bool = True
    legal_actions_current: bool = True
    legal_action_ids_present: bool = True
    current_owner_present: bool = True
    current_owner_unique: bool = True
    current_owner: str = "project_manager"
    current_state_family_present: bool = True
    required_repair_command_present: bool = True

    submitted_action_id: str = "record_parent_segment_decision"
    submitted_role: str = "project_manager"
    submitted_action_in_legal_set: bool = True
    submitted_role_matches_owner: bool = True
    submitted_event_supported: bool = True
    old_alias_used: bool = False
    old_alias_translated_to_current_action: bool = False
    fallback_or_prose_payload: bool = False
    fallback_or_prose_translated_to_current_action: bool = False

    wrong_path_rejected: bool = False
    rejection_feedback_owner_present: bool = True
    rejection_feedback_legal_actions_present: bool = True
    rejection_feedback_forbidden_actions_present: bool = True
    rejection_feedback_repair_command_present: bool = True
    rejection_feedback_names_no_translation: bool = True

    repeated_submission_same_as_rejected: bool = False
    repeated_submission_blocked_as_same_family: bool = True
    corrected_retry_after_rejection: bool = False
    corrected_retry_uses_required_command: bool = True
    corrected_retry_action_in_legal_set: bool = True

    route_commit_attempted: bool = True
    mesh_authority_projection_available: bool = True
    mesh_green_claimed: bool = False
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class RouteAuthorityStep:
    """Classify one current route-authority scenario.

    Input x State -> Set(Output x State)
    reads: route action policy registry, legal next-action context, external
    event, payload shape, control blocker family, model-mesh projection
    writes: accepted route action or route-authority rejection
    idempotency: pure for current run id, route id/version, active node, and
    submitted event/action.
    """

    name = "RouteAuthorityStep"
    input_description = "FlowPilot route-authority submission tick"
    output_description = "one accepted or rejected route-authority state"
    reads = (
        "route_action_policy_registry",
        "legal_next_action_context",
        "external_event_payload",
        "control_blocker_family",
        "model_mesh_projection",
    )
    writes = ("route_authority_decision", "control_blocker")
    idempotency = "current run/route/node/action classification"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(output=Action(transition.label), new_state=transition.state, label=transition.label)


def _valid_pm_single_path() -> State:
    return State(
        status="selected",
        scenario=VALID_PM_SINGLE_PATH,
        submitted_action_id="record_parent_segment_decision",
        current_owner="project_manager",
        submitted_role="project_manager",
    )


def _valid_reviewer_single_path() -> State:
    return State(
        status="selected",
        scenario=VALID_REVIEWER_SINGLE_PATH,
        submitted_action_id="review_parent_backward_replay",
        current_owner="human_like_reviewer",
        submitted_role="human_like_reviewer",
    )


def _valid_corrected_retry() -> State:
    return State(
        status="selected",
        scenario=VALID_CORRECTED_RETRY,
        submitted_action_id="record_parent_segment_decision",
        current_owner="project_manager",
        submitted_role="project_manager",
        wrong_path_rejected=True,
        corrected_retry_after_rejection=True,
        corrected_retry_uses_required_command=True,
        corrected_retry_action_in_legal_set=True,
        route_commit_attempted=True,
    )


def _scenario_state(scenario: str) -> State:
    if scenario == VALID_PM_SINGLE_PATH:
        return _valid_pm_single_path()
    if scenario == VALID_REVIEWER_SINGLE_PATH:
        return _valid_reviewer_single_path()
    if scenario == VALID_CORRECTED_RETRY:
        return _valid_corrected_retry()

    state = _valid_pm_single_path()
    updates: dict[str, object] = {"scenario": scenario}
    if scenario == OWNER_MISSING:
        updates.update(current_owner_present=False, current_owner="owner_missing")
    elif scenario == OWNER_CONFLICT:
        updates.update(current_owner_unique=False, current_owner="owner_conflict")
    elif scenario == LEGAL_ACTIONS_MISSING:
        updates.update(legal_actions_computed=False, legal_action_ids_present=False)
    elif scenario == PM_WRONG_PATH_PARENT_CLOSURE:
        updates.update(
            submitted_action_id="complete_parent_node",
            submitted_action_in_legal_set=False,
            wrong_path_rejected=False,
        )
    elif scenario == WRONG_ROLE_ROUTE_ACTION:
        updates.update(
            current_owner="human_like_reviewer",
            submitted_role="project_manager",
            submitted_role_matches_owner=False,
            wrong_path_rejected=False,
        )
    elif scenario == STALE_AUTHORITY_SNAPSHOT:
        updates.update(legal_actions_current=False, route_commit_attempted=True)
    elif scenario == OLD_ALIAS_TRANSLATED:
        updates.update(
            submitted_event_supported=False,
            old_alias_used=True,
            old_alias_translated_to_current_action=True,
        )
    elif scenario == FALLBACK_PROSE_TRANSLATED:
        updates.update(
            fallback_or_prose_payload=True,
            fallback_or_prose_translated_to_current_action=True,
        )
    elif scenario == REJECTION_FEEDBACK_MISSING:
        updates.update(
            submitted_action_id="complete_parent_node",
            submitted_action_in_legal_set=False,
            wrong_path_rejected=True,
            rejection_feedback_owner_present=False,
            rejection_feedback_legal_actions_present=False,
            rejection_feedback_repair_command_present=False,
        )
    elif scenario == REPEATED_NO_DELTA_ACCEPTED:
        updates.update(
            submitted_action_id="complete_parent_node",
            submitted_action_in_legal_set=False,
            wrong_path_rejected=True,
            repeated_submission_same_as_rejected=True,
            repeated_submission_blocked_as_same_family=False,
        )
    elif scenario == MESH_GREEN_WITHOUT_AUTHORITY_EVIDENCE:
        updates.update(mesh_authority_projection_available=False, mesh_green_claimed=True)
    else:
        raise KeyError(f"unknown scenario: {scenario}")
    return replace(state, **updates)


def initial_state() -> State:
    return State()


def route_authority_failures(state: State) -> list[str]:
    failures: list[str] = []
    if not state.authority_registry_present:
        failures.append("route authority registry missing")
    if not state.legal_actions_computed or not state.legal_action_ids_present:
        failures.append("legal action ids missing from route authority snapshot")
    if not state.legal_actions_current:
        failures.append("stale route authority snapshot used")
    if not state.current_owner_present:
        failures.append("current owner missing from route authority snapshot")
    if not state.current_owner_unique:
        failures.append("route authority owner conflict")
    if not state.current_state_family_present:
        failures.append("current state family missing from route authority snapshot")
    if not state.required_repair_command_present:
        failures.append("required repair command missing from route authority snapshot")
    if state.submitted_role and not state.submitted_role_matches_owner:
        failures.append("submitted role does not match current route authority owner")
    if not state.submitted_action_in_legal_set:
        if not state.wrong_path_rejected:
            failures.append("wrong route path was not rejected")
        if state.wrong_path_rejected and not (
            state.rejection_feedback_owner_present
            and state.rejection_feedback_legal_actions_present
            and state.rejection_feedback_forbidden_actions_present
            and state.rejection_feedback_repair_command_present
            and state.rejection_feedback_names_no_translation
        ):
            failures.append("route authority rejection feedback missing repair fields")
    if state.old_alias_used and state.old_alias_translated_to_current_action:
        failures.append("unsupported old route-action alias was translated")
    if state.fallback_or_prose_payload and state.fallback_or_prose_translated_to_current_action:
        failures.append("fallback or prose route-action payload was translated")
    if state.repeated_submission_same_as_rejected and not state.repeated_submission_blocked_as_same_family:
        failures.append("repeated no-delta wrong-path submission was accepted")
    if state.corrected_retry_after_rejection and not (
        state.corrected_retry_uses_required_command and state.corrected_retry_action_in_legal_set
    ):
        failures.append("corrected retry did not return to the current legal route path")
    if state.route_commit_attempted and not state.legal_actions_current:
        failures.append("route commit used stale authority snapshot")
    if state.mesh_green_claimed and not state.mesh_authority_projection_available:
        failures.append("mesh green claim lacked route authority projection")
    return failures


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"accepted", "rejected"}:
        return ()
    if state.status == "new":
        return tuple(Transition(label=f"select_{scenario}", state=_scenario_state(scenario)) for scenario in SCENARIOS)
    failures = route_authority_failures(state)
    if failures:
        return (
            Transition(
                label=f"reject_{state.scenario}",
                state=replace(state, status="rejected", terminal_reason="; ".join(failures)),
            ),
        )
    return (
        Transition(
            label=f"accept_{state.scenario}",
            state=replace(state, status="accepted", terminal_reason="route_authority_valid"),
        ),
    )


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status == "accepted" and route_authority_failures(state):
        failures.append("accepted invalid route authority submission")
    if state.status == "accepted" and state.scenario not in VALID_SCENARIOS:
        failures.append("negative route-authority scenario was accepted")
    if state.status == "rejected" and state.scenario in VALID_SCENARIOS:
        failures.append("valid route-authority scenario was rejected")
    return failures


def _invariant(name: str, description: str) -> Invariant:
    def _predicate(state: State, _trace):
        failures = invariant_failures(state)
        if failures:
            return InvariantResult.fail("; ".join(failures))
        return InvariantResult.pass_()

    return Invariant(name=name, description=description, predicate=_predicate)


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return is_terminal(state)


def terminal_predicate(_input_obj: object, state: State, _trace: object) -> bool:
    return is_terminal(state)


def build_workflow() -> Workflow:
    return Workflow([RouteAuthorityStep()])


def hazard_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}


def intended_plan_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in VALID_SCENARIOS}


EXTERNAL_INPUTS = (Tick(),)
INVARIANTS = (
    _invariant(
        "route_authority_accepts_only_single_current_path",
        "Route-authority submissions must have one current owner, one legal action set, no alias/fallback translation, and repairable rejection feedback.",
    ),
)
MAX_SEQUENCE_LENGTH = 2
