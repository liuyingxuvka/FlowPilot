"""FlowGuard model for Controller receipt evidence folding.

Risk purpose:
- Catch Controller actions whose direct apply path updates a Router-owned
  postcondition flag, while the asynchronous Controller receipt path cannot
  reconstruct the same flag from Router-visible evidence.
- Generalize the material scan miss: packets and leases proved dispatch, but
  the receipt reconciler returned ``unsupported_stateful_controller_receipt``
  and left ``material_scan_packets_relayed`` false.
- Keep the intended repair small: one registered evidence-fold contract per
  evidence-backed postcondition action family, not ad hoc retries or PM repair
  packets for evidence that Router can already verify.

Model lens:
- Input x State -> Set(Output x State)
- Reads: Controller action class, direct-apply flag writes, receipt status,
  Router-visible evidence, receipt fold registration, postcondition flag, and
  downstream wait selection.
- Writes: Router-owned postcondition flag, receipt reconciliation result,
  retry/blocker only when evidence is genuinely missing, and next wait action.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


DISPLAY_STATUS_REGISTERED_FOLD = "display_status_registered_fold"
MAIL_DELIVERY_REGISTERED_FOLD = "mail_delivery_registered_fold"
PACKET_RELAY_REGISTERED_FOLD = "packet_relay_registered_fold"
PACKET_RELAY_IN_PROGRESS_WAITS = "packet_relay_in_progress_waits"
MISSING_EVIDENCE_RETRY_OR_BLOCK = "missing_evidence_retry_or_block"
LOCAL_RECEIPT_WITHOUT_ROUTER_FLAG = "local_receipt_without_router_flag"

UNSUPPORTED_RECEIPT_WITH_PACKET_EVIDENCE = "unsupported_receipt_with_packet_evidence"
DIRECT_APPLY_ONLY_NO_RECEIPT_FOLD = "direct_apply_only_no_receipt_fold"
FALSE_BLOCKER_WITH_EVIDENCE_AVAILABLE = "false_blocker_with_evidence_available"
DUPLICATE_REQUEUE_WHILE_RECEIPT_DONE = "duplicate_requeue_while_receipt_done"
DOWNSTREAM_WAIT_GATED_BY_UNFOLDED_DISPATCH = "downstream_wait_gated_by_unfolded_dispatch"
RECONCILED_RECEIPT_WITHOUT_FLAG = "reconciled_receipt_without_flag"

VALID_SCENARIOS = (
    DISPLAY_STATUS_REGISTERED_FOLD,
    MAIL_DELIVERY_REGISTERED_FOLD,
    PACKET_RELAY_REGISTERED_FOLD,
    PACKET_RELAY_IN_PROGRESS_WAITS,
    MISSING_EVIDENCE_RETRY_OR_BLOCK,
    LOCAL_RECEIPT_WITHOUT_ROUTER_FLAG,
)

NEGATIVE_SCENARIOS = (
    UNSUPPORTED_RECEIPT_WITH_PACKET_EVIDENCE,
    DIRECT_APPLY_ONLY_NO_RECEIPT_FOLD,
    FALSE_BLOCKER_WITH_EVIDENCE_AVAILABLE,
    DUPLICATE_REQUEUE_WHILE_RECEIPT_DONE,
    DOWNSTREAM_WAIT_GATED_BY_UNFOLDED_DISPATCH,
    RECONCILED_RECEIPT_WITHOUT_FLAG,
)

SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    """One abstract receipt reconciliation transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | accepted | rejected
    scenario: str = "unset"
    action_family: str = "none"  # display | mail | packet_relay | local
    action_type: str = "none"
    postcondition_name: str = "none"

    controller_receipt_possible: bool = False
    controller_receipt_done: bool = False
    direct_apply_sets_flag: bool = False
    receipt_fold_registered: bool = False
    unsupported_receipt_result: bool = False

    router_visible_evidence_available: bool = False
    packet_batch_relayed: bool = False
    active_holder_leases_issued: bool = False
    worker_packet_opened_or_acknowledged: bool = False
    worker_result_still_pending: bool = False

    router_postcondition_flag_satisfied: bool = False
    router_marked_receipt_reconciled: bool = False
    repair_or_blocker_recorded: bool = False
    false_control_blocker_recorded: bool = False
    same_action_requeued: bool = False
    downstream_wait_selected: bool = False

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


def scenario_state(scenario: str) -> State:
    if scenario == DISPLAY_STATUS_REGISTERED_FOLD:
        return _accepted(
            scenario,
            action_family="display",
            action_type="write_display_surface_status",
            postcondition_name="startup_display_status_written",
            controller_receipt_possible=True,
            controller_receipt_done=True,
            direct_apply_sets_flag=True,
            receipt_fold_registered=True,
            router_visible_evidence_available=True,
            router_postcondition_flag_satisfied=True,
            router_marked_receipt_reconciled=True,
        )
    if scenario == MAIL_DELIVERY_REGISTERED_FOLD:
        return _accepted(
            scenario,
            action_family="mail",
            action_type="deliver_mail",
            postcondition_name="mail_delivered",
            controller_receipt_possible=True,
            controller_receipt_done=True,
            receipt_fold_registered=True,
            router_visible_evidence_available=True,
            router_postcondition_flag_satisfied=True,
            router_marked_receipt_reconciled=True,
        )
    if scenario == PACKET_RELAY_REGISTERED_FOLD:
        return _accepted(
            scenario,
            action_family="packet_relay",
            action_type="relay_material_scan_packets",
            postcondition_name="material_scan_packets_relayed",
            controller_receipt_possible=True,
            controller_receipt_done=True,
            direct_apply_sets_flag=True,
            receipt_fold_registered=True,
            router_visible_evidence_available=True,
            packet_batch_relayed=True,
            active_holder_leases_issued=True,
            worker_packet_opened_or_acknowledged=True,
            router_postcondition_flag_satisfied=True,
            router_marked_receipt_reconciled=True,
            downstream_wait_selected=True,
        )
    if scenario == PACKET_RELAY_IN_PROGRESS_WAITS:
        return _accepted(
            scenario,
            action_family="packet_relay",
            action_type="relay_material_scan_packets",
            postcondition_name="material_scan_packets_relayed",
            controller_receipt_possible=True,
            controller_receipt_done=True,
            direct_apply_sets_flag=True,
            receipt_fold_registered=True,
            router_visible_evidence_available=True,
            packet_batch_relayed=True,
            active_holder_leases_issued=True,
            worker_packet_opened_or_acknowledged=True,
            worker_result_still_pending=True,
            router_postcondition_flag_satisfied=True,
            router_marked_receipt_reconciled=True,
            downstream_wait_selected=True,
        )
    if scenario == MISSING_EVIDENCE_RETRY_OR_BLOCK:
        return _accepted(
            scenario,
            action_family="packet_relay",
            action_type="relay_material_scan_packets",
            postcondition_name="material_scan_packets_relayed",
            controller_receipt_possible=True,
            controller_receipt_done=True,
            direct_apply_sets_flag=True,
            receipt_fold_registered=True,
            router_visible_evidence_available=False,
            router_postcondition_flag_satisfied=False,
            repair_or_blocker_recorded=True,
        )
    if scenario == LOCAL_RECEIPT_WITHOUT_ROUTER_FLAG:
        return _accepted(
            scenario,
            action_family="local",
            action_type="controller_local_receipt",
            postcondition_name="none",
            controller_receipt_possible=True,
            controller_receipt_done=True,
            direct_apply_sets_flag=False,
            receipt_fold_registered=False,
            router_visible_evidence_available=False,
            router_postcondition_flag_satisfied=False,
            router_marked_receipt_reconciled=True,
        )
    if scenario == UNSUPPORTED_RECEIPT_WITH_PACKET_EVIDENCE:
        return _rejected(
            scenario,
            action_family="packet_relay",
            action_type="relay_material_scan_packets",
            postcondition_name="material_scan_packets_relayed",
            controller_receipt_possible=True,
            controller_receipt_done=True,
            direct_apply_sets_flag=True,
            receipt_fold_registered=False,
            unsupported_receipt_result=True,
            router_visible_evidence_available=True,
            packet_batch_relayed=True,
            active_holder_leases_issued=True,
            worker_packet_opened_or_acknowledged=True,
        )
    if scenario == DIRECT_APPLY_ONLY_NO_RECEIPT_FOLD:
        return _rejected(
            scenario,
            action_family="packet_relay",
            action_type="relay_material_scan_packets",
            postcondition_name="material_scan_packets_relayed",
            controller_receipt_possible=True,
            controller_receipt_done=False,
            direct_apply_sets_flag=True,
            receipt_fold_registered=False,
            router_visible_evidence_available=True,
            packet_batch_relayed=True,
            active_holder_leases_issued=True,
        )
    if scenario == FALSE_BLOCKER_WITH_EVIDENCE_AVAILABLE:
        return _rejected(
            scenario,
            action_family="packet_relay",
            action_type="relay_material_scan_packets",
            postcondition_name="material_scan_packets_relayed",
            controller_receipt_possible=True,
            controller_receipt_done=True,
            direct_apply_sets_flag=True,
            receipt_fold_registered=False,
            unsupported_receipt_result=True,
            router_visible_evidence_available=True,
            packet_batch_relayed=True,
            active_holder_leases_issued=True,
            false_control_blocker_recorded=True,
        )
    if scenario == DUPLICATE_REQUEUE_WHILE_RECEIPT_DONE:
        return _rejected(
            scenario,
            action_family="packet_relay",
            action_type="relay_material_scan_packets",
            postcondition_name="material_scan_packets_relayed",
            controller_receipt_possible=True,
            controller_receipt_done=True,
            direct_apply_sets_flag=True,
            receipt_fold_registered=False,
            router_visible_evidence_available=True,
            packet_batch_relayed=True,
            active_holder_leases_issued=True,
            same_action_requeued=True,
        )
    if scenario == DOWNSTREAM_WAIT_GATED_BY_UNFOLDED_DISPATCH:
        return _rejected(
            scenario,
            action_family="packet_relay",
            action_type="relay_material_scan_packets",
            postcondition_name="material_scan_packets_relayed",
            controller_receipt_possible=True,
            controller_receipt_done=True,
            direct_apply_sets_flag=True,
            receipt_fold_registered=False,
            router_visible_evidence_available=True,
            packet_batch_relayed=True,
            active_holder_leases_issued=True,
            worker_packet_opened_or_acknowledged=True,
            worker_result_still_pending=True,
            router_postcondition_flag_satisfied=False,
            downstream_wait_selected=False,
        )
    if scenario == RECONCILED_RECEIPT_WITHOUT_FLAG:
        return _rejected(
            scenario,
            action_family="packet_relay",
            action_type="relay_material_scan_packets",
            postcondition_name="material_scan_packets_relayed",
            controller_receipt_possible=True,
            controller_receipt_done=True,
            direct_apply_sets_flag=True,
            receipt_fold_registered=True,
            router_visible_evidence_available=True,
            packet_batch_relayed=True,
            active_holder_leases_issued=True,
            router_marked_receipt_reconciled=True,
            router_postcondition_flag_satisfied=False,
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
    failures = receipt_evidence_fold_failures(candidate)
    if not failures and state.scenario in VALID_SCENARIOS:
        yield Transition(f"accept_{state.scenario}", candidate)
    else:
        yield Transition(
            f"reject_{state.scenario}",
            replace(candidate, status="rejected", terminal_reason=failures[0] if failures else "negative scenario rejected"),
        )


class ControllerReceiptEvidenceFoldStep:
    """Model one Controller receipt reconciliation transition."""

    name = "ControllerReceiptEvidenceFoldStep"
    input_description = "Controller receipt plus Router-visible evidence"
    output_description = "Router-owned postcondition fold, wait, retry, or blocker"
    reads = (
        "controller_action_type",
        "controller_receipt_status",
        "direct_apply_flag_write_contract",
        "router_visible_evidence",
        "receipt_fold_registry",
        "router_owned_postcondition_flag",
        "downstream_wait_state",
    )
    writes = (
        "router_owned_postcondition_flag",
        "router_reconciliation_status",
        "control_blocker_or_retry",
        "next_wait_action",
    )
    idempotency = (
        "evidence-backed Controller receipts fold through a registered handler "
        "until the Router-owned flag is true; retry/blocker is reserved for "
        "missing or invalid evidence, not unsupported known action families"
    )

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def receipt_evidence_fold_failures(state: State) -> list[str]:
    failures: list[str] = []
    has_router_postcondition = state.postcondition_name != "none"
    if (
        state.controller_receipt_possible
        and has_router_postcondition
        and state.direct_apply_sets_flag
        and not state.receipt_fold_registered
    ):
        failures.append("direct apply writes a Router flag but Controller receipt has no registered evidence fold")
    if (
        state.controller_receipt_done
        and has_router_postcondition
        and state.router_visible_evidence_available
        and not state.receipt_fold_registered
    ):
        failures.append("evidence-backed Controller receipt has no registered fold handler")
    if (
        state.controller_receipt_done
        and state.router_visible_evidence_available
        and state.unsupported_receipt_result
    ):
        failures.append("evidence-backed Controller receipt returned unsupported_stateful_controller_receipt")
    if (
        state.false_control_blocker_recorded
        and state.router_visible_evidence_available
        and state.controller_receipt_done
        and has_router_postcondition
    ):
        failures.append("control blocker was recorded even though Router-visible evidence could satisfy the postcondition")
    if (
        state.same_action_requeued
        and state.controller_receipt_done
        and (state.router_visible_evidence_available or state.worker_packet_opened_or_acknowledged)
    ):
        failures.append("same Controller action was requeued while the previous receipt or packet work was already in flight")
    if (
        state.action_family == "packet_relay"
        and state.worker_packet_opened_or_acknowledged
        and state.worker_result_still_pending
        and state.router_visible_evidence_available
        and not state.router_postcondition_flag_satisfied
        and not state.downstream_wait_selected
    ):
        failures.append("worker wait was gated by an unfurled dispatch flag instead of evidence-backed packet relay")
    if (
        state.controller_receipt_done
        and state.receipt_fold_registered
        and state.router_visible_evidence_available
        and has_router_postcondition
        and not state.router_postcondition_flag_satisfied
        and not state.repair_or_blocker_recorded
    ):
        failures.append("registered receipt fold did not satisfy the Router-owned postcondition flag")
    if (
        state.router_marked_receipt_reconciled
        and has_router_postcondition
        and not state.router_postcondition_flag_satisfied
        and not state.repair_or_blocker_recorded
    ):
        failures.append("Controller receipt was marked reconciled while its Router-owned flag remained false")
    return failures


def accepts_only_safe_receipt_folds(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted":
        failures = receipt_evidence_fold_failures(state)
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
    return Workflow((ControllerReceiptEvidenceFoldStep(),), name="flowpilot_controller_receipt_evidence_fold")


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 2
INVARIANTS = (
    Invariant(
        name="controller_receipt_evidence_fold",
        description="Evidence-backed Controller receipts must fold into Router-owned flags or block only on missing evidence.",
        predicate=accepts_only_safe_receipt_folds,
    ),
)


def hazard_states() -> dict[str, State]:
    return {scenario: scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}
