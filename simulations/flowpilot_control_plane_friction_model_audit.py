"""Live-run audit adapter for ``flowpilot_control_plane_friction_model``."""

from __future__ import annotations

import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flowpilot_control_plane_friction_model_hazards import _safe_base
from flowpilot_control_plane_friction_model_invariants import invariant_failures
from flowpilot_control_plane_friction_model_state import PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES


def _read_json(path: Path) -> tuple[Any, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, f"missing file: {path.as_posix()}"
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON in {path.as_posix()}: {exc}"

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

def _legacy_route_challenge_missing_sources(
    *,
    card_id: str,
    run_id: str,
    missing: list[str],
    source_values: set[str],
    project_root: Path,
) -> list[str]:
    if card_id != "reviewer.route_challenge":
        return missing
    run_prefix = f".flowpilot/runs/{run_id}"
    product_model_path = f"{run_prefix}/flowguard/product_behavior_model.json"
    legacy_route_product_path = f"{run_prefix}/flowguard/route_product_check.json"
    if (
        product_model_path in missing
        and legacy_route_product_path in source_values
        and (project_root / product_model_path).exists()
        and (project_root / legacy_route_product_path).exists()
    ):
        return [path for path in missing if path != product_model_path]
    return missing

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
    legacy_migration, _legacy_migration_error = _read_json(
        run_root / "material" / "legacy_material_packet_migration.json"
    )
    migrated_packet_ids = {
        str(packet.get("packet_id"))
        for packet in (legacy_migration.get("packets") if isinstance(legacy_migration, dict) else []) or []
        if isinstance(packet, dict) and packet.get("packet_id")
    }
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
        legacy_contract_migrated = (
            packet_id in migrated_packet_ids
            and isinstance(envelope_contract, dict)
            and isinstance(body_contract, dict)
            and str(envelope_contract.get("contract_id") or "")
            == str(body_contract.get("contract_id") or "")
            and _contract_uniquely_matches_role(envelope_contract, to_role)
        )
        packet_contract_ok = (contracts_same and role_unique) or legacy_contract_migrated
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
        packet_canonical_ok = not spec or (
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
                "legacy_contract_migrated": legacy_contract_migrated,
                "ledger_result_body_path": ledger_result_body_path or None,
                "envelope_result_body_path": envelope_result_body_path or None,
                "body_mentions_result_body_path": body_mentions_result_path,
                "write_target_explicit": packet_write_target_ok,
                "pm_spec_body_path": spec_body_path or None,
                "pm_spec_body_hash": spec_body_hash or None,
                "envelope_body_hash": envelope_body_hash or None,
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

def _router_external_event_contracts(project_root: Path) -> tuple[dict[str, dict[str, str]], str | None]:
    source_path = project_root / "skills" / "flowpilot" / "assets" / "flowpilot_router.py"
    try:
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except OSError as exc:
        return {}, f"router source unreadable: {exc}"
    except SyntaxError as exc:
        return {}, f"router source unparsable: {exc}"
    for node in tree.body:
        value: ast.AST | None = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "EXTERNAL_EVENTS":
            value = node.value
        elif isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "EXTERNAL_EVENTS" for target in node.targets
        ):
            value = node.value
        if value is None:
            continue
        try:
            parsed = ast.literal_eval(value)
        except (ValueError, SyntaxError) as exc:
            return {}, f"EXTERNAL_EVENTS is not literal-evaluable: {exc}"
        if not isinstance(parsed, dict):
            return {}, "EXTERNAL_EVENTS was not a dict"
        contracts: dict[str, dict[str, str]] = {}
        for event, meta in parsed.items():
            if isinstance(event, str) and isinstance(meta, dict):
                contracts[event] = {str(key): str(item) for key, item in meta.items() if isinstance(item, str)}
        return contracts, None
    return {}, "EXTERNAL_EVENTS definition not found"

def _audit_expected_role_decision_event_prereqs(router_state: object, project_root: Path) -> dict[str, object]:
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
    contracts, contract_error = _router_external_event_contracts(project_root)
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

def _required_card_source_rules(run_id: str) -> dict[str, tuple[str, ...]]:
    run_prefix = f".flowpilot/runs/{run_id}"
    return {
        "pm.product_architecture": (
            f"{run_prefix}/pm_material_understanding.json",
            f"{run_prefix}/material/pm_material_understanding_payload.json",
        ),
        "product_officer.product_architecture_modelability": (
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
        "product_officer.root_contract_modelability": (
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
        "process_officer.child_skill_conformance_model": (
            f"{run_prefix}/child_skill_gate_manifest.json",
            f"{run_prefix}/reviews/child_skill_gate_manifest_review.json",
            f"{run_prefix}/pm_child_skill_selection.json",
            f"{run_prefix}/capabilities.json",
        ),
        "product_officer.child_skill_product_fit": (
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
        "process_officer.route_process_check": (
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
        "product_officer.product_architecture_modelability": "product_architecture",
        "reviewer.product_architecture_challenge": "product_architecture",
        "pm.root_contract": "root_contract",
        "reviewer.root_contract_challenge": "root_contract",
        "product_officer.root_contract_modelability": "root_contract",
        "pm.dependency_policy": "dependency_policy",
        "pm.child_skill_selection": "child_skill_selection",
        "pm.child_skill_gate_manifest": "child_skill_gate_manifest",
        "reviewer.child_skill_gate_manifest_review": "child_skill_gate_manifest",
        "process_officer.child_skill_conformance_model": "child_skill_gate_manifest",
        "product_officer.child_skill_product_fit": "child_skill_gate_manifest",
        "pm.prior_path_context": "prior_path_context",
        "pm.route_skeleton": "route_skeleton",
        "process_officer.route_process_check": "route_skeleton",
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
        missing = _legacy_route_challenge_missing_sources(
            card_id=card_id,
            run_id=run_id,
            missing=missing,
            source_values=source_values,
            project_root=project_root,
        )
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
    if event in {"process_officer_blocks_child_skill_conformance_model", "process_officer_passes_child_skill_conformance_model"}:
        return "child_skill_conformance_model"
    if event in {"product_officer_blocks_child_skill_product_fit", "product_officer_passes_child_skill_product_fit"}:
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
        binding.get("heartbeat_active") is False
        and cleanup_status not in {"external_cleanup_may_be_required", "unknown", None}
    )
    if automation_id and not automation_exists and cleanup_status != "missing_verified":
        proven = False
    return proven, {
        "terminal_status": True,
        "heartbeat_active": binding.get("heartbeat_active"),
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

def audit_live_run(project_root: str | Path = ".") -> dict[str, object]:
    """Project the current .flowpilot run into this model's invariants.

    This is intentionally read-only. It catches file-level control-plane
    friction that the abstract state graph alone cannot see.
    """

    root = Path(project_root)
    current_path = root / ".flowpilot" / "current.json"
    current, current_error = _read_json(current_path)
    if current_error:
        return {
            "ok": True,
            "skipped": True,
            "skip_reason": current_error,
            "findings": [],
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

    run_id = str(current.get("current_run_id") or current.get("active_run_id") or "")
    run_root_rel = str(current.get("current_run_root") or current.get("active_run_root") or "")
    run_root = root / run_root_rel
    router_state, _router_error = _read_json(run_root / "router_state.json")
    prompt_ledger, _prompt_error = _read_json(run_root / "prompt_delivery_ledger.json")
    frontier, _frontier_error = _read_json(run_root / "execution_frontier.json")
    snapshot, _snapshot_error = _read_json(run_root / "route_state_snapshot.json")
    display_plan, _display_error = _read_json(run_root / "display_plan.json")
    index, _index_error = _read_json(root / ".flowpilot" / "index.json")

    findings: list[dict[str, object]] = []
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
    route_process_check_delivered = _latest_delivery(prompt_deliveries, "process_officer.route_process_check") is not None
    route_process_check_passed = bool(flags.get("process_officer_route_check_passed"))
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
            summary="process_officer.route_process_check was delivered while the current route draft had no nodes",
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
    stale_expected_wait = _audit_expected_role_decision_event_prereqs(router_state, root)
    if stale_expected_wait.get("expected_role_decision_requires_unsatisfied_flag"):
        _add_finding(
            findings,
            code="role_decision_wait_requires_unsatisfied_flag",
            severity="error",
            summary="await_role_decision exposed an external event whose requires_flag is false in current router state",
            invariant="expected_role_decisions_require_satisfied_flags",
            evidence=stale_expected_wait,
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
            code="terminal_heartbeat_cleanup_unproven",
            severity="warning",
            summary="terminal continuation cleanup lacks durable host automation proof",
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

    non_current_running_entries: list[str] = []
    if isinstance(index, dict):
        for item in index.get("runs", []):
            if isinstance(item, dict) and item.get("status") == "running" and item.get("run_id") != run_id:
                non_current_running_entries.append(str(item.get("run_id")))
    background_running_entries: list[str] = []
    if isinstance(snapshot, dict):
        for item in snapshot.get("background_running_index_entries", []):
            if isinstance(item, dict) and item.get("run_id"):
                background_running_entries.append(str(item.get("run_id")))
            elif isinstance(item, str):
                background_running_entries.append(item)
    missing_background_projection = sorted(
        set(non_current_running_entries) - set(background_running_entries)
    )
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
            },
        )
    has_explicit_active_authority = (
        not non_current_running_entries
        or (
            isinstance(snapshot, dict)
            and snapshot.get("current_pointer_is_ui_focus_only") is True
            and snapshot.get("index_running_entries_are_parallel_run_authority") is True
            and not missing_background_projection
        )
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
        controller_delivery_target_role_wait_started=True,
        controller_delivery_used_as_role_completion=False,
        controller_delivery_missing_role_output_blocker=False,
        router_owned_artifact_exists=bool(durable_reclaim_gaps),
        router_owned_artifact_proof_valid=bool(durable_reclaim_gaps),
        router_owned_postcondition_reclaimed_from_artifact=not bool(durable_reclaim_gaps),
        router_tick_saw_receipt_before_flag=bool(durable_reclaim_gaps),
        router_tick_escalated_before_reclaim=bool(durable_reclaim_gaps),
        control_blocker_lane=active_blocker_lane if pm_repair_recorded else "none",
        control_blocker_target_role="project_manager" if pm_repair_recorded else "none",
        pm_repair_decision_recorded=pm_repair_recorded,
        role_output_event_submitted=bool(pm_repair_recorded or role_output_body_gaps),
        role_output_event_accepted=bool(pm_repair_recorded),
        role_output_file_backed_body_path_present=not bool(role_output_body_gaps),
        role_output_body_hash_verified=not bool(role_output_body_gaps),
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
        terminal_host_automation_cleanup_proven=terminal_cleanup_proven,
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
        "ok": error_count == 0,
        "skipped": False,
        "run_id": run_id,
        "run_root": run_root_rel,
        "error_count": error_count,
        "warning_count": sum(1 for finding in findings if finding.get("severity") == "warning"),
        "findings": findings,
        "projected_state": projected_state.__dict__,
        "projected_invariant_failures": projected_failures,
    }


__all__ = [
    "audit_live_run",
]
