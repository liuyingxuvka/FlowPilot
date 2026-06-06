"""Card return helper shard for FlowPilot router."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import card_runtime

def _startup_pm_card_bundle_ack_record(router: ModuleType, record: dict[str, Any]) -> bool:
    return router.is_startup_pm_card_bundle_ack_record(record, pre_review_startup_card_ids=router.PRE_REVIEW_STARTUP_CARD_IDS)

def _reconcile_card_wait_rows(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, delivery_attempt_id: str, expected_return_path: str, card_return_event: str, card_id: str, source: str, ack_path: str | None) -> int:
    action_dir = router._controller_actions_dir(run_root)
    if not action_dir.exists():
        return 0
    reconciled = 0
    for action_path in sorted(action_dir.glob('*.json')):
        entry = router._read_json_for_runtime_scan(action_path)
        if entry is None:
            continue
        if entry.get('schema_version') != router.CONTROLLER_ACTION_SCHEMA:
            continue
        if entry.get('action_type') not in {'await_card_return_event', 'check_card_return_event'}:
            continue
        if not router._record_matches_card_identity(entry, delivery_attempt_id=delivery_attempt_id, expected_return_path=expected_return_path, card_return_event=card_return_event, card_id=card_id):
            continue
        reconciliation = {'source': source, 'delivery_attempt_id': delivery_attempt_id, 'card_id': card_id, 'card_return_event': card_return_event, 'expected_return_path': expected_return_path, 'ack_path': ack_path, 'reconciled_at': router.utc_now(), 'clearance_kind': 'ack_wait_only', 'ack_does_not_complete_output_bearing_work': True}
        if entry.get('status') not in router.CONTROLLER_ACTION_CLOSED_STATUSES:
            entry['status'] = 'resolved'
            entry['completed_at'] = reconciliation['reconciled_at']
        entry['router_reconciliation_status'] = 'reconciled'
        entry['router_reconciliation'] = reconciliation
        entry['updated_at'] = router.utc_now()
        router.write_json(action_path, entry)
        row_id = str(entry.get('router_scheduler_row_id') or '')
        if row_id:
            router._update_router_scheduler_row(project_root, run_root, run_state, row_id=row_id, router_state='reconciled', reconciliation=reconciliation)
        reconciled += 1
    if reconciled:
        router._rebuild_controller_action_ledger(project_root, run_root, run_state)
    return reconciled

def _reconcile_card_bundle_wait_rows(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, bundle_id: str, expected_return_path: str, card_return_event: str, source: str, ack_path: str | None) -> int:
    action_dir = router._controller_actions_dir(run_root)
    if not action_dir.exists():
        return 0
    reconciled = 0
    for action_path in sorted(action_dir.glob('*.json')):
        entry = router._read_json_for_runtime_scan(action_path)
        if entry is None:
            continue
        if entry.get('schema_version') != router.CONTROLLER_ACTION_SCHEMA:
            continue
        if entry.get('action_type') not in {'await_card_bundle_return_event', 'check_card_bundle_return_event'}:
            continue
        if not router._record_matches_card_bundle_identity(entry, bundle_id=bundle_id, expected_return_path=expected_return_path, card_return_event=card_return_event):
            continue
        reconciliation = {'source': source, 'card_bundle_id': bundle_id, 'card_return_event': card_return_event, 'expected_return_path': expected_return_path, 'ack_path': ack_path, 'reconciled_at': router.utc_now()}
        if entry.get('status') not in router.CONTROLLER_ACTION_CLOSED_STATUSES:
            entry['status'] = 'resolved'
            entry['completed_at'] = reconciliation['reconciled_at']
        entry['router_reconciliation_status'] = 'reconciled'
        entry['router_reconciliation'] = reconciliation
        entry['updated_at'] = router.utc_now()
        router.write_json(action_path, entry)
        row_id = str(entry.get('router_scheduler_row_id') or '')
        if row_id:
            router._update_router_scheduler_row(project_root, run_root, run_state, row_id=row_id, router_state='reconciled', reconciliation=reconciliation)
        reconciled += 1
    if reconciled:
        router._rebuild_controller_action_ledger(project_root, run_root, run_state)
    return reconciled

def _router_release_startup_user_intake_to_pm(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, source: str) -> dict[str, Any]:
    del project_root, run_root
    flags = run_state.get('flags', {})
    required_flags = ['startup_mechanical_audit_written', 'startup_display_status_written']
    missing_flags = [flag for flag in required_flags if not flags.get(flag)]
    if missing_flags:
        return {'released': False, 'reason': 'startup_runtime_mechanics_not_ready', 'requires_all_flags': required_flags, 'missing_flags': missing_flags}
    return {'released': False, 'reason': 'controller_deliver_mail_required', 'requires_action': 'deliver_mail', 'mail_id': 'user_intake', 'to_role': 'project_manager', 'source': source}

def _run_router_return_settlement_finalizers(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, source: str) -> dict[str, Any]:
    return_ledger = router._read_return_event_ledger(run_root, str(run_state['run_id']))
    pending_returns = return_ledger.setdefault('pending_returns', [])
    completed_returns = return_ledger.setdefault('completed_returns', [])
    changed = False
    normalized = 0
    normalized_card_acks = 0
    normalized_card_bundle_acks = 0
    wait_rows_reconciled = 0
    startup_release: dict[str, Any] | None = None
    completed_card_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    completed_bundle_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for completed in completed_returns:
        if not isinstance(completed, dict):
            continue
        status = str(completed.get('status') or '')
        if status not in router.CARD_ACK_COMPLETE_STATUSES:
            continue
        event = str(completed.get('card_return_event') or '')
        if completed.get('return_kind') == 'system_card_bundle':
            bundle_id = str(completed.get('card_bundle_id') or '')
            if bundle_id and event:
                completed_bundle_by_key[bundle_id, event] = completed
        else:
            delivery_attempt_id = str(completed.get('delivery_attempt_id') or '')
            if delivery_attempt_id and event:
                completed_card_by_key[delivery_attempt_id, event] = completed
    resolved_card_records: list[dict[str, Any]] = []
    resolved_records: list[dict[str, Any]] = []
    for pending in pending_returns:
        if not isinstance(pending, dict):
            continue
        if pending.get('return_kind') == 'system_card_bundle':
            continue
        delivery_attempt_id = str(pending.get('delivery_attempt_id') or '')
        event = str(pending.get('card_return_event') or '')
        completed = completed_card_by_key.get((delivery_attempt_id, event))
        status = str(pending.get('status') or '')
        if status not in router.CARD_ACK_COMPLETE_STATUSES and completed is None:
            continue
        ack_path = str(pending.get('ack_path') or (completed or {}).get('ack_path') or pending.get('expected_return_path') or '')
        envelope_path = str(pending.get('card_envelope_path') or (completed or {}).get('card_envelope_path') or '')
        if not ack_path or not envelope_path:
            continue
        try:
            validation = card_runtime.validate_card_ack(project_root, ack_path=ack_path, envelope_path=envelope_path)
        except card_runtime.CardRuntimeError:
            continue
        if pending.get('status') != 'resolved':
            pending['status'] = 'resolved'
            pending['resolved_at'] = router.utc_now()
            changed = True
            normalized += 1
            normalized_card_acks += 1
        pending['ack_path'] = validation['ack_path']
        pending['ack_hash'] = validation['ack_hash']
        pending['receipt_ref_count'] = validation['receipt_ref_count']
        record = dict(pending)
        if completed is not None:
            if completed.get('status') != 'resolved':
                completed['status'] = 'resolved'
                completed['resolved_at'] = pending.get('resolved_at') or router.utc_now()
                changed = True
                normalized += 1
                normalized_card_acks += 1
            completed['ack_path'] = validation['ack_path']
            completed['ack_hash'] = validation['ack_hash']
            completed['receipt_ref_count'] = validation['receipt_ref_count']
            record.update(completed)
        resolved_card_records.append(record)
    for pending in pending_returns:
        if not isinstance(pending, dict) or pending.get('return_kind') != 'system_card_bundle':
            continue
        bundle_id = str(pending.get('card_bundle_id') or '')
        event = str(pending.get('card_return_event') or '')
        completed = completed_bundle_by_key.get((bundle_id, event))
        status = str(pending.get('status') or '')
        if status not in router.CARD_BUNDLE_ACK_COMPLETE_STATUSES and completed is None:
            continue
        ack_path = str(pending.get('ack_path') or (completed or {}).get('ack_path') or pending.get('expected_return_path') or '')
        envelope_path = str(pending.get('card_bundle_envelope_path') or (completed or {}).get('card_bundle_envelope_path') or '')
        if not ack_path or not envelope_path:
            continue
        try:
            validation = card_runtime.validate_card_bundle_ack(project_root, ack_path=ack_path, envelope_path=envelope_path)
        except card_runtime.CardRuntimeError:
            continue
        if pending.get('status') != 'resolved':
            pending['status'] = 'resolved'
            pending['resolved_at'] = router.utc_now()
            changed = True
            normalized += 1
            normalized_card_bundle_acks += 1
        pending['ack_path'] = validation['ack_path']
        pending['ack_hash'] = validation['ack_hash']
        pending['receipt_ref_count'] = validation['receipt_ref_count']
        record = dict(pending)
        if completed is not None:
            if completed.get('status') != 'resolved':
                completed['status'] = 'resolved'
                completed['resolved_at'] = pending.get('resolved_at') or router.utc_now()
                changed = True
                normalized += 1
                normalized_card_bundle_acks += 1
            completed['ack_path'] = validation['ack_path']
            completed['ack_hash'] = validation['ack_hash']
            completed['receipt_ref_count'] = validation['receipt_ref_count']
            record.update(completed)
        resolved_records.append(record)
    if changed:
        return_ledger['updated_at'] = router.utc_now()
        router.write_json(router._return_event_ledger_path(run_root), return_ledger)
    for record in resolved_card_records:
        delivery_attempt_id = str(record.get('delivery_attempt_id') or '')
        event = str(record.get('card_return_event') or '')
        expected_return_path = str(record.get('expected_return_path') or record.get('ack_path') or '')
        card_id = str(record.get('card_id') or '')
        wait_rows_reconciled += router._reconcile_card_wait_rows(project_root, run_root, run_state, delivery_attempt_id=delivery_attempt_id, expected_return_path=expected_return_path, card_return_event=event, card_id=card_id, source=source, ack_path=str(record.get('ack_path') or ''))
        pending_action = run_state.get('pending_action')
        if router._pending_action_matches_card_return(pending_action, record):
            run_state['pending_action'] = None
            router.append_history(run_state, 'router_return_settlement_cleared_pending_card_wait', {'source': source, 'delivery_attempt_id': delivery_attempt_id, 'card_id': card_id, 'card_return_event': event, 'clearance_kind': 'ack_wait_only'})
    for record in resolved_records:
        bundle_id = str(record.get('card_bundle_id') or '')
        event = str(record.get('card_return_event') or '')
        expected_return_path = str(record.get('expected_return_path') or record.get('ack_path') or '')
        wait_rows_reconciled += router._reconcile_card_bundle_wait_rows(project_root, run_root, run_state, bundle_id=bundle_id, expected_return_path=expected_return_path, card_return_event=event, source=source, ack_path=str(record.get('ack_path') or ''))
        pending_action = run_state.get('pending_action')
        if router._pending_action_matches_card_return(pending_action, record):
            run_state['pending_action'] = None
            router.append_history(run_state, 'router_return_settlement_cleared_pending_card_bundle_wait', {'source': source, 'card_bundle_id': bundle_id, 'card_return_event': event})
        if router._startup_pm_card_bundle_ack_record(record):
            startup_release = router._router_release_startup_user_intake_to_pm(project_root, run_root, run_state, source=source)
    startup_release_changed = bool(startup_release and (startup_release.get('ledger_changed') or startup_release.get('state_changed') or (startup_release.get('released') and (not startup_release.get('already_released')))))
    if normalized or wait_rows_reconciled or startup_release_changed:
        router.append_history(run_state, 'router_return_settlement_finalizers_completed', {'source': source, 'normalized_return_acks': normalized, 'normalized_card_bundle_acks': normalized_card_bundle_acks, 'normalized_single_card_acks': normalized_card_acks, 'wait_rows_reconciled': wait_rows_reconciled, 'startup_user_intake_release': startup_release})
    return {'changed': bool(normalized or wait_rows_reconciled or startup_release_changed), 'normalized_return_acks': normalized, 'normalized_card_bundle_acks': normalized_card_bundle_acks, 'normalized_single_card_acks': normalized_card_acks, 'wait_rows_reconciled': wait_rows_reconciled, 'startup_user_intake_release': startup_release}

def _mark_card_return_pending_explicit_check(router: ModuleType, run_root: Path, run_id: str, action: dict[str, Any], *, reason: str, error: object=None) -> None:
    return_ledger = router._read_return_event_ledger(run_root, run_id)
    changed = False
    for item in return_ledger.setdefault('pending_returns', []):
        if not isinstance(item, dict):
            continue
        if router._pending_action_matches_card_return(action, item):
            item['status'] = 'invalid_ack_pending_explicit_check'
            item['invalid_ack_reason'] = reason
            item['invalid_ack_error'] = str(error or '')
            item.pop('resolved_at', None)
            changed = True
    if changed:
        return_ledger['pending_returns'] = sorted([item for item in return_ledger.get('pending_returns', []) if isinstance(item, dict)], key=lambda item: (0 if item.get('status') == 'invalid_ack_pending_explicit_check' else 1, 1 if item.get('status') == 'resolved' else 0, str(item.get('expected_return_path') or item.get('card_bundle_id') or item.get('delivery_attempt_id') or '')))
        return_ledger['updated_at'] = router.utc_now()
        router.write_json(router._return_event_ledger_path(run_root), return_ledger)

def _committed_card_bundle_artifact_extra(router: ModuleType, project_root: Path, record: dict[str, Any], *, relay_allowed_if_ready: bool) -> dict[str, Any]:
    envelope_path = str(record.get('card_bundle_envelope_path') or '')
    expected_return_path = str(record.get('expected_return_path') or '')
    expected_receipt_paths = record.get('expected_receipt_paths')
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
            recorded_hash = str(record.get('card_bundle_envelope_hash') or '')
            artifact_hash_verified = bool(recorded_hash) and envelope.get('bundle_hash') == recorded_hash
    artifact_committed = bool(artifact_exists and artifact_hash_verified and expected_return_path and isinstance(expected_receipt_paths, list) and expected_receipt_paths)
    return {'resource_lifecycle': 'committed_artifact' if artifact_committed else 'missing_committed_artifact', 'artifact_committed': artifact_committed, 'artifact_exists': artifact_exists, 'artifact_hash_verified': artifact_hash_verified, 'ledger_recorded': True, 'return_wait_recorded': bool(expected_return_path), 'relay_allowed': bool(relay_allowed_if_ready and artifact_committed), 'apply_required': False}

__all__ = (
    '_startup_pm_card_bundle_ack_record',
    '_reconcile_card_wait_rows',
    '_reconcile_card_bundle_wait_rows',
    '_router_release_startup_user_intake_to_pm',
    '_run_router_return_settlement_finalizers',
    '_mark_card_return_pending_explicit_check',
    '_committed_card_bundle_artifact_extra',
)
