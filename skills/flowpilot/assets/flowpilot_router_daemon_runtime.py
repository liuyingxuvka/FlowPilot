"""Router daemon runtime helpers for FlowPilot router.

The public CLI and router names stay in `flowpilot_router`.  This module
owns bounded daemon loop/status/lock lifecycle while using the router facade for
shared state writers, controller scheduling, and startup-driver decisions.
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from types import ModuleType
from typing import Any

from flowpilot_router_daemon_runtime_diagnostics import (
    _router_daemon_artifact_size_summary,
    _router_daemon_error_diagnostics,
)
from flowpilot_router_daemon_runtime_lock import (
    _acquire_router_daemon_lock,
    _append_router_daemon_event,
    _refresh_router_daemon_lock,
    _request_router_daemon_stop,
    _release_router_daemon_lock,
    _resolve_run_root_target,
)
from flowpilot_router_io_json import write_json_if_changed as _write_json_if_changed
from flowpilot_router_runtime_state_persistence import _run_state_snapshot_hash

_ROUTER_DAEMON_ANOMALY_SAMPLE_LIMIT = 16
_ROUTER_DAEMON_TICK_RESULT_FIELDS = (
    'tick_at',
    'observe_only',
    'action_type',
    'controller_action_id',
    'waiting_for_controller_core',
    'startup_driver_active',
    'queued_count',
    'queued_actions',
    'queue_stop_reason',
    'lock_status',
    'release_reason',
    'terminal',
    'terminal_fence_observed',
    'stop_requested',
    'stop_reason',
    'deferred',
    'defer_reason',
    'ledger_path',
    'nested_defer_reason',
    'nested_ledger_path',
    'semantic_state_changed',
    'projection_changed',
    'frontier_advanced',
    'semantic_changed',
    'state_written',
    'change_reasons',
)


def _router_daemon_semantic_fingerprint(
    router: ModuleType,
    run_root: Path,
    run_state: dict[str, Any],
) -> dict[str, str]:
    fingerprint = {'run_state': _run_state_snapshot_hash(run_state)}
    paths = {
        'controller_action_ledger': router._controller_action_ledger_path(run_root),
        'router_scheduler_ledger': router._router_scheduler_ledger_path(run_root),
        'router_ownership_ledger': router._router_ownership_ledger_path(run_root),
        'execution_frontier': run_root / 'execution_frontier.json',
    }
    for name, path in paths.items():
        try:
            body = path.read_bytes()
        except OSError:
            body = b''
        fingerprint[name] = hashlib.sha256(body).hexdigest()
    return fingerprint


def _classify_router_daemon_tick(
    router: ModuleType,
    run_root: Path,
    run_state: dict[str, Any],
    tick: dict[str, Any],
    *,
    before: dict[str, str],
    state_written: bool,
) -> dict[str, Any]:
    after = _router_daemon_semantic_fingerprint(router, run_root, run_state)
    changed = [name for name, digest in after.items() if digest != before.get(name)]
    tick['semantic_state_changed'] = 'run_state' in changed
    tick['projection_changed'] = any(
        name in changed
        for name in (
            'controller_action_ledger',
            'router_scheduler_ledger',
            'router_ownership_ledger',
        )
    )
    tick['frontier_advanced'] = 'execution_frontier' in changed
    tick['semantic_changed'] = bool(changed)
    tick['state_written'] = bool(state_written)
    tick['change_reasons'] = changed
    return tick


def _compact_router_daemon_tick(tick: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(tick, dict):
        return None
    return {field: tick.get(field) for field in _ROUTER_DAEMON_TICK_RESULT_FIELDS if field in tick}


def _compact_router_daemon_status(status: dict[str, Any]) -> dict[str, Any]:
    lock = status.get('lock') if isinstance(status.get('lock'), dict) else {}
    control = status.get('control_projection') if isinstance(status.get('control_projection'), dict) else {}
    current_action = status.get('current_action') if isinstance(status.get('current_action'), dict) else {}
    return {
        'schema_version': status.get('schema_version'),
        'run_id': status.get('run_id'),
        'lifecycle_status': status.get('lifecycle_status'),
        'run_lifecycle_status': status.get('run_lifecycle_status'),
        'tick_interval_seconds': status.get('tick_interval_seconds'),
        'last_tick_at': status.get('last_tick_at'),
        'daemon_live': status.get('daemon_live'),
        'lock': {
            'status': lock.get('status'),
            'last_tick_at': lock.get('last_tick_at'),
            'live': lock.get('live'),
            'process_live': lock.get('process_live'),
            'fresh': lock.get('fresh'),
        },
        'control_projection': {
            'projection_kind': control.get('projection_kind'),
            'terminal_lifecycle_status': control.get('terminal_lifecycle_status'),
            'daemon_live': control.get('daemon_live'),
            'controller_stop_allowed': control.get('controller_stop_allowed'),
            'current_action_type': control.get('current_action_type'),
        },
        'current_action': {
            'action_type': current_action.get('action_type'),
            'controller_action_id': current_action.get('controller_action_id'),
            'controller_projection_kind': current_action.get('controller_projection_kind'),
        } if current_action else None,
        'error': bool(status.get('error')),
    }

def _router_daemon_control_projection(router: ModuleType, run_state: dict[str, Any], *, daemon_live: bool, current_wait: dict[str, Any], current_action: dict[str, Any] | None, controller_ledger: dict[str, Any] | None=None) -> dict[str, Any]:
    terminal_mode = router._terminal_lifecycle_mode(run_state)
    pending_action = run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else {}
    active_blocker = run_state.get('active_control_blocker') if isinstance(run_state.get('active_control_blocker'), dict) else {}
    current_action_type = str((current_action or {}).get('action_type') or '')
    pending_ids = []
    waiting_ids = []
    if isinstance(controller_ledger, dict):
        pending_ids = list(controller_ledger.get('pending_action_ids') or [])
        waiting_ids = list(controller_ledger.get('waiting_action_ids') or [])
    if terminal_mode == 'protocol_dead_end':
        projection_kind = 'protocol_dead_end'
    elif terminal_mode:
        projection_kind = 'terminal_stopped'
    elif pending_action.get('requires_user') or pending_action.get('requires_user_dialog_display_confirmation'):
        projection_kind = 'blocked_for_user'
    elif active_blocker or (current_wait.get('blocker') or {}).get('required') or (current_wait.get('reissue') or {}).get('required'):
        projection_kind = 'blocked_for_protocol'
    elif current_action_type and current_action_type != 'continuous_controller_standby':
        projection_kind = 'controller_work_ready'
    elif current_wait.get('waiting_for_role') or current_wait.get('action_type') == 'await_role_decision':
        projection_kind = 'waiting_for_role'
    elif daemon_live:
        projection_kind = 'live_daemon_standby'
    else:
        projection_kind = 'standby_no_live_daemon'
    return {
        'schema_version': 'flowpilot.router_control_projection.v1',
        'projection_kind': projection_kind,
        'terminal_lifecycle_status': terminal_mode,
        'daemon_live': bool(daemon_live),
        'controller_stop_allowed': projection_kind in {'terminal_stopped', 'protocol_dead_end'},
        'work_chain_liveness_claimed': False,
        'daemon_patrol_is_liveness_only': True,
        'old_route_state_liveness_rejected': True,
        'wait_agent_timeout_liveness_rejected': True,
        'authority_sources': ['runtime/router_daemon_status.json', 'runtime/router_daemon.lock', 'runtime/controller_action_ledger.json'],
        'active_control_blocker_id': active_blocker.get('blocker_id'),
        'current_action_type': current_action_type or None,
        'pending_action_ids': pending_ids,
        'waiting_action_ids': waiting_ids,
    }


def _write_router_daemon_status(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, lifecycle_status: str, current_action: dict[str, Any] | None=None, recovery_hints: list[str] | None=None, lock: dict[str, Any] | None=None, error: dict[str, Any] | None=None) -> dict[str, Any]:
    lock_payload = lock if isinstance(lock, dict) else router.read_daemon_critical_json_if_exists(router._router_daemon_lock_path(run_root))
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
    patrol_monitor = router._router_daemon_patrol_monitor(lock_payload, lock_liveness, status_exists=True, status_ok=True)
    current_work = router._derive_current_work(project_root, run_root, run_state, current_wait=current_wait, current_action=current_action, controller_ledger=controller_ledger_summary)
    daemon_live = bool(bool(run_state.get('daemon_mode_enabled')) and lock_liveness['live'])
    control_projection = _router_daemon_control_projection(router, run_state, daemon_live=daemon_live, current_wait=current_wait, current_action=current_action if isinstance(current_action, dict) else None, controller_ledger=controller_ledger_summary)
    status = {'schema_version': router.ROUTER_DAEMON_STATUS_SCHEMA, 'run_id': run_state.get('run_id'), 'run_root': router.project_relative(project_root, run_root), 'daemon_mode_enabled': bool(run_state.get('daemon_mode_enabled')), 'lifecycle_status': 'terminal_stopped' if terminal_mode else effective_lifecycle_status, 'run_lifecycle_status': terminal_mode, 'tick_interval_seconds': router.ROUTER_DAEMON_TICK_SECONDS, 'last_tick_at': router.utc_now(), 'process': lock_owner or router._router_daemon_owner(), 'lock': {'path': router.project_relative(project_root, router._router_daemon_lock_path(run_root)), 'status': lock_payload.get('status'), 'last_tick_at': lock_payload.get('last_tick_at'), 'live': lock_liveness['live'], 'process_live': lock_liveness['process_live'], 'fresh': lock_liveness['fresh'], 'age_seconds': lock_liveness['age_seconds'], 'reasons': lock_liveness['reasons']}, 'daemon_patrol': patrol_monitor, 'daemon_live': daemon_live, 'control_projection': control_projection, 'current_work': current_work, 'current_wait': current_wait, 'continuous_standby_task': (standby_entry.get('action') or {}).get('continuous_standby_task') if isinstance(standby_entry, dict) else router._continuous_standby_task_payload(project_root, run_root, current_wait) if standby_required else None, 'current_action': {'action_type': current_action.get('action_type'), 'label': current_action.get('label'), 'controller_action_id': current_action.get('controller_action_id'), 'controller_projection_kind': router._controller_action_projection_kind(current_action), 'ordinary_controller_work_row': not router._action_is_passive_wait_status(current_action), 'apply_required': current_action.get('apply_required'), 'relay_allowed': current_action.get('relay_allowed')} if isinstance(current_action, dict) else None, 'controller_action_ledger': controller_ledger_summary, 'router_scheduler_ledger': router_scheduler_summary, 'break_glass_reminder': router._controller_break_glass_reminder(), 'router_internal_ownership_ledger_visible_to_controller': False, 'recovery_hints': recovery_hints or [], 'error': error, 'controller_should_watch_action_ledger': True, 'router_owns_waiting': True}
    _write_json_if_changed(router._router_daemon_status_path(run_root), status)
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
    patrol_monitor = router._router_daemon_patrol_monitor(lock, lock_liveness, status_exists=status_path.exists(), status_ok=status.get('schema_version') == router.ROUTER_DAEMON_STATUS_SCHEMA)
    ledger_exists = ledger_path.exists()
    if terminal_mode:
        decision = 'terminal_no_restart_router_daemon'
    elif active_owner_live:
        decision = 'attach_controller_to_live_daemon'
    else:
        decision = 'restart_router_daemon_from_current_state'
    daemon_live = bool(bool(run_state.get('daemon_mode_enabled')) and lock_live)
    current_wait = router._pending_wait_summary(run_state, project_root=project_root)
    control_projection = _router_daemon_control_projection(router, run_state, daemon_live=daemon_live, current_wait=current_wait, current_action=status.get('current_action') if isinstance(status.get('current_action'), dict) else None, controller_ledger=router._controller_action_ledger_summary(run_root))
    return {'schema_version': 'flowpilot.router_daemon_resume_recovery.v1', 'router_daemon_status_path': router.project_relative(project_root, status_path), 'router_daemon_status_exists': status_path.exists(), 'router_daemon_lock_path': router.project_relative(project_root, lock_path), 'router_daemon_lock_exists': lock_path.exists(), 'router_daemon_lock_live': lock_live, 'router_daemon_owner_process_live': bool(lock_liveness.get('process_live')), 'router_daemon_active_owner_live': active_owner_live, 'router_daemon_lock_status': lock.get('status'), 'router_daemon_last_tick_at': lock.get('last_tick_at') or status.get('last_tick_at'), 'daemon_patrol': patrol_monitor, 'controller_action_ledger_path': router.project_relative(project_root, ledger_path), 'controller_action_ledger_exists': ledger_exists, 'controller_action_ledger_rescanned': True, 'decision': decision, 'terminal_lifecycle_status': terminal_mode, 'control_projection': control_projection, 'work_chain_liveness_claimed': False, 'liveness_authority': 'current_daemon_lock_process_and_controller_action_ledger', 'old_route_state_liveness_rejected': True, 'wait_agent_timeout_liveness_rejected': True, 'restart_only_after_controller_liveness_check_finds_dead': not bool(terminal_mode), 'never_start_second_router_writer': True}


def _ensure_daemon_runtime_state(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, lifecycle_status: str='manual_router_loop') -> dict[str, Any]:
    router._runtime_dir(run_root).mkdir(parents=True, exist_ok=True)
    router._controller_actions_dir(run_root).mkdir(parents=True, exist_ok=True)
    router._controller_receipts_dir(run_root).mkdir(parents=True, exist_ok=True)
    router._ensure_controller_action_ledger(project_root, run_root, run_state)
    router._ensure_router_scheduler_ledger(project_root, run_root, run_state)
    router._ensure_router_ownership_ledger(project_root, run_root, run_state)
    return router._write_router_daemon_status(project_root, run_root, run_state, lifecycle_status=lifecycle_status, recovery_hints=['start_router_daemon_if_daemon_mode_is_required'])


def _formal_router_daemon_ready(router: ModuleType, project_root: Path, run_root: Path) -> bool:
    # Readiness is a bounded poll. A Windows sharing violation or an atomic
    # replacement window means "not ready yet", never corruption or success.
    lock = router.read_json_if_valid(router._router_daemon_lock_path(run_root))
    status = router.read_json_if_valid(router._router_daemon_status_path(run_root))
    ledger = router.read_json_if_valid(router._controller_action_ledger_path(run_root))
    return router._router_daemon_lock_is_live(lock) and status.get('schema_version') == router.ROUTER_DAEMON_STATUS_SCHEMA and bool(status.get('daemon_mode_enabled')) and (status.get('tick_interval_seconds') == router.ROUTER_DAEMON_TICK_SECONDS) and bool((status.get('lock') or {}).get('live')) and (ledger.get('schema_version') == router.CONTROLLER_ACTION_LEDGER_SCHEMA) and (status.get('run_root') == router.project_relative(project_root, run_root))


def _tail_text(router: ModuleType, path: Path, *, max_chars: int=2000) -> str:
    try:
        text = path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return ''
    return text[-max_chars:]


def _current_live_startup_daemon_spawn(
    router: ModuleType,
    run_root: Path,
) -> dict[str, Any] | None:
    event_path = router._router_daemon_event_log_path(run_root)
    if not event_path.exists():
        return None
    try:
        lines = event_path.read_text(encoding='utf-8').splitlines()
    except OSError as exc:
        raise router.RouterError(f'cannot inspect current Router daemon startup authority: {exc}') from exc
    live_spawns: dict[tuple[int, str], dict[str, Any]] = {}
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = router.json.loads(line)
        except router.json.JSONDecodeError as exc:
            raise router.RouterError(
                f'current Router daemon event log is malformed at line {line_number}'
            ) from exc
        if not isinstance(record, dict) or record.get('event') != 'formal_router_daemon_process_opened':
            continue
        details = record.get('details') if isinstance(record.get('details'), dict) else {}
        identity = details.get('process_identity') if isinstance(details.get('process_identity'), dict) else {}
        if not router._process_identity_is_live(identity):
            continue
        key = (int(identity['pid']), str(identity['start_token']))
        live_spawns[key] = {
            'pid': int(identity['pid']),
            'process_identity': dict(identity),
            'process_launch_plan': dict(details.get('process_launch_plan') or {}),
            'daemon_instance_id': str(details.get('daemon_instance_id') or ''),
            'command': list(details.get('command') or []),
            'stdout_path': str(details.get('stdout_path') or ''),
            'stderr_path': str(details.get('stderr_path') or ''),
        }
    if len(live_spawns) > 1:
        raise router.RouterError(
            'multiple live Router daemon startup owners exist for the current run'
        )
    return next(iter(live_spawns.values()), None)


def _spawn_startup_router_daemon_process(router: ModuleType, project_root: Path, run_root: Path) -> dict[str, Any]:
    router._runtime_dir(run_root).mkdir(parents=True, exist_ok=True)
    stdout_path = router._runtime_dir(run_root) / 'router_daemon.startup.out.txt'
    stderr_path = router._runtime_dir(run_root) / 'router_daemon.startup.err.txt'
    command = [router.sys.executable, str(Path(router.__file__).resolve()), '--root', str(project_root), '--json', 'daemon', '--run-root', router.project_relative(project_root, run_root)]
    daemon_instance_id = f"router-daemon-{uuid.uuid4().hex}"
    child_env = dict(router.os.environ)
    child_env["FLOWPILOT_ROUTER_DAEMON_DEDICATED"] = "1"
    child_env["FLOWPILOT_ROUTER_DAEMON_INSTANCE_ID"] = daemon_instance_id
    process_command, process_environment, process_launch_plan = (
        router._resolve_current_python_process_launch(
            command,
            environment=child_env,
        )
    )
    creationflags = 0
    start_new_session = router.os.name != 'nt'
    if router.os.name == 'nt':
        start_new_session = False
        creationflags = getattr(router.subprocess, 'CREATE_NEW_PROCESS_GROUP', 0) | getattr(router.subprocess, 'CREATE_NO_WINDOW', 0)
        import msvcrt
        for stream in (router.sys.stdin, router.sys.stdout, router.sys.stderr):
            try:
                router.os.set_handle_inheritable(msvcrt.get_osfhandle(stream.fileno()), False)
            except (AttributeError, OSError, ValueError):
                pass
    stdout_handle = stdout_path.open('a', encoding='utf-8')
    stderr_handle = stderr_path.open('a', encoding='utf-8')
    try:
        process = router.subprocess.Popen(process_command, cwd=str(project_root), stdin=router.subprocess.DEVNULL, stdout=stdout_handle, stderr=stderr_handle, close_fds=True, start_new_session=start_new_session, creationflags=creationflags, env=process_environment)
    finally:
        stdout_handle.close()
        stderr_handle.close()
    process_identity = router._process_identity(process.pid)
    if process_identity is None:
        process.terminate()
        try:
            process.wait(timeout=router.ROUTER_DAEMON_STARTUP_TIMEOUT_SECONDS)
        except router.subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=router.ROUTER_DAEMON_STARTUP_TIMEOUT_SECONDS)
        raise router.RouterError('formal Router daemon process identity could not be established')
    router._append_router_daemon_event(run_root, 'formal_router_daemon_process_opened', {'process_identity': process_identity, 'process_launch_plan': process_launch_plan, 'daemon_instance_id': daemon_instance_id, 'command': command, 'stdout_path': router.project_relative(project_root, stdout_path), 'stderr_path': router.project_relative(project_root, stderr_path)})
    return {'pid': process.pid, 'process_identity': process_identity, 'process_launch_plan': process_launch_plan, 'daemon_instance_id': daemon_instance_id, 'command': command, 'stdout_path': router.project_relative(project_root, stdout_path), 'stderr_path': router.project_relative(project_root, stderr_path)}


def _start_or_attach_formal_router_daemon(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    lock_path = router._router_daemon_lock_path(run_root)
    status_path = router._router_daemon_status_path(run_root)
    ledger_path = router._controller_action_ledger_path(run_root)
    router._ensure_daemon_runtime_state(project_root, run_root, run_state, lifecycle_status='formal_daemon_starting')
    if router._formal_router_daemon_ready(project_root, run_root):
        attached_existing = True
        spawn_info: dict[str, Any] | None = None
    else:
        in_flight_spawn = _current_live_startup_daemon_spawn(router, run_root)
        lock = router.read_json_if_exists(lock_path)
        lock_liveness = router._router_daemon_lock_liveness(lock)
        lock_owner = lock.get('owner') if isinstance(lock.get('owner'), dict) else {}
        same_in_flight_owner = bool(
            in_flight_spawn
            and lock_owner.get('daemon_instance_id') == in_flight_spawn.get('daemon_instance_id')
            and lock_owner.get('pid') == (in_flight_spawn.get('process_identity') or {}).get('pid')
            and lock_owner.get('start_token') == (in_flight_spawn.get('process_identity') or {}).get('start_token')
        )
        if router._router_daemon_lock_is_live(lock):
            if not same_in_flight_owner:
                raise router.RouterError('cannot start Controller core: a live Router daemon lock exists but startup readiness artifacts are incomplete')
        if (
            lock.get('status') in {'stop_requested', 'terminal_exit_pending', 'cleanup_unconfirmed', 'error'}
            and lock_liveness.get('process_live')
        ):
            raise router.RouterError('cannot start Controller core: prior Router daemon cleanup is not complete')
        if lock.get('status') in {'active', 'stop_requested', 'terminal_exit_pending', 'cleanup_unconfirmed'}:
            if not same_in_flight_owner:
                raise router.RouterError('cannot start Controller core: Router daemon lock is stale; repair or replace stale lock explicitly')
        if in_flight_spawn is not None:
            spawn_info = in_flight_spawn
        else:
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
            cleanup = router._terminate_process_tree(
                spawn_info.get('process_identity'),
                timeout_seconds=router.ROUTER_DAEMON_STOP_TIMEOUT_SECONDS,
            )
            lock = router.read_json_if_exists(lock_path)
            owner = lock.get('owner') if isinstance(lock.get('owner'), dict) else {}
            if (
                cleanup.get('cleanup_confirmed') is True
                and lock.get('schema_version') == router.ROUTER_DAEMON_LOCK_SCHEMA
                and owner.get('daemon_instance_id') == spawn_info.get('daemon_instance_id')
            ):
                router._release_router_daemon_lock(
                    project_root,
                    run_root,
                    reason='formal_daemon_start_timeout_after_cleanup',
                    status='released',
                    cleanup_proof=cleanup,
                )
            router.append_history(run_state, 'formal_router_daemon_start_timeout', {'timeout_seconds': router.ROUTER_DAEMON_STARTUP_TIMEOUT_SECONDS, 'stderr_tail': stderr_tail, 'process_cleanup': cleanup})
            router.save_run_state(run_root, run_state)
            cleanup_suffix = '' if cleanup.get('cleanup_confirmed') else '; cleanup-unconfirmed'
            raise router.RouterError('formal Router daemon failed readiness check before Controller core load' + cleanup_suffix + (f'; stderr tail: {stderr_tail}' if stderr_tail else ''))
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
    lock_path = router._router_daemon_lock_path(run_root)
    existing = router.read_json_if_exists(lock_path)
    owner = existing.get('owner') if isinstance(existing.get('owner'), dict) else {}
    owner_is_current_dedicated_daemon = (
        owner.get('process_kind') == 'dedicated_daemon'
        and owner.get('pid') == router.os.getpid()
        and owner.get('start_token') == router._process_start_token(router.os.getpid())
    )
    if owner_is_current_dedicated_daemon:
        lock = dict(existing)
        lock['status'] = 'terminal_exit_pending'
        lock['terminal_observed_at'] = router.utc_now()
        lock['terminal_reason'] = reason
        router.write_json(lock_path, lock)
        router._append_router_daemon_event(
            run_root,
            'router_daemon_terminal_exit_pending',
            {'reason': reason, 'owner': owner},
        )
    else:
        inline_cleanup = {
            'cleanup_confirmed': True,
            'descendant_zero_confirmed': True,
            'reason': 'bounded_inline_terminal_loop_exit',
            'remaining_live_identities': [],
        }
        lock = router._release_router_daemon_lock(
            project_root,
            run_root,
            reason=reason,
            status='terminal_stopped',
            cleanup_proof=inline_cleanup,
        )
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
            passive_wait_fact = {'action_type': current_action.get('action_type'), 'controller_action_id': entry.get('action_id'), 'router_scheduler_row_id': current_action.get('router_scheduler_row_id'), 'scope_kind': current_action.get('scope_kind'), 'scope_id': current_action.get('scope_id')}
            if not any(
                isinstance(item, dict)
                and item.get('label') == 'router_projected_passive_wait_status_without_controller_work_row'
                and item.get('details') == passive_wait_fact
                for item in run_state.get('history', [])
            ):
                router.append_history(run_state, 'router_projected_passive_wait_status_without_controller_work_row', passive_wait_fact)
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
    semantic_before = _router_daemon_semantic_fingerprint(router, run_root, run_state)
    lock = router._refresh_router_daemon_lock(project_root, run_root)
    if lock.get('status') != 'active':
        run_state['daemon_mode_enabled'] = False
        status = router._write_router_daemon_status(project_root, run_root, run_state, lifecycle_status='daemon_stopped', current_action=run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else None, lock=lock)
        state_written = router.save_run_state(run_root, run_state)
        return _classify_router_daemon_tick(router, run_root, run_state, {'tick_at': status['last_tick_at'], 'observe_only': observe_only, 'lock_status': lock.get('status'), 'release_reason': lock.get('release_reason'), 'terminal': True}, before=semantic_before, state_written=state_written)
    latest_state, latest_root = router.load_run_state_from_run_root(project_root, run_root)
    if latest_state is None or latest_root is None:
        raise router.RouterError('router daemon tick requires bound run state')
    run_root = latest_root
    run_state.clear()
    run_state.update(latest_state)
    semantic_before = _router_daemon_semantic_fingerprint(router, run_root, run_state)
    if router._terminal_lifecycle_mode(run_state):
        run_state['daemon_mode_enabled'] = False
        lock = router._release_router_daemon_lock(project_root, run_root, reason='terminal_lifecycle_observed_by_daemon_tick', status='terminal_stopped')
        status = router._write_router_daemon_status(project_root, run_root, run_state, lifecycle_status='terminal_stopped', current_action=None, lock=lock)
        state_written = router.save_run_state(run_root, run_state)
        return _classify_router_daemon_tick(router, run_root, run_state, {'tick_at': status['last_tick_at'], 'observe_only': observe_only, 'lock_status': lock.get('status'), 'terminal': True, 'terminal_fence_observed': True}, before=semantic_before, state_written=state_written)
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
        state_written = router.save_run_state(run_root, run_state)
        return _classify_router_daemon_tick(router, run_root, run_state, {'tick_at': startup_schedule.get('tick_at') or router.utc_now(), 'observe_only': False, 'action_type': action.get('action_type') if isinstance(action, dict) else None, 'controller_action_id': startup_schedule.get('controller_action_id'), 'waiting_for_controller_core': False, 'startup_driver_active': True, 'startup_flag_fold': startup_flag_fold, 'receipt_summary': receipt_summary, 'scheduled_reconciliation': scheduled_reconciliation, 'boundary_projection': boundary_projection, 'startup_schedule': startup_schedule, 'queue_stop_reason': startup_schedule.get('queue_stop_reason'), 'terminal': bool(startup_schedule.get('terminal'))}, before=semantic_before, state_written=state_written)
    if observe_only:
        if isinstance(current_action, dict):
            router._write_controller_action_entry(project_root, run_root, run_state, current_action)
        status = router._write_router_daemon_status(project_root, run_root, run_state, lifecycle_status='daemon_observing', current_action=current_action, lock=lock)
        state_written = router.save_run_state(run_root, run_state)
        return _classify_router_daemon_tick(router, run_root, run_state, {'tick_at': status['last_tick_at'], 'observe_only': True, 'action_type': current_action.get('action_type') if isinstance(current_action, dict) else None, 'controller_action_id': current_action.get('controller_action_id') if isinstance(current_action, dict) else None, 'startup_flag_fold': startup_flag_fold, 'receipt_summary': receipt_summary, 'scheduled_reconciliation': scheduled_reconciliation, 'boundary_projection': boundary_projection, 'terminal': bool(status.get('run_lifecycle_status'))}, before=semantic_before, state_written=state_written)
    queue_result = router._router_daemon_fill_action_queue(project_root, run_root, run_state)
    current_action = queue_result.get('current_action') if isinstance(queue_result.get('current_action'), dict) else None
    status = router._write_router_daemon_status(project_root, run_root, run_state, lifecycle_status='daemon_active', current_action=current_action, lock=lock)
    state_written = router.save_run_state(run_root, run_state)
    return _classify_router_daemon_tick(router, run_root, run_state, {'tick_at': status['last_tick_at'], 'observe_only': False, 'action_type': current_action.get('action_type') if isinstance(current_action, dict) else None, 'controller_action_id': current_action.get('controller_action_id') if isinstance(current_action, dict) else None, 'startup_flag_fold': startup_flag_fold, 'receipt_summary': receipt_summary, 'scheduled_reconciliation': scheduled_reconciliation, 'boundary_projection': boundary_projection, 'queued_count': queue_result.get('queued_count'), 'queued_actions': queue_result.get('queued_actions'), 'queue_stop_reason': queue_result.get('stop_reason'), 'terminal': bool(status.get('run_lifecycle_status'))}, before=semantic_before, state_written=state_written)


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
        return {'ok': True, 'command': 'daemon', 'run_id': run_state.get('run_id'), 'run_root': router.project_relative(project_root, run_root), 'tick_interval_seconds': router.ROUTER_DAEMON_TICK_SECONDS, 'tick_count': 0, 'semantic_change_count': 0, 'no_change_tick_count': 0, 'last_tick': None, 'anomalies': [], 'observe_only': observe_only, 'lock_path': router.project_relative(project_root, router._router_daemon_lock_path(run_root)), 'lock_status': (router.read_json_if_exists(router._router_daemon_lock_path(run_root)) or {}).get('status'), 'status_path': router.project_relative(project_root, router._router_daemon_status_path(run_root)), 'daemon_status': _compact_router_daemon_status(status), 'terminal': True}
    run_state['daemon_mode_enabled'] = True
    daemon_process_kind = 'dedicated_daemon' if max_ticks is None else 'bounded_inline'
    lock = router._acquire_router_daemon_lock(
        project_root,
        run_root,
        run_state,
        replace_stale=replace_stale_lock,
        process_kind=daemon_process_kind,
        daemon_instance_id=router.os.environ.get('FLOWPILOT_ROUTER_DAEMON_INSTANCE_ID'),
    )
    tick_count = 0
    semantic_change_count = 0
    no_change_tick_count = 0
    last_tick: dict[str, Any] | None = None
    anomalies: list[dict[str, Any]] = []
    error: Exception | None = None
    runtime_initialized = False
    try:
        while True:
            stop_lock = router.read_json_if_exists(router._router_daemon_lock_path(run_root))
            if stop_lock.get('status') == 'stop_requested':
                stop_tick = {
                    'tick_at': router.utc_now(),
                    'observe_only': observe_only,
                    'stop_requested': True,
                    'stop_reason': stop_lock.get('stop_reason'),
                    'terminal': False,
                }
                tick_count += 1
                last_tick = _compact_router_daemon_tick(stop_tick)
                no_change_tick_count += 1
                router._append_router_daemon_event(
                    run_root,
                    'router_daemon_stop_acknowledged',
                    {'reason': stop_lock.get('stop_reason'), 'owner': stop_lock.get('owner')},
                )
                break
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
            tick_count += 1
            last_tick = _compact_router_daemon_tick(tick)
            if tick.get('semantic_changed'):
                semantic_change_count += 1
            else:
                no_change_tick_count += 1
            if (
                tick.get('deferred')
                or tick.get('nested_defer_reason')
                or tick.get('stop_requested')
            ) and len(anomalies) < _ROUTER_DAEMON_ANOMALY_SAMPLE_LIMIT:
                anomalies.append(last_tick or {})
            if tick.get('terminal'):
                break
            if max_ticks is not None and tick_count >= max_ticks:
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
        if error is None and (release_lock_on_exit or bool(last_tick and last_tick.get('terminal'))):
            existing_lock = router.read_json_if_exists(router._router_daemon_lock_path(run_root))
            if existing_lock.get('status') == 'active':
                final_status = 'terminal_stopped' if last_tick and last_tick.get('terminal') else 'released'
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
    return {'ok': True, 'command': 'daemon', 'run_id': run_state.get('run_id'), 'run_root': router.project_relative(project_root, run_root), 'tick_interval_seconds': router.ROUTER_DAEMON_TICK_SECONDS, 'tick_count': tick_count, 'semantic_change_count': semantic_change_count, 'no_change_tick_count': no_change_tick_count, 'last_tick': last_tick, 'anomalies': anomalies, 'observe_only': observe_only, 'lock_path': router.project_relative(project_root, router._router_daemon_lock_path(run_root)), 'lock_status': (router.read_json_if_exists(router._router_daemon_lock_path(run_root)) or {}).get('status'), 'status_path': router.project_relative(project_root, router._router_daemon_status_path(run_root)), 'daemon_status': _compact_router_daemon_status(status), 'terminal': bool(last_tick and last_tick.get('terminal'))}


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
    router.save_run_state(run_root, run_state)
    lock_path = router._router_daemon_lock_path(run_root)
    existing_lock = router.read_json_if_exists(lock_path)
    if existing_lock.get('schema_version') != router.ROUTER_DAEMON_LOCK_SCHEMA:
        cleanup = {
            'cleanup_confirmed': True,
            'descendant_zero_confirmed': True,
            'reason': 'daemon_lock_missing',
            'remaining_live_identities': [],
        }
        lock = {'status': 'missing', 'reason': reason, 'cleanup_proof': cleanup}
    elif (
        existing_lock.get('status') in {'released', 'terminal_stopped'}
        and isinstance(existing_lock.get('cleanup_proof'), dict)
        and existing_lock['cleanup_proof'].get('cleanup_confirmed') is True
        and existing_lock['cleanup_proof'].get('descendant_zero_confirmed') is True
    ):
        cleanup = existing_lock['cleanup_proof']
        lock = existing_lock
    else:
        owner = dict(existing_lock.get('owner') or {}) if isinstance(existing_lock.get('owner'), dict) else {}
        owner_is_current_process = (
            owner.get('pid') == router.os.getpid()
            and owner.get('start_token') == router._process_start_token(router.os.getpid())
        )
        owner_identity_live = router._process_identity_is_live(owner)
        observed_descendant_map: dict[tuple[int, str], dict[str, Any]] = {}

        def observe_exact_descendants() -> None:
            if owner_is_current_process or not router._process_identity_is_live(owner):
                return
            for descendant in router._process_descendant_identities(owner):
                key = (int(descendant['pid']), str(descendant['start_token']))
                observed_descendant_map[key] = descendant

        if owner_identity_live:
            observe_exact_descendants()
        _request_router_daemon_stop(router, project_root, run_root, reason=reason)
        if owner_is_current_process:
            cleanup = {
                'cleanup_confirmed': True,
                'descendant_zero_confirmed': True,
                'reason': 'bounded_inline_daemon_loop_not_running',
                'target_identity': owner,
                'observed_descendant_identities': [],
                'remaining_live_identities': [],
                'pid_reuse_detected': False,
                'signal_sent': False,
            }
        elif not owner_identity_live:
            cleanup = {
                'cleanup_confirmed': True,
                'descendant_zero_confirmed': True,
                'reason': (
                    'pid_reused_target_identity_not_signaled'
                    if router._process_is_live(owner.get('pid'))
                    else 'target_identity_already_exited'
                ),
                'target_identity': owner,
                'observed_descendant_identities': [],
                'remaining_live_identities': [],
                'pid_reuse_detected': bool(router._process_is_live(owner.get('pid'))),
                'signal_sent': False,
            }
        elif owner.get('process_kind') != 'dedicated_daemon':
            cleanup = {
                'cleanup_confirmed': False,
                'descendant_zero_confirmed': False,
                'reason': 'cleanup_unconfirmed_owner_process_kind',
                'target_identity': owner,
                'observed_descendant_identities': list(observed_descendant_map.values()),
                'remaining_live_identities': [owner, *observed_descendant_map.values()],
                'pid_reuse_detected': False,
                'signal_sent': False,
            }
        else:
            deadline = router.time.monotonic() + router.ROUTER_DAEMON_STOP_TIMEOUT_SECONDS
            while router.time.monotonic() < deadline and router._process_identity_is_live(owner):
                observe_exact_descendants()
                router.time.sleep(router.ROUTER_DAEMON_STARTUP_POLL_SECONDS)
            observe_exact_descendants()
            owner_cleanup: dict[str, Any] | None = None
            if router._process_identity_is_live(owner):
                owner_cleanup = router._terminate_process_tree(
                    owner,
                    timeout_seconds=router.ROUTER_DAEMON_STOP_TIMEOUT_SECONDS,
                )
                for descendant in owner_cleanup.get('observed_descendant_identities') or []:
                    key = (int(descendant['pid']), str(descendant['start_token']))
                    observed_descendant_map[key] = descendant
            observed_descendants = list(observed_descendant_map.values())
            descendant_cleanup: list[dict[str, Any]] = []
            for descendant in observed_descendants:
                if router._process_identity_is_live(descendant):
                    descendant_cleanup.append(
                        router._terminate_process_tree(
                            descendant,
                            timeout_seconds=router.ROUTER_DAEMON_STOP_TIMEOUT_SECONDS,
                        )
                    )
            remaining_identities = (
                [owner] if router._process_identity_is_live(owner) else []
            ) + [
                descendant
                for descendant in observed_descendants
                if router._process_identity_is_live(descendant)
            ]
            cleanup = {
                'cleanup_confirmed': not remaining_identities,
                'descendant_zero_confirmed': not remaining_identities,
                'reason': (
                    (
                        str(owner_cleanup.get('reason') or 'daemon_process_tree_terminated')
                        if owner_cleanup is not None
                        else 'daemon_exited_after_stop_request'
                    )
                    if not remaining_identities
                    else 'cleanup_unconfirmed'
                ),
                'target_identity': owner,
                'observed_descendant_identities': observed_descendants,
                'owner_cleanup_result': owner_cleanup,
                'descendant_cleanup_results': descendant_cleanup,
                'remaining_live_identities': remaining_identities,
                'pid_reuse_detected': bool(
                    owner_cleanup and owner_cleanup.get('pid_reuse_detected')
                ),
                'signal_sent': bool(
                    (owner_cleanup and owner_cleanup.get('signal_sent'))
                    or any(result.get('signal_sent') for result in descendant_cleanup)
                ),
            }
        if cleanup.get('cleanup_confirmed') is not True or cleanup.get('descendant_zero_confirmed') is not True:
            cleanup_lock = router.read_json_if_exists(lock_path)
            cleanup_lock['status'] = 'cleanup_unconfirmed'
            cleanup_lock['cleanup_checked_at'] = router.utc_now()
            cleanup_lock['cleanup_proof'] = cleanup
            router.write_json(lock_path, cleanup_lock)
            status = router._write_router_daemon_status(
                project_root,
                run_root,
                run_state,
                lifecycle_status='daemon_cleanup_unconfirmed',
                current_action=run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else None,
                lock=cleanup_lock,
                error={'reason': 'cleanup_unconfirmed', 'process_cleanup': cleanup},
            )
            router.save_run_state(run_root, run_state)
            raise router.RouterError('router daemon stop cleanup-unconfirmed; lock was not released')
        lock = router._release_router_daemon_lock(
            project_root,
            run_root,
            reason=reason,
            status='released',
            cleanup_proof=cleanup,
        )
    status = router._write_router_daemon_status(project_root, run_root, run_state, lifecycle_status='daemon_stopped', current_action=run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else None, lock=lock)
    router.save_run_state(run_root, run_state)
    return {'ok': True, 'command': 'daemon-stop', 'run_id': run_state.get('run_id'), 'lock_status': lock.get('status'), 'process_cleanup': cleanup, 'status_path': router.project_relative(project_root, router._router_daemon_status_path(run_root)), 'daemon_status': status}
