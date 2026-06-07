"""Runtime delivery operation builders for current-node packet handoffs."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import packet_runtime
from flowpilot_router_work_packets_current_node_relay_leases import _active_holder_plan_by_packet


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
    holder_agent_id = ''
    if isinstance(active_holder_item, dict):
        holder_agent_id = str(active_holder_item.get('target_agent_id') or '').strip()
    args: list[str] = [
        'dispatch-current-role',
        '--packet-id',
        packet_id,
        '--responsibility',
        target_role,
        '--host-kind',
        'live',
    ]
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
        'schema_version': 'flowpilot.runtime_delivery_operation.v1',
        'operation_type': 'current_role_dispatch',
        'runtime_entrypoint': 'flowpilot_new.py dispatch-current-role',
        'runtime_args': args,
        'packet_id': packet_id,
        'packet_family': packet_family,
        'envelope_kind': envelope_kind,
        'envelope_path': envelope_rel,
        'received_from_role': source_role,
        'assigned_to_role': target_role,
        'postcondition': postcondition,
        'expected_delivery_kind': 'current_role_dispatch',
        'expected_writes': sorted(dict.fromkeys(expected_writes)),
        'active_holder_lease_required': False,
        'active_holder_lease_path': str(active_holder_item.get('active_holder_lease_path') or '') if isinstance(active_holder_item, dict) else '',
        'target_agent_id': '',
        'prior_target_agent_id_observed': holder_agent_id,
        'lease_commit_requires_role_assignment_id': False,
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
