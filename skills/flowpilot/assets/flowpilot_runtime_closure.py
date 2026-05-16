"""Runtime-closure guard helpers for FlowPilot.

These helpers keep the router's closing edges explicit: officer packet loops,
resume-state quarantine, terminal user reporting, and route-display refresh.
They are pure data builders/validators so the router owns all filesystem writes.
"""

from __future__ import annotations

from typing import Any


OFFICER_REQUEST_LIFECYCLE_INDEX_SCHEMA = "flowpilot.officer_request_lifecycle_index.v1"
OFFICER_REQUEST_LIFECYCLE_ENTRY_SCHEMA = "flowpilot.officer_request_lifecycle_entry.v1"
CONTINUATION_QUARANTINE_SCHEMA = "flowpilot.continuation_quarantine.v1"
FINAL_USER_REPORT_SCHEMA = "flowpilot.final_user_report.v1"
ROUTE_DISPLAY_REFRESH_SCHEMA = "flowpilot.route_display_refresh.v1"

OFFICER_ROLES = frozenset({"process_flowguard_officer", "product_flowguard_officer"})
OFFICER_PROCESS_KINDS = frozenset({"officer_model_report", "officer_model_miss_report"})
OFFICER_OUTPUT_CONTRACT_IDS = frozenset(
    {
        "flowpilot.output_contract.officer_model_report.v1",
        "flowpilot.output_contract.flowguard_model_miss_report.v1",
    }
)
OFFICER_PACKET_TYPE = "officer_request"
PM_ROLE = "project_manager"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _nonempty(value: Any) -> bool:
    return bool(_text(value))


def is_officer_request_record(record: dict[str, Any]) -> bool:
    return (
        isinstance(record, dict)
        and _text(record.get("to_role")) in OFFICER_ROLES
        and (
            _text(record.get("process_kind")) in OFFICER_PROCESS_KINDS
            or _text(record.get("output_contract_id")) in OFFICER_OUTPUT_CONTRACT_IDS
            or _text(record.get("packet_type")) == OFFICER_PACKET_TYPE
        )
    )


def validate_officer_request_record(record: dict[str, Any]) -> list[str]:
    if not is_officer_request_record(record):
        return []
    issues: list[str] = []
    binding = record.get("process_contract_binding")
    binding = binding if isinstance(binding, dict) else {}
    if _text(record.get("requested_by_role")) != PM_ROLE:
        issues.append("requested_by_role must be project_manager")
    if _text(record.get("to_role")) not in OFFICER_ROLES:
        issues.append("to_role must be a FlowGuard officer")
    if _text(record.get("process_kind")) not in OFFICER_PROCESS_KINDS:
        issues.append("process_kind must be an officer process kind")
    if _text(record.get("output_contract_id")) not in OFFICER_OUTPUT_CONTRACT_IDS:
        issues.append("output_contract_id must be an officer output contract")
    if _text(record.get("packet_type")) != OFFICER_PACKET_TYPE:
        issues.append("packet_type must be officer_request")
    if record.get("strict_process_contract_binding") is not True:
        issues.append("strict_process_contract_binding must be true")
    if _text(record.get("required_result_next_recipient")) != PM_ROLE:
        issues.append("required_result_next_recipient must be project_manager")
    if record.get("controller_may_read_packet_body") is not False:
        issues.append("controller_may_read_packet_body must be false")
    if _text(binding.get("process_kind")) != _text(record.get("process_kind")):
        issues.append("process_contract_binding.process_kind must match record")
    if _text(binding.get("packet_type")) != OFFICER_PACKET_TYPE:
        issues.append("process_contract_binding.packet_type must be officer_request")
    if _text(binding.get("required_result_next_recipient")) != PM_ROLE:
        issues.append("process_contract_binding.required_result_next_recipient must be project_manager")
    for field in (
        "request_id",
        "packet_id",
        "packet_envelope_path",
        "packet_body_path",
        "packet_body_hash",
        "result_envelope_path",
        "result_body_path",
    ):
        if not _nonempty(record.get(field)):
            issues.append(f"{field} is required")
    return issues


def validate_officer_result_record(record: dict[str, Any], result: dict[str, Any]) -> list[str]:
    if not is_officer_request_record(record):
        return []
    issues = validate_officer_request_record(record)
    if _text(result.get("packet_id")) != _text(record.get("packet_id")):
        issues.append("result packet_id must match officer request packet")
    if _text(result.get("completed_by_role")) != _text(record.get("to_role")):
        issues.append("result completed_by_role must match officer role")
    if _text(result.get("next_recipient")) != PM_ROLE:
        issues.append("result next_recipient must be project_manager")
    if not _nonempty(result.get("result_body_path")):
        issues.append("result_body_path is required")
    if not _nonempty(result.get("result_body_hash")):
        issues.append("result_body_hash is required")
    return issues


def officer_lifecycle_entry_from_request(record: dict[str, Any], *, now: str) -> dict[str, Any]:
    issues = validate_officer_request_record(record)
    return {
        "schema_version": OFFICER_REQUEST_LIFECYCLE_ENTRY_SCHEMA,
        "request_id": record.get("request_id"),
        "batch_id": record.get("batch_id"),
        "officer_role": record.get("to_role"),
        "output_contract_id": record.get("output_contract_id"),
        "process_kind": record.get("process_kind"),
        "packet_id": record.get("packet_id"),
        "packet_type": record.get("packet_type"),
        "request_status": record.get("status"),
        "lifecycle_status": "request_registered",
        "request_authority": "pm_role_work_request",
        "request_authorized_by_role": PM_ROLE,
        "router_result_event_required": "role_work_result_returned",
        "pm_decision_event_required": "pm_records_role_work_result_decision",
        "sealed_body_refs": {
            "packet_envelope_path": record.get("packet_envelope_path"),
            "packet_body_path": record.get("packet_body_path"),
            "packet_body_hash": record.get("packet_body_hash"),
            "result_envelope_path": record.get("result_envelope_path"),
            "result_body_path": record.get("result_body_path"),
        },
        "controller_may_read_packet_body": False,
        "controller_may_read_result_body": False,
        "strict_process_contract_binding": True,
        "validation_passed": not issues,
        "validation_issues": issues,
        "registered_at": record.get("registered_at") or now,
        "updated_at": now,
    }


def officer_lifecycle_status_update(record: dict[str, Any], *, lifecycle_status: str, now: str) -> dict[str, Any]:
    update = {
        "request_id": record.get("request_id"),
        "request_status": record.get("status"),
        "lifecycle_status": lifecycle_status,
        "updated_at": now,
    }
    if lifecycle_status == "packet_relayed":
        update["packet_relayed_at"] = record.get("packet_relayed_at") or now
    elif lifecycle_status == "result_relayed_to_pm":
        update["result_relayed_to_pm_at"] = record.get("result_relayed_to_pm_at") or now
    return update


def officer_lifecycle_result_update(record: dict[str, Any], result: dict[str, Any], *, now: str) -> dict[str, Any]:
    issues = validate_officer_result_record(record, result)
    return {
        "request_id": record.get("request_id"),
        "request_status": record.get("status"),
        "lifecycle_status": "result_returned",
        "router_result_event_seen": True,
        "result_authority": "role_work_result_returned",
        "result_envelope_path": record.get("result_envelope_path"),
        "result_envelope_hash": record.get("result_envelope_hash"),
        "result_body_path": record.get("result_body_path") or result.get("result_body_path"),
        "result_body_hash": record.get("result_body_hash") or result.get("result_body_hash"),
        "result_completed_by_role": result.get("completed_by_role"),
        "result_next_recipient": result.get("next_recipient"),
        "controller_may_read_result_body": False,
        "validation_passed": not issues,
        "validation_issues": issues,
        "result_returned_at": record.get("result_returned_at") or now,
        "updated_at": now,
    }


def officer_lifecycle_decision_update(record: dict[str, Any], decision_record: dict[str, Any], *, now: str) -> dict[str, Any]:
    decision = _text(decision_record.get("decision"))
    return {
        "request_id": record.get("request_id"),
        "request_status": record.get("status"),
        "lifecycle_status": f"pm_{decision}" if decision else "pm_decision_recorded",
        "pm_decision_authority": "pm_records_role_work_result_decision",
        "pm_decision": decision or None,
        "pm_decision_path": record.get("pm_result_decision", {}).get("decision_path")
        if isinstance(record.get("pm_result_decision"), dict)
        else None,
        "pm_decision_recorded_at": decision_record.get("recorded_at") or now,
        "closed_by_pm": decision in {"absorbed", "canceled", "superseded"},
        "updated_at": now,
    }


def continuation_quarantine_record(
    *,
    run_id: str,
    run_root: str,
    current_pointer: dict[str, Any],
    run_index: dict[str, Any],
    created_at: str,
) -> dict[str, Any]:
    prior_runs: list[dict[str, Any]] = []
    for item in run_index.get("runs", []):
        if not isinstance(item, dict):
            continue
        item_run_id = _text(item.get("run_id"))
        if not item_run_id or item_run_id == run_id:
            continue
        prior_runs.append(
            {
                "run_id": item_run_id,
                "run_root": item.get("run_root"),
                "status": item.get("status"),
                "authority": "history_only",
            }
        )
    current_run_id = _text(current_pointer.get("current_run_id") or current_pointer.get("active_run_id"))
    current_run_root = _text(current_pointer.get("current_run_root") or current_pointer.get("active_run_root"))
    return {
        "schema_version": CONTINUATION_QUARANTINE_SCHEMA,
        "run_id": run_id,
        "run_root": run_root,
        "current_pointer_matches_run": current_run_id == run_id and current_run_root == run_root,
        "current_run_state_authority": "current_run_root_only",
        "prior_run_files_authority": "audit_history_only",
        "prior_run_files_are_evidence_by_default": False,
        "old_agent_ids_are_current_authority": False,
        "old_assets_are_current_evidence_by_default": False,
        "fresh_role_rehydration_required_for_current_authority": True,
        "prior_runs_quarantined": prior_runs,
        "old_agent_ids": [],
        "old_assets": [],
        "created_at": created_at,
    }


def validate_continuation_quarantine_record(record: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if record.get("schema_version") != CONTINUATION_QUARANTINE_SCHEMA:
        issues.append("schema_version mismatch")
    if record.get("prior_run_files_are_evidence_by_default") is not False:
        issues.append("prior run files must not be evidence by default")
    if record.get("old_agent_ids_are_current_authority") is not False:
        issues.append("old agent ids must not be current authority")
    if record.get("old_assets_are_current_evidence_by_default") is not False:
        issues.append("old assets must not be current evidence by default")
    if record.get("current_run_state_authority") != "current_run_root_only":
        issues.append("current run state authority must stay current-run scoped")
    return issues


def final_user_report_record(
    *,
    run_id: str,
    lifecycle_status: str,
    summary_path: str,
    summary_json_path: str,
    summary_sha256: str,
    displayed_to_user: bool,
    written_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": FINAL_USER_REPORT_SCHEMA,
        "run_id": run_id,
        "run_lifecycle_status": lifecycle_status,
        "report_authority": "terminal_summary_after_lifecycle_terminal",
        "report_after_lifecycle_terminal": True,
        "final_report_is_completion_authority": False,
        "controller_may_continue_route_work": False,
        "summary_markdown_path": summary_path,
        "summary_json_path": summary_json_path,
        "summary_sha256": summary_sha256,
        "displayed_to_user": displayed_to_user,
        "written_at": written_at,
    }


def validate_final_user_report_record(record: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if record.get("schema_version") != FINAL_USER_REPORT_SCHEMA:
        issues.append("schema_version mismatch")
    if record.get("report_after_lifecycle_terminal") is not True:
        issues.append("final user report must be after lifecycle terminal")
    if record.get("final_report_is_completion_authority") is not False:
        issues.append("final user report must not be completion authority")
    if record.get("displayed_to_user") is not True:
        issues.append("final user report must be displayed to user")
    return issues


def route_display_refresh_record(
    *,
    run_id: str,
    display_plan_path: str,
    route_state_snapshot_path: str,
    route_state_snapshot_hash: str | None,
    projection_hash: str,
    route_sign_markdown_path: str | None,
    route_sign_mermaid_sha256: str | None,
    display_kind: str | None,
    refreshed_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": ROUTE_DISPLAY_REFRESH_SCHEMA,
        "run_id": run_id,
        "display_plan_path": display_plan_path,
        "route_state_snapshot_path": route_state_snapshot_path,
        "route_state_snapshot_hash": route_state_snapshot_hash,
        "projection_hash": projection_hash,
        "route_sign_markdown_path": route_sign_markdown_path,
        "route_sign_mermaid_sha256": route_sign_mermaid_sha256,
        "display_kind": display_kind,
        "refresh_authority": "route_state_snapshot_and_execution_frontier",
        "display_is_route_authority": False,
        "display_version_matches_frontier": bool(route_state_snapshot_hash and projection_hash),
        "stale_when_any_source_hash_changes": True,
        "refreshed_at": refreshed_at,
    }


def validate_route_display_refresh_record(record: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if record.get("schema_version") != ROUTE_DISPLAY_REFRESH_SCHEMA:
        issues.append("schema_version mismatch")
    if record.get("display_is_route_authority") is not False:
        issues.append("display must not be route authority")
    if record.get("refresh_authority") != "route_state_snapshot_and_execution_frontier":
        issues.append("refresh authority must be the route snapshot/frontier")
    if not record.get("projection_hash"):
        issues.append("projection_hash is required")
    return issues
