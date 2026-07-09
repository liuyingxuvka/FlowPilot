"""FlowGuard model for recursive route entry and closure reconciliation.

Risk purpose:
- Reviews the FlowPilot maintenance pass that makes parent/module entry
  explicit across sibling subtrees and makes terminal closure reconcile defect
  ledgers, role memory, and imported-artifact quarantine.
- Guards against child-before-parent traversal, parent completion before child
  coverage, root-as-worker selection, and terminal closure with dirty
  reconciliation inputs.
- Companion command:
  `python simulations/run_flowpilot_recursive_closure_reconciliation_checks.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


SIBLING_PARENT_ENTRY = "sibling_parent_entry"
TERMINAL_CLOSURE_RECONCILIATION = "terminal_closure_reconciliation"

SCENARIOS = (SIBLING_PARENT_ENTRY, TERMINAL_CLOSURE_RECONCILIATION)
REQUIRED_LABELS = (
    "select_sibling_parent_entry",
    "child_coverage_complete_for_parent_a",
    "complete_parent_a_after_child_review",
    "enter_sibling_parent_b",
    "accept_sibling_parent_b_entry_gate",
    "enter_leaf_b1_after_parent_b",
    "sibling_parent_entry_complete",
    "select_terminal_closure_reconciliation",
    "final_ledger_marked_clean",
    "whole_ledger_hygiene_reconciled",
    "terminal_backward_replay_passed",
    "defect_ledger_reconciled_clean",
    "role_memory_reconciled_current",
    "continuation_quarantine_reconciled_clean",
    "pm_approves_terminal_closure",
    "terminal_closure_reconciliation_complete",
)
MAX_SEQUENCE_LENGTH = 9


@dataclass(frozen=True)
class Tick:
    """One route or closure reconciliation transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | complete
    scenario: str = "unset"

    parent_a_children_completed: bool = False
    parent_a_completed: bool = False
    sibling_parent_b_entered: bool = False
    sibling_parent_b_entry_gate_accepted: bool = False
    leaf_b1_entered: bool = False
    route_root_selected_as_worker: bool = False

    final_ledger_clean: bool = False
    whole_ledger_hygiene_clean: bool = False
    stale_active_blockers_reconciled: bool = False
    dirty_accepted_pointers_reconciled: bool = False
    open_breakglass_reconciled: bool = False
    pending_patch_validation_reconciled: bool = False
    final_replay_authorization_reconciled: bool = False
    terminal_backward_replay_passed: bool = False
    defect_ledger_clean: bool = False
    role_memory_current: bool = False
    continuation_quarantine_clean: bool = False
    pm_closure_approved: bool = False

    unresolved_defect_present: bool = False
    stale_role_memory_authority: bool = False
    imported_artifact_authority_present: bool = False


class RecursiveClosureReconciliationStep:
    """Input x State -> Set(Output x State) for this maintenance boundary.

    reads: effective route tree/frontier, node completion ledgers, final ledger,
      terminal replay, defect ledger, role memory packets, continuation
      quarantine
    writes: next frontier, final ledger reconciliation fields, terminal closure
      suite
    idempotency: route and closure facts are monotonic; terminal states remain
      terminal.
    """

    name = "RecursiveClosureReconciliationStep"
    input_description = "one FlowPilot route or closure reconciliation tick"
    output_description = "next route-frontier or terminal-closure transition"
    reads = (
        "effective_route_tree",
        "execution_frontier",
        "node_completion_ledgers",
        "final_route_wide_gate_ledger",
        "terminal_backward_replay",
        "defect_ledger",
        "role_memory",
        "continuation_quarantine",
    )
    writes = ("execution_frontier", "final_route_wide_gate_ledger", "terminal_closure_suite")
    idempotency = "Retries observe the same current-run source-of-truth ledgers."

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for label, new_state in next_states(state):
            yield FunctionResult(output=Action(label), new_state=new_state, label=label)


def initial_state() -> State:
    return State()


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    if state.status == "complete":
        return ()

    if state.scenario == "unset":
        return tuple(
            (
                f"select_{scenario}",
                replace(state, status="running", scenario=scenario),
            )
            for scenario in SCENARIOS
        )

    if state.scenario == SIBLING_PARENT_ENTRY:
        if not state.parent_a_children_completed:
            return (("child_coverage_complete_for_parent_a", replace(state, parent_a_children_completed=True)),)
        if not state.parent_a_completed:
            return (("complete_parent_a_after_child_review", replace(state, parent_a_completed=True)),)
        if not state.sibling_parent_b_entered:
            return (("enter_sibling_parent_b", replace(state, sibling_parent_b_entered=True)),)
        if not state.sibling_parent_b_entry_gate_accepted:
            return (
                (
                    "accept_sibling_parent_b_entry_gate",
                    replace(state, sibling_parent_b_entry_gate_accepted=True),
                ),
            )
        if not state.leaf_b1_entered:
            return (("enter_leaf_b1_after_parent_b", replace(state, leaf_b1_entered=True)),)
        return (("sibling_parent_entry_complete", replace(state, status="complete")),)

    if state.scenario == TERMINAL_CLOSURE_RECONCILIATION:
        if not state.final_ledger_clean:
            return (("final_ledger_marked_clean", replace(state, final_ledger_clean=True)),)
        if not state.whole_ledger_hygiene_clean:
            return (
                (
                    "whole_ledger_hygiene_reconciled",
                    replace(
                        state,
                        whole_ledger_hygiene_clean=True,
                        stale_active_blockers_reconciled=True,
                        dirty_accepted_pointers_reconciled=True,
                        open_breakglass_reconciled=True,
                        pending_patch_validation_reconciled=True,
                        final_replay_authorization_reconciled=True,
                    ),
                ),
            )
        if not state.terminal_backward_replay_passed:
            return (("terminal_backward_replay_passed", replace(state, terminal_backward_replay_passed=True)),)
        if not state.defect_ledger_clean:
            return (("defect_ledger_reconciled_clean", replace(state, defect_ledger_clean=True)),)
        if not state.role_memory_current:
            return (("role_memory_reconciled_current", replace(state, role_memory_current=True)),)
        if not state.continuation_quarantine_clean:
            return (
                (
                    "continuation_quarantine_reconciled_clean",
                    replace(state, continuation_quarantine_clean=True),
                ),
            )
        if not state.pm_closure_approved:
            return (("pm_approves_terminal_closure", replace(state, pm_closure_approved=True)),)
        return (("terminal_closure_reconciliation_complete", replace(state, status="complete")),)

    return ()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []

    if state.route_root_selected_as_worker:
        failures.append("route root selected as executable worker scope")
    if state.parent_a_completed and not state.parent_a_children_completed:
        failures.append("parent completed before child coverage")
    if state.leaf_b1_entered and not state.sibling_parent_b_entered:
        failures.append("sibling leaf entered before sibling parent/module")
    if state.leaf_b1_entered and not state.sibling_parent_b_entry_gate_accepted:
        failures.append("sibling leaf entered before sibling parent plan/context entry gate")
    if state.sibling_parent_b_entry_gate_accepted and not state.sibling_parent_b_entered:
        failures.append("sibling parent entry gate accepted before parent/module was entered")

    if state.pm_closure_approved and not state.final_ledger_clean:
        failures.append("terminal closure approved without clean final ledger")
    if state.pm_closure_approved and not state.whole_ledger_hygiene_clean:
        failures.append("terminal closure approved without whole-ledger hygiene reconciliation")
    if state.pm_closure_approved and not state.stale_active_blockers_reconciled:
        failures.append("terminal closure approved with stale active blockers unreconciled")
    if state.pm_closure_approved and not state.dirty_accepted_pointers_reconciled:
        failures.append("terminal closure approved with dirty accepted pointers unreconciled")
    if state.pm_closure_approved and not state.open_breakglass_reconciled:
        failures.append("terminal closure approved with open break-glass incidents unreconciled")
    if state.pm_closure_approved and not state.pending_patch_validation_reconciled:
        failures.append("terminal closure approved with pending break-glass patch validation unreconciled")
    if state.pm_closure_approved and not state.final_replay_authorization_reconciled:
        failures.append("terminal closure approved without final replay authorization reconciliation")
    if state.pm_closure_approved and not state.terminal_backward_replay_passed:
        failures.append("terminal closure approved without terminal backward replay")
    if state.pm_closure_approved and not state.defect_ledger_clean:
        failures.append("terminal closure approved without clean defect ledger reconciliation")
    if state.pm_closure_approved and not state.role_memory_current:
        failures.append("terminal closure approved without current role memory reconciliation")
    if state.pm_closure_approved and not state.continuation_quarantine_clean:
        failures.append("terminal closure approved without clean continuation quarantine")
    if state.pm_closure_approved and state.unresolved_defect_present:
        failures.append("terminal closure approved with unresolved defect")
    if state.pm_closure_approved and state.stale_role_memory_authority:
        failures.append("terminal closure approved with stale role memory authority")
    if state.pm_closure_approved and state.imported_artifact_authority_present:
        failures.append("terminal closure approved with imported artifact authority")

    return failures


def _invariant(name: str, expected: str) -> Invariant:
    def check(state: State, trace) -> InvariantResult:
        del trace
        failures = invariant_failures(state)
        if expected in failures:
            return InvariantResult.fail(expected)
        return InvariantResult.pass_()

    return Invariant(name=name, description=expected, predicate=check)


INVARIANTS = (
    _invariant("route_root_not_worker_scope", "route root selected as executable worker scope"),
    _invariant("parent_requires_child_coverage", "parent completed before child coverage"),
    _invariant("sibling_parent_before_leaf", "sibling leaf entered before sibling parent/module"),
    _invariant("sibling_parent_entry_gate_before_leaf", "sibling leaf entered before sibling parent plan/context entry gate"),
    _invariant("sibling_parent_entry_gate_after_parent_entry", "sibling parent entry gate accepted before parent/module was entered"),
    _invariant("closure_requires_clean_final_ledger", "terminal closure approved without clean final ledger"),
    _invariant("closure_requires_whole_ledger_hygiene", "terminal closure approved without whole-ledger hygiene reconciliation"),
    _invariant("closure_blocks_stale_active_blockers", "terminal closure approved with stale active blockers unreconciled"),
    _invariant("closure_blocks_dirty_accepted_pointers", "terminal closure approved with dirty accepted pointers unreconciled"),
    _invariant("closure_blocks_open_breakglass", "terminal closure approved with open break-glass incidents unreconciled"),
    _invariant("closure_blocks_pending_patch_validation", "terminal closure approved with pending break-glass patch validation unreconciled"),
    _invariant("closure_requires_final_replay_authorization", "terminal closure approved without final replay authorization reconciliation"),
    _invariant("closure_requires_terminal_replay", "terminal closure approved without terminal backward replay"),
    _invariant("closure_requires_defect_reconciliation", "terminal closure approved without clean defect ledger reconciliation"),
    _invariant("closure_requires_role_memory_reconciliation", "terminal closure approved without current role memory reconciliation"),
    _invariant("closure_requires_quarantine_reconciliation", "terminal closure approved without clean continuation quarantine"),
    _invariant("closure_blocks_unresolved_defect", "terminal closure approved with unresolved defect"),
    _invariant("closure_blocks_stale_role_memory", "terminal closure approved with stale role memory authority"),
    _invariant("closure_blocks_imported_artifact_authority", "terminal closure approved with imported artifact authority"),
)


HAZARD_STATES = {
    "root_selected_as_worker": replace(initial_state(), route_root_selected_as_worker=True),
    "parent_done_before_children": replace(
        initial_state(),
        status="complete",
        scenario=SIBLING_PARENT_ENTRY,
        parent_a_completed=True,
    ),
    "sibling_leaf_before_parent": replace(
        initial_state(),
        status="complete",
        scenario=SIBLING_PARENT_ENTRY,
        parent_a_children_completed=True,
        parent_a_completed=True,
        leaf_b1_entered=True,
    ),
    "sibling_leaf_before_parent_entry_gate": replace(
        initial_state(),
        status="complete",
        scenario=SIBLING_PARENT_ENTRY,
        parent_a_children_completed=True,
        parent_a_completed=True,
        sibling_parent_b_entered=True,
        leaf_b1_entered=True,
    ),
    "sibling_parent_entry_gate_without_parent_entry": replace(
        initial_state(),
        status="complete",
        scenario=SIBLING_PARENT_ENTRY,
        parent_a_children_completed=True,
        parent_a_completed=True,
        sibling_parent_b_entry_gate_accepted=True,
    ),
    "closure_without_defect_reconciliation": replace(
        initial_state(),
        status="complete",
        scenario=TERMINAL_CLOSURE_RECONCILIATION,
        final_ledger_clean=True,
        whole_ledger_hygiene_clean=True,
        stale_active_blockers_reconciled=True,
        dirty_accepted_pointers_reconciled=True,
        open_breakglass_reconciled=True,
        pending_patch_validation_reconciled=True,
        final_replay_authorization_reconciled=True,
        terminal_backward_replay_passed=True,
        role_memory_current=True,
        continuation_quarantine_clean=True,
        pm_closure_approved=True,
    ),
    "closure_with_stale_active_blocker": replace(
        initial_state(),
        status="complete",
        scenario=TERMINAL_CLOSURE_RECONCILIATION,
        final_ledger_clean=True,
        whole_ledger_hygiene_clean=True,
        stale_active_blockers_reconciled=False,
        dirty_accepted_pointers_reconciled=True,
        open_breakglass_reconciled=True,
        pending_patch_validation_reconciled=True,
        final_replay_authorization_reconciled=True,
        terminal_backward_replay_passed=True,
        defect_ledger_clean=True,
        role_memory_current=True,
        continuation_quarantine_clean=True,
        pm_closure_approved=True,
    ),
    "closure_with_dirty_accepted_pointer": replace(
        initial_state(),
        status="complete",
        scenario=TERMINAL_CLOSURE_RECONCILIATION,
        final_ledger_clean=True,
        whole_ledger_hygiene_clean=True,
        stale_active_blockers_reconciled=True,
        dirty_accepted_pointers_reconciled=False,
        open_breakglass_reconciled=True,
        pending_patch_validation_reconciled=True,
        final_replay_authorization_reconciled=True,
        terminal_backward_replay_passed=True,
        defect_ledger_clean=True,
        role_memory_current=True,
        continuation_quarantine_clean=True,
        pm_closure_approved=True,
    ),
    "closure_with_open_breakglass": replace(
        initial_state(),
        status="complete",
        scenario=TERMINAL_CLOSURE_RECONCILIATION,
        final_ledger_clean=True,
        whole_ledger_hygiene_clean=True,
        stale_active_blockers_reconciled=True,
        dirty_accepted_pointers_reconciled=True,
        open_breakglass_reconciled=False,
        pending_patch_validation_reconciled=True,
        final_replay_authorization_reconciled=True,
        terminal_backward_replay_passed=True,
        defect_ledger_clean=True,
        role_memory_current=True,
        continuation_quarantine_clean=True,
        pm_closure_approved=True,
    ),
    "closure_with_pending_patch_validation": replace(
        initial_state(),
        status="complete",
        scenario=TERMINAL_CLOSURE_RECONCILIATION,
        final_ledger_clean=True,
        whole_ledger_hygiene_clean=True,
        stale_active_blockers_reconciled=True,
        dirty_accepted_pointers_reconciled=True,
        open_breakglass_reconciled=True,
        pending_patch_validation_reconciled=False,
        final_replay_authorization_reconciled=True,
        terminal_backward_replay_passed=True,
        defect_ledger_clean=True,
        role_memory_current=True,
        continuation_quarantine_clean=True,
        pm_closure_approved=True,
    ),
    "closure_without_final_replay_authorization": replace(
        initial_state(),
        status="complete",
        scenario=TERMINAL_CLOSURE_RECONCILIATION,
        final_ledger_clean=True,
        whole_ledger_hygiene_clean=True,
        stale_active_blockers_reconciled=True,
        dirty_accepted_pointers_reconciled=True,
        open_breakglass_reconciled=True,
        pending_patch_validation_reconciled=True,
        final_replay_authorization_reconciled=False,
        terminal_backward_replay_passed=True,
        defect_ledger_clean=True,
        role_memory_current=True,
        continuation_quarantine_clean=True,
        pm_closure_approved=True,
    ),
    "closure_with_unresolved_defect": replace(
        initial_state(),
        status="complete",
        scenario=TERMINAL_CLOSURE_RECONCILIATION,
        final_ledger_clean=True,
        whole_ledger_hygiene_clean=True,
        stale_active_blockers_reconciled=True,
        dirty_accepted_pointers_reconciled=True,
        open_breakglass_reconciled=True,
        pending_patch_validation_reconciled=True,
        final_replay_authorization_reconciled=True,
        terminal_backward_replay_passed=True,
        defect_ledger_clean=True,
        role_memory_current=True,
        continuation_quarantine_clean=True,
        pm_closure_approved=True,
        unresolved_defect_present=True,
    ),
    "closure_with_stale_role_memory": replace(
        initial_state(),
        status="complete",
        scenario=TERMINAL_CLOSURE_RECONCILIATION,
        final_ledger_clean=True,
        whole_ledger_hygiene_clean=True,
        stale_active_blockers_reconciled=True,
        dirty_accepted_pointers_reconciled=True,
        open_breakglass_reconciled=True,
        pending_patch_validation_reconciled=True,
        final_replay_authorization_reconciled=True,
        terminal_backward_replay_passed=True,
        defect_ledger_clean=True,
        role_memory_current=True,
        continuation_quarantine_clean=True,
        pm_closure_approved=True,
        stale_role_memory_authority=True,
    ),
    "closure_with_imported_artifact_authority": replace(
        initial_state(),
        status="complete",
        scenario=TERMINAL_CLOSURE_RECONCILIATION,
        final_ledger_clean=True,
        whole_ledger_hygiene_clean=True,
        stale_active_blockers_reconciled=True,
        dirty_accepted_pointers_reconciled=True,
        open_breakglass_reconciled=True,
        pending_patch_validation_reconciled=True,
        final_replay_authorization_reconciled=True,
        terminal_backward_replay_passed=True,
        defect_ledger_clean=True,
        role_memory_current=True,
        continuation_quarantine_clean=True,
        pm_closure_approved=True,
        imported_artifact_authority_present=True,
    ),
}

HAZARD_EXPECTED_FAILURES = {
    "root_selected_as_worker": "route root selected as executable worker scope",
    "parent_done_before_children": "parent completed before child coverage",
    "sibling_leaf_before_parent": "sibling leaf entered before sibling parent/module",
    "sibling_leaf_before_parent_entry_gate": "sibling leaf entered before sibling parent plan/context entry gate",
    "sibling_parent_entry_gate_without_parent_entry": "sibling parent entry gate accepted before parent/module was entered",
    "closure_without_defect_reconciliation": "terminal closure approved without clean defect ledger reconciliation",
    "closure_with_stale_active_blocker": "terminal closure approved with stale active blockers unreconciled",
    "closure_with_dirty_accepted_pointer": "terminal closure approved with dirty accepted pointers unreconciled",
    "closure_with_open_breakglass": "terminal closure approved with open break-glass incidents unreconciled",
    "closure_with_pending_patch_validation": "terminal closure approved with pending break-glass patch validation unreconciled",
    "closure_without_final_replay_authorization": "terminal closure approved without final replay authorization reconciliation",
    "closure_with_unresolved_defect": "terminal closure approved with unresolved defect",
    "closure_with_stale_role_memory": "terminal closure approved with stale role memory authority",
    "closure_with_imported_artifact_authority": "terminal closure approved with imported artifact authority",
}


def is_terminal(state: State) -> bool:
    return state.status == "complete"


def is_success(state: State) -> bool:
    return is_terminal(state) and not invariant_failures(state)


def build_workflow() -> Workflow:
    return Workflow(
        (RecursiveClosureReconciliationStep(),),
        name="flowpilot_recursive_closure_reconciliation",
    )


EXTERNAL_INPUTS = (Tick(),)
