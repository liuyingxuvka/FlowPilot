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
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class FlowPilotPacketRuntimeTests(unittest.TestCase):
    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="flowpilot-packets-"))
        _write_json(
            root / ".flowpilot" / "current.json",
            {
                "current_run_id": "run-test",
                "current_run_root": ".flowpilot/runs/run-test",
            },
        )
        return root

    def issue_packet(self, root: Path, *, packet_id: str = "packet-001", body_text: str = "SECRET_WORKER_BODY") -> dict:
        return packet_runtime.create_packet(
            root,
            packet_id=packet_id,
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text=body_text,
        )

    def test_pm_issue_writes_physical_envelope_body_and_ledger(self) -> None:
        root = self.make_project()
        body_text = "SECRET_BODY_SENTINEL controller must never see this"

        envelope = self.issue_packet(root, body_text=body_text)

        envelope_path = root / ".flowpilot" / "runs" / "run-test" / "packets" / "packet-001" / "packet_envelope.json"
        body_path = root / ".flowpilot" / "runs" / "run-test" / "packets" / "packet-001" / "packet_body.md"
        ledger_path = root / ".flowpilot" / "runs" / "run-test" / "packet_ledger.json"
        status_path = root / envelope["controller_status_packet_path"]

        self.assertTrue(envelope_path.exists())
        self.assertTrue(body_path.exists())
        self.assertTrue(ledger_path.exists())
        self.assertTrue(status_path.exists())
        self.assertEqual(body_path.read_text(encoding="utf-8"), body_text)
        self.assertEqual(envelope["body_hash"], hashlib.sha256(body_text.encode("utf-8")).hexdigest())

        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        self.assertEqual(ledger["schema_version"], "flowpilot.packet_ledger.v2")
        self.assertEqual(ledger["active_packet_id"], "packet-001")
        self.assertEqual(ledger["packets"][0]["packet_body_path"], envelope["body_path"])
        self.assertTrue(ledger["packets"][0]["physical_packet_files_written"])
        self.assertTrue(ledger["packets"][0]["controller_context_body_exclusion_verified"])
        self.assertFalse(ledger["controller_boundary"]["controller_may_read_packet_body"])

    def test_controller_handoff_contains_envelope_only_not_body_content(self) -> None:
        root = self.make_project()
        body_text = "DO_NOT_LEAK_PACKET_BODY_7f4ec1"
        envelope = self.issue_packet(root, body_text=body_text)

        handoff = packet_runtime.build_controller_handoff(
            envelope,
            envelope_path=".flowpilot/runs/run-test/packets/packet-001/packet_envelope.json",
        )
        handoff_text = packet_runtime.controller_handoff_text(handoff)

        self.assertIn("packet_envelope_only", handoff_text)
        self.assertIn("packet_body.md", handoff_text)
        self.assertNotIn(body_text, handoff_text)
        self.assertIn("read_packet_body", handoff["controller_forbidden_actions"])

    def test_only_target_role_reads_packet_body(self) -> None:
        root = self.make_project()
        envelope = self.issue_packet(root, body_text="worker-only instructions")

        self.assertEqual(
            packet_runtime.read_packet_body_for_role(root, envelope, role="worker_a"),
            "worker-only instructions",
        )
        with self.assertRaises(packet_runtime.PacketRuntimeError):
            packet_runtime.read_packet_body_for_role(root, envelope, role="controller")

    def test_worker_result_writes_physical_result_files_and_reviewer_passes(self) -> None:
        root = self.make_project()
        envelope = self.issue_packet(root)

        result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role="worker_a",
            completed_by_agent_id="agent-worker-a-1",
            result_body_text="commands, files, screenshots, and findings",
            next_recipient="human_like_reviewer",
        )
        audit = packet_runtime.validate_for_reviewer(
            root,
            packet_envelope=envelope,
            result_envelope=result,
            agent_role_map={"agent-worker-a-1": "worker_a"},
        )

        result_envelope_path = root / ".flowpilot" / "runs" / "run-test" / "packets" / "packet-001" / "result_envelope.json"
        result_body_path = root / ".flowpilot" / "runs" / "run-test" / "packets" / "packet-001" / "result_body.md"
        self.assertTrue(result_envelope_path.exists())
        self.assertTrue(result_body_path.exists())
        self.assertEqual(result["result_body_hash"], hashlib.sha256(result_body_path.read_bytes()).hexdigest())
        self.assertTrue(audit["passed"])
        self.assertTrue(audit["packet_runtime_physical_files_checked"])
        self.assertTrue(audit["controller_context_body_exclusion_checked"])
        self.assertEqual(audit["blockers"], [])
        with self.assertRaises(packet_runtime.PacketRuntimeError):
            packet_runtime.read_result_body_for_role(root, result, role="controller")

    def test_reviewer_blocks_packet_or_result_hash_mismatch(self) -> None:
        root = self.make_project()
        envelope = self.issue_packet(root)
        result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role="worker_a",
            completed_by_agent_id="agent-worker-a-1",
            result_body_text="valid result",
            next_recipient="human_like_reviewer",
        )
        body_path = root / envelope["body_path"]
        body_path.write_text("tampered packet body", encoding="utf-8")

        audit = packet_runtime.validate_for_reviewer(
            root,
            packet_envelope=envelope,
            result_envelope=result,
            agent_role_map={"agent-worker-a-1": "worker_a"},
        )

        self.assertFalse(audit["passed"])
        self.assertIn("packet_body_hash_mismatch", audit["blockers"])

    def test_reviewer_blocks_wrong_role_and_controller_origin(self) -> None:
        root = self.make_project()
        envelope = self.issue_packet(root)

        wrong_role_result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role="worker_b",
            completed_by_agent_id="agent-worker-b-1",
            result_body_text="wrong role result",
            next_recipient="human_like_reviewer",
            strict_role=False,
        )
        wrong_role_audit = packet_runtime.validate_for_reviewer(
            root,
            packet_envelope=envelope,
            result_envelope=wrong_role_result,
            agent_role_map={"agent-worker-b-1": "worker_b"},
        )
        self.assertFalse(wrong_role_audit["passed"])
        self.assertIn("result_completed_by_wrong_role", wrong_role_audit["blockers"])

        controller_result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role="controller",
            completed_by_agent_id="agent-controller-1",
            result_body_text="controller tried to complete worker scope",
            next_recipient="human_like_reviewer",
            strict_role=False,
        )
        controller_audit = packet_runtime.validate_for_reviewer(
            root,
            packet_envelope=envelope,
            result_envelope=controller_result,
            agent_role_map={"agent-controller-1": "controller"},
        )
        self.assertFalse(controller_audit["passed"])
        self.assertIn("controller_origin_artifact", controller_audit["blockers"])
        self.assertIn("result_completed_by_wrong_role", controller_audit["blockers"])


if __name__ == "__main__":
    unittest.main()
