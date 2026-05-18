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

import flowpilot_router_route_frontier_context_memory as _route_frontier_child_0
import flowpilot_router_route_frontier_context_cards as _route_frontier_child_1
import flowpilot_router_route_frontier_context_drafts as _route_frontier_child_2
from flowpilot_router_route_frontier_context_memory import *
from flowpilot_router_route_frontier_context_cards import *
from flowpilot_router_route_frontier_context_drafts import *

_OWNER_CHILD_MODULES = (
    _route_frontier_child_0,
    _route_frontier_child_1,
    _route_frontier_child_2,
)

__all__ = (
    '_event_markers',
    '_route_node_history',
    '_refresh_route_memory',
    '_require_pm_prior_path_context',
    '_pm_context_action_extra',
    '_card_required_source_paths',
    '_card_delivery_phase',
    '_live_card_delivery_context',
    '_matching_controller_delivery_actions',
    '_controller_delivery_fact_for_pending_return',
    '_write_route_draft',
    '_reset_route_review_after_route_draft_repair',
    '_reset_route_hard_gate_approvals_for_recheck',
    '_product_behavior_model_report_path',
    '_product_behavior_model_compatibility_report_path',
    '_require_product_behavior_model_report',
    '_route_process_check_path',
    '_process_route_model_report_path',
    '_require_process_route_model_report',
    '_route_product_check_path',
    '_require_route_process_pass',
    '_supersede_active_current_node_packet_for_route_mutation',
    '_require_route_product_pass',
    '_current_route_draft_path',
)

_LOCAL_NAMES = set(globals())
