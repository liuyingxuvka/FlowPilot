"""Unified FlowPilot CLI for card, packet, and role-output runtimes."""

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
import packet_runtime  # noqa: E402
import role_output_runtime  # noqa: E402


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


def _add_card_identity_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--envelope-path", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--agent-id", required=True)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Open FlowPilot packets/cards and submit runtime-backed role outputs.")
    parser.add_argument("--root", default=".", help="Project root containing .flowpilot")
    sub = parser.add_subparsers(dest="command", required=True)

    open_packet = sub.add_parser("open-packet", help="Open a packet through the packet runtime session.")
    _add_card_identity_args(open_packet)

    open_card = sub.add_parser("open-card", help="Open a system-card envelope and write a read receipt.")
    _add_card_identity_args(open_card)

    ack_card = sub.add_parser("ack-card", help="Return an envelope-only card ACK referencing read receipts.")
    _add_card_identity_args(ack_card)
    ack_card.add_argument("--receipt-path", action="append", default=[])
    ack_card.add_argument("--status", choices=("acknowledged", "blocked"), default="acknowledged")

    receive_card = sub.add_parser("receive-card", help="Open a system card and write its runtime-backed ACK in one call.")
    _add_card_identity_args(receive_card)
    receive_card.add_argument("--status", choices=("acknowledged", "blocked"), default="acknowledged")

    open_bundle = sub.add_parser("open-card-bundle", help="Open a same-role system-card bundle and write read receipts.")
    _add_card_identity_args(open_bundle)

    ack_bundle = sub.add_parser("ack-card-bundle", help="Return one envelope-only ACK for a same-role card bundle.")
    _add_card_identity_args(ack_bundle)
    ack_bundle.add_argument("--receipt-path", action="append", default=[])
    ack_bundle.add_argument("--status", choices=("acknowledged", "blocked"), default="acknowledged")

    receive_bundle = sub.add_parser("receive-card-bundle", help="Open a system-card bundle and write its runtime-backed ACK.")
    _add_card_identity_args(receive_bundle)
    receive_bundle.add_argument("--status", choices=("acknowledged", "blocked"), default="acknowledged")

    complete_packet = sub.add_parser("complete-packet", help="Complete a packet session and generate a result envelope.")
    complete_packet.add_argument("--session-path", required=True)
    complete_packet.add_argument("--result-body-text", default="")
    complete_packet.add_argument("--result-body-file", default="")
    complete_packet.add_argument("--next-recipient", required=True)

    run_packet = sub.add_parser("run-packet", help="Open and complete a packet in one runtime call.")
    _add_card_identity_args(run_packet)
    run_packet.add_argument("--result-body-text", default="")
    run_packet.add_argument("--result-body-file", default="")
    run_packet.add_argument("--next-recipient", required=True)

    open_result = sub.add_parser("open-result", help="Open a result body through the review runtime session.")
    open_result.add_argument("--result-envelope-path", required=True)
    open_result.add_argument("--role", required=True)
    open_result.add_argument("--agent-id", required=True)

    prepare_output = sub.add_parser("prepare-output", help="Generate a role-output skeleton.")
    prepare_output.add_argument("--output-type", required=True, choices=sorted(role_output_runtime.SUPPORTED_OUTPUT_TYPES))
    prepare_output.add_argument("--role", required=True)
    prepare_output.add_argument("--agent-id", required=True)
    prepare_output.add_argument("--run-id", default="")
    prepare_output.add_argument("--body-path", default="")

    submit_output = sub.add_parser("submit-output", help="Submit a role-output body and return a compact envelope.")
    submit_output.add_argument("--output-type", required=True, choices=sorted(role_output_runtime.SUPPORTED_OUTPUT_TYPES))
    submit_output.add_argument("--role", required=True)
    submit_output.add_argument("--agent-id", required=True)
    submit_output.add_argument("--body-json", default="")
    submit_output.add_argument("--body-file", default="")
    submit_output.add_argument("--output-path", default="")
    submit_output.add_argument("--run-id", default="")
    submit_output.add_argument("--event-name", default="")

    verify_output = sub.add_parser("verify-output-envelope", help="Verify a role-output runtime receipt.")
    verify_output.add_argument("--envelope-file", required=True)

    return parser.parse_args(argv)


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
    elif args.command == "open-result":
        result = packet_runtime.begin_result_review_session(
            root,
            result_envelope_path=args.result_envelope_path,
            role=args.role,
            agent_id=args.agent_id,
        )
    elif args.command == "prepare-output":
        result = role_output_runtime.prepare_output_session(
            root,
            output_type=args.output_type,
            role=args.role,
            agent_id=args.agent_id,
            run_id=args.run_id or None,
            body_path=args.body_path or None,
        )
    elif args.command == "submit-output":
        body = _read_body_json(root, args.body_json, args.body_file)
        result = role_output_runtime.submit_output(
            root,
            output_type=args.output_type,
            role=args.role,
            agent_id=args.agent_id,
            body=body,
            output_path=args.output_path or None,
            run_id=args.run_id or None,
            event_name=args.event_name or None,
        )
    elif args.command == "verify-output-envelope":
        envelope = json.loads(Path(args.envelope_file).read_text(encoding="utf-8"))
        result = role_output_runtime.validate_envelope_runtime_receipt(root, envelope) or {
            "ok": True,
            "runtime_receipt": "absent",
        }
    else:  # pragma: no cover - argparse enforces command choices
        raise RuntimeError(f"unknown command: {args.command}")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
