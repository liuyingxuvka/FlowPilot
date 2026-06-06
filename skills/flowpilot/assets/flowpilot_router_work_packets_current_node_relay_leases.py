"""Active-holder lease helpers for current-node packet relays."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import packet_runtime
from flowpilot_router_errors import RouterError


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


def _active_holder_frontier_version(router: ModuleType, frontier: dict[str, Any]) -> int:
    _bind_router(router)
    return int(frontier.get('frontier_version') or frontier.get('route_version') or 0)

def _current_node_active_holder_lease_plan(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]], frontier: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    _bind_router(router)
    route_version = int(frontier.get('route_version') or 0)
    frontier_version = router._active_holder_frontier_version(frontier)
    planned: list[dict[str, Any]] = []
    allowed_writes: list[str] = []
    for record in records:
        envelope_path = router._packet_envelope_path_from_record(project_root, run_state, record)
        envelope = packet_runtime.load_envelope(project_root, envelope_path)
        holder_role = str(envelope.get('to_role') or record.get('to_role') or '')
        target_agent_id = _active_agent_id_for_role(run_root, holder_role)
        packet_dir = envelope_path.parent
        item = {'packet_id': str(envelope.get('packet_id') or record.get('packet_id') or ''), 'holder_role': holder_role, 'target_agent_id': target_agent_id, 'route_version': route_version, 'frontier_version': frontier_version, 'packet_envelope_path': project_relative(project_root, envelope_path), 'active_holder_lease_path': project_relative(project_root, packet_dir / 'active_holder_lease.json'), 'active_holder_events_path': project_relative(project_root, packet_dir / 'active_holder_events.jsonl'), 'mode': 'lease_on_current_node_delivery' if target_agent_id else 'no_live_agent_id'}
        planned.append(item)
        if target_agent_id:
            allowed_writes.extend([item['active_holder_lease_path'], item['active_holder_events_path']])
    return ({'mode': 'lease_on_current_node_delivery', 'requires_live_agent_id': True, 'controller_visibility': 'lease_metadata_only', 'route_version': route_version, 'frontier_version': frontier_version, 'packets': planned}, sorted(set(allowed_writes)))

def _issue_current_node_active_holder_leases(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    _bind_router(router)
    frontier = router._active_frontier(run_root)
    route_version = int(frontier.get('route_version') or 0)
    frontier_version = router._active_holder_frontier_version(frontier)
    issued: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for record in records:
        envelope_path = router._packet_envelope_path_from_record(project_root, run_state, record)
        envelope = packet_runtime.load_envelope(project_root, envelope_path)
        holder_role = str(envelope.get('to_role') or record.get('to_role') or '')
        target_agent_id = _active_agent_id_for_role(run_root, holder_role)
        packet_id = str(envelope.get('packet_id') or record.get('packet_id') or '')
        if not target_agent_id:
            skipped.append({'packet_id': packet_id, 'holder_role': holder_role, 'reason': 'no_live_agent_id_available'})
            continue
        try:
            lease = packet_runtime.issue_active_holder_lease(project_root, packet_envelope=envelope, holder_role=holder_role, holder_agent_id=target_agent_id, route_version=route_version, frontier_version=frontier_version)
        except packet_runtime.PacketRuntimeError as exc:
            raise RouterError(f'current-node active-holder lease failed for {packet_id}: {exc}') from exc
        issued.append({'packet_id': packet_id, 'holder_role': holder_role, 'holder_agent_id': target_agent_id, 'lease_path': lease['lease_path'], 'lease_id': lease['lease_id']})
    summary = {'schema_version': 'flowpilot.current_node_active_holder_fast_lane.v1', 'mode': 'lease_on_current_node_delivery', 'issued': issued, 'skipped': skipped, 'requires_live_agent_id': True, 'recorded_at': utc_now()}
    run_state['current_node_active_holder_fast_lane'] = summary
    return summary

def _packet_active_holder_lease_plan(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]], *, packet_family: str, mode: str) -> tuple[dict[str, Any], list[str]]:
    _bind_router(router)
    try:
        frontier = router._active_frontier(run_root)
    except RouterError:
        frontier = read_json_if_exists(run_root / 'execution_frontier.json') or {}
    route_version = int(frontier.get('route_version') or 0)
    frontier_version = router._active_holder_frontier_version(frontier)
    planned: list[dict[str, Any]] = []
    allowed_writes: list[str] = []
    for record in records:
        envelope_path = router._packet_envelope_path_from_record(project_root, run_state, record)
        envelope = packet_runtime.load_envelope(project_root, envelope_path)
        holder_role = str(envelope.get('to_role') or record.get('to_role') or '')
        target_agent_id = _active_agent_id_for_role(run_root, holder_role)
        packet_dir = envelope_path.parent
        item = {'packet_id': str(envelope.get('packet_id') or record.get('packet_id') or ''), 'packet_family': packet_family, 'holder_role': holder_role, 'target_agent_id': target_agent_id, 'route_version': route_version, 'frontier_version': frontier_version, 'packet_envelope_path': project_relative(project_root, envelope_path), 'active_holder_lease_path': project_relative(project_root, packet_dir / 'active_holder_lease.json'), 'active_holder_events_path': project_relative(project_root, packet_dir / 'active_holder_events.jsonl'), 'mode': mode if target_agent_id else 'no_live_agent_id'}
        planned.append(item)
        if target_agent_id:
            allowed_writes.extend([item['active_holder_lease_path'], item['active_holder_events_path']])
    return ({'schema_version': 'flowpilot.packet_active_holder_fast_lane.v1', 'mode': mode, 'packet_family': packet_family, 'requires_live_agent_id': True, 'controller_visibility': 'lease_metadata_only', 'route_version': route_version, 'frontier_version': frontier_version, 'packets': planned}, sorted(set(allowed_writes)))

def _issue_packet_active_holder_leases(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]], *, packet_family: str, mode: str) -> dict[str, Any]:
    _bind_router(router)
    try:
        frontier = router._active_frontier(run_root)
    except RouterError:
        frontier = read_json_if_exists(run_root / 'execution_frontier.json') or {}
    route_version = int(frontier.get('route_version') or 0)
    frontier_version = router._active_holder_frontier_version(frontier)
    issued: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for record in records:
        envelope_path = router._packet_envelope_path_from_record(project_root, run_state, record)
        envelope = packet_runtime.load_envelope(project_root, envelope_path)
        holder_role = str(envelope.get('to_role') or record.get('to_role') or '')
        target_agent_id = _active_agent_id_for_role(run_root, holder_role)
        packet_id = str(envelope.get('packet_id') or record.get('packet_id') or '')
        if not target_agent_id:
            skipped.append({'packet_id': packet_id, 'packet_family': packet_family, 'holder_role': holder_role, 'reason': 'no_live_agent_id_available'})
            continue
        try:
            lease = packet_runtime.issue_active_holder_lease(project_root, packet_envelope=envelope, holder_role=holder_role, holder_agent_id=target_agent_id, route_version=route_version, frontier_version=frontier_version)
        except packet_runtime.PacketRuntimeError as exc:
            raise RouterError(f'{packet_family} active-holder lease failed for {packet_id}: {exc}') from exc
        issued.append({'packet_id': packet_id, 'packet_family': packet_family, 'holder_role': holder_role, 'holder_agent_id': target_agent_id, 'lease_path': lease['lease_path'], 'lease_id': lease['lease_id']})
    summary = {'schema_version': 'flowpilot.packet_active_holder_fast_lane.v1', 'mode': mode, 'packet_family': packet_family, 'issued': issued, 'skipped': skipped, 'requires_live_agent_id': True, 'recorded_at': utc_now()}
    run_state.setdefault('packet_active_holder_fast_lanes', {})[packet_family] = summary
    return summary

def _active_holder_plan_by_packet(active_holder_plan: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(active_holder_plan, dict):
        return {}
    planned = active_holder_plan.get('packets')
    if not isinstance(planned, list):
        return {}
    return {
        str(item.get('packet_id') or ''): item
        for item in planned
        if isinstance(item, dict) and str(item.get('packet_id') or '').strip()
    }

__all__ = (
    "_active_holder_frontier_version",
    "_active_holder_plan_by_packet",
    "_current_node_active_holder_lease_plan",
    "_issue_current_node_active_holder_leases",
    "_issue_packet_active_holder_leases",
    "_packet_active_holder_lease_plan",
)

_LOCAL_NAMES = set(globals())
