"""FlowGuard model for the current FlowPilot startup Runtime/PM entry.

Current contract:
- FlowPilot must use background or parallel agents.
- The startup UI acknowledgement is the user authorization boundary.
- Missing authorization or host inability to open background collaboration is a
  startup blocker, not a single-agent/manual/heartbeat fallback.
- Runtime/Router performs mechanical startup entry, then PM decides the first material action before work beyond startup.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple


MIN_BACKGROUND_AGENT_COUNT = 1


@dataclass(frozen=True)
class State:
    startup_intake_ui_completed: bool = False
    background_collaboration_authorized: bool | None = None
    explicit_user_answer_recorded: bool = False
    startup_answer_provenance: str = "none"  # none | explicit_user_reply | inferred | default | naked
    agent_self_recorded_authorization: bool = False
    startup_authorization_blocked: bool = False
    banner_emitted: bool = False
    chat_route_sign_displayed: bool = False
    run_directory_created: bool = False
    current_pointer_written: bool = False
    run_index_updated: bool = False
    prior_work_mode: str = "unknown"  # unknown | new | continue
    prior_work_import_packet_written: bool = False
    control_state_written_under_run_root: bool = False
    prior_control_state_quarantined: bool = False
    old_control_state_reused_as_current: bool = False
    route_file_written: bool = False
    canonical_state_written: bool = False
    execution_frontier_written: bool = False
    background_agent_ledger_current: bool = False
    background_collaboration_requested: bool = False
    background_agent_capability_status: str = "unknown"  # unknown | available | unavailable | damaged
    live_background_agents_active: int = 0
    background_agents_current_task_ready: bool = False
    background_agents_opened_after_startup_authorization: bool = False
    background_agents_opened_after_route_allocation: bool = False
    historical_agent_ids_compared: bool = False
    reused_historical_agent_ids: bool = False
    clean_start_requirement: str = "unknown"  # unknown | required | not_required
    old_route_cleanup_done: bool = False
    runtime_checked_user_authorization: bool = False
    runtime_checked_route_state_frontier: bool = False
    runtime_checked_run_isolation: bool = False
    runtime_checked_prior_work_boundary: bool = False
    runtime_checked_old_route_assets: bool = False
    runtime_checked_background_collaboration: bool = False
    runtime_checked_live_agent_freshness: bool = False
    runtime_checked_no_historical_agent_reuse: bool = False
    runtime_checked_shadow_route: bool = False
    runtime_checked_display_surface_evidence: bool = False
    runtime_checked_background_agent_capability: bool = False
    runtime_verified_background_agent_block_required: bool = False
    startup_mechanical_audit_file_backed: bool = False
    startup_mechanical_audit_proof_file_backed: bool = False
    startup_mechanical_audit_delivered_to_pm: bool = False
    pm_entry_references_current_mechanical_audit: bool = False
    pm_startup_entry_record_file_backed: bool = False
    pm_startup_repair_decision_file_backed: bool = False
    pm_startup_repair_targeted: bool = False
    pm_first_round_decision_file_backed: bool = False
    pm_protocol_dead_end_decision_file_backed: bool = False
    pm_dead_end_has_no_legal_repair_path: bool = False
    pending_mail_suspended_after_dead_end: bool = False
    future_actions_prevented_after_dead_end: bool = False
    controller_direct_runtime_recheck_requested: bool = False
    controller_inspected_router_hard_checks: bool = False
    controller_free_text_authority_used: bool = False
    worker_claimed_capability_unavailable: bool = False
    startup_runtime_entry_status: str = "pending"  # pending | blocked | clean
    worker_remediation_done: bool = False
    pm_independent_gate_audit_done: bool = False
    pm_start_gate_decision: str = "pending"  # pending | return_to_worker | protocol_dead_end | open
    non_pm_opened_start_gate: bool = False
    work_beyond_startup_allowed: bool = False
    child_skill_started: bool = False
    imagegen_started: bool = False
    implementation_started: bool = False
    route_execution_started: bool = False
    shadow_route_detected: bool = False

    legacy_single_agent_continuity_authorized: bool = False
    legacy_manual_resume_downgrade_authorized: bool = False
    legacy_heartbeat_created: bool = False
    legacy_runtime_role_assistance_key_accepted: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def startup_authorization_complete(state: State) -> bool:
    return (
        state.startup_intake_ui_completed
        and state.background_collaboration_authorized is True
        and state.explicit_user_answer_recorded
        and state.startup_answer_provenance == "explicit_user_reply"
        and not state.agent_self_recorded_authorization
        and not state.startup_authorization_blocked
    )


def background_collaboration_ready(state: State) -> bool:
    return (
        state.background_collaboration_requested
        and state.background_agent_capability_status == "available"
        and state.live_background_agents_active >= MIN_BACKGROUND_AGENT_COUNT
        and state.background_agents_current_task_ready
        and state.background_agents_opened_after_startup_authorization
        and state.background_agents_opened_after_route_allocation
        and state.historical_agent_ids_compared
        and not state.reused_historical_agent_ids
        and not state.legacy_single_agent_continuity_authorized
    )


def cleanup_matches_request(state: State) -> bool:
    if state.clean_start_requirement == "required":
        return state.old_route_cleanup_done
    return state.clean_start_requirement == "not_required"


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
        and state.prior_control_state_quarantined
        and not state.old_control_state_reused_as_current
    )


def runtime_mechanical_scope_complete(state: State) -> bool:
    background_available_scope = (
        state.background_agent_capability_status == "available"
        and state.runtime_checked_live_agent_freshness
        and state.runtime_checked_no_historical_agent_reuse
    )
    background_block_scope = (
        state.background_agent_capability_status in {"unavailable", "damaged"}
        and state.runtime_verified_background_agent_block_required
    )
    return (
        state.runtime_checked_user_authorization
        and state.runtime_checked_route_state_frontier
        and state.runtime_checked_run_isolation
        and state.runtime_checked_prior_work_boundary
        and state.runtime_checked_old_route_assets
        and state.runtime_checked_background_collaboration
        and state.runtime_checked_shadow_route
        and state.runtime_checked_display_surface_evidence
        and state.runtime_checked_background_agent_capability
        and (background_available_scope or background_block_scope)
    )


def startup_ready_for_pm_open(state: State) -> bool:
    return (
        startup_authorization_complete(state)
        and state.banner_emitted
        and state.chat_route_sign_displayed
        and run_isolation_ready(state)
        and state.route_file_written
        and state.canonical_state_written
        and state.execution_frontier_written
        and state.background_agent_ledger_current
        and background_collaboration_ready(state)
        and cleanup_matches_request(state)
        and runtime_mechanical_scope_complete(state)
        and state.startup_mechanical_audit_file_backed
        and state.startup_mechanical_audit_proof_file_backed
        and state.startup_mechanical_audit_delivered_to_pm
        and state.pm_entry_references_current_mechanical_audit
        and state.startup_runtime_entry_status == "clean"
        and state.pm_startup_entry_record_file_backed
        and state.pm_independent_gate_audit_done
        and state.pm_first_round_decision_file_backed
        and not state.non_pm_opened_start_gate
        and not state.shadow_route_detected
    )


def startup_clean_report_allowed(state: State) -> bool:
    return background_collaboration_ready(state) and cleanup_matches_request(state)


def work_started(state: State) -> bool:
    return (
        state.child_skill_started
        or state.imagegen_started
        or state.implementation_started
        or state.route_execution_started
    )


def next_safe_states(state: State) -> Iterable[Transition]:
    if not state.startup_intake_ui_completed:
        yield Transition("startup_intake_ui_completed", replace(state, startup_intake_ui_completed=True))
        return
    if state.background_collaboration_authorized is None:
        yield Transition(
            "background_collaboration_authorized_by_startup_ui",
            replace(state, background_collaboration_authorized=True),
        )
        yield Transition(
            "startup_blocked_without_background_authorization",
            replace(
                state,
                background_collaboration_authorized=False,
                startup_authorization_blocked=True,
                pm_start_gate_decision="protocol_dead_end",
                pm_protocol_dead_end_decision_file_backed=True,
                pm_dead_end_has_no_legal_repair_path=True,
                pending_mail_suspended_after_dead_end=True,
                future_actions_prevented_after_dead_end=True,
            ),
        )
        return
    if state.startup_authorization_blocked:
        return
    if not state.explicit_user_answer_recorded:
        yield Transition(
            "explicit_background_authorization_recorded",
            replace(
                state,
                explicit_user_answer_recorded=True,
                startup_answer_provenance="explicit_user_reply",
            ),
        )
        return
    if not state.banner_emitted:
        yield Transition("startup_banner_emitted_after_background_authorization", replace(state, banner_emitted=True))
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
    if not state.prior_control_state_quarantined:
        yield Transition("prior_control_state_quarantined", replace(state, prior_control_state_quarantined=True))
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
    if not state.chat_route_sign_displayed:
        yield Transition("startup_route_sign_displayed_in_chat", replace(state, chat_route_sign_displayed=True))
        return
    if not state.background_agent_ledger_current:
        yield Transition("background_agent_ledger_current", replace(state, background_agent_ledger_current=True))
        return
    if not state.background_collaboration_requested:
        yield Transition("background_collaboration_requested", replace(state, background_collaboration_requested=True))
        return
    if state.background_agent_capability_status == "unknown":
        yield Transition(
            "current_background_agents_opened",
            replace(
                state,
                background_agent_capability_status="available",
                live_background_agents_active=MIN_BACKGROUND_AGENT_COUNT,
                background_agents_current_task_ready=True,
                background_agents_opened_after_startup_authorization=True,
                background_agents_opened_after_route_allocation=True,
                historical_agent_ids_compared=True,
                reused_historical_agent_ids=False,
            ),
        )
        yield Transition(
            "background_agent_capability_unavailable_detected",
            replace(
                state,
                background_agent_capability_status="unavailable",
                worker_claimed_capability_unavailable=True,
            ),
        )
        return
    if state.clean_start_requirement == "unknown":
        yield Transition("clean_start_required_by_user", replace(state, clean_start_requirement="required"))
        yield Transition("clean_start_not_required", replace(state, clean_start_requirement="not_required"))
        return
    if state.clean_start_requirement == "required" and not state.old_route_cleanup_done:
        yield Transition("old_route_cleanup_verified", replace(state, old_route_cleanup_done=True))
        return
    if not (
        state.startup_mechanical_audit_file_backed
        and state.startup_mechanical_audit_proof_file_backed
    ):
        yield Transition(
            "startup_mechanical_audit_written_before_pm_first_round",
            replace(
                state,
                startup_mechanical_audit_file_backed=True,
                startup_mechanical_audit_proof_file_backed=True,
            ),
        )
        return
    if not state.startup_mechanical_audit_delivered_to_pm:
        yield Transition(
            "startup_mechanical_audit_delivered_to_pm",
            replace(state, startup_mechanical_audit_delivered_to_pm=True),
        )
        return
    if not runtime_mechanical_scope_complete(state):
        runtime_changes = {
            "runtime_checked_user_authorization": True,
            "runtime_checked_route_state_frontier": True,
            "runtime_checked_run_isolation": True,
            "runtime_checked_prior_work_boundary": True,
            "runtime_checked_old_route_assets": True,
            "runtime_checked_background_collaboration": True,
            "runtime_checked_live_agent_freshness": True,
            "runtime_checked_no_historical_agent_reuse": True,
            "runtime_checked_shadow_route": True,
            "runtime_checked_display_surface_evidence": True,
            "runtime_checked_background_agent_capability": True,
        }
        if state.background_agent_capability_status in {"unavailable", "damaged"}:
            runtime_changes["runtime_verified_background_agent_block_required"] = True
            runtime_changes["runtime_checked_live_agent_freshness"] = False
            runtime_changes["runtime_checked_no_historical_agent_reuse"] = False
        yield Transition(
            "runtime_completed_startup_mechanical_scope",
            replace(state, **runtime_changes),
        )
        return
    if state.startup_runtime_entry_status == "pending":
        if not state.worker_remediation_done:
            yield Transition(
                "runtime_startup_entry_blocked",
                replace(
                    state,
                    startup_runtime_entry_status="blocked",
                    pm_startup_entry_record_file_backed=True,
                    pm_entry_references_current_mechanical_audit=True,
                ),
            )
        if startup_clean_report_allowed(state):
            yield Transition(
                "runtime_startup_entry_clean",
                replace(
                    state,
                    startup_runtime_entry_status="clean",
                    pm_startup_entry_record_file_backed=True,
                    pm_entry_references_current_mechanical_audit=True,
                ),
            )
        return
    if state.startup_runtime_entry_status == "blocked" and state.pm_start_gate_decision == "pending":
        yield Transition(
            "pm_returns_startup_blockers_to_worker",
            replace(
                state,
                pm_start_gate_decision="return_to_worker",
                pm_startup_repair_decision_file_backed=True,
                pm_startup_repair_targeted=True,
            ),
        )
        yield Transition(
            "pm_declares_protocol_dead_end_for_unroutable_startup_block",
            replace(
                state,
                pm_start_gate_decision="protocol_dead_end",
                pm_protocol_dead_end_decision_file_backed=True,
                pm_dead_end_has_no_legal_repair_path=True,
                pending_mail_suspended_after_dead_end=True,
                future_actions_prevented_after_dead_end=True,
            ),
        )
        return
    if state.pm_start_gate_decision == "return_to_worker" and not state.worker_remediation_done:
        yield Transition(
            "startup_worker_remediation_completed",
            replace(
                state,
                worker_remediation_done=True,
                startup_runtime_entry_status="pending",
                pm_start_gate_decision="pending",
                pm_startup_repair_decision_file_backed=False,
                pm_startup_repair_targeted=False,
                background_agent_capability_status="unknown",
                worker_claimed_capability_unavailable=False,
                runtime_checked_user_authorization=False,
                runtime_checked_route_state_frontier=False,
                runtime_checked_run_isolation=False,
                runtime_checked_prior_work_boundary=False,
                runtime_checked_old_route_assets=False,
                runtime_checked_background_collaboration=False,
                runtime_checked_live_agent_freshness=False,
                runtime_checked_no_historical_agent_reuse=False,
                runtime_checked_shadow_route=False,
                runtime_checked_display_surface_evidence=False,
                runtime_checked_background_agent_capability=False,
                runtime_verified_background_agent_block_required=False,
                pm_startup_entry_record_file_backed=False,
            ),
        )
        return
    if state.pm_start_gate_decision == "protocol_dead_end":
        return
    if state.startup_runtime_entry_status == "clean" and not state.pm_independent_gate_audit_done:
        yield Transition("pm_independently_audited_startup_gate", replace(state, pm_independent_gate_audit_done=True))
        return
    if (
        state.startup_runtime_entry_status == "clean"
        and state.pm_independent_gate_audit_done
        and state.pm_start_gate_decision == "pending"
    ):
        yield Transition(
            "pm_first_round_started_after_runtime_entry",
            replace(
                state,
                pm_start_gate_decision="open",
                pm_first_round_decision_file_backed=True,
                work_beyond_startup_allowed=True,
            ),
        )
        return
    if state.pm_start_gate_decision != "open":
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
    if state.banner_emitted and not startup_authorization_complete(state):
        failures.append("startup banner emitted before explicit background collaboration authorization")
    if state.explicit_user_answer_recorded and state.startup_answer_provenance != "explicit_user_reply":
        failures.append("startup authorization was recorded without explicit_user_reply provenance")
    if state.explicit_user_answer_recorded and state.background_collaboration_authorized is not True:
        failures.append("startup authorization was recorded without background_collaboration_authorized=true")
    if state.agent_self_recorded_authorization and state.explicit_user_answer_recorded:
        failures.append("agent self-recorded startup authorization without explicit user answer")
    if state.startup_authorization_blocked and (state.work_beyond_startup_allowed or work_started(state)):
        failures.append("work continued after startup blocked for missing background collaboration authorization")
    if state.non_pm_opened_start_gate:
        failures.append("non-PM role attempted to open the PM-owned startup gate")
    if state.old_control_state_reused_as_current:
        failures.append("old control state was reused as current run state")
    if state.startup_runtime_entry_status == "clean" and not runtime_mechanical_scope_complete(state):
        failures.append("Runtime marked startup entry clean without completing required mechanical checks")
    if state.startup_runtime_entry_status in {"blocked", "clean"} and not state.pm_startup_entry_record_file_backed:
        failures.append("Runtime startup entry record was accepted without a file-backed PM-visible record")
    if state.startup_runtime_entry_status in {"blocked", "clean"} and not (
        state.startup_mechanical_audit_file_backed
        and state.startup_mechanical_audit_proof_file_backed
        and state.startup_mechanical_audit_delivered_to_pm
        and state.pm_entry_references_current_mechanical_audit
    ):
        failures.append("Runtime startup entry record was accepted without the current prewritten router mechanical audit")
    if state.pm_start_gate_decision == "return_to_worker" and not (
        state.pm_startup_repair_decision_file_backed
        and state.pm_startup_repair_targeted
    ):
        failures.append("PM returned startup blockers without a file-backed repair decision targeted to a responsible actor")
    if state.pm_start_gate_decision == "protocol_dead_end" and not (
        state.pm_protocol_dead_end_decision_file_backed
        and state.pm_dead_end_has_no_legal_repair_path
        and state.pending_mail_suspended_after_dead_end
        and state.future_actions_prevented_after_dead_end
    ):
        failures.append("PM declared a startup protocol dead-end without a complete file-backed emergency stop record")
    if state.pm_start_gate_decision == "protocol_dead_end" and (state.work_beyond_startup_allowed or work_started(state)):
        failures.append("work continued after PM declared a startup protocol dead-end")
    if state.pm_start_gate_decision == "open" and not startup_ready_for_pm_open(state):
        failures.append("PM started first-round work without current authorization, background collaboration, clean Runtime entry, and independent PM audit")
    if state.pm_start_gate_decision == "open" and state.startup_runtime_entry_status != "clean":
        failures.append("PM started first-round work without a clean Runtime entry")
    if state.pm_start_gate_decision == "open" and not state.pm_first_round_decision_file_backed:
        failures.append("PM first-round startup decision was accepted without a file-backed decision envelope")
    if state.pm_start_gate_decision == "open" and not state.pm_independent_gate_audit_done:
        failures.append("PM opened startup without independently auditing startup gate evidence")
    if state.controller_direct_runtime_recheck_requested:
        failures.append("Controller directly requested Runtime recheck through free text instead of router-authorized current-runtime mail")
    if state.controller_inspected_router_hard_checks:
        failures.append("Controller inspected router hard-check internals instead of using black-box router actions")
    if state.controller_free_text_authority_used:
        failures.append("Controller free text was treated as role authority")
    if state.pm_start_gate_decision == "open" and not cleanup_matches_request(state):
        failures.append("PM opened startup before old-route cleanup matched the user request")
    if state.pm_start_gate_decision == "open" and not run_isolation_ready(state):
        failures.append("PM opened startup before active run isolation was complete")
    if state.startup_runtime_entry_status == "blocked" and state.work_beyond_startup_allowed:
        failures.append("work beyond startup was allowed despite blocking Runtime startup entry")
    if state.worker_remediation_done and state.pm_start_gate_decision == "open" and state.startup_runtime_entry_status != "clean":
        failures.append("worker remediation was not rerun through Runtime entry before PM start")
    if state.background_collaboration_requested and state.background_collaboration_authorized is not True:
        failures.append("background collaboration was requested without explicit startup authorization")
    if state.live_background_agents_active and state.background_collaboration_authorized is not True:
        failures.append("active background agents exist without explicit startup authorization")
    if (
        state.startup_runtime_entry_status == "clean"
        and state.background_agent_capability_status == "available"
        and state.live_background_agents_active < MIN_BACKGROUND_AGENT_COUNT
    ):
        failures.append("Runtime accepted background collaboration without any current background agent")
    if (
        state.startup_runtime_entry_status == "clean"
        and state.background_agent_capability_status == "available"
        and not (
            state.background_agents_current_task_ready
            and state.background_agents_opened_after_startup_authorization
            and state.background_agents_opened_after_route_allocation
            and state.historical_agent_ids_compared
            and not state.reused_historical_agent_ids
        )
    ):
        failures.append("Runtime accepted background collaboration without current-task current agent ids")
    if (
        state.startup_runtime_entry_status == "clean"
        and state.background_agent_capability_status == "available"
        and not (
            state.runtime_checked_live_agent_freshness
            and state.runtime_checked_no_historical_agent_reuse
        )
    ):
        failures.append("Runtime marked startup entry clean without checking background agent freshness and historical id reuse")
    if state.pm_start_gate_decision == "open" and state.reused_historical_agent_ids:
        failures.append("PM opened startup while current background-agent evidence reused historical agent ids")
    if (
        state.background_agent_capability_status in {"unavailable", "damaged"}
        and state.pm_start_gate_decision == "open"
    ):
        failures.append("PM opened startup after background collaboration was unavailable instead of blocking or repairing")
    if state.pm_start_gate_decision == "open" and state.background_agent_capability_status == "unknown":
        failures.append("PM opened startup while requested background capability status was still ambiguous")
    if state.legacy_single_agent_continuity_authorized:
        failures.append("legacy single-agent continuity was authorized instead of mandatory background collaboration")
    if state.legacy_manual_resume_downgrade_authorized:
        failures.append("legacy manual-resume downgrade was authorized instead of blocking or repairing startup")
    if state.legacy_heartbeat_created:
        failures.append("legacy heartbeat continuation was created in current startup flow")
    if state.legacy_runtime_role_assistance_key_accepted:
        failures.append("legacy runtime_role_assistances startup key was accepted")
    if work_started(state) and not state.work_beyond_startup_allowed:
        failures.append("work beyond startup started before PM allowed work from the Runtime startup entry record")
    if state.shadow_route_detected and state.work_beyond_startup_allowed:
        failures.append("shadow route was allowed through PM startup opening")
    return failures


def _ready_base(**changes: object) -> State:
    base = State(
        startup_intake_ui_completed=True,
        background_collaboration_authorized=True,
        explicit_user_answer_recorded=True,
        startup_answer_provenance="explicit_user_reply",
        banner_emitted=True,
        chat_route_sign_displayed=True,
        run_directory_created=True,
        current_pointer_written=True,
        run_index_updated=True,
        prior_work_mode="new",
        control_state_written_under_run_root=True,
        prior_control_state_quarantined=True,
        route_file_written=True,
        canonical_state_written=True,
        execution_frontier_written=True,
        background_agent_ledger_current=True,
        background_collaboration_requested=True,
        background_agent_capability_status="available",
        live_background_agents_active=MIN_BACKGROUND_AGENT_COUNT,
        background_agents_current_task_ready=True,
        background_agents_opened_after_startup_authorization=True,
        background_agents_opened_after_route_allocation=True,
        historical_agent_ids_compared=True,
        reused_historical_agent_ids=False,
        clean_start_requirement="not_required",
        runtime_checked_user_authorization=True,
        runtime_checked_route_state_frontier=True,
        runtime_checked_run_isolation=True,
        runtime_checked_prior_work_boundary=True,
        runtime_checked_old_route_assets=True,
        runtime_checked_background_collaboration=True,
        runtime_checked_live_agent_freshness=True,
        runtime_checked_no_historical_agent_reuse=True,
        runtime_checked_shadow_route=True,
        runtime_checked_display_surface_evidence=True,
        runtime_checked_background_agent_capability=True,
        startup_mechanical_audit_file_backed=True,
        startup_mechanical_audit_proof_file_backed=True,
        startup_mechanical_audit_delivered_to_pm=True,
        pm_entry_references_current_mechanical_audit=True,
        startup_runtime_entry_status="clean",
        pm_startup_entry_record_file_backed=True,
        pm_independent_gate_audit_done=True,
        pm_first_round_decision_file_backed=True,
    )
    return replace(base, **changes)


def hazard_states() -> dict[str, State]:
    return {
        "banner_before_background_authorization": State(startup_intake_ui_completed=True, banner_emitted=True),
        "authorization_recorded_with_inferred_provenance": State(
            startup_intake_ui_completed=True,
            background_collaboration_authorized=True,
            explicit_user_answer_recorded=True,
            startup_answer_provenance="inferred",
        ),
        "authorization_recorded_without_background_ack": State(
            startup_intake_ui_completed=True,
            background_collaboration_authorized=False,
            explicit_user_answer_recorded=True,
            startup_answer_provenance="explicit_user_reply",
        ),
        "startup_blocked_but_work_continues": State(
            startup_intake_ui_completed=True,
            background_collaboration_authorized=False,
            startup_authorization_blocked=True,
            work_beyond_startup_allowed=True,
        ),
        "runtime_entry_clean_without_mechanical_checks": _ready_base(
            runtime_checked_background_collaboration=False,
        ),
        "runtime_entry_clean_record_not_file_backed": _ready_base(
            pm_startup_entry_record_file_backed=False,
        ),
        "runtime_entry_clean_without_startup_mechanical_audit": _ready_base(
            startup_mechanical_audit_file_backed=False,
            startup_mechanical_audit_proof_file_backed=False,
            startup_mechanical_audit_delivered_to_pm=False,
            pm_entry_references_current_mechanical_audit=False,
        ),
        "pm_block_without_repair_target_or_dead_end": _ready_base(
            startup_runtime_entry_status="blocked",
            pm_independent_gate_audit_done=False,
            pm_first_round_decision_file_backed=False,
            pm_start_gate_decision="return_to_worker",
            pm_startup_repair_decision_file_backed=False,
            pm_startup_repair_targeted=False,
        ),
        "pm_dead_end_without_emergency_record": _ready_base(
            startup_runtime_entry_status="blocked",
            pm_independent_gate_audit_done=False,
            pm_first_round_decision_file_backed=False,
            pm_start_gate_decision="protocol_dead_end",
            pm_protocol_dead_end_decision_file_backed=False,
            pm_dead_end_has_no_legal_repair_path=False,
            pending_mail_suspended_after_dead_end=False,
            future_actions_prevented_after_dead_end=False,
        ),
        "pm_opens_from_inline_first_round_decision": _ready_base(
            pm_first_round_decision_file_backed=False,
            pm_start_gate_decision="open",
            work_beyond_startup_allowed=True,
        ),
        "controller_directs_runtime_recheck": _ready_base(
            controller_direct_runtime_recheck_requested=True,
        ),
        "controller_reads_router_hard_checks": _ready_base(
            controller_inspected_router_hard_checks=True,
        ),
        "controller_free_text_has_role_authority": _ready_base(
            controller_free_text_authority_used=True,
        ),
        "runtime_entry_clean_without_run_isolation_check": _ready_base(
            runtime_checked_run_isolation=False,
            runtime_checked_prior_work_boundary=False,
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
        "runtime_entry_clean_accepts_no_background_agent": _ready_base(live_background_agents_active=0),
        "runtime_entry_clean_accepts_reused_historical_agent_ids": _ready_base(
            background_agents_current_task_ready=False,
            reused_historical_agent_ids=True,
        ),
        "runtime_entry_clean_without_agent_freshness_check": _ready_base(
            runtime_checked_live_agent_freshness=False,
            runtime_checked_no_historical_agent_reuse=False,
        ),
        "pm_single_agent_continuity_fallback": _ready_base(
            legacy_single_agent_continuity_authorized=True,
            pm_start_gate_decision="open",
            work_beyond_startup_allowed=True,
        ),
        "pm_manual_resume_downgrade_fallback": _ready_base(
            legacy_manual_resume_downgrade_authorized=True,
            pm_start_gate_decision="open",
            work_beyond_startup_allowed=True,
        ),
        "pm_heartbeat_fallback": _ready_base(
            legacy_heartbeat_created=True,
            pm_start_gate_decision="open",
            work_beyond_startup_allowed=True,
        ),
        "legacy_runtime_role_assistance_key_accepted": _ready_base(
            legacy_runtime_role_assistance_key_accepted=True,
        ),
        "pm_opens_ambiguous_background_capability_status": _ready_base(
            background_agent_capability_status="unknown",
            pm_start_gate_decision="open",
            work_beyond_startup_allowed=True,
        ),
        "worker_claimed_no_capability_pm_downgrade": _ready_base(
            background_agent_capability_status="unavailable",
            worker_claimed_capability_unavailable=True,
            live_background_agents_active=0,
            background_agents_current_task_ready=False,
            background_agents_opened_after_startup_authorization=False,
            background_agents_opened_after_route_allocation=False,
            historical_agent_ids_compared=False,
            runtime_checked_background_agent_capability=False,
            runtime_verified_background_agent_block_required=False,
            pm_start_gate_decision="open",
            work_beyond_startup_allowed=True,
        ),
        "non_pm_role_directly_opens_start_gate": _ready_base(non_pm_opened_start_gate=True, work_beyond_startup_allowed=True),
        "pm_opens_without_independent_gate_audit": _ready_base(pm_independent_gate_audit_done=False, pm_start_gate_decision="open", work_beyond_startup_allowed=True),
        "pm_opens_without_runtime_entry": _ready_base(startup_runtime_entry_status="pending", pm_start_gate_decision="open", work_beyond_startup_allowed=True),
        "pm_opens_blocked_report": _ready_base(startup_runtime_entry_status="blocked", pm_start_gate_decision="open", work_beyond_startup_allowed=True),
        "clean_start_without_cleanup": _ready_base(clean_start_requirement="required", old_route_cleanup_done=False, pm_start_gate_decision="open", work_beyond_startup_allowed=True),
        "worker_fix_without_runtime_recheck": _ready_base(
            startup_runtime_entry_status="pending",
            worker_remediation_done=True,
            pm_start_gate_decision="open",
            work_beyond_startup_allowed=True,
        ),
        "imagegen_before_pm_open": _ready_base(startup_runtime_entry_status="pending", imagegen_started=True),
        "route_execution_before_pm_open": _ready_base(startup_runtime_entry_status="pending", route_execution_started=True),
    }



