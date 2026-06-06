"""PM package reconciliation helpers split from expected-waits reconciliation."""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType
from typing import Any

import packet_runtime
import role_output_runtime
import flowpilot_router_expected_waits_reconciliation as _parent
from flowpilot_router_errors import RouterError


_RECONCILED_PM_PACKAGE_DOMAIN_COMMITS: dict[str, dict[str, str]] = {
    "pm_records_material_scan_result_disposition": {
        "batch_kind": "material_scan",
        "package_label": "material_scan",
        "gate_kind": "material_sufficiency",
        "output_path": "material/pm_material_scan_result_disposition.json",
    },
    "pm_records_research_result_disposition": {
        "batch_kind": "research",
        "package_label": "research",
        "gate_kind": "research_direct_source_check",
        "output_path": "research/pm_research_result_disposition.json",
    },
    "pm_records_current_node_result_disposition": {
        "batch_kind": "current_node",
        "package_label": "current_node",
        "gate_kind": "node_completion",
        "output_path": "current_node",
    },
}


_BOUND_ROUTER: ModuleType | None = None
def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    _parent._bind_router(router)
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(_parent).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names or name in current:
            continue
        current[name] = value


def _reconciled_pm_package_output_path(run_root: Path, event: str) -> Path:
    config = _RECONCILED_PM_PACKAGE_DOMAIN_COMMITS[event]
    if event == "pm_records_current_node_result_disposition":
        frontier = _active_frontier(run_root)
        return _active_node_root(run_root, frontier) / "reviews" / "pm_current_node_result_disposition.json"
    return run_root / str(config["output_path"])


def _commit_reconciled_event_domain_artifact(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    event: str,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    config = _RECONCILED_PM_PACKAGE_DOMAIN_COMMITS.get(event)
    if config is None:
        return None
    output_path = _reconciled_pm_package_output_path(run_root, event)
    _write_pm_package_result_disposition(
        project_root,
        run_root,
        run_state,
        payload,
        batch_kind=str(config["batch_kind"]),
        package_label=str(config["package_label"]),
        gate_kind=str(config["gate_kind"]),
        output_path=output_path,
        router_event=event,
    )
    artifact = read_json_if_exists(output_path)
    if artifact.get("schema_version") != "flowpilot.pm_package_result_disposition.v1":
        raise RouterError(f"event {event} did not commit a valid PM package disposition artifact")
    return {
        "schema_version": "flowpilot.reconciled_event_domain_commit.v1",
        "event": event,
        "artifact_kind": "pm_package_result_disposition",
        "artifact_path": project_relative(project_root, output_path),
        "artifact_hash": packet_runtime.sha256_file(output_path),
        "batch_kind": config["batch_kind"],
        "source_body_hash": artifact.get("source_body_hash"),
        "decision": artifact.get("decision"),
    }


def _reconciled_event_domain_artifact_matches_payload(
    run_root: Path,
    event: str,
    payload: dict[str, Any],
) -> bool:
    config = _RECONCILED_PM_PACKAGE_DOMAIN_COMMITS.get(event)
    if config is None:
        return True
    output_path = _reconciled_pm_package_output_path(run_root, event)
    artifact = read_json_if_exists(output_path)
    source_body_hash = _payload_body_hash(payload)
    if (
        artifact.get("schema_version") != "flowpilot.pm_package_result_disposition.v1"
        or artifact.get("source_body_hash") != source_body_hash
    ):
        return False
    try:
        batch = _active_parallel_packet_batch(run_root, str(config["batch_kind"]))
    except (RouterError, OSError, json.JSONDecodeError, TypeError, ValueError):
        batch = None
    if not isinstance(batch, dict):
        return False
    disposition = batch.get("pm_result_disposition")
    return isinstance(disposition, dict) and disposition.get("source_body_hash") == source_body_hash


def _record_router_reconciled_external_event(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    event: str,
    payload: dict[str, Any],
) -> bool:
    _bind_router(router)
    meta = EXTERNAL_EVENTS[event]
    flag = str(meta["flag"])
    repeatable = event in {ROLE_WORK_RESULT_RETURNED_EVENT, "worker_current_node_result_returned"}
    scoped_identity = _scoped_event_identity(project_root, run_root, run_state, event, payload)
    domain_commit_required = event in _RECONCILED_PM_PACKAGE_DOMAIN_COMMITS
    already_recorded = _scoped_event_is_recorded(run_state, scoped_identity)
    if already_recorded and (
        not domain_commit_required
        or _reconciled_event_domain_artifact_matches_payload(run_root, event, payload)
    ):
        return False
    if not already_recorded:
        _check_scoped_event_conflict(run_state, scoped_identity)
    scoped_identity_requires_fresh_record = domain_commit_required and scoped_identity is not None
    if run_state.setdefault("flags", {}).get(flag) and not repeatable and not scoped_identity_requires_fresh_record:
        return False
    domain_commit = _commit_reconciled_event_domain_artifact(project_root, run_root, run_state, event, payload)
    run_state["flags"][flag] = True
    if already_recorded:
        wait_closure = _close_waiting_controller_actions_for_external_event(
            project_root,
            run_root,
            run_state,
            event=event,
            payload=payload,
            source="router_repaired_reconciled_event_domain_commit",
        )
        append_history(
            run_state,
            "router_repaired_reconciled_event_domain_commit",
            {
                "event": event,
                "payload": payload,
                "controller_visibility": "metadata_only",
                "domain_commit": domain_commit,
                "wait_closure": wait_closure,
            },
        )
        return True
    event_record = {
        "event": event,
        "summary": meta["summary"],
        "payload": payload,
        "recorded_at": utc_now(),
        "reconciled_by_router": True,
    }
    if domain_commit is not None:
        event_record["domain_commit"] = domain_commit
    run_state.setdefault("events", []).append(event_record)
    _mark_scoped_event_recorded(run_state, scoped_identity)
    wait_closure = _close_waiting_controller_actions_for_external_event(
        project_root,
        run_root,
        run_state,
        event=event,
        payload=payload,
        source="router_reconciled_external_event",
    )
    append_history(
        run_state,
        f"router_reconciled_{event}",
        {
            "event": event,
            "payload": payload,
            "controller_visibility": "metadata_only",
            "domain_commit": domain_commit,
            "wait_closure": wait_closure,
        },
    )
    return True


_LOCAL_NAMES = set(globals())

__all__ = ("_record_router_reconciled_external_event",)
