from __future__ import annotations

import sys
import unittest
from pathlib import Path

from flowguard import (
    review_behavior_commitment_ledger,
    review_field_lifecycle,
    review_primary_path_authority,
)


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))

import flowpilot_053_ppa_maintenance_model as model  # noqa: E402
import run_flowpilot_053_ppa_maintenance_checks as runner  # noqa: E402


class FlowPilot053PPAMaintenanceTests(unittest.TestCase):
    def test_runner_consumes_real_flowguard_053_routes(self) -> None:
        report = runner.build_report()

        self.assertTrue(report["ok"], report)
        self.assertTrue(report["gates"]["ppa"])
        self.assertTrue(report["gates"]["behavior_commitments"])
        self.assertTrue(report["gates"]["field_lifecycle"])
        self.assertTrue(report["gates"]["risk_evidence"])
        self.assertTrue(report["gates"]["pm_visible_summary_existing_runner"])
        self.assertTrue(report["gates"]["negative_cases"])

        ppa_report = report["primary_path_authority"]["report"]
        bcl_report = report["behavior_commitment_ledger"]["report"]
        field_report = report["field_lifecycle"]["report"]
        self.assertEqual(ppa_report["decision"], "primary_path_authority_green")
        self.assertEqual(bcl_report["decision"], "behavior_commitment_coverage_green")
        self.assertEqual(field_report["decision"], "field_lifecycle_full")
        self.assertEqual(
            set(report["coverage"]["primary_path_intents"]),
            {
                "accept_current_packet_result",
                "reject_or_reissue_current_packet_result",
                "open_authorized_result_material",
            },
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
        self.assertEqual(set(good.path_sensitive_commitment_ids), set(model.COMMITMENT_IDS))

        missing_ppa = review_behavior_commitment_ledger(model.build_broken_missing_ppa_ledger())
        missing_ppa_codes = {finding.code for finding in missing_ppa.findings}
        self.assertFalse(missing_ppa.ok)
        self.assertIn("commitment_missing_primary_path_authority", missing_ppa_codes)

        missing_primary_ids = review_behavior_commitment_ledger(model.build_broken_ppa_missing_primary_path_ids_ledger())
        missing_primary_ids_codes = {finding.code for finding in missing_primary_ids.findings}
        self.assertFalse(missing_primary_ids.ok)
        self.assertIn("commitment_primary_path_ids_missing", missing_primary_ids_codes)

        stale = review_behavior_commitment_ledger(model.build_broken_stale_evidence_ledger())
        stale_codes = {finding.code for finding in stale.findings}
        self.assertFalse(stale.ok)
        self.assertIn("commitment_current_evidence_missing", stale_codes)

    def test_field_lifecycle_covers_existing_fields_without_new_contract_fields(self) -> None:
        field_report = review_field_lifecycle(model.build_field_lifecycle_plan())
        self.assertTrue(field_report.ok, field_report.to_dict())
        self.assertEqual(field_report.confidence, "full")
        projected = {projection.field_id for projection in field_report.projections}
        self.assertIn("packet_result.body.pm_visible_summary", projected)
        self.assertIn("pm_packet.body.recent_role_report_summary", projected)
        self.assertIn("packet.envelope.authorized_result_reads[]", projected)

        broken = review_field_lifecycle(model.build_broken_missing_field_projection_plan())
        broken_codes = {finding.code for finding in broken.findings}
        self.assertFalse(broken.ok)
        self.assertIn("behavior_field_projection_missing", broken_codes)

    def test_source_guard_keeps_runtime_mechanical_and_summaries_navigation_only(self) -> None:
        report = runner.build_report()
        source_guard = report["source_guard"]

        self.assertTrue(source_guard["ok"], source_guard)
        self.assertTrue(source_guard["checks"]["runtime_uses_missing_summary_as_mechanical_failure"])
        self.assertTrue(source_guard["checks"]["prompt_says_runtime_does_not_synthesize"])
        self.assertTrue(source_guard["checks"]["prompt_says_summaries_not_substitutes"])


if __name__ == "__main__":
    unittest.main()
