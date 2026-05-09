"""Unified repo CLI for FlowPilot packet and role-output runtimes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))

import packet_runtime  # noqa: E402
import role_output_runtime  # noqa: E402


def _read_text_arg(text_value: str, file_value: str) -> str:
    if file_value:
        return Path(file_value).read_text(encoding="utf-8")
    return text_value


def _read_body_json(root: Path, raw_json: str, body_file: str) -> dict | None:
    if raw_json:
        return json.loads(raw_json)
    if body_file:
        path = Path(body_file)
        if not path.is_absolute():
            path = root / path
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Open packets and submit role outputs through one FlowPilot runtime entry.")
    parser.add_argument("--root", default=".", help="Project root containing .flowpilot")
    sub = parser.add_subparsers(dest="command", required=True)

    open_packet = sub.add_parser("open-packet", help="Open a packet through the packet runtime session.")
    open_packet.add_argument("--envelope-path", required=True)
    open_packet.add_argument("--role", required=True)
    open_packet.add_argument("--agent-id", required=True)

    complete_packet = sub.add_parser("complete-packet", help="Complete a packet session and generate a result envelope.")
    complete_packet.add_argument("--session-path", required=True)
    complete_packet.add_argument("--result-body-text", default="")
    complete_packet.add_argument("--result-body-file", default="")
    complete_packet.add_argument("--next-recipient", required=True)

    run_packet = sub.add_parser("run-packet", help="Open and complete a packet in one runtime call.")
    run_packet.add_argument("--envelope-path", required=True)
    run_packet.add_argument("--role", required=True)
    run_packet.add_argument("--agent-id", required=True)
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
