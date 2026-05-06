"""FlowGuard model for proof-carrying FlowPilot router checks.

Risk intent brief:
- Prevent AI-authored payload claims such as "done", "user chose X", or
  "automation verified" from becoming router-only pass conditions.
- Allow reviewer burden to move to Router only when the evidence is
  recomputable by the router/runtime or backed by a host/user receipt bound to
  the current run.
- Preserve human-like reviewer ownership for live external facts, source
  quality, user-intent ambiguity, visual/product judgement, and backward replay
  unless proof-carrying evidence exists.
- Modeled state includes proof source, run binding, router recomputation,
  audit-file emission, reviewer fallback, and gate opening.
- Blindspot: this is an abstract gate-ownership model. Production confidence
  still requires router runtime tests and card/protocol checks.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


TRUSTED_SOURCES = {"router_computed", "packet_runtime_hash", "host_receipt"}
REVIEWER_FACT_KINDS = {
    "live_heartbeat",
    "live_agent_freshness",
    "user_intent_without_receipt",
    "source_quality",
    "visual_or_product_judgement",
    "backward_replay_judgement",
}
REQUIRED_LABELS = (
    "router_collects_packet_runtime_hash",
    "router_collects_host_receipt",
    "router_collects_self_attested_live_fact",
    "trusted_router_check_writes_audit",
    "untrusted_fact_routes_to_reviewer",
    "reviewer_checks_live_fact",
    "gate_opens_from_router_proof",
    "gate_opens_from_reviewer_check",
)
MAX_SEQUENCE_LENGTH = 6


@dataclass(frozen=True)
class Tick:
    """One proof-classification tick."""


@dataclass(frozen=True)
class Action:
    name: str
    gate_owner: str


@dataclass(frozen=True)
class State:
    step: int = 0
    status: str = "new"  # new | classifying | waiting_for_reviewer | complete | blocked
    fact_kind: str = "none"
    proof_source: str = "none"  # none | self_attested_ai | router_computed | packet_runtime_hash | host_receipt
    proof_bound_to_current_run: bool = False
    router_recomputed_or_verified: bool = False
    router_audit_file_written: bool = False
    reviewer_required: bool = False
    reviewer_checked: bool = False
    router_only_passed: bool = False
    reviewer_passed: bool = False
    reviewer_gate_replaced: bool = False
    ai_claim_used_as_proof: bool = False
    work_gate_opened: bool = False


class Transition(NamedTuple):
    label: str
    gate_owner: str
    state: State


def initial_state() -> State:
    return State()


def proof_is_trusted(state: State) -> bool:
    if state.proof_source not in TRUSTED_SOURCES:
        return False
    if state.proof_source == "host_receipt" and not state.proof_bound_to_current_run:
        return False
    return state.router_recomputed_or_verified


def fact_requires_reviewer_without_trusted_proof(state: State) -> bool:
    return state.fact_kind in REVIEWER_FACT_KINDS and not proof_is_trusted(state)


class ProofCarryingGateStep:
    """Classify one FlowPilot gate as Router-owned or reviewer-owned.

    Input x State -> Set(Output x State)
    reads: fact kind, proof source, run binding, router recomputation status,
    audit-file status, and reviewer result status
    writes: reviewer_required, router_only_passed, reviewer_gate_replaced,
    router_audit_file_written, reviewer_passed, work_gate_opened
    idempotency: repeated ticks cannot convert self-attested evidence into
    trusted proof or open the same gate through a second owner
    """

    name = "ProofCarryingGateStep"
    reads = (
        "fact_kind",
        "proof_source",
        "proof_bound_to_current_run",
        "router_recomputed_or_verified",
        "router_audit_file_written",
        "reviewer_checked",
    )
    writes = (
        "reviewer_required",
        "router_only_passed",
        "reviewer_gate_replaced",
        "reviewer_passed",
        "work_gate_opened",
    )
    input_description = "one router/reviewer gate ownership decision"
    output_description = "router-owned audit pass, reviewer-required pass, or blocker"
    idempotency = "repeat ticks leave completed/blocked states terminal"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label, transition.gate_owner),
                new_state=transition.state,
                label=transition.label,
            )


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"complete", "blocked"}:
        return ()
    if invariant_failures(state):
        return (Transition("blocked_on_invariant_failure", "router", replace(state, status="blocked")),)

    if state.step == 0:
        return (
            Transition(
                "router_collects_packet_runtime_hash",
                "router",
                replace(
                    state,
                    step=1,
                    status="classifying",
                    fact_kind="packet_envelope",
                    proof_source="packet_runtime_hash",
                    proof_bound_to_current_run=True,
                    router_recomputed_or_verified=True,
                ),
            ),
            Transition(
                "router_collects_host_receipt",
                "router",
                replace(
                    state,
                    step=1,
                    status="classifying",
                    fact_kind="startup_user_intent",
                    proof_source="host_receipt",
                    proof_bound_to_current_run=True,
                    router_recomputed_or_verified=True,
                ),
            ),
            Transition(
                "router_collects_self_attested_live_fact",
                "reviewer",
                replace(
                    state,
                    step=1,
                    status="classifying",
                    fact_kind="live_heartbeat",
                    proof_source="self_attested_ai",
                    ai_claim_used_as_proof=True,
                ),
            ),
        )

    if state.step == 1:
        if proof_is_trusted(state):
            return (
                Transition(
                    "trusted_router_check_writes_audit",
                    "router",
                    replace(
                        state,
                        step=2,
                        router_only_passed=True,
                        reviewer_gate_replaced=True,
                        router_audit_file_written=True,
                    ),
                ),
            )
        return (
            Transition(
                "untrusted_fact_routes_to_reviewer",
                "human_like_reviewer",
                replace(state, step=2, status="waiting_for_reviewer", reviewer_required=True),
            ),
        )

    if state.step == 2:
        if state.reviewer_required:
            return (
                Transition(
                    "reviewer_checks_live_fact",
                    "human_like_reviewer",
                    replace(state, step=3, reviewer_checked=True, reviewer_passed=True),
                ),
            )
        return (
            Transition(
                "gate_opens_from_router_proof",
                "router",
                replace(state, step=4, status="complete", work_gate_opened=True),
            ),
        )

    if state.step == 3 and state.reviewer_required and state.reviewer_passed:
        return (
            Transition(
                "gate_opens_from_reviewer_check",
                "project_manager",
                replace(state, step=4, status="complete", work_gate_opened=True),
            ),
        )
    return ()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.router_only_passed and not proof_is_trusted(state):
        failures.append("router-only pass used evidence that was not recomputable or host-bound")
    if state.reviewer_gate_replaced and not state.router_audit_file_written:
        failures.append("reviewer gate was replaced without a router audit file")
    if state.reviewer_gate_replaced and state.ai_claim_used_as_proof:
        failures.append("self-attested AI claim replaced reviewer check")
    if fact_requires_reviewer_without_trusted_proof(state) and state.work_gate_opened and not state.reviewer_passed:
        failures.append("live or judgement fact opened work without reviewer pass")
    if state.work_gate_opened and not (state.router_only_passed or state.reviewer_passed):
        failures.append("work gate opened without router proof or reviewer pass")
    if state.reviewer_required and state.reviewer_gate_replaced:
        failures.append("gate is both reviewer-required and reviewer-replaced")
    if state.proof_source == "host_receipt" and state.router_only_passed and not state.proof_bound_to_current_run:
        failures.append("host receipt was accepted without current-run binding")
    return failures


def proof_carrying_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="proof_carrying_router_checks",
        description="Router-only checks require recomputable or host-bound proof; untrusted live facts keep reviewer review.",
        predicate=proof_carrying_invariant,
    ),
)
EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((ProofCarryingGateStep(),), name="flowpilot_proof_carrying_router_checks")


def is_terminal(state: State) -> bool:
    return state.status in {"complete", "blocked"}


def is_success(state: State) -> bool:
    return state.status == "complete"


def _complete_router_proof_base(**changes: object) -> State:
    base = State(
        step=4,
        status="complete",
        fact_kind="packet_envelope",
        proof_source="packet_runtime_hash",
        proof_bound_to_current_run=True,
        router_recomputed_or_verified=True,
        router_audit_file_written=True,
        router_only_passed=True,
        reviewer_gate_replaced=True,
        work_gate_opened=True,
    )
    return replace(base, **changes)


def _complete_reviewer_base(**changes: object) -> State:
    base = State(
        step=4,
        status="complete",
        fact_kind="live_heartbeat",
        proof_source="self_attested_ai",
        ai_claim_used_as_proof=True,
        reviewer_required=True,
        reviewer_checked=True,
        reviewer_passed=True,
        work_gate_opened=True,
    )
    return replace(base, **changes)


def hazard_states() -> dict[str, State]:
    return {
        "router_only_from_self_attested_claim": _complete_router_proof_base(
            fact_kind="live_heartbeat",
            proof_source="self_attested_ai",
            ai_claim_used_as_proof=True,
            router_recomputed_or_verified=False,
        ),
        "trusted_router_pass_without_audit_file": _complete_router_proof_base(
            router_audit_file_written=False,
        ),
        "live_fact_opened_without_reviewer": _complete_reviewer_base(
            reviewer_checked=False,
            reviewer_passed=False,
        ),
        "host_receipt_not_bound_to_current_run": _complete_router_proof_base(
            fact_kind="startup_user_intent",
            proof_source="host_receipt",
            proof_bound_to_current_run=False,
        ),
        "reviewer_required_and_replaced": _complete_reviewer_base(
            reviewer_gate_replaced=True,
            router_only_passed=True,
            router_audit_file_written=True,
        ),
    }


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "REQUIRED_LABELS",
    "State",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "next_states",
]
