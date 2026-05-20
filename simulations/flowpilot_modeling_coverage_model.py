"""FlowGuard model for FlowPilot modeling coverage planning.

Risk Purpose Header:
- This model uses FlowGuard to review the FlowPilot protocol change that makes
  FlowGuard capability snapshots, PM product/process modeling plans, and
  officer-owned model families explicit before route execution.
- It guards against treating FlowGuard as an ordinary optional child skill,
  skipping the startup snapshot, accepting unplanned single-model overcollapse,
  letting a child-skill manifest substitute for officer model-family coverage,
  activating a route before process model-family acceptance, or completing with
  unresolved model coverage.
- Future agents should run
  `python simulations/run_flowpilot_modeling_coverage_checks.py` before changing
  PM product modeling, Process/Product FlowGuard officer cards, child-skill
  manifest closure, route activation, or final ledger modeling-coverage rules.

Risk intent brief:
- The user wants FlowPilot to keep the core order: product model first, process
  model second, route execution third.
- Before product modeling, PM reads a current startup FlowGuard capability
  snapshot and plans which product model families are separate, merged, or
  intentionally skipped.
- After product model acceptance, PM selects ordinary child skills and maps them
  to product/route evidence.
- Before process modeling, PM plans process model families so Process Officer
  can prove the process covers the accepted product model family and child-skill
  manifest.
- Mid-run FlowGuard upgrades are intentionally out of scope; one startup
  snapshot is authoritative for the run.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


INTENDED_MODEL_COVERAGE = "intended_model_coverage"
FLOWGUARD_OPTIONAL_CHILD_SKILL = "flowguard_optional_child_skill"
MISSING_STARTUP_SNAPSHOT = "missing_startup_snapshot"
SNAPSHOT_NOT_ROUTER_GENERATED = "snapshot_not_router_generated"
PM_IGNORES_SNAPSHOT = "pm_ignores_snapshot"
MISSING_PRODUCT_MODELING_PLAN = "missing_product_modeling_plan"
PRODUCT_SINGLE_MODEL_OVERCOLLAPSE = "product_single_model_overcollapse"
PRODUCT_REPORT_MISSING_PLANNED_FAMILY = "product_report_missing_planned_family"
CHILD_SKILL_BEFORE_PRODUCT_MODEL = "child_skill_before_product_model"
MANIFEST_ONLY_MODEL_COVERAGE = "manifest_only_model_coverage"
MISSING_PROCESS_MODELING_PLAN = "missing_process_modeling_plan"
PROCESS_PLAN_OMITS_PRODUCT_OR_MANIFEST = "process_plan_omits_product_or_manifest"
PROCESS_REPORT_MISSING_PLANNED_FAMILY = "process_report_missing_planned_family"
ROUTE_ACTIVATED_BEFORE_MODEL_FAMILIES = "route_activated_before_model_families"
FINAL_LEDGER_UNRESOLVED_MODEL_FAMILY = "final_ledger_unresolved_model_family"

VALID_SCENARIOS = (INTENDED_MODEL_COVERAGE,)
NEGATIVE_SCENARIOS = (
    FLOWGUARD_OPTIONAL_CHILD_SKILL,
    MISSING_STARTUP_SNAPSHOT,
    SNAPSHOT_NOT_ROUTER_GENERATED,
    PM_IGNORES_SNAPSHOT,
    MISSING_PRODUCT_MODELING_PLAN,
    PRODUCT_SINGLE_MODEL_OVERCOLLAPSE,
    PRODUCT_REPORT_MISSING_PLANNED_FAMILY,
    CHILD_SKILL_BEFORE_PRODUCT_MODEL,
    MANIFEST_ONLY_MODEL_COVERAGE,
    MISSING_PROCESS_MODELING_PLAN,
    PROCESS_PLAN_OMITS_PRODUCT_OR_MANIFEST,
    PROCESS_REPORT_MISSING_PLANNED_FAMILY,
    ROUTE_ACTIVATED_BEFORE_MODEL_FAMILIES,
    FINAL_LEDGER_UNRESOLVED_MODEL_FAMILY,
)
SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS
MAX_SEQUENCE_LENGTH = 3


@dataclass(frozen=True)
class Tick:
    """One modeling-coverage protocol evaluation tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | selected | accepted | rejected
    scenario: str = "none"
    terminal_reason: str = ""

    flowguard_treated_as_foundation: bool = False
    startup_snapshot_written: bool = False
    startup_snapshot_generated_by_router: bool = False
    startup_snapshot_has_portable_resolution: bool = False
    startup_snapshot_has_version_paths_hashes: bool = False
    pm_references_snapshot_before_product_modeling: bool = False

    product_modeling_plan_written: bool = False
    product_plan_references_snapshot: bool = False
    product_model_families_declared: bool = False
    product_merge_or_skip_reasons_written: bool = False
    product_distinct_risk_families_present: bool = True
    product_officer_report_references_plan: bool = False
    product_officer_covers_planned_families: bool = False
    product_model_family_pm_accepted: bool = False

    ordinary_child_skills_selected_after_product_acceptance: bool = False
    child_skill_manifest_maps_to_product_family: bool = False
    child_skill_manifest_used_as_model_family_coverage: bool = False

    process_modeling_plan_written: bool = False
    process_plan_references_snapshot: bool = False
    process_plan_references_product_family: bool = False
    process_plan_references_child_manifest: bool = False
    process_model_families_declared: bool = False
    process_merge_or_skip_reasons_written: bool = False
    process_officer_report_references_plan: bool = False
    process_officer_covers_planned_families: bool = False
    process_model_family_pm_accepted: bool = False

    route_activated: bool = False
    final_ledger_references_modeling_coverage: bool = False
    final_ledger_has_unresolved_model_families: bool = False
    completion_declared: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _base_valid_state() -> State:
    return State(
        status="selected",
        scenario=INTENDED_MODEL_COVERAGE,
        flowguard_treated_as_foundation=True,
        startup_snapshot_written=True,
        startup_snapshot_generated_by_router=True,
        startup_snapshot_has_portable_resolution=True,
        startup_snapshot_has_version_paths_hashes=True,
        pm_references_snapshot_before_product_modeling=True,
        product_modeling_plan_written=True,
        product_plan_references_snapshot=True,
        product_model_families_declared=True,
        product_merge_or_skip_reasons_written=True,
        product_distinct_risk_families_present=True,
        product_officer_report_references_plan=True,
        product_officer_covers_planned_families=True,
        product_model_family_pm_accepted=True,
        ordinary_child_skills_selected_after_product_acceptance=True,
        child_skill_manifest_maps_to_product_family=True,
        child_skill_manifest_used_as_model_family_coverage=False,
        process_modeling_plan_written=True,
        process_plan_references_snapshot=True,
        process_plan_references_product_family=True,
        process_plan_references_child_manifest=True,
        process_model_families_declared=True,
        process_merge_or_skip_reasons_written=True,
        process_officer_report_references_plan=True,
        process_officer_covers_planned_families=True,
        process_model_family_pm_accepted=True,
        route_activated=True,
        final_ledger_references_modeling_coverage=True,
        final_ledger_has_unresolved_model_families=False,
        completion_declared=True,
    )


def intended_plan_state() -> State:
    return replace(
        _base_valid_state(),
        status="accepted",
        terminal_reason="modeling_coverage_contract_ok",
    )


def scenario_state(scenario: str) -> State:
    base = _base_valid_state()
    if scenario == INTENDED_MODEL_COVERAGE:
        return base
    replacements = {
        FLOWGUARD_OPTIONAL_CHILD_SKILL: {
            "flowguard_treated_as_foundation": False,
        },
        MISSING_STARTUP_SNAPSHOT: {
            "startup_snapshot_written": False,
            "startup_snapshot_generated_by_router": False,
            "startup_snapshot_has_portable_resolution": False,
            "startup_snapshot_has_version_paths_hashes": False,
        },
        SNAPSHOT_NOT_ROUTER_GENERATED: {
            "startup_snapshot_generated_by_router": False,
            "startup_snapshot_has_portable_resolution": False,
        },
        PM_IGNORES_SNAPSHOT: {
            "pm_references_snapshot_before_product_modeling": False,
            "product_plan_references_snapshot": False,
        },
        MISSING_PRODUCT_MODELING_PLAN: {
            "product_modeling_plan_written": False,
            "product_model_families_declared": False,
        },
        PRODUCT_SINGLE_MODEL_OVERCOLLAPSE: {
            "product_model_families_declared": False,
            "product_merge_or_skip_reasons_written": False,
        },
        PRODUCT_REPORT_MISSING_PLANNED_FAMILY: {
            "product_officer_covers_planned_families": False,
        },
        CHILD_SKILL_BEFORE_PRODUCT_MODEL: {
            "product_model_family_pm_accepted": False,
            "ordinary_child_skills_selected_after_product_acceptance": True,
        },
        MANIFEST_ONLY_MODEL_COVERAGE: {
            "product_officer_covers_planned_families": False,
            "process_officer_covers_planned_families": False,
            "child_skill_manifest_used_as_model_family_coverage": True,
        },
        MISSING_PROCESS_MODELING_PLAN: {
            "process_modeling_plan_written": False,
            "process_model_families_declared": False,
        },
        PROCESS_PLAN_OMITS_PRODUCT_OR_MANIFEST: {
            "process_plan_references_product_family": False,
            "process_plan_references_child_manifest": False,
        },
        PROCESS_REPORT_MISSING_PLANNED_FAMILY: {
            "process_officer_covers_planned_families": False,
        },
        ROUTE_ACTIVATED_BEFORE_MODEL_FAMILIES: {
            "product_model_family_pm_accepted": False,
            "process_model_family_pm_accepted": False,
            "route_activated": True,
        },
        FINAL_LEDGER_UNRESOLVED_MODEL_FAMILY: {
            "final_ledger_has_unresolved_model_families": True,
            "completion_declared": True,
        },
    }[scenario]
    return replace(base, scenario=scenario, **replacements)


def modeling_coverage_failures(state: State) -> list[str]:
    failures: list[str] = []
    if not state.flowguard_treated_as_foundation:
        failures.append("FlowGuard was treated as an optional ordinary child skill")
    if not state.startup_snapshot_written:
        failures.append("startup FlowGuard capability snapshot is missing")
    if state.startup_snapshot_written and not state.startup_snapshot_generated_by_router:
        failures.append("startup FlowGuard capability snapshot was not generated by Router startup script")
    if state.startup_snapshot_written and not state.startup_snapshot_has_portable_resolution:
        failures.append("startup FlowGuard capability snapshot does not record portable skill resolution")
    if state.startup_snapshot_written and not state.startup_snapshot_has_version_paths_hashes:
        failures.append("startup FlowGuard capability snapshot lacks version paths or hashes")
    if not state.pm_references_snapshot_before_product_modeling:
        failures.append("PM product modeling started without referencing the startup FlowGuard snapshot")

    if not state.product_modeling_plan_written:
        failures.append("PM product modeling plan is missing before Product Officer modeling")
    if state.product_modeling_plan_written and not state.product_plan_references_snapshot:
        failures.append("PM product modeling plan does not reference the startup FlowGuard snapshot")
    if state.product_distinct_risk_families_present and not (
        state.product_model_families_declared
        or state.product_merge_or_skip_reasons_written
    ):
        failures.append("distinct product risk families were collapsed into one model without merge or skip reasons")
    if state.product_officer_report_references_plan and not state.product_modeling_plan_written:
        failures.append("Product Officer report referenced a missing product modeling plan")
    if state.product_model_family_pm_accepted and not (
        state.product_modeling_plan_written
        and state.product_officer_report_references_plan
        and state.product_officer_covers_planned_families
    ):
        failures.append("PM accepted product model family before planned product families were covered")
    if not state.product_officer_covers_planned_families:
        failures.append("Product Officer report omitted a planned product model family")

    if (
        state.ordinary_child_skills_selected_after_product_acceptance
        and not state.product_model_family_pm_accepted
    ):
        failures.append("ordinary child skills were selected before PM accepted the product model family")
    if state.child_skill_manifest_used_as_model_family_coverage:
        failures.append("child-skill manifest was used as officer model-family coverage")
    if state.child_skill_manifest_maps_to_product_family and not state.product_model_family_pm_accepted:
        failures.append("child-skill manifest mapped to a product model family before PM accepted it")

    if not state.process_modeling_plan_written:
        failures.append("PM process modeling plan is missing before Process Officer modeling")
    if state.process_modeling_plan_written and not state.process_plan_references_snapshot:
        failures.append("PM process modeling plan does not reference the startup FlowGuard snapshot")
    if state.process_modeling_plan_written and not (
        state.process_plan_references_product_family
        and state.process_plan_references_child_manifest
    ):
        failures.append("process modeling plan does not consume accepted product family and child-skill manifest")
    if not (
        state.process_model_families_declared
        or state.process_merge_or_skip_reasons_written
    ):
        failures.append("process model families were not declared or explicitly merged/skipped")
    if not state.process_officer_covers_planned_families:
        failures.append("Process Officer report omitted a planned process model family")
    if state.process_model_family_pm_accepted and not (
        state.process_modeling_plan_written
        and state.process_officer_report_references_plan
        and state.process_officer_covers_planned_families
    ):
        failures.append("PM accepted process model family before planned process families were covered")

    if state.route_activated and not (
        state.product_model_family_pm_accepted
        and state.process_model_family_pm_accepted
    ):
        failures.append("route activated before accepted product and process model families")
    if state.completion_declared and not state.final_ledger_references_modeling_coverage:
        failures.append("final ledger omitted modeling coverage references")
    if state.completion_declared and state.final_ledger_has_unresolved_model_families:
        failures.append("terminal completion declared with unresolved model families")
    return failures


class ModelingCoverageStep:
    """Review one FlowPilot modeling-coverage scenario.

    Input x State -> Set(Output x State)
    reads: startup snapshot, PM product/process modeling plans, officer model
    family reports, child-skill manifest projection, route activation, and
    terminal ledger coverage
    writes: accepted or rejected scenario decision
    idempotency: scenario evaluation is read-only over protocol facts
    """

    name = "ModelingCoverageStep"
    reads = (
        "flowguard_snapshot",
        "product_modeling_plan",
        "product_model_family_report",
        "child_skill_manifest",
        "process_modeling_plan",
        "process_model_family_report",
        "route_activation",
        "final_ledger",
    )
    writes = ("modeling_coverage_decision",)
    input_description = "FlowPilot modeling coverage protocol tick"
    output_description = "one modeling coverage scenario decision"
    idempotency = "read-only scenario classification"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"accepted", "rejected"}:
        return ()
    if state.status == "new":
        return tuple(
            Transition(f"select_{scenario}", scenario_state(scenario))
            for scenario in SCENARIOS
        )
    failures = modeling_coverage_failures(state)
    if failures:
        return (
            Transition(
                f"reject_{state.scenario}",
                replace(state, status="rejected", terminal_reason="; ".join(failures)),
            ),
        )
    return (
        Transition(
            f"accept_{state.scenario}",
            replace(state, status="accepted", terminal_reason="modeling_coverage_contract_ok"),
        ),
    )


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    protocol_failures = modeling_coverage_failures(state)
    if state.status == "accepted" and protocol_failures:
        failures.append("invalid modeling coverage state was accepted")
    if state.status == "rejected" and state.scenario in VALID_SCENARIOS:
        failures.append("valid modeling coverage state was rejected")
    if (
        state.status == "accepted"
        and state.scenario in NEGATIVE_SCENARIOS
        and not protocol_failures
    ):
        failures.append("negative modeling coverage scenario reached acceptance without a failure")
    return failures


def modeling_coverage_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_modeling_coverage_plans",
        description=(
            "FlowPilot accepts route execution and closure only after a startup "
            "FlowGuard snapshot, PM product/process modeling plans, officer "
            "model-family reports, child-skill projection, and final coverage "
            "ledger are current for the run."
        ),
        predicate=modeling_coverage_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((ModelingCoverageStep(),), name="flowpilot_modeling_coverage")


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and state.scenario in VALID_SCENARIOS


def hazard_states() -> dict[str, State]:
    return {scenario: scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}


def model_plan() -> dict[str, object]:
    return {
        "schema_version": "flowpilot.modeling_coverage_plan.v1",
        "startup_snapshot": ".flowpilot/runs/<run-id>/flowguard/capability_snapshot.json",
        "startup_snapshot_owner": "router_startup_seed",
        "portable_resolution_required": True,
        "product_modeling_plan": ".flowpilot/runs/<run-id>/flowguard/product_modeling_plan.json",
        "process_modeling_plan": ".flowpilot/runs/<run-id>/flowguard/process_modeling_plan.json",
        "core_order": [
            "startup FlowGuard capability snapshot",
            "PM Product Modeling Plan",
            "Product Officer product model family",
            "PM accepts product model family",
            "PM child-skill manifest",
            "PM Process Modeling Plan",
            "Process Officer process model family",
            "PM accepts process model family",
            "route execution",
            "final route-wide modeling coverage ledger",
        ],
        "mid_run_flowguard_upgrade_policy": "not_tracked; startup snapshot is authoritative for the run",
    }
