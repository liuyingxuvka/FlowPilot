"""FlowGuard model for FlowPilot PM suggestion disposition.

Risk intent brief:
- Validate a unified Project-Manager-owned suggestion loop for reviewer,
  worker, and FlowGuard officer suggestions before changing FlowPilot protocol
  or runtime code.
- Protected harms: reviewer hard blockers being downgraded to advisory notes,
  reviewer preferences overblocking a gate, workers gaining gate authority,
  formal officer blockers being treated as maintenance notes, PM closing a gate
  with undisposed suggestions, vague deferrals, unexplained rejection/waiver,
  route mutation with stale evidence, sealed-body leakage into ledgers, duplicate
  skill-maintenance systems, and heavy empty reports for no-suggestion cases.
- Modeled state and side effects: suggestion source, classification, evidence
  reference, PM disposition, closure state, route-mutation effects, reviewer
  recheck, downstream binding, maintenance-report linkage, and sealed-body
  exclusion.
- Hard invariants: current-gate blockers cannot close until repaired/rechecked,
  waived, routed, or stopped; reviewer blockers require minimum-standard basis;
  worker suggestions cannot block before PM classification; deferred items need
  named targets; rejection/waiver/mutation need rationale and authority; skill
  maintenance remains nonblocking; ledgers carry references only.
- Blindspot: this model checks abstract control-flow and authority semantics.
  Runtime tests must still verify concrete templates, cards, and ledger files.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_REVIEWER_BLOCKER_REPAIRED = "valid_reviewer_blocker_repaired"
VALID_REVIEWER_IMPROVEMENT_DEFERRED = "valid_reviewer_improvement_deferred"
VALID_WORKER_NOTE_REJECTED = "valid_worker_note_rejected"
VALID_OFFICER_MODEL_MUTATES_ROUTE = "valid_officer_model_mutates_route"
VALID_SKILL_MAINTENANCE_RECORDED = "valid_skill_maintenance_recorded"
VALID_NO_SUGGESTION_LIGHTWEIGHT = "valid_no_suggestion_lightweight"

REVIEWER_HARD_BLOCKER_DOWNGRADED = "reviewer_hard_blocker_downgraded"
REVIEWER_PREFERENCE_BLOCKS_GATE = "reviewer_preference_blocks_gate"
WORKER_NOTE_BLOCKS_GATE = "worker_note_blocks_gate"
OFFICER_MAINTENANCE_BLOCKS_PROJECT = "officer_maintenance_blocks_project"
PM_CLOSES_WITH_UNDISPOSED_SUGGESTION = "pm_closes_with_undisposed_suggestion"
DEFER_WITHOUT_TARGET = "defer_without_target"
REJECT_WITHOUT_REASON = "reject_without_reason"
WAIVE_WITHOUT_AUTHORITY = "waive_without_authority"
MUTATE_WITHOUT_STALE_HANDLING = "mutate_without_stale_handling"
LEDGER_LEAKS_SEALED_BODY = "ledger_leaks_sealed_body"
DUPLICATE_SKILL_MAINTENANCE_SYSTEM = "duplicate_skill_maintenance_system"
NO_SUGGESTION_HEAVY_REPORT = "no_suggestion_heavy_report"
REPAIR_WITHOUT_REVIEWER_RECHECK = "repair_without_reviewer_recheck"

VALID_SCENARIOS = (
    VALID_REVIEWER_BLOCKER_REPAIRED,
    VALID_REVIEWER_IMPROVEMENT_DEFERRED,
    VALID_WORKER_NOTE_REJECTED,
    VALID_OFFICER_MODEL_MUTATES_ROUTE,
    VALID_SKILL_MAINTENANCE_RECORDED,
    VALID_NO_SUGGESTION_LIGHTWEIGHT,
)

NEGATIVE_SCENARIOS = (
    REVIEWER_HARD_BLOCKER_DOWNGRADED,
    REVIEWER_PREFERENCE_BLOCKS_GATE,
    WORKER_NOTE_BLOCKS_GATE,
    OFFICER_MAINTENANCE_BLOCKS_PROJECT,
    PM_CLOSES_WITH_UNDISPOSED_SUGGESTION,
    DEFER_WITHOUT_TARGET,
    REJECT_WITHOUT_REASON,
    WAIVE_WITHOUT_AUTHORITY,
    MUTATE_WITHOUT_STALE_HANDLING,
    LEDGER_LEAKS_SEALED_BODY,
    DUPLICATE_SKILL_MAINTENANCE_SYSTEM,
    NO_SUGGESTION_HEAVY_REPORT,
    REPAIR_WITHOUT_REVIEWER_RECHECK,
)

SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS

SOURCE_REVIEWER = "reviewer"
SOURCE_WORKER = "worker"
SOURCE_PROCESS_OFFICER = "process_officer"
SOURCE_PRODUCT_OFFICER = "product_officer"
SOURCE_NONE = "none"

CLASS_CURRENT_GATE_BLOCKER = "current_gate_blocker"
CLASS_CURRENT_NODE_IMPROVEMENT = "current_node_improvement"
CLASS_FUTURE_ROUTE_CANDIDATE = "future_route_candidate"
CLASS_NONBLOCKING_NOTE = "nonblocking_note"
CLASS_FLOWPILOT_SKILL_IMPROVEMENT = "flowpilot_skill_improvement"
CLASS_NONE = "none"

DISPOSITION_ADOPT_NOW = "adopt_now"
DISPOSITION_REPAIR_OR_REISSUE = "repair_or_reissue"
DISPOSITION_MUTATE_ROUTE = "mutate_route"
DISPOSITION_DEFER_TO_NAMED_NODE = "defer_to_named_node"
DISPOSITION_REJECT_WITH_REASON = "reject_with_reason"
DISPOSITION_WAIVE_WITH_AUTHORITY = "waive_with_authority"
DISPOSITION_STOP_FOR_USER = "stop_for_user"
DISPOSITION_RECORD_FOR_FLOWPILOT_MAINTENANCE = "record_for_flowpilot_maintenance"
DISPOSITION_NONE = "none"


@dataclass(frozen=True)
class Tick:
    """One abstract suggestion-disposition tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"

    source_role: str = SOURCE_NONE
    suggestion_logged: bool = False
    no_suggestion_case: bool = False
    heavy_empty_report_written: bool = False
    evidence_refs_recorded: bool = False
    sealed_body_content_in_ledger: bool = False

    classification: str = CLASS_NONE
    reviewer_minimum_standard_failure: bool = False
    officer_formal_model_gate: bool = False
    worker_or_officer_advisory_only: bool = False

    pm_disposition: str = DISPOSITION_NONE
    pm_disposition_recorded: bool = False
    pm_reason_recorded: bool = False
    waiver_authority_recorded: bool = False
    downstream_node_or_gate_named: bool = False
    route_version_impact_recorded: bool = False
    stale_evidence_handled: bool = False
    existing_skill_improvement_report_linked: bool = False
    duplicate_skill_maintenance_system_created: bool = False

    blocker_resolved: bool = False
    same_review_class_recheck_done: bool = False
    gate_closed: bool = False
    route_mutated: bool = False
    stopped_for_user: bool = False
    project_blocked_by_maintenance_note: bool = False
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class PMSuggestionDispositionStep:
    """Model one FlowPilot PM suggestion-disposition transition.

    Input x State -> Set(Output x State)
    reads: role output summary, suggestion classification, evidence refs,
    authority basis, PM disposition body, closure state
    writes: suggestion ledger item, PM disposition, route/closure effect
    idempotency: one abstract suggestion item is classified and disposed once;
    repeated ticks do not duplicate ledger entries.
    """

    name = "PMSuggestionDispositionStep"
    input_description = "FlowPilot PM suggestion-disposition tick"
    output_description = "one PM suggestion-disposition transition"
    reads = (
        "role_output_summary",
        "suggestion_classification",
        "evidence_refs",
        "authority_basis",
        "pm_disposition",
        "closure_state",
    )
    writes = (
        "pm_suggestion_ledger_item",
        "pm_disposition_record",
        "route_or_closure_effect",
    )
    idempotency = "single suggestion item disposition is monotonic"

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
        source_role=SOURCE_REVIEWER,
        suggestion_logged=True,
        evidence_refs_recorded=True,
        classification=CLASS_NONBLOCKING_NOTE,
        pm_disposition=DISPOSITION_REJECT_WITH_REASON,
        pm_disposition_recorded=True,
        pm_reason_recorded=True,
        gate_closed=True,
    )


def _scenario_state(scenario: str) -> State:
    if scenario == VALID_REVIEWER_BLOCKER_REPAIRED:
        return replace(
            _base_state(scenario),
            classification=CLASS_CURRENT_GATE_BLOCKER,
            reviewer_minimum_standard_failure=True,
            pm_disposition=DISPOSITION_REPAIR_OR_REISSUE,
            blocker_resolved=True,
            same_review_class_recheck_done=True,
        )
    if scenario == VALID_REVIEWER_IMPROVEMENT_DEFERRED:
        return replace(
            _base_state(scenario),
            classification=CLASS_FUTURE_ROUTE_CANDIDATE,
            pm_disposition=DISPOSITION_DEFER_TO_NAMED_NODE,
            downstream_node_or_gate_named=True,
        )
    if scenario == VALID_WORKER_NOTE_REJECTED:
        return replace(
            _base_state(scenario),
            source_role=SOURCE_WORKER,
            worker_or_officer_advisory_only=True,
            classification=CLASS_NONBLOCKING_NOTE,
            pm_disposition=DISPOSITION_REJECT_WITH_REASON,
        )
    if scenario == VALID_OFFICER_MODEL_MUTATES_ROUTE:
        return replace(
            _base_state(scenario),
            source_role=SOURCE_PROCESS_OFFICER,
            classification=CLASS_CURRENT_GATE_BLOCKER,
            officer_formal_model_gate=True,
            pm_disposition=DISPOSITION_MUTATE_ROUTE,
            gate_closed=False,
            route_mutated=True,
            route_version_impact_recorded=True,
            stale_evidence_handled=True,
        )
    if scenario == VALID_SKILL_MAINTENANCE_RECORDED:
        return replace(
            _base_state(scenario),
            source_role=SOURCE_PRODUCT_OFFICER,
            classification=CLASS_FLOWPILOT_SKILL_IMPROVEMENT,
            pm_disposition=DISPOSITION_RECORD_FOR_FLOWPILOT_MAINTENANCE,
            existing_skill_improvement_report_linked=True,
        )
    if scenario == VALID_NO_SUGGESTION_LIGHTWEIGHT:
        return State(
            status="running",
            scenario=scenario,
            no_suggestion_case=True,
            gate_closed=True,
        )

    if scenario == REVIEWER_HARD_BLOCKER_DOWNGRADED:
        return replace(
            _base_state(scenario),
            reviewer_minimum_standard_failure=True,
            classification=CLASS_NONBLOCKING_NOTE,
        )
    if scenario == REVIEWER_PREFERENCE_BLOCKS_GATE:
        return replace(
            _base_state(scenario),
            classification=CLASS_CURRENT_GATE_BLOCKER,
            reviewer_minimum_standard_failure=False,
            pm_disposition=DISPOSITION_REPAIR_OR_REISSUE,
            blocker_resolved=True,
            same_review_class_recheck_done=True,
        )
    if scenario == WORKER_NOTE_BLOCKS_GATE:
        return replace(
            _base_state(scenario),
            source_role=SOURCE_WORKER,
            worker_or_officer_advisory_only=True,
            classification=CLASS_CURRENT_GATE_BLOCKER,
            pm_disposition=DISPOSITION_REPAIR_OR_REISSUE,
            blocker_resolved=True,
        )
    if scenario == OFFICER_MAINTENANCE_BLOCKS_PROJECT:
        return replace(
            _base_state(scenario),
            source_role=SOURCE_PROCESS_OFFICER,
            classification=CLASS_FLOWPILOT_SKILL_IMPROVEMENT,
            pm_disposition=DISPOSITION_RECORD_FOR_FLOWPILOT_MAINTENANCE,
            existing_skill_improvement_report_linked=True,
            gate_closed=False,
            project_blocked_by_maintenance_note=True,
        )
    if scenario == PM_CLOSES_WITH_UNDISPOSED_SUGGESTION:
        return replace(
            _base_state(scenario),
            pm_disposition=DISPOSITION_NONE,
            pm_disposition_recorded=False,
            pm_reason_recorded=False,
        )
    if scenario == DEFER_WITHOUT_TARGET:
        return replace(
            _base_state(scenario),
            classification=CLASS_FUTURE_ROUTE_CANDIDATE,
            pm_disposition=DISPOSITION_DEFER_TO_NAMED_NODE,
            downstream_node_or_gate_named=False,
        )
    if scenario == REJECT_WITHOUT_REASON:
        return replace(_base_state(scenario), pm_reason_recorded=False)
    if scenario == WAIVE_WITHOUT_AUTHORITY:
        return replace(
            _base_state(scenario),
            classification=CLASS_CURRENT_GATE_BLOCKER,
            reviewer_minimum_standard_failure=True,
            pm_disposition=DISPOSITION_WAIVE_WITH_AUTHORITY,
            waiver_authority_recorded=False,
        )
    if scenario == MUTATE_WITHOUT_STALE_HANDLING:
        return replace(
            _base_state(scenario),
            source_role=SOURCE_PROCESS_OFFICER,
            classification=CLASS_CURRENT_GATE_BLOCKER,
            officer_formal_model_gate=True,
            pm_disposition=DISPOSITION_MUTATE_ROUTE,
            gate_closed=False,
            route_mutated=True,
            route_version_impact_recorded=True,
            stale_evidence_handled=False,
        )
    if scenario == LEDGER_LEAKS_SEALED_BODY:
        return replace(_base_state(scenario), sealed_body_content_in_ledger=True)
    if scenario == DUPLICATE_SKILL_MAINTENANCE_SYSTEM:
        return replace(
            _base_state(scenario),
            classification=CLASS_FLOWPILOT_SKILL_IMPROVEMENT,
            pm_disposition=DISPOSITION_RECORD_FOR_FLOWPILOT_MAINTENANCE,
            existing_skill_improvement_report_linked=False,
            duplicate_skill_maintenance_system_created=True,
        )
    if scenario == NO_SUGGESTION_HEAVY_REPORT:
        return State(
            status="running",
            scenario=scenario,
            no_suggestion_case=True,
            heavy_empty_report_written=True,
            gate_closed=True,
        )
    if scenario == REPAIR_WITHOUT_REVIEWER_RECHECK:
        return replace(
            _base_state(scenario),
            classification=CLASS_CURRENT_GATE_BLOCKER,
            reviewer_minimum_standard_failure=True,
            pm_disposition=DISPOSITION_REPAIR_OR_REISSUE,
            blocker_resolved=True,
            same_review_class_recheck_done=False,
        )
    return _base_state(scenario)


def suggestion_failures(state: State) -> list[str]:
    failures: list[str] = []

    if state.no_suggestion_case:
        if state.heavy_empty_report_written:
            failures.append("no-suggestion case wrote a heavy empty report")
        return failures

    if not state.suggestion_logged:
        failures.append("suggestion was not recorded in the PM suggestion ledger")
    if not state.evidence_refs_recorded:
        failures.append("suggestion lacks evidence references")
    if state.sealed_body_content_in_ledger:
        failures.append("suggestion ledger contains sealed body content")
    if not state.pm_disposition_recorded or state.pm_disposition == DISPOSITION_NONE:
        failures.append("PM closed or advanced without disposing the suggestion")

    if (
        state.reviewer_minimum_standard_failure
        and state.classification != CLASS_CURRENT_GATE_BLOCKER
    ):
        failures.append("reviewer hard blocker was downgraded to a soft note")

    if (
        state.source_role == SOURCE_REVIEWER
        and state.classification == CLASS_CURRENT_GATE_BLOCKER
        and not state.reviewer_minimum_standard_failure
    ):
        failures.append("reviewer blocked a gate without minimum-standard failure")

    if (
        state.source_role == SOURCE_WORKER
        and state.classification == CLASS_CURRENT_GATE_BLOCKER
    ):
        failures.append("worker advisory note was treated as a gate blocker")

    if (
        state.source_role in {SOURCE_PROCESS_OFFICER, SOURCE_PRODUCT_OFFICER}
        and state.classification == CLASS_CURRENT_GATE_BLOCKER
        and not state.officer_formal_model_gate
    ):
        failures.append("officer advisory note was treated as a formal gate blocker")

    if (
        state.classification == CLASS_FLOWPILOT_SKILL_IMPROVEMENT
        and state.project_blocked_by_maintenance_note
    ):
        failures.append("FlowPilot maintenance suggestion blocked current project completion")

    if (
        state.classification == CLASS_FLOWPILOT_SKILL_IMPROVEMENT
        and state.pm_disposition == DISPOSITION_RECORD_FOR_FLOWPILOT_MAINTENANCE
        and (
            not state.existing_skill_improvement_report_linked
            or state.duplicate_skill_maintenance_system_created
        )
    ):
        failures.append("FlowPilot maintenance suggestion did not link to existing skill-improvement report")

    if (
        state.pm_disposition == DISPOSITION_DEFER_TO_NAMED_NODE
        and not state.downstream_node_or_gate_named
    ):
        failures.append("PM deferred a suggestion without naming a downstream node or gate")

    if state.pm_disposition == DISPOSITION_REJECT_WITH_REASON and not state.pm_reason_recorded:
        failures.append("PM rejected a suggestion without a reason")

    if (
        state.pm_disposition == DISPOSITION_WAIVE_WITH_AUTHORITY
        and not (state.waiver_authority_recorded and state.pm_reason_recorded)
    ):
        failures.append("PM waived a suggestion without authority and reason")

    if state.pm_disposition == DISPOSITION_MUTATE_ROUTE and not (
        state.route_mutated
        and state.route_version_impact_recorded
        and state.stale_evidence_handled
    ):
        failures.append("PM route mutation omitted route-version or stale-evidence handling")

    if (
        state.classification == CLASS_CURRENT_GATE_BLOCKER
        and state.pm_disposition == DISPOSITION_REPAIR_OR_REISSUE
        and not (state.blocker_resolved and state.same_review_class_recheck_done)
    ):
        failures.append("current-gate blocker repair closed without same review-class recheck")

    if state.gate_closed and state.classification == CLASS_CURRENT_GATE_BLOCKER:
        safe_close = (
            state.pm_disposition == DISPOSITION_WAIVE_WITH_AUTHORITY
            and state.waiver_authority_recorded
            and state.pm_reason_recorded
        ) or (
            state.pm_disposition == DISPOSITION_REPAIR_OR_REISSUE
            and state.blocker_resolved
            and state.same_review_class_recheck_done
        )
        if not safe_close:
            failures.append("gate closed while current-gate blocker remained unresolved")

    if state.status in {"accepted", "rejected"} and not (
        state.gate_closed or state.route_mutated or state.stopped_for_user
    ):
        failures.append("terminal suggestion path lacks closure, route mutation, or user stop")

    return failures


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _scenario_state(scenario))
        return

    failures = suggestion_failures(state)
    if failures:
        yield Transition(
            f"reject_{state.scenario}",
            replace(state, status="rejected", terminal_reason="; ".join(failures)),
        )
        return
    yield Transition(
        f"accept_{state.scenario}",
        replace(state, status="accepted", terminal_reason="pm_suggestion_disposition_ok"),
    )


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and not suggestion_failures(state)


def accepts_only_safe_dispositions(state: State, trace) -> InvariantResult:
    del trace
    failures = suggestion_failures(state)
    if state.status == "accepted" and failures:
        return InvariantResult.fail("unsafe PM suggestion disposition was accepted")
    if state.status == "rejected" and not failures:
        return InvariantResult.fail("safe PM suggestion disposition was rejected")
    return InvariantResult.pass_()


def current_gate_blockers_require_resolution(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in suggestion_failures(state):
        if "current-gate blocker" in failure or "minimum-standard" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def advisory_roles_do_not_gain_gate_authority(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in suggestion_failures(state):
        if "worker advisory" in failure or "officer advisory" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def pm_dispositions_are_traceable(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in suggestion_failures(state):
        if (
            "without disposing" in failure
            or "without naming" in failure
            or "without a reason" in failure
            or "without authority" in failure
            or "stale-evidence" in failure
        ):
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def maintenance_suggestions_remain_nonblocking(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in suggestion_failures(state):
        if "maintenance suggestion" in failure or "skill-improvement report" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def ledger_records_are_reference_only(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.sealed_body_content_in_ledger:
        return InvariantResult.fail("accepted ledger entry leaked sealed body content")
    return InvariantResult.pass_()


def no_suggestion_cases_stay_lightweight(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.no_suggestion_case and state.heavy_empty_report_written:
        return InvariantResult.fail("accepted no-suggestion case wrote heavy empty report")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepts_only_safe_dispositions",
        description="Only safe PM suggestion disposition paths can be accepted.",
        predicate=accepts_only_safe_dispositions,
    ),
    Invariant(
        name="current_gate_blockers_require_resolution",
        description="Current-gate blockers require repair/recheck, waiver, route mutation, or stop before closure.",
        predicate=current_gate_blockers_require_resolution,
    ),
    Invariant(
        name="advisory_roles_do_not_gain_gate_authority",
        description="Worker and advisory officer notes cannot become gate authority before PM classification.",
        predicate=advisory_roles_do_not_gain_gate_authority,
    ),
    Invariant(
        name="pm_dispositions_are_traceable",
        description="PM disposition must include target, reason, authority, and stale-evidence handling where required.",
        predicate=pm_dispositions_are_traceable,
    ),
    Invariant(
        name="maintenance_suggestions_remain_nonblocking",
        description="FlowPilot maintenance suggestions link to the existing skill-improvement report and do not block the current project.",
        predicate=maintenance_suggestions_remain_nonblocking,
    ),
    Invariant(
        name="ledger_records_are_reference_only",
        description="Suggestion ledger entries reference evidence paths and never contain sealed body content.",
        predicate=ledger_records_are_reference_only,
    ),
    Invariant(
        name="no_suggestion_cases_stay_lightweight",
        description="No-suggestion cases do not create heavy empty reports.",
        predicate=no_suggestion_cases_stay_lightweight,
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
    return Workflow((PMSuggestionDispositionStep(),), name="flowpilot_pm_suggestion_disposition")


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
    "next_safe_states",
    "next_states",
    "suggestion_failures",
    "terminal_predicate",
]
