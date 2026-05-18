"""Router skeleton owner helpers for flowpilot_router_cli.

These helpers were moved out of ``flowpilot_router.py`` during the final
StructureMesh skeleton cleanup. The module is bound to the router skeleton
before execution so cross-owner transitional lookups stay explicit.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Iterable

import card_runtime
import flowpilot_runtime_closure
import flowpilot_user_flow_diagram
import packet_runtime
import role_output_runtime
import flowpilot_router_action_handlers
import flowpilot_router_action_providers
import flowpilot_router_card_returns
import flowpilot_router_daemon_runtime
import flowpilot_router_event_dispatcher
import flowpilot_router_events
import flowpilot_router_resume
import flowpilot_router_startup_flow
from flowpilot_prompt_store import PromptStoreError, card_manifest_entry, load_card_manifest_from_run
from flowpilot_router_errors import RouterError, RouterLedgerCorruptionError, RouterLedgerWriteInProgress
from flowpilot_router_protocol_catalog import *

_DEFAULT_SENTINEL = object()
_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router skeleton is not bound")
    return _BOUND_ROUTER


OWNER_MODULE = 'flowpilot_router_cli'

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FlowPilot prompt-isolated router.")
    parser.add_argument("--root", default=".", help="Project root containing .flowpilot")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    sub = parser.add_subparsers(dest="command", required=True)
    start_parser = sub.add_parser("start", help="Start a fresh formal FlowPilot invocation")
    start_parser.add_argument("--max-steps", type=int, default=50)
    start_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    next_parser = sub.add_parser("next", help="Return the next router-authorized action for an existing run")
    next_parser.add_argument("--new-invocation", action="store_true", help="Start a fresh formal FlowPilot invocation")
    next_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    run_wait_parser = sub.add_parser("run-until-wait", help="Apply safe internal router actions and return the next wait-boundary action")
    run_wait_parser.add_argument("--max-steps", type=int, default=50)
    run_wait_parser.add_argument("--new-invocation", action="store_true", help="Start a fresh formal FlowPilot invocation")
    run_wait_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    daemon_parser = sub.add_parser("daemon", help="Run the persistent Router daemon loop for the current run")
    daemon_parser.add_argument("--max-ticks", type=int, default=None, help="Stop after this many one-second daemon ticks")
    daemon_parser.add_argument("--observe-only", action="store_true", help="Write daemon status without advancing router state")
    daemon_parser.add_argument("--replace-stale-lock", action="store_true", help="Replace a stale daemon lock explicitly")
    daemon_parser.add_argument("--release-lock-on-exit", action="store_true", help="Release the daemon lock when a bounded daemon run exits")
    daemon_parser.add_argument("--run-id", default="", help="Bind daemon to this run id instead of the current focus run")
    daemon_parser.add_argument("--run-root", default="", help="Bind daemon to this run root instead of the current focus run")
    daemon_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    daemon_stop_parser = sub.add_parser("daemon-stop", help="Stop or release the current run's Router daemon lock")
    daemon_stop_parser.add_argument("--reason", default="manual_stop")
    daemon_stop_parser.add_argument("--run-id", default="", help="Stop this run id instead of the current focus run")
    daemon_stop_parser.add_argument("--run-root", default="", help="Stop this run root instead of the current focus run")
    daemon_stop_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    standby_parser = sub.add_parser("controller-standby", help="Keep foreground Controller waiting on Router daemon status and action ledger")
    standby_parser.add_argument("--max-seconds", type=float, default=FOREGROUND_CONTROLLER_STANDBY_DEFAULT_MAX_SECONDS)
    standby_parser.add_argument("--poll-seconds", type=float, default=FOREGROUND_CONTROLLER_STANDBY_POLL_SECONDS)
    standby_parser.add_argument("--bounded-diagnostic", action="store_true", help="Return timeout_still_waiting at max-seconds for diagnostics/tests instead of continuing standby")
    standby_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    patrol_parser = sub.add_parser("controller-patrol-timer", help="Wait, read the existing Router daemon monitor, and return the next Controller patrol instruction")
    patrol_parser.add_argument("--seconds", type=float, default=CONTROLLER_PATROL_TIMER_DEFAULT_SECONDS)
    patrol_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    receipt_parser = sub.add_parser("controller-receipt", help="Record a Controller action ledger receipt")
    receipt_parser.add_argument("--action-id", required=True)
    receipt_parser.add_argument("--status", required=True, choices=sorted(CONTROLLER_RECEIPT_STATUSES))
    receipt_parser.add_argument("--payload-json", default="")
    receipt_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    apply_parser = sub.add_parser("apply", help="Apply a pending router action")
    apply_parser.add_argument("--action-type", required=True)
    apply_parser.add_argument("--payload-json", default="")
    apply_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    event_parser = sub.add_parser("record-event", help="Record a PM/reviewer/worker external event")
    event_parser.add_argument("--event", required=True)
    event_parser.add_argument("--payload-json", default="")
    event_parser.add_argument("--envelope-path", default="", help="Project-local controller-visible event envelope path")
    event_parser.add_argument("--envelope-hash", default="", help="Expected sha256 for --envelope-path")
    event_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    envelope_parser = sub.add_parser("role-output-envelope", help="Write a role output body and return a controller-visible envelope")
    envelope_parser.add_argument("--output-path", required=True)
    envelope_parser.add_argument("--body-json", default="")
    envelope_parser.add_argument("--body-file", default="")
    envelope_parser.add_argument("--path-key", default="report_path")
    envelope_parser.add_argument("--hash-key", default="report_hash")
    envelope_parser.add_argument("--event-name", default="")
    envelope_parser.add_argument("--from-role", default="")
    envelope_parser.add_argument("--to-role", default="controller")
    envelope_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    validate_parser = sub.add_parser("validate-artifact", help="Validate a FlowPilot artifact before or during record-event")
    validate_parser.add_argument("--type", required=True, choices=["node_acceptance_plan", "final_route_wide_gate_ledger", "self_interrogation_record", "packet_envelope", "result_envelope", "role_output_envelope", "gate_decision"])
    validate_parser.add_argument("--path", required=True)
    validate_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    reconcile_parser = sub.add_parser("reconcile-run", help="Rebuild derived indexes and live-run views for the current run")
    reconcile_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    state_parser = sub.add_parser("state", help="Print bootstrap and current run router state")
    state_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    return parser.parse_args(argv)

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = Path(args.root).resolve()
    try:
        if args.command == "start":
            result = _run_foreground_with_runtime_writer_settlement(
                lambda: run_until_wait(root, max_steps=int(args.max_steps), new_invocation=True),
                command_name=args.command,
            )
        elif args.command == "next":
            result = _run_foreground_with_runtime_writer_settlement(
                lambda: next_action(root, new_invocation=bool(getattr(args, "new_invocation", False))),
                command_name=args.command,
            )
        elif args.command == "run-until-wait":
            result = _run_foreground_with_runtime_writer_settlement(
                lambda: run_until_wait(
                    root,
                    max_steps=int(args.max_steps),
                    new_invocation=bool(getattr(args, "new_invocation", False)),
                ),
                command_name=args.command,
            )
        elif args.command == "daemon":
            result = run_router_daemon(
                root,
                max_ticks=getattr(args, "max_ticks", None),
                observe_only=bool(getattr(args, "observe_only", False)),
                replace_stale_lock=bool(getattr(args, "replace_stale_lock", False)),
                release_lock_on_exit=bool(getattr(args, "release_lock_on_exit", False)),
                run_id=getattr(args, "run_id", "") or None,
                run_root=getattr(args, "run_root", "") or None,
            )
        elif args.command == "daemon-stop":
            result = stop_router_daemon(
                root,
                reason=str(getattr(args, "reason", "manual_stop") or "manual_stop"),
                run_id=getattr(args, "run_id", "") or None,
                run_root=getattr(args, "run_root", "") or None,
            )
        elif args.command == "controller-standby":
            result = _run_foreground_with_runtime_writer_settlement(
                lambda: foreground_controller_standby(
                    root,
                    max_seconds=float(getattr(args, "max_seconds", FOREGROUND_CONTROLLER_STANDBY_DEFAULT_MAX_SECONDS)),
                    poll_seconds=float(getattr(args, "poll_seconds", FOREGROUND_CONTROLLER_STANDBY_POLL_SECONDS)),
                    bounded_diagnostic=bool(getattr(args, "bounded_diagnostic", False)),
                ),
                command_name=args.command,
            )
        elif args.command == "controller-patrol-timer":
            result = _run_foreground_with_runtime_writer_settlement(
                lambda: controller_patrol_timer(
                    root,
                    seconds=float(getattr(args, "seconds", CONTROLLER_PATROL_TIMER_DEFAULT_SECONDS)),
                ),
                command_name=args.command,
            )
        elif args.command == "controller-receipt":
            payload = json.loads(args.payload_json) if args.payload_json else {}
            result = record_controller_action_receipt(root, action_id=args.action_id, status=args.status, payload=payload)
        elif args.command == "apply":
            payload = json.loads(args.payload_json) if args.payload_json else {}
            result = apply_action(root, args.action_type, payload)
        elif args.command == "record-event":
            payload = json.loads(args.payload_json) if args.payload_json else {}
            result = record_external_event(
                root,
                args.event,
                payload,
                envelope_path=args.envelope_path or None,
                envelope_hash=args.envelope_hash or None,
            )
        elif args.command == "role-output-envelope":
            body = json.loads(args.body_json) if args.body_json else None
            result = write_role_output_envelope(
                root,
                output_path=args.output_path,
                body=body,
                body_file=args.body_file or None,
                path_key=args.path_key,
                hash_key=args.hash_key,
                event_name=args.event_name or None,
                from_role=args.from_role or None,
                to_role=args.to_role,
            )
        elif args.command == "validate-artifact":
            result = validate_artifact(root, args.type, args.path)
        elif args.command == "reconcile-run":
            result = reconcile_current_run(root)
        elif args.command == "state":
            def _state_command() -> dict[str, Any]:
                bootstrap = load_bootstrap_state(root, create_if_missing=False)
                run_state, run_root = load_run_state(root, bootstrap)
                active_ui_task_catalog = (
                    _active_ui_task_catalog(root, run_root, run_state)
                    if run_state is not None and run_root is not None
                    else {"schema_version": "flowpilot.active_ui_task_catalog.v1", "active_tasks": []}
                )
                return {
                    "bootstrap": bootstrap,
                    "run_root": str(run_root) if run_root else None,
                    "run_state": run_state,
                    "active_ui_task_catalog": active_ui_task_catalog,
                    "router_daemon_status": read_json_if_exists(_router_daemon_status_path(run_root)) if run_root else {},
                    "controller_action_ledger": read_json_if_exists(_controller_action_ledger_path(run_root)) if run_root else {},
                }

            result = _run_foreground_with_runtime_writer_settlement(_state_command, command_name=args.command)
        else:
            raise RouterError(f"unknown command: {args.command}")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        error = {"ok": False, "error": str(exc)}
        control_blocker = getattr(exc, "control_blocker", None)
        if isinstance(control_blocker, dict):
            error["control_blocker"] = control_blocker
            error["blocker_artifact_path"] = control_blocker.get("blocker_artifact_path")
            error["handling_lane"] = control_blocker.get("handling_lane")
            error["controller_instruction"] = control_blocker.get("controller_instruction")
            if isinstance(control_blocker.get("skill_observation_reminder"), dict):
                error["skill_observation_reminder"] = control_blocker["skill_observation_reminder"]
        if "skill_observation_reminder" not in error and args.command in {"apply", "record-event"}:
            error["skill_observation_reminder"] = _skill_observation_reminder(
                str(exc),
                event=getattr(args, "event", None),
                action_type=getattr(args, "action_type", None),
            )
        print(json.dumps(error, indent=2, sort_keys=True))
        return 2

_LOCAL_NAMES = set(globals())
