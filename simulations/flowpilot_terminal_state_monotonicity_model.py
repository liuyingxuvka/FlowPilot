"""FlowGuard model for FlowPilot control-plane terminal-state monotonicity.

Risk purpose header:
- FlowGuard: https://github.com/liuyingxuvka/FlowGuard
- Reviews the FlowPilot Router/card-runtime state machine for duplicate, late,
  and replayed control-plane writes after a return, gate, blocker, repair, or
  result record has reached a terminal state.
- Guards against the concrete bug class where a card ACK was already resolved
  but a later duplicate check-in wrote the pending return back to ``returned``
  and made downstream role events look blocked again.
- Future agents should run
  ``python simulations/run_flowpilot_terminal_state_monotonicity_checks.py``
  before changing card ACK handling, pending-return selection, gate blockers,
  PM repair decisions, repair transactions, or result-disposition replay.

Risk intent brief:
- Prevent terminal control-plane facts from being downgraded by duplicate,
  stale, or late inputs.
- Preserve true idempotency: same identity replay writes audit metadata only,
  while a genuinely new identity is still accepted.
- Model-critical state: record kind, terminal proof, completed-record proof,
  incoming identity, write result, pending-selector behavior, downstream
  blocker visibility, and repair-channel liveness.
- Adversarial inputs include duplicate card ACKs, bundle ACKs, incomplete
  bundle ACKs after resolution, stale gate blocks after pass, stale control
  blocker artifacts after resolution, duplicate PM repair decisions, old repair
  generation failures after success, and duplicate result returns after PM
  disposition.
- Hard invariants: terminal wins over nonterminal; pending queries use effective
  status, not raw status alone; same-identity replay is audit-only; new
  identities are not swallowed by old terminal records; stale terminal records
  cannot block PM/reviewer repair events.
- Blindspot: this is an abstract model plus metadata/source audit. It does not
  inspect sealed card, packet, result, or report bodies.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


CARD_ACK_DUPLICATE_AFTER_RESOLVED = "card_ack_duplicate_after_resolved"
BUNDLE_ACK_DUPLICATE_AFTER_RESOLVED = "bundle_ack_duplicate_after_resolved"
INCOMPLETE_BUNDLE_ACK_AFTER_RESOLVED = "incomplete_bundle_ack_after_resolved"
STALE_GATE_BLOCK_AFTER_PASS = "stale_gate_block_after_pass"
STALE_CONTROL_BLOCKER_AFTER_RESOLVED = "stale_control_blocker_after_resolved"
DUPLICATE_PM_REPAIR_DECISION = "duplicate_pm_repair_decision"
NEW_PM_REPAIR_DECISION_NEW_BLOCKER = "new_pm_repair_decision_new_blocker"
OLD_REPAIR_FAILURE_AFTER_SUCCESS = "old_repair_failure_after_success"
NEW_REPAIR_FAILURE_NEW_GENERATION = "new_repair_failure_new_generation"
DUPLICATE_RESULT_AFTER_PM_DISPOSITION = "duplicate_result_after_pm_disposition"
NEW_GATE_BLOCK_NEW_GATE_AFTER_PASS = "new_gate_block_new_gate_after_pass"
NEW_CONTROL_BLOCKER_AFTER_RESOLVED = "new_control_blocker_after_resolved"
NEW_RESULT_RETURN_NEW_RESULT_AFTER_DISPOSITION = "new_result_return_new_result_after_disposition"
UNRESOLVED_CARD_RETURN_STILL_BLOCKS = "unresolved_card_return_still_blocks"

SCENARIOS = (
    CARD_ACK_DUPLICATE_AFTER_RESOLVED,
    BUNDLE_ACK_DUPLICATE_AFTER_RESOLVED,
    INCOMPLETE_BUNDLE_ACK_AFTER_RESOLVED,
    STALE_GATE_BLOCK_AFTER_PASS,
    STALE_CONTROL_BLOCKER_AFTER_RESOLVED,
    DUPLICATE_PM_REPAIR_DECISION,
    NEW_PM_REPAIR_DECISION_NEW_BLOCKER,
    OLD_REPAIR_FAILURE_AFTER_SUCCESS,
    NEW_REPAIR_FAILURE_NEW_GENERATION,
    DUPLICATE_RESULT_AFTER_PM_DISPOSITION,
    NEW_GATE_BLOCK_NEW_GATE_AFTER_PASS,
    NEW_CONTROL_BLOCKER_AFTER_RESOLVED,
    NEW_RESULT_RETURN_NEW_RESULT_AFTER_DISPOSITION,
    UNRESOLVED_CARD_RETURN_STILL_BLOCKS,
)

AUDIT_ONLY_SCENARIOS = {
    CARD_ACK_DUPLICATE_AFTER_RESOLVED,
    BUNDLE_ACK_DUPLICATE_AFTER_RESOLVED,
    INCOMPLETE_BUNDLE_ACK_AFTER_RESOLVED,
    STALE_GATE_BLOCK_AFTER_PASS,
    STALE_CONTROL_BLOCKER_AFTER_RESOLVED,
    DUPLICATE_PM_REPAIR_DECISION,
    OLD_REPAIR_FAILURE_AFTER_SUCCESS,
    DUPLICATE_RESULT_AFTER_PM_DISPOSITION,
}

NEW_IDENTITY_ACCEPTED_SCENARIOS = {
    NEW_PM_REPAIR_DECISION_NEW_BLOCKER,
    NEW_REPAIR_FAILURE_NEW_GENERATION,
    NEW_GATE_BLOCK_NEW_GATE_AFTER_PASS,
    NEW_CONTROL_BLOCKER_AFTER_RESOLVED,
    NEW_RESULT_RETURN_NEW_RESULT_AFTER_DISPOSITION,
}

VALID_BLOCKING_SCENARIOS = {
    UNRESOLVED_CARD_RETURN_STILL_BLOCKS,
}

TERMINAL_STATUSES = {"audit_only", "already_recorded", "accepted_new_identity", "valid_blocking"}


@dataclass(frozen=True)
class Tick:
    """One terminal-state merge decision."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | audit_only | already_recorded | accepted_new_identity
    scenario: str = "unset"
    record_kind: str = "unset"

    terminal_status_before: bool = False
    terminal_marker_present: bool = False
    completed_terminal_record_present: bool = False
    incoming_same_identity: bool = False
    incoming_new_identity: bool = False
    incoming_from_old_generation: bool = False

    writer_preserved_terminal: bool = False
    audit_record_written: bool = False
    pending_selector_uses_terminal_proof: bool = False
    downstream_blocked: bool = False
    repair_channel_blocked: bool = False

    new_side_effect_written: bool = False
    duplicate_side_effect_written: bool = False
    new_blocker_created: bool = False
    stale_block_reactivated: bool = False
    old_generation_reactivated: bool = False
    new_identity_swallowed: bool = False
    unresolved_item_released: bool = False
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class TerminalStateMergeStep:
    """Model one control-plane terminal-state merge.

    Input x State -> Set(Output x State)
    reads: existing terminal proof, completed-record proof, incoming identity,
    old/new generation identity, and pending selector behavior
    writes: audit-only replay, already-recorded replay, or accepted new
    identity side effect
    idempotency: same identity replays cannot downgrade terminal state; new
    identities keep their own scoped side effects
    """

    name = "TerminalStateMergeStep"
    reads = (
        "record_kind",
        "terminal_marker",
        "completed_terminal_record",
        "incoming_identity",
        "generation_identity",
        "pending_selector",
    )
    writes = ("effective_terminal_state", "audit_record", "new_identity_side_effect")
    input_description = "duplicate or late control-plane event"
    output_description = "terminal-state merge decision"
    idempotency = "terminal same-identity replay is audit-only; new identity remains routable"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def initial_state() -> State:
    return State()


def _selected_state(scenario: str) -> State:
    common = {
        "status": "running",
        "scenario": scenario,
        "terminal_status_before": True,
        "terminal_marker_present": True,
        "completed_terminal_record_present": True,
        "incoming_same_identity": True,
        "incoming_new_identity": False,
    }
    if scenario == CARD_ACK_DUPLICATE_AFTER_RESOLVED:
        return State(record_kind="system_card_return", **common)
    if scenario == BUNDLE_ACK_DUPLICATE_AFTER_RESOLVED:
        return State(record_kind="system_card_bundle_return", **common)
    if scenario == INCOMPLETE_BUNDLE_ACK_AFTER_RESOLVED:
        return State(record_kind="system_card_bundle_return", **common)
    if scenario == STALE_GATE_BLOCK_AFTER_PASS:
        return State(record_kind="gate_outcome", **common)
    if scenario == STALE_CONTROL_BLOCKER_AFTER_RESOLVED:
        return State(record_kind="control_blocker", **common)
    if scenario == DUPLICATE_PM_REPAIR_DECISION:
        return State(record_kind="pm_repair_decision", **common)
    if scenario == OLD_REPAIR_FAILURE_AFTER_SUCCESS:
        return State(
            record_kind="repair_transaction",
            incoming_from_old_generation=True,
            **common,
        )
    if scenario == DUPLICATE_RESULT_AFTER_PM_DISPOSITION:
        return State(record_kind="result_disposition", **common)
    if scenario == UNRESOLVED_CARD_RETURN_STILL_BLOCKS:
        return State(
            status="running",
            scenario=scenario,
            record_kind="system_card_return",
            terminal_status_before=False,
            terminal_marker_present=False,
            completed_terminal_record_present=False,
            incoming_same_identity=True,
            incoming_new_identity=False,
        )
    if scenario == NEW_PM_REPAIR_DECISION_NEW_BLOCKER:
        return State(
            status="running",
            scenario=scenario,
            record_kind="pm_repair_decision",
            terminal_status_before=True,
            terminal_marker_present=True,
            completed_terminal_record_present=True,
            incoming_same_identity=False,
            incoming_new_identity=True,
        )
    if scenario == NEW_REPAIR_FAILURE_NEW_GENERATION:
        return State(
            status="running",
            scenario=scenario,
            record_kind="repair_transaction",
            terminal_status_before=True,
            terminal_marker_present=True,
            completed_terminal_record_present=True,
            incoming_same_identity=False,
            incoming_new_identity=True,
        )
    if scenario == NEW_GATE_BLOCK_NEW_GATE_AFTER_PASS:
        return State(
            status="running",
            scenario=scenario,
            record_kind="gate_outcome",
            terminal_status_before=True,
            terminal_marker_present=True,
            completed_terminal_record_present=True,
            incoming_same_identity=False,
            incoming_new_identity=True,
        )
    if scenario == NEW_CONTROL_BLOCKER_AFTER_RESOLVED:
        return State(
            status="running",
            scenario=scenario,
            record_kind="control_blocker",
            terminal_status_before=True,
            terminal_marker_present=True,
            completed_terminal_record_present=True,
            incoming_same_identity=False,
            incoming_new_identity=True,
        )
    if scenario == NEW_RESULT_RETURN_NEW_RESULT_AFTER_DISPOSITION:
        return State(
            status="running",
            scenario=scenario,
            record_kind="result_disposition",
            terminal_status_before=True,
            terminal_marker_present=True,
            completed_terminal_record_present=True,
            incoming_same_identity=False,
            incoming_new_identity=True,
        )
    raise ValueError(f"unknown scenario: {scenario}")


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _selected_state(scenario))
        return
    if state.status != "running":
        return
    if state.scenario in NEW_IDENTITY_ACCEPTED_SCENARIOS:
        yield Transition(
            f"accept_{state.scenario}",
            replace(
                state,
                status="accepted_new_identity",
                writer_preserved_terminal=True,
                pending_selector_uses_terminal_proof=True,
                new_side_effect_written=True,
                terminal_reason="new_scoped_identity",
            ),
        )
        return
    if state.scenario in VALID_BLOCKING_SCENARIOS:
        yield Transition(
            f"keep_{state.scenario}_blocking",
            replace(
                state,
                status="valid_blocking",
                writer_preserved_terminal=True,
                downstream_blocked=True,
                terminal_reason="no_terminal_proof_real_wait",
            ),
        )
        return
    if state.scenario in AUDIT_ONLY_SCENARIOS:
        terminal_status = "already_recorded" if state.scenario == DUPLICATE_PM_REPAIR_DECISION else "audit_only"
        yield Transition(
            f"merge_{state.scenario}_as_audit_only",
            replace(
                state,
                status=terminal_status,
                writer_preserved_terminal=True,
                audit_record_written=True,
                pending_selector_uses_terminal_proof=True,
                terminal_reason="same_identity_terminal_replay",
            ),
        )
        return


def is_terminal(state: State) -> bool:
    return state.status in TERMINAL_STATUSES


def is_success(state: State) -> bool:
    return is_terminal(state)


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return is_terminal(state)


def _hard_check_failures(state: State) -> list[str]:
    failures: list[str] = []
    if not is_terminal(state):
        return failures
    same_terminal_replay = state.terminal_status_before and state.incoming_same_identity
    terminal_proof_available = (
        state.terminal_marker_present or state.completed_terminal_record_present
    )
    if same_terminal_replay and not state.writer_preserved_terminal:
        failures.append("terminal control-plane record was downgraded by same-identity replay")
    if terminal_proof_available and state.downstream_blocked:
        failures.append("terminal-proven record still blocked downstream events")
    if terminal_proof_available and state.repair_channel_blocked:
        failures.append("terminal-proven record blocked the repair channel")
    if terminal_proof_available and not state.pending_selector_uses_terminal_proof:
        failures.append("pending selector ignored terminal proof")
    if same_terminal_replay and state.new_side_effect_written:
        failures.append("same-identity replay wrote a new side effect")
    if state.duplicate_side_effect_written:
        failures.append("duplicate side effect written for terminal replay")
    if state.stale_block_reactivated:
        failures.append("stale block was reactivated after terminal pass or resolution")
    if state.old_generation_reactivated:
        failures.append("old generation event reactivated after newer terminal generation")
    if state.incoming_new_identity and state.new_identity_swallowed:
        failures.append("new scoped identity was swallowed by an old terminal record")
    if state.incoming_new_identity and not state.new_side_effect_written:
        failures.append("new scoped identity did not get its own side effect")
    if not terminal_proof_available and state.unresolved_item_released:
        failures.append("unresolved nonterminal control record was released")
    if state.scenario in VALID_BLOCKING_SCENARIOS and is_terminal(state) and not state.downstream_blocked:
        failures.append("real unresolved control record did not remain blocking")
    if state.status == "valid_blocking" and terminal_proof_available:
        failures.append("terminal-proven control record was treated as a real blocker")
    if state.status == "accepted_new_identity" and not state.incoming_new_identity:
        failures.append("same-identity replay was accepted as a new identity")
    if state.status in {"audit_only", "already_recorded"} and state.incoming_new_identity:
        failures.append("new scoped identity was treated as same-identity replay")
    return failures


def invariant_failures(state: State) -> list[str]:
    return _hard_check_failures(state)


def terminal_state_monotonicity_invariant(state: State, trace: object) -> InvariantResult:
    del trace
    failures = _hard_check_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "flowpilot_terminal_state_monotonicity",
        "Terminal control-plane records are monotonic under duplicate, late, and replayed inputs.",
        terminal_state_monotonicity_invariant,
    ),
)


def hazard_states() -> dict[str, State]:
    safe_card = replace(
        _selected_state(CARD_ACK_DUPLICATE_AFTER_RESOLVED),
        status="audit_only",
        writer_preserved_terminal=True,
        audit_record_written=True,
        pending_selector_uses_terminal_proof=True,
    )
    safe_bundle = replace(
        _selected_state(BUNDLE_ACK_DUPLICATE_AFTER_RESOLVED),
        status="audit_only",
        writer_preserved_terminal=True,
        audit_record_written=True,
        pending_selector_uses_terminal_proof=True,
    )
    safe_gate = replace(
        _selected_state(STALE_GATE_BLOCK_AFTER_PASS),
        status="audit_only",
        writer_preserved_terminal=True,
        audit_record_written=True,
        pending_selector_uses_terminal_proof=True,
    )
    safe_control = replace(
        _selected_state(STALE_CONTROL_BLOCKER_AFTER_RESOLVED),
        status="audit_only",
        writer_preserved_terminal=True,
        audit_record_written=True,
        pending_selector_uses_terminal_proof=True,
    )
    safe_repair = replace(
        _selected_state(OLD_REPAIR_FAILURE_AFTER_SUCCESS),
        status="audit_only",
        writer_preserved_terminal=True,
        audit_record_written=True,
        pending_selector_uses_terminal_proof=True,
    )
    safe_new_repair = replace(
        _selected_state(NEW_REPAIR_FAILURE_NEW_GENERATION),
        status="accepted_new_identity",
        writer_preserved_terminal=True,
        pending_selector_uses_terminal_proof=True,
        new_side_effect_written=True,
    )
    safe_unresolved_wait = replace(
        _selected_state(UNRESOLVED_CARD_RETURN_STILL_BLOCKS),
        status="valid_blocking",
        writer_preserved_terminal=True,
        downstream_blocked=True,
    )
    safe_new_gate = replace(
        _selected_state(NEW_GATE_BLOCK_NEW_GATE_AFTER_PASS),
        status="accepted_new_identity",
        writer_preserved_terminal=True,
        pending_selector_uses_terminal_proof=True,
        new_side_effect_written=True,
    )
    safe_new_control_blocker = replace(
        _selected_state(NEW_CONTROL_BLOCKER_AFTER_RESOLVED),
        status="accepted_new_identity",
        writer_preserved_terminal=True,
        pending_selector_uses_terminal_proof=True,
        new_side_effect_written=True,
    )
    safe_new_result = replace(
        _selected_state(NEW_RESULT_RETURN_NEW_RESULT_AFTER_DISPOSITION),
        status="accepted_new_identity",
        writer_preserved_terminal=True,
        pending_selector_uses_terminal_proof=True,
        new_side_effect_written=True,
    )
    return {
        "resolved_card_return_reopened_by_duplicate_ack": replace(
            safe_card,
            writer_preserved_terminal=False,
            downstream_blocked=True,
        ),
        "resolved_bundle_return_reopened_by_duplicate_ack": replace(
            safe_bundle,
            writer_preserved_terminal=False,
            downstream_blocked=True,
        ),
        "resolved_bundle_return_downgraded_to_incomplete": replace(
            safe_bundle,
            writer_preserved_terminal=False,
            downstream_blocked=True,
        ),
        "pending_selector_ignores_resolved_at": replace(
            safe_card,
            pending_selector_uses_terminal_proof=False,
            downstream_blocked=True,
        ),
        "pending_selector_ignores_completed_return": replace(
            safe_card,
            terminal_marker_present=False,
            completed_terminal_record_present=True,
            pending_selector_uses_terminal_proof=False,
            downstream_blocked=True,
        ),
        "repair_channel_blocked_by_resolved_return": replace(
            safe_card,
            repair_channel_blocked=True,
        ),
        "gate_pass_reopened_by_late_block": replace(
            safe_gate,
            stale_block_reactivated=True,
            downstream_blocked=True,
        ),
        "resolved_control_blocker_reactivated_by_stale_artifact": replace(
            safe_control,
            stale_block_reactivated=True,
            repair_channel_blocked=True,
        ),
        "duplicate_pm_repair_created_new_blocker": replace(
            _selected_state(DUPLICATE_PM_REPAIR_DECISION),
            status="already_recorded",
            writer_preserved_terminal=True,
            pending_selector_uses_terminal_proof=True,
            new_blocker_created=True,
            new_side_effect_written=True,
        ),
        "old_repair_generation_failure_reopened_success": replace(
            safe_repair,
            old_generation_reactivated=True,
            repair_channel_blocked=True,
        ),
        "new_repair_generation_failure_swallowed": replace(
            safe_new_repair,
            status="already_recorded",
            new_identity_swallowed=True,
            new_side_effect_written=False,
        ),
        "result_disposition_reopened_by_duplicate_result": replace(
            _selected_state(DUPLICATE_RESULT_AFTER_PM_DISPOSITION),
            status="audit_only",
            writer_preserved_terminal=False,
            pending_selector_uses_terminal_proof=True,
            downstream_blocked=True,
        ),
        "same_identity_replay_writes_duplicate_side_effect": replace(
            safe_card,
            duplicate_side_effect_written=True,
        ),
        "new_gate_identity_swallowed_by_old_pass": replace(
            safe_new_gate,
            status="audit_only",
            new_identity_swallowed=True,
            new_side_effect_written=False,
        ),
        "new_control_blocker_swallowed_by_old_resolution": replace(
            safe_new_control_blocker,
            status="audit_only",
            new_identity_swallowed=True,
            new_side_effect_written=False,
        ),
        "new_result_identity_swallowed_by_old_disposition": replace(
            safe_new_result,
            status="audit_only",
            new_identity_swallowed=True,
            new_side_effect_written=False,
        ),
        "real_unresolved_return_released_by_overbroad_terminal_merge": replace(
            safe_unresolved_wait,
            downstream_blocked=False,
            unresolved_item_released=True,
        ),
    }


def build_workflow() -> Workflow:
    return Workflow((TerminalStateMergeStep(),), name="flowpilot_terminal_state_monotonicity")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


__all__ = [
    "AUDIT_ONLY_SCENARIOS",
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "NEW_IDENTITY_ACCEPTED_SCENARIOS",
    "VALID_BLOCKING_SCENARIOS",
    "SCENARIOS",
    "State",
    "Tick",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "next_states",
    "terminal_predicate",
]
