from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))

import packet_runtime  # noqa: E402


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class FlowPilotOutputContractTests(unittest.TestCase):
    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="flowpilot-output-contracts-"))
        _write_json(
            root / ".flowpilot" / "current.json",
            {
                "current_run_id": "run-test",
                "current_run_root": ".flowpilot/runs/run-test",
            },
        )
        return root

    def read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_contract_registry_declares_pm_selection_and_self_check_policy(self) -> None:
        registry_path = ROOT / "skills" / "flowpilot" / "assets" / "runtime_kit" / "contracts" / "contract_index.json"
        registry = self.read_json(registry_path)

        self.assertEqual(registry["schema_version"], "flowpilot.output_contract_registry.v1")
        self.assertTrue(registry["pm_must_select_contract_before_dispatch"])
        self.assertTrue(registry["role_must_self_check_before_return"])
        contract_ids = {item["contract_id"] for item in registry["contracts"]}
        self.assertIn("flowpilot.output_contract.worker_current_node_result.v1", contract_ids)
        self.assertIn("flowpilot.output_contract.material_sufficiency_report.v1", contract_ids)
        self.assertIn("flowpilot.output_contract.terminal_backward_replay_report.v1", contract_ids)

    def test_pm_packet_repeats_output_contract_in_envelope_body_ledger_and_result(self) -> None:
        root = self.make_project()
        contract = {
            "schema_version": "flowpilot.output_contract.v1",
            "contract_id": "flowpilot.output_contract.worker_current_node_result.v1",
            "selected_by_role": "project_manager",
            "recipient_role": "worker_a",
            "task_family": "worker.current_node",
            "required_result_body_sections": ["Status", "Evidence", "Contract Self-Check"],
            "contract_self_check_required": True,
            "reviewer_must_block_missing_or_failed_check": True,
        }

        envelope = packet_runtime.create_packet(
            root,
            packet_id="packet-001",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="Build the current node slice.",
            output_contract=contract,
        )
        envelope_path = root / ".flowpilot" / "runs" / "run-test" / "packets" / "packet-001" / "packet_envelope.json"
        body_path = envelope_path.with_name("packet_body.md")
        ledger_path = root / ".flowpilot" / "runs" / "run-test" / "packet_ledger.json"

        self.assertEqual(envelope["output_contract_id"], contract["contract_id"])
        self.assertEqual(envelope["output_contract"]["recipient_role"], "worker_a")
        body_text = body_path.read_text(encoding="utf-8")
        self.assertIn("## Output Contract", body_text)
        self.assertIn(contract["contract_id"], body_text)

        ledger = self.read_json(ledger_path)
        self.assertEqual(ledger["packets"][0]["output_contract_id"], contract["contract_id"])
        self.assertEqual(ledger["packets"][0]["packet_envelope"]["output_contract_id"], contract["contract_id"])

        relayed = packet_runtime.controller_relay_envelope(
            root,
            envelope=envelope,
            envelope_path=envelope_path,
            controller_agent_id="controller",
            received_from_role="project_manager",
            relayed_to_role="worker_a",
        )
        packet_runtime.read_packet_body_for_role(root, relayed, role="worker_a")
        result_body = (
            "finished\n\n"
            "## Contract Self-Check\n\n"
            "- source_output_contract_id: flowpilot.output_contract.worker_current_node_result.v1\n"
            "- self_check_decision: satisfied\n"
        )
        result = packet_runtime.write_result(
            root,
            packet_envelope=relayed,
            completed_by_role="worker_a",
            completed_by_agent_id="worker-a-agent",
            result_body_text=result_body,
            next_recipient="human_like_reviewer",
        )

        self.assertEqual(result["source_output_contract_id"], contract["contract_id"])
        self.assertEqual(result["output_contract"]["contract_id"], contract["contract_id"])
        self.assertTrue(result["contract_self_check"]["completed"])
        self.assertTrue(result["contract_self_check"]["passed"])
        result_path = root / result["result_body_path"]
        self.assertEqual(result["result_body_hash"], hashlib.sha256(result_path.read_bytes()).hexdigest())

    def test_packet_rejects_contract_for_wrong_recipient(self) -> None:
        root = self.make_project()

        with self.assertRaises(packet_runtime.PacketRuntimeError):
            packet_runtime.create_packet(
                root,
                packet_id="packet-001",
                from_role="project_manager",
                to_role="worker_a",
                node_id="node-001",
                body_text="work",
                output_contract={
                    "schema_version": "flowpilot.output_contract.v1",
                    "contract_id": "flowpilot.output_contract.worker_current_node_result.v1",
                    "selected_by_role": "project_manager",
                    "recipient_role": "worker_b",
                },
            )


if __name__ == "__main__":
    unittest.main()
