"""FlowGuard model for the current FlowPilot startup-control path.

The current startup path is intentionally narrow:

1. Runtime records the user startup intake and current task contract.
2. Runtime/Router writes mechanical startup evidence and display status.
3. Runtime delivers the sealed `user_intake` mail to PM.
4. PM acknowledges the current startup-intake duty and starts the first work
   phase. Background role agents are opened on demand before role work.

Old FlowPilot startup-review paths are hazards only. A Reviewer startup fact
report, PM startup activation gate, fixed role-slot startup, or heartbeat
continuation must not be a legal way to advance this model.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_startup_control"

REQUIRED_LABELS = (
    "startup_intake_ui_completed",
    "startup_user_text_recorded",
    "router_records_startup_task_contract",
    "controller_loads_core_and_records_boundary",
    "router_writes_startup_mechanical_audit",
    "router_writes_startup_display_status",
    "router_delivers_user_intake_to_pm",
    "pm_acknowledges_startup_intake",
    "router_opens_current_role_agent_on_demand",
    "pm_product_architecture_card_delivered_after_user_intake",
    "pm_activates_route_after_current_entry",
    "router_issues_next_action_after_current_entry",
    "next_action_completes_without_router_error",
    "router_error_detected_for_next_action",
    "router_routes_sealed_repair_packet_to_responsible_role",
    "responsible_role_returns_repair_result_without_controller_body_access",
    "router_recovers_after_responsible_repair",
    "pm_closure_approved_before_lifecycle_continuation_close",
    "lifecycle_continuation_closed_after_pm_closure",
    "formal_user_stop_recorded",
    "formal_user_cancel_recorded",
)


@dataclass(frozen=True)
class Tick:
    """One abstract startup-control tick."""


@dataclass(frozen=True)
class Action:
    name: str
    recipient: str = "router"


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | stopped | cancelled | complete
    holder: str = "controller"

    startup_intake_ui_completed: bool = False
    user_text_recorded: bool = False
    startup_task_contract_recorded: bool = False
    controller_core_loaded: bool = False
    controller_boundary_evidence_written: bool = False
    startup_mechanical_audit_written: bool = False
    startup_display_status_written: bool = False
    user_intake_delivered_to_pm: bool = False
    pm_startup_intake_ack_clean: bool = False
    current_role_agent_opened_on_demand: bool = False
    product_architecture_card_delivered: bool = False
    active_route_exists: bool = False
    next_action_issued: bool = False
    route_work_completed: bool = False
    pm_closure_approved: bool = False
    lifecycle_continuation_closed: bool = False

    formal_lifecycle_signal: str = "none"  # none | stop | cancel
    future_actions_prevented: bool = False
    action_issued_after_lifecycle_signal: bool = False

    router_error_seen: bool = False
    repair_packet_registered: bool = False
    repair_packet_sealed: bool = False
    repair_packet_recipient: str = "none"
    controller_knows_repair_details: bool = False
    repair_result_returned_to_router: bool = False
    repair_result_body_read_by_controller: bool = False
    router_recovered_after_repair: bool = False

    # Old FlowPilot paths. These are forbidden hazards, not compatibility lanes.
    reviewer_startup_fact_gate_used: bool = False
    pm_startup_activation_gate_used: bool = False
    legacy_heartbeat_created: bool = False
    fixed_role_slots_started: bool = False
    reviewer_mechanical_fact_reproof_used: bool = False
    work_started_without_background_agent: bool = False


class Transition(NamedTuple):
    label: str
    recipient: str
    state: State


def initial_state() -> State:
    return State()


def _terminal_transition(state: State, signal: str) -> Transition:
    return Transition(
        f"formal_user_{signal}_recorded",
        "controller",
        replace(
            state,
            status="stopped" if signal == "stop" else "cancelled",
            holder="controller",
            formal_lifecycle_signal=signal,
            future_actions_prevented=True,
        ),
    )


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"stopped", "cancelled", "complete"}:
        return ()

    lifecycle = (
        _terminal_transition(state, "stop"),
        _terminal_transition(state, "cancel"),
    )

    if not state.startup_intake_ui_completed:
        return lifecycle + (
            Transition(
                "startup_intake_ui_completed",
                "controller",
                replace(state, status="running", startup_intake_ui_completed=True),
            ),
        )

    if not state.user_text_recorded:
        return lifecycle + (
            Transition(
                "startup_user_text_recorded",
                "controller",
                replace(state, user_text_recorded=True),
            ),
        )

    if not state.startup_task_contract_recorded:
        return lifecycle + (
            Transition(
                "router_records_startup_task_contract",
                "router",
                replace(state, holder="router", startup_task_contract_recorded=True),
            ),
        )

    if not state.controller_core_loaded:
        return lifecycle + (
            Transition(
                "controller_loads_core_and_records_boundary",
                "controller",
                replace(
                    state,
                    holder="controller",
                    controller_core_loaded=True,
                    controller_boundary_evidence_written=True,
                ),
            ),
        )

    if not state.startup_mechanical_audit_written:
        return lifecycle + (
            Transition(
                "router_writes_startup_mechanical_audit",
                "router",
                replace(state, holder="router", startup_mechanical_audit_written=True),
            ),
        )

    if not state.startup_display_status_written:
        return lifecycle + (
            Transition(
                "router_writes_startup_display_status",
                "router",
                replace(state, holder="router", startup_display_status_written=True),
            ),
        )

    if not state.user_intake_delivered_to_pm:
        return lifecycle + (
            Transition(
                "router_delivers_user_intake_to_pm",
                "project_manager",
                replace(state, holder="project_manager", user_intake_delivered_to_pm=True),
            ),
        )

    if not state.pm_startup_intake_ack_clean:
        return lifecycle + (
            Transition(
                "pm_acknowledges_startup_intake",
                "project_manager",
                replace(state, holder="project_manager", pm_startup_intake_ack_clean=True),
            ),
        )

    if not state.current_role_agent_opened_on_demand:
        return lifecycle + (
            Transition(
                "router_opens_current_role_agent_on_demand",
                "router",
                replace(state, holder="router", current_role_agent_opened_on_demand=True),
            ),
        )

    if not state.product_architecture_card_delivered:
        return lifecycle + (
            Transition(
                "pm_product_architecture_card_delivered_after_user_intake",
                "project_manager",
                replace(state, holder="project_manager", product_architecture_card_delivered=True),
            ),
        )

    if not state.active_route_exists:
        return lifecycle + (
            Transition(
                "pm_activates_route_after_current_entry",
                "project_manager",
                replace(state, holder="project_manager", active_route_exists=True),
            ),
        )

    if not state.next_action_issued:
        return lifecycle + (
            Transition(
                "router_issues_next_action_after_current_entry",
                "controller",
                replace(state, holder="controller", next_action_issued=True),
            ),
        )

    if not state.router_error_seen and not state.router_recovered_after_repair:
        return lifecycle + (
            Transition(
                "next_action_completes_without_router_error",
                "project_manager",
                replace(state, holder="project_manager", route_work_completed=True),
            ),
            Transition(
                "router_error_detected_for_next_action",
                "router",
                replace(state, holder="router", router_error_seen=True),
            ),
        )

    if state.router_error_seen and not state.repair_packet_registered:
        return lifecycle + (
            Transition(
                "router_routes_sealed_repair_packet_to_responsible_role",
                "worker",
                replace(
                    state,
                    holder="worker",
                    repair_packet_registered=True,
                    repair_packet_sealed=True,
                    repair_packet_recipient="worker",
                ),
            ),
        )

    if state.repair_packet_registered and not state.repair_result_returned_to_router:
        return lifecycle + (
            Transition(
                "responsible_role_returns_repair_result_without_controller_body_access",
                "worker",
                replace(
                    state,
                    holder="router",
                    repair_result_returned_to_router=True,
                    repair_result_body_read_by_controller=False,
                ),
            ),
        )

    if state.repair_result_returned_to_router and not state.router_recovered_after_repair:
        return lifecycle + (
            Transition(
                "router_recovers_after_responsible_repair",
                "router",
                replace(state, holder="controller", router_error_seen=False, router_recovered_after_repair=True),
            ),
        )

    if state.route_work_completed and not state.pm_closure_approved:
        return lifecycle + (
            Transition(
                "pm_closure_approved_before_lifecycle_continuation_close",
                "project_manager",
                replace(state, holder="project_manager", pm_closure_approved=True),
            ),
        )

    if state.pm_closure_approved and not state.lifecycle_continuation_closed:
        return lifecycle + (
            Transition(
                "lifecycle_continuation_closed_after_pm_closure",
                "controller",
                replace(state, status="complete", holder="controller", lifecycle_continuation_closed=True),
            ),
        )

    return lifecycle


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []

    if state.reviewer_startup_fact_gate_used:
        failures.append("legacy reviewer startup fact gate was used")
    if state.pm_startup_activation_gate_used:
        failures.append("legacy PM startup activation gate was used")
    if state.legacy_heartbeat_created:
        failures.append("legacy heartbeat continuation was created")
    if state.fixed_role_slots_started:
        failures.append("fixed startup role slots were started")
    if state.reviewer_mechanical_fact_reproof_used:
        failures.append("reviewer was asked to re-prove runtime/router mechanical facts")
    if state.work_started_without_background_agent:
        failures.append("role work started without current background agent opening")

    if state.user_text_recorded and not state.startup_intake_ui_completed:
        failures.append("startup user text was recorded before startup intake")
    if state.startup_task_contract_recorded and not state.user_text_recorded:
        failures.append("startup task contract was recorded before user text")
    if state.controller_core_loaded and not state.controller_boundary_evidence_written:
        failures.append("Controller core loaded without boundary evidence")
    if state.startup_mechanical_audit_written and not state.controller_core_loaded:
        failures.append("startup mechanical audit was written before Controller core")
    if state.startup_display_status_written and not state.startup_mechanical_audit_written:
        failures.append("startup display status was written before mechanical audit")
    if state.user_intake_delivered_to_pm and not (
        state.startup_mechanical_audit_written and state.startup_display_status_written
    ):
        failures.append("user_intake was delivered before runtime mechanical audit and display status")
    if state.pm_startup_intake_ack_clean and not state.user_intake_delivered_to_pm:
        failures.append("PM startup intake was acknowledged before user_intake delivery")
    if state.product_architecture_card_delivered and not (
        state.user_intake_delivered_to_pm
        and state.pm_startup_intake_ack_clean
        and state.current_role_agent_opened_on_demand
    ):
        failures.append("product architecture started before current PM entry and on-demand background agent opening")
    if state.active_route_exists and not state.product_architecture_card_delivered:
        failures.append("route was activated before first PM work entry")
    if state.next_action_issued and not state.active_route_exists:
        failures.append("next action was issued before active route")
    if state.route_work_completed and not state.next_action_issued:
        failures.append("route work completed before next action")
    if state.pm_closure_approved and not state.route_work_completed:
        failures.append("PM closure was approved before route work completed")
    if state.lifecycle_continuation_closed and not state.pm_closure_approved:
        failures.append("lifecycle continuation closed before PM closure")
    if state.status == "complete" and not (
        state.route_work_completed and state.pm_closure_approved and state.lifecycle_continuation_closed
    ):
        failures.append("startup control completed before route work, PM closure, and lifecycle close")
    if state.formal_lifecycle_signal in {"stop", "cancel"} and not state.future_actions_prevented:
        failures.append("formal user stop/cancel did not prevent future actions")
    if state.action_issued_after_lifecycle_signal:
        failures.append("action was issued after formal lifecycle stop/cancel")
    if state.repair_packet_registered and not state.repair_packet_sealed:
        failures.append("router repair packet was routed without being sealed")
    if state.repair_packet_registered and state.repair_packet_recipient == "controller":
        failures.append("router repair packet was routed to controller")
    if state.controller_knows_repair_details:
        failures.append("Controller learned sealed repair details")
    if state.repair_result_body_read_by_controller:
        failures.append("Controller read repair result body")
    if state.router_error_seen and state.status == "complete" and not state.router_recovered_after_repair:
        failures.append("startup control completed after router error without repair recovery")

    return failures


def hard_invariant(state: State, trace: object) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


def is_terminal(state: State) -> bool:
    return state.status in {"stopped", "cancelled", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete" and not invariant_failures(state)


class StartupControlStep:
    """Current startup-control transition.

    Input x State -> Set(Output x State)
    reads: startup intake, run state, boundary evidence, runtime mechanical
    audit, display status, user_intake mail, role-agent opening result
    writes: current startup entry state, next action, repair packet, terminal
    lifecycle marker
    """

    name = "StartupControlStep"
    reads = (
        "startup_intake",
        "controller_boundary",
        "startup_mechanical_audit",
        "startup_display_status",
        "user_intake_mail",
        "current_role_agent_binding",
    )
    writes = ("startup_entry_state", "next_action", "repair_packet", "terminal_lifecycle")
    input_description = "current startup control tick"
    output_description = "current startup entry state or terminal marker"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label, transition.recipient),
                new_state=transition.state,
                label=transition.label,
            )


INVARIANTS = (
    Invariant(
        "flowpilot_current_startup_control",
        "Startup advances only through runtime mechanics, PM user_intake, on-demand role-agent opening, and current route work.",
        hard_invariant,
    ),
)
EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 20


def build_workflow() -> Workflow:
    return Workflow((StartupControlStep(),), name=MODEL_ID)


def _ready_for_work() -> State:
    return State(
        status="running",
        startup_intake_ui_completed=True,
        user_text_recorded=True,
        startup_task_contract_recorded=True,
        controller_core_loaded=True,
        controller_boundary_evidence_written=True,
        startup_mechanical_audit_written=True,
        startup_display_status_written=True,
        user_intake_delivered_to_pm=True,
        pm_startup_intake_ack_clean=True,
        current_role_agent_opened_on_demand=True,
    )


def hazard_states() -> dict[str, State]:
    ready = _ready_for_work()
    return {
        "legacy_reviewer_startup_fact_gate": replace(ready, reviewer_startup_fact_gate_used=True),
        "legacy_pm_startup_activation_gate": replace(ready, pm_startup_activation_gate_used=True),
        "legacy_heartbeat_created": replace(ready, legacy_heartbeat_created=True),
        "fixed_role_slots_started": replace(ready, fixed_role_slots_started=True),
        "reviewer_mechanical_fact_reproof": replace(ready, reviewer_mechanical_fact_reproof_used=True),
        "work_without_background_agent": replace(
            ready,
            current_role_agent_opened_on_demand=False,
            product_architecture_card_delivered=True,
            work_started_without_background_agent=True,
        ),
        "product_architecture_before_user_intake": replace(
            State(
                status="running",
                startup_intake_ui_completed=True,
                user_text_recorded=True,
                startup_task_contract_recorded=True,
                controller_core_loaded=True,
                controller_boundary_evidence_written=True,
                startup_mechanical_audit_written=True,
                startup_display_status_written=True,
            ),
            product_architecture_card_delivered=True,
        ),
        "route_activation_before_current_entry": replace(ready, product_architecture_card_delivered=False, active_route_exists=True),
        "next_action_before_active_route": replace(ready, product_architecture_card_delivered=True, next_action_issued=True),
        "completion_before_pm_closure": replace(
            ready,
            product_architecture_card_delivered=True,
            active_route_exists=True,
            next_action_issued=True,
            route_work_completed=True,
            status="complete",
        ),
        "next_action_after_stop": replace(ready, formal_lifecycle_signal="stop", action_issued_after_lifecycle_signal=True),
        "unsealed_repair_packet": replace(ready, router_error_seen=True, repair_packet_registered=True, repair_packet_sealed=False, repair_packet_recipient="worker"),
        "repair_packet_to_controller": replace(ready, router_error_seen=True, repair_packet_registered=True, repair_packet_sealed=True, repair_packet_recipient="controller"),
        "controller_knows_repair_details": replace(ready, router_error_seen=True, repair_packet_registered=True, repair_packet_sealed=True, repair_packet_recipient="worker", controller_knows_repair_details=True),
    }
