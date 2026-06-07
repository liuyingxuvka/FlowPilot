"""startup bootloader action application helpers for ``flowpilot_router_startup_bootloader``.

This child module is imported by the public facade and keeps
router binding behavior explicit for the startup StructureMesh split.
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
from flowpilot_router_protocol_catalog import *

_DEFAULT_SENTINEL = object()
_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router skeleton is not bound")
    return _BOUND_ROUTER


OWNER_MODULE = 'flowpilot_router_startup_bootloader'

def _finish_bootloader_action(router: ModuleType, project_root: Path, state: dict[str, Any], scheduled_action: dict[str, Any], *, flag: str, label: str, action_type: str, result_extra: dict[str, Any]) -> None:
    _bind_router(router)
    router._set_boot_flag(project_root, state, flag, label, {'action_type': action_type})
    startup_daemon_receipt_payload = result_extra.pop('_startup_daemon_receipt_payload', None)
    completion = router._complete_startup_daemon_bootloader_row(project_root, state, scheduled_action, applied_action_type=action_type, receipt_payload=startup_daemon_receipt_payload if isinstance(startup_daemon_receipt_payload, dict) else None)
    if completion is not None:
        result_extra['startup_daemon_row_completion'] = {'controller_action_id': completion.get('controller_action_id'), 'router_scheduler_row_id': completion.get('router_scheduler_row_id')}
    if router._startup_daemon_controls_bootstrap(state):
        run_state, run_root = _ensure_startup_run_state(project_root, state)
        schedule = router._startup_daemon_schedule_bootloader_action(project_root, run_root, run_state, source='bootloader_apply_catchup')
        if schedule.get('scheduled'):
            next_action = schedule.get('action') if isinstance(schedule.get('action'), dict) else {}
            result_extra['startup_daemon_next_action'] = {'action_type': next_action.get('action_type'), 'controller_action_id': schedule.get('controller_action_id'), 'router_scheduler_row_id': schedule.get('router_scheduler_row_id'), 'existing': bool(schedule.get('existing'))}

def apply_bootloader_action(router: ModuleType, project_root: Path, action_type: str, payload: dict[str, Any] | None=None) -> dict[str, Any]:
    _bind_router(router)
    state = router.load_bootstrap_state(project_root, create_if_missing=False)
    if action_type == 'load_router':
        router._set_boot_flag(project_root, state, 'router_loaded', 'bootloader_router_loaded')
        return {'ok': True, 'applied': action_type}
    action_meta = next((item for item in BOOT_ACTIONS if item['action_type'] == action_type), None)
    if action_meta is None:
        raise RouterError(f'unknown bootloader action: {action_type}')
    pending = router._ensure_pending(state, action_type)
    payload = payload or {}
    result_extra: dict[str, Any] = {}
    flag = str(action_meta['flag'])
    if action_type == 'open_startup_intake_ui':
        result_extra.update(router._apply_startup_intake_result_to_bootstrap(project_root, state, payload))
    elif action_type == 'emit_startup_banner':
        banner = router._startup_banner_display()
        confirmation = router._display_confirmation_for_action(payload, pending)
        banner['dialog_display_confirmation'] = confirmation
        state['startup_banner_path'] = banner['display_path']
        state['startup_banner_display'] = banner
        state['startup_banner_dialog_display_confirmation'] = confirmation
        result_extra.update(banner)
    elif action_type == 'create_run_shell':
        run_id = str(payload.get('run_id') or state.get('run_id') or router._create_run_id())
        run_root = project_root / '.flowpilot' / 'runs' / run_id
        run_root.mkdir(parents=True, exist_ok=True)
        state['run_id'] = run_id
        state['run_root'] = project_relative(project_root, run_root)
        write_json(run_root / 'run.json', {'schema_version': 'flowpilot.run.v1', 'run_id': run_id, 'created_at': utc_now(), 'startup_model': 'prompt_isolated_router'})
    elif action_type == 'write_current_pointer':
        if not state.get('run_id') or not state.get('run_root'):
            raise RouterError('cannot write current pointer before run shell exists')
        write_json(project_root / '.flowpilot' / 'current.json', {'schema_version': 'flowpilot.current.v1', 'run_id': state['run_id'], 'run_root': state['run_root'], 'startup_bootstrap_path': project_relative(project_root, bootstrap_state_path(project_root, state)), 'status': 'running', 'updated_at': utc_now()})
    elif action_type == 'update_run_index':
        if not state.get('run_id') or not state.get('run_root'):
            raise RouterError('cannot update index before run shell exists')
        index_path = project_root / '.flowpilot' / 'index.json'
        index = read_json_if_exists(index_path) or {'schema_version': 'flowpilot.index.v1', 'runs': []}
        runs = index.setdefault('runs', [])
        if not any((isinstance(item, dict) and item.get('run_id') == state['run_id'] for item in runs)):
            runs.append({'run_id': state['run_id'], 'run_root': state['run_root'], 'created_at': utc_now(), 'status': 'running'})
        index['current_run_id'] = state['run_id']
        index['updated_at'] = utc_now()
        write_json(index_path, index)
    elif action_type == 'copy_runtime_kit':
        run_root = project_root / str(state['run_root'])
        _copy_runtime_kit_into_run_root(run_root)
    elif action_type == 'fill_runtime_placeholders':
        run_root = project_root / str(state['run_root'])
        write_json(run_root / 'startup_answers.json', {'schema_version': 'flowpilot.startup_answers.v1', 'run_id': state['run_id'], 'answers': state.get('startup_answers') or {}, 'recorded_at': utc_now()})
        snapshot = router._write_flowguard_capability_snapshot(project_root, run_root, state)
        result_extra['flowguard_capability_snapshot_path'] = snapshot['path']
        result_extra['flowguard_capability_snapshot_skill_route_count'] = snapshot['skill_route_count']
    elif action_type == 'initialize_mailbox':
        run_root = project_root / str(state['run_root'])
        for rel in ('mailbox/system_cards', 'mailbox/inbox', 'mailbox/outbox', 'mailbox/outbox/card_acks', 'runtime_receipts/card_reads', 'runtime_receipts/role_io_protocol', 'packets'):
            (run_root / rel).mkdir(parents=True, exist_ok=True)
        write_json(run_root / 'packet_ledger.json', router._create_empty_packet_ledger(project_root, str(state['run_id']), run_root))
        write_json(run_root / 'prompt_delivery_ledger.json', {'schema_version': 'flowpilot.prompt_delivery_ledger.v1', 'run_id': state['run_id'], 'deliveries': []})
        write_json(_card_ledger_path(run_root), _empty_card_ledger(str(state['run_id'])))
        write_json(_return_event_ledger_path(run_root), _empty_return_event_ledger(str(state['run_id'])))
        write_json(_role_io_protocol_ledger_path(run_root), _empty_role_io_protocol_ledger(str(state['run_id'])))
    elif action_type == 'record_user_request':
        run_root = project_root / str(state['run_root'])
        if router._confirmed_startup_intake(state) is not None and (not payload):
            intake_record = router._materialize_startup_intake_record(project_root, state, run_root)
            user_request = router._user_request_ref_from_startup_intake(project_root, state, intake_record)
            user_request_record = {'schema_version': 'flowpilot.user_request.v1', 'run_id': state['run_id'], 'source': 'startup_intake_ui', 'user_request_ref': user_request, 'startup_intake_record': intake_record, 'controller_may_read_body': False, 'body_text_included': False, 'recorded_at': utc_now()}
            state['startup_intake'] = intake_record
            state['startup_intake_record_path'] = intake_record['record_path']
            state['user_request_ref'] = user_request
        else:
            raise RouterError('record_user_request requires a confirmed native startup intake UI record; direct chat-body user_request payloads are unsupported')
        write_json(run_root / 'user_request.json', user_request_record)
        state['user_request'] = user_request
        state['user_request_path'] = project_relative(project_root, run_root / 'user_request.json')
    elif action_type == 'write_user_intake':
        run_root = project_root / str(state['run_root'])
        user_request = state.get('user_request')
        if not isinstance(user_request, dict):
            raise RouterError('cannot write user_intake before record_user_request')
        if user_request.get('schema_version') == USER_REQUEST_REF_SCHEMA:
            body_text = router._build_user_intake_body_from_ref(project_root, user_request, state.get('startup_answers') or {})
            user_intake = packet_runtime.create_user_intake_packet(project_root, run_id=str(state['run_id']), packet_id='user_intake', node_id='startup', body_text=body_text, startup_options=state.get('startup_answers') or {}, source='startup_intake_ui', body_visibility=packet_runtime.SEALED_BODY_VISIBILITY, startup_intake_ref=user_request, router_owned_startup_material=True)
            write_json(run_root / 'mailbox' / 'outbox' / 'user_intake.json', user_intake)
            result_extra['user_intake_source'] = 'startup_intake_ui'
            result_extra['controller_may_read_body'] = False
            result_extra['startup_intake_authority_source'] = 'startup_intake_record'
            router._finish_bootloader_action(project_root, state, pending, flag=flag, label=str(pending['label']), action_type=action_type, result_extra=result_extra)
            result = {'ok': True, 'applied': action_type, 'postcondition': flag}
            result.update(result_extra)
            return result
        raise RouterError('write_user_intake requires native startup intake user_request_ref; direct user_request payloads are unsupported')
    elif action_type == 'start_router_daemon':
        if not state.get('run_root'):
            raise RouterError('cannot start Router daemon before run shell exists')
        if not state.get('flags', {}).get('runtime_kit_copied'):
            _copy_runtime_kit_into_run_root(project_root / str(state['run_root']))
            state.setdefault('flags', {})['runtime_kit_copied'] = True
        run_state, run_root = _ensure_startup_run_state(project_root, state)
        result_extra.update(_start_or_attach_formal_router_daemon(project_root, run_root, run_state))
    elif action_type == 'load_controller_core':
        run_state, run_root = _ensure_startup_run_state(project_root, state)
        router._sync_startup_bootstrap_flags_to_run_state(state, run_state)
        if not _formal_router_daemon_ready(project_root, run_root):
            raise RouterError('cannot load Controller core before the formal Router daemon is live and ready')
        run_state['status'] = 'controller_ready'
        run_state['holder'] = 'controller'
        run_state['flags']['controller_core_loaded'] = True
        boundary_reconciliation = router._record_controller_boundary_confirmation_from_core_load(project_root, run_root, run_state, pending, payload or {'controller_action_completed': True, 'controller_boundary_confirmation_source': 'load_controller_core'}, source='load_controller_core_apply')
        result_extra['controller_boundary_confirmation'] = boundary_reconciliation.get('controller_boundary_confirmation')
        result_extra['coalesced_postconditions'] = ['controller_core_loaded', 'controller_role_confirmed']
        router._refresh_route_memory(project_root, run_root, run_state, trigger='load_controller_core')
        router.save_run_state(run_root, run_state)
    else:
        raise RouterError(f'unimplemented action: {action_type}')
    router._finish_bootloader_action(project_root, state, pending, flag=flag, label=str(pending['label']), action_type=action_type, result_extra=result_extra)
    result = {'ok': True, 'applied': action_type, 'postcondition': flag}
    result.update(result_extra)
    return result

__all__ = (
    '_finish_bootloader_action',
    'apply_bootloader_action',
)

_LOCAL_NAMES = set(globals())
