"""Live-run audit adapter for ``flowpilot_control_plane_friction_model``."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ASSETS_ROOT = Path(__file__).resolve().parents[1] / "skills" / "flowpilot" / "assets"
if str(ASSETS_ROOT) not in sys.path:
    sys.path.insert(0, str(ASSETS_ROOT))

from flowpilot_core_runtime import control_surface  # noqa: E402
from flowpilot_control_plane_friction_model_hazards import _safe_base
from flowpilot_control_plane_friction_model_invariants import invariant_failures
from flowpilot_control_plane_friction_model_state import PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES


def _read_json(path: Path) -> tuple[Any, str | None]:
    result = control_surface.safe_read_json(path)
    if result.ok:
        return result.value, None
    return None, result.message or result.error_code

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

def _latest_delivery(deliveries: object, card_id: str) -> dict[str, Any] | None:
    if not isinstance(deliveries, list):
        return None
    matches = [item for item in deliveries if isinstance(item, dict) and item.get("card_id") == card_id]
    if not matches:
        return None
    return max(matches, key=lambda item: _parse_time(item.get("delivered_at")) or datetime.min.replace(tzinfo=timezone.utc))

def _delivery_source_values(delivery: dict[str, Any] | None) -> set[str]:
    if not isinstance(delivery, dict):
        return set()
    source_paths = delivery.get("delivery_context", {}).get("source_paths", {})
    if isinstance(source_paths, dict):
        values = source_paths.values()
    elif isinstance(source_paths, list):
        values = source_paths
    else:
        values = ()
    return {str(value).replace("\\", "/") for value in values if isinstance(value, str)}

def _read_text(path: Path) -> tuple[str, str | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except FileNotFoundError:
        return "", f"missing file: {path.as_posix()}"
    except UnicodeDecodeError as exc:
        return "", f"invalid UTF-8 in {path.as_posix()}: {exc}"

def _packet_body_output_contract(path: Path) -> tuple[dict[str, Any] | None, str | None, str]:
    text, error = _read_text(path)
    if error:
        return None, error, text
    heading_index = text.find("## Output Contract")
    search_from = heading_index if heading_index >= 0 else 0
    fence_start = text.find("```json", search_from)
    if fence_start < 0:
        return None, "missing Output Contract JSON fence", text
    json_start = text.find("\n", fence_start)
    if json_start < 0:
        return None, "malformed Output Contract JSON fence", text
    json_start += 1
    fence_end = text.find("```", json_start)
    if fence_end < 0:
        return None, "unterminated Output Contract JSON fence", text
    raw_json = text[json_start:fence_end].strip()
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        return None, f"invalid Output Contract JSON: {exc}", text
    if not isinstance(payload, dict):
        return None, "Output Contract JSON is not an object", text
    return payload, None, text

def _contract_uniquely_matches_role(contract: object, to_role: str) -> bool:
    if not isinstance(contract, dict) or not to_role:
        return False
    if contract.get("recipient_role") == to_role:
        return True
    roles = contract.get("recipient_roles")
    return isinstance(roles, list) and roles == [to_role]

def _ledger_packets_by_id(packet_ledger: object) -> dict[str, dict[str, Any]]:
    if not isinstance(packet_ledger, dict):
        return {}
    packets = packet_ledger.get("packets")
    if not isinstance(packets, list):
        return {}
    return {
        str(packet.get("packet_id")): packet
        for packet in packets
        if isinstance(packet, dict) and packet.get("packet_id")
    }

def _pm_material_packet_specs_by_id(pm_spec: object) -> dict[str, dict[str, Any]]:
    if not isinstance(pm_spec, dict):
        return {}
    packets = pm_spec.get("packets")
    if not isinstance(packets, list):
        return {}
    return {
        str(packet.get("packet_id")): packet
        for packet in packets
        if isinstance(packet, dict) and packet.get("packet_id")
    }

def _material_packet_envelope_paths(run_root: Path, material_scan_packets: object) -> list[str]:
    paths: set[str] = set()
    if isinstance(material_scan_packets, dict):
        for packet in material_scan_packets.get("packets", []):
            if isinstance(packet, dict) and isinstance(packet.get("packet_envelope_path"), str):
                paths.add(packet["packet_envelope_path"].replace("\\", "/"))
        if paths:
            return sorted(paths)
    packet_root = run_root / "packets"
    if packet_root.exists():
        for envelope_path in sorted(packet_root.glob("*/packet_envelope.json")):
            envelope, error = _read_json(envelope_path)
            if error or not isinstance(envelope, dict):
                continue
            if envelope.get("packet_type") == "material_scan":
                paths.add(".flowpilot/runs/" + run_root.name + "/" + envelope_path.relative_to(run_root).as_posix())
    return sorted(paths)

def _background_running_projection_ids(snapshot: object) -> list[str]:
    if not isinstance(snapshot, dict):
        return []
    raw_entries = snapshot.get("background_running_index_entries")
    if raw_entries is None and isinstance(snapshot.get("authority"), dict):
        raw_entries = snapshot["authority"].get("background_running_index_entries")
    background_running_entries: list[str] = []
    if isinstance(raw_entries, list):
        for item in raw_entries:
            if isinstance(item, dict) and item.get("run_id"):
                background_running_entries.append(str(item.get("run_id")))
            elif isinstance(item, str):
                background_running_entries.append(item)
    return background_running_entries


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


def _active_set_authority_is_explicit(
    snapshot: object,
    *,
    non_current_running_entries: list[str],
    missing_background_projection: list[str],
) -> bool:
    if not non_current_running_entries:
        return True
    authority = _snapshot_authority(snapshot)
    catalog = _snapshot_active_catalog(snapshot)
    operation_targets = catalog.get("operation_targets")
    if not isinstance(operation_targets, dict):
        operation_targets = authority.get("operation_targets")
    single_targets = operation_targets.get("single_targets") if isinstance(operation_targets, dict) else None
    target_run_ids = {
        str(item.get("run_id") or "")
        for item in single_targets
        if isinstance(item, dict) and item.get("target_id")
    } if isinstance(single_targets, list) else set()
    background_tasks = catalog.get("background_active_tasks")
    background_run_ids = {
        str(item.get("run_id") or "")
        for item in background_tasks
        if isinstance(item, dict)
        and item.get("target_id")
        and item.get("operation_target_allowed") is True
    } if isinstance(background_tasks, list) else set()
    return bool(
        isinstance(snapshot, dict)
        and (snapshot.get("current_pointer_is_ui_focus_only") is True or authority.get("current_pointer_is_ui_focus_only") is True)
        and (
            snapshot.get("index_running_entries_are_parallel_run_authority") is True
            or authority.get("index_running_entries_are_parallel_run_authority") is True
        )
        and (snapshot.get("global_main_required") is False or authority.get("global_main_required") is False or catalog.get("global_main_required") is False)
        and (snapshot.get("operation_target_required") is True or authority.get("operation_target_required") is True or catalog.get("operation_target_required") is True)
        and catalog.get("authority") == "explicit_active_set"
        and not missing_background_projection
        and set(non_current_running_entries).issubset(target_run_ids)
        and set(non_current_running_entries).issubset(background_run_ids)
    )


def _run_target_id(run_id: str) -> str:
    return f"run:{run_id}"


def _active_set_authority_snapshot_from_index(
    *,
    current: object,
    index: object,
    current_run_id: str,
) -> dict[str, object] | None:
    """Build a read-only explicit active-set projection from current/index files."""

    if not isinstance(index, dict):
        return None
    current_status = current.get("status") if isinstance(current, dict) else None
    current_root = current.get("run_root") if isinstance(current, dict) else None
    running_entries: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in index.get("runs", []):
        if not isinstance(item, dict) or item.get("status") != "running" or not item.get("run_id"):
            continue
        item_run_id = str(item.get("run_id"))
        if item_run_id in seen:
            continue
        seen.add(item_run_id)
        focus_selected = item_run_id == current_run_id
        running_entries.append(
            {
                "run_id": item_run_id,
                "flow_block_id": str(
                    item.get("flow_block_id")
                    or item.get("active_route_id")
                    or item.get("route_id")
                    or "unknown"
                ),
                "run_root": str(item.get("run_root") or f".flowpilot/runs/{item_run_id}"),
                "status": "running",
                "target_id": _run_target_id(item_run_id),
                "target_scope": "single",
                "operation_target_allowed": True,
                "focus_selected": focus_selected,
                "background_active": not focus_selected,
                "stale_residue": False,
            }
        )
    if current_run_id and current_status == "running" and current_run_id not in seen:
        running_entries.append(
            {
                "run_id": current_run_id,
                "flow_block_id": "current_focus",
                "run_root": str(current_root or f".flowpilot/runs/{current_run_id}"),
                "status": "running",
                "target_id": _run_target_id(current_run_id),
                "target_scope": "single",
                "operation_target_allowed": True,
                "focus_selected": True,
                "background_active": False,
                "stale_residue": False,
            }
        )
    if not running_entries:
        return None

    active_run_ids = [str(item["run_id"]) for item in running_entries]
    active_flow_block_ids = [str(item.get("flow_block_id") or "unknown") for item in running_entries]
    single_targets = [
        {
            "target_id": str(item["target_id"]),
            "target_scope": "single",
            "run_id": str(item["run_id"]),
            "flow_block_id": str(item.get("flow_block_id") or "unknown"),
        }
        for item in running_entries
    ]
    operation_targets = {
        "target_scope_required": True,
        "current_focus": _run_target_id(current_run_id) if current_run_id else None,
        "single_targets": single_targets,
        "all_active": {
            "target_id": "all_active",
            "target_scope": "all_active",
            "run_ids": active_run_ids,
            "flow_block_ids": active_flow_block_ids,
        },
    }
    background_entries = [item for item in running_entries if not item.get("focus_selected")]
    snapshot = {
        "current_pointer_is_ui_focus_only": True,
        "index_running_entries_are_parallel_run_authority": True,
        "global_main_required": False,
        "operation_target_required": True,
        "authority": {
            "active_source": "explicit_active_set",
            "source_authority": "index_current_read_only_synthesis",
            "current_pointer_is_ui_focus_only": True,
            "index_running_entries_are_parallel_run_authority": True,
            "global_main_required": False,
            "operation_target_required": True,
            "operation_targets": operation_targets,
            "background_running_index_entries": background_entries,
        },
        "active_ui_task_catalog": {
            "authority": "explicit_active_set",
            "source_authority": "index_current_read_only_synthesis",
            "scope_kind": "parallel_runs" if len(running_entries) > 1 else "single_run",
            "current_focus": current_run_id,
            "global_main_required": False,
            "operation_target_required": True,
            "active_tasks": running_entries,
            "background_active_tasks": background_entries,
            "stale_residue_tasks": [],
            "operation_targets": operation_targets,
        },
    }
    return snapshot


def _audit_material_scan_dispatch_integrity(
    project_root: Path,
    run_root: Path,
    router_state: object,
    frontier: object,
) -> dict[str, object]:
    material_scan_packets, _material_packets_error = _read_json(
        run_root / "material" / "material_scan_packets.json"
    )
    pm_spec, _pm_spec_error = _read_json(
        run_root / "material" / "pm_material_scan_packet_specs.project_manager.json"
    )
    packet_ledger, _packet_ledger_error = _read_json(run_root / "packet_ledger.json")
    envelope_paths = _material_packet_envelope_paths(run_root, material_scan_packets)
    requested = bool(envelope_paths) or (
        isinstance(material_scan_packets, dict)
        and bool(material_scan_packets.get("router_direct_dispatch_required_before_worker"))
    )
    if not requested:
        return {
            "requested": False,
            "reviewed": False,
            "phase_context_consistent": True,
            "output_contract_consistent": True,
            "write_target_explicit": True,
            "single_canonical_body": True,
            "packet_details": [],
        }

    router_phase = str(router_state.get("phase") or "") if isinstance(router_state, dict) else ""
    router_status = str(router_state.get("status") or "") if isinstance(router_state, dict) else ""
    frontier_phase = str(frontier.get("phase") or "") if isinstance(frontier, dict) else ""
    frontier_status = str(frontier.get("status") or "") if isinstance(frontier, dict) else ""
    flags = _router_flags(router_state)
    stopped_by_user = (
        router_status == "stopped_by_user"
        or frontier_status == "stopped_by_user"
        or bool(flags.get("run_stopped_by_user"))
    )
    material_scan_complete = bool(flags.get("material_review_sufficient"))
    phase_context_consistent = stopped_by_user or material_scan_complete or (
        router_phase == "material_scan"
        and frontier_phase == "material_scan"
        and frontier_status == "material_scan"
    )
    ledger_by_id = _ledger_packets_by_id(packet_ledger)
    specs_by_id = _pm_material_packet_specs_by_id(pm_spec)
    contract_ok = True
    write_target_ok = True
    canonical_body_ok = True
    packet_details: list[dict[str, object]] = []
    for envelope_rel in envelope_paths:
        envelope_path = project_root / envelope_rel
        envelope, envelope_error = _read_json(envelope_path)
        if envelope_error or not isinstance(envelope, dict):
            contract_ok = False
            write_target_ok = False
            canonical_body_ok = False
            packet_details.append(
                {
                    "packet_envelope_path": envelope_rel,
                    "envelope_error": envelope_error,
                }
            )
            continue
        packet_id = str(envelope.get("packet_id") or "")
        to_role = str(envelope.get("to_role") or "")
        body_rel = str(envelope.get("body_path") or "").replace("\\", "/")
        body_contract, body_contract_error, body_text = _packet_body_output_contract(project_root / body_rel)
        envelope_contract = envelope.get("output_contract")
        contracts_same = isinstance(envelope_contract, dict) and envelope_contract == body_contract
        role_unique = _contract_uniquely_matches_role(
            envelope_contract, to_role
        ) and _contract_uniquely_matches_role(body_contract, to_role)
        packet_contract_ok = contracts_same and role_unique
        contract_ok = contract_ok and packet_contract_ok

        ledger_result_body_path = str(
            ledger_by_id.get(packet_id, {}).get("result_body_path") or ""
        ).replace("\\", "/")
        envelope_result_body_path = str(envelope.get("result_body_path") or "").replace("\\", "/")
        body_mentions_result_path = bool(
            ledger_result_body_path and ledger_result_body_path in body_text.replace("\\", "/")
        )
        packet_write_target_ok = bool(
            ledger_result_body_path
            and (
                envelope_result_body_path == ledger_result_body_path
                or body_mentions_result_path
            )
        )
        write_target_ok = write_target_ok and packet_write_target_ok

        spec = specs_by_id.get(packet_id, {})
        spec_body_path = str(spec.get("body_path") or "").replace("\\", "/")
        spec_body_hash = str(spec.get("body_hash") or "")
        envelope_body_hash = str(envelope.get("body_hash") or "")
        spec_body_text = ""
        spec_body_hash_valid = False
        if spec_body_path and spec_body_hash:
            spec_body_text, _spec_body_error = _read_text(project_root / spec_body_path)
            spec_body_hash_valid = (
                bool(spec_body_text)
                and hashlib.sha256(spec_body_text.encode("utf-8")).hexdigest() == spec_body_hash
            )
        spec_body_materialized = (
            spec_body_hash_valid
            and bool(envelope_body_hash)
            and spec_body_path != body_rel
            and spec_body_text.strip() in body_text
            and packet_contract_ok
            and packet_write_target_ok
        )
        packet_canonical_ok = not spec or spec_body_materialized or (
            spec_body_path == body_rel and spec_body_hash == envelope_body_hash
        )
        canonical_body_ok = canonical_body_ok and packet_canonical_ok

        packet_details.append(
            {
                "packet_id": packet_id,
                "to_role": to_role,
                "packet_envelope_path": envelope_rel,
                "packet_body_path": body_rel,
                "body_contract_error": body_contract_error,
                "contracts_same": contracts_same,
                "contract_uniquely_matches_to_role": role_unique,
                "ledger_result_body_path": ledger_result_body_path or None,
                "envelope_result_body_path": envelope_result_body_path or None,
                "body_mentions_result_body_path": body_mentions_result_path,
                "write_target_explicit": packet_write_target_ok,
                "pm_spec_body_path": spec_body_path or None,
                "pm_spec_body_hash": spec_body_hash or None,
                "envelope_body_hash": envelope_body_hash or None,
                "pm_spec_body_hash_valid": spec_body_hash_valid,
                "pm_spec_body_materialized": spec_body_materialized,
                "single_canonical_body": packet_canonical_ok,
            }
        )

    reviewed = False
    if isinstance(router_state, dict):
        reviewed = _json_contains(router_state, "reviewer_blocks_material_scan_dispatch") or _json_contains(
            router_state, "reviewer_dispatch_allowed"
        )
    reviewed = reviewed or (run_root / "material" / "reviewer_dispatch_report.human_like_reviewer.json").exists()
    return {
        "requested": requested,
        "reviewed": reviewed,
        "phase_context_consistent": phase_context_consistent,
        "output_contract_consistent": contract_ok,
        "write_target_explicit": write_target_ok,
        "single_canonical_body": canonical_body_ok,
        "phase_evidence": {
            "router_state_phase": router_phase,
            "execution_frontier_phase": frontier_phase,
            "execution_frontier_status": frontier_status,
            "material_scan_complete": material_scan_complete,
        },
        "packet_details": packet_details,
    }

def _router_flags(router_state: object) -> dict[str, Any]:
    if not isinstance(router_state, dict):
        return {}
    flags = router_state.get("state_flags")
    if isinstance(flags, dict):
        return flags
    flags = router_state.get("flags")
    if isinstance(flags, dict):
        return flags
    return {}

def _json_contains(data: object, needle: str) -> bool:
    if not needle:
        return False
    return needle.replace("\\", "/") in json.dumps(data, ensure_ascii=False, sort_keys=True).replace("\\", "/")

def _add_finding(
    findings: list[dict[str, object]],
    *,
    code: str,
    severity: str,
    summary: str,
    invariant: str,
    evidence: dict[str, object],
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

def _run_text_contains(run_root: Path, *needles: str) -> bool:
    for path in run_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl", ".txt", ".md"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if all(needle in text for needle in needles):
            return True
    return False

def _audit_role_output_event_dedup(router_state: object) -> dict[str, object]:
    if not isinstance(router_state, dict):
        return {
            "deduped_by_body_ref": True,
            "deduped_by_package_identity": True,
            "duplicate_side_effect_written": False,
            "duplicates": [],
            "package_identity_conflicts": [],
            "terminal_quarantined_duplicate_events": 0,
            "terminal_quarantined_package_identity_records": 0,
        }
    keys: list[tuple[str, str, str]] = []
    terminal_quarantined_duplicate_events = 0
    for event in router_state.get("events", []):
        if not isinstance(event, dict):
            continue
        if (
            isinstance(event.get("terminal_lifecycle_quarantine"), dict)
            and event["terminal_lifecycle_quarantine"].get("status") == "terminal_lifecycle_quarantined"
        ):
            terminal_quarantined_duplicate_events += 1
            continue
        payload = event.get("payload")
        body_ref = payload.get("body_ref") if isinstance(payload, dict) else None
        if not isinstance(body_ref, dict):
            continue
        path = str(body_ref.get("path") or "")
        digest = str(body_ref.get("hash") or body_ref.get("report_hash") or "")
        if path and digest:
            keys.append((str(event.get("event") or ""), path, digest))
    counts = Counter(keys)
    duplicates = [
        {"event": event, "path": path, "hash": digest, "count": count}
        for (event, path, digest), count in counts.items()
        if count > 1
    ]
    package_scope_groups: dict[tuple[str, str, str, str], set[str]] = {}
    terminal_quarantined_package_identity_records = 0
    idempotency = router_state.get("external_event_idempotency")
    processed = idempotency.get("processed") if isinstance(idempotency, dict) else {}
    if isinstance(processed, dict):
        for event_name in (
            "pm_records_material_scan_result_disposition",
            "pm_records_research_result_disposition",
            "pm_records_current_node_result_disposition",
        ):
            event_records = processed.get(event_name)
            if not isinstance(event_records, dict):
                continue
            for record in event_records.values():
                if not isinstance(record, dict):
                    continue
                if (
                    isinstance(record.get("terminal_lifecycle_quarantine"), dict)
                    and record["terminal_lifecycle_quarantine"].get("status") == "terminal_lifecycle_quarantined"
                ):
                    terminal_quarantined_package_identity_records += 1
                    continue
                scope = record.get("scope")
                if not isinstance(scope, dict):
                    continue
                key = (
                    event_name,
                    str(scope.get("batch_id") or ""),
                    str(scope.get("packet_ids") or ""),
                    str(scope.get("packet_generation_id") or ""),
                )
                body_hash = str(scope.get("body_hash") or "")
                if all(key) and body_hash:
                    package_scope_groups.setdefault(key, set()).add(body_hash)
    package_identity_conflicts = [
        {
            "event": event,
            "batch_id": batch_id,
            "packet_ids": packet_ids,
            "packet_generation_id": packet_generation_id,
            "distinct_body_hash_count": len(body_hashes),
        }
        for (event, batch_id, packet_ids, packet_generation_id), body_hashes in package_scope_groups.items()
        if len(body_hashes) > 1
    ]
    return {
        "deduped_by_body_ref": not duplicates,
        "deduped_by_package_identity": not package_identity_conflicts,
        "duplicate_side_effect_written": bool(duplicates or package_identity_conflicts),
        "duplicates": duplicates[:12],
        "package_identity_conflicts": package_identity_conflicts[:12],
        "terminal_quarantined_duplicate_events": terminal_quarantined_duplicate_events,
        "terminal_quarantined_package_identity_records": terminal_quarantined_package_identity_records,
    }

def _audit_packet_result_authority(run_root: Path) -> dict[str, object]:
    packet_ledger, packet_error = _read_json(run_root / "packet_ledger.json")
    role_binding_ledger, runtime_roles_error = _read_json(run_root / "role_binding_ledger.json")
    role_keys = {
        str(slot.get("role_key"))
        for slot in (role_binding_ledger.get("role_slots") if isinstance(role_binding_ledger, dict) else []) or []
        if isinstance(slot, dict) and slot.get("role_key")
    }
    issues: list[dict[str, object]] = []
    quarantined_issues: list[dict[str, object]] = []
    for packet in (packet_ledger.get("packets") if isinstance(packet_ledger, dict) else []) or []:
        if not isinstance(packet, dict):
            continue
        result = packet.get("result_envelope")
        if not isinstance(result, dict):
            continue
        completed_by_role = str(result.get("completed_by_role") or "")
        if result.get("completed_agent_id_belongs_to_role") is False or not result.get("completed_agent_id"):
            issue = {
                "packet_id": packet.get("packet_id"),
                "completed_by_role": completed_by_role,
                "completed_agent_id": result.get("completed_agent_id"),
                "completed_agent_id_belongs_to_role": result.get("completed_agent_id_belongs_to_role"),
                "role_exists_in_role_binding_ledger": completed_by_role in role_keys,
            }
            if (
                isinstance(result.get("author_identity_quarantine"), dict)
                and result["author_identity_quarantine"].get("status") == "terminal_lifecycle_quarantined"
            ):
                quarantined_issues.append(issue)
                continue
            issues.append(
                issue
            )
    return {
        "packet_ledger_error": packet_error,
        "role_binding_ledger_error": runtime_roles_error,
        "result_author_identity_replayable": not issues,
        "result_author_matches_current_role": all(issue.get("role_exists_in_role_binding_ledger") for issue in issues),
        "issues": issues[:12],
        "terminal_quarantined_issues": quarantined_issues[:12],
    }

def _safe_int(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0

def _project_path(project_root: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    return project_root / value.replace("\\", "/")

def _event_name_from_role_output(output: object) -> str:
    if not isinstance(output, dict):
        return ""
    event_name = output.get("event_name")
    if isinstance(event_name, str) and event_name:
        return event_name
    envelope = output.get("envelope")
    if isinstance(envelope, dict) and isinstance(envelope.get("event_name"), str):
        return envelope["event_name"]
    event = output.get("event")
    if isinstance(event, dict) and isinstance(event.get("event_name"), str):
        return event["event_name"]
    return ""

def _material_generation_source_checks(source_root: Path) -> dict[str, object]:
    next_actions_text, next_actions_error = _read_text(
        source_root
        / "skills"
        / "flowpilot"
        / "assets"
        / "flowpilot_router_work_packets_next_actions.py"
    )
    persistence_text, persistence_error = _read_text(
        source_root
        / "skills"
        / "flowpilot"
        / "assets"
        / "flowpilot_router_runtime_state_persistence.py"
    )
    role_output_text, role_output_error = _read_text(
        source_root
        / "skills"
        / "flowpilot"
        / "assets"
        / "flowpilot_router_role_output_bridge_events.py"
    )
    role_output_replay_text, role_output_replay_error = _read_text(
        source_root
        / "skills"
        / "flowpilot"
        / "assets"
        / "flowpilot_router_role_output_bridge_events_replay.py"
    )
    expected_waits_text, expected_waits_error = _read_text(
        source_root
        / "skills"
        / "flowpilot"
        / "assets"
        / "flowpilot_router_expected_waits_reconciliation.py"
    )
    expected_waits_pm_package_text, expected_waits_pm_package_error = _read_text(
        source_root
        / "skills"
        / "flowpilot"
        / "assets"
        / "flowpilot_router_expected_waits_reconciliation_pm_package.py"
    )
    expected_waits_family_text = "\n".join((expected_waits_text, expected_waits_pm_package_text))
    expected_waits_family_error = expected_waits_error or expected_waits_pm_package_error
    event_dispatcher_text, event_dispatcher_error = _read_text(
        source_root
        / "skills"
        / "flowpilot"
        / "assets"
        / "flowpilot_router_event_dispatcher.py"
    )
    action_provider_text, action_provider_error = _read_text(
        source_root
        / "skills"
        / "flowpilot"
        / "assets"
        / "flowpilot_router_action_providers_lifecycle.py"
    )
    next_action_uses_global_flags = (
        "if flags.get('pm_material_packets_issued') and (not flags.get('material_scan_packets_relayed'))"
        in next_actions_text
        or "if flags.get('worker_scan_results_returned') and (not flags.get('material_scan_results_relayed_to_pm'))"
        in next_actions_text
        or "if flags.get('material_scan_results_relayed_to_pm') and (not flags.get('material_scan_result_disposition_recorded'))"
        in next_actions_text
    )
    stale_save_preserves_existing_true_flags = (
        "existing_value is True" in persistence_text
        and "merged_flags[flag] = True" in persistence_text
        and "_MATERIAL_GENERATION_PROGRESS_FLAGS" not in persistence_text
    )
    role_output_global_flag_short_circuit = (
        "flags.get(flag) and event not in {ROLE_WORK_RESULT_RETURNED_EVENT, \"worker_current_node_result_returned\"}"
        in role_output_text
    )
    scoped_identity_text, scoped_identity_error = _read_text(
        source_root
        / "skills"
        / "flowpilot"
        / "assets"
        / "flowpilot_router_protocol_scoped_event_identity.py"
    )
    package_disposition_conflict_checked = (
        '"conflict_fields": ("body_hash",)' in scoped_identity_text
        and '"dedupe_fields": ("batch_id", "packet_ids", "packet_generation_id", "body_hash")'
        not in scoped_identity_text
    )
    domain_commit_index = expected_waits_family_text.find("domain_commit = _commit_reconciled_event_domain_artifact")
    event_flag_index = expected_waits_family_text.find('run_state["flags"][flag] = True')
    package_reconciliation_domain_first_commit = (
        expected_waits_family_error is None
        and domain_commit_index >= 0
        and event_flag_index >= 0
        and domain_commit_index < event_flag_index
        and "_write_pm_package_result_disposition(" in expected_waits_family_text
    )
    package_reconciliation_covers_all_domains = all(
        event_name in expected_waits_family_text and batch_kind in expected_waits_family_text
        for event_name, batch_kind in (
            ("pm_records_material_scan_result_disposition", "material_scan"),
            ("pm_records_research_result_disposition", "research"),
            ("pm_records_current_node_result_disposition", "current_node"),
        )
    )
    package_authority_split_guard_present = (
        role_output_error is None
        and role_output_replay_error is None
        and "_package_disposition_authority_split(" in role_output_replay_text
        and "_record_package_disposition_authority_split(" in role_output_replay_text
        and "package_authority_splits" in role_output_replay_text
        and event_dispatcher_error is None
        and "_repair_direct_package_disposition_authority_split(" in event_dispatcher_text
    )
    package_authority_split_preserves_wait = (
        package_authority_split_guard_present
        and action_provider_error is None
        and 'direct.get("package_authority_splits")' in action_provider_text
    )
    package_authority_split_repairs_domain_commit = (
        package_authority_split_guard_present
        and "_record_router_reconciled_external_event(" in role_output_replay_text
        and "router_repaired_reconciled_event_domain_commit" in expected_waits_family_text
        and "_write_pm_package_result_disposition(" in event_dispatcher_text
        and "domain_commit_repaired" in event_dispatcher_text
        and "router_repaired_direct_package_disposition_authority_split" in event_dispatcher_text
    )
    return {
        "next_actions_error": next_actions_error,
        "persistence_error": persistence_error,
        "role_output_error": role_output_error,
        "role_output_replay_error": role_output_replay_error,
        "expected_waits_error": expected_waits_error,
        "expected_waits_pm_package_error": expected_waits_pm_package_error,
        "event_dispatcher_error": event_dispatcher_error,
        "action_provider_error": action_provider_error,
        "scoped_identity_error": scoped_identity_error,
        "next_action_uses_global_material_flags": next_action_uses_global_flags,
        "stale_save_preserves_existing_true_flags": stale_save_preserves_existing_true_flags,
        "role_output_has_global_flag_short_circuit": role_output_global_flag_short_circuit,
        "package_disposition_conflict_checked": package_disposition_conflict_checked,
        "package_reconciliation_covers_all_domains": package_reconciliation_covers_all_domains,
        "package_reconciliation_domain_first_commit": (
            package_reconciliation_domain_first_commit
            and package_reconciliation_covers_all_domains
        ),
        "package_authority_split_preserves_wait": package_authority_split_preserves_wait,
        "package_authority_split_repairs_domain_commit": package_authority_split_repairs_domain_commit,
    }

def _audit_material_generation_progress_projection(
    project_root: Path,
    run_root: Path,
    router_state: object,
    source_root: Path,
) -> dict[str, object]:
    flags = _router_flags(router_state)
    material_index, material_index_error = _read_json(
        run_root / "material" / "material_scan_packets.json"
    )
    active_ref, active_ref_error = _read_json(
        run_root / "packet_batches" / "active_material_scan.json"
    )
    batch_path: Path | None = None
    if isinstance(active_ref, dict):
        batch_path = _project_path(project_root, active_ref.get("batch_path"))
        if batch_path is None and active_ref.get("batch_id"):
            batch_path = run_root / "packet_batches" / f"{active_ref['batch_id']}.json"
    active_batch, active_batch_error = _read_json(batch_path) if batch_path else (None, None)
    packets = active_batch.get("packets") if isinstance(active_batch, dict) else []
    packets = packets if isinstance(packets, list) else []
    counts = active_batch.get("counts") if isinstance(active_batch, dict) else {}
    counts = counts if isinstance(counts, dict) else {}
    member_status = active_batch.get("member_status") if isinstance(active_batch, dict) else {}
    member_status = member_status if isinstance(member_status, dict) else {}
    packet_count = max(
        len(packets),
        _safe_int(member_status.get("packet_count")),
        _safe_int(counts.get("registered")),
    )
    relayed = _safe_int(counts.get("relayed"))
    results_returned = max(
        _safe_int(counts.get("results_returned")),
        _safe_int(member_status.get("results_returned")),
    )
    current_generation_id = (
        str(material_index.get("current_generation_id") or "")
        if isinstance(material_index, dict)
        else ""
    )
    active_repair_transaction_id = (
        str(material_index.get("repair_transaction_id") or "")
        if isinstance(material_index, dict)
        else ""
    )
    batch_generation_ids = sorted(
        {
            str(packet.get("packet_generation_id"))
            for packet in packets
            if isinstance(packet, dict) and packet.get("packet_generation_id")
        }
    )
    batch_repair_ids = sorted(
        {
            str(packet.get("repair_transaction_id"))
            for packet in packets
            if isinstance(packet, dict) and packet.get("repair_transaction_id")
        }
    )
    active_batch_matches_generation = (
        not current_generation_id
        or not batch_generation_ids
        or batch_generation_ids == [current_generation_id]
    )
    batch_status = str(active_batch.get("status") or "") if isinstance(active_batch, dict) else ""
    all_results_returned = bool(member_status.get("all_results_returned"))
    pm_result_disposition = (
        active_batch.get("pm_result_disposition") if isinstance(active_batch, dict) else None
    )
    stale_progress_flag_mismatches: list[dict[str, object]] = []
    if flags.get("material_scan_packets_relayed") and relayed < packet_count:
        stale_progress_flag_mismatches.append(
            {
                "flag": "material_scan_packets_relayed",
                "flag_value": True,
                "active_batch_relayed": relayed,
                "active_batch_packet_count": packet_count,
            }
        )
    if flags.get("worker_packets_delivered") and relayed < packet_count:
        stale_progress_flag_mismatches.append(
            {
                "flag": "worker_packets_delivered",
                "flag_value": True,
                "active_batch_relayed": relayed,
                "active_batch_packet_count": packet_count,
            }
        )
    if flags.get("worker_scan_results_returned") and (
        not all_results_returned or results_returned < packet_count
    ):
        stale_progress_flag_mismatches.append(
            {
                "flag": "worker_scan_results_returned",
                "flag_value": True,
                "active_batch_results_returned": results_returned,
                "active_batch_packet_count": packet_count,
                "active_batch_all_results_returned": all_results_returned,
            }
        )
    if flags.get("material_scan_results_relayed_to_pm") and (
        not all_results_returned or batch_status not in {"results_relayed_to_pm", "pm_absorbed", "accepted", "complete"}
    ):
        stale_progress_flag_mismatches.append(
            {
                "flag": "material_scan_results_relayed_to_pm",
                "flag_value": True,
                "active_batch_status": batch_status or None,
                "active_batch_results_returned": results_returned,
                "active_batch_all_results_returned": all_results_returned,
            }
        )
    if flags.get("material_scan_result_disposition_recorded") and not isinstance(
        pm_result_disposition, dict
    ):
        stale_progress_flag_mismatches.append(
            {
                "flag": "material_scan_result_disposition_recorded",
                "flag_value": True,
                "active_batch_pm_result_disposition_present": False,
            }
        )

    material_dispatch_block = (
        router_state.get("material_dispatch_block") if isinstance(router_state, dict) else None
    )
    material_dispatch_block = material_dispatch_block if isinstance(material_dispatch_block, dict) else {}
    dispatch_repair_id = str(material_dispatch_block.get("repair_transaction_id") or "")
    dispatch_matches_active_generation = (
        not dispatch_repair_id
        or not active_repair_transaction_id
        or dispatch_repair_id == active_repair_transaction_id
    )

    role_output_ledger, role_output_error = _read_json(run_root / "role_output_ledger.json")
    pm_disposition_outputs: list[dict[str, object]] = []
    for output in (role_output_ledger.get("outputs") if isinstance(role_output_ledger, dict) else []) or []:
        if not isinstance(output, dict):
            continue
        if _event_name_from_role_output(output) != "pm_records_material_scan_result_disposition":
            continue
        pm_disposition_outputs.append(
            {
                "output_id": output.get("output_id"),
                "recorded_at": output.get("recorded_at"),
                "body_path": output.get("body_path"),
                "body_hash": output.get("body_hash"),
            }
        )

    source_checks = _material_generation_source_checks(source_root)
    has_active_repair_generation = bool(
        active_repair_transaction_id or batch_repair_ids or current_generation_id
    )
    has_stale_material_flags = bool(stale_progress_flag_mismatches)
    global_flags_match_active_generation = not has_stale_material_flags
    projection_generation_scoped = (
        active_batch_matches_generation
        and global_flags_match_active_generation
        and dispatch_matches_active_generation
    )
    next_action_derived_from_active_batch = not (
        has_stale_material_flags and source_checks.get("next_action_uses_global_material_flags")
    )
    reissue_clears_or_quarantines_stale_progress_flags = not (
        has_active_repair_generation and has_stale_material_flags
    )
    stale_save_preserves_material_generation_flag_clear = not (
        has_active_repair_generation
        and has_stale_material_flags
        and source_checks.get("stale_save_preserves_existing_true_flags")
    )
    role_output_current_generation_not_short_circuited_by_global_flag = not (
        flags.get("material_scan_result_disposition_recorded")
        and pm_disposition_outputs
        and not isinstance(pm_result_disposition, dict)
        and source_checks.get("role_output_has_global_flag_short_circuit")
    )
    packet_outcomes = (
        pm_result_disposition.get("packet_outcomes")
        if isinstance(pm_result_disposition, dict)
        else None
    )
    pm_package_packet_outcomes_recorded = not isinstance(pm_result_disposition, dict) or bool(packet_outcomes)
    return {
        "material_index_error": material_index_error,
        "active_material_ref_error": active_ref_error,
        "active_material_batch_error": active_batch_error,
        "active_material_batch_path": (
            batch_path.relative_to(project_root).as_posix()
            if batch_path and batch_path.is_relative_to(project_root)
            else str(batch_path) if batch_path else None
        ),
        "current_generation_id": current_generation_id or None,
        "active_repair_transaction_id": active_repair_transaction_id or None,
        "batch_generation_ids": batch_generation_ids,
        "batch_repair_transaction_ids": batch_repair_ids,
        "active_batch_matches_generation": active_batch_matches_generation,
        "active_batch_status": batch_status or None,
        "active_batch_counts": counts,
        "active_batch_member_status": member_status,
        "stale_progress_flag_mismatches": stale_progress_flag_mismatches,
        "material_dispatch_block_repair_transaction_id": dispatch_repair_id or None,
        "material_dispatch_block_matches_active_generation": dispatch_matches_active_generation,
        "pm_material_disposition_role_outputs": pm_disposition_outputs[:8],
        "role_output_ledger_error": role_output_error,
        "source_checks": source_checks,
        "projection_generation_scoped": projection_generation_scoped,
        "global_flags_match_active_generation": global_flags_match_active_generation,
        "next_action_derived_from_active_batch": next_action_derived_from_active_batch,
        "reissue_clears_or_quarantines_stale_progress_flags": reissue_clears_or_quarantines_stale_progress_flags,
        "stale_save_preserves_material_generation_flag_clear": stale_save_preserves_material_generation_flag_clear,
        "role_output_current_generation_not_short_circuited_by_global_flag": role_output_current_generation_not_short_circuited_by_global_flag,
        "pm_package_disposition_body_hash_conflict_checked": bool(source_checks.get("package_disposition_conflict_checked")),
        "role_output_package_disposition_domain_first_commit": bool(source_checks.get("package_reconciliation_domain_first_commit")),
        "pm_package_authority_split_preserves_wait": bool(source_checks.get("package_authority_split_preserves_wait")),
        "pm_package_authority_split_repairs_domain_commit": bool(source_checks.get("package_authority_split_repairs_domain_commit")),
        "pm_package_packet_outcomes_recorded": pm_package_packet_outcomes_recorded,
    }

def _audit_material_repair_generation_protocol(
    project_root: Path,
    run_root: Path,
    router_state: object,
    source_root: Path,
) -> dict[str, object]:
    action_samples: list[dict[str, object]] = []
    for action_path in sorted((run_root / "runtime" / "controller_actions").glob("*.json")):
        action_record, error = _read_json(action_path)
        if error or not isinstance(action_record, dict):
            continue
        action = action_record.get("action")
        if not isinstance(action, dict):
            action = action_record
        plan = action.get("repair_execution_plan")
        if not isinstance(plan, dict) or plan.get("mode") != "operation_replay":
            continue
        if action.get("action_type") != "relay_material_scan_results_to_pm":
            continue
        allowed = " ".join(str(item) for item in action.get("allowed_reads") or ())
        if "packet_ledger.json" not in allowed or "material_scan_packets" not in allowed:
            action_samples.append(
                {
                    "action_path": ".flowpilot/runs/" + run_root.name + "/" + action_path.relative_to(run_root).as_posix(),
                    "action_type": action.get("action_type"),
                    "allowed_reads": action.get("allowed_reads"),
                }
            )
    patch_pending: list[str] = []
    for patch_path in sorted((run_root / "controller_break_glass" / "patches").glob("*.json")):
        patch_record, error = _read_json(patch_path)
        if error or not isinstance(patch_record, dict):
            continue
        if patch_record.get("final_disposition") == "pending_validation":
            patch_pending.append(
                ".flowpilot/runs/" + run_root.name + "/" + patch_path.relative_to(run_root).as_posix()
            )
    event_dedup = _audit_role_output_event_dedup(router_state)
    packet_authority = _audit_packet_result_authority(run_root)
    material_progress_projection = _audit_material_generation_progress_projection(
        project_root,
        run_root,
        router_state,
        source_root,
    )
    return {
        "operation_replay_fresh_controller_action_id": not (
            (run_root / "controller_break_glass" / "incidents" / "incident-20260523T185400Z-controller-action-id-collision.json").exists()
            or _run_text_contains(run_root, "identity collision")
        ),
        "operation_replay_targets_current_generation": not _run_text_contains(
            run_root,
            "operation_replay_targets_superseded_packets",
        ),
        "operation_replay_ledger_io_authorized": not action_samples
        and not _run_text_contains(run_root, "material_scan_result_relay_requires_a_current_packet_ledger_check"),
        "controller_repair_work_packet_receipt_folded": not (
            (run_root / "controller_break_glass" / "incidents" / "incident-20260523T191900Z-controller-repair-work-packet-repeat.json").exists()
        ),
        "controller_repair_work_packet_facade_exported": not _run_text_contains(
            run_root,
            "_apply_controller_repair_work_packet_receipt",
            "no attribute",
        ),
        "pm_material_disposition_generation_scoped": not _run_text_contains(
            run_root,
            "existing material disposition was recorded for the superseded original material scan packet IDs",
        ),
        "pm_material_disposition_matches_current_generation": not _run_text_contains(
            run_root,
            "mix superseded original packet evidence with the current reissue generation",
        ),
        "stale_pm_material_disposition_restored": _run_text_contains(
            run_root,
            "router_state_material_scan_result_disposition_recorded_restored_from_old_pm_disposition",
        ),
        "role_output_event_deduped_by_body_ref": bool(event_dedup.get("deduped_by_body_ref")),
        "duplicate_role_event_side_effect_written": bool(event_dedup.get("duplicate_side_effect_written")),
        "pm_package_disposition_semantic_identity_deduped": bool(
            event_dedup.get("deduped_by_package_identity")
        ),
        "pm_package_disposition_body_hash_conflict_checked": bool(
            material_progress_projection.get("pm_package_disposition_body_hash_conflict_checked")
        ),
        "role_output_package_disposition_domain_first_commit": bool(
            material_progress_projection.get("role_output_package_disposition_domain_first_commit")
        ),
        "pm_package_authority_split_preserves_wait": bool(
            material_progress_projection.get("pm_package_authority_split_preserves_wait")
        ),
        "pm_package_authority_split_repairs_domain_commit": bool(
            material_progress_projection.get("pm_package_authority_split_repairs_domain_commit")
        ),
        "pm_package_packet_outcomes_recorded": bool(
            material_progress_projection.get("pm_package_packet_outcomes_recorded")
        ),
        "packet_result_author_identity_replayable": bool(
            packet_authority.get("result_author_identity_replayable")
        ),
        "packet_result_author_matches_current_role": bool(
            packet_authority.get("result_author_matches_current_role")
        ),
        "break_glass_patch_validation_finalized": not patch_pending,
        "material_progress_projection_generation_scoped": bool(
            material_progress_projection.get("projection_generation_scoped")
        ),
        "material_global_progress_flags_match_active_generation": bool(
            material_progress_projection.get("global_flags_match_active_generation")
        ),
        "material_next_action_derived_from_active_batch": bool(
            material_progress_projection.get("next_action_derived_from_active_batch")
        ),
        "material_reissue_clears_or_quarantines_stale_progress_flags": bool(
            material_progress_projection.get("reissue_clears_or_quarantines_stale_progress_flags")
        ),
        "stale_run_state_save_preserves_material_generation_flag_clear": bool(
            material_progress_projection.get("stale_save_preserves_material_generation_flag_clear")
        ),
        "material_dispatch_block_matches_active_generation": bool(
            material_progress_projection.get("material_dispatch_block_matches_active_generation")
        ),
        "role_output_current_generation_not_short_circuited_by_global_flag": bool(
            material_progress_projection.get("role_output_current_generation_not_short_circuited_by_global_flag")
        ),
        "operation_replay_actions_missing_ledger_io": action_samples,
        "pending_break_glass_patch_records": patch_pending,
        "event_dedup": event_dedup,
        "packet_result_authority": packet_authority,
        "material_generation_progress_projection": material_progress_projection,
    }

def _router_control_blocker_status_matches(router_state: object, project_root: Path) -> tuple[bool, list[dict[str, object]]]:
    if not isinstance(router_state, dict):
        return True, []
    mismatches: list[dict[str, object]] = []
    for entry in router_state.get("control_blockers", []):
        if not isinstance(entry, dict):
            continue
        rel_path = entry.get("blocker_artifact_path")
        if not isinstance(rel_path, str):
            continue
        artifact, error = _read_json(project_root / rel_path)
        if error or not isinstance(artifact, dict):
            continue
        artifact_status = artifact.get("delivery_status")
        router_status = entry.get("delivery_status")
        artifact_resolution = artifact.get("resolution_status")
        router_resolution = entry.get("resolution_status")
        if artifact_status != router_status or artifact_resolution != router_resolution:
            mismatches.append(
                {
                    "blocker_id": entry.get("blocker_id"),
                    "path": rel_path,
                    "router_delivery_status": router_status,
                    "artifact_delivery_status": artifact_status,
                    "router_resolution_status": router_resolution,
                    "artifact_resolution_status": artifact_resolution,
                }
            )
    return not mismatches, mismatches

def _return_ledger_records(ledger: object) -> list[dict[str, object]]:
    if not isinstance(ledger, dict):
        return []
    records: list[dict[str, object]] = []
    for key in ("pending_returns", "completed_returns"):
        values = ledger.get(key)
        if not isinstance(values, list):
            continue
        for item in values:
            if isinstance(item, dict):
                records.append({**item, "_ledger_section": key})
    return records

def _ack_record_has_complete_receipts(record: dict[str, object]) -> bool:
    receipt_count = int(record.get("receipt_ref_count") or 0)
    member_card_ids = record.get("member_card_ids") or record.get("card_ids") or []
    if record.get("return_kind") == "system_card_bundle" or record.get("card_bundle_id"):
        return isinstance(member_card_ids, list) and bool(member_card_ids) and receipt_count >= len(member_card_ids)
    return receipt_count >= 1

def _ack_record_is_valid_direct_ack(project_root: Path, record: dict[str, object]) -> bool:
    ack_path = record.get("ack_path")
    if not isinstance(ack_path, str) or not ack_path:
        return False
    resolved = project_root / ack_path
    return bool(
        resolved.exists()
        and record.get("ack_hash")
        and record.get("direct_router_ack_token_hash")
        and _ack_record_has_complete_receipts(record)
    )

def _audit_valid_ack_file_blocked_role_event(project_root: Path, run_root: Path) -> dict[str, object]:
    ledger, ledger_error = _read_json(run_root / "return_event_ledger.json")
    if ledger_error:
        return {
            "valid_ack_file_blocked_role_event": False,
            "blocked_valid_ack_count": 0,
            "samples": [],
            "read_error": ledger_error,
        }
    records = _return_ledger_records(ledger)
    samples: list[dict[str, object]] = []
    for blocker_path in sorted((run_root / "control_blocks").glob("control-blocker-*.json")):
        blocker, blocker_error = _read_json(blocker_path)
        if not isinstance(blocker, dict):
            continue
        error_code = str(blocker.get("error_code") or "")
        if not error_code.startswith("event_blocked_by_unresolved_card_return"):
            continue
        blocker_created = _parse_time(blocker.get("created_at"))
        if blocker_created is None:
            continue
        for record in records:
            event_name = str(record.get("card_return_event") or "")
            if not event_name or event_name not in error_code:
                continue
            returned_at = _parse_time(record.get("returned_at"))
            resolved_at = _parse_time(record.get("resolved_at") or record.get("checked_at"))
            ack_was_pending_when_blocked = bool(
                returned_at is not None
                and returned_at <= blocker_created
                and (resolved_at is None or resolved_at > blocker_created)
            )
            if not ack_was_pending_when_blocked or not _ack_record_is_valid_direct_ack(project_root, record):
                continue
            samples.append(
                {
                    "blocker_id": blocker.get("blocker_id"),
                    "blocker_path": _rel_run_path(run_root, blocker_path),
                    "originating_event": blocker.get("originating_event"),
                    "error_code": error_code,
                    "card_return_event": event_name,
                    "return_kind": record.get("return_kind") or "system_card",
                    "ack_path": record.get("ack_path"),
                    "ack_returned_at": returned_at.isoformat(),
                    "ledger_resolved_at": resolved_at.isoformat() if resolved_at else None,
                    "blocker_created_at": blocker_created.isoformat(),
                    "ledger_section": record.get("_ledger_section"),
                }
            )
    return {
        "valid_ack_file_blocked_role_event": bool(samples),
        "blocked_valid_ack_count": len(samples),
        "samples": samples,
    }

def _resolution_event_name(value: object) -> str | None:
    if isinstance(value, dict):
        for key in ("event", "corrected_followup_event", "event_name"):
            name = str(value.get(key) or "").strip()
            if name:
                return name
        return None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    parsed: object
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            parsed = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            return text
    return _resolution_event_name(parsed) or text

def _active_pm_repair_followup_event_matchable(router_state: object) -> tuple[bool, bool, dict[str, object]]:
    if not isinstance(router_state, dict):
        return False, True, {}
    active = router_state.get("active_control_blocker")
    if not isinstance(active, dict):
        return False, True, {}
    lane = str(active.get("handling_lane") or "")
    recorded = lane in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES and active.get("pm_repair_decision_status") == "recorded"
    if not recorded:
        return False, True, {}
    raw_events = active.get("allowed_resolution_events")
    allowed_names: list[str] = []
    if isinstance(raw_events, list):
        allowed_names = [name for item in raw_events if (name := _resolution_event_name(item))]
    rerun_target_name = _resolution_event_name(active.get("pm_repair_rerun_target"))
    originating_event = _resolution_event_name(active.get("originating_event"))
    expected_names = {name for name in (rerun_target_name, originating_event) if name}
    matchable = bool(allowed_names) and (not expected_names or bool(set(allowed_names) & expected_names))
    return recorded, matchable, {
        "blocker_id": active.get("blocker_id"),
        "handling_lane": lane,
        "allowed_resolution_events": raw_events,
        "allowed_event_names_after_normalization": allowed_names,
        "pm_repair_rerun_target_name_after_normalization": rerun_target_name,
        "originating_event": originating_event,
    }

def _resolution_event_names(value: object) -> list[str]:
    if isinstance(value, list):
        return [name for item in value if (name := _resolution_event_name(item))]
    name = _resolution_event_name(value)
    return [name] if name else []

def _event_is_non_success_repair_outcome(name: str) -> bool:
    lowered = name.lower()
    return any(
        token in lowered
        for token in (
            "block",
            "protocol",
            "required",
            "missing",
            "reject",
            "fail",
            "materialization",
        )
    )

def _event_is_success_repair_outcome(name: str) -> bool:
    lowered = name.lower()
    return "allow" in lowered or "pass" in lowered or "approve" in lowered

def _rel_run_path(run_root: Path, path: Path) -> str:
    return ".flowpilot/runs/" + run_root.name + "/" + path.relative_to(run_root).as_posix()

def _audit_pm_repair_reissue_liveness(
    project_root: Path,
    run_root: Path,
    router_state: object,
) -> dict[str, object]:
    active = router_state.get("active_control_blocker") if isinstance(router_state, dict) else None
    active = active if isinstance(active, dict) else {}
    lane = str(active.get("handling_lane") or "")
    pm_repair_recorded = lane in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES and active.get(
        "pm_repair_decision_status"
    ) == "recorded"
    allowed_names = _resolution_event_names(active.get("allowed_resolution_events"))
    success_names = [name for name in allowed_names if _event_is_success_repair_outcome(name)]
    non_success_names = [
        name for name in allowed_names if _event_is_non_success_repair_outcome(name)
    ]
    success_only_allowed = bool(success_names) and not non_success_names

    packet_ledger, _packet_ledger_error = _read_json(run_root / "packet_ledger.json")
    ledger_by_id = _ledger_packets_by_id(packet_ledger)
    material_scan_packets, _material_packets_error = _read_json(
        run_root / "material" / "material_scan_packets.json"
    )
    dispatch_packet_ids = (
        {
            str(packet.get("packet_id"))
            for packet in material_scan_packets.get("packets", [])
            if isinstance(packet, dict) and packet.get("packet_id")
        }
        if isinstance(material_scan_packets, dict)
        else set()
    )

    spec_paths = sorted((run_root / "material").glob("pm_material_scan_packet_specs_reissue*.json"))
    packet_details: list[dict[str, object]] = []
    packet_files_materialized = True
    packets_registered = True
    dispatch_index_updated = True
    for spec_path in spec_paths:
        spec, spec_error = _read_json(spec_path)
        spec_rel = _rel_run_path(run_root, spec_path)
        packets = spec.get("packets") if isinstance(spec, dict) else None
        if spec_error or not isinstance(packets, list):
            packet_files_materialized = False
            packets_registered = False
            dispatch_index_updated = False
            packet_details.append(
                {
                    "reissue_spec_path": spec_rel,
                    "read_error": spec_error or "reissue spec did not contain packets list",
                }
            )
            continue
        for packet in packets:
            if not isinstance(packet, dict):
                continue
            packet_id = str(packet.get("packet_id") or "")
            if not packet_id:
                continue
            envelope_rel = (
                f".flowpilot/runs/{run_root.name}/packets/{packet_id}/packet_envelope.json"
            )
            body_rel = f".flowpilot/runs/{run_root.name}/packets/{packet_id}/packet_body.md"
            envelope_exists = (project_root / envelope_rel).exists()
            body_exists = (project_root / body_rel).exists()
            ledger_registered = packet_id in ledger_by_id
            dispatch_registered = packet_id in dispatch_packet_ids or _json_contains(
                material_scan_packets, packet_id
            )
            packet_files_materialized = packet_files_materialized and envelope_exists and body_exists
            packets_registered = packets_registered and ledger_registered
            dispatch_index_updated = dispatch_index_updated and dispatch_registered
            packet_details.append(
                {
                    "packet_id": packet_id,
                    "replacement_for": packet.get("replacement_for"),
                    "reissue_spec_path": spec_rel,
                    "expected_packet_envelope_path": envelope_rel,
                    "expected_packet_body_path": body_rel,
                    "packet_envelope_exists": envelope_exists,
                    "packet_body_exists": body_exists,
                    "registered_in_packet_ledger": ledger_registered,
                    "registered_in_dispatch_index": dispatch_registered,
                }
            )

    protocol_blockers: list[dict[str, object]] = []
    protocol_blockers_routable = True
    control_blocks_root = run_root / "control_blocks"
    if control_blocks_root.exists():
        for blocker_path in sorted(control_blocks_root.glob("*.json")):
            blocker, error = _read_json(blocker_path)
            if not isinstance(blocker, dict):
                continue
            event_name = str(blocker.get("event_name") or "")
            schema = str(blocker.get("schema_version") or "")
            is_recheck_blocker = (
                "protocol_blocker" in schema
                or "protocol_blocker" in event_name
                or blocker.get("can_emit_requested_allowed_event") is False
            )
            if not is_recheck_blocker:
                continue
            rel_path = _rel_run_path(run_root, blocker_path)
            routable = (
                event_name in allowed_names
                or _json_contains(router_state, event_name)
                or _json_contains(router_state, rel_path)
            )
            protocol_blockers_routable = protocol_blockers_routable and routable
            protocol_blockers.append(
                {
                    "path": rel_path,
                    "event_name": event_name or None,
                    "read_error": error,
                    "requested_allowed_event": blocker.get("requested_allowed_event"),
                    "can_emit_requested_allowed_event": blocker.get(
                        "can_emit_requested_allowed_event"
                    ),
                    "routable_by_router_state": routable,
                }
            )

    runtime_ready = (
        packet_files_materialized and packets_registered and dispatch_index_updated
    )
    return {
        "pm_repair_recorded": pm_repair_recorded,
        "reissue_spec_written": bool(spec_paths),
        "packet_files_materialized": packet_files_materialized,
        "packets_registered_in_ledger": packets_registered,
        "dispatch_index_updated": dispatch_index_updated,
        "runtime_ready": runtime_ready,
        "allowed_resolution_event_names": allowed_names,
        "success_only_allowed": success_only_allowed,
        "non_success_outcome_routable": bool(non_success_names),
        "packet_details": packet_details,
        "reviewer_recheck_protocol_blocker_written": bool(protocol_blockers),
        "reviewer_recheck_protocol_blocker_routable": protocol_blockers_routable,
        "reviewer_recheck_protocol_blockers": protocol_blockers,
    }

def _repair_outcome_event_names(active_repair_transaction: object) -> set[str]:
    if not isinstance(active_repair_transaction, dict):
        return set()
    table = active_repair_transaction.get("outcome_table")
    if not isinstance(table, dict):
        return set()
    names: set[str] = set()
    for value in table.values():
        if isinstance(value, dict) and isinstance(value.get("event"), str):
            names.add(value["event"])
    return names

def _audit_stale_repair_lane(router_state: object, frontier: object) -> dict[str, object]:
    if not isinstance(router_state, dict):
        return {
            "active_repair_transaction_stale": False,
            "repair_recheck_pending_action_stale": False,
        }
    flags = router_state.get("flags") if isinstance(router_state.get("flags"), dict) else {}
    active_blocker = router_state.get("active_control_blocker")
    active_repair = router_state.get("active_repair_transaction")
    pending = router_state.get("pending_action")
    frontier_phase = str(frontier.get("phase") or "") if isinstance(frontier, dict) else ""
    frontier_status = str(frontier.get("status") or "") if isinstance(frontier, dict) else ""
    main_flow_advanced = (
        frontier_phase not in {"", "material_scan"}
        or frontier_status not in {"", "material_scan"}
        or bool(flags.get("material_review_sufficient"))
        or bool(flags.get("material_accepted_by_pm"))
        or bool(flags.get("pm_material_understanding_written"))
        or bool(flags.get("pm_product_architecture_card_delivered"))
    )
    outcome_events = _repair_outcome_event_names(active_repair)
    pending_events = set()
    if isinstance(pending, dict):
        pending_events = {
            str(item)
            for item in pending.get("allowed_external_events", [])
            if isinstance(item, str)
        }
    stale_active = bool(active_repair and not isinstance(active_blocker, dict) and main_flow_advanced)
    stale_pending = bool(
        isinstance(pending, dict)
        and pending.get("action_type") == "await_role_decision"
        and not isinstance(active_blocker, dict)
        and (
            pending.get("repair_transaction_id")
            or pending_events.intersection(outcome_events)
            or pending_events.intersection(
                {
                    "reviewer_blocks_material_scan_dispatch_recheck",
                    "reviewer_protocol_blocker_material_scan_dispatch_recheck",
                }
            )
        )
    )
    return {
        "active_repair_transaction_stale": stale_active,
        "repair_recheck_pending_action_stale": stale_pending,
        "active_repair_transaction": active_repair,
        "active_control_blocker": active_blocker,
        "pending_action": pending,
        "frontier_phase": frontier_phase or None,
        "frontier_status": frontier_status or None,
        "main_flow_advanced": main_flow_advanced,
    }

def _external_event_contracts_from_source(source_path: Path) -> tuple[dict[str, dict[str, str]], str | None]:
    try:
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except OSError as exc:
        return {}, f"external event source unreadable: {exc}"
    except SyntaxError as exc:
        return {}, f"external event source unparsable: {exc}"
    literal_defs: dict[str, Any] = {}
    candidates: list[tuple[str, ast.AST]] = []
    for node in tree.body:
        targets: list[str] = []
        value: ast.AST | None = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target.id]
            value = node.value
        elif isinstance(node, ast.Assign):
            targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
            value = node.value
        if value is None or not targets:
            continue
        for target in targets:
            if (
                target == "EXTERNAL_EVENTS"
                or target == "EXTERNAL_EVENT_DATA_BY_PHASE"
                or target.endswith("_EXTERNAL_EVENT_DATA")
            ):
                candidates.append((target, value))
        try:
            parsed = ast.literal_eval(value)
        except (ValueError, SyntaxError) as exc:
            if not any(target in {"EXTERNAL_EVENTS", "EXTERNAL_EVENT_DATA_BY_PHASE"} for target in targets):
                continue
            if isinstance(value, ast.Name) and value.id in literal_defs:
                parsed = literal_defs[value.id]
            else:
                return {}, f"EXTERNAL_EVENTS is not literal-evaluable: {exc}"
        for target in targets:
            literal_defs[target] = parsed
    for target, value in candidates:
        if target not in {"EXTERNAL_EVENTS", "EXTERNAL_EVENT_DATA_BY_PHASE"}:
            continue
        if isinstance(value, ast.Name) and value.id in literal_defs:
            parsed = literal_defs[value.id]
        else:
            try:
                parsed = ast.literal_eval(value)
            except (ValueError, SyntaxError) as exc:
                return {}, f"EXTERNAL_EVENTS is not literal-evaluable: {exc}"
        if not isinstance(parsed, dict):
            return {}, "external event definition was not a dict"
        if parsed and all(isinstance(item, dict) for item in parsed.values()):
            first_value = next(iter(parsed.values()))
            if isinstance(first_value, dict) and all(isinstance(item, dict) for item in first_value.values()):
                flattened: dict[str, Any] = {}
                for phase_events in parsed.values():
                    if isinstance(phase_events, dict):
                        flattened.update(phase_events)
                parsed = flattened
        contracts: dict[str, dict[str, str]] = {}
        for event, meta in parsed.items():
            if isinstance(event, str) and isinstance(meta, dict):
                contracts[event] = {str(key): str(item) for key, item in meta.items() if isinstance(item, str)}
        return contracts, None
    return {}, "external event definition not found"


def _router_external_event_contracts(source_root: Path) -> tuple[dict[str, dict[str, str]], str | None]:
    asset_root = source_root / "skills" / "flowpilot" / "assets"
    phase_contracts: dict[str, dict[str, str]] = {}
    phase_errors: list[str] = []
    for source_path in (
        asset_root / "flowpilot_router_protocol_external_event_data_startup.py",
        asset_root / "flowpilot_router_protocol_external_event_data_material.py",
        asset_root / "flowpilot_router_protocol_external_event_data_route.py",
        asset_root / "flowpilot_router_protocol_external_event_data_terminal.py",
    ):
        contracts, error = _external_event_contracts_from_source(source_path)
        if contracts:
            phase_contracts.update(contracts)
        elif error:
            phase_errors.append(f"{source_path.name}: {error}")
    if phase_contracts:
        return phase_contracts, None
    for source_path in (
        asset_root / "flowpilot_router.py",
        asset_root / "flowpilot_router_protocol_external_events.py",
        asset_root / "flowpilot_router_protocol_external_event_registry.py",
        asset_root / "flowpilot_router_protocol_external_event_data.py",
    ):
        contracts, error = _external_event_contracts_from_source(source_path)
        if contracts:
            return contracts, None
        if error and source_path.name == "flowpilot_router.py":
            router_error = error
    if phase_errors:
        return {}, "; ".join(phase_errors)
    return {}, router_error if "router_error" in locals() else "EXTERNAL_EVENTS definition not found"

def _audit_expected_role_decision_event_prereqs(router_state: object, source_root: Path) -> dict[str, object]:
    if not isinstance(router_state, dict):
        return {
            "expected_role_decision_requires_unsatisfied_flag": False,
            "invalid_expected_events": [],
            "pending_action": None,
        }
    pending = router_state.get("pending_action")
    if not isinstance(pending, dict) or pending.get("action_type") != "await_role_decision":
        return {
            "expected_role_decision_requires_unsatisfied_flag": False,
            "invalid_expected_events": [],
            "pending_action": pending if isinstance(pending, dict) else None,
        }
    events = [
        str(item)
        for item in pending.get("allowed_external_events", [])
        if isinstance(item, str)
    ]
    flags = router_state.get("flags") if isinstance(router_state.get("flags"), dict) else {}
    contracts, contract_error = _router_external_event_contracts(source_root)
    invalid: list[dict[str, object]] = []
    if contract_error:
        invalid.append({"issue": "external_event_contract_unreadable", "error": contract_error})
    for event in events:
        meta = contracts.get(event)
        if not isinstance(meta, dict):
            invalid.append({"event": event, "issue": "unknown_external_event"})
            continue
        required_flag = meta.get("requires_flag")
        if required_flag and not flags.get(required_flag):
            invalid.append(
                {
                    "event": event,
                    "issue": "requires_flag_false",
                    "requires_flag": required_flag,
                    "current_value": flags.get(required_flag),
                }
            )
    return {
        "expected_role_decision_requires_unsatisfied_flag": bool(invalid),
        "invalid_expected_events": invalid,
        "pending_action": pending,
        "allowed_external_events": events,
    }

def _audit_router_internal_postconditions(
    project_root: Path, run_root: Path, router_state: object
) -> dict[str, object]:
    flags = _router_flags(router_state)
    daemon_status, daemon_error = _read_json(run_root / "runtime" / "router_daemon_status.json")
    controller_ledger, ledger_error = _read_json(run_root / "runtime" / "controller_action_ledger.json")
    pending = router_state.get("pending_action") if isinstance(router_state, dict) else None
    current_wait = daemon_status.get("current_wait") if isinstance(daemon_status, dict) else None
    current_wait = current_wait if isinstance(current_wait, dict) else {}
    active_blocker = router_state.get("active_control_blocker") if isinstance(router_state, dict) else None
    active_blocker_text = json.dumps(active_blocker, ensure_ascii=False, sort_keys=True) if active_blocker else ""
    actions = controller_ledger.get("actions") if isinstance(controller_ledger, dict) else []
    actions = actions if isinstance(actions, list) else []

    run_prefix = f".flowpilot/runs/{run_root.name}"
    specs = (
        {
            "event": "capability_evidence_synced",
            "requires_flag": "child_skill_manifest_pm_approved_for_route",
            "event_flag": "capability_evidence_synced",
            "input_paths": (
                f"{run_prefix}/child_skill_gate_manifest.json",
                f"{run_prefix}/child_skill_manifest_pm_approval.json",
                f"{run_prefix}/capabilities.json",
            ),
            "evidence_paths": (f"{run_prefix}/capabilities/capability_sync.json",),
        },
    )
    samples: list[dict[str, object]] = []
    for spec in specs:
        event = str(spec["event"])
        input_paths = tuple(str(path) for path in spec["input_paths"])
        evidence_paths = tuple(str(path) for path in spec["evidence_paths"])
        inputs_ready = bool(flags.get(spec["requires_flag"])) and all(
            (project_root / path).exists() for path in input_paths
        )
        evidence_exists = any((project_root / path).exists() for path in evidence_paths)
        materialized = bool(flags.get(spec["event_flag"])) and evidence_exists
        pending_events = (
            pending.get("allowed_external_events", [])
            if isinstance(pending, dict)
            and pending.get("action_type") == "await_role_decision"
            else []
        )
        wait_events = current_wait.get("allowed_external_events", [])
        exposed_as_role_wait = event in pending_events or event in wait_events
        current_wait_expected = current_wait.get("expected_evidence")
        current_wait_expected = current_wait_expected if isinstance(current_wait_expected, dict) else {}
        expected_evidence_exists = bool(current_wait_expected.get("exists") or evidence_exists)
        executable_action_pending = any(
            isinstance(action, dict)
            and action.get("status") in {"pending", "in_progress"}
            and action.get("ordinary_controller_work_row") is True
            and event in json.dumps(action, ensure_ascii=False, sort_keys=True)
            for action in actions
        )
        blocker_materialized = bool(active_blocker and event in active_blocker_text)
        due = inputs_ready and not materialized
        if due or exposed_as_role_wait:
            samples.append(
                {
                    "event": event,
                    "requires_flag": spec["requires_flag"],
                    "event_flag": spec["event_flag"],
                    "due": due,
                    "inputs_ready": inputs_ready,
                    "input_paths": input_paths,
                    "evidence_paths": evidence_paths,
                    "materialized": materialized,
                    "blocker_materialized": blocker_materialized,
                    "exposed_as_role_wait": exposed_as_role_wait,
                    "expected_evidence_exists": expected_evidence_exists,
                    "executable_action_pending": executable_action_pending,
                    "pending_action_id": pending.get("action_id") if isinstance(pending, dict) else None,
                    "current_wait_label": current_wait.get("label"),
                }
            )
    return {
        "due": any(bool(item.get("due")) for item in samples),
        "inputs_ready": any(bool(item.get("inputs_ready")) for item in samples),
        "materialized": any(bool(item.get("materialized")) for item in samples),
        "blocker_materialized": any(bool(item.get("blocker_materialized")) for item in samples),
        "exposed_as_role_wait": any(bool(item.get("exposed_as_role_wait")) for item in samples),
        "expected_evidence_exists": any(bool(item.get("expected_evidence_exists")) for item in samples),
        "executable_action_pending": any(bool(item.get("executable_action_pending")) for item in samples),
        "samples": samples,
        "daemon_status_error": daemon_error,
        "controller_ledger_error": ledger_error,
    }

def _audit_resolved_obligation_projection_reconciliation(
    run_root: Path, router_state: object
) -> dict[str, object]:
    controller_ledger, ledger_error = _read_json(run_root / "runtime" / "controller_action_ledger.json")
    actions = controller_ledger.get("actions") if isinstance(controller_ledger, dict) else []
    actions = actions if isinstance(actions, list) else []
    active_blocker = router_state.get("active_control_blocker") if isinstance(router_state, dict) else None
    control_blockers = router_state.get("control_blockers") if isinstance(router_state, dict) else []
    control_blockers = control_blockers if isinstance(control_blockers, list) else []
    unresolved = {"open", "registered", "pending", "delivered", "waiting", "active"}
    resolved_control_blocker_exists = active_blocker is None and any(
        isinstance(blocker, dict)
        and (
            bool(blocker.get("resolved_at"))
            or str(blocker.get("resolution_status") or "") not in unresolved
        )
        for blocker in control_blockers
    )
    live_passive_waits = [
        {
            "action_id": action.get("action_id"),
            "label": action.get("label"),
            "status": action.get("status"),
            "updated_at": action.get("updated_at"),
        }
        for action in actions
        if isinstance(action, dict)
        and action.get("status") in {"waiting", "pending", "in_progress"}
        and action.get("controller_projection_kind") == "passive_wait_status"
        and action.get("label") == "controller_waits_for_control_blocker_resolution"
    ]
    ack_files = sorted((run_root / "mailbox" / "outbox" / "card_acks").glob("*.ack.json"))
    blocked_ack_reminders = [
        {
            "action_id": action.get("action_id"),
            "label": action.get("label"),
            "status": action.get("status"),
            "updated_at": action.get("updated_at"),
        }
        for action in actions
        if isinstance(action, dict)
        and action.get("status") == "blocked"
        and action.get("action_type") == "send_wait_target_reminder"
        and "ack" in str(action.get("label") or "").lower()
        and ack_files
    ]
    evidence_exists = bool(resolved_control_blocker_exists or ack_files)
    return {
        "evidence_exists": evidence_exists,
        "resolved_control_blocker_exists": resolved_control_blocker_exists,
        "ack_file_count": len(ack_files),
        "live_passive_wait": bool(live_passive_waits),
        "live_blocked_reminder": bool(blocked_ack_reminders),
        "projection_reconciled": not live_passive_waits and not blocked_ack_reminders,
        "live_passive_wait_samples": live_passive_waits,
        "blocked_reminder_samples": blocked_ack_reminders,
        "controller_ledger_error": ledger_error,
    }

def _required_card_source_rules(run_id: str) -> dict[str, tuple[str, ...]]:
    run_prefix = f".flowpilot/runs/{run_id}"
    return {
        "pm.product_architecture": (
            f"{run_prefix}/pm_material_understanding.json",
            f"{run_prefix}/material/pm_material_understanding_payload.json",
        ),
        "flowguard_operator.product_architecture_modelability": (
            f"{run_prefix}/product_function_architecture.json",
        ),
        "reviewer.product_architecture_challenge": (
            f"{run_prefix}/product_function_architecture.json",
            f"{run_prefix}/flowguard/product_architecture_modelability.json",
        ),
        "pm.root_contract": (
            f"{run_prefix}/product_function_architecture.json",
            f"{run_prefix}/reviews/product_architecture_challenge.json",
            f"{run_prefix}/flowguard/product_architecture_modelability.json",
        ),
        "reviewer.root_contract_challenge": (
            f"{run_prefix}/root_acceptance_contract.json",
            f"{run_prefix}/standard_scenario_pack.json",
        ),
        "flowguard_operator_product_scope.root_contract_modelability": (
            f"{run_prefix}/root_acceptance_contract.json",
            f"{run_prefix}/standard_scenario_pack.json",
        ),
        "pm.dependency_policy": (
            f"{run_prefix}/root_acceptance_contract.json",
            f"{run_prefix}/product_function_architecture.json",
        ),
        "pm.child_skill_selection": (
            f"{run_prefix}/dependency_policy.json",
            f"{run_prefix}/capabilities.json",
        ),
        "pm.child_skill_gate_manifest": (
            f"{run_prefix}/capabilities.json",
            f"{run_prefix}/pm_child_skill_selection.json",
            f"{run_prefix}/root_acceptance_contract.json",
        ),
        "reviewer.child_skill_gate_manifest_review": (
            f"{run_prefix}/child_skill_gate_manifest.json",
            f"{run_prefix}/pm_child_skill_selection.json",
            f"{run_prefix}/capabilities.json",
        ),
        "flowguard_operator_route_scope.child_skill_conformance_model": (
            f"{run_prefix}/child_skill_gate_manifest.json",
            f"{run_prefix}/reviews/child_skill_gate_manifest_review.json",
            f"{run_prefix}/pm_child_skill_selection.json",
            f"{run_prefix}/capabilities.json",
        ),
        "flowguard_operator_product_scope.child_skill_product_fit": (
            f"{run_prefix}/child_skill_gate_manifest.json",
            f"{run_prefix}/reviews/child_skill_gate_manifest_review.json",
            f"{run_prefix}/flowguard/child_skill_conformance_model.json",
            f"{run_prefix}/pm_child_skill_selection.json",
            f"{run_prefix}/capabilities.json",
            f"{run_prefix}/root_acceptance_contract.json",
        ),
        "pm.prior_path_context": (
            f"{run_prefix}/child_skill_gate_manifest.json",
            f"{run_prefix}/child_skill_manifest_pm_approval.json",
            f"{run_prefix}/capabilities/capability_sync.json",
        ),
        "pm.route_skeleton": (
            f"{run_prefix}/root_acceptance_contract.json",
            f"{run_prefix}/child_skill_gate_manifest.json",
            f"{run_prefix}/child_skill_manifest_pm_approval.json",
            f"{run_prefix}/capabilities/capability_sync.json",
            f"{run_prefix}/route_memory/pm_prior_path_context.json",
        ),
        "flowguard_operator.route_process_check": (
            f"{run_prefix}/root_acceptance_contract.json",
            f"{run_prefix}/child_skill_gate_manifest.json",
            f"{run_prefix}/capabilities/capability_sync.json",
            f"{run_prefix}/routes/route-001/flow.draft.json",
        ),
        "reviewer.route_challenge": (
            f"{run_prefix}/root_acceptance_contract.json",
            f"{run_prefix}/child_skill_gate_manifest.json",
            f"{run_prefix}/flowguard/route_process_check.json",
            f"{run_prefix}/flowguard/process_route_model_pm_decision.json",
            f"{run_prefix}/flowguard/product_behavior_model.json",
            f"{run_prefix}/routes/route-001/flow.draft.json",
        ),
    }

def _expected_card_phases() -> dict[str, str]:
    return {
        "pm.product_architecture": "product_architecture",
        "flowguard_operator.product_architecture_modelability": "product_architecture",
        "reviewer.product_architecture_challenge": "product_architecture",
        "pm.root_contract": "root_contract",
        "reviewer.root_contract_challenge": "root_contract",
        "flowguard_operator_product_scope.root_contract_modelability": "root_contract",
        "pm.dependency_policy": "dependency_policy",
        "pm.child_skill_selection": "child_skill_selection",
        "pm.child_skill_gate_manifest": "child_skill_gate_manifest",
        "reviewer.child_skill_gate_manifest_review": "child_skill_gate_manifest",
        "flowguard_operator_route_scope.child_skill_conformance_model": "child_skill_gate_manifest",
        "flowguard_operator_product_scope.child_skill_product_fit": "child_skill_gate_manifest",
        "pm.prior_path_context": "prior_path_context",
        "pm.route_skeleton": "route_skeleton",
        "flowguard_operator.route_process_check": "route_skeleton",
        "reviewer.route_challenge": "route_skeleton",
    }

def _audit_card_delivery_context(
    *,
    prompt_deliveries: object,
    run_id: str,
    project_root: Path,
) -> tuple[list[dict[str, object]], list[dict[str, object]], bool]:
    missing_sources: list[dict[str, object]] = []
    stale_phases: list[dict[str, object]] = []
    delivered_any = False
    required_sources = _required_card_source_rules(run_id)
    expected_phases = _expected_card_phases()
    for card_id, required_paths in required_sources.items():
        delivery = _latest_delivery(prompt_deliveries, card_id)
        if not delivery:
            continue
        delivered_any = True
        source_values = _delivery_source_values(delivery)
        missing = [path for path in required_paths if path not in source_values]
        if missing:
            missing_sources.append(
                {
                    "card_id": card_id,
                    "delivered_at": delivery.get("delivered_at"),
                    "missing_source_paths": missing,
                    "required_source_paths": list(required_paths),
                    "actual_source_paths": sorted(source_values),
                    "required_files_exist": {
                        path: (project_root / path).exists()
                        for path in required_paths
                    },
                }
            )
        expected_phase = expected_phases.get(card_id)
        actual_phase = (
            delivery.get("delivery_context", {})
            .get("current_stage", {})
            .get("current_phase")
        )
        if expected_phase and actual_phase != expected_phase:
            stale_phases.append(
                {
                    "card_id": card_id,
                    "delivered_at": delivery.get("delivered_at"),
                    "expected_phase": expected_phase,
                    "actual_phase": actual_phase,
                }
            )
    return missing_sources, stale_phases, delivered_any

def _audit_child_skill_gate_sync(run_root: Path) -> tuple[bool, dict[str, object]]:
    manifest, manifest_error = _read_json(run_root / "child_skill_gate_manifest.json")
    review, review_error = _read_json(run_root / "reviews" / "child_skill_gate_manifest_review.json")
    if manifest_error or review_error or not isinstance(manifest, dict) or not isinstance(review, dict):
        return True, {
            "manifest_error": manifest_error,
            "review_error": review_error,
        }
    approval = manifest.get("approval")
    if not isinstance(approval, dict):
        approval = {}
    review_passed = review.get("passed") is True
    manifest_reviewer_passed = approval.get("reviewer_passed") is True
    synced = (not review_passed) or manifest_reviewer_passed
    return synced, {
        "manifest_status": manifest.get("status"),
        "manifest_reviewer_passed": approval.get("reviewer_passed"),
        "review_passed": review.get("passed"),
        "manifest_path": ".flowpilot/runs/" + run_root.name + "/child_skill_gate_manifest.json",
        "review_path": ".flowpilot/runs/" + run_root.name + "/reviews/child_skill_gate_manifest_review.json",
    }

def _gate_key_for_outcome_event(event: object) -> str:
    if event in {"reviewer_blocks_child_skill_gate_manifest", "reviewer_passes_child_skill_gate_manifest"}:
        return "child_skill_gate_manifest"
    if event in {"flowguard_operator_route_scope_blocks_child_skill_conformance_model", "flowguard_operator_route_scope_passes_child_skill_conformance_model"}:
        return "child_skill_conformance_model"
    if event in {"flowguard_operator_product_scope_blocks_child_skill_product_fit", "flowguard_operator_product_scope_passes_child_skill_product_fit"}:
        return "child_skill_product_fit"
    return "unknown"

def _audit_gate_outcome_lifecycle(router_state: object) -> dict[str, object]:
    flags = _router_flags(router_state)
    active = router_state.get("active_gate_outcome_block") if isinstance(router_state, dict) else None
    active_event = active.get("event") if isinstance(active, dict) else None
    active_key = _gate_key_for_outcome_event(active_event)
    child_passed = flags.get("child_skill_manifest_reviewer_passed") is True
    pass_key = "child_skill_gate_manifest" if child_passed else "none"
    same_key = bool(child_passed and isinstance(active, dict) and active_key == pass_key)
    return {
        "gate_outcome_block_active": isinstance(active, dict),
        "gate_outcome_block_gate_key": active_key if isinstance(active, dict) else "none",
        "gate_outcome_pass_recorded": child_passed,
        "gate_outcome_pass_gate_key": pass_key,
        "gate_outcome_same_generation": True,
        "gate_outcome_clear_target_matches_pass_gate": True,
        "same_gate_active_block_after_pass": same_key,
        "active_gate_outcome_block_event": active_event,
        "active_gate_outcome_block_report_path": active.get("report_path") if isinstance(active, dict) else None,
    }

def _terminal_snapshot_flags_consistent(snapshot: object, router_state: object, current: object) -> tuple[bool, dict[str, object]]:
    if not isinstance(snapshot, dict):
        return True, {"snapshot_present": False}
    state = snapshot.get("state") if isinstance(snapshot.get("state"), dict) else {}
    flags = state.get("flags") if isinstance(state.get("flags"), dict) else {}
    router_flags = _router_flags(router_state)
    terminal_status = (
        (isinstance(current, dict) and current.get("status") == "stopped_by_user")
        or (isinstance(router_state, dict) and router_state.get("status") == "stopped_by_user")
        or state.get("status") == "stopped_by_user"
    )
    if not terminal_status:
        return True, {"terminal_status": False}
    snapshot_flag = flags.get("run_stopped_by_user")
    router_flag = router_flags.get("run_stopped_by_user")
    consistent = snapshot_flag is True and (router_flag is not False)
    return consistent, {
        "terminal_status": True,
        "snapshot_state_status": state.get("status"),
        "snapshot_flag_run_stopped_by_user": snapshot_flag,
        "router_flag_run_stopped_by_user": router_flag,
    }

def _terminal_continuation_cleanup_proven(project_root: Path, run_root: Path, current: object, router_state: object) -> tuple[bool, dict[str, object]]:
    terminal_status = (
        (isinstance(current, dict) and current.get("status") == "stopped_by_user")
        or (isinstance(router_state, dict) and router_state.get("status") == "stopped_by_user")
    )
    if not terminal_status:
        return True, {"terminal_status": False}
    binding, error = _read_json(run_root / "continuation" / "continuation_binding.json")
    if error or not isinstance(binding, dict):
        return False, {"terminal_status": True, "binding_error": error}
    automation_id = str(binding.get("host_automation_id") or "")
    automation_path = Path.home() / ".codex" / "automations" / automation_id / "automation.toml"
    cleanup_status = binding.get("host_automation_cleanup_status")
    automation_exists = automation_path.exists() if automation_id else None
    proven = (
        binding.get("manual_resume_binding_active") is False
        and cleanup_status not in {"external_cleanup_may_be_required", "unknown", None}
    )
    if automation_id and not automation_exists and cleanup_status != "missing_verified":
        proven = False
    return proven, {
        "terminal_status": True,
        "manual_resume_binding_active": binding.get("manual_resume_binding_active"),
        "host_automation_id": automation_id or None,
        "host_automation_cleanup_status": cleanup_status,
        "automation_toml_exists": automation_exists,
        "checked_path": str(automation_path) if automation_id else None,
    }

def _role_output_semantic_hash(path: Path) -> str | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    body = dict(payload)
    body.pop("_role_output_envelope", None)
    return hashlib.sha256((json.dumps(body, indent=2, sort_keys=True) + "\n").encode("utf-8")).hexdigest()

def _role_output_semantic_hashes(path: Path) -> set[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return set()
    if not isinstance(payload, dict):
        return set()
    body = dict(payload)
    body.pop("_role_output_envelope", None)
    canonical_lf = json.dumps(body, indent=2, sort_keys=True) + "\n"
    variants = {canonical_lf, canonical_lf.replace("\n", "\r\n")}
    return {hashlib.sha256(variant.encode("utf-8")).hexdigest() for variant in variants}

def _audit_role_output_hashes(project_root: Path, run_root: Path) -> tuple[bool, list[dict[str, object]], int]:
    mismatches: list[dict[str, object]] = []
    envelope_count = 0
    if not run_root.exists():
        return True, mismatches, envelope_count
    for path in sorted(run_root.rglob("*.json")):
        payload, error = _read_json(path)
        if error or not isinstance(payload, dict):
            continue
        envelope = payload.get("_role_output_envelope")
        if not isinstance(envelope, dict):
            continue
        body_path = envelope.get("body_path")
        expected_hash = envelope.get("body_hash")
        if not isinstance(body_path, str) or not isinstance(expected_hash, str):
            continue
        envelope_count += 1
        resolved = project_root / body_path
        if not resolved.exists():
            mismatches.append(
                {
                    "path": path.relative_to(project_root).as_posix(),
                    "issue": "missing_body_path",
                    "body_path": body_path,
                    "declared_hash": expected_hash,
                }
            )
            continue
        actual_hash = hashlib.sha256(resolved.read_bytes()).hexdigest()
        semantic_hash = _role_output_semantic_hash(resolved)
        accepted_hashes = {actual_hash}
        accepted_hashes.update(_role_output_semantic_hashes(resolved))
        if expected_hash not in accepted_hashes:
            mismatches.append(
                {
                    "path": path.relative_to(project_root).as_posix(),
                    "issue": "body_hash_mismatch",
                    "body_path": body_path,
                    "declared_hash": expected_hash,
                    "actual_hash": actual_hash,
                    "semantic_hash": semantic_hash,
                }
            )
    return not mismatches, mismatches, envelope_count

def _valid_startup_mechanical_audit_artifact(project_root: Path, run_root: Path) -> dict[str, object]:
    audit_path = run_root / "startup" / "startup_mechanical_audit.json"
    proof_path = run_root / "startup" / "startup_mechanical_audit.json.proof.json"
    audit, audit_error = _read_json(audit_path)
    proof, proof_error = _read_json(proof_path)
    audit_hash = hashlib.sha256(audit_path.read_bytes()).hexdigest() if audit_path.exists() else None
    proof_matches_audit = bool(
        isinstance(proof, dict)
        and audit_hash
        and proof.get("audit_sha256") == audit_hash
    )
    valid = bool(
        isinstance(audit, dict)
        and audit.get("schema_version") == "flowpilot.startup_mechanical_audit.v1"
        and audit.get("run_id") == run_root.name
        and isinstance(proof, dict)
        and proof.get("schema_version") == "flowpilot.router_owned_check_proof.v1"
        and proof_matches_audit
    )
    return {
        "valid": valid,
        "audit_path": ".flowpilot/runs/" + run_root.name + "/startup/startup_mechanical_audit.json",
        "proof_path": ".flowpilot/runs/" + run_root.name + "/startup/startup_mechanical_audit.json.proof.json",
        "audit_exists": audit_path.exists(),
        "proof_exists": proof_path.exists(),
        "audit_read_error": audit_error,
        "proof_read_error": proof_error,
        "proof_matches_audit": proof_matches_audit,
        "audit_hash": audit_hash,
    }

def _audit_evidence_closure_blockers(
    project_root: Path, run_root: Path
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    display_gaps: list[dict[str, object]] = []
    durable_reclaim_gaps: list[dict[str, object]] = []
    stateful_gaps: list[dict[str, object]] = []
    role_output_gaps: list[dict[str, object]] = []
    control_blocks_root = run_root / "control_blocks"
    if not control_blocks_root.exists():
        return display_gaps, durable_reclaim_gaps, stateful_gaps, role_output_gaps

    for blocker_path in sorted(control_blocks_root.glob("control-blocker-*.json")):
        if (
            blocker_path.name.endswith(".sealed_repair_packet.json")
            or ".pm_repair_decision." in blocker_path.name
        ):
            continue
        blocker, error = _read_json(blocker_path)
        if not isinstance(blocker, dict):
            continue
        if blocker.get("schema_version") != "flowpilot.control_blocker.v1":
            continue
        rel_path = ".flowpilot/runs/" + run_root.name + "/" + blocker_path.relative_to(run_root).as_posix()
        error_code = str(blocker.get("error_code") or "")
        source = str(blocker.get("source") or "")
        item = {
            "path": rel_path,
            "blocker_id": blocker.get("blocker_id"),
            "error_code": error_code,
            "source": source,
            "originating_action_type": blocker.get("originating_action_type"),
            "originating_event": blocker.get("originating_event"),
            "handling_lane": blocker.get("handling_lane"),
            "delivery_status": blocker.get("delivery_status"),
            "read_error": error,
        }
        is_postcondition_gap = (
            source == "controller_action_receipt_missing_stateful_postcondition"
            or "postcondition" in error_code
        )
        originating_action_type = str(blocker.get("originating_action_type") or "")
        if is_postcondition_gap and originating_action_type == "sync_display_plan":
            display_gaps.append(item)
        elif is_postcondition_gap and originating_action_type == "write_startup_mechanical_audit":
            artifact = _valid_startup_mechanical_audit_artifact(project_root, run_root)
            if artifact["valid"]:
                durable_reclaim_gaps.append({**item, "router_owned_artifact": artifact})
            else:
                stateful_gaps.append({**item, "router_owned_artifact": artifact})
        elif is_postcondition_gap:
            stateful_gaps.append(item)
        if error_code == "role_event_requires_a_file_backed_body_path":
            role_output_gaps.append(item)
    return display_gaps, durable_reclaim_gaps, stateful_gaps, role_output_gaps

def _audit_pm_role_work_unit_identity(
    run_root: Path, router_state: object
) -> dict[str, object]:
    reused_samples: list[dict[str, object]] = []
    missing_scope_samples: list[dict[str, object]] = []
    actions_root = run_root / "runtime" / "controller_actions"
    if actions_root.exists():
        for action_path in sorted(actions_root.glob("*.json")):
            record, error = _read_json(action_path)
            if not isinstance(record, dict):
                continue
            nested = record.get("action")
            action = nested if isinstance(nested, dict) else record
            if action.get("action_type") != "relay_pm_role_work_request_packet":
                continue
            rel_path = ".flowpilot/runs/" + run_root.name + "/" + action_path.relative_to(run_root).as_posix()
            required = {
                "batch_id": action.get("batch_id"),
                "request_id": action.get("request_id"),
                "packet_id": action.get("packet_id") or action.get("packet_ids"),
                "to_role": action.get("to_role"),
            }
            missing = [key for key, value in required.items() if not value]
            if missing:
                missing_scope_samples.append(
                    {
                        "path": rel_path,
                        "action_id": record.get("action_id"),
                        "missing_fields": missing,
                        "read_error": error,
                    }
                )

            reconciliation = record.get("router_reconciliation")
            reconciliation = reconciliation if isinstance(reconciliation, dict) else {}
            lifecycle = reconciliation.get("batch_lifecycle")
            lifecycle = lifecycle if isinstance(lifecycle, dict) else {}
            old_batch_id = lifecycle.get("batch_id")
            old_roles = str(record.get("to_role") or "")
            new_role = str(action.get("to_role") or "")
            top_completed = _parse_time(record.get("completed_at"))
            nested_created = _parse_time(action.get("created_at"))
            nested_after_done = bool(top_completed and nested_created and nested_created > top_completed)
            batch_changed = bool(old_batch_id and action.get("batch_id") and old_batch_id != action.get("batch_id"))
            role_changed = bool(old_roles and new_role and old_roles != new_role)
            if record.get("status") == "done" and isinstance(nested, dict) and (
                nested_after_done or batch_changed or role_changed
            ):
                reused_samples.append(
                    {
                        "path": rel_path,
                        "controller_action_id": record.get("action_id"),
                        "top_status": record.get("status"),
                        "top_created_at": record.get("created_at"),
                        "top_completed_at": record.get("completed_at"),
                        "nested_created_at": action.get("created_at"),
                        "old_batch_id": old_batch_id,
                        "new_batch_id": action.get("batch_id"),
                        "old_to_role": old_roles,
                        "new_to_role": new_role,
                    }
                )

    pm_index, pm_index_error = _read_json(run_root / "pm_work_requests" / "index.json")
    flags = _router_flags(router_state)
    unresolved_statuses = {"open", "registered", "packet_relayed", "active", "waiting", "in_progress"}
    unresolved_requests: list[dict[str, object]] = []
    if isinstance(pm_index, dict):
        active_request_ids = {
            str(item)
            for item in pm_index.get("active_request_ids", [])
            if isinstance(item, str)
        }
        active_request = pm_index.get("active_request_id")
        if isinstance(active_request, str):
            active_request_ids.add(active_request)
        for request in pm_index.get("requests", []):
            if not isinstance(request, dict):
                continue
            request_id = str(request.get("request_id") or "")
            status = str(request.get("status") or "")
            if request_id in active_request_ids and status in unresolved_statuses:
                unresolved_requests.append(
                    {
                        "request_id": request_id,
                        "batch_id": request.get("batch_id"),
                        "packet_id": request.get("packet_id"),
                        "to_role": request.get("to_role"),
                        "status": status,
                    }
                )
    global_postcondition_masks_open_request = bool(
        flags.get("pm_role_work_request_packet_relayed") and unresolved_requests
    )
    return {
        "identity_scoped": not missing_scope_samples,
        "closed_identity_reused": bool(reused_samples),
        "missing_scope_samples": missing_scope_samples,
        "reused_samples": reused_samples,
        "request_postcondition_scoped": not global_postcondition_masks_open_request,
        "global_postcondition_masks_open_request": global_postcondition_masks_open_request,
        "global_postcondition_flag": flags.get("pm_role_work_request_packet_relayed"),
        "unresolved_active_requests": unresolved_requests,
        "pm_index_error": pm_index_error,
    }

def _audit_controller_delivery_success(run_root: Path) -> dict[str, object]:
    failures: list[dict[str, object]] = []
    receipts_root = run_root / "runtime" / "controller_receipts"
    if not receipts_root.exists():
        return {"ok": True, "failures": failures}
    for receipt_path in sorted(receipts_root.glob("*.json")):
        receipt, error = _read_json(receipt_path)
        if not isinstance(receipt, dict):
            continue
        if receipt.get("status") != "done":
            continue
        payload = receipt.get("payload")
        packets = payload.get("packets") if isinstance(payload, dict) else []
        if not isinstance(packets, list):
            continue
        for packet in packets:
            if not isinstance(packet, dict):
                continue
            delivery_status = str(packet.get("message_delivery_status") or "")
            if delivery_status and delivery_status != "delivered":
                failures.append(
                    {
                        "path": ".flowpilot/runs/" + run_root.name + "/" + receipt_path.relative_to(run_root).as_posix(),
                        "action_id": receipt.get("action_id"),
                        "packet_id": packet.get("packet_id"),
                        "target_role": packet.get("target_role"),
                        "target_agent_id": packet.get("target_agent_id"),
                        "message_delivery_status": delivery_status,
                        "message_delivery_error": packet.get("message_delivery_error"),
                        "read_error": error,
                    }
                )
    return {"ok": not failures, "failures": failures}

def _audit_active_holder_liveness(run_root: Path) -> dict[str, object]:
    role_recovery, _role_recovery_error = _read_json(
        run_root / "continuation" / "role_recovery" / "latest_transaction.json"
    )
    missing_agent_ids: set[str] = set()
    if isinstance(role_recovery, dict):
        fault_payload = role_recovery.get("fault_payload")
        fault_payload = fault_payload if isinstance(fault_payload, dict) else {}
        probe = fault_payload.get("liveness_probe")
        probe = probe if isinstance(probe, dict) else {}
        if probe.get("result") == "missing":
            detail = str(probe.get("detail") or "")
            for token in detail.replace(";", " ").split():
                if token.startswith("019"):
                    missing_agent_ids.add(token)

    delivery_audit = _audit_controller_delivery_success(run_root)
    for failure in delivery_audit.get("failures", []):
        target_agent_id = failure.get("target_agent_id")
        if isinstance(target_agent_id, str) and target_agent_id:
            missing_agent_ids.add(target_agent_id)

    lease_issues: list[dict[str, object]] = []
    lease_count = 0
    for lease_path in sorted(run_root.glob("packets/*/active_holder_lease.json")):
        lease, error = _read_json(lease_path)
        if not isinstance(lease, dict):
            continue
        lease_count += 1
        holder_agent_id = str(lease.get("holder_agent_id") or "")
        holder_role = str(lease.get("holder_role") or "")
        packet_id = str(lease.get("packet_id") or "")
        packet_role_matches = True
        envelope, _envelope_error = _read_json(lease_path.parent / "packet_envelope.json")
        if isinstance(envelope, dict):
            packet_role_matches = str(envelope.get("to_role") or "") == holder_role
        host_live = holder_agent_id not in missing_agent_ids
        if not holder_agent_id or not holder_role or not packet_role_matches or not host_live:
            lease_issues.append(
                {
                    "path": ".flowpilot/runs/" + run_root.name + "/" + lease_path.relative_to(run_root).as_posix(),
                    "packet_id": packet_id,
                    "holder_role": holder_role or None,
                    "holder_agent_id": holder_agent_id or None,
                    "agent_identity_recorded": bool(holder_agent_id),
                    "host_live": host_live,
                    "packet_role_matches": packet_role_matches,
                    "read_error": error,
                }
            )
    return {
        "lease_count": lease_count,
        "lease_issues": lease_issues,
        "agent_identity_recorded": not any(not item["agent_identity_recorded"] for item in lease_issues),
        "host_live": not any(not item["host_live"] for item in lease_issues),
        "packet_role_matches": not any(not item["packet_role_matches"] for item in lease_issues),
    }

def _audit_packet_ledger_corruption(run_root: Path) -> dict[str, object]:
    corrupt_backups: list[dict[str, object]] = []
    for backup_path in sorted(run_root.glob("packet_ledger.corrupt-backup-*.json")):
        _payload, error = _read_json(backup_path)
        if error:
            corrupt_backups.append(
                {
                    "path": ".flowpilot/runs/" + run_root.name + "/" + backup_path.relative_to(run_root).as_posix(),
                    "read_error": error,
                }
            )
    events_text, events_error = _read_text(run_root / "runtime" / "router_daemon_events.jsonl")
    daemon_crashed = "router_daemon_error" in events_text and (
        "JSONDecodeError" in events_text or "Extra data" in events_text
    )
    return {
        "corrupt_backup_count": len(corrupt_backups),
        "corrupt_backups": corrupt_backups,
        "daemon_crashed_on_corrupt_read": bool(corrupt_backups and daemon_crashed),
        "events_read_error": events_error,
    }

def _audit_material_gate_evidence_contract(run_root: Path) -> dict[str, object]:
    reports = sorted((run_root / "reviews").glob("material_sufficiency_report-*.json"))
    self_check_samples: list[dict[str, object]] = []
    authority_samples: list[dict[str, object]] = []
    for report_path in reports:
        report, error = _read_json(report_path)
        if not isinstance(report, dict):
            continue
        blockers = report.get("blockers")
        if not isinstance(blockers, list):
            blockers = []
        for blocker in blockers:
            if not isinstance(blocker, dict):
                continue
            blocker_id = str(blocker.get("blocker_id") or "")
            item = {
                "path": ".flowpilot/runs/" + run_root.name + "/" + report_path.relative_to(run_root).as_posix(),
                "blocker_id": blocker_id,
                "description": blocker.get("description"),
                "read_error": error,
            }
            if "contract-self-check" in blocker_id:
                self_check_samples.append(item)
            if "review-access-mismatch" in blocker_id:
                authority_samples.append(item)
    depends_on_result_body = bool(self_check_samples or authority_samples)
    return {
        "depends_on_result_body": depends_on_result_body,
        "result_self_check_machine_parseable": not self_check_samples,
        "result_reader_authority_matches_runtime": not authority_samples,
        "self_check_samples": self_check_samples,
        "authority_samples": authority_samples,
    }

def audit_live_run(
    project_root: str | Path = ".",
    *,
    source_root: str | Path | None = None,
) -> dict[str, object]:
    """Project the current .flowpilot run into this model's invariants.

    This is intentionally read-only. It catches file-level control-plane
    friction that the abstract state graph alone cannot see.
    """

    root = Path(project_root).resolve()
    source = Path(source_root).resolve() if source_root is not None else root
    resolution = control_surface.resolve_current_run(root)
    current_path = root / ".flowpilot" / "current.json"
    current, current_error = _read_json(current_path)
    if not resolution.ok:
        missing_current_pointer = resolution.error_code == "missing_file"
        return {
            "ok": missing_current_pointer,
            "skipped": missing_current_pointer,
            "skip_reason": (
                "skipped_with_reason: .flowpilot/current.json is missing; "
                "no current live-run audit can be claimed"
            ) if missing_current_pointer else None,
            "run_id": resolution.run_id,
            "run_root": resolution.run_root.as_posix() if resolution.run_root else "",
            "finding_count": 0 if missing_current_pointer else 1,
            "error_count": 0 if missing_current_pointer else 1,
            "warning_count": 0,
            "findings": [] if missing_current_pointer else [resolution.finding()],
            "current_run_projection": {
                "status": "missing_current_pointer",
                "current_run_can_continue": False,
                "safe_to_claim_live_run_confidence": False,
                "metadata_only": True,
            } if missing_current_pointer else None,
            "projected_invariant_failures": [],
        }
    if not isinstance(current, dict):
        return {
            "ok": False,
            "skipped": False,
            "findings": [
                {
                    "code": "current_pointer_unreadable",
                    "severity": "error",
                    "summary": "current.json did not contain a JSON object",
                    "matched_invariant": "live_run_pointer_readable",
                    "evidence": {"path": current_path.as_posix()},
                }
            ],
            "projected_invariant_failures": [],
        }

    run_id = resolution.run_id
    run_root = resolution.run_root
    assert run_root is not None
    try:
        run_root_rel = run_root.relative_to(root).as_posix()
    except ValueError:
        run_root_rel = run_root.as_posix()
    findings: list[dict[str, object]] = []
    router_state, router_error = _read_json(run_root / "router_state.json")
    prompt_ledger, prompt_error = _read_json(run_root / "prompt_delivery_ledger.json")
    frontier, frontier_error = _read_json(run_root / "execution_frontier.json")
    snapshot, snapshot_error = _read_json(run_root / "route_state_snapshot.json")
    display_plan, display_error = _read_json(run_root / "display_plan.json")
    index, index_error = _read_json(root / ".flowpilot" / "index.json")
    runtime_ledger, runtime_ledger_error = _read_json(run_root / "ledger.json")
    for evidence_name, evidence_path, read_error in (
        ("router_state", run_root / "router_state.json", router_error),
        ("prompt_delivery_ledger", run_root / "prompt_delivery_ledger.json", prompt_error),
        ("execution_frontier", run_root / "execution_frontier.json", frontier_error),
        ("route_state_snapshot", run_root / "route_state_snapshot.json", snapshot_error),
        ("display_plan", run_root / "display_plan.json", display_error),
        ("index", root / ".flowpilot" / "index.json", index_error),
    ):
        if read_error and not read_error.startswith("missing file:"):
            _add_finding(
                findings,
                code="control_surface_evidence_unreadable",
                severity="error",
                summary=f"{evidence_name} could not be read as structured JSON",
                invariant="evidence_reads_are_structured",
                evidence={
                    "evidence_name": evidence_name,
                    "path": evidence_path.as_posix(),
                    "read_error": read_error,
                },
            )
    if isinstance(runtime_ledger, dict):
        findings.extend(control_surface.audit_packet_contracts(runtime_ledger))
    elif runtime_ledger_error:
        _add_finding(
            findings,
            code="runtime_ledger_unreadable",
            severity="error",
            summary="current-run ledger could not be read as UTF-8 JSON",
            invariant="role_packets_share_symmetric_control_surface_contract",
            evidence={
                "path": (run_root / "ledger.json").as_posix(),
                "read_error": runtime_ledger_error,
            },
        )
    flags = _router_flags(router_state)
    prompt_deliveries = prompt_ledger.get("deliveries") if isinstance(prompt_ledger, dict) else []
    product_delivery = _latest_delivery(prompt_deliveries, "pm.product_architecture")
    product_delivery_at = _parse_time(product_delivery.get("delivered_at")) if product_delivery else None
    required_material_paths = {
        f".flowpilot/runs/{run_id}/pm_material_understanding.json",
        f".flowpilot/runs/{run_id}/material/pm_material_understanding_payload.json",
    }
    material_source_values = _delivery_source_values(product_delivery)
    material_context_present = required_material_paths.issubset(material_source_values)
    pm_material_written = bool(
        flags.get("material_understanding_written_by_pm")
        or flags.get("pm_material_understanding_written_by_pm")
        or (run_root / "pm_material_understanding.json").exists()
    )
    pm_material_source_available = all((root / path).exists() for path in required_material_paths)
    product_architecture_delivered = bool(product_delivery or flags.get("pm_product_architecture_card_delivered"))
    product_stage_advanced = bool(
        product_architecture_delivered
        or flags.get("product_architecture_written_by_pm")
        or flags.get("product_architecture_modelability_passed")
        or flags.get("product_architecture_reviewer_passed")
    )
    phase_missing_sources, phase_stale_contexts, phase_dependency_cards_delivered = _audit_card_delivery_context(
        prompt_deliveries=prompt_deliveries,
        run_id=run_id,
        project_root=root,
    )
    route_draft_paths = sorted((run_root / "routes").glob("*/flow.draft.json"))
    route_draft_written = bool(route_draft_paths)
    route_draft_node_counts: dict[str, int] = {}
    route_draft_has_nodes = True
    for draft_path in route_draft_paths:
        draft, draft_error = _read_json(draft_path)
        rel = ".flowpilot/runs/" + run_root.name + "/" + draft_path.relative_to(run_root).as_posix()
        nodes = draft.get("nodes") if isinstance(draft, dict) else None
        node_count = len(nodes) if isinstance(nodes, list) else 0
        route_draft_node_counts[rel] = node_count
        if draft_error or node_count == 0:
            route_draft_has_nodes = False
    route_process_check_delivered = _latest_delivery(prompt_deliveries, "flowguard_operator.route_process_check") is not None
    route_process_check_passed = bool(flags.get("flowguard_operator_route_scope_route_check_passed"))
    material_dispatch = _audit_material_scan_dispatch_integrity(
        project_root=root,
        run_root=run_root,
        router_state=router_state,
        frontier=frontier,
    )
    if material_dispatch.get("requested") and not material_dispatch.get("phase_context_consistent"):
        _add_finding(
            findings,
            code="material_dispatch_phase_mismatch",
            severity="error",
            summary="material scan dispatch request saw router_state and execution_frontier disagree about the material_scan phase",
            invariant="material_scan_dispatch_requires_packet_integrity",
            evidence={
                "phase_evidence": material_dispatch.get("phase_evidence"),
                "reviewed": material_dispatch.get("reviewed"),
            },
        )
    if material_dispatch.get("requested") and not material_dispatch.get("output_contract_consistent"):
        _add_finding(
            findings,
            code="material_dispatch_output_contract_mismatch",
            severity="error",
            summary="material scan packet envelope and body output contracts were not the same role-specific contract",
            invariant="material_scan_dispatch_requires_packet_integrity",
            evidence={"packets": material_dispatch.get("packet_details")},
        )
    if material_dispatch.get("requested") and not material_dispatch.get("write_target_explicit"):
        _add_finding(
            findings,
            code="material_dispatch_write_target_missing",
            severity="error",
            summary="material scan packet did not expose the worker result_body_path in the envelope or body",
            invariant="material_scan_dispatch_requires_packet_integrity",
            evidence={"packets": material_dispatch.get("packet_details")},
        )
    if material_dispatch.get("requested") and not material_dispatch.get("single_canonical_body"):
        _add_finding(
            findings,
            code="material_dispatch_duplicate_canonical_body",
            severity="error",
            summary="material scan packet had separate PM-spec and physical packet body identities",
            invariant="material_scan_dispatch_requires_packet_integrity",
            evidence={"packets": material_dispatch.get("packet_details")},
        )
    if route_process_check_delivered and not route_draft_has_nodes:
        _add_finding(
            findings,
            code="route_process_check_on_empty_route_draft",
            severity="error",
            summary="flowguard_operator.route_process_check was delivered while the current route draft had no nodes",
            invariant="route_checks_require_nonempty_route_nodes",
            evidence={"route_draft_node_counts": route_draft_node_counts},
        )

    if product_architecture_delivered and pm_material_written and not material_context_present:
        _add_finding(
            findings,
            code="product_architecture_delivery_missing_material_context",
            severity="error",
            summary="pm.product_architecture was delivered without the canonical PM material-understanding paths",
            invariant="product_architecture_delivery_requires_material_context",
            evidence={
                "card_id": "pm.product_architecture",
                "delivered_at": product_delivery.get("delivered_at") if product_delivery else None,
                "required_source_paths": sorted(required_material_paths),
                "actual_source_paths": sorted(material_source_values),
                "material_files_exist": pm_material_source_available,
            },
        )

    if phase_missing_sources:
        _add_finding(
            findings,
            code="phase_card_required_source_paths_missing",
            severity="error",
            summary="delivered phase cards omitted required upstream source paths",
            invariant="delivered_cards_include_required_phase_sources",
            evidence={"cards": phase_missing_sources},
        )

    if phase_stale_contexts:
        _add_finding(
            findings,
            code="delivered_card_phase_context_stale",
            severity="error",
            summary="delivered cards carried a stale or wrong current_phase in live context",
            invariant="delivered_card_phase_context_is_fresh",
            evidence={"cards": phase_stale_contexts},
        )

    unregistered_protocol_blockers: list[dict[str, object]] = []
    if run_root.exists():
        for blocker_path in sorted((run_root / "blockers").glob("*.json")):
            blocker, error = _read_json(blocker_path)
            rel_path = blocker_path.relative_to(root).as_posix()
            blocker_key = ""
            if isinstance(blocker, dict):
                blocker_key = str(blocker.get("blocker_id") or blocker.get("blocker_type") or "")
            registered = _json_contains(router_state, rel_path) or _json_contains(router_state, blocker_path.name)
            if blocker_key:
                registered = registered or _json_contains(router_state, blocker_key)
            if error or not registered:
                unregistered_protocol_blockers.append(
                    {
                        "path": rel_path,
                        "blocker_key": blocker_key or None,
                        "read_error": error,
                    }
                )
    if unregistered_protocol_blockers:
        _add_finding(
            findings,
            code="protocol_blocker_file_unregistered",
            severity="error",
            summary="protocol blocker files exist but are not visible in router_state",
            invariant="protocol_blockers_are_router_visible",
            evidence={"blockers": unregistered_protocol_blockers},
        )

    frontier_status = ""
    frontier_updated_at = None
    if isinstance(frontier, dict):
        frontier_status = str(frontier.get("status") or frontier.get("phase") or "")
        frontier_updated_at = _parse_time(frontier.get("updated_at"))
    frontier_fresh = not product_stage_advanced or (
        frontier_status not in {"", "startup_intake", "material_scan"}
        and product_delivery_at is not None
        and frontier_updated_at is not None
        and frontier_updated_at >= product_delivery_at
    )
    if product_stage_advanced and not frontier_fresh:
        _add_finding(
            findings,
            code="frontier_stale_after_product_architecture_delivery",
            severity="error",
            summary="execution_frontier still describes an earlier phase after product architecture advanced",
            invariant="frontier_tracks_product_architecture_delivery",
            evidence={
                "frontier_status": frontier_status,
                "frontier_updated_at": frontier_updated_at.isoformat() if frontier_updated_at else None,
                "product_delivery_at": product_delivery_at.isoformat() if product_delivery_at else None,
            },
        )

    snapshot_created_at = _parse_time(snapshot.get("created_at")) if isinstance(snapshot, dict) else None
    snapshot_text = json.dumps(snapshot, ensure_ascii=False, sort_keys=True) if snapshot is not None else ""
    snapshot_fresh = not product_stage_advanced or (
        snapshot_created_at is not None
        and product_delivery_at is not None
        and snapshot_created_at >= product_delivery_at
        and '"pm_product_architecture_card_delivered": true' in snapshot_text
    )
    display_updated_at = _parse_time(display_plan.get("updated_at")) if isinstance(display_plan, dict) else None
    display_text = json.dumps(display_plan, ensure_ascii=False, sort_keys=True) if display_plan is not None else ""
    display_fresh = not product_stage_advanced or (
        display_updated_at is not None
        and product_delivery_at is not None
        and display_updated_at >= product_delivery_at
        and "Waiting for PM route" not in display_text
    )
    views_fresh = snapshot_fresh and display_fresh
    if product_stage_advanced and not views_fresh:
        _add_finding(
            findings,
            code="display_view_stale_after_product_architecture_delivery",
            severity="error",
            summary="route_state_snapshot or display_plan still shows an earlier startup/material view",
            invariant="display_surfaces_track_product_architecture_delivery",
            evidence={
                "snapshot_created_at": snapshot_created_at.isoformat() if snapshot_created_at else None,
                "display_updated_at": display_updated_at.isoformat() if display_updated_at else None,
                "product_delivery_at": product_delivery_at.isoformat() if product_delivery_at else None,
                "snapshot_mentions_product_architecture_delivered": '"pm_product_architecture_card_delivered": true'
                in snapshot_text,
                "display_still_waiting_for_pm_route": "Waiting for PM route" in display_text,
            },
        )

    control_blocker_index_synced, control_blocker_mismatches = _router_control_blocker_status_matches(
        router_state, root
    )
    if control_blocker_mismatches:
        _add_finding(
            findings,
            code="control_blocker_index_stale_after_artifact_update",
            severity="warning",
            summary="router_state control_blockers summaries disagree with the durable control-blocker files",
            invariant="control_blocker_indexes_match_artifacts",
            evidence={"mismatches": control_blocker_mismatches},
        )

    (
        display_receipt_gaps,
        durable_reclaim_gaps,
        stateful_receipt_gaps,
        role_output_body_gaps,
    ) = _audit_evidence_closure_blockers(root, run_root)
    if display_receipt_gaps:
        _add_finding(
            findings,
            code="display_work_escalated_to_pm_repair",
            severity="error",
            summary="display/status Controller work was escalated to PM repair instead of remaining nonblocking",
            invariant="controller_display_work_remains_nonblocking",
            evidence={"blockers": display_receipt_gaps},
        )
    if stateful_receipt_gaps:
        _add_finding(
            findings,
            code="stateful_receipt_done_without_postcondition_evidence",
            severity="error",
            summary="stateful Controller receipt was marked done while Router-visible postcondition evidence was missing",
            invariant="stateful_controller_receipts_require_postcondition_evidence",
            evidence={"blockers": stateful_receipt_gaps},
        )
    if durable_reclaim_gaps:
        _add_finding(
            findings,
            code="valid_router_owned_artifact_not_reclaimed_before_blocker",
            severity="error",
            summary="valid Router-owned artifact/proof existed but Router escalated before reclaiming the postcondition",
            invariant="router_owned_artifacts_are_reclaimed_before_blocker",
            evidence={"blockers": durable_reclaim_gaps},
        )
    if role_output_body_gaps:
        _add_finding(
            findings,
            code="role_output_event_missing_file_backed_body",
            severity="error",
            summary="role-output event was attempted without a file-backed body path",
            invariant="role_output_events_require_file_backed_body",
            evidence={"blockers": role_output_body_gaps},
        )

    pm_role_work_identity = _audit_pm_role_work_unit_identity(run_root, router_state)
    if pm_role_work_identity.get("closed_identity_reused"):
        _add_finding(
            findings,
            code="pm_role_work_closed_identity_reused_for_distinct_batch",
            severity="error",
            summary="a closed PM role-work Controller action row was reused for a distinct batch/request/packet/role obligation",
            invariant="pm_role_work_identity_is_work_unit_scoped",
            evidence=pm_role_work_identity,
        )
    if not pm_role_work_identity.get("identity_scoped"):
        _add_finding(
            findings,
            code="pm_role_work_wait_identity_missing_request_packet_role",
            severity="error",
            summary="PM role-work identity omitted batch, request, packet, or target-role fields",
            invariant="pm_role_work_identity_is_work_unit_scoped",
            evidence=pm_role_work_identity,
        )
    if pm_role_work_identity.get("global_postcondition_masks_open_request"):
        _add_finding(
            findings,
            code="pm_role_work_global_postcondition_masks_open_request",
            severity="error",
            summary="global PM role-work relay flag was true while an active request-specific obligation was still unresolved",
            invariant="pm_role_work_identity_is_work_unit_scoped",
            evidence=pm_role_work_identity,
        )

    controller_delivery = _audit_controller_delivery_success(run_root)
    if not controller_delivery.get("ok"):
        _add_finding(
            findings,
            code="controller_delivery_failed_marked_done",
            severity="error",
            summary="Controller receipt was marked done even though host message delivery failed",
            invariant="controller_delivery_receipts_do_not_complete_target_work",
            evidence=controller_delivery,
        )

    active_holder_liveness = _audit_active_holder_liveness(run_root)
    if active_holder_liveness.get("lease_issues"):
        _add_finding(
            findings,
            code="active_holder_lease_without_host_liveness",
            severity="error",
            summary="active-holder lease existed without host-liveness proof for the target agent",
            invariant="active_holder_leases_require_host_liveness",
            evidence=active_holder_liveness,
        )

    packet_ledger_io = _audit_packet_ledger_corruption(run_root)
    if packet_ledger_io.get("daemon_crashed_on_corrupt_read"):
        _add_finding(
            findings,
            code="packet_ledger_corrupt_read_crashes_daemon",
            severity="error",
            summary="packet ledger corruption crashed the daemon instead of being quarantined as a recoverable control blocker",
            invariant="packet_ledger_io_is_atomic_and_recoverable",
            evidence=packet_ledger_io,
        )

    material_gate_evidence = _audit_material_gate_evidence_contract(run_root)
    if not material_gate_evidence.get("result_self_check_machine_parseable"):
        _add_finding(
            findings,
            code="material_gate_result_self_check_unparseable",
            severity="error",
            summary="material gate depended on result-body self-check evidence that was not machine clean",
            invariant="material_gate_result_evidence_is_machine_and_authority_backed",
            evidence=material_gate_evidence,
        )
    if not material_gate_evidence.get("result_reader_authority_matches_runtime"):
        _add_finding(
            findings,
            code="material_gate_result_reader_not_runtime_backed",
            severity="error",
            summary="material artifact map advertised reviewer access that packet runtime authority did not grant",
            invariant="material_gate_result_evidence_is_machine_and_authority_backed",
            evidence=material_gate_evidence,
        )

    pre_event_ack = _audit_valid_ack_file_blocked_role_event(root, run_root)
    if pre_event_ack.get("valid_ack_file_blocked_role_event"):
        _add_finding(
            findings,
            code="valid_card_ack_file_present_role_event_blocked",
            severity="error",
            summary="role event was blocked as an unresolved card return even though a valid direct ACK file was already present",
            invariant="valid_card_ack_file_precedes_unresolved_role_event_block",
            evidence=pre_event_ack,
        )

    pm_repair_recorded, pm_repair_followup_matchable, pm_repair_followup_evidence = (
        _active_pm_repair_followup_event_matchable(router_state)
    )
    pm_repair_liveness = _audit_pm_repair_reissue_liveness(root, run_root, router_state)
    active_blocker = router_state.get("active_control_blocker") if isinstance(router_state, dict) else None
    active_blocker = active_blocker if isinstance(active_blocker, dict) else {}
    active_blocker_lane = str(active_blocker.get("handling_lane") or "none")
    if pm_repair_recorded and not pm_repair_followup_matchable:
        _add_finding(
            findings,
            code="pm_repair_followup_event_unmatchable",
            severity="error",
            summary="PM repair decision recorded a follow-up event that router resolution logic cannot match",
            invariant="pm_repair_followup_events_are_matchable",
            evidence=pm_repair_followup_evidence,
        )
    if (
        pm_repair_liveness.get("pm_repair_recorded")
        and pm_repair_liveness.get("reissue_spec_written")
        and not pm_repair_liveness.get("runtime_ready")
    ):
        _add_finding(
            findings,
            code="pm_repair_reissue_packets_not_materialized",
            severity="error",
            summary="PM repair wrote replacement packet specs that were not materialized into packet files, packet_ledger, and material dispatch index",
            invariant="pm_repair_reissue_requires_packet_runtime_materialization",
            evidence=pm_repair_liveness,
        )
    if (
        pm_repair_liveness.get("pm_repair_recorded")
        and (
            (
                pm_repair_liveness.get("reissue_spec_written")
                and not pm_repair_liveness.get("runtime_ready")
            )
            or pm_repair_liveness.get("reviewer_recheck_protocol_blocker_written")
        )
        and (
            pm_repair_liveness.get("success_only_allowed")
            or not pm_repair_liveness.get("non_success_outcome_routable")
            or not pm_repair_liveness.get("reviewer_recheck_protocol_blocker_routable")
        )
    ):
        _add_finding(
            findings,
            code="pm_repair_success_only_gate_blocks_reviewer_recheck_failure",
            severity="error",
            summary="PM repair left router accepting only the success event even though reviewer recheck could only produce a blocker or protocol outcome",
            invariant="pm_repair_recheck_outcomes_remain_routable",
            evidence=pm_repair_liveness,
        )
    if (
        pm_repair_liveness.get("reviewer_recheck_protocol_blocker_written")
        and not pm_repair_liveness.get("reviewer_recheck_protocol_blocker_routable")
    ):
        _add_finding(
            findings,
            code="reviewer_recheck_protocol_blocker_unroutable",
            severity="error",
            summary="Reviewer wrote a recheck protocol blocker that was not visible as a routable router resolution event",
            invariant="pm_repair_recheck_outcomes_remain_routable",
            evidence=pm_repair_liveness,
        )
    stale_repair_lane = _audit_stale_repair_lane(router_state, frontier)
    if stale_repair_lane.get("active_repair_transaction_stale") or stale_repair_lane.get(
        "repair_recheck_pending_action_stale"
    ):
        _add_finding(
            findings,
            code="repair_transaction_stale_after_success",
            severity="error",
            summary="repair transaction success left stale active repair transaction or repair recheck pending action after the main flow advanced",
            invariant="repair_success_clears_stale_repair_lane",
            evidence=stale_repair_lane,
        )
    stale_expected_wait = _audit_expected_role_decision_event_prereqs(router_state, source)
    if stale_expected_wait.get("expected_role_decision_requires_unsatisfied_flag"):
        _add_finding(
            findings,
            code="role_decision_wait_requires_unsatisfied_flag",
            severity="error",
            summary="await_role_decision exposed an external event whose requires_flag is false in current router state",
            invariant="expected_role_decisions_require_satisfied_flags",
            evidence=stale_expected_wait,
        )

    internal_postcondition = _audit_router_internal_postconditions(root, run_root, router_state)
    if (
        internal_postcondition.get("due")
        and internal_postcondition.get("inputs_ready")
        and internal_postcondition.get("exposed_as_role_wait")
    ):
        _add_finding(
            findings,
            code="router_internal_postcondition_role_wait_dead_end",
            severity="error",
            summary="router-owned internal evidence sync was exposed as a Controller wait instead of being materialized or blocked by Router",
            invariant="router_internal_postconditions_materialize_or_block",
            evidence=internal_postcondition,
        )
    elif internal_postcondition.get("due") and internal_postcondition.get("inputs_ready") and not (
        internal_postcondition.get("materialized")
        or internal_postcondition.get("blocker_materialized")
    ):
        _add_finding(
            findings,
            code="router_internal_postcondition_unmaterialized_after_ready_inputs",
            severity="error",
            summary="router-owned internal evidence sync had ready inputs but no materialized evidence or router-visible blocker",
            invariant="router_internal_postconditions_materialize_or_block",
            evidence=internal_postcondition,
        )

    resolved_projection = _audit_resolved_obligation_projection_reconciliation(run_root, router_state)
    if (
        resolved_projection.get("evidence_exists")
        and (
            resolved_projection.get("live_passive_wait")
            or resolved_projection.get("live_blocked_reminder")
        )
        and not resolved_projection.get("projection_reconciled")
    ):
        _add_finding(
            findings,
            code="resolved_obligation_projection_still_live",
            severity="error",
            summary="resolved router obligation still has a live passive wait or blocked reminder projection",
            invariant="resolved_obligation_projections_are_cleared",
            evidence=resolved_projection,
        )

    child_skill_gate_synced, child_skill_gate_evidence = _audit_child_skill_gate_sync(run_root)
    child_skill_review_recorded = bool(child_skill_gate_evidence.get("review_passed") is True)
    if child_skill_review_recorded and not child_skill_gate_synced:
        _add_finding(
            findings,
            code="child_skill_gate_manifest_review_unsynced",
            severity="error",
            summary="child-skill gate reviewer pass did not update the manifest approval state",
            invariant="child_skill_gate_manifest_syncs_review_status",
            evidence=child_skill_gate_evidence,
        )
    gate_lifecycle = _audit_gate_outcome_lifecycle(router_state)
    if gate_lifecycle.get("same_gate_active_block_after_pass"):
        _add_finding(
            findings,
            code="gate_pass_left_active_block",
            severity="error",
            summary="same-gate reviewer pass is recorded while the previous active gate outcome block is still live",
            invariant="gate_pass_clears_matching_current_block",
            evidence=gate_lifecycle,
        )

    terminal_snapshot_consistent, terminal_snapshot_evidence = _terminal_snapshot_flags_consistent(
        snapshot, router_state, current
    )
    terminal_snapshot_published = bool(terminal_snapshot_evidence.get("terminal_status"))
    if terminal_snapshot_published and not terminal_snapshot_consistent:
        _add_finding(
            findings,
            code="terminal_snapshot_flag_mismatch",
            severity="error",
            summary="terminal snapshot status and run_stopped_by_user flag disagree",
            invariant="terminal_snapshot_flags_match_terminal_state",
            evidence=terminal_snapshot_evidence,
        )

    terminal_cleanup_proven, terminal_cleanup_evidence = _terminal_continuation_cleanup_proven(
        root, run_root, current, router_state
    )
    terminal_cleanup_recorded = bool(terminal_cleanup_evidence.get("terminal_status"))
    if terminal_cleanup_recorded and not terminal_cleanup_proven:
        _add_finding(
            findings,
            code="terminal_manual_resume_binding_cleanup_unproven",
            severity="warning",
            summary="terminal continuation cleanup lacks durable foreground-patrol or manual-resume lifecycle proof",
            invariant="terminal_continuation_cleanup_is_proven",
            evidence=terminal_cleanup_evidence,
        )

    role_hashes_replayable, role_hash_mismatches, role_output_envelope_count = _audit_role_output_hashes(root, run_root)
    if role_hash_mismatches:
        _add_finding(
            findings,
            code="role_output_hash_replay_mismatch",
            severity="warning",
            summary="persisted role-output envelope hashes do not replay against current body paths",
            invariant="role_output_hashes_are_replayable",
            evidence={
                "mismatch_count": len(role_hash_mismatches),
                "checked_role_output_envelope_count": role_output_envelope_count,
                "samples": role_hash_mismatches[:12],
            },
        )

    material_repair_protocol = _audit_material_repair_generation_protocol(
        root,
        run_root,
        router_state,
        source,
    )
    if not material_repair_protocol.get("operation_replay_fresh_controller_action_id"):
        _add_finding(
            findings,
            code="operation_replay_reuses_controller_action_id",
            severity="error",
            summary="operation replay reused a closed Controller action identity",
            invariant="material_repair_generation_protocol_is_current",
            evidence=material_repair_protocol,
        )
    if not material_repair_protocol.get("operation_replay_targets_current_generation"):
        _add_finding(
            findings,
            code="operation_replay_targets_superseded_generation",
            severity="error",
            summary="operation replay targeted a superseded material packet generation",
            invariant="material_repair_generation_protocol_is_current",
            evidence=material_repair_protocol,
        )
    if not material_repair_protocol.get("operation_replay_ledger_io_authorized"):
        _add_finding(
            findings,
            code="material_result_relay_replay_without_ledger_authority",
            severity="error",
            summary="material result relay replay lacked current packet-ledger and material-index authority",
            invariant="material_repair_generation_protocol_is_current",
            evidence=material_repair_protocol,
        )
    if not material_repair_protocol.get("controller_repair_work_packet_receipt_folded"):
        _add_finding(
            findings,
            code="controller_repair_work_packet_receipt_not_folded",
            severity="error",
            summary="controller_repair_work_packet receipt did not fold the repair transaction",
            invariant="material_repair_generation_protocol_is_current",
            evidence=material_repair_protocol,
        )
    if not material_repair_protocol.get("controller_repair_work_packet_facade_exported"):
        _add_finding(
            findings,
            code="controller_repair_work_packet_facade_export_missing",
            severity="error",
            summary="controller_repair_work_packet receipt helper was not exported through the Router facade",
            invariant="material_repair_generation_protocol_is_current",
            evidence=material_repair_protocol,
        )
    if not (
        material_repair_protocol.get("pm_material_disposition_generation_scoped")
        and material_repair_protocol.get("pm_material_disposition_matches_current_generation")
    ):
        _add_finding(
            findings,
            code="pm_material_disposition_generation_blind",
            severity="error",
            summary="PM material result disposition was not scoped to the current packet generation",
            invariant="material_repair_generation_protocol_is_current",
            evidence=material_repair_protocol,
        )
    if material_repair_protocol.get("stale_pm_material_disposition_restored"):
        _add_finding(
            findings,
            code="stale_pm_material_disposition_restored",
            severity="error",
            summary="stale PM material disposition was restored as current-generation success",
            invariant="material_repair_generation_protocol_is_current",
            evidence=material_repair_protocol,
        )
    if not (
        material_repair_protocol.get("material_progress_projection_generation_scoped")
        and material_repair_protocol.get("material_global_progress_flags_match_active_generation")
    ):
        _add_finding(
            findings,
            code="material_progress_flags_not_generation_scoped",
            severity="error",
            summary="Router-visible material progress flags disagree with the active material generation",
            invariant="material_repair_generation_protocol_is_current",
            evidence=material_repair_protocol,
        )
    if not material_repair_protocol.get("material_next_action_derived_from_active_batch"):
        _add_finding(
            findings,
            code="material_next_action_uses_stale_global_flags",
            severity="error",
            summary="material packet next-action selection is driven by stale run-wide flags instead of active batch state",
            invariant="material_repair_generation_protocol_is_current",
            evidence=material_repair_protocol,
        )
    if not material_repair_protocol.get("material_reissue_clears_or_quarantines_stale_progress_flags"):
        _add_finding(
            findings,
            code="material_reissue_keeps_stale_progress_flags",
            severity="error",
            summary="material packet reissue left superseded progress flags visible for the current generation",
            invariant="material_repair_generation_protocol_is_current",
            evidence=material_repair_protocol,
        )
    if not material_repair_protocol.get("stale_run_state_save_preserves_material_generation_flag_clear"):
        _add_finding(
            findings,
            code="stale_material_progress_flags_resurrected_by_save",
            severity="error",
            summary="stale run-state save can restore superseded material progress flags after current generation reset",
            invariant="material_repair_generation_protocol_is_current",
            evidence=material_repair_protocol,
        )
    if not material_repair_protocol.get("material_dispatch_block_matches_active_generation"):
        _add_finding(
            findings,
            code="material_dispatch_block_stale_generation",
            severity="error",
            summary="material dispatch protocol block references a superseded repair generation",
            invariant="material_repair_generation_protocol_is_current",
            evidence=material_repair_protocol,
        )
    if not material_repair_protocol.get("role_output_current_generation_not_short_circuited_by_global_flag"):
        _add_finding(
            findings,
            code="role_output_current_generation_short_circuited_by_global_flag",
            severity="error",
            summary="role-output reconciliation can short-circuit current-generation material events on a run-wide flag",
            invariant="role_event_identity_and_audit_records_are_closed",
            evidence=material_repair_protocol,
        )
    if not material_repair_protocol.get("role_output_event_deduped_by_body_ref"):
        _add_finding(
            findings,
            code="role_output_duplicate_not_deduped",
            severity="error",
            summary="role-output events were not deduped by event type and body reference",
            invariant="role_event_identity_and_audit_records_are_closed",
            evidence=material_repair_protocol,
        )
    if not material_repair_protocol.get("pm_package_disposition_semantic_identity_deduped"):
        _add_finding(
            findings,
            code="pm_package_disposition_not_semantic_deduped",
            severity="error",
            summary="PM package dispositions were not deduped by semantic batch identity",
            invariant="role_event_identity_and_audit_records_are_closed",
            evidence=material_repair_protocol,
        )
    if not material_repair_protocol.get("pm_package_disposition_body_hash_conflict_checked"):
        _add_finding(
            findings,
            code="pm_package_disposition_conflict_unchecked",
            severity="error",
            summary="PM package disposition body_hash is not checked as conflict evidence",
            invariant="role_event_identity_and_audit_records_are_closed",
            evidence=material_repair_protocol,
        )
    if not material_repair_protocol.get("role_output_package_disposition_domain_first_commit"):
        _add_finding(
            findings,
            code="pm_package_disposition_reconciled_without_domain_commit",
            severity="error",
            summary="role-output package disposition reconciliation can record event progress before the canonical domain artifact commit",
            invariant="role_event_identity_and_audit_records_are_closed",
            evidence=material_repair_protocol,
        )
    if not (
        material_repair_protocol.get("pm_package_authority_split_preserves_wait")
        or material_repair_protocol.get("pm_package_authority_split_repairs_domain_commit")
    ):
        _add_finding(
            findings,
            code="pm_package_authority_split_lost_wait",
            severity="error",
            summary="recorded PM package disposition without canonical authority can close the legal wait before preserving it or repairing the canonical domain commit",
            invariant="role_event_identity_and_audit_records_are_closed",
            evidence=material_repair_protocol,
        )
    if not material_repair_protocol.get("pm_package_packet_outcomes_recorded"):
        _add_finding(
            findings,
            code="pm_package_disposition_packet_outcomes_missing",
            severity="error",
            summary="PM package disposition did not record per-packet outcomes",
            invariant="role_event_identity_and_audit_records_are_closed",
            evidence=material_repair_protocol,
        )
    if not material_repair_protocol.get("packet_result_author_identity_replayable"):
        _add_finding(
            findings,
            code="packet_result_author_identity_not_replayable",
            severity="error",
            summary="packet result author identity was not replayable from the packet ledger",
            invariant="packet_result_authority_is_ledger_replayable",
            evidence=material_repair_protocol,
        )
    if not material_repair_protocol.get("break_glass_patch_validation_finalized"):
        _add_finding(
            findings,
            code="break_glass_patch_validation_pending",
            severity="error",
            summary="break-glass patch record remained pending validation after validation evidence existed",
            invariant="role_event_identity_and_audit_records_are_closed",
            evidence=material_repair_protocol,
        )

    non_current_running_entries: list[str] = []
    if isinstance(index, dict):
        for item in index.get("runs", []):
            if isinstance(item, dict) and item.get("status") == "running" and item.get("run_id") != run_id:
                non_current_running_entries.append(str(item.get("run_id")))
    background_running_entries = _background_running_projection_ids(snapshot)
    missing_background_projection = sorted(
        set(non_current_running_entries) - set(background_running_entries)
    )
    active_set_authority_source = "stored_snapshot"
    has_explicit_active_authority = _active_set_authority_is_explicit(
        snapshot,
        non_current_running_entries=non_current_running_entries,
        missing_background_projection=missing_background_projection,
    )
    synthesized_active_authority = _active_set_authority_snapshot_from_index(
        current=current,
        index=index,
        current_run_id=run_id,
    )
    if not has_explicit_active_authority and synthesized_active_authority is not None:
        synthesized_background_entries = _background_running_projection_ids(synthesized_active_authority)
        synthesized_missing_background = sorted(
            set(non_current_running_entries) - set(synthesized_background_entries)
        )
        synthesized_is_explicit = _active_set_authority_is_explicit(
            synthesized_active_authority,
            non_current_running_entries=non_current_running_entries,
            missing_background_projection=synthesized_missing_background,
        )
        if synthesized_is_explicit:
            background_running_entries = synthesized_background_entries
            missing_background_projection = synthesized_missing_background
            active_set_authority_source = "read_only_index_synthesis"
            has_explicit_active_authority = True
    if missing_background_projection:
        _add_finding(
            findings,
            code="non_current_runs_missing_background_projection",
            severity="warning",
            summary="non-current running index entries lack background-active projection",
            invariant="multi_active_requires_explicit_authority",
            evidence={
                "current_run_id": run_id,
                "non_current_running_run_ids": non_current_running_entries,
                "missing_background_projection_run_ids": missing_background_projection,
                "active_set_authority_source": active_set_authority_source,
            },
        )

    projected_state = _safe_base(
        pm_material_understanding_written=pm_material_written,
        pm_material_understanding_source_available=pm_material_source_available,
        material_dispatch_requested=bool(material_dispatch.get("requested")),
        material_dispatch_reviewed=bool(material_dispatch.get("reviewed")),
        material_dispatch_allowed=bool(
            material_dispatch.get("requested")
            and material_dispatch.get("phase_context_consistent")
            and material_dispatch.get("output_contract_consistent")
            and material_dispatch.get("write_target_explicit")
            and material_dispatch.get("single_canonical_body")
        ),
        material_dispatch_phase_context_consistent=bool(
            material_dispatch.get("phase_context_consistent")
        ),
        material_dispatch_output_contract_consistent=bool(
            material_dispatch.get("output_contract_consistent")
        ),
        material_dispatch_write_target_explicit=bool(
            material_dispatch.get("write_target_explicit")
        ),
        material_dispatch_single_canonical_body=bool(
            material_dispatch.get("single_canonical_body")
        ),
        product_architecture_card_delivered=product_architecture_delivered,
        product_architecture_delivery_has_material_context=material_context_present,
        protocol_blocker_file_written=bool(unregistered_protocol_blockers),
        protocol_blocker_registered_in_router_state=not bool(unregistered_protocol_blockers),
        control_blocker_artifact_status_written=bool(control_blocker_mismatches),
        control_blocker_router_index_matches_artifact=control_blocker_index_synced,
        controller_display_work_soft_recorded=True,
        controller_display_work_hard_postcondition=bool(display_receipt_gaps),
        controller_display_work_escalated_to_pm=bool(display_receipt_gaps),
        stateful_controller_receipt_done=True,
        stateful_controller_postcondition_declared=True,
        stateful_controller_postcondition_evidence_written=not bool(stateful_receipt_gaps or durable_reclaim_gaps),
        stateful_controller_advanced_from_receipt=not bool(stateful_receipt_gaps or durable_reclaim_gaps),
        controller_delivery_receipt_done=True,
        controller_delivery_host_status=(
            "delivered" if controller_delivery.get("ok") else "failed_agent_not_found"
        ),
        controller_delivery_target_role_wait_started=True,
        controller_delivery_used_as_role_completion=False,
        controller_delivery_missing_role_output_blocker=False,
        pm_role_work_identity_includes_batch_request_packet_role=bool(
            pm_role_work_identity.get("identity_scoped")
        ),
        pm_role_work_closed_identity_reused_for_distinct_request=bool(
            pm_role_work_identity.get("closed_identity_reused")
        ),
        pm_role_work_request_postcondition_scoped=bool(
            pm_role_work_identity.get("request_postcondition_scoped")
        ),
        pm_role_work_open_request_masked_by_global_flag=bool(
            pm_role_work_identity.get("global_postcondition_masks_open_request")
        ),
        active_holder_lease_issued=bool(active_holder_liveness.get("lease_count")),
        active_holder_agent_identity_recorded=bool(
            active_holder_liveness.get("agent_identity_recorded")
        ),
        active_holder_agent_host_live=bool(active_holder_liveness.get("host_live")),
        active_holder_packet_role_matches=bool(
            active_holder_liveness.get("packet_role_matches")
        ),
        packet_ledger_write_atomic=not bool(
            packet_ledger_io.get("corrupt_backup_count")
        ),
        packet_ledger_write_locked_or_cas=not bool(
            packet_ledger_io.get("corrupt_backup_count")
        ),
        packet_ledger_readback_validated=not bool(
            packet_ledger_io.get("corrupt_backup_count")
        ),
        packet_ledger_corruption_recoverable=not bool(
            packet_ledger_io.get("daemon_crashed_on_corrupt_read")
        ),
        packet_ledger_corrupt_read_crashed_daemon=bool(
            packet_ledger_io.get("daemon_crashed_on_corrupt_read")
        ),
        router_owned_artifact_exists=bool(durable_reclaim_gaps),
        router_owned_artifact_proof_valid=bool(durable_reclaim_gaps),
        router_owned_postcondition_reclaimed_from_artifact=not bool(durable_reclaim_gaps),
        router_tick_saw_receipt_before_flag=bool(durable_reclaim_gaps),
        router_tick_escalated_before_reclaim=bool(durable_reclaim_gaps),
        router_internal_postcondition_due=bool(internal_postcondition.get("due")),
        router_internal_postcondition_inputs_ready=bool(
            internal_postcondition.get("inputs_ready")
        ),
        router_internal_postcondition_materialized=bool(
            internal_postcondition.get("materialized")
        ),
        router_internal_postcondition_blocker_materialized=bool(
            internal_postcondition.get("blocker_materialized")
        ),
        router_internal_postcondition_exposed_as_role_wait=bool(
            internal_postcondition.get("exposed_as_role_wait")
        ),
        router_internal_postcondition_expected_evidence_exists=bool(
            internal_postcondition.get("expected_evidence_exists")
        ),
        router_internal_postcondition_executable_action_pending=bool(
            internal_postcondition.get("executable_action_pending")
        ),
        resolved_obligation_evidence_exists=bool(
            resolved_projection.get("evidence_exists")
        ),
        resolved_obligation_live_passive_wait=bool(
            resolved_projection.get("live_passive_wait")
        ),
        resolved_obligation_live_blocked_reminder=bool(
            resolved_projection.get("live_blocked_reminder")
        ),
        resolved_obligation_projection_reconciled=bool(
            resolved_projection.get("projection_reconciled")
        ),
        control_blocker_lane=active_blocker_lane if pm_repair_recorded else "none",
        control_blocker_target_role="project_manager" if pm_repair_recorded else "none",
        pm_repair_decision_recorded=pm_repair_recorded,
        role_output_event_submitted=bool(pm_repair_recorded or role_output_body_gaps),
        role_output_event_accepted=bool(pm_repair_recorded),
        role_output_file_backed_body_path_present=not bool(role_output_body_gaps),
        role_output_body_hash_verified=not bool(role_output_body_gaps),
        material_repair_generation_protocol_checked=True,
        operation_replay_fresh_controller_action_id=bool(
            material_repair_protocol.get("operation_replay_fresh_controller_action_id")
        ),
        operation_replay_targets_current_generation=bool(
            material_repair_protocol.get("operation_replay_targets_current_generation")
        ),
        operation_replay_ledger_io_authorized=bool(
            material_repair_protocol.get("operation_replay_ledger_io_authorized")
        ),
        controller_repair_work_packet_receipt_folded=bool(
            material_repair_protocol.get("controller_repair_work_packet_receipt_folded")
        ),
        controller_repair_work_packet_facade_exported=bool(
            material_repair_protocol.get("controller_repair_work_packet_facade_exported")
        ),
        pm_material_disposition_generation_scoped=bool(
            material_repair_protocol.get("pm_material_disposition_generation_scoped")
        ),
        pm_material_disposition_matches_current_generation=bool(
            material_repair_protocol.get("pm_material_disposition_matches_current_generation")
        ),
        stale_pm_material_disposition_restored=bool(
            material_repair_protocol.get("stale_pm_material_disposition_restored")
        ),
        material_progress_projection_generation_scoped=bool(
            material_repair_protocol.get("material_progress_projection_generation_scoped")
        ),
        material_global_progress_flags_match_active_generation=bool(
            material_repair_protocol.get("material_global_progress_flags_match_active_generation")
        ),
        material_next_action_derived_from_active_batch=bool(
            material_repair_protocol.get("material_next_action_derived_from_active_batch")
        ),
        material_reissue_clears_or_quarantines_stale_progress_flags=bool(
            material_repair_protocol.get("material_reissue_clears_or_quarantines_stale_progress_flags")
        ),
        stale_run_state_save_preserves_material_generation_flag_clear=bool(
            material_repair_protocol.get("stale_run_state_save_preserves_material_generation_flag_clear")
        ),
        material_dispatch_block_matches_active_generation=bool(
            material_repair_protocol.get("material_dispatch_block_matches_active_generation")
        ),
        role_output_current_generation_not_short_circuited_by_global_flag=bool(
            material_repair_protocol.get("role_output_current_generation_not_short_circuited_by_global_flag")
        ),
        role_output_event_deduped_by_body_ref=bool(
            material_repair_protocol.get("role_output_event_deduped_by_body_ref")
        ),
        duplicate_role_event_side_effect_written=bool(
            material_repair_protocol.get("duplicate_role_event_side_effect_written")
        ),
        pm_package_disposition_semantic_identity_deduped=bool(
            material_repair_protocol.get("pm_package_disposition_semantic_identity_deduped")
        ),
        pm_package_disposition_body_hash_conflict_checked=bool(
            material_repair_protocol.get("pm_package_disposition_body_hash_conflict_checked")
        ),
        role_output_package_disposition_domain_first_commit=bool(
            material_repair_protocol.get("role_output_package_disposition_domain_first_commit")
        ),
        pm_package_authority_split_preserves_wait=bool(
            material_repair_protocol.get("pm_package_authority_split_preserves_wait")
        ),
        pm_package_authority_split_repairs_domain_commit=bool(
            material_repair_protocol.get("pm_package_authority_split_repairs_domain_commit")
        ),
        pm_package_packet_outcomes_recorded=bool(
            material_repair_protocol.get("pm_package_packet_outcomes_recorded")
        ),
        packet_result_author_identity_replayable=bool(
            material_repair_protocol.get("packet_result_author_identity_replayable")
        ),
        packet_result_author_matches_current_role=bool(
            material_repair_protocol.get("packet_result_author_matches_current_role")
        ),
        break_glass_patch_validation_finalized=bool(
            material_repair_protocol.get("break_glass_patch_validation_finalized")
        ),
        control_blocker_followup_event_matchable=pm_repair_followup_matchable,
        pm_repair_reissue_spec_written=bool(
            pm_repair_liveness.get("reissue_spec_written")
        ),
        pm_repair_reissue_packet_files_materialized=bool(
            pm_repair_liveness.get("packet_files_materialized")
        ),
        pm_repair_reissue_packets_registered_in_ledger=bool(
            pm_repair_liveness.get("packets_registered_in_ledger")
        ),
        pm_repair_reissue_dispatch_index_updated=bool(
            pm_repair_liveness.get("dispatch_index_updated")
        ),
        pm_repair_allowed_success_only=bool(
            pm_repair_liveness.get("success_only_allowed")
        ),
        pm_repair_non_success_outcome_routable=bool(
            pm_repair_liveness.get("non_success_outcome_routable")
        ),
        active_repair_transaction_stale=bool(
            stale_repair_lane.get("active_repair_transaction_stale")
        ),
        repair_recheck_pending_action_stale=bool(
            stale_repair_lane.get("repair_recheck_pending_action_stale")
        ),
        expected_role_decision_requires_unsatisfied_flag=bool(
            stale_expected_wait.get("expected_role_decision_requires_unsatisfied_flag")
        ),
        reviewer_recheck_protocol_blocker_written=bool(
            pm_repair_liveness.get("reviewer_recheck_protocol_blocker_written")
        ),
        reviewer_recheck_protocol_blocker_routable=bool(
            pm_repair_liveness.get("reviewer_recheck_protocol_blocker_routable")
        ),
        material_gate_depends_on_result_body=bool(
            material_gate_evidence.get("depends_on_result_body")
        ),
        result_self_check_machine_parseable=bool(
            material_gate_evidence.get("result_self_check_machine_parseable")
        ),
        result_reader_authority_matches_runtime=bool(
            material_gate_evidence.get("result_reader_authority_matches_runtime")
        ),
        phase_dependency_cards_delivered=phase_dependency_cards_delivered,
        phase_required_sources_complete=not bool(phase_missing_sources),
        delivered_card_phase_context_fresh=not bool(phase_stale_contexts),
        terminal_snapshot_published=terminal_snapshot_published,
        terminal_snapshot_flags_consistent=terminal_snapshot_consistent,
        child_skill_gate_review_recorded=child_skill_review_recorded,
        child_skill_gate_manifest_synced_with_review=child_skill_gate_synced,
        gate_outcome_block_active=bool(gate_lifecycle.get("gate_outcome_block_active")),
        gate_outcome_block_gate_key=str(gate_lifecycle.get("gate_outcome_block_gate_key") or "none"),
        gate_outcome_pass_recorded=bool(gate_lifecycle.get("gate_outcome_pass_recorded")),
        gate_outcome_pass_gate_key=str(gate_lifecycle.get("gate_outcome_pass_gate_key") or "none"),
        gate_outcome_same_generation=bool(gate_lifecycle.get("gate_outcome_same_generation")),
        gate_outcome_clear_target_matches_pass_gate=bool(
            gate_lifecycle.get("gate_outcome_clear_target_matches_pass_gate")
        ),
        pending_card_return_kind=(
            str((pre_event_ack.get("samples") or [{}])[0].get("return_kind") or "none")
            if pre_event_ack.get("valid_ack_file_blocked_role_event")
            else "none"
        ),
        pending_card_return_ack_file_present=bool(pre_event_ack.get("valid_ack_file_blocked_role_event")),
        pending_card_return_ack_valid=bool(pre_event_ack.get("valid_ack_file_blocked_role_event")),
        pending_card_return_ack_role_checked=True,
        pending_card_return_ack_hash_checked=True,
        pending_card_return_bundle_receipts_complete=True,
        card_return_ledger_resolved=not bool(pre_event_ack.get("valid_ack_file_blocked_role_event")),
        role_event_arrived_while_ack_pending=bool(pre_event_ack.get("valid_ack_file_blocked_role_event")),
        pre_event_card_ack_auto_consumed=False,
        role_event_blocked_by_unresolved_card_return=bool(pre_event_ack.get("valid_ack_file_blocked_role_event")),
        terminal_continuation_cleanup_recorded=terminal_cleanup_recorded,
        terminal_lifecycle_cleanup_proven=terminal_cleanup_proven,
        role_output_envelopes_recorded=role_output_envelope_count > 0,
        role_output_hashes_replayable=role_hashes_replayable,
        stage_advanced_after_material_scan=product_stage_advanced,
        frontier_fresh_after_stage_advance=frontier_fresh,
        product_stage_view_published=bool(snapshot is not None or display_plan is not None),
        product_stage_view_fresh=views_fresh,
        route_draft_written=route_draft_written,
        route_draft_has_nodes=route_draft_has_nodes,
        route_process_check_card_delivered=route_process_check_delivered,
        route_process_check_passed=route_process_check_passed,
        multiple_running_index_entries_visible=bool(non_current_running_entries),
        active_task_authority="explicit_active_set" if has_explicit_active_authority else "current_focus_only",
    )
    projected_failures = invariant_failures(projected_state)
    error_count = sum(1 for finding in findings if finding.get("severity") == "error")
    return {
        "ok": error_count == 0 and not projected_failures,
        "skipped": False,
        "run_id": run_id,
        "run_root": run_root_rel,
        "finding_count": len(findings),
        "error_count": error_count,
        "warning_count": sum(1 for finding in findings if finding.get("severity") == "warning"),
        "findings": findings,
        "projected_state": projected_state.__dict__,
        "projected_invariant_failures": projected_failures,
        "active_set_authority_source": active_set_authority_source,
    }


__all__ = [
    "audit_live_run",
]


