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
    if _route_scaffold_ready(state) and not state.heartbeat_loaded_state:
        yield _step(
            state,
            label="heartbeat_loaded_state",
            action="continuation turn loads local state, active route, capability evidence, latest heartbeat or manual-resume evidence, lifecycle evidence, and role-binding ledger",
            heartbeat_loaded_state=True,
        )
        return

    if _route_scaffold_ready(state) and not state.heartbeat_loaded_frontier:
        yield _step(
            state,
            label="heartbeat_loaded_execution_frontier",
            action="continuation turn loads execution_frontier.json before selecting capability work",
            heartbeat_loaded_frontier=True,
        )
        return

    if _route_scaffold_ready(state) and not state.heartbeat_loaded_packet_ledger:
        yield _step(
            state,
            label="heartbeat_loaded_packet_ledger",
            action="continuation turn loads packet_ledger.json before asking PM or dispatching capability work",
            heartbeat_loaded_packet_ledger=True,
        )
        return

    if (
        _route_scaffold_ready(state)
        and not state.router_daemon_recovered_on_resume
        and not state.terminal_router_daemon_stopped
    ):
        yield _step(
            state,
            label="heartbeat_checked_or_restarted_persistent_router_daemon",
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

    if _route_scaffold_ready(state) and not state.heartbeat_loaded_role_binding_memory:
        yield _step(
            state,
            label="heartbeat_loaded_role_binding_memory",
            action="continuation turn loads all six compact role memory packets before restoring or replacing runtime responsibilities",
            heartbeat_loaded_role_binding_memory=True,
        )
        return

    if _route_scaffold_ready(state) and not state.heartbeat_host_rehydrate_requested:
        yield _step(
            state,
            label="heartbeat_host_spawn_or_rehydrate_six_roles",
            action="router asks the host to restore or open all runtime-requested roles before PM resume",
            heartbeat_host_rehydrate_requested=True,
        )
        return

    if _route_scaffold_ready(state) and not state.heartbeat_restored_crew:
        yield _step(
            state,
            label="heartbeat_restored_required_role_binding_coverage",
            action="continuation turn restores live runtime responsibilities when available and prepares memory-seeded replacements otherwise",
            heartbeat_restored_crew=True,
            replacement_roles_seeded_from_memory=True,
        )
        return

    if _route_scaffold_ready(state) and not state.heartbeat_rehydrated_crew:
        yield _step(
            state,
            label="heartbeat_rehydrated_required_role_binding_coverage",
            action="rehydrate the six FlowPilot roles from role memory packets before asking the project manager for the next capability runway",
            heartbeat_rehydrated_crew=True,
        )
        return

    if _route_scaffold_ready(state) and not state.heartbeat_injected_current_run_memory_into_roles:
        yield _step(
            state,
            label="heartbeat_injected_current_run_memory_into_roles",
            action="host injects each role's current-run memory and PM resume context before PM runway",
            heartbeat_injected_current_run_memory_into_roles=True,
        )
        return

    if _route_scaffold_ready(state) and not state.role_binding_recovery_report_written:
        yield _step(
            state,
            label="role_binding_recovery_report_written",
            action="write the role-binding rehydration report with restored, replaced, blocked, and memory-seeded role status before any PM resume decision",
            role_binding_recovery_report_written=True,
        )
        return

    if _route_scaffold_ready(state) and not state.heartbeat_pm_decision_requested:
        yield _step(
            state,
            label="heartbeat_asked_project_manager",
            action="continuation turn asks the project manager for PM_DECISION from the current frontier and packet ledger",
            heartbeat_pm_decision_requested=True,
        )
        return

    if _route_scaffold_ready(state) and not state.heartbeat_pm_controller_reminder_checked:
        yield _step(
            state,
            label="heartbeat_pm_controller_reminder_checked",
            action="controller requires PM_DECISION to include controller_reminder before dispatching any capability packet",
            heartbeat_pm_controller_reminder_checked=True,
        )
        return

    if _route_scaffold_ready(state) and not state.heartbeat_reviewer_dispatch_policy_checked:
        yield _step(
            state,
            label="heartbeat_reviewer_dispatch_policy_checked",
            action="controller confirms NODE_PACKET dispatch requires reviewer approval and ambiguous worker state blocks controller execution",
            heartbeat_reviewer_dispatch_policy_checked=True,
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
            action="controller calls the host native plan tool when available, or records the fallback method, and replaces the visible capability plan with a downstream PM runway projection",
            pm_runway_synced_to_plan=True,
            plan_sync_method_recorded=True,
            visible_plan_has_runway_depth=True,
        )
        return

    if _route_scaffold_ready(state) and not state.heartbeat_health_checked:
        yield _step(
            state,
            label="continuation_resume_ready_checked",
            action="check automated heartbeat health when supported, or check manual-resume state/frontier/crew-memory readiness when no real wakeup exists",
            heartbeat_health_checked=True,
        )
        return
