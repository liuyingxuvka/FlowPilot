"""FlowGuard model for the FlowPilot current-node router packet loop.

Risk intent brief:
- Prevent Controller from turning packet relay into route authority.
- Protect sealed packet/result bodies and project evidence from Controller
  reads or authorship.
- Model-critical durable state: PM route activation, current-node packet
  registration, PM high-standard gate, reviewer dispatch, worker
  dispatch/result routing, reviewer pass/block, route mutation, stale
  evidence/frontier marking, node completion, final route-wide ledger
  source-of-truth generation, same-scope replay, generated-resource and visual
  evidence closure, and segmented final backward replay.
- Adversarial branches include packet registration before route activation,
  worker dispatch before reviewer dispatch, reviewer pass before result routing,
  result relay before packet-ledger checks, officer packet relay without an
  officer card, repair/recheck bypasses around the reviewer,
  route mutation without reviewer block or stale markers, PM completion before
  reviewer pass, final ledger without a current route scan/zero unresolved
  items/source-of-truth file, stale/unresolved evidence, pending generated
  resources, missing screenshots for UI/visual work, old assets reused as
  current evidence, final replay without a clean ledger or segment decisions,
  Controller body reads, and Controller-origin project evidence.
- Hard invariants: current-node packets require active route and fresh frontier;
  reviewer dispatch gates worker work; worker and officer results are
  packet-ledger checked before reviewer/PM relay; repair/recheck returns to the
  reviewer before PM completion; mutation requires reviewer block and stale
  evidence/frontier markers; same-scope replay reruns after mutation;
  evidence/quality package and reviewer evidence quality pass precede final
  ledger source-of-truth generation; final ledger and segmented replay are
  ordered terminal gates; Controller remains envelope-only.
- Blindspot: this is an abstract control-plane model, not a replay adapter for
  the concrete router implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MAX_ROUTE_MUTATIONS = 1


@dataclass(frozen=True)
class Tick:
    """One router/controller current-node loop tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | blocked | complete
    holder: str = "none"  # none | controller | pm | reviewer | worker | officer
    route_version: int = 0

    controller_boundary_confirmed: bool = False
    controller_read_sealed_body: bool = False
    controller_originated_project_evidence: bool = False
    controller_relayed_body_content: bool = False

    route_activated: bool = False
    officer_packet_card_delivered: bool = False
    officer_packet_relayed: bool = False
    officer_packet_identity_boundary_present: bool = False
    officer_result_returned: bool = False
    officer_result_identity_boundary_present: bool = False
    officer_result_ledger_checked: bool = False
    officer_result_routed_to_pm: bool = False
    pm_absorbed_officer_result: bool = False
    officer_lifecycle_flags_current: bool = False
    route_history_context_refreshed: bool = False
    pm_prior_path_context_reviewed: bool = False
    route_history_context_stale: bool = False
    node_acceptance_plan_prior_context_used: bool = False
    pm_prior_path_context_used_for_route_mutation: bool = False
    parent_segment_prior_context_used: bool = False
    evidence_quality_prior_context_used: bool = False
    final_ledger_prior_context_used: bool = False
    pm_node_high_standard_gate_opened: bool = False
    pm_node_high_standard_risks_reviewed: bool = False
    node_acceptance_plan_written: bool = False
    reviewer_node_acceptance_plan_reviewed: bool = False
    current_node_packet_registered: bool = False
    reviewer_dispatch_allowed: bool = False
    worker_dispatched: bool = False
    worker_packet_identity_boundary_present: bool = False
    worker_result_returned: bool = False
    worker_result_identity_boundary_present: bool = False
    worker_result_ledger_checked: bool = False
    worker_result_routed_to_reviewer: bool = False
    reviewer_decision: str = "none"  # none | pass | block
    reviewer_block_seen: bool = False
    repair_packet_registered: bool = False
    repair_dispatch_allowed: bool = False
    repair_worker_dispatched: bool = False
    repair_packet_identity_boundary_present: bool = False
    repair_result_returned: bool = False
    repair_result_identity_boundary_present: bool = False
    repair_result_ledger_checked: bool = False
    repair_result_routed_to_reviewer: bool = False
    repair_recheck_passed: bool = False
    pm_node_completed: bool = False
    parent_backward_targets_enumerated: bool = False
    parent_backward_replay_passed: bool = False
    parent_pm_segment_decision_recorded: bool = False
    parent_node_completed: bool = False

    route_mutation_count: int = 0
    stale_evidence_marked: bool = False
    frontier_marked_stale: bool = False
    frontier_rewritten_after_mutation: bool = False
    same_scope_replay_rerun_after_mutation: bool = False

    current_route_scan_done: bool = False
    pm_evidence_quality_package_card_delivered: bool = False
    evidence_quality_package_written: bool = False
    evidence_quality_reviewer_passed: bool = False
    stale_or_unresolved_evidence_present: bool = False
    pending_generated_resources: bool = False
    ui_visual_required: bool = False
    ui_visual_screenshots_present: bool = False
    old_assets_reused_as_current_evidence: bool = False
    unresolved_count_zero: bool = False
    pm_final_ledger_card_delivered: bool = False
    final_ledger_source_of_truth_generated: bool = False
    final_ledger_built: bool = False
    final_ledger_clean: bool = False
    terminal_replay_map_generated_from_final_ledger: bool = False
    terminal_replay_root_segment_passed: bool = False
    terminal_replay_parent_segment_passed: bool = False
    terminal_replay_leaf_segment_passed: bool = False
    terminal_replay_pm_segment_decisions_recorded: bool = False
    final_backward_replay_passed: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


class RouterLoopStep:
    """Model one current-node router transition.

    Input x State -> Set(Output x State)
    reads: route activation, packet loop holder, reviewer decision, mutation
    status, stale evidence/frontier state, and terminal ledger status
    writes: one control-plane fact, packet-loop handoff, mutation marker,
    terminal ledger fact, or terminal status
    idempotency: a repeated tick observes the current state and advances at
    most one missing fact; terminal states produce no further side effects.
    """

    name = "RouterLoopStep"
    reads = (
        "controller_boundary",
        "route_activation",
        "officer_packet_loop",
        "packet_loop",
        "repair_recheck_loop",
        "reviewer_decision",
        "route_mutation",
        "final_ledger",
    )
    writes = (
        "control_plane_fact",
        "packet_handoff",
        "packet_ledger_check",
        "route_mutation_marker",
        "final_ledger_fact",
        "terminal_status",
    )
    input_description = "current-node router tick"
    output_description = "one abstract FlowPilot packet-loop action"
    idempotency = "repeat ticks do not duplicate completed packet or ledger facts"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def _clear_current_node_cycle(state: State, **changes: object) -> State:
    return replace(
        state,
        route_activated=False,
        officer_packet_card_delivered=False,
        officer_packet_relayed=False,
        officer_packet_identity_boundary_present=False,
        officer_result_returned=False,
        officer_result_identity_boundary_present=False,
        officer_result_ledger_checked=False,
        officer_result_routed_to_pm=False,
        pm_absorbed_officer_result=False,
        officer_lifecycle_flags_current=False,
        route_history_context_refreshed=False,
        pm_prior_path_context_reviewed=False,
        route_history_context_stale=True,
        node_acceptance_plan_prior_context_used=False,
        parent_segment_prior_context_used=False,
        evidence_quality_prior_context_used=False,
        final_ledger_prior_context_used=False,
        pm_node_high_standard_gate_opened=False,
        pm_node_high_standard_risks_reviewed=False,
        node_acceptance_plan_written=False,
        reviewer_node_acceptance_plan_reviewed=False,
        current_node_packet_registered=False,
        reviewer_dispatch_allowed=False,
        worker_dispatched=False,
        worker_packet_identity_boundary_present=False,
        worker_result_returned=False,
        worker_result_identity_boundary_present=False,
        worker_result_ledger_checked=False,
        worker_result_routed_to_reviewer=False,
        reviewer_decision="none",
        repair_packet_registered=False,
        repair_dispatch_allowed=False,
        repair_worker_dispatched=False,
        repair_packet_identity_boundary_present=False,
        repair_result_returned=False,
        repair_result_identity_boundary_present=False,
        repair_result_ledger_checked=False,
        repair_result_routed_to_reviewer=False,
        repair_recheck_passed=False,
        pm_node_completed=False,
        parent_backward_targets_enumerated=False,
        parent_backward_replay_passed=False,
        parent_pm_segment_decision_recorded=False,
        parent_node_completed=False,
        same_scope_replay_rerun_after_mutation=False,
        current_route_scan_done=False,
        pm_evidence_quality_package_card_delivered=False,
        evidence_quality_package_written=False,
        evidence_quality_reviewer_passed=False,
        stale_or_unresolved_evidence_present=False,
        pending_generated_resources=False,
        ui_visual_required=False,
        ui_visual_screenshots_present=False,
        old_assets_reused_as_current_evidence=False,
        unresolved_count_zero=False,
        pm_final_ledger_card_delivered=False,
        final_ledger_source_of_truth_generated=False,
        final_ledger_built=False,
        final_ledger_clean=False,
        terminal_replay_map_generated_from_final_ledger=False,
        terminal_replay_root_segment_passed=False,
        terminal_replay_parent_segment_passed=False,
        terminal_replay_leaf_segment_passed=False,
        terminal_replay_pm_segment_decisions_recorded=False,
        final_backward_replay_passed=False,
        **changes,
    )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"blocked", "complete"}:
        return

    if not state.controller_boundary_confirmed:
        yield Transition(
            "controller_boundary_confirmed_envelope_only",
            replace(
                state,
                status="running",
                holder="controller",
                controller_boundary_confirmed=True,
            ),
        )
        return

    if state.route_mutation_count and not state.frontier_rewritten_after_mutation:
        yield Transition(
            "frontier_rewritten_for_mutated_route",
            replace(
                state,
                holder="pm",
                frontier_rewritten_after_mutation=True,
            ),
        )
        return

    if not state.route_activated:
        if state.route_version == 0:
            yield Transition(
                "pm_activates_route",
                replace(
                    state,
                    holder="pm",
                    route_version=1,
                    route_activated=True,
                ),
            )
            return
        yield Transition(
            "pm_activates_mutated_route",
            replace(state, holder="pm", route_activated=True),
        )
        return

    if not state.officer_lifecycle_flags_current:
        yield Transition(
            "officer_lifecycle_flags_reconciled_before_model_packet",
            replace(state, holder="pm", officer_lifecycle_flags_current=True),
        )
        return

    if not state.officer_packet_card_delivered:
        yield Transition(
            "officer_packet_card_delivered_before_controller_relay",
            replace(state, holder="officer", officer_packet_card_delivered=True),
        )
        return

    if not state.officer_packet_relayed:
        yield Transition(
            "officer_packet_relayed_after_officer_card",
            replace(
                state,
                holder="officer",
                officer_packet_relayed=True,
                officer_packet_identity_boundary_present=True,
            ),
        )
        return

    if not state.officer_result_returned:
        yield Transition(
            "officer_result_returned_to_packet_ledger",
            replace(
                state,
                holder="controller",
                officer_result_returned=True,
                officer_result_identity_boundary_present=True,
            ),
        )
        return

    if not state.officer_result_ledger_checked:
        yield Transition(
            "officer_result_ledger_checked_before_pm_relay",
            replace(state, holder="controller", officer_result_ledger_checked=True),
        )
        return

    if not state.officer_result_routed_to_pm:
        yield Transition(
            "officer_result_routed_to_pm_after_ledger_check",
            replace(state, holder="pm", officer_result_routed_to_pm=True),
        )
        return

    if not state.pm_absorbed_officer_result:
        yield Transition(
            "pm_absorbs_officer_result_before_node_packet",
            replace(state, holder="pm", pm_absorbed_officer_result=True),
        )
        return

    if (
        not state.node_acceptance_plan_written
        and (not state.route_history_context_refreshed or state.route_history_context_stale)
    ):
        yield Transition(
            "controller_refreshes_route_history_context_for_node_plan",
            replace(
                state,
                holder="controller",
                route_history_context_refreshed=True,
                pm_prior_path_context_reviewed=False,
                route_history_context_stale=False,
            ),
        )
        return

    if not state.node_acceptance_plan_written and not state.pm_prior_path_context_reviewed:
        yield Transition(
            "pm_reads_prior_path_context_for_node_plan",
            replace(state, holder="pm", pm_prior_path_context_reviewed=True),
        )
        return

    if not state.pm_node_high_standard_gate_opened:
        yield Transition(
            "pm_opens_current_node_high_standard_gate",
            replace(
                state,
                holder="pm",
                pm_node_high_standard_gate_opened=True,
                pm_node_high_standard_risks_reviewed=True,
            ),
        )
        return

    if not state.node_acceptance_plan_written:
        yield Transition(
            "pm_writes_node_acceptance_plan_before_packet",
            replace(
                state,
                holder="pm",
                node_acceptance_plan_written=True,
                node_acceptance_plan_prior_context_used=True,
            ),
        )
        return

    if not state.reviewer_node_acceptance_plan_reviewed:
        yield Transition(
            "reviewer_reviews_node_acceptance_plan_before_packet",
            replace(
                state,
                holder="reviewer",
                reviewer_node_acceptance_plan_reviewed=True,
            ),
        )
        return

    if not state.current_node_packet_registered:
        yield Transition(
            "current_node_packet_registered_after_route_activation_and_acceptance_plan",
            replace(
                state,
                holder="controller",
                current_node_packet_registered=True,
            ),
        )
        return

    if not state.reviewer_dispatch_allowed:
        yield Transition(
            "reviewer_dispatch_allowed_for_current_node",
            replace(state, holder="reviewer", reviewer_dispatch_allowed=True),
        )
        return

    if not state.worker_dispatched:
        yield Transition(
            "worker_dispatched_after_reviewer_dispatch",
            replace(
                state,
                holder="worker",
                worker_dispatched=True,
                worker_packet_identity_boundary_present=True,
            ),
        )
        return

    if not state.worker_result_returned:
        yield Transition(
            "worker_result_returned_to_packet_ledger",
            replace(
                state,
                holder="controller",
                worker_result_returned=True,
                worker_result_identity_boundary_present=True,
            ),
        )
        return

    if not state.worker_result_ledger_checked:
        yield Transition(
            "worker_result_ledger_checked_before_reviewer_relay",
            replace(state, holder="controller", worker_result_ledger_checked=True),
        )
        return

    if not state.worker_result_routed_to_reviewer:
        yield Transition(
            "worker_result_routed_to_reviewer",
            replace(
                state,
                holder="reviewer",
                worker_result_routed_to_reviewer=True,
            ),
        )
        return

    if state.reviewer_decision == "none":
        yield Transition(
            "reviewer_passes_current_node_result",
            replace(state, holder="reviewer", reviewer_decision="pass"),
        )
        if state.route_mutation_count < MAX_ROUTE_MUTATIONS:
            yield Transition(
                "reviewer_blocks_current_node_result",
                replace(
                    state,
                    holder="reviewer",
                    reviewer_decision="block",
                    reviewer_block_seen=True,
                    route_history_context_stale=True,
                ),
            )
        else:
            yield Transition(
                "reviewer_blocks_mutated_route_result_terminal",
                replace(
                    state,
                    status="blocked",
                    holder="reviewer",
                    reviewer_decision="block",
                    reviewer_block_seen=True,
                ),
            )
        return

    if state.reviewer_decision == "block":
        if not state.route_history_context_refreshed or state.route_history_context_stale:
            yield Transition(
                "controller_refreshes_route_history_context_for_repair_or_mutation",
                replace(
                    state,
                    holder="controller",
                    route_history_context_refreshed=True,
                    pm_prior_path_context_reviewed=False,
                    route_history_context_stale=False,
                ),
            )
            return

        if not state.pm_prior_path_context_reviewed:
            yield Transition(
                "pm_reads_prior_path_context_for_repair_or_mutation",
                replace(state, holder="pm", pm_prior_path_context_reviewed=True),
            )
            return

        if not state.repair_packet_registered:
            yield Transition(
                "pm_registers_repair_packet_after_reviewer_block",
                replace(state, holder="pm", repair_packet_registered=True),
            )
            if state.route_mutation_count < MAX_ROUTE_MUTATIONS:
                yield Transition(
                    "route_mutation_after_reviewer_block_marks_stale_evidence_and_frontier",
                    _clear_current_node_cycle(
                        state,
                        holder="pm",
                        route_version=state.route_version + 1,
                        route_mutation_count=state.route_mutation_count + 1,
                        pm_prior_path_context_used_for_route_mutation=True,
                        stale_evidence_marked=True,
                        frontier_marked_stale=True,
                        frontier_rewritten_after_mutation=False,
                    ),
                )
            return

        if not state.repair_dispatch_allowed:
            yield Transition(
                "reviewer_allows_repair_dispatch_after_block",
                replace(state, holder="reviewer", repair_dispatch_allowed=True),
            )
            return

        if not state.repair_worker_dispatched:
            yield Transition(
                "repair_worker_dispatched_after_reviewer_dispatch",
                replace(
                    state,
                    holder="worker",
                    repair_worker_dispatched=True,
                    repair_packet_identity_boundary_present=True,
                ),
            )
            return

        if not state.repair_result_returned:
            yield Transition(
                "repair_result_returned_to_packet_ledger",
                replace(
                    state,
                    holder="controller",
                    repair_result_returned=True,
                    repair_result_identity_boundary_present=True,
                ),
            )
            return

        if not state.repair_result_ledger_checked:
            yield Transition(
                "repair_result_ledger_checked_before_reviewer_relay",
                replace(state, holder="controller", repair_result_ledger_checked=True),
            )
            return

        if not state.repair_result_routed_to_reviewer:
            yield Transition(
                "repair_result_routed_to_reviewer_after_ledger_check",
                replace(state, holder="reviewer", repair_result_routed_to_reviewer=True),
            )
            return

        if not state.repair_recheck_passed:
            yield Transition(
                "reviewer_rechecks_repair_result",
                replace(state, holder="reviewer", repair_recheck_passed=True),
            )
            return

        yield Transition(
            "reviewer_passes_current_node_after_repair_recheck",
            replace(state, holder="reviewer", reviewer_decision="pass"),
        )
        return

    if state.reviewer_decision != "pass":
        return

    if not state.pm_node_completed:
        yield Transition(
            "pm_completes_current_node_after_reviewer_pass",
            replace(
                state,
                holder="pm",
                pm_node_completed=True,
                route_history_context_refreshed=False,
                pm_prior_path_context_reviewed=False,
                route_history_context_stale=True,
            ),
        )
        return

    if not state.parent_backward_targets_enumerated:
        yield Transition(
            "pm_enumerates_parent_backward_targets_after_node_completion",
            replace(state, holder="pm", parent_backward_targets_enumerated=True),
        )
        return

    if not state.parent_backward_replay_passed:
        yield Transition(
            "reviewer_parent_backward_replay_after_targets",
            replace(state, holder="reviewer", parent_backward_replay_passed=True),
        )
        return

    if (
        not state.parent_pm_segment_decision_recorded
        and (not state.route_history_context_refreshed or state.route_history_context_stale)
    ):
        yield Transition(
            "controller_refreshes_route_history_context_for_parent_segment",
            replace(
                state,
                holder="controller",
                route_history_context_refreshed=True,
                pm_prior_path_context_reviewed=False,
                route_history_context_stale=False,
            ),
        )
        return

    if not state.parent_pm_segment_decision_recorded and not state.pm_prior_path_context_reviewed:
        yield Transition(
            "pm_reads_prior_path_context_for_parent_segment",
            replace(state, holder="pm", pm_prior_path_context_reviewed=True),
        )
        return

    if not state.parent_pm_segment_decision_recorded:
        yield Transition(
            "pm_records_parent_segment_decision_after_backward_replay",
            replace(
                state,
                holder="pm",
                parent_pm_segment_decision_recorded=True,
                parent_segment_prior_context_used=True,
            ),
        )
        return

    if not state.parent_node_completed:
        yield Transition(
            "pm_completes_parent_node_after_replay_and_segment_decision",
            replace(state, holder="pm", parent_node_completed=True),
        )
        return

    if state.route_mutation_count and not state.same_scope_replay_rerun_after_mutation:
        yield Transition(
            "reviewer_reruns_same_scope_replay_after_route_mutation",
            replace(state, holder="reviewer", same_scope_replay_rerun_after_mutation=True),
        )
        return

    if not state.current_route_scan_done:
        yield Transition(
            "current_route_scanned_for_final_ledger",
            replace(state, holder="pm", current_route_scan_done=True),
        )
        return

    if not state.pm_evidence_quality_package_card_delivered:
        yield Transition(
            "pm_evidence_quality_package_card_delivered_before_final_ledger",
            replace(
                state,
                holder="pm",
                pm_evidence_quality_package_card_delivered=True,
            ),
        )
        return

    if not state.evidence_quality_package_written:
        yield Transition(
            "pm_writes_evidence_quality_package_before_final_ledger",
            replace(
                state,
                holder="pm",
                evidence_quality_package_written=True,
                evidence_quality_prior_context_used=True,
            ),
        )
        return

    if not state.evidence_quality_reviewer_passed:
        yield Transition(
            "reviewer_passes_evidence_quality_before_final_ledger",
            replace(
                state,
                holder="reviewer",
                evidence_quality_reviewer_passed=True,
                route_history_context_refreshed=False,
                pm_prior_path_context_reviewed=False,
                route_history_context_stale=True,
            ),
        )
        return

    if not state.route_history_context_refreshed or state.route_history_context_stale:
        yield Transition(
            "controller_refreshes_route_history_context_for_final_ledger",
            replace(
                state,
                holder="controller",
                route_history_context_refreshed=True,
                pm_prior_path_context_reviewed=False,
                route_history_context_stale=False,
            ),
        )
        return

    if not state.pm_prior_path_context_reviewed:
        yield Transition(
            "pm_reads_prior_path_context_for_final_ledger",
            replace(state, holder="pm", pm_prior_path_context_reviewed=True),
        )
        return

    if not state.unresolved_count_zero:
        yield Transition(
            "final_ledger_zero_unresolved_confirmed",
            replace(state, holder="pm", unresolved_count_zero=True),
        )
        yield Transition(
            "final_ledger_scan_finds_unresolved_items",
            replace(state, status="blocked", holder="pm"),
        )
        return

    if not state.pm_final_ledger_card_delivered:
        yield Transition(
            "pm_final_ledger_card_delivered_after_evidence_quality_pass",
            replace(
                state,
                holder="pm",
                pm_final_ledger_card_delivered=True,
                final_ledger_prior_context_used=True,
            ),
        )
        return

    if not state.final_ledger_source_of_truth_generated:
        yield Transition(
            "pm_generates_final_ledger_source_of_truth",
            replace(state, holder="pm", final_ledger_source_of_truth_generated=True),
        )
        return

    if not state.final_ledger_built:
        yield Transition(
            "pm_builds_clean_final_ledger",
            replace(
                state,
                holder="pm",
                final_ledger_built=True,
                final_ledger_clean=True,
                final_ledger_prior_context_used=True,
            ),
        )
        return

    if not state.terminal_replay_map_generated_from_final_ledger:
        yield Transition(
            "terminal_replay_map_generated_from_final_ledger",
            replace(
                state,
                holder="pm",
                terminal_replay_map_generated_from_final_ledger=True,
            ),
        )
        return

    if not state.terminal_replay_root_segment_passed:
        yield Transition(
            "reviewer_terminal_root_segment_replayed",
            replace(state, holder="reviewer", terminal_replay_root_segment_passed=True),
        )
        return

    if not state.terminal_replay_parent_segment_passed:
        yield Transition(
            "reviewer_terminal_parent_segment_replayed",
            replace(state, holder="reviewer", terminal_replay_parent_segment_passed=True),
        )
        return

    if not state.terminal_replay_leaf_segment_passed:
        yield Transition(
            "reviewer_terminal_leaf_segment_replayed",
            replace(state, holder="reviewer", terminal_replay_leaf_segment_passed=True),
        )
        return

    if not state.terminal_replay_pm_segment_decisions_recorded:
        yield Transition(
            "pm_records_terminal_segment_decisions",
            replace(
                state,
                holder="pm",
                terminal_replay_pm_segment_decisions_recorded=True,
            ),
        )
        return

    if not state.final_backward_replay_passed:
        yield Transition(
            "reviewer_final_backward_replay_after_all_segments",
            replace(state, holder="reviewer", final_backward_replay_passed=True),
        )
        return

    yield Transition(
        "completion_recorded_after_final_replay",
        replace(state, status="complete", holder="pm"),
    )


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []

    if state.controller_read_sealed_body:
        failures.append("Controller read a sealed packet/result body")
    if state.controller_originated_project_evidence:
        failures.append("Controller originated project evidence")
    if state.controller_relayed_body_content:
        failures.append("Controller relayed packet/result body content instead of envelope-only metadata")

    if state.route_activated and not state.controller_boundary_confirmed:
        failures.append("route activated before Controller relay boundary was confirmed")
    if state.officer_lifecycle_flags_current and not state.route_activated:
        failures.append("officer lifecycle flags reconciled before route activation")
    if state.officer_packet_card_delivered and not state.officer_lifecycle_flags_current:
        failures.append("officer packet card delivered before officer lifecycle flags were reconciled")
    if state.officer_packet_card_delivered and not state.route_activated:
        failures.append("officer packet card delivered before route activation")
    if state.officer_packet_relayed and not state.officer_packet_card_delivered:
        failures.append("officer packet relayed before officer card")
    if state.officer_packet_relayed and not state.officer_packet_identity_boundary_present:
        failures.append("officer packet relayed without packet recipient identity boundary")
    if state.officer_result_returned and not state.officer_packet_relayed:
        failures.append("officer result returned before officer packet relay")
    if state.officer_result_returned and not state.officer_result_identity_boundary_present:
        failures.append("officer result returned without completed-by identity boundary")
    if state.officer_result_ledger_checked and not state.officer_result_returned:
        failures.append("officer result ledger checked before officer result returned")
    if state.officer_result_routed_to_pm and not state.officer_result_ledger_checked:
        failures.append("officer result routed to PM before packet-ledger check")
    if state.pm_absorbed_officer_result and not state.officer_result_routed_to_pm:
        failures.append("PM absorbed officer result before result relay")
    if state.pm_node_high_standard_gate_opened and not (
        state.pm_absorbed_officer_result and state.pm_node_high_standard_risks_reviewed
    ):
        failures.append("PM high-standard gate opened before officer result absorption and risk review")
    if state.node_acceptance_plan_written and not state.node_acceptance_plan_prior_context_used:
        failures.append("node acceptance plan written before PM read fresh prior path context")
    if state.node_acceptance_plan_written and not state.pm_node_high_standard_gate_opened:
        failures.append("node acceptance plan written before PM high-standard gate")
    if state.node_acceptance_plan_written and not state.route_activated:
        failures.append("node acceptance plan written before route activation")
    if state.reviewer_node_acceptance_plan_reviewed and not state.node_acceptance_plan_written:
        failures.append("reviewer reviewed node acceptance plan before PM wrote it")
    if state.current_node_packet_registered and not state.route_activated:
        failures.append("current-node packet registered before route activation")
    if state.current_node_packet_registered and not (
        state.node_acceptance_plan_written
        and state.reviewer_node_acceptance_plan_reviewed
        and state.pm_node_high_standard_gate_opened
    ):
        failures.append("current-node packet registered before PM high-standard gate and reviewed node acceptance plan")
    if (
        state.current_node_packet_registered
        and state.route_mutation_count
        and not state.frontier_rewritten_after_mutation
    ):
        failures.append("current-node packet registered against stale mutation frontier")

    if state.reviewer_dispatch_allowed and not state.current_node_packet_registered:
        failures.append("reviewer dispatch allowed before current-node packet registration")
    if state.worker_dispatched and not state.reviewer_dispatch_allowed:
        failures.append("worker dispatched before reviewer dispatch")
    if state.worker_dispatched and not state.worker_packet_identity_boundary_present:
        failures.append("worker dispatched without packet recipient identity boundary")
    if state.worker_result_returned and not state.worker_dispatched:
        failures.append("worker result returned before worker dispatch")
    if state.worker_result_returned and not state.worker_result_identity_boundary_present:
        failures.append("worker result returned without completed-by identity boundary")
    if state.worker_result_ledger_checked and not state.worker_result_returned:
        failures.append("worker result ledger checked before result was returned")
    if state.worker_result_routed_to_reviewer and not (
        state.worker_result_returned and state.worker_result_ledger_checked
    ):
        failures.append("worker result routed before result was returned and packet-ledger checked")
    if state.reviewer_decision in {"pass", "block"} and not state.worker_result_routed_to_reviewer:
        failures.append("reviewer decided before worker result was routed to reviewer")
    if state.reviewer_decision == "pass" and not state.worker_result_routed_to_reviewer:
        failures.append("reviewer pass recorded before routed worker result")
    if state.repair_packet_registered and not state.reviewer_block_seen:
        failures.append("repair packet registered before reviewer block")
    if state.repair_dispatch_allowed and not state.repair_packet_registered:
        failures.append("reviewer allowed repair dispatch before repair packet")
    if state.repair_worker_dispatched and not state.repair_dispatch_allowed:
        failures.append("repair worker dispatched before reviewer repair dispatch")
    if state.repair_worker_dispatched and not state.repair_packet_identity_boundary_present:
        failures.append("repair worker dispatched without packet recipient identity boundary")
    if state.repair_result_returned and not state.repair_worker_dispatched:
        failures.append("repair result returned before repair worker dispatch")
    if state.repair_result_returned and not state.repair_result_identity_boundary_present:
        failures.append("repair result returned without completed-by identity boundary")
    if state.repair_result_ledger_checked and not state.repair_result_returned:
        failures.append("repair result ledger checked before repair result returned")
    if state.repair_result_routed_to_reviewer and not (
        state.repair_result_returned and state.repair_result_ledger_checked
    ):
        failures.append("repair result routed before result was returned and packet-ledger checked")
    if state.repair_recheck_passed and not state.repair_result_routed_to_reviewer:
        failures.append("repair recheck passed before repair result reached reviewer")
    if (
        state.reviewer_block_seen
        and state.route_mutation_count == 0
        and state.reviewer_decision == "pass"
        and not state.repair_recheck_passed
    ):
        failures.append("reviewer pass after block recorded without repair recheck")
    if state.pm_node_completed and state.reviewer_decision != "pass":
        failures.append("PM completed current node before reviewer pass")
    if state.pm_node_completed and state.reviewer_block_seen and not (
        state.route_mutation_count or state.repair_recheck_passed
    ):
        failures.append("PM completed repaired node before reviewer recheck or route mutation")
    if state.parent_backward_targets_enumerated and not state.pm_node_completed:
        failures.append("parent backward targets enumerated before current node completion")
    if state.parent_backward_replay_passed and not state.parent_backward_targets_enumerated:
        failures.append("parent backward replay passed before parent backward targets")
    if state.parent_pm_segment_decision_recorded and not state.parent_backward_replay_passed:
        failures.append("PM parent segment decision recorded before parent backward replay")
    if state.parent_pm_segment_decision_recorded and not state.parent_segment_prior_context_used:
        failures.append("PM parent segment decision recorded before PM read fresh prior path context")
    if state.parent_node_completed and not (
        state.parent_backward_replay_passed
        and state.parent_pm_segment_decision_recorded
    ):
        failures.append("parent node completed before parent backward replay and PM segment decision")

    if state.route_mutation_count and not state.reviewer_block_seen:
        failures.append("route mutation recorded without reviewer block")
    if state.route_mutation_count and not state.stale_evidence_marked:
        failures.append("route mutation did not mark affected evidence stale")
    if state.route_mutation_count and not state.frontier_marked_stale:
        failures.append("route mutation did not mark the execution frontier stale")
    if state.route_mutation_count and not state.pm_prior_path_context_used_for_route_mutation:
        failures.append("route mutation recorded before PM used prior path context")
    if state.frontier_rewritten_after_mutation and not state.route_mutation_count:
        failures.append("frontier rewrite recorded without a route mutation")
    if state.same_scope_replay_rerun_after_mutation and not (
        state.route_mutation_count and state.parent_node_completed
    ):
        failures.append("same-scope replay rerun recorded without route mutation and parent completion")

    if state.current_route_scan_done and not state.parent_node_completed:
        failures.append("current route scanned for final ledger before parent node completion")
    if (
        state.current_route_scan_done
        and state.route_mutation_count
        and not state.same_scope_replay_rerun_after_mutation
    ):
        failures.append("current route scanned for final ledger before same-scope replay rerun after mutation")
    if state.pm_evidence_quality_package_card_delivered and not state.current_route_scan_done:
        failures.append("PM evidence/quality package card delivered before current route scan")
    if state.evidence_quality_package_written and not (
        state.pm_evidence_quality_package_card_delivered
        and state.current_route_scan_done
    ):
        failures.append("PM evidence/quality package written before package card and current route scan")
    if state.evidence_quality_package_written and not state.evidence_quality_prior_context_used:
        failures.append("PM evidence/quality package written before PM read fresh prior path context")
    if state.evidence_quality_reviewer_passed and not state.evidence_quality_package_written:
        failures.append("reviewer evidence quality pass recorded before PM evidence/quality package")
    if state.unresolved_count_zero and not state.current_route_scan_done:
        failures.append("zero unresolved final ledger count confirmed before current route scan")
    if state.unresolved_count_zero and state.stale_or_unresolved_evidence_present:
        failures.append("zero unresolved final ledger count confirmed while stale or unresolved evidence remained")
    if state.unresolved_count_zero and state.pending_generated_resources:
        failures.append("zero unresolved final ledger count confirmed while generated resources were still pending")
    if state.unresolved_count_zero and (
        state.ui_visual_required and not state.ui_visual_screenshots_present
    ):
        failures.append("zero unresolved final ledger count confirmed before required UI/visual screenshots existed")
    if state.unresolved_count_zero and state.old_assets_reused_as_current_evidence:
        failures.append("zero unresolved final ledger count confirmed while old assets were reused as current evidence")
    if state.pm_final_ledger_card_delivered and not state.pm_evidence_quality_package_card_delivered:
        failures.append("PM final ledger card delivered before PM evidence/quality package card")
    if state.pm_final_ledger_card_delivered and not state.evidence_quality_reviewer_passed:
        failures.append("PM final ledger card delivered before reviewer evidence quality pass")
    if state.pm_final_ledger_card_delivered and not state.final_ledger_prior_context_used:
        failures.append("PM final ledger card delivered before PM read fresh prior path context")
    if state.final_ledger_source_of_truth_generated and not (
        state.current_route_scan_done
        and state.unresolved_count_zero
        and state.pm_final_ledger_card_delivered
        and state.evidence_quality_reviewer_passed
    ):
        failures.append("final ledger source of truth generated before current route scan, zero unresolved, final-ledger card, and reviewer evidence quality pass")
    if state.final_ledger_built and not (
        state.parent_node_completed
        and state.current_route_scan_done
        and state.unresolved_count_zero
        and state.pm_final_ledger_card_delivered
        and state.evidence_quality_reviewer_passed
        and state.final_ledger_source_of_truth_generated
    ):
        failures.append("final ledger built before parent node completion, current route scan, zero unresolved, final-ledger card, evidence quality reviewer pass, and source-of-truth generation")
    if state.final_ledger_built and not state.final_ledger_prior_context_used:
        failures.append("final ledger built before PM read fresh prior path context")
    if state.final_ledger_built and state.stale_or_unresolved_evidence_present:
        failures.append("final ledger built while stale or unresolved evidence remained")
    if state.final_ledger_built and state.pending_generated_resources:
        failures.append("final ledger built while generated resources were still pending")
    if state.final_ledger_built and (
        state.ui_visual_required and not state.ui_visual_screenshots_present
    ):
        failures.append("final ledger built before required UI/visual screenshots existed")
    if state.final_ledger_built and state.old_assets_reused_as_current_evidence:
        failures.append("final ledger built while old assets were reused as current evidence")
    if state.final_ledger_clean and not state.final_ledger_built:
        failures.append("final ledger marked clean before it was built")
    if state.terminal_replay_map_generated_from_final_ledger and not (
        state.final_ledger_clean and state.final_ledger_source_of_truth_generated
    ):
        failures.append("terminal replay map generated before clean source-of-truth final ledger")
    if state.terminal_replay_root_segment_passed and not state.terminal_replay_map_generated_from_final_ledger:
        failures.append("terminal root segment replayed before replay map generation")
    if state.terminal_replay_parent_segment_passed and not state.terminal_replay_root_segment_passed:
        failures.append("terminal parent segment replayed before root segment")
    if state.terminal_replay_leaf_segment_passed and not state.terminal_replay_parent_segment_passed:
        failures.append("terminal leaf segment replayed before parent segment")
    if state.terminal_replay_pm_segment_decisions_recorded and not (
        state.terminal_replay_root_segment_passed
        and state.terminal_replay_parent_segment_passed
        and state.terminal_replay_leaf_segment_passed
    ):
        failures.append("PM terminal segment decisions recorded before all terminal replay segments")
    if state.final_backward_replay_passed and not (
        state.final_ledger_clean
        and state.terminal_replay_map_generated_from_final_ledger
        and state.terminal_replay_pm_segment_decisions_recorded
    ):
        failures.append("final backward replay passed before clean ledger, replay map, and PM segment decisions")
    if state.status == "complete" and not state.final_backward_replay_passed:
        failures.append("completion recorded before final backward replay")

    return failures


def router_loop_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_router_current_node_packet_loop",
        description=(
        "The current-node packet loop requires route activation before packet "
            "registration, a PM high-standard gate and reviewed node acceptance "
            "plan before the packet, officer lifecycle flags before officer "
            "packet relay, reviewer dispatch before worker or repair work, "
            "packet-ledger checks before worker/officer result relay, reviewer "
            "recheck before repaired completion, reviewer-blocked route mutation "
            "with stale evidence/frontier markers, same-scope replay after "
            "mutation, parent backward replay plus PM segment decision before "
            "parent completion, evidence-quality review and resource closure "
            "before final ledger source of truth, and clean final ledger before "
            "segmented terminal backward replay."
        ),
        predicate=router_loop_invariant,
    ),
)


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 70


def build_workflow() -> Workflow:
    return Workflow((RouterLoopStep(),), name="flowpilot_router_current_node_loop")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


def _active_packet_loop(**changes: object) -> State:
    base = State(
        status="running",
        holder="reviewer",
        route_version=1,
        controller_boundary_confirmed=True,
        route_activated=True,
        officer_packet_card_delivered=True,
        officer_packet_relayed=True,
        officer_packet_identity_boundary_present=True,
        officer_result_returned=True,
        officer_result_identity_boundary_present=True,
        officer_result_ledger_checked=True,
        officer_result_routed_to_pm=True,
        pm_absorbed_officer_result=True,
        officer_lifecycle_flags_current=True,
        route_history_context_refreshed=True,
        pm_prior_path_context_reviewed=True,
        node_acceptance_plan_prior_context_used=True,
        pm_node_high_standard_gate_opened=True,
        pm_node_high_standard_risks_reviewed=True,
        node_acceptance_plan_written=True,
        reviewer_node_acceptance_plan_reviewed=True,
        current_node_packet_registered=True,
        reviewer_dispatch_allowed=True,
        worker_dispatched=True,
        worker_packet_identity_boundary_present=True,
        worker_result_returned=True,
        worker_result_identity_boundary_present=True,
        worker_result_ledger_checked=True,
        worker_result_routed_to_reviewer=True,
    )
    return replace(base, **changes)


def _reviewer_passed(**changes: object) -> State:
    return _active_packet_loop(reviewer_decision="pass", **changes)


def _reviewer_blocked(**changes: object) -> State:
    return _active_packet_loop(
        reviewer_decision="block",
        reviewer_block_seen=True,
        **changes,
    )


def _mutated(**changes: object) -> State:
    base = State(
        status="running",
        holder="pm",
        route_version=2,
        controller_boundary_confirmed=True,
        route_mutation_count=1,
        reviewer_block_seen=True,
        pm_prior_path_context_used_for_route_mutation=True,
        stale_evidence_marked=True,
        frontier_marked_stale=True,
        route_history_context_stale=True,
    )
    return replace(base, **changes)


def _node_completed(**changes: object) -> State:
    return _reviewer_passed(pm_node_completed=True, **changes)


def _parent_completed(**changes: object) -> State:
    base = _node_completed(
        parent_backward_targets_enumerated=True,
        parent_backward_replay_passed=True,
        parent_pm_segment_decision_recorded=True,
        parent_node_completed=True,
        parent_segment_prior_context_used=True,
        route_history_context_refreshed=False,
        pm_prior_path_context_reviewed=False,
        route_history_context_stale=True,
    )
    return replace(base, **changes)


def _final_ready(**changes: object) -> State:
    base = _parent_completed(
        current_route_scan_done=True,
        pm_evidence_quality_package_card_delivered=True,
        evidence_quality_package_written=True,
        evidence_quality_prior_context_used=True,
        evidence_quality_reviewer_passed=True,
        route_history_context_refreshed=True,
        pm_prior_path_context_reviewed=True,
        route_history_context_stale=False,
        unresolved_count_zero=True,
        pm_final_ledger_card_delivered=True,
        final_ledger_source_of_truth_generated=True,
        final_ledger_built=True,
        final_ledger_clean=True,
        final_ledger_prior_context_used=True,
        terminal_replay_map_generated_from_final_ledger=True,
        terminal_replay_root_segment_passed=True,
        terminal_replay_parent_segment_passed=True,
        terminal_replay_leaf_segment_passed=True,
        terminal_replay_pm_segment_decisions_recorded=True,
    )
    return replace(base, **changes)


def hazard_states() -> dict[str, State]:
    return {
        "packet_registered_before_route_activation": State(
            status="running",
            controller_boundary_confirmed=True,
            current_node_packet_registered=True,
        ),
        "officer_packet_card_before_route_activation": State(
            status="running",
            controller_boundary_confirmed=True,
            officer_packet_card_delivered=True,
        ),
        "officer_packet_card_before_lifecycle_flags": State(
            status="running",
            controller_boundary_confirmed=True,
            route_version=1,
            route_activated=True,
            officer_packet_card_delivered=True,
            officer_lifecycle_flags_current=False,
        ),
        "officer_packet_relayed_without_officer_card": State(
            status="running",
            controller_boundary_confirmed=True,
            route_version=1,
            route_activated=True,
            officer_packet_relayed=True,
        ),
        "officer_result_routed_without_ledger_check": State(
            status="running",
            controller_boundary_confirmed=True,
            route_version=1,
            route_activated=True,
            officer_packet_card_delivered=True,
            officer_packet_relayed=True,
            officer_result_returned=True,
            officer_result_routed_to_pm=True,
            officer_result_ledger_checked=False,
        ),
        "worker_dispatched_before_reviewer_dispatch": State(
            status="running",
            controller_boundary_confirmed=True,
            route_version=1,
            route_activated=True,
            node_acceptance_plan_written=True,
            reviewer_node_acceptance_plan_reviewed=True,
            current_node_packet_registered=True,
            worker_dispatched=True,
        ),
        "reviewer_acceptance_plan_review_without_plan": State(
            status="running",
            controller_boundary_confirmed=True,
            route_version=1,
            route_activated=True,
            reviewer_node_acceptance_plan_reviewed=True,
        ),
        "node_acceptance_plan_without_pm_high_standard_gate": State(
            status="running",
            controller_boundary_confirmed=True,
            route_version=1,
            route_activated=True,
            officer_lifecycle_flags_current=True,
            route_history_context_refreshed=True,
            pm_prior_path_context_reviewed=True,
            node_acceptance_plan_written=True,
        ),
        "node_acceptance_plan_without_prior_path_context": State(
            status="running",
            controller_boundary_confirmed=True,
            route_version=1,
            route_activated=True,
            officer_lifecycle_flags_current=True,
            pm_node_high_standard_gate_opened=True,
            pm_node_high_standard_risks_reviewed=True,
            node_acceptance_plan_written=True,
            route_history_context_refreshed=False,
            pm_prior_path_context_reviewed=False,
        ),
        "packet_registered_before_acceptance_plan_review": State(
            status="running",
            controller_boundary_confirmed=True,
            route_version=1,
            route_activated=True,
            pm_node_high_standard_gate_opened=True,
            pm_node_high_standard_risks_reviewed=True,
            current_node_packet_registered=True,
        ),
        "reviewer_pass_without_routed_worker_result": _active_packet_loop(
            worker_result_routed_to_reviewer=False,
            reviewer_decision="pass",
        ),
        "worker_result_routed_without_ledger_check": _active_packet_loop(
            worker_result_ledger_checked=False,
            worker_result_routed_to_reviewer=True,
        ),
        "pm_completion_without_reviewer_pass": _active_packet_loop(
            reviewer_decision="none",
            pm_node_completed=True,
        ),
        "repair_packet_without_reviewer_block": _active_packet_loop(
            repair_packet_registered=True,
            reviewer_decision="none",
            reviewer_block_seen=False,
        ),
        "repair_worker_dispatched_before_reviewer_dispatch": _reviewer_blocked(
            repair_packet_registered=True,
            repair_worker_dispatched=True,
            repair_dispatch_allowed=False,
        ),
        "repair_result_routed_without_ledger_check": _reviewer_blocked(
            repair_packet_registered=True,
            repair_dispatch_allowed=True,
            repair_worker_dispatched=True,
            repair_result_returned=True,
            repair_result_routed_to_reviewer=True,
            repair_result_ledger_checked=False,
        ),
        "repair_recheck_without_reviewer_result": _reviewer_blocked(
            repair_packet_registered=True,
            repair_dispatch_allowed=True,
            repair_worker_dispatched=True,
            repair_result_returned=True,
            repair_result_ledger_checked=True,
            repair_recheck_passed=True,
            repair_result_routed_to_reviewer=False,
        ),
        "pm_completion_after_block_without_recheck": _active_packet_loop(
            reviewer_decision="pass",
            reviewer_block_seen=True,
            repair_recheck_passed=False,
            pm_node_completed=True,
        ),
        "route_mutation_without_reviewer_block": _mutated(reviewer_block_seen=False),
        "route_mutation_without_stale_evidence": _mutated(stale_evidence_marked=False),
        "route_mutation_without_stale_frontier": _mutated(frontier_marked_stale=False),
        "route_mutation_without_prior_path_context": _mutated(
            pm_prior_path_context_used_for_route_mutation=False
        ),
        "packet_registered_against_stale_mutation_frontier": _mutated(
            route_activated=True,
            officer_lifecycle_flags_current=True,
            pm_node_high_standard_gate_opened=True,
            pm_node_high_standard_risks_reviewed=True,
            node_acceptance_plan_written=True,
            reviewer_node_acceptance_plan_reviewed=True,
            current_node_packet_registered=True,
            frontier_rewritten_after_mutation=False,
        ),
        "final_scan_before_same_scope_replay_after_mutation": _parent_completed(
            route_mutation_count=1,
            stale_evidence_marked=True,
            frontier_marked_stale=True,
            frontier_rewritten_after_mutation=True,
            same_scope_replay_rerun_after_mutation=False,
            current_route_scan_done=True,
        ),
        "parent_completed_without_backward_replay": _node_completed(
            parent_node_completed=True,
        ),
        "parent_completed_without_pm_segment_decision": _node_completed(
            parent_backward_targets_enumerated=True,
            parent_backward_replay_passed=True,
            parent_node_completed=True,
        ),
        "parent_segment_decision_without_prior_path_context": _node_completed(
            parent_backward_targets_enumerated=True,
            parent_backward_replay_passed=True,
            parent_pm_segment_decision_recorded=True,
            route_history_context_refreshed=False,
            pm_prior_path_context_reviewed=False,
            route_history_context_stale=True,
        ),
        "final_ledger_card_before_evidence_quality_package_card": _parent_completed(
            current_route_scan_done=True,
            pm_final_ledger_card_delivered=True,
        ),
        "final_ledger_card_before_reviewer_evidence_quality_pass": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            pm_final_ledger_card_delivered=True,
        ),
        "final_ledger_built_before_evidence_quality_reviewer_pass": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_built=True,
            final_ledger_clean=True,
        ),
        "final_ledger_without_parent_completion": _node_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_built=True,
            final_ledger_clean=True,
        ),
        "final_ledger_without_node_completion": State(
            status="running",
            controller_boundary_confirmed=True,
            route_version=1,
            route_activated=True,
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_built=True,
            final_ledger_clean=True,
        ),
        "final_ledger_without_current_route_scan": _parent_completed(
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_built=True,
            final_ledger_clean=True,
        ),
        "final_ledger_with_unresolved_items": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            unresolved_count_zero=False,
            pm_final_ledger_card_delivered=True,
            final_ledger_built=True,
            final_ledger_clean=True,
        ),
        "final_ledger_without_source_of_truth_generation": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            route_history_context_refreshed=True,
            pm_prior_path_context_reviewed=True,
            route_history_context_stale=False,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_source_of_truth_generated=False,
            final_ledger_built=True,
            final_ledger_clean=True,
        ),
        "final_ledger_card_without_prior_path_context": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            pm_final_ledger_card_delivered=True,
            route_history_context_refreshed=False,
            pm_prior_path_context_reviewed=False,
            route_history_context_stale=True,
        ),
        "final_ledger_without_prior_path_context": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_source_of_truth_generated=True,
            final_ledger_built=True,
            final_ledger_clean=True,
            route_history_context_refreshed=False,
            pm_prior_path_context_reviewed=False,
            route_history_context_stale=True,
        ),
        "final_ledger_with_stale_or_unresolved_evidence": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            stale_or_unresolved_evidence_present=True,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_built=True,
            final_ledger_clean=True,
        ),
        "final_ledger_with_pending_generated_resources": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            pending_generated_resources=True,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_built=True,
            final_ledger_clean=True,
        ),
        "final_ledger_missing_ui_visual_screenshots": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            ui_visual_required=True,
            ui_visual_screenshots_present=False,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_built=True,
            final_ledger_clean=True,
        ),
        "final_ledger_reuses_old_assets_as_current_evidence": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            old_assets_reused_as_current_evidence=True,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_built=True,
            final_ledger_clean=True,
        ),
        "final_backward_replay_without_clean_ledger": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_source_of_truth_generated=True,
            final_ledger_built=True,
            final_ledger_clean=False,
            terminal_replay_map_generated_from_final_ledger=True,
            terminal_replay_root_segment_passed=True,
            terminal_replay_parent_segment_passed=True,
            terminal_replay_leaf_segment_passed=True,
            terminal_replay_pm_segment_decisions_recorded=True,
            final_backward_replay_passed=True,
        ),
        "terminal_replay_map_without_source_ledger": _parent_completed(
            current_route_scan_done=True,
            pm_evidence_quality_package_card_delivered=True,
            evidence_quality_package_written=True,
            evidence_quality_reviewer_passed=True,
            unresolved_count_zero=True,
            pm_final_ledger_card_delivered=True,
            final_ledger_source_of_truth_generated=False,
            final_ledger_built=True,
            final_ledger_clean=True,
            terminal_replay_map_generated_from_final_ledger=True,
        ),
        "terminal_parent_segment_before_root": _final_ready(
            terminal_replay_map_generated_from_final_ledger=True,
            terminal_replay_root_segment_passed=False,
            terminal_replay_parent_segment_passed=True,
        ),
        "terminal_leaf_segment_before_parent": _final_ready(
            terminal_replay_map_generated_from_final_ledger=True,
            terminal_replay_root_segment_passed=True,
            terminal_replay_parent_segment_passed=False,
            terminal_replay_leaf_segment_passed=True,
        ),
        "terminal_pm_decisions_before_segments": _final_ready(
            terminal_replay_map_generated_from_final_ledger=True,
            terminal_replay_root_segment_passed=True,
            terminal_replay_parent_segment_passed=False,
            terminal_replay_leaf_segment_passed=True,
            terminal_replay_pm_segment_decisions_recorded=True,
        ),
        "final_backward_replay_without_segments": _final_ready(
            terminal_replay_map_generated_from_final_ledger=True,
            terminal_replay_root_segment_passed=True,
            terminal_replay_parent_segment_passed=True,
            terminal_replay_leaf_segment_passed=True,
            terminal_replay_pm_segment_decisions_recorded=False,
            final_backward_replay_passed=True,
        ),
        "controller_reads_sealed_body": State(
            status="running",
            controller_boundary_confirmed=True,
            controller_read_sealed_body=True,
        ),
        "controller_originates_project_evidence": State(
            status="running",
            controller_boundary_confirmed=True,
            controller_originated_project_evidence=True,
        ),
        "controller_relays_body_content": State(
            status="running",
            controller_boundary_confirmed=True,
            controller_relayed_body_content=True,
        ),
        "completion_before_final_backward_replay": _final_ready(status="complete"),
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
    "router_loop_invariant",
]
