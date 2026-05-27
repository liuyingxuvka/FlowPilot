from __future__ import annotations

import unittest

from simulations import flowpilot_role_recovery_liveness_model as model
from simulations import run_flowpilot_role_recovery_liveness_checks as checks


class FlowPilotRoleRecoveryLivenessModelTests(unittest.TestCase):
    def test_known_bad_liveness_hazards_are_detected(self) -> None:
        report = checks._hazard_report()

        self.assertTrue(report["ok"])
        self.assertEqual(
            {
                "stale_report_marked_safe",
                "unknown_liveness_marked_safe",
                "replacement_intent_only_marked_safe",
                "daemon_error_without_diagnostics_marked_safe",
                "current_report_overblocked",
            },
            set(report["hazards"]),
        )

    def test_flowguard_role_recovery_liveness_checks_pass(self) -> None:
        report = checks.run_checks()

        self.assertTrue(report["ok"], report)
        self.assertEqual(model.MODEL_ID, report["model_id"])
        self.assertIn("valid_current_report", report["safe_scenarios"])
        self.assertIn("stale_report_reclaim", report["risk_scenarios"])


if __name__ == "__main__":
    unittest.main()
