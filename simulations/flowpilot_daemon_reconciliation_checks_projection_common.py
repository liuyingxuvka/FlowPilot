"""Shared live-projection helpers for daemon reconciliation checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
STARTUP_RECONCILIATION_SOURCE = "startup_daemon_bootloader_postcondition"
STARTUP_BOOTLOADER_RECEIPT_SOURCE = "startup_bootloader_controller_receipt"
STARTUP_RECONCILIATION_SOURCES = (STARTUP_RECONCILIATION_SOURCE, STARTUP_BOOTLOADER_RECEIPT_SOURCE)
MISSING_POSTCONDITION_BLOCKER_SOURCE = "controller_action_receipt_missing_router_postcondition"
CONTROLLER_BOUNDARY_RECONCILIATION_SOURCE = "router_owned_controller_boundary_confirmation_reclaim"
STARTUP_BLOCKER_RECONCILIATION_RESOLUTIONS = {
    "resolved_by_startup_reconciliation",
    "superseded_by_startup_reconciliation",
    "superseded_by_successful_startup_reconciliation",
}
TERMINAL_ACTION_STATES = {"done", "reconciled", "resolved", "superseded", "cancelled", "skipped"}
TERMINAL_ROUTER_ROW_STATES = {"reconciled", "resolved", "superseded", "cancelled", "skipped"}
ACK_COMPLETE_STATUSES = {"resolved", "acknowledged"}

def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records

def _router_daemon_events(run_root: Path) -> list[dict[str, Any]]:
    return _iter_jsonl(run_root / "runtime" / "router_daemon_events.jsonl")

def _event_details(event: dict[str, Any]) -> dict[str, Any]:
    details = event.get("details")
    return details if isinstance(details, dict) else {}

def _resolve_current_run_root() -> tuple[Path | None, str]:
    current_path = PROJECT_ROOT / ".flowpilot" / "current.json"
    if not current_path.exists():
        return None, "no .flowpilot/current.json found"
    current = _read_json(current_path)
    run_root_text = current.get("run_root")
    if not isinstance(run_root_text, str) or not run_root_text:
        return None, ".flowpilot/current.json has no run_root"
    run_root = PROJECT_ROOT / run_root_text
    if not run_root.exists():
        return None, f"current run root does not exist: {run_root_text}"
    return run_root, ""

def _action_is_startup_bootloader(action: dict[str, Any]) -> bool:
    nested = action.get("action") if isinstance(action.get("action"), dict) else {}
    return bool(
        action.get("scope_kind") == "startup"
        and (
            nested.get("startup_daemon_scheduled") is True
            or nested.get("startup_daemon_scheduler_source")
        )
    )

def _startup_reconciliation_satisfied(
    action: dict[str, Any],
    row_by_id: dict[str, dict[str, Any]],
) -> tuple[bool, dict[str, Any] | None]:
    action_reconciliation = action.get("router_reconciliation")
    if not isinstance(action_reconciliation, dict):
        action_reconciliation = {}
    row = row_by_id.get(str(action.get("router_scheduler_row_id")))
    row_reconciliation = row.get("reconciliation", {}) if row else {}
    if not isinstance(row_reconciliation, dict):
        row_reconciliation = {}

    action_source = action_reconciliation.get("source")
    row_source = row_reconciliation.get("source")
    action_satisfied = bool(
        action.get("status") == "done"
        and action.get("router_reconciliation_status") == "reconciled"
        and (
            (
                action_source == STARTUP_RECONCILIATION_SOURCE
                and action_reconciliation.get("bootstrap_flag_satisfied") is True
            )
            or (
                action_source == STARTUP_BOOTLOADER_RECEIPT_SOURCE
                and action_reconciliation.get("applied") is True
                and bool(action_reconciliation.get("postcondition"))
            )
        )
    )
    row_satisfied = bool(
        row
        and row.get("router_state") == "reconciled"
        and (
            (
                row_source == STARTUP_RECONCILIATION_SOURCE
                and row_reconciliation.get("bootstrap_flag_satisfied") is True
            )
            or (
                row_source == STARTUP_BOOTLOADER_RECEIPT_SOURCE
                and row_reconciliation.get("applied") is True
                and bool(row_reconciliation.get("postcondition"))
            )
        )
    )
    return action_satisfied or row_satisfied, row

def _controller_boundary_artifact_status(run_root: Path) -> dict[str, Any]:
    path = run_root / "startup" / "controller_boundary_confirmation.json"
    if not path.exists():
        return {"valid": False, "exists": False, "path": str(path.relative_to(PROJECT_ROOT))}
    try:
        payload = _read_json(path)
    except Exception as exc:  # pragma: no cover - defensive live-run audit
        return {
            "valid": False,
            "exists": True,
            "path": str(path.relative_to(PROJECT_ROOT)),
            "read_error": str(exc),
        }
    valid = bool(
        payload.get("schema_version") == "flowpilot.controller_boundary_confirmation.v1"
        and payload.get("router_owned_confirmation") is True
        and payload.get("event") == "controller_role_confirmed_from_router_core"
    )
    return {
        "valid": valid,
        "exists": True,
        "path": str(path.relative_to(PROJECT_ROOT)),
        "schema_version": payload.get("schema_version"),
        "event": payload.get("event"),
        "router_owned_confirmation": payload.get("router_owned_confirmation"),
        "controller_action_id": payload.get("controller_action_id"),
    }

def _controller_boundary_receipt_status(run_root: Path, action: dict[str, Any], row: dict[str, Any] | None) -> dict[str, Any]:
    rel_path = action.get("receipt_path") or action.get("expected_receipt_path")
    if not rel_path and row:
        rel_path = row.get("controller_receipt_path")
    if not rel_path:
        nested = action.get("action") if isinstance(action.get("action"), dict) else {}
        rel_path = nested.get("controller_receipt_path")
    if not isinstance(rel_path, str) or not rel_path:
        return {"done": False, "path": None}
    receipt_path = PROJECT_ROOT / rel_path
    if not receipt_path.exists():
        receipt_path = run_root / Path(rel_path).name
    if not receipt_path.exists():
        return {"done": False, "path": rel_path, "exists": False}
    try:
        receipt = _read_json(receipt_path)
    except Exception as exc:  # pragma: no cover - defensive live-run audit
        return {"done": False, "path": rel_path, "exists": True, "read_error": str(exc)}
    return {
        "done": receipt.get("status") == "done",
        "path": rel_path,
        "exists": True,
        "status": receipt.get("status"),
        "recorded_at": receipt.get("recorded_at"),
    }

def _bundle_identity(record: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(record.get("card_bundle_id") or ""),
        str(record.get("expected_return_path") or record.get("ack_path") or ""),
        str(record.get("card_return_event") or ""),
    )

def _record_matches_bundle(record: dict[str, Any], bundle_id: str, expected_return_path: str, event: str) -> bool:
    nested = record.get("action") if isinstance(record.get("action"), dict) else {}
    record_bundle = str(record.get("card_bundle_id") or nested.get("card_bundle_id") or "")
    record_return = str(record.get("expected_return_path") or nested.get("expected_return_path") or "")
    record_event = str(record.get("card_return_event") or nested.get("card_return_event") or "")
    return bool(
        (bundle_id and record_bundle == bundle_id)
        or (expected_return_path and record_return == expected_return_path)
        or (event and record_event == event and (record_bundle or record_return))
    )

def _user_intake_packet_summary(packet_ledger: dict[str, Any]) -> dict[str, Any] | None:
    packets = packet_ledger.get("packets") if isinstance(packet_ledger.get("packets"), list) else []
    for packet in packets:
        if not isinstance(packet, dict) or packet.get("packet_id") != "user_intake":
            continue
        envelope = packet.get("packet_envelope") if isinstance(packet.get("packet_envelope"), dict) else {}
        holder = str(packet.get("active_packet_holder") or packet_ledger.get("active_packet_holder") or "")
        status = str(packet.get("active_packet_status") or "")
        router_release = packet.get("packet_router_release") or packet.get("router_startup_release")
        if not isinstance(router_release, dict):
            router_release = {}
        controller_relay = packet.get("packet_controller_relay") or packet.get("controller_relay")
        if not isinstance(controller_relay, dict):
            controller_relay = {}
        return {
            "packet_id": packet.get("packet_id"),
            "packet_holder": holder,
            "packet_status": status,
            "to_role": envelope.get("to_role") or packet.get("assigned_worker_role"),
            "next_holder": envelope.get("next_holder"),
            "router_direct_dispatch_decision": packet.get("router_direct_dispatch_decision"),
            "router_owned_startup_material": bool(packet.get("router_owned_startup_material")),
            "router_release_recorded": bool(
                router_release
                and router_release.get("delivered_by_router") is True
                and str(router_release.get("relayed_to_role") or "") == "project_manager"
            ),
            "controller_relay_recorded": bool(
                controller_relay
                and controller_relay.get("delivered_via_controller") is True
                and str(controller_relay.get("relayed_to_role") or "") == "project_manager"
            ),
            "top_level_active_packet_status": packet_ledger.get("active_packet_status"),
            "terminal_lifecycle": packet_ledger.get("terminal_lifecycle"),
        }
    return None

def _user_intake_delivery_action_exists(actions: list[dict[str, Any]]) -> bool:
    for action in actions:
        nested = action.get("action") if isinstance(action.get("action"), dict) else {}
        if action.get("action_type") != "deliver_mail":
            continue
        mail_id = str(action.get("mail_id") or nested.get("mail_id") or "")
        if mail_id == "user_intake":
            return True
    return False

def _mail_ledger_has_user_intake(packet_ledger: dict[str, Any]) -> bool:
    mail_entries = packet_ledger.get("mail") if isinstance(packet_ledger.get("mail"), list) else []
    return any(isinstance(item, dict) and item.get("mail_id") == "user_intake" for item in mail_entries)

def _user_intake_router_released(packet: dict[str, Any] | None, packet_ledger: dict[str, Any]) -> bool:
    if not isinstance(packet, dict):
        return False
    released_statuses = {
        "envelope-relayed",
        "packet-body-opened-by-recipient",
        "result-body-opened-by-recipient",
        "result-returned",
        "result-returned-to-router",
        "stopped_by_user",
    }
    terminal_lifecycle = packet.get("terminal_lifecycle")
    terminal_ok = isinstance(terminal_lifecycle, dict) and terminal_lifecycle.get("status") in {
        "stopped_by_user",
        "cancelled_by_user",
        "closed",
    }
    packet_status = str(packet.get("packet_status") or "")
    top_level_status = str(packet_ledger.get("active_packet_status") or "")
    return (
        str(packet.get("packet_holder") or "") == "project_manager"
        and packet_status in released_statuses
        and (
            (
                packet_ledger.get("active_packet_holder") == "project_manager"
                and top_level_status in released_statuses
            )
            or terminal_ok
        )
    )

def _computed_actions_after(router_state: dict[str, Any], after_time: str) -> list[str]:
    history = router_state.get("history") if isinstance(router_state.get("history"), list) else []
    actions: list[str] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        if item.get("label") != "router_computed_next_controller_action":
            continue
        at = str(item.get("at") or "")
        if after_time and at and at < after_time:
            continue
        details = item.get("details") if isinstance(item.get("details"), dict) else {}
        action_type = str(details.get("action_type") or "")
        if action_type:
            actions.append(action_type)
    return actions
