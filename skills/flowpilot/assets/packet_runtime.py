"""Create and validate physical FlowPilot packet envelope/body handoffs."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import re


PACKET_ENVELOPE_SCHEMA = "flowpilot.packet_envelope.v1"
RESULT_ENVELOPE_SCHEMA = "flowpilot.result_envelope.v1"
CONTROLLER_HANDOFF_SCHEMA = "flowpilot.controller_handoff.v1"
PACKET_LEDGER_SCHEMA = "flowpilot.packet_ledger.v2"
PACKET_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

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


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise PacketRuntimeError(f"JSON root must be an object: {path}")
    return payload


def project_relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise PacketRuntimeError(f"path is outside project root: {path}") from exc


def resolve_project_path(project_root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else project_root.resolve() / path


def read_json_if_exists(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    return payload if isinstance(payload, dict) else {}


def active_run_root(project_root: Path, run_id: str | None = None) -> tuple[str, Path]:
    root = project_root.resolve()
    if run_id:
        return run_id, root / ".flowpilot" / "runs" / run_id
    flowpilot_root = root / ".flowpilot"
    current = read_json_if_exists(flowpilot_root / "current.json")
    resolved_run_id = current.get("current_run_id") or current.get("active_run_id") or current.get("run_id")
    raw_run_root = current.get("current_run_root") or current.get("active_run_root") or current.get("run_root")
    if raw_run_root:
        run_root = Path(str(raw_run_root))
        if not run_root.is_absolute():
            run_root = root / run_root
        return str(resolved_run_id or run_root.name), run_root
    if resolved_run_id:
        return str(resolved_run_id), flowpilot_root / "runs" / str(resolved_run_id)
    return "legacy", flowpilot_root


def packet_paths(project_root: Path, packet_id: str, run_id: str | None = None) -> dict[str, Any]:
    validate_packet_id(packet_id)
    resolved_run_id, run_root = active_run_root(project_root, run_id)
    packet_dir = run_root / "packets" / packet_id
    return {
        "run_id": resolved_run_id,
        "run_root": run_root,
        "packet_dir": packet_dir,
        "packet_envelope": packet_dir / "packet_envelope.json",
        "packet_body": packet_dir / "packet_body.md",
        "result_envelope": packet_dir / "result_envelope.json",
        "result_body": packet_dir / "result_body.md",
        "controller_status_packet": packet_dir / "controller_status_packet.json",
        "packet_ledger": run_root / "packet_ledger.json",
    }


def packet_paths_from_envelope(project_root: Path, envelope: dict[str, Any]) -> dict[str, Any]:
    validate_packet_id(str(envelope["packet_id"]))
    packet_body = resolve_project_path(project_root, str(envelope["body_path"]))
    packet_dir = packet_body.parent
    packets_root = packet_dir.parent
    run_root = packets_root.parent if packets_root.name == "packets" else active_run_root(project_root)[1]
    return {
        "run_id": run_root.name,
        "run_root": run_root,
        "packet_dir": packet_dir,
        "packet_envelope": packet_dir / "packet_envelope.json",
        "packet_body": packet_body,
        "result_envelope": packet_dir / "result_envelope.json",
        "result_body": packet_dir / "result_body.md",
        "controller_status_packet": packet_dir / "controller_status_packet.json",
        "packet_ledger": run_root / "packet_ledger.json",
    }


def load_envelope(project_root: Path, envelope_path: str | Path) -> dict[str, Any]:
    return read_json(resolve_project_path(project_root, str(envelope_path)))


def verify_body_hash(project_root: Path, body_path: str, expected_hash: str) -> bool:
    return sha256_file(resolve_project_path(project_root, body_path)) == expected_hash


def _empty_packet_ledger(project_root: Path, run_id: str, run_root: Path) -> dict[str, Any]:
    return {
        "schema_version": PACKET_LEDGER_SCHEMA,
        "run_id": run_id,
        "run_root": project_relative(project_root, run_root),
        "updated_at": utc_now(),
        "packet_root": project_relative(project_root, run_root / "packets"),
        "controller_boundary": {
            "controller_only": True,
            "controller_visibility": "packet_and_result_envelopes_only",
            "controller_may_read_packet_body": False,
            "controller_may_read_result_body": False,
            "controller_may_execute_worker_packet": False,
            "controller_may_advance_from_own_evidence": False,
            "controller_may_relabel_wrong_role_origin": False,
            "pm_controller_reminder_required": True,
            "reviewer_dispatch_required_before_worker": True,
            "role_reminder_required_in_controller_messages": True,
            "role_echo_required_in_subagent_responses": True,
        },
        "active_packet_id": None,
        "active_packet_status": None,
        "active_packet_holder": None,
        "packets": [],
    }


def _upsert_packet_record(project_root: Path, ledger_path: Path, run_id: str, run_root: Path, record: dict[str, Any]) -> None:
    if ledger_path.exists():
        ledger = read_json(ledger_path)
    else:
        ledger = _empty_packet_ledger(project_root, run_id, run_root)

    packets = ledger.setdefault("packets", [])
    if not isinstance(packets, list):
        raise PacketRuntimeError("packet_ledger.packets must be a list")

    existing_index = next(
        (index for index, item in enumerate(packets) if isinstance(item, dict) and item.get("packet_id") == record["packet_id"]),
        None,
    )
    if existing_index is None:
        packets.append(record)
    else:
        merged = dict(packets[existing_index])
        merged.update(record)
        if packets[existing_index].get("holder_history") and record.get("holder_history"):
            merged["holder_history"] = record["holder_history"]
        packets[existing_index] = merged

    ledger["schema_version"] = PACKET_LEDGER_SCHEMA
    ledger["run_id"] = run_id
    ledger["run_root"] = project_relative(project_root, run_root)
    ledger["packet_root"] = project_relative(project_root, run_root / "packets")
    ledger["updated_at"] = utc_now()
    ledger["active_packet_id"] = record["packet_id"]
    ledger["active_packet_status"] = record.get("active_packet_status") or ledger.get("active_packet_status")
    ledger["active_packet_holder"] = record.get("active_packet_holder") or ledger.get("active_packet_holder")
    write_json_atomic(ledger_path, ledger)


def write_controller_status_packet(
    project_root: Path,
    envelope: dict[str, Any],
    *,
    holder: str,
    status: str,
    message: str,
    user_status_update_written: bool = True,
) -> dict[str, Any]:
    status_path = resolve_project_path(project_root, envelope["controller_status_packet_path"])
    payload = {
        "schema_version": "flowpilot.controller_status_packet.v1",
        "packet_id": envelope["packet_id"],
        "node_id": envelope["node_id"],
        "holder": holder,
        "status": status,
        "message": message,
        "updated_at": utc_now(),
        "user_status_update_written": user_status_update_written,
        "next_expected_event": "role_return_envelope",
        "controller_allowed_actions": DEFAULT_CONTROLLER_ALLOWED_ACTIONS,
        "controller_forbidden_actions": DEFAULT_CONTROLLER_FORBIDDEN_ACTIONS,
        "controller_visibility": "packet_and_result_envelopes_only",
    }
    write_json_atomic(status_path, payload)
    return payload


def create_packet(
    project_root: Path,
    *,
    packet_id: str,
    from_role: str,
    to_role: str,
    node_id: str,
    body_text: str,
    run_id: str | None = None,
    is_current_node: bool = True,
    return_to: str = "controller",
    next_holder: str | None = None,
    controller_allowed_actions: list[str] | None = None,
    controller_forbidden_actions: list[str] | None = None,
) -> dict[str, Any]:
    paths = packet_paths(project_root, packet_id, run_id)
    resolved_run_id = str(paths["run_id"])
    run_root = paths["run_root"]
    packet_body_path = paths["packet_body"]
    packet_envelope_path = paths["packet_envelope"]
    controller_status_path = paths["controller_status_packet"]
    write_text_atomic(packet_body_path, body_text)
    body_hash = sha256_file(packet_body_path)

    envelope = {
        "schema_version": PACKET_ENVELOPE_SCHEMA,
        "packet_id": packet_id,
        "from_role": from_role,
        "to_role": to_role,
        "node_id": node_id,
        "is_current_node": is_current_node,
        "body_path": project_relative(project_root, packet_body_path),
        "body_hash": body_hash,
        "body_hash_algorithm": "sha256",
        "return_to": return_to,
        "next_holder": next_holder or to_role,
        "controller_allowed_actions": controller_allowed_actions or DEFAULT_CONTROLLER_ALLOWED_ACTIONS,
        "controller_forbidden_actions": controller_forbidden_actions or DEFAULT_CONTROLLER_FORBIDDEN_ACTIONS,
        "controller_status_packet_path": project_relative(project_root, controller_status_path),
        "body_access": {
            "controller_can_read_body": False,
            "controller_can_execute_body": False,
            "target_role_can_read_body": True,
            "body_hash_required": True,
            "body_hash_mismatch_blocks_dispatch": True,
        },
        "created_at": utc_now(),
    }
    write_json_atomic(packet_envelope_path, envelope)

    write_controller_status_packet(
        project_root,
        envelope,
        holder="controller",
        status="envelope-created",
        message=f"Packet {packet_id} envelope is ready for relay to {to_role}.",
    )
    record = {
        "packet_id": packet_id,
        "node_id": node_id,
        "created_by_role": from_role,
        "created_at": envelope["created_at"],
        "packet_envelope_path": project_relative(project_root, packet_envelope_path),
        "packet_body_path": envelope["body_path"],
        "physical_packet_files_written": True,
        "controller_context_body_exclusion_verified": True,
        "packet_body_hash": body_hash,
        "packet_body_hash_verified": False,
        "controller_packet_body_access_detected": False,
        "controller_packet_body_execution_detected": False,
        "packet_envelope": {
            "from_role": from_role,
            "to_role": to_role,
            "node_id": node_id,
            "is_current_node": is_current_node,
            "return_to": return_to,
            "next_holder": next_holder or to_role,
            "controller_allowed_actions": envelope["controller_allowed_actions"],
            "controller_forbidden_actions": envelope["controller_forbidden_actions"],
        },
        "holder_history": [
            {
                "holder": "controller",
                "status": "envelope-created",
                "changed_at": envelope["created_at"],
                "user_status_update_written": True,
                "controller_status_packet_path": envelope["controller_status_packet_path"],
            }
        ],
        "active_packet_status": "packet-with-controller",
        "active_packet_holder": "controller",
        "reviewer_dispatch_decision": "pending",
        "assigned_worker_role": to_role,
        "result_envelope_path": project_relative(project_root, paths["result_envelope"]),
        "result_body_path": project_relative(project_root, paths["result_body"]),
        "result_body_hash": None,
        "result_body_hash_verified": False,
        "role_origin_audit": {
            "required_for_every_packet": True,
            "reviewer_must_check_before_pass": True,
            "packet_envelope_checked": False,
            "packet_runtime_physical_files_checked": False,
            "controller_context_body_exclusion_checked": False,
            "packet_envelope_to_role_checked": False,
            "packet_body_hash_checked": False,
            "result_envelope_checked": False,
            "result_envelope_completed_by_role_checked": False,
            "result_envelope_completed_by_agent_id_checked": False,
            "result_body_hash_checked": False,
            "expected_executor_role": to_role,
            "actual_result_author_role": "unknown",
            "controller_origin_evidence_detected": False,
            "wrong_role_completion_detected": False,
            "wrong_role_completion_cosign_or_relabel_forbidden": True,
            "body_hash_mismatch_detected": False,
            "stale_body_reuse_detected": False,
            "invalid_role_origin_blocked": False,
            "controller_boundary_warning_issued": False,
            "pm_reissue_or_repair_required": False,
            "contaminated_evidence_disposition": "none",
        },
        "controller_origin_evidence_allowed": False,
    }
    _upsert_packet_record(project_root, paths["packet_ledger"], resolved_run_id, run_root, record)
    return envelope


def build_controller_handoff(envelope: dict[str, Any], *, envelope_path: str) -> dict[str, Any]:
    body_keys = {"body_content", "body_text", "packet_body", "result_body"}
    leaked_keys = sorted(body_keys & set(envelope))
    if leaked_keys:
        raise PacketRuntimeError(f"packet envelope contains forbidden body content keys: {leaked_keys!r}")
    return {
        "schema_version": CONTROLLER_HANDOFF_SCHEMA,
        "controller_visibility": "packet_envelope_only",
        "packet_envelope_path": envelope_path,
        "packet_id": envelope["packet_id"],
        "from_role": envelope["from_role"],
        "to_role": envelope["to_role"],
        "node_id": envelope["node_id"],
        "is_current_node": envelope["is_current_node"],
        "body_path": envelope["body_path"],
        "body_hash": envelope["body_hash"],
        "return_to": envelope["return_to"],
        "next_holder": envelope["next_holder"],
        "controller_allowed_actions": envelope["controller_allowed_actions"],
        "controller_forbidden_actions": envelope["controller_forbidden_actions"],
        "instruction": "Relay this envelope only. Do not read, summarize, execute, edit, or quote the packet body.",
    }


def controller_handoff_text(handoff: dict[str, Any]) -> str:
    return json.dumps(handoff, indent=2, sort_keys=True)


def read_packet_body_for_role(project_root: Path, envelope: dict[str, Any], *, role: str) -> str:
    if role != envelope.get("to_role"):
        raise PacketRuntimeError(f"packet body may only be read by to_role={envelope.get('to_role')!r}, not {role!r}")
    body_path = resolve_project_path(project_root, envelope["body_path"])
    if sha256_file(body_path) != envelope["body_hash"]:
        raise PacketRuntimeError("packet body hash mismatch")
    return body_path.read_text(encoding="utf-8")


def write_result(
    project_root: Path,
    *,
    packet_envelope: dict[str, Any],
    completed_by_role: str,
    completed_by_agent_id: str,
    result_body_text: str,
    next_recipient: str,
    strict_role: bool = True,
) -> dict[str, Any]:
    if strict_role and completed_by_role != packet_envelope.get("to_role"):
        raise PacketRuntimeError(
            f"completed_by_role {completed_by_role!r} does not match packet to_role {packet_envelope.get('to_role')!r}"
        )
    paths = packet_paths_from_envelope(project_root, packet_envelope)
    result_body_path = paths["result_body"]
    result_envelope_path = paths["result_envelope"]
    write_text_atomic(result_body_path, result_body_text)
    result_body_hash = sha256_file(result_body_path)
    result_envelope = {
        "schema_version": RESULT_ENVELOPE_SCHEMA,
        "packet_id": packet_envelope["packet_id"],
        "source_packet_envelope_path": project_relative(project_root, paths["packet_envelope"]),
        "completed_by_role": completed_by_role,
        "completed_by_agent_id": completed_by_agent_id,
        "expected_role_from_packet_envelope": packet_envelope["to_role"],
        "completed_role_matches_packet_to_role": completed_by_role == packet_envelope["to_role"],
        "result_body_path": project_relative(project_root, result_body_path),
        "result_body_hash": result_body_hash,
        "result_body_hash_algorithm": "sha256",
        "next_recipient": next_recipient,
        "controller_allowed_actions": RESULT_CONTROLLER_ALLOWED_ACTIONS,
        "controller_forbidden_actions": RESULT_CONTROLLER_FORBIDDEN_ACTIONS,
        "created_at": utc_now(),
        "body_access": {
            "controller_can_read_body": False,
            "reviewer_or_pm_can_read_body": True,
            "result_body_hash_required": True,
            "result_body_hash_mismatch_blocks_review_pass": True,
        },
    }
    write_json_atomic(result_envelope_path, result_envelope)

    write_controller_status_packet(
        project_root,
        packet_envelope,
        holder="controller",
        status="result-envelope-returned",
        message=f"Packet {packet_envelope['packet_id']} result envelope is ready for relay to {next_recipient}.",
    )

    record = {
        "packet_id": packet_envelope["packet_id"],
        "active_packet_status": "worker-result-needs-review",
        "active_packet_holder": "controller",
        "result_envelope_path": project_relative(project_root, result_envelope_path),
        "result_body_path": result_envelope["result_body_path"],
        "result_body_hash": result_body_hash,
        "result_body_hash_verified": False,
        "result_envelope": {
            "completed_by_role": completed_by_role,
            "completed_by_agent_id": completed_by_agent_id,
            "expected_role_from_packet_envelope": packet_envelope["to_role"],
            "completed_role_matches_packet_to_role": completed_by_role == packet_envelope["to_role"],
            "completed_agent_id_belongs_to_role": False,
            "next_recipient": next_recipient,
        },
    }
    _upsert_packet_record(project_root, paths["packet_ledger"], str(paths["run_id"]), paths["run_root"], record)
    return result_envelope


def read_result_body_for_role(project_root: Path, result_envelope: dict[str, Any], *, role: str) -> str:
    allowed = {result_envelope.get("next_recipient"), "human_like_reviewer", "project_manager"}
    if role not in allowed:
        raise PacketRuntimeError(f"result body may only be read by {sorted(value for value in allowed if value)}, not {role!r}")
    body_path = resolve_project_path(project_root, result_envelope["result_body_path"])
    if sha256_file(body_path) != result_envelope["result_body_hash"]:
        raise PacketRuntimeError("result body hash mismatch")
    return body_path.read_text(encoding="utf-8")


def validate_for_reviewer(
    project_root: Path,
    *,
    packet_envelope: dict[str, Any],
    result_envelope: dict[str, Any],
    agent_role_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    packet_body_hash_matches = verify_body_hash(project_root, packet_envelope["body_path"], packet_envelope["body_hash"])
    result_body_hash_matches = verify_body_hash(
        project_root,
        result_envelope["result_body_path"],
        result_envelope["result_body_hash"],
    )
    expected_role = packet_envelope.get("to_role")
    completed_by_role = result_envelope.get("completed_by_role")
    completed_by_agent_id = result_envelope.get("completed_by_agent_id")
    agent_role = (agent_role_map or {}).get(str(completed_by_agent_id))
    agent_role_matches = agent_role == completed_by_role if agent_role_map is not None else completed_by_role != "controller"

    if not packet_body_hash_matches:
        blockers.append("packet_body_hash_mismatch")
    if not result_body_hash_matches:
        blockers.append("result_body_hash_mismatch")
    if completed_by_role == "controller":
        blockers.append("controller_origin_artifact")
    if completed_by_role != expected_role:
        blockers.append("result_completed_by_wrong_role")
    if not agent_role_matches:
        blockers.append("completed_agent_id_not_assigned_to_role")

    return {
        "schema_version": "flowpilot.packet_runtime_review_audit.v1",
        "packet_id": packet_envelope.get("packet_id"),
        "packet_envelope_checked": True,
        "packet_runtime_physical_files_checked": True,
        "controller_context_body_exclusion_checked": True,
        "packet_envelope_to_role_checked": True,
        "packet_body_hash_checked": True,
        "packet_body_hash_matches_envelope": packet_body_hash_matches,
        "result_envelope_checked": True,
        "result_envelope_completed_by_role_checked": True,
        "result_envelope_completed_by_agent_id_checked": True,
        "result_body_hash_checked": True,
        "result_body_hash_matches_envelope": result_body_hash_matches,
        "expected_role": expected_role,
        "completed_by_role": completed_by_role,
        "completed_by_agent_id": completed_by_agent_id,
        "completed_agent_id_belongs_to_role": agent_role_matches,
        "controller_origin_evidence_detected": completed_by_role == "controller",
        "wrong_role_completion_detected": completed_by_role != expected_role,
        "wrong_role_completion_cosign_or_relabel_forbidden": True,
        "blockers": blockers,
        "passed": not blockers,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create and validate physical FlowPilot packet envelope/body files.")
    parser.add_argument("--root", default=".", help="Project root containing .flowpilot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    issue = subparsers.add_parser("issue", help="Write packet_envelope.json and packet_body.md")
    issue.add_argument("--run-id", default="")
    issue.add_argument("--packet-id", required=True)
    issue.add_argument("--from-role", required=True)
    issue.add_argument("--to-role", required=True)
    issue.add_argument("--node-id", required=True)
    issue.add_argument("--body-text", default="")
    issue.add_argument("--body-file", default="")
    issue.add_argument("--return-to", default="controller")
    issue.add_argument("--next-holder", default="")

    handoff = subparsers.add_parser("handoff", help="Print controller-visible envelope handoff only")
    handoff.add_argument("--envelope-path", required=True)

    complete = subparsers.add_parser("complete", help="Write result_envelope.json and result_body.md")
    complete.add_argument("--envelope-path", required=True)
    complete.add_argument("--completed-by-role", required=True)
    complete.add_argument("--completed-by-agent-id", required=True)
    complete.add_argument("--result-body-text", default="")
    complete.add_argument("--result-body-file", default="")
    complete.add_argument("--next-recipient", required=True)
    complete.add_argument("--allow-wrong-role-for-audit", action="store_true")

    review = subparsers.add_parser("review", help="Validate packet/result envelope, hashes, and role origin")
    review.add_argument("--envelope-path", required=True)
    review.add_argument("--result-envelope-path", required=True)
    review.add_argument("--agent-role-map-json", default="")

    return parser.parse_args(argv)


def _read_text_arg(text_value: str, file_value: str) -> str:
    if file_value:
        return Path(file_value).read_text(encoding="utf-8")
    return text_value


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = Path(args.root).resolve()
    if args.command == "issue":
        envelope = create_packet(
            root,
            run_id=args.run_id or None,
            packet_id=args.packet_id,
            from_role=args.from_role,
            to_role=args.to_role,
            node_id=args.node_id,
            body_text=_read_text_arg(args.body_text, args.body_file),
            return_to=args.return_to,
            next_holder=args.next_holder or None,
        )
        print(json.dumps(envelope, indent=2, sort_keys=True))
        return 0
    if args.command == "handoff":
        envelope = load_envelope(root, args.envelope_path)
        handoff = build_controller_handoff(envelope, envelope_path=args.envelope_path)
        print(controller_handoff_text(handoff))
        return 0
    if args.command == "complete":
        envelope = load_envelope(root, args.envelope_path)
        result = write_result(
            root,
            packet_envelope=envelope,
            completed_by_role=args.completed_by_role,
            completed_by_agent_id=args.completed_by_agent_id,
            result_body_text=_read_text_arg(args.result_body_text, args.result_body_file),
            next_recipient=args.next_recipient,
            strict_role=not args.allow_wrong_role_for_audit,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "review":
        envelope = load_envelope(root, args.envelope_path)
        result = load_envelope(root, args.result_envelope_path)
        agent_role_map = json.loads(args.agent_role_map_json) if args.agent_role_map_json else None
        audit = validate_for_reviewer(root, packet_envelope=envelope, result_envelope=result, agent_role_map=agent_role_map)
        print(json.dumps(audit, indent=2, sort_keys=True))
        return 0 if audit["passed"] else 2
    raise PacketRuntimeError(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
