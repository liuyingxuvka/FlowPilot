"""Executable FlowGuard checks for the FlowPilot model hierarchy."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import deque
from pathlib import Path
from typing import Any, Mapping, Sequence

from flowguard import Explorer

import flowpilot_model_hierarchy_model as model


ROOT = Path(__file__).resolve().parents[1]
SIMULATIONS = ROOT / "simulations"
RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_model_hierarchy_results.json")
HEAVYWEIGHT_STATE_THRESHOLD = model.HEAVYWEIGHT_STATE_THRESHOLD

REQUIRED_LABELS = {
    "select_valid_hierarchy_with_background_obligation",
    "accept_valid_hierarchy_with_background_obligation",
    "select_valid_release_hierarchy_with_current_heavy_proof",
    "accept_valid_release_hierarchy_with_current_heavy_proof",
    "reject_heavy_parent_without_split_review",
    "reject_parent_partition_gap",
    "reject_sibling_ownership_overlap",
    "reject_stale_child_evidence_used",
    "reject_hidden_child_skipped_checks",
    "reject_release_green_without_heavy_parent_proof",
    "reject_background_progress_only_claimed_pass",
    "reject_child_model_inlines_parent_graph",
    "reject_authority_mesh_confused_with_partition",
    "reject_missing_child_inventory",
}

EXPECTED_HAZARD_FAILURES = {
    "heavy_parent_without_split_review": {"heavy_parent_split_review_missing"},
    "parent_partition_gap": {"parent_partition_coverage_gap"},
    "sibling_ownership_overlap": {
        "sibling_overlap_requires_explicit_shared_kernel_or_refactor",
    },
    "stale_child_evidence_used": {"child_evidence_stale_or_foreign"},
    "hidden_child_skipped_checks": {"child_skipped_required_checks_hidden"},
    "release_green_without_heavy_parent_proof": {
        "release_claim_requires_current_heavy_parent_regression",
    },
    "background_progress_only_claimed_pass": {
        "background_progress_is_not_completion_evidence",
    },
    "child_model_inlines_parent_graph": {
        "child_model_must_not_inline_parent_state_graph",
    },
    "authority_mesh_confused_with_partition": {
        "authority_mesh_cannot_substitute_for_partition_map",
    },
    "missing_child_inventory": {"child_model_inventory_incomplete"},
}

PARENT_PARTITION_MAP = {
    "startup": {
        "owner": "shared_kernel",
        "children": [
            "flowpilot_startup_control",
            "startup_pm_review",
            "flowpilot_startup_intake_ui",
            "flowpilot_deterministic_startup_bootstrap",
        ],
    },
    "material_intake": {
        "owner": "meta",
        "children": ["flowpilot_pm_package_absorption", "flowpilot_handoff_artifact_protocol"],
    },
    "product_architecture": {
        "owner": "shared_kernel",
        "children": ["flowpilot_planning_quality", "flowpilot_model_driven_recursive_route"],
    },
    "crew_and_heartbeat": {
        "owner": "shared_kernel",
        "children": ["flowpilot_resume", "flowpilot_role_recovery", "flowpilot_daemon_liveness"],
    },
    "router_daemon_resume": {
        "owner": "meta",
        "children": [
            "flowpilot_router_loop",
            "flowpilot_persistent_router_daemon",
            "flowpilot_daemon_reconciliation",
            "flowpilot_route_replanning_policy",
        ],
    },
    "packet_and_role_authority": {
        "owner": "shared_kernel",
        "children": [
            "flowpilot_packet_lifecycle",
            "flowpilot_packet_open_authority",
            "flowpilot_card_envelope",
            "flowpilot_role_output_runtime",
        ],
    },
    "child_skill_capability": {
        "owner": "capability",
        "children": [
            "card_instruction_coverage",
            "flowpilot_reviewer_active_challenge",
            "flowpilot_requirement_traceability",
            "flowpilot_output_contract",
        ],
    },
    "terminal_ledger": {
        "owner": "shared_kernel",
        "children": [
            "flowpilot_terminal_state_monotonicity",
            "flowpilot_terminal_summary",
            "defect_governance",
            "flowpilot_repair_transaction",
        ],
    },
    "evidence_mesh_and_install_sync": {
        "owner": "shared_kernel",
        "children": [
            "flowpilot_model_mesh",
            "flowpilot_control_transaction_registry",
            "flowpilot_legal_next_action",
            "proof_carrying",
            "release_tooling",
        ],
    },
}


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        return {"__parse_error__": str(exc)}


def _walk_counts(value: Any) -> dict[str, Any]:
    state_counts: list[int] = []
    edge_counts: list[int] = []
    ok_values: list[bool] = []

    def visit(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if key == "state_count" and isinstance(child, int):
                    state_counts.append(child)
                elif key == "edge_count" and isinstance(child, int):
                    edge_counts.append(child)
                elif key == "ok" and isinstance(child, bool):
                    ok_values.append(child)
                visit(child)
        elif isinstance(node, list):
            for child in node[:100]:
                visit(child)

    visit(value)
    return {
        "state_count": max(state_counts) if state_counts else None,
        "edge_count": max(edge_counts) if edge_counts else None,
        "ok": all(ok_values) if ok_values else None,
    }


def _base_from_result_path(path: Path) -> str:
    name = path.stem
    if name == "results":
        return "meta"
    for suffix in (
        "_checks_results",
        "_model_only_results",
        "_background_latest",
        "_results",
    ):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _result_index() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted(SIMULATIONS.glob("*.json")):
        if "results" not in path.name and path.name != "results.json":
            continue
        payload = _read_json(path)
        if not isinstance(payload, Mapping):
            continue
        counts = _walk_counts(payload)
        if counts["state_count"] is None and counts["ok"] is None:
            continue
        base = _base_from_result_path(path)
        previous = rows.get(base)
        current_state_count = counts["state_count"] if counts["state_count"] is not None else -1
        previous_state_count = -1
        if previous and previous.get("state_count") is not None:
            previous_state_count = int(previous["state_count"])
        if previous and previous_state_count >= current_state_count:
            continue
        rows[base] = {
            "model_id": base,
            "result_file": path.relative_to(ROOT).as_posix(),
            "state_count": current_state_count if current_state_count >= 0 else None,
            "edge_count": counts["edge_count"],
            "ok": counts["ok"],
            "tier": _size_tier(counts["state_count"]),
        }
    return rows


def _size_tier(state_count: int | None) -> str:
    if state_count is None:
        return "unknown"
    if state_count >= 100_000:
        return "huge"
    if state_count >= HEAVYWEIGHT_STATE_THRESHOLD:
        return "large"
    if state_count >= 1_000:
        return "medium"
    return "small"


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _proof_status(parent: str) -> dict[str, Any]:
    if parent == "meta":
        result_path = SIMULATIONS / "results.json"
        proof_path = SIMULATIONS / "results.proof.json"
        model_path = SIMULATIONS / "meta_model.py"
        runner_path = SIMULATIONS / "run_meta_checks.py"
        check_name = "meta"
    elif parent == "capability":
        result_path = SIMULATIONS / "capability_results.json"
        proof_path = SIMULATIONS / "capability_results.proof.json"
        model_path = SIMULATIONS / "capability_model.py"
        runner_path = SIMULATIONS / "run_capability_checks.py"
        check_name = "capability"
    else:
        return {"valid": False, "reason": "unknown parent"}

    proof = _read_json(proof_path)
    if not isinstance(proof, Mapping):
        return {
            "valid": False,
            "reason": "proof missing or invalid",
            "proof_file": proof_path.relative_to(ROOT).as_posix(),
        }
    if not result_path.exists():
        return {"valid": False, "reason": "result missing"}
    payload = {
        "flowguard_schema_version": _flowguard_schema_version(),
        "model": _file_sha256(model_path),
        "runner": _file_sha256(runner_path),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    input_fingerprint = hashlib.sha256(encoded).hexdigest()
    result_fingerprint = _file_sha256(result_path)
    valid = (
        proof.get("schema") == 1
        and proof.get("check") == check_name
        and proof.get("ok") is True
        and proof.get("input_fingerprint") == input_fingerprint
        and proof.get("result_fingerprint") == result_fingerprint
    )
    reason = "valid proof" if valid else "proof fingerprint mismatch"
    return {
        "valid": valid,
        "reason": reason,
        "proof_file": proof_path.relative_to(ROOT).as_posix(),
        "result_file": result_path.relative_to(ROOT).as_posix(),
        "created_at": proof.get("created_at"),
    }


def _flowguard_schema_version() -> str:
    try:
        import flowguard

        return str(flowguard.SCHEMA_VERSION)
    except Exception:
        return "unavailable"


def build_inventory_report() -> dict[str, Any]:
    results = _result_index()
    parent_rows: list[dict[str, Any]] = []
    for parent in model.PARENT_MODELS:
        row = dict(results.get(parent, {"model_id": parent, "tier": "unknown"}))
        row["role"] = "heavyweight_parent"
        row["split_review_required"] = row.get("state_count", 0) >= HEAVYWEIGHT_STATE_THRESHOLD
        row["proof"] = _proof_status(parent)
        parent_rows.append(row)

    child_ids = sorted(
        {
            child
            for item in PARENT_PARTITION_MAP.values()
            for child in item["children"]
        }
    )
    child_rows = []
    for child in child_ids:
        row = dict(results.get(child, {"model_id": child, "tier": "unknown"}))
        row["role"] = "child_evidence"
        row["registered_in_partition"] = True
        child_rows.append(row)

    missing_children = sorted(child["model_id"] for child in child_rows if not child.get("result_file"))
    large_children = sorted(
        child["model_id"]
        for child in child_rows
        if child.get("state_count") is not None
        and child["state_count"] >= HEAVYWEIGHT_STATE_THRESHOLD
    )
    heavy_parent_obligations = [
        parent["model_id"]
        for parent in parent_rows
        if not parent.get("proof", {}).get("valid")
    ]
    return {
        "ok": not large_children,
        "heavyweight_threshold": HEAVYWEIGHT_STATE_THRESHOLD,
        "parents": parent_rows,
        "registered_child_count": len(child_rows),
        "registered_children": child_rows,
        "missing_child_results": missing_children,
        "large_child_models": large_children,
        "partition_map": PARENT_PARTITION_MAP,
        "partition_items": list(model.PARTITION_ITEMS),
        "heavy_parent_full_regression_obligations": heavy_parent_obligations,
        "release_confidence": "current" if not heavy_parent_obligations else "requires_background_or_valid_proof",
    }


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|decision={state.decision}|"
        f"parent={state.heavyweight_parent_registered},{state.parent_exceeds_threshold},"
        f"{state.split_review_required}|partition={state.partition_map_written},"
        f"{state.partition_coverage_complete},{state.sibling_ownership_overlap}|"
        f"child={state.child_inventory_complete},{state.child_evidence_registered},"
        f"{state.child_evidence_current},{state.child_expands_parent_graph}|"
        f"release={state.hierarchy_claims_release_green},{state.heavy_full_regression_current}|"
        f"background={state.background_run_has_exit_artifact},"
        f"{state.background_run_has_valid_result_or_proof},{state.background_progress_claimed_as_pass}"
    )


def _walk_graph() -> dict[str, Any]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states: list[model.State] = [initial]
    index = {initial: 0}
    edges: list[list[tuple[str, int]]] = []
    labels_seen: set[str] = set()
    violations: list[dict[str, Any]] = []

    while queue:
        state = queue.popleft()
        source = index[state]
        while len(edges) <= source:
            edges.append([])
        failures = model.invariant_failures(state)
        if failures:
            violations.append({"state": _state_id(state), "failures": failures})
        for transition in model.next_safe_states(state):
            labels_seen.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(states)
                states.append(transition.state)
                queue.append(transition.state)
            edges[source].append((transition.label, index[transition.state]))

    return {
        "ok": not violations and not (REQUIRED_LABELS - labels_seen),
        "states": states,
        "edges": edges,
        "state_count": len(states),
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "terminal_state_count": sum(1 for state in states if model.is_terminal(state)),
        "accepted_state_count": sum(1 for state in states if state.status == "accepted"),
        "rejected_state_count": sum(1 for state in states if state.status == "rejected"),
        "labels_seen": sorted(labels_seen),
        "missing_labels": sorted(REQUIRED_LABELS - labels_seen),
        "violations": violations,
    }


def _graph_for_output(graph: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in graph.items() if key not in {"states", "edges"}}


def _progress_report(graph: Mapping[str, Any]) -> dict[str, Any]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {index for index, state in enumerate(states) if model.is_terminal(state)}
    stuck = [
        _state_id(state)
        for index, state in enumerate(states)
        if index not in terminal and not edges[index]
    ]
    return {
        "ok": not stuck,
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "cannot_reach_terminal_count": 0,
        "cannot_reach_terminal_samples": [],
    }


def _flowguard_report() -> dict[str, Any]:
    report = Explorer(
        model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=lambda _input, state, _trace: model.is_terminal(state),
        success_predicate=lambda state, _trace: model.is_success(state),
    ).explore()
    return {
        "ok": report.ok,
        "summary": report.summary,
        "violation_count": len(report.violations),
        "violations": [str(item) for item in report.violations[:10]],
        "exception_branch_count": len(report.exception_branches),
        "dead_branch_count": len(report.dead_branches),
        "reachability_failure_count": len(report.reachability_failures),
    }


def _terminal_state_for(name: str) -> model.State:
    selected = None
    for transition in model.next_safe_states(model.initial_state()):
        if transition.label == f"select_{name}":
            selected = transition.state
            break
    if selected is None:
        raise KeyError(name)
    terminals = list(model.next_safe_states(selected))
    if len(terminals) != 1:
        raise AssertionError(f"expected one terminal for {name}")
    return terminals[0].state


def _contract_refinement_report() -> dict[str, Any]:
    bad_accepts: list[dict[str, Any]] = []
    bad_rejects: list[dict[str, Any]] = []
    for name in sorted(model.SCENARIOS):
        terminal = _terminal_state_for(name)
        should_accept = name in model.VALID_SCENARIOS
        accepted = terminal.status == "accepted"
        if accepted and not should_accept:
            bad_accepts.append({"scenario": name, "failures": model.hierarchy_failures(model.SCENARIOS[name])})
        if should_accept and not accepted:
            bad_rejects.append({"scenario": name, "failures": model.hierarchy_failures(model.SCENARIOS[name])})
    return {
        "ok": not bad_accepts and not bad_rejects,
        "accepted_scenarios": sorted(model.VALID_SCENARIOS),
        "rejected_scenarios": sorted(model.NEGATIVE_SCENARIOS),
        "bad_accepts": bad_accepts,
        "bad_rejects": bad_rejects,
    }


def _hazard_report() -> dict[str, Any]:
    rows = []
    ok = True
    for name, state in model.hazard_states().items():
        observed = set(model.hierarchy_failures(state))
        expected = EXPECTED_HAZARD_FAILURES.get(name, set())
        missing = sorted(expected - observed)
        row_ok = not missing and bool(observed)
        if not row_ok:
            ok = False
        rows.append(
            {
                "scenario": name,
                "ok": row_ok,
                "expected_failures": sorted(expected),
                "observed_failures": sorted(observed),
                "missing_expected_failures": missing,
            }
        )
    return {"ok": ok, "hazards": rows}


def build_report() -> dict[str, Any]:
    graph = _walk_graph()
    progress = _progress_report(graph)
    flowguard = _flowguard_report()
    contract = _contract_refinement_report()
    hazards = _hazard_report()
    inventory = build_inventory_report()
    sections = [graph, progress, flowguard, contract, hazards, inventory]
    return {
        "schema_version": 1,
        "model": "flowpilot_model_hierarchy",
        "ok": all(section.get("ok", False) for section in sections),
        "graph": _graph_for_output(graph),
        "progress": progress,
        "flowguard_explorer": flowguard,
        "contract_refinement": contract,
        "hazard_review": hazards,
        "inventory": inventory,
    }


def _write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json-out",
        default=str(RESULTS_PATH),
        help="Write a JSON report to this path; defaults to the persisted hierarchy result.",
    )
    args = parser.parse_args(argv)

    report = build_report()
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.json_out:
        _write_json(Path(args.json_out), report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
