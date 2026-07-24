from __future__ import annotations

import ast
import contextlib
from dataclasses import replace
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from flowguard import (
    ModelObligation,
    ModelTestAlignmentPlan,
    TestEvidence,
    review_model_test_alignment,
)
from scripts.test_tier.definitions import commands_for_tier
from scripts.test_tier import impact_resolution
import scripts.run_test_tier as test_tier_runner
from tests.v5_evidence_fixtures import current_v5_manifest


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    old_module = sys.modules.get(name)
    sys.modules[name] = module
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
        if old_module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old_module
    return module


alignment_runner = load_module(
    "flowpilot_test_model_test_alignment_runner",
    ROOT / "simulations" / "run_flowpilot_model_test_alignment_checks.py",
)
alignment_diagnostics = load_module(
    "flowpilot_test_model_test_alignment_diagnostics",
    ROOT / "simulations" / "flowpilot_model_test_alignment_diagnostics.py",
)
runtime_path_evidence = load_module(
    "flowpilot_runtime_path_evidence",
    ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_runtime_path_evidence.py",
)


class FlowPilotModelTestAlignmentTests(unittest.TestCase):
    _manifest_cache: dict[tuple[str, ...], dict[str, object]] = {}

    @classmethod
    def _current_v5_manifest(
        cls,
        *,
        tiers: tuple[str, ...],
        release: bool,
    ) -> dict[str, object]:
        cache_key = (*tiers, "release" if release else "routine")
        commands = {
            command.name: command
            for tier in tiers
            for command in commands_for_tier(tier)
        }
        contracts = {
            contract.owner_id: contract
            for contract in impact_resolution.build_owner_contracts(
                tuple(commands.values())
            )
        }
        scope_id = "release" if release else "all"
        owner_ids = sorted(commands)
        manifest = current_v5_manifest(
            owner_ids,
            source_path=Path(__file__),
            selected_count=len(owner_ids),
            release=release,
            suite_id=scope_id,
            aggregate_artifact_id=f"proof.mta-current-{scope_id}-v5",
            owner_identities={
                owner_id: impact_resolution.owner_identity(
                    contracts[owner_id]
                ).to_dict()
                for owner_id in owner_ids
            },
            owner_commands={
                owner_id: commands[owner_id].command
                for owner_id in owner_ids
            },
        )
        cls._manifest_cache[cache_key] = manifest
        return manifest

    @classmethod
    def current_manifest(cls) -> dict[str, object]:
        return cls._current_v5_manifest(
            tiers=("all", "formal-submit-adversarial"),
            release=False,
        )

    @classmethod
    def done_manifest(cls) -> dict[str, object]:
        return cls._current_v5_manifest(
            tiers=("all", "formal-submit-adversarial", "release"),
            release=True,
        )

    def strict_report(self) -> dict[str, object]:
        return alignment_runner.build_report(evidence_manifest=self.current_manifest())

    def test_alignment_report_is_green_for_declared_current_scope(self) -> None:
        report = self.strict_report()

        self.assertTrue(report["ok"], report["findings"])
        self.assertTrue(report["alignment_ok"], report["findings"])
        self.assertTrue(report["known_bad_ok"])
        self.assertTrue(report["source_audit_ok"], report["findings"])
        self.assertTrue(report["source_known_bad_ok"])
        self.assertTrue(report["full_diagnostic_ok"])
        if not report["release_convergence_ok"]:
            self.assertFalse(report["full_model_test_code_diagnostic"]["release_convergence_ok"])
        if not report["full_coverage_ok"]:
            diagnostic = report["full_model_test_code_diagnostic"]
            self.assertGreater(
                diagnostic["deferred_structure_split_count"]
                + diagnostic["unresolved_non_deferred_gap_count"],
                0,
            )
        self.assertEqual(
            report["families"],
            [
                "startup",
                "packet/card/ack",
                "packet result family",
                "route mutation",
                "unified historical and terminal repair integrity",
                "field lifecycle currentness",
                "current-node trunk invariant",
                "terminal/closure/resume",
                "role/output contracts",
                "router loop/daemon",
                "repair transactions",
                "test tiering/slow-test contracts",
                "rejection/liveness matrix",
                "route authority singularity",
                "core deliverable non-downgrade",
                "flowguard 0.53 ppa maintenance",
                "complete workstream and ordinary resource discovery",
                "skillguard deep contract maintenance",
                "meta/capability parents",
            ],
        )
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["evidence_status"], "passed")

    def test_dedicated_mta_owner_remains_primary_when_release_repeats_file(self) -> None:
        bundle = {
            "owners": {
                "mta_evidence_target": {
                    "identity": {"covered_evidence_ids": ["evidence.subject"]}
                },
                "release_file_check": {
                    "identity": {"covered_evidence_ids": ["evidence.subject"]}
                },
            }
        }

        normalized = alignment_runner._single_mta_evidence_owner_bundle(
            bundle
        )

        self.assertEqual(
            normalized["owners"]["mta_evidence_target"]["identity"][
                "covered_evidence_ids"
            ],
            ["evidence.subject"],
        )
        self.assertEqual(
            normalized["owners"]["release_file_check"]["identity"][
                "covered_evidence_ids"
            ],
            [],
        )

    def test_multiple_dedicated_mta_owners_block_evidence_binding(self) -> None:
        bundle = {
            "owners": {
                "mta_evidence_first": {
                    "identity": {"covered_evidence_ids": ["evidence.subject"]}
                },
                "mta_evidence_second": {
                    "identity": {"covered_evidence_ids": ["evidence.subject"]}
                },
            }
        }

        normalized = alignment_runner._single_mta_evidence_owner_bundle(
            bundle
        )

        self.assertEqual(
            normalized,
            bundle,
        )

    def test_complete_workstream_report_contract_keeps_one_atomic_error_path(self) -> None:
        entries = alignment_runner.build_alignment_plan_entries()
        entry = next(
            entry
            for entry in entries
            if entry["family"] == "complete workstream and ordinary resource discovery"
        )
        contract = next(
            contract
            for contract in entry["plan"].code_contracts
            if contract.code_contract_id == "complete_workstream.semantic_report_projection"
        )

        self.assertEqual(
            contract.error_paths,
            ("missing, vague, incomplete, stale, or contradictory plan report",),
        )

    def test_route_authority_singularity_family_maps_model_runtime_and_replay(self) -> None:
        entries = alignment_runner.build_alignment_plan_entries()
        entry = next(entry for entry in entries if entry["family"] == "route authority singularity")
        plan = entry["plan"]
        obligations = {item.obligation_id for item in plan.obligations}
        contracts = {item.code_contract_id: item for item in plan.code_contracts}
        evidence = {item.evidence_id: item for item in plan.test_evidence}

        for obligation in (
            "route_authority.single_owner_and_legal_action_visibility",
            "route_authority.reject_wrong_path_alias_and_fallback",
            "route_authority.corrected_retry_changes_packet_shape",
            "route_authority.parent_mesh_blocks_missing_or_conflicted_evidence",
            "route_authority.fake_ai_variant_matrix",
        ):
            with self.subTest(obligation=obligation):
                self.assertIn(obligation, obligations)

        for contract in (
            "route_authority.runtime.snapshot",
            "route_authority.runtime.require_legal_action",
            "route_authority.runtime.reject_submission",
            "route_authority.runtime.reject_unsupported_payload",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, contracts)

        self.assertEqual(
            evidence["route_authority.replay.fake_ai_matrix_variants"].test_name,
            "test_route_authority_fake_ai_matrix_covers_alias_fallback_no_delta_and_feedback",
        )
        self.assertEqual(
            evidence["route_authority.replay.corrected_retry"].test_name,
            "test_route_authority_wrong_path_rejection_guides_corrected_retry_fake_package",
        )
        self.assertEqual(
            evidence["route_authority.negative.runtime_rejections"].path,
            "tests/router_runtime/route_mutation_parent_backward.py",
        )

    def test_packet_result_family_covers_flowguard_current_report_gate(self) -> None:
        entries = alignment_runner.build_alignment_plan_entries()
        packet_entry = next(entry for entry in entries if entry["family"] == "packet result family")
        obligations = {item.obligation_id for item in packet_entry["plan"].obligations}
        contracts = {item.code_contract_id: item for item in packet_entry["plan"].code_contracts}
        evidence = {item.evidence_id: item for item in packet_entry["plan"].test_evidence}

        for owner in ("research", "current_node", "pm_role_work"):
            for suffix in (
                "durable_event_fold",
                "partial_member_wait",
                "recipient_and_sealed_boundary",
            ):
                with self.subTest(owner=owner, suffix=suffix):
                    self.assertIn(
                        f"packet_result_family.{owner}.{suffix}", obligations
                    )

        retired_prefix = "packet_result_family.material_scan."
        self.assertFalse(
            any(obligation.startswith(retired_prefix) for obligation in obligations)
        )
        self.assertFalse(
            any(
                covered.startswith(retired_prefix)
                for item in evidence.values()
                for covered in item.covered_obligations
            )
        )
        self.assertFalse(
            any(
                evidence_id.startswith(
                    (
                        "packet_result_family.happy.material_scan_",
                        "packet_result_family.edge.material_scan_",
                        "packet_result_family.negative.material_scan_",
                    )
                )
                for evidence_id in evidence
            )
        )

        obligation = "packet_result_family.flowguard_current_report_before_reviewer"
        self.assertIn(obligation, obligations)
        self.assertIn("packet_result_family.flowguard_artifact_hard_decision_before_reviewer", obligations)
        self.assertIn("packet_result_family.flowguard_repair_blocker_identity_continuity", obligations)
        self.assertIn("packet_result_family.flowguard_semantic_recheck_subject_bound", obligations)
        self.assertIn("packet_result_family.reviewer_blocks_shallow_flowguard_depth", obligations)
        self.assertIn("packet_result_family.flowguard_semantic_recheck_ai_facing_projection", obligations)
        self.assertIn("packet_result_family.flowguard_semantic_recheck_corrected_retry_convergence", obligations)
        self.assertIn("packet_result_family.contract_driven_fake_ai_cartesian_retry", obligations)
        self.assertIn("packet_result_family.fake_ai_runtime_replay_matrix_closure", obligations)
        self.assertIn("packet_result_family.real_issue_backfeed_registry_bridge", obligations)
        self.assertIn("packet_result_family.sealed_body_related_context_reads", obligations)
        self.assertIn("packet_result_family.clean_e2e_authorized_material_openings", obligations)
        self.assertIn("packet_result_family.pm_repair_evidence_obligation_lifecycle", obligations)
        self.assertIn("packet_result_family.flowguard_reissue_preserves_current_evidence_policy", obligations)
        self.assertIn("packet_result_family.flowguard_reissue_preserves_required_authorized_result_reads", obligations)
        self.assertIn(
            "packet_result_family.flowguard_standard_reissue_preserves_required_authorized_result_reads",
            obligations,
        )
        self.assertIn(
            "packet_result_family.flowguard_semantic_recheck_reissue_preserves_required_authorized_result_reads",
            obligations,
        )
        self.assertIn("packet_result_family.review_handoff_blocks_empty_required_flowguard_manifest", obligations)
        self.assertIn("packet_result_family.repair_loop_glass_break_root_cause_identity", obligations)
        self.assertIn("packet_result_family.historical_failure_families_have_normal_repair_routes", obligations)
        self.assertIn("packet_result_family.glass_break_is_alarm_not_success_path", obligations)
        self.assertIn("packet_result_family.contract_exhaustion_matrix_owners_are_child_suites", obligations)
        self.assertIn("packet_result_family.cartesian_control_plane_cells_have_oracles", obligations)
        self.assertIn(
            "packet_result_family.integration_cartesian_coverage_keeps_pm_optimization_boundary",
            obligations,
        )
        self.assertIn("packet_result_family.pointer_persistence_hardening", obligations)
        self.assertIn("packet_result_family.submit_result_body_entry_hardening", obligations)
        for owner in alignment_runner.CURRENT_CARTESIAN_RISK_SHARD_OWNERS:
            self.assertIn(f"packet_result_family.current_cartesian_risk_shard.{owner}", obligations)
            self.assertIn(f"packet_result_family.runner.current_cartesian_risk_shard.{owner}", contracts)
        self.assertIn("packet_result_family.runtime.flowguard_current_report_gate", contracts)
        self.assertIn("packet_result_family.runtime.flowguard_artifact_hard_decision", contracts)
        self.assertIn("packet_result_family.runtime.flowguard_semantic_recheck_gate", contracts)
        self.assertIn("packet_result_family.runtime.review_packet_flowguard_depth_instruction", contracts)
        self.assertIn("packet_result_family.prompt.reviewer_shallow_flowguard_depth_card", contracts)
        self.assertIn("packet_result_family.runtime.effective_result_contract_profiles", contracts)
        self.assertIn("packet_result_family.runtime.current_handoff_result_profile_contract", contracts)
        self.assertIn("packet_result_family.runtime.current_contract_reissue_feedback", contracts)
        self.assertIn("packet_result_family.simulation.contract_driven_fake_ai_responder", contracts)
        self.assertIn("packet_result_family.model.fake_ai_runtime_replay_matrix", contracts)
        self.assertIn("packet_result_family.runner.fake_ai_runtime_replay_checks", contracts)
        self.assertIn("packet_result_family.model.real_issue_backfeed_registry", contracts)
        self.assertIn("packet_result_family.runtime.flowguard_reissue_inherited_body_payload", contracts)
        self.assertIn("packet_result_family.runtime.flowguard_reissue_inherited_authorized_reads", contracts)
        self.assertIn("packet_result_family.runtime.flowguard_reissue_issue_task_packet_reads", contracts)
        self.assertIn("packet_result_family.simulation.fake_e2e_authorized_material_proof", contracts)
        self.assertIn("packet_result_family.simulation.fake_e2e_shallow_flowguard_reviewer_block", contracts)
        self.assertIn("packet_result_family.runtime.flowguard_packet_issue_inherits_blocker", contracts)
        self.assertIn("packet_result_family.runtime.blocker_related_authorized_reads", contracts)
        self.assertIn("packet_result_family.runtime.pm_repair_obligation_disposition_gate", contracts)
        self.assertIn("packet_result_family.runtime.repair_obligation_context_projection", contracts)
        self.assertIn("packet_result_family.runtime.repair_blocker_identity_formal_gate", contracts)
        self.assertIn("packet_result_family.runtime.flowguard_work_order_hard_decision", contracts)
        self.assertIn("packet_result_family.runtime.flowguard_review_handoff", contracts)
        self.assertIn("packet_result_family.runtime.missing_flowguard_review_handoff_blocker", contracts)
        self.assertIn("packet_result_family.runtime.repair_loop_root_cause_count", contracts)
        self.assertIn("packet_result_family.model.contract_exhaustion_history_matrix", contracts)
        self.assertIn("packet_result_family.runner.contract_exhaustion_test_mesh_owner_consumption", contracts)
        self.assertIn("packet_result_family.model.cartesian_control_plane_exhaustion_matrix", contracts)
        self.assertIn("packet_result_family.runner.cartesian_control_plane_owner_consumption", contracts)
        self.assertIn("packet_result_family.model.integration_cartesian_coverage_matrix", contracts)
        self.assertIn("packet_result_family.runner.integration_cartesian_coverage_checks", contracts)
        self.assertIn("packet_result_family.runtime.pointer_store_write", contracts)
        self.assertIn("packet_result_family.runtime.pointer_store_recovery", contracts)
        self.assertIn("packet_result_family.runtime.submit_result_body_entry", contracts)
        self.assertIn("packet_result_family.cli.submit_result_body_file", contracts)
        self.assertEqual(
            evidence["packet_result_family.negative.flowguard_blocked_child_evidence"].test_name,
            "test_flowguard_packet_rejects_deleted_evidence_consistency_field_without_reviewer",
        )
        self.assertEqual(
            evidence["packet_result_family.edge.pointer_current_recovery"].test_name,
            "test_corrupt_current_pointer_recovers_from_single_current_run_evidence",
        )
        self.assertEqual(
            evidence["packet_result_family.negative.submit_result_pseudo_json"].test_name,
            "test_submit_result_rejects_pseudo_json_before_loading_current_run",
        )
        self.assertEqual(
            evidence["packet_result_family.negative.flowguard_failed_self_check"].test_name,
            "test_flowguard_packet_rejects_failed_contract_self_check_without_reviewer",
        )
        self.assertEqual(
            evidence["packet_result_family.replay.fake_e2e_flowguard_consistency_chaos"].test_name,
            "test_fake_end_to_end_flowguard_consistency_chaos_reissues_and_finishes",
        )
        self.assertEqual(
            evidence["packet_result_family.replay.fake_e2e_flowguard_artifact_chaos"].test_name,
            "test_fake_end_to_end_flowguard_artifact_chaos_reissues_and_finishes",
        )
        self.assertEqual(
            evidence["packet_result_family.replay.fake_e2e_shallow_flowguard_reviewer_block"].test_name,
            "test_fake_end_to_end_shallow_flowguard_is_reviewer_blocked",
        )
        self.assertEqual(
            evidence["packet_result_family.replay.fake_e2e_shallow_flowguard_reviewer_block"].covered_obligations,
            (
                "packet_result_family.reviewer_blocks_shallow_flowguard_depth",
                "packet_result_family.sealed_body_related_context_reads",
            ),
        )
        self.assertEqual(
            evidence["packet_result_family.negative.shallow_flowguard_reviewer_block"].test_name,
            "test_fake_end_to_end_shallow_flowguard_is_reviewer_blocked",
        )
        self.assertEqual(
            evidence["packet_result_family.prompt.reviewer_shallow_flowguard_depth_card"].test_name,
            "test_reviewer_card_blocks_shallow_flowguard_with_pm_recheck_guidance",
        )
        self.assertEqual(
            evidence["packet_result_family.replay.historical_skillguard_flowguard_artifact_block"].test_name,
            "test_historical_skillguard_flowguard_artifact_block_is_not_authoritative",
        )
        self.assertEqual(
            evidence["packet_result_family.negative.flowguard_artifact_missing_code_contract"].test_name,
            "test_flowguard_packet_rejects_artifact_missing_code_contract_without_reviewer",
        )
        self.assertEqual(
            evidence["packet_result_family.negative.flowguard_missing_evidence_output_policy"].test_name,
            "test_flowguard_packet_rejects_missing_evidence_output_policy",
        )
        self.assertEqual(
            evidence["packet_result_family.negative.flowguard_packet_policy_path_authority"].test_name,
            "test_flowguard_artifact_path_uses_packet_policy_before_derived_run_root",
        )
        self.assertEqual(
            evidence["packet_result_family.edge.flowguard_reissue_preserves_policy"].test_name,
            "test_flowguard_fallback_evidence_is_mechanically_reissued",
        )
        self.assertEqual(
            evidence["packet_result_family.edge.flowguard_reissue_preserves_authorized_reads"].test_name,
            "test_flowguard_reissue_inherits_required_authorized_result_reads",
        )
        self.assertEqual(
            evidence["packet_result_family.edge.flowguard_reissue_preserves_authorized_reads"].covered_obligations,
            ("packet_result_family.flowguard_standard_reissue_preserves_required_authorized_result_reads",),
        )
        self.assertEqual(
            evidence["packet_result_family.edge.flowguard_semantic_recheck_reissue_preserves_authorized_reads"].test_name,
            "test_flowguard_semantic_recheck_reissue_inherits_required_authorized_reads",
        )
        self.assertEqual(
            evidence["packet_result_family.edge.flowguard_semantic_recheck_reissue_preserves_authorized_reads"].covered_obligations,
            (
                "packet_result_family.flowguard_semantic_recheck_subject_bound",
                "packet_result_family.flowguard_semantic_recheck_reissue_preserves_required_authorized_result_reads",
            ),
        )
        self.assertEqual(
            evidence["packet_result_family.negative.flowguard_reissue_requires_inherited_body_open"].test_name,
            "test_reissued_flowguard_result_blocks_without_inherited_body_open",
        )
        self.assertEqual(
            evidence["packet_result_family.negative.empty_required_flowguard_manifest"].test_name,
            "test_review_packet_is_not_issued_with_empty_required_flowguard_manifest",
        )
        self.assertEqual(
            evidence["packet_result_family.negative.same_root_break_glass"].test_name,
            "test_break_glass_counts_same_flowguard_root_cause_across_surface_gates",
        )
        self.assertEqual(
            evidence["packet_result_family.edge.flowguard_auto_recheck_inherits_blocker"].test_name,
            "test_repair_task_flowguard_packet_inherits_blocker_identity",
        )
        self.assertEqual(
            evidence["packet_result_family.edge.flowguard_explicit_recheck_inherits_blocker"].test_name,
            "test_explicit_flowguard_action_inherits_repair_blocker_identity",
        )
        self.assertEqual(
            evidence["packet_result_family.negative.repair_identity_mismatch_blocks"].test_name,
            "test_formal_repair_identity_mismatch_is_runtime_mechanical_blocker",
        )
        self.assertEqual(
            evidence["packet_result_family.negative.flowguard_shape_only_semantic_recheck"].test_name,
            "test_semantic_recheck_rejects_shape_only_flowguard_pass",
        )
        self.assertEqual(
            evidence["packet_result_family.happy.flowguard_subject_bound_semantic_recheck"].test_name,
            "test_semantic_recheck_subject_bound_flowguard_pass_reaches_reviewer",
        )
        self.assertEqual(
            evidence["packet_result_family.happy.flowguard_ai_contract_projection"].test_name,
            "test_semantic_recheck_contract_projects_ai_facing_fields_and_options",
        )
        self.assertEqual(
            evidence["packet_result_family.negative.flowguard_ai_contract_forbidden_alias_feedback"].test_name,
            "test_semantic_recheck_near_synonyms_reissue_with_correct_minimal_shape",
        )
        self.assertEqual(
            evidence["packet_result_family.negative.flowguard_semantic_recheck_purpose_string"].test_name,
            "test_semantic_recheck_purpose_string_is_rejected_as_consumed_result_id",
        )
        self.assertEqual(
            evidence["packet_result_family.replay.flowguard_ai_contract_corrected_retry"].test_name,
            "test_semantic_recheck_wrong_value_then_corrected_retry_returns_to_legal_path",
        )
        self.assertEqual(
            evidence["packet_result_family.negative.contract_driven_fake_ai_missing_options"].test_name,
            "test_contract_driven_fake_ai_refuses_to_guess_when_finite_options_are_missing",
        )
        self.assertEqual(
            evidence["packet_result_family.replay.contract_driven_fake_ai_cartesian_retry"].test_name,
            "test_contract_driven_fake_ai_wrong_value_rows_repair_each_finite_option",
        )
        self.assertEqual(
            evidence["packet_result_family.replay.fake_ai_runtime_replay_matrix"].test_name,
            "test_runtime_replay_cells_bind_fake_ai_errors_to_runtime_reactions",
        )
        self.assertEqual(
            evidence["packet_result_family.replay.fake_e2e_authorized_material_openings"].test_name,
            "test_fake_end_to_end_rehearsal_reaches_final_closure",
        )
        self.assertEqual(
            evidence["packet_result_family.negative.fake_ai_runtime_replay_hazards"].test_name,
            "test_fake_ai_runtime_replay_runner_accepts_valid_and_rejects_hazards",
        )
        self.assertEqual(
            evidence["packet_result_family.replay.real_issue_backfeed_registry"].test_name,
            "test_real_issue_backfeed_registry_bridges_every_issue_to_runtime_replay",
        )
        self.assertEqual(
            evidence["packet_result_family.negative.real_issue_backfeed_rejects_incomplete_rows"].test_name,
            "test_real_issue_backfeed_rejects_missing_fields_and_sealed_body_copies",
        )
        self.assertEqual(
            evidence["packet_result_family.happy.related_blocker_bodies_delivered_to_pm"].test_name,
            "test_reviewer_required_repair_reaches_pm_repair_packet",
        )
        self.assertEqual(
            evidence["packet_result_family.negative.related_blocker_bodies_must_be_opened"].test_name,
            "test_pm_repair_decision_blocks_without_opening_all_related_bodies",
        )
        self.assertEqual(
            evidence["packet_result_family.happy.pm_repair_obligations_projected"].test_name,
            "test_pm_repair_packet_projects_blocker_body_into_repair_obligations",
        )
        self.assertEqual(
            evidence["packet_result_family.negative.pm_repair_reason_only_obligation_loss"].test_name,
            "test_pm_repair_decision_reason_only_is_rejected_when_obligations_exist",
        )
        self.assertEqual(
            evidence["packet_result_family.negative.pm_repair_stale_or_registry_only_obligation"].test_name,
            "test_pm_repair_obligation_rejects_stale_or_registry_only_disposition",
        )
        self.assertEqual(
            evidence["packet_result_family.negative.flowguard_missing_repair_obligation_consumption"].test_name,
            "test_repair_packet_and_flowguard_recheck_must_consume_repair_obligations",
        )
        self.assertEqual(
            evidence["packet_result_family.replay.contract_exhaustion_mesh"].test_name,
            "test_contract_exhaustion_mesh_accepts_valid_and_rejects_hazards",
        )
        self.assertEqual(
            evidence["packet_result_family.replay.contract_exhaustion_historical_failure_families"].test_name,
            "test_historical_failure_families_require_normal_repair_before_glass_break",
        )
        self.assertEqual(
            evidence["packet_result_family.replay.contract_exhaustion_test_mesh_owner_consumption"].test_name,
            "test_contract_exhaustion_test_mesh_registers_every_required_owner",
        )
        self.assertEqual(
            evidence["packet_result_family.negative.glass_break_alarm_not_success_path"].test_kind,
            "negative_path",
        )
        self.assertEqual(
            evidence["packet_result_family.replay.cartesian_control_plane_exhaustion"].test_name,
            "test_cartesian_runner_accepts_valid_and_rejects_hazards",
        )
        self.assertEqual(
            evidence["packet_result_family.negative.cartesian_normal_repair_not_glassbreak"].test_name,
            "test_normal_repair_cells_never_expect_glassbreak",
        )
        self.assertEqual(
            evidence["packet_result_family.replay.integration_cartesian_full_matrix"].test_name,
            "test_integration_cartesian_runner_accepts_full_matrix",
        )
        self.assertEqual(
            evidence["packet_result_family.negative.integration_cartesian_authority_boundary"].test_name,
            "test_worker_and_runtime_do_not_gain_semantic_integration_authority",
        )

    def test_full_diagnostic_inventory_reports_current_gap_classes(self) -> None:
        report = self.strict_report()
        diagnostic = report["full_model_test_code_diagnostic"]

        self.assertTrue(diagnostic["ok"], diagnostic["known_bad_sanity_checks"])
        self.assertGreater(diagnostic["surface_count"], 100)
        for kind in (
            "owner_module",
            "public_facade",
            "script_entrypoint",
            "model_check_runner",
            "test_tier",
            "test_tier_command",
        ):
            with self.subTest(kind=kind):
                self.assertGreater(diagnostic["surface_counts"].get(kind, 0), 0)

        self.assertEqual(diagnostic["gap_counts"].get("missing_model", 0), 0)
        self.assertEqual(diagnostic["gap_counts"].get("extra_code", 0), 0)
        self.assertEqual(diagnostic["gap_counts"].get("internal_only_test", 0), 0)
        self.assertEqual(diagnostic["gap_counts"].get("missing_test", 0), 0)
        unresolved_structural_findings = [
            finding
            for finding in diagnostic["actionable_findings"]
            if finding["code"] != "stale_evidence"
            and finding["repair_type"] != "defer_structure_split"
        ]
        self.assertEqual(unresolved_structural_findings, [])
        expected_release_convergence = not any(
            finding["repair_type"] != "defer_structure_split"
            for finding in diagnostic["actionable_findings"]
        )
        self.assertEqual(
            diagnostic["release_convergence_ok"],
            expected_release_convergence,
        )

        gate_contract_gaps = [
            finding
            for finding in diagnostic["actionable_findings"]
            if finding["release_relevance"] in {"release_gate", "validation_gate"}
            and finding["code"] in {"missing_test", "internal_only_test"}
        ]
        self.assertEqual(gate_contract_gaps, [])

        for field in (
            "gap_counts_by_severity",
            "gap_counts_by_repair_type",
            "gap_counts_by_release_relevance",
            "actionable_summary",
        ):
            with self.subTest(field=field):
                self.assertIn(field, diagnostic)
        non_deferred_non_evidence_findings = [
            finding
            for finding in diagnostic["actionable_findings"]
            if finding["repair_type"] != "defer_structure_split"
            and finding["code"] != "stale_evidence"
        ]
        self.assertEqual(non_deferred_non_evidence_findings, [])
        if diagnostic["full_coverage_ok"]:
            self.assertEqual(diagnostic["gap_counts"].get("needs_structure_split", 0), 0)
            self.assertEqual(diagnostic["actionable_findings"], [])
            self.assertEqual(diagnostic["actionable_summary"], [])
        else:
            self.assertGreater(diagnostic["gap_counts"].get("needs_structure_split", 0), 0)
            self.assertGreater(diagnostic["deferred_structure_split_count"], 0)

        surfaces = {surface["surface_id"]: surface for surface in diagnostic["surfaces"]}
        self.assertIn("asset:flowpilot_router", surfaces)
        self.assertIn("script:run_test_tier", surfaces)
        self.assertIn("model-check:run_flowpilot_model_test_alignment_checks", surfaces)
        self.assertIn("tier:router", surfaces)
        self.assertIn("model-check:run_flowpilot_singleton_identity_checks", surfaces)
        singleton_authority = diagnostic["singleton_authority_coverage"]
        self.assertTrue(singleton_authority["ok"], singleton_authority)
        self.assertGreaterEqual(singleton_authority["authority_matrix_count"], 8)
        self.assertEqual(
            "simulations/flowpilot_singleton_identity_results.json",
            singleton_authority["result_path"],
        )
        for surface_id in (
            "asset:flowpilot_router",
            "script:run_test_tier",
            "tier:router",
        ):
            with self.subTest(surface_id=surface_id):
                surface = surfaces[surface_id]
                self.assertIn("surface_owner", surface)
                self.assertIn("release_relevance", surface)
                self.assertIn("repair_types", surface)
                self.assertIn("max_severity", surface)

        for finding in diagnostic["actionable_findings"][:20]:
            with self.subTest(finding=finding["dedupe_key"]):
                for field in (
                    "severity",
                    "surface_owner",
                    "release_relevance",
                    "repair_type",
                    "dedupe_key",
                    "priority_score",
                ):
                    self.assertIn(field, finding)

        priority_scores = [
            item["priority_score"] for item in diagnostic["actionable_findings"]
        ]
        self.assertEqual(priority_scores, sorted(priority_scores))


    def test_full_diagnostic_known_bad_cases_cover_false_confidence_hazards(self) -> None:
        diagnostic = self.strict_report()["full_model_test_code_diagnostic"]
        checks = {case["name"]: case for case in diagnostic["known_bad_sanity_checks"]}

        for name in (
            "orphan_code",
            "wrapper_only_evidence",
            "progress_only_background",
            "local_only_release_proof",
            "broad_unsplit_module",
        ):
            with self.subTest(name=name):
                self.assertIn(name, checks)
                self.assertTrue(checks[name]["ok"], checks[name])
                self.assertLessEqual(
                    set(checks[name]["expected_codes"]),
                    set(checks[name]["finding_codes"]),
                )
                surface = checks[name]["surface"]
                self.assertIn("surface_owner", surface)
                self.assertIn("release_relevance", surface)
                self.assertIn("repair_types", surface)

        self.assertIn(
            "rerun_public_release_evidence",
            checks["local_only_release_proof"]["surface"]["repair_types"],
        )

    def test_full_diagnostic_recognizes_public_contract_and_split_metadata(self) -> None:
        diagnostic = self.strict_report()["full_model_test_code_diagnostic"]
        surfaces = {surface["surface_id"]: surface for surface in diagnostic["surfaces"]}

        for surface_id in (
            "asset:packet_runtime",
            "asset:flowpilot_router_controller_scheduler_receipts",
            "asset:flowpilot_router_work_packets_pm_role",
            "asset:flowpilot_router_terminal_ledger",
        ):
            with self.subTest(surface_id=surface_id):
                surface = surfaces[surface_id]
                self.assertTrue(surface["has_external_contract"], surface)
                self.assertNotIn("internal_only_test", surface["gap_codes"])

        for surface_id in (
            "tier:integration",
            "tier-command:integration:smoke_flowpilot_fast",
            "tier-command:all:smoke_flowpilot_fast",
        ):
            with self.subTest(surface_id=surface_id):
                surface = surfaces[surface_id]
                self.assertTrue(surface["has_external_contract"], surface)
                self.assertNotIn("missing_test", surface["gap_codes"])
                self.assertNotIn("internal_only_test", surface["gap_codes"])

        for surface_id in (
            "script:install_flowpilot",
            "script:audit_local_install_sync",
            "script:check_install",
            "script:check_public_release",
            "script:flowpilot_packets",
            "script:flowpilot_outputs",
            "script:flowpilot_lifecycle",
            "script:run_test_tier",
        ):
            with self.subTest(surface_id=surface_id):
                surface = surfaces[surface_id]
                self.assertTrue(surface["has_test"], surface)
                self.assertTrue(surface["has_external_contract"], surface)
                self.assertNotIn("internal_only_test", surface["gap_codes"])

        completed_runtime_split = surfaces["asset:flowpilot_router_card_returns"]
        self.assertEqual(completed_runtime_split["split_status"], "completed_split")
        self.assertTrue(completed_runtime_split["has_external_contract"], completed_runtime_split)
        self.assertNotIn("needs_structure_split", completed_runtime_split["gap_codes"])
        self.assertIn("peer_safety_status", completed_runtime_split)

        completed = surfaces["asset:flowpilot_router_protocol_boot_cards"]
        self.assertEqual(completed["split_status"], "completed_split")
        self.assertTrue(completed["has_external_contract"], completed)
        self.assertNotIn("needs_structure_split", completed["gap_codes"])
        for surface_id in (
            "asset:flowpilot_router_protocol_startup_catalog",
            "asset:flowpilot_router_protocol_planning_cards",
            "asset:flowpilot_router_protocol_runtime_cards",
            "asset:flowpilot_router_protocol_card_metadata",
        ):
            with self.subTest(completed_split_surface=surface_id):
                surface = surfaces[surface_id]
                self.assertTrue(surface["has_external_contract"], surface)
                self.assertEqual(surface["gap_codes"], [])

        split_table = surfaces["asset:flowpilot_router_protocol_external_event_data"]
        self.assertEqual(split_table["split_status"], "completed_split")
        self.assertEqual(split_table["safe_split_class"], "declarative_protocol_table")
        self.assertLessEqual(split_table["line_count"], split_table["split_threshold"])
        self.assertEqual(split_table["top_level_function_count"], 0)
        self.assertEqual(split_table["top_level_class_count"], 0)
        self.assertNotIn("needs_structure_split", split_table["gap_codes"])
        self.assertTrue(split_table["has_external_contract"], split_table)
        for surface_id in (
            "asset:flowpilot_router_protocol_external_event_data_startup",
            "asset:flowpilot_router_protocol_external_event_data_material",
            "asset:flowpilot_router_protocol_external_event_data_route",
            "asset:flowpilot_router_protocol_external_event_data_terminal",
        ):
            with self.subTest(completed_external_event_data_surface=surface_id):
                surface = surfaces[surface_id]
                self.assertTrue(surface["has_external_contract"], surface)
                self.assertEqual(surface["gap_codes"], [])

    def test_full_diagnostic_uses_scope_aware_testmesh_bundle_classification(self) -> None:
        diagnostic = self.strict_report()["full_model_test_code_diagnostic"]
        surfaces = {surface["surface_id"]: surface for surface in diagnostic["surfaces"]}
        surface = surfaces["tier-command:release:public_release_check"]

        self.assertEqual(surface["evidence_status"], "deferred_release_scope")
        self.assertIn("background_evidence", surface)
        self.assertIn("selected", surface["background_evidence"])
        self.assertEqual(surface["gap_codes"], [])

    def test_done_scope_consumes_upstream_bundle_and_leaves_final_confidence_downstream(self) -> None:
        report = alignment_runner.build_report(
            evidence_manifest=self.done_manifest(),
            evidence_scope="done",
        )
        self.assertTrue(report["ok"], report["findings"])
        surfaces = {
            surface["surface_id"]: surface
            for surface in report["full_model_test_code_diagnostic"]["surfaces"]
        }
        self.assertEqual(
            surfaces["tier-command:release:public_release_check"]["evidence_status"],
            "passed",
        )
        final_surface = surfaces["tier-command:final-confidence:flowpilot_final_confidence_gate"]
        self.assertEqual(final_surface["evidence_status"], "downstream_consumer")
        self.assertEqual(final_surface["gap_codes"], [])

    def test_bundle_classification_uses_exact_owner_proof_not_aggregate_summary(
        self,
    ) -> None:
        command = next(
            row
            for row in commands_for_tier("release")
            if row.name == "meta_full"
        )
        proof = {
            "artifact_id": "proof.owner.meta_full",
            "artifact_fingerprints": {
                "stdout": "a" * 64,
                "stderr": "b" * 64,
                "combined": "a" * 64,
                "child_meta": "b" * 64,
            },
            "current": True,
            "exit_code": 0,
            "metadata": {"owner_id": "meta_full"},
            "progress_only": False,
            "result_path": "tmp/test_background/release/meta_full.combined.txt",
            "result_status": "passed",
            "route_evidence_current": True,
        }
        bundle = {
            "owners": {
                "meta_full": {
                    "owner_id": "meta_full",
                    "result_status": "passed",
                    "result_reused": True,
                    "proof_artifact": proof,
                }
            },
            "proof_artifacts": [
                {
                    "artifact_id": "proof.aggregate",
                    "artifact_fingerprints": {"owner-set": "c" * 64},
                }
            ],
        }
        evidence = alignment_diagnostics._bundle_evidence_for_command(
            test_tier_runner,
            command,
            tier="release",
            bundle=bundle,
            scope="done",
        )

        self.assertIsNotNone(evidence)
        assert evidence is not None
        self.assertTrue(evidence["selected"]["ok"], evidence)
        self.assertEqual(
            evidence["selected"]["proof_scope"],
            "current_owner_testmesh_proof",
        )
        self.assertTrue(evidence["selected"]["owner_result_reused"])

        legacy_exit_only = {
            **proof,
            "artifact_fingerprints": {
                "combined": "a" * 64,
                "exit": "b" * 64,
            },
        }
        legacy = alignment_diagnostics._bundle_evidence_for_command(
            test_tier_runner,
            command,
            tier="release",
            bundle={
                "owners": {
                    "meta_full": {
                        "owner_id": "meta_full",
                        "result_status": "passed",
                        "result_reused": True,
                        "proof_artifact": legacy_exit_only,
                    }
                },
            },
            scope="done",
        )
        self.assertIsNotNone(legacy)
        assert legacy is not None
        self.assertFalse(legacy["selected"]["ok"])
        self.assertIn(
            "current owner proof check failed: proof_artifacts_present",
            legacy["selected"]["reasons"],
        )

        missing = alignment_diagnostics._bundle_evidence_for_command(
            test_tier_runner,
            command,
            tier="release",
            bundle={
                "owners": {},
                "proof_artifacts": bundle["proof_artifacts"],
            },
            scope="done",
        )
        self.assertIsNotNone(missing)
        assert missing is not None
        self.assertFalse(missing["selected"]["ok"])
        self.assertEqual(
            missing["selected"]["status"],
            "missing_final_artifacts",
        )

    def test_source_audit_binds_code_contracts_to_real_python_sources(self) -> None:
        report = self.strict_report()
        source_plan = report["source_contract_plan"]

        self.assertTrue(source_plan["ok"], source_plan["findings"])

        self.assertTrue(source_plan["alignment_report"]["ok"])
        self.assertTrue(source_plan["source_audit_report"]["ok"])
        self.assertEqual(source_plan["source_audit_report"]["findings"], [])
        self.assertIn("AST-supported subset", source_plan["source_audit_boundary"])

        code_contract_ids = {
            item["code_contract_id"] for item in source_plan["plan"]["code_contracts"]
        }
        for code_contract_id in (
            "router.record_external_event",
            "packet.create_packet",
            "card.submit_card_ack",
            "route_sign.generate",
            "role_output.prepare_output_session",
            "runtime_closure.validate_flowguard_operator_request_record",
            "runtime_closure.continuation_quarantine_record",
            "daemon.run_router_daemon",
            "daemon.acquire_lock",
            "daemon.write_status",
            "startup_daemon.patrol_monitor",
            "test_tier.commands_for_tier",
            "meta_runner.main",
            "smoke.main",
        ):
            with self.subTest(code_contract_id=code_contract_id):
                self.assertIn(code_contract_id, code_contract_ids)

        for evidence in source_plan["source_audit_report"]["test_evidence"]:
            with self.subTest(evidence=evidence["evidence_id"]):
                self.assertTrue(evidence["found"], evidence)
                self.assertGreater(evidence["assert_count"], 0, evidence)
                self.assertEqual(evidence["assertion_scope"], "external_contract")

    def test_material_map_navigation_has_one_exact_code_owner(self) -> None:
        plan = alignment_runner.build_source_contract_alignment_plan()
        contracts = {
            row.code_contract_id: row
            for row in plan.code_contracts
            if row.code_contract_id.startswith("material_artifact_map")
        }
        owner = contracts["material_artifact_map.navigation_status"]

        self.assertEqual(owner.role, "owner")
        self.assertEqual(owner.behavior_plane, "agent_operation")
        self.assertEqual(
            owner.behavior_commitment_id,
            "commit.material_map_is_optional_navigation_only",
        )
        self.assertTrue(owner.business_intent_id)
        self.assertTrue(owner.primary_path_id)
        for contract_id, row in contracts.items():
            if contract_id == "material_artifact_map.navigation_status":
                continue
            self.assertIn(row.role, {"helper", "read_only"}, contract_id)

    def test_each_plan_serializes_obligations_evidence_and_flowguard_report(self) -> None:
        report = self.strict_report()

        for plan in report["per_plan"]:
            with self.subTest(family=plan["family"]):
                self.assertTrue(plan["ok"], plan)
                self.assertEqual(plan["decision"], "model_test_alignment_green")
                self.assertTrue(plan["model_checks"])
                self.assertIn("coverage_boundary", plan)
                self.assertIn("runtime_path_summary", plan)
                self.assertGreaterEqual(len(plan["plan"]["obligations"]), 1)
                self.assertGreaterEqual(len(plan["plan"]["test_evidence"]), 1)
                self.assertEqual(plan["report"]["findings"], [])
                self.assertIn("model_test_alignment_green", plan["report"]["summary"])

    def test_each_plan_has_parseable_runtime_path_evidence(self) -> None:
        report = self.strict_report()

        for plan in report["per_plan"]:
            with self.subTest(family=plan["family"]):
                payload = plan["plan"]
                summary = plan["runtime_path_summary"]
                obligations = payload["obligations"]
                contracts = {
                    contract["node_id"]: contract
                    for contract in payload["runtime_node_contracts"]
                }

                self.assertTrue(payload["require_runtime_path_evidence"])
                self.assertEqual(summary["runtime_path_run_count"], 1)
                self.assertEqual(summary["runtime_node_contract_count"], len(obligations))
                self.assertEqual(summary["runtime_observation_count"], len(obligations))
                self.assertEqual(summary["progress_line_count"], len(obligations))

                for obligation in obligations:
                    required_nodes = obligation["required_runtime_node_ids"]
                    self.assertGreaterEqual(len(required_nodes), 1)
                    for node_id in required_nodes:
                        contract = contracts[node_id]
                        self.assertEqual(contract["model_id"], payload["model_id"])
                        self.assertEqual(contract["model_obligation_id"], obligation["obligation_id"])
                        self.assertTrue(contract["model_path"].startswith("FlowPilot model-test alignment/"))
                        self.assertTrue(contract["required_observation_ids"])

                for line in summary["progress_lines"]:
                    self.assertTrue(line.startswith("flowguard.runtime_path "), line)
                    for token in (
                        "model=",
                        "node=",
                        "run=",
                        "status=passed",
                        "model_path=",
                        "obligation=",
                        "input_case=",
                        "state_case=",
                        "evidence=",
                        "progress=",
                    ):
                        self.assertIn(token, line)

    def test_flowpilot_runtime_path_evidence_helper_binds_model_nodes(self) -> None:
        plan = ModelTestAlignmentPlan(
            model_id="helper_contract",
            obligations=(
                ModelObligation(
                    "helper_contract.required_node",
                    obligation_type="contract",
                    required_test_kinds=("happy_path",),
                ),
            ),
            test_evidence=(
                TestEvidence(
                    "helper_contract.test_evidence",
                    test_name="test_flowpilot_runtime_path_evidence_helper_binds_model_nodes",
                    path="tests/test_flowpilot_model_test_alignment.py",
                    command="python -m unittest tests.test_flowpilot_model_test_alignment.FlowPilotModelTestAlignmentTests.test_flowpilot_runtime_path_evidence_helper_binds_model_nodes",
                    result_status="passed",
                    test_kind="happy_path",
                    covered_obligations=("helper_contract.required_node",),
                ),
            ),
        )

        bound = runtime_path_evidence.attach_runtime_path_evidence_to_plan(
            plan,
            family="helper contract",
            authority=alignment_runner.MTA_RUNTIME_PATH_AUTHORITY,
            code_contract_prefix="runtime_path.helper_contract",
        )
        lines = runtime_path_evidence.runtime_path_progress_lines(bound)

        self.assertTrue(bound.require_runtime_path_evidence)
        self.assertEqual(len(bound.runtime_node_contracts), 1)
        self.assertEqual(len(bound.runtime_path_runs), 1)
        self.assertEqual(
            bound.obligations[0].required_runtime_node_ids,
            ("helper_contract:helper_contract.required_node",),
        )
        self.assertEqual(len(lines), 1)
        self.assertIn("model=helper_contract", lines[0])
        self.assertIn("node=helper_contract:helper_contract.required_node", lines[0])
        self.assertIn("obligation=helper_contract.required_node", lines[0])
        authority = alignment_runner.MTA_RUNTIME_PATH_AUTHORITY
        contract = bound.runtime_node_contracts[0]
        observation = bound.runtime_path_runs[0].observations[0]
        run = bound.runtime_path_runs[0]
        expected_triplet = (
            authority.business_intent_id,
            authority.behavior_commitment_id,
            authority.primary_path_id,
        )
        for row in (contract, observation, run):
            self.assertEqual(
                (
                    row.business_intent_id,
                    row.behavior_commitment_id,
                    row.primary_path_id,
                ),
                expected_triplet,
            )
        self.assertEqual(bound.obligations[0].business_intent_id, "")
        self.assertEqual(bound.obligations[0].behavior_commitment_id, "")
        diagnostic_contract = next(
            row
            for row in bound.code_contracts
            if row.code_contract_id.startswith("runtime_path.helper_contract")
        )
        self.assertEqual(diagnostic_contract.behavior_plane, "")
        self.assertEqual(diagnostic_contract.business_intent_id, "")

        broken = replace(
            bound,
            runtime_path_runs=(
                replace(run, primary_path_id="path.development-process.wrong"),
            ),
        )
        broken_codes = {
            finding.code
            for finding in review_model_test_alignment(broken).findings
        }
        self.assertIn("runtime_run_primary_path_id_mismatch", broken_codes)

    def test_each_declared_test_evidence_path_contains_definition_when_source_auditable(self) -> None:
        skipped_names = {
            "run_packet_control_plane_checks",
            "FlowPilotControlGateTests meta/capability invariant checks",
        }
        evidence_rows = []
        for entry in alignment_runner.build_alignment_plan_entries():
            evidence_rows.extend(entry["plan"].test_evidence)
        evidence_rows.extend(
            alignment_runner.build_source_contract_alignment_plan().test_evidence
        )

        names_by_path: dict[str, set[str]] = {}
        for evidence in evidence_rows:
            if evidence.test_name in skipped_names:
                continue
            if not (
                evidence.test_name.startswith("test_")
                or evidence.test_name.startswith("Test")
            ):
                continue
            names = names_by_path.get(evidence.path)
            if names is None:
                source = (ROOT / evidence.path).read_text(encoding="utf-8")
                tree = ast.parse(source, filename=evidence.path)
                names = {
                    node.name
                    for node in ast.walk(tree)
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                }
                names_by_path[evidence.path] = names
            with self.subTest(evidence_id=evidence.evidence_id, path=evidence.path):
                self.assertIn(evidence.test_name, names)

    def test_known_bad_sanity_checks_cover_required_hazards(self) -> None:
        report = self.strict_report()
        checks = {case["name"]: case for case in report["known_bad_sanity_checks"]}

        for name in (
            "missing_evidence",
            "stale_evidence",
            "progress_only_background_evidence",
            "overclaim_model_confidence",
            "orphan_evidence",
            "duplicate_same_kind_evidence",
            "missing_runtime_path_evidence",
        ):
            with self.subTest(name=name):
                self.assertIn(name, checks)
                self.assertTrue(checks[name]["ok"], checks[name])
                self.assertLessEqual(
                    set(checks[name]["expected_codes"]),
                    set(checks[name]["finding_codes"]),
                )
                self.assertFalse(checks[name]["report"]["ok"])

    def test_source_known_bad_sanity_checks_cover_ast_hazards(self) -> None:
        report = self.strict_report()
        checks = {
            case["name"]: case
            for case in report["source_known_bad_sanity_checks"]
        }

        for name in (
            "missing_python_symbol",
            "internal_path_only_test",
            "missing_external_assertion",
            "extra_side_effect",
        ):
            with self.subTest(name=name):
                self.assertIn(name, checks)
                self.assertTrue(checks[name]["ok"], checks[name])
                self.assertLessEqual(
                    set(checks[name]["expected_codes"]),
                    set(checks[name]["finding_codes"]),
                )
                self.assertFalse(checks[name]["report"]["ok"])

    def test_progress_only_background_evidence_is_not_passing_coverage(self) -> None:
        report = self.strict_report()
        case = {
            item["name"]: item for item in report["known_bad_sanity_checks"]
        }["progress_only_background_evidence"]

        self.assertIn("test_evidence_not_passing", case["finding_codes"])
        self.assertIn("missing_test_evidence", case["finding_codes"])
        evidence = case["plan"]["test_evidence"][0]
        self.assertEqual(evidence["result_status"], "running")

    def test_route_mutation_negative_evidence_points_to_runtime_tests(self) -> None:
        entries = alignment_runner.build_alignment_plan_entries()
        route_entry = next(entry for entry in entries if entry["family"] == "route mutation")
        evidence = {item.evidence_id: item for item in route_entry["plan"].test_evidence}

        for evidence_id in (
            "route_mutation.negative.required_preconditions",
            "route_mutation.negative.old_sibling_proof",
        ):
            with self.subTest(evidence_id=evidence_id):
                item = evidence[evidence_id]
                self.assertTrue(item.path.startswith("tests/router_runtime/route_mutation_"))
                self.assertIn("tests.router_runtime.route_mutation", item.command)

    def test_current_node_trunk_invariant_names_ordinary_and_structural_gates(self) -> None:
        entries = alignment_runner.build_alignment_plan_entries()
        trunk_entry = next(
            entry for entry in entries if entry["family"] == "current-node trunk invariant"
        )
        obligations = {item.obligation_id: item for item in trunk_entry["plan"].obligations}
        evidence = {item.evidence_id: item for item in trunk_entry["plan"].test_evidence}

        ordinary_obligation_id = "current_node_trunk.ordinary_reviewer_worker_postflowguard_reviewer"
        structural_obligation_id = "current_node_trunk.structural_route_flowguard_pm_absorption_reviewer"
        self.assertIn(ordinary_obligation_id, obligations)
        self.assertIn(structural_obligation_id, obligations)
        ordinary_description = obligations[ordinary_obligation_id].description
        structural_description = obligations[structural_obligation_id].description
        for phrase in (
            "ordinary node plan Reviewer -> Worker",
            "post-result FlowGuard -> independent Reviewer",
            "does not require a pre-worker FlowGuard packet",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, ordinary_description)
        for phrase in (
            "Structural route changes require FlowGuard simulation, PM absorption, and Reviewer",
            "route mutation commit",
            "rewrite and rerun FlowGuard",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, structural_description)

        self.assertEqual(
            evidence["current_node_trunk.happy.context_follows_worker_and_reviewer"].test_name,
            "test_node_context_package_follows_worker_postflowguard_and_reviewer_packets",
        )
        self.assertEqual(
            evidence["current_node_trunk.negative.ordinary_node_without_prework"].test_name,
            "test_ordinary_node_acceptance_plan_releases_worker_without_prework_flowguard",
        )
        self.assertEqual(
            evidence["current_node_trunk.negative.structural_flowguard_block"].test_name,
            "test_node_acceptance_redesign_route_flowguard_block_prevents_route_mutation",
        )
        self.assertEqual(
            evidence["current_node_trunk.happy.pm_absorption_required"].test_name,
            "test_node_acceptance_redesign_route_requires_pm_absorption_before_reviewer",
        )

    def test_known_friction_alignment_binds_matrix_and_contract_edges(self) -> None:
        entries = alignment_runner.build_alignment_plan_entries()
        router_entry = next(entry for entry in entries if entry["family"] == "router loop/daemon")
        role_output_entry = next(entry for entry in entries if entry["family"] == "role/output contracts")
        router_obligations = {item.obligation_id for item in router_entry["plan"].obligations}
        role_output_obligations = {item.obligation_id for item in role_output_entry["plan"].obligations}
        router_evidence = {item.evidence_id: item for item in router_entry["plan"].test_evidence}
        role_output_evidence = {item.evidence_id: item for item in role_output_entry["plan"].test_evidence}

        self.assertIn("router_loop.known_friction_regression_gate", router_obligations)
        self.assertIn("router_loop.package_disposition_repair_owned_role_output_replay", router_obligations)
        self.assertIn("router_loop.package_disposition_repair_owned_daemon_replay", router_obligations)
        self.assertIn("router_loop.package_disposition_stale_unowned_role_output_replay", router_obligations)
        self.assertIn("router_loop.package_disposition_stale_unowned_daemon_replay", router_obligations)
        self.assertIn("output_contract.self_check_required_fields", role_output_obligations)
        matrix_item = router_evidence["router_loop.known_friction.happy.matrix"]
        self.assertEqual(matrix_item.path, "tests/test_flowpilot_known_friction_regression_matrix.py")
        self.assertEqual(matrix_item.test_name, "test_known_friction_rows_cover_required_historical_failures")
        known_bad_item = router_evidence["router_loop.known_friction.negative.known_bad"]
        self.assertEqual(known_bad_item.test_name, "test_known_bad_cases_are_rejected")
        replay_item = router_evidence["router_loop.package_disposition_repair_owned_replay.edge.role_output"]
        self.assertEqual(
            replay_item.test_name,
            "test_repair_owned_package_disposition_conflict_replay_is_quarantined_without_daemon_error",
        )
        daemon_item = router_evidence["router_loop.package_disposition_repair_owned_replay.edge.daemon_tick"]
        self.assertEqual(
            daemon_item.test_name,
            "test_daemon_tick_quarantines_repair_owned_package_conflict_without_erasing_wait",
        )
        classifier_item = router_evidence["router_loop.package_disposition_repair_owned_replay.negative.classifier"]
        self.assertEqual(
            classifier_item.test_name,
            "test_pm_package_disposition_conflict_classifier_marks_repair_owned_replay",
        )
        stale_item = router_evidence["router_loop.package_disposition_stale_unowned_replay.edge.role_output"]
        self.assertEqual(
            stale_item.test_name,
            "test_stale_unowned_package_disposition_replay_preserves_canonical_body",
        )
        stale_daemon_item = router_evidence["router_loop.package_disposition_stale_unowned_replay.edge.daemon_tick"]
        self.assertEqual(
            stale_daemon_item.test_name,
            "test_daemon_tick_quarantines_stale_unowned_package_replay_without_reverting_body",
        )
        stale_negative_item = router_evidence["router_loop.package_disposition_stale_unowned_replay.negative.reject_old_body"]
        self.assertEqual(
            stale_negative_item.test_name,
            "test_stale_unowned_package_disposition_replay_preserves_canonical_body",
        )
        stale_daemon_negative_item = router_evidence["router_loop.package_disposition_stale_unowned_replay.negative.no_daemon_error"]
        self.assertEqual(
            stale_daemon_negative_item.test_name,
            "test_daemon_tick_quarantines_stale_unowned_package_replay_without_reverting_body",
        )
        contract_item = role_output_evidence["output_contract.negative.current_node_worker_missing_fields"]
        self.assertEqual(
            contract_item.test_name,
            "test_contract_self_check_metadata_reports_current_node_worker_missing_fields",
        )

    def test_repair_transaction_alignment_covers_current_producer_and_atomicity(self) -> None:
        entries = alignment_runner.build_alignment_plan_entries()
        repair_entry = next(entry for entry in entries if entry["family"] == "repair transactions")
        obligations = {item.obligation_id for item in repair_entry["plan"].obligations}
        evidence = {item.evidence_id: item for item in repair_entry["plan"].test_evidence}

        self.assertIn("repair_transactions.current_repair_requires_concrete_producer", obligations)
        self.assertIn("repair_transactions.no_producer_rejection_then_current_recovery", obligations)
        self.assertIn("repair_transactions.pm_decision_flag_atomicity", obligations)
        self.assertIn("repair_transactions.route_mutation_supersedes_open_repair_blocker", obligations)
        item = evidence["repair_transactions.negative.empty_followup_wait_requires_pm_decision"]
        self.assertEqual(item.test_name, "test_delivered_control_blocker_with_empty_repair_transaction_requires_pm_repair_decision")
        self.assertEqual(item.path, "tests/router_runtime/control_blockers.py")
        edge_item = evidence["repair_transactions.edge.pm_decision_side_effect_atomicity"]
        self.assertEqual(
            edge_item.test_name,
            "test_pm_repair_decision_state_persists_before_followup_wait_is_exposed",
        )
        self.assertEqual(edge_item.path, "tests/router_runtime/control_blockers.py")
        recovery_item = evidence["repair_transactions.happy.current_operation_replay"]
        self.assertEqual(
            recovery_item.test_name,
            "test_operation_replay_repair_transaction_queues_replay_action",
        )
        self.assertEqual(recovery_item.path, "tests/router_runtime/control_blockers.py")
        route_mutation_item = evidence["repair_transactions.edge.route_mutation_supersedes_repair_open_blocker"]
        self.assertEqual(
            route_mutation_item.test_name,
            "test_route_mutation_supersedes_repair_open_blocker_for_quarantined_packet",
        )
        self.assertEqual(route_mutation_item.path, "tests/test_flowpilot_core_runtime.py")

    def test_main_writes_json_only_when_requested(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-alignment-runner-") as tmp_name:
            output_path = Path(tmp_name) / "alignment.json"
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                exit_code = alignment_runner.main(
                    ["--declaration-only", "--json-out", str(output_path)]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["evidence_status"], "not_run")
            self.assertEqual(payload["claim_scope"], "declaration_only")
            self.assertEqual(json.loads(stdout.getvalue()), payload)


if __name__ == "__main__":
    unittest.main()
