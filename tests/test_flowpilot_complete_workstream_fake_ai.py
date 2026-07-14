from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
SIMULATIONS = ROOT / "simulations"
for path in (ASSETS, SIMULATIONS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import flowpilot_complete_workstream_fake_ai_execution as execution  # noqa: E402
import flowpilot_contract_driven_fake_ai as fake_ai  # noqa: E402


class FlowPilotCompleteWorkstreamFakeAITests(unittest.TestCase):
    def test_semantic_profiles_require_the_one_open_packet_constructor(self) -> None:
        execution.assert_public_constructor_is_single_authority()

    def test_every_workstream_profile_traverses_real_ack_open_submit_flowguard_reviewer_and_repair_routing(self) -> None:
        for profile_id in fake_ai.COMPLETE_WORKSTREAM_PROFILE_IDS:
            with self.subTest(profile_id=profile_id):
                receipt = execution.execute_workstream_profile(profile_id)
                self.assertEqual(receipt["execution_status"], "passed")
                self.assertTrue(receipt["generated_from_public_open_packet"])
                self.assertTrue(receipt["proof_backed"])
                self.assertEqual(receipt["subject_result_status"], "mechanically_valid")
                self.assertEqual(receipt["review_result_status"], "accepted")
                self.assertEqual(
                    receipt["review_semantic_decision"],
                    receipt["expected_semantic_decision"],
                )
                self.assertEqual(
                    receipt["pm_repair_routed"],
                    profile_id in fake_ai.WORKSTREAM_REVIEW_BLOCKING_PROFILE_IDS,
                )
                for field in (
                    "subject_contract_fingerprint",
                    "flowguard_contract_fingerprint",
                    "review_contract_fingerprint",
                ):
                    self.assertTrue(receipt[field], (profile_id, field, receipt))

    def test_resource_profiles_use_real_current_family_checklists_and_submit_paths(self) -> None:
        for profile_id in fake_ai.RESOURCE_DISCOVERY_PROFILE_IDS:
            with self.subTest(profile_id=profile_id):
                receipt = execution.execute_resource_profile(profile_id)
                self.assertEqual(receipt["execution_status"], "passed")
                self.assertTrue(receipt["generated_from_public_open_packet"])
                self.assertTrue(receipt["contract_fingerprint"])
                self.assertEqual(
                    receipt["result_status"],
                    receipt["expected_result_status"],
                )
                if profile_id == "ordinary_material_evidence_work":
                    self.assertEqual(receipt["contract_family_id"], "task.node")
                if profile_id == "forbidden_old_discovery_fields":
                    self.assertEqual(receipt["result_status"], "mechanical_contract_blocked")


if __name__ == "__main__":
    unittest.main()
