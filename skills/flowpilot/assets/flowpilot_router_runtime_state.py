"""Coarse runtime state owner helpers for the FlowPilot router.

The public router names stay in `flowpilot_router`. This module owns a
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
from flowpilot_control_plane_contracts import control_plane_pending_wait_same_identity
from flowpilot_router_errors import RouterError, RouterLedgerCorruptionError, RouterLedgerWriteInProgress
import flowpilot_router_runtime_state_persistence as runtime_state_persistence

_DEFAULT_SENTINEL = object()
_BOUND_ROUTER: ModuleType | None = None
_RUN_STATE_LOAD_META_HASH = runtime_state_persistence._RUN_STATE_LOAD_META_HASH
_RUN_STATE_LOAD_META_FLAGS = runtime_state_persistence._RUN_STATE_LOAD_META_FLAGS
_RUN_STATE_LOAD_META_PENDING = runtime_state_persistence._RUN_STATE_LOAD_META_PENDING


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get('_LOCAL_NAMES', set())
    for name, value in vars(router).items():
        if name.startswith('__') and name.endswith('__'):
            continue
        if name in local_names:
            continue
        current[name] = value
    runtime_state_persistence._bind_router(router)

def _json_clone(value: Any) -> Any:
    return runtime_state_persistence._json_clone(value)

def _public_run_state_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    return runtime_state_persistence._public_run_state_snapshot(state)

def _run_state_snapshot_hash(state: dict[str, Any]) -> str:
    return runtime_state_persistence._run_state_snapshot_hash(state)

def _attach_run_state_load_metadata(state: dict[str, Any]) -> dict[str, Any]:
    return runtime_state_persistence._attach_run_state_load_metadata(state)

def _merge_append_only_run_state_list(existing: list[Any], current: list[Any]) -> list[Any]:
    return runtime_state_persistence._merge_append_only_run_state_list(existing, current)

def _same_pending_wait_identity(first: dict[str, Any], second: dict[str, Any]) -> bool:
    return runtime_state_persistence._same_pending_wait_identity(first, second)

def _same_optional_pending_wait_identity(first: Any, second: Any) -> bool:
    return runtime_state_persistence._same_optional_pending_wait_identity(first, second)

def _merge_pending_wait_reminder_state(existing: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    return runtime_state_persistence._merge_pending_wait_reminder_state(existing, current)

def _merge_stale_pending_action_projection(existing: Any, current: Any, loaded: Any) -> dict[str, Any] | None:
    return runtime_state_persistence._merge_stale_pending_action_projection(existing, current, loaded)

def _merge_stale_run_state_save(existing: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    return runtime_state_persistence._merge_stale_run_state_save(existing, current)

def new_bootstrap_state(router: ModuleType, run_id: str | None=None, run_root_rel: str | None=None) -> dict[str, Any]:
    _bind_router(router)
    return {'schema_version': BOOTSTRAP_STATE_SCHEMA, 'status': 'new', 'bootstrap_scope': 'run_scoped' if run_id and run_root_rel else 'pre_run', 'router_loaded': False, 'startup_state': 'none', 'bootloader_actions': 0, 'router_action_requests': 0, 'pending_action': None, 'startup_answers': None, 'user_request': None, 'run_id': run_id, 'run_root': run_root_rel, 'flags': {action['flag']: False for action in BOOT_ACTIONS}, 'history': []}

def _create_startup_bootstrap_state(router: ModuleType, project_root: Path) -> dict[str, Any]:
    _bind_router(router)
    base_run_id = router._create_run_id()
    for suffix in range(100):
        run_id = base_run_id if suffix == 0 else f'{base_run_id}-{suffix:02d}'
        run_root = project_root / '.flowpilot' / 'runs' / run_id
        if not run_root.exists():
            break
    else:
        raise RouterError(f'could not allocate unique startup run id from {base_run_id}')
    run_root_rel = project_relative(project_root, run_root)
    state = router.new_bootstrap_state(run_id=run_id, run_root_rel=run_root_rel)
    write_json(project_root / '.flowpilot' / 'current.json', {'schema_version': 'flowpilot.current.v1', 'run_id': run_id, 'run_root': run_root_rel, 'status': 'startup_bootstrap', 'startup_bootstrap_path': project_relative(project_root, run_bootstrap_state_path(run_root)), 'updated_at': utc_now()})
    return state

def _load_existing_bootstrap_state(router: ModuleType, project_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    current = read_json_if_exists(project_root / '.flowpilot' / 'current.json')
    raw = current.get('startup_bootstrap_path')
    candidate: Path | None = project_root / str(raw) if raw else None
    if candidate is None:
        raw_root = current.get('run_root')
        if raw_root:
            candidate = run_bootstrap_state_path(project_root / str(raw_root))
    if candidate is None or not candidate.exists():
        return None
    state = read_json(candidate)
    if state.get('schema_version') != BOOTSTRAP_STATE_SCHEMA:
        return None
    return state

def load_bootstrap_state(router: ModuleType, project_root: Path, *, create_if_missing: bool=False, new_invocation: bool=False) -> dict[str, Any]:
    _bind_router(router)
    if new_invocation:
        return router._create_startup_bootstrap_state(project_root)
    state = router._load_existing_bootstrap_state(project_root)
    if state is None:
        if not create_if_missing:
            return router.new_bootstrap_state()
        state = router._create_startup_bootstrap_state(project_root)
    path = bootstrap_state_path(project_root, state)
    if not path.exists():
        return state
    flags = state.setdefault('flags', {})
    for action in BOOT_ACTIONS:
        flags.setdefault(action['flag'], False)
    state.setdefault('history', [])
    state.setdefault('pending_action', None)
    state.setdefault('router_action_requests', 0)
    state.setdefault('bootloader_actions', 0)
    return state

def save_bootstrap_state(router: ModuleType, project_root: Path, state: dict[str, Any]) -> None:
    _bind_router(router)
    write_json(bootstrap_state_path(project_root, state), state)

def active_run_root(router: ModuleType, project_root: Path, state: dict[str, Any] | None=None) -> Path | None:
    _bind_router(router)
    if state and state.get('run_root'):
        return project_root / str(state['run_root'])
    current = read_json_if_exists(project_root / '.flowpilot' / 'current.json')
    raw = current.get('run_root')
    if raw:
        return project_root / str(raw)
    run_id = current.get('run_id')
    if run_id:
        return project_root / '.flowpilot' / 'runs' / str(run_id)
    return None

def run_state_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'router_state.json'

def new_run_state(router: ModuleType, run_id: str, run_root_rel: str, *, controller_core_loaded: bool=False) -> dict[str, Any]:
    _bind_router(router)
    return {'schema_version': RUN_STATE_SCHEMA, 'run_id': run_id, 'run_root': run_root_rel, 'status': 'controller_ready' if controller_core_loaded else 'startup_bootstrap', 'phase': 'startup_intake', 'holder': 'controller' if controller_core_loaded else 'bootloader', 'pending_action': None, 'daemon_mode_enabled': False, 'router_daemon_status_path': None, 'controller_action_ledger_path': None, 'router_ownership_ledger_path': None, 'manifest_check_requests': 0, 'manifest_checks': 0, 'ledger_check_requests': 0, 'ledger_checks': 0, 'prompt_deliveries': 0, 'mail_deliveries': 0, 'control_blockers': [], 'resolved_control_blockers': [], 'blocker_repair_attempts': {}, 'blocker_repair_policy_snapshot': None, 'protocol_blockers': [], 'gate_decisions': [], 'active_control_blocker': None, 'latest_control_blocker_path': None, 'delivered_cards': [], 'delivered_mail': [], 'events': [], 'quarantined_role_reports': [], 'flags': {'controller_core_loaded': controller_core_loaded, **RUNTIME_FLAG_DEFAULTS, **{entry['flag']: False for entry in SYSTEM_CARD_SEQUENCE}, **{entry['flag']: False for entry in MAIL_SEQUENCE}, **{entry['flag']: False for entry in EXTERNAL_EVENTS.values()}}, 'history': []}

def load_run_state(router: ModuleType, project_root: Path, bootstrap_state: dict[str, Any] | None=None) -> tuple[dict[str, Any], Path] | tuple[None, None]:
    return runtime_state_persistence.load_run_state(router, project_root, bootstrap_state)

def load_run_state_from_run_root(router: ModuleType, project_root: Path, run_root: Path) -> tuple[dict[str, Any], Path] | tuple[None, Path]:
    return runtime_state_persistence.load_run_state_from_run_root(router, project_root, run_root)

def save_run_state(router: ModuleType, run_root: Path, state: dict[str, Any]) -> None:
    runtime_state_persistence.save_run_state(router, run_root, state)

def _create_run_id(router: ModuleType) -> str:
    _bind_router(router)
    return f"run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

def _create_empty_packet_ledger(router: ModuleType, project_root: Path, run_id: str, run_root: Path) -> dict[str, Any]:
    _bind_router(router)
    return {'schema_version': PACKET_LEDGER_SCHEMA, 'run_id': run_id, 'run_root': project_relative(project_root, run_root), 'created_at': utc_now(), 'updated_at': utc_now(), 'controller_boundary': {'controller_only': True, 'all_role_mail_routes_through_controller': True, 'controller_may_read_packet_body': False, 'controller_may_read_result_body': False, 'controller_may_create_project_evidence': False, 'router_direct_dispatch_required_before_worker': True, 'reviewer_dispatch_required_before_worker': False}, 'mail': [], 'packets': []}

def _active_packet_ledger_record(router: ModuleType, packet_ledger: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    active_packet_id = packet_ledger.get('active_packet_id')
    packets = packet_ledger.get('packets') if isinstance(packet_ledger.get('packets'), list) else []
    if active_packet_id:
        for record in reversed(packets):
            if isinstance(record, dict) and record.get('packet_id') == active_packet_id:
                return record
    for record in reversed(packets):
        if isinstance(record, dict):
            return record
    return None

def _packet_ledger_record_by_id(router: ModuleType, run_root: Path, packet_id: str) -> dict[str, Any] | None:
    _bind_router(router)
    packet_ledger = read_json_if_exists(run_root / 'packet_ledger.json') or {}
    packets = packet_ledger.get('packets') if isinstance(packet_ledger.get('packets'), list) else []
    for record in reversed(packets):
        if isinstance(record, dict) and str(record.get('packet_id') or '') == str(packet_id):
            return record
    return None

def _derive_resume_next_recipient_from_packet_ledger(router: ModuleType, run_root: Path) -> dict[str, Any]:
    _bind_router(router)
    packet_ledger = read_json_if_exists(run_root / 'packet_ledger.json') or {}
    record = router._active_packet_ledger_record(packet_ledger)
    active_packet_id = packet_ledger.get('active_packet_id')
    status = str(packet_ledger.get('active_packet_status') or '')
    holder = str(packet_ledger.get('active_packet_holder') or '')
    packet_envelope = record.get('packet_envelope') if isinstance(record, dict) and isinstance(record.get('packet_envelope'), dict) else {}
    result_envelope = record.get('result_envelope') if isinstance(record, dict) and isinstance(record.get('result_envelope'), dict) else {}
    assigned_worker = str(record.get('assigned_worker_role') or packet_envelope.get('to_role') or '') if isinstance(record, dict) else ''
    result_recipient = str(result_envelope.get('next_recipient') or '') if result_envelope else ''
    controller_next_action = 'resume_without_active_packet_then_request_pm_decision'
    next_recipient = 'project_manager'
    reason = 'No active packet is recorded, so resume must continue through PM resume decision after role rehydration.'
    if active_packet_id:
        if status == 'router-held-startup-material':
            next_recipient = assigned_worker or 'project_manager'
            controller_next_action = 'wait_for_controller_deliver_mail_after_pm_activation'
            reason = 'Packet ledger says startup user_intake is held by Router until PM approves startup activation, then Controller must relay it.'
        elif status == 'packet-with-controller':
            next_recipient = assigned_worker or 'unknown'
            controller_next_action = 'relay_packet_envelope_to_recorded_recipient'
            reason = 'Packet ledger says the packet is with Controller and records the worker recipient.'
        elif status in {'envelope-relayed', 'packet-body-opened-by-recipient'}:
            next_recipient = holder or assigned_worker or 'unknown'
            controller_next_action = 'wait_for_recorded_packet_holder_result'
            reason = "Packet ledger says the packet is already with a role; Controller waits for that role's envelope-only return."
        elif status in {'worker-result-needs-review', 'result-envelope-returned'}:
            next_recipient = 'project_manager'
            controller_next_action = 'relay_result_envelope_to_project_manager_for_disposition'
            reason = 'Packet ledger says a result envelope is with Controller; under PM-first package absorption, Controller must relay it to PM for disposition before any reviewer gate.'
        elif status == 'router-next-action-ready-for-controller':
            notice = record.get('router_next_action_notice') if isinstance(record, dict) and isinstance(record.get('router_next_action_notice'), dict) else {}
            next_recipient = str(notice.get('next_recipient') or result_recipient or 'project_manager')
            controller_next_action = str(notice.get('next_action') or 'deliver_result_to_recorded_next_recipient')
            reason = 'Router accepted active-holder result mechanics and wrote a Controller-visible next-action notice.'
        elif status in {'result-envelope-relayed', 'result-body-opened-by-recipient'}:
            next_recipient = holder or result_recipient or 'project_manager'
            controller_next_action = 'wait_for_pm_result_disposition_or_formal_gate_release'
            reason = 'Packet ledger says the result is already with its holder; PM disposition is required before any reviewer gate.'
        elif status == 'contaminated-returned-to-sender':
            next_recipient = holder or str(record.get('from_role') or 'project_manager') if isinstance(record, dict) else 'project_manager'
            controller_next_action = 'wait_for_sender_reissue_or_pm_repair_decision'
            reason = 'Packet ledger says the envelope was returned to sender because the control boundary was violated.'
        elif status == 'superseded-by-replacement':
            next_recipient = 'project_manager'
            controller_next_action = 'wait_for_replacement_packet_or_pm_route_repair'
            reason = 'Packet ledger says this packet was superseded, so PM owns the replacement or route repair decision.'
        else:
            next_recipient = holder or assigned_worker or result_recipient or 'project_manager'
            controller_next_action = 'wait_for_ledger_recorded_holder_or_pm_resume_decision'
            reason = 'Packet ledger has an active packet with a non-standard status; Controller must not infer from chat.'
    return {'schema_version': 'flowpilot.resume_next_recipient.v1', 'source': 'packet_ledger', 'active_packet_id': active_packet_id, 'active_packet_status': status or None, 'active_packet_holder': holder or None, 'controller_next_action': controller_next_action, 'next_recipient_role': next_recipient, 'controller_has_explicit_next_from_ledger': next_recipient != 'unknown', 'controller_may_infer_next_from_chat_history': False, 'sealed_body_reads_allowed': False, 'reason': reason}

def _create_empty_execution_frontier(router: ModuleType, run_id: str) -> dict[str, Any]:
    _bind_router(router)
    return {'schema_version': 'flowpilot.execution_frontier.v1', 'run_id': run_id, 'status': 'startup_intake', 'active_route_id': None, 'active_node_id': None, 'updated_at': utc_now(), 'source': 'router_bootstrap'}

def _set_pre_route_frontier_phase(router: ModuleType, run_root: Path, run_id: str, phase: str) -> None:
    _bind_router(router)
    frontier = read_json_if_exists(run_root / 'execution_frontier.json') or router._create_empty_execution_frontier(run_id)
    if frontier.get('active_route_id') or frontier.get('active_node_id'):
        return
    frontier['status'] = phase
    frontier['phase'] = phase
    frontier['updated_at'] = utc_now()
    frontier['source'] = 'flowpilot_router'
    write_json(run_root / 'execution_frontier.json', frontier)

def _create_empty_role_memory(router: ModuleType, run_id: str, role: str) -> dict[str, Any]:
    _bind_router(router)
    return {'schema_version': 'flowpilot.role_memory.v1', 'run_id': run_id, 'role_key': role, 'status': 'slot_created_no_work_yet', 'summary': '', 'controller_decision_authority': False, 'updated_at': utc_now()}

def _role_memory_event_role(router: ModuleType, event: str, payload: dict[str, Any]) -> str | None:
    _bind_router(router)
    for key in ('completed_by_role', 'reviewed_by_role', 'decided_by_role', 'recorded_by_role', 'requested_by_role', 'written_by_role', 'from_role'):
        value = str(payload.get(key) or '').strip()
        if value in RUNTIME_ROLE_KEYS:
            return value
    if event.startswith('pm_') or event.startswith('project_manager_'):
        return 'project_manager'
    if event.startswith('reviewer_') or event.startswith('current_node_reviewer_'):
        return 'human_like_reviewer'
    if event.startswith('flowguard_operator_'):
        return 'flowguard_operator'
    if event.startswith('worker_'):
        return 'worker'
    return None

def _append_role_memory_delta(router: ModuleType, run_root: Path, run_state: dict[str, Any], *, event: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    role = router._role_memory_event_role(event, payload)
    if role not in RUNTIME_ROLE_KEYS:
        return None
    memory_path = router._role_memory_path(run_root, role)
    memory = read_json_if_exists(memory_path) or router._create_empty_role_memory(str(run_state['run_id']), role)
    artifact_refs = {key: value for key, value in payload.items() if isinstance(key, str) and isinstance(value, str) and (key.endswith('_path') or key.endswith('_hash') or key in {'packet_id', 'request_id', 'defect_or_blocker_id', 'decision'})}
    delta = {'event': event, 'recorded_at': utc_now(), 'artifact_refs': artifact_refs, 'authority': 'memory_index_only', 'controller_decision_authority': False, 'sealed_body_stored': False}
    deltas = memory.get('recent_deltas') if isinstance(memory.get('recent_deltas'), list) else []
    deltas.append(delta)
    memory['recent_deltas'] = deltas[-16:]
    memory['status'] = 'available'
    memory['summary'] = f'Last observed event: {event}'
    memory['updated_at'] = delta['recorded_at']
    memory['controller_decision_authority'] = False
    memory['role_memory_used_for_completion_authority'] = False
    write_json(memory_path, memory)
    return {'role': role, 'event': event, 'delta_count': len(memory['recent_deltas'])}

def _startup_answers_from_run(router: ModuleType, run_root: Path) -> dict[str, Any]:
    _bind_router(router)
    payload = read_json_if_exists(run_root / 'startup_answers.json')
    answers = payload.get('answers')
    if not isinstance(answers, dict):
        return {}
    return dict(answers)

def _continuation_binding_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'continuation' / 'continuation_binding.json'

def _continuation_quarantine_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'continuation' / 'quarantine.json'

def _build_continuation_quarantine_record(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, created_at: str) -> dict[str, Any]:
    _bind_router(router)
    record = flowpilot_runtime_closure.continuation_quarantine_record(run_id=str(run_state.get('run_id') or ''), run_root=project_relative(project_root, run_root), current_pointer=read_json_if_exists(project_root / '.flowpilot' / 'current.json') or {}, run_index=read_json_if_exists(project_root / '.flowpilot' / 'index.json') or {}, created_at=created_at)
    issues = flowpilot_runtime_closure.validate_continuation_quarantine_record(record)
    if issues:
        raise RouterError(f'continuation quarantine invariant failed: {issues}')
    record['path'] = project_relative(project_root, router._continuation_quarantine_path(run_root))
    return record

def _write_continuation_quarantine(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], record: dict[str, Any] | None=None) -> dict[str, Any]:
    _bind_router(router)
    quarantine = record or router._build_continuation_quarantine_record(project_root, run_root, run_state, created_at=utc_now())
    path = router._continuation_quarantine_path(run_root)
    write_json(path, quarantine)
    run_state['continuation_quarantine'] = {'schema_version': CONTINUATION_QUARANTINE_SCHEMA, 'path': project_relative(project_root, path), 'prior_run_files_are_evidence_by_default': False, 'old_agent_ids_are_current_authority': False, 'updated_at': quarantine.get('created_at')}
    return quarantine


_LOCAL_NAMES = set(globals())
