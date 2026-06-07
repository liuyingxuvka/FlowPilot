"""Coarse events repair owner helpers for the FlowPilot router.

The public router names stay in `flowpilot_router`. This module owns a
cohesive behavior family and receives the router facade as an explicit runtime
dependency so shared state writers and public entrypoints stay aligned.
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
_BOUND_ROUTER: ModuleType | None = None


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

__all__ = (
    '_repair_transactions_root',
    '_repair_transaction_index_path',
    '_repair_transaction_path',
    '_repair_transaction_id',
    '_write_repair_transaction_index',
    '_active_repair_transaction_for_event',
    '_repair_transaction_outcome_kind',
)

_LOCAL_NAMES = set(globals())
