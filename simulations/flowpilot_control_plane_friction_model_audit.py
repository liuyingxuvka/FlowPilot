"""Read-only live/source audit for the current control-plane friction model."""

from __future__ import annotations

import ast
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ASSETS_ROOT = Path(__file__).resolve().parents[1] / "skills" / "flowpilot" / "assets"
if str(ASSETS_ROOT) not in sys.path:
    sys.path.insert(0, str(ASSETS_ROOT))

from flowpilot_core_runtime import control_surface  # noqa: E402
from flowpilot_control_plane_friction_model_hazards import _safe_base  # noqa: E402
from flowpilot_control_plane_friction_model_invariants import invariant_failures  # noqa: E402


CURRENT_ORDINARY_PACKET_FAMILIES = frozenset(
    {
        "research",
        "pm_role_work",
        "pm_role_work_request",
        "current_node",
        "task",
        "flowguard_check",
        "flowguard_operator_request",
        "review",
    }
)
RETIRED_MATERIAL_PACKET_FAMILIES = frozenset(
    {"material_scan", "material_sufficiency", "material_understanding"}
)
RETIRED_MATERIAL_EVENT_NAMES = frozenset(
    {
        "pm_issues_material_and_capability_scan_packets",
        "reviewer_reports_material_sufficient",
        "reviewer_reports_material_insufficient",
        "pm_records_material_scan_result_disposition",
        "pm_writes_material_understanding",
    }
)
RETIRED_MATERIAL_ACTION_TYPES = frozenset(
    {
        "relay_material_scan_packets",
        "relay_material_scan_results_to_pm",
        "deliver_material_sufficiency_card",
        "open_material_scan_packet",
        "open_material_sufficiency_review",
    }
)


def _portableize(value: Any, root: Path) -> Any:
    if isinstance(value, dict):
        return {key: _portableize(item, root) for key, item in value.items()}
    if isinstance(value, list):
        return [_portableize(item, root) for item in value]
    if isinstance(value, tuple):
        return tuple(_portableize(item, root) for item in value)
    if isinstance(value, str):
        portable = value
        for prefix in {str(root.resolve()), root.resolve().as_posix()}:
            portable = portable.replace(prefix, ".")
        return portable
    return value


def _read_json(path: Path) -> tuple[Any, str | None]:
    result = control_surface.safe_read_json(path)
    if result.ok:
        return result.value, None
    return None, result.message or result.error_code


def _read_text(path: Path) -> tuple[str, str | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except FileNotFoundError:
        return "", f"missing file: {path.as_posix()}"
    except UnicodeDecodeError as exc:
        return "", f"invalid UTF-8 in {path.as_posix()}: {exc}"


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _router_flags(router_state: object) -> dict[str, Any]:
    if not isinstance(router_state, dict):
        return {}
    for key in ("state_flags", "flags"):
        flags = router_state.get(key)
        if isinstance(flags, dict):
            return flags
    return {}


def _json_contains(data: object, needle: str) -> bool:
    if not needle:
        return False
    try:
        return needle in json.dumps(data, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        return False


def _background_running_projection_ids(snapshot: object) -> list[str]:
    if not isinstance(snapshot, dict):
        return []
    raw_entries = snapshot.get("background_running_index_entries")
    if raw_entries is None and isinstance(snapshot.get("authority"), dict):
        raw_entries = snapshot["authority"].get("background_running_index_entries")
    values: list[str] = []
    if isinstance(raw_entries, list):
        for item in raw_entries:
            if isinstance(item, dict) and item.get("run_id"):
                values.append(str(item["run_id"]))
            elif isinstance(item, str):
                values.append(item)
    return values


def _snapshot_authority(snapshot: object) -> dict[str, object]:
    if not isinstance(snapshot, dict):
        return {}
    authority = snapshot.get("authority")
    return authority if isinstance(authority, dict) else {}


def _snapshot_active_catalog(snapshot: object) -> dict[str, object]:
    if not isinstance(snapshot, dict):
        return {}
    catalog = snapshot.get("active_ui_task_catalog")
    return catalog if isinstance(catalog, dict) else {}


def _target_run_ids(catalog: dict[str, object]) -> set[str]:
    operation_targets = catalog.get("operation_targets")
    if not isinstance(operation_targets, dict):
        return set()
    single_targets = operation_targets.get("single_targets")
    if not isinstance(single_targets, list):
        return set()
    return {
        str(item["run_id"])
        for item in single_targets
        if isinstance(item, dict) and item.get("run_id") and item.get("target_id")
    }


def _active_set_authority_is_explicit(
    snapshot: object,
    *,
    non_current_running_entries: list[str],
    missing_background_projection: list[str],
) -> bool:
    if not non_current_running_entries:
        return True
    if missing_background_projection:
        return False
    authority = _snapshot_authority(snapshot)
    catalog = _snapshot_active_catalog(snapshot)
    background = catalog.get("background_active_tasks")
    background_ids = {
        str(item["run_id"])
        for item in background
        if isinstance(item, dict)
        and item.get("run_id")
        and item.get("target_id")
        and item.get("operation_target_allowed") is True
    } if isinstance(background, list) else set()
    expected = set(non_current_running_entries)
    return bool(
        authority.get("current_pointer_is_ui_focus_only") is True
        and authority.get("index_running_entries_are_parallel_run_authority") is True
        and authority.get("global_main_required") is False
        and authority.get("operation_target_required") is True
        and catalog.get("authority") == "explicit_active_set"
        and expected.issubset(background_ids)
        and expected.issubset(_target_run_ids(catalog))
    )


def _active_set_authority_snapshot_from_index(
    *,
    current: object,
    index: object,
    current_run_id: str,
) -> dict[str, object] | None:
    if not isinstance(current, dict) or not isinstance(index, dict):
        return None
    entries = index.get("runs")
    if not isinstance(entries, list):
        return None
    running = [
        {
            "run_id": str(item["run_id"]),
            "target_id": f"run:{item['run_id']}",
            "status": "running",
            "operation_target_allowed": True,
        }
        for item in entries
        if isinstance(item, dict)
        and item.get("status") == "running"
        and item.get("run_id")
    ]
    if not running:
        return None
    if current_run_id not in {item["run_id"] for item in running}:
        running.insert(
            0,
            {
                "run_id": current_run_id,
                "target_id": f"run:{current_run_id}",
                "status": str(current.get("status") or current.get("lifecycle_state") or "focused"),
                "operation_target_allowed": True,
            },
        )
    background = [item for item in running if item["run_id"] != current_run_id]
    single_targets = [
        {"run_id": item["run_id"], "target_id": item["target_id"]}
        for item in running
    ]
    all_ids = [item["run_id"] for item in running]
    return {
        "authority": {
            "current_pointer_is_ui_focus_only": True,
            "index_running_entries_are_parallel_run_authority": True,
            "global_main_required": False,
            "operation_target_required": True,
            "background_running_index_entries": background,
        },
        "active_ui_task_catalog": {
            "authority": "explicit_active_set",
            "global_main_required": False,
            "operation_target_required": True,
            "current_focus": current_run_id,
            "background_active_tasks": background,
            "operation_targets": {
                "single_targets": single_targets,
                "all_active": {"target_scope": "all_active", "run_ids": all_ids},
            },
        },
    }


def _external_event_contracts_from_source(
    source_path: Path,
) -> tuple[dict[str, dict[str, str]], str | None]:
    source, error = _read_text(source_path)
    if error:
        return {}, error
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return {}, f"external event source unparsable: {exc}"
    contracts: dict[str, dict[str, str]] = {}
    for node in tree.body:
        value: ast.AST | None = None
        names: list[str] = []
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names = [node.target.id]
            value = node.value
        elif isinstance(node, ast.Assign):
            names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            value = node.value
        if value is None or not any(
            name == "EXTERNAL_EVENTS"
            or name == "EXTERNAL_EVENT_DATA_BY_PHASE"
            or name.endswith("_EXTERNAL_EVENT_DATA")
            for name in names
        ):
            continue
        try:
            payload = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            continue
        if not isinstance(payload, dict):
            continue
        if payload and all(isinstance(item, dict) for item in payload.values()):
            first = next(iter(payload.values()))
            if isinstance(first, dict) and first and all(isinstance(item, dict) for item in first.values()):
                flattened: dict[str, object] = {}
                for phase in payload.values():
                    if isinstance(phase, dict):
                        flattened.update(phase)
                payload = flattened
        for event_name, metadata in payload.items():
            if isinstance(event_name, str) and isinstance(metadata, dict):
                contracts[event_name] = {
                    str(key): str(item)
                    for key, item in metadata.items()
                    if isinstance(item, str)
                }
    return contracts, None if contracts else "external event definition not found"


def _router_external_event_contracts(
    source_root: Path,
) -> tuple[dict[str, dict[str, str]], str | None]:
    asset_root = source_root / "skills" / "flowpilot" / "assets"
    contracts: dict[str, dict[str, str]] = {}
    errors: list[str] = []
    for source_path in sorted(asset_root.glob("flowpilot_router_protocol_external_event_data*.py")):
        rows, error = _external_event_contracts_from_source(source_path)
        contracts.update(rows)
        if error and not rows:
            errors.append(f"{source_path.name}: {error}")
    if contracts:
        return contracts, None
    return {}, "; ".join(errors) if errors else "EXTERNAL_EVENTS definition not found"


def _dict_literal_values_for_key(source_path: Path, key_name: str) -> set[str]:
    source, error = _read_text(source_path)
    if error:
        return set()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    values: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if (
                isinstance(key, ast.Constant)
                and key.value == key_name
                and isinstance(value, ast.Constant)
                and isinstance(value.value, str)
            ):
                values.add(value.value)
    return values


def _packet_rows(packet_ledger: object) -> list[dict[str, object]]:
    if not isinstance(packet_ledger, dict):
        return []
    raw = packet_ledger.get("packets")
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        return [item for item in raw.values() if isinstance(item, dict)]
    return []


def _packet_family(packet: dict[str, object]) -> str:
    envelope = packet.get("envelope")
    envelope = envelope if isinstance(envelope, dict) else {}
    return str(
        packet.get("packet_family")
        or packet.get("packet_type")
        or envelope.get("packet_family")
        or envelope.get("packet_type")
        or ""
    )


def _audit_ordinary_work_dispatch_integrity(
    *,
    project_root: Path,
    run_root: Path,
    router_state: object | None = None,
    frontier: object | None = None,
) -> dict[str, object]:
    del project_root, router_state, frontier
    packet_ledger, error = _read_json(run_root / "packet_ledger.json")
    details: list[dict[str, object]] = []
    retired: list[dict[str, object]] = []
    ordinary: list[dict[str, object]] = []
    for packet in _packet_rows(packet_ledger):
        family = _packet_family(packet)
        if family not in CURRENT_ORDINARY_PACKET_FAMILIES | RETIRED_MATERIAL_PACKET_FAMILIES:
            continue
        envelope = packet.get("envelope")
        envelope = envelope if isinstance(envelope, dict) else {}
        output_contract = packet.get("output_contract") or envelope.get("output_contract")
        result_path = (
            packet.get("result_body_path")
            or envelope.get("result_body_path")
            or (output_contract.get("expected_result_body_path") if isinstance(output_contract, dict) else None)
        )
        current_scope = bool(packet.get("packet_id") or envelope.get("packet_id"))
        contract_valid = isinstance(output_contract, dict) and bool(output_contract)
        write_target = isinstance(result_path, str) and bool(result_path)
        detail = {
            "packet_id": packet.get("packet_id") or envelope.get("packet_id"),
            "packet_family": family,
            "current_scope": current_scope,
            "output_contract_valid": contract_valid,
            "write_target_explicit": write_target,
        }
        details.append(detail)
        if family in RETIRED_MATERIAL_PACKET_FAMILIES:
            retired.append(detail)
        else:
            ordinary.append(detail)
    current_scope_ok = all(bool(item["current_scope"]) for item in ordinary)
    contract_ok = all(bool(item["output_contract_valid"]) for item in ordinary)
    write_target_ok = all(bool(item["write_target_explicit"]) for item in ordinary)
    requested = bool(details)
    reviewed = error is None
    allowed = bool(
        reviewed
        and not retired
        and current_scope_ok
        and contract_ok
        and write_target_ok
    )
    return {
        "requested": requested,
        "reviewed": reviewed,
        "allowed": allowed,
        "packet_ledger_error": error,
        "current_scope_consistent": current_scope_ok,
        "output_contract_consistent": contract_ok,
        "write_target_explicit": write_target_ok,
        "retired_surface_absent": not retired,
        "ordinary_packet_details": ordinary,
        "retired_packet_details": retired,
        "packet_details": details,
    }


def audit_retired_material_surfaces(source_root: str | Path = ".") -> dict[str, object]:
    """Prove that retired material protocols have no active registry authority."""

    source = Path(source_root).resolve()
    asset_root = source / "skills" / "flowpilot" / "assets"
    contracts, event_error = _router_external_event_contracts(source)
    retired_events = sorted(RETIRED_MATERIAL_EVENT_NAMES.intersection(contracts))
    action_values: set[str] = set()
    action_sources: dict[str, list[str]] = {}
    for path in sorted(asset_root.glob("flowpilot_router_*.py")):
        values = _dict_literal_values_for_key(path, "action_type")
        hits = sorted(RETIRED_MATERIAL_ACTION_TYPES.intersection(values))
        if hits:
            action_sources[path.relative_to(source).as_posix()] = hits
            action_values.update(hits)
    contract_index, contract_error = _read_json(
        asset_root / "runtime_kit" / "contracts" / "contract_index.json"
    )
    packet_families: set[str] = set()
    if isinstance(contract_index, dict):
        rows = contract_index.get("contracts")
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict):
                    family = str(row.get("packet_type") or row.get("packet_family") or "")
                    if family in RETIRED_MATERIAL_PACKET_FAMILIES:
                        packet_families.add(family)
    ok = not retired_events and not action_values and not packet_families
    return {
        "ok": ok,
        "retired_events": retired_events,
        "retired_actions": sorted(action_values),
        "retired_action_sources": action_sources,
        "retired_packet_families": sorted(packet_families),
        "event_registry_error": event_error,
        "contract_index_error": contract_error,
        "claim_boundary": (
            "Checks active external-event registries, Router action_type literals, and the "
            "current runtime contract index; historical labels and negative tests are outside authority."
        ),
    }


def _add_finding(
    findings: list[dict[str, object]],
    *,
    code: str,
    severity: str,
    summary: str,
    invariant: str,
    evidence: object,
) -> None:
    findings.append(
        {
            "code": code,
            "severity": severity,
            "summary": summary,
            "matched_invariant": invariant,
            "evidence": evidence,
        }
    )


def audit_live_run(
    project_root: str | Path = ".",
    *,
    source_root: str | Path | None = None,
) -> dict[str, object]:
    """Project the current run into generic dispatch/result/join/repair gates."""

    root = Path(project_root).resolve()
    source = Path(source_root).resolve() if source_root is not None else root
    resolution = control_surface.resolve_current_run(root)
    current, current_error = _read_json(root / ".flowpilot" / "current.json")
    if not resolution.ok:
        missing = resolution.error_code == "missing_file"
        return _portableize({
            "ok": missing,
            "skipped": missing,
            "skip_reason": (
                "skipped_with_reason: .flowpilot/current.json is missing; no current live-run audit can be claimed"
                if missing
                else None
            ),
            "run_id": resolution.run_id,
            "run_root": resolution.run_root.as_posix() if resolution.run_root else "",
            "finding_count": 0 if missing else 1,
            "error_count": 0 if missing else 1,
            "warning_count": 0,
            "findings": [] if missing else [resolution.finding()],
            "current_run_projection": {
                "status": "missing_current_pointer" if missing else "invalid_current_pointer",
                "current_run_can_continue": False,
                "safe_to_claim_live_run_confidence": False,
                "metadata_only": True,
            },
            "projected_invariant_failures": [],
        }, root)
    if not isinstance(current, dict):
        return _portableize({
            "ok": False,
            "skipped": False,
            "finding_count": 1,
            "error_count": 1,
            "warning_count": 0,
            "findings": [
                {
                    "code": "current_pointer_unreadable",
                    "severity": "error",
                    "summary": "current.json did not contain a JSON object",
                    "matched_invariant": "live_run_pointer_readable",
                    "evidence": {"read_error": current_error},
                }
            ],
            "projected_invariant_failures": [],
        }, root)

    run_root = resolution.run_root
    assert run_root is not None
    run_id = str(resolution.run_id or current.get("run_id") or "")
    findings: list[dict[str, object]] = []
    evidence_files = {
        "router_state": run_root / "router_state.json",
        "prompt_delivery_ledger": run_root / "prompt_delivery_ledger.json",
        "execution_frontier": run_root / "execution_frontier.json",
        "route_state_snapshot": run_root / "route_state_snapshot.json",
        "display_plan": run_root / "display_plan.json",
        "index": root / ".flowpilot" / "index.json",
        "runtime_ledger": run_root / "ledger.json",
        "packet_ledger": run_root / "packet_ledger.json",
    }
    evidence: dict[str, object] = {}
    for name, path in evidence_files.items():
        payload, error = _read_json(path)
        evidence[name] = payload
        if error and not error.startswith("missing file:"):
            _add_finding(
                findings,
                code="control_surface_evidence_unreadable",
                severity="error",
                summary=f"{name} could not be read as structured JSON",
                invariant="evidence_reads_are_structured",
                evidence={"path": path.as_posix(), "read_error": error},
            )

    runtime_ledger = evidence["runtime_ledger"]
    if isinstance(runtime_ledger, dict):
        findings.extend(control_surface.audit_packet_contracts(runtime_ledger))

    dispatch = _audit_ordinary_work_dispatch_integrity(
        project_root=root,
        run_root=run_root,
        router_state=evidence["router_state"],
        frontier=evidence["execution_frontier"],
    )
    if dispatch["retired_packet_details"]:
        _add_finding(
            findings,
            code="retired_material_packet_family_active",
            severity="error",
            summary="a retired material-specific packet family retained current dispatch authority",
            invariant="ordinary_work_dispatch_requires_current_contract",
            evidence=dispatch,
        )
    if dispatch["ordinary_packet_details"] and not dispatch["allowed"]:
        _add_finding(
            findings,
            code="ordinary_work_dispatch_contract_incomplete",
            severity="error",
            summary="ordinary work dispatch lacked current scope, output contract, or result write target",
            invariant="ordinary_work_dispatch_requires_current_contract",
            evidence=dispatch,
        )

    source_absence = audit_retired_material_surfaces(source)
    if not source_absence["ok"]:
        _add_finding(
            findings,
            code="retired_material_source_authority_active",
            severity="error",
            summary="retired material-specific event, action, or packet-family authority remained active",
            invariant="ordinary_work_dispatch_requires_current_contract",
            evidence=source_absence,
        )

    packet_rows = _packet_rows(evidence["packet_ledger"])
    packet_ids = {
        str(packet.get("packet_id") or (packet.get("envelope") or {}).get("packet_id") or "")
        for packet in packet_rows
        if isinstance(packet, dict)
    }
    router_state = evidence["router_state"]
    active_blocker = router_state.get("active_control_blocker") if isinstance(router_state, dict) else None
    if isinstance(active_blocker, dict):
        target_packet = str(
            active_blocker.get("target_packet_id")
            or active_blocker.get("source_packet_id")
            or ""
        )
        if target_packet and target_packet not in packet_ids:
            _add_finding(
                findings,
                code="active_blocker_targets_noncurrent_packet",
                severity="error",
                summary="current repair blocker targeted a packet absent from the current packet ledger",
                invariant="current_repair_targets_stay_on_current_packets",
                evidence={"target_packet_id": target_packet, "current_packet_ids": sorted(packet_ids)},
            )

    stopped = str(
        current.get("terminal_lifecycle_status")
        or current.get("lifecycle_state")
        or current.get("status")
        or ""
    ) in {"stopped_by_user", "complete", "failed", "cancelled"}
    flags = _router_flags(router_state)
    active_authority = bool(
        flags.get("manual_resume_binding_active")
        or flags.get("runtime_role_live_agents_active")
        or flags.get("packet_loop_active")
    )
    if stopped and active_authority:
        _add_finding(
            findings,
            code="terminal_lifecycle_left_active_authority",
            severity="error",
            summary="terminal lifecycle retained resume, role, or packet-loop authority",
            invariant="stopped_run_reconciles_authorities",
            evidence={"lifecycle": current, "active_flags": flags},
        )

    index = evidence["index"]
    non_current_running = [
        str(item["run_id"])
        for item in (index.get("runs") if isinstance(index, dict) else []) or []
        if isinstance(item, dict)
        and item.get("status") == "running"
        and item.get("run_id") != run_id
    ]
    snapshot = evidence["route_state_snapshot"]
    background = _background_running_projection_ids(snapshot)
    missing_background = sorted(set(non_current_running) - set(background))
    authority_source = "stored_snapshot"
    explicit_authority = _active_set_authority_is_explicit(
        snapshot,
        non_current_running_entries=non_current_running,
        missing_background_projection=missing_background,
    )
    if not explicit_authority:
        synthesized = _active_set_authority_snapshot_from_index(
            current=current,
            index=index,
            current_run_id=run_id,
        )
        if synthesized is not None:
            synthesized_background = _background_running_projection_ids(synthesized)
            synthesized_missing = sorted(set(non_current_running) - set(synthesized_background))
            if _active_set_authority_is_explicit(
                synthesized,
                non_current_running_entries=non_current_running,
                missing_background_projection=synthesized_missing,
            ):
                explicit_authority = True
                authority_source = "read_only_index_synthesis"
                missing_background = synthesized_missing
    if missing_background:
        _add_finding(
            findings,
            code="non_current_runs_missing_background_projection",
            severity="warning",
            summary="non-current running entries lacked explicit background active-set authority",
            invariant="multi_active_requires_explicit_authority",
            evidence={"missing_run_ids": missing_background},
        )

    dispatch_family = (
        "material_scan"
        if dispatch["retired_packet_details"] or not source_absence["ok"]
        else "pm_role_work"
    )
    projected_state = _safe_base(
        ordinary_work_dispatch_requested=bool(dispatch["requested"]),
        ordinary_work_dispatch_reviewed=bool(dispatch["reviewed"]),
        ordinary_work_dispatch_allowed=bool(dispatch["allowed"]),
        ordinary_work_dispatch_family=dispatch_family,
        ordinary_work_dispatch_current_scope=bool(dispatch["current_scope_consistent"]),
        ordinary_work_dispatch_output_contract_valid=bool(dispatch["output_contract_consistent"]),
        ordinary_work_dispatch_write_target_explicit=bool(dispatch["write_target_explicit"]),
        current_status_stopped=stopped,
        manual_resume_binding_active=bool(stopped and flags.get("manual_resume_binding_active")),
        runtime_role_live_agents_active=bool(stopped and flags.get("runtime_role_live_agents_active")),
        packet_loop_active=bool(stopped and flags.get("packet_loop_active")),
        frontier_terminal=stopped,
        multiple_running_index_entries_visible=bool(non_current_running),
        active_task_authority="explicit_active_set" if explicit_authority else "current_focus_only",
    )
    projected_failures = invariant_failures(projected_state)
    error_count = sum(1 for finding in findings if finding.get("severity") == "error")
    try:
        run_root_value = run_root.relative_to(root).as_posix()
    except ValueError:
        run_root_value = run_root.as_posix()
    return _portableize({
        "ok": error_count == 0 and not projected_failures,
        "skipped": False,
        "run_id": run_id,
        "run_root": run_root_value,
        "finding_count": len(findings),
        "error_count": error_count,
        "warning_count": sum(1 for finding in findings if finding.get("severity") == "warning"),
        "findings": findings,
        "ordinary_work_dispatch": dispatch,
        "retired_material_surface_absence": source_absence,
        "projected_state": projected_state.__dict__,
        "projected_invariant_failures": projected_failures,
        "active_set_authority_source": authority_source,
        "current_run_projection": {
            "status": "terminal" if stopped else "current",
            "current_run_can_continue": not stopped and error_count == 0,
            "safe_to_claim_live_run_confidence": error_count == 0 and not projected_failures,
            "metadata_only": False,
        },
    }, root)


__all__ = [
    "audit_live_run",
    "audit_retired_material_surfaces",
]
