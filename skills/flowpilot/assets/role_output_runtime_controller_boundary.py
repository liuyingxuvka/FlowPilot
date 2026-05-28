"""Controller-boundary confirmation helpers for role-output runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from role_output_runtime_schema import (
    CONTROLLER_BOUNDARY_CONFIRMATION_EVENT,
    CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE,
    CONTROLLER_BOUNDARY_CONFIRMATION_SCHEMA,
    _controller_boundary_sources,
    _project_relative,
    _run_paths,
    controller_boundary_constraints,
    utc_now,
)


def build_controller_boundary_confirmation_body(
    project_root: Path,
    *,
    run_id: str | None = None,
    action_id: str | None = None,
    source_action_id: str | None = None,
) -> dict[str, Any]:
    resolved_run_id, run_root = _run_paths(project_root, run_id)
    sources = _controller_boundary_sources(project_root, run_root)
    return {
        "schema_version": CONTROLLER_BOUNDARY_CONFIRMATION_SCHEMA,
        "run_id": resolved_run_id,
        "event": CONTROLLER_BOUNDARY_CONFIRMATION_EVENT,
        "confirmed_by_role": "controller",
        "confirmation_source": "router_delivered_controller_core",
        "controller_action_id": str(action_id or ""),
        "source_action_id": str(source_action_id or ""),
        "controller_core_card_id": "controller.core",
        "controller_core_path": _project_relative(project_root, sources["controller_core_path"]),
        "controller_core_sha256": sources["controller_core_hash"],
        "manifest_path": _project_relative(project_root, sources["manifest_path"]),
        "manifest_sha256": sources["manifest_hash"],
        "controller_policy": sources["controller_policy"],
        "controller_policy_sha256": sources["controller_policy_hash"],
        "boundary_constraints": controller_boundary_constraints(),
        "sealed_body_reads_allowed": False,
        "router_owned_confirmation": True,
        "confirmed_at": utc_now(),
    }


def submit_controller_boundary_confirmation(
    project_root: Path,
    *,
    agent_id: str,
    submit_output: Callable[..., dict[str, Any]],
    run_id: str | None = None,
    action_id: str | None = None,
    source_action_id: str | None = None,
    output_path: str | Path | None = None,
    controller_status_packet_path: str | Path | None = None,
) -> dict[str, Any]:
    resolved_run_id, run_root = _run_paths(project_root, run_id)
    body = build_controller_boundary_confirmation_body(
        project_root,
        run_id=resolved_run_id,
        action_id=action_id,
        source_action_id=source_action_id,
    )
    return submit_output(
        project_root,
        output_type=CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE,
        role="controller",
        agent_id=agent_id,
        body=body,
        output_path=output_path or (run_root / "startup" / "controller_boundary_confirmation.json"),
        run_id=resolved_run_id,
        controller_status_packet_path=controller_status_packet_path,
        router_directed_submission=False,
    )
