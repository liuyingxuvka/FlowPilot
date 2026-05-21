"""Helper module for the role-output runtime facade."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from role_output_runtime_contracts import (
    _apply_runtime_fixed_values,
    _deep_merge,
    build_output_skeleton,
    validate_output_body,
)
from role_output_runtime_envelopes import (
    submit_controller_boundary_confirmation,
    submit_output,
    validate_envelope_runtime_receipt,
)
from role_output_runtime_progress import prepare_output_session, update_output_progress
from role_output_runtime_schema import (
    SUPPORTED_OUTPUT_TYPES,
    RoleOutputRuntimeError,
    _contract_by_id,
    _read_json,
    _resolve_project_path,
    _run_paths,
    _spec_for,
)

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare and submit FlowPilot role outputs through the runtime.")
    parser.add_argument("--root", default=".", help="Project root containing .flowpilot")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare-output", help="Generate a contract skeleton for a formal role output")
    prepare.add_argument("--output-type", required=True, choices=sorted(SUPPORTED_OUTPUT_TYPES))
    prepare.add_argument("--role", required=True)
    prepare.add_argument("--agent-id", required=True)
    prepare.add_argument("--run-id", default="")
    prepare.add_argument("--body-path", default="")
    prepare.add_argument("--event-name", default="")
    prepare.add_argument("--controller-status-packet-path", default="")

    validate = sub.add_parser("validate-output", help="Validate a role output body without writing an envelope")
    validate.add_argument("--output-type", required=True, choices=sorted(SUPPORTED_OUTPUT_TYPES))
    validate.add_argument("--role", required=True)
    validate.add_argument("--body-file", required=True)
    validate.add_argument("--run-id", default="")

    submit = sub.add_parser("submit-output", help="Validate a role output body and return an envelope")
    submit.add_argument("--output-type", required=True, choices=sorted(SUPPORTED_OUTPUT_TYPES))
    submit.add_argument("--role", required=True)
    submit.add_argument("--agent-id", required=True)
    submit.add_argument("--body-json", default="")
    submit.add_argument("--body-file", default="")
    submit.add_argument("--output-path", default="")
    submit.add_argument("--run-id", default="")
    submit.add_argument("--event-name", default="")
    submit.add_argument("--session-path", default="")
    submit.add_argument("--controller-status-packet-path", default="")
    submit.add_argument("--controller-aside", default="")

    progress = sub.add_parser("progress-output", help="Update Controller-visible formal role-output progress")
    progress.add_argument("--output-type", required=True, choices=sorted(SUPPORTED_OUTPUT_TYPES))
    progress.add_argument("--role", required=True)
    progress.add_argument("--agent-id", required=True)
    progress.add_argument("--progress", required=True, type=int)
    progress.add_argument("--message", required=True)
    progress.add_argument("--run-id", default="")
    progress.add_argument("--event-name", default="")
    progress.add_argument("--session-path", default="")
    progress.add_argument("--controller-status-packet-path", default="")
    progress.add_argument("--controller-aside", default="")

    controller_boundary = sub.add_parser(
        "submit-controller-boundary-confirmation",
        help="Write the Controller boundary confirmation through the role-output runtime",
    )
    controller_boundary.add_argument("--agent-id", required=True)
    controller_boundary.add_argument("--run-id", default="")
    controller_boundary.add_argument("--action-id", default="")
    controller_boundary.add_argument("--source-action-id", default="")
    controller_boundary.add_argument("--output-path", default="")
    controller_boundary.add_argument("--controller-status-packet-path", default="")

    verify = sub.add_parser("verify-envelope", help="Verify a runtime-generated role-output envelope receipt")
    verify.add_argument("--envelope-file", required=True)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = Path(args.root).resolve()
    if args.command == "prepare-output":
        result = prepare_output_session(
            root,
            output_type=args.output_type,
            role=args.role,
            agent_id=args.agent_id,
            run_id=args.run_id or None,
            body_path=args.body_path or None,
            event_name=args.event_name or None,
            controller_status_packet_path=args.controller_status_packet_path or None,
        )
    elif args.command == "validate-output":
        body = _read_json(_resolve_project_path(root, args.body_file))
        skeleton = build_output_skeleton(root, output_type=args.output_type, role=args.role, run_id=args.run_id or None)
        merged = _deep_merge(skeleton, body)
        spec = _spec_for(args.output_type)
        contract = _contract_by_id(root, spec.contract_id)
        _apply_runtime_fixed_values(
            root,
            merged,
            spec=spec,
            contract=contract,
            role=args.role,
            run_root=_run_paths(root, args.run_id or None)[1],
        )
        result = validate_output_body(
            root,
            output_type=args.output_type,
            role=args.role,
            body=merged,
            run_id=args.run_id or None,
        )
    elif args.command == "submit-output":
        body = json.loads(args.body_json) if args.body_json else None
        result = submit_output(
            root,
            output_type=args.output_type,
            role=args.role,
            agent_id=args.agent_id,
            body=body,
            body_file=args.body_file or None,
            output_path=args.output_path or None,
            run_id=args.run_id or None,
            event_name=args.event_name or None,
            session_path=args.session_path or None,
            controller_status_packet_path=args.controller_status_packet_path or None,
            controller_aside=args.controller_aside or None,
        )
    elif args.command == "progress-output":
        result = update_output_progress(
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
            controller_aside=args.controller_aside or None,
        )
    elif args.command == "submit-controller-boundary-confirmation":
        result = submit_controller_boundary_confirmation(
            root,
            agent_id=args.agent_id,
            run_id=args.run_id or None,
            action_id=args.action_id or None,
            source_action_id=args.source_action_id or None,
            output_path=args.output_path or None,
            controller_status_packet_path=args.controller_status_packet_path or None,
        )
    elif args.command == "verify-envelope":
        envelope = _read_json(_resolve_project_path(root, args.envelope_file))
        result = validate_envelope_runtime_receipt(root, envelope) or {"ok": True, "runtime_receipt": "absent"}
    else:  # pragma: no cover - argparse enforces command choices
        raise RoleOutputRuntimeError(f"unknown command: {args.command}")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0
