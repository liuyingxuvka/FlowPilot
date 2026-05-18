"""Live-run projection report for daemon reconciliation checks."""

from __future__ import annotations

from typing import Any

from flowpilot_daemon_reconciliation_checks_projection_boundary import (
    _controller_boundary_projection_findings,
    _runtime_write_lock_projection_findings,
    _startup_dual_ledger_projection_findings,
    _temp_action_file_projection_findings,
)
from flowpilot_daemon_reconciliation_checks_projection_card_ack import _card_ack_handoff_projection_findings
from flowpilot_daemon_reconciliation_checks_projection_common import (
    MISSING_POSTCONDITION_BLOCKER_SOURCE,
    PROJECT_ROOT,
    STARTUP_BLOCKER_RECONCILIATION_RESOLUTIONS,
    STARTUP_RECONCILIATION_SOURCE,
    STARTUP_RECONCILIATION_SOURCES,
    _action_is_startup_bootloader,
    _controller_boundary_receipt_status,
    _read_json,
    _resolve_current_run_root,
    _startup_reconciliation_satisfied,
)
from flowpilot_daemon_reconciliation_checks_projection_mail import _mail_delivery_projection_findings

def _live_run_projection() -> dict[str, object]:
    run_root, skip_reason = _resolve_current_run_root()
    if run_root is None:
        return {
            "ok": True,
            "classification_ok": False,
            "skipped": True,
            "skip_reason": skip_reason,
        }

    scheduler_path = run_root / "runtime" / "router_scheduler_ledger.json"
    action_dir = run_root / "runtime" / "controller_actions"
    control_block_dir = run_root / "control_blocks"

    if not scheduler_path.exists() or not action_dir.exists():
        return {
            "ok": True,
            "classification_ok": False,
            "skipped": True,
            "run_root": str(run_root.relative_to(PROJECT_ROOT)),
            "skip_reason": "current run does not have runtime scheduler/action ledgers",
        }

    scheduler = _read_json(scheduler_path)
    rows = [row for row in scheduler.get("rows", []) if isinstance(row, dict)]
    row_by_id = {str(row.get("row_id")): row for row in rows if row.get("row_id")}

    actions = []
    for path in sorted(action_dir.glob("*.json")):
        if path.name.startswith(".tmp-") or path.name.endswith(".write.lock"):
            continue
        try:
            payload = _read_json(path)
        except FileNotFoundError:
            continue
        if isinstance(payload, dict):
            actions.append(payload)

    startup_dual_ledger_findings = _startup_dual_ledger_projection_findings(run_root)
    temp_file_findings = _temp_action_file_projection_findings(run_root)
    runtime_write_lock_findings = _runtime_write_lock_projection_findings(run_root)
    boundary_findings = _controller_boundary_projection_findings(run_root, row_by_id, actions)
    mail_findings = _mail_delivery_projection_findings(run_root, row_by_id, actions)
    card_ack_findings = _card_ack_handoff_projection_findings(run_root, row_by_id, actions)

    startup_actions_by_type: dict[str, list[dict[str, Any]]] = {}
    row_findings: list[dict[str, object]] = []
    for action in actions:
        if not _action_is_startup_bootloader(action):
            continue
        action_type = str(action.get("action_type", ""))
        startup_actions_by_type.setdefault(action_type, []).append(action)

        satisfied, row = _startup_reconciliation_satisfied(action, row_by_id)
        action_reconciliation = action.get("router_reconciliation", {})
        if not isinstance(action_reconciliation, dict):
            action_reconciliation = {}
        action_source = action_reconciliation.get("source")
        receipt_status = _controller_boundary_receipt_status(run_root, action, row)
        receipt_done = bool(action.get("receipt_recorded_at") or receipt_status.get("done"))
        if (
            action.get("router_reconciliation_status") == "reconciled"
            and receipt_done
            and action_source == STARTUP_RECONCILIATION_SOURCE
        ):
            row_findings.append(
                {
                    "id": "startup_receipt_reconciled_by_daemon_postcondition_owner",
                    "action_id": action.get("action_id"),
                    "action_type": action_type,
                    "router_scheduler_row_id": action.get("router_scheduler_row_id"),
                    "owner": action_source,
                    "receipt_path": action.get("receipt_path") or action.get("expected_receipt_path"),
                }
            )
        if (
            action.get("router_reconciliation_status") == "reconciled"
            and receipt_done
            and action_source == STARTUP_RECONCILIATION_SOURCE
            and action.get("router_pending_apply_required") is True
        ):
            row_findings.append(
                {
                    "id": "startup_receipt_apply_split_requires_later_apply",
                    "action_id": action.get("action_id"),
                    "action_type": action_type,
                    "router_scheduler_row_id": action.get("router_scheduler_row_id"),
                    "router_pending_apply_required": action.get("router_pending_apply_required"),
                    "owner": action_source,
                }
            )
        if action.get("router_reconciliation_status") == "reconciled" and not satisfied:
            row_findings.append(
                {
                    "id": "startup_reconciled_without_satisfied_postcondition",
                    "action_id": action.get("action_id"),
                    "action_type": action_type,
                    "router_scheduler_row_id": action.get("router_scheduler_row_id"),
                }
            )
        if (
            action.get("router_reconciliation_status") == "reconciled"
            and action_reconciliation.get("source") not in ("", *STARTUP_RECONCILIATION_SOURCES)
        ):
            row_findings.append(
                {
                    "id": "startup_reconciled_by_wrong_owner",
                    "action_id": action.get("action_id"),
                    "action_type": action_type,
                    "owner": action_reconciliation.get("source"),
                }
            )
        if row and row.get("router_state") == "reconciled":
            row_reconciliation = row.get("reconciliation", {})
            if not isinstance(row_reconciliation, dict):
                row_reconciliation = {}
            if receipt_done and row_reconciliation.get("source") == STARTUP_RECONCILIATION_SOURCE:
                row_findings.append(
                    {
                        "id": "startup_scheduler_row_reconciled_by_daemon_postcondition_owner",
                        "action_id": action.get("action_id"),
                        "action_type": action_type,
                        "row_id": row.get("row_id"),
                        "owner": row_reconciliation.get("source"),
                    }
                )
            if row_reconciliation.get("source") not in ("", *STARTUP_RECONCILIATION_SOURCES):
                row_findings.append(
                    {
                        "id": "startup_scheduler_row_reconciled_by_wrong_owner",
                        "action_id": action.get("action_id"),
                        "action_type": action_type,
                        "row_id": row.get("row_id"),
                        "owner": row_reconciliation.get("source"),
                    }
                )

    blocker_findings: list[dict[str, object]] = []
    if control_block_dir.exists():
        for path in sorted(control_block_dir.glob("*.json")):
            if path.name.endswith(".sealed_repair_packet.json") or path.name == "blocker_repair_policy_snapshot.json":
                continue
            blocker = _read_json(path)
            if blocker.get("source") != MISSING_POSTCONDITION_BLOCKER_SOURCE:
                continue
            blocker_id = str(blocker.get("blocker_id") or "")
            action_type = str(blocker.get("originating_action_type", ""))
            matching_startup_actions = startup_actions_by_type.get(action_type, [])
            reconciled_matches = []
            for action in matching_startup_actions:
                satisfied, row = _startup_reconciliation_satisfied(action, row_by_id)
                if satisfied:
                    reconciled_matches.append(
                        {
                            "action_id": action.get("action_id"),
                            "router_scheduler_row_id": action.get("router_scheduler_row_id"),
                            "row_state": row.get("router_state") if row else None,
                        }
                    )
            resolved_by_reconciliation = (
                str(blocker.get("resolution_status") or "")
                in STARTUP_BLOCKER_RECONCILIATION_RESOLUTIONS
            )
            queued_pm_actions = []
            if blocker_id:
                for action in actions:
                    nested = action.get("action") if isinstance(action.get("action"), dict) else {}
                    if action.get("action_type") != "handle_control_blocker":
                        continue
                    if action.get("status") in {"done", "reconciled", "cancelled", "skipped", "resolved", "superseded"}:
                        continue
                    target_role = str(action.get("to_role") or nested.get("to_role") or "")
                    if target_role != "project_manager":
                        continue
                    if blocker_id not in json.dumps(action, sort_keys=True):
                        continue
                    queued_pm_actions.append(
                        {
                            "action_id": action.get("action_id"),
                            "router_scheduler_row_id": action.get("router_scheduler_row_id"),
                            "status": action.get("status"),
                            "target_role": target_role,
                        }
                    )
            if (
                matching_startup_actions
                and blocker.get("handling_lane") == "pm_repair_decision_required"
                and not bool(blocker.get("direct_retry_budget_exhausted"))
                and int(blocker.get("direct_retry_budget") or 0) < 1
            ):
                blocker_findings.append(
                    {
                        "id": "startup_missing_postcondition_pm_lane_before_reissue",
                        "blocker_id": blocker.get("blocker_id"),
                        "action_type": action_type,
                        "handling_lane": blocker.get("handling_lane"),
                        "policy_row_id": blocker.get("policy_row_id"),
                        "direct_retry_budget": blocker.get("direct_retry_budget"),
                        "direct_retry_budget_exhausted": blocker.get("direct_retry_budget_exhausted"),
                    }
                )
            if reconciled_matches and not resolved_by_reconciliation:
                blocker_findings.append(
                    {
                        "id": "startup_reconciled_action_false_pm_blocker",
                        "blocker_id": blocker.get("blocker_id"),
                        "action_type": action_type,
                        "handling_lane": blocker.get("handling_lane"),
                        "resolution_status": blocker.get("resolution_status"),
                        "reconciled_matches": reconciled_matches,
                    }
                )
                blocker_findings.append(
                    {
                        "id": "startup_blocker_not_resolved_after_success",
                        "blocker_id": blocker.get("blocker_id"),
                        "action_type": action_type,
                        "handling_lane": blocker.get("handling_lane"),
                        "resolution_status": blocker.get("resolution_status"),
                        "reconciled_matches": reconciled_matches,
                    }
                )
            if reconciled_matches and queued_pm_actions:
                blocker_findings.append(
                    {
                        "id": "startup_reconciled_action_queued_pm_repair",
                        "blocker_id": blocker.get("blocker_id"),
                        "action_type": action_type,
                        "queued_pm_actions": queued_pm_actions,
                        "reconciled_matches": reconciled_matches,
                    }
                )

    findings = (
        startup_dual_ledger_findings
        + temp_file_findings
        + runtime_write_lock_findings
        + boundary_findings
        + mail_findings
        + card_ack_findings
        + row_findings
        + blocker_findings
    )
    return {
        "ok": not findings,
        "classification_ok": True,
        "skipped": False,
        "run_id": run_root.name,
        "run_root": str(run_root.relative_to(PROJECT_ROOT)),
        "current_run_can_continue": not findings,
        "decision": "blocked_by_daemon_reconciliation_projection_gap" if findings else "no_daemon_reconciliation_projection_gap",
        "finding_count": len(findings),
        "findings": findings,
    }
