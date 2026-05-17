"""Resume and heartbeat helpers for FlowPilot router."""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType
from typing import Any


def write_host_heartbeat_binding(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    binding_path = router._continuation_binding_path(run_root)
    binding = router.read_json_if_exists(binding_path)
    answers = router._startup_answers_from_run(run_root)
    scheduled_requested = router._scheduled_continuation_requested(answers)
    interval = int(payload.get("route_heartbeat_interval_minutes") or binding.get("route_heartbeat_interval_minutes") or 0)
    if scheduled_requested and interval != 1:
        raise router.RouterError("scheduled FlowPilot heartbeat must be one minute")
    if scheduled_requested and not payload.get("host_automation_id"):
        raise router.RouterError("scheduled FlowPilot heartbeat requires host_automation_id")
    if scheduled_requested and payload.get("host_automation_verified") is not True:
        raise router.RouterError("scheduled FlowPilot heartbeat requires host_automation_verified=true")
    host_automation_proof = payload.get("host_automation_proof")
    if scheduled_requested and not isinstance(host_automation_proof, dict):
        raise router.RouterError("scheduled FlowPilot heartbeat requires host_automation_proof")
    if host_automation_proof is not None:
        if not isinstance(host_automation_proof, dict):
            raise router.RouterError("host_automation_proof must be an object")
        if host_automation_proof.get("source_kind") != "host_receipt":
            raise router.RouterError("host_automation_proof requires source_kind=host_receipt")
        if host_automation_proof.get("run_id") != run_state["run_id"]:
            raise router.RouterError("host_automation_proof run_id must match current run")
        if host_automation_proof.get("host_automation_id") != payload.get("host_automation_id"):
            raise router.RouterError("host_automation_proof host_automation_id mismatch")
        if int(host_automation_proof.get("route_heartbeat_interval_minutes") or 0) != 1:
            raise router.RouterError("host_automation_proof requires one-minute heartbeat interval")
        if host_automation_proof.get("heartbeat_bound_to_current_run") is not True:
            raise router.RouterError("host_automation_proof must bind heartbeat to current run")
    binding.update(
        {
            "schema_version": "flowpilot.continuation_binding.v1",
            "run_id": run_state["run_id"],
            "mode": "scheduled_heartbeat" if scheduled_requested else "manual_resume",
            "scheduled_continuation_requested": scheduled_requested,
            "route_heartbeat_interval_minutes": 1 if scheduled_requested else 0,
            "heartbeat_active": bool(scheduled_requested),
            "host_automation_id": payload.get("host_automation_id") if scheduled_requested else None,
            "host_automation_verified": bool(scheduled_requested),
            "stable_launcher": router._stable_resume_launcher_contract(),
            **({"host_automation_proof": host_automation_proof} if scheduled_requested and isinstance(host_automation_proof, dict) else {}),
            "recorded_by": str(payload.get("recorded_by") or "host"),
            "updated_at": router.utc_now(),
        }
    )
    router.write_json(binding_path, binding)


def append_heartbeat_tick(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    del project_root
    source = str(payload.get("source") or "heartbeat_or_manual_resume")
    tick = {
        "schema_version": "flowpilot.heartbeat_tick.v1",
        "run_id": run_state["run_id"],
        "tick_id": f"heartbeat-{len(run_state.get('heartbeat_ticks', [])) + 1:04d}",
        "work_chain_status": str(payload.get("work_chain_status") or "broken_or_unknown"),
        "work_chain_status_trust": "diagnostic_only",
        "recorded_at": router.utc_now(),
        "source": source,
        "resume_requested": True,
        "router_reentry_required": True,
        "self_keepalive_allowed": False,
        "heartbeat_automation_status": str(payload.get("heartbeat_automation_status") or "unknown"),
        "heartbeat_automation_status_checked": payload.get("heartbeat_automation_status_checked") is True,
    }
    ticks_path = run_root / "continuation" / "heartbeat_ticks.jsonl"
    ticks_path.parent.mkdir(parents=True, exist_ok=True)
    with ticks_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(tick, sort_keys=True) + "\n")
    run_state.setdefault("heartbeat_ticks", []).append(
        {
            "tick_id": tick["tick_id"],
            "work_chain_status": tick["work_chain_status"],
            "resume_requested": tick["resume_requested"],
            "router_reentry_required": tick["router_reentry_required"],
            "self_keepalive_allowed": tick["self_keepalive_allowed"],
            "heartbeat_automation_status": tick["heartbeat_automation_status"],
            "heartbeat_automation_status_checked": tick["heartbeat_automation_status_checked"],
        }
    )
    return tick


def reset_resume_cycle_for_wakeup(router: ModuleType, run_state: dict[str, Any]) -> None:
    for flag in (
        "resume_reentry_requested",
        "resume_state_loaded",
        "resume_state_ambiguous",
        "resume_roles_restored",
        "resume_role_agents_rehydrated",
        "crew_rehydration_report_written",
        "controller_resume_card_delivered",
        "pm_crew_rehydration_freshness_card_delivered",
        "pm_resume_decision_card_delivered",
        "pm_resume_recovery_decision_returned",
        "role_recovery_requested",
        "role_recovery_state_loaded",
        "role_recovery_roles_restored",
        "role_recovery_report_written",
        "role_recovery_environment_blocked",
        "role_recovery_obligations_scanned",
        "role_recovery_obligation_replay_completed",
        "role_recovery_pm_escalation_required",
    ):
        run_state["flags"][flag] = False
