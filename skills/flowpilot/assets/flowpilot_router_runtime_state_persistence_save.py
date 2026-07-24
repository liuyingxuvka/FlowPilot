"""Save/load entrypoints split from flowpilot_router_runtime_state_persistence."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import flowpilot_router_runtime_state_persistence as _parent
from flowpilot_router_io_json import write_json_if_changed


for _name, _value in vars(_parent).items():
    if not (_name.startswith("__") and _name.endswith("__")):
        globals().setdefault(_name, _value)


_BOUND_ROUTER: ModuleType | None = None
def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    _parent._bind_router(router)
    current = globals()
    for name, value in vars(_parent).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        current.setdefault(name, value)
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        current[name] = value


def _merge_stale_run_state_save(existing: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    merged = _public_run_state_snapshot(current)
    if existing.get("schema_version") != merged.get("schema_version") or existing.get("run_id") != merged.get("run_id"):
        return merged
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

def save_run_state(router: ModuleType, run_root: Path, state: dict[str, Any]) -> bool:
    _bind_router(router)
    path = router.run_state_path(run_root)
    payload = _public_run_state_snapshot(state)
    loaded_hash = str(state.get(_RUN_STATE_LOAD_META_HASH) or "")
    existing = read_json_if_exists(path)
    if loaded_hash and existing and _run_state_snapshot_hash(existing) != loaded_hash:
        payload = _merge_stale_run_state_save(existing, state)
    written = write_json_if_changed(path, payload)
    state.clear()
    state.update(payload)
    _attach_run_state_load_metadata(state)
    return written
