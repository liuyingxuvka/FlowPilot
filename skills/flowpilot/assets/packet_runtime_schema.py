"""Schema constants and low-level helpers for the FlowPilot packet runtime."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flowpilot_runtime_gateway import GATEWAY_PACKET_RUNTIME, assert_runtime_gateway_write


PACKET_ENVELOPE_SCHEMA = "flowpilot.packet_envelope.v1"
RESULT_ENVELOPE_SCHEMA = "flowpilot.result_envelope.v1"
CONTROLLER_HANDOFF_SCHEMA = "flowpilot.controller_handoff.v1"
CONTROLLER_RELAY_SCHEMA = "flowpilot.controller_relay.v1"
ROUTER_STARTUP_RELEASE_SCHEMA = "flowpilot.router_startup_release.v1"
MUTUAL_ROLE_REMINDER_SCHEMA = "flowpilot.mutual_role_reminder.v1"
CHAIN_AUDIT_SCHEMA = "flowpilot.packet_chain_audit.v1"
ROLE_PACKET_SESSION_SCHEMA = "flowpilot.role_packet_runtime_session.v1"
RESULT_REVIEW_SESSION_SCHEMA = "flowpilot.result_review_runtime_session.v1"
PACKET_LEDGER_SCHEMA = "flowpilot.packet_ledger.v2"
ACTIVE_HOLDER_LEASE_SCHEMA = "flowpilot.active_holder_lease.v1"
ACTIVE_HOLDER_EVENT_SCHEMA = "flowpilot.active_holder_event.v1"
CONTROLLER_NEXT_ACTION_NOTICE_SCHEMA = "flowpilot.controller_next_action_notice.v1"
OUTPUT_CONTRACT_SCHEMA = "flowpilot.output_contract.v1"
PACKET_IDENTITY_MARKER = "FLOWPILOT_PACKET_IDENTITY_BOUNDARY_V1"
RESULT_IDENTITY_MARKER = "FLOWPILOT_RESULT_IDENTITY_BOUNDARY_V1"
PACKET_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SEALED_BODY_VISIBILITY = "sealed_target_role_only"
USER_INTAKE_BODY_VISIBILITY = "external_user_input_controller_visible"
ENVELOPE_HASH_EXCLUDED_KEYS = {
    "body_opened_by_role",
    "packet_open_work_authority",
    "controller_relay",
    "controller_relay_history",
    "router_startup_release",
    "router_startup_release_history",
    "controller_return_to_sender",
    "result_body_opened_by_role",
}

DEFAULT_CONTROLLER_ALLOWED_ACTIONS = [
    "read_packet_envelope",
    "update_packet_holder_and_status",
    "relay_envelope_to_to_role",
    "display_chat_mermaid_when_required",
    "emit_holder_change_status_update",
    "wait_for_role_return",
    "return_envelope_to_pm_on_blocker",
]

DEFAULT_CONTROLLER_FORBIDDEN_ACTIONS = [
    "read_packet_body",
    "edit_packet_body",
    "execute_packet_body",
    "implement_worker_scope",
    "generate_worker_artifacts",
    "run_product_validation_for_worker_scope",
    "approve_gate",
    "close_node",
    "change_to_role",
    "rewrite_body_hash",
    "relabel_wrong_role_origin",
]

RESULT_CONTROLLER_ALLOWED_ACTIONS = [
    "read_result_envelope",
    "update_packet_holder_and_status",
    "relay_result_envelope_to_next_recipient",
    "emit_holder_change_status_update",
    "wait_for_role_return",
]

RESULT_CONTROLLER_FORBIDDEN_ACTIONS = [
    "read_result_body",
    "edit_result_body",
    "execute_result_body",
    "summarize_result_body",
    "approve_gate",
    "close_node",
    "change_completed_by_role",
    "recompute_body_hash_to_hide_mismatch",
    "relabel_wrong_role_origin",
]

DIRECT_DISPATCH_PACKET_REQUIRED_FIELDS = [
    "schema_version",
    "packet_id",
    "packet_type",
    "from_role",
    "to_role",
    "node_id",
    "body_path",
    "body_hash",
    "body_visibility",
    "result_envelope_path",
    "result_body_path",
    "controller_allowed_actions",
    "controller_forbidden_actions",
    "body_access",
]

DIRECT_DISPATCH_REQUIRED_FORBIDDEN_ACTIONS = {
    "read_packet_body",
    "edit_packet_body",
    "execute_packet_body",
    "change_to_role",
    "rewrite_body_hash",
}

DIRECT_DISPATCH_FORBIDDEN_ALLOWED_ACTIONS = {
    "read_packet_body",
    "edit_packet_body",
    "execute_packet_body",
    "implement_worker_scope",
    "approve_gate",
    "close_node",
}

OUTPUT_CONTRACT_REQUIRED_RESULT_SECTIONS = [
    "Status",
    "Evidence",
    "Open Issues",
    "Artifact Handoff",
    "PM Suggestion Items",
    "Contract Self-Check",
]

OUTPUT_CONTRACT_REQUIRED_RESULT_ENVELOPE_FIELDS = [
    "completed_by_role",
    "completed_by_agent_id",
    "result_body_path",
    "result_body_hash",
    "next_recipient",
    "body_visibility",
]

OUTPUT_CONTRACT_FORBIDDEN_ENVELOPE_BODY_FIELDS = [
    "blockers",
    "checks",
    "commands",
    "decision",
    "evidence",
    "findings",
    "passed",
    "recommendations",
    "repair_instructions",
    "report_body",
    "decision_body",
    "result_body",
]

DEFAULT_OUTPUT_CONTRACT_BY_PACKET_TYPE = {
    "material_scan": "flowpilot.output_contract.worker_material_scan_result.v1",
    "research": "flowpilot.output_contract.worker_research_result.v1",
    "work_packet": "flowpilot.output_contract.worker_current_node_result.v1",
    "review_request": "flowpilot.output_contract.reviewer_review_report.v1",
    "flowguard_operator_request": "flowpilot.output_contract.flowguard_operator_model_report.v1",
    "pm_decision": "flowpilot.output_contract.pm_decision.v1",
}

DEFAULT_OUTPUT_CONTRACT_TASK_FAMILY_BY_PACKET_TYPE = {
    "material_scan": "worker.material_scan",
    "research": "worker.research",
    "work_packet": "worker.current_node",
    "review_request": "reviewer.review",
    "flowguard_operator_request": "flowguard_operator.model_report",
    "pm_decision": "pm.decision",
}

DEFAULT_OUTPUT_CONTRACT_CONDITIONAL_RESULT_SECTIONS_BY_PACKET_TYPE = {
    "material_scan": {
        "source_packet_declares_inherited_skill_standard_ids": ["Skill Standard Result Matrix"],
    },
    "research": {
        "source_packet_declares_inherited_skill_standard_ids": ["Skill Standard Result Matrix"],
    },
    "work_packet": {
        "source_packet_declares_inherited_skill_standard_ids": ["Skill Standard Result Matrix"],
        "source_packet_declares_active_child_skill_bindings": ["Child Skill Use Evidence"],
    },
}

PROGRESS_MESSAGE_MAX_LEN = 160
PROGRESS_MESSAGE_FORBIDDEN_TERMS = (
    "body summary",
    "evidence",
    "finding",
    "findings",
    "recommendation",
    "recommendations",
    "result details",
    "sealed body",
)

ROLE_KEYS = {
    "project_manager",
    "human_like_reviewer",
    "flowguard_operator",
    "worker",
    "controller",
}

PACKET_RUNTIME_JSON_WRITE_LOCK_TIMEOUT_SECONDS = 5.0
PACKET_RUNTIME_JSON_WRITE_LOCK_POLL_SECONDS = 0.05


class PacketRuntimeError(ValueError):
    """Raised when a physical packet operation violates the control plane."""


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def validate_packet_id(packet_id: str) -> None:
    if not PACKET_ID_RE.match(packet_id):
        raise PacketRuntimeError(f"invalid packet_id: {packet_id!r}")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def stable_json_hash(payload: dict[str, Any]) -> str:
    return sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def envelope_hash(envelope: dict[str, Any]) -> str:
    stable_payload = {key: value for key, value in envelope.items() if key not in ENVELOPE_HASH_EXCLUDED_KEYS}
    return stable_json_hash(stable_payload)


def _json_write_lock_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.lock")


def _acquire_json_write_lock(path: Path) -> Path:
    lock_path = _json_write_lock_path(path)
    deadline = time.monotonic() + PACKET_RUNTIME_JSON_WRITE_LOCK_TIMEOUT_SECONDS
    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "pid": os.getpid(),
                            "target": str(path),
                            "created_at": utc_now(),
                        },
                        sort_keys=True,
                    )
                )
            return lock_path
        except FileExistsError:
            try:
                stale = (time.time() - lock_path.stat().st_mtime) > PACKET_RUNTIME_JSON_WRITE_LOCK_TIMEOUT_SECONDS
                if stale:
                    lock_path.unlink()
                    continue
            except OSError:
                pass
            if time.monotonic() >= deadline:
                raise PacketRuntimeError(f"packet runtime JSON write lock is busy: {path}")
            time.sleep(PACKET_RUNTIME_JSON_WRITE_LOCK_POLL_SECONDS)


def _release_json_write_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink()
    except FileNotFoundError:
        return
    except OSError:
        return


def _write_bytes_atomic(path: Path, payload: bytes, *, verify_json: bool = False) -> None:
    assert_runtime_gateway_write(
        path,
        GATEWAY_PACKET_RUNTIME,
        operation="write_json_atomic" if verify_json else "write_text_atomic",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = _acquire_json_write_lock(path)
    tmp_path = path.with_name(f".tmp-{path.name}-{os.getpid()}-{time.time_ns():x}")
    try:
        with tmp_path.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        if verify_json:
            decoded = json.loads(path.read_text(encoding="utf-8-sig"))
            if not isinstance(decoded, dict):
                raise PacketRuntimeError(f"expected JSON object after write: {path}")
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        _release_json_write_lock(lock_path)


def write_text_atomic(path: Path, text: str) -> None:
    _write_bytes_atomic(path, text.encode("utf-8"), verify_json=False)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    _write_bytes_atomic(path, body, verify_json=True)
