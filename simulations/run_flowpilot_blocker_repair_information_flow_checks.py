"""Run FlowGuard checks for the FlowPilot blocker repair information-flow model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

try:  # pragma: no cover
    from . import flowpilot_blocker_repair_information_flow_model as model
except ImportError:  # pragma: no cover
    import flowpilot_blocker_repair_information_flow_model as model


RESULTS_PATH = Path(__file__).resolve().with_name(
    "flowpilot_blocker_repair_information_flow_results.json"
)

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.CURRENT_BLOCKER_PAYLOAD_MISSING_DETAILS: "current blocker payload lacks blocker id",
    model.STALE_BLOCKER_USED_FOR_PM_REPAIR: "PM repair used stale blocker payload",
    model.PM_REQUIRED_REPORT_NOT_DELIVERED: "PM repair decision was made before the required report body was delivered",
    model.REVIEWER_REQUIRED_REPAIR_DROPPED: "PM repair decision dropped the role required_repair",
    model.REVIEWER_ADVICE_NOT_INTEGRATED: "PM repair decision did not integrate reviewer repair advice",
    model.PM_REPAIR_PACKAGE_OMITS_NEW_BLOCKER_CONTENT: "PM repair package omits current blocker",
    model.WORKER_PACKET_OMITS_REPAIR_DIRECTION: "worker packet lacks concrete repair direction",
    model.WORKER_PACKET_HAS_NO_SEMANTIC_DELTA: "worker packet repeats the failed work without semantic delta",
    model.STALE_CONTEXT_COPIED_WITHOUT_DISPOSITION: "PM repair package copied stale context without disposition or quarantine",
    model.PM_CLOSES_BLOCKER_WITHOUT_RECHECK: "blocker was closed without a bound reviewer recheck pass",
    model.REVIEWER_RECHECK_NOT_BOUND_TO_BLOCKER: "reviewer recheck is not bound to the current blocker",
    model.FOLLOWUP_BLOCKER_LOST: "follow-up blocker returned by recheck was not recorded as current work",
    model.SAME_BLOCKER_REPEAT_LOOP_ALLOWED: "same blocker repeated with same work packet",
    model.NO_SUCCESS_EVIDENCE_CONTRACT: "worker packet lacks success evidence contract",
    model.BLOCKER_ROUTED_WITHOUT_PM_DECISION: "repair packet was issued without a PM repair decision",
    model.FLOWGUARD_RECHECK_EVIDENCE_NOT_DELIVERED_TO_REVIEWER: "reviewer recheck lacks the current FlowGuard evidence",
    model.REPAIR_STAGE_NOT_UPDATED_AFTER_FLOWGUARD_PASS: "blocker repair stage was not updated",
    model.FORMAL_BLOCKER_ID_ONLY_IN_PROSE_REACHES_REVIEWER: (
        "formal blocker identity missing reached Reviewer instead of Runtime reissue"
    ),
    model.FLOWGUARD_EVIDENCE_HAS_BLOCKER_BUT_STAGED_EFFECT_EMPTY: (
        "FlowGuard evidence contains blocker identity but staged_effect.blocker_id is empty"
    ),
    model.SUPERSEDED_REPAIR_BLOCKER_LEFT_OPEN: (
        "prior-route repair blocker was not dispositioned after route replacement"
    ),
    model.ACCEPTED_NONCURRENT_REPAIR_PACKET_BLOCKS_FINAL_PREFLIGHT: (
        "final preflight treated a noncurrent repair blocker as current authority"
    ),
    model.STALE_PRIOR_ROUTE_REPAIR_BLOCKER_LEFT_OPEN: (
        "prior-route repair blocker was not dispositioned after route replacement"
    ),
    model.REPAIR_LOOP_OVER_THRESHOLD_ALLOWED_PM_REPAIR: (
        "same-node repair loop threshold exceeded but ordinary PM repair continued"
    ),
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|source={state.blocker_source_role}|"
        f"blocker=current:{state.blocker_payload_current},id:{state.blocker_id_present},"
        f"source_ref:{state.source_result_ref_present},specific:{state.specific_failure_present},"
        f"required:{state.required_repair_present}|"
        f"pm=decision:{state.pm_repair_decision_recorded},body:{state.pm_authorized_report_delivered},"
        f"current:{state.pm_decision_references_current_blocker},required:{state.pm_decision_includes_required_repair},"
        f"advice:{state.pm_decision_integrates_reviewer_advice},new_work:{state.pm_decision_names_new_work}|"
        f"package=issued:{state.pm_repair_package_issued},gen:{state.pm_package_generation_new},"
        f"current:{state.pm_package_references_current_blocker},specific:{state.pm_package_includes_specific_failure},"
        f"required:{state.pm_package_includes_required_repair},new:{state.pm_package_includes_new_work_content},"
        f"dispose_old:{state.pm_package_disposes_old_context},formal:{state.pm_package_formal_blocker_id_bound}|"
        f"worker=packet:{state.worker_packet_issued},delta:{state.worker_packet_has_semantic_delta},"
        f"success_contract:{state.worker_packet_includes_success_evidence_contract},"
        f"result_addresses:{state.worker_result_addresses_required_repair}|"
        f"flowguard=recheck:{state.flowguard_recheck_requested},"
        f"repair_ref:{state.flowguard_recheck_references_repair_result},"
        f"passed:{state.flowguard_recheck_passed},manifest:{state.flowguard_evidence_manifest_attached},"
        f"formal_blocker:{state.flowguard_evidence_formal_blocker_id_bound}|"
        f"review=recheck:{state.reviewer_recheck_requested},bound:{state.reviewer_recheck_references_current_blocker},"
        f"evidence:{state.reviewer_recheck_uses_worker_evidence},passed:{state.reviewer_recheck_passed},"
        f"flowguard_evidence:{state.reviewer_recheck_uses_flowguard_evidence},"
        f"closed:{state.blocker_closed},stage_current:{state.blocker_stage_current}|"
        f"runtime_identity_gate={state.runtime_mechanical_identity_gate_passed},"
        f"staged_effect_blocker={state.staged_effect_blocker_id_bound},"
        f"prose_only={state.blocker_identity_in_prose_only},"
        f"missing_reached_reviewer={state.formal_identity_missing_reached_reviewer}|"
        f"superseded={state.route_replacement_supersedes_prior_repair},"
        f"superseded_disposition={state.superseded_blocker_disposition_recorded},"
        f"superseded_open={state.superseded_blocker_still_repair_open}|"
        f"final_preflight={state.final_preflight_uses_current_effective_blockers},"
        f"{state.final_preflight_reports_noncurrent_repair_blocker}|"
        f"followup={state.followup_blocker_returned},{state.followup_blocker_recorded}|"
        f"loop={state.same_blocker_repeat_count},{state.same_work_packet_hash_repeated},"
        f"{state.loop_escape_recorded},{state.terminal_stop_or_route_mutation}|"
        f"repair_loop={state.same_family_repair_attempt_count}>{state.repair_loop_threshold},"
        f"evidence={state.repair_loop_threshold_evidence_visible},"
        f"breakglass={state.break_glass_duty_projected},"
        f"ordinary_pm={state.ordinary_pm_repair_continued_over_threshold},"
        f"pm_superseded={state.same_family_pm_packets_superseded}|reason={state.terminal_reason}"
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
        state_failures = model.information_flow_failures(state)
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
    result = {
        "result_type": "flowpilot_blocker_repair_information_flow_checks",
        "model_id": model.MODEL_ID,
        "ok": safe_graph["ok"] and progress["ok"] and flowguard["ok"] and hazards["ok"],
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": flowguard,
        "hazard_detection": hazards,
        "claim_boundary": {
            "covers": [
                "blocker payload currency",
                "PM repair decision delivered-body and current-blocker references",
                "reviewer required repair and advice propagation",
                "fresh PM repair package generation",
                "worker repair packet semantic delta and success evidence",
                "FlowGuard recheck evidence attachment for repaired results",
                "Runtime mechanical blocker identity gate before reviewer review",
                "formal blocker identity in PM package, staged_effect, FlowGuard evidence, and replay inputs",
                "reviewer recheck binding",
                "superseded repair blocker disposition after route replacement",
                "stale prior-route repair blocker disposition after route mutation",
                "final preflight current-effective blocker filtering",
                "same-blocker no-progress loop escape",
                "same-family repair attempts above five route to Controller break-glass instead of ordinary PM repair",
            ],
            "does_not_cover": [
                "concrete runtime packet builder conformance",
                "prompt-card wording conformance",
                "installed skill synchronization",
            ],
        },
    }
    return result


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
