"""Run checks for the FlowPilot planning-quality model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

import flowpilot_planning_quality_model as model


RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_planning_quality_results.json")

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.VALID_SIMPLE_ROUTE: "small/simple task entered formal FlowPilot instead of staying outside FlowPilot",
    model.UI_WITHOUT_PROFILE: "complex task route lacks a selected planning profile",
    model.PROFILE_WITHOUT_CONVERGENCE_LOOP: "interactive UI route lacks required convergence loop",
    model.SKILL_SELECTED_NO_CONTRACT: "selected child skill lacks a compiled Skill Standard Contract",
    model.SKILL_CONTRACT_MISSING_FIELDS: "Skill Standard Contract omits required fields",
    model.SKILL_CONTRACT_NOT_MAPPED: "Skill Standard Contract is not mapped through route, packet, reviewer, and artifact obligations",
    model.LOOP_VERIFY_ARTIFACT_NOT_INHERITED: "LOOP/VERIFY/ARTIFACT standards were not inherited into execution",
    model.NODE_PLAN_MISSING_PROJECTION: "node acceptance plan lacks skill-standard projection",
    model.WORK_PACKET_MISSING_PROJECTION: "work packet or result matrix lacks skill-standard projection",
    model.REVIEWER_PASSES_HARD_BLINDSPOT: "reviewer passed a residual blindspot that touches a hard requirement or required child-skill gate",
    model.OVERMERGED_COMPLEX_IMPLEMENTATION_NODE: "route complexity does not match selected planning profile",
    model.ARTIFACTLESS_MAJOR_NODE: "major route node lacks a concrete acceptance artifact",
    model.SIMPLE_TASK_OVERTEMPLATED: "small/simple task entered formal FlowPilot instead of staying outside FlowPilot",
    model.PRODUCT_MODEL_MISSING: "route planning lacks a product behavior model from the FlowGuard operator product-scope",
    model.PM_ROUTE_NOT_MAPPED_TO_PRODUCT_MODEL: "PM route is not mapped to the product behavior model",
    model.PROCESS_FLOWGUARD_OPERATOR_ROUTE_VIABILITY_MISSING: "FlowGuard operator route-scope did not validate route viability against the product model",
    model.REPAIR_NODE_NO_MAINLINE_RETURN: "repair node lacks a defined return to the mainline product route",
    model.NODE_PLAN_NOT_MAPPED_TO_PRODUCT_MODEL: "node acceptance plan is not mapped to a product model segment",
    model.PM_USER_INTENT_SELF_CHECK_MISSING: "PM plan lacks final-user intent and product usefulness self-check",
    model.PM_HIGHER_STANDARD_SELF_CHECK_MISSING: "PM plan lacks higher-standard improvement-space self-check",
    model.PM_IMPROVEMENT_OPPORTUNITY_UNCLASSIFIED: "PM left higher-standard improvement opportunity unclassified",
    model.PM_IMPROVEMENT_SCOPE_CREEP: "PM treated a nonblocking higher-standard improvement as a hard current-gate requirement",
    model.PM_CLOSURE_USER_OUTCOME_REPLAY_MISSING: "PM closure lacks final-user outcome replay",
    model.PM_LOW_QUALITY_REVIEW_MISSING: "PM product architecture lacks low-quality-success review",
    model.PM_LOW_QUALITY_REVIEW_GENERIC: "PM low-quality-success review is generic or lacks hard parts, thin shortcuts, and proof of depth",
    model.HARD_LOW_QUALITY_RISK_NO_ROUTE_OWNER: "hard low-quality-success risk lacks an existing route or node owner",
    model.LOW_QUALITY_RISK_CAUSES_ROUTE_BLOAT: "PM created unjustified route bloat from low-quality-success review",
    model.PM_SHALLOW_COMPLETION_TRAPS_MISSING: "PM did not name the task-specific shallow-completion traps",
    model.PRACTICAL_OUTCOME_DESIGN_ONLY_ROUTE: "practical user outcome was planned as a design-only route without next-step evidence",
    model.NODE_PLAN_MISSING_LOW_QUALITY_MAPPING: "node acceptance plan lacks local low-quality-success mapping and proof of depth",
    model.NODE_PLAN_MISSING_CURRENT_CHECK_SURFACE: "node acceptance plan lacks current executable check surface, status vocabulary, expected failure shape, or bounded worker outcome",
    model.WORK_PACKET_MISSING_LOW_QUALITY_WARNING: "work packet lacks node low-quality-success warning",
    model.WORKER_PACKET_MISSING_IN_SCOPE_REPAIR: "executable worker packet lacks in-scope quality repair obligation",
    model.WORKER_PACKET_REPAIRS_OUT_OF_SCOPE: "worker packet does not escalate out-of-scope defects to PM",
    model.EVIDENCE_PACKET_REPAIRS_TARGET_ARTIFACT: "research or evidence-work packet grants target artifact repair instead of report self-correction",
    model.FLOWGUARD_OPERATOR_PACKET_REPAIRS_TARGET_ARTIFACT: "FlowGuard operator packet grants target artifact repair instead of model/report self-correction",
    model.REVIEWER_PROMPT_GRANTS_DIRECT_REPAIR: "reviewer prompt grants direct repair authority over the reviewed artifact",
    model.GENERIC_TEMPLATE_USES_BLANKET_REPAIR: "generic packet template uses blanket repair wording instead of role-scoped authority",
    model.PM_STRUCTURE_CONVERGENCE_REVIEW_MISSING: "PM route lacks structural convergence review for cleanup targets and owned current-runtime recovery",
    model.NODE_PLAN_MISSING_STRUCTURE_HYGIENE_EXPECTATION: "node acceptance plan lacks structure hygiene expectation",
    model.WORK_PACKET_MISSING_STRUCTURE_HYGIENE_DELTA: "work packet lacks structure hygiene delta obligation",
    model.WORKER_RESULT_LEAVES_UNOWNED_FALLBACK: "worker result retained an unowned fallback or compatibility path",
    model.REPAIR_LEAVES_COMPAT_BRANCH: "repair path retained a compatibility branch instead of reissuing or blocking current structured work",
    model.FINAL_LEDGER_STRUCTURE_DEBT_UNRESOLVED: "final ledger leaves structural debt unresolved",
    model.PM_CLOSURE_LOW_QUALITY_RISK_DISPOSITION_MISSING: "PM closure lacks low-quality-success risk disposition",
    model.PM_CLOSURE_SHALLOW_COMPLETION_TRAPS_UNRESOLVED: "PM closure leaves shallow-completion traps unresolved for the final user",
    model.PROCESS_SUPPORT_SKILL_IGNORED: "PM child-skill selection did not evaluate process-support skill candidates",
    model.ROLE_SKILL_BINDING_MISSING: "selected process-support skill lacks role-skill binding, evidence requirement, or reviewer check",
    model.ROLE_SKILL_USE_SELF_ATTESTED: "selected role skill use was self-attested without evidence",
    model.PM_IMPLEMENTATION_INTENT_MISSING: "PM implementation intent bridge is missing or too thin before route skeleton",
    model.TARGET_REALIZATION_MODEL_MISSING: "FlowGuard target-realization model is missing before route skeleton",
    model.TARGET_REALIZATION_MODEL_IGNORES_PM_INTENT: "target-realization model does not preserve PM implementation intent",
    model.PM_TARGET_REALIZATION_ACCEPTS_DOWNGRADE: "PM accepted a target-realization model that downgrades implementation intent",
    model.REVIEWER_IMPLEMENTATION_INTENT_ALIGNMENT_MISSING: "Reviewer did not check implementation-intent and target-realization alignment",
    model.ROUTE_MISSING_REALIZATION_OBLIGATIONS: "route skeleton does not consume target-realization obligations",
    model.NODE_PLAN_MISSING_REALIZATION_OBLIGATIONS: "node acceptance plan does not consume target-realization obligations",
    model.WORK_PACKET_MISSING_REALIZATION_OBLIGATIONS: "work packet does not carry target-realization obligations",
    model.FINAL_LEDGER_REALIZATION_OBLIGATIONS_UNRESOLVED: "final ledger or closure leaves target-realization obligations unresolved",
    model.ACCEPTANCE_ITEM_REGISTRY_MISSING: "PM high-standard contract lacks acceptance item registry with user and PM high-standard items",
    model.ACCEPTANCE_ITEM_NO_ROUTE_OWNER: "active acceptance item lacks a route node owner",
    model.NODE_PLAN_MISSING_ACCEPTANCE_ITEM_PROJECTION: "node acceptance plan lacks acceptance item projection",
    model.WORK_PACKET_MISSING_ACCEPTANCE_ITEM_MATRIX: "work packet or result lacks acceptance item result matrix",
    model.FINAL_LEDGER_ACCEPTANCE_ITEM_UNRESOLVED: "final ledger or closure leaves acceptance items unresolved",
    model.STARTUP_QUALITY_POSTURE_MISSING: "startup release does not carry high-quality current-run posture into PM product and route work",
    model.PRODUCT_ARCHITECTURE_IGNORES_STARTUP_QUALITY: "product architecture does not consume startup high-quality posture",
    model.SOURCE_INTENT_COLLAPSED_TO_GENERIC_ACCEPTANCE: "PM collapsed source intent into generic acceptance instead of concrete current-run acceptance rows",
    model.ROOT_CONTRACT_ACCEPTS_GENERIC_USER_GOAL: "root contract allows generic user-goal wording instead of concrete source-intent acceptance",
    model.ROUTE_QUALITY_POSTURE_DROPPED: "route design lowered the startup/product quality floor",
    model.PACKET_QUALITY_FLOOR_DROPPED: "work packet does not preserve the current quality floor",
    model.CHILD_SKILL_THEME_ONLY_STANDARD: "selected child skill is theme-only and lacks a concrete standards-lens projection",
    model.PRODUCT_ARCHITECTURE_MISSING_SYSTEM_INTEGRATION_INTENT: "PM product architecture lacks system integration intent for the whole output",
    model.ROUTE_CONVERGENCE_MISSING_COMPOSITION_REVIEW: "route structure convergence lacks parent child sibling composition review",
    model.NODE_PLAN_MISSING_INTEGRATION_TOUCHPOINT: "node acceptance plan lacks plan-level integration touchpoint",
    model.NODE_PLAN_MISSING_GLOBAL_STANDARD_REFERENCES: "node acceptance plan lacks current global standard references for backstage roles",
    model.PM_ABSORBS_LOCAL_RESULT_WITH_BROKEN_INTEGRATION: "PM absorbed current-node result without checking upstream downstream sibling and parent integration",
    model.PARENT_REPLAY_PASSES_SCATTERED_CHILD_OUTPUTS: "parent backward replay passed scattered local child outputs that do not compose into the parent goal",
    model.FINAL_LEDGER_PASSES_NODE_LEVEL_ONLY_COMPOSITION: "final ledger passed node-level completion without whole-output composition closure",
    model.SCATTERED_OUTPUT_NOT_ROUTED_TO_MODEL_MISS: "scattered local-pass global-incoherence defect class lacks model-miss triage coverage",
}


def _state_id(state: model.State) -> str:
    return f"scenario={state.scenario}|status={state.status}|task={state.task_class}|reason={state.terminal_reason}"


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
    terminal = [state for state in states if model.is_terminal(state)]
    accepted = [state for state in terminal if state.status == "accepted"]
    rejected = [state for state in terminal if state.status == "rejected"]
    missing_labels = sorted(set(REQUIRED_LABELS) - set(graph["labels"]))
    accepted_scenarios = sorted(state.scenario for state in accepted)
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and set(accepted_scenarios) == set(model.VALID_SCENARIOS)
        and len(rejected) == len(model.NEGATIVE_SCENARIOS),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "accepted_scenarios": accepted_scenarios,
        "rejected_state_count": len(rejected),
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
        "ok": not stuck and not cannot_reach_terminal,
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
        terminal_predicate=lambda _input, state, _trace: model.is_terminal(state),
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
        planning_failures = model.planning_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in planning_failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": planning_failures,
        }
        if not detected:
            failures.append(f"{name}: expected failure containing {expected!r}")
    return {"ok": not failures, "hazards": hazards, "failures": failures}


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _hazard_report()
    result = {
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
    }
    result["ok"] = all(section.get("ok", False) for section in (safe_graph, progress, explorer, hazards))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args()

    result = run_checks()
    output = json.dumps(result, indent=2, sort_keys=True)
    print(output)
    if args.json_out:
        args.json_out.write_text(output + "\n", encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
