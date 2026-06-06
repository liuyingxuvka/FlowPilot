"""FlowGuard model for FlowPilot startup intake UI integration.

Risk purpose:
- Use FlowGuard (https://github.com/liuyingxuvka/FlowGuard) to review the
  native startup intake UI as the formal startup boundary.
- Guard against Controller seeing user request body text, startup continuing
  after UI cancel or missing background-collaboration acknowledgement, removed
  startup option enums returning as user-visible choices, and reviewer startup
  checks relying on chat history instead of UI records.
- Guard that language selection is no longer a top-level startup option and is
  available only from the settings gear together with the support-developer
  entry.
- Guard against Windows PowerShell UTF-8 BOM artifacts breaking Router JSON
  parsing or leaking an encoding marker into the PM-bound intake packet.
- Guard against Windows PowerShell 5.1 parsing non-ASCII UTF-8 no-BOM `.ps1`
  source under a unsupported_historical code page before the startup intake UI can open.
- Guard against headless or synthesized startup intake output being accepted as
  a formal user-operated native UI confirmation.
- Run with `python simulations/run_flowpilot_startup_intake_ui_checks.py`
  before changing FlowPilot startup protocol code and after each meaningful
  startup integration edit.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


LEGACY_STARTUP_OPTION_KEYS = {
    "runtime_role_assistances",
    "runtime_role_assistance_authorized",
    "runtime_role_assistances_answer",
    "scheduled_continuation",
    "heartbeat_requested",
    "single_agent_role_continuity_authorized",
    "single_agent_user_selected",
}

REQUIRED_LABELS = (
    "router_loaded",
    "startup_ui_source_encoding_contract_verified",
    "startup_intake_ui_opened",
    "settings_button_visible_and_main_language_hidden",
    "settings_panel_opened_with_language_and_support",
    "ui_confirmed_with_all_artifacts",
    "ui_blocked_without_background_ack",
    "ui_cancelled_before_run",
    "startup_answers_recorded_from_ui",
    "ui_artifact_encoding_contract_verified",
    "run_shell_created_after_ui_confirm",
    "sealed_user_request_ref_recorded",
    "pm_intake_packet_created_from_sealed_body_ref",
    "reviewer_checks_ui_record_receipt_and_envelope",
    "background_collaboration_requested_after_ack",
    "controller_core_loaded_after_sealed_intake",
    "startup_ui_path_complete",
)

MAX_SEQUENCE_LENGTH = 19


@dataclass(frozen=True)
class Tick:
    """One startup-control transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | waiting_ui | blocked | cancelled | running | complete
    router_loaded: bool = False
    ui_opened: bool = False
    ui_result: str = "none"  # none | confirmed | blocked | cancelled
    launch_mode: str = "none"  # none | interactive_native | headless | synthetic
    headless_result: bool = False
    formal_startup_allowed: bool = False
    settings_button_visible: bool = False
    language_visible_on_main: bool = False
    settings_panel_opened: bool = False
    language_visible_in_settings: bool = False
    support_developer_visible_in_settings: bool = False
    support_uses_canonical_url: bool = False
    support_entitlement_disclaimer_visible: bool = False
    support_claims_paid_entitlement: bool = False

    receipt_written: bool = False
    envelope_written: bool = False
    body_written: bool = False
    body_hash_verified: bool = False
    body_path_recorded: bool = False
    body_text_in_controller_visible_state: bool = False
    controller_read_body: bool = False
    script_source_contains_non_ascii: bool = False
    script_source_utf8_bom: bool = False
    unsupported_historical_powershell_source_parse_safe: bool = False
    source_encoding_contract_verified: bool = False
    result_json_no_bom: bool = False
    receipt_json_no_bom: bool = False
    envelope_json_no_bom: bool = False
    router_json_reader_bom_tolerant: bool = False
    artifact_encoding_contract_verified: bool = False
    body_has_leading_bom: bool = False
    pm_packet_body_bom_stripped: bool = False

    startup_answers_recorded: bool = False
    startup_answer_values_valid: bool = False
    background_collaboration_authorized: bool | None = None
    legacy_startup_option_key_seen: str = ""
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

    background_collaboration_requested: bool = False
    host_background_collaboration_available: bool = True
    cockpit_opened: bool = False
    chat_display_requirement_recorded: bool = False
    cockpit_launch_failed: bool = False

    controller_core_loaded: bool = False


class Transition(NamedTuple):
    label: str
    state: State


class StartupIntakeStep:
    """Model one startup intake transition.

    Input x State -> Set(Output x State)
    reads: UI result files, startup option values, body path/hash, runtime receipt checks
    writes: startup answers, run shell, user request ref, PM intake packet, background collaboration request
    idempotency: repeated ticks do not re-confirm UI, duplicate run creation, or re-open cancelled startup.
    """

    name = "StartupIntakeStep"
    reads = (
        "startup_intake_result",
        "startup_intake_receipt",
        "startup_intake_envelope",
        "startup_intake_body_hash",
        "startup_options",
        "settings_panel",
    )
    writes = (
        "startup_answers",
        "run_shell",
        "sealed_user_request_ref",
        "pm_intake_packet",
        "startup_mechanical_audit",
        "host_startup_options",
        "settings_language_and_support_surface",
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
    return state.status in {"blocked", "cancelled", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


def _confirm_state(state: State) -> State:
    return replace(
        state,
        ui_result="confirmed",
        status="running",
        launch_mode="interactive_native",
        headless_result=False,
        formal_startup_allowed=True,
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
        background_collaboration_authorized=True,
    )


def _blocked_state(state: State) -> State:
    return replace(
        state,
        ui_result="blocked",
        status="blocked",
        launch_mode="interactive_native",
        headless_result=False,
        formal_startup_allowed=True,
        receipt_written=True,
        envelope_written=True,
        result_json_no_bom=True,
        receipt_json_no_bom=True,
        envelope_json_no_bom=True,
        router_json_reader_bom_tolerant=True,
        background_collaboration_authorized=False,
    )


def _source_safe_state(state: State) -> State:
    return replace(
        state,
        script_source_contains_non_ascii=True,
        script_source_utf8_bom=True,
        unsupported_historical_powershell_source_parse_safe=True,
        source_encoding_contract_verified=True,
    )


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status == "new" and not state.router_loaded:
        return (Transition("router_loaded", replace(state, router_loaded=True)),)
    if state.router_loaded and not state.source_encoding_contract_verified:
        return (
            Transition(
                "startup_ui_source_encoding_contract_verified",
                _source_safe_state(state),
            ),
        )
    if state.router_loaded and not state.ui_opened:
        return (
            Transition(
                "startup_intake_ui_opened",
                replace(state, ui_opened=True, status="waiting_ui"),
            ),
        )
    if state.status == "waiting_ui" and state.ui_opened and not state.settings_button_visible:
        return (
            Transition(
                "settings_button_visible_and_main_language_hidden",
                replace(
                    state,
                    settings_button_visible=True,
                    language_visible_on_main=False,
                ),
            ),
        )
    if state.status == "waiting_ui" and state.settings_button_visible and not state.settings_panel_opened:
        return (
            Transition(
                "settings_panel_opened_with_language_and_support",
                replace(
                    state,
                    settings_panel_opened=True,
                    language_visible_in_settings=True,
                    support_developer_visible_in_settings=True,
                    support_uses_canonical_url=True,
                    support_entitlement_disclaimer_visible=True,
                    support_claims_paid_entitlement=False,
                ),
            ),
        )
    if state.status == "waiting_ui" and state.ui_result == "none":
        return (
            Transition(
                "ui_confirmed_with_all_artifacts",
                _confirm_state(state),
            ),
            Transition(
                "ui_blocked_without_background_ack",
                _blocked_state(state),
            ),
            Transition(
                "ui_cancelled_before_run",
                replace(
                    state,
                    ui_result="cancelled",
                    status="cancelled",
                    launch_mode="interactive_native",
                    headless_result=False,
                    formal_startup_allowed=True,
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
        state.background_collaboration_requested
        or state.cockpit_opened
        or state.chat_display_requirement_recorded
    ):
        return (
            Transition(
                "background_collaboration_requested_after_ack",
                replace(
                    state,
                    background_collaboration_requested=True,
                    cockpit_opened=False,
                    chat_display_requirement_recorded=True,
                ),
            ),
        )
    if state.reviewer_startup_passed and not state.controller_core_loaded:
        options_applied = (
            state.background_collaboration_authorized is True
            and state.background_collaboration_requested
            and state.host_background_collaboration_available
            and state.chat_display_requirement_recorded
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
    if state.ui_result in {"confirmed", "blocked", "cancelled"} and state.status != "new":
        if state.launch_mode != "interactive_native" or state.headless_result or not state.formal_startup_allowed:
            return InvariantResult.fail("formal startup accepted non-interactive startup intake result")
    if state.ui_result in {"blocked", "cancelled"} and (
        state.run_shell_created
        or state.user_request_ref_recorded
        or state.background_collaboration_requested
        or state.cockpit_opened
        or state.controller_core_loaded
    ):
        return InvariantResult.fail("UI block/cancel still allowed startup side effects")
    if state.body_text_in_controller_visible_state or state.controller_read_body:
        return InvariantResult.fail("Controller-visible startup state leaked user request body")
    if state.ui_opened and not state.source_encoding_contract_verified:
        return InvariantResult.fail("startup UI opened before launcher source encoding contract was verified")
    if state.source_encoding_contract_verified and state.script_source_contains_non_ascii and not state.script_source_utf8_bom:
        return InvariantResult.fail("startup UI launcher source may not parse on unsupported_historical Windows PowerShell")
    if state.ui_opened and not state.unsupported_historical_powershell_source_parse_safe:
        return InvariantResult.fail("startup UI launcher source may not parse on unsupported_historical Windows PowerShell")
    if state.settings_button_visible and state.language_visible_on_main:
        return InvariantResult.fail("language selector remained visible on the startup main surface")
    if state.ui_result in {"confirmed", "blocked", "cancelled"} and not state.settings_button_visible:
        return InvariantResult.fail("startup UI reached a user decision before the settings gear was available")
    if state.ui_result in {"confirmed", "blocked", "cancelled"} and not state.settings_panel_opened:
        return InvariantResult.fail("startup UI reached a user decision before settings panel structure was verified")
    if state.settings_panel_opened and not state.language_visible_in_settings:
        return InvariantResult.fail("settings panel did not contain language selection")
    if state.settings_panel_opened and not (
        state.support_developer_visible_in_settings
        and state.support_uses_canonical_url
        and state.support_entitlement_disclaimer_visible
    ):
        return InvariantResult.fail("settings panel did not contain the canonical support-developer entry")
    if state.support_claims_paid_entitlement:
        return InvariantResult.fail("support developer copy implied a paid entitlement")
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
        if state.background_collaboration_authorized is not True:
            return InvariantResult.fail("startup answers accepted without background_collaboration_authorized=true")
        if state.legacy_startup_option_key_seen in LEGACY_STARTUP_OPTION_KEYS:
            return InvariantResult.fail("legacy startup option key was accepted")
    if state.legacy_startup_option_key_seen in LEGACY_STARTUP_OPTION_KEYS and state.ui_result == "confirmed":
        return InvariantResult.fail("legacy startup option key was accepted")
    if state.controller_core_loaded and not state.background_collaboration_requested:
        return InvariantResult.fail("Controller loaded before requesting mandatory background collaboration")
    if state.background_collaboration_requested and state.background_collaboration_authorized is not True:
        return InvariantResult.fail("background collaboration was requested without explicit UI acknowledgement")
    if state.background_collaboration_requested and not state.host_background_collaboration_available:
        return InvariantResult.fail("FlowPilot continued after host background collaboration was unavailable")
    if state.cockpit_opened:
        return InvariantResult.fail("Cockpit opened despite UI chat display choice")
    if state.controller_core_loaded and not state.chat_display_requirement_recorded:
        return InvariantResult.fail("chat display choice reached Controller without required chat display record")
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
    safe_waiting = replace(
        _source_safe_state(replace(initial_state(), router_loaded=True, ui_opened=True, status="waiting_ui")),
        settings_button_visible=True,
        language_visible_on_main=False,
        settings_panel_opened=True,
        language_visible_in_settings=True,
        support_developer_visible_in_settings=True,
        support_uses_canonical_url=True,
        support_entitlement_disclaimer_visible=True,
        support_claims_paid_entitlement=False,
    )
    base = _confirm_state(safe_waiting)
    recorded = replace(base, startup_answers_recorded=True, startup_answer_values_valid=True)
    encoded = replace(base, artifact_encoding_contract_verified=True)
    recorded = replace(encoded, startup_answers_recorded=True, startup_answer_values_valid=True)
    return {
        "controller_before_ui_confirm": replace(initial_state(), controller_core_loaded=True),
        "block_or_cancel_continues_to_run": replace(
            initial_state(),
            router_loaded=True,
            ui_opened=True,
            ui_result="cancelled",
            status="cancelled",
            launch_mode="interactive_native",
            headless_result=False,
            formal_startup_allowed=True,
            run_shell_created=True,
        ),
        "controller_body_leak": replace(recorded, body_text_in_controller_visible_state=True),
        "ui_opened_before_source_encoding_check": replace(
            initial_state(),
            router_loaded=True,
            ui_opened=True,
            status="waiting_ui",
        ),
        "language_visible_on_main_surface": replace(
            safe_waiting,
            language_visible_on_main=True,
        ),
        "settings_panel_missing_language": replace(
            safe_waiting,
            language_visible_in_settings=False,
        ),
        "settings_panel_missing_support_url": replace(
            safe_waiting,
            support_uses_canonical_url=False,
        ),
        "support_copy_claims_paid_entitlement": replace(
            safe_waiting,
            support_claims_paid_entitlement=True,
        ),
        "utf8_no_bom_script_source_unsupported_historical_powershell_parse_break": replace(
            recorded,
            script_source_contains_non_ascii=True,
            script_source_utf8_bom=False,
            unsupported_historical_powershell_source_parse_safe=False,
        ),
        "accepted_without_hash": replace(recorded, body_hash_verified=False),
        "ui_result_json_bom_breaks_router": replace(recorded, result_json_no_bom=False),
        "ui_receipt_json_bom_breaks_router": replace(recorded, receipt_json_no_bom=False),
        "ui_envelope_json_bom_breaks_router": replace(recorded, envelope_json_no_bom=False),
        "unsupported_historical_bom_json_without_reader_support": replace(recorded, router_json_reader_bom_tolerant=False),
        "headless_result_accepted": replace(
            recorded,
            launch_mode="headless",
            headless_result=True,
            formal_startup_allowed=False,
        ),
        "body_bom_leaks_to_pm_packet": replace(
            recorded,
            pm_intake_packet_created=True,
            body_has_leading_bom=True,
            pm_packet_body_bom_stripped=False,
        ),
        "bom_repair_bypasses_body_hash": replace(recorded, body_hash_verified=False),
        "background_ack_missing": replace(recorded, background_collaboration_authorized=None),
        "background_ack_false": replace(recorded, background_collaboration_authorized=False),
        "legacy_runtime_role_assistance_key_accepted": replace(
            recorded,
            legacy_startup_option_key_seen="runtime_role_assistances",
        ),
        "legacy_single_agent_key_accepted": replace(
            recorded,
            legacy_startup_option_key_seen="single_agent_role_continuity_authorized",
        ),
        "legacy_heartbeat_key_accepted": replace(
            recorded,
            legacy_startup_option_key_seen="heartbeat_requested",
        ),
        "background_requested_without_ack": replace(
            recorded,
            background_collaboration_authorized=False,
            background_collaboration_requested=True,
        ),
        "host_background_unavailable_continues": replace(
            recorded,
            pm_intake_packet_created=True,
            pm_is_only_body_reader=True,
            reviewer_checked_ui_record=True,
            reviewer_checked_ui_receipt=True,
            reviewer_checked_envelope_hash=True,
            reviewer_startup_passed=True,
            background_collaboration_requested=True,
            host_background_collaboration_available=False,
            chat_display_requirement_recorded=True,
            controller_core_loaded=True,
        ),
        "chat_opens_cockpit": replace(
            recorded,
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
    safe_waiting = replace(
        _source_safe_state(replace(initial_state(), router_loaded=True, ui_opened=True, status="waiting_ui")),
        settings_button_visible=True,
        language_visible_on_main=False,
        settings_panel_opened=True,
        language_visible_in_settings=True,
        support_developer_visible_in_settings=True,
        support_uses_canonical_url=True,
        support_entitlement_disclaimer_visible=True,
        support_claims_paid_entitlement=False,
    )
    return replace(
        _confirm_state(safe_waiting),
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
        background_collaboration_requested=True,
        host_background_collaboration_available=True,
        cockpit_opened=False,
        chat_display_requirement_recorded=True,
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
