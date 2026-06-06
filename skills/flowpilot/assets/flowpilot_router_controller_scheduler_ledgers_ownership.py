"""Router ownership ledger helpers for the FlowPilot router."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any


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


def _router_ownership_counts(router: ModuleType, entries: list[dict[str, Any]]) -> dict[str, int]:
    _bind_router(router)
    counts: dict[str, int] = {'controller_receipt_done': 0, 'router_reclaim_pending': 0, 'router_reclaimed': 0, 'waiting_for_role': 0, 'blocked': 0}
    for item in entries:
        state = str(item.get('router_state') or 'unknown')
        counts[state] = counts.get(state, 0) + 1
    counts['total'] = len(entries)
    return counts


def _empty_router_ownership_ledger(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    return {'schema_version': ROUTER_OWNERSHIP_LEDGER_SCHEMA, 'run_id': run_state.get('run_id'), 'run_root': project_relative(project_root, run_root), 'updated_at': utc_now(), 'entries': [], 'counts': router._router_ownership_counts([]), 'controller_may_record_only_local_receipts': True, 'router_only_fields': ['router_state', 'workflow_owner', 'postcondition', 'artifact_refs', 'blocker_source']}


def _read_router_ownership_ledger(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    path = _router_ownership_ledger_path(run_root)
    ledger = read_json_if_exists(path)
    if ledger.get('schema_version') != ROUTER_OWNERSHIP_LEDGER_SCHEMA:
        return router._empty_router_ownership_ledger(project_root, run_root, run_state)
    entries = ledger.get('entries') if isinstance(ledger.get('entries'), list) else []
    ledger['entries'] = [item for item in entries if isinstance(item, dict)]
    ledger['counts'] = router._router_ownership_counts(ledger['entries'])
    return ledger


def _write_router_ownership_ledger(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    entries = ledger.get('entries') if isinstance(ledger.get('entries'), list) else []
    ledger.update({'schema_version': ROUTER_OWNERSHIP_LEDGER_SCHEMA, 'run_id': run_state.get('run_id'), 'run_root': project_relative(project_root, run_root), 'updated_at': utc_now(), 'entries': [item for item in entries if isinstance(item, dict)]})
    ledger['counts'] = router._router_ownership_counts(ledger['entries'])
    write_json(_router_ownership_ledger_path(run_root), ledger)
    run_state['router_ownership_ledger_path'] = project_relative(project_root, _router_ownership_ledger_path(run_root))
    return ledger


def _ensure_router_ownership_ledger(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    ledger = router._read_router_ownership_ledger(project_root, run_root, run_state)
    return router._write_router_ownership_ledger(project_root, run_root, run_state, ledger)


def _router_ownership_ledger_summary(router: ModuleType, run_root: Path) -> dict[str, Any]:
    _bind_router(router)
    ledger = read_json_if_exists(_router_ownership_ledger_path(run_root))
    if ledger.get('schema_version') != ROUTER_OWNERSHIP_LEDGER_SCHEMA:
        return {'exists': False, 'counts': router._router_ownership_counts([]), 'entries': []}
    entries = [item for item in ledger.get('entries') or [] if isinstance(item, dict)]
    return {'exists': True, 'path': str(_router_ownership_ledger_path(run_root)), 'updated_at': ledger.get('updated_at'), 'counts': ledger.get('counts') or router._router_ownership_counts(entries), 'entries': [{'entry_id': item.get('entry_id'), 'action_id': item.get('action_id'), 'action_type': item.get('action_type'), 'router_state': item.get('router_state'), 'workflow_owner': item.get('workflow_owner'), 'postcondition': item.get('postcondition'), 'updated_at': item.get('updated_at')} for item in entries]}


def _record_router_ownership_entry(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, action_id: str, action_type: str, router_state: str, workflow_owner: str, postcondition: str='', source: str, receipt_path: str | None=None, artifact_refs: dict[str, Any] | None=None, details: dict[str, Any] | None=None) -> dict[str, Any]:
    _bind_router(router)
    ledger = router._read_router_ownership_ledger(project_root, run_root, run_state)
    entry_id = action_id or f'{action_type}:{postcondition or router_state}'
    entry = {'entry_id': entry_id, 'schema_version': 'flowpilot.router_ownership_entry.v1', 'run_id': run_state.get('run_id'), 'action_id': action_id, 'action_type': action_type, 'router_state': router_state, 'workflow_owner': workflow_owner, 'postcondition': postcondition, 'source': source, 'receipt_path': receipt_path, 'artifact_refs': artifact_refs or {}, 'details': details or {}, 'updated_at': utc_now(), 'controller_may_write_this_entry': False}
    entries = [item for item in ledger.get('entries', []) if isinstance(item, dict) and item.get('entry_id') != entry_id]
    entries.append(entry)
    ledger['entries'] = entries
    router._write_router_ownership_ledger(project_root, run_root, run_state, ledger)
    return entry


__all__ = (
    '_router_ownership_counts',
    '_empty_router_ownership_ledger',
    '_read_router_ownership_ledger',
    '_write_router_ownership_ledger',
    '_ensure_router_ownership_ledger',
    '_router_ownership_ledger_summary',
    '_record_router_ownership_entry',
)

_LOCAL_NAMES = set(globals())
