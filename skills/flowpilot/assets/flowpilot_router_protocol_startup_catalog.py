"""Startup question and boot action catalog for FlowPilot router protocol startup."""

from __future__ import annotations

from typing import Any

PM_PRIOR_CONTEXT_REQUIRED_CARD_IDS = {
    "pm.prior_path_context",
    "pm.route_skeleton",
    "pm.product_behavior_model_decision",
    "pm.process_route_model_decision",
    "pm.crew_rehydration_freshness",
    "pm.resume_decision",
    "pm.current_node_loop",
    "pm.node_acceptance_plan",
    "pm.model_miss_triage",
    "pm.review_repair",
    "pm.parent_segment_decision",
    "pm.evidence_quality_package",
    "pm.final_ledger",
    "pm.closure",
}

STARTUP_QUESTIONS = (
    {
        "id": "background_agents",
        "question": "Allow the standard six live background roles, or use single-agent six-role continuity?",
    },
    {
        "id": "scheduled_continuation",
        "question": "Allow scheduled continuation/heartbeat, or use manual resume only?",
    },
    {
        "id": "display_surface",
        "question": "Open FlowPilot Cockpit when startup state is ready, or use chat route signs?",
    },
)

BOOT_ACTIONS: tuple[dict[str, Any], ...] = (
    {
        "action_type": "create_run_shell",
        "flag": "run_shell_created",
        "label": "run_shell_created",
        "summary": "Create a fresh run root under .flowpilot/runs.",
        "actor": "bootloader",
    },
    {
        "action_type": "write_current_pointer",
        "flag": "current_pointer_written",
        "label": "current_pointer_written",
        "summary": "Write .flowpilot/current.json as the active-run pointer.",
        "actor": "bootloader",
    },
    {
        "action_type": "update_run_index",
        "flag": "run_index_updated",
        "label": "run_index_updated",
        "summary": "Register the active run in .flowpilot/index.json.",
        "actor": "bootloader",
    },
    {
        "action_type": "start_router_daemon",
        "flag": "router_daemon_started",
        "label": "formal_router_daemon_started_as_startup_driver",
        "summary": "Start or attach the built-in one-second Router daemon, then let it schedule startup rows before any external startup work.",
        "actor": "bootloader",
    },
    {
        "action_type": "open_startup_intake_ui",
        "flag": "startup_questions_asked",
        "label": "startup_intake_ui_opened_from_router",
        "summary": "Open the native FlowPilot startup intake UI, then return to Router daemon status and the Controller action ledger without reading the body text in Controller context.",
        "actor": "bootloader",
        "requires_host_automation": True,
        "requires_payload": "startup_intake_result",
        "terminal_for_turn": True,
    },
    {
        "action_type": "write_startup_awaiting_answers_state",
        "flag": "startup_state_written_awaiting_answers",
        "label": "startup_state_written_awaiting_answers",
        "summary": "Record that the startup dialog is waiting for explicit user answers.",
        "actor": "bootloader",
    },
    {
        "action_type": "stop_for_startup_answers",
        "flag": "dialog_stopped_for_answers",
        "label": "dialog_stopped_for_startup_answers",
        "summary": "Stop after asking startup questions; no banner, route, agents, heartbeat, or implementation may start.",
        "actor": "bootloader",
        "terminal_for_turn": True,
    },
    {
        "action_type": "record_startup_answers",
        "flag": "startup_answers_recorded",
        "label": "startup_answers_recorded_by_router",
        "summary": "Record the later user reply that explicitly answered all startup questions.",
        "actor": "bootloader",
        "requires_user": True,
        "requires_payload": "startup_answers",
    },
    {
        "action_type": "copy_runtime_kit",
        "flag": "runtime_kit_copied",
        "label": "bootstrap_runtime_kit_copied",
        "summary": "Copy the audited runtime kit into the run root without generating new prompt bodies.",
        "actor": "bootloader",
    },
    {
        "action_type": "fill_runtime_placeholders",
        "flag": "placeholders_filled",
        "label": "bootstrap_placeholders_filled",
        "summary": "Fill run id, timestamps, and startup-answer placeholders only.",
        "actor": "bootloader",
    },
    {
        "action_type": "initialize_mailbox",
        "flag": "mailbox_initialized",
        "label": "mailbox_initialized_from_copied_kit",
        "summary": "Create mailbox, prompt-delivery, and packet-ledger state files.",
        "actor": "bootloader",
    },
    {
        "action_type": "record_user_request",
        "flag": "user_request_recorded",
        "label": "user_request_recorded_from_explicit_user_request",
        "summary": "Record the exact current FlowPilot task text from explicit user input while the full user_intake remains sealed until startup activation.",
        "actor": "bootloader",
        "requires_user": True,
        "requires_payload": "user_request",
    },
    {
        "action_type": "write_user_intake",
        "flag": "user_intake_ready",
        "label": "user_intake_template_filled_from_raw_user_request",
        "summary": "Write the user-intake packet from the router-recorded raw user request and startup answers.",
        "actor": "bootloader",
    },
    {
        "action_type": "load_controller_core",
        "flag": "controller_core_loaded",
        "label": "controller_core_loaded",
        "summary": "End bootloader startup, attach Controller to the Router daemon action ledger, and record Controller boundary confirmation evidence before Controller-ledger startup obligations.",
        "actor": "bootloader",
    },
    {
        "action_type": "emit_startup_banner",
        "flag": "banner_emitted",
        "label": "startup_banner_emitted_after_controller_core",
        "summary": "Display the startup banner in the user dialog after Controller core is loaded, then record the confirmed display.",
        "actor": "bootloader",
        "card_id": "startup_banner",
    },
    {
        "action_type": "create_heartbeat_automation",
        "flag": "continuation_binding_recorded",
        "label": "host_bootstraps_startup_heartbeat_automation",
        "summary": "Create the one-minute Codex heartbeat after Controller core handoff and before startup review or route work.",
        "actor": "bootloader",
        "requires_host_automation": True,
    },
    {
        "action_type": "start_role_slots",
        "flag": "roles_started",
        "label": "six_roles_started_from_user_answer",
        "summary": "Start the six current-task roles and record same-action role core prompt delivery according to the user's background-agent answer.",
        "actor": "bootloader",
    },
    {
        "action_type": "inject_role_core_prompts",
        "flag": "role_core_prompts_injected",
        "label": "role_core_prompts_injected_from_copied_kit",
        "summary": "Legacy recovery: deliver each role only its role core card from the copied runtime kit when an older bootstrap state still lacks the delivery receipt.",
        "actor": "bootloader",
    },
)


def startup_boot_catalog() -> dict[str, object]:
    """Return the externally visible startup question and boot-action catalog."""

    return {
        "pm_prior_context_required_card_ids": frozenset(PM_PRIOR_CONTEXT_REQUIRED_CARD_IDS),
        "startup_questions": STARTUP_QUESTIONS,
        "boot_actions": BOOT_ACTIONS,
        "startup_question_ids": tuple(question["id"] for question in STARTUP_QUESTIONS),
        "boot_action_types": tuple(action["action_type"] for action in BOOT_ACTIONS),
    }


__all__ = (
    "PM_PRIOR_CONTEXT_REQUIRED_CARD_IDS",
    "STARTUP_QUESTIONS",
    "BOOT_ACTIONS",
    "startup_boot_catalog",
)
