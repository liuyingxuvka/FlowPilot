"""FlowGuard model for FlowPilot control-plane friction fixes.

Risk intent brief:
- Prevent prompt-isolation shortcuts from becoming handoff dead ends.
- Preserve Controller's envelope-only boundary while reducing purely
  mechanical handoff steps.
- Model-critical durable state: research package fields, worker packet
  materialization, packet/result open receipts, control-blocker routing,
  stop lifecycle reconciliation, active-task authority, display snapshot
  freshness, required phase-source context, and live-run artifact registration.
- Adversarial branches include dropped research scope fields, reviewer reports
  accepted without a result-body receipt, missing-receipt blockers escalated to
  PM instead of same-role reissue, stopped runs with live heartbeat/crew/packet
  state, stale snapshots treated as active UI state, ambiguous multi-active
  runs under current-json-only authority, product architecture delivery without
  PM material-understanding source paths, protocol blockers written outside
  router-visible state, stage-advance views left stale, and optimized
  transactions that skip hash, role, or Controller-boundary checks.
- Hard invariants: package-to-packet fields are preserved; reviewer decisions
  require legal open receipts; missing receipt repair is same-role reissue;
  stopped runs reconcile all visible lifecycle authorities; active snapshots
  are fresh; phase cards carry required source context; protocol blockers are
  router-visible; stage-advance views refresh; multi-active visibility has
  explicit authority; optimized transactions keep hash, role, and envelope-only
  guarantees.
- Blindspot: this is still a focused control-plane model. The live-run audit
  checks file-level consistency, but it does not prove product content quality.
"""

from __future__ import annotations

import ast
import json
import hashlib
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class Tick:
    """One control-plane handoff tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | complete
    mode: str = "unknown"  # unknown | expanded | optimized
    holder: str = "controller"
    handoff_steps: int = 0

    controller_boundary_confirmed: bool = False
    controller_read_sealed_body: bool = False
    role_identity_checked: bool = False
    hash_verified: bool = False

    pm_research_package_written: bool = False
    research_package_has_decision_question: bool = False
    research_package_has_allowed_sources: bool = False
    research_package_has_stop_conditions: bool = False
    research_capability_decision_recorded: bool = False
    worker_packet_written: bool = False
    worker_packet_preserves_research_fields: bool = False

    packet_delivered: bool = False
    packet_body_open_receipt: bool = False
    result_returned: bool = False
    result_routed_to_reviewer: bool = False
    result_body_open_receipt: bool = False
    reviewer_report_written: bool = False
    reviewer_report_accepted: bool = False

    pm_material_understanding_written: bool = False
    pm_material_understanding_source_available: bool = False
    product_architecture_card_delivered: bool = False
    product_architecture_delivery_has_material_context: bool = False
    protocol_blocker_file_written: bool = False
    protocol_blocker_registered_in_router_state: bool = False
    control_blocker_artifact_status_written: bool = False
    control_blocker_router_index_matches_artifact: bool = True
    phase_dependency_cards_delivered: bool = False
    phase_required_sources_complete: bool = False
    delivered_card_phase_context_fresh: bool = False
    terminal_snapshot_published: bool = False
    terminal_snapshot_flags_consistent: bool = True
    child_skill_gate_review_recorded: bool = False
    child_skill_gate_manifest_synced_with_review: bool = True
    terminal_continuation_cleanup_recorded: bool = False
    terminal_host_automation_cleanup_proven: bool = True
    role_output_envelopes_recorded: bool = False
    role_output_hashes_replayable: bool = True
    stage_advanced_after_material_scan: bool = False
    frontier_fresh_after_stage_advance: bool = False
    product_stage_view_published: bool = False
    product_stage_view_fresh: bool = False
    route_draft_written: bool = False
    route_draft_has_nodes: bool = True
    route_draft_single_canonical_source: bool = True
    route_draft_shadow_source_used: bool = False
    route_process_check_card_delivered: bool = False
    route_process_check_passed: bool = False
    route_draft_repaired_after_check: bool = False
    route_review_flags_reset_after_draft_repair: bool = True

    optimized_relay_transaction: bool = False
    optimized_transaction_records_delivery: bool = False
    optimized_transaction_records_open_receipts: bool = False
    optimized_transaction_records_result_return: bool = False

    receipt_missing_blocker: bool = False
    control_blocker_lane: str = "none"  # none | control_plane_reissue | pm_repair_decision_required
    control_blocker_target_role: str = "none"  # none | human_like_reviewer | project_manager
    pm_repair_decision_recorded: bool = False
    control_blocker_followup_event_matchable: bool = True
    control_resolution_predicate_normalized: bool = True

    stop_requested: bool = False
    current_status_stopped: bool = False
    continuation_heartbeat_active: bool = False
    crew_live_agents_active: bool = False
    packet_loop_active: bool = False
    frontier_terminal: bool = False

    snapshot_published_as_active: bool = False
    snapshot_fresh_against_frontier_and_ledger: bool = False
    multiple_running_index_entries_visible: bool = False
    active_task_authority: str = "current_json_only"  # current_json_only | explicit_active_set


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


class ControlPlaneStep:
    """Model one FlowPilot control-plane handoff transition.

    Input x State -> Set(Output x State)
    reads: package scope, packet receipts, blocker lane, lifecycle authorities,
    snapshot freshness, and optimized transaction markers
    writes: one durable control-plane fact or terminal status
    idempotency: each fact is monotonic; repeated ticks do not duplicate
    receipts or reopen sealed bodies
    """

    name = "ControlPlaneStep"
    input_description = "control-plane handoff tick"
    output_description = "one FlowPilot friction-control transition"
    reads = (
        "controller_boundary",
        "research_package",
        "packet_receipts",
        "control_blocker_lane",
        "lifecycle_authorities",
        "active_snapshot",
    )
    writes = (
        "package_materialization",
        "packet_transaction_receipt",
        "blocker_route",
        "lifecycle_reconciliation",
        "snapshot_refresh",
        "terminal_status",
    )
    idempotency = "monotonic state facts; optimized transaction records one composite receipt"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def _inc(state: State, **changes: object) -> State:
    return replace(state, handoff_steps=state.handoff_steps + 1, **changes)


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "complete":
        return

    if not state.controller_boundary_confirmed:
        yield Transition(
            "controller_boundary_confirmed_envelope_only",
            _inc(state, status="running", controller_boundary_confirmed=True),
        )
        return

    if state.mode == "unknown":
        yield Transition("select_expanded_safe_flow", _inc(state, mode="expanded"))
        yield Transition("select_optimized_transaction_flow", _inc(state, mode="optimized"))
        return

    if not state.pm_research_package_written:
        yield Transition(
            "pm_writes_research_package_with_scope_fields",
            _inc(
                state,
                holder="pm",
                pm_research_package_written=True,
                research_package_has_decision_question=True,
                research_package_has_allowed_sources=True,
                research_package_has_stop_conditions=True,
            ),
        )
        return

    if not state.research_capability_decision_recorded:
        yield Transition(
            "pm_records_research_capability_decision_preserving_package_scope",
            _inc(state, holder="pm", research_capability_decision_recorded=True),
        )
        return

    if not state.worker_packet_written:
        yield Transition(
            "worker_packet_materialized_with_research_scope",
            _inc(
                state,
                holder="controller",
                worker_packet_written=True,
                worker_packet_preserves_research_fields=True,
            ),
        )
        return

    if state.mode == "optimized":
        if not state.optimized_relay_transaction:
            yield Transition(
                "optimized_relay_transaction_records_delivery_open_and_hash",
                _inc(
                    state,
                    holder="reviewer",
                    packet_delivered=True,
                    packet_body_open_receipt=True,
                    result_returned=True,
                    result_routed_to_reviewer=True,
                    result_body_open_receipt=True,
                    optimized_relay_transaction=True,
                    optimized_transaction_records_delivery=True,
                    optimized_transaction_records_open_receipts=True,
                    optimized_transaction_records_result_return=True,
                    role_identity_checked=True,
                    hash_verified=True,
                ),
            )
            return
    else:
        if not state.packet_delivered:
            yield Transition("packet_delivered_by_controller", _inc(state, holder="worker", packet_delivered=True))
            return
        if not state.packet_body_open_receipt:
            yield Transition(
                "target_records_packet_body_open_receipt",
                _inc(state, holder="worker", packet_body_open_receipt=True, role_identity_checked=True, hash_verified=True),
            )
            return
        if not state.result_returned:
            yield Transition("worker_result_returned_to_ledger", _inc(state, holder="controller", result_returned=True))
            return
        if not state.result_routed_to_reviewer:
            yield Transition(
                "controller_routes_result_to_reviewer_after_ledger_check",
                _inc(state, holder="reviewer", result_routed_to_reviewer=True),
            )
            return
        if not state.result_body_open_receipt:
            yield Transition(
                "reviewer_records_result_body_open_receipt",
                _inc(state, holder="reviewer", result_body_open_receipt=True),
            )
            return

    if not state.reviewer_report_written:
        yield Transition(
            "reviewer_writes_report_after_receipts",
            _inc(state, holder="reviewer", reviewer_report_written=True),
        )
        return

    if not state.reviewer_report_accepted:
        yield Transition(
            "router_accepts_reviewer_report",
            _inc(state, holder="controller", reviewer_report_accepted=True),
        )
        return

    if not state.pm_material_understanding_written:
        yield Transition(
            "pm_material_understanding_written_to_canonical_files",
            _inc(
                state,
                holder="pm",
                pm_material_understanding_written=True,
                pm_material_understanding_source_available=True,
            ),
        )
        return

    if not state.product_architecture_card_delivered:
        yield Transition(
            "product_architecture_card_delivered_with_material_context_and_fresh_views",
            _inc(
                state,
                holder="pm",
                product_architecture_card_delivered=True,
                product_architecture_delivery_has_material_context=True,
                phase_dependency_cards_delivered=True,
                phase_required_sources_complete=True,
                delivered_card_phase_context_fresh=True,
                stage_advanced_after_material_scan=True,
                frontier_fresh_after_stage_advance=True,
                product_stage_view_published=True,
                product_stage_view_fresh=True,
            ),
        )
        return

    if not state.route_draft_written:
        yield Transition(
            "pm_writes_route_draft_with_nonempty_nodes",
            _inc(state, holder="pm", route_draft_written=True, route_draft_has_nodes=True),
        )
        return

    if state.route_draft_written and not state.route_process_check_card_delivered:
        yield Transition(
            "route_process_check_card_delivered_with_route_draft_context",
            _inc(state, holder="officer", route_process_check_card_delivered=True),
        )
        return

    if state.route_process_check_card_delivered and not state.route_process_check_passed:
        yield Transition(
            "process_officer_passes_route_check_after_nonempty_route",
            _inc(state, holder="controller", route_process_check_passed=True),
        )
        return

    if not state.stop_requested:
        yield Transition("user_stop_requested", _inc(state, holder="controller", stop_requested=True))
        return

    if not state.current_status_stopped:
        yield Transition(
            "run_lifecycle_reconciled_all_authorities",
            _inc(
                state,
                current_status_stopped=True,
                continuation_heartbeat_active=False,
                crew_live_agents_active=False,
                packet_loop_active=False,
                frontier_terminal=True,
                terminal_snapshot_published=True,
                terminal_snapshot_flags_consistent=True,
                terminal_continuation_cleanup_recorded=True,
                terminal_host_automation_cleanup_proven=True,
            ),
        )
        return

    if not state.snapshot_published_as_active:
        yield Transition(
            "route_state_snapshot_refreshed_after_lifecycle_change",
            _inc(
                state,
                snapshot_published_as_active=True,
                snapshot_fresh_against_frontier_and_ledger=True,
            ),
        )
        return

    yield Transition("control_plane_flow_complete", replace(state, status="complete"))


def research_scope_preserved(state: State, trace) -> InvariantResult:
    del trace
    if state.worker_packet_written and not (
        state.research_package_has_decision_question
        and state.research_package_has_allowed_sources
        and state.research_package_has_stop_conditions
        and state.worker_packet_preserves_research_fields
    ):
        return InvariantResult.fail(
            "worker research packet was materialized after PM package scope fields were dropped"
        )
    return InvariantResult.pass_()


def reviewer_report_requires_open_receipts(state: State, trace) -> InvariantResult:
    del trace
    if state.reviewer_report_accepted and not (
        state.packet_delivered
        and state.packet_body_open_receipt
        and state.result_returned
        and state.result_routed_to_reviewer
        and state.result_body_open_receipt
    ):
        return InvariantResult.fail(
            "reviewer report was accepted before delivery, packet-open, result-return, relay, and result-open receipts existed"
        )
    return InvariantResult.pass_()


def missing_receipt_uses_same_role_reissue(state: State, trace) -> InvariantResult:
    del trace
    if state.receipt_missing_blocker and not (
        state.control_blocker_lane == "control_plane_reissue"
        and state.control_blocker_target_role == "human_like_reviewer"
    ):
        return InvariantResult.fail(
            "missing receipt blocker was not routed as same-role reviewer control-plane reissue"
        )
    return InvariantResult.pass_()


def stopped_run_reconciles_authorities(state: State, trace) -> InvariantResult:
    del trace
    if state.current_status_stopped and (
        state.continuation_heartbeat_active
        or state.crew_live_agents_active
        or state.packet_loop_active
        or not state.frontier_terminal
    ):
        return InvariantResult.fail(
            "stopped run left heartbeat, crew, packet loop, or frontier authority active"
        )
    return InvariantResult.pass_()


def active_snapshot_is_fresh(state: State, trace) -> InvariantResult:
    del trace
    if state.snapshot_published_as_active and not state.snapshot_fresh_against_frontier_and_ledger:
        return InvariantResult.fail("active route_state_snapshot is stale against frontier or packet ledger")
    return InvariantResult.pass_()


def product_architecture_delivery_requires_material_context(state: State, trace) -> InvariantResult:
    del trace
    if state.product_architecture_card_delivered and not (
        state.pm_material_understanding_written
        and state.pm_material_understanding_source_available
        and state.product_architecture_delivery_has_material_context
    ):
        return InvariantResult.fail(
            "product architecture card was delivered without PM material-understanding source paths"
        )
    return InvariantResult.pass_()


def protocol_blockers_are_router_visible(state: State, trace) -> InvariantResult:
    del trace
    if state.protocol_blocker_file_written and not state.protocol_blocker_registered_in_router_state:
        return InvariantResult.fail("protocol blocker file existed without router-visible blocker registration")
    return InvariantResult.pass_()


def control_blocker_indexes_match_artifacts(state: State, trace) -> InvariantResult:
    del trace
    if state.control_blocker_artifact_status_written and not state.control_blocker_router_index_matches_artifact:
        return InvariantResult.fail("router control blocker index disagreed with control blocker artifact status")
    return InvariantResult.pass_()


def pm_repair_followup_events_are_matchable(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.control_blocker_lane == "pm_repair_decision_required"
        and state.pm_repair_decision_recorded
        and (
            not state.control_blocker_followup_event_matchable
            or not state.control_resolution_predicate_normalized
        )
    ):
        return InvariantResult.fail(
            "PM repair follow-up event could not be matched by normalized router resolution logic"
        )
    return InvariantResult.pass_()


def delivered_cards_include_required_phase_sources(state: State, trace) -> InvariantResult:
    del trace
    if state.phase_dependency_cards_delivered and not state.phase_required_sources_complete:
        return InvariantResult.fail("delivered phase card was missing required upstream source paths")
    return InvariantResult.pass_()


def delivered_card_phase_context_is_fresh(state: State, trace) -> InvariantResult:
    del trace
    if state.phase_dependency_cards_delivered and not state.delivered_card_phase_context_fresh:
        return InvariantResult.fail("delivered card current_phase did not match its actual workflow phase")
    return InvariantResult.pass_()


def terminal_snapshot_flags_match_terminal_state(state: State, trace) -> InvariantResult:
    del trace
    if state.terminal_snapshot_published and not state.terminal_snapshot_flags_consistent:
        return InvariantResult.fail("terminal route_state_snapshot flags disagreed with terminal run status")
    return InvariantResult.pass_()


def child_skill_gate_manifest_syncs_review_status(state: State, trace) -> InvariantResult:
    del trace
    if state.child_skill_gate_review_recorded and not state.child_skill_gate_manifest_synced_with_review:
        return InvariantResult.fail("child-skill gate manifest did not sync reviewer pass status")
    return InvariantResult.pass_()


def terminal_continuation_cleanup_is_proven(state: State, trace) -> InvariantResult:
    del trace
    if state.terminal_continuation_cleanup_recorded and not state.terminal_host_automation_cleanup_proven:
        return InvariantResult.fail("terminal continuation cleanup lacked host automation proof")
    return InvariantResult.pass_()


def role_output_hashes_are_replayable(state: State, trace) -> InvariantResult:
    del trace
    if state.role_output_envelopes_recorded and not state.role_output_hashes_replayable:
        return InvariantResult.fail("persisted role-output envelope hashes were not replayable against body paths")
    return InvariantResult.pass_()


def frontier_tracks_product_architecture_delivery(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.product_architecture_card_delivered
        and state.stage_advanced_after_material_scan
        and not state.frontier_fresh_after_stage_advance
    ):
        return InvariantResult.fail("execution frontier remained at material_scan after product architecture delivery")
    return InvariantResult.pass_()


def display_surfaces_track_product_architecture_delivery(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.product_architecture_card_delivered
        and state.product_stage_view_published
        and not state.product_stage_view_fresh
    ):
        return InvariantResult.fail("route snapshot or display plan remained stale after product architecture delivery")
    return InvariantResult.pass_()


def route_checks_require_nonempty_route_nodes(state: State, trace) -> InvariantResult:
    del trace
    if state.route_process_check_card_delivered and not state.route_draft_has_nodes:
        return InvariantResult.fail("route process check was delivered for an empty route draft")
    if state.route_process_check_card_delivered and (
        not state.route_draft_single_canonical_source or state.route_draft_shadow_source_used
    ):
        return InvariantResult.fail(
            "route process check used a shadow route draft instead of the canonical route source"
        )
    return InvariantResult.pass_()


def route_draft_repair_resets_stale_route_checks(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.route_draft_repaired_after_check
        and not state.route_review_flags_reset_after_draft_repair
        and (state.route_process_check_card_delivered or state.route_process_check_passed)
    ):
        return InvariantResult.fail("route draft repair left stale route-check flags active")
    return InvariantResult.pass_()


def multi_active_requires_explicit_authority(state: State, trace) -> InvariantResult:
    del trace
    if state.multiple_running_index_entries_visible and state.active_task_authority == "current_json_only":
        return InvariantResult.fail("multiple active UI tasks were exposed under current_json_only authority")
    return InvariantResult.pass_()


def controller_boundary_survives_optimization(state: State, trace) -> InvariantResult:
    del trace
    if state.controller_read_sealed_body:
        return InvariantResult.fail("Controller read sealed packet/result body")
    if state.optimized_relay_transaction and not (
        state.optimized_transaction_records_delivery
        and state.optimized_transaction_records_open_receipts
        and state.optimized_transaction_records_result_return
        and state.role_identity_checked
        and state.hash_verified
    ):
        return InvariantResult.fail(
            "optimized relay transaction skipped delivery, receipt, result-return, role, or hash evidence"
        )
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="research_scope_preserved",
        description="Research package scope fields survive capability decision and worker packet materialization.",
        predicate=research_scope_preserved,
    ),
    Invariant(
        name="reviewer_report_requires_open_receipts",
        description="Reviewer report acceptance requires legal packet/result receipts.",
        predicate=reviewer_report_requires_open_receipts,
    ),
    Invariant(
        name="missing_receipt_uses_same_role_reissue",
        description="Mechanical missing-receipt blockers route to same-role reissue, not PM repair.",
        predicate=missing_receipt_uses_same_role_reissue,
    ),
    Invariant(
        name="stopped_run_reconciles_authorities",
        description="A user-stopped run turns off heartbeat, crew, packet loop, and frontier authorities.",
        predicate=stopped_run_reconciles_authorities,
    ),
    Invariant(
        name="active_snapshot_is_fresh",
        description="User-visible active snapshots are fresh against frontier and packet ledger.",
        predicate=active_snapshot_is_fresh,
    ),
    Invariant(
        name="product_architecture_delivery_requires_material_context",
        description="Product architecture delivery includes canonical PM material-understanding source paths.",
        predicate=product_architecture_delivery_requires_material_context,
    ),
    Invariant(
        name="protocol_blockers_are_router_visible",
        description="Protocol blocker files are registered in router-visible blocker state.",
        predicate=protocol_blockers_are_router_visible,
    ),
    Invariant(
        name="control_blocker_indexes_match_artifacts",
        description="Router control-blocker summaries match the durable blocker artifact status.",
        predicate=control_blocker_indexes_match_artifacts,
    ),
    Invariant(
        name="pm_repair_followup_events_are_matchable",
        description="PM repair decisions store follow-up resolution events in a router-matchable form.",
        predicate=pm_repair_followup_events_are_matchable,
    ),
    Invariant(
        name="delivered_cards_include_required_phase_sources",
        description="Every delivered phase card carries required upstream source paths for its workflow phase.",
        predicate=delivered_cards_include_required_phase_sources,
    ),
    Invariant(
        name="delivered_card_phase_context_is_fresh",
        description="Delivered card current_phase matches the actual card workflow phase.",
        predicate=delivered_card_phase_context_is_fresh,
    ),
    Invariant(
        name="terminal_snapshot_flags_match_terminal_state",
        description="Terminal route_state_snapshot flags agree with terminal run status.",
        predicate=terminal_snapshot_flags_match_terminal_state,
    ),
    Invariant(
        name="child_skill_gate_manifest_syncs_review_status",
        description="Child-skill gate manifest approval state agrees with accepted reviewer reports.",
        predicate=child_skill_gate_manifest_syncs_review_status,
    ),
    Invariant(
        name="terminal_continuation_cleanup_is_proven",
        description="Terminal continuation cleanup has durable host automation proof.",
        predicate=terminal_continuation_cleanup_is_proven,
    ),
    Invariant(
        name="role_output_hashes_are_replayable",
        description="Persisted role-output envelopes can be replayed by hashing their body paths.",
        predicate=role_output_hashes_are_replayable,
    ),
    Invariant(
        name="frontier_tracks_product_architecture_delivery",
        description="Execution frontier moves forward when product architecture is delivered.",
        predicate=frontier_tracks_product_architecture_delivery,
    ),
    Invariant(
        name="display_surfaces_track_product_architecture_delivery",
        description="Route snapshot and display plan refresh after product architecture delivery.",
        predicate=display_surfaces_track_product_architecture_delivery,
    ),
    Invariant(
        name="route_checks_require_nonempty_route_nodes",
        description="Route process checks cannot be delivered for empty route drafts.",
        predicate=route_checks_require_nonempty_route_nodes,
    ),
    Invariant(
        name="route_draft_repair_resets_stale_route_checks",
        description="A repeated route draft before activation resets downstream route-check flags.",
        predicate=route_draft_repair_resets_stale_route_checks,
    ),
    Invariant(
        name="multi_active_requires_explicit_authority",
        description="Multiple active UI tasks require explicit active-set authority.",
        predicate=multi_active_requires_explicit_authority,
    ),
    Invariant(
        name="controller_boundary_survives_optimization",
        description="Handoff optimization cannot weaken Controller's envelope-only, role, or hash guarantees.",
        predicate=controller_boundary_survives_optimization,
    ),
)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(str(result.message))
    return failures


def _safe_base(**changes: object) -> State:
    return replace(
        State(
            status="running",
            controller_boundary_confirmed=True,
            mode="expanded",
            pm_research_package_written=True,
            research_package_has_decision_question=True,
            research_package_has_allowed_sources=True,
            research_package_has_stop_conditions=True,
            research_capability_decision_recorded=True,
            worker_packet_written=True,
            worker_packet_preserves_research_fields=True,
            packet_delivered=True,
            packet_body_open_receipt=True,
            result_returned=True,
            result_routed_to_reviewer=True,
            result_body_open_receipt=True,
            reviewer_report_written=True,
            reviewer_report_accepted=True,
            pm_material_understanding_written=True,
            pm_material_understanding_source_available=True,
            product_architecture_card_delivered=True,
            product_architecture_delivery_has_material_context=True,
            protocol_blocker_file_written=False,
            protocol_blocker_registered_in_router_state=False,
            control_blocker_artifact_status_written=False,
            control_blocker_router_index_matches_artifact=True,
            pm_repair_decision_recorded=False,
            control_blocker_followup_event_matchable=True,
            control_resolution_predicate_normalized=True,
            phase_dependency_cards_delivered=True,
            phase_required_sources_complete=True,
            delivered_card_phase_context_fresh=True,
            terminal_snapshot_published=False,
            terminal_snapshot_flags_consistent=True,
            child_skill_gate_review_recorded=False,
            child_skill_gate_manifest_synced_with_review=True,
            terminal_continuation_cleanup_recorded=False,
            terminal_host_automation_cleanup_proven=True,
            role_output_envelopes_recorded=False,
            role_output_hashes_replayable=True,
            stage_advanced_after_material_scan=True,
            frontier_fresh_after_stage_advance=True,
            product_stage_view_published=True,
            product_stage_view_fresh=True,
            route_draft_written=True,
            route_draft_has_nodes=True,
            route_draft_single_canonical_source=True,
            route_draft_shadow_source_used=False,
            route_process_check_card_delivered=True,
            route_process_check_passed=True,
            route_draft_repaired_after_check=False,
            route_review_flags_reset_after_draft_repair=True,
            role_identity_checked=True,
            hash_verified=True,
        ),
        **changes,
    )


def hazard_states() -> dict[str, State]:
    return {
        "research_package_scope_dropped": _safe_base(worker_packet_preserves_research_fields=False),
        "reviewer_report_without_result_open_receipt": _safe_base(result_body_open_receipt=False),
        "missing_receipt_blocker_escalated_to_pm": _safe_base(
            receipt_missing_blocker=True,
            control_blocker_lane="pm_repair_decision_required",
            control_blocker_target_role="project_manager",
        ),
        "stopped_run_with_active_heartbeat": _safe_base(
            current_status_stopped=True,
            continuation_heartbeat_active=True,
            frontier_terminal=True,
        ),
        "stopped_run_with_active_packet_loop": _safe_base(
            current_status_stopped=True,
            packet_loop_active=True,
            frontier_terminal=True,
        ),
        "stopped_run_without_terminal_frontier": _safe_base(
            current_status_stopped=True,
            frontier_terminal=False,
        ),
        "stale_snapshot_published_as_active": _safe_base(
            snapshot_published_as_active=True,
            snapshot_fresh_against_frontier_and_ledger=False,
        ),
        "product_architecture_delivery_missing_material_context": _safe_base(
            product_architecture_delivery_has_material_context=False,
        ),
        "protocol_blocker_file_unregistered": _safe_base(
            protocol_blocker_file_written=True,
            protocol_blocker_registered_in_router_state=False,
        ),
        "control_blocker_index_stale_after_artifact_update": _safe_base(
            control_blocker_artifact_status_written=True,
            control_blocker_router_index_matches_artifact=False,
        ),
        "pm_repair_followup_event_unmatchable": _safe_base(
            control_blocker_lane="pm_repair_decision_required",
            control_blocker_target_role="project_manager",
            pm_repair_decision_recorded=True,
            control_blocker_followup_event_matchable=False,
        ),
        "pm_repair_followup_event_not_normalized": _safe_base(
            control_blocker_lane="pm_repair_decision_required",
            control_blocker_target_role="project_manager",
            pm_repair_decision_recorded=True,
            control_blocker_followup_event_matchable=True,
            control_resolution_predicate_normalized=False,
        ),
        "phase_card_missing_required_upstream_source": _safe_base(
            phase_dependency_cards_delivered=True,
            phase_required_sources_complete=False,
        ),
        "delivered_card_phase_context_stale": _safe_base(
            phase_dependency_cards_delivered=True,
            delivered_card_phase_context_fresh=False,
        ),
        "terminal_snapshot_flag_mismatch": _safe_base(
            terminal_snapshot_published=True,
            terminal_snapshot_flags_consistent=False,
        ),
        "child_skill_gate_manifest_review_unsynced": _safe_base(
            child_skill_gate_review_recorded=True,
            child_skill_gate_manifest_synced_with_review=False,
        ),
        "terminal_heartbeat_cleanup_unproven": _safe_base(
            terminal_continuation_cleanup_recorded=True,
            terminal_host_automation_cleanup_proven=False,
        ),
        "role_output_hash_replay_mismatch": _safe_base(
            role_output_envelopes_recorded=True,
            role_output_hashes_replayable=False,
        ),
        "frontier_stale_after_product_architecture_delivery": _safe_base(
            frontier_fresh_after_stage_advance=False,
        ),
        "display_view_stale_after_product_architecture_delivery": _safe_base(
            product_stage_view_fresh=False,
        ),
        "route_process_check_on_empty_route_draft": _safe_base(
            route_draft_has_nodes=False,
            route_process_check_card_delivered=True,
        ),
        "route_process_check_on_shadow_route_draft": _safe_base(
            route_draft_has_nodes=True,
            route_draft_single_canonical_source=False,
            route_draft_shadow_source_used=True,
            route_process_check_card_delivered=True,
        ),
        "route_draft_repair_kept_stale_route_checks": _safe_base(
            route_draft_repaired_after_check=True,
            route_review_flags_reset_after_draft_repair=False,
            route_process_check_card_delivered=True,
            route_process_check_passed=True,
        ),
        "multiple_active_tasks_under_current_json_only": _safe_base(
            multiple_running_index_entries_visible=True,
            active_task_authority="current_json_only",
        ),
        "optimized_transaction_without_hash_check": _safe_base(
            mode="optimized",
            optimized_relay_transaction=True,
            optimized_transaction_records_delivery=True,
            optimized_transaction_records_open_receipts=True,
            optimized_transaction_records_result_return=True,
            hash_verified=False,
        ),
        "controller_reads_sealed_body": _safe_base(controller_read_sealed_body=True),
    }


def _read_json(path: Path) -> tuple[Any, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, f"missing file: {path.as_posix()}"
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON in {path.as_posix()}: {exc}"


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _latest_delivery(deliveries: object, card_id: str) -> dict[str, Any] | None:
    if not isinstance(deliveries, list):
        return None
    matches = [item for item in deliveries if isinstance(item, dict) and item.get("card_id") == card_id]
    if not matches:
        return None
    return max(matches, key=lambda item: _parse_time(item.get("delivered_at")) or datetime.min.replace(tzinfo=timezone.utc))


def _delivery_source_values(delivery: dict[str, Any] | None) -> set[str]:
    if not isinstance(delivery, dict):
        return set()
    source_paths = delivery.get("delivery_context", {}).get("source_paths", {})
    if isinstance(source_paths, dict):
        values = source_paths.values()
    elif isinstance(source_paths, list):
        values = source_paths
    else:
        values = ()
    return {str(value).replace("\\", "/") for value in values if isinstance(value, str)}


def _router_flags(router_state: object) -> dict[str, Any]:
    if not isinstance(router_state, dict):
        return {}
    flags = router_state.get("state_flags")
    if isinstance(flags, dict):
        return flags
    flags = router_state.get("flags")
    if isinstance(flags, dict):
        return flags
    return {}


def _json_contains(data: object, needle: str) -> bool:
    if not needle:
        return False
    return needle.replace("\\", "/") in json.dumps(data, ensure_ascii=False, sort_keys=True).replace("\\", "/")


def _add_finding(
    findings: list[dict[str, object]],
    *,
    code: str,
    severity: str,
    summary: str,
    invariant: str,
    evidence: dict[str, object],
) -> None:
    findings.append(
        {
            "code": code,
            "severity": severity,
            "summary": summary,
            "matched_invariant": invariant,
            "evidence": evidence,
        }
    )


def _router_control_blocker_status_matches(router_state: object, project_root: Path) -> tuple[bool, list[dict[str, object]]]:
    if not isinstance(router_state, dict):
        return True, []
    mismatches: list[dict[str, object]] = []
    for entry in router_state.get("control_blockers", []):
        if not isinstance(entry, dict):
            continue
        rel_path = entry.get("blocker_artifact_path")
        if not isinstance(rel_path, str):
            continue
        artifact, error = _read_json(project_root / rel_path)
        if error or not isinstance(artifact, dict):
            continue
        artifact_status = artifact.get("delivery_status")
        router_status = entry.get("delivery_status")
        artifact_resolution = artifact.get("resolution_status")
        router_resolution = entry.get("resolution_status")
        if artifact_status != router_status or artifact_resolution != router_resolution:
            mismatches.append(
                {
                    "blocker_id": entry.get("blocker_id"),
                    "path": rel_path,
                    "router_delivery_status": router_status,
                    "artifact_delivery_status": artifact_status,
                    "router_resolution_status": router_resolution,
                    "artifact_resolution_status": artifact_resolution,
                }
            )
    return not mismatches, mismatches


def _resolution_event_name(value: object) -> str | None:
    if isinstance(value, dict):
        for key in ("event", "corrected_followup_event", "event_name"):
            name = str(value.get(key) or "").strip()
            if name:
                return name
        return None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    parsed: object
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            parsed = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            return text
    return _resolution_event_name(parsed) or text


def _active_pm_repair_followup_event_matchable(router_state: object) -> tuple[bool, bool, dict[str, object]]:
    if not isinstance(router_state, dict):
        return False, True, {}
    active = router_state.get("active_control_blocker")
    if not isinstance(active, dict):
        return False, True, {}
    recorded = (
        active.get("handling_lane") == "pm_repair_decision_required"
        and active.get("pm_repair_decision_status") == "recorded"
    )
    if not recorded:
        return False, True, {}
    raw_events = active.get("allowed_resolution_events")
    allowed_names: list[str] = []
    if isinstance(raw_events, list):
        allowed_names = [name for item in raw_events if (name := _resolution_event_name(item))]
    rerun_target_name = _resolution_event_name(active.get("pm_repair_rerun_target"))
    originating_event = _resolution_event_name(active.get("originating_event"))
    expected_names = {name for name in (rerun_target_name, originating_event) if name}
    matchable = bool(allowed_names) and (not expected_names or bool(set(allowed_names) & expected_names))
    return recorded, matchable, {
        "blocker_id": active.get("blocker_id"),
        "allowed_resolution_events": raw_events,
        "allowed_event_names_after_normalization": allowed_names,
        "pm_repair_rerun_target_name_after_normalization": rerun_target_name,
        "originating_event": originating_event,
    }


def _required_card_source_rules(run_id: str) -> dict[str, tuple[str, ...]]:
    run_prefix = f".flowpilot/runs/{run_id}"
    return {
        "pm.product_architecture": (
            f"{run_prefix}/pm_material_understanding.json",
            f"{run_prefix}/material/pm_material_understanding_payload.json",
        ),
        "product_officer.product_architecture_modelability": (
            f"{run_prefix}/product_function_architecture.json",
        ),
        "reviewer.product_architecture_challenge": (
            f"{run_prefix}/product_function_architecture.json",
            f"{run_prefix}/flowguard/product_architecture_modelability.json",
        ),
        "pm.root_contract": (
            f"{run_prefix}/product_function_architecture.json",
            f"{run_prefix}/reviews/product_architecture_challenge.json",
            f"{run_prefix}/flowguard/product_architecture_modelability.json",
        ),
        "reviewer.root_contract_challenge": (
            f"{run_prefix}/root_acceptance_contract.json",
            f"{run_prefix}/standard_scenario_pack.json",
        ),
        "product_officer.root_contract_modelability": (
            f"{run_prefix}/root_acceptance_contract.json",
            f"{run_prefix}/standard_scenario_pack.json",
        ),
        "pm.dependency_policy": (
            f"{run_prefix}/root_acceptance_contract.json",
            f"{run_prefix}/product_function_architecture.json",
        ),
        "pm.child_skill_selection": (
            f"{run_prefix}/dependency_policy.json",
            f"{run_prefix}/capabilities.json",
        ),
        "pm.child_skill_gate_manifest": (
            f"{run_prefix}/capabilities.json",
            f"{run_prefix}/pm_child_skill_selection.json",
            f"{run_prefix}/root_acceptance_contract.json",
        ),
        "reviewer.child_skill_gate_manifest_review": (
            f"{run_prefix}/child_skill_gate_manifest.json",
            f"{run_prefix}/pm_child_skill_selection.json",
            f"{run_prefix}/capabilities.json",
        ),
        "process_officer.child_skill_conformance_model": (
            f"{run_prefix}/child_skill_gate_manifest.json",
            f"{run_prefix}/reviews/child_skill_gate_manifest_review.json",
            f"{run_prefix}/pm_child_skill_selection.json",
            f"{run_prefix}/capabilities.json",
        ),
        "product_officer.child_skill_product_fit": (
            f"{run_prefix}/child_skill_gate_manifest.json",
            f"{run_prefix}/reviews/child_skill_gate_manifest_review.json",
            f"{run_prefix}/flowguard/child_skill_conformance_model.json",
            f"{run_prefix}/pm_child_skill_selection.json",
            f"{run_prefix}/capabilities.json",
            f"{run_prefix}/root_acceptance_contract.json",
        ),
        "pm.prior_path_context": (
            f"{run_prefix}/child_skill_gate_manifest.json",
            f"{run_prefix}/child_skill_manifest_pm_approval.json",
            f"{run_prefix}/capabilities/capability_sync.json",
        ),
        "pm.route_skeleton": (
            f"{run_prefix}/root_acceptance_contract.json",
            f"{run_prefix}/child_skill_gate_manifest.json",
            f"{run_prefix}/child_skill_manifest_pm_approval.json",
            f"{run_prefix}/capabilities/capability_sync.json",
            f"{run_prefix}/route_memory/pm_prior_path_context.json",
        ),
        "process_officer.route_process_check": (
            f"{run_prefix}/root_acceptance_contract.json",
            f"{run_prefix}/child_skill_gate_manifest.json",
            f"{run_prefix}/capabilities/capability_sync.json",
            f"{run_prefix}/routes/route-001/flow.draft.json",
        ),
        "product_officer.route_product_check": (
            f"{run_prefix}/root_acceptance_contract.json",
            f"{run_prefix}/child_skill_gate_manifest.json",
            f"{run_prefix}/flowguard/route_process_check.json",
            f"{run_prefix}/routes/route-001/flow.draft.json",
        ),
        "reviewer.route_challenge": (
            f"{run_prefix}/root_acceptance_contract.json",
            f"{run_prefix}/child_skill_gate_manifest.json",
            f"{run_prefix}/flowguard/route_process_check.json",
            f"{run_prefix}/flowguard/route_product_check.json",
            f"{run_prefix}/routes/route-001/flow.draft.json",
        ),
    }


def _expected_card_phases() -> dict[str, str]:
    return {
        "pm.product_architecture": "product_architecture",
        "product_officer.product_architecture_modelability": "product_architecture",
        "reviewer.product_architecture_challenge": "product_architecture",
        "pm.root_contract": "root_contract",
        "reviewer.root_contract_challenge": "root_contract",
        "product_officer.root_contract_modelability": "root_contract",
        "pm.dependency_policy": "dependency_policy",
        "pm.child_skill_selection": "child_skill_selection",
        "pm.child_skill_gate_manifest": "child_skill_gate_manifest",
        "reviewer.child_skill_gate_manifest_review": "child_skill_gate_manifest",
        "process_officer.child_skill_conformance_model": "child_skill_gate_manifest",
        "product_officer.child_skill_product_fit": "child_skill_gate_manifest",
        "pm.prior_path_context": "prior_path_context",
        "pm.route_skeleton": "route_skeleton",
        "process_officer.route_process_check": "route_skeleton",
        "product_officer.route_product_check": "route_skeleton",
        "reviewer.route_challenge": "route_skeleton",
    }


def _audit_card_delivery_context(
    *,
    prompt_deliveries: object,
    run_id: str,
    project_root: Path,
) -> tuple[list[dict[str, object]], list[dict[str, object]], bool]:
    missing_sources: list[dict[str, object]] = []
    stale_phases: list[dict[str, object]] = []
    delivered_any = False
    required_sources = _required_card_source_rules(run_id)
    expected_phases = _expected_card_phases()
    for card_id, required_paths in required_sources.items():
        delivery = _latest_delivery(prompt_deliveries, card_id)
        if not delivery:
            continue
        delivered_any = True
        source_values = _delivery_source_values(delivery)
        missing = [path for path in required_paths if path not in source_values]
        if missing:
            missing_sources.append(
                {
                    "card_id": card_id,
                    "delivered_at": delivery.get("delivered_at"),
                    "missing_source_paths": missing,
                    "required_source_paths": list(required_paths),
                    "actual_source_paths": sorted(source_values),
                    "required_files_exist": {
                        path: (project_root / path).exists()
                        for path in required_paths
                    },
                }
            )
        expected_phase = expected_phases.get(card_id)
        actual_phase = (
            delivery.get("delivery_context", {})
            .get("current_stage", {})
            .get("current_phase")
        )
        if expected_phase and actual_phase != expected_phase:
            stale_phases.append(
                {
                    "card_id": card_id,
                    "delivered_at": delivery.get("delivered_at"),
                    "expected_phase": expected_phase,
                    "actual_phase": actual_phase,
                }
            )
    return missing_sources, stale_phases, delivered_any


def _audit_child_skill_gate_sync(run_root: Path) -> tuple[bool, dict[str, object]]:
    manifest, manifest_error = _read_json(run_root / "child_skill_gate_manifest.json")
    review, review_error = _read_json(run_root / "reviews" / "child_skill_gate_manifest_review.json")
    if manifest_error or review_error or not isinstance(manifest, dict) or not isinstance(review, dict):
        return True, {
            "manifest_error": manifest_error,
            "review_error": review_error,
        }
    approval = manifest.get("approval")
    if not isinstance(approval, dict):
        approval = {}
    review_passed = review.get("passed") is True
    manifest_reviewer_passed = approval.get("reviewer_passed") is True
    synced = (not review_passed) or manifest_reviewer_passed
    return synced, {
        "manifest_status": manifest.get("status"),
        "manifest_reviewer_passed": approval.get("reviewer_passed"),
        "review_passed": review.get("passed"),
        "manifest_path": ".flowpilot/runs/" + run_root.name + "/child_skill_gate_manifest.json",
        "review_path": ".flowpilot/runs/" + run_root.name + "/reviews/child_skill_gate_manifest_review.json",
    }


def _terminal_snapshot_flags_consistent(snapshot: object, router_state: object, current: object) -> tuple[bool, dict[str, object]]:
    if not isinstance(snapshot, dict):
        return True, {"snapshot_present": False}
    state = snapshot.get("state") if isinstance(snapshot.get("state"), dict) else {}
    flags = state.get("flags") if isinstance(state.get("flags"), dict) else {}
    router_flags = _router_flags(router_state)
    terminal_status = (
        (isinstance(current, dict) and current.get("status") == "stopped_by_user")
        or (isinstance(router_state, dict) and router_state.get("status") == "stopped_by_user")
        or state.get("status") == "stopped_by_user"
    )
    if not terminal_status:
        return True, {"terminal_status": False}
    snapshot_flag = flags.get("run_stopped_by_user")
    router_flag = router_flags.get("run_stopped_by_user")
    consistent = snapshot_flag is True and (router_flag is not False)
    return consistent, {
        "terminal_status": True,
        "snapshot_state_status": state.get("status"),
        "snapshot_flag_run_stopped_by_user": snapshot_flag,
        "router_flag_run_stopped_by_user": router_flag,
    }


def _terminal_continuation_cleanup_proven(project_root: Path, run_root: Path, current: object, router_state: object) -> tuple[bool, dict[str, object]]:
    terminal_status = (
        (isinstance(current, dict) and current.get("status") == "stopped_by_user")
        or (isinstance(router_state, dict) and router_state.get("status") == "stopped_by_user")
    )
    if not terminal_status:
        return True, {"terminal_status": False}
    binding, error = _read_json(run_root / "continuation" / "continuation_binding.json")
    if error or not isinstance(binding, dict):
        return False, {"terminal_status": True, "binding_error": error}
    automation_id = str(binding.get("host_automation_id") or "")
    automation_path = Path.home() / ".codex" / "automations" / automation_id / "automation.toml"
    cleanup_status = binding.get("host_automation_cleanup_status")
    automation_exists = automation_path.exists() if automation_id else None
    proven = (
        binding.get("heartbeat_active") is False
        and cleanup_status not in {"external_cleanup_may_be_required", "unknown", None}
    )
    if automation_id and not automation_exists and cleanup_status != "missing_verified":
        proven = False
    return proven, {
        "terminal_status": True,
        "heartbeat_active": binding.get("heartbeat_active"),
        "host_automation_id": automation_id or None,
        "host_automation_cleanup_status": cleanup_status,
        "automation_toml_exists": automation_exists,
        "checked_path": str(automation_path) if automation_id else None,
    }


def _role_output_semantic_hash(path: Path) -> str | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    body = dict(payload)
    body.pop("_role_output_envelope", None)
    return hashlib.sha256((json.dumps(body, indent=2, sort_keys=True) + "\n").encode("utf-8")).hexdigest()


def _role_output_semantic_hashes(path: Path) -> set[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return set()
    if not isinstance(payload, dict):
        return set()
    body = dict(payload)
    body.pop("_role_output_envelope", None)
    canonical_lf = json.dumps(body, indent=2, sort_keys=True) + "\n"
    variants = {canonical_lf, canonical_lf.replace("\n", "\r\n")}
    return {hashlib.sha256(variant.encode("utf-8")).hexdigest() for variant in variants}


def _audit_role_output_hashes(project_root: Path, run_root: Path) -> tuple[bool, list[dict[str, object]], int]:
    mismatches: list[dict[str, object]] = []
    envelope_count = 0
    if not run_root.exists():
        return True, mismatches, envelope_count
    for path in sorted(run_root.rglob("*.json")):
        payload, error = _read_json(path)
        if error or not isinstance(payload, dict):
            continue
        envelope = payload.get("_role_output_envelope")
        if not isinstance(envelope, dict):
            continue
        body_path = envelope.get("body_path")
        expected_hash = envelope.get("body_hash")
        if not isinstance(body_path, str) or not isinstance(expected_hash, str):
            continue
        envelope_count += 1
        resolved = project_root / body_path
        if not resolved.exists():
            mismatches.append(
                {
                    "path": path.relative_to(project_root).as_posix(),
                    "issue": "missing_body_path",
                    "body_path": body_path,
                    "declared_hash": expected_hash,
                }
            )
            continue
        actual_hash = hashlib.sha256(resolved.read_bytes()).hexdigest()
        semantic_hash = _role_output_semantic_hash(resolved)
        accepted_hashes = {actual_hash}
        accepted_hashes.update(_role_output_semantic_hashes(resolved))
        if expected_hash not in accepted_hashes:
            mismatches.append(
                {
                    "path": path.relative_to(project_root).as_posix(),
                    "issue": "body_hash_mismatch",
                    "body_path": body_path,
                    "declared_hash": expected_hash,
                    "actual_hash": actual_hash,
                    "semantic_hash": semantic_hash,
                }
            )
    return not mismatches, mismatches, envelope_count


def audit_live_run(project_root: str | Path = ".") -> dict[str, object]:
    """Project the current .flowpilot run into this model's invariants.

    This is intentionally read-only. It catches file-level control-plane
    friction that the abstract state graph alone cannot see.
    """

    root = Path(project_root)
    current_path = root / ".flowpilot" / "current.json"
    current, current_error = _read_json(current_path)
    if current_error:
        return {
            "ok": True,
            "skipped": True,
            "skip_reason": current_error,
            "findings": [],
            "projected_invariant_failures": [],
        }
    if not isinstance(current, dict):
        return {
            "ok": False,
            "skipped": False,
            "findings": [
                {
                    "code": "current_pointer_unreadable",
                    "severity": "error",
                    "summary": "current.json did not contain a JSON object",
                    "matched_invariant": "live_run_pointer_readable",
                    "evidence": {"path": current_path.as_posix()},
                }
            ],
            "projected_invariant_failures": [],
        }

    run_id = str(current.get("current_run_id") or current.get("active_run_id") or "")
    run_root_rel = str(current.get("current_run_root") or current.get("active_run_root") or "")
    run_root = root / run_root_rel
    router_state, _router_error = _read_json(run_root / "router_state.json")
    prompt_ledger, _prompt_error = _read_json(run_root / "prompt_delivery_ledger.json")
    frontier, _frontier_error = _read_json(run_root / "execution_frontier.json")
    snapshot, _snapshot_error = _read_json(run_root / "route_state_snapshot.json")
    display_plan, _display_error = _read_json(run_root / "display_plan.json")
    index, _index_error = _read_json(root / ".flowpilot" / "index.json")

    findings: list[dict[str, object]] = []
    flags = _router_flags(router_state)
    prompt_deliveries = prompt_ledger.get("deliveries") if isinstance(prompt_ledger, dict) else []
    product_delivery = _latest_delivery(prompt_deliveries, "pm.product_architecture")
    product_delivery_at = _parse_time(product_delivery.get("delivered_at")) if product_delivery else None
    required_material_paths = {
        f".flowpilot/runs/{run_id}/pm_material_understanding.json",
        f".flowpilot/runs/{run_id}/material/pm_material_understanding_payload.json",
    }
    material_source_values = _delivery_source_values(product_delivery)
    material_context_present = required_material_paths.issubset(material_source_values)
    pm_material_written = bool(
        flags.get("material_understanding_written_by_pm")
        or flags.get("pm_material_understanding_written_by_pm")
        or (run_root / "pm_material_understanding.json").exists()
    )
    pm_material_source_available = all((root / path).exists() for path in required_material_paths)
    product_architecture_delivered = bool(product_delivery or flags.get("pm_product_architecture_card_delivered"))
    product_stage_advanced = bool(
        product_architecture_delivered
        or flags.get("product_architecture_written_by_pm")
        or flags.get("product_architecture_modelability_passed")
        or flags.get("product_architecture_reviewer_passed")
    )
    phase_missing_sources, phase_stale_contexts, phase_dependency_cards_delivered = _audit_card_delivery_context(
        prompt_deliveries=prompt_deliveries,
        run_id=run_id,
        project_root=root,
    )
    route_draft_paths = sorted((run_root / "routes").glob("*/flow.draft.json"))
    route_draft_written = bool(route_draft_paths)
    route_draft_node_counts: dict[str, int] = {}
    route_draft_has_nodes = True
    for draft_path in route_draft_paths:
        draft, draft_error = _read_json(draft_path)
        rel = ".flowpilot/runs/" + run_root.name + "/" + draft_path.relative_to(run_root).as_posix()
        nodes = draft.get("nodes") if isinstance(draft, dict) else None
        node_count = len(nodes) if isinstance(nodes, list) else 0
        route_draft_node_counts[rel] = node_count
        if draft_error or node_count == 0:
            route_draft_has_nodes = False
    route_process_check_delivered = _latest_delivery(prompt_deliveries, "process_officer.route_process_check") is not None
    route_process_check_passed = bool(flags.get("process_officer_route_check_passed"))
    if route_process_check_delivered and not route_draft_has_nodes:
        _add_finding(
            findings,
            code="route_process_check_on_empty_route_draft",
            severity="error",
            summary="process_officer.route_process_check was delivered while the current route draft had no nodes",
            invariant="route_checks_require_nonempty_route_nodes",
            evidence={"route_draft_node_counts": route_draft_node_counts},
        )

    if product_architecture_delivered and pm_material_written and not material_context_present:
        _add_finding(
            findings,
            code="product_architecture_delivery_missing_material_context",
            severity="error",
            summary="pm.product_architecture was delivered without the canonical PM material-understanding paths",
            invariant="product_architecture_delivery_requires_material_context",
            evidence={
                "card_id": "pm.product_architecture",
                "delivered_at": product_delivery.get("delivered_at") if product_delivery else None,
                "required_source_paths": sorted(required_material_paths),
                "actual_source_paths": sorted(material_source_values),
                "material_files_exist": pm_material_source_available,
            },
        )

    if phase_missing_sources:
        _add_finding(
            findings,
            code="phase_card_required_source_paths_missing",
            severity="error",
            summary="delivered phase cards omitted required upstream source paths",
            invariant="delivered_cards_include_required_phase_sources",
            evidence={"cards": phase_missing_sources},
        )

    if phase_stale_contexts:
        _add_finding(
            findings,
            code="delivered_card_phase_context_stale",
            severity="error",
            summary="delivered cards carried a stale or wrong current_phase in live context",
            invariant="delivered_card_phase_context_is_fresh",
            evidence={"cards": phase_stale_contexts},
        )

    unregistered_protocol_blockers: list[dict[str, object]] = []
    if run_root.exists():
        for blocker_path in sorted((run_root / "blockers").glob("*.json")):
            blocker, error = _read_json(blocker_path)
            rel_path = blocker_path.relative_to(root).as_posix()
            blocker_key = ""
            if isinstance(blocker, dict):
                blocker_key = str(blocker.get("blocker_id") or blocker.get("blocker_type") or "")
            registered = _json_contains(router_state, rel_path) or _json_contains(router_state, blocker_path.name)
            if blocker_key:
                registered = registered or _json_contains(router_state, blocker_key)
            if error or not registered:
                unregistered_protocol_blockers.append(
                    {
                        "path": rel_path,
                        "blocker_key": blocker_key or None,
                        "read_error": error,
                    }
                )
    if unregistered_protocol_blockers:
        _add_finding(
            findings,
            code="protocol_blocker_file_unregistered",
            severity="error",
            summary="protocol blocker files exist but are not visible in router_state",
            invariant="protocol_blockers_are_router_visible",
            evidence={"blockers": unregistered_protocol_blockers},
        )

    frontier_status = ""
    frontier_updated_at = None
    if isinstance(frontier, dict):
        frontier_status = str(frontier.get("status") or frontier.get("phase") or "")
        frontier_updated_at = _parse_time(frontier.get("updated_at"))
    frontier_fresh = not product_stage_advanced or (
        frontier_status not in {"", "startup_intake", "material_scan"}
        and product_delivery_at is not None
        and frontier_updated_at is not None
        and frontier_updated_at >= product_delivery_at
    )
    if product_stage_advanced and not frontier_fresh:
        _add_finding(
            findings,
            code="frontier_stale_after_product_architecture_delivery",
            severity="error",
            summary="execution_frontier still describes an earlier phase after product architecture advanced",
            invariant="frontier_tracks_product_architecture_delivery",
            evidence={
                "frontier_status": frontier_status,
                "frontier_updated_at": frontier_updated_at.isoformat() if frontier_updated_at else None,
                "product_delivery_at": product_delivery_at.isoformat() if product_delivery_at else None,
            },
        )

    snapshot_created_at = _parse_time(snapshot.get("created_at")) if isinstance(snapshot, dict) else None
    snapshot_text = json.dumps(snapshot, ensure_ascii=False, sort_keys=True) if snapshot is not None else ""
    snapshot_fresh = not product_stage_advanced or (
        snapshot_created_at is not None
        and product_delivery_at is not None
        and snapshot_created_at >= product_delivery_at
        and '"pm_product_architecture_card_delivered": true' in snapshot_text
    )
    display_updated_at = _parse_time(display_plan.get("updated_at")) if isinstance(display_plan, dict) else None
    display_text = json.dumps(display_plan, ensure_ascii=False, sort_keys=True) if display_plan is not None else ""
    display_fresh = not product_stage_advanced or (
        display_updated_at is not None
        and product_delivery_at is not None
        and display_updated_at >= product_delivery_at
        and "Waiting for PM route" not in display_text
    )
    views_fresh = snapshot_fresh and display_fresh
    if product_stage_advanced and not views_fresh:
        _add_finding(
            findings,
            code="display_view_stale_after_product_architecture_delivery",
            severity="error",
            summary="route_state_snapshot or display_plan still shows an earlier startup/material view",
            invariant="display_surfaces_track_product_architecture_delivery",
            evidence={
                "snapshot_created_at": snapshot_created_at.isoformat() if snapshot_created_at else None,
                "display_updated_at": display_updated_at.isoformat() if display_updated_at else None,
                "product_delivery_at": product_delivery_at.isoformat() if product_delivery_at else None,
                "snapshot_mentions_product_architecture_delivered": '"pm_product_architecture_card_delivered": true'
                in snapshot_text,
                "display_still_waiting_for_pm_route": "Waiting for PM route" in display_text,
            },
        )

    control_blocker_index_synced, control_blocker_mismatches = _router_control_blocker_status_matches(
        router_state, root
    )
    if control_blocker_mismatches:
        _add_finding(
            findings,
            code="control_blocker_index_stale_after_artifact_update",
            severity="warning",
            summary="router_state control_blockers summaries disagree with the durable control-blocker files",
            invariant="control_blocker_indexes_match_artifacts",
            evidence={"mismatches": control_blocker_mismatches},
        )

    pm_repair_recorded, pm_repair_followup_matchable, pm_repair_followup_evidence = (
        _active_pm_repair_followup_event_matchable(router_state)
    )
    if pm_repair_recorded and not pm_repair_followup_matchable:
        _add_finding(
            findings,
            code="pm_repair_followup_event_unmatchable",
            severity="error",
            summary="PM repair decision recorded a follow-up event that router resolution logic cannot match",
            invariant="pm_repair_followup_events_are_matchable",
            evidence=pm_repair_followup_evidence,
        )

    child_skill_gate_synced, child_skill_gate_evidence = _audit_child_skill_gate_sync(run_root)
    child_skill_review_recorded = bool(child_skill_gate_evidence.get("review_passed") is True)
    if child_skill_review_recorded and not child_skill_gate_synced:
        _add_finding(
            findings,
            code="child_skill_gate_manifest_review_unsynced",
            severity="error",
            summary="child-skill gate reviewer pass did not update the manifest approval state",
            invariant="child_skill_gate_manifest_syncs_review_status",
            evidence=child_skill_gate_evidence,
        )

    terminal_snapshot_consistent, terminal_snapshot_evidence = _terminal_snapshot_flags_consistent(
        snapshot, router_state, current
    )
    terminal_snapshot_published = bool(terminal_snapshot_evidence.get("terminal_status"))
    if terminal_snapshot_published and not terminal_snapshot_consistent:
        _add_finding(
            findings,
            code="terminal_snapshot_flag_mismatch",
            severity="error",
            summary="terminal snapshot status and run_stopped_by_user flag disagree",
            invariant="terminal_snapshot_flags_match_terminal_state",
            evidence=terminal_snapshot_evidence,
        )

    terminal_cleanup_proven, terminal_cleanup_evidence = _terminal_continuation_cleanup_proven(
        root, run_root, current, router_state
    )
    terminal_cleanup_recorded = bool(terminal_cleanup_evidence.get("terminal_status"))
    if terminal_cleanup_recorded and not terminal_cleanup_proven:
        _add_finding(
            findings,
            code="terminal_heartbeat_cleanup_unproven",
            severity="warning",
            summary="terminal continuation cleanup lacks durable host automation proof",
            invariant="terminal_continuation_cleanup_is_proven",
            evidence=terminal_cleanup_evidence,
        )

    role_hashes_replayable, role_hash_mismatches, role_output_envelope_count = _audit_role_output_hashes(root, run_root)
    if role_hash_mismatches:
        _add_finding(
            findings,
            code="role_output_hash_replay_mismatch",
            severity="warning",
            summary="persisted role-output envelope hashes do not replay against current body paths",
            invariant="role_output_hashes_are_replayable",
            evidence={
                "mismatch_count": len(role_hash_mismatches),
                "checked_role_output_envelope_count": role_output_envelope_count,
                "samples": role_hash_mismatches[:12],
            },
        )

    stale_running_entries: list[str] = []
    if isinstance(index, dict):
        for item in index.get("runs", []):
            if isinstance(item, dict) and item.get("status") == "running" and item.get("run_id") != run_id:
                stale_running_entries.append(str(item.get("run_id")))
    if stale_running_entries:
        _add_finding(
            findings,
            code="non_current_runs_still_marked_running",
            severity="warning",
            summary="non-current index entries are still marked running and require active-authority filtering",
            invariant="multi_active_requires_explicit_authority",
            evidence={"current_run_id": run_id, "non_current_running_run_ids": stale_running_entries},
        )

    projected_state = _safe_base(
        pm_material_understanding_written=pm_material_written,
        pm_material_understanding_source_available=pm_material_source_available,
        product_architecture_card_delivered=product_architecture_delivered,
        product_architecture_delivery_has_material_context=material_context_present,
        protocol_blocker_file_written=bool(unregistered_protocol_blockers),
        protocol_blocker_registered_in_router_state=not bool(unregistered_protocol_blockers),
        control_blocker_artifact_status_written=bool(control_blocker_mismatches),
        control_blocker_router_index_matches_artifact=control_blocker_index_synced,
        pm_repair_decision_recorded=pm_repair_recorded,
        control_blocker_followup_event_matchable=pm_repair_followup_matchable,
        phase_dependency_cards_delivered=phase_dependency_cards_delivered,
        phase_required_sources_complete=not bool(phase_missing_sources),
        delivered_card_phase_context_fresh=not bool(phase_stale_contexts),
        terminal_snapshot_published=terminal_snapshot_published,
        terminal_snapshot_flags_consistent=terminal_snapshot_consistent,
        child_skill_gate_review_recorded=child_skill_review_recorded,
        child_skill_gate_manifest_synced_with_review=child_skill_gate_synced,
        terminal_continuation_cleanup_recorded=terminal_cleanup_recorded,
        terminal_host_automation_cleanup_proven=terminal_cleanup_proven,
        role_output_envelopes_recorded=role_output_envelope_count > 0,
        role_output_hashes_replayable=role_hashes_replayable,
        stage_advanced_after_material_scan=product_stage_advanced,
        frontier_fresh_after_stage_advance=frontier_fresh,
        product_stage_view_published=bool(snapshot is not None or display_plan is not None),
        product_stage_view_fresh=views_fresh,
        route_draft_written=route_draft_written,
        route_draft_has_nodes=route_draft_has_nodes,
        route_process_check_card_delivered=route_process_check_delivered,
        route_process_check_passed=route_process_check_passed,
        multiple_running_index_entries_visible=bool(stale_running_entries),
        active_task_authority="explicit_active_set" if stale_running_entries else "current_json_only",
    )
    projected_failures = invariant_failures(projected_state)
    error_count = sum(1 for finding in findings if finding.get("severity") == "error")
    return {
        "ok": error_count == 0,
        "skipped": False,
        "run_id": run_id,
        "run_root": run_root_rel,
        "error_count": error_count,
        "warning_count": sum(1 for finding in findings if finding.get("severity") == "warning"),
        "findings": findings,
        "projected_state": projected_state.__dict__,
        "projected_invariant_failures": projected_failures,
    }


def build_workflow() -> Workflow:
    return Workflow((ControlPlaneStep(),), name="flowpilot_control_plane_friction")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status == "complete"


def is_success(state: State) -> bool:
    return state.status == "complete"


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 32


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "Action",
    "State",
    "Tick",
    "Transition",
    "audit_live_run",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "next_states",
]
