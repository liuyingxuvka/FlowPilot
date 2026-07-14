from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
sys.path.insert(0, str(ASSETS))

import flowpilot_router as router  # noqa: E402
import flowpilot_router_event_dispatcher as event_dispatcher  # noqa: E402
import flowpilot_router_protocol_card_metadata as card_metadata  # noqa: E402
import flowpilot_router_protocol_external_event_registry as event_registry  # noqa: E402


RETIRED_MATERIAL_EXTERNAL_EVENTS = {
    "pm_issues_material_and_capability_scan_packets",
    "router_direct_material_scan_dispatch_recheck_passed",
    "router_direct_material_scan_dispatch_recheck_blocked",
    "router_protocol_blocker_material_scan_dispatch_recheck",
    "worker_scan_packet_bodies_delivered_after_dispatch",
    "worker_scan_results_returned",
    "pm_records_material_scan_result_disposition",
    "reviewer_reports_material_sufficient",
    "reviewer_reports_material_insufficient",
    "pm_accepts_reviewed_material",
    "pm_requests_research_after_material_insufficient",
    "pm_writes_material_understanding",
}

ORDINARY_RESEARCH_EXTERNAL_EVENTS = {
    "pm_writes_research_package",
    "research_capability_decision_recorded",
    "worker_research_report_returned",
    "pm_records_research_result_disposition",
    "reviewer_passes_research_direct_source_check",
    "reviewer_blocks_research_direct_source_check",
    "pm_absorbs_reviewed_research",
}

ORDINARY_PM_ROLE_WORK_EXTERNAL_EVENTS = {
    "pm_registers_role_work_request",
    "role_work_result_returned",
    "pm_records_role_work_result_decision",
}


class RetiredMaterialExternalEventTests(unittest.TestCase):
    def _write_minimal_current_run(self, project_root: Path) -> Path:
        run_id = "run-retired-material-events"
        run_root = project_root / ".flowpilot" / "runs" / run_id
        run_root_rel = router.project_relative(project_root, run_root)
        run_state = router.new_run_state(run_id, run_root_rel, controller_core_loaded=True)
        run_state["status"] = "running"
        bootstrap = router.new_bootstrap_state(run_id=run_id, run_root_rel=run_root_rel)
        bootstrap["status"] = "running"
        router.write_json(router.run_state_path(run_root), run_state)
        router.write_json(router.run_bootstrap_state_path(run_root), bootstrap)
        router.write_json(
            project_root / ".flowpilot" / "current.json",
            {
                "schema_version": "flowpilot.current.v1",
                "run_id": run_id,
                "run_root": run_root_rel,
                "startup_bootstrap_path": router.project_relative(
                    project_root,
                    router.run_bootstrap_state_path(run_root),
                ),
                "status": "running",
                "updated_at": router.utc_now(),
            },
        )
        return run_root

    def test_retired_material_events_are_absent_from_every_external_event_catalog(self) -> None:
        self.assertTrue(RETIRED_MATERIAL_EXTERNAL_EVENTS.isdisjoint(event_registry.EXTERNAL_EVENTS))
        for phase in event_registry.EXTERNAL_EVENT_PHASES:
            self.assertTrue(
                RETIRED_MATERIAL_EXTERNAL_EVENTS.isdisjoint(phase.events),
                msg=f"retired material event remains in {phase.phase} phase",
            )
        self.assertTrue(
            RETIRED_MATERIAL_EXTERNAL_EVENTS.isdisjoint(
                event_dispatcher._DIRECT_PACKAGE_DISPOSITION_DOMAIN_COMMITS
            )
        )

    def test_record_external_event_mechanically_rejects_every_retired_material_event(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-retired-material-events-") as tmp:
            project_root = Path(tmp)
            run_root = self._write_minimal_current_run(project_root)
            before = router.read_json(router.run_state_path(run_root))
            for event in sorted(RETIRED_MATERIAL_EXTERNAL_EVENTS):
                with self.subTest(event=event):
                    with self.assertRaisesRegex(
                        router.RouterError,
                        rf"unknown external event: {re.escape(event)}",
                    ):
                        router.record_external_event(project_root, event, {})
            self.assertEqual(router.read_json(router.run_state_path(run_root)), before)

    def test_ordinary_research_and_pm_role_work_events_remain_registered(self) -> None:
        expected = ORDINARY_RESEARCH_EXTERNAL_EVENTS | ORDINARY_PM_ROLE_WORK_EXTERNAL_EVENTS
        self.assertTrue(expected.issubset(event_registry.EXTERNAL_EVENTS))
        self.assertEqual(
            event_dispatcher._DIRECT_PACKAGE_DISPOSITION_DOMAIN_COMMITS[
                "pm_records_research_result_disposition"
            ]["batch_kind"],
            "research",
        )

    def test_retired_material_cards_and_source_requirements_are_not_metadata(self) -> None:
        self.assertNotIn("pm.material_scan", card_metadata.CARD_PHASE_BY_ID)
        self.assertNotIn("reviewer.material_sufficiency", card_metadata.CARD_PHASE_BY_ID)
        product_sources = card_metadata.CARD_REQUIRED_SOURCE_PATHS["pm.product_architecture"]
        self.assertNotIn("pm_material_understanding", product_sources)
        self.assertNotIn("pm_material_understanding_payload", product_sources)


if __name__ == "__main__":
    unittest.main()
