"""FlowGuard development-process model for the FlowPilot core runtime."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_core_runtime_development_process"
MAX_SEQUENCE_LENGTH = 14


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | complete | blocked
    openspec_validated: bool = False
    flowguard_dev_model_passed: bool = False
    runtime_assets_written: bool = False
    ledger_runtime_done: bool = False
    lease_packet_runtime_done: bool = False
    router_runtime_done: bool = False
    flowguard_review_closure_console_done: bool = False
    tests_written: bool = False
    routine_checks_passed: bool = False
    background_regressions_inspected: bool = False
    install_synced_and_checked: bool = False
    git_committed: bool = False
    fixed_role_topology_required: bool = False
    prior_runtime_state_authoritative: bool = False
    console_exposes_sealed_body: bool = False
    release_claimed: bool = False


@dataclass(frozen=True)
class Tick:
    """One development-process transition."""


@dataclass(frozen=True)
class Action:
    label: str


class Transition(NamedTuple):
    label: str
    state: State


REQUIRED_SAFE_LABELS = (
    "start_runtime_development",
    "validate_openspec_contract",
    "run_flowguard_development_model",
    "write_runtime_assets",
    "implement_ledger_runtime",
    "implement_lease_packet_runtime",
    "implement_router_runtime",
    "implement_flowguard_review_closure_console",
    "write_focused_tests",
    "run_routine_checks",
    "inspect_background_regressions",
    "sync_install_and_checks",
    "commit_local_git",
    "complete_runtime_development",
)


def initial_state() -> State:
    return State()


class DevelopmentStep:
    name = "FlowPilotCoreRuntimeDevelopmentStep"
    reads = (
        "openspec_validated",
        "flowguard_dev_model_passed",
        "runtime_assets_written",
        "routine_checks_passed",
        "background_regressions_inspected",
        "install_synced_and_checked",
    )
    writes = (
        "development_order",
        "runtime_assets",
        "test_evidence",
        "background_evidence",
        "install_evidence",
        "git_evidence",
    )
    input_description = "one clean-runtime development-process tick"
    output_description = "one ordered implementation or evidence step"
    idempotency = "safe transitions only add current evidence in order"

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
        return (Transition("development_blocked_on_invariant_failure", replace(state, status="blocked")),)
    if state.status == "new":
        return (Transition("start_runtime_development", replace(state, status="running")),)
    if not state.openspec_validated:
        return (Transition("validate_openspec_contract", replace(state, openspec_validated=True)),)
    if not state.flowguard_dev_model_passed:
        return (
            Transition(
                "run_flowguard_development_model",
                replace(state, flowguard_dev_model_passed=True),
            ),
        )
    if not state.runtime_assets_written:
        return (Transition("write_runtime_assets", replace(state, runtime_assets_written=True)),)
    if not state.ledger_runtime_done:
        return (Transition("implement_ledger_runtime", replace(state, ledger_runtime_done=True)),)
    if not state.lease_packet_runtime_done:
        return (
            Transition(
                "implement_lease_packet_runtime",
                replace(state, lease_packet_runtime_done=True),
            ),
        )
    if not state.router_runtime_done:
        return (Transition("implement_router_runtime", replace(state, router_runtime_done=True)),)
    if not state.flowguard_review_closure_console_done:
        return (
            Transition(
                "implement_flowguard_review_closure_console",
                replace(state, flowguard_review_closure_console_done=True),
            ),
        )
    if not state.tests_written:
        return (Transition("write_focused_tests", replace(state, tests_written=True)),)
    if not state.routine_checks_passed:
        return (Transition("run_routine_checks", replace(state, routine_checks_passed=True)),)
    if not state.background_regressions_inspected:
        return (
            Transition(
                "inspect_background_regressions",
                replace(state, background_regressions_inspected=True),
            ),
        )
    if not state.install_synced_and_checked:
        return (
            Transition(
                "sync_install_and_checks",
                replace(state, install_synced_and_checked=True),
            ),
        )
    if not state.git_committed:
        return (Transition("commit_local_git", replace(state, git_committed=True)),)
    if not state.release_claimed:
        return (Transition("complete_runtime_development", replace(state, release_claimed=True, status="complete")),)
    return ()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.flowguard_dev_model_passed and not state.openspec_validated:
        failures.append("FlowGuard development model ran before OpenSpec contract validation")
    if state.runtime_assets_written and not state.flowguard_dev_model_passed:
        failures.append("runtime assets were written before development-process modeling")
    if state.ledger_runtime_done and not state.runtime_assets_written:
        failures.append("ledger runtime was implemented before runtime asset boundary")
    if state.lease_packet_runtime_done and not state.ledger_runtime_done:
        failures.append("lease/packet runtime was implemented before ledger authority")
    if state.router_runtime_done and not state.lease_packet_runtime_done:
        failures.append("router runtime was implemented before lease/packet mechanics")
    if state.flowguard_review_closure_console_done and not state.router_runtime_done:
        failures.append("review/closure/console were implemented before router mechanics")
    if state.routine_checks_passed and not state.tests_written:
        failures.append("routine checks passed before focused tests existed")
    if state.background_regressions_inspected and not state.routine_checks_passed:
        failures.append("background regressions were inspected before routine checks")
    if state.install_synced_and_checked and not state.background_regressions_inspected:
        failures.append("install sync/check ran before background evidence was inspected")
    if state.git_committed and not state.install_synced_and_checked:
        failures.append("git commit happened before install sync/check")
    if state.release_claimed and not state.git_committed:
        failures.append("release completion was claimed before local git closure")
    if state.fixed_role_topology_required:
        failures.append("fixed role topology was required as current authority")
    if state.prior_runtime_state_authoritative:
        failures.append("prior runtime state was used as current authority")
    if state.console_exposes_sealed_body:
        failures.append("console exposed sealed packet or result body")
    return failures


def hazard_states() -> dict[str, State]:
    safe = State(
        status="complete",
        openspec_validated=True,
        flowguard_dev_model_passed=True,
        runtime_assets_written=True,
        ledger_runtime_done=True,
        lease_packet_runtime_done=True,
        router_runtime_done=True,
        flowguard_review_closure_console_done=True,
        tests_written=True,
        routine_checks_passed=True,
        background_regressions_inspected=True,
        install_synced_and_checked=True,
        git_committed=True,
        release_claimed=True,
    )
    return {
        "code_before_openspec": replace(safe, openspec_validated=False),
        "runtime_before_flowguard_model": replace(safe, flowguard_dev_model_passed=False),
        "router_before_packets": replace(safe, lease_packet_runtime_done=False),
        "checks_before_tests": replace(safe, tests_written=False),
        "install_before_background": replace(safe, background_regressions_inspected=False),
        "git_before_install": replace(safe, install_synced_and_checked=False),
        "release_before_git": replace(safe, git_committed=False),
        "fixed_role_topology_reintroduced": replace(safe, fixed_role_topology_required=True),
        "prior_runtime_state_authoritative": replace(safe, prior_runtime_state_authoritative=True),
        "console_leaks_sealed_body": replace(safe, console_exposes_sealed_body=True),
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
        name="flowpilot_core_runtime_development_order",
        description=(
            "The clean runtime build must validate OpenSpec, run FlowGuard "
            "development-process modeling, implement ledger authority before "
            "leases/packets/router/review, pass routine checks, inspect "
            "background evidence, sync install state, and close local git "
            "before release completion."
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
    return Workflow((DevelopmentStep(),), name=MODEL_ID)


def state_summary(state: State) -> dict[str, Any]:
    return {
        "status": state.status,
        "openspec_validated": state.openspec_validated,
        "flowguard_dev_model_passed": state.flowguard_dev_model_passed,
        "runtime_assets_written": state.runtime_assets_written,
        "ledger_runtime_done": state.ledger_runtime_done,
        "lease_packet_runtime_done": state.lease_packet_runtime_done,
        "router_runtime_done": state.router_runtime_done,
        "flowguard_review_closure_console_done": state.flowguard_review_closure_console_done,
        "tests_written": state.tests_written,
        "routine_checks_passed": state.routine_checks_passed,
        "background_regressions_inspected": state.background_regressions_inspected,
        "install_synced_and_checked": state.install_synced_and_checked,
        "git_committed": state.git_committed,
        "release_claimed": state.release_claimed,
    }
