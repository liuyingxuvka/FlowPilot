"""Barrier-bundle contract for equivalent FlowPilot control simplification.

The bundle contract is deliberately ledger/envelope metadata only. It never
merges role bodies, changes packet ownership, grants Controller project
authority, or lets an AI decide to downgrade a gate. A bundle is valid only
when it proves that the same legacy obligations are still satisfied by their
existing role-scoped packet, manifest, reviewer, officer, route, and final
ledger evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


BARRIER_BUNDLE_SCHEMA = "flowpilot.barrier_bundle.v1"
BARRIER_BUNDLE_EQUIVALENCE_MODE = "preserve_existing_packet_semantics"

ROLE_KEYS = (
    "controller",
    "project_manager",
    "human_like_reviewer",
    "process_flowguard_officer",
    "product_flowguard_officer",
    "worker_a",
    "worker_b",
)

LEGACY_OBLIGATIONS = (
    "explicit_three_question_startup_gate",
    "fresh_run_root_and_legacy_backup_boundary",
    "six_role_crew_authority",
    "controller_relay_only_boundary",
    "system_card_manifest_delivery",
    "packet_ledger_mail_delivery",
    "pm_material_and_research_decisions",
    "reviewer_before_worker_evidence_use",
    "flowguard_officer_model_gates",
    "route_frontier_and_current_node_loop",
    "route_mutation_and_stale_evidence",
    "heartbeat_manual_resume_reentry",
    "final_route_wide_ledger_and_terminal_replay",
    "cockpit_or_chat_route_display",
    "retired_assets_and_old_state_quarantine",
    "skill_improvement_nonblocking_report",
)


@dataclass(frozen=True)
class BarrierDefinition:
    barrier_id: str
    required_obligations: tuple[str, ...]
    required_role_slices: tuple[str, ...]
    dependencies: tuple[str, ...] = ()
    requires_all_legacy_obligations: bool = False


BARRIER_DEFINITIONS = (
    BarrierDefinition(
        barrier_id="startup",
        required_obligations=(
            "explicit_three_question_startup_gate",
            "fresh_run_root_and_legacy_backup_boundary",
            "six_role_crew_authority",
            "controller_relay_only_boundary",
            "system_card_manifest_delivery",
        ),
        required_role_slices=("controller", "project_manager", "human_like_reviewer"),
    ),
    BarrierDefinition(
        barrier_id="material",
        required_obligations=(
            "controller_relay_only_boundary",
            "system_card_manifest_delivery",
            "packet_ledger_mail_delivery",
            "pm_material_and_research_decisions",
            "reviewer_before_worker_evidence_use",
        ),
        required_role_slices=(
            "project_manager",
            "human_like_reviewer",
            "worker_a",
            "worker_b",
        ),
        dependencies=("startup",),
    ),
    BarrierDefinition(
        barrier_id="product_architecture",
        required_obligations=(
            "pm_material_and_research_decisions",
            "reviewer_before_worker_evidence_use",
            "flowguard_officer_model_gates",
        ),
        required_role_slices=(
            "project_manager",
            "human_like_reviewer",
            "product_flowguard_officer",
        ),
        dependencies=("material",),
    ),
    BarrierDefinition(
        barrier_id="root_contract",
        required_obligations=(
            "reviewer_before_worker_evidence_use",
        ),
        required_role_slices=(
            "project_manager",
            "human_like_reviewer",
        ),
        dependencies=("product_architecture",),
    ),
    BarrierDefinition(
        barrier_id="child_skill_manifest",
        required_obligations=(
            "system_card_manifest_delivery",
            "packet_ledger_mail_delivery",
            "route_frontier_and_current_node_loop",
        ),
        required_role_slices=(
            "project_manager",
            "human_like_reviewer",
        ),
        dependencies=("root_contract",),
    ),
    BarrierDefinition(
        barrier_id="route_skeleton",
        required_obligations=(
            "route_frontier_and_current_node_loop",
            "route_mutation_and_stale_evidence",
            "flowguard_officer_model_gates",
        ),
        required_role_slices=(
            "project_manager",
            "human_like_reviewer",
            "process_flowguard_officer",
            "product_flowguard_officer",
        ),
        dependencies=("child_skill_manifest",),
    ),
    BarrierDefinition(
        barrier_id="current_node",
        required_obligations=(
            "packet_ledger_mail_delivery",
            "reviewer_before_worker_evidence_use",
            "route_frontier_and_current_node_loop",
            "route_mutation_and_stale_evidence",
        ),
        required_role_slices=(
            "project_manager",
            "human_like_reviewer",
            "worker_a",
            "worker_b",
        ),
        dependencies=("route_skeleton",),
    ),
    BarrierDefinition(
        barrier_id="parent_backward",
        required_obligations=(
            "reviewer_before_worker_evidence_use",
            "route_frontier_and_current_node_loop",
            "route_mutation_and_stale_evidence",
        ),
        required_role_slices=("project_manager", "human_like_reviewer"),
        dependencies=("current_node",),
    ),
    BarrierDefinition(
        barrier_id="final_closure",
        required_obligations=(
            "heartbeat_manual_resume_reentry",
            "final_route_wide_ledger_and_terminal_replay",
            "cockpit_or_chat_route_display",
            "retired_assets_and_old_state_quarantine",
            "skill_improvement_nonblocking_report",
        ),
        required_role_slices=(
            "project_manager",
            "human_like_reviewer",
            "process_flowguard_officer",
            "product_flowguard_officer",
        ),
        dependencies=("parent_backward",),
        requires_all_legacy_obligations=True,
    ),
)

_BARRIER_BY_ID = {item.barrier_id: item for item in BARRIER_DEFINITIONS}
_LEGACY_OBLIGATION_SET = set(LEGACY_OBLIGATIONS)


def barrier_ids() -> tuple[str, ...]:
    return tuple(item.barrier_id for item in BARRIER_DEFINITIONS)


def required_obligation_ids(barrier_id: str) -> tuple[str, ...]:
    return _BARRIER_BY_ID[barrier_id].required_obligations


def all_legacy_obligation_ids() -> tuple[str, ...]:
    return LEGACY_OBLIGATIONS


def _as_bool_passed(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value in {"passed", "covered", "approved", "satisfied"}
    if isinstance(value, Mapping):
        if value.get("passed") is True:
            return True
        status = value.get("status")
        return isinstance(status, str) and status in {
            "passed",
            "covered",
            "approved",
            "satisfied",
        }
    return False


def _obligation_statuses(raw: Any) -> dict[str, bool]:
    if isinstance(raw, Mapping):
        return {str(key): _as_bool_passed(value) for key, value in raw.items()}
    if isinstance(raw, list):
        result: dict[str, bool] = {}
        for item in raw:
            if isinstance(item, str):
                result[item] = True
            elif isinstance(item, Mapping):
                obligation_id = item.get("id") or item.get("obligation_id")
                if obligation_id:
                    result[str(obligation_id)] = _as_bool_passed(item)
        return result
    return {}


def _role_statuses(raw: Any) -> tuple[dict[str, bool], list[str]]:
    wrong_role_entries: list[str] = []
    if isinstance(raw, Mapping):
        return {str(key): _as_bool_passed(value) for key, value in raw.items()}, []
    if isinstance(raw, list):
        result: dict[str, bool] = {}
        for item in raw:
            if not isinstance(item, Mapping):
                continue
            role = item.get("role") or item.get("approved_by_role")
            expected_role = item.get("expected_role") or role
            if role:
                result[str(role)] = _as_bool_passed(item)
                if expected_role and role != expected_role:
                    wrong_role_entries.append(f"{role}!={expected_role}")
        return result, wrong_role_entries
    return {}, []


def _cache_failures(cache_reuse: Any) -> list[str]:
    if not isinstance(cache_reuse, Mapping) or not cache_reuse.get("claimed"):
        return []
    failures: list[str] = []
    if not cache_reuse.get("input_hash_same"):
        failures.append("cache_reuse_input_hash_changed")
    if not cache_reuse.get("source_hash_same", True):
        failures.append("cache_reuse_source_hash_changed")
    if not cache_reuse.get("evidence_hash_valid"):
        failures.append("cache_reuse_evidence_hash_invalid")
    if cache_reuse.get("invalidated"):
        failures.append("cache_reuse_invalidated")
    return failures


def validate_barrier_bundle(
    bundle: Mapping[str, Any],
    *,
    cumulative_obligations: Any | None = None,
) -> dict[str, Any]:
    """Validate one barrier bundle without weakening packet semantics."""

    failures: list[str] = []
    schema_ok = bundle.get("schema_version") == BARRIER_BUNDLE_SCHEMA
    if not schema_ok:
        failures.append("invalid_schema_version")

    equivalence_mode = bundle.get("equivalence_mode")
    if equivalence_mode != BARRIER_BUNDLE_EQUIVALENCE_MODE:
        failures.append("equivalence_mode_does_not_preserve_packet_semantics")

    barrier_id = str(bundle.get("barrier_id") or "")
    definition = _BARRIER_BY_ID.get(barrier_id)
    if definition is None:
        failures.append("unknown_barrier_id")
        required_obligations: tuple[str, ...] = ()
        required_roles: tuple[str, ...] = ()
    else:
        required_obligations = definition.required_obligations
        required_roles = definition.required_role_slices

    obligations = _obligation_statuses(bundle.get("obligations"))
    role_slices, wrong_role_entries = _role_statuses(bundle.get("role_slices"))
    cumulative = _obligation_statuses(cumulative_obligations)
    cumulative.update(_obligation_statuses(bundle.get("cumulative_obligations")))
    cumulative.update(obligations)

    unknown_obligations = sorted(set(obligations) - _LEGACY_OBLIGATION_SET)
    missing_obligations = [
        obligation for obligation in required_obligations if not obligations.get(obligation)
    ]
    missing_roles = [role for role in required_roles if not role_slices.get(role)]
    if unknown_obligations:
        failures.append("unknown_legacy_obligation")
    if missing_obligations:
        failures.append("missing_required_obligations")
    if missing_roles:
        failures.append("missing_required_role_slices")
    if wrong_role_entries or bundle.get("wrong_role_approval_used"):
        failures.append("wrong_role_approval_used")

    if definition and definition.requires_all_legacy_obligations:
        missing_cumulative = [
            obligation for obligation in LEGACY_OBLIGATIONS if not cumulative.get(obligation)
        ]
        if missing_cumulative:
            failures.append("final_closure_missing_cumulative_legacy_obligations")
    else:
        missing_cumulative = []

    boundary = bundle.get("controller_boundary")
    boundary = boundary if isinstance(boundary, Mapping) else {}
    if bundle.get("ai_discretion_used") or boundary.get("ai_discretion_used"):
        failures.append("ai_discretion_used")
    if bundle.get("controller_read_sealed_body") or boundary.get("controller_read_sealed_body"):
        failures.append("controller_read_sealed_body")
    if bundle.get("controller_originated_evidence") or boundary.get("controller_originated_evidence"):
        failures.append("controller_originated_evidence")
    if bundle.get("controller_summarized_body") or boundary.get("controller_summarized_body"):
        failures.append("controller_summarized_body")

    failures.extend(_cache_failures(bundle.get("cache_reuse")))

    if bundle.get("stale_evidence_used"):
        failures.append("stale_evidence_used")
    if bundle.get("route_mutation_recorded"):
        if not bundle.get("stale_evidence_marked"):
            failures.append("route_mutation_without_stale_evidence_mark")
        if not bundle.get("frontier_rewritten_after_mutation"):
            failures.append("route_mutation_without_frontier_rewrite")

    if barrier_id == "final_closure":
        if not bundle.get("final_ledger_clean"):
            failures.append("final_closure_without_clean_ledger")
        if not bundle.get("terminal_backward_replay_passed"):
            failures.append("final_closure_without_terminal_backward_replay")

    report = {
        "schema_version": "flowpilot.barrier_bundle_validation.v1",
        "bundle_id": bundle.get("bundle_id"),
        "barrier_id": barrier_id,
        "ok": not failures,
        "failures": sorted(set(failures)),
        "missing_obligations": missing_obligations,
        "missing_cumulative_obligations": missing_cumulative,
        "missing_role_slices": missing_roles,
        "unknown_obligations": unknown_obligations,
        "wrong_role_entries": wrong_role_entries,
        "required_obligations": list(required_obligations),
        "required_role_slices": list(required_roles),
        "equivalence_mode": equivalence_mode,
    }
    return report


def barrier_bundle_summary(bundle: Mapping[str, Any]) -> dict[str, Any]:
    report = validate_barrier_bundle(bundle)
    return {
        "schema_version": "flowpilot.barrier_bundle_summary.v1",
        "bundle_id": bundle.get("bundle_id"),
        "barrier_id": bundle.get("barrier_id"),
        "status": "passed" if report["ok"] else "blocked",
        "equivalence_mode": bundle.get("equivalence_mode"),
        "member_packet_ids": list(bundle.get("member_packet_ids") or []),
        "validation_report": report,
    }


def passed_obligation_ids(bundle: Mapping[str, Any]) -> tuple[str, ...]:
    statuses = _obligation_statuses(bundle.get("obligations"))
    return tuple(item for item in LEGACY_OBLIGATIONS if statuses.get(item))


def make_pending_bundle(
    *,
    bundle_id: str,
    barrier_id: str,
    member_packet_ids: tuple[str, ...] = (),
    node_id: str | None = None,
    route_version: int | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": BARRIER_BUNDLE_SCHEMA,
        "bundle_id": bundle_id,
        "barrier_id": barrier_id,
        "node_id": node_id,
        "route_version": route_version,
        "equivalence_mode": BARRIER_BUNDLE_EQUIVALENCE_MODE,
        "member_packet_ids": list(member_packet_ids),
        "status": "pending",
        "obligations": [],
        "role_slices": [],
        "controller_boundary": {
            "controller_read_sealed_body": False,
            "controller_originated_evidence": False,
            "controller_summarized_body": False,
            "ai_discretion_used": False,
        },
    }
