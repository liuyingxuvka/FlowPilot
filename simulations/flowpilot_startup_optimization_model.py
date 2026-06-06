"""FlowGuard model for the current FlowPilot startup path.

Risk intent brief:
- Keep startup compressed around current-runtime mechanics, not old gates.
- Runtime/Router owns startup facts: current run, sealed startup intake,
  mechanical audit, display receipt, user-intake mail, packet paths, hashes,
  and current role-agent binding.
- PM starts with startup intake and later route planning. Reviewer never
  re-proves mechanical facts, and PM never opens a startup activation gate.
- Background or parallel role agents are mandatory, but they are opened on
  demand for the current role/work binding. If opening a required role agent
  fails, FlowPilot stops instead of falling back to foreground-only work.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


REQUIRED_LABELS = (
    "startup_answers_recorded",
    "run_shell_created",
    "controller_loaded_for_runtime_mechanics",
    "controller_confirms_boundary",
    "startup_intake_record_bound",
    "router_writes_mechanical_audit",
    "controller_writes_display_status",
    "router_exposes_user_intake_mail",
    "pm_startup_intake_ack_recorded",
    "pm_starts_route_planning",
    "first_role_work_allocated",
    "current_role_agent_opened_on_demand",
    "route_work_allowed_after_current_agent",
)


@dataclass(frozen=True)
class Tick:
    """One abstract startup-path tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | stopped | complete

    startup_answers_recorded: bool = False
    background_collaboration_authorized: bool = True
    run_shell_created: bool = False
    current_pointer_written: bool = False
    run_index_updated: bool = False

    controller_loaded: bool = False
    controller_boundary_confirmed: bool = False
    controller_read_sealed_body: bool = False
    self_attested_claim_used_as_proof: bool = False

    startup_intake_record_current: bool = False
    startup_intake_body_sealed: bool = False
    mechanical_audit_written: bool = False
    router_owned_mechanical_proof_current: bool = False
    display_status_written: bool = False
    display_receipt_current: bool = False

    user_intake_mail_exposed: bool = False
    user_intake_exposed_before_runtime_ready: bool = False
    pm_startup_intake_card_delivered: bool = False
    pm_startup_intake_ack_recorded: bool = False
    pm_startup_intake_ack_via_common_ledger: bool = False

    pm_route_planning_started: bool = False
    route_work_started: bool = False
    first_role_work_allocated: bool = False
    current_role_agent_open_attempted: bool = False
    current_role_agent_bound: bool = False
    current_role_agent_failed: bool = False
    stopped_after_agent_failure: bool = False

    startup_background_agents_preleased: bool = False
    fixed_role_count_gate_required: bool = False
    heartbeat_or_manual_resume_binding_required: bool = False
    reviewer_mechanical_fact_gate_used: bool = False
    reviewer_required_to_reprove_router_facts: bool = False
    pm_startup_activation_gate_used: bool = False
    fallback_foreground_only_work_used: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _inc(state: State, **changes: object) -> State:
    return replace(state, status="running", **changes)


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"complete", "stopped"}:
        return
    if not state.startup_answers_recorded:
        yield Transition("startup_answers_recorded", _inc(state, startup_answers_recorded=True))
        return
    if not state.run_shell_created:
        yield Transition(
            "run_shell_created",
            _inc(state, run_shell_created=True, current_pointer_written=True, run_index_updated=True),
        )
        return
    if not state.controller_loaded:
        yield Transition("controller_loaded_for_runtime_mechanics", _inc(state, controller_loaded=True))
        return
    if not state.controller_boundary_confirmed:
        yield Transition("controller_confirms_boundary", _inc(state, controller_boundary_confirmed=True))
        return
    if not state.startup_intake_record_current:
        yield Transition(
            "startup_intake_record_bound",
            _inc(state, startup_intake_record_current=True, startup_intake_body_sealed=True),
        )
        return
    if not state.mechanical_audit_written:
        yield Transition(
            "router_writes_mechanical_audit",
            _inc(state, mechanical_audit_written=True, router_owned_mechanical_proof_current=True),
        )
        return
    if not state.display_status_written:
        yield Transition(
            "controller_writes_display_status",
            _inc(state, display_status_written=True, display_receipt_current=True),
        )
        return
    if not state.user_intake_mail_exposed:
        yield Transition("router_exposes_user_intake_mail", _inc(state, user_intake_mail_exposed=True))
        return
    if not state.pm_startup_intake_ack_recorded:
        yield Transition(
            "pm_startup_intake_ack_recorded",
            _inc(
                state,
                pm_startup_intake_card_delivered=True,
                pm_startup_intake_ack_recorded=True,
                pm_startup_intake_ack_via_common_ledger=True,
            ),
        )
        return
    if not state.pm_route_planning_started:
        yield Transition("pm_starts_route_planning", _inc(state, pm_route_planning_started=True))
        return
    if not state.first_role_work_allocated:
        yield Transition("first_role_work_allocated", _inc(state, first_role_work_allocated=True))
        return
    if not state.current_role_agent_open_attempted:
        yield Transition(
            "current_role_agent_opened_on_demand",
            _inc(
                state,
                current_role_agent_open_attempted=True,
                current_role_agent_bound=True,
            ),
        )
        return
    if not state.route_work_started:
        yield Transition(
            "route_work_allowed_after_current_agent",
            replace(state, status="complete", route_work_started=True),
        )
        return


class StartupOptimizationStep:
    """Model one current startup transition.

    Input x State -> Set(Output x State)
    reads: startup answers, run pointers, sealed startup intake, runtime audit,
    display receipt, PM startup-intake ACK, current work allocation, and role
    agent binding evidence.
    writes: one startup control-plane action and its current-runtime evidence.
    idempotency: completed evidence is monotonic and current-run scoped.
    """

    name = "StartupOptimizationStep"
    reads = (
        "startup_answers",
        "run_state",
        "startup_intake_record",
        "startup_mechanical_audit",
        "display_surface",
        "controller_action_ledger",
        "card_pending_return_ledger",
        "user_intake_mail",
        "current_role_agent_binding",
    )
    writes = (
        "run_state",
        "startup_mechanical_audit",
        "display_surface",
        "controller_action_ledger",
        "card_ledger",
        "user_intake_mail",
        "current_role_agent_binding",
        "execution_frontier",
    )
    input_description = "one FlowPilot startup optimization tick"
    output_description = "one legal current startup action"
    idempotency = "startup evidence flags are monotonic and current-run scoped"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status == "new":
        return failures
    if not state.background_collaboration_authorized:
        failures.append("background collaboration was not authorized for mandatory FlowPilot role agents")
    if state.startup_background_agents_preleased:
        failures.append("startup pre-leased background agents instead of opening current role agents on demand")
    if state.fixed_role_count_gate_required:
        failures.append("startup required a fixed role-count gate")
    if state.heartbeat_or_manual_resume_binding_required:
        failures.append("startup required heartbeat or manual resume binding liveness")
    if state.controller_loaded and not state.run_shell_created:
        failures.append("Controller loaded before current run shell existed")
    if state.controller_read_sealed_body:
        failures.append("Controller read sealed startup or role body during startup")
    if state.self_attested_claim_used_as_proof:
        failures.append("self-attested startup claim was used as runtime proof")
    if state.mechanical_audit_written and not (
        state.controller_boundary_confirmed
        and state.startup_intake_record_current
        and state.startup_intake_body_sealed
        and state.router_owned_mechanical_proof_current
    ):
        failures.append("startup mechanical audit was written without current sealed intake and router proof")
    if state.display_status_written and not (
        state.mechanical_audit_written and state.display_receipt_current
    ):
        failures.append("startup display status was written without current audit and display receipt")
    if state.user_intake_exposed_before_runtime_ready or (
        state.user_intake_mail_exposed
        and not (
            state.mechanical_audit_written
            and state.router_owned_mechanical_proof_current
            and state.display_status_written
            and state.display_receipt_current
        )
    ):
        failures.append("user_intake mail was exposed before startup runtime mechanics were ready")
    if state.reviewer_mechanical_fact_gate_used:
        failures.append("Reviewer startup mechanical fact gate was used")
    if state.reviewer_required_to_reprove_router_facts:
        failures.append("Reviewer was required to re-prove router-owned mechanical facts")
    if state.pm_startup_activation_gate_used:
        failures.append("PM startup activation gate was used")
    if state.pm_startup_intake_ack_recorded and not (
        state.user_intake_mail_exposed
        and state.pm_startup_intake_card_delivered
        and state.pm_startup_intake_ack_via_common_ledger
    ):
        failures.append("PM startup intake ACK bypassed user_intake mail or common card ledger")
    if state.pm_route_planning_started and not state.pm_startup_intake_ack_recorded:
        failures.append("PM route planning started before PM startup intake ACK")
    if state.first_role_work_allocated and not state.pm_route_planning_started:
        failures.append("role work was allocated before PM route planning")
    if state.route_work_started and not (
        state.first_role_work_allocated
        and state.current_role_agent_open_attempted
        and state.current_role_agent_bound
    ):
        failures.append("route work started without a current role-agent binding")
    if state.current_role_agent_failed and not state.stopped_after_agent_failure:
        failures.append("FlowPilot continued after required current role-agent opening failed")
    if state.fallback_foreground_only_work_used:
        failures.append("FlowPilot used foreground-only fallback work after role-agent failure")
    return failures


def startup_optimization_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_current_startup_path_has_no_legacy_gates",
        description=(
            "Startup optimization preserves the single current runtime path: "
            "runtime mechanics, PM startup intake, and on-demand current role agents."
        ),
        predicate=startup_optimization_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 14


def build_workflow() -> Workflow:
    return Workflow((StartupOptimizationStep(),), name="flowpilot_startup_optimization")


def is_terminal(state: State) -> bool:
    return state.status in {"complete", "stopped"}


def is_success(state: State) -> bool:
    return state.status == "complete" and not invariant_failures(state)


def optimized_plan_state(**changes: object) -> State:
    return replace(
        State(
            status="complete",
            startup_answers_recorded=True,
            background_collaboration_authorized=True,
            run_shell_created=True,
            current_pointer_written=True,
            run_index_updated=True,
            controller_loaded=True,
            controller_boundary_confirmed=True,
            startup_intake_record_current=True,
            startup_intake_body_sealed=True,
            mechanical_audit_written=True,
            router_owned_mechanical_proof_current=True,
            display_status_written=True,
            display_receipt_current=True,
            user_intake_mail_exposed=True,
            pm_startup_intake_card_delivered=True,
            pm_startup_intake_ack_recorded=True,
            pm_startup_intake_ack_via_common_ledger=True,
            pm_route_planning_started=True,
            first_role_work_allocated=True,
            current_role_agent_open_attempted=True,
            current_role_agent_bound=True,
            route_work_started=True,
        ),
        **changes,
    )


def hazard_states() -> dict[str, State]:
    safe = optimized_plan_state()
    return {
        "background_not_authorized": replace(safe, background_collaboration_authorized=False),
        "startup_background_agents_preleased": replace(safe, startup_background_agents_preleased=True),
        "fixed_role_count_gate_required": replace(safe, fixed_role_count_gate_required=True),
        "heartbeat_or_manual_resume_binding_required": replace(safe, heartbeat_or_manual_resume_binding_required=True),
        "controller_loaded_before_run": replace(safe, run_shell_created=False),
        "controller_reads_sealed_body": replace(safe, controller_read_sealed_body=True),
        "self_attested_proof": replace(safe, self_attested_claim_used_as_proof=True),
        "mechanical_audit_without_current_intake": replace(safe, startup_intake_record_current=False),
        "display_status_without_runtime_ready": replace(safe, mechanical_audit_written=False),
        "user_intake_before_runtime_ready": replace(safe, user_intake_exposed_before_runtime_ready=True),
        "reviewer_mechanical_fact_gate_used": replace(safe, reviewer_mechanical_fact_gate_used=True),
        "reviewer_reproves_router_facts": replace(safe, reviewer_required_to_reprove_router_facts=True),
        "pm_startup_activation_gate_used": replace(safe, pm_startup_activation_gate_used=True),
        "pm_intake_ack_bypasses_common_ledger": replace(safe, pm_startup_intake_ack_via_common_ledger=False),
        "pm_route_planning_before_pm_intake": replace(safe, pm_startup_intake_ack_recorded=False),
        "role_work_before_pm_route_planning": replace(safe, pm_route_planning_started=False),
        "route_work_without_current_role_agent": replace(safe, current_role_agent_bound=False),
        "role_agent_failure_continues": replace(
            safe,
            current_role_agent_failed=True,
            stopped_after_agent_failure=False,
        ),
        "foreground_only_fallback_used": replace(safe, fallback_foreground_only_work_used=True),
    }


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "REQUIRED_LABELS",
    "State",
    "Tick",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "optimized_plan_state",
]
