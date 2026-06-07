"""Run lifecycle and status commands for the FlowPilot entrypoint."""

from __future__ import annotations

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
    runtime.record_progress(ledger, lease_id, packet_id, status)
    run_shell.save_run_ledger(shell, ledger, guard_trigger="progress")
    return {"ok": True, **_runtime_state(ledger)}


def host_liveness(
    root: Path,
    *,
    lease_id: str,
    packet_id: str,
    status: str,
    source: str = "host_report",
    detail: str = "",
) -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    report = host.record_liveness(
        ledger,
        lease_id,
        packet_id,
        status,
        source=source,
        detail=detail,
    )
    run_shell.save_run_ledger(shell, ledger, guard_trigger="host_liveness")
    return {"ok": True, "host_liveness": report, **_runtime_state(ledger)}


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


def submit_result(root: Path, *, lease_id: str, packet_id: str, body: str) -> dict[str, Any]:
    shell = run_shell.load_run_shell(root)
    ledger = run_shell.load_run_ledger(shell)
    result_id = host.submit_host_result(ledger, lease_id, packet_id, body)
    run_shell.save_run_ledger(shell, ledger, guard_trigger="submit_result_submitted")
    folded = _run_until_wait_and_save(shell, ledger, guard_trigger="submit_result")
    return {
        "ok": True,
        "result_id": result_id,
        "run_until_wait": folded,
        **_runtime_state(ledger),
    }


def run_fake_e2e(
    root: Path,
    *,
    run_id: str | None = None,
    startup_text: str,
    inject_contract_faults: bool = False,
) -> dict[str, Any]:
    return fake_e2e.run_fake_e2e(
        root,
        run_id=run_id,
        startup_text=startup_text,
        start_run=start_run,
        inject_contract_faults=inject_contract_faults,
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
