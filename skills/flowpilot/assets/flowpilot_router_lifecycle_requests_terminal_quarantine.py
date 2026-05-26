"""Terminal quarantine helpers for FlowPilot lifecycle reconciliation."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any


_TERMINAL_MATERIAL_PROGRESS_FLAGS = (
    "material_scan_packets_relayed",
    "worker_packets_delivered",
    "worker_scan_results_returned",
    "material_scan_results_relayed_to_pm",
    "material_scan_result_disposition_recorded",
    "material_scan_results_absorbed_by_pm",
    "material_review_sufficient",
    "material_review_insufficient",
)


def clear_active_repair_transaction_for_terminal_lifecycle(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    mode: str,
    event: str,
    cleared_at: str,
) -> dict[str, Any] | None:
    active = run_state.get("active_repair_transaction")
    if not isinstance(active, dict):
        return None
    transaction_id = str(active.get("transaction_id") or "")
    tx_path = router.resolve_project_path(project_root, str(active.get("path") or "")) if active.get("path") else None
    if not tx_path and transaction_id:
        tx_path = router._repair_transaction_path(run_root, transaction_id)
    previous_status = str(active.get("status") or "")
    if tx_path and tx_path.exists():
        record = router.read_json(tx_path)
        previous_status = str(record.get("status") or previous_status)
        if record.get("status") in {"opened", "committed", "awaiting_recheck"}:
            record["status"] = "superseded_by_terminal_lifecycle"
            record["superseded_by_event"] = event
            record["superseded_at"] = cleared_at
            record["terminal_lifecycle_status"] = mode
            router.write_json(tx_path, record)
    run_state["active_repair_transaction"] = None
    router._write_repair_transaction_index(project_root, run_root, run_state)
    return {
        "authority": "repair_transaction",
        "transaction_id": transaction_id or None,
        "previous_status": previous_status or None,
        "status": "superseded_by_terminal_lifecycle",
    }


def quarantine_material_progress_for_terminal_lifecycle(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    mode: str,
    event: str,
    reconciled_at: str,
) -> dict[str, Any] | None:
    flags = run_state.get("flags")
    if not isinstance(flags, dict):
        return None
    previous_true = {flag: True for flag in _TERMINAL_MATERIAL_PROGRESS_FLAGS if flags.get(flag) is True}
    if not previous_true:
        return None
    for flag in previous_true:
        flags[flag] = False
    receipt = {
        "authority": "material_progress_flags",
        "previous_true_flags": sorted(previous_true),
        "cleared_for_terminal_lifecycle": True,
    }
    material_index_path = run_root / "material" / "material_scan_packets.json"
    if material_index_path.exists():
        material_index = router.read_json(material_index_path)
        material_index["terminal_lifecycle_quarantine"] = {
            "status": "terminal_lifecycle_quarantined",
            "event": event,
            "terminal_lifecycle_status": mode,
            "reason": "run stopped before active material generation completed; stale run-wide progress flags are not current-generation evidence",
            "quarantined_at": reconciled_at,
        }
        router.write_json(material_index_path, material_index)
        receipt["material_index_path"] = router.project_relative(project_root, material_index_path)
    active_ref_path = run_root / "packet_batches" / "active_material_scan.json"
    if active_ref_path.exists():
        active_ref = router.read_json(active_ref_path)
        batch_path = router.resolve_project_path(project_root, str(active_ref.get("batch_path") or ""))
        if batch_path.exists():
            batch = router.read_json(batch_path)
            batch["terminal_lifecycle_quarantine"] = {
                "status": "terminal_lifecycle_quarantined",
                "event": event,
                "terminal_lifecycle_status": mode,
                "previous_status": batch.get("status"),
                "quarantined_at": reconciled_at,
            }
            router.write_json(batch_path, batch)
            receipt["active_batch_path"] = router.project_relative(project_root, batch_path)
    run_state["terminal_material_progress_quarantine"] = {
        "schema_version": "flowpilot.terminal_material_progress_quarantine.v1",
        "status": "terminal_lifecycle_quarantined",
        "event": event,
        "terminal_lifecycle_status": mode,
        "previous_true_flags": sorted(previous_true),
        "quarantined_at": reconciled_at,
    }
    return receipt


def quarantine_duplicate_role_events_for_terminal_lifecycle(
    run_state: dict[str, Any],
    *,
    mode: str,
    event: str,
    reconciled_at: str,
) -> dict[str, Any] | None:
    events = run_state.get("events")
    if not isinstance(events, list):
        return None
    duplicate_count = 0
    seen: dict[tuple[str, str, str], int] = {}
    for index, item in enumerate(events):
        if not isinstance(item, dict):
            continue
        payload = item.get("payload")
        body_ref = payload.get("body_ref") if isinstance(payload, dict) else None
        if not isinstance(body_ref, dict):
            continue
        key = (
            str(item.get("event") or ""),
            str(body_ref.get("path") or ""),
            str(body_ref.get("hash") or body_ref.get("report_hash") or ""),
        )
        if not all(key):
            continue
        first_index = seen.get(key)
        if first_index is None:
            seen[key] = index
            continue
        item["terminal_lifecycle_quarantine"] = {
            "status": "terminal_lifecycle_quarantined",
            "event": event,
            "terminal_lifecycle_status": mode,
            "duplicate_of_event_index": first_index,
            "reason": "duplicate role-output event side effect preserved as history after user stop",
            "quarantined_at": reconciled_at,
        }
        duplicate_count += 1

    package_conflict_count = 0
    idempotency = run_state.get("external_event_idempotency")
    processed = idempotency.get("processed") if isinstance(idempotency, dict) else None
    if isinstance(processed, dict):
        for event_name in (
            "pm_records_material_scan_result_disposition",
            "pm_records_research_result_disposition",
            "pm_records_current_node_result_disposition",
        ):
            event_records = processed.get(event_name)
            if not isinstance(event_records, dict):
                continue
            groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
            for record in event_records.values():
                if not isinstance(record, dict):
                    continue
                scope = record.get("scope")
                if not isinstance(scope, dict):
                    continue
                key = (
                    str(scope.get("batch_id") or ""),
                    str(scope.get("packet_ids") or ""),
                    str(scope.get("packet_generation_id") or ""),
                )
                if all(key) and scope.get("body_hash"):
                    groups.setdefault(key, []).append(record)
            for records in groups.values():
                body_hashes = {str((record.get("scope") or {}).get("body_hash") or "") for record in records}
                if len(body_hashes) <= 1:
                    continue
                for record in records[1:]:
                    record["terminal_lifecycle_quarantine"] = {
                        "status": "terminal_lifecycle_quarantined",
                        "event": event,
                        "terminal_lifecycle_status": mode,
                        "reason": "conflicting package disposition identity preserved as history after user stop",
                        "quarantined_at": reconciled_at,
                    }
                    package_conflict_count += 1
    if not duplicate_count and not package_conflict_count:
        return None
    return {
        "authority": "role_output_event_identity",
        "duplicate_event_records_quarantined": duplicate_count,
        "package_identity_records_quarantined": package_conflict_count,
    }


def quarantine_packet_result_authority_for_terminal_lifecycle(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    *,
    mode: str,
    event: str,
    reconciled_at: str,
) -> dict[str, Any] | None:
    packet_ledger_path = run_root / "packet_ledger.json"
    if not packet_ledger_path.exists():
        return None
    packet_ledger = router.read_json(packet_ledger_path)
    packets = packet_ledger.get("packets")
    if not isinstance(packets, list):
        return None
    quarantined = 0
    for packet in packets:
        if not isinstance(packet, dict):
            continue
        result = packet.get("result_envelope")
        if not isinstance(result, dict):
            continue
        if result.get("completed_agent_id") and result.get("completed_agent_id_belongs_to_role") is not False:
            continue
        result["author_identity_quarantine"] = {
            "status": "terminal_lifecycle_quarantined",
            "event": event,
            "terminal_lifecycle_status": mode,
            "reason": "historical packet result lacked replayable agent identity before user stop",
            "quarantined_at": reconciled_at,
        }
        quarantined += 1
    if not quarantined:
        return None
    router.write_json(packet_ledger_path, packet_ledger)
    return {
        "authority": "packet_result_author_identity",
        "path": router.project_relative(project_root, packet_ledger_path),
        "result_author_identity_records_quarantined": quarantined,
    }


__all__ = (
    "clear_active_repair_transaction_for_terminal_lifecycle",
    "quarantine_duplicate_role_events_for_terminal_lifecycle",
    "quarantine_material_progress_for_terminal_lifecycle",
    "quarantine_packet_result_authority_for_terminal_lifecycle",
)
