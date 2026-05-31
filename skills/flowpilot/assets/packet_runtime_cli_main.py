"""Command execution for the FlowPilot packet runtime CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from packet_runtime_active_holder import (
    active_holder_ack,
    active_holder_progress,
    active_holder_submit_existing_result,
    active_holder_submit_result,
    issue_active_holder_lease,
)
from packet_runtime_audit import audit_packet_chain
from packet_runtime_cli_args import parse_args
from packet_runtime_creation import (
    build_controller_handoff,
    controller_handoff_text,
    create_packet,
    create_user_intake_packet,
    read_packet_body_for_role,
)
from packet_runtime_paths import load_envelope
from packet_runtime_progress import update_controller_progress
from packet_runtime_results import read_result_body_for_role, write_result
from packet_runtime_reviewer import validate_for_reviewer
from packet_runtime_schema import PacketRuntimeError
from packet_runtime_sessions import (
    begin_result_review_session,
)


def _read_text_arg(text_value: str, file_value: str) -> str:
    if file_value:
        return Path(file_value).read_text(encoding="utf-8")
    return text_value


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = Path(args.root).resolve()
    if args.command == "issue":
        envelope = create_packet(
            root,
            run_id=args.run_id or None,
            packet_id=args.packet_id,
            from_role=args.from_role,
            to_role=args.to_role,
            node_id=args.node_id,
            body_text=_read_text_arg(args.body_text, args.body_file),
            return_to=args.return_to,
            next_holder=args.next_holder or None,
            replacement_for=args.replacement_for or None,
        )
        print(json.dumps(envelope, indent=2, sort_keys=True))
        return 0
    if args.command == "user-intake":
        startup_options = json.loads(args.startup_options_json) if args.startup_options_json else {}
        startup_options.update(
            {
                "runtime_role_assistance_authorized": bool(args.runtime_role_assistance_authorized),
                "heartbeat_requested": bool(args.heartbeat_requested),
                "display_surface": args.display_surface or "unspecified",
            }
        )
        envelope = create_user_intake_packet(
            root,
            run_id=args.run_id or None,
            packet_id=args.packet_id,
            node_id=args.node_id,
            body_text=_read_text_arg(args.body_text, args.body_file),
            startup_options=startup_options,
        )
        print(json.dumps(envelope, indent=2, sort_keys=True))
        return 0
    if args.command == "handoff":
        envelope = load_envelope(root, args.envelope_path)
        handoff = build_controller_handoff(envelope, envelope_path=args.envelope_path)
        print(controller_handoff_text(handoff))
        return 0
    if args.command == "read-packet":
        envelope = load_envelope(root, args.envelope_path)
        print(read_packet_body_for_role(root, envelope, role=args.role))
        return 0
    if args.command == "progress":
        status = update_controller_progress(
            root,
            envelope_path=args.envelope_path,
            role=args.role,
            agent_id=args.agent_id,
            progress=args.progress,
            message=args.message,
            controller_aside=args.controller_aside or None,
        )
        print(json.dumps(status, indent=2, sort_keys=True))
        return 0
    if args.command == "issue-active-holder-lease":
        envelope = load_envelope(root, args.envelope_path)
        lease = issue_active_holder_lease(
            root,
            packet_envelope=envelope,
            holder_role=args.holder_role,
            holder_agent_id=args.holder_agent_id,
            route_version=args.route_version,
            frontier_version=args.frontier_version,
            allowed_actions=args.allowed_action or None,
        )
        print(json.dumps(lease, indent=2, sort_keys=True))
        return 0
    if args.command == "active-holder-ack":
        event = active_holder_ack(
            root,
            lease_path=args.lease_path,
            role=args.role,
            agent_id=args.agent_id,
            route_version=args.route_version,
            frontier_version=args.frontier_version,
        )
        print(json.dumps(event, indent=2, sort_keys=True))
        return 0
    if args.command == "active-holder-progress":
        status = active_holder_progress(
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
        print(json.dumps(status, indent=2, sort_keys=True))
        return 0
    if args.command == "active-holder-submit-result":
        submission = active_holder_submit_result(
            root,
            lease_path=args.lease_path,
            role=args.role,
            agent_id=args.agent_id,
            result_body_text=_read_text_arg(args.result_body_text, args.result_body_file),
            next_recipient=args.next_recipient,
            controller_aside=args.controller_aside or None,
            route_version=args.route_version,
            frontier_version=args.frontier_version,
        )
        print(json.dumps(submission, indent=2, sort_keys=True))
        return 0 if submission["passed"] else 2
    if args.command == "active-holder-submit-existing-result":
        submission = active_holder_submit_existing_result(
            root,
            lease_path=args.lease_path,
            role=args.role,
            agent_id=args.agent_id,
            result_envelope_path=args.result_envelope_path,
            route_version=args.route_version,
            frontier_version=args.frontier_version,
        )
        print(json.dumps(submission, indent=2, sort_keys=True))
        return 0 if submission["passed"] else 2
    if args.command == "complete":
        envelope = load_envelope(root, args.envelope_path)
        result = write_result(
            root,
            packet_envelope=envelope,
            completed_by_role=args.completed_by_role,
            completed_by_agent_id=args.completed_by_agent_id,
            result_body_text=_read_text_arg(args.result_body_text, args.result_body_file),
            next_recipient=args.next_recipient,
            strict_role=not args.allow_wrong_role_for_audit,
            controller_aside=args.controller_aside or None,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "review":
        envelope = load_envelope(root, args.envelope_path)
        result = load_envelope(root, args.result_envelope_path)
        agent_role_map = json.loads(args.agent_role_map_json) if args.agent_role_map_json else None
        audit = validate_for_reviewer(root, packet_envelope=envelope, result_envelope=result, agent_role_map=agent_role_map)
        print(json.dumps(audit, indent=2, sort_keys=True))
        return 0 if audit["passed"] else 2
    if args.command == "read-result":
        result = load_envelope(root, args.result_envelope_path)
        print(read_result_body_for_role(root, result, role=args.role))
        return 0
    if args.command == "open-result-session":
        session = begin_result_review_session(
            root,
            result_envelope_path=args.result_envelope_path,
            role=args.role,
            agent_id=args.agent_id,
        )
        print(json.dumps(session, indent=2, sort_keys=True))
        return 0
    if args.command == "audit-chain":
        audit = audit_packet_chain(root, run_id=args.run_id or None, node_id=args.node_id or None)
        print(json.dumps(audit, indent=2, sort_keys=True))
        return 0 if audit["passed"] else 2
    raise PacketRuntimeError(f"unknown command: {args.command}")
