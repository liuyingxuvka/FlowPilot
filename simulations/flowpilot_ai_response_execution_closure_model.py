"""Execution-backed finite coverage for formal FlowPilot AI responses.

The complete registered packet-result family inventory is enumerated across a
declared mechanical mutation universe: one current minimal shape, every
top-level required-field omission, and every registered forbidden field.  A
constrained runtime universe is then reduced by a deterministic covering-array
selector.  Only selected cells execute the real FlowPilot submit-result
boundary; unselected cells remain explicit ``not_run`` receipts and are never
promoted to passing evidence.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from itertools import combinations, product
from pathlib import Path
from typing import Any, Iterable, Mapping, NamedTuple, Sequence

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
SIMULATIONS = ROOT / "simulations"
for candidate in (str(ASSETS), str(SIMULATIONS)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import flowpilot_new as public_flowpilot  # noqa: E402
from flowpilot_contract_driven_fake_ai import ContractDrivenFakeAIResponder  # noqa: E402
from flowpilot_core_runtime import packet_result_contracts, run_shell, runtime  # noqa: E402
from flowpilot_core_runtime_scenarios import (  # noqa: E402
    _base_ledger,
    _complete_open_packet,
    _flowguard_result_body,
    _open_packet_by_kind,
    _role_result_body,
)


MODEL_ID = "flowpilot_ai_response_execution_closure"
MAX_SEQUENCE_LENGTH = 4

FAST_BUDGET_SECONDS = 240.0
ADVERSARIAL_BUDGET_SECONDS = 3600.0
BENCHMARK_CASE_COUNT = 40
BENCHMARK_PARALLEL_WORKERS = 2
BENCHMARK_SHARD_COUNT = 4

EXECUTION_FAMILIES = (
    "task.node",
    "flowguard_check.post_result",
    "review.any_current_subject",
)
RESPONSE_SOURCES = (
    "current_projection",
    "required_field_omission",
    "forbidden_field_injection",
)
VALIDITIES = ("valid", "invalid")
ROLES = ("worker", "pm", "reviewer", "flowguard_operator")
TIMING_CLASSES = (
    "current",
    "before_ack",
    "stale_route",
    "duplicate_replay",
)
SELECTION_AXES = (
    "contract_family",
    "validity",
    "response_source",
    "role",
    "timing_class",
)
BUSINESS_TRIPLE_AXES: dict[str, tuple[str, str, str]] = {
    "role_source_state": ("role", "response_source", "timing_class"),
    "family_fault_lifecycle": ("contract_family", "fault_class", "lifecycle_state"),
    "review_depth_subject_evidence": ("review_depth", "subject_class", "evidence_class"),
    "read_set_open_submit": ("read_set_class", "open_state", "submit_state"),
    "reissue_identity_replay": ("reissue_class", "identity_class", "replay_class"),
}
CRITICAL_TRIPLE_AXES = tuple(BUSINESS_TRIPLE_AXES.values())

PUBLIC_PIPELINE_STAGES = (
    "dispatch_current_role",
    "lease",
    "ack",
    "open_packet",
    "submission_checklist.v2",
    "checklist_responder",
    "submit_result",
)

STATIC_PROFILE_VARIANTS: tuple[dict[str, Any], ...] = (
    {
        "variant_id": "flowguard.semantic_recheck_required",
        "family_id": "flowguard_check.post_result",
        "profile_ids": ("flowguard.semantic_recheck_required",),
        "profile_bindings": {
            "flowguard.semantic_recheck_required": {
                "blocker_id": "blocker-formal-static-001",
                "coverage_boundary": "subject_bound_semantic",
                "authorized_result_read_ids": ["result-formal-static-001"],
                "repair_obligation_ids": ["repair-obligation-formal-static-001"],
            }
        },
    },
    {
        "variant_id": "flowguard.subject_artifacts_consumed_required",
        "family_id": "flowguard_check.post_result",
        "profile_ids": ("flowguard.subject_artifacts_consumed_required",),
        "profile_bindings": {
            "flowguard.subject_artifacts_consumed_required": {
                "artifact_ids": ["artifact-formal-static-001"],
            }
        },
    },
)

STATIC_IDENTITY_FIELDS = (
    "run_id",
    "packet_id",
    "lease_id",
    "route_version",
    "source_generation",
    "contract_fingerprint",
)

HISTORICAL_MISS_IDS = (
    "databank_runtime_miss",
    "zero_forbidden_coverage",
    "checklist_bypass",
    "static_reviewer_policy",
    "wrong_role_submission",
    "daemon_replay_positive_path",
    "public_runtime_discrepancy",
)

FUZZ_PROFILE_IDS = (
    "duplicate_json_keys",
    "invalid_numeric_nan",
    "invalid_numeric_infinity",
    "utf8_bom",
    "invalid_unicode_scalar",
    "top_level_non_object",
    "prose_wrapper",
    "markdown_wrapper",
    "excessive_size",
    "excessive_depth",
    "sequential_replay",
    "concurrent_double_submit",
    "cross_run_identity_collision",
)

# These are the 22 source-path pairs that the predecessor sanitized-id scheme
# collapsed.  Repeated pairs are retained because they came from distinct
# predecessor source rows and every audited collision must stay visible.
AUDITED_LEGACY_COLLISION_PATH_PAIRS = (
    ("semantic_recheck", "result.semantic_recheck"),
    ("semantic_recheck.blocker_id", "result.semantic_recheck.blocker_id"),
    ("semantic_recheck.subject_result_consumed", "result.semantic_recheck.subject_result_consumed"),
    ("semantic_recheck.subject_bound_semantic_coverage", "result.semantic_recheck.subject_bound_semantic_coverage"),
    ("semantic_recheck.coverage_boundary", "result.semantic_recheck.coverage_boundary"),
    ("subject_artifacts_consumed", "result.subject_artifacts_consumed"),
    ("subject_artifacts_consumed[].artifact_id", "result.subject_artifacts_consumed[].artifact_id"),
    ("semantic_recheck", "result.semantic_recheck"),
    ("semantic_recheck.blocker_id", "result.semantic_recheck.blocker_id"),
    ("semantic_recheck.subject_result_consumed", "result.semantic_recheck.subject_result_consumed"),
    ("semantic_recheck.subject_bound_semantic_coverage", "result.semantic_recheck.subject_bound_semantic_coverage"),
    ("semantic_recheck.coverage_boundary", "result.semantic_recheck.coverage_boundary"),
    (
        "current_handoff_contract.required_report_contract.forbidden_aliases.authorized_result_body_consumed",
        "result.authorized_result_body_consumed",
    ),
    (
        "current_handoff_contract.required_report_contract.forbidden_aliases.blocker_bound_semantic_requirement_satisfied",
        "result.blocker_bound_semantic_requirement_satisfied",
    ),
    (
        "current_handoff_contract.required_report_contract.forbidden_aliases.repair_evidence_obligations_consumed",
        "result.repair_evidence_obligations_consumed",
    ),
    (
        "current_handoff_contract.required_report_contract.forbidden_aliases.semantic_recheck.authorized_result_body_consumed",
        "result.semantic_recheck.authorized_result_body_consumed",
    ),
    (
        "current_handoff_contract.required_report_contract.forbidden_aliases.semantic_recheck.blocker_bound_semantic_requirement_satisfied",
        "result.semantic_recheck.blocker_bound_semantic_requirement_satisfied",
    ),
    (
        "current_handoff_contract.required_report_contract.forbidden_aliases.semantic_recheck.repair_evidence_obligations_consumed",
        "result.semantic_recheck.repair_evidence_obligations_consumed",
    ),
    ("subject_artifacts_consumed", "result.subject_artifacts_consumed"),
    ("subject_artifacts_consumed[].artifact_id", "result.subject_artifacts_consumed[].artifact_id"),
    (
        "current_handoff_contract.required_report_contract.forbidden_aliases.consumed_subject_artifacts",
        "result.consumed_subject_artifacts",
    ),
    (
        "current_handoff_contract.required_report_contract.forbidden_aliases.subject_artifact_consumption",
        "result.subject_artifact_consumption",
    ),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_id(prefix: str, *parts: str) -> str:
    source = "\x1f".join(str(part) for part in parts)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]
    readable = "-".join(
        "".join(char if char.isalnum() else "-" for char in str(part)).strip("-")
        for part in parts
    )
    return f"{prefix}:{readable}:{digest}"


def _json_copy(value: Any) -> Any:
    return json.loads(json.dumps(value))


def source_fingerprint() -> str:
    paths = (
        Path(__file__),
        ASSETS / "flowpilot_core_runtime" / "packet_result_contracts.py",
        ASSETS / "flowpilot_core_runtime" / "runtime.py",
        ASSETS / "flowpilot_new.py",
        ASSETS / "flowpilot_new_role_commands.py",
        ASSETS / "flowpilot_new_run_commands.py",
        SIMULATIONS / "flowpilot_contract_driven_fake_ai.py",
        SIMULATIONS / "flowpilot_core_runtime_scenarios.py",
    )
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _path_root(path: str) -> str:
    return path.split(".", 1)[0].replace("[]", "")


def _inject_path(payload: dict[str, Any], path: str, value: Any) -> None:
    current: dict[str, Any] = payload
    parts = path.split(".")
    for index, raw_part in enumerate(parts):
        is_array = raw_part.endswith("[]")
        key = raw_part.removesuffix("[]")
        last = index == len(parts) - 1
        if last:
            current[key] = [value] if is_array else value
            return
        if is_array:
            rows = current.get(key)
            if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
                rows = [{}]
                current[key] = rows
            current = rows[0]
        else:
            child = current.get(key)
            if not isinstance(child, dict):
                child = {}
                current[key] = child
            current = child


def _path_exists(payload: Mapping[str, Any], path: str) -> bool:
    current: Any = payload
    for raw_part in path.split("."):
        is_array = raw_part.endswith("[]")
        key = raw_part.removesuffix("[]")
        if not isinstance(current, Mapping) or key not in current:
            return False
        current = current[key]
        if is_array:
            if not isinstance(current, list) or not current:
                return False
            current = current[0]
    return True


def case_id_collision_failures(cells: Sequence[Mapping[str, Any]]) -> list[str]:
    failures: list[str] = []
    by_id: dict[str, set[str]] = {}
    by_path: dict[str, set[str]] = {}
    identity_counts: dict[tuple[str, str], int] = {}
    for cell in cells:
        case_id = str(cell.get("case_id") or "")
        source_path = str(cell.get("source_contract_path") or "")
        if not case_id or not source_path:
            failures.append("case_identity_missing_full_source_path")
            continue
        by_id.setdefault(case_id, set()).add(source_path)
        by_path.setdefault(source_path, set()).add(case_id)
        identity = (case_id, source_path)
        identity_counts[identity] = identity_counts.get(identity, 0) + 1
    for (case_id, source_path), count in sorted(identity_counts.items()):
        if count > 1:
            failures.append(f"duplicate_case_identity:{case_id}:{source_path}:count={count}")
    for case_id, paths in sorted(by_id.items()):
        if len(paths) > 1:
            failures.append(f"case_id_collision:{case_id}:{sorted(paths)}")
    for source_path, ids in sorted(by_path.items()):
        if len(ids) > 1:
            failures.append(f"source_path_multiple_case_ids:{source_path}:{sorted(ids)}")
    return failures


def audited_collision_repair_report() -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    for index, (left, right) in enumerate(AUDITED_LEGACY_COLLISION_PATH_PAIRS, start=1):
        family = "flowguard.semantic_recheck_required" if "semantic_recheck" in left else "flowguard.subject_artifacts_consumed_required"
        left_source = f"audited-collision/{index:02d}/{family}/wrong-or-alias/{left}"
        right_source = f"audited-collision/{index:02d}/{family}/wrong-or-alias/{right}"
        rows.extend(
            [
                {"case_id": _stable_id("collision", left_source), "source_contract_path": left_source},
                {"case_id": _stable_id("collision", right_source), "source_contract_path": right_source},
            ]
        )
    failures = case_id_collision_failures(rows)
    pair_ids_distinct = all(rows[index]["case_id"] != rows[index + 1]["case_id"] for index in range(0, len(rows), 2))
    return {
        "ok": not failures and pair_ids_distinct and len(AUDITED_LEGACY_COLLISION_PATH_PAIRS) == 22,
        "audited_collision_pair_count": len(AUDITED_LEGACY_COLLISION_PATH_PAIRS),
        "regenerated_case_count": len(rows),
        "pair_ids_distinct": pair_ids_distinct,
        "failures": failures,
        "rows": rows,
    }


def _static_responsibility(packet_kind: str) -> str:
    if packet_kind == "flowguard_check":
        return "flowguard_operator"
    if packet_kind == "review":
        return "reviewer"
    if packet_kind.startswith("pm_"):
        return "pm"
    return "worker"


def _static_route_scope(raw_scope: str) -> str:
    return "node_result_review" if raw_scope.startswith("<") else raw_scope


def _new_static_packet(
    *,
    family_id: str,
    profile_ids: Sequence[str] = (),
    profile_bindings: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], str]:
    row = packet_result_contracts.contract_for_family(family_id)
    if row is None:
        raise KeyError(f"unknown static contract family: {family_id}")
    packet_kind = str(row["packet_kind"])
    route_scope = _static_route_scope(str(row["route_scope"]))
    responsibility = _static_responsibility(packet_kind)
    ledger = runtime.new_ledger(
        "Exercise one formal static response mutation",
        "A mechanical fault must block, reissue, and avoid forbidden downstream effects.",
    )
    ledger["run_root"] = tempfile.mkdtemp(prefix="flowpilot-formal-static-")
    ledger["startup_intake"] = {
        "status": "confirmed",
        "current_run_authority": True,
        "controller_may_read_body": False,
        "body_text_included": False,
        "startup_answers": {"background_collaboration_authorized": True},
    }
    runtime.create_route(ledger, "Formal static mutation route", ["exercise one static mutation"])
    route_node_id = ""
    if family_id == "task.node_acceptance_plan":
        route_node_id = "node-formal-static-001"
        ledger.setdefault("route_nodes", {})[route_node_id] = {
            "node_id": route_node_id,
            "title": "Formal static node",
            "node_kind": "leaf",
            "parent_node_id": "",
            "child_node_ids": [],
            "acceptance_item_ids": [],
            "status": "open",
        }
    subject_id = ""
    if family_id == "review.any_current_subject":
        subject_id = runtime.issue_task_packet(
            ledger,
            "worker",
            "Static review subject",
            "SEALED_STATIC_REVIEW_SUBJECT",
            route_scope="node",
        )
    packet_body = (
        json.dumps({"segment_targets": [{"segment_id": "segment-formal-static-001"}]})
        if family_id == "review.terminal_backward_replay"
        else "SEALED_FORMAL_STATIC_BODY"
    )
    packet_id = runtime.issue_task_packet(
        ledger,
        responsibility,
        "Return one current structured static result",
        packet_body,
        packet_kind=packet_kind,
        route_scope=route_scope,
        route_node_id=route_node_id,
        subject_id=subject_id,
        result_contract_profile_ids=list(profile_ids),
        result_contract_profile_bindings=profile_bindings or {},
        repair_trigger_origin=(
            "reviewer_or_system_failure"
            if packet_kind == "pm_repair_decision"
            else ""
        ),
    )
    observed_family = packet_result_contracts.packet_result_family_id(
        ledger["packets"][packet_id]["envelope"]
    )
    if observed_family != family_id:
        raise AssertionError(f"static packet family mismatch: expected={family_id} observed={observed_family}")
    return ledger, packet_id


def _static_variant_specs() -> tuple[dict[str, Any], ...]:
    variants: list[dict[str, Any]] = []
    for row in packet_result_contracts.PACKET_RESULT_CONTRACTS:
        variants.append(
            {
                "variant_id": "base",
                "family_id": str(row["family_id"]),
                "profile_ids": (),
                "profile_bindings": {},
                "delta_only": False,
            }
        )
    variants.extend({**variant, "delta_only": True} for variant in STATIC_PROFILE_VARIANTS)
    return tuple(variants)


def _contract_delta(profile: Mapping[str, Any], base: Mapping[str, Any]) -> dict[str, Any]:
    list_keys = (
        "required_fields",
        "required_child_fields",
        "explicit_array_fields",
        "non_empty_array_fields",
        "forbidden_fields",
    )
    result: dict[str, Any] = {
        key: [item for item in profile.get(key, []) if item not in set(base.get(key, []))]
        for key in list_keys
    }
    for key in ("allowed_value_options", "field_type_requirements", "forbidden_aliases"):
        profile_map = profile.get(key) if isinstance(profile.get(key), Mapping) else {}
        base_map = base.get(key) if isinstance(base.get(key), Mapping) else {}
        result[key] = {
            str(field): _json_copy(value)
            for field, value in profile_map.items()
            if field not in base_map or base_map.get(field) != value
        }
    return result


def _static_contract_from_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    contract = runtime._packet_effective_result_contract(packet)
    envelope = packet.get("envelope") if isinstance(packet.get("envelope"), Mapping) else {}
    handoff = envelope.get("current_handoff_contract") if isinstance(envelope, Mapping) else {}
    report = handoff.get("required_report_contract") if isinstance(handoff, Mapping) else {}
    forbidden = set(str(item) for item in contract.get("forbidden_fields") or [])
    if (
        isinstance(report, Mapping)
        and report.get("pm_visible_summary_required") is True
        and "pm_visible_summary" not in forbidden
    ):
        for key in ("required_fields", "explicit_array_fields", "non_empty_array_fields"):
            values = list(contract.get(key) or [])
            if "pm_visible_summary" not in values:
                values.append("pm_visible_summary")
            contract[key] = values
        minimal = _json_copy(contract.get("minimal_valid_shape") or {})
        minimal.setdefault("pm_visible_summary", ["Current role-authored summary."])
        contract["minimal_valid_shape"] = minimal
        branches = _json_copy(contract.get("branch_valid_shapes") or {})
        for shape in branches.values():
            if isinstance(shape, dict):
                shape.setdefault("pm_visible_summary", ["Current role-authored summary."])
        contract["branch_valid_shapes"] = branches
    return contract


def _static_cell_payload(
    contract: Mapping[str, Any],
    *,
    mutation_kind: str,
    mutation_path: str,
) -> dict[str, Any]:
    responder_contract = {
        "required_result_body_fields": list(contract.get("required_fields") or []),
        "required_child_fields": list(contract.get("required_child_fields") or []),
        "explicit_array_fields": list(contract.get("explicit_array_fields") or []),
        "non_empty_array_fields": list(contract.get("non_empty_array_fields") or []),
        "allowed_value_options": _json_copy(contract.get("allowed_value_options") or {}),
        "field_type_requirements": _json_copy(contract.get("field_type_requirements") or {}),
        "forbidden_fields": list(contract.get("forbidden_fields") or []),
        "forbidden_aliases": _json_copy(contract.get("forbidden_aliases") or {}),
        "minimal_valid_shape": _json_copy(contract.get("minimal_valid_shape") or {}),
        "branch_valid_shapes": _json_copy(contract.get("branch_valid_shapes") or {}),
    }
    responder = ContractDrivenFakeAIResponder(responder_contract)
    if mutation_kind == "valid_minimal_shape":
        return responder.legal_payload()
    if mutation_kind == "missing_required":
        return responder.missing_required_field_payload(mutation_path)
    if mutation_kind == "missing_required_child":
        return responder.missing_required_child_field_payload(mutation_path)
    if mutation_kind in {"wrong_explicit_array_type", "wrong_field_type"}:
        return responder.wrong_type_payload(mutation_path)
    if mutation_kind == "empty_non_empty_array":
        return responder.empty_required_array_payload(mutation_path)
    if mutation_kind == "invalid_allowed_value":
        return responder.invalid_allowed_value_payload(mutation_path)
    if mutation_kind == "forbidden_field":
        return responder.forbidden_field_payload(mutation_path)
    if mutation_kind == "forbidden_alias":
        return responder.alias_payload(mutation_path)
    raise KeyError(f"unsupported static mutation kind: {mutation_kind}")


def build_static_contract_universe() -> tuple[dict[str, Any], ...]:
    """Enumerate all current structural fault classes plus checklist identity faults."""

    cells: list[dict[str, Any]] = []
    for variant in _static_variant_specs():
        family_id = str(variant["family_id"])
        profile_ids = tuple(str(item) for item in variant.get("profile_ids") or ())
        profile_bindings = _json_copy(variant.get("profile_bindings") or {})
        ledger, packet_id = _new_static_packet(
            family_id=family_id,
            profile_ids=profile_ids,
            profile_bindings=profile_bindings,
        )
        packet = ledger["packets"][packet_id]
        contract = _static_contract_from_packet(packet)
        declaration = contract
        if variant.get("delta_only"):
            base_ledger, base_packet_id = _new_static_packet(family_id=family_id)
            base_contract = _static_contract_from_packet(base_ledger["packets"][base_packet_id])
            declaration = _contract_delta(contract, base_contract)
        variant_id = str(variant["variant_id"])
        common = {
            "contract_family": family_id,
            "contract_variant": variant_id,
            "profile_ids": list(profile_ids),
            "profile_bindings": profile_bindings,
            "packet_kind": str(packet["envelope"]["packet_kind"]),
            "route_scope": str(packet["envelope"]["route_scope"]),
            "responsibility": str(packet["envelope"]["responsibility"]),
            "applicable": True,
            "structured_exclusion": None,
        }
        valid_source_path = f"contract-registry/{family_id}/{variant_id}/valid-minimal-shape/$"
        cells.append(
            {
                **common,
                "case_id": _stable_id("static", valid_source_path),
                "source_contract_path": valid_source_path,
                "mutation_kind": "valid_minimal_shape",
                "mutation_path": "",
                "expected_reaction": "mechanically_candidate_valid",
                "payload": _static_cell_payload(
                    contract,
                    mutation_kind="valid_minimal_shape",
                    mutation_path="",
                ),
            }
        )
        mutation_sources = (
            ("missing_required", "required_fields"),
            ("missing_required_child", "required_child_fields"),
            ("wrong_explicit_array_type", "explicit_array_fields"),
            ("empty_non_empty_array", "non_empty_array_fields"),
            ("invalid_allowed_value", "allowed_value_options"),
            ("wrong_field_type", "field_type_requirements"),
            ("forbidden_field", "forbidden_fields"),
            ("forbidden_alias", "forbidden_aliases"),
        )
        for mutation_kind, contract_key in mutation_sources:
            raw_values = declaration.get(contract_key) or {}
            field_paths = list(raw_values) if isinstance(raw_values, Mapping) else list(raw_values)
            for field_path in field_paths:
                source_path = f"contract-registry/{family_id}/{variant_id}/{mutation_kind}/{field_path}"
                applicable = True
                structured_exclusion = None
                try:
                    payload = _static_cell_payload(
                        contract,
                        mutation_kind=mutation_kind,
                        mutation_path=str(field_path),
                    )
                except ValueError:
                    if str(field_path).startswith("flowguard_evidence.json."):
                        applicable = False
                        payload = {}
                        structured_exclusion = {
                            "reason": "field_is_owned_by_external_flowguard_evidence_artifact_not_result_body",
                            "source_reference": str(field_path),
                            "owner": "formal_artifact_contract_suite",
                            "expiry_condition": "becomes applicable only if the field moves into the packet result body contract",
                        }
                    else:
                        raise
                cells.append(
                    {
                        **common,
                        "case_id": _stable_id("static", source_path),
                        "source_contract_path": source_path,
                        "mutation_kind": mutation_kind,
                        "mutation_path": str(field_path),
                        "expected_reaction": "mechanical_contract_blocked",
                        "payload": payload,
                        "applicable": applicable,
                        "structured_exclusion": structured_exclusion,
                    }
                )
    for identity_field in STATIC_IDENTITY_FIELDS:
        source_path = f"public-open/task.node/identity-mismatch/{identity_field}"
        cells.append(
            {
                "case_id": _stable_id("static", source_path),
                "source_contract_path": source_path,
                "contract_family": "task.node",
                "contract_variant": "public_checklist_identity",
                "profile_ids": [],
                "profile_bindings": {},
                "packet_kind": "task",
                "route_scope": "node",
                "responsibility": "worker",
                "mutation_kind": "identity_mismatch",
                "mutation_path": identity_field,
                "expected_reaction": "rejected_before_submit",
                "payload": {},
                "applicable": True,
                "structured_exclusion": None,
            }
        )
    return tuple(sorted(cells, key=lambda cell: str(cell["case_id"])))


def static_universe_failures(cells: Sequence[Mapping[str, Any]]) -> list[str]:
    failures: list[str] = case_id_collision_failures(cells)
    observed_families = {str(cell.get("contract_family") or "") for cell in cells}
    registered_families = set(packet_result_contracts.PACKET_RESULT_CONTRACTS_BY_FAMILY)
    if observed_families != registered_families:
        failures.append("registered_contract_family_not_fully_enumerated")
    for cell in cells:
        family_id = str(cell["contract_family"])
        mutation = str(cell["mutation_kind"])
        if cell.get("applicable") is False:
            continue
        path = str(cell.get("mutation_path") or "")
        payload = cell.get("payload")
        if not isinstance(payload, Mapping):
            failures.append(f"{cell['case_id']}:payload_not_object")
            continue
        root = _path_root(path) if path else ""
        if mutation == "missing_required" and root in payload:
            failures.append(f"{cell['case_id']}:required_field_not_removed")
        if mutation == "missing_required_child" and _path_exists(payload, path):
            failures.append(f"{cell['case_id']}:required_child_field_not_removed")
        if mutation == "forbidden_field" and not _path_exists(payload, path):
            failures.append(f"{cell['case_id']}:forbidden_field_not_injected")
        if mutation == "forbidden_alias" and not _path_exists(payload, path):
            failures.append(f"{cell['case_id']}:forbidden_alias_not_injected")
        if mutation == "empty_non_empty_array":
            exists, value = runtime._payload_path_value(payload, path)
            if not exists or value != []:
                failures.append(f"{cell['case_id']}:non_empty_array_not_emptied")
        if mutation == "valid_minimal_shape":
            if not payload:
                failures.append(f"{cell['case_id']}:minimal_shape_empty")
    required_mutation_kinds = {
        "missing_required",
        "missing_required_child",
        "wrong_explicit_array_type",
        "empty_non_empty_array",
        "invalid_allowed_value",
        "wrong_field_type",
        "forbidden_field",
        "forbidden_alias",
        "identity_mismatch",
    }
    observed_mutation_kinds = {str(cell.get("mutation_kind") or "") for cell in cells}
    if not required_mutation_kinds.issubset(observed_mutation_kinds):
        failures.append(
            "static_mutation_class_missing:"
            + ",".join(sorted(required_mutation_kinds - observed_mutation_kinds))
        )
    return failures


def real_single_fault_validator_report(cells: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Execute every declared static cell through its current production owner."""

    receipts: list[dict[str, Any]] = []
    for cell in cells:
        mutation = str(cell["mutation_kind"])
        if cell.get("applicable") is False:
            receipts.append(
                {
                    "case_id": str(cell["case_id"]),
                    "source_contract_path": str(cell["source_contract_path"]),
                    "contract_family": str(cell["contract_family"]),
                    "contract_variant": str(cell.get("contract_variant") or "base"),
                    "mutation_kind": mutation,
                    "mutation_path": str(cell.get("mutation_path") or ""),
                    "execution_status": "excluded",
                    "structured_exclusion": _json_copy(cell.get("structured_exclusion") or {}),
                    "assertions": [],
                    "source_fingerprint": source_fingerprint(),
                }
            )
            continue
        if mutation == "identity_mismatch":
            receipts.append(_execute_static_identity_cell(cell))
            continue
        ledger, packet_id = _new_static_packet(
            family_id=str(cell["contract_family"]),
            profile_ids=tuple(str(item) for item in cell.get("profile_ids") or ()),
            profile_bindings=cell.get("profile_bindings") if isinstance(cell.get("profile_bindings"), Mapping) else {},
        )
        packet = ledger["packets"][packet_id]
        result_body = json.dumps(cell["payload"], sort_keys=True)
        expected_status = "allowed_candidate" if mutation == "valid_minimal_shape" else "mechanical_contract_blocked"
        assertions: list[dict[str, Any]] = []
        feedback: dict[str, Any] = {}
        observed_transition = "validator_only_no_state_change"
        repair_action: dict[str, Any] = {"action": "none", "reissue_packet_id": ""}
        observed_side_effects: dict[str, Any] = {
            "result_count_delta": 0,
            "fresh_packet_ids": [],
            "accepted_result_pointer": "",
            "downstream_release_packet_ids": [],
        }
        if mutation == "valid_minimal_shape":
            _payload, contract_error = runtime._json_payload_contract_check(packet, {"body": result_body})
            observed_status = "allowed_candidate" if contract_error is None else "mechanical_contract_blocked"
            feedback = contract_error.to_json() if contract_error is not None else {}
            assertions.append(
                _assertion("production_validator_outcome", observed_status == expected_status, observed_status)
            )
        else:
            lease_id = runtime.lease_agent(
                ledger,
                str(cell["responsibility"]),
                agent_id="formal-static-validator",
                packet_id=packet_id,
            )
            runtime.assign_packet(ledger, packet_id, lease_id)
            runtime.ack_lease(ledger, lease_id, packet_id)
            runtime.open_authorized_input_materials_for_role(ledger, packet_id, lease_id)
            initial_packet_ids = set(ledger["packets"])
            initial_result_count = len(ledger["results"])
            result_id = runtime.submit_result(ledger, lease_id, packet_id, result_body)
            result = ledger["results"][result_id]
            observed_status = str(result.get("status") or "")
            feedback = {
                "blocked_reason": result.get("blocked_reason"),
                "missing_required_fields": list(result.get("missing_required_fields") or []),
                "forbidden_fields_seen": list(result.get("forbidden_fields_seen") or []),
                "mechanical_contract_failure": result.get("mechanical_contract_failure"),
            }
            reissue_packet_id = _current_reissue_packet_id(ledger, packet_id)
            fresh_packet_ids = sorted(set(ledger["packets"]) - initial_packet_ids)
            downstream_release_ids = [fresh_id for fresh_id in fresh_packet_ids if fresh_id != reissue_packet_id]
            observed_transition = str(ledger["packets"][packet_id].get("status") or "")
            repair_action = {"action": "current_contract_reissue", "reissue_packet_id": reissue_packet_id}
            observed_side_effects = {
                "result_count_delta": len(ledger["results"]) - initial_result_count,
                "fresh_packet_ids": fresh_packet_ids,
                "accepted_result_pointer": str(ledger["packets"][packet_id].get("accepted_result_id") or ""),
                "downstream_release_packet_ids": downstream_release_ids,
            }
            expected_feedback_field = (
                "forbidden_fields_seen"
                if mutation in {"forbidden_field", "forbidden_alias"}
                else "missing_required_fields"
            )
            canonical_mutation_path = str(cell["mutation_path"]).split(" when ", 1)[0]
            feedback_paths = {str(item) for item in feedback[expected_feedback_field]}
            feedback_path_matched = (
                canonical_mutation_path in feedback_paths
                or any(
                    item.startswith(canonical_mutation_path + ".")
                    or item.startswith(canonical_mutation_path + "[]")
                    for item in feedback_paths
                )
                or canonical_mutation_path in str(feedback["blocked_reason"])
            )
            assertions.extend(
                [
                    _assertion("production_validator_outcome", observed_status == expected_status, observed_status),
                    _assertion(
                        "exact_feedback_names_mutation_path",
                        feedback_path_matched,
                        {
                            "canonical_mutation_path": canonical_mutation_path,
                            "structured_feedback_paths": sorted(feedback_paths),
                            "blocked_reason": feedback["blocked_reason"],
                        },
                    ),
                    _assertion("blocked_reason_is_actionable", bool(str(feedback["blocked_reason"] or "").strip()), feedback["blocked_reason"]),
                    _assertion("current_reissue_created", bool(reissue_packet_id), repair_action),
                    _assertion("original_superseded_after_repair", observed_transition == "superseded_after_repair", observed_transition),
                    _assertion("one_blocked_result_only", observed_side_effects["result_count_delta"] == 1, observed_side_effects),
                    _assertion("no_accepted_pointer", not observed_side_effects["accepted_result_pointer"], observed_side_effects),
                    _assertion("no_forbidden_downstream_release", not downstream_release_ids, observed_side_effects),
                ]
            )
        oracle = {
            "expected_status": expected_status,
            "expected_feedback_path": str(cell.get("mutation_path") or ""),
            "expected_repair": "none" if mutation == "valid_minimal_shape" else "current_contract_reissue",
            "expected_transition": (
                "validator_only_no_state_change" if mutation == "valid_minimal_shape" else "superseded_after_repair"
            ),
            "allowed_side_effects": [] if mutation == "valid_minimal_shape" else ["one_blocked_result", "one_current_reissue_packet"],
            "forbidden_side_effects": ["accepted_result_pointer", "downstream_stage_release"],
        }
        assertions.extend(
            [
                _assertion("oracle_status_equal", observed_status == oracle["expected_status"], observed_status),
                _assertion("oracle_repair_equal", repair_action["action"] == oracle["expected_repair"], repair_action),
                _assertion("oracle_transition_equal", observed_transition == oracle["expected_transition"], observed_transition),
                _assertion(
                    "oracle_forbidden_side_effects_absent",
                    not observed_side_effects["accepted_result_pointer"] and not observed_side_effects["downstream_release_packet_ids"],
                    observed_side_effects,
                ),
            ]
        )
        passed = all(assertion["ok"] for assertion in assertions)
        receipts.append(
            {
                "case_id": str(cell["case_id"]),
                "source_contract_path": str(cell["source_contract_path"]),
                "contract_family": str(cell["contract_family"]),
                "contract_variant": str(cell.get("contract_variant") or "base"),
                "mutation_kind": mutation,
                "mutation_path": str(cell.get("mutation_path") or ""),
                "validator_owner": "flowpilot_core_runtime.runtime._json_payload_contract_check+submit_result",
                "execution_status": "passed" if passed else "failed",
                "expected_status": expected_status,
                "observed_status": observed_status,
                "feedback": feedback,
                "repair_action": repair_action,
                "observed_transition": observed_transition,
                "observed_side_effects": observed_side_effects,
                "contract_oracle": oracle,
                "assertions": assertions,
                "source_fingerprint": source_fingerprint(),
            }
        )
    failed = [receipt for receipt in receipts if receipt["execution_status"] == "failed"]
    passed = [receipt for receipt in receipts if receipt["execution_status"] == "passed"]
    excluded = [receipt for receipt in receipts if receipt["execution_status"] == "excluded"]
    executed = passed + failed
    fault_receipts = [
        receipt for receipt in executed if receipt["mutation_kind"] != "valid_minimal_shape"
    ]
    return {
        "ok": len(receipts) == len(cells) and not failed,
        "declared_case_count": len(cells),
        "applicable_case_count": len(cells) - len(excluded),
        "excluded_case_count": len(excluded),
        "generated_case_count": len(cells),
        "selected_case_count": len(executed),
        "executed_case_count": len(executed),
        "passed_case_count": len(passed),
        "failed_case_count": len(failed),
        "stale_case_count": 0,
        "proof_backed_case_count": len(passed),
        "single_fault_case_count": len(fault_receipts),
        "valid_candidate_case_count": len(receipts) - len(fault_receipts),
        "source_fingerprint": source_fingerprint(),
        "receipts": receipts,
        "structured_exclusions": [receipt["structured_exclusion"] for receipt in excluded],
        "failed_receipts": failed[:20],
        "claim_boundary": (
            "Every declared static single mechanical mutation executes the production mechanical validator. "
            "Every static mutation executes its current production owner. Payload faults exercise runtime "
            "block/reissue behavior; valid minima remain validator-only candidates and are not counted as "
            "public dispatch/lease/ACK/open/submit evidence."
        ),
    }


@dataclass(frozen=True, slots=True)
class ExecutionCell:
    case_id: str
    source_contract_path: str
    contract_family: str
    validity: str
    response_source: str
    role: str
    timing_class: str

    @property
    def applicable_to_public_pipeline(self) -> bool:
        return self.timing_class != "before_ack"

    @property
    def structured_exclusion(self) -> dict[str, str] | None:
        if self.applicable_to_public_pipeline:
            return None
        return {
            "reason": "pre_ack_negative_cannot_traverse_ack_and_open_without destroying_the_fault",
            "source_reference": "OpenSpec executable public-pipeline requirement 6.3",
            "owner": "role_source_purity_and_runtime_preacceptance_negative_suites",
            "expiry_condition": "replace only when a distinct preacceptance public-path universe is declared",
        }

    def as_dict(self) -> dict[str, Any]:
        subject_class = {
            "task.node": "task_result",
            "flowguard_check.post_result": "flowguard_result",
            "review.any_current_subject": "review_subject_result",
        }[self.contract_family]
        evidence_class = {
            "task.node": "current_evidence_refs",
            "flowguard_check.post_result": "formal_flowguard_artifact",
            "review.any_current_subject": "authorized_subject_result",
        }[self.contract_family]
        read_set_class = (
            "no_required_result_reads"
            if self.contract_family == "task.node"
            else "required_result_reads_delivered"
        )
        submit_state = {
            "current": "first_submit",
            "before_ack": "preacceptance_submit",
            "stale_route": "post_route_mutation_submit",
            "duplicate_replay": "second_submit",
        }[self.timing_class]
        return {
            "case_id": self.case_id,
            "source_contract_path": self.source_contract_path,
            "contract_family": self.contract_family,
            "validity": self.validity,
            "response_source": self.response_source,
            "role": self.role,
            "timing_class": self.timing_class,
            "fault_class": self.response_source,
            "lifecycle_state": self.timing_class,
            "review_depth": (
                "delivered_stage_specific"
                if self.contract_family == "review.any_current_subject"
                else "not_a_reviewer_packet"
            ),
            "subject_class": subject_class,
            "evidence_class": evidence_class,
            "read_set_class": read_set_class,
            "open_state": "not_opened" if self.timing_class == "before_ack" else "opened_current",
            "submit_state": submit_state,
            "reissue_class": (
                "mechanical_reissue"
                if self.validity == "invalid" and self.timing_class == "current"
                else "no_reissue"
            ),
            "identity_class": (
                "stale_route_identity"
                if self.timing_class == "stale_route"
                else "consumed_lease_identity"
                if self.timing_class == "duplicate_replay"
                else "current_identity"
            ),
            "replay_class": "duplicate_replay" if self.timing_class == "duplicate_replay" else "first_attempt",
            "applicable_to_public_pipeline": self.applicable_to_public_pipeline,
            "structured_exclusion": self.structured_exclusion,
        }


@dataclass(frozen=True, slots=True)
class ContractOracle:
    oracle_id: str
    case_id: str
    owner: str
    validator_branch: str
    expected_statuses: tuple[str, ...]
    error_feedback_fields: tuple[str, ...]
    repair_fields: tuple[str, ...]
    forbidden_downstream_actions: tuple[str, ...]
    expected_state_transitions: tuple[str, ...]
    allowed_side_effects: tuple[str, ...]
    forbidden_side_effects: tuple[str, ...]
    expected_next_action_types: tuple[str, ...]

    def signature_payload(self) -> dict[str, Any]:
        return {
            "owner": self.owner,
            "validator_branch": self.validator_branch,
            "expected_statuses": list(self.expected_statuses),
            "error_feedback_fields": list(self.error_feedback_fields),
            "repair_fields": list(self.repair_fields),
            "forbidden_downstream_actions": list(self.forbidden_downstream_actions),
            "expected_state_transitions": list(self.expected_state_transitions),
            "allowed_side_effects": list(self.allowed_side_effects),
            "forbidden_side_effects": list(self.forbidden_side_effects),
            "expected_next_action_types": list(self.expected_next_action_types),
        }

    @property
    def oracle_signature(self) -> str:
        canonical = json.dumps(self.signature_payload(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        return {
            "oracle_id": self.oracle_id,
            "case_id": self.case_id,
            **self.signature_payload(),
            "oracle_signature": self.oracle_signature,
        }


def _valid_family_status_and_transition(family_id: str) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    if family_id == "task.node":
        return (("mechanically_valid",), ("result_submitted",), ("dispatch_current_role",))
    if family_id == "flowguard_check.post_result":
        return (("accepted",), ("accepted",), ("dispatch_current_role",))
    return (("accepted",), ("accepted",), ("terminal_complete",))


def contract_oracle_for_cell(cell: ExecutionCell) -> ContractOracle:
    owner = "flowpilot_core_runtime.runtime.submit_result"
    if cell.timing_class == "before_ack":
        values = {
            "validator_branch": "preacceptance_missing_ack",
            "expected_statuses": ("blocked",),
            "error_feedback_fields": ("mechanical_blockers", "quarantine_reason"),
            "repair_fields": (),
            "forbidden_downstream_actions": ("accepted_result_pointer_write", "flowguard_or_review_release"),
            "expected_state_transitions": ("result_blocked",),
            "allowed_side_effects": ("one_non_authoritative_blocked_result",),
            "forbidden_side_effects": ("accepted_result_pointer_write",),
            "expected_next_action_types": ("repair_packet",),
        }
    elif cell.timing_class == "stale_route":
        values = {
            "validator_branch": "preallocation_stale_route_rejection",
            "expected_statuses": ("rejected_without_result_allocation",),
            "error_feedback_fields": ("exception_message",),
            "repair_fields": (),
            "forbidden_downstream_actions": ("result_allocation", "accepted_result_pointer_write"),
            "expected_state_transitions": ("quarantined_after_route_mutation",),
            "allowed_side_effects": ("route_version_advance", "packet_quarantine"),
            "forbidden_side_effects": ("new_result_allocation", "accepted_result_pointer_write"),
            "expected_next_action_types": ("issue_task_packet",),
        }
    elif cell.timing_class == "duplicate_replay":
        _status, transitions, next_actions = _valid_family_status_and_transition(cell.contract_family)
        if cell.validity == "invalid":
            transitions = ("superseded_after_repair",)
            next_actions = ("dispatch_current_role",)
        values = {
            "validator_branch": "preallocation_duplicate_lease_rejection",
            "expected_statuses": ("rejected_without_result_allocation",),
            "error_feedback_fields": ("exception_message",),
            "repair_fields": (),
            "forbidden_downstream_actions": ("second_result_allocation", "second_accepted_result_pointer_write"),
            "expected_state_transitions": transitions,
            "allowed_side_effects": ("first_submission_only",),
            "forbidden_side_effects": ("second_result_allocation",),
            "expected_next_action_types": next_actions,
        }
    elif cell.validity == "invalid":
        missing = cell.response_source == "required_field_omission"
        values = {
            "validator_branch": (
                "required_field_validation" if missing else "forbidden_field_validation"
            ),
            "expected_statuses": ("mechanical_contract_blocked",),
            "error_feedback_fields": (
                "blocked_reason",
                "mechanical_contract_failure",
                "missing_required_fields" if missing else "mechanical_contract_failure.forbidden_fields_seen",
            ),
            "repair_fields": ("reissue_packet_id", "reissue.minimal_valid_shape"),
            "forbidden_downstream_actions": ("accepted_result_pointer_write", "subject_acceptance"),
            "expected_state_transitions": ("superseded_after_repair",),
            "allowed_side_effects": ("one_blocked_result", "one_current_reissue_packet"),
            "forbidden_side_effects": ("accepted_result_pointer_write",),
            "expected_next_action_types": ("dispatch_current_role",),
        }
    else:
        statuses, transitions, next_actions = _valid_family_status_and_transition(cell.contract_family)
        values = {
            "validator_branch": "current_contract_valid_submission",
            "expected_statuses": statuses,
            "error_feedback_fields": (),
            "repair_fields": (),
            "forbidden_downstream_actions": (),
            "expected_state_transitions": transitions,
            "allowed_side_effects": ("one_result_allocation", "owning_next_stage_release"),
            "forbidden_side_effects": ("cross_run_write", "second_result_allocation"),
            "expected_next_action_types": next_actions,
        }
    source = f"oracle/{cell.source_contract_path}"
    return ContractOracle(
        oracle_id=_stable_id("oracle", source),
        case_id=cell.case_id,
        owner=owner,
        **values,
    )


def oracle_equivalence_report(
    universe: Sequence[ExecutionCell],
    selected_case_ids: Sequence[str],
) -> dict[str, Any]:
    selected = {cell.case_id: cell for cell in universe if cell.case_id in set(selected_case_ids)}
    by_signature: dict[str, list[ExecutionCell]] = {}
    for cell in selected.values():
        by_signature.setdefault(contract_oracle_for_cell(cell).oracle_signature, []).append(cell)
    receipts: list[dict[str, Any]] = []
    uncovered: list[str] = []
    for cell in universe:
        if cell.case_id in selected:
            continue
        oracle = contract_oracle_for_cell(cell)
        representatives = by_signature.get(oracle.oracle_signature, [])
        if not representatives:
            uncovered.append(cell.case_id)
            continue
        representative = sorted(representatives, key=lambda item: item.case_id)[0]
        representative_oracle = contract_oracle_for_cell(representative)
        receipts.append(
            {
                "source_case_id": cell.case_id,
                "representative_case_id": representative.case_id,
                "oracle_signature": oracle.oracle_signature,
                "oracle_equal": oracle.as_dict()["oracle_signature"] == representative_oracle.as_dict()["oracle_signature"],
                "owner_equal": oracle.owner == representative_oracle.owner,
                "feedback_equal": oracle.error_feedback_fields == representative_oracle.error_feedback_fields,
                "transition_equal": oracle.expected_state_transitions == representative_oracle.expected_state_transitions,
                "side_effect_equal": (
                    oracle.allowed_side_effects == representative_oracle.allowed_side_effects
                    and oracle.forbidden_side_effects == representative_oracle.forbidden_side_effects
                ),
                "counted_as_executed": False,
            }
        )
    failures = [
        receipt["source_case_id"]
        for receipt in receipts
        if not all(
            receipt[field]
            for field in ("oracle_equal", "owner_equal", "feedback_equal", "transition_equal", "side_effect_equal")
        )
    ]
    representative_groups: dict[str, dict[str, Any]] = {}
    for receipt in receipts:
        representative_id = str(receipt["representative_case_id"])
        group = representative_groups.setdefault(
            representative_id,
            {
                "representative_case_id": representative_id,
                "oracle_signature": str(receipt["oracle_signature"]),
                "covered_source_case_ids": [],
                "counted_as_executed_case_ids": [representative_id],
            },
        )
        group["covered_source_case_ids"].append(str(receipt["source_case_id"]))
    for group in representative_groups.values():
        group["covered_source_case_ids"] = sorted(group["covered_source_case_ids"])
    return {
        "ok": not failures,
        "receipt_count": len(receipts),
        "uncompressed_not_run_case_ids": sorted(uncovered),
        "failures": failures,
        "receipts": receipts,
        "representative_receipts": sorted(
            representative_groups.values(), key=lambda row: str(row["representative_case_id"])
        ),
        "claim_boundary": "Equivalence receipts do not increment executed or passed counts.",
    }


def _roles_for_family(family_id: str) -> tuple[str, ...]:
    if family_id == "task.node":
        return ROLES
    if family_id == "flowguard_check.post_result":
        return ("flowguard_operator",)
    if family_id == "review.any_current_subject":
        return ("reviewer",)
    raise ValueError(f"unsupported execution family: {family_id}")


def build_execution_universe() -> tuple[ExecutionCell, ...]:
    cells: list[ExecutionCell] = []
    for family_id in EXECUTION_FAMILIES:
        for source, role, timing in product(
            RESPONSE_SOURCES,
            _roles_for_family(family_id),
            TIMING_CLASSES,
        ):
            validity = "valid" if source == "current_projection" else "invalid"
            source_path = f"public-submit/{family_id}/{role}/{source}/{timing}"
            cells.append(
                ExecutionCell(
                    case_id=_stable_id("exec", source_path),
                    source_contract_path=source_path,
                    contract_family=family_id,
                    validity=validity,
                    response_source=source,
                    role=role,
                    timing_class=timing,
                )
            )
    return tuple(sorted(cells, key=lambda cell: cell.case_id))


def _coverage_tokens(cell: ExecutionCell, axis_groups: Sequence[Sequence[str]]) -> set[tuple[str, ...]]:
    row = cell.as_dict()
    return {
        tuple(["axes", *axes, *[row[axis] for axis in axes]])
        for axes in axis_groups
    }


def _pair_axes() -> tuple[tuple[str, str], ...]:
    return tuple(combinations(SELECTION_AXES, 2))


def _mandatory_case_ids(universe: Sequence[ExecutionCell], mode: str) -> set[str]:
    mandatory: set[str] = set()
    requirements: list[tuple[str, str]] = []
    for axis in ("contract_family", "role", "timing_class", "response_source"):
        requirements.extend((axis, value) for value in sorted({str(getattr(cell, axis)) for cell in universe}))
    for axis, value in requirements:
        candidates = [cell for cell in universe if getattr(cell, axis) == value]
        preferred = sorted(
            candidates,
            key=lambda cell: (
                cell.timing_class != "current",
                cell.response_source != "current_projection",
                cell.case_id,
            ),
        )
        mandatory.add(preferred[0].case_id)
    if mode == "adversarial":
        for cell in universe:
            if cell.timing_class != "current" and cell.response_source != "current_projection":
                mandatory.add(cell.case_id)
    return mandatory


def select_execution_cases(
    universe: Sequence[ExecutionCell],
    *,
    mode: str,
) -> dict[str, Any]:
    if mode not in {"fast", "adversarial"}:
        raise ValueError("mode must be fast or adversarial")
    declared_universe = tuple(universe)
    universe = tuple(cell for cell in declared_universe if cell.applicable_to_public_pipeline)
    if not universe:
        raise ValueError("no applicable public-pipeline execution cells")
    pair_groups: tuple[tuple[str, ...], ...] = tuple(_pair_axes())
    triple_groups: tuple[tuple[str, ...], ...] = (
        tuple(CRITICAL_TRIPLE_AXES) if mode == "adversarial" else ()
    )
    required_tokens: set[tuple[str, ...]] = set()
    for cell in universe:
        required_tokens.update(_coverage_tokens(cell, (*pair_groups, *triple_groups)))

    by_id = {cell.case_id: cell for cell in universe}
    selected_ids = _mandatory_case_ids(universe, mode)
    covered_tokens: set[tuple[str, ...]] = set()
    for case_id in selected_ids:
        covered_tokens.update(_coverage_tokens(by_id[case_id], (*pair_groups, *triple_groups)))

    while required_tokens - covered_tokens:
        uncovered = required_tokens - covered_tokens
        candidates = [cell for cell in universe if cell.case_id not in selected_ids]
        scored = [
            (
                len(_coverage_tokens(cell, (*pair_groups, *triple_groups)) & uncovered),
                cell.case_id,
                cell,
            )
            for cell in candidates
        ]
        score, _case_id, winner = max(scored, key=lambda item: (item[0], item[1]))
        if score <= 0:
            break
        selected_ids.add(winner.case_id)
        covered_tokens.update(_coverage_tokens(winner, (*pair_groups, *triple_groups)))

    selected = tuple(cell for cell in universe if cell.case_id in selected_ids)
    uncovered_tokens = sorted(required_tokens - covered_tokens)
    return {
        "mode": mode,
        "declared_case_ids": sorted(cell.case_id for cell in declared_universe),
        "applicable_case_ids": sorted(cell.case_id for cell in universe),
        "excluded_cases": [
            {**cell.as_dict(), "exclusion": cell.structured_exclusion}
            for cell in declared_universe
            if not cell.applicable_to_public_pipeline
        ],
        "selected": selected,
        "selected_case_ids": sorted(selected_ids),
        "unselected_case_ids": sorted(cell.case_id for cell in universe if cell.case_id not in selected_ids),
        "pairwise_token_count": len(
            set().union(*(_coverage_tokens(cell, pair_groups) for cell in universe))
        ),
        "critical_triple_token_count": len(
            set().union(*(_coverage_tokens(cell, triple_groups) for cell in universe))
        ) if triple_groups else 0,
        "business_triple_groups": {
            name: {
                "axes": list(axes),
                "required_token_count": len(
                    set().union(*(_coverage_tokens(cell, (axes,)) for cell in universe))
                ),
                "covered_token_count": len(
                    set().union(*(_coverage_tokens(cell, (axes,)) for cell in selected))
                ),
            }
            for name, axes in BUSINESS_TRIPLE_AXES.items()
        } if triple_groups else {},
        "covered_token_count": len(covered_tokens),
        "required_token_count": len(required_tokens),
        "uncovered_tokens": [list(token) for token in uncovered_tokens],
        "selection_complete": not uncovered_tokens,
    }


def _new_task_packet(role: str) -> tuple[dict[str, Any], str, str]:
    ledger = runtime.new_ledger(
        "Exercise the formal AI result submission boundary",
        "Only current, acknowledged, contract-valid results may advance.",
    )
    ledger["run_root"] = tempfile.mkdtemp(prefix="flowpilot-formal-ai-exec-")
    ledger["startup_intake"] = {
        "status": "confirmed",
        "current_run_authority": True,
        "controller_may_read_body": False,
        "body_text_included": False,
        "startup_answers": {"background_collaboration_authorized": True},
    }
    runtime.create_route(ledger, "Formal AI execution route", ["exercise submit boundary"])
    packet_id = runtime.issue_task_packet(
        ledger,
        role,
        "Return one current structured result",
        "SEALED_FORMAL_AI_EXECUTION_BODY",
        route_scope="node",
    )
    lease_id = runtime.lease_agent(
        ledger,
        role,
        agent_id=f"formal-{role}",
        packet_id=packet_id,
    )
    runtime.assign_packet(ledger, packet_id, lease_id)
    return ledger, packet_id, lease_id


def _submit_base_task(ledger: dict[str, Any], packet_id: str, lease_id: str) -> str:
    runtime.ack_lease(ledger, lease_id, packet_id)
    runtime.open_authorized_input_materials_for_role(ledger, packet_id, lease_id)
    return runtime.submit_result(
        ledger,
        lease_id,
        packet_id,
        _role_result_body("Worker produced current formal execution evidence."),
        evidence_ids=["formal-ai-execution-base"],
    )


def _prepare_execution_packet(cell: ExecutionCell) -> tuple[dict[str, Any], str, str]:
    if cell.contract_family == "task.node":
        return _new_task_packet(cell.role)

    ledger, subject_packet_id, worker_lease = _base_ledger()
    _submit_base_task(ledger, subject_packet_id, worker_lease)
    flowguard_packet_id = _open_packet_by_kind(ledger, "flowguard_check")
    if cell.contract_family == "flowguard_check.post_result":
        flowguard_packet = ledger["packets"][flowguard_packet_id]
        lease_id = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            agent_id="formal-flowguard",
            packet_id=flowguard_packet_id,
        )
        runtime.assign_packet(ledger, flowguard_packet_id, lease_id)
        return ledger, flowguard_packet_id, lease_id

    _complete_open_packet(
        ledger,
        flowguard_packet_id,
        agent_id="formal-flowguard-setup",
        body=_flowguard_result_body("FlowGuard setup result passed for Reviewer execution."),
    )
    review_packet_id = _open_packet_by_kind(ledger, "review")
    review_lease = runtime.lease_agent(
        ledger,
        "reviewer",
        agent_id="formal-reviewer",
        packet_id=review_packet_id,
    )
    runtime.assign_packet(ledger, review_packet_id, review_lease)
    return ledger, review_packet_id, review_lease


def _new_unassigned_task_packet(role: str, *, run_root: Path) -> tuple[dict[str, Any], str]:
    ledger = runtime.new_ledger(
        "Exercise the formal public AI result submission boundary",
        "Only current checklist-derived results may advance through the public entrypoint.",
    )
    ledger["run_root"] = str(run_root)
    ledger["startup_intake"] = {
        "status": "confirmed",
        "current_run_authority": True,
        "controller_may_read_body": False,
        "body_text_included": False,
        "startup_answers": {"background_collaboration_authorized": True},
    }
    runtime.create_route(ledger, "Formal public AI execution route", ["exercise public submit boundary"])
    packet_id = runtime.issue_task_packet(
        ledger,
        role,
        "Return one current structured public result",
        "SEALED_FORMAL_PUBLIC_AI_BODY",
        route_scope="node",
    )
    return ledger, packet_id


def _prepare_public_execution_packet(cell: ExecutionCell, *, run_root: Path) -> tuple[dict[str, Any], str]:
    if cell.contract_family == "task.node":
        return _new_unassigned_task_packet(cell.role, run_root=run_root)

    ledger, subject_packet_id, worker_lease = _base_ledger()
    ledger["run_root"] = str(run_root)
    _submit_base_task(ledger, subject_packet_id, worker_lease)
    flowguard_packet_id = _open_packet_by_kind(ledger, "flowguard_check")
    if cell.contract_family == "flowguard_check.post_result":
        return ledger, flowguard_packet_id

    _complete_open_packet(
        ledger,
        flowguard_packet_id,
        agent_id="formal-flowguard-public-setup",
        body=_flowguard_result_body("FlowGuard setup passed for public Reviewer execution."),
    )
    return ledger, _open_packet_by_kind(ledger, "review")


def _persist_public_execution_ledger(
    root: Path,
    cell: ExecutionCell,
) -> tuple[run_shell.RunShell, str]:
    shell = run_shell.create_run_shell(
        root,
        "Formal public AI execution",
        "Dispatch, lease, ACK, open, checklist response, and public submit must all be current.",
        run_id=f"run-formal-{cell.case_id.rsplit(':', 1)[-1]}",
    )
    ledger, packet_id = _prepare_public_execution_packet(cell, run_root=shell.run_root)
    ledger["run_id"] = shell.run_id
    ledger["project_id"] = shell.run_id
    ledger["run_root"] = str(shell.run_root)
    ledger["projection_paths"] = {
        "ledger": str(shell.ledger_path),
        "events": str(shell.events_path),
        "console_status": str(shell.run_root / "console" / "status.json"),
    }
    run_shell.save_run_ledger(shell, ledger, guard_trigger="formal_public_fixture")
    return shell, packet_id


def _public_open_context(
    root: Path,
    cell: ExecutionCell,
) -> tuple[dict[str, Any], ContractDrivenFakeAIResponder, dict[str, Any]]:
    _shell, packet_id = _persist_public_execution_ledger(root, cell)
    ledger = run_shell.load_run_ledger(run_shell.load_run_shell(root))
    responsibility = str(ledger["packets"][packet_id]["envelope"]["responsibility"])
    dispatch = public_flowpilot.dispatch_current_role(
        root,
        packet_id=packet_id,
        responsibility=responsibility,
        host_kind="fake",
        agent_id=f"formal-public-{responsibility}",
    )
    if dispatch.get("ok") is not True:
        raise AssertionError(f"public dispatch failed: {dispatch}")
    lease_id = str(dispatch["lease_id"])
    ack = public_flowpilot.ack(root, lease_id=lease_id, packet_id=packet_id)
    opened = public_flowpilot.open_packet(root, lease_id=lease_id, packet_id=packet_id)
    if cell.contract_family == "flowguard_check.post_result":
        shell = run_shell.load_run_shell(root)
        ledger = run_shell.load_run_ledger(shell)
        from flowpilot_core_runtime_scenarios import _write_flowguard_evidence_artifact_for_packet

        _write_flowguard_evidence_artifact_for_packet(ledger, packet_id)
        run_shell.save_run_ledger(shell, ledger, guard_trigger="formal_public_flowguard_evidence")
    responder = ContractDrivenFakeAIResponder.from_open_packet_result(opened)
    checklist = opened["submission_checklist"]
    pipeline = {
        "stages_traversed": list(PUBLIC_PIPELINE_STAGES[:-1]),
        "dispatch_ok": dispatch.get("ok") is True,
        "lease_id": lease_id,
        "ack_ok": ack.get("ok") is True,
        "open_packet_schema": str(opened.get("schema_version") or ""),
        "submission_checklist_schema": str(checklist.get("schema_version") or ""),
        "submission_checklist_source": str(checklist.get("source") or ""),
        "responder_authority": "submission_checklist.v2",
        "packet_body_used_as_responder_authority": False,
        "contract_fingerprint": str(checklist.get("contract_fingerprint") or ""),
        "run_id": str(opened.get("run_id") or ""),
        "packet_id": packet_id,
        "responsibility": responsibility,
    }
    return opened, responder, pipeline


def _payload_from_public_open(
    responder: ContractDrivenFakeAIResponder,
    opened: Mapping[str, Any],
    cell: ExecutionCell,
) -> dict[str, Any]:
    review_trace: dict[str, Any] | None = None
    if cell.contract_family == "review.any_current_subject":
        review_payload = responder.review_window_behavior_payload(
            "reviewer_stage_specific_challenge_pass"
        )
        review_trace = _json_copy(review_payload.get("review_window_trace") or {})
    if cell.response_source == "current_projection":
        payload = (
            responder.review_window_behavior_payload("reviewer_stage_specific_challenge_pass")
            if cell.contract_family == "review.any_current_subject"
            else responder.legal_payload()
        )
    elif cell.response_source == "required_field_omission":
        payload = responder.missing_required_field_payload(responder.required_fields[0])
    elif cell.response_source == "forbidden_field_injection":
        payload = responder.forbidden_field_payload(responder.forbidden_fields[0])
    else:
        raise KeyError(f"unsupported public response source: {cell.response_source}")
    if review_trace is not None:
        payload["review_window_trace"] = review_trace
    return payload


def _execute_static_identity_cell(cell: Mapping[str, Any]) -> dict[str, Any]:
    identity_field = str(cell["mutation_path"])
    public_cell = next(
        candidate
        for candidate in build_execution_universe()
        if candidate.contract_family == "task.node"
        and candidate.role == "worker"
        and candidate.response_source == "current_projection"
        and candidate.timing_class == "current"
    )
    with tempfile.TemporaryDirectory(prefix="flowpilot-formal-identity-") as tmp_name:
        root = Path(tmp_name)
        opened, _responder, pipeline = _public_open_context(root, public_cell)
        shell = run_shell.load_run_shell(root)
        before = run_shell.load_run_ledger(shell)
        results_before = len(before.get("results", {}))
        packets_before = set(before.get("packets", {}))
        checklist = opened["submission_checklist"]
        if identity_field == "run_id":
            checklist[identity_field] = "run-stale-formal"
        elif identity_field == "packet_id":
            checklist[identity_field] = "packet-stale-formal"
        elif identity_field == "lease_id":
            checklist[identity_field] = "lease-stale-formal"
        elif identity_field == "route_version":
            checklist[identity_field] = int(checklist[identity_field]) + 1
        elif identity_field == "source_generation":
            checklist[identity_field] = int(checklist[identity_field]) + 1
        elif identity_field == "contract_fingerprint":
            checklist[identity_field] = "0" * 64
        else:
            raise KeyError(identity_field)
        exception_type = ""
        exception_message = ""
        try:
            ContractDrivenFakeAIResponder.from_open_packet_result(opened)
        except Exception as exc:
            exception_type = type(exc).__name__
            exception_message = str(exc)
        after = run_shell.load_run_ledger(shell)
        observed_side_effects = {
            "result_count_delta": len(after.get("results", {})) - results_before,
            "fresh_packet_ids": sorted(set(after.get("packets", {})) - packets_before),
            "submit_called": False,
        }
        assertions = [
            _assertion("identity_consumer_rejected", exception_type == "ValueError", exception_type),
            _assertion("identity_feedback_names_boundary", bool(exception_message), exception_message),
            _assertion("identity_rejected_before_submit", observed_side_effects["result_count_delta"] == 0, observed_side_effects),
            _assertion("identity_rejection_has_no_packet_side_effect", not observed_side_effects["fresh_packet_ids"], observed_side_effects),
            _assertion("responder_authority_is_current_checklist", pipeline["responder_authority"] == "submission_checklist.v2", pipeline),
        ]
        passed = all(assertion["ok"] for assertion in assertions)
        return {
            "case_id": str(cell["case_id"]),
            "source_contract_path": str(cell["source_contract_path"]),
            "contract_family": "task.node",
            "contract_variant": "public_checklist_identity",
            "mutation_kind": "identity_mismatch",
            "mutation_path": identity_field,
            "validator_owner": "ContractDrivenFakeAIResponder.from_open_packet_result",
            "execution_status": "passed" if passed else "failed",
            "expected_status": "rejected_before_submit",
            "observed_status": "rejected_before_submit" if exception_type else "unexpectedly_accepted",
            "feedback": {"exception_type": exception_type, "exception_message": exception_message},
            "repair_action": {"action": "open_current_packet_again", "reissue_packet_id": ""},
            "observed_transition": "open_packet_remains_current",
            "observed_side_effects": observed_side_effects,
            "contract_oracle": {
                "expected_status": "rejected_before_submit",
                "expected_repair": "open_current_packet_again",
                "expected_transition": "open_packet_remains_current",
                "forbidden_side_effects": ["result_allocation", "packet_creation", "submit_call"],
            },
            "public_pipeline": pipeline,
            "assertions": assertions,
            "source_fingerprint": source_fingerprint(),
        }


def _payload_for_cell(ledger: Mapping[str, Any], packet_id: str, cell: ExecutionCell) -> dict[str, Any]:
    packet = ledger["packets"][packet_id]
    contract = packet_result_contracts.effective_result_contract_from_envelope(packet["envelope"])
    payload = _json_copy(contract["minimal_valid_shape"])
    if cell.response_source == "required_field_omission":
        required = tuple(str(item) for item in contract.get("required_fields") or ())
        if not required:
            raise AssertionError(f"{cell.contract_family} has no required field to omit")
        payload.pop(_path_root(required[0]), None)
    elif cell.response_source == "forbidden_field_injection":
        forbidden = tuple(str(item) for item in contract.get("forbidden_fields") or ())
        if not forbidden:
            raise AssertionError(f"{cell.contract_family} has no forbidden field to inject")
        _inject_path(payload, forbidden[0], "FORBIDDEN_AI_FIELD")
    return payload


def _expected_reaction(cell: ExecutionCell) -> str:
    if cell.timing_class == "before_ack":
        return "blocked_missing_ack"
    if cell.timing_class in {"stale_route", "duplicate_replay"}:
        return "rejected_without_result_allocation"
    if cell.validity == "invalid":
        return "mechanical_contract_blocked"
    return "mechanically_valid_or_accepted"


def _open_current_packet(ledger: dict[str, Any], packet_id: str, lease_id: str) -> None:
    runtime.ack_lease(ledger, lease_id, packet_id)
    runtime.open_authorized_input_materials_for_role(ledger, packet_id, lease_id)
    packet = ledger["packets"][packet_id]
    if packet["envelope"].get("packet_kind") == "flowguard_check":
        # The formal FlowGuard report has one current file-backed evidence owner.
        from flowpilot_core_runtime_scenarios import _write_flowguard_evidence_artifact_for_packet

        _write_flowguard_evidence_artifact_for_packet(ledger, packet_id)


def _assertion(name: str, condition: bool, observed: Any) -> dict[str, Any]:
    return {"name": name, "ok": bool(condition), "observed": observed}


def _path_value(payload: Mapping[str, Any], path: str) -> Any:
    current: Any = payload
    for raw_part in path.split("."):
        key = raw_part.removesuffix("[]")
        if not isinstance(current, Mapping) or key not in current:
            return None
        current = current[key]
        if raw_part.endswith("[]"):
            if not isinstance(current, list) or not current:
                return None
            current = current[0]
    return current


def _oracle_field_missing(value: Any) -> bool:
    return value is None or value == "" or value == () or value == [] or value == {}


def _current_reissue_packet_id(ledger: Mapping[str, Any], blocked_packet_id: str) -> str:
    for event in reversed(list(ledger.get("events") or [])):
        if not isinstance(event, Mapping) or event.get("event_type") != "current_contract_reissue_packet_issued":
            continue
        payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
        if str(payload.get("blocked_packet_id") or "") == blocked_packet_id:
            return str(payload.get("fresh_packet_id") or "")
    return ""


def _observed_oracle_fields(
    ledger: Mapping[str, Any],
    *,
    packet_id: str,
    result_id: str,
    exception_message: str,
) -> dict[str, Any]:
    result = ledger.get("results", {}).get(result_id, {}) if result_id else {}
    reissue_packet_id = _current_reissue_packet_id(ledger, packet_id)
    reissue_packet = ledger.get("packets", {}).get(reissue_packet_id, {}) if reissue_packet_id else {}
    reissue_envelope = reissue_packet.get("envelope", {}) if isinstance(reissue_packet, Mapping) else {}
    reissue_contract = (
        packet_result_contracts.effective_result_contract_from_envelope(reissue_envelope)
        if isinstance(reissue_envelope, Mapping) and reissue_envelope
        else {}
    )
    return {
        "blocked_reason": result.get("blocked_reason"),
        "mechanical_contract_failure": result.get("mechanical_contract_failure"),
        "missing_required_fields": result.get("missing_required_fields"),
        "mechanical_blockers": result.get("mechanical_blockers"),
        "quarantine_reason": result.get("quarantine_reason"),
        "exception_message": exception_message or None,
        "reissue_packet_id": reissue_packet_id or None,
        "reissue": {
            "minimal_valid_shape": reissue_contract.get("minimal_valid_shape")
            if isinstance(reissue_contract, Mapping)
            else None,
        },
    }


def _side_effect_observation(
    ledger: Mapping[str, Any],
    *,
    cell: ExecutionCell,
    packet_id: str,
    result_id: str,
    first_result_id: str,
    results_before: int,
    results_after: int,
    initial_route_version: Any,
    initial_packet_ids: set[str],
    next_action_type: str,
) -> dict[str, Any]:
    packet = ledger.get("packets", {}).get(packet_id, {})
    result = ledger.get("results", {}).get(result_id, {}) if result_id else {}
    fresh_packet_ids = sorted(set(ledger.get("packets", {})) - initial_packet_ids)
    fresh_packet_kinds = [
        str((ledger["packets"][fresh_id].get("envelope") or {}).get("packet_kind") or "")
        for fresh_id in fresh_packet_ids
    ]
    reissue_packet_id = _current_reissue_packet_id(ledger, packet_id)
    original_accepted_pointer = str(packet.get("accepted_result_id") or "")
    accepted_pointer_written = bool(original_accepted_pointer or result.get("accepted") is True)
    observed_allocation = results_after > results_before
    second_allocation = bool(first_result_id) and observed_allocation
    observed_tokens: set[str] = set()
    if results_after - results_before == 1:
        observed_tokens.add("one_result_allocation")
    if result.get("non_authoritative") is True and str(result.get("status") or "") == "blocked":
        observed_tokens.add("one_non_authoritative_blocked_result")
    if ledger.get("active_route_version") != initial_route_version:
        observed_tokens.add("route_version_advance")
    if str(packet.get("status") or "") == "quarantined_after_route_mutation":
        observed_tokens.add("packet_quarantine")
    if first_result_id and not second_allocation:
        observed_tokens.add("first_submission_only")
    if str(result.get("status") or "") == "mechanical_contract_blocked":
        observed_tokens.add("one_blocked_result")
    if reissue_packet_id:
        observed_tokens.add("one_current_reissue_packet")
    if next_action_type in {"dispatch_current_role", "terminal_complete"} and cell.validity == "valid":
        observed_tokens.add("owning_next_stage_release")

    forbidden_actions = {
        "accepted_result_pointer_write": accepted_pointer_written,
        "flowguard_or_review_release": any(kind in {"flowguard_check", "review"} for kind in fresh_packet_kinds),
        "result_allocation": observed_allocation,
        "second_result_allocation": second_allocation,
        "second_accepted_result_pointer_write": second_allocation and accepted_pointer_written,
        "subject_acceptance": accepted_pointer_written,
    }
    forbidden_side_effects = {
        "accepted_result_pointer_write": accepted_pointer_written,
        "new_result_allocation": second_allocation,
        "second_result_allocation": second_allocation,
        "cross_run_write": False,  # Each formal case owns a fresh in-memory run root.
    }
    return {
        "observed_tokens": sorted(observed_tokens),
        "forbidden_downstream_actions_seen": {
            name: seen for name, seen in forbidden_actions.items() if seen
        },
        "forbidden_side_effects_seen": {
            name: seen for name, seen in forbidden_side_effects.items() if seen
        },
        "fresh_packet_ids": fresh_packet_ids,
        "fresh_packet_kinds": fresh_packet_kinds,
        "accepted_result_pointer": original_accepted_pointer,
        "result_count_delta": results_after - results_before,
    }


def execute_case(cell: ExecutionCell) -> dict[str, Any]:
    if not cell.applicable_to_public_pipeline:
        raise ValueError(f"excluded public-pipeline cell cannot execute as selected evidence: {cell.case_id}")
    started_clock = time.perf_counter()
    started_at = _utc_now()
    assertions: list[dict[str, Any]] = []
    result_id = ""
    first_result_id = ""
    exception_type = ""
    exception_message = ""
    observed_result_status = ""
    oracle = contract_oracle_for_cell(cell)
    with tempfile.TemporaryDirectory(prefix="flowpilot-formal-public-case-") as tmp_name:
        root = Path(tmp_name)
        opened, responder, public_pipeline = _public_open_context(root, cell)
        packet_id = str(public_pipeline["packet_id"])
        lease_id = str(public_pipeline["lease_id"])
        shell = run_shell.load_run_shell(root)
        ledger = run_shell.load_run_ledger(shell)
        initial_route_version = ledger.get("active_route_version")
        initial_packet_ids = set(ledger.get("packets", {}))
        packet_family = packet_result_contracts.packet_result_family_id(
            ledger["packets"][packet_id]["envelope"]
        )
        assertions.extend(
            [
                _assertion("executed_declared_contract_family", packet_family == cell.contract_family, packet_family),
                _assertion(
                    "public_pipeline_pre_submit_complete",
                    public_pipeline["stages_traversed"] == list(PUBLIC_PIPELINE_STAGES[:-1]),
                    public_pipeline,
                ),
                _assertion(
                    "submission_checklist_v2_is_responder_authority",
                    public_pipeline["submission_checklist_schema"]
                    == "black_box_flowpilot.submission_checklist.v2"
                    and public_pipeline["submission_checklist_source"] == "current_handoff_contract"
                    and public_pipeline["responder_authority"] == "submission_checklist.v2"
                    and public_pipeline["packet_body_used_as_responder_authority"] is False,
                    public_pipeline,
                ),
                _assertion(
                    "public_open_identity_bound",
                    responder.open_packet_identity is not None
                    and responder.open_packet_identity.get("packet_id") == packet_id
                    and responder.open_packet_identity.get("lease_id") == lease_id,
                    responder.open_packet_identity,
                ),
            ]
        )
        payload = _payload_from_public_open(responder, opened, cell)
        if cell.contract_family == "review.any_current_subject":
            delivered_rule = str(
                opened["packet"]["current_handoff_contract"]["review_window"]["review_depth_rule"]
            )
            assertions.append(
                _assertion(
                    "review_depth_rule_consumed_from_public_handoff",
                    _path_value(payload, "review_window_trace.review_depth_rule_consumed") == delivered_rule,
                    payload.get("review_window_trace"),
                )
            )
        body = json.dumps(payload, sort_keys=True)

        if cell.timing_class == "stale_route":
            runtime.create_route(ledger, "Mutated public route", ["new current public route"])
            run_shell.save_run_ledger(shell, ledger, guard_trigger="formal_public_stale_route")

        if cell.timing_class == "duplicate_replay":
            first_submission = public_flowpilot.submit_result(
                root,
                lease_id=lease_id,
                packet_id=packet_id,
                body=body,
            )
            first_result_id = str(first_submission["result_id"])
            ledger = run_shell.load_run_ledger(shell)
            first_status = str(ledger["results"][first_result_id].get("status") or "")
            assertions.append(
                _assertion(
                    "first_public_submission_created_real_result",
                    first_status in {"mechanically_valid", "accepted", "mechanical_contract_blocked"},
                    first_status,
                )
            )

        ledger = run_shell.load_run_ledger(shell)
        results_before = len(ledger.get("results", {}))
        try:
            submission = public_flowpilot.submit_result(
                root,
                lease_id=lease_id,
                packet_id=packet_id,
                body=body,
            )
            result_id = str(submission["result_id"])
        except Exception as exc:  # Public runtime rejection is an expected outcome for selected cells.
            exception_type = type(exc).__name__
            exception_message = str(exc)
        public_pipeline["stages_traversed"].append("submit_result")
        ledger = run_shell.load_run_ledger(shell)
        if result_id:
            observed_result_status = str(ledger["results"][result_id].get("status") or "")
        results_after = len(ledger.get("results", {}))
        assertions.append(
            _assertion(
                "complete_public_pipeline_traversed",
                public_pipeline["stages_traversed"] == list(PUBLIC_PIPELINE_STAGES),
                public_pipeline,
            )
        )

    expected = _expected_reaction(cell)
    if expected == "mechanically_valid_or_accepted":
        assertions.extend(
            [
                _assertion("result_allocated", bool(result_id), result_id),
                _assertion(
                    "valid_result_not_contract_blocked",
                    observed_result_status in {"mechanically_valid", "accepted"},
                    observed_result_status,
                ),
                _assertion("no_runtime_exception", not exception_type, exception_message),
            ]
        )
    elif expected == "mechanical_contract_blocked":
        result = ledger.get("results", {}).get(result_id, {})
        assertions.extend(
            [
                _assertion("blocked_result_allocated", bool(result_id), result_id),
                _assertion(
                    "invalid_contract_blocked",
                    observed_result_status == "mechanical_contract_blocked",
                    observed_result_status,
                ),
                _assertion("invalid_result_not_accepted", result.get("accepted") is False, result.get("accepted")),
                _assertion("no_runtime_exception", not exception_type, exception_message),
            ]
        )
    elif expected == "blocked_missing_ack":
        result = ledger.get("results", {}).get(result_id, {})
        blockers = list(result.get("mechanical_blockers") or [])
        assertions.extend(
            [
                _assertion("missing_ack_result_allocated", bool(result_id), result_id),
                _assertion("missing_ack_status_blocked", observed_result_status == "blocked", observed_result_status),
                _assertion("missing_ack_named", "missing_ack" in blockers, blockers),
                _assertion("missing_ack_non_authoritative", result.get("non_authoritative") is True, result.get("non_authoritative")),
            ]
        )
    else:
        rejection_markers = {
            "stale_route": ("stale_route_version", "quarantined_packet"),
            "duplicate_replay": ("duplicate_output_from_same_lease", "closed_or_inactive_lease"),
        }[cell.timing_class]
        assertions.extend(
            [
                _assertion("runtime_rejection_raised", exception_type == "BlackBoxRuntimeError", exception_type),
                _assertion(
                    "rejection_reason_specific",
                    any(marker in exception_message for marker in rejection_markers),
                    exception_message,
                ),
                _assertion("no_new_result_allocated", results_after == results_before, f"{results_before}->{results_after}"),
            ]
        )

    packet = ledger.get("packets", {}).get(packet_id, {})
    observed_transition = str(packet.get("status") or "")
    next_action = runtime.router_next_action(ledger).to_json()
    next_action_type = str(next_action.get("action_type") or "")
    oracle_fields = _observed_oracle_fields(
        ledger,
        packet_id=packet_id,
        result_id=result_id or first_result_id,
        exception_message=exception_message,
    )
    side_effects = _side_effect_observation(
        ledger,
        cell=cell,
        packet_id=packet_id,
        result_id=result_id,
        first_result_id=first_result_id,
        results_before=results_before,
        results_after=results_after,
        initial_route_version=initial_route_version,
        initial_packet_ids=initial_packet_ids,
        next_action_type=next_action_type,
    )
    observed_oracle_status = (
        "rejected_without_result_allocation"
        if exception_type and results_after == results_before
        else observed_result_status
    )
    missing_feedback = [
        path for path in oracle.error_feedback_fields if _oracle_field_missing(_path_value(oracle_fields, path))
    ]
    missing_repair = [
        path for path in oracle.repair_fields if _oracle_field_missing(_path_value(oracle_fields, path))
    ]
    forbidden_actions_seen = set(side_effects["forbidden_downstream_actions_seen"])
    forbidden_effects_seen = set(side_effects["forbidden_side_effects_seen"])
    observed_effect_tokens = set(side_effects["observed_tokens"])
    assertions.extend(
        [
            _assertion(
                "contract_oracle_status",
                observed_oracle_status in oracle.expected_statuses,
                {"expected": oracle.expected_statuses, "observed": observed_oracle_status},
            ),
            _assertion("contract_oracle_error_feedback", not missing_feedback, missing_feedback),
            _assertion("contract_oracle_repair_fields", not missing_repair, missing_repair),
            _assertion(
                "contract_oracle_state_transition",
                observed_transition in oracle.expected_state_transitions,
                {"expected": oracle.expected_state_transitions, "observed": observed_transition},
            ),
            _assertion(
                "contract_oracle_next_action",
                next_action_type in oracle.expected_next_action_types,
                {"expected": oracle.expected_next_action_types, "observed": next_action},
            ),
            _assertion(
                "contract_oracle_allowed_side_effects",
                set(oracle.allowed_side_effects).issubset(observed_effect_tokens),
                {"expected": oracle.allowed_side_effects, "observed": sorted(observed_effect_tokens)},
            ),
            _assertion(
                "contract_oracle_forbidden_downstream_actions",
                not (set(oracle.forbidden_downstream_actions) & forbidden_actions_seen),
                sorted(forbidden_actions_seen),
            ),
            _assertion(
                "contract_oracle_forbidden_side_effects",
                not (set(oracle.forbidden_side_effects) & forbidden_effects_seen),
                sorted(forbidden_effects_seen),
            ),
        ]
    )

    passed = bool(assertions) and all(assertion["ok"] for assertion in assertions)
    return {
        **cell.as_dict(),
        "execution_status": "passed" if passed else "failed",
        "expected_reaction": expected,
        "observed_result_status": observed_result_status,
        "result_id": result_id,
        "exception_type": exception_type,
        "exception_message": exception_message,
        "contract_oracle": oracle.as_dict(),
        "oracle_signature": oracle.oracle_signature,
        "observed_oracle_fields": oracle_fields,
        "observed_transition": observed_transition,
        "observed_next_action": next_action,
        "observed_side_effects": side_effects,
        "public_pipeline": public_pipeline,
        "proof_backed": passed
        and public_pipeline["stages_traversed"] == list(PUBLIC_PIPELINE_STAGES)
        and public_pipeline["responder_authority"] == "submission_checklist.v2",
        "assertions": assertions,
        "results_before_observed_submission": results_before,
        "results_after_observed_submission": results_after,
        "source_fingerprint": source_fingerprint(),
        "started_at": started_at,
        "ended_at": _utc_now(),
        "duration_ms": round((time.perf_counter() - started_clock) * 1000.0, 3),
    }


def _fuzz_task_cell() -> ExecutionCell:
    return next(
        cell
        for cell in build_execution_universe()
        if cell.contract_family == "task.node"
        and cell.role == "worker"
        and cell.response_source == "current_projection"
        and cell.timing_class == "current"
    )


def _fuzz_body_profiles(valid_payload: Mapping[str, Any]) -> dict[str, tuple[str, str]]:
    large_payload = _json_copy(valid_payload)
    large_payload["pm_visible_summary"] = ["x" * 70_000]
    deep: dict[str, Any] = {"leaf": "value"}
    for index in range(80):
        deep = {f"level_{index:02d}": deep}
    deep_payload = _json_copy(valid_payload)
    deep_payload["unknown_deep_branch"] = deep
    return {
        "duplicate_json_keys": (
            '{"decision":"block","decision":"pass","pm_visible_summary":["duplicate-key fuzz"],'
            '"current_evidence_refs":["fuzz"]}',
            "mechanically_valid",
        ),
        "invalid_numeric_nan": (
            '{"decision":NaN,"pm_visible_summary":["NaN fuzz"],"current_evidence_refs":["fuzz"]}',
            "mechanical_contract_blocked",
        ),
        "invalid_numeric_infinity": (
            '{"decision":Infinity,"pm_visible_summary":["Infinity fuzz"],"current_evidence_refs":["fuzz"]}',
            "mechanical_contract_blocked",
        ),
        "utf8_bom": ("\ufeff" + json.dumps(valid_payload, sort_keys=True), "mechanical_contract_blocked"),
        "invalid_unicode_scalar": (
            '{"decision":"pass","pm_visible_summary":["\ud800"],"current_evidence_refs":["fuzz"]}',
            "rejected_without_result_allocation",
        ),
        "top_level_non_object": ("[]", "mechanical_contract_blocked"),
        "prose_wrapper": (
            "Here is the result: " + json.dumps(valid_payload, sort_keys=True),
            "mechanical_contract_blocked",
        ),
        "markdown_wrapper": (
            "```json\n" + json.dumps(valid_payload, sort_keys=True) + "\n```",
            "mechanical_contract_blocked",
        ),
        "excessive_size": (json.dumps(large_payload, sort_keys=True), "mechanically_valid"),
        "excessive_depth": (json.dumps(deep_payload, sort_keys=True), "mechanically_valid"),
    }


def _duplicate_json_keys(body: str) -> list[str]:
    duplicates: list[str] = []

    def reject_silent_overwrite(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                duplicates.append(key)
            result[key] = value
        return result

    try:
        json.loads(body, object_pairs_hook=reject_silent_overwrite)
    except (TypeError, ValueError):
        return []
    return duplicates


def _execute_body_fuzz(profile_id: str, body: str, expected_status: str) -> dict[str, Any]:
    started = time.perf_counter()
    cell = _fuzz_task_cell()
    ledger, packet_id, lease_id = _prepare_execution_packet(cell)
    _open_current_packet(ledger, packet_id, lease_id)
    results_before = len(ledger["results"])
    result_id = ""
    exception_type = ""
    exception_message = ""
    try:
        result_id = runtime.submit_result(ledger, lease_id, packet_id, body)
    except Exception as exc:  # The encoding profile intentionally reaches the public-function rejection path.
        exception_type = type(exc).__name__
        exception_message = str(exc)
    results_after = len(ledger["results"])
    result = ledger["results"].get(result_id, {})
    observed_status = (
        "rejected_without_result_allocation"
        if exception_type and results_after == results_before
        else str(result.get("status") or "")
    )
    reissue_packet_id = _current_reissue_packet_id(ledger, packet_id)
    assertions = [
        _assertion("declared_parser_or_mechanical_outcome", observed_status == expected_status, observed_status),
    ]
    duplicate_keys = _duplicate_json_keys(body) if profile_id == "duplicate_json_keys" else []
    if profile_id == "duplicate_json_keys":
        assertions.append(
            _assertion(
                "duplicate_key_hook_detects_silent_json_overwrite",
                duplicate_keys == ["decision"],
                duplicate_keys,
            )
        )
    if expected_status == "mechanical_contract_blocked":
        assertions.extend(
            [
                _assertion("blocked_fuzz_allocates_one_result", results_after - results_before == 1, results_after - results_before),
                _assertion("blocked_fuzz_reissues_current_packet", bool(reissue_packet_id), reissue_packet_id),
                _assertion(
                    "blocked_fuzz_supersedes_subject_packet",
                    ledger["packets"][packet_id].get("status") == "superseded_after_repair",
                    ledger["packets"][packet_id].get("status"),
                ),
            ]
        )
    elif expected_status == "mechanically_valid":
        assertions.extend(
            [
                _assertion("accepted_parser_fuzz_allocates_one_result", results_after - results_before == 1, results_after - results_before),
                _assertion("accepted_parser_fuzz_does_not_reissue", not reissue_packet_id, reissue_packet_id),
                _assertion(
                    "accepted_parser_fuzz_advances_packet",
                    ledger["packets"][packet_id].get("status") == "result_submitted",
                    ledger["packets"][packet_id].get("status"),
                ),
            ]
        )
    else:
        assertions.extend(
            [
                _assertion("parser_exception_precedes_allocation", results_after == results_before, f"{results_before}->{results_after}"),
                _assertion("parser_exception_is_explicit", bool(exception_type), exception_type),
            ]
        )
    passed = all(assertion["ok"] for assertion in assertions)
    return {
        "case_id": _stable_id("fuzz", f"public-submit/task.node/{profile_id}"),
        "profile_id": profile_id,
        "source_contract_path": f"public-submit/task.node/fuzz/{profile_id}",
        "execution_status": "passed" if passed else "failed",
        "expected_status": expected_status,
        "observed_status": observed_status,
        "result_id": result_id,
        "result_created": bool(result_id),
        "reissue_packet_id": reissue_packet_id,
        "state_transition": str(ledger["packets"][packet_id].get("status") or ""),
        "next_action": runtime.router_next_action(ledger).to_json(),
        "exception_type": exception_type,
        "exception_message": exception_message,
        "duplicate_key_preflight": {
            "object_pairs_hook_used": profile_id == "duplicate_json_keys",
            "duplicate_keys": duplicate_keys,
            "plain_json_loads_is_not_duplicate_evidence": profile_id == "duplicate_json_keys",
        },
        "assertions": assertions,
        "duration_ms": round((time.perf_counter() - started) * 1000.0, 3),
    }


def _execute_replay_fuzz(*, concurrent: bool) -> dict[str, Any]:
    started = time.perf_counter()
    profile_id = "concurrent_double_submit" if concurrent else "sequential_replay"
    cell = _fuzz_task_cell()
    ledger, packet_id, lease_id = _prepare_execution_packet(cell)
    _open_current_packet(ledger, packet_id, lease_id)
    body = json.dumps(_payload_for_cell(ledger, packet_id, cell), sort_keys=True)
    outcomes: list[dict[str, str]] = []
    outcome_lock = threading.Lock()

    def submit_once(barrier: threading.Barrier | None = None) -> None:
        if barrier is not None:
            barrier.wait()
        try:
            result_id = runtime.submit_result(ledger, lease_id, packet_id, body)
            row = {"kind": "result", "value": result_id}
        except Exception as exc:  # One duplicate rejection is the expected second outcome.
            row = {"kind": "exception", "value": f"{type(exc).__name__}:{exc}"}
        with outcome_lock:
            outcomes.append(row)

    if concurrent:
        barrier = threading.Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(submit_once, barrier) for _index in range(2)]
            for future in futures:
                future.result()
    else:
        submit_once()
        submit_once()
    result_rows = [row for row in outcomes if row["kind"] == "result"]
    exception_rows = [row for row in outcomes if row["kind"] == "exception"]
    assertions = [
        _assertion("exactly_one_result_wins", len(result_rows) == 1, outcomes),
        _assertion("exactly_one_duplicate_is_rejected", len(exception_rows) == 1, outcomes),
        _assertion("runtime_persists_exactly_one_result", len(ledger["results"]) == 1, list(ledger["results"])),
        _assertion(
            "duplicate_rejection_is_specific",
            bool(exception_rows) and any(
                marker in exception_rows[0]["value"]
                for marker in ("duplicate_output_from_same_lease", "closed_or_inactive_lease")
            ),
            exception_rows,
        ),
    ]
    passed = all(assertion["ok"] for assertion in assertions)
    return {
        "case_id": _stable_id("fuzz", f"public-submit/task.node/{profile_id}"),
        "profile_id": profile_id,
        "source_contract_path": f"public-submit/task.node/fuzz/{profile_id}",
        "execution_status": "passed" if passed else "failed",
        "expected_status": "one_result_plus_one_rejection",
        "observed_status": "one_result_plus_one_rejection" if passed else "concurrency_contract_failed",
        "outcomes": sorted(outcomes, key=lambda row: (row["kind"], row["value"])),
        "result_created": bool(result_rows),
        "state_transition": str(ledger["packets"][packet_id].get("status") or ""),
        "next_action": runtime.router_next_action(ledger).to_json(),
        "assertions": assertions,
        "duration_ms": round((time.perf_counter() - started) * 1000.0, 3),
    }


def _execute_cross_run_fuzz() -> dict[str, Any]:
    started = time.perf_counter()
    cell = _fuzz_task_cell()
    source_ledger, source_packet_id, source_lease_id = _prepare_execution_packet(cell)
    target_ledger, target_packet_id, target_lease_id = _prepare_execution_packet(cell)
    _open_current_packet(source_ledger, source_packet_id, source_lease_id)
    _open_current_packet(target_ledger, target_packet_id, target_lease_id)
    body = json.dumps(_payload_for_cell(source_ledger, source_packet_id, cell), sort_keys=True)
    results_before = len(target_ledger["results"])
    result_id = ""
    exception = ""
    try:
        # The direct in-memory surface receives colliding local ids and has no run-id argument.
        result_id = runtime.submit_result(target_ledger, source_lease_id, source_packet_id, body)
    except Exception as exc:
        exception = f"{type(exc).__name__}:{exc}"
    results_after = len(target_ledger["results"])
    accepted_by_direct_surface = bool(result_id) and results_after == results_before + 1
    assertions = [
        _assertion(
            "cross_run_direct_surface_outcome_recorded",
            accepted_by_direct_surface or bool(exception),
            {"result_id": result_id, "exception": exception},
        ),
        _assertion("source_ledger_was_not_mutated", not source_ledger["results"], list(source_ledger["results"])),
    ]
    passed = all(assertion["ok"] for assertion in assertions)
    return {
        "case_id": _stable_id("fuzz", "public-submit/task.node/cross-run-identity-collision"),
        "profile_id": "cross_run_identity_collision",
        "source_contract_path": "public-submit/task.node/fuzz/cross_run_identity_collision",
        "execution_status": "passed" if passed else "failed",
        "expected_status": "explicit_direct_surface_outcome_and_backfeed",
        "observed_status": "accepted_by_run_local_direct_surface" if accepted_by_direct_surface else "rejected",
        "result_created": bool(result_id),
        "result_id": result_id,
        "exception_message": exception,
        "assertions": assertions,
        "claim_boundary": (
            "This direct function has no run-id parameter; public CLI/root isolation remains owned by the "
            "end-to-end synthetic chaos suite and this acceptance is mandatory problem backfeed."
        ),
        "duration_ms": round((time.perf_counter() - started) * 1000.0, 3),
    }


def run_deterministic_fuzz() -> dict[str, Any]:
    cell = _fuzz_task_cell()
    ledger, packet_id, _lease_id = _prepare_execution_packet(cell)
    valid_payload = _payload_for_cell(ledger, packet_id, cell)
    profiles = _fuzz_body_profiles(valid_payload)
    receipts = [
        _execute_body_fuzz(profile_id, body, expected_status)
        for profile_id, (body, expected_status) in profiles.items()
    ]
    receipts.extend(
        [
            _execute_replay_fuzz(concurrent=False),
            _execute_replay_fuzz(concurrent=True),
            _execute_cross_run_fuzz(),
        ]
    )
    by_id = {str(receipt["profile_id"]): receipt for receipt in receipts}
    missing = sorted(set(FUZZ_PROFILE_IDS) - set(by_id))
    duplicate_ids = len(by_id) != len(receipts)
    failed = [receipt for receipt in receipts if receipt["execution_status"] != "passed"]
    return {
        "ok": not missing and not duplicate_ids and not failed,
        "declared_profile_count": len(FUZZ_PROFILE_IDS),
        "executed_profile_count": len(receipts),
        "passed_profile_count": len(receipts) - len(failed),
        "failed_profile_count": len(failed),
        "missing_profile_ids": missing,
        "duplicate_profile_ids": duplicate_ids,
        "receipts": sorted(receipts, key=lambda receipt: str(receipt["profile_id"])),
        "failed_receipts": failed[:20],
    }


def _execute_wrong_role_historical() -> dict[str, Any]:
    cell = _fuzz_task_cell()
    ledger, packet_id, lease_id = _prepare_execution_packet(cell)
    _open_current_packet(ledger, packet_id, lease_id)
    wrong_lease_id = runtime.lease_agent(ledger, "reviewer", agent_id="historical-wrong-role")
    results_before = len(ledger["results"])
    exception = ""
    try:
        runtime.submit_result(
            ledger,
            wrong_lease_id,
            packet_id,
            json.dumps(_payload_for_cell(ledger, packet_id, cell), sort_keys=True),
        )
    except Exception as exc:
        exception = f"{type(exc).__name__}:{exc}"
    passed = "wrong_lease_for_packet" in exception and len(ledger["results"]) == results_before
    return {
        "execution_status": "passed" if passed else "failed",
        "exception": exception,
        "result_count_delta": len(ledger["results"]) - results_before,
    }


def historical_miss_registry(fuzz_report: Mapping[str, Any]) -> dict[str, Any]:
    wrong_role = _execute_wrong_role_historical()
    fuzz_receipts = {
        str(receipt.get("profile_id") or ""): receipt
        for receipt in fuzz_report.get("receipts", [])
        if isinstance(receipt, Mapping)
    }
    rows = [
        {
            "historical_miss_id": "databank_runtime_miss",
            "owner": "tests/test_flowpilot_historical_live_run_replay.py",
            "execution_owner": "formal_ai_submit_historical_regressions",
            "execution_status": "owned_by_registered_adversarial_child",
        },
        {
            "historical_miss_id": "zero_forbidden_coverage",
            "owner": "static_mechanical_universe.forbidden_field",
            "execution_owner": "formal_ai_submit_adversarial_runner",
            "execution_status": "passed" if any(
                cell["mutation_kind"] == "forbidden_field" for cell in build_static_contract_universe()
            ) else "failed",
        },
        {
            "historical_miss_id": "checklist_bypass",
            "owner": "tests/test_flowpilot_new_entrypoint.py",
            "execution_owner": "formal_ai_submit_historical_regressions",
            "execution_status": "owned_by_registered_adversarial_child",
        },
        {
            "historical_miss_id": "static_reviewer_policy",
            "owner": "tests/test_flowpilot_contract_driven_fake_ai_open_packet.py",
            "execution_owner": "formal_ai_submit_historical_regressions",
            "execution_status": "owned_by_registered_adversarial_child",
        },
        {
            "historical_miss_id": "wrong_role_submission",
            "owner": "flowpilot_core_runtime.runtime.submit_result",
            "execution_owner": "formal_ai_submit_adversarial_runner",
            **wrong_role,
        },
        {
            "historical_miss_id": "daemon_replay_positive_path",
            "owner": "tests/test_flowpilot_current_contract_cartesian_matrix.py",
            "execution_owner": "formal_ai_submit_historical_regressions",
            "execution_status": "owned_by_registered_adversarial_child",
        },
        {
            "historical_miss_id": "public_runtime_discrepancy",
            "owner": "deterministic_fuzz.public_submit",
            "execution_owner": "formal_ai_submit_adversarial_runner",
            "execution_status": (
                "passed"
                if fuzz_receipts.get("cross_run_identity_collision", {}).get("execution_status") == "passed"
                else "failed"
            ),
        },
    ]
    observed_ids = {str(row["historical_miss_id"]) for row in rows}
    failures = [
        str(row["historical_miss_id"])
        for row in rows
        if row["execution_status"] not in {"passed", "owned_by_registered_adversarial_child"}
    ]
    return {
        "ok": observed_ids == set(HISTORICAL_MISS_IDS) and not failures,
        "mandatory_case_ids": list(HISTORICAL_MISS_IDS),
        "registered_case_count": len(rows),
        "locally_executed_case_count": sum(row["execution_status"] == "passed" for row in rows),
        "delegated_child_case_count": sum(
            row["execution_status"] == "owned_by_registered_adversarial_child" for row in rows
        ),
        "failures": failures,
        "receipts": rows,
        "claim_boundary": (
            "Delegated historical children are mandatory tier commands; this runner does not count them as "
            "locally executed or passed evidence."
        ),
    }


def observed_problem_backfeed(
    fuzz_report: Mapping[str, Any],
    historical_report: Mapping[str, Any],
) -> dict[str, Any]:
    rows = [
        {
            "problem_id": f"observed-problem:{miss_id}",
            "source": "historical_miss_registry",
            "owner": next(
                (
                    str(row.get("owner") or "")
                    for row in historical_report.get("receipts", [])
                    if isinstance(row, Mapping) and row.get("historical_miss_id") == miss_id
                ),
                "unbound",
            ),
            "required_route": "flowguard-model-miss-review",
            "disposition": "pinned_regression",
        }
        for miss_id in HISTORICAL_MISS_IDS
    ]
    fuzz_by_id = {
        str(row.get("profile_id") or ""): row
        for row in fuzz_report.get("receipts", [])
        if isinstance(row, Mapping)
    }
    for profile_id in (
        "duplicate_json_keys",
        "excessive_size",
        "excessive_depth",
        "cross_run_identity_collision",
    ):
        receipt = fuzz_by_id.get(profile_id, {})
        rows.append(
            {
                "problem_id": f"observed-problem:fuzz:{profile_id}",
                "source": str(receipt.get("source_contract_path") or ""),
                "owner": "flowpilot_core_runtime.runtime.submit_result",
                "observed_status": str(receipt.get("observed_status") or ""),
                "required_route": (
                    "public-cli-cross-run-e2e" if profile_id == "cross_run_identity_collision" else "parser-boundary-policy-review"
                ),
                "disposition": "open_policy_or_public_boundary_followup",
                "blocks_this_execution_oracle": False,
            }
        )
    return {
        "row_count": len(rows),
        "all_historical_misses_backfed": all(
            f"observed-problem:{miss_id}" in {row["problem_id"] for row in rows}
            for miss_id in HISTORICAL_MISS_IDS
        ),
        "rows": rows,
    }


def benchmark_public_path_cases(
    *,
    case_count: int = BENCHMARK_CASE_COUNT,
    workers: int = BENCHMARK_PARALLEL_WORKERS,
) -> dict[str, Any]:
    if not 30 <= case_count <= 80:
        raise ValueError("public-path benchmark must execute 30-80 cases")
    if workers != 2:
        raise ValueError("Windows formal public-path benchmark is fixed at two workers")
    universe = build_execution_universe()
    selected_ids = set(select_execution_cases(universe, mode="adversarial")["selected_case_ids"])
    candidates = [cell for cell in universe if cell.case_id in selected_ids]
    sample = tuple(sorted(candidates, key=lambda cell: cell.case_id)[:case_count])
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        receipts = list(pool.map(execute_case, sample))
    wall_seconds = time.perf_counter() - started
    shard_rows: list[dict[str, Any]] = []
    for shard_index in range(BENCHMARK_SHARD_COUNT):
        shard_receipts = [
            receipt for index, receipt in enumerate(receipts) if index % BENCHMARK_SHARD_COUNT == shard_index
        ]
        shard_rows.append(
            {
                "shard_id": f"benchmark-{shard_index + 1:02d}",
                "case_count": len(shard_receipts),
                "sum_case_duration_ms": round(sum(float(row["duration_ms"]) for row in shard_receipts), 3),
                "max_case_duration_ms": round(max(float(row["duration_ms"]) for row in shard_receipts), 3),
                "case_ids": [str(row["case_id"]) for row in shard_receipts],
                "proof_backed_case_count": sum(row.get("proof_backed") is True for row in shard_receipts),
                "public_pipeline_complete": all(
                    row.get("public_pipeline", {}).get("stages_traversed") == list(PUBLIC_PIPELINE_STAGES)
                    for row in shard_receipts
                ),
            }
        )
    failed = [receipt for receipt in receipts if receipt["execution_status"] != "passed"]
    return {
        "ok": len(receipts) == case_count and not failed and all(
            row.get("proof_backed") is True
            and row.get("public_pipeline", {}).get("stages_traversed") == list(PUBLIC_PIPELINE_STAGES)
            and row.get("public_pipeline", {}).get("responder_authority") == "submission_checklist.v2"
            for row in receipts
        ),
        "platform": platform.platform(),
        "case_count": len(receipts),
        "worker_count": workers,
        "windows_recommended_parallelism_confirmed": workers == 2,
        "wall_seconds": round(wall_seconds, 3),
        "sum_case_duration_ms": round(sum(float(row["duration_ms"]) for row in receipts), 3),
        "max_case_duration_ms": round(max(float(row["duration_ms"]) for row in receipts), 3),
        "case_timings": [
            {
                "case_id": str(row["case_id"]),
                "duration_ms": float(row["duration_ms"]),
                "public_pipeline_stages": list(row["public_pipeline"]["stages_traversed"]),
                "submission_checklist_schema": str(row["public_pipeline"]["submission_checklist_schema"]),
                "responder_authority": str(row["public_pipeline"]["responder_authority"]),
                "proof_backed": row.get("proof_backed") is True,
            }
            for row in receipts
        ],
        "shards": shard_rows,
        "failed_case_ids": [str(row["case_id"]) for row in failed],
        "recommended_formal_parallel_workers": 2,
        "source_fingerprint": source_fingerprint(),
    }


def run_execution_closure(*, mode: str, budget_seconds: float | None = None) -> dict[str, Any]:
    run_started = time.perf_counter()
    if mode not in {"fast", "adversarial"}:
        raise ValueError("mode must be fast or adversarial")
    approved_budget = float(
        budget_seconds
        if budget_seconds is not None
        else (FAST_BUDGET_SECONDS if mode == "fast" else ADVERSARIAL_BUDGET_SECONDS)
    )
    static_cells = build_static_contract_universe()
    static_failures = static_universe_failures(static_cells)
    single_fault_validator = real_single_fault_validator_report(static_cells)
    collision_audit = audited_collision_repair_report()
    universe = build_execution_universe()
    execution_identity_failures = case_id_collision_failures([cell.as_dict() for cell in universe])
    selection = select_execution_cases(universe, mode=mode)
    selected_ids = set(selection["selected_case_ids"])
    excluded_ids = {
        cell.case_id for cell in universe if not cell.applicable_to_public_pipeline
    }
    receipts: list[dict[str, Any]] = []
    for cell in universe:
        if cell.case_id in excluded_ids:
            receipts.append(
                {
                    **cell.as_dict(),
                    "execution_status": "excluded",
                    "expected_reaction": _expected_reaction(cell),
                    "assertions": [],
                    "source_fingerprint": source_fingerprint(),
                    "structured_exclusion": cell.structured_exclusion,
                    "proof_backed": False,
                }
            )
        elif cell.case_id in selected_ids:
            receipts.append(execute_case(cell))
        else:
            receipts.append(
                {
                    **cell.as_dict(),
                    "execution_status": "not_run",
                    "expected_reaction": _expected_reaction(cell),
                    "assertions": [],
                    "source_fingerprint": source_fingerprint(),
                    "not_run_reason": f"not_selected_by_{mode}_covering_array",
                    "proof_backed": False,
                }
            )
    passed = [row for row in receipts if row["execution_status"] == "passed"]
    failed = [row for row in receipts if row["execution_status"] == "failed"]
    not_run = [row for row in receipts if row["execution_status"] == "not_run"]
    excluded = [row for row in receipts if row["execution_status"] == "excluded"]
    stale = [row for row in receipts if row.get("source_fingerprint") != source_fingerprint()]
    proof_backed = [row for row in receipts if row.get("proof_backed") is True]
    executed_ids = {row["case_id"] for row in passed + failed}
    selection_receipt_match = executed_ids == selected_ids
    equivalence = oracle_equivalence_report(universe, sorted(selected_ids))
    if mode == "adversarial":
        fuzz = run_deterministic_fuzz()
        historical = historical_miss_registry(fuzz)
        backfeed = observed_problem_backfeed(fuzz, historical)
        benchmark = benchmark_public_path_cases()
    else:
        fuzz = {
            "ok": True,
            "execution_status": "not_required_for_fast_tier",
            "declared_profile_count": len(FUZZ_PROFILE_IDS),
            "executed_profile_count": 0,
            "passed_profile_count": 0,
            "failed_profile_count": 0,
            "receipts": [],
        }
        historical = {
            "ok": True,
            "execution_status": "not_required_for_fast_tier",
            "mandatory_case_ids": list(HISTORICAL_MISS_IDS),
            "registered_case_count": len(HISTORICAL_MISS_IDS),
            "locally_executed_case_count": 0,
            "delegated_child_case_count": 0,
            "receipts": [],
        }
        backfeed = {
            "execution_status": "not_required_for_fast_tier",
            "row_count": 0,
            "all_historical_misses_backfed": False,
            "rows": [],
        }
        benchmark = {
            "ok": True,
            "execution_status": "not_required_for_fast_tier",
            "case_count": 0,
            "worker_count": BENCHMARK_PARALLEL_WORKERS,
            "windows_recommended_parallelism_confirmed": True,
            "case_timings": [],
            "shards": [],
        }
    duration_seconds = time.perf_counter() - run_started
    budget_passed = duration_seconds <= approved_budget
    ok = (
        not static_failures
        and single_fault_validator["ok"]
        and not execution_identity_failures
        and collision_audit["ok"]
        and selection["selection_complete"]
        and selection_receipt_match
        and not stale
        and len(proof_backed) == len(selected_ids)
        and equivalence["ok"]
        and bool(passed)
        and not failed
        and fuzz["ok"]
        and historical["ok"]
        and benchmark["ok"]
        and budget_passed
    )
    static_counts = {
        "declared": int(single_fault_validator["declared_case_count"]),
        "applicable": int(single_fault_validator["applicable_case_count"]),
        "excluded": int(single_fault_validator["excluded_case_count"]),
        "generated": int(single_fault_validator["generated_case_count"]),
        "selected": int(single_fault_validator["selected_case_count"]),
        "executed": int(single_fault_validator["executed_case_count"]),
        "passed": int(single_fault_validator["passed_case_count"]),
        "failed": int(single_fault_validator["failed_case_count"]),
        "stale": int(single_fault_validator["stale_case_count"]),
        "proof_backed": int(single_fault_validator["proof_backed_case_count"]),
    }
    public_counts = {
        "declared": len(universe),
        "applicable": len(universe) - len(excluded_ids),
        "excluded": len(excluded_ids),
        "generated": len(universe),
        "selected": len(selected_ids),
        "executed": len(executed_ids),
        "passed": len(passed),
        "failed": len(failed),
        "stale": len(stale),
        "proof_backed": len(proof_backed),
    }
    fuzz_declared = int(fuzz["declared_profile_count"])
    fuzz_executed = int(fuzz["executed_profile_count"])
    fuzz_passed = int(fuzz["passed_profile_count"])
    fuzz_failed = int(fuzz["failed_profile_count"])
    fuzz_counts = {
        "declared": fuzz_declared,
        "applicable": fuzz_declared if mode == "adversarial" else 0,
        "excluded": 0 if mode == "adversarial" else fuzz_declared,
        "generated": fuzz_executed,
        "selected": fuzz_executed,
        "executed": fuzz_executed,
        "passed": fuzz_passed,
        "failed": fuzz_failed,
        "stale": 0,
        "proof_backed": fuzz_passed,
    }
    aggregate_counts = {
        key: static_counts[key] + public_counts[key] + fuzz_counts[key]
        for key in (
            "declared",
            "applicable",
            "excluded",
            "generated",
            "selected",
            "executed",
            "passed",
            "failed",
            "stale",
            "proof_backed",
        )
    }
    return {
        "schema_version": "flowpilot.ai_response_execution_closure.v2",
        "model_id": MODEL_ID,
        "mode": mode,
        "ok": ok,
        "generated_at": _utc_now(),
        "source_fingerprint": source_fingerprint(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "recommended_windows_parallel_workers": BENCHMARK_PARALLEL_WORKERS,
        },
        "timing": {
            "duration_seconds": round(duration_seconds, 3),
            "approved_budget_seconds": approved_budget,
            "budget_passed": budget_passed,
        },
        "claim_boundary": (
            "Full execution of the declared finite current mechanical mutation universe "
            "(required, child, array, non-empty, type, enum, forbidden, alias, and checklist identity); "
            "execution-backed public-path coverage for selected pairwise and five named business-risk triples. "
            "Cross-products between independent static fault paths, unbounded malformed syntax, and future "
            "natural-language AI semantics remain outside this model and require their owning suites."
        ),
        "case_identity": {
            "source_path_preserving": True,
            "execution_identity_failures": execution_identity_failures,
            "audited_legacy_collision_repair": collision_audit,
        },
        "coverage_summary": {
            "count_fields": [
                "declared",
                "applicable",
                "excluded",
                "generated",
                "selected",
                "executed",
                "passed",
                "failed",
                "stale",
                "proof_backed",
            ],
            "static_mechanical": static_counts,
            "public_interaction": public_counts,
            "deterministic_fuzz": fuzz_counts,
            "aggregate": aggregate_counts,
            "counts_are_independent": True,
        },
        "static_mechanical_universe": {
            "universe_definition": [
                "one current minimal-valid-shape candidate per registered family/profile variant",
                "every declared required/child/array/non-empty/type/enum/forbidden/alias mutation",
                "every declared public checklist identity mutation",
            ],
            "explicit_exclusions": [
                "cross-products between independent static mutation paths",
                "unbounded malformed syntax",
                "arbitrary natural-language semantic quality",
            ],
            "registered_family_count": len(packet_result_contracts.PACKET_RESULT_CONTRACTS_BY_FAMILY),
            "enumerated_case_count": len(static_cells),
            "failures": static_failures,
            "by_mutation_kind": {
                kind: sum(1 for cell in static_cells if cell["mutation_kind"] == kind)
                for kind in sorted({str(cell["mutation_kind"]) for cell in static_cells})
            },
            "case_ids": [cell["case_id"] for cell in static_cells],
        },
        "real_single_fault_validator": single_fault_validator,
        "execution_universe": {
            "declared_case_count": len(universe),
            "applicable_case_count": len(universe) - len(excluded_ids),
            "excluded_case_count": len(excluded_ids),
            "generated_case_count": len(universe),
            "selected_case_count": len(selected_ids),
            "executed_case_count": len(executed_ids),
            "passed_case_count": len(passed),
            "failed_case_count": len(failed),
            "stale_case_count": len(stale),
            "proof_backed_case_count": len(proof_backed),
            "not_run_case_count": len(not_run),
            "structured_exclusions": [row["structured_exclusion"] for row in excluded],
            "selected_receipts_match": selection_receipt_match,
            "selection": {key: value for key, value in selection.items() if key != "selected"},
        },
        "oracle_equivalence": equivalence,
        "deterministic_fuzz": fuzz,
        "historical_misses": historical,
        "observed_problem_backfeed": backfeed,
        "public_path_benchmark": benchmark,
        "receipts": receipts,
        "failed_receipts": failed[:20],
        "test_mesh": {
            "parent_gate_id": f"formal_ai_submit_{mode}",
            "status": "passed" if ok else "failed",
            "freshness": "current_execution" if ok else "failed_current_execution",
            "required_child_case_ids": sorted(selected_ids),
            "executed_child_case_ids": sorted(executed_ids),
            "not_run_child_case_ids": sorted(row["case_id"] for row in not_run),
            "evidence_tier": "runtime_external_contract",
            "final_artifact_requirements": [
                "<name>.out.txt",
                "<name>.err.txt",
                "<name>.combined.txt",
                "<name>.exit.txt",
                "<name>.meta.json",
            ],
            "hidden_skip_allowed": False,
            "budget_seconds": approved_budget,
            "budget_passed": budget_passed,
        },
    }


@dataclass(frozen=True)
class State:
    scenario: str = "new"
    status: str = "new"
    finite_universe_declared: bool = True
    static_cases_unique: bool = True
    pairwise_closed: bool = True
    critical_triples_closed: bool = True
    named_business_triples_closed: bool = True
    coverage_counts_independent: bool = True
    public_pipeline_current: bool = True
    static_receipts_oracle_bound: bool = True
    selected_receipts_bound: bool = True
    contract_oracles_bound: bool = True
    source_path_collision_audit_passed: bool = True
    historical_misses_pinned: bool = True
    deterministic_fuzz_executed: bool = True
    benchmark_with_two_workers_completed: bool = True
    approved_budget_passed: bool = True
    background_final_artifacts_complete: bool = True
    not_run_separate: bool = True
    failed_receipt_claimed_pass: bool = False
    progress_claimed_complete: bool = False


@dataclass(frozen=True)
class Tick:
    """One execution-closure process step."""


@dataclass(frozen=True)
class Action:
    name: str


class Transition(NamedTuple):
    label: str
    state: State


SCENARIOS = {
    "valid_execution_closure": State(scenario="valid_execution_closure", status="selected"),
    "missing_universe": replace(State(), scenario="missing_universe", status="selected", finite_universe_declared=False),
    "duplicate_case_ids": replace(State(), scenario="duplicate_case_ids", status="selected", static_cases_unique=False),
    "pairwise_gap": replace(State(), scenario="pairwise_gap", status="selected", pairwise_closed=False),
    "critical_triple_gap": replace(State(), scenario="critical_triple_gap", status="selected", critical_triples_closed=False),
    "named_business_triple_gap": replace(
        State(), scenario="named_business_triple_gap", status="selected", named_business_triples_closed=False
    ),
    "coverage_counts_conflated": replace(
        State(), scenario="coverage_counts_conflated", status="selected", coverage_counts_independent=False
    ),
    "selected_internal_envelope_authority": replace(
        State(), scenario="selected_internal_envelope_authority", status="selected", public_pipeline_current=False
    ),
    "static_receipt_missing_oracle": replace(
        State(), scenario="static_receipt_missing_oracle", status="selected", static_receipts_oracle_bound=False
    ),
    "selected_without_receipt": replace(State(), scenario="selected_without_receipt", status="selected", selected_receipts_bound=False),
    "selected_without_contract_oracle": replace(
        State(), scenario="selected_without_contract_oracle", status="selected", contract_oracles_bound=False
    ),
    "source_path_collision_audit_failed": replace(
        State(), scenario="source_path_collision_audit_failed", status="selected", source_path_collision_audit_passed=False
    ),
    "historical_miss_optimized_out": replace(
        State(), scenario="historical_miss_optimized_out", status="selected", historical_misses_pinned=False
    ),
    "deterministic_fuzz_not_executed": replace(
        State(), scenario="deterministic_fuzz_not_executed", status="selected", deterministic_fuzz_executed=False
    ),
    "benchmark_parallelism_unproven": replace(
        State(), scenario="benchmark_parallelism_unproven", status="selected", benchmark_with_two_workers_completed=False
    ),
    "tier_budget_exceeded": replace(
        State(), scenario="tier_budget_exceeded", status="selected", approved_budget_passed=False
    ),
    "background_final_artifact_missing": replace(
        State(), scenario="background_final_artifact_missing", status="selected", background_final_artifacts_complete=False
    ),
    "not_run_collapsed_into_pass": replace(State(), scenario="not_run_collapsed_into_pass", status="selected", not_run_separate=False),
    "failed_receipt_claimed_pass": replace(State(), scenario="failed_receipt_claimed_pass", status="selected", failed_receipt_claimed_pass=True),
    "progress_claimed_complete": replace(State(), scenario="progress_claimed_complete", status="selected", progress_claimed_complete=True),
}
VALID_SCENARIOS = {"valid_execution_closure"}
NEGATIVE_SCENARIOS = set(SCENARIOS) - VALID_SCENARIOS


def state_failures(state: State) -> list[str]:
    failures: list[str] = []
    if not state.finite_universe_declared:
        failures.append("finite_execution_universe_missing")
    if not state.static_cases_unique:
        failures.append("execution_case_ids_not_unique")
    if not state.pairwise_closed:
        failures.append("pairwise_coverage_gap")
    if not state.critical_triples_closed:
        failures.append("critical_three_way_coverage_gap")
    if not state.named_business_triples_closed:
        failures.append("named_business_three_way_coverage_gap")
    if not state.coverage_counts_independent:
        failures.append("declared_applicable_excluded_generated_selected_executed_pass_fail_stale_proof_counts_conflated")
    if not state.public_pipeline_current:
        failures.append("selected_case_did_not_traverse_public_checklist_pipeline")
    if not state.static_receipts_oracle_bound:
        failures.append("static_case_missing_status_repair_transition_side_effect_oracle")
    if not state.selected_receipts_bound:
        failures.append("selected_case_missing_execution_receipt")
    if not state.contract_oracles_bound:
        failures.append("selected_case_missing_executable_contract_oracle")
    if not state.source_path_collision_audit_passed:
        failures.append("source_path_case_id_collision_unclosed")
    if not state.historical_misses_pinned:
        failures.append("historical_miss_optimized_out")
    if not state.deterministic_fuzz_executed:
        failures.append("deterministic_fuzz_not_executed")
    if not state.benchmark_with_two_workers_completed:
        failures.append("windows_two_worker_benchmark_unproven")
    if not state.approved_budget_passed:
        failures.append("formal_tier_budget_exceeded")
    if not state.background_final_artifacts_complete:
        failures.append("background_final_artifact_missing")
    if not state.not_run_separate:
        failures.append("not_run_case_collapsed_into_pass")
    if state.failed_receipt_claimed_pass:
        failures.append("failed_receipt_claimed_pass")
    if state.progress_claimed_complete:
        failures.append("background_progress_claimed_complete")
    return failures


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "new":
        for name, scenario in sorted(SCENARIOS.items()):
            yield Transition(f"select_{name}", scenario)
        return
    if state.status == "selected":
        failures = state_failures(state)
        terminal = "rejected" if failures else "accepted"
        yield Transition(f"{terminal}_{state.scenario}", replace(state, status=terminal))


def initial_state() -> State:
    return State()


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted"


def accepted_execution_closure_is_safe(state: State, _trace: object) -> InvariantResult:
    if state.status == "accepted" and state_failures(state):
        return InvariantResult.fail("; ".join(state_failures(state)))
    if state.status == "rejected" and not state_failures(state):
        return InvariantResult.fail("safe execution closure was rejected")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "accepted_execution_closure_is_safe",
        "Accepted closure requires finite enumeration, executable oracles, covering-array and fuzz closure, current final artifacts, budget proof, real receipts, and explicit not-run separation.",
        accepted_execution_closure_is_safe,
    ),
)
EXTERNAL_INPUTS = (Tick(),)


class AIResponseExecutionClosureStep:
    """Input x State -> Set(Output x State) for execution-closure decisions."""

    name = "AIResponseExecutionClosureStep"
    reads = (
        "finite_contract_universe",
        "contract_oracles",
        "selection_receipts",
        "historical_and_fuzz_receipts",
        "benchmark_and_budget_receipts",
        "background_final_artifacts",
        "runtime_execution_receipts",
    )
    writes = ("execution_closure_decision",)
    input_description = "one formal AI response execution closure state"
    output_description = "accepted or rejected closure decision"
    idempotency = "pure decision over immutable receipt identities"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def build_workflow() -> Workflow:
    return Workflow((AIResponseExecutionClosureStep(),), name=MODEL_ID)


def hazard_states() -> dict[str, State]:
    return {name: SCENARIOS[name] for name in sorted(NEGATIVE_SCENARIOS)}


def expected_failures_by_hazard() -> dict[str, list[str]]:
    return {name: state_failures(state) for name, state in hazard_states().items()}
