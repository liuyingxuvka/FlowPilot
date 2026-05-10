"""FlowGuard model for FlowPilot heartbeat/manual-resume re-entry.

Risk intent brief:
- Prevent resume launchers from becoming a second route-control authority.
- Protect current-run state, packet bodies, prompt cards, crew authority, and
  PM decisions from chat-history reconstruction or old-run reuse.
- Model-critical durable state: current pointer, current run root, router
  state, packet ledger, prompt ledger, execution frontier, crew memory, prompt
  manifest checks, packet-ledger checks, reviewed worker results, and PM
  recovery blocks.
- Adversarial branches include ambiguous worker state, duplicate resume ticks,
  old run control state, body reads, missing manifest/ledger checks, dynamic
  launchers, heartbeat keepalive self-classification, stale crew ids, missing
  one-minute heartbeat evidence, stale lifecycle flags, host role liveness
  ambiguity, and route progress inferred from chat history.
- Hard invariants: stable launcher only; Controller is relay-only; PM decisions
  happen after heartbeat/manual wake records re-entry to the router, one-minute
  heartbeat evidence when automated, current-run state, visible plan
  restoration, six-role liveness checking, lifecycle reconciliation, and crew
  rehydration;
  prompt/mail delivery is ledger gated; route progress can only come from
  reviewed packet evidence.
- Blindspot: this is an abstract control-plane model, not a replay adapter for
  the current FlowPilot router implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class Tick:
    """One launcher/controller re-entry tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | blocked | complete
    entry_mode: str = "none"  # none | heartbeat | manual
    holder: str = "none"  # none | launcher | controller | pm | reviewer | worker
    work_branch: str = "unknown"  # unknown | existing_result | fresh_worker
    ambiguous_state: str = "unknown"  # unknown | clear | ambiguous

    stable_launcher_entered: bool = False
    dynamic_launcher_used: bool = False
    launcher_prompt_contains_route_state: bool = False
    resume_wake_recorded_to_router: bool = False
    heartbeat_self_keepalive_without_router: bool = False
    heartbeat_trigger_evidence_loaded: bool = False
    heartbeat_interval_minutes: int = 0
    heartbeat_trigger_bound_to_current_run: bool = False

    current_pointer_loaded: bool = False
    current_pointer_valid: bool = False
    run_root_loaded: bool = False
    run_root_matches_pointer: bool = False
    old_run_scan_done: bool = False
    old_run_control_state_quarantined: bool = False
    old_run_control_state_reused: bool = False

    router_state_loaded: bool = False
    packet_ledger_loaded: bool = False
    prompt_ledger_loaded: bool = False
    frontier_loaded: bool = False
    visible_plan_restored_from_run: bool = False
    crew_memory_loaded: bool = False
    all_six_role_liveness_checked: bool = False
    role_liveness_outcome: str = "unknown"  # unknown | all_active | recovery_needed | timeout_unknown
    timeout_unknown_treated_as_active: bool = False
    missing_role_treated_as_waiting: bool = False
    host_role_rehydrate_requested: bool = False

    controller_relay_boundary_confirmed: bool = False
    controller_read_forbidden_body: bool = False
    sealed_body_read: bool = False
    controller_authored_project_evidence: bool = False
    controller_advanced_route: bool = False
    controller_self_approved_pm_decision: bool = False

    crew_roles_ready: bool = False
    crew_restored: bool = False
    crew_replaced: bool = False
    run_memory_injected_into_roles: bool = False
    crew_rehydration_report_written: bool = False
    all_roles_current_run_bound: bool = False
    replacement_roles_seeded_from_memory: bool = False
    crew_old_agent_ids_reused: bool = False
    crew_lifecycle_flags_current: bool = False
    capability_lifecycle_flags_current: bool = False
    officer_lifecycle_flags_current: bool = False

    pm_recovery_requested: bool = False
    pm_decision_requested: bool = False
    pm_decision_prompt_delivered: bool = False
    pm_controller_reminder_included: bool = False
    pm_decision_returned: bool = False
    pm_decision_from_chat_history: bool = False

    reviewer_dispatch_prompt_delivered: bool = False
    reviewer_dispatch_allowed: bool = False
    existing_worker_result_found: bool = False
    existing_worker_result_routed_to_reviewer: bool = False
    fresh_worker_packet_sent: bool = False
    worker_result_returned: bool = False
    worker_result_routed_to_reviewer: bool = False
    reviewer_result_passed: bool = False

    pm_node_decision_prompt_delivered: bool = False
    route_progress_recorded: bool = False
    route_progress_source: str = "none"  # none | reviewed_packet | chat_history | controller
    chat_history_progress_inferred: bool = False

    prompt_deliveries: int = 0
    manifest_check_requests: int = 0
    manifest_checks: int = 0
    manifest_check_requested: bool = False
    mail_deliveries: int = 0
    ledger_check_requests: int = 0
    ledger_checks: int = 0
    ledger_check_requested: bool = False
    system_card_identity_boundaries_verified: bool = False
    packet_body_identity_boundaries_verified: bool = False
    result_body_identity_boundaries_verified: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


class ResumeReentryStep:
    """Model one resume control-plane transition.

    Input x State -> Set(Output x State)
    reads: all state fields that select the next controller boundary
    writes: one durable control-plane fact, request, prompt, mail, or terminal
    idempotency: a repeated tick observes current state and advances at most one
    missing fact; terminal states produce no additional side effects.
    """

    name = "ResumeReentryStep"
    reads = ("status", "entry_mode", "loaded_state", "crew_roles", "prompt_mail_gates")
    writes = ("control_plane_fact", "manifest_or_ledger_check", "terminal_status")
    input_description = "heartbeat/manual resume tick"
    output_description = "one abstract FlowPilot resume control-plane action"
    idempotency = "repeat ticks do not duplicate completed facts"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def _request_manifest_check(state: State) -> State:
    return replace(
        state,
        manifest_check_requests=state.manifest_check_requests + 1,
        manifest_check_requested=True,
    )


def _request_ledger_check(state: State) -> State:
    return replace(
        state,
        ledger_check_requests=state.ledger_check_requests + 1,
        ledger_check_requested=True,
    )


def _prompt(state: State, **changes: object) -> State:
    return replace(
        state,
        prompt_deliveries=state.prompt_deliveries + 1,
        manifest_checks=state.manifest_checks + 1,
        manifest_check_requested=False,
        system_card_identity_boundaries_verified=True,
        **changes,
    )


def _mail(state: State, **changes: object) -> State:
    return replace(
        state,
        mail_deliveries=state.mail_deliveries + 1,
        ledger_checks=state.ledger_checks + 1,
        ledger_check_requested=False,
        packet_body_identity_boundaries_verified=True,
        result_body_identity_boundaries_verified=True,
        **changes,
    )


def _loaded_current_run_state(state: State) -> bool:
    return (
        state.current_pointer_loaded
        and state.current_pointer_valid
        and state.run_root_loaded
        and state.run_root_matches_pointer
        and state.old_run_scan_done
        and state.old_run_control_state_quarantined
        and state.router_state_loaded
        and state.packet_ledger_loaded
        and state.prompt_ledger_loaded
        and state.frontier_loaded
        and state.visible_plan_restored_from_run
        and state.crew_memory_loaded
    )


def _heartbeat_trigger_ready(state: State) -> bool:
    if state.entry_mode == "none":
        return True
    if not state.resume_wake_recorded_to_router:
        return False
    if state.entry_mode != "heartbeat":
        return True
    return (
        state.heartbeat_trigger_evidence_loaded
        and state.heartbeat_interval_minutes == 1
        and state.heartbeat_trigger_bound_to_current_run
    )


def _lifecycle_flags_current(state: State) -> bool:
    return (
        state.crew_lifecycle_flags_current
        and state.capability_lifecycle_flags_current
        and state.officer_lifecycle_flags_current
    )


def _next_required_prompt(state: State) -> str:
    if state.status in {"blocked", "complete"}:
        return "none"
    if (
        state.ambiguous_state == "clear"
        and state.crew_roles_ready
        and not state.pm_decision_prompt_delivered
    ):
        return "prompt"
    if state.pm_decision_returned and not state.reviewer_dispatch_prompt_delivered:
        return "prompt"
    if state.reviewer_result_passed and not state.pm_node_decision_prompt_delivered:
        return "prompt"
    return "none"


def _next_required_mail(state: State) -> str:
    if state.status in {"blocked", "complete"}:
        return "none"
    if (
        state.reviewer_dispatch_allowed
        and state.work_branch == "existing_result"
        and not state.existing_worker_result_routed_to_reviewer
    ):
        return "mail"
    if (
        state.reviewer_dispatch_allowed
        and state.work_branch == "fresh_worker"
        and not state.fresh_worker_packet_sent
    ):
        return "mail"
    if (
        state.fresh_worker_packet_sent
        and not state.worker_result_routed_to_reviewer
    ):
        return "mail"
    return "none"


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"blocked", "complete"}:
        return

    next_prompt = _next_required_prompt(state)
    if next_prompt == "prompt" and not state.manifest_check_requested:
        yield Transition(
            "controller_instructed_to_check_prompt_manifest",
            _request_manifest_check(state),
        )
        return

    next_mail = _next_required_mail(state)
    if next_mail == "mail" and not state.ledger_check_requested:
        yield Transition(
            "controller_instructed_to_check_packet_ledger",
            _request_ledger_check(state),
        )
        return

    if not state.stable_launcher_entered:
        yield Transition(
            "stable_heartbeat_launcher_entered",
            replace(
                state,
                status="running",
                entry_mode="heartbeat",
                holder="launcher",
                stable_launcher_entered=True,
            ),
        )
        yield Transition(
            "stable_manual_resume_launcher_entered",
            replace(
                state,
                status="running",
                entry_mode="manual",
                holder="launcher",
                stable_launcher_entered=True,
            ),
        )
        return
    if state.entry_mode in {"heartbeat", "manual"} and not state.resume_wake_recorded_to_router:
        yield Transition(
            "resume_wake_recorded_to_router",
            replace(state, resume_wake_recorded_to_router=True),
        )
        return
    if state.entry_mode == "heartbeat" and not state.heartbeat_trigger_evidence_loaded:
        yield Transition(
            "one_minute_heartbeat_resume_trigger_confirmed",
            replace(
                state,
                heartbeat_trigger_evidence_loaded=True,
                heartbeat_interval_minutes=1,
                heartbeat_trigger_bound_to_current_run=True,
            ),
        )
        return
    if not state.current_pointer_loaded:
        yield Transition(
            "current_pointer_loaded",
            replace(state, current_pointer_loaded=True, current_pointer_valid=True),
        )
        return
    if not state.run_root_loaded:
        yield Transition(
            "current_run_root_loaded",
            replace(state, run_root_loaded=True, run_root_matches_pointer=True),
        )
        return
    if not state.old_run_scan_done:
        yield Transition(
            "old_run_control_state_rejected",
            replace(
                state,
                old_run_scan_done=True,
                old_run_control_state_quarantined=True,
            ),
        )
        return
    if not state.router_state_loaded:
        yield Transition("router_state_loaded", replace(state, router_state_loaded=True))
        return
    if not state.packet_ledger_loaded:
        yield Transition("packet_ledger_loaded", replace(state, packet_ledger_loaded=True))
        return
    if not state.prompt_ledger_loaded:
        yield Transition("prompt_ledger_loaded", replace(state, prompt_ledger_loaded=True))
        return
    if not state.frontier_loaded:
        yield Transition("execution_frontier_loaded", replace(state, frontier_loaded=True))
        return
    if not state.visible_plan_restored_from_run:
        yield Transition(
            "visible_plan_restored_from_current_run",
            replace(state, visible_plan_restored_from_run=True),
        )
        return
    if not state.crew_memory_loaded:
        yield Transition("crew_memory_loaded", replace(state, crew_memory_loaded=True))
        return
    if not state.controller_relay_boundary_confirmed:
        yield Transition(
            "controller_relay_boundary_confirmed",
            replace(state, controller_relay_boundary_confirmed=True, holder="controller"),
        )
        return
    if not state.all_six_role_liveness_checked:
        yield Transition(
            "six_role_liveness_checked_all_active",
            replace(
                state,
                all_six_role_liveness_checked=True,
                role_liveness_outcome="all_active",
            ),
        )
        yield Transition(
            "six_role_liveness_checked_recovery_needed",
            replace(
                state,
                all_six_role_liveness_checked=True,
                role_liveness_outcome="recovery_needed",
            ),
        )
        yield Transition(
            "six_role_liveness_timeout_unknown_recorded",
            replace(
                state,
                all_six_role_liveness_checked=True,
                role_liveness_outcome="timeout_unknown",
            ),
        )
        return
    if not state.host_role_rehydrate_requested:
        yield Transition(
            "host_spawn_or_rehydrate_six_resume_roles_requested",
            replace(state, host_role_rehydrate_requested=True),
        )
        return
    if not state.run_memory_injected_into_roles:
        yield Transition(
            "current_run_memory_injected_into_resume_roles",
            replace(state, run_memory_injected_into_roles=True),
        )
        return
    if not state.crew_roles_ready:
        if state.role_liveness_outcome == "all_active":
            yield Transition(
                "crew_roles_restored_from_current_run_memory",
                replace(
                    state,
                    crew_roles_ready=True,
                    crew_restored=True,
                    all_roles_current_run_bound=True,
                ),
            )
        yield Transition(
            "crew_roles_replaced_from_current_run_memory",
            replace(
                state,
                crew_roles_ready=True,
                crew_replaced=True,
                all_roles_current_run_bound=True,
                replacement_roles_seeded_from_memory=True,
            ),
        )
        return
    if not state.crew_rehydration_report_written:
        yield Transition(
            "crew_rehydration_report_written_before_pm_resume",
            replace(state, crew_rehydration_report_written=True),
        )
        return
    if not _lifecycle_flags_current(state):
        yield Transition(
            "crew_capability_officer_lifecycle_flags_reconciled",
            replace(
                state,
                crew_lifecycle_flags_current=True,
                capability_lifecycle_flags_current=True,
                officer_lifecycle_flags_current=True,
            ),
        )
        return
    if state.ambiguous_state == "unknown":
        yield Transition(
            "resume_state_clear_for_pm_decision",
            replace(state, ambiguous_state="clear"),
        )
        yield Transition(
            "ambiguous_resume_state_blocked_for_pm_recovery",
            replace(
                state,
                status="blocked",
                ambiguous_state="ambiguous",
                pm_recovery_requested=True,
                holder="pm",
            ),
        )
        return
    if not state.pm_decision_prompt_delivered:
        yield Transition(
            "pm_decision_card_delivered_with_controller_reminder",
            _prompt(
                state,
                pm_decision_prompt_delivered=True,
                pm_controller_reminder_included=True,
                pm_decision_requested=True,
                holder="pm",
            ),
        )
        return
    if not state.pm_decision_returned:
        yield Transition(
            "pm_resume_decision_returned",
            replace(state, pm_decision_returned=True, holder="controller"),
        )
        return
    if not state.reviewer_dispatch_prompt_delivered:
        yield Transition(
            "reviewer_dispatch_card_delivered",
            _prompt(state, reviewer_dispatch_prompt_delivered=True, holder="reviewer"),
        )
        return
    if not state.reviewer_dispatch_allowed:
        yield Transition(
            "reviewer_dispatch_allowed",
            replace(state, reviewer_dispatch_allowed=True, holder="controller"),
        )
        return
    if state.work_branch == "unknown":
        yield Transition(
            "existing_worker_result_envelope_found",
            replace(
                state,
                work_branch="existing_result",
                existing_worker_result_found=True,
            ),
        )
        yield Transition(
            "pm_requests_fresh_worker_packet",
            replace(state, work_branch="fresh_worker"),
        )
        return
    if (
        state.work_branch == "existing_result"
        and not state.existing_worker_result_routed_to_reviewer
    ):
        yield Transition(
            "existing_worker_result_routed_to_reviewer_after_ledger",
            _mail(
                state,
                existing_worker_result_routed_to_reviewer=True,
                holder="reviewer",
            ),
        )
        return
    if state.work_branch == "fresh_worker" and not state.fresh_worker_packet_sent:
        yield Transition(
            "fresh_worker_packet_sent_after_ledger",
            _mail(state, fresh_worker_packet_sent=True, holder="worker"),
        )
        return
    if state.work_branch == "fresh_worker" and not state.worker_result_routed_to_reviewer:
        yield Transition(
            "fresh_worker_result_routed_to_reviewer_after_ledger",
            _mail(
                state,
                worker_result_returned=True,
                worker_result_routed_to_reviewer=True,
                holder="reviewer",
            ),
        )
        return
    if not state.reviewer_result_passed:
        yield Transition(
            "reviewer_passes_reviewed_worker_result",
            replace(state, reviewer_result_passed=True, holder="controller"),
        )
        return
    if not state.pm_node_decision_prompt_delivered:
        yield Transition(
            "pm_node_decision_card_delivered",
            _prompt(state, pm_node_decision_prompt_delivered=True, holder="pm"),
        )
        return
    if not state.route_progress_recorded:
        yield Transition(
            "pm_records_progress_from_reviewed_packet",
            replace(
                state,
                route_progress_recorded=True,
                route_progress_source="reviewed_packet",
                holder="controller",
            ),
        )
        return
    yield Transition("reentry_loop_complete", replace(state, status="complete"))


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []

    if state.dynamic_launcher_used or state.launcher_prompt_contains_route_state:
        failures.append("resume used a dynamic launcher instead of the stable launcher")
    if (
        state.current_pointer_loaded
        or state.run_root_loaded
        or state.router_state_loaded
        or state.frontier_loaded
    ) and not state.stable_launcher_entered:
        failures.append("current-run state loaded before stable launcher entry")
    if state.heartbeat_self_keepalive_without_router:
        failures.append("resume wake self-classified keepalive instead of entering the router")
    if (
        state.entry_mode in {"heartbeat", "manual"}
        and (
            state.current_pointer_loaded
            or state.run_root_loaded
            or state.router_state_loaded
            or state.frontier_loaded
            or state.pm_decision_requested
        )
        and not state.resume_wake_recorded_to_router
    ):
        failures.append("resume loaded or acted on current state before recording the wake to the router")
    if state.heartbeat_trigger_evidence_loaded and state.heartbeat_interval_minutes != 1:
        failures.append("heartbeat resume trigger evidence was not one-minute cadence")
    if state.heartbeat_trigger_evidence_loaded and not state.heartbeat_trigger_bound_to_current_run:
        failures.append("heartbeat resume trigger evidence was not bound to the current run")
    if (
        state.entry_mode == "heartbeat"
        and (
            state.current_pointer_loaded
            or state.pm_decision_requested
            or state.route_progress_recorded
            or state.status == "complete"
        )
        and not _heartbeat_trigger_ready(state)
    ):
        failures.append("heartbeat resume continued before current-run one-minute trigger evidence")
    if state.run_root_loaded and not (
        state.current_pointer_loaded and state.current_pointer_valid
    ):
        failures.append("run root loaded before a valid current pointer")
    if state.old_run_control_state_reused:
        failures.append("old run control state was reused as current state")
    if state.router_state_loaded and not (
        state.run_root_loaded
        and state.run_root_matches_pointer
        and state.old_run_scan_done
        and state.old_run_control_state_quarantined
    ):
        failures.append("router_state loaded before current run root and old-state rejection")
    if state.packet_ledger_loaded and not state.router_state_loaded:
        failures.append("packet ledger loaded before router_state")
    if state.prompt_ledger_loaded and not state.packet_ledger_loaded:
        failures.append("prompt ledger loaded before packet ledger")
    if state.frontier_loaded and not state.prompt_ledger_loaded:
        failures.append("frontier loaded before prompt ledger")
    if state.visible_plan_restored_from_run and not state.frontier_loaded:
        failures.append("visible plan restored before execution frontier")
    if state.crew_memory_loaded and not (
        state.frontier_loaded and state.visible_plan_restored_from_run
    ):
        failures.append("crew memory loaded before execution frontier and visible plan restoration")
    if state.controller_relay_boundary_confirmed and not _loaded_current_run_state(state):
        failures.append("Controller relay boundary confirmed before loading current-run state")

    if state.controller_read_forbidden_body or state.sealed_body_read:
        failures.append("Controller read a sealed packet/result body")
    if (
        state.controller_authored_project_evidence
        or state.controller_advanced_route
        or state.controller_self_approved_pm_decision
    ):
        failures.append("Controller acted beyond relay-only authority")
    if state.chat_history_progress_inferred or state.pm_decision_from_chat_history:
        failures.append("resume inferred route progress or PM decision from chat history")

    if state.all_six_role_liveness_checked and not state.controller_relay_boundary_confirmed:
        failures.append("six-role liveness checked before Controller loaded current-run resume state")
    if state.host_role_rehydrate_requested and not state.all_six_role_liveness_checked:
        failures.append("host role rehydration requested before all six role liveness was checked")
    if state.timeout_unknown_treated_as_active:
        failures.append("timeout_unknown was treated as an active role")
    if state.missing_role_treated_as_waiting:
        failures.append("missing or cancelled role was treated as a legal wait")
    if (
        state.role_liveness_outcome in {"recovery_needed", "timeout_unknown"}
        and state.crew_restored
    ):
        failures.append("roles were restored as active after missing/cancelled/timeout liveness")
    if state.crew_roles_ready and not (
        state.host_role_rehydrate_requested
        and state.all_six_role_liveness_checked
        and state.all_roles_current_run_bound
        and (
        state.crew_restored
        or (state.crew_replaced and state.replacement_roles_seeded_from_memory)
        )
    ):
        failures.append("crew roles became ready without host rehydration, current-run binding, and restore or memory-seeded replacement")
    if state.host_role_rehydrate_requested and state.crew_roles_ready and not state.run_memory_injected_into_roles:
        failures.append("host restored resume roles before current-run memory was injected")
    if state.run_memory_injected_into_roles and not state.crew_rehydration_report_written and (
        state.pm_decision_requested or state.pm_decision_prompt_delivered or state.pm_decision_returned
    ):
        failures.append("PM resume path proceeded before crew rehydration report was written")
    if state.crew_replaced and not state.replacement_roles_seeded_from_memory:
        failures.append("replacement crew roles were not seeded from current-run memory")
    if state.crew_old_agent_ids_reused:
        failures.append("old task agent ids were reused as current live crew")
    if (
        state.pm_decision_requested
        or state.pm_decision_returned
        or state.route_progress_recorded
        or state.status == "complete"
    ) and not (
        state.host_role_rehydrate_requested
        and state.all_six_role_liveness_checked
        and state.run_memory_injected_into_roles
        and state.crew_rehydration_report_written
        and _lifecycle_flags_current(state)
    ):
        failures.append("PM resume or closure proceeded before live role rehydration, memory injection, report, and lifecycle reconciliation")

    if state.ambiguous_state == "ambiguous" and not (
        state.status == "blocked" and state.pm_recovery_requested
    ):
        failures.append("ambiguous resume state did not block for PM recovery")
    if state.ambiguous_state == "ambiguous" and state.pm_decision_requested:
        failures.append("PM decision was requested while resume state was ambiguous")

    if state.pm_decision_requested and not (
        _heartbeat_trigger_ready(state)
        and _lifecycle_flags_current(state)
        and _loaded_current_run_state(state)
        and state.controller_relay_boundary_confirmed
        and state.all_six_role_liveness_checked
        and state.crew_roles_ready
        and state.ambiguous_state == "clear"
    ):
        failures.append("PM decision requested before wake/router entry, state load, visible plan, six-role liveness, lifecycle reconciliation, relay boundary, crew recovery, and ambiguity clearance")
    if state.pm_decision_prompt_delivered and not state.pm_controller_reminder_included:
        failures.append("PM decision card omitted the Controller relay-only reminder")
    if state.pm_decision_returned and not state.pm_decision_prompt_delivered:
        failures.append("PM decision returned before PM decision prompt card")

    if state.prompt_deliveries > state.manifest_checks:
        failures.append("prompt card delivered without a matching manifest check")
    if state.prompt_deliveries and not state.system_card_identity_boundaries_verified:
        failures.append("prompt card delivered without verified identity-boundary header")
    if state.prompt_deliveries > state.manifest_check_requests:
        failures.append("prompt card delivered before manifest-check instruction")
    if state.manifest_checks > state.manifest_check_requests:
        failures.append("manifest checked without a current Controller instruction")
    if state.prompt_deliveries and not state.prompt_ledger_loaded:
        failures.append("prompt delivered before prompt ledger was loaded")
    if state.mail_deliveries > state.ledger_checks:
        failures.append("mail delivered without a matching packet-ledger check")
    if state.mail_deliveries and not state.packet_body_identity_boundaries_verified:
        failures.append("mail delivered without verified packet recipient identity boundary")
    if (
        state.existing_worker_result_routed_to_reviewer
        or state.worker_result_routed_to_reviewer
    ) and not state.result_body_identity_boundaries_verified:
        failures.append("worker result routed without verified completed-by identity boundary")
    if state.mail_deliveries > state.ledger_check_requests:
        failures.append("mail delivered before packet-ledger check instruction")
    if state.ledger_checks > state.ledger_check_requests:
        failures.append("packet ledger checked without a current Controller instruction")
    if state.mail_deliveries and not state.packet_ledger_loaded:
        failures.append("mail delivered before packet ledger was loaded")

    if state.fresh_worker_packet_sent and not state.reviewer_dispatch_allowed:
        failures.append("worker packet sent before router direct dispatch approval")
    if state.existing_worker_result_routed_to_reviewer and not (
        state.existing_worker_result_found and state.reviewer_dispatch_allowed
    ):
        failures.append("existing worker result routed without router direct dispatch")
    if state.worker_result_routed_to_reviewer and not (
        state.fresh_worker_packet_sent and state.reviewer_dispatch_allowed
    ):
        failures.append("fresh worker result routed without worker packet and router direct dispatch")
    if state.reviewer_result_passed and not (
        state.existing_worker_result_routed_to_reviewer or state.worker_result_routed_to_reviewer
    ):
        failures.append("reviewer passed a worker result that was not routed through packet mail")
    if state.route_progress_recorded and not (
        state.reviewer_result_passed
        and state.pm_node_decision_prompt_delivered
        and state.route_progress_source == "reviewed_packet"
    ):
        failures.append("route progress recorded without PM decision from reviewed packet evidence")
    if state.route_progress_source in {"chat_history", "controller"}:
        failures.append("route progress source was chat history or Controller inference")
    if state.status == "complete" and not state.route_progress_recorded:
        failures.append("resume completed before PM-recorded route progress from reviewed packet")

    return failures


def resume_reentry_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_resume_reentry_control_plane",
        description=(
            "Heartbeat and manual resume re-enter through a stable launcher, "
            "confirm one-minute heartbeat evidence when automated, load current-run "
            "state and ledgers, reconcile lifecycle flags, recover crew before PM "
            "decision, keep Controller relay-only, and gate prompt/mail/project "
            "progress through manifest, packet ledger, reviewer, and PM evidence."
        ),
        predicate=resume_reentry_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 36


def build_workflow() -> Workflow:
    return Workflow((ResumeReentryStep(),), name="flowpilot_resume_reentry")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


def _ready_for_pm(**changes: object) -> State:
    base = State(
        status="running",
        entry_mode="heartbeat",
        holder="controller",
        stable_launcher_entered=True,
        resume_wake_recorded_to_router=True,
        heartbeat_trigger_evidence_loaded=True,
        heartbeat_interval_minutes=1,
        heartbeat_trigger_bound_to_current_run=True,
        current_pointer_loaded=True,
        current_pointer_valid=True,
        run_root_loaded=True,
        run_root_matches_pointer=True,
        old_run_scan_done=True,
        old_run_control_state_quarantined=True,
        router_state_loaded=True,
        packet_ledger_loaded=True,
        prompt_ledger_loaded=True,
        frontier_loaded=True,
        visible_plan_restored_from_run=True,
        crew_memory_loaded=True,
        controller_relay_boundary_confirmed=True,
        all_six_role_liveness_checked=True,
        role_liveness_outcome="all_active",
        host_role_rehydrate_requested=True,
        crew_roles_ready=True,
        crew_restored=True,
        run_memory_injected_into_roles=True,
        crew_rehydration_report_written=True,
        all_roles_current_run_bound=True,
        crew_lifecycle_flags_current=True,
        capability_lifecycle_flags_current=True,
        officer_lifecycle_flags_current=True,
        ambiguous_state="clear",
    )
    return replace(base, **changes)


def _with_pm_decision(**changes: object) -> State:
    base = _ready_for_pm(
        pm_decision_requested=True,
        pm_decision_prompt_delivered=True,
        pm_controller_reminder_included=True,
        pm_decision_returned=True,
        prompt_deliveries=1,
        manifest_check_requests=1,
        manifest_checks=1,
        system_card_identity_boundaries_verified=True,
    )
    return replace(base, **changes)


def hazard_states() -> dict[str, State]:
    return {
        "dynamic_launcher_used": State(dynamic_launcher_used=True),
        "launcher_prompt_carries_route_state": State(
            stable_launcher_entered=True,
            launcher_prompt_contains_route_state=True,
        ),
        "heartbeat_self_keepalive_without_router": State(
            status="running",
            entry_mode="heartbeat",
            stable_launcher_entered=True,
            heartbeat_self_keepalive_without_router=True,
        ),
        "load_pointer_without_stable_launcher": State(current_pointer_loaded=True),
        "manual_resume_continues_without_router_wake": State(
            status="running",
            entry_mode="manual",
            stable_launcher_entered=True,
            current_pointer_loaded=True,
            current_pointer_valid=True,
        ),
        "heartbeat_continues_without_one_minute_trigger": State(
            status="running",
            entry_mode="heartbeat",
            stable_launcher_entered=True,
            resume_wake_recorded_to_router=True,
            current_pointer_loaded=True,
            current_pointer_valid=True,
        ),
        "heartbeat_trigger_wrong_interval": State(
            status="running",
            entry_mode="heartbeat",
            stable_launcher_entered=True,
            resume_wake_recorded_to_router=True,
            heartbeat_trigger_evidence_loaded=True,
            heartbeat_interval_minutes=5,
            heartbeat_trigger_bound_to_current_run=True,
        ),
        "heartbeat_trigger_not_current_run_bound": State(
            status="running",
            entry_mode="heartbeat",
            stable_launcher_entered=True,
            resume_wake_recorded_to_router=True,
            heartbeat_trigger_evidence_loaded=True,
            heartbeat_interval_minutes=1,
            heartbeat_trigger_bound_to_current_run=False,
        ),
        "run_root_without_valid_pointer": State(stable_launcher_entered=True, run_root_loaded=True),
        "router_state_before_old_run_rejection": State(
            stable_launcher_entered=True,
            current_pointer_loaded=True,
            current_pointer_valid=True,
            run_root_loaded=True,
            run_root_matches_pointer=True,
            router_state_loaded=True,
        ),
        "old_run_control_state_reused": _ready_for_pm(old_run_control_state_reused=True),
        "pm_decision_before_host_rehydrate": _ready_for_pm(
            host_role_rehydrate_requested=False,
            pm_decision_requested=True,
        ),
        "pm_decision_before_visible_plan_restore": _ready_for_pm(
            visible_plan_restored_from_run=False,
            crew_memory_loaded=False,
            pm_decision_requested=True,
        ),
        "pm_decision_before_six_role_liveness": _ready_for_pm(
            all_six_role_liveness_checked=False,
            pm_decision_requested=True,
        ),
        "pm_decision_before_crew_recovery": _ready_for_pm(
            crew_roles_ready=False,
            crew_restored=False,
            pm_decision_requested=True,
        ),
        "timeout_unknown_treated_as_active": _ready_for_pm(
            role_liveness_outcome="timeout_unknown",
            timeout_unknown_treated_as_active=True,
        ),
        "missing_role_treated_as_waiting": _ready_for_pm(
            role_liveness_outcome="recovery_needed",
            missing_role_treated_as_waiting=True,
        ),
        "pm_decision_before_run_memory_injection": _ready_for_pm(
            run_memory_injected_into_roles=False,
            crew_rehydration_report_written=False,
            pm_decision_requested=True,
        ),
        "six_memory_files_counted_without_role_rehydrate": _ready_for_pm(
            host_role_rehydrate_requested=False,
            crew_roles_ready=True,
            crew_restored=True,
            all_roles_current_run_bound=True,
            run_memory_injected_into_roles=False,
            crew_rehydration_report_written=False,
            pm_decision_requested=True,
        ),
        "pm_decision_before_lifecycle_reconciliation": _ready_for_pm(
            crew_lifecycle_flags_current=False,
            capability_lifecycle_flags_current=False,
            officer_lifecycle_flags_current=False,
            pm_decision_requested=True,
        ),
        "replacement_roles_without_memory_seed": _ready_for_pm(
            crew_restored=False,
            crew_replaced=True,
            replacement_roles_seeded_from_memory=False,
        ),
        "old_agent_ids_reused": _ready_for_pm(crew_old_agent_ids_reused=True),
        "ambiguous_state_does_not_block": _ready_for_pm(ambiguous_state="ambiguous"),
        "pm_decision_while_ambiguous": _ready_for_pm(
            ambiguous_state="ambiguous",
            pm_decision_requested=True,
        ),
        "pm_card_without_controller_reminder": _ready_for_pm(
            pm_decision_requested=True,
            pm_decision_prompt_delivered=True,
            pm_controller_reminder_included=False,
            prompt_deliveries=1,
            manifest_check_requests=1,
            manifest_checks=1,
        ),
        "prompt_without_manifest_check": _ready_for_pm(
            prompt_deliveries=1,
            manifest_check_requests=0,
            manifest_checks=0,
        ),
        "prompt_before_prompt_ledger": _ready_for_pm(
            prompt_ledger_loaded=False,
            frontier_loaded=False,
            crew_memory_loaded=False,
            prompt_deliveries=1,
            manifest_check_requests=1,
            manifest_checks=1,
        ),
        "mail_without_packet_ledger_check": _with_pm_decision(
            reviewer_dispatch_prompt_delivered=True,
            reviewer_dispatch_allowed=True,
            work_branch="fresh_worker",
            fresh_worker_packet_sent=True,
            mail_deliveries=1,
            ledger_check_requests=0,
            ledger_checks=0,
        ),
        "mail_before_packet_ledger_loaded": _with_pm_decision(
            packet_ledger_loaded=False,
            prompt_ledger_loaded=False,
            frontier_loaded=False,
            crew_memory_loaded=False,
            mail_deliveries=1,
            ledger_check_requests=1,
            ledger_checks=1,
        ),
        "controller_reads_sealed_body": _ready_for_pm(sealed_body_read=True),
        "controller_origin_project_evidence": _ready_for_pm(
            controller_authored_project_evidence=True,
        ),
        "controller_self_approves_pm_decision": _ready_for_pm(
            controller_self_approved_pm_decision=True,
        ),
        "progress_from_chat_history": _with_pm_decision(
            route_progress_recorded=True,
            route_progress_source="chat_history",
            chat_history_progress_inferred=True,
        ),
        "route_progress_without_reviewer": _with_pm_decision(
            pm_node_decision_prompt_delivered=True,
            route_progress_recorded=True,
            route_progress_source="reviewed_packet",
        ),
        "worker_packet_before_reviewer_dispatch": _with_pm_decision(
            fresh_worker_packet_sent=True,
            reviewer_dispatch_allowed=False,
            mail_deliveries=1,
            ledger_check_requests=1,
            ledger_checks=1,
        ),
        "existing_result_used_without_dispatch": _with_pm_decision(
            work_branch="existing_result",
            existing_worker_result_found=True,
            existing_worker_result_routed_to_reviewer=True,
            reviewer_dispatch_allowed=False,
            mail_deliveries=1,
            ledger_check_requests=1,
            ledger_checks=1,
        ),
        "complete_without_reviewed_progress": _ready_for_pm(status="complete"),
        "pm_decision_from_chat_history": _ready_for_pm(
            pm_decision_requested=True,
            pm_decision_from_chat_history=True,
        ),
    }


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "Action",
    "State",
    "Tick",
    "Transition",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "next_states",
    "resume_reentry_invariant",
]
