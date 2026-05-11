"""Run checks for the FlowPilot role-output runtime model."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_role_output_runtime_model as model


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
RESULTS_PATH = ROOT / "flowpilot_role_output_runtime_results.json"

REQUIRED_LABELS = (
    "select_valid_pm_resume_decision",
    "select_valid_gate_decision",
    "select_valid_reviewer_report",
    "select_missing_runtime_receipt",
    "select_missing_required_field",
    "select_missing_explicit_empty_array",
    "select_wrong_role",
    "select_stale_body_hash",
    "select_inline_body_leak",
    "select_controller_reads_body",
    "select_semantic_auto_approval",
    "select_missing_quality_pack_check",
    "select_pack_specific_runtime_judgment",
    "runtime_prepares_contract_skeleton",
    "role_authors_body_inside_runtime_skeleton",
    "runtime_validates_writes_receipt_and_envelope",
    "controller_receives_runtime_envelope_only",
    "router_accepts_runtime_checked_role_output",
    "router_rejects_missing_runtime_receipt",
    "router_rejects_missing_required_field",
    "router_rejects_missing_explicit_empty_array",
    "router_rejects_wrong_role",
    "router_rejects_stale_body_hash",
    "router_rejects_inline_body_leak",
    "router_rejects_controller_read_body",
    "router_rejects_runtime_attempted_semantic_approval",
    "router_rejects_missing_quality_pack_check",
    "router_rejects_runtime_attempted_pack_specific_judgment",
)

HAZARD_EXPECTED_FAILURES = {
    "missing_runtime_receipt": "without runtime receipt",
    "missing_required_field": "missing required field",
    "missing_explicit_empty_array": "missing explicit empty array",
    "wrong_role": "wrong role",
    "stale_body_hash": "stale body hash",
    "inline_body_leak": "leaked body content",
    "controller_reads_body": "Controller body read",
    "semantic_auto_approval": "replaced semantic gate approval",
    "missing_default_progress_status": "without default progress status",
    "missing_progress_prompt": "without shared progress prompt",
    "progress_status_grants_output_dir": "progress visibility was wider than status metadata",
    "progress_status_leaks_body": "progress status leaked sealed body content",
    "progress_update_manual_write": "progress update bypassed runtime",
    "progress_value_nonnumeric": "progress value was not nonnegative numeric",
    "progress_used_as_semantic_decision": "progress was used as semantic decision evidence",
    "missing_quality_pack_check": "omitted declared quality-pack checks",
    "pack_specific_runtime_judgment": "judged quality-pack semantics",
}

REQUIRED_OUTPUT_TYPES = {
    "pm_resume_recovery_decision",
    "pm_control_blocker_repair_decision",
    "gate_decision",
    "reviewer_review_report",
    "officer_model_report",
}

REQUIRED_CONTRACT_IDS = {
    "flowpilot.output_contract.pm_resume_decision.v1",
    "flowpilot.output_contract.pm_control_blocker_repair_decision.v1",
    "flowpilot.output_contract.gate_decision.v1",
    "flowpilot.output_contract.reviewer_review_report.v1",
    "flowpilot.output_contract.officer_model_report.v1",
}

ROLE_CARDS = (
    "skills/flowpilot/assets/runtime_kit/cards/roles/project_manager.md",
    "skills/flowpilot/assets/runtime_kit/cards/roles/human_like_reviewer.md",
    "skills/flowpilot/assets/runtime_kit/cards/roles/process_flowguard_officer.md",
    "skills/flowpilot/assets/runtime_kit/cards/roles/product_flowguard_officer.md",
    "skills/flowpilot/assets/runtime_kit/cards/roles/worker_a.md",
    "skills/flowpilot/assets/runtime_kit/cards/roles/worker_b.md",
)


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|output={state.output_type}|"
        f"role={state.submitting_role}->{state.allowed_role}|"
        f"runtime={state.runtime_receipt_written}|hash={state.body_hash_verified}|"
        f"progress={state.runtime_progress_status_initialized},{state.progress_prompt_included},"
        f"{state.progress_visibility_grant},{state.progress_updates_runtime_written},"
        f"{state.progress_value_numeric},{state.progress_message_metadata_only}|"
        f"router={state.router_decision}:{state.router_rejection_reason}|lane={state.repair_lane}"
    )


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
    labels = set(graph["labels"])
    states: list[model.State] = graph["states"]
    terminals = [state for state in states if model.is_terminal(state)]
    accepted = [state for state in terminals if state.status == "accepted"]
    rejected = [state for state in terminals if state.status == "rejected"]
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and len(accepted) == len(model.VALID_SCENARIOS)
        and len(rejected) == len(model.NEGATIVE_SCENARIOS),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "accepted_state_count": len(accepted),
        "rejected_state_count": len(rejected),
        "missing_labels": missing_labels,
        "invariant_failure_count": len(graph["invariant_failures"]),
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
            if source not in can_reach_terminal and any(target in can_reach_terminal for target in targets):
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
    ok = True
    cases: dict[str, str] = {}
    failures: list[str] = []
    for name, state in model.hazard_states().items():
        invariant_failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in invariant_failures)
        cases[name] = "detected" if detected else "missed"
        if not detected:
            ok = False
            failures.append(f"{name}: expected invariant failure containing {expected!r}")
    return {"ok": ok, "cases": cases, "failures": failures}


def _contract_ids(project_root: Path) -> set[str]:
    path = project_root / "skills/flowpilot/assets/runtime_kit/contracts/contract_index.json"
    if not path.exists():
        return set()
    payload = json.loads(path.read_text(encoding="utf-8"))
    contracts = payload.get("contracts") if isinstance(payload, dict) else []
    return {str(item.get("contract_id")) for item in contracts if isinstance(item, dict)}


def _source_report(project_root: Path) -> dict[str, object]:
    failures: list[str] = []
    assets = project_root / "skills/flowpilot/assets"
    runtime_path = assets / "role_output_runtime.py"
    asset_unified_runtime_path = assets / "flowpilot_runtime.py"
    wrapper_path = project_root / "scripts/flowpilot_outputs.py"
    unified_wrapper_path = project_root / "scripts/flowpilot_runtime.py"
    quality_pack_catalog_path = assets / "runtime_kit/quality_pack_catalog.json"
    if not runtime_path.exists():
        failures.append("skills/flowpilot/assets/role_output_runtime.py is missing")
    if not asset_unified_runtime_path.exists():
        failures.append("skills/flowpilot/assets/flowpilot_runtime.py is missing")
    if not wrapper_path.exists():
        failures.append("scripts/flowpilot_outputs.py is missing")
    if not unified_wrapper_path.exists():
        failures.append("scripts/flowpilot_runtime.py is missing")
    if not quality_pack_catalog_path.exists():
        failures.append("skills/flowpilot/assets/runtime_kit/quality_pack_catalog.json is missing")

    contract_ids = _contract_ids(project_root)
    missing_contracts = sorted(REQUIRED_CONTRACT_IDS - contract_ids)
    if missing_contracts:
        failures.append(f"contract registry missing ids: {missing_contracts}")

    missing_card_mentions: list[str] = []
    missing_progress_guidance: list[str] = []
    for rel in ROLE_CARDS:
        path = project_root / rel
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        if "role_output_runtime.py" not in text:
            missing_card_mentions.append(rel)
        if "progress_status" not in text:
            missing_progress_guidance.append(rel)
    if missing_card_mentions:
        failures.append(f"role cards missing role_output_runtime.py guidance: {missing_card_mentions}")
    if missing_progress_guidance:
        failures.append(f"role cards missing role-output progress guidance: {missing_progress_guidance}")

    output_catalog = project_root / "skills/flowpilot/assets/runtime_kit/cards/phases/pm_output_contract_catalog.md"
    catalog_text = output_catalog.read_text(encoding="utf-8") if output_catalog.exists() else ""
    if "progress_status" not in catalog_text:
        failures.append("PM output contract catalog missing role-output progress_status guidance")

    runtime_output_types: set[str] = set()
    if runtime_path.exists():
        runtime_text = runtime_path.read_text(encoding="utf-8")
        if "def update_output_progress" not in runtime_text:
            failures.append("role_output_runtime missing update_output_progress")
        if "progress_written_by_runtime" not in runtime_text:
            failures.append("role_output_runtime missing runtime-written progress marker")
        if str(assets) not in sys.path:
            sys.path.insert(0, str(assets))
        try:
            runtime = importlib.import_module("role_output_runtime")
            supported = getattr(runtime, "SUPPORTED_OUTPUT_TYPES", set())
            runtime_output_types = {str(item) for item in supported}
            missing_types = sorted(REQUIRED_OUTPUT_TYPES - runtime_output_types)
            if missing_types:
                failures.append(f"role_output_runtime missing output types: {missing_types}")
            if not hasattr(runtime, "quality_pack_checks_for_run"):
                failures.append("role_output_runtime missing generic quality_pack_checks support")
        except Exception as exc:  # pragma: no cover - diagnostic script
            failures.append(f"role_output_runtime import failed: {exc!r}")

    if asset_unified_runtime_path.exists():
        asset_wrapper_text = asset_unified_runtime_path.read_text(encoding="utf-8")
        if "progress-output" not in asset_wrapper_text:
            failures.append("unified flowpilot_runtime missing progress-output command")

    return {
        "ok": not failures,
        "failures": failures,
        "facts": {
            "runtime_path_exists": runtime_path.exists(),
            "asset_unified_runtime_path_exists": asset_unified_runtime_path.exists(),
            "wrapper_path_exists": wrapper_path.exists(),
            "unified_wrapper_path_exists": unified_wrapper_path.exists(),
            "quality_pack_catalog_path_exists": quality_pack_catalog_path.exists(),
            "contract_ids_present": sorted(REQUIRED_CONTRACT_IDS & contract_ids),
            "runtime_output_types": sorted(runtime_output_types),
        },
    }


def _pass_fail(ok: bool) -> str:
    return "pass" if ok else "fail"


def run_checks(*, include_source: bool = True) -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    hazards = _hazard_report()
    explorer = _flowguard_report()
    source = _source_report(PROJECT_ROOT) if include_source else {
        "ok": True,
        "skipped": "model-only mode skips current source scan",
    }
    ok = all(bool(check["ok"]) for check in (safe_graph, progress, hazards, explorer, source))
    result: dict[str, object] = {
        "ok": ok,
        "checks": {
            "safe_graph": _pass_fail(bool(safe_graph["ok"])),
            "progress": _pass_fail(bool(progress["ok"])),
            "hazard_invariants": _pass_fail(bool(hazards["ok"])),
            "flowguard_explorer": _pass_fail(bool(explorer["ok"])),
            "current_source": _pass_fail(bool(source["ok"])),
        },
        "counts": {
            "states": safe_graph["state_count"],
            "edges": safe_graph["edge_count"],
            "accepted": safe_graph["accepted_state_count"],
            "rejected": safe_graph["rejected_state_count"],
        },
        "source": source,
        "skipped_checks": {
            "semantic_sufficiency": (
                "skipped_with_reason: role_output_runtime is a mechanical "
                "submission runtime; PM/reviewer/officer gates own semantics"
            )
        },
    }
    if not ok:
        result["failure_details"] = {
            "safe_graph": safe_graph,
            "progress": progress,
            "hazards": hazards,
            "flowguard_explorer": explorer,
            "source": source,
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-only", action="store_true")
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args()

    result = run_checks(include_source=not args.model_only)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
