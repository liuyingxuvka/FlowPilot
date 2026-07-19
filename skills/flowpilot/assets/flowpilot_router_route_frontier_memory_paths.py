"""Route memory, display-plan path, and route item status helpers."""

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
from flowpilot_prompt_store import PromptStoreError, card_manifest_entry, load_card_manifest_from_run
from flowpilot_router_errors import RouterError, RouterLedgerCorruptionError, RouterLedgerWriteInProgress

_DEFAULT_SENTINEL = object()
_BOUND_ROUTER: ModuleType | None = None

_ROUTE_MEMORY_SOURCE_SNAPSHOT_SCHEMA = "flowpilot.route_memory_source_snapshot.v1"
_ROUTE_MEMORY_REVIEW_BLOCK_EVENTS = frozenset(
    {
        "current_node_reviewer_blocks_result",
        "reviewer_blocks_node_acceptance_plan",
    }
)
_ROUTE_MEMORY_REVIEW_PASS_EVENTS = frozenset(
    {
        "reviewer_passes_research_direct_source_check",
        "reviewer_passes_node_acceptance_plan",
        "current_node_reviewer_passes_result",
        "reviewer_passes_parent_backward_replay",
        "reviewer_passes_evidence_quality_package",
        "reviewer_final_backward_replay_passed",
    }
)
_ROUTE_MEMORY_FIXED_CONTENT_PATHS = (
    "execution_frontier.json",
    "evidence/stale_evidence_ledger.json",
    "evidence/evidence_ledger.json",
    "generated_resource_ledger.json",
    "material/material_artifact_map.json",
)
_ROUTE_MEMORY_FIXED_EXISTENCE_PATHS = (
    "packet_ledger.json",
    "prompt_delivery_ledger.json",
    "research/research_package.json",
    "research/worker_research_report.json",
    "research/research_reviewer_report.json",
    "flowguard/product_architecture_modelability.json",
    "flowguard/root_contract_modelability.json",
    "flowguard/child_skill_conformance_model.json",
    "flowguard/child_skill_product_fit.json",
)
_ROUTE_MEMORY_NODE_EXISTENCE_PATHS = (
    "node_acceptance_plan.json",
    "reviews/node_acceptance_plan_review.json",
    "parent_backward_replay.json",
    "pm_parent_segment_decision.json",
)


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get('_LOCAL_NAMES', set())
    for name, value in vars(router).items():
        if name.startswith('__') and name.endswith('__'):
            continue
        if name in local_names:
            continue
        current[name] = value

def _route_memory_root(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'route_memory'

def _route_history_index_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return router._route_memory_root(run_root) / 'route_history_index.json'

def _pm_prior_path_context_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return router._route_memory_root(run_root) / 'pm_prior_path_context.json'


def _route_memory_review_projection(run_state: dict[str, Any]) -> dict[str, Any]:
    markers: dict[str, list[dict[str, Any]]] = {"blocks": [], "passes": []}
    for event in run_state.get("events") or []:
        if not isinstance(event, dict):
            continue
        event_name = str(event.get("event") or "")
        target = None
        if event_name in _ROUTE_MEMORY_REVIEW_BLOCK_EVENTS:
            target = markers["blocks"]
        elif event_name in _ROUTE_MEMORY_REVIEW_PASS_EVENTS:
            target = markers["passes"]
        if target is not None:
            target.append(
                {
                    "event": event_name,
                    "summary": event.get("summary"),
                    "recorded_at": event.get("recorded_at"),
                }
            )
    return {
        "run_id": str(run_state.get("run_id") or ""),
        "review_markers": markers,
    }


def _route_memory_expected_inputs(
    router: ModuleType,
    run_root: Path,
) -> tuple[list[tuple[str, Path]], str, int]:
    frontier = router.read_json_if_exists(run_root / "execution_frontier.json")
    route_id = str(frontier.get("active_route_id") or "route-001")
    route_version = int(frontier.get("route_version") or 0)
    route_path = run_root / "routes" / route_id / "flow.json"
    mutations_path = run_root / "routes" / route_id / "mutations.json"
    route = router.read_json_if_exists(route_path)

    inputs: list[tuple[str, Path]] = [
        ("content", run_root / relative_path)
        for relative_path in _ROUTE_MEMORY_FIXED_CONTENT_PATHS
    ]
    inputs.extend(
        [
            ("content", route_path),
            ("content", mutations_path),
        ]
    )
    inputs.extend(
        ("existence", run_root / relative_path)
        for relative_path in _ROUTE_MEMORY_FIXED_EXISTENCE_PATHS
    )
    for node in router._route_nodes(route):
        node_id = str(node.get("node_id") or "").strip()
        if not node_id:
            continue
        node_root = run_root / "routes" / route_id / "nodes" / node_id
        inputs.extend(
            ("existence", node_root / relative_path)
            for relative_path in _ROUTE_MEMORY_NODE_EXISTENCE_PATHS
        )

    unique: dict[tuple[str, str], tuple[str, Path]] = {}
    resolved_run_root = run_root.resolve()
    for mode, path in inputs:
        resolved_path = path.resolve()
        try:
            relative = resolved_path.relative_to(resolved_run_root).as_posix()
        except ValueError as exc:
            raise RouterError("route-memory source input escapes the current run root") from exc
        unique[(mode, relative)] = (mode, resolved_path)
    return (
        [unique[key] for key in sorted(unique)],
        route_id,
        route_version,
    )


def _route_memory_source_snapshot(
    router: ModuleType,
    run_root: Path,
    run_state: dict[str, Any],
) -> dict[str, Any]:
    _bind_router(router)
    expected_inputs, route_id, route_version = _route_memory_expected_inputs(router, run_root)
    resolved_run_root = run_root.resolve()
    input_rows: list[dict[str, Any]] = []
    for mode, path in expected_inputs:
        relative_path = path.relative_to(resolved_run_root).as_posix()
        exists = path.is_file()
        row: dict[str, Any] = {
            "path": relative_path,
            "mode": mode,
            "exists": exists,
        }
        if mode == "content" and exists:
            row["sha256"] = packet_runtime.sha256_file(path)
        input_rows.append(row)
    snapshot = {
        "schema_version": _ROUTE_MEMORY_SOURCE_SNAPSHOT_SCHEMA,
        "run_id": str(run_state.get("run_id") or ""),
        "active_route_id": route_id,
        "route_version": route_version,
        "inputs": input_rows,
        "run_state_projection": _route_memory_review_projection(run_state),
    }
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    snapshot["fingerprint"] = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return snapshot


def _route_memory_currentness(
    router: ModuleType,
    run_root: Path,
    run_state: dict[str, Any],
) -> dict[str, Any]:
    _bind_router(router)
    history = router.read_json_if_exists(router._route_history_index_path(run_root))
    context = router.read_json_if_exists(router._pm_prior_path_context_path(run_root))
    expected_run_id = str(run_state.get("run_id") or "")
    checks = (
        (history.get("schema_version") == ROUTE_HISTORY_INDEX_SCHEMA, "route_history_schema_mismatch"),
        (context.get("schema_version") == PM_PRIOR_PATH_CONTEXT_SCHEMA, "pm_context_schema_mismatch"),
        (str(history.get("run_id") or "") == expected_run_id, "route_history_run_mismatch"),
        (str(context.get("run_id") or "") == expected_run_id, "pm_context_run_mismatch"),
        (
            bool(history.get("refreshed_at"))
            and history.get("refreshed_at") == context.get("refreshed_at"),
            "route_memory_refresh_identity_mismatch",
        ),
        (
            isinstance(history.get("source_snapshot"), dict)
            and history.get("source_snapshot") == context.get("source_snapshot"),
            "route_memory_source_snapshot_pair_mismatch",
        ),
    )
    for passed, reason in checks:
        if not passed:
            return {"current": False, "reason": reason}
    current_snapshot = _route_memory_source_snapshot(router, run_root, run_state)
    if history.get("source_snapshot") != current_snapshot:
        return {
            "current": False,
            "reason": "route_memory_source_snapshot_stale",
            "expected_fingerprint": current_snapshot.get("fingerprint"),
            "recorded_fingerprint": (history.get("source_snapshot") or {}).get("fingerprint"),
        }
    return {
        "current": True,
        "reason": "current",
        "source_snapshot_fingerprint": current_snapshot["fingerprint"],
    }


def _route_memory_ready(router: ModuleType, run_root: Path, run_state: dict[str, Any]) -> bool:
    _bind_router(router)
    flags = run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {}
    if not (
        bool(flags.get('route_history_index_refreshed'))
        and bool(flags.get('pm_prior_path_context_refreshed'))
        and router._route_history_index_path(run_root).exists()
        and router._pm_prior_path_context_path(run_root).exists()
    ):
        return False
    return bool(_route_memory_currentness(router, run_root, run_state).get("current"))

def _display_plan_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'display_plan.json'

def _route_state_snapshot_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'route_state_snapshot.json'

def _route_display_refresh_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'display' / 'route_display_refresh.json'

def _optional_source_path(router: ModuleType, project_root: Path, path: Path) -> str | None:
    _bind_router(router)
    return project_relative(project_root, path) if path.exists() else None

def _plan_item_status(router: ModuleType, raw_status: Any, *, active: bool=False) -> str:
    _bind_router(router)
    status = str(raw_status or '').lower()
    if active:
        return 'in_progress'
    if status in {'complete', 'completed', 'done', 'passed'}:
        return 'completed'
    if status in {'active', 'running', 'current', 'in_progress'}:
        return 'in_progress'
    return 'pending'

def _frontier_completed_node_ids(router: ModuleType, run_root: Path) -> set[str]:
    _bind_router(router)
    frontier = read_json_if_exists(run_root / 'execution_frontier.json')
    completed = frontier.get('completed_nodes') if isinstance(frontier, dict) else []
    return {str(node_id) for node_id in completed or []}

def _route_item_status(router: ModuleType, run_root: Path, node_id: str, *, active_node_id: str | None, raw_status: Any=None) -> str:
    _bind_router(router)
    if node_id in router._frontier_completed_node_ids(run_root):
        return 'completed'
    if active_node_id and node_id == active_node_id:
        return 'in_progress'
    status = str(raw_status or '').lower()
    if status in {'complete', 'completed', 'done', 'passed'}:
        return 'completed'
    return 'pending'

__all__ = (
    '_route_memory_root',
    '_route_history_index_path',
    '_pm_prior_path_context_path',
    '_route_memory_ready',
    '_display_plan_path',
    '_route_state_snapshot_path',
    '_route_display_refresh_path',
    '_optional_source_path',
    '_plan_item_status',
    '_frontier_completed_node_ids',
    '_route_item_status',
)

_LOCAL_NAMES = set(globals())
