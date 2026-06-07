"""Next-action selection for FlowPilot controller runtime."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import packet_runtime
import flowpilot_router_action_providers
from flowpilot_router_errors import RouterError
from flowpilot_router_protocol_catalog import *

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


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router skeleton is not bound")
    return _BOUND_ROUTER


def _next_mail_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    flags = run_state["flags"]
    for entry in MAIL_SEQUENCE:
        if flags.get(entry["flag"]):
            continue
        required_flag = entry.get("requires_flag")
        if required_flag and not flags.get(required_flag):
            continue
        required_all = entry.get("requires_all_flags")
        if required_all and not all(flags.get(str(flag)) for flag in required_all):
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
    try:
        return compute_controller_action(project_root, run_state, run_root)
    except (RouterError, packet_runtime.PacketRuntimeError) as exc:
        existing_blocker = getattr(exc, "control_blocker", None)
        if not isinstance(existing_blocker, dict):
            message = str(exc)
            if "active execution frontier is missing route or node" in message:
                existing_blocker = _write_control_blocker(
                    project_root,
                    run_root,
                    run_state,
                    source="router_no_legal_next_action",
                    error_message=(
                        "Controller has no legal current route frontier; PM repair or routing decision is "
                        "required before any further route, mail, packet, or project work."
                    ),
                    action_type="controller_no_legal_next_action",
                    payload={
                        "path": project_relative(project_root, run_state_path(run_root)),
                        "role": "controller",
                        "frontier_error": message,
                    },
                )
            else:
                existing_blocker = _try_write_control_blocker_for_exception(
                    project_root,
                    source="router.next_action",
                    error_message=message,
                )
        if isinstance(existing_blocker, dict) and not existing_blocker.get("materialization_failed"):
            refreshed_state = read_json(run_state_path(run_root))
            action = _next_control_blocker_action(project_root, refreshed_state, run_root)
            if action is not None:
                return action
            raise RouterError(str(exc), control_blocker=existing_blocker) from exc
        raise


__all__ = ("compute_controller_action", "next_action")

_LOCAL_NAMES = set(globals())
