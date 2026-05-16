"""Pure dispatch-recipient gate helpers for FlowPilot router."""

from __future__ import annotations

from typing import Any


ROLE_WORK_RESULT_RETURNED_EVENT = "role_work_result_returned"
DISPATCH_RECIPIENT_GATE_SAME_OBLIGATION_CARDS_BY_PACKET = {
    ("project_manager", "user_intake"): "pm.material_scan",
}
DISPATCH_RECIPIENT_GATE_PACKET_COMPLETION_FLAGS = {
    "user_intake": "pm_material_packets_issued",
}
PM_ROLE_WORK_TARGET_BUSY_STATUSES = {"open", "packet_created", "packet_relayed"}
PM_ROLE_WORK_PM_BUSY_STATUSES = {"result_returned", "result_relayed_to_pm"}


def _role_set(value: str) -> set[str]:
    return {part.strip() for part in value.split(",") if part.strip()}


def _dispatch_gate_target_roles(action: dict[str, Any]) -> set[str]:
    return _role_set(str(action.get("to_role") or ""))


def _dispatch_gate_candidate_packet_ids(action: dict[str, Any]) -> set[str]:
    packet_ids: set[str] = set()
    for key in ("packet_id", "mail_id"):
        value = str(action.get(key) or "").strip()
        if value:
            packet_ids.add(value)
    raw_packet_ids = action.get("packet_ids")
    if isinstance(raw_packet_ids, list):
        packet_ids.update(str(item).strip() for item in raw_packet_ids if str(item).strip())
    active_holder = action.get("active_holder_fast_lane")
    packets = active_holder.get("packets") if isinstance(active_holder, dict) else None
    if isinstance(packets, list):
        for item in packets:
            if isinstance(item, dict):
                packet_id = str(item.get("packet_id") or "").strip()
                if packet_id:
                    packet_ids.add(packet_id)
    return packet_ids


def _dispatch_gate_candidate_request_ids(action: dict[str, Any]) -> set[str]:
    request_ids: set[str] = set()
    value = str(action.get("request_id") or "").strip()
    if value:
        request_ids.add(value)
    raw_requests = action.get("request_ids")
    if isinstance(raw_requests, list):
        request_ids.update(str(item).strip() for item in raw_requests if str(item).strip())
    return request_ids


def _dispatch_gate_system_card_ids(action: dict[str, Any]) -> list[str]:
    action_type = action.get("action_type")
    if action_type == "deliver_system_card":
        card_id = str(action.get("card_id") or "").strip()
        return [card_id] if card_id else []
    if action_type != "deliver_system_card_bundle":
        return []
    card_ids: list[str] = []
    raw_card_ids = action.get("card_ids")
    if isinstance(raw_card_ids, list):
        card_ids.extend(str(item).strip() for item in raw_card_ids if str(item or "").strip())
    raw_cards = action.get("cards")
    if isinstance(raw_cards, list):
        for item in raw_cards:
            if isinstance(item, dict):
                card_id = str(item.get("card_id") or item.get("id") or "").strip()
                if card_id:
                    card_ids.append(card_id)
    return list(dict.fromkeys(card_ids))


def _dispatch_gate_wait_events_for_packet_record(record: dict[str, Any]) -> list[str]:
    packet_family = str(record.get("packet_family") or "").strip()
    packet_type = str(record.get("packet_type") or "").strip()
    packet_id = str(record.get("packet_id") or "").strip()
    holder = str(record.get("active_packet_holder") or "").strip()
    if holder == "project_manager" and packet_id == "user_intake":
        return ["pm_issues_material_and_capability_scan_packets"]
    if holder == "project_manager" and packet_id.startswith("material-scan"):
        return ["pm_records_material_scan_result_disposition"]
    if holder == "project_manager" and "research" in packet_id:
        return ["pm_records_research_result_disposition"]
    if holder == "project_manager" and "node" in packet_id:
        return ["pm_completes_current_node_from_reviewed_result"]
    if packet_family == "pm_role_work" or packet_type == "pm_role_work_request" or packet_id.startswith("pm-role-work-"):
        return [ROLE_WORK_RESULT_RETURNED_EVENT]
    if packet_family == "research" or "research" in packet_id:
        return ["worker_research_report_returned"]
    if packet_family == "material_scan" or "material" in packet_id:
        return ["worker_scan_results_returned"]
    return ["worker_current_node_result_returned", ROLE_WORK_RESULT_RETURNED_EVENT]


def _dispatch_gate_packet_completed_by_flow_state(record: dict[str, Any], run_state: dict[str, Any]) -> bool:
    packet_id = str(record.get("packet_id") or "").strip()
    completion_flag = DISPATCH_RECIPIENT_GATE_PACKET_COMPLETION_FLAGS.get(packet_id)
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    if completion_flag and flags.get(completion_flag):
        return True
    if packet_id.startswith("material-scan") and flags.get("material_scan_results_absorbed_by_pm"):
        return True
    if "research" in packet_id and flags.get("research_result_absorbed_for_review_by_pm"):
        return True
    if "node" in packet_id and flags.get("current_node_result_absorbed_by_pm"):
        return True
    return False


def _dispatch_gate_same_obligation_instruction(
    action: dict[str, Any],
    record: dict[str, Any],
    run_state: dict[str, Any],
) -> bool:
    if action.get("action_type") != "deliver_system_card":
        return False
    holder = str(record.get("active_packet_holder") or "").strip()
    packet_id = str(record.get("packet_id") or "").strip()
    expected_card = DISPATCH_RECIPIENT_GATE_SAME_OBLIGATION_CARDS_BY_PACKET.get((holder, packet_id))
    if not expected_card or str(action.get("card_id") or "") != expected_card:
        return False
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    return bool(flags.get("user_intake_delivered_to_pm") and not flags.get("pm_material_packets_issued"))
