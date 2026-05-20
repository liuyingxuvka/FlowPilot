"""Cohesive child helpers for FlowPilot route-frontier compatibility facades."""

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

ROUTE_ACTION_POLICY_REQUIRED_BOOL_FLAGS = (
    "router_must_compute_before_pm_decision",
    "router_must_validate_before_event_acceptance",
    "router_must_validate_before_commit",
    "pm_may_choose_only_from_legal_next_actions",
)

ROUTE_ACTION_POLICY_EVENT_TO_ACTION = {
    "pm_builds_parent_backward_targets": "build_parent_backward_targets",
    "reviewer_passes_parent_backward_replay": "review_parent_backward_replay",
    "reviewer_blocks_parent_backward_replay": "review_parent_backward_replay",
    "pm_records_parent_segment_decision": "record_parent_segment_decision",
    "pm_completes_parent_node_from_backward_replay": "complete_parent_node",
    "pm_mutates_route_after_review_block": "mutate_route",
    "pm_approves_terminal_closure": "terminal_closure",
}

ROUTE_ACTION_POLICY_CARD_TO_ACTION = {
    "pm.parent_backward_targets": "build_parent_backward_targets",
    "reviewer.parent_backward_replay": "review_parent_backward_replay",
    "pm.parent_segment_decision": "record_parent_segment_decision",
    "pm.closure": "terminal_closure",
}

ROUTE_ACTION_POLICY_PARENT_CLOSURE_ACTIONS = {
    "build_parent_backward_targets",
    "review_parent_backward_replay",
    "record_parent_segment_decision",
    "complete_parent_node",
}

ROUTE_ACTION_POLICY_ROUTE_MOVEMENT_ACTIONS = set(ROUTE_ACTION_POLICY_EVENT_TO_ACTION.values())


def _bind_router(router: ModuleType) -> None:
    current = globals()
    local_names = current.get('_LOCAL_NAMES', set())
    for name, value in vars(router).items():
        if name.startswith('__') and name.endswith('__'):
            continue
        if name in local_names:
            continue
        current[name] = value

def _latest_event_payload(router: ModuleType, run_state: dict[str, Any], event_name: str) -> dict[str, Any]:
    _bind_router(router)
    for event in reversed(run_state.get('events', [])):
        if isinstance(event, dict) and event.get('event') == event_name:
            payload = event.get('payload')
            return payload if isinstance(payload, dict) else {}
    return {}


def _route_action_policy_registry_path(router: ModuleType, run_root: Path | None=None) -> Path:
    _bind_router(router)
    if run_root is not None:
        candidate = run_root / 'runtime_kit' / 'route_action_policy_registry.json'
        if candidate.exists():
            return candidate
    return runtime_kit_source() / 'route_action_policy_registry.json'


def _load_route_action_policy_registry(router: ModuleType, run_root: Path | None=None) -> dict[str, Any]:
    _bind_router(router)
    return read_json(router._route_action_policy_registry_path(run_root))


def _route_action_policy_rows(router: ModuleType, run_root: Path | None=None) -> list[dict[str, Any]]:
    _bind_router(router)
    registry = router._load_route_action_policy_registry(run_root)
    rows = registry.get('route_actions')
    if not isinstance(rows, list):
        raise RouterError('route action policy registry requires route_actions list')
    return [row for row in rows if isinstance(row, dict)]


def _route_action_policy_issues(router: ModuleType, run_root: Path | None=None) -> list[str]:
    _bind_router(router)
    issues: list[str] = []
    try:
        registry = router._load_route_action_policy_registry(run_root)
    except Exception as exc:
        return [f'route action policy registry cannot be loaded: {exc}']
    if registry.get('schema_version') != ROUTE_ACTION_POLICY_REGISTRY_SCHEMA:
        issues.append('route action policy registry schema_version mismatch')
    if registry.get('authority') != 'router':
        issues.append('route action policy registry authority must be router')
    for field in ROUTE_ACTION_POLICY_REQUIRED_BOOL_FLAGS:
        if registry.get(field) is not True:
            issues.append(f'route action policy registry requires {field}=true')
    raw_rows = registry.get('route_actions')
    if not isinstance(raw_rows, list) or not raw_rows:
        issues.append('route action policy registry requires non-empty route_actions list')
        return issues
    transaction_types = {str(row.get('transaction_type')) for row in _control_transaction_registry_rows(run_root)}
    seen: set[str] = set()
    for index, row in enumerate(raw_rows):
        if not isinstance(row, dict):
            issues.append(f'route_actions[{index}] must be an object')
            continue
        action_id = str(row.get('action_id') or '').strip()
        context = action_id or f'route_actions[{index}]'
        if not action_id:
            issues.append(f'{context}: action_id is required')
        elif action_id in seen:
            issues.append(f'{context}: duplicate action_id')
        seen.add(action_id)
        for field in ('actor_roles', 'router_events', 'requires', 'forbids', 'commit_targets'):
            if not isinstance(row.get(field), list):
                issues.append(f'{context}: {field} must be a list')
        transaction_type = str(row.get('transaction_type') or '').strip()
        if transaction_type not in transaction_types:
            issues.append(f'{context}: transaction_type is not registered: {transaction_type}')
        for event in row.get('router_events', []) if isinstance(row.get('router_events'), list) else []:
            if str(event) not in EXTERNAL_EVENTS:
                issues.append(f'{context}: router_event is not registered: {event}')
        for target in row.get('commit_targets', []) if isinstance(row.get('commit_targets'), list) else []:
            if str(target) not in CONTROL_TRANSACTION_COMMIT_TARGETS:
                issues.append(f'{context}: unsupported commit_target: {target}')
    return issues


def _validate_route_action_policy_registry(router: ModuleType, run_root: Path | None=None) -> None:
    _bind_router(router)
    issues = router._route_action_policy_issues(run_root)
    if issues:
        raise RouterError('route action policy registry invalid: ' + '; '.join(issues))


def _route_action_policy_by_id(router: ModuleType, run_root: Path | None=None) -> dict[str, dict[str, Any]]:
    _bind_router(router)
    router._validate_route_action_policy_registry(run_root)
    return {str(row['action_id']): row for row in router._route_action_policy_rows(run_root)}


def _route_action_for_event(router: ModuleType, event: str) -> str | None:
    _bind_router(router)
    return ROUTE_ACTION_POLICY_EVENT_TO_ACTION.get(str(event))


def _route_action_for_card(router: ModuleType, card_id: str) -> str | None:
    _bind_router(router)
    return ROUTE_ACTION_POLICY_CARD_TO_ACTION.get(str(card_id))


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
    '_route_action_for_event',
    '_route_action_for_card',
)

_LOCAL_NAMES = set(globals())
