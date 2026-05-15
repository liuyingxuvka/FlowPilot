"""FlowGuard model for FlowPilot startup optimization.

Risk intent brief:
- Validate the planned startup compression before runtime changes land.
- Protect harms: roles marked ready without core prompt/I/O receipts, delayed
  heartbeat binding, reviewer startup fact checks starting before common-ledger
  startup prep ACK clearance, reviewer re-proof of router-owned mechanical
  facts, hidden display evidence, PM activation before reviewer report
  acceptance, and
  Controller proof/body boundary violations.
- Modeled state and side effects: startup answers, run shell, six-role ledger,
  role-core delivery, heartbeat host proof, Controller boundary confirmation,
  mechanical audit, display receipt, reviewer startup fact card, PM prep cards,
  common Controller/card ledgers, reviewer report acceptance, pre-review
  startup ACK join, PM activation, and route work release.
- Hard invariants: optimizations may reduce handoffs only when current-run
  heartbeat, six-role authority, role core receipts, reviewer external-fact
  review, common ledger ACK clearance, PM activation, and Controller
  envelope-only boundaries remain intact.
- Blindspot: this is a control-plane model. Host-specific subagent spawn and
  Codex heartbeat behavior still require runtime tests and local install checks.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


REQUIRED_LABELS = (
    "startup_answers_recorded",
    "run_shell_created",
    "six_roles_started_with_core_prompt_receipts",
    "early_heartbeat_bound_to_current_run",
    "controller_loaded_after_startup_receipts",
    "controller_confirms_boundary",
    "router_writes_mechanical_audit_and_display_receipt",
    "pm_prep_runs_before_reviewer_dispatch",
    "startup_common_ack_join_checked_before_reviewer",
    "reviewer_startup_fact_card_dispatched_after_join",
    "reviewer_report_accepted_after_ack_clearance",
    "pm_opens_startup_after_reviewer_report",
    "route_work_allowed_after_pm_activation",
)


@dataclass(frozen=True)
class Tick:
    """One abstract startup-optimization tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | complete

    startup_answers_recorded: bool = False
    scheduled_continuation_requested: bool = True
    run_shell_created: bool = False
    current_pointer_written: bool = False
    run_index_updated: bool = False

    six_roles_started: bool = False
    role_ledger_current_run: bool = False
    role_core_prompts_delivered_at_spawn: bool = False
    role_core_prompt_hashes_recorded: bool = False
    role_io_protocol_receipts_current: bool = False
    later_core_injection_required: bool = False
    fewer_than_six_roles_used: bool = False

    heartbeat_created: bool = False
    heartbeat_created_before_run_or_roles: bool = False
    heartbeat_bound_to_current_run: bool = False
    heartbeat_interval_minutes: int = 0
    heartbeat_host_proof_verified: bool = False

    controller_loaded: bool = False
    controller_boundary_confirmed: bool = False
    controller_read_sealed_body: bool = False
    self_attested_claim_used_as_proof: bool = False

    mechanical_audit_written: bool = False
    router_owned_mechanical_proof_current: bool = False
    display_receipt_written: bool = False
    display_receipt_visible_to_reviewer: bool = False

    reviewer_fact_card_dispatched: bool = False
    reviewer_fact_card_dispatched_after_pre_review_join: bool = False
    reviewer_required_to_reprove_router_facts: bool = False
    reviewer_report_returned: bool = False
    reviewer_external_facts_checked: bool = False

    controller_action_ledger_used: bool = False
    card_pending_return_ledger_used: bool = False
    router_synced_common_ledgers: bool = False
    startup_card_ack_pending: bool = False
    independent_startup_dispatch_continues_with_pending_ack: bool = False
    startup_ack_join_checked_common_ledger: bool = False
    startup_ack_join_clean: bool = False
    startup_only_wait_table_created: bool = False

    pm_prep_started: bool = False
    pm_prep_independent_before_reviewer_dispatch: bool = False
    pm_prep_join_policy_recorded: bool = False
    pm_prep_completed: bool = False
    pm_prep_blocked_reviewer: bool = False

    startup_review_report_accepted: bool = False
    pm_activation_approved: bool = False
    work_beyond_startup_allowed: bool = False
    route_or_material_work_started: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _inc(state: State, **changes: object) -> State:
    return replace(state, status="running", **changes)


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "complete":
        return
    if not state.startup_answers_recorded:
        yield Transition("startup_answers_recorded", _inc(state, startup_answers_recorded=True))
        return
    if not state.run_shell_created:
        yield Transition(
            "run_shell_created",
            _inc(
                state,
                run_shell_created=True,
                current_pointer_written=True,
                run_index_updated=True,
            ),
        )
        return
    if not state.six_roles_started:
        yield Transition(
            "six_roles_started_with_core_prompt_receipts",
            _inc(
                state,
                six_roles_started=True,
                role_ledger_current_run=True,
                role_core_prompts_delivered_at_spawn=True,
                role_core_prompt_hashes_recorded=True,
                role_io_protocol_receipts_current=True,
                later_core_injection_required=False,
            ),
        )
        return
    if state.scheduled_continuation_requested and not state.heartbeat_created:
        yield Transition(
            "early_heartbeat_bound_to_current_run",
            _inc(
                state,
                heartbeat_created=True,
                heartbeat_bound_to_current_run=True,
                heartbeat_interval_minutes=1,
                heartbeat_host_proof_verified=True,
            ),
        )
        return
    if not state.controller_loaded:
        yield Transition(
            "controller_loaded_after_startup_receipts",
            _inc(state, controller_loaded=True),
        )
        return
    if not state.controller_boundary_confirmed:
        yield Transition(
            "controller_confirms_boundary",
            _inc(state, controller_boundary_confirmed=True),
        )
        return
    if not state.mechanical_audit_written:
        yield Transition(
            "router_writes_mechanical_audit_and_display_receipt",
            _inc(
                state,
                mechanical_audit_written=True,
                router_owned_mechanical_proof_current=True,
                display_receipt_written=True,
                display_receipt_visible_to_reviewer=True,
            ),
        )
        return
    if not state.pm_prep_started:
        yield Transition(
            "pm_prep_runs_before_reviewer_dispatch",
            _inc(
                state,
                pm_prep_started=True,
                pm_prep_independent_before_reviewer_dispatch=True,
                pm_prep_join_policy_recorded=True,
                pm_prep_completed=True,
                controller_action_ledger_used=True,
                card_pending_return_ledger_used=True,
                startup_card_ack_pending=True,
                independent_startup_dispatch_continues_with_pending_ack=True,
            ),
        )
        return
    if not state.startup_ack_join_checked_common_ledger:
        yield Transition(
            "startup_common_ack_join_checked_before_reviewer",
            _inc(
                state,
                router_synced_common_ledgers=True,
                startup_card_ack_pending=False,
                startup_ack_join_checked_common_ledger=True,
                startup_ack_join_clean=True,
            ),
        )
        return
    if not state.reviewer_fact_card_dispatched:
        yield Transition(
            "reviewer_startup_fact_card_dispatched_after_join",
            _inc(
                state,
                reviewer_fact_card_dispatched=True,
                reviewer_fact_card_dispatched_after_pre_review_join=state.startup_ack_join_clean,
                controller_action_ledger_used=True,
                card_pending_return_ledger_used=True,
                startup_card_ack_pending=True,
                startup_ack_join_clean=False,
            ),
        )
        return
    if not state.reviewer_report_returned:
        yield Transition(
            "reviewer_report_accepted_after_ack_clearance",
            _inc(
                state,
                reviewer_report_returned=True,
                reviewer_external_facts_checked=True,
                startup_card_ack_pending=False,
                startup_ack_join_clean=True,
                startup_review_report_accepted=True,
            ),
        )
        return
    if not state.pm_activation_approved:
        yield Transition(
            "pm_opens_startup_after_reviewer_report",
            _inc(
                state,
                pm_activation_approved=True,
                work_beyond_startup_allowed=True,
            ),
        )
        return
    if not state.route_or_material_work_started:
        yield Transition(
            "route_work_allowed_after_pm_activation",
            replace(state, status="complete", route_or_material_work_started=True),
        )
        return


class StartupOptimizationStep:
    """Model one optimized startup transition.

    Input x State -> Set(Output x State)
    reads: startup answers, run pointers, crew ledger, role-core receipts,
    continuation proof, controller boundary, audit/display evidence, reviewer
    report, PM prep completion, PM activation.
    writes: one startup control-plane action and its durable evidence flag.
    idempotency: completed evidence is monotonic and is not duplicated or
    downgraded by later transitions.
    """

    name = "StartupOptimizationStep"
    reads = (
        "startup_answers",
        "run_state",
        "crew_ledger",
        "role_core_prompt_delivery",
        "continuation_binding",
        "startup_mechanical_audit",
        "display_surface",
        "controller_action_ledger",
        "card_pending_return_ledger",
        "reviewer_report",
        "pm_prep_state",
        "pm_activation",
    )
    writes = (
        "crew_ledger",
        "role_core_prompt_delivery",
        "continuation_binding",
        "startup_mechanical_audit",
        "display_surface",
        "controller_action_ledger",
        "card_ledger",
        "startup_activation",
        "execution_frontier",
    )
    input_description = "one FlowPilot startup optimization tick"
    output_description = "one legal optimized startup action"
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
    if state.fewer_than_six_roles_used or (
        state.six_roles_started
        and not (
            state.role_ledger_current_run
            and state.role_core_prompts_delivered_at_spawn
            and state.role_core_prompt_hashes_recorded
            and state.role_io_protocol_receipts_current
        )
    ):
        failures.append("roles became ready without six current-run role slots, core prompt hashes, and role I/O receipts")
    if state.later_core_injection_required:
        failures.append("optimized startup still required a delayed role-core injection gate")
    if state.heartbeat_created_before_run_or_roles:
        failures.append("heartbeat was created before current run and role ledger existed")
    if state.scheduled_continuation_requested:
        if state.reviewer_fact_card_dispatched and not state.heartbeat_created:
            failures.append("reviewer startup fact card was dispatched before early heartbeat binding")
        if state.heartbeat_created and not (
            state.run_shell_created
            and state.six_roles_started
            and state.heartbeat_bound_to_current_run
            and state.heartbeat_interval_minutes == 1
            and state.heartbeat_host_proof_verified
        ):
            failures.append("heartbeat lacked current-run one-minute verified host proof")
    if state.controller_loaded and not (
        state.run_shell_created and state.six_roles_started
    ):
        failures.append("Controller loaded before run shell and six-role startup receipts existed")
    if state.controller_read_sealed_body:
        failures.append("Controller read sealed role body during startup optimization")
    if state.self_attested_claim_used_as_proof:
        failures.append("self-attested startup claim was used as proof")
    if state.mechanical_audit_written and not (
        state.controller_boundary_confirmed
        and state.router_owned_mechanical_proof_current
        and state.display_receipt_written
    ):
        failures.append("startup mechanical audit/display receipt was written before controller boundary and router proof")
    if state.reviewer_fact_card_dispatched and not (
        state.mechanical_audit_written
        and state.router_owned_mechanical_proof_current
        and state.display_receipt_visible_to_reviewer
    ):
        failures.append("reviewer startup fact card lacked current mechanical proof or display evidence")
    if state.reviewer_required_to_reprove_router_facts:
        failures.append("reviewer was required to re-prove router-owned mechanical facts")
    if (state.reviewer_fact_card_dispatched or state.pm_prep_started) and not state.controller_action_ledger_used:
        failures.append("startup actions bypassed the common Controller action ledger")
    if state.reviewer_fact_card_dispatched and not state.card_pending_return_ledger_used:
        failures.append("startup card ACK bypassed the common pending-return ledger")
    if state.startup_only_wait_table_created:
        failures.append("startup ACK join used a separate startup-only wait table")
    if (
        state.pm_prep_started
        and state.startup_card_ack_pending
        and not state.independent_startup_dispatch_continues_with_pending_ack
    ):
        failures.append("pending startup ACK blocked independent startup dispatch instead of common-ledger deferral")
    if state.reviewer_fact_card_dispatched and not state.reviewer_fact_card_dispatched_after_pre_review_join:
        failures.append("reviewer startup fact card was dispatched before common startup prep ACK join")
    if state.pm_prep_started and not (
        state.pm_prep_independent_before_reviewer_dispatch
        and state.pm_prep_join_policy_recorded
    ):
        failures.append("PM prep lacked independence and join policy before reviewer startup review")
    if state.pm_prep_blocked_reviewer:
        failures.append("PM prep blocked reviewer startup fact progress")
    if state.startup_review_report_accepted and not (
        state.reviewer_report_returned
        and state.reviewer_external_facts_checked
        and state.pm_prep_completed
        and state.startup_ack_join_clean
    ):
        failures.append("startup review report was accepted before reviewer report, PM prep completion, and ACK clearance")
    if state.startup_ack_join_clean and not (
        state.startup_ack_join_checked_common_ledger
        and state.router_synced_common_ledgers
        and state.card_pending_return_ledger_used
        and not state.startup_card_ack_pending
    ):
        failures.append("startup ACK join was marked clean without common ledger sync and clear pending returns")
    if state.pm_activation_approved and not state.startup_review_report_accepted:
        failures.append("PM startup activation occurred before reviewer startup report acceptance")
    if state.work_beyond_startup_allowed and not state.pm_activation_approved:
        failures.append("work beyond startup was allowed before PM startup activation")
    if state.route_or_material_work_started and not state.work_beyond_startup_allowed:
        failures.append("route or material work started before startup activation opened")
    return failures


def startup_optimization_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_startup_optimization_preserves_startup_guards",
        description=(
            "Startup compression preserves current-run roles, role core "
            "receipts, early heartbeat, reviewer external-fact review, PM join, "
            "and Controller boundaries."
        ),
        predicate=startup_optimization_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 15


def build_workflow() -> Workflow:
    return Workflow((StartupOptimizationStep(),), name="flowpilot_startup_optimization")


def is_terminal(state: State) -> bool:
    return state.status == "complete"


def is_success(state: State) -> bool:
    return state.status == "complete" and not invariant_failures(state)


def optimized_plan_state(**changes: object) -> State:
    return replace(
        State(
            status="complete",
            startup_answers_recorded=True,
            scheduled_continuation_requested=True,
            run_shell_created=True,
            current_pointer_written=True,
            run_index_updated=True,
            six_roles_started=True,
            role_ledger_current_run=True,
            role_core_prompts_delivered_at_spawn=True,
            role_core_prompt_hashes_recorded=True,
            role_io_protocol_receipts_current=True,
            heartbeat_created=True,
            heartbeat_bound_to_current_run=True,
            heartbeat_interval_minutes=1,
            heartbeat_host_proof_verified=True,
            controller_loaded=True,
            controller_boundary_confirmed=True,
            mechanical_audit_written=True,
            router_owned_mechanical_proof_current=True,
            display_receipt_written=True,
            display_receipt_visible_to_reviewer=True,
            reviewer_fact_card_dispatched=True,
            reviewer_fact_card_dispatched_after_pre_review_join=True,
            reviewer_report_returned=True,
            reviewer_external_facts_checked=True,
            controller_action_ledger_used=True,
            card_pending_return_ledger_used=True,
            router_synced_common_ledgers=True,
            startup_card_ack_pending=False,
            independent_startup_dispatch_continues_with_pending_ack=True,
            startup_ack_join_checked_common_ledger=True,
            startup_ack_join_clean=True,
            pm_prep_started=True,
            pm_prep_independent_before_reviewer_dispatch=True,
            pm_prep_join_policy_recorded=True,
            pm_prep_completed=True,
            startup_review_report_accepted=True,
            pm_activation_approved=True,
            work_beyond_startup_allowed=True,
            route_or_material_work_started=True,
        ),
        **changes,
    )


def hazard_states() -> dict[str, State]:
    safe = optimized_plan_state()
    return {
        "roles_ready_without_core_receipts": replace(
            safe,
            role_core_prompts_delivered_at_spawn=False,
            role_core_prompt_hashes_recorded=False,
        ),
        "later_core_injection_required": replace(safe, later_core_injection_required=True),
        "fewer_than_six_roles": replace(safe, fewer_than_six_roles_used=True),
        "heartbeat_before_run_or_roles": replace(safe, heartbeat_created_before_run_or_roles=True),
        "heartbeat_after_reviewer_dispatch": replace(
            safe,
            heartbeat_created=False,
            heartbeat_bound_to_current_run=False,
            heartbeat_interval_minutes=0,
            heartbeat_host_proof_verified=False,
        ),
        "heartbeat_wrong_cadence": replace(safe, heartbeat_interval_minutes=30),
        "heartbeat_missing_host_proof": replace(safe, heartbeat_host_proof_verified=False),
        "controller_loaded_before_roles": replace(safe, six_roles_started=False),
        "controller_reads_sealed_body": replace(safe, controller_read_sealed_body=True),
        "self_attested_proof": replace(safe, self_attested_claim_used_as_proof=True),
        "reviewer_without_mechanical_proof": replace(safe, router_owned_mechanical_proof_current=False),
        "reviewer_without_display_receipt": replace(safe, display_receipt_visible_to_reviewer=False),
        "reviewer_reproves_router_facts": replace(safe, reviewer_required_to_reprove_router_facts=True),
        "startup_actions_bypass_controller_ledger": replace(safe, controller_action_ledger_used=False),
        "startup_ack_bypass_pending_return_ledger": replace(safe, card_pending_return_ledger_used=False),
        "separate_startup_wait_table": replace(safe, startup_only_wait_table_created=True),
        "pending_ack_blocks_independent_dispatch": replace(
            safe,
            startup_card_ack_pending=True,
            independent_startup_dispatch_continues_with_pending_ack=False,
        ),
        "reviewer_before_pre_review_ack_join": replace(
            safe,
            reviewer_fact_card_dispatched_after_pre_review_join=False,
        ),
        "pm_prep_no_join_policy": replace(
            safe,
            pm_prep_independent_before_reviewer_dispatch=False,
            pm_prep_join_policy_recorded=False,
        ),
        "pm_prep_blocks_reviewer": replace(safe, pm_prep_blocked_reviewer=True),
        "startup_review_acceptance_without_reviewer": replace(
            safe,
            reviewer_report_returned=False,
            reviewer_external_facts_checked=False,
        ),
        "startup_ack_join_without_common_ledger": replace(
            safe,
            startup_ack_join_checked_common_ledger=False,
            router_synced_common_ledgers=False,
        ),
        "startup_ack_join_with_pending_ack": replace(safe, startup_card_ack_pending=True),
        "pm_activation_before_review_acceptance": replace(safe, startup_review_report_accepted=False),
        "work_before_pm_activation": replace(safe, pm_activation_approved=False),
        "route_work_before_startup_open": replace(safe, work_beyond_startup_allowed=False),
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
