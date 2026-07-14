"""Focused FlowGuard model for FlowPilot's optional material artifact map.

The map is a derived navigation index.  Its absence cannot create work or
block planning, formal package release, route memory, or terminal closure.
Only an explicit request may create it; routine consumers may refresh an
existing map.  When a map is actually linked, it must be safe, current, free
of blocked/stale/unresolved entries, and unable to replace direct evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_optional_material_artifact_map"
MAX_SEQUENCE_LENGTH = 3

VALID_MAP_ABSENT_FLOW = "valid_map_absent_flow"
VALID_MAP_REQUESTED_FLOW = "valid_map_requested_flow"
VALID_MAP_EXISTING_FLOW = "valid_map_existing_flow"
VALID_ORDINARY_EVIDENCE_FLOW = "valid_ordinary_evidence_flow"

MAP_CREATED_WITHOUT_REQUEST = "map_created_without_request"
MAP_ABSENCE_BLOCKS_PLANNING = "map_absence_blocks_planning"
MAP_ABSENCE_BLOCKS_FORMAL_PACKAGE = "map_absence_blocks_formal_package"
MAP_ABSENCE_BLOCKS_ROUTE_MEMORY = "map_absence_blocks_route_memory"
MAP_ABSENCE_BLOCKS_TERMINAL = "map_absence_blocks_terminal"
MAP_LEAKS_SEALED_BODY = "map_leaks_sealed_body"
MAP_USED_AS_ACCEPTANCE = "map_used_as_acceptance"
MAP_LINKS_UNSAFE_INDEX = "map_links_unsafe_index"
MAP_LINKS_STALE_INDEX = "map_links_stale_index"
MAP_LINKS_UNRESOLVED_INDEX = "map_links_unresolved_index"
FORMAL_PACKAGE_LACKS_DIRECT_EVIDENCE = "formal_package_lacks_direct_evidence"
SEALED_REF_BYPASSES_RUNTIME = "sealed_ref_bypasses_runtime"
RETIRED_MATERIAL_SCAN_PREFIX = "retired_material_scan_prefix"

VALID_SCENARIOS = (
    VALID_MAP_ABSENT_FLOW,
    VALID_MAP_REQUESTED_FLOW,
    VALID_MAP_EXISTING_FLOW,
    VALID_ORDINARY_EVIDENCE_FLOW,
)

NEGATIVE_SCENARIOS = (
    MAP_CREATED_WITHOUT_REQUEST,
    MAP_ABSENCE_BLOCKS_PLANNING,
    MAP_ABSENCE_BLOCKS_FORMAL_PACKAGE,
    MAP_ABSENCE_BLOCKS_ROUTE_MEMORY,
    MAP_ABSENCE_BLOCKS_TERMINAL,
    MAP_LEAKS_SEALED_BODY,
    MAP_USED_AS_ACCEPTANCE,
    MAP_LINKS_UNSAFE_INDEX,
    MAP_LINKS_STALE_INDEX,
    MAP_LINKS_UNRESOLVED_INDEX,
    FORMAL_PACKAGE_LACKS_DIRECT_EVIDENCE,
    SEALED_REF_BYPASSES_RUNTIME,
    RETIRED_MATERIAL_SCAN_PREFIX,
)

SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    """One abstract optional-map transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"

    map_initially_present: bool = False
    map_creation_requested: bool = False
    map_written: bool = False
    map_ref_present: bool = False
    map_safe_index: bool = True
    map_blocked_count: int = 0
    map_stale_count: int = 0
    map_unresolved_count: int = 0
    map_contains_sealed_body_text: bool = False
    map_claimed_as_acceptance_evidence: bool = False
    retired_material_scan_prefix_indexed: bool = False

    ordinary_research_indexed: bool = False
    current_evidence_direct_refs_present: bool = True
    sealed_refs_require_runtime_open: bool = True

    planning_advanced: bool = True
    formal_package_written: bool = True
    route_memory_written: bool = True
    final_ledger_written: bool = True
    underlying_required_evidence_clean: bool = True

    map_absence_blocks_planning: bool = False
    map_absence_blocks_formal_package: bool = False
    map_absence_blocks_route_memory: bool = False
    map_absence_blocks_terminal: bool = False

    formal_package_links_map: bool = False
    route_memory_links_map: bool = False
    final_ledger_links_map: bool = False
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class OptionalMaterialArtifactMapStep:
    """Input x State -> Set(Output x State) for optional map consumption.

    reads: explicit navigation request, existing map, direct package/result
    evidence, route memory, terminal evidence
    writes: an explicitly requested or already-existing derived map and
    conditional navigation refs only
    """

    name = "OptionalMaterialArtifactMapStep"
    input_description = "one optional material-map tick"
    output_description = "one accepted or rejected optional-map path"
    reads = (
        "explicit_navigation_request",
        "existing_material_artifact_map",
        "ordinary_research_and_current_evidence",
        "formal_package_direct_refs",
        "underlying_terminal_evidence",
    )
    writes = (
        "optional_material_artifact_map",
        "conditional_formal_package_map_ref",
        "conditional_route_memory_map_ref",
        "conditional_terminal_ledger_map_ref",
    )
    idempotency = "routine refresh never creates a missing map; existing entry ids are derived"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def initial_state() -> State:
    return State()


def _absent_success(scenario: str) -> State:
    return State(
        status="running",
        scenario=scenario,
        map_initially_present=False,
        map_creation_requested=False,
        map_written=False,
        map_ref_present=False,
        ordinary_research_indexed=False,
    )


def _present_success(scenario: str, *, requested: bool) -> State:
    return State(
        status="running",
        scenario=scenario,
        map_initially_present=not requested,
        map_creation_requested=requested,
        map_written=True,
        map_ref_present=True,
        ordinary_research_indexed=True,
        formal_package_links_map=True,
        route_memory_links_map=True,
        final_ledger_links_map=True,
    )


def _scenario_state(scenario: str) -> State:
    if scenario == VALID_MAP_ABSENT_FLOW:
        return _absent_success(scenario)
    if scenario == VALID_MAP_REQUESTED_FLOW:
        return _present_success(scenario, requested=True)
    if scenario in {VALID_MAP_EXISTING_FLOW, VALID_ORDINARY_EVIDENCE_FLOW}:
        return _present_success(scenario, requested=False)

    base_absent = _absent_success(scenario)
    base_present = _present_success(scenario, requested=False)
    if scenario == MAP_CREATED_WITHOUT_REQUEST:
        return replace(base_absent, map_written=True, map_ref_present=True)
    if scenario == MAP_ABSENCE_BLOCKS_PLANNING:
        return replace(base_absent, planning_advanced=False, map_absence_blocks_planning=True)
    if scenario == MAP_ABSENCE_BLOCKS_FORMAL_PACKAGE:
        return replace(base_absent, formal_package_written=False, map_absence_blocks_formal_package=True)
    if scenario == MAP_ABSENCE_BLOCKS_ROUTE_MEMORY:
        return replace(base_absent, route_memory_written=False, map_absence_blocks_route_memory=True)
    if scenario == MAP_ABSENCE_BLOCKS_TERMINAL:
        return replace(base_absent, final_ledger_written=False, map_absence_blocks_terminal=True)
    if scenario == MAP_LEAKS_SEALED_BODY:
        return replace(base_present, map_contains_sealed_body_text=True)
    if scenario == MAP_USED_AS_ACCEPTANCE:
        return replace(base_present, map_claimed_as_acceptance_evidence=True)
    if scenario == MAP_LINKS_UNSAFE_INDEX:
        return replace(base_present, map_safe_index=False)
    if scenario == MAP_LINKS_STALE_INDEX:
        return replace(base_present, map_stale_count=1)
    if scenario == MAP_LINKS_UNRESOLVED_INDEX:
        return replace(base_present, map_unresolved_count=1)
    if scenario == FORMAL_PACKAGE_LACKS_DIRECT_EVIDENCE:
        return replace(base_absent, current_evidence_direct_refs_present=False)
    if scenario == SEALED_REF_BYPASSES_RUNTIME:
        return replace(base_present, sealed_refs_require_runtime_open=False)
    if scenario == RETIRED_MATERIAL_SCAN_PREFIX:
        return replace(base_present, retired_material_scan_prefix_indexed=True)
    return base_absent


def material_map_failures(state: State) -> list[str]:
    failures: list[str] = []
    map_usable = (
        state.map_written
        and state.map_safe_index
        and state.map_blocked_count == 0
        and state.map_stale_count == 0
        and state.map_unresolved_count == 0
        and not state.map_contains_sealed_body_text
    )
    map_linked = state.formal_package_links_map or state.route_memory_links_map or state.final_ledger_links_map

    if state.map_written and not (state.map_initially_present or state.map_creation_requested):
        failures.append("missing optional map was created without an explicit request")
    if not state.map_written and state.map_ref_present:
        failures.append("missing optional map produced a navigation reference")
    if not state.map_written:
        if state.map_absence_blocks_planning or not state.planning_advanced:
            failures.append("optional map absence blocked planning")
        if state.map_absence_blocks_formal_package or not state.formal_package_written:
            failures.append("optional map absence blocked formal package release")
        if state.map_absence_blocks_route_memory or not state.route_memory_written:
            failures.append("optional map absence blocked route memory")
        if state.map_absence_blocks_terminal or not state.final_ledger_written:
            failures.append("optional map absence blocked terminal closure")
        if map_linked:
            failures.append("missing optional map was linked")

    if state.map_contains_sealed_body_text:
        failures.append("material artifact map leaked sealed packet or result body content")
    if not state.sealed_refs_require_runtime_open:
        failures.append("sealed material reference bypassed runtime open authority")
    if state.map_claimed_as_acceptance_evidence:
        failures.append("optional material map was treated as acceptance evidence")
    if state.retired_material_scan_prefix_indexed:
        failures.append("retired material-scan index or review prefix re-entered the current map")
    if map_linked and not map_usable:
        failures.append("unsafe, blocked, stale, or unresolved optional map was linked")
    if state.formal_package_written and not state.current_evidence_direct_refs_present:
        failures.append("formal package relied on optional map instead of direct current evidence")
    if state.final_ledger_written and not state.underlying_required_evidence_clean:
        failures.append("terminal closure ignored unresolved underlying required evidence")
    return failures


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _scenario_state(scenario))
        return
    failures = material_map_failures(state)
    if failures:
        yield Transition(
            f"reject_{state.scenario}",
            replace(state, status="rejected", terminal_reason="; ".join(failures)),
        )
        return
    yield Transition(
        f"accept_{state.scenario}",
        replace(state, status="accepted", terminal_reason="optional_material_map_contract_ok"),
    )


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and not material_map_failures(state)


def accepts_only_safe_optional_map_paths(state: State, trace) -> InvariantResult:
    del trace
    failures = material_map_failures(state)
    if state.status == "accepted" and failures:
        return InvariantResult.fail("unsafe optional material-map path was accepted")
    if state.status == "rejected" and not failures:
        return InvariantResult.fail("safe optional material-map path was rejected")
    return InvariantResult.pass_()


def absence_never_creates_or_blocks(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and not state.map_initially_present and not state.map_creation_requested:
        if state.map_written or not all(
            (state.planning_advanced, state.formal_package_written, state.route_memory_written, state.final_ledger_written)
        ):
            return InvariantResult.fail("accepted absent-map path created work or blocked progress")
    return InvariantResult.pass_()


def linked_map_is_safe_and_non_authoritative(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and (
        state.formal_package_links_map or state.route_memory_links_map or state.final_ledger_links_map
    ):
        if (
            not state.map_safe_index
            or state.map_blocked_count
            or state.map_stale_count
            or state.map_unresolved_count
            or state.map_claimed_as_acceptance_evidence
        ):
            return InvariantResult.fail("accepted linked map was unsafe, stale, unresolved, or authoritative")
    return InvariantResult.pass_()


def direct_evidence_and_sealed_boundary_remain_primary(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and (
        not state.current_evidence_direct_refs_present or not state.sealed_refs_require_runtime_open
    ):
        return InvariantResult.fail("accepted path lost direct evidence or sealed-body runtime authority")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepts_only_safe_optional_map_paths",
        description="Only safe optional-map paths are accepted.",
        predicate=accepts_only_safe_optional_map_paths,
    ),
    Invariant(
        name="absence_never_creates_or_blocks",
        description="A missing unrequested map neither appears nor blocks any project stage.",
        predicate=absence_never_creates_or_blocks,
    ),
    Invariant(
        name="linked_map_is_safe_and_non_authoritative",
        description="A linked map is safe/current navigation and never acceptance evidence.",
        predicate=linked_map_is_safe_and_non_authoritative,
    ),
    Invariant(
        name="direct_evidence_and_sealed_boundary_remain_primary",
        description="Formal/terminal decisions keep direct evidence and runtime-open sealed boundaries.",
        predicate=direct_evidence_and_sealed_boundary_remain_primary,
    ),
)

EXTERNAL_INPUTS = (Tick(),)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def build_workflow() -> Workflow:
    return Workflow((OptionalMaterialArtifactMapStep(),), name=MODEL_ID)


def terminal_predicate(_input_obj, state: State, _trace) -> bool:
    return is_terminal(state)


def hazard_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "MODEL_ID",
    "NEGATIVE_SCENARIOS",
    "SCENARIOS",
    "VALID_SCENARIOS",
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
    "material_map_failures",
    "next_safe_states",
    "next_states",
    "terminal_predicate",
]
