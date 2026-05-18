"""Role-output command execution for the unified FlowPilot runtime CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable


def execute_role_output_command(
    root: Path,
    args: Any,
    *,
    role_output_runtime: Any,
    flowpilot_router: Any,
    read_body_json: Callable[[Path, str, str], dict[str, Any] | None],
    record_router_event_or_blocked_next_action: Callable[[Path, str, dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    if args.command == "prepare-output":
        result = role_output_runtime.prepare_output_session(
            root,
            output_type=args.output_type,
            role=args.role,
            agent_id=args.agent_id,
            run_id=args.run_id or None,
            body_path=args.body_path or None,
            event_name=args.event_name or None,
            controller_status_packet_path=args.controller_status_packet_path or None,
        )
    elif args.command == "submit-output":
        body = read_body_json(root, args.body_json, args.body_file)
        result = role_output_runtime.submit_output(
            root,
            output_type=args.output_type,
            role=args.role,
            agent_id=args.agent_id,
            body=body,
            output_path=args.output_path or None,
            run_id=args.run_id or None,
            event_name=args.event_name or None,
            session_path=args.session_path or None,
            controller_status_packet_path=args.controller_status_packet_path or None,
        )
    elif args.command == "submit-output-to-router":
        body = read_body_json(root, args.body_json, args.body_file)
        authority = role_output_runtime.validate_direct_router_submission_authority(
            root,
            output_type=args.output_type,
            role=args.role,
            agent_id=args.agent_id,
            run_id=args.run_id or None,
            event_name=args.event_name or None,
            session_path=args.session_path or None,
        )
        envelope = role_output_runtime.submit_output(
            root,
            output_type=args.output_type,
            role=args.role,
            agent_id=args.agent_id,
            body=body,
            output_path=args.output_path or None,
            run_id=args.run_id or None,
            event_name=args.event_name or None,
            session_path=args.session_path or None,
            controller_status_packet_path=args.controller_status_packet_path or None,
        )
        event_name = str(args.event_name or envelope.get("event_name") or "").strip()
        if not event_name:
            raise role_output_runtime.RoleOutputRuntimeError("submit-output-to-router requires event_name")
        router_handoff = record_router_event_or_blocked_next_action(root, event_name, envelope)
        result = {
            "ok": True,
            "command": "submit-output-to-router",
            "event": event_name,
            "authority": authority,
            "envelope": envelope,
            **router_handoff,
        }
    elif args.command == "progress-output":
        result = role_output_runtime.update_output_progress(
            root,
            output_type=args.output_type,
            role=args.role,
            agent_id=args.agent_id,
            progress=args.progress,
            message=args.message,
            run_id=args.run_id or None,
            event_name=args.event_name or None,
            session_path=args.session_path or None,
            controller_status_packet_path=args.controller_status_packet_path or None,
        )
    elif args.command == "submit-controller-boundary-confirmation":
        result = role_output_runtime.submit_controller_boundary_confirmation(
            root,
            agent_id=args.agent_id,
            run_id=args.run_id or None,
            action_id=args.action_id or None,
            source_action_id=args.source_action_id or None,
            output_path=args.output_path or None,
            controller_status_packet_path=args.controller_status_packet_path or None,
        )
    elif args.command == "verify-output-envelope":
        envelope = json.loads(Path(args.envelope_file).read_text(encoding="utf-8"))
        result = role_output_runtime.validate_envelope_runtime_receipt(root, envelope) or {
            "ok": True,
            "runtime_receipt": "absent",
        }
    else:  # pragma: no cover - caller limits command choices
        raise RuntimeError(f"unknown role-output command: {args.command}")
    return result


__all__ = ("execute_role_output_command",)
