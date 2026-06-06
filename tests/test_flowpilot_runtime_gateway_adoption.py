from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
SIMULATIONS = ROOT / "simulations"
sys.path.insert(0, str(ASSETS))
sys.path.insert(0, str(SIMULATIONS))

import flowpilot_router_io_json  # noqa: E402
import flowpilot_runtime_gateway as runtime_gateway  # noqa: E402
import flowpilot_runtime_gateway_adoption  # noqa: E402
import packet_runtime_schema  # noqa: E402
import role_output_runtime_schema_io  # noqa: E402


class FlowPilotRuntimeGatewayAdoptionTests(unittest.TestCase):
    def test_gateway_classifies_and_blocks_wrong_owner_for_critical_state(self) -> None:
        current = Path(".flowpilot/current.json")
        target = runtime_gateway.classify_runtime_state_surface(current)

        self.assertTrue(target.critical)
        self.assertEqual(target.surface_id, "flowpilot_current_pointer")
        runtime_gateway.assert_runtime_gateway_write(
            current,
            runtime_gateway.GATEWAY_ROUTER_JSON,
            operation="test_router_pointer_write",
        )
        with self.assertRaises(runtime_gateway.RuntimeGatewayError):
            runtime_gateway.assert_runtime_gateway_write(
                current,
                runtime_gateway.GATEWAY_PACKET_RUNTIME,
                operation="test_wrong_owner",
            )

    def test_gateway_keeps_nested_runtime_indexes_and_role_outputs_with_their_owners(self) -> None:
        break_glass_index = Path(".flowpilot/runs/run-test/controller_break_glass/index.json")
        role_output_body = Path(".flowpilot/runs/run-test/continuation/pm_resume_runtime_body.json")
        gate_output_body = Path(".flowpilot/runs/run-test/gate_decisions/gate_decision-1.json")
        card_read_receipt = Path(
            ".flowpilot/runs/run-test/runtime_receipts/card_reads/"
            "pm_parent_segment_decision-delivery-001-attempt-001.receipt.json"
        )
        card_ack = Path(
            ".flowpilot/runs/run-test/mailbox/outbox/card_acks/"
            "pm_parent_segment_decision-delivery-001-attempt-001.ack.json"
        )

        self.assertEqual(
            runtime_gateway.classify_runtime_state_surface(break_glass_index).surface_id,
            "flowpilot_break_glass_state",
        )
        self.assertEqual(
            runtime_gateway.classify_runtime_state_surface(role_output_body).surface_id,
            "flowpilot_role_output_state",
        )
        self.assertEqual(
            runtime_gateway.classify_runtime_state_surface(gate_output_body).surface_id,
            "flowpilot_role_output_state",
        )
        self.assertEqual(
            runtime_gateway.classify_runtime_state_surface(card_read_receipt).surface_id,
            "flowpilot_card_state",
        )
        self.assertEqual(
            runtime_gateway.classify_runtime_state_surface(card_ack).surface_id,
            "flowpilot_card_state",
        )
        runtime_gateway.assert_runtime_gateway_write(
            break_glass_index,
            runtime_gateway.GATEWAY_BREAK_GLASS,
            operation="test_break_glass_index_write",
        )
        runtime_gateway.assert_runtime_gateway_write(
            role_output_body,
            runtime_gateway.GATEWAY_ROLE_OUTPUT,
            operation="test_role_output_body_write",
        )
        runtime_gateway.assert_runtime_gateway_write(
            gate_output_body,
            runtime_gateway.GATEWAY_ROLE_OUTPUT,
            operation="test_gate_output_body_write",
        )
        runtime_gateway.assert_runtime_gateway_write(
            card_read_receipt,
            runtime_gateway.GATEWAY_CARD_RUNTIME,
            operation="test_card_read_receipt_write",
        )
        runtime_gateway.assert_runtime_gateway_write(
            card_ack,
            runtime_gateway.GATEWAY_CARD_RUNTIME,
            operation="test_card_ack_write",
        )

    def test_low_level_runtime_writers_are_gatewayed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-runtime-gateway-") as tmp:
            root = Path(tmp)
            flowpilot_router_io_json.write_json_atomic(
                root / ".flowpilot" / "current.json",
                {
                    "schema_version": "flowpilot.current.v1",
                    "run_id": "run-test",
                    "run_root": ".flowpilot/runs/run-test",
                },
            )
            packet_runtime_schema.write_json_atomic(
                root / ".flowpilot" / "runs" / "run-test" / "packets" / "packet-1" / "packet_envelope.json",
                {"schema_version": packet_runtime_schema.PACKET_ENVELOPE_SCHEMA, "packet_id": "packet-1"},
            )
            role_output_runtime_schema_io._write_json(
                root / ".flowpilot" / "runs" / "run-test" / "role_outputs" / "output-1.json",
                {"schema_version": "flowpilot.role_output_receipt.v1"},
            )

            self.assertTrue((root / ".flowpilot" / "current.json").exists())
            self.assertTrue(
                (
                    root
                    / ".flowpilot"
                    / "runs"
                    / "run-test"
                    / "packets"
                    / "packet-1"
                    / "packet_envelope.json"
                ).exists()
            )
            self.assertTrue((root / ".flowpilot" / "runs" / "run-test" / "role_outputs" / "output-1.json").exists())

    def test_static_inventory_and_flowguard_runtime_gateway_report_pass(self) -> None:
        sites, findings = flowpilot_runtime_gateway_adoption.scan_static_write_sites()
        report = flowpilot_runtime_gateway_adoption.build_report()

        self.assertGreater(len(sites), 0)
        self.assertEqual(findings, [])
        self.assertTrue(report["ok"], report["static_findings"])
        self.assertTrue(report["flowguard_report"]["ok"], report["flowguard_report"]["findings"])
        self.assertEqual(
            report["critical_write_site_count"],
            report["gatewayed_critical_write_site_count"],
        )

    def test_flowguard_runtime_gateway_known_bad_direct_write_is_blocked(self) -> None:
        bad_cases = flowpilot_runtime_gateway_adoption.known_bad_cases()
        self.assertEqual(len(bad_cases), 1)
        finding_codes = {
            finding["code"]
            for finding in bad_cases[0]["report"]["findings"]
        }
        self.assertTrue(set(bad_cases[0]["expected_codes"]).issubset(finding_codes))
        self.assertFalse(bad_cases[0]["report"]["ok"])


if __name__ == "__main__":
    unittest.main()
