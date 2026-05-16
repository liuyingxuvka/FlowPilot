"""FlowGuard model for FlowPilot route mutation activation and display timing.

Risk intent brief:
- Prevent PM-added repair or replacement nodes from becoming visible current
  route state before the candidate route is checked and activated.
- Preserve PM freedom to choose a return repair, a replacement/supersede node,
  or a bounded branch-then-continue detour.
- Critical durable state: active route/frontier, candidate route topology,
  stale evidence invalidation, process/product/reviewer route checks, PM
  activation, current-node entry, and user-visible route display receipt.
- Adversarial branches include active flow overwrite before activation,
  frontier entering the candidate repair node too early, candidate route display
  before activation, missing topology strategy, forced return for replacement
  nodes, missing return target for return repairs, list-order Mermaid appending
  repair nodes after terminal stages, unresolved superseded nodes, stale
  evidence reuse, old current-node packet obligations blocking route recheck,
  generated-files-only display, and sealed-body leakage.
- Hard invariant: a mutation proposal is not the current route; only a checked
  and PM-activated route may become current, and only node entry may publish
  the new current route position to the user-visible route sign.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


RETURN_TO_ORIGINAL = "return_to_original"
SUPERSEDE_ORIGINAL = "supersede_original"
BRANCH_THEN_CONTINUE = "branch_then_continue"
SIBLING_BRANCH_REPLACEMENT = "sibling_branch_replacement"
TOPOLOGY_STRATEGIES = frozenset(
    {
        RETURN_TO_ORIGINAL,
        SUPERSEDE_ORIGINAL,
        BRANCH_THEN_CONTINUE,
        SIBLING_BRANCH_REPLACEMENT,
    }
)


@dataclass(frozen=True)
class Tick:
    """One route-mutation activation/display transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | complete
    holder: str = "controller"

    reviewer_block_recorded: bool = False
    pm_mutation_proposed: bool = False
    topology_strategy: str = "none"
    repair_node_id_declared: bool = False
    repair_of_node_id_declared: bool = False
    return_target_declared: bool = False
    superseded_nodes_declared: bool = False
    continue_target_declared: bool = False
    affected_sibling_nodes_declared: bool = False
    replay_scope_declared: bool = False

    active_route_overwritten_before_activation: bool = False
    frontier_entered_candidate_before_activation: bool = False
    candidate_route_displayed_as_current: bool = False

    stale_evidence_invalidated: bool = False
    old_current_node_packet_superseded: bool = False
    process_recheck_passed: bool = False
    product_recheck_passed: bool = False
    reviewer_recheck_passed: bool = False
    pm_activation_recorded: bool = False
    candidate_node_entry_recorded: bool = False
    same_scope_replay_rerun_after_mutation: bool = False
    final_ledger_started: bool = False

    route_visible_as_current: bool = False
    display_receipt_recorded: bool = False
    mermaid_topology_projected: bool = False
    repair_rendered_as_final_mainline: bool = False
    superseded_node_shown_as_pending: bool = False
    forced_return_for_supersede: bool = False
    old_sibling_evidence_reused_as_current: bool = False
    generated_files_only_display: bool = False
    sealed_body_boundary_preserved: bool = True


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _running(state: State, **changes: object) -> State:
    return replace(state, status="running", **changes)


def _proposal(
    state: State,
    *,
    label_holder: str,
    strategy: str,
    return_target: bool = False,
    superseded: bool = False,
    continue_target: bool = False,
    affected_siblings: bool = False,
    replay_scope: bool = False,
) -> State:
    return _running(
        state,
        holder=label_holder,
        pm_mutation_proposed=True,
        topology_strategy=strategy,
        repair_node_id_declared=True,
        repair_of_node_id_declared=True,
        return_target_declared=return_target,
        superseded_nodes_declared=superseded,
        continue_target_declared=continue_target,
        affected_sibling_nodes_declared=affected_siblings,
        replay_scope_declared=replay_scope,
    )


class RouteMutationActivationStep:
    """One route mutation activation/display transition.

    Input x State -> Set(Output x State)
    reads: active route/frontier, mutation proposal, stale evidence ledger,
      route-check reports, PM activation record, display receipt
    writes: candidate route topology, route-check pass facts, active route
      activation, current-node entry, user-visible route sign projection
    idempotency: repeated display or activation attempts do not make a draft
      route current before PM activation.
    """

    name = "RouteMutationActivationStep"
    input_description = "route-mutation activation/display tick"
    output_description = "one route mutation, check, activation, or display transition"
    reads = (
        "active_route",
        "execution_frontier",
        "candidate_route_topology",
        "stale_evidence_ledger",
        "route_check_reports",
        "display_receipt",
    )
    writes = (
        "candidate_route_draft",
        "route_mutation_record",
        "route_check_status",
        "active_route_activation",
        "current_node_entry",
        "user_visible_route_sign",
    )
    idempotency = "route-version scoped proposal, activation, and display"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "complete":
        return

    if not state.reviewer_block_recorded:
        yield Transition(
            "reviewer_block_records_route_mutation_need",
            _running(state, holder="human_like_reviewer", reviewer_block_recorded=True),
        )
        return

    if not state.pm_mutation_proposed:
        yield Transition(
            "pm_proposes_return_repair_candidate_route",
            _proposal(
                state,
                label_holder="project_manager",
                strategy=RETURN_TO_ORIGINAL,
                return_target=True,
            ),
        )
        yield Transition(
            "pm_proposes_supersede_replacement_candidate_route",
            _proposal(
                state,
                label_holder="project_manager",
                strategy=SUPERSEDE_ORIGINAL,
                superseded=True,
            ),
        )
        yield Transition(
            "pm_proposes_branch_then_continue_candidate_route",
            _proposal(
                state,
                label_holder="project_manager",
                strategy=BRANCH_THEN_CONTINUE,
                continue_target=True,
            ),
        )
        yield Transition(
            "pm_proposes_sibling_branch_replacement_candidate_route",
            _proposal(
                state,
                label_holder="project_manager",
                strategy=SIBLING_BRANCH_REPLACEMENT,
                affected_siblings=True,
                replay_scope=True,
            ),
        )
        return

    if not state.stale_evidence_invalidated:
        yield Transition(
            "controller_records_stale_evidence_before_route_recheck",
            _running(state, holder="controller", stale_evidence_invalidated=True),
        )
        return

    if not state.old_current_node_packet_superseded:
        yield Transition(
            "controller_supersedes_old_current_node_packet_for_route_mutation",
            _running(state, holder="controller", old_current_node_packet_superseded=True),
        )
        return

    if not state.process_recheck_passed:
        yield Transition(
            "process_flowguard_officer_simulates_candidate_route",
            _running(state, holder="process_flowguard_officer", process_recheck_passed=True),
        )
        return

    if not state.product_recheck_passed:
        yield Transition(
            "product_flowguard_officer_checks_candidate_route",
            _running(state, holder="product_flowguard_officer", product_recheck_passed=True),
        )
        return

    if not state.reviewer_recheck_passed:
        yield Transition(
            "human_like_reviewer_challenges_candidate_route",
            _running(state, holder="human_like_reviewer", reviewer_recheck_passed=True),
        )
        return

    if not state.pm_activation_recorded:
        yield Transition(
            "pm_activates_checked_candidate_route",
            _running(state, holder="project_manager", pm_activation_recorded=True),
        )
        return

    if not state.candidate_node_entry_recorded:
        yield Transition(
            "execution_frontier_enters_activated_mutation_node",
            _running(state, holder="controller", candidate_node_entry_recorded=True),
        )
        return

    if not state.same_scope_replay_rerun_after_mutation:
        yield Transition(
            "reviewer_reruns_same_scope_replay_after_route_mutation",
            _running(
                state,
                holder="human_like_reviewer",
                same_scope_replay_rerun_after_mutation=True,
            ),
        )
        return

    if not state.route_visible_as_current:
        yield Transition(
            "route_sign_displays_activated_current_mutation_node",
            _running(
                state,
                holder="controller",
                route_visible_as_current=True,
                display_receipt_recorded=True,
                mermaid_topology_projected=True,
            ),
        )
        return

    yield Transition(
        "route_mutation_activation_display_complete",
        replace(state, status="complete", holder="controller"),
    )


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []

    if state.pm_mutation_proposed:
        if state.topology_strategy not in TOPOLOGY_STRATEGIES:
            failures.append("route mutation proposal lacks an explicit topology strategy")
        if not state.repair_node_id_declared:
            failures.append("route mutation proposal lacks repair_node_id")
        if not state.repair_of_node_id_declared:
            failures.append("route mutation proposal lacks repair_of_node_id")
        if state.topology_strategy == RETURN_TO_ORIGINAL and not state.return_target_declared:
            failures.append("return_to_original mutation lacks repair_return_to_node_id")
        if state.topology_strategy == SUPERSEDE_ORIGINAL:
            if not state.superseded_nodes_declared:
                failures.append("supersede_original mutation lacks superseded_nodes")
            if state.forced_return_for_supersede or state.return_target_declared:
                failures.append("supersede_original mutation was incorrectly forced to return to the old node")
        if state.topology_strategy == BRANCH_THEN_CONTINUE and not state.continue_target_declared:
            failures.append("branch_then_continue mutation lacks continue_after_node_id")
        if state.topology_strategy == SIBLING_BRANCH_REPLACEMENT:
            if not state.affected_sibling_nodes_declared:
                failures.append("sibling_branch_replacement mutation lacks affected sibling nodes")
            if not state.replay_scope_declared:
                failures.append("sibling_branch_replacement mutation lacks replay scope")

    if state.active_route_overwritten_before_activation:
        failures.append("candidate route overwrote active flow.json before checked PM activation")
    if state.frontier_entered_candidate_before_activation and not state.pm_activation_recorded:
        failures.append("execution frontier entered candidate node before route activation")
    if state.candidate_route_displayed_as_current and not state.pm_activation_recorded:
        failures.append("candidate repair route was displayed as current before activation")

    if state.pm_activation_recorded:
        if not state.stale_evidence_invalidated:
            failures.append("PM activated candidate route before stale evidence was invalidated")
        if not state.old_current_node_packet_superseded:
            failures.append("PM activated candidate route while the old current-node packet still blocked recheck")
        if not state.process_recheck_passed:
            failures.append("PM activated candidate route before process FlowGuard recheck")
        if not state.product_recheck_passed:
            failures.append("PM activated candidate route before product FlowGuard recheck")
        if not state.reviewer_recheck_passed:
            failures.append("PM activated candidate route before reviewer route challenge")

    if state.route_visible_as_current:
        if not state.pm_activation_recorded:
            failures.append("route sign displayed mutation route before PM activation")
        if not state.candidate_node_entry_recorded:
            failures.append("route sign displayed mutation position before execution entered the activated node")
        if not state.display_receipt_recorded or state.generated_files_only_display:
            failures.append("route sign display used generated files without user-visible receipt")
        if not state.mermaid_topology_projected:
            failures.append("route sign displayed mutation without explicit topology projection")
        if state.repair_rendered_as_final_mainline:
            failures.append("repair node was rendered as a final sequential mainline stage")
        if state.superseded_node_shown_as_pending:
            failures.append("superseded old node remained visible as a pending or active obligation")

    if state.old_sibling_evidence_reused_as_current:
        failures.append("old sibling evidence was reused as current proof after replacement")
    if state.process_recheck_passed and not state.old_current_node_packet_superseded:
        failures.append("route recheck started while the old current-node packet still blocked PM work")
    if state.final_ledger_started and not state.same_scope_replay_rerun_after_mutation:
        failures.append("final ledger started before same-scope replay after route mutation")
    if state.status == "complete" and not state.same_scope_replay_rerun_after_mutation:
        failures.append("route mutation completed before same-scope replay rerun")

    if not state.sealed_body_boundary_preserved:
        failures.append("route mutation display weakened the sealed packet/result body boundary")

    return failures


def route_mutation_activation_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="route_mutation_activation_display_order",
        description=(
            "Route mutations remain proposals until topology is explicit, stale "
            "evidence is invalidated, process/product/reviewer checks pass, PM "
            "activates the route, execution enters the new node, and the route "
            "sign renders explicit mutation topology with a visible receipt."
        ),
        predicate=route_mutation_activation_invariant,
    ),
)


def _proposal_state(strategy: str, **changes: object) -> State:
    base = State(
        status="running",
        holder="project_manager",
        reviewer_block_recorded=True,
        pm_mutation_proposed=True,
        topology_strategy=strategy,
        repair_node_id_declared=True,
        repair_of_node_id_declared=True,
        return_target_declared=strategy == RETURN_TO_ORIGINAL,
        superseded_nodes_declared=strategy == SUPERSEDE_ORIGINAL,
        continue_target_declared=strategy == BRANCH_THEN_CONTINUE,
        affected_sibling_nodes_declared=strategy == SIBLING_BRANCH_REPLACEMENT,
        replay_scope_declared=strategy == SIBLING_BRANCH_REPLACEMENT,
    )
    return replace(base, **changes)


def _activated_display_state(strategy: str, **changes: object) -> State:
    base = _proposal_state(
        strategy,
        stale_evidence_invalidated=True,
        old_current_node_packet_superseded=True,
        process_recheck_passed=True,
        product_recheck_passed=True,
        reviewer_recheck_passed=True,
        pm_activation_recorded=True,
        candidate_node_entry_recorded=True,
        same_scope_replay_rerun_after_mutation=True,
        route_visible_as_current=True,
        display_receipt_recorded=True,
        mermaid_topology_projected=True,
    )
    return replace(base, **changes)


def hazard_states() -> dict[str, State]:
    return {
        "active_flow_overwritten_before_activation": _proposal_state(
            RETURN_TO_ORIGINAL,
            active_route_overwritten_before_activation=True,
        ),
        "frontier_entered_candidate_before_activation": _proposal_state(
            RETURN_TO_ORIGINAL,
            frontier_entered_candidate_before_activation=True,
        ),
        "candidate_route_displayed_before_activation": _proposal_state(
            RETURN_TO_ORIGINAL,
            candidate_route_displayed_as_current=True,
        ),
        "activation_without_process_recheck": _proposal_state(
            RETURN_TO_ORIGINAL,
            stale_evidence_invalidated=True,
            old_current_node_packet_superseded=True,
            product_recheck_passed=True,
            reviewer_recheck_passed=True,
            pm_activation_recorded=True,
        ),
        "activation_without_product_or_reviewer_recheck": _proposal_state(
            RETURN_TO_ORIGINAL,
            stale_evidence_invalidated=True,
            old_current_node_packet_superseded=True,
            process_recheck_passed=True,
            pm_activation_recorded=True,
        ),
        "missing_topology_strategy": _proposal_state(
            "none",
            return_target_declared=False,
            superseded_nodes_declared=False,
            continue_target_declared=False,
        ),
        "supersede_original_forced_to_return": _proposal_state(
            SUPERSEDE_ORIGINAL,
            forced_return_for_supersede=True,
        ),
        "return_repair_without_return_target": _proposal_state(
            RETURN_TO_ORIGINAL,
            return_target_declared=False,
        ),
        "sibling_replacement_without_affected_siblings": _proposal_state(
            SIBLING_BRANCH_REPLACEMENT,
            affected_sibling_nodes_declared=False,
        ),
        "sibling_replacement_without_replay_scope": _proposal_state(
            SIBLING_BRANCH_REPLACEMENT,
            replay_scope_declared=False,
        ),
        "old_sibling_evidence_reused_after_replacement": _activated_display_state(
            SIBLING_BRANCH_REPLACEMENT,
            old_sibling_evidence_reused_as_current=True,
        ),
        "route_recheck_before_old_packet_superseded": _proposal_state(
            RETURN_TO_ORIGINAL,
            stale_evidence_invalidated=True,
            process_recheck_passed=True,
        ),
        "final_scan_before_same_scope_replay_after_mutation": _proposal_state(
            RETURN_TO_ORIGINAL,
            stale_evidence_invalidated=True,
            old_current_node_packet_superseded=True,
            process_recheck_passed=True,
            product_recheck_passed=True,
            reviewer_recheck_passed=True,
            pm_activation_recorded=True,
            candidate_node_entry_recorded=True,
            final_ledger_started=True,
        ),
        "repair_rendered_as_final_mainline": _activated_display_state(
            RETURN_TO_ORIGINAL,
            repair_rendered_as_final_mainline=True,
        ),
        "superseded_node_visible_as_pending": _activated_display_state(
            SUPERSEDE_ORIGINAL,
            superseded_node_shown_as_pending=True,
        ),
        "stale_evidence_reused_before_activation": _proposal_state(
            RETURN_TO_ORIGINAL,
            old_current_node_packet_superseded=True,
            process_recheck_passed=True,
            product_recheck_passed=True,
            reviewer_recheck_passed=True,
            pm_activation_recorded=True,
        ),
        "generated_files_only_display": _activated_display_state(
            RETURN_TO_ORIGINAL,
            display_receipt_recorded=False,
            generated_files_only_display=True,
        ),
        "sealed_body_boundary_broken": _activated_display_state(
            RETURN_TO_ORIGINAL,
            sealed_body_boundary_preserved=False,
        ),
    }


def build_workflow() -> Workflow:
    return Workflow((RouteMutationActivationStep(),), name="flowpilot_route_mutation_activation")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status == "complete"


def is_success(state: State) -> bool:
    return state.status == "complete"


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 32


__all__ = [
    "BRANCH_THEN_CONTINUE",
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "RETURN_TO_ORIGINAL",
    "SIBLING_BRANCH_REPLACEMENT",
    "SUPERSEDE_ORIGINAL",
    "TOPOLOGY_STRATEGIES",
    "Action",
    "RouteMutationActivationStep",
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
]
