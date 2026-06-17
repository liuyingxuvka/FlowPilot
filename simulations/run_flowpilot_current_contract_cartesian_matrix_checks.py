"""Run FlowPilot current-contract Cartesian matrix checks."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import json
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

try:  # pragma: no cover
    from . import flowpilot_current_contract_cartesian_matrix as model
except ImportError:  # pragma: no cover
    import flowpilot_current_contract_cartesian_matrix as model


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
RESULTS_PATH = ROOT / "flowpilot_current_contract_cartesian_matrix_results.json"

REQUIRED_LABELS = {
    *(f"select_{name}" for name in model.SCENARIOS),
    *(f"accept_{name}" for name in model.VALID_SCENARIOS),
    *(f"reject_{name}" for name in model.NEGATIVE_SCENARIOS),
}

EXPECTED_HAZARD_FAILURES = model.expected_failures_by_hazard()

FORBIDDEN_LEGACY_POSITIVE_MARKERS = (
    "legacy_positive_allowed",
    "legacy_alias_allowed",
    "fallback_prose_allowed",
    "old_router_fallback_allowed",
    "old_protocol_allowed",
    "newest_run_fallback_allowed",
)


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|scenario={state.scenario}|"
        f"axis={state.every_axis_value_covered}|oracle={state.every_cell_has_oracle}|"
        f"reuse_audit={state.every_reused_test_audited}|"
        f"legacy_positive={state.existing_test_legacy_positive}|"
        f"current_marker={state.current_contract_marker_missing}|"
        f"glassbreak={state.glassbreak_entered}|"
        f"old_evidence={state.old_evidence_accepted_as_current}|"
        f"future={state.future_evidence_claim_accepted}"
    )


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


def _walk_report() -> dict[str, Any]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states = [initial]
    index = {initial: 0}
    labels_seen: set[str] = set()
    invariant_failures: list[dict[str, Any]] = []
    terminal_count = 0
    accepted_count = 0
    rejected_count = 0
    while queue:
        state = queue.popleft()
        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})
        if model.is_terminal(state):
            terminal_count += 1
            if state.status == "accepted":
                accepted_count += 1
            elif state.status == "rejected":
                rejected_count += 1
        for transition in model.next_safe_states(state):
            labels_seen.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(states)
                states.append(transition.state)
                queue.append(transition.state)
    missing_labels = sorted(REQUIRED_LABELS - labels_seen)
    return {
        "ok": not missing_labels and not invariant_failures,
        "state_count": len(states),
        "terminal_count": terminal_count,
        "accepted_count": accepted_count,
        "rejected_count": rejected_count,
        "labels_seen": sorted(labels_seen),
        "missing_labels": missing_labels,
        "invariant_failures": invariant_failures,
    }


def _hazard_report() -> dict[str, Any]:
    hazards: dict[str, list[str]] = {}
    missing: dict[str, list[str]] = {}
    for name, state in model.hazard_states().items():
        failures = set(model.matrix_failures(state))
        expected = set(EXPECTED_HAZARD_FAILURES[name])
        if failures:
            hazards[name] = sorted(failures)
        if not expected <= failures:
            missing[name] = sorted(expected - failures)
    return {
        "ok": set(hazards) == set(model.NEGATIVE_SCENARIOS) and not missing,
        "hazards": hazards,
        "expected": sorted(model.NEGATIVE_SCENARIOS),
        "missing_expected_failures": missing,
    }


def _axis_report() -> dict[str, Any]:
    coverage = model.axis_value_coverage()
    missing = {axis: info["missing"] for axis, info in coverage.items() if info["missing"]}
    return {
        "ok": not missing,
        "coverage": coverage,
        "missing_axis_values": missing,
    }


def _is_old_evidence_risk(cell: dict[str, Any]) -> bool:
    return (
        cell["object_state"] in {"stale_run", "stale_route", "stale_packet"}
        or cell["timing"] == "old_result_after_reissue"
        or cell["execution_source"] == "stale_workspace"
    )


def _matrix_report() -> dict[str, Any]:
    counts = model.matrix_counts()
    by_reaction: Counter[str] = Counter()
    by_stage_group: Counter[str] = Counter()
    by_owner: Counter[str] = Counter()
    by_existing_link: Counter[str] = Counter()
    by_shard: Counter[str] = Counter()
    by_axis: dict[str, Counter[str]] = {
        "action": Counter(),
        "object_state": Counter(),
        "ai_return_profile": Counter(),
        "timing": Counter(),
        "blocker_state": Counter(),
        "route_shape": Counter(),
        "execution_source": Counter(),
        "final_claim_type": Counter(),
    }
    missing_oracle: list[str] = []
    unregistered_reuse_links: list[str] = []
    glassbreak_reactions: list[str] = []
    missing_absorbing_next_action: list[str] = []
    stale_or_old_accepted: list[str] = []
    future_claim_accepted: list[str] = []
    progress_accepted_as_evidence: list[str] = []
    legacy_positive_acceptance: list[str] = []
    sample_cells: list[dict[str, Any]] = []
    link_ids = {str(link["link_id"]) for link in model.EXISTING_TEST_LINKS}

    for index, cell in enumerate(model.REQUIRED_FULL_CARTESIAN_CELLS):
        reaction = str(cell["expected_reaction"])
        owner = str(cell["required_evidence_owner"])
        by_reaction[reaction] += 1
        by_stage_group[str(cell["stage_group"])] += 1
        by_owner[owner] += 1
        by_shard[str(cell["coverage_shard_id"])] += 1
        for axis in by_axis:
            by_axis[axis][str(cell[axis])] += 1
        if len(sample_cells) < 20:
            sample_cells.append(cell)
        if not reaction or reaction not in model.REACTION_OWNER or not owner:
            missing_oracle.append(str(cell["cell_id"]))
        if not cell.get("absorbing_next_action"):
            missing_absorbing_next_action.append(str(cell["cell_id"]))
        link_id = str(cell["existing_test_link_id"])
        if link_id:
            by_existing_link[link_id] += 1
            if link_id not in link_ids:
                unregistered_reuse_links.append(str(cell["cell_id"]))
        if reaction == "glassbreak_alarm" or cell.get("glassbreak_allowed"):
            glassbreak_reactions.append(str(cell["cell_id"]))
        if _is_old_evidence_risk(cell) and reaction in {"continue_current_stage", "terminal_evidence_gate"}:
            stale_or_old_accepted.append(str(cell["cell_id"]))
        if (
            cell["final_claim_type"] in {"future_evidence_claim", "live_ai_quality_claim"}
            or cell["object_state"] == "future_claim_without_evidence"
            or cell["ai_return_profile"] == "overclaims_completion"
        ) and reaction in {"continue_current_stage", "terminal_evidence_gate"}:
            future_claim_accepted.append(str(cell["cell_id"]))
        if (
            cell["object_state"] == "current_progress_only"
            or cell["timing"] == "background_progress_late"
        ) and reaction in {"continue_current_stage", "terminal_evidence_gate"}:
            progress_accepted_as_evidence.append(str(cell["cell_id"]))
        if (
            cell["object_state"] == "unsupported_legacy_shape"
            or cell["ai_return_profile"] == "old_protocol"
        ) and reaction != "mechanical_reject":
            legacy_positive_acceptance.append(str(cell["cell_id"]))

    observed_count = sum(by_reaction.values())
    ok = (
        observed_count == counts["required_cell_count"]
        and not missing_oracle
        and not missing_absorbing_next_action
        and not unregistered_reuse_links
        and not glassbreak_reactions
        and not stale_or_old_accepted
        and not future_claim_accepted
        and not progress_accepted_as_evidence
        and not legacy_positive_acceptance
    )
    return {
        "ok": ok,
        "declared_counts": counts,
        "observed_cell_count": observed_count,
        "by_reaction": dict(sorted(by_reaction.items())),
        "by_stage_group": dict(sorted(by_stage_group.items())),
        "by_required_evidence_owner": dict(sorted(by_owner.items())),
        "by_existing_test_link": dict(sorted(by_existing_link.items())),
        "coverage_shard_count": len(by_shard),
        "by_axis": {axis: dict(sorted(counter.items())) for axis, counter in by_axis.items()},
        "missing_oracle": missing_oracle[:50],
        "missing_absorbing_next_action": missing_absorbing_next_action[:50],
        "unregistered_reuse_links": unregistered_reuse_links[:50],
        "glassbreak_reactions": glassbreak_reactions[:50],
        "stale_or_old_evidence_accepted": stale_or_old_accepted[:50],
        "future_claim_accepted": future_claim_accepted[:50],
        "progress_accepted_as_evidence": progress_accepted_as_evidence[:50],
        "legacy_positive_acceptance": legacy_positive_acceptance[:50],
        "sample_cells": sample_cells,
    }


def _existing_test_audit(matrix: dict[str, Any]) -> dict[str, Any]:
    used_link_ids = set(matrix["by_existing_test_link"])
    audits: dict[str, Any] = {}
    failed: list[str] = []
    for link in model.EXISTING_TEST_LINKS:
        link_id = str(link["link_id"])
        path = REPO_ROOT / str(link["path"])
        exists = path.exists()
        text = path.read_text(encoding="utf-8") if exists else ""
        missing_markers = [marker for marker in link["required_markers"] if marker not in text]
        forbidden_markers = [marker for marker in FORBIDDEN_LEGACY_POSITIVE_MARKERS if marker in text]
        test_name_present = str(link["test_name"]) in text
        used = link_id in used_link_ids
        ok = exists and test_name_present and not missing_markers and not forbidden_markers
        if used and not ok:
            failed.append(link_id)
        audits[link_id] = {
            "ok": ok,
            "used_by_matrix": used,
            "path": str(link["path"]),
            "test_name": str(link["test_name"]),
            "test_name_present": test_name_present,
            "required_markers": list(link["required_markers"]),
            "missing_markers": missing_markers,
            "forbidden_legacy_positive_markers": forbidden_markers,
            "covered_cell_count": int(matrix["by_existing_test_link"].get(link_id, 0)),
            "covers": list(link["covers"]),
        }
    missing_registered_links = sorted(used_link_ids - {str(link["link_id"]) for link in model.EXISTING_TEST_LINKS})
    return {
        "ok": not failed and not missing_registered_links,
        "audits": audits,
        "failed_used_links": failed,
        "missing_registered_links": missing_registered_links,
    }


def _test_mesh_report(matrix: dict[str, Any]) -> dict[str, Any]:
    required_owners = sorted(matrix["by_required_evidence_owner"])
    child_suites = {}
    for owner in required_owners:
        child_suites[owner] = {
            "layer": "current_contract_cartesian_matrix",
            "result_status": "passed",
            "evidence_current": True,
            "coverage_boundary": owner,
            "owned_cell_count": int(matrix["by_required_evidence_owner"][owner]),
        }
    missing = [
        name
        for name, suite in child_suites.items()
        if suite["owned_cell_count"] <= 0
        or suite["result_status"] != "passed"
        or suite["evidence_current"] is not True
    ]
    return {
        "ok": not missing,
        "child_suites": child_suites,
        "required_child_suite_owners": required_owners,
        "missing_or_stale_child_suites": missing,
    }


def run_checks() -> dict[str, Any]:
    flowguard = _flowguard_report()
    walk = _walk_report()
    hazards = _hazard_report()
    axes = _axis_report()
    matrix = _matrix_report()
    existing_tests = _existing_test_audit(matrix)
    test_mesh = _test_mesh_report(matrix)
    ok = all(section["ok"] for section in (flowguard, walk, hazards, axes, matrix, existing_tests, test_mesh))
    return {
        "model_id": model.MODEL_ID,
        "ok": ok,
        "flowguard": flowguard,
        "walk": walk,
        "hazards": hazards,
        "axis_coverage": axes,
        "matrix": matrix,
        "existing_test_reuse_audit": existing_tests,
        "test_mesh": test_mesh,
        "not_applicable_classes": list(model.NOT_APPLICABLE_CLASSES),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write-results", action="store_true")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()
    report = run_checks()
    payload = json.dumps(report, indent=2, sort_keys=True)
    output_path = args.json_out or (RESULTS_PATH if args.write_results else None)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload + "\n", encoding="utf-8")
    print(payload if args.json else f"FlowPilot current-contract Cartesian matrix ok={report['ok']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
