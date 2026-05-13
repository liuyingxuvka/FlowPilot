"""Run FlowGuard checks for the FlowPilot startup intake UI model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_startup_intake_ui_model as model


RESULTS_PATH = Path(__file__).resolve().parent / "flowpilot_startup_intake_ui_results.json"

HAZARD_EXPECTED_FAILURES = {
    "controller_before_ui_confirm": "Controller loaded before confirmed UI intake and PM packet",
    "cancel_continues_to_run": "UI cancel still allowed startup side effects",
    "controller_body_leak": "Controller-visible startup state leaked user request body",
    "accepted_without_hash": "startup answers accepted without complete UI receipt/envelope/body hash evidence",
    "ui_result_json_bom_breaks_router": "startup UI JSON artifacts must be UTF-8 without BOM",
    "ui_receipt_json_bom_breaks_router": "startup UI JSON artifacts must be UTF-8 without BOM",
    "ui_envelope_json_bom_breaks_router": "startup UI JSON artifacts must be UTF-8 without BOM",
    "legacy_bom_json_without_router_fallback": "Router startup intake JSON reader is not BOM-compatible",
    "body_bom_leaks_to_pm_packet": "PM intake packet leaked leading UTF-8 BOM marker",
    "bom_repair_bypasses_body_hash": "startup answers accepted without complete UI receipt/envelope/body hash evidence",
    "invalid_toggle_value": "background agent toggle did not map to a startup answer enum",
    "single_agent_starts_roles": "background agents started despite UI single-agent choice",
    "manual_creates_heartbeat": "heartbeat created despite UI manual continuation choice",
    "chat_opens_cockpit": "Cockpit opened despite UI chat display choice",
    "reviewer_uses_chat": "reviewer startup pass relied on chat instead of UI record/receipt/envelope",
    "ui_confirm_requires_old_chat": "UI-confirmed startup still required old chat answers",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|router={state.router_loaded}|ui={state.ui_opened},{state.ui_result}|"
        f"artifacts={state.receipt_written},{state.envelope_written},{state.body_written},"
        f"{state.body_path_recorded},{state.body_hash_verified}|"
        f"encoding={state.result_json_no_bom},{state.receipt_json_no_bom},{state.envelope_json_no_bom},"
        f"router_sig={state.router_json_reader_bom_tolerant},verified={state.artifact_encoding_contract_verified},"
        f"body_bom={state.body_has_leading_bom},pm_strip={state.pm_packet_body_bom_stripped}|"
        f"answers={state.startup_answers_recorded},{state.startup_answer_values_valid},"
        f"{state.background_agents},{state.scheduled_continuation},{state.display_surface}|"
        f"run={state.run_shell_created}|request_ref={state.user_request_ref_recorded}|"
        f"pm_packet={state.pm_intake_packet_created},{state.pm_is_only_body_reader}|"
        f"reviewer={state.reviewer_checked_ui_record},{state.reviewer_checked_ui_receipt},{state.reviewer_checked_envelope_hash},"
        f"chat={state.reviewer_used_chat_history},pass={state.reviewer_startup_passed}|"
        f"host={state.roles_started},{state.heartbeat_created},{state.cockpit_opened},"
        f"fallback={state.chat_display_fallback_recorded}|"
        f"controller={state.controller_core_loaded},read_body={state.controller_read_body},"
        f"leak={state.body_text_in_controller_visible_state}|old_chat={state.old_chat_answer_required}"
    )


def _build_graph() -> dict[str, object]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states: list[model.State] = [initial]
    index = {initial: 0}
    edges: list[list[tuple[str, int]]] = [[]]
    labels: set[str] = set()
    invariant_failures: list[dict[str, object]] = []

    while queue:
        state = queue.popleft()
        source = index[state]
        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})
        for transition in model.next_safe_states(state):
            labels.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(states)
                states.append(transition.state)
                edges.append([])
                queue.append(transition.state)
            edges[source].append((transition.label, index[transition.state]))

    return {
        "states": states,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _safe_graph_report(graph: dict[str, object]) -> dict[str, object]:
    labels = set(graph["labels"])
    missing_labels = sorted(set(model.REQUIRED_LABELS) - labels)
    states: list[model.State] = graph["states"]
    cancelled_with_side_effects = [
        _state_id(state)
        for state in states
        if state.ui_result == "cancelled"
        and (
            state.run_shell_created
            or state.roles_started
            or state.heartbeat_created
            or state.cockpit_opened
            or state.controller_core_loaded
        )
    ]
    return {
        "ok": (
            not graph["invariant_failures"]
            and not missing_labels
            and any(model.is_success(state) for state in states)
            and any(state.status == "cancelled" for state in states)
            and not cancelled_with_side_effects
        ),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "labels": sorted(labels),
        "missing_labels": missing_labels,
        "success_state_count": sum(1 for state in states if model.is_success(state)),
        "cancelled_state_count": sum(1 for state in states if state.status == "cancelled"),
        "cancelled_with_side_effects": cancelled_with_side_effects,
        "invariant_failures": graph["invariant_failures"],
    }


def _progress_report(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    success = {idx for idx, state in enumerate(states) if model.is_success(state)}
    can_reach_terminal = set(terminal)
    can_reach_success = set(success)
    changed = True
    while changed:
        changed = False
        for source, outgoing in enumerate(edges):
            targets = [target for _label, target in outgoing]
            if source not in can_reach_terminal and any(target in can_reach_terminal for target in targets):
                can_reach_terminal.add(source)
                changed = True
            if source not in can_reach_success and any(target in can_reach_success for target in targets):
                can_reach_success.add(source)
                changed = True
    stuck = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in terminal and not edges[idx]
    ]
    return {
        "ok": not stuck and 0 in can_reach_terminal and 0 in can_reach_success,
        "initial_can_reach_terminal": 0 in can_reach_terminal,
        "initial_can_reach_success": 0 in can_reach_success,
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
    }


def _flowguard_report() -> dict[str, object]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=lambda _input, state, _trace: model.is_terminal(state),
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


def _hazard_report() -> dict[str, object]:
    hazards: dict[str, object] = {}
    ok = True
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": failures,
            "state": state.__dict__,
        }
        ok = ok and detected
    return {"ok": ok, "hazards": hazards}


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _hazard_report()
    approved_plan_failures = model.invariant_failures(model.approved_plan_state())
    return {
        "ok": bool(safe_graph["ok"])
        and bool(progress["ok"])
        and bool(explorer["ok"])
        and bool(hazards["ok"])
        and not approved_plan_failures,
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard": explorer,
        "hazards": hazards,
        "approved_plan": {
            "ok": not approved_plan_failures,
            "failures": approved_plan_failures,
            "state": model.approved_plan_state().__dict__,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", default=str(RESULTS_PATH))
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    report = run_checks()
    if not args.no_write:
        Path(args.json_out).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
