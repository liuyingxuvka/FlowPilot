"""Packet ledger helpers for the FlowPilot packet runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import barrier_bundle

from packet_runtime_paths import packet_paths_from_any_envelope, project_relative, read_json
from packet_runtime_schema import (
    BARRIER_BUNDLE_SCHEMA,
    PACKET_LEDGER_SCHEMA,
    PacketRuntimeError,
    utc_now,
    write_json_atomic,
)


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
            "all_formal_mail_must_route_through_controller": True,
            "recipient_must_verify_controller_relay_before_body_open": True,
            "controller_relay_signature_required": True,
            "contaminated_mail_requires_sender_reissue": True,
            "pm_controller_reminder_required": True,
            "router_direct_dispatch_required_before_worker": True,
            "reviewer_dispatch_required_before_worker": False,
            "role_reminder_required_in_controller_messages": True,
            "role_echo_required_in_subagent_responses": True,
            "role_output_body_must_be_file_backed": True,
            "role_chat_response_must_be_envelope_only": True,
            "role_chat_body_content_contaminates_mail": True,
        },
        "active_packet_id": None,
        "active_packet_status": None,
        "active_packet_holder": None,
        "barrier_bundle_policy": {
            "schema_version": BARRIER_BUNDLE_SCHEMA,
            "equivalence_mode": barrier_bundle.BARRIER_BUNDLE_EQUIVALENCE_MODE,
            "metadata_only": True,
            "preserves_packet_and_result_body_isolation": True,
            "controller_may_read_or_summarize_bundled_bodies": False,
            "controller_may_approve_bundled_gates": False,
            "ai_discretion_to_skip_or_downgrade_barriers": False,
        },
        "barrier_bundles": [],
        "packets": [],
    }


def _upsert_barrier_bundle_record(ledger: dict[str, Any], bundle: dict[str, Any], *, packet_id: str) -> None:
    bundles = ledger.setdefault("barrier_bundles", [])
    if not isinstance(bundles, list):
        raise PacketRuntimeError("packet_ledger.barrier_bundles must be a list")

    stored = dict(bundle)
    member_packet_ids = list(stored.get("member_packet_ids") or [])
    if packet_id not in member_packet_ids:
        member_packet_ids.append(packet_id)
    stored["member_packet_ids"] = member_packet_ids
    summary = barrier_bundle.barrier_bundle_summary(stored)
    stored["validation_report"] = summary["validation_report"]
    stored["status"] = "passed" if summary["validation_report"]["ok"] else stored.get("status", "blocked")
    bundle_key = stored.get("bundle_id") or f"{stored.get('barrier_id', 'unknown')}:{packet_id}"
    stored["bundle_id"] = bundle_key

    existing_index = next(
        (
            index
            for index, item in enumerate(bundles)
            if isinstance(item, dict) and item.get("bundle_id") == bundle_key
        ),
        None,
    )
    if existing_index is None:
        bundles.append(stored)
    else:
        merged = dict(bundles[existing_index])
        merged.update(stored)
        bundles[existing_index] = merged


def _upsert_packet_record(project_root: Path, ledger_path: Path, run_id: str, run_root: Path, record: dict[str, Any]) -> None:
    if ledger_path.exists():
        ledger = read_json(ledger_path)
    else:
        ledger = _empty_packet_ledger(project_root, run_id, run_root)

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
    if isinstance(record.get("barrier_bundle"), dict):
        _upsert_barrier_bundle_record(ledger, record["barrier_bundle"], packet_id=str(record["packet_id"]))
    write_json_atomic(ledger_path, ledger)


def _update_packet_record(project_root: Path, ledger_path: Path, packet_id: str, updates: dict[str, Any]) -> None:
    if not ledger_path.exists():
        return
    ledger = read_json(ledger_path)
    packets = ledger.get("packets")
    if not isinstance(packets, list):
        return
    for record in packets:
        if isinstance(record, dict) and record.get("packet_id") == packet_id:
            for key, value in updates.items():
                if key in {"holder_history", "controller_relay_history", "router_startup_release_history"}:
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
    ledger = read_json(ledger_path)
    packets = ledger.get("packets")
    if not isinstance(packets, list):
        return None
    for record in packets:
        if isinstance(record, dict) and record.get("packet_id") == packet_id:
            return record
    return None


def packet_ledger_record_for_envelope(project_root: Path, envelope: dict[str, Any]) -> dict[str, Any] | None:
    paths = packet_paths_from_any_envelope(project_root, envelope)
    return _packet_ledger_record(paths["packet_ledger"], str(envelope.get("packet_id") or ""))
