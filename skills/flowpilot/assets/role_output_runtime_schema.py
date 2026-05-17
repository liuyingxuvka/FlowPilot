"""Helper module for the role-output runtime facade."""

from __future__ import annotations

import hashlib
import json
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


_BUILTIN_OUTPUT_TYPE_SPECS: dict[str, OutputTypeSpec] = {
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
        for alias in _registry_text_list(item, "output_type_aliases"):
            specs[alias] = _spec_from_registry_contract(item, output_type=alias)
    return specs


def _output_type_specs() -> dict[str, OutputTypeSpec]:
    specs = dict(_BUILTIN_OUTPUT_TYPE_SPECS)
    registry_path = _default_contract_registry_path()
    if registry_path.exists():
        specs.update(_load_registry_output_type_specs(registry_path))
    return specs


OUTPUT_TYPE_SPECS: dict[str, OutputTypeSpec] = _output_type_specs()
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
        fallback = _default_contract_registry_path()
        if fallback.exists():
            return _read_json(fallback)
        raise RoleOutputRuntimeError(f"output contract registry is missing: {_project_relative(project_root, path)}")
    return _read_json(path)


def _runtime_kit_source(project_root: Path) -> Path:
    project_runtime_kit = project_root.resolve() / "skills" / "flowpilot" / "assets" / "runtime_kit"
    if project_runtime_kit.exists():
        return project_runtime_kit
    return Path(__file__).resolve().parent / "runtime_kit"


def _json_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_json_bytes(payload)).hexdigest()


def _run_manifest_path(project_root: Path, run_root: Path) -> Path:
    manifest_path = run_root / "runtime_kit" / "manifest.json"
    if manifest_path.exists():
        return manifest_path
    return _runtime_kit_source(project_root) / "manifest.json"


def _manifest_card(manifest: dict[str, Any], card_id: str) -> dict[str, Any]:
    cards = manifest.get("cards")
    if not isinstance(cards, list):
        raise RoleOutputRuntimeError("prompt manifest cards must be a list")
    for card in cards:
        if isinstance(card, dict) and card.get("id") == card_id:
            return card
    raise RoleOutputRuntimeError(f"card not found in prompt manifest: {card_id}")


def controller_boundary_constraints() -> dict[str, Any]:
    return {
        "relay_and_record_only": True,
        "next_step_source": "flowpilot_router.py",
        "controller_may_create_project_evidence": False,
        "controller_may_read_sealed_bodies": False,
        "controller_may_implement": False,
        "controller_may_approve_gate": False,
        "controller_may_mutate_route": False,
        "controller_may_close_node": False,
    }


def _controller_boundary_sources(project_root: Path, run_root: Path) -> dict[str, Any]:
    manifest_path = _run_manifest_path(project_root, run_root)
    manifest = _read_json(manifest_path)
    if manifest.get("schema_version") != PROMPT_MANIFEST_SCHEMA:
        raise RoleOutputRuntimeError("invalid prompt manifest schema")
    controller_core = _manifest_card(manifest, "controller.core")
    card_path = manifest_path.parent / str(controller_core["path"])
    if not card_path.exists():
        raise RoleOutputRuntimeError("controller.core card path is missing")
    policy = manifest.get("controller_policy")
    if not isinstance(policy, dict):
        raise RoleOutputRuntimeError("prompt manifest controller_policy must be an object")
    return {
        "manifest": manifest,
        "manifest_path": manifest_path,
        "manifest_hash": _sha256_file(manifest_path),
        "controller_core_card": controller_core,
        "controller_core_path": card_path,
        "controller_core_hash": _sha256_file(card_path),
        "controller_policy": policy,
        "controller_policy_hash": _json_sha256(policy),
    }


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


def _contract_router_event_mode(project_root: Path, contract_id: str) -> str:
    contract = _contract_by_id(project_root, contract_id)
    mode = str(contract.get("router_event_mode") or "").strip()
    if mode not in {"fixed", "router_supplied"}:
        raise RoleOutputRuntimeError(f"{contract_id} has unsupported router_event_mode: {mode!r}")
    return mode


def _current_allowed_external_events(run_root: Path) -> tuple[str, ...]:
    state_path = run_root / "state.json"
    if not state_path.exists():
        state_path = run_root / "router_state.json"
    if not state_path.exists():
        return ()
    state = _read_json(state_path)
    pending = state.get("pending_action")
    if not isinstance(pending, dict):
        return ()
    raw_events = pending.get("allowed_external_events")
    if not isinstance(raw_events, list):
        return ()
    events: list[str] = []
    for event in raw_events:
        name = str(event or "").strip()
        if name and name not in events:
            events.append(name)
    return tuple(events)


def validate_direct_router_submission_authority(
    project_root: Path,
    *,
    output_type: str,
    role: str,
    agent_id: str,
    run_id: str | None = None,
    event_name: str | None = None,
    session_path: str | Path | None = None,
) -> dict[str, Any]:
    """Validate that a direct role-output Router submission has live authority."""

    resolved_agent_id = _require_concrete_agent_id(agent_id, role=role)
    spec = _spec_for(output_type)
    resolved_run_id, run_root = _run_paths(project_root, run_id)
    resolved_event = str(event_name or "").strip() or None
    session_id = None
    if session_path:
        session = _load_output_session(project_root, session_path)
        if session.get("role") != role:
            raise RoleOutputRuntimeError("direct Router submission role does not match role-output session")
        if session.get("agent_id") != resolved_agent_id:
            raise RoleOutputRuntimeError("direct Router submission agent_id does not match role-output session")
        if session.get("output_type") != output_type:
            raise RoleOutputRuntimeError("direct Router submission output_type does not match role-output session")
        resolved_run_id, run_root = _run_paths(project_root, str(session.get("run_id") or resolved_run_id))
        resolved_event = resolved_event or str(session.get("event_name") or "").strip() or None
        session_id = str(session.get("session_id") or "")
    if not _role_allowed(spec, role):
        raise RoleOutputRuntimeError(f"{output_type} may be submitted only by {', '.join(spec.allowed_roles)}")

    mode = _contract_router_event_mode(project_root, spec.contract_id)
    resolved_event = resolved_event or spec.event_name
    if mode == "fixed":
        if not resolved_event:
            raise RoleOutputRuntimeError("fixed-event role output has no router event")
        if spec.event_name and resolved_event != spec.event_name:
            raise RoleOutputRuntimeError("direct Router submission event_name does not match fixed contract event")
        return {
            "ok": True,
            "authority_source": "fixed_contract_event",
            "run_id": resolved_run_id,
            "event_name": resolved_event,
            "output_type": spec.output_type,
            "output_contract_id": spec.contract_id,
            "session_id": session_id,
        }

    if not resolved_event:
        raise RoleOutputRuntimeError(
            "router_supplied role output requires a Router-supplied event from the current wait; "
            "PM packet and active-holder work must return through packet runtime"
        )
    allowed_events = _current_allowed_external_events(run_root)
    if resolved_event not in allowed_events:
        raise RoleOutputRuntimeError(
            "router_supplied role output event_name is not currently allowed by Router wait state"
        )
    return {
        "ok": True,
        "authority_source": "current_router_wait",
        "run_id": resolved_run_id,
        "event_name": resolved_event,
        "output_type": spec.output_type,
        "output_contract_id": spec.contract_id,
        "allowed_external_events": list(allowed_events),
        "session_id": session_id,
    }


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
