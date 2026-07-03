"""FlowPilot control-plane contract exhaustion mesh.

This parent model covers the finite control-plane combinations that caused the
recent FlowPilot misses: missing current fields, missing packet bodies,
FlowGuard evidence policy or authorized material loss during reissue, empty
required reviewer manifests, accepted-result/work-order split brain, and
repeated no-delta repair loops. Child runtime tests still prove the concrete code behavior; this model
proves the matrix has a current owner and a safe disposition for every required
cell.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import product
from pathlib import Path
import sys
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


ROOT = Path(__file__).resolve().parents[1]
ASSETS_PATH = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS_PATH) not in sys.path:
    sys.path.insert(0, str(ASSETS_PATH))

from flowpilot_core_runtime import formal_artifact_contracts, packet_result_contracts, review_window_contracts  # noqa: E402
from flowpilot_fake_ai_runtime_replay_model import runtime_replay_cells  # noqa: E402
from flowpilot_integration_cartesian_coverage_model import iter_required_cells as integration_cartesian_cells  # noqa: E402
from flowpilot_real_issue_backfeed import backfeed_cells  # noqa: E402


MODEL_ID = "flowpilot_contract_exhaustion_mesh"
MAX_SEQUENCE_LENGTH = 2
FORMAL_ARTIFACT_MUTATION_KIND_SET = set(formal_artifact_contracts.FORMAL_ARTIFACT_FAULT_MODES)

CONTRACT_FAMILIES = (
    "task_packet_body",
    "task_result_body",
    "flowguard_check_packet",
    "flowguard_check_result",
    "flowguard_reissue_packet",
    "flowguard_work_order",
    "review_packet",
    "system_validation",
    "runtime_install_self_check",
    "pm_repair_packet",
    "break_glass_loop",
    "integration_cartesian_coverage",
)

MALFORMED_BODY_MUTATION_KINDS = (
    "malformed_body.unquoted_keys",
    "malformed_body.markdown_wrapped_json",
    "malformed_body.prose_plus_json",
    "malformed_body.top_level_array",
    "malformed_body.empty_body",
    "malformed_body.trailing_comma",
)

MUTATION_KINDS = (
    "missing_body",
    "missing_required_field",
    "wrong_type",
    "wrong_owner",
    "wrong_current_path",
    "stale_id",
    "evidence_path_mismatch",
    "empty_required_manifest",
    "empty_required_array",
    "missing_required_child_field",
    "forbidden_field_present",
    "missing_current_handoff_manifest",
    "missing_stage_evidence_matrix",
    "stage_evidence_mismatch",
    "missing_authorized_read",
    "missing_related_authorized_body",
    "packet_body_not_opened",
    "missing_repair_guidance",
    "missing_repair_evidence_obligations",
    "missing_repair_obligation_disposition",
    "unknown_repair_obligation_id",
    "stale_repair_obligation_evidence_ref",
    "missing_repair_obligation_consumption",
    "missing_result_contract_profile",
    "missing_allowed_value_options",
    "missing_field_type_requirements",
    "forbidden_alias_used",
    "wrong_allowed_value",
    "corrected_second_retry",
    "missing_root_cause_loop_key",
    "accepted_result_work_order_split",
    "reissue_loses_inherited_policy",
    "reissue_loses_inherited_authorized_reads",
    "reissue_loses_required_read_manifest",
    "same_payload_retry",
    "same_root_no_delta_retry",
    "missing_runtime_self_check_receipt",
    "target_requires_dev_repo_simulation",
    "synthetic_live_overclaim",
    *formal_artifact_contracts.FORMAL_ARTIFACT_FAULT_MODES,
    *MALFORMED_BODY_MUTATION_KINDS,
)

SYNTHETIC_MUTATION_KINDS = {
    "forbidden_alias_used",
    *MALFORMED_BODY_MUTATION_KINDS,
    *review_window_contracts.REVIEW_WINDOW_FAKE_AI_PROFILE_IDS,
    "same_payload_retry",
    "same_root_no_delta_retry",
    "synthetic_live_overclaim",
    "wrong_allowed_value",
    "corrected_second_retry",
    *formal_artifact_contracts.FORMAL_ARTIFACT_FAULT_MODES,
}

HISTORICAL_FAILURE_FAMILIES = (
    {
        "failure_id": "history.worker_result_body_missing_required_self_check_fields",
        "family": "task_result_body",
        "source_class": "worker_output_contract_failure",
        "historical_source": "known_friction.worker_self_check_failure",
        "mutation_kinds": ("missing_body", "missing_required_field", "wrong_type"),
        "normal_repair_route": "pm_records_package_rework_with_missing_field_guidance",
        "glass_break_allowed_in_acceptance": False,
    },
    {
        "failure_id": "history.packet_mail_missing_or_unopened_body",
        "family": "task_packet_body",
        "source_class": "mail_chain_or_packet_body_loss",
        "historical_source": "capability_packet_mail_chain_audit + synthetic_agent_trace_replay",
        "mutation_kinds": ("missing_body", "stale_id", "wrong_owner"),
        "normal_repair_route": "same_holder_retry_or_packet_reissue_with_current_packet_id",
        "glass_break_allowed_in_acceptance": False,
    },
    {
        "failure_id": "history.router_event_or_packet_address_wrong",
        "family": "task_packet_body",
        "source_class": "wrong_address_or_current_wait",
        "historical_source": "hard_gate.router_event.unauthorized_current_wait + role_output.router_supplied_event_mismatch",
        "mutation_kinds": ("wrong_current_path", "wrong_owner", "stale_id"),
        "normal_repair_route": "reject_before_state_mutation_then_retry_after_current_router_wait",
        "glass_break_allowed_in_acceptance": False,
    },
    {
        "failure_id": "history.research_packet_recipient_role_alias",
        "family": "research_packet_spec",
        "source_class": "legacy_alias_input_surface",
        "historical_source": "field_lifecycle_audit.research_packet_spec.recipient_role",
        "mutation_kinds": ("legacy_alias",),
        "normal_repair_route": "reject_before_packet_creation_and_require_to_role",
        "glass_break_allowed_in_acceptance": False,
    },
    {
        "failure_id": "history.context_or_route_frontier_stale",
        "family": "system_validation",
        "source_class": "route_mutation_stale_evidence",
        "historical_source": "historical_live_run.route.mutation.old_frontier_and_sibling_evidence",
        "mutation_kinds": ("stale_id", "wrong_current_path", "missing_current_handoff_manifest"),
        "normal_repair_route": "block_route_mutation_until_current_frontier_and_sibling_evidence_refresh",
        "glass_break_allowed_in_acceptance": False,
    },
    {
        "failure_id": "history.historical_evidence_or_background_proof_disappears",
        "family": "system_validation",
        "source_class": "historical_or_background_evidence_loss",
        "historical_source": "historical_live_run.background.proof.edge_artifact_mismatch + hard_gate.background.progress_only_not_proof",
        "mutation_kinds": ("evidence_path_mismatch", "missing_required_field", "synthetic_live_overclaim"),
        "normal_repair_route": "wait_for_final_exit_or_rerun_background_check_with_current_artifacts",
        "glass_break_allowed_in_acceptance": False,
    },
    {
        "failure_id": "history.install_source_split_brain",
        "family": "runtime_install_self_check",
        "source_class": "install_source_split_brain",
        "historical_source": "historical_live_run.install.split_brain.stale_installed_and_loaded_prompt",
        "mutation_kinds": (
            "wrong_current_path",
            "stale_id",
            "evidence_path_mismatch",
            "missing_runtime_self_check_receipt",
            "target_requires_dev_repo_simulation",
        ),
        "normal_repair_route": "sync_repo_owned_skill_then_recheck_source_hashes",
        "glass_break_allowed_in_acceptance": False,
    },
    {
        "failure_id": "history.pm_repair_no_producer_or_invalid_target",
        "family": "pm_repair_packet",
        "source_class": "pm_repair_target_or_producer_loss",
        "historical_source": "e2e.pm_repair.no_producer_then_packet_reissue + control_blocker.pm_repair_decision",
        "mutation_kinds": ("missing_repair_guidance", "wrong_current_path", "missing_required_child_field"),
        "normal_repair_route": "pm_records_corrected_packet_reissue_with_current_generation_producer",
        "glass_break_allowed_in_acceptance": False,
    },
    {
        "failure_id": "history.pm_repair_reason_only_drops_missing_evidence_obligations",
        "family": "pm_repair_packet",
        "source_class": "pm_repair_information_flow_loss",
        "historical_source": "runtime.pm_repair_reason_only + field_lifecycle.repair_obligation_chain",
        "mutation_kinds": (
            "missing_repair_evidence_obligations",
            "missing_repair_obligation_disposition",
            "stale_repair_obligation_evidence_ref",
            "missing_related_authorized_body",
        ),
        "normal_repair_route": "runtime_rejects_pm_result_and_reissues_current_pm_packet_with_precise_obligation_shape",
        "glass_break_allowed_in_acceptance": False,
    },
    {
        "failure_id": "history.same_blocker_repeats_until_glass_break_alarm",
        "family": "break_glass_loop",
        "source_class": "same_family_control_blocker_repetition",
        "historical_source": "known_friction.control_blocker_same_family_storm",
        "mutation_kinds": ("same_root_no_delta_retry", "missing_root_cause_loop_key"),
        "normal_repair_route": "repair_guidance_changes_or_pm_corrects_before_threshold",
        "glass_break_allowed_in_acceptance": False,
        "alarm_required_after_same_blocker_attempts": 5,
    },
)

CONTROL_PLANE_REQUIRED_PATHS = (
    {
        "family": "flowguard_check_packet",
        "path": "body.evidence_output_policy.run_local_evidence_root",
        "mutation_kinds": ("missing_required_field", "wrong_type", "wrong_current_path"),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "flowguard_check_packet",
        "path": "body.evidence_output_policy.required_for_formal_run",
        "mutation_kinds": ("missing_required_field", "wrong_type"),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "task_packet_body",
        "path": "current_handoff_contract.stage_evidence_matrix",
        "mutation_kinds": ("missing_stage_evidence_matrix", "stage_evidence_mismatch", "missing_current_handoff_manifest"),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "task_packet_body",
        "path": "current_handoff_contract.required_report_contract.required_acceptance_item_ids",
        "mutation_kinds": ("missing_required_field", "empty_required_array", "missing_allowed_value_options"),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "task_packet_body",
        "path": "current_handoff_contract.required_report_contract.ownership_coverage_rule",
        "mutation_kinds": ("missing_required_field", "missing_required_child_field", "missing_repair_guidance"),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "task_packet_body",
        "path": "current_handoff_contract.required_report_contract.required_node_acceptance_item_ids",
        "mutation_kinds": ("missing_required_field", "empty_required_array", "missing_allowed_value_options"),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "task_packet_body",
        "path": "current_handoff_contract.required_report_contract.node_acceptance_projection_rule",
        "mutation_kinds": ("missing_required_field", "missing_required_child_field", "missing_repair_guidance"),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "flowguard_check_packet",
        "path": "body.subject_stage_evidence_matrix",
        "mutation_kinds": ("missing_stage_evidence_matrix", "stage_evidence_mismatch", "missing_required_field"),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "review_packet",
        "path": "body.subject_stage_evidence_matrix",
        "mutation_kinds": ("missing_stage_evidence_matrix", "stage_evidence_mismatch", "missing_required_field"),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "review_packet",
        "path": "envelope.review_window",
        "mutation_kinds": ("missing_current_handoff_manifest", "missing_required_field", "wrong_type"),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "review_packet",
        "path": "current_handoff_contract.review_window.forbidden_future_stage_demands",
        "mutation_kinds": ("missing_required_field", "empty_required_array", "stage_evidence_mismatch"),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "runtime_install_self_check",
        "path": "run_root.runtime.flowpilot_runtime_self_check_receipt.json",
        "mutation_kinds": ("missing_runtime_self_check_receipt", "missing_required_field", "wrong_current_path"),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "runtime_install_self_check",
        "path": "flowpilot_runtime_self_check_receipt.dev_repo_simulations_required",
        "mutation_kinds": ("target_requires_dev_repo_simulation", "wrong_type"),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "flowguard_reissue_packet",
        "path": "body.reissue_inherited_contract.fresh_packet_id",
        "mutation_kinds": ("missing_required_field", "wrong_current_path"),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "flowguard_reissue_packet",
        "path": "envelope.authorized_result_reads[inherited_subject_result]",
        "mutation_kinds": (
            "missing_authorized_read",
            "missing_related_authorized_body",
            "reissue_loses_inherited_authorized_reads",
        ),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "flowguard_reissue_packet",
        "path": "current_handoff_contract.input_material_manifest.required_authorized_reads_before_submit",
        "mutation_kinds": (
            "missing_current_handoff_manifest",
            "packet_body_not_opened",
            "reissue_loses_required_read_manifest",
        ),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "review_packet",
        "path": "body.flowguard_evidence_manifest.entries[].flowguard_result_id",
        "mutation_kinds": ("empty_required_manifest", "missing_required_field", "missing_authorized_read"),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "review_packet",
        "path": "envelope.authorized_result_reads[matching_flowguard_result_for_review]",
        "mutation_kinds": ("missing_authorized_read",),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "pm_repair_packet",
        "path": "active_blocker.recommended_resolution",
        "mutation_kinds": ("missing_repair_guidance", "missing_required_field"),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "pm_repair_packet",
        "path": "body.repair_evidence_obligations[]",
        "mutation_kinds": ("missing_repair_evidence_obligations", "empty_required_array", "missing_required_child_field"),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "pm_repair_packet",
        "path": "result.repair_obligation_disposition[]",
        "mutation_kinds": (
            "missing_repair_obligation_disposition",
            "unknown_repair_obligation_id",
            "stale_repair_obligation_evidence_ref",
        ),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "flowguard_check_packet",
        "path": "envelope.result_contract_profile_bindings[flowguard.semantic_recheck_required].repair_obligation_ids",
        "mutation_kinds": ("missing_repair_obligation_consumption", "missing_required_field"),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "flowguard_check_packet",
        "path": "envelope.result_contract_profile_ids[flowguard.semantic_recheck_required]",
        "mutation_kinds": ("missing_result_contract_profile", "missing_required_field"),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "flowguard_check_packet",
        "path": "current_handoff_contract.required_report_contract.allowed_value_options.semantic_recheck.subject_bound_semantic_coverage",
        "mutation_kinds": ("missing_allowed_value_options", "wrong_allowed_value"),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "flowguard_check_packet",
        "path": "current_handoff_contract.required_report_contract.field_type_requirements.semantic_recheck.subject_bound_semantic_coverage",
        "mutation_kinds": ("missing_field_type_requirements", "wrong_type"),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "flowguard_check_result",
        "path": "result.semantic_recheck.subject_bound_semantic_coverage",
        "mutation_kinds": ("wrong_allowed_value", "corrected_second_retry"),
        "required_evidence_owner": "contract_exhaustion_fake_ai_matrix",
    },
    {
        "family": "flowguard_check_result",
        "path": "result.semantic_recheck.authorized_result_body_consumed",
        "mutation_kinds": ("forbidden_alias_used", "corrected_second_retry"),
        "required_evidence_owner": "contract_exhaustion_fake_ai_matrix",
    },
    {
        "family": "pm_repair_packet",
        "path": "envelope.authorized_result_reads[blocker_and_upstream_context]",
        "mutation_kinds": ("missing_authorized_read", "missing_related_authorized_body", "packet_body_not_opened"),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
    {
        "family": "break_glass_loop",
        "path": "active_blocker.root_cause_loop_key",
        "mutation_kinds": ("missing_root_cause_loop_key", "same_root_no_delta_retry"),
        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
    },
)


def _mutation_applicable(family: str, mutation: str) -> bool:
    if family == "integration_cartesian_coverage":
        return False
    if mutation in MALFORMED_BODY_MUTATION_KINDS:
        return family in {"task_result_body", "flowguard_check_result", "review_packet", "pm_repair_packet"}
    if mutation == "empty_required_manifest":
        return family in {"review_packet", "system_validation"}
    if mutation == "empty_required_array":
        return family in {"task_result_body", "flowguard_check_result", "review_packet", "pm_repair_packet"}
    if mutation == "missing_required_child_field":
        return family in {"task_result_body", "flowguard_check_result", "review_packet", "pm_repair_packet"}
    if mutation == "forbidden_field_present":
        return family in {"task_result_body", "flowguard_check_result", "review_packet", "pm_repair_packet"}
    if mutation in {"missing_current_handoff_manifest", "missing_authorized_read"}:
        return family in {"flowguard_check_packet", "flowguard_reissue_packet", "review_packet", "pm_repair_packet"}
    if mutation in {"missing_stage_evidence_matrix", "stage_evidence_mismatch"}:
        return family in {"task_packet_body", "flowguard_check_packet", "review_packet", "pm_repair_packet"}
    if mutation in {"missing_runtime_self_check_receipt", "target_requires_dev_repo_simulation"}:
        return family == "runtime_install_self_check"
    if mutation in {"missing_related_authorized_body", "packet_body_not_opened"}:
        return family in {
            "task_packet_body",
            "pm_repair_packet",
            "review_packet",
            "flowguard_check_packet",
            "flowguard_reissue_packet",
        }
    if mutation == "missing_repair_guidance":
        return family == "pm_repair_packet"
    if mutation in {
        "missing_repair_evidence_obligations",
        "missing_repair_obligation_disposition",
        "unknown_repair_obligation_id",
        "stale_repair_obligation_evidence_ref",
    }:
        return family == "pm_repair_packet"
    if mutation == "missing_repair_obligation_consumption":
        return family == "flowguard_check_packet"
    if mutation in {"missing_result_contract_profile", "missing_allowed_value_options", "missing_field_type_requirements"}:
        return family == "flowguard_check_packet"
    if mutation in {"forbidden_alias_used", "wrong_allowed_value", "corrected_second_retry"}:
        return family in {"flowguard_check_result", "pm_repair_packet", "system_validation"}
    if mutation == "missing_root_cause_loop_key":
        return family == "break_glass_loop"
    if mutation == "accepted_result_work_order_split":
        return family in {"flowguard_check_result", "flowguard_work_order", "review_packet", "system_validation"}
    if mutation == "reissue_loses_inherited_policy":
        return family == "flowguard_reissue_packet"
    if mutation in {"reissue_loses_inherited_authorized_reads", "reissue_loses_required_read_manifest"}:
        return family == "flowguard_reissue_packet"
    if mutation == "same_root_no_delta_retry":
        return family in {"pm_repair_packet", "break_glass_loop", "system_validation"}
    if mutation == "synthetic_live_overclaim":
        return family in {"break_glass_loop", "pm_repair_packet"}
    if mutation in FORMAL_ARTIFACT_MUTATION_KIND_SET:
        return family in {
            str(contract.get("contract_exhaustion_family") or "")
            for contract in formal_artifact_contracts.all_contracts()
        }
    if mutation == "evidence_path_mismatch":
        return family in {
            "flowguard_check_packet",
            "flowguard_check_result",
            "flowguard_reissue_packet",
            "flowguard_work_order",
            "review_packet",
            "system_validation",
        }
    return True


REQUIRED_CONTRACT_EXHAUSTION_CELLS = tuple(
    {
        "cell_id": f"{family}.{mutation}",
        "family": family,
        "mutation_kind": mutation,
        "branch_kind": "synthetic_replay" if mutation in SYNTHETIC_MUTATION_KINDS else "ordinary_runtime",
        "confidence_boundary": (
            "synthetic_non_live_control_flow"
            if mutation in SYNTHETIC_MUTATION_KINDS
            else "current_runtime_contract"
        ),
        "required_evidence_owner": (
            "contract_exhaustion_fake_ai_matrix"
            if mutation in SYNTHETIC_MUTATION_KINDS
            else "contract_exhaustion_runtime_matrix"
        ),
    }
    for family, mutation in product(CONTRACT_FAMILIES, MUTATION_KINDS)
    if _mutation_applicable(family, mutation)
)


def _sanitize_path(path: str) -> str:
    return (
        path.replace("[]", "_items")
        .replace("[", "_")
        .replace("]", "")
        .replace(".", "_")
        .replace("/", "_")
        .replace(" ", "_")
        .replace("=", "_")
        .replace(":", "_")
    )


def _contract_family_bucket(packet_kind: str) -> str:
    if packet_kind == "flowguard_check":
        return "flowguard_check_result"
    if packet_kind == "review":
        return "review_packet"
    if packet_kind in {"pm_repair_decision", "pm_disposition", "pm_flowguard_acceptance"}:
        return "pm_repair_packet"
    return "task_result_body"


def _contract_packet_family_bucket(packet_kind: str) -> str:
    if packet_kind == "flowguard_check":
        return "flowguard_check_packet"
    if packet_kind == "review":
        return "review_packet"
    if packet_kind in {"pm_repair_decision", "pm_disposition", "pm_flowguard_acceptance"}:
        return "pm_repair_packet"
    return "task_packet_body"


PROFILE_EXHAUSTION_SAMPLE_BINDINGS = {
    "flowguard.semantic_recheck_required": {
        "blocker_id": "blocker-contract-exhaustion-sample",
        "coverage_boundary": "subject_bound_semantic",
        "authorized_result_read_ids": ["result-contract-exhaustion-sample"],
        "repair_obligation_ids": ["repair-obligation-contract-exhaustion-sample"],
    },
    "flowguard.subject_artifacts_consumed_required": {
        "artifact_ids": ["artifact-contract-exhaustion-sample"],
    },
}

def _formal_artifact_exhaustion_contract(contract: dict[str, object]) -> dict[str, object]:
    return {
        "required_result_body_fields": ("pm_visible_summary", "reviewed_by_role", "passed", "blockers"),
        "minimal_valid_shape": {
            "pm_visible_summary": ["FlowGuard current packet passed with formal evidence."],
            "reviewed_by_role": "flowguard_operator",
            "passed": True,
            "blockers": [],
            "contract_self_check": {
                "all_required_fields_present": True,
                "exact_field_names_used": True,
                "empty_required_arrays_explicit": True,
                "runtime_mechanical_validation_passed": True,
            },
        },
        "evidence_output_policy": {
            "required_for_formal_run": True,
            "run_local_evidence_root": ".flowpilot/runs/<run-id>/evidence/flowguard/<packet-id>",
        },
        "formal_artifact_contract": {
            "artifact_id": str(contract["artifact_id"]),
            "required_field_paths": tuple(formal_artifact_contracts.required_field_paths(contract)),
            "allowed_value_options": dict(contract.get("allowed_value_options") or {}),
            "field_type_requirements": dict(contract.get("field_type_requirements") or {}),
        },
    }


FORMAL_ARTIFACT_EXHAUSTION_CONTRACTS = {
    str(contract["contract_id"]): _formal_artifact_exhaustion_contract(dict(contract))
    for contract in formal_artifact_contracts.all_contracts()
}
FORMAL_ARTIFACT_EXHAUSTION_CONTRACT_ID = str(
    formal_artifact_contracts.FLOWGUARD_FORMAL_ARTIFACT_CONTRACT["contract_id"]
)
FORMAL_ARTIFACT_EXHAUSTION_CONTRACT = FORMAL_ARTIFACT_EXHAUSTION_CONTRACTS[
    FORMAL_ARTIFACT_EXHAUSTION_CONTRACT_ID
]


def _packet_result_contract_field_cells() -> tuple[dict[str, str], ...]:
    cells: list[dict[str, str]] = []
    for row in packet_result_contracts.PACKET_RESULT_CONTRACTS:
        family_id = str(row["family_id"])
        packet_kind = str(row["packet_kind"])
        result_family = _contract_family_bucket(packet_kind)
        packet_family = _contract_packet_family_bucket(packet_kind)
        for mutation in MALFORMED_BODY_MUTATION_KINDS:
            cells.append(
                {
                    "cell_id": f"packet_result_contract.{family_id}.{mutation}.result_body",
                    "family": result_family,
                    "contract_family_id": family_id,
                    "contract_path": "result.body",
                    "mutation_kind": mutation,
                    "branch_kind": "synthetic_replay",
                    "confidence_boundary": "synthetic_non_live_control_flow",
                    "required_evidence_owner": "contract_exhaustion_fake_ai_matrix",
                }
            )
        for field in row.get("required_fields", ()):
            field_path = str(field)
            for mutation in ("missing_required_field", "wrong_type"):
                cells.append(
                    {
                        "cell_id": f"packet_result_contract.{family_id}.{mutation}.{_sanitize_path(field_path)}",
                        "family": result_family,
                        "contract_family_id": family_id,
                        "contract_path": field_path,
                        "mutation_kind": mutation,
                        "branch_kind": "ordinary_runtime",
                        "confidence_boundary": "current_runtime_contract",
                        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
                    }
                )
        for field in row.get("required_child_fields", ()):
            field_path = str(field)
            if " when " in field_path:
                branch_kind = "conditional_runtime"
            else:
                branch_kind = "ordinary_runtime"
            for mutation in ("missing_required_child_field", "wrong_type"):
                cells.append(
                    {
                        "cell_id": f"packet_result_contract.{family_id}.{mutation}.{_sanitize_path(field_path)}",
                        "family": result_family,
                        "contract_family_id": family_id,
                        "contract_path": field_path,
                        "mutation_kind": mutation,
                        "branch_kind": branch_kind,
                        "confidence_boundary": "current_runtime_contract",
                        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
                    }
                )
        for field in row.get("non_empty_array_fields", ()):
            field_path = str(field)
            cells.append(
                {
                    "cell_id": f"packet_result_contract.{family_id}.empty_required_array.{_sanitize_path(field_path)}",
                    "family": result_family,
                    "contract_family_id": family_id,
                    "contract_path": field_path,
                    "mutation_kind": "empty_required_array",
                    "branch_kind": "ordinary_runtime",
                    "confidence_boundary": "current_runtime_contract",
                    "required_evidence_owner": "contract_exhaustion_runtime_matrix",
                }
            )
        for field in row.get("forbidden_fields", ()):
            field_path = str(field)
            cells.append(
                {
                    "cell_id": f"packet_result_contract.{family_id}.forbidden_field_present.{_sanitize_path(field_path)}",
                    "family": result_family,
                    "contract_family_id": family_id,
                    "contract_path": field_path,
                    "mutation_kind": "forbidden_field_present",
                    "branch_kind": "negative_path",
                    "confidence_boundary": "current_runtime_contract",
                    "required_evidence_owner": "contract_exhaustion_runtime_matrix",
                }
            )
        for field in packet_result_contracts.allowed_value_options_for_family(family_id):
            field_path = str(field)
            cells.append(
                {
                    "cell_id": (
                        f"packet_result_contract.{family_id}.missing_allowed_value_options."
                        f"{_sanitize_path(field_path)}"
                    ),
                    "family": packet_family,
                    "contract_family_id": family_id,
                    "contract_path": (
                        "current_handoff_contract.required_report_contract."
                        f"allowed_value_options.{field_path}"
                    ),
                    "mutation_kind": "missing_allowed_value_options",
                    "branch_kind": "ordinary_runtime",
                    "confidence_boundary": "current_runtime_contract",
                    "required_evidence_owner": "contract_exhaustion_runtime_matrix",
                }
            )
            cells.append(
                {
                    "cell_id": (
                        f"packet_result_contract.{family_id}.wrong_allowed_value."
                        f"{_sanitize_path(field_path)}"
                    ),
                    "family": result_family,
                    "contract_family_id": family_id,
                    "contract_path": f"result.{field_path}",
                    "mutation_kind": "wrong_allowed_value",
                    "branch_kind": "synthetic_replay",
                    "confidence_boundary": "synthetic_non_live_control_flow",
                    "required_evidence_owner": "contract_exhaustion_fake_ai_matrix",
                }
            )
    return tuple(cells)


def _result_contract_profile_field_cells() -> tuple[dict[str, str], ...]:
    cells: list[dict[str, str]] = []
    for profile_id in packet_result_contracts.packet_stage_evidence_matrix.RESULT_CONTRACT_PROFILE_IDS:
        profile = packet_result_contracts.packet_stage_evidence_matrix.result_contract_profile(profile_id)
        family_id = str(profile["family_id"])
        contract_row = packet_result_contracts.contract_for_family(family_id) or {}
        packet_kind = str(contract_row.get("packet_kind") or "flowguard_check")
        packet_family = _contract_packet_family_bucket(packet_kind)
        result_family = _contract_family_bucket(packet_kind)
        sample_binding = PROFILE_EXHAUSTION_SAMPLE_BINDINGS.get(profile_id, {})
        effective_contract = packet_result_contracts.effective_result_contract_for_family(
            family_id,
            result_contract_profile_ids=(profile_id,),
            result_contract_profile_bindings={profile_id: sample_binding},
        )
        for field in profile.get("required_fields", ()):
            field_path = str(field)
            for mutation in ("missing_required_field", "wrong_type"):
                cells.append(
                    {
                        "cell_id": f"result_contract_profile.{profile_id}.{mutation}.{_sanitize_path(field_path)}",
                        "family": result_family,
                        "contract_family_id": profile_id,
                        "contract_path": field_path,
                        "mutation_kind": mutation,
                        "branch_kind": "conditional_runtime",
                        "confidence_boundary": "current_runtime_contract",
                        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
                    }
                )
        for field in profile.get("required_child_fields", ()):
            field_path = str(field)
            for mutation in ("missing_required_child_field", "wrong_type"):
                cells.append(
                    {
                        "cell_id": f"result_contract_profile.{profile_id}.{mutation}.{_sanitize_path(field_path)}",
                        "family": result_family,
                        "contract_family_id": profile_id,
                        "contract_path": field_path,
                        "mutation_kind": mutation,
                        "branch_kind": "conditional_runtime",
                        "confidence_boundary": "current_runtime_contract",
                        "required_evidence_owner": "contract_exhaustion_runtime_matrix",
                    }
                )
        for field in profile.get("non_empty_array_fields", ()):
            field_path = str(field)
            cells.append(
                {
                    "cell_id": f"result_contract_profile.{profile_id}.empty_required_array.{_sanitize_path(field_path)}",
                    "family": result_family,
                    "contract_family_id": profile_id,
                    "contract_path": field_path,
                    "mutation_kind": "empty_required_array",
                    "branch_kind": "conditional_runtime",
                    "confidence_boundary": "current_runtime_contract",
                    "required_evidence_owner": "contract_exhaustion_runtime_matrix",
                }
            )
        for field in (effective_contract.get("field_type_requirements") or {}):
            field_path = str(field)
            cells.append(
                {
                    "cell_id": (
                        f"result_contract_profile.{profile_id}.missing_field_type_requirements."
                        f"{_sanitize_path(field_path)}"
                    ),
                    "family": packet_family,
                    "contract_family_id": profile_id,
                    "contract_path": (
                        "current_handoff_contract.required_report_contract."
                        f"field_type_requirements.{field_path}"
                    ),
                    "mutation_kind": "missing_field_type_requirements",
                    "branch_kind": "conditional_runtime",
                    "confidence_boundary": "current_runtime_contract",
                    "required_evidence_owner": "contract_exhaustion_runtime_matrix",
                }
            )
            cells.append(
                {
                    "cell_id": f"result_contract_profile.{profile_id}.wrong_type.{_sanitize_path(field_path)}",
                    "family": result_family,
                    "contract_family_id": profile_id,
                    "contract_path": f"result.{field_path}",
                    "mutation_kind": "wrong_type",
                    "branch_kind": "conditional_runtime",
                    "confidence_boundary": "current_runtime_contract",
                    "required_evidence_owner": "contract_exhaustion_runtime_matrix",
                }
            )
        for alias in (effective_contract.get("forbidden_aliases") or {}):
            alias_path = str(alias)
            cells.append(
                {
                    "cell_id": (
                        f"result_contract_profile.{profile_id}.forbidden_alias_used."
                        f"{_sanitize_path(alias_path)}"
                    ),
                    "family": packet_family,
                    "contract_family_id": profile_id,
                    "contract_path": (
                        "current_handoff_contract.required_report_contract."
                        f"forbidden_aliases.{alias_path}"
                    ),
                    "mutation_kind": "forbidden_alias_used",
                    "branch_kind": "conditional_runtime",
                    "confidence_boundary": "current_runtime_contract",
                    "required_evidence_owner": "contract_exhaustion_runtime_matrix",
                }
            )
            cells.append(
                {
                    "cell_id": (
                        f"result_contract_profile.{profile_id}.forbidden_alias_result."
                        f"{_sanitize_path(alias_path)}"
                    ),
                    "family": result_family,
                    "contract_family_id": profile_id,
                    "contract_path": f"result.{alias_path}",
                    "mutation_kind": "forbidden_alias_used",
                    "branch_kind": "synthetic_replay",
                    "confidence_boundary": "synthetic_non_live_control_flow",
                    "required_evidence_owner": "contract_exhaustion_fake_ai_matrix",
                }
            )
        base_allowed_fields = set(packet_result_contracts.allowed_value_options_for_family(family_id))
        profile_allowed_fields = sorted(
            str(field)
            for field in (effective_contract.get("allowed_value_options") or {})
            if str(field) not in base_allowed_fields
        )
        for field_path in profile_allowed_fields:
            cells.append(
                {
                    "cell_id": (
                        f"result_contract_profile.{profile_id}.missing_allowed_value_options."
                        f"{_sanitize_path(field_path)}"
                    ),
                    "family": packet_family,
                    "contract_family_id": profile_id,
                    "contract_path": (
                        "current_handoff_contract.required_report_contract."
                        f"allowed_value_options.{field_path}"
                    ),
                    "mutation_kind": "missing_allowed_value_options",
                    "branch_kind": "conditional_runtime",
                    "confidence_boundary": "current_runtime_contract",
                    "required_evidence_owner": "contract_exhaustion_runtime_matrix",
                }
            )
            cells.append(
                {
                    "cell_id": (
                        f"result_contract_profile.{profile_id}.wrong_allowed_value."
                        f"{_sanitize_path(field_path)}"
                    ),
                    "family": result_family,
                    "contract_family_id": profile_id,
                    "contract_path": f"result.{field_path}",
                    "mutation_kind": "wrong_allowed_value",
                    "branch_kind": "synthetic_replay",
                    "confidence_boundary": "synthetic_non_live_control_flow",
                    "required_evidence_owner": "contract_exhaustion_fake_ai_matrix",
                }
            )
    return tuple(cells)


def _formal_artifact_contract_cells() -> tuple[dict[str, str], ...]:
    cells: list[dict[str, str]] = []
    for contract in formal_artifact_contracts.all_contracts():
        decision_field = str(contract["decision_field_path"])
        contract_id = str(contract["contract_id"])
        for profile_id in formal_artifact_contracts.fault_modes(contract):
            path = formal_artifact_contracts.artifact_contract_path(contract)
            if profile_id in {
                "missing_formal_artifact_decision",
                "wrong_formal_artifact_decision",
                "body_pass_artifact_blocks",
            }:
                path = formal_artifact_contracts.artifact_contract_path(contract, decision_field)
            cells.append(
                {
                    "cell_id": f"formal_artifact.{contract_id}.{profile_id}",
                    "family": str(contract.get("contract_exhaustion_family") or ""),
                    "contract_family_id": contract_id,
                    "contract_path": path,
                    "mutation_kind": profile_id,
                    "branch_kind": "synthetic_replay",
                    "confidence_boundary": "synthetic_non_live_control_flow",
                    "required_evidence_owner": "contract_exhaustion_fake_ai_matrix",
                }
            )
    return tuple(cells)


def _control_plane_required_path_cells() -> tuple[dict[str, str], ...]:
    cells: list[dict[str, str]] = []
    for row in CONTROL_PLANE_REQUIRED_PATHS:
        for mutation in row["mutation_kinds"]:
            synthetic = mutation in SYNTHETIC_MUTATION_KINDS
            cells.append(
                {
                    "cell_id": f"control_plane.{row['family']}.{mutation}.{_sanitize_path(str(row['path']))}",
                    "family": str(row["family"]),
                    "contract_family_id": str(row["family"]),
                    "contract_path": str(row["path"]),
                    "mutation_kind": str(mutation),
                    "branch_kind": "synthetic_replay" if synthetic else "ordinary_runtime",
                    "confidence_boundary": (
                        "synthetic_non_live_control_flow"
                        if synthetic
                        else "current_runtime_contract"
                    ),
                    "required_evidence_owner": str(row["required_evidence_owner"]),
                }
            )
    return tuple(cells)


def _historical_failure_family_cells() -> tuple[dict[str, object], ...]:
    cells: list[dict[str, object]] = []
    for row in HISTORICAL_FAILURE_FAMILIES:
        for mutation in row["mutation_kinds"]:
            cells.append(
                {
                    "cell_id": f"{row['failure_id']}.{mutation}",
                    "family": str(row["family"]),
                    "contract_family_id": str(row["failure_id"]),
                    "contract_path": str(row["historical_source"]),
                    "mutation_kind": str(mutation),
                    "branch_kind": "historical_failure_replay",
                    "confidence_boundary": "historical_same_class_non_live_control_flow",
                    "required_evidence_owner": "contract_exhaustion_historical_failure_matrix",
                    "source_class": str(row["source_class"]),
                    "normal_repair_route": str(row["normal_repair_route"]),
                    "glass_break_allowed_in_acceptance": bool(row["glass_break_allowed_in_acceptance"]),
                    "alarm_required_after_same_blocker_attempts": row.get(
                        "alarm_required_after_same_blocker_attempts"
                    ),
                }
            )
    return tuple(cells)


def _integration_cartesian_coverage_cells() -> tuple[dict[str, str], ...]:
    shard_ids = sorted({str(cell["coverage_shard_id"]) for cell in integration_cartesian_cells()})
    return tuple(
        {
            "cell_id": f"integration_cartesian_coverage.{_sanitize_path(shard_id)}",
            "family": "integration_cartesian_coverage",
            "contract_family_id": "flowpilot_integration_cartesian_coverage",
            "contract_path": shard_id,
            "mutation_kind": "missing_integration_cartesian_shard",
            "branch_kind": "executable_flowguard_cartesian",
            "confidence_boundary": "prompt_workflow_integration_coverage",
            "required_evidence_owner": "integration_cartesian_coverage_matrix",
        }
        for shard_id in shard_ids
    )


STATIC_CONTRACT_EXHAUSTION_CELLS = REQUIRED_CONTRACT_EXHAUSTION_CELLS
REQUIRED_CONTRACT_EXHAUSTION_CELLS = (
    *STATIC_CONTRACT_EXHAUSTION_CELLS,
    *_packet_result_contract_field_cells(),
    *_result_contract_profile_field_cells(),
    *_formal_artifact_contract_cells(),
    *_control_plane_required_path_cells(),
    *_historical_failure_family_cells(),
    *_integration_cartesian_coverage_cells(),
    *review_window_contracts.review_window_completeness_cells(),
    *runtime_replay_cells(),
    *backfeed_cells(),
)


@dataclass(frozen=True)
class State:
    scenario: str = "new"
    status: str = "new"
    malformed_input_seen: bool = False
    current_subject_named: bool = False
    owner_named: bool = False
    missing_or_invalid_fields_named: bool = False
    minimum_valid_shape_named: bool = False
    legal_repair_command_named: bool = False
    flowguard_policy_preserved_on_reissue: bool = True
    flowguard_evidence_root_retargeted: bool = True
    flowguard_authorized_reads_preserved_on_reissue: bool = True
    flowguard_reissue_body_open_gate_preserved: bool = True
    reviewer_requires_flowguard: bool = False
    reviewer_manifest_empty: bool = False
    reviewer_packet_issued: bool = False
    system_validation_late_failure: bool = False
    accepted_result_work_order_split: bool = False
    same_root_no_delta_retry: bool = False
    repeated_same_blocker_attempts: int = 0
    break_glass_triggered: bool = False
    normal_repair_prevents_glass_break: bool = False
    blocker_or_repair_disposition: bool = False
    synthetic_evidence_only: bool = False
    live_ai_quality_claimed: bool = False
    required_cell_owner_complete: bool = True
    required_cell_test_current: bool = True


@dataclass(frozen=True)
class Tick:
    """One contract-exhaustion matrix decision."""


@dataclass(frozen=True)
class Action:
    name: str


class Transition(NamedTuple):
    label: str
    state: State


def _valid_contract_rejection() -> State:
    return State(
        scenario="valid_contract_rejection",
        status="selected",
        malformed_input_seen=True,
        current_subject_named=True,
        owner_named=True,
        missing_or_invalid_fields_named=True,
        minimum_valid_shape_named=True,
        legal_repair_command_named=True,
        blocker_or_repair_disposition=True,
    )


def _valid_flowguard_reissue() -> State:
    return State(
        scenario="valid_flowguard_reissue",
        status="selected",
        malformed_input_seen=True,
        current_subject_named=True,
        owner_named=True,
        missing_or_invalid_fields_named=True,
        minimum_valid_shape_named=True,
        legal_repair_command_named=True,
        flowguard_policy_preserved_on_reissue=True,
        flowguard_evidence_root_retargeted=True,
        flowguard_authorized_reads_preserved_on_reissue=True,
        flowguard_reissue_body_open_gate_preserved=True,
        blocker_or_repair_disposition=True,
    )


def _valid_missing_flowguard_blocks_review() -> State:
    return State(
        scenario="valid_missing_flowguard_blocks_review",
        status="selected",
        reviewer_requires_flowguard=True,
        reviewer_manifest_empty=True,
        reviewer_packet_issued=False,
        blocker_or_repair_disposition=True,
    )


def _valid_break_glass_same_root() -> State:
    return State(
        scenario="valid_same_root_repaired_before_glass_break",
        status="selected",
        same_root_no_delta_retry=True,
        repeated_same_blocker_attempts=2,
        break_glass_triggered=False,
        normal_repair_prevents_glass_break=True,
        blocker_or_repair_disposition=True,
    )


SCENARIOS = {
    "valid_contract_rejection": _valid_contract_rejection(),
    "valid_flowguard_reissue": _valid_flowguard_reissue(),
    "valid_missing_flowguard_blocks_review": _valid_missing_flowguard_blocks_review(),
    "valid_same_root_repaired_before_glass_break": _valid_break_glass_same_root(),
    "vague_rejection_feedback": replace(
        _valid_contract_rejection(),
        scenario="vague_rejection_feedback",
        missing_or_invalid_fields_named=False,
        minimum_valid_shape_named=False,
    ),
    "flowguard_reissue_loses_policy": replace(
        _valid_flowguard_reissue(),
        scenario="flowguard_reissue_loses_policy",
        flowguard_policy_preserved_on_reissue=False,
    ),
    "flowguard_reissue_reuses_old_evidence_root": replace(
        _valid_flowguard_reissue(),
        scenario="flowguard_reissue_reuses_old_evidence_root",
        flowguard_evidence_root_retargeted=False,
    ),
    "flowguard_reissue_loses_authorized_reads": replace(
        _valid_flowguard_reissue(),
        scenario="flowguard_reissue_loses_authorized_reads",
        flowguard_authorized_reads_preserved_on_reissue=False,
    ),
    "flowguard_reissue_loses_required_body_open_gate": replace(
        _valid_flowguard_reissue(),
        scenario="flowguard_reissue_loses_required_body_open_gate",
        flowguard_reissue_body_open_gate_preserved=False,
    ),
    "empty_manifest_review_issued": replace(
        _valid_missing_flowguard_blocks_review(),
        scenario="empty_manifest_review_issued",
        reviewer_packet_issued=True,
        blocker_or_repair_disposition=False,
    ),
    "accepted_result_work_order_split": replace(
        _valid_missing_flowguard_blocks_review(),
        scenario="accepted_result_work_order_split",
        accepted_result_work_order_split=True,
        reviewer_packet_issued=True,
        blocker_or_repair_disposition=False,
    ),
    "system_validation_catches_missing_flowguard_late": replace(
        _valid_missing_flowguard_blocks_review(),
        scenario="system_validation_catches_missing_flowguard_late",
        reviewer_packet_issued=True,
        system_validation_late_failure=True,
    ),
    "same_root_no_delta_without_break_glass": replace(
        _valid_break_glass_same_root(),
        scenario="same_root_no_delta_without_break_glass",
        repeated_same_blocker_attempts=6,
        break_glass_triggered=False,
        normal_repair_prevents_glass_break=False,
    ),
    "same_blocker_six_times_triggers_glass_break_alarm": replace(
        _valid_break_glass_same_root(),
        scenario="same_blocker_six_times_triggers_glass_break_alarm",
        repeated_same_blocker_attempts=6,
        break_glass_triggered=True,
        normal_repair_prevents_glass_break=False,
    ),
    "ordinary_rehearsal_enters_glass_break": replace(
        _valid_break_glass_same_root(),
        scenario="ordinary_rehearsal_enters_glass_break",
        repeated_same_blocker_attempts=3,
        break_glass_triggered=True,
        normal_repair_prevents_glass_break=False,
    ),
    "synthetic_live_quality_overclaim": replace(
        _valid_contract_rejection(),
        scenario="synthetic_live_quality_overclaim",
        synthetic_evidence_only=True,
        live_ai_quality_claimed=True,
    ),
    "required_cell_missing_owner": replace(
        _valid_contract_rejection(),
        scenario="required_cell_missing_owner",
        required_cell_owner_complete=False,
    ),
    "required_cell_stale_test": replace(
        _valid_contract_rejection(),
        scenario="required_cell_stale_test",
        required_cell_test_current=False,
    ),
}

VALID_SCENARIOS = {
    "valid_contract_rejection",
    "valid_flowguard_reissue",
    "valid_missing_flowguard_blocks_review",
    "valid_same_root_repaired_before_glass_break",
    "same_blocker_six_times_triggers_glass_break_alarm",
}
NEGATIVE_SCENARIOS = set(SCENARIOS) - VALID_SCENARIOS


def contract_exhaustion_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.malformed_input_seen:
        if not state.current_subject_named:
            failures.append("contract_feedback_missing_current_subject")
        if not state.owner_named:
            failures.append("contract_feedback_missing_owner")
        if not state.missing_or_invalid_fields_named:
            failures.append("contract_feedback_missing_field_details")
        if not state.minimum_valid_shape_named:
            failures.append("contract_feedback_missing_minimum_valid_shape")
        if not state.legal_repair_command_named:
            failures.append("contract_feedback_missing_legal_repair_command")
    if not state.flowguard_policy_preserved_on_reissue:
        failures.append("flowguard_reissue_lost_evidence_output_policy")
    if not state.flowguard_evidence_root_retargeted:
        failures.append("flowguard_reissue_reused_old_evidence_root")
    if not state.flowguard_authorized_reads_preserved_on_reissue:
        failures.append("flowguard_reissue_lost_authorized_result_reads")
    if not state.flowguard_reissue_body_open_gate_preserved:
        failures.append("flowguard_reissue_lost_required_body_open_gate")
    if state.reviewer_requires_flowguard and state.reviewer_manifest_empty and state.reviewer_packet_issued:
        failures.append("reviewer_packet_issued_with_empty_required_flowguard_manifest")
    if state.system_validation_late_failure and state.reviewer_packet_issued:
        failures.append("missing_flowguard_report_detected_too_late")
    if state.accepted_result_work_order_split:
        failures.append("flowguard_result_acceptance_split_from_work_order_failure")
    if (
        state.same_root_no_delta_retry
        and state.repeated_same_blocker_attempts > 5
        and not state.break_glass_triggered
    ):
        failures.append("same_root_no_delta_retry_did_not_trigger_break_glass")
    if state.break_glass_triggered and not (
        state.same_root_no_delta_retry and state.repeated_same_blocker_attempts > 5
    ):
        failures.append("ordinary_rehearsal_entered_glass_break")
    if (
        state.reviewer_requires_flowguard
        and state.reviewer_manifest_empty
        and not state.reviewer_packet_issued
        and not state.blocker_or_repair_disposition
    ):
        failures.append("missing_flowguard_report_has_no_repair_disposition")
    if state.synthetic_evidence_only and state.live_ai_quality_claimed:
        failures.append("synthetic_evidence_overclaims_live_ai_quality")
    if not state.required_cell_owner_complete:
        failures.append("required_contract_exhaustion_cell_missing_owner")
    if not state.required_cell_test_current:
        failures.append("required_contract_exhaustion_cell_stale_or_missing_test")
    return sorted(set(failures))


def initial_state() -> State:
    return State()


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "new":
        for name, scenario in sorted(SCENARIOS.items()):
            yield Transition(f"select_{name}", scenario)
        return
    if state.status == "selected":
        failures = contract_exhaustion_failures(state)
        terminal = "rejected" if failures else "accepted"
        yield Transition(f"{terminal.removesuffix('ed')}_{state.scenario}", replace(state, status=terminal))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted"


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return is_terminal(state)


class ContractExhaustionStep:
    """Classify one current-contract mutation cell.

    Input x State -> Set(Output x State)
    reads: packet/result bodies, FlowGuard work orders, review manifests,
    repair blockers, and synthetic trace ownership
    writes: one accepted safe disposition or one blocking diagnostic
    idempotency: pure classification keyed by model id, cell id, and run source generation
    """

    name = "ContractExhaustionStep"
    reads = (
        "packet_result_contract",
        "flowguard_evidence_policy",
        "review_flowguard_manifest",
        "system_validation_blockers",
        "repair_loop_history",
        "synthetic_coverage_rows",
    )
    writes = ("contract_exhaustion_decision", "required_cell_coverage_finding")
    input_description = "one required current-contract mutation cell"
    output_description = "safe continuation, repair blocker, or hard diagnostic"
    idempotency = "classification is keyed by run id, subject packet/result id, and matrix cell id"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def accepted_states_are_safe(state: State, _trace: object) -> InvariantResult:
    if state.status == "accepted":
        failures = contract_exhaustion_failures(state)
        if failures:
            return InvariantResult.fail("; ".join(failures))
    if state.status == "rejected" and not contract_exhaustion_failures(state):
        return InvariantResult.fail("safe contract-exhaustion state was rejected")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "accepted_states_are_safe",
        "Accepted contract-exhaustion states cannot contain unclear rejection feedback, FlowGuard evidence loss, empty required reviewer manifests, split-brain evidence, or unabsorbed no-delta loops.",
        accepted_states_are_safe,
    ),
)
EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((ContractExhaustionStep(),), name=MODEL_ID)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(str(result.message))
    return failures


def hazard_states() -> dict[str, State]:
    return {name: SCENARIOS[name] for name in sorted(NEGATIVE_SCENARIOS)}


def expected_failures_by_hazard() -> dict[str, list[str]]:
    return {name: contract_exhaustion_failures(state) for name, state in hazard_states().items()}
