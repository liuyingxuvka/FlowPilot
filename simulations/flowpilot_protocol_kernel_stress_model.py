"""Stress model for the clean FlowPilot protocol kernel.

The model is intentionally deterministic. It simulates role-binding leases and
ledger events so multi-round failures can be replayed without external AI
services.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import Any, Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_protocol_kernel_stress"

ACCEPTED = "accepted"
BLOCK_MISSING_ACK = "block_missing_ack"
BLOCK_ACK_WITHOUT_OUTPUT = "block_ack_without_output"
BLOCK_WRONG_PACKET_SHAPE = "block_wrong_packet_shape"
BLOCK_CLOSED_AGENT_OUTPUT = "block_closed_agent_output"
BLOCK_ROUTE_MUTATION_OLD_PACKET = "block_route_mutation_old_packet"
BLOCK_SELF_REVIEW = "block_self_review"
BLOCK_WEAK_REVIEW = "block_weak_review"
BLOCK_FLOWGUARD_WRONG_TARGET = "block_flowguard_wrong_target"
BLOCK_STALE_EVIDENCE = "block_stale_evidence"
BLOCK_PROGRESS_ONLY_BACKGROUND = "block_progress_only_background"
BLOCK_FINAL_CLOSURE_GAP = "block_final_closure_gap"
BLOCK_INSUFFICIENT_EVIDENCE = "block_insufficient_acceptance_evidence"

SAFE_CLASSIFICATIONS = {ACCEPTED}

RANDOM_SEEDS = (101, 202, 303, 404, 505, 606, 707, 808, 909, 1001)
RANDOM_STEPS_PER_SEED = 80


@dataclass(frozen=True)
class StressState:
    status: str = "running"  # new | running | accepted | blocked
    active_route_version: int = 1
    active_lease_id: str = ""
    lease_status: str = "none"  # none | active | timed_out | closed
    packet_id: str = ""
    packet_route_version: int = 1
    ack_received: bool = False
    progress_seen: bool = False
    result_submitted: bool = False
    result_packet_valid: bool = False
    result_route_version: int = 1
    result_producer_lease_id: str = ""
    result_after_close: bool = False
    old_route_packets_open: bool = False
    old_route_disposition: str = ""  # open | closed | quarantined | rebound
    stale_result_rejected: bool = False
    reviewer_id: str = ""
    reviewer_independent: bool = False
    review_checks_evidence: bool = False
    review_decision: str = ""
    required_model_target: str = "development_process"
    flowguard_model_target: str = ""
    flowguard_decision: str = ""
    source_generation: int = 1
    evidence_generation: int = 0
    background_evidence_status: str = "not_required"
    final_backward_chain: bool = False
    classification: str = ""
    last_event: str = ""
    event_count: int = 0


@dataclass(frozen=True)
class ScriptedScenario:
    name: str
    events: tuple[str, ...]
    expected_classification: str
    family: str


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    expected_classification: str
    actual_classification: str
    accepted: bool
    ok: bool
    events: tuple[str, ...]
    final_state: StressState

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "expected_classification": self.expected_classification,
            "actual_classification": self.actual_classification,
            "accepted": self.accepted,
            "ok": self.ok,
            "events": list(self.events),
            "final_state": state_summary(self.final_state),
        }


@dataclass(frozen=True)
class Tick:
    """One stress-model exploration tick."""


@dataclass(frozen=True)
class Action:
    label: str


class Transition(NamedTuple):
    label: str
    state: StressState


SCRIPTED_SCENARIOS: tuple[ScriptedScenario, ...] = (
    ScriptedScenario(
        name="happy_path_replacement_worker",
        events=(
            "issue_worker",
            "worker_ack",
            "worker_progress",
            "worker_timeout",
            "close_lease",
            "issue_worker",
            "worker_ack",
            "submit_valid_result",
            "write_current_evidence",
            "independent_review_accept",
            "flowguard_development_process_pass",
            "final_backward_chain",
            "attempt_accept",
        ),
        expected_classification=ACCEPTED,
        family="replacement_success",
    ),
    ScriptedScenario(
        name="missing_ack_result_attempt",
        events=(
            "issue_worker",
            "submit_valid_result",
            "write_current_evidence",
            "independent_review_accept",
            "flowguard_development_process_pass",
            "final_backward_chain",
            "attempt_accept",
        ),
        expected_classification=BLOCK_MISSING_ACK,
        family="missing_ack",
    ),
    ScriptedScenario(
        name="ack_only_timeout",
        events=("issue_worker", "worker_ack", "worker_progress", "attempt_accept"),
        expected_classification=BLOCK_ACK_WITHOUT_OUTPUT,
        family="ack_without_output",
    ),
    ScriptedScenario(
        name="wrong_shape_result",
        events=(
            "issue_worker",
            "worker_ack",
            "submit_invalid_result",
            "write_current_evidence",
            "independent_review_accept",
            "flowguard_development_process_pass",
            "final_backward_chain",
            "attempt_accept",
        ),
        expected_classification=BLOCK_WRONG_PACKET_SHAPE,
        family="wrong_packet_shape",
    ),
    ScriptedScenario(
        name="closed_agent_late_output",
        events=(
            "issue_worker",
            "worker_ack",
            "close_lease",
            "late_submit_valid_result",
            "write_current_evidence",
            "independent_review_accept",
            "flowguard_development_process_pass",
            "final_backward_chain",
            "attempt_accept",
        ),
        expected_classification=BLOCK_CLOSED_AGENT_OUTPUT,
        family="closed_agent_late_output",
    ),
    ScriptedScenario(
        name="route_mutation_stale_return",
        events=(
            "issue_worker",
            "worker_ack",
            "mutate_route",
            "submit_old_route_result",
            "write_current_evidence",
            "independent_review_accept",
            "flowguard_development_process_pass",
            "final_backward_chain",
            "attempt_accept",
        ),
        expected_classification=BLOCK_ROUTE_MUTATION_OLD_PACKET,
        family="route_mutation_stale_output",
    ),
    ScriptedScenario(
        name="weak_review_after_valid_result",
        events=(
            "issue_worker",
            "worker_ack",
            "submit_valid_result",
            "write_current_evidence",
            "weak_review_accept",
            "flowguard_development_process_pass",
            "final_backward_chain",
            "attempt_accept",
        ),
        expected_classification=BLOCK_WEAK_REVIEW,
        family="weak_review",
    ),
    ScriptedScenario(
        name="self_review_after_valid_result",
        events=(
            "issue_worker",
            "worker_ack",
            "submit_valid_result",
            "write_current_evidence",
            "self_review_accept",
            "flowguard_development_process_pass",
            "final_backward_chain",
            "attempt_accept",
        ),
        expected_classification=BLOCK_SELF_REVIEW,
        family="self_review",
    ),
    ScriptedScenario(
        name="stale_evidence_after_source_change",
        events=(
            "issue_worker",
            "worker_ack",
            "submit_valid_result",
            "source_changes",
            "write_stale_evidence",
            "independent_review_accept",
            "flowguard_development_process_pass",
            "final_backward_chain",
            "attempt_accept",
        ),
        expected_classification=BLOCK_STALE_EVIDENCE,
        family="stale_evidence",
    ),
    ScriptedScenario(
        name="wrong_flowguard_target_then_final_claim",
        events=(
            "issue_worker",
            "worker_ack",
            "submit_valid_result",
            "write_current_evidence",
            "independent_review_accept",
            "flowguard_target_product_pass",
            "final_backward_chain",
            "attempt_accept",
        ),
        expected_classification=BLOCK_FLOWGUARD_WRONG_TARGET,
        family="wrong_flowguard_target",
    ),
    ScriptedScenario(
        name="mixed_correct_and_stale_results",
        events=(
            "issue_worker",
            "worker_ack",
            "mutate_route",
            "submit_old_route_result",
            "reject_stale_result",
            "close_old_route_packets",
            "issue_worker",
            "worker_ack",
            "submit_valid_result",
            "write_current_evidence",
            "independent_review_accept",
            "flowguard_development_process_pass",
            "final_backward_chain",
            "attempt_accept",
        ),
        expected_classification=ACCEPTED,
        family="stale_and_current_mixed",
    ),
    ScriptedScenario(
        name="final_closure_gap_after_all_green",
        events=(
            "issue_worker",
            "worker_ack",
            "submit_valid_result",
            "write_current_evidence",
            "independent_review_accept",
            "flowguard_development_process_pass",
            "attempt_accept",
        ),
        expected_classification=BLOCK_FINAL_CLOSURE_GAP,
        family="final_closure_gap",
    ),
    ScriptedScenario(
        name="progress_only_background_evidence",
        events=(
            "issue_worker",
            "worker_ack",
            "submit_valid_result",
            "write_current_evidence",
            "independent_review_accept",
            "flowguard_development_process_pass",
            "background_progress_only",
            "final_backward_chain",
            "attempt_accept",
        ),
        expected_classification=BLOCK_PROGRESS_ONLY_BACKGROUND,
        family="progress_only_background",
    ),
)

SCENARIO_BY_NAME = {scenario.name: scenario for scenario in SCRIPTED_SCENARIOS}
SAFE_SCENARIOS = {
    scenario.name for scenario in SCRIPTED_SCENARIOS if scenario.expected_classification == ACCEPTED
}
RISK_SCENARIOS = {scenario.name for scenario in SCRIPTED_SCENARIOS} - SAFE_SCENARIOS

HISTORICAL_REPLAY_CASES = (
    "ack_only_timeout",
    "closed_agent_late_output",
    "route_mutation_stale_return",
    "stale_evidence_after_source_change",
    "progress_only_background_evidence",
    "wrong_flowguard_target_then_final_claim",
    "weak_review_after_valid_result",
    "self_review_after_valid_result",
    "final_closure_gap_after_all_green",
)

RANDOM_EVENTS = (
    "issue_worker",
    "issue_worker",
    "worker_ack",
    "worker_progress",
    "submit_valid_result",
    "submit_invalid_result",
    "source_changes",
    "write_current_evidence",
    "write_stale_evidence",
    "independent_review_accept",
    "weak_review_accept",
    "self_review_accept",
    "flowguard_development_process_pass",
    "flowguard_target_product_pass",
    "mutate_route",
    "reject_stale_result",
    "close_old_route_packets",
    "close_lease",
    "late_submit_valid_result",
    "background_progress_only",
    "background_pass",
    "final_backward_chain",
    "attempt_accept",
)


def initial_state() -> StressState:
    return StressState(status="new")


def empty_run_state() -> StressState:
    return StressState(status="running")


def _new_packet_state(state: StressState, lease_id: str) -> StressState:
    return replace(
        state,
        active_lease_id=lease_id,
        lease_status="active",
        packet_id=f"packet-r{state.active_route_version}-{lease_id}",
        packet_route_version=state.active_route_version,
        ack_received=False,
        progress_seen=False,
        result_submitted=False,
        result_packet_valid=False,
        result_route_version=state.active_route_version,
        result_producer_lease_id="",
        result_after_close=False,
        reviewer_id="",
        reviewer_independent=False,
        review_checks_evidence=False,
        review_decision="",
        flowguard_model_target="",
        flowguard_decision="",
        final_backward_chain=False,
    )


def _with_event(state: StressState, event: str) -> StressState:
    return replace(state, last_event=event, event_count=state.event_count + 1)


def apply_event(state: StressState, event: str) -> StressState:
    state = _with_event(state, event)
    if state.status != "running":
        return state

    if event == "issue_worker":
        return _new_packet_state(state, f"worker-{state.event_count}")
    if event == "worker_ack":
        return replace(state, ack_received=True)
    if event == "worker_progress":
        return replace(state, progress_seen=True)
    if event == "worker_timeout":
        return replace(state, lease_status="timed_out")
    if event == "close_lease":
        return replace(state, lease_status="closed")
    if event == "submit_valid_result":
        return replace(
            state,
            result_submitted=True,
            result_packet_valid=True,
            result_route_version=state.packet_route_version,
            result_producer_lease_id=state.active_lease_id,
            result_after_close=state.lease_status != "active",
        )
    if event == "submit_invalid_result":
        return replace(
            state,
            result_submitted=True,
            result_packet_valid=False,
            result_route_version=state.packet_route_version,
            result_producer_lease_id=state.active_lease_id,
            result_after_close=state.lease_status != "active",
        )
    if event == "late_submit_valid_result":
        return replace(
            state,
            result_submitted=True,
            result_packet_valid=True,
            result_route_version=state.packet_route_version,
            result_producer_lease_id=state.active_lease_id or "worker-1",
            result_after_close=True,
        )
    if event == "mutate_route":
        return replace(
            state,
            active_route_version=state.active_route_version + 1,
            old_route_packets_open=True,
            old_route_disposition="open",
        )
    if event == "submit_old_route_result":
        old_version = max(1, state.active_route_version - 1)
        return replace(
            state,
            result_submitted=True,
            result_packet_valid=True,
            result_route_version=old_version,
            packet_route_version=old_version,
            result_producer_lease_id=state.active_lease_id,
            result_after_close=state.lease_status != "active",
        )
    if event == "reject_stale_result":
        return replace(
            state,
            stale_result_rejected=True,
            result_submitted=False,
            result_packet_valid=False,
            result_route_version=state.active_route_version,
            packet_route_version=state.active_route_version,
            result_producer_lease_id="",
            old_route_disposition="quarantined",
        )
    if event == "close_old_route_packets":
        return replace(state, old_route_packets_open=False, old_route_disposition="closed")
    if event == "source_changes":
        return replace(state, source_generation=state.source_generation + 1)
    if event == "write_current_evidence":
        return replace(state, evidence_generation=state.source_generation)
    if event == "write_stale_evidence":
        return replace(state, evidence_generation=max(0, state.source_generation - 1))
    if event == "independent_review_accept":
        return replace(
            state,
            reviewer_id="reviewer-1",
            reviewer_independent=True,
            review_checks_evidence=True,
            review_decision="accept",
        )
    if event == "weak_review_accept":
        return replace(
            state,
            reviewer_id="reviewer-1",
            reviewer_independent=True,
            review_checks_evidence=False,
            review_decision="accept",
        )
    if event == "self_review_accept":
        return replace(
            state,
            reviewer_id=state.active_lease_id,
            reviewer_independent=False,
            review_checks_evidence=True,
            review_decision="accept",
        )
    if event == "flowguard_development_process_pass":
        return replace(
            state,
            flowguard_model_target="development_process",
            flowguard_decision="pass",
        )
    if event == "flowguard_target_product_pass":
        return replace(
            state,
            flowguard_model_target="target_product_behavior",
            flowguard_decision="pass",
        )
    if event == "background_progress_only":
        return replace(state, background_evidence_status="progress_only")
    if event == "background_pass":
        return replace(state, background_evidence_status="passed")
    if event == "final_backward_chain":
        return replace(state, final_backward_chain=True)
    if event == "attempt_accept":
        classification = ACCEPTED if acceptance_ready(state) else block_label(state)
        return replace(
            state,
            status="accepted" if classification == ACCEPTED else "blocked",
            classification=classification,
        )
    raise ValueError(f"unknown stress event: {event}")


def evidence_fresh(state: StressState) -> bool:
    return state.evidence_generation >= state.source_generation and state.evidence_generation > 0


def old_route_safe(state: StressState) -> bool:
    if not state.old_route_packets_open:
        return True
    return state.old_route_disposition in {"closed", "quarantined", "rebound"}


def acceptance_ready(state: StressState) -> bool:
    return (
        state.status == "running"
        and state.active_lease_id != ""
        and state.lease_status == "active"
        and state.ack_received
        and state.result_submitted
        and state.result_packet_valid
        and state.result_producer_lease_id == state.active_lease_id
        and not state.result_after_close
        and state.packet_route_version == state.active_route_version
        and state.result_route_version == state.active_route_version
        and old_route_safe(state)
        and state.reviewer_independent
        and state.review_checks_evidence
        and state.review_decision == "accept"
        and state.flowguard_model_target == state.required_model_target
        and state.flowguard_decision == "pass"
        and evidence_fresh(state)
        and state.background_evidence_status in {"not_required", "passed"}
        and state.final_backward_chain
    )


def block_label(state: StressState) -> str:
    if not state.ack_received:
        return BLOCK_MISSING_ACK
    if not state.result_submitted:
        return BLOCK_ACK_WITHOUT_OUTPUT
    if state.lease_status != "active" or state.result_after_close:
        return BLOCK_CLOSED_AGENT_OUTPUT
    if not state.result_packet_valid:
        return BLOCK_WRONG_PACKET_SHAPE
    if state.packet_route_version != state.active_route_version:
        return BLOCK_ROUTE_MUTATION_OLD_PACKET
    if state.result_route_version != state.active_route_version:
        return BLOCK_ROUTE_MUTATION_OLD_PACKET
    if not old_route_safe(state):
        return BLOCK_ROUTE_MUTATION_OLD_PACKET
    if not state.reviewer_independent:
        return BLOCK_SELF_REVIEW
    if not state.review_checks_evidence:
        return BLOCK_WEAK_REVIEW
    if state.flowguard_model_target != state.required_model_target:
        return BLOCK_FLOWGUARD_WRONG_TARGET
    if not evidence_fresh(state):
        return BLOCK_STALE_EVIDENCE
    if state.background_evidence_status == "progress_only":
        return BLOCK_PROGRESS_ONLY_BACKGROUND
    if not state.final_backward_chain:
        return BLOCK_FINAL_CLOSURE_GAP
    return BLOCK_INSUFFICIENT_EVIDENCE


def run_events(events: Iterable[str]) -> StressState:
    state = empty_run_state()
    for event in events:
        state = apply_event(state, event)
    return state


def run_scripted_scenario(scenario: ScriptedScenario) -> ScenarioResult:
    final_state = run_events(scenario.events)
    actual = final_state.classification or block_label(final_state)
    return ScenarioResult(
        name=scenario.name,
        expected_classification=scenario.expected_classification,
        actual_classification=actual,
        accepted=final_state.status == "accepted",
        ok=actual == scenario.expected_classification,
        events=scenario.events,
        final_state=final_state,
    )


def run_scripted_scenarios() -> dict[str, Any]:
    cases = [run_scripted_scenario(scenario) for scenario in SCRIPTED_SCENARIOS]
    return {
        "ok": all(case.ok for case in cases),
        "case_count": len(cases),
        "accepted_cases": [case.name for case in cases if case.accepted],
        "blocked_cases": [case.name for case in cases if not case.accepted],
        "cases": [case.to_json() for case in cases],
    }


def run_historical_replay() -> dict[str, Any]:
    cases = [run_scripted_scenario(SCENARIO_BY_NAME[name]) for name in HISTORICAL_REPLAY_CASES]
    return {
        "ok": all(case.ok and not case.accepted for case in cases),
        "case_count": len(cases),
        "cases": [case.to_json() for case in cases],
    }


def _unsafe_acceptance_failure(state: StressState) -> str:
    failures = hard_check_failures(state)
    return "; ".join(failures)


def run_seeded_random_long_runs(
    seeds: tuple[int, ...] = RANDOM_SEEDS,
    steps_per_seed: int = RANDOM_STEPS_PER_SEED,
) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []
    for seed in seeds:
        rng = random.Random(seed)
        state = empty_run_state()
        executed_events: list[str] = []
        for step_index in range(steps_per_seed):
            event = rng.choice(RANDOM_EVENTS)
            executed_events.append(event)
            state = apply_event(state, event)
            if state.status == "accepted":
                failure = _unsafe_acceptance_failure(state)
                if failure:
                    violations.append(
                        {
                            "seed": seed,
                            "step_index": step_index,
                            "event": event,
                            "failure": failure,
                            "state": state_summary(state),
                        }
                    )
                break
            if state.status == "blocked":
                break
        runs.append(
            {
                "seed": seed,
                "executed_steps": len(executed_events),
                "terminal_status": state.status,
                "classification": state.classification,
                "events": executed_events,
            }
        )
    return {
        "ok": not violations,
        "seed_count": len(seeds),
        "steps_per_seed": steps_per_seed,
        "violations": violations,
        "runs": runs,
    }


def state_summary(state: StressState) -> dict[str, Any]:
    return {
        "status": state.status,
        "active_route_version": state.active_route_version,
        "active_lease_id": state.active_lease_id,
        "lease_status": state.lease_status,
        "packet_route_version": state.packet_route_version,
        "result_route_version": state.result_route_version,
        "ack_received": state.ack_received,
        "result_submitted": state.result_submitted,
        "result_packet_valid": state.result_packet_valid,
        "result_after_close": state.result_after_close,
        "old_route_packets_open": state.old_route_packets_open,
        "old_route_disposition": state.old_route_disposition,
        "reviewer_independent": state.reviewer_independent,
        "review_checks_evidence": state.review_checks_evidence,
        "flowguard_model_target": state.flowguard_model_target,
        "flowguard_decision": state.flowguard_decision,
        "source_generation": state.source_generation,
        "evidence_generation": state.evidence_generation,
        "background_evidence_status": state.background_evidence_status,
        "final_backward_chain": state.final_backward_chain,
        "classification": state.classification,
        "last_event": state.last_event,
    }


def next_safe_states(state: StressState) -> Iterable[Transition]:
    if state.status == "new":
        for scenario in SCRIPTED_SCENARIOS:
            result = run_scripted_scenario(scenario)
            yield Transition(f"select_{scenario.name}", result.final_state)


def is_terminal(state: StressState) -> bool:
    return state.status in {"accepted", "blocked"}


def terminal_predicate(_input_obj: Tick, state: StressState, _trace: object) -> bool:
    return is_terminal(state)


def is_success(state: StressState) -> bool:
    return is_terminal(state)


def hard_check_failures(state: StressState) -> list[str]:
    failures: list[str] = []
    if state.status == "accepted":
        running_state = replace(state, status="running")
        if not acceptance_ready(running_state):
            failures.append("stress completion was accepted without the full protocol gate")
        if state.classification != ACCEPTED:
            failures.append(f"accepted state has non-accepted classification: {state.classification}")
    if state.status == "blocked" and acceptance_ready(replace(state, status="running")):
        failures.append("stress model blocked a state that satisfied the full protocol gate")
    return failures


def hard_invariant(state: StressState, trace: object) -> InvariantResult:
    del trace
    failures = hard_check_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "flowpilot_protocol_kernel_stress_acceptance_gate",
        "Multi-round completion requires current lease, route, review, FlowGuard, freshness, background, and closure evidence.",
        hard_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 2


class FlowPilotProtocolStressStep:
    """Input x State -> Set(Output x State) for protocol stress scenarios."""

    name = "FlowPilotProtocolStressStep"
    reads = (
        "black_box_ledger",
        "agent_leases",
        "task_packets",
        "result_packets",
        "route_versions",
        "review_reports",
        "flowguard_work_orders",
        "evidence_generations",
        "background_artifacts",
        "final_backward_closure",
    )
    writes = ("stress_acceptance_or_block",)
    input_description = "deterministic multi-round stress tick"
    output_description = "accepted current result or explicit blocked path"

    def apply(self, input_obj: Tick, state: StressState) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def build_workflow() -> Workflow:
    return Workflow((FlowPilotProtocolStressStep(),), name=MODEL_ID)


def scenario_matrix() -> dict[str, str]:
    return {
        scenario.name: run_scripted_scenario(scenario).actual_classification
        for scenario in SCRIPTED_SCENARIOS
    }


def hazard_states() -> dict[str, StressState]:
    hazards: dict[str, StressState] = {}
    for scenario in SCRIPTED_SCENARIOS:
        result = run_scripted_scenario(scenario)
        if scenario.expected_classification != ACCEPTED:
            hazards[f"{scenario.name}_forced_accepted"] = replace(
                result.final_state,
                status="accepted",
                classification=ACCEPTED,
            )
    success = run_scripted_scenario(SCENARIO_BY_NAME["happy_path_replacement_worker"]).final_state
    hazards["happy_path_forced_blocked"] = replace(success, status="blocked", classification=BLOCK_INSUFFICIENT_EVIDENCE)
    return hazards
