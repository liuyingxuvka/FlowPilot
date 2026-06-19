from __future__ import annotations

import importlib
import unittest


runner = importlib.import_module("simulations.run_flowpilot_stop_host_orphan_recovery_checks")


class FlowPilotStopProgressOrphanRecoveryModelTests(unittest.TestCase):
    def test_flowguard_model_is_green_and_catches_known_hazards(self) -> None:
        result = runner.run_checks()

        self.assertTrue(result["ok"], result)
        hazards = result["hazard_detection"]["hazards"]
        for expected in (
            "new_work_after_terminal_allowed",
            "terminal_without_ledger_status",
            "stale_progress_counted_as_fresh_evidence",
            "completed_without_result_treated_terminal",
            "orphan_evidence_auto_accepted",
            "orphan_evidence_ignored",
        ):
            self.assertIn(expected, hazards)


if __name__ == "__main__":
    unittest.main()
