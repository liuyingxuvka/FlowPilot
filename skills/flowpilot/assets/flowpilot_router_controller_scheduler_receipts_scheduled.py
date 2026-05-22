"""Scheduled Controller receipt reconciliation and backfill helpers.

Receives the router facade explicitly so shared state writers and
public entrypoints keep the bound-router compatibility contract.
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
import flowpilot_router_controller_scheduler_receipts_scheduled_policy as _scheduled_policy
from flowpilot_router_controller_scheduler_receipts_scheduled_policy import *

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
    _scheduled_policy._bind_router(router)


def _reconcile_scheduled_controller_action_receipts(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    action_dir = _controller_actions_dir(run_root)
    if not action_dir.exists():
        return {'changed': False, 'reconciled': 0, 'blocked': 0}
    changed = False
    reconciled = 0
    blocked = 0
    superseded = 0
    for action_path in sorted(action_dir.glob('*.json')):
        entry = _read_json_for_runtime_scan(action_path)
        if entry is None:
            continue
        if entry.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
            continue
        action = entry.get('action') if isinstance(entry.get('action'), dict) else {}
        row_reconciliation = router._scheduler_row_reconciliation_for_entry(run_root, entry)
        action_id = str(entry.get('action_id') or action.get('controller_action_id') or '')
        receipt = read_json_if_exists(_controller_receipt_path(run_root, action_id)) if action_id else {}
        legacy_startup_canonical = router._canonicalize_legacy_startup_daemon_reconciliation(project_root, run_root, run_state, entry, action, receipt)
        if legacy_startup_canonical.get('applied'):
            now = utc_now()
            _commit_controller_action_reconciliation(
                router,
                project_root,
                run_root,
                run_state,
                action_path,
                entry,
                action=action,
                reconciliation=legacy_startup_canonical,
                scheduler_state='reconciled',
                resolve_blockers=True,
                now=now,
            )
            changed = True
            reconciled += 1
            continue
        if row_reconciliation is not None and (not (entry.get('router_reconciliation_status') == 'reconciled' or entry.get('router_reconciled_at'))):
            _commit_controller_action_reconciliation(
                router,
                project_root,
                run_root,
                run_state,
                action_path,
                entry,
                action=action or {'action_type': entry.get('action_type')},
                reconciliation=row_reconciliation,
                resolve_blockers=True,
                clear_pending_apply_required=False,
            )
            changed = True
            reconciled += 1
            continue
        current_scope_wait_resolved = False
        if entry.get('status') not in CONTROLLER_ACTION_CLOSED_STATUSES and action.get('action_type') == 'await_current_scope_reconciliation':
            try:
                current_scope_wait_resolved = not router._current_scope_reconciliation_wait_still_blocked(project_root, run_root, run_state, action)
            except RouterError:
                current_scope_wait_resolved = False
        if current_scope_wait_resolved:
            now = utc_now()
            reconciliation = {
                'applied': True,
                'source': 'current_scope_wait_no_longer_blocked',
                'scope_kind': action.get('scope_kind'),
                'scope_id': action.get('scope_id'),
                'superseded_at': now,
            }
            row_id = _commit_controller_action_reconciliation(
                router,
                project_root,
                run_root,
                run_state,
                action_path,
                entry,
                action=action,
                reconciliation=reconciliation,
                status='superseded',
                reconciliation_status='superseded_by_resolved_current_scope',
                scheduler_state='superseded',
                now=now,
            )
            router._clear_pending_controller_action_if_matches(run_state, entry, action, action_id=action_id, source='current_scope_wait_no_longer_blocked')
            append_history(
                run_state,
                'router_superseded_resolved_current_scope_wait',
                {
                    'controller_action_id': action_id,
                    'router_scheduler_row_id': row_id,
                    'scope_kind': action.get('scope_kind'),
                    'scope_id': action.get('scope_id'),
                },
            )
            changed = True
            superseded += 1
            continue
        if entry.get('status') not in CONTROLLER_ACTION_CLOSED_STATUSES and _card_return_resolved_for_action(run_root, str(run_state['run_id']), action):
            applied = {'applied': True, 'source': 'role_card_return_resolved_delivery_relay', 'card_id': action.get('card_id'), 'card_bundle_id': action.get('card_bundle_id'), 'delivery_attempt_id': action.get('delivery_attempt_id')}
            _commit_controller_action_reconciliation(
                router,
                project_root,
                run_root,
                run_state,
                action_path,
                entry,
                action=action,
                reconciliation=applied,
                scheduler_state='reconciled',
                clear_pending_apply_required=False,
            )
            changed = True
            reconciled += 1
            continue
        if entry.get('status') != 'done':
            continue
        if entry.get('router_reconciliation_status') == 'reconciled' or entry.get('router_reconciled_at'):
            action_type = str(action.get('action_type') or entry.get('action_type') or '')
            if action_type == WAIT_TARGET_REMINDER_ACTION_TYPE and receipt.get('schema_version') == CONTROLLER_RECEIPT_SCHEMA and receipt.get('status') == 'done':
                before_pending = json.dumps(run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else {}, sort_keys=True, default=str)
                try:
                    applied = router._apply_done_controller_receipt_effects(project_root, run_root, run_state, action, receipt)
                except RouterLedgerWriteInProgress:
                    raise
                except (RouterError, ValueError, OSError, json.JSONDecodeError) as exc:
                    applied = {'applied': False, 'reason': str(exc), 'action_type': action_type}
                after_pending = json.dumps(run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else {}, sort_keys=True, default=str)
                if applied.get('applied') and before_pending != after_pending:
                    now = utc_now()
                    reconciliation = dict(entry.get('router_reconciliation')) if isinstance(entry.get('router_reconciliation'), dict) else {}
                    reconciliation.update(
                        {
                            'applied': True,
                            'state_replay_source': 'already_reconciled_wait_target_reminder_receipt_replay',
                            'state_replayed_at': now,
                            'state_replay_result': applied,
                        }
                    )
                    entry['wait_target_receipt_state_replayed_at'] = now
                    _commit_controller_action_reconciliation(
                        router,
                        project_root,
                        run_root,
                        run_state,
                        action_path,
                        entry,
                        action=action,
                        reconciliation=reconciliation,
                        scheduler_state='reconciled',
                        preserve_reconciled_at=True,
                        set_status=False,
                        set_completed_at=False,
                        now=now,
                    )
                    append_history(
                        run_state,
                        'router_replayed_reconciled_wait_target_reminder_receipt',
                        {
                            'action_type': action_type,
                            'controller_action_id': action_id,
                            'router_scheduler_row_id': entry.get('router_scheduler_row_id'),
                            'source': reconciliation.get('state_replay_source'),
                        },
                    )
                    router.save_run_state(run_root, run_state)
                    changed = True
                    reconciled += 1
                    continue
            postcondition = _pending_action_postcondition(action)
            action_class = router._controller_action_completion_class(action) if action else {}
            stateful_kind = str(action_class.get('kind') or '')
            if (
                postcondition
                and not _pending_action_postcondition_satisfied(run_state, postcondition)
                and stateful_kind in {'display_status', 'router_owned_durable_artifact', 'stateful_host_postcondition'}
            ):
                if receipt.get('schema_version') == CONTROLLER_RECEIPT_SCHEMA and receipt.get('status') == 'done':
                    try:
                        applied = router._apply_done_controller_receipt_effects(project_root, run_root, run_state, action, receipt)
                    except RouterLedgerWriteInProgress:
                        raise
                    except (RouterError, ValueError, OSError, json.JSONDecodeError) as exc:
                        applied = {'applied': False, 'reason': str(exc), 'postcondition': postcondition}
                else:
                    applied = {'applied': False, 'reason': 'reconciled_stateful_action_missing_done_receipt', 'postcondition': postcondition, 'action_type': action.get('action_type')}
                if applied.get('applied') and _pending_action_postcondition_satisfied(run_state, postcondition):
                    now = utc_now()
                    reconciliation = dict(entry.get('router_reconciliation')) if isinstance(entry.get('router_reconciliation'), dict) else {}
                    reconciliation.update(
                        {
                            'applied': True,
                            'postcondition': postcondition,
                            'postcondition_replay_source': 'already_reconciled_controller_action_postcondition_drift_replay',
                            'postcondition_replayed_at': now,
                            'postcondition_replay_result': applied,
                        }
                    )
                    entry['router_postcondition_drift_reconciled_at'] = now
                    _commit_controller_action_reconciliation(
                        router,
                        project_root,
                        run_root,
                        run_state,
                        action_path,
                        entry,
                        action=action,
                        reconciliation=reconciliation,
                        scheduler_state='reconciled',
                        resolve_blockers=True,
                        preserve_reconciled_at=True,
                        now=now,
                    )
                    append_history(
                        run_state,
                        'router_replayed_reconciled_controller_postcondition',
                        {
                            'action_type': action.get('action_type'),
                            'controller_action_id': action_id,
                            'router_scheduler_row_id': entry.get('router_scheduler_row_id'),
                            'postcondition': postcondition,
                            'source': reconciliation.get('postcondition_replay_source'),
                        },
                    )
                    router._clear_pending_controller_action_if_matches(run_state, entry, action, action_id=action_id, source='already_reconciled_controller_action_postcondition_drift_replay')
                    router.save_run_state(run_root, run_state)
                    changed = True
                    reconciled += 1
                    continue
                apply_result_case = _scheduled_controller_receipt_apply_result_case(applied)
                if apply_result_case == 'repair_pending':
                    _clear_matching_controller_pending_and_save(router, run_root, run_state, entry, action, action_id=action_id, source='already_reconciled_controller_action_postcondition_repair_pending')
                    changed = True
                    continue
                if apply_result_case == 'blocked':
                    _clear_matching_controller_pending_and_save(router, run_root, run_state, entry, action, action_id=action_id, source='already_reconciled_controller_action_postcondition_blocked')
                    blocked += 1
                    changed = True
                    continue
                retry = _defer_controller_postcondition_reconciliation_retry(project_root, run_root, run_state, entry=entry, action=action, apply_result=applied)
                apply_result_case = _scheduled_controller_receipt_apply_result_case(applied, retry)
                if apply_result_case == 'retry_pending':
                    _clear_matching_controller_pending_and_save(router, run_root, run_state, entry, action, action_id=action_id, source='already_reconciled_controller_action_postcondition_retry_pending')
                    changed = True
                    continue
                if apply_result_case == 'blocked' and retry.get('retry_budget_exhausted'):
                    entry['postcondition_reconciliation_exhausted'] = True
                    entry['max_postcondition_reconciliation_attempts'] = retry.get('direct_retry_budget')
                    entry['router_reconciliation_status'] = 'blocked'
                    entry['router_reconciliation_blocked_at'] = utc_now()
                    entry['router_reconciliation_blocker'] = applied
                    write_json(action_path, entry)
                    router._write_control_blocker(project_root, run_root, run_state, source=CONTROLLER_POSTCONDITION_MISSING_BLOCKER_SOURCE, error_message=f"Controller action {entry.get('action_type')} was already reconciled, but Router could not replay its required postcondition after state drift.", action_type=str(entry.get('action_type') or ''), payload={'controller_action_id': action_id, 'router_scheduler_row_id': entry.get('router_scheduler_row_id'), 'postcondition': retry.get('postcondition') or applied.get('postcondition'), 'direct_retry_attempts_used': retry.get('direct_retry_attempts_used'), 'direct_retry_budget': retry.get('direct_retry_budget'), 'direct_retry_budget_exhausted': True, 'apply_result': applied})
                    if router._clear_pending_controller_action_if_matches(run_state, entry, action, action_id=action_id, source='already_reconciled_controller_action_postcondition_retry_exhausted'):
                        router.save_run_state(run_root, run_state)
                    blocked += 1
                    changed = True
                    continue
            scheduler_backfill = router._backfill_scheduler_row_from_reconciled_controller_action(project_root, run_root, run_state, entry, source='reconciled_controller_action_scheduler_backfill')
            blocker_resolution = router._resolve_control_blockers_for_reconciled_controller_action(project_root, run_root, run_state, action=action or {'action_type': entry.get('action_type')}, entry=entry, reconciliation=entry.get('router_reconciliation') if isinstance(entry.get('router_reconciliation'), dict) else None)
            if scheduler_backfill.get('changed') or blocker_resolution.get('changed'):
                changed = True
                if scheduler_backfill.get('changed'):
                    reconciled += 1
            continue
        if entry.get('router_reconciliation_status') == 'blocked':
            postcondition = _pending_action_postcondition(action)
            action_type = str(action.get('action_type') or entry.get('action_type') or '')
            if action_type == 'recover_role_agents' or postcondition == 'role_recovery_roles_restored':
                applied = router._reclaim_role_recovery_postcondition_from_report(project_root, run_root, run_state, source='blocked_controller_action_role_recovery_report_reclaim')
                if applied.get('applied') and (not postcondition or _pending_action_postcondition_satisfied(run_state, postcondition)):
                    now = utc_now()
                    entry['router_reconciliation_recovered_from_blocked_state'] = True
                    _commit_controller_action_reconciliation(
                        router,
                        project_root,
                        run_root,
                        run_state,
                        action_path,
                        entry,
                        action=action,
                        reconciliation=applied,
                        scheduler_state='reconciled',
                        resolve_blockers=True,
                        clear_pending_apply_required=False,
                        now=now,
                    )
                    changed = True
                    reconciled += 1
                    continue
            continue
        if not action:
            continue
        if row_reconciliation is not None:
            _commit_controller_action_reconciliation(
                router,
                project_root,
                run_root,
                run_state,
                action_path,
                entry,
                action=action,
                reconciliation=row_reconciliation,
                resolve_blockers=True,
                clear_pending_apply_required=False,
                set_status=False,
                set_completed_at=False,
            )
            changed = True
            reconciled += 1
            continue
        if receipt.get('schema_version') != CONTROLLER_RECEIPT_SCHEMA or receipt.get('status') != 'done':
            continue
        try:
            applied = router._apply_done_controller_receipt_effects(project_root, run_root, run_state, action, receipt)
        except RouterLedgerWriteInProgress:
            raise
        except (RouterError, ValueError, OSError, json.JSONDecodeError) as exc:
            applied = {'applied': False, 'reason': str(exc)}
        if not applied.get('applied'):
            apply_result_case = _scheduled_controller_receipt_apply_result_case(applied)
            if apply_result_case == 'repair_pending':
                changed = True
                continue
            if apply_result_case == 'blocked':
                blocked += 1
                changed = True
                continue
            retry = _defer_controller_postcondition_reconciliation_retry(project_root, run_root, run_state, entry=entry, action=action, apply_result=applied)
            apply_result_case = _scheduled_controller_receipt_apply_result_case(applied, retry)
            if apply_result_case == 'retry_pending':
                changed = True
                continue
            blocked += 1
            retry_exhausted = bool(retry.get('retry_budget_exhausted'))
            if retry_exhausted:
                entry['postcondition_reconciliation_exhausted'] = True
                entry['max_postcondition_reconciliation_attempts'] = retry.get('direct_retry_budget')
            entry['router_reconciliation_status'] = 'blocked'
            entry['router_reconciliation_blocked_at'] = utc_now()
            entry['router_reconciliation_blocker'] = applied
            write_json(action_path, entry)
            router._write_control_blocker(project_root, run_root, run_state, source=CONTROLLER_POSTCONDITION_MISSING_BLOCKER_SOURCE, error_message=f"Controller action {entry.get('action_type')} was marked done, but Router could not apply its required postcondition before reconciliation.", action_type=str(entry.get('action_type') or ''), payload={'controller_action_id': action_id, 'router_scheduler_row_id': entry.get('router_scheduler_row_id'), 'postcondition': retry.get('postcondition') or applied.get('postcondition'), 'direct_retry_attempts_used': retry.get('direct_retry_attempts_used'), 'direct_retry_budget': retry.get('direct_retry_budget'), 'direct_retry_budget_exhausted': retry_exhausted, 'apply_result': applied})
            changed = True
            continue
        _commit_controller_action_reconciliation(
            router,
            project_root,
            run_root,
            run_state,
            action_path,
            entry,
            action=action,
            reconciliation=applied,
            scheduler_state='reconciled',
            resolve_blockers=True,
            clear_pending_apply_required=False,
            set_status=False,
            set_completed_at=False,
        )
        changed = True
        reconciled += 1
    if changed:
        router._rebuild_controller_action_ledger(project_root, run_root, run_state)
        router._refresh_route_memory(project_root, run_root, run_state, trigger='after_scheduled_controller_receipt_reconciliation')
        router._sync_derived_run_views(project_root, run_root, run_state, reason='after_scheduled_controller_receipt_reconciliation', update_display=True)
        router.save_run_state(run_root, run_state)
    return {'changed': changed, 'reconciled': reconciled, 'blocked': blocked, 'superseded': superseded}

__all__ = (
    '_scheduler_row_reconciliation_for_entry',
    '_backfill_scheduler_row_from_reconciled_controller_action',
    '_canonicalize_legacy_startup_daemon_reconciliation',
    '_clear_pending_controller_action_if_matches',
    '_reconcile_scheduled_controller_action_receipts',
)

_LOCAL_NAMES = set(globals())
