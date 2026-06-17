"""Run checks for the FlowPilot daemon/Controller prompt-boundary model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

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
        f"lifecycle_resume={state.lifecycle_records_resume_request},{state.lifecycle_loads_current_guard},"
        f"{state.lifecycle_blocks_or_recovers_stale_duty},loop={state.lifecycle_continues_router_loop}|"
        f"unclear={state.unclear_step_rereads_daemon_and_ledger},{state.unclear_step_returns_to_router}|"
        f"rows=router_between:{state.row_to_row_uses_router_command}|"
        f"partial=wait:{state.partial_table_read_waits_next_tick},error:{state.partial_table_read_errors}|"
        f"metadata=receipt:{state.controller_row_metadata_receipt_command},"
        f"apply:{state.controller_row_metadata_apply_required},"
        f"preserve:{state.controller_row_metadata_preserves_router_apply_intent}|"
        f"startup_intake=work_board:{state.startup_intake_returns_to_work_board},"
        f"direct_apply:{state.startup_intake_direct_apply_prompt},"
        f"body_sealed:{state.startup_intake_body_sealed_from_controller}|"
        f"work_ack=receipt:{state.work_item_ack_receipt_only},"
        f"continue:{state.work_item_ack_continues_after_ack},"
        f"router_submit:{state.work_item_submission_to_router_required},"
        f"unfinished:{state.work_item_unfinished_until_router_output},"
        f"ack_completion:{state.work_item_ack_treated_as_completion}|"
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


def _source_bundle(*paths: str) -> str:
    return "\n".join(_source_text(path) for path in paths)


def _actual_prompt_source_report() -> dict[str, object]:
    skill = _source_text("skills/flowpilot/SKILL.md")
    controller = _source_text("skills/flowpilot/assets/runtime_kit/cards/roles/controller.md")
    startup_work_cards = _source_bundle(
        "skills/flowpilot/assets/runtime_kit/cards/phases/pm_startup_intake.md",
        "skills/flowpilot/assets/runtime_kit/cards/roles/project_manager.md",
        "skills/flowpilot/assets/runtime_kit/cards/roles/worker.md",
    )
    packet_body_template = _source_text("templates/flowpilot/packets/packet_body.template.md")
    packet_runtime = _source_text("skills/flowpilot/assets/packet_runtime.py")
    lifecycle_resume_prompt = _source_text(
        "skills/flowpilot/assets/runtime_kit/prompts/startup/lifecycle_resume.md"
    )
    router = _source_bundle(
        "skills/flowpilot/assets/flowpilot_router.py",
        "skills/flowpilot/assets/flowpilot_router_action_factory_envelope.py",
        "skills/flowpilot/assets/flowpilot_router_controller_reconciliation.py",
        "skills/flowpilot/assets/flowpilot_router_controller_scheduler_standby.py",
        "skills/flowpilot/assets/flowpilot_router_protocol_startup_catalog.py",
        "skills/flowpilot/assets/flowpilot_router_startup_intake_ui.py",
        "skills/flowpilot/assets/runtime_kit/prompts/cards/post_ack_policy.md",
        "skills/flowpilot/assets/runtime_kit/prompts/cards/next_step_source_policy.md",
    )
    checks: dict[str, bool] = {
        "skill_no_broad_wait_boundary_prefer_run_until_wait": (
            "After applying a wait-boundary action, prefer `run-until-wait`" not in skill
        ),
        "skill_has_only_current_start_entrypoint": (
            "Unsupported_historical equivalent:" not in skill
            and "Unsupported_historical-only alias retained for older automation" not in skill
            and "--new-invocation" not in skill
            and "run-until-wait --new-invocation" not in skill
            and "next --new-invocation" not in skill
        ),
        "skill_lifecycle_resume_no_return_to_router": (
            "record `heartbeat_or_manual_resume_requested` and return to the router" not in skill
            and "On heartbeat or manual mid-run wakeup" not in skill
        ),
        "skill_has_background_driver_bootloader_split": _contains_all(
            skill,
            (
                "Before the background driver is started or attached",
                "After the background driver startup action succeeds",
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
            (
                "diagnostic_router_reentry_policy",
                "not normal progress",
                "controller-receipt",
                "Controller action ledger",
            ),
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
        "lifecycle_resume_prompt_no_continue_router_loop": (
            "continue the router loop" not in lifecycle_resume_prompt
            and "returning to the FlowPilot router loop" not in lifecycle_resume_prompt
            and "heartbeat/manual resume" not in lifecycle_resume_prompt
            and "Every heartbeat" not in lifecycle_resume_prompt
            and "Rehydrate only" not in lifecycle_resume_prompt
        ),
        "lifecycle_resume_prompt_uses_new_runtime_guard": _contains_all(
            lifecycle_resume_prompt,
            ("flowpilot_new.py resume", "lifecycle guard", "foreground duty"),
        ),
        "controller_display_rows_use_receipt_wording": _contains_all(
            controller,
            ("display_confirmation", "controller-receipt", "receipt payload"),
        ),
        "skill_daemon_rows_distinguish_receipt_from_apply": _contains_all(
            skill,
            ("Controller ledger row", "controller-receipt", "direct pending action"),
        ),
        "skill_startup_intake_returns_to_router_work_board": _contains_all(
            skill,
            ("open_startup_intake_ui", "After the UI closes", "current lifecycle guard", "foreground duty", "Controller action ledger"),
        ),
        "skill_startup_intake_no_direct_apply_wording": (
            "After the UI closes, apply that same pending action" not in skill
        ),
        "router_startup_intake_returns_to_router_work_board": _contains_all(
            router,
            ("Open the native FlowPilot startup intake UI", "background driver status", "Controller action ledger"),
        ),
        "router_startup_intake_no_direct_apply_wording": (
            "After the UI closes, apply this pending action with only the returned startup_intake_result.result_path." not in router
        ),
        "router_startup_catalog_uses_current_receipt_repair": (
            "Unsupported_historical recovery:" not in router
            and "Unsupported_historical receipt repair" not in router
            and "Receipt repair:" in router
            and "not external recovery authority" in router
        ),
        "work_card_ack_continues_and_waits_for_router_output": _contains_all(
            startup_work_cards,
            (
                "After work-card ACK, do not stop or wait for another prompt",
                "immediately continue the assigned work",
                "task remains unfinished until the current runtime receives",
            ),
        ),
        "packet_ack_continues_and_waits_for_router_result": _contains_all(
            packet_body_template + packet_runtime,
            (
                "Packet ACK is receipt only",
                "do not stop or wait for another prompt",
                "remains unfinished until the current runtime receives",
            ),
        ),
        "router_card_checkin_policy_mentions_work_item_output": _contains_all(
            router,
            (
                "work cards that ask for an output, report, decision",
                "must not stop after ACK",
                "unfinished until the current runtime receives",
            ),
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
