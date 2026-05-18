"""Scoped external event identity builders."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import ModuleType
from typing import Any


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


__all__ = (
    '_stable_identity_hash',
    '_event_identity_ledger',
    '_payload_view_for_event_identity',
    '_payload_body_hash',
    '_frontier_for_event_identity',
    '_active_control_blocker_for_identity',
    '_route_mutation_identity_scope',
    '_control_blocker_repair_decision_identity_scope',
    '_control_blocker_repair_outcome_identity_scope',
    '_gate_decision_identity_scope',
    '_startup_repair_identity_scope',
    '_route_draft_identity_scope',
    '_current_node_completion_identity_scope',
    '_pm_role_work_request_identity_scope',
    '_role_work_result_identity_scope',
    '_current_node_result_identity_scope',
    '_pm_role_work_result_decision_identity_scope',
    '_scoped_event_identity',
)
