"""Boundary and startup live-projection findings for daemon reconciliation checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flowpilot_daemon_reconciliation_checks_projection_common import (
    CONTROLLER_BOUNDARY_RECONCILIATION_SOURCE,
    PROJECT_ROOT,
    _controller_boundary_artifact_status,
    _controller_boundary_receipt_status,
    _event_details,
    _iter_jsonl,
    _read_json,
    _router_daemon_events,
)

def _startup_dual_ledger_projection_findings(run_root: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    startup_state_path = run_root / "bootstrap" / "startup_state.json"
    router_state_path = run_root / "runtime" / "router_state.json"
    startup_state = _read_json(startup_state_path) if startup_state_path.exists() else {}
    router_state = _read_json(router_state_path) if router_state_path.exists() else {}

    startup_roles = bool(startup_state.get("roles_started"))
    startup_prompts = bool(startup_state.get("role_core_prompts_injected"))
    router_roles = bool(router_state.get("roles_started"))
    router_prompts = bool(router_state.get("role_core_prompts_injected"))
    if (startup_roles or startup_prompts) and not (router_roles and router_prompts):
        findings.append(
            {
                "id": "startup_role_flags_left_in_secondary_record",
                "startup_roles_started": startup_roles,
                "startup_role_core_prompts_injected": startup_prompts,
                "router_roles_started": router_roles,
                "router_role_core_prompts_injected": router_prompts,
            }
        )
    if router_roles and not router_prompts:
        findings.append(
            {
                "id": "startup_roles_started_without_core_prompt_router_flag",
                "router_roles_started": router_roles,
                "router_role_core_prompts_injected": router_prompts,
            }
        )

    for event in _router_daemon_events(run_root):
        if event.get("event") != "router_daemon_lock_released":
            continue
        details = _event_details(event)
        reason = str(event.get("reason") or details.get("reason") or "")
        if "start_role_flags_not_folded" not in reason:
            continue
        findings.append(
            {
                "id": "startup_role_flag_fold_required_manual_daemon_restart",
                "reason": reason,
                "time": event.get("time") or event.get("recorded_at"),
            }
        )
    return findings

def _temp_action_file_projection_findings(run_root: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for event in _router_daemon_events(run_root):
        if event.get("event") != "router_daemon_error":
            continue
        details = _event_details(event)
        error_type = event.get("error_type") or details.get("error_type")
        error_message = str(
            event.get("error_message")
            or details.get("error_message")
            or event.get("error")
            or details.get("error")
            or ""
        )
        normalized = error_message.replace("\\", "/")
        if (
            error_type == "FileNotFoundError"
            and "controller_actions" in normalized
            and ".tmp-" in normalized
            and ".json" in normalized
        ):
            findings.append(
                {
                    "id": "temp_controller_action_file_race_stopped_daemon",
                    "error_type": error_type,
                    "error_message": error_message,
                    "time": event.get("time") or event.get("recorded_at"),
                }
            )
    return findings

def _runtime_write_lock_projection_findings(run_root: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    runtime_dir = run_root / "runtime"
    if not runtime_dir.exists():
        return findings
    needles = (
        "runtime ledger write is still in progress",
        "fresh runtime JSON write lock",
        "runtime JSON write lock",
    )
    candidates: list[Path] = []
    for pattern in ("*.err.txt", "*.out.txt", "*.combined.txt", "*.log"):
        candidates.extend(sorted(runtime_dir.glob(pattern)))
    for path in candidates:
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines, start=1):
            normalized = line.lower()
            if not any(needle.lower() in normalized for needle in needles):
                continue
            findings.append(
                {
                    "id": "foreground_start_failed_on_fresh_runtime_writer",
                    "path": str(path.relative_to(PROJECT_ROOT)),
                    "line": line_no,
                    "message": line.strip()[:500],
                }
            )
            return findings
    return findings

def _controller_boundary_projection_findings(
    run_root: Path,
    row_by_id: dict[str, dict[str, Any]],
    actions: list[dict[str, Any]],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    router_state_path = run_root / "router_state.json"
    router_state = _read_json(router_state_path) if router_state_path.exists() else {}
    flags = router_state.get("flags") if isinstance(router_state.get("flags"), dict) else {}
    boundary_flags_synced = bool(
        flags.get("controller_boundary_confirmation_written") is True
        and flags.get("controller_role_confirmed") is True
        and flags.get("controller_role_confirmed_from_router_core") is True
    )
    artifact = _controller_boundary_artifact_status(run_root)
    history = router_state.get("history") if isinstance(router_state.get("history"), list) else []
    boundary_next_events = [
        item for item in history
        if isinstance(item, dict)
        and item.get("label") == "router_computed_next_controller_action"
        and isinstance(item.get("details"), dict)
        and item["details"].get("action_type") == "confirm_controller_core_boundary"
    ]
    pending_empty = router_state.get("pending_action") is None

    for action in actions:
        if action.get("action_type") != "confirm_controller_core_boundary":
            continue
        row = row_by_id.get(str(action.get("router_scheduler_row_id")))
        action_reconciliation = action.get("router_reconciliation", {})
        if not isinstance(action_reconciliation, dict):
            action_reconciliation = {}
        row_reconciliation = row.get("reconciliation", {}) if row else {}
        if not isinstance(row_reconciliation, dict):
            row_reconciliation = {}
        receipt = _controller_boundary_receipt_status(run_root, action, row)
        action_reconciled = bool(
            action.get("status") == "done"
            and action.get("router_reconciliation_status") == "reconciled"
            and action_reconciliation.get("source") == CONTROLLER_BOUNDARY_RECONCILIATION_SOURCE
        )
        row_reconciled = bool(
            row
            and row.get("router_state") == "reconciled"
            and row_reconciliation.get("source") == CONTROLLER_BOUNDARY_RECONCILIATION_SOURCE
        )
        evidence = {
            "action_id": action.get("action_id"),
            "router_scheduler_row_id": action.get("router_scheduler_row_id"),
            "action_reconciled": action_reconciled,
            "scheduler_reconciled": row_reconciled,
            "receipt": receipt,
            "artifact": artifact,
            "flags": {
                "controller_boundary_confirmation_written": flags.get("controller_boundary_confirmation_written"),
                "controller_role_confirmed": flags.get("controller_role_confirmed"),
                "controller_role_confirmed_from_router_core": flags.get("controller_role_confirmed_from_router_core"),
            },
        }
        if artifact.get("valid") and receipt.get("done") and action_reconciled != row_reconciled:
            findings.append(
                {
                    "id": "controller_boundary_action_scheduler_disagree",
                    "action_type": "confirm_controller_core_boundary",
                    **evidence,
                }
            )
        if artifact.get("valid") and receipt.get("done") and action_reconciled and row_reconciled and not boundary_flags_synced:
            findings.append(
                {
                    "id": "controller_boundary_reconciled_artifact_left_flags_false",
                    "action_type": "confirm_controller_core_boundary",
                    **evidence,
                }
            )
            nested = action.get("action") if isinstance(action.get("action"), dict) else {}
            if boundary_next_events:
                findings.append(
                    {
                        "id": "controller_boundary_reissued_after_reconciled_artifact",
                        "action_type": "confirm_controller_core_boundary",
                        "latest_computed_at": boundary_next_events[-1].get("at"),
                        "action_created_at": nested.get("created_at") or action.get("created_at"),
                        **evidence,
                    }
                )
            if pending_empty and boundary_next_events:
                findings.append(
                    {
                        "id": "controller_boundary_action_returned_without_pending_action",
                        "action_type": "confirm_controller_core_boundary",
                        "latest_computed_at": boundary_next_events[-1].get("at"),
                        **evidence,
                    }
                )
    return findings
