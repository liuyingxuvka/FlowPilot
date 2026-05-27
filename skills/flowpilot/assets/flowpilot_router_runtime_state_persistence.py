"""Run-state persistence and stale-save merge helpers for FlowPilot runtime state."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import ModuleType
from typing import Any

from flowpilot_control_plane_contracts import control_plane_pending_wait_same_identity
from flowpilot_router_errors import RouterError

_RUN_STATE_LOAD_META_HASH = "_flowpilot_loaded_run_state_hash"
_RUN_STATE_LOAD_META_FLAGS = "_flowpilot_loaded_run_state_flags"
_RUN_STATE_LOAD_META_PENDING = "_flowpilot_loaded_pending_action"
_RUN_STATE_LOAD_META_ACTIVE_CONTROL_BLOCKER = "_flowpilot_loaded_active_control_blocker"
_RUN_STATE_VOLATILE_META_KEYS = {_RUN_STATE_LOAD_META_HASH, _RUN_STATE_LOAD_META_FLAGS, _RUN_STATE_LOAD_META_PENDING, _RUN_STATE_LOAD_META_ACTIVE_CONTROL_BLOCKER}
_RUN_STATE_APPEND_ONLY_LIST_FIELDS = ("history", "events", "quarantined_role_reports", "control_blockers", "resolved_control_blockers", "protocol_blockers",
                                      "gate_decisions", "delivered_cards", "delivered_mail", "role_output_replay_quarantine")
_RUN_STATE_PENDING_REMINDER_FIELDS = ("last_wait_reminder_at", "last_wait_reminder_sha256", "wait_reminder_text", "wait_reminder_text_sha256",
                                      "last_liveness_probe", "liveness_probe_result")
_MATERIAL_GENERATION_PROGRESS_FLAGS = {"material_scan_packets_relayed", "worker_packets_delivered", "worker_scan_results_returned",
                                       "material_scan_results_relayed_to_pm", "material_scan_result_disposition_recorded",
                                       "material_scan_results_absorbed_by_pm", "material_review_sufficient", "material_review_insufficient"}
_PM_PACKAGE_DISPOSITION_EVENTS = {
    "pm_records_material_scan_result_disposition",
    "pm_records_research_result_disposition",
    "pm_records_current_node_result_disposition",
}


def _bind_router(router: ModuleType) -> None:
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value


def _json_clone(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True))


def _public_run_state_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    return {key: _json_clone(value) for key, value in state.items() if key not in _RUN_STATE_VOLATILE_META_KEYS}


def _material_generation_key(state: dict[str, Any]) -> tuple[str, str, str] | None:
    generation = state.get("active_material_generation")
    if not isinstance(generation, dict):
        return None
    key = (
        str(generation.get("packet_generation_id") or ""),
        str(generation.get("repair_transaction_id") or ""),
        str(generation.get("batch_id") or ""),
    )
    return key if any(key) else None


def _run_state_snapshot_hash(state: dict[str, Any]) -> str:
    public = _public_run_state_snapshot(state)
    return hashlib.sha256(json.dumps(public, sort_keys=True).encode("utf-8")).hexdigest()


def _attach_run_state_load_metadata(state: dict[str, Any]) -> dict[str, Any]:
    state[_RUN_STATE_LOAD_META_HASH] = _run_state_snapshot_hash(state)
    flags = state.get("flags") if isinstance(state.get("flags"), dict) else {}
    state[_RUN_STATE_LOAD_META_FLAGS] = dict(flags)
    pending = state.get("pending_action") if isinstance(state.get("pending_action"), dict) else None
    state[_RUN_STATE_LOAD_META_PENDING] = _json_clone(pending) if pending else None
    active_blocker = state.get("active_control_blocker") if isinstance(state.get("active_control_blocker"), dict) else None
    state[_RUN_STATE_LOAD_META_ACTIVE_CONTROL_BLOCKER] = _json_clone(active_blocker) if active_blocker else None
    return state


def _merge_append_only_run_state_list(existing: list[Any], current: list[Any]) -> list[Any]:
    merged: list[Any] = []
    seen: set[str] = set()
    for item in [*existing, *current]:
        identity = json.dumps(item, sort_keys=True)
        if identity in seen:
            continue
        seen.add(identity)
        merged.append(item)
    return merged


def _scope_body_hash(record: Any) -> str:
    if not isinstance(record, dict):
        return ""
    scope = record.get("scope") if isinstance(record.get("scope"), dict) else {}
    return str(scope.get("body_hash") or "").strip()


def _event_payload_body_hash(event_record: Any) -> str:
    if not isinstance(event_record, dict):
        return ""
    payload = event_record.get("payload") if isinstance(event_record.get("payload"), dict) else {}
    envelope = payload.get("_role_output_envelope") if isinstance(payload.get("_role_output_envelope"), dict) else {}
    for key in ("body_hash", "body_raw_sha256", "body_semantic_sha256"):
        value = str(envelope.get(key) or "").strip()
        if value:
            return value
    return str(payload.get("body_hash") or payload.get("source_body_hash") or "").strip()


def _merge_external_event_idempotency_ledger(existing: Any, current: Any) -> dict[str, Any]:
    existing_ledger = existing if isinstance(existing, dict) else {}
    current_ledger = current if isinstance(current, dict) else {}
    merged = _json_clone(current_ledger) if current_ledger else {}
    if not isinstance(merged, dict):
        merged = {}
    schema_version = existing_ledger.get("schema_version") or current_ledger.get("schema_version")
    if schema_version:
        merged["schema_version"] = schema_version
    merged_processed = merged.get("processed")
    if not isinstance(merged_processed, dict):
        merged_processed = {}
        merged["processed"] = merged_processed
    existing_processed = existing_ledger.get("processed")
    if isinstance(existing_processed, dict):
        for event, existing_keys in existing_processed.items():
            if not isinstance(existing_keys, dict):
                continue
            target_keys = merged_processed.setdefault(event, {})
            if not isinstance(target_keys, dict):
                target_keys = {}
                merged_processed[event] = target_keys
            for dedupe_key, existing_record in existing_keys.items():
                if not isinstance(existing_record, dict):
                    continue
                current_record = target_keys.get(dedupe_key)
                if not isinstance(current_record, dict):
                    target_keys[dedupe_key] = _json_clone(existing_record)
                    continue
                if (
                    str(event) in _PM_PACKAGE_DISPOSITION_EVENTS
                    and _scope_body_hash(existing_record)
                    and _scope_body_hash(current_record)
                    and _scope_body_hash(existing_record) != _scope_body_hash(current_record)
                ):
                    target_keys[dedupe_key] = _json_clone(existing_record)
    existing_attempts = existing_ledger.get("attempts")
    current_attempts = current_ledger.get("attempts")
    if isinstance(existing_attempts, list) and isinstance(current_attempts, list):
        merged["attempts"] = _merge_append_only_run_state_list(existing_attempts, current_attempts)
    elif isinstance(existing_attempts, list) and "attempts" not in merged:
        merged["attempts"] = _json_clone(existing_attempts)
    elif "attempts" not in merged:
        merged["attempts"] = []
    return merged


def _filter_stale_reconciled_package_events(events: Any, idempotency_ledger: Any) -> Any:
    if not isinstance(events, list) or not isinstance(idempotency_ledger, dict):
        return events
    processed = idempotency_ledger.get("processed")
    if not isinstance(processed, dict):
        return events
    authoritative_hashes: dict[str, set[str]] = {}
    for event, records in processed.items():
        if str(event) not in _PM_PACKAGE_DISPOSITION_EVENTS or not isinstance(records, dict):
            continue
        hashes = {body_hash for body_hash in (_scope_body_hash(record) for record in records.values()) if body_hash}
        if hashes:
            authoritative_hashes[str(event)] = hashes
    if not authoritative_hashes:
        return events
    filtered: list[Any] = []
    for item in events:
        event = str(item.get("event") or "") if isinstance(item, dict) else ""
        if event in authoritative_hashes and isinstance(item, dict) and item.get("reconciled_by_router") is True:
            body_hash = _event_payload_body_hash(item)
            if body_hash and body_hash not in authoritative_hashes[event]:
                continue
        filtered.append(item)
    return filtered


def _same_pending_wait_identity(first: dict[str, Any], second: dict[str, Any]) -> bool:
    return control_plane_pending_wait_same_identity(first, second)


def _same_optional_pending_wait_identity(first: Any, second: Any) -> bool:
    first_pending = first if isinstance(first, dict) else None
    second_pending = second if isinstance(second, dict) else None
    if first_pending is None or second_pending is None:
        return first_pending is None and second_pending is None
    return _same_pending_wait_identity(first_pending, second_pending)


def _same_active_control_blocker_identity(first: dict[str, Any], second: dict[str, Any]) -> bool:
    first_key = str(first.get("blocker_id") or first.get("blocker_artifact_path") or "")
    second_key = str(second.get("blocker_id") or second.get("blocker_artifact_path") or "")
    if first_key and second_key:
        return first_key == second_key
    return first == second


def _same_optional_active_control_blocker_identity(first: Any, second: Any) -> bool:
    first_blocker = first if isinstance(first, dict) else None
    second_blocker = second if isinstance(second, dict) else None
    if first_blocker is None or second_blocker is None:
        return first_blocker is None and second_blocker is None
    return _same_active_control_blocker_identity(first_blocker, second_blocker)


def _merge_pending_wait_reminder_state(existing: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(existing, dict) or not isinstance(current, dict):
        return current
    if not _same_pending_wait_identity(existing, current):
        return current
    merged = dict(current)
    for field in _RUN_STATE_PENDING_REMINDER_FIELDS:
        if existing.get(field) not in (None, "", []) and merged.get(field) in (None, "", []):
            merged[field] = existing.get(field)
    existing_history = existing.get("wait_reminder_history")
    current_history = current.get("wait_reminder_history")
    if isinstance(existing_history, list) and isinstance(current_history, list):
        merged["wait_reminder_history"] = _merge_append_only_run_state_list(existing_history, current_history)
    elif isinstance(existing_history, list) and "wait_reminder_history" not in merged:
        merged["wait_reminder_history"] = existing_history
    return merged


def _merge_stale_pending_action_projection(existing: Any, current: Any, loaded: Any) -> dict[str, Any] | None:
    existing_pending = existing if isinstance(existing, dict) else None
    current_pending = current if isinstance(current, dict) else None
    loaded_pending = loaded if isinstance(loaded, dict) else None
    if existing_pending is not None and current_pending is not None:
        if _same_pending_wait_identity(existing_pending, current_pending):
            return _merge_pending_wait_reminder_state(existing_pending, current_pending)
        current_is_unchanged = _same_optional_pending_wait_identity(current_pending, loaded_pending)
        existing_is_unchanged = _same_optional_pending_wait_identity(existing_pending, loaded_pending)
        if current_is_unchanged and not existing_is_unchanged:
            return existing_pending
        if existing_is_unchanged and not current_is_unchanged:
            return current_pending
        return existing_pending
    if existing_pending is not None and current_pending is None:
        if loaded_pending is not None and _same_pending_wait_identity(existing_pending, loaded_pending):
            return None
        if loaded_pending is None:
            return existing_pending
        return existing_pending
    if existing_pending is None and current_pending is not None:
        if loaded_pending is not None and _same_pending_wait_identity(current_pending, loaded_pending):
            return None
        return current_pending
    return None


def _merge_stale_active_control_blocker_projection(existing: Any, current: Any, loaded: Any) -> dict[str, Any] | None:
    existing_blocker = existing if isinstance(existing, dict) else None
    current_blocker = current if isinstance(current, dict) else None
    loaded_blocker = loaded if isinstance(loaded, dict) else None
    if existing_blocker is not None and current_blocker is not None:
        current_is_unchanged = _same_optional_active_control_blocker_identity(current_blocker, loaded_blocker)
        existing_is_unchanged = _same_optional_active_control_blocker_identity(existing_blocker, loaded_blocker)
        if current_is_unchanged and not existing_is_unchanged:
            return _json_clone(existing_blocker)
        if existing_is_unchanged and not current_is_unchanged:
            return _json_clone(current_blocker)
        return _json_clone(existing_blocker)
    if existing_blocker is not None and current_blocker is None:
        if loaded_blocker is not None and _same_active_control_blocker_identity(existing_blocker, loaded_blocker):
            return None
        return _json_clone(existing_blocker)
    if existing_blocker is None and current_blocker is not None:
        if loaded_blocker is not None and _same_active_control_blocker_identity(current_blocker, loaded_blocker):
            return None
        return _json_clone(current_blocker)
    return None


def _merge_stale_run_state_save(existing: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    merged = _public_run_state_snapshot(current)
    if existing.get("schema_version") != merged.get("schema_version") or existing.get("run_id") != merged.get("run_id"):
        return merged
    existing_material_generation_key = _material_generation_key(existing)
    current_material_generation_key = _material_generation_key(current)
    existing_has_newer_material_generation = bool(
        existing_material_generation_key
        and existing_material_generation_key != current_material_generation_key
    )
    if existing_has_newer_material_generation:
        merged["active_material_generation"] = _json_clone(existing.get("active_material_generation"))
    for field in _RUN_STATE_APPEND_ONLY_LIST_FIELDS:
        existing_items = existing.get(field)
        current_items = merged.get(field)
        if isinstance(existing_items, list) and isinstance(current_items, list):
            merged[field] = _merge_append_only_run_state_list(existing_items, current_items)
    merged["external_event_idempotency"] = _merge_external_event_idempotency_ledger(
        existing.get("external_event_idempotency"),
        merged.get("external_event_idempotency"),
    )
    merged["events"] = _filter_stale_reconciled_package_events(
        merged.get("events"),
        merged.get("external_event_idempotency"),
    )
    loaded_flags = current.get(_RUN_STATE_LOAD_META_FLAGS)
    loaded_flags = loaded_flags if isinstance(loaded_flags, dict) else {}
    existing_flags = existing.get("flags") if isinstance(existing.get("flags"), dict) else {}
    merged_flags = merged.setdefault("flags", {})
    if isinstance(merged_flags, dict):
        for flag, existing_value in existing_flags.items():
            if existing_has_newer_material_generation and flag in _MATERIAL_GENERATION_PROGRESS_FLAGS:
                merged_flags[flag] = bool(existing_value)
                continue
            loaded_value = loaded_flags.get(flag)
            current_value = merged_flags.get(flag)
            if existing_value is True and loaded_value is not True and current_value is not True:
                merged_flags[flag] = True
    merged["pending_action"] = _merge_stale_pending_action_projection(
        existing.get("pending_action"),
        merged.get("pending_action"),
        current.get(_RUN_STATE_LOAD_META_PENDING),
    )
    merged_active_blocker = _merge_stale_active_control_blocker_projection(
        existing.get("active_control_blocker"),
        merged.get("active_control_blocker"),
        current.get(_RUN_STATE_LOAD_META_ACTIVE_CONTROL_BLOCKER),
    )
    merged["active_control_blocker"] = merged_active_blocker
    if isinstance(merged_active_blocker, dict):
        if _same_optional_active_control_blocker_identity(merged_active_blocker, existing.get("active_control_blocker")):
            merged["latest_control_blocker_path"] = existing.get("latest_control_blocker_path")
        elif not merged.get("latest_control_blocker_path"):
            merged["latest_control_blocker_path"] = merged_active_blocker.get("blocker_artifact_path")
    else:
        merged["latest_control_blocker_path"] = None
    return merged


def _normalize_run_state_defaults(state: dict[str, Any]) -> None:
    state.setdefault("flags", {})
    for flag, default in RUNTIME_FLAG_DEFAULTS.items():
        state["flags"].setdefault(flag, default)
    for entry in SYSTEM_CARD_SEQUENCE:
        state["flags"].setdefault(entry["flag"], False)
    for entry in MAIL_SEQUENCE:
        state["flags"].setdefault(entry["flag"], False)
    for event in EXTERNAL_EVENTS.values():
        state["flags"].setdefault(event["flag"], False)
    state.setdefault("history", [])
    state.setdefault("pending_action", None)
    state.setdefault("daemon_mode_enabled", False)
    state.setdefault("router_daemon_status_path", None)
    state.setdefault("controller_action_ledger_path", None)
    state.setdefault("router_ownership_ledger_path", None)
    state.setdefault("delivered_cards", [])
    state.setdefault("delivered_mail", [])
    state.setdefault("control_blockers", [])
    state.setdefault("resolved_control_blockers", [])
    state.setdefault("blocker_repair_attempts", {})
    state.setdefault("blocker_repair_policy_snapshot", None)
    state.setdefault("protocol_blockers", [])
    state.setdefault("gate_decisions", [])
    state.setdefault("quarantined_role_reports", [])
    state.setdefault("active_control_blocker", None)
    state.setdefault("latest_control_blocker_path", None)
    state.setdefault("events", [])


def load_run_state(router: ModuleType, project_root: Path, bootstrap_state: dict[str, Any] | None = None) -> tuple[dict[str, Any], Path] | tuple[None, None]:
    _bind_router(router)
    run_root = router.active_run_root(project_root, bootstrap_state)
    if run_root is None:
        return (None, None)
    path = router.run_state_path(run_root)
    if not path.exists():
        return (None, run_root)
    state = read_json(path)
    _normalize_run_state_defaults(state)
    _attach_run_state_load_metadata(state)
    return (state, run_root)


def load_run_state_from_run_root(router: ModuleType, project_root: Path, run_root: Path) -> tuple[dict[str, Any], Path] | tuple[None, Path]:
    _bind_router(router)
    run_root = run_root.resolve()
    path = router.run_state_path(run_root)
    if not path.exists():
        return (None, run_root)
    state = read_json(path)
    expected_root = project_relative(project_root, run_root)
    state_root = str(state.get("run_root") or "")
    state_id = str(state.get("run_id") or "")
    if state_root and state_root != expected_root:
        raise RouterError(f"bound run state root mismatch: expected {expected_root}, found {state_root}")
    if state_id and run_root.name != state_id:
        raise RouterError(f"bound run state id mismatch: expected {run_root.name}, found {state_id}")
    _normalize_run_state_defaults(state)
    _attach_run_state_load_metadata(state)
    return (state, run_root)


def save_run_state(router: ModuleType, run_root: Path, state: dict[str, Any]) -> None:
    _bind_router(router)
    path = router.run_state_path(run_root)
    payload = _public_run_state_snapshot(state)
    loaded_hash = str(state.get(_RUN_STATE_LOAD_META_HASH) or "")
    existing = read_json_if_exists(path)
    if loaded_hash and existing and _run_state_snapshot_hash(existing) != loaded_hash:
        payload = _merge_stale_run_state_save(existing, state)
    write_json(path, payload)
    state.clear()
    state.update(payload)
    _attach_run_state_load_metadata(state)


__all__ = ("_RUN_STATE_LOAD_META_HASH", "_RUN_STATE_LOAD_META_FLAGS", "_RUN_STATE_LOAD_META_PENDING",
           "_RUN_STATE_LOAD_META_ACTIVE_CONTROL_BLOCKER", "_json_clone", "_public_run_state_snapshot", "_run_state_snapshot_hash",
           "_attach_run_state_load_metadata", "_merge_append_only_run_state_list", "_same_pending_wait_identity",
           "_same_optional_pending_wait_identity", "_merge_pending_wait_reminder_state", "_merge_stale_pending_action_projection",
           "_merge_stale_run_state_save", "load_run_state", "load_run_state_from_run_root", "save_run_state")

_LOCAL_NAMES = set(globals())
