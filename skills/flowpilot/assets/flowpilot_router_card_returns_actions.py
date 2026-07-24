"""Card return helper shard for FlowPilot router."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import card_runtime

def _action_is_startup_async_delivery(router: ModuleType, action: dict[str, Any] | None) -> bool:
    if not isinstance(action, dict):
        return False
    if action.get('action_type') == 'check_prompt_manifest':
        return str(action.get('next_card_id') or '') in router.STARTUP_ASYNC_CARD_IDS
    if action.get('action_type') == 'inject_role_io_protocol':
        return str(action.get('required_before_card_id') or '') in router.STARTUP_ASYNC_CARD_IDS
    if action.get('action_type') == 'deliver_system_card_bundle':
        raw_card_ids = action.get('card_ids')
        card_ids = {str(card_id) for card_id in raw_card_ids} if isinstance(raw_card_ids, list) else set()
        raw_cards = action.get('cards')
        if isinstance(raw_cards, list):
            card_ids.update((str(card.get('card_id') or '') for card in raw_cards if isinstance(card, dict)))
        return bool(card_ids) and card_ids.issubset(router.STARTUP_ASYNC_CARD_IDS)
    if action.get('action_type') == 'deliver_system_card':
        return str(action.get('card_id') or '') in router.STARTUP_ASYNC_CARD_IDS
    return False

def _action_is_startup_async_card_wait(router: ModuleType, action: dict[str, Any] | None) -> bool:
    if not isinstance(action, dict):
        return False
    if action.get('action_type') not in {'await_card_return_event', 'await_card_bundle_return_event'}:
        return False
    return router._pending_return_is_startup_async_scope(action)

def _startup_async_pending_returns(router: ModuleType, run_root: Path, pending_returns: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    deferred: list[dict[str, Any]] = []
    blocking: list[dict[str, Any]] = []
    for record in pending_returns:
        if router._pending_return_is_startup_async_scope(record):
            deferred.append(record)
        elif router._pending_return_is_outside_active_node_scope(run_root, record):
            continue
        else:
            blocking.append(record)
    return (deferred, blocking)

def _pending_card_return_blocker_for_event(router: ModuleType, run_root: Path, run_id: str, event: str, run_state: dict[str, Any]) -> dict[str, Any] | None:
    if event in router.CARD_RETURN_EVENT_BYPASS_EVENTS:
        return None
    pending_returns = router._pending_return_records(run_root, run_id)
    if not pending_returns:
        return None
    if event in router.STARTUP_REVIEW_BEGIN_JOIN_EVENTS:
        for record in pending_returns:
            if router._pending_return_is_pre_review_startup_scope(record):
                return record
    for record in pending_returns:
        if router._pending_card_return_matches_event_dependency(record, event, run_state):
            return record
    for record in pending_returns:
        if not router._pending_return_is_startup_async_scope(record) and (not router._pending_return_is_outside_active_node_scope(run_root, record)):
            return record
    return None

def _committed_card_artifact_extra(router: ModuleType, project_root: Path, record: dict[str, Any], *, relay_allowed_if_ready: bool) -> dict[str, Any]:
    envelope_path = str(record.get('card_envelope_path') or '')
    expected_return_path = str(record.get('expected_return_path') or '')
    expected_receipt_path = str(record.get('expected_receipt_path') or '')
    artifact_exists = False
    artifact_hash_verified = False
    if envelope_path:
        resolved = router.resolve_project_path(project_root, envelope_path)
        artifact_exists = resolved.exists() and resolved.is_file()
        if artifact_exists:
            try:
                envelope = router.read_json(resolved)
            except Exception:
                envelope = {}
            recorded_hash = str(record.get('card_envelope_hash') or '')
            artifact_hash_verified = bool(recorded_hash) and envelope.get('envelope_hash') == recorded_hash
    artifact_committed = bool(artifact_exists and artifact_hash_verified and expected_return_path and expected_receipt_path)
    return {'resource_lifecycle': 'committed_artifact' if artifact_committed else 'missing_committed_artifact', 'artifact_committed': artifact_committed, 'artifact_exists': artifact_exists, 'artifact_hash_verified': artifact_hash_verified, 'ledger_recorded': True, 'return_wait_recorded': bool(expected_return_path), 'relay_allowed': bool(relay_allowed_if_ready and artifact_committed), 'apply_required': False}

def _pending_return_wait_reminder_extra(router: ModuleType, record: dict[str, Any]) -> dict[str, Any]:
    del router
    extra: dict[str, Any] = {}
    for key in ('last_wait_reminder_at', 'last_wait_reminder_sha256', 'wait_reminder_text', 'wait_reminder_text_sha256'):
        if record.get(key) not in (None, '', []):
            extra[key] = record.get(key)
    return extra

def _next_pending_card_return_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path, pending_records: list[dict[str, Any]] | None=None, *, clearance_reason: str='router_progress') -> dict[str, Any] | None:
    pending_returns = list(pending_records) if pending_records is not None else router._pending_return_records(run_root, str(run_state['run_id']))
    if not pending_returns:
        return None
    record = pending_returns[0]
    clearance_scope_extra = {'scope_kind': 'startup', 'scope_id': 'startup'} if clearance_reason == 'current_scope_pre_review_reconciliation' and router._pending_return_is_pre_review_startup_scope(record) else {}
    if record.get('return_kind') == 'system_card_bundle':
        expected_return_path = str(record.get('expected_return_path') or '')
        envelope_path = str(record.get('card_bundle_envelope_path') or '')
        committed_extra = router._committed_card_bundle_artifact_extra(project_root, record, relay_allowed_if_ready=False)
        current_ack_hash: str | None = None
        if expected_return_path and router.resolve_project_path(project_root, expected_return_path).exists():
            try:
                current_ack = router.read_json(router.resolve_project_path(project_root, expected_return_path))
                current_ack_hash = str(current_ack.get('ack_hash') or card_runtime.stable_json_hash(current_ack))
            except Exception:
                current_ack_hash = None
        ack_is_unchanged_incomplete = bool(record.get('status') == 'bundle_ack_incomplete' and current_ack_hash and (current_ack_hash == record.get('incomplete_ack_hash')))
        if expected_return_path and router.resolve_project_path(project_root, expected_return_path).exists() and (not ack_is_unchanged_incomplete):
            return router.make_action(action_type='check_card_bundle_return_event', actor='controller', label=f"controller_checks_card_bundle_return_{router._safe_delivery_component(str(record.get('card_bundle_id') or 'pending'))}", summary=f"Validate returned {record.get('card_return_event')} from {record.get('target_role')} against all bundled runtime card read receipts before Router may continue.", allowed_reads=[expected_return_path, envelope_path, *[str(path) for path in record.get('expected_receipt_paths') or []], router.project_relative(project_root, router._card_ledger_path(run_root)), router.project_relative(project_root, router._return_event_ledger_path(run_root))], allowed_writes=[router.project_relative(project_root, router._card_ledger_path(run_root)), router.project_relative(project_root, router._return_event_ledger_path(run_root)), router.project_relative(project_root, router.run_state_path(run_root))], card_id=(record.get('card_ids') or [''])[0] if isinstance(record.get('card_ids'), list) else None, to_role=str(record.get('target_role') or ''), extra={'card_return_event': record.get('card_return_event'), 'card_bundle_id': record.get('card_bundle_id'), 'card_ids': record.get('card_ids') or [], 'delivery_attempt_ids': record.get('delivery_attempt_ids') or [], 'expected_return_path': expected_return_path, 'card_bundle_envelope_path': envelope_path, 'expected_receipt_paths': record.get('expected_receipt_paths') or [], 'ack_clearance_reason': clearance_reason, **clearance_scope_extra, 'ack_clearance_scope': record.get('ack_clearance_scope'), 'ack_is_read_receipt_only': True, 'target_work_completion_evidence_required_separately': True, 'controller_visibility': 'ack_envelope_and_receipts_only', 'sealed_body_reads_allowed': False, **committed_extra, 'apply_required': True})
        committed_extra = router._committed_card_bundle_artifact_extra(project_root, record, relay_allowed_if_ready=True)
        delivery_fact = router._controller_delivery_fact_for_pending_return(project_root, run_root, record, bundle=True, committed_extra=committed_extra)
        status_hint = ' after an incomplete bundle ACK' if ack_is_unchanged_incomplete else ''
        if delivery_fact.get('target_role_ack_reminder_allowed'):
            summary = f"Confirm the original committed system-card bundle reached {record.get('target_role')} if needed, then remind the role to complete {record.get('card_return_event')}{status_hint} by opening every bundled card through runtime and ACKing the original bundle. Do not issue a duplicate bundle unless the original committed artifact is invalid, lost, stale, or tied to a replaced role."
        else:
            summary = f"The {record.get('card_return_event')} ACK is missing{status_hint}, but Controller delivery is not confirmed. Confirm or reissue delivery of the original committed system-card bundle before reminding the target role."
        return router.make_action(action_type='await_card_bundle_return_event', actor='controller', label=f"controller_waits_for_card_bundle_return_{router._safe_delivery_component(str(record.get('card_bundle_id') or 'pending'))}", summary=summary, allowed_reads=[envelope_path, router.project_relative(project_root, router._return_event_ledger_path(run_root)), router.project_relative(project_root, router._card_ledger_path(run_root)), *[str(path) for path in delivery_fact.get('controller_read_paths') or []]], allowed_writes=[router.project_relative(project_root, router._return_event_ledger_path(run_root)), router.project_relative(project_root, router.run_state_path(run_root))], card_id=(record.get('card_ids') or [''])[0] if isinstance(record.get('card_ids'), list) else None, to_role=str(record.get('target_role') or ''), extra={'card_return_event': record.get('card_return_event'), 'card_bundle_id': record.get('card_bundle_id'), 'card_ids': record.get('card_ids') or [], 'delivery_attempt_ids': record.get('delivery_attempt_ids') or [], 'expected_return_path': expected_return_path, 'card_bundle_envelope_path': envelope_path, 'expected_receipt_paths': record.get('expected_receipt_paths') or [], 'bundle_ack_incomplete': ack_is_unchanged_incomplete, 'missing_card_ids': record.get('missing_card_ids') or [], 'incomplete_ack_path': record.get('incomplete_ack_path'), 'incomplete_ack_hash': record.get('incomplete_ack_hash'), 'ack_clearance_reason': clearance_reason, **clearance_scope_extra, 'waiting_for_role': record.get('target_role'), 'waiting_for_agent_id': record.get('target_agent_id'), 'controller_visibility': 'pending_return_metadata_only', 'sealed_body_reads_allowed': False, **_pending_return_wait_reminder_extra(router, record), **router._original_card_ack_reminder_policy(record, bundle=True, delivery_fact=delivery_fact), **committed_extra, 'next_recovery_actions': ['controller_confirms_or_reissues_original_committed_bundle_delivery_first', 'role_uses_open-card-bundle_then_ack-card-bundle_after_delivery_confirmed', 'controller_reminds_role_to_ack_original_committed_bundle_if_delivery_confirmed', 'router_reissues_bundle_only_if_original_invalid_lost_stale_or_role_replaced', 'router_records_protocol_blocker_if_bundle_ack_is_invalid']})
    expected_return_path = str(record.get('expected_return_path') or '')
    envelope_path = str(record.get('card_envelope_path') or '')
    committed_extra = router._committed_card_artifact_extra(project_root, record, relay_allowed_if_ready=False)
    if expected_return_path and router.resolve_project_path(project_root, expected_return_path).exists():
        return router.make_action(action_type='check_card_return_event', actor='controller', label=f"controller_checks_card_return_{router._safe_delivery_component(str(record.get('delivery_attempt_id') or 'pending'))}", summary=f"Validate returned {record.get('card_return_event')} from {record.get('target_role')} against runtime card read receipts before Router may continue.", allowed_reads=[expected_return_path, envelope_path, str(record.get('expected_receipt_path') or ''), router.project_relative(project_root, router._card_ledger_path(run_root)), router.project_relative(project_root, router._return_event_ledger_path(run_root))], allowed_writes=[router.project_relative(project_root, router._card_ledger_path(run_root)), router.project_relative(project_root, router._return_event_ledger_path(run_root)), router.project_relative(project_root, router.run_state_path(run_root))], to_role=str(record.get('target_role') or ''), extra={'card_return_event': record.get('card_return_event'), 'delivery_id': record.get('delivery_id'), 'delivery_attempt_id': record.get('delivery_attempt_id'), 'card_id': record.get('card_id'), 'expected_return_path': expected_return_path, 'card_envelope_path': envelope_path, 'expected_receipt_path': record.get('expected_receipt_path'), 'ack_clearance_reason': clearance_reason, **clearance_scope_extra, 'ack_clearance_scope': record.get('ack_clearance_scope'), 'ack_is_read_receipt_only': True, 'target_work_completion_evidence_required_separately': True, 'controller_visibility': 'ack_envelope_and_receipts_only', 'sealed_body_reads_allowed': False, **committed_extra, 'apply_required': True})
    committed_extra = router._committed_card_artifact_extra(project_root, record, relay_allowed_if_ready=True)
    delivery_fact = router._controller_delivery_fact_for_pending_return(project_root, run_root, record, bundle=False, committed_extra=committed_extra)
    if delivery_fact.get('target_role_ack_reminder_allowed'):
        summary = f"Confirm the original committed system-card envelope reached {record.get('target_role')} if needed, then remind the role to complete {record.get('card_return_event')} by opening the original card through runtime and ACKing it. Do not issue a duplicate card unless the original committed artifact is invalid, lost, stale, or tied to a replaced role."
    else:
        summary = f"The {record.get('card_return_event')} ACK is missing, but Controller delivery is not confirmed. Confirm or reissue delivery of the original committed system-card envelope before reminding the target role."
    return router.make_action(action_type='await_card_return_event', actor='controller', label=f"controller_waits_for_card_return_{router._safe_delivery_component(str(record.get('delivery_attempt_id') or 'pending'))}", summary=summary, allowed_reads=[envelope_path, router.project_relative(project_root, router._return_event_ledger_path(run_root)), router.project_relative(project_root, router._card_ledger_path(run_root)), *[str(path) for path in delivery_fact.get('controller_read_paths') or []]], allowed_writes=[router.project_relative(project_root, router._return_event_ledger_path(run_root)), router.project_relative(project_root, router.run_state_path(run_root))], to_role=str(record.get('target_role') or ''), extra={'card_return_event': record.get('card_return_event'), 'delivery_id': record.get('delivery_id'), 'delivery_attempt_id': record.get('delivery_attempt_id'), 'card_id': record.get('card_id'), 'expected_return_path': expected_return_path, 'card_envelope_path': envelope_path, 'expected_receipt_path': record.get('expected_receipt_path'), 'ack_clearance_reason': clearance_reason, **clearance_scope_extra, 'ack_clearance_scope': record.get('ack_clearance_scope'), 'waiting_for_role': record.get('target_role'), 'waiting_for_agent_id': record.get('target_agent_id'), 'controller_visibility': 'pending_return_metadata_only', 'sealed_body_reads_allowed': False, **_pending_return_wait_reminder_extra(router, record), **router._original_card_ack_reminder_policy(record, bundle=False, delivery_fact=delivery_fact), **committed_extra, 'next_recovery_actions': ['controller_confirms_or_reissues_original_committed_card_delivery_first', 'role_uses_open-card_then_ack-card_after_delivery_confirmed', 'controller_reminds_role_to_ack_original_committed_card_if_delivery_confirmed', 'router_reissues_card_only_if_original_invalid_lost_stale_or_role_replaced', 'router_records_protocol_blocker_if_ack_is_invalid']})

def _pending_return_record_for_action(router: ModuleType, run_root: Path, run_id: str, action: dict[str, Any]) -> dict[str, Any] | None:
    delivery_attempt_id = action.get('delivery_attempt_id')
    for record in router._pending_return_records(run_root, run_id):
        if isinstance(record, dict) and record.get('delivery_attempt_id') == delivery_attempt_id and (record.get('card_id') == action.get('card_id')):
            return record
    return None

def _pending_bundle_return_record_for_action(router: ModuleType, run_root: Path, run_id: str, action: dict[str, Any]) -> dict[str, Any] | None:
    bundle_id = action.get('card_bundle_id')
    for record in router._pending_return_records(run_root, run_id):
        if isinstance(record, dict) and record.get('return_kind') == 'system_card_bundle' and (record.get('card_bundle_id') == bundle_id):
            return record
    return None

def _apply_card_return_event_check(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], pending: dict[str, Any]) -> dict[str, Any]:
    ack_path = str(pending.get('expected_return_path') or '')
    envelope_path = str(pending.get('card_envelope_path') or '')
    if not ack_path or not envelope_path:
        raise router.RouterError('card return check requires expected_return_path and card_envelope_path')
    validation = card_runtime.validate_card_ack(project_root, ack_path=ack_path, envelope_path=envelope_path)
    return_ledger = router._read_return_event_ledger(run_root, str(run_state['run_id']))
    for item in return_ledger.setdefault('pending_returns', []):
        if isinstance(item, dict) and item.get('delivery_attempt_id') == pending.get('delivery_attempt_id') and (item.get('card_return_event') == pending.get('card_return_event')):
            item['status'] = 'resolved'
            item['resolved_at'] = router.utc_now()
            item['ack_path'] = validation['ack_path']
            item['ack_hash'] = validation['ack_hash']
            item['receipt_ref_count'] = validation['receipt_ref_count']
    completed = return_ledger.setdefault('completed_returns', [])
    if not any((isinstance(item, dict) and item.get('delivery_attempt_id') == pending.get('delivery_attempt_id') and (item.get('card_return_event') == pending.get('card_return_event')) for item in completed)):
        completed.append({'card_return_event': pending.get('card_return_event'), 'delivery_id': pending.get('delivery_id'), 'delivery_attempt_id': pending.get('delivery_attempt_id'), 'card_id': pending.get('card_id'), 'target_role': pending.get('to_role'), 'ack_path': validation['ack_path'], 'ack_hash': validation['ack_hash'], 'receipt_ref_count': validation['receipt_ref_count'], 'checked_at': router.utc_now(), 'status': 'resolved'})
    return_ledger['updated_at'] = router.utc_now()
    router.write_json(router._return_event_ledger_path(run_root), return_ledger)
    run_state['card_return_checks'] = int(run_state.get('card_return_checks', 0)) + 1
    run_state.setdefault('card_return_events', []).append(validation)
    return {'ok': True, 'status': 'resolved', 'validation': validation}

def _apply_card_bundle_return_event_check(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], pending: dict[str, Any]) -> dict[str, Any]:
    ack_path = str(pending.get('expected_return_path') or '')
    envelope_path = str(pending.get('card_bundle_envelope_path') or '')
    if not ack_path or not envelope_path:
        raise router.RouterError('card bundle return check requires expected_return_path and card_bundle_envelope_path')
    try:
        validation = card_runtime.validate_card_bundle_ack(project_root, ack_path=ack_path, envelope_path=envelope_path)
    except card_runtime.CardRuntimeError:
        inspection = card_runtime.inspect_card_bundle_ack_incomplete(project_root, ack_path=ack_path, envelope_path=envelope_path)
        if not inspection.get('incomplete'):
            raise
        return_ledger = router._read_return_event_ledger(run_root, str(run_state['run_id']))
        incomplete_record = {'return_kind': 'system_card_bundle', 'card_return_event': pending.get('card_return_event'), 'card_bundle_id': pending.get('card_bundle_id'), 'card_ids': pending.get('card_ids') or [], 'target_role': pending.get('to_role'), 'ack_path': inspection['ack_path'], 'ack_hash': inspection['ack_hash'], 'missing_card_ids': inspection['missing_card_ids'], 'checked_at': router.utc_now(), 'status': 'bundle_ack_incomplete', 'recovery': 'same_role_must_resubmit_bundle_ack_with_all_member_receipts'}
        for item in return_ledger.setdefault('pending_returns', []):
            if isinstance(item, dict) and item.get('return_kind') == 'system_card_bundle' and (item.get('card_bundle_id') == pending.get('card_bundle_id')) and (item.get('card_return_event') == pending.get('card_return_event')):
                item['status'] = 'bundle_ack_incomplete'
                item['missing_card_ids'] = list(inspection['missing_card_ids'])
                item['incomplete_ack_path'] = inspection['ack_path']
                item['incomplete_ack_hash'] = inspection['ack_hash']
                item['incomplete_checked_at'] = incomplete_record['checked_at']
                item['recovery'] = incomplete_record['recovery']
        return_ledger.setdefault('incomplete_returns', []).append(incomplete_record)
        return_ledger['updated_at'] = router.utc_now()
        router.write_json(router._return_event_ledger_path(run_root), return_ledger)
        run_state['card_return_checks'] = int(run_state.get('card_return_checks', 0)) + 1
        run_state.setdefault('card_return_events', []).append(incomplete_record)
        return {'ok': False, 'waiting': True, 'status': 'bundle_ack_incomplete', 'record': incomplete_record, 'missing_card_ids': inspection['missing_card_ids'], 'expected_return_path': ack_path, 'waiting_for_role': pending.get('to_role')}
    return_ledger = router._read_return_event_ledger(run_root, str(run_state['run_id']))
    for item in return_ledger.setdefault('pending_returns', []):
        if isinstance(item, dict) and item.get('return_kind') == 'system_card_bundle' and (item.get('card_bundle_id') == pending.get('card_bundle_id')) and (item.get('card_return_event') == pending.get('card_return_event')):
            item['status'] = 'resolved'
            item['resolved_at'] = router.utc_now()
            item['ack_path'] = validation['ack_path']
            item['ack_hash'] = validation['ack_hash']
            item['receipt_ref_count'] = validation['receipt_ref_count']
    completed = return_ledger.setdefault('completed_returns', [])
    if not any((isinstance(item, dict) and item.get('return_kind') == 'system_card_bundle' and (item.get('card_bundle_id') == pending.get('card_bundle_id')) and (item.get('card_return_event') == pending.get('card_return_event')) for item in completed)):
        completed.append({'return_kind': 'system_card_bundle', 'card_return_event': pending.get('card_return_event'), 'card_bundle_id': pending.get('card_bundle_id'), 'card_ids': validation['member_card_ids'], 'target_role': pending.get('to_role'), 'ack_path': validation['ack_path'], 'ack_hash': validation['ack_hash'], 'receipt_ref_count': validation['receipt_ref_count'], 'checked_at': router.utc_now(), 'status': 'resolved'})
    return_ledger['updated_at'] = router.utc_now()
    router.write_json(router._return_event_ledger_path(run_root), return_ledger)
    run_state['card_return_checks'] = int(run_state.get('card_return_checks', 0)) + 1
    run_state.setdefault('card_return_events', []).append(validation)
    return {'ok': True, 'status': 'resolved', 'validation': validation}

def _try_auto_consume_pending_card_return_ack(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], pending: dict[str, Any]) -> dict[str, Any]:
    if pending.get('artifact_committed') is False:
        return {'consumed': False, 'preserve_pending': True, 'reason': 'artifact_not_committed'}
    try:
        if pending.get('action_type') in {'await_card_bundle_return_event', 'check_card_bundle_return_event', 'deliver_system_card_bundle'}:
            result = router._apply_card_bundle_return_event_check(project_root, run_root, run_state, pending)
        else:
            result = router._apply_card_return_event_check(project_root, run_root, run_state, pending)
    except (router.RouterError, card_runtime.CardRuntimeError) as exc:
        return {'consumed': False, 'preserve_pending': False, 'reason': 'ack_requires_explicit_check', 'error': str(exc)}
    return {'consumed': True, 'result': result}

__all__ = (
    '_action_is_startup_async_delivery',
    '_action_is_startup_async_card_wait',
    '_startup_async_pending_returns',
    '_pending_card_return_blocker_for_event',
    '_committed_card_artifact_extra',
    '_next_pending_card_return_action',
    '_pending_return_record_for_action',
    '_pending_bundle_return_record_for_action',
    '_apply_card_return_event_check',
    '_apply_card_bundle_return_event_check',
    '_try_auto_consume_pending_card_return_ack',
)
