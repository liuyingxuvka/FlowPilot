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

import flowpilot_router_route_frontier_policy_registry as _route_frontier_child_0
import flowpilot_router_route_frontier_policy_topology as _route_frontier_child_1
import flowpilot_router_route_frontier_policy_completion as _route_frontier_child_2
from flowpilot_router_route_frontier_policy_registry import *
from flowpilot_router_route_frontier_policy_topology import *
from flowpilot_router_route_frontier_policy_completion import *

_OWNER_CHILD_MODULES = (
    _route_frontier_child_0,
    _route_frontier_child_1,
    _route_frontier_child_2,
)

__all__ = (
    'ROUTE_ACTION_POLICY_REQUIRED_BOOL_FLAGS',
    'ROUTE_ACTION_POLICY_EVENT_TO_ACTION',
    'ROUTE_ACTION_POLICY_CARD_TO_ACTION',
    'ROUTE_ACTION_POLICY_PARENT_CLOSURE_ACTIONS',
    'ROUTE_ACTION_POLICY_ROUTE_MOVEMENT_ACTIONS',
    '_latest_event_payload',
    '_route_action_policy_registry_path',
    '_load_route_action_policy_registry',
    '_route_action_policy_rows',
    '_route_action_policy_issues',
    '_validate_route_action_policy_registry',
    '_route_action_policy_by_id',
    '_active_frontier',
    '_active_route_path',
    '_active_route_flow',
    '_iter_route_nodes',
    '_active_node_definition',
    '_active_node_definition_from_route',
    '_is_route_root_like_node_id',
    '_route_mutation_review_lane',
    '_validate_route_mutation_phase_boundary',
    '_node_child_ids',
    '_active_node_has_children',
    '_route_node_map',
    '_route_descendant_node_ids',
    '_node_completion_ledger_path_for',
    '_node_completion_ledger_current',
    '_parent_segment_decision_value',
    '_route_action_for_event',
    '_route_action_for_card',
    '_legal_next_action_context',
    '_legal_next_action_ids',
    '_legal_route_action_allowed',
    '_first_incomplete_child_node_id',
    '_enter_next_child_node',
    '_next_parent_child_entry_action',
    '_require_legal_route_action',
    '_filter_events_by_legal_route_actions',
    '_write_node_completion_ledger',
    '_mark_current_node_packet_records_completed',
    '_mark_frontier_node_completed',
)

_LOCAL_NAMES = set(globals())
