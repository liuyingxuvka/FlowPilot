"""FlowGuard model for FlowPilot terminal supplemental repair.

Risk intent brief:
- Validate the terminal repair tail added after final Reviewer replay.
- Protected harms: mutating the frozen original contract, treating terminal
  gaps as optional notes, creating a second workflow, dispatching repair work
  without PM supplemental contract/node projection, letting Reviewer perform
  substantive repair work, accepting pre-contract or mismatched evidence,
  bypassing the original terminal gate or the shared-engine receipt handoff,
  omitting supplemental rows from final ledgers or terminal replay, omitting
  final artifact hygiene rows, treating required hygiene gaps as optional, and
  opening a fourth repair round.
- Function block: terminal Reviewer gap + PM repair state -> set of next
  repair/closure/exhaustion states. The runtime/router owns mechanical fields
  and the hard cap; PM owns the supplemental contract; FlowGuard/Reviewer/PM
  gates still own substantive repair confidence.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_TERMINAL_SUPPLEMENTAL_COMPLETION = "valid_terminal_supplemental_completion"
MISSING_SUPPLEMENTAL_CONTRACT = "missing_supplemental_contract"
ORIGINAL_CONTRACT_MUTATED = "original_contract_mutated"
MISSING_REPAIR_ITEM_OWNER = "missing_repair_item_owner"
MISSING_ROUTE_NODE_PROJECTION = "missing_route_node_projection"
REPAIR_BYPASSES_EXISTING_GATES = "repair_bypasses_existing_gates"
FINAL_LEDGER_OMITS_SUPPLEMENTAL = "final_ledger_omits_supplemental"
TERMINAL_REPLAY_OMITS_SUPPLEMENTAL = "terminal_replay_omits_supplemental"
FOURTH_ROUND_PM_PACKET_OPENED = "fourth_round_pm_packet_opened"
HYGIENE_GAP_NOT_CONTRACTUALIZED = "hygiene_gap_not_contractualized"
HYGIENE_CATEGORY_MISSING = "hygiene_category_missing"
FINAL_LEDGER_OMITS_HYGIENE = "final_ledger_omits_hygiene"
TERMINAL_REPLAY_OMITS_HYGIENE_SEGMENT = "terminal_replay_omits_hygiene_segment"
OPTIONAL_HYGIENE_NOTE_BLOCKS = "optional_hygiene_note_blocks"
REVIEWER_ONLY_SUBSTANTIVE_REPAIR = "reviewer_only_substantive_repair"
MISSING_WORKER_REPAIR_PACKET = "missing_worker_repair_packet"
MISSING_WORKER_REPAIR_RESULT = "missing_worker_repair_result"
WORKER_SELF_REVIEWS_REPAIR = "worker_self_reviews_repair"
PRE_CONTRACT_REPAIR_EVIDENCE = "pre_contract_repair_evidence"
MISMATCHED_REPAIR_EVIDENCE = "mismatched_repair_evidence"
WRONG_TERMINAL_GATE = "wrong_terminal_gate"
MISSING_SHARED_ENGINE_RECEIPT = "missing_shared_engine_receipt"
MISMATCHED_SHARED_ENGINE_HANDOFF = "mismatched_shared_engine_handoff"

VALID_SCENARIOS = (VALID_TERMINAL_SUPPLEMENTAL_COMPLETION,)
NEGATIVE_SCENARIOS = (
    MISSING_SUPPLEMENTAL_CONTRACT,
    ORIGINAL_CONTRACT_MUTATED,
    MISSING_REPAIR_ITEM_OWNER,
    MISSING_ROUTE_NODE_PROJECTION,
    REPAIR_BYPASSES_EXISTING_GATES,
    FINAL_LEDGER_OMITS_SUPPLEMENTAL,
    TERMINAL_REPLAY_OMITS_SUPPLEMENTAL,
    FOURTH_ROUND_PM_PACKET_OPENED,
    HYGIENE_GAP_NOT_CONTRACTUALIZED,
    HYGIENE_CATEGORY_MISSING,
    FINAL_LEDGER_OMITS_HYGIENE,
    TERMINAL_REPLAY_OMITS_HYGIENE_SEGMENT,
    OPTIONAL_HYGIENE_NOTE_BLOCKS,
    REVIEWER_ONLY_SUBSTANTIVE_REPAIR,
    MISSING_WORKER_REPAIR_PACKET,
    MISSING_WORKER_REPAIR_RESULT,
    WORKER_SELF_REVIEWS_REPAIR,
    PRE_CONTRACT_REPAIR_EVIDENCE,
    MISMATCHED_REPAIR_EVIDENCE,
    WRONG_TERMINAL_GATE,
    MISSING_SHARED_ENGINE_RECEIPT,
    MISMATCHED_SHARED_ENGINE_HANDOFF,
)
SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class State:
    scenario: str = ""
    status: str = "start"
    terminal_gap_reported: bool = False
    terminal_gap_report_role: str = ""
    original_contract_preserved: bool = True
    supplemental_contract_written: bool = False
    supplemental_contract_id: str = ""
    supplemental_repair_item_id: str = ""
    owner_repair_node_id: str = ""
    supplemental_contract_generation: int = 0
    repair_items_required: bool = False
    repair_items_have_owner_nodes: bool = False
    route_nodes_project_items: bool = False
    substantive_repair_role: str = ""
    repair_packet_kind: str = ""
    repair_packet_generation: int = 0
    repair_result_role: str = ""
    repair_result_generation: int = 0
    repair_evidence_generation: int = 0
    repair_evidence_contract_id: str = ""
    repair_evidence_item_id: str = ""
    repair_evidence_owner_node_id: str = ""
    review_role: str = ""
    review_generation: int = 0
    existing_gates_reused: bool = False
    source_terminal_gate_id: str = ""
    repair_terminal_gate_id: str = ""
    same_terminal_gate_reused: bool = False
    shared_engine_receipt_id: str = ""
    shared_engine_receipt_generation: int = 0
    reviewer_handoff_receipt_id: str = ""
    reviewer_handoff_generation: int = 0
    final_ledger_covers_supplemental: bool = False
    terminal_replay_covers_supplemental: bool = False
    hygiene_gap_reported: bool = False
    hygiene_gap_required: bool = False
    hygiene_gap_contractualized: bool = False
    hygiene_category_recorded: bool = False
    final_ledger_covers_hygiene: bool = False
    terminal_replay_covers_hygiene: bool = False
    optional_hygiene_note_blocks: bool = False
    current_round: int = 0
    max_rounds: int = 3
    pm_packet_open_after_exhaustion: bool = False
    terminal_lifecycle_status: str = ""


class Tick(NamedTuple):
    command: str = "step"


class Action(NamedTuple):
    label: str


class Transition(NamedTuple):
    label: str
    state: State


class TerminalSupplementalRepairStep:
    name = "TerminalSupplementalRepairStep"
    input_description = "terminal supplemental repair tick"
    output_description = "one terminal repair transition"
    reads = (
        "terminal_gap_reported",
        "supplemental_contract_written",
        "route_nodes_project_items",
        "repair_actor_and_packet_contract",
        "repair_evidence_generation",
        "shared_engine_receipt_handoff",
        "terminal_gate_identity",
        "current_round",
    )
    writes = (
        "terminal_supplemental_repair",
        "worker_repair_result",
        "reviewer_decision",
        "shared_engine_receipt_handoff",
        "final_ledgers",
        "terminal_lifecycle",
    )
    idempotency = "monotonic terminal repair facts"

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


def _scenario_state(scenario: str) -> State:
    base = State(
        scenario=scenario,
        status="running",
        terminal_gap_reported=True,
        terminal_gap_report_role="reviewer",
        original_contract_preserved=True,
        supplemental_contract_written=True,
        supplemental_contract_id="terminal-supplemental-repair-r1",
        supplemental_repair_item_id="terminal-gap-r1-item-1",
        owner_repair_node_id="node-terminal-repair-r1",
        supplemental_contract_generation=1,
        repair_items_required=True,
        repair_items_have_owner_nodes=True,
        route_nodes_project_items=True,
        substantive_repair_role="worker",
        repair_packet_kind="task",
        repair_packet_generation=2,
        repair_result_role="worker",
        repair_result_generation=3,
        repair_evidence_generation=3,
        repair_evidence_contract_id="terminal-supplemental-repair-r1",
        repair_evidence_item_id="terminal-gap-r1-item-1",
        repair_evidence_owner_node_id="node-terminal-repair-r1",
        review_role="reviewer",
        review_generation=6,
        existing_gates_reused=True,
        source_terminal_gate_id="terminal_backward_replay",
        repair_terminal_gate_id="terminal_backward_replay",
        same_terminal_gate_reused=True,
        shared_engine_receipt_id="flowguard-terminal-repair-r1",
        shared_engine_receipt_generation=4,
        reviewer_handoff_receipt_id="flowguard-terminal-repair-r1",
        reviewer_handoff_generation=5,
        final_ledger_covers_supplemental=True,
        terminal_replay_covers_supplemental=True,
        hygiene_gap_reported=False,
        hygiene_gap_required=False,
        hygiene_gap_contractualized=True,
        hygiene_category_recorded=True,
        final_ledger_covers_hygiene=True,
        terminal_replay_covers_hygiene=True,
        optional_hygiene_note_blocks=False,
        current_round=1,
        max_rounds=3,
    )
    if scenario == VALID_TERMINAL_SUPPLEMENTAL_COMPLETION:
        return base
    if scenario == MISSING_SUPPLEMENTAL_CONTRACT:
        return replace(base, supplemental_contract_written=False)
    if scenario == ORIGINAL_CONTRACT_MUTATED:
        return replace(base, original_contract_preserved=False)
    if scenario == MISSING_REPAIR_ITEM_OWNER:
        return replace(base, repair_items_have_owner_nodes=False)
    if scenario == MISSING_ROUTE_NODE_PROJECTION:
        return replace(base, route_nodes_project_items=False)
    if scenario == REPAIR_BYPASSES_EXISTING_GATES:
        return replace(base, existing_gates_reused=False)
    if scenario == FINAL_LEDGER_OMITS_SUPPLEMENTAL:
        return replace(base, final_ledger_covers_supplemental=False)
    if scenario == TERMINAL_REPLAY_OMITS_SUPPLEMENTAL:
        return replace(base, terminal_replay_covers_supplemental=False)
    if scenario == FOURTH_ROUND_PM_PACKET_OPENED:
        return replace(
            base,
            current_round=3,
            pm_packet_open_after_exhaustion=True,
            terminal_lifecycle_status="",
        )
    if scenario == HYGIENE_GAP_NOT_CONTRACTUALIZED:
        return replace(
            base,
            hygiene_gap_reported=True,
            hygiene_gap_required=True,
            hygiene_gap_contractualized=False,
        )
    if scenario == HYGIENE_CATEGORY_MISSING:
        return replace(
            base,
            hygiene_gap_reported=True,
            hygiene_gap_required=True,
            hygiene_gap_contractualized=True,
            hygiene_category_recorded=False,
        )
    if scenario == FINAL_LEDGER_OMITS_HYGIENE:
        return replace(
            base,
            hygiene_gap_reported=True,
            hygiene_gap_required=True,
            final_ledger_covers_hygiene=False,
        )
    if scenario == TERMINAL_REPLAY_OMITS_HYGIENE_SEGMENT:
        return replace(
            base,
            hygiene_gap_reported=True,
            terminal_replay_covers_hygiene=False,
        )
    if scenario == OPTIONAL_HYGIENE_NOTE_BLOCKS:
        return replace(
            base,
            hygiene_gap_reported=True,
            hygiene_gap_required=False,
            optional_hygiene_note_blocks=True,
        )
    if scenario == REVIEWER_ONLY_SUBSTANTIVE_REPAIR:
        return replace(
            base,
            substantive_repair_role="reviewer",
            repair_packet_kind="review",
            repair_result_role="reviewer",
        )
    if scenario == MISSING_WORKER_REPAIR_PACKET:
        return replace(base, substantive_repair_role="", repair_packet_kind="", repair_packet_generation=0)
    if scenario == MISSING_WORKER_REPAIR_RESULT:
        return replace(base, repair_result_role="", repair_result_generation=0)
    if scenario == WORKER_SELF_REVIEWS_REPAIR:
        return replace(base, review_role="worker")
    if scenario == PRE_CONTRACT_REPAIR_EVIDENCE:
        return replace(base, supplemental_contract_generation=4, repair_evidence_generation=3)
    if scenario == MISMATCHED_REPAIR_EVIDENCE:
        return replace(base, repair_evidence_contract_id="terminal-supplemental-repair-r0")
    if scenario == WRONG_TERMINAL_GATE:
        return replace(base, repair_terminal_gate_id="node_result_review", same_terminal_gate_reused=False)
    if scenario == MISSING_SHARED_ENGINE_RECEIPT:
        return replace(base, shared_engine_receipt_id="", shared_engine_receipt_generation=0)
    if scenario == MISMATCHED_SHARED_ENGINE_HANDOFF:
        return replace(base, reviewer_handoff_receipt_id="flowguard-unrelated-receipt")
    raise ValueError(f"unknown scenario: {scenario}")


def repair_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.terminal_gap_reported and not state.supplemental_contract_written:
        failures.append("terminal gap repair requires PM supplemental contract")
    if state.terminal_gap_reported and state.terminal_gap_report_role != "reviewer":
        failures.append("terminal gap must be reported by Reviewer before PM contracts repair")
    if not state.original_contract_preserved:
        failures.append("terminal supplemental repair must not mutate frozen original contract")
    if state.supplemental_contract_written and not state.repair_items_required:
        failures.append("supplemental contract requires repair_items")
    if state.supplemental_contract_written and not state.repair_items_have_owner_nodes:
        failures.append("supplemental repair items require owner repair nodes")
    if state.supplemental_contract_written and not state.route_nodes_project_items:
        failures.append("repair route nodes must project supplemental contract and item ids")
    if state.supplemental_contract_written:
        if state.substantive_repair_role != "worker" or state.repair_packet_kind != "task":
            failures.append("terminal substantive repair requires a Worker task packet, not a Reviewer repair packet")
        if state.repair_packet_generation <= state.supplemental_contract_generation:
            failures.append("Worker repair packet must be created after the supplemental contract")
        if state.repair_result_role != "worker" or state.repair_result_generation <= state.repair_packet_generation:
            failures.append("terminal substantive repair requires a fresh Worker-owned result after the repair packet")
        if state.review_role != "reviewer" or state.review_role == state.substantive_repair_role:
            failures.append("terminal repair result requires a distinct Reviewer after Worker execution")
        if state.review_generation <= state.reviewer_handoff_generation:
            failures.append("Reviewer decision must occur after the shared-engine evidence handoff")
        if state.repair_evidence_generation <= state.supplemental_contract_generation:
            failures.append("repair evidence must be created after supplemental contract generation")
        if state.repair_evidence_generation < state.repair_result_generation:
            failures.append("repair evidence cannot predate the Worker repair result")
        evidence_matches = (
            state.repair_evidence_contract_id == state.supplemental_contract_id
            and state.repair_evidence_item_id == state.supplemental_repair_item_id
            and state.repair_evidence_owner_node_id == state.owner_repair_node_id
        )
        if not evidence_matches:
            failures.append("repair evidence must match the supplemental contract, item, and owner repair node")
    if state.supplemental_contract_written and not state.existing_gates_reused:
        failures.append("supplemental repair nodes must reuse existing FlowPilot gates")
    if state.supplemental_contract_written and (
        not state.same_terminal_gate_reused
        or not state.source_terminal_gate_id
        or state.repair_terminal_gate_id != state.source_terminal_gate_id
    ):
        failures.append("terminal repair must return through the same terminal backward-replay gate")
    if state.supplemental_contract_written and (
        not state.shared_engine_receipt_id
        or state.shared_engine_receipt_generation <= state.repair_evidence_generation
    ):
        failures.append("terminal repair requires a current shared-engine receipt after Worker evidence")
    if state.supplemental_contract_written and (
        state.reviewer_handoff_receipt_id != state.shared_engine_receipt_id
        or state.reviewer_handoff_generation <= state.shared_engine_receipt_generation
    ):
        failures.append("Reviewer handoff must consume the matching current shared-engine receipt")
    if state.supplemental_contract_written and not state.final_ledger_covers_supplemental:
        failures.append("final ledgers must include supplemental repair closure rows")
    if state.supplemental_contract_written and not state.terminal_replay_covers_supplemental:
        failures.append("terminal backward replay must include supplemental repair segments")
    if state.current_round >= state.max_rounds and state.pm_packet_open_after_exhaustion:
        failures.append("runtime must stop instead of opening a fourth supplemental repair round")
    if state.hygiene_gap_reported and state.hygiene_gap_required and not state.hygiene_gap_contractualized:
        failures.append("required final artifact hygiene gap requires PM supplemental repair contract")
    if state.hygiene_gap_reported and state.hygiene_gap_required and not state.hygiene_category_recorded:
        failures.append("final artifact hygiene repair items require hygiene_category")
    if state.hygiene_gap_reported and state.hygiene_gap_required and not state.final_ledger_covers_hygiene:
        failures.append("final ledgers must include final artifact hygiene closure rows")
    if state.hygiene_gap_reported and not state.terminal_replay_covers_hygiene:
        failures.append("terminal backward replay must include final artifact hygiene segment")
    if state.hygiene_gap_reported and not state.hygiene_gap_required and state.optional_hygiene_note_blocks:
        failures.append("optional hygiene notes must not block closure unless PM imports them")
    return failures


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "start":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _scenario_state(scenario))
        return
    if state.status != "running":
        return
    failures = repair_failures(state)
    if failures:
        terminal_status = "repair_rounds_exhausted" if state.current_round >= state.max_rounds else ""
        yield Transition(
            f"reject_{state.scenario}",
            replace(state, status="rejected", terminal_lifecycle_status=terminal_status),
        )
    else:
        yield Transition(f"accept_{state.scenario}", replace(state, status="accepted"))


def build_workflow() -> Workflow:
    return Workflow((TerminalSupplementalRepairStep(),), name="flowpilot_terminal_supplemental_repair")


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and not repair_failures(state)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def _accepted_state_is_clean(state: State, _trace: object = ()) -> InvariantResult:
    if state.status == "accepted" and repair_failures(state):
        return InvariantResult(False, "accepted supplemental repair state still has failures")
    return InvariantResult(True, "accepted states are clean")


def _exhaustion_blocks_new_pm_packet(state: State, _trace: object = ()) -> InvariantResult:
    if state.current_round >= state.max_rounds and state.pm_packet_open_after_exhaustion and state.status == "accepted":
        return InvariantResult(False, "fourth-round PM packet cannot be accepted")
    return InvariantResult(True, "round cap blocks fourth-round PM packet")


INVARIANTS = (
    Invariant(
        name="accepted_state_is_clean",
        description="Accepted terminal supplemental repair states must have no repair failures.",
        predicate=_accepted_state_is_clean,
    ),
    Invariant(
        name="exhaustion_blocks_new_pm_packet",
        description="The third supplemental repair round must stop instead of opening another PM repair packet.",
        predicate=_exhaustion_blocks_new_pm_packet,
    ),
)


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 4
