"""FlowGuard model for FlowPilot terminal supplemental repair.

Risk intent brief:
- Validate the terminal repair tail added after final Reviewer replay.
- Protected harms: mutating the frozen original contract, treating terminal
  gaps as optional notes, creating a second workflow, dispatching repair work
  without PM supplemental contract/node projection, omitting supplemental rows
  from final ledgers or terminal replay, omitting final artifact hygiene rows,
  treating required hygiene gaps as optional, and opening a fourth repair round.
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
)
SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class State:
    scenario: str = ""
    status: str = "start"
    terminal_gap_reported: bool = False
    original_contract_preserved: bool = True
    supplemental_contract_written: bool = False
    repair_items_required: bool = False
    repair_items_have_owner_nodes: bool = False
    route_nodes_project_items: bool = False
    existing_gates_reused: bool = False
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
        "current_round",
    )
    writes = ("terminal_supplemental_repair", "final_ledgers", "terminal_lifecycle")
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
        original_contract_preserved=True,
        supplemental_contract_written=True,
        repair_items_required=True,
        repair_items_have_owner_nodes=True,
        route_nodes_project_items=True,
        existing_gates_reused=True,
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
    raise ValueError(f"unknown scenario: {scenario}")


def repair_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.terminal_gap_reported and not state.supplemental_contract_written:
        failures.append("terminal gap repair requires PM supplemental contract")
    if not state.original_contract_preserved:
        failures.append("terminal supplemental repair must not mutate frozen original contract")
    if state.supplemental_contract_written and not state.repair_items_required:
        failures.append("supplemental contract requires repair_items")
    if state.supplemental_contract_written and not state.repair_items_have_owner_nodes:
        failures.append("supplemental repair items require owner repair nodes")
    if state.supplemental_contract_written and not state.route_nodes_project_items:
        failures.append("repair route nodes must project supplemental contract and item ids")
    if state.supplemental_contract_written and not state.existing_gates_reused:
        failures.append("supplemental repair nodes must reuse existing FlowPilot gates")
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
