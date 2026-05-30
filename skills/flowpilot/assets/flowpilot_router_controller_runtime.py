"""Router skeleton owner helpers for flowpilot_router_controller_runtime.

These helpers were moved out of ``flowpilot_router.py`` during the final
StructureMesh skeleton cleanup. The module is bound to the router skeleton
before execution so cross-owner transitional lookups stay explicit.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Iterable

import card_runtime
import flowpilot_runtime_closure
import flowpilot_user_flow_diagram
import packet_runtime
import role_output_runtime
import flowpilot_router_action_handlers
import flowpilot_router_action_providers
import flowpilot_router_card_returns
import flowpilot_router_daemon_runtime
import flowpilot_router_event_dispatcher
import flowpilot_router_events
import flowpilot_router_resume
import flowpilot_router_startup_flow
from flowpilot_prompt_store import PromptStoreError, card_manifest_entry, load_card_manifest_from_run
from flowpilot_router_errors import RouterError, RouterLedgerCorruptionError, RouterLedgerWriteInProgress
from flowpilot_router_protocol_catalog import *

_DEFAULT_SENTINEL = object()
_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router skeleton is not bound")
    return _BOUND_ROUTER


OWNER_MODULE = 'flowpilot_router_controller_runtime'

def _next_mail_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    flags = run_state["flags"]
    for entry in MAIL_SEQUENCE:
        if flags.get(entry["flag"]):
            continue
        required_flag = entry.get("requires_flag")
        if required_flag and not flags.get(required_flag):
            continue
        if not run_state.get("ledger_check_requested"):
            return make_action(
                action_type="check_packet_ledger",
                actor="router",
                label="router_checks_packet_ledger",
                summary="Router checks the packet ledger internally before exposing the next mail relay.",
                allowed_reads=[project_relative(project_root, run_root / "packet_ledger.json")],
                allowed_writes=[project_relative(project_root, run_state_path(run_root))],
                extra={"next_mail_id": entry["mail_id"], "next_mail_to_role": entry["to_role"]},
            )
        extra = {"postcondition": entry["flag"]}
        role_obligation = _mail_role_obligation_contract(entry)
        if role_obligation is not None:
            extra["mail_role_obligation"] = role_obligation
        action = make_action(
            action_type="deliver_mail",
            actor="controller",
            label=entry["label"],
            summary=f"Deliver mail {entry['mail_id']} to {entry['to_role']} through Controller.",
            allowed_reads=[project_relative(project_root, run_root / "mailbox" / "outbox" / f"{entry['mail_id']}.json")],
            allowed_writes=[project_relative(project_root, run_root / "packet_ledger.json")],
            mail_id=entry["mail_id"],
            to_role=entry["to_role"],
            extra=extra,
        )
        if role_obligation is not None:
            action["next_step_contract"]["mail_role_obligation"] = role_obligation
        return action
    return None

def compute_controller_action(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    *,
    _router_internal_depth: int = 0,
) -> dict[str, Any]:
    router_module = _bound_router()

    def compute_again(
        next_project_root: Path,
        next_run_state: dict[str, Any],
        next_run_root: Path,
        next_depth: int,
    ) -> dict[str, Any]:
        return compute_controller_action(
            next_project_root,
            next_run_state,
            next_run_root,
            _router_internal_depth=next_depth,
        )

    lifecycle_action = flowpilot_router_action_providers.lifecycle_provider(
        router_module,
        project_root,
        run_state,
        run_root,
    )
    if lifecycle_action is not None:
        return lifecycle_action

    flowpilot_router_action_providers.run_reconciliation_barrier(
        router_module,
        project_root,
        run_state,
        run_root,
    )
    pending_action = flowpilot_router_action_providers.pending_action_provider(
        router_module,
        project_root,
        run_state,
        run_root,
        router_internal_depth=_router_internal_depth,
        compute_again=compute_again,
    )
    if pending_action is not None:
        return pending_action

    action_outcome = flowpilot_router_action_providers.fresh_action_provider(
        router_module,
        project_root,
        run_state,
        run_root,
    )
    if action_outcome is None:
        raise RouterError("no legal next action provider returned an action")
    if action_outcome.finalized:
        return action_outcome.action

    return flowpilot_router_action_providers.finalize_controller_action(
        router_module,
        project_root,
        run_state,
        run_root,
        action_outcome.action,
        router_internal_depth=_router_internal_depth,
        compute_again=compute_again,
    )

def next_action(project_root: Path, *, new_invocation: bool = False) -> dict[str, Any]:
    project_root = project_root.resolve()
    bootstrap = load_bootstrap_state(project_root, create_if_missing=True, new_invocation=new_invocation)
    if _startup_daemon_controls_bootstrap(bootstrap):
        pending = bootstrap.get("pending_action")
        if (
            isinstance(pending, dict)
            and _daemon_scheduled_bootloader_action(pending)
            and _router_daemon_can_continue_after_enqueued_action(pending)
        ):
            run_state, run_root = load_run_state(project_root, bootstrap)
            if run_state is None or run_root is None:
                raise RouterError("startup daemon controls bootloader but run router state is missing")
            schedule = _startup_daemon_schedule_bootloader_action(
                project_root,
                run_root,
                run_state,
                source="foreground_next_daemon_catchup",
            )
            action = schedule.get("action") if isinstance(schedule.get("action"), dict) else None
            if isinstance(action, dict):
                return action
        boot_action = compute_bootloader_action(project_root, bootstrap)
        if boot_action is not None:
            return boot_action
        run_state, run_root = load_run_state(project_root, bootstrap)
        if run_state is None or run_root is None:
            raise RouterError("startup daemon controls bootloader but run router state is missing")
        schedule = _startup_daemon_schedule_bootloader_action(
            project_root,
            run_root,
            run_state,
            source="foreground_next_daemon_catchup",
        )
        action = schedule.get("action") if isinstance(schedule.get("action"), dict) else None
        if isinstance(action, dict):
            return action
        raise RouterError(
            "Router daemon controls startup but has not scheduled the next startup row; "
            f"reason={schedule.get('reason')}"
        )
    boot_action = compute_bootloader_action(project_root, bootstrap)
    if boot_action is not None:
        return boot_action
    run_state, run_root = load_run_state(project_root, bootstrap)
    if run_state is None or run_root is None:
        raise RouterError("bootloader complete but run router state is missing")
    return compute_controller_action(project_root, run_state, run_root)

def apply_controller_action(project_root: Path, action_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    bootstrap = load_bootstrap_state(project_root, create_if_missing=False)
    run_state, run_root = load_run_state(project_root, bootstrap)
    if run_state is None or run_root is None:
        raise RouterError("run state is missing")
    _ensure_daemon_runtime_state(project_root, run_root, run_state, lifecycle_status="controller_apply")
    _reconcile_controller_receipts(project_root, run_root, run_state)
    pending = _ensure_pending(run_state, action_type)
    result_extra: dict[str, Any] = {}
    handled_action = flowpilot_router_action_handlers.apply_registered_action(
        _bound_router(),
        project_root,
        run_root,
        run_state,
        pending,
        action_type,
        payload,
    )
    if handled_action is not None:
        if handled_action.early_return is not None:
            return handled_action.early_return
        result_extra.update(handled_action.result_extra)
    else:
        raise RouterError(f"unknown controller action: {action_type}")
    append_history(run_state, str(pending["label"]), {"action_type": action_type})
    _maybe_write_controller_receipt_for_pending(
        project_root,
        run_root,
        run_state,
        pending,
        status="done",
        payload={"applied": action_type},
    )
    next_pending_after_apply = run_state.pop("_pending_action_after_current_apply", None)
    run_state["pending_action"] = next_pending_after_apply if isinstance(next_pending_after_apply, dict) else None
    if action_type == "write_terminal_summary":
        _mark_router_daemon_terminal(project_root, run_root, run_state, reason="terminal_summary_written")
        save_run_state(run_root, run_state)
        result = {"ok": True, "applied": action_type}
        result.update(result_extra)
        return result
    _refresh_route_memory(project_root, run_root, run_state, trigger=f"after_controller_action:{action_type}")
    _sync_derived_run_views(
        project_root,
        run_root,
        run_state,
        reason=f"after_controller_action:{action_type}",
        update_display=action_type != "sync_display_plan",
    )
    save_run_state(run_root, run_state)
    result = {"ok": True, "applied": action_type}
    result.update(result_extra)
    if action_type == "sync_display_plan":
        result.update(_display_plan_sync_payload(project_root, run_root, run_state))
        if "user_dialog_display_confirmation" in run_state["visible_plan_sync"]:
            result["user_dialog_display_confirmation"] = run_state["visible_plan_sync"]["user_dialog_display_confirmation"]
    return result

def record_external_event(
    project_root: Path,
    event: str,
    payload: dict[str, Any] | None = None,
    *,
    envelope_path: str | None = None,
    envelope_hash: str | None = None,
) -> dict[str, Any]:
    try:
        return _record_external_event_unchecked(
            project_root,
            event,
            payload,
            envelope_path=envelope_path,
            envelope_hash=envelope_hash,
        )
    except (RouterError, packet_runtime.PacketRuntimeError) as exc:
        existing_blocker = getattr(exc, "control_blocker", None)
        if isinstance(existing_blocker, dict):
            raise
        blocker = _try_write_control_blocker_for_exception(
            project_root,
            source="router.record_external_event",
            error_message=str(exc),
            event=event,
            payload=payload,
        )
        if blocker:
            raise RouterError(str(exc), control_blocker=blocker) from exc
        raise

def apply_action(project_root: Path, action_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    bootstrap = load_bootstrap_state(project_root, create_if_missing=False)
    pending = bootstrap.get("pending_action")
    if isinstance(pending, dict) and pending.get("action_type") == action_type:
        return apply_bootloader_action(project_root, action_type, payload)
    try:
        return apply_controller_action(project_root, action_type, payload)
    except (RouterError, packet_runtime.PacketRuntimeError) as exc:
        existing_blocker = getattr(exc, "control_blocker", None)
        if isinstance(existing_blocker, dict):
            raise
        blocker = _try_write_control_blocker_for_exception(
            project_root,
            source="router.apply_controller_action",
            error_message=str(exc),
            action_type=action_type,
            payload=payload,
        )
        if blocker:
            raise RouterError(str(exc), control_blocker=blocker) from exc
        raise

def run_until_wait(project_root: Path, *, max_steps: int = 50, new_invocation: bool = False) -> dict[str, Any]:
    if max_steps < 1:
        raise RouterError("run-until-wait requires max_steps >= 1")
    applied_actions: list[dict[str, Any]] = []
    start_new = new_invocation
    for _ in range(max_steps):
        action = next_action(project_root, new_invocation=start_new)
        start_new = False
        action_type = str(action.get("action_type") or "")
        action_crosses_boundary = (
            action_type not in SAFE_RUN_UNTIL_WAIT_ACTION_TYPES
            or bool(action.get("requires_user"))
            or bool(action.get("requires_payload"))
            or bool(action.get("requires_user_dialog_display_confirmation"))
            or bool(action.get("requires_host_role_binding"))
            or bool(action.get("requires_host_automation"))
            or bool(action.get("card_id"))
        )
        if action_crosses_boundary:
            result = dict(action)
            result["folded_command"] = "run-until-wait"
            result["folded_applied_count"] = len(applied_actions)
            result["folded_applied_actions"] = applied_actions
            result["folded_stop_reason"] = "requires_user_host_or_role_boundary"
            return result
        applied = apply_action(project_root, action_type, {})
        applied_actions.append({"action_type": action_type, "result": applied})
        if applied.get("waiting") or applied.get("terminal"):
            result = dict(applied)
            result["folded_command"] = "run-until-wait"
            result["folded_applied_count"] = len(applied_actions)
            result["folded_applied_actions"] = applied_actions
            result["folded_stop_reason"] = "terminal_or_waiting_action_applied"
            return result
    raise RouterError("run-until-wait reached max_steps before a wait boundary")

def record_controller_action_receipt(
    project_root: Path,
    *,
    action_id: str,
    status: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    bootstrap = load_bootstrap_state(project_root, create_if_missing=False)
    run_state, run_root = load_run_state(project_root, bootstrap)
    if run_state is None or run_root is None:
        raise RouterError("controller receipt requires an active FlowPilot run")
    receipt = _write_controller_receipt(
        project_root,
        run_root,
        run_state,
        action_id=action_id,
        status=status,
        payload=payload,
    )
    _reconcile_scheduled_controller_action_receipts(project_root, run_root, run_state)
    status_payload = _write_router_daemon_status(
        project_root,
        run_root,
        run_state,
        lifecycle_status="controller_receipt_recorded",
        current_action=run_state.get("pending_action") if isinstance(run_state.get("pending_action"), dict) else None,
    )
    save_run_state(run_root, run_state)
    return {
        "ok": True,
        "command": "controller-receipt",
        "receipt": receipt,
        "daemon_status": status_payload,
        "controller_action_ledger": _controller_action_ledger_summary(run_root),
    }

_LOCAL_NAMES = set(globals())
