"""Role-output event reconciliation helpers for the router bridge."""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType
from typing import Any

import role_output_runtime
from flowpilot_runtime_gateway import GATEWAY_ROUTER_JSON, assert_runtime_gateway_write
from flowpilot_router_errors import RouterError
from flowpilot_router_protocol_catalog import *


_PACKAGE_DISPOSITION_BATCH_KIND_BY_EVENT = {
    "pm_records_material_scan_result_disposition": "material_scan",
    "pm_records_research_result_disposition": "research",
    "pm_records_current_node_result_disposition": "current_node",
}


_BOUND_ROUTER: ModuleType | None = None
def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value


def _role_output_ledger_outputs(router: ModuleType, run_root: Path) -> list[dict[str, Any]]:
    _bind_router(router)
    ledger = read_json_if_exists(run_root / "role_output_ledger.json")
    outputs = ledger.get("outputs") if isinstance(ledger.get("outputs"), list) else []
    return [item for item in outputs if isinstance(item, dict)]


def _role_output_body_payload_from_record(
    router: ModuleType,
    project_root: Path,
    record: dict[str, Any],
    envelope: dict[str, Any],
) -> dict[str, Any]:
    _bind_router(router)
    body_path = ""
    body_ref = envelope.get("body_ref")
    if isinstance(body_ref, dict):
        body_path = str(body_ref.get("path") or "")
    if not body_path:
        for key in ("body_path", "report_path", "decision_path", "result_body_path"):
            value = envelope.get(key)
            if isinstance(value, str) and value.strip():
                body_path = value
                break
    if not body_path:
        body_path = str(record.get("body_path") or "")
    payload: dict[str, Any] = {}
    if body_path:
        resolved = resolve_project_path(project_root, body_path)
        loaded = read_json_if_exists(resolved)
        if isinstance(loaded, dict):
            payload = dict(loaded)
    payload["_role_output_envelope"] = envelope
    return payload


def _role_output_event_has_durable_authority(
    router: ModuleType,
    run_root: Path,
    run_state: dict[str, Any],
    event: str,
) -> bool:
    _bind_router(router)
    meta = EXTERNAL_EVENTS.get(event)
    if not isinstance(meta, dict):
        return False
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    package_batch_kind = _PACKAGE_DISPOSITION_BATCH_KIND_BY_EVENT.get(event)
    if package_batch_kind:
        try:
            batch = router._active_parallel_packet_batch(run_root, package_batch_kind)
        except (RouterError, OSError, json.JSONDecodeError, TypeError, ValueError):
            batch = None
        if isinstance(batch, dict) and isinstance(batch.get("pm_result_disposition"), dict):
            return True
        if _run_state_has_event(run_state, event):
            return True
    if flags.get(meta.get("flag")) or _run_state_has_event(run_state, event):
        return True
    pending = run_state.get("pending_action")
    if isinstance(pending, dict) and pending.get("action_type") == "await_role_decision":
        allowed = [str(item) for item in (pending.get("allowed_external_events") or []) if isinstance(item, str)]
        if event in allowed:
            return True
    action_dir = _controller_actions_dir(run_root)
    if action_dir.exists():
        for action_path in sorted(action_dir.glob("*.json")):
            entry = _read_json_for_runtime_scan(action_path)
            if not isinstance(entry, dict) or entry.get("schema_version") != CONTROLLER_ACTION_SCHEMA:
                continue
            if str(entry.get("action_type") or "") != "await_role_decision":
                continue
            if event in _controller_wait_allowed_external_events(entry):
                return True
    try:
        groups = _pending_expected_external_event_groups(run_state)
    except (RouterError, TypeError, ValueError):
        groups = []
    for group in groups or []:
        try:
            allowed_group = _gate_completion_wait_group(group)
        except (RouterError, TypeError, ValueError):
            continue
        if any(event == item_event for item_event, _meta in allowed_group):
            return True
    return False


def _event_allows_run_wide_flag_short_circuit(event: str, scoped_identity: dict[str, Any] | None) -> bool:
    if event in {ROLE_WORK_RESULT_RETURNED_EVENT, "worker_current_node_result_returned"}:
        return False
    if (
        scoped_identity is not None
        and scoped_identity.get("family") == "pm_package_disposition"
    ):
        return False
    return True


def _sync_material_review_from_role_output_payload(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    event: str,
    payload: dict[str, Any],
) -> bool:
    _bind_router(router)
    if event not in {"reviewer_reports_material_sufficient", "reviewer_reports_material_insufficient"}:
        return False
    sufficient = event == "reviewer_reports_material_sufficient"
    review_value = "sufficient" if sufficient else "insufficient"
    report = read_json_if_exists(run_root / "material" / "material_sufficiency_report.json")
    report_already_synced = (
        report.get("schema_version") == "flowpilot.material_sufficiency_report.v1"
        and report.get("run_id") == run_state.get("run_id")
        and report.get("reviewed_by_role") == "human_like_reviewer"
        and report.get("sufficient") is sufficient
    )
    if report_already_synced and run_state.get("material_review") == review_value:
        return False
    changed = run_state.get("material_review") != review_value
    try:
        _write_material_sufficiency_report(project_root, run_root, run_state, payload, sufficient=sufficient)
        changed = True
    except (RouterError, role_output_runtime.RoleOutputRuntimeError, OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        if run_state.get("material_review") == review_value:
            return False
        run_state["material_review"] = review_value
        append_history(
            run_state,
            "router_synced_material_review_projection_from_role_output_ledger",
            {
                "event": event,
                "material_review": review_value,
                "canonical_report_written": False,
                "canonical_report_error": str(exc),
            },
        )
        return True
    run_state["material_review"] = review_value
    material_batch = _active_parallel_packet_batch(run_root, "material_scan")
    if material_batch:
        try:
            _mark_parallel_batch_reviewed(
                run_root,
                "material_scan",
                passed=sufficient,
                reviewed_packet_ids=[
                    str(item.get("packet_id"))
                    for item in material_batch.get("packets", [])
                    if isinstance(item, dict) and item.get("packet_id")
                ],
            )
            changed = True
        except (RouterError, OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    return changed


def _record_role_output_replay_quarantine(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, event: str, record: dict[str, Any], classification: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    output_id = str(record.get("output_id") or "")
    key = "|".join((event, str(classification.get("classification") or ""), str(classification.get("dedupe_key") or ""), output_id))
    rows = run_state.setdefault("role_output_replay_quarantine", [])
    if isinstance(rows, list):
        existing = next((item for item in rows if isinstance(item, dict) and item.get("quarantine_key") == key), None)
        if isinstance(existing, dict):
            return {**existing, "already_quarantined": True}
    else:
        rows = []
        run_state["role_output_replay_quarantine"] = rows
    path = run_root / "runtime" / "role_output_replay_quarantine.jsonl"
    summary = {
        "schema_version": "flowpilot.role_output_replay_quarantine.v1",
        "status": "quarantined_audit_only",
        "quarantine_key": key,
        "event": event,
        "classification": classification.get("classification"),
        "dedupe_key": classification.get("dedupe_key"),
        "mismatches": classification.get("mismatches") or [],
        "owner": classification.get("owner"),
        "output_id": output_id or None,
        "quarantined_at": router.utc_now(),
        "quarantine_path": router.project_relative(project_root, path),
    }
    assert_runtime_gateway_write(path, GATEWAY_ROUTER_JSON, operation="append_role_output_replay_quarantine")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(summary, sort_keys=True) + "\n")
    rows.append(summary)
    return summary


def _canonical_pm_package_disposition_authority(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    event: str,
) -> dict[str, Any] | None:
    _bind_router(router)
    batch_kind = _PACKAGE_DISPOSITION_BATCH_KIND_BY_EVENT.get(event)
    if not batch_kind:
        return None
    try:
        batch = router._active_parallel_packet_batch(run_root, batch_kind)
    except (RouterError, OSError, json.JSONDecodeError, TypeError, ValueError):
        batch = None
    if not isinstance(batch, dict):
        return None
    disposition = batch.get("pm_result_disposition")
    if not isinstance(disposition, dict):
        return None
    source_body_hash = str(disposition.get("source_body_hash") or "").strip()
    decision_path = str(disposition.get("decision_path") or "").strip()
    artifact: dict[str, Any] = {}
    if decision_path:
        try:
            loaded = read_json_if_exists(resolve_project_path(project_root, decision_path))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            loaded = {}
        if isinstance(loaded, dict):
            artifact = loaded
            if not source_body_hash:
                source_body_hash = str(loaded.get("source_body_hash") or "").strip()
    if not source_body_hash:
        return None
    records = [item for item in batch.get("packets") or [] if isinstance(item, dict)]
    generation_ids = sorted({str(item.get("packet_generation_id") or "") for item in records if item.get("packet_generation_id")})
    return {
        "authority": "canonical_pm_package_disposition",
        "batch_kind": batch_kind,
        "batch_id": str(batch.get("batch_id") or ""),
        "packet_ids": sorted(str(item.get("packet_id") or "") for item in records if item.get("packet_id")),
        "packet_generation_id": (
            str((artifact.get("material_generation") or {}).get("current_generation_id") or "")
            if isinstance(artifact.get("material_generation"), dict)
            else ""
        ) or str(artifact.get("packet_generation_id") or "") or (",".join(generation_ids) if generation_ids else ""),
        "decision": disposition.get("decision") or artifact.get("decision"),
        "decision_path": decision_path or None,
        "source_body_hash": source_body_hash,
    }


def _classify_stale_unowned_pm_package_replay(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    event: str,
    scoped_identity: dict[str, Any] | None,
    conflict_classification: dict[str, Any],
) -> dict[str, Any] | None:
    _bind_router(router)
    if not isinstance(scoped_identity, dict):
        return None
    if scoped_identity.get("family") != "pm_package_disposition":
        return None
    if conflict_classification.get("classification") in {
        "terminal_quarantine",
        "pm_repair_owned_stale_conflict",
        "control_blocker_owned_stale_conflict",
        "unknown_corruption",
    }:
        return None
    authority = _canonical_pm_package_disposition_authority(router, project_root, run_root, event)
    if authority is None:
        return None
    scope = scoped_identity.get("scope") if isinstance(scoped_identity.get("scope"), dict) else {}
    replay_body_hash = str(scope.get("body_hash") or "").strip()
    canonical_body_hash = str(authority.get("source_body_hash") or "").strip()
    if not replay_body_hash or not canonical_body_hash or replay_body_hash == canonical_body_hash:
        return None
    return {
        "classification": "canonical_package_authority_stale_conflict",
        "event": event,
        "dedupe_key": scoped_identity.get("dedupe_key"),
        "family": scoped_identity.get("family"),
        "mismatches": ["body_hash"],
        "old_scope": {
            "body_hash": canonical_body_hash,
            "batch_kind": authority.get("batch_kind"),
            "batch_id": authority.get("batch_id"),
            "packet_ids": ",".join(authority.get("packet_ids") or []),
            "packet_generation_id": authority.get("packet_generation_id"),
        },
        "new_scope": scope,
        "owner": authority,
        "replay_source": "role_output_ledger",
        "previous_classification": conflict_classification.get("classification"),
    }








from flowpilot_router_role_output_bridge_events_replay import (
    _package_disposition_authority_split,
    _record_package_disposition_authority_split,
    _try_reconcile_direct_role_output_event_ledger,
)
_LOCAL_NAMES = set(globals())
