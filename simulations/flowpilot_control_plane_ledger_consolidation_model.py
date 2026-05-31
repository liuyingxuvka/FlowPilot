"""FlowGuard model for FlowPilot control-plane ledger consolidation.

Risk intent:
- prevent Router scheduler rows from having multiple live writers;
- ensure transient daemon-critical JSON access denial defers daemon progress
  instead of killing the daemon;
- keep unsupported_historical pending_action as a projection when Controller action ledger
  authority exists;
- derive worker batch waits from member state rather than a single inferred
  worker event role;
- close stale passive/current-scope wait rows after their prerequisite is
  already resolved;
- force all blocker scans to use one canonical closed-row predicate, so
  resolved+reconciled and other terminal Controller states cannot be counted as
  pending work by another table;
- preserve signed packet/result envelope immutability.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_SCENARIOS = (
    "receipt_append_daemon_folds_scheduler",
    "transient_readback_permission_deferred",
    "pending_action_projection_demoted",
    "batch_wait_members_project_missing_roles",
    "stale_passive_wait_superseded",
    "closed_status_vocabulary_uses_canonical_predicate",
    "cross_surface_closure_kernel_uses_canonical_predicate",
    "unknown_closure_classification_remains_blocking",
    "signed_envelope_projection_sidecar",
)

NEGATIVE_SCENARIOS = (
    "foreground_receipt_writes_scheduler_during_daemon",
    "readback_permission_kills_daemon",
    "pending_action_overrides_controller_ledger",
    "worker_event_collapses_batch_to_worker",
    "stale_passive_wait_left_open",
    "closed_status_vocabulary_blocks_passive_wait",
    "non_controller_closed_row_blocks_wait",
    "unknown_closure_classification_clears_wait",
    "signed_envelope_mutated_for_projection",
)

SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    """One abstract control-plane reconciliation step."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | accepted | rejected
    scenario: str = "unset"

    daemon_mode: bool = True
    daemon_live: bool = True
    controller_receipt_persisted: bool = False
    scheduler_fold_owner: str = "daemon"  # daemon | foreground | none
    foreground_mutated_scheduler: bool = False
    scheduler_row_folded_from_receipt: bool = False
    action_local_receipt_metadata_written: bool = False

    daemon_critical_json_access_denied: bool = False
    fresh_runtime_write_activity: bool = False
    daemon_deferred_tick: bool = False
    daemon_lock_released_error: bool = False

    controller_action_ledger_authority: bool = False
    unsupported_historical_pending_action_present: bool = False
    unsupported_historical_pending_apply_required: bool = False
    controller_action_apply_required: bool = False
    controller_action_wait_mode: str = "none"  # none | receipt_only | router_controlled_wait
    decision_used_controller_ledger: bool = False
    pending_action_labeled_projection: bool = False

    batch_member_roles: tuple[str, ...] = ()
    batch_returned_roles: tuple[str, ...] = ()
    event_inferred_role: str = ""
    projected_missing_roles: tuple[str, ...] = ()

    passive_wait_open: bool = False
    passive_wait_prerequisite_resolved: bool = False
    passive_wait_superseded_or_reconciled: bool = False
    passive_wait_in_open_rows: bool = False

    controller_obligation_status: str = "none"
    controller_obligation_reconciliation_status: str = "none"
    canonical_closed_row_predicate_used: bool = True
    closed_controller_row_counted_pending: bool = False

    closure_surfaces: tuple[str, ...] = ()
    closure_kernel_used_for_surfaces: tuple[str, ...] = ()
    non_controller_closed_row_counted_pending: bool = False
    unknown_closure_classification_cleared_wait: bool = False

    signed_envelope_relayed: bool = False
    signed_envelope_mutated: bool = False
    sidecar_projection_written: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _accepted(scenario: str, **changes: object) -> State:
    return replace(State(status="accepted", scenario=scenario), **changes)


def _rejected(scenario: str, **changes: object) -> State:
    return replace(State(status="rejected", scenario=scenario), **changes)


def scenario_state(scenario: str) -> State:
    if scenario == "receipt_append_daemon_folds_scheduler":
        return _accepted(
            scenario,
            controller_receipt_persisted=True,
            action_local_receipt_metadata_written=True,
            scheduler_fold_owner="daemon",
            scheduler_row_folded_from_receipt=True,
        )
    if scenario == "transient_readback_permission_deferred":
        return _accepted(
            scenario,
            daemon_critical_json_access_denied=True,
            fresh_runtime_write_activity=True,
            daemon_deferred_tick=True,
        )
    if scenario == "pending_action_projection_demoted":
        return _accepted(
            scenario,
            controller_action_ledger_authority=True,
            unsupported_historical_pending_action_present=True,
            unsupported_historical_pending_apply_required=True,
            controller_action_apply_required=False,
            controller_action_wait_mode="router_controlled_wait",
            decision_used_controller_ledger=True,
            pending_action_labeled_projection=True,
        )
    if scenario == "batch_wait_members_project_missing_roles":
        return _accepted(
            scenario,
            batch_member_roles=("worker", "worker"),
            batch_returned_roles=("worker",),
            event_inferred_role="worker",
            projected_missing_roles=("worker",),
        )
    if scenario == "stale_passive_wait_superseded":
        return _accepted(
            scenario,
            passive_wait_open=True,
            passive_wait_prerequisite_resolved=True,
            passive_wait_superseded_or_reconciled=True,
            passive_wait_in_open_rows=False,
        )
    if scenario == "closed_status_vocabulary_uses_canonical_predicate":
        return _accepted(
            scenario,
            passive_wait_open=True,
            passive_wait_prerequisite_resolved=True,
            passive_wait_superseded_or_reconciled=True,
            passive_wait_in_open_rows=False,
            controller_obligation_status="resolved",
            controller_obligation_reconciliation_status="reconciled",
            canonical_closed_row_predicate_used=True,
            closed_controller_row_counted_pending=False,
        )
    if scenario == "cross_surface_closure_kernel_uses_canonical_predicate":
        return _accepted(
            scenario,
            passive_wait_open=True,
            passive_wait_prerequisite_resolved=True,
            passive_wait_superseded_or_reconciled=True,
            passive_wait_in_open_rows=False,
            closure_surfaces=("controller_action", "pm_role_work", "packet_lifecycle", "ack_return"),
            closure_kernel_used_for_surfaces=("controller_action", "pm_role_work", "packet_lifecycle", "ack_return"),
            non_controller_closed_row_counted_pending=False,
        )
    if scenario == "unknown_closure_classification_remains_blocking":
        return _accepted(
            scenario,
            passive_wait_open=True,
            passive_wait_prerequisite_resolved=False,
            passive_wait_superseded_or_reconciled=False,
            passive_wait_in_open_rows=True,
            closure_surfaces=("worker_result",),
            closure_kernel_used_for_surfaces=("worker_result",),
            unknown_closure_classification_cleared_wait=False,
        )
    if scenario == "signed_envelope_projection_sidecar":
        return _accepted(
            scenario,
            signed_envelope_relayed=True,
            signed_envelope_mutated=False,
            sidecar_projection_written=True,
        )
    if scenario == "foreground_receipt_writes_scheduler_during_daemon":
        return _rejected(
            scenario,
            controller_receipt_persisted=True,
            scheduler_fold_owner="foreground",
            foreground_mutated_scheduler=True,
        )
    if scenario == "readback_permission_kills_daemon":
        return _rejected(
            scenario,
            daemon_critical_json_access_denied=True,
            fresh_runtime_write_activity=True,
            daemon_deferred_tick=False,
            daemon_lock_released_error=True,
        )
    if scenario == "pending_action_overrides_controller_ledger":
        return _rejected(
            scenario,
            controller_action_ledger_authority=True,
            unsupported_historical_pending_action_present=True,
            unsupported_historical_pending_apply_required=True,
            controller_action_apply_required=False,
            controller_action_wait_mode="receipt_only",
            decision_used_controller_ledger=False,
            pending_action_labeled_projection=False,
        )
    if scenario == "worker_event_collapses_batch_to_worker":
        return _rejected(
            scenario,
            batch_member_roles=("worker", "worker"),
            batch_returned_roles=("worker",),
            event_inferred_role="worker",
            projected_missing_roles=("worker",),
        )
    if scenario == "stale_passive_wait_left_open":
        return _rejected(
            scenario,
            passive_wait_open=True,
            passive_wait_prerequisite_resolved=True,
            passive_wait_superseded_or_reconciled=False,
            passive_wait_in_open_rows=True,
        )
    if scenario == "closed_status_vocabulary_blocks_passive_wait":
        return _rejected(
            scenario,
            passive_wait_open=True,
            passive_wait_prerequisite_resolved=True,
            passive_wait_superseded_or_reconciled=False,
            passive_wait_in_open_rows=True,
            controller_obligation_status="resolved",
            controller_obligation_reconciliation_status="reconciled",
            canonical_closed_row_predicate_used=False,
            closed_controller_row_counted_pending=True,
        )
    if scenario == "non_controller_closed_row_blocks_wait":
        return _rejected(
            scenario,
            passive_wait_open=True,
            passive_wait_prerequisite_resolved=True,
            passive_wait_superseded_or_reconciled=False,
            passive_wait_in_open_rows=True,
            closure_surfaces=("pm_role_work", "packet_lifecycle"),
            closure_kernel_used_for_surfaces=("controller_action",),
            non_controller_closed_row_counted_pending=True,
        )
    if scenario == "unknown_closure_classification_clears_wait":
        return _rejected(
            scenario,
            passive_wait_open=True,
            passive_wait_prerequisite_resolved=False,
            passive_wait_superseded_or_reconciled=True,
            passive_wait_in_open_rows=False,
            closure_surfaces=("worker_result",),
            closure_kernel_used_for_surfaces=("worker_result",),
            unknown_closure_classification_cleared_wait=True,
        )
    if scenario == "signed_envelope_mutated_for_projection":
        return _rejected(
            scenario,
            signed_envelope_relayed=True,
            signed_envelope_mutated=True,
            sidecar_projection_written=False,
        )
    raise ValueError(f"unknown scenario: {scenario}")


def consolidation_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.daemon_mode and state.daemon_live and state.foreground_mutated_scheduler:
        failures.append("foreground receipt path mutated Router scheduler ledger while daemon owned folding")
    if state.controller_receipt_persisted and not state.action_local_receipt_metadata_written:
        failures.append("Controller receipt was not preserved as action-local durable metadata")
    if state.controller_receipt_persisted and state.scheduler_fold_owner == "daemon" and not state.scheduler_row_folded_from_receipt:
        failures.append("daemon-owned fold did not reconcile scheduler row from receipt")
    if (
        state.daemon_critical_json_access_denied
        and state.fresh_runtime_write_activity
        and not state.daemon_deferred_tick
    ):
        failures.append("transient daemon-critical JSON access denial was not deferred")
    if (
        state.daemon_critical_json_access_denied
        and state.fresh_runtime_write_activity
        and state.daemon_lock_released_error
    ):
        failures.append("transient ledger access denial released daemon lock as error")
    if (
        state.controller_action_ledger_authority
        and state.unsupported_historical_pending_action_present
        and not state.decision_used_controller_ledger
    ):
        failures.append("unsupported_historical pending_action overrode Controller action ledger authority")
    if (
        state.controller_action_ledger_authority
        and state.unsupported_historical_pending_action_present
        and state.unsupported_historical_pending_apply_required != state.controller_action_apply_required
        and not state.pending_action_labeled_projection
    ):
        failures.append("conflicting unsupported_historical pending_action was not labeled as projection")
    if state.batch_member_roles:
        missing = tuple(role for role in state.batch_member_roles if role not in set(state.batch_returned_roles))
        if state.projected_missing_roles != missing:
            failures.append("batch wait projection did not derive missing roles from member state")
    if (
        state.passive_wait_open
        and state.passive_wait_prerequisite_resolved
        and not state.passive_wait_superseded_or_reconciled
    ):
        failures.append("stale passive wait remained unresolved after prerequisite resolved")
    if state.passive_wait_prerequisite_resolved and state.passive_wait_in_open_rows:
        failures.append("stale passive wait stayed in open scheduler rows")
    if state.closed_controller_row_counted_pending:
        failures.append("closed Controller row was counted as pending by a noncanonical blocker scan")
    if (
        state.controller_obligation_status == "resolved"
        and state.controller_obligation_reconciliation_status == "reconciled"
        and not state.canonical_closed_row_predicate_used
    ):
        failures.append("resolved+reconciled Controller row bypassed the canonical closure predicate")
    if state.closure_surfaces:
        missing_surfaces = tuple(
            surface
            for surface in state.closure_surfaces
            if surface not in set(state.closure_kernel_used_for_surfaces)
        )
        if missing_surfaces:
            failures.append("closure surface bypassed the canonical closure predicate")
    if state.non_controller_closed_row_counted_pending:
        failures.append("closed non-Controller row was counted as pending by a noncanonical blocker scan")
    if state.unknown_closure_classification_cleared_wait:
        failures.append("unknown closure classification cleared a wait")
    if state.signed_envelope_relayed and state.signed_envelope_mutated:
        failures.append("signed packet or result envelope was mutated after relay")
    if state.signed_envelope_relayed and not state.sidecar_projection_written and not state.signed_envelope_mutated:
        failures.append("signed envelope projection lacked sidecar metadata")
    return failures


def accepts_only_safe_consolidation(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted":
        failures = consolidation_failures(state)
        if failures:
            return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="control_plane_ledger_consolidation",
        description="Control plane has one scheduler fold owner, deferrable transient ledger access, authoritative Controller action rows, accurate batch projections, and immutable signed envelopes.",
        predicate=accepts_only_safe_consolidation,
    ),
)


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.scenario == "unset":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", replace(State(), scenario=scenario))
        return
    candidate = scenario_state(state.scenario)
    failures = consolidation_failures(candidate)
    if not failures and state.scenario in VALID_SCENARIOS:
        yield Transition(f"accept_{state.scenario}", candidate)
    else:
        yield Transition(f"reject_{state.scenario}", candidate)


class ControlPlaneLedgerConsolidationStep:
    """Model one control-plane fold/projection decision.

    Input x State -> Set(Output x State)
    reads: Controller receipts, Controller action ledger, Router scheduler
    ledger, unsupported_historical pending_action projection, packet batch members, runtime JSON
    write-lock state, and signed envelope metadata
    writes: scheduler folds, action-local receipt metadata, display/current-work
    projections, passive-wait reconciliation, and sidecar projections
    idempotency: receipt folds and stale-wait supersession are keyed by
    controller action id, router scheduler row id, or packet batch id
    """

    name = "ControlPlaneLedgerConsolidationStep"
    input_description = "one control-plane event or daemon fold"
    output_description = "safe fold/projection or rejected hazard"
    reads = (
        "controller_receipts",
        "controller_action_ledger",
        "router_scheduler_ledger",
        "pending_action_projection",
        "packet_batch_members",
        "runtime_json_write_lock",
        "signed_envelope_metadata",
    )
    writes = (
        "router_scheduler_fold",
        "action_local_receipt_metadata",
        "current_work_projection",
        "passive_wait_reconciliation",
        "signed_envelope_sidecar_projection",
    )
    idempotency = "controller_action_id/router_scheduler_row_id/packet_batch_id"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def build_workflow() -> Workflow:
    return Workflow((ControlPlaneLedgerConsolidationStep(),), name="flowpilot_control_plane_ledger_consolidation")


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def hazard_states() -> dict[str, State]:
    return {scenario: scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and state.scenario in VALID_SCENARIOS


def terminal_predicate(_input_obj: Tick, state: State, _trace) -> bool:
    return is_terminal(state)


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 2


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "NEGATIVE_SCENARIOS",
    "SCENARIOS",
    "VALID_SCENARIOS",
    "Action",
    "State",
    "Tick",
    "Transition",
    "build_workflow",
    "consolidation_failures",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "scenario_state",
    "terminal_predicate",
]
