"""Prepare, validate, and submit FlowPilot role-output envelopes.

This runtime is the report/decision counterpart to packet_runtime. It does not
replace packet mail: packet bodies and packet results still flow through
packet_runtime. This module handles formal role outputs such as PM decisions,
reviewer reports, officer reports, and GateDecision bodies before they are
submitted to Router as envelope-only payloads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import packet_runtime


ROLE_OUTPUT_RUNTIME_SCHEMA = "flowpilot.role_output_runtime.v1"
ROLE_OUTPUT_RUNTIME_RECEIPT_SCHEMA = "flowpilot.role_output_runtime_receipt.v1"
ROLE_OUTPUT_RUNTIME_SESSION_SCHEMA = "flowpilot.role_output_runtime_session.v1"
ROLE_OUTPUT_LEDGER_SCHEMA = "flowpilot.role_output_ledger.v1"
ROLE_OUTPUT_ENVELOPE_SCHEMA = "flowpilot.role_output_envelope.v1"
ROLE_OUTPUT_DIRECT_ROUTER_SUBMISSION_SCHEMA = "flowpilot.role_output_direct_router_submission.v1"
ROLE_OUTPUT_STATUS_SCHEMA = "flowpilot.controller_status_packet.v1"
CONTRACT_REGISTRY_PATH = Path("skills/flowpilot/assets/runtime_kit/contracts/contract_index.json")
QUALITY_PACK_CATALOG_PATH = Path("skills/flowpilot/assets/runtime_kit/quality_pack_catalog.json")
ATTACHED_QUALITY_PACK_REL_PATHS = (
    Path("quality/attached_quality_packs.json"),
    Path("quality_packs.json"),
    Path("route_quality_packs.json"),
)
QUALITY_PACK_STATUS_VALUES = ("satisfied", "blocked", "waived", "not_applicable")

ROLE_KEYS = {
    "project_manager",
    "human_like_reviewer",
    "process_flowguard_officer",
    "product_flowguard_officer",
    "worker_a",
    "worker_b",
}

FORBIDDEN_CONTROLLER_VISIBLE_BODY_FIELDS = {
    "blockers",
    "checks",
    "commands",
    "decision",
    "decision_body",
    "evidence",
    "findings",
    "passed",
    "recommendations",
    "repair_instructions",
    "report_body",
    "result_body",
}

PLACEHOLDER_PREFIXES = ("<required:", "<choose:")
PROGRESS_MESSAGE_MAX_LEN = getattr(packet_runtime, "PROGRESS_MESSAGE_MAX_LEN", 160)
PROGRESS_MESSAGE_FORBIDDEN_TERMS = getattr(
    packet_runtime,
    "PROGRESS_MESSAGE_FORBIDDEN_TERMS",
    (
        "body summary",
        "evidence",
        "finding",
        "findings",
        "recommendation",
        "recommendations",
        "result details",
        "sealed body",
    ),
)


class RoleOutputRuntimeError(ValueError):
    """Raised when a role-output runtime operation violates the contract."""


@dataclass(frozen=True)
class OutputTypeSpec:
    output_type: str
    contract_id: str
    allowed_roles: tuple[str, ...]
    path_key: str
    hash_key: str
    default_subdir: str
    default_filename_prefix: str
    event_name: str | None = None
    body_schema_version: str | None = None
    explicit_array_fields: tuple[str, ...] = ()


OUTPUT_TYPE_SPECS: dict[str, OutputTypeSpec] = {
    "pm_resume_recovery_decision": OutputTypeSpec(
        output_type="pm_resume_recovery_decision",
        contract_id="flowpilot.output_contract.pm_resume_decision.v1",
        allowed_roles=("project_manager",),
        path_key="decision_path",
        hash_key="decision_hash",
        default_subdir="continuation",
        default_filename_prefix="pm_resume_decision",
        event_name="pm_resume_recovery_decision_returned",
        body_schema_version="flowpilot.pm_resume_decision.v1",
        explicit_array_fields=(
            "prior_path_context_review.completed_nodes_considered",
            "prior_path_context_review.superseded_nodes_considered",
            "prior_path_context_review.stale_evidence_considered",
            "prior_path_context_review.prior_blocks_or_experiments_considered",
        ),
    ),
    "pm_control_blocker_repair_decision": OutputTypeSpec(
        output_type="pm_control_blocker_repair_decision",
        contract_id="flowpilot.output_contract.pm_control_blocker_repair_decision.v1",
        allowed_roles=("project_manager",),
        path_key="decision_path",
        hash_key="decision_hash",
        default_subdir="control_blocks",
        default_filename_prefix="pm_control_blocker_repair_decision",
        event_name="pm_records_control_blocker_repair_decision",
        body_schema_version="flowpilot.pm_control_blocker_repair_decision.v1",
        explicit_array_fields=(
            "blockers",
            "repair_transaction.replacement_packets",
            "prior_path_context_review.completed_nodes_considered",
            "prior_path_context_review.superseded_nodes_considered",
            "prior_path_context_review.stale_evidence_considered",
            "prior_path_context_review.prior_blocks_or_experiments_considered",
        ),
    ),
    "gate_decision": OutputTypeSpec(
        output_type="gate_decision",
        contract_id="flowpilot.output_contract.gate_decision.v1",
        allowed_roles=("project_manager", "human_like_reviewer", "process_flowguard_officer", "product_flowguard_officer"),
        path_key="decision_path",
        hash_key="decision_hash",
        default_subdir="gate_decisions",
        default_filename_prefix="gate_decision",
        event_name="role_records_gate_decision",
        explicit_array_fields=("required_evidence", "evidence_refs"),
    ),
    "reviewer_review_report": OutputTypeSpec(
        output_type="reviewer_review_report",
        contract_id="flowpilot.output_contract.reviewer_review_report.v1",
        allowed_roles=("human_like_reviewer",),
        path_key="report_path",
        hash_key="report_hash",
        default_subdir="reviews",
        default_filename_prefix="reviewer_review_report",
        body_schema_version="flowpilot.reviewer_review_report.v1",
        explicit_array_fields=(
            "direct_evidence_paths_checked",
            "findings",
            "blockers",
            "residual_risks",
            "pm_suggestion_items",
            "independent_challenge.explicit_and_implicit_commitments",
            "independent_challenge.failure_hypotheses",
            "independent_challenge.challenge_actions",
            "independent_challenge.blocking_findings",
            "independent_challenge.non_blocking_findings",
            "independent_challenge.reroute_request",
            "independent_challenge.challenge_waivers",
        ),
    ),
    "officer_model_report": OutputTypeSpec(
        output_type="officer_model_report",
        contract_id="flowpilot.output_contract.officer_model_report.v1",
        allowed_roles=("process_flowguard_officer", "product_flowguard_officer"),
        path_key="report_path",
        hash_key="report_hash",
        default_subdir="officer_reports",
        default_filename_prefix="officer_model_report",
        body_schema_version="flowpilot.officer_model_report.v1",
        explicit_array_fields=(
            "commands_run",
            "counterexamples_or_absence",
            "hard_invariants",
            "skipped_checks",
            "pm_suggestion_items",
        ),
    ),
    "startup_fact_report": OutputTypeSpec(
        output_type="startup_fact_report",
        contract_id="flowpilot.output_contract.startup_fact_report.v1",
        allowed_roles=("human_like_reviewer",),
        path_key="report_path",
        hash_key="report_hash",
        default_subdir="reviews",
        default_filename_prefix="startup_fact_report",
        body_schema_version="flowpilot.startup_fact_report.v1",
        explicit_array_fields=(
            "external_fact_review.direct_evidence_paths_checked",
            "external_fact_review.reviewer_checked_requirement_ids",
            "findings",
            "blockers",
            "residual_risks",
            "pm_suggestion_items",
            "independent_challenge.explicit_and_implicit_commitments",
            "independent_challenge.failure_hypotheses",
            "independent_challenge.challenge_actions",
            "independent_challenge.blocking_findings",
            "independent_challenge.non_blocking_findings",
            "independent_challenge.reroute_request",
            "independent_challenge.challenge_waivers",
        ),
    ),
    "material_sufficiency_report": OutputTypeSpec(
        output_type="material_sufficiency_report",
        contract_id="flowpilot.output_contract.material_sufficiency_report.v1",
        allowed_roles=("human_like_reviewer",),
        path_key="report_path",
        hash_key="report_hash",
        default_subdir="reviews",
        default_filename_prefix="material_sufficiency_report",
        body_schema_version="flowpilot.material_sufficiency_report.v1",
        explicit_array_fields=(
            "checked_source_paths",
            "findings",
            "blockers",
            "residual_risks",
            "pm_suggestion_items",
            "independent_challenge.explicit_and_implicit_commitments",
            "independent_challenge.failure_hypotheses",
            "independent_challenge.challenge_actions",
            "independent_challenge.blocking_findings",
            "independent_challenge.non_blocking_findings",
            "independent_challenge.reroute_request",
            "independent_challenge.challenge_waivers",
        ),
    ),
    "terminal_backward_replay_report": OutputTypeSpec(
        output_type="terminal_backward_replay_report",
        contract_id="flowpilot.output_contract.terminal_backward_replay_report.v1",
        allowed_roles=("human_like_reviewer",),
        path_key="report_path",
        hash_key="report_hash",
        default_subdir="reviews",
        default_filename_prefix="terminal_backward_replay_report",
        body_schema_version="flowpilot.terminal_backward_replay_report.v1",
        explicit_array_fields=(
            "segment_reviews",
            "direct_evidence_paths_checked",
            "blockers",
            "residual_risks",
            "pm_suggestion_items",
            "independent_challenge.explicit_and_implicit_commitments",
            "independent_challenge.failure_hypotheses",
            "independent_challenge.challenge_actions",
            "independent_challenge.blocking_findings",
            "independent_challenge.non_blocking_findings",
            "independent_challenge.reroute_request",
            "independent_challenge.challenge_waivers",
        ),
    ),
}

SUPPORTED_OUTPUT_TYPES = frozenset(OUTPUT_TYPE_SPECS)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_bytes(_json_bytes(payload))
    tmp_path.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RoleOutputRuntimeError(f"JSON root must be an object: {path}")
    return payload


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_concrete_agent_id(agent_id: str, *, role: str) -> str:
    resolved = str(agent_id or "").strip()
    if not resolved:
        raise RoleOutputRuntimeError(f"{role} role-output runtime session requires a concrete agent_id")
    if resolved in ROLE_KEYS:
        raise RoleOutputRuntimeError("agent_id must be a concrete agent id, not a role key")
    return resolved


def _project_relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise RoleOutputRuntimeError(f"path is outside project root: {path}") from exc


def _resolve_project_path(project_root: Path, raw_path: str | Path) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else project_root.resolve() / path


def _run_paths(project_root: Path, run_id: str | None = None) -> tuple[str, Path]:
    resolved_run_id, run_root = packet_runtime.active_run_root(project_root, run_id)
    return str(resolved_run_id), run_root


def _registry_path(project_root: Path) -> Path:
    return project_root.resolve() / CONTRACT_REGISTRY_PATH


def load_contract_registry(project_root: Path) -> dict[str, Any]:
    path = _registry_path(project_root)
    if not path.exists():
        raise RoleOutputRuntimeError(f"output contract registry is missing: {_project_relative(project_root, path)}")
    return _read_json(path)


def _quality_pack_catalog_path(project_root: Path) -> Path:
    return project_root.resolve() / QUALITY_PACK_CATALOG_PATH


def load_quality_pack_catalog(project_root: Path) -> dict[str, Any]:
    path = _quality_pack_catalog_path(project_root)
    if not path.exists():
        return {"schema_version": "flowpilot.quality_pack_catalog.v1", "quality_packs": []}
    return _read_json(path)


def _catalog_quality_pack_ids(project_root: Path) -> set[str]:
    catalog = load_quality_pack_catalog(project_root)
    packs = catalog.get("quality_packs")
    if not isinstance(packs, list):
        return set()
    return {str(item.get("pack_id")) for item in packs if isinstance(item, dict) and item.get("pack_id")}


def _pack_ids_from_payload(payload: Any) -> list[str]:
    raw: Any = payload
    if isinstance(payload, dict):
        for key in ("quality_packs", "attached_quality_packs", "route_quality_packs"):
            if key in payload:
                raw = payload[key]
                break
    if not isinstance(raw, list):
        return []
    pack_ids: list[str] = []
    for item in raw:
        if isinstance(item, str):
            pack_id = item.strip()
        elif isinstance(item, dict):
            pack_id = str(item.get("pack_id") or item.get("id") or "").strip()
        else:
            pack_id = ""
        if pack_id and pack_id not in pack_ids:
            pack_ids.append(pack_id)
    return pack_ids


def quality_pack_checks_for_run(project_root: Path, run_root: Path) -> list[dict[str, Any]]:
    """Return generic quality-pack check rows required by the current run.

    The runtime treats quality packs as data. It checks that declared pack IDs
    are answered and evidence references are well-formed; it does not encode
    UI, desktop, localization, or product-quality semantics.
    """

    pack_ids: list[str] = []
    for rel_path in ATTACHED_QUALITY_PACK_REL_PATHS:
        path = run_root / rel_path
        if path.exists():
            try:
                pack_ids.extend(_pack_ids_from_payload(_read_json(path)))
            except (OSError, json.JSONDecodeError, RoleOutputRuntimeError):
                raise RoleOutputRuntimeError(f"quality pack declaration is invalid: {_project_relative(project_root, path)}")
    unique = []
    for pack_id in pack_ids:
        if pack_id not in unique:
            unique.append(pack_id)
    return [
        {
            "pack_id": pack_id,
            "status": _choose_placeholder(f"quality_pack_checks.{pack_id}.status", list(QUALITY_PACK_STATUS_VALUES)),
            "evidence_refs": [],
            "blockers": [],
            "waivers": [],
            "detail_path": None,
        }
        for pack_id in unique
    ]


def _contract_by_id(project_root: Path, contract_id: str) -> dict[str, Any]:
    registry = load_contract_registry(project_root)
    for item in registry.get("contracts", []):
        if isinstance(item, dict) and item.get("contract_id") == contract_id:
            return item
    raise RoleOutputRuntimeError(f"output contract is missing from registry: {contract_id}")


def _spec_for(output_type: str) -> OutputTypeSpec:
    try:
        return OUTPUT_TYPE_SPECS[output_type]
    except KeyError as exc:
        supported = ", ".join(sorted(SUPPORTED_OUTPUT_TYPES))
        raise RoleOutputRuntimeError(f"unsupported output_type {output_type!r}; supported: {supported}") from exc


def _role_allowed(spec: OutputTypeSpec, role: str) -> bool:
    return role in spec.allowed_roles


def _path_parts(field_path: str) -> list[str]:
    return [part for part in field_path.split(".") if part]


def _has_path(payload: dict[str, Any], field_path: str) -> bool:
    current: Any = payload
    for part in _path_parts(field_path):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True


def _get_path(payload: dict[str, Any], field_path: str, default: Any = None) -> Any:
    current: Any = payload
    for part in _path_parts(field_path):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _set_path(payload: dict[str, Any], field_path: str, value: Any) -> None:
    parts = _path_parts(field_path)
    current = payload
    for part in parts[:-1]:
        next_value = current.get(part)
        if not isinstance(next_value, dict):
            next_value = {}
            current[part] = next_value
        current = next_value
    if parts:
        current[parts[-1]] = value


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _is_placeholder(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(PLACEHOLDER_PREFIXES)


def _choose_placeholder(field_path: str, choices: list[Any]) -> str:
    return f"<choose:{field_path}:{'|'.join(str(item) for item in choices)}>"


def _required_placeholder(field_path: str) -> str:
    return f"<required:{field_path}>"


def _prior_path_context(project_root: Path, run_root: Path) -> dict[str, Any]:
    return {
        "reviewed": True,
        "source_paths": [
            _project_relative(project_root, run_root / "route_memory" / "pm_prior_path_context.json"),
            _project_relative(project_root, run_root / "route_memory" / "route_history_index.json"),
        ],
        "completed_nodes_considered": [],
        "superseded_nodes_considered": [],
        "stale_evidence_considered": [],
        "prior_blocks_or_experiments_considered": [],
        "impact_on_decision": _required_placeholder("prior_path_context_review.impact_on_decision"),
        "controller_summary_used_as_evidence": False,
    }


def _contract_self_check(explicit_arrays_required: bool) -> dict[str, Any]:
    return {
        "all_required_fields_present": False,
        "exact_field_names_used": True,
        "empty_required_arrays_explicit": not explicit_arrays_required,
        "runtime_mechanical_validation_passed": False,
        "semantic_sufficiency_reviewed_by_runtime": False,
    }


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


def _default_output_path(run_root: Path, spec: OutputTypeSpec) -> Path:
    suffix = uuid.uuid4().hex[:12]
    return run_root / spec.default_subdir / f"{spec.default_filename_prefix}-{suffix}.json"


def _role_output_sessions_dir(run_root: Path) -> Path:
    return run_root / "role_output_sessions"


def _role_output_ledger_path(run_root: Path) -> Path:
    return run_root / "role_output_ledger.json"


def _role_output_status_dir(run_root: Path) -> Path:
    return run_root / "role_output_status"


def _safe_status_part(value: str) -> str:
    cleaned: list[str] = []
    for char in str(value or "").strip():
        if char.isalnum() or char in {"-", "_", "."}:
            cleaned.append(char)
        elif cleaned and cleaned[-1] != "_":
            cleaned.append("_")
    return "".join(cleaned).strip("._-")[:96] or "unknown"


def default_role_output_status_packet_path(
    run_root: Path,
    *,
    role: str,
    output_type: str,
    event_name: str | None = None,
) -> Path:
    key = event_name or output_type
    return _role_output_status_dir(run_root) / (
        f"{_safe_status_part(role)}--{_safe_status_part(key)}--controller_status_packet.json"
    )


def _validate_progress_value(progress: int) -> int:
    if isinstance(progress, bool) or not isinstance(progress, int) or progress < 0:
        raise RoleOutputRuntimeError("progress must be a nonnegative integer")
    return progress


def _validate_progress_message(message: str) -> str:
    text = str(message or "").strip()
    if not text:
        raise RoleOutputRuntimeError("progress message must be non-empty")
    if len(text) > PROGRESS_MESSAGE_MAX_LEN:
        raise RoleOutputRuntimeError(f"progress message must be {PROGRESS_MESSAGE_MAX_LEN} characters or fewer")
    lowered = text.lower()
    for term in PROGRESS_MESSAGE_FORBIDDEN_TERMS:
        if term in lowered:
            raise RoleOutputRuntimeError("progress message must not include sealed body details")
    return text


def write_output_progress_status(
    project_root: Path,
    *,
    run_root: Path,
    output_type: str,
    role: str,
    agent_id: str,
    status: str,
    message: str,
    progress: int,
    event_name: str | None = None,
    controller_status_packet_path: str | Path | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    resolved_agent_id = _require_concrete_agent_id(agent_id, role=role)
    spec = _spec_for(output_type)
    if not _role_allowed(spec, role):
        raise RoleOutputRuntimeError(f"{output_type} progress may be updated only by {', '.join(spec.allowed_roles)}")
    status_path = (
        _resolve_project_path(project_root, controller_status_packet_path)
        if controller_status_packet_path
        else default_role_output_status_packet_path(
            run_root,
            role=role,
            output_type=spec.output_type,
            event_name=event_name or spec.event_name,
        )
    )
    payload = {
        "schema_version": ROLE_OUTPUT_STATUS_SCHEMA,
        "runtime_entrypoint": "role_output_runtime.progress",
        "run_id": run_root.name,
        "holder": role,
        "status": status,
        "message": _validate_progress_message(message),
        "progress": _validate_progress_value(progress),
        "progress_written_by_runtime": True,
        "progress_updated_by_role": role,
        "progress_updated_by_agent_id": resolved_agent_id,
        "output_type": spec.output_type,
        "output_contract_id": spec.contract_id,
        "event_name": event_name or spec.event_name,
        "updated_at": utc_now(),
        "controller_visibility": "role_output_status_metadata_only",
        "controller_allowed_actions": ["read_role_output_status", "wait_for_role_output_envelope"],
        "controller_forbidden_actions": [
            "read_role_output_body",
            "read_role_output_directory",
            "infer_role_decision_from_progress",
            "approve_gate",
        ],
        "controller_may_read_body": False,
        "progress_is_decision_evidence": False,
        "body_text_persisted_in_status": False,
    }
    if session_id:
        payload["session_id"] = session_id
    _write_json(status_path, payload)
    payload["controller_status_packet_path"] = _project_relative(project_root, status_path)
    return payload


def _load_output_session(project_root: Path, session_path: str | Path) -> dict[str, Any]:
    session = _read_json(_resolve_project_path(project_root, session_path))
    if session.get("schema_version") != ROLE_OUTPUT_RUNTIME_SESSION_SCHEMA:
        raise RoleOutputRuntimeError("role output session has unsupported schema")
    return session


def update_output_progress(
    project_root: Path,
    *,
    output_type: str,
    role: str,
    agent_id: str,
    progress: int,
    message: str,
    run_id: str | None = None,
    event_name: str | None = None,
    session_path: str | Path | None = None,
    controller_status_packet_path: str | Path | None = None,
) -> dict[str, Any]:
    resolved_run_id, run_root = _run_paths(project_root, run_id)
    resolved_agent_id = _require_concrete_agent_id(agent_id, role=role)
    session_id = None
    if session_path:
        session = _load_output_session(project_root, session_path)
        if session.get("role") != role:
            raise RoleOutputRuntimeError("progress role does not match role-output session")
        if session.get("agent_id") != resolved_agent_id:
            raise RoleOutputRuntimeError("progress agent_id does not match role-output session")
        if session.get("output_type") != output_type:
            raise RoleOutputRuntimeError("progress output_type does not match role-output session")
        resolved_run_id, run_root = _run_paths(project_root, str(session.get("run_id") or resolved_run_id))
        controller_status_packet_path = (
            controller_status_packet_path or session.get("controller_status_packet_path")
        )
        event_name = event_name or session.get("event_name")
        session_id = str(session.get("session_id") or "")
    return write_output_progress_status(
        project_root,
        run_root=run_root,
        output_type=output_type,
        role=role,
        agent_id=resolved_agent_id,
        status="working",
        message=message,
        progress=progress,
        event_name=event_name,
        controller_status_packet_path=controller_status_packet_path,
        session_id=session_id,
    )


def _read_ledger(path: Path, run_id: str) -> dict[str, Any]:
    if path.exists():
        ledger = _read_json(path)
        ledger.setdefault("outputs", [])
        return ledger
    return {
        "schema_version": ROLE_OUTPUT_LEDGER_SCHEMA,
        "run_id": run_id,
        "outputs": [],
        "created_at": utc_now(),
    }


def _append_ledger(run_root: Path, run_id: str, record: dict[str, Any]) -> None:
    path = _role_output_ledger_path(run_root)
    ledger = _read_ledger(path, run_id)
    outputs = ledger.setdefault("outputs", [])
    if not isinstance(outputs, list):
        outputs = []
        ledger["outputs"] = outputs
    outputs.append(record)
    ledger["updated_at"] = utc_now()
    _write_json(path, ledger)


def _write_receipt(run_root: Path, receipt: dict[str, Any]) -> Path:
    receipt_id = str(receipt["receipt_id"])
    path = _role_output_sessions_dir(run_root) / f"{receipt_id}.json"
    _write_json(path, receipt)
    return path


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


def prepare_output_session(
    project_root: Path,
    *,
    output_type: str,
    role: str,
    agent_id: str,
    run_id: str | None = None,
    body_path: str | Path | None = None,
    event_name: str | None = None,
    controller_status_packet_path: str | Path | None = None,
) -> dict[str, Any]:
    resolved_agent_id = _require_concrete_agent_id(agent_id, role=role)
    spec = _spec_for(output_type)
    resolved_run_id, run_root = _run_paths(project_root, run_id)
    skeleton = build_output_skeleton(project_root, output_type=output_type, role=role, run_id=resolved_run_id)
    output_path = _resolve_project_path(project_root, body_path) if body_path else _default_output_path(run_root, spec)
    status_path = (
        _resolve_project_path(project_root, controller_status_packet_path)
        if controller_status_packet_path
        else default_role_output_status_packet_path(
            run_root,
            role=role,
            output_type=spec.output_type,
            event_name=event_name or spec.event_name,
        )
    )
    session = {
        "schema_version": ROLE_OUTPUT_RUNTIME_SESSION_SCHEMA,
        "runtime_entrypoint": "prepare_output_session",
        "session_id": f"role-output-prepare-{uuid.uuid4().hex}",
        "run_id": resolved_run_id,
        "role": role,
        "agent_id": resolved_agent_id,
        "output_type": spec.output_type,
        "output_contract_id": spec.contract_id,
        "suggested_body_path": _project_relative(project_root, output_path),
        "controller_status_packet_path": _project_relative(project_root, status_path),
        "path_key": spec.path_key,
        "hash_key": spec.hash_key,
        "event_name": event_name or spec.event_name,
        "controller_visibility": "session_metadata_only",
        "controller_may_read_body": False,
        "runtime_validates_mechanics_only": True,
        "created_at": utc_now(),
    }
    session_path = _role_output_sessions_dir(run_root) / f"{session['session_id']}.json"
    session["session_path"] = _project_relative(project_root, session_path)
    skeleton.setdefault("_role_output_contract", {})
    skeleton["_role_output_contract"]["progress_status"] = {
        "default_progress_required": True,
        "controller_status_packet_path": session["controller_status_packet_path"],
        "runtime_command": "flowpilot_runtime.py progress-output",
        "message_boundary": (
            "Use brief metadata only. Do not include sealed body content, findings, evidence, "
            "recommendations, decisions, or result details."
        ),
    }
    write_output_progress_status(
        project_root,
        run_root=run_root,
        output_type=spec.output_type,
        role=role,
        agent_id=resolved_agent_id,
        status="prepared",
        message=f"Role output {spec.output_type} prepared for {role}.",
        progress=0,
        event_name=event_name or spec.event_name,
        controller_status_packet_path=status_path,
        session_id=session["session_id"],
    )
    _write_json(session_path, session)
    return {
        **session,
        "body_skeleton": skeleton,
    }


def _build_envelope(
    project_root: Path,
    *,
    spec: OutputTypeSpec,
    role: str,
    output_path: Path,
    body_hash: str,
    receipt_path: Path,
    receipt_hash: str,
    agent_id: str,
    event_name: str | None,
    controller_status_packet_path: str | None = None,
) -> dict[str, Any]:
    envelope = {
        "schema_version": ROLE_OUTPUT_ENVELOPE_SCHEMA,
        "router_submission_schema": ROLE_OUTPUT_DIRECT_ROUTER_SUBMISSION_SCHEMA,
        "body_ref": {
            "path": _project_relative(project_root, output_path),
            "hash": body_hash,
            "path_key": spec.path_key,
            "hash_key": spec.hash_key,
        },
        "runtime_receipt_ref": {
            "path": _project_relative(project_root, receipt_path),
            "hash": receipt_hash,
        },
        "controller_visibility": "role_output_envelope_only",
        "chat_response_body_allowed": False,
        "delivery_mode": "direct_to_router",
        "submitted_to": "router",
        "controller_handoff_used": False,
        "controller_receives_role_output": False,
        "controller_next_step_source": "router_status_or_notice",
        "from_role": role,
        "to_role": "router",
        "output_type": spec.output_type,
        "output_contract_id": spec.contract_id,
        "role_output_runtime_validated": True,
        "runtime_validates_mechanics_only": True,
        "semantic_sufficiency_reviewed_by_runtime": False,
    }
    if event_name:
        envelope["event_name"] = event_name
    if controller_status_packet_path:
        envelope["controller_status_packet_path"] = controller_status_packet_path
    return envelope


def submit_output(
    project_root: Path,
    *,
    output_type: str,
    role: str,
    agent_id: str,
    body: dict[str, Any] | None = None,
    body_file: str | Path | None = None,
    output_path: str | Path | None = None,
    run_id: str | None = None,
    event_name: str | None = None,
    session_path: str | Path | None = None,
    controller_status_packet_path: str | Path | None = None,
) -> dict[str, Any]:
    resolved_agent_id = _require_concrete_agent_id(agent_id, role=role)
    spec = _spec_for(output_type)
    resolved_run_id, run_root = _run_paths(project_root, run_id)
    session_id = None
    if session_path:
        session = _load_output_session(project_root, session_path)
        if session.get("role") != role:
            raise RoleOutputRuntimeError("submit-output role does not match role-output session")
        if session.get("agent_id") != resolved_agent_id:
            raise RoleOutputRuntimeError("submit-output agent_id does not match role-output session")
        if session.get("output_type") != output_type:
            raise RoleOutputRuntimeError("submit-output output_type does not match role-output session")
        resolved_run_id, run_root = _run_paths(project_root, str(session.get("run_id") or resolved_run_id))
        event_name = event_name or session.get("event_name")
        controller_status_packet_path = (
            controller_status_packet_path or session.get("controller_status_packet_path")
        )
        session_id = str(session.get("session_id") or "")
    if not _role_allowed(spec, role):
        raise RoleOutputRuntimeError(f"{output_type} may be submitted only by {', '.join(spec.allowed_roles)}")
    if body_file:
        submitted_body = _read_json(_resolve_project_path(project_root, body_file))
    elif body is not None:
        submitted_body = body
    else:
        raise RoleOutputRuntimeError("submit-output requires body-json or body-file")
    skeleton = build_output_skeleton(project_root, output_type=output_type, role=role, run_id=resolved_run_id)
    merged_body = _deep_merge(skeleton, submitted_body)
    contract = _contract_by_id(project_root, spec.contract_id)
    _apply_runtime_fixed_values(
        project_root,
        merged_body,
        spec=spec,
        contract=contract,
        role=role,
        run_root=run_root,
    )
    first_validation = validate_output_body(
        project_root,
        output_type=output_type,
        role=role,
        body=merged_body,
        run_id=resolved_run_id,
    )
    _finalize_contract_self_check(merged_body, first_validation, explicit_arrays_required=bool(spec.explicit_array_fields))
    validation = validate_output_body(
        project_root,
        output_type=output_type,
        role=role,
        body=merged_body,
        run_id=resolved_run_id,
    )
    if not validation["ok"]:
        raise RoleOutputRuntimeError(f"role output validation failed: {validation['issues'][0]}")
    resolved_output_path = _resolve_project_path(project_root, output_path) if output_path else _default_output_path(run_root, spec)
    status_path = (
        _resolve_project_path(project_root, controller_status_packet_path)
        if controller_status_packet_path
        else default_role_output_status_packet_path(
            run_root,
            role=role,
            output_type=spec.output_type,
            event_name=event_name or spec.event_name,
        )
    )
    _write_json(resolved_output_path, merged_body)
    body_hash = _sha256_file(resolved_output_path)
    receipt_id = f"role-output-receipt-{uuid.uuid4().hex}"
    receipt = {
        "schema_version": ROLE_OUTPUT_RUNTIME_RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "runtime_schema_version": ROLE_OUTPUT_RUNTIME_SCHEMA,
        "runtime_entrypoint": "submit_output",
        "run_id": resolved_run_id,
        "role": role,
        "agent_id": resolved_agent_id,
        "output_type": spec.output_type,
        "output_contract_id": spec.contract_id,
        "body_path": _project_relative(project_root, resolved_output_path),
        "body_hash": body_hash,
        "path_key": spec.path_key,
        "hash_key": spec.hash_key,
        "validation_status": "passed",
        "validation_issue_count": 0,
        "controller_visibility": "receipt_metadata_only",
        "controller_may_read_body": False,
        "body_text_persisted_in_receipt": False,
        "runtime_validates_mechanics_only": True,
        "semantic_sufficiency_reviewed_by_runtime": False,
        "created_at": utc_now(),
    }
    receipt_path = _write_receipt(run_root, receipt)
    receipt_hash = _sha256_file(receipt_path)
    envelope = _build_envelope(
        project_root,
        spec=spec,
        role=role,
        output_path=resolved_output_path,
        body_hash=body_hash,
        receipt_path=receipt_path,
        receipt_hash=receipt_hash,
        agent_id=resolved_agent_id,
        event_name=event_name or spec.event_name,
        controller_status_packet_path=_project_relative(project_root, status_path),
    )
    ledger_record = {
        "output_id": receipt_id,
        "run_id": resolved_run_id,
        "role": role,
        "agent_id": resolved_agent_id,
        "output_type": spec.output_type,
        "output_contract_id": spec.contract_id,
        "body_path": _project_relative(project_root, resolved_output_path),
        "body_hash": body_hash,
        "envelope": envelope,
        "receipt_path": _project_relative(project_root, receipt_path),
        "receipt_hash": receipt_hash,
        "controller_status_packet_path": _project_relative(project_root, status_path),
        "controller_visibility": "ledger_metadata_only",
        "controller_may_read_body": False,
        "semantic_sufficiency_reviewed_by_runtime": False,
        "recorded_at": utc_now(),
    }
    _append_ledger(run_root, resolved_run_id, ledger_record)
    write_output_progress_status(
        project_root,
        run_root=run_root,
        output_type=spec.output_type,
        role=role,
        agent_id=resolved_agent_id,
        status="submitted",
        message=f"Role output {spec.output_type} submitted by {role}.",
        progress=999,
        event_name=event_name or spec.event_name,
        controller_status_packet_path=status_path,
        session_id=session_id,
    )
    return envelope


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


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare and submit FlowPilot role outputs through the runtime.")
    parser.add_argument("--root", default=".", help="Project root containing .flowpilot")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare-output", help="Generate a contract skeleton for a formal role output")
    prepare.add_argument("--output-type", required=True, choices=sorted(SUPPORTED_OUTPUT_TYPES))
    prepare.add_argument("--role", required=True)
    prepare.add_argument("--agent-id", required=True)
    prepare.add_argument("--run-id", default="")
    prepare.add_argument("--body-path", default="")
    prepare.add_argument("--event-name", default="")
    prepare.add_argument("--controller-status-packet-path", default="")

    validate = sub.add_parser("validate-output", help="Validate a role output body without writing an envelope")
    validate.add_argument("--output-type", required=True, choices=sorted(SUPPORTED_OUTPUT_TYPES))
    validate.add_argument("--role", required=True)
    validate.add_argument("--body-file", required=True)
    validate.add_argument("--run-id", default="")

    submit = sub.add_parser("submit-output", help="Validate a role output body and return an envelope")
    submit.add_argument("--output-type", required=True, choices=sorted(SUPPORTED_OUTPUT_TYPES))
    submit.add_argument("--role", required=True)
    submit.add_argument("--agent-id", required=True)
    submit.add_argument("--body-json", default="")
    submit.add_argument("--body-file", default="")
    submit.add_argument("--output-path", default="")
    submit.add_argument("--run-id", default="")
    submit.add_argument("--event-name", default="")
    submit.add_argument("--session-path", default="")
    submit.add_argument("--controller-status-packet-path", default="")

    progress = sub.add_parser("progress-output", help="Update Controller-visible formal role-output progress")
    progress.add_argument("--output-type", required=True, choices=sorted(SUPPORTED_OUTPUT_TYPES))
    progress.add_argument("--role", required=True)
    progress.add_argument("--agent-id", required=True)
    progress.add_argument("--progress", required=True, type=int)
    progress.add_argument("--message", required=True)
    progress.add_argument("--run-id", default="")
    progress.add_argument("--event-name", default="")
    progress.add_argument("--session-path", default="")
    progress.add_argument("--controller-status-packet-path", default="")

    verify = sub.add_parser("verify-envelope", help="Verify a runtime-generated role-output envelope receipt")
    verify.add_argument("--envelope-file", required=True)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = Path(args.root).resolve()
    if args.command == "prepare-output":
        result = prepare_output_session(
            root,
            output_type=args.output_type,
            role=args.role,
            agent_id=args.agent_id,
            run_id=args.run_id or None,
            body_path=args.body_path or None,
            event_name=args.event_name or None,
            controller_status_packet_path=args.controller_status_packet_path or None,
        )
    elif args.command == "validate-output":
        body = _read_json(_resolve_project_path(root, args.body_file))
        skeleton = build_output_skeleton(root, output_type=args.output_type, role=args.role, run_id=args.run_id or None)
        merged = _deep_merge(skeleton, body)
        spec = _spec_for(args.output_type)
        contract = _contract_by_id(root, spec.contract_id)
        _apply_runtime_fixed_values(
            root,
            merged,
            spec=spec,
            contract=contract,
            role=args.role,
            run_root=_run_paths(root, args.run_id or None)[1],
        )
        result = validate_output_body(
            root,
            output_type=args.output_type,
            role=args.role,
            body=merged,
            run_id=args.run_id or None,
        )
    elif args.command == "submit-output":
        body = json.loads(args.body_json) if args.body_json else None
        result = submit_output(
            root,
            output_type=args.output_type,
            role=args.role,
            agent_id=args.agent_id,
            body=body,
            body_file=args.body_file or None,
            output_path=args.output_path or None,
            run_id=args.run_id or None,
            event_name=args.event_name or None,
            session_path=args.session_path or None,
            controller_status_packet_path=args.controller_status_packet_path or None,
        )
    elif args.command == "progress-output":
        result = update_output_progress(
            root,
            output_type=args.output_type,
            role=args.role,
            agent_id=args.agent_id,
            progress=args.progress,
            message=args.message,
            run_id=args.run_id or None,
            event_name=args.event_name or None,
            session_path=args.session_path or None,
            controller_status_packet_path=args.controller_status_packet_path or None,
        )
    elif args.command == "verify-envelope":
        envelope = _read_json(_resolve_project_path(root, args.envelope_file))
        result = validate_envelope_runtime_receipt(root, envelope) or {"ok": True, "runtime_receipt": "absent"}
    else:  # pragma: no cover - argparse enforces command choices
        raise RoleOutputRuntimeError(f"unknown command: {args.command}")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
