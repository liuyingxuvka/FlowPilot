"""FlowGuard model for the FlowPilot current-node router packet loop.

Risk intent brief:
- Prevent Controller from turning packet relay into route authority.
- Protect sealed packet/result bodies and project evidence from Controller
  reads or authorship.
- Model-critical durable state: PM route activation, current-node packet
  registration, PM high-standard gate, router direct dispatch, worker
  dispatch, active-holder packet lease, fast-lane mechanical retry/result
  submission, Controller next-action notice, PM result disposition, formal
  reviewer gate release, reviewer pass/block, route mutation, stale
  evidence/frontier marking, node completion, final route-wide ledger
  source-of-truth generation, same-scope replay, generated-resource and visual
  evidence closure, and segmented final backward replay.
- Adversarial branches include packet registration before route activation,
  worker dispatch before router direct dispatch, reviewer pass before PM
  disposition and formal gate release, result relay before packet-ledger checks,
  reviewer result-review card before PM gate release, FlowGuard operator packet relay without a FlowGuard operator card, repair/recheck
  bypasses around the reviewer,
  router wait events that are impossible under the active node kind, parent
  repair lanes that target leaf/current-node worker dispatch, collapsed repair
  outcome tables that map success/blocker/protocol-blocker to one
  business-validated event,
  route mutation without reviewer block or stale markers, PM completion before
  reviewer pass, final ledger without a current route scan/zero unresolved
  items/source-of-truth file, stale/unresolved evidence, pending generated
  resources, missing screenshots for UI/visual work, old assets reused as
  current evidence, final replay without a clean ledger or segment decisions,
  Controller body reads, and Controller-origin project evidence.
- Hard invariants: current-node packets require active route and fresh frontier;
  controller-only mode fail-closes to PM when no legal next action exists;
  expected PM/reviewer role-event waits must not be materialized as
  no-next-action blockers;
  current-node packets gate write grants; router direct dispatch gates worker work;
  worker and FlowGuard operator results are
  packet-ledger checked before PM relay; PM dispositions worker results before
  formal reviewer gate packages; active-holder fast-lane
  closure writes a Controller-visible next-action notice before cross-role relay; repair/recheck returns to the
  reviewer before PM completion; reviewer result decisions require the
  formal PM gate package and result-review system card; mutation requires reviewer block and stale
  evidence/frontier markers; same-scope replay reruns after mutation;
  PM node completion updates the durable completion ledger before parent replay
  or task completion projection;
  evidence/quality package and reviewer evidence quality pass precede final
  ledger source-of-truth generation; final ledger and segmented replay are
  ordered terminal gates; Controller remains envelope-only.
- Blindspot: this is an abstract control-plane model, not a replay adapter for
  the concrete router implementation.
"""


from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple






MAX_ROUTE_MUTATIONS = 1
NODE_KINDS = {"leaf", "parent", "module", "repair"}
PARENT_NODE_KINDS = {"parent", "module"}
LEAF_CURRENT_NODE_EVENTS = {
    "pm_registers_current_node_packet",
    "reviewer_allows_current_node_dispatch",
    "worker_current_node_result_returned",
    "reviewer_current_node_result_decision",
    "pm_completes_current_node",
}
PARENT_REPAIR_SAFE_EVENTS = {
    "pm_enters_child_subtree",
    "pm_records_parent_protocol_blocker",
    "pm_records_parent_segment_decision",
    "pm_completes_parent_node",
    "reviewer_parent_backward_replay",
}
BUSINESS_VALIDATED_REPAIR_EVENTS = LEAF_CURRENT_NODE_EVENTS | {
    "pm_completes_parent_node",
    "pm_records_parent_segment_decision",
}
EVENT_NODE_KIND_COMPATIBILITY = {
    event: {"leaf", "repair"}
    for event in LEAF_CURRENT_NODE_EVENTS
}
EVENT_NODE_KIND_COMPATIBILITY.update(
    {
        "pm_enters_child_subtree": PARENT_NODE_KINDS,
        "pm_records_parent_protocol_blocker": PARENT_NODE_KINDS,
        "pm_records_parent_segment_decision": PARENT_NODE_KINDS,
        "pm_completes_parent_node": PARENT_NODE_KINDS,
        "reviewer_parent_backward_replay": PARENT_NODE_KINDS,
    }
)


@dataclass(frozen=True)
class Tick:
    """One router/controller current-node loop tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | blocked | complete
    holder: str = "none"  # none | controller | pm | reviewer | worker | FlowGuard operator
    active_node_kind: str = "leaf"  # leaf | parent | module | repair
    route_version: int = 0

    controller_boundary_confirmed: bool = False
    controller_only_mode_active: bool = False
    no_next_action_detected: bool = False
    pm_decision_required_blocker_written: bool = False
    controller_read_sealed_body: bool = False
    controller_originated_project_evidence: bool = False
    controller_relayed_body_content: bool = False
    control_repair_origin: str = "none"  # none | parent_backward_replay | current_node_result | material_dispatch
    control_repair_wait_event: str = "none"
    repair_outcome_success_event: str = "none"
    repair_outcome_blocker_event: str = "none"
    repair_outcome_protocol_blocker_event: str = "none"

    route_activated: bool = False
    flowguard_operator_packet_card_delivered: bool = False
    flowguard_operator_packet_relayed: bool = False
    flowguard_operator_packet_identity_boundary_present: bool = False
    flowguard_operator_result_returned: bool = False
    flowguard_operator_result_identity_boundary_present: bool = False
    flowguard_operator_result_ledger_checked: bool = False
    flowguard_operator_result_routed_to_pm: bool = False
    pm_absorbed_flowguard_operator_result: bool = False
    flowguard_operator_lifecycle_flags_current: bool = False
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
    write_grant_issued: bool = False
    reviewer_dispatch_allowed: bool = False
    worker_dispatched: bool = False
    worker_project_write_performed: bool = False
    worker_packet_identity_boundary_present: bool = False
    active_holder_lease_issued: bool = False
    active_holder_contact_attempted: bool = False
    active_holder_contact_is_current_holder: bool = True
    active_holder_contact_agent_matches: bool = True
    active_holder_contact_packet_current: bool = True
    active_holder_contact_route_frontier_current: bool = True
    active_holder_contact_action_allowed: bool = True
    active_holder_ack_recorded: bool = False
    active_holder_packet_opened_through_runtime: bool = False
    active_holder_progress_recorded: bool = False
    active_holder_progress_controller_safe: bool = True
    active_holder_packet_family: str = "current_node"  # current_node | material_scan | research | pm_role_work
    generalized_packet_registered: bool = False
    generalized_packet_relayed: bool = False
    generalized_packet_identity_boundary_present: bool = True
    generalized_packet_live_holder_known: bool = True
    generalized_result_target_is_pm: bool = True
    fast_lane_initial_result_submitted: bool = False
    fast_lane_mechanical_reject_recorded: bool = False
    fast_lane_result_resubmitted: bool = False
    fast_lane_result_mechanics_passed: bool = False
    fast_lane_controller_notice_written: bool = False
    worker_result_returned: bool = False
    worker_result_identity_boundary_present: bool = False
    worker_result_ledger_checked: bool = False
    worker_result_routed_to_pm: bool = False
    pm_result_disposition_recorded: bool = False
    pm_formal_node_gate_package_released: bool = False
    worker_result_routed_to_reviewer: bool = False
    reviewer_worker_result_card_delivered: bool = False
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
    pm_node_completion_card_delivered: bool = False
    pm_node_completed: bool = False
    node_completion_ledger_updated: bool = False
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
    evidence_quality_review_card_delivered: bool = False
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
    final_backward_replay_card_delivered: bool = False
    final_backward_replay_passed: bool = False
    task_completion_projection_published: bool = False
    pm_terminal_closure_card_delivered: bool = False


class Transition(NamedTuple):
    label: str
    state: State


Condition = tuple[str, object]
ConditionGroup = tuple[Condition, ...]


@dataclass(frozen=True)
class EventContract:
    """Abstract role-event contract used to distinguish legal waits from dead ends."""

    name: str
    requires_all: ConditionGroup
    satisfied_by_any: tuple[ConditionGroup, ...]
    role: str


EXPECTED_ROLE_EVENT_CONTRACTS: tuple[EventContract, ...] = (
    EventContract(
        name="flowguard_operator_result_returned",
        role="FlowGuard operator",
        requires_all=(("flowguard_operator_packet_relayed", True),),
        satisfied_by_any=(
            (("flowguard_operator_result_returned", True),),
        ),
    ),
    EventContract(
        name="pm_absorbs_flowguard_operator_result",
        role="pm",
        requires_all=(("flowguard_operator_result_routed_to_pm", True),),
        satisfied_by_any=(
            (("pm_absorbed_flowguard_operator_result", True),),
        ),
    ),
    EventContract(
        name="pm_opens_current_node_high_standard_gate",
        role="pm",
        requires_all=(
            ("pm_absorbed_flowguard_operator_result", True),
            ("pm_prior_path_context_reviewed", True),
        ),
        satisfied_by_any=(
            (("pm_node_high_standard_gate_opened", True),),
        ),
    ),
    EventContract(
        name="pm_writes_node_acceptance_plan",
        role="pm",
        requires_all=(
            ("pm_node_high_standard_gate_opened", True),
            ("pm_prior_path_context_reviewed", True),
        ),
        satisfied_by_any=(
            (("node_acceptance_plan_written", True),),
        ),
    ),
    EventContract(
        name="reviewer_reviews_node_acceptance_plan",
        role="reviewer",
        requires_all=(("node_acceptance_plan_written", True),),
        satisfied_by_any=(
            (("reviewer_node_acceptance_plan_reviewed", True),),
        ),
    ),
    EventContract(
        name="pm_registers_current_node_packet",
        role="pm",
        requires_all=(("reviewer_node_acceptance_plan_reviewed", True),),
        satisfied_by_any=(
            (("current_node_packet_registered", True),),
        ),
    ),
    EventContract(
        name="reviewer_allows_current_node_dispatch",
        role="reviewer",
        requires_all=(
            ("current_node_packet_registered", True),
            ("write_grant_issued", True),
        ),
        satisfied_by_any=(
            (("reviewer_dispatch_allowed", True),),
        ),
    ),
    EventContract(
        name="worker_current_node_result_returned",
        role="worker",
        requires_all=(("worker_dispatched", True),),
        satisfied_by_any=(
            (("worker_result_returned", True),),
        ),
    ),
    EventContract(
        name="pm_records_current_node_result_disposition",
        role="pm",
        requires_all=(("worker_result_routed_to_pm", True),),
        satisfied_by_any=(
            (("pm_result_disposition_recorded", True),),
        ),
    ),
    EventContract(
        name="pm_releases_current_node_formal_gate",
        role="pm",
        requires_all=(("pm_result_disposition_recorded", True),),
        satisfied_by_any=(
            (("pm_formal_node_gate_package_released", True),),
        ),
    ),
    EventContract(
        name="reviewer_current_node_result_decision",
        role="reviewer",
        requires_all=(
            ("pm_formal_node_gate_package_released", True),
            ("reviewer_worker_result_card_delivered", True),
        ),
        satisfied_by_any=(
            (("reviewer_decision", "pass"),),
            (("reviewer_decision", "block"),),
        ),
    ),
    EventContract(
        name="pm_repair_or_route_mutation_decision",
        role="pm",
        requires_all=(
            ("reviewer_decision", "block"),
            ("pm_prior_path_context_reviewed", True),
        ),
        satisfied_by_any=(
            (("repair_packet_registered", True),),
            (("route_mutation_count", 1),),
        ),
    ),
    EventContract(
        name="reviewer_allows_repair_dispatch",
        role="reviewer",
        requires_all=(("repair_packet_registered", True),),
        satisfied_by_any=(
            (("repair_dispatch_allowed", True),),
        ),
    ),
    EventContract(
        name="worker_repair_result_returned",
        role="worker",
        requires_all=(("repair_worker_dispatched", True),),
        satisfied_by_any=(
            (("repair_result_returned", True),),
        ),
    ),
    EventContract(
        name="reviewer_rechecks_repair_result",
        role="reviewer",
        requires_all=(("repair_result_routed_to_reviewer", True),),
        satisfied_by_any=(
            (("repair_recheck_passed", True),),
        ),
    ),
    EventContract(
        name="pm_completes_current_node",
        role="pm",
        requires_all=(
            ("reviewer_decision", "pass"),
            ("pm_node_completion_card_delivered", True),
        ),
        satisfied_by_any=(
            (("pm_node_completed", True),),
        ),
    ),
    EventContract(
        name="pm_enumerates_parent_backward_targets",
        role="pm",
        requires_all=(("node_completion_ledger_updated", True),),
        satisfied_by_any=(
            (("parent_backward_targets_enumerated", True),),
        ),
    ),
    EventContract(
        name="reviewer_parent_backward_replay",
        role="reviewer",
        requires_all=(("parent_backward_targets_enumerated", True),),
        satisfied_by_any=(
            (("parent_backward_replay_passed", True),),
        ),
    ),
    EventContract(
        name="pm_records_parent_segment_decision",
        role="pm",
        requires_all=(
            ("parent_backward_replay_passed", True),
            ("pm_prior_path_context_reviewed", True),
        ),
        satisfied_by_any=(
            (("parent_pm_segment_decision_recorded", True),),
        ),
    ),
    EventContract(
        name="pm_completes_parent_node",
        role="pm",
        requires_all=(("parent_pm_segment_decision_recorded", True),),
        satisfied_by_any=(
            (("parent_node_completed", True),),
        ),
    ),
    EventContract(
        name="pm_writes_evidence_quality_package",
        role="pm",
        requires_all=(("pm_evidence_quality_package_card_delivered", True),),
        satisfied_by_any=(
            (("evidence_quality_package_written", True),),
        ),
    ),
    EventContract(
        name="reviewer_evidence_quality_review",
        role="reviewer",
        requires_all=(("evidence_quality_review_card_delivered", True),),
        satisfied_by_any=(
            (("evidence_quality_reviewer_passed", True),),
        ),
    ),
    EventContract(
        name="pm_generates_final_ledger_source_of_truth",
        role="pm",
        requires_all=(("pm_final_ledger_card_delivered", True),),
        satisfied_by_any=(
            (("final_ledger_source_of_truth_generated", True),),
        ),
    ),
    EventContract(
        name="pm_builds_clean_final_ledger",
        role="pm",
        requires_all=(
            ("pm_final_ledger_card_delivered", True),
            ("final_ledger_source_of_truth_generated", True),
        ),
        satisfied_by_any=(
            (("final_ledger_built", True), ("final_ledger_clean", True)),
        ),
    ),
    EventContract(
        name="reviewer_terminal_root_segment_replay",
        role="reviewer",
        requires_all=(("terminal_replay_map_generated_from_final_ledger", True),),
        satisfied_by_any=(
            (("terminal_replay_root_segment_passed", True),),
        ),
    ),
    EventContract(
        name="reviewer_terminal_parent_segment_replay",
        role="reviewer",
        requires_all=(("terminal_replay_root_segment_passed", True),),
        satisfied_by_any=(
            (("terminal_replay_parent_segment_passed", True),),
        ),
    ),
    EventContract(
        name="reviewer_terminal_leaf_segment_replay",
        role="reviewer",
        requires_all=(("terminal_replay_parent_segment_passed", True),),
        satisfied_by_any=(
            (("terminal_replay_leaf_segment_passed", True),),
        ),
    ),
    EventContract(
        name="pm_records_terminal_segment_decisions",
        role="pm",
        requires_all=(("terminal_replay_leaf_segment_passed", True),),
        satisfied_by_any=(
            (("terminal_replay_pm_segment_decisions_recorded", True),),
        ),
    ),
    EventContract(
        name="reviewer_final_backward_replay",
        role="reviewer",
        requires_all=(("final_backward_replay_card_delivered", True),),
        satisfied_by_any=(
            (("final_backward_replay_passed", True),),
        ),
    ),
    EventContract(
        name="pm_terminal_closure",
        role="pm",
        requires_all=(("pm_terminal_closure_card_delivered", True),),
        satisfied_by_any=(
            (("status", "complete"),),
        ),
    ),
)


def initial_state() -> State:
    return State()
