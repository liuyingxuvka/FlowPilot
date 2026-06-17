"""Run checks for the FlowPilot project-control information-flow parent model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

try:  # pragma: no cover
    from . import flowpilot_project_control_information_flow_model as model
except ImportError:  # pragma: no cover
    import flowpilot_project_control_information_flow_model as model


RESULTS_PATH = Path(__file__).resolve().with_name(
    "flowpilot_project_control_information_flow_results.json"
)

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.RESUME_FROM_CHAT_HISTORY_LOSES_BLOCKER: "current run, frontier, and packet ledger were not loaded",
    model.RESUME_LOADS_OLD_RUN_AS_CURRENT: "historical state or evidence was promoted to current authority",
    model.REOPEN_REUSES_OLD_AGENT_IDS_AS_CURRENT: "role assignment lacks requested role",
    model.PM_RUNWAY_OMITS_ACTIVE_BLOCKER: "PM runway lacks current state, active blocker",
    model.WORK_PACKET_LACKS_MINIMUM_INFORMATION: "work packet lacks minimum executable information",
    model.SAME_WORK_REPEATED_WITH_NO_NEW_INFO: "work packet has no new information delta",
    model.BREAK_GLASS_WITHOUT_NORMAL_REPAIR_FAILURE: "break-glass used before normal PM/control-blocker repair was proven blocked",
    model.BREAK_GLASS_UNBOUNDED_OR_TARGET_PROJECT_REPAIR: "break-glass attempted target-project repair",
    model.BREAK_GLASS_BYPASSES_PM_REVIEWER_REINTEGRATION: "break-glass did not reintegrate through PM/reviewer validation",
    model.ROUTE_MUTATION_OMITS_BLOCKER_OR_ACCEPTANCE_PLAN: "route mutation lacks blocker context",
    model.ROUTE_MUTATION_DOES_NOT_INVALIDATE_STALE_EVIDENCE: "route mutation lacks blocker context",
    model.ROLE_ASSIGNMENT_WITHOUT_CURRENT_PACKET_CONTEXT: "role assignment lacks requested role",
    model.FOLLOWUP_BLOCKER_NOT_PROPAGATED_TO_NEXT_RUNWAY: "follow-up blocker did not propagate",
    model.FINAL_CLOSURE_WITH_UNRESOLVED_INFORMATION_GAP: "closure was claimed with unresolved information gap",
    model.HISTORICAL_EVIDENCE_PROMOTED_TO_CURRENT: "historical state or evidence was promoted to current authority",
    model.PACKET_RESULT_CONTRACT_NOT_VISIBLE_TO_ROLE: "role-visible result output contract",
    model.FLOWGUARD_EVIDENCE_NOT_BOUND_TO_REVIEWER: "FlowGuard evidence handoff lacks current subject result",
    model.BLOCKER_REPAIR_STAGE_HIDDEN_FROM_STATUS: "blocker repair chain stage is hidden",
    model.SYNTHETIC_TRACE_BYPASSES_VISIBLE_CONTRACT: "synthetic trace used hidden success contract",
    model.WORK_PACKET_MISSING_INPUT_MATERIALS: "required input material manifest",
    model.WORK_PACKET_MISSING_REPORT_REQUIREMENTS: "required report contract",
    model.DOWNSTREAM_REPORT_NOT_AUTHORIZED: "downstream packet is not authorized",
    model.MISSING_INFO_RESPONSE_NOT_DEFINED: "does not define the current-runtime response",
    model.BRANCH_CONTRACT_SHAPE_NOT_VISIBLE: "branch-specific current result shapes",
    model.FINAL_PREFLIGHT_PROMOTES_NONCURRENT_REPAIR_BLOCKER: (
        "final preflight promoted a noncurrent repair blocker to current authority"
    ),
    model.ROUTE_MUTATION_LEAVES_STALE_PRIOR_ROUTE_REPAIR_BLOCKER: (
        "route mutation left stale prior-route repair blockers as current work"
    ),
    model.REPAIR_LOOP_OVER_THRESHOLD_ISSUES_PM_PACKET: (
        "same-node consecutive repair loop threshold exceeded but ordinary PM repair continued"
    ),
    model.RUN_LEDGER_PARTIAL_READ_ACCEPTED_AS_DEFAULT: (
        "run ledger persistence accepted partial JSON or synthesized fallback state"
    ),
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|surface={state.surface}|"
        f"current={state.current_run_loaded},{state.active_run_id_current},"
        f"{state.frontier_loaded},{state.packet_ledger_loaded},blocker={state.active_blocker_loaded},"
        f"packet_ctx={state.current_packet_context_loaded},role_assignment={state.role_assignment_current_or_replaced}|"
        f"history={state.historical_state_imported_as_history_only},{state.old_evidence_marked_historical},"
        f"used_current={state.historical_evidence_used_as_current}|"
        f"pm={state.pm_runway_recorded},{state.pm_runway_references_current_state},"
        f"{state.pm_runway_includes_active_blocker},{state.pm_runway_names_next_owner},"
        f"{state.pm_runway_names_next_command_or_packet}|"
        f"work={state.work_packet_issued},{state.work_packet_current_generation},"
        f"{state.work_packet_names_owner},{state.work_packet_names_objective},"
        f"{state.work_packet_carries_current_blocker},{state.work_packet_carries_new_repair_direction},"
        f"{state.work_packet_carries_allowed_reads_writes},{state.work_packet_carries_forbidden_actions},"
        f"{state.work_packet_carries_success_evidence},{state.work_packet_disposes_stale_context},"
        f"contract={state.work_packet_carries_output_contract},"
        f"{state.work_packet_carries_minimal_valid_result_shape},"
        f"{state.work_packet_carries_forbidden_result_fields},"
        f"materials={state.work_packet_carries_input_material_manifest},"
        f"report={state.work_packet_carries_required_report_contract},"
        f"branch_shapes={state.work_packet_carries_branch_valid_shapes},"
        f"consumer={state.work_packet_names_downstream_consumer},"
        f"missing_info={state.work_packet_names_missing_info_response},"
        f"submitted={state.result_report_submitted},"
        f"satisfies={state.result_report_satisfies_required_contract},"
        f"authorized_report={state.downstream_packet_authorized_to_read_report},"
        f"delta={state.new_information_delta_present},hidden_contract={state.synthetic_trace_uses_hidden_contract}|"
        f"flowguard_review={state.flowguard_gate_required},{state.flowguard_result_current_for_subject},"
        f"{state.flowguard_evidence_manifest_attached},{state.flowguard_evidence_subject_matches_result},"
        f"reviewer={state.reviewer_packet_issued},{state.reviewer_packet_authorized_to_read_subject_result},"
        f"{state.reviewer_packet_authorized_to_read_flowguard_evidence},"
        f"{state.reviewer_packet_names_flowguard_evidence_id}|"
        f"blocker_stage={state.blocker_repair_chain_open},{state.blocker_status_reflects_current_stage},"
        f"{state.status_projection_shows_repair_chain},"
        f"final_preflight={state.final_preflight_uses_current_effective_blockers},"
        f"{state.final_preflight_reports_noncurrent_repair_blocker},"
        f"stale_prior_route_superseded={state.stale_prior_route_repair_blockers_superseded}|"
        f"repair_loop={state.repair_loop_attempt_count}>{state.repair_loop_threshold},"
        f"evidence={state.repair_loop_threshold_evidence_visible},"
        f"breakglass_duty={state.break_glass_duty_projected},"
        f"ordinary_pm_over_threshold={state.ordinary_pm_repair_packet_issued_over_threshold},"
        f"pm_superseded={state.same_family_pm_packets_superseded}|"
        f"breakglass={state.break_glass_used},{state.normal_repair_path_failed},"
        f"{state.break_glass_bounded_reads_writes},{state.break_glass_control_plane_only},"
        f"{state.break_glass_target_project_repair},{state.break_glass_reenters_normal_flow}|"
        f"route={state.route_mutation_used},{state.route_mutation_references_blocker},"
        f"{state.route_version_advanced},{state.stale_evidence_invalidated},"
        f"{state.replacement_acceptance_plan_created},{state.replay_scope_declared}|"
        f"role={state.role_assignment_used},{state.requested_role_known},"
        f"{state.assigned_role_bound_to_current_task},{state.old_agent_id_treated_as_current}|"
        f"followup={state.followup_blocker_returned},{state.followup_blocker_recorded},"
        f"{state.followup_blocker_in_next_runway}|closure={state.closure_claimed},"
        f"gap={state.unresolved_information_gap_present}|reason={state.terminal_reason}"
    )


def _build_graph() -> dict[str, Any]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states: list[model.State] = [initial]
    index = {initial: 0}
    edges: list[list[tuple[str, int]]] = []
    labels: set[str] = set()
    invariant_failures: list[dict[str, Any]] = []

    while queue:
        state = queue.popleft()
        source = index[state]
        while len(edges) <= source:
            edges.append([])
        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})
        for label, next_state in model.next_states(state):
            labels.add(label)
            if next_state not in index:
                index[next_state] = len(states)
                states.append(next_state)
                queue.append(next_state)
            edges[source].append((label, index[next_state]))
    return {
        "states": states,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _safe_graph_report(graph: dict[str, Any]) -> dict[str, Any]:
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
        "invariant_failures": graph["invariant_failures"][:10],
    }


def _progress_report(graph: dict[str, Any]) -> dict[str, Any]:
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
    stuck = [_state_id(state) for idx, state in enumerate(states) if idx not in terminal and not edges[idx]]
    cannot_reach_terminal = [_state_id(state) for idx, state in enumerate(states) if idx not in can_reach_terminal]
    return {
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_terminal,
        "terminal_state_count": len(terminal),
        "stuck_state_count": len(stuck),
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "samples": (stuck + cannot_reach_terminal)[:5],
    }


def _flowguard_report() -> dict[str, Any]:
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


def _hazard_report() -> dict[str, Any]:
    hazards: dict[str, Any] = {}
    failures: list[str] = []
    for name, state in model.hazard_states().items():
        state_failures = model.information_sufficiency_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in state_failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": state_failures,
        }
        if not detected:
            failures.append(f"{name}: expected failure containing {expected!r}")
    return {"ok": not failures, "hazards": hazards, "failures": failures}


def run_checks() -> dict[str, Any]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    flowguard = _flowguard_report()
    hazards = _hazard_report()
    return {
        "result_type": "flowpilot_project_control_information_flow_checks",
        "model_id": model.MODEL_ID,
        "ok": safe_graph["ok"] and progress["ok"] and flowguard["ok"] and hazards["ok"],
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": flowguard,
        "hazard_detection": hazards,
        "coverage_matrix": {
            "ordinary_repair_packet": "covered_by_parent_and_child_blocker_repair_information_flow_model",
            "repair_loop_threshold": "same-family attempt count above five requires visible evidence and Controller break-glass duty",
            "interrupt_resume": "current run/frontier/ledger/blocker/PM runway required",
            "reopen_continuation": "history import must remain historical; current run and current role assignment required",
            "break_glass": "normal repair failure, bounded control-plane repair, PM/reviewer reintegration required",
            "route_mutation": "blocker context, new route version, stale evidence invalidation, acceptance plan, replay scope required",
            "role_assignment": "requested role, current packet context, and current-task binding required",
            "closure_or_stop": "unresolved information gaps block closure; terminal stop preserves unresolved work",
        },
        "claim_boundary": {
            "covers": [
                "parent information sufficiency across major FlowPilot control surfaces",
                "stale historical evidence rejection",
                "same-work/no-new-information loop rejection",
                "same-family repair loop threshold to Controller break-glass duty",
                "break-glass reintegration requirements",
                "route mutation information and replay requirements",
                "stale prior-route repair blocker supersession after route mutation",
                "final preflight noncurrent repair blocker rejection",
                "actor input material manifest requirements",
                "required report contract and downstream consumer authorization",
                "missing-information response definition",
                "role-visible packet result output contracts",
                "FlowGuard evidence manifest handoff into reviewer packets",
                "repair-chain status projection visibility",
            ],
            "does_not_cover": [
                "full concrete runtime conformance for every packet builder",
                "all prompt/card wording checks",
                "release or install synchronization",
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--no-write-results", action="store_true")
    args = parser.parse_args()

    result = run_checks()
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(output, end="")
    if not args.no_write_results:
        args.json_out.write_text(output, encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
