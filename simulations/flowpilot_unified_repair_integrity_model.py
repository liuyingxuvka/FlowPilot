"""FlowGuard model for one FlowPilot repair mechanism across discovery phases.

The model deliberately separates two facts that a linear route can otherwise
conflate:

* logical placement: a repair graft is anchored beside the historical target
  in the same owning slot and points back through ``repairs_node_id``;
* execution placement: the graft is appended at the current execution
  frontier, never inserted into or used to rewrite historical execution.

Function block:
    RepairTrigger x State -> Set(Action x State)

This is a design/model-miss gate.  It does not claim that the current
FlowPilot runtime implements the modeled contract.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Iterable, Mapping

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_unified_repair_integrity"
MAX_SEQUENCE_LENGTH = 6

TRIGGER_ORIGINS = (
    "pm_historical_defect",
    "reviewer_node_failure",
    "system_postcondition_failure",
    "parent_backward_replay",
    "terminal_backward_replay",
)

SUBSTANTIVE_REPAIR_ACTIONS = (
    "repair_same_slot",
    "repair_parent_scope",
    "repair_subtree",
    "redesign_route",
)
TERMINAL_DISPOSITION_ACTIONS = (
    "authorized_waiver",
    "stop_for_user",
)
REPAIR_ACTIONS = SUBSTANTIVE_REPAIR_ACTIONS + TERMINAL_DISPOSITION_ACTIONS

DECISION_GATE_SEQUENCE = (
    "PMDecision",
    "StageEffect",
    "FlowGuardDecisionCheck",
    "PMAcceptance",
    "ReviewerDecisionReview",
    "SystemValidation",
    "CommitEffect",
    "OpenWorker",
)
POST_WORK_ROLE_SEQUENCE = ("Worker", "FlowGuard", "Reviewer")
SUBSTANTIVE_STAGE_NAMES = (
    "triggered",
    "decision_staged",
    "decision_gate_accepted",
    "effect_committed_and_worker_open",
    "post_work_checked",
    "complete",
)
TERMINAL_STAGE_NAMES = (
    "terminal_disposition_selected",
    "complete",
)
REJECTED_GATE_STATUS = "decision_gate_rejected_disposed"
REJECTED_GATE_EXIT_OPTIONS = (
    "pm_revise",
    "authorized_waiver",
    "stop_for_user",
    "retry",
)

# This is an explicit refinement comparison, not a claim of runtime parity.
# Missing or semantically narrower runtime actions remain visible conformance
# gaps in the runner instead of being silently treated as aliases.
ACTION_REFINEMENT_MAP: Mapping[str, Mapping[str, str | None]] = {
    "repair_same_slot": {
        "runtime_action": "repair_current_scope",
        "status": "explicit_name_refinement",
    },
    "repair_parent_scope": {
        "runtime_action": "repair_parent_scope",
        "status": "exact_name_candidate",
    },
    "repair_subtree": {
        "runtime_action": None,
        "status": "runtime_action_absent",
    },
    "redesign_route": {
        "runtime_action": "redesign_route",
        "status": "exact_name_candidate",
    },
    "authorized_waiver": {
        "runtime_action": "waive_with_authority",
        "status": "semantic_refinement_unverified",
    },
    "stop_for_user": {
        "runtime_action": "stop_for_user",
        "status": "exact_name_candidate",
    },
}


@dataclass(frozen=True, slots=True)
class FindingSpec:
    finding_id: str
    message: str
    action_id: str


ACTION_CATALOG: Mapping[str, str] = {
    "ACT-URI-001": "Use one repair transaction for every discovery origin.",
    "ACT-URI-002": "Let PM select repair scope directly from a structured defect observation.",
    "ACT-URI-003": "Create an immutable-history repair graft beside the target and append it at the current frontier.",
    "ACT-URI-004": "Dispatch substantive repair to Worker, then FlowGuard, then Reviewer.",
    "ACT-URI-005": "Bind repair contract and all accepted evidence to one fresh generation.",
    "ACT-URI-006": "Carry repair root, previous repair node, and monotonically increasing attempt lineage.",
    "ACT-URI-007": "Conserve active membership and explicitly rebind every unaffected sibling.",
    "ACT-URI-008": "Invalidate and replay the complete affected dependency cone before closure.",
    "ACT-URI-009": "Make terminal contracts coordinate ordinary repair grafts and require fresh terminal replay.",
    "ACT-URI-010": "Advance the route version and start a new run instead of reopening a terminal run.",
    "ACT-URI-011": "Keep authorized waiver and stop as packet-free terminal dispositions with their own authority/lifecycle gates.",
}


FINDING_CATALOG: Mapping[str, FindingSpec] = {
    "URI-F001": FindingSpec("URI-F001", "PM repair scope was not selected explicitly", "ACT-URI-002"),
    "URI-F002": FindingSpec("URI-F002", "PM historical defect was forced through a blocker prerequisite", "ACT-URI-002"),
    "URI-F003": FindingSpec("URI-F003", "accepted historical node state was mutated in place", "ACT-URI-003"),
    "URI-F004": FindingSpec("URI-F004", "repair graft does not point to its historical target", "ACT-URI-003"),
    "URI-F005": FindingSpec("URI-F005", "repair graft is not in the target's logical owning slot", "ACT-URI-003"),
    "URI-F006": FindingSpec("URI-F006", "repair work was inserted into historical order instead of the current frontier", "ACT-URI-003"),
    "URI-F007": FindingSpec("URI-F007", "substantive repair packet is not owned by Worker", "ACT-URI-004"),
    "URI-F008": FindingSpec("URI-F008", "repair packet lacks a concrete repair route node identity", "ACT-URI-004"),
    "URI-F009": FindingSpec("URI-F009", "repair gates do not follow Worker -> FlowGuard -> Reviewer", "ACT-URI-004"),
    "URI-F010": FindingSpec("URI-F010", "repair evidence is stale or crosses generations", "ACT-URI-005"),
    "URI-F011": FindingSpec("URI-F011", "repeated repair lineage is missing or discontinuous", "ACT-URI-006"),
    "URI-F012": FindingSpec("URI-F012", "active route membership is not conserved across replacement", "ACT-URI-007"),
    "URI-F013": FindingSpec("URI-F013", "unaffected sibling membership was not rebound into the new route version", "ACT-URI-007"),
    "URI-F014": FindingSpec("URI-F014", "final ledger omits an active route member", "ACT-URI-007"),
    "URI-F015": FindingSpec("URI-F015", "affected downstream evidence was not marked stale", "ACT-URI-008"),
    "URI-F016": FindingSpec("URI-F016", "stale downstream work was not replayed", "ACT-URI-008"),
    "URI-F017": FindingSpec("URI-F017", "terminal repair lacks its coordinating supplemental contract", "ACT-URI-009"),
    "URI-F018": FindingSpec("URI-F018", "terminal contract items are not projected onto repair nodes", "ACT-URI-009"),
    "URI-F019": FindingSpec("URI-F019", "terminal closure reused evidence predating the terminal repair contract", "ACT-URI-009"),
    "URI-F020": FindingSpec("URI-F020", "runtime opened a terminal repair round beyond the declared cap", "ACT-URI-009"),
    "URI-F021": FindingSpec("URI-F021", "selected repair scope was not materialized with matching scope semantics", "ACT-URI-003"),
    "URI-F022": FindingSpec("URI-F022", "repair changed active membership without advancing route version", "ACT-URI-010"),
    "URI-F023": FindingSpec("URI-F023", "repair attempted to reopen a complete or stopped run", "ACT-URI-010"),
    "URI-F024": FindingSpec("URI-F024", "terminal repair used a parallel shortcut instead of the ordinary repair transaction", "ACT-URI-001"),
    "URI-F025": FindingSpec("URI-F025", "superseded target remains an active route member", "ACT-URI-007"),
    "URI-F026": FindingSpec("URI-F026", "terminal backward replay did not rerun after repair", "ACT-URI-009"),
    "URI-F027": FindingSpec("URI-F027", "repair contract has no current evidence generation", "ACT-URI-005"),
    "URI-F028": FindingSpec("URI-F028", "unaffected sibling evidence was invalidated without declared dependency impact", "ACT-URI-008"),
    "URI-F029": FindingSpec("URI-F029", "repair trigger lacks a structured defect observation", "ACT-URI-001"),
    "URI-F030": FindingSpec("URI-F030", "authorized waiver lacks an explicit authority reference", "ACT-URI-011"),
    "URI-F031": FindingSpec("URI-F031", "terminal disposition created substantive repair work", "ACT-URI-011"),
    "URI-F032": FindingSpec("URI-F032", "stop_for_user did not terminate the current run", "ACT-URI-011"),
    "URI-F033": FindingSpec("URI-F033", "repair child identity vectors are malformed or ambiguous", "ACT-URI-003"),
    "URI-F034": FindingSpec("URI-F034", "repair child is not parented by the active replacement repair node", "ACT-URI-003"),
    "URI-F035": FindingSpec("URI-F035", "repair child generation is stale for the current repair generation", "ACT-URI-005"),
    "URI-F036": FindingSpec("URI-F036", "continue-repair decision gate is missing, stale, rejected, or out of order", "ACT-URI-004"),
    "URI-F037": FindingSpec("URI-F037", "staged repair effect committed or opened Worker before the decision gate accepted it", "ACT-URI-004"),
    "URI-F038": FindingSpec("URI-F038", "decision-gate Reviewer evidence was reused as post-work Reviewer evidence", "ACT-URI-004"),
    "URI-F039": FindingSpec("URI-F039", "rejected decision gate left an orphan effect or consumed a terminal repair round", "ACT-URI-009"),
    "URI-F040": FindingSpec("URI-F040", "terminal disposition entered the continue-repair decision gate", "ACT-URI-011"),
    "URI-F041": FindingSpec("URI-F041", "repeated repair did not supersede the latest repair generation or formed a lineage cycle", "ACT-URI-006"),
    "URI-F042": FindingSpec("URI-F042", "repair child is absent from active, terminal, execution, or acceptance closure", "ACT-URI-007"),
    "URI-F043": FindingSpec("URI-F043", "declared stale/replay work does not equal the dependency graph reachability cone", "ACT-URI-008"),
    "URI-F044": FindingSpec("URI-F044", "affected parent was not replayed after same-slot or scoped repair", "ACT-URI-008"),
    "URI-F045": FindingSpec("URI-F045", "terminal-run repair did not create a distinct active run with immutable read-only imports", "ACT-URI-010"),
    "URI-F046": FindingSpec("URI-F046", "repair effect, worker, evidence, or membership became active before its owning stage", "ACT-URI-004"),
    "URI-F047": FindingSpec("URI-F047", "rejected decision gate lacks an explicit disposed effect and PM revise/waive/stop/retry exits", "ACT-URI-011"),
}


@dataclass(frozen=True, slots=True)
class RepairTrigger:
    """One discovery event plus the PM-selected repair action."""

    origin: str
    requested_action: str
    case_id: str
    repair_attempt: int = 1
    terminal_round: int = 0
    fault_case_id: str = ""


@dataclass(frozen=True, slots=True)
class Action:
    action_id: str
    name: str
    repair_node_id: str


@dataclass(frozen=True, slots=True)
class State:
    status: str = "new"
    case_id: str = ""
    trigger_origin: str = ""
    defect_observation_id: str = ""
    blocker_prerequisite_required: bool = False
    pm_scope_selected: bool = False
    repair_action: str = ""
    authority_ref: str = ""
    repair_packet_created: bool = False
    terminal_disposition: bool = False
    run_terminated: bool = False
    run_status: str = "active"  # active | complete | stopped
    new_run_id: str = ""
    new_run_status: str = ""
    old_run_id: str = ""
    old_run_status: str = ""
    old_run_immutable: bool = False
    old_output_ids: tuple[str, ...] = ()
    read_only_imported_output_ids: tuple[str, ...] = ()

    original_node_id: str = ""
    original_parent_id: str = ""
    expected_logical_parent_id: str = ""
    original_snapshot_hash: str = ""
    old_history_immutable: bool = False
    old_node_mutated: bool = False
    repair_node_id: str = ""
    repairs_node_id: str = ""
    logical_parent_id: str = ""
    current_repair_generation: int = 0
    repair_child_ids: tuple[str, ...] = ()
    repair_child_parent_ids: tuple[str, ...] = ()
    repair_child_generations: tuple[int, ...] = ()
    execution_frontier_appended: bool = False
    historical_index_inserted: bool = False

    packet_owner: str = ""
    route_node_id: str = ""
    role_sequence: tuple[str, ...] = ()
    decision_gate_sequence: tuple[str, ...] = ()
    decision_gate_current: bool = False
    decision_gate_accepted: bool = False
    decision_gate_rejected: bool = False
    staged_effect_id: str = ""
    staged_effect_status: str = ""
    effect_committed_before_worker: bool = False
    worker_opened_after_effect_commit: bool = False
    decision_reviewer_result_id: str = ""
    post_work_reviewer_result_id: str = ""
    orphan_staged_effect: bool = False
    terminal_round_consumed_on_rejected_gate: bool = False
    rejected_gate_exit_options: tuple[str, ...] = ()

    current_generation: int = 0
    repair_contract_generation: int = 0
    worker_result_generation: int = 0
    flowguard_evidence_generation: int = 0
    reviewer_evidence_generation: int = 0

    repair_root_id: str = ""
    previous_repair_node_id: str = ""
    previous_repair_root_id: str = ""
    previous_repair_generation: int = 0
    previous_repair_attempt: int = 0
    repair_ancestor_node_ids: tuple[str, ...] = ()
    repair_attempt: int = 1
    lineage_complete: bool = False

    active_members_before: tuple[str, ...] = ()
    superseded_member_ids: tuple[str, ...] = ()
    replacement_member_ids: tuple[str, ...] = ()
    active_members_after: tuple[str, ...] = ()
    unaffected_member_ids: tuple[str, ...] = ()
    unaffected_rebound_ids: tuple[str, ...] = ()
    final_ledger_active_member_ids: tuple[str, ...] = ()
    active_route_node_order: tuple[str, ...] = ()
    terminal_target_node_ids: tuple[str, ...] = ()
    execution_acceptance_inventory: tuple[str, ...] = ()
    executed_repair_child_ids: tuple[str, ...] = ()
    accepted_repair_child_ids: tuple[str, ...] = ()

    dependency_edges: tuple[tuple[str, str], ...] = ()
    downstream_stale_ids: tuple[str, ...] = ()
    downstream_replayed_ids: tuple[str, ...] = ()
    affected_parent_node_ids: tuple[str, ...] = ()
    parent_replayed_node_ids: tuple[str, ...] = ()

    same_slot_replaced: bool = False
    parent_scope_replaced: bool = False
    subtree_superseded: bool = False
    route_replaced: bool = False
    route_version_before: int = 0
    route_version_after: int = 0

    terminal_contract_id: str = ""
    terminal_contract_item_ids: tuple[str, ...] = ()
    terminal_projected_item_ids: tuple[str, ...] = ()
    terminal_contract_generation: int = 0
    terminal_round: int = 0
    terminal_max_rounds: int = 3
    terminal_replay_completed: bool = False
    parallel_terminal_shortcut: bool = False


def _good_attempt(origin: str, action: str) -> int:
    if action in TERMINAL_DISPOSITION_ACTIONS:
        return 1
    if origin == "terminal_backward_replay" and action == "repair_parent_scope":
        return 3
    if origin == "terminal_backward_replay" and action == "repair_same_slot":
        return 2
    if origin == "system_postcondition_failure" and action == "repair_same_slot":
        return 2
    return 1


def _good_terminal_round(origin: str, action: str, attempt: int) -> int:
    if origin != "terminal_backward_replay" or action in TERMINAL_DISPOSITION_ACTIONS:
        return 0
    return attempt


GOOD_INPUTS = tuple(
    RepairTrigger(
        origin=origin,
        requested_action=action,
        case_id=f"good.{origin}.{action}",
        repair_attempt=_good_attempt(origin, action),
        terminal_round=_good_terminal_round(origin, action, _good_attempt(origin, action)),
    )
    for origin in TRIGGER_ORIGINS
    for action in REPAIR_ACTIONS
)

EXTERNAL_INPUTS = GOOD_INPUTS
REQUIRED_SAFE_LABELS = tuple(
    f"{stage}.{item.case_id}"
    for item in GOOD_INPUTS
    for stage in (
        TERMINAL_STAGE_NAMES
        if item.requested_action in TERMINAL_DISPOSITION_ACTIONS
        else SUBSTANTIVE_STAGE_NAMES
    )
) + tuple(
    f"{REJECTED_GATE_STATUS}.{item.case_id}"
    for item in GOOD_INPUTS
    if item.requested_action in SUBSTANTIVE_REPAIR_ACTIONS
)


def initial_state() -> State:
    return State()


def _scope_identity(action: str) -> tuple[str, str, str]:
    if action == "repair_same_slot":
        return "node-work", "node-module", "node-work-repair-r1"
    if action == "repair_parent_scope":
        return "node-module", "node-root", "node-module-repair-r1"
    if action == "repair_subtree":
        return "node-subtree-root", "node-root", "node-subtree-repair-r1"
    if action == "redesign_route":
        return "route-v1", "run-001", "route-v2-repair-root"
    raise ValueError(f"unsupported repair action: {action}")


def _repair_node_id_for_attempt(base_id: str, attempt: int) -> str:
    if attempt < 1:
        raise ValueError("repair attempt must be positive")
    if attempt == 1:
        return base_id
    if base_id.endswith("-r1"):
        return f"{base_id[:-2]}r{attempt}"
    return f"{base_id}-r{attempt}"


def canonical_state(trigger: RepairTrigger) -> State:
    if trigger.origin not in TRIGGER_ORIGINS:
        raise ValueError(f"unsupported trigger origin: {trigger.origin}")
    if trigger.requested_action not in REPAIR_ACTIONS:
        raise ValueError(f"unsupported repair action: {trigger.requested_action}")
    if trigger.repair_attempt < 1:
        raise ValueError("repair attempt must be positive")
    if trigger.requested_action in TERMINAL_DISPOSITION_ACTIONS:
        stopped = trigger.requested_action == "stop_for_user"
        return State(
            status="complete",
            case_id=trigger.case_id,
            trigger_origin=trigger.origin,
            defect_observation_id=f"defect-{trigger.case_id}",
            blocker_prerequisite_required=False,
            pm_scope_selected=True,
            repair_action=trigger.requested_action,
            authority_ref="authority://explicit-waiver" if trigger.requested_action == "authorized_waiver" else "",
            repair_packet_created=False,
            terminal_disposition=True,
            run_terminated=stopped,
            run_status="stopped" if stopped else "active",
            original_snapshot_hash="sha256:terminal-disposition-history",
            old_history_immutable=True,
            old_node_mutated=False,
            route_version_before=1,
            route_version_after=1,
            terminal_max_rounds=3,
            repair_attempt=trigger.repair_attempt,
        )
    target_id, logical_parent_id, base_repair_node_id = _scope_identity(trigger.requested_action)
    repair_node_id = _repair_node_id_for_attempt(base_repair_node_id, trigger.repair_attempt)
    prior_repair_node_ids = tuple(
        _repair_node_id_for_attempt(base_repair_node_id, attempt)
        for attempt in range(1, trigger.repair_attempt)
    )
    previous_repair_node_id = prior_repair_node_ids[-1] if prior_repair_node_ids else ""
    superseded_target_id = previous_repair_node_id or target_id
    repair_root_id = f"repair-root-{target_id}"
    repair_child_id = f"{repair_node_id}-child-1"
    sibling_a = f"{logical_parent_id}-unaffected-a"
    sibling_b = f"{logical_parent_id}-unaffected-b"
    before = (superseded_target_id, sibling_a, sibling_b)
    after = (repair_node_id, repair_child_id, sibling_a, sibling_b)
    terminal = trigger.origin == "terminal_backward_replay"
    dependent_id = f"dependent-of-{target_id}"
    terminal_dependent_id = f"terminal-dependent-of-{target_id}"
    dependency_edges = (
        (repair_node_id, logical_parent_id),
        (logical_parent_id, dependent_id),
        (dependent_id, terminal_dependent_id),
    )
    impact_cone = (logical_parent_id, dependent_id, terminal_dependent_id)
    bridges_terminal_run = (
        trigger.origin == "pm_historical_defect"
        and trigger.requested_action == "repair_parent_scope"
    )
    return State(
        status="complete",
        case_id=trigger.case_id,
        trigger_origin=trigger.origin,
        defect_observation_id=f"defect-{trigger.case_id}",
        blocker_prerequisite_required=False,
        pm_scope_selected=True,
        repair_action=trigger.requested_action,
        repair_packet_created=True,
        terminal_disposition=False,
        run_terminated=False,
        run_status="active",
        old_run_id="run-complete-001" if bridges_terminal_run else "",
        old_run_status="complete" if bridges_terminal_run else "",
        old_run_immutable=bridges_terminal_run,
        old_output_ids=("output://run-complete-001/final",) if bridges_terminal_run else (),
        new_run_id="run-repair-002" if bridges_terminal_run else "",
        new_run_status="active" if bridges_terminal_run else "",
        read_only_imported_output_ids=("output://run-complete-001/final",) if bridges_terminal_run else (),
        original_node_id=target_id,
        original_parent_id=logical_parent_id,
        expected_logical_parent_id=logical_parent_id,
        original_snapshot_hash=f"sha256:original-{target_id}",
        old_history_immutable=True,
        old_node_mutated=False,
        repair_node_id=repair_node_id,
        repairs_node_id=superseded_target_id,
        logical_parent_id=logical_parent_id,
        current_repair_generation=trigger.repair_attempt,
        repair_child_ids=(repair_child_id,),
        repair_child_parent_ids=(repair_node_id,),
        repair_child_generations=(trigger.repair_attempt,),
        execution_frontier_appended=True,
        historical_index_inserted=False,
        packet_owner="Worker",
        route_node_id=repair_node_id,
        role_sequence=POST_WORK_ROLE_SEQUENCE,
        decision_gate_sequence=DECISION_GATE_SEQUENCE,
        decision_gate_current=True,
        decision_gate_accepted=True,
        decision_gate_rejected=False,
        staged_effect_id=f"effect-{trigger.case_id}",
        staged_effect_status="committed",
        effect_committed_before_worker=True,
        worker_opened_after_effect_commit=True,
        decision_reviewer_result_id=f"decision-review-{trigger.case_id}",
        post_work_reviewer_result_id=f"post-work-review-{trigger.case_id}",
        orphan_staged_effect=False,
        terminal_round_consumed_on_rejected_gate=False,
        current_generation=trigger.repair_attempt,
        repair_contract_generation=trigger.repair_attempt,
        worker_result_generation=trigger.repair_attempt,
        flowguard_evidence_generation=trigger.repair_attempt,
        reviewer_evidence_generation=trigger.repair_attempt,
        repair_root_id=repair_root_id,
        previous_repair_node_id=previous_repair_node_id,
        previous_repair_root_id=repair_root_id if previous_repair_node_id else "",
        previous_repair_generation=trigger.repair_attempt - 1,
        previous_repair_attempt=trigger.repair_attempt - 1,
        repair_ancestor_node_ids=(target_id, *prior_repair_node_ids),
        repair_attempt=trigger.repair_attempt,
        lineage_complete=True,
        active_members_before=before,
        superseded_member_ids=(superseded_target_id,),
        replacement_member_ids=(repair_node_id, repair_child_id),
        active_members_after=after,
        unaffected_member_ids=(sibling_a, sibling_b),
        unaffected_rebound_ids=(sibling_a, sibling_b),
        final_ledger_active_member_ids=after,
        active_route_node_order=after,
        terminal_target_node_ids=(repair_node_id, repair_child_id),
        execution_acceptance_inventory=(repair_child_id,),
        executed_repair_child_ids=(repair_child_id,),
        accepted_repair_child_ids=(repair_child_id,),
        dependency_edges=dependency_edges,
        downstream_stale_ids=impact_cone,
        downstream_replayed_ids=impact_cone,
        affected_parent_node_ids=(logical_parent_id,),
        parent_replayed_node_ids=(logical_parent_id,),
        same_slot_replaced=trigger.requested_action == "repair_same_slot",
        parent_scope_replaced=trigger.requested_action == "repair_parent_scope",
        subtree_superseded=trigger.requested_action == "repair_subtree",
        route_replaced=trigger.requested_action == "redesign_route",
        route_version_before=1,
        route_version_after=2,
        terminal_contract_id=(
            f"terminal-repair-contract-r{trigger.terminal_round}"
            if terminal
            else ""
        ),
        terminal_contract_item_ids=("terminal-repair-item-1",) if terminal else (),
        terminal_projected_item_ids=("terminal-repair-item-1",) if terminal else (),
        terminal_contract_generation=trigger.repair_attempt if terminal else 0,
        terminal_round=trigger.terminal_round if terminal else 0,
        terminal_max_rounds=3,
        terminal_replay_completed=terminal,
        parallel_terminal_shortcut=False,
    )


def _substantive_precommit_state(trigger: RepairTrigger, status: str) -> State:
    final = canonical_state(trigger)
    return replace(
        final,
        status=status,
        repair_packet_created=False,
        repair_node_id="",
        repairs_node_id="",
        logical_parent_id="",
        current_repair_generation=0,
        repair_child_ids=(),
        repair_child_parent_ids=(),
        repair_child_generations=(),
        execution_frontier_appended=False,
        packet_owner="",
        route_node_id="",
        role_sequence=(),
        decision_gate_sequence=(),
        decision_gate_current=False,
        decision_gate_accepted=False,
        decision_gate_rejected=False,
        staged_effect_id="",
        staged_effect_status="",
        effect_committed_before_worker=False,
        worker_opened_after_effect_commit=False,
        decision_reviewer_result_id="",
        post_work_reviewer_result_id="",
        rejected_gate_exit_options=(),
        current_generation=0,
        repair_contract_generation=0,
        worker_result_generation=0,
        flowguard_evidence_generation=0,
        reviewer_evidence_generation=0,
        repair_root_id="",
        previous_repair_node_id="",
        previous_repair_root_id="",
        previous_repair_generation=0,
        previous_repair_attempt=0,
        repair_ancestor_node_ids=(),
        lineage_complete=False,
        superseded_member_ids=(),
        replacement_member_ids=(),
        active_members_after=final.active_members_before,
        unaffected_member_ids=(),
        unaffected_rebound_ids=(),
        final_ledger_active_member_ids=final.active_members_before,
        active_route_node_order=final.active_members_before,
        terminal_target_node_ids=(),
        execution_acceptance_inventory=(),
        executed_repair_child_ids=(),
        accepted_repair_child_ids=(),
        dependency_edges=(),
        downstream_stale_ids=(),
        downstream_replayed_ids=(),
        affected_parent_node_ids=(),
        parent_replayed_node_ids=(),
        same_slot_replaced=False,
        parent_scope_replaced=False,
        subtree_superseded=False,
        route_replaced=False,
        route_version_after=final.route_version_before,
        terminal_contract_id="",
        terminal_contract_item_ids=(),
        terminal_projected_item_ids=(),
        terminal_contract_generation=0,
        terminal_round=0,
        terminal_replay_completed=False,
    )


def stage_state(trigger: RepairTrigger, status: str) -> State:
    if trigger.requested_action in TERMINAL_DISPOSITION_ACTIONS:
        if status not in TERMINAL_STAGE_NAMES:
            raise ValueError(f"unsupported terminal disposition stage: {status}")
        return replace(canonical_state(trigger), status=status)
    if status == "triggered":
        return _substantive_precommit_state(trigger, status)
    if status == "decision_staged":
        return replace(
            _substantive_precommit_state(trigger, status),
            decision_gate_sequence=DECISION_GATE_SEQUENCE[:2],
            decision_gate_current=True,
            staged_effect_id=f"effect-{trigger.case_id}",
            staged_effect_status="staged",
        )
    if status == "decision_gate_accepted":
        return replace(
            _substantive_precommit_state(trigger, status),
            decision_gate_sequence=DECISION_GATE_SEQUENCE[:6],
            decision_gate_current=True,
            decision_gate_accepted=True,
            staged_effect_id=f"effect-{trigger.case_id}",
            staged_effect_status="accepted",
            decision_reviewer_result_id=f"decision-review-{trigger.case_id}",
        )
    if status == REJECTED_GATE_STATUS:
        return replace(
            _substantive_precommit_state(trigger, status),
            decision_gate_sequence=DECISION_GATE_SEQUENCE[:3],
            decision_gate_current=True,
            decision_gate_rejected=True,
            staged_effect_id=f"effect-{trigger.case_id}",
            staged_effect_status="disposed",
            rejected_gate_exit_options=REJECTED_GATE_EXIT_OPTIONS,
        )
    if status == "effect_committed_and_worker_open":
        return replace(
            canonical_state(trigger),
            status=status,
            role_sequence=(),
            worker_result_generation=0,
            flowguard_evidence_generation=0,
            reviewer_evidence_generation=0,
            post_work_reviewer_result_id="",
            executed_repair_child_ids=(),
            accepted_repair_child_ids=(),
            downstream_replayed_ids=(),
            parent_replayed_node_ids=(),
            terminal_replay_completed=False,
        )
    if status == "post_work_checked":
        return replace(
            canonical_state(trigger),
            status=status,
            terminal_replay_completed=False,
        )
    if status == "complete":
        return canonical_state(trigger)
    raise ValueError(f"unsupported substantive repair stage: {status}")


def next_stage_name(state: State) -> str:
    stages = (
        TERMINAL_STAGE_NAMES
        if state.repair_action in TERMINAL_DISPOSITION_ACTIONS
        else SUBSTANTIVE_STAGE_NAMES
    )
    if state.status == "new":
        return stages[0]
    try:
        index = stages.index(state.status)
    except ValueError:
        return ""
    return stages[index + 1] if index + 1 < len(stages) else ""


def _set_eq(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    return set(left) == set(right) and len(left) == len(set(left)) and len(right) == len(set(right))


def _dependency_descendants(
    start_id: str,
    edges: tuple[tuple[str, str], ...],
) -> tuple[str, ...]:
    """Return the finite transitive dependency cone in stable breadth-first order."""

    adjacency: dict[str, list[str]] = {}
    for source_id, target_id in edges:
        adjacency.setdefault(source_id, []).append(target_id)
    visited = {start_id}
    queue = [start_id]
    descendants: list[str] = []
    while queue:
        source_id = queue.pop(0)
        for target_id in adjacency.get(source_id, []):
            if target_id in visited:
                continue
            visited.add(target_id)
            descendants.append(target_id)
            queue.append(target_id)
    return tuple(descendants)


def _dependency_graph_malformed(state: State) -> bool:
    if not state.dependency_edges:
        return True
    if any(
        not source_id or not target_id or source_id == target_id
        for source_id, target_id in state.dependency_edges
    ):
        return True
    # A reachable edge back to the repair node would make the impact cone cyclic.
    return any(
        target_id == state.repair_node_id
        for source_id, target_id in state.dependency_edges
        if source_id != state.repair_node_id
    )


def _precommit_repair_surface_present(state: State) -> bool:
    return any(
        (
            state.repair_packet_created,
            bool(state.repair_node_id),
            bool(state.repairs_node_id),
            bool(state.logical_parent_id),
            state.current_repair_generation > 0,
            bool(state.repair_child_ids),
            state.execution_frontier_appended,
            bool(state.packet_owner),
            bool(state.route_node_id),
            bool(state.role_sequence),
            state.current_generation > 0,
            state.repair_contract_generation > 0,
            state.worker_result_generation > 0,
            state.flowguard_evidence_generation > 0,
            state.reviewer_evidence_generation > 0,
            bool(state.superseded_member_ids),
            bool(state.replacement_member_ids),
            bool(state.dependency_edges),
            bool(state.downstream_stale_ids),
            bool(state.downstream_replayed_ids),
            bool(state.affected_parent_node_ids),
            bool(state.parent_replayed_node_ids),
            state.route_version_after != state.route_version_before,
            bool(state.terminal_contract_id),
            state.terminal_round > 0,
        )
    )


def invariant_findings(state: State) -> tuple[FindingSpec, ...]:
    if state.status == "new":
        return ()
    finding_ids: list[str] = []

    def add(finding_id: str) -> None:
        if finding_id not in finding_ids:
            finding_ids.append(finding_id)

    if not state.defect_observation_id or state.trigger_origin not in TRIGGER_ORIGINS:
        add("URI-F029")
    if not state.pm_scope_selected or state.repair_action not in REPAIR_ACTIONS:
        add("URI-F001")
    if state.trigger_origin == "pm_historical_defect" and state.blocker_prerequisite_required:
        add("URI-F002")

    if state.repair_action in TERMINAL_DISPOSITION_ACTIONS:
        if not state.old_history_immutable or state.old_node_mutated or not state.original_snapshot_hash:
            add("URI-F003")
        if state.repair_action == "authorized_waiver" and not state.authority_ref:
            add("URI-F030")
        repair_surface_present = any(
            (
                state.repair_packet_created,
                bool(state.repair_node_id),
                bool(state.repairs_node_id),
                bool(state.packet_owner),
                bool(state.route_node_id),
                bool(state.role_sequence),
                bool(state.repair_child_ids),
                bool(state.repair_child_parent_ids),
                bool(state.repair_child_generations),
                state.current_repair_generation > 0,
                state.repair_contract_generation > 0,
                bool(state.replacement_member_ids),
                state.route_version_after != state.route_version_before,
                bool(state.dependency_edges),
            )
        )
        if repair_surface_present or not state.terminal_disposition:
            add("URI-F031")
        decision_gate_surface_present = any(
            (
                bool(state.decision_gate_sequence),
                state.decision_gate_current,
                state.decision_gate_accepted,
                state.decision_gate_rejected,
                bool(state.staged_effect_id),
                bool(state.staged_effect_status),
                state.effect_committed_before_worker,
                state.worker_opened_after_effect_commit,
                bool(state.decision_reviewer_result_id),
                bool(state.post_work_reviewer_result_id),
                state.orphan_staged_effect,
                state.terminal_round_consumed_on_rejected_gate,
                bool(state.rejected_gate_exit_options),
            )
        )
        if decision_gate_surface_present:
            add("URI-F040")
        if state.repair_action == "stop_for_user" and not (
            state.run_terminated and state.run_status == "stopped"
        ):
            add("URI-F032")
        return tuple(FINDING_CATALOG[finding_id] for finding_id in finding_ids)

    if state.repair_action not in SUBSTANTIVE_REPAIR_ACTIONS:
        add("URI-F021")
        return tuple(FINDING_CATALOG[finding_id] for finding_id in finding_ids)
    if not state.old_history_immutable or state.old_node_mutated or not state.original_snapshot_hash:
        add("URI-F003")

    allowed_stages = set(SUBSTANTIVE_STAGE_NAMES) | {REJECTED_GATE_STATUS}
    if state.status not in allowed_stages:
        add("URI-F046")
        return tuple(FINDING_CATALOG[finding_id] for finding_id in finding_ids)

    precommit_statuses = {"triggered", "decision_staged", "decision_gate_accepted"}
    if state.status in precommit_statuses or state.status == REJECTED_GATE_STATUS:
        if _precommit_repair_surface_present(state):
            add("URI-F046")
        if state.status == "triggered":
            if any(
                (
                    state.decision_gate_sequence,
                    state.decision_gate_current,
                    state.decision_gate_accepted,
                    state.decision_gate_rejected,
                    state.staged_effect_id,
                    state.staged_effect_status,
                )
            ):
                add("URI-F036")
        elif state.status == "decision_staged":
            if not (
                state.decision_gate_sequence == DECISION_GATE_SEQUENCE[:2]
                and state.decision_gate_current
                and not state.decision_gate_accepted
                and not state.decision_gate_rejected
                and bool(state.staged_effect_id)
                and state.staged_effect_status == "staged"
                and not state.decision_reviewer_result_id
            ):
                add("URI-F036")
        elif state.status == "decision_gate_accepted":
            if not (
                state.decision_gate_sequence == DECISION_GATE_SEQUENCE[:6]
                and state.decision_gate_current
                and state.decision_gate_accepted
                and not state.decision_gate_rejected
                and bool(state.staged_effect_id)
                and state.staged_effect_status == "accepted"
                and bool(state.decision_reviewer_result_id)
            ):
                add("URI-F036")
        else:
            rejected_shape_ok = (
                state.decision_gate_sequence == DECISION_GATE_SEQUENCE[:3]
                and state.decision_gate_current
                and not state.decision_gate_accepted
                and state.decision_gate_rejected
                and bool(state.staged_effect_id)
                and state.staged_effect_status == "disposed"
                and not state.orphan_staged_effect
                and not state.terminal_round_consumed_on_rejected_gate
                and state.terminal_round == 0
            )
            if not rejected_shape_ok:
                add("URI-F039")
            if state.rejected_gate_exit_options != REJECTED_GATE_EXIT_OPTIONS:
                add("URI-F047")
        return tuple(FINDING_CATALOG[finding_id] for finding_id in finding_ids)

    # From effect commit onward, the decision gate must be fully accepted first.
    if not (
        state.decision_gate_sequence == DECISION_GATE_SEQUENCE
        and state.decision_gate_current
        and state.decision_gate_accepted
        and not state.decision_gate_rejected
        and bool(state.staged_effect_id)
        and state.staged_effect_status == "committed"
    ):
        add("URI-F036")
    if (
        not state.effect_committed_before_worker
        or not state.worker_opened_after_effect_commit
        or (state.staged_effect_status == "committed" and not state.decision_gate_accepted)
    ):
        add("URI-F037")
    if state.decision_gate_rejected and (
        state.orphan_staged_effect
        or state.terminal_round_consumed_on_rejected_gate
        or state.staged_effect_status != "disposed"
    ):
        add("URI-F039")
    if not state.decision_reviewer_result_id:
        add("URI-F036")

    if not state.repair_packet_created or state.terminal_disposition or state.run_terminated:
        add("URI-F021")
    if state.run_status in {"complete", "stopped"}:
        add("URI-F023")
    bridge_surface = any(
        (
            state.old_run_id,
            state.old_run_status,
            state.new_run_id,
            state.new_run_status,
            state.old_run_immutable,
            state.old_output_ids,
            state.read_only_imported_output_ids,
        )
    )
    if bridge_surface and not (
        bool(state.old_run_id)
        and state.old_run_status in {"complete", "stopped"}
        and bool(state.new_run_id)
        and state.new_run_id != state.old_run_id
        and state.new_run_status == "active"
        and state.run_status == "active"
        and state.old_run_immutable
        and bool(state.old_output_ids)
        and _set_eq(state.old_output_ids, state.read_only_imported_output_ids)
    ):
        add("URI-F045")

    if not state.execution_frontier_appended or state.historical_index_inserted:
        add("URI-F006")
    if state.packet_owner != "Worker":
        add("URI-F007")
    if not state.route_node_id or state.route_node_id != state.repair_node_id:
        add("URI-F008")
    if (
        not state.logical_parent_id
        or state.logical_parent_id != state.expected_logical_parent_id
        or state.logical_parent_id != state.original_parent_id
    ):
        add("URI-F005")

    if not state.repair_root_id or state.repair_attempt < 1 or not state.lineage_complete:
        add("URI-F011")
    if state.current_repair_generation != state.repair_attempt:
        add("URI-F041")
    if state.repair_attempt == 1:
        if (
            state.repairs_node_id != state.original_node_id
            or state.previous_repair_node_id
            or state.previous_repair_root_id
            or state.previous_repair_generation != 0
            or state.previous_repair_attempt != 0
            or state.repair_ancestor_node_ids != (state.original_node_id,)
        ):
            add("URI-F011")
            add("URI-F004")
    else:
        ancestors = state.repair_ancestor_node_ids
        repeated_ok = (
            bool(state.previous_repair_node_id)
            and state.repairs_node_id == state.previous_repair_node_id
            and state.superseded_member_ids == (state.previous_repair_node_id,)
            and state.previous_repair_node_id in set(state.active_members_before)
            and state.original_node_id not in set(state.superseded_member_ids)
            and state.previous_repair_root_id == state.repair_root_id
            and state.previous_repair_generation + 1 == state.current_repair_generation
            and state.previous_repair_attempt + 1 == state.repair_attempt
            and bool(ancestors)
            and ancestors[0] == state.original_node_id
            and ancestors[-1] == state.previous_repair_node_id
            and len(ancestors) == len(set(ancestors))
            and state.repair_node_id not in set(ancestors)
        )
        if not repeated_ok:
            add("URI-F011")
            add("URI-F041")
        if state.repairs_node_id != state.previous_repair_node_id:
            add("URI-F004")

    child_lengths = (
        len(state.repair_child_ids),
        len(state.repair_child_parent_ids),
        len(state.repair_child_generations),
    )
    child_vectors_ok = (
        child_lengths[0] > 0
        and len(set(child_lengths)) == 1
        and all(state.repair_child_ids)
        and len(set(state.repair_child_ids)) == child_lengths[0]
    )
    if not child_vectors_ok:
        add("URI-F033")
    else:
        active_replacement = (
            bool(state.repair_node_id)
            and state.repair_node_id in set(state.replacement_member_ids)
            and state.route_node_id == state.repair_node_id
        )
        for parent_id, generation in zip(
            state.repair_child_parent_ids,
            state.repair_child_generations,
        ):
            if (
                not active_replacement
                or parent_id != state.repair_node_id
                or parent_id == state.original_node_id
            ):
                add("URI-F034")
            if generation != state.current_repair_generation:
                add("URI-F035")

    before = set(state.active_members_before)
    superseded = set(state.superseded_member_ids)
    replacements = set(state.replacement_member_ids)
    children = set(state.repair_child_ids)
    expected_after = (before - superseded) | replacements
    if (
        not superseded.issubset(before)
        or not _set_eq(state.active_members_after, tuple(expected_after))
        or state.repair_node_id not in replacements
        or not children.issubset(replacements)
    ):
        add("URI-F012")
    expected_unaffected = before - superseded
    if not _set_eq(state.unaffected_member_ids, tuple(expected_unaffected)) or not _set_eq(
        state.unaffected_rebound_ids,
        tuple(expected_unaffected),
    ):
        add("URI-F013")
    if not _set_eq(state.final_ledger_active_member_ids, state.active_members_after):
        add("URI-F014")
    if superseded & set(state.active_members_after):
        add("URI-F025")

    child_closure_sets = (
        set(state.active_members_after),
        set(state.active_route_node_order),
        set(state.final_ledger_active_member_ids),
        set(state.terminal_target_node_ids),
        set(state.execution_acceptance_inventory),
    )
    if any(not children.issubset(container) for container in child_closure_sets):
        add("URI-F042")

    scope_flags = {
        "repair_same_slot": state.same_slot_replaced,
        "repair_parent_scope": state.parent_scope_replaced,
        "repair_subtree": state.subtree_superseded,
        "redesign_route": state.route_replaced,
    }
    if not scope_flags[state.repair_action] or sum(bool(value) for value in scope_flags.values()) != 1:
        add("URI-F021")
    if state.route_version_after != state.route_version_before + 1:
        add("URI-F022")

    if state.repair_contract_generation <= 0:
        add("URI-F027")
    if not (
        state.current_repair_generation == state.current_generation
        and state.repair_contract_generation == state.current_generation
    ):
        add("URI-F010")

    if _dependency_graph_malformed(state):
        add("URI-F043")
        derived_cone: tuple[str, ...] = ()
    else:
        derived_cone = _dependency_descendants(state.repair_node_id, state.dependency_edges)
    if not _set_eq(state.downstream_stale_ids, derived_cone):
        add("URI-F015")
        add("URI-F043")
    if not set(state.affected_parent_node_ids).issubset(set(derived_cone)) or not state.affected_parent_node_ids:
        add("URI-F044")
    if set(state.unaffected_member_ids) & (
        set(derived_cone) | set(state.downstream_stale_ids)
    ):
        add("URI-F028")

    if state.status == "effect_committed_and_worker_open":
        if any(
            (
                state.role_sequence,
                state.worker_result_generation,
                state.flowguard_evidence_generation,
                state.reviewer_evidence_generation,
                state.post_work_reviewer_result_id,
                state.executed_repair_child_ids,
                state.accepted_repair_child_ids,
                state.downstream_replayed_ids,
                state.parent_replayed_node_ids,
                state.terminal_replay_completed,
            )
        ):
            add("URI-F046")
    else:
        if state.role_sequence != POST_WORK_ROLE_SEQUENCE:
            add("URI-F009")
        evidence_generations = (
            state.worker_result_generation,
            state.flowguard_evidence_generation,
            state.reviewer_evidence_generation,
        )
        if (
            any(value != state.current_generation for value in evidence_generations)
            or len(set(evidence_generations)) != 1
        ):
            add("URI-F010")
        if (
            not state.post_work_reviewer_result_id
            or state.post_work_reviewer_result_id == state.decision_reviewer_result_id
        ):
            add("URI-F038")
        if not _set_eq(state.executed_repair_child_ids, state.repair_child_ids) or not _set_eq(
            state.accepted_repair_child_ids,
            state.repair_child_ids,
        ):
            add("URI-F042")
        if not _set_eq(state.downstream_replayed_ids, derived_cone):
            add("URI-F016")
        if not _set_eq(state.parent_replayed_node_ids, state.affected_parent_node_ids):
            add("URI-F044")

    if state.trigger_origin == "terminal_backward_replay":
        if not state.terminal_contract_id or not state.terminal_contract_item_ids:
            add("URI-F017")
        if not _set_eq(state.terminal_projected_item_ids, state.terminal_contract_item_ids):
            add("URI-F018")
        if (
            state.terminal_contract_generation <= 0
            or state.terminal_contract_generation != state.repair_contract_generation
            or (
                state.status != "effect_committed_and_worker_open"
                and state.terminal_contract_generation > state.worker_result_generation
            )
        ):
            add("URI-F019")
        if (
            state.terminal_round < 1
            or state.terminal_round > state.terminal_max_rounds
            or state.terminal_round != state.repair_attempt
        ):
            add("URI-F020")
        if state.parallel_terminal_shortcut:
            add("URI-F024")
        if state.status == "complete" and not state.terminal_replay_completed:
            add("URI-F026")
        if state.status != "complete" and state.terminal_replay_completed:
            add("URI-F046")
    elif any(
        (
            state.terminal_contract_id,
            state.terminal_contract_item_ids,
            state.terminal_projected_item_ids,
            state.terminal_contract_generation,
            state.terminal_round,
            state.terminal_replay_completed,
            state.parallel_terminal_shortcut,
        )
    ):
        add("URI-F024")
    return tuple(FINDING_CATALOG[finding_id] for finding_id in finding_ids)


def invariant_failures(state: State) -> list[str]:
    return [f"{finding.finding_id}: {finding.message}" for finding in invariant_findings(state)]


def _integrity_invariant(state: State, _trace: object = ()) -> InvariantResult:
    findings = invariant_findings(state)
    if findings:
        return InvariantResult.fail("; ".join(f"{item.finding_id}: {item.message}" for item in findings))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="unified_repair_integrity",
        description=(
            "All repair origins refine to one immutable-history repair graft, current-frontier execution, "
            "Worker-FlowGuard-Reviewer evidence generation, lineage, membership conservation, dependency replay, "
            "and terminal contract/replay boundary."
        ),
        predicate=_integrity_invariant,
    ),
)


def action_id_for_scope(action: str) -> str:
    if action in TERMINAL_DISPOSITION_ACTIONS:
        return "ACT-URI-011"
    if action in {"repair_same_slot", "repair_parent_scope", "repair_subtree"}:
        return "ACT-URI-003"
    if action == "redesign_route":
        return "ACT-URI-010"
    return "ACT-URI-001"


class UnifiedRepairIntegrityBlock:
    """RepairTrigger x State -> Set(Action x State)."""

    name = "UnifiedRepairIntegrityBlock"
    input_description = "structured late-defect trigger plus PM-selected repair scope"
    output_description = "one canonical repair action and resulting integrity state"
    reads = ("repair_trigger", "route_membership", "evidence_generations", "terminal_contract")
    writes = ("repair_graft", "execution_frontier", "replay_requirements", "closure_evidence")
    idempotency = "case_id and repair_root_id"

    def apply(self, input_obj: RepairTrigger, state: State) -> Iterable[FunctionResult]:
        if input_obj.fault_case_id and state.status == "new":
            next_state, _expected = known_bad_cases()[input_obj.fault_case_id]
            label = f"reject.{input_obj.fault_case_id}"
        else:
            if state.status == "complete":
                return
            if state.status != "new" and (
                input_obj.case_id != state.case_id
                or input_obj.origin != state.trigger_origin
                or input_obj.requested_action != state.repair_action
                or input_obj.repair_attempt != state.repair_attempt
            ):
                return
            if state.status == "new":
                next_stage = (
                    TERMINAL_STAGE_NAMES[0]
                    if input_obj.requested_action in TERMINAL_DISPOSITION_ACTIONS
                    else SUBSTANTIVE_STAGE_NAMES[0]
                )
            else:
                next_stage = next_stage_name(state)
            if not next_stage:
                return
            next_state = stage_state(input_obj, next_stage)
            label = f"{next_stage}.{input_obj.case_id}"
        yield FunctionResult(
            output=Action(
                action_id=action_id_for_scope(input_obj.requested_action),
                name=input_obj.requested_action,
                repair_node_id=next_state.repair_node_id,
            ),
            new_state=next_state,
            label=label,
        )
        if (
            not input_obj.fault_case_id
            and state.status == "decision_staged"
            and input_obj.requested_action in SUBSTANTIVE_REPAIR_ACTIONS
        ):
            rejected_state = stage_state(input_obj, REJECTED_GATE_STATUS)
            yield FunctionResult(
                output=Action(
                    action_id="ACT-URI-011",
                    name="dispose_rejected_repair_decision",
                    repair_node_id="",
                ),
                new_state=rejected_state,
                label=f"{REJECTED_GATE_STATUS}.{input_obj.case_id}",
            )


def build_workflow() -> Workflow:
    return Workflow((UnifiedRepairIntegrityBlock(),), name=MODEL_ID)


def terminal_predicate(_input_obj: RepairTrigger, state: State, _trace: object) -> bool:
    return state.status in {"complete", REJECTED_GATE_STATUS}


def is_success(state: State) -> bool:
    return state.status in {"complete", REJECTED_GATE_STATUS} and not invariant_findings(state)


def _bad_base(origin: str, action: str, case_id: str) -> State:
    attempt = _good_attempt(origin, action)
    return canonical_state(
        RepairTrigger(
            origin=origin,
            requested_action=action,
            case_id=case_id,
            repair_attempt=attempt,
            terminal_round=_good_terminal_round(origin, action, attempt),
        )
    )


def known_bad_cases() -> dict[str, tuple[State, tuple[str, ...]]]:
    """Return current audit regressions and the stable findings they must trigger."""

    historical = _bad_base("pm_historical_defect", "repair_same_slot", "bad.historical")
    terminal = _bad_base("terminal_backward_replay", "repair_same_slot", "bad.terminal")
    parent = _bad_base("parent_backward_replay", "repair_parent_scope", "bad.parent")
    subtree = _bad_base("reviewer_node_failure", "repair_subtree", "bad.subtree")
    route = _bad_base("system_postcondition_failure", "redesign_route", "bad.route")
    waiver = _bad_base("terminal_backward_replay", "authorized_waiver", "bad.waiver")
    stop = _bad_base("terminal_backward_replay", "stop_for_user", "bad.stop")
    repeated = canonical_state(
        RepairTrigger(
            origin="pm_historical_defect",
            requested_action="repair_same_slot",
            case_id="bad.repeated",
            repair_attempt=2,
        )
    )
    cases: dict[str, tuple[State, tuple[str, ...]]] = {
        "KB-URI-001-historical-blocker-prerequisite": (
            replace(historical, blocker_prerequisite_required=True),
            ("URI-F002",),
        ),
        "KB-URI-002-auto-scope-without-pm-choice": (
            replace(historical, pm_scope_selected=False),
            ("URI-F001",),
        ),
        "KB-URI-003-old-node-mutated-in-place": (
            replace(historical, old_history_immutable=False, old_node_mutated=True),
            ("URI-F003",),
        ),
        "KB-URI-004-unanchored-repair": (
            replace(historical, repairs_node_id=""),
            ("URI-F004",),
        ),
        "KB-URI-005-repair-in-wrong-logical-slot": (
            replace(historical, logical_parent_id="wrong-parent"),
            ("URI-F005",),
        ),
        "KB-URI-006-repair-inserted-into-history": (
            replace(historical, execution_frontier_appended=False, historical_index_inserted=True),
            ("URI-F006",),
        ),
        "KB-URI-007-terminal-repair-owned-by-reviewer": (
            replace(terminal, packet_owner="Reviewer"),
            ("URI-F007",),
        ),
        "KB-URI-008-repair-missing-route-node-id": (
            replace(terminal, route_node_id=""),
            ("URI-F008",),
        ),
        "KB-URI-009-reviewer-before-flowguard": (
            replace(terminal, role_sequence=("Worker", "Reviewer", "FlowGuard")),
            ("URI-F009",),
        ),
        "KB-URI-010-worker-evidence-predates-contract": (
            replace(terminal, worker_result_generation=1),
            ("URI-F010", "URI-F019"),
        ),
        "KB-URI-011-mixed-gate-generations": (
            replace(historical, flowguard_evidence_generation=0),
            ("URI-F010",),
        ),
        "KB-URI-012-repeated-repair-missing-root": (
            replace(repeated, repair_root_id=""),
            ("URI-F011",),
        ),
        "KB-URI-013-repeated-repair-missing-previous-link": (
            replace(repeated, previous_repair_node_id=""),
            ("URI-F011",),
        ),
        "KB-URI-014-unaffected-sibling-dropped": (
            replace(
                historical,
                active_members_after=("node-work-repair-r1", "node-module-unaffected-a"),
                final_ledger_active_member_ids=("node-work-repair-r1", "node-module-unaffected-a"),
            ),
            ("URI-F012",),
        ),
        "KB-URI-015-unaffected-sibling-not-rebound": (
            replace(historical, unaffected_rebound_ids=("node-module-unaffected-a",)),
            ("URI-F013",),
        ),
        "KB-URI-016-final-ledger-omits-active-sibling": (
            replace(
                historical,
                final_ledger_active_member_ids=("node-work-repair-r1", "node-module-unaffected-a"),
            ),
            ("URI-F014",),
        ),
        "KB-URI-017-downstream-not-staled": (
            replace(historical, downstream_stale_ids=()),
            ("URI-F015",),
        ),
        "KB-URI-018-stale-downstream-not-replayed": (
            replace(historical, downstream_replayed_ids=()),
            ("URI-F016",),
        ),
        "KB-URI-019-terminal-contract-missing": (
            replace(terminal, terminal_contract_id="", terminal_contract_item_ids=()),
            ("URI-F017",),
        ),
        "KB-URI-020-terminal-item-not-projected": (
            replace(terminal, terminal_projected_item_ids=()),
            ("URI-F018",),
        ),
        "KB-URI-021-terminal-precontract-evidence-reused": (
            replace(
                terminal,
                current_generation=3,
                terminal_contract_generation=3,
                repair_contract_generation=3,
                worker_result_generation=2,
                flowguard_evidence_generation=2,
                reviewer_evidence_generation=2,
            ),
            ("URI-F010", "URI-F019"),
        ),
        "KB-URI-022-fourth-terminal-round-opened": (
            replace(terminal, terminal_round=4),
            ("URI-F020",),
        ),
        "KB-URI-023-parent-scope-not-materialized": (
            replace(parent, parent_scope_replaced=False),
            ("URI-F021",),
        ),
        "KB-URI-024-subtree-not-superseded": (
            replace(subtree, subtree_superseded=False),
            ("URI-F021",),
        ),
        "KB-URI-025-route-redesign-not-materialized": (
            replace(route, route_replaced=False),
            ("URI-F021",),
        ),
        "KB-URI-026-route-version-not-advanced": (
            replace(historical, route_version_after=1),
            ("URI-F022",),
        ),
        "KB-URI-027-complete-run-reopened": (
            replace(historical, run_status="complete", new_run_id=""),
            ("URI-F023",),
        ),
        "KB-URI-028-terminal-parallel-shortcut": (
            replace(terminal, parallel_terminal_shortcut=True),
            ("URI-F024",),
        ),
        "KB-URI-029-superseded-target-still-active": (
            replace(
                historical,
                active_members_after=(
                    "node-work",
                    "node-work-repair-r1",
                    "node-module-unaffected-a",
                    "node-module-unaffected-b",
                ),
                final_ledger_active_member_ids=(
                    "node-work",
                    "node-work-repair-r1",
                    "node-module-unaffected-a",
                    "node-module-unaffected-b",
                ),
            ),
            ("URI-F012", "URI-F025"),
        ),
        "KB-URI-030-terminal-replay-not-rerun": (
            replace(terminal, terminal_replay_completed=False),
            ("URI-F026",),
        ),
        "KB-URI-031-repair-contract-generation-missing": (
            replace(historical, repair_contract_generation=0),
            ("URI-F027", "URI-F010"),
        ),
        "KB-URI-032-unaffected-sibling-invalidated": (
            replace(
                historical,
                downstream_stale_ids=("dependent-of-node-work", "node-module-unaffected-a"),
                downstream_replayed_ids=("dependent-of-node-work", "node-module-unaffected-a"),
            ),
            ("URI-F015", "URI-F028"),
        ),
        "KB-URI-033-parent-replay-not-completed": (
            replace(parent, parent_replayed_node_ids=()),
            ("URI-F044",),
        ),
        "KB-URI-034-trigger-without-defect-observation": (
            replace(historical, defect_observation_id=""),
            ("URI-F029",),
        ),
        "KB-URI-035-waiver-without-authority": (
            replace(waiver, authority_ref=""),
            ("URI-F030",),
        ),
        "KB-URI-036-waiver-created-repair-work": (
            replace(
                waiver,
                repair_packet_created=True,
                repair_node_id="waiver-repair-node",
                packet_owner="Worker",
                route_node_id="waiver-repair-node",
                role_sequence=POST_WORK_ROLE_SEQUENCE,
            ),
            ("URI-F031",),
        ),
        "KB-URI-037-stop-created-repair-work": (
            replace(
                stop,
                repair_packet_created=True,
                repair_node_id="stop-repair-node",
                packet_owner="Worker",
                route_node_id="stop-repair-node",
                role_sequence=POST_WORK_ROLE_SEQUENCE,
            ),
            ("URI-F031",),
        ),
        "KB-URI-038-stop-did-not-terminate": (
            replace(stop, run_terminated=False, run_status="active"),
            ("URI-F032",),
        ),
        "KB-URI-039-child-parented-by-superseded-source": (
            replace(historical, repair_child_parent_ids=(historical.original_node_id,)),
            ("URI-F034",),
        ),
        "KB-URI-040-child-generation-stale": (
            replace(historical, repair_child_generations=(0,)),
            ("URI-F035",),
        ),
        "KB-URI-041-child-parented-by-inactive-replacement": (
            replace(historical, repair_child_parent_ids=("node-work-repair-inactive",)),
            ("URI-F034",),
        ),
        "KB-URI-042-terminal-disposition-generated-child": (
            replace(
                waiver,
                current_repair_generation=1,
                repair_child_ids=("illegal-waiver-child",),
                repair_child_parent_ids=("illegal-waiver-repair",),
                repair_child_generations=(1,),
            ),
            ("URI-F031",),
        ),
        "KB-URI-043-effect-committed-before-decision-gate": (
            replace(
                historical,
                decision_gate_sequence=(),
                decision_gate_current=False,
                decision_gate_accepted=False,
            ),
            ("URI-F036", "URI-F037"),
        ),
        "KB-URI-044-decision-review-reused-as-post-work-review": (
            replace(
                historical,
                post_work_reviewer_result_id=historical.decision_reviewer_result_id,
            ),
            ("URI-F038",),
        ),
        "KB-URI-045-rejected-gate-left-orphan-and-consumed-round": (
            replace(
                historical,
                decision_gate_accepted=False,
                decision_gate_rejected=True,
                staged_effect_status="staged",
                orphan_staged_effect=True,
                terminal_round_consumed_on_rejected_gate=True,
            ),
            ("URI-F039",),
        ),
        "KB-URI-046-waiver-entered-continue-repair-gate": (
            replace(
                waiver,
                decision_gate_sequence=DECISION_GATE_SEQUENCE,
                decision_gate_current=True,
                decision_gate_accepted=True,
                staged_effect_id="illegal-waiver-effect",
                staged_effect_status="committed",
                effect_committed_before_worker=True,
                worker_opened_after_effect_commit=True,
                decision_reviewer_result_id="illegal-waiver-decision-review",
                post_work_reviewer_result_id="illegal-waiver-post-review",
            ),
            ("URI-F040",),
        ),
        "KB-URI-047-repeated-repair-replaced-original-again": (
            replace(
                repeated,
                repairs_node_id=repeated.original_node_id,
                superseded_member_ids=(repeated.original_node_id,),
            ),
            ("URI-F004", "URI-F041"),
        ),
        "KB-URI-048-repeated-repair-reused-generation": (
            replace(
                repeated,
                current_repair_generation=repeated.previous_repair_generation,
            ),
            ("URI-F041",),
        ),
        "KB-URI-049-repeated-repair-lineage-cycle": (
            replace(
                repeated,
                repair_ancestor_node_ids=(
                    *repeated.repair_ancestor_node_ids,
                    repeated.repair_node_id,
                ),
            ),
            ("URI-F041",),
        ),
        "KB-URI-050-child-never-executed-or-accepted": (
            replace(
                historical,
                executed_repair_child_ids=(),
                accepted_repair_child_ids=(),
            ),
            ("URI-F042",),
        ),
        "KB-URI-051-child-omitted-from-terminal-targets": (
            replace(
                historical,
                terminal_target_node_ids=(historical.repair_node_id,),
            ),
            ("URI-F042",),
        ),
        "KB-URI-052-self-reported-impact-cone-disagrees-with-graph": (
            replace(
                historical,
                dependency_edges=historical.dependency_edges[:2],
            ),
            ("URI-F043",),
        ),
        "KB-URI-053-same-slot-parent-not-replayed": (
            replace(historical, parent_replayed_node_ids=()),
            ("URI-F044",),
        ),
        "KB-URI-054-terminal-run-bridge-reuses-old-run": (
            replace(
                _bad_base("pm_historical_defect", "repair_parent_scope", "bad.run-bridge"),
                new_run_id="run-complete-001",
            ),
            ("URI-F045",),
        ),
        "KB-URI-055-post-work-evidence-present-at-worker-open": (
            replace(
                stage_state(
                    RepairTrigger(
                        origin="pm_historical_defect",
                        requested_action="repair_same_slot",
                        case_id="bad.premature-post-work",
                    ),
                    "effect_committed_and_worker_open",
                ),
                role_sequence=POST_WORK_ROLE_SEQUENCE,
                worker_result_generation=1,
            ),
            ("URI-F046",),
        ),
        "KB-URI-056-rejected-gate-has-no-explicit-exits": (
            replace(
                stage_state(
                    RepairTrigger(
                        origin="pm_historical_defect",
                        requested_action="repair_same_slot",
                        case_id="bad.rejected-no-exit",
                    ),
                    REJECTED_GATE_STATUS,
                ),
                rejected_gate_exit_options=(),
            ),
            ("URI-F047",),
        ),
    }
    return cases


def bad_trigger(case_id: str) -> RepairTrigger:
    state, _expected = known_bad_cases()[case_id]
    return RepairTrigger(
        origin=state.trigger_origin,
        requested_action=state.repair_action,
        case_id=case_id,
        fault_case_id=case_id,
    )


def state_summary(state: State) -> dict[str, object]:
    return asdict(state)


__all__ = [
    "ACTION_CATALOG",
    "ACTION_REFINEMENT_MAP",
    "DECISION_GATE_SEQUENCE",
    "EXTERNAL_INPUTS",
    "FINDING_CATALOG",
    "GOOD_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "MODEL_ID",
    "POST_WORK_ROLE_SEQUENCE",
    "REPAIR_ACTIONS",
    "REJECTED_GATE_EXIT_OPTIONS",
    "REJECTED_GATE_STATUS",
    "REQUIRED_SAFE_LABELS",
    "SUBSTANTIVE_REPAIR_ACTIONS",
    "TERMINAL_DISPOSITION_ACTIONS",
    "TRIGGER_ORIGINS",
    "Action",
    "RepairTrigger",
    "State",
    "UnifiedRepairIntegrityBlock",
    "bad_trigger",
    "build_workflow",
    "canonical_state",
    "initial_state",
    "invariant_failures",
    "invariant_findings",
    "is_success",
    "known_bad_cases",
    "state_summary",
    "terminal_predicate",
]
