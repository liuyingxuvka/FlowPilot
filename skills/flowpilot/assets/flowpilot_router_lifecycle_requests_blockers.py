"""Exception blocker fallback helpers for FlowPilot router lifecycle requests."""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType
from typing import Any

from flowpilot_runtime_gateway import GATEWAY_ROUTER_JSON, assert_runtime_gateway_write


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
        raise RuntimeError("router facade is not bound")
    return _BOUND_ROUTER


def _try_write_control_blocker_for_exception(
    project_root: Path,
    *,
    source: str,
    error_message: str,
    event: str | None = None,
    action_type: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not _should_materialize_control_blocker(
        error_message,
        event=event,
        action_type=action_type,
        payload=payload,
    ):
        return None
    try:
        bootstrap = load_bootstrap_state(project_root, create_if_missing=False)
        run_state, run_root = load_run_state(project_root, bootstrap)
        if run_state is None or run_root is None:
            return None
        return _write_control_blocker(
            project_root,
            run_root,
            run_state,
            source=source,
            error_message=error_message,
            event=event,
            action_type=action_type,
            payload=payload,
        )
    except Exception:
        try:
            fallback = {
                "schema_version": "flowpilot.control_blocker_materialization_failure.v1",
                "materialization_failed": True,
                "source": source,
                "error_message": error_message,
                "event": event,
                "action_type": action_type,
                "recorded_at": utc_now(),
            }
            flowpilot_root = project_root / ".flowpilot"
            failure_path = flowpilot_root / "control_blocker_materialization_failures.jsonl"
            assert_runtime_gateway_write(failure_path, GATEWAY_ROUTER_JSON, operation="append_control_blocker_materialization_failure")
            failure_path.parent.mkdir(parents=True, exist_ok=True)
            with failure_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(fallback, sort_keys=True) + "\n")
            fallback["fallback_diagnostic_path"] = project_relative(project_root, failure_path)
            return fallback
        except Exception:
            return {
                "schema_version": "flowpilot.control_blocker_materialization_failure.v1",
                "materialization_failed": True,
                "source": source,
                "error_message": error_message,
                "event": event,
                "action_type": action_type,
            }


__all__ = ("_try_write_control_blocker_for_exception",)


_LOCAL_NAMES = set(globals())
