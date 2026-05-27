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


def _scoped_event_conflict_record(
    router: ModuleType,
    run_state: dict[str, Any],
    identity: dict[str, Any] | None,
) -> dict[str, Any]:
    if not identity:
        return {'classification': 'no_identity'}
    conflict_fields = tuple(str(field) for field in identity.get('conflict_fields') or () if field)
    if not conflict_fields:
        return {'classification': 'no_conflict_fields'}
    ledger = router._event_identity_ledger(run_state)
    processed = ledger.get('processed')
    if not isinstance(processed, dict):
        return {'classification': 'no_processed_ledger'}
    event = str(identity.get('event') or '')
    key = str(identity.get('dedupe_key') or '')
    event_keys = processed.get(event)
    if not isinstance(event_keys, dict):
        return {'classification': 'no_existing_event'}
    if key not in event_keys:
        return {'classification': 'no_existing_key'}
    existing = event_keys.get(key)
    if not isinstance(existing, dict):
        return {
            'classification': 'unknown_corruption',
            'event': event,
            'dedupe_key': key,
            'reason': 'processed idempotency entry is not an object',
        }
    old_scope = existing.get('scope') if isinstance(existing.get('scope'), dict) else {}
    new_scope = identity.get('scope') if isinstance(identity.get('scope'), dict) else {}
    mismatches = tuple(
        field for field in conflict_fields
        if str(old_scope.get(field) or '') != str(new_scope.get(field) or '')
    )
    if not mismatches:
        return {
            'classification': 'no_conflict',
            'event': event,
            'dedupe_key': key,
            'family': identity.get('family'),
        }
    return {
        'classification': 'new_conflict',
        'event': event,
        'dedupe_key': key,
        'family': identity.get('family'),
        'mismatches': list(mismatches),
        'old_scope': old_scope,
        'new_scope': new_scope,
    }


def _active_control_blocker_owns_scoped_package_conflict(
    router: ModuleType,
    run_state: dict[str, Any],
    identity: dict[str, Any],
) -> dict[str, Any] | None:
    active = run_state.get('active_control_blocker')
    if not isinstance(active, dict):
        return None
    event = str(identity.get('event') or '')
    active_event = str(active.get('originating_event') or '')
    if active_event and active_event != event:
        return None
    if str(active.get('resolution_status') or ''):
        return None
    if str(active.get('delivery_status') or '') in {'resolved', 'superseded', 'terminal_lifecycle_quarantined'}:
        return None
    if (
        active.get('pm_decision_required') is not True
        and active.get('handling_lane') not in router.PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES
        and active.get('target_role') != 'project_manager'
        and active.get('repair_transaction_id') is None
    ):
        return None
    return {
        'blocker_id': active.get('blocker_id'),
        'handling_lane': active.get('handling_lane'),
        'delivery_status': active.get('delivery_status'),
        'target_role': active.get('target_role'),
        'repair_transaction_id': active.get('repair_transaction_id'),
        'originating_event': active.get('originating_event'),
    }


def _active_repair_transaction_owns_scoped_package_conflict(
    router: ModuleType,
    run_state: dict[str, Any],
    identity: dict[str, Any],
) -> dict[str, Any] | None:
    active = run_state.get('active_repair_transaction')
    if not isinstance(active, dict):
        return None
    if active.get('status') not in {'opened', 'committed', 'awaiting_recheck'}:
        return None
    event = str(identity.get('event') or '')
    active_event = str(active.get('originating_event') or '')
    if active_event and active_event != event:
        return None
    active_blocker = run_state.get('active_control_blocker')
    if isinstance(active_blocker, dict):
        blocker_id = str(active.get('blocker_id') or '')
        if blocker_id and blocker_id != str(active_blocker.get('blocker_id') or ''):
            return None
    return {
        'transaction_id': active.get('transaction_id'),
        'blocker_id': active.get('blocker_id'),
        'status': active.get('status'),
        'path': active.get('path'),
        'originating_event': active.get('originating_event'),
    }


def _terminal_lifecycle_owns_scoped_package_conflict(
    router: ModuleType,
    run_state: dict[str, Any],
    identity: dict[str, Any],
) -> dict[str, Any] | None:
    del router, identity
    status = str(run_state.get('status') or '')
    flags = run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {}
    if status in {'stopped_by_user', 'protocol_dead_end', 'completed', 'terminal'} or flags.get('run_stopped_by_user'):
        return {'status': status or 'terminal_lifecycle', 'run_stopped_by_user': bool(flags.get('run_stopped_by_user'))}
    return None


def _classify_scoped_event_conflict(
    router: ModuleType,
    run_state: dict[str, Any],
    identity: dict[str, Any] | None,
) -> dict[str, Any]:
    record = _scoped_event_conflict_record(router, run_state, identity)
    if record.get('classification') != 'new_conflict' or not isinstance(identity, dict):
        return record
    if identity.get('family') != 'pm_package_disposition':
        return record
    terminal_owner = _terminal_lifecycle_owns_scoped_package_conflict(router, run_state, identity)
    if terminal_owner is not None:
        return {**record, 'classification': 'terminal_quarantine', 'owner': terminal_owner}
    repair_owner = _active_repair_transaction_owns_scoped_package_conflict(router, run_state, identity)
    if repair_owner is not None:
        return {**record, 'classification': 'pm_repair_owned_stale_conflict', 'owner': repair_owner}
    blocker_owner = _active_control_blocker_owns_scoped_package_conflict(router, run_state, identity)
    if blocker_owner is not None:
        return {**record, 'classification': 'control_blocker_owned_stale_conflict', 'owner': blocker_owner}
    return record


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


def _check_scoped_event_conflict(router: ModuleType, run_state: dict[str, Any], identity: dict[str, Any] | None) -> None:
    classification = _classify_scoped_event_conflict(router, run_state, identity)
    if classification.get('classification') in {
        'no_identity',
        'no_conflict_fields',
        'no_processed_ledger',
        'no_existing_event',
        'no_existing_key',
        'no_conflict',
    }:
        return
    if classification.get('classification') == 'unknown_corruption':
        raise router.RouterError(
            f"event {classification.get('event')} has corrupt scoped idempotency evidence for "
            f"dedupe key {classification.get('dedupe_key')}"
        )
    if classification.get('classification') in {
        'new_conflict',
        'terminal_quarantine',
        'pm_repair_owned_stale_conflict',
        'control_blocker_owned_stale_conflict',
    }:
        fields = ', '.join(str(field) for field in classification.get('mismatches') or ())
        raise router.RouterError(
            f"event {classification.get('event')} conflicts with an already recorded package disposition for this batch/generation; "
            f"different {fields} requires an authorized repair/reissue path"
        )


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
    if scoped_identity and scoped_identity.get('family') == 'pm_package_disposition':
        return True
    return bool(scoped_identity and event == 'pm_mutates_route_after_review_block' and router._active_model_miss_review_block_flags(run_state))


__all__ = (
    '_scoped_event_is_recorded',
    '_classify_scoped_event_conflict',
    '_check_scoped_event_conflict',
    '_check_scoped_event_retry_budget',
    '_mark_scoped_event_recorded',
    '_already_recorded_external_event_result',
    '_external_event_flag_replay_requires_new_processing',
)
