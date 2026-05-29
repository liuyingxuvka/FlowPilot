"""Receipt validation and lookup helpers for role-output envelopes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from role_output_runtime_progress import _role_output_ledger_path
from role_output_runtime_schema import (
    FORBIDDEN_CONTROLLER_VISIBLE_BODY_FIELDS,
    ROLE_OUTPUT_RUNTIME_RECEIPT_SCHEMA,
    RoleOutputRuntimeError,
    OutputTypeSpec,
    _read_json,
    _resolve_project_path,
    _role_allowed,
    _run_paths,
    _sha256_file,
    _spec_for,
    _project_relative,
)


def _ref_pair(payload: dict[str, Any], ref_key: str) -> tuple[str | None, str | None]:
    ref = payload.get(ref_key)
    if not isinstance(ref, dict):
        return None, None
    path = ref.get("path")
    hash_value = ref.get("hash")
    return (str(path) if path else None, str(hash_value) if hash_value else None)


def _envelope_body_path_hash(envelope: dict[str, Any], spec: OutputTypeSpec) -> tuple[str | None, str | None]:
    ref_path, ref_hash = _ref_pair(envelope, "body_ref")
    return (
        ref_path or (str(envelope.get(spec.path_key)) if envelope.get(spec.path_key) else None),
        ref_hash or (str(envelope.get(spec.hash_key)) if envelope.get(spec.hash_key) else None),
    )


def _envelope_receipt_path_hash(envelope: dict[str, Any]) -> tuple[str | None, str | None]:
    ref_path, ref_hash = _ref_pair(envelope, "runtime_receipt_ref")
    return (
        ref_path or (str(envelope.get("role_output_runtime_receipt_path")) if envelope.get("role_output_runtime_receipt_path") else None),
        ref_hash or (str(envelope.get("role_output_runtime_receipt_hash")) if envelope.get("role_output_runtime_receipt_hash") else None),
    )


def validate_envelope_runtime_receipt(project_root: Path, envelope: dict[str, Any]) -> dict[str, Any] | None:
    receipt_path_value, receipt_hash_value = _envelope_receipt_path_hash(envelope)
    if not receipt_path_value and not receipt_hash_value:
        if envelope.get("role_output_runtime_validated") is True:
            raise RoleOutputRuntimeError("role output runtime envelope claims validation but has no receipt")
        return None
    if not receipt_path_value or not receipt_hash_value:
        raise RoleOutputRuntimeError("role output runtime receipt requires both path and hash")
    receipt_path = _resolve_project_path(project_root, str(receipt_path_value))
    if not receipt_path.exists():
        raise RoleOutputRuntimeError("role output runtime receipt path is missing")
    if _sha256_file(receipt_path) != str(receipt_hash_value):
        raise RoleOutputRuntimeError("role output runtime receipt hash mismatch")
    receipt = _read_json(receipt_path)
    if receipt.get("schema_version") != ROLE_OUTPUT_RUNTIME_RECEIPT_SCHEMA:
        raise RoleOutputRuntimeError("role output runtime receipt has wrong schema")
    if receipt.get("validation_status") != "passed":
        raise RoleOutputRuntimeError("role output runtime receipt did not pass validation")
    if receipt.get("semantic_sufficiency_reviewed_by_runtime") is not False:
        raise RoleOutputRuntimeError("role output runtime receipt must not claim semantic sufficiency")
    output_type = str(envelope.get("output_type") or receipt.get("output_type") or "")
    spec = _spec_for(output_type)
    if envelope.get("output_contract_id") and envelope.get("output_contract_id") != receipt.get("output_contract_id"):
        raise RoleOutputRuntimeError("role output runtime receipt contract mismatch")
    if receipt.get("output_contract_id") != spec.contract_id:
        raise RoleOutputRuntimeError("role output runtime receipt output contract mismatch")
    if envelope.get("from_role") and envelope.get("from_role") != receipt.get("role"):
        raise RoleOutputRuntimeError("role output runtime receipt role mismatch")
    if not _role_allowed(spec, str(receipt.get("role") or "")):
        raise RoleOutputRuntimeError("role output runtime receipt was recorded by an invalid role")
    body_path_value, body_hash_value = _envelope_body_path_hash(envelope, spec)
    if not body_path_value or not body_hash_value:
        raise RoleOutputRuntimeError("role output runtime envelope missing output path/hash pair")
    if body_path_value != receipt.get("body_path"):
        raise RoleOutputRuntimeError("role output runtime receipt body path mismatch")
    if body_hash_value != receipt.get("body_hash"):
        raise RoleOutputRuntimeError("role output runtime receipt body hash mismatch")
    body_path = _resolve_project_path(project_root, str(body_path_value))
    if not body_path.exists() or _sha256_file(body_path) != str(body_hash_value):
        raise RoleOutputRuntimeError("role output runtime envelope body hash is stale")
    leaked = sorted(FORBIDDEN_CONTROLLER_VISIBLE_BODY_FIELDS & set(envelope))
    if leaked:
        raise RoleOutputRuntimeError(f"role output runtime envelope leaked body fields: {', '.join(leaked)}")
    return receipt


def runtime_envelope_for_body(
    project_root: Path,
    *,
    output_type: str,
    body_path: str | Path,
    body_hash: str,
    run_id: str | None = None,
) -> dict[str, Any] | None:
    _resolved_run_id, run_root = _run_paths(project_root, run_id)
    target_path = _project_relative(project_root, _resolve_project_path(project_root, body_path))
    ledger_path = _role_output_ledger_path(run_root)
    if not ledger_path.exists():
        return None
    ledger = _read_json(ledger_path)
    outputs = ledger.get("outputs")
    if not isinstance(outputs, list):
        return None
    for record in reversed(outputs):
        if not isinstance(record, dict):
            continue
        if record.get("output_type") != output_type:
            continue
        if record.get("body_path") != target_path or record.get("body_hash") != body_hash:
            continue
        envelope = record.get("envelope")
        if not isinstance(envelope, dict):
            continue
        try:
            validate_envelope_runtime_receipt(project_root, envelope)
        except RoleOutputRuntimeError:
            continue
        return envelope
    return None
