"""Card ACK return settlement helpers for the FlowPilot router.

The public compatibility names stay in `flowpilot_router`.  This module owns
pending-return selection, ACK validation, wait-row reconciliation, and return
settlement finalizers.  It receives the router facade as an explicit dependency
so shared state writers remain centralized while the settlement logic leaves the
large entrypoint.
"""

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


def _current_node_pre_review_reconciliation_blockers(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    frontier = router._active_frontier(run_root)
    if str(frontier.get('status') or '') != 'current_node_loop':
        return []
    active_node_id = str(frontier.get('active_node_id') or '')
    if not active_node_id:
        return []
    flags = run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {}
    blockers: list[dict[str, Any]] = []
    required_flags = (('current_node_result_relayed_to_pm', 'current-node result must be relayed to PM before reviewer work'), ('current_node_result_disposition_recorded', 'PM disposition must be recorded before reviewer work'), ('current_node_result_absorbed_by_pm', 'PM must absorb current-node result before reviewer work'))
    for flag, reason in required_flags:
        if not flags.get(flag):
            blockers.append({'kind': 'missing_current_node_flag', 'flag': flag, 'reason': reason, 'scope_kind': 'current_node', 'node_id': active_node_id})
    batch = router._active_parallel_packet_batch(run_root, 'current_node')
    if not isinstance(batch, dict):
        blockers.append({'kind': 'missing_current_node_batch', 'reason': 'current-node review requires a current-node packet batch', 'scope_kind': 'current_node', 'node_id': active_node_id})
    elif str(batch.get('node_id') or '') == active_node_id:
        batch_status = str(batch.get('status') or '')
        if batch_status != 'pm_absorbed':
            blockers.append({'kind': 'current_node_batch_not_absorbed', 'batch_id': batch.get('batch_id'), 'batch_status': batch_status, 'reason': 'current-node batch must be PM-absorbed before reviewer work', 'scope_kind': 'current_node', 'node_id': active_node_id})
    else:
        blockers.append({'kind': 'missing_current_node_batch_for_active_node', 'batch_id': batch.get('batch_id'), 'batch_node_id': batch.get('node_id'), 'reason': 'active node has no matching local current-node batch', 'scope_kind': 'current_node', 'node_id': active_node_id})
    for pending_return in router._pending_return_records(run_root, str(run_state['run_id'])):
        if router._pending_return_matches_active_node_scope(pending_return, frontier):
            blockers.append({'kind': 'pending_current_node_card_return', 'card_id': pending_return.get('card_id'), 'card_ids': pending_return.get('card_ids') or [], 'target_role': pending_return.get('target_role'), 'card_return_event': pending_return.get('card_return_event'), 'expected_return_path': pending_return.get('expected_return_path'), 'reason': 'current-node system-card ACK/read receipt must close before reviewer work', 'scope_kind': 'current_node', 'node_id': active_node_id})
    return blockers


def _startup_pre_review_reconciliation_blockers(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    flags = run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {}
    blockers: list[dict[str, Any]] = []
    required_flags = (('banner_emitted', 'startup banner display must be reconciled before startup fact review'), ('roles_started', 'startup role slots must be reconciled before startup fact review'), ('role_core_prompts_injected', 'startup role core prompts must be reconciled before startup fact review'), ('controller_role_confirmed', 'Controller boundary confirmation must be reconciled before startup fact review'), ('startup_mechanical_audit_written', 'startup mechanical audit must be reconciled before startup fact review'), ('startup_display_status_written', 'startup display status must be reconciled before startup fact review'))
    answers = router._startup_answers_from_run(run_root)
    if router._scheduled_continuation_requested(answers):
        required_flags = (('continuation_binding_recorded', 'startup heartbeat binding must be reconciled before startup fact review'), *required_flags)
    for flag, reason in required_flags:
        if not flags.get(flag):
            blockers.append({'kind': 'missing_startup_flag', 'flag': flag, 'reason': reason, 'scope_kind': 'startup', 'scope_id': 'startup'})
    try:
        bootstrap = router.load_bootstrap_state(project_root, create_if_missing=False)
    except router.RouterError:
        bootstrap = {}
    bootstrap_flags = bootstrap.get('flags') if isinstance(bootstrap.get('flags'), dict) else {}
    for flag, reason in (('banner_emitted', 'startup banner display must be reconciled before startup fact review'), ('roles_started', 'startup role slots must be reconciled before startup fact review')):
        if not bootstrap_flags.get(flag):
            blockers.append({'kind': 'missing_startup_bootstrap_flag', 'flag': flag, 'reason': reason, 'scope_kind': 'startup', 'scope_id': 'startup'})
    if not router._startup_pre_review_cards_delivered(run_state):
        blockers.append({'kind': 'startup_prep_cards_not_all_sent', 'missing_card_flags': sorted((flag for flag in router._startup_pre_review_card_flags() if not flags.get(flag))), 'reason': 'startup prep cards must be sent before Reviewer startup fact review', 'scope_kind': 'startup', 'scope_id': 'startup'})
    for pending_return in router._startup_pre_review_pending_returns(run_root, run_state):
        blockers.append({'kind': 'pending_startup_prep_card_return', 'card_id': pending_return.get('card_id'), 'card_ids': pending_return.get('card_ids') or [], 'target_role': pending_return.get('target_role'), 'card_return_event': pending_return.get('card_return_event'), 'expected_return_path': pending_return.get('expected_return_path'), 'reason': 'startup prep card ACK/read receipt must close before Reviewer startup fact review', 'scope_kind': 'startup', 'scope_id': 'startup'})
    action_dir = router._controller_actions_dir(run_root)
    if action_dir.exists():
        for action_path in sorted(action_dir.glob('*.json')):
            entry = router._read_json_for_runtime_scan(action_path)
            if entry is None:
                continue
            if entry.get('schema_version') != router.CONTROLLER_ACTION_SCHEMA:
                continue
            if not router._controller_action_is_ordinary_work_row(entry):
                continue
            if entry.get('status') in {'done', 'blocked', 'skipped'} and entry.get('router_reconciliation_status') == 'reconciled':
                continue
            action = entry.get('action') if isinstance(entry.get('action'), dict) else {}
            scope_kind = str(entry.get('scope_kind') or action.get('scope_kind') or '')
            if scope_kind != 'startup' and (not router._action_is_startup_scoped(action)):
                continue
            if entry.get('action_type') in {'await_card_return_event', 'await_card_bundle_return_event'}:
                continue
            if entry.get('status') not in {'done', 'blocked', 'skipped'} or entry.get('router_reconciliation_status') != 'reconciled':
                blockers.append({'kind': 'pending_startup_controller_row', 'action_id': entry.get('action_id'), 'action_type': entry.get('action_type'), 'status': entry.get('status'), 'router_reconciliation_status': entry.get('router_reconciliation_status'), 'reason': 'startup-local Controller row must be done and Router-reconciled before Reviewer startup fact review', 'scope_kind': 'startup', 'scope_id': 'startup'})
    active_blocker = run_state.get('active_control_blocker')
    if isinstance(active_blocker, dict) and active_blocker.get('status') not in {'resolved', 'superseded', 'closed'} and (not router._resume_reentry_gate_pending(run_state)):
        blockers.append({'kind': 'active_startup_control_blocker', 'control_blocker_id': active_blocker.get('control_blocker_id'), 'source': active_blocker.get('source'), 'reason': 'active local control blocker must be resolved before Reviewer startup fact review', 'scope_kind': 'startup', 'scope_id': 'startup'})
    return blockers


def _pre_review_reconciliation_blockers_for_trigger(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], review_trigger: str) -> list[dict[str, Any]]:
    if review_trigger in router.STARTUP_REVIEW_BEGIN_JOIN_EVENTS or review_trigger == router.REVIEWER_STARTUP_FACT_CARD_ID:
        return router._startup_pre_review_reconciliation_blockers(project_root, run_root, run_state)
    return router._current_node_pre_review_reconciliation_blockers(project_root, run_root, run_state)


def _current_scope_reconciliation_wait_still_blocked(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], pending_action: dict[str, Any]) -> bool:
    if pending_action.get('action_type') != 'await_current_scope_reconciliation':
        return False
    if pending_action.get('scope_kind') == 'startup':
        return bool(router._startup_pre_review_reconciliation_blockers(project_root, run_root, run_state))
    if pending_action.get('scope_kind') != 'current_node':
        return False
    return bool(router._current_node_pre_review_reconciliation_blockers(project_root, run_root, run_state))


def _next_local_obligation_before_passive_wait(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], pending_action: dict[str, Any]) -> dict[str, Any] | None:
    if pending_action.get('action_type') != 'await_current_scope_reconciliation':
        return None
    if pending_action.get('scope_kind') != 'startup':
        return None
    for producer in (router._next_controller_boundary_confirmation_action, router._next_startup_mechanical_audit_action, router._next_startup_display_action):
        action = producer(project_root, run_state, run_root)
        if action is not None:
            action['preempts_passive_wait_action_type'] = pending_action.get('action_type')
            action['preempts_passive_wait_label'] = pending_action.get('label')
            return action
    return None


def _current_node_scope_exit_reconciliation_blockers(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], frontier: dict[str, Any]) -> list[dict[str, Any]]:
    active_node_id = str(frontier.get('active_node_id') or '')
    if not active_node_id:
        return []
    flags = run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {}
    blockers: list[dict[str, Any]] = []
    required_flags = (('current_node_result_disposition_recorded', 'PM disposition must remain recorded before node exit'), ('current_node_result_absorbed_by_pm', 'PM absorption must remain recorded before node exit'), ('node_reviewer_passed_result', 'Reviewer pass must remain recorded before node exit'))
    for flag, reason in required_flags:
        if not flags.get(flag):
            blockers.append({'kind': 'missing_current_node_exit_flag', 'flag': flag, 'reason': reason, 'scope_kind': 'current_node', 'node_id': active_node_id})
    batch = router._active_parallel_packet_batch(run_root, 'current_node')
    if isinstance(batch, dict) and str(batch.get('node_id') or '') == active_node_id:
        batch_status = str(batch.get('status') or '')
        if batch_status != 'reviewed':
            blockers.append({'kind': 'current_node_batch_not_reviewed', 'batch_id': batch.get('batch_id'), 'batch_status': batch_status, 'reason': 'current-node review-created obligations must close before node exit', 'scope_kind': 'current_node', 'node_id': active_node_id})
    for pending_return in router._pending_return_records(run_root, str(run_state['run_id'])):
        if router._pending_return_matches_active_node_scope(pending_return, frontier):
            blockers.append({'kind': 'pending_current_node_card_return', 'card_id': pending_return.get('card_id'), 'card_ids': pending_return.get('card_ids') or [], 'target_role': pending_return.get('target_role'), 'card_return_event': pending_return.get('card_return_event'), 'expected_return_path': pending_return.get('expected_return_path'), 'reason': 'current-node system-card ACK/read receipt must close before node exit', 'scope_kind': 'current_node', 'node_id': active_node_id})
    return blockers


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
        return router.make_action(action_type='await_card_bundle_return_event', actor='controller', label=f"controller_waits_for_card_bundle_return_{router._safe_delivery_component(str(record.get('card_bundle_id') or 'pending'))}", summary=summary, allowed_reads=[envelope_path, router.project_relative(project_root, router._return_event_ledger_path(run_root)), router.project_relative(project_root, router._card_ledger_path(run_root)), *[str(path) for path in delivery_fact.get('controller_read_paths') or []]], allowed_writes=[router.project_relative(project_root, router._return_event_ledger_path(run_root)), router.project_relative(project_root, router.run_state_path(run_root))], card_id=(record.get('card_ids') or [''])[0] if isinstance(record.get('card_ids'), list) else None, to_role=str(record.get('target_role') or ''), extra={'card_return_event': record.get('card_return_event'), 'card_bundle_id': record.get('card_bundle_id'), 'card_ids': record.get('card_ids') or [], 'delivery_attempt_ids': record.get('delivery_attempt_ids') or [], 'expected_return_path': expected_return_path, 'card_bundle_envelope_path': envelope_path, 'expected_receipt_paths': record.get('expected_receipt_paths') or [], 'bundle_ack_incomplete': ack_is_unchanged_incomplete, 'missing_card_ids': record.get('missing_card_ids') or [], 'incomplete_ack_path': record.get('incomplete_ack_path'), 'incomplete_ack_hash': record.get('incomplete_ack_hash'), 'ack_clearance_reason': clearance_reason, **clearance_scope_extra, 'waiting_for_role': record.get('target_role'), 'waiting_for_agent_id': record.get('target_agent_id'), 'controller_visibility': 'pending_return_metadata_only', 'sealed_body_reads_allowed': False, **router._original_card_ack_reminder_policy(record, bundle=True, delivery_fact=delivery_fact), **committed_extra, 'next_recovery_actions': ['controller_confirms_or_reissues_original_committed_bundle_delivery_first', 'role_uses_open-card-bundle_then_ack-card-bundle_after_delivery_confirmed', 'controller_reminds_role_to_ack_original_committed_bundle_if_delivery_confirmed', 'router_reissues_bundle_only_if_original_invalid_lost_stale_or_role_replaced', 'router_records_protocol_blocker_if_bundle_ack_is_invalid']})
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
    return router.make_action(action_type='await_card_return_event', actor='controller', label=f"controller_waits_for_card_return_{router._safe_delivery_component(str(record.get('delivery_attempt_id') or 'pending'))}", summary=summary, allowed_reads=[envelope_path, router.project_relative(project_root, router._return_event_ledger_path(run_root)), router.project_relative(project_root, router._card_ledger_path(run_root)), *[str(path) for path in delivery_fact.get('controller_read_paths') or []]], allowed_writes=[router.project_relative(project_root, router._return_event_ledger_path(run_root)), router.project_relative(project_root, router.run_state_path(run_root))], to_role=str(record.get('target_role') or ''), extra={'card_return_event': record.get('card_return_event'), 'delivery_id': record.get('delivery_id'), 'delivery_attempt_id': record.get('delivery_attempt_id'), 'card_id': record.get('card_id'), 'expected_return_path': expected_return_path, 'card_envelope_path': envelope_path, 'expected_receipt_path': record.get('expected_receipt_path'), 'ack_clearance_reason': clearance_reason, **clearance_scope_extra, 'ack_clearance_scope': record.get('ack_clearance_scope'), 'waiting_for_role': record.get('target_role'), 'waiting_for_agent_id': record.get('target_agent_id'), 'controller_visibility': 'pending_return_metadata_only', 'sealed_body_reads_allowed': False, **router._original_card_ack_reminder_policy(record, bundle=False, delivery_fact=delivery_fact), **committed_extra, 'next_recovery_actions': ['controller_confirms_or_reissues_original_committed_card_delivery_first', 'role_uses_open-card_then_ack-card_after_delivery_confirmed', 'controller_reminds_role_to_ack_original_committed_card_if_delivery_confirmed', 'router_reissues_card_only_if_original_invalid_lost_stale_or_role_replaced', 'router_records_protocol_blocker_if_ack_is_invalid']})


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
    if not run_state.get('flags', {}).get('startup_activation_approved'):
        return {'released': False, 'reason': 'startup_activation_not_approved', 'requires_flag': 'startup_activation_approved'}
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
            startup_release = {'released': False, 'reason': 'controller_deliver_mail_required' if run_state.get('flags', {}).get('startup_activation_approved') else 'startup_activation_not_approved', 'requires_flag': 'startup_activation_approved', 'requires_action': 'deliver_mail', 'mail_id': 'user_intake', 'to_role': 'project_manager', 'source': source}
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
