"""Coarse events repair owner helpers for the FlowPilot router.

The public compatibility names stay in `flowpilot_router`. This module owns a
cohesive behavior family and receives the router facade as an explicit runtime
dependency so shared state writers and public entrypoints remain compatible.
"""

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


def _bind_router(router: ModuleType) -> None:
    current = globals()
    local_names = current.get('_LOCAL_NAMES', set())
    for name, value in vars(router).items():
        if name.startswith('__') and name.endswith('__'):
            continue
        if name in local_names:
            continue
        current[name] = value

def _control_blocker_allows_resolution_event(router: ModuleType, record: dict[str, Any], event: str) -> bool:
    _bind_router(router)
    if record.get('handling_lane') in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES and event == PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT:
        return False
    raw_events = record.get('allowed_resolution_events')
    if isinstance(raw_events, list) and raw_events:
        allowed_events = {name for item in raw_events if (name := router._control_resolution_event_name(item))}
        return event in allowed_events
    if record.get('handling_lane') == 'control_plane_reissue':
        return event == record.get('originating_event')
    return event in EXTERNAL_EVENTS

def _control_resolution_event_name(router: ModuleType, value: Any) -> str | None:
    _bind_router(router)
    if isinstance(value, dict):
        for key in ('event', 'corrected_followup_event', 'event_name'):
            name = str(value.get(key) or '').strip()
            if name:
                return router._control_resolution_event_name(name)
        return None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text in EXTERNAL_EVENTS:
        return text
    parsed: Any = None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            parsed = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            return None
    return router._control_resolution_event_name(parsed)

def _resolve_delivered_control_blocker(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, resolved_by_event: str, from_already_recorded_event: bool=False) -> dict[str, Any] | None:
    _bind_router(router)
    active = run_state.get('active_control_blocker')
    if not isinstance(active, dict) or active.get('delivery_status') != 'delivered':
        return None
    record = dict(active)
    artifact_rel = str(active.get('blocker_artifact_path') or '')
    artifact_path: Path | None = None
    if artifact_rel:
        artifact_path = resolve_project_path(project_root, artifact_rel)
        if artifact_path.exists():
            record = read_json(artifact_path)
    if from_already_recorded_event:
        lane = record.get('handling_lane')
        pm_repair_recorded = lane in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES and record.get('pm_repair_decision_status') == 'recorded'
        if lane != 'control_plane_reissue' and (not pm_repair_recorded):
            return None
    if not router._control_blocker_allows_resolution_event(record, resolved_by_event):
        return None
    if artifact_path and artifact_path.exists():
        resolved_at = utc_now()
        record['resolution_status'] = 'accepted_followup_event_recorded'
        record['resolved_by_event'] = resolved_by_event
        record['resolved_at'] = resolved_at
        write_json(artifact_path, record)
    resolved = dict(active)
    resolved['resolution_status'] = 'accepted_followup_event_recorded'
    resolved['resolved_by_event'] = resolved_by_event
    resolved['resolved_at'] = record.get('resolved_at') or utc_now()
    run_state.setdefault('resolved_control_blockers', []).append(resolved)
    run_state['active_control_blocker'] = None
    run_state['latest_control_blocker_path'] = None
    append_history(run_state, 'router_resolved_control_blocker', {'blocker_id': resolved.get('blocker_id'), 'resolved_by_event': resolved_by_event})
    router._sync_control_plane_indexes(project_root, run_root, run_state)
    return resolved

def _repair_transactions_root(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'control_blocks' / 'repair_transactions'

def _repair_transaction_index_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return router._repair_transactions_root(run_root) / 'repair_transaction_index.json'

def _repair_transaction_path(router: ModuleType, run_root: Path, transaction_id: str) -> Path:
    _bind_router(router)
    return router._repair_transactions_root(run_root) / f'{transaction_id}.json'

def _repair_transaction_id(router: ModuleType, blocker_id: str) -> str:
    _bind_router(router)
    safe = ''.join((ch if ch.isalnum() or ch in {'-', '_'} else '-' for ch in blocker_id)).strip('-')
    return f"repair-tx-{safe or 'control-blocker'}"

def _control_blocker_repair_origin(router: ModuleType, active: dict[str, Any], *, rerun_target: str, requested_plan_kind: str, run_root: Path, run_state: dict[str, Any]) -> str:
    _bind_router(router)
    originating_event = str(active.get('originating_event') or '')
    if requested_plan_kind == 'packet_reissue' or rerun_target in MATERIAL_REPAIR_OUTCOME_EVENTS or originating_event in MATERIAL_REPAIR_OUTCOME_EVENTS or (originating_event in {'reviewer_blocks_material_scan_dispatch', 'reviewer_blocks_material_scan_dispatch_recheck'}):
        return 'material_dispatch'
    if rerun_target in PARENT_REPAIR_SAFE_EVENTS or originating_event in PARENT_REPAIR_SAFE_EVENTS or run_state.get('flags', {}).get('parent_backward_replay_blocked'):
        return 'parent_backward_replay'
    if rerun_target in LEAF_CURRENT_NODE_EVENT_CAPABILITY_EVENTS or originating_event in LEAF_CURRENT_NODE_EVENT_CAPABILITY_EVENTS:
        return 'current_node_result'
    try:
        if router._active_node_kind_for_event_capability(run_root) in {'parent', 'module'} and originating_event in {'pm_records_parent_segment_decision', 'pm_completes_parent_node_from_backward_replay'}:
            return 'parent_backward_replay'
    except (RouterError, OSError, ValueError, TypeError):
        pass
    return 'none'

def _repair_outcome_table(router: ModuleType, rerun_target: str, *, repair_origin: str='none') -> dict[str, dict[str, Any]]:
    _bind_router(router)
    if rerun_target in {'router_direct_material_scan_dispatch_recheck_passed', 'reviewer_allows_material_scan_dispatch'}:
        return {'success': {'event': 'router_direct_material_scan_dispatch_recheck_passed', 'terminal': 'complete'}, 'blocker': {'event': 'router_direct_material_scan_dispatch_recheck_blocked', 'terminal': 'blocked'}, 'protocol_blocker': {'event': 'router_protocol_blocker_material_scan_dispatch_recheck', 'terminal': 'blocked'}}
    if repair_origin == 'parent_backward_replay':
        if rerun_target not in PARENT_REPAIR_SAFE_EVENTS:
            raise RouterError('parent backward replay repair rerun_target must be a parent-safe event')
        if rerun_target in {'reviewer_blocks_parent_backward_replay', PM_PARENT_PROTOCOL_BLOCKER_EVENT}:
            raise RouterError('parent backward replay repair rerun_target must be a success-capable parent event')
        return {'success': {'event': rerun_target, 'terminal': 'complete'}, 'blocker': {'event': 'reviewer_blocks_parent_backward_replay', 'terminal': 'blocked'}, 'protocol_blocker': {'event': PM_PARENT_PROTOCOL_BLOCKER_EVENT, 'terminal': 'blocked'}}
    if rerun_target in CONTROL_BLOCKER_REPAIR_NON_SUCCESS_EVENTS or rerun_target == PM_PARENT_PROTOCOL_BLOCKER_EVENT:
        raise RouterError('control blocker repair rerun_target must be a success-capable follow-up event')
    return {'success': {'event': rerun_target, 'terminal': 'complete'}, 'blocker': {'event': PM_CONTROL_BLOCKER_FOLLOWUP_BLOCKER_EVENT, 'terminal': 'blocked'}, 'protocol_blocker': {'event': PM_CONTROL_BLOCKER_PROTOCOL_BLOCKER_EVENT, 'terminal': 'blocked'}}

def _validate_repair_outcome_table(router: ModuleType, outcome_table: dict[str, Any], *, context: str, run_root: Path, run_state: dict[str, Any], repair_origin: str) -> None:
    _bind_router(router)
    events_by_kind: dict[str, str] = {}
    for kind in ('success', 'blocker', 'protocol_blocker'):
        outcome = outcome_table.get(kind)
        if not isinstance(outcome, dict):
            raise RouterError(f'{context} requires {kind} outcome row')
        event = str(outcome.get('event') or '').strip()
        if not event:
            raise RouterError(f'{context} {kind} outcome row requires event')
        events_by_kind[kind] = event
    if len(set(events_by_kind.values())) != len(events_by_kind):
        raise RouterError(f'{context} must use distinct success, blocker, and protocol-blocker events')
    for kind, event in events_by_kind.items():
        router._validated_event_capability_names([event], context=f'{context} {kind} outcome', run_root=run_root, run_state=run_state, usage='repair_outcome', repair_origin=repair_origin, outcome_kind=kind, allow_pm_repair_event=False)

def _repair_outcome_events(router: ModuleType, outcome_table: dict[str, Any]) -> list[str]:
    _bind_router(router)
    events: list[str] = []
    for name in ('success', 'blocker', 'protocol_blocker'):
        outcome = outcome_table.get(name)
        if not isinstance(outcome, dict):
            continue
        event = str(outcome.get('event') or '').strip()
        if event and event not in events:
            events.append(event)
    return events

def _repair_packet_specs_from_decision(router: ModuleType, project_root: Path, run_root: Path, decision: dict[str, Any], *, rerun_target: str) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    _bind_router(router)
    transaction = decision.get('repair_transaction') if isinstance(decision.get('repair_transaction'), dict) else {}
    raw_packets = transaction.get('replacement_packets') or transaction.get('packets') or decision.get('replacement_packets') or decision.get('packets')
    if isinstance(raw_packets, list) and raw_packets:
        return (raw_packets, {'source': 'decision_inline', 'packet_count': len(raw_packets)})
    raw_path = transaction.get('replacement_packet_specs_path') or transaction.get('packet_reissue_spec_path') or decision.get('replacement_packet_specs_path') or decision.get('packet_reissue_spec_path')
    if not raw_path and rerun_target in {'router_direct_material_scan_dispatch_recheck_passed', 'reviewer_allows_material_scan_dispatch'}:
        default_path = run_root / 'material' / 'pm_material_scan_packet_specs_reissue.project_manager.json'
        if default_path.exists():
            raw_path = project_relative(project_root, default_path)
    if not raw_path:
        return ([], None)
    spec_path = resolve_project_path(project_root, str(raw_path))
    if not spec_path.exists():
        raise RouterError(f'repair transaction packet spec path is missing: {raw_path}')
    expected_hash = transaction.get('replacement_packet_specs_hash') or transaction.get('packet_reissue_spec_hash') or decision.get('replacement_packet_specs_hash') or decision.get('packet_reissue_spec_hash')
    if expected_hash and packet_runtime.sha256_file(spec_path) != str(expected_hash):
        raise RouterError('repair transaction packet spec hash mismatch')
    spec = read_json(spec_path)
    packets = spec.get('packets')
    if not isinstance(packets, list) or not packets:
        raise RouterError('repair transaction packet spec requires non-empty packets')
    return (packets, {'source': 'packet_spec_file', 'path': project_relative(project_root, spec_path), 'sha256': packet_runtime.sha256_file(spec_path), 'packet_count': len(packets)})

def _write_repair_transaction_index(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    _bind_router(router)
    root = router._repair_transactions_root(run_root)
    transactions: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None
    if root.exists():
        for path in sorted(root.glob('repair-tx-*.json')):
            record = read_json_if_exists(path)
            if record.get('schema_version') != REPAIR_TRANSACTION_SCHEMA:
                continue
            summary = {'transaction_id': record.get('transaction_id'), 'blocker_id': record.get('blocker_id'), 'status': record.get('status'), 'plan_kind': record.get('plan_kind'), 'packet_generation_id': record.get('packet_generation_id'), 'path': project_relative(project_root, path), 'outcome_table': record.get('outcome_table')}
            transactions.append(summary)
            if record.get('status') in {'opened', 'committed', 'awaiting_recheck'}:
                active = summary
    index = {'schema_version': REPAIR_TRANSACTION_INDEX_SCHEMA, 'run_id': run_state.get('run_id'), 'active_transaction': active, 'transactions': transactions, 'updated_at': utc_now()}
    write_json(router._repair_transaction_index_path(run_root), index)
    run_state['repair_transactions'] = transactions
    run_state['active_repair_transaction'] = active

def _commit_material_scan_repair_generation(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, transaction_id: str, packet_generation_id: str, packet_specs: list[dict[str, Any]]) -> dict[str, Any]:
    _bind_router(router)
    existing_index = read_json_if_exists(router._material_scan_index_path(run_root))
    superseded_packets = []
    for record in existing_index.get('packets', []) if isinstance(existing_index.get('packets'), list) else []:
        if isinstance(record, dict):
            superseded = dict(record)
            superseded['is_current_generation'] = False
            superseded['superseded_by_generation_id'] = packet_generation_id
            superseded_packets.append(superseded)
    records: list[dict[str, Any]] = []
    for index, spec in enumerate(packet_specs, start=1):
        if not isinstance(spec, dict):
            raise RouterError('each repair transaction packet spec must be an object')
        packet_id = str(spec.get('packet_id') or f'material-scan-repair-{index:03d}')
        to_role = str(spec.get('to_role') or 'worker_a')
        if to_role not in {'worker_a', 'worker_b'}:
            raise RouterError('material scan repair packet must target worker_a or worker_b')
        body_text = router._material_packet_body_text_from_spec(project_root, spec)
        envelope = packet_runtime.create_packet(project_root, run_id=str(run_state['run_id']), packet_id=packet_id, from_role='project_manager', to_role=to_role, node_id=str(spec.get('node_id') or 'material-intake'), body_text=body_text, is_current_node=False, packet_type='material_scan', metadata={'stage': 'material_scan', 'source': 'repair_transaction_commit', 'repair_transaction_id': transaction_id, 'packet_generation_id': packet_generation_id, 'replacement_for': spec.get('replacement_for'), **(spec.get('metadata') if isinstance(spec.get('metadata'), dict) else {})}, output_contract=spec.get('output_contract') if isinstance(spec.get('output_contract'), dict) else None)
        paths = packet_runtime.packet_paths(project_root, packet_id, str(run_state['run_id']))
        records.append({'packet_id': packet_id, 'to_role': to_role, 'packet_generation_id': packet_generation_id, 'repair_transaction_id': transaction_id, 'replacement_for': spec.get('replacement_for'), 'is_current_generation': True, 'packet_envelope_path': envelope['body_path'].replace('packet_body.md', 'packet_envelope.json'), 'result_envelope_path': project_relative(project_root, paths['result_envelope']), 'result_body_path': project_relative(project_root, paths['result_body']), 'result_write_target': {'result_envelope_path': project_relative(project_root, paths['result_envelope']), 'result_body_path': project_relative(project_root, paths['result_body'])}, 'output_contract_id': envelope.get('output_contract_id')})
    write_json(router._material_scan_index_path(run_root), {'schema_version': 'flowpilot.material_scan_packets.v2', 'run_id': run_state['run_id'], 'written_by_role': 'project_manager', 'controller_may_read_packet_body': False, 'router_direct_dispatch_required_before_worker': True, 'reviewer_dispatch_required_before_worker': False, 'current_generation_id': packet_generation_id, 'repair_transaction_id': transaction_id, 'packets': records, 'superseded_packets': superseded_packets, 'written_at': utc_now()})
    run_state['flags']['material_scan_packets_relayed'] = False
    run_state['flags']['worker_packets_delivered'] = False
    run_state['flags']['worker_scan_results_returned'] = False
    run_state['flags']['material_scan_results_relayed_to_reviewer'] = False
    run_state['flags']['material_scan_results_relayed_to_pm'] = False
    run_state['flags']['material_scan_result_disposition_recorded'] = False
    run_state['flags']['material_scan_results_absorbed_by_pm'] = False
    run_state['flags']['material_review_sufficient'] = False
    run_state['flags']['material_review_insufficient'] = False
    run_state['material_review'] = None
    return {'packet_generation_id': packet_generation_id, 'packet_count': len(records), 'packets': records, 'superseded_packet_count': len(superseded_packets), 'dispatch_index_path': project_relative(project_root, router._material_scan_index_path(run_root)), 'packet_ledger_path': project_relative(project_root, run_root / 'packet_ledger.json')}

def _active_repair_transaction_for_event(router: ModuleType, run_root: Path, event: str) -> tuple[Path, dict[str, Any]] | tuple[None, None]:
    _bind_router(router)
    root = router._repair_transactions_root(run_root)
    if not root.exists():
        return (None, None)
    for path in sorted(root.glob('repair-tx-*.json'), reverse=True):
        record = read_json_if_exists(path)
        if record.get('schema_version') != REPAIR_TRANSACTION_SCHEMA:
            continue
        if record.get('status') not in {'committed', 'awaiting_recheck', 'opened'}:
            continue
        if event in router._repair_outcome_events(record.get('outcome_table') if isinstance(record.get('outcome_table'), dict) else {}):
            return (path, record)
    return (None, None)

def _repair_transaction_outcome_kind(router: ModuleType, transaction: dict[str, Any], event: str) -> str | None:
    _bind_router(router)
    table = transaction.get('outcome_table')
    if not isinstance(table, dict):
        return None
    for kind in ('success', 'blocker', 'protocol_blocker'):
        outcome = table.get(kind)
        if isinstance(outcome, dict) and outcome.get('event') == event:
            return kind
    return None

def _clear_successful_repair_lane_state(router: ModuleType, run_state: dict[str, Any], transaction: dict[str, Any], *, event: str) -> None:
    _bind_router(router)
    rerun_target = str(transaction.get('rerun_target') or '')
    is_material_repair = event in MATERIAL_REPAIR_OUTCOME_EVENTS or rerun_target in MATERIAL_REPAIR_OUTCOME_EVENTS
    flags = run_state.get('flags')
    if isinstance(flags, dict) and is_material_repair:
        for flag in MATERIAL_REPAIR_RECHECK_FLAGS:
            flags[flag] = False
        if event in {'router_direct_material_scan_dispatch_recheck_passed', 'reviewer_allows_material_scan_dispatch'}:
            flags['material_scan_dispatch_blocked'] = False
    if is_material_repair:
        run_state['material_dispatch_block'] = None
    pending = run_state.get('pending_action')
    if isinstance(pending, dict):
        outcome_events = set(router._repair_outcome_events(transaction.get('outcome_table') if isinstance(transaction.get('outcome_table'), dict) else {}))
        pending_events = set((str(item) for item in pending.get('allowed_external_events', []) if isinstance(item, str)))
        if pending.get('repair_transaction_id') == transaction.get('transaction_id') or (pending_events and pending_events.issubset(outcome_events)):
            run_state['pending_action'] = None

def _finalize_repair_transaction_outcome(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, event: str, payload: dict[str, Any] | None) -> dict[str, Any] | None:
    _bind_router(router)
    tx_path, transaction = router._active_repair_transaction_for_event(run_root, event)
    if tx_path is None or transaction is None:
        return None
    outcome_kind = router._repair_transaction_outcome_kind(transaction, event)
    if not outcome_kind:
        return None
    now = utc_now()
    transaction['reviewer_recheck'] = {'outcome': outcome_kind, 'event': event, 'payload_envelope_public_view': router._control_payload_public_view(payload), 'recorded_at': now}
    if outcome_kind == 'success':
        transaction['status'] = 'complete'
        transaction['completed_at'] = now
        write_json(tx_path, transaction)
        router._clear_successful_repair_lane_state(run_state, transaction, event=event)
        router._write_repair_transaction_index(project_root, run_root, run_state)
        return {'transaction_id': transaction.get('transaction_id'), 'outcome': outcome_kind, 'status': 'complete'}
    transaction['status'] = 'blocked'
    transaction['blocked_at'] = now
    transaction['followup_blocker_required'] = True
    write_json(tx_path, transaction)
    blocker_id = str(transaction.get('blocker_id') or '')
    active = run_state.get('active_control_blocker')
    artifact_rel = str(active.get('blocker_artifact_path') or '') if isinstance(active, dict) else ''
    if artifact_rel:
        artifact_path = resolve_project_path(project_root, artifact_rel)
        if artifact_path.exists():
            blocker_record = read_json(artifact_path)
            if blocker_record.get('blocker_id') == blocker_id:
                blocker_record['resolution_status'] = f'repair_transaction_{outcome_kind}'
                blocker_record['resolved_by_event'] = event
                blocker_record['resolved_at'] = now
                blocker_record['repair_transaction_id'] = transaction.get('transaction_id')
                write_json(artifact_path, blocker_record)
    followup = router._write_control_blocker(project_root, run_root, run_state, source='repair_transaction_recheck', error_message=f"repair transaction {transaction.get('transaction_id')} ended with reviewer {outcome_kind}; PM repair or routing decision is required before retrying dispatch.", event=event, payload=payload)
    transaction['followup_blocker_id'] = followup.get('blocker_id')
    transaction['followup_blocker_path'] = followup.get('blocker_artifact_path')
    write_json(tx_path, transaction)
    router._write_repair_transaction_index(project_root, run_root, run_state)
    return {'transaction_id': transaction.get('transaction_id'), 'outcome': outcome_kind, 'status': 'blocked', 'followup_blocker_id': followup.get('blocker_id')}

__all__ = (
    '_control_blocker_allows_resolution_event',
    '_control_resolution_event_name',
    '_resolve_delivered_control_blocker',
    '_repair_transactions_root',
    '_repair_transaction_index_path',
    '_repair_transaction_path',
    '_repair_transaction_id',
    '_control_blocker_repair_origin',
    '_repair_outcome_table',
    '_validate_repair_outcome_table',
    '_repair_outcome_events',
    '_repair_packet_specs_from_decision',
    '_write_repair_transaction_index',
    '_commit_material_scan_repair_generation',
    '_active_repair_transaction_for_event',
    '_repair_transaction_outcome_kind',
    '_clear_successful_repair_lane_state',
    '_finalize_repair_transaction_outcome',
)

_LOCAL_NAMES = set(globals())
