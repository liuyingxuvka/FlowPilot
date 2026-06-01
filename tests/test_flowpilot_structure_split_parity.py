from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
sys.path.insert(0, str(ASSETS))

import flowpilot_router_controller_scheduler_receipts_packet_fold_evidence as packet_fold_evidence  # noqa: E402
import flowpilot_router_controller_scheduler_receipts_packet_fold_record_evidence as packet_fold_record_evidence  # noqa: E402
import flowpilot_router_controller_scheduler_receipts_packet_folds as packet_folds  # noqa: E402
import flowpilot_router_work_packets_current_node_relay as current_node_relay  # noqa: E402
import flowpilot_router_work_packets_current_node_relay_leases as current_node_relay_leases  # noqa: E402
import flowpilot_router_work_packets_current_node_relay_runtime_ops as current_node_relay_runtime_ops  # noqa: E402
import flowpilot_runtime_command_dispatch as runtime_command_dispatch  # noqa: E402
import flowpilot_runtime_commands as runtime_commands  # noqa: E402


class FlowPilotStructureSplitParityTests(unittest.TestCase):
    def test_controller_receipt_packet_fold_facade_preserves_public_helpers(self) -> None:
        self.assertIs(
            packet_folds._controller_receipt_fold_records,
            packet_fold_evidence._controller_receipt_fold_records,
        )
        self.assertIs(
            packet_folds._packet_dispatch_record_evidence,
            packet_fold_record_evidence._packet_dispatch_record_evidence,
        )
        self.assertIs(
            packet_folds._result_relay_record_evidence,
            packet_fold_record_evidence._result_relay_record_evidence,
        )
        self.assertIn("_apply_registered_controller_receipt_evidence_fold", packet_folds.__all__)

    def test_current_node_relay_facade_preserves_lease_and_runtime_helpers(self) -> None:
        self.assertIs(
            current_node_relay._current_node_active_holder_lease_plan,
            current_node_relay_leases._current_node_active_holder_lease_plan,
        )
        self.assertIs(
            current_node_relay._packet_runtime_relay_operations,
            current_node_relay_runtime_ops._packet_runtime_relay_operations,
        )
        self.assertIs(
            current_node_relay._result_runtime_relay_operations,
            current_node_relay_runtime_ops._result_runtime_relay_operations,
        )

    def test_runtime_commands_facade_uses_dispatch_child(self) -> None:
        self.assertIs(
            runtime_commands.execute_runtime_command,
            runtime_command_dispatch.execute_runtime_command,
        )
        self.assertIn("main", runtime_commands.__all__)
        self.assertIn("execute_runtime_command", runtime_command_dispatch.__all__)

    def test_runtime_dispatch_uses_injected_receive_card_helper(self) -> None:
        result = runtime_command_dispatch.execute_runtime_command(
            Path("."),
            SimpleNamespace(command="receive-card"),
            packet_runtime=object(),
            card_runtime=object(),
            flowpilot_router=object(),
            role_output_runtime=object(),
            execute_role_output_command=lambda *args, **kwargs: {"unexpected": True},
            read_text_arg=lambda text_value, file_value: text_value,
            read_body_json=lambda root, raw_json, body_file: None,
            record_router_event_or_blocked_next_action=lambda root, event_name, envelope: {},
            receive_card=lambda root, args: {"ok": True, "helper": "receive-card"},
            receive_card_bundle=lambda root, args: {"unexpected": True},
        )

        self.assertEqual(result, {"ok": True, "helper": "receive-card"})


if __name__ == "__main__":
    unittest.main()
