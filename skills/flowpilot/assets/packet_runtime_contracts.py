"""Identity and output-contract helpers for packet runtime envelopes."""

from __future__ import annotations

import json
from typing import Any

from packet_runtime_schema import (
    DEFAULT_OUTPUT_CONTRACT_BY_PACKET_TYPE,
    DEFAULT_OUTPUT_CONTRACT_CONDITIONAL_RESULT_SECTIONS_BY_PACKET_TYPE,
    DEFAULT_OUTPUT_CONTRACT_TASK_FAMILY_BY_PACKET_TYPE,
    MUTUAL_ROLE_REMINDER_SCHEMA,
    OUTPUT_CONTRACT_FORBIDDEN_ENVELOPE_BODY_FIELDS,
    OUTPUT_CONTRACT_REQUIRED_RESULT_ENVELOPE_FIELDS,
    OUTPUT_CONTRACT_REQUIRED_RESULT_SECTIONS,
    OUTPUT_CONTRACT_SCHEMA,
    PACKET_IDENTITY_MARKER,
    RESULT_IDENTITY_MARKER,
    PacketRuntimeError,
)
from flowpilot_prompt_store import render_prompt_text


def mutual_role_reminder(*, source_role: str, target_role: str, envelope_kind: str) -> dict[str, str]:
    return {
        "schema_version": MUTUAL_ROLE_REMINDER_SCHEMA,
        "controller_reminder": (
            f"You are Controller only. Relay and record this {envelope_kind}; do not open, "
            "summarize, execute, approve gates, mutate routes, close nodes, or issue "
            "free-text work instructions."
        ),
        "sender_reminder": f"The sender/producer for this envelope is `{source_role}`.",
        "recipient_reminder": (
            f"The recipient is `{target_role}` for this envelope only. Open the body only "
            "after verifying Controller relay, role target, and hash; act only inside the "
            "addressed role and packet/result scope."
        ),
        "reply_continuation_reminder": (
            "When returning or relaying the next envelope, include this same visible "
            "mutual-role reminder so Controller and the next recipient are reminded again."
        ),
        "body_boundary_reminder": (
            "Keep sealed body content out of Controller-visible chat; return envelope "
            "metadata only."
        ),
    }


def packet_open_work_authority(*, role: str, packet_type: str, source: str) -> dict[str, Any]:
    if role == "project_manager":
        required_exit = "expected_pm_packet_output_or_existing_pm_recovery_decision"
        legal_exits = [
            "expected_packet_result",
            "pm_startup_repair_request",
            "pm_startup_protocol_dead_end",
            "pm_control_blocker_repair_decision",
        ]
    else:
        required_exit = "expected_packet_result_or_existing_formal_blocker"
        legal_exits = [
            "expected_packet_result",
            "existing_formal_blocker",
            "result_with_blocker",
            "pm_suggestion_when_allowed",
        ]
    return {
        "schema_version": "flowpilot.packet_open_work_authority.v1",
        "authorized": True,
        "role": role,
        "packet_type": packet_type,
        "scope": "addressed_packet_only",
        "source": source,
        "controller_relay_or_startup_release_verified": True,
        "body_hash_verified": True,
        "do_not_wait_for_additional_controller_relay": True,
        "required_exit": required_exit,
        "legal_exits": legal_exits,
    }


def packet_identity_boundary(role: str) -> str:
    return render_prompt_text(
        "packets.packet_identity_boundary",
        {
            "packet_identity_marker": PACKET_IDENTITY_MARKER,
            "role": role,
        },
    )


def result_identity_boundary(role: str) -> str:
    return render_prompt_text(
        "packets.result_identity_boundary",
        {
            "result_identity_marker": RESULT_IDENTITY_MARKER,
            "role": role,
        },
    )


def ensure_packet_identity_boundary(body_text: str, role: str) -> str:
    if PACKET_IDENTITY_MARKER in body_text:
        return body_text
    return packet_identity_boundary(role) + body_text


def ensure_result_identity_boundary(body_text: str, role: str) -> str:
    if RESULT_IDENTITY_MARKER in body_text:
        return body_text
    return result_identity_boundary(role) + body_text


def validate_packet_identity_boundary(body_text: str, role: str) -> None:
    if PACKET_IDENTITY_MARKER not in body_text:
        raise PacketRuntimeError("packet body missing role identity boundary")
    if f"recipient_role: {role}" not in body_text:
        raise PacketRuntimeError(f"packet body identity boundary does not target role {role!r}")


def validate_result_identity_boundary(body_text: str, role: str) -> None:
    if RESULT_IDENTITY_MARKER not in body_text:
        raise PacketRuntimeError("result body missing role identity boundary")
    if f"completed_by_role: {role}" not in body_text:
        raise PacketRuntimeError(f"result body identity boundary does not match role {role!r}")


def default_output_contract(
    *,
    packet_type: str,
    from_role: str,
    to_role: str,
    node_id: str,
) -> dict[str, Any] | None:
    if from_role != "project_manager":
        return None
    contract_id = DEFAULT_OUTPUT_CONTRACT_BY_PACKET_TYPE.get(packet_type)
    if not contract_id:
        return None
    contract = {
        "schema_version": OUTPUT_CONTRACT_SCHEMA,
        "contract_id": contract_id,
        "selected_by_role": "project_manager",
        "recipient_role": to_role,
        "task_family": DEFAULT_OUTPUT_CONTRACT_TASK_FAMILY_BY_PACKET_TYPE.get(packet_type, packet_type),
        "node_id": node_id,
        "required_result_body_sections": OUTPUT_CONTRACT_REQUIRED_RESULT_SECTIONS,
        "required_result_envelope_fields": OUTPUT_CONTRACT_REQUIRED_RESULT_ENVELOPE_FIELDS,
        "forbidden_envelope_body_fields": OUTPUT_CONTRACT_FORBIDDEN_ENVELOPE_BODY_FIELDS,
        "contract_self_check_required": True,
        "reviewer_must_block_missing_or_failed_check": True,
        "registry_path": "runtime_kit/contracts/contract_index.json",
    }
    conditional_sections = DEFAULT_OUTPUT_CONTRACT_CONDITIONAL_RESULT_SECTIONS_BY_PACKET_TYPE.get(packet_type)
    if conditional_sections:
        contract["conditional_required_result_body_sections"] = conditional_sections
    return contract


def normalize_output_contract(
    output_contract: dict[str, Any] | None,
    *,
    packet_type: str,
    from_role: str,
    to_role: str,
    node_id: str,
) -> dict[str, Any] | None:
    if output_contract is None:
        return default_output_contract(
            packet_type=packet_type,
            from_role=from_role,
            to_role=to_role,
            node_id=node_id,
        )
    if not isinstance(output_contract, dict):
        raise PacketRuntimeError("output_contract must be an object")
    normalized = dict(output_contract)
    normalized.setdefault("schema_version", OUTPUT_CONTRACT_SCHEMA)
    normalized.setdefault("selected_by_role", from_role)
    normalized.setdefault("recipient_role", to_role)
    normalized.setdefault("task_family", DEFAULT_OUTPUT_CONTRACT_TASK_FAMILY_BY_PACKET_TYPE.get(packet_type, packet_type))
    normalized.setdefault("node_id", node_id)
    normalized.setdefault("required_result_body_sections", OUTPUT_CONTRACT_REQUIRED_RESULT_SECTIONS)
    normalized.setdefault("required_result_envelope_fields", OUTPUT_CONTRACT_REQUIRED_RESULT_ENVELOPE_FIELDS)
    normalized.setdefault("forbidden_envelope_body_fields", OUTPUT_CONTRACT_FORBIDDEN_ENVELOPE_BODY_FIELDS)
    conditional_sections = DEFAULT_OUTPUT_CONTRACT_CONDITIONAL_RESULT_SECTIONS_BY_PACKET_TYPE.get(packet_type)
    if conditional_sections:
        normalized.setdefault("conditional_required_result_body_sections", conditional_sections)
    normalized.setdefault("contract_self_check_required", True)
    normalized.setdefault("reviewer_must_block_missing_or_failed_check", True)
    normalized.setdefault("registry_path", "runtime_kit/contracts/contract_index.json")
    if normalized.get("schema_version") != OUTPUT_CONTRACT_SCHEMA:
        raise PacketRuntimeError("output_contract has unsupported schema_version")
    if not normalized.get("contract_id"):
        raise PacketRuntimeError("output_contract.contract_id is required")
    if normalized.get("recipient_role") != to_role:
        raise PacketRuntimeError("output_contract.recipient_role must match packet to_role")
    if from_role == "project_manager" and normalized.get("selected_by_role") != "project_manager":
        raise PacketRuntimeError("PM-authored packets require output_contract.selected_by_role=project_manager")
    return normalized


def output_contract_id(output_contract: dict[str, Any] | None) -> str:
    if not isinstance(output_contract, dict):
        return ""
    return str(output_contract.get("contract_id") or "")


def _contract_value_for_field(output_contract: dict[str, Any], field_path: str) -> Any:
    values = output_contract.get("required_body_values")
    if isinstance(values, dict) and field_path in values:
        return values[field_path]
    if field_path.endswith("_paths") or field_path.endswith("_ids") or field_path.endswith("_items"):
        return []
    if field_path in {"segment_reviews", "commands_run", "hard_invariants", "skipped_checks"}:
        return []
    if field_path in {"passed", "pm_ready", "sufficient"}:
        return False
    return "<required>"


def _set_contract_template_field(target: dict[str, Any], field_path: str, value: Any) -> None:
    parts = [part for part in field_path.split(".") if part]
    if not parts:
        return
    cursor = target
    for part in parts[:-1]:
        existing = cursor.get(part)
        if not isinstance(existing, dict):
            existing = {}
            cursor[part] = existing
        cursor = existing
    cursor[parts[-1]] = value


def _contract_body_template(output_contract: dict[str, Any]) -> dict[str, Any]:
    template: dict[str, Any] = {}
    fields: list[str] = []
    for key in ("required_body_fields", "required_report_body_fields"):
        raw = output_contract.get(key)
        if isinstance(raw, list):
            fields.extend(str(item) for item in raw if str(item).strip())
    values = output_contract.get("required_body_values")
    if isinstance(values, dict):
        for field_path in values:
            if field_path not in fields:
                fields.append(str(field_path))
    for field_path in fields:
        _set_contract_template_field(template, field_path, _contract_value_for_field(output_contract, field_path))
    return template


def _contract_list_block(title: str, values: Any) -> str:
    if not values:
        return ""
    if isinstance(values, dict):
        rendered = json.dumps(values, indent=2, sort_keys=True)
        return f"{title}:\n\n```json\n{rendered}\n```\n\n"
    if isinstance(values, list):
        lines = "\n".join(f"- `{item}`" for item in values)
        return f"{title}:\n\n{lines}\n\n"
    return f"{title}: `{values}`\n\n"


def output_contract_section(output_contract: dict[str, Any]) -> str:
    body_template = _contract_body_template(output_contract)
    body_template_block = ""
    if body_template:
        body_template_block = (
            "Required body JSON skeleton. Keep these exact field names; do not "
            "replace them with synonyms:\n\n"
            "```json\n"
            f"{json.dumps(body_template, indent=2, sort_keys=True)}\n"
            "```\n\n"
        )
    required_sections_block = _contract_list_block(
        "Required sealed body sections",
        output_contract.get("required_result_body_sections"),
    )
    required_envelope_block = _contract_list_block(
        "Required return envelope fields",
        output_contract.get("required_result_envelope_fields"),
    )
    required_values_block = _contract_list_block(
        "Required exact body values",
        output_contract.get("required_body_values"),
    )
    allowed_decisions_block = _contract_list_block(
        "Allowed decision values",
        output_contract.get("allowed_decision_values"),
    )
    segment_values_block = _contract_list_block(
        "Required values for each segment review",
        output_contract.get("segment_review_required_values"),
    )
    return render_prompt_text(
        "packets.output_contract_section",
        {
            "allowed_decisions_block": allowed_decisions_block,
            "body_template_block": body_template_block,
            "json_contract": json.dumps(output_contract, indent=2, sort_keys=True),
            "required_envelope_block": required_envelope_block,
            "required_sections_block": required_sections_block,
            "required_values_block": required_values_block,
            "segment_values_block": segment_values_block,
        },
    )


def ensure_packet_output_contract_section(body_text: str, output_contract: dict[str, Any] | None) -> str:
    if not output_contract:
        return body_text
    heading_index = body_text.find("## Output Contract")
    if heading_index >= 0:
        fence_start = body_text.find("```json", heading_index)
        if fence_start >= 0:
            json_start = body_text.find("\n", fence_start)
            if json_start >= 0:
                json_start += 1
                fence_end = body_text.find("```", json_start)
                if fence_end >= 0:
                    canonical = json.dumps(output_contract, indent=2, sort_keys=True)
                    return body_text[:json_start] + canonical + "\n" + body_text[fence_end:]
    return body_text.rstrip() + "\n" + output_contract_section(output_contract)


def contract_self_check_metadata(result_body_text: str, output_contract: dict[str, Any] | None) -> dict[str, Any]:
    required = bool(output_contract and output_contract.get("contract_self_check_required", True))
    completed = "## Contract Self-Check" in result_body_text
    lower = result_body_text.lower()
    passed = completed and (
        "self_check_decision: satisfied" in lower
        or "self-check decision: satisfied" in lower
        or "self_check_decision: pass" in lower
    )
    return {
        "required": required,
        "source_output_contract_id": output_contract_id(output_contract),
        "result_body_section": "Contract Self-Check",
        "completed": completed,
        "passed": passed,
    }
