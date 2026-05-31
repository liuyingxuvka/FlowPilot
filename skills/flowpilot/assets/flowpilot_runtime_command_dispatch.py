"""Command dispatch table for the unified FlowPilot runtime CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def execute_runtime_command(
    root: Path,
    args: Any,
    *,
    packet_runtime: Any,
    card_runtime: Any,
    flowpilot_router: Any,
    role_output_runtime: Any,
    execute_role_output_command: Callable[..., dict[str, Any]],
    read_text_arg: Callable[[str, str], str],
    read_body_json: Callable[[Path, str, str], dict[str, Any] | None],
    record_router_event_or_blocked_next_action: Callable[[Path, str, dict[str, Any]], dict[str, Any]],
    receive_card: Callable[[Path, Any], dict[str, Any]],
    receive_card_bundle: Callable[[Path, Any], dict[str, Any]],
) -> dict[str, Any]:
    if args.command == "open-card":
        result = card_runtime.open_card(
            root,
            envelope_path=args.envelope_path,
            role=args.role,
            agent_id=args.agent_id,
        )
    elif args.command == "ack-card":
        result = card_runtime.submit_card_ack(
            root,
            envelope_path=args.envelope_path,
            role=args.role,
            agent_id=args.agent_id,
            receipt_paths=args.receipt_path or None,
            status=args.status,
        )
    elif args.command == "receive-card":
        result = receive_card(root, args)
    elif args.command == "open-card-bundle":
        result = card_runtime.open_card_bundle(
            root,
            envelope_path=args.envelope_path,
            role=args.role,
            agent_id=args.agent_id,
        )
    elif args.command == "ack-card-bundle":
        result = card_runtime.submit_card_bundle_ack(
            root,
            envelope_path=args.envelope_path,
            role=args.role,
            agent_id=args.agent_id,
            receipt_paths=args.receipt_path or None,
            status=args.status,
        )
    elif args.command == "receive-card-bundle":
        result = receive_card_bundle(root, args)
    elif args.command == "complete-packet":
        result = packet_runtime.complete_role_packet_session(
            root,
            session_path=args.session_path,
            result_body_text=read_text_arg(args.result_body_text, args.result_body_file),
            next_recipient=args.next_recipient,
            controller_aside=args.controller_aside or None,
        )
    elif args.command == "issue-active-holder-lease":
        envelope = packet_runtime.load_envelope(root, args.envelope_path)
        result = packet_runtime.issue_active_holder_lease(
            root,
            packet_envelope=envelope,
            holder_role=args.holder_role,
            holder_agent_id=args.holder_agent_id,
            route_version=args.route_version,
            frontier_version=args.frontier_version,
            allowed_actions=args.allowed_action or None,
        )
    elif args.command == "active-holder-ack":
        result = packet_runtime.active_holder_ack(
            root,
            lease_path=args.lease_path,
            role=args.role,
            agent_id=args.agent_id,
            route_version=args.route_version,
            frontier_version=args.frontier_version,
        )
    elif args.command == "active-holder-progress":
        result = packet_runtime.active_holder_progress(
            root,
            lease_path=args.lease_path,
            role=args.role,
            agent_id=args.agent_id,
            progress=args.progress,
            message=args.message,
            controller_aside=args.controller_aside or None,
            route_version=args.route_version,
            frontier_version=args.frontier_version,
        )
    elif args.command == "active-holder-submit-result":
        result = packet_runtime.active_holder_submit_result(
            root,
            lease_path=args.lease_path,
            role=args.role,
            agent_id=args.agent_id,
            result_body_text=read_text_arg(args.result_body_text, args.result_body_file),
            next_recipient=args.next_recipient,
            controller_aside=args.controller_aside or None,
            route_version=args.route_version,
            frontier_version=args.frontier_version,
        )
    elif args.command == "active-holder-submit-existing-result":
        result = packet_runtime.active_holder_submit_existing_result(
            root,
            lease_path=args.lease_path,
            role=args.role,
            agent_id=args.agent_id,
            result_envelope_path=args.result_envelope_path,
            route_version=args.route_version,
            frontier_version=args.frontier_version,
        )
    elif args.command == "open-result":
        result = packet_runtime.begin_result_review_session(
            root,
            result_envelope_path=args.result_envelope_path,
            role=args.role,
            agent_id=args.agent_id,
        )
    elif args.command in {
        "prepare-output",
        "submit-output",
        "submit-output-to-router",
        "progress-output",
        "submit-controller-boundary-confirmation",
        "verify-output-envelope",
    }:
        result = execute_role_output_command(
            root,
            args,
            role_output_runtime=role_output_runtime,
            flowpilot_router=flowpilot_router,
            read_body_json=read_body_json,
            record_router_event_or_blocked_next_action=record_router_event_or_blocked_next_action,
        )
    else:  # pragma: no cover - argparse enforces command choices
        raise RuntimeError(f"unknown command: {args.command}")
    return result


__all__ = ("execute_runtime_command",)
