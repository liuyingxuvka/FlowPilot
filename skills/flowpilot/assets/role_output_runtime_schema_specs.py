"""Schema constants and output-type specifications for role outputs."""

from __future__ import annotations

import json
from dataclasses import dataclass
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
PROMPT_MANIFEST_SCHEMA = "flowpilot.prompt_manifest.v1"
CONTROLLER_BOUNDARY_CONFIRMATION_SCHEMA = "flowpilot.controller_boundary_confirmation.v1"
CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE = "controller_boundary_confirmation"
CONTROLLER_BOUNDARY_CONFIRMATION_CONTRACT_ID = "flowpilot.output_contract.controller_boundary_confirmation.v1"
CONTROLLER_BOUNDARY_CONFIRMATION_EVENT = "controller_role_confirmed_from_router_core"
CONTRACT_REGISTRY_PATH = Path("skills/flowpilot/assets/runtime_kit/contracts/contract_index.json")
QUALITY_PACK_CATALOG_PATH = Path("skills/flowpilot/assets/runtime_kit/quality_pack_catalog.json")
ATTACHED_QUALITY_PACK_REL_PATHS = (
    Path("quality/attached_quality_packs.json"),
    Path("quality_packs.json"),
    Path("route_quality_packs.json"),
)
QUALITY_PACK_STATUS_VALUES = ("satisfied", "blocked", "waived", "not_applicable")

ROLE_KEYS = {
    "controller",
    "project_manager",
    "human_like_reviewer",
    "flowguard_operator",
    "worker",
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


_BUILTIN_OUTPUT_TYPE_SPECS: dict[str, OutputTypeSpec] = {
    "pm_resume_decision": OutputTypeSpec(
        output_type="pm_resume_decision",
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
        allowed_roles=("project_manager", "human_like_reviewer", "flowguard_operator"),
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
            "pm_visible_summary",
            "findings",
            "blockers",
            "pm_suggestion_items",
        ),
    ),
    "flowguard_operator_model_report": OutputTypeSpec(
        output_type="flowguard_operator_model_report",
        contract_id="flowpilot.output_contract.flowguard_operator_model_report.v1",
        allowed_roles=("flowguard_operator",),
        path_key="report_path",
        hash_key="report_hash",
        default_subdir="flowguard_operator_reports",
        default_filename_prefix="flowguard_operator_model_report",
        body_schema_version="flowpilot.flowguard_operator_model_report.v1",
        explicit_array_fields=(
            "pm_visible_summary",
            "blockers",
            "pm_suggestion_items",
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
            "pm_visible_summary",
            "checked_source_paths",
            "runtime_open_receipt_refs",
            "findings",
            "blockers",
            "pm_suggestion_items",
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
            "final_artifact_refs",
            "acceptance_item_closure",
            "route_segment_replay",
            "waiver_records",
            "final_blockers",
        ),
    ),
}


def _default_contract_registry_path() -> Path:
    return Path(__file__).resolve().parent / "runtime_kit" / "contracts" / "contract_index.json"


def _registry_text(item: dict[str, Any], key: str, *, contract_id: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RoleOutputRuntimeError(f"{contract_id} runtime binding is missing {key}")
    return value.strip()


def _registry_text_list(item: dict[str, Any], key: str) -> tuple[str, ...]:
    value = item.get(key)
    if not isinstance(value, list):
        return ()
    return tuple(str(part).strip() for part in value if str(part).strip())


def _registry_event_name(item: dict[str, Any], *, contract_id: str) -> str | None:
    mode = item.get("router_event_mode")
    if mode == "fixed":
        return _registry_text(item, "router_event", contract_id=contract_id)
    if mode == "router_supplied":
        return None
    raise RoleOutputRuntimeError(f"{contract_id} runtime binding has unsupported router_event_mode: {mode!r}")


def _spec_from_registry_contract(item: dict[str, Any], *, output_type: str) -> OutputTypeSpec:
    contract_id = _registry_text(item, "contract_id", contract_id="<unknown>")
    allowed_roles = _registry_text_list(item, "recipient_roles")
    if not allowed_roles:
        raise RoleOutputRuntimeError(f"{contract_id} runtime binding has no recipient_roles")
    return OutputTypeSpec(
        output_type=output_type,
        contract_id=contract_id,
        allowed_roles=allowed_roles,
        path_key=_registry_text(item, "path_key", contract_id=contract_id),
        hash_key=_registry_text(item, "hash_key", contract_id=contract_id),
        default_subdir=_registry_text(item, "default_subdir", contract_id=contract_id),
        default_filename_prefix=_registry_text(item, "default_filename_prefix", contract_id=contract_id),
        event_name=_registry_event_name(item, contract_id=contract_id),
        body_schema_version=str(item.get("body_schema_version") or "").strip() or None,
        explicit_array_fields=_registry_text_list(item, "explicit_array_fields"),
    )


def _load_registry_output_type_specs(path: Path) -> dict[str, OutputTypeSpec]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RoleOutputRuntimeError(f"output contract registry root must be an object: {path}")
    specs: dict[str, OutputTypeSpec] = {}
    contracts = payload.get("contracts")
    if not isinstance(contracts, list):
        raise RoleOutputRuntimeError(f"output contract registry contracts must be a list: {path}")
    for item in contracts:
        if not isinstance(item, dict) or item.get("runtime_channel") != "role_output_runtime":
            continue
        contract_id = _registry_text(item, "contract_id", contract_id="<unknown>")
        output_type = _registry_text(item, "output_type", contract_id=contract_id)
        specs[output_type] = _spec_from_registry_contract(item, output_type=output_type)
    return specs


def _output_type_specs() -> dict[str, OutputTypeSpec]:
    specs = dict(_BUILTIN_OUTPUT_TYPE_SPECS)
    registry_path = _default_contract_registry_path()
    if registry_path.exists():
        specs.update(_load_registry_output_type_specs(registry_path))
    return specs


def output_type_spec_source_summary(path: Path | None = None) -> dict[str, Any]:
    registry_path = path or _default_contract_registry_path()
    registry_specs = _load_registry_output_type_specs(registry_path) if registry_path.exists() else {}
    builtin_names = set(_BUILTIN_OUTPUT_TYPE_SPECS)
    registry_names = set(registry_specs)
    return {
        "registry_path": str(registry_path),
        "builtin_output_types": sorted(builtin_names),
        "registry_output_types": sorted(registry_names),
        "registry_overrides_builtin": sorted(builtin_names & registry_names),
        "builtin_only_output_types": sorted(builtin_names - registry_names),
        "registry_first": not bool(builtin_names - registry_names),
    }


OUTPUT_TYPE_SPECS: dict[str, OutputTypeSpec] = _output_type_specs()
SUPPORTED_OUTPUT_TYPES = frozenset(OUTPUT_TYPE_SPECS)


def _spec_for(output_type: str) -> OutputTypeSpec:
    try:
        return OUTPUT_TYPE_SPECS[output_type]
    except KeyError as exc:
        supported = ", ".join(sorted(SUPPORTED_OUTPUT_TYPES))
        raise RoleOutputRuntimeError(f"unsupported output_type {output_type!r}; supported: {supported}") from exc


def _role_allowed(spec: OutputTypeSpec, role: str) -> bool:
    return role in spec.allowed_roles
