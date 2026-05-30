"""FlowGuard model for FlowPilot behavior-preserving structural refactors.

Risk purpose:
- Uses real FlowGuard (https://github.com/liuyingxuvka/FlowGuard) to review the
  maintenance process for structure-only FlowPilot refactors.
- Guards against mixing behavior changes into code movement, deleting unsupported_historical
  entrypoints, changing protocol/JSON shapes, validating only after multiple
  slices, skipping Meta/Capability checks after model-file edits, or committing
  local main before install/public-boundary validation.
- Run with `python simulations/run_flowpilot_structural_refactor_checks.py`
  whenever a maintenance pass splits router, model, test, or install tooling
  structure without intending behavior changes.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


BOUNDARIES = (
    "duplicate_wrappers",
    "packet_runtime",
    "install_check_tooling",
    "meta_model_phases",
    "capability_model_phases",
    "router_event_intake",
    "router_action_apply",
    "router_runtime_tests",
    "docs_install_sync",
)


@dataclass(frozen=True)
class Tick:
    """One structural maintenance step."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | complete
    baseline_recorded: bool = False
    openspec_ready: bool = False
    flowguard_ready: bool = False
    current_boundary: str = "none"
    boundary_changed: bool = False
    boundaries_completed: tuple[str, ...] = ()
    focused_validation_done: bool = False
    unsupported_historical_entrypoints_preserved: bool = True
    protocol_json_shape_preserved: bool = True
    behavior_tests_passed: bool = False
    model_files_touched: bool = False
    meta_capability_checks_completed: bool = False
    install_sync_checked: bool = False
    public_boundary_checked: bool = False
    local_git_sync_done: bool = False
    extra_work_branch_present: bool = False
    tag_or_release_done: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _start_next_boundary(state: State) -> Transition | None:
    completed = set(state.boundaries_completed)
    for boundary in BOUNDARIES:
        if boundary not in completed:
            return Transition(
                f"start_{boundary}_slice",
                replace(
                    state,
                    current_boundary=boundary,
                    boundary_changed=True,
                    focused_validation_done=False,
                    model_files_touched=boundary in {"meta_model_phases", "capability_model_phases"},
                ),
            )
    return None


class StructuralRefactorStep:
    """One behavior-preserving structural maintenance transition.

    Input x State -> Set(Output x State)
    reads: baseline record, OpenSpec plan, FlowGuard guard model, active slice,
      validation evidence, install/public-boundary sync evidence
    writes: slice completion evidence, validation status, final sync status
    idempotency: each boundary is completed at most once before local git sync.
    """

    name = "StructuralRefactorStep"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "complete":
        return

    if not state.baseline_recorded:
        yield Transition("record_baseline_and_rollback_point", replace(state, status="running", baseline_recorded=True))
        return
    if not state.openspec_ready:
        yield Transition("write_openspec_structure_contract", replace(state, openspec_ready=True))
        return
    if not state.flowguard_ready:
        yield Transition("run_structural_refactor_flowguard_guard", replace(state, flowguard_ready=True))
        return

    if state.current_boundary == "none":
        next_boundary = _start_next_boundary(state)
        if next_boundary is not None:
            yield next_boundary
            return
        if not state.install_sync_checked:
            yield Transition("sync_installed_flowpilot_skill", replace(state, install_sync_checked=True))
            return
        if not state.public_boundary_checked:
            yield Transition("run_public_boundary_privacy_check", replace(state, public_boundary_checked=True))
            return
        if not state.local_git_sync_done:
            yield Transition("commit_local_main_without_release", replace(state, local_git_sync_done=True))
            return
        yield Transition("structural_refactor_complete", replace(state, status="complete"))
        return

    if state.model_files_touched and not state.meta_capability_checks_completed:
        yield Transition(
            "run_meta_and_capability_checks_for_model_split",
            replace(state, meta_capability_checks_completed=True),
        )
        return

    if not state.focused_validation_done:
        yield Transition(
            "run_focused_validation_for_current_slice",
            replace(state, focused_validation_done=True, behavior_tests_passed=True),
        )
        return

    completed = tuple(list(state.boundaries_completed) + [state.current_boundary])
    yield Transition(
        f"complete_{state.current_boundary}_slice",
        replace(
            state,
            current_boundary="none",
            boundary_changed=False,
            focused_validation_done=False,
            boundaries_completed=completed,
        ),
    )


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.boundary_changed and not state.baseline_recorded:
        failures.append("structural refactor changed code before baseline was recorded")
    if state.boundary_changed and not state.openspec_ready:
        failures.append("structural refactor changed code before OpenSpec contract was ready")
    if state.boundary_changed and not state.flowguard_ready:
        failures.append("structural refactor changed code before FlowGuard guard passed")
    if not state.unsupported_historical_entrypoints_preserved:
        failures.append("structural refactor deleted or bypassed unsupported_historical entrypoints")
    if not state.protocol_json_shape_preserved:
        failures.append("structure-only refactor changed protocol or JSON shape")
    if state.current_boundary != "none" and state.focused_validation_done and not state.behavior_tests_passed:
        failures.append("slice validation recorded without behavior-facing tests")
    if (
        ("meta_model_phases" in state.boundaries_completed or "capability_model_phases" in state.boundaries_completed)
        and not state.meta_capability_checks_completed
    ):
        failures.append("Meta/Capability model split completed before both heavyweight checks completed")
    if state.local_git_sync_done and not state.install_sync_checked:
        failures.append("local git sync happened before installed skill sync check")
    if state.local_git_sync_done and not state.public_boundary_checked:
        failures.append("local git sync happened before public-boundary privacy check")
    if state.local_git_sync_done and state.current_boundary != "none":
        failures.append("local git sync happened while a slice was still open")
    if state.local_git_sync_done and state.extra_work_branch_present:
        failures.append("local git sync finished while an extra local work branch still existed")
    if state.tag_or_release_done:
        failures.append("structure maintenance performed tag or release without explicit release scope")
    return failures


def structural_refactor_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="behavior_preserving_structural_refactor_order",
        description=(
            "Structure-only FlowPilot refactors keep a rollback baseline, "
            "OpenSpec contract, FlowGuard guard, one changed boundary per "
            "validated slice, model checks after model-file edits, and install/"
            "privacy checks before local git sync."
        ),
        predicate=structural_refactor_invariant,
    ),
)


def hazard_states() -> dict[str, State]:
    return {
        "change_before_baseline": State(status="running", boundary_changed=True),
        "change_before_openspec": State(status="running", baseline_recorded=True, boundary_changed=True),
        "change_before_flowguard": State(
            status="running",
            baseline_recorded=True,
            openspec_ready=True,
            boundary_changed=True,
        ),
        "compat_entrypoint_deleted": State(
            status="running",
            baseline_recorded=True,
            openspec_ready=True,
            flowguard_ready=True,
            boundary_changed=True,
            unsupported_historical_entrypoints_preserved=False,
        ),
        "protocol_shape_changed": State(
            status="running",
            baseline_recorded=True,
            openspec_ready=True,
            flowguard_ready=True,
            boundary_changed=True,
            protocol_json_shape_preserved=False,
        ),
        "model_split_without_heavy_checks": State(
            status="running",
            baseline_recorded=True,
            openspec_ready=True,
            flowguard_ready=True,
            boundaries_completed=("meta_model_phases",),
            meta_capability_checks_completed=False,
        ),
        "local_git_sync_before_install_sync": State(
            status="running",
            baseline_recorded=True,
            openspec_ready=True,
            flowguard_ready=True,
            public_boundary_checked=True,
            local_git_sync_done=True,
        ),
        "local_git_sync_before_privacy_check": State(
            status="running",
            baseline_recorded=True,
            openspec_ready=True,
            flowguard_ready=True,
            install_sync_checked=True,
            local_git_sync_done=True,
        ),
        "local_git_sync_with_extra_work_branch": State(
            status="running",
            baseline_recorded=True,
            openspec_ready=True,
            flowguard_ready=True,
            install_sync_checked=True,
            public_boundary_checked=True,
            local_git_sync_done=True,
            extra_work_branch_present=True,
        ),
        "tag_release_in_structure_pass": State(
            status="running",
            baseline_recorded=True,
            openspec_ready=True,
            flowguard_ready=True,
            tag_or_release_done=True,
        ),
    }


def build_workflow() -> Workflow:
    return Workflow((StructuralRefactorStep(),), name="flowpilot_structural_refactor")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status == "complete"


def is_success(state: State) -> bool:
    return state.status == "complete" and state.local_git_sync_done


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 40
