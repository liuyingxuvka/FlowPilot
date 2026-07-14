from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIMULATIONS = ROOT / "simulations"
sys.path.insert(0, str(SIMULATIONS))

import flowpilot_event_envelope_transfer_model as model  # noqa: E402
import run_flowpilot_event_envelope_transfer_checks as runner  # noqa: E402


class EventEnvelopeTransferCurrentContractTests(unittest.TestCase):
    def test_model_uses_current_node_envelopes_instead_of_retired_material_events(self) -> None:
        source = (SIMULATIONS / "flowpilot_event_envelope_transfer_model.py").read_text(encoding="utf-8")
        self.assertNotIn("pm_issues_material_and_capability_scan_packets", source)
        self.assertNotIn("VALID_MATERIAL", source)
        self.assertIn("pm_registers_current_node_packet", source)
        self.assertIn(model.VALID_CURRENT_NODE_REF, model.ACCEPTED_SCENARIOS)

    def test_real_flowguard_runner_is_green(self) -> None:
        report = runner.run_checks()
        self.assertTrue(report["ok"], report)
        scenarios = report["scenario_checks"]["scenarios"]
        self.assertTrue(scenarios["current_node_full_payload_and_ref_equivalent"]["ok"])
        self.assertTrue(scenarios["known_manual_reconstruction_failures_rejected"]["ok"])


if __name__ == "__main__":
    unittest.main()
