"""CLI parser and dispatcher for the current FlowPilot entrypoint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from flowpilot_new_role_commands import (
    ack,
    dispatch_current_role,
    open_packet,
    open_result,
    role_handoff_payload,
)
from flowpilot_new_run_commands import (
    cancel_run,
    final_preflight,
    patrol,
    progress,
    repair_accepted_packet,
    resolve_stopped_blocker,
    resume,
    run_until_wait,
    status,
    stop_run,
    submit_result,
)
from flowpilot_new_shared import HOST_KIND_HELP, _print, host, runtime, start_run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="Start a fresh new FlowPilot run through the native startup UI")
    start.add_argument("--run-id", default=None)

    run_wait = sub.add_parser("run-until-wait", help="Fold safe black-box mechanics until the next foreground boundary")
    run_wait.add_argument("--max-steps", type=int, default=runtime.RUN_UNTIL_WAIT_MAX_STEPS)
    status_parser = sub.add_parser("status", help="Render public status for the current new FlowPilot run")
    status_parser.add_argument("--full", action="store_true", help="Render the full body-free debug projection instead of compact status")
    patrol_parser = sub.add_parser("patrol", help="Refresh lifecycle guard and foreground duty status for the current run")
    patrol_parser.add_argument("--sleep-seconds", type=int, default=0, help="Optional foreground duty delay before refreshing")
    sub.add_parser("final-preflight", help="Fail unless current foreground duty allows terminal return")
    resume_parser = sub.add_parser("resume", help="Record manual resume and rehydrate lifecycle guard status")
    resume_parser.add_argument("--reason", default="manual_resume")
    stopped_parser = sub.add_parser("resolve-stopped-blocker", help="Resolve a PM-stopped semantic blocker explicitly")
    stopped_parser.add_argument("--blocker-id", required=True)
    stopped_parser.add_argument(
        "--resolution",
        required=True,
        choices=["reissue_pm_repair_decision", "reattach_required_recheck", "stop_run", "cancel_run"],
    )
    stopped_parser.add_argument("--reason", default="")
    stopped_parser.add_argument(
        "--user-requested",
        action="store_true",
        help="Required when reissuing or reattaching after stop_for_user.",
    )

    dispatch = sub.add_parser("dispatch-current-role", help="Dispatch the current packet to its authorized role")
    dispatch.add_argument("--packet-id", required=True)
    dispatch.add_argument("--responsibility", required=True)
    dispatch.add_argument("--agent-id", default="")
    dispatch.add_argument(
        "--host-kind",
        default="live",
        choices=sorted(host.HOST_KINDS),
        metavar="{live,fake,dry_run}",
        help=HOST_KIND_HELP,
    )

    ack_parser = sub.add_parser("ack", help="Record lease ACK for a packet")
    ack_parser.add_argument("--lease-id", required=True)
    ack_parser.add_argument("--packet-id", required=True)

    handoff_parser = sub.add_parser("role-handoff", help="Render the Controller-safe handoff for an assigned role packet")
    handoff_parser.add_argument("--lease-id", required=True)
    handoff_parser.add_argument("--packet-id", required=True)

    open_parser = sub.add_parser("open-packet", help="Open the sealed body for the assigned ACKed role packet")
    open_parser.add_argument("--lease-id", required=True)
    open_parser.add_argument("--packet-id", required=True)

    open_result_parser = sub.add_parser("open-result", help="Open an authorized sealed result body for the assigned ACKed role packet")
    open_result_parser.add_argument("--lease-id", required=True)
    open_result_parser.add_argument("--packet-id", required=True)
    open_result_parser.add_argument("--result-id", required=True)

    progress_parser = sub.add_parser("progress", help="Record current-run lease progress without completing the packet")
    progress_parser.add_argument("--lease-id", required=True)
    progress_parser.add_argument("--packet-id", required=True)
    progress_parser.add_argument("--status", required=True)

    stop_parser = sub.add_parser("stop", help="Stop the current run as an explicit terminal lifecycle event")
    stop_parser.add_argument("--reason", default="manual_stop")
    cancel_parser = sub.add_parser("cancel", help="Cancel the current run as an explicit terminal lifecycle event")
    cancel_parser.add_argument("--reason", default="manual_cancel")

    submit = sub.add_parser("submit-result", help="Submit a sealed result body for a packet")
    submit.add_argument("--lease-id", required=True)
    submit.add_argument("--packet-id", required=True)
    submit.add_argument("--body", default=None)
    submit.add_argument("--body-file", type=Path, default=None)

    repair_parser = sub.add_parser("repair-accepted-packet", help="Repair accepted packet assignment race state")
    repair_parser.add_argument("--packet-id", required=True)

    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == "start":
            payload = start_run(
                root,
                run_id=args.run_id,
                require_formal_ui=True,
            )
        elif args.command == "run-until-wait":
            payload = run_until_wait(root, max_steps=args.max_steps)
        elif args.command == "status":
            payload = status(root, full=args.full)
        elif args.command == "patrol":
            payload = patrol(root, sleep_seconds=args.sleep_seconds)
        elif args.command == "final-preflight":
            payload = final_preflight(root)
        elif args.command == "resume":
            payload = resume(root, reason=args.reason)
        elif args.command == "resolve-stopped-blocker":
            payload = resolve_stopped_blocker(
                root,
                blocker_id=args.blocker_id,
                resolution=args.resolution,
                reason=args.reason,
                user_requested=args.user_requested,
            )
        elif args.command == "dispatch-current-role":
            payload = dispatch_current_role(
                root,
                packet_id=args.packet_id,
                responsibility=args.responsibility,
                host_kind=args.host_kind,
                agent_id=args.agent_id,
            )
        elif args.command == "ack":
            payload = ack(root, lease_id=args.lease_id, packet_id=args.packet_id)
        elif args.command == "role-handoff":
            payload = role_handoff_payload(root, lease_id=args.lease_id, packet_id=args.packet_id)
        elif args.command == "open-packet":
            payload = open_packet(root, lease_id=args.lease_id, packet_id=args.packet_id)
        elif args.command == "open-result":
            payload = open_result(root, lease_id=args.lease_id, packet_id=args.packet_id, result_id=args.result_id)
        elif args.command == "progress":
            payload = progress(root, lease_id=args.lease_id, packet_id=args.packet_id, status=args.status)
        elif args.command == "stop":
            payload = stop_run(root, reason=args.reason)
        elif args.command == "cancel":
            payload = cancel_run(root, reason=args.reason)
        elif args.command == "submit-result":
            payload = submit_result(
                root,
                lease_id=args.lease_id,
                packet_id=args.packet_id,
                body=args.body,
                body_file=args.body_file,
            )
        elif args.command == "repair-accepted-packet":
            payload = repair_accepted_packet(root, packet_id=args.packet_id)
        else:  # pragma: no cover
            raise runtime.BlackBoxRuntimeError(f"unsupported command: {args.command}")
    except runtime.BlackBoxRuntimeError as exc:
        payload = {"ok": False, "error": str(exc)}
        if args.json:
            _print(payload)
        else:
            print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        _print(payload)
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok", False) else 1
