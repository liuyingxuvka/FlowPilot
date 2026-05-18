"""Packet runtime cli helpers for FlowPilot packet runtime."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

import barrier_bundle
from packet_runtime_active_holder import (
    _load_active_holder_lease,
    _require_concrete_agent_id,
    active_holder_ack,
    active_holder_progress,
    active_holder_submit_existing_result,
    active_holder_submit_result,
    issue_active_holder_lease,
)
from packet_runtime_contracts import (
    contract_self_check_metadata,
    default_output_contract,
    ensure_packet_identity_boundary,
    ensure_packet_output_contract_section,
    ensure_result_identity_boundary,
    mutual_role_reminder,
    normalize_output_contract,
    output_contract_id,
    packet_open_work_authority,
    validate_packet_identity_boundary,
    validate_result_identity_boundary,
)
from packet_runtime_ledger import (
    _empty_packet_ledger,
    _packet_ledger_record,
    _update_packet_record,
    _upsert_barrier_bundle_record,
    _upsert_packet_record,
    packet_ledger_record_for_envelope,
)
from packet_runtime_paths import (
    active_run_root,
    load_envelope,
    normalize_envelope_aliases,
    packet_paths,
    packet_paths_from_any_envelope,
    packet_paths_from_envelope,
    packet_paths_from_result_envelope,
    project_relative,
    read_json,
    read_json_if_exists,
    resolve_project_path,
    verify_body_hash,
)
from packet_runtime_relay import (
    _completed_agent_id_is_role_key,
    _same_project_path,
    controller_relay_envelope,
    mark_controller_contamination,
    validate_packet_ready_for_direct_relay,
    validate_result_ready_for_reviewer_relay,
    verify_controller_relay,
    verify_packet_open_receipt,
    verify_router_startup_release,
)
from packet_runtime_reviewer import validate_for_reviewer
from packet_runtime_schema import (
    ACTIVE_HOLDER_EVENT_SCHEMA,
    ACTIVE_HOLDER_LEASE_SCHEMA,
    BARRIER_BUNDLE_SCHEMA,
    CHAIN_AUDIT_SCHEMA,
    CONTROLLER_HANDOFF_SCHEMA,
    CONTROLLER_NEXT_ACTION_NOTICE_SCHEMA,
    CONTROLLER_RELAY_SCHEMA,
    DEFAULT_CONTROLLER_ALLOWED_ACTIONS,
    DEFAULT_CONTROLLER_FORBIDDEN_ACTIONS,
    DIRECT_DISPATCH_FORBIDDEN_ALLOWED_ACTIONS,
    DIRECT_DISPATCH_PACKET_REQUIRED_FIELDS,
    DIRECT_DISPATCH_REQUIRED_FORBIDDEN_ACTIONS,
    OUTPUT_CONTRACT_FORBIDDEN_ENVELOPE_BODY_FIELDS,
    OUTPUT_CONTRACT_REQUIRED_RESULT_ENVELOPE_FIELDS,
    OUTPUT_CONTRACT_REQUIRED_RESULT_SECTIONS,
    OUTPUT_CONTRACT_SCHEMA,
    PACKET_ENVELOPE_SCHEMA,
    PACKET_IDENTITY_MARKER,
    PACKET_LEDGER_SCHEMA,
    PROGRESS_MESSAGE_FORBIDDEN_TERMS,
    PROGRESS_MESSAGE_MAX_LEN,
    RESULT_CONTROLLER_ALLOWED_ACTIONS,
    RESULT_CONTROLLER_FORBIDDEN_ACTIONS,
    RESULT_ENVELOPE_SCHEMA,
    RESULT_IDENTITY_MARKER,
    RESULT_REVIEW_SESSION_SCHEMA,
    ROLE_KEYS,
    ROLE_PACKET_SESSION_SCHEMA,
    ROUTER_STARTUP_RELEASE_SCHEMA,
    SEALED_BODY_VISIBILITY,
    USER_INTAKE_BODY_VISIBILITY,
    PacketRuntimeError,
    envelope_hash,
    sha256_file,
    stable_json_hash,
    utc_now,
    validate_packet_id,
    write_json_atomic,
    write_text_atomic,
)
from packet_runtime_sessions import (
    _load_role_packet_session,
    begin_result_review_session,
    begin_role_packet_session,
    complete_role_packet_session,
    run_role_packet_session,
)




















from packet_runtime_audit import audit_packet_chain
from packet_runtime_creation import build_controller_handoff, create_packet, create_user_intake_packet, read_packet_body_for_role
from packet_runtime_progress import update_controller_progress
from packet_runtime_results import read_result_body_for_role, write_result

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create and validate physical FlowPilot packet envelope/body files.")
    parser.add_argument("--root", default=".", help="Project root containing .flowpilot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    issue = subparsers.add_parser("issue", help="Write packet_envelope.json and packet_body.md")
    issue.add_argument("--run-id", default="")
    issue.add_argument("--packet-id", required=True)
    issue.add_argument("--from-role", required=True)
    issue.add_argument("--to-role", required=True)
    issue.add_argument("--node-id", required=True)
    issue.add_argument("--body-text", default="")
    issue.add_argument("--body-file", default="")
    issue.add_argument("--return-to", default="controller")
    issue.add_argument("--next-holder", default="")
    issue.add_argument("--replacement-for", default="")

    intake = subparsers.add_parser("user-intake", help="Write the first user prompt packet for PM")
    intake.add_argument("--run-id", default="")
    intake.add_argument("--packet-id", required=True)
    intake.add_argument("--node-id", required=True)
    intake.add_argument("--body-text", default="")
    intake.add_argument("--body-file", default="")
    intake.add_argument("--startup-options-json", default="")
    intake.add_argument("--background-agents-authorized", action="store_true")
    intake.add_argument("--heartbeat-requested", action="store_true")
    intake.add_argument("--display-surface", default="")

    handoff = subparsers.add_parser("handoff", help="Print controller-visible envelope handoff only")
    handoff.add_argument("--envelope-path", required=True)

    relay = subparsers.add_parser("relay", help="Controller signs and relays an envelope without opening body")
    relay.add_argument("--envelope-path", required=True)
    relay.add_argument("--controller-agent-id", default="controller")
    relay.add_argument("--received-from-role", default="")
    relay.add_argument("--relayed-to-role", default="")
    relay.add_argument("--holder-before", default="")
    relay.add_argument("--holder-after", default="")
    relay.add_argument("--body-was-read-by-controller", action="store_true")
    relay.add_argument("--body-was-executed-by-controller", action="store_true")
    relay.add_argument("--private-role-to-role-delivery-detected", action="store_true")

    read_packet = subparsers.add_parser("read-packet", help="Target role verifies relay and opens packet body")
    read_packet.add_argument("--envelope-path", required=True)
    read_packet.add_argument("--role", required=True)

    open_packet_session = subparsers.add_parser(
        "open-packet-session",
        help="Target role opens a packet through the runtime session entrypoint",
    )
    open_packet_session.add_argument("--envelope-path", required=True)
    open_packet_session.add_argument("--role", required=True)
    open_packet_session.add_argument("--agent-id", required=True)

    complete_packet_session = subparsers.add_parser(
        "complete-packet-session",
        help="Complete a previously opened role packet session and generate the result envelope",
    )
    complete_packet_session.add_argument("--session-path", required=True)
    complete_packet_session.add_argument("--result-body-text", default="")
    complete_packet_session.add_argument("--result-body-file", default="")
    complete_packet_session.add_argument("--next-recipient", required=True)

    run_packet_session = subparsers.add_parser(
        "run-packet-session",
        help="Open a packet session and complete it in one runtime call",
    )
    run_packet_session.add_argument("--envelope-path", required=True)
    run_packet_session.add_argument("--role", required=True)
    run_packet_session.add_argument("--agent-id", required=True)
    run_packet_session.add_argument("--result-body-text", default="")
    run_packet_session.add_argument("--result-body-file", default="")
    run_packet_session.add_argument("--next-recipient", required=True)

    progress = subparsers.add_parser("progress", help="Target role updates Controller-visible packet progress")
    progress.add_argument("--envelope-path", required=True)
    progress.add_argument("--role", required=True)
    progress.add_argument("--agent-id", required=True)
    progress.add_argument("--progress", required=True, type=int)
    progress.add_argument("--message", required=True)

    issue_active = subparsers.add_parser(
        "issue-active-holder-lease",
        help="Router issues a scoped fast-lane lease to the current packet holder",
    )
    issue_active.add_argument("--envelope-path", required=True)
    issue_active.add_argument("--holder-role", required=True)
    issue_active.add_argument("--holder-agent-id", required=True)
    issue_active.add_argument("--route-version", required=True, type=int)
    issue_active.add_argument("--frontier-version", required=True, type=int)
    issue_active.add_argument("--allowed-action", action="append", default=[])

    active_ack = subparsers.add_parser("active-holder-ack", help="Current holder acknowledges a fast-lane packet lease")
    active_ack.add_argument("--lease-path", required=True)
    active_ack.add_argument("--role", required=True)
    active_ack.add_argument("--agent-id", required=True)
    active_ack.add_argument("--route-version", type=int, default=None)
    active_ack.add_argument("--frontier-version", type=int, default=None)

    active_progress = subparsers.add_parser(
        "active-holder-progress",
        help="Current holder writes controller-safe fast-lane packet progress",
    )
    active_progress.add_argument("--lease-path", required=True)
    active_progress.add_argument("--role", required=True)
    active_progress.add_argument("--agent-id", required=True)
    active_progress.add_argument("--progress", required=True, type=int)
    active_progress.add_argument("--message", required=True)
    active_progress.add_argument("--route-version", type=int, default=None)
    active_progress.add_argument("--frontier-version", type=int, default=None)

    active_submit = subparsers.add_parser(
        "active-holder-submit-result",
        help="Current holder submits a result through the fast lane and writes a Controller next-action notice",
    )
    active_submit.add_argument("--lease-path", required=True)
    active_submit.add_argument("--role", required=True)
    active_submit.add_argument("--agent-id", required=True)
    active_submit.add_argument("--result-body-text", default="")
    active_submit.add_argument("--result-body-file", default="")
    active_submit.add_argument("--next-recipient", required=True)
    active_submit.add_argument("--route-version", type=int, default=None)
    active_submit.add_argument("--frontier-version", type=int, default=None)

    active_submit_existing = subparsers.add_parser(
        "active-holder-submit-existing-result",
        help="Current holder submits an existing result envelope through the fast lane",
    )
    active_submit_existing.add_argument("--lease-path", required=True)
    active_submit_existing.add_argument("--role", required=True)
    active_submit_existing.add_argument("--agent-id", required=True)
    active_submit_existing.add_argument("--result-envelope-path", required=True)
    active_submit_existing.add_argument("--route-version", type=int, default=None)
    active_submit_existing.add_argument("--frontier-version", type=int, default=None)

    complete = subparsers.add_parser("complete", help="Write result_envelope.json and result_body.md")
    complete.add_argument("--envelope-path", required=True)
    complete.add_argument("--completed-by-role", required=True)
    complete.add_argument("--completed-by-agent-id", required=True)
    complete.add_argument("--result-body-text", default="")
    complete.add_argument("--result-body-file", default="")
    complete.add_argument("--next-recipient", required=True)
    complete.add_argument("--allow-wrong-role-for-audit", action="store_true")

    review = subparsers.add_parser("review", help="Validate packet/result envelope, hashes, and role origin")
    review.add_argument("--envelope-path", required=True)
    review.add_argument("--result-envelope-path", required=True)
    review.add_argument("--agent-role-map-json", default="")

    read_result = subparsers.add_parser("read-result", help="Reviewer/PM verifies relay and opens result body")
    read_result.add_argument("--result-envelope-path", required=True)
    read_result.add_argument("--role", required=True)

    open_result_session = subparsers.add_parser(
        "open-result-session",
        help="Reviewer/PM opens a result body through the runtime session entrypoint",
    )
    open_result_session.add_argument("--result-envelope-path", required=True)
    open_result_session.add_argument("--role", required=True)
    open_result_session.add_argument("--agent-id", required=True)

    audit_chain = subparsers.add_parser("audit-chain", help="Reviewer audits packet mail chain for a run or node")
    audit_chain.add_argument("--run-id", default="")
    audit_chain.add_argument("--node-id", default="")

    return parser.parse_args(argv)

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
                "background_agents_authorized": bool(args.background_agents_authorized),
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
    if args.command == "relay":
        envelope = load_envelope(root, args.envelope_path)
        relayed = controller_relay_envelope(
            root,
            envelope=envelope,
            envelope_path=args.envelope_path,
            controller_agent_id=args.controller_agent_id,
            received_from_role=args.received_from_role or None,
            relayed_to_role=args.relayed_to_role or None,
            holder_before=args.holder_before or None,
            holder_after=args.holder_after or None,
            body_was_read_by_controller=bool(args.body_was_read_by_controller),
            body_was_executed_by_controller=bool(args.body_was_executed_by_controller),
            private_role_to_role_delivery_detected=bool(args.private_role_to_role_delivery_detected),
        )
        print(json.dumps(relayed, indent=2, sort_keys=True))
        return 0
    if args.command == "read-packet":
        envelope = load_envelope(root, args.envelope_path)
        print(read_packet_body_for_role(root, envelope, role=args.role))
        return 0
    if args.command == "open-packet-session":
        session = begin_role_packet_session(
            root,
            envelope_path=args.envelope_path,
            role=args.role,
            agent_id=args.agent_id,
        )
        print(json.dumps(session, indent=2, sort_keys=True))
        return 0
    if args.command == "complete-packet-session":
        result = complete_role_packet_session(
            root,
            session_path=args.session_path,
            result_body_text=_read_text_arg(args.result_body_text, args.result_body_file),
            next_recipient=args.next_recipient,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "run-packet-session":
        output = run_role_packet_session(
            root,
            envelope_path=args.envelope_path,
            role=args.role,
            agent_id=args.agent_id,
            result_body_text=_read_text_arg(args.result_body_text, args.result_body_file),
            next_recipient=args.next_recipient,
        )
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    if args.command == "progress":
        status = update_controller_progress(
            root,
            envelope_path=args.envelope_path,
            role=args.role,
            agent_id=args.agent_id,
            progress=args.progress,
            message=args.message,
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
