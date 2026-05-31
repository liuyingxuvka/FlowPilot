"""Invariant helpers for ``flowpilot_router_loop_model``."""

from __future__ import annotations

from flowguard import Invariant, InvariantResult

from flowpilot_router_loop_model_state import (
    BUSINESS_VALIDATED_REPAIR_EVENTS,
    NODE_KINDS,
    PARENT_NODE_KINDS,
    PARENT_REPAIR_SAFE_EVENTS,
    State,
)
from flowpilot_router_loop_model_transitions import (
    _event_allowed_for_node_kind,
    _repair_outcome_events,
    expected_role_event_waits,
)

def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []

    if state.active_node_kind not in NODE_KINDS:
        failures.append("active node kind is outside the modeled event unsupported_historical table")
    if state.controller_read_sealed_body:
        failures.append("Controller read a sealed packet/result body")
    if state.controller_originated_project_evidence:
        failures.append("Controller originated project evidence")
    if state.controller_relayed_body_content:
        failures.append("Controller relayed packet/result body content instead of envelope-only metadata")
    if state.no_next_action_detected and not state.pm_decision_required_blocker_written:
        failures.append("Controller detected no legal next action without writing a PM decision-required blocker")
    if state.no_next_action_detected and state.controller_originated_project_evidence:
        failures.append("Controller started project work after no-next-action instead of fail-closing to PM")
    if expected_role_event_waits(state) and (
        state.no_next_action_detected or state.pm_decision_required_blocker_written
    ):
        failures.append("expected role-event wait incorrectly wrote PM decision-required blocker")
    if (
        state.control_repair_wait_event != "none"
        and not _event_allowed_for_node_kind(state.control_repair_wait_event, state.active_node_kind)
    ):
        failures.append("router allowed event incompatible with active node kind")
    if (
        state.control_repair_origin == "parent_backward_replay"
        and state.control_repair_wait_event != "none"
        and state.control_repair_wait_event not in PARENT_REPAIR_SAFE_EVENTS
    ):
        failures.append("parent backward replay repair waited on non-parent-safe event")
    outcome_events = _repair_outcome_events(state)
    if (
        len(outcome_events) == 3
        and len(set(outcome_events)) == 1
        and outcome_events[0] in BUSINESS_VALIDATED_REPAIR_EVENTS
    ):
        failures.append("repair outcome table collapsed success blocker and protocol-blocker onto one business-validated event")
    for outcome_event in outcome_events:
        if not _event_allowed_for_node_kind(outcome_event, state.active_node_kind):
            failures.append("repair outcome event incompatible with active node kind")

    if state.route_activated and not state.controller_boundary_confirmed:
        failures.append("route activated before Controller relay boundary was confirmed")
    if state.flowguard_operator_lifecycle_flags_current and not state.route_activated:
        failures.append("FlowGuard operator lifecycle flags reconciled before route activation")
    if state.flowguard_operator_packet_card_delivered and not state.flowguard_operator_lifecycle_flags_current:
        failures.append("FlowGuard operator packet card delivered before FlowGuard operator lifecycle flags were reconciled")
    if state.flowguard_operator_packet_card_delivered and not state.route_activated:
        failures.append("FlowGuard operator packet card delivered before route activation")
    if state.flowguard_operator_packet_relayed and not state.flowguard_operator_packet_card_delivered:
        failures.append("FlowGuard operator packet relayed before FlowGuard operator card")
    if state.flowguard_operator_packet_relayed and not state.flowguard_operator_packet_identity_boundary_present:
        failures.append("FlowGuard operator packet relayed without packet recipient identity boundary")
    if state.flowguard_operator_result_returned and not state.flowguard_operator_packet_relayed:
        failures.append("FlowGuard operator result returned before FlowGuard operator packet relay")
    if state.flowguard_operator_result_returned and not state.flowguard_operator_result_identity_boundary_present:
        failures.append("FlowGuard operator result returned without completed-by identity boundary")
    if state.flowguard_operator_result_ledger_checked and not state.flowguard_operator_result_returned:
        failures.append("FlowGuard operator result ledger checked before FlowGuard operator result returned")
    if state.flowguard_operator_result_routed_to_pm and not state.flowguard_operator_result_ledger_checked:
        failures.append("FlowGuard operator result routed to PM before packet-ledger check")
    if state.pm_absorbed_flowguard_operator_result and not state.flowguard_operator_result_routed_to_pm:
        failures.append("PM absorbed FlowGuard operator result before result relay")
    if state.pm_node_high_standard_gate_opened and not (
        state.pm_absorbed_flowguard_operator_result and state.pm_node_high_standard_risks_reviewed
    ):
        failures.append("PM high-standard gate opened before FlowGuard operator result absorption and risk review")
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
    if state.current_node_packet_registered and state.active_node_kind in PARENT_NODE_KINDS:
        failures.append("current-node packet registered for parent or module node")
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
        failures.append("router direct dispatch allowed before current-node packet registration")
    if state.write_grant_issued and not state.current_node_packet_registered:
        failures.append("write grant issued before current-node packet registration")
    if state.worker_dispatched and not state.reviewer_dispatch_allowed:
        failures.append("worker dispatched before router direct dispatch")
    if state.worker_dispatched and not state.write_grant_issued:
        failures.append("worker dispatched before current-node write grant")
    if state.worker_project_write_performed and not state.write_grant_issued:
        failures.append("worker project write occurred before current-node write grant")
    if state.worker_project_write_performed and not state.active_holder_lease_issued:
        failures.append("worker project work started before active-holder lease")
    if state.worker_dispatched and not state.worker_packet_identity_boundary_present:
        failures.append("worker dispatched without packet recipient identity boundary")
    if state.active_holder_packet_family not in {"current_node", "material_scan", "research", "pm_role_work"}:
        failures.append("active-holder lease used unsupported packet family")
    if state.active_holder_lease_issued and state.active_holder_packet_family == "current_node" and not (
        state.current_node_packet_registered
        and state.write_grant_issued
        and state.reviewer_dispatch_allowed
        and state.worker_dispatched
        and state.worker_packet_identity_boundary_present
    ):
        failures.append("active-holder lease issued before current worker dispatch and write grant")
    if state.active_holder_lease_issued and state.active_holder_packet_family != "current_node" and not (
        state.generalized_packet_registered
        and state.generalized_packet_relayed
        and state.generalized_packet_identity_boundary_present
        and state.generalized_packet_live_holder_known
    ):
        failures.append(
            "generalized active-holder lease issued before packet registration, relay, identity boundary, or live holder"
        )
    if (
        state.active_holder_lease_issued
        and state.active_holder_packet_family in {"material_scan", "research", "pm_role_work"}
        and not state.generalized_result_target_is_pm
    ):
        failures.append("generalized active-holder result did not return to PM disposition path")
    if state.active_holder_contact_attempted and not state.active_holder_lease_issued:
        failures.append("active-holder contact attempted without an issued lease")
    if state.active_holder_contact_attempted and not state.active_holder_contact_is_current_holder:
        failures.append("active-holder fast lane accepted contact from a non-holder role")
    if state.active_holder_contact_attempted and not state.active_holder_contact_agent_matches:
        failures.append("active-holder fast lane accepted contact from a stale or wrong agent")
    if state.active_holder_contact_attempted and not state.active_holder_contact_packet_current:
        failures.append("active-holder fast lane accepted a stale or wrong packet")
    if state.active_holder_contact_attempted and not state.active_holder_contact_route_frontier_current:
        failures.append("active-holder fast lane accepted contact after route or frontier staleness")
    if state.active_holder_contact_attempted and not state.active_holder_contact_action_allowed:
        failures.append("active-holder fast lane accepted an action outside the lease")
    if state.active_holder_ack_recorded and not state.active_holder_contact_attempted:
        failures.append("active-holder ack recorded without a fast-lane contact attempt")
    if state.active_holder_packet_opened_through_runtime and not state.active_holder_ack_recorded:
        failures.append("active-holder packet opened through runtime before packet ack")
    if state.active_holder_progress_recorded and not state.active_holder_ack_recorded:
        failures.append("active-holder progress recorded before packet ack")
    if state.active_holder_progress_recorded and not state.active_holder_packet_opened_through_runtime:
        failures.append("active-holder progress recorded before packet body runtime open")
    if state.active_holder_progress_recorded and not state.active_holder_progress_controller_safe:
        failures.append("active-holder progress exposed sealed body, findings, evidence, or recommendations")
    if state.fast_lane_initial_result_submitted and not state.active_holder_ack_recorded:
        failures.append("active-holder result submitted before packet ack")
    if state.fast_lane_initial_result_submitted and not state.active_holder_packet_opened_through_runtime:
        failures.append("active-holder result submitted before packet body was opened through packet runtime")
    if state.fast_lane_initial_result_submitted and not state.active_holder_contact_attempted:
        failures.append("active-holder result submitted without a fast-lane contact attempt")
    if state.fast_lane_mechanical_reject_recorded and not state.fast_lane_initial_result_submitted:
        failures.append("router mechanical rejection recorded before active-holder result submission")
    if state.fast_lane_result_resubmitted and not state.fast_lane_mechanical_reject_recorded:
        failures.append("active-holder result resubmitted without prior router mechanical rejection")
    if state.fast_lane_result_mechanics_passed and not (
        state.fast_lane_initial_result_submitted
        and (
            not state.fast_lane_mechanical_reject_recorded
            or state.fast_lane_result_resubmitted
        )
    ):
        failures.append("router accepted fast-lane result mechanics before valid submit or resubmit")
    if state.worker_result_returned and not state.fast_lane_result_mechanics_passed:
        failures.append("worker result returned before active-holder mechanics pass")
    if state.worker_result_returned and not state.worker_dispatched:
        failures.append("worker result returned before worker dispatch")
    if state.worker_result_returned and not state.worker_result_identity_boundary_present:
        failures.append("worker result returned without completed-by identity boundary")
    if state.worker_result_ledger_checked and not state.worker_result_returned:
        failures.append("worker result ledger checked before result was returned")
    if state.fast_lane_controller_notice_written and not (
        state.worker_result_ledger_checked and state.fast_lane_result_mechanics_passed
    ):
        failures.append("router wrote Controller next-action notice before fast-lane mechanics and ledger check passed")
    if state.worker_result_routed_to_pm and not (
        state.worker_result_returned and state.worker_result_ledger_checked
    ):
        failures.append("worker result routed before result was returned and packet-ledger checked")
    if state.worker_result_routed_to_pm and not state.fast_lane_controller_notice_written:
        failures.append("worker result routed to PM before router wrote Controller next-action notice")
    if state.worker_result_routed_to_reviewer:
        failures.append("worker result routed directly to reviewer before PM disposition")
    if state.pm_result_disposition_recorded and not state.worker_result_routed_to_pm:
        failures.append("PM disposition recorded before worker result was routed to PM")
    if state.pm_formal_node_gate_package_released and not state.pm_result_disposition_recorded:
        failures.append("PM formal node gate package released before result disposition")
    if state.reviewer_worker_result_card_delivered and not state.pm_formal_node_gate_package_released:
        failures.append("reviewer result-review card delivered before PM formal gate package")
    if state.reviewer_decision in {"pass", "block"} and not state.pm_formal_node_gate_package_released:
        failures.append("reviewer decided before PM formal gate package release")
    if state.reviewer_decision in {"pass", "block"} and not state.reviewer_worker_result_card_delivered:
        failures.append("reviewer decided before result-review card delivery")
    if state.reviewer_decision == "pass" and not state.pm_result_disposition_recorded:
        failures.append("reviewer pass recorded before PM result disposition")
    if state.repair_packet_registered and not state.reviewer_block_seen:
        failures.append("repair packet registered before reviewer block")
    if state.repair_dispatch_allowed and not state.repair_packet_registered:
        failures.append("reviewer allowed repair dispatch before repair packet")
    if state.repair_worker_dispatched and not state.repair_dispatch_allowed:
        failures.append("repair worker dispatched before router direct repair dispatch")
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
    if state.pm_node_completion_card_delivered and state.reviewer_decision != "pass":
        failures.append("PM node completion card delivered before reviewer pass")
    if state.pm_node_completed and state.reviewer_block_seen and not (
        state.route_mutation_count or state.repair_recheck_passed
    ):
        failures.append("PM completed repaired node before reviewer recheck or route mutation")
    if state.node_completion_ledger_updated and not state.pm_node_completed:
        failures.append("node completion ledger updated before PM node completion")
    if state.parent_backward_targets_enumerated and not state.pm_node_completed:
        failures.append("parent backward targets enumerated before current node completion")
    if state.parent_backward_targets_enumerated and not state.node_completion_ledger_updated:
        failures.append("parent backward targets enumerated before node completion ledger update")
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
    if state.evidence_quality_review_card_delivered and not state.evidence_quality_package_written:
        failures.append("evidence quality review card delivered before PM evidence/quality package")
    if state.evidence_quality_reviewer_passed and not state.evidence_quality_package_written:
        failures.append("reviewer evidence quality pass recorded before PM evidence/quality package")
    if state.evidence_quality_reviewer_passed and not state.evidence_quality_review_card_delivered:
        failures.append("reviewer evidence quality pass recorded before evidence quality review card")
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
    if (
        state.final_backward_replay_card_delivered
        and not state.terminal_replay_pm_segment_decisions_recorded
    ):
        failures.append("final backward replay card delivered before terminal replay segment decisions")
    if state.final_backward_replay_passed and not state.final_backward_replay_card_delivered:
        failures.append("final backward replay passed before reviewer card delivery")
    if state.task_completion_projection_published and not (
        state.node_completion_ledger_updated and state.final_backward_replay_passed
    ):
        failures.append("task completion projection published before node completion ledger and final backward replay")
    if state.pm_terminal_closure_card_delivered and not state.task_completion_projection_published:
        failures.append("PM terminal closure card delivered before task completion projection")
    if state.status == "complete" and not state.final_backward_replay_passed:
        failures.append("completion recorded before final backward replay")
    if state.status == "complete" and not state.pm_terminal_closure_card_delivered:
        failures.append("completion recorded before PM terminal closure card")
    if state.status == "complete" and not state.task_completion_projection_published:
        failures.append("completion recorded before task completion projection was derived from completion ledger")

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
            "plan before the packet, FlowGuard operator lifecycle flags before FlowGuard operator "
            "packet relay, controller no-next-action states fail-close to PM, "
            "expected role-event waits never materialize PM blockers, "
            "current-node packets gate write grants, router direct dispatch before "
            "worker or repair work, "
            "packet-ledger checks before worker/FlowGuard operator result relay, PM result "
            "disposition before formal reviewer node-completion gates, reviewer "
            "recheck before repaired completion, reviewer-blocked route mutation "
            "with stale evidence/frontier markers, same-scope replay after "
            "mutation, node completion ledger updates before parent backward replay "
            "or task completion projection, parent backward replay plus PM segment "
            "decision before parent completion, evidence-quality review and resource closure "
            "before final ledger source of truth, and clean final ledger before "
            "segmented terminal backward replay."
        ),
        predicate=router_loop_invariant,
    ),
)
