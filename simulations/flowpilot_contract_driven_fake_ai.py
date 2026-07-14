"""Contract-driven fake AI responder for FlowPilot runtime rehearsals.

This helper is intentionally mechanical: it reads the AI-facing packet contract
that runtime projects, then builds legal, invalid, alias, and repair payloads
from that contract. Tests use it to avoid hand-writing fake AI packages that
silently encode the author's assumptions.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
CORE_ASSETS = ROOT / "skills" / "flowpilot" / "assets"
if str(CORE_ASSETS) not in sys.path:
    sys.path.insert(0, str(CORE_ASSETS))

from flowpilot_core_runtime import (  # noqa: E402
    formal_artifact_contracts,
    packet_result_contracts,
    review_window_contracts,
)


OPEN_PACKET_RESULT_SCHEMA_VERSION = "black_box_flowpilot.open_packet_result.v1"
SUBMISSION_CHECKLIST_SCHEMA_VERSION = "black_box_flowpilot.submission_checklist.v2"
CURRENT_HANDOFF_CONTRACT_SCHEMA_VERSION = "black_box_flowpilot.current_handoff_contract.v2"

_CHECKLIST_REPORT_PROJECTIONS = {
    "required_result_body_fields": "required_result_body_fields",
    "required_child_fields": "required_child_fields",
    "explicit_array_fields": "explicit_array_fields",
    "non_empty_array_fields": "non_empty_array_fields",
    "allowed_value_options": "allowed_value_options",
    "field_type_requirements": "field_type_requirements",
    "forbidden_fields": "forbidden_fields",
    "forbidden_aliases": "forbidden_aliases",
    "result_skeleton": "minimal_valid_shape",
    "branch_valid_shapes": "branch_valid_shapes",
}


MALFORMED_BODY_PROFILE_IDS = (
    "unquoted_keys",
    "markdown_wrapped_json",
    "prose_plus_json",
    "top_level_array",
    "empty_body",
    "trailing_comma",
)

RETRY_PROFILE_IDS = (
    "corrected_second_retry",
    "same_payload_retry",
    "partial_repair_then_corrected",
)

PROJECTION_GAP_PROFILE_IDS = (
    "hidden_projection_gap",
    "finite_option_mistake",
    "forbidden_alias",
    "missing_active_id_coverage",
    "partial_owner_set_missing_id",
    "extra_owner_id",
    "empty_owner_set_extra_id",
    "malformed_projection_row",
    "complete_owner_coverage",
)

REVIEW_WINDOW_FAKE_AI_PROFILE_IDS = review_window_contracts.REVIEW_WINDOW_FAKE_AI_PROFILE_IDS
CORE_DELIVERABLE_DOWNGRADE_FAKE_AI_PROFILE_IDS = (
    review_window_contracts.CORE_DELIVERABLE_DOWNGRADE_FAKE_AI_PROFILE_IDS
)

FORMAL_ARTIFACT_PROFILE_IDS = formal_artifact_contracts.FORMAL_ARTIFACT_FAULT_MODES

COMPLETE_WORKSTREAM_PROFILE_IDS = (
    "complete_workstream_pass",
    "missing_numbered_plan",
    "vague_numbered_plan",
    "incomplete_required_plan_step",
    "completion_claim_contradiction",
    "truthful_disclosed_blocker",
    "plan_evidence_mismatch",
    "stale_plan_evidence",
    "unintegrated_delegation",
    "role_local_flowguard_self_approval",
    "formal_flowguard_independence_preserved",
    "reviewer_sub9_pm_disposition_required",
    "pm_sub9_disposition_recorded",
    "corrected_workstream_retry",
    "repeated_incomplete_plan_repair",
)

RESOURCE_DISCOVERY_PROFILE_IDS = (
    "mandatory_local_skill_inventory",
    "selected_skill_deep_read",
    "ordinary_material_evidence_work",
    "optional_material_map_absent",
    "forbidden_old_discovery_fields",
)

WORKSTREAM_REVIEW_BLOCKING_PROFILE_IDS = frozenset(
    {
        "missing_numbered_plan",
        "vague_numbered_plan",
        "incomplete_required_plan_step",
        "completion_claim_contradiction",
        "truthful_disclosed_blocker",
        "plan_evidence_mismatch",
        "stale_plan_evidence",
        "unintegrated_delegation",
        "role_local_flowguard_self_approval",
        "repeated_incomplete_plan_repair",
    }
)


@dataclass(frozen=True)
class ProjectionFinding:
    code: str
    field_path: str
    message: str


def _required_mapping(parent: Mapping[str, Any], key: str, *, owner: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"{owner}.{key} must be a mapping")
    return deepcopy(dict(value))


def _required_nonempty_string(parent: Mapping[str, Any], key: str, *, owner: str) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{owner}.{key} must be a non-empty string")
    return value.strip()


def _fingerprint_payload(
    *,
    run_id: str,
    packet_id: str,
    lease_id: str,
    route_version: Any,
    source_generation: int,
    contract_family_id: str,
    required_report_contract: Mapping[str, Any],
    review_window: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "run_id": run_id,
        "packet_id": packet_id,
        "lease_id": lease_id,
        "route_version": route_version,
        "source_generation": source_generation,
        "contract_family_id": contract_family_id,
        "required_report_contract": deepcopy(dict(required_report_contract)),
        "review_window": (
            deepcopy(dict(review_window))
            if isinstance(review_window, Mapping)
            else {}
        ),
    }
    return payload


def _fingerprint_for_payload(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _validate_review_window(review_window: Mapping[str, Any]) -> dict[str, Any]:
    projected = deepcopy(dict(review_window))
    review_depth_rule = _required_nonempty_string(
        projected,
        "review_depth_rule",
        owner="current_handoff_contract.review_window",
    )
    required_rule_markers = (
        "Fixed Reviewer stage card:",
        "Stage focus:",
        "challenge",
        "core deliverable non-downgrade",
    )
    if any(marker.lower() not in review_depth_rule.lower() for marker in required_rule_markers):
        raise ValueError(
            "current_handoff_contract.review_window.review_depth_rule is incomplete or tampered"
        )
    _required_nonempty_string(
        projected,
        "review_flow_id",
        owner="current_handoff_contract.review_window",
    )
    if projected.get("review_window_coverage_status") != "declared":
        raise ValueError(
            "current_handoff_contract.review_window must have declared coverage"
        )
    return projected


def _strip_condition(field_path: str) -> str:
    return field_path.split(" when ", 1)[0]


def _path_tokens(field_path: str) -> list[str]:
    return [token for token in _strip_condition(field_path).split(".") if token]


def _is_formal_artifact_path(field_path: str) -> bool:
    return any(
        field_path.startswith(str(artifact_id))
        or field_path.startswith(f"artifact.{artifact_id}")
        for artifact_id in formal_artifact_contracts.artifact_ids()
    )


def _shape_has_path(shape: Mapping[str, Any], field_path: str) -> bool:
    current: Any = shape
    for token in _path_tokens(field_path):
        is_array = token.endswith("[]")
        key = token[:-2] if is_array else token
        if "/" in key:
            key_options = [part for part in key.split("/") if part]
            if not isinstance(current, Mapping) or not all(part in current for part in key_options):
                return False
            return True
        if not isinstance(current, Mapping) or key not in current:
            return False
        current = current[key]
        if is_array:
            if not isinstance(current, list):
                return False
            if not current:
                return True
            current = current[0]
    return True


def _contract_shape_has_path(contract: Mapping[str, Any], field_path: str) -> bool:
    minimal = contract.get("minimal_valid_shape")
    if isinstance(minimal, Mapping) and _shape_has_path(minimal, field_path):
        return True
    branch_shapes = contract.get("branch_valid_shapes")
    if isinstance(branch_shapes, Mapping):
        for shape in branch_shapes.values():
            if isinstance(shape, Mapping) and _shape_has_path(shape, field_path):
                return True
    return False


def _contract_base_shapes(contract: Mapping[str, Any]) -> list[tuple[str, Mapping[str, Any]]]:
    shapes: list[tuple[str, Mapping[str, Any]]] = []
    minimal = contract.get("minimal_valid_shape")
    if isinstance(minimal, Mapping) and minimal:
        shapes.append(("minimal_valid_shape", minimal))
    branch_shapes = contract.get("branch_valid_shapes")
    if isinstance(branch_shapes, Mapping):
        for branch_id, shape in branch_shapes.items():
            if isinstance(shape, Mapping) and shape:
                shapes.append((f"branch_valid_shapes.{branch_id}", shape))
    return shapes


def _contract_shape_for_path(contract: Mapping[str, Any], field_path: str) -> tuple[str, Mapping[str, Any]] | None:
    for shape_id, shape in _contract_base_shapes(contract):
        if _shape_has_path(shape, field_path):
            return shape_id, shape
    return None


def _set_path_value(payload: dict[str, Any], field_path: str, value: Any) -> dict[str, Any]:
    current: Any = payload
    tokens = _path_tokens(field_path)
    for index, token in enumerate(tokens):
        is_last = index == len(tokens) - 1
        is_array = token.endswith("[]")
        key = token[:-2] if is_array else token
        if is_last:
            if is_array:
                current[key] = value if isinstance(value, list) else [value]
            else:
                current[key] = value
            return payload
        if is_array:
            current.setdefault(key, [{}])
            if not isinstance(current[key], list) or not current[key]:
                current[key] = [{}]
            if not isinstance(current[key][0], dict):
                current[key][0] = {}
            current = current[key][0]
            continue
        current.setdefault(key, {})
        if not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    return payload


def _delete_path(payload: dict[str, Any], field_path: str) -> dict[str, Any]:
    current_values: list[Any] = [payload]
    tokens = _path_tokens(field_path)
    for index, token in enumerate(tokens):
        is_last = index == len(tokens) - 1
        is_array = token.endswith("[]")
        key = token[:-2] if is_array else token
        next_values: list[Any] = []
        for current in current_values:
            if not isinstance(current, dict) or key not in current:
                continue
            if is_last:
                del current[key]
                continue
            value = current[key]
            if is_array:
                if isinstance(value, list):
                    next_values.extend(item for item in value if isinstance(item, dict))
                elif isinstance(value, dict):
                    next_values.append(value)
            elif isinstance(value, dict):
                next_values.append(value)
        current_values = next_values
        if not current_values and not is_last:
            return payload
    return payload


def _get_path_values(payload: Mapping[str, Any], field_path: str) -> tuple[bool, list[Any]]:
    current_values: list[Any] = [payload]
    for token in _path_tokens(field_path):
        next_values: list[Any] = []
        is_array = token.endswith("[]")
        key = token[:-2] if is_array else token
        for current in current_values:
            if not isinstance(current, Mapping) or key not in current:
                continue
            value = current[key]
            if is_array:
                if isinstance(value, list):
                    next_values.extend(value)
                else:
                    next_values.append(value)
            else:
                next_values.append(value)
        if not next_values:
            return False, []
        current_values = next_values
    return True, current_values


def _invalid_value_for(allowed_values: list[Any]) -> Any:
    if all(isinstance(value, bool) for value in allowed_values):
        return False if False not in allowed_values else "__invalid_boolean_option__"
    if all(isinstance(value, str) for value in allowed_values):
        return "__invalid_option__"
    if all(isinstance(value, int) for value in allowed_values):
        candidate = -999999
        return candidate if candidate not in allowed_values else "__invalid_integer_option__"
    return {"invalid_option": True}


def _wrong_type_for(value: Any) -> Any:
    if isinstance(value, bool):
        return {"wrong_type": value}
    if isinstance(value, str):
        return ["wrong_type"]
    if isinstance(value, list):
        return "wrong_type"
    if isinstance(value, Mapping):
        return "wrong_type"
    if isinstance(value, int):
        return "wrong_type"
    return {"wrong_type": True}


def _value_key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _sequence_field(contract: Mapping[str, Any], *names: str) -> list[str]:
    for name in names:
        values = contract.get(name)
        if isinstance(values, (list, tuple)):
            return [str(value) for value in values]
    return []


def _flatten_shape_paths(value: Any, prefix: str = "") -> list[str]:
    paths: list[str] = []
    if prefix:
        paths.append(prefix)
    if isinstance(value, Mapping):
        keys = set(value)
        if prefix and {"parent_node_id", "child_node_ids"} <= keys:
            paths.append(f"{prefix}.parent_node_id/child_node_ids")
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            paths.extend(_flatten_shape_paths(child, child_prefix))
    elif isinstance(value, list):
        array_prefix = f"{prefix}[]" if prefix else "[]"
        paths.append(array_prefix)
        if value:
            paths.extend(_flatten_shape_paths(value[0], array_prefix))
    return list(dict.fromkeys(paths))


def _branch_shape_fields(contract: Mapping[str, Any]) -> list[str]:
    branch_shapes = contract.get("branch_valid_shapes")
    if not isinstance(branch_shapes, Mapping):
        return []
    fields: list[str] = []
    for branch_id, shape in branch_shapes.items():
        if not isinstance(shape, Mapping):
            continue
        for path in _flatten_shape_paths(shape):
            if path == "decision":
                continue
            fields.append(f"{path} when {branch_id}")
    return list(dict.fromkeys(fields))


def review_window_behavior_cells() -> list[dict[str, str]]:
    return [
        dict(cell)
        for cell in review_window_contracts.review_window_completeness_cells()
        if cell.get("required_evidence_owner") == "review_window_fake_ai_matrix"
    ]


class ContractDrivenFakeAIResponder:
    """Mechanical fake AI that derives responses from packet-local contracts."""

    def __init__(
        self,
        contract: Mapping[str, Any],
        *,
        delivered_review_window: Mapping[str, Any] | None = None,
        open_packet_identity: Mapping[str, Any] | None = None,
    ):
        self.contract = deepcopy(dict(contract))
        self.delivered_review_window = (
            deepcopy(dict(delivered_review_window))
            if isinstance(delivered_review_window, Mapping)
            else None
        )
        self.open_packet_identity = (
            deepcopy(dict(open_packet_identity))
            if isinstance(open_packet_identity, Mapping)
            else None
        )

    @classmethod
    def from_open_packet_result(
        cls,
        open_packet_result: Mapping[str, Any],
    ) -> "ContractDrivenFakeAIResponder":
        """Build from the one current public role-open result.

        Packet bodies, remembered contracts, reissue bodies, and static flow-id
        lookups are deliberately not accepted as contract authority.
        """

        if not isinstance(open_packet_result, Mapping):
            raise ValueError("open_packet_result must be a mapping")
        if open_packet_result.get("ok") is not True:
            raise ValueError("open_packet_result must be a successful current open")
        if open_packet_result.get("schema_version") != OPEN_PACKET_RESULT_SCHEMA_VERSION:
            raise ValueError(
                f"open_packet_result must use {OPEN_PACKET_RESULT_SCHEMA_VERSION}"
            )
        if open_packet_result.get("authorized_input_materials_delivered") is not True:
            raise ValueError("open_packet_result did not deliver authorized input materials")

        run_id = _required_nonempty_string(open_packet_result, "run_id", owner="open_packet_result")
        packet = _required_mapping(open_packet_result, "packet", owner="open_packet_result")
        lease = _required_mapping(open_packet_result, "lease", owner="open_packet_result")
        checklist = _required_mapping(
            open_packet_result,
            "submission_checklist",
            owner="open_packet_result",
        )
        if checklist.get("schema_version") != SUBMISSION_CHECKLIST_SCHEMA_VERSION:
            raise ValueError(
                f"submission_checklist must use {SUBMISSION_CHECKLIST_SCHEMA_VERSION}"
            )
        if checklist.get("source") != "current_handoff_contract":
            raise ValueError("submission_checklist source must be current_handoff_contract")
        if checklist.get("current_handoff_contract_inspected") is not True:
            raise ValueError("submission_checklist did not inspect current_handoff_contract")
        if checklist.get("current_packet_body_inspected") is not False:
            raise ValueError("submission_checklist must not use the packet body as contract authority")
        if lease.get("ack_received") is not True:
            raise ValueError("the current lease must be ACKed before fake AI consumes the checklist")

        packet_id = _required_nonempty_string(packet, "packet_id", owner="open_packet_result.packet")
        lease_id = _required_nonempty_string(lease, "lease_id", owner="open_packet_result.lease")
        responsibility = _required_nonempty_string(
            packet,
            "responsibility",
            owner="open_packet_result.packet",
        )
        packet_kind = _required_nonempty_string(
            packet,
            "packet_kind",
            owner="open_packet_result.packet",
        )
        lease_responsibility = _required_nonempty_string(
            lease,
            "responsibility",
            owner="open_packet_result.lease",
        )
        if lease_responsibility != responsibility:
            raise ValueError("open_packet_result packet and lease responsibilities disagree")

        handoff = _required_mapping(
            packet,
            "current_handoff_contract",
            owner="open_packet_result.packet",
        )
        if handoff.get("schema_version") != CURRENT_HANDOFF_CONTRACT_SCHEMA_VERSION:
            raise ValueError(
                f"current_handoff_contract must use {CURRENT_HANDOFF_CONTRACT_SCHEMA_VERSION}"
            )
        if handoff.get("contract_id") != CURRENT_HANDOFF_CONTRACT_SCHEMA_VERSION:
            raise ValueError("current_handoff_contract contract_id does not match its schema")
        if handoff.get("current_run_only") is not True:
            raise ValueError("current_handoff_contract must be current-run-only")
        if str(handoff.get("recipient_responsibility") or "") != responsibility:
            raise ValueError("current_handoff_contract recipient responsibility disagrees with the lease")
        if str(handoff.get("packet_kind") or "") != packet_kind:
            raise ValueError("current_handoff_contract packet_kind disagrees with the opened packet")

        handoff_packet_id = _required_nonempty_string(
            handoff,
            "packet_id",
            owner="current_handoff_contract",
        )
        checklist_run_id = _required_nonempty_string(
            checklist,
            "run_id",
            owner="submission_checklist",
        )
        checklist_packet_id = _required_nonempty_string(
            checklist,
            "packet_id",
            owner="submission_checklist",
        )
        checklist_lease_id = _required_nonempty_string(
            checklist,
            "lease_id",
            owner="submission_checklist",
        )
        if checklist_run_id != run_id:
            raise ValueError("submission_checklist run_id does not match open_packet_result")
        if packet_id != handoff_packet_id or packet_id != checklist_packet_id:
            raise ValueError("packet identity disagrees across open result, handoff, and checklist")
        if lease_id != checklist_lease_id:
            raise ValueError("lease identity disagrees across open result and checklist")

        route_version = handoff.get("route_version")
        source_generation = handoff.get("source_generation")
        if route_version in (None, ""):
            raise ValueError("current_handoff_contract.route_version is missing")
        if not isinstance(source_generation, int) or isinstance(source_generation, bool):
            raise ValueError("current_handoff_contract.source_generation must be an integer")
        if packet.get("route_version") != route_version or checklist.get("route_version") != route_version:
            raise ValueError("route_version disagrees across open result, handoff, and checklist")
        if checklist.get("source_generation") != source_generation:
            raise ValueError("source_generation disagrees across handoff and checklist")

        family_id = _required_nonempty_string(
            handoff,
            "contract_family_id",
            owner="current_handoff_contract",
        )
        if packet_result_contracts.contract_for_family(family_id) is None:
            raise ValueError(f"unknown current contract family: {family_id}")
        derived_family_id = packet_result_contracts.packet_result_family_id(
            {
                "packet_kind": packet_kind,
                "route_scope": str(handoff.get("route_scope") or ""),
            }
        )
        if derived_family_id != family_id:
            raise ValueError(
                "contract_family_id does not match the current packet kind and route scope"
            )
        if checklist.get("contract_family_id") != family_id:
            raise ValueError("contract_family_id disagrees across handoff and checklist")

        report_contract = _required_mapping(
            handoff,
            "required_report_contract",
            owner="current_handoff_contract",
        )
        for checklist_key, report_key in _CHECKLIST_REPORT_PROJECTIONS.items():
            if checklist.get(checklist_key) != report_contract.get(report_key):
                raise ValueError(
                    f"submission_checklist.{checklist_key} does not match "
                    f"current_handoff_contract.required_report_contract.{report_key}"
                )

        review_window_raw = handoff.get("review_window")
        review_window = None
        if review_window_raw is not None:
            if not isinstance(review_window_raw, Mapping):
                raise ValueError("current_handoff_contract.review_window must be a mapping")
            review_window = _validate_review_window(review_window_raw)

        fingerprint = _required_nonempty_string(
            checklist,
            "contract_fingerprint",
            owner="submission_checklist",
        )
        expected_fingerprint = _fingerprint_for_payload(
            _fingerprint_payload(
                run_id=run_id,
                packet_id=packet_id,
                lease_id=lease_id,
                route_version=route_version,
                source_generation=source_generation,
                contract_family_id=family_id,
                required_report_contract=report_contract,
                review_window=review_window,
            )
        )
        if fingerprint != expected_fingerprint:
            raise ValueError("submission_checklist contract_fingerprint is stale or tampered")

        open_receipt = _required_mapping(
            open_packet_result,
            "open_receipt",
            owner="open_packet_result",
        )
        if (
            open_receipt.get("event_type") != "sealed_packet_body_opened"
            or open_receipt.get("packet_id") != packet_id
            or open_receipt.get("lease_id") != lease_id
            or open_receipt.get("body_hash") != packet.get("body_hash")
        ):
            raise ValueError("open_packet_result open_receipt does not bind the current packet and lease")

        responder_contract = deepcopy(checklist)
        responder_contract["minimal_valid_shape"] = deepcopy(checklist["result_skeleton"])
        return cls(
            responder_contract,
            delivered_review_window=review_window,
            open_packet_identity={
                "run_id": run_id,
                "packet_id": packet_id,
                "lease_id": lease_id,
                "route_version": route_version,
                "source_generation": source_generation,
                "contract_family_id": family_id,
                "contract_fingerprint": fingerprint,
            },
        )

    @property
    def allowed_value_options(self) -> dict[str, list[Any]]:
        options = self.contract.get("allowed_value_options")
        if not isinstance(options, Mapping):
            return {}
        return {
            str(field): list(values) if isinstance(values, list) else []
            for field, values in options.items()
        }

    @property
    def field_type_requirements(self) -> dict[str, Any]:
        requirements = self.contract.get("field_type_requirements")
        if not isinstance(requirements, Mapping):
            return {}
        return {str(field): requirement for field, requirement in requirements.items()}

    @property
    def required_fields(self) -> list[str]:
        return _sequence_field(
            self.contract,
            "required_result_body_fields",
            "required_fields",
        )

    @property
    def required_child_fields(self) -> list[str]:
        return list(
            dict.fromkeys(
                (
                    *_sequence_field(self.contract, "required_child_fields"),
                    *_branch_shape_fields(self.contract),
                )
            )
        )

    @property
    def non_empty_array_fields(self) -> list[str]:
        return _sequence_field(self.contract, "non_empty_array_fields")

    @property
    def forbidden_fields(self) -> list[str]:
        return _sequence_field(self.contract, "forbidden_fields")

    @property
    def forbidden_aliases(self) -> dict[str, str]:
        aliases = self.contract.get("forbidden_aliases")
        if not isinstance(aliases, Mapping):
            return {}
        return {str(alias): str(target) for alias, target in aliases.items()}

    def projection_findings(self) -> list[ProjectionFinding]:
        findings: list[ProjectionFinding] = []
        minimal_shape = self.contract.get("minimal_valid_shape")
        if not isinstance(minimal_shape, Mapping) or not minimal_shape:
            findings.append(
                ProjectionFinding(
                    "projection_missing_minimal_valid_shape",
                    "minimal_valid_shape",
                    "AI-facing contract must expose a minimal legal payload shape.",
                )
            )
        for field_path in self.required_fields:
            if not _contract_shape_has_path(self.contract, field_path):
                findings.append(
                    ProjectionFinding(
                        "projection_missing_required_shape_path",
                        field_path,
                        "Required fields must be reachable from minimal_valid_shape or branch_valid_shapes.",
                    )
                )
        for field_path in self.required_child_fields:
            if not _contract_shape_has_path(self.contract, field_path):
                findings.append(
                    ProjectionFinding(
                        "projection_missing_required_child_shape_path",
                        field_path,
                        "Required child fields must be reachable from minimal_valid_shape or branch_valid_shapes.",
                    )
                )
        for field_path, values in self.allowed_value_options.items():
            if not values:
                findings.append(
                    ProjectionFinding(
                        "projection_missing_options",
                        field_path,
                        "Finite option fields must expose at least one selectable value.",
                    )
                )
            if _is_formal_artifact_path(field_path):
                continue
            if not _contract_shape_has_path(self.contract, field_path):
                findings.append(
                    ProjectionFinding(
                        "projection_missing_shape_path",
                        field_path,
                        "Finite option fields must be reachable from minimal_valid_shape or branch_valid_shapes.",
                    )
                )
        return findings

    def legal_payload(self) -> dict[str, Any]:
        minimal_shape = self.contract.get("minimal_valid_shape")
        if not isinstance(minimal_shape, Mapping) or not minimal_shape:
            raise ValueError("AI-facing contract is missing minimal_valid_shape")
        return deepcopy(dict(minimal_shape))

    def _require_current_open_packet_authority(self) -> str:
        if not isinstance(self.open_packet_identity, Mapping):
            raise ValueError(
                "semantic fake AI profiles require ContractDrivenFakeAIResponder.from_open_packet_result"
            )
        family_id = str(self.open_packet_identity.get("contract_family_id") or "")
        if not family_id:
            raise ValueError("semantic fake AI profile has no current contract family")
        return family_id

    @staticmethod
    def _workstream_section(payload: dict[str, Any]) -> dict[str, Any]:
        self_check = payload.setdefault("contract_self_check", {})
        if not isinstance(self_check, dict):
            raise ValueError("current legal payload contract_self_check must be an object")
        section = self_check.setdefault(
            "workstream_plan_and_completion",
            packet_result_contracts.workstream_plan_and_completion_example(),
        )
        if not isinstance(section, dict):
            raise ValueError("workstream_plan_and_completion must be an object")
        return section

    @staticmethod
    def _semantic_block_payload(payload: dict[str, Any], reason: str) -> None:
        if "passed" in payload:
            payload["passed"] = False
        if "decision" in payload:
            payload["decision"] = "block"
        blockers = payload.get("blockers")
        if isinstance(blockers, list):
            blockers.append(
                {
                    "blocker_id": "fake-workstream-semantic-blocker",
                    "blocker_class": "local_artifact",
                    "summary": reason,
                    "recommended_resolution": "Repair the named workstream-plan gap and return through the existing recheck path.",
                }
            )

    def complete_workstream_payload(self, profile_id: str) -> dict[str, Any]:
        """Return one semantic workstream profile from the current open checklist.

        The method mutates only the optional semantic self-check carried by the
        existing family payload. Runtime mechanics remain checklist-owned;
        Reviewer owns the profile oracle.
        """

        if profile_id not in COMPLETE_WORKSTREAM_PROFILE_IDS:
            raise KeyError(f"unknown complete-workstream fake AI profile: {profile_id}")
        self._require_current_open_packet_authority()
        payload = self.legal_payload()
        section = self._workstream_section(payload)
        section["semantic_profile_id"] = profile_id
        steps = section.get("steps")
        if not isinstance(steps, list) or not steps:
            raise ValueError("current result skeleton lacks semantic workstream plan steps")

        if profile_id == "missing_numbered_plan":
            payload["contract_self_check"].pop("workstream_plan_and_completion", None)
            return payload
        if profile_id == "vague_numbered_plan":
            steps[0]["plan"] = "Do the work."
            section["plan_specificity"] = "vague"
        elif profile_id == "incomplete_required_plan_step":
            steps[-1]["status"] = "pending"
            steps[-1]["unresolved"] = "Required final reconciliation was not completed."
        elif profile_id == "completion_claim_contradiction":
            steps[-1]["status"] = "pending"
            steps[-1]["unresolved"] = "Still pending despite overall pass claim."
            section["overall_completion_claim"] = "complete"
        elif profile_id == "truthful_disclosed_blocker":
            steps[-1]["status"] = "blocked"
            steps[-1]["unresolved"] = "External authority is required."
            section["remaining_blockers"] = ["authority-required"]
            self._semantic_block_payload(payload, "Role truthfully disclosed an unresolved authority blocker.")
        elif profile_id == "plan_evidence_mismatch":
            steps[1]["evidence_refs"] = ["artifact-that-does-not-contain-the-claimed-work"]
            section["evidence_consistency"] = "mismatch"
        elif profile_id == "stale_plan_evidence":
            steps[2]["evidence_refs"] = ["stale-prior-generation-verification"]
            section["evidence_freshness"] = "stale"
        elif profile_id == "unintegrated_delegation":
            section["delegation_and_integration"] = {
                "delegated": True,
                "integration_status": "not_integrated",
                "evidence_refs": ["delegated-result-unconsumed"],
            }
        elif profile_id == "role_local_flowguard_self_approval":
            section["role_local_flowguard"] = {
                "used": True,
                "approval_claim": "self_approved",
                "formal_independent_gate_preserved": False,
            }
        elif profile_id == "formal_flowguard_independence_preserved":
            section["role_local_flowguard"] = {
                "used": True,
                "approval_claim": "advisory_only",
                "formal_independent_gate_preserved": True,
            }
        elif profile_id == "reviewer_sub9_pm_disposition_required":
            section["reviewer_score_context"] = {
                "score": 8,
                "target": 9,
                "minimum_hard_gate_passed": True,
                "pm_disposition_status": "pending",
            }
        elif profile_id == "pm_sub9_disposition_recorded":
            section["reviewer_score_context"] = {
                "score": 8,
                "target": 9,
                "minimum_hard_gate_passed": True,
                "pm_disposition_status": "rejected_with_evidence_specific_reason",
                "pm_disposition_reason": "Current evidence proves the remaining improvement is optional and not worth more scope.",
            }
        elif profile_id == "corrected_workstream_retry":
            section["repair_attempt"] = 2
            section["prior_profile"] = "incomplete_required_plan_step"
            section["repair_delta"] = "Completed the missing reconciliation step and attached current evidence."
        elif profile_id == "repeated_incomplete_plan_repair":
            steps[-1]["status"] = "pending"
            steps[-1]["unresolved"] = "The same required reconciliation step remains incomplete."
            section["repair_attempt"] = 3
            section["prior_profile"] = "incomplete_required_plan_step"
            section["repair_delta"] = "No effective delta."
        return payload

    def complete_workstream_review_payload(self, profile_id: str) -> dict[str, Any]:
        """Return the existing Reviewer family payload for one plan-audit oracle."""

        if profile_id not in COMPLETE_WORKSTREAM_PROFILE_IDS:
            raise KeyError(f"unknown complete-workstream fake AI profile: {profile_id}")
        family_id = self._require_current_open_packet_authority()
        if family_id not in {
            "review.any_current_subject",
            "review.parent_backward_replay",
        }:
            raise ValueError("workstream Reviewer profiles require an opened current Reviewer packet")
        payload = self.legal_payload()
        section = self._workstream_section(payload)
        blocking = profile_id in WORKSTREAM_REVIEW_BLOCKING_PROFILE_IDS
        audit = {
            "subject_profile_id": profile_id,
            "plan_rows_compared_with_actual_artifact": True,
            "delegation_integration_checked": True,
            "evidence_freshness_checked": True,
            "verification_and_repair_checked": True,
            "decision": (
                "pass_with_pm_disposition_required"
                if profile_id == "reviewer_sub9_pm_disposition_required"
                else ("block" if blocking else "pass")
            ),
        }
        payload["contract_self_check"]["workstream_plan_audit"] = audit
        if blocking:
            payload["passed"] = False
            payload["findings"] = [f"Workstream semantic profile failed: {profile_id}."]
            payload["blockers"] = [
                {
                    "blocker_id": f"fake-workstream-{profile_id}",
                    "blocker_class": "local_artifact",
                    "summary": f"Workstream plan audit failed for {profile_id}.",
                    "recommended_resolution": "Return the current result through the existing PM repair/recheck path.",
                }
            ]
            payload["pm_suggestion_items"] = [
                f"PM decision-support: repair the current {profile_id} gap and recheck the same workstream."
            ]
        else:
            payload["passed"] = True
            payload["findings"] = []
            payload["blockers"] = []
            if profile_id == "reviewer_sub9_pm_disposition_required":
                payload["pm_visible_summary"] = [
                    "Quality score: 8/10; target: 9/10; minimum hard gate passed: true."
                ]
                payload["pm_suggestion_items"] = [
                    "PM decision-support: the hard gate passes, but PM must explicitly disposition this sub-9 gap before closure; the score alone is not a blocker."
                ]
            else:
                payload["pm_suggestion_items"] = [
                    f"PM decision-support: {profile_id} passed plan-to-artifact audit; record any sub-9 disposition before closure."
                ]
        return payload

    def resource_discovery_payload(self, profile_id: str) -> dict[str, Any]:
        """Return current resource/discovery profiles from the opened family checklist."""

        if profile_id not in RESOURCE_DISCOVERY_PROFILE_IDS:
            raise KeyError(f"unknown resource-discovery fake AI profile: {profile_id}")
        family_id = self._require_current_open_packet_authority()
        payload = self.legal_payload()
        section = self._workstream_section(payload)
        section["resource_profile_id"] = profile_id
        if profile_id == "mandatory_local_skill_inventory":
            if family_id != "task.discovery":
                raise ValueError("mandatory local skill inventory profile requires task.discovery")
            payload["candidate_skill_inventory"] = ["flowguard-development-process-flow"]
            section["runtime_inventory_reviewed"] = True
            section["inventory_depth"] = "path_and_availability_only"
        elif profile_id == "selected_skill_deep_read":
            if family_id != "task.skill_standard":
                raise ValueError("selected skill deep-read profile requires task.skill_standard")
            section["selected_skills_deep_read"] = True
            section["raw_inventory_deep_read"] = False
        elif profile_id == "ordinary_material_evidence_work":
            if family_id != "task.node":
                raise ValueError("ordinary material evidence profile requires task.node")
            section["ordinary_role_work"] = {
                "responsibility": "research_worker",
                "special_material_result_family_used": False,
                "risk_appropriate_review_required": True,
            }
        elif profile_id == "optional_material_map_absent":
            section["material_artifact_map"] = {
                "present": False,
                "navigation_only": True,
                "absence_blocks": False,
            }
        elif profile_id == "forbidden_old_discovery_fields":
            if family_id != "task.discovery":
                raise ValueError("forbidden old discovery field profile requires task.discovery")
            payload["material_sources"] = ["legacy-positive-shape"]
            payload["material_sufficiency"] = "legacy-positive-shape"
        return payload

    def legal_payload_for_path(self, field_path: str) -> dict[str, Any]:
        base = _contract_shape_for_path(self.contract, field_path)
        if base is None:
            raise ValueError(f"AI-facing contract has no legal shape for {field_path}")
        _shape_id, shape = base
        return deepcopy(dict(shape))

    def missing_required_field_payload(self, field_path: str) -> dict[str, Any]:
        if field_path not in self.required_fields:
            raise KeyError(f"no required field entry for {field_path}")
        payload = self.legal_payload_for_path(field_path)
        return _delete_path(payload, field_path)

    def missing_required_child_field_payload(self, field_path: str) -> dict[str, Any]:
        if field_path not in self.required_child_fields:
            raise KeyError(f"no required child field entry for {field_path}")
        payload = self.legal_payload_for_path(field_path)
        return _delete_path(payload, field_path)

    def wrong_type_payload(self, field_path: str) -> dict[str, Any]:
        payload = self.legal_payload_for_path(field_path)
        exists, values = _get_path_values(payload, field_path)
        _set_path_value(payload, field_path, _wrong_type_for(values[0] if exists and values else None))
        return payload

    def empty_required_array_payload(self, field_path: str) -> dict[str, Any]:
        if field_path not in self.non_empty_array_fields:
            raise KeyError(f"no non-empty array entry for {field_path}")
        payload = self.legal_payload_for_path(field_path)
        _set_path_value(payload, field_path, [])
        return payload

    def forbidden_field_payload(self, field_path: str) -> dict[str, Any]:
        if field_path not in self.forbidden_fields:
            raise KeyError(f"no forbidden field entry for {field_path}")
        payload = self.legal_payload()
        _set_path_value(payload, field_path, True)
        return payload

    def invalid_allowed_value_payload(self, field_path: str) -> dict[str, Any]:
        options = self.allowed_value_options
        if field_path not in options:
            raise KeyError(f"no allowed_value_options entry for {field_path}")
        payload = self.legal_payload_for_path(field_path)
        _set_path_value(payload, field_path, _invalid_value_for(options[field_path]))
        return payload

    def allowed_value_payload(self, field_path: str, value: Any) -> dict[str, Any]:
        options = self.allowed_value_options
        if field_path not in options:
            raise KeyError(f"no allowed_value_options entry for {field_path}")
        if value not in options[field_path]:
            raise ValueError(f"{value!r} is not an allowed value for {field_path}")
        payload = self.legal_payload_for_path(field_path)
        _set_path_value(payload, field_path, value)
        return payload

    def alias_payload(self, alias_path: str) -> dict[str, Any]:
        aliases = self.forbidden_aliases
        if alias_path not in aliases:
            raise KeyError(f"no forbidden_aliases entry for {alias_path}")
        payload = self.legal_payload_for_path(aliases[alias_path])
        target_path = aliases[alias_path]
        exists, values = _get_path_values(payload, target_path)
        _set_path_value(payload, alias_path, values[0] if exists and values else True)
        return payload

    def repaired_payload_from_open_packet_result(
        self,
        open_packet_result: Mapping[str, Any],
    ) -> dict[str, Any]:
        responder = ContractDrivenFakeAIResponder.from_open_packet_result(open_packet_result)
        findings = responder.projection_findings()
        if findings:
            messages = ", ".join(f"{finding.code}:{finding.field_path}" for finding in findings)
            raise ValueError(f"reissued current checklist is not repairable by fake AI: {messages}")
        return responder.legal_payload()

    def option_values_seen(self, payload: Mapping[str, Any], field_path: str) -> list[Any]:
        exists, values = _get_path_values(payload, field_path)
        return values if exists else []

    def review_window_behavior_payload(
        self,
        profile_id: str,
        material_state_class: str = "all_required_material_available",
        retry_count_class: str = "first_failure",
    ) -> dict[str, Any]:
        if profile_id not in REVIEW_WINDOW_FAKE_AI_PROFILE_IDS:
            raise KeyError(f"unknown review-window fake AI profile: {profile_id}")
        if material_state_class not in review_window_contracts.REVIEW_WINDOW_MATERIAL_STATE_CLASSES:
            raise KeyError(f"unknown review-window material state: {material_state_class}")
        if retry_count_class not in review_window_contracts.RETRY_COUNT_CLASSES:
            raise KeyError(f"unknown review-window retry count class: {retry_count_class}")
        if self.delivered_review_window is None:
            raise ValueError(
                "review fake AI requires the current open_packet_result review_window"
            )
        review_window = _validate_review_window(self.delivered_review_window)
        flow_id = str(review_window.get("review_flow_id") or "")
        review_depth_rule = str(review_window["review_depth_rule"])
        required_reads = [
            str(item)
            for item in review_window.get("required_authorized_result_read_ids_before_submit", [])
            if str(item)
        ]
        base = {
            "pm_visible_summary": [
                (
                    f"Fake reviewer profile {profile_id} followed the delivered review-depth rule for {flow_id}; "
                    "weakest evidence and a current-stage failure hypothesis were inspected."
                )
            ],
            "reviewed_by_role": "human_like_reviewer",
            "passed": True,
            "findings": [],
            "blockers": [],
            "pm_suggestion_items": [
                (
                    f"PM decision-support: weakest evidence for {flow_id} is the current-stage proof boundary; "
                    "PM should adopt a targeted verification if that boundary is still thin, or reject the suggestion "
                    "because the cited current evidence already disproves the failure hypothesis."
                )
            ],
            "contract_self_check": {
                "all_required_fields_present": True,
                "exact_field_names_used": True,
                "empty_required_arrays_explicit": True,
                "runtime_mechanical_validation_passed": True,
            },
            "review_window_trace": {
                "review_flow_id": flow_id,
                "subject_lifecycle_stage": str(review_window.get("subject_lifecycle_stage") or ""),
                "consumed_authorized_result_read_ids": required_reads,
                "material_state_class": material_state_class,
                "retry_count_class": retry_count_class,
                "boundary": "review_window_control_rehearsal",
                "review_depth_rule_consumed": review_depth_rule,
                "stage_specific_challenge_projected": True,
            },
        }
        if material_state_class == "missing_required_material":
            base["review_window_trace"]["required_material_missing"] = True
            base["passed"] = False
            base["recommended_resolution"] = "Return a missing-material blocker with the missing structured path."
        elif material_state_class == "required_read_not_consumed":
            base["review_window_trace"]["consumed_authorized_result_read_ids"] = []
            base["review_window_trace"]["required_reads_skipped"] = required_reads
        elif material_state_class == "unauthorized_body_requested":
            base["review_window_trace"]["unauthorized_sealed_body_requested"] = True
            base["passed"] = False
            base["recommended_resolution"] = "Use only authorized_result_reads or return a missing-material blocker."
        elif material_state_class == "future_stage_material_requested":
            base["review_window_trace"]["future_stage_material_requested"] = True
            base["passed"] = False
            base["recommended_resolution"] = "Remove the future-stage demand and review only current-stage material."
        if profile_id == "reviewer_shallow_pass":
            base["review_window_trace"]["challenge_work_omitted"] = True
            base["findings"] = []
        if profile_id == "reviewer_stage_specific_challenge_pass":
            base["review_window_trace"]["stage_specific_challenge_performed"] = True
        if profile_id == "reviewer_generic_optimization_only":
            base["pm_visible_summary"] = [
                "Fake reviewer copied the mechanical pass style without a stage-specific challenge."
            ]
            base["pm_suggestion_items"] = [
                "PM decision-support: consider optimization toward 9/10; no hard blocker is present."
            ]
            base["review_window_trace"]["generic_optimization_only"] = True
            base["review_window_trace"]["stage_specific_challenge_projected"] = False
        if profile_id == "reviewer_skips_required_read":
            base["review_window_trace"]["consumed_authorized_result_read_ids"] = []
            base["review_window_trace"]["required_reads_skipped"] = required_reads
        if profile_id == "reviewer_future_stage_demand":
            base["passed"] = False
            base["blockers"] = [
                {
                    "blocker_id": "fake-review-window-future-stage",
                    "blocker_class": "local_artifact",
                    "summary": "Requires future-stage evidence before the current stage permits it.",
                }
            ]
            base["recommended_resolution"] = "Remove the future-stage demand and review only current-stage material."
        if profile_id == "reviewer_unauthorized_sealed_body_request":
            base["review_window_trace"]["unauthorized_sealed_body_requested"] = True
            base["passed"] = False
            base["blockers"] = [
                {
                    "blocker_id": "fake-review-window-unauthorized-body",
                    "blocker_class": "local_artifact",
                    "summary": "Requested sealed body access outside authorized_result_reads.",
                }
            ]
            base["recommended_resolution"] = "Use only authorized_result_reads or return a missing-material blocker."
        if profile_id == "reviewer_invents_scope":
            base["review_window_trace"]["invented_review_scope"] = "extra_terminal_full_project_review"
        if profile_id == "reviewer_self_repairs_subject":
            base["review_window_trace"]["reviewer_repaired_subject"] = True
            base["pm_suggestion_items"] = ["Reviewer attempted to patch the subject instead of blocking."]
        if profile_id == "reviewer_quality_score_10_exceeds_standard":
            base["pm_visible_summary"] = [
                (
                    "Quality score: 10/10; target: 9/10; minimum hard gate passed: true; "
                    "the reviewed work substantially exceeds the user's standard."
                )
            ]
            base["review_window_trace"]["quality_score"] = 10
            base["review_window_trace"]["minimum_hard_gate_passed"] = True
        if profile_id == "reviewer_quality_score_6_soft_pm_optimization":
            base["pm_visible_summary"] = [
                (
                    "Quality score: 6/10; target: 9/10; minimum hard gate passed: true; "
                    "minimum user standard is just met."
                )
            ]
            base["pm_suggestion_items"] = [
                (
                    "PM decision-support: weakest evidence is polish depth after the minimum gate; "
                    "PM may adopt a named verification or reject it because the current hard gate evidence is sufficient."
                )
            ]
            base["review_window_trace"]["quality_score"] = 6
            base["review_window_trace"]["minimum_hard_gate_passed"] = True
            base["review_window_trace"]["soft_score_pm_decision_support"] = True
        if profile_id == "reviewer_quantitative_gap_blocks":
            base["pm_visible_summary"] = [
                (
                    "Quality score: 3/10; target: 9/10; minimum hard gate passed: false; "
                    "required 100 items, delivered 5, gap 95."
                )
            ]
            base["passed"] = False
            base["blockers"] = [
                {
                    "blocker_id": "fake-review-window-quantitative-gap",
                    "blocker_class": "local_artifact",
                    "summary": "Quantitative hard requirement failed: required 100 items, delivered 5, gap 95.",
                    "required": 100,
                    "delivered": 5,
                    "gap": 95,
                    "required_repair": "Produce the missing 95 required items or obtain PM waiver authority.",
                }
            ]
            base["recommended_resolution"] = (
                "Repair the quantitative gap: required 100 items, delivered 5, gap 95."
            )
            base["review_window_trace"]["quality_score"] = 3
            base["review_window_trace"]["minimum_hard_gate_passed"] = False
            base["review_window_trace"]["quantitative_gap"] = {
                "required": 100,
                "delivered": 5,
                "gap": 95,
            }
        if profile_id == "reviewer_overblocks_sub9_soft_score":
            base["pm_visible_summary"] = [
                (
                    "Quality score: 8/10; target: 9/10; minimum hard gate passed: true; "
                    "Reviewer incorrectly treats the score alone as a blocker."
                )
            ]
            base["passed"] = False
            base["blockers"] = [
                {
                    "blocker_id": "fake-review-window-soft-score-overblock",
                    "blocker_class": "local_artifact",
                    "summary": "Incorrect blocker: score below 9/10 with hard gate already passed.",
                }
            ]
            base["recommended_resolution"] = (
                "Convert the soft score gap to PM decision-support unless a hard failure is named."
            )
            base["review_window_trace"]["quality_score"] = 8
            base["review_window_trace"]["minimum_hard_gate_passed"] = True
            base["review_window_trace"]["overblocked_soft_score"] = True
        if profile_id == "reviewer_recheck_consumes_score_context":
            base["pm_visible_summary"] = [
                (
                    "Quality score: 9/10; target: 9/10; minimum hard gate passed: true; "
                    "prior score and quantitative gap were rechecked against repaired evidence."
                )
            ]
            base["review_window_trace"]["quality_score"] = 9
            base["review_window_trace"]["prior_score_context_consumed"] = True
            base["review_window_trace"]["prior_quantitative_gap_rechecked"] = True
        core_downgrade_profiles = {
            "reviewer_reachable_only_downgrade_blocks": (
                "reachable_only_subset",
                "Reachable-only subset cannot complete the accepted deliverable.",
            ),
            "reviewer_honest_missing_substitute_blocks": (
                "honest_missing_substitute",
                "Honest missing explanation cannot complete the accepted deliverable.",
            ),
            "reviewer_status_only_closure_blocks": (
                "status_only_closure",
                "Status-only closure cannot complete the accepted deliverable.",
            ),
            "reviewer_partial_deliverable_count_blocks": (
                "partial_deliverable_count",
                "Partial count cannot complete the accepted quantity.",
            ),
            "reviewer_weaker_child_skill_output_blocks": (
                "weaker_child_skill_output",
                "Weaker child-skill output cannot close the parent deliverable.",
            ),
        }
        if profile_id in core_downgrade_profiles:
            downgrade_kind, summary = core_downgrade_profiles[profile_id]
            base["pm_visible_summary"] = [
                (
                    "Quality score: 2/10; target: 9/10; minimum hard gate passed: false; "
                    f"{summary}"
                )
            ]
            base["passed"] = False
            base["blockers"] = [
                {
                    "blocker_id": f"fake-review-window-core-deliverable-{downgrade_kind}",
                    "blocker_class": "current_gate_blocker",
                    "summary": summary,
                    "required_repair": (
                        "Return to PM for the existing repair, evidence, research, waiver, "
                        "route mutation, or user-stop path before claiming completion."
                    ),
                }
            ]
            base["recommended_resolution"] = (
                "Preserve the original core deliverable or route the missing proof through "
                "the existing blocker/repair/research/waiver/mutation/user-stop path."
            )
            base["review_window_trace"]["stage_specific_challenge_performed"] = True
            base["review_window_trace"]["core_deliverable_non_downgrade_checked"] = True
            base["review_window_trace"]["core_deliverable_downgrade_kind"] = downgrade_kind
            base["review_window_trace"]["minimum_hard_gate_passed"] = False
        if profile_id == "pm_bypasses_reviewer_blocker":
            base["review_window_trace"]["pm_text_bypass_attempted"] = True
            base["passed"] = False
            base["recommended_resolution"] = "PM must create repair work and return repaired evidence to Reviewer."
        if profile_id == "corrected_second_reviewer_retry":
            base["review_window_trace"]["corrected_retry"] = True
        if profile_id == "same_review_failure_attempts_1_to_4":
            base["review_window_trace"]["same_failure_retry_class"] = "normal_before_threshold"
            base["passed"] = False
            base["recommended_resolution"] = "Continue normal reissue or PM repair before break-glass threshold."
        if profile_id == "same_review_failure_attempt_5_break_glass":
            base["review_window_trace"]["same_failure_retry_class"] = "break_glass_threshold"
            base["passed"] = False
            base["recommended_resolution"] = "Escalate through the existing break-glass recovery threshold."
        if retry_count_class == "corrected_second_attempt":
            base["review_window_trace"]["corrected_retry"] = True
            base["passed"] = True
            base["blockers"] = []
            base["recommended_resolution"] = "Reviewer corrected the prior issue and can be rechecked normally."
            return base
        if retry_count_class == "same_failure_attempts_1_to_4":
            base["review_window_trace"]["same_failure_retry_class"] = "normal_before_threshold"
            if profile_id == "same_review_failure_attempt_5_break_glass":
                base["recommended_resolution"] = "Continue normal reissue or PM repair before break-glass threshold."
            return base
        if retry_count_class == "same_failure_attempt_5":
            base["review_window_trace"]["same_failure_retry_class"] = "break_glass_threshold"
            base["passed"] = False
            base["recommended_resolution"] = "Escalate through the existing break-glass recovery threshold."
            return base
        return base

    def malformed_body(self, profile_id: str, payload: Mapping[str, Any] | None = None) -> str:
        if profile_id not in MALFORMED_BODY_PROFILE_IDS:
            raise KeyError(f"unknown malformed body profile: {profile_id}")
        base_payload = deepcopy(dict(payload)) if isinstance(payload, Mapping) else self.legal_payload()
        legal_json = json.dumps(base_payload, ensure_ascii=True, sort_keys=True)
        if profile_id == "unquoted_keys":
            return "{decision: \"pass\", pm_visible_summary: [\"not strict json\"]}"
        if profile_id == "markdown_wrapped_json":
            return f"```json\n{legal_json}\n```"
        if profile_id == "prose_plus_json":
            return f"Here is the result:\n{legal_json}"
        if profile_id == "top_level_array":
            return f"[{legal_json}]"
        if profile_id == "empty_body":
            return ""
        if profile_id == "trailing_comma":
            return legal_json[:-1] + ",}" if legal_json.endswith("}") else f"{legal_json},"
        raise KeyError(f"unknown malformed body profile: {profile_id}")

    def malformed_body_cells(self) -> list[dict[str, str]]:
        return [
            {
                "cell_id": f"fake_ai.raw_body.{profile_id}",
                "field_path": "body",
                "contract_path": "result.body",
                "mutation_kind": f"malformed_body.{profile_id}",
                "format_profile": profile_id,
                "expected_reaction": "mechanical_reject_reissue",
                "required_evidence_owner": "contract_exhaustion_fake_ai_matrix",
            }
            for profile_id in MALFORMED_BODY_PROFILE_IDS
        ]

    def retry_cells(self) -> list[dict[str, str]]:
        cells: list[dict[str, str]] = []
        repairable_paths = list(
            dict.fromkeys(
                [
                    *self.required_fields,
                    *self.required_child_fields,
                    *[f"result.{field}" for field in sorted(self.allowed_value_options)],
                    *[f"result.{alias}" for alias in sorted(self.forbidden_aliases)],
                ]
            )
        ) or ["result.body"]
        for profile_id in RETRY_PROFILE_IDS:
            for field_path in repairable_paths:
                cells.append(
                    {
                        "cell_id": f"fake_ai.retry.{profile_id}.{field_path}",
                        "field_path": field_path,
                        "contract_path": field_path,
                        "mutation_kind": profile_id,
                        "expected_reaction": (
                            "accepted_after_reissue"
                            if profile_id == "corrected_second_retry"
                            else "same_family_repair_or_reissue_without_glassbreak_before_threshold"
                        ),
                        "required_evidence_owner": "contract_exhaustion_fake_ai_matrix",
                    }
                )
        return cells

    def projection_gap_cells(self) -> list[dict[str, str]]:
        cells: list[dict[str, str]] = []
        if self.required_child_fields:
            cells.append(
                {
                    "cell_id": "fake_ai.projection.hidden_required_child_gap",
                    "field_path": self.required_child_fields[0],
                    "contract_path": self.required_child_fields[0],
                    "mutation_kind": "hidden_projection_gap",
                    "expected_reaction": "projection_preflight_failure",
                    "required_evidence_owner": "contract_exhaustion_fake_ai_matrix",
                }
            )
        if self.allowed_value_options:
            field_path = sorted(self.allowed_value_options)[0]
            cells.append(
                {
                    "cell_id": f"fake_ai.projection.finite_option_mistake.{field_path}",
                    "field_path": field_path,
                    "contract_path": f"result.{field_path}",
                    "mutation_kind": "finite_option_mistake",
                    "expected_reaction": "mechanical_reject_reissue_with_options",
                    "required_evidence_owner": "contract_exhaustion_fake_ai_matrix",
                }
            )
        if self.forbidden_aliases:
            alias_path = sorted(self.forbidden_aliases)[0]
            cells.append(
                {
                    "cell_id": f"fake_ai.projection.forbidden_alias.{alias_path}",
                    "field_path": alias_path,
                    "contract_path": f"result.{alias_path}",
                    "mutation_kind": "forbidden_alias",
                    "expected_reaction": "mechanical_reject_reissue_with_exact_field",
                    "required_evidence_owner": "contract_exhaustion_fake_ai_matrix",
                }
            )
        for contract_key, field_path in (
            ("required_acceptance_item_ids", "nodes[].acceptance_item_ids[]"),
            ("required_node_acceptance_item_ids", "node_context_package.acceptance_item_projection[].acceptance_item_id"),
        ):
            values = self.contract.get(contract_key)
            if isinstance(values, list):
                cells.append(
                    {
                        "cell_id": f"fake_ai.projection.complete_owner_coverage.{contract_key}",
                        "field_path": field_path,
                        "contract_path": contract_key,
                        "mutation_kind": "complete_owner_coverage",
                        "expected_reaction": "accepted_current_contract",
                        "required_evidence_owner": "contract_exhaustion_fake_ai_matrix",
                    }
                )
            if isinstance(values, list) and not values:
                cells.append(
                    {
                        "cell_id": f"fake_ai.projection.empty_owner_set_extra_id.{contract_key}",
                        "field_path": field_path,
                        "contract_path": contract_key,
                        "mutation_kind": "empty_owner_set_extra_id",
                        "expected_reaction": "mechanical_reject_reissue_with_owner_set",
                        "required_evidence_owner": "contract_exhaustion_fake_ai_matrix",
                    }
                )
            if isinstance(values, list) and values:
                cells.append(
                    {
                        "cell_id": f"fake_ai.projection.missing_active_id_coverage.{contract_key}",
                        "field_path": field_path,
                        "contract_path": contract_key,
                        "mutation_kind": "missing_active_id_coverage",
                        "expected_reaction": "mechanical_reject_reissue_with_missing_ids",
                        "required_evidence_owner": "contract_exhaustion_fake_ai_matrix",
                    }
                )
                cells.append(
                    {
                        "cell_id": f"fake_ai.projection.partial_owner_set_missing_id.{contract_key}",
                        "field_path": field_path,
                        "contract_path": contract_key,
                        "mutation_kind": "partial_owner_set_missing_id",
                        "expected_reaction": "mechanical_reject_reissue_with_missing_ids",
                        "required_evidence_owner": "contract_exhaustion_fake_ai_matrix",
                    }
                )
                cells.append(
                    {
                        "cell_id": f"fake_ai.projection.extra_owner_id.{contract_key}",
                        "field_path": field_path,
                        "contract_path": contract_key,
                        "mutation_kind": "extra_owner_id",
                        "expected_reaction": "mechanical_reject_reissue_with_owner_set",
                        "required_evidence_owner": "contract_exhaustion_fake_ai_matrix",
                    }
                )
                if contract_key == "required_node_acceptance_item_ids":
                    cells.append(
                        {
                            "cell_id": f"fake_ai.projection.malformed_projection_row.{contract_key}",
                            "field_path": "node_context_package.acceptance_item_projection[]",
                            "contract_path": contract_key,
                            "mutation_kind": "malformed_projection_row",
                            "expected_reaction": "mechanical_reject_reissue",
                            "required_evidence_owner": "contract_exhaustion_fake_ai_matrix",
                        }
                    )
        return cells

    def formal_artifact_cells(self) -> list[dict[str, str]]:
        artifact_contract = self.contract.get("formal_artifact_contract")
        evidence_policy = self.contract.get("evidence_output_policy")
        if not isinstance(artifact_contract, Mapping) and not (
            isinstance(evidence_policy, Mapping)
            and evidence_policy.get("required_for_formal_run") is True
        ):
            return []
        artifact_id = str(formal_artifact_contracts.FLOWGUARD_FORMAL_ARTIFACT_CONTRACT["artifact_id"])
        if isinstance(artifact_contract, Mapping):
            artifact_id = str(artifact_contract.get("artifact_id") or artifact_id)
        decision_path = f"{artifact_id}.model_test_alignment_report.decision"
        return [
            {
                "cell_id": f"fake_ai.formal_artifact.{profile_id}",
                "field_path": decision_path if "decision" in profile_id or "blocks" in profile_id else artifact_id,
                "contract_path": f"artifact.{decision_path}" if "decision" in profile_id or "blocks" in profile_id else f"artifact.{artifact_id}",
                "mutation_kind": profile_id,
                "expected_reaction": (
                    "breakglass_after_fifth_same_failure"
                    if profile_id == "wrong_formal_artifact_path"
                    else "mechanical_reject_reissue_with_artifact_instructions"
                ),
                "required_evidence_owner": "contract_exhaustion_fake_ai_matrix",
            }
            for profile_id in FORMAL_ARTIFACT_PROFILE_IDS
        ]

    def option_value_cells(self) -> list[dict[str, str]]:
        cells: list[dict[str, str]] = []
        for field_path, values in sorted(self.allowed_value_options.items()):
            if not _contract_shape_has_path(self.contract, field_path):
                continue
            for value in values:
                payload = self.allowed_value_payload(field_path, value)
                if value not in self.option_values_seen(payload, field_path):
                    continue
                cells.append(
                    {
                        "field_path": field_path,
                        "contract_path": f"result.{field_path}",
                        "mutation_kind": "legal_allowed_value",
                        "value_json": _value_key(value),
                    }
                )
        return cells
    def coverage_cells(self) -> list[dict[str, str]]:
        cells: list[dict[str, str]] = [
            *self.malformed_body_cells(),
            *self.retry_cells(),
            *self.projection_gap_cells(),
            *self.formal_artifact_cells(),
        ]
        for field_path in self.required_fields:
            cells.append(
                {
                    "field_path": field_path,
                    "contract_path": field_path,
                    "mutation_kind": "missing_required_field",
                }
            )
            cells.append(
                {
                    "field_path": field_path,
                    "contract_path": field_path,
                    "mutation_kind": "wrong_type",
                }
            )
        for field_path in self.required_child_fields:
            cells.append(
                {
                    "field_path": field_path,
                    "contract_path": field_path,
                    "mutation_kind": "missing_required_child_field",
                }
            )
            cells.append(
                {
                    "field_path": field_path,
                    "contract_path": field_path,
                    "mutation_kind": "wrong_type",
                }
            )
        for field_path in self.non_empty_array_fields:
            cells.append(
                {
                    "field_path": field_path,
                    "contract_path": field_path,
                    "mutation_kind": "empty_required_array",
                }
            )
        for field_path in self.forbidden_fields:
            cells.append(
                {
                    "field_path": field_path,
                    "contract_path": field_path,
                    "mutation_kind": "forbidden_field_present",
                }
            )
        for field_path in sorted(self.allowed_value_options):
            cells.append(
                {
                    "field_path": field_path,
                    "contract_path": (
                        "current_handoff_contract.required_report_contract."
                        f"allowed_value_options.{field_path}"
                    ),
                    "mutation_kind": "missing_allowed_value_options",
                }
            )
            cells.append(
                {
                    "field_path": field_path,
                    "contract_path": f"result.{field_path}",
                    "mutation_kind": "wrong_allowed_value",
                }
            )
        for field_path in sorted(self.field_type_requirements):
            cells.append(
                {
                    "field_path": field_path,
                    "contract_path": (
                        "current_handoff_contract.required_report_contract."
                        f"field_type_requirements.{field_path}"
                    ),
                    "mutation_kind": "missing_field_type_requirements",
                }
            )
            cells.append(
                {
                    "field_path": field_path,
                    "contract_path": f"result.{field_path}",
                    "mutation_kind": "wrong_type",
                }
            )
        for alias_path in sorted(self.forbidden_aliases):
            cells.append(
                {
                    "field_path": alias_path,
                    "contract_path": (
                        "current_handoff_contract.required_report_contract."
                        f"forbidden_aliases.{alias_path}"
                    ),
                    "mutation_kind": "forbidden_alias_used",
                }
            )
            cells.append(
                {
                    "field_path": alias_path,
                    "contract_path": f"result.{alias_path}",
                    "mutation_kind": "forbidden_alias_used",
                }
            )
        return cells


def runtime_known_formal_artifact_cells() -> list[dict[str, str]]:
    cells: list[dict[str, str]] = []
    for contract in formal_artifact_contracts.all_contracts():
        artifact_id = str(contract["artifact_id"])
        decision_field = str(contract["decision_field_path"])
        decision_path = formal_artifact_contracts.artifact_field_path(contract, decision_field)
        for profile_id in formal_artifact_contracts.fault_modes(contract):
            field_path = decision_path if "decision" in profile_id or "blocks" in profile_id else artifact_id
            cells.append(
                {
                    "cell_id": f"fake_ai.formal_artifact.{contract['contract_id']}.{profile_id}",
                    "field_path": field_path,
                    "contract_path": f"artifact.{field_path}",
                    "mutation_kind": profile_id,
                    "expected_reaction": (
                        "breakglass_after_fifth_same_failure"
                        if profile_id == "wrong_formal_artifact_path"
                        else "mechanical_reject_reissue_with_artifact_instructions"
                    ),
                    "required_evidence_owner": "contract_exhaustion_fake_ai_matrix",
                }
            )
    return cells
