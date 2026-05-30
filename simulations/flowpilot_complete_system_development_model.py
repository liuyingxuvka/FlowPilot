"""FlowGuard development-process model for the complete black-box FlowPilot system."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_complete_system_development_process"
MAX_SEQUENCE_LENGTH = 23


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | complete | blocked
    openspec_contract_validated: bool = False
    existing_model_preflight_done: bool = False
    development_model_passed: bool = False
    structure_model_passed: bool = False
    ui_model_passed: bool = False
    testmesh_model_passed: bool = False
    alignment_model_passed: bool = False
    run_shell_done: bool = False
    router_state_machine_done: bool = False
    dynamic_host_done: bool = False
    flowguard_work_orders_done: bool = False
    review_repair_closure_done: bool = False
    cockpit_projection_done: bool = False
    migration_cutover_done: bool = False
    tests_written: bool = False
    routine_checks_passed: bool = False
    historical_replay_passed: bool = False
    background_regressions_inspected: bool = False
    live_host_evidence_recorded: bool = False
    install_synced_and_checked: bool = False
    git_committed: bool = False
    full_completion_claimed: bool = False
    historical_role_topology_authoritative: bool = False
    old_state_authoritative: bool = False
    cockpit_direct_state_write: bool = False
    sealed_body_leaked: bool = False
    progress_only_background_accepted: bool = False
    fake_only_claimed_as_live: bool = False


@dataclass(frozen=True)
class Tick:
    """One complete-system development step."""


@dataclass(frozen=True)
class Action:
    label: str


class Transition(NamedTuple):
    label: str
    state: State


REQUIRED_SAFE_LABELS = (
    "start_complete_system_development",
    "validate_openspec_contract",
    "run_existing_model_preflight",
    "run_development_process_model",
    "run_code_structure_model",
    "run_ui_flow_model",
    "run_testmesh_model",
    "run_model_test_alignment",
    "implement_run_shell",
    "implement_router_state_machine",
    "implement_dynamic_host",
    "implement_flowguard_work_orders",
    "implement_review_repair_closure",
    "implement_cockpit_projection",
    "implement_migration_cutover",
    "write_full_system_tests",
    "run_routine_checks",
    "run_historical_replay",
    "inspect_background_regressions",
    "record_live_host_evidence_boundary",
    "sync_install_and_checks",
    "commit_local_git",
    "claim_complete_system_done",
)


def initial_state() -> State:
    return State()


class CompleteSystemDevelopmentStep:
    name = "CompleteSystemDevelopmentStep"
    reads = (
        "openspec_contract_validated",
        "development_model_passed",
        "structure_model_passed",
        "ui_model_passed",
        "testmesh_model_passed",
        "alignment_model_passed",
        "routine_checks_passed",
        "historical_replay_passed",
        "background_regressions_inspected",
        "install_synced_and_checked",
    )
    writes = (
        "model_evidence",
        "runtime_implementation",
        "host_implementation",
        "ui_projection",
        "test_evidence",
        "install_evidence",
        "git_evidence",
        "completion_claim",
    )
    input_description = "Input x State: one requested complete-system development transition"
    output_description = "Set(Output x State): the next legal implementation or evidence step"
    idempotency = "safe transitions only add current evidence in modeled order"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"blocked", "complete"}:
        return ()
    failures = invariant_failures(state)
    if failures:
        return (Transition("blocked_on_complete_system_invariant", replace(state, status="blocked")),)
    if state.status == "new":
        return (Transition("start_complete_system_development", replace(state, status="running")),)
    if not state.openspec_contract_validated:
        return (Transition("validate_openspec_contract", replace(state, openspec_contract_validated=True)),)
    if not state.existing_model_preflight_done:
        return (Transition("run_existing_model_preflight", replace(state, existing_model_preflight_done=True)),)
    if not state.development_model_passed:
        return (Transition("run_development_process_model", replace(state, development_model_passed=True)),)
    if not state.structure_model_passed:
        return (Transition("run_code_structure_model", replace(state, structure_model_passed=True)),)
    if not state.ui_model_passed:
        return (Transition("run_ui_flow_model", replace(state, ui_model_passed=True)),)
    if not state.testmesh_model_passed:
        return (Transition("run_testmesh_model", replace(state, testmesh_model_passed=True)),)
    if not state.alignment_model_passed:
        return (Transition("run_model_test_alignment", replace(state, alignment_model_passed=True)),)
    if not state.run_shell_done:
        return (Transition("implement_run_shell", replace(state, run_shell_done=True)),)
    if not state.router_state_machine_done:
        return (Transition("implement_router_state_machine", replace(state, router_state_machine_done=True)),)
    if not state.dynamic_host_done:
        return (Transition("implement_dynamic_host", replace(state, dynamic_host_done=True)),)
    if not state.flowguard_work_orders_done:
        return (Transition("implement_flowguard_work_orders", replace(state, flowguard_work_orders_done=True)),)
    if not state.review_repair_closure_done:
        return (Transition("implement_review_repair_closure", replace(state, review_repair_closure_done=True)),)
    if not state.cockpit_projection_done:
        return (Transition("implement_cockpit_projection", replace(state, cockpit_projection_done=True)),)
    if not state.migration_cutover_done:
        return (Transition("implement_migration_cutover", replace(state, migration_cutover_done=True)),)
    if not state.tests_written:
        return (Transition("write_full_system_tests", replace(state, tests_written=True)),)
    if not state.routine_checks_passed:
        return (Transition("run_routine_checks", replace(state, routine_checks_passed=True)),)
    if not state.historical_replay_passed:
        return (Transition("run_historical_replay", replace(state, historical_replay_passed=True)),)
    if not state.background_regressions_inspected:
        return (
            Transition(
                "inspect_background_regressions",
                replace(state, background_regressions_inspected=True),
            ),
        )
    if not state.live_host_evidence_recorded:
        return (
            Transition(
                "record_live_host_evidence_boundary",
                replace(state, live_host_evidence_recorded=True),
            ),
        )
    if not state.install_synced_and_checked:
        return (Transition("sync_install_and_checks", replace(state, install_synced_and_checked=True)),)
    if not state.git_committed:
        return (Transition("commit_local_git", replace(state, git_committed=True)),)
    if not state.full_completion_claimed:
        return (
            Transition(
                "claim_complete_system_done",
                replace(state, full_completion_claimed=True, status="complete"),
            ),
        )
    return ()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.existing_model_preflight_done and not state.openspec_contract_validated:
        failures.append("existing-model preflight ran before OpenSpec contract validation")
    if state.development_model_passed and not state.existing_model_preflight_done:
        failures.append("development model passed before existing model preflight")
    if state.structure_model_passed and not state.development_model_passed:
        failures.append("structure model passed before development process model")
    if state.ui_model_passed and not state.structure_model_passed:
        failures.append("UI model passed before code-structure ownership was derived")
    if state.testmesh_model_passed and not state.ui_model_passed:
        failures.append("TestMesh passed before UI-flow model")
    if state.alignment_model_passed and not state.testmesh_model_passed:
        failures.append("model-test alignment passed before TestMesh model")
    if state.run_shell_done and not state.alignment_model_passed:
        failures.append("run shell implemented before required FlowGuard models")
    if state.router_state_machine_done and not state.run_shell_done:
        failures.append("router state machine implemented before run shell")
    if state.dynamic_host_done and not state.router_state_machine_done:
        failures.append("dynamic host implemented before router state machine")
    if state.flowguard_work_orders_done and not state.dynamic_host_done:
        failures.append("FlowGuard work orders implemented before dynamic host boundary")
    if state.review_repair_closure_done and not state.flowguard_work_orders_done:
        failures.append("review/repair/closure implemented before FlowGuard orders")
    if state.cockpit_projection_done and not state.review_repair_closure_done:
        failures.append("Cockpit projection implemented before review/closure boundary")
    if state.migration_cutover_done and not state.cockpit_projection_done:
        failures.append("migration/cutover implemented before Cockpit/status projection")
    if state.tests_written and not state.migration_cutover_done:
        failures.append("full-system tests written before all implementation surfaces existed")
    if state.routine_checks_passed and not state.tests_written:
        failures.append("routine checks passed before full-system tests existed")
    if state.historical_replay_passed and not state.routine_checks_passed:
        failures.append("historical replay passed before routine checks")
    if state.background_regressions_inspected and not state.historical_replay_passed:
        failures.append("background regressions inspected before historical replay")
    if state.live_host_evidence_recorded and not state.background_regressions_inspected:
        failures.append("live-host evidence recorded before background regression evidence")
    if state.install_synced_and_checked and not state.live_host_evidence_recorded:
        failures.append("install sync ran before live-host evidence boundary was recorded")
    if state.git_committed and not state.install_synced_and_checked:
        failures.append("git commit happened before install sync/check")
    if state.full_completion_claimed and not state.git_committed:
        failures.append("full completion claimed before local git closure")
    if state.historical_role_topology_authoritative:
        failures.append("historical role topology was reintroduced as runtime authority")
    if state.old_state_authoritative:
        failures.append("old FlowPilot state was used as current authority")
    if state.cockpit_direct_state_write:
        failures.append("Cockpit direct state write bypassed router")
    if state.sealed_body_leaked:
        failures.append("sealed packet or result body leaked into public projection")
    if state.progress_only_background_accepted:
        failures.append("progress-only background evidence was accepted as completion")
    if state.fake_only_claimed_as_live:
        failures.append("fake-agent evidence was claimed as live-host confidence")
    return failures


def _safe_complete_state() -> State:
    return State(
        status="complete",
        openspec_contract_validated=True,
        existing_model_preflight_done=True,
        development_model_passed=True,
        structure_model_passed=True,
        ui_model_passed=True,
        testmesh_model_passed=True,
        alignment_model_passed=True,
        run_shell_done=True,
        router_state_machine_done=True,
        dynamic_host_done=True,
        flowguard_work_orders_done=True,
        review_repair_closure_done=True,
        cockpit_projection_done=True,
        migration_cutover_done=True,
        tests_written=True,
        routine_checks_passed=True,
        historical_replay_passed=True,
        background_regressions_inspected=True,
        live_host_evidence_recorded=True,
        install_synced_and_checked=True,
        git_committed=True,
        full_completion_claimed=True,
    )


def hazard_states() -> dict[str, State]:
    safe = _safe_complete_state()
    return {
        "code_before_models": replace(safe, alignment_model_passed=False),
        "host_before_router": replace(safe, router_state_machine_done=False),
        "flowguard_orders_before_host": replace(safe, dynamic_host_done=False),
        "cockpit_before_closure_boundary": replace(safe, review_repair_closure_done=False),
        "tests_before_implementation": replace(safe, migration_cutover_done=False),
        "history_before_routine": replace(safe, routine_checks_passed=False),
        "background_before_history": replace(safe, historical_replay_passed=False),
        "install_before_live_boundary": replace(safe, live_host_evidence_recorded=False),
        "completion_before_git": replace(safe, git_committed=False),
        "historical_role_topology_authoritative": replace(safe, historical_role_topology_authoritative=True),
        "old_state_authoritative": replace(safe, old_state_authoritative=True),
        "cockpit_direct_write": replace(safe, cockpit_direct_state_write=True),
        "sealed_body_leak": replace(safe, sealed_body_leaked=True),
        "progress_only_background": replace(safe, progress_only_background_accepted=True),
        "fake_only_live_claim": replace(safe, fake_only_claimed_as_live=True),
    }


def target_state() -> State:
    state = initial_state()
    for label in REQUIRED_SAFE_LABELS:
        transitions = {transition.label: transition for transition in next_safe_states(state)}
        state = transitions[label].state
    return state


def development_invariant(state: State, trace: Any) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="complete_flowpilot_development_order",
        description=(
            "Complete FlowPilot system development must validate OpenSpec, "
            "ground existing models, run FlowGuard process/structure/UI/test "
            "models, implement state/router/host/FlowGuard/review/UI/migration "
            "layers in order, prove routine/history/background/live evidence, "
            "sync install state, and close local git before full completion."
        ),
        predicate=development_invariant,
    ),
)
EXTERNAL_INPUTS = (Tick(),)


def terminal_predicate(_input_obj: Tick, state: State, _trace: Any) -> bool:
    return state.status in {"complete", "blocked"}


def is_success(state: State) -> bool:
    return state.status == "complete" and not invariant_failures(state)


def build_workflow() -> Workflow:
    return Workflow((CompleteSystemDevelopmentStep(),), name=MODEL_ID)


def state_summary(state: State) -> dict[str, Any]:
    return {
        "status": state.status,
        "openspec_contract_validated": state.openspec_contract_validated,
        "existing_model_preflight_done": state.existing_model_preflight_done,
        "development_model_passed": state.development_model_passed,
        "structure_model_passed": state.structure_model_passed,
        "ui_model_passed": state.ui_model_passed,
        "testmesh_model_passed": state.testmesh_model_passed,
        "alignment_model_passed": state.alignment_model_passed,
        "run_shell_done": state.run_shell_done,
        "router_state_machine_done": state.router_state_machine_done,
        "dynamic_host_done": state.dynamic_host_done,
        "flowguard_work_orders_done": state.flowguard_work_orders_done,
        "review_repair_closure_done": state.review_repair_closure_done,
        "cockpit_projection_done": state.cockpit_projection_done,
        "migration_cutover_done": state.migration_cutover_done,
        "tests_written": state.tests_written,
        "routine_checks_passed": state.routine_checks_passed,
        "historical_replay_passed": state.historical_replay_passed,
        "background_regressions_inspected": state.background_regressions_inspected,
        "live_host_evidence_recorded": state.live_host_evidence_recorded,
        "install_synced_and_checked": state.install_synced_and_checked,
        "git_committed": state.git_committed,
        "full_completion_claimed": state.full_completion_claimed,
    }
