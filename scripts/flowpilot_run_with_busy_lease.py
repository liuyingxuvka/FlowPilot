"""Run a bounded command while maintaining a FlowPilot busy lease.

This helper is the concrete form of the FlowPilot protocol rule: long
operations that may outlive the heartbeat stale threshold should be wrapped by
a route/node-scoped busy lease, and that lease must be cleared when the command
finishes.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from types import SimpleNamespace

import flowpilot_busy_lease


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a command with automatic FlowPilot busy-lease start/clear evidence."
    )
    parser.add_argument("--root", default=".", help="Project root containing .flowpilot")
    parser.add_argument("--path", default=".flowpilot/busy_lease.json", help="Lease path; the default resolves to the active run")
    parser.add_argument("--lease-id", default="", help="Optional stable lease id")
    parser.add_argument("--operation", default="bounded FlowPilot command", help="Operation label written into the lease")
    parser.add_argument("--route", default="", help="Route id; defaults to active-run state active_route")
    parser.add_argument("--node", default="", help="Node id; defaults to active-run state active_node")
    parser.add_argument("--max-minutes", type=float, default=30.0, help="Lease expiry window")
    parser.add_argument("--owner", default="flowpilot-controller")
    parser.add_argument("--reason", default="automatic busy-lease command wrapper")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to run after --")
    args = parser.parse_args(argv)
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("command is required after --")
    return args


def _lease_args(args: argparse.Namespace, command: str, clear_reason: str = "") -> SimpleNamespace:
    return SimpleNamespace(
        root=args.root,
        path=args.path,
        lease_id=args.lease_id,
        operation=args.operation or command,
        route=args.route,
        node=args.node,
        max_minutes=args.max_minutes,
        owner=args.owner,
        reason=clear_reason or args.reason,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if not args.lease_id:
        args.lease_id = f"lease-{uuid.uuid4().hex[:12]}"
    command_text = " ".join(args.command)
    start_payload = flowpilot_busy_lease.start(_lease_args(args, command_text))
    returncode = 1
    command_error = None
    try:
        completed = subprocess.run(args.command, check=False)
        returncode = completed.returncode
    except Exception as exc:  # pragma: no cover - diagnostic path
        command_error = repr(exc)
        returncode = 127
    finally:
        clear_payload = flowpilot_busy_lease.clear(
            _lease_args(args, command_text, clear_reason=f"command_exit:{returncode}")
        )

    result = {
        "ok": returncode == 0,
        "returncode": returncode,
        "command": args.command,
        "command_error": command_error,
        "lease_start": start_payload,
        "lease_clear": clear_payload,
    }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"command_exit={returncode} lease={args.lease_id}")
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
