"""FlowGuard model for FlowPilot PM-first worker package absorption.

Risk purpose:
- Uses FlowGuard (https://github.com/liuyingxuvka/FlowGuard) to review the
  FlowPilot protocol change where PM-issued worker package results return to
  the Project Manager before any reviewer gate.
- Guards against raw worker results being sent to the human-like reviewer,
  PM decisions using undisposed worker results, accidental removal of critical
  reviewer gates, resume paths bypassing PM disposition, legacy reviewer-relay
  flags becoming current proof, and Controller sealed-body access.
- Update and run this model whenever package result routing, reviewer gate
  authority, resume result handling, or packet/result envelope contracts change.
- Companion check command:
  `python simulations/run_flowpilot_pm_package_absorption_checks.py`.

Risk intent brief:
- Protected harm: FlowPilot authority drift, where the reviewer becomes a
  receiving clerk for PM-issued worker packages or, conversely, reviewer hard
  gates are removed while cleaning up noisy package reviews.
- Model-critical state: PM package authorship, worker result return, mechanical
  result validation, PM relay, PM disposition, formal PM gate package creation,
  reviewer gate review, route/node/material/research evidence use, resume
  result handling, legacy direct-review flags, and Controller body isolation.
- Adversarial branches: raw direct-to-reviewer routing, hidden PM forwarding
  to reviewer, node completion without reviewer gate, formal evidence from
  undisposed worker result, reviewer gate without PM package, removed critical
  gate, resume direct-to-reviewer, material/research decision without gate,
  legacy reviewer relay used as current acceptance, and Controller body reads.
- Hard invariants: every PM-issued worker result returns to PM; reviewer reviews
  only PM-built formal gate packages; PM disposition is mandatory before formal
  evidence use; protected route/node/material/research/closure gates still
  require reviewer participation; resume follows the same PM-first rule; legacy
  reviewer-relay flags are audit history only; Controller remains envelope-only.
- Blindspot: this is an abstract protocol model. Runtime tests must still check
  concrete router actions, cards, contract files, and installed-skill sync.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_CURRENT_NODE_PM_GATE = "valid_current_node_pm_gate"
VALID_MATERIAL_PM_GATE = "valid_material_pm_gate"
VALID_RESEARCH_PM_GATE = "valid_research_pm_gate"
VALID_RESUME_RESULT_TO_PM = "valid_resume_result_to_pm"
VALID_CRITICAL_GATE_WITHOUT_WORKER_PACKAGE = "valid_critical_gate_without_worker_package"

RAW_WORKER_RESULT_RELAYED_TO_REVIEWER = "raw_worker_result_relayed_to_reviewer"
FORMAL_EVIDENCE_FROM_UNDISPOSITIONED_RESULT = "formal_evidence_from_undispositioned_result"
REVIEWER_STARTED_WITHOUT_PM_GATE_PACKAGE = "reviewer_started_without_pm_gate_package"
NODE_COMPLETION_WITHOUT_REVIEWER_GATE = "node_completion_without_reviewer_gate"
CRITICAL_REVIEWER_GATE_REMOVED = "critical_reviewer_gate_removed"
RESUME_RESULT_DIRECT_TO_REVIEWER = "resume_result_direct_to_reviewer"
MATERIAL_RESEARCH_DECISION_WITHOUT_GATE = "material_research_decision_without_gate"
CONTROLLER_READS_SEALED_BODY = "controller_reads_sealed_body"
LEGACY_REVIEWER_RELAY_USED_AS_CURRENT_ACCEPTANCE = (
    "legacy_reviewer_relay_used_as_current_acceptance"
)
PM_FORWARDED_RAW_PACKAGE_TO_REVIEWER = "pm_forwarded_raw_package_to_reviewer"

VALID_SCENARIOS = (
    VALID_CURRENT_NODE_PM_GATE,
    VALID_MATERIAL_PM_GATE,
    VALID_RESEARCH_PM_GATE,
    VALID_RESUME_RESULT_TO_PM,
    VALID_CRITICAL_GATE_WITHOUT_WORKER_PACKAGE,
)

NEGATIVE_SCENARIOS = (
    RAW_WORKER_RESULT_RELAYED_TO_REVIEWER,
    FORMAL_EVIDENCE_FROM_UNDISPOSITIONED_RESULT,
    REVIEWER_STARTED_WITHOUT_PM_GATE_PACKAGE,
    NODE_COMPLETION_WITHOUT_REVIEWER_GATE,
    CRITICAL_REVIEWER_GATE_REMOVED,
    RESUME_RESULT_DIRECT_TO_REVIEWER,
    MATERIAL_RESEARCH_DECISION_WITHOUT_GATE,
    CONTROLLER_READS_SEALED_BODY,
    LEGACY_REVIEWER_RELAY_USED_AS_CURRENT_ACCEPTANCE,
    PM_FORWARDED_RAW_PACKAGE_TO_REVIEWER,
)

SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS

PACKAGE_NONE = "none"
PACKAGE_CURRENT_NODE = "current_node_work"
PACKAGE_MATERIAL_SCAN = "material_scan"
PACKAGE_RESEARCH = "research"
PACKAGE_RESUME_EXISTING = "resume_existing_result"

GATE_NONE = "none"
GATE_MATERIAL_SUFFICIENCY = "material_sufficiency"
GATE_RESEARCH_SOURCE = "research_source"
GATE_PRODUCT_ARCHITECTURE = "product_architecture"
GATE_ROUTE_CHALLENGE = "route_challenge"
GATE_NODE_ACCEPTANCE_PLAN = "node_acceptance_plan"
GATE_NODE_COMPLETION = "node_completion"
GATE_PARENT_BACKWARD = "parent_backward_replay"
GATE_EVIDENCE_QUALITY = "evidence_quality"
GATE_FINAL_BACKWARD = "final_backward_replay"

CRITICAL_REVIEWER_GATES = frozenset(
    {
        GATE_MATERIAL_SUFFICIENCY,
        GATE_RESEARCH_SOURCE,
        GATE_PRODUCT_ARCHITECTURE,
        GATE_ROUTE_CHALLENGE,
        GATE_NODE_ACCEPTANCE_PLAN,
        GATE_NODE_COMPLETION,
        GATE_PARENT_BACKWARD,
        GATE_EVIDENCE_QUALITY,
        GATE_FINAL_BACKWARD,
    }
)

DISPOSITION_NONE = "none"
DISPOSITION_ABSORBED = "absorbed"
DISPOSITION_REWORK_REQUESTED = "rework_requested"
DISPOSITION_CANCELED = "canceled"
DISPOSITION_BLOCKED = "blocked"
DISPOSITION_MUTATE = "route_or_node_mutation_required"


@dataclass(frozen=True)
class Tick:
    """One abstract PM package-absorption protocol tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"

    package_kind: str = PACKAGE_NONE
    gate_kind: str = GATE_NONE
    resume_path: bool = False
    critical_gate_required: bool = False

    pm_authored_package: bool = False
    worker_result_returned: bool = False
    result_mechanically_validated: bool = False
    result_relayed_to_pm: bool = False
    pm_disposition: str = DISPOSITION_NONE
    pm_disposition_recorded: bool = False

    pm_gate_package_written: bool = False
    reviewer_received_raw_worker_result: bool = False
    pm_forwarded_raw_package_to_reviewer: bool = False
    reviewer_gate_started: bool = False
    reviewer_gate_passed: bool = False

    formal_evidence_uses_worker_result: bool = False
    material_or_research_affects_decision: bool = False
    route_or_node_decision_recorded: bool = False
    node_completion_recorded: bool = False

    legacy_direct_reviewer_relay_flag: bool = False
    legacy_flag_used_as_current_acceptance: bool = False
    controller_read_sealed_body: bool = False
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class PMPackageAbsorptionStep:
    """Model one FlowPilot PM package-result transition.

    Input x State -> Set(Output x State)
    reads: package kind, worker result envelope, PM disposition, reviewer gate
    package, resume marker, legacy relay marker, and Controller boundary
    writes: PM result relay, PM disposition, formal gate package, reviewer gate
    decision, route/node/material/research use, or terminal rejection
    idempotency: a worker result has one PM disposition; repeated ticks do not
    create a second current acceptance from the same raw or legacy result.
    """

    name = "PMPackageAbsorptionStep"
    input_description = "FlowPilot PM package absorption tick"
    output_description = "one PM-first package routing transition"
    reads = (
        "worker_result_envelope",
        "pm_disposition",
        "reviewer_gate_package",
        "resume_state",
        "legacy_direct_reviewer_relay_flag",
    )
    writes = (
        "pm_result_relay",
        "pm_disposition_record",
        "formal_gate_package",
        "reviewer_gate_result",
        "route_or_node_decision",
    )
    idempotency = "single worker result disposition is monotonic"

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


def _scenario_base(scenario: str) -> State:
    if scenario == VALID_CURRENT_NODE_PM_GATE:
        return State(
            status="running",
            scenario=scenario,
            package_kind=PACKAGE_CURRENT_NODE,
            gate_kind=GATE_NODE_COMPLETION,
            critical_gate_required=True,
            pm_authored_package=True,
            worker_result_returned=True,
            result_mechanically_validated=True,
            result_relayed_to_pm=True,
            pm_disposition=DISPOSITION_ABSORBED,
            pm_disposition_recorded=True,
            pm_gate_package_written=True,
            reviewer_gate_started=True,
            reviewer_gate_passed=True,
            formal_evidence_uses_worker_result=True,
            route_or_node_decision_recorded=True,
            node_completion_recorded=True,
        )
    if scenario == VALID_MATERIAL_PM_GATE:
        return State(
            status="running",
            scenario=scenario,
            package_kind=PACKAGE_MATERIAL_SCAN,
            gate_kind=GATE_MATERIAL_SUFFICIENCY,
            critical_gate_required=True,
            pm_authored_package=True,
            worker_result_returned=True,
            result_mechanically_validated=True,
            result_relayed_to_pm=True,
            pm_disposition=DISPOSITION_ABSORBED,
            pm_disposition_recorded=True,
            pm_gate_package_written=True,
            reviewer_gate_started=True,
            reviewer_gate_passed=True,
            formal_evidence_uses_worker_result=True,
            material_or_research_affects_decision=True,
            route_or_node_decision_recorded=True,
        )
    if scenario == VALID_RESEARCH_PM_GATE:
        return replace(_scenario_base(VALID_MATERIAL_PM_GATE), scenario=scenario, package_kind=PACKAGE_RESEARCH, gate_kind=GATE_RESEARCH_SOURCE)
    if scenario == VALID_RESUME_RESULT_TO_PM:
        return State(
            status="running",
            scenario=scenario,
            package_kind=PACKAGE_RESUME_EXISTING,
            gate_kind=GATE_NODE_COMPLETION,
            resume_path=True,
            critical_gate_required=True,
            pm_authored_package=True,
            worker_result_returned=True,
            result_mechanically_validated=True,
            result_relayed_to_pm=True,
            pm_disposition=DISPOSITION_ABSORBED,
            pm_disposition_recorded=True,
            pm_gate_package_written=True,
            reviewer_gate_started=True,
            reviewer_gate_passed=True,
            formal_evidence_uses_worker_result=True,
            route_or_node_decision_recorded=True,
            node_completion_recorded=True,
        )
    if scenario == VALID_CRITICAL_GATE_WITHOUT_WORKER_PACKAGE:
        return State(
            status="running",
            scenario=scenario,
            package_kind=PACKAGE_NONE,
            gate_kind=GATE_ROUTE_CHALLENGE,
            critical_gate_required=True,
            pm_gate_package_written=True,
            reviewer_gate_started=True,
            reviewer_gate_passed=True,
            route_or_node_decision_recorded=True,
        )
    raise KeyError(scenario)


def _scenario_state(scenario: str) -> State:
    if scenario in VALID_SCENARIOS:
        return _scenario_base(scenario)
    if scenario == RAW_WORKER_RESULT_RELAYED_TO_REVIEWER:
        return replace(
            _scenario_base(VALID_CURRENT_NODE_PM_GATE),
            scenario=scenario,
            result_relayed_to_pm=False,
            pm_disposition=DISPOSITION_NONE,
            pm_disposition_recorded=False,
            pm_gate_package_written=False,
            reviewer_received_raw_worker_result=True,
        )
    if scenario == FORMAL_EVIDENCE_FROM_UNDISPOSITIONED_RESULT:
        return replace(
            _scenario_base(VALID_CURRENT_NODE_PM_GATE),
            scenario=scenario,
            pm_disposition=DISPOSITION_NONE,
            pm_disposition_recorded=False,
            formal_evidence_uses_worker_result=True,
        )
    if scenario == REVIEWER_STARTED_WITHOUT_PM_GATE_PACKAGE:
        return replace(
            _scenario_base(VALID_CURRENT_NODE_PM_GATE),
            scenario=scenario,
            pm_gate_package_written=False,
            reviewer_gate_started=True,
            reviewer_gate_passed=True,
        )
    if scenario == NODE_COMPLETION_WITHOUT_REVIEWER_GATE:
        return replace(
            _scenario_base(VALID_CURRENT_NODE_PM_GATE),
            scenario=scenario,
            reviewer_gate_started=False,
            reviewer_gate_passed=False,
            node_completion_recorded=True,
        )
    if scenario == CRITICAL_REVIEWER_GATE_REMOVED:
        return State(
            status="running",
            scenario=scenario,
            package_kind=PACKAGE_NONE,
            gate_kind=GATE_ROUTE_CHALLENGE,
            critical_gate_required=True,
            pm_gate_package_written=True,
            reviewer_gate_started=False,
            reviewer_gate_passed=False,
            route_or_node_decision_recorded=True,
        )
    if scenario == RESUME_RESULT_DIRECT_TO_REVIEWER:
        return replace(
            _scenario_base(VALID_RESUME_RESULT_TO_PM),
            scenario=scenario,
            result_relayed_to_pm=False,
            pm_disposition=DISPOSITION_NONE,
            pm_disposition_recorded=False,
            pm_gate_package_written=False,
            reviewer_received_raw_worker_result=True,
        )
    if scenario == MATERIAL_RESEARCH_DECISION_WITHOUT_GATE:
        return replace(
            _scenario_base(VALID_RESEARCH_PM_GATE),
            scenario=scenario,
            pm_gate_package_written=False,
            reviewer_gate_started=False,
            reviewer_gate_passed=False,
            material_or_research_affects_decision=True,
            route_or_node_decision_recorded=True,
        )
    if scenario == CONTROLLER_READS_SEALED_BODY:
        return replace(_scenario_base(VALID_CURRENT_NODE_PM_GATE), scenario=scenario, controller_read_sealed_body=True)
    if scenario == LEGACY_REVIEWER_RELAY_USED_AS_CURRENT_ACCEPTANCE:
        return replace(
            _scenario_base(VALID_CURRENT_NODE_PM_GATE),
            scenario=scenario,
            legacy_direct_reviewer_relay_flag=True,
            legacy_flag_used_as_current_acceptance=True,
            result_relayed_to_pm=False,
            pm_disposition=DISPOSITION_NONE,
            pm_disposition_recorded=False,
        )
    if scenario == PM_FORWARDED_RAW_PACKAGE_TO_REVIEWER:
        return replace(
            _scenario_base(VALID_CURRENT_NODE_PM_GATE),
            scenario=scenario,
            pm_forwarded_raw_package_to_reviewer=True,
            reviewer_received_raw_worker_result=True,
            pm_gate_package_written=False,
        )
    raise KeyError(scenario)


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.scenario == "unset":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _scenario_state(scenario))
        return

    failures = package_absorption_failures(state)
    if not failures and state.scenario in VALID_SCENARIOS:
        yield Transition(
            f"accept_{state.scenario}",
            replace(state, status="accepted", terminal_reason="safe_pm_first_package_flow"),
        )
    else:
        yield Transition(
            f"reject_{state.scenario}",
            replace(
                state,
                status="rejected",
                terminal_reason=failures[0] if failures else "negative scenario rejected",
            ),
        )


def next_states(state: State) -> Iterable[State]:
    for transition in next_safe_states(state):
        yield transition.state


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted"


def package_absorption_failures(state: State) -> list[str]:
    failures: list[str] = []
    pm_issued_package = state.package_kind in {
        PACKAGE_CURRENT_NODE,
        PACKAGE_MATERIAL_SCAN,
        PACKAGE_RESEARCH,
        PACKAGE_RESUME_EXISTING,
    }
    if state.controller_read_sealed_body:
        failures.append("Controller read sealed packet/result body")
    if pm_issued_package and state.worker_result_returned and state.reviewer_received_raw_worker_result:
        failures.append("raw PM-issued worker result reached reviewer before PM gate package")
    if state.pm_forwarded_raw_package_to_reviewer:
        failures.append("PM disposition forwarded a raw worker package to reviewer")
    if pm_issued_package and state.worker_result_returned and not state.result_relayed_to_pm:
        failures.append("PM-issued worker result did not return to project_manager")
    if (
        state.formal_evidence_uses_worker_result
        and (not state.pm_disposition_recorded or state.pm_disposition != DISPOSITION_ABSORBED)
    ):
        failures.append("formal evidence used a worker result without PM absorbed disposition")
    if state.reviewer_gate_started and not state.pm_gate_package_written:
        failures.append("reviewer gate started without a PM-built formal gate package")
    if state.reviewer_gate_passed and not state.reviewer_gate_started:
        failures.append("reviewer gate passed without reviewer gate start")
    if (
        state.critical_gate_required
        and state.gate_kind in CRITICAL_REVIEWER_GATES
        and state.route_or_node_decision_recorded
        and not state.reviewer_gate_passed
    ):
        failures.append("critical PM route/node/material/research decision bypassed reviewer gate")
    if state.node_completion_recorded and not (
        state.gate_kind == GATE_NODE_COMPLETION
        and state.pm_gate_package_written
        and state.reviewer_gate_passed
        and state.pm_disposition_recorded
    ):
        failures.append("PM completed a node without PM disposition and reviewer node-completion gate")
    if (
        state.material_or_research_affects_decision
        and state.package_kind in {PACKAGE_MATERIAL_SCAN, PACKAGE_RESEARCH}
        and not (state.pm_disposition_recorded and state.pm_gate_package_written and state.reviewer_gate_passed)
    ):
        failures.append("material/research result affected a protected decision without PM absorption and reviewer gate")
    if (
        state.resume_path
        and state.worker_result_returned
        and (state.reviewer_received_raw_worker_result or not state.result_relayed_to_pm)
    ):
        failures.append("resume worker result bypassed PM disposition")
    if state.legacy_direct_reviewer_relay_flag and state.legacy_flag_used_as_current_acceptance:
        failures.append("legacy direct-reviewer relay flag was used as current acceptance")
    return failures


def accepts_only_safe_pm_first_flows(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted":
        failures = package_absorption_failures(state)
        if failures:
            return InvariantResult.fail(failures[0])
    return InvariantResult.pass_()


def raw_worker_results_never_become_reviewer_work(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.reviewer_received_raw_worker_result:
        return InvariantResult.fail("accepted state sent a raw worker result to reviewer")
    return InvariantResult.pass_()


def pm_disposition_precedes_formal_evidence_use(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.formal_evidence_uses_worker_result:
        if not (state.pm_disposition_recorded and state.pm_disposition == DISPOSITION_ABSORBED):
            return InvariantResult.fail("accepted state used worker evidence before PM disposition")
    return InvariantResult.pass_()


def critical_reviewer_gates_stay_mandatory(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.status == "accepted"
        and state.critical_gate_required
        and state.gate_kind in CRITICAL_REVIEWER_GATES
        and state.route_or_node_decision_recorded
        and not state.reviewer_gate_passed
    ):
        return InvariantResult.fail("accepted critical decision bypassed reviewer gate")
    return InvariantResult.pass_()


def resume_uses_same_pm_first_path(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.resume_path and not state.result_relayed_to_pm:
        return InvariantResult.fail("accepted resume path bypassed PM result relay")
    return InvariantResult.pass_()


def legacy_reviewer_relay_is_audit_only(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.legacy_flag_used_as_current_acceptance:
        return InvariantResult.fail("accepted legacy reviewer relay as current proof")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepts_only_safe_pm_first_flows",
        description="Accepted paths must satisfy PM-first package absorption and reviewer formal gate rules.",
        predicate=accepts_only_safe_pm_first_flows,
    ),
    Invariant(
        name="raw_worker_results_never_become_reviewer_work",
        description="Reviewer does not receive raw PM-issued worker package results.",
        predicate=raw_worker_results_never_become_reviewer_work,
    ),
    Invariant(
        name="pm_disposition_precedes_formal_evidence_use",
        description="Formal evidence cannot use worker results before PM absorbed disposition.",
        predicate=pm_disposition_precedes_formal_evidence_use,
    ),
    Invariant(
        name="critical_reviewer_gates_stay_mandatory",
        description="Protected route, node, material, research, and closure gates still require reviewer pass.",
        predicate=critical_reviewer_gates_stay_mandatory,
    ),
    Invariant(
        name="resume_uses_same_pm_first_path",
        description="Resume paths route worker results to PM before reviewer gates.",
        predicate=resume_uses_same_pm_first_path,
    ),
    Invariant(
        name="legacy_reviewer_relay_is_audit_only",
        description="Legacy direct-reviewer relay flags cannot satisfy current PM disposition or gate proof.",
        predicate=legacy_reviewer_relay_is_audit_only,
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
    return Workflow((PMPackageAbsorptionStep(),), name="flowpilot_pm_package_absorption")


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
    "package_absorption_failures",
    "terminal_predicate",
]
