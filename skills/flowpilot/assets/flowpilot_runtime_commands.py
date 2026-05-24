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
from flowpilot_runtime_command_dispatch import execute_runtime_command  # noqa: E402
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


def _packet_record_summary(root: Path, envelope: dict[str, Any]) -> dict[str, Any]:
    paths = packet_runtime.packet_paths_from_any_envelope(root, envelope)
    packet_id = str(envelope.get("packet_id") or "")
    record = packet_runtime.packet_ledger_record_for_envelope(root, envelope)
    if isinstance(record, dict):
        return {
            "packet_id": packet_id,
            "active_packet_holder": record.get("active_packet_holder"),
            "active_packet_status": record.get("active_packet_status"),
            "packet_controller_relay_recorded": bool(record.get("packet_controller_relay")),
            "result_controller_relay_recorded": bool(record.get("result_controller_relay")),
            "active_holder_lease_issued": bool(record.get("active_holder_lease_issued")),
            "active_holder_lease_path": record.get("active_holder_lease_path"),
            "active_holder_liveness_proven": bool(record.get("active_holder_liveness_proven")),
        }
    return {"packet_id": packet_id, "record_missing": True}


def _relay_envelope(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    envelope = packet_runtime.load_envelope(root, args.envelope_path)
    relayed = packet_runtime.controller_relay_envelope(
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
    relay = packet_runtime.verify_controller_relay(
        relayed,
        recipient_role=str(args.relayed_to_role or relayed.get("to_role") or relayed.get("next_recipient") or ""),
    )
    lease: dict[str, Any] | None = None
    holder_agent_id = str(args.holder_agent_id or "").strip()
    if holder_agent_id:
        if args.route_version is None or args.frontier_version is None:
            raise packet_runtime.PacketRuntimeError(
                "relay-envelope with --holder-agent-id requires --route-version and --frontier-version"
            )
        holder_role = str(args.relayed_to_role or relayed.get("to_role") or relayed.get("next_recipient") or "")
        lease = packet_runtime.issue_active_holder_lease(
            root,
            packet_envelope=relayed,
            holder_role=holder_role,
            holder_agent_id=holder_agent_id,
            route_version=args.route_version,
            frontier_version=args.frontier_version,
            allowed_actions=args.allowed_action or None,
        )
    paths = packet_runtime.packet_paths_from_any_envelope(root, relayed)
    envelope_kind = "packet_envelope" if "body_path" in relayed else "result_envelope"
    result: dict[str, Any] = {
        "ok": True,
        "command": "relay-envelope",
        "packet_id": relayed.get("packet_id"),
        "envelope_kind": envelope_kind,
        "envelope_path": packet_runtime.project_relative(root, packet_runtime.resolve_project_path(root, str(args.envelope_path))),
        "packet_ledger_path": packet_runtime.project_relative(root, paths["packet_ledger"]),
        "relayed_to_role": relay.get("relayed_to_role"),
        "controller_agent_id": relay.get("controller_agent_id"),
        "controller_relay_signature_recorded": True,
        "controller_relay_envelope_hash": relay.get("envelope_hash"),
        "body_was_read_by_controller": relay.get("body_was_read_by_controller"),
        "body_was_executed_by_controller": relay.get("body_was_executed_by_controller"),
        "ledger_record": _packet_record_summary(root, relayed),
    }
    if lease is not None:
        result["active_holder_lease"] = {
            "lease_id": lease.get("lease_id"),
            "lease_path": lease.get("lease_path"),
            "holder_role": lease.get("holder_role"),
            "holder_agent_id": lease.get("holder_agent_id"),
            "route_version": lease.get("route_version"),
            "frontier_version": lease.get("frontier_version"),
            "holder_liveness": lease.get("holder_liveness"),
        }
    return result


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

    result = execute_runtime_command(
        root,
        args,
        packet_runtime=packet_runtime,
        card_runtime=card_runtime,
        flowpilot_router=flowpilot_router,
        role_output_runtime=role_output_runtime,
        execute_role_output_command=execute_role_output_command,
        read_text_arg=_read_text_arg,
        read_body_json=_read_body_json,
        relay_envelope=_relay_envelope,
        record_router_event_or_blocked_next_action=_record_router_event_or_blocked_next_action,
        receive_card=_receive_card,
        receive_card_bundle=_receive_card_bundle,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.command in {"active-holder-submit-result", "active-holder-submit-existing-result"} and result.get("passed") is False:
        return 2
    return 0

__all__ = (
    "_read_text_arg",
    "_read_body_json",
    "_packet_record_summary",
    "_relay_envelope",
    "_record_router_event_or_blocked_next_action",
    "_receive_card",
    "_receive_card_bundle",
    "main",
)
