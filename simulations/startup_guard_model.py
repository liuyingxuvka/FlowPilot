"""Small FlowPilot startup hard-gate model.

This model isolates the simplified startup contract: FlowPilot invocation first
asks three questions, stops the assistant response to wait for the user, then
records explicit answers, emits the banner, and may assemble the route, crew,
continuation evidence, and startup guard. The safe path requires the stop-and-
wait state plus explicit answers before the banner and before any child-skill,
imagegen, implementation, or route-execution work can start.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple


REQUIRED_ROLE_MEMORY_PACKETS = 6


@dataclass(frozen=True)
class State:
    startup_questions_asked: bool = False
    dialog_stopped_for_user_answers: bool = False
    run_mode_answered: bool = False
    background_agents_answer: str = "unknown"  # unknown | allow | single-agent | pause
    scheduled_continuation_answer: str = "unknown"  # unknown | allow | manual | pause
    explicit_user_answer_recorded: bool = False
    agent_self_recorded_authorization: bool = False
    banner_emitted: bool = False
    route_file_written: bool = False
    canonical_state_written: bool = False
    execution_frontier_written: bool = False
    crew_ledger_current: bool = False
    role_memory_packets_current: int = 0
    live_subagents_started: bool = False
    single_agent_role_continuity_authorized: bool = False
    automated_continuation_ready: bool = False
    manual_resume_ready: bool = False
    startup_guard_passed: bool = False
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
        and state.run_mode_answered
        and state.background_agents_answer in {"allow", "single-agent"}
        and state.scheduled_continuation_answer in {"allow", "manual"}
        and state.explicit_user_answer_recorded
        and not state.agent_self_recorded_authorization
    )


def subagent_decision_matches_answer(state: State) -> bool:
    if state.background_agents_answer == "allow":
        return state.live_subagents_started and not state.single_agent_role_continuity_authorized
    if state.background_agents_answer == "single-agent":
        return state.single_agent_role_continuity_authorized and not state.live_subagents_started
    return False


def continuation_matches_answer(state: State) -> bool:
    if state.scheduled_continuation_answer == "allow":
        return state.automated_continuation_ready and not state.manual_resume_ready
    if state.scheduled_continuation_answer == "manual":
        return state.manual_resume_ready and not state.automated_continuation_ready
    return False


def startup_ready_for_guard(state: State) -> bool:
    return (
        startup_answers_complete(state)
        and state.banner_emitted
        and state.route_file_written
        and state.canonical_state_written
        and state.execution_frontier_written
        and state.crew_ledger_current
        and state.role_memory_packets_current == REQUIRED_ROLE_MEMORY_PACKETS
        and subagent_decision_matches_answer(state)
        and continuation_matches_answer(state)
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
        yield Transition(
            "startup_dialog_stopped_for_user_answers",
            replace(state, dialog_stopped_for_user_answers=True),
        )
        return
    if not state.run_mode_answered:
        yield Transition("run_mode_answer_recorded", replace(state, run_mode_answered=True))
        return
    if state.background_agents_answer == "unknown":
        yield Transition("background_agents_allowed", replace(state, background_agents_answer="allow"))
        yield Transition("background_agents_declined_single_agent", replace(state, background_agents_answer="single-agent"))
        return
    if state.scheduled_continuation_answer == "unknown":
        yield Transition("scheduled_continuation_allowed", replace(state, scheduled_continuation_answer="allow"))
        yield Transition("scheduled_continuation_declined_manual", replace(state, scheduled_continuation_answer="manual"))
        return
    if not state.explicit_user_answer_recorded:
        yield Transition("explicit_startup_answers_recorded", replace(state, explicit_user_answer_recorded=True))
        return
    if not state.banner_emitted:
        yield Transition("startup_banner_emitted_after_answers", replace(state, banner_emitted=True))
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
    if not state.crew_ledger_current:
        yield Transition("crew_ledger_current", replace(state, crew_ledger_current=True))
        return
    if state.role_memory_packets_current < REQUIRED_ROLE_MEMORY_PACKETS:
        yield Transition(
            "role_memory_packets_current",
            replace(state, role_memory_packets_current=REQUIRED_ROLE_MEMORY_PACKETS),
        )
        return
    if state.background_agents_answer == "allow" and not state.live_subagents_started:
        yield Transition("live_subagents_started", replace(state, live_subagents_started=True))
        return
    if state.background_agents_answer == "single-agent" and not state.single_agent_role_continuity_authorized:
        yield Transition(
            "single_agent_role_continuity_authorized",
            replace(state, single_agent_role_continuity_authorized=True),
        )
        return
    if state.scheduled_continuation_answer == "allow" and not state.automated_continuation_ready:
        yield Transition("automated_continuation_ready", replace(state, automated_continuation_ready=True))
        return
    if state.scheduled_continuation_answer == "manual" and not state.manual_resume_ready:
        yield Transition("manual_resume_ready", replace(state, manual_resume_ready=True))
        return
    if not state.startup_guard_passed:
        yield Transition("startup_activation_guard_passed", replace(state, startup_guard_passed=True))
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
    if (
        not state.dialog_stopped_for_user_answers
        and (
            state.run_mode_answered
            or state.background_agents_answer != "unknown"
            or state.scheduled_continuation_answer != "unknown"
            or state.explicit_user_answer_recorded
            or state.banner_emitted
            or state.route_file_written
            or state.live_subagents_started
            or state.single_agent_role_continuity_authorized
            or state.automated_continuation_ready
            or state.manual_resume_ready
            or state.startup_guard_passed
            or work_started(state)
        )
    ):
        failures.append("startup proceeded after asking questions without stopping for the user's reply")
    if state.startup_guard_passed and not startup_ready_for_guard(state):
        failures.append("startup guard passed before canonical startup activation was complete")
    if state.agent_self_recorded_authorization and (
        state.explicit_user_answer_recorded
        or state.single_agent_role_continuity_authorized
        or state.manual_resume_ready
    ):
        failures.append("agent self-recorded startup authorization without explicit user answer")
    if state.single_agent_role_continuity_authorized and state.background_agents_answer != "single-agent":
        failures.append("single-agent role continuity was authorized without the user's single-agent answer")
    if state.live_subagents_started and state.background_agents_answer != "allow":
        failures.append("live subagents were started without the user's live-agent answer")
    if state.manual_resume_ready and state.scheduled_continuation_answer != "manual":
        failures.append("manual resume was recorded without the user's manual-resume answer")
    if state.automated_continuation_ready and state.scheduled_continuation_answer != "allow":
        failures.append("automated continuation was recorded without the user's scheduled-continuation answer")
    if work_started(state) and not state.startup_guard_passed:
        failures.append("work beyond startup started before the startup guard passed")
    if state.shadow_route_detected and state.startup_guard_passed:
        failures.append("shadow route was allowed through the startup guard")
    return failures


def hazard_states() -> dict[str, State]:
    return {
        "banner_before_three_answers": State(
            startup_questions_asked=True,
            run_mode_answered=True,
            banner_emitted=True,
        ),
        "answers_recorded_without_dialog_stop": State(
            startup_questions_asked=True,
            run_mode_answered=True,
            background_agents_answer="allow",
            scheduled_continuation_answer="allow",
            explicit_user_answer_recorded=True,
        ),
        "guard_before_questions": State(
            route_file_written=True,
            canonical_state_written=True,
            execution_frontier_written=True,
            crew_ledger_current=True,
            role_memory_packets_current=REQUIRED_ROLE_MEMORY_PACKETS,
            startup_guard_passed=True,
        ),
        "agent_self_records_single_agent": State(
            startup_questions_asked=True,
            dialog_stopped_for_user_answers=True,
            run_mode_answered=True,
            background_agents_answer="unknown",
            scheduled_continuation_answer="manual",
            explicit_user_answer_recorded=True,
            agent_self_recorded_authorization=True,
            single_agent_role_continuity_authorized=True,
        ),
        "manual_resume_without_user_answer": State(
            startup_questions_asked=True,
            dialog_stopped_for_user_answers=True,
            run_mode_answered=True,
            background_agents_answer="single-agent",
            explicit_user_answer_recorded=True,
            manual_resume_ready=True,
        ),
        "shadow_route_child_skill": State(
            route_file_written=True,
            child_skill_started=True,
            shadow_route_detected=True,
        ),
        "imagegen_before_guard": State(
            startup_questions_asked=True,
            dialog_stopped_for_user_answers=True,
            run_mode_answered=True,
            background_agents_answer="allow",
            scheduled_continuation_answer="allow",
            explicit_user_answer_recorded=True,
            banner_emitted=True,
            route_file_written=True,
            canonical_state_written=True,
            imagegen_started=True,
        ),
        "single_agent_despite_live_agent_answer": State(
            startup_questions_asked=True,
            dialog_stopped_for_user_answers=True,
            run_mode_answered=True,
            background_agents_answer="allow",
            scheduled_continuation_answer="manual",
            explicit_user_answer_recorded=True,
            single_agent_role_continuity_authorized=True,
        ),
        "manual_resume_despite_heartbeat_answer": State(
            startup_questions_asked=True,
            dialog_stopped_for_user_answers=True,
            run_mode_answered=True,
            background_agents_answer="single-agent",
            scheduled_continuation_answer="allow",
            explicit_user_answer_recorded=True,
            manual_resume_ready=True,
        ),
        "route_execution_before_guard": State(
            startup_questions_asked=True,
            dialog_stopped_for_user_answers=True,
            run_mode_answered=True,
            background_agents_answer="allow",
            scheduled_continuation_answer="allow",
            explicit_user_answer_recorded=True,
            banner_emitted=True,
            route_file_written=True,
            canonical_state_written=True,
            execution_frontier_written=True,
            crew_ledger_current=True,
            role_memory_packets_current=REQUIRED_ROLE_MEMORY_PACKETS,
            live_subagents_started=True,
            automated_continuation_ready=True,
            route_execution_started=True,
        ),
    }
