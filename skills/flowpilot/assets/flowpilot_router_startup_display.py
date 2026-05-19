"""Startup owner helpers extracted from ``flowpilot_router_startup_flow``.

This module is part of the startup StructureMesh split. It is bound to the
router skeleton before execution so cross-owner transitional lookups stay
explicit while startup behavior is owned by smaller modules.
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


OWNER_MODULE = 'flowpilot_router_startup_display'

def _display_text_hash(router: ModuleType, display_text: str) -> str:
    _bind_router(router)
    return hashlib.sha256(display_text.encode('utf-8')).hexdigest()

def _user_dialog_display_gate(router: ModuleType, fields: dict[str, Any], *, display_kind: str, display_text: str) -> dict[str, Any]:
    _bind_router(router)
    gated = dict(fields)
    gated.update({'display_kind': display_kind, 'display_text_sha256': router._display_text_hash(display_text), 'requires_payload': 'display_confirmation', 'requires_user_dialog_display_confirmation': True, 'required_render_target': DISPLAY_CONFIRMATION_TARGET, 'display_confirmation_schema': DISPLAY_CONFIRMATION_SCHEMA})
    return gated

def _validate_display_confirmation(router: ModuleType, payload: dict[str, Any], *, action_type: str, display_kind: str, display_text: str) -> dict[str, Any]:
    _bind_router(router)
    confirmation = payload.get('display_confirmation')
    if not isinstance(confirmation, dict):
        raise RouterError(f'{action_type} requires payload.display_confirmation before apply; render display_text in the user dialog first')
    if confirmation.get('provenance') != DISPLAY_CONFIRMATION_PROVENANCE:
        raise RouterError(f'{action_type} display_confirmation requires provenance={DISPLAY_CONFIRMATION_PROVENANCE}')
    if confirmation.get('rendered_to') != DISPLAY_CONFIRMATION_TARGET:
        raise RouterError(f'{action_type} display_confirmation requires rendered_to={DISPLAY_CONFIRMATION_TARGET}')
    if confirmation.get('action_type') != action_type:
        raise RouterError(f'{action_type} display_confirmation action_type mismatch')
    if confirmation.get('display_kind') != display_kind:
        raise RouterError(f'{action_type} display_confirmation display_kind mismatch')
    expected_hash = router._display_text_hash(display_text)
    if confirmation.get('display_text_sha256') != expected_hash:
        raise RouterError(f'{action_type} display_confirmation display_text_sha256 mismatch')
    return {'schema_version': DISPLAY_CONFIRMATION_SCHEMA, 'action_type': action_type, 'display_kind': display_kind, 'rendered_to': DISPLAY_CONFIRMATION_TARGET, 'display_text_sha256': expected_hash, 'provenance': DISPLAY_CONFIRMATION_PROVENANCE, 'confirmed_at': utc_now()}

def _display_confirmation_for_action(router: ModuleType, payload: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    payload = payload or {}
    display_text = action.get('display_text')
    if not isinstance(display_text, str) or not display_text:
        raise RouterError('display confirmation requested for action without display_text')
    display_kind = action.get('display_kind')
    if not isinstance(display_kind, str) or not display_kind:
        raise RouterError('display confirmation requested for action without display_kind')
    return router._validate_display_confirmation(payload, action_type=str(action.get('action_type') or ''), display_kind=display_kind, display_text=display_text)

def _append_user_dialog_display_ledger(router: ModuleType, project_root: Path, run_root: Path, record: dict[str, Any]) -> None:
    _bind_router(router)
    del project_root
    ledger_path = run_root / 'display' / 'user_dialog_display_ledger.json'
    ledger = read_json_if_exists(ledger_path) or {'schema_version': 'flowpilot.user_dialog_display_ledger.v1', 'run_id': run_root.name, 'records': []}
    ledger.setdefault('records', []).append(record)
    ledger['updated_at'] = utc_now()
    write_json(ledger_path, ledger)

def _display_plan_display_kind(router: ModuleType, plan_projection: dict[str, Any]) -> str:
    _bind_router(router)
    items = plan_projection.get('items') if isinstance(plan_projection.get('items'), list) else []
    if len(items) == 1 and isinstance(items[0], dict) and (items[0].get('id') == 'await_pm_route') and (plan_projection.get('current_node_id') is None):
        return 'startup_waiting_state'
    return 'route_map'

def _display_plan_chat_markdown(router: ModuleType, plan_projection: dict[str, Any], *, display_kind: str) -> str:
    _bind_router(router)
    title = '# FlowPilot Startup Status' if display_kind == 'startup_waiting_state' else '# FlowPilot Route Map'
    lines = [title, '']
    for item in plan_projection.get('items') or []:
        if not isinstance(item, dict):
            continue
        label = str(item.get('label') or item.get('id') or 'Route item')
        status = str(item.get('status') or 'pending')
        lines.append(f'- {label} - {status}')
    if len(lines) == 2:
        lines.append('- Waiting for PM route - in_progress')
    active_path = plan_projection.get('active_path') if isinstance(plan_projection.get('active_path'), list) else []
    if active_path:
        path_labels = [str(item.get('label') or item.get('id')) for item in active_path if isinstance(item, dict) and (item.get('label') or item.get('id'))]
        if path_labels:
            lines.extend(['', f"Current path: {' > '.join(path_labels)}"])
    progress = plan_projection.get('hidden_leaf_progress')
    if isinstance(progress, dict) and progress.get('total'):
        lines.append(f"Hidden leaf progress: {progress.get('completed', 0)}/{progress.get('total')} complete")
    return '\n'.join(lines).rstrip() + '\n'

def _display_plan_user_dialog_fields(router: ModuleType, plan_projection: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    display_kind = router._display_plan_display_kind(plan_projection)
    display_text = router._display_plan_chat_markdown(plan_projection, display_kind=display_kind)
    display_label = 'startup waiting state' if display_kind == 'startup_waiting_state' else 'route map'
    return router._user_dialog_display_gate({'display_text': display_text, 'display_text_format': 'markdown', 'display_required': True, 'controller_must_display_text_before_apply': True, 'generated_files_alone_satisfy_chat_display': False, 'controller_display_rule': f'Paste this exact {display_label} display_text in the user dialog before writing the Controller receipt for sync_display_plan; display_plan.json or host-plan replacement alone does not satisfy display.'}, display_kind=display_kind, display_text=display_text)

def _startup_waiting_internal_display_fields(router: ModuleType) -> dict[str, Any]:
    _bind_router(router)
    return {'display_kind': 'startup_waiting_state', 'display_required': False, 'display_text_format': 'internal_state', 'controller_must_display_text_before_apply': False, 'requires_user_dialog_display_confirmation': False, 'generated_files_alone_satisfy_chat_display': False, 'user_visible_display_suppressed': True, 'internal_display_reason': 'waiting_for_pm_route_before_canonical_route', 'controller_display_rule': 'Do not paste a FlowPilot Startup Status waiting card into the user dialog. This sync is internal host-plan state only; startup user visibility is handled by the startup FlowPilot Route Sign display.'}

def _display_route_sign_user_dialog_fields(router: ModuleType, route_sign: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    display_text = route_sign.get('markdown')
    if not isinstance(display_text, str) or not display_text.strip():
        raise RouterError('route-sign display requires non-empty markdown')
    return router._user_dialog_display_gate({'display_text': display_text, 'display_text_format': 'markdown_mermaid', 'display_required': True, 'controller_must_display_text_before_apply': True, 'generated_files_alone_satisfy_chat_display': False, 'controller_display_rule': 'Paste this exact FlowPilot Route Sign Mermaid in the user dialog before writing the Controller receipt for sync_display_plan; display_plan.json or generated files alone do not satisfy display.'}, display_kind='route_map', display_text=display_text)

def _startup_banner_display(router: ModuleType) -> dict[str, Any]:
    _bind_router(router)
    banner_path = runtime_kit_source() / 'cards' / 'system' / 'startup_banner.md'
    if not banner_path.exists():
        raise RouterError('startup banner card is missing')
    text = banner_path.read_text(encoding='utf-8')
    stripped = text.lstrip()
    if stripped.startswith('<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1'):
        end = stripped.find('-->')
        if end >= 0:
            stripped = stripped[end + 3:].lstrip()
    display_text = stripped.rstrip() + '\n'
    return router._user_dialog_display_gate({'display_path': str(banner_path), 'display_text': display_text, 'display_text_format': 'plain_text', 'display_required': True, 'controller_must_display_text_before_apply': True, 'generated_files_alone_satisfy_chat_display': False, 'controller_display_rule': 'Paste this exact startup banner display_text in the user dialog before writing the Controller receipt for emit_startup_banner; the Controller receipt requires display_confirmation.rendered_to=user_dialog with matching display_text_sha256.'}, display_kind='startup_banner', display_text=display_text)

def _route_sign_payload(router: ModuleType, project_root: Path, *, write: bool, trigger: str, mark_chat_displayed: bool, cockpit_open: bool=False, mark_ui_displayed: bool=False) -> dict[str, Any]:
    _bind_router(router)
    return flowpilot_user_flow_diagram.generate(project_root, write=write, trigger=trigger, cockpit_open=cockpit_open, display_surface='both' if cockpit_open else 'chat', mark_chat_displayed=mark_chat_displayed, mark_ui_displayed=mark_ui_displayed, reviewer_check=False)

def _startup_route_sign_payload(router: ModuleType, project_root: Path, *, write: bool, mark_chat_displayed: bool) -> dict[str, Any]:
    _bind_router(router)
    return router._route_sign_payload(project_root, write=write, trigger='startup', mark_chat_displayed=mark_chat_displayed)

def _route_map_route_sign_payload(router: ModuleType, project_root: Path, *, write: bool, mark_chat_displayed: bool) -> dict[str, Any]:
    _bind_router(router)
    return router._route_sign_payload(project_root, write=write, trigger='key_node_change', mark_chat_displayed=mark_chat_displayed)

def _route_sign_has_canonical_route(router: ModuleType, payload: dict[str, Any]) -> bool:
    _bind_router(router)
    return payload.get('flowpilot_path_status') == 'ok' and int(payload.get('route_node_count') or 0) > 0 and (str(payload.get('route_source_kind') or 'none') != 'none')

def _display_surface_receipt_from_payload(router: ModuleType, payload: dict[str, Any], *, run_id: str, requested: str, selected_surface: str) -> dict[str, Any]:
    _bind_router(router)
    receipt = payload.get('display_surface_receipt') if isinstance(payload, dict) else None
    if receipt is None:
        return {'schema_version': DISPLAY_SURFACE_RECEIPT_SCHEMA, 'run_id': run_id, 'requested_display_surface': requested, 'actual_surface': selected_surface, 'source_kind': 'controller_user_dialog_render', 'host_display_surface_verified': False, 'fallback_displayed': selected_surface != 'cockpit', 'recorded_at': utc_now()}
    if not isinstance(receipt, dict):
        raise RouterError('display_surface_receipt must be an object when supplied')
    if receipt.get('schema_version') != DISPLAY_SURFACE_RECEIPT_SCHEMA:
        raise RouterError(f'display_surface_receipt requires schema_version={DISPLAY_SURFACE_RECEIPT_SCHEMA}')
    actual = receipt.get('actual_surface')
    if actual not in {'chat_route_sign', 'chat_route_sign_fallback', 'cockpit'}:
        raise RouterError('display_surface_receipt.actual_surface must be chat_route_sign, chat_route_sign_fallback, or cockpit')
    if receipt.get('run_id') not in {None, run_id}:
        raise RouterError('display_surface_receipt.run_id must match current run_id')
    if actual == 'cockpit' and receipt.get('host_display_surface_verified') is not True:
        raise RouterError('display_surface_receipt for cockpit requires host_display_surface_verified=true')
    return {'schema_version': DISPLAY_SURFACE_RECEIPT_SCHEMA, 'run_id': run_id, 'requested_display_surface': requested, 'actual_surface': actual, 'source_kind': str(receipt.get('source_kind') or 'host_receipt'), 'host_display_surface_verified': bool(receipt.get('host_display_surface_verified')), 'fallback_displayed': bool(receipt.get('fallback_displayed', actual != 'cockpit')), 'host_surface_id': receipt.get('host_surface_id'), 'notes': receipt.get('notes'), 'recorded_at': utc_now()}

def _write_display_surface_status(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], display_confirmation: dict[str, Any], payload: dict[str, Any] | None=None) -> None:
    _bind_router(router)
    answers = router._startup_answers_from_run(run_root)
    requested = str(answers.get('display_surface') or 'chat route signs')
    requested_normalized = requested.lower()
    selected_surface = 'chat_route_sign' if 'chat' in requested_normalized else 'chat_route_sign_fallback'
    display_receipt = router._display_surface_receipt_from_payload(payload or {}, run_id=str(run_state['run_id']), requested=requested, selected_surface=selected_surface)
    actual_surface = str(display_receipt.get('actual_surface') or selected_surface)
    if actual_surface == 'cockpit':
        selected_surface = 'cockpit'
    route_sign = router._startup_route_sign_payload(project_root, write=True, mark_chat_displayed=True)
    sign_path = run_root / 'diagrams' / 'current_route_sign.md'
    sign_path.parent.mkdir(parents=True, exist_ok=True)
    sign_path.write_text(route_sign['markdown'], encoding='utf-8')
    write_json(run_root / 'display' / 'display_surface.json', {'schema_version': 'flowpilot.display_surface.v1', 'run_id': run_state['run_id'], 'requested_display_surface': requested, 'selected_surface': selected_surface, 'actual_display_surface': actual_surface, 'chat_route_sign_path': project_relative(project_root, sign_path), 'standard_route_sign_markdown_path': project_relative(project_root, Path(route_sign['markdown_preview_path'])), 'standard_route_sign_mermaid_path': project_relative(project_root, Path(route_sign['mermaid_path'])), 'standard_route_sign_display_packet_path': project_relative(project_root, Path(route_sign['display_packet_path'])), 'route_sign_mermaid_sha256': route_sign['mermaid_sha256'], 'chat_display_required': route_sign['chat_display_required'], 'chat_displayed_by_controller': True, 'user_dialog_display_confirmation': display_confirmation, 'display_surface_receipt': display_receipt, 'host_display_surface_verified': bool(display_receipt.get('host_display_surface_verified')), 'generated_files_alone_satisfy_chat_display': False, 'controller_display_rule': 'Controller must paste the router-provided display_text Mermaid block in chat before writing the Controller receipt for this action; generated files alone do not satisfy display.', 'cockpit_status': 'host_verified_open' if selected_surface == 'cockpit' else 'not_started_in_router_runtime', 'cockpit_probe_required_for_requested_cockpit': 'cockpit' in requested_normalized, 'reviewer_fallback_check_required_for_requested_cockpit': 'cockpit' in requested_normalized, 'fallback_is_display_only_not_product_ui_completion': True, 'updated_at': utc_now()})

def _next_display_plan_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    sync_payload = router._display_plan_sync_payload(project_root, run_root, run_state)
    last_sync = run_state.get('visible_plan_sync') if isinstance(run_state.get('visible_plan_sync'), dict) else {}
    route_sign_fresh = not sync_payload.get('route_sign_display_required') or last_sync.get('route_sign_mermaid_sha256') == sync_payload.get('route_sign_mermaid_sha256')
    if last_sync.get('projection_hash') == sync_payload['projection_hash'] and route_sign_fresh:
        return None
    idempotency_key = _router_scheduler_idempotency_key({'action_type': 'sync_display_plan', 'label': 'controller_syncs_display_plan', 'projection_hash': sync_payload['projection_hash']}, 'startup', 'startup')
    if router._controller_action_open_for(run_root, action_type='sync_display_plan', idempotency_key=idempotency_key):
        return None
    allowed_writes = [project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, router._route_state_snapshot_path(run_root)), project_relative(project_root, router._continuation_quarantine_path(run_root)), project_relative(project_root, router._route_display_refresh_path(run_root)), project_relative(project_root, run_root / 'display' / 'user_dialog_display_ledger.json')]
    if not sync_payload['display_plan_exists']:
        allowed_writes.append(project_relative(project_root, router._display_plan_path(run_root)))
    if sync_payload.get('route_sign_display_required'):
        allowed_writes.extend([project_relative(project_root, run_root / 'diagrams' / 'user-flow-diagram.mmd'), project_relative(project_root, run_root / 'diagrams' / 'user-flow-diagram.md'), project_relative(project_root, run_root / 'diagrams' / 'user-flow-diagram-display.json')])
    allowed_reads = [project_relative(project_root, project_root / '.flowpilot' / 'current.json'), project_relative(project_root, router._display_plan_path(run_root)), project_relative(project_root, router._route_state_snapshot_path(run_root)), project_relative(project_root, router._current_status_summary_path(run_root)), project_relative(project_root, _router_daemon_status_path(run_root)), project_relative(project_root, router.run_state_path(run_root))]
    for raw_path in (sync_payload.get('route_sign_source_frontier_path'), sync_payload.get('route_sign_source_route_path')):
        if isinstance(raw_path, str) and raw_path:
            path = Path(raw_path)
            read_path = path if path.is_absolute() else project_root / path
            try:
                rel_path = project_relative(project_root, read_path)
            except RouterError:
                continue
            if rel_path not in allowed_reads:
                allowed_reads.append(rel_path)
    return make_action(action_type='sync_display_plan', actor='controller', label='controller_syncs_display_plan', summary=router._display_plan_sync_action_summary(sync_payload), allowed_reads=allowed_reads, allowed_writes=allowed_writes, extra={**sync_payload})

def _display_plan_sync_action_summary(router: ModuleType, sync_payload: dict[str, Any]) -> str:
    _bind_router(router)
    if sync_payload.get('route_sign_display_required'):
        return 'Display the canonical FlowPilot Route Sign in the user dialog, then sync the host visible plan from committed route state.'
    if sync_payload.get('display_kind') == 'startup_waiting_state' and sync_payload.get('user_visible_display_suppressed'):
        return 'Sync the host visible plan to the internal waiting-for-PM-route placeholder; no user-dialog route map is required until a canonical PM route exists.'
    return 'Display the current route map projection in the user dialog, then sync the host visible plan from display_plan.json.'

def _apply_sync_display_plan_state(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], action: dict[str, Any], payload: dict[str, Any] | None=None) -> dict[str, Any]:
    _bind_router(router)
    payload = payload or {}
    confirmation = None
    if action.get('requires_user_dialog_display_confirmation'):
        confirmation = router._display_confirmation_for_action(payload, action)
    sync_payload = router._display_plan_sync_payload(project_root, run_root, run_state)
    if not sync_payload['display_plan_exists']:
        write_json(router._display_plan_path(run_root), router._waiting_for_pm_display_plan(run_state))
        sync_payload = router._display_plan_sync_payload(project_root, run_root, run_state)
    router._write_route_state_snapshot(project_root, run_root, run_state, source_event='sync_display_plan')
    sync_payload = router._display_plan_sync_payload(project_root, run_root, run_state)
    if sync_payload.get('route_sign_display_required'):
        route_sign = router._route_map_route_sign_payload(project_root, write=True, mark_chat_displayed=True)
        sync_payload = {**sync_payload, 'route_sign_markdown_path': route_sign.get('markdown_preview_path'), 'route_sign_mermaid_path': route_sign.get('mermaid_path'), 'route_sign_display_packet_path': route_sign.get('display_packet_path'), 'route_sign_mermaid_sha256': route_sign.get('mermaid_sha256'), 'route_sign_source_kind': route_sign.get('route_source_kind'), 'route_sign_node_count': route_sign.get('route_node_count'), 'route_sign_checklist_item_count': route_sign.get('route_checklist_item_count'), 'route_sign_layout': route_sign.get('route_sign_layout'), 'route_sign_source_route_path': route_sign.get('source_route_path'), 'route_sign_source_frontier_path': route_sign.get('source_frontier_path')}
        if isinstance(sync_payload.get('route_display_refresh'), dict):
            sync_payload['route_display_refresh']['route_sign_markdown_path'] = route_sign.get('markdown_preview_path')
            sync_payload['route_display_refresh']['route_sign_mermaid_sha256'] = route_sign.get('mermaid_sha256')
    if confirmation is not None:
        router._append_user_dialog_display_ledger(project_root, run_root, confirmation)
    if isinstance(sync_payload.get('route_display_refresh'), dict):
        write_json(router._route_display_refresh_path(run_root), sync_payload['route_display_refresh'])
    run_state['visible_plan_sync'] = {'display_plan_path': sync_payload['display_plan_path'], 'route_state_snapshot_path': sync_payload['route_state_snapshot_path'], 'route_state_snapshot_hash': sync_payload['route_state_snapshot_hash'], 'current_status_summary_path': sync_payload.get('current_status_summary_path'), 'current_status_summary_hash': sync_payload.get('current_status_summary_hash'), 'projection_hash': sync_payload['projection_hash'], 'display_text_format': sync_payload.get('display_text_format'), 'route_sign_display_required': sync_payload.get('route_sign_display_required'), 'route_sign_display_degraded_reason': sync_payload.get('route_sign_display_degraded_reason'), 'route_sign_markdown_path': sync_payload.get('route_sign_markdown_path'), 'route_sign_mermaid_path': sync_payload.get('route_sign_mermaid_path'), 'route_sign_display_packet_path': sync_payload.get('route_sign_display_packet_path'), 'route_sign_mermaid_sha256': sync_payload.get('route_sign_mermaid_sha256'), 'route_sign_source_kind': sync_payload.get('route_sign_source_kind'), 'route_sign_node_count': sync_payload.get('route_sign_node_count'), 'route_sign_checklist_item_count': sync_payload.get('route_sign_checklist_item_count'), 'route_sign_layout': sync_payload.get('route_sign_layout'), 'route_sign_source_route_path': sync_payload.get('route_sign_source_route_path'), 'route_sign_source_frontier_path': sync_payload.get('route_sign_source_frontier_path'), 'route_display_refresh_path': sync_payload.get('route_display_refresh_path'), 'route_display_refresh_sha256': packet_runtime.sha256_file(router._route_display_refresh_path(run_root)) if router._route_display_refresh_path(run_root).exists() else None, 'display_is_route_authority': False, 'display_required': sync_payload.get('display_required'), 'user_visible_display_suppressed': sync_payload.get('user_visible_display_suppressed', False), 'internal_display_reason': sync_payload.get('internal_display_reason'), 'synced_at': utc_now(), 'host_action': sync_payload['host_action']}
    if confirmation is not None:
        run_state['visible_plan_sync']['user_dialog_display_confirmation'] = confirmation
    run_state.setdefault('flags', {})['visible_plan_synced'] = True
    return sync_payload

def _next_startup_display_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    flags = run_state['flags']
    if not flags.get('controller_role_confirmed'):
        return None
    if flags.get('startup_display_status_written'):
        return None
    if router._controller_action_open_for(run_root, action_type='write_display_surface_status', postcondition='startup_display_status_written'):
        return None
    if router._controller_action_reconciled_for(run_root, action_type='write_display_surface_status', postcondition='startup_display_status_written'):
        return None
    route_sign = router._startup_route_sign_payload(project_root, write=False, mark_chat_displayed=False)
    answers = router._startup_answers_from_run(run_root)
    requested_display_surface = str(answers.get('display_surface') or 'chat')
    cockpit_requested = requested_display_surface == 'cockpit'
    display_gate = router._user_dialog_display_gate({'display_text': route_sign['markdown'], 'display_text_format': 'markdown_mermaid', 'display_required': True, 'controller_must_display_text_before_apply': True, 'generated_files_alone_satisfy_chat_display': False, 'controller_display_rule': 'Paste this exact startup route-sign display_text in the user dialog before writing the Controller receipt for write_display_surface_status; generated files alone do not satisfy display.'}, display_kind='startup_route_sign', display_text=route_sign['markdown'])
    return make_action(action_type='write_display_surface_status', actor='controller', label='controller_writes_startup_display_surface_status', summary='Display the startup FlowPilot Route Sign Mermaid in chat, then write startup display-surface status before reviewer startup fact review.', allowed_reads=[project_relative(project_root, run_root / 'startup_answers.json'), project_relative(project_root, run_root / 'execution_frontier.json')], allowed_writes=[project_relative(project_root, run_root / 'display' / 'display_surface.json'), project_relative(project_root, run_root / 'diagrams' / 'current_route_sign.md'), project_relative(project_root, run_root / 'diagrams' / 'user-flow-diagram.mmd'), project_relative(project_root, run_root / 'diagrams' / 'user-flow-diagram.md'), project_relative(project_root, run_root / 'diagrams' / 'user-flow-diagram-display.json'), project_relative(project_root, run_root / 'display' / 'user_dialog_display_ledger.json'), project_relative(project_root, router.run_state_path(run_root))], extra={'postcondition': 'startup_display_status_written', **display_gate, 'chat_display_required': route_sign['chat_display_required'], 'route_sign_mermaid_sha256': route_sign['mermaid_sha256'], 'requested_display_surface': requested_display_surface, 'resolved_display_surface': 'chat-fallback' if cockpit_requested else 'chat-requested', 'cockpit_probe_required_for_requested_cockpit': cockpit_requested, 'reviewer_fallback_check_required_for_requested_cockpit': cockpit_requested, 'fallback_is_display_only_not_product_ui_completion': True, 'payload_contract': _display_surface_receipt_payload_contract()})

_LOCAL_NAMES = set(globals())
