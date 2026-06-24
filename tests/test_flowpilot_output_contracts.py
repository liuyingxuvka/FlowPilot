from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))

import packet_runtime  # noqa: E402
import role_output_runtime  # noqa: E402


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class FlowPilotOutputContractTests(unittest.TestCase):
    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="flowpilot-output-contracts-"))
        _write_json(
            root / ".flowpilot" / "current.json",
            {
                "run_id": "run-test",
                "run_root": ".flowpilot/runs/run-test",
            },
        )
        run_root = root / ".flowpilot" / "runs" / "run-test"
        run_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(ROOT / "skills" / "flowpilot" / "assets" / "runtime_kit", run_root / "runtime_kit")
        return root

    def read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_pm_packet_repeats_output_contract_in_envelope_body_ledger_and_result(self) -> None:
        root = self.make_project()
        default_contract = packet_runtime.default_output_contract(
            packet_type="work_packet",
            from_role="project_manager",
            to_role="worker",
            node_id="node-001",
        )
        self.assertIn("PM Suggestion Items", default_contract["required_result_body_sections"])  # type: ignore[index]
        self.assertIn("Artifact Handoff", default_contract["required_result_body_sections"])  # type: ignore[index]
        contract = {
            "schema_version": "flowpilot.output_contract.v1",
            "contract_id": "flowpilot.output_contract.worker_current_node_result.v1",
            "selected_by_role": "project_manager",
            "recipient_role": "worker",
            "task_family": "worker.current_node",
            "required_result_body_sections": ["Status", "Evidence", "Contract Self-Check"],
            "contract_self_check_required": True,
            "reviewer_must_block_missing_or_failed_check": True,
        }

        envelope = packet_runtime.create_packet(
            root,
            packet_id="packet-001",
            from_role="project_manager",
            to_role="worker",
            node_id="node-001",
            body_text="Build the current node slice.",
            output_contract=contract,
        )
        envelope_path = root / ".flowpilot" / "runs" / "run-test" / "packets" / "packet-001" / "packet_envelope.json"
        body_path = envelope_path.with_name("packet_body.md")
        ledger_path = root / ".flowpilot" / "runs" / "run-test" / "packet_ledger.json"

        self.assertEqual(envelope["output_contract_id"], contract["contract_id"])
        self.assertEqual(envelope["output_contract"]["recipient_role"], "worker")
        body_text = body_path.read_text(encoding="utf-8")
        self.assertIn("## Output Contract", body_text)
        self.assertIn("## Report Contract For This Task", body_text)
        self.assertIn(contract["contract_id"], body_text)
        self.assertIn("Do not rename fields with synonyms", body_text)
        self.assertIn("Required sealed body sections", body_text)
        self.assertIn("Required return envelope fields", body_text)

        ledger = self.read_json(ledger_path)
        self.assertEqual(ledger["packets"][0]["output_contract_id"], contract["contract_id"])
        self.assertEqual(ledger["packets"][0]["packet_envelope"]["output_contract_id"], contract["contract_id"])

        relayed = packet_runtime.deliver_envelope_metadata(
            root,
            envelope=envelope,
            envelope_path=envelope_path,
            controller_agent_id="controller",
            received_from_role="project_manager",
            relayed_to_role="worker",
        )
        packet_runtime.read_packet_body_for_role(root, relayed, role="worker")
        result_body = (
            "finished\n\n"
            "## Contract Self-Check\n\n"
            "- source_output_contract_id: flowpilot.output_contract.worker_current_node_result.v1\n"
            "- self_check_decision: satisfied\n"
        )
        result = packet_runtime.write_result(
            root,
            packet_envelope=relayed,
            completed_by_role="worker",
            completed_by_agent_id="worker-1-agent",
            result_body_text=result_body,
            next_recipient="human_like_reviewer",
        )

        self.assertEqual(result["source_output_contract_id"], contract["contract_id"])
        self.assertEqual(result["output_contract"]["contract_id"], contract["contract_id"])
        self.assertTrue(result["contract_self_check"]["completed"])
        self.assertTrue(result["contract_self_check"]["passed"])
        result_path = root / result["result_body_path"]
        self.assertEqual(result["result_body_hash"], hashlib.sha256(result_path.read_bytes()).hexdigest())

    def test_contract_self_check_metadata_accepts_common_heading_and_decision_formats(self) -> None:
        contract = {
            "schema_version": "flowpilot.output_contract.v1",
            "contract_id": "flowpilot.output_contract.worker_current_node_result.v1",
            "contract_self_check_required": True,
        }

        h1 = packet_runtime.contract_self_check_metadata(
            "# Contract Self-Check\n\n\"self_check_decision\": \"satisfied\"\n",
            contract,
        )
        self.assertTrue(h1["completed"])
        self.assertTrue(h1["passed"])
        self.assertEqual(h1["missing_required_fields"], ["source_output_contract_id"])

        plain_heading = packet_runtime.contract_self_check_metadata(
            "Status\n\nComplete\n\nContract Self-Check\n\nPassed.",
            contract,
        )
        self.assertTrue(plain_heading["completed"])
        self.assertTrue(plain_heading["passed"])
        self.assertEqual(plain_heading["missing_required_fields"], ["source_output_contract_id"])

        failed = packet_runtime.contract_self_check_metadata(
            "## Contract Self-Check\n\n- self_check_decision: failed\n",
            contract,
        )
        self.assertTrue(failed["completed"])
        self.assertFalse(failed["passed"])
        self.assertIn("source_output_contract_id", failed["missing_required_fields"])

        wrong_contract = packet_runtime.contract_self_check_metadata(
            "## Contract Self-Check\n\n"
            "- source_output_contract_id: flowpilot.output_contract.other.v1\n"
            "- self_check_decision: satisfied\n",
            contract,
        )
        self.assertTrue(wrong_contract["completed"])
        self.assertFalse(wrong_contract["passed"])
        self.assertFalse(wrong_contract["source_output_contract_id_matches"])

    def test_contract_self_check_metadata_reports_live_worker_missing_fields(self) -> None:
        contract = {
            "schema_version": "flowpilot.output_contract.v1",
            "contract_id": "flowpilot.output_contract.worker_material_scan_result.v1",
            "contract_self_check_required": True,
        }

        live_worker_shape = (
            "Material scan result\n\n"
            "## Contract Self-Check\n\n"
            "- output_contract_id: flowpilot.output_contract.worker_material_scan_result.v1\n"
        )

        result = packet_runtime.contract_self_check_metadata(live_worker_shape, contract)

        self.assertTrue(result["completed"])
        self.assertFalse(result["passed"])
        self.assertIsNone(result["decision"])
        self.assertIsNone(result["declared_source_output_contract_id"])
        self.assertEqual(
            result["missing_required_fields"],
            ["self_check_decision", "source_output_contract_id"],
        )

    def test_packet_rejects_contract_for_wrong_recipient(self) -> None:
        root = self.make_project()

        with self.assertRaises(packet_runtime.PacketRuntimeError):
            packet_runtime.create_packet(
                root,
                packet_id="packet-001",
                from_role="project_manager",
                to_role="worker",
                node_id="node-001",
                body_text="work",
                output_contract={
                    "schema_version": "flowpilot.output_contract.v1",
                    "contract_id": "flowpilot.output_contract.worker_current_node_result.v1",
                    "selected_by_role": "project_manager",
                    "recipient_role": "human_like_reviewer",
                },
            )

    def test_terminal_flowguard_coverage_report_contract_is_registered(self) -> None:
        root = self.make_project()

        skeleton = role_output_runtime.build_output_skeleton(
            root,
            output_type="flowguard_terminal_coverage_report",
            role="flowguard_operator",
        )

        self.assertEqual(skeleton["schema_version"], "flowpilot.flowguard_terminal_coverage_report.v1")
        self.assertEqual(skeleton["reviewed_by_role"], "flowguard_operator")
        self.assertEqual(skeleton["modeled_boundary"], "terminal_flowguard_coverage")
        self.assertTrue(skeleton["coverage_matrix_ref"]["fresh"])
        self.assertIn("missing_or_stale_evidence", skeleton)


if __name__ == "__main__":
    unittest.main()
