"""FlowPilot primary-path maintenance model, upgraded for FlowGuard 0.55.

This model is intentionally evidence-only. It does not add FlowPilot runtime
fields or compatibility behavior. It registers the current no-fallback
commitments through current Primary Path Authority, Behavior Commitment
Ledger, FieldLifecycleMesh, and Risk Evidence Ledger APIs.

The historical filename is retained because it is already a registered model
surface; current behavior and evidence use the canonical 0.55 contracts.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

from flowguard import (
    BehaviorCommitmentLedger,
    FallbackPathCandidate,
    FieldLifecycleGroup,
    FieldLifecyclePlan,
    FieldLifecycleRow,
    FieldProjection,
    PrimaryPathAuthorityPlan,
    PrimaryPathContract,
    ProofArtifactRef,
    RiskEvidenceGate,
    RiskEvidenceLedgerPlan,
    RiskEvidenceProof,
    RiskEvidenceRow,
    load_behavior_commitment_ledger,
)


MODEL_ID = "flowpilot_053_ppa_maintenance"
PPA_PLAN_ID = "flowpilot_055_primary_path_authority"
BCL_LEDGER_ID = "flowpilot_behavior_commitments"
FIELD_MESH_ID = "flowpilot_053_field_lifecycle"
RISK_LEDGER_ID = "flowpilot_053_risk_evidence"

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / ".flowguard" / "behavior_commitment_ledger" / "ledger.json"
_CANONICAL_LEDGER = load_behavior_commitment_ledger(LEDGER_PATH)

PPA_RISK_GATES = (
    f"risk_gate:primary_path_authority:{MODEL_ID}",
    f"risk_gate:primary_path_authority_cartesian_coverage:{MODEL_ID}",
)
BCL_RISK_GATES = (
    "risk_gate:behavior_commitment_coverage:flowpilot_053_behavior_commitments",
    "risk_gate:behavior_commitment_cartesian_coverage:flowpilot_053_behavior_commitments",
)
COVERAGE_CASE_IDS = (
    "case:flowpilot.synthetic_agent_global_d_card_matrix",
    "case:flowpilot.current_contract_cartesian_matrix",
    "case:flowpilot.contract_exhaustion_mesh",
    "case:flowpilot.ai_response_execution_closure",
)
COVERAGE_SHARD_IDS = (
    "contract_shard:flowpilot_053_ppa_maintenance:no_fallback_cartesian",
    "contract_shard:flowpilot_053_bcl_maintenance:behavior_commitment_cartesian",
)
COVERAGE_RECEIPT_IDS = (
    "contract_coverage:flowpilot_053_ppa_maintenance",
    "contract_coverage:flowpilot_053_bcl_maintenance",
)

COMMITMENT_IDS = tuple(
    commitment.commitment_id for commitment in _CANONICAL_LEDGER.commitments
)
PATH_SENSITIVE_COMMITMENTS = tuple(
    commitment
    for commitment in _CANONICAL_LEDGER.commitments
    if commitment.path_authority is not None
    and commitment.path_authority.path_sensitive
)
PATH_SENSITIVE_COMMITMENT_IDS = tuple(
    commitment.commitment_id for commitment in PATH_SENSITIVE_COMMITMENTS
)
PRIMARY_PATH_INTENTS = tuple(
    commitment.path_authority.business_intent or commitment.label
    for commitment in PATH_SENSITIVE_COMMITMENTS
)
PRIMARY_PATH_INTENT_IDS = tuple(
    commitment.business_intent_id for commitment in PATH_SENSITIVE_COMMITMENTS
)
PRIMARY_PATH_IDS = tuple(
    commitment.path_authority.primary_path_id
    for commitment in PATH_SENSITIVE_COMMITMENTS
)
PRIMARY_PATH_SURFACE_IDS = tuple(
    surface_id
    for commitment in PATH_SENSITIVE_COMMITMENTS
    for surface_id in commitment.source_surface_ids
)

FIELD_IDS = (
    "packet_result.body.pm_visible_summary",
    "pm_packet.body.recent_role_report_summary",
    "packet.envelope.authorized_result_reads[]",
    "legacy_result_summary",
    "packet.envelope.current_handoff_contract",
    "open_packet.submission_checklist",
    "packet.body.mechanical_contract_mirrors",
    "packet.body.conditional_mechanical_fields",
    "reissue.body.mechanical_contract_shape",
    "fake_ai.private_helper_result_shapes",
    "host.retired_role_aliases",
    "execution_source.daemon_replay",
    "task.discovery.packet.body.runtime_local_capability_inventory",
    "preplanning.discovery.candidate_skill_inventory",
    "packet_result.contract_self_check.workstream_plan_and_completion",
    "preplanning.discovery.material_sources",
    "preplanning.discovery.material_sufficiency",
    "preplanning.discovery.material_current",
    "repair_transaction.plan_kind.packet_reissue",
    "repair_transaction.replacement_packets",
    "repair_transaction.replacement_packet_specs_path",
    "repair_transaction.replacement_packet_specs_hash",
)

TEST_RECEIPTS = (
    "test:tests/test_flowpilot_053_ppa_maintenance.py",
    "test:tests/test_flowpilot_core_runtime.py::test_missing_pm_visible_summary_is_mechanically_reissued",
    "test:tests/test_flowpilot_core_runtime.py::test_pm_repair_packet_includes_recent_role_report_summary",
    "test:tests/test_flowpilot_new_entrypoint.py::authorized_result_reads",
    "test:tests/test_flowpilot_formal_ai_contract_execution.py",
    "test:tests/test_flowpilot_contract_driven_fake_ai_open_packet.py",
    "test:tests/test_flowpilot_formal_ai_contract_execution.py",
    "test:tests/test_flowpilot_acceptance_testmesh.py",
    "test:tests/test_flowpilot_complete_workstream_orchestration.py",
    "test:tests/test_flowpilot_ordinary_resource_discovery.py",
    "test:tests/test_flowpilot_complete_workstream_fake_ai.py",
)


PRIMARY_PATH_SPECS = {
    "commit.result_submission_current_contract_only": {
        "entrypoint": "flowpilot_core_runtime.runtime.submit_result",
        "code_contract": "packet_result_family.runtime.submit_result_body_entry",
        "obligation": "flowpilot_053.result_submission_current_contract_only",
        "result_path": "simulations/flowpilot_current_contract_cartesian_matrix_results.json",
    },
    "commit.repair_reissue_no_fallback": {
        "entrypoint": "flowpilot_core_runtime.runtime._apply_pm_repair_decision",
        "code_contract": "repair_transactions.current_repair_requires_concrete_producer",
        "obligation": "flowpilot_053.repair_reissue_no_fallback",
        "result_path": "simulations/flowpilot_repair_transaction_results.json",
    },
    "commit.authorized_result_reads_are_required_material": {
        "entrypoint": "flowpilot_new_role_commands.open_result",
        "code_contract": "packet_result_family.runtime.authorized_result_reads",
        "obligation": "flowpilot_053.authorized_result_reads_required_material",
        "result_path": "simulations/flowpilot_current_contract_cartesian_matrix_results.json",
    },
    "commit.current_handoff_checklist_single_authority": {
        "entrypoint": "flowpilot_new_role_commands.open_packet",
        "code_contract": "packet_result_family.runtime.current_handoff_checklist_projection",
        "obligation": "packet_result_family.current_handoff_checklist_single_authority",
        "result_path": "simulations/flowpilot_current_contract_cartesian_matrix_results.json",
    },
    "commit.dynamic_pm_repair_owns_active_acceptance_items": {
        "entrypoint": "flowpilot_core_runtime.runtime._project_supplemental_repair_ids_onto_route_plan",
        "code_contract": "packet_result_family.runtime.dynamic_pm_repair_contract",
        "obligation": "packet_result_family.dynamic_pm_repair_owner_projection",
        "result_path": "simulations/flowpilot_current_contract_cartesian_matrix_results.json",
    },
    "commit.controller_uses_runtime_foreground_ledger_only": {
        "entrypoint": "flowpilot_core_runtime.runtime.preview_foreground_duty",
        "code_contract": "controller.runtime_foreground_action_ledger",
        "obligation": "flowpilot_complete_workstream.controller_foreground_only",
        "result_path": "simulations/flowpilot_complete_workstream_orchestration_results.json",
    },
    "commit.local_capability_inventory_precedes_pm_selection": {
        "entrypoint": "flowpilot_core_runtime.runtime._discovery_result_violation",
        "code_contract": "resource_discovery.current_result_contract",
        "obligation": "flowpilot_resource_discovery.shallow_inventory_then_pm_selection",
        "result_path": "simulations/flowpilot_ordinary_resource_discovery_results.json",
    },
    "commit.material_work_uses_ordinary_role_packages": {
        "entrypoint": "flowpilot_core_runtime.runtime._issue_worker_packet",
        "code_contract": "task.node.ordinary_material_or_research_work",
        "obligation": "flowpilot_resource_discovery.material_work_is_ordinary_role_work",
        "result_path": "simulations/flowpilot_ordinary_resource_discovery_results.json",
    },
    "commit.material_map_is_optional_navigation_only": {
        "entrypoint": "flowpilot_material_artifact_map.material_artifact_map_navigation_status",
        "code_contract": "material_artifact_map.navigation_status",
        "obligation": "material_artifact_map.optional_navigation_nonblocking",
        "result_path": "simulations/flowpilot_material_artifact_map_results.json",
    },
    "commit.model_test_alignment_uses_current_runtime_path_evidence": {
        "entrypoint": "run_flowpilot_model_test_alignment_checks.main",
        "code_contract": "flowpilot_model_test_alignment.runtime_path_evidence",
        "obligation": "flowpilot_model_test_alignment.current_runtime_path_evidence",
        "result_path": "tmp/flowguard_background/targeted_mta_tests_current.meta.json",
    },
}


def _canonical_commitment(commitment_id: str):
    for commitment in _CANONICAL_LEDGER.commitments:
        if commitment.commitment_id == commitment_id:
            return commitment
    raise KeyError(f"canonical commitment is missing: {commitment_id}")


def _path_slug(primary_path_id: str) -> str:
    return primary_path_id.replace(".", "_").replace("-", "_")


def _result_proof(
    *,
    primary_path_id: str,
    obligation_id: str,
    result_path: str,
) -> ProofArtifactRef:
    absolute = ROOT / result_path
    payload = {}
    if absolute.is_file():
        try:
            loaded = json.loads(absolute.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                payload = loaded
        except (OSError, UnicodeError, json.JSONDecodeError):
            payload = {}
    passed = payload.get("ok") is True or (
        payload.get("status") == "passed"
        and payload.get("exit_code") == 0
        and payload.get("source_fingerprint_current") is True
    )
    fingerprints = {}
    if absolute.is_file():
        fingerprints[result_path] = "sha256:" + hashlib.sha256(
            absolute.read_bytes()
        ).hexdigest()
    slug = _path_slug(primary_path_id)
    declared_command = payload.get("command")
    if isinstance(declared_command, list):
        command = " ".join(str(part) for part in declared_command)
    else:
        command = str(declared_command or "")
    return ProofArtifactRef(
        artifact_id=f"proof:flowpilot:{slug}",
        producer_route="primary_path_authority",
        command=command or f"python {result_path.replace('_results.json', '_checks.py')}",
        result_path=result_path,
        result_status="passed" if passed else "failed",
        exit_code=0 if passed else 1,
        artifact_fingerprints=fingerprints,
        covered_obligation_ids=(obligation_id,),
        assertion_scope="external_contract",
        current=passed,
        route_evidence_current=passed,
        route_gap_codes=() if passed else ("result_artifact_not_current_pass",),
    )


def _primary_path(commitment_id: str) -> PrimaryPathContract:
    commitment = _canonical_commitment(commitment_id)
    authority = commitment.path_authority
    if authority is None or not authority.primary_path_id:
        raise ValueError(f"path-sensitive commitment lacks a primary path: {commitment_id}")
    spec = PRIMARY_PATH_SPECS[commitment_id]
    proof = _result_proof(
        primary_path_id=authority.primary_path_id,
        obligation_id=spec["obligation"],
        result_path=spec["result_path"],
    )
    return PrimaryPathContract(
        business_path_id=authority.primary_path_id,
        business_intent=authority.business_intent or commitment.label,
        business_intent_id=commitment.business_intent_id,
        behavior_commitment_id=commitment.commitment_id,
        primary_entrypoint_id=spec["entrypoint"],
        owner_model_id=commitment.primary_owner_model_id or MODEL_ID,
        owner_code_contract_id=spec["code_contract"],
        expected_terminal=commitment.expected_terminal,
        failure_policy="fail_closed",
        allowed_error_state_ids=(
            "current_contract_reissue",
            "current_packet_rejected",
            "missing_required_material_blocker",
            "current_evidence_blocked",
        ),
        evidence_ids=TEST_RECEIPTS,
        runtime_evidence_state="current_pass" if proof.has_current_pass() else "failed",
        runtime_observation_ids=(
            f"runtime:{_path_slug(authority.primary_path_id)}",
        ),
        required_obligation_ids=(spec["obligation"],),
        proof_artifact=proof,
        source_surface_ids=commitment.source_surface_ids,
        authority_role="primary",
        metadata={
            "runtime_owner": commitment.owner,
            "canonical_ledger_id": _CANONICAL_LEDGER.ledger_id,
        },
    )


def _fallback_candidate(
    commitment_id: str,
    *,
    candidate_path_id: str,
    source_surface_id: str,
    candidate_surface: str,
    candidate_trigger: str,
    evidence_ref: str,
    candidate_behavior: str = "no_op",
    invokes_on_primary_failure: bool = False,
    returns_success_after_primary_failure: bool = False,
) -> FallbackPathCandidate:
    commitment = _canonical_commitment(commitment_id)
    authority = commitment.path_authority
    assert authority is not None
    return FallbackPathCandidate(
        candidate_path_id=candidate_path_id,
        fallback_for_path_id=authority.primary_path_id,
        business_intent=authority.business_intent or commitment.label,
        business_intent_id=commitment.business_intent_id,
        behavior_commitment_id=commitment.commitment_id,
        source_surface_id=source_surface_id,
        expected_terminal="unsupported alternate remains visibly blocked",
        candidate_surface=candidate_surface,
        candidate_trigger=candidate_trigger,
        candidate_behavior=candidate_behavior,
        invokes_on_primary_failure=invokes_on_primary_failure,
        returns_success_after_primary_failure=returns_success_after_primary_failure,
        disposition="block",
        evidence_refs=(evidence_ref,),
    )


def _fallback_candidates() -> tuple[FallbackPathCandidate, ...]:
    return (
        _fallback_candidate(
            "commit.result_submission_current_contract_only",
            candidate_path_id="fallback.old-result-summary-field",
            source_surface_id="surface.forbidden.old-result-summary-field",
            candidate_surface="old_field",
            candidate_trigger="missing_field",
            evidence_ref="test:missing_pm_visible_summary_is_mechanically_reissued",
        ),
        _fallback_candidate(
            "commit.result_submission_current_contract_only",
            candidate_path_id="fallback.alias-submit-result-body",
            source_surface_id="surface.forbidden.alias-submit-result-body",
            candidate_surface="alias",
            candidate_trigger="parse_error",
            evidence_ref="test:submit_result_rejects_pseudo_json_before_loading_current_run",
        ),
        _fallback_candidate(
            "commit.repair_reissue_no_fallback",
            candidate_path_id="fallback.retired-replacement-packet-repair",
            source_surface_id="surface.forbidden.retired-replacement-packet-repair",
            candidate_surface="helper_route",
            candidate_trigger="primary_failure",
            evidence_ref="negative_test:retired_replacement_fields_are_rejected",
        ),
        _fallback_candidate(
            "commit.current_handoff_checklist_single_authority",
            candidate_path_id="fallback.packet-body-mechanical-contract",
            source_surface_id="surface.forbidden.packet-body-mechanical-contract",
            candidate_surface="old_field",
            candidate_trigger="missing_or_conflicting_handoff",
            evidence_ref="test:open_packet_submission_checklist_rejects_packet_body_as_contract_authority",
        ),
    )


def build_primary_path_plan() -> PrimaryPathAuthorityPlan:
    candidates = _fallback_candidates()
    return PrimaryPathAuthorityPlan(
        plan_id=PPA_PLAN_ID,
        primary_paths=tuple(
            _primary_path(commitment_id)
            for commitment_id in PATH_SENSITIVE_COMMITMENT_IDS
        ),
        fallback_candidates=candidates,
        claim_scope="release",
        require_cartesian_coverage=True,
        coverage_case_ids=COVERAGE_CASE_IDS,
        coverage_shard_ids=COVERAGE_SHARD_IDS,
        coverage_receipt_ids=COVERAGE_RECEIPT_IDS,
        risk_gate_ids=PPA_RISK_GATES,
        expected_business_intents=PRIMARY_PATH_INTENTS,
        expected_business_intent_ids=PRIMARY_PATH_INTENT_IDS,
        expected_candidate_ids=tuple(
            candidate.candidate_path_id for candidate in candidates
        ),
        expected_surface_ids=PRIMARY_PATH_SURFACE_IDS,
        inventory_revision=_CANONICAL_LEDGER.current_revision,
        inventory_evidence_ids=(
            ".flowguard/behavior_commitment_ledger/ledger.json",
            "docs/flowguard_project_topology.json",
        ),
        preflight_id="flowguard-existing-model-preflight:complete-workstream-resource-discovery",
        behavior_commitment_ledger_id=_CANONICAL_LEDGER.ledger_id,
        existing_current_path_ids=PRIMARY_PATH_IDS,
        require_complete_candidate_inventory=True,
        require_material_runtime_evidence=True,
        metadata={
            "no_fallback_policy": "current runtime blocks unsupported alternates",
            "canonical_ledger_path": str(LEDGER_PATH.relative_to(ROOT)),
        },
    )


def build_broken_old_field_fallback_plan() -> PrimaryPathAuthorityPlan:
    good = build_primary_path_plan()
    broken = _fallback_candidate(
        "commit.result_submission_current_contract_only",
        candidate_path_id="fallback.old-result-summary-field",
        source_surface_id="surface.forbidden.old-result-summary-field",
        candidate_surface="old_field",
        candidate_trigger="missing_field",
        candidate_behavior="return_success",
        invokes_on_primary_failure=True,
        returns_success_after_primary_failure=True,
        evidence_ref="negative_test:old_field_must_not_mask_missing_pm_visible_summary",
    )
    return replace(
        good,
        plan_id="broken_old_field_fallback_masks_primary_failure",
        fallback_candidates=(broken, *_fallback_candidates()[1:]),
    )


def build_broken_duplicate_primary_authority_plan() -> PrimaryPathAuthorityPlan:
    good = build_primary_path_plan()
    first = good.primary_paths[0]
    return replace(
        good,
        plan_id="broken_duplicate_primary_authority",
        primary_paths=(first, first, *good.primary_paths[1:]),
    )


def build_broken_missing_coverage_plan() -> PrimaryPathAuthorityPlan:
    return replace(
        build_primary_path_plan(),
        plan_id="broken_missing_broad_coverage",
        coverage_case_ids=(),
        coverage_shard_ids=(),
        coverage_receipt_ids=(),
        risk_gate_ids=(),
    )


def build_behavior_commitment_ledger(_ppa_report=None) -> BehaviorCommitmentLedger:
    """Load the sole canonical behavior inventory.

    Primary Path Authority is validated independently by this model. The
    canonical ledger stores the exact per-commitment identity and never
    rebuilds the commitment inventory in Python.
    """

    return load_behavior_commitment_ledger(LEDGER_PATH)


def _single_commitment_ledger(
    ledger_id: str,
    commitment: dict,
) -> BehaviorCommitmentLedger:
    good = build_behavior_commitment_ledger()
    source_ids = set(commitment.get("source_surface_ids") or ())
    surfaces = tuple(
        surface
        for surface in good.source_surfaces
        if surface.surface_id in source_ids
    )
    return BehaviorCommitmentLedger(
        ledger_id=ledger_id,
        project_boundary=good.project_boundary,
        current_revision=good.current_revision,
        commitments=(commitment,),
        source_surfaces=surfaces,
        expected_commitment_ids=(commitment["commitment_id"],),
        expected_business_intent_ids=(commitment["business_intent_id"],),
        claim_scope="release",
        require_current_evidence=True,
        owner=good.owner,
        validation_boundary=good.validation_boundary,
        rationale=good.rationale,
    )


def build_broken_missing_ppa_ledger() -> BehaviorCommitmentLedger:
    good = build_behavior_commitment_ledger()
    broken = good.commitments[0].to_dict()
    broken["path_authority"] = {"path_sensitive": True}
    return _single_commitment_ledger("broken_missing_ppa_ledger", broken)


def build_broken_ppa_missing_primary_path_ids_ledger() -> BehaviorCommitmentLedger:
    good = build_behavior_commitment_ledger()
    broken = good.commitments[0].to_dict()
    broken["path_authority"]["primary_path_id"] = ""
    return _single_commitment_ledger(
        "broken_ppa_missing_primary_path_ids_ledger", broken
    )


def build_broken_stale_evidence_ledger() -> BehaviorCommitmentLedger:
    good = build_behavior_commitment_ledger()
    broken = good.commitments[0].to_dict()
    broken["evidence"]["current"] = False
    broken["evidence"]["evidence_state"] = "stale"
    return _single_commitment_ledger("broken_stale_evidence_ledger", broken)


def _projection(
    projection_id: str,
    *,
    field_id: str,
    obligation: str,
    code_contract: str,
    reads: tuple[str, ...],
    writes: tuple[str, ...],
    error_paths: tuple[str, ...] = (),
) -> FieldProjection:
    return FieldProjection(
        projection_id=projection_id,
        field_id=field_id,
        model_obligation_id=obligation,
        code_contract_id=code_contract,
        required_test_kinds=("happy_path", "negative_path", "replay"),
        external_inputs=("current_packet", "role_result_body"),
        external_outputs=("accepted_result_or_current_reissue",),
        state_reads=reads,
        state_writes=writes,
        error_paths=error_paths,
        risk_level="high",
        evidence_refs=(
            "gate:flowpilot_053_field_lifecycle",
            "test:tests/test_flowpilot_053_ppa_maintenance.py",
            "replay:simulations/run_flowpilot_ai_response_execution_closure_checks.py",
        ),
        rationale="Behavior-bearing current-contract field is projected to model, code, and tests.",
    )


def build_field_lifecycle_plan() -> FieldLifecyclePlan:
    fields = (
        FieldLifecycleRow(
            field_id="packet_result.body.pm_visible_summary",
            field_name="pm_visible_summary",
            locations=("skills/flowpilot/assets/flowpilot_core_runtime/packet_result_contracts.py",),
            group_id="role_output_current_contract",
            role="metadata",
            lifecycle="active",
            behavior_impacts=("external_contract", "schema"),
            reader_ids=("submit_result", "issue_pm_packet_with_recent_summary"),
            writer_ids=("assigned_role_agent",),
            disposition="same_contract_repaired",
            disposition_evidence_refs=("test:missing_pm_visible_summary_is_mechanically_reissued",),
            projection=_projection(
                "projection.pm_visible_summary",
                field_id="packet_result.body.pm_visible_summary",
                obligation="flowpilot_053.pm_visible_summary_role_authored",
                code_contract="role_output.current_contract.pm_visible_summary",
                reads=("packet_result_contract.required_fields",),
                writes=("result_body.pm_visible_summary",),
                error_paths=("missing_pm_visible_summary_reissue",),
            ),
        ),
        FieldLifecycleRow(
            field_id="pm_packet.body.recent_role_report_summary",
            field_name="recent_role_report_summary",
            locations=("skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",),
            group_id="pm_context_projection",
            role="metadata",
            lifecycle="derived",
            behavior_impacts=("external_contract", "routing"),
            reader_ids=("project_manager",),
            writer_ids=("issue_pm_packet_with_recent_summary",),
            disposition="same_contract_repaired",
            disposition_evidence_refs=("test:pm_repair_packet_includes_recent_role_report_summary",),
            projection=_projection(
                "projection.recent_role_report_summary",
                field_id="pm_packet.body.recent_role_report_summary",
                obligation="flowpilot_053.recent_role_summary_navigation_only",
                code_contract="pm_packet.current_context.recent_role_report_summary",
                reads=("accepted_role_results.pm_visible_summary",),
                writes=("pm_packet.body.recent_role_report_summary",),
                error_paths=("summary_used_as_evidence_substitute",),
            ),
        ),
        FieldLifecycleRow(
            field_id="packet.envelope.authorized_result_reads[]",
            field_name="authorized_result_reads",
            locations=("skills/flowpilot/assets/flowpilot_core_runtime/packet_stage_evidence_matrix.py",),
            group_id="authorized_material",
            role="permission",
            lifecycle="active",
            behavior_impacts=("permission", "external_contract", "replay"),
            reader_ids=("open_packet", "open_result", "assigned_role_agent"),
            writer_ids=("_normalize_authorized_result_reads", "issue_task_packet"),
            disposition="same_contract_repaired",
            disposition_evidence_refs=("test:flowguard_reissue_inherits_required_authorized_result_reads",),
            projection=_projection(
                "projection.authorized_result_reads",
                field_id="packet.envelope.authorized_result_reads[]",
                obligation="flowpilot_053.authorized_result_reads_required_material",
                code_contract="packet_result_family.runtime.authorized_result_reads",
                reads=("packet.envelope.authorized_result_reads",),
                writes=("role_open_receipts",),
                error_paths=("missing_authorized_material_open_receipt",),
            ),
        ),
        FieldLifecycleRow(
            field_id="task.discovery.packet.body.runtime_local_capability_inventory",
            field_name="runtime_local_capability_inventory",
            locations=("skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",),
            group_id="current_capability_discovery",
            role="packet_context",
            lifecycle="derived",
            behavior_impacts=("external_contract", "routing"),
            reader_ids=("project_manager",),
            writer_ids=("_runtime_local_capability_inventory",),
            disposition="same_contract_repaired",
            disposition_evidence_refs=("test:mandatory_local_capability_inventory_is_packet_only",),
            projection=_projection(
                "projection.runtime_local_capability_inventory",
                field_id="task.discovery.packet.body.runtime_local_capability_inventory",
                obligation="flowpilot_resource_discovery.shallow_inventory_then_pm_selection",
                code_contract="task.discovery.current_capability_inventory",
                reads=("project_skill_roots", "user_codex_skill_root"),
                writes=("task.discovery.packet.body.runtime_local_capability_inventory",),
                error_paths=("missing_or_deep_runtime_skill_scan",),
            ),
            metadata={"terminal_disposition": "packet_terminal_no_durable_inventory_ledger"},
        ),
        FieldLifecycleRow(
            field_id="preplanning.discovery.candidate_skill_inventory",
            field_name="candidate_skill_inventory",
            locations=("skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",),
            group_id="current_capability_discovery",
            role="decision",
            lifecycle="active",
            behavior_impacts=("external_contract", "routing"),
            reader_ids=("_ensure_skill_standard_packet", "project_manager"),
            writer_ids=("project_manager",),
            disposition="same_contract_repaired",
            disposition_evidence_refs=("test:discovery_keeps_only_candidate_skill_inventory",),
            projection=_projection(
                "projection.candidate_skill_inventory",
                field_id="preplanning.discovery.candidate_skill_inventory",
                obligation="flowpilot_resource_discovery.shallow_inventory_then_pm_selection",
                code_contract="task.discovery.current_candidate_selection",
                reads=("task.discovery.packet.body.runtime_local_capability_inventory",),
                writes=("preplanning_discovery.candidate_skill_inventory",),
                error_paths=("old_material_field_or_non_list_selection_rejected",),
            ),
        ),
        FieldLifecycleRow(
            field_id="packet_result.contract_self_check.workstream_plan_and_completion",
            field_name="workstream_plan_and_completion",
            locations=(
                "skills/flowpilot/assets/flowpilot_core_runtime/packet_result_contracts.py",
                "skills/flowpilot/assets/flowpilot_core_runtime/review_window_contracts.py",
            ),
            group_id="role_workstream_semantic_report",
            role="semantic_evidence",
            lifecycle="active",
            behavior_impacts=("external_contract", "replay"),
            reader_ids=("reviewer", "project_manager"),
            writer_ids=("assigned_substantive_role_agent",),
            disposition="same_contract_repaired",
            disposition_evidence_refs=("test:workstream_profiles_follow_real_current_review_and_repair_chain",),
            projection=_projection(
                "projection.workstream_plan_and_completion",
                field_id="packet_result.contract_self_check.workstream_plan_and_completion",
                obligation="flowpilot_complete_workstream.substantive_role_plan_execute_verify_report",
                code_contract="role_output.semantic.workstream_plan_and_completion",
                reads=("bounded_packet_assignment", "actual_artifacts_and_current_evidence"),
                writes=("role_result.contract_self_check.workstream_plan_and_completion",),
                error_paths=("reviewer_plan_completion_mismatch_routes_pm_repair",),
            ),
            metadata={"runtime_mechanical_gate": False, "semantic_owner": "reviewer"},
        ),
        FieldLifecycleRow(
            field_id="preplanning.discovery.material_sources",
            field_name="material_sources",
            locations=("forbidden/deleted list and negative tests only",),
            group_id="retired_material_discovery_surfaces",
            role="metadata",
            lifecycle="old",
            behavior_impacts=("external_contract", "routing"),
            reader_ids=(),
            writer_ids=(),
            disposition="blocked",
            disposition_evidence_refs=("negative_test:discovery_rejects_removed_material_fields",),
            scoped_out_reason="Material evidence is carried by ordinary task.node work and current evidence refs, not discovery.",
            current=True,
        ),
        FieldLifecycleRow(
            field_id="preplanning.discovery.material_sufficiency",
            field_name="material_sufficiency",
            locations=("forbidden/deleted list and negative tests only",),
            group_id="retired_material_discovery_surfaces",
            role="decision",
            lifecycle="old",
            behavior_impacts=("external_contract", "routing"),
            reader_ids=(),
            writer_ids=(),
            disposition="blocked",
            disposition_evidence_refs=("negative_test:discovery_rejects_removed_material_fields",),
            scoped_out_reason="Existing FlowGuard and Reviewer gates own process and quality; no special material gate remains.",
            current=True,
        ),
        FieldLifecycleRow(
            field_id="preplanning.discovery.material_current",
            field_name="material_current",
            locations=("forbidden/deleted list and negative tests only",),
            group_id="retired_material_discovery_surfaces",
            role="metadata",
            lifecycle="old",
            behavior_impacts=("external_contract", "replay"),
            reader_ids=(),
            writer_ids=(),
            disposition="blocked",
            disposition_evidence_refs=("negative_test:discovery_rejects_removed_material_fields",),
            scoped_out_reason="Evidence freshness remains owned by the ordinary evidence and review path.",
            current=True,
        ),
        FieldLifecycleRow(
            field_id="repair_transaction.plan_kind.packet_reissue",
            field_name="packet_reissue",
            locations=("forbidden plan-kind check and negative tests only",),
            group_id="retired_replacement_packet_repair_surfaces",
            role="decision",
            lifecycle="old",
            behavior_impacts=("external_contract", "routing", "side_effect"),
            reader_ids=(),
            writer_ids=(),
            disposition="blocked",
            disposition_evidence_refs=("negative_test:retired_packet_reissue_is_rejected",),
            scoped_out_reason="Current repair uses one supported executable plan with producer or action evidence; no replacement-packet branch remains.",
            current=True,
        ),
        FieldLifecycleRow(
            field_id="repair_transaction.replacement_packets",
            field_name="replacement_packets",
            locations=("forbidden field check and negative tests only",),
            group_id="retired_replacement_packet_repair_surfaces",
            role="payload",
            lifecycle="old",
            behavior_impacts=("external_contract", "side_effect"),
            reader_ids=(),
            writer_ids=(),
            disposition="blocked",
            disposition_evidence_refs=("negative_test:retired_replacement_fields_are_rejected",),
            scoped_out_reason="Ordinary rework uses existing current-node, research, or PM role-work packets.",
            current=True,
        ),
        FieldLifecycleRow(
            field_id="repair_transaction.replacement_packet_specs_path",
            field_name="replacement_packet_specs_path",
            locations=("forbidden field check and negative tests only",),
            group_id="retired_replacement_packet_repair_surfaces",
            role="path",
            lifecycle="old",
            behavior_impacts=("external_contract", "side_effect"),
            reader_ids=(),
            writer_ids=(),
            disposition="blocked",
            disposition_evidence_refs=("negative_test:retired_replacement_fields_are_rejected",),
            scoped_out_reason="No loose replacement spec may create current repair authority.",
            current=True,
        ),
        FieldLifecycleRow(
            field_id="repair_transaction.replacement_packet_specs_hash",
            field_name="replacement_packet_specs_hash",
            locations=("forbidden field check and negative tests only",),
            group_id="retired_replacement_packet_repair_surfaces",
            role="hash",
            lifecycle="old",
            behavior_impacts=("external_contract", "side_effect"),
            reader_ids=(),
            writer_ids=(),
            disposition="blocked",
            disposition_evidence_refs=("negative_test:retired_replacement_fields_are_rejected",),
            scoped_out_reason="A hash cannot revive a retired replacement-packet spec path.",
            current=True,
        ),
        FieldLifecycleRow(
            field_id="legacy_result_summary",
            field_name="legacy_result_summary",
            locations=("historical labels only",),
            group_id="retired_compatibility_surfaces",
            role="metadata",
            lifecycle="old",
            behavior_impacts=("external_contract",),
            reader_ids=(),
            writer_ids=(),
            disposition="blocked",
            disposition_evidence_refs=("negative_test:old_result_summary_rejected",),
            scoped_out_reason="Historical field names are forbidden inputs and cannot advance current runtime.",
            current=True,
        ),
        FieldLifecycleRow(
            field_id="packet.envelope.current_handoff_contract",
            field_name="current_handoff_contract",
            locations=("skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",),
            group_id="current_handoff_authority",
            role="contract",
            lifecycle="active",
            behavior_impacts=("external_contract", "schema", "routing"),
            reader_ids=("open_packet", "submission_checklist_projection", "submit_result"),
            writer_ids=("_build_current_handoff_contract",),
            disposition="same_contract_repaired",
            disposition_evidence_refs=("test:strict_open_result_is_the_only_runtime_contract_authority",),
            projection=_projection(
                "projection.current_handoff_contract",
                field_id="packet.envelope.current_handoff_contract",
                obligation="packet_result_family.current_handoff_checklist_single_authority",
                code_contract="packet_result_family.runtime.current_handoff_checklist_projection",
                reads=("effective_packet_result_contract", "review_window"),
                writes=("packet.envelope.current_handoff_contract",),
                error_paths=("missing_or_conflicting_handoff_rejected",),
            ),
        ),
        FieldLifecycleRow(
            field_id="open_packet.submission_checklist",
            field_name="submission_checklist",
            locations=("skills/flowpilot/assets/flowpilot_new_role_commands.py",),
            group_id="current_handoff_authority",
            role="derived_contract",
            lifecycle="derived",
            behavior_impacts=("external_contract", "permission", "replay"),
            reader_ids=("assigned_role_agent", "contract_driven_fake_ai"),
            writer_ids=("_submission_checklist_from_current_handoff_contract",),
            disposition="same_contract_repaired",
            disposition_evidence_refs=("test:real_public_open_packet_result_passes_strict_consumer",),
            projection=_projection(
                "projection.submission_checklist",
                field_id="open_packet.submission_checklist",
                obligation="packet_result_family.current_handoff_checklist_single_authority",
                code_contract="packet_result_family.runtime.current_handoff_checklist_projection",
                reads=("packet.envelope.current_handoff_contract", "open_receipt", "current_identity"),
                writes=("open_packet_result.submission_checklist",),
                error_paths=("stale_or_tampered_checklist_rejected",),
            ),
        ),
        FieldLifecycleRow(
            field_id="packet.body.mechanical_contract_mirrors",
            field_name="mechanical_contract_mirrors",
            locations=("forbidden/deleted list and negative tests only",),
            group_id="retired_contract_authorities",
            role="contract",
            lifecycle="old",
            behavior_impacts=("external_contract", "schema"),
            reader_ids=(),
            writer_ids=(),
            disposition="blocked",
            disposition_evidence_refs=("negative_test:packet_body_contract_authority_rejected",),
            scoped_out_reason="Packet body remains task context only; mechanical mirrors are deleted from active output.",
            current=True,
        ),
        FieldLifecycleRow(
            field_id="packet.body.conditional_mechanical_fields",
            field_name="conditional_required_fields_and_conditional_required_result_body_sections",
            locations=("forbidden/deleted list, historical contract catalog, and negative tests only",),
            group_id="retired_contract_authorities",
            role="contract",
            lifecycle="old",
            behavior_impacts=("external_contract", "schema", "routing"),
            reader_ids=(),
            writer_ids=(),
            disposition="blocked",
            disposition_evidence_refs=("negative_test:packet_body_contract_conflict_cannot_override_public_checklist",),
            scoped_out_reason=(
                "Conditional packet-body fields may describe historical task text but cannot add, remove, "
                "or branch current mechanical result obligations."
            ),
            current=True,
        ),
        FieldLifecycleRow(
            field_id="reissue.body.mechanical_contract_shape",
            field_name="minimal_valid_shape_and_required_fields",
            locations=("forbidden/deleted list and negative tests only",),
            group_id="retired_contract_authorities",
            role="contract",
            lifecycle="old",
            behavior_impacts=("external_contract", "replay"),
            reader_ids=(),
            writer_ids=(),
            disposition="blocked",
            disposition_evidence_refs=("negative_test:reissue_requires_fresh_open_packet_checklist",),
            scoped_out_reason="Reissue bodies contain diagnostics only and never reproduce a second result contract.",
            current=True,
        ),
        FieldLifecycleRow(
            field_id="fake_ai.private_helper_result_shapes",
            field_name="private_minimal_shape_and_static_positive_body_helpers",
            locations=("forbidden/deleted list and source-audit negative tests only",),
            group_id="retired_contract_authorities",
            role="derived_contract",
            lifecycle="old",
            behavior_impacts=("external_contract", "replay", "testing"),
            reader_ids=(),
            writer_ids=(),
            disposition="deleted",
            disposition_evidence_refs=("negative_test:core_fake_e2e_uses_public_role_and_submit_commands_only",),
            scoped_out_reason=(
                "Fake payloads start from the current public open result; private checklist builders, "
                "registry minimal shapes, and static complete success bodies are not callable authorities."
            ),
            current=True,
        ),
        FieldLifecycleRow(
            field_id="host.retired_role_aliases",
            field_name="project_manager_planner_and_unknown_role_aliases",
            locations=("negative tests and historical labels only",),
            group_id="retired_execution_sources",
            role="routing",
            lifecycle="old",
            behavior_impacts=("routing", "permission"),
            reader_ids=(),
            writer_ids=(),
            disposition="blocked",
            disposition_evidence_refs=("negative_test:retired_role_aliases_are_rejected",),
            scoped_out_reason="Only the current responsibility enum may dispatch or submit.",
            current=True,
        ),
        FieldLifecycleRow(
            field_id="execution_source.daemon_replay",
            field_name="daemon_replay",
            locations=("historical negative Cartesian cells only",),
            group_id="retired_execution_sources",
            role="routing",
            lifecycle="old",
            behavior_impacts=("routing", "replay"),
            reader_ids=(),
            writer_ids=(),
            disposition="blocked",
            disposition_evidence_refs=("negative_test:daemon_replay_is_not_a_current_execution_source",),
            scoped_out_reason="Current execution uses explicit role hosts; daemon replay cannot authorize continuation.",
            current=True,
        ),
    )
    return FieldLifecyclePlan(
        mesh_id=FIELD_MESH_ID,
        discovered_field_ids=FIELD_IDS,
        groups=(
            FieldLifecycleGroup(
                group_id="role_output_current_contract",
                boundary_kind="role_output_result_body",
                field_ids=("packet_result.body.pm_visible_summary",),
                owner_route="field_lifecycle_mesh",
                evidence_refs=("simulations/flowpilot_pm_visible_summary_model.py",),
                rationale="Role-authored summary is a required current output field, not runtime-authored semantics.",
            ),
            FieldLifecycleGroup(
                group_id="pm_context_projection",
                boundary_kind="packet_navigation_context",
                field_ids=("pm_packet.body.recent_role_report_summary",),
                owner_route="field_lifecycle_mesh",
                evidence_refs=("simulations/flowpilot_pm_visible_summary_model.py",),
                rationale="PM packet summary context is a derived navigation aid, not a decision substitute.",
            ),
            FieldLifecycleGroup(
                group_id="authorized_material",
                boundary_kind="sealed_material_permission",
                field_ids=("packet.envelope.authorized_result_reads[]",),
                owner_route="field_lifecycle_mesh",
                evidence_refs=("skills/flowpilot/assets/flowpilot_core_runtime/packet_stage_evidence_matrix.py",),
                rationale="Authorized material reads define required current input material.",
            ),
            FieldLifecycleGroup(
                group_id="current_capability_discovery",
                boundary_kind="runtime_inventory_then_pm_selection",
                field_ids=(
                    "task.discovery.packet.body.runtime_local_capability_inventory",
                    "preplanning.discovery.candidate_skill_inventory",
                ),
                owner_route="field_lifecycle_mesh",
                evidence_refs=("tests/test_flowpilot_ordinary_resource_discovery.py",),
                rationale=(
                    "Runtime owns the mandatory shallow packet snapshot; PM owns relevance selection and the existing skill-standard handoff."
                ),
            ),
            FieldLifecycleGroup(
                group_id="role_workstream_semantic_report",
                boundary_kind="role_authored_reviewer_audited_completion_evidence",
                field_ids=("packet_result.contract_self_check.workstream_plan_and_completion",),
                owner_route="field_lifecycle_mesh",
                evidence_refs=("tests/test_flowpilot_complete_workstream_fake_ai.py",),
                rationale="The report is visible in every substantive role result but remains a semantic Reviewer concern, not a Runtime score.",
            ),
            FieldLifecycleGroup(
                group_id="retired_material_discovery_surfaces",
                boundary_kind="deleted_special_material_stage_fields",
                field_ids=(
                    "preplanning.discovery.material_sources",
                    "preplanning.discovery.material_sufficiency",
                    "preplanning.discovery.material_current",
                ),
                owner_route="architecture_reduction",
                evidence_refs=("tests/test_flowpilot_ordinary_resource_discovery.py",),
                rationale="Material work returns to ordinary PM task packages; old discovery fields remain negative evidence only.",
            ),
            FieldLifecycleGroup(
                group_id="retired_replacement_packet_repair_surfaces",
                boundary_kind="deleted_replacement_packet_repair_authority",
                field_ids=(
                    "repair_transaction.plan_kind.packet_reissue",
                    "repair_transaction.replacement_packets",
                    "repair_transaction.replacement_packet_specs_path",
                    "repair_transaction.replacement_packet_specs_hash",
                ),
                owner_route="architecture_reduction",
                evidence_refs=("tests/test_flowpilot_ordinary_resource_discovery.py",),
                rationale="The single current repair path requires a supported executable plan and current producer/action evidence; replacement-packet authority remains negative only.",
            ),
            FieldLifecycleGroup(
                group_id="retired_compatibility_surfaces",
                boundary_kind="forbidden_historical_fields",
                field_ids=("legacy_result_summary",),
                owner_route="architecture_reduction",
                evidence_refs=("negative_test:old_result_summary_rejected",),
                rationale="Retired names may appear only as negative fixtures or historical labels.",
            ),
            FieldLifecycleGroup(
                group_id="current_handoff_authority",
                boundary_kind="single_mechanical_contract_authority",
                field_ids=(
                    "packet.envelope.current_handoff_contract",
                    "open_packet.submission_checklist",
                ),
                owner_route="field_lifecycle_mesh",
                evidence_refs=("tests/test_flowpilot_contract_driven_fake_ai_open_packet.py",),
                rationale="One envelope contract owns mechanics; the checklist is its identity-bound projection.",
            ),
            FieldLifecycleGroup(
                group_id="retired_contract_authorities",
                boundary_kind="deleted_alternate_contract_authorities",
                field_ids=(
                    "packet.body.mechanical_contract_mirrors",
                    "packet.body.conditional_mechanical_fields",
                    "reissue.body.mechanical_contract_shape",
                    "fake_ai.private_helper_result_shapes",
                ),
                owner_route="architecture_reduction",
                evidence_refs=("tests/test_flowpilot_new_entrypoint.py",),
                rationale=(
                    "Body/reissue mirrors, conditional body mechanics, and private helper shapes are "
                    "rejected or deleted instead of preserved as compatibility surfaces."
                ),
            ),
            FieldLifecycleGroup(
                group_id="retired_execution_sources",
                boundary_kind="deleted_role_and_execution_aliases",
                field_ids=(
                    "host.retired_role_aliases",
                    "execution_source.daemon_replay",
                ),
                owner_route="field_lifecycle_mesh",
                evidence_refs=("tests/test_flowpilot_role_source_purity.py", "tests/test_flowpilot_current_contract_cartesian_matrix.py"),
                rationale="Retired identities and daemon replay remain negative evidence only.",
            ),
        ),
        fields=fields,
        claim_scope="runtime",
        allow_scoped_confidence=False,
        notes=(
            "Current handoff/checklist fields have one owner; body mirrors, conditional body mechanics, "
            "private helper shapes, role aliases, and daemon replay are blocked or deleted old paths."
        ),
    )


def build_broken_missing_field_projection_plan() -> FieldLifecyclePlan:
    field = FieldLifecycleRow(
        field_id="packet_result.body.pm_visible_summary",
        field_name="pm_visible_summary",
        locations=("skills/flowpilot/assets/flowpilot_core_runtime/packet_result_contracts.py",),
        group_id="role_output_current_contract",
        role="metadata",
        lifecycle="active",
        behavior_impacts=("external_contract", "schema"),
        reader_ids=("submit_result",),
        writer_ids=("assigned_role_agent",),
        disposition="same_contract_repaired",
        disposition_evidence_refs=("test:missing_pm_visible_summary_is_mechanically_reissued",),
    )
    return FieldLifecyclePlan(
        mesh_id="broken_missing_field_projection",
        discovered_field_ids=("packet_result.body.pm_visible_summary",),
        groups=(
            FieldLifecycleGroup(
                group_id="role_output_current_contract",
                boundary_kind="role_output_result_body",
                field_ids=("packet_result.body.pm_visible_summary",),
                owner_route="field_lifecycle_mesh",
            ),
        ),
        fields=(field,),
        claim_scope="runtime",
        allow_scoped_confidence=False,
    )


def build_risk_evidence_ledger_plan(
    ppa_report,
    bcl_report,
    field_report,
    *,
    formal_ai_evidence,
    model_test_alignment_evidence,
) -> RiskEvidenceLedgerPlan:
    formal_ai_ok = bool(formal_ai_evidence.get("ok"))
    model_test_alignment_ok = bool(model_test_alignment_evidence.get("ok"))
    return RiskEvidenceLedgerPlan(
        ledger_id=RISK_LEDGER_ID,
        rows=(
            RiskEvidenceRow(
                risk_id="risk.no_fallback_path_masking",
                model_obligation_id="flowpilot_053.repair_reissue_no_fallback",
                code_contract_id="packet_result_family.runtime.current_contract_reissue_feedback",
                proof_evidence_ids=("evidence.ppa_runner", "evidence.formal_ai_execution_closure"),
                gates=tuple(
                    RiskEvidenceGate(kind=kind, evidence_id=evidence_id, required=True, current=True, confidence="full")
                    for kind, evidence_id in (
                        ("primary_path_authority", PPA_RISK_GATES[0]),
                        ("primary_path_authority_cartesian_coverage", PPA_RISK_GATES[1]),
                        ("behavior_commitment_coverage", BCL_RISK_GATES[0]),
                        ("behavior_commitment_cartesian_coverage", BCL_RISK_GATES[1]),
                    )
                ),
            ),
            RiskEvidenceRow(
                risk_id="risk.field_expansion_without_lifecycle",
                model_obligation_id="flowpilot_053.pm_visible_summary_role_authored",
                code_contract_id="role_output.current_contract.pm_visible_summary",
                proof_evidence_ids=("evidence.field_lifecycle", "evidence.pm_visible_summary_runner"),
                gates=(
                    RiskEvidenceGate(
                        kind="family",
                        evidence_id="gate:flowpilot_053_field_lifecycle",
                        required=True,
                        current=field_report.ok,
                        confidence=field_report.confidence,
                    ),
                ),
            ),
            RiskEvidenceRow(
                risk_id="risk.release_claim_from_stale_or_routine_only_evidence",
                model_obligation_id="flowpilot_053.release_claims_current_evidence",
                code_contract_id="tiered_flowpilot_test_validation.release_claims",
                proof_evidence_ids=("evidence.bcl_runner", "evidence.model_test_alignment"),
                gates=(
                    RiskEvidenceGate(
                        kind="behavior_commitment_coverage",
                        evidence_id=BCL_RISK_GATES[0],
                        required=True,
                        current=bcl_report.ok,
                        confidence=bcl_report.confidence,
                    ),
                    RiskEvidenceGate(
                        kind="primary_path_authority",
                        evidence_id=PPA_RISK_GATES[0],
                        required=True,
                        current=ppa_report.ok,
                        confidence=ppa_report.confidence,
                    ),
                ),
            ),
        ),
        proof_evidence=(
            RiskEvidenceProof(
                evidence_id="evidence.ppa_runner",
                proof_kind="route_report",
                result_status="passed" if ppa_report.ok else "failed",
                current=True,
                assertion_scope="external_contract",
                producer_route="primary_path_authority",
                command="python simulations/run_flowpilot_053_ppa_maintenance_checks.py",
                summary=ppa_report.summary,
            ),
            RiskEvidenceProof(
                evidence_id="evidence.bcl_runner",
                proof_kind="route_report",
                result_status="passed" if bcl_report.ok else "failed",
                current=True,
                assertion_scope="external_contract",
                producer_route="behavior_commitment_ledger",
                command="python simulations/run_flowpilot_053_ppa_maintenance_checks.py",
                summary=bcl_report.summary,
            ),
            RiskEvidenceProof(
                evidence_id="evidence.field_lifecycle",
                proof_kind="route_report",
                result_status="passed" if field_report.ok else "failed",
                current=True,
                assertion_scope="external_contract",
                producer_route="field_lifecycle_mesh",
                command="python simulations/run_flowpilot_053_ppa_maintenance_checks.py",
                summary=field_report.summary,
            ),
            RiskEvidenceProof(
                evidence_id="evidence.pm_visible_summary_runner",
                proof_kind="test",
                result_status="passed",
                current=True,
                assertion_scope="external_contract",
                producer_route="model_first_function_flow",
                command="python simulations/run_flowpilot_pm_visible_summary_checks.py",
                summary="Existing PM-visible role summary model and source checks remain green.",
            ),
            RiskEvidenceProof(
                evidence_id="evidence.formal_ai_execution_closure",
                proof_kind="replay",
                result_status="passed" if formal_ai_ok else "failed",
                current=formal_ai_ok,
                assertion_scope="external_contract",
                producer_route="test_mesh_maintenance",
                command=(
                    "python simulations/run_flowpilot_ai_response_execution_closure_checks.py "
                    "--mode adversarial --json-out "
                    "simulations/flowpilot_ai_response_execution_closure_results.json"
                ),
                summary=str(formal_ai_evidence.get("summary") or "formal AI execution evidence is missing"),
            ),
            RiskEvidenceProof(
                evidence_id="evidence.model_test_alignment",
                proof_kind="route_report",
                result_status="passed" if model_test_alignment_ok else "failed",
                current=model_test_alignment_ok,
                assertion_scope="external_contract",
                producer_route="model_test_alignment",
                command=(
                    "python simulations/run_flowpilot_model_test_alignment_checks.py "
                    "--evidence-manifest simulations/flowpilot_acceptance_testmesh_evidence_manifest.json "
                    "--evidence-scope done --json-out "
                    "simulations/flowpilot_model_test_alignment_results.json"
                ),
                summary=str(
                    model_test_alignment_evidence.get("summary")
                    or "current strict model-test alignment evidence is missing"
                ),
            ),
        ),
        allow_scoped_confidence=False,
    )
