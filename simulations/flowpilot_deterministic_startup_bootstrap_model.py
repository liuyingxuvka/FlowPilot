"""FlowGuard model for FlowPilot deterministic startup bootstrap.

Risk purpose:
- Uses FlowGuard (https://github.com/liuyingxuvka/FlowGuard) to review the
  refactor that moves deterministic startup file setup out of Controller rows
  and into a narrow bootstrap seed.
- Guards against the class of bugs where the Router scheduler starts from a
  partial foundation, deterministic setup remains duplicated as Controller
  work, seed failures become PM repair blockers before a route exists, or
  scheduled startup rows still emit false blockers after reconciliation.
- Update and run this model whenever FlowPilot startup seed creation,
  bootstrap evidence, startup scheduler row selection, or scheduled-row
  reconciliation changes.
- Companion check command:
  `python simulations/run_flowpilot_deterministic_startup_bootstrap_checks.py`.

Risk intent brief:
- Protected harm: FlowPilot starts from missing runtime files, repeats
  deterministic startup work as Controller tasks, leaks user request bodies
  into Controller context, hides seed failure as route success, or sends PM a
  false control blocker before real route work starts.
- Model-critical state: bootstrap seed proof, foundation artifacts, user
  request/intake visibility, Router scheduler activation, startup obligations,
  Controller action rows, receipt replay, blocker creation, install freshness,
  and git recording.
- Adversarial branches: scheduler activation before seed proof, seed success
  without all artifacts, deterministic setup rows left in the scheduler, seed
  failure converted to PM repair, already reconciled row turned into blocker,
  role/heartbeat/core work bypassing scheduler, Controller reading sealed user
  body, stale install after repo fix, and overwriting peer changes.
- Hard invariants: the seed must prove every deterministic artifact before the
  scheduler starts; deterministic setup must not be scheduled as Controller
  work; only non-deterministic startup obligations enter the scheduler; already
  reconciled rows are idempotent; seed failure is pre-route startup failure;
  user request bodies remain sealed/ref-scoped; final sync must update the
  installed skill and preserve peer-agent changes.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


DETERMINISTIC_SEED_CREATES_FOUNDATION_THEN_SCHEDULER_STARTS = (
    "deterministic_seed_creates_foundation_then_scheduler_starts"
)
SCHEDULER_CONTAINS_ONLY_STARTUP_OBLIGATIONS = "scheduler_contains_only_startup_obligations"
RECEIPT_REPLAY_IDEMPOTENTLY_SKIPS_RECONCILED_ROW = "receipt_replay_idempotently_skips_reconciled_row"
SEED_RECORDS_REQUEST_REF_AND_INTAKE_SCAFFOLD = "seed_records_request_ref_and_intake_scaffold"
OBLIGATIONS_SCHEDULE_AFTER_SEED = "obligations_schedule_after_seed"
REPO_INSTALL_CHECK_GIT_READY = "repo_install_check_git_ready"

SCHEDULER_BEFORE_SEED_SUCCESS = "scheduler_before_seed_success"
SEED_SUCCESS_WITHOUT_ALL_ARTIFACTS = "seed_success_without_all_artifacts"
DETERMINISTIC_SETUP_LEFT_AS_CONTROLLER_ROW = "deterministic_setup_left_as_controller_row"
SEED_FAILURE_AS_PM_BLOCKER = "seed_failure_as_pm_blocker"
RECONCILED_ROW_FALSE_PM_BLOCKER = "reconciled_row_false_pm_blocker"
UNSUPPORTED_STARTUP_RECEIPT_ESCALATED_TO_PM = "unsupported_startup_receipt_escalated_to_pm"
ROLE_SLOTS_BYPASS_SCHEDULER = "role_slots_bypass_scheduler"
HEARTBEAT_BYPASS_SCHEDULER = "heartbeat_bypass_scheduler"
CONTROLLER_CORE_BEFORE_SEED_AND_SCHEDULER = "controller_core_before_seed_and_scheduler"
CONTROLLER_READS_SEALED_USER_BODY = "controller_reads_sealed_user_body"
INTAKE_WRITTEN_WITHOUT_USER_REQUEST_REF = "intake_written_without_user_request_ref"
INSTALLED_SKILL_STALE_AFTER_FIX = "installed_skill_stale_after_fix"
PEER_CHANGES_OVERWRITTEN = "peer_changes_overwritten"

VALID_SCENARIOS = (
    DETERMINISTIC_SEED_CREATES_FOUNDATION_THEN_SCHEDULER_STARTS,
    SCHEDULER_CONTAINS_ONLY_STARTUP_OBLIGATIONS,
    RECEIPT_REPLAY_IDEMPOTENTLY_SKIPS_RECONCILED_ROW,
    SEED_RECORDS_REQUEST_REF_AND_INTAKE_SCAFFOLD,
    OBLIGATIONS_SCHEDULE_AFTER_SEED,
    REPO_INSTALL_CHECK_GIT_READY,
)

NEGATIVE_SCENARIOS = (
    SCHEDULER_BEFORE_SEED_SUCCESS,
    SEED_SUCCESS_WITHOUT_ALL_ARTIFACTS,
    DETERMINISTIC_SETUP_LEFT_AS_CONTROLLER_ROW,
    SEED_FAILURE_AS_PM_BLOCKER,
    RECONCILED_ROW_FALSE_PM_BLOCKER,
    UNSUPPORTED_STARTUP_RECEIPT_ESCALATED_TO_PM,
    ROLE_SLOTS_BYPASS_SCHEDULER,
    HEARTBEAT_BYPASS_SCHEDULER,
    CONTROLLER_CORE_BEFORE_SEED_AND_SCHEDULER,
    CONTROLLER_READS_SEALED_USER_BODY,
    INTAKE_WRITTEN_WITHOUT_USER_REQUEST_REF,
    INSTALLED_SKILL_STALE_AFTER_FIX,
    PEER_CHANGES_OVERWRITTEN,
)

SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    """One startup-bootstrap design review tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | accepted | rejected
    scenario: str = "unset"
    terminal_reason: str = "none"

    seed_started: bool = False
    run_shell_created: bool = False
    current_pointer_written: bool = False
    run_index_updated: bool = False
    runtime_dirs_created: bool = False
    empty_ledgers_created: bool = False
    placeholders_filled: bool = False
    mailbox_initialized: bool = False
    startup_answers_recorded: bool = False
    user_request_ref_recorded: bool = False
    user_intake_scaffold_written: bool = False
    bootstrap_evidence_written: bool = False
    seed_success: bool = False
    seed_failure: bool = False

    scheduler_started: bool = False
    deterministic_setup_controller_rows: bool = False
    role_slots_scheduled: bool = False
    heartbeat_requested: bool = False
    heartbeat_scheduled: bool = False
    controller_core_scheduled: bool = False
    role_slots_bypassed_scheduler: bool = False
    heartbeat_bypassed_scheduler: bool = False
    controller_core_loaded: bool = False

    row_reconciled: bool = False
    receipt_replayed: bool = False
    unsupported_startup_receipt_action: bool = False
    control_blocker_written: bool = False
    real_unsatisfied_postcondition: bool = False

    controller_reads_sealed_user_body: bool = False
    intake_body_visibility: str = "sealed_ref"  # sealed_ref | plain_controller

    repo_changed: bool = False
    installed_skill_synced: bool = False
    install_freshness_checked: bool = False
    git_recorded: bool = False
    peer_changes_detected: bool = False
    peer_changes_preserved: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _foundation_complete(state: State) -> bool:
    return (
        state.run_shell_created
        and state.current_pointer_written
        and state.run_index_updated
        and state.runtime_dirs_created
        and state.empty_ledgers_created
        and state.placeholders_filled
        and state.mailbox_initialized
        and state.startup_answers_recorded
        and state.user_request_ref_recorded
        and state.user_intake_scaffold_written
        and state.bootstrap_evidence_written
    )


def _accepted(scenario: str, **changes: object) -> State:
    defaults = {
        "status": "accepted",
        "scenario": scenario,
        "seed_started": True,
        "run_shell_created": True,
        "current_pointer_written": True,
        "run_index_updated": True,
        "runtime_dirs_created": True,
        "empty_ledgers_created": True,
        "placeholders_filled": True,
        "mailbox_initialized": True,
        "startup_answers_recorded": True,
        "user_request_ref_recorded": True,
        "user_intake_scaffold_written": True,
        "bootstrap_evidence_written": True,
        "seed_success": True,
        "scheduler_started": True,
        "role_slots_scheduled": True,
        "heartbeat_requested": True,
        "heartbeat_scheduled": True,
        "controller_core_scheduled": True,
        "intake_body_visibility": "sealed_ref",
    }
    defaults.update(changes)
    return replace(State(), **defaults)


def _rejected(scenario: str, **changes: object) -> State:
    return replace(State(), status="rejected", scenario=scenario, **changes)


def scenario_state(scenario: str) -> State:
    if scenario == DETERMINISTIC_SEED_CREATES_FOUNDATION_THEN_SCHEDULER_STARTS:
        return _accepted(scenario)
    if scenario == SCHEDULER_CONTAINS_ONLY_STARTUP_OBLIGATIONS:
        return _accepted(scenario, deterministic_setup_controller_rows=False)
    if scenario == RECEIPT_REPLAY_IDEMPOTENTLY_SKIPS_RECONCILED_ROW:
        return _accepted(scenario, row_reconciled=True, receipt_replayed=True, control_blocker_written=False)
    if scenario == SEED_RECORDS_REQUEST_REF_AND_INTAKE_SCAFFOLD:
        return _accepted(
            scenario,
            user_request_ref_recorded=True,
            user_intake_scaffold_written=True,
            controller_reads_sealed_user_body=False,
            intake_body_visibility="sealed_ref",
        )
    if scenario == OBLIGATIONS_SCHEDULE_AFTER_SEED:
        return _accepted(
            scenario,
            role_slots_scheduled=True,
            heartbeat_requested=True,
            heartbeat_scheduled=True,
            controller_core_scheduled=True,
            controller_core_loaded=False,
        )
    if scenario == REPO_INSTALL_CHECK_GIT_READY:
        return _accepted(
            scenario,
            repo_changed=True,
            installed_skill_synced=True,
            install_freshness_checked=True,
            git_recorded=True,
            peer_changes_detected=True,
            peer_changes_preserved=True,
        )

    if scenario == SCHEDULER_BEFORE_SEED_SUCCESS:
        return _rejected(scenario, seed_started=True, run_shell_created=True, scheduler_started=True, seed_success=False)
    if scenario == SEED_SUCCESS_WITHOUT_ALL_ARTIFACTS:
        return _rejected(
            scenario,
            seed_started=True,
            run_shell_created=True,
            current_pointer_written=True,
            empty_ledgers_created=True,
            mailbox_initialized=False,
            bootstrap_evidence_written=True,
            seed_success=True,
        )
    if scenario == DETERMINISTIC_SETUP_LEFT_AS_CONTROLLER_ROW:
        return _rejected(scenario, seed_started=True, seed_success=True, scheduler_started=True, deterministic_setup_controller_rows=True)
    if scenario == SEED_FAILURE_AS_PM_BLOCKER:
        return _rejected(scenario, seed_started=True, seed_failure=True, seed_success=False, control_blocker_written=True)
    if scenario == RECONCILED_ROW_FALSE_PM_BLOCKER:
        return _rejected(
            scenario,
            seed_started=True,
            seed_success=True,
            scheduler_started=True,
            row_reconciled=True,
            receipt_replayed=True,
            control_blocker_written=True,
        )
    if scenario == UNSUPPORTED_STARTUP_RECEIPT_ESCALATED_TO_PM:
        return _rejected(
            scenario,
            seed_started=True,
            seed_success=True,
            scheduler_started=True,
            row_reconciled=True,
            receipt_replayed=True,
            unsupported_startup_receipt_action=True,
            control_blocker_written=True,
        )
    if scenario == ROLE_SLOTS_BYPASS_SCHEDULER:
        return _rejected(scenario, seed_started=True, seed_success=True, scheduler_started=True, role_slots_bypassed_scheduler=True)
    if scenario == HEARTBEAT_BYPASS_SCHEDULER:
        return _rejected(
            scenario,
            seed_started=True,
            seed_success=True,
            scheduler_started=True,
            heartbeat_requested=True,
            heartbeat_bypassed_scheduler=True,
        )
    if scenario == CONTROLLER_CORE_BEFORE_SEED_AND_SCHEDULER:
        return _rejected(scenario, controller_core_loaded=True, seed_success=False, scheduler_started=False)
    if scenario == CONTROLLER_READS_SEALED_USER_BODY:
        return _rejected(
            scenario,
            seed_started=True,
            user_request_ref_recorded=True,
            user_intake_scaffold_written=True,
            controller_reads_sealed_user_body=True,
            intake_body_visibility="plain_controller",
        )
    if scenario == INTAKE_WRITTEN_WITHOUT_USER_REQUEST_REF:
        return _rejected(scenario, seed_started=True, user_request_ref_recorded=False, user_intake_scaffold_written=True)
    if scenario == INSTALLED_SKILL_STALE_AFTER_FIX:
        return _rejected(scenario, repo_changed=True, installed_skill_synced=False, install_freshness_checked=False, git_recorded=True)
    if scenario == PEER_CHANGES_OVERWRITTEN:
        return _rejected(scenario, repo_changed=True, peer_changes_detected=True, peer_changes_preserved=False)
    raise ValueError(f"unknown scenario: {scenario}")


def bootstrap_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.scheduler_started and not state.seed_success:
        failures.append("Router scheduler started before deterministic bootstrap seed succeeded")
    if state.seed_success and not _foundation_complete(state):
        failures.append("bootstrap seed reported success without all deterministic foundation artifacts")
    if state.deterministic_setup_controller_rows:
        failures.append("deterministic startup setup remained scheduled as Controller rows")
    if state.seed_failure and state.control_blocker_written:
        failures.append("bootstrap seed failure was converted into a PM repair blocker before route start")
    if state.row_reconciled and state.control_blocker_written:
        failures.append("already reconciled scheduled row produced a control blocker")
    if state.unsupported_startup_receipt_action and state.row_reconciled and state.control_blocker_written:
        failures.append("unsupported startup receipt was escalated to PM after row reconciliation")
    if state.role_slots_bypassed_scheduler:
        failures.append("startup role slots bypassed the unified Router scheduler")
    if state.heartbeat_requested and state.heartbeat_bypassed_scheduler:
        failures.append("startup heartbeat binding bypassed the unified Router scheduler")
    if state.controller_core_loaded and not (state.seed_success and state.scheduler_started and state.controller_core_scheduled):
        failures.append("Controller core loaded before deterministic seed and scheduler handoff")
    if state.controller_reads_sealed_user_body or state.intake_body_visibility == "plain_controller":
        failures.append("Controller could read sealed startup user request body")
    if state.user_intake_scaffold_written and not state.user_request_ref_recorded:
        failures.append("user intake scaffold was written without a user request reference")
    if state.repo_changed and not (state.installed_skill_synced and state.install_freshness_checked):
        failures.append("installed FlowPilot skill was stale after repository startup fix")
    if state.peer_changes_detected and not state.peer_changes_preserved:
        failures.append("peer-agent changes were overwritten or dropped")
    return failures


def accepts_only_valid_bootstrap_states(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted":
        failures = bootstrap_failures(state)
        if failures:
            return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.scenario == "unset":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", replace(State(), status="new", scenario=scenario))
        return
    candidate = scenario_state(state.scenario)
    failures = bootstrap_failures(candidate)
    if not failures and state.scenario in VALID_SCENARIOS:
        yield Transition(f"accept_{state.scenario}", candidate)
    else:
        yield Transition(
            f"reject_{state.scenario}",
            replace(candidate, status="rejected", terminal_reason=failures[0] if failures else "negative scenario rejected"),
        )


class DeterministicStartupBootstrapStep:
    """Model one startup bootstrap design transition.

    Input x State -> Set(Output x State)
    reads: bootstrap seed proof, scheduler rows, Controller rows, receipts,
    install freshness, and peer-change state
    writes: accepted/rejected design state and terminal reason
    idempotency: replayed receipts over reconciled rows are no-ops and seed
    artifacts are checked before scheduler activation
    """

    name = "DeterministicStartupBootstrapStep"
    input_description = "one startup bootstrap design tick"
    output_description = "one bootstrap/scheduler/reconciliation decision"
    reads = (
        "bootstrap_seed_proof",
        "router_scheduler_ledger",
        "controller_action_ledger",
        "controller_receipts",
        "install_freshness",
        "git_peer_change_state",
    )
    writes = (
        "bootstrap_decision",
        "scheduler_boundary_decision",
        "reconciliation_decision",
        "sync_readiness_decision",
    )
    idempotency = "bootstrap proof gates scheduler activation; reconciled row receipt replay is a no-op"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and state.scenario in VALID_SCENARIOS


def terminal_predicate(_input_obj: Tick, state: State, _trace) -> bool:
    return is_terminal(state)


def build_workflow() -> Workflow:
    return Workflow((DeterministicStartupBootstrapStep(),), name="flowpilot_deterministic_startup_bootstrap")


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 2
INVARIANTS = (
    Invariant(
        name="deterministic_startup_bootstrap_boundary",
        description="Deterministic seed must prove foundation before scheduler and scheduled rows must reconcile idempotently.",
        predicate=accepts_only_valid_bootstrap_states,
    ),
)


def hazard_states() -> dict[str, State]:
    return {scenario: scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}
