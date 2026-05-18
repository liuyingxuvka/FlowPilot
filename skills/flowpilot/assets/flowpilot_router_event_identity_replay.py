"""Scoped event replay and retry-budget helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import ModuleType
from typing import Any


def _scoped_event_is_recorded(router: ModuleType, run_state: dict[str, Any], identity: dict[str, Any] | None) -> bool:
    if not identity:
        return False
    ledger = router._event_identity_ledger(run_state)
    processed = ledger.get('processed')
    if not isinstance(processed, dict):
        return False
    event_keys = processed.get(str(identity.get('event')))
    return isinstance(event_keys, dict) and str(identity.get('dedupe_key')) in event_keys


def _check_scoped_event_retry_budget(router: ModuleType, run_state: dict[str, Any], identity: dict[str, Any] | None) -> None:
    if not identity:
        return
    raw_budget = identity.get('max_distinct_keys_per_retry_group')
    if raw_budget in (None, ''):
        return
    budget = int(raw_budget)
    ledger = router._event_identity_ledger(run_state)
    attempts = ledger.get('attempts') if isinstance(ledger.get('attempts'), list) else []
    group = str(identity.get('retry_group') or '')
    key = str(identity.get('dedupe_key') or '')
    distinct_keys = {str(item.get('dedupe_key')) for item in attempts if isinstance(item, dict) and item.get('retry_group') == group and item.get('dedupe_key')}
    if key not in distinct_keys and len(distinct_keys) >= budget:
        raise router.RouterError(f"event {identity.get('event')} exceeded scoped retry budget for this repair group; PM must record an escalation or protocol dead-end instead of another silent retry")


def _mark_scoped_event_recorded(router: ModuleType, run_state: dict[str, Any], identity: dict[str, Any] | None) -> None:
    if not identity:
        return
    ledger = router._event_identity_ledger(run_state)
    processed = ledger['processed']
    event = str(identity['event'])
    key = str(identity['dedupe_key'])
    event_keys = processed.setdefault(event, {})
    record = {'dedupe_key': key, 'event': event, 'family': identity.get('family'), 'scope': identity.get('scope'), 'retry_group': identity.get('retry_group'), 'recorded_at': router.utc_now()}
    event_keys[key] = record
    attempts = ledger.setdefault('attempts', [])
    if isinstance(attempts, list) and (not any((isinstance(item, dict) and item.get('event') == event and (item.get('dedupe_key') == key) for item in attempts))):
        attempts.append(record)


def _already_recorded_external_event_result(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, event: str, payload: dict[str, Any], scoped_identity: dict[str, Any] | None=None) -> dict[str, Any]:
    finalized = router._finalize_repair_transaction_outcome(project_root, run_root, run_state, event=event, payload=payload)
    resolved = router._resolve_delivered_control_blocker(project_root, run_root, run_state, resolved_by_event=event, from_already_recorded_event=True)
    wait_closure = router._close_waiting_controller_actions_for_external_event(project_root, run_root, run_state, event=event, payload=payload, source='already_recorded_external_event')
    if resolved or finalized:
        run_state['pending_action'] = None
    if resolved or finalized or wait_closure.get('changed'):
        router._refresh_route_memory(project_root, run_root, run_state, trigger=f'after_already_recorded_event:{event}')
        router._sync_derived_run_views(project_root, run_root, run_state, reason=f'after_already_recorded_event:{event}')
        router.save_run_state(run_root, run_state)
        result = {'ok': True, 'event': event, 'already_recorded': True, 'control_blocker_resolved': bool(resolved), 'blocker_id': resolved.get('blocker_id') if resolved else None, 'repair_transaction_finalized': finalized}
        if wait_closure.get('changed'):
            result['wait_closure'] = wait_closure
        if scoped_identity:
            result['dedupe_key'] = scoped_identity.get('dedupe_key')
            result['idempotency_scope'] = scoped_identity.get('scope')
        return result
    result = {'ok': True, 'event': event, 'already_recorded': True}
    if scoped_identity:
        result['dedupe_key'] = scoped_identity.get('dedupe_key')
        result['idempotency_scope'] = scoped_identity.get('scope')
    return result


def _external_event_flag_replay_requires_new_processing(router: ModuleType, run_root: Path, run_state: dict[str, Any], *, event: str, flag: str, payload: dict[str, Any], scoped_identity: dict[str, Any] | None) -> bool:
    active_blocker = run_state.get('active_control_blocker')
    if event == router.PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT and isinstance(active_blocker, dict) and (active_blocker.get('delivery_status') == 'delivered') and (active_blocker.get('handling_lane') in router.PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES):
        return True
    if event == router.GATE_DECISION_EVENT:
        return True
    if event in router.GATE_OUTCOME_BLOCK_EVENTS:
        return True
    if event in router.CONTROL_BLOCKER_REPAIR_NON_SUCCESS_EVENTS or event == router.PM_PARENT_PROTOCOL_BLOCKER_EVENT:
        return True
    if event == 'pm_requests_startup_repair' and run_state['flags'].get(flag) and run_state['flags'].get('startup_fact_reported') and run_state['flags'].get('pm_startup_activation_card_delivered'):
        return True
    if event == 'pm_writes_route_draft' and run_state['flags'].get(flag) and (not run_state['flags'].get('route_activated_by_pm')):
        return True
    if event in {'pm_completes_current_node_from_reviewed_result', 'pm_completes_parent_node_from_backward_replay'} and run_state['flags'].get(flag) and router._active_node_completion_write_missing(run_root, run_state, payload):
        return True
    if event in {router.PM_ROLE_WORK_REQUEST_EVENT, router.ROLE_WORK_RESULT_RETURNED_EVENT, router.PM_ROLE_WORK_RESULT_DECISION_EVENT, 'worker_current_node_result_returned'}:
        return True
    return bool(scoped_identity and event == 'pm_mutates_route_after_review_block' and router._active_model_miss_review_block_flags(run_state))


__all__ = (
    '_scoped_event_is_recorded',
    '_check_scoped_event_retry_budget',
    '_mark_scoped_event_recorded',
    '_already_recorded_external_event_result',
    '_external_event_flag_replay_requires_new_processing',
)
