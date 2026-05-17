"""External event identity and payload helpers for FlowPilot router.

The facade still records external events and owns the side-effect dispatcher.
This module owns payload reconstruction, event-envelope validation, scoped
idempotency keys, retry-budget records, and already-recorded event replay.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import ModuleType
from typing import Any


def _load_file_backed_role_payload(router: ModuleType, project_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Load a role report/decision body from an envelope-only event payload."""
    if not isinstance(payload, dict):
        raise router.RouterError('role event payload must be an object')
    path_keys = ('body_path', 'report_path', 'decision_path', 'result_body_path', 'memo_path', 'architecture_path', 'contract_path', 'manifest_path', 'route_path', 'draft_path', 'plan_path', 'package_path', 'ledger_path')
    hash_keys = ('body_hash', 'report_hash', 'decision_hash', 'result_body_hash', 'memo_hash', 'architecture_hash', 'contract_hash', 'manifest_hash', 'route_hash', 'draft_hash', 'plan_hash', 'package_hash', 'ledger_hash')
    body_path_key = next((key for key in path_keys if payload.get(key)), None)
    body_ref = payload.get('body_ref') if isinstance(payload.get('body_ref'), dict) else None
    if not body_path_key and body_ref and body_ref.get('path'):
        body_path_key = str(body_ref.get('path_key') or 'body_ref.path')
    if not body_path_key:
        if 'path' in payload or 'hash' in payload:
            raise router.RouterError('role event envelope must use body_ref.path/body_ref.hash or a known body_path/report_path/decision_path/result_body_path path/hash pair')
        raise router.RouterError('role event requires a file-backed body path')
    body_hash_key = next((key for key in hash_keys if payload.get(key)), None)
    if not body_hash_key and body_ref and body_ref.get('hash'):
        body_hash_key = str(body_ref.get('hash_key') or 'body_ref.hash')
    if not body_hash_key:
        raise router.RouterError('role event requires a body/report/decision hash')
    body_path = body_ref['path'] if body_ref and body_ref.get('path') and (not payload.get(body_path_key)) else payload[body_path_key]
    forbidden_controller_visible_body_keys = {'blockers', 'checks', 'decision', 'evidence', 'findings', 'passed', 'recommendations', 'repair_instructions', 'commands', 'report_body', 'decision_body', 'result_body'}
    leaked_keys = sorted(forbidden_controller_visible_body_keys & set(payload))
    if leaked_keys:
        raise router.RouterError(f"envelope payload leaked role body fields to Controller: {', '.join(leaked_keys)}")
    try:
        runtime_receipt = router.role_output_runtime.validate_envelope_runtime_receipt(project_root, payload)
    except router.role_output_runtime.RoleOutputRuntimeError as exc:
        raise router.RouterError(str(exc)) from exc
    path = router.resolve_project_path(project_root, str(body_path))
    if not path.exists():
        raise router.RouterError(f'role body path is missing: {body_path}')
    expected_hash = str(body_ref['hash'] if body_ref and body_ref.get('hash') and (not payload.get(body_hash_key)) else payload[body_hash_key])
    raw_hash, semantic_hash = router._role_output_hashes(path)
    accepted_hashes = {raw_hash}
    accepted_hashes.update(router._role_output_semantic_hashes(path))
    if expected_hash not in accepted_hashes:
        raise router.RouterError('role body hash mismatch')
    loaded = router.read_json(path)
    replay_hash = semantic_hash or raw_hash
    loaded['_role_output_envelope'] = {'body_path': router.project_relative(project_root, path), 'body_hash': replay_hash, 'body_raw_sha256': raw_hash, 'body_semantic_sha256': semantic_hash, 'body_path_key': body_path_key, 'body_hash_key': body_hash_key, 'controller_visibility': payload.get('controller_visibility') or 'role_output_envelope_only', 'chat_response_body_allowed': False}
    if isinstance(runtime_receipt, dict):
        receipt_ref = payload.get('runtime_receipt_ref') if isinstance(payload.get('runtime_receipt_ref'), dict) else {}
        loaded['_role_output_envelope']['role_output_runtime_receipt_path'] = receipt_ref.get('path') or payload.get('role_output_runtime_receipt_path')
        loaded['_role_output_envelope']['role_output_runtime_receipt_hash'] = receipt_ref.get('hash') or payload.get('role_output_runtime_receipt_hash')
        loaded['_role_output_envelope']['role_output_runtime_validated'] = True
        loaded['_role_output_envelope']['output_type'] = runtime_receipt.get('output_type')
        loaded['_role_output_envelope']['output_contract_id'] = runtime_receipt.get('output_contract_id')
    return loaded


def _load_file_backed_role_payload_if_present(router: ModuleType, project_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    path_keys = {'body_path', 'report_path', 'decision_path', 'result_body_path', 'memo_path', 'architecture_path', 'contract_path', 'manifest_path', 'route_path', 'draft_path', 'plan_path', 'package_path', 'ledger_path'}
    if isinstance(payload, dict) and (any((payload.get(key) for key in path_keys)) or (isinstance(payload.get('body_ref'), dict) and payload['body_ref'].get('path'))):
        return router._load_file_backed_role_payload(project_root, payload)
    return payload


def _record_event_envelope_ref_from_payload(router: ModuleType, payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    ref = payload.get('event_envelope_ref')
    if ref is None:
        return None
    if not isinstance(ref, dict):
        raise router.RouterError('event_envelope_ref must be an object with path and hash')
    return ref


def _looks_like_record_event_envelope(router: ModuleType, payload: dict[str, Any] | None) -> bool:
    if not isinstance(payload, dict):
        return False
    schema = payload.get('schema_version')
    return isinstance(schema, str) and schema in router.ALLOWED_RECORD_EVENT_ENVELOPE_SCHEMAS and bool(payload.get('event') or payload.get('event_name'))


def _payload_requires_record_event_envelope_validation(router: ModuleType, payload: dict[str, Any] | None, *, envelope_path: str | None=None, envelope_hash: str | None=None) -> bool:
    if envelope_path or envelope_hash:
        return True
    if router._record_event_envelope_ref_from_payload(payload) is not None:
        return True
    return router._looks_like_record_event_envelope(payload)


def _currently_allowed_external_events(router: ModuleType, run_state: dict[str, Any]) -> list[str]:
    pending_action = run_state.get('pending_action')
    if isinstance(pending_action, dict) and pending_action.get('action_type') == 'await_role_decision':
        raw_allowed = pending_action.get('allowed_external_events')
        if isinstance(raw_allowed, list) and all((isinstance(item, str) for item in raw_allowed)):
            try:
                allowed = router._validated_external_event_names(raw_allowed, context='pending role wait')
            except router.RouterError:
                if pending_action.get('label') == 'controller_waits_for_control_blocker_resolution' and pending_action.get('handling_lane') in router.PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES:
                    allowed = [router.PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT]
                else:
                    allowed = []
            to_role = str(pending_action.get('to_role') or '')
            if 'project_manager' in {part.strip() for part in to_role.split(',')} and router.PM_ROLE_WORK_REQUEST_EVENT not in allowed:
                allowed.append(router.PM_ROLE_WORK_REQUEST_EVENT)
            return allowed
    groups = router._pending_expected_external_event_groups(run_state)
    if groups:
        group = router._gate_completion_wait_group(groups[0])
        allowed = [event for event, _meta in group]
        if any((router._event_wait_role(event, meta) == 'project_manager' for event, meta in group)):
            allowed.append(router.PM_ROLE_WORK_REQUEST_EVENT)
        return allowed
    return []


def _record_event_expected_role(router: ModuleType, event: str, run_state: dict[str, Any]) -> str:
    if event == router.ROLE_WORK_RESULT_RETURNED_EVENT:
        summary = run_state.get('pm_role_work_requests') if isinstance(run_state.get('pm_role_work_requests'), dict) else {}
        active_to_role = str(summary.get('active_to_role') or '').strip()
        if active_to_role:
            return active_to_role
        return ','.join(sorted(router.PM_ROLE_WORK_REQUEST_RECIPIENT_ROLES))
    pending_action = run_state.get('pending_action')
    if isinstance(pending_action, dict) and pending_action.get('action_type') == 'await_role_decision':
        raw_allowed = pending_action.get('allowed_external_events')
        if isinstance(raw_allowed, list) and event in raw_allowed:
            if (pending_action.get('label') == 'controller_waits_for_control_blocker_resolution' or pending_action.get('blocker_artifact_path')) and event != router.PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT:
                meta = router.EXTERNAL_EVENTS.get(event) or {}
                return router._event_wait_role(event, meta)
            to_role = pending_action.get('to_role')
            if isinstance(to_role, str) and to_role:
                return to_role
    meta = router.EXTERNAL_EVENTS.get(event) or {}
    return router._event_wait_role(event, meta)


def _record_event_from_role_matches(router: ModuleType, event: str, from_role: str, expected_role: str) -> bool:
    if from_role == expected_role:
        return True
    if event.startswith('worker_') and expected_role == 'worker_a' and (from_role in {'worker_a', 'worker_b'}):
        return True
    if ',' in expected_role and from_role in {part.strip() for part in expected_role.split(',') if part.strip()}:
        return True
    return False


def _validate_record_event_envelope(router: ModuleType, project_root: Path, run_state: dict[str, Any], *, event: str, envelope: dict[str, Any]) -> dict[str, Any]:
    schema = envelope.get('schema_version')
    if schema not in router.ALLOWED_RECORD_EVENT_ENVELOPE_SCHEMAS:
        allowed = ', '.join(sorted(router.ALLOWED_RECORD_EVENT_ENVELOPE_SCHEMAS))
        raise router.RouterError(f'event envelope schema_version must be one of: {allowed}')
    envelope_event = envelope.get('event') or envelope.get('event_name')
    if envelope_event != event:
        raise router.RouterError(f'event envelope event mismatch: expected {event}, got {envelope_event!r}')
    currently_allowed = router._currently_allowed_external_events(run_state)
    meta = router.EXTERNAL_EVENTS.get(event) or {}
    flag = meta.get('flag')
    event_already_recorded = bool(flag and run_state.get('flags', {}).get(flag))
    if event not in currently_allowed and (not event_already_recorded):
        allowed_display = ', '.join(currently_allowed) if currently_allowed else 'none'
        raise router.RouterError(f'event envelope is not currently allowed by router wait state: {event}; allowed: {allowed_display}')
    from_role = envelope.get('from_role')
    if not isinstance(from_role, str) or not from_role:
        raise router.RouterError('event envelope requires from_role')
    expected_role = router._record_event_expected_role(event, run_state)
    if not router._record_event_from_role_matches(event, from_role, expected_role):
        raise router.RouterError(f'event envelope from_role mismatch: expected {expected_role}, got {from_role}')
    visibility = envelope.get('controller_visibility')
    if visibility not in router.ALLOWED_RECORD_EVENT_CONTROLLER_VISIBILITIES:
        allowed = ', '.join(sorted(router.ALLOWED_RECORD_EVENT_CONTROLLER_VISIBILITIES))
        raise router.RouterError(f'event envelope controller_visibility must be one of: {allowed}')
    leaked_keys = sorted(router.FORBIDDEN_RECORD_EVENT_ENVELOPE_BODY_FIELDS & set(envelope))
    if leaked_keys:
        raise router.RouterError(f"event envelope leaked role body fields to Controller: {', '.join(leaked_keys)}")
    return envelope


def _load_record_event_envelope_ref(router: ModuleType, project_root: Path, run_state: dict[str, Any], *, event: str, path: str, expected_hash: str) -> dict[str, Any]:
    if not path:
        raise router.RouterError('record-event --envelope-path or event_envelope_ref.path is required')
    if not expected_hash:
        raise router.RouterError('record-event --envelope-hash or event_envelope_ref.hash is required')
    resolved = router.resolve_project_path(project_root, path)
    router.project_relative(project_root, resolved)
    if not resolved.exists():
        raise router.RouterError(f'event envelope file is missing: {path}')
    if not resolved.is_file():
        raise router.RouterError(f'event envelope path is not a file: {path}')
    actual_hash = router.packet_runtime.sha256_file(resolved)
    if actual_hash != expected_hash:
        raise router.RouterError('event envelope hash mismatch')
    envelope = router.read_json(resolved)
    return router._validate_record_event_envelope(project_root, run_state, event=event, envelope=envelope)


def _normalize_record_event_payload(router: ModuleType, project_root: Path, run_state: dict[str, Any], *, event: str, payload: dict[str, Any] | None, envelope_path: str | None=None, envelope_hash: str | None=None) -> dict[str, Any]:
    payload = payload or {}
    if envelope_path or envelope_hash:
        return router._load_record_event_envelope_ref(project_root, run_state, event=event, path=str(envelope_path or ''), expected_hash=str(envelope_hash or ''))
    ref = router._record_event_envelope_ref_from_payload(payload)
    if ref is not None:
        return router._load_record_event_envelope_ref(project_root, run_state, event=event, path=str(ref.get('path') or ''), expected_hash=str(ref.get('hash') or ''))
    if router._looks_like_record_event_envelope(payload):
        return router._validate_record_event_envelope(project_root, run_state, event=event, envelope=payload)
    return payload


def _stable_identity_hash(router: ModuleType, value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def _event_identity_ledger(router: ModuleType, run_state: dict[str, Any]) -> dict[str, Any]:
    ledger = run_state.get('external_event_idempotency')
    if not isinstance(ledger, dict):
        ledger = {}
        run_state['external_event_idempotency'] = ledger
    ledger.setdefault('schema_version', router.EVENT_IDEMPOTENCY_LEDGER_SCHEMA)
    processed = ledger.get('processed')
    if not isinstance(processed, dict):
        processed = {}
        ledger['processed'] = processed
    attempts = ledger.get('attempts')
    if not isinstance(attempts, list):
        attempts = []
        ledger['attempts'] = attempts
    return ledger


def _payload_view_for_event_identity(router: ModuleType, project_root: Path, event: str, payload: dict[str, Any]) -> dict[str, Any]:
    if event not in router.SCOPED_EVENT_IDENTITY_POLICIES:
        return payload
    return router._load_file_backed_role_payload_if_present(project_root, payload)


def _payload_body_hash(router: ModuleType, payload_view: dict[str, Any]) -> str:
    envelope = payload_view.get('_role_output_envelope')
    if isinstance(envelope, dict):
        for key in ('body_hash', 'body_raw_sha256', 'body_semantic_sha256'):
            value = str(envelope.get(key) or '').strip()
            if value:
                return value
    return router._stable_identity_hash(payload_view)


def _frontier_for_event_identity(router: ModuleType, run_root: Path) -> dict[str, Any]:
    frontier = router.read_json_if_exists(run_root / 'execution_frontier.json')
    return frontier if isinstance(frontier, dict) else {}


def _active_control_blocker_for_identity(router: ModuleType, run_state: dict[str, Any]) -> dict[str, Any]:
    active = run_state.get('active_control_blocker')
    return active if isinstance(active, dict) else {}


def _route_mutation_identity_scope(router: ModuleType, run_root: Path, run_state: dict[str, Any], payload_view: dict[str, Any]) -> dict[str, str]:
    frontier = router._frontier_for_event_identity(run_root)
    active = router._active_control_blocker_for_identity(run_state)
    active_block_flags = router._active_model_miss_review_block_flags(run_state)
    route_id = str(payload_view.get('route_id') or frontier.get('active_route_id') or 'route-001')
    raw_route_version = payload_view.get('route_version')
    route_version = str(raw_route_version).strip() if raw_route_version not in (None, '') else ''
    repair_identity = {'active_node_id': payload_view.get('active_node_id') or payload_view.get('repair_node_id') or frontier.get('active_node_id'), 'reason': payload_view.get('reason'), 'repair_action': payload_view.get('repair_action') or payload_view.get('selected_next_action'), 'stale_evidence': payload_view.get('stale_evidence') or [], 'superseded_nodes': payload_view.get('superseded_nodes') or [], 'body_hash': router._payload_body_hash(payload_view)}
    return {'event': 'pm_mutates_route_after_review_block', 'control_blocker_id': str(payload_view.get('control_blocker_id') or payload_view.get('blocker_id') or active.get('blocker_id') or 'no-control-blocker'), 'repair_transaction_id': str(payload_view.get('repair_transaction_id') or payload_view.get('transaction_id') or active.get('repair_transaction_id') or 'no-repair-transaction'), 'route_id': route_id, 'route_version': route_version or f'payload:{router._stable_identity_hash(repair_identity)}', 'model_miss_block': ','.join(active_block_flags) or 'no-model-miss-block'}


def _control_blocker_repair_decision_identity_scope(router: ModuleType, payload_view: dict[str, Any], run_state: dict[str, Any]) -> dict[str, str]:
    active = router._active_control_blocker_for_identity(run_state)
    blocker_id = str(payload_view.get('blocker_id') or active.get('blocker_id') or 'missing-blocker')
    return {'event': router.PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT, 'control_blocker_id': blocker_id, 'repair_transaction_id': str(payload_view.get('repair_transaction_id') or f'repair-tx-{blocker_id}')}


def _control_blocker_repair_outcome_identity_scope(router: ModuleType, payload_view: dict[str, Any], run_state: dict[str, Any], event: str) -> dict[str, str]:
    active = router._active_control_blocker_for_identity(run_state)
    blocker_id = str(payload_view.get('blocker_id') or active.get('blocker_id') or 'missing-blocker')
    outcome = 'protocol_blocker' if event in {router.PM_CONTROL_BLOCKER_PROTOCOL_BLOCKER_EVENT, router.PM_PARENT_PROTOCOL_BLOCKER_EVENT} else 'blocker'
    return {'event': event, 'control_blocker_id': blocker_id, 'repair_transaction_id': str(payload_view.get('repair_transaction_id') or active.get('repair_transaction_id') or f'repair-tx-{blocker_id}'), 'outcome': outcome}


def _gate_decision_identity_scope(router: ModuleType, run_root: Path, payload_view: dict[str, Any]) -> dict[str, str]:
    frontier = router._frontier_for_event_identity(run_root)
    return {'event': router.GATE_DECISION_EVENT, 'gate_id': str(payload_view.get('gate_id') or 'missing-gate-id'), 'route_version': str(payload_view.get('route_version') or frontier.get('route_version') or 'no-route-version'), 'decided_by_role': str(payload_view.get('owner_role') or payload_view.get('decided_by_role') or 'unknown-role')}


def _startup_repair_identity_scope(router: ModuleType, run_root: Path, run_state: dict[str, Any], payload_view: dict[str, Any]) -> dict[str, str]:
    fact_report_path = run_root / 'startup' / 'startup_fact_report.json'
    fact_hash = router.packet_runtime.sha256_file(fact_report_path) if fact_report_path.exists() else 'missing-startup-fact-report'
    return {'event': 'pm_requests_startup_repair', 'startup_review_cycle': str(payload_view.get('startup_review_cycle') or int(run_state.get('startup_repair_cycle') or 0) + 1), 'startup_fact_report_hash': str(payload_view.get('startup_fact_report_hash') or payload_view.get('blocked_report_hash') or fact_hash), 'decision_hash': router._payload_body_hash(payload_view)}


def _route_draft_identity_scope(router: ModuleType, payload_view: dict[str, Any]) -> dict[str, str]:
    route_payload = payload_view.get('route') if isinstance(payload_view.get('route'), dict) else {}
    route_id = str(payload_view.get('route_id') or route_payload.get('route_id') or 'route-001')
    route_hash = str(payload_view.get('route_hash') or payload_view.get('draft_hash') or router._payload_body_hash(payload_view))
    return {'event': 'pm_writes_route_draft', 'route_id': route_id, 'draft_version': str(payload_view.get('draft_version') or payload_view.get('route_version') or route_payload.get('route_version') or '1'), 'route_hash': route_hash}


def _current_node_completion_identity_scope(router: ModuleType, run_root: Path, run_state: dict[str, Any], payload_view: dict[str, Any]) -> dict[str, str]:
    frontier = router._frontier_for_event_identity(run_root)
    node_id = str(payload_view.get('node_id') or frontier.get('active_node_id') or 'missing-node')
    packet_id = str(payload_view.get('packet_id') or frontier.get('active_packet_id') or run_state.get('current_node_packet_id') or 'missing-packet')
    result_hash = str(payload_view.get('result_hash') or payload_view.get('result_body_hash') or payload_view.get('body_hash') or '')
    if not result_hash:
        result_hash = router._payload_body_hash(payload_view)
    return {'event': 'pm_completes_current_node_from_reviewed_result', 'node_id': node_id, 'packet_id': packet_id, 'result_hash': result_hash}


def _pm_role_work_request_identity_scope(router: ModuleType, payload_view: dict[str, Any]) -> dict[str, str]:
    return {'event': router.PM_ROLE_WORK_REQUEST_EVENT, 'request_id': str(payload_view.get('request_id') or 'missing-request-id')}


def _role_work_result_identity_scope(router: ModuleType, payload_view: dict[str, Any]) -> dict[str, str]:
    result_hash = str(payload_view.get('result_hash') or payload_view.get('result_body_hash') or payload_view.get('body_hash') or '')
    if not result_hash:
        result_hash = router._payload_body_hash(payload_view)
    return {'event': router.ROLE_WORK_RESULT_RETURNED_EVENT, 'request_id': str(payload_view.get('request_id') or 'missing-request-id'), 'packet_id': str(payload_view.get('packet_id') or 'missing-packet-id'), 'result_hash': result_hash}


def _current_node_result_identity_scope(router: ModuleType, payload_view: dict[str, Any]) -> dict[str, str]:
    result_hash = str(payload_view.get('result_hash') or payload_view.get('result_body_hash') or payload_view.get('body_hash') or '')
    if not result_hash:
        result_hash = router._payload_body_hash(payload_view)
    return {'event': 'worker_current_node_result_returned', 'packet_id': str(payload_view.get('packet_id') or 'missing-packet-id'), 'result_hash': result_hash}


def _pm_role_work_result_decision_identity_scope(router: ModuleType, payload_view: dict[str, Any]) -> dict[str, str]:
    return {'event': router.PM_ROLE_WORK_RESULT_DECISION_EVENT, 'request_id': str(payload_view.get('request_id') or 'missing-request-id'), 'decision': str(payload_view.get('decision') or 'missing-decision')}


def _scoped_event_identity(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], event: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    policy = router.SCOPED_EVENT_IDENTITY_POLICIES.get(event)
    if not isinstance(policy, dict):
        return None
    payload_view = router._payload_view_for_event_identity(project_root, event, payload)
    if event == 'pm_mutates_route_after_review_block':
        scope = router._route_mutation_identity_scope(run_root, run_state, payload_view)
    elif event == router.PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT:
        scope = router._control_blocker_repair_decision_identity_scope(payload_view, run_state)
    elif event in router.CONTROL_BLOCKER_REPAIR_NON_SUCCESS_EVENTS or event == router.PM_PARENT_PROTOCOL_BLOCKER_EVENT:
        scope = router._control_blocker_repair_outcome_identity_scope(payload_view, run_state, event)
    elif event == router.GATE_DECISION_EVENT:
        scope = router._gate_decision_identity_scope(run_root, payload_view)
    elif event == 'pm_requests_startup_repair':
        scope = router._startup_repair_identity_scope(run_root, run_state, payload_view)
    elif event == 'pm_writes_route_draft':
        scope = router._route_draft_identity_scope(payload_view)
    elif event == 'pm_completes_current_node_from_reviewed_result':
        scope = router._current_node_completion_identity_scope(run_root, run_state, payload_view)
    elif event == router.PM_ROLE_WORK_REQUEST_EVENT:
        scope = router._pm_role_work_request_identity_scope(payload_view)
    elif event == router.ROLE_WORK_RESULT_RETURNED_EVENT:
        scope = router._role_work_result_identity_scope(payload_view)
    elif event == 'worker_current_node_result_returned':
        scope = router._current_node_result_identity_scope(payload_view)
    elif event == router.PM_ROLE_WORK_RESULT_DECISION_EVENT:
        scope = router._pm_role_work_result_decision_identity_scope(payload_view)
    else:
        return None
    key_fields = tuple((str(field) for field in policy.get('dedupe_fields', ())))
    key_parts = {field: str(scope.get(field) or '') for field in key_fields}
    dedupe_key = f'{event}:{router._stable_identity_hash(key_parts)}'
    retry_group_fields = tuple((str(field) for field in policy.get('retry_group_fields', ())))
    retry_group = f"{event}:{router._stable_identity_hash({field: str(scope.get(field) or '') for field in retry_group_fields})}"
    return {'schema_version': router.EVENT_IDEMPOTENCY_LEDGER_SCHEMA, 'event': event, 'family': policy.get('family'), 'dedupe_key': dedupe_key, 'scope': scope, 'dedupe_fields': list(key_fields), 'retry_group': retry_group, 'max_distinct_keys_per_retry_group': policy.get('max_distinct_keys_per_retry_group')}


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
