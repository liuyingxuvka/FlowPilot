"""FlowGuard model for FlowPilot startup intake UI integration.

Risk purpose:
- Use FlowGuard (https://github.com/liuyingxuvka/FlowGuard) to review the
  planned replacement of the chat three-question startup boundary with the
  native startup intake UI.
- Guard against Controller seeing user request body text, startup continuing
  after UI cancel, option toggles drifting from existing startup enums, and
  reviewer startup checks relying on chat history instead of UI records.
- Guard against Windows PowerShell UTF-8 BOM artifacts breaking Router JSON
  parsing or leaking an encoding marker into the PM-bound intake packet.
- Run with `python simulations/run_flowpilot_startup_intake_ui_checks.py`
  before changing FlowPilot startup protocol code and after each meaningful
  startup integration edit.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


STARTUP_ENUMS = {
    "background_agents": {"allow", "single-agent"},
    "scheduled_continuation": {"allow", "manual"},
    "display_surface": {"cockpit", "chat"},
}

REQUIRED_LABELS = (
    "router_loaded",
    "startup_intake_ui_opened",
    "ui_confirmed_with_all_artifacts",
    "ui_cancelled_before_run",
    "startup_answers_recorded_from_ui",
    "ui_artifact_encoding_contract_verified",
    "run_shell_created_after_ui_confirm",
    "sealed_user_request_ref_recorded",
    "pm_intake_packet_created_from_sealed_body_ref",
    "reviewer_checks_ui_record_receipt_and_envelope",
    "host_options_applied_from_ui_choices",
    "controller_core_loaded_after_sealed_intake",
    "startup_ui_path_complete",
)

MAX_SEQUENCE_LENGTH = 17


@dataclass(frozen=True)
class Tick:
    """One startup-control transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | waiting_ui | cancelled | running | complete
    router_loaded: bool = False
    ui_opened: bool = False
    ui_result: str = "none"  # none | confirmed | cancelled

    receipt_written: bool = False
    envelope_written: bool = False
    body_written: bool = False
    body_hash_verified: bool = False
    body_path_recorded: bool = False
    body_text_in_controller_visible_state: bool = False
    controller_read_body: bool = False
    result_json_no_bom: bool = False
    receipt_json_no_bom: bool = False
    envelope_json_no_bom: bool = False
    router_json_reader_bom_tolerant: bool = False
    artifact_encoding_contract_verified: bool = False
    body_has_leading_bom: bool = False
    pm_packet_body_bom_stripped: bool = False

    startup_answers_recorded: bool = False
    startup_answer_values_valid: bool = False
    background_agents: str = "unknown"  # unknown | allow | single-agent
    scheduled_continuation: str = "unknown"  # unknown | allow | manual
    display_surface: str = "unknown"  # unknown | cockpit | chat
    old_chat_answer_required: bool = False

    run_shell_created: bool = False
    user_request_ref_recorded: bool = False
    pm_intake_packet_created: bool = False
    pm_is_only_body_reader: bool = False

    reviewer_checked_ui_record: bool = False
    reviewer_checked_ui_receipt: bool = False
    reviewer_checked_envelope_hash: bool = False
    reviewer_used_chat_history: bool = False
    reviewer_startup_passed: bool = False

    roles_started: bool = False
    heartbeat_created: bool = False
    cockpit_opened: bool = False
    chat_display_fallback_recorded: bool = False
    cockpit_launch_failed: bool = False

    controller_core_loaded: bool = False


class Transition(NamedTuple):
    label: str
    state: State


class StartupIntakeStep:
    """Model one startup intake transition.

    Input x State -> Set(Output x State)
    reads: UI result files, startup option values, body path/hash, reviewer receipt checks
    writes: startup answers, run shell, user request ref, PM intake packet, host option effects
    idempotency: repeated ticks do not re-confirm UI, duplicate run creation, or re-open cancelled startup.
    """

    name = "StartupIntakeStep"
    reads = (
        "startup_intake_result",
        "startup_intake_receipt",
        "startup_intake_envelope",
        "startup_intake_body_hash",
        "startup_options",
    )
    writes = (
        "startup_answers",
        "run_shell",
        "sealed_user_request_ref",
        "pm_intake_packet",
        "reviewer_startup_fact_check",
        "host_startup_options",
    )
    input_description = "one FlowPilot startup intake UI/router tick"
    output_description = "one legal startup intake state transition"
    idempotency = "confirmed/cancelled intake and run creation are monotonic"

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


def build_workflow() -> Workflow:
    return Workflow((StartupIntakeStep(),), name="flowpilot_startup_intake_ui")


def is_terminal(state: State) -> bool:
    return state.status in {"cancelled", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


def _confirm_state(state: State, *, background: str, continuation: str, display: str) -> State:
    return replace(
        state,
        ui_result="confirmed",
        status="running",
        receipt_written=True,
        envelope_written=True,
        body_written=True,
        body_hash_verified=True,
        body_path_recorded=True,
        result_json_no_bom=True,
        receipt_json_no_bom=True,
        envelope_json_no_bom=True,
        router_json_reader_bom_tolerant=True,
        pm_packet_body_bom_stripped=True,
        background_agents=background,
        scheduled_continuation=continuation,
        display_surface=display,
    )


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status == "new" and not state.router_loaded:
        return (Transition("router_loaded", replace(state, router_loaded=True)),)
    if state.router_loaded and not state.ui_opened:
        return (
            Transition(
                "startup_intake_ui_opened",
                replace(state, ui_opened=True, status="waiting_ui"),
            ),
        )
    if state.status == "waiting_ui" and state.ui_result == "none":
        return (
            Transition(
                "ui_confirmed_with_all_artifacts",
                _confirm_state(
                    state,
                    background="allow",
                    continuation="allow",
                    display="cockpit",
                ),
            ),
            Transition(
                "ui_cancelled_before_run",
                replace(state, ui_result="cancelled", status="cancelled"),
            ),
            Transition(
                "ui_confirmed_with_all_artifacts",
                _confirm_state(
                    state,
                    background="single-agent",
                    continuation="manual",
                    display="chat",
                ),
            ),
        )
    if state.ui_result == "confirmed" and not state.startup_answers_recorded:
        if not state.artifact_encoding_contract_verified:
            return (
                Transition(
                    "ui_artifact_encoding_contract_verified",
                    replace(state, artifact_encoding_contract_verified=True),
                ),
            )
        return (
            Transition(
                "startup_answers_recorded_from_ui",
                replace(
                    state,
                    startup_answers_recorded=True,
                    startup_answer_values_valid=True,
                ),
            ),
        )
    if state.startup_answers_recorded and not state.run_shell_created:
        return (
            Transition(
                "run_shell_created_after_ui_confirm",
                replace(state, run_shell_created=True),
            ),
        )
    if state.run_shell_created and not state.user_request_ref_recorded:
        return (
            Transition(
                "sealed_user_request_ref_recorded",
                replace(state, user_request_ref_recorded=True),
            ),
        )
    if state.user_request_ref_recorded and not state.pm_intake_packet_created:
        return (
            Transition(
                "pm_intake_packet_created_from_sealed_body_ref",
                replace(
                    state,
                    pm_intake_packet_created=True,
                    pm_is_only_body_reader=True,
                ),
            ),
        )
    if state.pm_intake_packet_created and not state.reviewer_startup_passed:
        return (
            Transition(
                "reviewer_checks_ui_record_receipt_and_envelope",
                replace(
                    state,
                    reviewer_checked_ui_record=True,
                    reviewer_checked_ui_receipt=True,
                    reviewer_checked_envelope_hash=True,
                    reviewer_startup_passed=True,
                ),
            ),
        )
    if state.reviewer_startup_passed and not (
        state.roles_started
        or state.heartbeat_created
        or state.cockpit_opened
        or state.chat_display_fallback_recorded
    ):
        return (
            Transition(
                "host_options_applied_from_ui_choices",
                replace(
                    state,
                    roles_started=state.background_agents == "allow",
                    heartbeat_created=state.scheduled_continuation == "allow",
                    cockpit_opened=state.display_surface == "cockpit" and not state.cockpit_launch_failed,
                    chat_display_fallback_recorded=state.display_surface == "chat"
                    or state.cockpit_launch_failed,
                ),
            ),
        )
    if state.reviewer_startup_passed and not state.controller_core_loaded:
        options_applied = (
            (state.background_agents != "allow" or state.roles_started)
            and (state.scheduled_continuation != "allow" or state.heartbeat_created)
            and (
                (state.display_surface == "cockpit" and state.cockpit_opened)
                or (state.display_surface == "chat" and state.chat_display_fallback_recorded)
            )
        )
        if options_applied:
            return (
                Transition(
                    "controller_core_loaded_after_sealed_intake",
                    replace(state, controller_core_loaded=True),
                ),
            )
    if state.controller_core_loaded and state.status != "complete":
        return (
            Transition(
                "startup_ui_path_complete",
                replace(state, status="complete"),
            ),
        )
    return ()


def startup_intake_invariants(state: State, _trace) -> InvariantResult:
    if state.controller_core_loaded and not (
        state.ui_result == "confirmed"
        and state.startup_answers_recorded
        and state.pm_intake_packet_created
    ):
        return InvariantResult.fail("Controller loaded before confirmed UI intake and PM packet")
    if state.ui_result == "cancelled" and (
        state.run_shell_created
        or state.user_request_ref_recorded
        or state.roles_started
        or state.heartbeat_created
        or state.cockpit_opened
        or state.controller_core_loaded
    ):
        return InvariantResult.fail("UI cancel still allowed startup side effects")
    if state.body_text_in_controller_visible_state or state.controller_read_body:
        return InvariantResult.fail("Controller-visible startup state leaked user request body")
    if state.startup_answers_recorded and not (
        state.receipt_written
        and state.envelope_written
        and state.body_written
        and state.body_path_recorded
        and state.body_hash_verified
        and state.artifact_encoding_contract_verified
    ):
        return InvariantResult.fail("startup answers accepted without complete UI receipt/envelope/body hash evidence")
    if state.ui_result == "confirmed" and not (
        state.result_json_no_bom
        and state.receipt_json_no_bom
        and state.envelope_json_no_bom
    ):
        return InvariantResult.fail("startup UI JSON artifacts must be UTF-8 without BOM")
    if state.ui_result == "confirmed" and not state.router_json_reader_bom_tolerant:
        return InvariantResult.fail("Router startup intake JSON reader is not BOM-compatible")
    if state.pm_intake_packet_created and state.body_has_leading_bom and not state.pm_packet_body_bom_stripped:
        return InvariantResult.fail("PM intake packet leaked leading UTF-8 BOM marker")
    if state.startup_answers_recorded:
        if state.background_agents not in STARTUP_ENUMS["background_agents"]:
            return InvariantResult.fail("background agent toggle did not map to a startup answer enum")
        if state.scheduled_continuation not in STARTUP_ENUMS["scheduled_continuation"]:
            return InvariantResult.fail("scheduled continuation toggle did not map to a startup answer enum")
        if state.display_surface not in STARTUP_ENUMS["display_surface"]:
            return InvariantResult.fail("display surface toggle did not map to a startup answer enum")
    if state.background_agents == "single-agent" and state.roles_started:
        return InvariantResult.fail("background agents started despite UI single-agent choice")
    if state.scheduled_continuation == "manual" and state.heartbeat_created:
        return InvariantResult.fail("heartbeat created despite UI manual continuation choice")
    if state.display_surface == "chat" and state.cockpit_opened:
        return InvariantResult.fail("Cockpit opened despite UI chat display choice")
    if state.display_surface == "chat" and state.controller_core_loaded and not state.chat_display_fallback_recorded:
        return InvariantResult.fail("chat display choice reached Controller without chat fallback record")
    if state.reviewer_startup_passed and not (
        state.reviewer_checked_ui_receipt
        and state.reviewer_checked_ui_record
        and state.reviewer_checked_envelope_hash
        and not state.reviewer_used_chat_history
    ):
        return InvariantResult.fail("reviewer startup pass relied on chat instead of UI record/receipt/envelope")
    if state.old_chat_answer_required and state.ui_result == "confirmed":
        return InvariantResult.fail("UI-confirmed startup still required old chat answers")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="startup_intake_ui_boundary",
        description="Native UI confirm/cancel is the only startup answer boundary before Controller.",
        predicate=startup_intake_invariants,
    ),
)


EXTERNAL_INPUTS = (Tick(),)


def invariant_failures(state: State) -> list[str]:
    result = startup_intake_invariants(state, ())
    if result.ok:
        return []
    return [result.message]


def hazard_states() -> dict[str, State]:
    base = _confirm_state(
        replace(initial_state(), router_loaded=True, ui_opened=True, status="waiting_ui"),
        background="allow",
        continuation="allow",
        display="cockpit",
    )
    recorded = replace(base, startup_answers_recorded=True, startup_answer_values_valid=True)
    encoded = replace(base, artifact_encoding_contract_verified=True)
    recorded = replace(encoded, startup_answers_recorded=True, startup_answer_values_valid=True)
    return {
        "controller_before_ui_confirm": replace(initial_state(), controller_core_loaded=True),
        "cancel_continues_to_run": replace(
            initial_state(),
            router_loaded=True,
            ui_opened=True,
            ui_result="cancelled",
            status="cancelled",
            run_shell_created=True,
        ),
        "controller_body_leak": replace(recorded, body_text_in_controller_visible_state=True),
        "accepted_without_hash": replace(recorded, body_hash_verified=False),
        "ui_result_json_bom_breaks_router": replace(recorded, result_json_no_bom=False),
        "ui_receipt_json_bom_breaks_router": replace(recorded, receipt_json_no_bom=False),
        "ui_envelope_json_bom_breaks_router": replace(recorded, envelope_json_no_bom=False),
        "legacy_bom_json_without_router_fallback": replace(recorded, router_json_reader_bom_tolerant=False),
        "body_bom_leaks_to_pm_packet": replace(
            recorded,
            pm_intake_packet_created=True,
            body_has_leading_bom=True,
            pm_packet_body_bom_stripped=False,
        ),
        "bom_repair_bypasses_body_hash": replace(recorded, body_hash_verified=False),
        "invalid_toggle_value": replace(recorded, background_agents="yes"),
        "single_agent_starts_roles": replace(
            recorded,
            background_agents="single-agent",
            roles_started=True,
        ),
        "manual_creates_heartbeat": replace(
            recorded,
            scheduled_continuation="manual",
            heartbeat_created=True,
        ),
        "chat_opens_cockpit": replace(
            recorded,
            display_surface="chat",
            cockpit_opened=True,
        ),
        "reviewer_uses_chat": replace(
            recorded,
            pm_intake_packet_created=True,
            reviewer_startup_passed=True,
            reviewer_checked_ui_record=False,
            reviewer_checked_ui_receipt=False,
            reviewer_checked_envelope_hash=False,
            reviewer_used_chat_history=True,
        ),
        "ui_confirm_requires_old_chat": replace(recorded, old_chat_answer_required=True),
    }


def approved_plan_state() -> State:
    return replace(
        _confirm_state(
            replace(initial_state(), router_loaded=True, ui_opened=True, status="waiting_ui"),
            background="allow",
            continuation="allow",
            display="cockpit",
        ),
        startup_answers_recorded=True,
        startup_answer_values_valid=True,
        artifact_encoding_contract_verified=True,
        run_shell_created=True,
        user_request_ref_recorded=True,
        pm_intake_packet_created=True,
        pm_is_only_body_reader=True,
        reviewer_checked_ui_record=True,
        reviewer_checked_ui_receipt=True,
        reviewer_checked_envelope_hash=True,
        reviewer_startup_passed=True,
        roles_started=True,
        heartbeat_created=True,
        cockpit_opened=True,
        controller_core_loaded=True,
        status="complete",
    )


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "REQUIRED_LABELS",
    "State",
    "Tick",
    "approved_plan_state",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
]
