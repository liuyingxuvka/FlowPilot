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
_RUN_STATE_VOLATILE_META_KEYS = {
    _RUN_STATE_LOAD_META_HASH,
    _RUN_STATE_LOAD_META_FLAGS,
    _RUN_STATE_LOAD_META_PENDING,
}
_RUN_STATE_APPEND_ONLY_LIST_FIELDS = (
    "history",
    "events",
    "quarantined_role_reports",
    "control_blockers",
    "resolved_control_blockers",
    "protocol_blockers",
    "gate_decisions",
    "delivered_cards",
    "delivered_mail",
)
_RUN_STATE_PENDING_REMINDER_FIELDS = (
    "last_wait_reminder_at",
    "last_wait_reminder_sha256",
    "wait_reminder_text",
    "wait_reminder_text_sha256",
    "last_liveness_probe",
    "liveness_probe_result",
)


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


def _run_state_snapshot_hash(state: dict[str, Any]) -> str:
    public = _public_run_state_snapshot(state)
    return hashlib.sha256(json.dumps(public, sort_keys=True).encode("utf-8")).hexdigest()


def _attach_run_state_load_metadata(state: dict[str, Any]) -> dict[str, Any]:
    state[_RUN_STATE_LOAD_META_HASH] = _run_state_snapshot_hash(state)
    flags = state.get("flags") if isinstance(state.get("flags"), dict) else {}
    state[_RUN_STATE_LOAD_META_FLAGS] = dict(flags)
    pending = state.get("pending_action") if isinstance(state.get("pending_action"), dict) else None
    state[_RUN_STATE_LOAD_META_PENDING] = _json_clone(pending) if pending else None
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


def _same_pending_wait_identity(first: dict[str, Any], second: dict[str, Any]) -> bool:
    return control_plane_pending_wait_same_identity(first, second)


def _same_optional_pending_wait_identity(first: Any, second: Any) -> bool:
    first_pending = first if isinstance(first, dict) else None
    second_pending = second if isinstance(second, dict) else None
    if first_pending is None or second_pending is None:
        return first_pending is None and second_pending is None
    return _same_pending_wait_identity(first_pending, second_pending)


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


def _merge_stale_run_state_save(existing: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    merged = _public_run_state_snapshot(current)
    if existing.get("schema_version") != merged.get("schema_version") or existing.get("run_id") != merged.get("run_id"):
        return merged
    for field in _RUN_STATE_APPEND_ONLY_LIST_FIELDS:
        existing_items = existing.get(field)
        current_items = merged.get(field)
        if isinstance(existing_items, list) and isinstance(current_items, list):
            merged[field] = _merge_append_only_run_state_list(existing_items, current_items)
    loaded_flags = current.get(_RUN_STATE_LOAD_META_FLAGS)
    loaded_flags = loaded_flags if isinstance(loaded_flags, dict) else {}
    existing_flags = existing.get("flags") if isinstance(existing.get("flags"), dict) else {}
    merged_flags = merged.setdefault("flags", {})
    if isinstance(merged_flags, dict):
        for flag, existing_value in existing_flags.items():
            loaded_value = loaded_flags.get(flag)
            current_value = merged_flags.get(flag)
            if existing_value is True and loaded_value is not True and current_value is not True:
                merged_flags[flag] = True
    merged["pending_action"] = _merge_stale_pending_action_projection(
        existing.get("pending_action"),
        merged.get("pending_action"),
        current.get(_RUN_STATE_LOAD_META_PENDING),
    )
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


__all__ = (
    "_RUN_STATE_LOAD_META_HASH",
    "_RUN_STATE_LOAD_META_FLAGS",
    "_RUN_STATE_LOAD_META_PENDING",
    "_json_clone",
    "_public_run_state_snapshot",
    "_run_state_snapshot_hash",
    "_attach_run_state_load_metadata",
    "_merge_append_only_run_state_list",
    "_same_pending_wait_identity",
    "_same_optional_pending_wait_identity",
    "_merge_pending_wait_reminder_state",
    "_merge_stale_pending_action_projection",
    "_merge_stale_run_state_save",
    "load_run_state",
    "load_run_state_from_run_root",
    "save_run_state",
)

_LOCAL_NAMES = set(globals())
