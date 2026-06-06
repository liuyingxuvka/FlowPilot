from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))

import run_startup_pm_review_checks as runner  # noqa: E402
import startup_pm_review_model as model  # noqa: E402


class FlowPilotStartupPmReviewModelTests(unittest.TestCase):
    def test_startup_pm_review_model_rejects_single_agent_continuity_gate_opening(self) -> None:
        state = model._ready_base(
            live_background_agents_active=0,
            background_agents_current_task_ready=False,
            background_agents_opened_after_startup_authorization=False,
            background_agents_opened_after_route_allocation=False,
            historical_agent_ids_compared=False,
            legacy_single_agent_continuity_authorized=True,
            pm_start_gate_decision="open",
            work_beyond_startup_allowed=True,
        )

        failures = model.invariant_failures(state)

        self.assertIn(
            "legacy single-agent continuity was authorized instead of mandatory background collaboration",
            failures,
        )
        self.assertIn(
            "PM started first-round work without current authorization, background collaboration, clean Runtime entry, and independent PM audit",
            failures,
        )

    def test_startup_pm_review_model_rejects_heartbeat_and_manual_downgrades(self) -> None:
        heartbeat = model._ready_base(legacy_heartbeat_created=True)
        manual = model._ready_base(legacy_manual_resume_downgrade_authorized=True)

        self.assertIn(
            "legacy heartbeat continuation was created in current startup flow",
            model.invariant_failures(heartbeat),
        )
        self.assertIn(
            "legacy manual-resume downgrade was authorized instead of blocking or repairing startup",
            model.invariant_failures(manual),
        )

    def test_startup_pm_review_runner_passes_with_legacy_paths_as_hazards_only(self) -> None:
        safe = runner.explore_safe_graph()
        hazards = runner.check_hazards()

        self.assertTrue(safe["ok"], safe)
        self.assertTrue(hazards["ok"], hazards)


if __name__ == "__main__":
    unittest.main()

