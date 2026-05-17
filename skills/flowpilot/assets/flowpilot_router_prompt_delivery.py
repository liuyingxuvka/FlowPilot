"""Prompt and card-delivery prompt helpers for the FlowPilot router."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flowpilot_prompt_store import render_prompt_text
from flowpilot_router_controller_boundary import (
    CONTINUOUS_CONTROLLER_STANDBY_ACTION_TYPE,
    CONTROLLER_PATROL_TIMER_DEFAULT_SECONDS,
    _controller_patrol_timer_command,
)
from flowpilot_router_io import _flowpilot_runtime_entrypoint_ref


def card_checkin_instruction(
    project_root: Path,
    *,
    envelope_path: str,
    role: str,
    agent_id: str | None,
    card_return_event: str,
    bundle: bool,
) -> dict[str, Any]:
    command_name = "receive-card-bundle" if bundle else "receive-card"
    entrypoint = _flowpilot_runtime_entrypoint_ref(project_root)
    command = [
        "python",
        entrypoint,
        "--root",
        ".",
        command_name,
        "--envelope-path",
        envelope_path,
        "--role",
        role,
        "--agent-id",
        agent_id or "<agent-id>",
    ]
    post_ack_policy = render_prompt_text("cards.post_ack_policy")
    bundle_post_ack_policy = render_prompt_text("cards.bundle_post_ack_policy")
    return {
        "schema_version": "flowpilot.card_checkin_instruction.v1",
        "required": True,
        "command_name": command_name,
        "runtime_entrypoint": entrypoint,
        "run_from": "project_root",
        "command": command,
        "card_return_event": card_return_event,
        "ack_submission_mode": "direct_to_router",
        "controller_ack_handoff_allowed": False,
        "expected_outcome": "runtime writes the read receipt and direct Router ACK envelope",
        "post_ack_policy": post_ack_policy,
        "bundle_post_ack_policy": bundle_post_ack_policy if bundle else None,
        "do_not_handwrite_ack": True,
        "do_not_record_as_external_event": True,
        "plain_instruction": (
            f"Run {command_name} from the project root to open this card through the runtime and submit "
            f"{card_return_event} directly to Router. Do not hand-write the ACK, do not give the ACK to "
            "Controller, and do not record it as a normal external event. "
            f"{bundle_post_ack_policy if bundle else post_ack_policy}"
        ),
    }


def controller_break_glass_reminder() -> dict[str, Any]:
    playbook_path = "skills/flowpilot/assets/runtime_kit/cards/system/controller_break_glass_repair.md"
    return {
        "schema_version": "flowpilot.controller_break_glass_reminder.v1",
        "playbook_path": playbook_path,
        "text": (
            "Emergency break-glass reminder: use this only if normal FlowPilot "
            "control flow itself appears broken, stuck, looping, or unable to "
            "produce a legal next action. For that case only, read "
            f"`{playbook_path}`. Do not use it for ordinary project bugs, "
            "worker defects, review failures, or normal PM repair."
        ),
        "allowed_only_when": [
            "normal_flow_itself_broken",
            "stuck_or_looping_control_flow",
            "no_legal_next_controller_action",
            "normal_pm_control_blocker_packet_repair_unavailable_or_contradictory",
        ],
        "not_for": [
            "ordinary_project_bugs",
            "worker_defects",
            "review_failures",
            "normal_pm_repair",
            "route_or_acceptance_changes",
        ],
    }


def controller_table_prompt() -> dict[str, Any]:
    patrol_command = _controller_patrol_timer_command()
    break_glass = controller_break_glass_reminder()
    return {
        "language": "en",
        "prompt_kind": "controller_action_ledger_table_prompt",
        "text": render_prompt_text(
            "controller.action_ledger_table",
            {
                "break_glass_text": break_glass["text"],
                "patrol_command": patrol_command,
            },
        ),
        "applies_to": ["runtime/controller_action_ledger.json"],
        "break_glass_reminder": break_glass,
        "row_processing_order": "top_to_bottom",
        "foreground_controller_must_remain_attached_while_flowpilot_running": True,
        "continuous_standby_row": CONTINUOUS_CONTROLLER_STANDBY_ACTION_TYPE,
        "patrol_timer_command": patrol_command,
        "patrol_timer_seconds": CONTROLLER_PATROL_TIMER_DEFAULT_SECONDS,
        "sealed_body_reads_allowed": False,
    }


def startup_heartbeat_prompt(project_root: Path, run_id: str) -> str:
    return render_prompt_text(
        "startup.heartbeat_resume",
        {
            "project_root": project_root,
            "run_id": run_id,
        },
    )
