from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIMULATIONS = ROOT / "simulations"
if str(SIMULATIONS) not in sys.path:
    sys.path.insert(0, str(SIMULATIONS))

budget = importlib.import_module("run_flowpilot_milestone_renewal_budget_checks")


class FlowPilotMilestoneRenewalBudgetTests(unittest.TestCase):
    def test_large_gate_keeps_authorized_result_reads_bounded(self) -> None:
        case = budget._build_case(100, 99)

        self.assertEqual(len(case["authorized_read_ids"]), 4)
        self.assertEqual(
            case["authorized_read_ids"][-1],
            "result-milestone-audit-098",
        )
        self.assertNotIn(
            "contract_hash",
            case["pm_shape"]["milestone_audit"],
        )
        self.assertTrue(
            all(
                "evidence_refs" not in row
                for row in case["pm_shape"]["milestone_audit"]["completed"]
            )
        )

    def test_budget_uses_four_role_submissions_and_two_local_steps(self) -> None:
        row = budget._measure_once(10, 5)
        submissions = budget._role_submissions(
            budget._build_case(10, 5)["pm_shape"],
            5,
        )

        self.assertEqual(len(submissions), 4)
        self.assertEqual(
            [item["role"] for item in submissions],
            ["pm", "flowguard", "pm_absorption", "reviewer"],
        )
        self.assertEqual(row["authorized_read_count"], 4)
        self.assertGreater(row["packet_context_bytes"], 0)
        self.assertGreater(row["role_submission_bytes"], 0)

    def test_reduced_trial_budget_stays_within_declared_bounds(self) -> None:
        original_sizes = budget.ROUTE_SIZES
        original_trials = budget.TRIALS_PER_GATE
        try:
            budget.ROUTE_SIZES = (10, 50, 100)
            budget.TRIALS_PER_GATE = 2
            result = budget.run_checks()
        finally:
            budget.ROUTE_SIZES = original_sizes
            budget.TRIALS_PER_GATE = original_trials

        self.assertTrue(result["ok"])
        self.assertTrue(all(result["checks"].values()))
        self.assertLessEqual(
            result["observed_10_to_100_transport_growth_ratio"],
            budget.MAX_10_TO_100_PAYLOAD_GROWTH,
        )


if __name__ == "__main__":
    unittest.main()
