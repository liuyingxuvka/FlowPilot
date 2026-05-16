"""FlowGuard model for FlowPilot parallel run isolation.

Risk purpose:
- Uses FlowGuard (https://github.com/liuyingxuvka/FlowGuard) to review the
  FlowPilot parallel-run runtime boundary.
- Guards against fast-restart and future multi-FlowPilot bugs where a Router
  daemon follows `.flowpilot/current.json`, writes another run, revives a
  released lock, marks background runs stale just because UI focus moved, or
  reports historical done rows as active work.
- Guards the human/bootloader invocation boundary: a fresh "start FlowPilot"
  request creates a new run even when old or parallel runs exist, while resume
  attaches to an existing run only after explicit resume intent and target
  selection.
- Future agents should update and rerun this model when changing daemon start,
  daemon tick, daemon stop, lock refresh, current/index semantics, active task
  projection, controller work-board summaries, or fresh-start/resume entry
  semantics.
- Companion command: `python simulations/run_flowpilot_parallel_run_isolation_checks.py --json`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult


@dataclass(frozen=True)
class Tick:
    """One parallel run isolation transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | complete
    run_a_exists: bool = False
    run_b_exists: bool = False
    run_c_exists: bool = False
    current_focus: str = "none"  # none | A | B | C
    daemon_a_bound: bool = False
    daemon_b_bound: bool = False
    daemon_a_tick_after_focus_change: bool = False
    daemon_a_read_current_pointer: bool = False
    daemon_a_write_target: str = "none"  # none | A | B
    daemon_b_write_target: str = "none"  # none | A | B
    writer_count_a: int = 0
    writer_count_b: int = 0
    parallel_runs_allowed: bool = False
    run_a_marked_stale_due_to_focus: bool = False
    stop_target: str = "none"  # none | A | B
    stopped_run: str = "none"  # none | A | B
    other_run_remains_active: bool = False
    lock_a_status: str = "none"  # none | active | released | terminal | error
    lock_b_status: str = "none"
    lock_a_refreshed_after_release: bool = False
    status_active_without_process: bool = False
    done_history_rows: int = 0
    active_work_rows: int = 0
    board_reports_active_work: bool = False
    current_focus_used_as_daemon_authority: bool = False
    fresh_start_requested: bool = False
    fresh_start_created_new_run: bool = False
    fresh_start_attached_existing_run: bool = False
    fresh_start_mutated_existing_run: bool = False
    current_pointer_used_as_startup_intent: bool = False
    explicit_resume_requested: bool = False
    resume_target_selected: str = "none"  # none | A | B | C
    resume_attached_target: str = "none"  # none | A | B | C
    ambiguous_resume_requested: bool = False
    ambiguous_resume_blocked_for_selection: bool = False
    ambiguous_resume_silently_chose_current: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _step(state: State, **changes: object) -> State:
    return replace(state, status="running", **changes)


class ParallelRunIsolationStep:
    """Model one parallel-run state transition.

    Input x State -> Set(Output x State)
    reads: run catalog, UI focus pointer, run-scoped daemon lock/status,
      run-scoped router_state, controller action ledger summaries, invocation
      intent
    writes: run-scoped daemon lock/status, run-scoped router_state, active task
      projection metadata, fresh run shell, resume target selection
    idempotency: daemon writes are scoped by bound run_id/run_root and lock
      identity; board projection is derived from row statuses
    """

    name = "ParallelRunIsolationStep"
    input_description = "one daemon/focus/stop/projection transition"
    output_description = "one run-isolation state transition"
    reads = ("index", "current_focus", "run_locks", "run_states", "controller_ledgers")
    writes = ("run_lock", "daemon_status", "run_state", "active_task_projection")
    idempotency = "run_id/run_root scoped"

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

    if not state.run_a_exists:
        yield Transition(
            "start_run_a_with_bound_daemon",
            _step(
                state,
                run_a_exists=True,
                current_focus="A",
                daemon_a_bound=True,
                daemon_a_write_target="A",
                writer_count_a=1,
                lock_a_status="active",
                parallel_runs_allowed=True,
            ),
        )
        return

    if not state.run_b_exists:
        yield Transition(
            "start_run_b_with_independent_daemon_and_focus",
            _step(
                state,
                run_b_exists=True,
                current_focus="B",
                daemon_b_bound=True,
                daemon_b_write_target="B",
                writer_count_b=1,
                lock_b_status="active",
                parallel_runs_allowed=True,
            ),
        )
        return

    if not state.daemon_a_tick_after_focus_change:
        yield Transition(
            "old_daemon_ticks_bound_run_after_focus_moves",
            _step(
                state,
                daemon_a_tick_after_focus_change=True,
                daemon_a_read_current_pointer=False,
                daemon_a_write_target="A",
                current_focus_used_as_daemon_authority=False,
            ),
        )
        return

    if not state.fresh_start_requested:
        yield Transition(
            "fresh_start_creates_new_run_c_despite_parallel_runs",
            _step(
                state,
                fresh_start_requested=True,
                fresh_start_created_new_run=True,
                fresh_start_attached_existing_run=False,
                fresh_start_mutated_existing_run=False,
                current_pointer_used_as_startup_intent=False,
                run_c_exists=True,
                current_focus="C",
            ),
        )
        return

    if not state.explicit_resume_requested:
        yield Transition(
            "explicit_resume_attaches_selected_run_b",
            _step(
                state,
                explicit_resume_requested=True,
                resume_target_selected="B",
                resume_attached_target="B",
            ),
        )
        return

    if not state.ambiguous_resume_requested:
        yield Transition(
            "ambiguous_resume_blocks_for_target_selection",
            _step(
                state,
                ambiguous_resume_requested=True,
                ambiguous_resume_blocked_for_selection=True,
                ambiguous_resume_silently_chose_current=False,
            ),
        )
        return

    if state.stop_target == "none":
        yield Transition(
            "targeted_stop_releases_only_run_a",
            _step(
                state,
                stop_target="A",
                stopped_run="A",
                lock_a_status="released",
                other_run_remains_active=True,
                lock_b_status="active",
            ),
        )
        return

    if state.done_history_rows == 0:
        yield Transition(
            "done_history_does_not_count_as_active_board_work",
            _step(
                state,
                done_history_rows=1,
                active_work_rows=0,
                board_reports_active_work=False,
            ),
        )
        return

    yield Transition("safe_parallel_run_isolation_complete", replace(state, status="complete"))


def next_states(state: State) -> Iterable[tuple[str, State]]:
    for transition in next_safe_states(state):
        yield transition.label, transition.state


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if (
        state.daemon_a_tick_after_focus_change
        and state.current_focus == "B"
        and state.daemon_a_read_current_pointer
    ):
        failures.append("daemon read current pointer after focus changed")
    if state.daemon_a_bound and state.daemon_a_write_target not in {"none", "A"}:
        failures.append("daemon A wrote outside its bound run")
    if state.daemon_b_bound and state.daemon_b_write_target not in {"none", "B"}:
        failures.append("daemon B wrote outside its bound run")
    if state.writer_count_a > 1 or state.writer_count_b > 1:
        failures.append("more than one daemon writer exists for one run")
    if state.run_a_exists and state.run_b_exists and not state.parallel_runs_allowed:
        failures.append("parallel runs were forced into a repository singleton")
    if state.run_a_marked_stale_due_to_focus:
        failures.append("background run was marked stale only because focus moved")
    if state.stop_target == "none" and state.stopped_run != "none":
        failures.append("daemon stop released a run without an explicit target")
    if state.stop_target == "A" and state.stopped_run == "B":
        failures.append("targeted stop released the wrong run")
    if state.stop_target == "A" and not state.other_run_remains_active and state.run_b_exists:
        failures.append("targeted stop did not preserve the other active run")
    if state.lock_a_status == "released" and state.lock_a_refreshed_after_release:
        failures.append("released daemon lock was refreshed back toward active")
    if state.status_active_without_process:
        failures.append("daemon status reported active without a live process")
    if state.done_history_rows > 0 and state.active_work_rows == 0 and state.board_reports_active_work:
        failures.append("historical done rows were reported as active board work")
    if state.current_focus_used_as_daemon_authority:
        failures.append("current focus was used as daemon authority")
    if state.fresh_start_requested and state.fresh_start_attached_existing_run:
        failures.append("fresh startup attached to an existing run")
    if state.fresh_start_requested and state.fresh_start_mutated_existing_run:
        failures.append("fresh startup mutated an existing run")
    if state.fresh_start_requested and state.current_pointer_used_as_startup_intent:
        failures.append("current pointer was used as fresh startup intent")
    if state.fresh_start_requested and not state.fresh_start_created_new_run:
        failures.append("fresh startup did not create a new run")
    if state.explicit_resume_requested and state.resume_target_selected == "none":
        failures.append("explicit resume attached without a selected target")
    if state.explicit_resume_requested and state.resume_attached_target != state.resume_target_selected:
        failures.append("explicit resume attached a run other than the selected target")
    if state.ambiguous_resume_requested and state.ambiguous_resume_silently_chose_current:
        failures.append("ambiguous resume silently chose current pointer")
    if state.ambiguous_resume_requested and not state.ambiguous_resume_blocked_for_selection:
        failures.append("ambiguous resume did not block for target selection")
    return failures


def is_terminal(state: State) -> bool:
    return state.status == "complete"


def hazard_states() -> dict[str, State]:
    safe = State(
        status="running",
        run_a_exists=True,
        run_b_exists=True,
        run_c_exists=True,
        current_focus="B",
        daemon_a_bound=True,
        daemon_b_bound=True,
        daemon_a_tick_after_focus_change=True,
        daemon_a_write_target="A",
        daemon_b_write_target="B",
        writer_count_a=1,
        writer_count_b=1,
        parallel_runs_allowed=True,
        stop_target="A",
        stopped_run="A",
        other_run_remains_active=True,
        lock_a_status="released",
        lock_b_status="active",
        done_history_rows=1,
        active_work_rows=0,
        board_reports_active_work=False,
        fresh_start_requested=True,
        fresh_start_created_new_run=True,
        explicit_resume_requested=True,
        resume_target_selected="B",
        resume_attached_target="B",
        ambiguous_resume_requested=True,
        ambiguous_resume_blocked_for_selection=True,
    )
    return {
        "daemon_reads_current_after_focus_change": replace(safe, daemon_a_read_current_pointer=True),
        "daemon_cross_writes_other_run": replace(safe, daemon_a_write_target="B"),
        "duplicate_writer_same_run": replace(safe, writer_count_a=2),
        "parallel_runs_forced_singleton": replace(safe, parallel_runs_allowed=False),
        "focus_change_marks_background_run_stale": replace(safe, run_a_marked_stale_due_to_focus=True),
        "untargeted_stop_releases_wrong_run": replace(safe, stop_target="none", stopped_run="A"),
        "targeted_stop_releases_wrong_run": replace(safe, stop_target="A", stopped_run="B"),
        "released_lock_reactivated": replace(safe, lock_a_refreshed_after_release=True),
        "active_status_without_live_process": replace(safe, status_active_without_process=True),
        "done_history_reported_as_active_work": replace(safe, board_reports_active_work=True),
        "current_focus_used_as_daemon_authority": replace(safe, current_focus_used_as_daemon_authority=True),
        "fresh_start_attaches_existing_run": replace(safe, run_c_exists=False, fresh_start_created_new_run=False, fresh_start_attached_existing_run=True),
        "fresh_start_mutates_existing_run": replace(safe, fresh_start_mutated_existing_run=True),
        "fresh_start_uses_current_pointer_as_intent": replace(safe, current_pointer_used_as_startup_intent=True),
        "fresh_start_without_new_run": replace(safe, run_c_exists=False, fresh_start_created_new_run=False),
        "explicit_resume_without_target": replace(safe, resume_target_selected="none"),
        "explicit_resume_attaches_wrong_run": replace(safe, resume_target_selected="A", resume_attached_target="B"),
        "ambiguous_resume_silently_chooses_current": replace(safe, ambiguous_resume_blocked_for_selection=False, ambiguous_resume_silently_chose_current=True),
    }
