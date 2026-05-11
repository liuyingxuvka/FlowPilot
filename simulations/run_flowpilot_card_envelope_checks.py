"""Run checks for the FlowPilot card envelope return-event model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from flowguard import Explorer

import flowpilot_card_envelope_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_card_envelope_results.json"


HAZARD_EXPECTED_FAILURES = {
    "legacy_delivery_treated_as_read": "legacy prompt delivery record was treated as a v2 read receipt",
    "preapply_pending_relayed_as_committed_artifact": "Controller relayed planned system-card action before committed envelope artifact existed",
    "preapply_planned_action_marked_relay_allowed": "pre-apply system-card planning action was marked relay-allowed",
    "public_apply_deliver_system_card_used": "public Controller apply attempted to deliver a relay-only system-card action",
    "legacy_return_event_field_used": "legacy return_event JSON field was still emitted",
    "missing_checkin_instruction": "card envelope omitted explicit runtime check-in instruction",
    "missing_checkin_tool_command": "card envelope omitted explicit runtime check-in instruction",
    "missing_card_ack_token": "card envelope omitted direct Router ACK token or instruction",
    "missing_direct_router_ack_instruction": "card envelope omitted direct Router ACK token or instruction",
    "direct_ack_token_requires_frontier_before_startup_frontier_exists": "direct Router ACK token required route/frontier before startup frontier exists",
    "startup_card_token_missing_frontier_optional_binding": "startup card ACK token did not allow missing route/frontier binding",
    "role_handwrites_ack_instead_of_runtime": "ack/report envelope did not match current run, role, agent, receipt refs, and relay boundary",
    "card_ack_recorded_as_external_event": "card ack was accepted as a normal external event instead of direct Router ACK",
    "card_ack_external_event_auto_rerouted": "legacy card ACK external-event entrypoint still auto-rerouted instead of hard failing",
    "card_ack_external_event_not_rejected": "legacy card ACK external-event entrypoint was not rejected",
    "check_card_return_apply_optional": "check_card_return_event changed state but was marked apply_required false",
    "missing_read_receipt": "required system card coverage passed without valid read receipt and ack/report envelope",
    "missing_ack_report": "required system card coverage passed without valid read receipt and ack/report envelope",
    "ack_without_receipt_refs": "ack/report envelope did not match current run, role, agent, receipt refs, and relay boundary",
    "ack_without_direct_router_token": "ack/report envelope did not match current run, role, agent, receipt refs, and relay boundary",
    "ack_sent_through_controller_handoff": "ack/report envelope did not match current run, role, agent, receipt refs, and relay boundary",
    "ack_contains_body_content": "ack/report envelope did not match current run, role, agent, receipt refs, and relay boundary",
    "ack_not_submitted_to_router": "ack/report envelope did not match current run, role, agent, receipt refs, and relay boundary",
    "advanced_during_missing_receipt_wait": "required system card coverage passed without valid read receipt and ack/report envelope",
    "advanced_during_missing_return_wait": "required system card coverage passed without valid read receipt and ack/report envelope",
    "pending_return_without_recovery": "pending return wait had no heartbeat/manual resume recovery action",
    "wrong_role_receipt": "card read receipt did not match current run, role, agent, hash, delivery, and I/O ack",
    "wrong_role_ack_report": "ack/report envelope did not match current run, role, agent, receipt refs, and relay boundary",
    "old_run_receipt": "card read receipt did not match current run, role, agent, hash, delivery, and I/O ack",
    "old_run_ack_report": "ack/report envelope did not match current run, role, agent, receipt refs, and relay boundary",
    "old_agent_after_replacement": "card read receipt did not match current run, role, agent, hash, delivery, and I/O ack",
    "hash_mismatch": "card read receipt did not match current run, role, agent, hash, delivery, and I/O ack",
    "receipt_before_delivery": "card read receipt did not match current run, role, agent, hash, delivery, and I/O ack",
    "resume_without_role_io_ack": "card read receipt did not match current run, role, agent, hash, delivery, and I/O ack",
    "bundle_receipt_without_per_card_refs": "bundle receipt replaced independent per-card receipts",
    "same_role_bundle_cross_role_or_run": "same-role system-card bundle crossed run, role, agent, or resume-tick boundary",
    "same_role_bundle_missing_manifest_batch": "same-role system-card bundle crossed run, role, agent, or resume-tick boundary",
    "same_role_bundle_unsafe_dependency": "same-role system-card bundle included an unsafe dependency or external boundary",
    "same_role_bundle_hides_external_boundary": "same-role system-card bundle included an unsafe dependency or external boundary",
    "same_role_bundle_missing_per_card_receipts": "same-role system-card bundle advanced without per-card receipt and bundle ACK join",
    "same_role_bundle_missing_ack_join": "same-role system-card bundle advanced without per-card receipt and bundle ACK join",
    "same_role_bundle_check_apply_optional": "same-role bundle return check was not an explicit apply-required router action",
    "same_role_bundle_incomplete_ack_missing_recovery_wait": "incomplete same-role bundle ACK did not return a same-role recovery wait",
    "same_role_bundle_incomplete_ack_advanced_without_complete_ack": "same-role bundle advanced after incomplete ACK without a completed recovery ACK",
    "preload_receipt_authorizes_work": "preload-only receipt was used as work authorization",
    "cross_role_batch_missing_dependency_graph": "cross-role batch lacked explicit dependency graph, return events, join policy, or independence proof",
    "cross_role_batch_missing_card_return_events": "cross-role batch lacked explicit dependency graph, return events, join policy, or independence proof",
    "cross_role_hidden_dependency_parallelized": "cross-role batch parallelized a hidden dependency",
    "cross_role_missing_required_join": "Router advanced before required cross-role batch ack/report and receipt joins",
    "controller_reads_card_body": "Controller read a system-card body",
    "controller_mutates_batch": "Controller changed Router-authored batch delivery",
    "read_receipt_replaces_semantic_gate": "system-card read receipt replaced semantic PM/reviewer/officer judgement",
    "stale_controller_ack_prompt": "stale prompt still instructed ACK return to Controller",
    "missing_role_direct_router_ack_prompt": "Router advanced without prompt coverage for direct Router ACK instructions",
    "missing_packet_direct_router_ack_prompt": "Router advanced without prompt coverage for direct Router ACK instructions",
    "missing_packet_direct_router_result_prompt": "Router advanced without prompt coverage for direct Router ACK instructions",
    "missing_controller_waits_on_router_notice_prompt": "Router advanced without prompt coverage for direct Router ACK instructions",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|steps={state.steps}|"
        f"legacy={state.legacy_prompt_delivery_recorded},{state.legacy_delivery_treated_as_read}|"
        f"io={state.resume_tick_active},{state.role_io_protocol_injected},"
        f"{state.role_io_ack_current_tick},{state.role_io_ack_current_agent}|"
        f"lifecycle={state.internal_delivery_action_exposed},{state.planned_artifact_paths_exposed},"
        f"{state.planned_action_relay_allowed},{state.router_auto_committed_internal_action},"
        f"{state.committed_artifact_exists},{state.committed_artifact_hash_verified},"
        f"{state.post_apply_envelope_issued},{state.controller_relayed_preapply_artifact},"
        f"{state.runtime_open_blocked_not_committed},{state.public_system_card_apply_used}|"
        f"delivery={state.card_envelope_issued},{state.card_delivery_recorded},"
        f"{state.card_return_event_declared},{state.checkin_instruction_declared},"
        f"{state.checkin_tool_command_declared},{state.card_ack_token_declared},"
        f"{state.direct_router_ack_instruction_declared},{state.startup_card_before_frontier},"
        f"{state.direct_ack_token_frontier_optional_when_missing},"
        f"{state.direct_ack_token_requires_frontier_before_available},"
        f"{state.pending_return_recorded}|"
        f"legacy_field={state.legacy_return_event_field_used}|"
        f"controller={state.controller_relayed_card_envelope},{state.controller_envelope_only},"
        f"read_body={state.controller_read_card_body},mutated={state.controller_mutated_batch}|"
        f"receipt={state.card_read_receipt_written},{state.receipt_current_run},"
        f"{state.receipt_current_role},{state.receipt_current_agent},"
        f"{state.receipt_hash_matches_manifest},{state.role_used_checkin_runtime}|"
        f"ack={state.ack_report_returned},{state.ack_current_run},{state.ack_current_role},"
        f"{state.ack_current_agent},{state.ack_references_read_receipts},"
        f"{state.ack_body_empty},{state.ack_direct_to_router},"
        f"{state.ack_router_token_valid},{state.ack_no_controller_handoff},"
        f"{state.handwritten_ack_attempted}|"
        f"wait={state.await_expected_return},{state.recovery_action_available},"
        f"{state.return_reminder_issued},{state.redelivery_attempt_issued}|"
        f"coverage={state.required_card_coverage_checked},{state.required_card_coverage_passed}|"
        f"same_bundle={state.same_role_bundle_used},{state.same_role_bundle_same_run_role_agent_tick},"
        f"{state.same_role_bundle_manifest_batch_checked},{state.same_role_bundle_dependencies_safe},"
        f"{state.same_role_bundle_no_external_boundary_hidden},{state.same_role_bundle_per_card_receipts_joined},"
        f"{state.same_role_bundle_ack_joined},{state.same_role_bundle_check_apply_required},"
        f"{state.same_role_bundle_incomplete_ack_detected},{state.same_role_bundle_recovery_wait_returned},"
        f"{state.same_role_bundle_recovered_after_complete_ack}|"
        f"batch={state.cross_role_batch_used},{state.batch_dependency_graph_declared},"
        f"{state.batch_card_return_events_declared},{state.batch_join_policy_declared},"
        f"{state.all_required_batch_receipts_joined},{state.all_required_batch_ack_reports_joined}|"
        f"ack_control={state.card_ack_sent_to_external_event_entrypoint},"
        f"{state.card_ack_external_event_auto_rerouted},"
        f"{state.card_ack_external_event_rejected},{state.card_ack_recorded_as_external_event},"
        f"{state.check_card_return_apply_required}|"
        f"prompt_ack={state.prompt_ack_coverage_checked},{state.prompt_ack_coverage_passed},"
        f"{state.stale_controller_ack_prompt_present},"
        f"{state.role_direct_router_ack_prompt_present},"
        f"{state.packet_direct_router_ack_prompt_present},"
        f"{state.packet_direct_router_result_prompt_present},"
        f"{state.controller_waits_on_router_notice_prompt_present}|"
        f"advanced={state.router_advanced}"
    )


def _build_graph() -> dict[str, object]:
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


def _safe_graph_report(graph: dict[str, object]) -> dict[str, object]:
    labels = set(graph["labels"])
    states: list[model.State] = graph["states"]
    terminals = [state for state in states if model.is_terminal(state)]
    success = [state for state in terminals if model.is_success(state)]
    missing_labels = sorted(set(model.REQUIRED_LABELS) - labels)
    return {
        "ok": not graph["invariant_failures"] and not missing_labels and bool(success),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "terminal_state_count": len(terminals),
        "success_state_count": len(success),
        "missing_labels": missing_labels,
        "invariant_failure_count": len(graph["invariant_failures"]),
        "invariant_failures": graph["invariant_failures"][:10],
    }


def _progress_report(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for idx, outgoing in enumerate(edges):
            if idx not in can_reach_terminal and any(target in can_reach_terminal for _label, target in outgoing):
                can_reach_terminal.add(idx)
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
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_terminal,
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "cannot_reach_terminal_samples": cannot_reach_terminal[:10],
    }


def _scenario_report() -> dict[str, object]:
    legacy = model.legacy_prompt_delivery_state()
    legacy_expected_bad = model.legacy_expected_bad_state()
    target = model.target_v2_state()
    legacy_failures = model.invariant_failures(legacy)
    legacy_bad_failures = model.invariant_failures(legacy_expected_bad)
    target_failures = model.invariant_failures(target)
    expected_legacy_bad = HAZARD_EXPECTED_FAILURES["legacy_delivery_treated_as_read"]
    return {
        "ok": (
            not legacy_failures
            and any(expected_legacy_bad in failure for failure in legacy_bad_failures)
            and not target_failures
        ),
        "legacy_v1_old_rules": {
            "ok": not legacy_failures,
            "interpretation": "legacy delivery can exist as history, but it does not authorize v2 advancement",
            "failures": legacy_failures,
        },
        "legacy_v1_under_v2_rules": {
            "ok": any(expected_legacy_bad in failure for failure in legacy_bad_failures),
            "expected_failure": expected_legacy_bad,
            "failures": legacy_bad_failures,
        },
        "target_v2_card_return_event_loop": {
            "ok": not target_failures,
            "interpretation": "envelope, runtime receipt, direct Router ACK/report envelope, prompt coverage, receipt coverage, guarded same-role bundle, cross-role join, and PM gate all hold",
            "failures": target_failures,
        },
    }


def _check_hazards() -> dict[str, object]:
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


def _run_flowguard_explorer() -> dict[str, object]:
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


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    scenarios = _scenario_report()
    hazards = _check_hazards()
    explorer = _run_flowguard_explorer()
    ok = bool(
        safe_graph["ok"]
        and progress["ok"]
        and scenarios["ok"]
        and hazards["ok"]
        and explorer["ok"]
    )
    return {
        "ok": ok,
        "model": "flowpilot_card_envelope",
        "safe_graph": safe_graph,
        "progress": progress,
        "scenario_checks": scenarios,
        "hazard_detection": hazards,
        "flowguard_explorer": explorer,
        "model_boundary": (
            "focused card-envelope and return-event control plane; semantic "
            "understanding of card/report bodies remains out of scope"
        ),
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    report = run_checks()
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if not args.no_write:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
