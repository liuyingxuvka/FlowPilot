"""Formal entrypoint for the new black-box FlowPilot runtime.

This entrypoint starts a new FlowPilot run from the native startup intake UI,
then hands all authority to ``ai_project_runtime``. The old router remains
available for diagnostics, but a fresh formal run should enter here.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


ASSETS_ROOT = Path(__file__).resolve().parent
STARTUP_UI = ASSETS_ROOT / "ui" / "startup_intake" / "flowpilot_startup_intake.ps1"
DEFAULT_GOAL = "FlowPilot sealed startup request"
DEFAULT_ACCEPTANCE_CONTRACT = (
    "Complete only when the current-run ledger has sealed startup intake, "
    "an active materialized route tree, accepted route nodes, matching "
    "FlowGuard evidence, independent review, PM disposition, current "
    "validation evidence, a clean final route-wide gate ledger, and final "
    "backward closure."
)
HOST_KIND_HELP = (
    "Allowed values: live=real Codex/multi-agent/background host, "
    "fake=deterministic rehearsal wrapper, dry_run=no real agent. "
    "Do not invent values such as codex_subagent."
)

try:  # pragma: no cover - direct script fallback.
    from ai_project_runtime import cockpit, fake_e2e, host, router, run_shell, runtime
except ImportError:  # pragma: no cover
    sys.path.insert(0, str(ASSETS_ROOT))
    from ai_project_runtime import cockpit, fake_e2e, host, router, run_shell, runtime  # type: ignore


def _print(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True) + "\n", end="")


def startup_ui_command(root: Path, run_id: str, *, headless_startup_text: str = "") -> tuple[list[str], Path]:
    output_dir = root / ".flowpilot" / "bootstrap" / "startup_intake" / run_id
    command = [
        "powershell",
        "-STA",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(STARTUP_UI),
        "-OutputDir",
        str(output_dir),
    ]
    if headless_startup_text:
        command.extend(["-HeadlessConfirmText", headless_startup_text])
    return command, output_dir


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise runtime.BlackBoxRuntimeError(f"expected JSON object: {path}")
    return payload


def _result_path_from_process(completed: subprocess.CompletedProcess[str], output_dir: Path) -> Path:
    lines = [line.strip() for line in (completed.stdout or "").splitlines() if line.strip()]
    if lines:
        return Path(lines[-1]).resolve()
    return (output_dir / "startup_intake_result.json").resolve()


def _run_startup_ui(root: Path, run_id: str, *, headless_startup_text: str = "") -> Path:
    command, output_dir = startup_ui_command(root, run_id, headless_startup_text=headless_startup_text)
    completed = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise runtime.BlackBoxRuntimeError(
            "startup UI failed: "
            + (completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}")
        )
    result_path = _result_path_from_process(completed, output_dir)
    if not result_path.exists():
        raise runtime.BlackBoxRuntimeError(f"startup UI did not write result: {result_path}")
    return result_path


def _assert_formal_interactive_result(result_path: Path) -> None:
    result = _read_json(result_path)
    if result.get("status") == "cancelled":
        raise runtime.BlackBoxRuntimeError("startup intake was cancelled")
    if (
        result.get("launch_mode") != "interactive_native"
        or result.get("headless") is not False
        or result.get("formal_startup_allowed") is not True
    ):
        raise runtime.BlackBoxRuntimeError("formal FlowPilot startup requires the native interactive startup UI result")


def _startup_body_ref(ledger: dict[str, Any]) -> dict[str, str]:
    intake = ledger.get("startup_intake") or {}
    run_paths = intake.get("run_paths") if isinstance(intake, dict) else {}
    return {
        "body_path": str((run_paths or {}).get("body", "")),
        "body_hash": str(intake.get("body_hash", "")),
        "visibility": "sealed_pm_only",
    }


def _runtime_state(ledger: dict[str, Any]) -> dict[str, Any]:
    guard = ledger.get("lifecycle_guard")
    if not isinstance(guard, dict):
        guard = runtime.preview_lifecycle_guard(ledger, trigger="runtime_state")
    duty = ledger.get("foreground_duty")
    if not isinstance(duty, dict):
        duty = runtime.preview_foreground_duty(ledger, guard=guard, trigger="runtime_state")
    return {
        "next_action": router.router_next_action(ledger).to_json(),
        "lifecycle_guard": guard,
        "foreground_duty": duty,
        "final_return_preflight": duty.get("final_return_preflight", runtime.final_return_preflight(ledger, guard=guard)),
    }


def _run_until_wait_and_save(
    shell: run_shell.RunShell,
    ledger: dict[str, Any],
    *,
    guard_trigger: str,
    max_steps: int = runtime.RUN_UNTIL_WAIT_MAX_STEPS,
    resume_source: str = "",
) -> dict[str, Any]:
    folded = runtime.run_until_wait(ledger, max_steps=max_steps)
    run_shell.save_run_ledger(shell, ledger, guard_trigger=guard_trigger, resume_source=resume_source)
    return folded


def _bootstrap_new_runtime(shell: run_shell.RunShell) -> dict[str, Any]:
    ledger = run_shell.load_run_ledger(shell)
    ledger["recursive_route_execution_required"] = True
    ledger["high_standard_control_flow_required"] = True
    if not ledger.get("contract_frozen"):
        runtime.freeze_contract(ledger)
    if not ledger.get("route_drafts"):
        runtime.draft_route(
            ledger,
            "New FlowPilot black-box route from sealed startup intake",
            [
                "Read the sealed startup intake as the authorized work request.",
                "Plan and execute the route with dynamic responsibility leases.",
                "Run FlowGuard for the modeled target before acceptance.",
                "Review evidence independently and close by backward replay.",
            ],
            reason="fresh_new_flowpilot_start",
        )
    if ledger.get("active_route_version") is None:
        runtime.create_route(
            ledger,
            "New FlowPilot black-box route from sealed startup intake",
            [
                "Read sealed startup intake",
                "Plan route and issue work packets",
                "Run FlowGuard target checks",
                "Review and close",
            ],
        )
    active_version = ledger.get("active_route_version")
    active_packets = [
        packet
        for packet in ledger.get("packets", {}).values()
        if packet["envelope"]["route_version"] == active_version
    ]
    if not active_packets:
        runtime.ensure_preplanning_gate_packet(ledger)
    runtime.run_until_wait(ledger)
    run_shell.save_run_ledger(shell, ledger)
    return ledger


def start_run(
    root: Path,
    *,
    run_id: str | None = None,
    headless_startup_text: str = "",
    require_formal_ui: bool = True,
) -> dict[str, Any]:
    root = Path(root).resolve()
    shell = run_shell.create_run_shell(root, DEFAULT_GOAL, DEFAULT_ACCEPTANCE_CONTRACT, run_id=run_id)
    result_path = _run_startup_ui(root, shell.run_id, headless_startup_text=headless_startup_text)
    if require_formal_ui:
        _assert_formal_interactive_result(result_path)
    startup_record = run_shell.record_startup_intake_result(shell, result_path)
    ledger = _bootstrap_new_runtime(shell)
    return {
        "ok": True,
        "mode": "formal" if require_formal_ui else "rehearsal",
        "run": shell.to_json(),
        "startup_intake": {
            "status": startup_record["status"],
            "body_hash": startup_record["body_hash"],
            "controller_may_read_body": startup_record["controller_may_read_body"],
            "body_text_included": startup_record["body_text_included"],
        },
        **_runtime_state(ledger),
        "status": cockpit.render_status(ledger),
    }


def _first_active_packet(ledger: dict[str, Any]) -> str:
    active_version = ledger.get("active_route_version")
    for packet_id, packet in ledger.get("packets", {}).items():
        if packet["envelope"]["route_version"] == active_version and packet["status"] != "accepted":
            return packet_id
    raise runtime.BlackBoxRuntimeError("no active packet found")


def _packet_by_kind(ledger: dict[str, Any], packet_kind: str) -> str:
    for packet_id, packet in ledger.get("packets", {}).items():
        if packet["envelope"].get("packet_kind", "task") == packet_kind and packet["status"] == "open":
            return packet_id
    raise runtime.BlackBoxRuntimeError(f"no open {packet_kind} packet found")


def lease_agent(root: Path, *, packet_id: str, responsibility: str, agent_id: str, host_kind: str) -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    lease_id = host.lease_responsibility(
        ledger,
        responsibility,
        agent_id=agent_id,
        host_kind=host_kind,
        packet_id=packet_id,
        scope="current_run",
    )
    runtime.assign_packet(ledger, packet_id, lease_id)
    run_shell.save_run_ledger(shell, ledger, guard_trigger="lease_agent")
    return {
        "ok": True,
        "lease_id": lease_id,
        **_runtime_state(ledger),
    }


def ack(root: Path, *, lease_id: str, packet_id: str) -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    runtime.ack_lease(ledger, lease_id, packet_id)
    run_shell.save_run_ledger(shell, ledger, guard_trigger="ack")
    return {"ok": True, **_runtime_state(ledger)}


def progress(root: Path, *, lease_id: str, packet_id: str, status: str) -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    runtime.record_progress(ledger, lease_id, packet_id, status)
    run_shell.save_run_ledger(shell, ledger, guard_trigger="progress")
    return {"ok": True, **_runtime_state(ledger)}


def submit_result(root: Path, *, lease_id: str, packet_id: str, body: str) -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    result_id = host.submit_host_result(ledger, lease_id, packet_id, body)
    folded = _run_until_wait_and_save(shell, ledger, guard_trigger="submit_result")
    return {
        "ok": True,
        "result_id": result_id,
        "run_until_wait": folded,
        **_runtime_state(ledger),
    }


def run_fake_e2e(root: Path, *, run_id: str | None = None, startup_text: str) -> dict[str, Any]:
    return fake_e2e.run_fake_e2e(root, run_id=run_id, startup_text=startup_text, start_run=start_run)


def status(root: Path) -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    return {
        "ok": True,
        "run": shell.to_json(),
        **_runtime_state(ledger),
        "status": cockpit.render_status(ledger),
    }


def patrol(root: Path, *, sleep_seconds: int = 0) -> dict[str, Any]:
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    folded = _run_until_wait_and_save(shell, ledger, guard_trigger="patrol")
    return {
        "ok": True,
        "run": shell.to_json(),
        "run_until_wait": folded,
        **_runtime_state(ledger),
        "status": cockpit.render_status(ledger),
    }


def resume(root: Path, *, reason: str = "manual_resume") -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    runtime.record_resume_request(ledger, reason)
    runtime.reconcile_resume_request(ledger, resume_source=reason)
    folded = _run_until_wait_and_save(shell, ledger, guard_trigger="resume", resume_source=reason)
    return {
        "ok": True,
        "run": shell.to_json(),
        "run_until_wait": folded,
        **_runtime_state(ledger),
        "status": cockpit.render_status(ledger),
    }


def final_preflight(root: Path) -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    run_shell.save_run_ledger(shell, ledger, guard_trigger="final_preflight")
    state = _runtime_state(ledger)
    preflight = state["final_return_preflight"]
    payload = {
        "ok": bool(preflight.get("allowed") is True),
        "run": shell.to_json(),
        **state,
    }
    if payload["ok"] is not True:
        payload["error"] = "final foreground return is not allowed"
    return payload


def repair_accepted_packet(root: Path, *, packet_id: str) -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    repair = runtime.repair_accepted_packet_assignment(ledger, packet_id)
    folded = _run_until_wait_and_save(shell, ledger, guard_trigger="repair_accepted_packet")
    return {
        "ok": True,
        "repair": repair,
        "run_until_wait": folded,
        **_runtime_state(ledger),
        "status": cockpit.render_status(ledger),
    }


def run_until_wait(root: Path, *, max_steps: int = runtime.RUN_UNTIL_WAIT_MAX_STEPS) -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    folded = _run_until_wait_and_save(shell, ledger, guard_trigger="run_until_wait", max_steps=max_steps)
    return {
        "ok": True,
        "run": shell.to_json(),
        "run_until_wait": folded,
        **_runtime_state(ledger),
        "status": cockpit.render_status(ledger),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="Start a fresh new FlowPilot run through the native startup UI")
    start.add_argument("--run-id", default=None)
    start.add_argument("--headless-startup-text", default="", help="Test/rehearsal only; formal starts require the native UI")

    fake = sub.add_parser("run-fake-e2e", help="Run a deterministic fake-host end-to-end rehearsal")
    fake.add_argument("--run-id", default=None)
    fake.add_argument("--startup-text", required=True)

    run_wait = sub.add_parser("run-until-wait", help="Fold safe black-box mechanics until the next foreground boundary")
    run_wait.add_argument("--max-steps", type=int, default=runtime.RUN_UNTIL_WAIT_MAX_STEPS)
    sub.add_parser("status", help="Render public status for the current new FlowPilot run")
    patrol_parser = sub.add_parser("patrol", help="Refresh lifecycle guard and foreground duty status for the current run")
    patrol_parser.add_argument("--sleep-seconds", type=int, default=0, help="Optional foreground duty delay before refreshing")
    sub.add_parser("final-preflight", help="Fail unless current foreground duty allows terminal return")
    resume_parser = sub.add_parser("resume", help="Record manual resume and rehydrate lifecycle guard status")
    resume_parser.add_argument("--reason", default="manual_resume")

    lease = sub.add_parser("lease-agent", help="Record a dynamic responsibility lease and assign a packet")
    lease.add_argument("--packet-id", required=True)
    lease.add_argument("--responsibility", required=True)
    lease.add_argument("--agent-id", required=True)
    lease.add_argument(
        "--host-kind",
        default="live",
        choices=sorted(host.HOST_KINDS),
        metavar="{live,fake,dry_run}",
        help=HOST_KIND_HELP,
    )

    ack_parser = sub.add_parser("ack", help="Record lease ACK for a packet")
    ack_parser.add_argument("--lease-id", required=True)
    ack_parser.add_argument("--packet-id", required=True)

    progress_parser = sub.add_parser("progress", help="Record current-run lease progress without completing the packet")
    progress_parser.add_argument("--lease-id", required=True)
    progress_parser.add_argument("--packet-id", required=True)
    progress_parser.add_argument("--status", required=True)

    submit = sub.add_parser("submit-result", help="Submit a sealed result body for a packet")
    submit.add_argument("--lease-id", required=True)
    submit.add_argument("--packet-id", required=True)
    submit.add_argument("--body", required=True)

    repair_parser = sub.add_parser("repair-accepted-packet", help="Repair accepted packet assignment race state")
    repair_parser.add_argument("--packet-id", required=True)

    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == "start":
            payload = start_run(
                root,
                run_id=args.run_id,
                headless_startup_text=args.headless_startup_text,
                require_formal_ui=not bool(args.headless_startup_text),
            )
        elif args.command == "run-fake-e2e":
            payload = run_fake_e2e(root, run_id=args.run_id, startup_text=args.startup_text)
        elif args.command == "run-until-wait":
            payload = run_until_wait(root, max_steps=args.max_steps)
        elif args.command == "status":
            payload = status(root)
        elif args.command == "patrol":
            payload = patrol(root, sleep_seconds=args.sleep_seconds)
        elif args.command == "final-preflight":
            payload = final_preflight(root)
        elif args.command == "resume":
            payload = resume(root, reason=args.reason)
        elif args.command == "lease-agent":
            payload = lease_agent(
                root,
                packet_id=args.packet_id,
                responsibility=args.responsibility,
                agent_id=args.agent_id,
                host_kind=args.host_kind,
            )
        elif args.command == "ack":
            payload = ack(root, lease_id=args.lease_id, packet_id=args.packet_id)
        elif args.command == "progress":
            payload = progress(root, lease_id=args.lease_id, packet_id=args.packet_id, status=args.status)
        elif args.command == "submit-result":
            payload = submit_result(root, lease_id=args.lease_id, packet_id=args.packet_id, body=args.body)
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


if __name__ == "__main__":
    raise SystemExit(main())
