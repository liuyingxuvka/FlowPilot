"""Packet ledger helpers for the FlowPilot packet runtime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


from packet_runtime_paths import packet_paths_from_any_envelope, project_relative, read_json
from packet_runtime_schema import (
    PACKET_LEDGER_SCHEMA,
    PacketRuntimeError,
    utc_now,
    write_json_atomic,
)


def _packet_ledger_corrupt_backup_path(ledger_path: Path) -> Path:
    stamp = utc_now().replace(":", "").replace("-", "").replace("Z", "Z")
    return ledger_path.with_name(f"{ledger_path.stem}.corrupt-backup-{stamp}{ledger_path.suffix}")


def _salvage_packet_ledger_payload(ledger_path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        text = ledger_path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return None, f"unreadable:{type(exc).__name__}"
    try:
        payload, end = json.JSONDecoder().raw_decode(text)
    except json.JSONDecodeError as exc:
        return None, f"unsalvageable:{exc.msg}"
    if not isinstance(payload, dict):
        return None, "unsalvageable:root_not_object"
    trailing = text[end:].strip()
    reason = "salvaged_full_object" if not trailing else "salvaged_first_json_object_with_trailing_bytes"
    return payload, reason


def _read_packet_ledger_or_recover(
    project_root: Path,
    ledger_path: Path,
    run_id: str,
    run_root: Path,
) -> dict[str, Any]:
    if not ledger_path.exists():
        return _empty_packet_ledger(project_root, run_id, run_root)
    try:
        return read_json(ledger_path)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, PacketRuntimeError) as exc:
        backup_path = _packet_ledger_corrupt_backup_path(ledger_path)
        salvaged, reason = _salvage_packet_ledger_payload(ledger_path)
        backup_rel: str | None = None
        try:
            ledger_path.replace(backup_path)
            backup_rel = project_relative(project_root, backup_path)
        except OSError:
            backup_rel = None
        ledger = salvaged if isinstance(salvaged, dict) else _empty_packet_ledger(project_root, run_id, run_root)
        recovery = {
            "recovered_at": utc_now(),
            "reason": reason,
            "error": str(exc),
            "corrupt_backup_path": backup_rel,
        }
        ledger["schema_version"] = PACKET_LEDGER_SCHEMA
        ledger["run_id"] = run_id
        ledger["run_root"] = project_relative(project_root, run_root)
        ledger["packet_root"] = project_relative(project_root, run_root / "packets")
        ledger["updated_at"] = utc_now()
        history = ledger.get("recovery_history") if isinstance(ledger.get("recovery_history"), list) else []
        history.append(recovery)
        ledger["recovery_history"] = history
        ledger["last_recovery"] = recovery
        write_json_atomic(ledger_path, ledger)
        return ledger


def _empty_packet_ledger(project_root: Path, run_id: str, run_root: Path) -> dict[str, Any]:
    return {
        "schema_version": PACKET_LEDGER_SCHEMA,
        "run_id": run_id,
        "run_root": project_relative(project_root, run_root),
        "updated_at": utc_now(),
        "packet_root": project_relative(project_root, run_root / "packets"),
        "controller_boundary": {
            "controller_only": True,
            "controller_visibility": "packet_and_result_envelopes_only",
            "controller_may_read_packet_body": False,
            "controller_may_read_result_body": False,
            "controller_may_execute_worker_packet": False,
            "controller_may_advance_from_own_evidence": False,
            "controller_may_relabel_wrong_role_origin": False,
            "all_formal_mail_must_use_current_assignment": True,
            "recipient_must_verify_current_assignment_before_body_open": True,
            "contaminated_mail_requires_sender_reissue": True,
            "pm_controller_reminder_required": True,
            "router_direct_dispatch_required_before_worker": True,
            "reviewer_dispatch_required_before_worker": False,
            "role_reminder_required_in_controller_messages": True,
            "role_echo_required_in_role_binding_responses": True,
            "role_output_body_must_be_file_backed": True,
            "role_chat_response_must_be_envelope_only": True,
            "role_chat_body_content_contaminates_mail": True,
        },
        "active_packet_id": None,
        "active_packet_status": None,
        "active_packet_holder": None,
        "packets": [],
    }


def _upsert_packet_record(project_root: Path, ledger_path: Path, run_id: str, run_root: Path, record: dict[str, Any]) -> None:
    ledger = _read_packet_ledger_or_recover(project_root, ledger_path, run_id, run_root)

    packets = ledger.setdefault("packets", [])
    if not isinstance(packets, list):
        raise PacketRuntimeError("packet_ledger.packets must be a list")

    existing_index = next(
        (index for index, item in enumerate(packets) if isinstance(item, dict) and item.get("packet_id") == record["packet_id"]),
        None,
    )
    if existing_index is None:
        packets.append(record)
    else:
        merged = dict(packets[existing_index])
        merged.update(record)
        if packets[existing_index].get("holder_history") and record.get("holder_history"):
            merged["holder_history"] = record["holder_history"]
        packets[existing_index] = merged

    ledger["schema_version"] = PACKET_LEDGER_SCHEMA
    ledger["run_id"] = run_id
    ledger["run_root"] = project_relative(project_root, run_root)
    ledger["packet_root"] = project_relative(project_root, run_root / "packets")
    ledger["updated_at"] = utc_now()
    ledger["active_packet_id"] = record["packet_id"]
    ledger["active_packet_status"] = record.get("active_packet_status") or ledger.get("active_packet_status")
    ledger["active_packet_holder"] = record.get("active_packet_holder") or ledger.get("active_packet_holder")
    write_json_atomic(ledger_path, ledger)


def _update_packet_record(project_root: Path, ledger_path: Path, packet_id: str, updates: dict[str, Any]) -> None:
    if not ledger_path.exists():
        return
    run_root = ledger_path.parent
    ledger = _read_packet_ledger_or_recover(project_root, ledger_path, run_root.name, run_root)
    packets = ledger.get("packets")
    if not isinstance(packets, list):
        return
    for record in packets:
        if isinstance(record, dict) and record.get("packet_id") == packet_id:
            for key, value in updates.items():
                if key in {"holder_history", "router_startup_release_history"}:
                    existing = record.setdefault(key, [])
                    if isinstance(existing, list):
                        existing.extend(value if isinstance(value, list) else [value])
                    else:
                        record[key] = value if isinstance(value, list) else [value]
                else:
                    record[key] = value
            ledger["active_packet_id"] = packet_id
            if "active_packet_status" in updates:
                ledger["active_packet_status"] = updates["active_packet_status"]
            if "active_packet_holder" in updates:
                ledger["active_packet_holder"] = updates["active_packet_holder"]
            ledger["updated_at"] = utc_now()
            write_json_atomic(ledger_path, ledger)
            return


def _packet_ledger_record(ledger_path: Path, packet_id: str) -> dict[str, Any] | None:
    if not ledger_path.exists():
        return None
    try:
        ledger = read_json(ledger_path)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, PacketRuntimeError):
        return None
    packets = ledger.get("packets")
    if not isinstance(packets, list):
        return None
    for record in packets:
        if isinstance(record, dict) and record.get("packet_id") == packet_id:
            return record
    return None


def packet_ledger_record_for_envelope(project_root: Path, envelope: dict[str, Any]) -> dict[str, Any] | None:
    paths = packet_paths_from_any_envelope(project_root, envelope)
    ledger = _read_packet_ledger_or_recover(
        project_root,
        paths["packet_ledger"],
        str(paths["run_id"]),
        paths["run_root"],
    )
    packets = ledger.get("packets")
    if not isinstance(packets, list):
        return None
    packet_id = str(envelope.get("packet_id") or "")
    for record in packets:
        if isinstance(record, dict) and record.get("packet_id") == packet_id:
            return record
    return None
