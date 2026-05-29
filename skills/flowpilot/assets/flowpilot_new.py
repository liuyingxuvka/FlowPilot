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
from typing import Any


ASSETS_ROOT = Path(__file__).resolve().parent
STARTUP_UI = ASSETS_ROOT / "ui" / "startup_intake" / "flowpilot_startup_intake.ps1"
DEFAULT_GOAL = "FlowPilot sealed startup request"
DEFAULT_ACCEPTANCE_CONTRACT = (
    "Complete only when the current-run ledger has sealed startup intake, "
    "an active route, accepted packet results, matching FlowGuard evidence, "
    "independent review, current validation evidence, and final backward closure."
)
HOST_KIND_HELP = (
    "Allowed values: live=real Codex/multi-agent/background host, "
    "fake=deterministic rehearsal wrapper, dry_run=no real agent. "
    "Do not invent values such as codex_subagent."
)

try:  # pragma: no cover - direct script fallback.
    from ai_project_runtime import cockpit, host, router, run_shell, runtime
except ImportError:  # pragma: no cover
    sys.path.insert(0, str(ASSETS_ROOT))
    from ai_project_runtime import cockpit, host, router, run_shell, runtime  # type: ignore


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


def _bootstrap_new_runtime(shell: run_shell.RunShell) -> dict[str, Any]:
    ledger = run_shell.load_run_ledger(shell)
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
        body = json.dumps(
            {
                "schema_version": "black_box_flowpilot.pm_startup_packet.v1",
                "instruction": "Open the sealed startup body through the current-run packet boundary and plan the project route.",
                "startup_intake_ref": _startup_body_ref(ledger),
                "old_runtime_authority": "forbidden",
            },
            indent=2,
            sort_keys=True,
        )
        runtime.issue_task_packet(
            ledger,
            "pm",
            "Plan and execute the sealed startup request with the new FlowPilot runtime",
            body,
            required_output_type="artifact",
            required_flowguard_target="development_process",
        )
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
        "next_action": router.router_next_action(ledger).to_json(),
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
    run_shell.save_run_ledger(shell, ledger)
    return {"ok": True, "lease_id": lease_id, "next_action": router.router_next_action(ledger).to_json()}


def ack(root: Path, *, lease_id: str, packet_id: str) -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    runtime.ack_lease(ledger, lease_id, packet_id)
    run_shell.save_run_ledger(shell, ledger)
    return {"ok": True, "next_action": router.router_next_action(ledger).to_json()}


def submit_result(root: Path, *, lease_id: str, packet_id: str, body: str) -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    result_id = host.submit_host_result(ledger, lease_id, packet_id, body)
    run_shell.save_run_ledger(shell, ledger)
    return {"ok": True, "result_id": result_id, "next_action": router.router_next_action(ledger).to_json()}


def run_fake_e2e(root: Path, *, run_id: str | None, startup_text: str) -> dict[str, Any]:
    start_result = start_run(
        root,
        run_id=run_id,
        headless_startup_text=startup_text,
        require_formal_ui=False,
    )
    shell = run_shell.load_run_shell(root, run_id=start_result["run"]["run_id"])
    ledger = run_shell.load_run_ledger(shell)

    def complete_open_packet(packet_id: str, *, agent_id: str, body: str) -> tuple[str, str]:
        packet = ledger["packets"][packet_id]
        responsibility = packet["envelope"]["responsibility"]
        lease_id = host.lease_responsibility(
            ledger,
            responsibility,
            host_kind="fake",
            agent_id=agent_id,
            packet_id=packet_id,
            scope="e2e",
        )
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)
        result_id = host.submit_host_result(ledger, lease_id, packet_id, body)
        return lease_id, result_id

    packet_id = _first_active_packet(ledger)
    lease_id, result_id = complete_open_packet(
        packet_id,
        agent_id="fake-pm",
        body="SEALED_RESULT_BODY: fake PM completed the new FlowPilot route rehearsal.",
    )
    flowguard_packet_id = _packet_by_kind(ledger, "flowguard_check")
    flowguard_lease_id, flowguard_result_id = complete_open_packet(
        flowguard_packet_id,
        agent_id="fake-flowguard",
        body="SEALED_RESULT_BODY: fake FlowGuard evidence passed for the PM result.",
    )
    review_packet_id = _packet_by_kind(ledger, "review")
    reviewer_lease_id, review_result_id = complete_open_packet(
        review_packet_id,
        agent_id="fake-reviewer",
        body="SEALED_RESULT_BODY: fake reviewer accepted the PM result and FlowGuard evidence.",
    )
    validation_packet_id = _packet_by_kind(ledger, "validation")
    validation_lease_id, validation_result_id = complete_open_packet(
        validation_packet_id,
        agent_id="fake-validator",
        body="SEALED_RESULT_BODY: fake validation evidence is current.",
    )
    closure_packet_id = _packet_by_kind(ledger, "closure")
    closure_lease_id, closure_result_id = complete_open_packet(
        closure_packet_id,
        agent_id="fake-closure",
        body="SEALED_RESULT_BODY: fake closure officer confirmed backward chain.",
    )
    closure = ledger["closure"]
    order_id = next(iter(ledger["flowguard_work_orders"]))
    review_id = next(iter(ledger["reviews"]))
    run_shell.save_run_ledger(shell, ledger)
    return {
        "ok": closure["decision"] == "complete",
        "mode": "rehearsal",
        "run": shell.to_json(),
        "packet_id": packet_id,
        "lease_id": lease_id,
        "result_id": result_id,
        "flowguard_packet_id": flowguard_packet_id,
        "flowguard_lease_id": flowguard_lease_id,
        "flowguard_result_id": flowguard_result_id,
        "review_packet_id": review_packet_id,
        "reviewer_lease_id": reviewer_lease_id,
        "review_result_id": review_result_id,
        "validation_packet_id": validation_packet_id,
        "validation_lease_id": validation_lease_id,
        "validation_result_id": validation_result_id,
        "closure_packet_id": closure_packet_id,
        "closure_lease_id": closure_lease_id,
        "closure_result_id": closure_result_id,
        "order_id": order_id,
        "review_id": review_id,
        "closure": closure,
        "next_action": router.router_next_action(ledger).to_json(),
        "status": cockpit.render_status(ledger),
    }


def status(root: Path) -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    return {"ok": True, "run": shell.to_json(), "next_action": router.router_next_action(ledger).to_json(), "status": cockpit.render_status(ledger)}


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

    sub.add_parser("status", help="Render public status for the current new FlowPilot run")

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

    submit = sub.add_parser("submit-result", help="Submit a sealed result body for a packet")
    submit.add_argument("--lease-id", required=True)
    submit.add_argument("--packet-id", required=True)
    submit.add_argument("--body", required=True)

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
        elif args.command == "status":
            payload = status(root)
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
        elif args.command == "submit-result":
            payload = submit_result(root, lease_id=args.lease_id, packet_id=args.packet_id, body=args.body)
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
