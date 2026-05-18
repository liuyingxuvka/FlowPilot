"""Compatibility facade for terminal ledger helpers.

This compatibility facade preserves the original import path while focused
child modules own the implementation groups.
"""

from __future__ import annotations

from types import ModuleType


def _bind_router(router: ModuleType) -> None:
    current = globals()
    local_names = current.get('_LOCAL_NAMES', set())
    for name, value in vars(router).items():
        if name.startswith('__') and name.endswith('__'):
            continue
        if name in local_names:
            continue
        current[name] = value
    for child_module in globals().get("_OWNER_CHILD_MODULES", ()):
        if hasattr(child_module, "_bind_router"):
            child_module._bind_router(router)


import flowpilot_router_terminal_ledger_summary as _owner_child_0
import flowpilot_router_terminal_ledger_traceability as _owner_child_1
import flowpilot_router_terminal_ledger_closure as _owner_child_2
import flowpilot_router_terminal_ledger_recovery as _owner_child_3
from flowpilot_router_terminal_ledger_summary import *
from flowpilot_router_terminal_ledger_traceability import *
from flowpilot_router_terminal_ledger_closure import *
from flowpilot_router_terminal_ledger_recovery import *

_OWNER_CHILD_MODULES = (
    _owner_child_0,
    _owner_child_1,
    _owner_child_2,
    _owner_child_3,
)

__all__ = (
    '_terminal_summary_index_entry',
    '_terminal_summary_written',
    '_terminal_summary_action',
    '_validate_terminal_summary_payload',
    '_write_terminal_summary',
    '_root_requirement_ids',
    '_string_list',
    '_route_nodes_with_requirement_trace',
    '_node_acceptance_traceability_issues',
    '_requirement_trace_closure_from_root_replay',
    '_final_ledger_traceability_issues',
    '_validated_root_replay',
    '_build_source_of_truth_final_entries',
    '_route_mutation_completion_issues',
    '_write_final_route_wide_ledger',
    '_terminal_closure_suite_is_closed',
    '_write_terminal_backward_replay',
    '_write_task_completion_projection',
    '_write_terminal_closure_suite',
    '_recover_terminal_status_from_run_authorities',
    '_repair_legacy_material_packet_contracts',
    'reconcile_current_run',
)

_LOCAL_NAMES = set(globals())
