"""PM role-work request index and FlowGuard operator lifecycle public facade."""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_work_packets_pm_role_lifecycle_index as _owner_child_0
import flowpilot_router_work_packets_pm_role_lifecycle_flowguard_operator as _owner_child_1
import flowpilot_router_work_packets_pm_role_lifecycle_contracts as _owner_child_2
from flowpilot_router_work_packets_pm_role_lifecycle_index import *
from flowpilot_router_work_packets_pm_role_lifecycle_flowguard_operator import *
from flowpilot_router_work_packets_pm_role_lifecycle_contracts import *

_OWNER_CHILD_MODULES = (
    _owner_child_0,
    _owner_child_1,
    _owner_child_2,
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
    '_pm_role_work_request_index_path',
    '_empty_pm_role_work_request_index',
    '_load_pm_role_work_request_index',
    '_write_pm_role_work_request_index',
    '_flowguard_operator_request_lifecycle_index_path',
    '_empty_flowguard_operator_request_lifecycle_index',
    '_load_flowguard_operator_request_lifecycle_index',
    '_flowguard_operator_lifecycle_entry',
    '_upsert_flowguard_operator_lifecycle_entry',
    '_write_flowguard_operator_request_lifecycle_index',
    '_record_flowguard_operator_lifecycle_request',
    '_record_flowguard_operator_lifecycle_status',
    '_record_flowguard_operator_lifecycle_result_returned',
    '_record_flowguard_operator_lifecycle_pm_decision',
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
)

_LOCAL_NAMES = set(globals())
