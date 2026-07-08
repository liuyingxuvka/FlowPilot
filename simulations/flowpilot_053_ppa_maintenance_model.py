"""FlowGuard 0.53 maintenance model for FlowPilot primary-path authority.

This model is intentionally evidence-only. It does not add FlowPilot runtime
fields or compatibility behavior. It registers the current no-fallback
commitments through FlowGuard 0.53 Primary Path Authority, Behavior Commitment
Ledger, FieldLifecycleMesh, and Risk Evidence Ledger APIs.
"""

from __future__ import annotations

from flowguard import (
    BehaviorCommitment,
    BehaviorCommitmentLedger,
    BehaviorEvidenceBinding,
    BehaviorSourceSurface,
    FallbackPathCandidate,
    FieldLifecycleGroup,
    FieldLifecyclePlan,
    FieldLifecycleRow,
    FieldProjection,
    PrimaryPathAuthorityPlan,
    PrimaryPathContract,
    RiskEvidenceGate,
    RiskEvidenceLedgerPlan,
    RiskEvidenceProof,
    RiskEvidenceRow,
    behavior_path_binding_from_primary_path_report,
)


MODEL_ID = "flowpilot_053_ppa_maintenance"
PPA_PLAN_ID = "flowpilot_053_primary_path_authority"
BCL_LEDGER_ID = "flowpilot_053_behavior_commitments"
FIELD_MESH_ID = "flowpilot_053_field_lifecycle"
RISK_LEDGER_ID = "flowpilot_053_risk_evidence"

PPA_RISK_GATES = (
    f"risk_gate:primary_path_authority:{MODEL_ID}",
    f"risk_gate:primary_path_authority_cartesian_coverage:{MODEL_ID}",
)
BCL_RISK_GATES = (
    f"risk_gate:behavior_commitment_coverage:{BCL_LEDGER_ID}",
    f"risk_gate:behavior_commitment_cartesian_coverage:{BCL_LEDGER_ID}",
)
COVERAGE_CASE_IDS = (
    "case:flowpilot.synthetic_agent_global_d_card_matrix",
    "case:flowpilot.current_contract_cartesian_matrix",
    "case:flowpilot.contract_exhaustion_mesh",
)
COVERAGE_SHARD_IDS = (
    "contract_shard:flowpilot_053_ppa_maintenance:no_fallback_cartesian",
    "contract_shard:flowpilot_053_bcl_maintenance:behavior_commitment_cartesian",
)
COVERAGE_RECEIPT_IDS = (
    "contract_coverage:flowpilot_053_ppa_maintenance",
    "contract_coverage:flowpilot_053_bcl_maintenance",
)

PRIMARY_PATH_INTENTS = (
    "accept_current_packet_result",
    "reject_or_reissue_current_packet_result",
    "open_authorized_result_material",
)

COMMITMENT_IDS = (
    "commit.result_submission_current_contract_only",
    "commit.repair_reissue_no_fallback",
    "commit.pm_visible_summary_is_role_authored",
    "commit.authorized_result_reads_are_required_material",
    "commit.release_claims_require_current_evidence",
)

FIELD_IDS = (
    "packet_result.body.pm_visible_summary",
    "pm_packet.body.recent_role_report_summary",
    "packet.envelope.authorized_result_reads[]",
    "legacy_result_summary",
)

TEST_RECEIPTS = (
    "test:tests/test_flowpilot_053_ppa_maintenance.py",
    "test:tests/test_flowpilot_core_runtime.py::test_missing_pm_visible_summary_is_mechanically_reissued",
    "test:tests/test_flowpilot_core_runtime.py::test_pm_repair_packet_includes_recent_role_report_summary",
    "test:tests/test_flowpilot_new_entrypoint.py::authorized_result_reads",
    "test:tests/test_flowpilot_synthetic_agent_coverage_matrix.py",
)


def _primary_path(
    business_path_id: str,
    *,
    business_intent: str,
    entrypoint: str,
    code_contract: str,
    expected_terminal: str,
) -> PrimaryPathContract:
    return PrimaryPathContract(
        business_path_id=business_path_id,
        business_intent=business_intent,
        primary_entrypoint_id=entrypoint,
        owner_model_id=MODEL_ID,
        owner_code_contract_id=code_contract,
        expected_terminal=expected_terminal,
        failure_policy="fail_closed",
        allowed_error_state_ids=(
            "current_contract_reissue",
            "current_packet_rejected",
            "missing_required_material_blocker",
        ),
        evidence_ids=TEST_RECEIPTS,
        authority_role="primary",
        metadata={"runtime_owner": "FlowPilot runtime/router"},
    )


def build_primary_path_plan() -> PrimaryPathAuthorityPlan:
    return PrimaryPathAuthorityPlan(
        plan_id=PPA_PLAN_ID,
        primary_paths=(
            _primary_path(
                "path.runtime.submit_current_result",
                business_intent="accept_current_packet_result",
                entrypoint="flowpilot_core_runtime.runtime.submit_result",
                code_contract="packet_result_family.runtime.submit_result_body_entry",
                expected_terminal="accepted_current_result_or_current_contract_reissue",
            ),
            _primary_path(
                "path.runtime.reissue_or_reject_current_result",
                business_intent="reject_or_reissue_current_packet_result",
                entrypoint="flowpilot_core_runtime.runtime._accept_packet_result",
                code_contract="packet_result_family.runtime.current_contract_reissue_feedback",
                expected_terminal="old_duplicate_or_malformed_result_rejected",
            ),
            _primary_path(
                "path.runtime.open_authorized_result_material",
                business_intent="open_authorized_result_material",
                entrypoint="flowpilot_new_role_commands.open_result",
                code_contract="packet_result_family.runtime.authorized_result_reads",
                expected_terminal="only_current_authorized_material_opened",
            ),
        ),
        fallback_candidates=(
            FallbackPathCandidate(
                candidate_path_id="fallback.old_result_summary_field",
                fallback_for_path_id="path.runtime.submit_current_result",
                business_intent="accept_current_packet_result",
                candidate_surface="old_field",
                candidate_trigger="missing_field",
                candidate_behavior="no_op",
                invokes_on_primary_failure=False,
                returns_success_after_primary_failure=False,
                disposition="block",
                evidence_refs=("test:missing_pm_visible_summary_is_mechanically_reissued",),
            ),
            FallbackPathCandidate(
                candidate_path_id="fallback.alias_submit_result_body",
                fallback_for_path_id="path.runtime.submit_current_result",
                business_intent="accept_current_packet_result",
                candidate_surface="alias",
                candidate_trigger="parse_error",
                candidate_behavior="no_op",
                returns_success_after_primary_failure=False,
                disposition="block",
                evidence_refs=("test:submit_result_rejects_pseudo_json_before_loading_current_run",),
            ),
            FallbackPathCandidate(
                candidate_path_id="fallback.prose_reviewer_pass",
                fallback_for_path_id="path.runtime.reissue_or_reject_current_result",
                business_intent="reject_or_reissue_current_packet_result",
                candidate_surface="helper_route",
                candidate_trigger="primary_failure",
                candidate_behavior="no_op",
                returns_success_after_primary_failure=False,
                disposition="block",
                evidence_refs=("test:shallow_flowguard_reviewer_block",),
            ),
        ),
        claim_scope="release",
        require_cartesian_coverage=True,
        coverage_case_ids=COVERAGE_CASE_IDS,
        coverage_shard_ids=COVERAGE_SHARD_IDS,
        coverage_receipt_ids=COVERAGE_RECEIPT_IDS,
        risk_gate_ids=PPA_RISK_GATES,
        expected_business_intents=PRIMARY_PATH_INTENTS,
        metadata={"no_fallback_policy": "current runtime blocks unsupported alternates"},
    )


def build_broken_old_field_fallback_plan() -> PrimaryPathAuthorityPlan:
    good = build_primary_path_plan()
    return PrimaryPathAuthorityPlan(
        plan_id="broken_old_field_fallback_masks_primary_failure",
        primary_paths=good.primary_paths,
        fallback_candidates=(
            FallbackPathCandidate(
                candidate_path_id="fallback.old_result_summary_field",
                fallback_for_path_id="path.runtime.submit_current_result",
                business_intent="accept_current_packet_result",
                candidate_surface="old_field",
                candidate_trigger="missing_field",
                candidate_behavior="return_success",
                invokes_on_primary_failure=True,
                returns_success_after_primary_failure=True,
                disposition="block",
                evidence_refs=("negative_test:old_field_must_not_mask_missing_pm_visible_summary",),
            ),
        ),
        claim_scope="release",
        require_cartesian_coverage=True,
        coverage_case_ids=COVERAGE_CASE_IDS,
        coverage_shard_ids=COVERAGE_SHARD_IDS,
        coverage_receipt_ids=COVERAGE_RECEIPT_IDS,
        risk_gate_ids=PPA_RISK_GATES,
        expected_business_intents=PRIMARY_PATH_INTENTS,
    )


def build_broken_duplicate_primary_authority_plan() -> PrimaryPathAuthorityPlan:
    first = build_primary_path_plan().primary_paths[0]
    return PrimaryPathAuthorityPlan(
        plan_id="broken_duplicate_primary_authority",
        primary_paths=(first, first),
        claim_scope="routine",
        expected_business_intents=("accept_current_packet_result",),
    )


def build_broken_missing_coverage_plan() -> PrimaryPathAuthorityPlan:
    return PrimaryPathAuthorityPlan(
        plan_id="broken_missing_broad_coverage",
        primary_paths=build_primary_path_plan().primary_paths,
        claim_scope="release",
        require_cartesian_coverage=True,
        expected_business_intents=PRIMARY_PATH_INTENTS,
    )


def _evidence_binding(*, obligation: str, contract: str, test_id: str) -> BehaviorEvidenceBinding:
    return BehaviorEvidenceBinding(
        model_obligation_ids=(obligation,),
        code_contract_ids=(contract,),
        test_evidence_ids=(test_id,),
        proof_artifact_ids=("simulations/flowpilot_053_ppa_maintenance_results.json",),
        risk_gate_ids=BCL_RISK_GATES,
        coverage_case_ids=COVERAGE_CASE_IDS,
        coverage_shard_ids=COVERAGE_SHARD_IDS,
        coverage_receipt_ids=COVERAGE_RECEIPT_IDS,
        evidence_state="current_pass",
        current=True,
    )


def _source_surface(surface_id: str, *, kind: str, source_ref: str, commitment_id: str) -> BehaviorSourceSurface:
    return BehaviorSourceSurface(
        surface_id=surface_id,
        surface_kind=kind,
        label=surface_id,
        source_ref=source_ref,
        commitment_ids=(commitment_id,),
        owner="FlowPilot maintenance model",
        validation_boundary="current FlowPilot runtime contract",
        rationale="Maps a current behavior surface to one behavior commitment.",
    )


def build_behavior_commitment_ledger(ppa_report) -> BehaviorCommitmentLedger:
    path_binding = behavior_path_binding_from_primary_path_report(
        ppa_report,
        business_intent="FlowPilot current-contract no-fallback behavior",
        ppa_report_id=PPA_PLAN_ID,
        evidence_refs=("simulations/flowpilot_053_ppa_maintenance_results.json",),
    )
    commitments = (
        BehaviorCommitment(
            commitment_id="commit.result_submission_current_contract_only",
            label="Current packet results use only current result contracts.",
            commitment_kind="workflow",
            actor="assigned role agent",
            trigger="submit-result for a current packet",
            expected_result="runtime accepts only current structured result bodies or reissues the current packet",
            failure_boundary="unsupported fields, prose, stale packets, and aliases are rejected",
            source_surface_ids=("surface.runtime.submit_result",),
            source_refs=("skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",),
            primary_owner_model_id=MODEL_ID,
            supporting_model_ids=("flowpilot_field_contracts", "flowpilot_pm_visible_summary"),
            path_authority=path_binding,
            evidence=_evidence_binding(
                obligation="flowpilot_053.result_submission_current_contract_only",
                contract="packet_result_family.runtime.submit_result_body_entry",
                test_id="test:tests/test_flowpilot_core_runtime.py",
            ),
            owner="FlowPilot runtime/router",
            validation_boundary="mechanical result contract validation",
            rationale="Runtime must fail closed on unsupported result shapes.",
        ),
        BehaviorCommitment(
            commitment_id="commit.repair_reissue_no_fallback",
            label="Repair and reissue stay on the current package/result/blocker path.",
            commitment_kind="workflow",
            actor="FlowPilot runtime/router",
            trigger="current packet result is missing required data or repeats an old accepted package",
            expected_result="runtime rejects the old package and names the current repair or reissue path",
            failure_boundary="no old package, fallback cache, alias, or prose result may become success",
            source_surface_ids=("surface.runtime.repair_reissue",),
            source_refs=("skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",),
            primary_owner_model_id=MODEL_ID,
            supporting_model_ids=("flowpilot_route_authority_singularity",),
            path_authority=path_binding,
            evidence=_evidence_binding(
                obligation="flowpilot_053.repair_reissue_no_fallback",
                contract="packet_result_family.runtime.current_contract_reissue_feedback",
                test_id="test:tests/test_flowpilot_synthetic_agent_coverage_matrix.py",
            ),
            owner="FlowPilot runtime/router",
            validation_boundary="current packet/result/blocker repair state",
            rationale="Repeated and stale submissions are audit records, not alternate success paths.",
        ),
        BehaviorCommitment(
            commitment_id="commit.pm_visible_summary_is_role_authored",
            label="PM-visible summaries are role-authored current fields.",
            commitment_kind="workflow",
            actor="worker, FlowGuard operator, or reviewer role",
            trigger="formal non-PM role result body is submitted",
            expected_result="runtime requires and relays pm_visible_summary but never synthesizes semantic content",
            failure_boundary="missing summary blocks mechanically; summary text never substitutes for sealed body review",
            source_surface_ids=("surface.pm_visible_summary",),
            source_refs=("simulations/flowpilot_pm_visible_summary_model.py",),
            primary_owner_model_id=MODEL_ID,
            supporting_model_ids=("flowpilot_pm_visible_summary",),
            path_authority=path_binding,
            evidence=_evidence_binding(
                obligation="flowpilot_053.pm_visible_summary_role_authored",
                contract="role_output.current_contract.pm_visible_summary",
                test_id="test:tests/test_flowpilot_core_runtime.py::test_missing_pm_visible_summary_is_mechanically_reissued",
            ),
            owner="Role output runtime",
            validation_boundary="mechanical required field validation only",
            rationale="Runtime can require the field but cannot perform semantic reviewer quality checks.",
        ),
        BehaviorCommitment(
            commitment_id="commit.authorized_result_reads_are_required_material",
            label="Authorized result reads are required material, not optional summaries.",
            commitment_kind="workflow",
            actor="assigned role agent",
            trigger="packet envelope includes authorized_result_reads",
            expected_result="assigned role receives and uses the authorized current material before submit-result",
            failure_boundary="recent summaries and ordinary file access do not satisfy required sealed-body reads",
            source_surface_ids=("surface.authorized_result_reads",),
            source_refs=("skills/flowpilot/assets/flowpilot_core_runtime/packet_stage_evidence_matrix.py",),
            primary_owner_model_id=MODEL_ID,
            supporting_model_ids=("flowpilot_field_contracts",),
            path_authority=path_binding,
            evidence=_evidence_binding(
                obligation="flowpilot_053.authorized_result_reads_required_material",
                contract="packet_result_family.runtime.authorized_result_reads",
                test_id="test:tests/test_flowpilot_new_entrypoint.py",
            ),
            owner="FlowPilot runtime/router",
            validation_boundary="authorized material opening and receipt validation",
            rationale="This keeps summary navigation separate from formal evidence consumption.",
        ),
        BehaviorCommitment(
            commitment_id="commit.release_claims_require_current_evidence",
            label="Release and done claims require current model/test/install evidence.",
            commitment_kind="process",
            actor="maintaining agent",
            trigger="maintenance, done, release, or publish confidence is claimed",
            expected_result="routine-green evidence is separated from current release-suite evidence",
            failure_boundary="stale full proofs and deferred release suites block broad claims",
            source_surface_ids=("surface.release_evidence",),
            source_refs=("simulations/run_meta_checks.py", "simulations/run_capability_checks.py"),
            primary_owner_model_id=MODEL_ID,
            supporting_model_ids=("flowpilot_complete_system_testmesh", "flowpilot_model_test_alignment"),
            path_authority=path_binding,
            evidence=_evidence_binding(
                obligation="flowpilot_053.release_claims_current_evidence",
                contract="tiered_flowpilot_test_validation.release_claims",
                test_id="test:simulations/run_meta_checks.py",
            ),
            owner="DevelopmentProcessFlow",
            validation_boundary="current release evidence gate",
            rationale="A project upgrade record is not itself validation proof.",
        ),
    )
    return BehaviorCommitmentLedger(
        ledger_id=BCL_LEDGER_ID,
        project_boundary="FlowPilot current-contract runtime, prompts, models, tests, and install sync",
        current_revision="flowguard-0.53-maintenance",
        commitments=commitments,
        source_surfaces=(
            _source_surface(
                "surface.runtime.submit_result",
                kind="code",
                source_ref="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                commitment_id="commit.result_submission_current_contract_only",
            ),
            _source_surface(
                "surface.runtime.repair_reissue",
                kind="code",
                source_ref="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                commitment_id="commit.repair_reissue_no_fallback",
            ),
            _source_surface(
                "surface.pm_visible_summary",
                kind="code",
                source_ref="simulations/flowpilot_pm_visible_summary_model.py",
                commitment_id="commit.pm_visible_summary_is_role_authored",
            ),
            _source_surface(
                "surface.authorized_result_reads",
                kind="code",
                source_ref="skills/flowpilot/assets/flowpilot_core_runtime/packet_stage_evidence_matrix.py",
                commitment_id="commit.authorized_result_reads_are_required_material",
            ),
            _source_surface(
                "surface.release_evidence",
                kind="process",
                source_ref="simulations/run_meta_checks.py",
                commitment_id="commit.release_claims_require_current_evidence",
            ),
        ),
        expected_commitment_ids=COMMITMENT_IDS,
        claim_scope="release",
        require_current_evidence=True,
        owner="FlowPilot maintenance",
        validation_boundary="FlowGuard 0.53 PPA/BCL maintenance pass",
        rationale="Registers the user-visible no-fallback and evidence freshness promises before broad confidence claims.",
    )


def build_broken_missing_ppa_ledger() -> BehaviorCommitmentLedger:
    good_ppa = __import__("flowguard").review_primary_path_authority(build_primary_path_plan())
    good = build_behavior_commitment_ledger(good_ppa)
    broken = good.commitments[0].to_dict()
    broken["path_authority"] = {"path_sensitive": True}
    return BehaviorCommitmentLedger(
        ledger_id="broken_missing_ppa_ledger",
        project_boundary=good.project_boundary,
        current_revision=good.current_revision,
        commitments=(broken,),
        source_surfaces=(
            BehaviorSourceSurface(
                surface_id="surface.runtime.submit_result",
                surface_kind="code",
                source_ref="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                commitment_ids=("commit.result_submission_current_contract_only",),
            ),
        ),
        expected_commitment_ids=("commit.result_submission_current_contract_only",),
        claim_scope="release",
        require_current_evidence=True,
        owner=good.owner,
        validation_boundary=good.validation_boundary,
        rationale=good.rationale,
    )


def build_broken_ppa_missing_primary_path_ids_ledger() -> BehaviorCommitmentLedger:
    good_ppa = __import__("flowguard").review_primary_path_authority(build_primary_path_plan())
    good = build_behavior_commitment_ledger(good_ppa)
    broken = good.commitments[0].to_dict()
    broken["path_authority"]["primary_path_ids"] = []
    return BehaviorCommitmentLedger(
        ledger_id="broken_ppa_missing_primary_path_ids_ledger",
        project_boundary=good.project_boundary,
        current_revision=good.current_revision,
        commitments=(broken,),
        source_surfaces=(
            BehaviorSourceSurface(
                surface_id="surface.runtime.submit_result",
                surface_kind="code",
                source_ref="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                commitment_ids=("commit.result_submission_current_contract_only",),
            ),
        ),
        expected_commitment_ids=("commit.result_submission_current_contract_only",),
        claim_scope="release",
        require_current_evidence=True,
        owner=good.owner,
        validation_boundary=good.validation_boundary,
        rationale=good.rationale,
    )


def build_broken_stale_evidence_ledger() -> BehaviorCommitmentLedger:
    good_ppa = __import__("flowguard").review_primary_path_authority(build_primary_path_plan())
    good = build_behavior_commitment_ledger(good_ppa)
    broken = good.commitments[0].to_dict()
    broken["evidence"]["current"] = False
    broken["evidence"]["evidence_state"] = "stale"
    return BehaviorCommitmentLedger(
        ledger_id="broken_stale_evidence_ledger",
        project_boundary=good.project_boundary,
        current_revision=good.current_revision,
        commitments=(broken,),
        source_surfaces=(
            BehaviorSourceSurface(
                surface_id="surface.runtime.submit_result",
                surface_kind="code",
                source_ref="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                commitment_ids=("commit.result_submission_current_contract_only",),
            ),
        ),
        expected_commitment_ids=("commit.result_submission_current_contract_only",),
        claim_scope="release",
        require_current_evidence=True,
        owner=good.owner,
        validation_boundary=good.validation_boundary,
        rationale=good.rationale,
    )


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
            "replay:simulations/flowpilot_synthetic_agent_coverage_matrix.py",
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
                group_id="retired_compatibility_surfaces",
                boundary_kind="forbidden_historical_fields",
                field_ids=("legacy_result_summary",),
                owner_route="architecture_reduction",
                evidence_refs=("negative_test:old_result_summary_rejected",),
                rationale="Retired names may appear only as negative fixtures or historical labels.",
            ),
        ),
        fields=fields,
        claim_scope="runtime",
        allow_scoped_confidence=False,
        notes="No new fields are introduced; existing current fields are assigned lifecycle and evidence boundaries.",
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


def build_risk_evidence_ledger_plan(ppa_report, bcl_report, field_report) -> RiskEvidenceLedgerPlan:
    return RiskEvidenceLedgerPlan(
        ledger_id=RISK_LEDGER_ID,
        rows=(
            RiskEvidenceRow(
                risk_id="risk.no_fallback_path_masking",
                model_obligation_id="flowpilot_053.repair_reissue_no_fallback",
                code_contract_id="packet_result_family.runtime.current_contract_reissue_feedback",
                proof_evidence_ids=("evidence.ppa_runner", "evidence.synthetic_agent_matrix"),
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
                evidence_id="evidence.synthetic_agent_matrix",
                proof_kind="replay",
                result_status="passed",
                current=True,
                assertion_scope="external_contract",
                producer_route="test_mesh_maintenance",
                command="python simulations/flowpilot_synthetic_agent_coverage_matrix.py",
                summary="Global synthetic fake-agent D-card matrix covers no-fallback families.",
            ),
            RiskEvidenceProof(
                evidence_id="evidence.model_test_alignment",
                proof_kind="route_report",
                result_status="passed",
                current=True,
                assertion_scope="external_contract",
                producer_route="model_test_alignment",
                command="python simulations/run_flowpilot_model_test_alignment_checks.py",
                summary="Model-test alignment consumes the FlowGuard 0.53 maintenance family.",
            ),
        ),
        allow_scoped_confidence=False,
    )
