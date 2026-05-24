"""Packet and result record evidence checks for Controller receipt folds."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import packet_runtime
from flowpilot_router_errors import RouterError
import flowpilot_router_controller_scheduler_receipts_packet_fold_evidence as _packet_fold_evidence
from flowpilot_router_controller_scheduler_receipts_packet_fold_evidence import (
    _active_holder_lease_evidence,
    _packet_ledger_record_for_envelope,
    _parallel_batch_packet_evidence,
)


def _bind_router(router: ModuleType) -> None:
    _packet_fold_evidence._bind_router(router)
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value


def _packet_dispatch_record_evidence(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    spec: dict[str, str],
    action: dict[str, Any],
    record: dict[str, Any],
) -> dict[str, Any]:
    _bind_router(router)
    packet_id = str(record.get("packet_id") or "").strip()
    if not packet_id:
        return {"ok": False, "reason": "packet_record_missing_packet_id"}
    try:
        envelope_path = router._packet_envelope_path_from_record(project_root, run_state, record)
        envelope = packet_runtime.load_envelope(project_root, envelope_path)
    except (RouterError, OSError, ValueError, packet_runtime.PacketRuntimeError) as exc:
        return {"ok": False, "packet_id": packet_id, "reason": "packet_envelope_unreadable", "error": str(exc)}
    expected_role = str(envelope.get("to_role") or record.get("to_role") or "").strip()
    if not expected_role:
        return {"ok": False, "packet_id": packet_id, "reason": "packet_record_missing_target_role"}
    try:
        relay = packet_runtime.verify_controller_relay(envelope, recipient_role=expected_role)
    except packet_runtime.PacketRuntimeError as exc:
        return {
            "ok": False,
            "packet_id": packet_id,
            "reason": "packet_runtime_relay_evidence_missing",
            "controller_relay_error": str(exc),
            "packet_envelope_path": project_relative(project_root, envelope_path),
        }
    try:
        ledger_record, ledger_path = _packet_ledger_record_for_envelope(project_root, envelope)
    except (OSError, ValueError, packet_runtime.PacketRuntimeError) as exc:
        return {
            "ok": False,
            "packet_id": packet_id,
            "reason": "packet_ledger_record_missing",
            "error": str(exc),
            "packet_envelope_path": project_relative(project_root, envelope_path),
        }
    if not isinstance(ledger_record, dict):
        return {"ok": False, "packet_id": packet_id, "reason": "packet_ledger_record_missing"}
    if not isinstance(ledger_record.get("packet_controller_relay"), dict):
        return {
            "ok": False,
            "packet_id": packet_id,
            "reason": "packet_ledger_controller_relay_missing",
            "packet_ledger_path": project_relative(project_root, ledger_path),
        }
    holder_matches = str(ledger_record.get("active_packet_holder") or "") == expected_role
    opened_by_expected = str(ledger_record.get("packet_body_opened_by_role") or "") == expected_role
    result_recorded = bool(ledger_record.get("result_envelope_path") or ledger_record.get("result_body_path"))
    if not (holder_matches or opened_by_expected or result_recorded):
        return {
            "ok": False,
            "packet_id": packet_id,
            "reason": "packet_ledger_relay_holder_mismatch",
            "expected_holder": expected_role,
            "actual_holder": ledger_record.get("active_packet_holder"),
            "packet_ledger_path": project_relative(project_root, ledger_path),
        }
    lease_evidence = _active_holder_lease_evidence(project_root, packet_id, expected_role, action)
    if lease_evidence.get("required") and not lease_evidence.get("ok"):
        return {"ok": False, "packet_id": packet_id, **lease_evidence}
    evidence: list[dict[str, Any]] = [
        {"source": "packet_controller_relay", "relayed_at": relay.get("relayed_at")},
        {
            "source": "packet_ledger_controller_relay",
            "active_packet_holder": ledger_record.get("active_packet_holder"),
            "active_packet_status": ledger_record.get("active_packet_status"),
            "packet_ledger_path": project_relative(project_root, ledger_path),
        },
    ]
    if lease_evidence.get("ok"):
        evidence.append({key: value for key, value in lease_evidence.items() if key not in {"required", "ok"}})
    try:
        open_record = packet_runtime.verify_packet_open_receipt(project_root, envelope, role=expected_role)
        evidence.append({"source": "packet_open_receipt", "opened_by_role": open_record.get("packet_body_opened_by_role")})
    except packet_runtime.PacketRuntimeError:
        pass
    batch_evidence = _parallel_batch_packet_evidence(router, run_root, spec, packet_id)
    if batch_evidence:
        evidence.append(batch_evidence)
    return {
        "ok": True,
        "packet_id": packet_id,
        "target_role": expected_role,
        "packet_envelope_path": project_relative(project_root, envelope_path),
        "evidence": evidence,
    }

def _result_relay_record_evidence(
    router: ModuleType,
    project_root: Path,
    run_state: dict[str, Any],
    spec: dict[str, str],
    record: dict[str, Any],
    action: dict[str, Any],
) -> dict[str, Any]:
    _bind_router(router)
    packet_id = str(record.get("packet_id") or "").strip()
    if not packet_id:
        return {"ok": False, "reason": "packet_record_missing_packet_id"}
    expected_role = str(action.get("to_role") or spec.get("to_role") or "").strip()
    if not expected_role:
        return {"ok": False, "packet_id": packet_id, "reason": "result_relay_missing_expected_recipient"}
    try:
        result_path = router._result_envelope_path_from_packet_record(project_root, run_state, record)
        result = packet_runtime.load_envelope(project_root, result_path)
    except (RouterError, OSError, ValueError, packet_runtime.PacketRuntimeError) as exc:
        return {"ok": False, "packet_id": packet_id, "reason": "result_envelope_unreadable", "error": str(exc)}
    if str(result.get("next_recipient") or "") != expected_role:
        return {
            "ok": False,
            "packet_id": packet_id,
            "reason": "result_relay_wrong_next_recipient",
            "expected_recipient": expected_role,
            "actual_recipient": result.get("next_recipient"),
        }
    try:
        relay = packet_runtime.verify_controller_relay(result, recipient_role=expected_role)
    except packet_runtime.PacketRuntimeError as exc:
        return {
            "ok": False,
            "packet_id": packet_id,
            "reason": "result_relay_evidence_missing",
            "controller_relay_error": str(exc),
        }
    try:
        ledger_record, ledger_path = _packet_ledger_record_for_envelope(project_root, result)
    except (OSError, ValueError, packet_runtime.PacketRuntimeError) as exc:
        return {
            "ok": False,
            "packet_id": packet_id,
            "reason": "result_ledger_record_missing",
            "error": str(exc),
            "result_envelope_path": project_relative(project_root, result_path),
        }
    if not isinstance(ledger_record, dict):
        return {"ok": False, "packet_id": packet_id, "reason": "result_ledger_record_missing"}
    if not isinstance(ledger_record.get("result_controller_relay"), dict):
        return {
            "ok": False,
            "packet_id": packet_id,
            "reason": "result_ledger_controller_relay_missing",
            "packet_ledger_path": project_relative(project_root, ledger_path),
        }
    holder_matches = str(ledger_record.get("active_packet_holder") or "") == expected_role
    opened_by_expected = str(ledger_record.get("result_body_opened_by_role") or "") == expected_role
    if not (holder_matches or opened_by_expected):
        return {
            "ok": False,
            "packet_id": packet_id,
            "reason": "result_ledger_relay_holder_mismatch",
            "expected_holder": expected_role,
            "actual_holder": ledger_record.get("active_packet_holder"),
            "packet_ledger_path": project_relative(project_root, ledger_path),
        }
    return {
        "ok": True,
        "packet_id": packet_id,
        "target_role": expected_role,
        "result_envelope_path": project_relative(project_root, result_path),
        "evidence": [
            {"source": "result_controller_relay", "relayed_at": relay.get("relayed_at")},
            {
                "source": "packet_ledger_result_controller_relay",
                "active_packet_holder": ledger_record.get("active_packet_holder"),
                "active_packet_status": ledger_record.get("active_packet_status"),
                "packet_ledger_path": project_relative(project_root, ledger_path),
            },
        ],
    }

__all__ = (
    "_packet_dispatch_record_evidence",
    "_result_relay_record_evidence",
)

_LOCAL_NAMES = set(globals())
