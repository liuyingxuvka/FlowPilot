"""Phase helper extracted from :mod:`capability_model`."""

from __future__ import annotations

from typing import Iterable

if __package__:
    from . import capability_model as _model
else:
    import capability_model as _model

_REQUIRED_MODEL_NAMES = (
    "FunctionResult",
    "Iterable",
    "State",
    "_route_scaffold_ready",
    "_step",
)
for _name in _REQUIRED_MODEL_NAMES:
    globals()[_name] = getattr(_model, _name)
del _name

__all__ = ["apply_resume_phase"]


def apply_resume_phase(self, state: State) -> Iterable[FunctionResult]:
    if _route_scaffold_ready(state) and not state.resume_loaded_state:
        yield _step(
            state,
            label="resume_loaded_state",
            action="continuation turn loads local state, active route, capability evidence, latest manual-resume and foreground-duty evidence, lifecycle evidence, and role-binding ledger",
            resume_loaded_state=True,
        )
        return

    if _route_scaffold_ready(state) and not state.resume_loaded_frontier:
        yield _step(
            state,
            label="resume_loaded_execution_frontier",
            action="continuation turn loads execution_frontier.json before selecting capability work",
            resume_loaded_frontier=True,
        )
        return

    if _route_scaffold_ready(state) and not state.resume_loaded_packet_ledger:
        yield _step(
            state,
            label="resume_loaded_packet_ledger",
            action="continuation turn loads packet_ledger.json before asking PM or dispatching capability work",
            resume_loaded_packet_ledger=True,
        )
        return

    if (
        _route_scaffold_ready(state)
        and not state.router_daemon_recovered_on_resume
        and not state.terminal_router_daemon_stopped
    ):
        yield _step(
            state,
            label="resume_checked_or_restarted_persistent_router_daemon",
            action="continuation turn checks the persistent Router daemon lock/status, restarts only a dead or stale daemon, and rescans the Controller action ledger before role recovery or PM resume",
            router_daemon_started=True,
            router_daemon_lock_acquired=True,
            router_daemon_tick_seconds=1,
            router_daemon_status_written=True,
            controller_action_ledger_initialized=True,
            controller_action_watch_active=True,
            router_daemon_recovered_on_resume=True,
            terminal_router_daemon_stopped=False,
        )
        return

    if _route_scaffold_ready(state) and not state.resume_loaded_role_binding_memory:
        yield _step(
            state,
            label="resume_loaded_role_binding_memory",
            action="continuation turn loads the exact current-obligation role memory packet and current route delta; idle or historical roles remain audit-only",
            resume_loaded_role_binding_memory=True,
        )
        return

    if _route_scaffold_ready(state) and not state.resume_host_rehydrate_requested:
        yield _step(
            state,
            label="resume_host_spawn_or_rehydrate_runtime_roles",
            action="router asks the host to restore or open only the exact currently requested responsibility before PM resume",
            resume_host_rehydrate_requested=True,
        )
        return

    if _route_scaffold_ready(state) and not state.resume_restored_runtime_roles:
        yield _step(
            state,
            label="resume_restored_required_role_binding_coverage",
            action="continuation turn restores the exact requested live responsibility when current and prepares one memory-seeded replacement only when that responsibility requires replacement",
            resume_restored_runtime_roles=True,
            replacement_roles_seeded_from_memory=True,
        )
        return

    if _route_scaffold_ready(state) and not state.resume_rehydrated_runtime_roles:
        yield _step(
            state,
            label="resume_rehydrated_required_role_binding_coverage",
            action="rehydrate only the exact current-obligation role from current route memory before asking the project manager for the next capability runway",
            resume_rehydrated_runtime_roles=True,
        )
        return

    if _route_scaffold_ready(state) and not state.resume_injected_current_run_memory_into_roles:
        yield _step(
            state,
            label="resume_injected_current_run_memory_into_roles",
            action="host injects the requested role's current-run memory and current route delta before PM runway",
            resume_injected_current_run_memory_into_roles=True,
        )
        return

    if _route_scaffold_ready(state) and not state.role_binding_recovery_report_written:
        yield _step(
            state,
            label="role_binding_recovery_report_written",
            action="write the requested-role rehydration report with exact target, restored or replaced status, current generation, and route delta before any PM resume decision",
            role_binding_recovery_report_written=True,
        )
        return

    if _route_scaffold_ready(state) and not state.resume_pm_decision_requested:
        yield _step(
            state,
            label="resume_asked_project_manager",
            action="continuation turn asks the project manager for PM_DECISION from the current frontier and packet ledger",
            resume_pm_decision_requested=True,
        )
        return

    if _route_scaffold_ready(state) and not state.resume_pm_controller_reminder_checked:
        yield _step(
            state,
            label="resume_pm_controller_reminder_checked",
            action="controller requires PM_DECISION to include controller_reminder before dispatching any capability packet",
            resume_pm_controller_reminder_checked=True,
        )
        return

    if _route_scaffold_ready(state) and not state.resume_reviewer_dispatch_policy_checked:
        yield _step(
            state,
            label="resume_reviewer_dispatch_policy_checked",
            action="controller confirms NODE_PACKET dispatch requires reviewer approval and ambiguous worker state blocks controller execution",
            resume_reviewer_dispatch_policy_checked=True,
        )
        return

    if _route_scaffold_ready(state) and not state.pm_resume_decision_recorded:
        yield _step(
            state,
            label="pm_resume_completion_runway_recorded",
            action="project manager records a completion-oriented capability runway from the current gate toward completion, including hard stops and checkpoint cadence",
            pm_resume_decision_recorded=True,
            pm_completion_runway_recorded=True,
            pm_runway_hard_stops_recorded=True,
            pm_runway_checkpoint_cadence_recorded=True,
        )
        return

    if _route_scaffold_ready(state) and not state.pm_runway_synced_to_plan:
        yield _step(
            state,
            label="pm_runway_synced_to_visible_plan",
            action="controller calls the host native plan tool when available, or records the manual projection method, and replaces the visible capability plan with a downstream PM runway projection",
            pm_runway_synced_to_plan=True,
            plan_sync_method_recorded=True,
            visible_plan_has_runway_depth=True,
        )
        return

    if _route_scaffold_ready(state) and not state.manual_resume_binding_health_checked:
        yield _step(
            state,
            label="continuation_resume_ready_checked",
            action="check manual resume binding health when supported, or check manual-resume state/frontier/role-binding-memory readiness when no real wakeup exists",
            manual_resume_binding_health_checked=True,
        )
        return
