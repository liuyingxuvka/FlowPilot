"""Runtime relay operation builders for current-node packet relays."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import packet_runtime
from flowpilot_router_work_packets_current_node_relay_leases import _active_holder_plan_by_packet


def _bind_router(router: ModuleType) -> None:
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value


def _flowpilot_runtime_relay_operation(
    router: ModuleType,
    project_root: Path,
    *,
    packet_id: str,
    envelope_path: Path,
    envelope_kind: str,
    source_role: str,
    target_role: str,
    packet_family: str,
    postcondition: str,
    active_holder_item: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _bind_router(router)
    envelope_rel = project_relative(project_root, envelope_path)
    args = [
        'relay-envelope',
        '--envelope-path',
        envelope_rel,
        '--controller-agent-id',
        'controller',
        '--received-from-role',
        source_role,
        '--relayed-to-role',
        target_role,
    ]
    holder_agent_id = ''
    if isinstance(active_holder_item, dict):
        holder_agent_id = str(active_holder_item.get('target_agent_id') or '').strip()
    if holder_agent_id:
        args.extend(
            [
                '--holder-agent-id',
                holder_agent_id,
                '--route-version',
                str(int(active_holder_item.get('route_version') or 0)),
                '--frontier-version',
                str(int(active_holder_item.get('frontier_version') or 0)),
            ]
        )
    packet_dir = envelope_path.parent
    expected_writes = [
        envelope_rel,
        project_relative(project_root, packet_dir.parent.parent / 'packet_ledger.json'),
    ]
    if isinstance(active_holder_item, dict) and holder_agent_id:
        for key in ('active_holder_lease_path', 'active_holder_events_path'):
            value = str(active_holder_item.get(key) or '').strip()
            if value:
                expected_writes.append(value)
    expected_writes = [item for item in expected_writes if item]
    return {
        'schema_version': 'flowpilot.runtime_relay_operation.v1',
        'operation_type': 'controller_runtime_relay_envelope',
        'runtime_entrypoint': 'flowpilot_runtime.py relay-envelope',
        'runtime_args': args,
        'packet_id': packet_id,
        'packet_family': packet_family,
        'envelope_kind': envelope_kind,
        'envelope_path': envelope_rel,
        'received_from_role': source_role,
        'relayed_to_role': target_role,
        'postcondition': postcondition,
        'expected_relay_kind': 'packet_controller_relay' if envelope_kind == 'packet_envelope' else 'result_controller_relay',
        'expected_writes': sorted(dict.fromkeys(expected_writes)),
        'active_holder_lease_required': bool(holder_agent_id),
        'active_holder_lease_path': str(active_holder_item.get('active_holder_lease_path') or '') if isinstance(active_holder_item, dict) else '',
        'target_agent_id': holder_agent_id,
        'sealed_body_reads_allowed': False,
        'path_only_handoff_is_not_completion': True,
    }

def _packet_runtime_relay_operations(
    router: ModuleType,
    project_root: Path,
    run_state: dict[str, Any],
    records: list[dict[str, Any]],
    *,
    packet_family: str,
    postcondition: str,
    active_holder_plan: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    _bind_router(router)
    holder_plan = _active_holder_plan_by_packet(active_holder_plan)
    operations: list[dict[str, Any]] = []
    for record in records:
        envelope_path = router._packet_envelope_path_from_record(project_root, run_state, record)
        envelope = packet_runtime.load_envelope(project_root, envelope_path)
        packet_id = str(envelope.get('packet_id') or record.get('packet_id') or '')
        target_role = str(envelope.get('to_role') or record.get('to_role') or '')
        operations.append(
            _flowpilot_runtime_relay_operation(
                router,
                project_root,
                packet_id=packet_id,
                envelope_path=envelope_path,
                envelope_kind='packet_envelope',
                source_role=str(envelope.get('from_role') or record.get('from_role') or 'project_manager'),
                target_role=target_role,
                packet_family=packet_family,
                postcondition=postcondition,
                active_holder_item=holder_plan.get(packet_id),
            )
        )
    return operations

def _result_runtime_relay_operations(
    router: ModuleType,
    project_root: Path,
    run_state: dict[str, Any],
    records: list[dict[str, Any]],
    *,
    packet_family: str,
    postcondition: str,
    to_role: str,
) -> list[dict[str, Any]]:
    _bind_router(router)
    operations: list[dict[str, Any]] = []
    for record in records:
        result_path = router._result_envelope_path_from_packet_record(project_root, run_state, record)
        result = packet_runtime.load_envelope(project_root, result_path)
        packet_id = str(result.get('packet_id') or record.get('packet_id') or '')
        operations.append(
            _flowpilot_runtime_relay_operation(
                router,
                project_root,
                packet_id=packet_id,
                envelope_path=result_path,
                envelope_kind='result_envelope',
                source_role=str(result.get('completed_by_role') or record.get('to_role') or 'unknown'),
                target_role=to_role,
                packet_family=packet_family,
                postcondition=postcondition,
            )
        )
    return operations

__all__ = (
    "_flowpilot_runtime_relay_operation",
    "_packet_runtime_relay_operations",
    "_result_runtime_relay_operations",
)

_LOCAL_NAMES = set(globals())
