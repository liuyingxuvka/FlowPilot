"""FlowGuard model for FlowPilot shared skill maintenance log bookkeeping.

Risk intent brief:
- Validate the smallest PM-owned bookkeeping behavior before prompt cards and
  runtime material-understanding copy-through are changed.
- Protected harms: FlowPilot creating a private maintenance table instead of
  the shared Spark-style log, Controller or Router owning semantic work
  summaries, bookkeeping becoming a reviewer/FlowGuard/route/acceptance gate,
  missing lookup fields, and the shared log replacing existing run-local final
  or skill-improvement reports.
- Modeled state and side effects: PM material understanding, existing-log
  append, missing-log fallback creation, PM report preservation, and non-gating
  handling.
- Hard invariants: accepted flows use a shared log format, include the required
  run lookup fields, preserve the PM report, remain non-gating, and keep the
  skill-improvement/final-report surfaces separate.
- Blindspot: this model checks the abstract PM contract. Prompt text, runtime
  copy-through, and ordinary tests must still verify implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_EXISTING_LOG_APPEND = "valid_existing_log_append"
VALID_MISSING_LOG_CREATE_AND_APPEND = "valid_missing_log_create_and_append"

FLOWPILOT_PRIVATE_LOG = "flowpilot_private_log"
CONTROLLER_WRITES_SEMANTIC_SUMMARY = "controller_writes_semantic_summary"
ROUTER_VALIDATES_LOG_SEMANTICS = "router_validates_log_semantics"
MISSING_REQUIRED_LOOKUP_FIELDS = "missing_required_lookup_fields"
PM_REPORT_NOT_PRESERVED = "pm_report_not_preserved"
BOOKKEEPING_REVIEWER_GATE = "bookkeeping_reviewer_gate"
BOOKKEEPING_FLOWGUARD_GATE = "bookkeeping_flowguard_gate"
BOOKKEEPING_ROUTE_NODE = "bookkeeping_route_node"
BOOKKEEPING_ACCEPTANCE_GATE = "bookkeeping_acceptance_gate"
REPLACES_SKILL_IMPROVEMENT_REPORT = "replaces_skill_improvement_report"
FINAL_REPORT_REQUIRED_AT_START = "final_report_required_at_start"

VALID_SCENARIOS = (
    VALID_EXISTING_LOG_APPEND,
    VALID_MISSING_LOG_CREATE_AND_APPEND,
)
NEGATIVE_SCENARIOS = (
    FLOWPILOT_PRIVATE_LOG,
    CONTROLLER_WRITES_SEMANTIC_SUMMARY,
    ROUTER_VALIDATES_LOG_SEMANTICS,
    MISSING_REQUIRED_LOOKUP_FIELDS,
    PM_REPORT_NOT_PRESERVED,
    BOOKKEEPING_REVIEWER_GATE,
    BOOKKEEPING_FLOWGUARD_GATE,
    BOOKKEEPING_ROUTE_NODE,
    BOOKKEEPING_ACCEPTANCE_GATE,
    REPLACES_SKILL_IMPROVEMENT_REPORT,
    FINAL_REPORT_REQUIRED_AT_START,
)
SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    """One abstract shared-maintenance bookkeeping evaluation tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"
    material_understanding_phase: bool = False
    pm_owns_work_summary: bool = False
    controller_owns_work_summary: bool = False
    router_validates_semantic_content: bool = False

    existing_shared_log_found: bool = False
    fallback_shared_log_created: bool = False
    log_scope: str = "none"  # none | shared | flowpilot_private
    log_format: str = "none"  # none | spark_style_jsonl | flowpilot_private_json
    row_appended: bool = False

    field_skill_flowpilot: bool = False
    field_work_summary: bool = False
    field_workspace_root: bool = False
    field_run_id: bool = False
    field_run_root: bool = False
    final_report_path_optional: bool = False

    pm_report_preserved_in_material_understanding: bool = False
    reviewer_gate_created: bool = False
    flowguard_gate_created: bool = False
    route_node_created: bool = False
    acceptance_gate_created: bool = False
    replaces_skill_improvement_report: bool = False
    final_report_required_before_material_understanding: bool = False
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class SharedMaintenanceLogStep:
    """Model one PM shared-maintenance bookkeeping decision.

    Input x State -> Set(Output x State)
    reads: material-understanding phase, PM/controller/router ownership,
    shared-log discovery, row fields, and gate side effects
    writes: terminal bookkeeping policy decision
    idempotency: scenario facts are monotonic; accepted/rejected terminal
    decisions do not change on repeated ticks.
    """

    name = "SharedMaintenanceLogStep"
    input_description = "FlowPilot PM shared maintenance log bookkeeping tick"
    output_description = "one shared-maintenance transition"
    reads = (
        "material_understanding_phase",
        "pm_owns_work_summary",
        "existing_shared_log_found",
        "fallback_shared_log_created",
        "log_scope",
        "row_appended",
        "required_fields",
        "gate_side_effects",
    )
    writes = ("terminal_shared_maintenance_decision",)
    idempotency = "monotonic shared-maintenance facts"

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


def _valid_existing_log_append() -> State:
    return State(
        status="running",
        scenario=VALID_EXISTING_LOG_APPEND,
        material_understanding_phase=True,
        pm_owns_work_summary=True,
        existing_shared_log_found=True,
        log_scope="shared",
        log_format="spark_style_jsonl",
        row_appended=True,
        field_skill_flowpilot=True,
        field_work_summary=True,
        field_workspace_root=True,
        field_run_id=True,
        field_run_root=True,
        final_report_path_optional=True,
        pm_report_preserved_in_material_understanding=True,
    )


def _valid_missing_log_create_and_append() -> State:
    return replace(
        _valid_existing_log_append(),
        scenario=VALID_MISSING_LOG_CREATE_AND_APPEND,
        existing_shared_log_found=False,
        fallback_shared_log_created=True,
    )


def _scenario_state(scenario: str) -> State:
    if scenario == VALID_EXISTING_LOG_APPEND:
        return _valid_existing_log_append()
    if scenario == VALID_MISSING_LOG_CREATE_AND_APPEND:
        return _valid_missing_log_create_and_append()

    state = replace(_valid_existing_log_append(), scenario=scenario)
    if scenario == FLOWPILOT_PRIVATE_LOG:
        return replace(state, log_scope="flowpilot_private", log_format="flowpilot_private_json")
    if scenario == CONTROLLER_WRITES_SEMANTIC_SUMMARY:
        return replace(state, pm_owns_work_summary=False, controller_owns_work_summary=True)
    if scenario == ROUTER_VALIDATES_LOG_SEMANTICS:
        return replace(state, router_validates_semantic_content=True)
    if scenario == MISSING_REQUIRED_LOOKUP_FIELDS:
        return replace(state, field_workspace_root=False, field_run_root=False)
    if scenario == PM_REPORT_NOT_PRESERVED:
        return replace(state, pm_report_preserved_in_material_understanding=False)
    if scenario == BOOKKEEPING_REVIEWER_GATE:
        return replace(state, reviewer_gate_created=True)
    if scenario == BOOKKEEPING_FLOWGUARD_GATE:
        return replace(state, flowguard_gate_created=True)
    if scenario == BOOKKEEPING_ROUTE_NODE:
        return replace(state, route_node_created=True)
    if scenario == BOOKKEEPING_ACCEPTANCE_GATE:
        return replace(state, acceptance_gate_created=True)
    if scenario == REPLACES_SKILL_IMPROVEMENT_REPORT:
        return replace(state, replaces_skill_improvement_report=True)
    if scenario == FINAL_REPORT_REQUIRED_AT_START:
        return replace(
            state,
            final_report_path_optional=False,
            final_report_required_before_material_understanding=True,
        )
    return state


def bookkeeping_failures(state: State) -> list[str]:
    failures: list[str] = []

    if not state.material_understanding_phase:
        failures.append("shared maintenance bookkeeping is outside PM material understanding")
    if not state.pm_owns_work_summary:
        failures.append("PM does not own the maintenance work summary")
    if state.controller_owns_work_summary:
        failures.append("Controller owns the semantic maintenance summary")
    if state.router_validates_semantic_content:
        failures.append("Router validates semantic maintenance content instead of preserving PM report")
    if state.log_scope != "shared" or state.log_format != "spark_style_jsonl":
        failures.append("maintenance row is not written to a shared Spark-style log")
    if not (state.existing_shared_log_found or state.fallback_shared_log_created):
        failures.append("no existing shared log was found and no shared fallback log was created")
    if not state.row_appended:
        failures.append("PM did not append a maintenance row")
    if not (
        state.field_skill_flowpilot
        and state.field_work_summary
        and state.field_workspace_root
        and state.field_run_id
        and state.field_run_root
    ):
        failures.append("maintenance row lacks required skill summary workspace run_id or run_root fields")
    if not state.pm_report_preserved_in_material_understanding:
        failures.append("PM material understanding does not preserve the shared maintenance record")
    if state.reviewer_gate_created:
        failures.append("bookkeeping created a reviewer gate")
    if state.flowguard_gate_created:
        failures.append("bookkeeping created a FlowGuard gate")
    if state.route_node_created:
        failures.append("bookkeeping created a route node")
    if state.acceptance_gate_created:
        failures.append("bookkeeping became a project acceptance gate")
    if state.replaces_skill_improvement_report:
        failures.append("shared maintenance log replaced the FlowPilot skill-improvement report")
    if state.final_report_required_before_material_understanding:
        failures.append("startup bookkeeping requires final report path before material understanding")
    if not state.final_report_path_optional:
        failures.append("final report path is not optional in the startup maintenance row")
    return failures


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _scenario_state(scenario))
        return

    failures = bookkeeping_failures(state)
    if failures:
        yield Transition(
            f"reject_{state.scenario}",
            replace(state, status="rejected", terminal_reason="; ".join(failures)),
        )
    else:
        yield Transition(
            f"accept_{state.scenario}",
            replace(state, status="accepted", terminal_reason="shared_maintenance_bookkeeping_ok"),
        )


def accepts_only_valid_bookkeeping(state: State, trace) -> InvariantResult:
    del trace
    failures = bookkeeping_failures(state)
    if state.status == "accepted" and failures:
        return InvariantResult.fail("invalid shared maintenance bookkeeping was accepted")
    if state.status == "rejected" and not failures:
        return InvariantResult.fail("valid shared maintenance bookkeeping was rejected")
    return InvariantResult.pass_()


def uses_shared_spark_style_log(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and (state.log_scope != "shared" or state.log_format != "spark_style_jsonl"):
        return InvariantResult.fail("maintenance row is not written to a shared Spark-style log")
    return InvariantResult.pass_()


def pm_owns_summary_router_preserves_report(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    if not state.pm_owns_work_summary or state.controller_owns_work_summary:
        return InvariantResult.fail("PM does not uniquely own the maintenance summary")
    if state.router_validates_semantic_content:
        return InvariantResult.fail("Router validates semantic maintenance content")
    if not state.pm_report_preserved_in_material_understanding:
        return InvariantResult.fail("PM material understanding does not preserve the shared maintenance record")
    return InvariantResult.pass_()


def bookkeeping_remains_non_gating(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    if (
        state.reviewer_gate_created
        or state.flowguard_gate_created
        or state.route_node_created
        or state.acceptance_gate_created
    ):
        return InvariantResult.fail("bookkeeping created a gate or route node")
    return InvariantResult.pass_()


def keeps_existing_reports_separate(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    if state.replaces_skill_improvement_report:
        return InvariantResult.fail("shared maintenance log replaced the FlowPilot skill-improvement report")
    if state.final_report_required_before_material_understanding or not state.final_report_path_optional:
        return InvariantResult.fail("startup bookkeeping incorrectly requires final report data")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepts_only_valid_bookkeeping",
        description="Only valid PM-owned shared maintenance bookkeeping flows are accepted.",
        predicate=accepts_only_valid_bookkeeping,
    ),
    Invariant(
        name="uses_shared_spark_style_log",
        description="FlowPilot must use or create a shared Spark-style maintenance log, not a FlowPilot-private log.",
        predicate=uses_shared_spark_style_log,
    ),
    Invariant(
        name="pm_owns_summary_router_preserves_report",
        description="PM owns the work summary and Router only preserves the PM report.",
        predicate=pm_owns_summary_router_preserves_report,
    ),
    Invariant(
        name="bookkeeping_remains_non_gating",
        description="The shared maintenance row cannot create review, FlowGuard, route, or acceptance gates.",
        predicate=bookkeeping_remains_non_gating,
    ),
    Invariant(
        name="keeps_existing_reports_separate",
        description="The shared maintenance row does not replace skill-improvement or final-report surfaces.",
        predicate=keeps_existing_reports_separate,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


def build_workflow() -> Workflow:
    return Workflow((SharedMaintenanceLogStep(),), name="flowpilot_shared_maintenance_log")


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and not bookkeeping_failures(state)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def hazard_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "NEGATIVE_SCENARIOS",
    "SCENARIOS",
    "VALID_SCENARIOS",
    "State",
    "Tick",
    "bookkeeping_failures",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
]
