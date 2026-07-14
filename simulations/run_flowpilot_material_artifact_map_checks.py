"""Run checks for the FlowPilot optional material artifact-map model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

import flowpilot_material_artifact_map_model as model


RESULTS_PATH = Path(__file__).resolve().with_name(
    "flowpilot_material_artifact_map_results.json"
)

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.MAP_CREATED_WITHOUT_REQUEST: "missing optional map was created without an explicit request",
    model.MAP_ABSENCE_BLOCKS_PLANNING: "optional map absence blocked planning",
    model.MAP_ABSENCE_BLOCKS_FORMAL_PACKAGE: "optional map absence blocked formal package release",
    model.MAP_ABSENCE_BLOCKS_ROUTE_MEMORY: "optional map absence blocked route memory",
    model.MAP_ABSENCE_BLOCKS_TERMINAL: "optional map absence blocked terminal closure",
    model.MAP_LEAKS_SEALED_BODY: "material artifact map leaked sealed packet or result body content",
    model.MAP_USED_AS_ACCEPTANCE: "optional material map was treated as acceptance evidence",
    model.MAP_LINKS_UNSAFE_INDEX: "unsafe, blocked, stale, or unresolved optional map was linked",
    model.MAP_LINKS_STALE_INDEX: "unsafe, blocked, stale, or unresolved optional map was linked",
    model.MAP_LINKS_UNRESOLVED_INDEX: "unsafe, blocked, stale, or unresolved optional map was linked",
    model.FORMAL_PACKAGE_LACKS_DIRECT_EVIDENCE: "formal package relied on optional map instead of direct current evidence",
    model.SEALED_REF_BYPASSES_RUNTIME: "sealed material reference bypassed runtime open authority",
    model.RETIRED_MATERIAL_SCAN_PREFIX: "retired material-scan index or review prefix re-entered the current map",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|"
        f"map={state.map_initially_present},{state.map_creation_requested},{state.map_written},"
        f"{state.map_ref_present}|stages={state.planning_advanced},{state.formal_package_written},"
        f"{state.route_memory_written},{state.final_ledger_written}|reason={state.terminal_reason}"
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
    stuck = [_state_id(state) for idx, state in enumerate(states) if idx not in terminal and not edges[idx]]
    cannot_reach_terminal = [_state_id(state) for idx, state in enumerate(states) if idx not in can_reach_terminal]
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
        observed = model.material_map_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in observed)
        hazards[name] = {"detected": detected, "expected_failure": expected, "failures": observed}
        if not detected:
            failures.append(f"{name}: expected failure containing {expected!r}")
    return {"ok": not failures, "hazards": hazards, "failures": failures}


def _implementation_alignment() -> dict[str, object]:
    root = Path(__file__).resolve().parents[1]
    paths = {
        "map": root / "skills/flowpilot/assets/flowpilot_material_artifact_map.py",
        "formal": root / "skills/flowpilot/assets/flowpilot_router_work_packets_pm_role_writes_decisions_formal_gate.py",
        "disposition": root / "skills/flowpilot/assets/flowpilot_router_work_packets_pm_role_writes_decisions_package_disposition.py",
        "memory": root / "skills/flowpilot/assets/flowpilot_router_route_frontier_context_memory.py",
        "terminal": root / "skills/flowpilot/assets/flowpilot_router_terminal_ledger_writer.py",
        "tests": root / "tests/test_flowpilot_material_access_mesh.py",
    }
    texts = {key: path.read_text(encoding="utf-8") for key, path in paths.items()}
    checks = {
        "missing_map_not_created_by_default": "create_if_missing: bool = False" in texts["map"],
        "explicit_creation_required": "if not path.exists() and not create_if_missing" in texts["map"],
        "retired_index_prefix_absent": "material_scan:packet_index" not in texts["map"],
        "formal_package_uses_optional_ref": "material_artifact_map_navigation_usable" in texts["formal"],
        "retired_disposition_branch_absent": "batch_kind == 'material_scan'" not in texts["disposition"],
        "retired_disposition_event_absent": "pm_records_material_scan_result_disposition" not in texts["disposition"],
        "route_memory_uses_optional_context": "map_context is not None" in texts["memory"],
        "retired_route_markers_absent": "reviewer_reports_material_sufficient" not in texts["memory"],
        "terminal_links_map_conditionally": "if isinstance(map_ref, dict)" in texts["terminal"],
        "absent_and_present_tests_exist": "test_missing_map_stays_absent" in texts["tests"] and "test_existing_map_is_refreshed" in texts["tests"],
    }
    missing = sorted(key for key, value in checks.items() if not value)
    return {
        "ok": not missing,
        "checks": checks,
        "missing": missing,
        "paths": [path.relative_to(root).as_posix() for path in paths.values()],
    }


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _hazard_report()
    alignment = _implementation_alignment()
    result = {
        "model_id": model.MODEL_ID,
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "implementation_alignment": alignment,
        "claim_boundary": (
            "This finite model proves only the declared missing/requested/existing map paths and known-bad "
            "mutations; direct runtime tests still own concrete file and terminal behavior."
        ),
    }
    result["ok"] = all(section.get("ok", False) for section in (safe_graph, progress, explorer, hazards, alignment))
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
