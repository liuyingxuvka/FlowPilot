"""FlowGuard model for the new FlowPilot formal entrypoint."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_new_formal_entrypoint"
MAX_SEQUENCE_LENGTH = 20


@dataclass(frozen=True)
class State:
    status: str = "new"
    formal_use_flowpilot_request: bool = False
    old_startup_ui_opened: bool = False
    interactive_startup_result: bool = False
    sealed_intake_recorded: bool = False
    new_ledger_authority: bool = False
    contract_frozen: bool = False
    route_created: bool = False
    dynamic_agent_lease_requested: bool = False
    host_kind_value_menu_presented: bool = False
    host_kind_selected_from_allowed_menu: bool = False
    dynamic_agent_lease_bound: bool = False
    ack_recorded: bool = False
    result_submitted: bool = False
    flowguard_evidence_run_local: bool = False
    flowguard_targeted: bool = False
    independent_review_passed: bool = False
    validation_recorded: bool = False
    final_closure_complete: bool = False
    old_router_authority: bool = False
    monitor_ui_required: bool = False
    fixed_six_required: bool = False
    chat_body_leaked: bool = False
    headless_result_treated_as_formal: bool = False
    ack_only_completed: bool = False
    fake_host_claimed_live: bool = False
    host_kind_menu_missing: bool = False
    invented_host_kind_value: bool = False
    tracked_baseline_flowguard_evidence: bool = False


@dataclass(frozen=True)
class Tick:
    """One new-entrypoint transition."""


@dataclass(frozen=True)
class Action:
    label: str


class Transition(NamedTuple):
    label: str
    state: State


REQUIRED_SAFE_LABELS = (
    "receive_formal_use_flowpilot_request",
    "open_reused_startup_ui",
    "record_interactive_ui_result",
    "write_sealed_intake_to_new_ledger",
    "freeze_contract",
    "create_new_route",
    "request_dynamic_agent_lease",
    "present_host_kind_value_menu",
    "select_host_kind_from_allowed_menu",
    "bind_dynamic_agent_lease",
    "record_ack_as_liveness_only",
    "submit_result_artifact",
    "write_flowguard_evidence_to_run_local_path",
    "run_targeted_flowguard",
    "record_independent_review",
    "record_validation_evidence",
    "complete_final_backward_closure",
)


def initial_state() -> State:
    return State()


class NewFlowPilotEntrypointStep:
    name = "NewFlowPilotEntrypointStep"
    reads = (
        "formal_use_flowpilot_request",
        "old_startup_ui_opened",
        "sealed_intake_recorded",
        "new_ledger_authority",
        "route_created",
        "host_kind_value_menu_presented",
        "dynamic_agent_lease_bound",
        "flowguard_evidence_run_local",
        "flowguard_targeted",
        "independent_review_passed",
    )
    writes = (
        "startup_ui_result",
        "current_run_ledger",
        "route_state",
        "lease_state",
        "host_value_menu",
        "packet_result_state",
        "run_local_flowguard_evidence_path",
        "flowguard_report",
        "review_report",
        "closure",
    )
    input_description = "Input x State: one formal new FlowPilot entrypoint transition"
    output_description = "Set(Output x State): the next legal startup-to-closure state"
    idempotency = "safe transitions add current-run evidence without old router authority"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(output=Action(transition.label), new_state=transition.state, label=transition.label)


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"blocked", "complete"}:
        return ()
    failures = invariant_failures(state)
    if failures:
        return (Transition("blocked_on_new_entrypoint_invariant", replace(state, status="blocked")),)
    if state.status == "new":
        return (Transition("receive_formal_use_flowpilot_request", replace(state, status="running", formal_use_flowpilot_request=True)),)
    if not state.old_startup_ui_opened:
        return (Transition("open_reused_startup_ui", replace(state, old_startup_ui_opened=True)),)
    if not state.interactive_startup_result:
        return (Transition("record_interactive_ui_result", replace(state, interactive_startup_result=True)),)
    if not state.sealed_intake_recorded:
        return (Transition("write_sealed_intake_to_new_ledger", replace(state, sealed_intake_recorded=True, new_ledger_authority=True)),)
    if not state.contract_frozen:
        return (Transition("freeze_contract", replace(state, contract_frozen=True)),)
    if not state.route_created:
        return (Transition("create_new_route", replace(state, route_created=True)),)
    if not state.dynamic_agent_lease_requested:
        return (Transition("request_dynamic_agent_lease", replace(state, dynamic_agent_lease_requested=True)),)
    if not state.host_kind_value_menu_presented:
        return (Transition("present_host_kind_value_menu", replace(state, host_kind_value_menu_presented=True)),)
    if not state.host_kind_selected_from_allowed_menu:
        return (Transition("select_host_kind_from_allowed_menu", replace(state, host_kind_selected_from_allowed_menu=True)),)
    if not state.dynamic_agent_lease_bound:
        return (Transition("bind_dynamic_agent_lease", replace(state, dynamic_agent_lease_bound=True)),)
    if not state.ack_recorded:
        return (Transition("record_ack_as_liveness_only", replace(state, ack_recorded=True)),)
    if not state.result_submitted:
        return (Transition("submit_result_artifact", replace(state, result_submitted=True)),)
    if not state.flowguard_evidence_run_local:
        return (Transition("write_flowguard_evidence_to_run_local_path", replace(state, flowguard_evidence_run_local=True)),)
    if not state.flowguard_targeted:
        return (Transition("run_targeted_flowguard", replace(state, flowguard_targeted=True)),)
    if not state.independent_review_passed:
        return (Transition("record_independent_review", replace(state, independent_review_passed=True)),)
    if not state.validation_recorded:
        return (Transition("record_validation_evidence", replace(state, validation_recorded=True)),)
    if not state.final_closure_complete:
        return (Transition("complete_final_backward_closure", replace(state, final_closure_complete=True, status="complete")),)
    return ()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.old_startup_ui_opened and not state.formal_use_flowpilot_request:
        failures.append("startup UI opened before formal Use FlowPilot request")
    if state.interactive_startup_result and not state.old_startup_ui_opened:
        failures.append("startup result recorded before reused startup UI opened")
    if state.sealed_intake_recorded and not state.interactive_startup_result:
        failures.append("sealed intake recorded without interactive startup UI result")
    if state.new_ledger_authority and not state.sealed_intake_recorded:
        failures.append("new ledger became authority before sealed intake")
    if state.contract_frozen and not state.new_ledger_authority:
        failures.append("contract frozen before new ledger authority")
    if state.route_created and not state.contract_frozen:
        failures.append("route created before contract freeze")
    if state.dynamic_agent_lease_requested and not state.route_created:
        failures.append("dynamic agent requested before route creation")
    if state.host_kind_value_menu_presented and not state.dynamic_agent_lease_requested:
        failures.append("host kind menu presented before router requested a dynamic agent")
    if state.host_kind_selected_from_allowed_menu and not state.host_kind_value_menu_presented:
        failures.append("host kind value selected before the allowed-value menu was presented")
    if state.dynamic_agent_lease_bound and not state.host_kind_selected_from_allowed_menu:
        failures.append("agent lease bound before host kind was selected from the allowed-value menu")
    if state.ack_recorded and not state.dynamic_agent_lease_bound:
        failures.append("ACK recorded before dynamic lease was bound")
    if state.result_submitted and not state.ack_recorded:
        failures.append("result submitted before ACK liveness")
    if state.flowguard_evidence_run_local and not state.result_submitted:
        failures.append("FlowGuard evidence path was selected before result artifact")
    if state.flowguard_targeted and not state.flowguard_evidence_run_local:
        failures.append("FlowGuard ran before run-local evidence output was selected")
    if state.independent_review_passed and not state.flowguard_targeted:
        failures.append("review passed before targeted FlowGuard evidence")
    if state.validation_recorded and not state.independent_review_passed:
        failures.append("validation recorded before independent review")
    if state.final_closure_complete and not state.validation_recorded:
        failures.append("final closure completed before validation evidence")
    if state.old_router_authority:
        failures.append("old flowpilot_router authority was used by the new system")
    if state.monitor_ui_required:
        failures.append("non-startup monitoring UI was required")
    if state.fixed_six_required:
        failures.append("fixed six agents were required instead of dynamic leases")
    if state.chat_body_leaked:
        failures.append("sealed startup body leaked into chat/status")
    if state.headless_result_treated_as_formal:
        failures.append("headless startup result was treated as formal UI evidence")
    if state.ack_only_completed:
        failures.append("ACK-only liveness was treated as completion")
    if state.fake_host_claimed_live:
        failures.append("fake host evidence was claimed as live host confidence")
    if state.host_kind_menu_missing:
        failures.append("host kind was requested without an allowed-value menu")
    if state.invented_host_kind_value:
        failures.append("an unlisted host kind value was invented")
    if state.tracked_baseline_flowguard_evidence:
        failures.append("formal FlowGuard evidence wrote to a tracked simulation baseline")
    return failures


def is_success(state: State) -> bool:
    return state.status == "complete" and state.final_closure_complete and not invariant_failures(state)


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
    return {
        "old_router_authority": replace(target_state(), old_router_authority=True),
        "monitor_ui_required": replace(target_state(), monitor_ui_required=True),
        "fixed_six_required": replace(target_state(), fixed_six_required=True),
        "chat_body_leak": replace(target_state(), chat_body_leaked=True),
        "headless_formal_overclaim": replace(target_state(), headless_result_treated_as_formal=True),
        "ack_only_completion": replace(target_state(), ack_only_completed=True),
        "fake_live_overclaim": replace(target_state(), fake_host_claimed_live=True),
        "missing_host_kind_menu": replace(
            target_state(),
            host_kind_value_menu_presented=False,
            host_kind_selected_from_allowed_menu=True,
            dynamic_agent_lease_bound=True,
        ),
        "invented_host_kind_value": replace(target_state(), invented_host_kind_value=True),
        "tracked_baseline_flowguard_evidence": replace(target_state(), tracked_baseline_flowguard_evidence=True),
        "flowguard_without_run_local_evidence": replace(target_state(), flowguard_evidence_run_local=False, flowguard_targeted=True),
        "route_before_ledger": replace(target_state(), new_ledger_authority=False, contract_frozen=True, route_created=True),
        "review_before_flowguard": replace(target_state(), flowguard_targeted=False, independent_review_passed=True),
    }


def build_workflow() -> Workflow:
    return Workflow(blocks=(NewFlowPilotEntrypointStep(),), name=MODEL_ID)


def _invariant(state: State, trace: object) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "new_flowpilot_entrypoint_order_and_authority",
        "A fresh FlowPilot run reuses only startup UI, then advances through the new current-run ledger, dynamic leases, FlowGuard, review, validation, and closure.",
        _invariant,
    ),
)
EXTERNAL_INPUTS = (Tick(),)
