"""PM role-work owner compatibility facade for the FlowPilot router.

The behavior is split into gate mappings, request/result writes, request index
and officer lifecycle, and next-action reconciliation helpers. Public import
names remain available from this module.
"""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_work_packets_pm_role_gates as _owner_child_0
import flowpilot_router_work_packets_pm_role_writes as _owner_child_1
import flowpilot_router_work_packets_pm_role_lifecycle as _owner_child_2
import flowpilot_router_work_packets_pm_role_actions as _owner_child_3
from flowpilot_router_work_packets_pm_role_gates import *
from flowpilot_router_work_packets_pm_role_writes import *
from flowpilot_router_work_packets_pm_role_lifecycle import *
from flowpilot_router_work_packets_pm_role_actions import *

_OWNER_CHILD_MODULES = (
    _owner_child_0,
    _owner_child_1,
    _owner_child_2,
    _owner_child_3,
)


def _bind_router(router: ModuleType) -> None:
    current = globals()
    local_names = current.get('_LOCAL_NAMES', set())
    for name, value in vars(router).items():
        if name.startswith('__') and name.endswith('__'):
            continue
        if name in local_names:
            continue
        current[name] = value
    for child_module in _OWNER_CHILD_MODULES:
        child_module._bind_router(router)


__all__ = (
    '_pm_role_work_target_gate_contract',
    '_pm_role_work_gate_mapping_candidates',
    '_pm_role_work_gate_mapping_artifact_path',
    '_pm_role_work_gate_mapping_alias_specs',
    '_pm_role_work_gate_mappings_for_decision',
    '_apply_pm_role_work_gate_mappings',
    '_pm_role_work_result_decision_payload_contract',
    '_write_pm_role_work_request',
    '_normalize_pm_role_work_result_recipient',
    '_validate_role_work_result_process_binding',
    '_write_role_work_result_returned',
    '_write_pm_role_work_result_decision',
    '_validate_result_bodies_opened_by_pm',
    '_write_pm_package_result_disposition',
    '_pm_role_work_request_index_path',
    '_empty_pm_role_work_request_index',
    '_load_pm_role_work_request_index',
    '_write_pm_role_work_request_index',
    '_officer_request_lifecycle_index_path',
    '_empty_officer_request_lifecycle_index',
    '_load_officer_request_lifecycle_index',
    '_officer_lifecycle_entry',
    '_upsert_officer_lifecycle_entry',
    '_write_officer_request_lifecycle_index',
    '_record_officer_lifecycle_request',
    '_record_officer_lifecycle_status',
    '_record_officer_lifecycle_result_returned',
    '_record_officer_lifecycle_pm_decision',
    '_pm_role_work_request_record',
    '_active_pm_role_work_request',
    '_active_pm_role_work_batch_records',
    '_unresolved_pm_role_work_requests',
    '_safe_packet_id_component',
    '_pm_role_work_request_body_text',
    '_validate_pm_role_work_process_contract_binding',
    '_pm_role_work_packet_type_from_contract',
    '_pm_role_work_output_contract',
    '_pm_role_work_record_is_nonblocking',
    '_pm_role_work_records_are_nonblocking',
    '_pm_role_work_records_dependency_class',
    '_unresolved_advisory_pm_role_work_records',
    '_next_pm_role_work_request_action',
    '_try_reconcile_pm_role_work_results',
)

_LOCAL_NAMES = set(globals())
