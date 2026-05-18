"""Command execution for the unified FlowPilot runtime CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ASSETS = Path(__file__).resolve().parent
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))

import card_runtime  # noqa: E402
import flowpilot_router  # noqa: E402
import packet_runtime  # noqa: E402
import role_output_runtime  # noqa: E402
from flowpilot_runtime_args import parse_args  # noqa: E402
from flowpilot_runtime_role_output_commands import execute_role_output_command  # noqa: E402

def _read_text_arg(text_value: str, file_value: str) -> str:
    if file_value:
        return Path(file_value).read_text(encoding="utf-8")
    return text_value


def _read_body_json(root: Path, raw_json: str, body_file: str) -> dict[str, Any] | None:
    if raw_json:
        return json.loads(raw_json)
    if body_file:
        path = Path(body_file)
        if not path.is_absolute():
            path = root / path
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _record_router_event_or_blocked_next_action(root: Path, event_name: str, envelope: dict[str, Any]) -> dict[str, Any]:
    try:
        return {
            "blocked": False,
            "router_result": flowpilot_router.record_external_event(root, event_name, envelope),
        }
    except flowpilot_router.RouterError as exc:
        blocker = getattr(exc, "control_blocker", None)
        if not isinstance(blocker, dict):
            raise
        next_action: dict[str, Any] | None = None
        next_action_error: dict[str, str] | None = None
        try:
            next_action = flowpilot_router.next_action(root)
        except Exception as next_exc:  # pragma: no cover - defensive fallback, original blocker still returned
            next_action_error = {
                "error_type": type(next_exc).__name__,
                "message": str(next_exc),
            }
        result: dict[str, Any] = {
            "blocked": True,
            "router_result": {
                "ok": False,
                "event": event_name,
                "router_error": str(exc),
                "control_blocker": blocker,
            },
            "router_error": str(exc),
            "control_blocker": blocker,
            "next_action": next_action,
            "next_action_source": "router" if next_action is not None else "unavailable",
            "controller_next_step_source": "router_next_action_after_control_blocker",
        }
        if next_action_error is not None:
            result["next_action_error"] = next_action_error
        return result


def _receive_card(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    opened = card_runtime.open_card(
        root,
        envelope_path=args.envelope_path,
        role=args.role,
        agent_id=args.agent_id,
    )
    ack = card_runtime.submit_card_ack(
        root,
        envelope_path=args.envelope_path,
        role=args.role,
        agent_id=args.agent_id,
        receipt_paths=[str(opened["read_receipt_path"])],
        status=args.status,
    )
    validation = card_runtime.validate_card_ack(
        root,
        ack_path=str(ack["ack_path"]),
        envelope_path=args.envelope_path,
    )
    return {
        "ok": True,
        "command": "receive-card",
        "opened": opened,
        "ack": ack,
        "validation": validation,
    }


def _receive_card_bundle(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    opened = card_runtime.open_card_bundle(
        root,
        envelope_path=args.envelope_path,
        role=args.role,
        agent_id=args.agent_id,
    )
    ack = card_runtime.submit_card_bundle_ack(
        root,
        envelope_path=args.envelope_path,
        role=args.role,
        agent_id=args.agent_id,
        receipt_paths=[str(path) for path in opened["read_receipt_paths"]],
        status=args.status,
    )
    validation = card_runtime.validate_card_bundle_ack(
        root,
        ack_path=str(ack["ack_path"]),
        envelope_path=args.envelope_path,
    )
    return {
        "ok": True,
        "command": "receive-card-bundle",
        "opened": opened,
        "ack": ack,
        "validation": validation,
    }

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = Path(args.root).resolve()
    if args.command == "open-packet":
        result = packet_runtime.begin_role_packet_session(
            root,
            envelope_path=args.envelope_path,
            role=args.role,
            agent_id=args.agent_id,
        )
    elif args.command == "open-card":
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
        result = _receive_card(root, args)
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
        result = _receive_card_bundle(root, args)
    elif args.command == "complete-packet":
        result = packet_runtime.complete_role_packet_session(
            root,
            session_path=args.session_path,
            result_body_text=_read_text_arg(args.result_body_text, args.result_body_file),
            next_recipient=args.next_recipient,
        )
    elif args.command == "run-packet":
        result = packet_runtime.run_role_packet_session(
            root,
            envelope_path=args.envelope_path,
            role=args.role,
            agent_id=args.agent_id,
            result_body_text=_read_text_arg(args.result_body_text, args.result_body_file),
            next_recipient=args.next_recipient,
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
            route_version=args.route_version,
            frontier_version=args.frontier_version,
        )
    elif args.command == "active-holder-submit-result":
        result = packet_runtime.active_holder_submit_result(
            root,
            lease_path=args.lease_path,
            role=args.role,
            agent_id=args.agent_id,
            result_body_text=_read_text_arg(args.result_body_text, args.result_body_file),
            next_recipient=args.next_recipient,
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
            read_body_json=_read_body_json,
            record_router_event_or_blocked_next_action=_record_router_event_or_blocked_next_action,
        )
    else:  # pragma: no cover - argparse enforces command choices
        raise RuntimeError(f"unknown command: {args.command}")
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.command in {"active-holder-submit-result", "active-holder-submit-existing-result"} and result.get("passed") is False:
        return 2
    return 0

__all__ = (
    "_read_text_arg",
    "_read_body_json",
    "_record_router_event_or_blocked_next_action",
    "_receive_card",
    "_receive_card_bundle",
    "main",
)
