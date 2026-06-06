"""Manual resume helpers for FlowPilot router."""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType
from typing import Any

from flowpilot_runtime_gateway import GATEWAY_ROUTER_JSON, assert_runtime_gateway_write

_MANUAL_RESUME_BINDING_PAYLOAD_FIELDS = {"recorded_by"}


def write_manual_resume_binding(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    del project_root
    binding_path = router._continuation_binding_path(run_root)
    binding = router.read_json_if_exists(binding_path)
    unsupported = sorted(set(payload) - _MANUAL_RESUME_BINDING_PAYLOAD_FIELDS)
    if unsupported:
        raise router.RouterError(
            "manual resume binding payload contains unsupported fields: "
            + ", ".join(unsupported)
        )
    binding.update(
        {
            "schema_version": "flowpilot.continuation_binding.v1",
            "run_id": run_state["run_id"],
            "mode": "manual_resume",
            "manual_resume_required": True,
            "manual_resume_binding_active": True,
            "host_automation_supported": False,
            "stable_launcher": router._stable_resume_launcher_contract(),
            "recorded_by": str(payload.get("recorded_by") or "host"),
            "updated_at": router.utc_now(),
        }
    )
    router.write_json(binding_path, binding)


def append_manual_resume_tick(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    del project_root
    source = str(payload.get("source") or "manual_resume")
    if source != "manual_resume":
        raise router.RouterError("manual_resume_requested requires payload.source=manual_resume")
    tick = {
        "schema_version": "flowpilot.manual_resume_tick.v1",
        "run_id": run_state["run_id"],
        "tick_id": f"manual-resume-{len(run_state.get('resume_ticks', [])) + 1:04d}",
        "work_chain_status": str(payload.get("work_chain_status") or "broken_or_unknown"),
        "work_chain_status_trust": "diagnostic_only",
        "recorded_at": router.utc_now(),
        "source": source,
        "resume_requested": True,
        "router_reentry_required": True,
        "self_keepalive_allowed": False,
        "host_automation_supported": False,
    }
    ticks_path = run_root / "continuation" / "manual_resume_ticks.jsonl"
    assert_runtime_gateway_write(ticks_path, GATEWAY_ROUTER_JSON, operation="append_manual_resume_tick")
    ticks_path.parent.mkdir(parents=True, exist_ok=True)
    with ticks_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(tick, sort_keys=True) + "\n")
    run_state.setdefault("resume_ticks", []).append(
        {
            "tick_id": tick["tick_id"],
            "work_chain_status": tick["work_chain_status"],
            "resume_requested": tick["resume_requested"],
            "router_reentry_required": tick["router_reentry_required"],
            "self_keepalive_allowed": tick["self_keepalive_allowed"],
            "host_automation_supported": False,
        }
    )
    return tick


def reset_resume_cycle_for_wakeup(router: ModuleType, run_state: dict[str, Any]) -> None:
    for flag in (
        "resume_reentry_requested",
        "resume_state_loaded",
        "resume_state_ambiguous",
        "resume_roles_restored",
        "resume_role_bindings_rehydrated",
        "role_binding_recovery_report_written",
        "controller_resume_card_delivered",
        "pm_role_binding_recovery_freshness_card_delivered",
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
