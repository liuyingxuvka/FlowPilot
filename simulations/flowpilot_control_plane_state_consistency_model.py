"""FlowGuard model for FlowPilot control-plane state consistency.

This is a model-miss repair surface for the 2026-05-19 Router/Controller
incident.  Earlier models checked that individual actions happened; this model
checks that their durable effects agree before Router computes the next action.

Risk purpose:
- A Controller receipt must fold into every authoritative lifecycle record, not
  only a Router flag.
- A replacement PM role-work request must terminalize the old request before it
  can influence dispatch.
- A target role is busy only when it really holds unresolved work; an unrelayed
  Controller-held request is a control-plane inconsistency, not role workload.
- Daemon saves must not erase newer foreground evidence.
- Wait reminders and body/envelope metadata projections must be derived from
  stable durable identity, not stale transient projections.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


RECEIPT_FOLD_UPDATES_ALL_VIEWS = "receipt_fold_updates_all_views"
SUPERSEDE_TERMINALIZES_OLD_REQUEST = "supersede_terminalizes_old_request"
DISPATCH_BUSY_REQUIRES_TRUE_HOLDER = "dispatch_busy_requires_true_holder"
DAEMON_MERGE_PRESERVES_FOREGROUND_EVENT = "daemon_merge_preserves_foreground_event"
WAIT_REMINDER_HAS_STABLE_COOLDOWN = "wait_reminder_has_stable_cooldown"
SELF_CHECK_HEADING_PROJECTS_TO_ENVELOPE = "self_check_heading_projects_to_envelope"
UNIFIED_RECONCILER_ROOT_FIX = "unified_reconciler_root_fix"

OBSERVED_RECEIPT_FLAG_WITHOUT_BATCH_LIFECYCLE = "observed_receipt_flag_without_batch_lifecycle"
OBSERVED_SUPERSEDED_OLD_REQUEST_STILL_OPEN = "observed_superseded_old_request_still_open"
OBSERVED_UNRELAYED_OLD_REQUEST_BLOCKS_REPLACEMENT = "observed_unrelayed_old_request_blocks_replacement"
DAEMON_STALE_SNAPSHOT_ERASES_FOREGROUND_EVENT = "daemon_stale_snapshot_erases_foreground_event"
REMINDER_RECREATED_AFTER_PENDING_WAIT_LOSS = "reminder_recreated_after_pending_wait_loss"
RESULT_BODY_SELF_CHECK_NOT_PROJECTED = "result_body_self_check_not_projected"
RECEIPT_ONLY_FIX_LEAVES_ROLE_WORK_DEADLOCK = "receipt_only_fix_leaves_role_work_deadlock"
SUPERSEDE_ONLY_FIX_LEAVES_PROJECTION_DRIFT = "supersede_only_fix_leaves_projection_drift"
CASE_PATCHES_CLAIM_ROOT_FIX_WITHOUT_RECONCILER = "case_patches_claim_root_fix_without_reconciler"
NO_CAS_FIX_LOSES_FOREGROUND_EVENT = "no_cas_fix_loses_foreground_event"

VALID_SCENARIOS = (
    RECEIPT_FOLD_UPDATES_ALL_VIEWS,
    SUPERSEDE_TERMINALIZES_OLD_REQUEST,
    DISPATCH_BUSY_REQUIRES_TRUE_HOLDER,
    DAEMON_MERGE_PRESERVES_FOREGROUND_EVENT,
    WAIT_REMINDER_HAS_STABLE_COOLDOWN,
    SELF_CHECK_HEADING_PROJECTS_TO_ENVELOPE,
    UNIFIED_RECONCILER_ROOT_FIX,
)

NEGATIVE_SCENARIOS = (
    OBSERVED_RECEIPT_FLAG_WITHOUT_BATCH_LIFECYCLE,
    OBSERVED_SUPERSEDED_OLD_REQUEST_STILL_OPEN,
    OBSERVED_UNRELAYED_OLD_REQUEST_BLOCKS_REPLACEMENT,
    DAEMON_STALE_SNAPSHOT_ERASES_FOREGROUND_EVENT,
    REMINDER_RECREATED_AFTER_PENDING_WAIT_LOSS,
    RESULT_BODY_SELF_CHECK_NOT_PROJECTED,
    RECEIPT_ONLY_FIX_LEAVES_ROLE_WORK_DEADLOCK,
    SUPERSEDE_ONLY_FIX_LEAVES_PROJECTION_DRIFT,
    CASE_PATCHES_CLAIM_ROOT_FIX_WITHOUT_RECONCILER,
    NO_CAS_FIX_LOSES_FOREGROUND_EVENT,
)

SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS

TERMINAL_REQUEST_STATUSES = frozenset({"superseded", "canceled", "absorbed", "closed"})
RELAYED_BATCH_STATUSES = frozenset({"results_relayed_to_pm", "results_relayed_to_reviewer", "pm_absorbed"})


@dataclass(frozen=True)
class Tick:
    """One abstract control-plane reconciliation tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | accepted | rejected
    scenario: str = "unset"

    material_results_joined: bool = False
    controller_receipt_done: bool = False
    receipt_postcondition_flag: bool = False
    durable_batch_status: str = "none"
    router_projection_batch_status: str = "none"
    pm_disposition_attempted: bool = False
    pm_disposition_accepted: bool = False

    supersedes_declared: bool = False
    old_request_status: str = "none"
    old_request_in_active_index: bool = False
    new_request_status: str = "none"
    old_packet_relayed_to_target: bool = False
    old_packet_holder: str = "none"  # none | controller | target
    candidate_replacement_request: bool = False
    gate_treats_target_busy: bool = False
    gate_exposes_replacement_dispatch: bool = False
    control_blocker_exposed: bool = False

    foreground_event_version: int = 0
    daemon_snapshot_version: int = 0
    daemon_merge_before_save: bool = False
    daemon_save_preserves_foreground_event: bool = True

    wait_identity_stable: bool = True
    reminder_last_sent_persisted: bool = True
    reminder_cooldown_enforced: bool = True
    duplicate_reminder_materialized: bool = False

    body_self_check_heading_level: int = 0  # 0 none | 1 h1 | 2 h2
    envelope_self_check_completed: bool = False
    envelope_self_check_passed: bool = False

    shared_reconcile_before_next_action: bool = False
    next_action_from_reconciled_state: bool = False
    root_fix_claimed: bool = False
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _accepted(scenario: str, **changes: object) -> State:
    return replace(State(scenario=scenario), status="accepted", terminal_reason="valid", **changes)


def _rejected(scenario: str, **changes: object) -> State:
    return replace(State(scenario=scenario), status="rejected", terminal_reason="invalid", **changes)


def _receipt_good() -> dict[str, object]:
    return {
        "material_results_joined": True,
        "controller_receipt_done": True,
        "receipt_postcondition_flag": True,
        "durable_batch_status": "results_relayed_to_pm",
        "router_projection_batch_status": "results_relayed_to_pm",
        "pm_disposition_attempted": True,
        "pm_disposition_accepted": True,
    }


def _supersede_good() -> dict[str, object]:
    return {
        "supersedes_declared": True,
        "old_request_status": "superseded",
        "old_request_in_active_index": False,
        "new_request_status": "open",
    }


def _dispatch_good() -> dict[str, object]:
    return {
        "candidate_replacement_request": True,
        "old_request_status": "superseded",
        "old_packet_holder": "controller",
        "old_packet_relayed_to_target": False,
        "gate_treats_target_busy": False,
        "gate_exposes_replacement_dispatch": True,
    }


def _daemon_good() -> dict[str, object]:
    return {
        "foreground_event_version": 2,
        "daemon_snapshot_version": 1,
        "daemon_merge_before_save": True,
        "daemon_save_preserves_foreground_event": True,
    }


def _reminder_good() -> dict[str, object]:
    return {
        "wait_identity_stable": True,
        "reminder_last_sent_persisted": True,
        "reminder_cooldown_enforced": True,
        "duplicate_reminder_materialized": False,
    }


def _self_check_good() -> dict[str, object]:
    return {
        "body_self_check_heading_level": 1,
        "envelope_self_check_completed": True,
        "envelope_self_check_passed": True,
    }


def _root_fix_good() -> dict[str, object]:
    return {
        "shared_reconcile_before_next_action": True,
        "next_action_from_reconciled_state": True,
        "root_fix_claimed": True,
    }


def scenario_state(scenario: str) -> State:
    if scenario == RECEIPT_FOLD_UPDATES_ALL_VIEWS:
        return _accepted(scenario, **_receipt_good())
    if scenario == SUPERSEDE_TERMINALIZES_OLD_REQUEST:
        return _accepted(scenario, **_supersede_good())
    if scenario == DISPATCH_BUSY_REQUIRES_TRUE_HOLDER:
        return _accepted(scenario, **_dispatch_good())
    if scenario == DAEMON_MERGE_PRESERVES_FOREGROUND_EVENT:
        return _accepted(scenario, **_daemon_good())
    if scenario == WAIT_REMINDER_HAS_STABLE_COOLDOWN:
        return _accepted(scenario, **_reminder_good())
    if scenario == SELF_CHECK_HEADING_PROJECTS_TO_ENVELOPE:
        return _accepted(scenario, **_self_check_good())
    if scenario == UNIFIED_RECONCILER_ROOT_FIX:
        changes: dict[str, object] = {}
        for fragment in (_receipt_good(), _supersede_good(), _dispatch_good(), _daemon_good(), _reminder_good(), _self_check_good(), _root_fix_good()):
            changes.update(fragment)
        return _accepted(scenario, **changes)

    if scenario == OBSERVED_RECEIPT_FLAG_WITHOUT_BATCH_LIFECYCLE:
        return _rejected(
            scenario,
            material_results_joined=True,
            controller_receipt_done=True,
            receipt_postcondition_flag=True,
            durable_batch_status="results_joined",
            router_projection_batch_status="results_joined",
            pm_disposition_attempted=True,
            pm_disposition_accepted=False,
        )
    if scenario == OBSERVED_SUPERSEDED_OLD_REQUEST_STILL_OPEN:
        return _rejected(
            scenario,
            supersedes_declared=True,
            old_request_status="open",
            old_request_in_active_index=True,
            new_request_status="open",
        )
    if scenario == OBSERVED_UNRELAYED_OLD_REQUEST_BLOCKS_REPLACEMENT:
        return _rejected(
            scenario,
            old_request_status="open",
            old_request_in_active_index=True,
            old_packet_holder="controller",
            old_packet_relayed_to_target=False,
            candidate_replacement_request=True,
            gate_treats_target_busy=True,
            gate_exposes_replacement_dispatch=False,
        )
    if scenario == DAEMON_STALE_SNAPSHOT_ERASES_FOREGROUND_EVENT:
        return _rejected(
            scenario,
            foreground_event_version=2,
            daemon_snapshot_version=1,
            daemon_merge_before_save=False,
            daemon_save_preserves_foreground_event=False,
        )
    if scenario == REMINDER_RECREATED_AFTER_PENDING_WAIT_LOSS:
        return _rejected(
            scenario,
            wait_identity_stable=False,
            reminder_last_sent_persisted=False,
            reminder_cooldown_enforced=False,
            duplicate_reminder_materialized=True,
        )
    if scenario == RESULT_BODY_SELF_CHECK_NOT_PROJECTED:
        return _rejected(
            scenario,
            body_self_check_heading_level=1,
            envelope_self_check_completed=False,
            envelope_self_check_passed=False,
        )
    if scenario == RECEIPT_ONLY_FIX_LEAVES_ROLE_WORK_DEADLOCK:
        return _rejected(
            scenario,
            **_receipt_good(),
            supersedes_declared=True,
            old_request_status="open",
            old_request_in_active_index=True,
            new_request_status="open",
            old_packet_holder="controller",
            candidate_replacement_request=True,
            gate_treats_target_busy=True,
        )
    if scenario == SUPERSEDE_ONLY_FIX_LEAVES_PROJECTION_DRIFT:
        return _rejected(
            scenario,
            **_supersede_good(),
            material_results_joined=True,
            controller_receipt_done=True,
            receipt_postcondition_flag=True,
            durable_batch_status="results_joined",
            router_projection_batch_status="results_joined",
        )
    if scenario == CASE_PATCHES_CLAIM_ROOT_FIX_WITHOUT_RECONCILER:
        changes = {}
        for fragment in (_receipt_good(), _supersede_good(), _dispatch_good(), _daemon_good(), _reminder_good(), _self_check_good()):
            changes.update(fragment)
        changes.update(
            {
                "shared_reconcile_before_next_action": False,
                "next_action_from_reconciled_state": False,
                "root_fix_claimed": True,
            }
        )
        return _rejected(scenario, **changes)
    if scenario == NO_CAS_FIX_LOSES_FOREGROUND_EVENT:
        changes = {}
        for fragment in (_receipt_good(), _supersede_good(), _dispatch_good(), _reminder_good(), _self_check_good()):
            changes.update(fragment)
        changes.update(
            {
                "foreground_event_version": 2,
                "daemon_snapshot_version": 1,
                "daemon_merge_before_save": False,
                "daemon_save_preserves_foreground_event": False,
                "shared_reconcile_before_next_action": True,
                "next_action_from_reconciled_state": True,
                "root_fix_claimed": True,
            }
        )
        return _rejected(scenario, **changes)
    raise ValueError(f"unknown scenario: {scenario}")


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.scenario == "unset":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", replace(State(), scenario=scenario))
        return
    candidate = scenario_state(state.scenario)
    failures = consistency_failures(candidate)
    if not failures and state.scenario in VALID_SCENARIOS:
        yield Transition(f"accept_{state.scenario}", candidate)
    else:
        yield Transition(
            f"reject_{state.scenario}",
            replace(candidate, status="rejected", terminal_reason=failures[0] if failures else "negative scenario rejected"),
        )


class ControlPlaneStateConsistencyStep:
    """Model one pre-next-action control-plane reconciliation step."""

    name = "ControlPlaneStateConsistencyStep"
    input_description = "durable control-plane evidence and current Router projection"
    output_description = "reconciled Router projection or explicit control blocker"
    reads = (
        "controller_receipts",
        "packet_batches",
        "packet_ledger",
        "pm_role_work_index",
        "officer_lifecycle_index",
        "router_state_projection",
        "daemon_snapshot_version",
        "wait_reminder_identity",
        "result_body_contract_section",
    )
    writes = (
        "router_state_projection",
        "pm_role_work_terminal_status",
        "dispatch_gate_result",
        "daemon_merged_save",
        "wait_reminder_cooldown",
        "result_envelope_contract_metadata",
    )
    idempotency = "same durable evidence produces the same reconciled state before next action"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def _batch_relayed_or_absorbed(value: str) -> bool:
    return value in RELAYED_BATCH_STATUSES


def _old_request_is_terminal(value: str) -> bool:
    return value in TERMINAL_REQUEST_STATUSES


def consistency_failures(state: State) -> list[str]:
    failures: list[str] = []

    if (
        state.controller_receipt_done
        and state.receipt_postcondition_flag
        and state.material_results_joined
        and not _batch_relayed_or_absorbed(state.durable_batch_status)
    ):
        failures.append("receipt flag says material results relayed but durable batch lifecycle was not advanced")

    if (
        _batch_relayed_or_absorbed(state.durable_batch_status)
        and state.router_projection_batch_status
        and state.router_projection_batch_status != state.durable_batch_status
    ):
        failures.append("Router projection batch status diverged from durable batch status")

    if (
        state.pm_disposition_attempted
        and state.receipt_postcondition_flag
        and state.material_results_joined
        and not _batch_relayed_or_absorbed(state.durable_batch_status)
    ):
        failures.append("PM disposition was blocked by stale batch lifecycle after receipt relay evidence")

    if state.supersedes_declared and not _old_request_is_terminal(state.old_request_status):
        failures.append("superseding PM role-work request did not terminalize the old request")

    if state.supersedes_declared and state.old_request_in_active_index:
        failures.append("superseded PM role-work request remained in the active request index")

    if (
        state.candidate_replacement_request
        and state.gate_treats_target_busy
        and state.old_request_status == "open"
        and state.old_packet_holder == "controller"
        and not state.old_packet_relayed_to_target
    ):
        failures.append("unrelayed Controller-held old request was treated as target role busy")

    if (
        state.candidate_replacement_request
        and state.gate_exposes_replacement_dispatch
        and state.old_packet_relayed_to_target
        and state.old_packet_holder == "target"
        and not _old_request_is_terminal(state.old_request_status)
    ):
        failures.append("replacement dispatch was exposed while target role still truly held old work")

    if (
        state.foreground_event_version > state.daemon_snapshot_version
        and not state.daemon_merge_before_save
        and not state.daemon_save_preserves_foreground_event
    ):
        failures.append("daemon stale snapshot save erased newer foreground evidence")

    if (
        state.duplicate_reminder_materialized
        and (not state.wait_identity_stable or not state.reminder_last_sent_persisted or not state.reminder_cooldown_enforced)
    ):
        failures.append("wait reminder duplicate was materialized because wait identity or cooldown was not durable")

    if (
        state.body_self_check_heading_level in {1, 2}
        and (not state.envelope_self_check_completed or not state.envelope_self_check_passed)
    ):
        failures.append("result body self-check section was not projected into envelope metadata")

    if state.root_fix_claimed and not state.shared_reconcile_before_next_action:
        failures.append("root fix was claimed without a shared durable reconciliation barrier before next action")

    if state.root_fix_claimed and not state.next_action_from_reconciled_state:
        failures.append("root fix was claimed while next action still used unreconciled projection state")

    return failures


def accepts_only_consistent_states(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted":
        failures = consistency_failures(state)
        if failures:
            return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and state.scenario in VALID_SCENARIOS


def terminal_predicate(_input_obj: Tick, state: State, _trace) -> bool:
    return is_terminal(state)


def build_workflow() -> Workflow:
    return Workflow((ControlPlaneStateConsistencyStep(),), name="flowpilot_control_plane_state_consistency")


def hazard_states() -> dict[str, State]:
    return {scenario: scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}


def repair_candidate_states() -> dict[str, State]:
    receipt_only = scenario_state(RECEIPT_ONLY_FIX_LEAVES_ROLE_WORK_DEADLOCK)
    receipt_and_supersede = _rejected(
        "candidate_receipt_and_supersede_only",
        **_receipt_good(),
        **_supersede_good(),
        candidate_replacement_request=True,
        gate_treats_target_busy=False,
        gate_exposes_replacement_dispatch=True,
        foreground_event_version=2,
        daemon_snapshot_version=1,
        daemon_merge_before_save=False,
        daemon_save_preserves_foreground_event=False,
        duplicate_reminder_materialized=True,
        reminder_last_sent_persisted=False,
    )
    case_patches = scenario_state(CASE_PATCHES_CLAIM_ROOT_FIX_WITHOUT_RECONCILER)
    unified_root = scenario_state(UNIFIED_RECONCILER_ROOT_FIX)
    return {
        "receipt_only": receipt_only,
        "receipt_and_supersede_only": receipt_and_supersede,
        "case_patches_without_shared_reconciler": case_patches,
        "unified_reconciler_with_cas_and_true_holder_gate": unified_root,
    }


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 2
INVARIANTS = (
    Invariant(
        name="flowpilot_control_plane_state_consistency",
        description="Router may compute the next action only from reconciled durable control-plane state.",
        predicate=accepts_only_consistent_states,
    ),
)
