"""FlowGuard model for FlowPilot command refinement.

Risk intent brief:
- Treat the original multi-command router loop as the baseline oracle before
  reintroducing any aggregate command.
- Only allow a production fold when it is behaviorally equivalent to the
  unfolded baseline and does not cross user, host, role, card-delivery, packet
  relay, ledger, final replay, or role-output boundaries.
- Model-critical state: startup next/apply/next order, post-banner bootloader
  writes, post-user-request intake writes, wait-boundary return, candidate fold
  classification, runtime binding checks, and high-risk fold rejection.
- Hard invariants: accepted startup paths must apply `load_router` exactly once
  before returning `ask_startup_questions`; accepted bootloader paths must stop
  before `record_user_request`; accepted intake paths must stop before
  `start_role_slots`; enabled folds must have binding and CLI smoke evidence;
  high-risk card, relay, ledger, final replay, host, startup fact-card, and
  role-output folds remain rejected until they get their own conformance replay.
- Blindspot: this model checks command-refinement policy, not concrete Python
  name binding. The package also needs static undefined-name checks and CLI
  smoke tests.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


STARTUP_UNFOLDED = "startup_unfolded"
STARTUP_SAFE_FOLD = "startup_safe_fold"
POST_BANNER_BOOTLOADER_UNFOLDED = "post_banner_bootloader_unfolded"
POST_BANNER_BOOTLOADER_SAFE_FOLD = "post_banner_bootloader_safe_fold"
POST_USER_REQUEST_INTAKE_UNFOLDED = "post_user_request_intake_unfolded"
POST_USER_REQUEST_INTAKE_SAFE_FOLD = "post_user_request_intake_safe_fold"
CARD_BUNDLE_FOLD = "card_bundle_fold"
PACKET_RELAY_FOLD = "packet_relay_fold"
USER_REQUEST_RECORDING_FOLD = "user_request_recording_fold"
HOST_CONTINUATION_FOLD = "host_continuation_fold"
ROLE_SLOT_START_FOLD = "role_slot_start_fold"
LEDGER_FINALIZATION_FOLD = "ledger_finalization_fold"
FINAL_REPLAY_FOLD = "final_replay_fold"
STARTUP_FACT_CARD_FOLD = "startup_fact_card_fold"
ROLE_OUTPUT_PREFLIGHT_FOLD = "role_output_preflight_fold"

NEGATIVE_SCENARIOS = (
    CARD_BUNDLE_FOLD,
    PACKET_RELAY_FOLD,
    USER_REQUEST_RECORDING_FOLD,
    HOST_CONTINUATION_FOLD,
    ROLE_SLOT_START_FOLD,
    LEDGER_FINALIZATION_FOLD,
    FINAL_REPLAY_FOLD,
    STARTUP_FACT_CARD_FOLD,
    ROLE_OUTPUT_PREFLIGHT_FOLD,
)

SCENARIOS = (
    STARTUP_UNFOLDED,
    STARTUP_SAFE_FOLD,
    POST_BANNER_BOOTLOADER_UNFOLDED,
    POST_BANNER_BOOTLOADER_SAFE_FOLD,
    POST_USER_REQUEST_INTAKE_UNFOLDED,
    POST_USER_REQUEST_INTAKE_SAFE_FOLD,
    *NEGATIVE_SCENARIOS,
)

ACCEPTED_SCENARIOS = (
    STARTUP_UNFOLDED,
    STARTUP_SAFE_FOLD,
    POST_BANNER_BOOTLOADER_UNFOLDED,
    POST_BANNER_BOOTLOADER_SAFE_FOLD,
    POST_USER_REQUEST_INTAKE_UNFOLDED,
    POST_USER_REQUEST_INTAKE_SAFE_FOLD,
)

EXPECTED_REJECTIONS = {
    CARD_BUNDLE_FOLD: "multi_card_delivery_requires_dedicated_replay",
    PACKET_RELAY_FOLD: "packet_relay_requires_dedicated_replay",
    USER_REQUEST_RECORDING_FOLD: "user_boundary_requires_explicit_wait",
    HOST_CONTINUATION_FOLD: "host_boundary_requires_dedicated_replay",
    ROLE_SLOT_START_FOLD: "role_boundary_requires_dedicated_replay",
    LEDGER_FINALIZATION_FOLD: "ledger_boundary_requires_dedicated_replay",
    FINAL_REPLAY_FOLD: "final_replay_boundary_requires_dedicated_replay",
    STARTUP_FACT_CARD_FOLD: "startup_fact_card_crosses_reviewer_delivery_boundary",
    ROLE_OUTPUT_PREFLIGHT_FOLD: "role_output_preflight_requires_error_semantics_replay",
}


@dataclass(frozen=True)
class Tick:
    """One command-refinement tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"
    next_load_router_seen: bool = False
    load_router_applied: bool = False
    startup_questions_returned: bool = False
    run_shell_created: bool = False
    current_pointer_written: bool = False
    run_index_updated: bool = False
    runtime_kit_copied: bool = False
    runtime_placeholders_filled: bool = False
    mailbox_initialized: bool = False
    user_request_available: bool = False
    user_request_recorded: bool = False
    user_intake_written: bool = False
    role_slots_started: bool = False
    user_boundary_crossed: bool = False
    host_boundary_crossed: bool = False
    role_boundary_crossed: bool = False
    card_boundary_crossed: bool = False
    packet_boundary_crossed: bool = False
    ledger_boundary_crossed: bool = False
    final_replay_boundary_crossed: bool = False
    folded_command_enabled: bool = False
    cli_binding_verified: bool = False
    runtime_smoke_verified: bool = False
    install_smoke_required: bool = True
    install_smoke_verified: bool = False
    high_risk_fold_rejected: bool = False
    router_decision: str = "none"
    router_rejection_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class CommandRefinementStep:
    """Model one command refinement transition.

    Input x State -> Set(Output x State)
    reads: selected scenario, startup command order, binding evidence, boundary
    state
    writes: startup command progress, candidate acceptance/rejection, terminal
    decision
    idempotency: terminal decisions do not duplicate router actions
    """

    name = "CommandRefinementStep"
    reads = (
        "scenario",
        "startup_command_order",
        "bootloader_internal_order",
        "user_intake_internal_order",
        "binding_and_smoke_evidence",
        "boundary_state",
    )
    writes = (
        "startup_progress",
        "bootloader_progress",
        "user_intake_progress",
        "fold_candidate_decision",
        "router_terminal_decision",
    )
    input_description = "router command-refinement tick"
    output_description = "one abstract command-refinement step"
    idempotency = "terminal command-refinement decisions are not duplicated"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def initial_state() -> State:
    return State()


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return

    if state.scenario == "unset":
        for scenario in SCENARIOS:
            initial_updates = {}
            if scenario in {
                POST_USER_REQUEST_INTAKE_UNFOLDED,
                POST_USER_REQUEST_INTAKE_SAFE_FOLD,
            }:
                initial_updates["user_request_available"] = True
            yield Transition(
                "router_selects_command_refinement_scenario",
                replace(state, status="running", scenario=scenario, **initial_updates),
            )
        return

    if state.scenario == STARTUP_UNFOLDED:
        if not state.next_load_router_seen:
            yield Transition("unfolded_next_returns_load_router", replace(state, next_load_router_seen=True))
            return
        if not state.load_router_applied:
            yield Transition("unfolded_apply_records_load_router", replace(state, load_router_applied=True))
            return
        yield Transition(
            "unfolded_next_returns_startup_questions",
            replace(
                state,
                startup_questions_returned=True,
                status="accepted",
                router_decision="accept",
            ),
        )
        return

    if state.scenario == STARTUP_SAFE_FOLD:
        if not state.cli_binding_verified:
            yield Transition("safe_fold_verifies_cli_binding", replace(state, cli_binding_verified=True))
            return
        if not state.runtime_smoke_verified:
            yield Transition("safe_fold_verifies_runtime_smoke", replace(state, runtime_smoke_verified=True))
            return
        if not state.install_smoke_verified:
            yield Transition("safe_fold_requires_install_smoke", replace(state, install_smoke_verified=True))
            return
        yield Transition(
            "safe_fold_applies_load_router_and_returns_startup_questions",
            replace(
                state,
                next_load_router_seen=True,
                load_router_applied=True,
                startup_questions_returned=True,
                folded_command_enabled=True,
                status="accepted",
                router_decision="accept",
            ),
        )
        return

    if state.scenario == POST_BANNER_BOOTLOADER_UNFOLDED:
        if not state.run_shell_created:
            yield Transition("bootloader_unfolded_create_run_shell", replace(state, run_shell_created=True))
            return
        if not state.current_pointer_written:
            yield Transition("bootloader_unfolded_write_current_pointer", replace(state, current_pointer_written=True))
            return
        if not state.run_index_updated:
            yield Transition("bootloader_unfolded_update_run_index", replace(state, run_index_updated=True))
            return
        if not state.runtime_kit_copied:
            yield Transition("bootloader_unfolded_copy_runtime_kit", replace(state, runtime_kit_copied=True))
            return
        if not state.runtime_placeholders_filled:
            yield Transition(
                "bootloader_unfolded_fill_runtime_placeholders",
                replace(state, runtime_placeholders_filled=True),
            )
            return
        yield Transition(
            "bootloader_unfolded_initialize_mailbox_then_wait_for_user_request",
            replace(
                state,
                mailbox_initialized=True,
                status="accepted",
                router_decision="accept",
            ),
        )
        return

    if state.scenario == POST_BANNER_BOOTLOADER_SAFE_FOLD:
        if not state.cli_binding_verified:
            yield Transition("bootloader_safe_fold_verifies_cli_binding", replace(state, cli_binding_verified=True))
            return
        if not state.runtime_smoke_verified:
            yield Transition("bootloader_safe_fold_verifies_runtime_smoke", replace(state, runtime_smoke_verified=True))
            return
        if not state.install_smoke_verified:
            yield Transition("bootloader_safe_fold_requires_install_smoke", replace(state, install_smoke_verified=True))
            return
        yield Transition(
            "bootloader_safe_fold_initializes_mailbox_then_waits_for_user_request",
            replace(
                state,
                run_shell_created=True,
                current_pointer_written=True,
                run_index_updated=True,
                runtime_kit_copied=True,
                runtime_placeholders_filled=True,
                mailbox_initialized=True,
                folded_command_enabled=True,
                status="accepted",
                router_decision="accept",
            ),
        )
        return

    if state.scenario == POST_USER_REQUEST_INTAKE_UNFOLDED:
        yield Transition(
            "intake_unfolded_write_user_intake_then_wait_for_role_slots",
            replace(
                state,
                user_intake_written=True,
                status="accepted",
                router_decision="accept",
            ),
        )
        return

    if state.scenario == POST_USER_REQUEST_INTAKE_SAFE_FOLD:
        if not state.cli_binding_verified:
            yield Transition("intake_safe_fold_verifies_cli_binding", replace(state, cli_binding_verified=True))
            return
        if not state.runtime_smoke_verified:
            yield Transition("intake_safe_fold_verifies_runtime_smoke", replace(state, runtime_smoke_verified=True))
            return
        if not state.install_smoke_verified:
            yield Transition("intake_safe_fold_requires_install_smoke", replace(state, install_smoke_verified=True))
            return
        yield Transition(
            "intake_safe_fold_writes_user_intake_then_waits_for_role_slots",
            replace(
                state,
                user_intake_written=True,
                folded_command_enabled=True,
                status="accepted",
                router_decision="accept",
            ),
        )
        return

    if state.scenario in EXPECTED_REJECTIONS:
        yield Transition(
            f"{state.scenario}_rejected_pending_dedicated_replay",
            replace(
                state,
                high_risk_fold_rejected=True,
                status="rejected",
                router_decision="reject",
                router_rejection_reason=EXPECTED_REJECTIONS[state.scenario],
            ),
        )
        return


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return is_terminal(state) and not invariant_failures(state)


def terminal_predicate(_input_obj, state: State, _trace) -> bool:
    return is_terminal(state)


def accepted_startup_matches_unfolded_baseline(state: State, _trace) -> InvariantResult:
    if state.status == "accepted" and state.scenario in {STARTUP_UNFOLDED, STARTUP_SAFE_FOLD}:
        if not state.load_router_applied:
            return InvariantResult.fail("accepted startup path did not apply load_router")
        if not state.startup_questions_returned:
            return InvariantResult.fail("accepted startup path did not return startup questions")
    return InvariantResult.pass_()


def accepted_bootloader_matches_unfolded_baseline(state: State, _trace) -> InvariantResult:
    if state.status == "accepted" and state.scenario in {
        POST_BANNER_BOOTLOADER_UNFOLDED,
        POST_BANNER_BOOTLOADER_SAFE_FOLD,
    }:
        if not (
            state.run_shell_created
            and state.current_pointer_written
            and state.run_index_updated
            and state.runtime_kit_copied
            and state.runtime_placeholders_filled
            and state.mailbox_initialized
        ):
            return InvariantResult.fail("accepted bootloader path did not complete internal bootloader writes")
        if state.user_request_recorded:
            return InvariantResult.fail("accepted bootloader path crossed record_user_request wait boundary")
    return InvariantResult.pass_()


def accepted_intake_matches_unfolded_baseline(state: State, _trace) -> InvariantResult:
    if state.status == "accepted" and state.scenario in {
        POST_USER_REQUEST_INTAKE_UNFOLDED,
        POST_USER_REQUEST_INTAKE_SAFE_FOLD,
    }:
        if not state.user_request_available:
            return InvariantResult.fail("accepted intake path ran before user request was available")
        if state.user_request_recorded:
            return InvariantResult.fail("accepted intake path performed record_user_request instead of starting post-user-request")
        if not state.user_intake_written:
            return InvariantResult.fail("accepted intake path did not write user intake")
        if state.role_slots_started:
            return InvariantResult.fail("accepted intake path crossed start_role_slots wait boundary")
    return InvariantResult.pass_()


def accepted_folds_do_not_cross_wait_or_external_boundaries(state: State, _trace) -> InvariantResult:
    if state.status != "accepted":
        return InvariantResult.pass_()
    if (
        state.user_boundary_crossed
        or state.host_boundary_crossed
        or state.role_boundary_crossed
        or state.card_boundary_crossed
        or state.packet_boundary_crossed
        or state.ledger_boundary_crossed
        or state.final_replay_boundary_crossed
    ):
        return InvariantResult.fail("accepted path crossed a user, host, role, card, packet, ledger, or final replay boundary")
    return InvariantResult.pass_()


def enabled_folds_require_binding_and_smoke(state: State, _trace) -> InvariantResult:
    if state.folded_command_enabled:
        if not state.cli_binding_verified:
            return InvariantResult.fail("enabled fold lacks CLI binding verification")
        if not state.runtime_smoke_verified:
            return InvariantResult.fail("enabled fold lacks runtime smoke verification")
        if state.install_smoke_required and not state.install_smoke_verified:
            return InvariantResult.fail("enabled fold lacks installed-skill smoke verification")
    return InvariantResult.pass_()


def only_safe_startup_fold_is_production_enabled(state: State, _trace) -> InvariantResult:
    if state.folded_command_enabled and state.scenario not in {
        STARTUP_SAFE_FOLD,
        POST_BANNER_BOOTLOADER_SAFE_FOLD,
        POST_USER_REQUEST_INTAKE_SAFE_FOLD,
    }:
        return InvariantResult.fail(f"high-risk fold was production-enabled: {state.scenario}")
    return InvariantResult.pass_()


def high_risk_candidates_reject_without_replay(state: State, _trace) -> InvariantResult:
    if state.scenario in NEGATIVE_SCENARIOS and state.status == "accepted":
        return InvariantResult.fail(f"high-risk fold was accepted without dedicated replay: {state.scenario}")
    return InvariantResult.pass_()


def terminal_decisions_are_explicit(state: State, _trace) -> InvariantResult:
    if state.status in {"accepted", "rejected"} and state.router_decision not in {"accept", "reject"}:
        return InvariantResult.fail("terminal state lacks explicit router decision")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepted_startup_matches_unfolded_baseline",
        description="Accepted startup paths apply load_router once and return startup questions without crossing boundaries.",
        predicate=accepted_startup_matches_unfolded_baseline,
    ),
    Invariant(
        name="accepted_bootloader_matches_unfolded_baseline",
        description="Accepted post-banner bootloader paths create run shell, current pointer, run index, runtime kit, placeholders, and mailbox, then wait before record_user_request.",
        predicate=accepted_bootloader_matches_unfolded_baseline,
    ),
    Invariant(
        name="accepted_intake_matches_unfolded_baseline",
        description="Accepted post-user-request intake paths write user intake, then wait before start_role_slots.",
        predicate=accepted_intake_matches_unfolded_baseline,
    ),
    Invariant(
        name="accepted_folds_do_not_cross_wait_or_external_boundaries",
        description="Accepted paths do not cross user, host, role, card, packet, ledger, or final replay boundaries.",
        predicate=accepted_folds_do_not_cross_wait_or_external_boundaries,
    ),
    Invariant(
        name="enabled_folds_require_binding_and_smoke",
        description="Production folds require CLI, runtime, and installed-skill smoke evidence.",
        predicate=enabled_folds_require_binding_and_smoke,
    ),
    Invariant(
        name="only_safe_startup_fold_is_production_enabled",
        description="Only replayed internal folds may be production enabled.",
        predicate=only_safe_startup_fold_is_production_enabled,
    ),
    Invariant(
        name="high_risk_candidates_reject_without_replay",
        description="High-risk fold candidates remain rejected until a dedicated replay model exists.",
        predicate=high_risk_candidates_reject_without_replay,
    ),
    Invariant(
        name="terminal_decisions_are_explicit",
        description="Terminal model states record explicit accept/reject decisions.",
        predicate=terminal_decisions_are_explicit,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 8
REQUIRED_LABELS = (
    "router_selects_command_refinement_scenario",
    "unfolded_next_returns_load_router",
    "unfolded_apply_records_load_router",
    "unfolded_next_returns_startup_questions",
    "safe_fold_verifies_cli_binding",
    "safe_fold_verifies_runtime_smoke",
    "safe_fold_requires_install_smoke",
    "safe_fold_applies_load_router_and_returns_startup_questions",
    "bootloader_unfolded_create_run_shell",
    "bootloader_unfolded_write_current_pointer",
    "bootloader_unfolded_update_run_index",
    "bootloader_unfolded_copy_runtime_kit",
    "bootloader_unfolded_fill_runtime_placeholders",
    "bootloader_unfolded_initialize_mailbox_then_wait_for_user_request",
    "bootloader_safe_fold_verifies_cli_binding",
    "bootloader_safe_fold_verifies_runtime_smoke",
    "bootloader_safe_fold_requires_install_smoke",
    "bootloader_safe_fold_initializes_mailbox_then_waits_for_user_request",
    "intake_unfolded_write_user_intake_then_wait_for_role_slots",
    "intake_safe_fold_verifies_cli_binding",
    "intake_safe_fold_verifies_runtime_smoke",
    "intake_safe_fold_requires_install_smoke",
    "intake_safe_fold_writes_user_intake_then_waits_for_role_slots",
    "card_bundle_fold_rejected_pending_dedicated_replay",
    "packet_relay_fold_rejected_pending_dedicated_replay",
    "user_request_recording_fold_rejected_pending_dedicated_replay",
    "host_continuation_fold_rejected_pending_dedicated_replay",
    "role_slot_start_fold_rejected_pending_dedicated_replay",
    "ledger_finalization_fold_rejected_pending_dedicated_replay",
    "final_replay_fold_rejected_pending_dedicated_replay",
    "startup_fact_card_fold_rejected_pending_dedicated_replay",
    "role_output_preflight_fold_rejected_pending_dedicated_replay",
)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def build_workflow() -> Workflow:
    return Workflow((CommandRefinementStep(),), name="flowpilot_command_refinement")
