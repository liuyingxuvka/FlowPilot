from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from flowguard import (
    behavior_commitment_ledger_fingerprint,
    load_behavior_commitment_ledger,
    review_behavior_commitment_ledger,
    review_field_lifecycle,
    review_primary_path_authority,
    review_risk_evidence_ledger,
)


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))

import flowpilot_053_ppa_maintenance_model as model  # noqa: E402
import run_flowpilot_053_ppa_maintenance_checks as runner  # noqa: E402


class FlowPilot053PPAMaintenanceTests(unittest.TestCase):
    @staticmethod
    def _current_evidence(summary: str) -> dict[str, object]:
        return {"ok": True, "summary": summary}

    def test_runner_consumes_real_flowguard_053_routes(self) -> None:
        report = runner.build_report(
            formal_ai_evidence=self._current_evidence("current formal AI execution"),
            model_test_alignment_evidence=self._current_evidence("current strict MTA"),
        )

        self.assertTrue(report["ok"], report)
        self.assertTrue(report["gates"]["ppa"])
        self.assertTrue(report["gates"]["behavior_commitments"])
        self.assertTrue(report["gates"]["field_lifecycle"])
        self.assertTrue(report["gates"]["risk_evidence"])
        self.assertTrue(report["gates"]["pm_visible_summary_existing_runner"])
        self.assertTrue(report["gates"]["negative_cases"])
        self.assertTrue(report["gates"]["formal_ai_execution_evidence"])
        self.assertTrue(report["gates"]["model_test_alignment_evidence"])

        ppa_report = report["primary_path_authority"]["report"]
        bcl_report = report["behavior_commitment_ledger"]["report"]
        field_report = report["field_lifecycle"]["report"]
        self.assertEqual(ppa_report["decision"], "primary_path_authority_green")
        self.assertEqual(bcl_report["decision"], "behavior_commitment_coverage_green")
        self.assertEqual(field_report["decision"], "field_lifecycle_full")
        self.assertEqual(
            set(report["coverage"]["primary_path_intents"]),
            set(model.PRIMARY_PATH_INTENTS),
        )
        self.assertTrue(
            {
                "commit.current_handoff_checklist_single_authority",
                "commit.fake_ai_coverage_is_execution_backed",
                "commit.testmesh_pass_requires_current_proof",
                "commit.repair_reissue_no_fallback",
                "commit.substantive_roles_complete_bounded_workstreams",
                "commit.controller_uses_runtime_foreground_ledger_only",
                "commit.local_capability_inventory_precedes_pm_selection",
                "commit.material_work_uses_ordinary_role_packages",
                "commit.reviewer_audits_plan_completion_and_pm_disposition",
                "commit.role_local_flowguard_cannot_self_approve",
                "commit.material_map_is_optional_navigation_only",
                "commit.model_test_alignment_uses_current_runtime_path_evidence",
            }.issubset(set(report["coverage"]["commitment_ids"]))
        )
        self.assertTrue(
            {
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
            }.issubset(set(report["coverage"]["field_ids"]))
        )

    def test_proof_commands_reject_machine_specific_absolute_paths(self) -> None:
        portable, portable_ok = model._portable_proof_command(
            "python simulations/run_check.py"
        )
        windows, windows_ok = model._portable_proof_command(
            "C:" + "\\Users\\example\\python.exe simulations/run_check.py"
        )
        posix, posix_ok = model._portable_proof_command(
            "/home/example/.venv/bin/python simulations/run_check.py"
        )

        self.assertTrue(portable_ok)
        self.assertEqual(portable, "python simulations/run_check.py")
        self.assertFalse(windows_ok)
        self.assertFalse(posix_ok)
        self.assertEqual(windows, "<nonportable-command-rejected>")
        self.assertEqual(posix, "<nonportable-command-rejected>")

    def test_evidence_report_paths_are_repository_relative(self) -> None:
        formal = runner._formal_ai_execution_evidence_report()
        alignment = runner._model_test_alignment_evidence_report()

        self.assertEqual(
            formal["path"],
            "simulations/flowpilot_ai_response_execution_closure_results.json",
        )
        self.assertEqual(
            alignment["path"],
            "simulations/flowpilot_model_test_alignment_results.json",
        )

    def test_primary_path_authority_rejects_old_field_and_duplicate_primary_paths(self) -> None:
        good = review_primary_path_authority(model.build_primary_path_plan())
        self.assertTrue(good.ok, good.to_dict())
        self.assertEqual(good.decision, "primary_path_authority_green")

        old_field = review_primary_path_authority(model.build_broken_old_field_fallback_plan())
        old_field_codes = {finding.code for finding in old_field.findings}
        self.assertFalse(old_field.ok)
        self.assertIn("primary_failure_masked_by_fallback_success", old_field_codes)
        self.assertIn("old_field_or_backup_cache_masks_primary_failure", old_field_codes)

        duplicate = review_primary_path_authority(model.build_broken_duplicate_primary_authority_plan())
        duplicate_codes = {finding.code for finding in duplicate.findings}
        self.assertFalse(duplicate.ok)
        self.assertIn("duplicate_primary_runtime_authority", duplicate_codes)

        missing_coverage = review_primary_path_authority(model.build_broken_missing_coverage_plan())
        missing_coverage_codes = {finding.code for finding in missing_coverage.findings}
        self.assertFalse(missing_coverage.ok)
        self.assertIn("primary_path_cartesian_coverage_missing", missing_coverage_codes)
        self.assertIn("primary_path_coverage_shards_missing", missing_coverage_codes)
        self.assertIn("primary_path_risk_gate_missing", missing_coverage_codes)

    def test_behavior_commitment_ledger_requires_ppa_and_current_evidence(self) -> None:
        ppa = review_primary_path_authority(model.build_primary_path_plan())
        good = review_behavior_commitment_ledger(model.build_behavior_commitment_ledger(ppa))
        self.assertTrue(good.ok, good.to_dict())
        self.assertEqual(set(good.covered_commitment_ids), set(model.COMMITMENT_IDS))
        self.assertEqual(
            set(good.path_sensitive_commitment_ids),
            set(model.PATH_SENSITIVE_COMMITMENT_IDS),
        )

        missing_ppa = review_behavior_commitment_ledger(model.build_broken_missing_ppa_ledger())
        missing_ppa_codes = {finding.code for finding in missing_ppa.findings}
        self.assertFalse(missing_ppa.ok)
        self.assertIn("commitment_missing_primary_path_authority", missing_ppa_codes)

        missing_primary_ids = review_behavior_commitment_ledger(model.build_broken_ppa_missing_primary_path_ids_ledger())
        missing_primary_ids_codes = {finding.code for finding in missing_primary_ids.findings}
        self.assertFalse(missing_primary_ids.ok)
        self.assertIn("commitment_primary_path_id_missing", missing_primary_ids_codes)

        stale = review_behavior_commitment_ledger(model.build_broken_stale_evidence_ledger())
        stale_codes = {finding.code for finding in stale.findings}
        self.assertFalse(stale.ok)
        self.assertIn("commitment_current_evidence_missing", stale_codes)

    def test_behavior_commitment_inventory_has_one_canonical_json_authority(self) -> None:
        ledger = load_behavior_commitment_ledger(model.LEDGER_PATH)
        reloaded = model.build_behavior_commitment_ledger()
        source = (model.LEDGER_PATH.parent / "model.py").read_text(
            encoding="utf-8"
        )

        self.assertEqual(len(ledger.commitments), 17)
        self.assertEqual(
            behavior_commitment_ledger_fingerprint(ledger),
            behavior_commitment_ledger_fingerprint(reloaded),
        )
        self.assertEqual(
            ledger.metadata["canonical_authority"],
            ".flowguard/behavior_commitment_ledger/ledger.json",
        )
        self.assertEqual(ledger.metadata["python_adapter_role"], "thin_loader_only")
        self.assertNotIn("BehaviorCommitment(", source)
        self.assertNotIn("commit.result_submission_current_contract_only\"", source)

    def test_behavior_commitment_inventory_uses_current_singular_path_authority_contract(self) -> None:
        payload = json.loads(model.LEDGER_PATH.read_text(encoding="utf-8"))
        commitments = payload["ledger"]["commitments"]
        forbidden = {
            "legacy_primary_path_ids",
            "primary_path_ids",
            "legacy_plural_migrated",
            "primary_path_migration_ambiguous",
        }

        self.assertEqual(len(commitments), 17)
        for commitment in commitments:
            authority = commitment["path_authority"]
            self.assertFalse(
                forbidden.intersection(authority),
                commitment["commitment_id"],
            )
            self.assertIn("primary_path_id", authority)
            if authority["path_sensitive"]:
                self.assertTrue(
                    authority["primary_path_id"],
                    commitment["commitment_id"],
                )

    def test_unified_late_defect_repair_has_one_commitment_and_primary_path(self) -> None:
        payload = json.loads(model.LEDGER_PATH.read_text(encoding="utf-8"))[
            "ledger"
        ]
        intent_id = (
            "intent:flowpilot.repair-late-defect-through-current-shared-engine"
        )
        commitments = [
            row
            for row in payload["commitments"]
            if row["business_intent_id"] == intent_id
        ]
        surfaces = [
            row
            for row in payload["source_surfaces"]
            if intent_id in row["business_intent_ids"]
        ]

        self.assertEqual(len(commitments), 1)
        commitment = commitments[0]
        self.assertEqual(
            commitment["path_authority"]["primary_path_id"],
            "path.runtime.unified-late-defect-repair",
        )
        self.assertEqual(len(surfaces), 5)
        self.assertEqual(
            len(
                [
                    surface
                    for surface in surfaces
                    if not surface["delegates_to_primary_path"]
                ]
            ),
            1,
        )
        self.assertEqual(
            {
                surface["metadata"].get("repair_trigger_origin")
                for surface in surfaces
                if surface["delegates_to_primary_path"]
            },
            {
                "pm_historical_defect",
                "reviewer_or_system_failure",
                "parent_backward_replay_or_scoped_decision",
                "terminal_backward_replay",
            },
        )
        self.assertNotIn(
            "commit.dynamic_pm_repair_owns_active_acceptance_items",
            {row["commitment_id"] for row in payload["commitments"]},
        )

    def test_field_lifecycle_covers_existing_fields_without_new_contract_fields(self) -> None:
        field_report = review_field_lifecycle(model.build_field_lifecycle_plan())
        self.assertTrue(field_report.ok, field_report.to_dict())
        self.assertEqual(field_report.confidence, "full")
        projected = {projection.field_id for projection in field_report.projections}
        self.assertIn("packet_result.body.pm_visible_summary", projected)
        self.assertIn("pm_packet.body.recent_role_report_summary", projected)
        self.assertIn("packet.envelope.authorized_result_reads[]", projected)
        self.assertIn("task.discovery.packet.body.runtime_local_capability_inventory", projected)
        self.assertIn("preplanning.discovery.candidate_skill_inventory", projected)
        self.assertIn("packet_result.contract_self_check.workstream_plan_and_completion", projected)

        rows = {row.field_id: row for row in model.build_field_lifecycle_plan().fields}
        conditional_body = rows["packet.body.conditional_mechanical_fields"]
        private_helper = rows["fake_ai.private_helper_result_shapes"]
        self.assertEqual(conditional_body.lifecycle, "old")
        self.assertEqual(conditional_body.disposition, "blocked")
        self.assertFalse(conditional_body.reader_ids)
        self.assertFalse(conditional_body.writer_ids)
        self.assertEqual(private_helper.lifecycle, "old")
        self.assertEqual(private_helper.disposition, "deleted")
        self.assertFalse(private_helper.reader_ids)
        self.assertFalse(private_helper.writer_ids)

        for field_id in (
            "preplanning.discovery.material_sources",
            "preplanning.discovery.material_sufficiency",
            "preplanning.discovery.material_current",
        ):
            retired_material = rows[field_id]
            self.assertEqual(retired_material.lifecycle, "old")
            self.assertEqual(retired_material.disposition, "blocked")
            self.assertFalse(retired_material.reader_ids)
            self.assertFalse(retired_material.writer_ids)

        broken = review_field_lifecycle(model.build_broken_missing_field_projection_plan())
        broken_codes = {finding.code for finding in broken.findings}
        self.assertFalse(broken.ok)
        self.assertIn("behavior_field_projection_missing", broken_codes)

    def test_source_guard_keeps_runtime_mechanical_and_summaries_navigation_only(self) -> None:
        report = runner.build_report(
            formal_ai_evidence=self._current_evidence("current formal AI execution"),
            model_test_alignment_evidence=self._current_evidence("current strict MTA"),
        )
        source_guard = report["source_guard"]

        self.assertTrue(source_guard["ok"], source_guard)
        self.assertTrue(source_guard["checks"]["runtime_uses_missing_summary_as_mechanical_failure"])
        self.assertTrue(source_guard["checks"]["prompt_says_runtime_does_not_synthesize"])
        self.assertTrue(source_guard["checks"]["prompt_says_summaries_not_substitutes"])

    def test_risk_ledger_rejects_missing_current_execution_handoffs(self) -> None:
        ppa = review_primary_path_authority(model.build_primary_path_plan())
        bcl = review_behavior_commitment_ledger(model.build_behavior_commitment_ledger(ppa))
        field = review_field_lifecycle(model.build_field_lifecycle_plan())
        plan = model.build_risk_evidence_ledger_plan(
            ppa,
            bcl,
            field,
            formal_ai_evidence={"ok": False, "summary": "formal result missing"},
            model_test_alignment_evidence={"ok": False, "summary": "MTA result stale"},
        )
        report = review_risk_evidence_ledger(plan)

        self.assertFalse(report.ok, report.to_dict())
        proofs = {proof.evidence_id: proof for proof in plan.proof_evidence}
        self.assertFalse(proofs["evidence.formal_ai_execution_closure"].current)
        self.assertFalse(proofs["evidence.model_test_alignment"].current)


if __name__ == "__main__":
    unittest.main()
