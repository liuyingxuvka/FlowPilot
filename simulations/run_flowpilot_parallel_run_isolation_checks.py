"""Run checks for the FlowPilot parallel run isolation model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

import flowpilot_parallel_run_isolation_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_parallel_run_isolation_results.json"

REQUIRED_LABELS = (
    "start_run_a_with_bound_daemon",
    "start_run_b_with_independent_daemon_and_focus",
    "old_daemon_ticks_bound_run_after_focus_moves",
    "fresh_start_creates_new_run_c_despite_parallel_runs",
    "explicit_resume_attaches_selected_run_b",
    "ambiguous_resume_blocks_for_target_selection",
    "targeted_stop_releases_only_run_a",
    "done_history_does_not_count_as_active_board_work",
    "safe_parallel_run_isolation_complete",
)

HAZARD_EXPECTED_FAILURES = {
    "daemon_reads_current_after_focus_change": "daemon read current pointer after focus changed",
    "daemon_cross_writes_other_run": "daemon A wrote outside its bound run",
    "duplicate_writer_same_run": "more than one daemon writer exists for one run",
    "parallel_runs_forced_singleton": "parallel runs were forced into a repository singleton",
    "focus_change_marks_background_run_stale": "background run was marked stale only because focus moved",
    "untargeted_stop_releases_wrong_run": "daemon stop released a run without an explicit target",
    "targeted_stop_releases_wrong_run": "targeted stop released the wrong run",
    "released_lock_reactivated": "released daemon lock was refreshed back toward active",
    "active_status_without_live_process": "daemon status reported active without a live process",
    "done_history_reported_as_active_work": "historical done rows were reported as active board work",
    "current_focus_used_as_daemon_authority": "current focus was used as daemon authority",
    "fresh_start_attaches_existing_run": "fresh startup attached to an existing run",
    "fresh_start_mutates_existing_run": "fresh startup mutated an existing run",
    "fresh_start_uses_current_pointer_as_intent": "current pointer was used as fresh startup intent",
    "fresh_start_without_new_run": "fresh startup did not create a new run",
    "explicit_resume_without_target": "explicit resume attached without a selected target",
    "explicit_resume_attaches_wrong_run": "explicit resume attached a run other than the selected target",
    "ambiguous_resume_silently_chooses_current": "ambiguous resume silently chose current pointer",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|runs={state.run_a_exists},{state.run_b_exists},{state.run_c_exists}|"
        f"focus={state.current_focus}|bound={state.daemon_a_bound},{state.daemon_b_bound}|"
        f"tick_after_focus={state.daemon_a_tick_after_focus_change}|"
        f"reads_current={state.daemon_a_read_current_pointer}|"
        f"writes={state.daemon_a_write_target},{state.daemon_b_write_target}|"
        f"writers={state.writer_count_a},{state.writer_count_b}|"
        f"parallel={state.parallel_runs_allowed}|"
        f"stale_by_focus={state.run_a_marked_stale_due_to_focus}|"
        f"stop={state.stop_target}->{state.stopped_run},other={state.other_run_remains_active}|"
        f"locks={state.lock_a_status},{state.lock_b_status},reactivated={state.lock_a_refreshed_after_release}|"
        f"active_no_process={state.status_active_without_process}|"
        f"board=done{state.done_history_rows},active{state.active_work_rows},reported{state.board_reports_active_work}|"
        f"current_authority={state.current_focus_used_as_daemon_authority}|"
        f"fresh_start={state.fresh_start_requested},new={state.fresh_start_created_new_run},"
        f"attached_existing={state.fresh_start_attached_existing_run},"
        f"mutated_existing={state.fresh_start_mutated_existing_run},"
        f"current_as_intent={state.current_pointer_used_as_startup_intent}|"
        f"resume={state.explicit_resume_requested},target={state.resume_target_selected},"
        f"attached={state.resume_attached_target}|"
        f"ambiguous_resume={state.ambiguous_resume_requested},"
        f"blocked={state.ambiguous_resume_blocked_for_selection},"
        f"chose_current={state.ambiguous_resume_silently_chose_current}"
    )


def _build_graph() -> dict[str, Any]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states: list[model.State] = [initial]
    index = {initial: 0}
    edges: list[list[tuple[str, int]]] = []
    labels: set[str] = set()
    invariant_failures: list[dict[str, object]] = []

    while queue:
        state = queue.popleft()
        source = index[state]
        while len(edges) <= source:
            edges.append([])
        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})
        for label, new_state in model.next_states(state):
            labels.add(label)
            if new_state not in index:
                index[new_state] = len(states)
                states.append(new_state)
                queue.append(new_state)
            edges[source].append((label, index[new_state]))
    return {
        "states": states,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _safe_graph_report(graph: dict[str, Any]) -> dict[str, object]:
    labels = set(graph["labels"])
    states: list[model.State] = graph["states"]
    terminal_states = [state for state in states if model.is_terminal(state)]
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    return {
        "ok": not graph["invariant_failures"] and not missing_labels and bool(terminal_states),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "terminal_state_count": len(terminal_states),
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"],
    }


def _hazard_report() -> dict[str, object]:
    failures: dict[str, list[str]] = {}
    missing_detection: dict[str, list[str]] = {}
    for name, state in model.hazard_states().items():
        found = model.invariant_failures(state)
        failures[name] = found
        expected = HAZARD_EXPECTED_FAILURES[name]
        if expected not in found:
            missing_detection[name] = found
    return {
        "ok": not missing_detection,
        "failures": failures,
        "missing_detection": missing_detection,
    }


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe = _safe_graph_report(graph)
    hazards = _hazard_report()
    result = {
        "ok": bool(safe["ok"] and hazards["ok"]),
        "schema_version": "flowpilot.parallel_run_isolation_results.v1",
        "model": "flowpilot_parallel_run_isolation_model",
        "safe_graph": safe,
        "hazards": hazards,
        "heavy_models_skipped": {
            "meta_model": "skipped_by_user_direction",
            "capability_model": "skipped_by_user_direction",
        },
    }
    RESULTS_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run_checks()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"ok={result['ok']} states={result['safe_graph']['state_count']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
