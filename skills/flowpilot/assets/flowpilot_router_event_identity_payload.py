"""External event payload and envelope helpers."""

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
    if ',' in expected_role and from_role in {part.strip() for part in expected_role.split(',') if part.strip()}:
        return True
    return False


def _pending_event_payload_contract(router: ModuleType, run_state: dict[str, Any], event: str) -> dict[str, Any]:
    pending_action = run_state.get('pending_action')
    if not isinstance(pending_action, dict) or pending_action.get('action_type') != 'await_role_decision':
        return {}
    allowed = pending_action.get('allowed_external_events')
    if not isinstance(allowed, list) or event not in allowed:
        return {}
    contract = pending_action.get('payload_contract')
    return contract if isinstance(contract, dict) else {}


def _validate_expected_role_output_envelope(router: ModuleType, project_root: Path, run_state: dict[str, Any], *, event: str, envelope: dict[str, Any]) -> None:
    payload_contract = _pending_event_payload_contract(router, run_state, event)
    expected_output_type = str(payload_contract.get('expected_output_type') or '').strip()
    expected_contract_id = str(payload_contract.get('expected_output_contract_id') or '').strip()
    requires_role_output = (
        payload_contract.get('required_object') == 'role_output_body'
        or payload_contract.get('expected_return_envelope') == 'role_output_envelope'
        or bool(expected_output_type)
        or bool(expected_contract_id)
    )
    if not requires_role_output:
        return
    if envelope.get('schema_version') != router.ROLE_OUTPUT_ENVELOPE_SCHEMA:
        raise router.RouterError('this router wait requires a role-output runtime envelope, not a hand-written event envelope')
    if envelope.get('router_submission_schema') != router.role_output_runtime.ROLE_OUTPUT_DIRECT_ROUTER_SUBMISSION_SCHEMA:
        raise router.RouterError('role-output envelope is missing the direct router submission schema')
    if envelope.get('role_output_runtime_validated') is not True:
        raise router.RouterError('role-output envelope must be generated and validated by role-output runtime')
    if expected_output_type and envelope.get('output_type') != expected_output_type:
        raise router.RouterError(f"role-output envelope output_type mismatch: expected {expected_output_type}, got {envelope.get('output_type')!r}")
    if expected_contract_id and envelope.get('output_contract_id') != expected_contract_id:
        raise router.RouterError(f"role-output envelope output_contract_id mismatch: expected {expected_contract_id}, got {envelope.get('output_contract_id')!r}")
    body_ref = envelope.get('body_ref')
    receipt_ref = envelope.get('runtime_receipt_ref')
    if not (isinstance(body_ref, dict) and body_ref.get('path') and body_ref.get('hash')):
        raise router.RouterError('role-output envelope requires body_ref.path/body_ref.hash')
    if not (isinstance(receipt_ref, dict) and receipt_ref.get('path') and receipt_ref.get('hash')):
        raise router.RouterError('role-output envelope requires runtime_receipt_ref.path/runtime_receipt_ref.hash')
    try:
        receipt = router.role_output_runtime.validate_envelope_runtime_receipt(project_root, envelope)
    except router.role_output_runtime.RoleOutputRuntimeError as exc:
        raise router.RouterError(str(exc)) from exc
    if expected_output_type and receipt.get('output_type') != expected_output_type:
        raise router.RouterError(f"role-output runtime receipt output_type mismatch: expected {expected_output_type}")
    if expected_contract_id and receipt.get('output_contract_id') != expected_contract_id:
        raise router.RouterError(f"role-output runtime receipt output_contract_id mismatch: expected {expected_contract_id}")


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
    _validate_expected_role_output_envelope(router, project_root, run_state, event=event, envelope=envelope)
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


__all__ = (
    '_load_file_backed_role_payload',
    '_load_file_backed_role_payload_if_present',
    '_record_event_envelope_ref_from_payload',
    '_looks_like_record_event_envelope',
    '_payload_requires_record_event_envelope_validation',
    '_currently_allowed_external_events',
    '_record_event_expected_role',
    '_record_event_from_role_matches',
    '_pending_event_payload_contract',
    '_validate_expected_role_output_envelope',
    '_validate_record_event_envelope',
    '_load_record_event_envelope_ref',
    '_normalize_record_event_payload',
)
