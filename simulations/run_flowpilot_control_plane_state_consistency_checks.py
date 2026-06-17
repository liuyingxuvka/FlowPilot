"""Run checks for the FlowPilot control-plane state consistency model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

import flowpilot_control_plane_state_consistency_model as model


RESULTS_PATH = Path(__file__).resolve().with_name(
    "flowpilot_control_plane_state_consistency_results.json"
)

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.OBSERVED_RECEIPT_FLAG_WITHOUT_BATCH_LIFECYCLE: (
        "receipt flag says material results relayed but durable batch lifecycle was not advanced"
    ),
    model.OBSERVED_SUPERSEDED_OLD_REQUEST_STILL_OPEN: (
        "superseding PM role-work request did not terminalize the old request"
    ),
    model.OBSERVED_UNRELAYED_OLD_REQUEST_BLOCKS_REPLACEMENT: (
        "unrelayed Controller-held old request was treated as target role busy"
    ),
    model.DAEMON_STALE_SNAPSHOT_ERASES_FOREGROUND_EVENT: (
        "daemon stale snapshot save erased newer foreground evidence"
    ),
    model.REMINDER_RECREATED_AFTER_PENDING_WAIT_LOSS: (
        "wait reminder duplicate was materialized because wait identity or cooldown was not durable"
    ),
    model.RESULT_BODY_SELF_CHECK_NOT_PROJECTED: (
        "result body self-check section was not projected into envelope metadata"
    ),
    model.MATERIAL_REVIEW_EVENT_LEFT_ONLY_IN_ROLE_OUTPUT_LEDGER: (
        "direct role-output event stayed in role output ledger without canonical Router event"
    ),
    model.DONE_WAIT_ROW_STILL_AUTHORIZES_PENDING_ACTION: (
        "pending_action was not validated against resolved Controller or scheduler wait rows"
    ),
    model.RECONCILED_WAIT_STILL_GENERATES_REMINDER: (
        "wait reminder was created for an already reconciled wait row"
    ),
    model.RECEIPT_ONLY_FIX_LEAVES_ROLE_WORK_DEADLOCK: (
        "superseding PM role-work request did not terminalize the old request"
    ),
    model.SUPERSEDE_ONLY_FIX_LEAVES_PROJECTION_DRIFT: (
        "receipt flag says material results relayed but durable batch lifecycle was not advanced"
    ),
    model.CASE_PATCHES_CLAIM_ROOT_FIX_WITHOUT_RECONCILER: (
        "root fix was claimed without a shared durable reconciliation barrier before next action"
    ),
    model.ROOT_FIX_WITHOUT_ROLE_OUTPUT_EVENT_RECONCILER: (
        "root fix was claimed without generic role-output event reconciliation"
    ),
    model.NO_CAS_FIX_LOSES_FOREGROUND_EVENT: (
        "daemon stale snapshot save erased newer foreground evidence"
    ),
    model.OBSERVED_RESEARCH_BATCH_JOINED_WITHOUT_RETURN_EVENT: (
        "research batch results_joined did not synthesize worker_research_report_returned"
    ),
    model.REMINDER_SENT_AFTER_RESEARCH_BATCH_JOINED: (
        "wait reminder was created after joined packet batch result already satisfied the wait"
    ),
    model.DAEMON_RECOVERY_USES_MUTABLE_SOURCE_PROMPT: (
        "daemon recovery read mutable source prompt instead of active run runtime_kit"
    ),
    model.GLOBAL_STOP_CLAIM_WITH_ACTIVE_HOST_AUTOMATIONS: (
        "global host stop was claimed while unrelated host automations remained active"
    ),
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|"
        f"receipt={state.controller_receipt_done},{state.receipt_postcondition_flag},"
        f"{state.material_results_joined},{state.durable_batch_status},"
        f"{state.router_projection_batch_status}|"
        f"pm_disposition={state.pm_disposition_attempted},{state.pm_disposition_accepted}|"
        f"supersede={state.supersedes_declared},{state.old_request_status},"
        f"{state.old_request_in_active_index},{state.new_request_status}|"
        f"holder={state.old_packet_holder},{state.old_packet_relayed_to_target}|"
        f"gate={state.candidate_replacement_request},{state.gate_treats_target_busy},"
        f"{state.gate_exposes_replacement_dispatch},{state.control_blocker_exposed}|"
        f"daemon={state.foreground_event_version},{state.daemon_snapshot_version},"
        f"{state.daemon_merge_before_save},{state.daemon_save_preserves_foreground_event}|"
        f"reminder={state.wait_identity_stable},{state.reminder_last_sent_persisted},"
        f"{state.reminder_cooldown_enforced},{state.duplicate_reminder_materialized}|"
        f"selfcheck={state.body_self_check_heading_level},"
        f"{state.envelope_self_check_completed},{state.envelope_self_check_passed}|"
        f"role_output_event={state.direct_role_output_event_submitted},"
        f"{state.role_output_event_type},{state.generic_role_output_event_reconciler},"
        f"{state.role_output_event_folded_to_router_state},{state.router_event_flag_synced},"
        f"{state.material_review_projection_synced},"
        f"{state.material_insufficient_pm_repair_branch_exposed}|"
        f"packet_batch={state.packet_batch_family},{state.packet_batch_results_joined},"
        f"{state.packet_batch_all_results_returned},{state.packet_batch_missing_roles},"
        f"{state.packet_batch_next_recipient},{state.packet_batch_reconciler_covers_family},"
        f"{state.worker_result_return_event_recorded},{state.packet_batch_result_relayed_to_pm}|"
        f"wait_rows={state.controller_wait_row_status},{state.scheduler_wait_row_status},"
        f"{state.pending_action_references_wait},"
        f"{state.pending_action_validated_against_wait_ledgers},"
        f"{state.pending_action_cleared_after_wait_resolution},"
        f"{state.current_work_from_pending_action},"
        f"{state.stale_wait_reminder_created}|"
        f"daemon_recovery={state.daemon_recovery_attempted},"
        f"{state.active_run_runtime_kit_prompt_manifest_present},"
        f"{state.source_runtime_kit_prompt_changed_after_run_start},"
        f"{state.daemon_recovery_reads_run_runtime_kit_prompt},"
        f"{state.daemon_recovery_reads_mutable_source_prompt},"
        f"{state.prompt_hash_mismatch_blocks_daemon_recovery},"
        f"{state.daemon_recovery_status_write_succeeds}|"
        f"stop={state.stop_scope},{state.flowpilot_daemon_stopped},"
        f"{state.flowpilot_heartbeat_stopped},{state.flowpilot_role_bindings_stopped},"
        f"{state.unrelated_host_automations_active},{state.global_host_cleanup_claimed}|"
        f"root={state.shared_reconcile_before_next_action},"
        f"{state.next_action_from_reconciled_state},{state.root_fix_claimed}|"
        f"reason={state.terminal_reason}"
    )


def _build_graph() -> dict[str, Any]:
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


def _safe_graph_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    terminal = [state for state in states if model.is_terminal(state)]
    accepted = sorted(state.scenario for state in terminal if state.status == "accepted")
    rejected = sorted(state.scenario for state in terminal if state.status == "rejected")
    missing_labels = sorted(set(REQUIRED_LABELS) - set(graph["labels"]))
    return {
        "ok": (
            not graph["invariant_failures"]
            and not missing_labels
            and set(accepted) == set(model.VALID_SCENARIOS)
            and set(rejected) == set(model.NEGATIVE_SCENARIOS)
        ),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "accepted_scenarios": accepted,
        "rejected_scenarios": rejected,
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"][:5],
    }


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
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_terminal,
        "stuck_state_count": len(stuck),
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "samples": (stuck + cannot_reach_terminal)[:5],
    }


def _flowguard_report() -> dict[str, object]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=model.terminal_predicate,
        success_predicate=lambda state, _trace: model.is_success(state),
        required_labels=REQUIRED_LABELS,
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
    failures: list[str] = []
    for name, state in model.hazard_states().items():
        scenario_failures = model.consistency_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in scenario_failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": scenario_failures,
            "state": state.__dict__,
        }
        if not detected:
            failures.append(f"{name}: expected failure containing {expected!r}")
    return {"ok": not failures, "hazards": hazards, "failures": failures}


def _repair_candidate_report() -> dict[str, object]:
    candidates: dict[str, object] = {}
    passing: list[str] = []
    for name, state in model.repair_candidate_states().items():
        failures = model.consistency_failures(state)
        candidates[name] = {
            "passes_model": not failures,
            "failures": failures,
            "state": state.__dict__,
        }
        if not failures:
            passing.append(name)
    return {
        "ok": passing == [
            "unified_reconciler_with_event_fold_pending_authority_cas_true_holder_batch_prompt_and_stop_scope"
        ],
        "passing_candidates": passing,
        "candidates": candidates,
    }


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _hazard_report()
    repair_candidates = _repair_candidate_report()
    return {
        "ok": (
            safe_graph["ok"]
            and progress["ok"]
            and explorer["ok"]
            and hazards["ok"]
            and repair_candidates["ok"]
        ),
        "safe_graph": safe_graph,
        "progress": progress,
        "explorer": explorer,
        "hazards": hazards,
        "repair_candidates": repair_candidates,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print the full JSON report.")
    parser.add_argument("--json-out", type=Path, help="Write the full JSON report to this path.")
    args = parser.parse_args()

    report = run_checks()
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    output_path = args.json_out or RESULTS_PATH
    output_path.write_text(payload, encoding="utf-8")

    if args.json:
        print(payload, end="")
    else:
        print(
            "flowpilot control-plane state consistency checks: "
            f"ok={report['ok']} "
            f"safe_graph={report['safe_graph']['ok']} "
            f"progress={report['progress']['ok']} "
            f"explorer={report['explorer']['ok']} "
            f"hazards={report['hazards']['ok']} "
            f"repair_candidates={report['repair_candidates']['ok']}"
        )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
