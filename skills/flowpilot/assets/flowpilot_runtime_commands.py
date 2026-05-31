"""Command execution for the unified FlowPilot runtime CLI."""

from __future__ import annotations

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
            "active_holder_lease_issued": bool(record.get("active_holder_lease_issued")),
            "active_holder_lease_path": record.get("active_holder_lease_path"),
            "active_holder_liveness_proven": bool(record.get("active_holder_liveness_proven")),
        }
    return {"packet_id": packet_id, "record_missing": True}


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
    "_record_router_event_or_blocked_next_action",
    "_receive_card",
    "_receive_card_bundle",
    "main",
)
