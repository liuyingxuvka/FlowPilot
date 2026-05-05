"""FlowGuard model for the FlowPilot startup PM/reviewer gate.

The runtime startup gate has only two authority roles:

- the human-like reviewer independently checks facts and writes a factual
  report with blockers;
- the project manager independently audits the current clean factual report,
  direct startup evidence, and report-only failure hypotheses before opening
  work beyond startup, or returns blockers to workers.

There is no third startup opener or runtime startup-check script in this model.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple


REQUIRED_ROLE_MEMORY_PACKETS = 6


@dataclass(frozen=True)
class State:
    startup_questions_asked: bool = False
    dialog_stopped_for_user_answers: bool = False
    background_agents_answer: str = "unknown"  # unknown | allow | single-agent | pause
    scheduled_continuation_answer: str = "unknown"  # unknown | allow | manual | pause
    display_surface_answer: str = "unknown"  # unknown | cockpit | chat | pause
    explicit_user_answer_recorded: bool = False
    startup_answer_provenance: str = "none"  # none | explicit_user_reply | inferred | default | naked
    agent_self_recorded_authorization: bool = False
    banner_emitted: bool = False
    cockpit_entry_action_done: bool = False
    cockpit_ui_opened: bool = False
    chat_route_sign_displayed: bool = False
    cockpit_open_failed: bool = False
    cockpit_capability_status: str = "unknown"  # unknown | available | unavailable | damaged
    run_directory_created: bool = False
    current_pointer_written: bool = False
    run_index_updated: bool = False
    prior_work_mode: str = "unknown"  # unknown | new | continue
    prior_work_import_packet_written: bool = False
    control_state_written_under_run_root: bool = False
    top_level_control_state_absent_or_quarantined: bool = False
    old_control_state_reused_as_current: bool = False
    route_file_written: bool = False
    canonical_state_written: bool = False
    execution_frontier_written: bool = False
    crew_ledger_current: bool = False
    role_memory_packets_current: int = 0
    live_subagents_started: bool = False
    live_agents_active: int = 0
    background_agents_capability_status: str = "unknown"  # unknown | available | unavailable | damaged
    live_subagents_current_task_fresh: bool = False
    fresh_agents_spawned_after_startup_answers: bool = False
    fresh_agents_spawned_after_route_allocation: bool = False
    historical_agent_ids_compared: bool = False
    reused_historical_agent_ids: bool = False
    single_agent_role_continuity_authorized: bool = False
    automated_continuation_ready: bool = False
    manual_resume_ready: bool = False
    scheduled_continuation_capability_status: str = "unknown"  # unknown | available | unavailable | damaged
    route_heartbeat_interval_minutes: int = 0
    actual_heartbeat_automation_checked: bool = False
    actual_heartbeat_interval_minutes: int = 0
    heartbeat_bound_to_current_run: bool = False
    heartbeat_current_run_binding_checked: bool = False
    heartbeat_same_name_only_checked: bool = False
    clean_start_requirement: str = "unknown"  # unknown | required | not_required
    old_route_cleanup_done: bool = False
    reviewer_checked_user_authorization: bool = False
    reviewer_checked_route_state_frontier: bool = False
    reviewer_checked_run_isolation: bool = False
    reviewer_checked_prior_work_boundary: bool = False
    reviewer_checked_old_route_assets: bool = False
    reviewer_checked_background_agents: bool = False
    reviewer_checked_live_agent_freshness: bool = False
    reviewer_checked_no_historical_agent_reuse: bool = False
    reviewer_checked_shadow_route: bool = False
    reviewer_checked_continuation_evidence: bool = False
    reviewer_checked_current_heartbeat_binding: bool = False
    reviewer_checked_display_surface_evidence: bool = False
    reviewer_probed_background_agent_capability: bool = False
    reviewer_probed_scheduled_continuation_capability: bool = False
    reviewer_probed_cockpit_capability: bool = False
    reviewer_verified_background_agent_fallback_needed: bool = False
    reviewer_verified_scheduled_continuation_fallback_needed: bool = False
    reviewer_verified_cockpit_fallback_needed: bool = False
    startup_reviewer_report_file_backed: bool = False
    pm_startup_activation_decision_file_backed: bool = False
    controller_direct_reviewer_recheck_requested: bool = False
    controller_inspected_router_hard_checks: bool = False
    controller_free_text_authority_used: bool = False
    worker_claimed_capability_unavailable: bool = False
    startup_review_status: str = "pending"  # pending | blocked | clean
    worker_remediation_done: bool = False
    pm_independent_gate_audit_done: bool = False
    pm_recorded_background_agent_fallback: bool = False
    pm_recorded_scheduled_continuation_fallback: bool = False
    pm_recorded_cockpit_fallback: bool = False
    pm_start_gate_decision: str = "pending"  # pending | return_to_worker | open
    reviewer_opened_start_gate: bool = False
    work_beyond_startup_allowed: bool = False
    child_skill_started: bool = False
    imagegen_started: bool = False
    implementation_started: bool = False
    route_execution_started: bool = False
    shadow_route_detected: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def startup_answers_complete(state: State) -> bool:
    return (
        state.startup_questions_asked
        and state.dialog_stopped_for_user_answers
        and state.background_agents_answer in {"allow", "single-agent"}
        and state.scheduled_continuation_answer in {"allow", "manual"}
        and state.display_surface_answer in {"cockpit", "chat"}
        and state.explicit_user_answer_recorded
        and state.startup_answer_provenance == "explicit_user_reply"
        and not state.agent_self_recorded_authorization
    )


def subagent_decision_matches_answer(state: State) -> bool:
    if state.background_agents_answer == "allow":
        live_agents_ready = (
            state.live_subagents_started
            and state.live_agents_active >= REQUIRED_ROLE_MEMORY_PACKETS
            and state.background_agents_capability_status == "available"
            and state.live_subagents_current_task_fresh
            and state.fresh_agents_spawned_after_startup_answers
            and state.fresh_agents_spawned_after_route_allocation
            and state.historical_agent_ids_compared
            and not state.reused_historical_agent_ids
            and not state.single_agent_role_continuity_authorized
        )
        reviewer_verified_fallback = (
            state.background_agents_capability_status in {"unavailable", "damaged"}
            and state.reviewer_probed_background_agent_capability
            and state.reviewer_verified_background_agent_fallback_needed
            and state.pm_recorded_background_agent_fallback
            and state.single_agent_role_continuity_authorized
            and not state.live_subagents_started
            and state.live_agents_active == 0
        )
        return live_agents_ready or reviewer_verified_fallback
    if state.background_agents_answer == "single-agent":
        return (
            state.single_agent_role_continuity_authorized
            and not state.live_subagents_started
            and state.live_agents_active == 0
        )
    return False


def automated_continuation_facts_ready(state: State) -> bool:
    return (
        state.automated_continuation_ready
        and not state.manual_resume_ready
        and state.scheduled_continuation_capability_status == "available"
        and state.route_heartbeat_interval_minutes == 1
        and state.actual_heartbeat_automation_checked
        and state.actual_heartbeat_interval_minutes == 1
        and state.heartbeat_bound_to_current_run
        and state.heartbeat_current_run_binding_checked
        and not state.heartbeat_same_name_only_checked
    )


def continuation_matches_answer(state: State) -> bool:
    if state.scheduled_continuation_answer == "allow":
        reviewer_verified_fallback = (
            state.scheduled_continuation_capability_status in {"unavailable", "damaged"}
            and state.reviewer_probed_scheduled_continuation_capability
            and state.reviewer_verified_scheduled_continuation_fallback_needed
            and state.pm_recorded_scheduled_continuation_fallback
            and state.manual_resume_ready
            and not state.automated_continuation_ready
        )
        return automated_continuation_facts_ready(state) or reviewer_verified_fallback
    if state.scheduled_continuation_answer == "manual":
        return state.manual_resume_ready and not state.automated_continuation_ready
    return False


def cleanup_matches_request(state: State) -> bool:
    if state.clean_start_requirement == "required":
        return state.old_route_cleanup_done
    return state.clean_start_requirement == "not_required"


def display_entry_action_matches_answer(state: State) -> bool:
    if state.display_surface_answer == "cockpit":
        cockpit_ready = (
            state.cockpit_entry_action_done
            and state.cockpit_capability_status == "available"
            and state.cockpit_ui_opened
            and not state.chat_route_sign_displayed
            and not state.cockpit_open_failed
        )
        reviewer_verified_fallback = (
            state.cockpit_capability_status in {"unavailable", "damaged"}
            and state.reviewer_probed_cockpit_capability
            and state.reviewer_verified_cockpit_fallback_needed
            and state.pm_recorded_cockpit_fallback
            and state.cockpit_entry_action_done
            and state.chat_route_sign_displayed
            and not state.cockpit_ui_opened
        )
        return cockpit_ready or reviewer_verified_fallback
    if state.display_surface_answer == "chat":
        return (
            state.cockpit_entry_action_done
            and state.chat_route_sign_displayed
            and not state.cockpit_ui_opened
        )
    return False


def run_isolation_ready(state: State) -> bool:
    prior_work_resolved = state.prior_work_mode == "new" or (
        state.prior_work_mode == "continue"
        and state.prior_work_import_packet_written
    )
    return (
        state.run_directory_created
        and state.current_pointer_written
        and state.run_index_updated
        and prior_work_resolved
        and state.control_state_written_under_run_root
        and state.top_level_control_state_absent_or_quarantined
        and not state.old_control_state_reused_as_current
    )


def reviewer_fact_scope_complete(state: State) -> bool:
    background_agent_scope = state.reviewer_checked_background_agents
    if state.background_agents_answer == "allow":
        live_agent_scope = (
            state.background_agents_capability_status == "available"
            and state.reviewer_checked_live_agent_freshness
            and state.reviewer_checked_no_historical_agent_reuse
        )
        fallback_scope = (
            state.background_agents_capability_status in {"unavailable", "damaged"}
            and state.reviewer_verified_background_agent_fallback_needed
        )
        background_agent_scope = (
            background_agent_scope
            and state.reviewer_probed_background_agent_capability
            and (live_agent_scope or fallback_scope)
        )
    continuation_scope = state.reviewer_checked_continuation_evidence
    if state.scheduled_continuation_answer == "allow":
        heartbeat_scope = (
            state.scheduled_continuation_capability_status == "available"
            and state.actual_heartbeat_automation_checked
            and state.actual_heartbeat_interval_minutes == 1
            and state.heartbeat_bound_to_current_run
            and state.heartbeat_current_run_binding_checked
            and state.reviewer_checked_current_heartbeat_binding
            and not state.heartbeat_same_name_only_checked
        )
        fallback_scope = (
            state.scheduled_continuation_capability_status in {"unavailable", "damaged"}
            and state.reviewer_verified_scheduled_continuation_fallback_needed
        )
        continuation_scope = (
            continuation_scope
            and state.reviewer_probed_scheduled_continuation_capability
            and (heartbeat_scope or fallback_scope)
        )
    display_scope = state.reviewer_checked_display_surface_evidence
    if state.display_surface_answer == "cockpit":
        display_scope = (
            display_scope
            and state.reviewer_probed_cockpit_capability
            and (
                (state.cockpit_capability_status == "available" and state.cockpit_ui_opened)
                or (
                    state.cockpit_capability_status in {"unavailable", "damaged"}
                    and state.reviewer_verified_cockpit_fallback_needed
                )
            )
        )
    return (
        state.reviewer_checked_user_authorization
        and state.reviewer_checked_route_state_frontier
        and state.reviewer_checked_run_isolation
        and state.reviewer_checked_prior_work_boundary
        and state.reviewer_checked_old_route_assets
        and background_agent_scope
        and state.reviewer_checked_shadow_route
        and continuation_scope
        and display_scope
    )


def startup_ready_for_pm_open(state: State) -> bool:
    return (
        startup_answers_complete(state)
        and state.banner_emitted
        and run_isolation_ready(state)
        and state.route_file_written
        and state.canonical_state_written
        and state.execution_frontier_written
        and state.crew_ledger_current
        and state.role_memory_packets_current == REQUIRED_ROLE_MEMORY_PACKETS
        and subagent_decision_matches_answer(state)
        and continuation_matches_answer(state)
        and display_entry_action_matches_answer(state)
        and cleanup_matches_request(state)
        and reviewer_fact_scope_complete(state)
        and state.startup_review_status == "clean"
        and state.startup_reviewer_report_file_backed
        and state.pm_independent_gate_audit_done
        and state.pm_startup_activation_decision_file_backed
        and not state.reviewer_opened_start_gate
        and not state.shadow_route_detected
    )


def work_started(state: State) -> bool:
    return (
        state.child_skill_started
        or state.imagegen_started
        or state.implementation_started
        or state.route_execution_started
    )


def next_safe_states(state: State) -> Iterable[Transition]:
    if not state.startup_questions_asked:
        yield Transition("startup_three_questions_asked", replace(state, startup_questions_asked=True))
        return
    if not state.dialog_stopped_for_user_answers:
        yield Transition("startup_dialog_stopped_for_user_answers", replace(state, dialog_stopped_for_user_answers=True))
        return
    if state.background_agents_answer == "unknown":
        yield Transition("background_agents_allowed", replace(state, background_agents_answer="allow"))
        yield Transition("background_agents_declined_single_agent", replace(state, background_agents_answer="single-agent"))
        return
    if state.scheduled_continuation_answer == "unknown":
        yield Transition("scheduled_continuation_allowed", replace(state, scheduled_continuation_answer="allow"))
        yield Transition("scheduled_continuation_declined_manual", replace(state, scheduled_continuation_answer="manual"))
        return
    if state.display_surface_answer == "unknown":
        yield Transition("cockpit_ui_requested", replace(state, display_surface_answer="cockpit"))
        yield Transition("chat_route_sign_requested", replace(state, display_surface_answer="chat"))
        return
    if not state.explicit_user_answer_recorded:
        yield Transition(
            "explicit_startup_answers_recorded",
            replace(
                state,
                explicit_user_answer_recorded=True,
                startup_answer_provenance="explicit_user_reply",
            ),
        )
        return
    if not state.banner_emitted:
        yield Transition("startup_banner_emitted_after_answers", replace(state, banner_emitted=True))
        return
    if not state.run_directory_created:
        yield Transition("run_directory_created", replace(state, run_directory_created=True))
        return
    if not state.current_pointer_written:
        yield Transition("current_pointer_written", replace(state, current_pointer_written=True))
        return
    if not state.run_index_updated:
        yield Transition("run_index_updated", replace(state, run_index_updated=True))
        return
    if state.prior_work_mode == "unknown":
        yield Transition("new_task_no_prior_import", replace(state, prior_work_mode="new"))
        yield Transition("continue_previous_work_selected", replace(state, prior_work_mode="continue"))
        return
    if state.prior_work_mode == "continue" and not state.prior_work_import_packet_written:
        yield Transition("prior_work_import_packet_written", replace(state, prior_work_import_packet_written=True))
        return
    if not state.control_state_written_under_run_root:
        yield Transition("control_state_written_under_run_root", replace(state, control_state_written_under_run_root=True))
        return
    if not state.top_level_control_state_absent_or_quarantined:
        yield Transition("top_level_control_state_absent_or_quarantined", replace(state, top_level_control_state_absent_or_quarantined=True))
        return
    if not state.route_file_written:
        yield Transition("route_file_written", replace(state, route_file_written=True))
        return
    if not state.canonical_state_written:
        yield Transition("canonical_state_written", replace(state, canonical_state_written=True))
        return
    if not state.execution_frontier_written:
        yield Transition("execution_frontier_written", replace(state, execution_frontier_written=True))
        return
    if not state.cockpit_entry_action_done:
        if state.display_surface_answer == "cockpit" and state.cockpit_capability_status == "unknown":
            yield Transition(
                "cockpit_ui_opened_for_startup",
                replace(
                    state,
                    cockpit_entry_action_done=True,
                    cockpit_ui_opened=True,
                    cockpit_capability_status="available",
                ),
            )
            yield Transition(
                "cockpit_capability_unavailable_detected",
                replace(
                    state,
                    cockpit_open_failed=True,
                    cockpit_capability_status="unavailable",
                    worker_claimed_capability_unavailable=True,
                ),
            )
            return
        if state.display_surface_answer == "cockpit" and state.pm_recorded_cockpit_fallback:
            yield Transition(
                "chat_route_sign_displayed_after_pm_cockpit_fallback",
                replace(state, cockpit_entry_action_done=True, chat_route_sign_displayed=True),
            )
            return
        elif state.display_surface_answer == "chat":
            yield Transition(
                "startup_route_sign_displayed_in_chat",
                replace(state, cockpit_entry_action_done=True, chat_route_sign_displayed=True),
            )
            return
    if not state.crew_ledger_current:
        yield Transition("crew_ledger_current", replace(state, crew_ledger_current=True))
        return
    if state.role_memory_packets_current < REQUIRED_ROLE_MEMORY_PACKETS:
        yield Transition("role_memory_packets_current", replace(state, role_memory_packets_current=REQUIRED_ROLE_MEMORY_PACKETS))
        return
    if (
        state.background_agents_answer == "allow"
        and state.background_agents_capability_status == "unknown"
    ):
        yield Transition(
            "fresh_live_subagents_started",
            replace(
                state,
                background_agents_capability_status="available",
                live_subagents_started=True,
                live_agents_active=REQUIRED_ROLE_MEMORY_PACKETS,
                live_subagents_current_task_fresh=True,
                fresh_agents_spawned_after_startup_answers=True,
                fresh_agents_spawned_after_route_allocation=True,
                historical_agent_ids_compared=True,
                reused_historical_agent_ids=False,
            ),
        )
        yield Transition(
            "background_agent_capability_unavailable_detected",
            replace(
                state,
                background_agents_capability_status="unavailable",
                worker_claimed_capability_unavailable=True,
            ),
        )
        return
    if state.background_agents_answer == "single-agent" and not state.single_agent_role_continuity_authorized:
        yield Transition("single_agent_role_continuity_authorized", replace(state, single_agent_role_continuity_authorized=True))
        return
    if (
        state.scheduled_continuation_answer == "allow"
        and state.scheduled_continuation_capability_status == "unknown"
    ):
        yield Transition(
            "automated_heartbeat_factually_verified",
            replace(
                state,
                scheduled_continuation_capability_status="available",
                automated_continuation_ready=True,
                route_heartbeat_interval_minutes=1,
                actual_heartbeat_automation_checked=True,
                actual_heartbeat_interval_minutes=1,
                heartbeat_bound_to_current_run=True,
                heartbeat_current_run_binding_checked=True,
            ),
        )
        yield Transition(
            "scheduled_continuation_capability_unavailable_detected",
            replace(
                state,
                scheduled_continuation_capability_status="unavailable",
                worker_claimed_capability_unavailable=True,
            ),
        )
        return
    if state.scheduled_continuation_answer == "manual" and not state.manual_resume_ready:
        yield Transition("manual_resume_ready", replace(state, manual_resume_ready=True))
        return
    if state.clean_start_requirement == "unknown":
        yield Transition("clean_start_required_by_user", replace(state, clean_start_requirement="required"))
        yield Transition("clean_start_not_required", replace(state, clean_start_requirement="not_required"))
        return
    if state.clean_start_requirement == "required" and not state.old_route_cleanup_done:
        yield Transition("old_route_cleanup_verified", replace(state, old_route_cleanup_done=True))
        return
    if not reviewer_fact_scope_complete(state):
        reviewer_changes = {
            "reviewer_checked_user_authorization": True,
            "reviewer_checked_route_state_frontier": True,
            "reviewer_checked_run_isolation": True,
            "reviewer_checked_prior_work_boundary": True,
            "reviewer_checked_old_route_assets": True,
            "reviewer_checked_background_agents": True,
            "reviewer_checked_live_agent_freshness": True,
            "reviewer_checked_no_historical_agent_reuse": True,
            "reviewer_checked_shadow_route": True,
            "reviewer_checked_continuation_evidence": True,
            "reviewer_checked_current_heartbeat_binding": True,
            "reviewer_checked_display_surface_evidence": True,
            "reviewer_probed_background_agent_capability": True,
            "reviewer_probed_scheduled_continuation_capability": True,
            "reviewer_probed_cockpit_capability": True,
        }
        if state.background_agents_capability_status in {"unavailable", "damaged"}:
            reviewer_changes["reviewer_verified_background_agent_fallback_needed"] = True
            reviewer_changes["reviewer_checked_live_agent_freshness"] = False
            reviewer_changes["reviewer_checked_no_historical_agent_reuse"] = False
        if state.scheduled_continuation_capability_status in {"unavailable", "damaged"}:
            reviewer_changes["reviewer_verified_scheduled_continuation_fallback_needed"] = True
            reviewer_changes["reviewer_checked_current_heartbeat_binding"] = False
        if state.cockpit_capability_status in {"unavailable", "damaged"}:
            reviewer_changes["reviewer_verified_cockpit_fallback_needed"] = True
        yield Transition(
            "reviewer_independently_checked_startup_facts",
            replace(state, **reviewer_changes),
        )
        return
    if state.startup_review_status == "pending":
        if not state.worker_remediation_done:
            yield Transition(
                "startup_preflight_reviewer_fact_report_blocked",
                replace(state, startup_review_status="blocked", startup_reviewer_report_file_backed=True),
            )
        yield Transition(
            "startup_preflight_reviewer_fact_report_clean",
            replace(state, startup_review_status="clean", startup_reviewer_report_file_backed=True),
        )
        return
    if state.startup_review_status == "blocked" and state.pm_start_gate_decision == "pending":
        yield Transition("pm_returns_startup_blockers_to_worker", replace(state, pm_start_gate_decision="return_to_worker"))
        return
    if state.pm_start_gate_decision == "return_to_worker" and not state.worker_remediation_done:
        yield Transition(
            "startup_worker_remediation_completed",
            replace(
                state,
                worker_remediation_done=True,
                startup_review_status="pending",
                startup_reviewer_report_file_backed=False,
                pm_start_gate_decision="pending",
                pm_startup_activation_decision_file_backed=False,
                reviewer_checked_user_authorization=False,
                reviewer_checked_route_state_frontier=False,
                reviewer_checked_run_isolation=False,
                reviewer_checked_prior_work_boundary=False,
                reviewer_checked_old_route_assets=False,
                reviewer_checked_background_agents=False,
                reviewer_checked_live_agent_freshness=False,
                reviewer_checked_no_historical_agent_reuse=False,
                reviewer_checked_shadow_route=False,
                reviewer_checked_continuation_evidence=False,
                reviewer_checked_current_heartbeat_binding=False,
                reviewer_checked_display_surface_evidence=False,
                reviewer_probed_background_agent_capability=False,
                reviewer_probed_scheduled_continuation_capability=False,
                reviewer_probed_cockpit_capability=False,
                reviewer_verified_background_agent_fallback_needed=False,
                reviewer_verified_scheduled_continuation_fallback_needed=False,
                reviewer_verified_cockpit_fallback_needed=False,
                pm_independent_gate_audit_done=False,
                pm_recorded_background_agent_fallback=False,
                pm_recorded_scheduled_continuation_fallback=False,
                pm_recorded_cockpit_fallback=False,
            ),
        )
        return
    if (
        state.startup_review_status == "clean"
        and not state.pm_independent_gate_audit_done
        and state.pm_start_gate_decision == "pending"
    ):
        pm_audit_changes = {"pm_independent_gate_audit_done": True}
        if state.reviewer_verified_background_agent_fallback_needed:
            pm_audit_changes.update(
                {
                    "pm_recorded_background_agent_fallback": True,
                    "single_agent_role_continuity_authorized": True,
                }
            )
        if state.reviewer_verified_scheduled_continuation_fallback_needed:
            pm_audit_changes.update(
                {
                    "pm_recorded_scheduled_continuation_fallback": True,
                    "manual_resume_ready": True,
                }
            )
        if state.reviewer_verified_cockpit_fallback_needed:
            pm_audit_changes["pm_recorded_cockpit_fallback"] = True
        yield Transition(
            "pm_independently_audited_startup_gate",
            replace(state, **pm_audit_changes),
        )
        return
    if state.startup_review_status == "clean" and state.pm_start_gate_decision == "pending":
        yield Transition(
            "pm_start_gate_opened_from_fact_report",
            replace(
                state,
                pm_start_gate_decision="open",
                pm_startup_activation_decision_file_backed=True,
                work_beyond_startup_allowed=True,
            ),
        )
        return
    if not state.route_execution_started:
        yield Transition("route_execution_started", replace(state, route_execution_started=True))
        return
    if not state.child_skill_started:
        yield Transition("child_skill_started", replace(state, child_skill_started=True))
        return
    if not state.imagegen_started:
        yield Transition("imagegen_started", replace(state, imagegen_started=True))
        return
    if not state.implementation_started:
        yield Transition("implementation_started", replace(state, implementation_started=True))


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.banner_emitted and not startup_answers_complete(state):
        failures.append("startup banner emitted before all three explicit startup answers")
    if state.explicit_user_answer_recorded and state.startup_answer_provenance != "explicit_user_reply":
        failures.append("startup answers were recorded without explicit_user_reply provenance")
    if state.explicit_user_answer_recorded and (
        state.background_agents_answer not in {"allow", "single-agent"}
        or state.scheduled_continuation_answer not in {"allow", "manual"}
        or state.display_surface_answer not in {"cockpit", "chat"}
    ):
        failures.append("startup answers were recorded with illegal enum values")
    if (
        not state.dialog_stopped_for_user_answers
        and (
            state.background_agents_answer != "unknown"
            or state.scheduled_continuation_answer != "unknown"
            or state.display_surface_answer != "unknown"
            or state.explicit_user_answer_recorded
            or state.banner_emitted
            or state.cockpit_entry_action_done
            or state.cockpit_ui_opened
            or state.chat_route_sign_displayed
            or state.run_directory_created
            or state.current_pointer_written
            or state.run_index_updated
            or state.control_state_written_under_run_root
            or state.route_file_written
            or state.live_subagents_started
            or state.live_agents_active
            or state.live_subagents_current_task_fresh
            or state.reused_historical_agent_ids
            or state.single_agent_role_continuity_authorized
            or state.automated_continuation_ready
            or state.manual_resume_ready
            or state.work_beyond_startup_allowed
            or work_started(state)
        )
    ):
        failures.append("startup proceeded after asking questions without stopping for the user's reply")
    if state.reviewer_opened_start_gate:
        failures.append("reviewer attempted to open the PM-owned startup gate")
    if state.old_control_state_reused_as_current:
        failures.append("old control state was reused as current run state")
    if (
        state.startup_review_status == "clean"
        and not (
            state.reviewer_checked_run_isolation
            and state.reviewer_checked_prior_work_boundary
        )
    ):
        failures.append("reviewer wrote a clean startup report without checking run isolation and prior-work boundary")
    if state.startup_review_status == "clean" and not reviewer_fact_scope_complete(state):
        failures.append("reviewer wrote a clean startup report without independently checking required facts")
    if state.startup_review_status in {"blocked", "clean"} and not state.startup_reviewer_report_file_backed:
        failures.append("reviewer startup fact report was accepted without a file-backed report envelope")
    if state.pm_start_gate_decision == "open" and not startup_ready_for_pm_open(state):
        failures.append("PM opened startup without a current clean factual reviewer report, verified startup facts, and independent PM audit")
    if state.pm_start_gate_decision == "open" and state.startup_review_status != "clean":
        failures.append("PM opened startup without a clean reviewer report")
    if state.pm_start_gate_decision == "open" and not state.pm_startup_activation_decision_file_backed:
        failures.append("PM startup activation was accepted without a file-backed decision envelope")
    if state.pm_start_gate_decision == "open" and not state.pm_independent_gate_audit_done:
        failures.append("PM opened startup without independently auditing startup gate evidence")
    if state.controller_direct_reviewer_recheck_requested:
        failures.append("Controller directly requested reviewer recheck through free text instead of router-authorized mail")
    if state.controller_inspected_router_hard_checks:
        failures.append("Controller inspected router hard-check internals instead of using black-box router actions")
    if state.controller_free_text_authority_used:
        failures.append("Controller free text was treated as role authority")
    if state.pm_start_gate_decision == "open" and not cleanup_matches_request(state):
        failures.append("PM opened startup before old-route cleanup matched the user request")
    if state.pm_start_gate_decision == "open" and not run_isolation_ready(state):
        failures.append("PM opened startup before active run isolation was complete")
    if state.startup_review_status == "blocked" and state.work_beyond_startup_allowed:
        failures.append("work beyond startup was allowed despite blocking reviewer findings")
    if state.worker_remediation_done and state.pm_start_gate_decision == "open" and state.startup_review_status != "clean":
        failures.append("worker remediation was not rechecked by the reviewer before PM start")
    if state.agent_self_recorded_authorization and (
        state.explicit_user_answer_recorded
        or state.single_agent_role_continuity_authorized
        or state.manual_resume_ready
    ):
        failures.append("agent self-recorded startup authorization without explicit user answer")
    if state.cockpit_ui_opened and state.display_surface_answer != "cockpit":
        failures.append("Cockpit UI was opened without the user's startup display answer")
    if (
        state.chat_route_sign_displayed
        and state.display_surface_answer != "chat"
        and not (
            state.display_surface_answer == "cockpit"
            and state.pm_recorded_cockpit_fallback
            and state.reviewer_verified_cockpit_fallback_needed
        )
    ):
        failures.append("chat route sign was used as startup display despite the user's Cockpit answer")
    if (
        state.display_surface_answer == "cockpit"
        and state.startup_review_status == "clean"
        and not (
            (
                state.cockpit_capability_status == "available"
                and state.cockpit_ui_opened
            )
            or (
                state.cockpit_capability_status in {"unavailable", "damaged"}
                and state.reviewer_verified_cockpit_fallback_needed
            )
        )
    ):
        failures.append("reviewer accepted Cockpit startup display before the UI was opened")
    if state.display_surface_answer == "chat" and state.startup_review_status == "clean" and not state.chat_route_sign_displayed:
        failures.append("reviewer accepted chat startup display before the route sign appeared in chat")
    if state.pm_start_gate_decision == "open" and not display_entry_action_matches_answer(state):
        failures.append("PM opened startup before the display entry action matched the user's fourth startup answer")
    if (
        state.single_agent_role_continuity_authorized
        and state.background_agents_answer != "single-agent"
        and not (
            state.background_agents_answer == "allow"
            and state.pm_recorded_background_agent_fallback
            and state.reviewer_verified_background_agent_fallback_needed
        )
    ):
        failures.append("single-agent role continuity was authorized without the user's single-agent answer")
    if state.live_subagents_started and state.background_agents_answer != "allow":
        failures.append("live subagents were started without the user's live-agent answer")
    if state.live_agents_active and state.background_agents_answer != "allow":
        failures.append("active live subagents exist without the user's live-agent answer")
    if (
        state.startup_review_status == "clean"
        and state.background_agents_answer == "allow"
        and state.background_agents_capability_status == "available"
        and state.live_agents_active < REQUIRED_ROLE_MEMORY_PACKETS
    ):
        failures.append("reviewer accepted live-agent startup without six active subagents")
    if (
        state.startup_review_status == "clean"
        and state.background_agents_answer == "allow"
        and state.background_agents_capability_status == "available"
        and not (
            state.live_subagents_current_task_fresh
            and state.fresh_agents_spawned_after_startup_answers
            and state.fresh_agents_spawned_after_route_allocation
            and state.historical_agent_ids_compared
            and not state.reused_historical_agent_ids
        )
    ):
        failures.append("reviewer accepted live-agent startup without current-task fresh agent ids")
    if (
        state.startup_review_status == "clean"
        and state.background_agents_answer == "allow"
        and state.background_agents_capability_status == "available"
        and not (
            state.reviewer_checked_live_agent_freshness
            and state.reviewer_checked_no_historical_agent_reuse
        )
    ):
        failures.append("reviewer wrote a clean startup report without checking live-agent freshness and historical id reuse")
    if state.pm_start_gate_decision == "open" and state.reused_historical_agent_ids:
        failures.append("PM opened startup while current live-agent evidence reused historical agent ids")
    if (
        state.manual_resume_ready
        and state.scheduled_continuation_answer != "manual"
        and not (
            state.scheduled_continuation_answer == "allow"
            and state.pm_recorded_scheduled_continuation_fallback
            and state.reviewer_verified_scheduled_continuation_fallback_needed
        )
    ):
        failures.append("manual resume was recorded without the user's manual-resume answer")
    if state.automated_continuation_ready and state.scheduled_continuation_answer != "allow":
        failures.append("automated continuation was recorded without the user's scheduled-continuation answer")
    if (
        state.scheduled_continuation_answer == "allow"
        and state.startup_review_status == "clean"
        and not (
            automated_continuation_facts_ready(state)
            or (
                state.scheduled_continuation_capability_status
                in {"unavailable", "damaged"}
                and state.reviewer_verified_scheduled_continuation_fallback_needed
            )
        )
    ):
        failures.append("reviewer accepted automated continuation without verified one-minute route heartbeat facts")
    if (
        state.scheduled_continuation_answer == "allow"
        and state.scheduled_continuation_capability_status == "available"
        and state.automated_continuation_ready
        and (
            not state.heartbeat_bound_to_current_run
            or not state.heartbeat_current_run_binding_checked
            or state.heartbeat_same_name_only_checked
        )
    ):
        failures.append("heartbeat verification did not prove the automation is attached to the current run")
    if state.pm_recorded_background_agent_fallback and not (
        state.reviewer_probed_background_agent_capability
        and state.reviewer_verified_background_agent_fallback_needed
    ):
        failures.append("PM recorded single-agent fallback without reviewer-verified background-agent capability evidence")
    if state.pm_recorded_scheduled_continuation_fallback and not (
        state.reviewer_probed_scheduled_continuation_capability
        and state.reviewer_verified_scheduled_continuation_fallback_needed
    ):
        failures.append("PM recorded manual-resume fallback without reviewer-verified scheduled-continuation evidence")
    if state.pm_recorded_cockpit_fallback and not (
        state.reviewer_probed_cockpit_capability
        and state.reviewer_verified_cockpit_fallback_needed
    ):
        failures.append("PM recorded chat-display fallback without reviewer-verified Cockpit evidence")
    if state.pm_start_gate_decision == "open" and (
        (
            state.background_agents_answer == "allow"
            and state.background_agents_capability_status == "unknown"
        )
        or (
            state.scheduled_continuation_answer == "allow"
            and state.scheduled_continuation_capability_status == "unknown"
        )
        or (
            state.display_surface_answer == "cockpit"
            and state.cockpit_capability_status == "unknown"
        )
    ):
        failures.append("PM opened startup while requested capability status was still ambiguous")
    if work_started(state) and not state.work_beyond_startup_allowed:
        failures.append("work beyond startup started before PM allowed work from the factual reviewer report")
    if state.shadow_route_detected and state.work_beyond_startup_allowed:
        failures.append("shadow route was allowed through PM startup opening")
    return failures


def _ready_base(**changes: object) -> State:
    base = State(
        startup_questions_asked=True,
        dialog_stopped_for_user_answers=True,
        background_agents_answer="allow",
        scheduled_continuation_answer="allow",
        display_surface_answer="cockpit",
        explicit_user_answer_recorded=True,
        startup_answer_provenance="explicit_user_reply",
        banner_emitted=True,
        run_directory_created=True,
        current_pointer_written=True,
        run_index_updated=True,
        prior_work_mode="new",
        control_state_written_under_run_root=True,
        top_level_control_state_absent_or_quarantined=True,
        route_file_written=True,
        canonical_state_written=True,
        execution_frontier_written=True,
        cockpit_entry_action_done=True,
        cockpit_ui_opened=True,
        cockpit_capability_status="available",
        crew_ledger_current=True,
        role_memory_packets_current=REQUIRED_ROLE_MEMORY_PACKETS,
        background_agents_capability_status="available",
        live_subagents_started=True,
        live_agents_active=REQUIRED_ROLE_MEMORY_PACKETS,
        live_subagents_current_task_fresh=True,
        fresh_agents_spawned_after_startup_answers=True,
        fresh_agents_spawned_after_route_allocation=True,
        historical_agent_ids_compared=True,
        reused_historical_agent_ids=False,
        scheduled_continuation_capability_status="available",
        automated_continuation_ready=True,
        route_heartbeat_interval_minutes=1,
        actual_heartbeat_automation_checked=True,
        actual_heartbeat_interval_minutes=1,
        heartbeat_bound_to_current_run=True,
        heartbeat_current_run_binding_checked=True,
        clean_start_requirement="not_required",
        reviewer_checked_user_authorization=True,
        reviewer_checked_route_state_frontier=True,
        reviewer_checked_run_isolation=True,
        reviewer_checked_prior_work_boundary=True,
        reviewer_checked_old_route_assets=True,
        reviewer_checked_background_agents=True,
        reviewer_checked_live_agent_freshness=True,
        reviewer_checked_no_historical_agent_reuse=True,
        reviewer_checked_shadow_route=True,
        reviewer_checked_continuation_evidence=True,
        reviewer_checked_current_heartbeat_binding=True,
        reviewer_checked_display_surface_evidence=True,
        reviewer_probed_background_agent_capability=True,
        reviewer_probed_scheduled_continuation_capability=True,
        reviewer_probed_cockpit_capability=True,
        startup_review_status="clean",
        startup_reviewer_report_file_backed=True,
        pm_independent_gate_audit_done=True,
        pm_startup_activation_decision_file_backed=True,
    )
    return replace(base, **changes)


def hazard_states() -> dict[str, State]:
    return {
        "banner_before_three_answers": State(startup_questions_asked=True, banner_emitted=True),
        "answers_recorded_without_dialog_stop": State(
            startup_questions_asked=True,
            background_agents_answer="allow",
            scheduled_continuation_answer="allow",
            display_surface_answer="cockpit",
            explicit_user_answer_recorded=True,
            startup_answer_provenance="explicit_user_reply",
        ),
        "answers_recorded_with_inferred_provenance": State(
            startup_questions_asked=True,
            dialog_stopped_for_user_answers=True,
            background_agents_answer="allow",
            scheduled_continuation_answer="manual",
            display_surface_answer="chat",
            explicit_user_answer_recorded=True,
            startup_answer_provenance="inferred",
        ),
        "answers_recorded_with_naked_provenance": State(
            startup_questions_asked=True,
            dialog_stopped_for_user_answers=True,
            background_agents_answer="allow",
            scheduled_continuation_answer="manual",
            display_surface_answer="chat",
            explicit_user_answer_recorded=True,
            startup_answer_provenance="naked",
        ),
        "answers_recorded_with_illegal_value": State(
            startup_questions_asked=True,
            dialog_stopped_for_user_answers=True,
            background_agents_answer="assistant-default-long-text",
            scheduled_continuation_answer="manual",
            display_surface_answer="chat",
            explicit_user_answer_recorded=True,
            startup_answer_provenance="explicit_user_reply",
        ),
        "cockpit_requested_but_not_opened": _ready_base(
            cockpit_entry_action_done=False,
            cockpit_ui_opened=False,
            pm_start_gate_decision="open",
            work_beyond_startup_allowed=True,
        ),
        "chat_requested_but_not_displayed": _ready_base(
            display_surface_answer="chat",
            cockpit_entry_action_done=False,
            cockpit_ui_opened=False,
            chat_route_sign_displayed=False,
            pm_start_gate_decision="open",
            work_beyond_startup_allowed=True,
        ),
        "chat_used_despite_cockpit_answer": _ready_base(
            cockpit_ui_opened=False,
            chat_route_sign_displayed=True,
            pm_start_gate_decision="open",
            work_beyond_startup_allowed=True,
        ),
        "reviewer_clean_without_fact_checks": _ready_base(
            reviewer_checked_continuation_evidence=False,
        ),
        "reviewer_clean_report_not_file_backed": _ready_base(
            startup_reviewer_report_file_backed=False,
        ),
        "pm_opens_from_inline_activation_decision": _ready_base(
            pm_startup_activation_decision_file_backed=False,
            pm_start_gate_decision="open",
            work_beyond_startup_allowed=True,
        ),
        "controller_directs_reviewer_recheck": _ready_base(
            controller_direct_reviewer_recheck_requested=True,
        ),
        "controller_reads_router_hard_checks": _ready_base(
            controller_inspected_router_hard_checks=True,
        ),
        "controller_free_text_has_role_authority": _ready_base(
            controller_free_text_authority_used=True,
        ),
        "reviewer_clean_without_run_isolation_check": _ready_base(
            reviewer_checked_run_isolation=False,
            reviewer_checked_prior_work_boundary=False,
        ),
        "pm_opens_with_top_level_control_state_reuse": _ready_base(
            old_control_state_reused_as_current=True,
            pm_start_gate_decision="open",
            work_beyond_startup_allowed=True,
        ),
        "continue_previous_work_without_import_packet": _ready_base(
            prior_work_mode="continue",
            prior_work_import_packet_written=False,
            pm_start_gate_decision="open",
            work_beyond_startup_allowed=True,
        ),
        "reviewer_clean_accepts_underfilled_live_subagents": _ready_base(live_agents_active=3),
        "reviewer_clean_accepts_reused_historical_agent_ids": _ready_base(
            live_subagents_current_task_fresh=False,
            reused_historical_agent_ids=True,
        ),
        "reviewer_clean_without_agent_freshness_check": _ready_base(
            reviewer_checked_live_agent_freshness=False,
            reviewer_checked_no_historical_agent_reuse=False,
        ),
        "reviewer_clean_accepts_30_min_route_heartbeat": _ready_base(
            route_heartbeat_interval_minutes=30,
            actual_heartbeat_interval_minutes=30,
        ),
        "reviewer_clean_accepts_same_name_heartbeat_not_current_run": _ready_base(
            heartbeat_bound_to_current_run=False,
            heartbeat_current_run_binding_checked=False,
            heartbeat_same_name_only_checked=True,
        ),
        "pm_single_agent_fallback_without_reviewer_probe": _ready_base(
            background_agents_capability_status="unavailable",
            live_subagents_started=False,
            live_agents_active=0,
            live_subagents_current_task_fresh=False,
            fresh_agents_spawned_after_startup_answers=False,
            fresh_agents_spawned_after_route_allocation=False,
            historical_agent_ids_compared=False,
            reviewer_probed_background_agent_capability=False,
            reviewer_verified_background_agent_fallback_needed=False,
            reviewer_checked_live_agent_freshness=False,
            reviewer_checked_no_historical_agent_reuse=False,
            pm_recorded_background_agent_fallback=True,
            single_agent_role_continuity_authorized=True,
            pm_start_gate_decision="open",
            work_beyond_startup_allowed=True,
        ),
        "pm_manual_resume_fallback_without_reviewer_probe": _ready_base(
            scheduled_continuation_capability_status="unavailable",
            automated_continuation_ready=False,
            route_heartbeat_interval_minutes=0,
            actual_heartbeat_automation_checked=False,
            actual_heartbeat_interval_minutes=0,
            heartbeat_bound_to_current_run=False,
            heartbeat_current_run_binding_checked=False,
            reviewer_probed_scheduled_continuation_capability=False,
            reviewer_verified_scheduled_continuation_fallback_needed=False,
            reviewer_checked_current_heartbeat_binding=False,
            pm_recorded_scheduled_continuation_fallback=True,
            manual_resume_ready=True,
            pm_start_gate_decision="open",
            work_beyond_startup_allowed=True,
        ),
        "pm_chat_fallback_without_reviewer_probe": _ready_base(
            cockpit_capability_status="unavailable",
            cockpit_ui_opened=False,
            cockpit_open_failed=True,
            chat_route_sign_displayed=True,
            reviewer_probed_cockpit_capability=False,
            reviewer_verified_cockpit_fallback_needed=False,
            pm_recorded_cockpit_fallback=True,
            pm_start_gate_decision="open",
            work_beyond_startup_allowed=True,
        ),
        "pm_opens_ambiguous_capability_status": _ready_base(
            background_agents_capability_status="unknown",
            pm_start_gate_decision="open",
            work_beyond_startup_allowed=True,
        ),
        "worker_claimed_no_capability_pm_fallback": _ready_base(
            background_agents_capability_status="unavailable",
            worker_claimed_capability_unavailable=True,
            live_subagents_started=False,
            live_agents_active=0,
            live_subagents_current_task_fresh=False,
            fresh_agents_spawned_after_startup_answers=False,
            fresh_agents_spawned_after_route_allocation=False,
            historical_agent_ids_compared=False,
            reviewer_probed_background_agent_capability=False,
            reviewer_verified_background_agent_fallback_needed=False,
            pm_recorded_background_agent_fallback=True,
            single_agent_role_continuity_authorized=True,
            pm_start_gate_decision="open",
            work_beyond_startup_allowed=True,
        ),
        "reviewer_directly_opens_start_gate": _ready_base(reviewer_opened_start_gate=True, work_beyond_startup_allowed=True),
        "pm_opens_without_independent_gate_audit": _ready_base(pm_independent_gate_audit_done=False, pm_start_gate_decision="open", work_beyond_startup_allowed=True),
        "pm_opens_without_reviewer_report": _ready_base(startup_review_status="pending", pm_start_gate_decision="open", work_beyond_startup_allowed=True),
        "pm_opens_blocked_report": _ready_base(startup_review_status="blocked", pm_start_gate_decision="open", work_beyond_startup_allowed=True),
        "clean_start_without_cleanup": _ready_base(clean_start_requirement="required", old_route_cleanup_done=False, pm_start_gate_decision="open", work_beyond_startup_allowed=True),
        "worker_fix_without_reviewer_recheck": _ready_base(
            startup_review_status="pending",
            worker_remediation_done=True,
            pm_start_gate_decision="open",
            work_beyond_startup_allowed=True,
        ),
        "imagegen_before_pm_open": _ready_base(startup_review_status="pending", imagegen_started=True),
        "route_execution_before_pm_open": _ready_base(startup_review_status="pending", route_execution_started=True),
    }
