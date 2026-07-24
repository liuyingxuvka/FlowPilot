"""Run lifecycle and status commands for the FlowPilot entrypoint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flowpilot_new_shared import (
    _run_until_wait_and_save,
    _runtime_state,
    _status_projection,
    fake_e2e,
    host,
    run_shell,
    runtime,
    start_run,
    time,
)


def progress(root: Path, *, lease_id: str, packet_id: str, status: str) -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    progress_update = runtime.record_progress(ledger, lease_id, packet_id, status)
    if progress_update["persisted"]:
        run_shell.save_run_ledger(shell, ledger, guard_trigger="progress")
    return {
        "ok": True,
        "coalesced": progress_update["coalesced"],
        "progress_update": progress_update,
        **_runtime_state(ledger),
    }


def stop_run(root: Path, *, reason: str = "manual_stop") -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    terminal = runtime.record_terminal_lifecycle(ledger, "stopped_by_user", reason=reason, actor="controller")
    run_shell.save_run_ledger(shell, ledger, guard_trigger="stop")
    return {
        "ok": True,
        "terminal_lifecycle": terminal,
        "run": shell.to_json(),
        **_runtime_state(ledger),
        "status": _status_projection(ledger),
    }


def cancel_run(root: Path, *, reason: str = "manual_cancel") -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    terminal = runtime.record_terminal_lifecycle(ledger, "cancelled_by_user", reason=reason, actor="controller")
    run_shell.save_run_ledger(shell, ledger, guard_trigger="cancel")
    return {
        "ok": True,
        "terminal_lifecycle": terminal,
        "run": shell.to_json(),
        **_runtime_state(ledger),
        "status": _status_projection(ledger),
    }


def submit_result(
    root: Path,
    *,
    lease_id: str,
    packet_id: str,
    body: str | None = None,
    body_file: Path | None = None,
) -> dict[str, Any]:
    resolved_body = _resolve_submit_result_body(body=body, body_file=body_file)
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    result_id = host.submit_host_result(ledger, lease_id, packet_id, resolved_body)
    run_shell.save_run_ledger(shell, ledger, guard_trigger="submit_result_submitted")
    folded = _run_until_wait_and_save(shell, ledger, guard_trigger="submit_result")
    return {
        "ok": True,
        "result_id": result_id,
        "run_until_wait": folded,
        **_runtime_state(ledger),
    }


def _resolve_submit_result_body(*, body: str | None, body_file: Path | None) -> str:
    sources = [value is not None for value in (body, body_file)]
    if sources.count(True) != 1:
        raise runtime.BlackBoxRuntimeError("submit-result requires exactly one body source: --body or --body-file")
    if body_file is not None:
        try:
            body = Path(body_file).read_text(encoding="utf-8")
        except OSError as exc:
            raise runtime.BlackBoxRuntimeError(
                f"submit-result --body-file is unreadable: {body_file} ({type(exc).__name__})"
            ) from exc
        source = "--body-file"
    else:
        source = "--body"
    assert body is not None
    return _require_json_object_body(body, source=source)


def _require_json_object_body(body: str, *, source: str) -> str:
    if not body.strip():
        raise runtime.BlackBoxRuntimeError(
            f"submit-result body must be a top-level JSON object; source={source}; payload_type=empty"
        )
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise runtime.BlackBoxRuntimeError(
            "submit-result body must be a top-level JSON object; "
            f"source={source}; payload_type=invalid_json; error={exc}; preview={_payload_preview(body)}"
        ) from exc
    if not isinstance(payload, dict):
        raise runtime.BlackBoxRuntimeError(
            "submit-result body must be a top-level JSON object; "
            f"source={source}; payload_type={type(payload).__name__}; preview={_payload_preview(body)}"
        )
    return body


def _payload_preview(text: str, *, limit: int = 80) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit]}...{compact[-limit:]}"


def run_fake_e2e(
    root: Path,
    *,
    run_id: str | None = None,
    startup_text: str,
    inject_contract_faults: bool = False,
    inject_consistency_faults: bool = False,
    inject_artifact_consistency_faults: bool = False,
    flowguard_artifact_fault_mode: str = "",
    inject_shallow_flowguard_report: bool = False,
    inject_terminal_replay_blocker: bool = False,
    repair_terminal_replay_blocker: bool = False,
    use_parent_route: bool = False,
) -> dict[str, Any]:
    return fake_e2e.run_fake_e2e(
        root,
        run_id=run_id,
        startup_text=startup_text,
        start_run=start_run,
        inject_contract_faults=inject_contract_faults,
        inject_consistency_faults=inject_consistency_faults,
        inject_artifact_consistency_faults=inject_artifact_consistency_faults,
        flowguard_artifact_fault_mode=flowguard_artifact_fault_mode,
        inject_shallow_flowguard_report=inject_shallow_flowguard_report,
        inject_terminal_replay_blocker=inject_terminal_replay_blocker,
        repair_terminal_replay_blocker=repair_terminal_replay_blocker,
        use_parent_route=use_parent_route,
    )


def status(root: Path, *, full: bool = False) -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    return {
        "ok": True,
        "run": shell.to_json(),
        **_runtime_state(ledger),
        "status": _status_projection(ledger, full=full),
        "status_mode": "full" if full else "compact",
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
        "status": _status_projection(ledger),
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
        "status": _status_projection(ledger),
    }


def resolve_stopped_blocker(
    root: Path,
    *,
    blocker_id: str,
    resolution: str,
    reason: str = "",
    user_requested: bool = False,
) -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    recovery = runtime.resolve_stopped_blocker(
        ledger,
        blocker_id,
        resolution=resolution,
        reason=reason,
        user_requested=user_requested,
    )
    folded = _run_until_wait_and_save(shell, ledger, guard_trigger="resolve_stopped_blocker")
    return {
        "ok": True,
        "recovery": recovery,
        "run_until_wait": folded,
        **_runtime_state(ledger),
        "status": _status_projection(ledger),
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
        "status": _status_projection(ledger),
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
        "status": _status_projection(ledger),
    }
