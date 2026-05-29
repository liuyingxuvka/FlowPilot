"""Metadata scanners for Controller wait receipt audits."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flowpilot_router_io import project_relative, read_json_if_exists


_DONE_WORDS = (
    "submitted",
    "complete",
    "completed",
    "done",
    "ready",
    "交了",
    "提交",
    "完成",
)


def _nonempty(value: object) -> bool:
    return value not in (None, "", [])


def _as_list(value: object) -> list[Any]:
    if isinstance(value, list):
        return value
    if value in (None, "", []):
        return []
    return [value]


def _as_str_set(*values: object) -> set[str]:
    result: set[str] = set()
    for value in values:
        for item in _as_list(value):
            text = str(item or "").strip()
            if text:
                result.add(text)
    return result


def _split_roles(value: object) -> set[str]:
    roles: set[str] = set()
    for item in _as_list(value):
        for part in str(item or "").replace(";", ",").split(","):
            role = part.strip()
            if role:
                roles.add(role)
    return roles


def _path_text(value: object) -> str:
    return str(value or "").replace("\\", "/").strip()


def _path_matches(candidate: object, expected_paths: set[str]) -> bool:
    if not expected_paths:
        return False
    text = _path_text(candidate)
    return bool(text and text in expected_paths)


def _role_matches(candidate: object, roles: set[str]) -> bool:
    return bool(roles and str(candidate or "").strip() in roles)


def _event_matches(candidate: object, events: set[str]) -> bool:
    return bool(events and str(candidate or "").strip() in events)


def _packet_matches(candidate: object, packet_ids: set[str]) -> bool:
    return bool(packet_ids and str(candidate or "").strip() in packet_ids)


def _has_wait(current_wait: dict[str, Any]) -> bool:
    keys = (
        "action_type",
        "label",
        "waiting_for_role",
        "target_role",
        "to_role",
        "allowed_external_events",
        "expected_return_path",
        "expected_evidence",
        "wait_class",
    )
    return any(_nonempty(current_wait.get(key)) for key in keys)


def _expected_path_set(current_wait: dict[str, Any]) -> set[str]:
    paths = _as_str_set(current_wait.get("expected_return_path"))
    evidence = current_wait.get("expected_evidence")
    for item in _as_list(evidence):
        if isinstance(item, dict):
            paths.update(_as_str_set(item.get("path"), item.get("result_envelope_path"), item.get("envelope_path")))
        else:
            paths.update(_as_str_set(item))
    return {_path_text(path) for path in paths if _path_text(path)}


def _current_wait_fingerprint(current_wait: dict[str, Any]) -> dict[str, Any]:
    return {
        "action_type": current_wait.get("action_type"),
        "label": current_wait.get("label"),
        "waiting_for_role": current_wait.get("waiting_for_role"),
        "target_role": current_wait.get("target_role"),
        "wait_class": current_wait.get("wait_class"),
        "allowed_external_events": current_wait.get("allowed_external_events") or [],
        "expected_return_path": current_wait.get("expected_return_path"),
    }


def _match_record(
    record: dict[str, Any],
    *,
    roles: set[str],
    events: set[str],
    paths: set[str],
    packet_ids: set[str],
) -> bool:
    path_values = (
        record.get("ack_path"),
        record.get("expected_return_path"),
        record.get("result_envelope_path"),
        record.get("router_next_action_notice_path"),
        record.get("controller_next_action_notice_path"),
        record.get("notice_path"),
        record.get("receipt_path"),
        record.get("body_path"),
    )
    if any(_path_matches(value, paths) for value in path_values):
        return True
    event_values = (
        record.get("event"),
        record.get("event_name"),
        record.get("router_event_name"),
        record.get("card_return_event"),
        record.get("satisfied_by_external_event"),
    )
    if any(_event_matches(value, events) for value in event_values):
        return True
    role_values = (
        record.get("role"),
        record.get("role_key"),
        record.get("target_role"),
        record.get("waiting_for_role"),
        record.get("completed_by_role"),
        record.get("progress_updated_by_role"),
        record.get("from_role"),
    )
    if any(_role_matches(value, roles) for value in role_values):
        return True
    packet_values = (
        record.get("packet_id"),
        record.get("active_packet_id"),
    )
    return any(_packet_matches(value, packet_ids) for value in packet_values)


def _is_malformed(record: dict[str, Any], required_keys: tuple[str, ...]) -> bool:
    return any(not _nonempty(record.get(key)) for key in required_keys)


def _add_match(
    matches: list[dict[str, Any]],
    *,
    surface: str,
    path: Path | None = None,
    kind: str,
    record: dict[str, Any],
    malformed: bool = False,
) -> None:
    matches.append(
        {
            "surface": surface,
            "path": str(path) if path is not None else None,
            "kind": kind,
            "malformed": malformed,
            "event": record.get("event") or record.get("event_name") or record.get("router_event_name"),
            "role": record.get("role") or record.get("role_key") or record.get("completed_by_role") or record.get("from_role"),
            "packet_id": record.get("packet_id"),
            "result_envelope_path": record.get("result_envelope_path"),
            "notice_path": record.get("notice_path") or record.get("router_next_action_notice_path"),
            "body_path_present": bool(record.get("body_path") or record.get("result_body_path") or record.get("body_ref")),
        }
    )


def _aside_claims_done(aside: object) -> bool:
    if not isinstance(aside, dict):
        return False
    text = str(aside.get("text") or "").strip().lower()
    return bool(text and any(word in text for word in _DONE_WORDS))


def _scan_return_ledger(
    run_root: Path,
    *,
    roles: set[str],
    events: set[str],
    paths: set[str],
    packet_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    path = run_root / "return_event_ledger.json"
    ledger = read_json_if_exists(path)
    matches: list[dict[str, Any]] = []
    asides: list[dict[str, Any]] = []
    for section in ("completed_returns", "pending_returns"):
        for item in ledger.get(section, []) if isinstance(ledger.get(section), list) else []:
            if not isinstance(item, dict):
                continue
            if _match_record(item, roles=roles, events=events, paths=paths, packet_ids=packet_ids):
                malformed = _is_malformed(item, ("role_key",)) or not (
                    _nonempty(item.get("ack_path")) or _nonempty(item.get("card_return_event"))
                )
                _add_match(matches, surface="return_event_ledger", path=path, kind=section, record=item, malformed=malformed)
            if _aside_claims_done(item.get("controller_aside")):
                _add_match(asides, surface="return_event_ledger", path=path, kind=section, record=item)
    return matches, asides


def _scan_role_outputs(
    run_root: Path,
    *,
    roles: set[str],
    events: set[str],
    paths: set[str],
    packet_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    del packet_ids
    matches: list[dict[str, Any]] = []
    asides: list[dict[str, Any]] = []
    ledger_path = run_root / "role_output_ledger.json"
    ledger = read_json_if_exists(ledger_path)
    outputs = ledger.get("outputs") if isinstance(ledger.get("outputs"), list) else []
    for item in outputs:
        if not isinstance(item, dict):
            continue
        envelope = item.get("envelope") if isinstance(item.get("envelope"), dict) else {}
        merged = {**envelope, **item}
        if _match_record(merged, roles=roles, events=events, paths=paths, packet_ids=set()):
            malformed = _is_malformed(merged, ("role", "output_type")) or not (
                _nonempty(merged.get("receipt_path")) or _nonempty(merged.get("body_path")) or _nonempty(envelope.get("body_ref"))
            )
            _add_match(matches, surface="role_output_ledger", path=ledger_path, kind="output", record=merged, malformed=malformed)
        if _aside_claims_done(envelope.get("controller_aside")):
            _add_match(asides, surface="role_output_ledger", path=ledger_path, kind="output_aside", record=merged)

    status_dir = run_root / "role_output_status"
    if status_dir.exists():
        for path in status_dir.glob("*.json"):
            status = read_json_if_exists(path)
            if not status:
                continue
            if _match_record(status, roles=roles, events=events, paths=paths, packet_ids=set()):
                malformed = _is_malformed(status, ("status",)) or not (
                    _nonempty(status.get("event_name")) or _nonempty(status.get("router_event_name"))
                )
                _add_match(matches, surface="role_output_status", path=path, kind="status_packet", record=status, malformed=malformed)
            if _aside_claims_done(status.get("controller_aside")):
                _add_match(asides, surface="role_output_status", path=path, kind="status_aside", record=status)
    return matches, asides


def _scan_packets(
    project_root: Path,
    run_root: Path,
    *,
    roles: set[str],
    events: set[str],
    paths: set[str],
    packet_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    del events
    formal_matches: list[dict[str, Any]] = []
    result_matches: list[dict[str, Any]] = []
    notice_matches: list[dict[str, Any]] = []
    asides: list[dict[str, Any]] = []
    ledger_path = run_root / "packet_ledger.json"
    ledger = read_json_if_exists(ledger_path)
    packets = ledger.get("packets") if isinstance(ledger.get("packets"), list) else []
    for item in packets:
        if not isinstance(item, dict):
            continue
        packet_id = str(item.get("packet_id") or "")
        local_packet_ids = set(packet_ids)
        if not local_packet_ids and paths:
            local_packet_ids.add(packet_id)
        result_record = item.get("result_envelope") if isinstance(item.get("result_envelope"), dict) else {}
        notice_record = item.get("router_next_action_notice") if isinstance(item.get("router_next_action_notice"), dict) else {}
        merged_result = {**result_record, **item}
        if result_record and _match_record(merged_result, roles=roles, events=set(), paths=paths, packet_ids=local_packet_ids):
            malformed = _is_malformed(result_record, ("completed_by_role", "result_body_path", "result_body_hash"))
            _add_match(formal_matches, surface="packet_ledger", path=ledger_path, kind="result_envelope", record=merged_result, malformed=malformed)
            _add_match(result_matches, surface="packet_ledger", path=ledger_path, kind="result_envelope", record=merged_result, malformed=malformed)
        if notice_record and _match_record(notice_record, roles=roles, events=set(), paths=paths, packet_ids=local_packet_ids):
            malformed = _is_malformed(notice_record, ("next_action", "result_envelope_path"))
            _add_match(notice_matches, surface="packet_ledger", path=ledger_path, kind="next_action_notice", record=notice_record, malformed=malformed)
        for aside_source in (item.get("controller_aside"), item.get("active_holder_latest_progress_event", {}).get("controller_aside") if isinstance(item.get("active_holder_latest_progress_event"), dict) else None, result_record.get("controller_aside"), notice_record.get("controller_aside")):
            if _aside_claims_done(aside_source):
                _add_match(asides, surface="packet_ledger", path=ledger_path, kind="packet_aside", record=merged_result or item)

    packet_root = run_root / "packets"
    if packet_root.exists():
        for envelope_path in packet_root.glob("*/result_envelope.json"):
            envelope = read_json_if_exists(envelope_path)
            if not envelope:
                continue
            packet_id = envelope_path.parent.name
            merged = {
                **envelope,
                "packet_id": packet_id,
                "result_envelope_path": project_relative(project_root, envelope_path),
            }
            local_packet_ids = packet_ids or {packet_id}
            if _match_record(merged, roles=roles, events=set(), paths=paths, packet_ids=local_packet_ids):
                malformed = _is_malformed(envelope, ("completed_by_role", "result_body_path", "result_body_hash"))
                _add_match(formal_matches, surface="packet_result_envelope", path=envelope_path, kind="result_envelope", record=merged, malformed=malformed)
                _add_match(result_matches, surface="packet_result_envelope", path=envelope_path, kind="result_envelope", record=merged, malformed=malformed)
            if _aside_claims_done(envelope.get("controller_aside")):
                _add_match(asides, surface="packet_result_envelope", path=envelope_path, kind="result_aside", record=merged)
        for notice_path in packet_root.glob("*/controller_next_action_notice.json"):
            notice = read_json_if_exists(notice_path)
            if not notice:
                continue
            packet_id = notice_path.parent.name
            local_packet_ids = packet_ids or {packet_id}
            if _match_record(notice, roles=roles, events=set(), paths=paths, packet_ids=local_packet_ids):
                malformed = _is_malformed(notice, ("next_action", "result_envelope_path"))
                _add_match(notice_matches, surface="controller_next_action_notice", path=notice_path, kind="next_action_notice", record=notice, malformed=malformed)
            if _aside_claims_done(notice.get("controller_aside")):
                _add_match(asides, surface="controller_next_action_notice", path=notice_path, kind="notice_aside", record=notice)
    return formal_matches, result_matches, notice_matches, asides


def _scan_run_events(
    run_state: dict[str, Any],
    *,
    roles: set[str],
    events: set[str],
    paths: set[str],
    packet_ids: set[str],
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for section in ("events", "history"):
        rows = run_state.get(section) if isinstance(run_state.get(section), list) else []
        for item in rows:
            if not isinstance(item, dict):
                continue
            payload = item.get("payload") if isinstance(item.get("payload"), dict) else item.get("details")
            payload = payload if isinstance(payload, dict) else {}
            merged = {**payload, **item}
            if _match_record(merged, roles=roles, events=events, paths=paths, packet_ids=packet_ids):
                malformed = not (_nonempty(merged.get("event")) or _nonempty(merged.get("label")))
                _add_match(matches, surface=f"run_state.{section}", kind="router_event", record=merged, malformed=malformed)
    return matches


def _scan_controller_actions(run_root: Path) -> list[dict[str, Any]]:
    ledger_path = run_root / "runtime" / "controller_action_ledger.json"
    ledger = read_json_if_exists(ledger_path)
    rows = ledger.get("actions") if isinstance(ledger.get("actions"), list) else []
    matches: list[dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        if item.get("status") in {"pending", "in_progress"} and bool(item.get("ordinary_controller_work_row", True)):
            _add_match(matches, surface="controller_action_ledger", path=ledger_path, kind="controller_action", record=item)
    return matches
