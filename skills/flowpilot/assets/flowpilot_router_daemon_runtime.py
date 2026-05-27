"""Router daemon runtime helpers for FlowPilot router.

The public CLI and compatibility names stay in `flowpilot_router`.  This module
owns bounded daemon loop/status/lock lifecycle while using the router facade for
shared state writers, controller scheduling, and startup-driver decisions.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

from flowpilot_router_daemon_runtime_diagnostics import (
    _router_daemon_artifact_size_summary,
    _router_daemon_error_diagnostics,
)


def _resolve_run_root_target(router: ModuleType, project_root: Path, *, run_id: str | None=None, run_root: str | Path | None=None, bootstrap_state: dict[str, Any] | None=None) -> Path | None:
    if run_root:
        candidate = Path(run_root)
        return candidate if candidate.is_absolute() else project_root / candidate
    if run_id:
        return project_root / '.flowpilot' / 'runs' / str(run_id)
    return router.active_run_root(project_root, bootstrap_state)


def _append_router_daemon_event(router: ModuleType, run_root: Path, event: str, details: dict[str, Any] | None=None) -> None:
    path = router._router_daemon_event_log_path(run_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {'schema_version': router.ROUTER_DAEMON_EVENT_LOG_SCHEMA, 'event': event, 'recorded_at': router.utc_now(), 'details': details or {}}
    with path.open('a', encoding='utf-8') as handle:
        handle.write(router.json.dumps(record, sort_keys=True) + '\n')


def _acquire_router_daemon_lock(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, replace_stale: bool=False) -> dict[str, Any]:
    path = router._router_daemon_lock_path(run_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    now = router.utc_now()
    lock = {'schema_version': router.ROUTER_DAEMON_LOCK_SCHEMA, 'run_id': run_state.get('run_id'), 'run_root': router.project_relative(project_root, run_root), 'status': 'active', 'created_at': now, 'last_tick_at': now, 'tick_interval_seconds': router.ROUTER_DAEMON_TICK_SECONDS, 'stale_after_seconds': router.ROUTER_DAEMON_LOCK_STALE_SECONDS, 'owner': router._router_daemon_owner(), 'single_writer_lock': True}
    try:
        with path.open('x', encoding='utf-8') as handle:
            handle.write(router.json.dumps(lock, indent=2, sort_keys=True) + '\n')
            handle.flush()
            router.os.fsync(handle.fileno())
        router._append_router_daemon_event(run_root, 'router_daemon_lock_acquired', {'lock_path': router.project_relative(project_root, path)})
        return lock
    except FileExistsError:
        existing = router.read_json_if_exists(path)
        existing_liveness = router._router_daemon_lock_liveness(existing)
        if existing_liveness.get('live') or router._router_daemon_lock_has_live_owner(existing_liveness):
            raise router.RouterError('router daemon lock is already active for this run; attach to the existing daemon instead of starting a second writer')
        if existing.get('status') == 'active' and (not replace_stale):
            raise router.RouterError('router daemon lock is stale; restart with --replace-stale-lock so stale ownership is explicit')
        lock['replaced_lock'] = {'status': existing.get('status'), 'created_at': existing.get('created_at'), 'last_tick_at': existing.get('last_tick_at'), 'owner': existing.get('owner')}
        router.write_json(path, lock)
        router._append_router_daemon_event(run_root, 'router_daemon_lock_replaced', {'lock_path': router.project_relative(project_root, path), 'previous_status': existing.get('status')})
        return lock


def _refresh_router_daemon_lock(router: ModuleType, project_root: Path, run_root: Path) -> dict[str, Any]:
    path = router._router_daemon_lock_path(run_root)
    lock = router.read_json_if_exists(path)
    if lock.get('schema_version') != router.ROUTER_DAEMON_LOCK_SCHEMA:
        raise router.RouterError('router daemon lock is missing or invalid')
    if lock.get('status') != 'active':
        return lock
    lock['status'] = 'active'
    lock['last_tick_at'] = router.utc_now()
    lock['owner'] = router._router_daemon_owner()
    router.write_json(path, lock)
    return lock


def _release_router_daemon_lock(router: ModuleType, project_root: Path, run_root: Path, *, reason: str, status: str='released') -> dict[str, Any]:
    path = router._router_daemon_lock_path(run_root)
    lock = router.read_json_if_exists(path)
    if lock.get('schema_version') != router.ROUTER_DAEMON_LOCK_SCHEMA:
        return {'status': 'missing', 'reason': reason}
    lock['status'] = status
    lock['released_at'] = router.utc_now()
    lock['release_reason'] = reason
    lock['owner'] = router._router_daemon_owner()
    router.write_json(path, lock)
    router._append_router_daemon_event(run_root, 'router_daemon_lock_released', {'status': status, 'reason': reason})
    return lock


def _write_router_daemon_status(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, lifecycle_status: str, current_action: dict[str, Any] | None=None, recovery_hints: list[str] | None=None, lock: dict[str, Any] | None=None, error: dict[str, Any] | None=None) -> dict[str, Any]:
    lock_payload = lock if isinstance(lock, dict) else router.read_json_if_exists(router._router_daemon_lock_path(run_root))
    lock_liveness = router._router_daemon_lock_liveness(lock_payload)
    effective_lifecycle_status = lifecycle_status
    if lifecycle_status in {'daemon_active', 'daemon_observing', 'daemon_starting'}:
        if lock_payload.get('status') == 'error':
            effective_lifecycle_status = 'daemon_error'
        elif not router._router_daemon_lock_has_live_owner(lock_liveness):
            effective_lifecycle_status = 'daemon_stale_or_missing'
    terminal_mode = router._terminal_lifecycle_mode(run_state)
    if terminal_mode:
        current_action = None
    current_wait = router._pending_wait_summary(run_state, project_root=project_root)
    standby_required = router._should_refresh_continuous_standby_row(run_state, lifecycle_status=effective_lifecycle_status, current_action=current_action)
    if terminal_mode:
        standby_required = False
    standby_entry = None
    if standby_required:
        standby_entry = router._ensure_continuous_standby_controller_action(project_root, run_root, run_state, current_wait)
    lock_owner = lock_liveness.get('owner') if isinstance(lock_liveness.get('owner'), dict) else {}
    controller_ledger_summary = router._controller_action_ledger_summary(run_root)
    router_scheduler_summary = router._router_scheduler_ledger_summary(run_root)
    heartbeat_monitor = router._router_daemon_heartbeat_monitor(lock_payload, lock_liveness, status_exists=True, status_ok=True)
    current_work = router._derive_current_work(project_root, run_root, run_state, current_wait=current_wait, current_action=current_action, controller_ledger=controller_ledger_summary)
    status = {'schema_version': router.ROUTER_DAEMON_STATUS_SCHEMA, 'run_id': run_state.get('run_id'), 'run_root': router.project_relative(project_root, run_root), 'daemon_mode_enabled': bool(run_state.get('daemon_mode_enabled')), 'lifecycle_status': 'terminal_stopped' if terminal_mode else effective_lifecycle_status, 'run_lifecycle_status': terminal_mode, 'tick_interval_seconds': router.ROUTER_DAEMON_TICK_SECONDS, 'last_tick_at': router.utc_now(), 'process': lock_owner or router._router_daemon_owner(), 'lock': {'path': router.project_relative(project_root, router._router_daemon_lock_path(run_root)), 'status': lock_payload.get('status'), 'last_tick_at': lock_payload.get('last_tick_at'), 'live': lock_liveness['live'], 'process_live': lock_liveness['process_live'], 'fresh': lock_liveness['fresh'], 'age_seconds': lock_liveness['age_seconds'], 'reasons': lock_liveness['reasons']}, 'heartbeat': heartbeat_monitor, 'daemon_live': bool(bool(run_state.get('daemon_mode_enabled')) and lock_liveness['live']), 'current_work': current_work, 'current_wait': current_wait, 'continuous_standby_task': (standby_entry.get('action') or {}).get('continuous_standby_task') if isinstance(standby_entry, dict) else router._continuous_standby_task_payload(project_root, run_root, current_wait) if standby_required else None, 'current_action': {'action_type': current_action.get('action_type'), 'label': current_action.get('label'), 'controller_action_id': current_action.get('controller_action_id'), 'controller_projection_kind': router._controller_action_projection_kind(current_action), 'ordinary_controller_work_row': not router._action_is_passive_wait_status(current_action), 'apply_required': current_action.get('apply_required'), 'relay_allowed': current_action.get('relay_allowed')} if isinstance(current_action, dict) else None, 'controller_action_ledger': controller_ledger_summary, 'router_scheduler_ledger': router_scheduler_summary, 'break_glass_reminder': router._controller_break_glass_reminder(), 'router_internal_ownership_ledger_visible_to_controller': False, 'recovery_hints': recovery_hints or [], 'error': error, 'controller_should_watch_action_ledger': True, 'router_owns_waiting': True}
    router.write_json(router._router_daemon_status_path(run_root), status)
    run_state['router_daemon_status_path'] = router.project_relative(project_root, router._router_daemon_status_path(run_root))
    return status


def _router_daemon_resume_recovery_summary(router: ModuleType, project_root: Path, run_root: Path) -> dict[str, Any]:
    lock_path = router._router_daemon_lock_path(run_root)
    status_path = router._router_daemon_status_path(run_root)
    ledger_path = router._controller_action_ledger_path(run_root)
    lock = router.read_json_if_exists(lock_path)
    status = router.read_json_if_exists(status_path)
    run_state = router.read_json_if_exists(router.run_state_path(run_root))
    terminal_mode = router._terminal_lifecycle_mode(run_state)
    lock_liveness = router._router_daemon_lock_liveness(lock)
    lock_live = bool(lock_liveness.get('live'))
    active_owner_live = router._router_daemon_lock_has_live_owner(lock_liveness)
    heartbeat_monitor = router._router_daemon_heartbeat_monitor(lock, lock_liveness, status_exists=status_path.exists(), status_ok=status.get('schema_version') == router.ROUTER_DAEMON_STATUS_SCHEMA)
    ledger_exists = ledger_path.exists()
    if terminal_mode:
        decision = 'terminal_no_restart_router_daemon'
    elif active_owner_live:
        decision = 'attach_controller_to_live_daemon'
    else:
        decision = 'restart_router_daemon_from_current_state'
    return {'schema_version': 'flowpilot.router_daemon_resume_recovery.v1', 'router_daemon_status_path': router.project_relative(project_root, status_path), 'router_daemon_status_exists': status_path.exists(), 'router_daemon_lock_path': router.project_relative(project_root, lock_path), 'router_daemon_lock_exists': lock_path.exists(), 'router_daemon_lock_live': lock_live, 'router_daemon_owner_process_live': bool(lock_liveness.get('process_live')), 'router_daemon_active_owner_live': active_owner_live, 'router_daemon_lock_status': lock.get('status'), 'router_daemon_last_tick_at': lock.get('last_tick_at') or status.get('last_tick_at'), 'heartbeat': heartbeat_monitor, 'controller_action_ledger_path': router.project_relative(project_root, ledger_path), 'controller_action_ledger_exists': ledger_exists, 'controller_action_ledger_rescanned': True, 'decision': decision, 'terminal_lifecycle_status': terminal_mode, 'restart_only_after_controller_liveness_check_finds_dead': not bool(terminal_mode), 'never_start_second_router_writer': True}


def _ensure_daemon_runtime_state(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, lifecycle_status: str='manual_router_loop') -> dict[str, Any]:
    router._runtime_dir(run_root).mkdir(parents=True, exist_ok=True)
    router._controller_actions_dir(run_root).mkdir(parents=True, exist_ok=True)
    router._controller_receipts_dir(run_root).mkdir(parents=True, exist_ok=True)
    router._ensure_controller_action_ledger(project_root, run_root, run_state)
    router._ensure_router_scheduler_ledger(project_root, run_root, run_state)
    router._ensure_router_ownership_ledger(project_root, run_root, run_state)
    return router._write_router_daemon_status(project_root, run_root, run_state, lifecycle_status=lifecycle_status, recovery_hints=['start_router_daemon_if_daemon_mode_is_required'])


def _formal_router_daemon_ready(router: ModuleType, project_root: Path, run_root: Path) -> bool:
    lock = router.read_json_if_exists(router._router_daemon_lock_path(run_root))
    status = router.read_json_if_exists(router._router_daemon_status_path(run_root))
    ledger = router.read_json_if_exists(router._controller_action_ledger_path(run_root))
    return router._router_daemon_lock_is_live(lock) and status.get('schema_version') == router.ROUTER_DAEMON_STATUS_SCHEMA and bool(status.get('daemon_mode_enabled')) and (status.get('tick_interval_seconds') == router.ROUTER_DAEMON_TICK_SECONDS) and bool((status.get('lock') or {}).get('live')) and (ledger.get('schema_version') == router.CONTROLLER_ACTION_LEDGER_SCHEMA) and (status.get('run_root') == router.project_relative(project_root, run_root))


def _tail_text(router: ModuleType, path: Path, *, max_chars: int=2000) -> str:
    try:
        text = path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return ''
    return text[-max_chars:]


def _spawn_startup_router_daemon_process(router: ModuleType, project_root: Path, run_root: Path) -> dict[str, Any]:
    router._runtime_dir(run_root).mkdir(parents=True, exist_ok=True)
    stdout_path = router._runtime_dir(run_root) / 'router_daemon.startup.out.txt'
    stderr_path = router._runtime_dir(run_root) / 'router_daemon.startup.err.txt'
    command = [router.sys.executable, str(Path(router.__file__).resolve()), '--root', str(project_root), '--json', 'daemon', '--run-root', router.project_relative(project_root, run_root)]
    creationflags = 0
    start_new_session = router.os.name != 'nt'
    if router.os.name == 'nt':
        start_new_session = False
        creationflags = getattr(router.subprocess, 'CREATE_NEW_PROCESS_GROUP', 0) | getattr(router.subprocess, 'DETACHED_PROCESS', 0) | getattr(router.subprocess, 'CREATE_NO_WINDOW', 0)
    stdout_handle = stdout_path.open('a', encoding='utf-8')
    stderr_handle = stderr_path.open('a', encoding='utf-8')
    try:
        process = router.subprocess.Popen(command, cwd=str(project_root), stdin=router.subprocess.DEVNULL, stdout=stdout_handle, stderr=stderr_handle, start_new_session=start_new_session, creationflags=creationflags)
    finally:
        stdout_handle.close()
        stderr_handle.close()
    router._append_router_daemon_event(run_root, 'formal_router_daemon_process_spawned', {'pid': process.pid, 'stdout_path': router.project_relative(project_root, stdout_path), 'stderr_path': router.project_relative(project_root, stderr_path)})
    return {'pid': process.pid, 'command': command, 'stdout_path': router.project_relative(project_root, stdout_path), 'stderr_path': router.project_relative(project_root, stderr_path)}


def _start_or_attach_formal_router_daemon(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    lock_path = router._router_daemon_lock_path(run_root)
    status_path = router._router_daemon_status_path(run_root)
    ledger_path = router._controller_action_ledger_path(run_root)
    router._ensure_daemon_runtime_state(project_root, run_root, run_state, lifecycle_status='formal_daemon_starting')
    if router._formal_router_daemon_ready(project_root, run_root):
        attached_existing = True
        spawn_info: dict[str, Any] | None = None
    else:
        lock = router.read_json_if_exists(lock_path)
        if router._router_daemon_lock_is_live(lock):
            raise router.RouterError('cannot start Controller core: a live Router daemon lock exists but startup readiness artifacts are incomplete')
        if lock.get('status') == 'active':
            raise router.RouterError('cannot start Controller core: Router daemon lock is stale; repair or replace stale lock explicitly')
        try:
            spawn_info = router._spawn_startup_router_daemon_process(project_root, run_root)
        except Exception as exc:
            run_state['daemon_mode_enabled'] = False
            run_state['flags']['router_daemon_start_failed'] = True
            router.append_history(run_state, 'formal_router_daemon_start_failed', {'error': str(exc)})
            router.save_run_state(run_root, run_state)
            raise router.RouterError(f'formal Router daemon failed to start: {exc}') from exc
        attached_existing = False
        deadline = router.time.monotonic() + router.ROUTER_DAEMON_STARTUP_TIMEOUT_SECONDS
        while router.time.monotonic() < deadline:
            if router._formal_router_daemon_ready(project_root, run_root):
                break
            router.time.sleep(router.ROUTER_DAEMON_STARTUP_POLL_SECONDS)
        if not router._formal_router_daemon_ready(project_root, run_root):
            run_state['daemon_mode_enabled'] = False
            run_state['flags']['router_daemon_start_failed'] = True
            stderr_tail = router._tail_text(router.resolve_project_path(project_root, str(spawn_info.get('stderr_path') or '')))
            router.append_history(run_state, 'formal_router_daemon_start_timeout', {'timeout_seconds': router.ROUTER_DAEMON_STARTUP_TIMEOUT_SECONDS, 'stderr_tail': stderr_tail})
            router.save_run_state(run_root, run_state)
            raise router.RouterError('formal Router daemon failed readiness check before Controller core load' + (f'; stderr tail: {stderr_tail}' if stderr_tail else ''))
    latest_state, latest_root = router.load_run_state_from_run_root(project_root, run_root)
    if latest_state is not None and latest_root is not None:
        run_root = latest_root
        run_state.clear()
        run_state.update(latest_state)
    run_state['daemon_mode_enabled'] = True
    run_state['router_daemon_status_path'] = router.project_relative(project_root, status_path)
    run_state['controller_action_ledger_path'] = router.project_relative(project_root, ledger_path)
    run_state['flags']['formal_router_daemon_started'] = True
    run_state['flags']['router_daemon_start_failed'] = False
    router.append_history(run_state, 'formal_router_daemon_ready_before_controller_core', {'attached_existing_daemon': attached_existing, 'lock_path': router.project_relative(project_root, lock_path), 'status_path': router.project_relative(project_root, status_path), 'controller_action_ledger_path': router.project_relative(project_root, ledger_path)})
    router.save_run_state(run_root, run_state)
    return {'router_daemon_ready': True, 'attached_existing_daemon': attached_existing, 'spawn_info': spawn_info, 'lock_path': router.project_relative(project_root, lock_path), 'status_path': router.project_relative(project_root, status_path), 'controller_action_ledger_path': router.project_relative(project_root, ledger_path)}


def _mark_router_daemon_terminal(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, reason: str) -> dict[str, Any]:
    lock = router._release_router_daemon_lock(project_root, run_root, reason=reason, status='terminal_stopped')
    return router._write_router_daemon_status(project_root, run_root, run_state, lifecycle_status='terminal_stopped', lock=lock, recovery_hints=[])


def _router_daemon_can_continue_after_enqueued_action(router: ModuleType, action: dict[str, Any]) -> bool:
    progress_class = action.get('router_scheduler_progress_class') or router._router_scheduler_progress_class(action)
    if progress_class in {'parallel_obligation', 'local_dependency'}:
        return router._action_is_startup_scoped(action)
    barrier = action.get('router_scheduler_barrier_kind') or router._router_scheduler_barrier_kind(action)
    if barrier and barrier != 'none':
        return False
    action_type = str(action.get('action_type') or '')
    if action_type in {'sync_display_plan', 'confirm_controller_core_boundary', 'write_startup_mechanical_audit', 'write_display_surface_status'}:
        return router._action_is_startup_scoped(action)
    if action_type in {'deliver_system_card', 'deliver_system_card_bundle'}:
        return router._action_is_startup_async_delivery(action)
    return False


def _router_daemon_fill_action_queue(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, max_actions: int | None=None) -> dict[str, Any]:
    if max_actions is None:
        max_actions = router.ROUTER_DAEMON_MAX_QUEUE_ACTIONS_PER_TICK
    queued_actions: list[dict[str, Any]] = []
    stop_reason = 'no_action'
    current_action: dict[str, Any] | None = None
    for _index in range(max_actions):
        current_action = router.compute_controller_action(project_root, run_state, run_root)
        if not isinstance(current_action, dict):
            stop_reason = 'no_action'
            break
        current_action = router._prepare_router_scheduled_action(project_root, run_root, run_state, current_action)
        entry = router._write_controller_action_entry(project_root, run_root, run_state, current_action)
        projection_kind = router._controller_action_projection_kind(current_action)
        queued_actions.append({'action_type': current_action.get('action_type'), 'controller_action_id': entry.get('action_id'), 'controller_projection_kind': projection_kind, 'ordinary_controller_work_row': not router._action_is_passive_wait_status(current_action), 'router_scheduler_row_id': current_action.get('router_scheduler_row_id'), 'barrier_kind': current_action.get('router_scheduler_barrier_kind'), 'scope_kind': current_action.get('scope_kind'), 'scope_id': current_action.get('scope_id')})
        if router._action_is_passive_wait_status(current_action):
            router.append_history(run_state, 'router_projected_passive_wait_status_without_controller_work_row', {'action_type': current_action.get('action_type'), 'controller_action_id': entry.get('action_id'), 'router_scheduler_row_id': current_action.get('router_scheduler_row_id'), 'scope_kind': current_action.get('scope_kind'), 'scope_id': current_action.get('scope_id')})
            router.save_run_state(run_root, run_state)
            stop_reason = 'passive_wait_status'
            break
        if not router._router_daemon_can_continue_after_enqueued_action(current_action):
            stop_reason = 'barrier'
            break
        pending = run_state.get('pending_action')
        if isinstance(pending, dict) and (pending.get('controller_action_id') == entry.get('action_id') or pending.get('router_scheduler_row_id') == current_action.get('router_scheduler_row_id') or pending.get('label') == current_action.get('label')):
            run_state['pending_action'] = None
            router.append_history(run_state, 'router_daemon_deferred_nonblocking_controller_row', {'action_type': current_action.get('action_type'), 'controller_action_id': entry.get('action_id'), 'router_scheduler_row_id': current_action.get('router_scheduler_row_id'), 'scope_kind': current_action.get('scope_kind'), 'scope_id': current_action.get('scope_id')})
            router.save_run_state(run_root, run_state)
        else:
            stop_reason = 'pending_action_changed'
            break
    else:
        stop_reason = 'max_actions_per_tick'
    return {'queued_count': len(queued_actions), 'queued_actions': queued_actions, 'stop_reason': stop_reason, 'current_action': current_action}


def _router_daemon_tick_requests_immediate_next_tick(router: ModuleType, tick: dict[str, Any]) -> bool:
    reason = str(tick.get('queue_stop_reason') or '').strip()
    if not reason and isinstance(tick.get('startup_schedule'), dict):
        reason = str(tick['startup_schedule'].get('queue_stop_reason') or '').strip()
    return reason == 'max_actions_per_tick'


def _router_daemon_tick(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, observe_only: bool) -> dict[str, Any]:
    lock = router._refresh_router_daemon_lock(project_root, run_root)
    if lock.get('status') != 'active':
        run_state['daemon_mode_enabled'] = False
        status = router._write_router_daemon_status(project_root, run_root, run_state, lifecycle_status='daemon_stopped', current_action=run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else None, lock=lock)
        router.save_run_state(run_root, run_state)
        return {'tick_at': status['last_tick_at'], 'observe_only': observe_only, 'lock_status': lock.get('status'), 'release_reason': lock.get('release_reason'), 'terminal': True}
    latest_state, latest_root = router.load_run_state_from_run_root(project_root, run_root)
    if latest_state is None or latest_root is None:
        raise router.RouterError('router daemon tick requires bound run state')
    run_root = latest_root
    run_state.clear()
    run_state.update(latest_state)
    if router._terminal_lifecycle_mode(run_state):
        run_state['daemon_mode_enabled'] = False
        lock = router._release_router_daemon_lock(project_root, run_root, reason='terminal_lifecycle_observed_by_daemon_tick', status='terminal_stopped')
        status = router._write_router_daemon_status(project_root, run_root, run_state, lifecycle_status='terminal_stopped', current_action=None, lock=lock)
        router.save_run_state(run_root, run_state)
        return {'tick_at': status['last_tick_at'], 'observe_only': observe_only, 'lock_status': lock.get('status'), 'terminal': True, 'terminal_fence_observed': True}
    run_state['daemon_mode_enabled'] = True
    router._ensure_daemon_runtime_state(project_root, run_root, run_state, lifecycle_status='daemon_active')
    startup_flag_fold = router._fold_stable_startup_role_flags_from_bootstrap(project_root, run_root, run_state)
    receipt_summary = router._reconcile_controller_receipts(project_root, run_root, run_state, scheduler_fold_owner='daemon')
    scheduled_reconciliation = router._reconcile_scheduled_controller_action_receipts(project_root, run_root, run_state)
    boundary_projection = router._reconcile_controller_boundary_confirmation_projection(project_root, run_root, run_state, source='router_daemon_tick_projection_barrier')
    current_action = run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else None
    bootstrap = router.load_bootstrap_state(project_root, create_if_missing=False)
    if not observe_only and router._startup_daemon_controls_bootstrap(bootstrap):
        startup_schedule = router._startup_daemon_schedule_bootloader_action(project_root, run_root, run_state, lock=lock, source='router_daemon_tick')
        action = startup_schedule.get('action') if isinstance(startup_schedule.get('action'), dict) else None
        router.save_run_state(run_root, run_state)
        return {'tick_at': startup_schedule.get('tick_at') or router.utc_now(), 'observe_only': False, 'action_type': action.get('action_type') if isinstance(action, dict) else None, 'controller_action_id': startup_schedule.get('controller_action_id'), 'waiting_for_controller_core': False, 'startup_driver_active': True, 'startup_flag_fold': startup_flag_fold, 'receipt_summary': receipt_summary, 'scheduled_reconciliation': scheduled_reconciliation, 'boundary_projection': boundary_projection, 'startup_schedule': startup_schedule, 'queue_stop_reason': startup_schedule.get('queue_stop_reason'), 'terminal': bool(startup_schedule.get('terminal'))}
    if observe_only:
        if isinstance(current_action, dict):
            router._write_controller_action_entry(project_root, run_root, run_state, current_action)
        status = router._write_router_daemon_status(project_root, run_root, run_state, lifecycle_status='daemon_observing', current_action=current_action, lock=lock)
        router.save_run_state(run_root, run_state)
        return {'tick_at': status['last_tick_at'], 'observe_only': True, 'action_type': current_action.get('action_type') if isinstance(current_action, dict) else None, 'controller_action_id': current_action.get('controller_action_id') if isinstance(current_action, dict) else None, 'startup_flag_fold': startup_flag_fold, 'receipt_summary': receipt_summary, 'scheduled_reconciliation': scheduled_reconciliation, 'boundary_projection': boundary_projection, 'terminal': bool(status.get('run_lifecycle_status'))}
    queue_result = router._router_daemon_fill_action_queue(project_root, run_root, run_state)
    current_action = queue_result.get('current_action') if isinstance(queue_result.get('current_action'), dict) else None
    status = router._write_router_daemon_status(project_root, run_root, run_state, lifecycle_status='daemon_active', current_action=current_action, lock=lock)
    router.save_run_state(run_root, run_state)
    return {'tick_at': status['last_tick_at'], 'observe_only': False, 'action_type': current_action.get('action_type') if isinstance(current_action, dict) else None, 'controller_action_id': current_action.get('controller_action_id') if isinstance(current_action, dict) else None, 'startup_flag_fold': startup_flag_fold, 'receipt_summary': receipt_summary, 'scheduled_reconciliation': scheduled_reconciliation, 'boundary_projection': boundary_projection, 'queued_count': queue_result.get('queued_count'), 'queued_actions': queue_result.get('queued_actions'), 'queue_stop_reason': queue_result.get('stop_reason'), 'terminal': bool(status.get('run_lifecycle_status'))}


def run_router_daemon(router: ModuleType, project_root: Path, *, max_ticks: int | None=None, observe_only: bool=False, replace_stale_lock: bool=False, release_lock_on_exit: bool=False, run_id: str | None=None, run_root: str | Path | None=None) -> dict[str, Any]:
    if max_ticks is not None and max_ticks < 1:
        raise router.RouterError('router daemon requires max_ticks >= 1 when provided')
    project_root = project_root.resolve()
    bootstrap = router.load_bootstrap_state(project_root, create_if_missing=False)
    target_run_root = router._resolve_run_root_target(project_root, run_id=run_id, run_root=run_root, bootstrap_state=bootstrap)
    if target_run_root is None:
        raise router.RouterError('router daemon requires an active FlowPilot run')
    run_state, run_root = router.load_run_state_from_run_root(project_root, target_run_root)
    if run_state is None or run_root is None:
        raise router.RouterError('router daemon requires an active FlowPilot run')
    if router._terminal_lifecycle_mode(run_state):
        run_state['daemon_mode_enabled'] = False
        status = router._mark_router_daemon_terminal(project_root, run_root, run_state, reason='daemon_start_saw_terminal_lifecycle')
        router.save_run_state(run_root, run_state)
        return {'ok': True, 'command': 'daemon', 'run_id': run_state.get('run_id'), 'run_root': router.project_relative(project_root, run_root), 'tick_interval_seconds': router.ROUTER_DAEMON_TICK_SECONDS, 'tick_count': 0, 'ticks': [], 'observe_only': observe_only, 'lock_path': router.project_relative(project_root, router._router_daemon_lock_path(run_root)), 'lock_status': (router.read_json_if_exists(router._router_daemon_lock_path(run_root)) or {}).get('status'), 'status_path': router.project_relative(project_root, router._router_daemon_status_path(run_root)), 'daemon_status': status, 'terminal': True}
    run_state['daemon_mode_enabled'] = True
    lock = router._acquire_router_daemon_lock(project_root, run_root, run_state, replace_stale=replace_stale_lock)
    ticks: list[dict[str, Any]] = []
    error: Exception | None = None
    runtime_initialized = False
    try:
        while True:
            try:
                if not runtime_initialized:
                    router._ensure_daemon_runtime_state(project_root, run_root, run_state, lifecycle_status='daemon_starting')
                    router.save_run_state(run_root, run_state)
                    runtime_initialized = True
                tick = router._router_daemon_tick(project_root, run_root, run_state, observe_only=observe_only)
            except router.RouterLedgerWriteInProgress as exc:
                nested_exc: Any = None
                status: dict[str, Any] | None = None
                try:
                    lock = router._refresh_router_daemon_lock(project_root, run_root)
                    status = router._write_router_daemon_status(project_root, run_root, run_state, lifecycle_status='daemon_waiting_for_runtime_ledger_write', current_action=run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else None, recovery_hints=['runtime_ledger_write_in_progress_retry_next_daemon_tick', 'if_the_write_lock_becomes_stale_treat_the_ledger_as_corrupt_and_repair_it'], lock=lock)
                    router.save_run_state(run_root, run_state)
                except router.RouterLedgerWriteInProgress as status_exc:
                    nested_exc = status_exc
                tick = {'tick_at': (status or {}).get('last_tick_at') or router.utc_now(), 'observe_only': observe_only, 'deferred': True, 'defer_reason': 'runtime_ledger_write_in_progress', 'ledger_path': router.project_relative(project_root, exc.path), 'write_lock': exc.write_lock, 'terminal': False}
                if isinstance(nested_exc, router.RouterLedgerWriteInProgress):
                    tick.update({'nested_defer_reason': 'runtime_ledger_write_status_save_in_progress', 'nested_ledger_path': router.project_relative(project_root, nested_exc.path), 'nested_write_lock': nested_exc.write_lock})
            ticks.append(tick)
            if tick.get('terminal'):
                break
            if max_ticks is not None and len(ticks) >= max_ticks:
                break
            if router._router_daemon_tick_requests_immediate_next_tick(tick):
                continue
            router.time.sleep(router.ROUTER_DAEMON_TICK_SECONDS)
    except Exception as exc:
        error = exc
        lock = router._release_router_daemon_lock(project_root, run_root, reason=f'daemon_error:{type(exc).__name__}', status='error')
        diagnostics = router._router_daemon_error_diagnostics(project_root, run_root, run_state, exc)
        router._append_router_daemon_event(run_root, 'router_daemon_error', {'error_type': type(exc).__name__, 'error_message': str(exc), 'diagnostics': diagnostics})
        try:
            router._write_router_daemon_status(project_root, run_root, run_state, lifecycle_status='daemon_error', current_action=run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else None, recovery_hints=['repair_or_replace_invalid_runtime_ledger_before_restarting_router_daemon', 'restart_router_daemon_with_replace_stale_lock_after_repair_if_needed'], lock=lock, error=diagnostics)
            router.save_run_state(run_root, run_state)
        except Exception:
            pass
        raise
    finally:
        if error is None and (release_lock_on_exit or (ticks and ticks[-1].get('terminal'))):
            existing_lock = router.read_json_if_exists(router._router_daemon_lock_path(run_root))
            if existing_lock.get('status') == 'active':
                final_status = 'terminal_stopped' if ticks and ticks[-1].get('terminal') else 'released'
                lock = router._release_router_daemon_lock(project_root, run_root, reason='daemon_loop_exit', status=final_status)
            else:
                lock = existing_lock
                final_status = str(lock.get('status') or 'released')
            try:
                router._write_router_daemon_status(project_root, run_root, run_state, lifecycle_status=final_status, current_action=run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else None, lock=lock)
                router.save_run_state(run_root, run_state)
            except router.RouterLedgerWriteInProgress:
                pass
    status = router.read_json_if_exists(router._router_daemon_status_path(run_root))
    return {'ok': True, 'command': 'daemon', 'run_id': run_state.get('run_id'), 'run_root': router.project_relative(project_root, run_root), 'tick_interval_seconds': router.ROUTER_DAEMON_TICK_SECONDS, 'tick_count': len(ticks), 'ticks': ticks, 'observe_only': observe_only, 'lock_path': router.project_relative(project_root, router._router_daemon_lock_path(run_root)), 'lock_status': (router.read_json_if_exists(router._router_daemon_lock_path(run_root)) or {}).get('status'), 'status_path': router.project_relative(project_root, router._router_daemon_status_path(run_root)), 'daemon_status': status}


def stop_router_daemon(router: ModuleType, project_root: Path, *, reason: str='manual_stop', run_id: str | None=None, run_root: str | Path | None=None) -> dict[str, Any]:
    project_root = project_root.resolve()
    bootstrap = router.load_bootstrap_state(project_root, create_if_missing=False)
    target_run_root = router._resolve_run_root_target(project_root, run_id=run_id, run_root=run_root, bootstrap_state=bootstrap)
    if target_run_root is None:
        raise router.RouterError('router daemon stop requires an active FlowPilot run')
    run_state, run_root = router.load_run_state_from_run_root(project_root, target_run_root)
    if run_state is None or run_root is None:
        raise router.RouterError('router daemon stop requires an active FlowPilot run')
    run_state['daemon_mode_enabled'] = False
    lock = router._release_router_daemon_lock(project_root, run_root, reason=reason, status='released')
    status = router._write_router_daemon_status(project_root, run_root, run_state, lifecycle_status='daemon_stopped', current_action=run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else None, lock=lock)
    router.save_run_state(run_root, run_state)
    return {'ok': True, 'command': 'daemon-stop', 'run_id': run_state.get('run_id'), 'lock_status': lock.get('status'), 'status_path': router.project_relative(project_root, router._router_daemon_status_path(run_root)), 'daemon_status': status}
