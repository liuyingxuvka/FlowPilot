"""Startup bootloader receipt policy for Controller scheduler receipts.

Receives the router facade explicitly so startup bootstrap/run-state writes
stay under the existing router-owned boundary.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any


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


def _boot_action_meta(router: ModuleType, action_type: str) -> dict[str, Any] | None:
    _bind_router(router)
    if action_type == "load_router":
        return {
            "action_type": "load_router",
            "flag": "router_loaded",
            "label": "bootloader_router_loaded",
            "actor": "bootloader",
        }
    for item in BOOT_ACTIONS:
        if item.get("action_type") == action_type:
            return item
    return None


def _matching_bootstrap_pending_action(
    router: ModuleType,
    bootstrap_state: dict[str, Any],
    action: dict[str, Any],
) -> bool:
    _bind_router(router)
    pending = bootstrap_state.get("pending_action")
    if not isinstance(pending, dict):
        return False
    for key in ("controller_action_id", "router_scheduler_row_id", "action_id"):
        if pending.get(key) and pending.get(key) == action.get(key):
            return True
    return bool(pending.get("action_type") and pending.get("action_type") == action.get("action_type"))


def _apply_startup_bootloader_receipt_effects(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    action: dict[str, Any],
    receipt_payload: dict[str, Any],
) -> dict[str, Any]:
    _bind_router(router)
    action_type = str(action.get("action_type") or "")
    action_meta = router._boot_action_meta(action_type)
    if action_meta is None:
        return {"applied": False, "reason": "not_bootloader_action"}
    if str(action.get("scope_kind") or "") != "startup" and (not router._daemon_scheduled_bootloader_action(action)):
        return {"applied": False, "reason": "not_startup_bootloader_scheduler_row"}
    bootstrap = router.load_bootstrap_state(project_root, create_if_missing=False)
    flag = str(action_meta.get("flag") or _pending_action_postcondition(action) or "")
    result: dict[str, Any] = {
        "applied": True,
        "source": "startup_bootloader_controller_receipt",
        "postcondition": flag,
        "action_type": action_type,
    }
    terminal_mode = router._terminal_lifecycle_mode(run_state)
    if terminal_mode:
        append_history(
            run_state,
            "startup_bootloader_receipt_ignored_for_terminal_lifecycle",
            {"action_type": action_type, "terminal_lifecycle_status": terminal_mode},
        )
        result.update(
            {
                "source": "terminal_lifecycle_skipped_startup_receipt",
                "terminal_lifecycle_status": terminal_mode,
            }
        )
        return result
    if action_type == "open_startup_intake_ui" and str(receipt_payload.get("source") or "") != "startup_daemon_bootloader_apply":
        result.update(router._apply_startup_intake_result_to_bootstrap(project_root, bootstrap, receipt_payload))
        router._sync_startup_bootstrap_flags_to_run_state(bootstrap, run_state)
    elif action_type == "emit_startup_banner":
        banner = router._startup_banner_display()
        confirmation = router._display_confirmation_for_action(receipt_payload, action)
        banner["dialog_display_confirmation"] = confirmation
        bootstrap["startup_banner_path"] = banner["display_path"]
        bootstrap["startup_banner_display"] = banner
        bootstrap["startup_banner_dialog_display_confirmation"] = confirmation
        run_state.setdefault("flags", {})["banner_emitted"] = True
        result["display_text_sha256"] = confirmation.get("display_text_sha256")
    elif action_type == "load_controller_core":
        if not _formal_router_daemon_ready(project_root, run_root):
            return {
                "applied": False,
                "reason": "startup_router_daemon_not_ready_for_controller_core",
                "action_type": action_type,
                "postcondition": flag,
            }
        router._sync_startup_bootstrap_flags_to_run_state(bootstrap, run_state)
        run_state["status"] = "controller_ready"
        run_state["holder"] = "controller"
        run_state.setdefault("flags", {})["controller_core_loaded"] = True
        boundary_reconciliation = router._record_controller_boundary_confirmation_from_core_load(
            project_root,
            run_root,
            run_state,
            action,
            receipt_payload,
            source="load_controller_core_receipt_reconciliation",
        )
        result["controller_boundary_confirmation"] = boundary_reconciliation.get("controller_boundary_confirmation")
        result["coalesced_postconditions"] = sorted(set(result.get("coalesced_postconditions") or []) | {"controller_role_confirmed"})
        result["source"] = "startup_bootloader_controller_receipt"
    elif str(receipt_payload.get("source") or "") == "startup_daemon_bootloader_apply":
        seed_projection = router._sync_completed_deterministic_startup_seed_to_bootstrap(
            project_root,
            bootstrap,
            source=f"{action_type}_daemon_apply_receipt",
        )
        if seed_projection.get("changed"):
            result["deterministic_seed_projection"] = seed_projection
        bootstrap_flags = bootstrap.get("flags") if isinstance(bootstrap.get("flags"), dict) else {}
        if flag and (not (receipt_payload.get("bootstrap_flag_satisfied") or bootstrap_flags.get(flag))):
            return {
                "applied": False,
                "reason": "startup_bootloader_receipt_postcondition_missing",
                "action_type": action_type,
                "postcondition": flag,
            }
        router._sync_startup_bootstrap_flags_to_run_state(bootstrap, run_state)
        result["bootstrap_flag_satisfied"] = bool(flag and bootstrap_flags.get(flag))
        result["source"] = "startup_bootloader_controller_receipt"
    else:
        return {"applied": False, "reason": "unsupported_startup_bootloader_receipt_action", "action_type": action_type}
    if flag:
        bootstrap.setdefault("flags", {})[flag] = True
        run_state.setdefault("flags", {})[flag] = True
    if router._matching_bootstrap_pending_action(bootstrap, action):
        bootstrap["pending_action"] = None
        result["cleared_bootstrap_pending_action"] = True
    append_history(
        bootstrap,
        "router_reconciled_startup_bootloader_receipt",
        {
            "action_type": action_type,
            "postcondition": flag,
            "controller_action_id": action.get("controller_action_id"),
            "router_scheduler_row_id": action.get("router_scheduler_row_id"),
        },
    )
    router.save_bootstrap_state(project_root, bootstrap)
    router.save_run_state(run_root, run_state)
    return result


__all__ = (
    "_boot_action_meta",
    "_matching_bootstrap_pending_action",
    "_apply_startup_bootloader_receipt_effects",
)

_LOCAL_NAMES = set(globals())
