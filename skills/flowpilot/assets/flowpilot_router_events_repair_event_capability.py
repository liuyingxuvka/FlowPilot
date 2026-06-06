"""Coarse events repair owner helpers for the FlowPilot router.

The public router names stay in `flowpilot_router`. This module owns a
cohesive behavior family and receives the router facade as an explicit runtime
dependency so shared state writers and public entrypoints remain compatible.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Iterable

import card_runtime
import flowpilot_runtime_closure
import flowpilot_user_flow_diagram
import packet_runtime
import role_output_runtime
from flowpilot_prompt_store import PromptStoreError, card_manifest_entry, load_card_manifest_from_run
from flowpilot_router_errors import RouterError, RouterLedgerCorruptionError, RouterLedgerWriteInProgress

_DEFAULT_SENTINEL = object()
_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get('_LOCAL_NAMES', set())
    for name, value in vars(router).items():
        if name.startswith('__') and name.endswith('__'):
            continue
        if name in local_names:
            continue
        current[name] = value

def _validated_external_event_names(router: ModuleType, events: Any, *, context: str, allow_pm_repair_event: bool=True) -> list[str]:
    _bind_router(router)
    if not isinstance(events, list) or not events:
        raise RouterError(f'{context} requires a non-empty allowed_external_events list')
    normalized: list[str] = []
    invalid: list[str] = []
    for item in events:
        name = router._control_resolution_event_name(item)
        if not name:
            invalid.append(str(item))
            continue
        if name == PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT and (not allow_pm_repair_event):
            invalid.append(name)
            continue
        if name not in EXTERNAL_EVENTS:
            invalid.append(name)
            continue
        if name not in normalized:
            normalized.append(name)
    if invalid:
        raise RouterError(f"{context} contains unregistered external event(s): {', '.join(invalid)}")
    return normalized

def _active_node_kind_for_event_capability(router: ModuleType, run_root: Path | None) -> str | None:
    _bind_router(router)
    if run_root is None:
        return None
    try:
        frontier = router._active_frontier(run_root)
        node = router._active_node_definition(run_root, frontier)
    except (OSError, KeyError, RouterError, json.JSONDecodeError, ValueError, TypeError):
        return None
    kind = router._node_kind(node)
    if router._node_child_ids(node) and kind not in {'parent', 'module'}:
        return 'parent'
    return kind or None

def _event_capability_issue(router: ModuleType, event: str, *, run_root: Path | None=None, run_state: dict[str, Any] | None=None, usage: str='wait', repair_origin: str | None=None, outcome_kind: str | None=None, currently_receivable: bool=True) -> str | None:
    _bind_router(router)
    if event not in EXTERNAL_EVENTS:
        return 'event is not registered'
    if not currently_receivable:
        return 'event is not currently receivable'
    if usage == 'rerun_target' and event in {PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT, *CONTROL_BLOCKER_REPAIR_NON_SUCCESS_EVENTS, PM_PARENT_PROTOCOL_BLOCKER_EVENT}:
        return 'event cannot be used as a repair rerun target'
    active_node_kind = router._active_node_kind_for_event_capability(run_root)
    if active_node_kind in {'parent', 'module'} and event in LEAF_CURRENT_NODE_EVENT_CAPABILITY_EVENTS:
        return 'event is incompatible with parent/module active node'
    if active_node_kind in {'leaf', 'repair'} and event in PARENT_NODE_EVENT_CAPABILITY_EVENTS:
        return 'event requires a parent/module active node'
    active_node_has_children = _active_node_children_status(run_root)
    meta = EXTERNAL_EVENTS.get(event) or {}
    if not _event_applicable_for_active_node(meta, active_node_has_children):
        return 'event is incompatible with active node child state'
    origin = repair_origin or 'none'
    if origin == 'parent_backward_replay' and event not in PARENT_REPAIR_SAFE_EVENTS:
        return 'parent backward replay repair cannot target this event'
    if usage == 'repair_outcome':
        if outcome_kind == 'success' and event in CONTROL_BLOCKER_REPAIR_NON_SUCCESS_EVENTS | {PM_PARENT_PROTOCOL_BLOCKER_EVENT}:
            return 'repair success outcome cannot use a non-success event'
        if outcome_kind == 'blocker' and event not in CONTROL_BLOCKER_REPAIR_NON_SUCCESS_EVENTS | {'reviewer_blocks_parent_backward_replay', 'router_direct_material_scan_dispatch_recheck_blocked'}:
            return 'repair blocker outcome must use a blocker-capable event'
        if outcome_kind == 'protocol_blocker' and event not in {PM_CONTROL_BLOCKER_PROTOCOL_BLOCKER_EVENT, PM_PARENT_PROTOCOL_BLOCKER_EVENT, 'router_protocol_blocker_material_scan_dispatch_recheck'}:
            return 'repair protocol-blocker outcome must use a protocol-blocker-capable event'
    if usage == 'wait' and origin == 'control_plane_reissue':
        return None
    required_flag = meta.get('requires_flag')
    if usage in {'wait', 'rerun_target'} and run_state is not None and required_flag and (not run_state.get('flags', {}).get(required_flag)):
        return f'event requires unsatisfied flag {required_flag}'
    return None

def _run_state_with_assumed_flag(router: ModuleType, run_state: dict[str, Any], flag: str) -> dict[str, Any]:
    _bind_router(router)
    assumed = dict(run_state)
    flags = dict(run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {})
    flags[flag] = True
    assumed['flags'] = flags
    return assumed

def _validated_event_capability_names(router: ModuleType, events: Any, *, context: str, run_root: Path | None=None, run_state: dict[str, Any] | None=None, usage: str='wait', repair_origin: str | None=None, outcome_kind: str | None=None, allow_pm_repair_event: bool=True, currently_receivable: bool=True) -> list[str]:
    _bind_router(router)
    normalized = router._validated_external_event_names(events, context=context, allow_pm_repair_event=allow_pm_repair_event)
    issues = [f'{event}: {issue}' for event in normalized if (issue := router._event_capability_issue(event, run_root=run_root, run_state=run_state, usage=usage, repair_origin=repair_origin, outcome_kind=outcome_kind, currently_receivable=currently_receivable))]
    if issues:
        raise RouterError(f"{context} contains non-executable external event(s): {', '.join(issues)}")
    return normalized

def _external_event_validation_issue(router: ModuleType, events: Any) -> dict[str, Any] | None:
    _bind_router(router)
    try:
        router._validated_external_event_names(events, context='event validation')
    except RouterError as exc:
        return {'reason': 'invalid_allowed_external_events', 'error': str(exc)}
    return None

def _control_blocker_allowed_resolution_events(router: ModuleType, category: str, event: str | None) -> list[str]:
    _bind_router(router)
    if category == 'control_plane_reissue' and event:
        return router._validated_external_event_names([event], context='control-plane reissue resolution')
    if category in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES:
        return [PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT]
    return sorted(EXTERNAL_EVENTS)

def _control_blocker_policy(router: ModuleType, category: str, *, responsible_role: str, event: str | None, policy_row: dict[str, Any], target_role: str) -> dict[str, Any]:
    _bind_router(router)
    if category == 'control_plane_reissue' and target_role != 'project_manager':
        instruction = f'Deliver the sealed repair packet envelope to `{target_role}` and request a same-role reissue of the rejected control-plane output. Controller may route the packet path, hash, policy row, and retry count only.'
        allowed = ['read this control blocker artifact', 'deliver sealed_repair_packet_path and sealed_repair_packet_hash to the responsible role', 'quote policy_row_id, direct_retry_budget, and direct_retry_attempts_used', 'tell the responsible role to reissue the same control-plane output']
        forbidden = ['open sealed packet/result/report bodies', 'infer project status from chat history', 'ask a worker to change project substance', 'convert the router rejection into PM-owned evidence']
        pm_required = False
    elif category == 'fatal_protocol_violation':
        instruction = 'Stop normal route work and deliver this control blocker to `project_manager` for escalation. Controller may route the sealed repair packet envelope only and must not repair the route from chat.'
        allowed = ['read this control blocker artifact', 'deliver sealed_repair_packet_path and sealed_repair_packet_hash to project_manager', 'wait for an explicit PM or user recovery decision']
        forbidden = ['open sealed packet/result/report bodies', 'contact the worker directly', 'advance, close, or mutate the route', 'treat controller-visible leaked content as evidence']
        pm_required = True
    else:
        instruction = 'Deliver the sealed repair packet envelope to `project_manager` for a repair decision. Controller must not decide whether the work is substantively acceptable and must not inspect or restate the repair details. PM must choose a policy-listed recovery option and name the gate or terminal stop that follows.'
        allowed = ['read this control blocker artifact', 'deliver sealed_repair_packet_path and sealed_repair_packet_hash to project_manager', 'quote blocker_id, error_code, handling_lane, target_role, policy_row_id, return_policy, and pm_recovery_options']
        forbidden = ['open sealed packet/result/report bodies', 'contact the worker directly about project repair', 'summarize reviewer or worker body content', 'advance route state from the rejected event']
        pm_required = True
    return {'target_role': target_role, 'pm_decision_required': pm_required, 'controller_instruction': instruction, 'controller_allowed_actions': allowed, 'controller_forbidden_actions': forbidden, 'allowed_resolution_events': router._control_blocker_allowed_resolution_events(category, event), 'policy_row_id': policy_row.get('policy_row_id'), 'blocker_family': policy_row.get('blocker_family')}

__all__ = (
    '_validated_external_event_names',
    '_active_node_kind_for_event_capability',
    '_event_capability_issue',
    '_run_state_with_assumed_flag',
    '_validated_event_capability_names',
    '_external_event_validation_issue',
    '_control_blocker_allowed_resolution_events',
    '_control_blocker_policy',
)

_LOCAL_NAMES = set(globals())
