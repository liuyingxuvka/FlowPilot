"""FlowGuard model for FlowPilot route display projection lifecycle.

Risk intent brief:
- Prevent FlowPilot from showing a stale startup ``route=unknown`` sign or a
  compressed display-plan bullet list after the PM has authored a real route.
- Protect the canonical route/frontier/snapshot authority boundary: Controller
  may display derived route signs, but it may not invent route nodes from chat
  history or expose sealed packet/result body content.
- Critical durable state: route draft or active route, execution frontier,
  route_state_snapshot, display_plan, user-flow-diagram Markdown/Mermaid,
  Cockpit route-map source, and user_dialog_display_ledger.
- Adversarial branches include draft-only routes without flow.json, node_id/id
  alias drift, active_route_id/active_node_id alias drift, bullet-list chat
  fallback after route draft, stale startup Mermaid, generated files without a
  visible receipt, Cockpit/chat source drift, checklist loss, status conflation,
  and accidental internal evidence/source-field display.
- Hard invariant: once a route source exists, every user-visible route map must
  be derived from the canonical route/frontier/snapshot source and rendered as
  a Mermaid route sign unless a degraded Mermaid source is explicitly recorded.
- Blindspot: this is a display-control model. It does not render or visually
  inspect Mermaid; runtime tests and live conformance cover concrete files.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


SCENARIOS = (
    "startup no route",
    "PM writes route draft",
    "PM activates reviewed route",
    "major node entry/current node starts",
    "current node completes and moves to next",
    "route mutation or review-failure repair return",
    "Cockpit unavailable, chat fallback required",
    "Cockpit available, same graph source used by UI and chat fallback",
)


@dataclass(frozen=True)
class Tick:
    """One route-display projection transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | complete
    holder: str = "controller"
    steps: int = 0

    startup_displayed: bool = False
    route_phase: str = "startup"  # startup | draft | active | node_entry | node_complete | repair_return
    route_source_exists: bool = False
    route_source_kind: str = "none"  # none | draft | active | snapshot
    route_source_is_canonical: bool = True
    controller_invented_nodes: bool = False
    route_node_aliases_supported: bool = False
    frontier_aliases_supported: bool = False
    draft_route_fallback_supported: bool = False
    snapshot_fallback_supported: bool = False
    route_nodes_real: bool = False
    route_checklists_preserved: bool = False
    route_statuses_distinct: bool = True
    display_plan_preserved_native_projection: bool = True
    display_plan_only_source: bool = False

    route_generation: int = 0
    diagram_generation: int = 0
    visible_generation: int = 0
    diagram_written: bool = False
    mermaid_source_available: bool = False
    mermaid_route_unknown: bool = False
    mermaid_node_unknown: bool = False
    mermaid_uses_route_nodes: bool = False
    mermaid_uses_canonical_source: bool = False
    mermaid_degraded_reason_recorded: bool = False

    chat_fallback_required: bool = True
    cockpit_available: bool = False
    chat_display_kind: str = "none"  # none | bullet | mermaid | degraded
    cockpit_display_kind: str = "none"  # none | route_map | degraded
    same_graph_source_for_chat_and_cockpit: bool = True
    user_dialog_display_ledger_recorded: bool = False
    cockpit_receipt_recorded: bool = False
    generated_files_only: bool = False

    sealed_body_boundary_preserved: bool = True
    internal_source_fields_visible: bool = False
    evidence_table_visible: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _inc(state: State, **changes: object) -> State:
    return replace(state, steps=state.steps + 1, status="running", **changes)


def _route_dirty(state: State, *, phase: str, source_kind: str, cockpit_available: bool | None = None) -> State:
    return _inc(
        state,
        route_phase=phase,
        route_source_exists=True,
        route_source_kind=source_kind,
        route_source_is_canonical=True,
        route_node_aliases_supported=True,
        frontier_aliases_supported=True,
        draft_route_fallback_supported=True,
        snapshot_fallback_supported=True,
        route_nodes_real=True,
        route_checklists_preserved=True,
        route_statuses_distinct=True,
        route_generation=state.route_generation + 1,
        diagram_generation=state.diagram_generation,
        visible_generation=state.visible_generation,
        mermaid_source_available=False,
        mermaid_route_unknown=True,
        mermaid_node_unknown=True,
        mermaid_uses_route_nodes=False,
        mermaid_uses_canonical_source=False,
        chat_display_kind="none",
        cockpit_display_kind="none",
        user_dialog_display_ledger_recorded=False,
        cockpit_receipt_recorded=False,
        generated_files_only=False,
        cockpit_available=state.cockpit_available if cockpit_available is None else cockpit_available,
    )


class RouteDisplayProjectionStep:
    """One FlowPilot route display projection transition.

    Input x State -> Set(Output x State)
    reads: route draft or active route, execution_frontier, route_state_snapshot,
      display_plan, diagram files, Cockpit/chat display receipts
    writes: user-flow-diagram Markdown/Mermaid/display packet, user dialog
      display ledger, optional Cockpit receipt, visible-plan sync metadata
    idempotency: the same canonical route generation produces the same display
      generation and can be re-shown without inventing nodes
    """

    name = "RouteDisplayProjectionStep"
    input_description = "route-display tick"
    output_description = "one route display projection state transition"
    reads = (
        "route_draft_or_active_route",
        "execution_frontier",
        "route_state_snapshot",
        "display_plan",
        "diagram_files",
        "display_receipts",
    )
    writes = (
        "user_flow_diagram",
        "display_packet",
        "user_dialog_display_ledger",
        "cockpit_route_map_receipt",
        "visible_plan_sync",
    )
    idempotency = "route-generation scoped projection refresh"

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

    if state.route_phase == "startup" and not state.startup_displayed:
        yield Transition(
            "startup_no_route_displays_stage_mermaid_with_ledger",
            _inc(
                state,
                startup_displayed=True,
                diagram_written=True,
                mermaid_source_available=True,
                mermaid_route_unknown=True,
                mermaid_node_unknown=True,
                chat_display_kind="mermaid",
                user_dialog_display_ledger_recorded=True,
                visible_generation=0,
            ),
        )
        return

    if state.route_phase == "startup":
        yield Transition(
            "pm_writes_route_draft_with_real_nodes_and_checklists",
            _route_dirty(state, phase="draft", source_kind="draft", cockpit_available=False),
        )
        return

    if state.route_source_exists and state.diagram_generation < state.route_generation:
        yield Transition(
            "router_refreshes_mermaid_from_canonical_route_source",
            _inc(
                state,
                diagram_written=True,
                diagram_generation=state.route_generation,
                mermaid_source_available=True,
                mermaid_route_unknown=False,
                mermaid_node_unknown=False,
                mermaid_uses_route_nodes=True,
                mermaid_uses_canonical_source=True,
                generated_files_only=True,
            ),
        )
        return

    if state.route_source_exists and state.visible_generation < state.route_generation:
        yield Transition(
            "chat_fallback_displays_mermaid_route_sign_and_records_ledger",
            _inc(
                state,
                chat_fallback_required=True,
                chat_display_kind="mermaid",
                user_dialog_display_ledger_recorded=True,
                generated_files_only=False,
                visible_generation=state.route_generation,
            ),
        )
        yield Transition(
            "cockpit_displays_same_canonical_graph_and_records_receipt",
            _inc(
                state,
                cockpit_available=True,
                cockpit_display_kind="route_map",
                cockpit_receipt_recorded=True,
                chat_display_kind="mermaid",
                user_dialog_display_ledger_recorded=True,
                same_graph_source_for_chat_and_cockpit=True,
                generated_files_only=False,
                visible_generation=state.route_generation,
            ),
        )
        return

    if state.route_phase == "draft":
        yield Transition(
            "pm_activates_reviewed_route_and_marks_display_dirty",
            _route_dirty(state, phase="active", source_kind="active"),
        )
        return

    if state.route_phase == "active":
        yield Transition(
            "major_node_entry_marks_route_sign_dirty",
            _route_dirty(state, phase="node_entry", source_kind="snapshot"),
        )
        return

    if state.route_phase == "node_entry":
        yield Transition(
            "current_node_completion_moves_to_next_and_marks_display_dirty",
            _route_dirty(state, phase="node_complete", source_kind="snapshot"),
        )
        return

    if state.route_phase == "node_complete":
        yield Transition(
            "route_mutation_or_review_failure_return_marks_display_dirty",
            _route_dirty(state, phase="repair_return", source_kind="snapshot"),
        )
        return

    if state.route_phase == "repair_return":
        yield Transition(
            "route_display_projection_lifecycle_complete",
            replace(state, status="complete", steps=state.steps + 1),
        )
        return


def visible_route_map_uses_canonical_source(state: State, trace) -> InvariantResult:
    del trace
    if state.route_source_exists and state.visible_generation == state.route_generation:
        if state.controller_invented_nodes or not state.route_source_is_canonical:
            return InvariantResult.fail(
                "user-visible route map was not derived from canonical route/frontier/snapshot"
            )
    return InvariantResult.pass_()


def route_source_replaces_startup_unknown_mermaid(state: State, trace) -> InvariantResult:
    del trace
    if state.route_source_exists and state.visible_generation == state.route_generation:
        if state.mermaid_route_unknown or state.mermaid_node_unknown:
            return InvariantResult.fail(
                "route draft or active route existed but user-visible Mermaid still showed route=unknown or node=unknown"
            )
    return InvariantResult.pass_()


def chat_fallback_is_mermaid_or_explicitly_degraded(state: State, trace) -> InvariantResult:
    del trace
    if state.route_source_exists and state.chat_fallback_required and state.visible_generation == state.route_generation:
        if state.chat_display_kind == "bullet":
            return InvariantResult.fail("chat fallback displayed bullet list instead of Mermaid route sign")
        if state.chat_display_kind == "degraded" and not state.mermaid_degraded_reason_recorded:
            return InvariantResult.fail("chat fallback degraded without recording a Mermaid source reason")
        if state.chat_display_kind not in {"mermaid", "degraded"}:
            return InvariantResult.fail("chat fallback did not display a route sign")
    return InvariantResult.pass_()


def cockpit_and_chat_share_canonical_graph_source(state: State, trace) -> InvariantResult:
    del trace
    if state.cockpit_available and state.visible_generation == state.route_generation:
        if not state.same_graph_source_for_chat_and_cockpit:
            return InvariantResult.fail("Cockpit route map and chat fallback used different route sources")
    return InvariantResult.pass_()


def route_nodes_and_checklists_are_preserved(state: State, trace) -> InvariantResult:
    del trace
    if state.route_source_exists and state.visible_generation == state.route_generation:
        if not (state.route_nodes_real and state.route_checklists_preserved):
            return InvariantResult.fail("route display dropped real major nodes or node checklists")
    return InvariantResult.pass_()


def route_statuses_remain_distinct(state: State, trace) -> InvariantResult:
    del trace
    if state.route_source_exists and state.visible_generation == state.route_generation and not state.route_statuses_distinct:
        return InvariantResult.fail("completed, active, selected, blocked, or pending node states were conflated")
    return InvariantResult.pass_()


def visible_display_requires_receipt_not_files_only(state: State, trace) -> InvariantResult:
    del trace
    if state.route_source_exists and state.visible_generation == state.route_generation:
        if state.generated_files_only or not (state.user_dialog_display_ledger_recorded or state.cockpit_receipt_recorded):
            return InvariantResult.fail("generated route diagram files existed without a user-visible display receipt")
    return InvariantResult.pass_()


def display_does_not_break_sealed_body_boundary_or_leak_evidence(state: State, trace) -> InvariantResult:
    del trace
    if not state.sealed_body_boundary_preserved:
        return InvariantResult.fail("route display repair broke sealed packet/result body boundary")
    if state.internal_source_fields_visible or state.evidence_table_visible:
        return InvariantResult.fail("user-visible route sign leaked internal source fields or evidence tables")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="visible_route_map_uses_canonical_source",
        description="Visible route maps come from canonical route/frontier/snapshot state.",
        predicate=visible_route_map_uses_canonical_source,
    ),
    Invariant(
        name="route_source_replaces_startup_unknown_mermaid",
        description="A real route cannot keep displaying startup route=unknown Mermaid.",
        predicate=route_source_replaces_startup_unknown_mermaid,
    ),
    Invariant(
        name="chat_fallback_is_mermaid_or_explicitly_degraded",
        description="Chat fallback shows Mermaid route signs or a recorded degraded reason.",
        predicate=chat_fallback_is_mermaid_or_explicitly_degraded,
    ),
    Invariant(
        name="cockpit_and_chat_share_canonical_graph_source",
        description="Cockpit and chat fallback use the same route source semantics.",
        predicate=cockpit_and_chat_share_canonical_graph_source,
    ),
    Invariant(
        name="route_nodes_and_checklists_are_preserved",
        description="Real major nodes and checklist items remain visible to the route map source.",
        predicate=route_nodes_and_checklists_are_preserved,
    ),
    Invariant(
        name="route_statuses_remain_distinct",
        description="Completed, active, selected, blocked, and pending states do not collapse.",
        predicate=route_statuses_remain_distinct,
    ),
    Invariant(
        name="visible_display_requires_receipt_not_files_only",
        description="Generated files alone do not satisfy the user-visible route display gate.",
        predicate=visible_display_requires_receipt_not_files_only,
    ),
    Invariant(
        name="display_does_not_break_sealed_body_boundary_or_leak_evidence",
        description="Route display keeps sealed bodies and internal evidence out of user-visible text.",
        predicate=display_does_not_break_sealed_body_boundary_or_leak_evidence,
    ),
)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(str(result.message))
    return failures


def _safe_visible_route_base(**changes: object) -> State:
    return replace(
        State(
            status="running",
            route_phase="draft",
            route_source_exists=True,
            route_source_kind="snapshot",
            route_source_is_canonical=True,
            route_node_aliases_supported=True,
            frontier_aliases_supported=True,
            draft_route_fallback_supported=True,
            snapshot_fallback_supported=True,
            route_nodes_real=True,
            route_checklists_preserved=True,
            route_statuses_distinct=True,
            route_generation=1,
            diagram_generation=1,
            visible_generation=1,
            diagram_written=True,
            mermaid_source_available=True,
            mermaid_route_unknown=False,
            mermaid_node_unknown=False,
            mermaid_uses_route_nodes=True,
            mermaid_uses_canonical_source=True,
            chat_fallback_required=True,
            chat_display_kind="mermaid",
            user_dialog_display_ledger_recorded=True,
            generated_files_only=False,
            display_plan_preserved_native_projection=True,
        ),
        **changes,
    )


def hazard_states() -> dict[str, State]:
    return {
        "controller_invents_route_nodes": _safe_visible_route_base(
            controller_invented_nodes=True,
        ),
        "route_draft_keeps_startup_unknown_mermaid": _safe_visible_route_base(
            mermaid_route_unknown=True,
            mermaid_node_unknown=True,
        ),
        "chat_fallback_bullet_list_after_route_draft": _safe_visible_route_base(
            chat_display_kind="bullet",
            display_plan_only_source=True,
        ),
        "degraded_mermaid_without_reason": _safe_visible_route_base(
            chat_display_kind="degraded",
            mermaid_degraded_reason_recorded=False,
        ),
        "cockpit_chat_source_drift": _safe_visible_route_base(
            cockpit_available=True,
            cockpit_display_kind="route_map",
            cockpit_receipt_recorded=True,
            same_graph_source_for_chat_and_cockpit=False,
        ),
        "route_checklists_simplified_away": _safe_visible_route_base(
            route_checklists_preserved=False,
        ),
        "route_statuses_collapsed": _safe_visible_route_base(
            route_statuses_distinct=False,
        ),
        "generated_files_without_visible_receipt": _safe_visible_route_base(
            generated_files_only=True,
            user_dialog_display_ledger_recorded=False,
            cockpit_receipt_recorded=False,
        ),
        "sealed_body_boundary_broken_by_display": _safe_visible_route_base(
            sealed_body_boundary_preserved=False,
        ),
        "internal_source_fields_visible_to_user": _safe_visible_route_base(
            internal_source_fields_visible=True,
        ),
        "evidence_table_visible_to_user": _safe_visible_route_base(
            evidence_table_visible=True,
        ),
    }


def current_implementation_failure_trace() -> dict[str, object]:
    state = _safe_visible_route_base(
        mermaid_route_unknown=True,
        mermaid_node_unknown=True,
        mermaid_uses_route_nodes=False,
        mermaid_uses_canonical_source=False,
        chat_display_kind="bullet",
        display_plan_only_source=True,
    )
    return {
        "labels": [
            "startup_no_route_displays_stage_mermaid_with_ledger",
            "pm_writes_route_draft_with_real_nodes_and_checklists",
            "current_sync_display_plan_projects_display_plan_as_bullets",
            "current_mermaid_generator_reads_missing_flow_json_and_old_alias_fields",
            "user_dialog_display_ledger_records_route_map_bullet_display_while_mermaid_remains_unknown",
        ],
        "failures": invariant_failures(state),
        "state": state.__dict__,
    }


def build_workflow() -> Workflow:
    return Workflow((RouteDisplayProjectionStep(),), name="flowpilot_route_display_projection")


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
    "SCENARIOS",
    "Action",
    "State",
    "Tick",
    "build_workflow",
    "current_implementation_failure_trace",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_states",
]
