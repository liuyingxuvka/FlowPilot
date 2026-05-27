"""Role-output event reconciliation helpers for the router bridge."""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType
from typing import Any

import role_output_runtime
from flowpilot_router_errors import RouterError
from flowpilot_router_protocol_catalog import *


def _bind_router(router: ModuleType) -> None:
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


def _startup_fact_canonical_report_is_valid(
    router: ModuleType,
    run_root: Path,
    run_state: dict[str, Any],
) -> bool:
    _bind_router(router)
    report = read_json_if_exists(run_root / "startup" / "startup_fact_report.json")
    return (
        report.get("schema_version") == "flowpilot.startup_fact_report.v1"
        and report.get("run_id") == run_state.get("run_id")
        and report.get("reviewed_by_role") == "human_like_reviewer"
        and report.get("status") in {"pass", "findings"}
    )


def _try_reconcile_startup_fact_role_output_ledger(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
) -> dict[str, Any]:
    _bind_router(router)
    event = "reviewer_reports_startup_facts"
    meta = EXTERNAL_EVENTS[event]
    flag = str(meta["flag"])
    flags = run_state.setdefault("flags", {})
    required_flag = str(meta.get("requires_flag") or "")
    changed = False
    reconciled = 0
    skipped_invalid = 0
    if flags.get(flag) and _run_state_has_event(run_state, event):
        return {"changed": False, "reconciled": 0, "skipped_invalid": 0}
    for record in _role_output_ledger_outputs(router, run_root):
        envelope = record.get("envelope")
        if not isinstance(envelope, dict):
            continue
        if str(envelope.get("event_name") or "") != event:
            continue
        if required_flag and not flags.get(required_flag):
            continue
        try:
            role_output_runtime.validate_envelope_runtime_receipt(project_root, envelope)
        except role_output_runtime.RoleOutputRuntimeError:
            skipped_invalid += 1
            continue
        _preconsume_pending_card_return_ack_before_external_event(
            project_root,
            run_root,
            run_state,
            event=event,
        )
        if _pending_card_return_blocker_for_event(run_root, str(run_state["run_id"]), event, run_state) is not None:
            continue
        if not _startup_fact_canonical_report_is_valid(router, run_root, run_state):
            try:
                _write_startup_fact_report(project_root, run_root, run_state, envelope)
            except (RouterError, role_output_runtime.RoleOutputRuntimeError, OSError, json.JSONDecodeError):
                skipped_invalid += 1
                continue
        if _run_state_has_event(run_state, event):
            if not flags.get(flag):
                flags[flag] = True
                append_history(
                    run_state,
                    "router_synced_startup_fact_flag_from_role_output_ledger",
                    {
                        "event": event,
                        "output_id": record.get("output_id"),
                        "canonical_report_path": project_relative(
                            project_root,
                            run_root / "startup" / "startup_fact_report.json",
                        ),
                    },
                )
                changed = True
                reconciled += 1
            break
        if _record_router_reconciled_external_event(project_root, run_root, run_state, event, envelope):
            changed = True
            reconciled += 1
            break
    return {
        "changed": changed,
        "reconciled": reconciled,
        "skipped_invalid": skipped_invalid,
    }


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
    if event == "pm_records_material_scan_result_disposition":
        try:
            batch = router._active_parallel_packet_batch(run_root, "material_scan")
        except (RouterError, OSError, json.JSONDecodeError, TypeError, ValueError):
            batch = None
        if isinstance(batch, dict) and isinstance(batch.get("pm_result_disposition"), dict):
            return True
        return _run_state_has_event(run_state, event)
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
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(summary, sort_keys=True) + "\n")
    rows.append(summary)
    return summary


def _try_reconcile_direct_role_output_event_ledger(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
) -> dict[str, Any]:
    _bind_router(router)
    flags = run_state.setdefault("flags", {})
    changed = False
    reconciled = 0
    already_recorded = 0
    repair_owned_conflicts = 0
    skipped_invalid = 0
    skipped_not_ready = 0
    skipped_unauthorized = 0
    events: list[str] = []
    for record in _role_output_ledger_outputs(router, run_root):
        envelope = record.get("envelope")
        if not isinstance(envelope, dict):
            continue
        event = str(envelope.get("event_name") or "")
        if not event or event not in EXTERNAL_EVENTS:
            continue
        if event == "reviewer_reports_startup_facts":
            continue
        meta = EXTERNAL_EVENTS[event]
        flag = str(meta["flag"])
        required_flag = str(meta.get("requires_flag") or "")
        scoped_policy = getattr(router, "SCOPED_EVENT_IDENTITY_POLICIES", {}).get(event)
        is_package_disposition_event = (
            isinstance(scoped_policy, dict)
            and scoped_policy.get("family") == "pm_package_disposition"
        )
        required_flag_missing = bool(required_flag and not flags.get(required_flag))
        if required_flag_missing and not is_package_disposition_event:
            skipped_not_ready += 1
            continue
        if not _role_output_event_has_durable_authority(router, run_root, run_state, event):
            skipped_unauthorized += 1
            continue
        try:
            role_output_runtime.validate_envelope_runtime_receipt(project_root, envelope)
            payload = _role_output_body_payload_from_record(router, project_root, record, envelope)
        except (role_output_runtime.RoleOutputRuntimeError, OSError, json.JSONDecodeError, TypeError, ValueError):
            skipped_invalid += 1
            continue
        scoped_identity = _scoped_event_identity(project_root, run_root, run_state, event, payload)
        conflict_classification = _classify_scoped_event_conflict(run_state, scoped_identity)
        if conflict_classification.get("classification") in {
            "terminal_quarantine",
            "pm_repair_owned_stale_conflict",
            "control_blocker_owned_stale_conflict",
        }:
            repair_owned_conflicts += 1
            quarantine = _record_role_output_replay_quarantine(
                router,
                project_root,
                run_root,
                run_state,
                event=event,
                record=record,
                classification=conflict_classification,
            )
            events.append(event)
            if not quarantine.get("already_quarantined"):
                changed = True
                append_history(
                    run_state,
                    "router_skipped_repair_owned_package_disposition_conflict_replay",
                    quarantine,
                )
            continue
        if required_flag_missing:
            skipped_not_ready += 1
            continue
        _preconsume_pending_card_return_ack_before_external_event(
            project_root,
            run_root,
            run_state,
            event=event,
        )
        if _pending_card_return_blocker_for_event(run_root, str(run_state["run_id"]), event, run_state) is not None:
            skipped_not_ready += 1
            continue
        side_effect_changed = _sync_material_review_from_role_output_payload(
            router,
            project_root,
            run_root,
            run_state,
            event,
            payload,
        )
        _check_scoped_event_conflict(run_state, scoped_identity)
        if _scoped_event_is_recorded(run_state, scoped_identity) or (
            flags.get(flag) and _event_allows_run_wide_flag_short_circuit(event, scoped_identity)
        ):
            wait_closure = _close_waiting_controller_actions_for_external_event(
                project_root,
                run_root,
                run_state,
                event=event,
                payload=payload,
                source="role_output_ledger_event_already_recorded",
            )
            if wait_closure.get("changed") or side_effect_changed:
                changed = True
                already_recorded += 1
                events.append(event)
            continue
        if _record_router_reconciled_external_event(project_root, run_root, run_state, event, payload):
            changed = True
            reconciled += 1
            events.append(event)
        elif side_effect_changed:
            changed = True
            already_recorded += 1
            events.append(event)
    if changed:
        append_history(
            run_state,
            "router_reconciled_direct_role_output_event_ledger",
            {
                "reconciled": reconciled,
                "already_recorded": already_recorded,
                "repair_owned_conflicts": repair_owned_conflicts,
                "events": events,
                "skipped_invalid": skipped_invalid,
                "skipped_not_ready": skipped_not_ready,
                "skipped_unauthorized": skipped_unauthorized,
            },
        )
    return {
        "changed": changed,
        "reconciled": reconciled,
        "already_recorded": already_recorded,
        "repair_owned_conflicts": repair_owned_conflicts,
        "events": events,
        "skipped_invalid": skipped_invalid,
        "skipped_not_ready": skipped_not_ready,
        "skipped_unauthorized": skipped_unauthorized,
    }


_LOCAL_NAMES = set(globals())
