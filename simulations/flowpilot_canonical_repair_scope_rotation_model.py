"""FlowGuard model for FlowPilot canonical repair-scope rotation.

Risk intent:
- Prevent PM repair loops from marking a blocker repaired without a fresh
  executable packet.
- Collapse the PM repair menu to one current contract.
- Replace current, parent, or route scope cleanly instead of mutating an old
  node in place.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_canonical_repair_scope_rotation"
MAX_SEQUENCE_LENGTH = 13
CURRENT_PM_REPAIR_DECISIONS = (
    "break_glass",
    "repair_current_scope",
    "repair_parent_scope",
    "redesign_route",
    "waive_with_authority",
    "stop_for_user",
)
REMOVED_PM_REPAIR_DECISIONS = (
    "same_node_repair",
    "sender_reissue",
    "collect_more_evidence",
    "mutate_route",
    "quarantine_evidence",
)
NONTERMINAL_REPAIRS = {
    "repair_current_scope",
    "repair_parent_scope",
    "redesign_route",
}
TERMINAL_REPAIRS = {"waive_with_authority", "stop_for_user"}


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | complete | blocked
    trigger_origin: str = "none"
    blocker_detected: bool = False
    historical_defect_recorded: bool = False
    historical_defect_id: str = ""
    historical_target_evidence_present: bool = False
    impact_frontier_declared: bool = False
    menu_declared: bool = False
    old_decisions_rejected: bool = False
    pm_decision: str = "none"
    authority_ref_present: bool = False
    source_id: str = ""
    blocker_id: str = ""
    repair_subject_id: str = ""
    fresh_packet_id: str = ""
    fresh_packet_current_open: bool = False
    transaction_recorded: bool = False
    old_scope_superseded: bool = False
    replacement_scope_created: bool = False
    parent_found: bool = False
    descendants_superseded: bool = False
    parent_repair_contract_present: bool = False
    repair_child_specs_count: int = 0
    active_repair_child_nodes_created: int = 0
    inherited_child_history_recorded: bool = False
    inherited_children_current: bool = False
    parent_repair_inherited_only_replay: bool = False
    route_plan_packet_present: bool = False
    flowguard_scan_passed: bool = False
    reviewer_scan_passed: bool = False
    route_version_switched: bool = False
    blocker_repair_packet_open: bool = False
    blocker_terminal: bool = False
    same_node_repair_in_place: bool = False
    old_decision_accepted: bool = False
    same_lineage_attempt_count: int = 0
    repair_loop_break_glass_required: bool = False
    break_glass_routed_to_controller: bool = False


@dataclass(frozen=True)
class Tick:
    """One canonical repair-scope transition."""


@dataclass(frozen=True)
class Action:
    label: str


class Transition(NamedTuple):
    label: str
    state: State


REQUIRED_SAFE_LABELS = (
    "record_current_blocker",
    "record_pm_historical_defect",
    "declare_current_pm_menu",
    "reject_removed_pm_decisions",
    "pm_selects_break_glass",
    "runtime_routes_break_glass_to_controller",
    "pm_selects_repair_current_scope",
    "runtime_replaces_current_scope",
    "runtime_records_fresh_packet_transaction",
    "runtime_opens_blocker_repair_packet",
    "runtime_opens_historical_repair_packet",
    "complete_nonterminal_repair_rotation",
    "pm_selects_repair_parent_scope",
    "runtime_replaces_parent_scope",
    "pm_selects_redesign_route",
    "runtime_stage_route_plan_scan",
    "runtime_activates_redesigned_route",
    "pm_selects_authorized_waiver",
    "pm_selects_stop_for_user",
)


def initial_state() -> State:
    return State()


class CanonicalRepairScopeRotationStep:
    name = "CanonicalRepairScopeRotationStep"
    input_description = "one PM repair/control-plane tick"
    output_description = "one ordered current-contract repair transition"
    reads = ("repair_trigger", "semantic_blocker", "historical_defect", "pm_repair_decision", "route_nodes", "packets")
    writes = ("repair_transaction", "route_mutation", "blocker_status")
    idempotency = "repair-subject-id plus source-id scoped repair transaction"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(output=Action(transition.label), new_state=transition.state, label=transition.label)


def _with_current_transaction(state: State) -> State:
    return replace(
        state,
        source_id=state.source_id or "node-001",
        blocker_id=state.blocker_id,
        repair_subject_id=state.repair_subject_id
        or state.blocker_id
        or state.historical_defect_id,
        fresh_packet_id="packet-001-repair",
        fresh_packet_current_open=True,
        transaction_recorded=True,
    )


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"blocked", "complete"}:
        return ()
    failures = invariant_failures(state)
    if failures:
        return (Transition("blocked_on_repair_scope_invariant", replace(state, status="blocked")),)
    if state.status == "new":
        return (
            Transition(
                "record_current_blocker",
                replace(
                    state,
                    status="running",
                    trigger_origin="reviewer_or_system_blocker",
                    blocker_detected=True,
                    blocker_id="blocker-001",
                    repair_subject_id="blocker-001",
                ),
            ),
            Transition(
                "record_pm_historical_defect",
                replace(
                    state,
                    status="running",
                    trigger_origin="pm_historical_defect",
                    historical_defect_recorded=True,
                    historical_defect_id="historical-defect-001",
                    historical_target_evidence_present=True,
                    impact_frontier_declared=True,
                    source_id="node-001",
                    repair_subject_id="historical-defect-001",
                ),
            ),
        )
    if not state.menu_declared:
        return (Transition("declare_current_pm_menu", replace(state, menu_declared=True)),)
    if not state.old_decisions_rejected:
        return (Transition("reject_removed_pm_decisions", replace(state, old_decisions_rejected=True)),)
    if state.pm_decision == "none":
        blocker_id = state.blocker_id if state.trigger_origin == "reviewer_or_system_blocker" else ""
        return (
            Transition(
                "pm_selects_break_glass",
                replace(state, pm_decision="break_glass", blocker_id=blocker_id),
            ),
            Transition(
                "pm_selects_repair_current_scope",
                replace(
                    state,
                    pm_decision="repair_current_scope",
                    source_id=state.source_id or "node-001",
                    blocker_id=blocker_id,
                ),
            ),
            Transition(
                "pm_selects_repair_parent_scope",
                replace(
                    state,
                    pm_decision="repair_parent_scope",
                    source_id="node-001",
                    blocker_id=blocker_id,
                    parent_found=True,
                    parent_repair_contract_present=True,
                    repair_child_specs_count=1,
                ),
            ),
            Transition(
                "pm_selects_redesign_route",
                replace(state, pm_decision="redesign_route", source_id="route-v1", blocker_id=blocker_id),
            ),
            Transition(
                "pm_selects_authorized_waiver",
                replace(
                    state,
                    pm_decision="waive_with_authority",
                    blocker_id=blocker_id,
                    authority_ref_present=True,
                    blocker_terminal=True,
                    status="complete",
                ),
            ),
            Transition(
                "pm_selects_stop_for_user",
                replace(state, pm_decision="stop_for_user", blocker_id=blocker_id, blocker_terminal=True, status="complete"),
            ),
        )
    if state.pm_decision == "break_glass" and not state.break_glass_routed_to_controller:
        return (
            Transition(
                "runtime_routes_break_glass_to_controller",
                replace(state, break_glass_routed_to_controller=True, status="complete"),
            ),
        )
    if state.pm_decision == "repair_current_scope" and not state.replacement_scope_created:
        return (
            Transition(
                "runtime_replaces_current_scope",
                replace(state, old_scope_superseded=True, replacement_scope_created=True),
            ),
        )
    if state.pm_decision == "repair_parent_scope" and not state.replacement_scope_created:
        return (
            Transition(
                "runtime_replaces_parent_scope",
                replace(
                    state,
                    old_scope_superseded=True,
                    replacement_scope_created=True,
                    descendants_superseded=True,
                    active_repair_child_nodes_created=1,
                    inherited_child_history_recorded=True,
                ),
            ),
        )
    if state.pm_decision == "redesign_route" and not state.route_plan_packet_present:
        return (
            Transition(
                "runtime_stage_route_plan_scan",
                replace(
                    state,
                    route_plan_packet_present=True,
                    flowguard_scan_passed=True,
                    reviewer_scan_passed=True,
                ),
            ),
        )
    if state.pm_decision == "redesign_route" and not state.route_version_switched:
        return (
            Transition(
                "runtime_activates_redesigned_route",
                replace(state, old_scope_superseded=True, replacement_scope_created=True, route_version_switched=True),
            ),
        )
    if state.pm_decision in NONTERMINAL_REPAIRS and state.replacement_scope_created and not state.transaction_recorded:
        return (Transition("runtime_records_fresh_packet_transaction", _with_current_transaction(state)),)
    if state.pm_decision in NONTERMINAL_REPAIRS and state.transaction_recorded and not state.blocker_repair_packet_open:
        label = (
            "runtime_opens_historical_repair_packet"
            if state.trigger_origin == "pm_historical_defect"
            else "runtime_opens_blocker_repair_packet"
        )
        return (
            Transition(
                label,
                replace(state, blocker_repair_packet_open=True),
            ),
        )
    if state.pm_decision in NONTERMINAL_REPAIRS and state.blocker_repair_packet_open:
        return (Transition("complete_nonterminal_repair_rotation", replace(state, status="complete")),)
    return ()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status != "new" and state.trigger_origin not in {
        "reviewer_or_system_blocker",
        "pm_historical_defect",
    }:
        failures.append("repair trigger origin is missing or unsupported")
    if state.trigger_origin == "reviewer_or_system_blocker":
        if not state.blocker_detected or not state.blocker_id:
            failures.append("reviewer/system repair trigger lacks blocker evidence")
    if state.trigger_origin == "pm_historical_defect":
        if not state.historical_defect_recorded or not state.historical_defect_id:
            failures.append("PM historical repair lacks a structured defect identity")
        if not state.historical_target_evidence_present:
            failures.append("PM historical repair lacks target defect evidence")
        if not state.impact_frontier_declared:
            failures.append("PM historical repair lacks an affected frontier")
        if state.blocker_id or state.blocker_detected:
            failures.append("PM historical repair fabricated a blocker prerequisite")
    if state.menu_declared and not set(CURRENT_PM_REPAIR_DECISIONS).isdisjoint(REMOVED_PM_REPAIR_DECISIONS):
        failures.append("current PM repair menu overlaps removed decisions")
    if state.old_decision_accepted:
        failures.append("removed PM repair decision was accepted")
    if state.pm_decision in REMOVED_PM_REPAIR_DECISIONS:
        failures.append("removed PM repair decision reached runtime application")
    if state.same_node_repair_in_place:
        failures.append("same-node repair-in-place path survived")
    if state.pm_decision in NONTERMINAL_REPAIRS and state.blocker_repair_packet_open:
        if not state.fresh_packet_id:
            failures.append("repair_packet_open without fresh_packet_id")
        if not state.fresh_packet_current_open:
            failures.append("repair_packet_open without current open fresh packet")
        if not state.transaction_recorded:
            failures.append("repair_packet_open without repair transaction")
        if not state.source_id or not state.repair_subject_id:
            failures.append("repair transaction missing source_id or repair_subject_id")
        if state.trigger_origin == "reviewer_or_system_blocker" and not state.blocker_id:
            failures.append("blocker-backed repair transaction missing blocker_id")
    if state.pm_decision in {"repair_current_scope", "repair_parent_scope"} and state.blocker_repair_packet_open:
        if not (state.old_scope_superseded and state.replacement_scope_created):
            failures.append("scope repair opened without superseded old scope and replacement scope")
    if state.pm_decision == "repair_parent_scope":
        if state.replacement_scope_created and not state.parent_repair_contract_present:
            failures.append("parent repair replacement accepted without repair_parent_scope_contract")
        if state.replacement_scope_created and state.repair_child_specs_count <= 0:
            failures.append("parent repair replacement accepted without repair_child_specs")
        if state.replacement_scope_created and state.active_repair_child_nodes_created <= 0:
            failures.append("parent repair replacement parent has no active repair child nodes")
        if state.replacement_scope_created and not state.inherited_child_history_recorded:
            failures.append("parent repair replacement failed to record inherited child history")
        if state.inherited_children_current:
            failures.append("parent repair kept inherited children as current closure path")
        if state.parent_repair_inherited_only_replay:
            failures.append("parent repair replay closed from inherited history without current repair child result")
        if state.replacement_scope_created and not state.parent_found:
            failures.append("parent repair guessed a parent scope")
        if state.blocker_repair_packet_open and not state.descendants_superseded:
            failures.append("parent repair kept descendants current")
    if state.same_lineage_attempt_count >= 5 and not state.repair_loop_break_glass_required:
        failures.append("same repair dossier reached five consecutive repair nodes without break-glass")
    if state.pm_decision == "redesign_route":
        if state.route_version_switched and not (state.route_plan_packet_present and state.flowguard_scan_passed and state.reviewer_scan_passed):
            failures.append("route redesign activated without strict route plan and scans")
        if state.blocker_repair_packet_open and not state.route_version_switched:
            failures.append("route redesign opened blocker before route activation")
    if state.pm_decision == "waive_with_authority":
        if state.blocker_terminal and not state.authority_ref_present:
            failures.append("waiver terminal state lacks authority reference")
        if state.fresh_packet_id or state.blocker_repair_packet_open:
            failures.append("authorized waiver created a repair packet")
    if state.pm_decision == "break_glass":
        if state.fresh_packet_id or state.blocker_repair_packet_open:
            failures.append("break_glass created a repair packet")
        if state.status == "complete" and not state.break_glass_routed_to_controller:
            failures.append("break_glass completed without controller control-plane route")
    if state.pm_decision == "stop_for_user":
        if state.fresh_packet_id or state.blocker_repair_packet_open:
            failures.append("stop_for_user created a repair packet")
    if state.status == "complete" and not is_success(state):
        failures.append("completion claimed before repair-scope obligations were satisfied")
    return failures


def invariant(state: State, trace: object) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="canonical_repair_scope_rotation_invariants",
        description=(
            "PM repair decisions use exactly the current menu, "
            "removed decisions are rejected, nonterminal repair opens only "
            "after a fresh current executable packet exists, parent repair "
            "uses a structured child-spec contract, abandons descendants into "
            "history, creates active repair children, route redesign is scanned before activation, "
            "and terminal/control-plane exit decisions create no packet."
        ),
        predicate=invariant,
    ),
)
EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((CanonicalRepairScopeRotationStep(),), name=MODEL_ID)


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return state.status in {"complete", "blocked"}


def is_success(state: State) -> bool:
    if state.status != "complete":
        return False
    trigger_ready = (
        state.trigger_origin == "reviewer_or_system_blocker"
        and state.blocker_detected
        and bool(state.blocker_id)
    ) or (
        state.trigger_origin == "pm_historical_defect"
        and state.historical_defect_recorded
        and bool(state.historical_defect_id)
        and state.historical_target_evidence_present
        and state.impact_frontier_declared
        and not state.blocker_id
    )
    if not (trigger_ready and state.menu_declared and state.old_decisions_rejected):
        return False
    if state.pm_decision in NONTERMINAL_REPAIRS:
        if not (
            state.old_scope_superseded
            and state.replacement_scope_created
            and state.transaction_recorded
            and state.source_id
            and state.repair_subject_id
            and state.fresh_packet_id
            and state.fresh_packet_current_open
            and state.blocker_repair_packet_open
        ):
            return False
        if state.pm_decision == "repair_parent_scope" and not (
            state.parent_found
            and state.descendants_superseded
            and state.parent_repair_contract_present
            and state.repair_child_specs_count > 0
            and state.active_repair_child_nodes_created > 0
            and state.inherited_child_history_recorded
            and not state.inherited_children_current
            and not state.parent_repair_inherited_only_replay
        ):
            return False
        if state.pm_decision == "redesign_route" and not (
            state.route_plan_packet_present
            and state.flowguard_scan_passed
            and state.reviewer_scan_passed
            and state.route_version_switched
        ):
            return False
        return True
    if state.pm_decision == "waive_with_authority":
        return state.authority_ref_present and state.blocker_terminal and not state.fresh_packet_id
    if state.pm_decision == "stop_for_user":
        return state.blocker_terminal and not state.fresh_packet_id
    if state.pm_decision == "break_glass":
        return state.break_glass_routed_to_controller and not state.fresh_packet_id
    return False


def target_state() -> State:
    return replace(
        initial_state(),
        status="complete",
        trigger_origin="reviewer_or_system_blocker",
        blocker_detected=True,
        menu_declared=True,
        old_decisions_rejected=True,
        pm_decision="repair_current_scope",
        source_id="node-001",
        blocker_id="blocker-001",
        repair_subject_id="blocker-001",
        fresh_packet_id="packet-001-repair",
        fresh_packet_current_open=True,
        transaction_recorded=True,
        old_scope_superseded=True,
        replacement_scope_created=True,
        blocker_repair_packet_open=True,
    )


def historical_target_state() -> State:
    return replace(
        target_state(),
        trigger_origin="pm_historical_defect",
        blocker_detected=False,
        blocker_id="",
        historical_defect_recorded=True,
        historical_defect_id="historical-defect-001",
        historical_target_evidence_present=True,
        impact_frontier_declared=True,
        repair_subject_id="historical-defect-001",
    )


def hazard_states() -> dict[str, State]:
    base = target_state()
    historical_base = historical_target_state()
    route_base = replace(
        base,
        pm_decision="redesign_route",
        source_id="route-v1",
        route_plan_packet_present=True,
        flowguard_scan_passed=True,
        reviewer_scan_passed=True,
        route_version_switched=True,
    )
    parent_base = replace(
        base,
        pm_decision="repair_parent_scope",
        parent_found=True,
        descendants_superseded=True,
        parent_repair_contract_present=True,
        repair_child_specs_count=1,
        active_repair_child_nodes_created=1,
        inherited_child_history_recorded=True,
    )
    return {
        "pm_historical_defect_forced_through_blocker": replace(
            historical_base,
            blocker_detected=True,
            blocker_id="fabricated-blocker-001",
        ),
        "pm_historical_defect_missing_target_evidence": replace(
            historical_base,
            historical_target_evidence_present=False,
        ),
        "pm_historical_defect_missing_impact_frontier": replace(
            historical_base,
            impact_frontier_declared=False,
        ),
        "removed_decision_reached_runtime": replace(base, pm_decision="same_node_repair"),
        "same_node_repair_in_place_survived": replace(base, same_node_repair_in_place=True),
        "repair_packet_open_without_fresh_packet": replace(base, fresh_packet_id=""),
        "repair_packet_open_without_current_open_packet": replace(base, fresh_packet_current_open=False),
        "repair_packet_open_without_transaction": replace(base, transaction_recorded=False),
        "parent_repair_guessed_parent": replace(parent_base, parent_found=False),
        "parent_repair_missing_contract": replace(parent_base, parent_repair_contract_present=False),
        "parent_repair_missing_child_specs": replace(parent_base, repair_child_specs_count=0),
        "parent_repair_empty_replacement_parent": replace(parent_base, active_repair_child_nodes_created=0),
        "parent_repair_missing_inherited_history": replace(parent_base, inherited_child_history_recorded=False),
        "parent_repair_inherited_children_current": replace(parent_base, inherited_children_current=True),
        "parent_repair_inherited_only_replay": replace(parent_base, parent_repair_inherited_only_replay=True),
        "parent_repair_kept_descendants_current": replace(parent_base, descendants_superseded=False),
        "same_repair_dossier_loop_without_break_glass": replace(
            base,
            same_lineage_attempt_count=5,
            repair_loop_break_glass_required=False,
        ),
        "route_redesign_without_plan": replace(route_base, route_plan_packet_present=False),
        "route_redesign_without_flowguard_scan": replace(route_base, flowguard_scan_passed=False),
        "waiver_without_authority": replace(
            base,
            pm_decision="waive_with_authority",
            authority_ref_present=False,
            blocker_terminal=True,
            fresh_packet_id="",
            blocker_repair_packet_open=False,
        ),
        "terminal_stop_created_packet": replace(
            base,
            pm_decision="stop_for_user",
            blocker_terminal=True,
            fresh_packet_id="packet-stop-should-not-exist",
            blocker_repair_packet_open=False,
        ),
        "break_glass_created_packet": replace(
            base,
            pm_decision="break_glass",
            break_glass_routed_to_controller=True,
            fresh_packet_id="packet-break-glass-should-not-exist",
            blocker_repair_packet_open=False,
        ),
        "break_glass_completed_without_controller_route": replace(
            base,
            pm_decision="break_glass",
            break_glass_routed_to_controller=False,
            fresh_packet_id="",
            blocker_repair_packet_open=False,
        ),
    }


def state_summary(state: State) -> dict[str, object]:
    return state.__dict__.copy()
