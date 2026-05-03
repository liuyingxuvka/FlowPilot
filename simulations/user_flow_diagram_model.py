"""FlowGuard model for FlowPilot's realtime user route sign.

Risk intent: the user-facing Mermaid route sign must be a visible control
artifact, not a stale file. When Cockpit UI is not open, chat display is the
required surface for startup, major route-node entry, parent/module or leaf
route-node entry, PM current-node work brief, route mutations, review or
validation returns, completion review, and explicit user requests. A raw
FlowGuard state graph cannot satisfy this user-facing gate.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import InvariantResult


DISPLAY_TRIGGERS = {
    "startup",
    "major_node_entry",
    "parent_node_entry",
    "leaf_node_entry",
    "pm_work_brief",
    "key_node_change",
    "route_mutation",
    "review_failure",
    "validation_failure",
    "completion",
    "user_request",
}
RETURN_TRIGGERS = {"route_mutation", "review_failure", "validation_failure"}


@dataclass(frozen=True)
class State:
    route_frontier_loaded: bool = False
    current_node_resolved: bool = False
    display_trigger: str = "none"
    cockpit_open: bool = False
    chat_display_required: bool = False
    return_edge_required: bool = False
    simplified_mermaid_generated: bool = False
    english_flowpilot_labels: bool = False
    raw_flowguard_graph_used: bool = False
    active_node_highlighted: bool = False
    return_edge_present: bool = False
    display_packet_written: bool = False
    chat_mermaid_displayed: bool = False
    cockpit_route_sign_displayed: bool = False
    reviewer_checked_display: bool = False
    reviewer_checked_chat_surface: bool = False
    reviewer_checked_route_match: bool = False
    reviewer_passed: bool = False
    node_work_started: bool = False
    node_advanced: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def trigger_requires_chat(trigger: str, cockpit_open: bool) -> bool:
    return trigger in DISPLAY_TRIGGERS and not cockpit_open


def trigger_requires_return_edge(trigger: str) -> bool:
    return trigger in RETURN_TRIGGERS


def next_safe_states(state: State) -> Iterable[Transition]:
    if not state.route_frontier_loaded:
        yield Transition("route_frontier_loaded", replace(state, route_frontier_loaded=True))
        return
    if not state.current_node_resolved:
        yield Transition("current_node_resolved", replace(state, current_node_resolved=True))
        return
    if state.display_trigger == "none":
        for label, trigger, cockpit_open in (
            ("trigger_startup_chat_required", "startup", False),
            ("trigger_major_node_entry_chat_required", "major_node_entry", False),
            ("trigger_parent_node_entry_chat_required", "parent_node_entry", False),
            ("trigger_leaf_node_entry_chat_required", "leaf_node_entry", False),
            ("trigger_pm_work_brief_chat_required", "pm_work_brief", False),
            ("trigger_key_node_change_chat_required", "key_node_change", False),
            ("trigger_route_mutation_cockpit_open", "route_mutation", True),
            ("trigger_review_failure_chat_required", "review_failure", False),
            ("trigger_validation_failure_chat_required", "validation_failure", False),
            ("trigger_completion_chat_required", "completion", False),
            ("trigger_user_request_chat_required", "user_request", False),
        ):
            yield Transition(
                label,
                replace(
                    state,
                    display_trigger=trigger,
                    cockpit_open=cockpit_open,
                    chat_display_required=trigger_requires_chat(trigger, cockpit_open),
                    return_edge_required=trigger_requires_return_edge(trigger),
                ),
            )
        return
    if not state.simplified_mermaid_generated:
        yield Transition(
            "realtime_route_sign_generated",
            replace(
                state,
                simplified_mermaid_generated=True,
                english_flowpilot_labels=True,
                active_node_highlighted=True,
                display_packet_written=True,
            ),
        )
        return
    if state.return_edge_required and not state.return_edge_present:
        yield Transition("return_edge_added", replace(state, return_edge_present=True))
        return
    if state.chat_display_required and not state.chat_mermaid_displayed:
        yield Transition("chat_mermaid_displayed", replace(state, chat_mermaid_displayed=True))
        return
    if state.cockpit_open and not state.cockpit_route_sign_displayed:
        yield Transition(
            "cockpit_route_sign_displayed",
            replace(state, cockpit_route_sign_displayed=True),
        )
        return
    if not state.reviewer_checked_display:
        yield Transition(
            "reviewer_checked_chat_route_sign",
            replace(
                state,
                reviewer_checked_display=True,
                reviewer_checked_chat_surface=state.chat_display_required,
                reviewer_checked_route_match=True,
                reviewer_passed=True,
            ),
        )
        return
    if not state.node_work_started:
        yield Transition(
            "node_work_started_after_display_gate",
            replace(state, node_work_started=True),
        )
        return
    if not state.node_advanced:
        yield Transition(
            "node_advanced_after_reviewer_gate",
            replace(state, node_advanced=True),
        )


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.display_trigger in DISPLAY_TRIGGERS and state.raw_flowguard_graph_used:
        failures.append("raw FlowGuard Mermaid was used as the user-facing route sign")
    if (
        state.display_trigger in DISPLAY_TRIGGERS
        and not state.cockpit_open
        and not state.chat_display_required
        and (
            state.simplified_mermaid_generated
            or state.reviewer_passed
            or state.node_work_started
            or state.node_advanced
        )
    ):
        failures.append("closed-Cockpit display trigger did not require chat Mermaid")
    if state.chat_display_required and (
        state.reviewer_passed or state.node_work_started or state.node_advanced
    ):
        if not state.chat_mermaid_displayed:
            failures.append("Cockpit was closed but node progress happened before Mermaid was shown in chat")
        if not state.simplified_mermaid_generated or not state.english_flowpilot_labels:
            failures.append("chat display gate did not use the simplified English FlowPilot route sign")
    if state.return_edge_required and (
        state.chat_mermaid_displayed or state.cockpit_route_sign_displayed or state.reviewer_passed
    ):
        if not state.return_edge_present:
            failures.append("route mutation or failed review was displayed without a return/repair edge")
    if state.reviewer_passed:
        if not state.reviewer_checked_display:
            failures.append("reviewer passed the route sign without checking the visible display")
        if state.chat_display_required and not state.reviewer_checked_chat_surface:
            failures.append("reviewer passed a closed-Cockpit case without checking the chat Mermaid")
        if not state.reviewer_checked_route_match or not state.active_node_highlighted:
            failures.append("reviewer passed before checking active route/node match and highlight")
    if state.node_advanced and not state.reviewer_passed:
        failures.append("node advanced before reviewer display gate passed")
    return failures


def hazard_states() -> dict[str, State]:
    return {
        "chat_required_no_chat": State(
            route_frontier_loaded=True,
            current_node_resolved=True,
            display_trigger="major_node_entry",
            chat_display_required=True,
            simplified_mermaid_generated=True,
            english_flowpilot_labels=True,
            active_node_highlighted=True,
            reviewer_checked_display=True,
            reviewer_checked_route_match=True,
            reviewer_passed=True,
            node_work_started=True,
        ),
        "raw_flowguard_substituted": State(
            route_frontier_loaded=True,
            current_node_resolved=True,
            display_trigger="startup",
            chat_display_required=True,
            raw_flowguard_graph_used=True,
            reviewer_checked_display=True,
            reviewer_checked_chat_surface=True,
            reviewer_checked_route_match=True,
            reviewer_passed=True,
        ),
        "repair_without_return_edge": State(
            route_frontier_loaded=True,
            current_node_resolved=True,
            display_trigger="review_failure",
            chat_display_required=True,
            return_edge_required=True,
            simplified_mermaid_generated=True,
            english_flowpilot_labels=True,
            active_node_highlighted=True,
            chat_mermaid_displayed=True,
            reviewer_checked_display=True,
            reviewer_checked_chat_surface=True,
            reviewer_checked_route_match=True,
            reviewer_passed=True,
        ),
        "reviewer_file_only": State(
            route_frontier_loaded=True,
            current_node_resolved=True,
            display_trigger="startup",
            chat_display_required=True,
            simplified_mermaid_generated=True,
            english_flowpilot_labels=True,
            active_node_highlighted=True,
            chat_mermaid_displayed=True,
            reviewer_checked_route_match=True,
            reviewer_passed=True,
        ),
        "stale_active_node": State(
            route_frontier_loaded=True,
            current_node_resolved=True,
            display_trigger="completion",
            chat_display_required=True,
            simplified_mermaid_generated=True,
            english_flowpilot_labels=True,
            chat_mermaid_displayed=True,
            reviewer_checked_display=True,
            reviewer_checked_chat_surface=True,
            reviewer_checked_route_match=True,
            reviewer_passed=True,
        ),
        "advance_without_reviewer_gate": State(
            route_frontier_loaded=True,
            current_node_resolved=True,
            display_trigger="startup",
            chat_display_required=True,
            simplified_mermaid_generated=True,
            english_flowpilot_labels=True,
            active_node_highlighted=True,
            chat_mermaid_displayed=True,
            node_advanced=True,
        ),
        "major_node_entry_not_classified": State(
            route_frontier_loaded=True,
            current_node_resolved=True,
            display_trigger="major_node_entry",
            cockpit_open=False,
            chat_display_required=False,
            simplified_mermaid_generated=True,
            english_flowpilot_labels=True,
            active_node_highlighted=True,
            reviewer_checked_display=True,
            reviewer_checked_route_match=True,
            reviewer_passed=True,
            node_work_started=True,
        ),
        "cockpit_closed_ui_only": State(
            route_frontier_loaded=True,
            current_node_resolved=True,
            display_trigger="startup",
            cockpit_open=False,
            chat_display_required=True,
            simplified_mermaid_generated=True,
            english_flowpilot_labels=True,
            active_node_highlighted=True,
            cockpit_route_sign_displayed=True,
            reviewer_checked_display=True,
            reviewer_checked_route_match=True,
            reviewer_passed=True,
            node_work_started=True,
        ),
    }


def check_invariants(state: State) -> InvariantResult:
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.ok()
