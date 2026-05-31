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
ROLE_OUTPUT_EVENT_FOLDS_TO_ROUTER_STATE_AND_CLEARS_WAIT = (
    "role_output_event_folds_to_router_state_and_clears_wait"
)
RESOLVED_WAIT_INVALIDATES_PENDING_PROJECTION = "resolved_wait_invalidates_pending_projection"
UNIFIED_RECONCILER_ROOT_FIX = "unified_reconciler_root_fix"
RESEARCH_BATCH_RESULT_RECONCILES_EVENT_AND_PM_RELAY = (
    "research_batch_result_reconciles_event_and_pm_relay"
)
DAEMON_RECOVERY_USES_RUN_RUNTIME_KIT_AUTHORITY = "daemon_recovery_uses_run_runtime_kit_authority"
STOP_SCOPE_DECLARATION_MATCHES_HOST_CLEANUP = "stop_scope_declaration_matches_host_cleanup"

OBSERVED_RECEIPT_FLAG_WITHOUT_BATCH_LIFECYCLE = "observed_receipt_flag_without_batch_lifecycle"
OBSERVED_SUPERSEDED_OLD_REQUEST_STILL_OPEN = "observed_superseded_old_request_still_open"
OBSERVED_UNRELAYED_OLD_REQUEST_BLOCKS_REPLACEMENT = "observed_unrelayed_old_request_blocks_replacement"
DAEMON_STALE_SNAPSHOT_ERASES_FOREGROUND_EVENT = "daemon_stale_snapshot_erases_foreground_event"
REMINDER_RECREATED_AFTER_PENDING_WAIT_LOSS = "reminder_recreated_after_pending_wait_loss"
RESULT_BODY_SELF_CHECK_NOT_PROJECTED = "result_body_self_check_not_projected"
MATERIAL_REVIEW_EVENT_LEFT_ONLY_IN_ROLE_OUTPUT_LEDGER = (
    "material_review_event_left_only_in_role_output_ledger"
)
DONE_WAIT_ROW_STILL_AUTHORIZES_PENDING_ACTION = "done_wait_row_still_authorizes_pending_action"
RECONCILED_WAIT_STILL_GENERATES_REMINDER = "reconciled_wait_still_generates_reminder"
RECEIPT_ONLY_FIX_LEAVES_ROLE_WORK_DEADLOCK = "receipt_only_fix_leaves_role_work_deadlock"
SUPERSEDE_ONLY_FIX_LEAVES_PROJECTION_DRIFT = "supersede_only_fix_leaves_projection_drift"
CASE_PATCHES_CLAIM_ROOT_FIX_WITHOUT_RECONCILER = "case_patches_claim_root_fix_without_reconciler"
ROOT_FIX_WITHOUT_ROLE_OUTPUT_EVENT_RECONCILER = "root_fix_without_role_output_event_reconciler"
NO_CAS_FIX_LOSES_FOREGROUND_EVENT = "no_cas_fix_loses_foreground_event"
OBSERVED_RESEARCH_BATCH_JOINED_WITHOUT_RETURN_EVENT = (
    "observed_research_batch_joined_without_return_event"
)
REMINDER_SENT_AFTER_RESEARCH_BATCH_JOINED = "reminder_sent_after_research_batch_joined"
DAEMON_RECOVERY_USES_MUTABLE_SOURCE_PROMPT = "daemon_recovery_uses_mutable_source_prompt"
GLOBAL_STOP_CLAIM_WITH_ACTIVE_HOST_AUTOMATIONS = "global_stop_claim_with_active_host_automations"

VALID_SCENARIOS = (
    RECEIPT_FOLD_UPDATES_ALL_VIEWS,
    SUPERSEDE_TERMINALIZES_OLD_REQUEST,
    DISPATCH_BUSY_REQUIRES_TRUE_HOLDER,
    DAEMON_MERGE_PRESERVES_FOREGROUND_EVENT,
    WAIT_REMINDER_HAS_STABLE_COOLDOWN,
    SELF_CHECK_HEADING_PROJECTS_TO_ENVELOPE,
    ROLE_OUTPUT_EVENT_FOLDS_TO_ROUTER_STATE_AND_CLEARS_WAIT,
    RESOLVED_WAIT_INVALIDATES_PENDING_PROJECTION,
    UNIFIED_RECONCILER_ROOT_FIX,
    RESEARCH_BATCH_RESULT_RECONCILES_EVENT_AND_PM_RELAY,
    DAEMON_RECOVERY_USES_RUN_RUNTIME_KIT_AUTHORITY,
    STOP_SCOPE_DECLARATION_MATCHES_HOST_CLEANUP,
)

NEGATIVE_SCENARIOS = (
    OBSERVED_RECEIPT_FLAG_WITHOUT_BATCH_LIFECYCLE,
    OBSERVED_SUPERSEDED_OLD_REQUEST_STILL_OPEN,
    OBSERVED_UNRELAYED_OLD_REQUEST_BLOCKS_REPLACEMENT,
    DAEMON_STALE_SNAPSHOT_ERASES_FOREGROUND_EVENT,
    REMINDER_RECREATED_AFTER_PENDING_WAIT_LOSS,
    RESULT_BODY_SELF_CHECK_NOT_PROJECTED,
    MATERIAL_REVIEW_EVENT_LEFT_ONLY_IN_ROLE_OUTPUT_LEDGER,
    DONE_WAIT_ROW_STILL_AUTHORIZES_PENDING_ACTION,
    RECONCILED_WAIT_STILL_GENERATES_REMINDER,
    RECEIPT_ONLY_FIX_LEAVES_ROLE_WORK_DEADLOCK,
    SUPERSEDE_ONLY_FIX_LEAVES_PROJECTION_DRIFT,
    CASE_PATCHES_CLAIM_ROOT_FIX_WITHOUT_RECONCILER,
    ROOT_FIX_WITHOUT_ROLE_OUTPUT_EVENT_RECONCILER,
    NO_CAS_FIX_LOSES_FOREGROUND_EVENT,
    OBSERVED_RESEARCH_BATCH_JOINED_WITHOUT_RETURN_EVENT,
    REMINDER_SENT_AFTER_RESEARCH_BATCH_JOINED,
    DAEMON_RECOVERY_USES_MUTABLE_SOURCE_PROMPT,
    GLOBAL_STOP_CLAIM_WITH_ACTIVE_HOST_AUTOMATIONS,
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

    direct_role_output_event_submitted: bool = False
    role_output_event_type: str = "none"  # none | material_review_insufficient | generic
    generic_role_output_event_reconciler: bool = False
    role_output_event_folded_to_router_state: bool = False
    router_event_flag_synced: bool = False
    material_review_projection_synced: bool = False
    material_insufficient_pm_repair_branch_exposed: bool = False
    packet_batch_family: str = "none"  # none | material_scan | research | current_node | pm_role_work
    packet_batch_results_joined: bool = False
    packet_batch_all_results_returned: bool = False
    packet_batch_missing_roles: int = 0
    packet_batch_next_recipient: str = "none"  # none | project_manager | reviewer
    packet_batch_reconciler_covers_family: bool = False
    worker_result_return_event_recorded: bool = False
    packet_batch_result_relayed_to_pm: bool = False
    controller_wait_row_status: str = "none"  # none | waiting | done
    scheduler_wait_row_status: str = "none"  # none | waiting | reconciled
    pending_action_references_wait: bool = False
    pending_action_validated_against_wait_ledgers: bool = False
    pending_action_cleared_after_wait_resolution: bool = False
    current_work_from_pending_action: bool = False
    stale_wait_reminder_created: bool = False

    shared_reconcile_before_next_action: bool = False
    next_action_from_reconciled_state: bool = False
    daemon_recovery_attempted: bool = False
    active_run_runtime_kit_prompt_manifest_present: bool = False
    source_runtime_kit_prompt_changed_after_run_start: bool = False
    daemon_recovery_reads_run_runtime_kit_prompt: bool = False
    daemon_recovery_reads_mutable_source_prompt: bool = False
    prompt_hash_mismatch_blocks_daemon_recovery: bool = False
    daemon_recovery_status_write_succeeds: bool = False
    stop_scope: str = "none"  # none | flowpilot_run | all_codex_host
    flowpilot_daemon_stopped: bool = False
    flowpilot_heartbeat_stopped: bool = False
    flowpilot_role_bindings_stopped: bool = False
    unrelated_host_automations_active: bool = False
    global_host_cleanup_claimed: bool = False
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


def _role_output_event_good() -> dict[str, object]:
    return {
        "direct_role_output_event_submitted": True,
        "role_output_event_type": "material_review_insufficient",
        "generic_role_output_event_reconciler": True,
        "role_output_event_folded_to_router_state": True,
        "router_event_flag_synced": True,
        "material_review_projection_synced": True,
        "material_insufficient_pm_repair_branch_exposed": True,
        "controller_wait_row_status": "done",
        "scheduler_wait_row_status": "reconciled",
        "pending_action_references_wait": True,
        "pending_action_validated_against_wait_ledgers": True,
        "pending_action_cleared_after_wait_resolution": True,
        "current_work_from_pending_action": False,
        "stale_wait_reminder_created": False,
    }


def _resolved_wait_good() -> dict[str, object]:
    return {
        "controller_wait_row_status": "done",
        "scheduler_wait_row_status": "reconciled",
        "pending_action_references_wait": True,
        "pending_action_validated_against_wait_ledgers": True,
        "pending_action_cleared_after_wait_resolution": True,
        "current_work_from_pending_action": False,
        "stale_wait_reminder_created": False,
    }


def _research_batch_good() -> dict[str, object]:
    return {
        "packet_batch_family": "research",
        "packet_batch_results_joined": True,
        "packet_batch_all_results_returned": True,
        "packet_batch_missing_roles": 0,
        "packet_batch_next_recipient": "project_manager",
        "packet_batch_reconciler_covers_family": True,
        "worker_result_return_event_recorded": True,
        "router_event_flag_synced": True,
        "packet_batch_result_relayed_to_pm": True,
        "controller_wait_row_status": "done",
        "scheduler_wait_row_status": "reconciled",
        "pending_action_references_wait": True,
        "pending_action_validated_against_wait_ledgers": True,
        "pending_action_cleared_after_wait_resolution": True,
        "current_work_from_pending_action": False,
        "stale_wait_reminder_created": False,
    }


def _daemon_recovery_prompt_good() -> dict[str, object]:
    return {
        "daemon_recovery_attempted": True,
        "active_run_runtime_kit_prompt_manifest_present": True,
        "source_runtime_kit_prompt_changed_after_run_start": True,
        "daemon_recovery_reads_run_runtime_kit_prompt": True,
        "daemon_recovery_reads_mutable_source_prompt": False,
        "prompt_hash_mismatch_blocks_daemon_recovery": False,
        "daemon_recovery_status_write_succeeds": True,
    }


def _stop_scope_good() -> dict[str, object]:
    return {
        "stop_scope": "flowpilot_run",
        "flowpilot_daemon_stopped": True,
        "flowpilot_heartbeat_stopped": True,
        "flowpilot_role_bindings_stopped": True,
        "unrelated_host_automations_active": True,
        "global_host_cleanup_claimed": False,
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
    if scenario == ROLE_OUTPUT_EVENT_FOLDS_TO_ROUTER_STATE_AND_CLEARS_WAIT:
        return _accepted(scenario, **_role_output_event_good())
    if scenario == RESOLVED_WAIT_INVALIDATES_PENDING_PROJECTION:
        return _accepted(scenario, **_resolved_wait_good())
    if scenario == UNIFIED_RECONCILER_ROOT_FIX:
        changes: dict[str, object] = {}
        for fragment in (
            _receipt_good(),
            _supersede_good(),
            _dispatch_good(),
            _daemon_good(),
            _reminder_good(),
            _self_check_good(),
            _role_output_event_good(),
            _research_batch_good(),
            _daemon_recovery_prompt_good(),
            _stop_scope_good(),
            _root_fix_good(),
        ):
            changes.update(fragment)
        return _accepted(scenario, **changes)
    if scenario == RESEARCH_BATCH_RESULT_RECONCILES_EVENT_AND_PM_RELAY:
        return _accepted(scenario, **_research_batch_good())
    if scenario == DAEMON_RECOVERY_USES_RUN_RUNTIME_KIT_AUTHORITY:
        return _accepted(scenario, **_daemon_recovery_prompt_good())
    if scenario == STOP_SCOPE_DECLARATION_MATCHES_HOST_CLEANUP:
        return _accepted(scenario, **_stop_scope_good())

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
    if scenario == MATERIAL_REVIEW_EVENT_LEFT_ONLY_IN_ROLE_OUTPUT_LEDGER:
        return _rejected(
            scenario,
            direct_role_output_event_submitted=True,
            role_output_event_type="material_review_insufficient",
            generic_role_output_event_reconciler=False,
            role_output_event_folded_to_router_state=False,
            router_event_flag_synced=False,
            material_review_projection_synced=False,
            material_insufficient_pm_repair_branch_exposed=False,
            controller_wait_row_status="done",
            scheduler_wait_row_status="reconciled",
            pending_action_references_wait=True,
            pending_action_validated_against_wait_ledgers=False,
            pending_action_cleared_after_wait_resolution=False,
            current_work_from_pending_action=True,
            stale_wait_reminder_created=True,
        )
    if scenario == DONE_WAIT_ROW_STILL_AUTHORIZES_PENDING_ACTION:
        return _rejected(
            scenario,
            role_output_event_folded_to_router_state=True,
            router_event_flag_synced=True,
            material_review_projection_synced=True,
            material_insufficient_pm_repair_branch_exposed=True,
            controller_wait_row_status="done",
            scheduler_wait_row_status="reconciled",
            pending_action_references_wait=True,
            pending_action_validated_against_wait_ledgers=False,
            pending_action_cleared_after_wait_resolution=False,
            current_work_from_pending_action=True,
        )
    if scenario == RECONCILED_WAIT_STILL_GENERATES_REMINDER:
        changes = dict(_role_output_event_good())
        changes.update(
            {
                "pending_action_validated_against_wait_ledgers": False,
                "pending_action_cleared_after_wait_resolution": False,
                "stale_wait_reminder_created": True,
            }
        )
        return _rejected(
            scenario,
            **changes,
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
    if scenario == ROOT_FIX_WITHOUT_ROLE_OUTPUT_EVENT_RECONCILER:
        changes = {}
        for fragment in (
            _receipt_good(),
            _supersede_good(),
            _dispatch_good(),
            _daemon_good(),
            _reminder_good(),
            _self_check_good(),
            _root_fix_good(),
        ):
            changes.update(fragment)
        changes.update(
            {
                "direct_role_output_event_submitted": True,
                "role_output_event_type": "material_review_insufficient",
                "generic_role_output_event_reconciler": False,
                "role_output_event_folded_to_router_state": False,
                "router_event_flag_synced": False,
                "material_review_projection_synced": False,
                "material_insufficient_pm_repair_branch_exposed": False,
                "controller_wait_row_status": "done",
                "scheduler_wait_row_status": "reconciled",
                "pending_action_references_wait": True,
                "pending_action_validated_against_wait_ledgers": True,
                "pending_action_cleared_after_wait_resolution": True,
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
    if scenario == OBSERVED_RESEARCH_BATCH_JOINED_WITHOUT_RETURN_EVENT:
        return _rejected(
            scenario,
            packet_batch_family="research",
            packet_batch_results_joined=True,
            packet_batch_all_results_returned=True,
            packet_batch_missing_roles=0,
            packet_batch_next_recipient="project_manager",
            packet_batch_reconciler_covers_family=False,
            worker_result_return_event_recorded=False,
            router_event_flag_synced=False,
            packet_batch_result_relayed_to_pm=False,
            controller_wait_row_status="waiting",
            scheduler_wait_row_status="waiting",
            pending_action_references_wait=True,
            current_work_from_pending_action=True,
        )
    if scenario == REMINDER_SENT_AFTER_RESEARCH_BATCH_JOINED:
        changes = dict(_research_batch_good())
        changes.update(
            {
                "pending_action_validated_against_wait_ledgers": False,
                "pending_action_cleared_after_wait_resolution": False,
                "current_work_from_pending_action": True,
                "stale_wait_reminder_created": True,
            }
        )
        return _rejected(scenario, **changes)
    if scenario == DAEMON_RECOVERY_USES_MUTABLE_SOURCE_PROMPT:
        return _rejected(
            scenario,
            daemon_recovery_attempted=True,
            active_run_runtime_kit_prompt_manifest_present=True,
            source_runtime_kit_prompt_changed_after_run_start=True,
            daemon_recovery_reads_run_runtime_kit_prompt=False,
            daemon_recovery_reads_mutable_source_prompt=True,
            prompt_hash_mismatch_blocks_daemon_recovery=True,
            daemon_recovery_status_write_succeeds=False,
        )
    if scenario == GLOBAL_STOP_CLAIM_WITH_ACTIVE_HOST_AUTOMATIONS:
        return _rejected(
            scenario,
            stop_scope="all_codex_host",
            flowpilot_daemon_stopped=True,
            flowpilot_heartbeat_stopped=True,
            flowpilot_role_bindings_stopped=True,
            unrelated_host_automations_active=True,
            global_host_cleanup_claimed=True,
        )
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
        "flowguard_operator_lifecycle_index",
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


def _wait_row_is_resolved(state: State) -> bool:
    return state.controller_wait_row_status == "done" or state.scheduler_wait_row_status == "reconciled"


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

    if state.direct_role_output_event_submitted and not state.generic_role_output_event_reconciler:
        failures.append("direct role-output event had no generic durable event reconciler")

    if state.direct_role_output_event_submitted and not state.role_output_event_folded_to_router_state:
        failures.append("direct role-output event stayed in role output ledger without canonical Router event")

    if state.role_output_event_folded_to_router_state and not state.router_event_flag_synced:
        failures.append("Router event was recorded without syncing its state flag")

    if (
        state.role_output_event_type == "material_review_insufficient"
        and state.role_output_event_folded_to_router_state
        and not state.material_review_projection_synced
    ):
        failures.append("material review role-output event did not update Router material_review projection")

    if (
        state.role_output_event_type == "material_review_insufficient"
        and state.role_output_event_folded_to_router_state
        and state.material_review_projection_synced
        and not state.material_insufficient_pm_repair_branch_exposed
    ):
        failures.append("material-insufficient review did not expose the PM repair or research branch")

    if _wait_row_is_resolved(state) and state.pending_action_references_wait:
        if not state.pending_action_validated_against_wait_ledgers:
            failures.append("pending_action was not validated against resolved Controller or scheduler wait rows")
        if not state.pending_action_cleared_after_wait_resolution:
            failures.append("resolved Controller or scheduler wait row did not clear pending_action")

    if _wait_row_is_resolved(state) and state.current_work_from_pending_action:
        failures.append("daemon status/current work was derived from stale pending_action after wait resolution")

    if _wait_row_is_resolved(state) and state.stale_wait_reminder_created:
        failures.append("wait reminder was created for an already reconciled wait row")

    if (
        state.packet_batch_results_joined
        and state.packet_batch_all_results_returned
        and state.packet_batch_missing_roles == 0
    ):
        if not state.packet_batch_reconciler_covers_family:
            failures.append("joined packet batch had no durable family reconciler")
        if state.packet_batch_family == "research" and not state.worker_result_return_event_recorded:
            failures.append("research batch results_joined did not synthesize worker_research_report_returned")
        if state.packet_batch_next_recipient == "project_manager" and not state.packet_batch_result_relayed_to_pm:
            failures.append("joined packet batch result was not relayed to project_manager")
        if state.stale_wait_reminder_created:
            failures.append("wait reminder was created after joined packet batch result already satisfied the wait")

    if state.daemon_recovery_attempted:
        if not state.active_run_runtime_kit_prompt_manifest_present:
            failures.append("daemon recovery had no active-run runtime_kit prompt manifest authority")
        if (
            state.source_runtime_kit_prompt_changed_after_run_start
            and state.daemon_recovery_reads_mutable_source_prompt
            and not state.daemon_recovery_reads_run_runtime_kit_prompt
        ):
            failures.append("daemon recovery read mutable source prompt instead of active run runtime_kit")
        if state.prompt_hash_mismatch_blocks_daemon_recovery:
            failures.append("prompt hash drift blocked daemon recovery or status write")
        if not state.daemon_recovery_status_write_succeeds:
            failures.append("daemon recovery did not finish its status write")

    if state.stop_scope == "flowpilot_run" and not (
        state.flowpilot_daemon_stopped
        and state.flowpilot_heartbeat_stopped
        and state.flowpilot_role_bindings_stopped
    ):
        failures.append("FlowPilot run stop did not reconcile daemon, heartbeat, and role bindings")

    if state.global_host_cleanup_claimed and state.unrelated_host_automations_active:
        failures.append("global host stop was claimed while unrelated host automations remained active")

    if state.root_fix_claimed and not state.shared_reconcile_before_next_action:
        failures.append("root fix was claimed without a shared durable reconciliation barrier before next action")

    if state.root_fix_claimed and not state.next_action_from_reconciled_state:
        failures.append("root fix was claimed while next action still used unreconciled projection state")

    if state.root_fix_claimed and not state.generic_role_output_event_reconciler:
        failures.append("root fix was claimed without generic role-output event reconciliation")

    if state.root_fix_claimed and not state.pending_action_validated_against_wait_ledgers:
        failures.append("root fix was claimed without validating pending_action against durable wait ledgers")

    if state.root_fix_claimed and not state.packet_batch_reconciler_covers_family:
        failures.append("root fix was claimed without packet-family batch reconciliation")

    if state.root_fix_claimed and not state.daemon_recovery_reads_run_runtime_kit_prompt:
        failures.append("root fix was claimed without active-run runtime_kit prompt authority")

    if state.root_fix_claimed and state.global_host_cleanup_claimed and state.unrelated_host_automations_active:
        failures.append("root fix overclaimed global host cleanup")

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
    role_output_event_only_changes = dict(_role_output_event_good())
    role_output_event_only_changes.update(
        {
            "pending_action_validated_against_wait_ledgers": False,
            "pending_action_cleared_after_wait_resolution": False,
            "current_work_from_pending_action": True,
        }
    )
    role_output_event_only = _rejected(
        "candidate_role_output_event_reconciler_only",
        **role_output_event_only_changes,
    )
    pending_clear_only = _rejected(
        "candidate_pending_clear_only",
        direct_role_output_event_submitted=True,
        role_output_event_type="material_review_insufficient",
        generic_role_output_event_reconciler=False,
        role_output_event_folded_to_router_state=False,
        router_event_flag_synced=False,
        material_review_projection_synced=False,
        material_insufficient_pm_repair_branch_exposed=False,
        controller_wait_row_status="done",
        scheduler_wait_row_status="reconciled",
        pending_action_references_wait=True,
        pending_action_validated_against_wait_ledgers=True,
        pending_action_cleared_after_wait_resolution=True,
    )
    case_patches = scenario_state(CASE_PATCHES_CLAIM_ROOT_FIX_WITHOUT_RECONCILER)
    batch_family_only = _rejected(
        "candidate_batch_family_reconciler_only",
        **_research_batch_good(),
        shared_reconcile_before_next_action=True,
        next_action_from_reconciled_state=True,
        root_fix_claimed=True,
    )
    run_prompt_only = _rejected(
        "candidate_run_prompt_authority_only",
        **_daemon_recovery_prompt_good(),
        shared_reconcile_before_next_action=True,
        next_action_from_reconciled_state=True,
        root_fix_claimed=True,
    )
    stop_scope_only = _rejected(
        "candidate_stop_scope_only",
        **_stop_scope_good(),
        shared_reconcile_before_next_action=True,
        next_action_from_reconciled_state=True,
        root_fix_claimed=True,
    )
    unified_root = scenario_state(UNIFIED_RECONCILER_ROOT_FIX)
    return {
        "receipt_only": receipt_only,
        "receipt_and_supersede_only": receipt_and_supersede,
        "role_output_event_reconciler_only": role_output_event_only,
        "pending_clear_only": pending_clear_only,
        "case_patches_without_shared_reconciler": case_patches,
        "batch_family_reconciler_only": batch_family_only,
        "run_prompt_authority_only": run_prompt_only,
        "stop_scope_only": stop_scope_only,
        "unified_reconciler_with_event_fold_pending_authority_cas_true_holder_batch_prompt_and_stop_scope": unified_root,
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
