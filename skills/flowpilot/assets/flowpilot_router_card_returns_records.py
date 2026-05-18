"""Card return helper shard for FlowPilot router."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import card_runtime

def _pending_return_records(router: ModuleType, run_root: Path, run_id: str) -> list[dict[str, Any]]:
    ledger = router._read_return_event_ledger(run_root, run_id)
    completed_keys: set[tuple[str, str, str]] = set()
    for item in ledger.get('completed_returns', []):
        if not isinstance(item, dict) or item.get('status') != 'resolved':
            continue
        return_kind = str(item.get('return_kind') or 'system_card')
        identity = str(item.get('card_bundle_id') or item.get('delivery_attempt_id') or '')
        event_name = str(item.get('card_return_event') or '')
        if identity and event_name:
            completed_keys.add((return_kind, identity, event_name))
    pending: list[dict[str, Any]] = []
    for item in ledger.get('pending_returns', []):
        if not isinstance(item, dict):
            continue
        status = item.get('status')
        if status == 'returned':
            return_kind = str(item.get('return_kind') or 'system_card')
            identity = str(item.get('card_bundle_id') or item.get('delivery_attempt_id') or '')
            event_name = str(item.get('card_return_event') or '')
            if item.get('resolved_at') or (return_kind, identity, event_name) in completed_keys:
                continue
        if status in {None, 'pending', 'awaiting_return', 'reminded', 'returned', 'bundle_ack_incomplete', 'invalid_ack_pending_explicit_check'}:
            pending.append(item)
    return pending

def _card_return_resolved_for_action(router: ModuleType, run_root: Path, run_id: str, action: dict[str, Any]) -> bool:
    action_type = str(action.get('action_type') or '')
    if action_type not in {'deliver_system_card', 'deliver_system_card_bundle'}:
        return False
    ledger = router._read_return_event_ledger(run_root, run_id)
    if action_type == 'deliver_system_card_bundle':
        bundle_id = str(action.get('card_bundle_id') or '')
        return bool(bundle_id and any((isinstance(item, dict) and item.get('status') == 'resolved' and (item.get('return_kind') == 'system_card_bundle') and (item.get('card_bundle_id') == bundle_id) for item in ledger.get('completed_returns', []))))
    delivery_attempt_id = str(action.get('delivery_attempt_id') or '')
    return bool(delivery_attempt_id and any((isinstance(item, dict) and item.get('status') == 'resolved' and (item.get('return_kind', 'system_card') == 'system_card') and (item.get('delivery_attempt_id') == delivery_attempt_id) for item in ledger.get('completed_returns', []))))

def _pending_card_return_ack_exists(router: ModuleType, project_root: Path, pending_action: object) -> bool:
    if not isinstance(pending_action, dict) or pending_action.get('action_type') not in {'await_card_return_event', 'await_card_bundle_return_event', 'check_card_return_event', 'check_card_bundle_return_event', 'deliver_system_card', 'deliver_system_card_bundle'}:
        return False
    raw_path = pending_action.get('expected_return_path')
    return isinstance(raw_path, str) and raw_path and router.resolve_project_path(project_root, raw_path).exists()

def _pending_return_card_ids(router: ModuleType, pending_return: dict[str, Any]) -> set[str]:
    card_ids: set[str] = set()
    if pending_return.get('return_kind') == 'system_card_bundle':
        raw_card_ids = pending_return.get('card_ids')
        if isinstance(raw_card_ids, list):
            card_ids.update((str(card_id) for card_id in raw_card_ids if str(card_id or '').strip()))
    else:
        card_id = str(pending_return.get('card_id') or '').strip()
        if card_id:
            card_ids.add(card_id)
    scope = pending_return.get('ack_clearance_scope')
    if isinstance(scope, dict):
        scoped_card_id = str(scope.get('card_id') or '').strip()
        if scoped_card_id:
            card_ids.add(scoped_card_id)
        member_scopes = scope.get('member_scopes')
        if isinstance(member_scopes, list):
            for member in member_scopes:
                if isinstance(member, dict):
                    scoped_member_id = str(member.get('card_id') or '').strip()
                    if scoped_member_id:
                        card_ids.add(scoped_member_id)
    return card_ids

def _pending_return_is_startup_async_scope(router: ModuleType, pending_return: dict[str, Any]) -> bool:
    card_ids = router._pending_return_card_ids(pending_return)
    return bool(card_ids) and card_ids.issubset(router.STARTUP_ASYNC_CARD_IDS)

def _pending_return_is_pre_review_startup_scope(router: ModuleType, pending_return: dict[str, Any]) -> bool:
    card_ids = router._pending_return_card_ids(pending_return)
    return bool(card_ids) and card_ids.issubset(router.PRE_REVIEW_STARTUP_CARD_IDS)

def _startup_pre_review_card_flags(router: ModuleType) -> set[str]:
    flags: set[str] = set()
    for entry in router.SYSTEM_CARD_SEQUENCE:
        if entry.get('card_id') in router.PRE_REVIEW_STARTUP_CARD_IDS:
            flag = str(entry.get('flag') or '')
            if flag:
                flags.add(flag)
    return flags

def _startup_pre_review_cards_delivered(router: ModuleType, run_state: dict[str, Any]) -> bool:
    flags = run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {}
    required_flags = router._startup_pre_review_card_flags()
    return bool(required_flags) and all((flags.get(flag) for flag in required_flags))

def _startup_pre_review_pending_returns(router: ModuleType, run_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    return [record for record in router._pending_return_records(run_root, str(run_state['run_id'])) if router._pending_return_is_pre_review_startup_scope(record)]

def _startup_pre_review_ack_join_clean(router: ModuleType, run_root: Path, run_state: dict[str, Any]) -> bool:
    return router._startup_pre_review_cards_delivered(run_state) and (not router._startup_pre_review_pending_returns(run_root, run_state))

def _pending_return_matches_active_node_scope(router: ModuleType, pending_return: dict[str, Any], frontier: dict[str, Any]) -> bool:
    scope = pending_return.get('ack_clearance_scope')
    if not isinstance(scope, dict):
        return False
    active_node_id = str(frontier.get('active_node_id') or '')
    if not active_node_id or str(scope.get('current_node_id') or '') != active_node_id:
        return False
    raw_scope_version = scope.get('route_version')
    raw_frontier_version = frontier.get('route_version')
    if raw_scope_version in (None, '') or raw_frontier_version in (None, ''):
        return True
    try:
        return int(raw_scope_version) == int(raw_frontier_version)
    except (TypeError, ValueError):
        return str(raw_scope_version) == str(raw_frontier_version)

def _pending_return_is_outside_active_node_scope(router: ModuleType, run_root: Path, pending_return: dict[str, Any]) -> bool:
    scope = pending_return.get('ack_clearance_scope')
    if not isinstance(scope, dict):
        return False
    scoped_node_id = str(scope.get('current_node_id') or '')
    if not scoped_node_id:
        return False
    frontier = router.read_json_if_exists(run_root / 'execution_frontier.json')
    active_node_id = str(frontier.get('active_node_id') or '')
    if not active_node_id:
        return False
    if scoped_node_id != active_node_id:
        return True
    raw_scope_version = scope.get('route_version')
    raw_frontier_version = frontier.get('route_version')
    if raw_scope_version in (None, '') or raw_frontier_version in (None, ''):
        return False
    try:
        return int(raw_scope_version) != int(raw_frontier_version)
    except (TypeError, ValueError):
        return str(raw_scope_version) != str(raw_frontier_version)

__all__ = (
    '_pending_return_records',
    '_card_return_resolved_for_action',
    '_pending_card_return_ack_exists',
    '_pending_return_card_ids',
    '_pending_return_is_startup_async_scope',
    '_pending_return_is_pre_review_startup_scope',
    '_startup_pre_review_card_flags',
    '_startup_pre_review_cards_delivered',
    '_startup_pre_review_pending_returns',
    '_startup_pre_review_ack_join_clean',
    '_pending_return_matches_active_node_scope',
    '_pending_return_is_outside_active_node_scope',
)
