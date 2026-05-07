"""Run checks for the FlowPilot GateDecision implementation contract model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_gate_decision_contract_model as model


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
CONTRACT_DOC = PROJECT_ROOT / "docs" / "gate_decision_implementation_contract.md"
RESULTS_PATH = ROOT / "flowpilot_gate_decision_contract_results.json"

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + ["accept_valid_gate_decision_contract"]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.MISSING_PROMPT_FIELDS: "prompt contract omitted GateDecision fields",
    model.ROUTER_MISSING_FIELDS: "router mechanical contract omitted GateDecision checks",
    model.ROUTER_SEMANTIC_OVERREACH: "router overreached into semantic gate judgment",
    model.REVIEWER_SEMANTIC_GAP: "reviewer scope omitted semantic gate sufficiency",
    model.VISUAL_FLOWGUARD_ONLY: "visual-quality GateDecision lacks reviewer walkthrough proof",
    model.PRODUCT_WITHOUT_FLOWGUARD: "product/state GateDecision lacks Product FlowGuard proof",
    model.MIXED_WITHOUT_REVIEWER: "mixed product/visual GateDecision lacks both proof paths",
    model.DOCUMENTATION_FORCED_PRODUCT_FLOWGUARD: "documentation-only GateDecision was forced through Product FlowGuard",
    model.ADVISORY_BLOCKS_COMPLETION: "advisory GateDecision blocked completion",
    model.SKIP_WITHOUT_REASON: "skip or waiver GateDecision lacked a concrete reason",
    model.LOCAL_DEFECT_FORCES_MUTATION: "local defect GateDecision forced route mutation",
    model.ROUTE_MUTATION_WITHOUT_STALE_INVALIDATION: "route mutation GateDecision did not invalidate stale evidence",
    model.LOW_RISK_PARENT_REPLAY_HARD: "parent replay GateDecision is not risk based or waivable",
    model.DIAGNOSTIC_RESOURCE_BLOCKS: "diagnostic temporary resource GateDecision blocked completion",
    model.DELIVERY_EVIDENCE_UNRESOLVED: "delivery evidence GateDecision was unresolved at completion",
    model.STAGE_ADVANCE_SPLIT_REFRESH: "stage advance GateDecision did not require atomic state refresh",
}

DOC_REQUIRED_SNIPPETS = (
    "gate_decision_version",
    "gate_id",
    "gate_kind",
    "owner_role",
    "risk_type",
    "gate_strength",
    "decision",
    "blocking",
    "required_evidence",
    "evidence_refs",
    "reason",
    "next_action",
    "Router responsibility is mechanical conformance",
    "Reviewer and PM responsibility is semantic sufficiency",
    "product_state",
    "visual_quality",
    "mixed_product_visual",
    "documentation_only",
    "repair_local",
    "mutate_route",
    "high composition risk",
    "diagnostic_temp",
    "delivery_evidence",
    "advance_stage -> refresh(frontier, display, ledger, blocker_index)",
    "Prompt/card instruction models should check",
    "Router/protocol models should check",
    "Reviewer/router scope models should check",
    "Control-plane models should check",
)


def _state_id(state: model.State) -> str:
    return f"scenario={state.scenario}|status={state.status}|reason={state.terminal_reason}"


def _build_graph() -> dict[str, Any]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    seen: list[model.State] = [initial]
    index = {initial: 0}
    edges: list[list[tuple[str, int]]] = []
    labels: set[str] = set()
    invariant_failures: list[dict[str, object]] = []

    while queue:
        state = queue.popleft()
        source_index = index[state]
        while len(edges) <= source_index:
            edges.append([])

        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})

        for transition in model.next_safe_states(state):
            labels.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(seen)
                seen.append(transition.state)
                queue.append(transition.state)
            edges[source_index].append((transition.label, index[transition.state]))

    return {
        "states": seen,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _safe_graph_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    terminal_states = [state for state in states if model.is_terminal(state)]
    accepted = [state for state in terminal_states if state.status == "accepted"]
    rejected = [state for state in terminal_states if state.status == "rejected"]
    missing_labels = sorted(set(REQUIRED_LABELS) - set(graph["labels"]))
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and len(accepted) == 1
        and accepted[0].scenario == model.VALID_CONTRACT
        and len(rejected) == len(model.NEGATIVE_SCENARIOS),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "accepted_state_count": len(accepted),
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
            targets = [target for _label, target in outgoing]
            if source not in can_reach_terminal and any(
                target in can_reach_terminal for target in targets
            ):
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
        "reachability_failures": [
            failure.message for failure in report.reachability_failures
        ],
    }


def _hazard_report() -> dict[str, object]:
    hazards: dict[str, object] = {}
    failures: list[str] = []
    for name, state in model.hazard_states().items():
        contract_failures = model.contract_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in contract_failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": contract_failures,
        }
        if not detected:
            failures.append(f"{name}: expected failure containing {expected!r}")
    return {"ok": not failures, "hazards": hazards, "failures": failures}


def _doc_audit() -> dict[str, object]:
    if not CONTRACT_DOC.exists():
        return {
            "ok": False,
            "missing_doc": str(CONTRACT_DOC),
            "failures": ["GateDecision implementation contract document is missing"],
        }
    text = CONTRACT_DOC.read_text(encoding="utf-8")
    missing = [snippet for snippet in DOC_REQUIRED_SNIPPETS if snippet not in text]
    return {
        "ok": not missing,
        "path": str(CONTRACT_DOC),
        "missing_snippets": missing,
        "required_snippet_count": len(DOC_REQUIRED_SNIPPETS),
    }


def run_checks(*, include_doc_audit: bool = True) -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _hazard_report()
    doc_audit = _doc_audit() if include_doc_audit else {
        "ok": True,
        "skipped": "skipped_with_reason: --skip-doc-audit was provided",
    }
    result = {
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "doc_audit": doc_audit,
    }
    result["ok"] = all(
        section.get("ok", False)
        for section in (safe_graph, progress, explorer, hazards, doc_audit)
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--skip-doc-audit", action="store_true")
    args = parser.parse_args()

    result = run_checks(include_doc_audit=not args.skip_doc_audit)
    output = json.dumps(result, indent=2, sort_keys=True)
    print(output)
    if args.json_out:
        args.json_out.write_text(output + "\n", encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
