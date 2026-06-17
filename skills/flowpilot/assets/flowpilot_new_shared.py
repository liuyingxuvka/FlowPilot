"""Formal entrypoint for the new black-box FlowPilot runtime.

This entrypoint starts a new FlowPilot run from the native startup intake UI,
then hands all authority to ``flowpilot_core_runtime``.
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
    "Allowed values: live=real host-supported role surface, "
    "fake=deterministic rehearsal wrapper, dry_run=no real agent. "
    "Do not invent values outside this menu."
)

if str(ASSETS_ROOT) not in sys.path:
    sys.path.insert(0, str(ASSETS_ROOT))
import flowpilot_runtime_self_check
from flowpilot_core_runtime import cockpit, fake_e2e, host, packets, role_handoff, router, run_shell, runtime

ENTRYPOINT_PATH = ASSETS_ROOT / "flowpilot_new.py"


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
    if result.get("status") not in {"confirmed", "blocked"}:
        raise runtime.BlackBoxRuntimeError("startup intake returned unsupported status")
    if (
        result.get("launch_mode") != "interactive_native"
        or result.get("headless") is not False
        or result.get("formal_startup_allowed") is not True
    ):
        raise runtime.BlackBoxRuntimeError("formal FlowPilot startup requires the native interactive startup UI result")
    answers = result.get("startup_answers") if isinstance(result.get("startup_answers"), dict) else {}
    if result.get("status") == "confirmed" and answers.get(runtime.BACKGROUND_COLLABORATION_ACK_FIELD) is not True:
        raise runtime.BlackBoxRuntimeError(runtime.BACKGROUND_COLLABORATION_REQUIRED_MESSAGE)


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
        "progress_fraction": runtime.current_progress_fraction(ledger),
        "lifecycle_guard": guard,
        "foreground_duty": duty,
        "final_return_preflight": duty.get("final_return_preflight", runtime.final_return_preflight(ledger, guard=guard)),
    }


def _status_projection(ledger: dict[str, Any], *, full: bool = False) -> dict[str, Any]:
    if full:
        return cockpit.render_status(ledger, compact=False)
    return runtime.render_compact_console(ledger)


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


def _record_runtime_self_check_receipt(shell: run_shell.RunShell) -> dict[str, Any]:
    receipt = flowpilot_runtime_self_check.write_runtime_self_check_receipt(
        shell.run_root,
        assets_root=ASSETS_ROOT,
    )
    ledger = run_shell.load_run_ledger(shell)
    ledger["flowpilot_runtime_self_check"] = receipt
    runtime._event(
        ledger,
        "flowpilot_runtime_self_check_recorded",
        ok=receipt.get("ok") is True,
        receipt_path=str(receipt.get("receipt_path") or ""),
    )
    run_shell.save_run_ledger(shell, ledger)
    if receipt.get("ok") is not True:
        raise runtime.BlackBoxRuntimeError(
            "FlowPilot installed runtime self-check failed: "
            + ", ".join(str(item) for item in receipt.get("missing_runtime_assets") or [])
            + (f"; {receipt.get('flowguard_error')}" if receipt.get("flowguard_error") else "")
        )
    return receipt


def start_run(
    root: Path,
    *,
    run_id: str | None = None,
    headless_startup_text: str = "",
    require_formal_ui: bool = True,
) -> dict[str, Any]:
    root = Path(root).resolve()
    shell = run_shell.create_run_shell(root, DEFAULT_GOAL, DEFAULT_ACCEPTANCE_CONTRACT, run_id=run_id)
    runtime_self_check = _record_runtime_self_check_receipt(shell)
    result_path = _run_startup_ui(root, shell.run_id, headless_startup_text=headless_startup_text)
    if require_formal_ui:
        _assert_formal_interactive_result(result_path)
    startup_record = run_shell.record_startup_intake_result(shell, result_path)
    if startup_record["status"] == "blocked":
        ledger = run_shell.load_run_ledger(shell)
        return {
            "ok": False,
            "mode": "formal" if require_formal_ui else "rehearsal",
            "run": shell.to_json(),
            "startup_intake": {
                "status": startup_record["status"],
                "block_reason": startup_record.get("block_reason", "background_collaboration_required"),
                "controller_may_read_body": startup_record["controller_may_read_body"],
                "body_text_included": startup_record["body_text_included"],
            },
            "flowpilot_runtime_self_check": runtime_self_check,
            "error": startup_record.get("block_reason", "background_collaboration_required"),
            **_runtime_state(ledger),
            "status": _status_projection(ledger),
        }
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
        "flowpilot_runtime_self_check": runtime_self_check,
        **_runtime_state(ledger),
        "status": _status_projection(ledger),
    }
