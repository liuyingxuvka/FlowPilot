"""FlowGuard model for FlowPilot Router reconciliation branch pruning.

Risk intent brief:
- Reduce Router reconciliation bug risk by making complex branch families map
  to a small result-case vocabulary before runtime code is contracted.
- Keep state-writing branches separate until replay or model-test evidence
  proves the observable state writes and side effects are equivalent.
- Preserve dynamic role-output event authority and runtime-state ownership
  boundaries while planning structure simplification.
- Treat background progress logs as liveness only; completion claims require
  exit-bearing artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


RESULT_CASES = (
    "noop",
    "reconciled",
    "superseded",
    "replay_required",
    "retry_pending",
    "repair_pending",
    "blocked",
)

SCHEDULED_RECEIPT_SURFACE = "scheduled_controller_receipt"
ROLE_OUTPUT_SURFACE = "role_output_event"
RUNTIME_STATE_SURFACE = "runtime_state_resume"
BACKGROUND_VALIDATION_SURFACE = "background_validation"

SCHEDULED_NO_ACTION_DIR = "scheduled_no_action_dir"
SCHEDULED_INVALID_SCHEMA = "scheduled_invalid_schema"
SCHEDULED_LEGACY_STARTUP_CANONICAL = "scheduled_legacy_startup_canonical"
SCHEDULED_ROW_RECONCILIATION = "scheduled_row_reconciliation"
SCHEDULED_CURRENT_SCOPE_RESOLVED = "scheduled_current_scope_resolved"
SCHEDULED_CARD_RETURN_RESOLVED = "scheduled_card_return_resolved"
SCHEDULED_ALREADY_RECONCILED_WAIT_TARGET_REPLAY = (
    "scheduled_already_reconciled_wait_target_replay"
)
SCHEDULED_RECONCILED_POSTCONDITION_REPAIR_PENDING = (
    "scheduled_reconciled_postcondition_repair_pending"
)
SCHEDULED_RECONCILED_POSTCONDITION_RETRY_PENDING = (
    "scheduled_reconciled_postcondition_retry_pending"
)
SCHEDULED_RECEIPT_APPLY_BLOCKED = "scheduled_receipt_apply_blocked"
SCHEDULED_BLOCKED_ROLE_RECOVERY_RECLAIM = "scheduled_blocked_role_recovery_reclaim"

ROLE_OUTPUT_INVALID_ENVELOPE = "role_output_invalid_envelope"
ROLE_OUTPUT_NOT_READY_REQUIRED_FLAG = "role_output_not_ready_required_flag"
ROLE_OUTPUT_UNAUTHORIZED = "role_output_unauthorized"
ROLE_OUTPUT_ALREADY_RECORDED = "role_output_already_recorded"
ROLE_OUTPUT_VALID_DIRECT_EVENT = "role_output_valid_direct_event"

RUNTIME_PACKET_NO_ACTIVE = "runtime_packet_no_active"
RUNTIME_PACKET_WITH_CONTROLLER = "runtime_packet_with_controller"
RUNTIME_PACKET_RESULT_NEEDS_PM = "runtime_packet_result_needs_pm"
RUNTIME_PACKET_SUPERSEDED = "runtime_packet_superseded"
RUNTIME_PACKET_NONSTANDARD_STATUS = "runtime_packet_nonstandard_status"

OVERCLAIM_BRANCH_EQUIVALENCE = "overclaim_branch_equivalence"
MISSING_EVENT_AUTHORITY = "missing_event_authority"
DUPLICATE_RUNTIME_STATE_OWNER = "duplicate_runtime_state_owner"
PROGRESS_ONLY_VALIDATION = "progress_only_validation"

VALID_SCENARIOS = (
    SCHEDULED_NO_ACTION_DIR,
    SCHEDULED_INVALID_SCHEMA,
    SCHEDULED_LEGACY_STARTUP_CANONICAL,
    SCHEDULED_ROW_RECONCILIATION,
    SCHEDULED_CURRENT_SCOPE_RESOLVED,
    SCHEDULED_CARD_RETURN_RESOLVED,
    SCHEDULED_ALREADY_RECONCILED_WAIT_TARGET_REPLAY,
    SCHEDULED_RECONCILED_POSTCONDITION_REPAIR_PENDING,
    SCHEDULED_RECONCILED_POSTCONDITION_RETRY_PENDING,
    SCHEDULED_RECEIPT_APPLY_BLOCKED,
    SCHEDULED_BLOCKED_ROLE_RECOVERY_RECLAIM,
    ROLE_OUTPUT_INVALID_ENVELOPE,
    ROLE_OUTPUT_NOT_READY_REQUIRED_FLAG,
    ROLE_OUTPUT_UNAUTHORIZED,
    ROLE_OUTPUT_ALREADY_RECORDED,
    ROLE_OUTPUT_VALID_DIRECT_EVENT,
    RUNTIME_PACKET_NO_ACTIVE,
    RUNTIME_PACKET_WITH_CONTROLLER,
    RUNTIME_PACKET_RESULT_NEEDS_PM,
    RUNTIME_PACKET_SUPERSEDED,
    RUNTIME_PACKET_NONSTANDARD_STATUS,
)

NEGATIVE_SCENARIOS = (
    OVERCLAIM_BRANCH_EQUIVALENCE,
    MISSING_EVENT_AUTHORITY,
    DUPLICATE_RUNTIME_STATE_OWNER,
    PROGRESS_ONLY_VALIDATION,
)

SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    """One branch-pruning model transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | selected | accepted | rejected
    scenario: str = "unset"
    surface: str = "unset"
    source_function: str = "unset"
    result_case: str = "unset"
    result_subcase: str = "unset"
    observable_state_writes: tuple[str, ...] = ()
    side_effects: tuple[str, ...] = ()
    requires_replay_evidence: bool = False
    replay_or_alignment_evidence: bool = False
    contraction_allowed: bool = False
    branch_equivalence_overclaimed: bool = False
    event_authority_required: bool = False
    event_authority_present: bool = False
    event_recorded: bool = False
    runtime_state_owner_count: int = 1
    background_progress_seen: bool = False
    background_exit_artifact_seen: bool = False
    validation_claimed_passed: bool = False
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _scheduled_state(
    scenario: str,
    result_case: str,
    *,
    subcase: str = "none",
    writes: tuple[str, ...] = (),
    side_effects: tuple[str, ...] = (),
    requires_replay_evidence: bool = False,
    replay_or_alignment_evidence: bool = False,
    contraction_allowed: bool = True,
) -> State:
    return State(
        status="selected",
        scenario=scenario,
        surface=SCHEDULED_RECEIPT_SURFACE,
        source_function="_reconcile_scheduled_controller_action_receipts",
        result_case=result_case,
        result_subcase=subcase,
        observable_state_writes=writes,
        side_effects=side_effects,
        requires_replay_evidence=requires_replay_evidence,
        replay_or_alignment_evidence=replay_or_alignment_evidence,
        contraction_allowed=contraction_allowed,
    )


def _role_output_state(
    scenario: str,
    result_case: str,
    *,
    subcase: str,
    authority_required: bool,
    authority_present: bool,
    event_recorded: bool,
    writes: tuple[str, ...] = (),
    side_effects: tuple[str, ...] = (),
    contraction_allowed: bool = True,
) -> State:
    return State(
        status="selected",
        scenario=scenario,
        surface=ROLE_OUTPUT_SURFACE,
        source_function="_try_reconcile_direct_role_output_event_ledger",
        result_case=result_case,
        result_subcase=subcase,
        observable_state_writes=writes,
        side_effects=side_effects,
        event_authority_required=authority_required,
        event_authority_present=authority_present,
        event_recorded=event_recorded,
        contraction_allowed=contraction_allowed,
    )


def _runtime_state(
    scenario: str,
    result_case: str,
    *,
    subcase: str,
    owner_count: int = 1,
    contraction_allowed: bool = False,
) -> State:
    return State(
        status="selected",
        scenario=scenario,
        surface=RUNTIME_STATE_SURFACE,
        source_function="_derive_resume_next_recipient_from_packet_ledger",
        result_case=result_case,
        result_subcase=subcase,
        observable_state_writes=("resume_next_recipient_projection",),
        runtime_state_owner_count=owner_count,
        contraction_allowed=contraction_allowed,
    )


def _scenario_state(scenario: str) -> State:
    if scenario == SCHEDULED_NO_ACTION_DIR:
        return _scheduled_state(scenario, "noop", subcase="no_action_directory", contraction_allowed=True)
    if scenario == SCHEDULED_INVALID_SCHEMA:
        return _scheduled_state(scenario, "noop", subcase="invalid_action_schema", contraction_allowed=True)
    if scenario == SCHEDULED_LEGACY_STARTUP_CANONICAL:
        return _scheduled_state(
            scenario,
            "reconciled",
            subcase="legacy_startup_canonical",
            writes=(
                "controller_action_row",
                "router_scheduler_row",
                "control_blocker_index",
                "derived_run_views",
                "run_state",
            ),
            side_effects=("resolve_control_blockers", "save_run_state"),
            requires_replay_evidence=True,
            replay_or_alignment_evidence=True,
            contraction_allowed=True,
        )
    if scenario == SCHEDULED_ROW_RECONCILIATION:
        return _scheduled_state(
            scenario,
            "reconciled",
            subcase="scheduler_row_already_satisfied",
            writes=("controller_action_row", "control_blocker_index", "derived_run_views"),
            side_effects=("resolve_control_blockers",),
            requires_replay_evidence=True,
            replay_or_alignment_evidence=True,
            contraction_allowed=True,
        )
    if scenario == SCHEDULED_CURRENT_SCOPE_RESOLVED:
        return _scheduled_state(
            scenario,
            "superseded",
            subcase="current_scope_wait_no_longer_blocked",
            writes=(
                "controller_action_row",
                "router_scheduler_row",
                "pending_action_projection",
                "run_history",
                "derived_run_views",
            ),
            side_effects=("clear_pending_controller_action", "save_run_state"),
            requires_replay_evidence=True,
            replay_or_alignment_evidence=True,
            contraction_allowed=True,
        )
    if scenario == SCHEDULED_CARD_RETURN_RESOLVED:
        return _scheduled_state(
            scenario,
            "reconciled",
            subcase="role_card_return_resolved_delivery_relay",
            writes=("controller_action_row", "router_scheduler_row", "derived_run_views"),
            requires_replay_evidence=True,
            replay_or_alignment_evidence=True,
            contraction_allowed=True,
        )
    if scenario == SCHEDULED_ALREADY_RECONCILED_WAIT_TARGET_REPLAY:
        return _scheduled_state(
            scenario,
            "replay_required",
            subcase="already_reconciled_wait_target_reminder_receipt_replay",
            writes=(
                "pending_action_projection",
                "controller_action_row",
                "router_scheduler_row",
                "run_history",
                "run_state",
            ),
            side_effects=("apply_done_controller_receipt_effects", "save_run_state"),
            requires_replay_evidence=True,
            replay_or_alignment_evidence=True,
            contraction_allowed=True,
        )
    if scenario == SCHEDULED_RECONCILED_POSTCONDITION_REPAIR_PENDING:
        return _scheduled_state(
            scenario,
            "repair_pending",
            subcase="already_reconciled_controller_action_postcondition_repair_pending",
            writes=("pending_action_projection", "repair_transaction"),
            side_effects=("clear_pending_controller_action",),
            requires_replay_evidence=True,
            replay_or_alignment_evidence=True,
            contraction_allowed=True,
        )
    if scenario == SCHEDULED_RECONCILED_POSTCONDITION_RETRY_PENDING:
        return _scheduled_state(
            scenario,
            "retry_pending",
            subcase="postcondition_reconciliation_direct_retry",
            writes=("controller_action_row", "pending_action_projection"),
            side_effects=("defer_controller_postcondition_reconciliation_retry",),
            requires_replay_evidence=True,
            replay_or_alignment_evidence=True,
            contraction_allowed=True,
        )
    if scenario == SCHEDULED_RECEIPT_APPLY_BLOCKED:
        return _scheduled_state(
            scenario,
            "blocked",
            subcase="postcondition_reconciliation_blocker",
            writes=("controller_action_row", "control_blocker_index", "pending_action_projection"),
            side_effects=("write_control_blocker", "save_run_state"),
            requires_replay_evidence=True,
            replay_or_alignment_evidence=True,
            contraction_allowed=False,
        )
    if scenario == SCHEDULED_BLOCKED_ROLE_RECOVERY_RECLAIM:
        return _scheduled_state(
            scenario,
            "reconciled",
            subcase="blocked_controller_action_role_recovery_report_reclaim",
            writes=("controller_action_row", "router_scheduler_row", "control_blocker_index"),
            side_effects=("reclaim_role_recovery_postcondition_from_report",),
            requires_replay_evidence=True,
            replay_or_alignment_evidence=True,
            contraction_allowed=True,
        )
    if scenario == ROLE_OUTPUT_INVALID_ENVELOPE:
        return _role_output_state(
            scenario,
            "noop",
            subcase="invalid_envelope",
            authority_required=False,
            authority_present=False,
            event_recorded=False,
        )
    if scenario == ROLE_OUTPUT_NOT_READY_REQUIRED_FLAG:
        return _role_output_state(
            scenario,
            "noop",
            subcase="not_ready",
            authority_required=True,
            authority_present=False,
            event_recorded=False,
        )
    if scenario == ROLE_OUTPUT_UNAUTHORIZED:
        return _role_output_state(
            scenario,
            "noop",
            subcase="unauthorized",
            authority_required=True,
            authority_present=False,
            event_recorded=False,
        )
    if scenario == ROLE_OUTPUT_ALREADY_RECORDED:
        return _role_output_state(
            scenario,
            "reconciled",
            subcase="already_recorded_wait_closure_or_side_effect",
            authority_required=True,
            authority_present=True,
            event_recorded=True,
            writes=("waiting_controller_actions", "run_history"),
            side_effects=("close_waiting_controller_actions",),
        )
    if scenario == ROLE_OUTPUT_VALID_DIRECT_EVENT:
        return _role_output_state(
            scenario,
            "reconciled",
            subcase="valid_direct_role_output_event",
            authority_required=True,
            authority_present=True,
            event_recorded=True,
            writes=("external_event_ledger", "run_flags", "run_history"),
            side_effects=("record_router_reconciled_external_event",),
        )
    if scenario == RUNTIME_PACKET_NO_ACTIVE:
        return _runtime_state(scenario, "noop", subcase="resume_without_active_packet_then_pm")
    if scenario == RUNTIME_PACKET_WITH_CONTROLLER:
        return _runtime_state(scenario, "retry_pending", subcase="relay_packet_envelope")
    if scenario == RUNTIME_PACKET_RESULT_NEEDS_PM:
        return _runtime_state(scenario, "retry_pending", subcase="relay_result_to_pm")
    if scenario == RUNTIME_PACKET_SUPERSEDED:
        return _runtime_state(scenario, "superseded", subcase="wait_for_replacement_packet")
    if scenario == RUNTIME_PACKET_NONSTANDARD_STATUS:
        return _runtime_state(scenario, "retry_pending", subcase="wait_for_ledger_holder")
    if scenario == OVERCLAIM_BRANCH_EQUIVALENCE:
        return replace(
            _scheduled_state(
                scenario,
                "reconciled",
                subcase="unsafe_shared_effect_claim",
                writes=("controller_action_row", "run_state", "control_blocker_index"),
                requires_replay_evidence=True,
                replay_or_alignment_evidence=False,
                contraction_allowed=True,
            ),
            branch_equivalence_overclaimed=True,
        )
    if scenario == MISSING_EVENT_AUTHORITY:
        return _role_output_state(
            scenario,
            "reconciled",
            subcase="unauthorized_but_recorded",
            authority_required=True,
            authority_present=False,
            event_recorded=True,
            writes=("external_event_ledger", "run_flags"),
        )
    if scenario == DUPLICATE_RUNTIME_STATE_OWNER:
        return _runtime_state(
            scenario,
            "reconciled",
            subcase="runtime_resume_split_claimed_two_owners",
            owner_count=2,
            contraction_allowed=True,
        )
    if scenario == PROGRESS_ONLY_VALIDATION:
        return State(
            status="selected",
            scenario=scenario,
            surface=BACKGROUND_VALIDATION_SURFACE,
            source_function="background_regression_artifact_contract",
            result_case="reconciled",
            result_subcase="progress_log_claimed_as_pass",
            background_progress_seen=True,
            background_exit_artifact_seen=False,
            validation_claimed_passed=True,
            contraction_allowed=True,
        )
    raise ValueError(f"unknown branch-pruning scenario: {scenario}")


def branch_pruning_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status == "new":
        return failures
    if state.result_case not in RESULT_CASES:
        failures.append("branch result case is not in the shared pruning vocabulary")
    if (
        state.contraction_allowed
        and state.requires_replay_evidence
        and state.observable_state_writes
        and not state.replay_or_alignment_evidence
    ):
        failures.append("branch contraction overclaimed equivalence without replay evidence")
    if state.branch_equivalence_overclaimed:
        failures.append("branch contraction overclaimed equivalence without replay evidence")
    if (
        state.surface == ROLE_OUTPUT_SURFACE
        and state.event_authority_required
        and state.event_recorded
        and not state.event_authority_present
    ):
        failures.append("role-output event was recorded without durable Router authority")
    if state.surface == RUNTIME_STATE_SURFACE and state.runtime_state_owner_count != 1:
        failures.append("runtime-state branch pruning introduced duplicate state ownership")
    if (
        state.validation_claimed_passed
        and state.background_progress_seen
        and not state.background_exit_artifact_seen
    ):
        failures.append("background progress was claimed as pass without exit artifact")
    return sorted(set(failures))


class ReconciliationBranchPruningStep:
    """Model one Router reconciliation branch-pruning transition.

    Input x State -> Set(Output x State)
    reads: Controller action rows, Controller receipts, scheduler rows,
    pending action projection, role-output ledger envelopes, dynamic Router
    wait authority, packet ledger status, and background check artifacts.
    writes: branch result-case decision, planned observable state writes,
    branch contraction allow/block decision, and validation-evidence boundary.
    idempotency: repeated reconciliation must remain keyed by existing action,
    event, packet, blocker, or background-check identity instead of creating a
    second observable effect.
    """

    name = "ReconciliationBranchPruningStep"
    input_description = "router reconciliation branch evidence"
    output_description = "one branch result-case classification"
    reads = (
        "controller_action_rows",
        "controller_receipts",
        "router_scheduler_rows",
        "pending_action_projection",
        "role_output_ledger",
        "dynamic_router_event_authority",
        "packet_ledger",
        "background_check_artifacts",
    )
    writes = (
        "branch_result_case",
        "observable_state_write_plan",
        "branch_contraction_gate",
        "validation_evidence_boundary",
    )
    idempotency = "action/event/packet/blocker/check-artifact scoped"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _scenario_state(scenario))
        return

    failures = branch_pruning_failures(state)
    if failures:
        yield Transition(
            f"reject_{state.scenario}",
            replace(state, status="rejected", terminal_reason="; ".join(failures)),
        )
        return
    yield Transition(
        f"accept_{state.scenario}",
        replace(state, status="accepted", terminal_reason="branch_pruning_contract_ok"),
    )


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and not branch_pruning_failures(state)


def accepted_states_are_safe(state: State, trace) -> InvariantResult:
    del trace
    failures = branch_pruning_failures(state)
    if state.status == "accepted" and failures:
        return InvariantResult.fail("unsafe branch-pruning state was accepted")
    if state.status == "rejected" and not failures:
        return InvariantResult.fail("safe branch-pruning state was rejected")
    return InvariantResult.pass_()


def state_writing_contraction_has_evidence(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    if (
        state.contraction_allowed
        and state.observable_state_writes
        and state.requires_replay_evidence
        and not state.replay_or_alignment_evidence
    ):
        return InvariantResult.fail(
            "accepted state-writing branch contraction without replay or alignment evidence"
        )
    return InvariantResult.pass_()


def role_output_authority_remains_explicit(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted" or state.surface != ROLE_OUTPUT_SURFACE:
        return InvariantResult.pass_()
    if state.event_authority_required and state.event_recorded and not state.event_authority_present:
        return InvariantResult.fail("accepted role-output event without durable Router authority")
    return InvariantResult.pass_()


def runtime_state_has_single_owner(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.surface == RUNTIME_STATE_SURFACE:
        if state.runtime_state_owner_count != 1:
            return InvariantResult.fail("accepted runtime-state branch with duplicate owners")
    return InvariantResult.pass_()


def background_pass_requires_exit_artifact(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    if state.validation_claimed_passed and not state.background_exit_artifact_seen:
        return InvariantResult.fail("accepted background regression pass without exit artifact")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepted_states_are_safe",
        description="Only branch-pruning classifications without known failures can be accepted.",
        predicate=accepted_states_are_safe,
    ),
    Invariant(
        name="state_writing_contraction_has_evidence",
        description="State-writing branch contraction requires replay or model-test alignment evidence.",
        predicate=state_writing_contraction_has_evidence,
    ),
    Invariant(
        name="role_output_authority_remains_explicit",
        description="Role-output events cannot be recorded without current durable Router authority.",
        predicate=role_output_authority_remains_explicit,
    ),
    Invariant(
        name="runtime_state_has_single_owner",
        description="Runtime-state resume mapping remains owned by one branch owner until replay evidence proves a split.",
        predicate=runtime_state_has_single_owner,
    ),
    Invariant(
        name="background_pass_requires_exit_artifact",
        description="Background model regressions require exit-bearing artifacts before pass claims.",
        predicate=background_pass_requires_exit_artifact,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def build_workflow() -> Workflow:
    return Workflow(
        (ReconciliationBranchPruningStep(),),
        name="flowpilot_router_reconciliation_branch_pruning",
    )


def terminal_predicate(_input_obj, state: State, _trace) -> bool:
    return is_terminal(state)


def hazard_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}


def ownership_snapshot() -> dict[str, object]:
    """Return the existing modeled owners this child model is grounded in."""

    return {
        "reuse_decision": "add_child_model",
        "parent_boundaries": (
            "flowpilot_router_facade_split_model",
            "flowpilot_structure_maintenance_model",
            "flowpilot_model_test_alignment_source_code_contracts",
        ),
        "branch_owner_functions": {
            SCHEDULED_RECEIPT_SURFACE: "_reconcile_scheduled_controller_action_receipts",
            ROLE_OUTPUT_SURFACE: (
                "_try_reconcile_startup_fact_role_output_ledger",
                "_role_output_event_has_durable_authority",
                "_try_reconcile_direct_role_output_event_ledger",
            ),
            RUNTIME_STATE_SURFACE: "_derive_resume_next_recipient_from_packet_ledger",
        },
        "decision": (
            "Use the existing Router StructureMesh and model-test alignment parents; "
            "add this narrower child model only for branch-pruning evidence."
        ),
    }


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "NEGATIVE_SCENARIOS",
    "RESULT_CASES",
    "SCENARIOS",
    "VALID_SCENARIOS",
    "Action",
    "State",
    "Tick",
    "Transition",
    "branch_pruning_failures",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "next_states",
    "ownership_snapshot",
    "terminal_predicate",
]
