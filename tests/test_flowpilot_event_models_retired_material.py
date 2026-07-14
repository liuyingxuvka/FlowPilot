from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIMULATIONS = ROOT / "simulations"
if str(SIMULATIONS) not in sys.path:
    sys.path.insert(0, str(SIMULATIONS))

import flowpilot_event_capability_registry_model as capability_model  # noqa: E402
import flowpilot_event_contract_model as contract_model  # noqa: E402
import flowpilot_event_idempotency_model as idempotency_model  # noqa: E402
import run_flowpilot_event_capability_registry_checks as capability_checks  # noqa: E402
import run_flowpilot_event_contract_checks as contract_checks  # noqa: E402
import run_flowpilot_event_idempotency_checks as idempotency_checks  # noqa: E402


class RetiredMaterialEventModelTests(unittest.TestCase):
    def test_all_three_models_share_the_complete_retired_event_set(self) -> None:
        self.assertEqual(
            contract_model.RETIRED_MATERIAL_EXTERNAL_EVENTS,
            capability_model.RETIRED_MATERIAL_EXTERNAL_EVENTS,
        )
        self.assertEqual(
            contract_model.RETIRED_MATERIAL_EXTERNAL_EVENTS,
            idempotency_model.RETIRED_MATERIAL_EXTERNAL_EVENTS,
        )
        self.assertEqual(len(contract_model.RETIRED_MATERIAL_EXTERNAL_EVENTS), 12)

    def test_retired_events_are_negative_only_in_contract_and_capability_models(self) -> None:
        retired = contract_model.RETIRED_MATERIAL_EXTERNAL_EVENTS
        self.assertTrue(retired.isdisjoint(contract_model.REGISTERED_EXTERNAL_EVENTS))
        self.assertTrue(retired.isdisjoint(capability_model.EVENT_CAPABILITIES))

        for scenario in contract_model.RETIRED_MATERIAL_EVENT_WAIT_SCENARIOS:
            with self.subTest(model="contract", scenario=scenario):
                failures = contract_model.event_contract_failures(
                    contract_model._scenario_state(scenario)  # type: ignore[attr-defined]
                )
                self.assertIn("persisted role wait contains unregistered external event", failures)

        for scenario in capability_model.RETIRED_MATERIAL_EVENT_CAPABILITY_SCENARIOS:
            with self.subTest(model="capability", scenario=scenario):
                failures = capability_model.event_capability_failures(
                    capability_model._scenario_state(scenario)  # type: ignore[attr-defined]
                )
                self.assertIn("event capability row is missing", failures)

    def test_positive_scenarios_use_current_research_node_or_role_work_events(self) -> None:
        current_events = {
            "worker_research_report_returned",
            "reviewer_passes_research_direct_source_check",
            "reviewer_blocks_research_direct_source_check",
            "worker_current_node_result_returned",
            "role_work_result_returned",
            "pm_records_research_result_disposition",
        }
        contract_positive_events = {
            event
            for scenario in contract_model.VALID_SCENARIOS
            for event in contract_model._scenario_state(scenario).allowed_external_events  # type: ignore[attr-defined]
        }
        capability_positive_events = {
            event
            for scenario in capability_model.VALID_SCENARIOS
            for event in capability_model._scenario_state(scenario).wait_events  # type: ignore[attr-defined]
        }
        idempotency_scenario_events = {
            idempotency_model._selected_state(scenario).event_name  # type: ignore[attr-defined]
            for scenario in idempotency_model.SCENARIOS
        }
        self.assertTrue(
            current_events
            & contract_positive_events,
            msg="contract model must retain a current research/current-node wait",
        )
        self.assertTrue(
            current_events
            & capability_positive_events,
            msg="capability model must retain a current research/current-node/role-work wait",
        )
        self.assertIn(idempotency_model.PACKAGE_DISPOSITION_EVENT, current_events)
        self.assertIn(idempotency_model.PACKAGE_DISPOSITION_EVENT, idempotency_scenario_events)
        self.assertTrue(
            contract_model.RETIRED_MATERIAL_EXTERNAL_EVENTS.isdisjoint(idempotency_scenario_events)
        )

    def test_runners_prove_current_catalog_and_retired_event_absence(self) -> None:
        contract = contract_checks.run_checks()
        capability = capability_checks.run_checks()
        idempotency = idempotency_checks.run_checks()

        self.assertTrue(contract["ok"], contract)
        self.assertTrue(capability["ok"], capability)
        self.assertTrue(idempotency["ok"], idempotency)
        self.assertEqual(contract["source_audit"]["retired_material_runtime_catalog_residue"], [])
        self.assertEqual(capability["source_audit"]["retired_material_model_capability_residue"], [])
        self.assertEqual(idempotency["source_audit"]["retired_material_scoped_policy_residue"], [])


if __name__ == "__main__":
    unittest.main()
