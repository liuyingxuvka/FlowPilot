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
    "select_valid_startup_activation_approval",
    "select_valid_gate_decision",
    "select_valid_reviewer_report",
    "select_valid_controller_boundary_confirmation",
    "select_missing_registry_runtime_binding",
    "select_registry_contract_id_mismatch",
    "select_registry_allowed_role_mismatch",
    "select_registry_router_event_missing",
    "select_unregistered_runtime_output_type",
    "select_broken_compat_output_alias",
    "select_missing_runtime_receipt",
    "select_missing_required_field",
    "select_missing_explicit_empty_array",
    "select_wrong_role",
    "select_stale_body_hash",
    "select_inline_body_leak",
    "select_controller_reads_body",
    "select_controller_intermediates_output",
    "select_semantic_auto_approval",
    "select_missing_quality_pack_check",
    "select_pack_specific_runtime_judgment",
    "runtime_prepares_contract_skeleton",
    "role_authors_body_inside_runtime_skeleton",
    "runtime_validates_writes_receipt_and_envelope",
    "runtime_submits_role_output_directly_to_router",
    "router_accepts_runtime_checked_role_output",
    "router_rejects_missing_registry_runtime_binding",
    "router_rejects_registry_contract_id_mismatch",
    "router_rejects_registry_allowed_role_mismatch",
    "router_rejects_registry_router_event_missing",
    "router_rejects_unregistered_runtime_output_type",
    "router_rejects_broken_compat_output_alias",
    "router_rejects_missing_runtime_receipt",
    "router_rejects_missing_required_field",
    "router_rejects_missing_explicit_empty_array",
    "router_rejects_wrong_role",
    "router_rejects_stale_body_hash",
    "router_rejects_inline_body_leak",
    "router_rejects_controller_read_body",
    "router_rejects_controller_intermediated_output",
    "router_rejects_runtime_attempted_semantic_approval",
    "router_rejects_missing_quality_pack_check",
    "router_rejects_runtime_attempted_pack_specific_judgment",
)

HAZARD_EXPECTED_FAILURES = {
    "missing_registry_runtime_binding": "without registry runtime binding",
    "registry_contract_id_mismatch": "registry/runtime contract id mismatch",
    "registry_allowed_role_mismatch": "registry/runtime allowed role mismatch",
    "registry_router_event_missing": "missing Router event binding",
    "unregistered_runtime_output_type": "not declared by registry",
    "broken_compat_output_alias": "broken compatibility output alias",
    "missing_runtime_receipt": "without runtime receipt",
    "missing_required_field": "missing required field",
    "missing_explicit_empty_array": "missing explicit empty array",
    "wrong_role": "wrong role",
    "stale_body_hash": "stale body hash",
    "inline_body_leak": "leaked body content",
    "controller_reads_body": "Controller body read",
    "controller_intermediates_output": "routed through Controller",
    "missing_direct_router_submission": "without direct Router submission",
    "missing_router_receipt": "was not received by Router",
    "controller_waits_role_instead_of_router": "left Controller waiting on a role instead of Router",
    "router_ready_next_action_waited_on_role": "Router-ready evidence unconsumed before foreground wait",
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
    "controller_boundary_confirmation",
}

REQUIRED_CONTRACT_IDS = {
    "flowpilot.output_contract.pm_resume_decision.v1",
    "flowpilot.output_contract.pm_control_blocker_repair_decision.v1",
    "flowpilot.output_contract.gate_decision.v1",
    "flowpilot.output_contract.reviewer_review_report.v1",
    "flowpilot.output_contract.officer_model_report.v1",
    "flowpilot.output_contract.controller_boundary_confirmation.v1",
}

REGISTRY_BINDING_REQUIRED_FIELDS = {
    "runtime_channel",
    "output_type",
    "body_schema_version",
    "expected_return_envelope",
    "default_subdir",
    "default_filename_prefix",
    "path_key",
    "hash_key",
    "router_event_mode",
}

ROUTER_EVENT_MODES = {"fixed", "router_supplied"}

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
        f"registry={state.registry_runtime_binding_present},"
        f"{state.registry_contract_id_matches_runtime},"
        f"{state.registry_allowed_roles_match_runtime},"
        f"{state.registry_router_event_exists},"
        f"{state.runtime_output_type_declared_by_registry},"
        f"{state.compat_output_alias_valid}|"
        f"runtime={state.runtime_receipt_written}|hash={state.body_hash_verified}|"
        f"direct_router={state.direct_router_submission},{state.router_receives_role_output_envelope},"
        f"{state.controller_waits_router_status}|router_ready="
        f"{state.router_ready_evidence_available},"
        f"{state.controller_reentered_router_before_foreground_wait},"
        f"{state.controller_foreground_waits_role_after_router_ready}|"
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


def _registry_contracts(project_root: Path) -> list[dict[str, Any]]:
    path = project_root / "skills/flowpilot/assets/runtime_kit/contracts/contract_index.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    contracts = payload.get("contracts") if isinstance(payload, dict) else []
    return [item for item in contracts if isinstance(item, dict)]


def _runtime_binding_contracts(contracts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        item
        for item in contracts
        if item.get("runtime_channel") == "role_output_runtime"
        or item.get("expected_return_envelope") == "role_output_envelope"
        or item.get("task_family") == "pm.startup_activation"
    ]


def _runtime_specs(runtime: Any) -> dict[str, Any]:
    specs = getattr(runtime, "OUTPUT_TYPE_SPECS", {})
    if isinstance(specs, dict):
        return specs
    return {}


def _router_events(project_root: Path) -> set[str]:
    assets = project_root / "skills/flowpilot/assets"
    if str(assets) not in sys.path:
        sys.path.insert(0, str(assets))
    try:
        router = importlib.import_module("flowpilot_router")
    except Exception:  # pragma: no cover - diagnostics handle import failure elsewhere
        return set()
    events = getattr(router, "EXTERNAL_EVENTS", {})
    return {str(name) for name in events} if isinstance(events, dict) else set()


def _binding_source_report(project_root: Path, runtime: Any) -> dict[str, object]:
    failures: list[str] = []
    contracts = _registry_contracts(project_root)
    bound_contracts = _runtime_binding_contracts(contracts)
    specs = _runtime_specs(runtime)
    router_events = _router_events(project_root)

    contracts_by_id = {str(item.get("contract_id")): item for item in contracts}
    declared_output_types: set[str] = set()
    declared_aliases: set[str] = set()

    for contract in bound_contracts:
        contract_id = str(contract.get("contract_id") or "")
        missing_fields = sorted(
            field
            for field in REGISTRY_BINDING_REQUIRED_FIELDS
            if contract.get(field) in (None, "", [])
        )
        if missing_fields:
            failures.append(f"{contract_id}: registry binding missing fields {missing_fields}")
            continue

        if contract.get("runtime_channel") != "role_output_runtime":
            failures.append(f"{contract_id}: runtime_channel must be role_output_runtime")
        if contract.get("expected_return_envelope") != "role_output_envelope":
            failures.append(f"{contract_id}: expected_return_envelope must be role_output_envelope")

        event_mode = str(contract.get("router_event_mode") or "")
        if event_mode not in ROUTER_EVENT_MODES:
            failures.append(f"{contract_id}: router_event_mode must be one of {sorted(ROUTER_EVENT_MODES)}")
        if event_mode == "fixed":
            router_event = str(contract.get("router_event") or "")
            if not router_event:
                failures.append(f"{contract_id}: fixed router_event_mode requires router_event")
            elif router_event not in router_events:
                failures.append(f"{contract_id}: router_event {router_event!r} is not handled by Router")

        output_type = str(contract.get("output_type") or "")
        declared_output_types.add(output_type)
        spec = specs.get(output_type)
        if spec is None:
            failures.append(f"{contract_id}: runtime missing output_type {output_type!r}")
        else:
            if getattr(spec, "contract_id", None) != contract_id:
                failures.append(
                    f"{contract_id}: runtime output_type {output_type!r} points at "
                    f"{getattr(spec, 'contract_id', None)!r}"
                )
            if tuple(contract.get("recipient_roles") or ()) != tuple(getattr(spec, "allowed_roles", ())):
                failures.append(f"{contract_id}: runtime allowed_roles differ from registry recipient_roles")
            for attr, field in (
                ("body_schema_version", "body_schema_version"),
                ("default_subdir", "default_subdir"),
                ("default_filename_prefix", "default_filename_prefix"),
                ("path_key", "path_key"),
                ("hash_key", "hash_key"),
            ):
                if getattr(spec, attr, None) != contract.get(field):
                    failures.append(f"{contract_id}: runtime {attr} differs from registry {field}")
            expected_event = contract.get("router_event") if event_mode == "fixed" else None
            if getattr(spec, "event_name", None) != expected_event:
                failures.append(f"{contract_id}: runtime event_name differs from registry router_event binding")

        for alias in contract.get("output_type_aliases") or []:
            alias = str(alias)
            declared_aliases.add(alias)
            alias_spec = specs.get(alias)
            if alias_spec is None:
                failures.append(f"{contract_id}: runtime missing alias output_type {alias!r}")
            elif getattr(alias_spec, "contract_id", None) != contract_id:
                failures.append(f"{contract_id}: alias output_type {alias!r} points at wrong contract")

    declared_contract_ids = {str(item.get("contract_id")) for item in bound_contracts}
    for output_type, spec in specs.items():
        output_type = str(output_type)
        contract_id = str(getattr(spec, "contract_id", ""))
        if contract_id not in contracts_by_id:
            failures.append(f"{output_type}: runtime contract_id {contract_id!r} is absent from registry")
            continue
        if contract_id not in declared_contract_ids:
            failures.append(f"{output_type}: runtime contract {contract_id!r} is not declared runtime-backed")
            continue
        if output_type not in declared_output_types and output_type not in declared_aliases:
            failures.append(f"{output_type}: runtime output_type is not declared by registry or aliases")

    return {
        "ok": not failures,
        "failures": failures,
        "facts": {
            "bound_contract_count": len(bound_contracts),
            "declared_output_types": sorted(declared_output_types),
            "declared_aliases": sorted(declared_aliases),
        },
    }


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
    missing_direct_router_submit_guidance: list[str] = []
    missing_progress_guidance: list[str] = []
    for rel in ROLE_CARDS:
        path = project_root / rel
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        if "flowpilot_runtime.py" not in text:
            missing_card_mentions.append(rel)
        if "submit-output-to-router" not in text:
            missing_direct_router_submit_guidance.append(rel)
        if "progress_status" not in text:
            missing_progress_guidance.append(rel)
    if missing_card_mentions:
        failures.append(f"role cards missing flowpilot_runtime.py guidance: {missing_card_mentions}")
    if missing_direct_router_submit_guidance:
        failures.append(f"role cards missing submit-output-to-router guidance: {missing_direct_router_submit_guidance}")
    if missing_progress_guidance:
        failures.append(f"role cards missing role-output progress guidance: {missing_progress_guidance}")

    output_catalog = project_root / "skills/flowpilot/assets/runtime_kit/cards/phases/pm_output_contract_catalog.md"
    catalog_text = output_catalog.read_text(encoding="utf-8") if output_catalog.exists() else ""
    if "progress_status" not in catalog_text:
        failures.append("PM output contract catalog missing role-output progress_status guidance")
    if "submit-output-to-router" not in catalog_text:
        failures.append("PM output contract catalog missing submit-output-to-router guidance")

    controller_card = project_root / "skills/flowpilot/assets/runtime_kit/cards/roles/controller.md"
    controller_text = controller_card.read_text(encoding="utf-8") if controller_card.exists() else ""
    skill_text = (project_root / "skills/flowpilot/SKILL.md").read_text(encoding="utf-8")
    resume_card = project_root / "skills/flowpilot/assets/runtime_kit/cards/system/controller_resume_reentry.md"
    resume_text = resume_card.read_text(encoding="utf-8") if resume_card.exists() else ""
    required_router_first_snippets = {
        "controller card": (
            controller_text,
            [
                "Router-ready evidence preempts foreground role waits",
                "scan daemon status and the Controller action ledger before",
                "flowpilot_router.py controller-standby",
            ],
        ),
        "skill launcher": (
            skill_text,
            [
                "Router-ready state preempts foreground waits",
                "scan daemon status and the Controller action",
                "controller-standby",
            ],
        ),
        "controller resume reentry card": (
            resume_text,
            [
                "Router-ready evidence still preempts foreground role waits",
                "scan daemon status and clear",
                "controller-standby",
            ],
        ),
    }
    for source_name, (text, snippets) in required_router_first_snippets.items():
        for snippet in snippets:
            if snippet not in text:
                failures.append(f"{source_name} missing Router-ready preemption guidance: {snippet}")

    runtime_output_types: set[str] = set()
    binding_report: dict[str, object] = {
        "ok": False,
        "failures": ["role_output_runtime import did not complete"],
    }
    if runtime_path.exists():
        runtime_text = runtime_path.read_text(encoding="utf-8")
        if "def update_output_progress" not in runtime_text:
            failures.append("role_output_runtime missing update_output_progress")
        if "progress_written_by_runtime" not in runtime_text:
            failures.append("role_output_runtime missing runtime-written progress marker")
        if "\"submitted_to\": \"router\"" not in runtime_text:
            failures.append("role_output_runtime missing direct Router submission envelope marker")
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
            binding_report = _binding_source_report(project_root, runtime)
            if not binding_report["ok"]:
                failures.extend(str(item) for item in binding_report.get("failures", []))
        except Exception as exc:  # pragma: no cover - diagnostic script
            failures.append(f"role_output_runtime import failed: {exc!r}")

    if asset_unified_runtime_path.exists():
        asset_wrapper_text = asset_unified_runtime_path.read_text(encoding="utf-8")
        if "progress-output" not in asset_wrapper_text:
            failures.append("unified flowpilot_runtime missing progress-output command")
        if "submit-output-to-router" not in asset_wrapper_text:
            failures.append("unified flowpilot_runtime missing submit-output-to-router command")

    stale_role_output_prompt_patterns = (
        "return only the Router-directed controller-visible envelope",
        "return to Controller only as a runtime envelope",
        "returns only the compact controller-visible envelope",
        "returned to Controller as envelope-only payloads",
        "All formal cross-role mail goes through Controller",
    )
    stale_hits: list[str] = []
    scan_roots = [
        project_root / "skills/flowpilot/assets/runtime_kit/cards",
        project_root / "skills/flowpilot/references",
        project_root / "templates/flowpilot/packets",
        project_root / "skills/flowpilot/assets/role_output_runtime.py",
    ]
    for scan_root in scan_roots:
        if not scan_root.exists():
            continue
        paths = [scan_root] if scan_root.is_file() else sorted(scan_root.rglob("*.md"))
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for pattern in stale_role_output_prompt_patterns:
                if pattern in text:
                    stale_hits.append(f"{path.relative_to(project_root).as_posix()}: {pattern}")
    if stale_hits:
        failures.append(f"stale Controller role-output return guidance remains: {stale_hits[:20]}")

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
            "binding_report": binding_report,
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
