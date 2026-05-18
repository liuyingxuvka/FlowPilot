"""Compatibility facade for route-frontier helpers."""

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
    for child_module in globals().get('_OWNER_CHILD_MODULES', ()):
        if hasattr(child_module, '_bind_router'):
            child_module._bind_router(router)

import flowpilot_router_route_frontier_status_catalog as _route_frontier_child_0
import flowpilot_router_route_frontier_status_summary as _route_frontier_child_1
import flowpilot_router_route_frontier_status_views as _route_frontier_child_2
from flowpilot_router_route_frontier_status_catalog import *
from flowpilot_router_route_frontier_status_summary import *
from flowpilot_router_route_frontier_status_views import *

_OWNER_CHILD_MODULES = (
    _route_frontier_child_0,
    _route_frontier_child_1,
    _route_frontier_child_2,
)

__all__ = (
    '_active_ui_task_catalog',
    '_route_node_checklist',
    '_active_route_payload',
    '_current_status_summary_path',
    '_run_elapsed_seconds',
    '_route_progress_parent_map',
    '_route_progress_completed_ids',
    '_route_progress_path_nodes',
    '_build_progress_summary',
    '_route_node_label',
    '_status_summary_waiting_for',
    '_current_status_active_batch_summary',
    '_build_current_status_summary',
    '_write_current_status_summary',
    '_build_route_state_snapshot',
    '_write_route_state_snapshot',
    '_mark_display_plan_dirty',
    '_write_display_plan_from_route',
    '_update_display_plan_current_node',
    '_latest_pre_route_phase',
    '_sync_execution_frontier_phase',
    '_write_pre_route_phase_display_plan_if_needed',
    '_reconcile_non_current_running_index_entries',
    '_sync_derived_run_views',
    '_write_display_plan_from_pm_payload',
)

_LOCAL_NAMES = set(globals())
