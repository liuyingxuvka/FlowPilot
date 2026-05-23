"""Compatibility facade for current-node work-packet helpers.

The implementation lives in focused child modules. This facade preserves the
historical import path, helper names, ``__all__`` order, and router-binding
handoff used by the router skeleton.
"""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_work_packets_current_node_paths as _current_node_paths
from flowpilot_router_work_packets_current_node_paths import (
    _packet_paths,
    _active_current_node_packet_records,
    _current_node_batch_packet_record,
    _packet_envelope_path,
    _result_envelope_path,
    _current_node_packet_context,
    _current_node_packet_records,
    _current_node_results_complete,
    _current_node_missing_result_roles,
    _active_child_skill_bindings_from_plan,
    _active_child_skill_source_paths,
    _metadata_string_list,
    _metadata_binding_ids,
    _current_node_result_context,
    _packet_envelope_path_from_record,
    _result_envelope_path_from_packet_record,
    _load_packet_index,
    _ensure_barrier_bundles_ready,
    _material_scan_index_path,
    _research_packet_index_path,
)
import flowpilot_router_work_packets_current_node_relay as _current_node_relay
from flowpilot_router_work_packets_current_node_relay import (
    _relay_packet_records,
    _active_holder_frontier_version,
    _current_node_active_holder_lease_plan,
    _issue_current_node_active_holder_leases,
    _packet_active_holder_lease_plan,
    _issue_packet_active_holder_leases,
    _packet_runtime_relay_operations,
    _result_runtime_relay_operations,
    _relay_result_records,
    _agent_role_map_from_crew_ledger,
    _merge_agent_role_maps,
    _validate_packet_bodies_opened_by_targets,
    _validate_results_exist_for_packets,
    _validate_packet_group_for_reviewer,
)
import flowpilot_router_work_packets_current_node_validation as _current_node_validation
from flowpilot_router_work_packets_current_node_validation import (
    _validate_current_node_packet_envelope,
    _validate_current_node_packet_event,
    _validate_current_node_result_event,
    _validate_current_node_reviewer_pass,
    _next_current_node_packet_action,
    _controller_status_packet_path_from_packet_envelope,
    _role_output_status_packet_path_for_wait,
    _try_reconcile_current_node_results,
)

_BOUND_ROUTER: ModuleType | None = None

_CHILD_MODULES = (
    _current_node_paths,
    _current_node_relay,
    _current_node_validation,
)


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    _BOUND_ROUTER = router
    for module in _CHILD_MODULES:
        module._bind_router(router)
    current = globals()
    local_names = current.get('_LOCAL_NAMES', set())
    for name, value in vars(router).items():
        if name.startswith('__') and name.endswith('__'):
            continue
        if name in local_names:
            continue
        current[name] = value


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError('router skeleton is not bound')
    return _BOUND_ROUTER

__all__ = (
    '_packet_paths',
    '_active_current_node_packet_records',
    '_current_node_batch_packet_record',
    '_packet_envelope_path',
    '_result_envelope_path',
    '_current_node_packet_context',
    '_current_node_packet_records',
    '_current_node_results_complete',
    '_current_node_missing_result_roles',
    '_active_child_skill_bindings_from_plan',
    '_active_child_skill_source_paths',
    '_metadata_string_list',
    '_metadata_binding_ids',
    '_current_node_result_context',
    '_packet_envelope_path_from_record',
    '_result_envelope_path_from_packet_record',
    '_load_packet_index',
    '_ensure_barrier_bundles_ready',
    '_material_scan_index_path',
    '_research_packet_index_path',
    '_relay_packet_records',
    '_active_holder_frontier_version',
    '_current_node_active_holder_lease_plan',
    '_issue_current_node_active_holder_leases',
    '_packet_active_holder_lease_plan',
    '_issue_packet_active_holder_leases',
    '_packet_runtime_relay_operations',
    '_result_runtime_relay_operations',
    '_relay_result_records',
    '_agent_role_map_from_crew_ledger',
    '_merge_agent_role_maps',
    '_validate_packet_bodies_opened_by_targets',
    '_validate_results_exist_for_packets',
    '_validate_packet_group_for_reviewer',
    '_validate_current_node_packet_envelope',
    '_validate_current_node_packet_event',
    '_validate_current_node_result_event',
    '_validate_current_node_reviewer_pass',
    '_next_current_node_packet_action',
    '_controller_status_packet_path_from_packet_envelope',
    '_role_output_status_packet_path_for_wait',
    '_try_reconcile_current_node_results',
)

_LOCAL_NAMES = set(globals())
