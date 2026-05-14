"""FlowGuard model for FlowPilot committed-route display lifecycle.

Risk intent brief:
- Prevent FlowPilot from presenting ``flow.draft.json`` as a user-visible route
  commitment in chat or Cockpit.
- Protect the canonical source-of-truth boundary: drafts and repair candidates
  are internal review artifacts, while the user-visible route map may only read
  the last committed ``flow.json`` or a snapshot explicitly built from it.
- Keep the startup waiting-for-PM-route status internal so the user sees the
  startup banner and Route Sign placeholder, not a low-information waiting
  status card.
- Critical durable state: draft route, route check results, committed route,
  execution frontier, route_state_snapshot, display_plan, route-sign files,
  Cockpit/chat receipts, and the previous committed visible route.
- Adversarial branches include draft-only routes with no ``flow.json``,
  draft-backed display plans, draft-backed snapshots, draft-backed route signs,
  startup placeholders with missing identity/replacement metadata, repair
  candidates shown before recheck, previous committed routes overwritten by
  drafts, Cockpit/chat source drift, checklist loss, status conflation, and
  accidental internal evidence/source-field display.
- Hard invariant: user-visible route maps are committed-route only. A draft may
  be reviewed internally, but it must not advance the visible route generation,
  replace the visible display plan, or become the Cockpit/chat route source.
- Blindspot: this is a display-control model. It does not render or visually
  inspect Mermaid; runtime tests and live conformance cover concrete files.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


SCENARIOS = (
    "startup no committed route",
    "PM writes internal route draft",
    "route draft is reviewed without user-visible projection",
    "PM activates reviewed route as flow.json",
    "major node entry/current node starts",
    "current node completes and moves to next",
    "route mutation or review-failure repair candidate remains internal",
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
    internal_waiting_state_recorded: bool = False
    startup_waiting_status_card_visible: bool = False
    route_phase: str = "startup"  # startup | draft | review | committed | node_entry | node_complete | repair_return
    draft_route_exists: bool = False
    draft_review_passed: bool = False
    repair_candidate_exists: bool = False
    committed_route_exists: bool = False
    previous_committed_visible_route_exists: bool = False
    route_source_exists: bool = False
    route_source_kind: str = "none"  # none | flow_json | snapshot_from_flow_json
    visible_source_kind: str = "none"  # none | waiting | flow_json | snapshot_from_flow_json | flow_draft | repair_candidate
    route_source_is_canonical: bool = True
    display_role: str = "none"  # none | startup_placeholder | canonical_route
    is_placeholder: bool = False
    replacement_rule: str = "none"  # none | replace_when_canonical_route_available
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
    draft_wrote_visible_display_plan: bool = False
    route_state_snapshot_backed_by_draft: bool = False

    route_generation: int = 0
    draft_generation: int = 0
    committed_generation: int = 0
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


def _draft_written(state: State, *, repair: bool = False) -> State:
    return _inc(
        state,
        route_phase="repair_return" if repair else "draft",
        draft_route_exists=True,
        repair_candidate_exists=repair,
        route_source_exists=state.committed_route_exists,
        route_source_kind=state.route_source_kind,
        route_source_is_canonical=True,
        route_node_aliases_supported=True,
        frontier_aliases_supported=True,
        draft_route_fallback_supported=False,
        snapshot_fallback_supported=True,
        route_nodes_real=True,
        route_checklists_preserved=True,
        route_statuses_distinct=True,
        draft_generation=state.draft_generation + 1,
        route_generation=state.route_generation,
        diagram_generation=state.diagram_generation,
        visible_generation=state.visible_generation,
        visible_source_kind=state.visible_source_kind,
        display_role=state.display_role,
        is_placeholder=state.is_placeholder,
        replacement_rule=state.replacement_rule,
        chat_display_kind=state.chat_display_kind,
        cockpit_display_kind=state.cockpit_display_kind,
        user_dialog_display_ledger_recorded=state.user_dialog_display_ledger_recorded,
        cockpit_receipt_recorded=state.cockpit_receipt_recorded,
        generated_files_only=False,
        cockpit_available=state.cockpit_available,
    )


def _committed_route_dirty(
    state: State,
    *,
    phase: str,
    source_kind: str,
    cockpit_available: bool | None = None,
) -> State:
    committed_generation = state.committed_generation + 1
    return _inc(
        state,
        route_phase=phase,
        draft_route_exists=False,
        draft_review_passed=False,
        repair_candidate_exists=False,
        committed_route_exists=True,
        previous_committed_visible_route_exists=True,
        route_source_exists=True,
        route_source_kind=source_kind,
        visible_source_kind=state.visible_source_kind,
        display_role=state.display_role,
        is_placeholder=state.is_placeholder,
        replacement_rule=state.replacement_rule,
        route_source_is_canonical=True,
        route_node_aliases_supported=True,
        frontier_aliases_supported=True,
        draft_route_fallback_supported=False,
        snapshot_fallback_supported=True,
        route_nodes_real=True,
        route_checklists_preserved=True,
        route_statuses_distinct=True,
        route_generation=committed_generation,
        committed_generation=committed_generation,
        diagram_generation=state.diagram_generation,
        visible_generation=state.visible_generation,
        mermaid_source_available=False,
        mermaid_route_unknown=False,
        mermaid_node_unknown=False,
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
            "startup_no_committed_route_displays_route_sign_with_internal_waiting_state",
            _inc(
                state,
                startup_displayed=True,
                internal_waiting_state_recorded=True,
                startup_waiting_status_card_visible=False,
                diagram_written=False,
                mermaid_source_available=False,
                mermaid_route_unknown=True,
                mermaid_node_unknown=True,
                visible_source_kind="waiting",
                display_role="startup_placeholder",
                is_placeholder=True,
                replacement_rule="replace_when_canonical_route_available",
                chat_display_kind="mermaid",
                mermaid_degraded_reason_recorded=True,
                user_dialog_display_ledger_recorded=True,
                visible_generation=0,
            ),
        )
        return

    if state.route_phase == "startup":
        yield Transition(
            "pm_writes_internal_route_draft_without_visible_projection",
            _draft_written(state, repair=False),
        )
        return

    if state.route_phase == "draft":
        yield Transition(
            "process_product_reviewer_checks_draft_without_visible_projection",
            _inc(state, route_phase="review", draft_review_passed=True),
        )
        return

    if state.route_phase == "review":
        yield Transition(
            "pm_activates_reviewed_route_as_committed_flow_json",
            _committed_route_dirty(state, phase="committed", source_kind="flow_json"),
        )
        return

    if state.committed_route_exists and state.diagram_generation < state.committed_generation:
        yield Transition(
            "router_refreshes_mermaid_from_committed_route_source",
            _inc(
                state,
                diagram_written=True,
                diagram_generation=state.committed_generation,
                mermaid_source_available=True,
                mermaid_route_unknown=False,
                mermaid_node_unknown=False,
                mermaid_uses_route_nodes=True,
                mermaid_uses_canonical_source=True,
                generated_files_only=True,
            ),
        )
        return

    if state.committed_route_exists and state.visible_generation < state.committed_generation:
        yield Transition(
            "committed_route_synced_to_user_visible_surface",
            _inc(
                state,
                chat_fallback_required=True,
                chat_display_kind="mermaid",
                visible_source_kind=state.route_source_kind,
                display_role="canonical_route",
                is_placeholder=False,
                replacement_rule="none",
                user_dialog_display_ledger_recorded=True,
                generated_files_only=False,
                visible_generation=state.committed_generation,
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
                visible_source_kind=state.route_source_kind,
                display_role="canonical_route",
                is_placeholder=False,
                replacement_rule="none",
                user_dialog_display_ledger_recorded=True,
                same_graph_source_for_chat_and_cockpit=True,
                generated_files_only=False,
                visible_generation=state.committed_generation,
            ),
        )
        return

    if (
        state.route_phase == "committed"
        and state.committed_generation >= 4
        and state.visible_generation == state.committed_generation
    ):
        yield Transition(
            "route_display_projection_lifecycle_complete",
            replace(state, status="complete", steps=state.steps + 1),
        )
        return

    if state.route_phase == "committed":
        yield Transition(
            "major_node_entry_marks_route_sign_dirty",
            _committed_route_dirty(state, phase="node_entry", source_kind="snapshot_from_flow_json"),
        )
        return

    if state.route_phase == "node_entry":
        yield Transition(
            "current_node_completion_moves_to_next_and_marks_display_dirty",
            _committed_route_dirty(state, phase="node_complete", source_kind="snapshot_from_flow_json"),
        )
        return

    if state.route_phase == "node_complete":
        yield Transition(
            "route_mutation_or_review_failure_repair_candidate_stays_internal",
            _draft_written(state, repair=True),
        )
        return

    if state.route_phase == "repair_return" and state.repair_candidate_exists:
        yield Transition(
            "pm_activates_reviewed_repair_as_committed_flow_json",
            _committed_route_dirty(state, phase="committed", source_kind="flow_json"),
        )
        return


def visible_route_map_uses_canonical_source(state: State, trace) -> InvariantResult:
    del trace
    if state.committed_route_exists and state.visible_generation == state.committed_generation:
        if state.controller_invented_nodes or not state.route_source_is_canonical:
            return InvariantResult.fail(
                "user-visible route map was not derived from canonical route/frontier/snapshot"
            )
    return InvariantResult.pass_()


def visible_route_map_is_committed_only(state: State, trace) -> InvariantResult:
    del trace
    if state.visible_source_kind in {"flow_draft", "repair_candidate"}:
        return InvariantResult.fail("draft or repair candidate was projected to the user-visible route surface")
    if state.chat_display_kind == "mermaid" or state.cockpit_display_kind == "route_map":
        if not state.committed_route_exists and state.is_placeholder and state.display_role == "startup_placeholder":
            return InvariantResult.pass_()
        if state.visible_source_kind not in {"flow_json", "snapshot_from_flow_json"}:
            return InvariantResult.fail("user-visible route map did not come from committed flow.json state")
        if not state.committed_route_exists:
            return InvariantResult.fail("user-visible route map was displayed before a committed flow.json existed")
    return InvariantResult.pass_()


def startup_placeholder_has_explicit_identity_and_replacement_rule(state: State, trace) -> InvariantResult:
    del trace
    startup_mermaid = (
        state.startup_displayed
        and not state.committed_route_exists
        and state.chat_display_kind == "mermaid"
    )
    if startup_mermaid:
        if state.display_role != "startup_placeholder" or not state.is_placeholder:
            return InvariantResult.fail("startup placeholder route sign lacked explicit placeholder identity")
        if state.replacement_rule != "replace_when_canonical_route_available":
            return InvariantResult.fail("startup placeholder route sign lacked explicit canonical-route replacement rule")
    return InvariantResult.pass_()


def startup_waiting_state_is_internal_only(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.startup_waiting_status_card_visible
        and state.startup_displayed
        and not state.committed_route_exists
    ):
        return InvariantResult.fail("startup waiting status card was shown to the user before PM route activation")
    if state.startup_displayed and not state.committed_route_exists and not state.internal_waiting_state_recorded:
        return InvariantResult.fail("startup display lacked an internal waiting-for-PM-route record")
    return InvariantResult.pass_()


def canonical_route_replaces_placeholder_identity(state: State, trace) -> InvariantResult:
    del trace
    canonical_visible = (
        state.committed_route_exists
        and state.visible_generation == state.committed_generation
        and (state.chat_display_kind == "mermaid" or state.cockpit_display_kind == "route_map")
    )
    if canonical_visible:
        if state.is_placeholder or state.replacement_rule != "none":
            return InvariantResult.fail("canonical route display kept startup placeholder semantics")
        if state.display_role != "canonical_route":
            return InvariantResult.fail("canonical route display lacked explicit canonical identity")
    return InvariantResult.pass_()


def draft_review_cannot_update_visible_route_plan(state: State, trace) -> InvariantResult:
    del trace
    if state.draft_wrote_visible_display_plan:
        return InvariantResult.fail("route draft wrote or replaced the user-visible display plan")
    if state.route_state_snapshot_backed_by_draft:
        return InvariantResult.fail("user-visible route_state_snapshot was backed by flow.draft.json")
    if state.draft_route_fallback_supported:
        return InvariantResult.fail("user-visible route sign generator allowed flow.draft.json fallback")
    if state.draft_route_exists and not state.committed_route_exists and state.visible_source_kind != "waiting":
        return InvariantResult.fail("draft-only run did not keep the user-visible surface in waiting state")
    if state.repair_candidate_exists and state.visible_source_kind == "repair_candidate":
        return InvariantResult.fail("repair candidate was displayed before committed activation")
    return InvariantResult.pass_()


def draft_cannot_overwrite_previous_committed_visible_route(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.previous_committed_visible_route_exists
        and state.draft_route_exists
        and state.visible_source_kind == "flow_draft"
    ):
        return InvariantResult.fail("new draft overwrote the previous committed visible route")
    return InvariantResult.pass_()


def route_source_replaces_startup_unknown_mermaid(state: State, trace) -> InvariantResult:
    del trace
    if state.committed_route_exists and state.visible_generation == state.committed_generation:
        if state.mermaid_route_unknown or state.mermaid_node_unknown:
            return InvariantResult.fail(
                "committed route existed but user-visible Mermaid still showed route=unknown or node=unknown"
            )
    return InvariantResult.pass_()


def chat_fallback_is_mermaid_or_explicitly_degraded(state: State, trace) -> InvariantResult:
    del trace
    if state.committed_route_exists and state.chat_fallback_required and state.visible_generation == state.committed_generation:
        if state.chat_display_kind == "bullet":
            return InvariantResult.fail("chat fallback displayed bullet list instead of Mermaid route sign")
        if state.chat_display_kind == "degraded" and not state.mermaid_degraded_reason_recorded:
            return InvariantResult.fail("chat fallback degraded without recording a Mermaid source reason")
        if state.chat_display_kind not in {"mermaid", "degraded"}:
            return InvariantResult.fail("chat fallback did not display a route sign")
    return InvariantResult.pass_()


def cockpit_and_chat_share_canonical_graph_source(state: State, trace) -> InvariantResult:
    del trace
    if state.cockpit_available and state.visible_generation == state.committed_generation:
        if not state.same_graph_source_for_chat_and_cockpit:
            return InvariantResult.fail("Cockpit route map and chat fallback used different route sources")
    return InvariantResult.pass_()


def route_nodes_and_checklists_are_preserved(state: State, trace) -> InvariantResult:
    del trace
    if state.committed_route_exists and state.visible_generation == state.committed_generation:
        if not (state.route_nodes_real and state.route_checklists_preserved):
            return InvariantResult.fail("route display dropped real major nodes or node checklists")
    return InvariantResult.pass_()


def route_statuses_remain_distinct(state: State, trace) -> InvariantResult:
    del trace
    if state.committed_route_exists and state.visible_generation == state.committed_generation and not state.route_statuses_distinct:
        return InvariantResult.fail("completed, active, selected, blocked, or pending node states were conflated")
    return InvariantResult.pass_()


def visible_display_requires_receipt_not_files_only(state: State, trace) -> InvariantResult:
    del trace
    if state.committed_route_exists and state.visible_generation == state.committed_generation:
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
        name="visible_route_map_is_committed_only",
        description="Drafts and repair candidates never become the user-visible route source.",
        predicate=visible_route_map_is_committed_only,
    ),
    Invariant(
        name="draft_review_cannot_update_visible_route_plan",
        description="Draft and review stages preserve waiting or previous committed user-visible state.",
        predicate=draft_review_cannot_update_visible_route_plan,
    ),
    Invariant(
        name="startup_placeholder_has_explicit_identity_and_replacement_rule",
        description="Startup placeholder route signs are explicitly marked and carry their replacement rule.",
        predicate=startup_placeholder_has_explicit_identity_and_replacement_rule,
    ),
    Invariant(
        name="startup_waiting_state_is_internal_only",
        description="Waiting-for-PM-route state is internal and does not become a user-visible status card.",
        predicate=startup_waiting_state_is_internal_only,
    ),
    Invariant(
        name="canonical_route_replaces_placeholder_identity",
        description="Canonical route displays replace placeholder semantics when real route data appears.",
        predicate=canonical_route_replaces_placeholder_identity,
    ),
    Invariant(
        name="draft_cannot_overwrite_previous_committed_visible_route",
        description="A new draft cannot replace the last committed visible route.",
        predicate=draft_cannot_overwrite_previous_committed_visible_route,
    ),
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
            route_phase="committed",
            committed_route_exists=True,
            previous_committed_visible_route_exists=True,
            route_source_exists=True,
            route_source_kind="snapshot_from_flow_json",
            visible_source_kind="snapshot_from_flow_json",
            route_source_is_canonical=True,
            display_role="canonical_route",
            is_placeholder=False,
            replacement_rule="none",
            route_node_aliases_supported=True,
            frontier_aliases_supported=True,
            draft_route_fallback_supported=False,
            snapshot_fallback_supported=True,
            route_nodes_real=True,
            route_checklists_preserved=True,
            route_statuses_distinct=True,
            route_generation=1,
            committed_generation=1,
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
        "draft_route_projected_to_user_visible_surface": _safe_visible_route_base(
            route_phase="draft",
            draft_route_exists=True,
            committed_route_exists=False,
            visible_source_kind="flow_draft",
        ),
        "draft_writes_visible_display_plan": _safe_visible_route_base(
            draft_route_exists=True,
            draft_wrote_visible_display_plan=True,
        ),
        "draft_backed_route_state_snapshot_visible": _safe_visible_route_base(
            route_state_snapshot_backed_by_draft=True,
        ),
        "draft_backed_chat_route_sign": _safe_visible_route_base(
            draft_route_fallback_supported=True,
        ),
        "draft_only_run_leaves_waiting_state": _safe_visible_route_base(
            route_phase="draft",
            draft_route_exists=True,
            committed_route_exists=False,
            visible_source_kind="flow_draft",
        ),
        "draft_overwrites_previous_committed_visible_route": _safe_visible_route_base(
            draft_route_exists=True,
            previous_committed_visible_route_exists=True,
            visible_source_kind="flow_draft",
        ),
        "repair_candidate_projected_before_commit": _safe_visible_route_base(
            repair_candidate_exists=True,
            visible_source_kind="repair_candidate",
        ),
        "controller_invents_route_nodes": _safe_visible_route_base(
            controller_invented_nodes=True,
        ),
        "route_draft_keeps_startup_unknown_mermaid": _safe_visible_route_base(
            mermaid_route_unknown=True,
            mermaid_node_unknown=True,
        ),
        "startup_placeholder_missing_identity": State(
            status="running",
            startup_displayed=True,
            internal_waiting_state_recorded=True,
            visible_source_kind="waiting",
            chat_display_kind="mermaid",
            user_dialog_display_ledger_recorded=True,
            mermaid_route_unknown=True,
            mermaid_node_unknown=True,
        ),
        "startup_placeholder_missing_replacement_rule": State(
            status="running",
            startup_displayed=True,
            internal_waiting_state_recorded=True,
            visible_source_kind="waiting",
            chat_display_kind="mermaid",
            display_role="startup_placeholder",
            is_placeholder=True,
            replacement_rule="none",
            user_dialog_display_ledger_recorded=True,
            mermaid_route_unknown=True,
            mermaid_node_unknown=True,
        ),
        "startup_waiting_status_card_visible": State(
            status="running",
            startup_displayed=True,
            internal_waiting_state_recorded=True,
            startup_waiting_status_card_visible=True,
            visible_source_kind="waiting",
            display_role="startup_placeholder",
            is_placeholder=True,
            replacement_rule="replace_when_canonical_route_available",
            chat_display_kind="mermaid",
            user_dialog_display_ledger_recorded=True,
        ),
        "canonical_route_keeps_placeholder_identity": _safe_visible_route_base(
            display_role="startup_placeholder",
            is_placeholder=True,
            replacement_rule="replace_when_canonical_route_available",
        ),
        "canonical_route_missing_identity": _safe_visible_route_base(
            display_role="none",
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
        route_phase="draft",
        draft_route_exists=True,
        committed_route_exists=False,
        visible_source_kind="flow_draft",
        draft_wrote_visible_display_plan=True,
        route_state_snapshot_backed_by_draft=True,
        draft_route_fallback_supported=True,
    )
    return {
        "labels": [
            "startup_no_committed_route_displays_route_sign_with_internal_waiting_state",
            "pm_writes_internal_route_draft_without_visible_projection",
            "current_router_writes_display_plan_from_flow_draft",
            "current_route_sign_generator_accepts_flow_draft_fallback",
            "user_dialog_or_cockpit_can_receive_a_draft_backed_route_map",
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
