"""Run checks for the FlowPilot daemon/Controller prompt-boundary model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_prompt_boundary_model as model


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
RESULTS_PATH = ROOT / "flowpilot_prompt_boundary_results.json"


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|daemon={state.daemon_started}|"
        f"pre_daemon={state.minimal_run_target_created},{state.pre_daemon_bootloader_manual_allowed}|"
        f"ledger={state.controller_attaches_to_daemon_status},{state.controller_reads_action_ledger},"
        f"{state.controller_writes_receipt},{state.controller_standby_when_no_row}|"
        f"router={state.router_owns_ordering_and_barriers},diag_only={state.diagnostic_router_commands_only},"
        f"metronome={state.manual_router_metronome_allowed}|"
        f"heartbeat={state.heartbeat_records_resume_event},{state.heartbeat_attaches_existing_daemon},"
        f"{state.heartbeat_repairs_stale_daemon_only},loop={state.heartbeat_continues_router_loop}|"
        f"unclear={state.unclear_step_rereads_daemon_and_ledger},{state.unclear_step_returns_to_router}|"
        f"rows=router_between:{state.row_to_row_uses_router_command}|"
        f"partial=wait:{state.partial_table_read_waits_next_tick},error:{state.partial_table_read_errors}|"
        f"metadata=receipt:{state.controller_row_metadata_receipt_command},"
        f"apply:{state.controller_row_metadata_apply_required},"
        f"preserve:{state.controller_row_metadata_preserves_router_apply_intent}|"
        f"reason={state.rejection_reason}"
    )


def _build_reachable_graph() -> dict[str, Any]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states: list[model.State] = [initial]
    index = {initial: 0}
    labels: set[str] = set()
    edges: list[list[tuple[str, int]]] = []
    invariant_failures: list[dict[str, object]] = []

    while queue:
        state = queue.popleft()
        source = index[state]
        while len(edges) <= source:
            edges.append([])

        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})

        for transition in model.next_safe_states(state):
            labels.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(states)
                states.append(transition.state)
                queue.append(transition.state)
            edges[source].append((transition.label, index[transition.state]))

    return {
        "states": states,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _safe_graph_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    missing_labels = sorted(set(model.REQUIRED_LABELS) - set(graph["labels"]))
    terminal = [state for state in states if model.is_terminal(state)]
    accepted = sorted(state.scenario for state in terminal if state.status == "accepted")
    rejected = sorted(state.scenario for state in terminal if state.status == "rejected")
    return {
        "ok": (
            not graph["invariant_failures"]
            and not missing_labels
            and accepted == sorted(model.VALID_SCENARIOS)
            and rejected == sorted(model.NEGATIVE_SCENARIOS)
        ),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "accepted_scenarios": accepted,
        "rejected_scenarios": rejected,
        "missing_labels": missing_labels,
        "invariant_failure_count": len(graph["invariant_failures"]),
        "invariant_failures": graph["invariant_failures"][:10],
    }


def _expected_rejections_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    terminal_by_scenario = {
        state.scenario: state
        for state in states
        if model.is_terminal(state) and state.scenario != "unset"
    }
    failures: list[str] = []
    results: dict[str, str] = {}
    for scenario in model.SCENARIOS:
        terminal = terminal_by_scenario.get(scenario)
        if terminal is None:
            failures.append(f"{scenario}: no terminal state")
            results[scenario] = "missing"
            continue
        if scenario in model.EXPECTED_REJECTIONS:
            expected = model.EXPECTED_REJECTIONS[scenario]
            results[scenario] = f"{terminal.status}:{terminal.rejection_reason}"
            if terminal.status != "rejected" or terminal.rejection_reason != expected:
                failures.append(f"{scenario}: expected rejected:{expected}, got {results[scenario]}")
        else:
            results[scenario] = terminal.status
            if terminal.status != "accepted":
                failures.append(f"{scenario}: expected accepted, got {terminal.status}")
    return {"ok": not failures, "results": results, "failures": failures}


def _progress_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for source, outgoing in enumerate(edges):
            if source not in can_reach_terminal and any(target in can_reach_terminal for _label, target in outgoing):
                can_reach_terminal.add(source)
                changed = True
    stuck = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in terminal and not edges[idx]
    ]
    cannot_reach_terminal = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in can_reach_terminal
    ]
    return {
        "ok": not stuck and not cannot_reach_terminal,
        "stuck_state_count": len(stuck),
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "samples": (stuck + cannot_reach_terminal)[:10],
    }


def _run_flowguard_explorer() -> dict[str, object]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=model.terminal_predicate,
        success_predicate=lambda state, _trace: model.is_success(state),
        required_labels=model.REQUIRED_LABELS,
    ).explore()
    return {
        "ok": report.ok,
        "summary": report.summary,
        "violation_count": len(report.violations),
        "dead_branch_count": len(report.dead_branches),
        "exception_branch_count": len(report.exception_branches),
        "reachability_failure_count": len(report.reachability_failures),
        "reachability_failures": [failure.message for failure in report.reachability_failures],
    }


def _contains_all(text: str, terms: tuple[str, ...]) -> bool:
    lower = text.lower()
    return all(term.lower() in lower for term in terms)


def _source_text(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def _actual_prompt_source_report() -> dict[str, object]:
    skill = _source_text("skills/flowpilot/SKILL.md")
    controller = _source_text("skills/flowpilot/assets/runtime_kit/cards/roles/controller.md")
    router = _source_text("skills/flowpilot/assets/flowpilot_router.py")
    heartbeat_template = _source_text("templates/flowpilot/heartbeats/hb.template.md")

    checks: dict[str, bool] = {
        "skill_no_broad_wait_boundary_prefer_run_until_wait": (
            "After applying a wait-boundary action, prefer `run-until-wait`" not in skill
        ),
        "skill_heartbeat_no_return_to_router": (
            "record `heartbeat_or_manual_resume_requested` and return to the router" not in skill
        ),
        "skill_has_pre_daemon_split": _contains_all(
            skill,
            (
                "Before the daemon is started or attached",
                "After `start_router_daemon` succeeds",
                "diagnostic, test, or explicit repair",
            ),
        ),
        "controller_no_unclear_return_to_router": (
            "If the next step is unclear, return to the router." not in controller
        ),
        "controller_has_reread_daemon_ledger_receipts": _contains_all(
            controller,
            ("reread daemon status", "Controller action ledger", "receipts"),
        ),
        "controller_partial_table_reads_defer": _contains_all(
            controller,
            ("valid JSON", "wait for the next daemon tick", "do not record corruption"),
        ),
        "router_table_prompt_forbids_router_commands_between_rows": _contains_all(
            router,
            ("Do not call `next`, `apply`, or `run-until-wait` between rows", "row action plus Controller receipt"),
        ),
        "router_projects_controller_rows_to_receipt_metadata": _contains_all(
            router,
            (
                "controller_completion_command",
                "controller-receipt",
                "controller_action_ledger_receipt",
                "router_pending_apply_required",
            ),
        ),
        "router_projection_disables_controller_apply_required": _contains_all(
            router,
            (
                '"apply_required": False',
                '"router_pending_apply_required"',
                '"controller_completion_mode"',
            ),
        ),
        "router_heartbeat_prompt_no_continue_router_loop": (
            "continue the router loop" not in router
            and "returning to the FlowPilot router loop" not in router
        ),
        "router_heartbeat_prompt_attaches_daemon_ledger": _contains_all(
            router,
            ("attach to daemon status", "Controller action ledger", "process only exposed Controller rows"),
        ),
        "heartbeat_template_disclaims_manual_router_loop": _contains_all(
            heartbeat_template,
            ("does not authorize a manual Router loop", "daemon status", "Controller action ledger"),
        ),
        "controller_display_rows_use_receipt_wording": _contains_all(
            controller,
            ("display_confirmation", "controller-receipt", "receipt payload"),
        ),
        "skill_daemon_rows_distinguish_receipt_from_apply": _contains_all(
            skill,
            ("Controller ledger row", "controller-receipt", "direct pending action"),
        ),
    }
    failures = [name for name, ok in checks.items() if not ok]
    return {"ok": not failures, "checks": checks, "failures": failures}


def run_checks() -> dict[str, object]:
    graph = _build_reachable_graph()
    checks = {
        "safe_graph": _safe_graph_report(graph),
        "expected_rejections": _expected_rejections_report(graph),
        "progress": _progress_report(graph),
        "flowguard_explorer": _run_flowguard_explorer(),
        "actual_prompt_sources": _actual_prompt_source_report(),
    }
    return {
        "ok": all(bool(check["ok"]) for check in checks.values()),
        "model": "flowpilot_prompt_boundary",
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", default=str(RESULTS_PATH))
    args = parser.parse_args()
    report = run_checks()
    out = Path(args.json_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
