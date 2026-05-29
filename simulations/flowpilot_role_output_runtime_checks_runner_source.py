"""Current-source checks for the FlowPilot role-output runtime runner."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_OUTPUT_TYPES = {
    "pm_resume_decision",
    "pm_control_blocker_repair_decision",
    "gate_decision",
    "reviewer_review_report",
    "officer_model_report",
    "controller_boundary_confirmation",
    "pm_package_result_disposition",
}


REQUIRED_CONTRACT_IDS = {
    "flowpilot.output_contract.pm_resume_decision.v1",
    "flowpilot.output_contract.pm_control_blocker_repair_decision.v1",
    "flowpilot.output_contract.gate_decision.v1",
    "flowpilot.output_contract.reviewer_review_report.v1",
    "flowpilot.output_contract.officer_model_report.v1",
    "flowpilot.output_contract.controller_boundary_confirmation.v1",
    "flowpilot.output_contract.pm_package_result_disposition.v1",
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
        if output_type not in declared_output_types:
            failures.append(f"{output_type}: runtime output_type is not declared by registry")

    return {
        "ok": not failures,
        "failures": failures,
        "facts": {
            "bound_contract_count": len(bound_contracts),
            "declared_output_types": sorted(declared_output_types),
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
