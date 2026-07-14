"""Run the focused ordinary-resource discovery FlowGuard child model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from dataclasses import asdict, is_dataclass
from pathlib import Path
import sys
from typing import Any, Sequence

from flowguard.explorer import Explorer

import flowpilot_ordinary_resource_discovery_model as model


RESULTS_PATH = Path(__file__).resolve().with_name(
    "flowpilot_ordinary_resource_discovery_results.json"
)

REQUIRED_LABELS = (
    "ordinary_resource_discovery_started",
    "runtime_projects_shallow_local_skill_inventory",
    "pm_selects_relevant_skill_candidates",
    "pm_deep_reads_only_selected_skills",
    "pm_decides_whether_ordinary_material_work_is_needed",
    "pm_issues_ordinary_role_work_packet",
    "evidence_role_submits_ordinary_work_result",
    "ordinary_material_work_receives_risk_appropriate_review",
    "optional_material_map_is_navigation_only",
    "ordinary_resource_discovery_complete",
)

HAZARD_EXPECTED_FAILURES = {
    "missing_local_inventory": "planning advanced without mandatory local skill inventory",
    "stale_inventory_paths": "planning advanced with stale or incomplete inventory projection",
    "runtime_deep_reads_all_skills": "Runtime deep-read every discovered skill",
    "missing_pm_selection": "skills were deeply read before PM relevance selection",
    "missing_selected_skill_obligations": "selected skill deep read produced no reviewer-checkable obligations",
    "dedicated_material_gate": "mandatory dedicated material gate re-entered",
    "dedicated_material_result": "dedicated material result family became current authority",
    "old_material_sources_field": "removed material_sources discovery field was accepted",
    "old_material_sufficiency_field": "removed material_sufficiency discovery field was accepted",
    "old_field_translation": "removed discovery material field was translated or defaulted",
    "ordinary_packet_bypassed": "material result bypassed the ordinary role-work packet",
    "ordinary_review_bypassed": "risk-applicable ordinary material work bypassed existing review",
    "map_absence_blocks": "optional material artifact-map absence blocked the flow",
}


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(child) for key, child in value.items()}
    return value


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|needed={state.material_work_needed}|map={state.material_map_present}|"
        f"inventory={state.runtime_shallow_inventory_projected},{state.inventory_paths_current}|"
        f"skills={state.pm_candidate_selection_recorded},{state.selected_skills_deep_read},"
        f"{state.selected_skill_obligations_written}|ordinary={state.ordinary_role_work_packet_issued},"
        f"{state.ordinary_role_work_result_submitted},{state.risk_appropriate_review_completed}|"
        f"ready={state.planning_ready}"
    )


def _graph_report() -> dict[str, object]:
    initials = model.initial_states()
    queue: deque[model.State] = deque(initials)
    states = list(initials)
    index = {state: idx for idx, state in enumerate(states)}
    edges: list[list[tuple[str, int]]] = [[] for _ in states]
    labels: set[str] = set()
    failures: list[dict[str, object]] = []
    while queue:
        state = queue.popleft()
        source = index[state]
        current_failures = model.invariant_failures(state)
        if current_failures:
            failures.append({"state": _state_id(state), "failures": current_failures})
        for transition in model.next_safe_states(state):
            labels.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(states)
                states.append(transition.state)
                edges.append([])
                queue.append(transition.state)
            edges[source].append((transition.label, index[transition.state]))
    success = {idx for idx, state in enumerate(states) if model.is_success(state)}
    can_reach_success = set(success)
    changed = True
    while changed:
        changed = False
        for idx, outgoing in enumerate(edges):
            if idx not in can_reach_success and any(target in can_reach_success for _label, target in outgoing):
                can_reach_success.add(idx)
                changed = True
    stuck = [
        _state_id(state)
        for idx, state in enumerate(states)
        if not model.is_terminal(state) and not edges[idx]
    ]
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    missing_variants = [
        _state_id(initial)
        for initial in initials
        if index[initial] not in can_reach_success
    ]
    return {
        "ok": not failures and not stuck and not missing_labels and not missing_variants,
        "state_count": len(states),
        "edge_count": sum(len(row) for row in edges),
        "invariant_failures": failures,
        "stuck_states": stuck,
        "missing_labels": missing_labels,
        "initial_variants_without_success": missing_variants,
    }


def _explorer_report() -> dict[str, object]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=model.initial_states(),
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
    rows: dict[str, object] = {}
    ok = True
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in failures)
        rows[name] = {"detected": detected, "expected": expected, "failures": failures}
        ok = ok and detected
    return {"ok": ok, "known_bad_count": len(rows), "rows": rows}


def _architecture_reduction() -> dict[str, object]:
    report = model.architecture_reduction_report()
    data = _jsonable(report)
    ok = bool(getattr(report, "ok", data.get("ok", False)))
    decision = str(getattr(report, "decision", data.get("decision", "")))
    return {
        "ok": ok,
        "decision": decision,
        "report": data,
    }


def _implementation_alignment() -> dict[str, object]:
    root = Path(__file__).resolve().parents[1]
    core_runtime = root / "skills/flowpilot/assets/flowpilot_core_runtime"
    if str(core_runtime) not in sys.path:
        sys.path.insert(0, str(core_runtime))
    import packet_result_contracts  # noqa: PLC0415

    paths = {
        "runtime": root / "skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
        "contracts": root / "skills/flowpilot/assets/flowpilot_core_runtime/packet_result_contracts.py",
        "stage_matrix": root / "skills/flowpilot/assets/flowpilot_core_runtime/packet_stage_evidence_matrix.py",
        "tests": root / "tests/test_flowpilot_ordinary_resource_discovery.py",
    }
    texts = {
        key: path.read_text(encoding="utf-8").lower() if path.exists() else ""
        for key, path in paths.items()
    }
    discovery_row = packet_result_contracts.contract_for_family("task.discovery") or {}
    required_fields = set(discovery_row.get("required_fields") or ())
    forbidden_fields = set(discovery_row.get("forbidden_fields") or ())
    fake_success_fields = set(discovery_row.get("fake_ai_success_fields") or ())
    accepted_discovery_slice = texts["runtime"].split('if route_scope == "discovery":', 1)[-1].split(
        'if route_scope == "skill_standard":', 1
    )[0]
    checks = {
        "runtime_inventory_projection": "runtime_local_capability_inventory" in texts["runtime"],
        "discovery_contract_keeps_candidate_inventory": "candidate_skill_inventory" in required_fields,
        "discovery_contract_removes_material_sources": (
            "material_sources" not in required_fields
            and "material_sources" not in fake_success_fields
            and "material_sources" in forbidden_fields
        ),
        "discovery_contract_removes_material_sufficiency": (
            "material_sufficiency" not in required_fields
            and "material_sufficiency" not in fake_success_fields
            and "material_sufficiency" in forbidden_fields
        ),
        "accepted_discovery_has_no_material_current": '"material_current"' not in accepted_discovery_slice,
        "focused_negative_source_audit_exists": "removed_material_discovery_fields" in texts["tests"],
        "ordinary_role_work_test_exists": "ordinary_material_work" in texts["tests"],
        "optional_map_test_exists": "material_map_absence" in texts["tests"],
    }
    missing = sorted(key for key, value in checks.items() if not value)
    return {"ok": not missing, "checks": checks, "missing": missing, "paths": [str(path) for path in paths.values()]}


def run_checks() -> dict[str, object]:
    graph = _graph_report()
    explorer = _explorer_report()
    hazards = _hazard_report()
    reduction = _architecture_reduction()
    alignment = _implementation_alignment()
    target_failures = {
        f"material={material_needed},map={map_present}": model.invariant_failures(
            model.success_state(material_work_needed=material_needed, material_map_present=map_present)
        )
        for material_needed in (False, True)
        for map_present in (False, True)
    }
    targets_ok = all(not failures for failures in target_failures.values())
    return {
        "model_id": model.MODEL_ID,
        "ok": graph["ok"] and explorer["ok"] and hazards["ok"] and reduction["ok"] and alignment["ok"] and targets_ok,
        "safe_graph_and_progress": graph,
        "flowguard_explorer": explorer,
        "known_bad_hazards": hazards,
        "architecture_reduction": reduction,
        "implementation_alignment": alignment,
        "target_success_failures": target_failures,
        "claim_boundary": (
            "The model proves the declared finite discovery/resource states only; it does not prove "
            "that every future skill or source is semantically useful."
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args(argv)
    result = run_checks()
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
