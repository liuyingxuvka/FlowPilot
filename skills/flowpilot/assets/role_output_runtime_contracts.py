"""Helper module for the role-output runtime facade."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from role_output_runtime_schema import (
    ATTACHED_QUALITY_PACK_REL_PATHS,
    PLACEHOLDER_PREFIXES,
    QUALITY_PACK_STATUS_VALUES,
    ROLE_OUTPUT_RUNTIME_SCHEMA,
    RoleOutputRuntimeError,
    OutputTypeSpec,
    _catalog_quality_pack_ids,
    _choose_placeholder,
    _contract_by_id,
    _contract_self_check,
    _deep_merge,
    _get_path,
    _has_path,
    _is_placeholder,
    _pack_ids_from_payload,
    _path_parts,
    _prior_path_context,
    _project_relative,
    _read_json,
    _required_placeholder,
    _resolve_project_path,
    _role_allowed,
    _run_paths,
    _set_path,
    _sha256_file,
    _spec_for,
    quality_pack_checks_for_run,
)

def _default_for_required_field(
    field_path: str,
    *,
    spec: OutputTypeSpec,
    contract: dict[str, Any],
    role: str,
    project_root: Path,
    run_root: Path,
) -> Any:
    if field_path in spec.explicit_array_fields:
        return []
    if field_path == "run_id":
        return run_root.name
    if field_path == "contract_self_check":
        return _contract_self_check(bool(spec.explicit_array_fields))
    if field_path == "prior_path_context_review":
        return _prior_path_context(project_root, run_root)
    if field_path == "repair_transaction":
        choices = contract.get("allowed_repair_transaction_plan_kind_values") or ["event_replay"]
        return {
            "plan_kind": _choose_placeholder("repair_transaction.plan_kind", [str(item) for item in choices]),
            "replacement_packet_specs_path": None,
            "replacement_packet_specs_hash": None,
            "replacement_packets": [],
        }
    if field_path == "controller_reminder":
        return {
            "controller_only": True,
            "controller_may_read_sealed_bodies": False,
            "controller_may_infer_from_chat_history": False,
            "controller_may_advance_or_close_route": False,
            "controller_may_create_project_evidence": False,
            "controller_may_approve_gates": False,
            "controller_may_implement": False,
        }
    if field_path == "independent_challenge":
        return {
            "scope_restatement": _required_placeholder("independent_challenge.scope_restatement"),
            "explicit_and_implicit_commitments": [],
            "failure_hypotheses": [],
            "challenge_actions": [],
            "blocking_findings": [],
            "non_blocking_findings": [],
            "pass_or_block": _required_placeholder("independent_challenge.pass_or_block"),
            "reroute_request": [],
            "challenge_waivers": [],
        }
    role_defaults = {
        "decision_owner": role,
        "decided_by_role": role,
        "declared_by_role": role,
        "approved_by_role": role,
        "reviewed_by_role": role,
        "owner_role": role,
        "reported_by_role": role,
    }
    if field_path in role_defaults:
        return role_defaults[field_path]
    allowed_decisions = contract.get("allowed_decision_values")
    if field_path == "decision" and isinstance(allowed_decisions, list):
        return _choose_placeholder(field_path, allowed_decisions)
    allowed_targets = contract.get("allowed_target_role_or_system_values")
    if field_path == "target_role_or_system" and isinstance(allowed_targets, list):
        return _choose_placeholder(field_path, allowed_targets)
    if field_path.endswith("_paths") or field_path.endswith("_refs") or field_path.endswith("_items"):
        return []
    if field_path.endswith("evidence_refs") or field_path.endswith("required_evidence"):
        return []
    if field_path.endswith("passed") or field_path.endswith("blocking"):
        return _required_placeholder(field_path)
    return _required_placeholder(field_path)


def build_output_skeleton(
    project_root: Path,
    *,
    output_type: str,
    role: str,
    run_id: str | None = None,
) -> dict[str, Any]:
    spec = _spec_for(output_type)
    if not _role_allowed(spec, role):
        raise RoleOutputRuntimeError(f"{output_type} may be submitted only by {', '.join(spec.allowed_roles)}")
    _resolved_run_id, run_root = _run_paths(project_root, run_id)
    contract = _contract_by_id(project_root, spec.contract_id)
    skeleton: dict[str, Any] = {}
    if spec.body_schema_version:
        skeleton["schema_version"] = spec.body_schema_version
    skeleton["run_id"] = run_root.name
    required_values = contract.get("required_body_values") if isinstance(contract.get("required_body_values"), dict) else {}
    for field_path, value in required_values.items():
        _set_path(skeleton, str(field_path), value)
    if contract.get("required_prior_path_context_source_paths"):
        _set_path(skeleton, "prior_path_context_review", _prior_path_context(project_root, run_root))
    for field_path in contract.get("required_body_fields", []):
        field = str(field_path)
        if not _has_path(skeleton, field):
            _set_path(
                skeleton,
                field,
                _default_for_required_field(
                    field,
                    spec=spec,
                    contract=contract,
                    role=role,
                    project_root=project_root,
                    run_root=run_root,
                ),
            )
    if contract.get("contract_self_check_required") and not _has_path(skeleton, "contract_self_check"):
        _set_path(skeleton, "contract_self_check", _contract_self_check(bool(spec.explicit_array_fields)))
    quality_pack_checks = quality_pack_checks_for_run(project_root, run_root)
    if quality_pack_checks and not _has_path(skeleton, "quality_pack_checks"):
        _set_path(skeleton, "quality_pack_checks", quality_pack_checks)
    if spec.output_type == "gate_decision":
        _set_path(skeleton, "owner_role", role)
    if spec.output_type == "pm_control_blocker_repair_decision" and not _has_path(skeleton, "prior_path_context_review"):
        _set_path(skeleton, "prior_path_context_review", _prior_path_context(project_root, run_root))
    skeleton.setdefault("_role_output_contract", {})
    skeleton["_role_output_contract"] = {
        "contract_id": spec.contract_id,
        "output_type": spec.output_type,
        "runtime_validates_mechanics_only": True,
        "semantic_sufficiency_owner": "assigned_role_or_downstream_gate",
        "progress_status": {
            "default_progress_required": True,
            "runtime_command": "flowpilot_runtime.py progress-output",
            "controller_visibility": "metadata_only",
            "message_boundary": (
                "Use brief status metadata only. Do not include sealed body content, findings, "
                "evidence, recommendations, decisions, or result details."
            ),
        },
    }
    return skeleton


def _apply_runtime_fixed_values(
    project_root: Path,
    body: dict[str, Any],
    *,
    spec: OutputTypeSpec,
    contract: dict[str, Any],
    role: str,
    run_root: Path,
) -> None:
    body["run_id"] = run_root.name
    if spec.body_schema_version:
        body.setdefault("schema_version", spec.body_schema_version)
    required_values = contract.get("required_body_values") if isinstance(contract.get("required_body_values"), dict) else {}
    for field_path, value in required_values.items():
        _set_path(body, str(field_path), value)
    if contract.get("required_prior_path_context_source_paths"):
        current_prior = _get_path(body, "prior_path_context_review", {})
        if not isinstance(current_prior, dict):
            current_prior = {}
        body["prior_path_context_review"] = _deep_merge(_prior_path_context(project_root, run_root), current_prior)
        _set_path(
            body,
            "prior_path_context_review.source_paths",
            _prior_path_context(project_root, run_root)["source_paths"],
        )
        _set_path(body, "prior_path_context_review.controller_summary_used_as_evidence", False)
    if spec.output_type == "gate_decision":
        _set_path(body, "gate_decision_version", "flowpilot.gate_decision.v1")
        _set_path(body, "owner_role", role)


def _field_missing(payload: dict[str, Any], field_path: str) -> bool:
    if not _has_path(payload, field_path):
        return True
    value = _get_path(payload, field_path)
    if value is None or value == "":
        return True
    if _is_placeholder(value):
        return True
    return False


def _allowed_value_issues(payload: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    checks = (
        ("decision", "allowed_decision_values"),
        ("target_role_or_system", "allowed_target_role_or_system_values"),
        ("repair_transaction.plan_kind", "allowed_repair_transaction_plan_kind_values"),
        ("gate_kind", "allowed_gate_kind_values"),
        ("owner_role", "allowed_owner_role_values"),
        ("risk_type", "allowed_risk_type_values"),
        ("gate_strength", "allowed_gate_strength_values"),
        ("next_action", "allowed_next_action_values"),
    )
    issues: list[str] = []
    for field_path, contract_key in checks:
        allowed = contract.get(contract_key)
        if not isinstance(allowed, list) or not _has_path(payload, field_path):
            continue
        value = _get_path(payload, field_path)
        if _is_placeholder(value) or value not in allowed:
            issues.append(f"{field_path} must be one of {allowed}")
    evidence_allowed = contract.get("allowed_evidence_ref_kind_values")
    evidence_refs = payload.get("evidence_refs")
    if isinstance(evidence_allowed, list) and isinstance(evidence_refs, list):
        for index, ref in enumerate(evidence_refs):
            if isinstance(ref, dict) and ref.get("kind") not in evidence_allowed:
                issues.append(f"evidence_refs[{index}].kind must be one of {evidence_allowed}")
    return issues


def _evidence_ref_issues(project_root: Path, ref: Any, field_prefix: str) -> list[str]:
    issues: list[str] = []
    if not isinstance(ref, dict):
        issues.append(f"{field_prefix} must be an object")
        return issues
    path_value = ref.get("path")
    hash_value = ref.get("hash")
    kind = ref.get("kind")
    if kind == "file" and path_value:
        evidence_path = _resolve_project_path(project_root, str(path_value))
        if not evidence_path.exists():
            issues.append(f"{field_prefix}.path does not exist")
        elif hash_value and _sha256_file(evidence_path) != str(hash_value):
            issues.append(f"{field_prefix}.hash does not match file")
    return issues


def _evidence_hash_issues(project_root: Path, payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    evidence_refs = payload.get("evidence_refs")
    if isinstance(evidence_refs, list):
        for index, ref in enumerate(evidence_refs):
            issues.extend(_evidence_ref_issues(project_root, ref, f"evidence_refs[{index}]"))
    quality_checks = payload.get("quality_pack_checks")
    if isinstance(quality_checks, list):
        for check_index, check in enumerate(quality_checks):
            if not isinstance(check, dict):
                continue
            refs = check.get("evidence_refs")
            if isinstance(refs, list):
                for ref_index, ref in enumerate(refs):
                    issues.extend(
                        _evidence_ref_issues(
                            project_root,
                            ref,
                            f"quality_pack_checks[{check_index}].evidence_refs[{ref_index}]",
                        )
                    )
    return issues


def _quality_pack_check_issues(project_root: Path, run_root: Path, payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    declared_rows = quality_pack_checks_for_run(project_root, run_root)
    declared_ids = {str(item["pack_id"]) for item in declared_rows}
    checks = payload.get("quality_pack_checks")
    if not declared_ids and checks is None:
        return issues
    if not isinstance(checks, list):
        issues.append("quality_pack_checks must be an explicit array when route quality packs are declared")
        return issues
    catalog_ids = _catalog_quality_pack_ids(project_root)
    seen: set[str] = set()
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            issues.append(f"quality_pack_checks[{index}] must be an object")
            continue
        pack_id = str(check.get("pack_id") or "").strip()
        if not pack_id:
            issues.append(f"quality_pack_checks[{index}].pack_id is required")
            continue
        if catalog_ids and pack_id not in catalog_ids:
            issues.append(f"quality_pack_checks[{index}].pack_id is not in the quality pack catalog")
        if declared_ids and pack_id not in declared_ids:
            issues.append(f"quality_pack_checks[{index}].pack_id was not declared for this run")
        if pack_id in seen:
            issues.append(f"quality_pack_checks[{index}].pack_id duplicates an earlier row")
        seen.add(pack_id)
        status = check.get("status")
        if status not in QUALITY_PACK_STATUS_VALUES:
            issues.append(f"quality_pack_checks[{index}].status must be one of {list(QUALITY_PACK_STATUS_VALUES)}")
        for array_key in ("evidence_refs", "blockers", "waivers"):
            if not isinstance(check.get(array_key), list):
                issues.append(f"quality_pack_checks[{index}].{array_key} must be an explicit array")
    missing = sorted(declared_ids - seen)
    if missing:
        issues.append(f"quality_pack_checks missing declared pack ids: {missing}")
    return issues


def validate_output_body(
    project_root: Path,
    *,
    output_type: str,
    role: str,
    body: dict[str, Any],
    run_id: str | None = None,
) -> dict[str, Any]:
    spec = _spec_for(output_type)
    _resolved_run_id, run_root = _run_paths(project_root, run_id)
    contract = _contract_by_id(project_root, spec.contract_id)
    issues: list[dict[str, str]] = []
    if not _role_allowed(spec, role):
        issues.append({"field": "role", "message": f"{role} may not submit {output_type}"})
    for field_path in contract.get("required_body_fields", []):
        field = str(field_path)
        if _field_missing(body, field):
            issues.append({"field": field, "message": "missing required field"})
    if contract.get("contract_self_check_required") and _field_missing(body, "contract_self_check"):
        issues.append({"field": "contract_self_check", "message": "missing required contract self-check"})
    for field in spec.explicit_array_fields:
        if not _has_path(body, field):
            issues.append({"field": field, "message": "explicit array field is missing"})
            continue
        value = _get_path(body, field)
        if not isinstance(value, list):
            issues.append({"field": field, "message": "must be an explicit array"})
    required_values = contract.get("required_body_values") if isinstance(contract.get("required_body_values"), dict) else {}
    for field_path, expected in required_values.items():
        actual = _get_path(body, str(field_path))
        if actual != expected:
            issues.append({"field": str(field_path), "message": f"must equal {expected!r}"})
    expected_prior_paths = contract.get("required_prior_path_context_source_paths")
    if isinstance(expected_prior_paths, list):
        expected = _prior_path_context(project_root, run_root)["source_paths"]
        actual = _get_path(body, "prior_path_context_review.source_paths")
        if actual != expected:
            issues.append({"field": "prior_path_context_review.source_paths", "message": "must cite current-run route memory source paths"})
    for message in _allowed_value_issues(body, contract):
        field = message.split(" ", 1)[0]
        issues.append({"field": field, "message": message})
    for message in _evidence_hash_issues(project_root, body):
        field = message.split(" ", 1)[0]
        issues.append({"field": field, "message": message})
    for message in _quality_pack_check_issues(project_root, run_root, body):
        field = message.split(" ", 1)[0]
        issues.append({"field": field, "message": message})
    return {
        "ok": not issues,
        "schema_version": ROLE_OUTPUT_RUNTIME_SCHEMA,
        "output_type": spec.output_type,
        "output_contract_id": spec.contract_id,
        "role": role,
        "issue_count": len(issues),
        "issues": issues,
        "semantic_sufficiency_reviewed_by_runtime": False,
    }


def _finalize_contract_self_check(body: dict[str, Any], validation: dict[str, Any], *, explicit_arrays_required: bool) -> None:
    current = body.get("contract_self_check")
    if not isinstance(current, dict):
        current = {}
    current["all_required_fields_present"] = bool(validation["ok"])
    current["exact_field_names_used"] = bool(validation["ok"])
    current["empty_required_arrays_explicit"] = bool(validation["ok"] or not explicit_arrays_required)
    current["runtime_mechanical_validation_passed"] = bool(validation["ok"])
    current["semantic_sufficiency_reviewed_by_runtime"] = False
    body["contract_self_check"] = current
