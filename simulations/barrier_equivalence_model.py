"""FlowGuard model for equivalent FlowPilot barrier-bundle compression.

The model checks that a shorter barrier sequence cannot drop any legacy
obligation, role boundary, packet-body isolation rule, route-mutation stale
evidence requirement, cache hash requirement, or final ledger/replay gate.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))

import barrier_bundle  # noqa: E402


BARRIER_ORDER = barrier_bundle.barrier_ids()
LEGACY_OBLIGATIONS = barrier_bundle.all_legacy_obligation_ids()
OBLIGATION_BITS = {name: 1 << index for index, name in enumerate(LEGACY_OBLIGATIONS)}
BARRIER_BITS = {name: 1 << index for index, name in enumerate(BARRIER_ORDER)}
ALL_OBLIGATION_MASK = sum(OBLIGATION_BITS.values())
ALL_BARRIER_MASK = sum(BARRIER_BITS.values())
MAX_SEQUENCE_LENGTH = len(BARRIER_ORDER) + 2


@dataclass(frozen=True)
class Tick:
    """One barrier-bundle controller/ledger transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | blocked | complete
    next_barrier_index: int = 0
    passed_barrier_mask: int = 0
    obligation_mask: int = 0

    controller_read_sealed_body: bool = False
    controller_originated_evidence: bool = False
    controller_summarized_body: bool = False
    ai_discretion_used: bool = False
    wrong_role_approval_used: bool = False
    missing_required_role_slice: bool = False
    missing_required_obligation: bool = False
    reviewer_gate_missing: bool = False
    officer_gate_missing: bool = False
    cache_reuse_claimed: bool = False
    input_hash_same: bool = True
    source_hash_same: bool = True
    evidence_hash_valid: bool = True
    stale_evidence_used: bool = False
    route_mutation_recorded: bool = False
    stale_evidence_marked: bool = True
    frontier_rewritten_after_mutation: bool = True
    final_ledger_clean: bool = True
    terminal_backward_replay_passed: bool = True


class Transition(NamedTuple):
    label: str
    state: State


def _mask_for_obligations(obligations: Iterable[str]) -> int:
    result = 0
    for obligation in obligations:
        result |= OBLIGATION_BITS[obligation]
    return result


def initial_state() -> State:
    return State()


class BarrierBundleStep:
    """Model one equivalent barrier transition.

    Input x State -> Set(Output x State)
    reads: current barrier index, previous barrier mask, obligation mask, cache
    reuse flags, route-mutation freshness, controller boundary, final closure
    facts
    writes: one passed barrier, its covered legacy obligation bits, or terminal
    completion status
    idempotency: a repeated tick observes already-passed barriers and advances
    at most one missing barrier; no role body content is read or merged.
    """

    name = "BarrierBundleStep"
    reads = (
        "barrier_index",
        "passed_barriers",
        "legacy_obligation_coverage",
        "controller_boundary",
        "cache_hashes",
        "route_mutation_freshness",
        "final_closure",
    )
    writes = ("passed_barrier", "legacy_obligation_coverage", "terminal_status")
    input_description = "FlowPilot barrier-bundle tick"
    output_description = "one abstract equivalent barrier action"
    idempotency = "ticks are monotonic over barrier and obligation masks"

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
    if state.status == "new":
        return (Transition("barrier_bundle_run_started", replace(state, status="running")),)
    if invariant_failures(state):
        return (Transition("barrier_bundle_blocked_on_invariant_failure", replace(state, status="blocked")),)
    if state.next_barrier_index < len(BARRIER_ORDER):
        barrier_id = BARRIER_ORDER[state.next_barrier_index]
        required = barrier_bundle.required_obligation_ids(barrier_id)
        new_mask = state.obligation_mask | _mask_for_obligations(required)
        if barrier_id == "final_closure":
            new_mask |= ALL_OBLIGATION_MASK
        return (
            Transition(
                f"{barrier_id}_barrier_bundle_passed",
                replace(
                    state,
                    next_barrier_index=state.next_barrier_index + 1,
                    passed_barrier_mask=state.passed_barrier_mask | BARRIER_BITS[barrier_id],
                    obligation_mask=new_mask,
                ),
            ),
        )
    return (
        Transition(
            "completion_recorded_after_all_equivalent_obligations",
            replace(state, status="complete"),
        ),
    )


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.controller_read_sealed_body:
        failures.append("Controller read a sealed packet/result body")
    if state.controller_originated_evidence:
        failures.append("Controller originated project evidence")
    if state.controller_summarized_body:
        failures.append("Controller summarized sealed body content")
    if state.ai_discretion_used:
        failures.append("AI discretion was used to downgrade or skip a barrier")
    if state.wrong_role_approval_used:
        failures.append("wrong role approval was used for a bundled gate")
    if state.missing_required_role_slice:
        failures.append("barrier bundle missing a required role slice")
    if state.missing_required_obligation:
        failures.append("barrier bundle missing a required legacy obligation")
    if state.reviewer_gate_missing:
        failures.append("reviewer gate missing from bundled evidence")
    if state.officer_gate_missing:
        failures.append("FlowGuard officer gate missing from bundled evidence")
    if state.cache_reuse_claimed and not state.input_hash_same:
        failures.append("cache reuse claimed after input hash changed")
    if state.cache_reuse_claimed and not state.source_hash_same:
        failures.append("cache reuse claimed after source hash changed")
    if state.cache_reuse_claimed and not state.evidence_hash_valid:
        failures.append("cache reuse claimed with invalid evidence hash")
    if state.stale_evidence_used:
        failures.append("stale evidence was used by a barrier")
    if state.route_mutation_recorded and not state.stale_evidence_marked:
        failures.append("route mutation did not mark affected evidence stale")
    if state.route_mutation_recorded and not state.frontier_rewritten_after_mutation:
        failures.append("route mutation did not rewrite the frontier")
    if state.passed_barrier_mask & BARRIER_BITS["final_closure"]:
        if state.obligation_mask != ALL_OBLIGATION_MASK:
            failures.append("final closure passed before all legacy obligations were covered")
        if not state.final_ledger_clean:
            failures.append("final closure passed without clean final ledger")
        if not state.terminal_backward_replay_passed:
            failures.append("final closure passed without terminal backward replay")
    if state.status == "complete" and state.obligation_mask != ALL_OBLIGATION_MASK:
        failures.append("completion recorded before all legacy obligations were covered")
    if state.status == "complete" and state.passed_barrier_mask != ALL_BARRIER_MASK:
        failures.append("completion recorded before every barrier bundle passed")
    return failures


def barrier_equivalence_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_barrier_bundle_equivalence",
        description=(
            "Barrier bundles may compress control transitions only when they "
            "preserve all legacy obligations, required role slices, hash-checked "
            "cache reuse, stale-evidence invalidation, final ledger, terminal "
            "backward replay, and Controller envelope-only authority."
        ),
        predicate=barrier_equivalence_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((BarrierBundleStep(),), name="flowpilot_barrier_bundle_equivalence")


def is_terminal(state: State) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


def _complete_prefix_state() -> State:
    return State(
        status="running",
        next_barrier_index=len(BARRIER_ORDER),
        passed_barrier_mask=ALL_BARRIER_MASK,
        obligation_mask=ALL_OBLIGATION_MASK,
    )


def hazard_states() -> dict[str, State]:
    base = _complete_prefix_state()
    partial = replace(
        base,
        obligation_mask=ALL_OBLIGATION_MASK ^ OBLIGATION_BITS["packet_ledger_mail_delivery"],
    )
    without_final_barrier = replace(base, passed_barrier_mask=ALL_BARRIER_MASK ^ BARRIER_BITS["final_closure"])
    return {
        "ai_discretion_bypass": replace(base, ai_discretion_used=True),
        "controller_reads_sealed_body": replace(base, controller_read_sealed_body=True),
        "controller_originates_evidence": replace(base, controller_originated_evidence=True),
        "controller_summarizes_body": replace(base, controller_summarized_body=True),
        "wrong_role_approval": replace(base, wrong_role_approval_used=True),
        "missing_required_role_slice": replace(base, missing_required_role_slice=True),
        "missing_required_obligation": replace(base, missing_required_obligation=True),
        "missing_reviewer_gate": replace(base, reviewer_gate_missing=True),
        "missing_officer_gate": replace(base, officer_gate_missing=True),
        "cache_reuse_after_input_change": replace(base, cache_reuse_claimed=True, input_hash_same=False),
        "cache_reuse_after_source_change": replace(base, cache_reuse_claimed=True, source_hash_same=False),
        "cache_reuse_with_bad_evidence_hash": replace(base, cache_reuse_claimed=True, evidence_hash_valid=False),
        "stale_evidence_used": replace(base, stale_evidence_used=True),
        "route_mutation_without_stale_mark": replace(
            base,
            route_mutation_recorded=True,
            stale_evidence_marked=False,
        ),
        "route_mutation_without_frontier_rewrite": replace(
            base,
            route_mutation_recorded=True,
            frontier_rewritten_after_mutation=False,
        ),
        "final_closure_without_all_obligations": replace(
            partial,
            passed_barrier_mask=ALL_BARRIER_MASK,
        ),
        "final_closure_without_clean_ledger": replace(base, final_ledger_clean=False),
        "final_closure_without_terminal_replay": replace(base, terminal_backward_replay_passed=False),
        "completion_without_all_barriers": replace(without_final_barrier, status="complete"),
    }


__all__ = [
    "BARRIER_ORDER",
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "LEGACY_OBLIGATIONS",
    "MAX_SEQUENCE_LENGTH",
    "State",
    "Tick",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
]
