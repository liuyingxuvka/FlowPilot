"""Card return helper shard for FlowPilot router."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import card_runtime

def _current_node_pre_review_reconciliation_blockers(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    frontier = router._active_frontier(run_root)
    if str(frontier.get('status') or '') != 'current_node_loop':
        return []
    active_node_id = str(frontier.get('active_node_id') or '')
    if not active_node_id:
        return []
    flags = run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {}
    blockers: list[dict[str, Any]] = []
    required_flags = (('current_node_result_relayed_to_pm', 'current-node result must be relayed to PM before reviewer work'), ('current_node_result_disposition_recorded', 'PM disposition must be recorded before reviewer work'), ('current_node_result_absorbed_by_pm', 'PM must absorb current-node result before reviewer work'))
    for flag, reason in required_flags:
        if not flags.get(flag):
            blockers.append({'kind': 'missing_current_node_flag', 'flag': flag, 'reason': reason, 'scope_kind': 'current_node', 'node_id': active_node_id})
    batch = router._active_parallel_packet_batch(run_root, 'current_node')
    if not isinstance(batch, dict):
        blockers.append({'kind': 'missing_current_node_batch', 'reason': 'current-node review requires a current-node packet batch', 'scope_kind': 'current_node', 'node_id': active_node_id})
    elif str(batch.get('node_id') or '') == active_node_id:
        batch_status = str(batch.get('status') or '')
        if batch_status != 'pm_absorbed':
            blockers.append({'kind': 'current_node_batch_not_absorbed', 'batch_id': batch.get('batch_id'), 'batch_status': batch_status, 'reason': 'current-node batch must be PM-absorbed before reviewer work', 'scope_kind': 'current_node', 'node_id': active_node_id})
    else:
        blockers.append({'kind': 'missing_current_node_batch_for_active_node', 'batch_id': batch.get('batch_id'), 'batch_node_id': batch.get('node_id'), 'reason': 'active node has no matching local current-node batch', 'scope_kind': 'current_node', 'node_id': active_node_id})
    for pending_return in router._pending_return_records(run_root, str(run_state['run_id'])):
        if router._pending_return_matches_active_node_scope(pending_return, frontier):
            blockers.append({'kind': 'pending_current_node_card_return', 'card_id': pending_return.get('card_id'), 'card_ids': pending_return.get('card_ids') or [], 'target_role': pending_return.get('target_role'), 'card_return_event': pending_return.get('card_return_event'), 'expected_return_path': pending_return.get('expected_return_path'), 'reason': 'current-node system-card ACK/read receipt must close before reviewer work', 'scope_kind': 'current_node', 'node_id': active_node_id})
    return blockers

def _startup_pre_review_reconciliation_blockers(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    flags = run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {}
    blockers: list[dict[str, Any]] = []
    required_flags = (('banner_emitted', 'startup banner display must be reconciled before startup fact review'), ('roles_started', 'startup role slots must be reconciled before startup fact review'), ('role_core_prompts_injected', 'startup role core prompts must be reconciled before startup fact review'), ('controller_role_confirmed', 'Controller boundary confirmation must be reconciled before startup fact review'), ('startup_mechanical_audit_written', 'startup mechanical audit must be reconciled before startup fact review'), ('startup_display_status_written', 'startup display status must be reconciled before startup fact review'))
    answers = router._startup_answers_from_run(run_root)
    if router._scheduled_continuation_requested(answers):
        required_flags = (('continuation_binding_recorded', 'startup heartbeat binding must be reconciled before startup fact review'), *required_flags)
    for flag, reason in required_flags:
        if not flags.get(flag):
            blockers.append({'kind': 'missing_startup_flag', 'flag': flag, 'reason': reason, 'scope_kind': 'startup', 'scope_id': 'startup'})
    try:
        bootstrap = router.load_bootstrap_state(project_root, create_if_missing=False)
    except router.RouterError:
        bootstrap = {}
    bootstrap_flags = bootstrap.get('flags') if isinstance(bootstrap.get('flags'), dict) else {}
    for flag, reason in (('banner_emitted', 'startup banner display must be reconciled before startup fact review'), ('roles_started', 'startup role slots must be reconciled before startup fact review')):
        if not bootstrap_flags.get(flag):
            blockers.append({'kind': 'missing_startup_bootstrap_flag', 'flag': flag, 'reason': reason, 'scope_kind': 'startup', 'scope_id': 'startup'})
    if not router._startup_pre_review_cards_delivered(run_state):
        blockers.append({'kind': 'startup_prep_cards_not_all_sent', 'missing_card_flags': sorted((flag for flag in router._startup_pre_review_card_flags() if not flags.get(flag))), 'reason': 'startup prep cards must be sent before Reviewer startup fact review', 'scope_kind': 'startup', 'scope_id': 'startup'})
    for pending_return in router._startup_pre_review_pending_returns(run_root, run_state):
        blockers.append({'kind': 'pending_startup_prep_card_return', 'card_id': pending_return.get('card_id'), 'card_ids': pending_return.get('card_ids') or [], 'target_role': pending_return.get('target_role'), 'card_return_event': pending_return.get('card_return_event'), 'expected_return_path': pending_return.get('expected_return_path'), 'reason': 'startup prep card ACK/read receipt must close before Reviewer startup fact review', 'scope_kind': 'startup', 'scope_id': 'startup'})
    action_dir = router._controller_actions_dir(run_root)
    if action_dir.exists():
        for action_path in sorted(action_dir.glob('*.json')):
            entry = router._read_json_for_runtime_scan(action_path)
            if entry is None:
                continue
            if entry.get('schema_version') != router.CONTROLLER_ACTION_SCHEMA:
                continue
            if not router._controller_action_is_ordinary_work_row(entry):
                continue
            if entry.get('status') in {'done', 'blocked', 'skipped'} and entry.get('router_reconciliation_status') == 'reconciled':
                continue
            action = entry.get('action') if isinstance(entry.get('action'), dict) else {}
            scope_kind = str(entry.get('scope_kind') or action.get('scope_kind') or '')
            if scope_kind != 'startup' and (not router._action_is_startup_scoped(action)):
                continue
            if entry.get('action_type') in {'await_card_return_event', 'await_card_bundle_return_event'}:
                continue
            if entry.get('status') not in {'done', 'blocked', 'skipped'} or entry.get('router_reconciliation_status') != 'reconciled':
                blockers.append({'kind': 'pending_startup_controller_row', 'action_id': entry.get('action_id'), 'action_type': entry.get('action_type'), 'status': entry.get('status'), 'router_reconciliation_status': entry.get('router_reconciliation_status'), 'reason': 'startup-local Controller row must be done and Router-reconciled before Reviewer startup fact review', 'scope_kind': 'startup', 'scope_id': 'startup'})
    active_blocker = run_state.get('active_control_blocker')
    if isinstance(active_blocker, dict) and active_blocker.get('status') not in {'resolved', 'superseded', 'closed'} and (not router._resume_reentry_gate_pending(run_state)):
        blockers.append({'kind': 'active_startup_control_blocker', 'control_blocker_id': active_blocker.get('control_blocker_id'), 'source': active_blocker.get('source'), 'reason': 'active local control blocker must be resolved before Reviewer startup fact review', 'scope_kind': 'startup', 'scope_id': 'startup'})
    return blockers

def _pre_review_reconciliation_blockers_for_trigger(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], review_trigger: str) -> list[dict[str, Any]]:
    if review_trigger in router.STARTUP_REVIEW_BEGIN_JOIN_EVENTS or review_trigger == router.REVIEWER_STARTUP_FACT_CARD_ID:
        return router._startup_pre_review_reconciliation_blockers(project_root, run_root, run_state)
    return router._current_node_pre_review_reconciliation_blockers(project_root, run_root, run_state)

def _current_scope_reconciliation_wait_still_blocked(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], pending_action: dict[str, Any]) -> bool:
    if pending_action.get('action_type') != 'await_current_scope_reconciliation':
        return False
    if pending_action.get('scope_kind') == 'startup':
        return bool(router._startup_pre_review_reconciliation_blockers(project_root, run_root, run_state))
    if pending_action.get('scope_kind') != 'current_node':
        return False
    return bool(router._current_node_pre_review_reconciliation_blockers(project_root, run_root, run_state))

def _next_local_obligation_before_passive_wait(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], pending_action: dict[str, Any]) -> dict[str, Any] | None:
    if pending_action.get('action_type') != 'await_current_scope_reconciliation':
        return None
    if pending_action.get('scope_kind') != 'startup':
        return None
    for producer in (router._next_controller_boundary_confirmation_action, router._next_startup_mechanical_audit_action, router._next_startup_display_action):
        action = producer(project_root, run_state, run_root)
        if action is not None:
            action['preempts_passive_wait_action_type'] = pending_action.get('action_type')
            action['preempts_passive_wait_label'] = pending_action.get('label')
            return action
    return None

def _current_node_scope_exit_reconciliation_blockers(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], frontier: dict[str, Any]) -> list[dict[str, Any]]:
    active_node_id = str(frontier.get('active_node_id') or '')
    if not active_node_id:
        return []
    flags = run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {}
    blockers: list[dict[str, Any]] = []
    required_flags = (('current_node_result_disposition_recorded', 'PM disposition must remain recorded before node exit'), ('current_node_result_absorbed_by_pm', 'PM absorption must remain recorded before node exit'), ('node_reviewer_passed_result', 'Reviewer pass must remain recorded before node exit'))
    for flag, reason in required_flags:
        if not flags.get(flag):
            blockers.append({'kind': 'missing_current_node_exit_flag', 'flag': flag, 'reason': reason, 'scope_kind': 'current_node', 'node_id': active_node_id})
    batch = router._active_parallel_packet_batch(run_root, 'current_node')
    if isinstance(batch, dict) and str(batch.get('node_id') or '') == active_node_id:
        batch_status = str(batch.get('status') or '')
        if batch_status != 'reviewed':
            blockers.append({'kind': 'current_node_batch_not_reviewed', 'batch_id': batch.get('batch_id'), 'batch_status': batch_status, 'reason': 'current-node review-created obligations must close before node exit', 'scope_kind': 'current_node', 'node_id': active_node_id})
    for pending_return in router._pending_return_records(run_root, str(run_state['run_id'])):
        if router._pending_return_matches_active_node_scope(pending_return, frontier):
            blockers.append({'kind': 'pending_current_node_card_return', 'card_id': pending_return.get('card_id'), 'card_ids': pending_return.get('card_ids') or [], 'target_role': pending_return.get('target_role'), 'card_return_event': pending_return.get('card_return_event'), 'expected_return_path': pending_return.get('expected_return_path'), 'reason': 'current-node system-card ACK/read receipt must close before node exit', 'scope_kind': 'current_node', 'node_id': active_node_id})
    return blockers

__all__ = (
    '_current_node_pre_review_reconciliation_blockers',
    '_startup_pre_review_reconciliation_blockers',
    '_pre_review_reconciliation_blockers_for_trigger',
    '_current_scope_reconciliation_wait_still_blocked',
    '_next_local_obligation_before_passive_wait',
    '_current_node_scope_exit_reconciliation_blockers',
)
