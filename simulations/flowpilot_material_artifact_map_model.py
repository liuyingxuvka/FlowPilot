"""FlowGuard model for the FlowPilot material artifact map.

Risk intent brief:
- Validate a minimal derived map for reusable material, modeling, research,
  self-interrogation, reviewer, PM package, and generated-resource artifacts.
- Protected harms: sealed packet/result body leakage, Controller summary being
  treated as evidence, worker reads outside a current packet boundary, reviewer
  material sufficiency passing without concrete checked sources, PM formal
  packages lacking review refs, and final ledger accepting stale/unresolved
  material as current evidence.
- Modeled state and side effects: material map refresh, metadata-only entries,
  PM formal package review refs, worker packet allowed reads, runtime-open
  requirements, reviewer source checks, route-memory linkage, and final-ledger
  material disposition.
- Hard invariants: the map is reference-only; existing packet/runtime/PM/
  reviewer ledgers remain authoritative; workers need packet-declared reads;
  sealed body refs require runtime open; reviewer pass needs checked refs; final
  ledger cannot close with stale/unresolved current material.
- Blindspot: this model checks abstract control-flow and authority semantics.
  Runtime tests must still verify concrete JSON fields, cards, contracts, and
  file writes.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_REFRESH_METADATA_ONLY = "valid_refresh_metadata_only"
VALID_PM_PACKAGE_REVIEW_REFS = "valid_pm_package_review_refs"
VALID_WORKER_AUTHORIZED_READ = "valid_workeruthorized_read"
VALID_RUNTIME_OPEN_FOR_SEALED_REF = "valid_runtime_open_for_sealed_ref"
VALID_ROUTE_MEMORY_AND_FINAL_LEDGER = "valid_route_memory_and_final_ledger"

MAP_LEAKS_SEALED_BODY = "map_leaks_sealed_body"
CONTROLLER_SUMMARY_USED_AS_EVIDENCE = "controller_summary_used_as_evidence"
WORKER_READS_UNLISTED_ENTRY = "worker_reads_unlisted_entry"
WORKER_READS_SEALED_WITHOUT_RUNTIME = "worker_reads_sealed_without_runtime"
REVIEWER_PASSES_WITHOUT_CHECKED_SOURCES = "reviewer_passes_without_checked_sources"
PM_PACKAGE_LACKS_REVIEW_REFS = "pm_package_lacks_review_refs"
FINAL_LEDGER_ACCEPTS_STALE_MATERIAL = "final_ledger_accepts_stale_material"
FINAL_LEDGER_ACCEPTS_UNRESOLVED_MATERIAL = "final_ledger_accepts_unresolved_material"

VALID_SCENARIOS = (
    VALID_REFRESH_METADATA_ONLY,
    VALID_PM_PACKAGE_REVIEW_REFS,
    VALID_WORKER_AUTHORIZED_READ,
    VALID_RUNTIME_OPEN_FOR_SEALED_REF,
    VALID_ROUTE_MEMORY_AND_FINAL_LEDGER,
)

NEGATIVE_SCENARIOS = (
    MAP_LEAKS_SEALED_BODY,
    CONTROLLER_SUMMARY_USED_AS_EVIDENCE,
    WORKER_READS_UNLISTED_ENTRY,
    WORKER_READS_SEALED_WITHOUT_RUNTIME,
    REVIEWER_PASSES_WITHOUT_CHECKED_SOURCES,
    PM_PACKAGE_LACKS_REVIEW_REFS,
    FINAL_LEDGER_ACCEPTS_STALE_MATERIAL,
    FINAL_LEDGER_ACCEPTS_UNRESOLVED_MATERIAL,
)

SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    """One abstract material-map transition tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"

    map_written: bool = False
    entries_have_paths_and_hashes: bool = False
    map_contains_sealed_body_text: bool = False
    map_authority_is_index_only: bool = False
    existing_runtime_ledgers_authoritative: bool = False
    controller_summary_used_as_evidence: bool = False

    pm_formal_package_released: bool = False
    package_cites_map_path: bool = False
    package_cites_review_source_entries: bool = False
    package_cites_reviewable_source_paths: bool = False
    package_includes_raw_worker_result_body: bool = False

    worker_packet_opened: bool = False
    workerllowed_entry_ids_declared: bool = False
    worker_reads_only_declared_entries: bool = False
    worker_reads_sealed_body_without_runtime: bool = False

    sealed_ref_requires_runtime_open: bool = False
    runtime_open_receipt_present: bool = False

    reviewer_reports_sufficient: bool = False
    reviewer_checked_source_refs_present: bool = False
    reviewer_uses_map_summary_only: bool = False

    route_memory_links_map: bool = False
    final_ledger_links_map: bool = False
    stale_current_material_used_as_evidence: bool = False
    unresolved_current_material_used_as_evidence: bool = False
    final_ledger_closes: bool = False
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class MaterialArtifactMapStep:
    """Model one FlowPilot material artifact-map transition.

    Input x State -> Set(Output x State)
    reads: existing material/research/reviewer/package/runtime/route artifacts
    writes: derived material artifact map, package refs, route/final refs
    idempotency: refresh is derived from source paths and hashes; repeating a
    refresh updates the same entry ids instead of creating approval authority.
    """

    name = "MaterialArtifactMapStep"
    input_description = "FlowPilot material artifact-map tick"
    output_description = "one material artifact-map transition"
    reads = (
        "packet_ledger",
        "material_scan_index",
        "pm_formal_gate_package",
        "reviewer_material_report",
        "route_memory",
        "final_ledger",
    )
    writes = (
        "material_artifact_map",
        "pm_formal_gate_package_refs",
        "route_memory_material_map_ref",
        "final_ledger_material_map_ref",
    )
    idempotency = "map entries are derived and keyed by stable source refs"

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


def _base_state(scenario: str) -> State:
    return State(
        status="running",
        scenario=scenario,
        map_written=True,
        entries_have_paths_and_hashes=True,
        map_authority_is_index_only=True,
        existing_runtime_ledgers_authoritative=True,
        pm_formal_package_released=True,
        package_cites_map_path=True,
        package_cites_review_source_entries=True,
        package_cites_reviewable_source_paths=True,
        worker_packet_opened=True,
        workerllowed_entry_ids_declared=True,
        worker_reads_only_declared_entries=True,
        sealed_ref_requires_runtime_open=True,
        runtime_open_receipt_present=True,
        reviewer_reports_sufficient=True,
        reviewer_checked_source_refs_present=True,
        route_memory_links_map=True,
        final_ledger_links_map=True,
        final_ledger_closes=True,
    )


def _scenario_state(scenario: str) -> State:
    if scenario in VALID_SCENARIOS:
        return _base_state(scenario)
    if scenario == MAP_LEAKS_SEALED_BODY:
        return replace(_base_state(scenario), map_contains_sealed_body_text=True)
    if scenario == CONTROLLER_SUMMARY_USED_AS_EVIDENCE:
        return replace(
            _base_state(scenario),
            controller_summary_used_as_evidence=True,
            map_authority_is_index_only=False,
        )
    if scenario == WORKER_READS_UNLISTED_ENTRY:
        return replace(_base_state(scenario), worker_reads_only_declared_entries=False)
    if scenario == WORKER_READS_SEALED_WITHOUT_RUNTIME:
        return replace(
            _base_state(scenario),
            runtime_open_receipt_present=False,
            worker_reads_sealed_body_without_runtime=True,
        )
    if scenario == REVIEWER_PASSES_WITHOUT_CHECKED_SOURCES:
        return replace(
            _base_state(scenario),
            reviewer_checked_source_refs_present=False,
            reviewer_uses_map_summary_only=True,
        )
    if scenario == PM_PACKAGE_LACKS_REVIEW_REFS:
        return replace(
            _base_state(scenario),
            package_cites_map_path=False,
            package_cites_review_source_entries=False,
            package_cites_reviewable_source_paths=False,
        )
    if scenario == FINAL_LEDGER_ACCEPTS_STALE_MATERIAL:
        return replace(_base_state(scenario), stale_current_material_used_as_evidence=True)
    if scenario == FINAL_LEDGER_ACCEPTS_UNRESOLVED_MATERIAL:
        return replace(_base_state(scenario), unresolved_current_material_used_as_evidence=True)
    return _base_state(scenario)


def material_map_failures(state: State) -> list[str]:
    failures: list[str] = []
    if not state.map_written:
        failures.append("material artifact map was not written")
    if not state.entries_have_paths_and_hashes:
        failures.append("material artifact map entries lack source paths or hashes")
    if state.map_contains_sealed_body_text:
        failures.append("material artifact map leaked sealed packet or result body content")
    if not state.map_authority_is_index_only or state.controller_summary_used_as_evidence:
        failures.append("material artifact map or Controller summary was treated as acceptance evidence")
    if not state.existing_runtime_ledgers_authoritative:
        failures.append("material artifact map replaced packet/runtime/PM/reviewer ledger authority")

    if state.pm_formal_package_released and state.package_includes_raw_worker_result_body:
        failures.append("PM formal package included raw worker result body content")
    if state.pm_formal_package_released and not (
        state.package_cites_map_path
        and state.package_cites_review_source_entries
        and state.package_cites_reviewable_source_paths
    ):
        failures.append("PM formal package lacks material-map review refs")

    if state.worker_packet_opened and not state.workerllowed_entry_ids_declared:
        failures.append("worker packet did not declare material-map allowed reads")
    if state.worker_packet_opened and not state.worker_reads_only_declared_entries:
        failures.append("worker read material-map entries outside the current packet authorization")
    if state.worker_reads_sealed_body_without_runtime:
        failures.append("worker read a sealed body without packet-runtime authority")
    if state.sealed_ref_requires_runtime_open and not state.runtime_open_receipt_present:
        failures.append("sealed material-map reference lacks runtime-open receipt")

    if state.reviewer_reports_sufficient and not state.reviewer_checked_source_refs_present:
        failures.append("reviewer material sufficiency passed without checked source refs")
    if state.reviewer_reports_sufficient and state.reviewer_uses_map_summary_only:
        failures.append("reviewer passed from material-map or Controller summary alone")

    if not state.route_memory_links_map:
        failures.append("route memory does not link the material artifact map")
    if state.final_ledger_closes and not state.final_ledger_links_map:
        failures.append("final ledger closed without material artifact map linkage")
    if state.final_ledger_closes and state.stale_current_material_used_as_evidence:
        failures.append("final ledger accepted stale current material as completion evidence")
    if state.final_ledger_closes and state.unresolved_current_material_used_as_evidence:
        failures.append("final ledger accepted unresolved current material as completion evidence")
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
        replace(state, status="accepted", terminal_reason="material_artifact_map_ok"),
    )


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and not material_map_failures(state)


def accepts_only_safe_maps(state: State, trace) -> InvariantResult:
    del trace
    failures = material_map_failures(state)
    if state.status == "accepted" and failures:
        return InvariantResult.fail("unsafe material artifact map path was accepted")
    if state.status == "rejected" and not failures:
        return InvariantResult.fail("safe material artifact map path was rejected")
    return InvariantResult.pass_()


def map_is_reference_only(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and (
        state.map_contains_sealed_body_text
        or not state.map_authority_is_index_only
        or state.controller_summary_used_as_evidence
    ):
        return InvariantResult.fail("accepted material map violated reference-only authority")
    return InvariantResult.pass_()


def worker_reads_are_packet_authorized(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and (
        not state.worker_reads_only_declared_entries
        or state.worker_reads_sealed_body_without_runtime
    ):
        return InvariantResult.fail("accepted worker material-map read escaped packet authority")
    return InvariantResult.pass_()


def reviewer_pass_requires_source_refs(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.reviewer_reports_sufficient and (
        not state.reviewer_checked_source_refs_present
        or state.reviewer_uses_map_summary_only
    ):
        return InvariantResult.fail("accepted reviewer sufficiency without concrete source refs")
    return InvariantResult.pass_()


def final_ledger_rejects_bad_material(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.final_ledger_closes and (
        state.stale_current_material_used_as_evidence
        or state.unresolved_current_material_used_as_evidence
    ):
        return InvariantResult.fail("accepted final ledger with stale or unresolved current material")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepts_only_safe_maps",
        description="Only safe material artifact-map paths can be accepted.",
        predicate=accepts_only_safe_maps,
    ),
    Invariant(
        name="map_is_reference_only",
        description="The material map is metadata-only and never gate evidence by itself.",
        predicate=map_is_reference_only,
    ),
    Invariant(
        name="worker_reads_are_packet_authorized",
        description="Worker material-map reads stay inside the opened packet boundary.",
        predicate=worker_reads_are_packet_authorized,
    ),
    Invariant(
        name="reviewer_pass_requires_source_refs",
        description="Reviewer material sufficiency pass requires concrete checked source refs.",
        predicate=reviewer_pass_requires_source_refs,
    ),
    Invariant(
        name="final_ledger_rejects_bad_material",
        description="Final ledger cannot close with stale or unresolved current material evidence.",
        predicate=final_ledger_rejects_bad_material,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def build_workflow() -> Workflow:
    return Workflow((MaterialArtifactMapStep(),), name="flowpilot_material_artifact_map")


def terminal_predicate(_input_obj, state: State, _trace) -> bool:
    return is_terminal(state)


def hazard_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
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
