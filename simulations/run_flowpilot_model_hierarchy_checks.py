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
from flowpilot_thin_parent_checks import (
    LEDGER_PATH,
    LEGACY_RESULT_PATHS,
    THIN_PROOF_PATHS,
    THIN_RESULT_PATHS,
    legacy_full_status,
    release_regression_status,
    read_json,
    thin_input_fingerprint,
    valid_thin_proof,
)


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
    "reject_release_obligation_hidden",
    "reject_routine_thin_parent_blocked_by_full_regression",
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
    "release_obligation_hidden": {
        "release_full_regression_obligation_hidden",
    },
    "routine_thin_parent_blocked_by_full_regression": {
        "full_regression_must_not_block_routine_thin_parent",
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


def _result_row_from_path(path: Path, model_id: str) -> dict[str, Any] | None:
    payload = _read_json(path)
    if not isinstance(payload, Mapping):
        return None
    graph_payload = payload.get("graph") if payload.get("result_type") == "thin_parent" else None
    if isinstance(graph_payload, Mapping):
        counts = {
            "state_count": graph_payload.get("state_count"),
            "edge_count": graph_payload.get("edge_count"),
            "ok": graph_payload.get("ok"),
        }
    else:
        counts = _walk_counts(payload)
    if counts["state_count"] is None and counts["ok"] is None:
        return None
    return {
        "model_id": model_id,
        "result_file": path.relative_to(ROOT).as_posix(),
        "state_count": counts["state_count"],
        "edge_count": counts["edge_count"],
        "ok": counts["ok"],
        "tier": _size_tier(counts["state_count"]),
        "result_type": str(payload.get("result_type") or payload.get("model") or "unknown"),
        "release_confidence": payload.get("release_confidence"),
        "routine_confidence": payload.get("routine_confidence"),
    }


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


def _thin_proof_status(parent: str) -> dict[str, Any]:
    if parent == "meta":
        runner_path = SIMULATIONS / "run_meta_checks.py"
    elif parent == "capability":
        runner_path = SIMULATIONS / "run_capability_checks.py"
    else:
        return {"valid": False, "reason": "unknown parent"}
    result_path = THIN_RESULT_PATHS[parent]
    proof_path = THIN_PROOF_PATHS[parent]
    proof = _read_json(proof_path)
    try:
        input_fingerprint = thin_input_fingerprint(parent, runner_path)
        valid, reason = valid_thin_proof(
            parent=parent,
            runner_path=runner_path,
            result_path=result_path,
            proof_path=proof_path,
            input_fingerprint=input_fingerprint,
        )
    except Exception as exc:
        valid = False
        reason = f"thin proof check failed: {exc}"
    row = {
        "valid": valid,
        "reason": reason,
        "proof_file": proof_path.relative_to(ROOT).as_posix(),
        "result_file": result_path.relative_to(ROOT).as_posix(),
    }
    if isinstance(proof, Mapping):
        row["created_at"] = proof.get("created_at")
        row["result_type"] = proof.get("result_type")
    return row


def _flowguard_schema_version() -> str:
    try:
        import flowguard

        return str(flowguard.SCHEMA_VERSION)
    except Exception:
        return "unavailable"


def _owner_label(parent: str, owner_type: str) -> str:
    if owner_type == "child":
        return parent
    return owner_type


def _partition_contracts_from_ledger() -> dict[str, Any]:
    ledger = read_json(LEDGER_PATH)
    if not isinstance(ledger, Mapping):
        return {
            "ok": False,
            "ledger_file": LEDGER_PATH.relative_to(ROOT).as_posix(),
            "parents": {},
            "by_partition": {},
            "state_write_ownership": [],
            "failures": ["ledger_missing_or_invalid"],
        }

    failures: list[str] = []
    parents: dict[str, dict[str, Any]] = {}
    by_partition: dict[str, dict[str, Any]] = {}
    ledger_parents = ledger.get("parents", {})
    if not isinstance(ledger_parents, Mapping):
        failures.append("ledger_parents_missing")
        ledger_parents = {}

    for parent in model.PARENT_MODELS:
        parent_data = ledger_parents.get(parent)
        if not isinstance(parent_data, Mapping):
            failures.append(f"{parent}:parent_missing")
            continue
        partitions = parent_data.get("partitions")
        if not isinstance(partitions, list):
            failures.append(f"{parent}:partitions_missing")
            continue
        parent_rows: dict[str, Any] = {}
        for partition in partitions:
            if not isinstance(partition, Mapping):
                failures.append(f"{parent}:partition_not_object")
                continue
            partition_id = str(partition.get("id") or "")
            if not partition_id:
                failures.append(f"{parent}:partition_id_missing")
                continue
            evidence_ids = [str(item) for item in partition.get("evidence_ids", [])]
            owner_type = str(partition.get("owner_type") or "")
            release_obligation = str(partition.get("release_obligation") or "")
            invariant_families = [str(item) for item in partition.get("invariant_families", [])]
            row = {
                "parent": parent,
                "owner_type": owner_type,
                "owner": _owner_label(parent, owner_type),
                "children": evidence_ids,
                "invariant_families": invariant_families,
                "release_obligation": release_obligation,
            }
            parent_rows[partition_id] = row

            aggregate = by_partition.setdefault(
                partition_id,
                {
                    "parents": [],
                    "owners": [],
                    "children": [],
                    "invariant_families": [],
                    "release_obligations": [],
                },
            )
            aggregate["parents"].append(parent)
            aggregate["owners"].append(row["owner"])
            aggregate["children"] = sorted(set(aggregate["children"]) | set(evidence_ids))
            aggregate["invariant_families"] = sorted(
                set(aggregate["invariant_families"]) | set(invariant_families)
            )
            if release_obligation:
                aggregate["release_obligations"] = sorted(
                    set(aggregate["release_obligations"]) | {release_obligation}
                )
        parents[parent] = parent_rows

    expected_partitions = set(model.PARTITION_ITEMS)
    actual_partitions = set(by_partition)
    missing = sorted(expected_partitions - actual_partitions)
    extra = sorted(actual_partitions - expected_partitions)
    if missing:
        failures.extend(f"partition_missing:{item}" for item in missing)
    if extra:
        failures.extend(f"partition_unknown:{item}" for item in extra)

    return {
        "ok": not failures,
        "ledger_file": LEDGER_PATH.relative_to(ROOT).as_posix(),
        "parents": parents,
        "by_partition": by_partition,
        "state_write_ownership": ledger.get("state_write_ownership", []),
        "missing_partition_items": missing,
        "unknown_partition_items": extra,
        "failures": failures,
    }


def build_inventory_report() -> dict[str, Any]:
    partition_contracts = _partition_contracts_from_ledger()
    results = _result_index()
    parent_rows: list[dict[str, Any]] = []
    for parent in model.PARENT_MODELS:
        thin_row = _result_row_from_path(THIN_RESULT_PATHS[parent], parent)
        full_row = _result_row_from_path(LEGACY_RESULT_PATHS[parent], parent)
        release_status = release_regression_status(parent)
        legacy_status = legacy_full_status(parent)
        thin_proof = _thin_proof_status(parent)
        row = dict(thin_row or full_row or results.get(parent, {"model_id": parent, "tier": "unknown"}))
        row["role"] = "thin_parent" if thin_row else "heavyweight_parent"
        row["thin_parent"] = {
            "result": thin_row,
            "proof": thin_proof,
        }
        row["legacy_full_regression"] = {
            "result": full_row,
            "proof": release_status,
            "required_for_release": bool(release_status.get("legacy_monolith_required")),
            "current": bool(release_status.get("valid")),
            "legacy_monolith_status": legacy_status,
        }
        row["full_state_count"] = full_row.get("state_count") if full_row else None
        row["split_review_required"] = (
            (full_row is not None and (full_row.get("state_count") or 0) >= HEAVYWEIGHT_STATE_THRESHOLD)
            or row.get("role") == "thin_parent"
        )
        row["proof"] = release_status
        row["release_confidence"] = (
            row.get("release_confidence")
            or ("current" if release_status.get("valid") else "requires_background_or_valid_proof")
        )
        row["routine_validation_command"] = f"python simulations/run_{parent}_checks.py --fast"
        row["release_validation_command"] = f"python simulations/run_{parent}_checks.py --full"
        row["legacy_monolith_command"] = f"python simulations/run_{parent}_checks.py --legacy-full"
        parent_rows.append(row)

    child_ids = sorted(
        {
            child
            for parent_map in partition_contracts.get("parents", {}).values()
            for item in parent_map.values()
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
        if not parent.get("legacy_full_regression", {}).get("current")
    ]
    thin_parent_obligations = [
        parent["model_id"]
        for parent in parent_rows
        if not parent.get("thin_parent", {}).get("proof", {}).get("valid")
    ]
    tier_counts: dict[str, int] = {}
    for child in child_rows:
        tier = str(child.get("tier") or "unknown")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    routine_ok = (
        partition_contracts.get("ok") is True
        and not large_children
        and not missing_children
        and not thin_parent_obligations
    )
    return {
        "ok": routine_ok,
        "evidence_contract_version": "flowpilot.parent_evidence_layers.v1",
        "heavyweight_threshold": HEAVYWEIGHT_STATE_THRESHOLD,
        "routine_confidence": "current" if routine_ok else "blocked",
        "routine_validation_commands": {
            "meta": "python simulations/run_meta_checks.py --fast",
            "capability": "python simulations/run_capability_checks.py --fast",
            "hierarchy": (
                "python simulations/run_flowpilot_model_hierarchy_checks.py "
                "--json-out simulations/flowpilot_model_hierarchy_results.json"
            ),
        },
        "release_validation_commands": {
            "meta": "python simulations/run_meta_checks.py --full",
            "capability": "python simulations/run_capability_checks.py --full",
        },
        "legacy_monolith_commands": {
            "meta": "python simulations/run_meta_checks.py --legacy-full",
            "capability": "python simulations/run_capability_checks.py --legacy-full",
        },
        "parents": parent_rows,
        "registered_child_count": len(child_rows),
        "registered_children": child_rows,
        "child_evidence_tier_counts": tier_counts,
        "missing_child_results": missing_children,
        "large_child_models": large_children,
        "thin_parent_obligations": thin_parent_obligations,
        "partition_contracts": partition_contracts,
        "partition_map": partition_contracts.get("by_partition", {}),
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
        f"layer={state.release_obligation_visible},{state.full_regression_used_as_routine_gate}|"
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
